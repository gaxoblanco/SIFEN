"""
Modelos Pydantic para el módulo SIFEN Client

Define las estructuras de datos para requests y responses de SIFEN,
con validación automática según las especificaciones del Manual Técnico v150.

Modelos principales:
- DocumentRequest: Datos para envío de documento individual
- BatchRequest: Datos para envío de lote (hasta 50 documentos)
- SifenResponse: Respuesta estándar de SIFEN
- DocumentStatus: Estados de documentos electrónicos
- QueryRequest: Consultas por CDC o RUC

Validaciones incluidas:
- Formato CDC (44 caracteres)
- RUC paraguayo (8-9 dígitos + DV)
- Códigos de estado SIFEN
- Timestamps según ISO 8601
- Límites de lote (máximo 50 documentos)

Basado en:
- Manual Técnico SIFEN v150
- Esquemas XSD oficiales
- Códigos de respuesta SET Paraguay
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import re
import structlog

# Logger para modelos
logger = structlog.get_logger(__name__)


# ========================================
# ENUMS Y CONSTANTES
# ========================================

class DocumentType(str, Enum):
    """
    Tipos de documentos electrónicos según SIFEN v150
    """
    FACTURA = "01"                  # Factura Electrónica (FE)
    AUTOFACTURA = "04"              # Autofactura Electrónica (AFE)
    NOTA_CREDITO = "05"             # Nota de Crédito Electrónica (NCE)
    NOTA_DEBITO = "06"              # Nota de Débito Electrónica (NDE)
    NOTA_REMISION = "07"            # Nota de Remisión Electrónica (NRE)


class DocumentStatus(str, Enum):
    """
    Estados de documentos electrónicos en SIFEN
    """
    # Estados durante procesamiento
    PENDIENTE = "PENDING"           # Documento recibido, en cola
    PROCESANDO = "PROCESSING"       # Siendo procesado por SIFEN

    # Estados finales exitosos
    APROBADO = "APPROVED"           # Código 0260 - Aprobado
    APROBADO_OBSERVACION = "APPROVED_WITH_OBSERVATIONS"  # Código 1005

    # Estados finales de error
    RECHAZADO = "REJECTED"          # Códigos 1000-4999
    ERROR_TECNICO = "TECHNICAL_ERROR"  # Errores 5000+

    # Estados especiales
    EXTEMPORANEO = "LATE"           # Enviado fuera de plazo (72h-720h)
    CANCELADO = "CANCELLED"         # Cancelado por evento
    ANULADO = "ANNULLED"           # Anulado por evento


class ResponseType(str, Enum):
    """
    Tipos de respuesta de SIFEN
    """
    INDIVIDUAL = "individual"       # Respuesta envío individual
    BATCH = "batch"                # Respuesta envío lote
    QUERY = "query"                # Respuesta consulta
    EVENT = "event"                # Respuesta evento


# ========================================
# MODELOS BASE
# ========================================

class SifenBaseModel(BaseModel):
    """
    Modelo base para todas las estructuras SIFEN

    Proporciona funcionalidad común como validación,
    serialización segura y metadatos.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,  # Era allow_population_by_field_name
    )

    def dict_safe(self, exclude_sensitive: bool = True) -> Dict[str, Any]:
        """
        Serializa el modelo ocultando datos sensibles

        Args:
            exclude_sensitive: Si ocultar datos sensibles

        Returns:
            Dict con datos seguros para logging
        """
        data = self.dict()

        if exclude_sensitive:
            # Campos que contienen información sensible
            sensitive_fields = [
                'xml_content', 'signature', 'certificate_serial',
                'private_key', 'password', 'token'
            ]

            for field in sensitive_fields:
                if field in data and data[field]:
                    if isinstance(data[field], str) and len(data[field]) > 10:
                        data[field] = f"{data[field][:5]}...{data[field][-5:]}"
                    else:
                        data[field] = "***"

        return data

# ========================================
# EXCEPCIONES ESPECÍFICAS DE SIFEN
# ========================================


