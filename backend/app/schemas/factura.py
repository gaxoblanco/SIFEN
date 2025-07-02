# ===============================================
# ARCHIVO: backend/app/schemas/factura.py
# PROPÓSITO: DTOs para facturas y documentos SIFEN
# PRIORIDAD: 🔴 CRÍTICO - Documento principal del sistema
# ===============================================

"""
Esquemas Pydantic para gestión de facturas y documentos electrónicos.

Este módulo define DTOs para:
- Creación y gestión de facturas electrónicas
- Items de factura con validaciones IVA
- Integración completa con SIFEN (XML → Firma → Envío)
- Estados y seguimiento de documentos
- Totales y cálculos automáticos

Integra con:
- models/documento.py, models/factura.py (SQLAlchemy)
- schemas/empresa.py, schemas/cliente.py, schemas/producto.py
- services/xml_generator (generación XML)
- services/digital_sign (firma digital)
- services/sifen_client (envío SIFEN)
- api/v1/facturas.py (endpoints facturación)

Flujo completo SIFEN:
1. FacturaCreateDTO → validación entrada
2. ItemFacturaDTO → validación items
3. FacturaResponseDTO → respuesta con cálculos
4. FacturaSifenDTO → procesamiento SIFEN
"""

from typing import Optional, List, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
import re

# Imports de schemas relacionados (serán resueltos en runtime)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .empresa import EmpresaResponseDTO
    from .cliente import ClienteResponseDTO
    from .producto import ProductoResponseDTO
    from .common import EstadoDocumentoEnum, MonedaEnum


# ===============================================
# ENUMS SIFEN
# ===============================================

class TipoDocumentoSifenEnum(str, Enum):
    """Tipos de documentos electrónicos SIFEN"""
    FACTURA = "1"                    # Factura Electrónica
    AUTOFACTURA = "4"               # Autofactura Electrónica
    NOTA_CREDITO = "5"              # Nota de Crédito Electrónica
    NOTA_DEBITO = "6"               # Nota de Débito Electrónica
    NOTA_REMISION = "7"             # Nota de Remisión Electrónica


class TipoEmisionEnum(str, Enum):
    """Tipos de emisión según SIFEN"""
    NORMAL = "1"                     # Emisión normal
    CONTINGENCIA = "2"               # Emisión de contingencia


class TipoOperacionEnum(str, Enum):
    """Tipos de operación según SIFEN"""
    VENTA = "1"                      # Venta de mercaderías
    PRESTACION_SERVICIOS = "2"       # Prestación de servicios
    MIXTA = "3"                      # Mixta (mercaderías + servicios)
    CONSIGNACION = "4"               # Consignación


class CondicionOperacionEnum(str, Enum):
    """Condiciones de operación según SIFEN"""
    CONTADO = "1"                    # Operación al contado
    CREDITO = "2"                    # Operación a crédito


# ===============================================
# DTOs DE ITEMS
# ===============================================

