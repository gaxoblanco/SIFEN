# Validadores SIFEN v150

Sistema modular de validación para documentos electrónicos SIFEN v150 de Paraguay.

## 🚀 Uso Rápido

```python
from validators import validate_xml

# Validación completa
is_valid, errors = validate_xml(xml_content)
if not is_valid:
    for error in errors:
        print(f"❌ {error}")
```

## 📋 API Principal

### Validación Completa
```python
from validators import validate_xml, SifenValidator

# Función simple
is_valid, errors = validate_xml(xml_content)

# Clase con configuración
validator = SifenValidator()
is_valid, errors = validator.validate_xml(xml_content)
```

### Validaciones Específicas
```python
from validators import validate_xml_structure, validate_sifen_format

# Solo estructura básica (rápido)
struct_ok, struct_errors = validate_xml_structure(xml_content)

# Solo formatos SIFEN (RUC, CDC, fechas)
format_ok, format_errors = validate_sifen_format(xml_content)
```

### Validación Rápida
```python
from validators import quick_validate

# Solo resultado booleano
if quick_validate(xml_content):
    print("✅ XML válido")
```

## 🔧 Validaciones Granulares

### Campos Específicos
```python
from validators import quick_validate_ruc, quick_validate_cdc, quick_validate_date

# Validar RUC
valid_ruc = quick_validate_ruc("12345678")

# Validar CDC
valid_cdc = quick_validate_cdc("01234567890123456789012345678901234567890123")

# Validar fecha ISO
valid_date = quick_validate_date("2024-12-15T14:30:45")
```

### Reportes Detallados
```python
from validators import validate_with_detailed_report

report = validate_with_detailed_report(xml_content)
print(f"Válido: {report['overall_valid']}")
print(f"Errores totales: {report['total_errors']}")
print(f"Por categoría: {report['error_summary']['categories']}")
```

## 🏗️ Arquitectura Modular

### Componentes
- **`StructureValidator`** - Validación básica de estructura XML
- **`FormatValidator`** - Validación de formatos específicos SIFEN  
- **`CoreXSDValidator`** - Validación autoritativa contra XSD oficial
- **`ErrorHandler`** - Formateo y categorización de errores
- **`SifenValidator`** - Facade que combina todos los validadores

### Orden de Validación
1. **Estructura básica** (fail-fast para errores críticos)
2. **Validación XSD** (autoritativa contra esquemas oficiales)
3. **Formatos SIFEN** (validaciones específicas complementarias)

## 📊 Tipos de Validación

### Estructura Básica
- XML well-formed
- Namespace SIFEN correcto
- Elemento raíz `rDE`
- Atributos obligatorios (`version`)
- Elementos mínimos requeridos

### Formatos SIFEN
- **CDC**: 44 dígitos numéricos
- **RUC**: 8 dígitos numéricos  
- **Fechas**: ISO 8601 (YYYY-MM-DDTHH:MM:SS)
- **Códigos documento**: 01, 04, 05, 06, 07
- **Establecimiento/Expedición**: 3 dígitos
- **Monedas**: Códigos ISO (PYG, USD, EUR)

### Validación XSD
- Validación completa contra `DE_v150.xsd`
- Elementos y atributos obligatorios
- Tipos de datos y restricciones
- Cardinalidad y estructura jerárquica

## 🚨 Manejo de Errores

### Categorías de Error
- **Error de Sintaxis XML** - XML malformado
- **Error de Estructura** - Elementos/atributos faltantes
- **Error de Formato SIFEN** - Formatos incorrectos (RUC, CDC, etc.)
- **Error de Validación XSD** - Violaciones del esquema oficial
- **Error de Regla de Negocio** - Reglas específicas SIFEN

