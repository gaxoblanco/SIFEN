# 📋 Esquemas XSD SIFEN v150 - Catálogo Completo

**Ubicación**: `backend/app/services/xml_generator/schemas/`  
**Propósito**: Esquemas XSD oficiales para validación documentos SIFEN Paraguay  
**Versión**: 1.5.0 (Septiembre 2019)  
**Namespace**: `http://ekuatia.set.gov.py/sifen/xsd`  

---

## 🎯 **Estado Actual del Proyecto**

### ✅ **Esquemas IMPLEMENTADOS**
```
backend/app/services/xml_generator/schemas/
├── ✅ DE_v150.xsd                     # COMPLETAMENTE CORREGIDO
└── ❌ [FALTANTES] - Ver lista completa abajo
```

### 🚨 **ESQUEMAS CRÍTICOS FALTANTES**
**SIN ESTOS NO FUNCIONA INTEGRACIÓN CON SIFEN**

---

## 📊 **Inventario Completo Esquemas SIFEN v150**

### **🔴 CRÍTICOS (Prioridad 1 - BLOQUEANTE)**

#### **1. Documentos Electrónicos (Core)**
```
✅ DE_v150.xsd                        # Estructura documentos electrónicos
                                      # ✅ IMPLEMENTADO Y CORREGIDO
```

#### **2. Web Services - Envío Individual**
```
✅ siRecepDE_v150.xsd                 # Request envío documento individual
✅ resRecepDE_v150.xsd                # Response envío documento individual
```

#### **3. Firma Digital**
```
✅ xmldsig-core-schema-v150.xsd       # Firma digital XML (W3C estándar)
```

#### **4. Protocolos de Procesamiento**
```
❌ ProtProcesDE_v150.xsd              # Protocolo procesamiento individual
```

### **🟡 ALTO IMPACTO (Prioridad 2 - FUNCIONALIDAD IMPORTANTE)**

#### **5. Web Services - Envío por Lotes**
```
❌ SiRecepLoteDE_v150.xsd             # Request envío lote (hasta 50 docs)
❌ resRecepLoteDE_v150.xsd            # Response envío lote
❌ ProtProcesLoteDE_v150.xsd          # Protocolo procesamiento lote
❌ SiResultLoteDE_v150.xsd            # Request consulta resultado lote
❌ resResultLoteDE_v150.xsd           # Response consulta resultado lote
```

### **🟢 MEDIO (Prioridad 3 - CONSULTAS Y EVENTOS)**

#### **6. Consultas de Documentos**
```
❌ siConsDE_v150.xsd                  # Request consulta documento por CDC
❌ resConsDE_v150.xsd                 # Response consulta documento
```

#### **7. Consultas RUC**
```
❌ siConsRUC_v150.xsd                 # Request consulta datos RUC
❌ resConsRUC_v150.xsd                # Response consulta RUC
```

#### **8. Eventos del Sistema**
```
❌ siRecepEvento_v150.xsd             # Request registro eventos
❌ resRecepEvento_v150.xsd            # Response registro eventos
❌ Evento_v150.xsd                    # Estructura eventos
```

### **🔵 BAJO (Prioridad 4 - CONTENEDORES AUXILIARES)**

#### **9. Contenedores**
```
❌ ContenedorDE_v150.xsd              # Contenedor documentos
❌ ContenedorEvento_v150.xsd          # Contenedor eventos
❌ ContenedorRUC_v150.xsd             # Contenedor RUC
```

---

## 🔧 **Plan de Implementación Schemas**

### **FASE 1: Esquemas Críticos (Días 1-3)**
**🚨 SIN ESTOS NO FUNCIONA NADA**

#### **Día 1: Web Services Básicos**
```bash
# 1. Envío individual (CRÍTICO)
✅ siRecepDE_v150.xsd                 # Para enviar documentos a SIFEN
✅ resRecepDE_v150.xsd                # Para recibir respuestas SIFEN

# 2. Protocolo procesamiento
✅ ProtProcesDE_v150.xsd              # Para estado del procesamiento
```

