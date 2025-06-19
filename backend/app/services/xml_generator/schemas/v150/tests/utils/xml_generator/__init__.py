"""
XML Generator API - Facade principal para testing de schemas v150

Este módulo proporciona una API unificada que combina todos los componentes
modulares del generador XML para testing, incluyendo:

- Validadores SIFEN especializados
- APIs de datos de muestra paraguayos  
- Generadores de elementos XML básicos
- Utilidades de validación y testing

Uso:
    # Validación XML completa
    from ..utils.xml_generator import validate_xml, SifenValidator
    
    # Generación de datos de muestra
    from ..utils.xml_generator import SampleDataAPI
    
    # Validaciones específicas
    from ..utils.xml_generator import quick_validate_ruc, quick_validate_cdc

Arquitectura modular:
- validators/: Validadores especializados SIFEN
- sample_data/: APIs para datos de muestra paraguayos
- base_generator.py: Funcionalidad común de generación

Autor: Sistema SIFEN Paraguay
Versión: 1.0.0
Fecha: 2025-06-18
"""

from typing import Tuple, List, Optional, Dict, Any

# =====================================
# IMPORTS DE VALIDADORES MODULARES
# =====================================

# Importar desde validators/
from .validators import (
    # Clase principal
    SifenValidator,

    # Funciones de validación completa
    validate_xml,
    validate_xml_structure,
    validate_sifen_format,
    quick_validate,

    # Validaciones específicas de campos
    quick_validate_ruc,
    quick_validate_cdc,
    quick_validate_date,

    # Funciones de análisis detallado
    validate_with_detailed_report,
    get_xsd_errors_only,
    get_format_errors_only,

    # Clases individuales de validadores
    CoreXSDValidator,
    StructureValidator,
    FormatValidator,
    ErrorHandler,
    ValidationError,
)

# =====================================
# IMPORTS DE DATOS DE MUESTRA
# =====================================

# Importar desde sample_data/
from .sample_data import (
    # API principal
    SampleData,

    # Datos por categoría
    EMPRESAS_TIPICAS,
    CLIENTES_FRECUENTES,
    PRODUCTOS_POR_SECTOR,
    CIUDADES_PRINCIPALES,
    DIRECCIONES_TIPICAS,
    RUC_TESTING,
    TELEFONOS_VALIDOS,
    MONEDAS_VALIDAS,
    ESCENARIOS_TESTING,

    # Funciones auxiliares
    get_empresa_by_sector,
    get_cliente_by_tipo,
    get_productos_by_sector,
    get_producto_by_codigo,
    get_escenario,

    # Funciones de conveniencia
    quick_emisor,
    quick_receptor,
    quick_items,
    quick_scenario,
)

# =====================================
# IMPORTS DEL GENERADOR BASE
# =====================================

# Importar desde base_generator.py
from .base_generator import (
    GeneratorConfig,
)

# =====================================
# FUNCIONES DE CONVENIENCIA
# =====================================


def create_sample_data() -> SampleData:
    """
    Crea una instancia de SampleData.

    Returns:
        SampleData: Instancia configurada con datos paraguayos
    """
    return SampleData()


def create_sifen_validator(xsd_path: Optional[str] = None) -> SifenValidator:
    """
    Crea una instancia configurada de SifenValidator.

    Args:
        xsd_path: Ruta al schema XSD (opcional, usa default si no se especifica)

    Returns:
        SifenValidator: Instancia configurada
    """
    return SifenValidator(xsd_path=xsd_path)  # <-- Parámetro correcto es xsd_path


def quick_validation_suite(xml_content: str) -> Dict[str, Any]:
    """
    Ejecuta una suite completa de validaciones rápidas.

    Args:
        xml_content: Contenido XML a validar

    Returns:
        Dict: Resultados organizados de todas las validaciones
    """
    results = {
        "overall_valid": False,
        "structure_valid": False,
        "xsd_valid": False,
        "format_valid": False,
        "errors": [],
        "warnings": []
    }

    try:
        # Validación de estructura
        struct_valid, struct_errors = validate_xml_structure(xml_content)
        results["structure_valid"] = struct_valid
        if not struct_valid:
            results["errors"].extend(
                [f"ESTRUCTURA: {err}" for err in struct_errors])

        # Validación XSD
        xsd_valid, xsd_errors = validate_xml(xml_content)
        results["xsd_valid"] = xsd_valid
        if not xsd_valid:
            results["errors"].extend([f"XSD: {err}" for err in xsd_errors])

        # Validación de formatos
        format_valid, format_errors = validate_sifen_format(xml_content)
        results["format_valid"] = format_valid
        if not format_valid:
            results["errors"].extend(
                [f"FORMATO: {err}" for err in format_errors])

        # Resultado general
        results["overall_valid"] = struct_valid and xsd_valid and format_valid

    except Exception as e:
        results["errors"].append(f"ERROR_GENERAL: {str(e)}")

    return results


def generate_test_xml_element(element_name: str, value: str,
                              namespace: str = "http://ekuatia.set.gov.py/sifen/xsd") -> str:
    """
    Genera un elemento XML simple para testing.

    Args:
        element_name: Nombre del elemento XML
        value: Valor del elemento
        namespace: Namespace XML (default SIFEN)

    Returns:
        str: Elemento XML formateado
    """
    return f'<{element_name} xmlns="{namespace}">{value}</{element_name}>'


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    # Validadores principales
    "SifenValidator",
    "validate_xml",
    "validate_xml_structure",
    "validate_sifen_format",
    "quick_validate",

    # Validaciones específicas
    "quick_validate_ruc",
    "quick_validate_cdc",
    "quick_validate_date",

    # Análisis detallado
    "validate_with_detailed_report",
    "get_xsd_errors_only",
    "get_format_errors_only",

    # Clases de validadores
    "CoreXSDValidator",
    "StructureValidator",
    "FormatValidator",
    "ErrorHandler",
    "ValidationError",

    # API de datos de muestra
    "SampleData",
    "EMPRESAS_TIPICAS",
    "CLIENTES_FRECUENTES",
    "PRODUCTOS_POR_SECTOR",
    "CIUDADES_PRINCIPALES",
    "DIRECCIONES_TIPICAS",
    "RUC_TESTING",
    "TELEFONOS_VALIDOS",
    "MONEDAS_VALIDAS",
    "ESCENARIOS_TESTING",

    # Funciones auxiliares
    "get_empresa_by_sector",
    "get_cliente_by_tipo",
    "get_productos_by_sector",
    "get_producto_by_codigo",
    "get_escenario",
    "quick_emisor",
    "quick_receptor",
    "quick_items",
    "quick_scenario",

    # Generador base (comentado - no exportado)
    # "BaseXMLGenerator",
    # "GeneratorConfig",

    # Funciones de conveniencia
    "create_sample_data",
    "create_sifen_validator",
    "quick_validation_suite",
    "generate_test_xml_element",
]


# =====================================
# METADATOS DEL MÓDULO
# =====================================

__version__ = "1.0.0"
__author__ = "Sistema SIFEN Paraguay"
__description__ = "API unificada para testing de schemas XML SIFEN v150"