### Ejemplo de Errores
```python
is_valid, errors = validate_xml(xml_content)
# errors = [
#     "[Error de Formato SIFEN] RUC inválido en dRUCEmi: '1234567'. Debe tener 8 dígitos",
#     "[Error de Validación XSD] Línea 25: Elemento 'gCamItem' es obligatorio",
#     "[Error de Estructura] Namespace incorrecto. Esperado: http://ekuatia.set.gov.py/sifen/xsd"
# ]
```

## ⚙️ Configuración

### XSD Personalizado
```python
# Usar XSD específico
validator = SifenValidator("/path/to/custom.xsd")
is_valid, errors = validator.validate_xml(xml_content)
```

### Solo Errores Específicos
```python
from validators import get_xsd_errors_only, get_format_errors_only

# Solo errores XSD
xsd_errors = get_xsd_errors_only(xml_content)

# Solo errores de formato
format_errors = get_format_errors_only(xml_content)
```

## 📈 Análisis de Calidad

```python
from validators import analyze_xml_quality

analysis = analyze_xml_quality(xml_content)
print(f"Puntaje: {analysis['quality_score']['overall_score']}/100")
print(f"Nivel: {analysis['quality_score']['quality_level']}")
print("Recomendaciones:")
for rec in analysis['recommendations']:
    print(f"• {rec}")
```

## 🧪 Testing

### Casos de Prueba
```python
# XML válido mínimo
valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd" version="150">
    <DE Id="01234567890123456789012345678901234567890123">
        <dVerFor>150</dVerFor>
        <dCodSeg>123456789</dCodSeg>
        <!-- Resto del documento -->
    </DE>
</rDE>"""

assert quick_validate(valid_xml) == True
```

## 🔗 Dependencias

- **lxml** - Parsing XML y validación XSD
- **pathlib** - Manejo de rutas
- **typing** - Type hints
- **re** - Expresiones regulares para formatos

## 📁 Estructura de Archivos

```
validators/
├── __init__.py              # API principal (facade)
├── core_validator.py        # Validación XSD
├── structure_validator.py   # Validación estructura básica  
├── format_validator.py      # Validación formatos SIFEN
├── error_handler.py         # Manejo de errores
├── constants.py             # Constantes y patrones
└── README.md               # Esta documentación
```

## 🎯 Casos de Uso

### Generación de XML
```python
# Validar antes de envío
xml_generated = generate_invoice_xml(data)
is_valid, errors = validate_xml(xml_generated)
if not is_valid:
    raise ValidationError(f"XML inválido: {errors}")
```

### Pipeline de Procesamiento
```python
# Validación rápida inicial
if not quick_validate(xml_content):
    return {"error": "XML inválido"}

# Procesamiento normal...
```

### Debugging de Documentos
```python
# Análisis completo para debugging
report = validate_with_detailed_report(xml_content)
if not report['overall_valid']:
    print("Errores por tipo:")
    for validation_type, result in report['validation_results'].items():
        if not result['valid']:
            print(f"{validation_type}: {result['error_count']} errores")
```

## ⚡ Performance

### Optimizaciones
- **Lazy loading** de esquemas XSD
- **Cache** de schemas cargados
- **Fail-fast** para errores estructurales críticos
- **Búsqueda optimizada** de elementos XML

### Benchmarks Típicos
- Validación estructura: < 10ms
- Validación XSD: < 100ms  
- Validación formatos: < 50ms
- Documento típico (50KB): < 200ms total

## 🐛 Troubleshooting

### Errores Comunes

**Schema no encontrado**
```python
# Verificar ruta del XSD
validator = SifenValidator("/correct/path/to/DE_v150.xsd")
```

**XML malformado**
```python
# Verificar sintaxis básica
try:
    from lxml import etree
    etree.fromstring(xml_content)
except etree.XMLSyntaxError as e:
    print(f"Error sintaxis: {e}")
```

**Namespace incorrecto**
```python
# Verificar namespace SIFEN
assert 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml_content
```

---

## 📄 Licencia

Sistema de Facturación Electrónica Paraguay - SIFEN v150