#### **Día 2: Firma Digital (CRÍTICO)**
```bash
# 3. Firma digital (OBLIGATORIO por ley)
✅ xmldsig-core-schema-v150.xsd       # Estándar W3C para firma XML
```

#### **Día 3: Validación Integración**
```bash
# Validar que esquemas funcionen en conjunto
pytest backend/app/services/xml_generator/tests/test_schema_integration.py
```

### **FASE 2: Funcionalidad Lotes (Días 4-6)**
**🟡 MEJORA PERFORMANCE Y USABILIDAD**

#### **Día 4-5: Envío por Lotes**
```bash
❌ SiRecepLoteDE_v150.xsd             # Enviar hasta 50 documentos juntos
❌ resRecepLoteDE_v150.xsd            # Respuesta lotes
❌ ProtProcesLoteDE_v150.xsd          # Estado procesamiento lotes
```

#### **Día 6: Consulta Lotes**
```bash
❌ SiResultLoteDE_v150.xsd            # Consultar resultado de lote
❌ resResultLoteDE_v150.xsd           # Respuesta consulta lote
```

### **FASE 3: Consultas y Eventos (Días 7-8)**
**🟢 FUNCIONALIDAD COMPLETA**

#### **Día 7: Consultas**
```bash
❌ siConsDE_v150.xsd                  # Consultar documentos por CDC
❌ resConsDE_v150.xsd                 # Respuesta consulta documento
❌ siConsRUC_v150.xsd                 # Consultar datos RUC
❌ resConsRUC_v150.xsd                # Respuesta consulta RUC
```

#### **Día 8: Eventos**
```bash
❌ siRecepEvento_v150.xsd             # Registrar eventos del emisor
❌ resRecepEvento_v150.xsd            # Respuesta registro eventos
❌ Evento_v150.xsd                    # Estructura eventos (cancelación, etc.)
```

---

## 📂 **Estructura Final Esperada**

```
backend/app/services/xml_generator/schemas/
├── 📋 README.md                              # Este archivo
├── 🔗 catalog.xml                           # Catálogo resolución referencias
│
├── 📄 Core Documents/
│   └── ✅ DE_v150.xsd                       # Documentos electrónicos (IMPLEMENTADO)
│
├── 📡 Web Services - Individual/
│   ├── ✅ siRecepDE_v150.xsd                # Request envío individual
│   ├── ✅ resRecepDE_v150.xsd               # Response envío individual
│   └── ✅ ProtProcesDE_v150.xsd             # Protocolo procesamiento
│
├── 📦 Web Services - Batch/
│   ├── ❌ SiRecepLoteDE_v150.xsd            # Request envío lote
│   ├── ❌ resRecepLoteDE_v150.xsd           # Response envío lote
│   ├── ❌ ProtProcesLoteDE_v150.xsd         # Protocolo procesamiento lote
│   ├── ❌ SiResultLoteDE_v150.xsd           # Request consulta resultado
│   └── ❌ resResultLoteDE_v150.xsd          # Response consulta resultado
│
├── 🔍 Web Services - Query/
│   ├── ❌ siConsDE_v150.xsd                 # Request consulta documento
│   ├── ❌ resConsDE_v150.xsd                # Response consulta documento
│   ├── ❌ siConsRUC_v150.xsd                # Request consulta RUC
│   └── ❌ resConsRUC_v150.xsd               # Response consulta RUC
│
├── 📋 Events/
│   ├── ❌ siRecepEvento_v150.xsd            # Request registro eventos
│   ├── ❌ resRecepEvento_v150.xsd           # Response registro eventos
│   └── ❌ Evento_v150.xsd                   # Estructura eventos
│
├── 🔐 Security/
│   └── ✅ xmldsig-core-schema-v150.xsd      # Firma digital W3C
│
├── 📦 Containers/
│   ├── ❌ ContenedorDE_v150.xsd             # Contenedor documentos
│   ├── ❌ ContenedorEvento_v150.xsd         # Contenedor eventos
│   └── ❌ ContenedorRUC_v150.xsd            # Contenedor RUC
│
└── 🧪 Testing/
    ├── 📄 minimal_schemas/                   # Esquemas mínimos para tests
    │   ├── test_DE_minimal.xsd              # Solo elementos básicos
    │   └── test_response_minimal.xsd        # Respuestas simplificadas
    └── 📄 validation_samples/
        ├── valid_request_samples.xml        # XMLs válidos de ejemplo
        ├── valid_response_samples.xml       # Respuestas válidas
        └── invalid_samples.xml              # XMLs inválidos para test
```

