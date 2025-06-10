# 🧪 Tests SIFEN Client - Plan de Testing Completo

## 📁 Estado Actual de Tests

### ✅ **Tests Existentes (Implementados)**
```
backend/app/services/sifen_client/tests/
├── conftest.py                    # Configuración pytest global
├── run_sifen_tests.py            # Runner personalizado
├── test_sifen_integration.py     # Tests de integración vs SIFEN real
├── test_client.py                # Tests del cliente SOAP básico
├── test_document_sender.py       # Tests del orquestador principal ⭐
├── test_document_status.py       # Tests de estados de documento ⭐
├── fixtures/
│   ├── test_documents.py         # Fixtures de documentos XML
│   └── test_config.py            # Configuración automática tests
└── mocks/
    └── mock_soap_client.py       # Mock cliente SOAP
```

### 🆕 **Tests Críticos Faltantes (Por Implementar)**
```
backend/app/services/sifen_client/tests/
├── test_sifen_error_codes.py            # 🔴 CRÍTICO - Códigos específicos v150
├── test_time_limits_validation.py       # 🔴 CRÍTICO - Límites 72h/720h
├── test_certificate_validation.py       # 🔴 CRÍTICO - Certificados PSC
├── test_document_size_limits.py         # 🟡 ALTO - Tamaños y límites
├── test_concurrency_rate_limits.py      # 🟡 ALTO - Rate limiting SIFEN
├── test_currency_amount_validation.py   # 🟡 ALTO - Monedas y montos
├── test_contingency_mode.py             # 🟢 MEDIO - Modo contingencia
├── test_document_types_specific.py      # 🟢 MEDIO - AFE, NCE, NDE, NRE
├── test_async_batch_workflow.py         # 🟢 MEDIO - Lotes asíncronos
└── test_encoding_special_chars.py       # 🟢 MEDIO - UTF-8 y guaraní
```

---

## 🎯 **Roadmap de Implementación**

### **FASE 1: Tests Críticos (Bloquean Producción)**

#### **1. test_sifen_error_codes.py** 🔴
**Objetivo**: Validar manejo correcto de códigos específicos SIFEN v150

**Tests Más Importantes**:
```python
class TestSifenSpecificErrorCodes:
    # Códigos CDC (1000-1099)
    test_error_code_1000_cdc_mismatch()           # CDC no corresponde
    test_error_code_1001_cdc_duplicated()         # CDC duplicado
    test_error_code_1002_cdc_malformed()          # CDC mal formado
    
    # Códigos Timbrado (1100-1199)
    test_error_code_1101_invalid_timbrado()       # Timbrado inválido
    test_error_code_1102_expired_timbrado()       # Timbrado vencido
    test_error_code_1103_unauthorized_timbrado()  # Timbrado no autorizado
    
    # Códigos RUC (1250-1299)
    test_error_code_1250_ruc_emisor_not_found()   # RUC emisor inexistente
    test_error_code_1255_ruc_receptor_invalid()   # RUC receptor inválido
    test_error_code_1251_ruc_emisor_inactive()    # RUC emisor inactivo
    
    # Códigos Firma Digital (0140-0149)
    test_error_code_0141_invalid_signature()      # Firma digital inválida
    test_error_code_0142_expired_certificate()    # Certificado vencido
    test_error_code_0143_revoked_certificate()    # Certificado revocado
    
    # Códigos Sistema (5000+)
    test_error_code_5001_internal_server_error()  # Error interno servidor
    test_error_code_5002_maintenance_mode()       # Servidor en mantenimiento
    test_error_code_5003_database_timeout()       # Timeout base datos

class TestErrorCodeMapping:
    test_error_category_mapping()                 # Mapeo código -> categoría
    test_error_severity_classification()          # Clasificación severidad
    test_user_friendly_messages()                 # Mensajes user-friendly
    test_retry_recommendations()                  # Recomendaciones retry
```

#### **2. test_time_limits_validation.py** 🔴
**Objetivo**: Validar límites críticos de tiempo según Manual v150

**Tests Más Importantes**:
```python
class TestTimeValidationLimits:
    # Límites 72 horas (Normal -> Extemporáneo)
    test_document_at_71_hours_normal()            # 71h = Normal
    test_document_at_72_hours_boundary()          # 72h = Límite exacto
    test_document_at_73_hours_extemporaneous()    # 73h = Extemporáneo
    
    # Límites 720 horas (Extemporáneo -> Rechazado)
    test_document_at_719_hours_late_accepted()    # 719h = Aún aceptado
    test_document_at_720_hours_boundary()         # 720h = Límite exacto
    test_document_at_721_hours_rejected()         # 721h = Rechazado
    
    # Casos edge críticos
    test_document_future_date_rejection()         # Fecha futura
    test_document_weekend_holiday_calculation()   # Días no laborables
    test_timezone_handling_paraguay()             # Zona horaria Paraguay

class TestTimeCalculationAccuracy:
    test_leap_year_calculation()                  # Años bisiestos
    test_daylight_saving_time()                   # Horario de verano
    test_millisecond_precision_boundaries()       # Precisión milisegundos
```

