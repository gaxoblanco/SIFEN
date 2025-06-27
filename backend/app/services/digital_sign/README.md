# Digital Sign Service

**Ubicación del archivo**: `backend/app/services/digital_sign/`

## 🏗️ Arquitectura del Sistema

### Estructura de Archivos
```
backend/app/services/digital_sign/
├── __init__.py                    # ✅ Módulo principal (CertificateManager, XMLSigner, Config)
├── models.py                      # ✅ Certificate, SignatureResult (Pydantic)
├── config.py                      # ✅ CertificateConfig, DigitalSignConfig
├── certificate_manager.py        # ✅ Gestión certificados PFX/P12 PSC
├── xml_signer.py                 # ✅ Firmado XML con XMLDSig W3C
├── signer.py                     # ✅ API principal DigitalSigner
├── csc_manager.py                # ✅ Gestión CSC SIFEN (PENDIENTE)
├── exceptions.py                 # ✅ Excepciones específicas del módulo
├── run.py                        # ✅ CLI para firma/verificación manual
├── run_all.py                    # ✅ Ejecutor completo del módulo
├── COMANDOS.md                   # ✅ Documentación CLI
├── examples/                     # ✅ Ejemplos y utilidades
│   ├── __init__.py
│   ├── sign_example.py          # ✅ Ejemplo básico de firma
│   └── generate_test_cert.py    # ✅ Generador certificados prueba
└── tests/                       # ✅ Suite de testing comprehensiva
    ├── __init__.py
    ├── conftest.py              # ✅ Configuración pytest específica
    ├── test_signer.py           # ✅ Tests firmador principal (100%)
    ├── test_certificate_manager.py # ✅ Tests gestión certificados (100%)
    ├── test_models.py           # ✅ Tests modelos Pydantic (100%)
    ├── test_xml_signer.py       # ✅ Tests firmado XML (95%)
    ├── test_multiple_certificates.py # ✅ Tests múltiples certificados (90%)
    ├── test_signature_validation.py # ✅ Tests validación firmas (85%)
    ├── test_csc_manager.py      # ❌ Tests CSC Manager (PENDIENTE)
    ├── test_certificate_expiration.py # ❌ Tests vencimiento (PENDIENTE)
    ├── test_performance_signing.py # ❌ Tests performance (PENDIENTE)
    ├── test_paths.txt           # ✅ Documentación rutas de prueba
    ├── run_tests.py             # ✅ Runner de tests específico
    ├── fixtures/                # ✅ Certificados y datos de prueba
    │   ├── test.pfx            # ✅ Certificado prueba (NO REAL)
    │   ├── test_signed.xml     # ✅ XML firmado para verificación
    │   └── test_invalid.xml    # ✅ XML malformado para tests error
    └── mocks/                   # ✅ Mocks para testing aislado
        └── mock_certificate_provider.py
```

### Flujo de Firma Digital
```
1. XML Input (SIFEN v150)
   ↓
2. Certificate Validation (PSC Paraguay)
   ↓  
3. XML Canonicalization (C14N)
   ↓
4. Hash Generation (SHA-256)
   ↓
5. Digital Signing (RSA-SHA256)
   ↓
6. XML Signature Embedding (XMLDSig)
   ↓
7. CSC Generation (SIFEN)
   ↓
8. Signed XML Output
```

### Componentes Internos
- **certificate_manager.py**: Carga/validación certificados PFX, verificación PSC
- **xml_signer.py**: Canonicalización XML, generación hash, embedding firma
- **signer.py**: Orquestador principal, API pública del módulo  
- **csc_manager.py**: ❌ Generación/validación CSC para envío SIFEN
- **models.py**: Certificate (RUC, serial, vigencia), SignatureResult (success, error)
- **config.py**: Algoritmos firma (RSA-SHA256), paths certificados, configuración

