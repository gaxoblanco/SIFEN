"""
Validador de formatos específicos SIFEN v150

Este módulo proporciona validación de formatos de campos específicos SIFEN
como RUC, CDC, fechas, códigos de documento y otros campos que tienen
patrones de formato estrictos según las especificaciones SIFEN v150.

Responsabilidades:
- Validar formato CDC (44 dígitos) en atributo Id
- Validar formato RUC (8 dígitos) en campos específicos
- Validar fechas ISO 8601 en campos de fecha
- Validar códigos de documento (01, 04, 05, 06, 07)
- Validar formatos de establecimiento, punto expedición, etc.

Uso:
    from .format_validator import FormatValidator
    
    validator = FormatValidator()
    is_valid, errors = validator.validate(xml_content)
    
    # Validaciones específicas
    is_ruc_valid = validator.validate_ruc("12345678")
    is_cdc_valid = validator.validate_cdc("01234567890123456789012345678901234567890123")

Características:
- Validación granular por tipo de campo
- Búsqueda eficiente con xpath
- Mensajes de error informativos con contexto
- Métodos públicos para validaciones individuales

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
"""

import re
from typing import Tuple, List, Optional, Dict, Any
from lxml import etree

from .constants import (
    VALIDATION_PATTERNS,
    SIFEN_NAMESPACE,
    VALID_DOCUMENT_TYPES,
    VALID_OPERATION_CONDITIONS,
    VALID_BUYER_PRESENCE
)


# =====================================
# VALIDADOR DE FORMATOS PRINCIPAL
# =====================================

