"""
Tests para validar la función _extract_ruc_from_certificate
Módulo: backend/app/services/digital_sign/tests/test_extract_ruc_from_certificate.py
"""
from ..config import CertificateConfig
from ..certificate_manager import CertificateManager
from ..certificate_manager import CertificateManager
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from pathlib import Path

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


class TestExtractRucFromCertificate:
    """Tests para la función _extract_ruc_from_certificate según SIFEN v150"""

    def setup_method(self):
        """Setup para cada test"""
        self.config = CertificateConfig(
            cert_path=Path("test_cert.pfx"),
            cert_password="test_password"
        )

    def test_extract_ruc_from_serial_number_persona_juridica(self):
        """Test: Extraer RUC desde SerialNumber para persona jurídica"""
        # Arrange
        cert = self._create_mock_certificate_with_serial_ruc("RUC80016875-1")
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc == "RUC80016875-1"

    def test_extract_ruc_from_subject_alternative_name_persona_fisica(self):
        """Test: Extraer RUC desde SubjectAlternativeName para persona física"""
        # Arrange
        cert = self._create_mock_certificate_with_san_ruc("RUC12345678-4")
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc == "RUC12345678-4"

    def test_extract_ruc_prioritizes_serial_number_over_san(self):
        """Test: Prioriza SerialNumber sobre SubjectAlternativeName"""
        # Arrange
        cert = self._create_mock_certificate_with_both_rucs(
            serial_ruc="RUC80016875-1",
            san_ruc="RUC87654321-5"
        )
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc == "RUC80016875-1"  # Debe priorizar SerialNumber

    def test_extract_ruc_not_found_returns_none(self):
        """Test: Retorna None cuando no encuentra RUC"""
        # Arrange
        cert = self._create_mock_certificate_without_ruc()
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc is None

    def test_extract_ruc_invalid_format_returns_none(self):
        """Test: Retorna None cuando el formato de RUC es inválido"""
        # Arrange
        cert = self._create_mock_certificate_with_serial_ruc("INVALID_FORMAT")
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc is None

    def test_extract_ruc_handles_exception_gracefully(self):
        """Test: Maneja excepciones graciosamente"""
        # Arrange
        manager = CertificateManager(self.config)

        # Crear un certificado mock que lanza excepción al acceder a subject
        cert = Mock(spec=x509.Certificate)
        cert.subject.__iter__ = Mock(
            side_effect=Exception("Error accediendo a subject"))

        # Act & Assert
        ruc = manager._extract_ruc_from_certificate(cert)
        assert ruc is None

    def test_extract_ruc_with_extension_not_found_exception(self):
        """Test: Maneja ExtensionNotFound graciosamente"""
        # Arrange
        cert = self._create_mock_certificate_without_san()
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc is None

    def test_extract_ruc_validates_ruc_format_with_hyphen(self):
        """Test: Valida que el RUC contenga guión"""
        # Arrange
        cert = self._create_mock_certificate_with_serial_ruc(
            "RUC800168755")  # Sin guión
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc is None

    def test_extract_ruc_validates_ruc_starts_with_ruc(self):
        """Test: Valida que el RUC empiece con 'RUC'"""
        # Arrange
        cert = self._create_mock_certificate_with_serial_ruc(
            "80016875-5")  # Sin RUC prefix
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc is None

    def test_extract_ruc_multiple_serial_attributes_picks_ruc(self):
        """Test: Selecciona el atributo que contiene RUC entre múltiples SerialNumber"""
        # Arrange
        cert = self._create_mock_certificate_with_multiple_serial_attributes()
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc == "RUC80016875-1"

    def test_extract_ruc_san_with_multiple_names(self):
        """Test: Extrae RUC de SAN con múltiples nombres"""
        # Arrange
        cert = self._create_mock_certificate_with_multiple_san_names()
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        ruc = manager._extract_ruc_from_certificate(cert)

        # Assert
        assert ruc == "RUC12345678-4"

    def test_extract_ruc_integration_with_validate_for_sifen(self):
        """Test: Integración con validate_for_sifen - RUC encontrado"""
        # Arrange
        cert = self._create_real_test_certificate_with_ruc("RUC80016875-1")
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        validation_result = manager.validate_for_sifen()

        # Assert
        assert "No se encontró RUC en el certificado" not in validation_result['errors']

    def test_extract_ruc_integration_with_validate_for_sifen_no_ruc(self):
        """Test: Integración con validate_for_sifen - RUC no encontrado"""
        # Arrange
        cert = self._create_real_test_certificate_without_ruc()
        manager = self._create_manager_with_mock_cert(cert)

        # Act
        validation_result = manager.validate_for_sifen()

        # Assert
        assert "No se encontró RUC en el certificado" in validation_result['errors']
        assert validation_result['valid'] is False

    # Métodos helper para crear certificados mock
    def _create_manager_with_mock_cert(self, cert):
        """Crea CertificateManager con certificado mockeado"""
        manager = CertificateManager(self.config)
        manager._certificate = cert
        return manager

    def _create_mock_certificate_with_serial_ruc(self, ruc: str):
        """Mock de certificado con RUC en SerialNumber"""
        cert = Mock(spec=x509.Certificate)

        # Mock subject con RUC en SerialNumber
        serial_attr = Mock()
        serial_attr.oid = NameOID.SERIAL_NUMBER
        serial_attr.value = ruc

        other_attr = Mock()
        other_attr.oid = NameOID.COMMON_NAME
        other_attr.value = "Test Certificate"

        cert.subject = [serial_attr, other_attr]

        # Mock extensions sin SubjectAlternativeName
        cert.extensions.get_extension_for_oid.side_effect = x509.ExtensionNotFound(
            "Extension not found", ExtensionOID.SUBJECT_ALTERNATIVE_NAME)

        return cert

    def _create_mock_certificate_with_san_ruc(self, ruc: str):
        """Mock de certificado con RUC en SubjectAlternativeName"""
        cert = Mock(spec=x509.Certificate)

        # Mock subject sin SerialNumber con RUC
        other_attr = Mock()
        other_attr.oid = NameOID.COMMON_NAME
        other_attr.value = "Test Certificate"

        cert.subject = [other_attr]

        # Mock SubjectAlternativeName con RUC
        san_name = Mock()
        san_name.value = ruc

        san_extension = Mock()
        san_extension.value = [san_name]

        def mock_get_extension(oid):
            if oid == ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
                return san_extension
            raise x509.ExtensionNotFound("Extension not found", oid)

        cert.extensions.get_extension_for_oid.side_effect = mock_get_extension

        return cert

    def _create_mock_certificate_with_both_rucs(self, serial_ruc: str, san_ruc: str):
        """Mock de certificado con RUC en ambos lugares"""
        cert = Mock(spec=x509.Certificate)

        # Mock subject con RUC en SerialNumber
        serial_attr = Mock()
        serial_attr.oid = NameOID.SERIAL_NUMBER
        serial_attr.value = serial_ruc

        cert.subject = [serial_attr]

        # Mock SubjectAlternativeName con otro RUC
        san_name = Mock()
        san_name.value = san_ruc

        san_extension = Mock()
        san_extension.value = [san_name]

        def mock_get_extension(oid):
            if oid == ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
                return san_extension
            raise x509.ExtensionNotFound("Extension not found", oid)

        cert.extensions.get_extension_for_oid.side_effect = mock_get_extension

        return cert

    def _create_mock_certificate_without_ruc(self):
        """Mock de certificado sin RUC"""
        cert = Mock(spec=x509.Certificate)

        # Mock subject sin RUC
        other_attr = Mock()
        other_attr.oid = NameOID.COMMON_NAME
        other_attr.value = "Test Certificate"

        cert.subject = [other_attr]

        # Mock extensions sin SubjectAlternativeName
        cert.extensions.get_extension_for_oid.side_effect = x509.ExtensionNotFound(
            "Extension not found", ExtensionOID.SUBJECT_ALTERNATIVE_NAME)

        return cert

    def _create_mock_certificate_without_san(self):
        """Mock de certificado sin SubjectAlternativeName"""
        cert = Mock(spec=x509.Certificate)

        # Mock subject sin SerialNumber con RUC
        other_attr = Mock()
        other_attr.oid = NameOID.COMMON_NAME
        other_attr.value = "Test Certificate"

        cert.subject = [other_attr]

        # Mock extensions que lanza ExtensionNotFound
        cert.extensions.get_extension_for_oid.side_effect = x509.ExtensionNotFound(
            "Extension not found", ExtensionOID.SUBJECT_ALTERNATIVE_NAME)

        return cert

    def _create_mock_certificate_with_multiple_serial_attributes(self):
        """Mock de certificado con múltiples atributos SerialNumber"""
        cert = Mock(spec=x509.Certificate)

        # Mock múltiples atributos en subject
        serial_attr1 = Mock()
        serial_attr1.oid = NameOID.SERIAL_NUMBER
        serial_attr1.value = "123456"

        serial_attr2 = Mock()
        serial_attr2.oid = NameOID.SERIAL_NUMBER
        serial_attr2.value = "RUC80016875-1"

        other_attr = Mock()
        other_attr.oid = NameOID.COMMON_NAME
        other_attr.value = "Test Certificate"

        cert.subject = [serial_attr1, serial_attr2, other_attr]

        # Mock extensions sin SubjectAlternativeName
        cert.extensions.get_extension_for_oid.side_effect = x509.ExtensionNotFound(
            "Extension not found", ExtensionOID.SUBJECT_ALTERNATIVE_NAME)

        return cert

    def _create_mock_certificate_with_multiple_san_names(self):
        """Mock de certificado con múltiples nombres en SAN"""
        cert = Mock(spec=x509.Certificate)

        # Mock subject sin RUC
        other_attr = Mock()
        other_attr.oid = NameOID.COMMON_NAME
        other_attr.value = "Test Certificate"

        cert.subject = [other_attr]

        # Mock múltiples nombres en SAN
        san_name1 = Mock()
        san_name1.value = "email@example.com"

        san_name2 = Mock()
        san_name2.value = "RUC12345678-4"

        san_extension = Mock()
        san_extension.value = [san_name1, san_name2]

        def mock_get_extension(oid):
            if oid == ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
                return san_extension
            raise x509.ExtensionNotFound("Extension not found", oid)

        cert.extensions.get_extension_for_oid.side_effect = mock_get_extension

        return cert

    def _create_real_test_certificate_with_ruc(self, ruc: str):
        """Crea certificado real de prueba con RUC"""
        # Generar clave privada
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Crear certificado con RUC en SerialNumber
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PY"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Central"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Asunción"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Test Certificate"),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, ruc),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now()
        ).not_valid_after(
            datetime.now() + timedelta(days=365)
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        return cert

    def _create_real_test_certificate_without_ruc(self):
        """Crea certificado real de prueba sin RUC"""
        # Generar clave privada
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Crear certificado SIN RUC
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PY"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Central"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Asunción"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Test Certificate"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now()
        ).not_valid_after(
            datetime.now() + timedelta(days=365)
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        return cert


class TestExtractRucEdgeCases:
    """Tests de casos edge específicos para SIFEN"""

    def setup_method(self):
        """Setup para cada test"""
        self.config = CertificateConfig(
            cert_path=Path("test_cert.pfx"),
            cert_password="test_password"
        )

    def test_extract_ruc_with_different_ruc_formats(self):
        """Test: Diferentes formatos válidos de RUC"""
        valid_ruc_formats = [
            "RUC80016875-1",
            "RUC12345678-4",
            "RUC87654321-5",
            "RUC11111111-1"
        ]

        for ruc in valid_ruc_formats:
            cert = self._create_mock_certificate_with_ruc(ruc)
            manager = CertificateManager(self.config)
            manager._certificate = cert

            extracted_ruc = manager._extract_ruc_from_certificate(cert)
            assert extracted_ruc == ruc

    def test_extract_ruc_with_invalid_ruc_formats(self):
        """Test: Formatos inválidos de RUC"""
        invalid_ruc_formats = [
            "800168755",      # Sin RUC prefix
            "RUC80016875",    # Sin guión
            "RUC-80016875-5",  # Guión extra
            "RUC80016875-9",  # Dígito verificador incorrecto
            "RUC80016875-",   # Sin dígito verificador
            "RUC-5",          # Solo dígito verificador
        ]

        for invalid_ruc in invalid_ruc_formats:
            cert = self._create_mock_certificate_with_ruc(invalid_ruc)
            manager = CertificateManager(self.config)
            manager._certificate = cert

            extracted_ruc = manager._extract_ruc_from_certificate(cert)
            assert extracted_ruc is None

    def test_extract_ruc_with_san_exception_handling(self):
        """Test: Manejo de excepciones en SubjectAlternativeName"""
        cert = Mock(spec=x509.Certificate)

        # Mock subject sin RUC
        other_attr = Mock()
        other_attr.oid = NameOID.COMMON_NAME
        other_attr.value = "Test Certificate"
        cert.subject = [other_attr]

        # Mock que lanza excepción al acceder a SAN
        def mock_get_extension_with_error(oid):
            if oid == ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
                raise ValueError("Error procesando SAN")
            raise x509.ExtensionNotFound("Extension not found", oid)

        cert.extensions.get_extension_for_oid.side_effect = mock_get_extension_with_error

        manager = CertificateManager(self.config)
        manager._certificate = cert

        # No debe lanzar excepción, debe retornar None
        extracted_ruc = manager._extract_ruc_from_certificate(cert)
        assert extracted_ruc is None

    def _create_mock_certificate_with_ruc(self, ruc: str):
        """Helper para crear mock de certificado con RUC específico"""
        cert = Mock(spec=x509.Certificate)

        serial_attr = Mock()
        serial_attr.oid = NameOID.SERIAL_NUMBER
        serial_attr.value = ruc

        cert.subject = [serial_attr]
        cert.extensions.get_extension_for_oid.side_effect = x509.ExtensionNotFound(
            "Extension not found", ExtensionOID.SUBJECT_ALTERNATIVE_NAME)

        return cert


# Fixtures para pytest
@pytest.fixture
def certificate_config():
    """Fixture para configuración de certificado"""
    return CertificateConfig(
        cert_path=Path("test_cert.pfx"),
        cert_password="test_password",
        cert_expiry_days=30
    )


@pytest.fixture
def mock_certificate_with_ruc():
    """Fixture para certificado mock con RUC válido"""
    cert = Mock(spec=x509.Certificate)

    serial_attr = Mock()
    serial_attr.oid = NameOID.SERIAL_NUMBER
    serial_attr.value = "RUC80016875-1"

    cert.subject = [serial_attr]
    cert.extensions.get_extension_for_oid.side_effect = x509.ExtensionNotFound(
        "Extension not found", ExtensionOID.SUBJECT_ALTERNATIVE_NAME)

    return cert


@pytest.fixture
def mock_certificate_without_ruc():
    """Fixture para certificado mock sin RUC"""
    cert = Mock(spec=x509.Certificate)

    other_attr = Mock()
    other_attr.oid = NameOID.COMMON_NAME
    other_attr.value = "Test Certificate"

    cert.subject = [other_attr]
    cert.extensions.get_extension_for_oid.side_effect = x509.ExtensionNotFound(
        "Extension not found", ExtensionOID.SUBJECT_ALTERNATIVE_NAME)

    return cert


# Tests usando fixtures
def test_extract_ruc_with_fixture(certificate_config, mock_certificate_with_ruc):
    """Test usando fixtures de pytest"""
    manager = CertificateManager(certificate_config)
    manager._certificate = mock_certificate_with_ruc

    ruc = manager._extract_ruc_from_certificate(mock_certificate_with_ruc)

    assert ruc == "RUC80016875-1"


def test_extract_ruc_no_ruc_with_fixture(certificate_config, mock_certificate_without_ruc):
    """Test usando fixtures de pytest - sin RUC"""
    manager = CertificateManager(certificate_config)
    manager._certificate = mock_certificate_without_ruc

    ruc = manager._extract_ruc_from_certificate(mock_certificate_without_ruc)

    assert ruc is None


if __name__ == "__main__":
    # Ejecutar tests si se ejecuta directamente
    pytest.main([__file__, "-v", "--tb=short"])
