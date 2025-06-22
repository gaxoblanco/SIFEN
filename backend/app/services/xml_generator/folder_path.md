# Plan de Reorganización de Tests para Schemas Modulares

## 🎯 Estructura de Testing Reorganizada

### **📁 Nueva Organización de Carpetas**

```
backend/app/services/xml_generator/
├── tests/                           # 🧪 Tests del generador XML (mantener)
│   ├── test_generator.py            # ✅ Tests de generación XML
│   ├── test_validator.py            # ✅ Tests del validador principal
│   ├── test_document_types.py       # ✅ Tests tipos de documentos
│   ├── test_performance.py          # ✅ Tests de rendimiento
│   ├── test_integration.py          # 🆕 Tests de integración completa
│   ├── fixtures/                    # ✅ Datos de prueba comunes
│   │   ├── factura_simple.py
│   │   ├── autofactura_sample.py
│   │   ├── nota_credito_sample.py
│   │   └── test_data.py
│   └── mocks/                       # ✅ Mocks para dependencias
│       ├── mock_sifen_client.py
│       └── mock_validators.py
└── schemas/
    └── v150/                        # 🆕 Schemas modulares organizados
│   │   └──/tests/
│   │   │   ├── utils/                     # 🟢 MANTENER TODO - ya implementado
│   │   │   │   ├── schema_validator.py
│   │   │   │   ├── xml_generator/         # API facade completa
│   │   │   │   └── test_helpers/          # Helpers especializados
│   │   │   │
│   │   │   ├── conftest.py                 # Configuración compartida (si tiene ✅ usa conftest)
│   │   │   ├── test_schemas_basic.py       # ✅ Tipos básicos
│   │   │   ├── test_schemas_contact.py     # 🟢 Tipos de contacto  
│   │   │   ├── test_schemas_geographic.py  # 🟢 Tipos geográficos
│   │   │   ├── test_schemas_core.py        # 🟢 Schema principal
│   │   │   ├── test_schemas_business.py    # Lógica de negocio
│   │   │   └── test_schemas_currency.py    # Tipos monetarios
│   │   │
        ├── DE_v150.xsd                # 🟢 Schema principal
        ├── common/                    # 🟢 Tipos básicos
        ├── document_core/             # 🟢 Estructura núcleo
        ├── parties/                   # Emisores y receptores
        ├── document_types/            # Tipos específicos
        ├── operations/                # Operaciones y pagos
        ├── transport/                 # Transporte
        └── extensions/                # Extensiones sectoriales
```

## 🧪 Tipos de Tests Necesarios

### **1. Tests de Módulos de Schema (Nuevos)**

```python
# shared/schemas/v150/tests/test_basic_types.py
import pytest
from lxml import etree

class TestBasicTypes:
    """Tests para tipos básicos reutilizables"""
    
    def test_version_format_valid(self):
        """Test validación de versión del formato"""
        schema = etree.XMLSchema(file="common/basic_types.xsd")
        # Test con valor válido "150"
        xml = "<dVerFor>150</dVerFor>"
        assert schema.validate(etree.fromstring(xml))
        
    def test_version_format_invalid(self):
        """Test validación con versión inválida"""
        schema = etree.XMLSchema(file="common/basic_types.xsd")
        # Test con valor inválido
        xml = "<dVerFor>140</dVerFor>"
        assert not schema.validate(etree.fromstring(xml))
    
    def test_ruc_number_valid(self):
        """Test validación de número RUC válido"""
        schema = etree.XMLSchema(file="common/basic_types.xsd")
        xml = "<dRUCEmi>12345678</dRUCEmi>"
        assert schema.validate(etree.fromstring(xml))
        
    def test_codigo_seguridad_format(self):
        """Test formato código de seguridad"""
        schema = etree.XMLSchema(file="common/basic_types.xsd")
        xml = "<dCodSeg>123456789</dCodSeg>"
        assert schema.validate(etree.fromstring(xml))
```

### **2. Tests de Integración de Schemas**

```python
# shared/schemas/v150/tests/test_schema_integration.py
import pytest
from lxml import etree

class TestSchemaIntegration:
    """Tests de integración entre módulos de schema"""
    
    def test_main_schema_loads_all_modules(self):
        """Test que el schema principal carga todos los módulos"""
        schema = etree.XMLSchema(file="DE_v150.xsd")
        assert schema is not None
        
    def test_complete_document_validation(self):
        """Test validación de documento completo"""
        schema = etree.XMLSchema(file="DE_v150.xsd")
        with open("fixtures/xml_samples/factura_valida.xml") as f:
            xml_doc = etree.parse(f)
        assert schema.validate(xml_doc)
        
    def test_cross_module_type_resolution(self):
        """Test resolución de tipos entre módulos"""
        # Verificar que tipos de basic_types se usan en issuer_types
        schema = etree.XMLSchema(file="DE_v150.xsd")
        # Test específico de resolución de tipos
        xml = """
        <rDE version="1.5.0">
            <dVerFor>150</dVerFor>
            <DE Id="01234567890123456789012345678901234567890123">
                <!-- Documento con tipos de múltiples módulos -->
            </DE>
        </rDE>
        """
        assert schema.validate(etree.fromstring(xml))
```

### **3. Tests de Generador XML (Mejorados)**

