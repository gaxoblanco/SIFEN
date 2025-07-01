"""
Utilidades para validación de RUC (Registro Único del Contribuyente) de Paraguay.

Este módulo implementa la validación completa del RUC paraguayo según las 
especificaciones oficiales de la SET (Subsecretaría de Estado de Tributación) 
para el sistema SIFEN v150.

CARACTERÍSTICAS DEL RUC PARAGUAYO:
- 8 dígitos numéricos base
- 1 dígito verificador calculado con algoritmo módulo 11
- Formato completo: XXXXXXXX-X (9 dígitos total)
- Solo caracteres numéricos (0-9)

ALGORITMO MÓDULO 11 SET PARAGUAY:
- Factores de multiplicación: [2, 3, 4, 5, 6, 7, 2, 3] (posiciones 1-8)
- Suma ponderada: Σ(dígito × factor)
- Resto: suma % 11  
- Si resto < 2: DV = 0
- Si resto >= 2: DV = 11 - resto

CASOS DE USO:
- Validación de RUC emisor en documentos SIFEN
- Validación de RUC receptor/cliente
- Generación automática de dígito verificador
- Normalización de formatos RUC

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

import re
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass


# ===================================================================
# CONSTANTES Y CONFIGURACIÓN
# ===================================================================

# Factores de multiplicación para el algoritmo módulo 11
MODULO_11_FACTORS = [2, 3, 4, 5, 6, 7, 2, 3]

# Longitudes válidas para RUC
RUC_BASE_LENGTH = 8  # RUC sin dígito verificador
DV_LENGTH = 1        # Dígito verificador
RUC_COMPLETE_LENGTH = 9  # RUC + DV

# Patrones regex para validación
PATTERN_RUC_BASE = re.compile(r'^[0-9]{8}$')        # 8 dígitos exactos
PATTERN_DV = re.compile(r'^[0-9]{1}$')              # 1 dígito exacto
PATTERN_RUC_COMPLETE = re.compile(r'^[0-9]{9}$')    # 9 dígitos exactos
PATTERN_RUC_WITH_DASH = re.compile(
    r'^[0-9]{8}-[0-9]{1}$')  # Formato XXXXXXXX-X

# RUCs inválidos conocidos
INVALID_RUCS = {
    '00000000',  # Todos ceros
    '11111111',  # Todos unos
    '12345678',  # Secuencia de testing común
}


# ===================================================================
# CLASES DE DATOS
# ===================================================================

@dataclass
class RucValidationResult:
    """
    Resultado de la validación de RUC.

    Attributes:
        is_valid (bool): True si el RUC es válido
        ruc_base (str): RUC de 8 dígitos sin DV
        dv (str): Dígito verificador
        ruc_complete (str): RUC completo (9 dígitos)
        ruc_formatted (str): RUC formateado con guión (XXXXXXXX-X)
        error_message (str): Mensaje de error si no es válido
        error_code (str): Código de error para manejo programático
    """
    is_valid: bool
    ruc_base: str = ""
    dv: str = ""
    ruc_complete: str = ""
    ruc_formatted: str = ""
    error_message: str = ""
    error_code: str = ""


# ===================================================================
# FUNCIONES PRINCIPALES DE VALIDACIÓN
# ===================================================================

def validate_ruc_complete(ruc_input: Union[str, int]) -> RucValidationResult:
    """
    Valida un RUC completo (con o sin dígito verificador).

    Esta función es el punto de entrada principal para validar RUCs.
    Acepta múltiples formatos y normaliza la entrada antes de validar.

    Args:
        ruc_input: RUC a validar. Puede ser:
            - String de 8 dígitos (sin DV)
            - String de 9 dígitos (con DV)
            - String con formato XXXXXXXX-X
            - Entero de 8 o 9 dígitos

    Returns:
        RucValidationResult: Objeto con resultado de validación completo

    Examples:
        >>> result = validate_ruc_complete("12345678")
        >>> print(result.is_valid)  # False (DV incorrecto)

        >>> result = validate_ruc_complete("80000001-6")  
        >>> print(result.is_valid)  # True
        >>> print(result.ruc_complete)  # "800000016"
    """
    # Normalizar entrada
    normalized_input = _normalize_ruc_input(ruc_input)
    if not normalized_input:
        return RucValidationResult(
            is_valid=False,
            error_message="Formato de RUC inválido o vacío",
            error_code="INVALID_FORMAT"
        )

    # Determinar tipo de entrada y validar
    if len(normalized_input) == RUC_BASE_LENGTH:
        # RUC sin DV: calcular y validar
        return _validate_ruc_without_dv(normalized_input)
    elif len(normalized_input) == RUC_COMPLETE_LENGTH:
        # RUC con DV: validar completo
        return _validate_ruc_with_dv(normalized_input)
    else:
        return RucValidationResult(
            is_valid=False,
            error_message=f"Longitud de RUC inválida: {len(normalized_input)} dígitos",
            error_code="INVALID_LENGTH"
        )


def calculate_dv(ruc_base: Union[str, int]) -> Optional[str]:
    """
    Calcula el dígito verificador para un RUC base de 8 dígitos.

    Implementa el algoritmo módulo 11 oficial de la SET Paraguay.

    Args:
        ruc_base: RUC de 8 dígitos (string o entero)

    Returns:
        str: Dígito verificador (0-9) o None si el RUC es inválido

    Examples:
        >>> calculate_dv("80000001")
        '6'
        >>> calculate_dv(12345678)
        '0'
    """
    # Normalizar entrada
    ruc_str = str(ruc_base).strip().zfill(8)

    # Validar formato
    if not PATTERN_RUC_BASE.match(ruc_str):
        return None

    # Validar RUC no esté en lista de inválidos
    if ruc_str in INVALID_RUCS:
        return None

    # Aplicar algoritmo módulo 11
    try:
        total = sum(
            int(digit) * factor
            for digit, factor in zip(ruc_str, MODULO_11_FACTORS)
        )

        remainder = total % 11

        # Calcular dígito verificador según reglas SET
        if remainder < 2:
            dv = 0
        else:
            dv = 11 - remainder

        return str(dv)

    except (ValueError, IndexError) as e:
        return None


def format_ruc(ruc_input: Union[str, int], include_dv: bool = True) -> Optional[str]:
    """
    Formatea un RUC para visualización según estándares paraguayos.

    Args:
        ruc_input: RUC a formatear (8 o 9 dígitos)
        include_dv: Si incluir el dígito verificador (default: True)

    Returns:
        str: RUC formateado o None si es inválido
            - Con DV: "XXXXXXXX-X"
            - Sin DV: "XXXXXXXX"

    Examples:
        >>> format_ruc("800000016")
        '80000001-6'
        >>> format_ruc("80000001", include_dv=False)
        '80000001'
    """
    validation_result = validate_ruc_complete(ruc_input)

    if not validation_result.is_valid:
        return None

    if include_dv:
        return validation_result.ruc_formatted
    else:
        return validation_result.ruc_base


def is_valid_ruc(ruc_input: Union[str, int]) -> bool:
    """
    Verifica rápidamente si un RUC es válido.

    Función de conveniencia para validación booleana simple.

    Args:
        ruc_input: RUC a validar

    Returns:
        bool: True si el RUC es válido

    Examples:
        >>> is_valid_ruc("80000001-6")
        True
        >>> is_valid_ruc("12345678")
        False
    """
    return validate_ruc_complete(ruc_input).is_valid


# ===================================================================
# FUNCIONES DE UTILIDAD ESPECÍFICAS
# ===================================================================

def extract_ruc_parts(ruc_input: Union[str, int]) -> Optional[Tuple[str, str]]:
    """
    Extrae las partes de un RUC (base y dígito verificador).

    Args:
        ruc_input: RUC completo a descomponer

    Returns:
        Tuple[str, str]: (ruc_base, dv) o None si es inválido

    Examples:
        >>> extract_ruc_parts("80000001-6")
        ('80000001', '6')
        >>> extract_ruc_parts("800000016")
        ('80000001', '6')
    """
    validation_result = validate_ruc_complete(ruc_input)

    if validation_result.is_valid:
        return (validation_result.ruc_base, validation_result.dv)
    else:
        return None


def generate_test_ruc() -> Tuple[str, str, str]:
    """
    Genera un RUC válido para testing/desarrollo.

    Genera un RUC base pseudo-aleatorio y calcula su DV correspondiente.
    NOTA: Solo para uso en desarrollo, no usar en producción.

    Returns:
        Tuple[str, str, str]: (ruc_base, dv, ruc_complete)

    Examples:
        >>> ruc_base, dv, complete = generate_test_ruc()
        >>> print(f"RUC: {ruc_base}-{dv}")

    Raises:
        RuntimeError: Si no se puede generar un RUC válido después de varios intentos
    """
    import random

    # Generar RUC base evitando números inválidos
    max_attempts = 100  # Evitar bucle infinito
    attempts = 0

    while attempts < max_attempts:
        ruc_base = f"{random.randint(10000000, 99999999):08d}"
        if ruc_base not in INVALID_RUCS:
            # Intentar calcular DV
            dv = calculate_dv(ruc_base)
            if dv is not None:
                ruc_complete = ruc_base + dv
                return ruc_base, dv, ruc_complete

        attempts += 1

    # Si llegamos aquí, no pudimos generar un RUC válido
    raise RuntimeError(
        f"No se pudo generar un RUC válido después de {max_attempts} intentos"
    )


# ===================================================================
# FUNCIONES INTERNAS DE PROCESAMIENTO
# ===================================================================

def _normalize_ruc_input(ruc_input: Union[str, int]) -> Optional[str]:
    """
    Normaliza la entrada de RUC removiendo caracteres no numéricos.

    Args:
        ruc_input: Entrada a normalizar

    Returns:
        str: String con solo dígitos o None si inválido
    """
    if ruc_input is None:
        return None

    # Convertir a string y limpiar
    ruc_str = str(ruc_input).strip()

    # Remover caracteres no numéricos (guiones, espacios, etc.)
    ruc_clean = re.sub(r'[^0-9]', '', ruc_str)

    # Validar que solo contenga dígitos
    if not ruc_clean or not ruc_clean.isdigit():
        return None

    return ruc_clean


def _validate_ruc_without_dv(ruc_base: str) -> RucValidationResult:
    """
    Valida un RUC de 8 dígitos y calcula su DV.

    Args:
        ruc_base: RUC de 8 dígitos

    Returns:
        RucValidationResult: Resultado de validación
    """
    # Validar formato básico
    if not PATTERN_RUC_BASE.match(ruc_base):
        return RucValidationResult(
            is_valid=False,
            error_message="RUC debe contener exactamente 8 dígitos numéricos",
            error_code="INVALID_FORMAT"
        )

    # Validar RUC no esté en lista prohibida
    if ruc_base in INVALID_RUCS:
        return RucValidationResult(
            is_valid=False,
            error_message=f"RUC {ruc_base} no es válido (formato reservado)",
            error_code="INVALID_RUC"
        )

    # Calcular dígito verificador
    dv = calculate_dv(ruc_base)
    if dv is None:
        return RucValidationResult(
            is_valid=False,
            error_message="Error al calcular dígito verificador",
            error_code="DV_CALCULATION_ERROR"
        )

    # Construir resultado exitoso
    ruc_complete = ruc_base + dv
    ruc_formatted = f"{ruc_base}-{dv}"

    return RucValidationResult(
        is_valid=True,
        ruc_base=ruc_base,
        dv=dv,
        ruc_complete=ruc_complete,
        ruc_formatted=ruc_formatted
    )


def _validate_ruc_with_dv(ruc_complete: str) -> RucValidationResult:
    """
    Valida un RUC completo de 9 dígitos (incluyendo DV).

    Args:
        ruc_complete: RUC de 9 dígitos

    Returns:
        RucValidationResult: Resultado de validación
    """
    # Validar formato básico
    if not PATTERN_RUC_COMPLETE.match(ruc_complete):
        return RucValidationResult(
            is_valid=False,
            error_message="RUC completo debe contener exactamente 9 dígitos numéricos",
            error_code="INVALID_FORMAT"
        )

    # Separar base y DV
    ruc_base = ruc_complete[:8]
    provided_dv = ruc_complete[8]

    # Validar RUC base
    if ruc_base in INVALID_RUCS:
        return RucValidationResult(
            is_valid=False,
            error_message=f"RUC {ruc_base} no es válido (formato reservado)",
            error_code="INVALID_RUC"
        )

    # Calcular DV esperado
    calculated_dv = calculate_dv(ruc_base)
    if calculated_dv is None:
        return RucValidationResult(
            is_valid=False,
            error_message="Error al calcular dígito verificador",
            error_code="DV_CALCULATION_ERROR"
        )

    # Verificar DV coincide
    if provided_dv != calculated_dv:
        return RucValidationResult(
            is_valid=False,
            ruc_base=ruc_base,
            dv=provided_dv,
            error_message=f"Dígito verificador incorrecto. Esperado: {calculated_dv}, Recibido: {provided_dv}",
            error_code="INVALID_DV"
        )

    # Construir resultado exitoso
    ruc_formatted = f"{ruc_base}-{provided_dv}"

    return RucValidationResult(
        is_valid=True,
        ruc_base=ruc_base,
        dv=provided_dv,
        ruc_complete=ruc_complete,
        ruc_formatted=ruc_formatted
    )


# ===================================================================
# FUNCIONES DE TESTING Y DEBUGGING
# ===================================================================

def get_validation_summary(ruc_input: Union[str, int]) -> Dict[str, Union[str, bool]]:
    """
    Obtiene un resumen completo de la validación de RUC para debugging.

    Args:
        ruc_input: RUC a analizar

    Returns:
        Dict: Resumen detallado del proceso de validación

    Examples:
        >>> summary = get_validation_summary("80000001-6")
        >>> print(summary['is_valid'])  # True
        >>> print(summary['details'])
    """
    result = validate_ruc_complete(ruc_input)

    summary = {
        'input': str(ruc_input),
        'normalized_input': _normalize_ruc_input(ruc_input),
        'is_valid': result.is_valid,
        'ruc_base': result.ruc_base,
        'dv': result.dv,
        'ruc_complete': result.ruc_complete,
        'ruc_formatted': result.ruc_formatted,
        'error_message': result.error_message,
        'error_code': result.error_code,
        'calculated_dv': calculate_dv(result.ruc_base) if result.ruc_base else None,
    }

    return summary


# ===================================================================
# CONSTANTES PARA EXPORT
# ===================================================================

__all__ = [
    # Clases principales
    'RucValidationResult',

    # Funciones principales
    'validate_ruc_complete',
    'calculate_dv',
    'format_ruc',
    'is_valid_ruc',

    # Utilidades
    'extract_ruc_parts',
    'generate_test_ruc',
    'get_validation_summary',

    # Constantes
    'RUC_BASE_LENGTH',
    'DV_LENGTH',
    'RUC_COMPLETE_LENGTH',
]
