from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from decimal import Decimal


class Contribuyente(BaseModel):
    """Datos del contribuyente (emisor o receptor)"""
    ruc: str = Field(..., min_length=8, max_length=9)
    dv: str = Field(..., min_length=1, max_length=1)
    razon_social: str = Field(..., min_length=1, max_length=100)
    direccion: str = Field(..., min_length=1, max_length=100)
    telefono: Optional[str] = Field(None, min_length=1, max_length=20)
    email: Optional[str] = Field(None, min_length=1, max_length=100)


class ItemFactura(BaseModel):
    """Item de la factura"""
    codigo: str = Field(..., min_length=1, max_length=20)
    descripcion: str = Field(..., min_length=1, max_length=100)
    cantidad: Decimal = Field(..., gt=0)
    precio_unitario: Decimal = Field(..., gt=0)
    iva: Decimal = Field(..., ge=0, le=100)
    monto_total: Decimal = Field(..., gt=0)


class FacturaSimple(BaseModel):
    """Datos básicos de una factura simple"""
    tipo_documento: str = Field(
        ..., pattern="^[1-3]$")  # 1: Factura, 2: Nota Crédito, 3: Nota Débito
    numero_documento: str = Field(..., min_length=1, max_length=20)
    fecha_emision: datetime
    emisor: Contribuyente
    receptor: Contribuyente
    items: List[ItemFactura] = Field(..., min_length=1)
    total_iva: Decimal = Field(..., ge=0)
    total_gravada: Decimal = Field(..., ge=0)
    total_exenta: Decimal = Field(..., ge=0)
    total_general: Decimal = Field(..., gt=0)
    moneda: str = Field(..., pattern="^(PYG|USD)$")
    tipo_cambio: Optional[Decimal] = Field(None, gt=0)  # Solo si moneda es USD
