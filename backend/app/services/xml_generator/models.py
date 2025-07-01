# """
# Deprecado
# """
# from pydantic import BaseModel, Field, field_validator
# from datetime import datetime
# from typing import List, Optional
# from decimal import Decimal
# import re


# class Contribuyente(BaseModel):
#     """Datos del contribuyente (emisor o receptor)"""
#     ruc: str = Field(..., min_length=8, max_length=9)
#     dv: str = Field(..., min_length=1, max_length=1)
#     razon_social: str = Field(..., min_length=1, max_length=100)
#     direccion: str = Field(..., min_length=1, max_length=100)
#     numero_casa: str = Field(..., min_length=1, max_length=10)
#     codigo_departamento: str = Field(..., min_length=1, max_length=3)
#     codigo_ciudad: str = Field(..., min_length=1, max_length=3)
#     descripcion_ciudad: str = Field(..., min_length=1, max_length=50)
#     telefono: str = Field(..., min_length=1, max_length=20)
#     email: str = Field(..., min_length=1, max_length=100)

#     @field_validator('ruc')
#     def validate_ruc(cls, v):
#         """Valida formato RUC"""
#         if not re.match(r'^\d{8,9}$', v):
#             raise ValueError('RUC debe contener solo números (8-9 dígitos)')
#         return v

#     @field_validator('dv')
#     def validate_dv(cls, v):
#         """Valida dígito verificador"""
#         if not re.match(r'^\d$', v):
#             raise ValueError('DV debe ser un dígito')
#         return v

#     @field_validator('email')
#     def validate_email(cls, v):
#         """Valida formato email"""
#         if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
#             raise ValueError('Email inválido')
#         return v


# class ItemFactura(BaseModel):
#     """Item de la factura"""
#     codigo: str = Field(..., min_length=1, max_length=20)
#     descripcion: str = Field(..., min_length=1, max_length=100)
#     cantidad: Decimal = Field(..., gt=0)
#     precio_unitario: Decimal = Field(..., gt=0)
#     iva: Decimal = Field(..., ge=0, le=100)
#     monto_total: Decimal = Field(..., gt=0)

#     @field_validator('monto_total')
#     def validate_monto_total(cls, v, info):
#         """Valida que el monto total sea correcto"""
#         if 'cantidad' in info.data and 'precio_unitario' in info.data:
#             expected = info.data['cantidad'] * info.data['precio_unitario']
#             if abs(v - expected) > Decimal('0.01'):  # Tolerancia para redondeo
#                 raise ValueError(
#                     'Monto total no coincide con cantidad * precio unitario')
#         return v


# class FacturaSimple(BaseModel):
#     """Datos básicos de una factura simple"""
#     tipo_documento: str = Field(
#         ..., pattern="^[1-5]$")  # 1: Factura, 2: Autofactura, 3: Nota Crédito, 4: Nota Débito, 5: Nota Remisión
#     numero_documento: str = Field(..., min_length=1, max_length=20)
#     fecha_emision: datetime
#     emisor: Contribuyente
#     receptor: Contribuyente
#     items: List[ItemFactura] = Field(..., min_length=1)
#     total_iva: Decimal
#     total_gravada: Decimal
#     total_exenta: Decimal = Field(..., ge=0)
#     total_general: Decimal
#     moneda: str = Field("PYG", pattern="^(PYG|USD|EUR|BRL)$")
#     tipo_cambio: Decimal = Field(Decimal("1.00"), ge=0.01, le=999999.99)
#     # Código Seguridad Contribuyente
#     csc: str = Field(..., pattern="^[A-Z0-9]{8}$")
#     condicion_venta: str = Field(
#         "1", pattern="^[1-2]$")  # 1: Contado, 2: Crédito
#     condicion_operacion: str = Field(
#         "1", pattern="^[1-2]$")  # 1: Normal, 2: Contingencia
#     # 1: Terrestre, 2: Marítimo, 3: Aéreo
#     modalidad_transporte: str = Field("1", pattern="^[1-3]$")
#     # 1: Normal, 2: Régimen Especial
#     categoria_emisor: str = Field("1", pattern="^[1-2]$")

#     @field_validator('total_iva', 'total_gravada', 'total_general')
#     def validate_negative_amounts(cls, v, info):
#         """Permite montos negativos solo para notas de crédito (tipo 3)"""
#         tipo_doc = info.data.get('tipo_documento')
#         if tipo_doc == '3':
#             return v  # Permite cualquier valor para notas de crédito
#         if v < 0:
#             raise ValueError(
#                 'Los montos no pueden ser negativos para este tipo de documento')
#         return v

#     @field_validator('tipo_cambio')
#     def validate_tipo_cambio(cls, v, info):
#         """Valida que tipo_cambio sea 1.00 para PYG y requerido para otras monedas"""
#         moneda = info.data.get('moneda')
#         if moneda == 'PYG' and v != Decimal('1.00'):
#             raise ValueError('tipo_cambio debe ser 1.00 cuando moneda es PYG')
#         if moneda != 'PYG' and v is None:
#             raise ValueError(
#                 'tipo_cambio es requerido cuando moneda no es PYG')
#         return v

#     @field_validator('total_general')
#     def validate_total_general(cls, v, info):
#         """Valida que el total general sea la suma correcta"""
#         if 'total_gravada' in info.data and 'total_exenta' in info.data and 'total_iva' in info.data:
#             expected = info.data['total_gravada'] + \
#                 info.data['total_exenta'] + info.data['total_iva']
#             if abs(v - expected) > Decimal('0.01'):  # Tolerancia para redondeo
#                 raise ValueError(
#                     'Total general no coincide con la suma de los subtotales')
#         return v
