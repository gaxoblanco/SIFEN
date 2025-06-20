"""
Constantes y patrones para validación SIFEN v150

Este módulo centraliza todas las constantes necesarias para la validación
de documentos electrónicos según las especificaciones SIFEN v150 de Paraguay.

Responsabilidades:
- Definir configuración básica SIFEN
- Centralizar patrones de validación regex
- Especificar elementos y atributos obligatorios
- Mapear códigos de documentos válidos
- Definir mensajes de error amigables

Uso:
    from .constants import SIFEN_NAMESPACE, VALIDATION_PATTERNS
    
Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
"""

import re
from pathlib import Path
from typing import Dict, List, Pattern


# =====================================
# CONFIGURACIÓN BÁSICA SIFEN v150
# =====================================

# Namespace oficial para documentos SIFEN v150
SIFEN_NAMESPACE: str = "http://ekuatia.set.gov.py/sifen/xsd"

# Versión del formato SIFEN utilizada
SIFEN_VERSION: str = "150"

# Schema location completa para validación XSD
SCHEMA_LOCATION: str = f"{SIFEN_NAMESPACE} DE_v150.xsd"

# Ruta por defecto al archivo XSD principal
# Calculada desde la ubicación actual del módulo
# Estructura esperada: schemas/v150/DE_v150.xsd
DEFAULT_XSD_PATH: Path = Path(
    __file__).parent.parent.parent.parent / "DE_v150.xsd"

# URI completa del namespace con prefijo
NAMESPACE_URI: str = f"{{{SIFEN_NAMESPACE}}}"


# =====================================
# PATRONES REGEX DE VALIDACIÓN
# =====================================

# Patrones de validación compilados para mejor performance
# Cada patrón está optimizado para las especificaciones SIFEN v150

VALIDATION_PATTERNS: Dict[str, Pattern[str]] = {
    # CDC (Código de Control): 44 dígitos numéricos exactos
    # Ejemplo: 01000000000000000000000000000000000000000001
    'cdc': re.compile(r'^\d{44}$'),

    # RUC (Registro Único del Contribuyente): 8 dígitos exactos
    # Ejemplo: 12345678
    'ruc': re.compile(r'^\d{8,9}$'),

    # DV (Dígito Verificador): 1 dígito exacto
    # Ejemplo: 9
    'dv': re.compile(r'^\d{1}$'),

    # Fecha ISO 8601: YYYY-MM-DDTHH:MM:SS
    # Ejemplo: 2024-12-15T14:30:45
    'fecha_iso': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'),

    # Fecha ISO extendida con milisegundos (opcional)
    # Ejemplo: 2024-12-15T14:30:45.123
    'fecha_iso_extended': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?$'),

    # Código de tipo de documento: 01, 04, 05, 06, 07
    # 01=Factura, 04=Autofactura, 05=NotaCrédito, 06=NotaDébito, 07=NotaRemisión
    'codigo_documento': re.compile(r'^0[1-7]$'),

    # Establecimiento: 3 dígitos exactos
    # Ejemplo: 001
    'establecimiento': re.compile(r'^\d{3}$'),

    # Punto de expedición: 3 dígitos exactos
    # Ejemplo: 001
    'punto_expedicion': re.compile(r'^\d{3}$'),

    # Número de documento: 7 dígitos exactos
    # Ejemplo: 0000001
    'numero_documento': re.compile(r'^\d{7}$'),

    # Código de seguridad: 9 dígitos exactos
    # Ejemplo: 123456789
    'codigo_seguridad': re.compile(r'^\d{9}$'),

    # Timbrado: 8 dígitos exactos
    # Ejemplo: 12345678
    'timbrado': re.compile(r'^\d{8}$'),

    # Código de moneda ISO: 3 caracteres alfabéticos
    # Ejemplo: PYG, USD, EUR
    'codigo_moneda': re.compile(r'^[A-Z]{3}$'),

    # Código de condición de operación: 1 dígito (1-2)
    # 1=Contado, 2=Crédito
    'condicion_operacion': re.compile(r'^[12]$'),

    # Código de presencia del comprador: 1 dígito (1-9)
    # 1=Operación presencial, 2=Operación electrónica, etc.
    'presencia_comprador': re.compile(r'^[1-9]$')
}


