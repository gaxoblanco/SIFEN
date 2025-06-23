"""
Módulo: SIFEN Test Constants

Propósito:
    Definición centralizada de constantes para testing de schemas SIFEN v150.
    Incluye namespaces, versiones, patrones de validación, tipos de documentos,
    elementos requeridos y configuraciones específicas del sistema SIFEN.

Funcionalidades principales:
    - Constantes de namespaces y versiones SIFEN
    - Definición de tipos de documentos electrónicos
    - Patrones de validación para campos específicos
    - Elementos XML requeridos por tipo de documento
    - Códigos de respuesta y error SIFEN
    - Configuraciones de testing y validación

Uso:
    from .constants import SIFEN_NAMESPACE_URI, SIFEN_DOCUMENT_TYPES
    
    # Usar namespace en validaciones
    if xml_tree.nsmap.get(None) == SIFEN_NAMESPACE_URI:
        # Procesar documento SIFEN
    
    # Validar tipo de documento
    if doc_type in SIFEN_DOCUMENT_TYPES:
        doc_info = SIFEN_DOCUMENT_TYPES[doc_type]

Autor: Sistema SIFEN
Versión: 1.0.0
Fecha: 2025-06-17
"""

from typing import Dict, Union
from decimal import Decimal
from typing import Final, TYPE_CHECKING
from typing import Dict, List, Any, Pattern, Optional
import re
from enum import Enum
from dataclasses import dataclass


# ================================
# CONFIGURACIÓN BÁSICA SIFEN
# ================================

# Namespace oficial SIFEN v150
SIFEN_NAMESPACE_URI = "http://ekuatia.set.gov.py/sifen/xsd"

# URI de XMLSchema Instance
XSI_NAMESPACE_URI = "http://www.w3.org/2001/XMLSchema-instance"

# Versión actual del schema SIFEN
SIFEN_SCHEMA_VERSION = "150"

# Versión del formato (dVerFor)
SIFEN_FORMAT_VERSION = "150"

# Encoding obligatorio
SIFEN_REQUIRED_ENCODING = "UTF-8"

# Schema Location
SIFEN_SCHEMA_LOCATION = f"{SIFEN_NAMESPACE_URI} DE_v150.xsd"


# ================================
# TIPOS DE DOCUMENTOS ELECTRÓNICOS
# ================================

@dataclass
class DocumentTypeInfo:
    """Información de un tipo de documento SIFEN"""
    code: str
    name: str
    description: str
    required_elements: List[str]
    prohibited_elements: List[str]
    specific_validations: Dict[str, Any]


# Definición completa de tipos de documentos SIFEN
SIFEN_DOCUMENT_TYPES: Dict[str, DocumentTypeInfo] = {
    "01": DocumentTypeInfo(
        code="01",
        name="Factura Electrónica",
        description="FE - Factura estándar entre contribuyentes",
        required_elements=[
            "//gDatGral/iTiDE[text()='01']",
            "//gEmis",  # Datos del emisor
            "//gDatRec",  # Datos del receptor
            "//gDtipDE/gCamFE",  # Campos específicos de FE
            "//gTotSub",  # Totales
        ],
        prohibited_elements=[
            "//gCamAE",   # Campos de autofactura
            "//gCamNCE",  # Campos de nota crédito
            "//gCamNDE",  # Campos de nota débito
            "//gCamNRE",  # Campos de nota remisión
        ],
        specific_validations={
            "requires_receiver": True,
            "requires_items": True,
            "requires_totals": True,
            "requires_payment_condition": True,
        }
    ),
    "04": DocumentTypeInfo(
        code="04",
        name="Autofactura Electrónica",
        description="AFE - Factura emitida por el receptor de bienes/servicios",
        required_elements=[
            "//gDatGral/iTiDE[text()='04']",
            "//gEmis",  # Datos del emisor
            "//gDatRec",  # Datos del receptor
            "//gDtipDE/gCamAE",  # Campos específicos de AFE
            "//gTotSub",  # Totales
        ],
        prohibited_elements=[
            "//gCamFE",   # Campos de factura
            "//gCamNCE",  # Campos de nota crédito
            "//gCamNDE",  # Campos de nota débito
            "//gCamNRE",  # Campos de nota remisión
        ],
        specific_validations={
            "requires_receiver": True,
            "requires_items": True,
            "requires_totals": True,
            "autofactura_specific": True,
        }
    ),
    "05": DocumentTypeInfo(
        code="05",
        name="Nota de Crédito Electrónica",
        description="NCE - Documento que disminuye el valor de una factura",
        required_elements=[
            "//gDatGral/iTiDE[text()='05']",
            "//gEmis",  # Datos del emisor
            "//gDatRec",  # Datos del receptor
            "//gDtipDE/gCamNCE",  # Campos específicos de NCE
            "//gTotSub",  # Totales
        ],
        prohibited_elements=[
            "//gCamFE",   # Campos de factura
            "//gCamAE",   # Campos de autofactura
            "//gCamNDE",  # Campos de nota débito
            "//gCamNRE",  # Campos de nota remisión
        ],
        specific_validations={
            "requires_receiver": True,
            "requires_items": True,
            "requires_totals": True,
            "requires_associated_document": True,
        }
    ),
    "06": DocumentTypeInfo(
        code="06",
        name="Nota de Débito Electrónica",
        description="NDE - Documento que aumenta el valor de una factura",
        required_elements=[
            "//gDatGral/iTiDE[text()='06']",
            "//gEmis",  # Datos del emisor
            "//gDatRec",  # Datos del receptor
            "//gDtipDE/gCamNDE",  # Campos específicos de NDE
            "//gTotSub",  # Totales
        ],
        prohibited_elements=[
            "//gCamFE",   # Campos de factura
            "//gCamAE",   # Campos de autofactura
            "//gCamNCE",  # Campos de nota crédito
            "//gCamNRE",  # Campos de nota remisión
        ],
        specific_validations={
            "requires_receiver": True,
            "requires_items": True,
            "requires_totals": True,
            "requires_associated_document": True,
        }
    ),
    "07": DocumentTypeInfo(
        code="07",
        name="Nota de Remisión Electrónica",
        description="NRE - Documento de traslado de mercaderías",
        required_elements=[
            "//gDatGral/iTiDE[text()='07']",
            "//gEmis",  # Datos del emisor
            "//gDatRec",  # Datos del receptor
            "//gDtipDE/gCamNRE",  # Campos específicos de NRE
            "//gTransp",  # Datos de transporte (obligatorio)
        ],
        prohibited_elements=[
            "//gCamFE",   # Campos de factura
            "//gCamAE",   # Campos de autofactura
            "//gCamNCE",  # Campos de nota crédito
            "//gCamNDE",  # Campos de nota débito
        ],
        specific_validations={
            "requires_receiver": True,
            "requires_items": True,
            "requires_transport": True,
            "no_totals_required": True,
        }
    ),
}