class ItemFacturaDTO(BaseModel):
    """
    DTO para items de factura.

    Representa un producto/servicio dentro de una factura.
    Incluye validaciones de montos, IVA y totales.

    Examples:
        ```python
        item = ItemFacturaDTO(
            producto_id=123,
            cantidad=2,
            precio_unitario=1500000,
            observaciones="Notebook empresarial"
        )
        ```
    """

    # === IDENTIFICACIÓN ===
    producto_id: int = Field(
        ...,
        description="ID del producto en el catálogo"
    )

    # === CANTIDADES Y PRECIOS ===
    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad del producto/servicio"
    )

    precio_unitario: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Precio unitario (si es None, usa precio del producto)"
    )

    # === DESCUENTOS ===
    descuento_unitario: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Descuento por unidad en Guaraníes"
    )

    descuento_porcentual: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        description="Descuento porcentual (0-100%)"
    )

    # === INFORMACIÓN ADICIONAL ===
    observaciones: Optional[str] = Field(
        None,
        max_length=500,
        description="Observaciones específicas del item"
    )

    @validator('cantidad')
    def validate_cantidad_guaranies(cls, v):
        """Valida cantidad con máximo 3 decimales"""
        # Paraguay permite hasta 3 decimales en cantidades
        if v.as_tuple().exponent < -3:
            raise ValueError('Cantidad no puede tener más de 3 decimales')
        # Validar cantidad máxima razonable
        if v > 999999:  # 999,999 unidades máximo
            raise ValueError('Cantidad excede límite máximo permitido')

        # Validar cantidad mínima
        if v <= 0:
            raise ValueError('Cantidad debe ser mayor a 0')
        return v

    @validator('precio_unitario')
    def validate_precio_guaranies(cls, v):
        """Valida precio unitario en Guaraníes (sin centavos)"""
        if v is not None:
            if v < 0:
                raise ValueError('Precio unitario no puede ser negativo')

            if v > 99999999999:  # 99 mil millones (más realista)
                raise ValueError('Precio unitario excede límite máximo')

            # Guaraníes no tienen centavos
            if v != int(v):
                raise ValueError('Precio en Guaraníes no puede tener centavos')

        return v

    @validator('descuento_unitario')
    def validate_descuento_unitario(cls, v):
        """Valida descuento unitario en Guaraníes"""
        if v < 0:
            raise ValueError('Descuento unitario no puede ser negativo')

        if v != int(v):
            raise ValueError('Descuento en Guaraníes no puede tener centavos')

        return v

    @root_validator  # type: ignore
    def validate_descuentos_consistency(cls, values):
        """Valida que no se usen ambos tipos de descuento simultáneamente"""
        desc_unitario = values.get('descuento_unitario', Decimal("0"))
        desc_porcentual = values.get('descuento_porcentual', Decimal("0"))

        if desc_unitario > 0 and desc_porcentual > 0:
            raise ValueError(
                'No se pueden aplicar descuento unitario y porcentual simultáneamente'
            )

        return values

    @validator('descuento_porcentual', always=True)
    def validate_descuento_logico(cls, v, values):
        """Valida que el descuento sea lógico respecto al precio"""
        precio = values.get('precio_unitario')
        desc_unitario = values.get('descuento_unitario', Decimal("0"))

        if precio and desc_unitario > precio:
            raise ValueError('Descuento unitario no puede ser mayor al precio')

        return v

    class Config:
        schema_extra = {
            "example": {
                "producto_id": 123,
                "cantidad": "2.000",
                "precio_unitario": "1500000",
                "descuento_porcentual": "5.0",
                "observaciones": "Notebook empresarial con garantía extendida"
            }
        }


class ItemFacturaResponseDTO(BaseModel):
    """
    DTO para respuesta de items de factura con cálculos.

    Incluye todos los campos calculados automáticamente
    como subtotales, IVA y totales por item.
    """

    # === IDENTIFICACIÓN ===
    id: Optional[int] = Field(None, description="ID del item (si existe)")

    producto_id: int = Field(..., description="ID del producto")

    # === DATOS DEL PRODUCTO ===
    producto: Optional["ProductoResponseDTO"] = Field(
        None, description="Datos completos del producto")
    # === CANTIDADES Y PRECIOS ===
    cantidad: Decimal = Field(..., description="Cantidad")

    precio_unitario: Decimal = Field(..., description="Precio unitario final")

    precio_original: Optional[Decimal] = Field(
        None, description="Precio original del producto"
    )

    # === DESCUENTOS ===
    descuento_unitario: Decimal = Field(...,
                                        description="Descuento por unidad")

    descuento_porcentual: Decimal = Field(...,
                                          description="Descuento porcentual")

    monto_descuento: Decimal = Field(..., description="Monto total descuento")

    # === IMPUESTOS ===
    tasa_iva: Decimal = Field(..., description="Tasa de IVA aplicada (%)")

    afectacion_iva: str = Field(..., description="Afectación de IVA")

    # === TOTALES CALCULADOS ===
    subtotal: Decimal = Field(..., description="Subtotal sin IVA")

    monto_iva: Decimal = Field(..., description="Monto de IVA")

    total_item: Decimal = Field(..., description="Total del item con IVA")

    # === INFORMACIÓN ADICIONAL ===
    observaciones: Optional[str] = Field(None, description="Observaciones")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "producto_id": 123,
                "codigo_producto": "PROD001",
                "descripcion_producto": "NOTEBOOK LENOVO THINKPAD E14",
                "unidad_medida": "Unidad",
                "cantidad": "2.000",
                "precio_unitario": "1425000",
                "precio_original": "1500000",
                "descuento_unitario": "0",
                "descuento_porcentual": "5.0",
                "monto_descuento": "150000",
                "tasa_iva": "10",
                "afectacion_iva": "1",
                "subtotal": "2850000",
                "monto_iva": "285000",
                "total_item": "3135000"
            }
        }


