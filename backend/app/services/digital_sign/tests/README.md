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
```

### ❌ **Tests RESTANTES (Por Implementar)**
```
backend/app/services/digital_sign/tests/
├── ❌ test_performance_signing.py         # 🟡 ALTO - Performance y benchmarks
├── ❌ test_edge_cases_certificates.py     # 🟢 MEDIO - Casos extremos y errores
├── ❌ test_xml_signature_integration.py   # 🟢 MEDIO - Integración XML+Firma
├── ❌ test_certificate_formats.py         # 🟢 MEDIO - Múltiples formatos cert
├── fixtures/
│   ├── ❌ expired_certificate.pfx         # Certificado vencido para tests
│   ├── ❌ invalid_certificate.pfx         # Certificado inválido para tests
│   └── ❌ test_xml_documents.py           # XMLs de prueba para firma
└── mocks/
    ├── ❌ mock_certificate_provider.py    # Mock proveedor certificados
    └── ❌ mock_csc_generator.py           # Mock generador CSC
```

---

## 🚨 **Tests Críticos Detallados**

## 🟡 **Tests de Alto Impacto**

#### **5. test_performance_signing.py** - Performance y Benchmarks
```python
"""
OBJETIVO: Validar performance firma digital
TARGETS: <500ms por documento, <5MB RAM por proceso
CONCURRENCIA: Mínimo 10 firmas simultáneas
"""

class TestPerformanceSigning:
    
    def test_single_document_signing_speed(self):
        """Velocidad firma documento individual"""
        # Target: <500ms para XML típico (50KB)
        
    def test_batch_signing_throughput(self):
        """Throughput firma masiva (lotes)"""
        # Target: >100 documentos/minuto
        
    def test_memory_usage_optimization(self):
        """Uso memoria optimizado"""
        # Target: <5MB RAM por proceso firma
        
    def test_concurrent_signing_limits(self):
        """Límites concurrencia firma"""
        # Mínimo: 10 firmas simultáneas sin degradación
```

---

## 🟢 **Tests de Completitud**

#### **6. test_edge_cases_certificates.py** - Casos Extremos
```python
"""
OBJETIVO: Robustez ante certificados problemáticos
CASOS: Corruptos, formatos raros, ataques, etc.
"""

class TestEdgeCasesCertificates:
    
    def test_corrupted_pfx_file_handling(self):
        """Manejo archivo PFX corrupto"""
        # Debe fallar gracefully con error claro
        
    def test_certificate_without_private_key(self):
        """Certificado sin clave privada"""
        # Detectar y reportar error específico
        
    def test_weak_encryption_certificates(self):
        """Certificados con cifrado débil"""
        # Rechazar algoritmos deprecated (MD5, SHA1)
        
    def test_timing_attack_resistance(self):
        """Resistencia ataques de timing"""
        # Operaciones criptográficas en tiempo constante
```

#### **7. test_xml_signature_integration.py** - Integración XML
```python
"""
OBJETIVO: Integración completa XML + Firma Digital
FLUJO: XML generado → firma → validación SIFEN
"""

class TestXMLSignatureIntegration:
    
    def test_xml_generation_to_signing_workflow(self):
        """Flujo completo: XML generado → firmado"""
        # xml_generator → digital_sign → XML firmado válido
        
    def test_signed_xml_sifen_compliance(self):
        """XML firmado cumple requisitos SIFEN"""
        # Estructura firma compatible con validador SIFEN
        
    def test_signature_placement_in_xml(self):
        """Ubicación correcta firma en XML"""
        # <Signature> en posición correcta según schema
```

#### **8. test_certificate_formats.py** - Múltiples Formatos
```python
"""
OBJETIVO: Soporte múltiples formatos certificados
FORMATOS: PFX/P12 (primario), PEM, DER (secundarios)
"""

class TestCertificateFormats:
    
    def test_pfx_p12_format_support(self):
        """Soporte formato PFX/P12 (principal)"""
        # Carga, validación, uso para firma
        
    def test_pem_format_certificates(self):
        """Soporte formato PEM (opcional)"""
        # Conversión PEM → formato interno
        
    def test_format_conversion_utilities(self):
        """Utilidades conversión formatos"""
        # PFX ↔ PEM, validación post-conversión
```

---

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

### **Estados de Implementación**
```
✅ EXISTENTE: test_signer.py (Firmador principal)
✅ EXISTENTE: test_certificate_manager.py (Gestión certificados básica)

🔴 CRÍTICO FALTANTE:
   - test_csc_manager.py (0% - BLOQUEA PRODUCCIÓN)
   - test_signature_validation.py (0% - BLOQUEA PRODUCCIÓN)

🟡 ALTO FALTANTE:
   - test_certificate_expiration.py (0%)
   - test_multiple_certificates.py (0%)
   - test_performance_signing.py (0%)

🟢 MEDIO FALTANTE:
   - test_edge_cases_certificates.py (0%)
   - test_xml_signature_integration.py (0%)
   - test_certificate_formats.py (0%)
```

---

## 🎯 **Plan de Implementación**

### **Fase 1: Tests Críticos (Semana 1)**
1. **test_csc_manager.py** - 2 días
2. **test_signature_validation.py** - 2 días

### **Fase 2: Tests Alto Impacto (Semana 2)**
3. **test_certificate_expiration.py** - 1 día
4. **test_multiple_certificates.py** - 1 día
5. **test_performance_signing.py** - 2 días

### **Fase 3: Tests Completitud (Días finales)**
6. **test_edge_cases_certificates.py** - 1 día
7. **test_xml_signature_integration.py** - 1 día
8. **test_certificate_formats.py** - 1 día

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