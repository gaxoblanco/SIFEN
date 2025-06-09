"""
Orquestador principal para envío de documentos a SIFEN Paraguay

Combina todos los componentes del módulo sifen_client para proporcionar
una API simple y robusta para el envío de documentos electrónicos.

Funcionalidades:
- Envío individual con validación y reintentos automáticos
- Envío de lotes con procesamiento paralelo y seguimiento
- Validación previa antes del envío
- Logging exhaustivo del proceso completo
- Manejo inteligente de errores con recomendaciones

Componentes integrados:
- SifenSOAPClient: Comunicación de bajo nivel
- SifenResponseParser: Procesamiento de respuestas
- SifenErrorHandler: Manejo de errores user-friendly
- RetryManager: Reintentos automáticos con circuit breaker

Basado en:
- Manual Técnico SIFEN v150
- Patrones de arquitectura para sistemas distribuidos
- Best practices para APIs robustas
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import structlog

# Módulos internos
from .config import SifenConfig
from .models import (
    DocumentRequest,
    BatchRequest,
    QueryRequest,
    SifenResponse,
    BatchResponse,
    QueryResponse,
    ResponseType,
    DocumentStatus,
    create_document_request,
    create_batch_request
)
from .client import SifenSOAPClient
from .response_parser import SifenResponseParser
from .error_handler import SifenErrorHandler, ErrorCategory, ErrorSeverity
from .retry_manager import RetryManager, create_retry_manager_from_config
from .exceptions import (
    SifenClientError,
    SifenValidationError,
    SifenConnectionError,
    SifenRetryExhaustedError,
    create_sifen_error_from_response
)

# Logger para el document sender
logger = structlog.get_logger(__name__)


@dataclass
class SendResult:
    """
    Resultado detallado de envío de documento
    """
    success: bool
    response: SifenResponse
    processing_time_ms: float
    retry_count: int
    enhanced_info: Dict[str, Any]
    validation_warnings: List[str] = field(default_factory=list)


@dataclass
class BatchSendResult:
    """
    Resultado detallado de envío de lote
    """
    success: bool
    batch_response: BatchResponse
    individual_results: List[SendResult]
    total_processing_time_ms: float
    successful_documents: int
    failed_documents: int
    batch_summary: Dict[str, Any]


class DocumentSender:
    """
    Orquestador principal para envío de documentos a SIFEN

    Proporciona una API de alto nivel que combina validación,
    envío, manejo de errores y reintentos automáticos.
    """

    def __init__(
        self,
        config: Optional[SifenConfig] = None,
        soap_client: Optional[SifenSOAPClient] = None,
        response_parser: Optional[SifenResponseParser] = None,
        error_handler: Optional[SifenErrorHandler] = None,
        retry_manager: Optional[RetryManager] = None
    ):
        """
        Inicializa el document sender con configuración y componentes

        Args:
            config: Configuración SIFEN (se crea default si no se proporciona)
            soap_client: Cliente SOAP (se crea automáticamente si no se proporciona)
            response_parser: Parser de respuestas (se crea automáticamente)
            error_handler: Manejador de errores (se crea automáticamente)
            retry_manager: Gestor de reintentos (se crea automáticamente)
        """
        # Configuración base
        self.config = config or SifenConfig.from_env()

        # Componentes (se crean bajo demanda si no se proporcionan)
        self._soap_client = soap_client
        self._response_parser = response_parser or SifenResponseParser()
        self._error_handler = error_handler or SifenErrorHandler()
        self._retry_manager = retry_manager or create_retry_manager_from_config(
            self.config)

        # Estado interno
        self._client_initialized = False
        self._stats = {
            'total_documents_sent': 0,
            'successful_documents': 0,
            'failed_documents': 0,
            'total_retries': 0,
            'avg_processing_time_ms': 0.0
        }

        logger.info(
            "document_sender_initialized",
            environment=self.config.environment,
            base_url=self.config.effective_base_url,
            max_retries=self._retry_manager.max_retries
        )

    async def __aenter__(self):
        """Context manager entry - inicializa cliente SOAP"""
        await self._ensure_client_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - limpia recursos"""
        if self._soap_client:
            await self._soap_client._cleanup()

    async def _ensure_client_initialized(self):
        """Asegura que el cliente SOAP esté inicializado"""
        if not self._client_initialized:
            if self._soap_client is None:
                self._soap_client = SifenSOAPClient(self.config)

            await self._soap_client._initialize()
            self._client_initialized = True

            logger.debug("soap_client_initialized_by_sender")

    async def send_document(
        self,
        xml_content: str,
        certificate_serial: str,
        validate_before_send: bool = True,
        operation_name: str = "send_document"
    ) -> SendResult:
        """
        Envía un documento individual a SIFEN con validación y reintentos

        Args:
            xml_content: Contenido XML del documento firmado
            certificate_serial: Número de serie del certificado digital
            validate_before_send: Realizar validación previa
            operation_name: Nombre de la operación para logging

        Returns:
            SendResult con información detallada del envío

        Raises:
            SifenValidationError: Si la validación previa falla
            SifenRetryExhaustedError: Si se agotan los reintentos
            SifenClientError: Para otros errores
        """
        start_time = datetime.now()
        validation_warnings: List[str] = []

        try:
            # Asegurar cliente inicializado
            await self._ensure_client_initialized()

            # Validación previa (opcional pero recomendada)
            if validate_before_send:
                validation_warnings = await self._validate_document_before_send(
                    xml_content, certificate_serial
                )

            # Crear request del documento
            document_request = create_document_request(
                xml_content=xml_content,
                certificate_serial=certificate_serial,
                metadata={
                    'sender_operation': operation_name,
                    'validation_warnings_count': len(validation_warnings),
                    'send_timestamp': start_time.isoformat()
                }
            )

            # Log del inicio del envío
            logger.info(
                "document_send_start",
                operation=operation_name,
                cdc=document_request.cdc,
                doc_type=document_request.document_type,
                cert_serial=self._mask_serial(certificate_serial),
                validation_warnings=len(validation_warnings)
            )

            # Verificar que el cliente SOAP esté disponible
            if self._soap_client is None:
                raise SifenClientError("Cliente SOAP no inicializado")

            # Envío con reintentos automáticos
            response = await self._retry_manager.execute_with_retry(
                self._soap_client.send_document,
                document_request,
                operation_name=operation_name
            )

            # Procesar y enriquecer la respuesta
            enhanced_info = self._error_handler.create_enhanced_response(
                response)

            # Calcular métricas
            processing_time = (
                datetime.now() - start_time).total_seconds() * 1000
            retry_count = await self._get_retry_count_from_stats()

            # Actualizar estadísticas
            self._update_stats(True, processing_time, retry_count)

            # Crear resultado
            result = SendResult(
                success=response.success,
                response=response,
                processing_time_ms=processing_time,
                retry_count=retry_count,
                enhanced_info=enhanced_info,
                validation_warnings=validation_warnings
            )

            # Log del resultado
            logger.info(
                "document_send_completed",
                operation=operation_name,
                success=response.success,
                sifen_code=response.code,
                cdc=response.cdc,
                processing_time_ms=processing_time,
                retry_count=retry_count
            )

            return result

        except Exception as e:
            # Calcular tiempo incluso en error
            processing_time = (
                datetime.now() - start_time).total_seconds() * 1000
            retry_count = await self._get_retry_count_from_stats()

            # Actualizar estadísticas de error
            self._update_stats(False, processing_time, retry_count)

            # Log del error
            logger.error(
                "document_send_failed",
                operation=operation_name,
                error=str(e),
                error_type=type(e).__name__,
                processing_time_ms=processing_time,
                retry_count=retry_count
            )

            # Re-lanzar la excepción
            raise

    async def send_batch(
        self,
        # [(xml_content, certificate_serial), ...]
        documents: List[Tuple[str, str]],
        batch_id: str,
        validate_before_send: bool = True,
        max_concurrent: int = 5,
        operation_name: str = "send_batch"
    ) -> BatchSendResult:
        """
        Envía un lote de documentos a SIFEN con procesamiento paralelo

        Args:
            documents: Lista de tuplas (xml_content, certificate_serial)
            batch_id: Identificador único del lote
            validate_before_send: Realizar validación previa
            max_concurrent: Máximo número de envíos concurrentes
            operation_name: Nombre de la operación para logging

        Returns:
            BatchSendResult con información detallada del lote

        Raises:
            SifenValidationError: Si hay errores de validación críticos
            SifenClientError: Para otros errores del lote
        """
        start_time = datetime.now()

        try:
            # Validar parámetros del lote
            if not documents:
                raise SifenValidationError("El lote no puede estar vacío")

            if len(documents) > 50:
                raise SifenValidationError(
                    "El lote no puede tener más de 50 documentos")

            # Asegurar cliente inicializado
            await self._ensure_client_initialized()

            # Log del inicio del lote
            logger.info(
                "batch_send_start",
                operation=operation_name,
                batch_id=batch_id,
                documents_count=len(documents),
                max_concurrent=max_concurrent
            )

            # Procesar documentos con concurrencia limitada
            semaphore = asyncio.Semaphore(max_concurrent)
            individual_results = []

            async def send_single_document(index: int, xml_content: str, cert_serial: str) -> SendResult:
                async with semaphore:
                    try:
                        return await self.send_document(
                            xml_content=xml_content,
                            certificate_serial=cert_serial,
                            validate_before_send=validate_before_send,
                            operation_name=f"{operation_name}_doc_{index+1}"
                        )
                    except Exception as e:
                        # Crear resultado de error para mantener consistencia
                        error_response = SifenResponse(
                            success=False,
                            code="CLIENT_ERROR",
                            message=str(e),
                            cdc=None,
                            protocol_number=None,
                            document_status=DocumentStatus.ERROR_TECNICO,
                            timestamp=datetime.now(),
                            processing_time_ms=0,
                            errors=[str(e)],
                            observations=[],
                            additional_data={'batch_index': index}
                        )

                        return SendResult(
                            success=False,
                            response=error_response,
                            processing_time_ms=0,
                            retry_count=0,
                            enhanced_info=self._error_handler.create_enhanced_response(
                                error_response),
                            validation_warnings=[]
                        )

            # Ejecutar envíos en paralelo
            tasks = [
                send_single_document(i, xml_content, cert_serial)
                for i, (xml_content, cert_serial) in enumerate(documents)
            ]

            individual_results = await asyncio.gather(*tasks, return_exceptions=False)

            # Analizar resultados
            successful_count = sum(
                1 for result in individual_results if result.success)
            failed_count = len(individual_results) - successful_count

            # Calcular métricas del lote
            total_processing_time = (
                datetime.now() - start_time).total_seconds() * 1000

            # Crear respuesta de lote sintética
            batch_response = self._create_batch_response(
                batch_id=batch_id,
                total_documents=len(documents),
                successful_documents=successful_count,
                failed_documents=failed_count,
                individual_results=individual_results
            )

            # Crear resultado del lote
            result = BatchSendResult(
                success=failed_count == 0,  # Éxito solo si todos los documentos fueron exitosos
                batch_response=batch_response,
                individual_results=individual_results,
                total_processing_time_ms=total_processing_time,
                successful_documents=successful_count,
                failed_documents=failed_count,
                batch_summary={
                    'batch_id': batch_id,
                    'success_rate': (successful_count / len(documents)) * 100,
                    'avg_processing_time_ms': sum(r.processing_time_ms for r in individual_results) / len(individual_results),
                    'total_retries': sum(r.retry_count for r in individual_results),
                    'validation_warnings_total': sum(len(r.validation_warnings) for r in individual_results)
                }
            )

            # Log del resultado del lote
            logger.info(
                "batch_send_completed",
                operation=operation_name,
                batch_id=batch_id,
                total_documents=len(documents),
                successful=successful_count,
                failed=failed_count,
                success_rate=result.batch_summary['success_rate'],
                total_processing_time_ms=total_processing_time
            )

            return result

        except Exception as e:
            processing_time = (
                datetime.now() - start_time).total_seconds() * 1000

            logger.error(
                "batch_send_failed",
                operation=operation_name,
                batch_id=batch_id,
                error=str(e),
                error_type=type(e).__name__,
                processing_time_ms=processing_time
            )

            raise

    async def query_document(
        self,
        query_request: QueryRequest,
        operation_name: str = "query_document"
    ) -> QueryResponse:
        """
        Consulta información de documentos en SIFEN

        Args:
            query_request: Parámetros de consulta
            operation_name: Nombre de la operación para logging

        Returns:
            QueryResponse con resultados de la consulta

        Raises:
            SifenClientError: En caso de error en la consulta
        """
        try:
            # Asegurar cliente inicializado
            await self._ensure_client_initialized()

            # Log del inicio de consulta
            logger.info(
                "document_query_start",
                operation=operation_name,
                query_type=query_request.query_type,
                cdc=query_request.cdc,
                ruc=self._mask_ruc(
                    query_request.ruc) if query_request.ruc else None
            )

            # Verificar que el cliente SOAP esté disponible
            if self._soap_client is None:
                raise SifenClientError("Cliente SOAP no inicializado")

            # Ejecutar consulta con reintentos
            response = await self._retry_manager.execute_with_retry(
                self._soap_client.query_document,
                query_request,
                operation_name=operation_name
            )

            # Si la respuesta no es QueryResponse, convertirla
            if not isinstance(response, QueryResponse):
                # Crear QueryResponse desde SifenResponse básico
                query_response = QueryResponse(
                    success=response.success,
                    code=response.code,
                    message=response.message,
                    cdc=response.cdc,
                    protocol_number=response.protocol_number,
                    document_status=response.document_status,
                    timestamp=response.timestamp,
                    processing_time_ms=response.processing_time_ms,
                    errors=response.errors,
                    observations=response.observations,
                    additional_data=response.additional_data,
                    response_type=ResponseType.QUERY,
                    query_type=query_request.query_type,
                    documents=response.additional_data.get('documents', []),
                    total_found=response.additional_data.get('total_found', 0),
                    page=query_request.page,
                    page_size=query_request.page_size,
                    total_pages=response.additional_data.get('total_pages', 1),
                    has_next_page=response.additional_data.get(
                        'has_next_page', False)
                )
                response = query_response

            # Log del resultado
            logger.info(
                "document_query_completed",
                operation=operation_name,
                success=response.success,
                query_type=response.query_type,
                total_found=response.total_found,
                documents_returned=len(response.documents)
            )

            return response

        except Exception as e:
            logger.error(
                "document_query_failed",
                operation=operation_name,
                query_type=query_request.query_type,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def _validate_document_before_send(
        self,
        xml_content: str,
        certificate_serial: str
    ) -> List[str]:
        """
        Realiza validaciones previas antes del envío

        Args:
            xml_content: Contenido XML del documento
            certificate_serial: Número de serie del certificado

        Returns:
            Lista de warnings de validación

        Raises:
            SifenValidationError: Si hay errores críticos de validación
        """
        warnings: List[str] = []

        try:
            # Validación básica de XML
            if not xml_content or not xml_content.strip():
                raise SifenValidationError("XML no puede estar vacío")

            if len(xml_content) > 10_000_000:  # 10MB
                raise SifenValidationError(
                    "XML excede el tamaño máximo permitido (10MB)")

            # Validación de estructura XML básica
            if not xml_content.strip().startswith('<?xml'):
                warnings.append("XML no inicia con declaración XML estándar")

            if 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' not in xml_content:
                raise SifenValidationError(
                    "XML no contiene namespace SIFEN requerido")

            # Validación de certificado
            if not certificate_serial or len(certificate_serial) < 8:
                raise SifenValidationError(
                    "Número de serie del certificado inválido")

            # Validaciones de contenido específico SIFEN
            required_elements = ['<rDE', '<DE', '<gDE>']
            missing_elements = [
                elem for elem in required_elements if elem not in xml_content]

            if missing_elements:
                raise SifenValidationError(
                    f"Faltan elementos requeridos: {missing_elements}")

            # Warnings no críticos
            if '<dTotGralOpe>0</dTotGralOpe>' in xml_content:
                warnings.append("Documento con total general igual a cero")

            if len(xml_content) > 1_000_000:  # 1MB
                warnings.append(
                    "Documento de gran tamaño puede afectar performance")

            logger.debug(
                "document_validation_completed",
                warnings_count=len(warnings),
                xml_size_bytes=len(xml_content.encode('utf-8'))
            )

            return warnings

        except SifenValidationError:
            # Re-lanzar errores de validación críticos
            raise
        except Exception as e:
            # Convertir otros errores a errores de validación
            raise SifenValidationError(
                message=f"Error en validación previa: {str(e)}",
                original_exception=e
            )

    def _create_batch_response(
        self,
        batch_id: str,
        total_documents: int,
        successful_documents: int,
        failed_documents: int,
        individual_results: List[SendResult]
    ) -> BatchResponse:
        """Crea una respuesta de lote sintética"""

        # Determinar estado general del lote
        if failed_documents == 0:
            batch_success = True
            batch_code = "0260"
            batch_message = f"Lote procesado exitosamente: {successful_documents}/{total_documents} documentos"
        elif successful_documents == 0:
            batch_success = False
            batch_code = "5000"
            batch_message = f"Lote falló completamente: {failed_documents}/{total_documents} documentos fallaron"
        else:
            batch_success = False  # Parcialmente exitoso se considera fallo
            batch_code = "1005"
            batch_message = f"Lote parcialmente exitoso: {successful_documents}/{total_documents} documentos exitosos"

        # Determinar estado del lote
        if successful_documents == total_documents:
            batch_status = "completed"
        elif successful_documents == 0:
            batch_status = "failed"
        else:
            batch_status = "completed"  # Parcialmente exitoso

        # Extraer respuestas individuales
        document_results = [result.response for result in individual_results]

        return BatchResponse(
            success=batch_success,
            code=batch_code,
            message=batch_message,
            cdc=None,  # Los lotes no tienen CDC único
            protocol_number=None,
            document_status=None,
            timestamp=datetime.now(),
            processing_time_ms=int(
                sum(r.processing_time_ms for r in individual_results)),
            errors=[],
            observations=[],
            additional_data={
                'individual_processing_times': [r.processing_time_ms for r in individual_results],
                'total_validation_warnings': sum(len(r.validation_warnings) for r in individual_results)
            },
            response_type=ResponseType.BATCH,
            batch_id=batch_id,
            total_documents=total_documents,
            processed_documents=successful_documents + failed_documents,
            failed_documents=failed_documents,
            document_results=document_results,
            batch_status=batch_status
        )

    async def _get_retry_count_from_stats(self) -> int:
        """Obtiene el conteo de reintentos desde las estadísticas del retry manager"""
        try:
            retry_stats = self._retry_manager.get_stats()
            return retry_stats.get('total_retries', 0)
        except Exception as e:
            # Fallback robusto si no se pueden obtener estadísticas
            logger.warning(
                f"No se pudieron obtener estadísticas de reintentos: {e}")
            return 0

    def _update_stats(self, success: bool, processing_time_ms: float, retry_count: int):
        """Actualiza las estadísticas del document sender"""
        self._stats['total_documents_sent'] += 1

        if success:
            self._stats['successful_documents'] += 1
        else:
            self._stats['failed_documents'] += 1

        self._stats['total_retries'] += retry_count

        # Calcular promedio de tiempo de procesamiento
        total_docs = self._stats['total_documents_sent']
        current_avg = self._stats['avg_processing_time_ms']
        self._stats['avg_processing_time_ms'] = (
            (current_avg * (total_docs - 1) + processing_time_ms) / total_docs
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

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas completas del document sender

        Returns:
            Diccionario con estadísticas detalladas
        """
        try:
            retry_stats = self._retry_manager.get_stats()
        except Exception as e:
            logger.warning(
                f"Error obteniendo estadísticas de retry manager: {e}")
            retry_stats = {'error': 'stats_unavailable'}

        return {
            'document_sender': self._stats.copy(),
            'retry_manager': retry_stats,
            'configuration': {
                'environment': self.config.environment,
                'base_url': self.config.effective_base_url,
                'max_retries': self._retry_manager.max_retries,
                'timeout': self.config.timeout
            }
        }

    async def reset_stats(self):
        """Resetea todas las estadísticas"""
        self._stats = {
            'total_documents_sent': 0,
            'successful_documents': 0,
            'failed_documents': 0,
            'total_retries': 0,
            'avg_processing_time_ms': 0.0
        }

        try:
            self._retry_manager.reset_stats()
        except Exception as e:
            logger.warning(
                f"Error reseteando estadísticas de retry manager: {e}")

        logger.info("document_sender_stats_reset")


# ========================================
# FUNCIONES HELPER
# ========================================

async def send_document_to_sifen(
    xml_content: str,
    certificate_serial: str,
    config: Optional[SifenConfig] = None
) -> SendResult:
    """
    Función helper para envío simple de documento

    Args:
        xml_content: Contenido XML del documento
        certificate_serial: Número de serie del certificado
        config: Configuración SIFEN (opcional)

    Returns:
        SendResult con información del envío
    """
    async with DocumentSender(config) as sender:
        return await sender.send_document(xml_content, certificate_serial)


async def send_batch_to_sifen(
    documents: List[Tuple[str, str]],
    batch_id: str,
    config: Optional[SifenConfig] = None
) -> BatchSendResult:
    """
    Función helper para envío simple de lote

    Args:
        documents: Lista de tuplas (xml_content, certificate_serial)
        batch_id: ID del lote
        config: Configuración SIFEN (opcional)

    Returns:
        BatchSendResult con información del lote
    """
    async with DocumentSender(config) as sender:
        return await sender.send_batch(documents, batch_id)


logger.info(
    "document_sender_module_loaded",
    features=[
        "individual_document_sending",
        "batch_processing",
        "parallel_execution",
        "validation_integration",
        "retry_integration",
        "enhanced_error_handling",
        "comprehensive_statistics"
    ]
)