# ===============================================
# DTOs DE ENTRADA (REQUEST)
# ===============================================

class FacturaCreateDTO(BaseModel):
    """
    DTO para creación de nuevas facturas.

    Valida datos mínimos requeridos para crear una factura
    electrónica compatible con SIFEN Paraguay.

    Examples:
        ```python
        # POST /api/v1/facturas
        factura_data = FacturaCreateDTO(
            cliente_id=456,
            items=[
                ItemFacturaDTO(producto_id=123, cantidad=2),
                ItemFacturaDTO(producto_id=124, cantidad=1, precio_unitario=800000)
            ],
            tipo_operacion="1",
            condicion_operacion="1",
            observaciones="Factura de ejemplo"
        )
        ```
    """

    # === IDENTIFICACIÓN OBLIGATORIA ===
    cliente_id: int = Field(
        ...,
        description="ID del cliente receptor"
    )

    # === ITEMS OBLIGATORIOS ===
    items: List[ItemFacturaDTO] = Field(
        ...,
        min_length=1,
        max_length=999,
        description="Lista de items de la factura (mín. 1, máx. 999)"
    )

    # === CONFIGURACIÓN OPERACIÓN ===
    tipo_operacion: TipoOperacionEnum = Field(
        default=TipoOperacionEnum.VENTA,
        description="Tipo de operación SIFEN"
    )

    condicion_operacion: CondicionOperacionEnum = Field(
        default=CondicionOperacionEnum.CONTADO,
        description="Condición de operación (contado/crédito)"
    )

    # === CONFIGURACIÓN OPCIONAL ===
    fecha_emision: Optional[date] = Field(
        default=None,
        description="Fecha de emisión (hoy si es None)"
    )

    tipo_emision: TipoEmisionEnum = Field(
        default=TipoEmisionEnum.NORMAL,
        description="Tipo de emisión"
    )

    moneda: MonedaEnum = Field(
        default=MonedaEnum.PYG,
        description="Moneda de la operación"
    )

    tipo_cambio: Decimal = Field(
        default=Decimal("1.0000"),
        gt=0,
        description="Tipo de cambio (1.0000 para PYG)"
    )

    # === INFORMACIÓN ADICIONAL ===
    observaciones: Optional[str] = Field(
        None,
        max_length=500,
        description="Observaciones generales de la factura"
    )

    motivo_emision: Optional[str] = Field(
        None,
        max_length=500,
        description="Motivo específico de emisión"
    )

    # === CONFIGURACIÓN AVANZADA ===
    establecimiento: Optional[str] = Field(
        None,
        pattern=r'^\d{3}$',
        description="Establecimiento específico (si difiere del default)"
    )

    punto_expedicion: Optional[str] = Field(
        None,
        pattern=r'^\d{3}$',
        description="Punto expedición específico (si difiere del default)"
    )

    @validator('fecha_emision')
    def validate_fecha_emision(cls, v):
        """Valida fecha de emisión"""
        if v is not None:
            # No puede ser fecha futura
            if v > date.today():
                raise ValueError('Fecha de emisión no puede ser futura')

            # No puede ser muy antigua (más de 45 días)
            days_diff = (date.today() - v).days
            if days_diff > 45:  # Según normativa SIFEN oficial
                raise ValueError(
                    'Fecha de emisión no puede ser mayor a 45 días')

        return v

    @validator('tipo_cambio')
    def validate_tipo_cambio(cls, v, values):
        """Valida tipo de cambio según moneda"""
        moneda = values.get('moneda', MonedaEnum.PYG)

        if moneda == MonedaEnum.PYG and v != Decimal("1.0000"):
            raise ValueError('Tipo de cambio debe ser 1.0000 para Guaraníes')

        if moneda != MonedaEnum.PYG and v <= Decimal("0"):
            raise ValueError(
                'Tipo de cambio debe ser mayor a 0 para moneda extranjera')

        return v

    @root_validator  # type: ignore
    def validate_factura_consistency(cls, values):
        """Validaciones de consistencia general"""
        items = values.get('items', [])

        if not items:
            raise ValueError('Factura debe tener al menos 1 item')

        # Permitir mismo producto con diferentes precios/descuentos
        # Solo alertar si son exactamente iguales
        duplicates = []
        for i, item1 in enumerate(items):
            for j, item2 in enumerate(items[i+1:], i+1):
                if (item1.producto_id == item2.producto_id and
                    item1.precio_unitario == item2.precio_unitario and
                    item1.descuento_unitario == item2.descuento_unitario and
                        item1.descuento_porcentual == item2.descuento_porcentual):
                    duplicates.append(f"Items {i+1} y {j+1} son idénticos")

        if duplicates:
            raise ValueError(
                f'Items duplicados detectados: {", ".join(duplicates)}')

        return values

    @validator('establecimiento', 'punto_expedicion')
    def validate_codigo_sifen(cls, v):
        """Valida códigos SIFEN específicos"""
        if v is not None:
            if not re.match(r'^\d{3}$', v):
                raise ValueError('Código debe ser exactamente 3 dígitos')

            num = int(v)
            if num < 1 or num > 999:
                raise ValueError('Código debe estar entre 001 y 999')

            if v == "000":
                raise ValueError('Código no puede ser 000')

        return v

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "cliente_id": 456,
                "items": [
                    {
                        "producto_id": 123,
                        "cantidad": "2.000",
                        "descuento_porcentual": "5.0"
                    },
                    {
                        "producto_id": 124,
                        "cantidad": "1.000",
                        "precio_unitario": "800000"
                    }
                ],
                "tipo_operacion": "1",
                "condicion_operacion": "1",
                "observaciones": "Factura de ejemplo para demo",
                "motivo_emision": "Venta productos tecnológicos"
            }
        }