# =====================================
# ELEMENTOS OBLIGATORIOS XML
# =====================================

# Elementos mínimos requeridos en cualquier documento SIFEN v150
# Estos elementos deben estar presentes para que el XML sea válido
REQUIRED_ELEMENTS: List[str] = [
    'rDE',           # Elemento raíz del documento
    'DE',            # Documento electrónico principal
    'dVerFor',       # Versión del formato (debe ser "150")
    'dCodSeg',       # Código de seguridad del documento
    'gDatGralOpe',   # Datos generales de la operación
    'gOpDE',         # Datos específicos de la operación
    'gEmis',         # Datos del emisor
    'gDatRec',       # Datos del receptor
    'gCamItem',      # Campos de ítems (al menos uno)
    'gTotSub'        # Totales y subtotales
]

# Elementos obligatorios para datos del emisor
REQUIRED_EMISOR_ELEMENTS: List[str] = [
    'dRUCEmi',       # RUC del emisor
    'dDVEmi',        # Dígito verificador del emisor
    'dNomEmi'        # Nombre del emisor
]

# Elementos obligatorios para datos de la operación
REQUIRED_OPERACION_ELEMENTS: List[str] = [
    'iTipDE',        # Tipo de documento electrónico
    'dNumTim',       # Número de timbrado
    'dEst',          # Establecimiento
    'dPunExp',       # Punto de expedición
    'dNumDoc',       # Número de documento
    'dFeEmiDE'       # Fecha de emisión del documento electrónico
]

# Atributos obligatorios del elemento raíz rDE
REQUIRED_ATTRIBUTES: List[str] = [
    'version'        # Versión del esquema (debe ser "150")
]

# Atributos obligatorios del elemento DE
REQUIRED_DE_ATTRIBUTES: List[str] = [
    'Id'            # CDC del documento (44 dígitos)
]


# =====================================
# CÓDIGOS DE DOCUMENTO VÁLIDOS
# =====================================

# Tipos de documentos electrónicos válidos en SIFEN v150
# Cada código corresponde a un tipo específico de documento
VALID_DOCUMENT_TYPES: Dict[str, str] = {
    '01': 'Factura Electrónica',
    '04': 'Autofactura Electrónica',
    '05': 'Nota de Crédito Electrónica',
    '06': 'Nota de Débito Electrónica',
    '07': 'Nota de Remisión Electrónica'
}

# Códigos de documento que requieren datos del receptor
DOCUMENT_TYPES_WITH_RECEIVER: List[str] = ['01', '05', '06', '07']

# Códigos de documento que NO requieren datos del receptor
DOCUMENT_TYPES_WITHOUT_RECEIVER: List[str] = ['04']

# Códigos de condición de operación válidos
VALID_OPERATION_CONDITIONS: Dict[str, str] = {
    '1': 'Contado',
    '2': 'Crédito'
}

# Códigos de presencia del comprador válidos
VALID_BUYER_PRESENCE: Dict[str, str] = {
    '1': 'Operación presencial',
    '2': 'Operación electrónica',
    '3': 'Operación telemarketing',
    '4': 'Venta a domicilio',
    '5': 'Operación bancaria',
    '6': 'Operación cíclica',
    '7': 'Operación con entrega a domicilio',
    '8': 'Operación Pago Electrónico',
    '9': 'Otros'
}


# =====================================
# MAPEO DE ERRORES XSD
# =====================================