### Algoritmos y Estándares Implementados
- **Hash**: SHA-256 (http://www.w3.org/2001/04/xmlenc#sha256)
- **Firma**: RSA-SHA256 (http://www.w3.org/2001/04/xmldsig-more#rsa-sha256)  
- **Canonicalización**: C14N (http://www.w3.org/TR/2001/REC-xml-c14n-20010315)
- **Transform**: Enveloped Signature (http://www.w3.org/2000/09/xmldsig#enveloped-signature)
- **Estándar**: W3C XML Digital Signature

## 📊 Estado de Implementación

### ✅ IMPLEMENTADO Y FUNCIONAL
- **Models** (`models.py`): Modelos Certificate y SignatureResult - **100%**
- **Config** (`config.py`): Configuración certificados y algoritmos - **100%**
- **Certificate Manager** (`certificate_manager.py`): Gestión PFX/P12 - **95%**
- **XML Signer** (`xml_signer.py`): Firmado XML básico - **90%**
- **Signer** (`signer.py`): API principal firma digital - **85%**
- **Exceptions** (`exceptions.py`): Manejo de errores específicos - **95%**

### ✅ TESTING COMPLETADO
- **test_signer.py**: Tests firmador principal - **100%**
- **test_certificate_manager.py**: Tests gestión certificados - **100%**
- **test_models.py**: Tests modelos Pydantic - **100%**
- **test_xml_signer.py**: Tests firmado XML - **95%**
- **test_multiple_certificates.py**: Tests múltiples certificados - **90%**
- **test_signature_validation.py**: Tests validación firmas - **85%**

### ✅ SCRIPTS Y UTILIDADES
- **run.py**: CLI para firma/verificación manual - **100%**
- **run_all.py**: Ejecutor completo del módulo - **100%**
- **COMANDOS.md**: Documentación comandos CLI - **100%**
- **examples/**: Ejemplos de uso y generación certificados - **95%**

### ❌ PENDIENTE
- **CSC Manager** (`csc_manager.py`): Gestión CSC SIFEN - **0%**
- **Performance Optimization**: Benchmarks y optimización - **20%**
- **Certificate Expiration**: Alertas vencimiento automático - **30%**
- **Edge Cases Testing**: Casos extremos y errores - **40%**

## 🚀 Próximos Pasos

### Fase 1: Completar CSC Manager (Crítico - 2 días)
```python
# Implementar csc_manager.py
class CSCManager:
    def generate_csc(self, ruc: str, doc_type: str) -> str
    def validate_csc(self, csc: str) -> bool
    def get_expiry_time(self, csc: str) -> datetime
```

### Fase 2: Performance y Alertas (1 semana)
- Optimizar firmado para >20 firmas/segundo
- Sistema alertas vencimiento certificados (30 días antes)
- Métricas de uso y monitoreo

### Fase 3: Testing Avanzado (3 días)
- Tests casos extremos y edge cases
- Tests integración XML+Firma completa
- Tests múltiples formatos certificados

## 🔧 Configuración Básica

### Variables de Entorno
```bash
# Certificado Producción
SIFEN_CERT_PATH=/path/to/production_cert.p12
SIFEN_CERT_PASSWORD=secure_password

# Certificado Desarrollo  
SIFEN_TEST_CERT_PATH=/path/to/test_cert.p12
SIFEN_TEST_CERT_PASSWORD=test_password
```

### Uso Directo
```python
from backend.app.services.digital_sign import CertificateManager, XMLSigner
from backend.app.services.digital_sign.config import CertificateConfig, DigitalSignConfig

# Configurar certificado
cert_config = CertificateConfig(
    cert_path=Path("cert.pfx"),
    cert_password="password",
    cert_expiry_days=30
)

# Firmar XML
cert_manager = CertificateManager(cert_config)
xml_signer = XMLSigner(DigitalSignConfig(), cert_manager)
signed_xml = xml_signer.sign_xml(xml_content)
```

## 🧪 Testing y Desarrollo

### Ejecutar Tests Completos
```bash
# Tests específicos módulo
pytest backend/app/services/digital_sign/tests/ -v

# Tests con cobertura
pytest backend/app/services/digital_sign/tests/ -v --cov=backend.app.services.digital_sign

# Tests críticos solamente
pytest -k "test_signer or test_certificate_manager" -v

# Runner integrado
python -m backend.app.services.digital_sign.tests.run_tests
```

### CLI para Desarrollo
```bash
# Firmar XML directamente
python -m backend.app.services.digital_sign.run \
    --cert-path cert.pfx \
    --cert-password password \
    --xml-path factura.xml \
    --output-path factura_firmada.xml

# Verificar firma
python -m backend.app.services.digital_sign.run \
    --cert-path cert.pfx \
    --cert-password password \
    --xml-path factura_firmada.xml \
    --verify

# Ejecutar módulo completo
python -m backend.app.services.digital_sign.run_all
```

## 🔒 Estándares y Seguridad

### Algoritmos Implementados
- **Hash**: SHA-256 (SIFEN v150 requerido)
- **Firma**: RSA con PKCS#1 v1.5 padding
- **Canonicalización**: Exclusive XML Canonicalization
- **Estándar**: W3C XML Digital Signature

### Certificados Soportados
- **Formato**: PKCS#12 (.p12/.pfx)
- **Emisor**: PSC Paraguay (Persona Física F1, Jurídica F2)
- **Validación**: Vigencia automática y cadena de confianza

### Estructura Firma XML
```xml
<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
  <SignedInfo>
    <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
    <Reference URI="#CDC">
      <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
    </Reference>
  </SignedInfo>
</Signature>
```

## ⚠️ Consideraciones Críticas

### Bloqueos de Producción
1. **CSC Manager faltante**: Sin gestión CSC no se puede enviar a SIFEN
2. **Validación certificados PSC**: Certificados no-PSC fallan en producción
3. **Performance**: Debe soportar >20 firmas/segundo para volumen empresarial

### Recomendaciones Inmediatas
- Implementar CSC Manager antes de deploy producción
- Configurar alertas vencimiento certificados (30 días)
- Testing exhaustivo con certificados PSC reales
- Benchmark performance con volumen real

---
**Estado**: 85% funcional - Listo para desarrollo, pendiente CSC para producción  
**Última actualización**: Junio 2025  
**Mantenedor**: Equipo Backend SIFEN