class FacturaUpdateDTO(BaseModel):
    """
    DTO para actualización de facturas.

    Permite modificar facturas en estado BORRADOR únicamente.
    Solo se pueden actualizar campos específicos.

    Examples:
        ```python
        # PUT /api/v1/facturas/{id}
        update_data = FacturaUpdateDTO(
            observaciones="Observaciones actualizadas",
            motivo_emision="Motivo actualizado"
        )
        ```
    """

    # === SOLO CAMPOS MODIFICABLES ===
    observaciones: Optional[str] = Field(
        None,
        max_length=500,
        description="Nuevas observaciones"
    )

    motivo_emision: Optional[str] = Field(
        None,
        max_length=500,
        description="Nuevo motivo de emisión"
    )

    # NOTA: Items, cliente, totales NO son modificables
    # Para cambios significativos, crear nueva factura

    class Config:
        schema_extra = {
            "example": {
                "observaciones": "Observaciones actualizadas",
                "motivo_emision": "Motivo actualizado por solicitud del cliente"
            }
        }


# ===============================================
# DTOs DE SALIDA (RESPONSE)
# ===============================================

class FacturaResponseDTO(BaseModel):
    """
    DTO para respuesta con datos completos de factura.

    Información completa de la factura incluyendo cálculos,
    datos de emisor/receptor y estado SIFEN.

    Examples:
        ```python
        # GET /api/v1/facturas/{id} response
        factura_response = FacturaResponseDTO(
            id=789,
            numero_completo="001-001-0000123",
            cdc="01234567890123456789012345678901234567890123",
            estado="aprobado",
            # ... resto de campos
        )
        ```
    """

    # === IDENTIFICACIÓN ===
    id: int = Field(..., description="ID único de la factura")

    cdc: Optional[str] = Field(None, description="CDC de 44 caracteres")

    numero_completo: str = Field(...,
                                 description="Número completo (001-001-0000123)")

    tipo_documento: str = Field(..., description="Tipo de documento SIFEN")

    # === NUMERACIÓN ===
    establecimiento: str = Field(..., description="Código establecimiento")

    punto_expedicion: str = Field(..., description="Punto de expedición")

    numero_documento: str = Field(..., description="Número de documento")

    numero_timbrado: str = Field(..., description="Número de timbrado")

    # === FECHAS ===
    fecha_emision: date = Field(..., description="Fecha de emisión")

    created_at: datetime = Field(..., description="Fecha de creación")

    updated_at: datetime = Field(..., description="Última actualización")

    # === CONFIGURACIÓN ===
    tipo_emision: str = Field(..., description="Tipo de emisión")

    tipo_operacion: str = Field(..., description="Tipo de operación")

    condicion_operacion: str = Field(..., description="Condición de operación")

    moneda: str = Field(..., description="Moneda de la operación")

    tipo_cambio: Decimal = Field(..., description="Tipo de cambio")

    # === PARTICIPANTES ===
    empresa_id: int = Field(..., description="ID empresa emisora")

    cliente_id: int = Field(..., description="ID cliente receptor")

    # Datos anidados (opcional, según endpoint)
    empresa: Optional["EmpresaResponseDTO"] = Field(
        None, description="Datos del emisor"
    )

    cliente: Optional["ClienteResponseDTO"] = Field(
        None, description="Datos del receptor"
    )

    # === ITEMS ===
    items: List[ItemFacturaResponseDTO] = Field(
        ..., description="Items de la factura"
    )

    # === TOTALES CALCULADOS ===
    total_operacion: Decimal = Field(..., description="Total sin IVA")

    total_iva: Decimal = Field(..., description="Total IVA")

    total_general: Decimal = Field(..., description="Total con IVA")

    # Subtotales por tasa IVA
    subtotal_exento: Decimal = Field(..., description="Subtotal exento (0%)")

    subtotal_iva5: Decimal = Field(..., description="Subtotal IVA 5%")

    subtotal_iva10: Decimal = Field(..., description="Subtotal IVA 10%")

    monto_iva5: Decimal = Field(..., description="Monto IVA 5%")

    monto_iva10: Decimal = Field(..., description="Monto IVA 10%")

    # === ESTADO Y SIFEN ===
    estado: str = Field(..., description="Estado actual del documento")

    puede_ser_enviado: bool = Field(...,
                                    description="Si puede enviarse a SIFEN")

    esta_aprobado: bool = Field(..., description="Si está aprobado por SIFEN")

    # Información SIFEN (si existe)
    codigo_respuesta_sifen: Optional[str] = Field(
        None, description="Código respuesta SIFEN"
    )

    mensaje_sifen: Optional[str] = Field(
        None, description="Mensaje de SIFEN"
    )

    numero_protocolo: Optional[str] = Field(
        None, description="Número de protocolo SIFEN"
    )

    url_consulta_publica: Optional[str] = Field(
        None, description="URL consulta pública SET"
    )

    # === TIMESTAMPS SIFEN ===
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

    # === INFORMACIÓN ADICIONAL ===
    observaciones: Optional[str] = Field(None, description="Observaciones")

    motivo_emision: Optional[str] = Field(
        None, description="Motivo de emisión")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 789,
                "cdc": "01234567890123456789012345678901234567890123",
                "numero_completo": "001-001-0000123",
                "tipo_documento": "1",
                "establecimiento": "001",
                "punto_expedicion": "001",
                "numero_documento": "0000123",
                "numero_timbrado": "12345678",
                "fecha_emision": "2025-01-15",
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:35:00",
                "tipo_emision": "1",
                "tipo_operacion": "1",
                "condicion_operacion": "1",
                "moneda": "PYG",
                "tipo_cambio": "1.0000",
                "empresa_id": 1,
                "cliente_id": 456,
                "total_operacion": "2850000",
                "total_iva": "285000",
                "total_general": "3135000",
                "subtotal_exento": "0",
                "subtotal_iva5": "0",
                "subtotal_iva10": "2850000",
                "monto_iva5": "0",
                "monto_iva10": "285000",
                "estado": "aprobado",
                "puede_ser_enviado": False,
                "esta_aprobado": True,
                "codigo_respuesta_sifen": "0260",
                "mensaje_sifen": "Aprobado",
                "numero_protocolo": "PROT123456789",
                "url_consulta_publica": "https://sifen.set.gov.py/consulta/...",
                "fecha_generacion_xml": "2025-01-15T10:31:00",
                "fecha_firma_digital": "2025-01-15T10:32:00",
                "fecha_envio_sifen": "2025-01-15T10:33:00",
                "fecha_respuesta_sifen": "2025-01-15T10:35:00",
                "observaciones": "Factura de ejemplo",
                "items": []
            }
        }