# ================================
# ELEMENTOS XML REQUERIDOS
# ================================

# Elementos básicos requeridos en todo documento SIFEN
REQUIRED_SIFEN_ELEMENTS = [
    "//dVerFor",          # Versión del formato
    "//rDE",              # Elemento raíz
    "//DE[@Id]",          # Documento electrónico con ID
    "//gTimb",            # Datos de timbrado
    "//iTiDE",            # Tipo de documento
    "//dNumDoc",          # Número de documento
    "//dFeEmiDE",         # Fecha de emisión
    "//gEmis",            # Datos del emisor
    "//dRUCEmi",          # RUC del emisor
    "//dNomEmi",          # Nombre del emisor
    "//gActEco",          # Actividad económica
    "//cActEco",          # Código de actividad económica
    "//dDesActEco",       # Descripción actividad económica
]

# Elementos requeridos para el timbrado
REQUIRED_STAMPING_ELEMENTS = [
    "//iTimbr",           # Número de timbrado
    "//dEstTimbr",        # Establecimiento
    "//dPunExp",          # Punto de expedición
    "//dNumTimbr",        # Número de timbrado
    "//dFeIniT",          # Fecha inicio timbrado
]

# Elementos requeridos para items/productos
REQUIRED_ITEM_ELEMENTS = [
    "//dCodInt",          # Código interno
    "//dDesProSer",       # Descripción producto/servicio
    "//cUniMed",          # Unidad de medida
    "//dCantProSer",      # Cantidad
    "//dPUniProSer",      # Precio unitario
]


# ================================
# PATRONES DE VALIDACIÓN DE CAMPOS
# ================================

# Patrones regex para campos específicos SIFEN
FIELD_REGEX_PATTERNS = {
    # Identificadores
    "dRUCEmi": re.compile(r"^\d{1,8}-\d{1}$|^\d{1,8}$"),  # RUC con o sin DV
    "dRUCRec": re.compile(r"^\d{1,8}-\d{1}$|^\d{1,8}$"),  # RUC receptor
    "dCodSeg": re.compile(r"^[A-Za-z0-9]{9}$"),           # Código de seguridad
    # ID del documento (CDC)
    "Id": re.compile(r"^[A-Za-z0-9]{44}$"),

    # Números de documento y timbrado
    # Formato XXX-XXX-XXXXXXX
    "dNumDoc": re.compile(r"^\d{3}-\d{3}-\d{7}$"),
    "iTimbr": re.compile(r"^\d{8}$"),                      # 8 dígitos
    "dEstTimbr": re.compile(r"^\d{3}$"),                   # 3 dígitos
    "dPunExp": re.compile(r"^\d{3}$"),                     # 3 dígitos

    # Fechas (formato YYYY-MM-DD)
    "dFeEmiDE": re.compile(r"^\d{4}-\d{2}-\d{2}$"),       # Fecha emisión
    # Fecha inicio timbrado
    "dFeIniT": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "dFeFinT": re.compile(r"^\d{4}-\d{2}-\d{2}$"),        # Fecha fin timbrado

    # Horas (formato HH:MM:SS)
    "dHorEmi": re.compile(r"^\d{2}:\d{2}:\d{2}$"),        # Hora emisión

    # Montos (hasta 15 dígitos con 4 decimales)
    "dPUniProSer": re.compile(r"^\d{1,11}(\.\d{1,4})?$"),  # Precio unitario
    "dTotBruOpeItem": re.compile(r"^\d{1,11}(\.\d{1,4})?$"),  # Total bruto
    "dTotOpe": re.compile(r"^\d{1,11}(\.\d{1,4})?$"),     # Total operación

    # Cantidades (hasta 11 dígitos con 4 decimales)
    "dCantProSer": re.compile(r"^\d{1,7}(\.\d{1,4})?$"),  # Cantidad

    # Códigos específicos
    # Unidad de medida (2 dígitos)
    "cUniMed": re.compile(r"^\d{2}$"),
    # Actividad económica (5 dígitos)
    "cActEco": re.compile(r"^\d{5}$"),
    # Código país (3 letras)
    "cPaiEmi": re.compile(r"^[A-Z]{3}$"),
    "iTiDE": re.compile(r"^(01|04|05|06|07)$"),            # Tipo de documento
    # Tipo transacción venta
    "iTiTranVenta": re.compile(r"^[1-9]$"),
    # Naturaleza receptor
    "iNatRec": re.compile(r"^[1-2]$"),
    "iTiOpe": re.compile(r"^[1-2]$"),                      # Tipo operación
    "cMoneOpe": re.compile(r"^[A-Z]{3}$"),                 # Moneda operación

    # Textos con longitudes específicas
    "dNomEmi": re.compile(r"^.{4,60}$"),                   # Nombre emisor
    "dNomRec": re.compile(r"^.{4,60}$"),                   # Nombre receptor
    # Descripción producto
    "dDesProSer": re.compile(r"^.{1,120}$"),
    # Descripción actividad
    "dDesActEco": re.compile(r"^.{1,60}$"),
    "dDirEmi": re.compile(r"^.{1,80}$"),                   # Dirección emisor
    "dDirRec": re.compile(r"^.{1,80}$"),                   # Dirección receptor

    # Números de teléfono
    "dTelEmi": re.compile(r"^\d{6,15}$"),                  # Teléfono emisor
    "dTelRec": re.compile(r"^\d{6,15}$"),                  # Teléfono receptor

    # Emails
    # Email emisor
    "dEmailE": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    # Email receptor
    "dEmailRec": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
}

