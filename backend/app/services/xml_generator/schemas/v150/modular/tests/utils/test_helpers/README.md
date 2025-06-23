# Test Helpers - SIFEN v150

Módulo de utilidades para testing de schemas SIFEN modulares y validación XML.

## 📁 Estructura

```
test_helpers/
├── __init__.py              # 🔌 API principal (facade)
├── xml_helpers.py           # ✅ Utilidades XML básicas
├── data_factory.py          # ✅ Generador de datos SIFEN
├── schema_helpers.py        # ✅ Helpers específicos de schemas
├── performance_helpers.py   # 🚧 Medición de performance (pendiente)
├── assertion_helpers.py     # 🚧 Assertions customizadas (pendiente)
├── constants.py             # ✅ Constantes compartidas
└── README.md               # 📚 Esta documentación
```

## 🎯 Funcionalidades Implementadas

### ✅ `xml_helpers.py`
- Parsing seguro de XML con manejo de errores
- Extracción de elementos usando XPath
- Comparación de estructuras XML
- Formateo para debugging
- Validación básica contra schemas

### ✅ `schema_helpers.py`
- Validación contra módulos específicos de schema
- Verificación de estructura básica SIFEN
- Testing de dependencias entre módulos
- Validación de campos específicos SIFEN
- Integración de validación modular

### ✅ `data_factory.py`
- Generación de datos de testing SIFEN
- Fábrica de documentos electrónicos
- Datos de empresas, clientes y productos
- Escenarios de testing predefinidos

### ✅ `constants.py`
- Namespace y versiones SIFEN
- Tipos de documentos electrónicos
- Patrones de validación de campos
- Códigos de respuesta y error
- Configuración por entorno

## 🚧 Pendientes de Implementación

### `performance_helpers.py`
- Medición de tiempos de validación
- Benchmarking de operaciones XML
- Monitoring de memoria y recursos
- Reportes de performance

### `assertion_helpers.py`
- Assertions específicas para SIFEN
- Validaciones customizadas de documentos
- Helpers para comparaciones XML
- Assertions de estructura modular

## 🚀 Uso Rápido

```python
# Importar API principal
from .test_helpers import XMLTestHelpers, SchemaTestHelpers

# Validar XML básico
success, tree, errors = XMLTestHelpers.parse_xml_safely(xml_content)

# Validar contra schema SIFEN
helper = SchemaTestHelpers()
result = helper.validate_sifen_basic_structure(xml_content)

# Generar datos de testing
from .test_helpers import SampleDataAPI
data = SampleDataAPI.generate_factura_sample()
```

## 📋 Próximos Pasos

1. **Completar `performance_helpers.py`** - Medición y benchmarking
2. **Completar `assertion_helpers.py`** - Assertions customizadas
3. **Tests unitarios** para todos los módulos
4. **Integración** con sistema de testing existente
5. **Documentación** de casos de uso específicos

---

**Estado**: 4/6 módulos completados | **Versión**: 1.0.0 | **SIFEN**: v150