class FacturaListDTO(BaseModel):
    """
    DTO para elemento en lista de facturas.

    Versión compacta para listados con información esencial.
    """

    id: int = Field(..., description="ID único de la factura")

    numero_completo: str = Field(..., description="Número completo")

    fecha_emision: date = Field(..., description="Fecha de emisión")

    cliente_nombre: str = Field(..., description="Nombre del cliente")

    cliente_documento: str = Field(..., description="Documento del cliente")

    total_general: Decimal = Field(..., description="Total con IVA")

    moneda: str = Field(..., description="Moneda")

    estado: str = Field(..., description="Estado actual")

    esta_aprobado: bool = Field(..., description="Si está aprobado")

    created_at: datetime = Field(..., description="Fecha de creación")

    items_count: int = Field(..., description="Cantidad de items")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 789,
                "numero_completo": "001-001-0000123",
                "fecha_emision": "2025-01-15",
                "cliente_nombre": "CLIENTE EJEMPLO S.R.L.",
                "cliente_documento": "80087654-3",
                "total_general": "3135000",
                "moneda": "PYG",
                "estado": "aprobado",
                "esta_aprobado": True,
                "created_at": "2025-01-15T10:30:00",
                "items_count": 2
            }
        }


# ===============================================
# DTOs ESPECIALIZADOS SIFEN
# ===============================================

