# 🧪 PROMPT PARA GENERAR TESTS XML_GENERATOR

## CONTEXTO
Sistema SIFEN v150 con módulo `xml_generator` ya funcionando. Necesito generar archivo de test faltante que siga las mismas convenciones de los tests existentes.

## TAREA
**Genera el archivo: `[NOMBRE_ARCHIVO_TEST]`**

## ESTRUCTURA EXISTENTE

### Tests Implementados
```
backend/app/services/xml_generator/tests/
├── ✅ test_generator.py           # Tests generación XML
├── ✅ test_validator.py           # Tests validación XML  
├── ✅ test_validations.py         # Tests validaciones específicas
├── ✅ test_document_types.py      # Tests tipos de documento
├── ✅ test_edge_cases.py          # Tests casos límite
├── ✅ test_performance.py         # Tests rendimiento
├── ✅ test_format_validations.py  # Tests validaciones formato
└── ❌ [ARCHIVO_FALTANTE]          # ← GENERAR ESTE
```

### Imports Estándar
```python
"""
[DESCRIPCIÓN DEL ARCHIVO]
"""
import pytest
from decimal import Decimal
from datetime import datetime
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator
```

### Fixtures Disponibles
```python
# Usar estas fixtures que ya existen
@pytest.fixture
def validator():
    return XMLValidator()

@pytest.fixture  
def xml_generator():
    return XMLGenerator()

# Función para crear datos de prueba
create_factura_base()  # Factura con datos válidos por defecto
```

## PATRONES DE TESTING

### Estructura de Test
```python
def test_[descripcion_funcionalidad]():
    """Test para [descripción específica]"""
    # 1. Arrange - Preparar datos
    factura = create_factura_base()
    # Modificar datos específicos del test
    
    # 2. Act - Ejecutar función  
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)
    
    # 3. Assert - Verificar resultados
    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)
    
    assert is_valid, f"XML inválido: {errors}"
    assert "[contenido_esperado]" in xml
```

### Tipos de Assertions
```python
# Validación XML
assert is_valid, f"XML inválido: {errors}"

# Contenido XML específico
assert "<elemento>valor</elemento>" in xml

# Valores numéricos 
assert tiempo_generacion < 1.0, f"Muy lento: {tiempo_generacion}s"

# Estructura de datos
assert len(items) == 5, "Debe tener 5 items"
```

## ESPECIFICACIONES SIFEN v150

### Tipos de Documento
- **1**: Factura Electrónica (FE)
- **4**: Autofactura Electrónica (AFE)  
- **5**: Nota de Crédito Electrónica (NCE)
- **6**: Nota de Débito Electrónica (NDE)
- **7**: Nota de Remisión Electrónica (NRE)

### Elementos XML Importantes
```xml
<iTipDE>1</iTipDE>                    <!-- Tipo documento -->
<dNumID>001-001-0000001</dNumID>      <!-- Número documento -->
<dFeEmiDE>2024-01-01T12:00:00</dFeEmiDE> <!-- Fecha emisión -->
<dTotGralOpe>110000</dTotGralOpe>     <!-- Total general -->
<dTotIVA>10000</dTotIVA>              <!-- Total IVA -->
```

### Validaciones Clave
- **Namespace**: `http://ekuatia.set.gov.py/sifen/xsd`
- **Encoding**: UTF-8
- **Versión**: 1.5.0
- **Formato números**: Sin separadores de miles
- **Formato fechas**: ISO 8601

## EJEMPLOS DE TESTS POR CATEGORÍA

### Tests de Funcionalidad
```python
def test_funcionalidad_especifica():
    """Test funcionalidad específica del módulo"""
    factura = create_factura_base()
    # Configurar caso específico
    
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)
    
    assert "[resultado_esperado]" in xml
```

### Tests de Validación
```python
def test_validacion_especifica():
    """Test validación específica"""
    factura = create_factura_base()
    # Datos que causan error específico
    
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)
    
    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)
    
    assert is_valid, f"Debe ser válido: {errors}"
```

### Tests de Error
```python  
def test_manejo_error():
    """Test manejo de errores específicos"""
    with pytest.raises(SifenValidationError) as exc_info:
        # Acción que debe fallar
        pass
    
    assert "mensaje_error_esperado" in str(exc_info.value)
```

## CONVENCIONES DEL PROYECTO

### Nombres de Tests
- **Prefijo**: Siempre `test_`
- **Descriptivo**: `test_validacion_ruc_paraguayo`
- **Específico**: `test_formato_fecha_iso_8601`

### Docstrings
- **Formato**: `"""Test para [descripción específica]"""`
- **Específico**: Describir qué se está probando exactamente

### Datos de Prueba
- **Usar**: `create_factura_base()` como punto de partida
- **Modificar**: Solo los campos necesarios para el test
- **Limpios**: Datos representativos y válidos

## REQUERIMIENTOS

1. **Seguir patrones existentes** de otros archivos test
2. **Usar imports estándar** del módulo  
3. **Documentar cada test** con docstring descriptivo
4. **Assertions específicas** y mensajes de error claros
5. **Datos de prueba realistas** usando `create_factura_base()`

**Genera un archivo de test completo y funcional siguiendo estas especificaciones.**