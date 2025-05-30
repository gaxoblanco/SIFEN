# Módulo de Firma Digital

## Propósito
Este módulo maneja la firma digital de documentos XML para el sistema SIFEN, incluyendo la gestión de certificados PFX y la generación/verificación de firmas XML.

## API Pública

### CertificateManager
- `load_certificate()` - Carga el certificado y clave privada
- `check_expiry()` - Verifica si el certificado está próximo a expirar
- `certificate` - Propiedad que obtiene el certificado cargado
- `private_key` - Propiedad que obtiene la clave privada cargada

### XMLSigner
- `sign_xml(xml_content: str)` - Firma un documento XML
- `verify_signature(signed_xml: str)` - Verifica la firma de un XML

## Dependencias
- Externa: cryptography, lxml
- Interna: config

## Uso Básico
```python
from .digital_sign import CertificateManager, XMLSigner
from .config import CertificateConfig, DigitalSignConfig

# Configurar certificado
cert_config = CertificateConfig(
    cert_path=Path("cert.pfx"),
    cert_password="secret",
    cert_expiry_days=30
)

# Configurar firma
sign_config = DigitalSignConfig()

# Crear instancias
cert_manager = CertificateManager(cert_config)
xml_signer = XMLSigner(sign_config, cert_manager)

# Firmar XML
signed_xml = xml_signer.sign_xml(xml_content)

# Verificar firma
is_valid = xml_signer.verify_signature(signed_xml)
```

## Tests
```bash
pytest backend/app/services/digital_sign/tests/ -v
```

## Troubleshooting
- Error "Certificado no encontrado": Verificar que la ruta al archivo PFX sea correcta
- Error "Contraseña inválida": Verificar que la contraseña del certificado sea correcta
- Error "Certificado expirado": Renovar el certificado antes de su fecha de expiración
- Error "XML inválido": Asegurar que el XML cumpla con la sintaxis correcta
- Error "Firma inválida": Verificar que el XML no haya sido modificado después de firmar 