"""
Modelos para el módulo de firma digital
"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class Certificate(BaseModel):
    """Modelo para certificados digitales según SIFEN"""
    ruc: str = Field(..., description="RUC del titular del certificado")
    serial_number: str = Field(...,
                               description="Número de serie del certificado")
    valid_from: datetime = Field(..., description="Fecha de inicio de validez")
    valid_to: datetime = Field(..., description="Fecha de fin de validez")
    certificate_path: str = Field(...,
                                  description="Ruta al archivo del certificado")
    password: Optional[str] = Field(
        None, description="Contraseña del certificado (si aplica)")

    @field_validator('ruc')
    @classmethod
    def validate_ruc(cls, v: str) -> str:
        """Validar formato de RUC"""
        if not v.replace('-', '').isdigit():
            raise ValueError("RUC debe contener solo números y guiones")
        return v

    @field_validator('valid_to')
    @classmethod
    def validate_dates(cls, v: datetime, info) -> datetime:
        """Validar que la fecha de fin sea posterior a la de inicio"""
        valid_from = info.data.get('valid_from')
        if valid_from and v <= valid_from:
            raise ValueError(
                "La fecha de fin debe ser posterior a la fecha de inicio")
        return v


class SignatureResult(BaseModel):
    """Modelo para el resultado de la firma digital"""
    success: bool = Field(..., description="Indica si la firma fue exitosa")
    error: Optional[str] = Field(
        None, description="Mensaje de error si la firma falló")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Fecha y hora de la firma")
    signature: Optional[str] = Field(
        None, description="Firma digital en base64")
    certificate_serial: Optional[str] = Field(
        None, description="Número de serie del certificado usado")
    signature_algorithm: Optional[str] = Field(
        None, description="Algoritmo usado para la firma")
