"""
Tests para el gestor de certificados
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from ..certificate_manager import CertificateManager
from ..config import CertificateConfig


def test_validate_certificate_valid(certificate_manager):
    """Test que valida un certificado válido"""
    assert certificate_manager.validate_certificate() is True


def test_validate_certificate_none(certificate_manager):
    """Test que valida cuando no hay certificado"""
    certificate_manager._certificate = None
    assert certificate_manager.validate_certificate() is False


def test_validate_certificate_expired(certificate_manager):
    """Test que valida un certificado expirado"""
    # Modificar la fecha de expiración a una fecha pasada
    certificate_manager._certificate.not_valid_after_utc = datetime.now() - \
        timedelta(days=1)
    assert certificate_manager.validate_certificate() is False


def test_load_certificate(cert_manager):
    """Test carga de certificado"""
    cert, key = cert_manager.load_certificate()

    assert isinstance(cert, x509.Certificate)
    assert isinstance(key, rsa.RSAPrivateKey)


def test_certificate_not_found():
    """Test error cuando no existe certificado"""
    config = CertificateConfig(
        cert_path=Path("no_existe.pfx"),
        cert_password="test123",
        cert_expiry_days=30
    )
    manager = CertificateManager(config)

    with pytest.raises(ValueError, match="Certificado no encontrado"):
        manager.load_certificate()


def test_invalid_password(cert_config):
    """Test error con contraseña inválida"""
    config = CertificateConfig(
        cert_path=cert_config.cert_path,
        cert_password="wrong",
        cert_expiry_days=30
    )
    manager = CertificateManager(config)

    with pytest.raises(ValueError, match="Error al cargar el certificado"):
        manager.load_certificate()


def test_check_expiry(cert_manager):
    """Test verificación de expiración"""
    is_expiring, days_left = cert_manager.check_expiry()

    assert isinstance(is_expiring, bool)
    assert isinstance(days_left, timedelta)


def test_certificate_property(cert_manager):
    """Test propiedad certificate"""
    cert = cert_manager.certificate
    assert isinstance(cert, x509.Certificate)


def test_private_key_property(cert_manager):
    """Test propiedad private_key"""
    key = cert_manager.private_key
    assert isinstance(key, rsa.RSAPrivateKey)