# Mapeo de errores comunes de lxml XSD a mensajes amigables
# Estos errores son los más frecuentes en validación de documentos SIFEN
XSD_ERROR_MAPPINGS: Dict[str, str] = {
    # Errores de patrón (regex)
    'cvc-pattern-valid': 'El formato del campo no cumple con el patrón requerido',

    # Errores de longitud
    'cvc-minLength-valid': 'El campo no alcanza la longitud mínima requerida',
    'cvc-maxLength-valid': 'El campo excede la longitud máxima permitida',
    'cvc-length-valid': 'El campo no tiene la longitud exacta requerida',

    # Errores de tipo de dato
    'cvc-type.3.1.3': 'El valor no corresponde al tipo de dato esperado',
    'cvc-datatype-valid.1.2.1': 'Valor de tipo de dato inválido',

    # Errores de enumeración
    'cvc-enumeration-valid': 'El valor no está dentro de los valores permitidos',

    # Errores de elementos
    'cvc-complex-type.2.4.a': 'Elemento obligatorio faltante',
    'cvc-complex-type.2.4.b': 'Elemento no permitido en este contexto',
    'cvc-complex-type.2.4.c': 'Elemento duplicado no permitido',
    'cvc-complex-type.2.4.d': 'Contenido del elemento no válido',

    # Errores de atributos
    'cvc-complex-type.3.2.2': 'Atributo no permitido',
    'cvc-complex-type.4': 'Atributo obligatorio faltante',

    # Errores de cardinalidad
    'cvc-complex-type.2.1': 'Elemento no puede tener contenido de texto',
    'cvc-complex-type.2.2': 'Elemento no puede tener contenido mixto',
    'cvc-complex-type.2.3': 'Elemento debe tener contenido',

    # Errores de restricciones
    'cvc-minInclusive-valid': 'Valor menor al mínimo permitido',
    'cvc-maxInclusive-valid': 'Valor mayor al máximo permitido',
    'cvc-minExclusive-valid': 'Valor debe ser mayor al mínimo',
    'cvc-maxExclusive-valid': 'Valor debe ser menor al máximo',
    'cvc-totalDigits-valid': 'Número total de dígitos excedido',
    'cvc-fractionDigits-valid': 'Número de decimales excedido',

    # Errores de identidad
    'cvc-identity-constraint.3': 'Valor duplicado en campo único',
    'cvc-identity-constraint.4.1': 'Clave no encontrada',
    'cvc-identity-constraint.4.2.2': 'Referencia de clave inválida'
}

# Categorías de errores para agrupación y análisis
ERROR_CATEGORIES: Dict[str, List[str]] = {
    'format_errors': [
        'cvc-pattern-valid',
        'cvc-datatype-valid.1.2.1',
        'cvc-type.3.1.3'
    ],
    'structure_errors': [
        'cvc-complex-type.2.4.a',
        'cvc-complex-type.2.4.b',
        'cvc-complex-type.4'
    ],
    'content_errors': [
        'cvc-enumeration-valid',
        'cvc-minLength-valid',
        'cvc-maxLength-valid',
        'cvc-length-valid'
    ],
    'constraint_errors': [
        'cvc-minInclusive-valid',
        'cvc-maxInclusive-valid',
        'cvc-totalDigits-valid',
        'cvc-fractionDigits-valid'
    ]
}


# =====================================
# CONSTANTES DE CONFIGURACIÓN
# =====================================

# Encoding por defecto para archivos XML
DEFAULT_XML_ENCODING: str = 'utf-8'

# Namespace para XML Schema Instance
XSI_NAMESPACE: str = 'http://www.w3.org/2001/XMLSchema-instance'

# Prefijos de namespace comunes
NAMESPACE_PREFIXES: Dict[str, str] = {
    'xsi': XSI_NAMESPACE,
    'sifen': SIFEN_NAMESPACE
}

# Configuración del parser XML
XML_PARSER_CONFIG: Dict[str, bool] = {
    'remove_blank_text': True,
    'remove_comments': True,
    'strip_cdata': False,
    'recover': False  # Modo estricto para validación
}

# Límites de performance para validación
VALIDATION_LIMITS: Dict[str, int] = {
    'max_file_size_mb': 10,      # Tamaño máximo de archivo XML en MB
    'max_validation_time_ms': 5000,  # Tiempo máximo de validación en ms
    'max_error_count': 100       # Número máximo de errores a reportar
}


# =====================================
# VALIDACIÓN DE CONSTANTES
# =====================================

