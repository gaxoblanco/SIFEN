"""
Utilidades de formateo y presentación para CDC SIFEN.

Este módulo contiene funciones de utilidad para formatear, presentar
y manipular CDCs de manera legible y útil para el usuario final.

RESPONSABILIDADES:
- Formatear CDCs para visualización
- Generar información legible sobre CDCs
- Proporcionar utilidades de conversión
- Crear reportes y resúmenes

DEPENDENCIAS:
- types.py: Para tipos de datos y constantes
- components.py: Para extracción de componentes
- validator.py: Para validación

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Imports locales del módulo CDC
from .types import (
    CdcComponents,
    CdcGenerationRequest,
    TipoDocumento,
    TipoEmision,
)
from .components import extract_cdc_components, get_components_summary
from .validator import validate_cdc


# ===================================================================
# FUNCIONES DE FORMATEO Y PRESENTACIÓN
# ===================================================================

def format_cdc_display(cdc: str) -> str:
    """
    Formatea un CDC para visualización legible.

    Divide el CDC en grupos separados por guiones para facilitar la lectura.

    Args:
        cdc: CDC de 44 dígitos

    Returns:
        str: CDC formateado con guiones para legibilidad

    Examples:
        >>> formatted = format_cdc_display("01234567890123456789012345678901234567890123")
        >>> print(formatted)  # "01234567-8-01-234-567-8901234-20241201-1-234567890-1"
    """
    if len(cdc) != 44:
        return cdc  # Retornar sin formato si es inválido

    try:
        components = extract_cdc_components(cdc)
        return (f"{components.ruc_emisor}-{components.dv_ruc}-{components.tipo_documento}-"
                f"{components.establecimiento}-{components.punto_expedicion}-{components.numero_documento}-"
                f"{components.fecha_emision}-{components.tipo_emision}-{components.codigo_seguridad}-"
                f"{components.dv_cdc}")
    except:
        return cdc  # Retornar sin formato si hay error


def get_cdc_info(cdc: str) -> Dict[str, Any]:
    """
    Obtiene información legible sobre un CDC.

    Extrae y presenta toda la información relevante de un CDC
    en formato legible para el usuario.

    Args:
        cdc: CDC a analizar

    Returns:
        Dict: Información detallada del CDC

    Examples:
        >>> info = get_cdc_info("01234567890123456789012345678901234567890123")
        >>> print(info['tipo_documento_descripcion'])
    """
    validation_result = validate_cdc(cdc)

    if not validation_result.is_valid:
        return {
            'valid': False,
            'error': validation_result.error_message,
            'error_code': validation_result.error_code,
            'cdc': cdc
        }

    components = validation_result.components
    if not components:
        return {
            'valid': False,
            'error': "No se pudieron extraer componentes",
            'cdc': cdc
        }

    return {
        'valid': True,
        'cdc': cdc,
        'cdc_formatted': format_cdc_display(cdc),
        'ruc_emisor': components.ruc_emisor,
        'ruc_completo': components.get_ruc_completo(),
        'ruc_formatted': f"{components.ruc_emisor}-{components.dv_ruc}",
        'tipo_documento': components.tipo_documento,
        'tipo_documento_descripcion': components.get_tipo_documento_descripcion(),
        'establecimiento': components.establecimiento,
        'punto_expedicion': components.punto_expedicion,
        'numero_documento': components.get_numero_documento_int(),
        'fecha_emision': components.fecha_emision,
        'fecha_emision_formatted': format_fecha_display(components.fecha_emision),
        'tipo_emision': components.tipo_emision,
        'tipo_emision_descripcion': components.get_tipo_emision_descripcion(),
        'codigo_seguridad': components.codigo_seguridad,
        'dv_cdc': components.dv_cdc,
        'summary': get_components_summary(components),
    }


def format_fecha_display(fecha_str: str) -> str:
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


def create_cdc_report(cdcs: List[str]) -> Dict[str, Any]:
    """
    Crea un reporte completo sobre una lista de CDCs.

    Args:
        cdcs: Lista de CDCs a analizar

    Returns:
        Dict: Reporte completo con estadísticas y análisis

    Examples:
        >>> report = create_cdc_report(["cdc1", "cdc2", "cdc3"])
        >>> print(report['summary']['total_cdcs'])
    """
    if not cdcs:
        return {
            'summary': {
                'total_cdcs': 0,
                'valid_cdcs': 0,
                'invalid_cdcs': 0,
                'validation_rate': 0.0
            },
            'details': [],
            'statistics': {},
            'errors': []
        }

    # Procesar cada CDC
    details = []
    valid_count = 0
    errors = []

    for i, cdc in enumerate(cdcs):
        try:
            info = get_cdc_info(cdc)
            details.append(info)
            if info['valid']:
                valid_count += 1
        except Exception as e:
            error_info = {
                'index': i,
                'cdc': cdc,
                'error': str(e)
            }
            errors.append(error_info)
            details.append({
                'valid': False,
                'cdc': cdc,
                'error': str(e)
            })

    # Calcular estadísticas
    from .validator import get_cdc_statistics
    statistics = get_cdc_statistics(cdcs)

    # Crear resumen
    summary = {
        'total_cdcs': len(cdcs),
        'valid_cdcs': valid_count,
        'invalid_cdcs': len(cdcs) - valid_count,
        'validation_rate': (valid_count / len(cdcs)) * 100 if cdcs else 0.0,
        'processing_errors': len(errors)
    }

    return {
        'summary': summary,
        'details': details,
        'statistics': statistics,
        'errors': errors,
        'generated_at': datetime.now().isoformat()
    }


def format_cdc_table(cdcs: List[str], max_rows: int = 20) -> List[Dict[str, str]]:
    """
    Formatea una lista de CDCs como tabla para visualización.

    Args:
        cdcs: Lista de CDCs
        max_rows: Número máximo de filas a mostrar

    Returns:
        List[Dict]: Lista de filas formateadas para tabla

    Examples:
        >>> table = format_cdc_table(["cdc1", "cdc2"])
        >>> for row in table:
        ...     print(row['cdc'], row['valid'], row['tipo_documento'])
    """
    table_rows = []

    for i, cdc in enumerate(cdcs[:max_rows]):
        try:
            info = get_cdc_info(cdc)

            if info['valid']:
                row = {
                    'index': str(i + 1),
                    'cdc': cdc[:20] + "..." if len(cdc) > 20 else cdc,
                    'valid': '✅',
                    'ruc_emisor': info['ruc_emisor'],
                    'tipo_documento': info['tipo_documento_descripcion'] or info['tipo_documento'],
                    'fecha_emision': info['fecha_emision_formatted'],
                    'numero_documento': str(info['numero_documento']),
                }
            else:
                row = {
                    'index': str(i + 1),
                    'cdc': cdc[:20] + "..." if len(cdc) > 20 else cdc,
                    'valid': '❌',
                    'ruc_emisor': 'N/A',
                    'tipo_documento': 'N/A',
                    'fecha_emision': 'N/A',
                    'numero_documento': 'N/A',
                    'error': info.get('error', 'Error desconocido')[:50]
                }

        except Exception as e:
            row = {
                'index': str(i + 1),
                'cdc': cdc[:20] + "..." if len(cdc) > 20 else cdc,
                'valid': '❌',
                'ruc_emisor': 'N/A',
                'tipo_documento': 'N/A',
                'fecha_emision': 'N/A',
                'numero_documento': 'N/A',
                'error': str(e)[:50]
            }

        table_rows.append(row)

    return table_rows


def compare_cdcs(cdc1: str, cdc2: str) -> Dict[str, Any]:
    """
    Compara dos CDCs y muestra las diferencias.

    Args:
        cdc1: Primer CDC
        cdc2: Segundo CDC

    Returns:
        Dict: Comparación detallada de los CDCs

    Examples:
        >>> comparison = compare_cdcs("cdc1", "cdc2")
        >>> print(comparison['differences'])
    """
    try:
        info1 = get_cdc_info(cdc1)
        info2 = get_cdc_info(cdc2)

        if not info1['valid'] or not info2['valid']:
            return {
                'comparison_possible': False,
                'cdc1_valid': info1['valid'],
                'cdc2_valid': info2['valid'],
                'cdc1_error': info1.get('error'),
                'cdc2_error': info2.get('error')
            }

        # Comparar componentes
        components1 = extract_cdc_components(cdc1)
        components2 = extract_cdc_components(cdc2)

        from .components import compare_components
        component_comparison = compare_components(components1, components2)

        # Identificar diferencias
        differences = []
        for component, are_equal in component_comparison.items():
            if not are_equal:
                val1 = getattr(components1, component)
                val2 = getattr(components2, component)
                differences.append({
                    'component': component,
                    'cdc1_value': val1,
                    'cdc2_value': val2
                })

        return {
            'comparison_possible': True,
            'are_identical': len(differences) == 0,
            'differences_count': len(differences),
            'differences': differences,
            'component_comparison': component_comparison,
            'cdc1_info': info1,
            'cdc2_info': info2
        }

    except Exception as e:
        return {
            'comparison_possible': False,
            'error': str(e)
        }


# ===================================================================
# FUNCIONES DE TESTING Y GENERACIÓN
# ===================================================================

def generate_test_cdc(
    ruc_base: Optional[str] = None,
    tipo_documento: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Genera un CDC válido para testing/desarrollo.

    Args:
        ruc_base: RUC base opcional (auto-generado si None)
        tipo_documento: Tipo de documento opcional (FE por defecto)

    Returns:
        Tuple[str, Dict]: (cdc, información_detallada)

    Examples:
        >>> cdc, info = generate_test_cdc()
        >>> print(len(cdc))  # 44
        >>> print(info['tipo_documento_descripcion'])
    """
    from ..ruc_utils import generate_test_ruc
    from .generator import generate_cdc

    # Generar RUC si no se proporciona
    if ruc_base is None:
        ruc_base, _, _ = generate_test_ruc()

    # Usar FE por defecto
    if tipo_documento is None:
        tipo_documento = TipoDocumento.FACTURA_ELECTRONICA.value

    # Crear request con datos de testing
    request = CdcGenerationRequest(
        ruc_emisor=ruc_base,
        tipo_documento=tipo_documento,
        establecimiento="001",
        punto_expedicion="001",
        numero_documento=1,
        fecha_emision=datetime.now(),
        tipo_emision=TipoEmision.NORMAL.value
    )

    # Generar CDC
    cdc = generate_cdc(request)

    # Obtener información detallada
    info = get_cdc_info(cdc)

    return cdc, info


