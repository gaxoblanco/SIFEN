# Módulo: Digital Sign

## Propósito
Maneja la firma digital de documentos XML para el sistema SIFEN Paraguay, incluyendo la gestión de certificados digitales PSC y la generación/verificación de firmas XML según especificaciones SIFEN v150.

Este módulo es **crítico** para el cumplimiento normativo - todos los documentos electrónicos deben estar firmados digitalmente antes del envío a SIFEN.

## API Pública

### DigitalSigner
Clase principal para manejar la firma digital de documentos SIFEN.

- `__init__(certificate: Certificate)` - Inicializa el firmador con un certificado
- `sign_xml(xml_content: str) -> SignatureResult` - Firma un documento XML
- `verify_signature(xml_content: str, signature: Optional[str]) -> bool` - Verifica una firma digital

### Certificate (Modelo)
Modelo Pydantic para certificados digitales según SIFEN.

```python
Certificate(
    ruc: str,                    # RUC del titular del certificado
    serial_number: str,          # Número de serie del certificado
    valid_from: datetime,        # Fecha de inicio de validez
    valid_to: datetime,          # Fecha de fin de validez
    certificate_path: str,       # Ruta al archivo del certificado (.p12)
    password: Optional[str]      # Contraseña del certificado
)
```

### SignatureResult (Modelo)
Resultado de la operación de firma digital.

```python
SignatureResult(
    success: bool,                    # Indica si la firma fue exitosa
    error: Optional[str],             # Mensaje de error si falló
    timestamp: datetime,              # Fecha y hora de la firma
    signature: Optional[str],         # Firma digital en base64
    certificate_serial: Optional[str], # Número de serie del certificado usado
    signature_algorithm: Optional[str] # Algoritmo usado para la firma
)
```

## Dependencias
- **Externa**: `cryptography`, `base64`, `datetime`
- **Interna**: `.models` (Certificate, SignatureResult)

## Uso Básico

```python
from datetime import datetime, timedelta
from .models import Certificate
from .signer import DigitalSigner

# 1. Configurar certificado
certificate = Certificate(
    ruc="12345678-9",
    serial_number="1234567890",
    valid_from=datetime.now(),
    valid_to=datetime.now() + timedelta(days=365),
    certificate_path="/path/to/certificate.p12",
    password="mi_password_seguro"
)

# 2. Crear firmador
signer = DigitalSigner(certificate)

# 3. Firmar documento XML
xml_content = "<rDE>...</rDE>"
result = signer.sign_xml(xml_content)

if result.success:
    print(f"Documento firmado exitosamente")
    print(f"Firma: {result.signature}")
    print(f"Certificado: {result.certificate_serial}")
else:
    print(f"Error al firmar: {result.error}")

# 4. Verificar firma
is_valid = signer.verify_signature(xml_content, result.signature)
print(f"Firma válida: {is_valid}")
```

## Configuración de Certificados

### Certificados PSC Paraguay
Este módulo trabaja con certificados digitales emitidos por PSC (Paraguay Seguro Certificado):

- **Formato**: PKCS#12 (.p12 o .pfx)
- **Tipos**: F1 (Persona Física) o F2 (Persona Jurídica)
- **Algoritmo**: RSA con SHA-256
- **Vigencia**: Verificada al momento de la firma

### Variables de Entorno
```bash
# Certificado de producción
SIFEN_CERT_PATH=/path/to/production_cert.p12
SIFEN_CERT_PASSWORD=secure_password

# Certificado de desarrollo/test
SIFEN_TEST_CERT_PATH=/path/to/test_cert.p12
SIFEN_TEST_CERT_PASSWORD=test_password
```

## Tests

### Ejecutar Tests
```bash
# Tests específicos del módulo
pytest backend/app/services/digital_sign/tests/ -v

# Con cobertura
pytest backend/app/services/digital_sign/tests/ -v --cov

# Test específico
pytest backend/app/services/digital_sign/tests/test_signer.py -v
```

### Estructura de Tests
```
tests/
├── __init__.py
├── test_models.py          # Tests de modelos Pydantic
├── test_signer.py          # Tests del firmador digital
├── fixtures/               # Certificados y datos de prueba
└── mocks/                  # Mocks para testing
```

### Tests Implementados
- ✅ Creación y validación de certificados
- ✅ Firma digital de documentos XML
- ✅ Verificación de firmas
- ✅ Manejo de errores (certificados inválidos, expirados)
- ✅ Casos límite y edge cases

## Algoritmos y Estándares

### Firma Digital
- **Estándar**: W3C XML Digital Signature
- **Algoritmo Hash**: SHA-256
- **Algoritmo Firma**: RSA con PKCS#1 v1.5 padding
- **Canonicalización**: Exclusive XML Canonicalization
- **Codificación**: Base64

