"""
Generador principal de Códigos de Control de Documentos (CDC) SIFEN.

Este módulo contiene la lógica principal para generar CDCs válidos
según las especificaciones SIFEN v150. Se enfoca únicamente en la
generación, delegando validación y utilidades a otros módulos.

RESPONSABILIDADES:
- Generar CDCs completos a partir de parámetros
- Formatear y validar componentes individuales
- Calcular dígitos verificadores
- Generar códigos de seguridad

DEPENDENCIAS:
- types.py: Para tipos de datos y constantes
- ../ruc_utils.py: Para validación de RUC

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

import re
import secrets
from datetime import datetime, date
from typing import Union

# Imports locales del módulo CDC
from .types import (
    CdcGenerationRequest,
    CdcComponents,
    TipoDocumento,
    TipoEmision,
    CDC_LENGTH,
    CDC_COMPONENT_LENGTHS,
    CDC_MODULO_11_BASE_FACTORS,
    PATTERN_FECHA_CDC,
    PATTERN_CODIGO_SEGURIDAD,
    MIN_SECURITY_CODE,
    MAX_SECURITY_CODE,
)

# Import del módulo hermano RUC
from ..ruc_utils import validate_ruc_complete


# ===================================================================
# FUNCIÓN PRINCIPAL DE GENERACIÓN
# ===================================================================

def generate_cdc(request: CdcGenerationRequest) -> str:
    """
    Genera un CDC completo según los parámetros proporcionados.

    Esta es la función principal para generar CDCs. Valida todos los 
    parámetros de entrada, normaliza los datos y construye el CDC final
    con su dígito verificador.

    Args:
        request: Parámetros de generación del CDC

    Returns:
        str: CDC de 44 dígitos

    Raises:
        ValueError: Si algún parámetro es inválido

    Examples:
        >>> req = CdcGenerationRequest(
        ...     ruc_emisor="80000001",
        ...     tipo_documento=TipoDocumento.FACTURA_ELECTRONICA.value,
        ...     establecimiento="001",
        ...     punto_expedicion="001",
        ...     numero_documento=123,
        ...     fecha_emision=datetime.now()
        ... )
        >>> cdc = generate_cdc(req)
        >>> print(len(cdc))  # 44
    """
    # Validaciones básicas del request
    basic_errors = request.validate_basic()
    if basic_errors:
        raise ValueError(f"Parámetros inválidos: {', '.join(basic_errors)}")

    # Validar y normalizar RUC emisor
    ruc_result = validate_ruc_complete(request.ruc_emisor)
    if not ruc_result.is_valid:
        raise ValueError(f"RUC emisor inválido: {ruc_result.error_message}")

    # Validar tipo de documento
    if not TipoDocumento.is_valid(request.tipo_documento):
        raise ValueError(
            f"Tipo de documento inválido: {request.tipo_documento}")

    # Validar y formatear componentes
    establecimiento = _format_numeric_component(
        request.establecimiento, CDC_COMPONENT_LENGTHS['est'], "establecimiento"
    )

    punto_expedicion = _format_numeric_component(
        request.punto_expedicion, CDC_COMPONENT_LENGTHS['pe'], "punto_expedicion"
    )

    numero_documento = _format_numeric_component(
        str(
            request.numero_documento), CDC_COMPONENT_LENGTHS['num'], "numero_documento"
    )

    # Formatear fecha
    fecha_formatted = _format_fecha_emision(request.fecha_emision)

    # Validar tipo de emisión
    if not TipoEmision.is_valid(request.tipo_emision):
        raise ValueError(f"Tipo de emisión inválido: {request.tipo_emision}")

    # Generar código de seguridad si no se proporciona
    codigo_seguridad = request.codigo_seguridad
    if codigo_seguridad is None:
        codigo_seguridad = generate_security_code()
    else:
        if not PATTERN_CODIGO_SEGURIDAD.match(codigo_seguridad):
            raise ValueError(
                "Código de seguridad debe tener 9 dígitos numéricos")

    # Construir CDC sin dígito verificador
    cdc_sin_dv = (
        ruc_result.ruc_base + ruc_result.dv + request.tipo_documento +
        establecimiento + punto_expedicion + numero_documento +
        fecha_formatted + request.tipo_emision + codigo_seguridad
    )

    # Calcular dígito verificador del CDC
    dv_cdc = calculate_cdc_dv(cdc_sin_dv)

    # Construir CDC final
    cdc_final = cdc_sin_dv + dv_cdc

    # Validación final de longitud
    if len(cdc_final) != CDC_LENGTH:
        raise ValueError(
            f"CDC generado tiene longitud incorrecta: {len(cdc_final)}")

    return cdc_final


def calculate_cdc_dv(cdc_sin_dv: str) -> str:
    """
    Calcula el dígito verificador de un CDC usando algoritmo módulo 11.

    Implementa el algoritmo específico de SIFEN para el cálculo del DV del CDC.

    Args:
        cdc_sin_dv: CDC sin el dígito verificador (43 dígitos)

    Returns:
        str: Dígito verificador (0-9)

    Raises:
        ValueError: Si la entrada no tiene el formato correcto

    Examples:
        >>> dv = calculate_cdc_dv("0123456789012345678901234567890123456789012")
        >>> print(dv)  # "X" (dígito calculado)
    """
    if len(cdc_sin_dv) != CDC_LENGTH - 1:
        raise ValueError(f"CDC sin DV debe tener {CDC_LENGTH - 1} dígitos")

    if not cdc_sin_dv.isdigit():
        raise ValueError("CDC debe contener solo dígitos numéricos")

    # Generar factores cíclicos
    factors = []
    for i in range(len(cdc_sin_dv)):
        factor_index = i % len(CDC_MODULO_11_BASE_FACTORS)
        factors.append(CDC_MODULO_11_BASE_FACTORS[factor_index])

    # Calcular suma ponderada
    total = sum(
        int(digit) * factor
        for digit, factor in zip(cdc_sin_dv, factors)
    )

    # Aplicar módulo 11
    remainder = total % 11

    # Calcular dígito verificador
    if remainder < 2:
        dv = 0
    else:
        dv = 11 - remainder

    return str(dv)


def generate_security_code() -> str:
    """
    Genera un código de seguridad aleatorio de 9 dígitos.

    Utiliza el módulo secrets para generar números criptográficamente seguros.

    Returns:
        str: Código de seguridad de 9 dígitos

    Examples:
        >>> code = generate_security_code()
        >>> print(len(code))  # 9
        >>> print(code.isdigit())  # True
    """
    return f"{secrets.randbelow(MAX_SECURITY_CODE - MIN_SECURITY_CODE + 1) + MIN_SECURITY_CODE:09d}"


# ===================================================================
# FUNCIONES AUXILIARES DE FORMATEO
# ===================================================================

def _format_numeric_component(value: str, expected_length: int, component_name: str) -> str:
    """
    Formatea un componente numérico con ceros a la izquierda.

    Args:
        value: Valor a formatear
        expected_length: Longitud esperada
        component_name: Nombre del componente (para errores)

    Returns:
        str: Valor formateado con ceros a la izquierda

    Raises:
        ValueError: Si el valor no es válido
    """
    if not value or not str(value).strip():
        raise ValueError(f"{component_name} no puede estar vacío")

    clean_value = str(value).strip()

    # Verificar que solo contenga dígitos
    if not clean_value.isdigit():
        raise ValueError(
            f"{component_name} debe contener solo dígitos numéricos")

    # Verificar longitud máxima
    if len(clean_value) > expected_length:
        raise ValueError(
            f"{component_name} no puede tener más de {expected_length} dígitos")

    # Formatear con ceros a la izquierda
    return clean_value.zfill(expected_length)


def _format_fecha_emision(fecha: Union[datetime, date, str]) -> str:
    """
    Formatea una fecha para el CDC en formato YYYYMMDD.

    Args:
        fecha: Fecha a formatear

    Returns:
        str: Fecha en formato YYYYMMDD

    Raises:
        ValueError: Si la fecha no es válida
    """
    if isinstance(fecha, datetime):
        return fecha.strftime("%Y%m%d")
    elif isinstance(fecha, date):
        return fecha.strftime("%Y%m%d")
    elif isinstance(fecha, str):
        # Intentar parsear diferentes formatos
        fecha_clean = fecha.strip()

        # Formato YYYYMMDD (ya correcto)
        if PATTERN_FECHA_CDC.match(fecha_clean):
            return fecha_clean

        # Formato YYYY-MM-DD
        if re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_clean):
            return fecha_clean.replace('-', '')

        # Formato DD/MM/YYYY
        date_match = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', fecha_clean)
        if date_match:
            dd, mm, yyyy = date_match.groups()
            return f"{yyyy}{mm}{dd}"

        raise ValueError(f"Formato de fecha no reconocido: {fecha}")
    else:
        raise ValueError(f"Tipo de fecha no soportado: {type(fecha)}")


def _validate_fecha_format(fecha_str: str) -> bool:
    """
    Valida que una fecha tenga formato YYYYMMDD válido.

    Args:
        fecha_str: Fecha en formato string

    Returns:
        bool: True si la fecha es válida
    """
    if not PATTERN_FECHA_CDC.match(fecha_str):
        return False

    try:
        # Extraer componentes
        year = int(fecha_str[:4])
        month = int(fecha_str[4:6])
        day = int(fecha_str[6:8])

        # Validar rangos básicos
        if year < 1900 or year > 2100:
            return False
        if month < 1 or month > 12:
            return False
        if day < 1 or day > 31:
            return False

        # Intentar crear fecha para validación completa
        datetime(year, month, day)
        return True

    except (ValueError, IndexError):
        return False


# ===================================================================
# CONSTANTES PARA EXPORT
# ===================================================================

__all__ = [
    # Función principal
    'generate_cdc',

    # Funciones auxiliares
    'calculate_cdc_dv',
    'generate_security_code',

    # Funciones internas (para testing)
    '_format_numeric_component',
    '_format_fecha_emision',
    '_validate_fecha_format',
]
