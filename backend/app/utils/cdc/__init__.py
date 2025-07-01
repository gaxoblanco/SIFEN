"""
Módulo CDC - Generación y Validación de Códigos de Control de Documentos SIFEN.

Este módulo proporciona funcionalidad completa para generar, validar y manipular
Códigos de Control de Documentos (CDC) según las especificaciones SIFEN v150
de Paraguay.

ARQUITECTURA MODULAR:
├── types.py        - Tipos de datos, enumeraciones y constantes
├── generator.py    - Generación principal de CDCs
├── validator.py    - Validación completa de CDCs
├── components.py   - Extracción y manejo de componentes
├── utils.py        - Utilidades de formateo y presentación
└── testing.py      - Funciones de testing y debugging (TODO)

CARACTERÍSTICAS PRINCIPALES:
✅ Generación completa de CDCs de 44 dígitos
✅ Validación integral según especificaciones SIFEN
✅ Extracción y análisis de componentes individuales
✅ Formateo y presentación legible
✅ Funciones de testing y debugging
✅ Procesamiento por lotes
✅ Reportes y estadísticas

ESTRUCTURA CDC (44 dígitos):
[RUC_8][DV_1][TIPO_2][EST_3][PE_3][NUM_7][FECHA_8][EMISION_1][SEG_9][DV_CDC_1]

CASOS DE USO PRINCIPALES:
1. Generar CDC para documentos electrónicos
2. Validar CDCs recibidos
3. Extraer información de CDCs existentes
4. Procesar lotes de CDCs
5. Generar reportes y estadísticas

EJEMPLOS DE USO:

>>> # Generar un CDC nuevo
>>> from app.utils.cdc import generate_cdc, CdcGenerationRequest, TipoDocumento
>>> request = CdcGenerationRequest(
...     ruc_emisor="80000001",
...     tipo_documento=TipoDocumento.FACTURA_ELECTRONICA.value,
...     establecimiento="001",
...     punto_expedicion="001",
...     numero_documento=123
... )
>>> cdc = generate_cdc(request)
>>> print(len(cdc))  # 44

>>> # Validar un CDC existente
>>> from app.utils.cdc import validate_cdc, get_cdc_info
>>> result = validate_cdc(cdc)
>>> print(result.is_valid)  # True
>>> info = get_cdc_info(cdc)
>>> print(info['tipo_documento_descripcion'])  # "Factura Electrónica"

>>> # Extraer componentes de un CDC
>>> from app.utils.cdc import extract_cdc_components
>>> components = extract_cdc_components(cdc)
>>> print(components.ruc_emisor)  # "80000001"
>>> print(components.get_ruc_completo())  # "800000016"

>>> # Procesar lotes de CDCs
>>> from app.utils.cdc import validate_cdc_batch, create_cdc_report
>>> cdcs = ["cdc1", "cdc2", "cdc3"]
>>> results = validate_cdc_batch(cdcs)
>>> report = create_cdc_report(cdcs)
>>> print(report['summary']['validation_rate'])

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

# ===================================================================
# IMPORTS PRINCIPALES DE LOS SUBMÓDULOS
# ===================================================================

# Tipos de datos y enumeraciones
from .types import (
    # Enumeraciones
    TipoDocumento,
    TipoEmision,

    # Clases de datos
    CdcComponents,
    CdcGenerationRequest,
    CdcValidationResult,

    # Códigos de error
    CdcErrorCode,

    # Constantes principales
    CDC_LENGTH,
    CDC_COMPONENT_LENGTHS,
)

# Generación de CDCs
from .generator import (
    # Función principal
    generate_cdc,

    # Funciones auxiliares
    calculate_cdc_dv,
    generate_security_code,
)

# Validación de CDCs
from .validator import (
    # Función principal
    validate_cdc,
    is_valid_cdc,

    # Funciones de lote
    validate_cdc_batch,
    get_cdc_statistics,
)

# Manejo de componentes
from .components import (
    # Función principal
    extract_cdc_components,

    # Funciones auxiliares
    extract_cdc_parts,
    get_component_info,
    reconstruct_cdc,

    # Funciones de análisis
    debug_cdc_structure,
    analyze_cdc_patterns,
)

# Utilidades y formateo
from .utils import (
    # Formateo y presentación
    format_cdc_display,
    get_cdc_info,
    format_fecha_display,

    # Reportes y análisis
    create_cdc_report,
    format_cdc_table,
    compare_cdcs,

    # Testing y generación
    generate_test_cdc,
    generate_test_cdc_batch,
    validate_and_format_cdc_list,
)


# ===================================================================
# INFORMACIÓN DEL MÓDULO
# ===================================================================

__version__ = "1.0.0"
__author__ = "Sistema de Gestión de Documentos"
__email__ = "dev@sistema-documentos.py"
__status__ = "Production"

# Metadatos del módulo CDC
__module_info__ = {
    "name": "cdc",
    "description": "Generación y validación de CDCs SIFEN Paraguay",
    "version": __version__,
    "python_requires": ">=3.8",
    "components": {
        "types": "Tipos de datos y enumeraciones",
        "generator": "Generación principal de CDCs",
        "validator": "Validación completa de CDCs",
        "components": "Extracción y manejo de componentes",
        "utils": "Utilidades de formateo y presentación",
        "testing": "Funciones de testing (TODO)"
    },
    "features": [
        "Generación de CDCs de 44 dígitos",
        "Validación según especificaciones SIFEN v150",
        "Extracción de componentes individuales",
        "Procesamiento por lotes",
        "Reportes y estadísticas",
        "Formateo para visualización",
        "Funciones de testing y debugging"
    ]
}


# ===================================================================
# FUNCIONES DE UTILIDAD DEL MÓDULO
# ===================================================================

def get_module_status() -> dict:
    """
    Obtiene el estado actual del módulo CDC.

    Returns:
        dict: Estado detallado de cada componente

    Examples:
        >>> status = get_module_status()
        >>> print(status['generator']['status'])  # 'implemented'
    """
    return {
        'types': {
            'status': 'implemented',
            'version': '1.0.0',
            'classes': ['TipoDocumento', 'TipoEmision', 'CdcComponents', 'CdcGenerationRequest', 'CdcValidationResult'],
            'description': 'Tipos de datos y enumeraciones completas'
        },
        'generator': {
            'status': 'implemented',
            'version': '1.0.0',
            'functions': ['generate_cdc', 'calculate_cdc_dv', 'generate_security_code'],
            'description': 'Generación completa de CDCs con validación'
        },
        'validator': {
            'status': 'implemented',
            'version': '1.0.0',
            'functions': ['validate_cdc', 'is_valid_cdc', 'validate_cdc_batch', 'get_cdc_statistics'],
            'description': 'Validación integral según especificaciones SIFEN'
        },
        'components': {
            'status': 'implemented',
            'version': '1.0.0',
            'functions': ['extract_cdc_components', 'extract_cdc_parts', 'reconstruct_cdc'],
            'description': 'Extracción y análisis de componentes CDC'
        },
        'utils': {
            'status': 'implemented',
            'version': '1.0.0',
            'functions': ['format_cdc_display', 'get_cdc_info', 'create_cdc_report'],
            'description': 'Utilidades de formateo y presentación'
        },
        'testing': {
            'status': 'pending',
            'priority': 'low',
            'description': 'Funciones especializadas de testing y debugging'
        }
    }


def validate_module_dependencies() -> bool:
    """
    Valida que todas las dependencias del módulo CDC estén disponibles.

    Returns:
        bool: True si todas las dependencias están satisfechas

    Raises:
        ImportError: Si falta alguna dependencia crítica
    """
    required_modules = [
        're', 'typing', 'dataclasses', 'datetime',
        'secrets', 'enum'
    ]

    try:
        for module in required_modules:
            __import__(module)

        # Verificar dependencia de RUC utils
        from ..ruc_utils import validate_ruc_complete, calculate_dv

        return True
    except ImportError as e:
        raise ImportError(f"Dependencia requerida no encontrada: {e}")


def run_self_test() -> dict:
    """
    Ejecuta una batería de pruebas básicas del módulo CDC.

    Returns:
        dict: Resultados de las pruebas

    Examples:
        >>> results = run_self_test()
        >>> print(results['all_passed'])  # True si todo funciona
    """
    tests = []

    try:
        # Test 1: Generar CDC de prueba
        cdc_test, info_test = generate_test_cdc()
        tests.append({
            'test': 'generate_test_cdc',
            'passed': len(cdc_test) == CDC_LENGTH and info_test['valid'],
            'details': f"CDC generado: {len(cdc_test)} caracteres"
        })

        # Test 2: Validar CDC generado
        validation_result = validate_cdc(cdc_test)
        tests.append({
            'test': 'validate_cdc',
            'passed': validation_result.is_valid,
            'details': f"Validación: {validation_result.is_valid}"
        })

        # Test 3: Extraer componentes
        components = extract_cdc_components(cdc_test)
        tests.append({
            'test': 'extract_cdc_components',
            'passed': components.validate_lengths(),
            'details': f"Componentes extraídos correctamente"
        })

        # Test 4: Formatear CDC
        formatted = format_cdc_display(cdc_test)
        tests.append({
            'test': 'format_cdc_display',
            'passed': len(formatted) > len(cdc_test),  # Debe tener guiones
            'details': f"Formato: {formatted[:50]}..."
        })

        # Test 5: Información de CDC
        info = get_cdc_info(cdc_test)
        tests.append({
            'test': 'get_cdc_info',
            'passed': info['valid'] and 'tipo_documento_descripcion' in info,
            'details': f"Info extraída: {info.get('tipo_documento_descripcion', 'N/A')}"
        })

    except Exception as e:
        tests.append({
            'test': 'general_error',
            'passed': False,
            'details': f"Error en pruebas: {str(e)}"
        })

    # Compilar resultados
    all_passed = all(test['passed'] for test in tests)
    passed_count = sum(1 for test in tests if test['passed'])

    return {
        'all_passed': all_passed,
        'passed_count': passed_count,
        'total_tests': len(tests),
        'success_rate': (passed_count / len(tests)) * 100 if tests else 0,
        'tests': tests,
        'module_status': 'OK' if all_passed else 'ISSUES_FOUND'
    }


def get_usage_examples() -> dict:
    """
    Obtiene ejemplos de uso del módulo CDC.

    Returns:
        dict: Ejemplos organizados por categoría
    """
    return {
        'basic_generation': {
            'description': 'Generar un CDC básico',
            'code': '''
from app.utils.cdc import generate_cdc, CdcGenerationRequest, TipoDocumento
from datetime import datetime

request = CdcGenerationRequest(
    ruc_emisor="80000001",
    tipo_documento=TipoDocumento.FACTURA_ELECTRONICA.value,
    establecimiento="001",
    punto_expedicion="001",
    numero_documento=123,
    fecha_emision=datetime.now()
)

cdc = generate_cdc(request)
print(f"CDC generado: {cdc}")
            '''
        },
        'validation': {
            'description': 'Validar un CDC existente',
            'code': '''
from app.utils.cdc import validate_cdc, get_cdc_info

cdc = "01234567890123456789012345678901234567890123"
result = validate_cdc(cdc)

if result.is_valid:
    info = get_cdc_info(cdc)
    print(f"CDC válido: {info['tipo_documento_descripcion']}")
else:
    print(f"CDC inválido: {result.error_message}")
            '''
        },
        'component_extraction': {
            'description': 'Extraer componentes de un CDC',
            'code': '''
from app.utils.cdc import extract_cdc_components, format_cdc_display

cdc = "01234567890123456789012345678901234567890123"
components = extract_cdc_components(cdc)

print(f"RUC Emisor: {components.ruc_emisor}")
print(f"Tipo Documento: {components.get_tipo_documento_descripcion()}")
print(f"Número Documento: {components.get_numero_documento_int()}")
print(f"CDC Formateado: {format_cdc_display(cdc)}")
            '''
        },
        'batch_processing': {
            'description': 'Procesar lotes de CDCs',
            'code': '''
from app.utils.cdc import validate_cdc_batch, create_cdc_report

cdcs = [
    "01234567890123456789012345678901234567890123",
    "98765432109876543210987654321098765432109876"
]

# Validar lote
results = validate_cdc_batch(cdcs)
valid_count = sum(1 for r in results.values() if r.is_valid)

# Crear reporte
report = create_cdc_report(cdcs)
print(f"Validación: {report['summary']['validation_rate']:.1f}%")
            '''
        }
    }


# ===================================================================
# EXPORTS PÚBLICOS
# ===================================================================

__all__ = [
    # Enumeraciones
    'TipoDocumento',
    'TipoEmision',

    # Clases de datos
    'CdcComponents',
    'CdcGenerationRequest',
    'CdcValidationResult',
    'CdcErrorCode',

    # Funciones principales
    'generate_cdc',
    'validate_cdc',
    'is_valid_cdc',
    'extract_cdc_components',

    # Funciones auxiliares de generación
    'calculate_cdc_dv',
    'generate_security_code',

    # Funciones de componentes
    'extract_cdc_parts',
    'get_component_info',
    'reconstruct_cdc',

    # Funciones de validación por lotes
    'validate_cdc_batch',
    'get_cdc_statistics',

    # Funciones de utilidades
    'format_cdc_display',
    'get_cdc_info',
    'format_fecha_display',

    # Funciones de reportes
    'create_cdc_report',
    'format_cdc_table',
    'compare_cdcs',

    # Funciones de testing
    'generate_test_cdc',
    'generate_test_cdc_batch',
    'validate_and_format_cdc_list',

    # Funciones de análisis
    'debug_cdc_structure',
    'analyze_cdc_patterns',

    # Constantes
    'CDC_LENGTH',
    'CDC_COMPONENT_LENGTHS',

    # Utilidades del módulo
    'get_module_status',
    'validate_module_dependencies',
    'run_self_test',
    'get_usage_examples',

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
        f"Módulo CDC: {_module_status}",
        category=ImportWarning
    )
