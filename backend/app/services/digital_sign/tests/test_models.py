"""
Tests para los modelos de firma digital
"""
from datetime import datetime, timedelta
import pytest
from ..models import Certificate


def test_certificate_creation():
    """Test para crear un certificado válido"""
    cert = Certificate(
        ruc="12345678-9",
        serial_number="1234567890",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=365),
        certificate_path="/path/to/cert.p12",
        password=None
    )

    assert cert.ruc == "12345678-9"
    assert cert.serial_number == "1234567890"
    assert cert.certificate_path == "/path/to/cert.p12"


def test_certificate_invalid_ruc():
    """Test para validar RUC inválido"""
    with pytest.raises(ValueError, match="RUC debe contener solo números y guiones"):
        Certificate(
            ruc="12345678A",  # RUC inválido con letra
            serial_number="1234567890",
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=365),
            certificate_path="/path/to/cert.p12",
            password=None
        )


def test_certificate_invalid_dates():
    """Test para validar fechas inválidas"""
    now = datetime.now()
    with pytest.raises(ValueError, match="La fecha de fin debe ser posterior a la fecha de inicio"):
        Certificate(
            ruc="12345678-9",
            serial_number="1234567890",
            valid_from=now,
            valid_to=now - timedelta(days=1),  # Fecha de fin anterior a inicio
            certificate_path="/path/to/cert.p12",
            password=None
        )
