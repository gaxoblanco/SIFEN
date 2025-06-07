"""
Parser especializado para respuestas XML de SIFEN Paraguay

Extrae información estructurada de las respuestas XML de SIFEN,
incluyendo códigos de estado, CDCs, errores y datos adicionales.

Funcionalidades:
- Parse de respuestas de envío individual y lotes
- Extracción de CDCs y números de protocolo
- Mapeo de códigos de error SIFEN
- Extracción de observaciones y warnings
- Validación de estructura XML según esquemas

Basado en:
- Manual Técnico SIFEN v150
- Esquemas XSD de respuesta oficiales
- Códigos de error SET Paraguay
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Union, Literal
from datetime import datetime
from decimal import Decimal
import structlog

# Módulos internos
from .models import SifenResponse, BatchResponse, QueryResponse, DocumentStatus, ResponseType
from .exceptions import SifenParsingError, SifenValidationError

# Logger para el parser
logger = structlog.get_logger(__name__)


class SifenResponseParser:
    """
    Parser especializado para respuestas XML de SIFEN

    Maneja el parsing de diferentes tipos de respuestas:
    - Envío individual de documentos
    - Envío de lotes
    - Consultas por CDC/RUC
    - Respuestas de eventos
    """

    def __init__(self):
        """Inicializa el parser con namespaces y configuración"""

        # Namespaces XML de SIFEN v150
        self.namespaces = {
            'sifen': 'http://ekuatia.set.gov.py/sifen/xsd',
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }

        # Mapeo de códigos de estado SIFEN según Manual Técnico v150
        self.status_codes = {
            # Códigos exitosos
            '0260': ('APPROVED', 'Documento aprobado'),
            '1005': ('APPROVED_WITH_OBSERVATIONS', 'Aprobado con observaciones'),

            # Códigos de error comunes (1000-4999)
            '1000': ('REJECTED', 'CDC no corresponde con XML'),
            '1001': ('REJECTED', 'CDC duplicado'),
            '1101': ('REJECTED', 'Número timbrado inválido'),
            '1250': ('REJECTED', 'RUC emisor inexistente'),
            '0141': ('REJECTED', 'Firma digital inválida'),
            '1110': ('REJECTED', 'Timbrado vencido'),
            '1111': ('REJECTED', 'Timbrado inactivo'),
            '1255': ('REJECTED', 'RUC receptor inexistente'),
            '2001': ('REJECTED', 'Error en datos del emisor'),
            '2002': ('REJECTED', 'Error en datos del receptor'),
            '3001': ('REJECTED', 'Error en items del documento'),
            '4001': ('REJECTED', 'Error en totales del documento'),

            # Códigos de error del sistema (5000+)
            '5000': ('TECHNICAL_ERROR', 'Error interno del sistema'),
            '5001': ('TECHNICAL_ERROR', 'Servicio temporalmente no disponible'),
            '5002': ('TECHNICAL_ERROR', 'Error de base de datos'),
            '5003': ('TECHNICAL_ERROR', 'Error de comunicación'),
        }

        logger.info(
            "sifen_response_parser_initialized",
            supported_codes=len(self.status_codes),
            namespaces=list(self.namespaces.keys())
        )

    def parse_response(self, xml_content: str, response_type: ResponseType = ResponseType.INDIVIDUAL) -> SifenResponse:
        """
        Parse principal de respuestas SIFEN

        Args:
            xml_content: Contenido XML de la respuesta
            response_type: Tipo de respuesta esperada

        Returns:
            SifenResponse o subclase apropiada

        Raises:
            SifenParsingError: Si no se puede parsear el XML
        """
        try:
            # Validar que el XML no esté vacío
            if not xml_content or not xml_content.strip():
                raise SifenParsingError(
                    message="Respuesta XML vacía de SIFEN",
                    xml_content="",
                    parsing_stage="initial_validation"
                )

            # Parsear XML
            root = self._parse_xml_safely(xml_content)

            # Log del inicio del parsing
            logger.debug(
                "sifen_response_parsing_start",
                response_type=response_type.value,
                xml_root_tag=root.tag,
                xml_length=len(xml_content)
            )

            # Determinar tipo de respuesta y parsear apropiadamente
            if response_type == ResponseType.BATCH:
                return self._parse_batch_response(root, xml_content)
            elif response_type == ResponseType.QUERY:
                return self._parse_query_response(root, xml_content)
            else:
                return self._parse_individual_response(root, xml_content)

        except ET.ParseError as e:
            raise SifenParsingError(
                message=f"XML malformado en respuesta SIFEN: {str(e)}",
                xml_content=xml_content,
                parsing_stage="xml_parsing",
                original_exception=e
            )
        except Exception as e:
            logger.error(
                "sifen_response_parsing_failed",
                error=str(e),
                error_type=type(e).__name__,
                response_type=response_type.value
            )
            raise SifenParsingError(
                message=f"Error inesperado al parsear respuesta: {str(e)}",
                xml_content=xml_content,
                parsing_stage="general_parsing",
                original_exception=e
            )

    def _parse_xml_safely(self, xml_content: str) -> ET.Element:
        """
        Parsea XML con validaciones de seguridad

        Args:
            xml_content: Contenido XML a parsear

        Returns:
            Elemento raíz del XML

        Raises:
            SifenParsingError: Si el XML es inválido o inseguro
        """
        try:
            # Limpiar contenido XML
            xml_content = xml_content.strip()

            # Validaciones de seguridad básicas
            if '<!DOCTYPE' in xml_content.upper():
                raise SifenParsingError(
                    message="XML contiene DOCTYPE - no permitido por seguridad",
                    xml_content=xml_content,
                    parsing_stage="security_validation"
                )

            if '<!ENTITY' in xml_content.upper():
                raise SifenParsingError(
                    message="XML contiene entidades externas - no permitido por seguridad",
                    xml_content=xml_content,
                    parsing_stage="security_validation"
                )

            # Parsear XML
            root = ET.fromstring(xml_content)

            return root

        except ET.ParseError as e:
            raise SifenParsingError(
                message=f"Error de sintaxis XML: {str(e)}",
                xml_content=xml_content,
                parsing_stage="xml_syntax",
                original_exception=e
            )

    def _parse_individual_response(self, root: ET.Element, xml_content: str) -> SifenResponse:
        """
        Parsea respuesta de envío individual

        Args:
            root: Elemento raíz del XML
            xml_content: Contenido XML completo

        Returns:
            SifenResponse con datos extraídos
        """
        try:
            # Extraer campos básicos
            success = self._extract_success_status(root)
            code = self._extract_response_code(root)
            message = self._extract_response_message(root)

            # Extraer identificadores
            cdc = self._extract_cdc(root)
            protocol_number = self._extract_protocol_number(root)

            # Determinar estado del documento
            document_status = self._determine_document_status(code, success)

            # Extraer errores y observaciones
            errors = self._extract_errors(root)
            observations = self._extract_observations(root)

            # Datos adicionales específicos
            additional_data = self._extract_additional_data(root)

            # Log del resultado
            logger.info(
                "individual_response_parsed",
                success=success,
                code=code,
                cdc=cdc,
                errors_count=len(errors),
                observations_count=len(observations)
            )

            return SifenResponse(
                success=success,
                code=code,
                message=message,
                cdc=cdc,
                protocol_number=protocol_number,
                document_status=document_status,
                timestamp=datetime.now(),
                processing_time_ms=None,  # Se calcula en el cliente
                errors=errors,
                observations=observations,
                additional_data=additional_data,
                response_type=ResponseType.INDIVIDUAL
            )

        except Exception as e:
            raise SifenParsingError(
                message=f"Error al parsear respuesta individual: {str(e)}",
                xml_content=xml_content,
                parsing_stage="individual_response",
                original_exception=e
            )

    def _parse_batch_response(self, root: ET.Element, xml_content: str) -> BatchResponse:
        """
        Parsea respuesta de envío de lote

        Args:
            root: Elemento raíz del XML
            xml_content: Contenido XML completo

        Returns:
            BatchResponse con datos del lote
        """
        try:
            # Extraer datos básicos de la respuesta
            base_response = self._parse_individual_response(root, xml_content)

            # Extraer datos específicos del lote
            batch_id = self._extract_batch_id(root)
            total_documents = self._extract_total_documents(root)
            processed_documents = self._extract_processed_documents(root)
            failed_documents = self._extract_failed_documents(root)

            # Extraer resultados individuales
            document_results = self._extract_document_results(root)

            # Determinar estado del lote
            batch_status = self._determine_batch_status(
                processed_documents, failed_documents, total_documents)

            logger.info(
                "batch_response_parsed",
                batch_id=batch_id,
                total=total_documents,
                processed=processed_documents,
                failed=failed_documents,
                batch_status=batch_status
            )

            return BatchResponse(
                # Campos heredados de SifenResponse
                success=base_response.success,
                code=base_response.code,
                message=base_response.message,
                cdc=base_response.cdc,
                protocol_number=base_response.protocol_number,
                document_status=base_response.document_status,
                timestamp=base_response.timestamp,
                processing_time_ms=base_response.processing_time_ms,
                errors=base_response.errors,
                observations=base_response.observations,
                additional_data=base_response.additional_data,
                response_type=ResponseType.BATCH,

                # Campos específicos del lote
                batch_id=batch_id,
                total_documents=total_documents,
                processed_documents=processed_documents,
                failed_documents=failed_documents,
                document_results=document_results,
                batch_status=batch_status
            )

        except Exception as e:
            raise SifenParsingError(
                message=f"Error al parsear respuesta de lote: {str(e)}",
                xml_content=xml_content,
                parsing_stage="batch_response",
                original_exception=e
            )

    def _parse_query_response(self, root: ET.Element, xml_content: str) -> QueryResponse:
        """
        Parsea respuesta de consulta

        Args:
            root: Elemento raíz del XML
            xml_content: Contenido XML completo

        Returns:
            QueryResponse con resultados de la consulta
        """
        try:
            # Extraer datos básicos de la respuesta
            base_response = self._parse_individual_response(root, xml_content)

            # Extraer datos específicos de la consulta
            query_type = self._extract_query_type(root)
            documents = self._extract_query_documents(root)
            total_found = self._extract_total_found(root)

            # Extraer información de paginación
            page_info = self._extract_page_info(root)

            logger.info(
                "query_response_parsed",
                query_type=query_type,
                total_found=total_found,
                documents_count=len(documents),
                page=page_info.get('page', 1)
            )

            return QueryResponse(
                # Campos heredados de SifenResponse
                success=base_response.success,
                code=base_response.code,
                message=base_response.message,
                cdc=base_response.cdc,
                protocol_number=base_response.protocol_number,
                document_status=base_response.document_status,
                timestamp=base_response.timestamp,
                processing_time_ms=base_response.processing_time_ms,
                errors=base_response.errors,
                observations=base_response.observations,
                additional_data=base_response.additional_data,
                response_type=ResponseType.QUERY,

                # Campos específicos de consulta
                query_type=query_type,
                documents=documents,
                total_found=total_found,
                page=page_info.get('page', 1),
                page_size=page_info.get('page_size', 50),
                total_pages=page_info.get('total_pages', 1),
                has_next_page=page_info.get('has_next_page', False)
            )

        except Exception as e:
            raise SifenParsingError(
                message=f"Error al parsear respuesta de consulta: {str(e)}",
                xml_content=xml_content,
                parsing_stage="query_response",
                original_exception=e
            )

    def _extract_success_status(self, root: ET.Element) -> bool:
        """Extrae el estado de éxito de la respuesta"""
        # Buscar indicadores de éxito en diferentes ubicaciones posibles
        success_indicators = [
            './/sifen:success',
            './/success',
            './/estado',
            './/Status'
        ]

        for indicator in success_indicators:
            element = root.find(indicator, self.namespaces)
            if element is not None:
                text = element.text.lower() if element.text else ''
                return text in ['true', '1', 'ok', 'success', 'exitoso']

        # Si no se encuentra indicador explícito, inferir desde código
        code = self._extract_response_code(root)
        return code in ['0260', '1005'] if code else False

    def _extract_response_code(self, root: ET.Element) -> str:
        """Extrae el código de respuesta SIFEN"""
        code_selectors = [
            './/sifen:codigo',
            './/sifen:responseCode',
            './/codigo',
            './/responseCode',
            './/Code',
            './/dCodRes'
        ]

        for selector in code_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                return element.text.strip()

        return 'UNKNOWN'

    def _extract_response_message(self, root: ET.Element) -> str:
        """Extrae el mensaje de respuesta SIFEN"""
        message_selectors = [
            './/sifen:mensaje',
            './/sifen:responseMessage',
            './/mensaje',
            './/responseMessage',
            './/Message',
            './/dMsgRes'
        ]

        for selector in message_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                return element.text.strip()

        return 'Sin mensaje disponible'

    def _extract_cdc(self, root: ET.Element) -> Optional[str]:
        """Extrae el CDC de la respuesta"""
        cdc_selectors = [
            './/sifen:cdc',
            './/cdc',
            './/CDC',
            './/Id',
            './/dId'
        ]

        for selector in cdc_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                cdc = element.text.strip()
                # Validar que sea un CDC válido (44 dígitos)
                if re.match(r'^\d{44}$', cdc):
                    return cdc

        return None

    def _extract_protocol_number(self, root: ET.Element) -> Optional[str]:
        """Extrae el número de protocolo SIFEN"""
        protocol_selectors = [
            './/sifen:protocolo',
            './/sifen:protocolNumber',
            './/protocolo',
            './/protocolNumber',
            './/Protocol',
            './/dProtAut'
        ]

        for selector in protocol_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                return element.text.strip()

        return None

    def _extract_errors(self, root: ET.Element) -> List[str]:
        """Extrae lista de errores de la respuesta"""
        errors = []

        error_selectors = [
            './/sifen:error',
            './/sifen:errores//error',
            './/error',
            './/errores//error',
            './/Error',
            './/dMsgError'
        ]

        for selector in error_selectors:
            elements = root.findall(selector, self.namespaces)
            for element in elements:
                if element.text:
                    errors.append(element.text.strip())

        return errors

    def _extract_observations(self, root: ET.Element) -> List[str]:
        """Extrae lista de observaciones de la respuesta"""
        observations = []

        obs_selectors = [
            './/sifen:observacion',
            './/sifen:observaciones//observacion',
            './/observacion',
            './/observaciones//observacion',
            './/Observation',
            './/dMsgObs'
        ]

        for selector in obs_selectors:
            elements = root.findall(selector, self.namespaces)
            for element in elements:
                if element.text:
                    observations.append(element.text.strip())

        return observations

    def _extract_additional_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extrae datos adicionales de la respuesta"""
        additional_data = {}

        # Extraer timestamp si está disponible
        timestamp_element = root.find('.//sifen:timestamp', self.namespaces)
        if timestamp_element is not None and timestamp_element.text:
            additional_data['timestamp'] = timestamp_element.text

        # Extraer información del emisor/receptor si está disponible
        emisor_element = root.find('.//sifen:emisor', self.namespaces)
        if emisor_element is not None:
            additional_data['emisor_info'] = self._extract_contribuyente_info(
                emisor_element)

        return additional_data

    def _extract_contribuyente_info(self, element: ET.Element) -> Dict[str, str]:
        """Extrae información de contribuyente (emisor/receptor)"""
        info = {}

        # Campos comunes de contribuyente
        fields = ['ruc', 'razonSocial', 'direccion', 'telefono', 'email']

        for field in fields:
            field_element = element.find(f'.//sifen:{field}', self.namespaces)
            if field_element is not None and field_element.text:
                info[field] = field_element.text.strip()

        return info

    def _determine_document_status(self, code: str, success: bool) -> Optional[DocumentStatus]:
        """Determina el estado del documento según el código"""
        if not code:
            return None

        status_info = self.status_codes.get(code)
        if status_info:
            status_key = status_info[0]
            return DocumentStatus(status_key)

        # Determinar por rangos de código
        if success:
            return DocumentStatus.APROBADO
        elif code.startswith(('1', '2', '3', '4')):
            return DocumentStatus.RECHAZADO
        elif code.startswith('5'):
            return DocumentStatus.ERROR_TECNICO
        else:
            return DocumentStatus.RECHAZADO

    def _extract_batch_id(self, root: ET.Element) -> str:
        """Extrae ID del lote"""
        batch_element = root.find('.//sifen:batchId', self.namespaces)
        if batch_element is not None and batch_element.text:
            return batch_element.text.strip()
        return "UNKNOWN_BATCH"

    def _extract_total_documents(self, root: ET.Element) -> int:
        """Extrae total de documentos en el lote"""
        total_element = root.find('.//sifen:totalDocuments', self.namespaces)
        if total_element is not None and total_element.text:
            try:
                return int(total_element.text)
            except ValueError:
                pass
        return 0

    def _extract_processed_documents(self, root: ET.Element) -> int:
        """Extrae número de documentos procesados exitosamente"""
        processed_element = root.find(
            './/sifen:processedDocuments', self.namespaces)
        if processed_element is not None and processed_element.text:
            try:
                return int(processed_element.text)
            except ValueError:
                pass
        return 0

    def _extract_failed_documents(self, root: ET.Element) -> int:
        """Extrae número de documentos fallidos"""
        failed_element = root.find('.//sifen:failedDocuments', self.namespaces)
        if failed_element is not None and failed_element.text:
            try:
                return int(failed_element.text)
            except ValueError:
                pass
        return 0

    def _extract_document_results(self, root: ET.Element) -> List[SifenResponse]:
        """Extrae resultados individuales de documentos en el lote"""
        results = []

        # Buscar elementos de resultados individuales
        result_elements = root.findall(
            './/sifen:documentResult', self.namespaces)

        for result_element in result_elements:
            try:
                # Parsear cada resultado como respuesta individual
                result_xml = ET.tostring(result_element, encoding='unicode')
                individual_result = self._parse_individual_response(
                    result_element, result_xml)
                results.append(individual_result)
            except Exception as e:
                logger.warning(
                    "failed_to_parse_individual_result",
                    error=str(e)
                )
                # Continuar con otros resultados
                continue

        return results

    def _determine_batch_status(self, processed: int, failed: int, total: int) -> Literal["pending", "processing", "completed", "failed"]:
        """Determina el estado del lote basado en contadores"""
        if processed + failed == 0:
            return "pending"
        elif processed + failed < total:
            return "processing"
        elif failed == 0:
            return "completed"
        elif processed == 0:
            return "failed"
        else:
            return "completed"  # Parcialmente exitoso se considera completado

    def _extract_query_type(self, root: ET.Element) -> str:
        """Extrae el tipo de consulta realizada"""
        query_element = root.find('.//sifen:queryType', self.namespaces)
        if query_element is not None and query_element.text:
            return query_element.text.strip()
        return "unknown"

    def _extract_query_documents(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extrae documentos encontrados en la consulta"""
        documents = []

        doc_elements = root.findall('.//sifen:document', self.namespaces)

        for doc_element in doc_elements:
            doc_data = {}

            # Extraer campos básicos del documento
            fields = ['cdc', 'tipo', 'fecha', 'emisor',
                      'receptor', 'total', 'estado']

            for field in fields:
                field_element = doc_element.find(
                    f'.//sifen:{field}', self.namespaces)
                if field_element is not None and field_element.text:
                    doc_data[field] = field_element.text.strip()

            if doc_data:  # Solo agregar si tiene datos
                documents.append(doc_data)

        return documents

    def _extract_total_found(self, root: ET.Element) -> int:
        """Extrae total de documentos encontrados en la consulta"""
        total_element = root.find('.//sifen:totalFound', self.namespaces)
        if total_element is not None and total_element.text:
            try:
                return int(total_element.text)
            except ValueError:
                pass
        # Fallback al conteo local
        return len(self._extract_query_documents(root))

    def _extract_page_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extrae información de paginación"""
        page_info = {}

        # Extraer campos de paginación
        page_fields = {
            'page': './/sifen:page',
            'pageSize': './/sifen:pageSize',
            'totalPages': './/sifen:totalPages',
            'hasNextPage': './/sifen:hasNextPage'
        }

        for field, selector in page_fields.items():
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                try:
                    if field in ['page', 'pageSize', 'totalPages']:
                        page_info[field] = int(element.text)
                    elif field == 'hasNextPage':
                        page_info[field] = element.text.lower() in [
                            'true', '1']
                    else:
                        page_info[field] = element.text.strip()
                except ValueError:
                    # Ignorar valores inválidos
                    pass

        return page_info


# ========================================
# FUNCIONES HELPER
# ========================================

def parse_sifen_response(xml_content: str, response_type: ResponseType = ResponseType.INDIVIDUAL) -> SifenResponse:
    """
    Función helper para parsear respuestas SIFEN

    Args:
        xml_content: Contenido XML de la respuesta
        response_type: Tipo de respuesta esperada

    Returns:
        SifenResponse o subclase apropiada
    """
    parser = SifenResponseParser()
    return parser.parse_response(xml_content, response_type)


def extract_cdc_from_response(xml_content: str) -> Optional[str]:
    """
    Extrae únicamente el CDC de una respuesta SIFEN

    Args:
        xml_content: Contenido XML de la respuesta

    Returns:
        CDC extraído o None si no se encuentra
    """
    try:
        parser = SifenResponseParser()
        root = parser._parse_xml_safely(xml_content)
        return parser._extract_cdc(root)
    except Exception:
        return None


def extract_response_code(xml_content: str) -> Optional[str]:
    """
    Extrae únicamente el código de respuesta de SIFEN

    Args:
        xml_content: Contenido XML de la respuesta

    Returns:
        Código de respuesta o None si no se encuentra
    """
    try:
        parser = SifenResponseParser()
        root = parser._parse_xml_safely(xml_content)
        return parser._extract_response_code(root)
    except Exception:
        return None


def is_success_response(xml_content: str) -> bool:
    """
    Determina rápidamente si una respuesta es exitosa

    Args:
        xml_content: Contenido XML de la respuesta

    Returns:
        True si la respuesta indica éxito, False si no
    """
    try:
        parser = SifenResponseParser()
        root = parser._parse_xml_safely(xml_content)
        return parser._extract_success_status(root)
    except Exception:
        return False


logger.info(
    "sifen_response_parser_module_loaded",
    features=[
        "individual_response_parsing",
        "batch_response_parsing",
        "query_response_parsing",
        "error_extraction",
        "security_validation",
        "helper_functions"
    ]
)