class FacturaSifenDTO(BaseModel):
    """
    DTO para procesamiento SIFEN completo.

    Coordina todo el flujo: XML → Firma → SIFEN
    Usado en endpoints de envío masivo a SIFEN.

    Examples:
        ```python
        # POST /api/v1/facturas/{id}/enviar-sifen
        sifen_request = FacturaSifenDTO(
            generar_xml=True,
            firmar_digital=True,
            enviar_sifen=True
        )
        ```
    """

    # === CONFIGURACIÓN PROCESAMIENTO ===
    generar_xml: bool = Field(
        default=True,
        description="Si generar XML automáticamente"
    )

    firmar_digital: bool = Field(
        default=True,
        description="Si firmar digitalmente"
    )

    enviar_sifen: bool = Field(
        default=True,
        description="Si enviar a SIFEN"
    )

    # === CONFIGURACIÓN AVANZADA ===
    forzar_regeneracion: bool = Field(
        default=False,
        description="Forzar regeneración de XML existente"
    )

    ambiente_sifen: Optional[str] = Field(
        None,
        description="Ambiente específico (test/production)"
    )

    # === CONFIGURACIÓN CERTIFICADO ===
    certificado_especifico: Optional[str] = Field(
        None,
        description="Path certificado específico (opcional)"
    )

    class Config:
        schema_extra = {
            "example": {
                "generar_xml": True,
                "firmar_digital": True,
                "enviar_sifen": True,
                "forzar_regeneracion": False
            }
        }


class FacturaSifenResponseDTO(BaseModel):
    """
    DTO para respuesta de procesamiento SIFEN.

    Resultado detallado del procesamiento completo
    con información de cada etapa.
    """

    # === RESULTADO GENERAL ===
    success: bool = Field(..., description="Si el procesamiento fue exitoso")

    factura_id: int = Field(..., description="ID de la factura procesada")

    # === RESULTADOS POR ETAPA ===
    xml_generado: bool = Field(..., description="Si XML fue generado")

    xml_firmado: bool = Field(..., description="Si XML fue firmado")

    enviado_sifen: bool = Field(..., description="Si fue enviado a SIFEN")

    aprobado_sifen: bool = Field(..., description="Si fue aprobado por SIFEN")

    # === INFORMACIÓN SIFEN ===
    cdc_generado: Optional[str] = Field(None, description="CDC generado")

    codigo_respuesta: Optional[str] = Field(
        None, description="Código respuesta SIFEN")

    mensaje_respuesta: Optional[str] = Field(None, description="Mensaje SIFEN")

    numero_protocolo: Optional[str] = Field(
        None, description="Número protocolo")

    url_consulta: Optional[str] = Field(
        None, description="URL consulta pública")

    # === TIMESTAMPS ===
    tiempo_xml: Optional[float] = Field(
        None, description="Tiempo generación XML (seg)")

    tiempo_firma: Optional[float] = Field(
        None, description="Tiempo firma digital (seg)")

    tiempo_sifen: Optional[float] = Field(
        None, description="Tiempo envío SIFEN (seg)")

    tiempo_total: Optional[float] = Field(
        None, description="Tiempo total procesamiento (seg)")

    # === ERRORES (SI LOS HAY) ===
    errores: List[str] = Field(
        default_factory=list, description="Lista de errores")

    warnings: List[str] = Field(
        default_factory=list, description="Lista de advertencias")

    # === ESTADO FINAL ===
    estado_final: str = Field(..., description="Estado final del documento")

    procesamiento_completo: bool = Field(...,
                                         description="Si completó todo el flujo")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "factura_id": 789,
                "xml_generado": True,
                "xml_firmado": True,
                "enviado_sifen": True,
                "aprobado_sifen": True,
                "cdc_generado": "01234567890123456789012345678901234567890123",
                "codigo_respuesta": "0260",
                "mensaje_respuesta": "Aprobado",
                "numero_protocolo": "PROT123456789",
                "url_consulta": "https://sifen.set.gov.py/consulta/...",
                "tiempo_xml": 0.5,
                "tiempo_firma": 1.2,
                "tiempo_sifen": 3.8,
                "tiempo_total": 5.5,
                "errores": [],
                "warnings": [],
                "estado_final": "aprobado",
                "procesamiento_completo": True
            }
        }


