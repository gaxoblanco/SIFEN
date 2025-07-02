# ===============================================
# ARCHIVO: backend/app/schemas/documento.py
# PROPÓSITO: DTOs base para documentos electrónicos SIFEN
# PRIORIDAD: 🟡 IMPORTANTE - Base para todos los documentos
# ===============================================

"""
Esquemas Pydantic base para documentos electrónicos SIFEN.

Este módulo define DTOs genéricos para:
- Documento base electrónico (padre de factura, notas, etc.)
- Estados y tracking de documentos
- Respuestas SIFEN genéricas
- Consultas y reportes de documentos

Usado por:
- schemas/factura.py (hereda DocumentoBaseDTO)
- Futuras notas de crédito/débito/remisión
- apis de consulta y reportes
- Integración con xml_generator, digital_sign, sifen_client

Arquitectura:
- DocumentoBaseDTO: Campos comunes a todos los documentos
- DocumentoEstadoDTO: Estado y tracking temporal
- DocumentoSifenDTO: Información específica SIFEN
- DocumentoConsultaDTO: Para consultas masivas
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, validator


# ===============================================
# ENUMS BASE DOCUMENTOS
# ===============================================

class TipoDocumentoBaseEnum(str, Enum):
    """Tipos de documentos electrónicos SIFEN base"""
    FACTURA = "1"                    # Factura Electrónica
    AUTOFACTURA = "4"               # Autofactura Electrónica
    NOTA_CREDITO = "5"              # Nota de Crédito Electrónica
    NOTA_DEBITO = "6"               # Nota de Débito Electrónica
    NOTA_REMISION = "7"             # Nota de Remisión Electrónica


class EstadoDocumentoBaseEnum(str, Enum):
    """Estados base de documentos en el sistema"""
    BORRADOR = "borrador"            # En creación/edición
    GENERADO = "generado"            # XML generado
    FIRMADO = "firmado"              # Firmado digitalmente
    ENVIADO = "enviado"              # Enviado a SIFEN
    APROBADO = "aprobado"            # Aprobado por SIFEN
    APROBADO_OBSERVACION = "aprobado_observacion"  # Aprobado con observaciones
    RECHAZADO = "rechazado"          # Rechazado por SIFEN
    CANCELADO = "cancelado"          # Cancelado por usuario
    ANULADO = "anulado"              # Anulado por SIFEN


class CodigoRespuestaSifenEnum(str, Enum):
    """Códigos de respuesta SIFEN más comunes"""
    # Exitosos
    APROBADO = "0260"                           # Aprobado
    APROBADO_OBSERVACIONES = "1005"             # Aprobado con observaciones

    # Errores de documento
    CDC_NO_CORRESPONDE = "1000"                 # CDC no corresponde con XML
    CDC_DUPLICADO = "1001"                      # CDC duplicado
    TIMBRADO_INVALIDO = "1101"                  # Número timbrado inválido

    # Errores de contribuyente
    RUC_INEXISTENTE = "1250"                    # RUC emisor inexistente
    RUC_NO_AUTORIZADO = "1251"                  # RUC no autorizado

    # Errores de firma
    FIRMA_INVALIDA = "0141"                     # Firma digital inválida
    CERTIFICADO_INVALIDO = "0142"               # Certificado inválido

    # Errores de servidor
    ERROR_INTERNO = "5000"                      # Error interno del servidor


# ===============================================
# DTOs BASE
# ===============================================

class DocumentoBaseDTO(BaseModel):
    """
    DTO base para todos los documentos electrónicos.

    Contiene campos comunes a facturas, notas de crédito/débito, etc.
    Usado como clase base para DTOs específicos de documentos.

    Examples:
        ```python
        # Usado como base en FacturaResponseDTO
        class FacturaResponseDTO(DocumentoBaseDTO):
            # campos específicos de factura...
        ```
    """

    # === IDENTIFICACIÓN BÁSICA ===
    id: int = Field(..., description="ID único del documento")

    tipo_documento: str = Field(..., description="Tipo de documento SIFEN")

    cdc: Optional[str] = Field(
        None,
        min_length=44,
        max_length=44,
        description="CDC de 44 caracteres"
    )

    # === NUMERACIÓN ===
    numero_completo: str = Field(...,
                                 description="Número completo (001-001-0000123)")

    establecimiento: str = Field(..., description="Código establecimiento")

    punto_expedicion: str = Field(..., description="Punto de expedición")

    numero_documento: str = Field(..., description="Número de documento")

    numero_timbrado: str = Field(..., description="Número de timbrado")

    # === FECHAS BÁSICAS ===
    fecha_emision: date = Field(..., description="Fecha de emisión")

    created_at: datetime = Field(..., description="Fecha de creación")

    updated_at: datetime = Field(..., description="Última actualización")

    # === PARTICIPANTES ===
    empresa_id: int = Field(..., description="ID empresa emisora")

    cliente_id: int = Field(..., description="ID cliente receptor")

    # === TOTALES BÁSICOS ===
    total_operacion: Decimal = Field(..., description="Total sin IVA")

    total_iva: Decimal = Field(..., description="Total IVA")

    total_general: Decimal = Field(..., description="Total con IVA")

    moneda: str = Field(..., description="Moneda de la operación")

    # === ESTADO BÁSICO ===
    estado: str = Field(..., description="Estado actual del documento")

    is_active: bool = Field(..., description="Si el documento está activo")

    # === INFORMACIÓN ADICIONAL ===
    observaciones: Optional[str] = Field(None, description="Observaciones")

    @validator('cdc')
    def validate_cdc_format(cls, v):
        """Valida formato CDC de 44 dígitos"""
        if v is not None:
            # Limpiar espacios
            v = v.strip()

            # Validar formato: exactamente 44 dígitos
            if not v.isdigit() or len(v) != 44:
                raise ValueError(
                    'CDC debe tener exactamente 44 dígitos numéricos')

        return v

    @validator('numero_completo')
    def validate_numero_completo_format(cls, v):
        """Valida formato número completo XXX-XXX-XXXXXXX"""
        import re
        if not re.match(r'^\d{3}-\d{3}-\d{7}$', v):
            raise ValueError(
                'Número completo debe tener formato XXX-XXX-XXXXXXX')
        return v

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 123,
                "tipo_documento": "1",
                "cdc": "01234567890123456789012345678901234567890123",
                "numero_completo": "001-001-0000123",
                "establecimiento": "001",
                "punto_expedicion": "001",
                "numero_documento": "0000123",
                "numero_timbrado": "12345678",
                "fecha_emision": "2025-01-15",
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:35:00",
                "empresa_id": 1,
                "cliente_id": 456,
                "total_operacion": "2850000",
                "total_iva": "285000",
                "total_general": "3135000",
                "moneda": "PYG",
                "estado": "aprobado",
                "is_active": True,
                "observaciones": "Documento de ejemplo"
            }
        }


class DocumentoEstadoDTO(BaseModel):
    """
    DTO para estado y tracking temporal de documentos.

    Información detallada sobre el estado actual del documento
    y su progreso en el flujo SIFEN.

    Examples:
        ```python
        # GET /api/v1/documentos/{id}/estado response
        estado = DocumentoEstadoDTO(
            documento_id=123,
            estado_actual="aprobado",
            puede_ser_enviado=False,
            esta_aprobado=True
        )
        ```
    """

    documento_id: int = Field(..., description="ID del documento")

    # === ESTADO ACTUAL ===
    estado_actual: str = Field(..., description="Estado actual")

    descripcion_estado: str = Field(..., description="Descripción del estado")

    fecha_cambio_estado: datetime = Field(...,
                                          description="Fecha del último cambio")

    # === CAPACIDADES ===
    puede_ser_editado: bool = Field(..., description="Si puede ser editado")

    puede_ser_enviado: bool = Field(...,
                                    description="Si puede enviarse a SIFEN")

    puede_ser_cancelado: bool = Field(...,
                                      description="Si puede ser cancelado")

    puede_ser_anulado: bool = Field(..., description="Si puede ser anulado")

    # === ESTADO SIFEN ===
    esta_en_sifen: bool = Field(..., description="Si ya fue enviado a SIFEN")

    esta_aprobado: bool = Field(..., description="Si está aprobado por SIFEN")

    es_documento_fiscal: bool = Field(...,
                                      description="Si es documento fiscal válido")

    # === TIMESTAMPS WORKFLOW ===
    fecha_creacion: datetime = Field(..., description="Fecha de creación")

    fecha_generacion_xml: Optional[datetime] = Field(
        None, description="Fecha generación XML"
    )

    fecha_firma_digital: Optional[datetime] = Field(
        None, description="Fecha firma digital"
    )

    fecha_envio_sifen: Optional[datetime] = Field(
        None, description="Fecha envío a SIFEN"
    )

    fecha_respuesta_sifen: Optional[datetime] = Field(
        None, description="Fecha respuesta SIFEN"
    )

    # === PRÓXIMOS PASOS ===
    proxima_accion: Optional[str] = Field(
        None, description="Próxima acción recomendada"
    )

    tiempo_limite_envio: Optional[datetime] = Field(
        None, description="Límite para envío a SIFEN (72 horas)"
    )

    class Config:
        schema_extra = {
            "example": {
                "documento_id": 123,
                "estado_actual": "aprobado",
                "descripcion_estado": "Documento aprobado por SIFEN",
                "fecha_cambio_estado": "2025-01-15T10:35:00",
                "puede_ser_editado": False,
                "puede_ser_enviado": False,
                "puede_ser_cancelado": False,
                "puede_ser_anulado": True,
                "esta_en_sifen": True,
                "esta_aprobado": True,
                "es_documento_fiscal": True,
                "fecha_creacion": "2025-01-15T10:30:00",
                "fecha_generacion_xml": "2025-01-15T10:31:00",
                "fecha_firma_digital": "2025-01-15T10:32:00",
                "fecha_envio_sifen": "2025-01-15T10:33:00",
                "fecha_respuesta_sifen": "2025-01-15T10:35:00",
                "proxima_accion": None,
                "tiempo_limite_envio": None
            }
        }


class DocumentoSifenDTO(BaseModel):
    """
    DTO para información específica de SIFEN.

    Datos relacionados con la interacción con SIFEN:
    respuestas, códigos, URLs, protocolos, etc.

    Examples:
        ```python
        # GET /api/v1/documentos/{id}/sifen response
        sifen_info = DocumentoSifenDTO(
            documento_id=123,
            codigo_respuesta="0260",
            mensaje="Aprobado",
            numero_protocolo="PROT123456789"
        )
        ```
    """

    documento_id: int = Field(..., description="ID del documento")

    # === RESPUESTA SIFEN ===
    codigo_respuesta: Optional[str] = Field(
        None, description="Código de respuesta SIFEN"
    )

    mensaje_respuesta: Optional[str] = Field(
        None, description="Mensaje de respuesta SIFEN"
    )

    numero_protocolo: Optional[str] = Field(
        None, description="Número de protocolo SIFEN"
    )

    # === URLs Y CONSULTAS ===
    url_consulta_publica: Optional[str] = Field(
        None, description="URL consulta pública SET"
    )

    url_kude: Optional[str] = Field(
        None, description="URL representación gráfica KuDE"
    )

    qr_code_data: Optional[str] = Field(
        None, description="Datos para código QR"
    )

    # === INFORMACIÓN TÉCNICA ===
    ambiente_sifen: str = Field(...,
                                description="Ambiente usado (test/production)")

    version_sifen: str = Field(
        default="150", description="Versión SIFEN usada")

    # === DETALLES DE ENVÍO ===
    request_id: Optional[str] = Field(
        None, description="ID interno del request"
    )

    tiempo_respuesta: Optional[float] = Field(
        None, description="Tiempo de respuesta en segundos"
    )

    intentos_envio: int = Field(
        default=0, description="Número de intentos de envío"
    )

    ultimo_intento: Optional[datetime] = Field(
        None, description="Fecha del último intento"
    )

    # === ERRORES Y OBSERVACIONES ===
    errores_sifen: List[str] = Field(
        default_factory=list, description="Lista de errores SIFEN"
    )

    observaciones_sifen: List[str] = Field(
        default_factory=list, description="Lista de observaciones SIFEN"
    )

    # === CERTIFICADO USADO ===
    certificado_serial: Optional[str] = Field(
        None, description="Serial del certificado usado"
    )

    certificado_emisor: Optional[str] = Field(
        None, description="Emisor del certificado"
    )

    class Config:
        schema_extra = {
            "example": {
                "documento_id": 123,
                "codigo_respuesta": "0260",
                "mensaje_respuesta": "Aprobado",
                "numero_protocolo": "PROT123456789",
                "url_consulta_publica": "https://sifen.set.gov.py/consulta/...",
                "qr_code_data": "https://sifen.set.gov.py/qr/...",
                "ambiente_sifen": "test",
                "version_sifen": "150",
                "tiempo_respuesta": 3.5,
                "intentos_envio": 1,
                "ultimo_intento": "2025-01-15T10:33:00",
                "errores_sifen": [],
                "observaciones_sifen": [],
                "certificado_serial": "ABC123456789"
            }
        }


# ===============================================
# DTOs DE CONSULTA
# ===============================================

class DocumentoConsultaDTO(BaseModel):
    """
    DTO para consultas masivas de documentos.

    Parámetros para búsquedas y filtros en listados de documentos
    de cualquier tipo (facturas, notas, etc.).

    Examples:
        ```python
        # GET /api/v1/documentos?desde=2025-01-01&estado=aprobado
        consulta = DocumentoConsultaDTO(
            fecha_desde="2025-01-01",
            fecha_hasta="2025-01-31",
            tipos_documento=["1", "5"],
            estados=["aprobado"]
        )
        ```
    """

    # === FILTROS POR FECHA ===
    fecha_desde: Optional[date] = Field(
        None, description="Fecha inicio del rango"
    )

    fecha_hasta: Optional[date] = Field(
        None, description="Fecha fin del rango"
    )

    # === FILTROS POR TIPO ===
    tipos_documento: Optional[List[str]] = Field(
        None, description="Lista de tipos de documento a incluir"
    )

    # === FILTROS POR ESTADO ===
    estados: Optional[List[str]] = Field(
        None, description="Lista de estados a incluir"
    )

    solo_aprobados: Optional[bool] = Field(
        None, description="Solo documentos aprobados por SIFEN"
    )

    solo_fiscales: Optional[bool] = Field(
        None, description="Solo documentos fiscales válidos"
    )

    # === FILTROS POR PARTICIPANTES ===
    empresa_id: Optional[int] = Field(
        None, description="Filtrar por empresa específica"
    )

    cliente_id: Optional[int] = Field(
        None, description="Filtrar por cliente específico"
    )

    # === FILTROS POR MONTOS ===
    monto_minimo: Optional[Decimal] = Field(
        None, ge=0, description="Monto mínimo"
    )

    monto_maximo: Optional[Decimal] = Field(
        None, ge=0, description="Monto máximo"
    )

    # === FILTROS POR MONEDA ===
    monedas: Optional[List[str]] = Field(
        None, description="Lista de monedas a incluir"
    )

    # === BÚSQUEDA GENERAL ===
    q: Optional[str] = Field(
        None, min_length=2, max_length=100,
        description="Búsqueda general (número, cliente, observaciones)"
    )

    # === CONFIGURACIÓN DE RESPUESTA ===
    incluir_items: bool = Field(
        default=False, description="Incluir items en la respuesta"
    )

    incluir_estado_detallado: bool = Field(
        default=False, description="Incluir estado detallado"
    )

    incluir_info_sifen: bool = Field(
        default=False, description="Incluir información SIFEN"
    )

    @validator('fecha_hasta')
    def validate_fecha_range(cls, v, values):
        """Valida que fecha_hasta >= fecha_desde"""
        fecha_desde = values.get('fecha_desde')
        if fecha_desde and v and v < fecha_desde:
            raise ValueError(
                'fecha_hasta debe ser mayor o igual a fecha_desde')
        return v

    @validator('monto_maximo')
    def validate_monto_range(cls, v, values):
        """Valida que monto_maximo >= monto_minimo"""
        monto_minimo = values.get('monto_minimo')
        if monto_minimo and v and v < monto_minimo:
            raise ValueError(
                'monto_maximo debe ser mayor o igual a monto_minimo')
        return v

    class Config:
        schema_extra = {
            "example": {
                "fecha_desde": "2025-01-01",
                "fecha_hasta": "2025-01-31",
                "tipos_documento": ["1", "5"],
                "estados": ["aprobado", "aprobado_observacion"],
                "solo_aprobados": True,
                "monto_minimo": "100000",
                "monto_maximo": "10000000",
                "monedas": ["PYG"],
                "incluir_estado_detallado": True
            }
        }


# ===============================================
# DTOs DE ESTADÍSTICAS
# ===============================================

class DocumentoStatsDTO(BaseModel):
    """
    DTO para estadísticas generales de documentos.

    Métricas agregadas de todos los tipos de documentos
    para dashboards y reportes ejecutivos.

    Examples:
        ```python
        # GET /api/v1/documentos/stats response
        stats = DocumentoStatsDTO(
            total_documentos=500,
            total_facturado=1500000000,
            aprobados_sifen=485
        )
        ```
    """

    # === CONTADORES GENERALES ===
    total_documentos: int = Field(
        default=0, description="Total de documentos emitidos"
    )

    # === CONTADORES POR TIPO ===
    facturas: int = Field(default=0, description="Total facturas")

    notas_credito: int = Field(default=0, description="Total notas de crédito")

    notas_debito: int = Field(default=0, description="Total notas de débito")

    notas_remision: int = Field(
        default=0, description="Total notas de remisión")

    autofacturas: int = Field(default=0, description="Total autofacturas")

    # === CONTADORES POR ESTADO ===
    borradores: int = Field(default=0, description="Documentos en borrador")

    enviados: int = Field(default=0, description="Documentos enviados")

    aprobados: int = Field(default=0, description="Documentos aprobados")

    rechazados: int = Field(default=0, description="Documentos rechazados")

    # === MONTOS ===
    total_facturado: Decimal = Field(
        default=Decimal("0"), description="Monto total facturado"
    )

    total_iva: Decimal = Field(
        default=Decimal("0"), description="Total IVA generado"
    )

    promedio_documento: Decimal = Field(
        default=Decimal("0"), description="Promedio por documento"
    )

    # === MÉTRICAS TEMPORALES ===
    documentos_hoy: int = Field(
        default=0, description="Documentos emitidos hoy"
    )

    documentos_mes: int = Field(
        default=0, description="Documentos emitidos este mes"
    )

    # === PERÍODO ANALIZADO ===
    periodo_desde: Optional[date] = Field(
        None, description="Inicio del período"
    )

    periodo_hasta: Optional[date] = Field(
        None, description="Fin del período"
    )

    # === TASA DE ÉXITO ===
    tasa_aprobacion: float = Field(
        default=0.0, description="Porcentaje de aprobación SIFEN"
    )

    tiempo_promedio_aprobacion: Optional[float] = Field(
        None, description="Tiempo promedio hasta aprobación (horas)"
    )

    class Config:
        schema_extra = {
            "example": {
                "total_documentos": 500,
                "facturas": 450,
                "notas_credito": 35,
                "notas_debito": 10,
                "notas_remision": 5,
                "autofacturas": 0,
                "borradores": 5,
                "enviados": 10,
                "aprobados": 485,
                "rechazados": 0,
                "total_facturado": "1500000000",
                "total_iva": "136363636",
                "promedio_documento": "3000000",
                "documentos_hoy": 12,
                "documentos_mes": 150,
                "periodo_desde": "2025-01-01",
                "periodo_hasta": "2025-01-31",
                "tasa_aprobacion": 97.0,
                "tiempo_promedio_aprobacion": 2.5
            }
        }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # === ENUMS ===
    "TipoDocumentoBaseEnum",
    "EstadoDocumentoBaseEnum",
    "CodigoRespuestaSifenEnum",

    # === DTOs BASE ===
    "DocumentoBaseDTO",
    "DocumentoEstadoDTO",
    "DocumentoSifenDTO",

    # === DTOs CONSULTA ===
    "DocumentoConsultaDTO",
    "DocumentoStatsDTO"
]
