"""
Validador principal contra esquemas XSD SIFEN v150

Este módulo proporciona validación autoritativa contra los esquemas XSD
oficiales de SIFEN v150. Es la validación final y más completa que se
realiza después de las validaciones de estructura y formato.

Responsabilidades:
- Cargar y cachear esquemas XSD oficiales SIFEN v150
- Validar documentos XML contra esquemas completos
- Capturar y formatear errores específicos de lxml
- Proporcionar validación robusta con manejo de excepciones

Uso:
    from .core_validator import CoreXSDValidator
    
    validator = CoreXSDValidator()
    is_valid, errors = validator.validate(xml_content)
    
    # Con XSD personalizado
    validator = CoreXSDValidator("/path/to/custom.xsd")
    is_valid, errors = validator.validate(xml_content)

Características:
- Carga única de schema al inicializar (performance)
- Manejo robusto de errores XML y XSD
- Parsing optimizado con configuración específica
- Validación autoritativa contra especificaciones oficiales

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
"""

from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
from lxml import etree

from .constants import DEFAULT_XSD_PATH, SIFEN_VERSION, XML_PARSER_CONFIG
from .error_handler import ValidationError


# =====================================
# VALIDADOR XSD PRINCIPAL
# =====================================

class CoreXSDValidator:
    """
    Validador principal contra esquemas XSD oficiales SIFEN v150

    Este validador proporciona la validación más completa y autoritativa
    contra los esquemas oficiales SIFEN. Debe usarse como validación final
    después de verificar estructura básica y formatos.

    Características:
    - Carga única de schema (lazy loading con cache)
    - Validación completa contra especificaciones oficiales
    - Manejo robusto de errores con contexto detallado
    - Optimización para validación de múltiples documentos
    """

    def __init__(self, xsd_path: Optional[str] = None):
        """
        Inicializa el validador XSD

        Args:
            xsd_path: Ruta opcional al archivo XSD. Si no se proporciona,
                     usa DEFAULT_XSD_PATH desde constants

        Raises:
            ValidationError: Si hay problemas cargando el schema

        Example:
            >>> # Usar schema por defecto
            >>> validator = CoreXSDValidator()
            >>> 
            >>> # Usar schema personalizado
            >>> validator = CoreXSDValidator("/path/to/schema.xsd")
        """
        # Configurar ruta del schema
        if xsd_path:
            self.xsd_path = Path(xsd_path)
        else:
            self.xsd_path = DEFAULT_XSD_PATH

        # Schema se carga en lazy loading para optimización
        self._schema = None
        self._schema_loaded = False
        self._schema_load_error = None

        # Configurar parser XML optimizado para validación
        self._xml_parser = self._create_xml_parser()

        # Estadísticas de uso (opcional para debugging)
        self._validation_count = 0
        self._last_validation_time = None

    def _create_xml_parser(self) -> etree.XMLParser:
        """
        Crea parser XML optimizado para validación

        Returns:
            Parser XML configurado
        """
        return etree.XMLParser(
            remove_blank_text=XML_PARSER_CONFIG['remove_blank_text'],
            remove_comments=XML_PARSER_CONFIG['remove_comments'],
            strip_cdata=XML_PARSER_CONFIG['strip_cdata'],
            recover=XML_PARSER_CONFIG['recover']
        )

    def _load_schema(self) -> None:
        """
        Carga el esquema XSD con manejo robusto de errores

        Realiza carga única del schema con lazy loading para optimización.
        El schema se mantiene en cache para validaciones subsequentes.

        Raises:
            ValidationError: Si el schema no se puede cargar
        """
        if self._schema_loaded:
            return

        try:
            # Verificar que el archivo existe
            if not self.xsd_path.exists():
                raise ValidationError(
                    f"Schema XSD no encontrado: {self.xsd_path}",
                    error_code="SCHEMA_NOT_FOUND"
                )

            # Verificar que es un archivo
            if not self.xsd_path.is_file():
                raise ValidationError(
                    f"Ruta XSD no es un archivo válido: {self.xsd_path}",
                    error_code="SCHEMA_INVALID_PATH"
                )

            # Cargar y parsear el schema
            try:
                schema_doc = etree.parse(str(self.xsd_path), self._xml_parser)
                self._schema = etree.XMLSchema(schema_doc)

            except etree.XMLSyntaxError as e:
                raise ValidationError(
                    f"Error de sintaxis en schema XSD: {str(e)}",
                    error_code="SCHEMA_SYNTAX_ERROR",
                    context={'file': str(self.xsd_path),
                             'line': getattr(e, 'lineno', None)}
                )

            except etree.XMLSchemaParseError as e:
                raise ValidationError(
                    f"Error parseando schema XSD: {str(e)}",
                    error_code="SCHEMA_PARSE_ERROR",
                    context={'file': str(self.xsd_path)}
                )

            except Exception as e:
                raise ValidationError(
                    f"Error inesperado cargando schema XSD: {str(e)}",
                    error_code="SCHEMA_LOAD_ERROR",
                    context={'file': str(self.xsd_path),
                             'exception_type': type(e).__name__}
                )

            # Verificar que el schema se cargó correctamente
            if self._schema is None:
                raise ValidationError(
                    "Schema XSD se cargó pero está vacío",
                    error_code="SCHEMA_EMPTY"
                )

            self._schema_loaded = True
            self._schema_load_error = None

        except ValidationError:
            # Re-lanzar errores de validación
            self._schema_load_error = True
            raise
        except Exception as e:
            # Capturar cualquier otro error inesperado
            error = ValidationError(
                f"Error crítico cargando schema: {str(e)}",
                error_code="SCHEMA_CRITICAL_ERROR",
                context={'exception_type': type(e).__name__}
            )
            self._schema_load_error = error
            raise error

    def validate(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Valida un documento XML contra el esquema XSD SIFEN

        Realiza validación completa y autoritativa contra el esquema oficial.
        Esta debe ser la validación final después de estructura y formato.

        Args:
            xml_content: Contenido XML a validar como string

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores_detallados)

        Raises:
            ValidationError: Solo para errores críticos del sistema,
                           errores de validación normal se retornan en la lista

        Example:
            >>> validator = CoreXSDValidator()
            >>> xml = '<?xml version="1.0"?><rDE>...</rDE>'
            >>> is_valid, errors = validator.validate(xml)
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Error XSD: {error}")
        """
        # Asegurar que el schema esté cargado
        try:
            self._load_schema()
        except ValidationError as e:
            # Error crítico de schema - no se puede validar
            return False, [f"Error crítico de schema: {e.message}"]

        # Verificar que el schema se cargó correctamente
        if self._schema is None:
            return False, ["Error crítico: Schema XSD no está disponible para validación"]

        # Incrementar contador de validaciones
        self._validation_count += 1

        try:
            # Parsear el documento XML
            xml_doc = self._parse_xml_document(xml_content)

            # Realizar validación contra schema
            is_valid = self._schema.validate(xml_doc)

            # Procesar errores si los hay
            errors = []
            if not is_valid:
                errors = self._process_validation_errors()

            return is_valid, errors

        except etree.XMLSyntaxError as e:
            # Error de sintaxis XML - retornar como error de validación
            return False, [f"Error de sintaxis XML: {self._format_xml_syntax_error(e)}"]

        except Exception as e:
            # Error inesperado - retornar como error de validación
            return False, [f"Error inesperado durante validación XSD: {str(e)}"]

    def _parse_xml_document(self, xml_content: str) -> etree._Element:
        """
        Parsea el documento XML con manejo robusto de errores

        Args:
            xml_content: Contenido XML como string

        Returns:
            Documento XML parseado

        Raises:
            etree.XMLSyntaxError: Si el XML tiene errores de sintaxis
            Exception: Para otros errores de parsing
        """
        try:
            # Codificar a UTF-8 si es necesario
            if isinstance(xml_content, str):
                xml_bytes = xml_content.encode('utf-8')
            else:
                xml_bytes = xml_content

            # Parsear con el parser configurado
            xml_doc = etree.fromstring(xml_bytes, self._xml_parser)

            return xml_doc

        except etree.XMLSyntaxError:
            # Re-lanzar errores de sintaxis XML
            raise
        except UnicodeEncodeError as e:
            raise Exception(f"Error de codificación UTF-8: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parseando documento XML: {str(e)}")

    def _process_validation_errors(self) -> List[str]:
        """
        Procesa y formatea errores de validación del schema

        Returns:
            Lista de errores formateados
        """
        errors = []

        # Verificar que el schema esté disponible
        if self._schema is None:
            return ["Error interno: Schema no disponible para procesar errores"]

        # Obtener errores del log del schema
        for error in self._schema.error_log:
            formatted_error = self._format_schema_error(error)
            errors.append(formatted_error)

        return errors

    def _format_schema_error(self, error: etree._LogEntry) -> str:
        """
        Formatea un error individual del schema para mejor legibilidad

        Args:
            error: Error del log de lxml

        Returns:
            Error formateado
        """
        # Información básica del error
        line_info = f"Línea {error.line}" if error.line else "Línea desconocida"
        column_info = f", Columna {error.column}" if error.column else ""
        location = f"{line_info}{column_info}"

        # Limpiar mensaje del error
        message = self._clean_error_message(error.message)

        # Agregar contexto si está disponible
        if error.filename:
            location += f" en {error.filename}"

        # Formatear error final
        return f"{location}: {message}"

    def _clean_error_message(self, message: str) -> str:
        """
        Limpia y mejora mensajes de error de lxml

        Args:
            message: Mensaje original del error

        Returns:
            Mensaje limpio y mejorado
        """
        # Remover namespace URIs largos del mensaje
        import re
        cleaned = re.sub(r'\{[^}]*\}', '', message)

        # Remover paths de archivos temporales
        cleaned = re.sub(r'file:///[^\s,]+', '<schema>', cleaned)

        # Reemplazos comunes para mejorar legibilidad
        replacements = {
            "Element ": "Elemento ",
            "attribute ": "atributo ",
            "is not a valid value": "no es un valor válido",
            "Missing child element": "Elemento hijo faltante",
            "Invalid content was found": "Contenido inválido encontrado",
            "The value": "El valor",
            "Expected is": "Se esperaba",
            "but was": "pero se encontró"
        }

        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        return cleaned.strip()

    def _format_xml_syntax_error(self, error: etree.XMLSyntaxError) -> str:
        """
        Formatea errores de sintaxis XML

        Args:
            error: Error de sintaxis XML

        Returns:
            Error formateado
        """
        line_info = f"Línea {error.lineno}" if error.lineno else "Línea desconocida"
        return f"{line_info}: {str(error)}"

    def get_schema_version(self) -> str:
        """
        Retorna la versión del schema cargado

        Returns:
            Versión del schema (ej: "150")
        """
        return SIFEN_VERSION

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Obtiene información detallada del schema cargado

        Returns:
            Diccionario con información del schema
        """
        try:
            self._load_schema()
        except ValidationError:
            return {
                'loaded': False,
                'error': 'Schema no se pudo cargar',
                'path': str(self.xsd_path)
            }

        return {
            'loaded': self._schema_loaded,
            'version': self.get_schema_version(),
            'path': str(self.xsd_path),
            'exists': self.xsd_path.exists(),
            'size_bytes': self.xsd_path.stat().st_size if self.xsd_path.exists() else 0,
            'validation_count': self._validation_count
        }

    def is_schema_loaded(self) -> bool:
        """
        Verifica si el schema está cargado correctamente

        Returns:
            True si el schema está cargado y disponible
        """
        return (self._schema_loaded and
                self._schema is not None and
                self._schema_load_error is None)

    def reload_schema(self) -> None:
        """
        Fuerza la recarga del schema

        Útil si el archivo XSD ha cambiado y se necesita recargar.

        Raises:
            ValidationError: Si hay problemas recargando el schema
        """
        self._schema = None
        self._schema_loaded = False
        self._schema_load_error = None

        # Forzar recarga
        self._load_schema()

    def validate_with_detailed_report(self, xml_content: str) -> Dict[str, Any]:
        """
        Valida con reporte detallado para debugging avanzado

        Args:
            xml_content: Contenido XML a validar

        Returns:
            Diccionario con información detallada de validación
        """
        import time

        start_time = time.time()

        # Realizar validación normal
        is_valid, errors = self.validate(xml_content)

        validation_time = time.time() - start_time

        # Recopilar información adicional
        report = {
            'is_valid': is_valid,
            'errors': errors,
            'error_count': len(errors),
            'validation_time_ms': round(validation_time * 1000, 2),
            'schema_info': self.get_schema_info(),
            'xml_info': self._analyze_xml_content(xml_content)
        }

        return report

    def _analyze_xml_content(self, xml_content: str) -> Dict[str, Any]:
        """
        Analiza el contenido XML para el reporte detallado

        Args:
            xml_content: Contenido XML

        Returns:
            Análisis del contenido XML
        """
        try:
            xml_doc = self._parse_xml_document(xml_content)

            # Información básica
            info = {
                'size_bytes': len(xml_content.encode('utf-8')),
                'lines': xml_content.count('\n') + 1,
                'root_element': xml_doc.tag,
                'total_elements': len(list(xml_doc.iter(tag=etree.Element))),
                'namespaces': dict(xml_doc.nsmap) if xml_doc.nsmap else {},
                'encoding_detected': 'utf-8'  # Asumimos UTF-8
            }

            return info

        except Exception as e:
            return {
                'error': f"No se pudo analizar XML: {str(e)}",
                'size_bytes': len(xml_content.encode('utf-8', errors='ignore'))
            }


