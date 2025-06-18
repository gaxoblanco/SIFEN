"""
Módulo: Schema Test Helpers

Propósito:
    Utilidades específicas para testing de schemas SIFEN v150 modulares.
    Proporciona helpers para validación, comparación y testing de elementos
    específicos de schemas XSD organizados de forma modular.

Funcionalidades principales:
    - Validación contra módulos específicos de schema
    - Helpers para testing de tipos básicos SIFEN
    - Validación de estructura modular
    - Testing de resolución de dependencias entre módulos
    - Utilidades para debugging de schemas

Dependencias:
    - lxml: Manipulación XML y validación XSD
    - pathlib: Manejo de rutas de schemas modulares
    - .xml_helpers: Utilidades XML básicas

Uso:
    from .schema_helpers import SchemaTestHelpers
    
    # Validar contra módulo específico
    is_valid = SchemaTestHelpers.validate_against_module(xml, "basic_types")
    
    # Verificar dependencias entre módulos
    deps_ok = SchemaTestHelpers.check_module_dependencies("document_core")

Autor: Sistema SIFEN
Versión: 1.0.0
Fecha: 2025-06-17
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum

from lxml import etree

from .xml_helpers import XMLTestHelpers
from .constants import (
    SIFEN_NAMESPACE_URI,
    SIFEN_SCHEMA_VERSION,
    REQUIRED_SIFEN_ELEMENTS,
    SIFEN_DOCUMENT_TYPES,
    BASIC_FIELD_PATTERNS
)


# ================================
# CONFIGURACIÓN DEL MÓDULO
# ================================

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Excepción para errores de validación de schema"""
    pass


class ModuleDependencyError(Exception):
    """Excepción para errores de dependencias entre módulos"""
    pass


# ================================
# ENUMS Y DATACLASSES
# ================================

class SchemaModule(Enum):
    """Módulos de schema SIFEN v150"""
    MAIN = "DE_v150.xsd"
    BASIC_TYPES = "common/basic_types.xsd"
    GEOGRAPHIC_TYPES = "common/geographic_types.xsd"
    CONTACT_TYPES = "common/contact_types.xsd"
    CURRENCY_TYPES = "common/currency_types.xsd"
    DOCUMENT_CORE = "document_core/core_types.xsd"
    OPERATION_DATA = "operations/operation_types.xsd"
    STAMPING_DATA = "document_core/stamping_types.xsd"
    ISSUER_TYPES = "parties/issuer_types.xsd"
    RECEIVER_TYPES = "parties/receiver_types.xsd"
    PAYMENT_METHODS = "operations/payment_types.xsd"
    ITEMS = "operations/item_types.xsd"
    TRANSPORT = "transport/transport_types.xsd"


