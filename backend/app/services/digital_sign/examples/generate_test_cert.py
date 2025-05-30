"""
Genera un certificado de prueba para desarrollo
"""
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12, BestAvailableEncryption


def generate_test_cert():
    """Genera un certificado de prueba"""
    # Generar clave privada
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Crear certificado
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Test Certificate"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Test Organization"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"PY"),
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
        datetime.now()
    ).not_valid_after(
        datetime.now() + timedelta(days=365)
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True
    ).sign(private_key, hashes.SHA256())

    # Crear directorio de fixtures si no existe
    fixtures_dir = Path("backend/app/services/digital_sign/tests/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Guardar certificado y clave en archivo PFX
    with open(fixtures_dir / "test.pfx", "wb") as f:
        f.write(
            pkcs12.serialize_key_and_certificates(
                name=b"test",
                key=private_key,
                cert=cert,
                cas=None,
                encryption_algorithm=BestAvailableEncryption(
                    b"test123")
            )
        )

    print("✅ Certificado de prueba generado en tests/fixtures/test.pfx")
    print("Contraseña: test123")


if __name__ == "__main__":
    generate_test_cert()
