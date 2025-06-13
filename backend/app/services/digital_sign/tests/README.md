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
```

### ❌ **Tests RESTANTES (Por Implementar)**
```
backend/app/services/digital_sign/tests/
├── ❌ test_signature_validation.py        # 🔴 CRÍTICO - Validación firmas existentes
├── ❌ test_certificate_expiration.py      # 🟡 ALTO - Vencimiento certificados
├── ❌ test_multiple_certificates.py       # 🟡 ALTO - Múltiples certificados empresa
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

#### **1. test_csc_manager.py** - Gestión CSC (Código Seguridad Contribuyente)
```python
"""
OBJETIVO: Validar generación y gestión CSC según SIFEN
ALGORITMO: Específico Paraguay (entropy mínima 128 bits)
FORMATOS: Alfanumérico 9 caracteres exactos
"""

class TestCSCManager:
    
    def test_generate_valid_csc_code(self):
        """Generar CSC válido según algoritmo SIFEN"""
        # Longitud exacta: 9 caracteres
        # Solo alfanuméricos: A-Z, 0-9
        # Entropy mínima: 128 bits
        
    def test_csc_format_validation(self):
        """Validar formato CSC estricto"""
        # Debe rechazar: símbolos especiales, minúsculas, <9 chars
        
    def test_csc_collision_detection(self):
        """Detectar colisiones en generación CSC"""
        # Generar 1000 CSCs, todos únicos
        
    def test_csc_with_certificate_binding(self):
        """CSC vinculado correctamente con certificado"""
        # CSC debe asociarse con certificado específico
```

#### **2. test_signature_validation.py** - Validación Firmas Digitales
```python
"""
OBJETIVO: Validar firmas XML existentes exhaustivamente
ALGORITMOS: RSA-SHA256, RSA-SHA1 (legacy)
ESTÁNDAR: XMLDSig W3C compliance
"""

class TestSignatureValidation:
    
    def test_valid_xmldsig_signature(self):
        """Validar firma XMLDSig correcta"""
        # Signature, SignedInfo, Reference válidos
        # Canonicalización C14N correcta
        
    def test_tampered_document_detection(self):
        """Detectar alteración documento firmado"""
        # Modificar XML después de firma → debe fallar
        
    def test_certificate_chain_validation(self):
        """Validar cadena completa certificado"""
        # Desde certificado hasta CA raíz PSC
        
    def test_revoked_certificate_detection(self):
        """Detectar certificado revocado"""
        # Consulta CRL/OCSP cuando disponible
```

#### **3. test_certificate_expiration.py** - Gestión Vencimiento
```python
"""
OBJETIVO: Gestión completa ciclo vida certificados
ALERTAS: 90, 30, 7 días antes vencimiento
ACCIONES: Bloqueo automático post-vencimiento
"""

class TestCertificateExpiration:
    
    def test_certificate_validity_check(self):
        """Verificar vigencia certificado actual"""
        # Validar: not_before <= now <= not_after
        
    def test_expiration_warning_thresholds(self):
        """Alertas pre-vencimiento escalonadas"""
        # 90 días: INFO, 30 días: WARNING, 7 días: CRITICAL
        
    def test_expired_certificate_rejection(self):
        """Rechazar certificado vencido automáticamente"""
        # Debe fallar firma con certificado expirado
        
    def test_grace_period_handling(self):
        """Período gracia post-vencimiento"""
        # 24h gracia para completar procesos iniciados
```

---

## 🟡 **Tests de Alto Impacto**

#### **4. test_multiple_certificates.py** - Múltiples Certificados
```python
"""
OBJETIVO: Gestión múltiples certificados por empresa
ESCENARIOS: Primario/backup, rotación, selección automática
"""

class TestMultipleCertificates:
    
    def test_primary_backup_selection(self):
        """Selección certificado primario con backup"""
        # Primario disponible → usar primario
        # Primario no disponible → usar backup
        
    def test_certificate_rotation_workflow(self):
        """Rotación ordenada de certificados"""
        # Proceso: nuevo → test → activar → deprecar anterior
        
    def test_concurrent_signing_multiple_certs(self):
        """Firma concurrente con certificados distintos"""
        # Múltiples procesos, certificados diferentes, sin conflictos
```

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