#### **3. test_certificate_validation.py** 🔴
**Objetivo**: Validar certificados PSC Paraguay específicos

**Tests Más Importantes**:
```python
class TestPSCCertificateValidation:
    # Tipos de certificado PSC
    test_psc_f1_certificate_validation()          # Certificado F1
    test_psc_f2_certificate_validation()          # Certificado F2
    test_non_psc_certificate_rejection()          # No PSC = rechazo
    
    # Validación RUC en certificado
    test_ruc_in_serial_number_juridica()          # RUC en SerialNumber (jurídica)
    test_ruc_in_subject_alt_name_fisica()         # RUC en SubjectAlternativeName (física)
    test_ruc_mismatch_certificate_document()      # RUC certificado ≠ documento
    
    # Estados del certificado
    test_expired_certificate_rejection()          # Certificado vencido
    test_revoked_certificate_rejection()          # Certificado revocado
    test_not_yet_valid_certificate()              # Certificado futuro

class TestCertificateChainValidation:
    test_psc_root_ca_validation()                 # Validación cadena PSC
    test_intermediate_ca_validation()             # CAs intermedias
    test_crl_checking()                          # Lista revocación
    test_ocsp_validation()                       # Validación OCSP
```

---

### **FASE 2: Tests de Alto Impacto**

#### **4. test_document_size_limits.py** 🟡
**Objetivo**: Validar límites exactos del Manual v150

**Tests Más Importantes**:
```python
class TestDocumentSizeLimits:
    test_individual_document_max_size()           # Límite individual
    test_batch_max_documents_50()                 # Máx 50 docs en lote
    test_batch_total_size_limit()                 # Tamaño total lote
    test_xml_complexity_limits()                  # Niveles anidamiento
    test_base64_attachment_limits()               # Adjuntos base64

class TestPerformanceUnderLimits:
    test_large_document_processing_time()         # Tiempo docs grandes
    test_memory_usage_large_batches()             # Uso memoria lotes
    test_streaming_large_documents()              # Streaming docs grandes
```

#### **5. test_concurrency_rate_limits.py** 🟡
**Objetivo**: Validar rate limiting y concurrencia SIFEN

**Tests Más Importantes**:
```python
class TestSifenRateLimits:
    test_rate_limit_per_ruc_per_minute()          # Límite por RUC/minuto
    test_concurrent_requests_same_ruc()           # Requests concurrentes
    test_rate_limit_exceeded_handling()           # Manejo límite excedido
    test_backoff_strategy_rate_limits()           # Estrategia backoff

class TestConcurrencyControl:
    test_multiple_clients_same_ruc()              # Múltiples clientes
    test_client_side_rate_limiting()              # Rate limiting cliente
    test_circuit_breaker_rate_limits()            # Circuit breaker
```

#### **6. test_currency_amount_validation.py** 🟡
**Objetivo**: Validar monedas y montos según Manual v150

**Tests Más Importantes**:
```python
class TestCurrencyValidation:
    test_pyg_currency_validation()                # Guaraníes (PYG)
    test_usd_currency_validation()                # Dólares (USD)
    test_eur_currency_validation()                # Euros (EUR)
    test_invalid_currency_rejection()             # Monedas inválidas

class TestAmountCalculations:
    test_pyg_no_decimals_validation()             # PYG sin decimales
    test_usd_decimal_precision()                  # USD 2 decimales
    test_tax_calculation_accuracy()               # Cálculo IVA preciso
    test_rounding_rules_by_currency()             # Reglas redondeo
```

---

### **FASE 3: Tests de Completitud Funcional**

#### **7. test_contingency_mode.py** 🟢
**Objetivo**: Validar modo contingencia según Manual v150

**Tests Más Importantes**:
```python
class TestContingencyMode:
    test_primary_endpoint_failure_fallback()      # Failover automático
    test_contingency_mode_activation()            # Activación contingencia
    test_contingency_document_submission()        # Envío en contingencia
    test_normal_mode_restoration()                # Restauración modo normal

class TestContingencyWorkflow:
    test_offline_queue_management()               # Cola offline
    test_batch_submission_after_restore()         # Envío masivo post-restauración
    test_contingency_status_reporting()           # Reporte estado contingencia
```

#### **8. test_document_types_specific.py** 🟢
**Objetivo**: Validar tipos específicos AFE, NCE, NDE, NRE

**Tests Más Importantes**:
```python
class TestAutoFacturaElectronica:
    test_afe_import_validation()                  # Validaciones AFE importación
    test_afe_required_fields()                    # Campos obligatorios AFE
    test_afe_tax_calculation()                    # Cálculo impuestos AFE

class TestNotaCredito:
    test_nce_reference_validation()               # Referencia doc original NCE
    test_nce_amount_limits()                      # Límites montos NCE
    test_nce_tax_reversal()                       # Reversión impuestos NCE

class TestNotaDebito:
    test_nde_additional_charges()                 # Cargos adicionales NDE
    test_nde_interest_calculation()               # Cálculo intereses NDE

class TestNotaRemision:
    test_nre_transport_validation()               # Validaciones transporte NRE
    test_nre_goods_description()                  # Descripción mercadería NRE
```