@dataclass
class ValidationResult:
    """Resultado de validación de schema"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    module: Optional[str] = None
    validation_time: Optional[float] = None


@dataclass
class ModuleDependency:
    """Dependencia entre módulos de schema"""
    source_module: str
    target_module: str
    dependency_type: str  # 'import', 'include', 'reference'
    is_required: bool = True


# ================================
# CLASE PRINCIPAL: SchemaTestHelpers
# ================================

class SchemaTestHelpers:
    """
    Utilidades específicas para testing de schemas SIFEN modulares

    Esta clase proporciona métodos para validación, testing y debugging
    de schemas XSD organizados de forma modular, con énfasis en las
    especificaciones SIFEN v150.
    """

    def __init__(self, schema_base_path: Optional[Union[str, Path]] = None):
        """
        Inicializa helpers con ruta base de schemas

        Args:
            schema_base_path: Ruta base donde están los schemas modulares
        """
        if schema_base_path is None:
            schema_base_path = Path(
                __file__).parent.parent.parent / "schemas" / "v150"

        self.schema_base_path = Path(schema_base_path)
        self._schema_cache: Dict[str, etree.XMLSchema] = {}
        self._dependency_cache: Dict[str, List[ModuleDependency]] = {}

    # ================================
    # VALIDACIÓN CONTRA MÓDULOS
    # ================================

    def validate_against_module(
        self,
        xml_content: str,
        module: Union[str, SchemaModule],
        wrap_in_root: bool = True
    ) -> ValidationResult:
        """
        Valida XML contra un módulo específico de schema

        Args:
            xml_content: Contenido XML a validar
            module: Módulo de schema (nombre o enum)
            wrap_in_root: Si envolver el XML en elemento raíz si es necesario

        Returns:
            ValidationResult: Resultado detallado de la validación

        Examples:
            >>> helper = SchemaTestHelpers()
            >>> xml = "<dRUCEmi>12345678</dRUCEmi>"
            >>> result = helper.validate_against_module(xml, "basic_types")
            >>> assert result.is_valid == True
        """
        import time
        start_time = time.time()

        try:
            # Obtener ruta del módulo
            module_path = self._get_module_path(module)

            # Cargar schema del módulo
            schema = self._load_module_schema(module_path)

            # Preparar XML para validación
            prepared_xml = self._prepare_xml_for_module_validation(
                xml_content, module, wrap_in_root
            )

            # Parsear XML
            success, xml_tree, parse_errors = XMLTestHelpers.parse_xml_safely(
                prepared_xml)

            if not success or xml_tree is None:
                return ValidationResult(
                    is_valid=False,
                    errors=parse_errors,
                    warnings=[],
                    module=str(module),
                    validation_time=time.time() - start_time
                )

            # Validar contra schema
            is_valid = schema.validate(xml_tree)

            # Recopilar errores y warnings
            errors = []
            warnings = []

            if not is_valid:
                for error in schema.error_log:
                    error_msg = f"Línea {error.line}: {error.message}"
                    if error.level_name == 'ERROR':
                        errors.append(error_msg)
                    else:
                        warnings.append(error_msg)

            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                module=str(module),
                validation_time=time.time() - start_time
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error validando contra módulo {module}: {str(e)}"],
                warnings=[],
                module=str(module),
                validation_time=time.time() - start_time
            )

    def validate_sifen_basic_structure(self, xml_content: str) -> ValidationResult:
        """
        Valida estructura básica SIFEN requerida

        Verifica elementos fundamentales como namespace, versión,
        estructura rDE, elemento DE, etc.

        Args:
            xml_content: Contenido XML a validar

        Returns:
            ValidationResult: Resultado de validación

        Examples:
            >>> xml = '''<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            ...     <dVerFor>150</dVerFor>
            ...     <DE Id="...">...</DE>
            ... </rDE>'''
            >>> result = helper.validate_sifen_basic_structure(xml)
            >>> assert result.is_valid == True
        """
        errors = []
        warnings = []

        try:
            # Parsear XML
            success, xml_tree, parse_errors = XMLTestHelpers.parse_xml_safely(
                xml_content)

            if not success or xml_tree is None:
                return ValidationResult(
                    is_valid=False,
                    errors=parse_errors,
                    warnings=[],
                    module="basic_structure"
                )

            # Verificar namespace SIFEN
            if xml_tree.nsmap.get(None) != SIFEN_NAMESPACE_URI:
                errors.append(
                    f"Namespace SIFEN incorrecto. Esperado: {SIFEN_NAMESPACE_URI}")

            # Verificar elemento raíz
            if xml_tree.tag != f"{{{SIFEN_NAMESPACE_URI}}}rDE":
                errors.append(
                    f"Elemento raíz debe ser 'rDE' con namespace SIFEN")

            # Verificar versión del formato
            version_element = XMLTestHelpers.extract_element_text(
                xml_tree, "//dVerFor")
            if version_element != SIFEN_SCHEMA_VERSION:
                errors.append(
                    f"Versión incorrecta. Esperada: {SIFEN_SCHEMA_VERSION}, encontrada: {version_element}")

            # Verificar elementos requeridos
            for xpath in REQUIRED_SIFEN_ELEMENTS:
                if not XMLTestHelpers.element_exists(xml_tree, xpath):
                    errors.append(f"Elemento requerido faltante: {xpath}")

            # Verificar elemento DE con Id
            de_element = xml_tree.xpath("//DE[@Id]")
            if not de_element:
                errors.append("Elemento DE con atributo Id es requerido")
            elif len(de_element[0].get("Id", "")) != 44:
                warnings.append("ID del documento debe tener 44 caracteres")

            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                module="basic_structure"
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error validando estructura básica: {str(e)}"],
                warnings=[],
                module="basic_structure"
            )

    def validate_document_type_structure(
        self,
        xml_content: str,
        document_type: str
    ) -> ValidationResult:
        """
        Valida estructura específica según tipo de documento

        Args:
            xml_content: Contenido XML a validar
            document_type: Tipo de documento SIFEN (01, 04, 05, 06, 07)

        Returns:
            ValidationResult: Resultado de validación

        Examples:
            >>> xml = "<rDE>...factura...</rDE>"
            >>> result = helper.validate_document_type_structure(xml, "01")
            >>> assert result.is_valid == True
        """
        if document_type not in SIFEN_DOCUMENT_TYPES:
            return ValidationResult(
                is_valid=False,
                errors=[f"Tipo de documento inválido: {document_type}"],
                warnings=[],
                module=f"document_type_{document_type}"
            )

        doc_info = SIFEN_DOCUMENT_TYPES[document_type]
        errors = []
        warnings = []

        try:
            # Parsear XML
            success, xml_tree, parse_errors = XMLTestHelpers.parse_xml_safely(
                xml_content)

            if not success or xml_tree is None:
                return ValidationResult(
                    is_valid=False,
                    errors=parse_errors,
                    warnings=[],
                    module=f"document_type_{document_type}"
                )

            # Verificar tipo de documento en XML
            tipo_doc = XMLTestHelpers.extract_element_text(xml_tree, "//iTiDE")
            if tipo_doc != document_type:
                errors.append(
                    f"Tipo de documento inconsistente. Esperado: {document_type}, encontrado: {tipo_doc}")

            # Verificar elementos específicos del tipo de documento
            for element_xpath in doc_info.required_elements:
                if not XMLTestHelpers.element_exists(xml_tree, element_xpath):
                    errors.append(
                        f"Elemento requerido para {doc_info.name}: {element_xpath}")

            # Verificar elementos prohibidos para este tipo
            for element_xpath in doc_info.prohibited_elements:
                if XMLTestHelpers.element_exists(xml_tree, element_xpath):
                    errors.append(
                        f"Elemento no permitido para {doc_info.name}: {element_xpath}")

            # Verificar validaciones específicas del documento
            if hasattr(doc_info.specific_validations, 'get'):
                # Si specific_validations es un dict, usar .get()
                if doc_info.specific_validations.get("requires_receiver", False):
                    if not XMLTestHelpers.element_exists(xml_tree, "//gDatRec"):
                        errors.append(
                            f"Datos del receptor requeridos para {doc_info.name}")

                if doc_info.specific_validations.get("requires_items", False):
                    if not XMLTestHelpers.element_exists(xml_tree, "//gCamItem"):
                        errors.append(f"Items requeridos para {doc_info.name}")

                if doc_info.specific_validations.get("requires_totals", False):
                    if not XMLTestHelpers.element_exists(xml_tree, "//gTotSub"):
                        errors.append(
                            f"Totales requeridos para {doc_info.name}")

                if doc_info.specific_validations.get("requires_transport", False):
                    if not XMLTestHelpers.element_exists(xml_tree, "//gTransp"):
                        errors.append(
                            f"Datos de transporte requeridos para {doc_info.name}")

                if doc_info.specific_validations.get("requires_associated_document", False):
                    # Para notas de crédito/débito, verificar documento asociado
                    if not XMLTestHelpers.element_exists(xml_tree, "//gCamDEAsoc"):
                        errors.append(
                            f"Documento asociado requerido para {doc_info.name}")

            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                module=f"document_type_{document_type}"
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[
                    f"Error validando tipo de documento {document_type}: {str(e)}"],
                warnings=[],
                module=f"document_type_{document_type}"
            )

    # ================================
    # TESTING DE DEPENDENCIAS MODULARES
    # ================================

    def check_module_dependencies(self, module: Union[str, SchemaModule]) -> Tuple[bool, List[str]]:
        """
        Verifica que todas las dependencias de un módulo se resuelvan correctamente

        Args:
            module: Módulo a verificar

        Returns:
            Tuple[bool, List[str]]: (dependencias_ok, lista_de_errores)

        Examples:
            >>> deps_ok, errors = helper.check_module_dependencies("document_core")
            >>> assert deps_ok == True
            >>> assert len(errors) == 0
        """
        errors = []

        try:
            module_path = self._get_module_path(module)
            dependencies = self._get_module_dependencies(module_path)

            for dependency in dependencies:
                target_path = self.schema_base_path / dependency.target_module

                if not target_path.exists():
                    if dependency.is_required:
                        errors.append(
                            f"Dependencia requerida no encontrada: {dependency.target_module}")
                    else:
                        logger.warning(
                            f"Dependencia opcional no encontrada: {dependency.target_module}")

                # Verificar que el módulo de destino sea válido
                try:
                    self._load_module_schema(target_path)
                except Exception as e:
                    errors.append(
                        f"Error cargando dependencia {dependency.target_module}: {str(e)}")

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(
                f"Error verificando dependencias de {module}: {str(e)}")
            return False, errors

    def validate_modular_schema_integration(self) -> ValidationResult:
        """
        Valida que todos los módulos de schema se integren correctamente

        Returns:
            ValidationResult: Resultado de validación de integración

        Examples:
            >>> result = helper.validate_modular_schema_integration()
            >>> assert result.is_valid == True
        """
        errors = []
        warnings = []

        try:
            # Verificar que el schema principal exista
            main_schema_path = self.schema_base_path / SchemaModule.MAIN.value
            if not main_schema_path.exists():
                errors.append(
                    f"Schema principal no encontrado: {main_schema_path}")
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    module="integration"
                )

            # Intentar cargar el schema principal
            try:
                main_schema = self._load_module_schema(main_schema_path)
            except Exception as e:
                errors.append(f"Error cargando schema principal: {str(e)}")
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    module="integration"
                )

            # Verificar cada módulo
            for schema_module in SchemaModule:
                if schema_module == SchemaModule.MAIN:
                    continue

                module_path = self.schema_base_path / schema_module.value

                if not module_path.exists():
                    warnings.append(
                        f"Módulo opcional no encontrado: {schema_module.value}")
                    continue

                # Verificar dependencias del módulo
                deps_ok, dep_errors = self.check_module_dependencies(
                    schema_module.value)
                if not deps_ok:
                    errors.extend(dep_errors)

                # Intentar cargar el módulo
                try:
                    self._load_module_schema(module_path)
                except Exception as e:
                    errors.append(
                        f"Error cargando módulo {schema_module.value}: {str(e)}")

            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                module="integration"
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error en validación de integración: {str(e)}"],
                warnings=warnings,
                module="integration"
            )

    # ================================
    # TESTING DE TIPOS ESPECÍFICOS
    # ================================

    def validate_sifen_field_format(self, field_name: str, field_value: str) -> Tuple[bool, List[str]]:
        """
        Valida formato de campo específico según patrones SIFEN

        Args:
            field_name: Nombre del campo (ej: dRUCEmi, dCodSeg)
            field_value: Valor a validar

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores)

        Examples:
            >>> is_valid, errors = helper.validate_sifen_field_format("dRUCEmi", "12345678")
            >>> assert is_valid == True
        """
        errors = []

        if field_name not in BASIC_FIELD_PATTERNS:
            errors.append(f"Patrón no definido para campo: {field_name}")
            return False, errors

        pattern_info = BASIC_FIELD_PATTERNS[field_name]

        # Validar longitud
        if 'min_length' in pattern_info:
            if len(field_value) < pattern_info['min_length']:
                errors.append(
                    f"{field_name}: longitud mínima {pattern_info['min_length']}, actual {len(field_value)}")

        if 'max_length' in pattern_info:
            if len(field_value) > pattern_info['max_length']:
                errors.append(
                    f"{field_name}: longitud máxima {pattern_info['max_length']}, actual {len(field_value)}")

        # Validar patrón regex
        if 'pattern' in pattern_info:
            import re
            if not re.match(pattern_info['pattern'], field_value):
                errors.append(
                    f"{field_name}: formato inválido. Patrón esperado: {pattern_info['pattern']}")

        # Validar tipo de dato
        if 'data_type' in pattern_info:
            try:
                if pattern_info['data_type'] == 'integer':
                    int(field_value)
                elif pattern_info['data_type'] == 'decimal':
                    float(field_value)
            except ValueError:
                errors.append(
                    f"{field_name}: tipo de dato inválido. Esperado: {pattern_info['data_type']}")

        return len(errors) == 0, errors

    def extract_and_validate_sifen_elements(
        self,
        xml_content: str,
        elements_to_validate: List[str]
    ) -> Dict[str, ValidationResult]:
        """
        Extrae y valida múltiples elementos SIFEN de un XML

        Args:
            xml_content: Contenido XML
            elements_to_validate: Lista de XPaths de elementos a validar

        Returns:
            Dict[str, ValidationResult]: Resultados por elemento

        Examples:
            >>> elements = ["//dRUCEmi", "//dCodSeg", "//dVerFor"]
            >>> results = helper.extract_and_validate_sifen_elements(xml, elements)
            >>> assert all(result.is_valid for result in results.values())
        """
        results = {}

        # Parsear XML
        success, xml_tree, parse_errors = XMLTestHelpers.parse_xml_safely(
            xml_content)

        if not success or xml_tree is None:
            # Si el XML no se puede parsear, todos los elementos fallan
            for element_xpath in elements_to_validate:
                results[element_xpath] = ValidationResult(
                    is_valid=False,
                    errors=parse_errors,
                    warnings=[],
                    module="element_extraction"
                )
            return results

        # Validar cada elemento
        for element_xpath in elements_to_validate:
            try:
                # Extraer valor del elemento
                element_value = XMLTestHelpers.extract_element_text(
                    xml_tree, element_xpath)

                if element_value is None:
                    results[element_xpath] = ValidationResult(
                        is_valid=False,
                        errors=[f"Elemento no encontrado: {element_xpath}"],
                        warnings=[],
                        module="element_extraction"
                    )
                    continue

                # Determinar nombre del campo para validación de formato
                field_name = element_xpath.split(
                    "//")[-1].split("[")[0]  # Extraer nombre limpio

                # Validar formato si está definido
                is_valid, format_errors = self.validate_sifen_field_format(
                    field_name, element_value)

                results[element_xpath] = ValidationResult(
                    is_valid=is_valid,
                    errors=format_errors,
                    warnings=[],
                    module="element_extraction"
                )

            except Exception as e:
                results[element_xpath] = ValidationResult(
                    is_valid=False,
                    errors=[
                        f"Error validando elemento {element_xpath}: {str(e)}"],
                    warnings=[],
                    module="element_extraction"
                )

        return results

    # ================================
    # MÉTODOS PRIVADOS DE UTILIDAD
    # ================================

    def _get_module_path(self, module: Union[str, SchemaModule]) -> Path:
        """Obtiene la ruta de un módulo de schema"""
        if isinstance(module, SchemaModule):
            module_name = module.value
        else:
            module_name = str(module)

        # Si no tiene extensión, asumir .xsd
        if not module_name.endswith('.xsd'):
            module_name += '.xsd'

        return self.schema_base_path / module_name

    def _load_module_schema(self, module_path: Path) -> etree.XMLSchema:
        """Carga un schema de módulo con cache"""
        module_key = str(module_path)

        if module_key in self._schema_cache:
            return self._schema_cache[module_key]

        try:
            parser = etree.XMLParser(
                remove_blank_text=True,
                resolve_entities=False,
                no_network=True
            )

            schema_doc = etree.parse(str(module_path), parser=parser)
            schema = etree.XMLSchema(schema_doc)

            self._schema_cache[module_key] = schema
            return schema

        except Exception as e:
            raise SchemaValidationError(
                f"Error cargando schema {module_path}: {str(e)}")

    def _prepare_xml_for_module_validation(
        self,
        xml_content: str,
        module: Union[str, SchemaModule],
        wrap_in_root: bool
    ) -> str:
        """Prepara XML para validación contra módulo específico"""
        if not wrap_in_root:
            return xml_content

        # Si el XML no tiene elemento raíz apropiado, envolverlo
        if not xml_content.strip().startswith('<rDE'):
            # Crear wrapper con namespace SIFEN
            wrapped_xml = f'''<rDE xmlns="{SIFEN_NAMESPACE_URI}">
                <dVerFor>{SIFEN_SCHEMA_VERSION}</dVerFor>
                {xml_content}
            </rDE>'''
            return wrapped_xml

        return xml_content

    def _get_module_dependencies(self, module_path: Path) -> List[ModuleDependency]:
        """Extrae dependencias de un módulo de schema"""
        module_key = str(module_path)

        if module_key in self._dependency_cache:
            return self._dependency_cache[module_key]

        dependencies = []

        try:
            # Parsear el schema para encontrar imports/includes
            parser = etree.XMLParser(remove_blank_text=True)
            schema_doc = etree.parse(str(module_path), parser=parser)

            # Buscar elementos xs:import
            for import_elem in schema_doc.xpath("//xs:import", namespaces={'xs': 'http://www.w3.org/2001/XMLSchema'}):
                schema_location = import_elem.get('schemaLocation')
                if schema_location:
                    dependencies.append(ModuleDependency(
                        source_module=module_path.name,
                        target_module=schema_location,
                        dependency_type='import',
                        is_required=True
                    ))

            # Buscar elementos xs:include
            for include_elem in schema_doc.xpath("//xs:include", namespaces={'xs': 'http://www.w3.org/2001/XMLSchema'}):
                schema_location = include_elem.get('schemaLocation')
                if schema_location:
                    dependencies.append(ModuleDependency(
                        source_module=module_path.name,
                        target_module=schema_location,
                        dependency_type='include',
                        is_required=True
                    ))

            self._dependency_cache[module_key] = dependencies
            return dependencies

        except Exception as e:
            logger.warning(
                f"Error extrayendo dependencias de {module_path}: {str(e)}")
            return []


# ================================
# FUNCIONES DE CONVENIENCIA
# ================================

def validate_xml_against_sifen_module(
    xml_content: str,
    module_name: str,
    schema_base_path: Optional[Path] = None
) -> ValidationResult:
    """
    Función de conveniencia para validar XML contra módulo SIFEN específico

    Args:
        xml_content: Contenido XML a validar
        module_name: Nombre del módulo de schema
        schema_base_path: Ruta base de schemas (opcional)

    Returns:
        ValidationResult: Resultado de la validación

    Examples:
        >>> result = validate_xml_against_sifen_module(xml, "basic_types")
        >>> assert result.is_valid == True
    """
    helper = SchemaTestHelpers(schema_base_path)
    return helper.validate_against_module(xml_content, module_name)


def check_sifen_document_completeness(xml_content: str) -> Tuple[bool, Dict[str, bool]]:
    """
    Verifica completitud de documento SIFEN según elementos requeridos

    Args:
        xml_content: Contenido XML del documento

    Returns:
        Tuple[bool, Dict[str, bool]]: (es_completo, mapa_de_elementos)

    Examples:
        >>> is_complete, element_map = check_sifen_document_completeness(xml)
        >>> assert is_complete == True
        >>> assert element_map["//dRUCEmi"] == True
    """
    helper = SchemaTestHelpers()
    results = helper.extract_and_validate_sifen_elements(
        xml_content, REQUIRED_SIFEN_ELEMENTS)

    element_map = {xpath: result.is_valid for xpath, result in results.items()}
    is_complete = all(element_map.values())

    return is_complete, element_map


def validate_sifen_document_type(xml_content: str, expected_type: str) -> ValidationResult:
    """
    Función de conveniencia para validar documento según su tipo SIFEN

    Args:
        xml_content: Contenido XML del documento
        expected_type: Tipo de documento esperado (01, 04, 05, 06, 07)

    Returns:
        ValidationResult: Resultado de la validación

    Examples:
        >>> result = validate_sifen_document_type(factura_xml, "01")
        >>> assert result.is_valid == True
    """
    helper = SchemaTestHelpers()
    return helper.validate_document_type_structure(xml_content, expected_type)
