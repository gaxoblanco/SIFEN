# 📄 XML Templates SIFEN v150 - Guía Completa

**Ubicación**: `backend/app/services/xml_generator/templates/`  
**Propósito**: Templates Jinja2 para generar documentos XML según Manual SIFEN v150  
**Motor**: Jinja2 Template Engine  
**Formato**: XML válido contra XSD DE_v150.xsd  
**Autor**: Sistema modular para Paraguay - SIFEN

---

## 🎯 **Arquitectura de Templates**

### **📁 Estructura Completa a Implementar**
```
backend/app/services/xml_generator/templates/
├── 📄 base_document.xml                    # ✅ PRIORIDAD 1 - Template base común
├── 📄 factura_electronica.xml              # ✅ Tipo 1 (FE)
├── 📄 autofactura_electronica.xml          # ✅ Tipo 4 (AFE)  
├── 📄 nota_credito_electronica.xml         # ✅ Tipo 5 (NCE)
├── 📄 nota_debito_electronica.xml          # ✅ Tipo 6 (NDE)
├── 📄 nota_remision_electronica.xml        # ✅ Tipo 7 (NRE)
├── partials/                                # 📁 Componentes reutilizables
│   ├── 📄 _header_common.xml               # ✅ - Header + namespaces
│   ├── 📄 _grupo_operacion.xml             # ✅ - gOpeDE (datos operación)
│   ├── 📄 _grupo_timbrado.xml              # ✅ - gTimb (timbrado)
│   ├── 📄 _grupo_datos_generales.xml       # ✅ - gDatGralOpe
│   ├── 📄 _grupo_emisor.xml                # ✅ - gDatEm (datos emisor)
│   ├── 📄 _grupo_receptor.xml              # ✅ - gDatRec (datos receptor)
│   ├── 📄 _grupo_items.xml                 # ✅ - gCamItem (productos)
│   ├── 📄 _grupo_totales.xml               # ✅ - gTotSub (totales)
│   ├── 📄 _grupo_condiciones.xml           # ✅ - gCamGen (condiciones)
│   ├── 📄 _grupo_transporte.xml            # ✅ - gCamTrans (NRE específico)
│   ├── 📄 _grupo_qr.xml                    # ✅ - gCamFuFD (código QR)
│   ├── 📄 _seccion_afe.xml                 # ✅ - gCamAE (AFE específico)
│   └── 📄 _documento_asociado.xml          # ✅ - Ref docs (NCE/NDE)
└── validation/                              # 📁 Helpers de validación
    ├── 📄 _validate_amounts.xml            # ✅ - Validación montos
    ├── 📄 _validate_dates.xml              # ✅ - Validación fechas
    └── 📄 _validate_ruc.xml                # ✅ - Validación RUC/DV
```

---

## 🎯 **Plan de Implementación con Claude**

#### **2.2 nota_debito_electronica.xml** 🔄 **SEGUNDA PRIORIDAD**  
```xml
<!-- NDE - Tipo 6: Cargos adicionales, intereses, gastos -->
<!-- Variables: documento_asociado, motivo_debito, montos_adicionales -->
<!-- Características: referencia documento original, totales aumentan deuda -->
```

**Prompt para Claude:**
> Genera template `nota_debito_electronica.xml` que:
> - Extienda de base_document.xml
> - iTipDE = 6
> - Incluya sección documento asociado
> - Maneje cargos adicionales
> - Incluya tipos específicos NDE (intereses, gastos, otros)

### **📋 FASE 4: Transporte (Días 7-8)**

#### **4.1 nota_remision_electronica.xml** 🔄 **CUARTA PRIORIDAD**
```xml
<!-- NRE - Tipo 7: Traslado mercaderías sin venta -->
<!-- Variables: datos_transporte, vehiculos, direcciones -->
<!-- Características: totales = 0, datos transporte obligatorios -->
```

