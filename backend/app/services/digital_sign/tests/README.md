# 🔐 Digital Sign - Tests Módulo Firma Digital

**Servicio**: `backend/app/services/digital_sign/`  
**Propósito**: Firma digital XML con certificados PFX/P12 y gestión CSC  
**Estándares**: XMLDSig, PKCS#12, PSC Paraguay  
**Criticidad**: 🔴 **BLOQUEANTE PRODUCCIÓN**

---

## 📊 **Inventario Completo de Tests**

### ✅ **Tests EXISTENTES (Implementados y Funcionando)**
```
backend/app/services/digital_sign/tests/
├── ✅ conftest.py                         # Configuración pytest específica digital_sign
├── ✅ test_signer.py                      # ⭐ Tests del firmador digital principal (COMPLETO)
├── ✅ test_certificate_manager.py         # ⭐ Tests gestión certificados PFX (COMPLETO)
├── fixtures/
│   └── ✅ test_certificate.pfx            # Certificado de prueba (NO REAL)
├── ✅ test_csc_manager.py                 # 🔴 CRÍTICO - Gestión CSC SIFEN (COMPLETO)
├── ✅ test_signature_validation.py        # 🔴 CRÍTICO - Validación firmas existentes (COMPLETO)
├── ✅ test_certificate_expiration.py      # 🟡 ALTO - Vencimiento certificados (COMPLETO)
├── ✅ test_multiple_certificates.py       # 🟡 ALTO - Múltiples certificados empresa (COMPLETO)
├── 🟡 test_performance_signing.py         # 🟡 ALTO - Performance y 
```


## 📊 **Métricas de Completitud**

### **Cobertura Obligatoria**
```bash
# CRÍTICO: Tests que NO pueden fallar
pytest backend/app/services/digital_sign/tests/test_csc_manager.py -v --tb=short
pytest backend/app/services/digital_sign/tests/test_signature_validation.py -v --tb=short

# ALTO IMPACTO: Tests importantes
pytest backend/app/services/digital_sign/tests/test_certificate_expiration.py -v
pytest backend/app/services/digital_sign/tests/test_multiple_certificates.py -v
pytest backend/app/services/digital_sign/tests/test_performance_signing.py -v

# COMPLETITUD: Tests de funcionalidad completa
pytest backend/app/services/digital_sign/tests/test_edge_cases_certificates.py -v
pytest backend/app/services/digital_sign/tests/test_xml_signature_integration.py -v
pytest backend/app/services/digital_sign/tests/test_certificate_formats.py -v
```


### **Comando Master de Ejecución**
```bash
# Ejecutar TODOS los tests críticos Digital Sign
pytest backend/app/services/digital_sign/tests/ -v \
  --cov=backend.app.services.digital_sign \
  --cov-report=html \
  --tb=short \
  -m "not integration" \
  --maxfail=0

# Solo tests críticos (bloquean producción)
pytest -k "csc_manager or signature_validation" -v --maxfail=0

# Tests de performance (con benchmarks)
pytest backend/app/services/digital_sign/tests/test_performance_signing.py -v --benchmark-only
```

---

## 📚 **Referencias Técnicas**

- **XMLDSig Specification** - W3C Digital Signature estándar
- **PKCS#12 Standard** - Formato certificados PFX/P12  
- **Manual Técnico SIFEN v150** - Requisitos firma digital Paraguay
- **PSC Paraguay** - Autoridad certificadora oficial Paraguay
- **RFC 3369** - Cryptographic Message Syntax (CMS)

**IMPORTANTE**: Este README es un documento vivo que debe actualizarse conforme se implementen los tests y se descubran nuevos requisitos durante las pruebas con certificados reales.