# =====================================
# UTILIDADES DE CONVENIENCIA
# =====================================

def quick_xsd_validation(xml_content: str, xsd_path: Optional[str] = None) -> bool:
    """
    Validación XSD rápida que retorna solo resultado booleano

    Args:
        xml_content: Contenido XML a validar
        xsd_path: Ruta opcional al XSD

    Returns:
        True si es válido según XSD
    """
    try:
        validator = CoreXSDValidator(xsd_path)
        is_valid, _ = validator.validate(xml_content)
        return is_valid
    except Exception:
        return False


def get_xsd_errors_only(xml_content: str, xsd_path: Optional[str] = None) -> List[str]:
    """
    Obtiene solo los errores de validación XSD

    Args:
        xml_content: Contenido XML a validar
        xsd_path: Ruta opcional al XSD

    Returns:
        Lista de errores XSD
    """
    try:
        validator = CoreXSDValidator(xsd_path)
        _, errors = validator.validate(xml_content)
        return errors
    except Exception as e:
        return [f"Error en validación XSD: {str(e)}"]


def validate_with_performance_metrics(
    xml_content: str,
    xsd_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validación con métricas de performance incluidas

    Args:
        xml_content: Contenido XML a validar
        xsd_path: Ruta opcional al XSD

    Returns:
        Diccionario con resultados y métricas
    """
    try:
        validator = CoreXSDValidator(xsd_path)
        return validator.validate_with_detailed_report(xml_content)
    except Exception as e:
        return {
            'is_valid': False,
            'errors': [f"Error crítico: {str(e)}"],
            'error_count': 1,
            'validation_time_ms': 0
        }


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    'CoreXSDValidator',
    'quick_xsd_validation',
    'get_xsd_errors_only',
    'validate_with_performance_metrics'
]
