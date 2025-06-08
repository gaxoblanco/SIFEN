"""
Modelos para el cliente SIFEN

Define todas las estructuras de datos necesarias para:
- Requests y responses de SIFEN
- Configuración del cliente  
- Manejo de errores
- Enums de códigos oficiales

Basado en Manual Técnico SIFEN v150
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class SifenEnvironment(str, Enum):
    """Ambientes SIFEN disponibles"""
    TEST = "test"
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    STAGING = "staging"


class DocumentType(str, Enum):
    """Tipos de documentos electrónicos SIFEN"""
    FACTURA = "1"                    # Factura Electrónica
    AUTOFACTURA = "4"               # Autofactura Electrónica
    NOTA_CREDITO = "5"              # Nota de Crédito Electrónica
    NOTA_DEBITO = "6"               # Nota de Débito Electrónica
    NOTA_REMISION = "7"             # Nota de Remisión Electrónica


class SifenResponseCode(str, Enum):
    """Códigos de respuesta oficiales SIFEN"""
    # Respuestas exitosas
    APROBADO = "0260"                           # Aprobado
    APROBADO_OBSERVACIONES = "1005"             # Aprobado con observaciones

    # Errores de documento
    CDC_NO_CORRESPONDE = "1000"                 # CDC no corresponde con XML
    CDC_DUPLICADO = "1001"                      # CDC duplicado
    TIMBRADO_INVALIDO = "1101"                  # Número timbrado inválido

    # Errores de contribuyente
    RUC_INEXISTENTE = "1250"                    # RUC emisor inexistente
    RUC_NO_AUTORIZADO = "1251"                  # RUC no autorizado para DE

    # Errores de firma
    FIRMA_INVALIDA = "0141"                     # Firma digital inválida
    CERTIFICADO_INVALIDO = "0142"               # Certificado inválido

    # Errores de servidor
    ERROR_INTERNO = "5000"                      # Error interno del servidor
    SERVICIO_NO_DISPONIBLE = "5001"            # Servicio no disponible


class TipoCambio(str, Enum):
    """Tipos de cambio según SIFEN"""
    FIJO = "1"          # Tipo de cambio fijo
    VARIABLE = "2"      # Tipo de cambio variable


class TipoEmision(str, Enum):
    """Tipos de emisión de documentos"""
    NORMAL = "1"        # Emisión normal
    CONTINGENCIA = "2"  # Emisión de contingencia


class MonedaOperacion(str, Enum):
    """Monedas soportadas por SIFEN"""
    PYG = "PYG"         # Guaraní paraguayo
    USD = "USD"         # Dólar americano
    EUR = "EUR"         # Euro
    BRL = "BRL"         # Real brasileño


# =============================================
# MODELOS DE CONFIGURACIÓN
# =============================================

class RetryConfig(BaseModel):
    """Configuración para reintentos"""
    max_retries: int = Field(
        3, description="Número máximo de reintentos", ge=0, le=10)
    initial_delay: float = Field(
        1.0, description="Delay inicial en segundos", gt=0)
    backoff_factor: float = Field(
        2.0, description="Factor de incremento del delay", ge=1.0)
    max_delay: float = Field(
        60.0, description="Delay máximo en segundos", gt=0)


class SifenClientConfig(BaseModel):
    """Configuración completa del cliente SIFEN"""
    # Ambiente y URLs
    environment: SifenEnvironment = Field(
        SifenEnvironment.TEST, description="Ambiente SIFEN")
    base_url: str = Field(..., description="URL base del servicio SIFEN")

    # Endpoints específicos
    wsdl_path: str = Field("/de/ws/sync/recibe.wsdl",
                           description="Path del WSDL individual")
    batch_wsdl_path: str = Field(
        "/de/ws/async/recibe-lote.wsdl", description="Path del WSDL de lotes")
    query_wsdl_path: str = Field(
        "/de/ws/consultas/consulta.wsdl", description="Path del WSDL de consultas")

    # Timeouts
    default_timeout: float = Field(
        30.0, description="Timeout por defecto", gt=0)
    connect_timeout: float = Field(
        10.0, description="Timeout de conexión", gt=0)
    read_timeout: float = Field(30.0, description="Timeout de lectura", gt=0)

    # Reintentos - FIX: Usar lambda para crear nueva instancia
    retry_config: RetryConfig = Field(
        default_factory=lambda: RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            backoff_factor=2.0,
            max_delay=60.0
        ), description="Configuración de reintentos")

    # SSL/TLS
    verify_ssl: bool = Field(True, description="Verificar certificados SSL")
    cert_file: Optional[str] = Field(
        None, description="Archivo de certificado cliente")
    key_file: Optional[str] = Field(
        None, description="Archivo de clave privada")

    # HTTP
    user_agent: str = Field("SIFEN-Client-Python/1.0",
                            description="User agent para requests")
    pool_connections: int = Field(10, description="Conexiones en pool", ge=1)
    pool_maxsize: int = Field(20, description="Tamaño máximo del pool", ge=1)

    # Logging
    enable_request_logging: bool = Field(
        True, description="Habilitar logging de requests")
    enable_response_logging: bool = Field(
        False, description="Habilitar logging de responses")
    log_level: str = Field("INFO", description="Nivel de logging")

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validar que la URL base sea válida"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("base_url debe comenzar con http:// o https://")
        return v.rstrip('/')


# =============================================
# MODELOS DE REQUEST
# =============================================

class SifenRequest(BaseModel):
    """Modelo base para requests a SIFEN"""
    xml_content: str = Field(...,
                             description="Contenido XML del documento", min_length=1)
    certificate_data: bytes = Field(...,
                                    description="Datos del certificado en formato bytes")
    certificate_password: Optional[str] = Field(
        None, description="Password del certificado")
    environment: SifenEnvironment = Field(
        SifenEnvironment.TEST, description="Ambiente SIFEN")
    timeout: float = Field(
        30.0, description="Timeout específico para este request", gt=0)

    # Metadatos opcionales
    request_id: Optional[str] = Field(None, description="ID único del request")
    user_id: Optional[str] = Field(
        None, description="ID del usuario que envía")

    @field_validator('xml_content')
    @classmethod
    def validate_xml_content(cls, v: str) -> str:
        """Validación básica del contenido XML"""
        v = v.strip()
        if not v:
            raise ValueError("XML content no puede estar vacío")
        if not v.startswith('<?xml'):
            raise ValueError("XML content debe comenzar con declaración XML")
        return v


class BatchSifenRequest(BaseModel):
    """Modelo para envío de lotes de documentos"""
    xml_documents: List[str] = Field(
        ..., description="Lista de documentos XML", min_length=1, max_length=50)
    certificate_data: bytes = Field(..., description="Datos del certificado")
    certificate_password: Optional[str] = Field(
        None, description="Password del certificado")
    environment: SifenEnvironment = Field(
        SifenEnvironment.TEST, description="Ambiente SIFEN")
    timeout: float = Field(
        60.0, description="Timeout para procesamiento de lote", gt=0)

    # Configuración de lote
    batch_name: Optional[str] = Field(
        None, description="Nombre identificador del lote")
    priority: int = Field(
        5, description="Prioridad del lote (1-10)", ge=1, le=10)

    @field_validator('xml_documents')
    @classmethod
    def validate_xml_documents(cls, v: List[str]) -> List[str]:
        """Validar que todos los documentos sean XML válidos básicamente"""
        if len(v) > 50:
            raise ValueError("Un lote no puede contener más de 50 documentos")

        for i, xml_doc in enumerate(v):
            if not xml_doc.strip():
                raise ValueError(f"Documento {i+1} está vacío")
            if not xml_doc.strip().startswith('<?xml'):
                raise ValueError(f"Documento {i+1} no es XML válido")

        return v


class QueryDocumentRequest(BaseModel):
    """Modelo para consulta de documentos por CDC"""
    cdc: str = Field(..., description="Código de Control del Documento",
                     min_length=44, max_length=44)
    environment: SifenEnvironment = Field(
        SifenEnvironment.TEST, description="Ambiente SIFEN")
    timeout: float = Field(15.0, description="Timeout para consulta", gt=0)

    # Filtros opcionales
    include_xml: bool = Field(
        False, description="Incluir XML original en respuesta")
    include_events: bool = Field(
        False, description="Incluir eventos del documento")

    @field_validator('cdc')
    @classmethod
    def validate_cdc(cls, v: str) -> str:
        """Validar formato de CDC"""
        if len(v) != 44:
            raise ValueError("CDC debe tener exactamente 44 caracteres")
        if not v.isdigit():
            raise ValueError("CDC debe contener solo dígitos")
        return v


class QueryRucRequest(BaseModel):
    """Modelo para consulta de información de RUC"""
    ruc: str = Field(..., description="RUC a consultar",
                     min_length=8, max_length=12)
    environment: SifenEnvironment = Field(
        SifenEnvironment.TEST, description="Ambiente SIFEN")
    timeout: float = Field(10.0, description="Timeout para consulta", gt=0)

    @field_validator('ruc')
    @classmethod
    def validate_ruc(cls, v: str) -> str:
        """Validar formato de RUC"""
        # Remover guiones y espacios
        clean_ruc = v.replace('-', '').replace(' ', '')

        if not clean_ruc.isdigit():
            raise ValueError("RUC debe contener solo números")
        if len(clean_ruc) < 8 or len(clean_ruc) > 11:
            raise ValueError("RUC debe tener entre 8 y 11 dígitos")

        return clean_ruc


# =============================================
# MODELOS DE RESPONSE
# =============================================

class SifenResponse(BaseModel):
    """Modelo para respuestas de SIFEN"""
    # Resultado de la operación
    success: bool = Field(...,
                          description="Indica si la operación fue exitosa")
    response_code: str = Field(..., description="Código de respuesta SIFEN")
    message: str = Field(..., description="Mensaje de respuesta")

    # Datos del documento procesado
    protocol_number: Optional[str] = Field(
        None, description="Número de protocolo de autorización")
    cdc: Optional[str] = Field(
        None, description="Código de Control del Documento")
    document_status: Optional[str] = Field(
        None, description="Estado del documento")

    # Información de procesamiento
    processing_time: float = Field(...,
                                   description="Tiempo de procesamiento en segundos")
    server_time: Optional[datetime] = Field(
        None, description="Timestamp del servidor SIFEN")

    # Datos técnicos
    raw_response: str = Field(..., description="Respuesta cruda del servidor")
    request_id: Optional[str] = Field(
        None, description="ID del request original")

    # Errores y observaciones
    errors: List[str] = Field(default_factory=list,
                              description="Lista de errores")
    warnings: List[str] = Field(
        default_factory=list, description="Lista de advertencias")
    observations: List[str] = Field(
        default_factory=list, description="Lista de observaciones")

    @property
    def is_approved(self) -> bool:
        """Indica si el documento fue aprobado"""
        return self.response_code in [SifenResponseCode.APROBADO, SifenResponseCode.APROBADO_OBSERVACIONES]

    @property
    def has_errors(self) -> bool:
        """Indica si hay errores"""
        return len(self.errors) > 0 or not self.success

    @property
    def has_warnings(self) -> bool:
        """Indica si hay advertencias"""
        return len(self.warnings) > 0

    def get_error_summary(self) -> str:
        """Obtiene un resumen de errores"""
        if not self.has_errors:
            return "Sin errores"

        error_summary = f"Código: {self.response_code}, Mensaje: {self.message}"
        if self.errors:
            error_summary += f", Errores: {'; '.join(self.errors)}"

        return error_summary


class BatchSifenResponse(BaseModel):
    """Modelo para respuestas de lotes SIFEN"""
    # Resultado general del lote
    success: bool = Field(..., description="Indica si el lote fue procesado")
    batch_id: Optional[str] = Field(
        None, description="ID del lote asignado por SIFEN")
    batch_status: Optional[str] = Field(None, description="Estado del lote")

    # Estadísticas del lote
    total_documents: int = Field(...,
                                 description="Total de documentos en el lote")
    processed_documents: int = Field(...,
                                     description="Documentos procesados exitosamente")
    failed_documents: int = Field(..., description="Documentos que fallaron")
    pending_documents: int = Field(
        0, description="Documentos pendientes de procesar")

    # Resultados individuales
    document_results: List[SifenResponse] = Field(
        default_factory=list, description="Resultados por documento")

    # Información de procesamiento
    processing_time: float = Field(...,
                                   description="Tiempo total de procesamiento")
    start_time: Optional[datetime] = Field(
        None, description="Inicio de procesamiento")
    end_time: Optional[datetime] = Field(
        None, description="Fin de procesamiento")

    # Errores generales del lote
    errors: List[str] = Field(default_factory=list,
                              description="Errores generales del lote")

    @property
    def success_rate(self) -> float:
        """Porcentaje de documentos procesados exitosamente"""
        if self.total_documents == 0:
            return 0.0
        return (self.processed_documents / self.total_documents) * 100

    @property
    def is_complete(self) -> bool:
        """Indica si el lote fue procesado completamente"""
        return self.pending_documents == 0

    def get_failed_documents(self) -> List[SifenResponse]:
        """Obtiene lista de documentos que fallaron"""
        return [doc for doc in self.document_results if not doc.success]


class QueryDocumentResponse(BaseModel):
    """Modelo para respuesta de consulta de documentos"""
    # Resultado de la consulta
    success: bool = Field(..., description="Indica si la consulta fue exitosa")
    cdc: str = Field(..., description="CDC consultado")

    # Información del documento
    document_exists: bool = Field(
        False, description="Indica si el documento existe")
    document_status: Optional[str] = Field(
        None, description="Estado actual del documento")
    authorization_protocol: Optional[str] = Field(
        None, description="Protocolo de autorización")

    # Datos del documento
    document_type: Optional[str] = Field(None, description="Tipo de documento")
    issue_date: Optional[datetime] = Field(
        None, description="Fecha de emisión")
    issuer_ruc: Optional[str] = Field(None, description="RUC del emisor")
    issuer_name: Optional[str] = Field(None, description="Nombre del emisor")
    receiver_ruc: Optional[str] = Field(None, description="RUC del receptor")
    receiver_name: Optional[str] = Field(
        None, description="Nombre del receptor")

    # Montos
    total_amount: Optional[float] = Field(
        None, description="Monto total del documento")
    tax_amount: Optional[float] = Field(None, description="Monto de impuestos")
    currency: Optional[str] = Field(None, description="Moneda del documento")

    # Contenido adicional (opcional)
    xml_content: Optional[str] = Field(
        None, description="XML original del documento")
    events: List[Dict[str, Any]] = Field(
        default_factory=list, description="Eventos del documento")

    # Errores
    errors: List[str] = Field(default_factory=list,
                              description="Errores en la consulta")


class QueryRucResponse(BaseModel):
    """Modelo para respuesta de consulta de RUC"""
    success: bool = Field(..., description="Indica si la consulta fue exitosa")
    ruc: str = Field(..., description="RUC consultado")

    # Información del contribuyente
    exists: bool = Field(False, description="Indica si el RUC existe")
    business_name: Optional[str] = Field(None, description="Razón social")
    trade_name: Optional[str] = Field(None, description="Nombre comercial")
    status: Optional[str] = Field(None, description="Estado del RUC")

    # Autorización para documentos electrónicos
    authorized_for_electronic_documents: bool = Field(
        False, description="Autorizado para DE")
    authorization_date: Optional[datetime] = Field(
        None, description="Fecha de autorización")

    # Errores
    errors: List[str] = Field(default_factory=list,
                              description="Errores en la consulta")


# =============================================
# MODELOS DE EVENTOS
# =============================================

class DocumentEvent(BaseModel):
    """Modelo para eventos de documentos"""
    event_type: str = Field(..., description="Tipo de evento")
    event_date: datetime = Field(..., description="Fecha del evento")
    description: str = Field(..., description="Descripción del evento")
    user_id: Optional[str] = Field(
        None, description="Usuario que generó el evento")
    additional_data: Dict[str, Any] = Field(
        default_factory=dict, description="Datos adicionales")


# =============================================
# EXCEPCIONES PERSONALIZADAS
# =============================================

class SifenError(Exception):
    """Excepción base para errores SIFEN"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        response: Optional[SifenResponse] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.response = response
        super().__init__(self.message)

    def __str__(self) -> str:
        result = self.message
        if self.error_code:
            result = f"[{self.error_code}] {result}"
        return result


