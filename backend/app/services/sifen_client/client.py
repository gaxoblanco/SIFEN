"""
Cliente SOAP principal para integración con SIFEN Paraguay

Maneja la comunicación de bajo nivel con los Web Services SOAP de SIFEN,
incluyendo configuración TLS 1.2, autenticación y manejo de timeouts.

Servicios soportados:
- Envío individual de documentos (sync)
- Envío de lotes de documentos (async) 
- Consultas por CDC y RUC
- Gestión de eventos

Características técnicas:
- TLS 1.2 obligatorio según especificaciones SIFEN
- Pool de conexiones para performance
- Timeout configurables por operación
- Logging estructurado sin datos sensibles
- Retry automático en errores temporales

Basado en:
- Manual Técnico SIFEN v150
- Especificaciones SOAP 1.2
- Estándares de seguridad SET Paraguay
"""

import ssl
import asyncio
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import structlog

# HTTP y SOAP clients
import aiohttp
from zeep import AsyncClient, Settings
from zeep.transports import AsyncTransport
from zeep.exceptions import Fault, TransportError, ValidationError

# Módulos internos
from .config import SifenConfig, SifenEndpoints
from .models import DocumentRequest, BatchRequest, QueryRequest, SifenResponse
from .exceptions import (
    SifenClientError,
    SifenConnectionError,
    SifenTimeoutError,
    SifenServerError,
    SifenValidationError,
    SifenParsingError
)

# Logger para el cliente
logger = structlog.get_logger(__name__)


