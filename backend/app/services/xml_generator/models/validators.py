"""
validators.py - Validadores para XML SIFEN v150

Propósito:
    Módulo principal de validación que combina validación XSD, validaciones
    específicas de formato SIFEN y validaciones de negocio Paraguay.

Funcionalidades principales:
    - Validación contra esquemas XSD oficiales SIFEN v150
    - Validaciones específicas de formato (RUC, CDC, fechas, etc.)
    - Validaciones de reglas de negocio Paraguay
    - Manejo de errores detallado y estructurado
    - API simple para validación completa o granular

Autor: Sistema SIFEN
Versión: 1.0.0  
Fecha: 2025-06-29
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

# Imports para validación XSD avanzada
try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
    etree = None


# =============================================
# EXCEPCIONES CUSTOMIZADAS
# =============================================

class SifenValidationError(Exception):
    """Excepción específica para errores de validación SIFEN"""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


# =============================================
# CONFIGURACIÓN Y CONSTANTES
# =============================================

class ValidationConfig:
    """Configuración de validación SIFEN"""

    # Namespace oficial SIFEN v150
    SIFEN_NAMESPACE = "http://ekuatia.set.gov.py/sifen/xsd"

    # Patrones de validación regex
    PATTERNS = {
        'cdc': re.compile(r'^\d{44}$'),
        'ruc': re.compile(r'^\d{8,9}$'),
        'dv': re.compile(r'^\d{1}$'),
        'fecha_iso': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'),
        'numero_documento': re.compile(r'^\d{3}-\d{3}-\d{7}$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'monto': re.compile(r'^\d{1,11}(\.\d{1,8})?$'),
    }

    # Departamentos Paraguay válidos
    DEPARTAMENTOS_VALIDOS = {
        "1": "Concepción", "2": "San Pedro", "3": "Cordillera",
        "4": "Guairá", "5": "Caaguazú", "6": "Caazapá",
        "7": "Itapúa", "8": "Misiones", "9": "Paraguarí",
        "10": "Alto Paraná", "11": "Central", "12": "Ñeembucú",
        "13": "Amambay", "14": "Canindeyú", "15": "Presidente Hayes",
        "16": "Alto Paraguay", "17": "Boquerón"
    }

    # Tipos de documento válidos SIFEN v150
    TIPOS_DOCUMENTO = {
        "1": "Factura Electrónica",
        "4": "Autofactura Electrónica",
        "5": "Nota de Crédito Electrónica",
        "6": "Nota de Débito Electrónica",
        "7": "Nota de Remisión Electrónica"
    }


# =============================================
# VALIDADOR PRINCIPAL
# =============================================

class XMLValidator:
    """
    Validador XML principal para documentos SIFEN v150

    Combina validación XSD, validaciones de formato específicas SIFEN
    y validaciones de reglas de negocio de Paraguay en una API unificada.
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """Inicializa el validador"""
        self.config = config or ValidationConfig()
        self._xsd_schema = None
        self._load_xsd_schema()

    def _load_xsd_schema(self) -> None:
        """Carga el esquema XSD principal"""
        if not LXML_AVAILABLE or etree is None:
            return

        try:
            xsd_path = Path(__file__).parent / "schemas" / \
                "v150" / "DE_v150.xsd"
            if xsd_path.exists():
                with open(xsd_path, 'r', encoding='utf-8') as f:
                    parser = etree.XMLParser()
                    schema_doc = etree.parse(f, parser)
                self._xsd_schema = etree.XMLSchema(schema_doc)
        except Exception:
            self._xsd_schema = None

    def validate_xml(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Validación completa de XML SIFEN

        Args:
            xml_content: Contenido XML como string

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores)
        """
        errors = []

        # 1. Validación de estructura básica XML
        structure_valid, structure_errors = self._validate_xml_structure(
            xml_content)
        errors.extend(structure_errors)

        if not structure_valid:
            return False, errors

        # 2. Validación XSD (si está disponible)
        if self._xsd_schema:
            xsd_valid, xsd_errors = self._validate_against_xsd(xml_content)
            errors.extend(xsd_errors)

        # 3. Validaciones específicas SIFEN
        sifen_valid, sifen_errors = self._validate_sifen_specifics(xml_content)
        errors.extend(sifen_errors)

        # 4. Validaciones de reglas de negocio
        business_valid, business_errors = self._validate_business_rules(
            xml_content)
        errors.extend(business_errors)

        return len(errors) == 0, errors

    def _validate_xml_structure(self, xml_content: str) -> Tuple[bool, List[str]]:
        """Validación de estructura básica XML"""
        errors = []

        if not xml_content or not xml_content.strip():
            return False, ["XML vacío o solo espacios en blanco"]

        try:
            if LXML_AVAILABLE and etree is not None:
                parser = etree.XMLParser(recover=True)
                etree.fromstring(xml_content.encode('utf-8'), parser)
            else:
                ET.fromstring(xml_content)
        except ET.ParseError as e:
            errors.append(f"Error de sintaxis XML: {str(e)}")
            return False, errors
        except Exception as e:
            errors.append(f"Error parseando XML: {str(e)}")
            return False, errors

        if self.config.SIFEN_NAMESPACE not in xml_content:
            errors.append(
                f"Namespace SIFEN requerido: {self.config.SIFEN_NAMESPACE}")

        if not xml_content.strip().startswith('<?xml'):
            errors.append("Declaración XML faltante")

        return len(errors) == 0, errors

    def _validate_against_xsd(self, xml_content: str) -> Tuple[bool, List[str]]:
        """Validación contra esquema XSD"""
        if not self._xsd_schema or not LXML_AVAILABLE or etree is None:
            return True, []

        errors = []

        try:
            parser = etree.XMLParser(recover=True)
            xml_doc = etree.fromstring(xml_content.encode('utf-8'), parser)
            is_valid = self._xsd_schema.validate(xml_doc)

            if not is_valid:
                for error in self._xsd_schema.error_log:
                    errors.append(
                        f"Error XSD (línea {error.line}): {error.message}")

        except Exception as e:
            errors.append(f"Error en validación XSD: {str(e)}")

        return len(errors) == 0, errors

    def _validate_sifen_specifics(self, xml_content: str) -> Tuple[bool, List[str]]:
        """Validaciones específicas de formato SIFEN"""
        errors = []

        try:
            if LXML_AVAILABLE and etree is not None:
                parser = etree.XMLParser(recover=True)
                xml_doc = etree.fromstring(xml_content.encode('utf-8'), parser)
            else:
                xml_doc = ET.fromstring(xml_content)
        except:
            return False, ["No se pudo parsear XML para validaciones SIFEN"]

        # Validar CDC
        cdc_errors = self._validate_cdc_format(xml_doc)
        errors.extend(cdc_errors)

        # Validar RUCs
        ruc_errors = self._validate_ruc_formats(xml_doc)
        errors.extend(ruc_errors)

        # Validar fechas
        date_errors = self._validate_date_formats(xml_doc)
        errors.extend(date_errors)

        # Validar tipo de documento
        doc_type_errors = self._validate_document_type(xml_doc)
        errors.extend(doc_type_errors)

        return len(errors) == 0, errors

    def _validate_business_rules(self, xml_content: str) -> Tuple[bool, List[str]]:
        """Validaciones de reglas de negocio Paraguay"""
        errors = []

        try:
            if LXML_AVAILABLE and etree is not None:
                parser = etree.XMLParser(recover=True)
                xml_doc = etree.fromstring(xml_content.encode('utf-8'), parser)
            else:
                xml_doc = ET.fromstring(xml_content)
        except:
            return False, ["No se pudo parsear XML para validaciones de negocio"]

        # Validar códigos geográficos
        geo_errors = self._validate_geographic_codes(xml_doc)
        errors.extend(geo_errors)

        # Validar consistencia de totales
        total_errors = self._validate_total_consistency(xml_doc)
        errors.extend(total_errors)

        return len(errors) == 0, errors

    def _validate_cdc_format(self, xml_doc) -> List[str]:
        """Valida formato de CDC (44 dígitos)"""
        errors = []

        if LXML_AVAILABLE and etree is not None:
            de_elements = xml_doc.xpath('.//DE[@Id]')
            for de_elem in de_elements:
                cdc = de_elem.get('Id')
                if cdc and not self.config.PATTERNS['cdc'].match(cdc):
                    errors.append(
                        f"CDC inválido: '{cdc}' debe tener exactamente 44 dígitos")
        else:
            for de_elem in xml_doc.iter():
                if de_elem.tag.endswith('DE') and 'Id' in de_elem.attrib:
                    cdc = de_elem.attrib['Id']
                    if not self.config.PATTERNS['cdc'].match(cdc):
                        errors.append(
                            f"CDC inválido: '{cdc}' debe tener exactamente 44 dígitos")

        return errors

    def _validate_ruc_formats(self, xml_doc) -> List[str]:
        """Valida formatos de RUC en el documento"""
        errors = []

        ruc_fields = ['dRucEmi', 'dRucRec', 'dRUCEmi', 'dRUCRec']

        for field in ruc_fields:
            elements = self._find_elements_by_name(xml_doc, field)
            for elem in elements:
                ruc = elem.text if elem.text else ""
                if ruc and not self.validate_ruc(ruc):
                    errors.append(f"RUC inválido en {field}: '{ruc}'")

        return errors

    def _validate_date_formats(self, xml_doc) -> List[str]:
        """Valida formatos de fecha en el documento"""
        errors = []

        date_fields = ['dFeEmiDE', 'dFecEmiDI']

        for field in date_fields:
            elements = self._find_elements_by_name(xml_doc, field)
            for elem in elements:
                date_str = elem.text if elem.text else ""
                if date_str and not self.validate_date_format(date_str):
                    errors.append(f"Fecha inválida en {field}: '{date_str}'")

        return errors

    def _validate_document_type(self, xml_doc) -> List[str]:
        """Valida tipo de documento"""
        errors = []

        elements = self._find_elements_by_name(xml_doc, 'iTipDE')
        for elem in elements:
            doc_type = elem.text if elem.text else ""
            if doc_type and doc_type not in self.config.TIPOS_DOCUMENTO:
                valid_types = list(self.config.TIPOS_DOCUMENTO.keys())
                errors.append(
                    f"Tipo de documento inválido: '{doc_type}'. Válidos: {valid_types}")

        return errors

    def _validate_geographic_codes(self, xml_doc) -> List[str]:
        """Valida códigos de departamento"""
        errors = []

        dep_fields = ['cDepEmi', 'cDepRec']
        for field in dep_fields:
            elements = self._find_elements_by_name(xml_doc, field)
            for elem in elements:
                dep_code = elem.text if elem.text else ""
                if dep_code and dep_code not in self.config.DEPARTAMENTOS_VALIDOS:
                    errors.append(
                        f"Código de departamento inválido en {field}: '{dep_code}'")

        return errors

    def _validate_total_consistency(self, xml_doc) -> List[str]:
        """Valida consistencia de totales"""
        errors = []

        try:
            total_gravada = self._get_decimal_value(xml_doc, 'dTotOpeGrav')
            total_exenta = self._get_decimal_value(xml_doc, 'dTotOpeEx')
            total_iva = self._get_decimal_value(xml_doc, 'dTotIVA')
            total_general = self._get_decimal_value(xml_doc, 'dTotGralOpe')

            # Verificar que todos los valores estén presentes antes de sumar
            if all(x is not None for x in [total_gravada, total_exenta, total_iva, total_general]):
                # Type narrowing: aquí sabemos que todos son Decimal, no None
                assert total_gravada is not None
                assert total_exenta is not None
                assert total_iva is not None
                assert total_general is not None

                calculated_total = total_gravada + total_exenta + total_iva
                if abs(calculated_total - total_general) > Decimal('0.01'):
                    errors.append(
                        f"Inconsistencia en totales: "
                        f"Gravada + Exenta + IVA = {calculated_total} != Total General({total_general})"
                    )
        except Exception as e:
            errors.append(f"Error validando totales: {str(e)}")

        return errors

    def _find_elements_by_name(self, xml_doc, element_name: str) -> List:
        """Encuentra elementos por nombre"""
        if LXML_AVAILABLE and etree is not None:
            return xml_doc.xpath(f'.//*[local-name()="{element_name}"]')
        else:
            elements = []
            for elem in xml_doc.iter():
                if elem.tag.endswith(element_name) or elem.tag == element_name:
                    elements.append(elem)
            return elements

    def _get_text_value(self, xml_doc, element_name: str) -> Optional[str]:
        """Obtiene valor de texto de un elemento"""
        elements = self._find_elements_by_name(xml_doc, element_name)
        return elements[0].text if elements and elements[0].text else None

    def _get_decimal_value(self, xml_doc, element_name: str) -> Optional[Decimal]:
        """Obtiene valor decimal de un elemento"""
        text_value = self._get_text_value(xml_doc, element_name)
        if text_value:
            try:
                return Decimal(text_value)
            except:
                return None
        return None

    # =============================================
    # MÉTODOS DE VALIDACIÓN ESPECÍFICA
    # =============================================

    def validate_ruc(self, ruc: str) -> bool:
        """Valida formato de RUC paraguayo"""
        if not ruc:
            return False

        clean_ruc = ruc.replace("-", "")
        return self.config.PATTERNS['ruc'].match(clean_ruc) is not None

    def validate_dv(self, dv: str) -> bool:
        """Valida dígito verificador"""
        if not dv:
            return False

        return self.config.PATTERNS['dv'].match(dv) is not None

    def validate_date_format(self, date_str: str) -> bool:
        """Valida formato de fecha ISO 8601"""
        if not date_str:
            return False

        if not self.config.PATTERNS['fecha_iso'].match(date_str):
            return False

        try:
            datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
            return True
        except ValueError:
            return False

    def validate_amount_format(self, amount: Decimal) -> bool:
        """Valida formato de monto"""
        if amount is None:
            return False

        try:
            amount_str = str(amount)
            return self.config.PATTERNS['monto'].match(amount_str) is not None and amount >= 0
        except:
            return False

    def validate_cdc(self, cdc: str) -> bool:
        """Valida formato de CDC"""
        if not cdc:
            return False

        return self.config.PATTERNS['cdc'].match(cdc) is not None

    def validate_email(self, email: str) -> bool:
        """Valida formato de email"""
        if not email:
            return False

        return self.config.PATTERNS['email'].match(email) is not None


# =============================================
# FUNCIONES DE CONVENIENCIA GLOBALES
# =============================================

def validate_xml(xml_content: str) -> Tuple[bool, List[str]]:
    """
    Función de conveniencia para validación XML completa

    Args:
        xml_content: Contenido XML a validar

    Returns:
        Tuple[bool, List[str]]: (es_válido, lista_de_errores)
    """
    validator = XMLValidator()
    return validator.validate_xml(xml_content)


def quick_validate_ruc(ruc: str) -> bool:
    """Validación rápida de RUC paraguayo"""
    validator = XMLValidator()
    return validator.validate_ruc(ruc)


def quick_validate_cdc(cdc: str) -> bool:
    """Validación rápida de CDC"""
    validator = XMLValidator()
    return validator.validate_cdc(cdc)


def quick_validate_date(date_str: str) -> bool:
    """Validación rápida de fecha ISO 8601"""
    validator = XMLValidator()
    return validator.validate_date_format(date_str)


def validate_ruc_with_algorithm(ruc: str, dv: str) -> bool:
    """
    Validación completa de RUC con algoritmo de dígito verificador Paraguay

    Args:
        ruc: RUC de 8 dígitos sin DV
        dv: Dígito verificador

    Returns:
        bool: True si el RUC y DV son válidos
    """
    if not ruc or not dv:
        return False

    if not re.match(r'^\d{8}$', ruc) or not re.match(r'^\d{1}$', dv):
        return False

    try:
        # Algoritmo oficial Paraguay - Módulo 11
        factores = [2, 3, 4, 5, 6, 7, 2, 3]

        suma = 0
        for i, digito in enumerate(ruc):
            suma += int(digito) * factores[i]

        resto = suma % 11

        if resto < 2:
            dv_calculado = 0
        else:
            dv_calculado = 11 - resto

        return str(dv_calculado) == dv

    except (ValueError, IndexError):
        return False


# =============================================
# EXPORTACIONES DEL MÓDULO
# =============================================

__all__ = [
    "XMLValidator",
    "SifenValidationError",
    "ValidationConfig",
    "validate_xml",
    "quick_validate_ruc",
    "quick_validate_cdc",
    "quick_validate_date",
    "validate_ruc_with_algorithm"
]
