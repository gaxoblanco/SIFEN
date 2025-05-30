"""
Fixtures comunes para tests de firma digital
"""
import pytest
from pathlib import Path
from ..certificate_manager import CertificateManager
from ..config import CertificateConfig, DigitalSignConfig


@pytest.fixture
def cert_config():
    """Fixture con configuración de certificado"""
    return CertificateConfig(
        cert_path=Path(
            "backend/app/services/digital_sign/tests/fixtures/test.pfx"),
        cert_password="test123",
        cert_expiry_days=30
    )


@pytest.fixture
def cert_manager(cert_config):
    """Fixture con gestor de certificados"""
    return CertificateManager(cert_config)


@pytest.fixture
def sign_config():
    """Fixture con configuración de firma"""
    return DigitalSignConfig(
        signature_algorithm="RSA-SHA256",
        digest_algorithm="SHA256"
    )