### Estructura de Firma XML
```xml
<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
  <SignedInfo>
    <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
    <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
    <Reference URI="#CDC_DEL_DOCUMENTO">
      <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
      <DigestValue>...</DigestValue>
    </Reference>
  </SignedInfo>
  <SignatureValue>...</SignatureValue>
  <KeyInfo>
    <X509Data>
      <X509Certificate>...</X509Certificate>
    </X509Data>
  </KeyInfo>
</Signature>
```

## Troubleshooting

### Errores Comunes

**Error: "No se pudo cargar el certificado"**
- ✅ Verificar que la ruta al archivo .p12/.pfx sea correcta
- ✅ Verificar permisos de lectura del archivo
- ✅ Verificar que el archivo no esté corrupto

**Error: "Error al cargar el certificado: [error específico]"**
- ✅ Verificar que la contraseña del certificado sea correcta
- ✅ Verificar que el formato del certificado sea PKCS#12
- ✅ Verificar que el certificado contenga tanto la clave privada como el certificado público

**Error: "La clave privada debe ser RSA"**
- ✅ El certificado debe contener una clave privada RSA
- ✅ Verificar que el certificado sea emitido por PSC Paraguay
- ✅ Verificar que el certificado sea de tipo F1 o F2

**Error: "No hay clave privada disponible para firmar"**
- ✅ Verificar que el certificado .p12 contenga la clave privada
- ✅ Verificar que la contraseña sea correcta
- ✅ Regenerar el certificado si está corrupto

**Error de Verificación de Firma**
- ✅ Verificar que el XML no haya sido modificado después de la firma
- ✅ Verificar que la firma corresponda al documento específico
- ✅ Verificar que el certificado usado para firmar sea válido

### Debugging

```python
# Habilitar logging detallado
import logging
logging.basicConfig(level=logging.DEBUG)

# Verificar carga de certificado
try:
    signer = DigitalSigner(certificate)
    print("✅ Certificado cargado correctamente")
except Exception as e:
    print(f"❌ Error cargando certificado: {e}")

# Verificar algoritmos soportados
from cryptography.hazmat.primitives.asymmetric import rsa
print(f"Clave privada es RSA: {isinstance(signer.private_key, rsa.RSAPrivateKey)}")
```

## Integración con Otros Módulos

### Con XML Generator
```python
from ..xml_generator import XMLGenerator
from .signer import DigitalSigner

# Generar XML
generator = XMLGenerator()
xml = generator.generate_simple_invoice_xml(factura)

# Firmar XML generado
signer = DigitalSigner(certificate)
result = signer.sign_xml(xml)
```

### Con SIFEN Client (Próximo módulo)
```python
# El XML firmado será enviado al cliente SIFEN
if result.success:
    # Enviar XML firmado a SIFEN
    sifen_response = sifen_client.send_document(result.signature)
```

## Seguridad

### Consideraciones de Seguridad
- 🔒 **Nunca hardcodear contraseñas** en el código
- 🔒 **Usar variables de entorno** para credenciales
- 🔒 **Validar vigencia** del certificado antes de firmar
- 🔒 **No loggear información sensible** (contraseñas, claves privadas)
- 🔒 **Almacenar certificados** en ubicaciones seguras
- 🔒 **Rotación regular** de certificados según políticas SET

### Mejores Prácticas
```python
# ✅ CORRECTO - Usar variables de entorno
import os
certificate = Certificate(
    certificate_path=os.getenv("SIFEN_CERT_PATH"),
    password=os.getenv("SIFEN_CERT_PASSWORD"),
    # ... otros campos
)

# ❌ INCORRECTO - Hardcodear credenciales
certificate = Certificate(
    certificate_path="/path/to/cert.p12",
    password="mi_password",  # ¡Nunca hacer esto!
    # ... otros campos
)
```

## Estado del Módulo

### Criterios de Completitud ✅
- [x] **Tests unitarios**: >80% cobertura ✅
- [x] **Tests integración**: Implementados ✅  
- [x] **Documentación**: README.md completo ✅
- [x] **Ejemplos de uso**: Funcionando ✅
- [x] **Error handling**: Implementado ✅
- [x] **Logging**: Configurado ✅
- [x] **Sin dependencias circulares**: Validado ✅

### Próximos Pasos
1. **Integración**: Conectar con módulo `sifen_client/`
2. **Optimización**: Performance para firmas en lote
3. **Monitoreo**: Alertas para certificados próximos a vencer

---

**Módulo implementado según**: Manual Técnico SIFEN v150, W3C XML Digital Signature
**Certificados compatibles**: PSC Paraguay (F1, F2)
**Estado**: ✅ **COMPLETO** - Listo para integración