# Información detallada de patrones de campos
BASIC_FIELD_PATTERNS: Dict[str, Dict[str, Any]] = {
    "dVerFor": {
        "pattern": r"^150$",
        "data_type": "string",
        "min_length": 3,
        "max_length": 3,
        "description": "Versión del formato SIFEN"
    },
    "dRUCEmi": {
        "pattern": r"^\d{1,8}-?\d?$",
        "data_type": "string",
        "min_length": 3,
        "max_length": 10,
        "description": "RUC del emisor"
    },
    "dCodSeg": {
        "pattern": r"^[A-Za-z0-9]{9}$",
        "data_type": "string",
        "min_length": 9,
        "max_length": 9,
        "description": "Código de seguridad"
    },
    "iTiDE": {
        "pattern": r"^(01|04|05|06|07)$",
        "data_type": "string",
        "min_length": 2,
        "max_length": 2,
        "description": "Tipo de documento electrónico"
    },
    "dNumDoc": {
        "pattern": r"^\d{3}-\d{3}-\d{7}$",
        "data_type": "string",
        "min_length": 15,
        "max_length": 15,
        "description": "Número de documento"
    },
    "dFeEmiDE": {
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "data_type": "date",
        "min_length": 10,
        "max_length": 10,
        "description": "Fecha de emisión"
    },
    "dHorEmi": {
        "pattern": r"^\d{2}:\d{2}:\d{2}$",
        "data_type": "time",
        "min_length": 8,
        "max_length": 8,
        "description": "Hora de emisión"
    },
    "iTimbr": {
        "pattern": r"^\d{8}$",
        "data_type": "integer",
        "min_length": 8,
        "max_length": 8,
        "description": "Número de timbrado"
    },
    "dEstTimbr": {
        "pattern": r"^\d{3}$",
        "data_type": "integer",
        "min_length": 3,
        "max_length": 3,
        "description": "Establecimiento"
    },
    "dPunExp": {
        "pattern": r"^\d{3}$",
        "data_type": "integer",
        "min_length": 3,
        "max_length": 3,
        "description": "Punto de expedición"
    },
    "cActEco": {
        "pattern": r"^\d{5}$",
        "data_type": "integer",
        "min_length": 5,
        "max_length": 5,
        "description": "Código de actividad económica"
    },
    "cPaiEmi": {
        "pattern": r"^[A-Z]{3}$",
        "data_type": "string",
        "min_length": 3,
        "max_length": 3,
        "description": "Código de país del emisor"
    },
    "cUniMed": {
        "pattern": r"^\d{2}$",
        "data_type": "integer",
        "min_length": 2,
        "max_length": 2,
        "description": "Código de unidad de medida"
    },
    "dCantProSer": {
        "pattern": r"^\d{1,7}(\.\d{1,4})?$",
        "data_type": "decimal",
        "min_value": 0.0001,
        "max_value": 9999999.9999,
        "description": "Cantidad de producto/servicio"
    },
    "dPUniProSer": {
        "pattern": r"^\d{1,11}(\.\d{1,4})?$",
        "data_type": "decimal",
        "min_value": 0.0001,
        "max_value": 99999999999.9999,
        "description": "Precio unitario"
    },
}


# ================================
# CÓDIGOS Y TABLAS DE REFERENCIA
# ================================

# Códigos de país (ISO 3166-1 alpha-3) - principales
COUNTRY_CODES = {
    "PRY": "Paraguay",
    "ARG": "Argentina",
    "BRA": "Brasil",
    "BOL": "Bolivia",
    "URY": "Uruguay",
    "CHL": "Chile",
    "USA": "Estados Unidos",
    "ESP": "España",
    "DEU": "Alemania",
    "FRA": "Francia",
}

# Códigos de moneda (ISO 4217) - principales
CURRENCY_CODES = {
    "PYG": "Guaraní paraguayo",
    "USD": "Dólar estadounidense",
    "EUR": "Euro",
    "ARS": "Peso argentino",
    "BRL": "Real brasileño",
    "BOB": "Boliviano",
    "UYU": "Peso uruguayo",
    "CLP": "Peso chileno",
}

# Tipos de transacción de venta
TRANSACTION_TYPES = {
    "1": "Venta de mercaderías",
    "2": "Prestación de servicios",
    "3": "Mixto (mercaderías y servicios)",
    "4": "Venta de activo fijo",
    "5": "Venta de oro y metales preciosos",
    "6": "Venta de divisas",
    "7": "Venta de lotería, quiniela y similares",
    "8": "Venta de productos sujetos a régimen especial",
    "9": "Otros",
}