class FormatValidator:
    """
    Validador de formatos específicos para documentos XML SIFEN v150

    Se enfoca en validar que los campos tengan los formatos correctos
    según las especificaciones SIFEN, sin validar reglas de negocio.

    La validación incluye:
    - CDC (Código de Control): 44 dígitos numéricos
    - RUC (Registro Único Contribuyente): 8 dígitos numéricos
    - Fechas: Formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)
    - Códigos de documento: 01, 04, 05, 06, 07
    - Códigos de establecimiento y punto expedición
    - Otros campos con formatos específicos
    """

    def __init__(self):
        """Inicializa el validador de formatos"""
        # Patrones de validación precompilados desde constants
        self.patterns = VALIDATION_PATTERNS

        # Mapeo de elementos que contienen tipos específicos de datos
        self.field_mappings = self._initialize_field_mappings()

        # Configuración del parser XML optimizada
        self._parser = etree.XMLParser(
            remove_blank_text=True,
            remove_comments=True,
            strip_cdata=False
        )

    def _initialize_field_mappings(self) -> Dict[str, List[str]]:
        """
        Inicializa mapeo de tipos de campo a elementos XML

        Returns:
            Diccionario con mapeo de tipos a elementos
        """
        return {
            'ruc_fields': [
                'dRUCEmi',      # RUC del emisor
                'dRUCRec',      # RUC del receptor
                'dRUCTrans',    # RUC del transportista
                'dRUCAgen'      # RUC del agente
            ],
            'dv_fields': [
                'dDVEmi',       # DV del emisor
                'dDVRec',       # DV del receptor
                'dDVTrans',     # DV del transportista
                'dDVAgen'       # DV del agente
            ],
            'date_fields': [
                'dFeEmiDE',     # Fecha emisión documento electrónico
                'dFechaE',      # Fecha de la factura
                'dFechaSalida',  # Fecha de salida
                'dFecVencPag',  # Fecha vencimiento pago
                'dFecIniT',     # Fecha inicio transporte
                'dFecFinT',     # Fecha fin transporte
                'dFecEm'        # Fecha emisión
            ],
            'document_code_fields': [
                'iTipDE'        # Tipo de documento electrónico
            ],
            'establishment_fields': [
                'dEst'          # Establecimiento
            ],
            'expedition_point_fields': [
                'dPunExp'       # Punto de expedición
            ],
            'document_number_fields': [
                'dNumDoc'       # Número de documento
            ],
            'security_code_fields': [
                'dCodSeg'       # Código de seguridad
            ],
            'timbrado_fields': [
                'dNumTim'       # Número de timbrado
            ],
            'currency_fields': [
                'cMoneOpe',     # Moneda de la operación
                'cMoneDoc'      # Moneda del documento
            ],
            'operation_condition_fields': [
                'iTiOpe'        # Tipo de operación (contado/crédito)
            ],
            'buyer_presence_fields': [
                'iPresComp'     # Presencia del comprador
            ]
        }

    def validate(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Valida formatos de campos específicos SIFEN en el XML completo

        Args:
            xml_content: Contenido XML a validar como string

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores)

        Example:
            >>> validator = FormatValidator()
            >>> xml = '<?xml version="1.0"?><rDE>...</rDE>'
            >>> is_valid, errors = validator.validate(xml)
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Error de formato: {error}")
        """
        errors = []

        try:
            xml_doc = etree.fromstring(
                xml_content.encode('utf-8'), self._parser)
        except etree.XMLSyntaxError as e:
            return False, [f"XML mal formado: {str(e)}"]
        except Exception as e:
            return False, [f"Error parseando XML: {str(e)}"]

        # Validar CDC si existe
        cdc_errors = self._validate_cdc(xml_doc)
        errors.extend(cdc_errors)

        # Validar campos RUC
        ruc_errors = self._validate_ruc_fields(xml_doc)
        errors.extend(ruc_errors)

        # Validar campos de dígito verificador
        dv_errors = self._validate_dv_fields(xml_doc)
        errors.extend(dv_errors)

        # Validar campos de fecha
        date_errors = self._validate_date_fields(xml_doc)
        errors.extend(date_errors)

        # Validar códigos de documento
        doc_code_errors = self._validate_document_codes(xml_doc)
        errors.extend(doc_code_errors)

        # Validar códigos de establecimiento
        est_errors = self._validate_establishment_codes(xml_doc)
        errors.extend(est_errors)

        # Validar puntos de expedición
        exp_errors = self._validate_expedition_points(xml_doc)
        errors.extend(exp_errors)

        # Validar números de documento
        num_doc_errors = self._validate_document_numbers(xml_doc)
        errors.extend(num_doc_errors)

        # Validar códigos de seguridad
        sec_code_errors = self._validate_security_codes(xml_doc)
        errors.extend(sec_code_errors)

        # Validar timbrados
        timbrado_errors = self._validate_timbrado_fields(xml_doc)
        errors.extend(timbrado_errors)

        # Validar códigos de moneda
        currency_errors = self._validate_currency_codes(xml_doc)
        errors.extend(currency_errors)

        # Validar condiciones de operación
        operation_errors = self._validate_operation_conditions(xml_doc)
        errors.extend(operation_errors)

        # Validar presencia del comprador
        buyer_errors = self._validate_buyer_presence(xml_doc)
        errors.extend(buyer_errors)

        return len(errors) == 0, errors

    def _validate_cdc(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida formato CDC (44 dígitos) en atributo Id del elemento DE

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de CDC
        """
        errors = []

        # Buscar elemento DE con atributo Id
        de_elements = xml_doc.xpath(f'.//*[local-name()="DE"]')

        for de_element in de_elements:
            cdc = de_element.get('Id')
            if cdc is not None:
                if not self.patterns['cdc'].match(cdc):
                    errors.append(
                        f"CDC inválido en atributo Id: '{cdc}'. "
                        f"Debe tener exactamente 44 dígitos numéricos"
                    )
            else:
                errors.append("Atributo Id (CDC) faltante en elemento DE")

        return errors

    def _validate_ruc_fields(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida campos RUC en el documento

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de RUC
        """
        errors = []

        for ruc_field in self.field_mappings['ruc_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{ruc_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    ruc_value = elem.text.strip()
                    if not self.patterns['ruc'].match(ruc_value):
                        errors.append(
                            f"RUC inválido en {ruc_field}: '{ruc_value}'. "
                            f"Debe tener exactamente 8 dígitos numéricos"
                        )

        return errors

    def _validate_dv_fields(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida campos de dígito verificador

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de DV
        """
        errors = []

        for dv_field in self.field_mappings['dv_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{dv_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    dv_value = elem.text.strip()
                    if not self.patterns['dv'].match(dv_value):
                        errors.append(
                            f"Dígito verificador inválido en {dv_field}: '{dv_value}'. "
                            f"Debe ser exactamente 1 dígito numérico"
                        )

        return errors

    def _validate_date_fields(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida campos de fecha ISO 8601

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de fecha
        """
        errors = []

        for date_field in self.field_mappings['date_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{date_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    date_value = elem.text.strip()
                    # Intentar ambos patrones: básico y extendido
                    is_valid = (self.patterns['fecha_iso'].match(date_value) or
                                self.patterns['fecha_iso_extended'].match(date_value))

                    if not is_valid:
                        errors.append(
                            f"Fecha inválida en {date_field}: '{date_value}'. "
                            f"Formato esperado: YYYY-MM-DDTHH:MM:SS"
                        )

        return errors

    def _validate_document_codes(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida códigos de tipo de documento

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de códigos de documento
        """
        errors = []

        for doc_field in self.field_mappings['document_code_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{doc_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    doc_code = elem.text.strip()
                    if not self.patterns['codigo_documento'].match(doc_code):
                        valid_codes = ', '.join(VALID_DOCUMENT_TYPES.keys())
                        errors.append(
                            f"Código de documento inválido en {doc_field}: '{doc_code}'. "
                            f"Códigos válidos: {valid_codes}"
                        )

        return errors

    def _validate_establishment_codes(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida códigos de establecimiento

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de establecimiento
        """
        errors = []

        for est_field in self.field_mappings['establishment_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{est_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    est_value = elem.text.strip()
                    if not self.patterns['establecimiento'].match(est_value):
                        errors.append(
                            f"Código de establecimiento inválido en {est_field}: '{est_value}'. "
                            f"Debe tener exactamente 3 dígitos numéricos"
                        )

        return errors

    def _validate_expedition_points(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida puntos de expedición

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de punto de expedición
        """
        errors = []

        for exp_field in self.field_mappings['expedition_point_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{exp_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    exp_value = elem.text.strip()
                    if not self.patterns['punto_expedicion'].match(exp_value):
                        errors.append(
                            f"Punto de expedición inválido en {exp_field}: '{exp_value}'. "
                            f"Debe tener exactamente 3 dígitos numéricos"
                        )

        return errors

    def _validate_document_numbers(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida números de documento

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de número de documento
        """
        errors = []

        for num_field in self.field_mappings['document_number_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{num_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    num_value = elem.text.strip()
                    if not self.patterns['numero_documento'].match(num_value):
                        errors.append(
                            f"Número de documento inválido en {num_field}: '{num_value}'. "
                            f"Debe tener exactamente 7 dígitos numéricos"
                        )

        return errors

    def _validate_security_codes(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida códigos de seguridad

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de código de seguridad
        """
        errors = []

        for sec_field in self.field_mappings['security_code_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{sec_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    sec_value = elem.text.strip()
                    if not self.patterns['codigo_seguridad'].match(sec_value):
                        errors.append(
                            f"Código de seguridad inválido en {sec_field}: '{sec_value}'. "
                            f"Debe tener exactamente 9 dígitos numéricos"
                        )

        return errors

    def _validate_timbrado_fields(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida campos de timbrado

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de timbrado
        """
        errors = []

        for tim_field in self.field_mappings['timbrado_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{tim_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    tim_value = elem.text.strip()
                    if not self.patterns['timbrado'].match(tim_value):
                        errors.append(
                            f"Número de timbrado inválido en {tim_field}: '{tim_value}'. "
                            f"Debe tener exactamente 8 dígitos numéricos"
                        )

        return errors

    def _validate_currency_codes(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida códigos de moneda ISO

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de código de moneda
        """
        errors = []

        for curr_field in self.field_mappings['currency_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{curr_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    curr_value = elem.text.strip()
                    if not self.patterns['codigo_moneda'].match(curr_value):
                        errors.append(
                            f"Código de moneda inválido en {curr_field}: '{curr_value}'. "
                            f"Debe ser código ISO de 3 letras (ej: PYG, USD, EUR)"
                        )

        return errors

    def _validate_operation_conditions(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida condiciones de operación

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de condición de operación
        """
        errors = []

        for op_field in self.field_mappings['operation_condition_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{op_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    op_value = elem.text.strip()
                    if op_value not in VALID_OPERATION_CONDITIONS:
                        valid_ops = ', '.join(
                            f"{k}={v}" for k, v in VALID_OPERATION_CONDITIONS.items())
                        errors.append(
                            f"Condición de operación inválida en {op_field}: '{op_value}'. "
                            f"Valores válidos: {valid_ops}"
                        )

        return errors

    def _validate_buyer_presence(self, xml_doc: etree._Element) -> List[str]:
        """
        Valida códigos de presencia del comprador

        Args:
            xml_doc: Documento XML parseado

        Returns:
            Lista de errores de presencia del comprador
        """
        errors = []

        for buyer_field in self.field_mappings['buyer_presence_fields']:
            elements = xml_doc.xpath(f'.//*[local-name()="{buyer_field}"]')
            for elem in elements:
                if elem.text and elem.text.strip():
                    buyer_value = elem.text.strip()
                    if buyer_value not in VALID_BUYER_PRESENCE:
                        valid_presence = ', '.join(
                            f"{k}={v}" for k, v in VALID_BUYER_PRESENCE.items())
                        errors.append(
                            f"Presencia del comprador inválida en {buyer_field}: '{buyer_value}'. "
                            f"Valores válidos: {valid_presence}"
                        )

        return errors

    # =====================================
    # MÉTODOS PÚBLICOS DE VALIDACIÓN ESPECÍFICA
    # =====================================

    def validate_ruc(self, ruc: str) -> bool:
        """
        Valida formato RUC específico

        Args:
            ruc: Número RUC a validar

        Returns:
            True si el formato es válido

        Example:
            >>> validator = FormatValidator()
            >>> validator.validate_ruc("12345678")
            True
            >>> validator.validate_ruc("1234567")
            False
        """
        if not ruc or not isinstance(ruc, str):
            return False
        return self.patterns['ruc'].match(ruc.strip()) is not None

    def validate_cdc(self, cdc: str) -> bool:
        """
        Valida formato CDC específico

        Args:
            cdc: CDC a validar

        Returns:
            True si el formato es válido

        Example:
            >>> validator = FormatValidator()
            >>> validator.validate_cdc("01234567890123456789012345678901234567890123")
            True
            >>> validator.validate_cdc("123")
            False
        """
        if not cdc or not isinstance(cdc, str):
            return False
        return self.patterns['cdc'].match(cdc.strip()) is not None

    def validate_date_iso(self, date: str) -> bool:
        """
        Valida formato de fecha ISO 8601

        Args:
            date: Fecha a validar

        Returns:
            True si el formato es válido

        Example:
            >>> validator = FormatValidator()
            >>> validator.validate_date_iso("2024-12-15T14:30:45")
            True
            >>> validator.validate_date_iso("2024/12/15")
            False
        """
        if not date or not isinstance(date, str):
            return False
        date_clean = date.strip()
        return (self.patterns['fecha_iso'].match(date_clean) is not None or
                self.patterns['fecha_iso_extended'].match(date_clean) is not None)

    def validate_document_code(self, code: str) -> bool:
        """
        Valida código de tipo de documento

        Args:
            code: Código a validar

        Returns:
            True si el código es válido

        Example:
            >>> validator = FormatValidator()
            >>> validator.validate_document_code("01")
            True
            >>> validator.validate_document_code("99")
            False
        """
        if not code or not isinstance(code, str):
            return False
        return code.strip() in VALID_DOCUMENT_TYPES

    def validate_establishment_code(self, code: str) -> bool:
        """
        Valida código de establecimiento

        Args:
            code: Código a validar

        Returns:
            True si el formato es válido
        """
        if not code or not isinstance(code, str):
            return False
        return self.patterns['establecimiento'].match(code.strip()) is not None

    def validate_security_code(self, code: str) -> bool:
        """
        Valida código de seguridad

        Args:
            code: Código a validar

        Returns:
            True si el formato es válido
        """
        if not code or not isinstance(code, str):
            return False
        return self.patterns['codigo_seguridad'].match(code.strip()) is not None

    def get_field_validation_summary(self, xml_content: str) -> Dict[str, Any]:
        """
        Obtiene resumen de validación por tipo de campo

        Args:
            xml_content: Contenido XML a analizar

        Returns:
            Diccionario con resumen de validación por tipo
        """
        try:
            xml_doc = etree.fromstring(
                xml_content.encode('utf-8'), self._parser)
        except:
            return {'error': 'XML mal formado'}

        summary = {}

        # Validar cada tipo de campo
        field_types = [
            ('cdc', self._validate_cdc),
            ('ruc', self._validate_ruc_fields),
            ('dv', self._validate_dv_fields),
            ('dates', self._validate_date_fields),
            ('document_codes', self._validate_document_codes),
            ('establishments', self._validate_establishment_codes),
            ('expedition_points', self._validate_expedition_points),
            ('document_numbers', self._validate_document_numbers),
            ('security_codes', self._validate_security_codes),
            ('timbrados', self._validate_timbrado_fields),
            ('currencies', self._validate_currency_codes),
            ('operations', self._validate_operation_conditions),
            ('buyer_presence', self._validate_buyer_presence)
        ]

        for field_type, validator_func in field_types:
            errors = validator_func(xml_doc)
            summary[field_type] = {
                'valid': len(errors) == 0,
                'error_count': len(errors),
                'errors': errors
            }

        # Estadísticas generales
        total_errors = sum(item['error_count'] for item in summary.values())
        valid_fields = sum(1 for item in summary.values() if item['valid'])

        summary['_statistics'] = {
            'total_field_types': len(field_types),
            'valid_field_types': valid_fields,
            'total_errors': total_errors,
            'overall_valid': total_errors == 0
        }

        return summary


# =====================================
# UTILIDADES DE CONVENIENCIA
# =====================================

def quick_validate_ruc(ruc: str) -> bool:
    """
    Validación rápida de RUC

    Args:
        ruc: RUC a validar

    Returns:
        True si es válido
    """
    validator = FormatValidator()
    return validator.validate_ruc(ruc)


def quick_validate_cdc(cdc: str) -> bool:
    """
    Validación rápida de CDC

    Args:
        cdc: CDC a validar

    Returns:
        True si es válido
    """
    validator = FormatValidator()
    return validator.validate_cdc(cdc)


def quick_validate_date(date: str) -> bool:
    """
    Validación rápida de fecha ISO

    Args:
        date: Fecha a validar

    Returns:
        True si es válida
    """
    validator = FormatValidator()
    return validator.validate_date_iso(date)


def get_format_errors_only(xml_content: str) -> List[str]:
    """
    Obtiene solo los errores de formato del XML

    Args:
        xml_content: Contenido XML a validar

    Returns:
        Lista de errores de formato
    """
    validator = FormatValidator()
    _, errors = validator.validate(xml_content)
    return errors


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    'FormatValidator',
    'quick_validate_ruc',
    'quick_validate_cdc',
    'quick_validate_date',
    'get_format_errors_only'
]
