# 🌐 SIFEN Client - Tests Críticos Obligatorios v150

**Servicio**: `backend/app/services/sifen_client/`  
**Documentación Base**: Manual Técnico SIFEN v150  
**Ambiente Target**: SIFEN Paraguay (sifen.set.gov.py)  
**Criticidad**: 🔴 **BLOQUEANTE PRODUCCIÓN**

---

## 📊 **Inventario Completo de Tests**

### ✅ **Tests EXISTENTES (Implementados y Funcionando)**
```
backend/app/services/sifen_client/tests/
├── ✅ conftest.py                         # Configuración pytest global
├── ✅ run_sifen_tests.py                  # Runner personalizado con opciones
├── ✅ test_client.py                      # ⭐ Tests del cliente SOAP básico (COMPLETO)
├── ✅ test_document_sender.py             # ⭐ Tests del orquestador principal (MUY COMPLETO)
├── ✅ test_document_status.py             # ⭐ Tests de estados de documento (EXHAUSTIVO)
├── ✅ test_mock_soap_client.py           # ⭐ Tests del mock SOAP (ROBUSTO)
├── ✅ test_sifen_error_codes.py          # 🔴 CRÍTICO - Códigos específicos v150 (COMPLETO ✅)
├── ✅ test_time_limits_validation.py     # 🔴 CRÍTICO - Límites 72h/720h (COMPLETO ✅)
├── ✅ test_certificate_validation.py      # 🔴 CRÍTICO - Certificados PSC (COMPLETO ✅)
├── ✅ test_document_size_limits.py        # 🟡 ALTO - Tamaños y límites (COMPLETO ✅)
├── ✅ test_concurrency_rate_limits.py     # 🟡 ALTO - Rate limiting SIFEN (COMPLETO ✅)
├── ✅ test_currency_amount_validation.py  # 🟡 ALTO - Monedas y montos (COMPLETO ✅)
├── ✅ test_contingency_mode.py            # 🟢 MEDIO - Modo contingencia (COMPLETO ✅)
├── ❌ test_sifen_integration.py          # 🚫 DEPRECADO - Reemplazado por tests modulares
├── fixtures/
│   ├── ✅ test_documents.py               # Fixtures de documentos XML con datos reales
│   └── ✅ test_config.py                  # Configuración automática para tests
└── mocks/
    └── ✅ mock_soap_client.py             # Mock cliente SOAP con respuestas realistas
```

### ❌ **Tests RESTANTES (Por Implementar)**
```
backend/app/services/sifen_client/tests/
(ÚNICO CRÍTICO RESTANTE)
├── ❌ test_document_types_specific.py     # 🟢 MEDIO - AFE, NCE, NDE, NRE
├── ❌ test_async_batch_workflow.py        # 🟢 MEDIO - Lotes asíncronos
└── ❌ test_encoding_special_chars.py      # 🟢 MEDIO - UTF-8 y guaraní
```


#### **8. test_document_types_specific.py** - Tipos de Documento
```python
"""
OBJETIVO: Validar tipos específicos según Manual v150
TIPOS: AFE (4), NCE (5), NDE (6), NRE (7)
VALIDACIONES: Campos obligatorios únicos por tipo
"""

class TestSpecificDocumentTypes:
    
    def test_autofactura_afe_type_4(self):
        """Autofactura Electrónica (AFE) - Código 4"""
        # Campos específicos para AFE
        # Validaciones particulares
        
    def test_nota_credito_nce_type_5(self):
        """Nota de Crédito Electrónica (NCE) - Código 5"""
        # Debe referenciar factura original
        # Montos no pueden superar original
        
    def test_nota_debito_nde_type_6(self):
        """Nota de Débito Electrónica (NDE) - Código 6"""
        # Campos específicos para débito
        
    def test_nota_remision_nre_type_7(self):
        """Nota de Remisión Electrónica (NRE) - Código 7"""
        # Sin montos, solo productos/servicios
        # Campos de transporte obligatorios
```

