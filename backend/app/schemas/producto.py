# ===============================================
# ARCHIVO: backend/app/schemas/producto.py
# PROPÓSITO: DTOs para productos y servicios SIFEN
# PRIORIDAD: 🟡 CRÍTICO - Catálogo para facturación electrónica
# ===============================================

"""
Esquemas Pydantic para gestión de productos y servicios.

Este módulo define DTOs para:
- Catálogo de productos físicos y servicios
- Configuración de precios e IVA Paraguay
- Control básico de inventario
- Integración con documentos SIFEN

Integra con:
- models/producto.py (SQLAlchemy)
- services/xml_generator (items factura)
- api/v1/productos.py (endpoints CRUD)

Regulaciones Paraguay:
- IVA: 0% (exento), 5% (reducido), 10% (estándar)
- Unidades de medida comunes Paraguay
- Códigos NCM para productos físicos
- Validaciones específicas SIFEN
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, validator
import re


# ===============================================
# ENUMS PARAGUAY
# ===============================================

class TipoProductoEnum(str, Enum):
    """Tipos de productos/servicios según normativa SIFEN"""
    PRODUCTO = "producto"          # Producto físico
    SERVICIO = "servicio"          # Servicio profesional/técnico
    BIEN_USO = "bien_uso"          # Bien de uso/activo fijo
    OTROS = "otros"                # Otros tipos


class AfectacionIvaEnum(str, Enum):
    """Afectación de IVA según SIFEN Paraguay"""
    GRAVADO = "1"                  # Gravado con IVA (10% estándar, 5% reducido)
    EXONERADO = "2"                # Exonerado de IVA
    EXENTO = "3"                   # Exento de IVA


class TasaIvaEnum(str, Enum):
    """Tasas de IVA vigentes en Paraguay"""
    EXENTO = "0"                   # 0% - Exento de IVA
    REDUCIDO = "5"                 # 5% - Tasa reducida
    GENERAL = "10"                 # 10% - Tasa general


class UnidadMedidaEnum(str, Enum):
    """Unidades de medida comunes en Paraguay"""
    UNIDAD = "Unidad"              # Unidad por defecto
    KILOGRAMO = "Kilogramo"        # Peso
    METRO = "Metro"                # Longitud
    METRO_CUADRADO = "Metro cuadrado"  # Superficie
    METRO_CUBICO = "Metro cúbico"  # Volumen
    LITRO = "Litro"                # Líquidos
    BOLSA = "Bolsa"                # Cemento, harinas
    CAJA = "Caja"                  # Medicamentos, productos
    BALDE = "Balde"                # Pinturas, químicos
    SERVICIO = "Servicio"          # Servicios profesionales
    HORA = "Hora"                  # Servicios por tiempo
    PACK = "Pack"                  # Paquetes/conjuntos


# ===============================================
# HELPER FUNCTIONS
# ===============================================
# === validar precio ===
def validate_precio_paraguayo(precio: Optional[Decimal]) -> Optional[Decimal]:
    """
    Helper para validar precios según normativa Paraguay.

    Args:
        precio: Precio a validar (puede ser None para updates)

    Returns:
        Precio validado

    Raises:
        ValueError: Si precio no cumple normativa Paraguay
    """
    if precio is None:
        return None

    if precio < 0:
        raise ValueError('Precio no puede ser negativo')

    if precio > 99999999999:  # 99 mil millones (realista)
        raise ValueError('Precio excede límite máximo permitido')

    # Guaraníes no tienen centavos
    if precio != int(precio):
        raise ValueError('Precio en Guaraníes no puede tener centavos')

    return precio


def validate_descripcion(cls, v):
    """
    Valida y normaliza descripción del producto.

    Limpia espacios extra y valida caracteres permitidos para SIFEN.
    """
    # Limpiar espacios extra
    v = ' '.join(v.strip().split())

    # Caracteres no permitidos
    caracteres_prohibidos = [
        '<', '>', '{', '}', '[', ']', '|', '\\', '^', '~', '`']
    if any(char in v for char in caracteres_prohibidos):
        raise ValueError(
            'Descripción contiene caracteres no permitidos para SIFEN')

    return v.upper()  # Normalizar a mayúsculas para SIFEN


def validate_codigo_barras(cls, v):
    if v is not None and v.strip():
        v = v.strip()
        if v and not re.match(r'^[A-Z0-9\-]{6,20}$', v):
            raise ValueError(
                'Código de barras debe ser numérico de 8-14 dígitos'
            )
    return v


def validate_codigo_ncm(cls, v):
    if v is not None and v.strip():
        v = re.sub(r'[\s\.]', '', v.strip())
        if not re.match(r'^\d{8,10}$', v):
            raise ValueError('Código NCM debe tener 8-10 dígitos')
    return v


def validate_iva_consistency(cls, v, values):
    """Valida consistencia entre tasa IVA y afectación"""
    tasa_iva = values.get('tasa_iva')

    if tasa_iva and v:
        # Si es exento, tasa debe ser 0%
        if v == AfectacionIvaEnum.EXENTO and tasa_iva != TasaIvaEnum.EXENTO:
            raise ValueError(
                'Si afectación es EXENTO, tasa IVA debe ser 0%')

        # Si tasa es 0%, afectación debe ser exento
        if tasa_iva == TasaIvaEnum.EXENTO and v != AfectacionIvaEnum.EXENTO:
            raise ValueError(
                'Si tasa IVA es 0%, afectación debe ser EXENTO')

        # Si es gravado, tasa debe ser 5% o 10%
        if v == AfectacionIvaEnum.GRAVADO:
            if tasa_iva not in [TasaIvaEnum.REDUCIDO, TasaIvaEnum.GENERAL]:
                raise ValueError(
                    'Si afectación es GRAVADO, tasa IVA debe ser 5% o 10%')

    return v


def validate_stock_consistency(cls, v, values):
    """Valida consistencia del stock"""
    if v is not None:
        controla_stock = values.get('controla_stock', True)

        # Si controla stock, no puede ser negativo
        if controla_stock and v < 0:
            raise ValueError(
                'Stock actual no puede ser negativo si controla stock')

    return v

# ===============================================
# DTOs DE ENTRADA (REQUEST)
# ===============================================


class ProductoCreateDTO(BaseModel):
    """
    DTO para registro de nuevos productos/servicios.

    Valida datos requeridos para catálogo de productos
    compatible con documentos electrónicos SIFEN.

    Examples:
        ```python
        # POST /api/v1/productos
        producto_data = ProductoCreateDTO(
            codigo_interno="PROD001",
            descripcion="NOTEBOOK LENOVO THINKPAD",
            tipo_producto="producto",
            precio_unitario=5000000,
            tasa_iva="10",
            unidad_medida="Unidad"
        )
        ```
    """

    # === IDENTIFICACIÓN OBLIGATORIA ===
    codigo_interno: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Código interno único del producto/servicio"
    )

    descripcion: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Descripción detallada del producto/servicio"
    )

    # === CLASIFICACIÓN ===
    tipo_producto: TipoProductoEnum = Field(
        default=TipoProductoEnum.PRODUCTO,
        description="Tipo de producto o servicio"
    )

    unidad_medida: UnidadMedidaEnum = Field(
        default=UnidadMedidaEnum.UNIDAD,
        description="Unidad de medida"
    )

    # === PRECIOS E IMPUESTOS ===
    precio_unitario: Decimal = Field(
        ...,
        ge=0,
        description="Precio unitario en Guaraníes (sin IVA)"
    )

    tasa_iva: TasaIvaEnum = Field(
        default=TasaIvaEnum.GENERAL,
        description="Tasa de IVA aplicable (0%, 5%, 10%)"
    )

    afectacion_iva: AfectacionIvaEnum = Field(
        default=AfectacionIvaEnum.GRAVADO,
        description="Afectación de IVA según SIFEN"
    )

    # === CÓDIGOS OPCIONALES ===
    codigo_barras: Optional[str] = Field(
        None,
        max_length=50,
        description="Código de barras (EAN, UPC, etc.)"
    )

    codigo_ncm: Optional[str] = Field(
        None,
        min_length=8,
        max_length=10,
        description="Código NCM para productos físicos"
    )

    # === CONTROL DE INVENTARIO (OPCIONAL) ===
    controla_stock: bool = Field(
        default=True,
        description="Si controla stock del producto"
    )

    stock_actual: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Stock actual (solo referencial)"
    )

    stock_minimo: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Stock mínimo de alerta"
    )

    # === INFORMACIÓN ADICIONAL ===
    observaciones: Optional[str] = Field(
        None,
        max_length=1000,
        description="Observaciones adicionales del producto"
    )

    @validator('codigo_interno')
    def validate_codigo_interno(cls, v):
        """
        Valida formato del código interno.

        Debe ser alfanumérico, puede incluir guiones, puntos y guiones bajos.
        Se normaliza a mayúsculas para consistencia.
        """
        # Limpiar espacios
        v = v.strip().upper()

        # Validar formato: alfanumérico + algunos caracteres especiales
        if not re.match(r'^[A-Z0-9\-\._\/\#]{1,20}$', v):
            raise ValueError(
                'Código interno debe ser alfanumérico, puede incluir guiones, puntos y guiones bajos'
            )

        return v

    @validator('descripcion')
    def validate_descripcion(cls, v):
        """Valida y normaliza descripción del producto."""
        return validate_descripcion(cls, v)

    @validator('precio_unitario')
    def validate_precio_paraguay(cls, v):
        """Valida precio usando helper compartido"""
        return validate_precio_paraguayo(v)

    @validator('codigo_barras')
    def validate_codigo_barras(cls, v):
        """Valida formato del código de barras"""
        return validate_codigo_barras(cls, v)

    @validator('codigo_ncm')
    def validate_codigo_ncm(cls, v):
        """Valida formato del código NCM"""
        return validate_codigo_ncm(cls, v)

    @validator('afectacion_iva', always=True)
    def validate_iva_consistency(cls, v, values):
        """Valida consistencia entre tasa IVA y afectación"""
        return validate_iva_consistency(cls, v, values)

    @validator('stock_actual', always=True)
    def validate_stock_consistency(cls, v, values):
        """Valida consistencia del stock"""
        return validate_stock_consistency(cls, v, values)

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "codigo_interno": "PROD001",
                "descripcion": "NOTEBOOK LENOVO THINKPAD E14",
                "tipo_producto": "producto",
                "unidad_medida": "Unidad",
                "precio_unitario": "5000000",
                "tasa_iva": "10",
                "afectacion_iva": "1",
                "codigo_barras": "7891234567890",
                "codigo_ncm": "84713000",
                "controla_stock": True,
                "stock_actual": "10",
                "stock_minimo": "2",
                "observaciones": "Notebook empresarial con garantía 3 años"
            }
        }


class ProductoUpdateDTO(BaseModel):
    """
    DTO para actualización de productos existentes.

    Permite modificar datos del producto excepto código interno.
    Todos los campos son opcionales para updates parciales.

    Examples:
        ```python
        # PUT /api/v1/productos/{id}
        update_data = ProductoUpdateDTO(
            precio_unitario=5500000,
            stock_actual=15,
            observaciones="Precio actualizado por inflación"
        )
        ```
    """

    # === CÓDIGO INTERNO NO SE PUEDE CAMBIAR (OMITIDO) ===

    descripcion: Optional[str] = Field(
        None,
        min_length=3,
        max_length=500,
        description="Nueva descripción"
    )

    tipo_producto: Optional[TipoProductoEnum] = Field(
        None,
        description="Nuevo tipo de producto"
    )

    unidad_medida: Optional[UnidadMedidaEnum] = Field(
        None,
        description="Nueva unidad de medida"
    )

    precio_unitario: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Nuevo precio unitario"
    )

    tasa_iva: Optional[TasaIvaEnum] = Field(
        None,
        description="Nueva tasa de IVA"
    )

    afectacion_iva: Optional[AfectacionIvaEnum] = Field(
        None,
        description="Nueva afectación de IVA"
    )

    codigo_barras: Optional[str] = Field(
        None,
        max_length=50,
        description="Nuevo código de barras"
    )

    codigo_ncm: Optional[str] = Field(
        None,
        min_length=8,
        max_length=10,
        description="Nuevo código NCM"
    )

    controla_stock: Optional[bool] = Field(
        None,
        description="Cambiar control de stock"
    )

    stock_actual: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Actualizar stock actual"
    )

    stock_minimo: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Nuevo stock mínimo"
    )

    observaciones: Optional[str] = Field(
        None,
        max_length=1000,
        description="Nuevas observaciones"
    )

    # Reutilizar validadores de ProductoCreateDTO con lógica duplicada
    @validator('descripcion')
    def validate_descripcion(cls, v):
        """Valida y normaliza descripción del producto."""
        return validate_descripcion(cls, v)

    @validator('precio_unitario')
    def validate_precio_paraguay(cls, v):
        """Valida precio usando helper compartido"""
        return validate_precio_paraguayo(v)

    @validator('codigo_barras')
    def validate_codigo_barras(cls, v):
        if v is not None and v.strip():
            v = v.strip()
            if v and not re.match(r'^[A-Z0-9\-]{6,20}$', v):
                raise ValueError(
                    'Código de barras debe ser numérico de 8-14 dígitos'
                )
        return v

    @validator('codigo_ncm')
    def validate_codigo_ncm(cls, v):
        """Valida formato del código NCM"""
        return validate_codigo_ncm(cls, v)

    @validator('afectacion_iva', always=True)
    def validate_iva_consistency(cls, v, values):
        """Valida consistencia entre tasa IVA y afectación"""
        return validate_iva_consistency(cls, v, values)

    @validator('stock_actual', always=True)
    def validate_stock_consistency(cls, v, values):
        """Valida consistencia del stock"""
        return validate_stock_consistency(cls, v, values)

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "precio_unitario": "5500000",
                "stock_actual": "15",
                "observaciones": "Precio actualizado por inflación"
            }
        }


# ===============================================
# DTOs DE SALIDA (RESPONSE)
# ===============================================

class ProductoResponseDTO(BaseModel):
    """
    DTO para respuesta con datos completos de producto.

    Información completa del producto para APIs y frontend.
    Incluye precios, stock y metadata.

    Examples:
        ```python
        # GET /api/v1/productos/{id} response
        producto_response = ProductoResponseDTO(
            id=1,
            codigo_interno="PROD001",
            descripcion="NOTEBOOK LENOVO THINKPAD",
            precio_unitario=5000000,
            precio_con_iva=5500000,
            # ... resto de campos
        )
        ```
    """

    # === IDENTIFICACIÓN ===
    id: int = Field(..., description="ID único del producto")

    codigo_interno: str = Field(..., description="Código interno")

    descripcion: str = Field(..., description="Descripción del producto")

    # === CLASIFICACIÓN ===
    tipo_producto: str = Field(..., description="Tipo de producto")

    unidad_medida: str = Field(..., description="Unidad de medida")

    # === PRECIOS E IMPUESTOS ===
    precio_unitario: Decimal = Field(..., description="Precio sin IVA (Gs.)")

    tasa_iva: str = Field(..., description="Tasa de IVA (%)")

    afectacion_iva: str = Field(..., description="Afectación de IVA")

    # Campos calculados
    monto_iva: Optional[Decimal] = Field(
        None, description="Monto IVA por unidad (Gs.)"
    )

    precio_con_iva: Optional[Decimal] = Field(
        None, description="Precio con IVA incluido (Gs.)"
    )

    # === CÓDIGOS ===
    codigo_barras: Optional[str] = Field(
        None, description="Código de barras"
    )

    codigo_ncm: Optional[str] = Field(
        None, description="Código NCM"
    )

    # === INVENTARIO ===
    controla_stock: bool = Field(..., description="Si controla stock")

    stock_actual: Decimal = Field(..., description="Stock actual")

    stock_minimo: Decimal = Field(..., description="Stock mínimo")

    # Estado del stock (calculado)
    estado_stock: Optional[str] = Field(
        None, description="Estado del stock (OK/BAJO/AGOTADO)"
    )

    # === METADATA ===
    is_active: bool = Field(..., description="Si está activo")

    created_at: datetime = Field(..., description="Fecha de creación")

    updated_at: datetime = Field(..., description="Última actualización")

    empresa_id: int = Field(..., description="ID empresa propietaria")

    observaciones: Optional[str] = Field(
        None, description="Observaciones"
    )

    # === INFORMACIÓN ADICIONAL ===
    veces_facturado: Optional[int] = Field(
        None, description="Número de veces facturado"
    )

    ultima_facturacion: Optional[datetime] = Field(
        None, description="Fecha última facturación"
    )

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "codigo_interno": "PROD001",
                "descripcion": "NOTEBOOK LENOVO THINKPAD E14",
                "tipo_producto": "producto",
                "unidad_medida": "Unidad",
                "precio_unitario": "5000000",
                "tasa_iva": "10",
                "afectacion_iva": "1",
                "monto_iva": "500000",
                "precio_con_iva": "5500000",
                "codigo_barras": "7891234567890",
                "codigo_ncm": "84713000",
                "controla_stock": True,
                "stock_actual": "10",
                "stock_minimo": "2",
                "estado_stock": "OK",
                "is_active": True,
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:30:00",
                "empresa_id": 1,
                "observaciones": "Notebook empresarial con garantía 3 años",
                "veces_facturado": 25,
                "ultima_facturacion": "2025-01-14T15:20:00"
            }
        }


class ProductoListDTO(BaseModel):
    """
    DTO para elemento en lista de productos.

    Versión compacta de ProductoResponseDTO para listados
    que requieren menos información por performance.

    Examples:
        ```python
        # GET /api/v1/productos response (lista)
        productos_list = [
            ProductoListDTO(
                id=1,
                codigo_interno="PROD001",
                descripcion="NOTEBOOK LENOVO THINKPAD",
                precio_unitario=5000000,
                stock_actual=10,
                is_active=True
            )
        ]
        ```
    """

    id: int = Field(..., description="ID único del producto")

    codigo_interno: str = Field(..., description="Código interno")

    descripcion: str = Field(..., description="Descripción")

    tipo_producto: str = Field(..., description="Tipo de producto")

    precio_unitario: Decimal = Field(..., description="Precio sin IVA")

    tasa_iva: str = Field(..., description="Tasa de IVA")

    stock_actual: Decimal = Field(..., description="Stock actual")

    estado_stock: Optional[str] = Field(
        None, description="Estado del stock"
    )

    is_active: bool = Field(..., description="Si está activo")

    created_at: datetime = Field(..., description="Fecha de creación")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "codigo_interno": "PROD001",
                "descripcion": "NOTEBOOK LENOVO THINKPAD E14",
                "tipo_producto": "producto",
                "precio_unitario": "5000000",
                "tasa_iva": "10",
                "stock_actual": "10",
                "estado_stock": "OK",
                "is_active": True,
                "created_at": "2025-01-15T10:30:00"
            }
        }


# ===============================================
# DTOs ESPECIALIZADOS
# ===============================================

class ProductoCatalogoDTO(BaseModel):
    """
    DTO para catálogo público de productos.

    Información básica de productos para mostrar en
    catálogos públicos o interfaces de selección.

    Examples:
        ```python
        # GET /api/v1/productos/catalogo response
        catalogo = [
            ProductoCatalogoDTO(
                id=1,
                codigo_interno="PROD001",
                descripcion="NOTEBOOK LENOVO THINKPAD",
                precio_con_iva=5500000,
                disponible=True
            )
        ]
        ```
    """

    id: int = Field(..., description="ID único del producto")

    codigo_interno: str = Field(..., description="Código interno")

    descripcion: str = Field(..., description="Descripción")

    unidad_medida: str = Field(..., description="Unidad de medida")

    precio_unitario: Decimal = Field(..., description="Precio sin IVA")

    precio_con_iva: Decimal = Field(..., description="Precio con IVA")

    tasa_iva: str = Field(..., description="Tasa de IVA")

    disponible: bool = Field(..., description="Si está disponible")

    stock_disponible: Optional[Decimal] = Field(
        None, description="Stock disponible (si controla stock)"
    )

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "codigo_interno": "PROD001",
                "descripcion": "NOTEBOOK LENOVO THINKPAD E14",
                "unidad_medida": "Unidad",
                "precio_unitario": "5000000",
                "precio_con_iva": "5500000",
                "tasa_iva": "10",
                "disponible": True,
                "stock_disponible": "10"
            }
        }


class ProductoStatsDTO(BaseModel):
    """
    DTO para estadísticas de producto.

    Métricas y estadísticas de facturación del producto
    útiles para análisis de ventas y stock.

    Examples:
        ```python
        # GET /api/v1/productos/{id}/stats response
        producto_stats = ProductoStatsDTO(
            producto_id=1,
            veces_facturado=25,
            cantidad_total_vendida=50,
            monto_total_vendido=250000000,
            ultima_venta="2025-01-14T15:20:00"
        )
        ```
    """

    producto_id: int = Field(..., description="ID del producto")

    # === ESTADÍSTICAS VENTAS ===
    veces_facturado: int = Field(
        default=0,
        description="Número de veces facturado"
    )

    cantidad_total_vendida: Decimal = Field(
        default=Decimal("0"),
        description="Cantidad total vendida"
    )

    monto_total_vendido: Decimal = Field(
        default=Decimal("0"),
        description="Monto total vendido (sin IVA)"
    )

    monto_iva_generado: Decimal = Field(
        default=Decimal("0"),
        description="Total IVA generado por el producto"
    )

    # === FECHAS ===
    ultima_venta: Optional[datetime] = Field(
        None,
        description="Fecha de última venta"
    )

    primera_venta: Optional[datetime] = Field(
        None,
        description="Fecha de primera venta"
    )

    # === PROMEDIOS ===
    cantidad_promedio_por_venta: Decimal = Field(
        default=Decimal("0"),
        description="Cantidad promedio por venta"
    )

    frecuencia_ventas_mes: float = Field(
        default=0.0,
        description="Ventas promedio por mes"
    )

    # === STOCK ===
    rotacion_stock: Optional[float] = Field(
        None,
        description="Rotación de stock (veces por año)"
    )

    dias_stock_actual: Optional[int] = Field(
        None,
        description="Días de stock con venta promedio"
    )

    class Config:
        schema_extra = {
            "example": {
                "producto_id": 1,
                "veces_facturado": 25,
                "cantidad_total_vendida": "50",
                "monto_total_vendido": "250000000",
                "monto_iva_generado": "25000000",
                "ultima_venta": "2025-01-14T15:20:00",
                "primera_venta": "2024-06-15T10:30:00",
                "cantidad_promedio_por_venta": "2",
                "frecuencia_ventas_mes": 3.2,
                "rotacion_stock": 6.5,
                "dias_stock_actual": 56
            }
        }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # === ENUMS ===
    "TipoProductoEnum",
    "AfectacionIvaEnum",
    "TasaIvaEnum",
    "UnidadMedidaEnum",

    # === DTOs DE ENTRADA ===
    "ProductoCreateDTO",
    "ProductoUpdateDTO",

    # === DTOs DE SALIDA ===
    "ProductoResponseDTO",
    "ProductoListDTO",

    # === DTOs ESPECIALIZADOS ===
    "ProductoCatalogoDTO",
    "ProductoStatsDTO"
]
