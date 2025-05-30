"""
Configuración del módulo de firma digital
"""
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class CertificateConfig(BaseModel):
    """Configuración de certificado"""
    cert_path: Path = Field(..., description="Ruta al archivo PFX")
    cert_password: str = Field(..., description="Contraseña del certificado")
    cert_expiry_days: int = Field(
        default=30,
        description="Días antes de expiración para alertar"
    )


class DigitalSignConfig(BaseModel):
    """Configuración de firma digital"""
    signature_algorithm: str = Field(
        default="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        description="Algoritmo de firma"
    )
    digest_algorithm: str = Field(
        default="http://www.w3.org/2001/04/xmlenc#sha256",
        description="Algoritmo de digest"
    )
    canonicalization_method: str = Field(
        default="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        description="Método de canonicalización"
    )
    transform_algorithm: str = Field(
        default="http://www.w3.org/2000/09/xmldsig#enveloped-signature",
        description="Algoritmo de transformación"
    )


# Configuración por defecto
DEFAULT_CONFIG = DigitalSignConfig()