**Prompt para Claude:**
> Genera template `nota_remision_electronica.xml` que:
> - Extienda de base_document.xml
> - iTipDE = 7
> - Totales monetarios = 0
> - Incluya sección transporte completa
> - Maneje múltiples vehículos

## 📝 **Especificaciones Técnicas por Template**

### **🔧 Variables de Contexto por Template**

#### **base_document.xml**
```python
context = {
    'cdc': str,              # 44 caracteres CDC
    'version': str,          # "150" 
    # Blocks: document_content, digital_signature
}
```

#### **factura_electronica.xml** ✅ **YA EXISTE**
```python
context = {
    'tipo_documento': "1",
    'emisor': dict,          # RUC, razón social, dirección
    'receptor': dict,        # RUC, razón social, dirección  
    'items': list,           # Productos/servicios
    'totales': dict,         # Gravadas, IVA, total general
    'condiciones': dict,     # Venta, pago, crédito
    'fecha_emision': str,    # ISO format
}
```

#### **nota_credito_electronica.xml**
```python
context = {
    'tipo_documento': "5",
    'documento_asociado': {
        'tipo_doc_ref': str,     # Tipo documento original
        'numero_doc_ref': str,   # Número documento original
        'fecha_doc_ref': str,    # Fecha documento original  
        'cdc_ref': str,          # CDC documento original
    },
    'motivo_credito': str,       # Razón devolución
    'tipo_credito': str,         # 1=Total, 2=Parcial
    # + variables comunes factura
}
```

#### **autofactura_electronica.xml**
```python
context = {
    'tipo_documento': "4",
    'datos_afe': {
        'naturaleza_vendedor': str,  # 1=No contribuyente, 2=Extranjero
        'tipo_documento_vendedor': str,
        'numero_documento_vendedor': str,
        'nombre_vendedor': str,
        'direccion_vendedor': str,
        'pais_vendedor': str,        # Para extranjeros
    },
    'tipo_operacion_afe': str,       # 1=Importación, 2=No contribuyente
    # + variables comunes factura
}
```

#### **nota_remision_electronica.xml**
```python
context = {
    'tipo_documento': "7",
    'datos_transporte': {
        'tipo_responsable': str,     # 1=Emisor, 2=Receptor, 3=Tercero
        'modalidad_transporte': str, # 1=Propio, 2=Tercerizado
        'tipo_transporte': str,      # 1=Terrestre, 2=Aéreo, 3=Acuático
        'fecha_inicio_traslado': str,
        'direccion_salida': str,
        'direccion_llegada': str,
    },
    'vehiculos': [
        {
            'tipo_vehiculo': str,    # 1=Auto, 2=Camión, 3=Moto
            'marca': str,
            'numero_chapa': str,
            'numero_senacsa': str,   # Opcional
        }
    ],
    'totales': {                     # TODOS EN 0 para NRE
        'total_gravadas': 0,
        'total_iva': 0,
        'total_general': 0,
    }
}
```

---

### **📝 Template Test Pattern**
```python
def test_{tipo}_template_generation():
    """Test generación template {tipo}"""
    context = get_{tipo}_context()
    
    template_engine = TemplateEngine()
    xml = template_engine.render('{tipo}.xml', context)
    
    # Validar estructura específica
    assert f'<iTipDE>{codigo}</iTipDE>' in xml
    assert '<dRucEm>' in xml
    assert '<dTotGralOpe>' in xml
    
    # Validar contra XSD
    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"XML inválido: {errors}"
```

## 🎯 **Meta Final**

**OBJETIVO**: Templates modulares, mantenibles, 100% compatibles con XSD DE_v150.xsd corregido, que soporten los 5 tipos de documento SIFEN v150 con reutilización máxima de código.

**RESULTADO ESPERADO**: Sistema de templates que permita generar XMLs válidos para cualquier tipo de documento electrónico paraguayo con contextos específicos por tipo y validación automática.