#### **9. test_async_batch_workflow.py** - Flujo Lotes Asíncronos
```python
"""
OBJETIVO: Validar procesamiento lotes asíncronos
ENDPOINT: /de/ws/async/recibe-lote.wsdl
LÍMITES: Hasta 50 documentos por lote
"""

class TestAsyncBatchWorkflow:
    
    def test_batch_submission_workflow(self):
        """Flujo completo envío lote asíncrono"""
        # 1. Enviar lote de 10 documentos
        # 2. Recibir número de lote
        # 3. Consultar estado del lote
        # 4. Obtener resultados individuales
        
    def test_batch_status_polling(self):
        """Polling de estado de lote hasta completar"""
        # Estados: EN_PROCESO, COMPLETADO, ERROR
        # Polling cada 30 segundos hasta estado final
        
    def test_partial_batch_failures(self):
        """Manejo de fallos parciales en lote"""
        # Lote con 5 documentos válidos + 5 inválidos
        # Debe procesar válidos y reportar errores específicos
```

#### **10. test_encoding_special_chars.py** - Codificación UTF-8
```python
"""
OBJETIVO: Validar codificación UTF-8 y caracteres especiales
CARACTERES: Guaraní (ã, ẽ, ĩ, õ, ũ, ỹ), tildes, ñ, símbolos
ENCODING: UTF-8 sin BOM obligatorio
"""

class TestEncodingValidation:
    
    def test_guarani_characters(self):
        """Caracteres específicos del guaraní"""
        # ã, ẽ, ĩ, õ, ũ, ỹ, Ã, Ẽ, Ĩ, Õ, Ũ, Ỹ
        text_guarani = "Pytã, kañy, mitã"
        # Debe ser aceptado sin corrupción
        
    def test_spanish_characters(self):
        """Caracteres del español: ñ, tildes"""
        text_spanish = "Empresa Ñandú & Cía. S.A."
        # Debe ser aceptado correctamente
        
    def test_special_symbols(self):
        """Símbolos especiales permitidos"""
        symbols = "& < > \" ' % @ # $ ( ) [ ] { }"
        # Debe escaparse correctamente en XML
        
    def test_utf8_without_bom(self):
        """UTF-8 sin BOM (obligatorio)"""
        # XML debe empezar con <?xml encoding="UTF-8"?>
        # Sin bytes BOM (EF BB BF)
```

---

## 📊 **Métricas de Completitud**


## 🎯 **Plan de Implementación**

### **Fase 1: Tests Críticos (Semana 1-2)**
1. **test_sifen_error_codes.py** - 2 días
2. **test_time_limits_validation.py** - 1 día  
3. **test_certificate_validation.py** - 2 días

### **Fase 2: Tests Altos (Semana 3)**
4. **test_document_size_limits.py** - 1 día
5. **test_concurrency_rate_limits.py** - 1 día
6. **test_currency_amount_validation.py** - 1 día

### **Fase 3: Tests Completitud (Semana 4)**
7. **test_contingency_mode.py** - 1 día
8. **test_document_types_specific.py** - 1 día
9. **test_async_batch_workflow.py** - 1 día
10. **test_encoding_special_chars.py** - 1 día

### **Comando Master de Ejecución**
```bash
# Ejecutar TODOS los tests críticos SIFEN
pytest backend/app/services/sifen_client/tests/ -v \
  --cov=backend.app.services.sifen_client \
  --cov-report=html \
  --tb=short \
  -m "not integration" \
  --maxfail=0

# Solo tests críticos (bloquean producción)
pytest -k "error_codes or time_limits or certificate" -v --maxfail=0

# Tests de integración real (requiere certificados válidos)
pytest -m integration -v --tb=long
```

---

## 📚 **Referencias Técnicas**

- **Manual Técnico SIFEN v150** - Autoridad definitiva
- **Esquemas XSD v150** - Validación estructura XML
- **Códigos de Error SET** - Mapeo oficial de errores
- **PSC Paraguay** - Certificados digitales autorizados
- **BCP Paraguay** - Monedas y tipos de cambio oficiales

**IMPORTANTE**: Este README es un documento vivo que debe actualizarse conforme se implementen los tests y se descubran nuevos requisitos durante las pruebas con el ambiente real de SIFEN.