---

## 🌐 **Fuentes Oficiales**

### **Esquemas Oficiales SIFEN**
```bash
# URLs oficiales para descargar esquemas
https://sifen.set.gov.py/schemas/v150/DE_v150.xsd
https://sifen.set.gov.py/schemas/v150/siRecepDE_v150.xsd
https://sifen.set.gov.py/schemas/v150/resRecepDE_v150.xsd
# [etc. para todos los esquemas]

# Portal público
https://ekuatia.set.gov.py/sifen/xsd/
```

### **Documentación de Referencia**
- 📖 **Manual Técnico SIFEN v150** - Especificación completa
- 📖 **Guía Web Services SIFEN** - Endpoints y formatos
- 📖 **W3C XML Digital Signature** - Estándar firma digital
- 📖 **Manual de Desarrolladores SET** - Implementación práctica

---

## 🧪 **Testing con Esquemas**

### **Tests por Categoría de Schema**
```python
# tests/test_schemas/
├── test_core_schemas.py              # DE_v150.xsd
├── test_webservice_schemas.py        # siRecepDE, resRecepDE
├── test_batch_schemas.py             # Esquemas lotes
├── test_query_schemas.py             # Consultas
├── test_event_schemas.py             # Eventos
└── test_signature_schemas.py         # Firma digital
```

### **Ejemplo Test Schema**
```python
def test_sirecepde_schema_validation():
    """Test validación esquema siRecepDE_v150.xsd"""
    schema_path = SCHEMAS_DIR / "siRecepDE_v150.xsd"
    sample_xml = create_sirecepde_sample()
    
    validator = XMLValidator(schema_path)
    is_valid, errors = validator.validate_xml(sample_xml)
    
    assert is_valid, f"Schema siRecepDE inválido: {errors}"
    assert contains_required_elements(sample_xml)
```

### **Validación Cruzada Esquemas**
```python
def test_schemas_integration():
    """Test que todos los schemas funcionen en conjunto"""
    # 1. Generar documento con DE_v150.xsd
    document_xml = generate_factura_xml()
    
    # 2. Crear request con siRecepDE_v150.xsd
    request_xml = create_sirecepde_request(document_xml)
    
    # 3. Validar ambos schemas funcionan juntos
    assert validate_document_schema(document_xml)
    assert validate_request_schema(request_xml)
```

---

## 🔧 **Configuración Validador**

### **XMLValidator Actualizado**
```python
class XMLValidator:
    def __init__(self, schema_type='DE'):
        """
        Validador multieschema para SIFEN
        
        Args:
            schema_type: 'DE', 'siRecep', 'resRecep', 'signature', etc.
        """
        self.schema_mappings = {
            'DE': 'DE_v150.xsd',
            'siRecep': 'siRecepDE_v150.xsd', 
            'resRecep': 'resRecepDE_v150.xsd',
            'signature': 'xmldsig-core-schema-v150.xsd',
            'batch_request': 'SiRecepLoteDE_v150.xsd',
            'batch_response': 'resRecepLoteDE_v150.xsd',
            'query_doc': 'siConsDE_v150.xsd',
            'query_ruc': 'siConsRUC_v150.xsd',
            'event': 'siRecepEvento_v150.xsd'
        }
        self.load_schema(schema_type)
    
    def validate_workflow(self, document_xml, request_xml):
        """Validar flujo completo documento + request"""
        # 1. Validar documento
        doc_valid, doc_errors = self.validate_xml(document_xml, 'DE')
        
        # 2. Validar request
        req_valid, req_errors = self.validate_xml(request_xml, 'siRecep')
        
        return (doc_valid and req_valid), (doc_errors + req_errors)
```

---

## 📊 **Métricas de Completitud**

