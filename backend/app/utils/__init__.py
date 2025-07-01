"""
Módulo de utilidades para el Sistema de Gestión de Documentos SIFEN.

Este módulo centraliza todas las utilidades comunes necesarias para el manejo
de documentos electrónicos según las especificaciones SIFEN v150 de Paraguay.

MÓDULOS DISPONIBLES:
- ruc_utils: Validación y manejo de RUC paraguayo
- cdc: Generación y validación de Códigos de Control (CDC) 
- date_utils: Utilidades para fechas Paraguay (zona horaria, formatos)
- constants: Constantes SIFEN y configuraciones oficiales

USO RECOMENDADO:
    from app.utils import ruc_utils, constants
    from app.utils.ruc_utils import validate_ruc_complete, calculate_dv
    from app.utils.constants import TIPOS_DOCUMENTO, DEPARTAMENTOS_PARAGUAY

DEPENDENCIAS:
- Python 3.8+
- typing (built-in)
- datetime (built-in)  
- re (built-in)
- dataclasses (built-in)

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

# ===================================================================
# IMPORTS PRINCIPALES DE LOS SUBMÓDULOS
# ===================================================================

# Importaciones principales para acceso directo desde el módulo
from .ruc_utils import (
    # Clases principales
    RucValidationResult,

    # Funciones de validación
    validate_ruc_complete,
    calculate_dv,
    format_ruc,
    is_valid_ruc,

    # Utilidades específicas
    extract_ruc_parts,
    generate_test_ruc,
    get_validation_summary,

    # Constantes RUC
    RUC_BASE_LENGTH,
    DV_LENGTH,
    RUC_COMPLETE_LENGTH,
)

from .cdc import (
    # Enumeraciones
    TipoDocumento,
    TipoEmision,

    # Clases de datos
    CdcComponents,
    CdcGenerationRequest,
    CdcValidationResult,

    # Funciones principales
    generate_cdc,
    validate_cdc,
    extract_cdc_components,
    calculate_cdc_dv,
    generate_security_code,
    is_valid_cdc,

    # Utilidades
    format_cdc_display,
    get_cdc_info,
    generate_test_cdc,

    # Funciones de testing
    validate_cdc_batch,
    get_cdc_statistics,

    # Constantes CDC
    CDC_LENGTH,
    CDC_COMPONENT_LENGTHS,
)

from .date_utils import (
    # Enumeraciones
    TipoFecha,
    EstadoValidacionFecha,

    # Clases de datos
    FechaValidationResult,
    RangoFechas,

    # Funciones de zona horaria
    get_paraguay_timezone,
    get_current_paraguay_datetime,
    get_current_paraguay_date,
    convert_to_paraguay_time,

    # Funciones de formateo
    format_sifen_date,
    format_sifen_datetime,
    format_cdc_date,

    # Funciones de parsing
    parse_sifen_date,
    parse_sifen_datetime,
    parse_flexible_datetime,

    # Funciones de validación
    validate_fecha_emision,
    is_valid_sifen_date_format,
    is_valid_sifen_datetime_format,

    # Funciones de cálculo temporal
    calculate_document_delay,
    get_document_deadline,
    is_within_normal_deadline,

    # Constantes
    PARAGUAY_TIMEZONE,
    SIFEN_TIME_LIMITS,
)

from .constants import (
    # Información del sistema
    SIFEN_VERSION,
    SIFEN_NAMESPACE,
    SIFEN_URLS,
    PAIS_INFO,

    # Enumeraciones principales
    TipoDocumentoElectronico,
    CodigoRespuestaSifen,
    MonedaOperacion,
    EstadoDocumento,

    # Diccionarios de códigos
    TIPOS_DOCUMENTO,
    TIPOS_EMISION,
    MONEDAS_SIFEN,
    DEPARTAMENTOS_PARAGUAY,

    # Listas de validación
    CODIGOS_DOCUMENTO_VALIDOS,
    TASAS_IVA_VALIDAS,
    CODIGOS_EXITOSOS,

    # Patrones y límites
    VALIDATION_PATTERNS,
    LONGITUDES_CAMPO,
    LIMITES_NUMERICOS,

    # Funciones de utilidad
    get_descripcion_documento,
    get_descripcion_departamento,
    is_valid_tipo_documento,
    is_valid_tasa_iva,
    get_validation_pattern,
)


# ===================================================================
# INFORMACIÓN DEL MÓDULO
# ===================================================================

__version__ = "1.0.0"
__author__ = "Sistema de Gestión de Documentos"
__email__ = "dev@sistema-documentos.py"
__status__ = "Production"

# Metadatos para introspección
__module_info__ = {
    "name": "utils",
    "description": "Utilidades para Sistema de Gestión de Documentos SIFEN",
    "version": __version__,
    "python_requires": ">=3.8",
    "implemented_modules": [
        "ruc_utils",     # ✅ Implementado
        "cdc",           # ✅ Implementado (modular)
        "date_utils",    # ✅ Implementado
        "constants",     # ✅ Implementado
    ],
    "pending_modules": [
        # Todos los módulos principales completados
    ]
}


# ===================================================================
# FUNCIONES DE UTILIDAD DEL MÓDULO
# ===================================================================

def get_module_status() -> dict:
    """
    Obtiene el estado actual de implementación del módulo utils.

    Returns:
        dict: Estado de cada submódulo con información detallada

    Examples:
        >>> status = get_module_status()
        >>> print(status['ruc_utils']['status'])  # 'implemented'
    """
    return {
        'ruc_utils': {
            'status': 'implemented',
            'version': '1.0.0',
            'functions': [
                'validate_ruc_complete',
                'calculate_dv',
                'format_ruc',
                'is_valid_ruc',
                'extract_ruc_parts',
                'generate_test_ruc',
            ],
            'classes': ['RucValidationResult'],
            'description': 'Validación completa de RUC paraguayo con algoritmo módulo 11'
        },
        'cdc': {
            'status': 'implemented',
            'version': '1.0.0',
            'functions': [
                'generate_cdc',
                'validate_cdc',
                'extract_cdc_components',
                'calculate_cdc_dv',
                'generate_security_code',
                'is_valid_cdc',
                'format_cdc_display',
                'get_cdc_info',
                'generate_test_cdc',
            ],
            'classes': ['CdcComponents', 'CdcGenerationRequest', 'CdcValidationResult'],
            'enums': ['TipoDocumento', 'TipoEmision'],
            'description': 'Generación y validación completa de CDCs SIFEN de 44 dígitos'
        },
        'date_utils': {
            'status': 'implemented',
            'version': '1.0.0',
            'functions': [
                'get_current_paraguay_datetime',
                'format_sifen_date',
                'format_sifen_datetime',
                'parse_flexible_datetime',
                'validate_fecha_emision',
                'calculate_document_delay',
                'convert_to_paraguay_time',
            ],
            'classes': ['FechaValidationResult', 'RangoFechas'],
            'enums': ['TipoFecha', 'EstadoValidacionFecha'],
            'description': 'Manejo completo de fechas Paraguay con zona horaria y validaciones SIFEN'
        },
        'constants': {
            'status': 'implemented',
            'version': '1.0.0',
            'functions': [
                'get_descripcion_documento',
                'get_descripcion_departamento',
                'is_valid_tipo_documento',
                'is_valid_tasa_iva',
                'get_validation_pattern',
                'get_all_document_types',
                'get_all_departments',
            ],
            'enums': ['TipoDocumentoElectronico', 'CodigoRespuestaSifen', 'MonedaOperacion'],
            'constants': ['TIPOS_DOCUMENTO', 'DEPARTAMENTOS_PARAGUAY', 'VALIDATION_PATTERNS'],
            'description': 'Constantes completas SIFEN v150 con códigos oficiales Paraguay'
        },
    }


def validate_module_dependencies() -> bool:
    """
    Valida que todas las dependencias del módulo estén disponibles.

    Returns:
        bool: True si todas las dependencias están satisfechas

    Raises:
        ImportError: Si falta alguna dependencia crítica
    """
    required_modules = ['re', 'typing', 'dataclasses', 'datetime']

    try:
        for module in required_modules:
            __import__(module)
        return True
    except ImportError as e:
        raise ImportError(f"Dependencia requerida no encontrada: {e}")


def run_basic_tests() -> dict:
    """
    Ejecuta pruebas básicas de todos los submódulos.

    Returns:
        dict: Resultados de las pruebas
    """
    results = {
        'all_passed': True,
        'tests': [],
        'summary': {}
    }

    try:
        # Test RUC
        ruc_result = validate_ruc_complete("80000001")
        results['tests'].append({
            'module': 'ruc_utils',
            'test': 'validate_ruc_complete',
            'passed': ruc_result.is_valid,
            'details': f"RUC válido: {ruc_result.is_valid}"
        })

        # Test CDC
        test_cdc, _ = generate_test_cdc()
        cdc_validation = validate_cdc(test_cdc)
        results['tests'].append({
            'module': 'cdc',
            'test': 'generate_and_validate_cdc',
            'passed': cdc_validation.is_valid and len(test_cdc) == CDC_LENGTH,
            'details': f"CDC generado y validado: {len(test_cdc)} caracteres"
        })

        # Test fecha
        now_py = get_current_paraguay_datetime()
        fecha_formatted = format_sifen_datetime(now_py)
        results['tests'].append({
            'module': 'date_utils',
            'test': 'paraguay_datetime_format',
            'passed': is_valid_sifen_datetime_format(fecha_formatted),
            'details': f"Fecha Paraguay formateada: {fecha_formatted}"
        })

        # Test constantes
        fe_desc = get_descripcion_documento("01")
        central_desc = get_descripcion_departamento("11")
        results['tests'].append({
            'module': 'constants',
            'test': 'descripcion_lookup',
            'passed': fe_desc == "Factura Electrónica" and central_desc == "Central",
            'details': f"Descripciones correctas: {fe_desc}, {central_desc}"
        })

    except Exception as e:
        results['tests'].append({
            'module': 'general',
            'test': 'exception_handling',
            'passed': False,
            'details': f"Error: {str(e)}"
        })
        results['all_passed'] = False

    # Compilar resumen
    passed_count = sum(1 for test in results['tests'] if test['passed'])
    results['summary'] = {
        'total_tests': len(results['tests']),
        'passed': passed_count,
        'failed': len(results['tests']) - passed_count,
        'success_rate': (passed_count / len(results['tests'])) * 100 if results['tests'] else 0
    }

    results['all_passed'] = passed_count == len(results['tests'])

    return results


# ===================================================================
# EXPORTS PÚBLICOS
# ===================================================================

__all__ = [
    # Clases de datos RUC
    'RucValidationResult',

    # Funciones RUC
    'validate_ruc_complete',
    'calculate_dv',
    'format_ruc',
    'is_valid_ruc',
    'extract_ruc_parts',
    'generate_test_ruc',
    'get_validation_summary',

    # Constantes RUC
    'RUC_BASE_LENGTH',
    'DV_LENGTH',
    'RUC_COMPLETE_LENGTH',

    # Enumeraciones CDC
    'TipoDocumento',
    'TipoEmision',

    # Clases de datos CDC
    'CdcComponents',
    'CdcGenerationRequest',
    'CdcValidationResult',

    # Funciones CDC principales
    'generate_cdc',
    'validate_cdc',
    'extract_cdc_components',
    'calculate_cdc_dv',
    'generate_security_code',
    'is_valid_cdc',

    # Utilidades CDC
    'format_cdc_display',
    'get_cdc_info',
    'generate_test_cdc',
    'debug_cdc_generation',
    'validate_cdc_batch',
    'get_cdc_statistics',

    # Constantes CDC
    'CDC_LENGTH',
    'CDC_COMPONENT_LENGTHS',

    # Enumeraciones de fechas
    'TipoFecha',
    'EstadoValidacionFecha',

    # Clases de datos fechas
    'FechaValidationResult',
    'RangoFechas',

    # Funciones de zona horaria
    'get_paraguay_timezone',
    'get_current_paraguay_datetime',
    'get_current_paraguay_date',
    'convert_to_paraguay_time',

    # Funciones de formateo fechas
    'format_sifen_date',
    'format_sifen_datetime',
    'format_cdc_date',
    'format_date_spanish',

    # Funciones de parsing fechas
    'parse_sifen_date',
    'parse_sifen_datetime',
    'parse_flexible_datetime',

    # Funciones de validación fechas
    'validate_fecha_emision',
    'is_valid_sifen_date_format',
    'is_valid_sifen_datetime_format',

    # Funciones de cálculo temporal
    'calculate_document_delay',
    'get_document_deadline',
    'is_within_normal_deadline',

    # Constantes fechas
    'PARAGUAY_TIMEZONE',
    'SIFEN_TIME_LIMITS',

    # Información del sistema SIFEN
    'SIFEN_VERSION',
    'SIFEN_NAMESPACE',
    'SIFEN_URLS',
    'PAIS_INFO',

    # Enumeraciones de constantes
    'TipoDocumentoElectronico',
    'CodigoRespuestaSifen',
    'MonedaOperacion',
    'EstadoDocumento',

    # Diccionarios de códigos oficiales
    'TIPOS_DOCUMENTO',
    'TIPOS_EMISION',
    'MONEDAS_SIFEN',
    'DEPARTAMENTOS_PARAGUAY',

    # Listas de validación
    'CODIGOS_DOCUMENTO_VALIDOS',
    'TASAS_IVA_VALIDAS',
    'CODIGOS_EXITOSOS',

    # Patrones y límites de validación
    'VALIDATION_PATTERNS',
    'LONGITUDES_CAMPO',
    'LIMITES_NUMERICOS',

    # Funciones de utilidad constantes
    'get_descripcion_documento',
    'get_descripcion_departamento',
    'is_valid_tipo_documento',
    'is_valid_tasa_iva',
    'get_validation_pattern',

    # Utilidades del módulo
    'get_module_status',
    'validate_module_dependencies',
    'run_basic_tests',

    # Metadatos
    '__version__',
    '__author__',
    '__module_info__',
]


# ===================================================================
# INICIALIZACIÓN DEL MÓDULO
# ===================================================================

# Validar dependencias al importar
try:
    validate_module_dependencies()
    _module_status = "OK"
except ImportError as e:
    _module_status = f"DEPENDENCY_ERROR: {e}"
    import warnings
    warnings.warn(
        f"Módulo utils: {_module_status}",
        category=ImportWarning
    )

# Información de inicialización
_initialization_info = {
    'module': 'utils',
    'version': __version__,
    'status': _module_status,
    'available_modules': ['ruc_utils', 'cdc', 'date_utils', 'constants'],
    'total_functions': len([name for name in __all__ if not name.startswith('_')]),
    'ready': _module_status == "OK"
}
