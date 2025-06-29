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
import logging

# Módulos internos
from .models import SifenResponse, BatchResponse, QueryResponse, DocumentStatus, ResponseType
from .exceptions import SifenParsingError, SifenValidationError

# Logger para el parser
logger = logging.getLogger(__name__)


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

        # CORRECCIÓN: Mapeo actualizado con enums correctos según DocumentStatus
        self.status_codes = {
            # Códigos exitosos
            '0260': (DocumentStatus.APROBADO, 'Documento aprobado'),
            '1005': (DocumentStatus.APROBADO_OBSERVACION, 'Aprobado con observaciones'),

            # Códigos de error comunes (1000-4999)
            '1000': (DocumentStatus.RECHAZADO, 'CDC no corresponde con XML'),
            '1001': (DocumentStatus.RECHAZADO, 'CDC duplicado'),
            '1101': (DocumentStatus.RECHAZADO, 'Número timbrado inválido'),
            '1250': (DocumentStatus.RECHAZADO, 'RUC emisor inexistente'),
            '0141': (DocumentStatus.RECHAZADO, 'Firma digital inválida'),
            '1110': (DocumentStatus.RECHAZADO, 'Timbrado vencido'),
            '1111': (DocumentStatus.RECHAZADO, 'Timbrado inactivo'),
            '1255': (DocumentStatus.RECHAZADO, 'RUC receptor inexistente'),
            '2001': (DocumentStatus.RECHAZADO, 'Error en datos del emisor'),
            '2002': (DocumentStatus.RECHAZADO, 'Error en datos del receptor'),
            '3001': (DocumentStatus.RECHAZADO, 'Error en items del documento'),
            '4001': (DocumentStatus.RECHAZADO, 'Error en totales del documento'),

            # Códigos de error del sistema (5000+)
            '5000': (DocumentStatus.ERROR_TECNICO, 'Error interno del sistema'),
            '5001': (DocumentStatus.ERROR_TECNICO, 'Servicio temporalmente no disponible'),
            '5002': (DocumentStatus.ERROR_TECNICO, 'Error de base de datos'),
            '5003': (DocumentStatus.ERROR_TECNICO, 'Error de comunicación'),

            # Códigos de estados especiales (según esquemas XSD encontrados)
            '0200': (DocumentStatus.PENDIENTE, 'Documento en cola de procesamiento'),
            '0201': (DocumentStatus.PROCESANDO, 'Documento siendo procesado'),
        }

        logger.info(
            "SIFEN Response Parser initialized - supported_codes=%d, namespaces=%s",
            len(self.status_codes),
            list(self.namespaces.keys())
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

            # Parsear XML con validaciones de seguridad
            root = self._parse_xml_safely(xml_content)

            # Log del inicio del parsing
            logger.debug(
                "SIFEN response parsing start - type=%s, root_tag=%s, xml_length=%d",
                response_type.value,
                root.tag,
                len(xml_content)
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
        except SifenParsingError:
            raise  # Re-raise custom parsing errors
        except Exception as e:
            logger.error(
                "SIFEN response parsing failed - error=%s, type=%s, response_type=%s",
                str(e),
                type(e).__name__,
                response_type.value
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

            # NUEVO: Validar que tenga los namespaces mínimos requeridos
            self._validate_xml_namespaces(root)

            return root

        except ET.ParseError as e:
            raise SifenParsingError(
                message=f"XML malformado - Error de sintaxis: {str(e)}",
                xml_content=xml_content,
                parsing_stage="xml_parsing",
                original_exception=e
            )

    def _validate_xml_namespaces(self, root: ET.Element) -> None:
        """
        NUEVO: Valida que el XML tenga los namespaces SIFEN requeridos

        Args:
            root: Elemento raíz del XML

        Raises:
            SifenParsingError: Si faltan namespaces críticos
        """
        # Obtener todos los namespaces del elemento raíz
        root_nsmap = getattr(root, 'nsmap', {}) if hasattr(
            root, 'nsmap') else {}
        root_tag = root.tag

        # Verificar que contenga elementos SIFEN
        has_sifen_content = (
            'sifen' in str(root_tag).lower() or
            'ekuatia' in str(root_tag).lower() or
            any('sifen' in str(child.tag).lower() for child in root) or
            any('ekuatia' in str(child.tag).lower() for child in root)
        )

        if not has_sifen_content:
            logger.warning(
                "XML namespace validation warning - root_tag=%s, namespaces=%s - XML does not seem to contain standard SIFEN elements",
                root_tag,
                root_nsmap
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

            # CORRECCIÓN: Determinar estado usando enums correctos
            document_status = self._determine_document_status(code, success)

            # Extraer errores y observaciones con contexto mejorado
            errors = self._extract_errors_with_context(root)
            observations = self._extract_observations(root)

            # Datos adicionales específicos
            additional_data = self._extract_additional_data(root)

            # Log del resultado
            logger.info(
                "Individual response parsed - success=%s, code=%s, cdc=%s, status=%s, errors=%d, observations=%d",
                success,
                code,
                cdc,
                document_status.value if document_status else None,
                len(errors),
                len(observations)
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
                "Batch response parsed - batch_id=%s, total=%d, processed=%d, failed=%d, status=%s",
                batch_id,
                total_documents,
                processed_documents,
                failed_documents,
                batch_status
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
                "Query response parsed - type=%s, total_found=%d, documents=%d, page=%d",
                query_type,
                total_found,
                len(documents),
                page_info.get('page', 1)
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

    def _extract_errors_with_context(self, root: ET.Element) -> List[str]:
        """
        MEJORADO: Extrae lista de errores con información de contexto
        """
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
                    error_text = element.text.strip()

                    # Extraer código de error si está disponible
                    error_code = element.get('codigo', element.get('code', ''))
                    error_field = element.get(
                        'campo', element.get('field', ''))

                    # Crear mensaje de error contextualizado
                    if error_code and error_field:
                        formatted_error = f"[{error_code}] {error_text} (Campo: {error_field})"
                    elif error_code:
                        formatted_error = f"[{error_code}] {error_text}"
                    else:
                        formatted_error = error_text

                    errors.append(formatted_error)

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
        """
        CORRECCIÓN: Determina el estado del documento usando enums correctos
        """
        if not code:
            return None

        status_info = self.status_codes.get(code)
        if status_info:
            # Retorna el enum DocumentStatus directamente
            return status_info[0]

        # Determinar por rangos de código si no está en el mapeo
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
        batch_selectors = [
            './/sifen:batchId',
            './/batchId',
            './/loteId',
            './/idLote'
        ]

        for selector in batch_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                return element.text.strip()

        return "UNKNOWN_BATCH"

    def _extract_total_documents(self, root: ET.Element) -> int:
        """Extrae total de documentos en el lote"""
        total_selectors = [
            './/sifen:totalDocuments',
            './/totalDocuments',
            './/totalDocs',
            './/cantidadTotal'
        ]

        for selector in total_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                try:
                    return int(element.text)
                except ValueError:
                    continue

        return 0

    def _extract_processed_documents(self, root: ET.Element) -> int:
        """Extrae número de documentos procesados exitosamente"""
        processed_selectors = [
            './/sifen:processedDocuments',
            './/processedDocuments',
            './/docsExitosos',
            './/cantidadProcesados'
        ]

        for selector in processed_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                try:
                    return int(element.text)
                except ValueError:
                    continue

        return 0

    def _extract_failed_documents(self, root: ET.Element) -> int:
        """Extrae número de documentos fallidos"""
        failed_selectors = [
            './/sifen:failedDocuments',
            './/failedDocuments',
            './/docsFallidos',
            './/cantidadFallidos'
        ]

        for selector in failed_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                try:
                    return int(element.text)
                except ValueError:
                    continue

        return 0

    def _extract_document_results(self, root: ET.Element) -> List[SifenResponse]:
        """Extrae resultados individuales de documentos en el lote"""
        results = []

        # Buscar elementos de resultados individuales
        result_elements = root.findall(
            './/sifen:documentResult | .//documentResult | .//resultado',
            self.namespaces
        )

        for result_element in result_elements:
            try:
                # Parsear cada resultado como respuesta individual
                result_xml = ET.tostring(result_element, encoding='unicode')
                individual_result = self._parse_individual_response(
                    result_element, result_xml)
                results.append(individual_result)
            except Exception as e:
                logger.warning(
                    "Failed to parse individual result - error=%s, element_tag=%s",
                    str(e),
                    result_element.tag
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
        query_selectors = [
            './/sifen:queryType',
            './/queryType',
            './/tipoConsulta',
            './/tipo'
        ]

        for selector in query_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                return element.text.strip()

        return "unknown"

    def _extract_query_documents(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extrae documentos encontrados en la consulta"""
        documents = []

        doc_elements = root.findall(
            './/sifen:document | .//document | .//documento',
            self.namespaces
        )

        for doc_element in doc_elements:
            doc_data = {}

            # Extraer campos básicos del documento
            fields = ['cdc', 'tipo', 'fecha', 'emisor',
                      'receptor', 'total', 'estado']

            for field in fields:
                field_element = doc_element.find(
                    f'.//sifen:{field} | .//{field}', self.namespaces)
                if field_element is not None and field_element.text:
                    doc_data[field] = field_element.text.strip()

            if doc_data:  # Solo agregar si tiene datos
                documents.append(doc_data)

        return documents

    def _extract_total_found(self, root: ET.Element) -> int:
        """Extrae total de documentos encontrados en la consulta"""
        total_selectors = [
            './/sifen:totalFound',
            './/totalFound',
            './/totalEncontrados',
            './/cantidad'
        ]

        for selector in total_selectors:
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                try:
                    return int(element.text)
                except ValueError:
                    continue

        # Fallback al conteo local
        return len(self._extract_query_documents(root))

    def _extract_page_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extrae información de paginación"""
        page_info = {}

        # Extraer campos de paginación
        page_fields = {
            'page': './/sifen:page | .//page | .//pagina',
            'page_size': './/sifen:pageSize | .//pageSize | .//tamanoPagina',
            'total_pages': './/sifen:totalPages | .//totalPages | .//totalPaginas',
            'has_next_page': './/sifen:hasNextPage | .//hasNextPage | .//tieneSiguiente'
        }

        for field, selector in page_fields.items():
            element = root.find(selector, self.namespaces)
            if element is not None and element.text:
                try:
                    if field in ['page', 'page_size', 'total_pages']:
                        page_info[field] = int(element.text)
                    elif field == 'has_next_page':
                        page_info[field] = element.text.lower() in [
                            'true', '1', 'si', 'yes']
                    else:
                        page_info[field] = element.text.strip()
                except ValueError:
                    # Ignorar valores inválidos
                    pass

        # Valores por defecto si no se encontraron
        page_info.setdefault('page', 1)
        page_info.setdefault('page_size', 50)
        page_info.setdefault('total_pages', 1)
        page_info.setdefault('has_next_page', False)

        return page_info


# ========================================
# FUNCIONES HELPER MEJORADAS
# ========================================

def parse_sifen_response(xml_content: str, response_type: ResponseType = ResponseType.INDIVIDUAL) -> SifenResponse:
    """
    Función helper para parsear respuestas SIFEN

    Args:
        xml_content: Contenido XML de la respuesta
        response_type: Tipo de respuesta esperada

    Returns:
        SifenResponse o subclase apropiada

    Raises:
        SifenParsingError: Si el parsing falla
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

    Raises:
        SifenParsingError: Si el XML es inválido
    """
    try:
        parser = SifenResponseParser()
        root = parser._parse_xml_safely(xml_content)
        return parser._extract_cdc(root)
    except Exception as e:
        logger.warning(
            "CDC extraction failed - error=%s, xml_length=%d",
            str(e),
            len(xml_content) if xml_content else 0
        )
        return None


def extract_response_code(xml_content: str) -> Optional[str]:
    """
    Extrae únicamente el código de respuesta de SIFEN

    Args:
        xml_content: Contenido XML de la respuesta

    Returns:
        Código de respuesta o None si no se encuentra

    Raises:
        SifenParsingError: Si el XML es inválido
    """
    try:
        parser = SifenResponseParser()
        root = parser._parse_xml_safely(xml_content)
        return parser._extract_response_code(root)
    except Exception as e:
        logger.warning(
            "Response code extraction failed - error=%s, xml_length=%d",
            str(e),
            len(xml_content) if xml_content else 0
        )
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
    except Exception as e:
        logger.warning(
            "Success status extraction failed - error=%s, xml_length=%d",
            str(e),
            len(xml_content) if xml_content else 0
        )
        return False


def get_document_status_from_code(code: str) -> Optional[DocumentStatus]:
    """
    NUEVA: Obtiene el DocumentStatus basado en código SIFEN

    Args:
        code: Código de respuesta SIFEN

    Returns:
        DocumentStatus correspondiente o None
    """
    parser = SifenResponseParser()
    return parser._determine_document_status(code, code in ['0260', '1005'])


def validate_response_xml_structure(xml_content: str) -> Dict[str, Any]:
    """
    NUEVA: Valida la estructura del XML de respuesta sin parsearlo completamente

    Args:
        xml_content: Contenido XML a validar

    Returns:
        Dict con información de validación
    """
    validation_result = {
        'is_valid': False,
        'has_sifen_elements': False,
        'has_security_issues': False,
        'estimated_type': None,
        'errors': []
    }

    try:
        if not xml_content or not xml_content.strip():
            validation_result['errors'].append("XML vacío")
            return validation_result

        # Verificar problemas de seguridad
        xml_upper = xml_content.upper()
        if '<!DOCTYPE' in xml_upper or '<!ENTITY' in xml_upper:
            validation_result['has_security_issues'] = True
            validation_result['errors'].append(
                "XML contiene elementos de seguridad no permitidos")

        # Verificar elementos SIFEN
        if 'sifen' in xml_content.lower() or 'ekuatia' in xml_content.lower():
            validation_result['has_sifen_elements'] = True

        # Estimar tipo de respuesta
        if 'batch' in xml_content.lower() or 'lote' in xml_content.lower():
            validation_result['estimated_type'] = ResponseType.BATCH
        elif 'query' in xml_content.lower() or 'consulta' in xml_content.lower():
            validation_result['estimated_type'] = ResponseType.QUERY
        else:
            validation_result['estimated_type'] = ResponseType.INDIVIDUAL

        # Intentar parsing básico
        ET.fromstring(xml_content)
        validation_result['is_valid'] = True

    except ET.ParseError as e:
        validation_result['errors'].append(f"Error de sintaxis XML: {str(e)}")
    except Exception as e:
        validation_result['errors'].append(f"Error inesperado: {str(e)}")

    return validation_result


# Log de inicialización del módulo
logger.info(
    "SIFEN Response Parser module loaded - version=1.5.0, features=%s, status_codes=%d",
    [
        "individual_response_parsing",
        "batch_response_parsing",
        "query_response_parsing",
        "enhanced_error_extraction",
        "security_validation",
        "helper_functions",
        "document_status_enum_support",
        "improved_xml_validation"
    ],
    len(SifenResponseParser().status_codes)
)