```python
# backend/app/services/xml_generator/tests/test_generator.py
import pytest
from ..generator import XMLGenerator
from ..validators import XMLValidator
from ...schemas.v150.tests.utils.schema_validator import SchemaValidator

class TestXMLGenerator:
    """Tests del generador XML con validación de schema modular"""
    
    def test_generate_with_modular_schema_validation(self, factura_simple):
        """Test generación y validación con schema modular"""
        generator = XMLGenerator()
        xml = generator.generate_simple_invoice_xml(factura_simple)
        
        # Validar con schema modular
        schema_validator = SchemaValidator("shared/schemas/v150/DE_v150.xsd")
        is_valid, errors = schema_validator.validate_xml(xml)
        
        assert is_valid, f"XML inválido con schema modular: {errors}"
        
    def test_generate_different_document_types(self):
        """Test generación de diferentes tipos de documentos"""
        generator = XMLGenerator()
        
        # Test factura
        factura_xml = generator.generate_invoice_xml(factura_data)
        assert self._validate_against_module(factura_xml, "document_types/invoice_types.xsd")
        
        # Test autofactura  
        autofactura_xml = generator.generate_autoinvoice_xml(autofactura_data)
        assert self._validate_against_module(autofactura_xml, "document_types/autoinvoice_types.xsd")
        
    def _validate_against_module(self, xml, module_path):
        """Helper para validar contra módulo específico"""
        validator = SchemaValidator(f"shared/schemas/v150/{module_path}")
        is_valid, _ = validator.validate_xml(xml)
        return is_valid
```

### **4. Tests de Performance (Modulares)**

```python
# backend/app/services/xml_generator/tests/test_performance.py
import pytest
import time
from ..generator import XMLGenerator
from ...schemas.v150.tests.utils.schema_validator import SchemaValidator

class TestPerformanceModular:
    """Tests de performance con schemas modulares"""
    
    def test_modular_schema_loading_performance(self):
        """Test tiempo de carga de schema modular vs monolítico"""
        # Test schema modular
        start_time = time.time()
        modular_validator = SchemaValidator("shared/schemas/v150/DE_v150.xsd")
        modular_load_time = time.time() - start_time
        
        # Debe cargar en menos de 500ms
        assert modular_load_time < 0.5, f"Schema modular muy lento: {modular_load_time:.2f}s"
        
    def test_validation_performance_parity(self, factura_simple):
        """Test que validación modular no sea más lenta"""
        generator = XMLGenerator()
        xml = generator.generate_simple_invoice_xml(factura_simple)
        
        # Validar performance
        start_time = time.time()
        validator = SchemaValidator("shared/schemas/v150/DE_v150.xsd")
        is_valid, errors = validator.validate_xml(xml)
        validation_time = time.time() - start_time
        
        assert validation_time < 3.0, f"Validación muy lenta: {validation_time:.2f}s"
        assert is_valid, f"XML inválido: {errors}"
```

### **Tests por Módulo**
```bash
# Tests de tipos básicos
pytest shared/schemas/v150/tests/test_basic_types.py -v

# Tests de métodos de pago
pytest shared/schemas/v150/tests/test_payment_methods.py -v

# Tests de integración de schemas
pytest shared/schemas/v150/tests/test_schema_integration.py -v
```

### **Tests del Generador XML**
```bash
# Tests completos del generador
pytest backend/app/services/xml_generator/tests/ -v

# Tests específicos con schema modular
pytest backend/app/services/xml_generator/tests/test_generator.py::TestXMLGenerator::test_generate_with_modular_schema_validation -v

# Tests de performance
pytest backend/app/services/xml_generator/tests/test_performance.py -v
```

### **Tests Completos**
```bash
# Todos los tests de XML y schemas
pytest backend/app/services/xml_generator/tests/ shared/schemas/v150/tests/ -v

# Tests con cobertura
pytest --cov=backend/app/services/xml_generator --cov=shared/schemas/v150 --cov-report=html

# Tests de regresión rápidos
pytest -m "not slow" backend/app/services/xml_generator/tests/ shared/schemas/v150/tests/
```

## 📊 Métricas de Calidad

### **Cobertura Objetivo**
- **Módulos de schema**: 95% cobertura
- **Generador XML**: 90% cobertura  
- **Validadores**: 95% cobertura
- **Tests de integración**: 100% casos críticos

### **Performance Objetivo**
- **Carga de schema**: < 500ms
- **Validación por documento**: < 100ms
- **Tests unitarios**: < 50ms cada uno
- **Tests de integración**: < 5s cada uno

## 🔧 Utilidades de Testing Necesarias

### **SchemaValidator**
```python
# shared/schemas/v150/tests/utils/schema_validator.py
from lxml import etree
from typing import Tuple, List

class SchemaValidator:
    """Validador específico para tests de schemas modulares"""
    
    def __init__(self, schema_path: str):
        self.schema = etree.XMLSchema(file=schema_path)
    
    def validate_xml(self, xml_content: str) -> Tuple[bool, List[str]]:
        """Valida XML y retorna errores detallados"""
        try:
            doc = etree.fromstring(xml_content)
            is_valid = self.schema.validate(doc)
            errors = [str(error) for error in self.schema.error_log]
            return is_valid, errors
        except Exception as e:
            return False, [str(e)]
    
    def validate_module(self, xml_fragment: str, root_element: str) -> bool:
        """Valida fragmento XML contra módulo específico"""
        wrapped_xml = f"<{root_element}>{xml_fragment}</{root_element}>"
        is_valid, _ = self.validate_xml(wrapped_xml)
        return is_valid
```

### **XMLSampleGenerator**
```python
# shared/schemas/v150/tests/utils/xml_generator.py
class XMLSampleGenerator:
    """Generador de XMLs de muestra para testing"""
    
    def generate_minimal_invoice(self) -> str:
        """Genera factura mínima válida"""
        # Implementación
        
    def generate_complete_invoice(self) -> str:
        """Genera factura completa con todos los campos"""
        # Implementación
        
    def generate_invalid_sample(self, error_type: str) -> str:
        """Genera XML inválido para tests negativos"""
        # Implementación
```