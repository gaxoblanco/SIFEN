"""
Ejemplo de uso del módulo de firma digital
"""
from pathlib import Path
from ..certificate_manager import CertificateManager
from ..xml_signer import XMLSigner
from ..config import CertificateConfig, DigitalSignConfig


def main():
    # Configurar certificado
    cert_config = CertificateConfig(
        cert_path=Path("examples/cert.pfx"),
        cert_password="test123",
        cert_expiry_days=30
    )

    # Configurar firma
    sign_config = DigitalSignConfig()

    try:
        # Crear instancias
        cert_manager = CertificateManager(cert_config)
        xml_signer = XMLSigner(sign_config, cert_manager)

        # XML de ejemplo
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <DE version="150">
            <dDoc>FAC</dDoc>
            <dNum>001</dNum>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumID>12345678-9</dNumID>
            <dDV>1</dDV>
            <dTit>EMPRESA EJEMPLO S.A.</dTit>
            <dNumIDRec>98765432-1</dNumIDRec>
            <dTitRec>CLIENTE EJEMPLO</dTitRec>
            <dTotG>100000</dTotG>
        </DE>"""

        # Firmar XML
        signed_xml = xml_signer.sign_xml(xml)
        print("XML firmado:")
        print(signed_xml)

        # Verificar firma
        is_valid = xml_signer.verify_signature(signed_xml)
        print(f"\nFirma válida: {is_valid}")

    except ValueError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"Error inesperado: {str(e)}")


if __name__ == "__main__":
    main()