def _validate_constants() -> None:
    """
    Valida que las constantes estén correctamente definidas
    Esta función se ejecuta al importar el módulo
    """
    # Verificar que todos los patrones regex compilen correctamente
    for pattern_name, pattern in VALIDATION_PATTERNS.items():
        try:
            # Test de compilación (ya están compilados, pero verificamos)
            pattern.pattern
        except Exception as e:
            raise ValueError(f"Patrón regex inválido '{pattern_name}': {e}")

    # Verificar que la ruta del XSD sea válida (Path object)
    if not isinstance(DEFAULT_XSD_PATH, Path):
        raise ValueError("DEFAULT_XSD_PATH debe ser un objeto Path")

    # Verificar que los códigos de documento sean válidos
    for code in VALID_DOCUMENT_TYPES.keys():
        if not VALIDATION_PATTERNS['codigo_documento'].match(code):
            raise ValueError(f"Código de documento inválido: {code}")


# Ejecutar validación al importar el módulo
_validate_constants()


# =====================================
# UTILIDADES DE CONSTANTES
# =====================================

def get_pattern(pattern_name: str) -> Pattern[str]:
    """
    Obtiene un patrón de validación por nombre

    Args:
        pattern_name: Nombre del patrón a obtener

    Returns:
        Pattern compilado

    Raises:
        KeyError: Si el patrón no existe
    """
    if pattern_name not in VALIDATION_PATTERNS:
        available = ', '.join(VALIDATION_PATTERNS.keys())
        raise KeyError(
            f"Patrón '{pattern_name}' no encontrado. Disponibles: {available}")

    return VALIDATION_PATTERNS[pattern_name]


def get_document_type_name(code: str) -> str:
    """
    Obtiene el nombre del tipo de documento por código

    Args:
        code: Código del tipo de documento

    Returns:
        Nombre del tipo de documento

    Raises:
        KeyError: Si el código no es válido
    """
    if code not in VALID_DOCUMENT_TYPES:
        available = ', '.join(VALID_DOCUMENT_TYPES.keys())
        raise KeyError(
            f"Código de documento '{code}' no válido. Válidos: {available}")

    return VALID_DOCUMENT_TYPES[code]


def is_document_type_valid(code: str) -> bool:
    """
    Verifica si un código de tipo de documento es válido

    Args:
        code: Código a verificar

    Returns:
        True si el código es válido
    """
    return code in VALID_DOCUMENT_TYPES


def get_error_message(error_code: str) -> str:
    """
    Obtiene un mensaje amigable para un código de error XSD

    Args:
        error_code: Código de error de lxml

    Returns:
        Mensaje amigable o el código original si no se encuentra
    """
    return XSD_ERROR_MAPPINGS.get(error_code, f"Error de validación: {error_code}")


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    # Configuración básica
    'SIFEN_NAMESPACE',
    'SIFEN_VERSION',
    'SCHEMA_LOCATION',
    'DEFAULT_XSD_PATH',
    'NAMESPACE_URI',

    # Patrones de validación
    'VALIDATION_PATTERNS',

    # Elementos y atributos obligatorios
    'REQUIRED_ELEMENTS',
    'REQUIRED_EMISOR_ELEMENTS',
    'REQUIRED_OPERACION_ELEMENTS',
    'REQUIRED_ATTRIBUTES',
    'REQUIRED_DE_ATTRIBUTES',

    # Códigos válidos
    'VALID_DOCUMENT_TYPES',
    'DOCUMENT_TYPES_WITH_RECEIVER',
    'DOCUMENT_TYPES_WITHOUT_RECEIVER',
    'VALID_OPERATION_CONDITIONS',
    'VALID_BUYER_PRESENCE',

    # Mapeo de errores
    'XSD_ERROR_MAPPINGS',
    'ERROR_CATEGORIES',

    # Configuración
    'DEFAULT_XML_ENCODING',
    'XSI_NAMESPACE',
    'NAMESPACE_PREFIXES',
    'XML_PARSER_CONFIG',
    'VALIDATION_LIMITS',

    # Utilidades
    'get_pattern',
    'get_document_type_name',
    'is_document_type_valid',
    'get_error_message'
]