class SifenError(Exception):
    """
    Excepción base para todos los errores del cliente SIFEN

    Proporciona información estructurada sobre errores específicos
    del procesamiento SIFEN para manejo diferenciado por tipo.
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        raw_response: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.raw_response = raw_response
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para logging"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'code': self.code,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class SifenConnectionError(SifenError):
    """
    Error de conectividad con servicios SIFEN

    Se lanza cuando hay problemas de red, DNS, o SSL
    que impiden la comunicación con los endpoints de SIFEN.
    """
    pass


class SifenTimeoutError(SifenError):
    """
    Error de timeout en operaciones SIFEN

    Se lanza cuando una operación excede los timeouts configurados,
    ya sea de conexión o de lectura de respuesta.
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class SifenValidationError(SifenError):
    """
    Error de validación de datos o estructura XML

    Se lanza cuando los datos enviados no cumplen con las
    validaciones locales antes del envío a SIFEN.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value


class SifenAuthenticationError(SifenError):
    """
    Error de autenticación con SIFEN

    Se lanza cuando hay problemas con certificados digitales,
    credenciales o autorización para acceder a los servicios.
    """

    def __init__(
        self,
        message: str,
        certificate_serial: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.certificate_serial = certificate_serial


class SifenServerError(SifenError):
    """
    Error interno del servidor SIFEN

    Se lanza cuando SIFEN retorna códigos de error 5XXX
    indicando problemas del lado del servidor.
    """
    pass


class SifenBusinessRuleError(SifenError):
    """
    Error de reglas de negocio SIFEN

    Se lanza cuando SIFEN rechaza el documento por no cumplir
    con reglas específicas de negocio (RUC inexistente, CDC duplicado, etc.)
    """

    def __init__(
        self,
        message: str,
        business_rule: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.business_rule = business_rule


class SifenRetryExhaustedError(SifenError):
    """
    Error cuando se agotan los reintentos configurados

    Se lanza cuando el sistema de reintentos ha agotado
    todos los intentos sin obtener una respuesta exitosa.
    """

    def __init__(
        self,
        message: str,
        attempt_count: int = 0,
        last_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.attempt_count = attempt_count
        self.last_error = last_error


class SifenParsingError(SifenError):
    """
    Error al parsear respuestas de SIFEN

    Se lanza cuando no se puede interpretar o parsear
    la respuesta XML recibida de SIFEN.
    """

    def __init__(
        self,
        message: str,
        xml_content: Optional[str] = None,
        parsing_stage: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.xml_content = xml_content
        self.parsing_stage = parsing_stage


# Mapeo de códigos SIFEN a excepciones específicas
SIFEN_CODE_TO_EXCEPTION = {
    # Errores de validación
    '1000': SifenValidationError,
    '1001': SifenBusinessRuleError,  # CDC duplicado
    '1101': SifenValidationError,    # Timbrado inválido
    '1250': SifenBusinessRuleError,  # RUC inexistente

    # Errores de autenticación
    '0141': SifenAuthenticationError,  # Firma digital inválida

    # Errores del servidor
    '5000': SifenServerError,
    '5001': SifenServerError,
    '5002': SifenServerError,
}


def create_sifen_exception(
    code: str,
    message: str,
    **kwargs
) -> SifenError:
    """
    Factory para crear excepción apropiada según código SIFEN

    Args:
        code: Código de error SIFEN
        message: Mensaje de error
        **kwargs: Parámetros adicionales

    Returns:
        Instancia de la excepción apropiada
    """
    exception_class = SIFEN_CODE_TO_EXCEPTION.get(code, SifenError)
    return exception_class(message, code=code, **kwargs)
# ========================================
# MODELOS DE REQUEST
# ========================================


class DocumentRequest(SifenBaseModel):
    """
    Request para envío de documento individual a SIFEN

    Contiene el XML firmado y metadatos necesarios para
    el envío a través del servicio sync de SIFEN.
    """

    # Contenido del documento
    xml_content: str = Field(
        ...,
        min_length=100,

        description="Contenido XML del documento firmado digitalmente"
    )

    # Metadatos del certificado
    certificate_serial: str = Field(
        ...,
        min_length=8,
        max_length=50,
        description="Número de serie del certificado usado para firmar"
    )

    # Información temporal
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp del request (ISO 8601)"
    )

    # Información opcional del documento
    document_type: Optional[DocumentType] = Field(
        None,
        description="Tipo de documento (extraído del XML si no se proporciona)"
    )

    cdc: Optional[str] = Field(
        None,
        min_length=44,
        max_length=44,
        description="CDC del documento (extraído del XML si no se proporciona)"
    )

    # Metadatos adicionales
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos adicionales del request"
    )

    @field_validator('xml_content')
    @classmethod
    def validate_xml_content(cls, v):
        """Valida que el contenido sea XML válido básicamente"""
        if not v.strip().startswith('<?xml') and not v.strip().startswith('<'):
            raise ValueError("xml_content debe ser contenido XML válido")

        # Verificar que contenga elementos obligatorios de SIFEN
        required_elements = [
            '<rDE', 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"']
        for element in required_elements:
            if element not in v:
                raise ValueError(
                    f"XML debe contener elemento obligatorio: {element}")

        return v

    @field_validator('cdc')
    @classmethod
    def validate_cdc_format(cls, v):
        """Valida formato CDC paraguayo (44 caracteres)"""
        if v is None:
            return v

        # CDC debe tener exactamente 44 caracteres numéricos
        if not re.match(r'^\d{44}$', v):
            raise ValueError("CDC debe tener exactamente 44 dígitos numéricos")

        return v


class BatchRequest(SifenBaseModel):
    """
    Request para envío de lote de documentos a SIFEN

    Permite enviar hasta 50 documentos en un solo request
    al servicio async de SIFEN.
    """

    # Lista de documentos (máximo 50)
    documents: List[DocumentRequest] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Lista de documentos a enviar (máximo 50)"
    )

    # Identificador único del lote
    batch_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Identificador único del lote"
    )

    # Metadatos del lote
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de creación del lote"
    )

    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Prioridad del lote (1=alta, 10=baja)"
    )

    # Configuración de procesamiento
    notify_on_completion: bool = Field(
        default=True,
        description="Notificar cuando se complete el procesamiento"
    )

    @field_validator('batch_id')
    @classmethod
    def validate_batch_id(cls, v):
        """Valida formato del ID de lote"""
        # Solo caracteres alfanuméricos, guiones y underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "batch_id solo puede contener letras, números, guiones y underscores")

        return v

    @model_validator(mode='before')
    @classmethod
    def validate_batch_consistency(cls, data: Any) -> Any:
        """Valida consistencia del lote completo"""
        if isinstance(data, dict):
            documents = data.get('documents', [])

            if not documents:
                return data

            # Verificar que no hay CDCs duplicados
            cdcs = []
            for doc in documents:
                if hasattr(doc, 'cdc'):
                    cdc = doc.cdc
                elif isinstance(doc, dict):
                    cdc = doc.get('cdc')
                else:
                    continue

                if cdc:
                    cdcs.append(cdc)

            if len(cdcs) != len(set(cdcs)):
                raise ValueError(
                    "El lote no puede contener documentos con CDCs duplicados")

            # Verificar que todos los certificados son del mismo emisor (opcional)
            # Esta validación se puede hacer más estricta según requerimientos

        return data


class QueryRequest(SifenBaseModel):
    """
    Request para consulta de documentos o información en SIFEN

    Permite consultar por CDC, RUC o rangos de fechas.
    """

    # Tipo de consulta
    query_type: Literal["cdc", "ruc", "date_range"] = Field(
        ...,
        description="Tipo de consulta a realizar"
    )

    # Parámetros de consulta
    cdc: Optional[str] = Field(
        None,
        min_length=44,
        max_length=44,
        description="CDC específico a consultar"
    )

    ruc: Optional[str] = Field(
        None,
        min_length=8,
        max_length=12,
        description="RUC a consultar (formato: 12345678-9)"
    )

    # Rango de fechas
    date_from: Optional[datetime] = Field(
        None,
        description="Fecha inicio para consulta de rango"
    )

    date_to: Optional[datetime] = Field(
        None,
        description="Fecha fin para consulta de rango"
    )

    # Filtros adicionales
    document_types: Optional[List[DocumentType]] = Field(
        None,
        description="Filtrar por tipos de documento específicos"
    )

    status_filter: Optional[List[DocumentStatus]] = Field(
        None,
        description="Filtrar por estados específicos"
    )

    # Paginación
    page: int = Field(
        default=1,
        ge=1,
        description="Número de página (para consultas con muchos resultados)"
    )

    page_size: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Tamaño de página (máximo 1000)"
    )

    @field_validator('ruc')
    @classmethod
    def validate_ruc_format(cls, v):
        """Valida formato RUC paraguayo"""
        if v is None:
            return v

        # RUC puede ser 8 o 9 dígitos, opcionalmente con guión y DV
        if not re.match(r'^\d{8,9}(-\d)?$', v):
            raise ValueError("RUC debe tener formato: 12345678 o 12345678-9")

        return v

    @model_validator(mode='before')
    @classmethod
    def validate_query_parameters(cls, data: Any) -> Any:
        """Valida que los parámetros de consulta sean consistentes"""
        if isinstance(data, dict):
            query_type = data.get('query_type')

            if query_type == 'cdc' and not data.get('cdc'):
                raise ValueError("query_type 'cdc' requiere parámetro 'cdc'")

            if query_type == 'ruc' and not data.get('ruc'):
                raise ValueError("query_type 'ruc' requiere parámetro 'ruc'")

            if query_type == 'date_range':
                if not data.get('date_from') or not data.get('date_to'):
                    raise ValueError(
                        "query_type 'date_range' requiere 'date_from' y 'date_to'")

                date_from = data.get('date_from')
                date_to = data.get('date_to')
                if date_from and date_to and date_from >= date_to:
                    raise ValueError("date_from debe ser anterior a date_to")

        return data


# ========================================
# MODELOS DE RESPONSE
# ========================================

class SifenResponse(SifenBaseModel):
    """
    Respuesta estándar de SIFEN para cualquier operación

    Estructura unificada que maneja respuestas exitosas,
    errores y estados intermedios.
    """

    # Estado de la respuesta
    success: bool = Field(
        ...,
        description="Indica si la operación fue exitosa"
    )

    # Código de respuesta SIFEN
    code: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Código de respuesta SIFEN (ej: 0260, 1000, etc.)"
    )

    # Mensaje descriptivo
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Mensaje descriptivo del resultado"
    )

    # Información del documento
    cdc: Optional[str] = Field(
        None,
        description="CDC del documento procesado"
    )

    protocol_number: Optional[str] = Field(
        None,
        description="Número de protocolo SIFEN para seguimiento"
    )

    # Estado del documento
    document_status: Optional[DocumentStatus] = Field(
        None,
        description="Estado actual del documento"
    )

    # Información temporal
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de la respuesta"
    )

    processing_time_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Tiempo de procesamiento en milisegundos"
    )

    # Errores y observaciones
    errors: List[str] = Field(
        default_factory=list,
        description="Lista de errores específicos"
    )

    observations: List[str] = Field(
        default_factory=list,
        description="Lista de observaciones (para código 1005)"
    )

    # Información adicional
    additional_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Datos adicionales específicos del tipo de respuesta"
    )

    # Metadatos de la respuesta
    response_type: ResponseType = Field(
        default=ResponseType.INDIVIDUAL,
        description="Tipo de respuesta SIFEN"
    )

    @field_validator('code')
    @classmethod
    def validate_sifen_code(cls, v):
        """Valida que el código sea un código SIFEN válido"""
        # Códigos SIFEN son numéricos de 3-4 dígitos
        if not re.match(r'^\d{3,4}$', v):
            raise ValueError("Código SIFEN debe ser numérico de 3-4 dígitos")

        return v

    @model_validator(mode='before')
    @classmethod
    def validate_success_consistency(cls, data: Any) -> Any:
        """Valida consistencia entre success y code"""
        if isinstance(data, dict):
            success = data.get('success')
            code = data.get('code')

            if code and success is not None:
                # Códigos 0260 y 1005 son exitosos
                code_is_success = code in ['0260', '1005']

                if success != code_is_success:
                    logger.warning(
                        "sifen_response_success_mismatch",
                        success=success,
                        code=code,
                        expected_success=code_is_success
                    )

        return data


class BatchResponse(SifenResponse):
    """
    Respuesta específica para operaciones de lote

    Extiende SifenResponse con información específica
    de procesamiento de lotes.
    """

    # Información del lote
    batch_id: str = Field(
        ...,
        description="ID del lote procesado"
    )

    total_documents: int = Field(
        ...,
        ge=0,
        description="Total de documentos en el lote"
    )

    processed_documents: int = Field(
        default=0,
        ge=0,
        description="Documentos procesados exitosamente"
    )

    failed_documents: int = Field(
        default=0,
        ge=0,
        description="Documentos que fallaron"
    )

    # Resultados por documento
    document_results: List[SifenResponse] = Field(
        default_factory=list,
        description="Resultados individuales por documento"
    )

    # Estado del lote
    batch_status: Literal["pending", "processing", "completed", "failed"] = Field(
        default="pending",
        description="Estado del procesamiento del lote"
    )

    @model_validator(mode='before')
    @classmethod
    def validate_batch_consistency(cls, value):
        """Valida consistencia de contadores del lote"""
        if isinstance(value, dict):
            total = value.get('total_documents', 0)
            processed = value.get('processed_documents', 0)
            failed = value.get('failed_documents', 0)
            results = value.get('document_results', [])

            # Verificar que los contadores sean consistentes
            if processed + failed > total:
                raise ValueError(
                    "processed + failed no puede ser mayor que total")

            # Verificar que el número de resultados sea consistente
            if len(results) > total:
                raise ValueError(
                    "Número de resultados no puede ser mayor que total")

        return value


class QueryResponse(SifenResponse):
    """
    Respuesta específica para consultas

    Contiene los resultados de consultas por CDC, RUC o rangos.
    """

    # Parámetros de la consulta original
    query_type: str = Field(
        ...,
        description="Tipo de consulta realizada"
    )

    # Resultados de la consulta
    documents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Lista de documentos encontrados"
    )

    total_found: int = Field(
        default=0,
        ge=0,
        description="Total de documentos encontrados"
    )

    # Información de paginación
    page: int = Field(
        default=1,
        ge=1,
        description="Página actual"
    )

    page_size: int = Field(
        default=50,
        ge=1,
        description="Tamaño de página"
    )

    total_pages: int = Field(
        default=1,
        ge=1,
        description="Total de páginas disponibles"
    )

    has_next_page: bool = Field(
        default=False,
        description="Indica si hay más páginas disponibles"
    )


# ========================================
# FUNCIONES HELPER
# ========================================

def create_document_request(
    xml_content: str,
    certificate_serial: str,
    **kwargs
) -> DocumentRequest:
    """
    Factory function para crear DocumentRequest con validación

    Args:
        xml_content: Contenido XML firmado
        certificate_serial: Serial del certificado
        **kwargs: Parámetros adicionales

    Returns:
        DocumentRequest validado
    """
    try:
        return DocumentRequest(
            xml_content=xml_content,
            certificate_serial=certificate_serial,
            **kwargs
        )
    except Exception as e:
        logger.error(
            "document_request_creation_failed",
            error=str(e),
            xml_length=len(xml_content) if xml_content else 0,
            certificate_serial=certificate_serial
        )
        raise


def create_batch_request(
    documents: List[DocumentRequest],
    batch_id: str,
    **kwargs
) -> BatchRequest:
    """
    Factory function para crear BatchRequest con validación

    Args:
        documents: Lista de documentos
        batch_id: ID único del lote
        **kwargs: Parámetros adicionales

    Returns:
        BatchRequest validado
    """
    try:
        return BatchRequest(
            documents=documents,
            batch_id=batch_id,
            **kwargs
        )
    except Exception as e:
        logger.error(
            "batch_request_creation_failed",
            error=str(e),
            documents_count=len(documents) if documents else 0,
            batch_id=batch_id
        )
        raise


def extract_cdc_from_xml(xml_content: str) -> Optional[str]:
    """
    Extrae el CDC del contenido XML

    Args:
        xml_content: Contenido XML del documento

    Returns:
        CDC extraído o None si no se encuentra
    """
    try:
        # Buscar CDC en el atributo Id del elemento DE
        import re
        match = re.search(r'<DE\s+[^>]*Id="([^"]+)"', xml_content)
        if match:
            cdc = match.group(1)
            # Validar que tenga 44 dígitos
            if re.match(r'^\d{44}$', cdc):
                return cdc

        return None
    except Exception:
        return None


def extract_document_type_from_xml(xml_content: str) -> Optional[DocumentType]:
    """
    Extrae el tipo de documento del contenido XML

    Args:
        xml_content: Contenido XML del documento

    Returns:
        DocumentType o None si no se puede determinar
    """
    try:
        import re
        # Buscar en el CDC (posiciones 9-10)
        cdc = extract_cdc_from_xml(xml_content)
        if cdc and len(cdc) >= 10:
            doc_type_code = cdc[9:11]

            # Mapear código a enum
            type_mapping = {
                "01": DocumentType.FACTURA,
                "04": DocumentType.AUTOFACTURA,
                "05": DocumentType.NOTA_CREDITO,
                "06": DocumentType.NOTA_DEBITO,
                "07": DocumentType.NOTA_REMISION
            }

            return type_mapping.get(doc_type_code)

        return None
    except Exception:
        return None


logger.info(
    "sifen_client_models_loaded",
    models=[
        "DocumentRequest",
        "BatchRequest",
        "QueryRequest",
        "SifenResponse",
        "BatchResponse",
        "QueryResponse"
    ],
    enums=[
        "DocumentType",
        "DocumentStatus",
        "ResponseType"
    ]
)