class SifenConnectionError(SifenError):
    """Error de conexión con SIFEN"""
    pass


class SifenTimeoutError(SifenError):
    """Error de timeout en SIFEN"""
    pass


class SifenValidationError(SifenError):
    """Error de validación de documentos"""
    pass


class SifenAuthenticationError(SifenError):
    """Error de autenticación con SIFEN"""
    pass


class SifenConfigurationError(SifenError):
    """Error de configuración del cliente"""
    pass


class SifenCertificateError(SifenError):
    """Error relacionado con certificados digitales"""
    pass


# =============================================
# MODELOS DE CERTIFICADOS
# =============================================

class CertificateInfo(BaseModel):
    """Información de certificado digital"""
    serial_number: str = Field(...,
                               description="Número de serie del certificado")
    subject: str = Field(..., description="Subject del certificado")
    issuer: str = Field(..., description="Emisor del certificado")
    valid_from: datetime = Field(..., description="Válido desde")
    valid_to: datetime = Field(..., description="Válido hasta")
    key_usage: List[str] = Field(
        default_factory=list, description="Uso de la clave")

    @property
    def is_valid(self) -> bool:
        """Indica si el certificado está vigente"""
        now = datetime.now()
        return self.valid_from <= now <= self.valid_to

    @property
    def days_until_expiry(self) -> int:
        """Días hasta que expire el certificado"""
        delta = self.valid_to - datetime.now()
        return max(0, delta.days)


