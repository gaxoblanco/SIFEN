"""
Extracción y manejo de componentes de CDC SIFEN.

Este módulo se especializa en la extracción y manipulación de los
componentes individuales que conforman un CDC (Código de Control
de Documento) según especificaciones SIFEN v150.

RESPONSABILIDADES:
- Extraer componentes individuales de un CDC completo
- Reconstruir CDC a partir de componentes
- Validar longitudes de componentes
- Proporcionar utilidades de conversión

ESTRUCTURA CDC:
[RUC_8][DV_1][TIPO_2][EST_3][PE_3][NUM_7][FECHA_8][EMISION_1][SEG_9][DV_CDC_1]

DEPENDENCIAS:
- types.py: Para tipos de datos y constantes

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

from typing import Tuple, List, Dict, Any

# Imports locales del módulo CDC
from .types import (
    CdcComponents,
    CDC_LENGTH,
    CDC_COMPONENT_LENGTHS,
)


# ===================================================================
# FUNCIÓN PRINCIPAL DE EXTRACCIÓN
# ===================================================================

def extract_cdc_components(cdc: str) -> CdcComponents:
    """
    Extrae los componentes individuales de un CDC.

    Descompone un CDC de 44 dígitos en sus componentes constituyentes
    según la especificación SIFEN v150.

    Args:
        cdc: CDC de 44 dígitos

    Returns:
        CdcComponents: Componentes extraídos

    Raises:
        ValueError: Si el CDC no tiene el formato correcto

    Examples:
        >>> components = extract_cdc_components("01234567890123456789012345678901234567890123")
        >>> print(components.ruc_emisor)  # "01234567"
        >>> print(components.tipo_documento)  # "89"
    """
    if len(cdc) != CDC_LENGTH:
        raise ValueError(
            f"CDC debe tener {CDC_LENGTH} caracteres, recibido: {len(cdc)}")

    if not cdc.isdigit():
        raise ValueError("CDC debe contener solo dígitos numéricos")

    # Extraer cada componente según su posición y longitud
    pos = 0

    # RUC emisor (8 dígitos)
    ruc_emisor = cdc[pos:pos + CDC_COMPONENT_LENGTHS['ruc']]
    pos += CDC_COMPONENT_LENGTHS['ruc']

    # Dígito verificador RUC (1 dígito)
    dv_ruc = cdc[pos:pos + CDC_COMPONENT_LENGTHS['dv_ruc']]
    pos += CDC_COMPONENT_LENGTHS['dv_ruc']

    # Tipo de documento (2 dígitos)
    tipo_documento = cdc[pos:pos + CDC_COMPONENT_LENGTHS['tipo']]
    pos += CDC_COMPONENT_LENGTHS['tipo']

    # Establecimiento (3 dígitos)
    establecimiento = cdc[pos:pos + CDC_COMPONENT_LENGTHS['est']]
    pos += CDC_COMPONENT_LENGTHS['est']

    # Punto de expedición (3 dígitos)
    punto_expedicion = cdc[pos:pos + CDC_COMPONENT_LENGTHS['pe']]
    pos += CDC_COMPONENT_LENGTHS['pe']

    # Número de documento (7 dígitos)
    numero_documento = cdc[pos:pos + CDC_COMPONENT_LENGTHS['num']]
    pos += CDC_COMPONENT_LENGTHS['num']

    # Fecha de emisión (8 dígitos)
    fecha_emision = cdc[pos:pos + CDC_COMPONENT_LENGTHS['fecha']]
    pos += CDC_COMPONENT_LENGTHS['fecha']

    # Tipo de emisión (1 dígito)
    tipo_emision = cdc[pos:pos + CDC_COMPONENT_LENGTHS['emision']]
    pos += CDC_COMPONENT_LENGTHS['emision']

    # Código de seguridad (9 dígitos)
    codigo_seguridad = cdc[pos:pos + CDC_COMPONENT_LENGTHS['seguridad']]
    pos += CDC_COMPONENT_LENGTHS['seguridad']

    # Dígito verificador CDC (1 dígito)
    dv_cdc = cdc[pos:pos + CDC_COMPONENT_LENGTHS['dv_cdc']]

    return CdcComponents(
        ruc_emisor=ruc_emisor,
        dv_ruc=dv_ruc,
        tipo_documento=tipo_documento,
        establecimiento=establecimiento,
        punto_expedicion=punto_expedicion,
        numero_documento=numero_documento,
        fecha_emision=fecha_emision,
        tipo_emision=tipo_emision,
        codigo_seguridad=codigo_seguridad,
        dv_cdc=dv_cdc
    )


def reconstruct_cdc(components: CdcComponents) -> str:
    """
    Reconstruye un CDC a partir de sus componentes.

    Args:
        components: Componentes del CDC

    Returns:
        str: CDC reconstruido

    Raises:
        ValueError: Si los componentes no son válidos

    Examples:
        >>> components = CdcComponents(...)
        >>> cdc = reconstruct_cdc(components)
        >>> print(len(cdc))  # 44
    """
    # Validar longitudes de componentes
    if not components.validate_lengths():
        raise ValueError("Los componentes no tienen las longitudes correctas")

    return components.to_cdc()


def extract_cdc_parts(cdc: str) -> Tuple[str, str, str, str, str, str, str, str, str, str]:
    """
    Extrae los componentes de un CDC como tupla.

    Función de conveniencia que retorna los componentes como tupla
    en lugar de objeto CdcComponents.

    Args:
        cdc: CDC de 44 dígitos

    Returns:
        Tuple con los 10 componentes del CDC

    Examples:
        >>> parts = extract_cdc_parts("01234567890123456789012345678901234567890123")
        >>> ruc_emisor, dv_ruc, tipo_doc, est, pe, num, fecha, emision, seg, dv = parts
    """
    components = extract_cdc_components(cdc)

    return (
        components.ruc_emisor,
        components.dv_ruc,
        components.tipo_documento,
        components.establecimiento,
        components.punto_expedicion,
        components.numero_documento,
        components.fecha_emision,
        components.tipo_emision,
        components.codigo_seguridad,
        components.dv_cdc
    )


def get_component_info(cdc: str, component_name: str) -> str:
    """
    Obtiene un componente específico de un CDC.

    Args:
        cdc: CDC de 44 dígitos
        component_name: Nombre del componente a extraer

    Returns:
        str: Valor del componente solicitado

    Raises:
        ValueError: Si el CDC es inválido o el componente no existe

    Examples:
        >>> ruc = get_component_info("01234567890123456789012345678901234567890123", "ruc_emisor")
        >>> print(ruc)  # "01234567"
    """
    components = extract_cdc_components(cdc)

    # Mapeo de nombres de componentes
    component_map = {
        'ruc_emisor': components.ruc_emisor,
        'dv_ruc': components.dv_ruc,
        'tipo_documento': components.tipo_documento,
        'establecimiento': components.establecimiento,
        'punto_expedicion': components.punto_expedicion,
        'numero_documento': components.numero_documento,
        'fecha_emision': components.fecha_emision,
        'tipo_emision': components.tipo_emision,
        'codigo_seguridad': components.codigo_seguridad,
        'dv_cdc': components.dv_cdc,
        'ruc_completo': components.get_ruc_completo(),
    }

    if component_name not in component_map:
        available_components = ', '.join(component_map.keys())
        raise ValueError(
            f"Componente '{component_name}' no existe. Disponibles: {available_components}")

    return component_map[component_name]


def validate_component_lengths(components: CdcComponents) -> Dict[str, bool]:
    """
    Valida las longitudes de todos los componentes individualmente.

    Args:
        components: Componentes a validar

    Returns:
        Dict con resultado de validación por componente

    Examples:
        >>> components = extract_cdc_components("01234567890123456789012345678901234567890123")
        >>> validation = validate_component_lengths(components)
        >>> print(validation['ruc_emisor'])  # True o False
    """
    return {
        'ruc_emisor': len(components.ruc_emisor) == CDC_COMPONENT_LENGTHS['ruc'],
        'dv_ruc': len(components.dv_ruc) == CDC_COMPONENT_LENGTHS['dv_ruc'],
        'tipo_documento': len(components.tipo_documento) == CDC_COMPONENT_LENGTHS['tipo'],
        'establecimiento': len(components.establecimiento) == CDC_COMPONENT_LENGTHS['est'],
        'punto_expedicion': len(components.punto_expedicion) == CDC_COMPONENT_LENGTHS['pe'],
        'numero_documento': len(components.numero_documento) == CDC_COMPONENT_LENGTHS['num'],
        'fecha_emision': len(components.fecha_emision) == CDC_COMPONENT_LENGTHS['fecha'],
        'tipo_emision': len(components.tipo_emision) == CDC_COMPONENT_LENGTHS['emision'],
        'codigo_seguridad': len(components.codigo_seguridad) == CDC_COMPONENT_LENGTHS['seguridad'],
        'dv_cdc': len(components.dv_cdc) == CDC_COMPONENT_LENGTHS['dv_cdc'],
    }


def get_component_positions() -> Dict[str, Dict[str, int]]:
    """
    Obtiene las posiciones de cada componente en el CDC.

    Returns:
        Dict con posiciones de inicio y fin de cada componente

    Examples:
        >>> positions = get_component_positions()
        >>> print(positions['ruc_emisor'])  # {'start': 0, 'end': 8, 'length': 8}
    """
    positions = {}
    pos = 0

    for component_name, length in CDC_COMPONENT_LENGTHS.items():
        positions[component_name] = {
            'start': pos,
            'end': pos + length,
            'length': length
        }
        pos += length

    return positions


def extract_components_by_position(cdc: str, start: int, length: int) -> str:
    """
    Extrae un componente específico por posición.

    Args:
        cdc: CDC completo
        start: Posición de inicio (0-based)
        length: Longitud del componente

    Returns:
        str: Componente extraído

    Raises:
        ValueError: Si las posiciones son inválidas

    Examples:
        >>> # Extraer RUC emisor (posición 0, longitud 8)
        >>> ruc = extract_components_by_position("01234567890123456789012345678901234567890123", 0, 8)
        >>> print(ruc)  # "01234567"
    """
    if len(cdc) != CDC_LENGTH:
        raise ValueError(f"CDC debe tener {CDC_LENGTH} caracteres")

    if start < 0 or start >= len(cdc):
        raise ValueError(f"Posición de inicio inválida: {start}")

    if length <= 0:
        raise ValueError(f"Longitud debe ser positiva: {length}")

    if start + length > len(cdc):
        raise ValueError(
            f"La posición final ({start + length}) excede la longitud del CDC")

    return cdc[start:start + length]


def compare_components(components1: CdcComponents, components2: CdcComponents) -> Dict[str, bool]:
    """
    Compara dos conjuntos de componentes CDC.

    Args:
        components1: Primer conjunto de componentes
        components2: Segundo conjunto de componentes

    Returns:
        Dict con resultado de comparación por componente

    Examples:
        >>> comp1 = extract_cdc_components("cdc1")
        >>> comp2 = extract_cdc_components("cdc2") 
        >>> comparison = compare_components(comp1, comp2)
        >>> print(comparison['ruc_emisor'])  # True si son iguales
    """
    return {
        'ruc_emisor': components1.ruc_emisor == components2.ruc_emisor,
        'dv_ruc': components1.dv_ruc == components2.dv_ruc,
        'tipo_documento': components1.tipo_documento == components2.tipo_documento,
        'establecimiento': components1.establecimiento == components2.establecimiento,
        'punto_expedicion': components1.punto_expedicion == components2.punto_expedicion,
        'numero_documento': components1.numero_documento == components2.numero_documento,
        'fecha_emision': components1.fecha_emision == components2.fecha_emision,
        'tipo_emision': components1.tipo_emision == components2.tipo_emision,
        'codigo_seguridad': components1.codigo_seguridad == components2.codigo_seguridad,
        'dv_cdc': components1.dv_cdc == components2.dv_cdc,
    }


def get_components_summary(components: CdcComponents) -> Dict[str, Any]:
    """
    Obtiene un resumen legible de los componentes.

    Args:
        components: Componentes a resumir

    Returns:
        Dict con información legible de cada componente

    Examples:
        >>> components = extract_cdc_components("01234567890123456789012345678901234567890123")
        >>> summary = get_components_summary(components)
        >>> print(summary['ruc_info']['complete'])
    """
    return {
        'ruc_info': {
            'base': components.ruc_emisor,
            'dv': components.dv_ruc,
            'complete': components.get_ruc_completo(),
        },
        'document_info': {
            'type_code': components.tipo_documento,
            'type_description': components.get_tipo_documento_descripcion(),
            'establishment': components.establecimiento,
            'expedition_point': components.punto_expedicion,
            'document_number': components.get_numero_documento_int(),
        },
        'emission_info': {
            'date_raw': components.fecha_emision,
            'date_formatted': _format_fecha_display(components.fecha_emision),
            'emission_type': components.tipo_emision,
            'emission_description': components.get_tipo_emision_descripcion(),
        },
        'security_info': {
            'security_code': components.codigo_seguridad,
            'cdc_dv': components.dv_cdc,
        },
        'validation_info': {
            'lengths_valid': components.validate_lengths(),
            'component_count': 10,
            'total_length': len(components.to_cdc()),
        }
    }


def extract_multiple_components(cdc: str, component_names: List[str]) -> Dict[str, str]:
    """
    Extrae múltiples componentes específicos de una vez.

    Args:
        cdc: CDC de 44 dígitos
        component_names: Lista de nombres de componentes a extraer

    Returns:
        Dict con los componentes solicitados

    Examples:
        >>> components = extract_multiple_components("cdc", ["ruc_emisor", "tipo_documento"])
        >>> print(components['ruc_emisor'])
    """
    all_components = extract_cdc_components(cdc)
    result = {}

    for component_name in component_names:
        try:
            result[component_name] = get_component_info(cdc, component_name)
        except ValueError:
            # Componente no existe, omitir
            continue

    return result


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
# UTILIDADES DE DEBUGGING Y ANÁLISIS
# ===================================================================

def debug_cdc_structure(cdc: str) -> Dict[str, Any]:
    """
    Proporciona información detallada sobre la estructura de un CDC.

    Args:
        cdc: CDC a analizar

    Returns:
        Dict con información de debugging detallada

    Examples:
        >>> debug_info = debug_cdc_structure("01234567890123456789012345678901234567890123")
        >>> print(debug_info['structure'])
    """
    if len(cdc) != CDC_LENGTH:
        return {
            'valid_length': False,
            'provided_length': len(cdc),
            'expected_length': CDC_LENGTH,
            'error': f"CDC debe tener {CDC_LENGTH} caracteres"
        }

    try:
        components = extract_cdc_components(cdc)
        positions = get_component_positions()
        length_validation = validate_component_lengths(components)

        return {
            'valid_length': True,
            'cdc': cdc,
            'structure': {
                name: {
                    'value': getattr(components, name),
                    'position': positions[name],
                    'length_valid': length_validation[name],
                    'expected_length': CDC_COMPONENT_LENGTHS[name]
                }
                for name in CDC_COMPONENT_LENGTHS.keys()
            },
            'summary': get_components_summary(components),
            'reconstructed_cdc': components.to_cdc(),
            'reconstruction_matches': cdc == components.to_cdc()
        }

    except Exception as e:
        return {
            'valid_length': True,
            'cdc': cdc,
            'extraction_error': str(e),
            'structure': None
        }


def analyze_cdc_patterns(cdcs: List[str]) -> Dict[str, Any]:
    """
    Analiza patrones en una lista de CDCs.

    Args:
        cdcs: Lista de CDCs a analizar

    Returns:
        Dict con análisis de patrones encontrados

    Examples:
        >>> patterns = analyze_cdc_patterns(["cdc1", "cdc2", "cdc3"])
        >>> print(patterns['common_ruc_emisors'])
    """
    if not cdcs:
        return {
            'total_cdcs': 0,
            'valid_cdcs': 0,
            'patterns': {}
        }

    valid_components = []

    for cdc in cdcs:
        try:
            if len(cdc) == CDC_LENGTH and cdc.isdigit():
                components = extract_cdc_components(cdc)
                valid_components.append(components)
        except:
            continue

    if not valid_components:
        return {
            'total_cdcs': len(cdcs),
            'valid_cdcs': 0,
            'patterns': {}
        }

    # Analizar patrones
    patterns = {
        'ruc_emisors': {},
        'tipos_documento': {},
        'establecimientos': {},
        'puntos_expedicion': {},
        'tipos_emision': {},
    }

    for comp in valid_components:
        # Contar RUCs emisores
        ruc_complete = comp.get_ruc_completo()
        patterns['ruc_emisors'][ruc_complete] = patterns['ruc_emisors'].get(
            ruc_complete, 0) + 1

        # Contar tipos de documento
        tipo_desc = comp.get_tipo_documento_descripcion() or comp.tipo_documento
        patterns['tipos_documento'][tipo_desc] = patterns['tipos_documento'].get(
            tipo_desc, 0) + 1

        # Contar establecimientos
        patterns['establecimientos'][comp.establecimiento] = patterns['establecimientos'].get(
            comp.establecimiento, 0) + 1

        # Contar puntos de expedición
        patterns['puntos_expedicion'][comp.punto_expedicion] = patterns['puntos_expedicion'].get(
            comp.punto_expedicion, 0) + 1

        # Contar tipos de emisión
        emision_desc = comp.get_tipo_emision_descripcion() or comp.tipo_emision
        patterns['tipos_emision'][emision_desc] = patterns['tipos_emision'].get(
            emision_desc, 0) + 1

    return {
        'total_cdcs': len(cdcs),
        'valid_cdcs': len(valid_components),
        'patterns': patterns,
        'most_common': {
            'ruc_emisor': max(patterns['ruc_emisors'].items(), key=lambda x: x[1]) if patterns['ruc_emisors'] else None,
            'tipo_documento': max(patterns['tipos_documento'].items(), key=lambda x: x[1]) if patterns['tipos_documento'] else None,
            'establecimiento': max(patterns['establecimientos'].items(), key=lambda x: x[1]) if patterns['establecimientos'] else None,
        }
    }
