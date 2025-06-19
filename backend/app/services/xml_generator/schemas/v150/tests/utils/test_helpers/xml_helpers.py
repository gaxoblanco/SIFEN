"""
Módulo: XML Test Helpers

Propósito:
    Proporciona utilidades para manipulación, validación y comparación
    de documentos XML en el contexto de testing de schemas SIFEN v150.
    
    Este módulo se enfoca específicamente en operaciones XML seguras,
    parsing robusto, extracción de elementos y formateo para debugging.

Funcionalidades principales:
    - Parsing seguro de XML con manejo de errores
    - Extracción de elementos usando XPath
    - Comparación de estructuras XML
    - Formateo para debugging
    - Validación básica contra schemas

Dependencias:
    - lxml: Manipulación XML robusta
    - pathlib: Manejo de rutas de archivos

Uso:
    from .xml_helpers import XMLTestHelpers
    
    # Parsear XML de forma segura
    success, tree, errors = XMLTestHelpers.parse_xml_safely(xml_content)
    
    # Extraer elementos específicos
    ruc = XMLTestHelpers.extract_element_text(tree, "//dRUCEmi")
    
    # Comparar estructuras
    same_structure = XMLTestHelpers.compare_xml_structure(xml1, xml2)

Autor: Sistema SIFEN
Versión: 1.0.0
Fecha: 2025-06-17
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from lxml import etree


# ================================
# CONFIGURACIÓN DEL MÓDULO
# ================================

logger = logging.getLogger(__name__)


class XMLParsingError(Exception):
    """Excepción personalizada para errores de parsing XML"""
    pass


class XMLValidationError(Exception):
    """Excepción personalizada para errores de validación XML"""
    pass

# ================================
# CONSTANTES SIFEN
# ================================


SIFEN_NAMESPACES = {
    'sifen': 'http://ekuatia.set.gov.py/sifen/xsd',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

DEFAULT_XML_ENCODING = 'utf-8'

# ================================
# CLASE PRINCIPAL: XMLTestHelpers
# ================================


class XMLTestHelpers:
    """
    Utilidades para manipulación y validación XML en tests

    Esta clase proporciona métodos estáticos para operaciones XML
    comunes en el contexto de testing, con énfasis en robustez
    y manejo de errores.
    """

    @staticmethod
    def parse_xml_safely(xml_content: str) -> Tuple[bool, Optional[etree._Element], List[str]]:
        """
        Parsea XML de forma segura con manejo completo de errores

        Realiza validación previa del contenido, limpieza de caracteres
        problemáticos y parsing robusto con captura de errores específicos.

        Args:
            xml_content (str): Contenido XML como string

        Returns:
            Tuple[bool, Optional[etree._Element], List[str]]:
                - bool: True si el parsing fue exitoso
                - etree._Element: Árbol XML parseado (None si falló)
                - List[str]: Lista de errores encontrados

        Examples:
            >>> success, tree, errors = XMLTestHelpers.parse_xml_safely("<root><test>valor</test></root>")
            >>> assert success == True
            >>> assert tree is not None
            >>> assert len(errors) == 0

            >>> success, tree, errors = XMLTestHelpers.parse_xml_safely("<malformed>")
            >>> assert success == False
            >>> assert tree is None
            >>> assert len(errors) > 0
        """
        errors = []

        try:
            # Validación previa del contenido
            if not xml_content:
                errors.append("Contenido XML vacío o None")
                return False, None, errors

            if not isinstance(xml_content, (str, bytes)):
                errors.append(
                    f"Contenido debe ser string, recibido: {type(xml_content)}")
                return False, None, errors

            # Limpiar contenido XML
            clean_xml = xml_content.strip()

            if not clean_xml:
                errors.append("Contenido XML vacío después de limpieza")
                return False, None, errors

            # Verificar que empiece con declaración XML o elemento raíz
            if not (clean_xml.startswith('<?xml') or clean_xml.startswith('<')):
                errors.append("Contenido no parece ser XML válido")
                return False, None, errors

            # Crear parser XML con configuración segura
            parser = etree.XMLParser(
                remove_blank_text=True,  # Remover espacios en blanco
                # No resolver entidades externas (seguridad)
                resolve_entities=False,
                no_network=True,         # No acceso a red (seguridad)
                dtd_validation=False,    # No validar DTD (seguridad)
                load_dtd=False          # No cargar DTD (seguridad)
            )

            # Parsear XML con encoding UTF-8
            try:
                tree = etree.fromstring(
                    clean_xml.encode('utf-8'), parser=parser)
            except UnicodeEncodeError:
                # Intentar con el string directamente si hay problemas de encoding
                tree = etree.fromstring(clean_xml, parser=parser)

            # Validación adicional del árbol parseado
            if tree is None:
                errors.append("Árbol XML parseado es None")
                return False, None, errors

            logger.debug(
                f"XML parseado exitosamente. Elemento raíz: {tree.tag}")
            return True, tree, errors

        except etree.XMLSyntaxError as e:
            error_msg = f"Error de sintaxis XML: {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
            return False, None, errors

        except ValueError as e:
            error_msg = f"Error de valor en XML: {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
            return False, None, errors

        except Exception as e:
            error_msg = f"Error inesperado al parsear XML: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, None, errors

    @staticmethod
    def extract_element_text(xml_tree: etree._Element, xpath: str, default: Optional[str] = None, namespaces: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Extrae texto de un elemento usando expresión XPath

        Proporciona extracción robusta con manejo de namespaces,
        múltiples elementos y valores por defecto.

        Args:
            xml_tree (etree._Element): Árbol XML parseado
            xpath (str): Expresión XPath para localizar el elemento
            default (Optional[str]): Valor por defecto si no se encuentra el elemento

        Returns:
            Optional[str]: Texto del elemento encontrado, default, o None

        Examples:
            >>> tree = etree.fromstring("<root><test>valor</test></root>")
            >>> text = XMLTestHelpers.extract_element_text(tree, "//test")
            >>> assert text == "valor"

            >>> text = XMLTestHelpers.extract_element_text(tree, "//inexistente", "default")
            >>> assert text == "default"
        """
        if xml_tree is None:
            logger.warning("Árbol XML es None, no se puede extraer elemento")
            return default

        if not xpath:
            logger.warning("XPath vacío, no se puede extraer elemento")
            return default

        try:
            # Ejecutar XPath
            elements = xml_tree.xpath(xpath, namespaces=namespaces)

            if not elements:
                logger.debug(
                    f"No se encontraron elementos para XPath: {xpath}")
                return default

            # Si hay múltiples elementos, tomar el primero
            if len(elements) > 1:
                logger.debug(
                    f"Se encontraron {len(elements)} elementos para XPath {xpath}, tomando el primero")

            element = elements[0]

            # Extraer texto según el tipo de resultado
            if hasattr(element, 'text'):
                # Es un elemento XML
                text = element.text
            elif isinstance(element, str):
                # Es un valor de atributo o texto directo
                text = element
            else:
                # Convertir a string como último recurso
                text = str(element)

            # Retornar texto limpio o default si está vacío
            return text.strip() if text else default

        except etree.XPathEvalError as e:
            error_msg = f"Error en expresión XPath '{xpath}': {str(e)}"
            logger.warning(error_msg)
            return default

        except Exception as e:
            error_msg = f"Error inesperado extrayendo elemento con XPath '{xpath}': {str(e)}"
            logger.warning(error_msg)
            return default

    @staticmethod
    def extract_multiple_elements(xml_tree: etree._Element, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List[str]:
        """
        Extrae texto de múltiples elementos que coincidan con el XPath

        Args:
            xml_tree (etree._Element): Árbol XML parseado
            xpath (str): Expresión XPath

        Returns:
            List[str]: Lista de textos de todos los elementos encontrados

        Examples:
            >>> xml = "<root><item>A</item><item>B</item><item>C</item></root>"
            >>> tree = etree.fromstring(xml)
            >>> items = XMLTestHelpers.extract_multiple_elements(tree, "//item")
            >>> assert items == ["A", "B", "C"]
        """
        if xml_tree is None or not xpath:
            return []

        try:
            elements = xml_tree.xpath(xpath, namespaces=namespaces)
            results = []

            for element in elements:
                if hasattr(element, 'text') and element.text:
                    results.append(element.text.strip())
                elif isinstance(element, str):
                    results.append(element.strip())
                else:
                    results.append(str(element).strip())

            return results

        except Exception as e:
            logger.warning(
                f"Error extrayendo múltiples elementos con XPath '{xpath}': {str(e)}")
            return []

    @staticmethod
    def compare_xml_structure(xml1: str, xml2: str, ignore_text: bool = True, ignore_attributes: bool = False) -> bool:
        """
        Compara la estructura de dos documentos XML

        Permite comparar solo la estructura (elementos y jerarquía)
        o incluir atributos y contenido de texto según los parámetros.

        Args:
            xml1 (str): Primer documento XML
            xml2 (str): Segundo documento XML
            ignore_text (bool): Si True, ignora el contenido de texto de los elementos
            ignore_attributes (bool): Si True, ignora los atributos de los elementos

        Returns:
            bool: True si las estructuras son equivalentes

        Examples:
            >>> xml1 = "<root><child>texto1</child></root>"
            >>> xml2 = "<root><child>texto2</child></root>"
            >>> assert XMLTestHelpers.compare_xml_structure(xml1, xml2, ignore_text=True) == True
            >>> assert XMLTestHelpers.compare_xml_structure(xml1, xml2, ignore_text=False) == False
        """
        def normalize_element(element, ignore_text: bool, ignore_attributes: bool) -> Dict[str, Any]:
            """Convierte un elemento XML a estructura comparable"""
            result = {
                'tag': element.tag,
                'children': []
            }

            # Incluir atributos si no se ignoran
            if not ignore_attributes:
                result['attributes'] = dict(sorted(element.attrib.items()))

            # Incluir texto si no se ignora
            if not ignore_text and element.text:
                result['text'] = element.text.strip()

            # Procesar elementos hijos
            for child in element:
                result['children'].append(normalize_element(
                    child, ignore_text, ignore_attributes))

            # Ordenar hijos por tag para comparación consistente
            result['children'].sort(key=lambda x: x['tag'])

            return result

        try:
            # Parsear ambos XMLs
            success1, tree1, errors1 = XMLTestHelpers.parse_xml_safely(xml1)
            success2, tree2, errors2 = XMLTestHelpers.parse_xml_safely(xml2)

            if not success1:
                logger.warning(f"Error parseando primer XML: {errors1}")
                return False

            if not success2:
                logger.warning(f"Error parseando segundo XML: {errors2}")
                return False

            # Normalizar y comparar estructuras
            structure1 = normalize_element(
                tree1, ignore_text, ignore_attributes)
            structure2 = normalize_element(
                tree2, ignore_text, ignore_attributes)

            return structure1 == structure2

        except Exception as e:
            logger.error(f"Error comparando estructuras XML: {str(e)}")
            return False

    @staticmethod
    def format_xml_pretty(xml_content: str, encoding: str = 'unicode', indent: str = "  ") -> str:
        """
        Formatea XML con indentación para mejor legibilidad

        Args:
            xml_content (str): Contenido XML a formatear
            encoding (str): Codificación de salida ('unicode' o 'utf-8')
            indent (str): String de indentación (por defecto 2 espacios)

        Returns:
            str: XML formateado con indentación

        Examples:
            >>> xml = "<root><child>valor</child></root>"
            >>> formatted = XMLTestHelpers.format_xml_pretty(xml)
            >>> assert "  <child>" in formatted
        """
        if not xml_content:
            logger.warning("Contenido XML vacío para formatear")
            return xml_content or ""

        try:
            success, tree, errors = XMLTestHelpers.parse_xml_safely(
                xml_content)

            if not success or tree is None:
                logger.warning(f"No se pudo formatear XML, errores: {errors}")
                return xml_content

            # Aplicar indentación
            etree.indent(tree, space=indent)

            # Convertir a string con encoding apropiado
            if encoding == 'unicode':
                return etree.tostring(tree)
            else:
                return etree.tostring(tree).decode(encoding)

        except Exception as e:
            logger.warning(f"Error formateando XML: {str(e)}")
            return xml_content

    @staticmethod
    def get_xml_validation_errors(xml_content: str, schema_path: Union[str, Path]) -> List[str]:
        """
        Obtiene errores detallados de validación XML contra schema XSD

        Args:
            xml_content (str): Contenido XML a validar
            schema_path (Union[str, Path]): Ruta al archivo de schema XSD

        Returns:
            List[str]: Lista de errores de validación encontrados

        Examples:
            >>> xml = "<invalid>content</invalid>"
            >>> errors = XMLTestHelpers.get_xml_validation_errors(xml, "schema.xsd")
            >>> assert len(errors) > 0  # Debería tener errores de validación
        """
        errors = []

        try:
            # Convertir ruta a Path object
            if isinstance(schema_path, str):
                schema_path = Path(schema_path)

            # Verificar que existe el schema
            if not schema_path.exists():
                errors.append(
                    f"Archivo de schema no encontrado: {schema_path}")
                return errors

            # Parsear XML de entrada
            success, xml_tree, parse_errors = XMLTestHelpers.parse_xml_safely(
                xml_content)

            if not success:
                errors.extend(
                    [f"Error parsing XML: {error}" for error in parse_errors])
                return errors

            # Cargar y parsear schema XSD
            try:
                # Crear parser para schema
                parser = etree.XMLParser(
                    remove_blank_text=True,
                    resolve_entities=False,
                    no_network=True,
                    dtd_validation=False,
                    load_dtd=False
                )

                with open(schema_path, 'r', encoding='utf-8') as schema_file:
                    schema_doc = etree.parse(schema_file, parser=parser)
                    schema = etree.XMLSchema(schema_doc)
            except Exception as e:
                errors.append(f"Error cargando schema {schema_path}: {str(e)}")
                return errors

            # Realizar validación
            is_valid = schema.validate(xml_tree)

            if not is_valid:
                # Recopilar errores de validación
                for error in schema.error_log:
                    error_msg = f"Línea {error.line}: {error.message}"
                    errors.append(error_msg)

            logger.debug(
                f"Validación XML completada. Válido: {is_valid}, Errores: {len(errors)}")

        except Exception as e:
            error_msg = f"Error inesperado en validación XML: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

        return errors

    @staticmethod
    def element_exists(xml_tree: etree._Element, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> bool:
        """
        Verifica si existe al menos un elemento que coincida con el XPath

        Args:
            xml_tree (etree._Element): Árbol XML parseado
            xpath (str): Expresión XPath a evaluar

        Returns:
            bool: True si existe al menos un elemento

        Examples:
            >>> tree = etree.fromstring("<root><test>valor</test></root>")
            >>> assert XMLTestHelpers.element_exists(tree, "//test") == True
            >>> assert XMLTestHelpers.element_exists(tree, "//inexistente") == False
        """
        if xml_tree is None or not xpath:
            return False

        try:
            elements = xml_tree.xpath(xpath, namespaces=namespaces)
            return len(elements) > 0
        except Exception as e:
            logger.warning(
                f"Error verificando existencia de elemento con XPath '{xpath}': {str(e)}")
            return False

    @staticmethod
    def count_elements(xml_tree: etree._Element, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> int:
        """
        Cuenta el número de elementos que coinciden con el XPath

        Args:
            xml_tree (etree._Element): Árbol XML parseado
            xpath (str): Expresión XPath a evaluar

        Returns:
            int: Número de elementos encontrados

        Examples:
            >>> xml = "<root><item>1</item><item>2</item><item>3</item></root>"
            >>> tree = etree.fromstring(xml)
            >>> assert XMLTestHelpers.count_elements(tree, "//item") == 3
        """
        if xml_tree is None or not xpath:
            return 0

        try:
            elements = xml_tree.xpath(xpath, namespaces=namespaces)
            return len(elements)
        except Exception as e:
            logger.warning(
                f"Error contando elementos con XPath '{xpath}': {str(e)}")
            return 0

    @staticmethod
    def extract_element_attribute(xml_tree: etree._Element, xpath: str, attribute: str,
                                  default: Optional[str] = None, namespaces: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Extrae el valor de un atributo específico de un elemento

        Args:
            xml_tree (etree._Element): Árbol XML parseado
            xpath (str): Expresión XPath para localizar el elemento
            attribute (str): Nombre del atributo a extraer
            default (Optional[str]): Valor por defecto si no se encuentra
            namespaces (Optional[Dict[str, str]]): Diccionario de namespaces

        Returns:
            Optional[str]: Valor del atributo o default

        Examples:
            >>> xml = '<root><item id="123">valor</item></root>'
            >>> tree = etree.fromstring(xml)
            >>> attr = XMLTestHelpers.extract_element_attribute(tree, "//item", "id")
            >>> assert attr == "123"
        """
        if xml_tree is None or not xpath or not attribute:
            return default

        try:
            elements = xml_tree.xpath(xpath, namespaces=namespaces)

            if not elements:
                return default

            element = elements[0]

            if hasattr(element, 'get'):
                return element.get(attribute, default)
            else:
                return default

        except Exception as e:
            logger.warning(
                f"Error extrayendo atributo '{attribute}' con XPath '{xpath}': {str(e)}")
            return default

    @staticmethod
    def validate_xml_against_xsd(xml_content: str, xsd_path: Union[str, Path]) -> Tuple[bool, List[str]]:
        """
        Valida XML contra un schema XSD específico

        Args:
            xml_content (str): Contenido XML a validar
            xsd_path (Union[str, Path]): Ruta al archivo XSD

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores)

        Examples:
            >>> xml = "<root><valid>content</valid></root>"
            >>> valid, errors = XMLTestHelpers.validate_xml_against_xsd(xml, "schema.xsd")
            >>> assert isinstance(valid, bool)
            >>> assert isinstance(errors, list)
        """
        try:
            errors = XMLTestHelpers.get_xml_validation_errors(
                xml_content, xsd_path)
            is_valid = len(errors) == 0
            return is_valid, errors
        except Exception as e:
            error_msg = f"Error validando XML contra XSD: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]

    @staticmethod
    def get_root_element_info(xml_tree: etree._Element) -> Dict[str, Any]:
        """
        Obtiene información del elemento raíz del XML

        Args:
            xml_tree (etree._Element): Árbol XML parseado

        Returns:
            Dict[str, Any]: Información del elemento raíz

        Examples:
            >>> xml = '<root xmlns="http://example.com" version="1.0"><child/></root>'
            >>> tree = etree.fromstring(xml)
            >>> info = XMLTestHelpers.get_root_element_info(tree)
            >>> assert info['tag'] == '{http://example.com}root'
        """
        if xml_tree is None:
            return {}

        try:
            return {
                'tag': xml_tree.tag,
                'attributes': dict(xml_tree.attrib),
                'namespace': xml_tree.nsmap,
                'children_count': len(xml_tree),
                'text_content': xml_tree.text.strip() if xml_tree.text else None
            }
        except Exception as e:
            logger.warning(
                f"Error obteniendo información del elemento raíz: {str(e)}")
            return {}
# ================================
# UTILIDADES ADICIONALES
# ================================


def validate_xml_basic_structure(xml_content: str, required_elements: List[str]) -> Tuple[bool, List[str]]:
    """
    Validación básica de estructura XML verificando elementos requeridos

    Esta función es una utilidad de conveniencia que combina parsing
    y verificación de elementos requeridos en una sola operación.

    Args:
        xml_content (str): Contenido XML a validar
        required_elements (List[str]): Lista de XPaths de elementos requeridos

    Returns:
        Tuple[bool, List[str]]: (es_válido, lista_de_errores)

    Examples:
        >>> xml = "<root><name>test</name><value>123</value></root>"
        >>> valid, errors = validate_xml_basic_structure(xml, ["//name", "//value"])
        >>> assert valid == True
        >>> assert len(errors) == 0
    """
    errors = []

    # Parsear XML
    success, tree, parse_errors = XMLTestHelpers.parse_xml_safely(xml_content)

    if not success or tree is None:
        errors.extend(parse_errors)
        return False, errors

    # Verificar elementos requeridos
    for xpath in required_elements:
        if not XMLTestHelpers.element_exists(tree, xpath):
            errors.append(f"Elemento requerido no encontrado: {xpath}")

    is_valid = len(errors) == 0
    return is_valid, errors


def compare_xml_values(xml1: str, xml2: str, value_xpaths: List[str]) -> Dict[str, bool]:
    """
    Compara valores específicos entre dos documentos XML

    Args:
        xml1 (str): Primer documento XML
        xml2 (str): Segundo documento XML  
        value_xpaths (List[str]): Lista de XPaths de valores a comparar

    Returns:
        Dict[str, bool]: Diccionario con resultados de comparación por XPath

    Examples:
        >>> xml1 = "<root><name>test</name><value>123</value></root>"
        >>> xml2 = "<root><name>test</name><value>456</value></root>"
        >>> results = compare_xml_values(xml1, xml2, ["//name", "//value"])
        >>> assert results["//name"] == True
        >>> assert results["//value"] == False
    """
    results = {}

    # Parsear ambos XMLs
    success1, tree1, _ = XMLTestHelpers.parse_xml_safely(xml1)
    success2, tree2, _ = XMLTestHelpers.parse_xml_safely(xml2)

    if not success1 or not success2:
        # Si cualquiera falla, todos los resultados son False
        return {xpath: False for xpath in value_xpaths}
    if tree1 is None or tree2 is None:
        # Si cualquiera falla, todos los resultados son False
        return {xpath: False for xpath in value_xpaths}

    # Comparar cada valor
    for xpath in value_xpaths:
        value1 = XMLTestHelpers.extract_element_text(tree1, xpath)
        value2 = XMLTestHelpers.extract_element_text(tree2, xpath)
        results[xpath] = value1 == value2

    return results


def extract_sifen_document_info(xml_content: str) -> Dict[str, Optional[str]]:
    """
    Extrae información básica de un documento SIFEN

    Args:
        xml_content (str): Contenido XML del documento SIFEN

    Returns:
        Dict[str, Optional[str]]: Información extraída del documento

    Examples:
        >>> xml = '''<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
        ...     <DE><dTiDE>1</dTiDE><dRUCEmi>12345678</dRUCEmi></DE>
        ... </rDE>'''
        >>> info = extract_sifen_document_info(xml)
        >>> assert info['tipo_documento'] == '1'
        >>> assert info['ruc_emisor'] == '12345678'
    """
    success, tree, errors = XMLTestHelpers.parse_xml_safely(xml_content)

    if not success or tree is None:
        logger.warning(f"Error parseando documento SIFEN: {errors}")
        return {}

    # Información básica del documento SIFEN
    info = {
        'tipo_documento': XMLTestHelpers.extract_element_text(tree, "//dTiDE", namespaces=SIFEN_NAMESPACES),
        'ruc_emisor': XMLTestHelpers.extract_element_text(tree, "//dRUCEmi", namespaces=SIFEN_NAMESPACES),
        'numero_documento': XMLTestHelpers.extract_element_text(tree, "//dNumDoc", namespaces=SIFEN_NAMESPACES),
        'serie_documento': XMLTestHelpers.extract_element_text(tree, "//dSerie", namespaces=SIFEN_NAMESPACES),
        'fecha_emision': XMLTestHelpers.extract_element_text(tree, "//dFeEmiDE", namespaces=SIFEN_NAMESPACES),
        'condicion_operacion': XMLTestHelpers.extract_element_text(tree, "//iTiOpe", namespaces=SIFEN_NAMESPACES),
        'moneda': XMLTestHelpers.extract_element_text(tree, "//cMoneOpe", namespaces=SIFEN_NAMESPACES)
    }

    return info


def validate_sifen_structure(xml_content: str) -> Tuple[bool, List[str]]:
    """
    Validación básica de estructura para documentos SIFEN

    Args:
        xml_content (str): Contenido XML del documento SIFEN

    Returns:
        Tuple[bool, List[str]]: (es_válido, lista_de_errores)

    Examples:
        >>> xml = '''<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
        ...     <DE><dTiDE>1</dTiDE><dRUCEmi>12345678</dRUCEmi></DE>
        ... </rDE>'''
        >>> valid, errors = validate_sifen_structure(xml)
        >>> assert isinstance(valid, bool)
    """
    errors = []

    # Elementos requeridos básicos para cualquier documento SIFEN
    required_elements = [
        "//dTiDE",      # Tipo de documento
        "//dRUCEmi",    # RUC del emisor
        "//dFeEmiDE"    # Fecha de emisión
    ]

    return validate_xml_basic_structure(xml_content, required_elements)