# =============================================
# CONSTANTES Y HELPERS
# =============================================

# Códigos de respuesta comunes para validación
SUCCESS_CODES = [SifenResponseCode.APROBADO,
                 SifenResponseCode.APROBADO_OBSERVACIONES]
ERROR_CODES = [
    SifenResponseCode.CDC_NO_CORRESPONDE,
    SifenResponseCode.CDC_DUPLICADO,
    SifenResponseCode.TIMBRADO_INVALIDO,
    SifenResponseCode.RUC_INEXISTENTE,
    SifenResponseCode.FIRMA_INVALIDA
]

# Timeouts por defecto según tipo de operación
DEFAULT_TIMEOUTS = {
    'send_document': 30.0,
    'send_batch': 120.0,
    'query_document': 15.0,
    'query_ruc': 10.0
}

# Límites de SIFEN
SIFEN_LIMITS = {
    'max_batch_size': 50,
    'max_xml_size_mb': 10,
    'max_concurrent_requests': 10,
    'max_retry_attempts': 5
}


def is_success_response(response_code: str) -> bool:
    """Verifica si un código de respuesta indica éxito"""
    return response_code in [code.value for code in SUCCESS_CODES]


def is_error_response(response_code: str) -> bool:
    """Verifica si un código de respuesta indica error"""
    return response_code in [code.value for code in ERROR_CODES]


def get_error_description(error_code: str) -> str:
    """Obtiene descripción de un código de error"""
    descriptions = {
        SifenResponseCode.CDC_NO_CORRESPONDE: "El CDC no corresponde con el contenido del XML",
        SifenResponseCode.CDC_DUPLICADO: "El CDC ya fue enviado anteriormente",
        SifenResponseCode.TIMBRADO_INVALIDO: "El número de timbrado no es válido",
        SifenResponseCode.RUC_INEXISTENTE: "El RUC del emisor no existe en la base de datos",
        SifenResponseCode.FIRMA_INVALIDA: "La firma digital no es válida",
        SifenResponseCode.CERTIFICADO_INVALIDO: "El certificado digital no es válido",
        SifenResponseCode.ERROR_INTERNO: "Error interno del servidor SIFEN"
    }

    return descriptions.get(SifenResponseCode(error_code), f"Error desconocido: {error_code}")