def generate_test_cdc_batch(count: int = 10) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Genera múltiples CDCs de prueba.

    Args:
        count: Número de CDCs a generar

    Returns:
        List[Tuple]: Lista de (cdc, info) generados

    Examples:
        >>> batch = generate_test_cdc_batch(5)
        >>> print(f"Generados {len(batch)} CDCs")
    """
    cdcs = []
    tipos_documento = list(TipoDocumento)

    for i in range(count):
        # Alternar tipos de documento
        tipo = tipos_documento[i % len(tipos_documento)]

        try:
            cdc, info = generate_test_cdc(tipo_documento=tipo.value)
            cdcs.append((cdc, info))
        except Exception as e:
            # Si falla, usar valores por defecto
            try:
                cdc, info = generate_test_cdc()
                cdcs.append((cdc, info))
            except:
                continue  # Omitir si falla completamente

    return cdcs


def validate_and_format_cdc_list(cdcs: List[str]) -> Dict[str, Any]:
    """
    Valida y formatea una lista de CDCs con resumen.

    Args:
        cdcs: Lista de CDCs a procesar

    Returns:
        Dict: Resultados procesados con formato y validación

    Examples:
        >>> result = validate_and_format_cdc_list(["cdc1", "cdc2"])
        >>> print(result['summary']['valid_count'])
    """
    processed_cdcs = []
    valid_count = 0

    for cdc in cdcs:
        try:
            info = get_cdc_info(cdc)
            processed_info = {
                'cdc_original': cdc,
                'cdc_formatted': format_cdc_display(cdc) if info['valid'] else cdc,
                'is_valid': info['valid'],
                'error': info.get('error'),
                'components': info if info['valid'] else None
            }
            processed_cdcs.append(processed_info)

            if info['valid']:
                valid_count += 1

        except Exception as e:
            processed_cdcs.append({
                'cdc_original': cdc,
                'cdc_formatted': cdc,
                'is_valid': False,
                'error': str(e),
                'components': None
            })

    return {
        'processed_cdcs': processed_cdcs,
        'summary': {
            'total_count': len(cdcs),
            'valid_count': valid_count,
            'invalid_count': len(cdcs) - valid_count,
            'success_rate': (valid_count / len(cdcs)) * 100 if cdcs else 0
        }
    }


# ===================================================================
# CONSTANTES PARA EXPORT
# ===================================================================

__all__ = [
    # Funciones de formateo
    'format_cdc_display',
    'get_cdc_info',
    'format_fecha_display',

    # Funciones de reporte
    'create_cdc_report',
    'format_cdc_table',
    'compare_cdcs',

    # Funciones de testing
    'generate_test_cdc',
    'generate_test_cdc_batch',
    'validate_and_format_cdc_list',
]
