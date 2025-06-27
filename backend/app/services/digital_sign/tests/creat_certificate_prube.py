"""
Script para crear certificado de prueba para testing del sistema digital_sign
NO para uso en producción - solo para desarrollo y testing
"""
import os
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from datetime import datetime, timedelta


def crear_certificado_prueba(
    output_path: Path = Path("certificado_prueba.pfx"),
    password: str = "test123",
    ruc_emisor: str = "80016875-1"
):
    """
    Crear certificado de prueba para testing

    Args:
        output_path: Ruta donde guardar el certificado .pfx
        password: Contraseña del certificado
        ruc_emisor: RUC del emisor (formato paraguayo)
    """

    print(f"🔐 CREANDO CERTIFICADO DE PRUEBA")
    print(f"📁 Archivo: {output_path}")
    print(f"🔒 Password: {password}")
    print(f"🏢 RUC: {ruc_emisor}")

    # 1. Generar llave privada RSA
    print(f"\n🔑 Generando llave privada RSA-2048...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. Crear datos del certificado
    print(f"📋 Configurando datos del certificado...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "PY"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Central"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Asunción"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,
                           "EMPRESA TEST SIFEN S.A."),
        x509.NameAttribute(NameOID.COMMON_NAME,
                           f"CERTIFICADO TEST {ruc_emisor}"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Testing"),
        # Incluir RUC en el Subject Alternative Name
        x509.NameAttribute(NameOID.SERIAL_NUMBER, ruc_emisor.replace("-", "")),
    ])

    # 3. Crear certificado X.509
    print(f"📜 Creando certificado X.509...")
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
        # Válido por 1 año
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        # Key usage para firma digital
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=True,  # Non-repudiation
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    ).add_extension(
        # Extended key usage
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.CLIENT_AUTH,
            ExtendedKeyUsageOID.EMAIL_PROTECTION,
        ]),
        critical=True,
    ).add_extension(
        # Subject Alternative Name con RUC
        x509.SubjectAlternativeName([
            x509.RFC822Name(
                f"test@empresa{ruc_emisor.replace('-', '')}.com.py"),
            x509.DNSName(f"test-{ruc_emisor.replace('-', '')}.sifen.test"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # 4. Crear archivo PKCS#12 (.pfx)
    print(f"💾 Creando archivo PKCS#12 (.pfx)...")

    # Empaquetar en formato PKCS#12 (PFX)
    pfx_data = pkcs12.serialize_key_and_certificates(
        name=b"Certificado Test SIFEN",
        key=private_key,
        cert=cert,
        cas=None,  # No hay certificados de CA adicionales
        encryption_algorithm=serialization.BestAvailableEncryption(
            password.encode())
    )

    # 5. Guardar archivo
    print(f"💾 Guardando certificado...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(pfx_data)

    print(f"\n✅ CERTIFICADO CREADO EXITOSAMENTE")
    print(f"📁 Ubicación: {output_path.absolute()}")
    print(f"📏 Tamaño: {len(pfx_data)} bytes")
    print(f"📅 Válido desde: {cert.not_valid_before}")
    print(f"📅 Válido hasta: {cert.not_valid_after}")

    # 6. Información para usar en tests
    print(f"\n🔧 CONFIGURACIÓN PARA TESTS:")
    print(f"""
# Usar en tus tests:
cert_config = CertificateConfig(
    cert_path=Path("{output_path}"),
    cert_password="{password}",
    cert_expiry_days=30
)
""")

    print(f"\n⚠️ IMPORTANTE:")
    print(f"   - Este certificado es SOLO para testing")
    print(f"   - NO usar en producción")
    print(f"   - Para SIFEN real necesitas certificado PSC oficial")

    return output_path, password


def verificar_certificado(cert_path: Path, password: str):
    """Verificar que el certificado se creó correctamente"""

    print(f"\n🔍 VERIFICANDO CERTIFICADO CREADO")
    print(f"📁 Archivo: {cert_path}")

    try:
        # Leer archivo PKCS#12
        with open(cert_path, "rb") as f:
            pfx_data = f.read()

        # Deserializar PKCS#12 con type hints corregidos
        try:
            private_key, cert, additional_certs = pkcs12.load_key_and_certificates(
                pfx_data,
                password.encode()
            )
        except Exception as e:
            print(f"❌ Error cargando PKCS#12: {e}")
            return False

        # Verificar que el certificado se cargó correctamente
        if cert is None:
            print(f"❌ No se pudo cargar el certificado")
            return False

        if private_key is None:
            print(f"❌ No se pudo cargar la llave privada")
            return False

        print(f"✅ Certificado cargado correctamente")
        print(f"🔑 Llave privada: {type(private_key)}")
        print(f"📜 Certificado: {type(cert)}")
        print(f"👤 Subject: {cert.subject}")
        print(f"🏢 Issuer: {cert.issuer}")
        print(f"📅 Válido desde: {cert.not_valid_before}")
        print(f"📅 Válido hasta: {cert.not_valid_after}")

        # Extraer RUC del certificado
        for attribute in cert.subject:
            if attribute.oid == NameOID.SERIAL_NUMBER:
                print(f"🏢 RUC extraído: {attribute.value}")

        return True

    except Exception as e:
        print(f"❌ Error verificando certificado: {e}")
        return False


if __name__ == "__main__":
    print(f"🔐 CREADOR DE CERTIFICADO DE PRUEBA SIFEN")
    print("=" * 50)

    # Crear certificado en la carpeta de tests
    test_cert_path = Path(
        "app/services/digital_sign/tests/fixtures/test_real.pfx")

    # Crear directorio si no existe
    test_cert_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Crear certificado
        cert_path, cert_password = crear_certificado_prueba(
            output_path=test_cert_path,
            password="test123",
            ruc_emisor="80016875-1"
        )

        # Verificar que funciona
        if verificar_certificado(cert_path, cert_password):
            print(f"\n🎉 ¡CERTIFICADO LISTO PARA USAR EN TESTS!")
            print(f"\n▶️ AHORA PUEDES:")
            print(f"   1. Usar este certificado en los tests")
            print(f"   2. El XMLSigner podrá firmar XML realmente")
            print(f"   3. Ver el proceso completo funcionando")
            print(f"\n🚀 EJECUTAR TEST 5:")
            print(
                f"   python app/services/digital_sign/tests/quicks/test_5_integration.py")
        else:
            print(f"\n❌ Error creando certificado")

    except ImportError as e:
        print(f"\n❌ ERROR DE DEPENDENCIAS:")
        print(f"   {e}")
        print(f"\n💡 INSTALAR DEPENDENCIAS FALTANTES:")
        print(f"   pip install cryptography")

    except Exception as e:
        print(f"\n❌ ERROR INESPERADO:")
        print(f"   {type(e).__name__}: {e}")
        print(f"\n💡 VERIFICAR:")
        print(f"   1. Permisos de escritura en: {test_cert_path.parent}")
        print(f"   2. Espacio en disco disponible")
        print(f"   3. Versión de cryptography instalada")
