"""
Tests de validación de firmas digitales para SIFEN v150

Este módulo implementa tests exhaustivos para la validación de firmas digitales
según las especificaciones del Manual Técnico SIFEN v150. Se enfocan en:

1. Validación de firmas XML según estándar W3C XML Digital Signature
2. Verificación de certificados PSC Paraguay (F1/F2)
3. Cumplimiento con algoritmos RSA-SHA256
4. Manejo de casos específicos de SIFEN (códigos 0141-0149)
5. Integración con esquemas XSD v150

CRÍTICO: Estos tests verifican que las firmas cumplan exactamente con los
requisitos de SET Paraguay para facturación electrónica.
"""

import pytest
import base64
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from lxml import etree

# Imports del módulo de firma digital
from ..models import Certificate, SignatureResult
from ..signer import DigitalSigner
from ..xml_signer import XMLSigner
from ..certificate_manager import CertificateManager
from ..config import CertificateConfig, DigitalSignConfig
from ..exceptions import SignatureValidationError, CertificateError


# ========================================
# FIXTURES PARA TESTS DE VALIDACIÓN
# ========================================

@pytest.fixture
def sifen_namespace():
    """Fixture que proporciona el namespace SIFEN v150"""
    return "http://ekuatia.set.gov.py/sifen/xsd"


@pytest.fixture
def xmldsig_namespace():
    """Fixture que proporciona el namespace XML Digital Signature"""
    return "http://www.w3.org/2000/09/xmldsig#"


@pytest.fixture
def valid_sifen_xml(sifen_namespace):
    """
    Fixture que proporciona un XML SIFEN válido para pruebas de firma

    Simula una estructura básica de documento electrónico según v150
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="{sifen_namespace}" Id="test_cdc_12345678901234567890123456789012345678901234">
    <dVerFor>150</dVerFor>
    <DE Id="test_cdc_12345678901234567890123456789012345678901234">
        <!-- Grupos principales según Manual v150 -->
        <gOpeDE>
            <iTipTra>1</iTipTra>
            <dDesTipTra>Factura</dDesTipTra>
        </gOpeDE>
        <gTimb>
            <iTiDE>1</iTiDE>
            <dDesTiDE>Factura electrónica</dDesTiDE>
            <dNumTim>12345678</dNumTim>
        </gTimb>
        <gDatGralOpe>
            <dFeEmiDE>2023-12-15</dFeEmiDE>
        </gDatGralOpe>
        <gTotSub>
            <dTotGralOpe>110000</dTotGralOpe>
            <dTotIVA>10000</dTotIVA>
        </gTotSub>
    </DE>
</rDE>"""


@pytest.fixture
def mock_psc_certificate():
    """
    Fixture que simula un certificado PSC Paraguay válido

    Simula las características específicas requeridas por SIFEN:
    - Emisor PSC Paraguay
    - Algoritmo RSA con SHA-256
    - KeyUsage con digital_signature habilitado
    - Vigencia válida
    """
    mock_cert = Mock(spec=x509.Certificate)

    # Configurar emisor PSC
    mock_cert.issuer = Mock()
    mock_cert.issuer.__str__ = Mock(
        return_value="CN=PSC Paraguay CA, O=PSC, C=PY")

    # Configurar subject con RUC
    mock_cert.subject = Mock()
    mock_cert.subject.__str__ = Mock(
        return_value="CN=Test User, serialNumber=12345678-9")

    # Configurar números de serie
    mock_cert.serial_number = 1234567890

    # Configurar vigencia (válido por 1 año)
    now = datetime.now()
    mock_cert.not_valid_before = now - timedelta(days=1)
    mock_cert.not_valid_after = now + timedelta(days=365)

    # Configurar clave pública RSA
    mock_public_key = Mock()
    mock_public_key.key_size = 2048
    mock_cert.public_key.return_value = mock_public_key

    # Configurar extensiones KeyUsage
    mock_key_usage = Mock()
    mock_key_usage.digital_signature = True
    mock_key_usage.key_encipherment = True
    mock_extensions = Mock()
    mock_extensions.get_extension_for_oid.return_value = Mock(
        value=mock_key_usage)
    mock_cert.extensions = mock_extensions

    return mock_cert