# Naturaleza del receptor
RECEIVER_NATURE = {
    "1": "Contribuyente",
    "2": "No contribuyente",
}

# Tipo de operación
OPERATION_TYPES = {
    "1": "B2B (Business to Business)",
    "2": "B2C (Business to Consumer)",
    "3": "B2G (Business to Government)",
    "4": "B2F (Business to Final Consumer)",
}

# Unidades de medida más comunes
MEASUREMENT_UNITS = {
    "01": "Unidad",
    "02": "Kilogramo",
    "03": "Gramo",
    "04": "Tonelada",
    "05": "Litro",
    "06": "Metro",
    "07": "Metro cuadrado",
    "08": "Metro cúbico",
    "09": "Kilómetro",
    "10": "Centímetro",
    "11": "Milímetro",
    "12": "Pulgada",
    "13": "Pie",
    "14": "Yarda",
    "15": "Milla",
    "16": "Onza",
    "17": "Libra",
    "18": "Quintal",
    "19": "Galón",
    "20": "Barril",
}


# ================================
# CÓDIGOS DE RESPUESTA SIFEN
# ================================

# Códigos de estado de respuesta SIFEN
SIFEN_RESPONSE_CODES = {
    # Códigos de éxito
    "0260": "Aprobado",
    "0261": "Aprobado con observaciones",

    # Códigos de error comunes
    "1000": "Error de formato XML",
    "1001": "Error de schema XSD",
    "1002": "Error de namespace",
    "1003": "Error de encoding",
    "1010": "Error de firma digital",
    "1011": "Certificado inválido",
    "1012": "Certificado vencido",
    "1020": "RUC no encontrado",
    "1021": "RUC no habilitado para facturar",
    "1030": "Timbrado inválido",
    "1031": "Timbrado vencido",
    "1032": "Timbrado no activo",
    "1040": "Número de documento duplicado",
    "1041": "Secuencia de numeración incorrecta",
    "1050": "Error en datos del receptor",
    "1051": "RUC receptor inválido",
    "1060": "Error en totales",
    "1061": "Totales no coinciden",
    "1070": "Error en items",
    "1071": "Código de producto inválido",
    "1080": "Error en condición de pago",
    "1090": "Error en datos de transporte",
    "1100": "Error de negocio",
    "1250": "Error de validación",
    "5000": "Error interno del sistema",
}

# Códigos de error por categoría
ERROR_CATEGORIES = {
    "format": ["1000", "1001", "1002", "1003"],
    "digital_signature": ["1010", "1011", "1012"],
    "ruc": ["1020", "1021", "1050", "1051"],
    "stamping": ["1030", "1031", "1032"],
    "numbering": ["1040", "1041"],
    "business_logic": ["1060", "1061", "1070", "1071", "1080", "1090", "1100"],
    "validation": ["1250"],
    "system": ["5000"],
}


# ================================
# CONFIGURACIÓN DE TESTING
# ================================

# Timeouts para operaciones de testing (en segundos)
TEST_TIMEOUTS = {
    "xml_parsing": 5.0,
    "schema_validation": 10.0,
    "schema_loading": 15.0,
    "dependency_check": 30.0,
    "full_validation": 60.0,
}

# Límites para testing de performance
PERFORMANCE_LIMITS = {
    "max_xml_size_mb": 10,
    "max_validation_time_sec": 5.0,
    "max_schema_load_time_sec": 2.0,
    "max_items_per_document": 1000,
    "max_memory_usage_mb": 100,
}

# Configuración de cache para testing
CACHE_CONFIG = {
    "max_schemas_cached": 20,
    "max_xml_samples_cached": 100,
    "cache_timeout_minutes": 30,
    "enable_dependency_cache": True,
    "enable_validation_cache": True,
}

# Niveles de logging para testing
TEST_LOG_LEVELS = {
    "xml_parsing": "DEBUG",
    "schema_validation": "INFO",
    "dependency_check": "WARNING",
    "performance": "INFO",
    "errors": "ERROR",
}

# Configuración de mocks para testing
MOCK_CONFIG = {
    "use_real_schemas": True,
    "mock_network_calls": True,
    "mock_file_system": False,
    "generate_test_data": True,
    "validate_mock_responses": True,
}


# ================================
# DATOS DE TESTING
# ================================

# RUCs de testing válidos (ficticios para pruebas)
TEST_VALID_RUCS = [
    "12345678-9",
    "87654321-0",
    "11111111-1",
    "22222222-2",
    "33333333-3",
]

# Timbrados de testing válidos (ficticios)
TEST_VALID_STAMPS = [
    "12345678",
    "87654321",
    "11111111",
    "22222222",
    "33333333",
]

# Códigos de seguridad de testing
TEST_SECURITY_CODES = [
    "ABC123456",
    "XYZ789012",
    "DEF345678",
    "GHI901234",
    "JKL567890",
]

# Fechas de testing (formato YYYY-MM-DD)
TEST_VALID_DATES = [
    "2024-01-15",
    "2024-06-30",
    "2024-12-31",
    "2025-01-01",
    "2025-06-18",
]

# Direcciones de testing para endpoints
TEST_ENDPOINTS = {
    "production": {
        "sync": "https://sifen.set.gov.py/de/ws/sync/recibe.wsdl",
        "async": "https://sifen.set.gov.py/de/ws/async/recibe-lote.wsdl",
        "query": "https://sifen.set.gov.py/de/ws/consultas/consulta.wsdl",
    },
    "testing": {
        "sync": "https://sifen-test.set.gov.py/de/ws/sync/recibe.wsdl",
        "async": "https://sifen-test.set.gov.py/de/ws/async/recibe-lote.wsdl",
        "query": "https://sifen-test.set.gov.py/de/ws/consultas/consulta.wsdl",
    }
}