# ===============================================
# DTOs DE BÚSQUEDA Y FILTROS
# ===============================================

class FacturaSearchDTO(BaseModel):
    """
    DTO para búsqueda de facturas.

    Parámetros de búsqueda y filtros para listados de facturas.

    Examples:
        ```python
        # GET /api/v1/facturas?desde=2025-01-01&estado=aprobado
        search_params = FacturaSearchDTO(
            fecha_desde="2025-01-01",
            fecha_hasta="2025-01-31",
            estado="aprobado",
            cliente_documento="80087654-3"
        )
        ```
    """

    # === FILTROS POR FECHA ===
    fecha_desde: Optional[date] = Field(
        None,
        description="Fecha inicio del rango de búsqueda"
    )

    fecha_hasta: Optional[date] = Field(
        None,
        description="Fecha fin del rango de búsqueda"
    )

    # === FILTROS POR PARTICIPANTES ===
    cliente_id: Optional[int] = Field(
        None,
        description="Filtrar por cliente específico"
    )

    cliente_documento: Optional[str] = Field(
        None,
        max_length=20,
        description="Filtrar por documento del cliente"
    )

    cliente_nombre: Optional[str] = Field(
        None,
        max_length=100,
        description="Buscar por nombre/razón social del cliente"
    )

    # === FILTROS POR ESTADO ===
    estado: Optional[EstadoDocumentoEnum] = Field(
        None,
        description="Filtrar por estado específico"
    )

    aprobado_sifen: Optional[bool] = Field(
        None,
        description="Filtrar por aprobación SIFEN"
    )

    # === FILTROS POR MONTOS ===
    monto_desde: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Monto mínimo"
    )

    monto_hasta: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Monto máximo"
    )

    # === FILTROS POR CONFIGURACIÓN ===
    moneda: Optional[MonedaEnum] = Field(
        None,
        description="Filtrar por moneda"
    )

    tipo_operacion: Optional[TipoOperacionEnum] = Field(
        None,
        description="Filtrar por tipo de operación"
    )

    # === BÚSQUEDA GENERAL ===
    q: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Búsqueda general (número, cliente, observaciones)"
    )

    @validator('fecha_hasta')
    def validate_fecha_range(cls, v, values):
        """Valida que fecha_hasta >= fecha_desde"""
        fecha_desde = values.get('fecha_desde')
        if fecha_desde and v and v < fecha_desde:
            raise ValueError(
                'fecha_hasta debe ser mayor o igual a fecha_desde')
        return v

    @validator('monto_hasta')
    def validate_monto_range(cls, v, values):
        """Valida que monto_hasta >= monto_desde"""
        monto_desde = values.get('monto_desde')
        if monto_desde and v and v < monto_desde:
            raise ValueError(
                'monto_hasta debe ser mayor o igual a monto_desde')
        return v

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "fecha_desde": "2025-01-01",
                "fecha_hasta": "2025-01-31",
                "estado": "aprobado",
                "cliente_documento": "80087654-3",
                "monto_desde": "100000",
                "monto_hasta": "10000000",
                "moneda": "PYG"
            }
        }


# ===============================================
# DTOs DE ESTADÍSTICAS
# ===============================================

