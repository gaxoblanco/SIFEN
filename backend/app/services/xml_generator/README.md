# Módulo: XML Generator

## Propósito
Genera y valida documentos XML según las especificaciones del Manual Técnico SIFEN v150.

## API Pública
- `generate_simple_invoice_xml()` - Genera XML para factura simple
- `validate_xml()` - Valida XML contra esquemas XSD

## Dependencias
- Externa: lxml, xmlschema
- Interna: shared.types, shared.validators

## Uso Básico
```python
from .xml_generator import generate_simple_invoice_xml
xml = generate_simple_invoice_xml(datos_factura)
```

## Tests
```bash
pytest backend/app/services/xml_generator/tests/ -v
```

## Troubleshooting
- Error de validación XSD: Verificar esquemas en ./schemas/
- Error de formato: Revisar estructura según Manual Técnico v150 