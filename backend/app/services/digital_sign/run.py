"""
Script principal para ejecutar el módulo de firma digital
"""
import argparse
import sys
from pathlib import Path
from typing import Optional
from .certificate_manager import CertificateManager
from .xml_signer import XMLSigner
from .config import CertificateConfig, DigitalSignConfig


def setup_argparse() -> argparse.ArgumentParser:
    """Configura el parser de argumentos"""
    parser = argparse.ArgumentParser(
        description="Firma digital de documentos XML para SIFEN"
    )

    parser.add_argument(
        "--cert-path",
        type=Path,
        required=True,
        help="Ruta al archivo PFX"
    )

    parser.add_argument(
        "--cert-password",
        type=str,
        required=True,
        help="Contraseña del certificado"
    )

    parser.add_argument(
        "--xml-path",
        type=Path,
        required=True,
        help="Ruta al archivo XML a firmar"
    )

    parser.add_argument(
        "--output-path",
        type=Path,
        help="Ruta donde guardar el XML firmado (opcional)"
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verificar firma en lugar de firmar"
    )

    return parser


def read_xml(xml_path: Path) -> str:
    """Lee el contenido del archivo XML"""
    try:
        with open(xml_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error al leer archivo XML: {str(e)}")
        sys.exit(1)


def write_xml(xml_content: str, output_path: Path) -> None:
    """Escribe el XML firmado al archivo de salida"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
    except Exception as e:
        print(f"Error al escribir archivo XML: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Función principal"""
    parser = setup_argparse()
    args = parser.parse_args()

    # Configurar certificado
    cert_config = CertificateConfig(
        cert_path=args.cert_path,
        cert_password=args.cert_password,
        cert_expiry_days=30
    )

    # Configurar firma
    sign_config = DigitalSignConfig()

    try:
        # Crear instancias
        cert_manager = CertificateManager(cert_config)
        xml_signer = XMLSigner(sign_config, cert_manager)

        # Leer XML
        xml_content = read_xml(args.xml_path)

        if args.verify:
            # Verificar firma
            is_valid = xml_signer.verify_signature(xml_content)
            if is_valid:
                print("✅ Firma válida")
            else:
                print("❌ Firma inválida")
                sys.exit(1)
        else:
            # Firmar XML
            signed_xml = xml_signer.sign_xml(xml_content)

            # Guardar o mostrar resultado
            if args.output_path:
                write_xml(signed_xml, args.output_path)
                print(f"✅ XML firmado guardado en: {args.output_path}")
            else:
                print(signed_xml)

    except ValueError as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
