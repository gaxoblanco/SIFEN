"""
Modelos para la generación de XML SIFEN
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional
from decimal import Decimal


class Contribuyente(BaseModel):
    """Datos del contribuyente (emisor o receptor)"""
    ruc: str = Field(..., min_length=8, max_length=9)
    dv: str = Field(..., min_length=1, max_length=1)
    razon_social: str = Field(..., min_length=1, max_length=100)
    direccion: str = Field(..., min_length=1, max_length=100)
    numero_casa: str = Field(..., min_length=1, max_length=10)
    codigo_departamento: str = Field(..., min_length=1, max_length=3)
    codigo_ciudad: str = Field(..., min_length=1, max_length=3)
    descripcion_ciudad: str = Field(..., min_length=1, max_length=50)
    telefono: str = Field(..., min_length=1, max_length=20)
    email: str = Field(..., min_length=1, max_length=100)


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
        ..., pattern="^[1-5]$")  # 1: Factura, 2: Autofactura, 3: Nota Crédito, 4: Nota Débito, 5: Nota Remisión
    numero_documento: str = Field(..., min_length=1, max_length=20)
    fecha_emision: datetime
    emisor: Contribuyente
    receptor: Contribuyente
    items: List[ItemFactura] = Field(..., min_length=1)
    total_iva: Decimal
    total_gravada: Decimal
    total_exenta: Decimal = Field(..., ge=0)
    total_general: Decimal
    moneda: str = Field(..., pattern="^(PYG|USD)$")
    tipo_cambio: Optional[Decimal] = Field(None, gt=0)  # Solo si moneda es USD

    @field_validator('total_iva', 'total_gravada', 'total_general')
    def validate_negative_amounts(cls, v, values):
        """Permite montos negativos solo para notas de crédito (tipo 3)"""
        tipo_doc = values.data.get('tipo_documento') if hasattr(
            values, 'data') else values.get('tipo_documento')
        if tipo_doc == '3':
            return v  # Permite cualquier valor para notas de crédito
        if v < 0:
            raise ValueError(
                'Los montos no pueden ser negativos para este tipo de documento')
        return v
