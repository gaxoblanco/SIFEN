"""
Validador de estructura básica XML para SIFEN v150

Este módulo proporciona validación rápida de estructura XML básica sin
dependencia de esquemas XSD. Es la primera línea de validación que verifica
que el documento tenga la estructura mínima requerida antes de proceder
con validaciones más costosas.

Responsabilidades:
- Verificar que el XML sea well-formed (parseable)
- Validar namespace SIFEN correcto
- Verificar elemento raíz 'rDE'
- Validar atributos obligatorios
- Verificar elementos mínimos requeridos

Uso:
    from .structure_validator import StructureValidator
    
    validator = StructureValidator()
    is_valid, errors = validator.validate(xml_content)

Características:
- Validación rápida sin carga de XSD
- Fail-fast para errores críticos de estructura
- Mensajes de error específicos y actionables
- Búsqueda eficiente de elementos

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
"""

from typing import Tuple, List, Optional
from lxml import etree

from .constants import (
    SIFEN_NAMESPACE,
    REQUIRED_ELEMENTS,
    REQUIRED_EMISOR_ELEMENTS,
    REQUIRED_OPERACION_ELEMENTS,
    REQUIRED_ATTRIBUTES,
    REQUIRED_DE_ATTRIBUTES,
    SIFEN_VERSION
)


# =====================================
# VALIDADOR DE ESTRUCTURA PRINCIPAL
# =====================================

