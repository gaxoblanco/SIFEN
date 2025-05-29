"""
Tests para el firmador digital
"""
import os
import pytest
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
from ..models import Certificate
from ..signer import DigitalSigner


@pytest.fixture
def test_certificate(tmp_path):
    """Fixture para crear un certificado de prueba"""
    # Crear clave privada RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Crear certificado
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Test Certificate"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).sign(private_key, hashes.SHA256())

    # Guardar certificado y clave privada en formato PKCS12
    cert_path = tmp_path / "test_cert.p12"

    # Crear archivo PKCS12
    from cryptography.hazmat.primitives.serialization import pkcs12
    p12 = pkcs12.serialize_key_and_certificates(
        name=b"test_cert",
        key=private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(
            b"test_password")
    )

    with open(cert_path, 'wb') as f:
        f.write(p12)

    return Certificate(
        ruc="12345678-9",
        serial_number="1234567890",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=365),
        certificate_path=str(cert_path),
        password="test_password"
    )


def test_signer_initialization(test_certificate):
    """Test para inicializar el firmador"""
    signer = DigitalSigner(test_certificate)
    assert signer.certificate == test_certificate


def test_sign_xml(test_certificate):
    """Test para firmar un documento XML"""
    signer = DigitalSigner(test_certificate)
    xml_content = "<test>contenido</test>"

    result = signer.sign_xml(xml_content)
    assert result.success
    assert result.signature is not None
    assert result.certificate_serial == test_certificate.serial_number


def test_verify_signature(test_certificate):
    """Test para verificar una firma"""
    signer = DigitalSigner(test_certificate)
    xml_content = "<test>contenido</test>"

    # Firmar el documento
    result = signer.sign_xml(xml_content)
    assert result.success

    # Verificar la firma
    is_valid = signer.verify_signature(xml_content, result.signature)
    assert is_valid


def test_invalid_signature(test_certificate):
    """Test para verificar firma inválida"""
    signer = DigitalSigner(test_certificate)
    xml_content = "<test>contenido</test>"

    # Intentar verificar con una firma inválida
    invalid_signature = "firma_invalida"  # Esto es un string válido
    is_valid = signer.verify_signature(xml_content, invalid_signature)
    assert not is_valid