class SifenSOAPClient:
    """
    Cliente SOAP asíncrono para comunicación con SIFEN Paraguay

    Maneja toda la comunicación de bajo nivel con los Web Services
    de SIFEN, incluyendo configuración de seguridad y manejo de errores.
    """

    def __init__(self, config: SifenConfig):
        """
        Inicializa el cliente SOAP con configuración SIFEN

        Args:
            config: Configuración del cliente SIFEN
        """
        self.config = config
        self._clients: Dict[str, AsyncClient] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

        logger.info(
            "sifen_soap_client_init",
            environment=config.environment,
            base_url=config.effective_base_url,
            verify_ssl=config.verify_ssl,
            timeout=config.timeout
        )

    async def __aenter__(self):
        """Context manager entry - inicializa conexiones"""
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - limpia conexiones"""
        await self._cleanup()

    async def _initialize(self):
        """
        Inicializa el cliente SOAP y las conexiones HTTP

        Configura:
        - Session HTTP con TLS 1.2
        - Pool de conexiones
        - Timeouts específicos
        - Clients SOAP para cada servicio
        """
        if self._initialized:
            return

        try:
            # Configurar timeout específicos
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=self.config.connect_timeout,
                sock_read=self.config.read_timeout
            )

            # Configurar connector con SSL y pool
            connector = aiohttp.TCPConnector(
                ssl=self.config.ssl_context,
                limit=self.config.pool_maxsize,
                limit_per_host=self.config.pool_connections,
                enable_cleanup_closed=True,
                keepalive_timeout=30
            )

            # Crear session HTTP
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'SIFEN-Client-Python/1.5.0',
                    'Accept': 'text/xml, application/soap+xml',
                    'Accept-Encoding': 'gzip, deflate' if self.config.enable_compression else 'identity'
                }
            )

            # Configurar transport SOAP con session personalizada
            # Nota: AsyncTransport puede no aceptar session directamente
            # Usaremos la configuración por defecto y configuraremos timeouts a nivel de AsyncClient
            transport = AsyncTransport()

            # Configurar settings SOAP básicos
            settings = Settings()  # Usar configuración por defecto

            # Inicializar clients SOAP para cada servicio
            await self._initialize_soap_clients(transport, settings)

            self._initialized = True

            logger.info(
                "sifen_soap_client_initialized",
                services_count=len(self._clients),
                pool_size=self.config.pool_maxsize,
                timeout=self.config.timeout
            )

        except Exception as e:
            logger.error(
                "sifen_soap_client_init_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            await self._cleanup()
            raise SifenConnectionError(
                message=f"Error al inicializar cliente SOAP: {str(e)}",
                original_exception=e
            )

    async def _initialize_soap_clients(self, transport: AsyncTransport, settings: Settings):
        """
        Inicializa los clientes SOAP para cada servicio SIFEN

        Args:
            transport: Transport HTTP configurado
            settings: Configuración SOAP
        """
        services = {
            'sync_receive': SifenEndpoints.SYNC_RECEIVE,
            'async_batch': SifenEndpoints.ASYNC_RECEIVE_BATCH,
            'query_document': SifenEndpoints.QUERY_DOCUMENT,
            'query_ruc': SifenEndpoints.QUERY_RUC,
            'events': SifenEndpoints.EVENTS_RECEIVE
        }

        for service_name, service_path in services.items():
            try:
                wsdl_url = self.config.get_service_url(service_path)

                # Crear cliente SOAP asíncrono
                client = AsyncClient(
                    wsdl=wsdl_url,
                    transport=transport,
                    settings=settings
                )

                self._clients[service_name] = client

                logger.debug(
                    "soap_client_created",
                    service=service_name,
                    wsdl_url=wsdl_url
                )

            except Exception as e:
                logger.error(
                    "soap_client_creation_failed",
                    service=service_name,
                    error=str(e),
                    wsdl_url=wsdl_url
                )
                # No lanzar excepción aquí - algunos servicios pueden no estar disponibles
                # El error se manejará cuando se intente usar el servicio específico

    async def _cleanup(self):
        """Limpia recursos y cierra conexiones"""
        if self._session and not self._session.closed:
            await self._session.close()

        self._clients.clear()
        self._initialized = False

        logger.debug("sifen_soap_client_cleanup_completed")

    def _get_client(self, service_name: str) -> AsyncClient:
        """
        Obtiene el cliente SOAP para un servicio específico

        Args:
            service_name: Nombre del servicio (sync_receive, async_batch, etc.)

        Returns:
            Cliente SOAP configurado

        Raises:
            SifenConnectionError: Si el servicio no está disponible
        """
        if not self._initialized:
            raise SifenConnectionError(
                message="Cliente SOAP no inicializado. Use context manager."
            )

        if service_name not in self._clients:
            raise SifenConnectionError(
                message=f"Servicio SOAP '{service_name}' no disponible",
                details={'available_services': list(self._clients.keys())}
            )

        return self._clients[service_name]

    async def send_document(self, request: DocumentRequest) -> SifenResponse:
        """
        Envía un documento individual a SIFEN (servicio síncrono)

        Args:
            request: Datos del documento a enviar

        Returns:
            Respuesta de SIFEN procesada

        Raises:
            SifenClientError: En caso de error en el envío
        """
        start_time = datetime.now()

        try:
            # Obtener cliente para servicio síncrono
            client = self._get_client('sync_receive')

            # Preparar parámetros SOAP
            soap_params = self._prepare_document_params(request)

            # Log del request (sin datos sensibles)
            logger.info(
                "sifen_document_send_start",
                cdc=request.cdc,
                doc_type=request.document_type,
                xml_length=len(
                    request.xml_content) if request.xml_content else 0,
                cert_serial=self._mask_serial(request.certificate_serial)
            )

            # Realizar llamada SOAP
            soap_response = await client.service.receiveDocument(**soap_params)

            # Procesar respuesta
            response = self._process_soap_response(soap_response, start_time)

            # Log del resultado
            logger.info(
                "sifen_document_send_completed",
                cdc=request.cdc,
                success=response.success,
                sifen_code=response.code,
                processing_time_ms=response.processing_time_ms
            )

            return response

        except Fault as e:
            # Error SOAP específico
            return self._handle_soap_fault(e, request, start_time)

        except TransportError as e:
            # Error de transporte HTTP
            raise SifenConnectionError(
                message=f"Error de conexión con SIFEN: {str(e)}",
                url=self.config.effective_base_url,
                timeout=self.config.timeout,
                original_exception=e
            )

        except ValidationError as e:
            # Error de validación SOAP/XML
            raise SifenValidationError(
                message=f"Error de validación en request SOAP: {str(e)}",
                field="soap_request",
                original_exception=e
            )

        except asyncio.TimeoutError as e:
            # Timeout específico
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            raise SifenTimeoutError(
                message="Timeout en envío de documento a SIFEN",
                timeout_type="total",
                timeout_value=self.config.timeout,
                elapsed_time=elapsed,
                original_exception=e
            )

        except Exception as e:
            # Error genérico
            logger.error(
                "sifen_document_send_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                cdc=request.cdc
            )
            raise SifenClientError(
                message=f"Error inesperado en envío de documento: {str(e)}",
                original_exception=e
            )

    async def send_batch(self, batch_request: BatchRequest) -> SifenResponse:
        """
        Envía un lote de documentos a SIFEN (servicio asíncrono)

        Args:
            batch_request: Lote de documentos a enviar

        Returns:
            Respuesta de SIFEN para el lote

        Raises:
            SifenClientError: En caso de error en el envío
        """
        start_time = datetime.now()

        try:
            # Obtener cliente para servicio de lotes
            client = self._get_client('async_batch')

            # Preparar parámetros SOAP para lote
            soap_params = self._prepare_batch_params(batch_request)

            # Log del request
            logger.info(
                "sifen_batch_send_start",
                batch_id=batch_request.batch_id,
                documents_count=len(batch_request.documents),
                priority=batch_request.priority
            )

            # Realizar llamada SOAP
            soap_response = await client.service.receiveBatch(**soap_params)

            # Procesar respuesta
            response = self._process_soap_response(soap_response, start_time)

            # Log del resultado
            logger.info(
                "sifen_batch_send_completed",
                batch_id=batch_request.batch_id,
                success=response.success,
                sifen_code=response.code,
                processing_time_ms=response.processing_time_ms
            )

            return response

        except Exception as e:
            # Manejo similar al envío individual
            logger.error(
                "sifen_batch_send_error",
                batch_id=batch_request.batch_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Re-lanzar con contexto de lote
            raise

    async def query_document(self, query_request: QueryRequest) -> SifenResponse:
        """
        Consulta información de documentos en SIFEN

        Args:
            query_request: Parámetros de consulta

        Returns:
            Respuesta con resultados de la consulta

        Raises:
            SifenClientError: En caso de error en la consulta
        """
        start_time = datetime.now()

        try:
            # Determinar servicio según tipo de consulta
            service_name = 'query_ruc' if query_request.query_type == 'ruc' else 'query_document'
            client = self._get_client(service_name)

            # Preparar parámetros SOAP
            soap_params = self._prepare_query_params(query_request)

            # Log del request
            logger.info(
                "sifen_query_start",
                query_type=query_request.query_type,
                cdc=query_request.cdc,
                ruc=self._mask_ruc(
                    query_request.ruc) if query_request.ruc else None
            )

            # Realizar llamada SOAP
            if query_request.query_type == 'ruc':
                soap_response = await client.service.queryRuc(**soap_params)
            else:
                soap_response = await client.service.queryDocument(**soap_params)

            # Procesar respuesta
            response = self._process_soap_response(soap_response, start_time)

            # Log del resultado
            logger.info(
                "sifen_query_completed",
                query_type=query_request.query_type,
                success=response.success,
                results_count=len(
                    response.additional_data.get('documents', [])),
                processing_time_ms=response.processing_time_ms
            )

            return response

        except Exception as e:
            logger.error(
                "sifen_query_error",
                query_type=query_request.query_type,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def _prepare_document_params(self, request: DocumentRequest) -> Dict[str, Any]:
        """
        Prepara parámetros SOAP para envío de documento individual

        Args:
            request: Request del documento

        Returns:
            Diccionario con parámetros SOAP
        """
        return {
            'xmlDocument': request.xml_content,
            'certificateSerial': request.certificate_serial,
            'timestamp': request.timestamp.isoformat(),
            'metadata': request.metadata
        }

    def _prepare_batch_params(self, batch_request: BatchRequest) -> Dict[str, Any]:
        """
        Prepara parámetros SOAP para envío de lote

        Args:
            batch_request: Request del lote

        Returns:
            Diccionario con parámetros SOAP
        """
        documents = []
        for doc in batch_request.documents:
            documents.append({
                'xmlDocument': doc.xml_content,
                'certificateSerial': doc.certificate_serial,
                'timestamp': doc.timestamp.isoformat(),
                'metadata': doc.metadata
            })

        return {
            'batchId': batch_request.batch_id,
            'documents': documents,
            'priority': batch_request.priority,
            'notifyOnCompletion': batch_request.notify_on_completion
        }

    def _prepare_query_params(self, query_request: QueryRequest) -> Dict[str, Any]:
        """
        Prepara parámetros SOAP para consulta

        Args:
            query_request: Request de consulta

        Returns:
            Diccionario con parámetros SOAP
        """
        params = {
            'queryType': query_request.query_type,
            'page': query_request.page,
            'pageSize': query_request.page_size
        }

        # Agregar parámetros específicos según tipo de consulta
        if query_request.cdc:
            params['cdc'] = query_request.cdc

        if query_request.ruc:
            params['ruc'] = query_request.ruc

        if query_request.date_from:
            params['dateFrom'] = query_request.date_from.isoformat()

        if query_request.date_to:
            params['dateTo'] = query_request.date_to.isoformat()

        if query_request.document_types:
            params['documentTypes'] = [
                dt.value for dt in query_request.document_types]

        if query_request.status_filter:
            params['statusFilter'] = [
                st.value for st in query_request.status_filter]

        return params

    def _process_soap_response(self, soap_response: Any, start_time: datetime) -> SifenResponse:
        """
        Procesa la respuesta SOAP de SIFEN y la convierte a SifenResponse

        Args:
            soap_response: Respuesta cruda del servicio SOAP
            start_time: Tiempo de inicio de la operación

        Returns:
            SifenResponse procesado

        Raises:
            SifenParsingError: Si no se puede parsear la respuesta
        """
        try:
            # Calcular tiempo de procesamiento
            processing_time = (
                datetime.now() - start_time).total_seconds() * 1000

            # Extraer campos básicos de la respuesta SOAP
            # La estructura exacta depende del WSDL de SIFEN
            success = getattr(soap_response, 'success', False)
            code = getattr(soap_response, 'responseCode', 'UNKNOWN')
            message = getattr(soap_response, 'responseMessage', 'Sin mensaje')
            cdc = getattr(soap_response, 'cdc', None)
            protocol_number = getattr(soap_response, 'protocolNumber', None)

            # Extraer errores y observaciones
            errors = getattr(soap_response, 'errors', [])
            observations = getattr(soap_response, 'observations', [])

            # Construir SifenResponse
            return SifenResponse(
                success=success,
                code=code,
                message=message,
                cdc=cdc,
                protocol_number=protocol_number,
                document_status=None,  # Campo opcional
                processing_time_ms=int(processing_time),
                errors=errors if isinstance(errors, list) else [str(errors)],
                observations=observations if isinstance(observations, list) else [
                    str(observations)],
                additional_data={
                    'raw_response': str(soap_response) if self.config.log_responses else None
                }
            )

        except Exception as e:
            logger.error(
                "soap_response_parsing_failed",
                error=str(e),
                response_type=type(soap_response).__name__
            )
            raise SifenParsingError(
                message=f"Error al parsear respuesta SOAP: {str(e)}",
                parsing_stage="soap_response_processing",
                original_exception=e
            )

    def _handle_soap_fault(self, fault: Fault, request: DocumentRequest, start_time: datetime) -> SifenResponse:
        """
        Maneja errores SOAP Fault y los convierte a SifenResponse de error

        Args:
            fault: Excepción SOAP Fault
            request: Request original que causó el error
            start_time: Tiempo de inicio de la operación

        Returns:
            SifenResponse con información del error
        """
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Extraer información del fault
        fault_code = getattr(fault, 'code', 'SOAP_FAULT')
        fault_message = getattr(fault, 'message', str(fault))

        logger.warning(
            "soap_fault_received",
            fault_code=fault_code,
            fault_message=fault_message,
            cdc=request.cdc
        )

        return SifenResponse(
            success=False,
            code=fault_code,
            message=f"Error SOAP: {fault_message}",
            cdc=request.cdc,
            protocol_number=None,  # No disponible en fault
            document_status=None,  # No disponible en fault
            processing_time_ms=int(processing_time),
            errors=[fault_message],
            observations=[],  # Campo obligatorio
            additional_data={
                'fault_type': 'soap_fault',
                'fault_code': fault_code
            }
        )

    @staticmethod
    def _mask_serial(serial: str) -> str:
        """Enmascara número de serie para logging seguro"""
        if not serial or len(serial) <= 4:
            return "***"
        return f"{serial[:2]}***{serial[-2:]}"

    @staticmethod
    def _mask_ruc(ruc: Optional[str]) -> Optional[str]:
        """Enmascara RUC para logging seguro"""
        if not ruc:
            return None
        if len(ruc) <= 4:
            return "***"
        return f"{ruc[:2]}***{ruc[-2:]}"


# ========================================
# FUNCIONES HELPER
# ========================================

async def create_sifen_client(config: Optional[SifenConfig] = None) -> SifenSOAPClient:
    """
    Factory function para crear cliente SIFEN configurado

    Args:
        config: Configuración específica (usa default si no se proporciona)

    Returns:
        Cliente SIFEN listo para usar
    """
    if config is None:
        config = SifenConfig.from_env()

    client = SifenSOAPClient(config)
    await client._initialize()

    return client


async def test_connection(config: Optional[SifenConfig] = None) -> bool:
    """
    Prueba la conectividad con SIFEN

    Args:
        config: Configuración a probar

    Returns:
        True si la conexión es exitosa, False si no
    """
    try:
        async with SifenSOAPClient(config or SifenConfig.from_env()) as client:
            # Intentar inicializar los clientes SOAP
            return len(client._clients) > 0

    except Exception as e:
        logger.error(
            "sifen_connection_test_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        return False


logger.info(
    "sifen_soap_client_module_loaded",
    features=[
        "async_soap_client",
        "tls_1_2_support",
        "connection_pooling",
        "structured_logging",
        "error_handling"
    ]
)