class StructureValidator:
    """
    Validador de estructura básica para documentos XML SIFEN v150

    Realiza validaciones estructurales rápidas sin necesidad de cargar
    esquemas XSD. Es ideal para fail-fast validation antes de validaciones
    más costosas.

    La validación sigue este orden:
    1. XML well-formed (parseable por lxml)
    2. Namespace SIFEN correcto
    3. Elemento raíz 'rDE'
    4. Atributos obligatorios presentes
    5. Elementos mínimos presentes
    """

    def __init__(self):
        """Inicializa el validador de estructura"""
        # Cache para namespaces encontrados (optimización)
        self._namespace_cache = {}

        # Configuración del parser XML optimizada para validación rápida
        self._parser = etree.XMLParser(
            remove_blank_text=False,  # Preservar para análisis completo
            remove_comments=False,    # Preservar comentarios
            strip_cdata=False,        # Preservar CDATA
            recover=False             # Modo estricto, no intentar recuperar
        )

    def validate(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Valida la estructura básica del XML SIFEN

        Realiza todas las validaciones estructurales necesarias para
        determinar si el documento tiene la estructura mínima válida.

        Args:
            xml_content: Contenido XML a validar como string

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores)

        Raises:
            No lanza excepciones - todos los errores se capturan y retornan

        Example:
            >>> validator = StructureValidator()
            >>> xml = '<?xml version="1.0"?><rDE xmlns="...">...</rDE>'
            >>> is_valid, errors = validator.validate(xml)
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Error: {error}")
        """
        errors = []

        # 1. Verificar que sea XML well-formed
        try:
            xml_doc = etree.fromstring(
                xml_content.encode('utf-8'), self._parser)
        except etree.XMLSyntaxError as e:
            return False, [f"XML mal formado: {str(e)}"]
        except Exception as e:
            return False, [f"Error parseando XML: {str(e)}"]

        # 2. Validar namespace SIFEN
        namespace_errors = self._validate_namespace(xml_doc)
        errors.extend(namespace_errors)

        # 3. Validar elemento raíz
        root_errors = self._validate_root_element(xml_doc)
        errors.extend(root_errors)

        # 4. Validar atributos obligatorios
        attribute_errors = self._validate_required_attributes(xml_doc)
        errors.extend(attribute_errors)

        # 5. Validar elementos obligatorios
        element_errors = self._validate_required_elements(xml_doc)
        errors.extend(element_errors)

        # 6. Validaciones específicas SIFEN adicionales
        sifen_errors = self._validate_sifen_specifics(xml_doc)
        errors.extend(sifen_errors)

        return len(errors) == 0, errors

    def _validate_namespace(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida que el documento use el namespace SIFEN correcto

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de namespace
        """
        errors = []

        # Obtener namespace por defecto del elemento raíz
        default_namespace = xml_doc.nsmap.get(None)

        if default_namespace != SIFEN_NAMESPACE:
            errors.append(
                f"Namespace incorrecto. "
                f"Encontrado: '{default_namespace}', "
                f"Esperado: '{SIFEN_NAMESPACE}'"
            )

        # Verificar que no haya namespace faltante
        if default_namespace is None:
            errors.append(
                f"Namespace por defecto faltante. "
                f"Se requiere: '{SIFEN_NAMESPACE}'"
            )

        # Verificar declaración xmlns en el elemento raíz
        if 'xmlns' not in xml_doc.attrib and default_namespace is None:
            errors.append(
                "Declaración de namespace xmlns faltante en elemento raíz")

        return errors

    def _validate_root_element(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida que el elemento raíz sea 'rDE'

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores del elemento raíz
        """
        errors = []

        # Obtener nombre del elemento sin namespace
        local_name = etree.QName(xml_doc).localname

        if local_name != 'rDE':
            errors.append(
                f"Elemento raíz incorrecto. "
                f"Encontrado: '{local_name}', "
                f"Esperado: 'rDE'"
            )

        return errors

    def _validate_required_attributes(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida atributos obligatorios del elemento raíz

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de atributos faltantes
        """
        errors = []

        # Validar atributos del elemento raíz (rDE)
        for attr in REQUIRED_ATTRIBUTES:
            if attr not in xml_doc.attrib:
                errors.append(
                    f"Atributo obligatorio faltante en rDE: '{attr}'")

        # Validar valor del atributo version si existe
        if 'version' in xml_doc.attrib:
            version_value = xml_doc.attrib['version']
            if version_value != SIFEN_VERSION:
                errors.append(
                    f"Versión incorrecta en atributo 'version'. "
                    f"Encontrado: '{version_value}', "
                    f"Esperado: '{SIFEN_VERSION}'"
                )

        # Validar atributos del elemento DE si existe
        de_element = self._find_element_by_name(xml_doc, 'DE')
        if de_element is not None:
            for attr in REQUIRED_DE_ATTRIBUTES:
                if attr not in de_element.attrib:
                    errors.append(
                        f"Atributo obligatorio faltante en DE: '{attr}'")

        return errors

    def _validate_required_elements(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida que estén presentes los elementos obligatorios

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de elementos faltantes
        """
        errors = []

        # Convertir documento a string para búsqueda eficiente
        xml_text = etree.tostring(xml_doc).decode('utf-8')

        # Validar elementos básicos obligatorios
        missing_basic = self._check_missing_elements(
            xml_text, REQUIRED_ELEMENTS)
        for element in missing_basic:
            errors.append(f"Elemento obligatorio faltante: '{element}'")

        # Validar elementos específicos del emisor si gEmis existe
        if self._element_exists_in_text(xml_text, 'gEmis'):
            missing_emisor = self._check_missing_elements(
                xml_text, REQUIRED_EMISOR_ELEMENTS)
            for element in missing_emisor:
                errors.append(
                    f"Elemento obligatorio faltante en emisor: '{element}'")

        # Validar elementos específicos de operación si gOpDE existe
        if self._element_exists_in_text(xml_text, 'gOpDE'):
            missing_operacion = self._check_missing_elements(
                xml_text, REQUIRED_OPERACION_ELEMENTS)
            for element in missing_operacion:
                errors.append(
                    f"Elemento obligatorio faltante en operación: '{element}'")

        return errors

    def _validate_sifen_specifics(self, xml_doc: etree._Element) -> List[str]:
        """
        Validaciones específicas adicionales para SIFEN

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores específicos SIFEN
        """
        errors = []

        # Validar que dVerFor tenga el valor correcto
        ver_for_element = self._find_element_by_name(xml_doc, 'dVerFor')
        if ver_for_element is not None and ver_for_element.text:
            if ver_for_element.text.strip() != SIFEN_VERSION:
                errors.append(
                    f"Versión de formato incorrecta en dVerFor. "
                    f"Encontrado: '{ver_for_element.text.strip()}', "
                    f"Esperado: '{SIFEN_VERSION}'"
                )

        # Validar estructura jerárquica básica: rDE > DE
        de_element = self._find_element_by_name(xml_doc, 'DE')
        if de_element is None:
            errors.append("Elemento DE no encontrado como hijo de rDE")
        elif de_element.getparent() != xml_doc:
            errors.append("Elemento DE debe ser hijo directo de rDE")

        # Validar que al menos existe un gCamItem
        xml_text = etree.tostring(xml_doc).decode('utf-8')
        if not self._element_exists_in_text(xml_text, 'gCamItem'):
            errors.append(
                "Documento debe contener al menos un elemento gCamItem (ítem)")

        return errors

    def _find_element_by_name(self, parent: etree._Element, element_name: str) -> Optional[etree._Element]:
        """
        Busca un elemento por nombre local (sin namespace)

        Args:
            parent: Elemento padre donde buscar
            element_name: Nombre del elemento a buscar

        Returns:
            Elemento encontrado o None
        """
        # Usar xpath para búsqueda eficiente por nombre local
        elements = parent.xpath(f'.//*[local-name()="{element_name}"]')
        return elements[0] if elements else None

    def _check_missing_elements(self, xml_text: str, required_elements: List[str]) -> List[str]:
        """
        Verifica qué elementos de una lista están faltantes en el XML

        Args:
            xml_text: Contenido XML como string
            required_elements: Lista de elementos requeridos

        Returns:
            Lista de elementos faltantes
        """
        missing = []

        for element in required_elements:
            if not self._element_exists_in_text(xml_text, element):
                missing.append(element)

        return missing

    def _element_exists_in_text(self, xml_text: str, element_name: str) -> bool:
        """
        Verifica si un elemento existe en el texto XML

        Usa búsqueda de texto simple para eficiencia en lugar de xpath.

        Args:
            xml_text: Contenido XML como string
            element_name: Nombre del elemento a buscar

        Returns:
            True si el elemento existe
        """
        # Buscar tanto etiqueta de apertura como etiqueta self-closing
        return (f'<{element_name}>' in xml_text or
                f'<{element_name} ' in xml_text or
                f'<{element_name}/>' in xml_text)

    def validate_minimal_structure(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Validación mínima ultra-rápida para verificación inicial

        Solo verifica que sea XML válido con namespace y elemento raíz correctos.
        Útil para validación rápida antes de procesamiento más intensivo.

        Args:
            xml_content: Contenido XML a validar

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores)
        """
        errors = []

        try:
            xml_doc = etree.fromstring(
                xml_content.encode('utf-8'), self._parser)
        except etree.XMLSyntaxError as e:
            return False, [f"XML mal formado: {str(e)}"]

        # Solo validar namespace y elemento raíz
        namespace_errors = self._validate_namespace(xml_doc)
        errors.extend(namespace_errors)

        root_errors = self._validate_root_element(xml_doc)
        errors.extend(root_errors)

        return len(errors) == 0, errors

    def get_document_structure_info(self, xml_content: str) -> Optional[dict]:
        """
        Extrae información estructural del documento para debugging

        Args:
            xml_content: Contenido XML a analizar

        Returns:
            Diccionario con información estructural o None si hay error
        """
        try:
            xml_doc = etree.fromstring(
                xml_content.encode('utf-8'), self._parser)
        except:
            return None

        # Recopilar información estructural
        info = {
            'root_element': etree.QName(xml_doc).localname,
            'default_namespace': xml_doc.nsmap.get(None),
            'all_namespaces': dict(xml_doc.nsmap),
            'root_attributes': dict(xml_doc.attrib),
            'child_elements': [],
            'total_elements': 0
        }

        # Contar elementos y recopilar estructura
        for elem in xml_doc.iter():
            info['total_elements'] += 1
            if elem.getparent() == xml_doc:  # Solo hijos directos del raíz
                info['child_elements'].append(etree.QName(elem).localname)

        # Verificar presencia de elementos críticos
        xml_text = etree.tostring(xml_doc).decode('utf-8')
        critical_elements = ['DE', 'gDatGralOpe', 'gOpDE', 'gEmis', 'gCamItem']
        info['critical_elements_present'] = {
            elem: self._element_exists_in_text(xml_text, elem)
            for elem in critical_elements
        }

        return info


# =====================================
# UTILIDADES DE CONVENIENCIA
# =====================================

def quick_structure_check(xml_content: str) -> bool:
    """
    Verificación rápida de estructura válida

    Args:
        xml_content: Contenido XML a verificar

    Returns:
        True si la estructura básica es válida
    """
    validator = StructureValidator()
    is_valid, _ = validator.validate_minimal_structure(xml_content)
    return is_valid


def get_structure_errors(xml_content: str) -> List[str]:
    """
    Obtiene solo los errores de estructura sin validación completa

    Args:
        xml_content: Contenido XML a validar

    Returns:
        Lista de errores de estructura
    """
    validator = StructureValidator()
    _, errors = validator.validate(xml_content)
    return errors


def analyze_document_structure(xml_content: str) -> dict:
    """
    Analiza y retorna información estructural del documento

    Args:
        xml_content: Contenido XML a analizar

    Returns:
        Diccionario con análisis estructural
    """
    validator = StructureValidator()
    is_valid, errors = validator.validate(xml_content)
    structure_info = validator.get_document_structure_info(xml_content)

    return {
        'is_structurally_valid': is_valid,
        'structure_errors': errors,
        'structure_info': structure_info,
        'error_count': len(errors)
    }


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    'StructureValidator',
    'quick_structure_check',
    'get_structure_errors',
    'analyze_document_structure'
]