### **Checklist Implementación Schemas**
- [ ] **🔴 DE_v150.xsd** - ✅ IMPLEMENTADO Y CORREGIDO
- [ ] **🔴 siRecepDE_v150.xsd** - ❌ CRÍTICO FALTANTE
- [ ] **🔴 resRecepDE_v150.xsd** - ❌ CRÍTICO FALTANTE  
- [ ] **🔴 xmldsig-core-schema-v150.xsd** - ❌ CRÍTICO FALTANTE
- [ ] **🔴 ProtProcesDE_v150.xsd** - ❌ CRÍTICO FALTANTE
- [ ] **🟡 SiRecepLoteDE_v150.xsd** - ❌ ALTO IMPACTO FALTANTE
- [ ] **🟡 resRecepLoteDE_v150.xsd** - ❌ ALTO IMPACTO FALTANTE
- [ ] **🟢 siConsDE_v150.xsd** - ❌ MEDIO IMPACTO FALTANTE
- [ ] **🟢 Evento_v150.xsd** - ❌ MEDIO IMPACTO FALTANTE

### **Estados de Implementación**
```
✅ IMPLEMENTADO (1/17):    5.9%  - Solo DE_v150.xsd
🔴 CRÍTICO FALTANTE:      23.5%  - 4 esquemas bloqueantes
🟡 ALTO FALTANTE:         29.4%  - 5 esquemas importantes  
🟢 MEDIO FALTANTE:        41.2%  - 7 esquemas opcionales
```

### **Impacto en Funcionalidad**
```
SIN Esquemas Críticos:
❌ No se puede enviar NINGÚN documento a SIFEN
❌ No se puede firmar digitalmente (ilegal)
❌ No se puede procesar respuestas SIFEN
❌ SISTEMA COMPLETAMENTE NO FUNCIONAL

CON Esquemas Críticos:
✅ Envío individual documentos
✅ Firma digital válida
✅ Procesamiento respuestas básico
❌ Sin envío lotes (performance limitada)
❌ Sin consultas (funcionalidad limitada)
```

---

## 🚨 **Acción Inmediata Requerida**

### **PASO 1: Obtener Esquemas Oficiales**
```bash
# Descargar desde fuentes oficiales SET
wget https://sifen.set.gov.py/schemas/v150/siRecepDE_v150.xsd
wget https://sifen.set.gov.py/schemas/v150/resRecepDE_v150.xsd
wget https://sifen.set.gov.py/schemas/v150/xmldsig-core-schema-v150.xsd
wget https://sifen.set.gov.py/schemas/v150/ProtProcesDE_v150.xsd

# O solicitar a SET Paraguay si URLs no están disponibles
```

### **PASO 2: Validar Esquemas**
```bash
# Validar que esquemas funcionen con DE_v150.xsd corregido
pytest backend/app/services/xml_generator/tests/test_schema_integration.py -v
```

### **PASO 3: Actualizar XMLValidator**
```bash
# Modificar validador para soportar múltiples esquemas
# Implementar validación cruzada DE + siRecep + signature
```

---

## 📞 **Escalación y Soporte**

### **Para Problemas Críticos de Esquemas:**
- 🔴 **Esquemas no validando**: Escalación inmediata a arquitecto
- 🔴 **Incompatibilidad esquemas**: Consultar con SET Paraguay
- 🟡 **Performance validación**: Optimización en siguiente sprint
- 🟢 **Esquemas opcionales**: Implementar según demanda

### **Recursos Externos:**
- 📧 **Soporte SET**: soporte.ekuatia@set.gov.py
- 🌐 **Portal Desarrolladores**: https://ekuatia.set.gov.py/dev
- 📖 **Documentación Oficial**: Manual Técnico SIFEN v150
- 🧪 **Ambiente Pruebas**: https://sifen-test.set.gov.py

---

## 🎯 **Objetivo Final**

**META**: Todos los esquemas XSD oficiales implementados y funcionando correctamente para validación completa antes del envío a SIFEN, cumpliendo 100% con las especificaciones del Manual Técnico SIFEN v150.

**CHECKPOINT CRÍTICO**: No continuar con templates hasta que al menos los 4 esquemas críticos estén implementados y funcionando.



