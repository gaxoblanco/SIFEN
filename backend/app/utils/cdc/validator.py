"""
Validador de Códigos de Control de Documentos (CDC) SIFEN.

Este módulo se especializa en la validación completa de CDCs,
verificando formato, estructura, componentes individuales y
coherencia de datos según especificaciones SIFEN v150.

RESPONSABILIDADES:
- Validar formato y longitud de CDC
- Verificar coherencia de componentes
- Validar dígitos verificadores
- Proporcionar diagnósticos detallados de errores

DEPENDENCIAS:
- types.py: Para tipos de datos y constantes
- components.py: Para extracción de componentes
- generator.py: Para cálculo de DV
- ../ruc_utils.py: Para validación de RUC

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

from typing import Dict, List, Any

# Imports locales del módulo CDC
from .types import (
    CdcValidationResult,
    CdcComponents,
    TipoDocumento,
    TipoEmision,
    CdcErrorCode,
    CDC_LENGTH,
    PATTERN_CDC,
)

# Import del módulo hermano RUC
from ..ruc_utils import validate_ruc_complete


# ===================================================================
# FUNCIÓN PRINCIPAL DE VALIDACIÓN
# ===================================================================

def validate_cdc(cdc: str) -> CdcValidationResult:
    """
    Valida un CDC completo y extrae sus componentes.

    Verifica el formato, longitud, dígito verificador y la validez
    de cada componente individual del CDC.

    Args:
        cdc: CDC a validar (44 dígitos)

    Returns:
        CdcValidationResult: Resultado detallado de la validación

    Examples:
        >>> result = validate_cdc("01234567890123456789012345678901234567890123")
        >>> print(result.is_valid)
        >>> print(result.components.ruc_emisor if result.components else "Invalid")
    """
    # Validación básica de formato
    basic_validation = _validate_basic_format(cdc)
    if not basic_validation['is_valid']:
        return CdcValidationResult(
            is_valid=False,
            cdc=cdc,
            error_message=basic_validation['error_message'],
            error_code=basic_validation['error_code']
        )

    # Extraer componentes
    try:
        from .components import extract_cdc_components
        components = extract_cdc_components(cdc)
    except Exception as e:
        return CdcValidationResult(
            is_valid=False,
            cdc=cdc,
            error_message=f"Error al extraer componentes: {str(e)}",
            error_code=CdcErrorCode.COMPONENT_EXTRACTION_ERROR
        )

    # Validar cada componente individualmente
    component_validation = _validate_components(components, cdc)

    return component_validation


def is_valid_cdc(cdc: str) -> bool:
    """
    Verifica rápidamente si un CDC es válido.

    Función de conveniencia para validación booleana simple.

    Args:
        cdc: CDC a validar

    Returns:
        bool: True si el CDC es válido

    Examples:
        >>> is_valid_cdc("01234567890123456789012345678901234567890123")
        True
        >>> is_valid_cdc("invalid_cdc")
        False
    """
    return validate_cdc(cdc).is_valid


def validate_cdc_batch(cdcs: List[str]) -> Dict[str, CdcValidationResult]:
    """
    Valida un lote de CDCs.

    Args:
        cdcs: Lista de CDCs a validar

    Returns:
        Dict[str, CdcValidationResult]: Resultados de validación indexados por CDC

    Examples:
        >>> results = validate_cdc_batch(["cdc1", "cdc2", "cdc3"])
        >>> valid_count = sum(1 for r in results.values() if r.is_valid)
    """
    results: Dict[str, CdcValidationResult] = {}

    for cdc in cdcs:
        try:
            results[cdc] = validate_cdc(cdc)
        except Exception as e:
            results[cdc] = CdcValidationResult(
                is_valid=False,
                cdc=cdc,
                error_message=f"Error inesperado: {str(e)}",
                error_code=CdcErrorCode.UNEXPECTED_ERROR
            )

    return results


def get_cdc_statistics(cdcs: List[str]) -> Dict[str, Any]:
    """
    Obtiene estadísticas sobre un conjunto de CDCs.

    Args:
        cdcs: Lista de CDCs a analizar

    Returns:
        Dict: Estadísticas del conjunto de CDCs
    """
    if not cdcs:
        return {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'valid_percentage': 0.0,
            'error_summary': {},
            'document_types': {},
            'sample_valid_cdc': None,
            'sample_invalid_cdc': None
        }

    results = validate_cdc_batch(cdcs)

    valid_count = sum(1 for r in results.values() if r.is_valid)
    invalid_count = len(cdcs) - valid_count

    # Agrupar errores
    error_counts: Dict[str, int] = {}
    tipo_documento_counts: Dict[str, int] = {}

    for result in results.values():
        if not result.is_valid:
            error_code = result.error_code
            error_counts[error_code] = error_counts.get(error_code, 0) + 1
        else:
            if result.components:
                tipo = result.components.tipo_documento
                desc = TipoDocumento.get_descripcion(tipo) or tipo
                tipo_documento_counts[desc] = tipo_documento_counts.get(
                    desc, 0) + 1

    return {
        'total': len(cdcs),
        'valid': valid_count,
        'invalid': invalid_count,
        'valid_percentage': (valid_count / len(cdcs)) * 100,
        'error_summary': error_counts,
        'document_types': tipo_documento_counts,
        'sample_valid_cdc': next((cdc for cdc, result in results.items() if result.is_valid), None),
        'sample_invalid_cdc': next((cdc for cdc, result in results.items() if not result.is_valid), None)
    }


# ===================================================================
# FUNCIONES INTERNAS DE VALIDACIÓN
# ===================================================================

def _validate_basic_format(cdc: str) -> Dict[str, Any]:
    """
    Valida el formato básico de un CDC.

    Args:
        cdc: CDC a validar

    Returns:
        Dict con resultado de validación básica
    """
    # Validación de tipo
    if not cdc or not isinstance(cdc, str):
        return {
            'is_valid': False,
            'error_message': "CDC debe ser una cadena de texto",
            'error_code': CdcErrorCode.INVALID_TYPE
        }

    # Validar longitud
    if len(cdc) != CDC_LENGTH:
        return {
            'is_valid': False,
            'error_message': f"CDC debe tener exactamente {CDC_LENGTH} dígitos, recibido: {len(cdc)}",
            'error_code': CdcErrorCode.INVALID_LENGTH
        }

    # Validar que solo contenga dígitos
    if not PATTERN_CDC.match(cdc):
        return {
            'is_valid': False,
            'error_message': "CDC debe contener solo dígitos numéricos",
            'error_code': CdcErrorCode.INVALID_FORMAT
        }

    return {'is_valid': True}


def _validate_components(components: CdcComponents, original_cdc: str) -> CdcValidationResult:
    """
    Valida todos los componentes individuales de un CDC.

    Args:
        components: Componentes extraídos del CDC
        original_cdc: CDC original para referencia

    Returns:
        CdcValidationResult: Resultado completo de validación
    """
    validation_details: Dict[str, Any] = {}

    # Validar longitudes de componentes
    if not components.validate_lengths():
        return CdcValidationResult(
            is_valid=False,
            cdc=original_cdc,
            components=components,
            error_message="Uno o más componentes tienen longitud incorrecta",
            error_code=CdcErrorCode.COMPONENT_EXTRACTION_ERROR,
            validation_details=validation_details
        )

    # 1. Validar RUC y DV
    ruc_validation = _validate_ruc_component(components, validation_details)
    if not ruc_validation['is_valid']:
        return CdcValidationResult(
            is_valid=False,
            cdc=original_cdc,
            components=components,
            error_message=ruc_validation['error_message'],
            error_code=ruc_validation['error_code'],
            validation_details=validation_details
        )

    # 2. Validar tipo de documento
    tipo_validation = _validate_tipo_documento_component(
        components, validation_details)
    if not tipo_validation['is_valid']:
        return CdcValidationResult(
            is_valid=False,
            cdc=original_cdc,
            components=components,
            error_message=tipo_validation['error_message'],
            error_code=tipo_validation['error_code'],
            validation_details=validation_details
        )

    # 3. Validar fecha
    fecha_validation = _validate_fecha_component(
        components, validation_details)
    if not fecha_validation['is_valid']:
        return CdcValidationResult(
            is_valid=False,
            cdc=original_cdc,
            components=components,
            error_message=fecha_validation['error_message'],
            error_code=fecha_validation['error_code'],
            validation_details=validation_details
        )

    # 4. Validar tipo de emisión
    emision_validation = _validate_tipo_emision_component(
        components, validation_details)
    if not emision_validation['is_valid']:
        return CdcValidationResult(
            is_valid=False,
            cdc=original_cdc,
            components=components,
            error_message=emision_validation['error_message'],
            error_code=emision_validation['error_code'],
            validation_details=validation_details
        )

    # 5. Validar dígito verificador del CDC
    dv_validation = _validate_cdc_dv_component(
        components, original_cdc, validation_details)
    if not dv_validation['is_valid']:
        return CdcValidationResult(
            is_valid=False,
            cdc=original_cdc,
            components=components,
            error_message=dv_validation['error_message'],
            error_code=dv_validation['error_code'],
            validation_details=validation_details
        )

    # Si llegamos aquí, el CDC es válido
    return CdcValidationResult(
        is_valid=True,
        cdc=original_cdc,
        components=components,
        validation_details=validation_details
    )


def _validate_ruc_component(components: CdcComponents, validation_details: Dict[str, Any]) -> Dict[str, Any]:
    """Valida el componente RUC del CDC."""
    ruc_complete = components.ruc_emisor + components.dv_ruc
    ruc_result = validate_ruc_complete(ruc_complete)

    validation_details['ruc_validation'] = {
        'ruc_base': components.ruc_emisor,
        'dv_provided': components.dv_ruc,
        'is_valid': ruc_result.is_valid,
        'error': ruc_result.error_message if not ruc_result.is_valid else None
    }

    if not ruc_result.is_valid:
        return {
            'is_valid': False,
            'error_message': f"RUC inválido en CDC: {ruc_result.error_message}",
            'error_code': CdcErrorCode.INVALID_RUC_IN_CDC
        }

    return {'is_valid': True}


def _validate_tipo_documento_component(components: CdcComponents, validation_details: Dict[str, Any]) -> Dict[str, Any]:
    """Valida el componente tipo de documento del CDC."""
    is_valid = TipoDocumento.is_valid(components.tipo_documento)

    validation_details['tipo_documento_validation'] = {
        'code': components.tipo_documento,
        'description': TipoDocumento.get_descripcion(components.tipo_documento),
        'is_valid': is_valid
    }

    if not is_valid:
        return {
            'is_valid': False,
            'error_message': f"Tipo de documento inválido: {components.tipo_documento}",
            'error_code': CdcErrorCode.INVALID_DOCUMENT_TYPE
        }

    return {'is_valid': True}


def _validate_fecha_component(components: CdcComponents, validation_details: Dict[str, Any]) -> Dict[str, Any]:
    """Valida el componente fecha del CDC."""
    from .generator import _validate_fecha_format

    is_valid = _validate_fecha_format(components.fecha_emision)

    validation_details['fecha_validation'] = {
        'fecha_raw': components.fecha_emision,
        'fecha_formatted': _format_fecha_display(components.fecha_emision) if is_valid else None,
        'is_valid': is_valid
    }

    if not is_valid:
        return {
            'is_valid': False,
            'error_message': f"Fecha inválida en CDC: {components.fecha_emision}",
            'error_code': CdcErrorCode.INVALID_DATE_FORMAT
        }

    return {'is_valid': True}


def _validate_tipo_emision_component(components: CdcComponents, validation_details: Dict[str, Any]) -> Dict[str, Any]:
    """Valida el componente tipo de emisión del CDC."""
    is_valid = TipoEmision.is_valid(components.tipo_emision)

    validation_details['tipo_emision_validation'] = {
        'code': components.tipo_emision,
        'description': TipoEmision.get_descripcion(components.tipo_emision),
        'is_valid': is_valid
    }

    if not is_valid:
        return {
            'is_valid': False,
            'error_message': f"Tipo de emisión inválido: {components.tipo_emision}",
            'error_code': CdcErrorCode.INVALID_EMISSION_TYPE
        }

    return {'is_valid': True}


def _validate_cdc_dv_component(components: CdcComponents, original_cdc: str, validation_details: Dict[str, Any]) -> Dict[str, Any]:
    """Valida el dígito verificador del CDC."""
    from .generator import calculate_cdc_dv

    # Reconstruir CDC sin DV para validar
    cdc_sin_dv = original_cdc[:-1]
    expected_dv = calculate_cdc_dv(cdc_sin_dv)

    validation_details['dv_cdc_validation'] = {
        'provided_dv': components.dv_cdc,
        'calculated_dv': expected_dv,
        'is_valid': components.dv_cdc == expected_dv
    }

    if components.dv_cdc != expected_dv:
        return {
            'is_valid': False,
            'error_message': f"Dígito verificador CDC incorrecto. Esperado: {expected_dv}, Recibido: {components.dv_cdc}",
            'error_code': CdcErrorCode.INVALID_CDC_DV
        }

    return {'is_valid': True}


def _format_fecha_display(fecha_str: str) -> str:
    """
    Formatea una fecha CDC para visualización.

    Args:
        fecha_str: Fecha en formato YYYYMMDD

    Returns:
        str: Fecha formateada como DD/MM/YYYY
    """
    if len(fecha_str) != 8:
        return fecha_str

    try:
        year = fecha_str[:4]
        month = fecha_str[4:6]
        day = fecha_str[6:8]
        return f"{day}/{month}/{year}"
    except:
        return fecha_str


# ===================================================================
# CONSTANTES PARA EXPORT
# ===================================================================

__all__ = [
    # Funciones principales
    'validate_cdc',
    'is_valid_cdc',

    # Funciones de lote
    'validate_cdc_batch',
    'get_cdc_statistics',

    # Funciones internas (para testing)
    '_validate_basic_format',
    '_validate_components',
    '_validate_ruc_component',
    '_validate_tipo_documento_component',
    '_validate_fecha_component',
    '_validate_tipo_emision_component',
    '_validate_cdc_dv_component',
]