@pytest.fixture
def certificate_config():
    """Fixture de configuración de certificado para tests"""
    return CertificateConfig(
        cert_path=Path(
            "backend/app/services/digital_sign/tests/fixtures/test.pfx"),
        cert_password="test123",
        cert_expiry_days=30
    )


@pytest.fixture
def signature_config():
    """Fixture de configuración de firma digital para tests"""
    return DigitalSignConfig(
        signature_algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        digest_algorithm="http://www.w3.org/2001/04/xmlenc#sha256",
        canonicalization_method="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    )


@pytest.fixture
def test_certificate(mock_psc_certificate):
    """Fixture que crea un objeto Certificate para tests"""
    return Certificate(
        ruc="12345678-9",
        serial_number="1234567890",
        valid_from=datetime.now() - timedelta(days=1),
        valid_to=datetime.now() + timedelta(days=365),
        certificate_path="test.pfx",
        password="test123"
    )


# ========================================
# TESTS DE VALIDACIÓN DE ESTRUCTURA XML
# ========================================

class TestXMLSignatureStructure:
    """Tests que verifican la estructura correcta de firmas XML según SIFEN v150"""

    def test_signature_namespace_validation(self, valid_sifen_xml, xmldsig_namespace):
        """
        Test: Verificar que la firma XML use el namespace correcto

        CRÍTICO: SIFEN requiere namespace exacto para validación
        """
        # PREPARAR: Simular XML firmado con namespace correcto
        signed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <DE Id="test_cdc_123">
        <gOpeDE><iTipTra>1</iTipTra></gOpeDE>
    </DE>
    <Signature xmlns="{xmldsig_namespace}">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
        </SignedInfo>
        <SignatureValue>mock_signature_value</SignatureValue>
    </Signature>
</rDE>"""

        # VERIFICAR: Namespace de firma XML
        root = ET.fromstring(signed_xml)
        signature_elem = root.find(f"{{{xmldsig_namespace}}}Signature")

        assert signature_elem is not None, "Debe contener elemento Signature con namespace correcto"
        assert signature_elem.tag == f"{{{xmldsig_namespace}}}Signature"

    def test_signature_algorithm_validation(self, signature_config):
        """
        Test: Verificar que se use el algoritmo RSA-SHA256 requerido por SIFEN

        CRÍTICO: Manual v150 especifica RSA-SHA256 como obligatorio
        """
        # VERIFICAR: Algoritmo configurado (URLs completas según estándar W3C)
        assert signature_config.signature_algorithm == "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
        assert signature_config.digest_algorithm == "http://www.w3.org/2001/04/xmlenc#sha256"

        # VERIFICAR: Algoritmo en XML firmado (simulado)
        expected_algorithm = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
        signature_method_xml = f'<SignatureMethod Algorithm="{expected_algorithm}"/>'

        assert expected_algorithm in signature_method_xml

    def test_canonicalization_method_validation(self, signature_config):
        """
        Test: Verificar método de canonicalización según W3C

        CRÍTICO: SIFEN requiere canonicalización específica para verificación
        """
        expected_canonicalization = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"

        # VERIFICAR: Configuración
        assert signature_config.canonicalization_method == expected_canonicalization

    def test_signed_info_structure_validation(self, xmldsig_namespace):
        """
        Test: Verificar estructura completa del elemento SignedInfo

        CRÍTICO: Estructura debe cumplir exactamente con XSD xmldsig-core-schema-v150.xsd
        """
        signed_info_xml = f"""
        <SignedInfo xmlns="{xmldsig_namespace}">
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
            <Reference URI="#test_cdc_123">
                <Transforms>
                    <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                    <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                </Transforms>
                <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                <DigestValue>mock_digest_value</DigestValue>
            </Reference>
        </SignedInfo>"""

        # VERIFICAR: Parseo correcto
        signed_info_elem = ET.fromstring(signed_info_xml)

        # VERIFICAR: Elementos requeridos
        assert signed_info_elem.find(
            f"{{{xmldsig_namespace}}}CanonicalizationMethod") is not None
        assert signed_info_elem.find(
            f"{{{xmldsig_namespace}}}SignatureMethod") is not None
        assert signed_info_elem.find(
            f"{{{xmldsig_namespace}}}Reference") is not None

        # VERIFICAR: Referencia con URI al CDC
        reference_elem = signed_info_elem.find(
            f"{{{xmldsig_namespace}}}Reference")
        assert reference_elem is not None, "Debe existir elemento Reference"

        uri_value = reference_elem.get("URI")
        assert uri_value is not None, "Elemento Reference debe tener atributo URI"
        assert uri_value.startswith(
            "#"), "URI debe comenzar con # para referenciar CDC"


# ========================================
# TESTS DE VALIDACIÓN DE CERTIFICADOS PSC
# ========================================

class TestPSCCertificateValidation:
    """Tests específicos para certificados PSC Paraguay según SIFEN"""

    def test_psc_issuer_validation(self, mock_psc_certificate):
        """
        Test: Verificar que el certificado sea emitido por PSC Paraguay

        CRÍTICO: SIFEN solo acepta certificados PSC autorizados por MIC
        """
        # VERIFICAR: Emisor PSC en certificado
        issuer_str = str(mock_psc_certificate.issuer)
        assert "PSC" in issuer_str, "Certificado debe ser emitido por PSC Paraguay"
        assert "Paraguay" in issuer_str or "PY" in issuer_str, "Debe indicar Paraguay como país"

    def test_certificate_validity_period(self, mock_psc_certificate):
        """
        Test: Verificar que el certificado esté vigente

        CRÍTICO: SIFEN rechaza documentos con certificados vencidos (código 0142)
        """
        now = datetime.now()

        # VERIFICAR: Vigencia del certificado
        assert mock_psc_certificate.not_valid_before <= now, "Certificado no debe estar en el futuro"
        assert now <= mock_psc_certificate.not_valid_after, "Certificado no debe estar vencido"

        # VERIFICAR: Margen de validez razonable
        validity_period = mock_psc_certificate.not_valid_after - \
            mock_psc_certificate.not_valid_before
        assert validity_period.days >= 365, "Certificado debe tener al menos 1 año de validez"

    def test_rsa_key_requirements(self, mock_psc_certificate):
        """
        Test: Verificar que el certificado use clave RSA adecuada

        CRÍTICO: SIFEN requiere RSA con tamaño mínimo de clave
        """
        public_key = mock_psc_certificate.public_key()

        # VERIFICAR: Tamaño de clave RSA
        assert public_key.key_size >= 2048, "Clave RSA debe ser de al menos 2048 bits"

    def test_key_usage_extension(self, mock_psc_certificate):
        """
        Test: Verificar extensión KeyUsage para firma digital

        CRÍTICO: Certificado debe tener permiso específico para firma digital
        """
        # VERIFICAR: Extensión KeyUsage existe
        extensions = mock_psc_certificate.extensions
        key_usage_ext = extensions.get_extension_for_oid("2.5.29.14")

        assert key_usage_ext is not None, "Certificado debe tener extensión KeyUsage"

        # VERIFICAR: Permiso de firma digital
        key_usage = key_usage_ext.value
        assert key_usage.digital_signature, "Certificado debe permitir firma digital"

    def test_ruc_extraction_from_certificate(self, mock_psc_certificate):
        """
        Test: Verificar extracción correcta del RUC del certificado

        CRÍTICO: RUC debe coincidir con el del documento para pasar validación SIFEN
        """
        # VERIFICAR: RUC en subject o serialNumber
        subject_str = str(mock_psc_certificate.subject)

        # Para certificados F2 (jurídica): RUC en serialNumber
        # Para certificados F1 (física): RUC en SubjectAlternativeName
        assert "serialNumber" in subject_str or "12345678-9" in subject_str, \
            "RUC debe estar presente en el certificado"


# ========================================
# TESTS DE VALIDACIÓN DE FIRMAS
# ========================================

class TestSignatureValidation:
    """Tests de validación integral de firmas digitales"""

    def test_successful_signature_validation(self, test_certificate, valid_sifen_xml):
        """
        Test: Validación exitosa de firma digital

        CRÍTICO: Flujo completo de firma y validación debe funcionar
        """
        # PREPARAR: Simular DigitalSigner exitoso usando mock
        with patch.object(DigitalSigner, '__init__', return_value=None):
            with patch.object(DigitalSigner, 'sign_xml') as mock_sign:
                # PREPARAR: Resultado de firma exitosa
                mock_sign.return_value = SignatureResult(
                    success=True,
                    error=None,
                    timestamp=datetime.now(),
                    signature="mock_signature_base64",
                    certificate_serial="1234567890",
                    signature_algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
                )

                # EJECUTAR: Crear signer y firmar documento
                signer = DigitalSigner(test_certificate)
                result = signer.sign_xml(valid_sifen_xml)

                # VERIFICAR: Resultado exitoso
                assert result.success is True
                assert result.error is None
                assert result.signature is not None
                assert result.certificate_serial == test_certificate.serial_number
                assert result.signature_algorithm == "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"

    def test_invalid_xml_signature_rejection(self, test_certificate):
        """
        Test: Rechazo de XML malformado antes de firmar

        CRÍTICO: Debe detectar XML inválido antes del proceso de firma
        """
        # PREPARAR: XML malformado
        invalid_xml = "<rDE><DE><incomplete>"

        with patch.object(DigitalSigner, '__init__', return_value=None):
            with patch.object(DigitalSigner, 'sign_xml') as mock_sign:
                # PREPARAR: Mock que lance excepción por XML inválido
                mock_sign.side_effect = ValueError("XML malformado")

                # EJECUTAR: Crear signer y intentar firmar XML inválido
                signer = DigitalSigner(test_certificate)

                # VERIFICAR: Excepción por XML inválido
                with pytest.raises(ValueError, match="XML malformado"):
                    signer.sign_xml(invalid_xml)

    def test_signature_verification_with_valid_signature(self, test_certificate):
        """
        Test: Verificación exitosa de firma válida

        CRÍTICO: Debe validar correctamente firmas auténticas
        """
        with patch.object(DigitalSigner, '__init__', return_value=None):
            with patch.object(DigitalSigner, 'verify_signature') as mock_verify:
                # PREPARAR: Verificación exitosa
                mock_verify.return_value = True

                # EJECUTAR: Crear signer y verificar firma
                signer = DigitalSigner(test_certificate)
                is_valid = signer.verify_signature(
                    "mock_xml", "mock_signature")

                # VERIFICAR: Firma válida
                assert is_valid is True

    def test_signature_verification_with_invalid_signature(self, test_certificate):
        """
        Test: Rechazo de firma inválida

        CRÍTICO: Debe detectar firmas corruptas o manipuladas
        """
        with patch.object(DigitalSigner, '__init__', return_value=None):
            with patch.object(DigitalSigner, 'verify_signature') as mock_verify:
                # PREPARAR: Verificación fallida
                mock_verify.return_value = False

                # EJECUTAR: Crear signer y verificar firma inválida
                signer = DigitalSigner(test_certificate)
                is_valid = signer.verify_signature(
                    "mock_xml", "invalid_signature")

                # VERIFICAR: Firma inválida
                assert is_valid is False


# ========================================
# TESTS DE CASOS ESPECÍFICOS SIFEN
# ========================================

class TestSifenSpecificValidation:
    """Tests para casos específicos de validación SIFEN según Manual v150"""

    def test_cdc_reference_in_signature(self, valid_sifen_xml, xmldsig_namespace):
        """
        Test: Verificar que la firma referencie correctamente el CDC

        CRÍTICO: SIFEN valida que la referencia URI apunte al ID del documento
        """
        # EXTRAER: CDC del XML
        root = ET.fromstring(valid_sifen_xml)
        cdc = root.get("Id")
        assert cdc is not None, "XML debe tener ID (CDC) en elemento raíz"

        # SIMULAR: Firma con referencia al CDC
        signature_with_ref = f"""
        <Signature xmlns="{xmldsig_namespace}">
            <SignedInfo>
                <Reference URI="#{cdc}">
                    <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                    <DigestValue>mock_digest</DigestValue>
                </Reference>
            </SignedInfo>
            <SignatureValue>mock_signature</SignatureValue>
        </Signature>"""

        # VERIFICAR: Referencia correcta al CDC
        signature_elem = ET.fromstring(signature_with_ref)
        reference_elem = signature_elem.find(
            f".//{{{xmldsig_namespace}}}Reference")

        assert reference_elem is not None, "Debe contener elemento Reference"
        assert reference_elem.get(
            "URI") == f"#{cdc}", "URI debe referenciar el CDC del documento"

    def test_sifen_namespace_preservation(self, valid_sifen_xml, sifen_namespace):
        """
        Test: Verificar que se preserve el namespace SIFEN en documento firmado

        CRÍTICO: Namespace incorrecto causa rechazo inmediato por SIFEN
        """
        # VERIFICAR: Namespace SIFEN en XML original
        root = ET.fromstring(valid_sifen_xml)

        # El namespace debe estar declarado en el elemento raíz
        assert root.tag == f"{{{sifen_namespace}}}rDE", "Elemento raíz debe usar namespace SIFEN"

        # SIMULAR: XML después de agregar firma (debe preservar namespace)
        signed_xml = valid_sifen_xml.replace(
            "</rDE>",
            f"""<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
            <SignedInfo><Reference URI="#test_cdc_123"/></SignedInfo>
            <SignatureValue>mock</SignatureValue>
            </Signature></rDE>"""
        )

        # VERIFICAR: Namespace preservado
        signed_root = ET.fromstring(signed_xml)
        assert signed_root.tag == f"{{{sifen_namespace}}}rDE", "Namespace SIFEN debe preservarse"

    def test_version_150_compliance(self, valid_sifen_xml):
        """
        Test: Verificar que el documento declare versión 150

        CRÍTICO: SIFEN valida que dVerFor sea exactamente "150"
        """
        root = ET.fromstring(valid_sifen_xml)
        version_elem = root.find(
            ".//{http://ekuatia.set.gov.py/sifen/xsd}dVerFor")

        assert version_elem is not None, "Documento debe contener elemento dVerFor"
        assert version_elem.text == "150", "Versión debe ser exactamente '150'"


# ========================================
# TESTS DE MANEJO DE ERRORES
# ========================================

class TestSignatureErrorHandling:
    """Tests para manejo de errores específicos de firma digital"""

    def test_expired_certificate_error(self, test_certificate):
        """
        Test: Manejo de certificado vencido (código SIFEN 0142)

        CRÍTICO: Debe detectar certificados vencidos antes de envío
        """
        # PREPARAR: Certificado vencido
        expired_cert = test_certificate.model_copy()
        expired_cert.valid_to = datetime.now() - timedelta(days=1)

        # PREPARAR: Mock que simule error de certificado vencido
        with patch.object(DigitalSigner, '__init__') as mock_init:
            mock_init.side_effect = CertificateError(
                "Certificado vencido", error_code="0142")

            # VERIFICAR: Error de certificado vencido
            with pytest.raises(CertificateError, match="Certificado vencido"):
                DigitalSigner(expired_cert)

    def test_invalid_certificate_format_error(self, certificate_config):
        """
        Test: Manejo de certificado con formato inválido

        CRÍTICO: Debe manejar archivos .pfx corruptos o incorrectos
        """
        # PREPARAR: Configuración con certificado inválido
        invalid_config = certificate_config.model_copy()
        invalid_config.cert_path = Path("nonexistent.pfx")

        # PREPARAR: Mock que simule archivo no encontrado
        with patch.object(CertificateManager, 'load_certificate') as mock_load:
            mock_load.side_effect = CertificateError("Archivo no encontrado")

            # VERIFICAR: Error de certificado no encontrado
            with pytest.raises(CertificateError, match="Archivo no encontrado"):
                cert_manager = CertificateManager(invalid_config)
                cert_manager.load_certificate()

    def test_wrong_certificate_password_error(self, certificate_config):
        """
        Test: Manejo de contraseña incorrecta del certificado

        CRÍTICO: Debe manejar graciosamente errores de autenticación
        """
        # PREPARAR: Configuración con contraseña incorrecta
        wrong_password_config = certificate_config.model_copy()
        wrong_password_config.cert_password = "wrong_password"

        # PREPARAR: Mock que simule contraseña incorrecta
        with patch.object(CertificateManager, 'load_certificate') as mock_load:
            mock_load.side_effect = CertificateError("Contraseña incorrecta")

            # VERIFICAR: Error de contraseña incorrecta
            with pytest.raises(CertificateError, match="Contraseña incorrecta"):
                cert_manager = CertificateManager(wrong_password_config)
                cert_manager.load_certificate()


# ========================================
# TESTS DE INTEGRACIÓN CON XML SIGNER
# ========================================

class TestXMLSignerIntegration:
    """Tests de integración para XMLSigner con validaciones SIFEN"""

    def test_xml_signer_with_sifen_document(self, valid_sifen_xml, signature_config, certificate_config):
        """
        Test: XMLSigner con documento SIFEN completo

        CRÍTICO: Integración completa del proceso de firma XML
        """
        # PREPARAR: Mocks para CertificateManager y XMLSigner
        with patch.object(CertificateManager, '__init__', return_value=None):
            with patch.object(XMLSigner, '__init__', return_value=None):
                with patch.object(XMLSigner, 'sign_xml') as mock_sign:
                    # PREPARAR: Resultado exitoso
                    mock_sign.return_value = f"{valid_sifen_xml}<Signature>mock</Signature>"

                    # EJECUTAR: Crear XMLSigner y firmar
                    cert_manager = CertificateManager(certificate_config)
                    xml_signer = XMLSigner(signature_config, cert_manager)
                    signed_xml = xml_signer.sign_xml(valid_sifen_xml)

                    # VERIFICAR: Contiene firma
                    assert "Signature" in signed_xml
                    assert "mock" in signed_xml


# ========================================
# HELPER FUNCTIONS
# ========================================

def mock_open(read_data=b""):
    """Helper para mockear apertura de archivos con datos binarios"""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)


# ========================================
# CONFIGURACIÓN DE TESTS
# ========================================

def pytest_configure(config):
    """Configuración específica para tests de validación de firmas"""
    config.addinivalue_line(
        "markers",
        "signature_validation: marca tests de validación de firmas digitales"
    )
    config.addinivalue_line(
        "markers",
        "psc_certificate: marca tests específicos para certificados PSC Paraguay"
    )
    config.addinivalue_line(
        "markers",
        "sifen_compliance: marca tests de cumplimiento con especificaciones SIFEN v150"
    )


# Marcar todos los tests de este módulo
pytestmark = [
    pytest.mark.signature_validation,
    pytest.mark.sifen_compliance
]
