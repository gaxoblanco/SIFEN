"""
Constantes y tablas de referencia para SIFEN v150 Paraguay.

Este módulo centraliza todas las constantes oficiales, códigos de referencia,
tablas de validación y enumeraciones utilizadas en el sistema SIFEN 
(Sistema Integrado de Facturación Electrónica Nacional) de Paraguay.

RESPONSABILIDADES:
- Tipos de documentos electrónicos oficiales
- Códigos de respuesta y estados SIFEN
- Referencias geográficas (departamentos, distritos, ciudades)
- Tablas de monedas, unidades de medida y códigos tributarios
- Patrones de validación y formatos
- Configuraciones del sistema

FUENTES OFICIALES:
- Manual Técnico SIFEN v150 (Sept 2019)
- Portal Ekuatia SET: https://ekuatia.set.gov.py/
- Tablas de códigos oficiales SET Paraguay
- Esquemas XSD v150 oficiales

ÚLTIMA ACTUALIZACIÓN: Basado en especificaciones vigentes 2025

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum
from decimal import Decimal


# ===================================================================
# INFORMACIÓN DEL SISTEMA SIFEN
# ===================================================================

# Información básica del sistema
SIFEN_VERSION = "150"
SIFEN_NAMESPACE = "http://ekuatia.set.gov.py/sifen/xsd"
SIFEN_SCHEMA_LOCATION = f"{SIFEN_NAMESPACE} DE_v150.xsd"

# URLs oficiales
SIFEN_URLS = {
    'production': 'https://sifen.set.gov.py/',
    'test': 'https://sifen-test.set.gov.py/',
    'portal': 'https://ekuatia.set.gov.py/',
    'documentation': 'https://ekuatia.set.gov.py/portal/ekuatia/documentacion/'
}

# Información del país
PAIS_INFO = {
    'codigo': 'PY',
    'nombre': 'Paraguay',
    'moneda_oficial': 'PYG',
    'timezone': 'America/Asuncion',
    'timezone_offset': 'UTC-3'
}


# ===================================================================
# TIPOS DE DOCUMENTOS ELECTRÓNICOS
# ===================================================================

class TipoDocumentoElectronico(Enum):
    """Tipos de documentos electrónicos SIFEN v150."""
    FACTURA_ELECTRONICA = ("01", "Factura Electrónica")
    AUTOFACTURA_ELECTRONICA = ("04", "Autofactura Electrónica")
    NOTA_CREDITO_ELECTRONICA = ("05", "Nota de Crédito Electrónica")
    NOTA_DEBITO_ELECTRONICA = ("06", "Nota de Débito Electrónica")
    NOTA_REMISION_ELECTRONICA = ("07", "Nota de Remisión Electrónica")

    def __init__(self, codigo: str, descripcion: str):
        self.codigo = codigo
        self.descripcion = descripcion


# Diccionario para búsqueda rápida
TIPOS_DOCUMENTO = {
    "01": "Factura Electrónica",
    "04": "Autofactura Electrónica",
    "05": "Nota de Crédito Electrónica",
    "06": "Nota de Débito Electrónica",
    "07": "Nota de Remisión Electrónica"
}

# Lista de códigos válidos
CODIGOS_DOCUMENTO_VALIDOS = list(TIPOS_DOCUMENTO.keys())


# ===================================================================
# CÓDIGOS DE RESPUESTA SIFEN
# ===================================================================

class CodigoRespuestaSifen(Enum):
    """Códigos de respuesta oficiales SIFEN."""
    # Respuestas exitosas
    APROBADO = ("0260", "Documento aprobado")
    APROBADO_OBSERVACIONES = ("1005", "Documento aprobado con observaciones")

    # Errores de estructura XML
    XML_MALFORMADO = ("0100", "XML malformado")
    SCHEMA_INVALIDO = ("0101", "Documento no válido según schema")
    ENCODING_INVALIDO = ("0102", "Encoding del documento inválido")

    # Errores de firma digital
    FIRMA_INVALIDA = ("0141", "Firma digital inválida")
    CERTIFICADO_INVALIDO = ("0142", "Certificado digital inválido")
    CERTIFICADO_VENCIDO = ("0143", "Certificado digital vencido")

    # Errores de CDC
    CDC_DUPLICADO = ("1001", "CDC duplicado")
    CDC_FORMATO_INVALIDO = ("1002", "Formato de CDC inválido")
    CDC_NO_CORRESPONDE = ("1003", "CDC no corresponde con los datos")

    # Errores de RUC
    RUC_INEXISTENTE = ("1250", "RUC emisor inexistente")
    RUC_NO_AUTORIZADO = (
        "1251", "RUC no autorizado para documentos electrónicos")
    RUC_SUSPENDIDO = ("1252", "RUC emisor suspendido")

    # Errores de timbrado
    TIMBRADO_INVALIDO = ("1101", "Número de timbrado inválido")
    TIMBRADO_VENCIDO = ("1102", "Timbrado vencido")
    TIMBRADO_NO_VIGENTE = ("1103", "Timbrado no vigente")

    # Errores de fechas
    FECHA_FUTURA = ("1403", "Fecha de emisión futura")
    FECHA_MUY_ANTIGUA = ("1404", "Documento fuera de plazo")

    # Errores de servidor
    ERROR_INTERNO = ("5000", "Error interno del servidor")
    SERVICIO_NO_DISPONIBLE = ("5001", "Servicio no disponible")
    TIMEOUT = ("5002", "Timeout en el procesamiento")

    def __init__(self, codigo: str, descripcion: str):
        self.codigo = codigo
        self.descripcion = descripcion


# Agrupación por categorías
CODIGOS_EXITOSOS = ["0260", "1005"]
CODIGOS_ERROR_XML = ["0100", "0101", "0102"]
CODIGOS_ERROR_FIRMA = ["0141", "0142", "0143"]
CODIGOS_ERROR_CDC = ["1001", "1002", "1003"]
CODIGOS_ERROR_RUC = ["1250", "1251", "1252"]
CODIGOS_ERROR_SERVIDOR = ["5000", "5001", "5002"]


# ===================================================================
# TIPOS DE EMISIÓN
# ===================================================================

class TipoEmision(Enum):
    """Tipos de emisión de documentos."""
    NORMAL = ("1", "Emisión Normal")
    CONTINGENCIA = ("2", "Emisión de Contingencia")

    def __init__(self, codigo: str, descripcion: str):
        self.codigo = codigo
        self.descripcion = descripcion


TIPOS_EMISION = {
    "1": "Emisión Normal",
    "2": "Emisión de Contingencia"
}


# ===================================================================
# TIPOS DE CONTRIBUYENTE
# ===================================================================

class TipoContribuyente(Enum):
    """Tipos de contribuyente según SIFEN."""
    PERSONA_FISICA = ("1", "Persona Física")
    PERSONA_JURIDICA = ("2", "Persona Jurídica")

    def __init__(self, codigo: str, descripcion: str):
        self.codigo = codigo
        self.descripcion = descripcion


TIPOS_CONTRIBUYENTE = {
    "1": "Persona Física",
    "2": "Persona Jurídica"
}


# ===================================================================
# TIPOS DE RÉGIMEN TRIBUTARIO
# ===================================================================

TIPOS_REGIMEN = {
    "1": "Régimen de Turismo",
    "2": "Importador",
    "3": "Exportador",
    "4": "Maquila",
    "5": "Ley N° 60/90",
    "6": "Régimen del Pequeño Productor",
    "7": "Régimen del Mediano Productor",
    "8": "Régimen Contable"
}


# ===================================================================
# MONEDAS Y TIPOS DE CAMBIO
# ===================================================================

class MonedaOperacion(Enum):
    """Monedas soportadas por SIFEN."""
    GUARANI = ("PYG", "Guaraní paraguayo")
    DOLAR = ("USD", "Dólar americano")
    EURO = ("EUR", "Euro")
    REAL = ("BRL", "Real brasileño")
    PESO_ARGENTINO = ("ARS", "Peso argentino")

    def __init__(self, codigo: str, descripcion: str):
        self.codigo = codigo
        self.descripcion = descripcion


MONEDAS_SIFEN = {
    "PYG": "Guaraní paraguayo",
    "USD": "Dólar americano",
    "EUR": "Euro",
    "BRL": "Real brasileño",
    "ARS": "Peso argentino"
}

# Moneda por defecto
MONEDA_DEFAULT = "PYG"

# Tipos de cambio
TIPOS_CAMBIO = {
    "1": "Tipo de cambio fijo",
    "2": "Tipo de cambio variable"
}


# ===================================================================
# TASAS DE IVA PARAGUAY
# ===================================================================

# Tasas válidas de IVA en Paraguay
TASAS_IVA_VALIDAS = [
    Decimal("0"),     # Exento
    Decimal("5"),     # IVA 5%
    Decimal("10")     # IVA 10%
]

# Tasas como strings para validación
TASAS_IVA_STR = ["0", "5", "10"]

# Códigos de afectación IVA
AFECTACION_IVA = {
    "1": "Gravado IVA",
    "2": "Exonerado",
    "3": "Exento"
}


# ===================================================================
# DEPARTAMENTOS DE PARAGUAY
# ===================================================================

DEPARTAMENTOS_PARAGUAY = {
    "1": "Concepción",
    "2": "San Pedro",
    "3": "Cordillera",
    "4": "Guairá",
    "5": "Caaguazú",
    "6": "Caazapá",
    "7": "Itapúa",
    "8": "Misiones",
    "9": "Paraguarí",
    "10": "Alto Paraná",
    "11": "Central",
    "12": "Ñeembucú",
    "13": "Amambay",
    "14": "Canindeyú",
    "15": "Presidente Hayes",
    "16": "Alto Paraguay",
    "17": "Boquerón"
}

# Códigos válidos de departamento
CODIGOS_DEPARTAMENTO_VALIDOS = list(DEPARTAMENTOS_PARAGUAY.keys())

# Principales distritos (muestra - la tabla completa debe obtenerse del SET)
DISTRITOS_PRINCIPALES = {
    "11": {  # Central
        "1": "Asunción",
        "2": "Fernando de la Mora",
        "3": "Lambaré",
        "4": "Luque",
        "5": "Mariano Roque Alonso",
        "6": "San Lorenzo",
        "7": "Villa Elisa"
    },
    "10": {  # Alto Paraná
        "1": "Ciudad del Este",
        "2": "Presidente Franco",
        "3": "Hernandarias"
    }
}


# ===================================================================
# UNIDADES DE MEDIDA
# ===================================================================

# Principales unidades de medida utilizadas
UNIDADES_MEDIDA = {
    "1": "Unidad",
    "2": "Kilogramo",
    "3": "Metro",
    "4": "Metro cuadrado",
    "5": "Metro cúbico",
    "6": "Litro",
    "7": "Docena",
    "8": "Paquete",
    "9": "Caja",
    "10": "Tonelada",
    "11": "Hora",
    "12": "Servicio",
    "13": "Mes",
    "14": "Año"
}


# ===================================================================
# PATRONES DE VALIDACIÓN
# ===================================================================

# Patrones regex para validación
VALIDATION_PATTERNS = {
    # Documentos y códigos
    'cdc': re.compile(r'^\d{44}$'),
    'ruc_base': re.compile(r'^\d{8}$'),
    'ruc_completo': re.compile(r'^\d{8}-?\d{1}$'),
    'timbrado': re.compile(r'^\d{8}$'),
    'establecimiento': re.compile(r'^\d{3}$'),
    'punto_expedicion': re.compile(r'^\d{3}$'),
    'numero_documento': re.compile(r'^\d{1,7}$'),

    # Fechas
    'fecha_sifen': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
    'datetime_sifen': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'),
    'fecha_cdc': re.compile(r'^\d{8}$'),

    # Identificaciones
    'codigo_seguridad': re.compile(r'^\d{9}$'),
    'dv': re.compile(r'^\d{1}$'),

    # Contacto
    'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
    'telefono': re.compile(r'^\+?[\d\s\-\(\)]{7,15}$'),

    # Geográficos
    'codigo_departamento': re.compile(r'^[1-9]\d{0,1}$'),
    'codigo_distrito': re.compile(r'^\d{1,3}$'),
    'codigo_ciudad': re.compile(r'^\d{1,3}$'),
}

# Longitudes máximas de campos de texto
LONGITUDES_CAMPO = {
    'razon_social': 60,
    'nombre_fantasia': 60,
    'direccion': 200,
    'descripcion_producto': 120,
    'observaciones': 500,
    'motivo_emision': 500,
    'numero_casa': 20,
    'complemento_direccion': 200,
    'telefono': 15,
    'email': 80,
    'actividad_economica': 200
}


# ===================================================================
# LÍMITES NUMÉRICOS
# ===================================================================

# Límites para campos numéricos
LIMITES_NUMERICOS = {
    'cantidad_item': {
        'min': Decimal('0.0001'),
        'max': Decimal('999999999.9999'),
        'decimales': 4
    },
    'precio_unitario': {
        'min': Decimal('0.00'),
        'max': Decimal('999999999999.99'),
        'decimales': 2
    },
    'monto_total': {
        'min': Decimal('0.00'),
        'max': Decimal('999999999999.99'),
        'decimales': 2
    },
    'tipo_cambio': {
        'min': Decimal('0.01'),
        'max': Decimal('99999.99999'),
        'decimales': 5
    }
}

# Límites específicos para Paraguay
LIMITE_MONTO_SIN_TIMBRADO = Decimal('1000000')  # 1 millón de guaraníes


# ===================================================================
# ESTADOS DE DOCUMENTOS
# ===================================================================

class EstadoDocumento(Enum):
    """Estados posibles de documentos electrónicos."""
    BORRADOR = ("draft", "Borrador")
    FIRMADO = ("signed", "Firmado digitalmente")
    ENVIADO = ("sent", "Enviado a SIFEN")
    APROBADO = ("approved", "Aprobado por SIFEN")
    RECHAZADO = ("rejected", "Rechazado por SIFEN")
    CANCELADO = ("cancelled", "Cancelado")

    def __init__(self, codigo: str, descripcion: str):
        self.codigo = codigo
        self.descripcion = descripcion


# ===================================================================
# CONFIGURACIÓN DE LOTES
# ===================================================================

# Límites para procesamiento por lotes
LIMITES_LOTE = {
    'max_documentos_lote': 50,
    'max_size_mb': 10,
    'timeout_procesamiento': 300,  # 5 minutos
    'max_reintentos': 3
}


# ===================================================================
# CONDICIONES DE CRÉDITO
# ===================================================================

CONDICIONES_CREDITO = {
    "1": "Contado",
    "2": "Crédito"
}

TIPOS_PLAZO = {
    "1": "Días",
    "2": "Meses"
}


# ===================================================================
# INDICADORES DE PRESENCIA
# ===================================================================

INDICADORES_PRESENCIA = {
    "1": "Operación presencial",
    "2": "Operación electrónica",
    "3": "Operación telefónica",
    "4": "Operación por correspondencia",
    "9": "Otros"
}


# ===================================================================
# NATURALEZA DE TRANSACCIÓN
# ===================================================================

NATURALEZA_TRANSACCION = {
    "1": "Venta de mercaderías",
    "2": "Prestación de servicios",
    "3": "Mixto (mercaderías y servicios)",
    "4": "Venta de activo fijo",
    "5": "Venta de divisa",
    "6": "Compra de divisa",
    "7": "Promoción o entrega gratuita",
    "8": "Consignación",
    "9": "Otros"
}


# ===================================================================
# TIPOS DE OPERACIÓN
# ===================================================================

TIPOS_OPERACION = {
    "1": "B2B - Negocio a Negocio",
    "2": "B2C - Negocio a Consumidor",
    "3": "B2G - Negocio a Gobierno",
    "4": "B2F - Negocio a Extranjero",
    "5": "G2B - Gobierno a Negocio",
    "6": "G2C - Gobierno a Consumidor",
    "7": "G2G - Gobierno a Gobierno"
}


# ===================================================================
# TIPOS DE TRANSPORTE
# ===================================================================

TIPOS_TRANSPORTE = {
    "1": "Terrestre",
    "2": "Fluvial",
    "3": "Aéreo",
    "4": "Multimodal"
}

MODALIDADES_TRANSPORTE = {
    "1": "Por cuenta propia",
    "2": "Por cuenta de terceros",
    "3": "Sin transporte"
}

RESPONSABLES_TRANSPORTE = {
    "1": "Emisor",
    "2": "Receptor",
    "3": "Tercero"
}


# ===================================================================
# FUNCIONES DE UTILIDAD
# ===================================================================

def get_descripcion_documento(codigo: str) -> Optional[str]:
    """
    Obtiene la descripción de un tipo de documento.

    Args:
        codigo: Código del tipo de documento

    Returns:
        str: Descripción del documento o None si no existe
    """
    return TIPOS_DOCUMENTO.get(codigo)


def get_descripcion_departamento(codigo: str) -> Optional[str]:
    """
    Obtiene la descripción de un departamento.

    Args:
        codigo: Código del departamento

    Returns:
        str: Nombre del departamento o None si no existe
    """
    return DEPARTAMENTOS_PARAGUAY.get(codigo)


def get_descripcion_moneda(codigo: str) -> Optional[str]:
    """
    Obtiene la descripción de una moneda.

    Args:
        codigo: Código ISO de la moneda

    Returns:
        str: Descripción de la moneda o None si no existe
    """
    return MONEDAS_SIFEN.get(codigo)


def is_valid_tipo_documento(codigo: str) -> bool:
    """
    Verifica si un código de tipo de documento es válido.

    Args:
        codigo: Código a verificar

    Returns:
        bool: True si es válido
    """
    return codigo in TIPOS_DOCUMENTO


def is_valid_departamento(codigo: str) -> bool:
    """
    Verifica si un código de departamento es válido.

    Args:
        codigo: Código a verificar

    Returns:
        bool: True si es válido
    """
    return codigo in DEPARTAMENTOS_PARAGUAY


def is_valid_moneda(codigo: str) -> bool:
    """
    Verifica si un código de moneda es válido.

    Args:
        codigo: Código a verificar

    Returns:
        bool: True si es válido
    """
    return codigo in MONEDAS_SIFEN


def is_valid_tasa_iva(tasa: str) -> bool:
    """
    Verifica si una tasa de IVA es válida en Paraguay.

    Args:
        tasa: Tasa a verificar

    Returns:
        bool: True si es válida
    """
    return tasa in TASAS_IVA_STR


def get_all_document_types() -> Dict[str, str]:
    """
    Obtiene todos los tipos de documentos disponibles.

    Returns:
        Dict: Mapeo código -> descripción
    """
    return TIPOS_DOCUMENTO.copy()


def get_all_departments() -> Dict[str, str]:
    """
    Obtiene todos los departamentos de Paraguay.

    Returns:
        Dict: Mapeo código -> nombre
    """
    return DEPARTAMENTOS_PARAGUAY.copy()


def get_all_currencies() -> Dict[str, str]:
    """
    Obtiene todas las monedas soportadas.

    Returns:
        Dict: Mapeo código -> descripción
    """
    return MONEDAS_SIFEN.copy()


def get_validation_pattern(field_name: str) -> Optional[re.Pattern]:
    """
    Obtiene el patrón de validación para un campo.

    Args:
        field_name: Nombre del campo

    Returns:
        Pattern: Patrón regex o None si no existe
    """
    return VALIDATION_PATTERNS.get(field_name)


def get_field_max_length(field_name: str) -> Optional[int]:
    """
    Obtiene la longitud máxima para un campo de texto.

    Args:
        field_name: Nombre del campo

    Returns:
        int: Longitud máxima o None si no existe
    """
    return LONGITUDES_CAMPO.get(field_name)


def get_numeric_limits(field_name: str) -> Optional[Dict]:
    """
    Obtiene los límites numéricos para un campo.

    Args:
        field_name: Nombre del campo

    Returns:
        Dict: Límites (min, max, decimales) o None si no existe
    """
    return LIMITES_NUMERICOS.get(field_name)


# ===================================================================
# INFORMACIÓN DEL MÓDULO
# ===================================================================

__module_info__ = {
    'name': 'constants',
    'version': '1.0.0',
    'description': 'Constantes y tablas de referencia SIFEN v150 Paraguay',
    'sifen_version': SIFEN_VERSION,
    'total_constants': len([
        k for k in globals().keys()
        if k.isupper() and not k.startswith('_')
    ]),
    'categories': [
        'Tipos de documentos',
        'Códigos de respuesta',
        'Referencias geográficas',
        'Monedas y tipos de cambio',
        'Patrones de validación',
        'Límites numéricos',
        'Estados y configuraciones'
    ]
}


# ===================================================================
# EXPORTS PÚBLICOS
# ===================================================================

__all__ = [
    # Información del sistema
    'SIFEN_VERSION',
    'SIFEN_NAMESPACE',
    'SIFEN_URLS',
    'PAIS_INFO',

    # Enumeraciones principales
    'TipoDocumentoElectronico',
    'CodigoRespuestaSifen',
    'TipoEmision',
    'TipoContribuyente',
    'MonedaOperacion',
    'EstadoDocumento',

    # Diccionarios de códigos
    'TIPOS_DOCUMENTO',
    'TIPOS_EMISION',
    'TIPOS_CONTRIBUYENTE',
    'TIPOS_REGIMEN',
    'MONEDAS_SIFEN',
    'DEPARTAMENTOS_PARAGUAY',
    'UNIDADES_MEDIDA',

    # Listas de validación
    'CODIGOS_DOCUMENTO_VALIDOS',
    'CODIGOS_DEPARTAMENTO_VALIDOS',
    'TASAS_IVA_VALIDAS',
    'TASAS_IVA_STR',

    # Agrupaciones de códigos
    'CODIGOS_EXITOSOS',
    'CODIGOS_ERROR_XML',
    'CODIGOS_ERROR_FIRMA',
    'CODIGOS_ERROR_CDC',
    'CODIGOS_ERROR_RUC',

    # Patrones y límites
    'VALIDATION_PATTERNS',
    'LONGITUDES_CAMPO',
    'LIMITES_NUMERICOS',
    'LIMITES_LOTE',

    # Constantes específicas
    'MONEDA_DEFAULT',
    'LIMITE_MONTO_SIN_TIMBRADO',

    # Funciones de utilidad
    'get_descripcion_documento',
    'get_descripcion_departamento',
    'get_descripcion_moneda',
    'is_valid_tipo_documento',
    'is_valid_departamento',
    'is_valid_moneda',
    'is_valid_tasa_iva',
    'get_all_document_types',
    'get_all_departments',
    'get_all_currencies',
    'get_validation_pattern',
    'get_field_max_length',
    'get_numeric_limits',

    # Información del módulo
    '__module_info__',
]