#### **9. test_async_batch_workflow.py** 🟢
**Objetivo**: Validar workflow completo de lotes asíncronos

**Tests Más Importantes**:
```python
class TestAsyncBatchWorkflow:
    test_batch_submission_async()                 # Envío lote asíncrono
    test_batch_status_polling()                   # Polling estado lote
    test_batch_partial_processing()               # Procesamiento parcial
    test_batch_completion_notification()          # Notificación completitud

class TestBatchStatusManagement:
    test_individual_document_status_in_batch()    # Estado docs individuales
    test_batch_cancellation()                     # Cancelación lote
    test_batch_timeout_handling()                 # Manejo timeout lote
```

#### **10. test_encoding_special_chars.py** 🟢
**Objetivo**: Validar encoding UTF-8 y caracteres especiales Paraguay

**Tests Más Importantes**:
```python
class TestUTF8Encoding:
    test_guarani_characters()                     # Caracteres guaraní
    test_spanish_special_chars()                  # Ñ, acentos, etc.
    test_xml_entity_escaping()                    # Escape entidades XML
    test_base64_encoding_attachments()            # Adjuntos base64

class TestCharacterLimits:
    test_max_string_lengths()                     # Longitudes máximas campos
    test_invalid_character_rejection()            # Caracteres inválidos
    test_emoji_handling()                         # Manejo emojis
```

---

## 🚀 **Comandos de Ejecución**

### **Ejecutar Tests por Prioridad**
```bash
# CRÍTICOS (deben pasar en producción)
pytest -v -k "test_sifen_error_codes or test_time_limits or test_certificate"

# ALTO IMPACTO
pytest -v -k "test_document_size or test_concurrency or test_currency"

# COMPLETITUD
pytest -v -k "test_contingency or test_document_types or test_async_batch or test_encoding"
```

### **Ejecutar por Archivo Específico**
```bash
# Tests de códigos de error específicos
pytest backend/app/services/sifen_client/tests/test_sifen_error_codes.py -v

# Tests de límites de tiempo
pytest backend/app/services/sifen_client/tests/test_time_limits_validation.py -v

# Con coverage específico
pytest backend/app/services/sifen_client/tests/test_certificate_validation.py --cov=app.services.sifen_client.document_sender -v
```

### **Tests Existentes (Ya Funcionando)**
```bash
# Orquestador principal (MUY COMPLETO)
pytest backend/app/services/sifen_client/tests/test_document_sender.py -v

# Estados de documento (EXHAUSTIVO)  
pytest backend/app/services/sifen_client/tests/test_document_status.py -v

# Integración real SIFEN
pytest backend/app/services/sifen_client/tests/test_sifen_integration.py -v -m integration
```

---

## 📊 **Métricas de Completitud**

### **Estado Actual vs Objetivo**
```
✅ Tests Básicos:          2/2  (100%) - document_sender + document_status
🔄 Tests Específicos:      0/10 (0%)   - Códigos error, límites, etc.
🔄 Tests Integración:      1/3  (33%)  - Solo SIFEN básico
📊 Cobertura Estimada:     60%         - Objetivo: 90%+
```

### **Prioridad de Implementación**
1. **🔴 CRÍTICO**: test_sifen_error_codes.py (2-3 horas)
2. **🔴 CRÍTICO**: test_time_limits_validation.py (2 horas)  
3. **🔴 CRÍTICO**: test_certificate_validation.py (3 horas)
4. **🟡 ALTO**: test_document_size_limits.py (1 hora)
5. **🟡 ALTO**: test_concurrency_rate_limits.py (2 horas)

---

## 💡 **Estrategia de Implementación**

### **Enfoque Modular**
- **Un archivo por sesión** (2-3 horas por archivo)
- **Tests independientes** entre archivos
- **Fixtures reutilizables** en `conftest.py`
- **Mocks específicos** por tipo de test

### **Metodología TDD**
1. **Escribir test que falle** para caso específico
2. **Implementar mínimo código** para pasar test
3. **Refactorizar y optimizar** código
4. **Agregar casos edge** y validaciones

### **Criterio de Aceptación**
- ✅ **Todos los tests pasan** en ambiente local
- ✅ **Coverage >80%** por archivo
- ✅ **Tests rápidos** (<500ms por test)
- ✅ **Documentación clara** por test crítico
- ✅ **Casos edge cubiertos** para cada funcionalidad

---

## 🎯 **Objetivos por Fase**

### **Fase 1 Completada** ➜ **Document Sender Indestructible**
- Maneja todos los códigos SIFEN v150
- Respeta límites de tiempo exactos  
- Valida certificados PSC correctamente
- **Ready para producción básica**

### **Fase 2 Completada** ➜ **Production Ready**
- Maneja límites de tamaño y concurrencia
- Soporte completo de monedas
- **Ready para carga media de producción**

### **Fase 3 Completada** ➜ **Enterprise Ready**
- Modo contingencia automático
- Todos los tipos de documento
- Lotes asíncronos y encoding completo
- **Ready para enterprise scale**

---
