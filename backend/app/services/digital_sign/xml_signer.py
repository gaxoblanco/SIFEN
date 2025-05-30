"""
Firmador de documentos XML para SIFEN
"""
from typing import Optional
from lxml import etree
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding
from .config import DigitalSignConfig
from .certificate_manager import CertificateManager


class XMLSigner:
    """Firmador de documentos XML"""

    def __init__(self, config: DigitalSignConfig, cert_manager: CertificateManager):
        """Inicializa el firmador XML"""
        self.config = config
        self.cert_manager = cert_manager

    def sign_xml(self, xml_content: str) -> str:
        """
        Firma un documento XML

        Args:
            xml_content: Contenido XML a firmar

        Returns:
            str: XML firmado
        """
        try:
            # Parsear XML
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.fromstring(xml_content.encode('utf-8'), parser)

            # Agregar namespace de SIFEN al root
            root.set("xmlns", "http://ekuatia.set.gov.py/sifen/xsd")

            # Calcular digest del documento original
            canonicalized = etree.tostring(root)
            digest = hashes.Hash(hashes.SHA256())
            digest.update(canonicalized)
            digest_value = digest.finalize()

            # Crear firma
            signature = etree.SubElement(
                root,
                "{http://www.w3.org/2000/09/xmldsig#}Signature",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )

            # Información de firma
            signed_info = etree.SubElement(
                signature,
                "{http://www.w3.org/2000/09/xmldsig#}SignedInfo",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )

            # Método de canonicalización
            canonicalization_method = etree.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            canonicalization_method.set(
                "Algorithm",
                "http://www.w3.org/2001/10/xml-exc-c14n#"
            )

            # Método de firma
            signature_method = etree.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}SignatureMethod",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            signature_method.set(
                "Algorithm",
                "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
            )

            # Referencia
            reference = etree.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}Reference",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            reference.set("URI", "")

            # Transformaciones
            transforms = etree.SubElement(
                reference,
                "{http://www.w3.org/2000/09/xmldsig#}Transforms",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            transform = etree.SubElement(
                transforms,
                "{http://www.w3.org/2000/09/xmldsig#}Transform",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            transform.set(
                "Algorithm",
                "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
            )

            # Digest
            digest_method = etree.SubElement(
                reference,
                "{http://www.w3.org/2000/09/xmldsig#}DigestMethod",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            digest_method.set(
                "Algorithm",
                "http://www.w3.org/2001/04/xmlenc#sha256"
            )

            # Agregar valor del digest
            digest_value_elem = etree.SubElement(
                reference,
                "{http://www.w3.org/2000/09/xmldsig#}DigestValue",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            digest_value_elem.text = digest_value.hex()

            # Firmar SignedInfo
            signed_info_canonicalized = etree.tostring(signed_info)
            signature_bytes = self.cert_manager.private_key.sign(
                signed_info_canonicalized,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # Agregar firma
            signature_value = etree.SubElement(
                signature,
                "{http://www.w3.org/2000/09/xmldsig#}SignatureValue",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            signature_value.text = signature_bytes.hex()

            # Agregar certificado
            key_info = etree.SubElement(
                signature,
                "{http://www.w3.org/2000/09/xmldsig#}KeyInfo",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            x509_data = etree.SubElement(
                key_info,
                "{http://www.w3.org/2000/09/xmldsig#}X509Data",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            x509_certificate = etree.SubElement(
                x509_data,
                "{http://www.w3.org/2000/09/xmldsig#}X509Certificate",
                attrib={},
                nsmap={"ds": "http://www.w3.org/2000/09/xmldsig#"}
            )
            x509_certificate.text = self.cert_manager.certificate.public_bytes(
                encoding=Encoding.PEM
            ).decode('utf-8')

            # Preservar la declaración XML con encoding UTF-8
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root).decode('utf-8')

        except Exception as e:
            raise ValueError(f"Error al firmar XML: {str(e)}")

    def verify_signature(self, xml_content: str) -> bool:
        """
        Verifica la firma de un XML

        Args:
            xml_content: XML firmado a verificar

        Returns:
            bool: True si la firma es válida
        """
        try:
            # Parsear XML
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.fromstring(xml_content.encode('utf-8'), parser)

            # Obtener firma
            signature = root.find(
                ".//{http://www.w3.org/2000/09/xmldsig#}Signature"
            )
            if signature is None:
                raise ValueError("No se encontró firma en el XML")

            # Obtener SignedInfo
            signed_info = signature.find(
                ".//{http://www.w3.org/2000/09/xmldsig#}SignedInfo"
            )
            if signed_info is None:
                raise ValueError("No se encontró SignedInfo en la firma")

            # Obtener valor de firma
            signature_value = signature.find(
                ".//{http://www.w3.org/2000/09/xmldsig#}SignatureValue"
            )
            if signature_value is None:
                raise ValueError("No se encontró SignatureValue en la firma")

            # Obtener digest almacenado
            digest_value = signed_info.find(
                ".//{http://www.w3.org/2000/09/xmldsig#}DigestValue"
            )
            if digest_value is None:
                raise ValueError("No se encontró DigestValue en la firma")

            # Remover firma para calcular digest del documento original
            root.remove(signature)
            canonicalized = etree.tostring(root)
            digest = hashes.Hash(hashes.SHA256())
            digest.update(canonicalized)
            current_digest = digest.finalize().hex()

            # Verificar que el digest coincida
            if current_digest != digest_value.text:
                return False

            # Verificar firma del SignedInfo
            signed_info_canonicalized = etree.tostring(signed_info)
            public_key = self.cert_manager.certificate.public_key()
            if not isinstance(public_key, rsa.RSAPublicKey):
                raise ValueError("El certificado no contiene una clave RSA")

            try:
                public_key.verify(
                    bytes.fromhex(signature_value.text),
                    signed_info_canonicalized,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                return True
            except Exception:
                return False

        except Exception as e:
            raise ValueError(f"Error al verificar firma: {str(e)}")