# ================================
# VERSIONING Y COMPATIBILIDAD
# ================================

# Versiones soportadas de SIFEN
SUPPORTED_SIFEN_VERSIONS = ["150"]

# Versiones deprecadas
DEPRECATED_SIFEN_VERSIONS = ["120", "130", "141"]

# Compatibilidad hacia atrás
BACKWARD_COMPATIBILITY = {
    "150": {
        "supports": ["150"],
        "deprecated": ["141", "130"],
        "migration_required": ["120"],
    }
}

# Información de versión del módulo
MODULE_VERSION = {
    "version": "1.0.0",
    "sifen_version": "150",
    "last_updated": "2025-06-17",
    "compatible_schemas": ["DE_v150.xsd"],
    "python_min_version": "3.8",
}


# ================================
# CONFIGURACIÓN POR ENTORNO
# ================================

class Environment(Enum):
    """Entornos de ejecución disponibles"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


# Configuración específica por entorno
ENVIRONMENT_CONFIG = {
    Environment.DEVELOPMENT: {
        "strict_validation": False,
        "cache_enabled": True,
        "mock_external_services": True,
        "log_level": "DEBUG",
        "performance_monitoring": False,
    },
    Environment.TESTING: {
        "strict_validation": True,
        "cache_enabled": True,
        "mock_external_services": True,
        "log_level": "INFO",
        "performance_monitoring": True,
    },
    Environment.STAGING: {
        "strict_validation": True,
        "cache_enabled": True,
        "mock_external_services": False,
        "log_level": "WARNING",
        "performance_monitoring": True,
    },
    Environment.PRODUCTION: {
        "strict_validation": True,
        "cache_enabled": True,
        "mock_external_services": False,
        "log_level": "ERROR",
        "performance_monitoring": True,
    }
}


# ================================
# XPATH EXPRESSIONS COMUNES
# ================================

# XPaths para elementos principales
MAIN_XPATH_EXPRESSIONS = {
    # Elementos de documento
    "document_root": "//rDE",
    "document_element": "//DE",
    "document_id": "//DE/@Id",
    "format_version": "//dVerFor",
    "document_type": "//iTiDE",
    "document_number": "//dNumDoc",
    "emission_date": "//dFeEmiDE",
    "emission_time": "//dHorEmi",

    # Datos de timbrado
    "stamping_data": "//gTimb",
    "stamp_number": "//iTimbr",
    "establishment": "//dEstTimbr",
    "expedition_point": "//dPunExp",
    "stamp_start_date": "//dFeIniT",
    "stamp_end_date": "//dFeFinT",

    # Datos del emisor
    "issuer_data": "//gEmis",
    "issuer_ruc": "//dRUCEmi",
    "issuer_name": "//dNomEmi",
    "issuer_address": "//dDirEmi",
    "issuer_phone": "//dTelEmi",
    "issuer_email": "//dEmailE",
    "issuer_country": "//cPaiEmi",

    # Actividad económica
    "economic_activity": "//gActEco",
    "activity_code": "//cActEco",
    "activity_description": "//dDesActEco",

    # Datos del receptor
    "receiver_data": "//gDatRec",
    "receiver_ruc": "//dRUCRec",
    "receiver_name": "//dNomRec",
    "receiver_address": "//dDirRec",
    "receiver_phone": "//dTelRec",
    "receiver_email": "//dEmailRec",
    "receiver_nature": "//iNatRec",

    # Datos generales
    "general_data": "//gDatGral",
    "operation_type": "//iTiOpe",
    "transaction_type": "//iTiTranVenta",
    "operation_currency": "//cMoneOpe",
    "exchange_rate": "//dTiCam",

    # Items/productos
    "items_group": "//gCamItem",
    "item": "//gCamItem/gItem",
    "item_code": "//dCodInt",
    "item_description": "//dDesProSer",
    "item_unit": "//cUniMed",
    "item_quantity": "//dCantProSer",
    "item_unit_price": "//dPUniProSer",
    "item_total": "//dTotBruOpeItem",

    # Totales
    "totals": "//gTotSub",
    "subtotal": "//dSubExe",
    "total_operation": "//dTotOpe",
    "total_general": "//dTotGral",

    # Datos específicos por tipo de documento
    "fe_specific": "//gCamFE",
    "ae_specific": "//gCamAE",
    "nce_specific": "//gCamNCE",
    "nde_specific": "//gCamNDE",
    "nre_specific": "//gCamNRE",

    # Transporte (para notas de remisión)
    "transport_data": "//gTransp",
    "transport_mode": "//iModTrans",
    "vehicle_data": "//gVehTras",
    "driver_data": "//gCondTrans",

    # Condición de pago
    "payment_condition": "//gPaConEIni",
    "payment_type": "//iTiPago",
    "payment_amount": "//dMonTiPag",
    "payment_currency": "//cMoneTiPag",

    # Firma digital
    "signature": "//ds:Signature",
    "signature_info": "//ds:SignedInfo",
    "signature_value": "//ds:SignatureValue",
    "key_info": "//ds:KeyInfo",
}

# XPaths para validaciones específicas
VALIDATION_XPATH_EXPRESSIONS = {
    # Validaciones de estructura básica
    "has_namespace": "//rDE[namespace-uri()='http://ekuatia.set.gov.py/sifen/xsd']",
    "has_version": "//dVerFor[text()='150']",
    "has_document_id": "//DE[@Id and string-length(@Id)=44]",
    "has_valid_doc_type": "//iTiDE[text()='01' or text()='04' or text()='05' or text()='06' or text()='07']",

    # Validaciones de formato de fecha
    "valid_emission_date": "//dFeEmiDE[matches(text(), '^\\d{4}-\\d{2}-\\d{2})]",
    "valid_emission_time": "//dHorEmi[matches(text(), '^\\d{2}:\\d{2}:\\d{2})]",

    # Validaciones de RUC
    "valid_issuer_ruc": "//dRUCEmi[matches(text(), '^\\d{1,8}-?\\d?)]",
    "valid_receiver_ruc": "//dRUCRec[matches(text(), '^\\d{1,8}-?\\d?)]",

    # Validaciones de timbrado
    "valid_stamp_number": "//iTimbr[matches(text(), '^\\d{8})]",
    "valid_establishment": "//dEstTimbr[matches(text(), '^\\d{3})]",
    "valid_expedition_point": "//dPunExp[matches(text(), '^\\d{3})]",

    # Validaciones de montos
    "valid_unit_price": "//dPUniProSer[matches(text(), '^\\d{1,11}(\\.\\d{1,4})?)]",
    "valid_quantity": "//dCantProSer[matches(text(), '^\\d{1,7}(\\.\\d{1,4})?)]",
    "valid_total": "//dTotOpe[matches(text(), '^\\d{1,11}(\\.\\d{1,4})?)]",

    # Validaciones de códigos
    "valid_activity_code": "//cActEco[matches(text(), '^\\d{5})]",
    "valid_unit_code": "//cUniMed[matches(text(), '^\\d{2})]",
    "valid_country_code": "//cPaiEmi[matches(text(), '^[A-Z]{3})]",
    "valid_currency_code": "//cMoneOpe[matches(text(), '^[A-Z]{3})]",
}


# ================================
# MENSAJES DE ERROR ESTÁNDAR
# ================================

# Mensajes de error para validaciones comunes
VALIDATION_ERROR_MESSAGES = {
    # Errores de estructura
    "missing_namespace": "Namespace SIFEN requerido: {0}",
    "invalid_version": "Versión de formato inválida. Esperada: 150, encontrada: {0}",
    "missing_document_id": "Atributo Id del elemento DE es requerido",
    "invalid_document_id_length": "Id del documento debe tener 44 caracteres, encontrado: {0}",
    "invalid_document_type": "Tipo de documento inválido: {0}. Valores válidos: 01, 04, 05, 06, 07",

    # Errores de formato
    "invalid_date_format": "Formato de fecha inválido en {0}. Esperado: YYYY-MM-DD, encontrado: {1}",
    "invalid_time_format": "Formato de hora inválido en {0}. Esperado: HH:MM:SS, encontrado: {1}",
    "invalid_ruc_format": "Formato de RUC inválido en {0}: {1}",
    "invalid_amount_format": "Formato de monto inválido en {0}: {1}",
    "invalid_quantity_format": "Formato de cantidad inválido en {0}: {1}",

    # Errores de contenido
    "missing_required_element": "Elemento requerido faltante: {0}",
    "prohibited_element_present": "Elemento no permitido para este tipo de documento: {0}",
    "empty_required_field": "Campo requerido no puede estar vacío: {0}",
    "invalid_field_length": "Longitud inválida en {0}. Mín: {1}, Máx: {2}, Actual: {3}",

    # Errores de negocio
    "invalid_stamp_dates": "Fecha de emisión fuera del rango del timbrado",
    "duplicate_document_number": "Número de documento duplicado: {0}",
    "invalid_totals": "Los totales no coinciden con la suma de items",
    "invalid_receiver_for_document_type": "Receptor inválido para tipo de documento {0}",

    # Errores de dependencias
    "missing_module_dependency": "Dependencia de módulo faltante: {0}",
    "invalid_schema_reference": "Referencia de schema inválida: {0}",
    "circular_dependency": "Dependencia circular detectada en módulo: {0}",
}

# Mensajes de warning
VALIDATION_WARNING_MESSAGES = {
    "deprecated_field": "Campo deprecado detectado: {0}",
    "optional_field_missing": "Campo opcional recomendado faltante: {0}",
    "performance_warning": "Operación tardó más de lo esperado: {0}ms",
    "large_document": "Documento grande detectado: {0} items",
    "old_schema_version": "Versión de schema antigua: {0}",
}


# ================================
# CONFIGURACIÓN DE SCHEMAS MODULARES
# ================================

# Módulos de schema y sus dependencias
SCHEMA_MODULE_DEPENDENCIES = {
    "DE_v150.xsd": [
        "common/basic_types.xsd",
        "common/geographic_types.xsd",
        "common/contact_types.xsd",
        "common/currency_types.xsd",
        "document_core/core_types.xsd",
        "parties/issuer_types.xsd",
        "parties/receiver_types.xsd",
        "operations/operation_types.xsd",
        "operations/payment_types.xsd",
        "operations/item_types.xsd",
        "transport/transport_types.xsd",
    ],
    "common/basic_types.xsd": [],
    "common/geographic_types.xsd": ["common/basic_types.xsd"],
    "common/contact_types.xsd": ["common/basic_types.xsd"],
    "common/currency_types.xsd": ["common/basic_types.xsd"],
    "document_core/core_types.xsd": ["common/basic_types.xsd"],
    "document_core/stamping_types.xsd": ["common/basic_types.xsd"],
    "parties/issuer_types.xsd": [
        "common/basic_types.xsd",
        "common/geographic_types.xsd",
        "common/contact_types.xsd"
    ],
    "parties/receiver_types.xsd": [
        "common/basic_types.xsd",
        "common/geographic_types.xsd",
        "common/contact_types.xsd"
    ],
    "operations/operation_types.xsd": [
        "common/basic_types.xsd",
        "common/currency_types.xsd"
    ],
    "operations/payment_types.xsd": [
        "common/basic_types.xsd",
        "common/currency_types.xsd"
    ],
    "operations/item_types.xsd": [
        "common/basic_types.xsd",
        "common/currency_types.xsd"
    ],
    "transport/transport_types.xsd": [
        "common/basic_types.xsd",
        "common/geographic_types.xsd",
        "parties/issuer_types.xsd"
    ],
}

# Orden de carga de módulos (para resolver dependencias)
SCHEMA_LOAD_ORDER = [
    "common/basic_types.xsd",
    "common/geographic_types.xsd",
    "common/contact_types.xsd",
    "common/currency_types.xsd",
    "document_core/core_types.xsd",
    "document_core/stamping_types.xsd",
    "parties/issuer_types.xsd",
    "parties/receiver_types.xsd",
    "operations/operation_types.xsd",
    "operations/payment_types.xsd",
    "operations/item_types.xsd",
    "transport/transport_types.xsd",
    "DE_v150.xsd",
]


# ================================
# UTILIDADES DE DEBUGGING
# ================================

# Elementos a mostrar en debugging básico
DEBUG_ELEMENTS = [
    "//dVerFor",
    "//iTiDE",
    "//dNumDoc",
    "//dFeEmiDE",
    "//dRUCEmi",
    "//dNomEmi",
    "//dRUCRec",
    "//dNomRec",
    "//iTimbr",
    "//dTotOpe",
]

# Elementos sensibles que no se deben loggear
SENSITIVE_ELEMENTS = [
    "//ds:Signature",
    "//ds:SignatureValue",
    "//ds:KeyInfo",
    "//dCodSeg",  # Código de seguridad
]

# Configuración de pretty printing para XML
XML_PRETTY_PRINT_CONFIG = {
    "indent": "  ",
    "encoding": "unicode",
    "xml_declaration": True,
    "pretty_print": True,
    "remove_blank_text": True,
}


# ================================
# FUNCIONES DE UTILIDAD
# ================================

def get_document_type_info(doc_type: str) -> Optional[DocumentTypeInfo]:
    """
    Obtiene información de un tipo de documento SIFEN

    Args:
        doc_type: Código del tipo de documento (01, 04, 05, 06, 07)

    Returns:
        DocumentTypeInfo con información del documento o None si no existe
    """
    return SIFEN_DOCUMENT_TYPES.get(doc_type)


def is_valid_document_type(doc_type: str) -> bool:
    """
    Verifica si un tipo de documento es válido

    Args:
        doc_type: Código del tipo de documento

    Returns:
        True si es válido, False en caso contrario
    """
    return doc_type in SIFEN_DOCUMENT_TYPES


def get_field_pattern(field_name: str) -> Optional[Pattern[str]]:
    """
    Obtiene el patrón regex para un campo específico

    Args:
        field_name: Nombre del campo

    Returns:
        Patrón regex compilado o None si no existe
    """
    return FIELD_REGEX_PATTERNS.get(field_name)


def get_error_message(error_code: str) -> str:
    """
    Obtiene el mensaje de error para un código SIFEN

    Args:
        error_code: Código de error SIFEN

    Returns:
        Mensaje de error o mensaje genérico si no existe
    """
    return SIFEN_RESPONSE_CODES.get(error_code, f"Error desconocido: {error_code}")


def get_xpath_expression(expression_name: str) -> Optional[str]:
    """
    Obtiene una expresión XPath predefinida

    Args:
        expression_name: Nombre de la expresión

    Returns:
        Expresión XPath o None si no existe
    """
    return MAIN_XPATH_EXPRESSIONS.get(expression_name)


def get_required_elements_for_document_type(doc_type: str) -> List[str]:
    """
    Obtiene los elementos requeridos para un tipo de documento específico

    Args:
        doc_type: Código del tipo de documento

    Returns:
        Lista de XPaths de elementos requeridos
    """
    doc_info = get_document_type_info(doc_type)
    if doc_info:
        return REQUIRED_SIFEN_ELEMENTS + doc_info.required_elements
    return REQUIRED_SIFEN_ELEMENTS


def get_prohibited_elements_for_document_type(doc_type: str) -> List[str]:
    """
    Obtiene los elementos prohibidos para un tipo de documento específico

    Args:
        doc_type: Código del tipo de documento

    Returns:
        Lista de XPaths de elementos prohibidos
    """
    doc_info = get_document_type_info(doc_type)
    if doc_info:
        return doc_info.prohibited_elements
    return []


def is_production_environment() -> bool:
    """
    Determina si se está ejecutando en entorno de producción

    Returns:
        True si es producción, False en caso contrario
    """
    import os
    env = os.getenv('SIFEN_ENVIRONMENT', 'development').lower()
    return env == 'production'


def get_environment_config(env: Optional[Environment] = None) -> Dict[str, Any]:
    """
    Obtiene la configuración para un entorno específico

    Args:
        env: Entorno deseado. Si es None, detecta automáticamente

    Returns:
        Diccionario con configuración del entorno
    """
    if env is None:
        import os
        env_str = os.getenv('SIFEN_ENVIRONMENT', 'development').lower()
        try:
            env = Environment(env_str)
        except ValueError:
            env = Environment.DEVELOPMENT

    return ENVIRONMENT_CONFIG.get(env, ENVIRONMENT_CONFIG[Environment.DEVELOPMENT])


# ================================
# VALIDACIÓN DEL MÓDULO
# ================================

def validate_constants() -> List[str]:
    """
    Valida la consistencia de las constantes definidas

    Returns:
        Lista de errores encontrados (vacía si todo está bien)
    """
    errors = []

    # Validar que todos los tipos de documento tengan información completa
    for doc_type, doc_info in SIFEN_DOCUMENT_TYPES.items():
        if not doc_info.name:
            errors.append(f"Tipo de documento {doc_type} sin nombre")
        if not doc_info.required_elements:
            errors.append(
                f"Tipo de documento {doc_type} sin elementos requeridos")

    # Validar que todos los XPaths en required_elements sean válidos
    for doc_type, doc_info in SIFEN_DOCUMENT_TYPES.items():
        for xpath in doc_info.required_elements:
            if not xpath.startswith('//'):
                errors.append(f"XPath inválido en {doc_type}: {xpath}")

    # Validar que los patrones regex sean válidos
    for field_name, pattern in FIELD_REGEX_PATTERNS.items():
        try:
            re.compile(pattern.pattern)
        except re.error as e:
            errors.append(f"Patrón regex inválido para {field_name}: {e}")

    # Validar que las dependencias de módulos existan
    for module, deps in SCHEMA_MODULE_DEPENDENCIES.items():
        for dep in deps:
            if dep not in SCHEMA_MODULE_DEPENDENCIES and dep != module:
                errors.append(
                    f"Dependencia no definida: {dep} requerida por {module}")

    return errors


# Ejecutar validación al importar el módulo
_validation_errors = validate_constants()
if _validation_errors:
    import warnings
    warnings.warn(f"Errores en constantes SIFEN: {_validation_errors}")

# Document Types

DOCUMENT_TYPE_INVOICE: str = "1"
DOCUMENT_TYPE_CREDIT_NOTE: str = "2"
DOCUMENT_TYPE_DEBIT_NOTE: str = "3"
DOCUMENT_TYPE_REMISSION: str = "4"
DOCUMENT_TYPE_SELF_INVOICE: str = "5"

# Tax Types
TAX_TYPE_IVA: str = "1"
TAX_TYPE_ISC: str = "2"
TAX_TYPE_RENTA: str = "3"

# Common test values
DEFAULT_STRING_LENGTH: int = 100
MAX_DECIMAL_PLACES: int = 8
DEFAULT_CURRENCY: str = "PYG"

# Testing boundaries
AMOUNT_LIMITS: Dict[str, Union[int, float]] = {
    "min": 0,
    "max": 999999999999.99999999,
    "decimal_places": 8
}

STRING_LIMITS: Dict[str, int] = {
    "min_length": 1,
    "max_length": 100
}

DATE_LIMITS: Dict[str, int] = {
    "min_year": 2000,
    "max_year": 2100
}

# Document number formats
ESTABLISHMENT_LENGTH: int = 3
POINT_OF_SALE_LENGTH: int = 3
DOCUMENT_NUMBER_LENGTH: int = 7

# ================================
# METADATA DEL MÓDULO
# ================================

__all__ = [
    # Configuración básica
    'SIFEN_NAMESPACE_URI',
    'SIFEN_SCHEMA_VERSION',
    'SIFEN_FORMAT_VERSION',
    'SIFEN_REQUIRED_ENCODING',

    # Tipos de documentos
    'SIFEN_DOCUMENT_TYPES',
    'DocumentTypeInfo',

    # Elementos requeridos
    'REQUIRED_SIFEN_ELEMENTS',
    'REQUIRED_STAMPING_ELEMENTS',
    'REQUIRED_ITEM_ELEMENTS',

    # Patrones de validación
    'FIELD_REGEX_PATTERNS',
    'BASIC_FIELD_PATTERNS',

    # Códigos de referencia
    'COUNTRY_CODES',
    'CURRENCY_CODES',
    'TRANSACTION_TYPES',
    'RECEIVER_NATURE',
    'OPERATION_TYPES',
    'MEASUREMENT_UNITS',

    # Códigos de respuesta
    'SIFEN_RESPONSE_CODES',
    'ERROR_CATEGORIES',

    # Configuración de testing
    'TEST_TIMEOUTS',
    'PERFORMANCE_LIMITS',
    'CACHE_CONFIG',
    'TEST_LOG_LEVELS',
    'MOCK_CONFIG',

    # Datos de testing
    'TEST_VALID_RUCS',
    'TEST_VALID_STAMPS',
    'TEST_SECURITY_CODES',
    'TEST_VALID_DATES',
    'TEST_ENDPOINTS',

    # XPath expressions
    'MAIN_XPATH_EXPRESSIONS',
    'VALIDATION_XPATH_EXPRESSIONS',

    # Mensajes de error
    'VALIDATION_ERROR_MESSAGES',
    'VALIDATION_WARNING_MESSAGES',

    # Configuración modular
    'SCHEMA_MODULE_DEPENDENCIES',
    'SCHEMA_LOAD_ORDER',

    # Debugging
    'DEBUG_ELEMENTS',
    'SENSITIVE_ELEMENTS',
    'XML_PRETTY_PRINT_CONFIG',

    # Entornos
    'Environment',
    'ENVIRONMENT_CONFIG',

    # Funciones de utilidad
    'get_document_type_info',
    'is_valid_document_type',
    'get_field_pattern',
    'get_error_message',
    'get_xpath_expression',
    'get_required_elements_for_document_type',
    'get_prohibited_elements_for_document_type',
    'is_production_environment',
    'get_environment_config',
    'validate_constants',
]
