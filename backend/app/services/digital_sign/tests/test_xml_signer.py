"""
Tests para el firmador XML de SIFEN
"""
import pytest
from pathlib import Path
from lxml import etree
from datetime import datetime, timedelta
from ..xml_signer import XMLSigner
from ..config import CertificateConfig, DigitalSignConfig
from ..certificate_manager import CertificateManager
from cryptography.hazmat.primitives.serialization import pkcs12


@pytest.fixture
def parser():
    """Fixture que proporciona un parser XML"""
    return etree.XMLParser(remove_blank_text=True)


@pytest.fixture
def test_xml():
    """Fixture que proporciona un XML de prueba"""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <data>Test</data>
    </root>"""


@pytest.fixture
def test_certificate():
    """Fixture que genera certificado auto-firmado para tests"""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from datetime import datetime, timedelta
    import tempfile
    import os

    # Generar clave privada
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Crear certificado auto-firmado
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "PY"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Central"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Asunción"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Company"),
        x509.NameAttribute(NameOID.COMMON_NAME, "test.sifen.local"),
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
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("test.sifen.local"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Crear archivo PFX temporal
    p12_password = b"test123"
    p12_data = pkcs12.serialize_key_and_certificates(
        name=b"Test Certificate",
        key=private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(
            p12_password)
    )

    # Guardar en archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pfx') as tmp:
        tmp.write(p12_data)
        tmp_path = tmp.name

    yield {
        'path': tmp_path,
        'password': 'test123',
        'certificate': cert,
        'private_key': private_key
    }

    # Limpiar archivo temporal
    os.unlink(tmp_path)


@pytest.fixture
def xml_signer(test_certificate):
    """Fixture que proporciona una instancia de XMLSigner"""
    cert_config = CertificateConfig(
        cert_path=Path(
            "backend/app/services/digital_sign/tests/fixtures/test.pfx"),
        cert_password="test123",
        cert_expiry_days=30
    )
    sign_config = DigitalSignConfig()
    cert_manager = CertificateManager(cert_config)
    return XMLSigner(sign_config, cert_manager)


def test_sign_xml(xml_signer, test_xml, parser):
    """Test que verifica que el XML se firma correctamente"""
    signed_xml = xml_signer.sign_xml(test_xml)
    assert 'Signature' in signed_xml
    assert 'SignedInfo' in signed_xml
    assert 'SignatureValue' in signed_xml


def test_verify_signature(xml_signer, test_xml, parser):
    """Test que verifica que una firma válida es aceptada"""
    signed_xml = xml_signer.sign_xml(test_xml)
    assert xml_signer.verify_signature(signed_xml)


def test_verify_invalid_signature(xml_signer, test_xml, parser):
    """Test que verifica que una firma inválida es rechazada"""
    signed_xml = xml_signer.sign_xml(test_xml)
    # Modificar el XML después de firmar
    modified_xml = signed_xml.replace('Test', 'Modified')
    assert not xml_signer.verify_signature(modified_xml)


def test_sign_invalid_xml(xml_signer, parser):
    """Test que verifica que se lanza error con XML inválido"""
    invalid_xml = "<invalid>"
    with pytest.raises(ValueError):
        xml_signer.sign_xml(invalid_xml)


def test_verify_no_signature(xml_signer, test_xml, parser):
    """Test que verifica que se lanza error al verificar XML sin firma"""
    with pytest.raises(ValueError):
        xml_signer.verify_signature(test_xml)


def test_signature_namespace(xml_signer, test_xml, parser):
    """Test que verifica que el XML usa el namespace correcto de SIFEN"""
    signed_xml = xml_signer.sign_xml(test_xml)
    assert 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in signed_xml
    assert 'xmlns:ds="http://www.w3.org/2000/09/xmldsig#"' in signed_xml


def test_certificate_validation(xml_signer, test_certificate):
    """Verifica que el certificado usado cumple con los requisitos de SIFEN"""
    # Verificar emisor PSC
    assert "PSC" in test_certificate.issuer, "El certificado debe ser emitido por PSC"

    # Verificar vigencia
    now = datetime.now()
    assert test_certificate.not_valid_before <= now <= test_certificate.not_valid_after, \
        "El certificado debe estar vigente"

    # Verificar permisos
    key_usage = test_certificate.extensions.get_extension_for_oid("2.5.29.14")
    assert key_usage is not None, "El certificado debe tener KeyUsage"
    assert key_usage.value.digital_signature, "El certificado debe tener permiso de firma digital"


def test_signature_structure(xml_signer, test_xml, parser):
    """Verifica que la estructura de la firma cumple con el esquema XSD"""
    signed_xml = xml_signer.sign_xml(test_xml)
    root = etree.fromstring(signed_xml.encode('utf-8'), parser=parser)

    # Verificar SignedInfo
    signed_info = root.find(
        ".//{http://www.w3.org/2000/09/xmldsig#}SignedInfo")
    assert signed_info is not None, "Debe existir SignedInfo"

    # Verificar orden de elementos en SignedInfo
    children = signed_info.getchildren()
    assert children[0].tag.endswith(
        "CanonicalizationMethod"), "Primer elemento debe ser CanonicalizationMethod"
    assert children[1].tag.endswith(
        "SignatureMethod"), "Segundo elemento debe ser SignatureMethod"
    assert children[2].tag.endswith(
        "Reference"), "Tercer elemento debe ser Reference"

    # Verificar transformaciones
    transforms = root.find(".//{http://www.w3.org/2000/09/xmldsig#}Transforms")
    assert transforms is not None, "Deben existir transformaciones"
    transform = transforms.find(
        ".//{http://www.w3.org/2000/09/xmldsig#}Transform")
    assert transform.get("Algorithm") == "http://www.w3.org/2000/09/xmldsig#enveloped-signature", \
        "Debe usar transformación enveloped-signature"


def test_namespace_declaration(xml_signer, test_xml, parser):
    """Verifica que el XML usa el namespace correcto de SIFEN"""
    signed_xml = xml_signer.sign_xml(test_xml)
    root = etree.fromstring(signed_xml.encode('utf-8'), parser=parser)

    # Verificar namespace SIFEN
    assert root.get("xmlns") == "http://ekuatia.set.gov.py/sifen/xsd", \
        "Debe usar el namespace de SIFEN"

    # Verificar namespace xsi
    assert "xmlns:xsi" in root.attrib, "Debe incluir namespace xsi"
    assert root.get("xmlns:xsi") == "http://www.w3.org/2001/XMLSchema-instance", \
        "Debe usar el namespace xsi correcto"

    # Verificar namespace ds
    assert "xmlns:ds" in root.attrib, "Debe incluir namespace ds"
    assert root.get("xmlns:ds") == "http://www.w3.org/2000/09/xmldsig#", \
        "Debe usar el namespace ds correcto"


def test_xml_encoding(xml_signer, test_xml, parser):
    """Verifica que el XML usa UTF-8 encoding"""
    # Verificar declaración XML
    signed_xml = xml_signer.sign_xml(test_xml)
    assert signed_xml.startswith('<?xml version="1.0" encoding="UTF-8"?>'), \
        "Debe incluir declaración XML con encoding UTF-8"

    # Verificar caracteres especiales
    test_xml_with_special_chars = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <data>Test ñ á é</data>
    </root>"""
    signed_xml = xml_signer.sign_xml(test_xml_with_special_chars)
    root = etree.fromstring(signed_xml.encode('utf-8'), parser=parser)
    data = root.find(".//data")
    assert data is not None, "Debe existir el elemento data"
    assert "ñ" in data.text and "á" in data.text and "é" in data.text, \
        "Debe preservar caracteres especiales"


def test_signature_algorithms(xml_signer, test_xml, parser):
    """Verifica que se usan los algoritmos correctos"""
    signed_xml = xml_signer.sign_xml(test_xml)
    root = etree.fromstring(signed_xml.encode('utf-8'), parser=parser)

    # Verificar algoritmo de canonicalización
    canonicalization = root.find(
        ".//{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod")
    assert canonicalization.get("Algorithm") == "http://www.w3.org/2001/10/xml-exc-c14n#", \
        "Debe usar canonicalización exclusiva"

    # Verificar algoritmo de firma
    signature_method = root.find(
        ".//{http://www.w3.org/2000/09/xmldsig#}SignatureMethod")
    assert signature_method.get("Algorithm") == "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256", \
        "Debe usar RSA-SHA256"

    # Verificar algoritmo de digest
    digest_method = root.find(
        ".//{http://www.w3.org/2000/09/xmldsig#}DigestMethod")
    assert digest_method.get("Algorithm") == "http://www.w3.org/2001/04/xmlenc#sha256", \
        "Debe usar SHA256 para digest"
