"""
🎯 Schema Validator - Responsabilidad ÚNICA: Validación XSD

Este módulo se encarga EXCLUSIVAMENTE de:
- Cargar y cachear schemas XSD
- Validar estructura XML contra XSD  
- Extraer y reportar errores de validación
- Proporcionar validación de fragmentos XML

NO GENERA XML | NO CREA DATOS | NO MANEJA LÓGICA DE NEGOCIO
Utiliza composición para integrar con otros módulos especializados.
"""

from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging
from lxml import etree

# Importaciones de módulos especializados (composición)
# NOTA: Algunos imports están comentados hasta que se implementen los módulos

# TODO: Implementar estos módulos especializados
# from ...tests.utils.xml_generator import XMLGeneratorAPI
# from ...tests.utils.xml_generator.sample_data.sample_data_api import SampleDataAPI
# from ...tests.utils.xml_generator.document_types_generator import DocumentTypesAPI

# Import real existente - ErrorHandler desde validators.py existente
# Desde: schemas/v150/tests/utils/schema_validator.py
from ...tests.utils.xml_generator.validators import ErrorHandler

# Configuración logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Resultado inmutable de validación XSD

    Attributes:
        is_valid: Indica si el XML es válido según el schema
        errors: Lista de errores de validación encontrados
        warnings: Lista de advertencias (opcional)
        schema_version: Versión del schema utilizado
        validation_time_ms: Tiempo de validación en milisegundos
        element_count: Número de elementos validados
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str] = field(default_factory=list)
    schema_version: str = "v150"
    validation_time_ms: Optional[float] = None
    element_count: Optional[int] = None


@dataclass
class FragmentValidationResult:
    """
    Resultado de validación de fragmento XML

    Attributes:
        is_valid: Si el fragmento es válido
        fragment_type: Tipo de fragmento validado
        errors: Errores específicos del fragmento
        suggested_fixes: Sugerencias de corrección
    """
    is_valid: bool
    fragment_type: str
    errors: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)


