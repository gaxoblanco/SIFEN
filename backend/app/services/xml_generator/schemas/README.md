# 📋 Schemas SIFEN v150 - Arquitectura Modular

**Ubicación**: `backend/app/services/xml_generator/schemas/v150/`  
**Propósito**: Validación de documentos electrónicos SIFEN Paraguay  
**Versión**: 1.5.0 | **Namespace**: `http://ekuatia.set.gov.py/sifen/xsd`

---

## 🏗️ **Arquitectura del Sistema**

### **📁 Estructura Actual**
```
schemas/v150/
├── DE_v150.xsd                    # ✅ Schema principal (orquestador)
├── modular/                       # ✅ Arquitectura modular implementada
│   ├── common/                    # ✅ Tipos básicos reutilizables
│   ├── document_core/             # ✅ Estructura núcleo del documento
│   ├── parties/                   # ✅ Emisores y receptores
│   ├── operations/                # ✅ Items, pagos, operaciones
│   ├── transport/                 # ✅ Transporte y logística
│   ├── extensions/                # ✅ Extensiones sectoriales
│   └── tests/                     # ✅ Tests modulares completos
├── official_set/                  # ❌ Schemas oficiales SET (pendientes)
│   ├── webservices/               # ❌ Web services SIFEN
│   │   ├── individual/            # ❌ siRecepDE, resRecepDE, ProtProcesDE
│   │   ├── batch/                 # ❌ SiRecepLoteDE, resRecepLoteDE
│   │   ├── queries/               # ❌ siConsDE, siConsRUC
│   │   └── events/                # ❌ siRecepEvento, Evento
│   └── security/                  # ❌ xmldsig-core-schema
├── integration/                   # ❌ Puente modular ↔ oficial (pendiente)
└── unified_tests/                 # ❌ Tests E2E completos (pendiente)
```

### **🎯 Filosofía Arquitectural**
- **Modular**: Cada módulo tiene responsabilidad específica
- **Reutilizable**: Tipos básicos compartidos entre módulos  
- **Escalable**: Fácil agregar nuevos tipos de documentos
- **Testeable**: Tests independientes por módulo

---

## 📊 **Estado de Implementación**

### **✅ IMPLEMENTADO (Arquitectura Modular)**
| Módulo | Estado | Cobertura | Descripción |
|--------|--------|-----------|-------------|
| **DE_v150.xsd** | ✅ | 100% | Schema principal integrador |
| **modular/common/** | ✅ | 100% | Tipos básicos, geográficos, monetarios |
| **modular/document_core/** | ✅ | 100% | Operación, timbrado, totales |
| **modular/parties/** | ✅ | 100% | Emisores y receptores |
| **modular/operations/** | ✅ | 90% | Items completado, pagos en desarrollo |
| **modular/transport/** | ✅ | 95% | Vehículos y condiciones implementados |
| **modular/extensions/** | ✅ | 80% | Supermercados completo, otros preparatorios |
| **modular/tests/** | ✅ | 85% | Suite completa de tests modulares |

### **❌ PENDIENTE (Integración SIFEN)**
| Carpeta | Estado | Descripción |
|---------|--------|-------------|
| **official_set/webservices/individual/** | ❌ | siRecepDE, resRecepDE, ProtProcesDE |
| **official_set/webservices/batch/** | ❌ | SiRecepLoteDE, resRecepLoteDE |
| **official_set/webservices/queries/** | ❌ | siConsDE, siConsRUC + responses |
| **official_set/webservices/events/** | ❌ | siRecepEvento, Evento + responses |
| **official_set/security/** | ❌ | xmldsig-core-schema |
| **integration/** | ❌ | Puente modular ↔ oficial |
| **unified_tests/** | ❌ | Tests E2E SIFEN |

---

## 🎯 **Alcance Actual**

### **✅ LO QUE SÍ FUNCIONA**
- ✅ **Generación XML** documentos electrónicos válidos
- ✅ **Validación local** contra DE_v150.xsd modular
- ✅ **Testing robusto** de todos los módulos implementados
- ✅ **Extensibilidad** para nuevos tipos de documentos
- ✅ **Arquitectura preparada** para crecimiento

### **❌ LO QUE NO FUNCIONA (Aún)**
- ❌ **Envío a SIFEN** (faltan schemas web services)
- ❌ **Firma digital** (falta xmldsig-core-schema.xsd)
- ❌ **Procesamiento respuestas SET** (faltan schemas response)
- ❌ **Envío por lotes** (faltan schemas batch)
- ❌ **Consultas CDC/RUC** (faltan schemas query)

---

## 🚀 **Próximos Pasos**

### **Fase 1: Integración SIFEN (Crítica)**
1. **Crear estructura oficial_set/** y subcarpetas webservices/
2. **Obtener 16 schemas oficiales** desde `https://ekuatia.set.gov.py/sifen/xsd/`
3. **Organizar por categorías** en individual/, batch/, queries/, events/, security/
4. **Implementar integration/** para mapeo modular ↔ oficial
5. **Tests E2E** en unified_tests/ con SIFEN real

### **Fase 2: Producción Ready**
1. **Validación cruzada** modular + oficial
2. **Performance optimization** 
3. **Error handling** robusto
4. **Documentación completa**

---

## 🧪 **Testing**

### **Comandos Útiles**
```bash
# Tests modulares (arquitectura actual)
pytest schemas/v150/modular/tests/ -v

# Tests específicos por módulo
pytest schemas/v150/modular/tests/test_schemas_basic.py
pytest schemas/v150/modular/tests/test_schemas_core.py

# Coverage modular completo
pytest --cov=schemas/v150/modular --cov-report=html

# Una vez implementado: Tests integración SIFEN
# pytest schemas/v150/unified_tests/ -v
```

### **Cobertura Actual: 85%**
- ✅ Tipos básicos: 100%
- ✅ Schema principal: 100% 
- ✅ Módulos core: 95%
- 🔄 Integración SIFEN: 0% (pendiente)

---

## 📚 **Referencias**

- 📖 **Manual Técnico SIFEN v150** - Especificación oficial
- 🌐 **Portal SET**: https://ekuatia.set.gov.py/
- 🔗 **Schemas Oficiales**: https://ekuatia.set.gov.py/sifen/xsd/
- 📧 **Soporte**: soporte.ekuatia@set.gov.py

---

## ⚡ **Quick Start**

```python
# Generar documento con arquitectura modular
from xml_generator import XMLGenerator

generator = XMLGenerator()
xml = generator.generate_invoice_xml(factura_data)

# Validar localmente (funciona)
validator = XMLValidator("DE_v150.xsd")
is_valid = validator.validate(xml)  # ✅ OK

# Enviar a SIFEN (pendiente schemas oficiales)
# sifen_client.send(xml)  # ❌ Requiere schemas web services
```

**🎯 Sistema listo para desarrollo, pendiente integración SIFEN productiva.**