class FacturaStatsDTO(BaseModel):
    """
    DTO para estadísticas de facturación.

    Métricas y estadísticas agregadas de facturación
    útiles para dashboards y reportes.

    Examples:
        ```python
        # GET /api/v1/facturas/stats response
        stats = FacturaStatsDTO(
            total_facturas=150,
            total_facturado=450000000,
            aprobadas_sifen=145,
            promedio_diario=2500000
        )
        ```
    """

    # === CONTADORES GENERALES ===
    total_facturas: int = Field(
        default=0,
        description="Total de facturas emitidas"
    )

    total_items: int = Field(
        default=0,
        description="Total de items facturados"
    )

    # === CONTADORES POR ESTADO ===
    borradores: int = Field(default=0, description="Facturas en borrador")

    enviadas: int = Field(default=0, description="Facturas enviadas")

    aprobadas_sifen: int = Field(default=0, description="Aprobadas por SIFEN")

    rechazadas_sifen: int = Field(
        default=0, description="Rechazadas por SIFEN")

    canceladas: int = Field(default=0, description="Facturas canceladas")

    # === MONTOS ===
    total_facturado: Decimal = Field(
        default=Decimal("0"),
        description="Monto total facturado (Guaraníes)"
    )

    total_iva_generado: Decimal = Field(
        default=Decimal("0"),
        description="Total IVA generado (Guaraníes)"
    )

    promedio_por_factura: Decimal = Field(
        default=Decimal("0"),
        description="Promedio por factura (Guaraníes)"
    )

    factura_mayor: Decimal = Field(
        default=Decimal("0"),
        description="Factura de mayor monto (Guaraníes)"
    )

    factura_menor: Decimal = Field(
        default=Decimal("0"),
        description="Factura de menor monto (Guaraníes)"
    )

    # === MÉTRICAS TEMPORALES ===
    promedio_diario: Decimal = Field(
        default=Decimal("0"),
        description="Facturación promedio diaria (Guaraníes)"
    )

    promedio_mensual: Decimal = Field(
        default=Decimal("0"),
        description="Facturación promedio mensual (Guaraníes)"
    )

    # === MÉTRICAS DE PRODUCTOS ===
    productos_mas_vendidos: List[dict] = Field(
        default_factory=list,
        description="Top 10 productos más vendidos"
    )

    # === MÉTRICAS DE CLIENTES ===
    clientes_mas_frecuentes: List[dict] = Field(
        default_factory=list,
        description="Top 10 clientes más frecuentes"
    )

    # === FECHAS ===
    primera_factura: Optional[datetime] = Field(
        None,
        description="Fecha de primera factura"
    )

    ultima_factura: Optional[datetime] = Field(
        None,
        description="Fecha de última factura"
    )

    # === PERIODO DE ANÁLISIS ===
    periodo_desde: Optional[date] = Field(
        None,
        description="Inicio del período analizado"
    )

    periodo_hasta: Optional[date] = Field(
        None,
        description="Fin del período analizado"
    )

    class Config:
        schema_extra = {
            "example": {
                "total_facturas": 150,
                "total_items": 287,
                "borradores": 2,
                "enviadas": 3,
                "aprobadas_sifen": 145,
                "rechazadas_sifen": 0,
                "canceladas": 0,
                "total_facturado": "450000000",
                "total_iva_generado": "40909091",
                "promedio_por_factura": "3000000",
                "factura_mayor": "15000000",
                "factura_menor": "125000",
                "promedio_diario": "2500000",
                "promedio_mensual": "75000000",
                "productos_mas_vendidos": [
                    {"producto": "NOTEBOOK LENOVO",
                        "cantidad": 45, "monto": "225000000"},
                    {"producto": "MOUSE INALAMBRICO",
                        "cantidad": 78, "monto": "15600000"}
                ],
                "clientes_mas_frecuentes": [
                    {"cliente": "EMPRESA XYZ", "facturas": 12, "monto": "45000000"},
                    {"cliente": "CLIENTE ABC", "facturas": 8, "monto": "32000000"}
                ],
                "primera_factura": "2024-06-15T10:30:00",
                "ultima_factura": "2025-01-15T10:30:00",
                "periodo_desde": "2025-01-01",
                "periodo_hasta": "2025-01-31"
            }
        }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # === ENUMS ===
    "TipoDocumentoSifenEnum",
    "TipoEmisionEnum",
    "TipoOperacionEnum",
    "CondicionOperacionEnum",
    "MonedaEnum",

    # === DTOs DE ITEMS ===
    "ItemFacturaDTO",
    "ItemFacturaResponseDTO",

    # === DTOs DE ENTRADA ===
    "FacturaCreateDTO",
    "FacturaUpdateDTO",

    # === DTOs DE SALIDA ===
    "FacturaResponseDTO",
    "FacturaListDTO",

    # === DTOs ESPECIALIZADOS SIFEN ===
    "FacturaSifenDTO",
    "FacturaSifenResponseDTO",

    # === DTOs DE BÚSQUEDA ===
    "FacturaSearchDTO",
    "FacturaStatsDTO"
]