class SchemaValidator:
    """
    🎯 Validador XSD con responsabilidad única

    RESPONSABILIDADES:
    ✅ Cargar schemas XSD modulares
    ✅ Validar XML completo contra schema
    ✅ Validar fragmentos XML específicos
    ✅ Extraer errores de validación detallados
    ✅ Cachear schemas para performance

    NO HACE:
    ❌ Generar XML (responsabilidad de XMLGeneratorAPI)
    ❌ Crear datos de muestra (responsabilidad de SampleDataAPI)
    ❌ Lógica específica de tipos de documentos
    ❌ Formateo complejo de errores de negocio

    Usage:
        validator = SchemaValidator("schemas/v150/DE_v150.xsd")
        result = validator.validate_xml(xml_content)
        if not result.is_valid:
            print(f"Errores: {result.errors}")
    """

    def __init__(
        self,
        schema_path: str,
        error_handler: Optional[ErrorHandler] = None,
        cache_enabled: bool = True
    ):
        """
        Inicializa el validador XSD

        Args:
            schema_path: Ruta al archivo XSD principal
            error_handler: Manejador de errores personalizado (inyección)
            cache_enabled: Si habilitar cache de schemas

        Raises:
            ValueError: Si no se puede cargar el schema
            FileNotFoundError: Si el archivo de schema no existe
        """
        self.schema_path = Path(schema_path)
        self.cache_enabled = cache_enabled
        self.error_handler = error_handler or ErrorHandler()

        # Cache de schemas para performance
        self._schema_cache: Dict[str, etree.XMLSchema] = {}

        # Cargar schema principal
        self.schema = self._load_schema()

        # Metadatos del schema
        self.schema_version = self._extract_schema_version()

        logger.info(
            f"SchemaValidator inicializado - Schema: {self.schema_path}")

    def validate_xml(self, xml_content: str) -> ValidationResult:
        """
        Valida XML completo contra schema XSD principal

        Args:
            xml_content: Contenido XML como string UTF-8

        Returns:
            ValidationResult con estado detallado de validación

        Example:
            result = validator.validate_xml(xml_string)
            if result.is_valid:
                print("XML válido")
            else:
                for error in result.errors:
                    print(f"Error: {error}")
        """
        import time
        start_time = time.time()

        try:
            # Parse XML con encoding explícito y parser seguro
            xml_bytes = xml_content.encode(
                'utf-8') if isinstance(xml_content, str) else xml_content
            parser = etree.XMLParser(
                remove_blank_text=True, resolve_entities=False)
            doc = etree.fromstring(xml_bytes, parser)

            # Validación contra schema
            is_valid = self.schema.validate(doc)

            # Extraer errores detallados
            errors = self._extract_validation_errors()
            warnings = self._extract_warnings()

            # Métricas de validación
            validation_time = (time.time() - start_time) * 1000
            element_count = len(doc.xpath("//*"))

            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                schema_version=self.schema_version,
                validation_time_ms=validation_time,
                element_count=element_count
            )

        except etree.XMLSyntaxError as e:
            logger.warning(f"Error sintaxis XML: {str(e)}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Error de sintaxis XML: {str(e)}"],
                schema_version=self.schema_version,
                validation_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.error(f"Error inesperado en validación: {str(e)}")
            return self.error_handler.handle_unexpected_validation_error(e)

    def validate_fragment(
        self,
        xml_fragment: str,
        wrapper_element: str,
        namespace: Optional[str] = None
    ) -> FragmentValidationResult:
        """
        Valida fragmento XML específico envolviéndolo en elemento raíz

        Args:
            xml_fragment: Fragmento XML a validar
            wrapper_element: Elemento raíz para envolver
            namespace: Namespace opcional para el wrapper

        Returns:
            FragmentValidationResult con estado específico del fragmento

        Example:
            fragment = "<dVerFor>150</dVerFor>"
            result = validator.validate_fragment(fragment, "root")
            assert result.is_valid
        """
        try:
            # Construir XML completo con namespace si se proporciona
            if namespace:
                wrapped_xml = f'<{wrapper_element} xmlns="{namespace}">{xml_fragment}</{wrapper_element}>'
            else:
                wrapped_xml = f"<{wrapper_element}>{xml_fragment}</{wrapper_element}>"

            # Validar XML envuelto
            validation_result = self.validate_xml(wrapped_xml)

            # Filtrar errores específicos del fragmento
            fragment_errors = self._filter_fragment_errors(
                validation_result.errors, wrapper_element)

            return FragmentValidationResult(
                is_valid=validation_result.is_valid,
                fragment_type=wrapper_element,
                errors=fragment_errors,
                suggested_fixes=self._generate_fragment_fixes(fragment_errors)
            )

        except Exception as e:
            logger.error(f"Error validando fragmento: {str(e)}")
            return FragmentValidationResult(
                is_valid=False,
                fragment_type=wrapper_element,
                errors=[f"Error procesando fragmento: {str(e)}"]
            )

    def validate_against_module(self, xml_content: str, module_schema_path: str) -> ValidationResult:
        """
        Valida XML contra un módulo específico del schema

        Args:
            xml_content: Contenido XML a validar
            module_schema_path: Ruta al schema del módulo específico

        Returns:
            ValidationResult usando el schema del módulo

        Example:
            result = validator.validate_against_module(xml, "common/basic_types.xsd")
        """
        module_validator = self._get_module_validator(module_schema_path)

        # Usar el validador específico del módulo
        temp_schema = self.schema
        self.schema = module_validator

        try:
            result = self.validate_xml(xml_content)
            result.schema_version = f"{self.schema_version}-{Path(module_schema_path).stem}"
            return result
        finally:
            # Restaurar schema principal
            self.schema = temp_schema

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Obtiene información del schema cargado

        Returns:
            Diccionario con metadatos del schema
        """
        return {
            "schema_path": str(self.schema_path),
            "schema_version": self.schema_version,
            "target_namespace": self._get_target_namespace(),
            "element_count": len(self.schema.schema.xpath("//xs:element", namespaces={"xs": "http://www.w3.org/2001/XMLSchema"})),
            "cache_enabled": self.cache_enabled,
            "cached_schemas": list(self._schema_cache.keys())
        }

    def clear_cache(self) -> None:
        """Limpia el cache de schemas"""
        self._schema_cache.clear()
        logger.info("Cache de schemas limpiado")

    # ===== MÉTODOS PRIVADOS =====

    def _load_schema(self) -> etree.XMLSchema:
        """
        Carga el schema XSD desde archivo con cache

        Returns:
            Schema XSD compilado

        Raises:
            ValueError: Si no se puede cargar el schema
            FileNotFoundError: Si el archivo no existe
        """
        schema_key = str(self.schema_path)

        # Verificar cache si está habilitado
        if self.cache_enabled and schema_key in self._schema_cache:
            logger.debug(f"Schema cargado desde cache: {schema_key}")
            return self._schema_cache[schema_key]

        try:
            if not self.schema_path.exists():
                raise FileNotFoundError(
                    f"Schema no encontrado: {self.schema_path}")

            # Cargar y parsear schema con parser seguro
            parser = etree.XMLParser(
                remove_blank_text=True, resolve_entities=False)
            with open(self.schema_path, 'r', encoding='utf-8') as schema_file:
                schema_doc = etree.parse(schema_file, parser)
                schema = etree.XMLSchema(schema_doc)

            # Guardar en cache si está habilitado
            if self.cache_enabled:
                self._schema_cache[schema_key] = schema
                logger.debug(f"Schema cacheado: {schema_key}")

            logger.info(f"Schema cargado exitosamente: {self.schema_path}")
            return schema

        except etree.XMLSchemaError as e:
            error_msg = f"Error en schema XSD {self.schema_path}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error cargando schema {self.schema_path}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _extract_validation_errors(self) -> List[str]:
        """Extrae errores de validación del schema log"""
        return [
            self._format_validation_error(error)
            for error in self.schema.error_log
        ]

    def _extract_warnings(self) -> List[str]:
        """Extrae advertencias de validación (si las hay)"""
        # En lxml, warnings típicamente vienen en el error_log con nivel diferente
        warnings = []
        for error in self.schema.error_log:
            if "warning" in str(error).lower():
                warnings.append(str(error))
        return warnings

    def _format_validation_error(self, error) -> str:
        """
        Formatea error de validación para mejor legibilidad

        Args:
            error: Error object de lxml

        Returns:
            String formateado del error
        """
        return f"Línea {error.line}: {error.message}"

    def _extract_schema_version(self) -> str:
        """Extrae versión del schema desde el archivo XSD"""
        try:
            # Buscar atributo version o inferir desde nombre archivo
            if "v150" in str(self.schema_path):
                return "v150"
            elif "150" in str(self.schema_path):
                return "v150"
            else:
                return "unknown"
        except Exception:
            return "v150"  # Default para SIFEN

    def _get_target_namespace(self) -> Optional[str]:
        """Obtiene el target namespace del schema"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Buscar targetNamespace en el contenido
                import re
                match = re.search(r'targetNamespace="([^"]+)"', content)
                return match.group(1) if match else None
        except Exception:
            return None

    def _get_module_validator(self, module_path: str) -> etree.XMLSchema:
        """Obtiene validador para módulo específico"""
        full_module_path = self.schema_path.parent / module_path
        return SchemaValidator(str(full_module_path), cache_enabled=self.cache_enabled).schema

    def _filter_fragment_errors(self, errors: List[str], wrapper_element: str) -> List[str]:
        """Filtra errores específicos del fragmento (no del wrapper)"""
        filtered_errors = []
        for error in errors:
            # Excluir errores relacionados con el wrapper artificial
            if wrapper_element not in error and "root element" not in error.lower():
                filtered_errors.append(error)
        return filtered_errors

    def _generate_fragment_fixes(self, errors: List[str]) -> List[str]:
        """Genera sugerencias de corrección para errores de fragmento"""
        fixes = []
        for error in errors:
            if "required" in error.lower():
                fixes.append(
                    "Verificar que todos los elementos requeridos estén presentes")
            elif "format" in error.lower():
                fixes.append(
                    "Revisar formato de los datos según especificación SIFEN")
            elif "type" in error.lower():
                fixes.append("Verificar que los tipos de datos sean correctos")
        return fixes


