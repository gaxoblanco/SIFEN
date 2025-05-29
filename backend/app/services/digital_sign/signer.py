"""
Implementación de firma digital para documentos SIFEN
"""
import base64
from datetime import datetime
from typing import Optional, cast
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import load_pem_x509_certificate
from .models import Certificate, SignatureResult


class DigitalSigner:
    """Clase para manejar la firma digital de documentos SIFEN"""

    def __init__(self, certificate: Certificate):
        """
        Inicializa el firmador con un certificado

        Args:
            certificate: Certificado digital a usar para firmar
        """
        self.certificate = certificate
        self._load_certificate()

    def _load_certificate(self) -> None:
        """Carga el certificado y la clave privada"""
        try:
            # Cargar certificado desde archivo
            with open(self.certificate.certificate_path, 'rb') as cert_file:
                cert_data = cert_file.read()

            # Cargar certificado y clave privada
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                cert_data,
                self.certificate.password.encode() if self.certificate.password else None
            )

            if not certificate:
                raise ValueError("No se pudo cargar el certificado")

            self.certificate_obj = certificate
            # Asegurarnos que la clave privada es RSA
            if not isinstance(private_key, rsa.RSAPrivateKey):
                raise ValueError("La clave privada debe ser RSA")
            self.private_key = private_key

        except Exception as e:
            raise ValueError(f"Error al cargar el certificado: {str(e)}")

    def sign_xml(self, xml_content: str) -> SignatureResult:
        """
        Firma un documento XML según especificaciones SIFEN

        Args:
            xml_content: Contenido XML a firmar

        Returns:
            SignatureResult con el resultado de la firma
        """
        try:
            if not self.private_key:
                return SignatureResult(
                    success=False,
                    error="No hay clave privada disponible para firmar",
                    signature=None,
                    certificate_serial=None,
                    signature_algorithm=None
                )

            # Calcular hash del XML usando SHA-256
            hash_obj = hashes.Hash(hashes.SHA256())
            hash_obj.update(xml_content.encode())
            digest = hash_obj.finalize()

            # Firmar el hash usando RSA
            signature = self.private_key.sign(
                digest,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # Codificar firma en base64
            signature_b64 = base64.b64encode(signature).decode()

            return SignatureResult(
                success=True,
                error=None,
                signature=signature_b64,
                certificate_serial=self.certificate.serial_number,
                signature_algorithm="SHA256withRSA"
            )

        except Exception as e:
            return SignatureResult(
                success=False,
                error=f"Error al firmar el documento: {str(e)}",
                signature=None,
                certificate_serial=None,
                signature_algorithm=None
            )

    def verify_signature(self, xml_content: str, signature: Optional[str]) -> bool:
        """
        Verifica una firma digital

        Args:
            xml_content: Contenido XML firmado
            signature: Firma digital en base64 (opcional)

        Returns:
            bool indicando si la firma es válida
        """
        try:
            if not signature:
                return False

            # Decodificar firma
            signature_bytes = base64.b64decode(signature)

            # Calcular hash del XML
            hash_obj = hashes.Hash(hashes.SHA256())
            hash_obj.update(xml_content.encode())
            digest = hash_obj.finalize()

            # Verificar firma usando la clave pública del certificado
            public_key = cast(rsa.RSAPublicKey,
                              self.certificate_obj.public_key())
            public_key.verify(
                signature_bytes,
                digest,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            return True

        except Exception:
            return False