class SchemaValidatorWithHelpers:
    """
    🔌 Validador enriquecido que COMPONE funcionalidades especializadas

    Esta clase actúa como un facade que integra:
    - SchemaValidator (validación XSD)
    - XMLGeneratorAPI (generación XML) - TODO: implementar
    - SampleDataAPI (datos de muestra) - TODO: implementar

    Útil para testing y workflows completos de validación.

    Usage:
        validator = SchemaValidatorWithHelpers("schema.xsd")
        # result = validator.validate_with_sample_data("factura")  # TODO: implementar
    """

    def __init__(self, schema_path: str):
        """
        Inicializa validador con helpers integrados

        Args:
            schema_path: Ruta al schema XSD principal
        """
        # ✅ Validador principal - FUNCIONAL
        self.validator = SchemaValidator(schema_path)

        # TODO: Descomentar cuando se implementen los módulos
        # self.xml_generator = XMLGeneratorAPI()
        # self.sample_data = SampleDataAPI()
        # self.doc_types = DocumentTypesAPI()

        logger.info("SchemaValidatorWithHelpers inicializado (sin helpers aún)")

    def validate_with_sample_data(self, doc_type: str) -> ValidationResult:
        """
        TODO: Implementar cuando existan XMLGeneratorAPI y SampleDataAPI

        Args:
            doc_type: Tipo de documento (factura, autofactura, etc.)

        Returns:
            ValidationResult del documento generado con datos de muestra
        """
        # Implementación temporal hasta que existan los módulos
        logger.warning(
            "validate_with_sample_data aún no implementado - faltan módulos especializados")
        return ValidationResult(
            is_valid=False,
            errors=[
                "Funcionalidad no implementada: faltan XMLGeneratorAPI y SampleDataAPI"],
            schema_version=self.validator.schema_version
        )

    def test_minimal_document(self, doc_type: str) -> ValidationResult:
        """
        TODO: Implementar cuando exista XMLGeneratorAPI

        Args:
            doc_type: Tipo de documento a probar

        Returns:
            ValidationResult del documento mínimo
        """
        logger.warning(
            "test_minimal_document aún no implementado - falta XMLGeneratorAPI")
        return ValidationResult(
            is_valid=False,
            errors=["Funcionalidad no implementada: falta XMLGeneratorAPI"],
            schema_version=self.validator.schema_version
        )

    def test_complete_document(self, doc_type: str) -> ValidationResult:
        """
        TODO: Implementar cuando exista XMLGeneratorAPI

        Args:
            doc_type: Tipo de documento a probar

        Returns:
            ValidationResult del documento completo
        """
        logger.warning(
            "test_complete_document aún no implementado - falta XMLGeneratorAPI")
        return ValidationResult(
            is_valid=False,
            errors=["Funcionalidad no implementada: falta XMLGeneratorAPI"],
            schema_version=self.validator.schema_version
        )

    def batch_validate_samples(self, doc_types: List[str]) -> Dict[str, ValidationResult]:
        """
        TODO: Implementar cuando existan todos los módulos especializados

        Args:
            doc_types: Lista de tipos de documentos a validar

        Returns:
            Diccionario con resultados por tipo de documento
        """
        logger.warning(
            "batch_validate_samples aún no implementado - faltan módulos especializados")
        results = {}
        for doc_type in doc_types:
            results[doc_type] = ValidationResult(
                is_valid=False,
                errors=[
                    "Funcionalidad no implementada: faltan módulos especializados"],
                schema_version=self.validator.schema_version
            )
        return results


# ===== UTILIDADES ADICIONALES =====

def create_validator_for_document_type(doc_type: str) -> SchemaValidator:
    """
    Factory para crear validador específico por tipo de documento

    Args:
        doc_type: Tipo de documento (factura, autofactura, etc.)

    Returns:
        SchemaValidator configurado para el tipo específico
    """
    schema_mappings = {
        "factura": "schemas/v150/document_types/invoice_types.xsd",
        "autofactura": "schemas/v150/document_types/autoinvoice_types.xsd",
        "nota_credito": "schemas/v150/document_types/credit_note_types.xsd",
        "nota_debito": "schemas/v150/document_types/debit_note_types.xsd",
        "nota_remision": "schemas/v150/document_types/remission_note_types.xsd"
    }

    schema_path = schema_mappings.get(doc_type, "schemas/v150/DE_v150.xsd")
    return SchemaValidator(schema_path)


def validate_xml_file(file_path: str, schema_path: str) -> ValidationResult:
    """
    Utility para validar archivo XML directamente

    Args:
        file_path: Ruta al archivo XML
        schema_path: Ruta al schema XSD

    Returns:
        ValidationResult del archivo
    """
    validator = SchemaValidator(schema_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()

    return validator.validate_xml(xml_content)
