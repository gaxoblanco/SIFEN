# 📄 XML Templates - Generador SIFEN v150

**Ubicación**: `backend/app/services/xml_generator/templates/`  
**Propósito**: Templates Jinja2 para generar documentos XML según Manual SIFEN v150  
**Motor**: Jinja2 Template Engine  
**Formato**: XML con validación XSD DE_v150.xsd

---

## 📊 **Arquitectura de Templates**

### **🎯 ESTRATEGIA: Templates Especializados por Tipo**
```
backend/app/services/xml_generator/templates/
├── 📄 base_document.xml              # Template base común (estructura rDE)
├── 📄 factura_electronica.xml        # Factura Electrónica (FE) - Tipo 1
├── 📄 autofactura_electronica.xml     # Autofactura Electrónica (AFE) - Tipo 4  
├── 📄 nota_credito_electronica.xml    # Nota Crédito Electrónica (NCE) - Tipo 5
├── 📄 nota_debito_electronica.xml     # Nota Débito Electrónica (NDE) - Tipo 6
├── 📄 nota_remision_electronica.xml   # Nota Remisión Electrónica (NRE) - Tipo 7
├── partials/
│   ├── 📄 _header_common.xml          # Header común (dVerFor, namespaces)
│   ├── 📄 _grupo_operacion.xml        # gOpeDE (datos operación)
│   ├── 📄 _grupo_timbrado.xml         # gTimb (timbrado)
│   ├── 📄 _grupo_datos_generales.xml  # gDatGralOpe (datos generales)
│   ├── 📄 _grupo_emisor.xml           # gDatEm (datos emisor)
│   ├── 📄 _grupo_receptor.xml         # gDatRec (datos receptor)
│   ├── 📄 _grupo_items.xml            # gCamItem (productos/servicios)
│   ├── 📄 _grupo_totales.xml          # gTotSub (totales y subtotales)
│   ├── 📄 _grupo_condiciones.xml      # gCamGen (condiciones pago)
│   ├── 📄 _grupo_transporte.xml       # gCamTrans (específico NRE)
│   └── 📄 _grupo_qr.xml               # gCamFuFD (código QR)
└── validation/
    ├── 📄 _validate_amounts.xml       # Validación montos
    ├── 📄 _validate_dates.xml         # Validación fechas
    └── 📄 _validate_ruc.xml           # Validación RUC/DV
```

---

## 🎯 **Templates Principales por Tipo**

### **📋 PRIORIDAD DE IMPLEMENTACIÓN**

#### **🔴 CRÍTICO (Implementar Primero)**
1. **`base_document.xml`** - Estructura base común
2. **`factura_electronica.xml`** - 90% de casos de uso
3. **Partials esenciales**: `_grupo_operacion.xml`, `_grupo_emisor.xml`, `_grupo_receptor.xml`

#### **🟡 ALTO (Implementar Segundo)**  
4. **`nota_credito_electronica.xml`** - Devoluciones comunes
5. **`nota_debito_electronica.xml`** - Cargos adicionales
6. **Partials específicos**: `_grupo_totales.xml`, `_grupo_condiciones.xml`

#### **🟢 MEDIO (Implementar Tercero)**
7. **`autofactura_electronica.xml`** - Casos especiales
8. **`nota_remision_electronica.xml`** - Transporte
9. **Partials avanzados**: `_grupo_transporte.xml`, `_validate_amounts.xml`

---

## 📝 **Especificaciones por Template**

### **1. base_document.xml** - Template Base Común
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- TEMPLATE BASE para todos los documentos SIFEN v150 -->
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd" 
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd"
     version="1.5.0">
    
    <!-- Versión formato (OBLIGATORIO) -->
    <dVerFor>150</dVerFor>
    
    <!-- Documento electrónico -->
    <DE Id="{{ cdc }}">
        <!-- Contenido específico por tipo -->
        {% block document_content %}{% endblock %}
    </DE>
    
    <!-- Firma digital (insertada por módulo firma) -->
    {% block digital_signature %}{% endblock %}
    
    <!-- Campos fuera de firma (QR) -->
    {% include 'partials/_grupo_qr.xml' %}
</rDE>
```

**Variables requeridas:**
- `cdc`: String 44 caracteres
- `document_content`: Bloque específico por tipo

---

### **2. factura_electronica.xml** - Factura Electrónica (FE)
```xml
{% extends "base_document.xml" %}

{% block document_content %}
    <!-- gOpeDE: Operación -->
    {% include 'partials/_grupo_operacion.xml' with context %}
    
    <!-- gTimb: Timbrado -->
    {% include 'partials/_grupo_timbrado.xml' with context %}
    
    <!-- gDatGralOpe: Datos generales -->
    {% include 'partials/_grupo_datos_generales.xml' with context %}
    
    <!-- gDtipDE: Específicos Factura -->
    <gDtipDE>
        <gCamFE>
            <iIndPres>{{ indicador_presencia | default(1) }}</iIndPres>
            <dDesIndPres>{{ descripcion_presencia | default("Operación presencial") }}</dDesIndPres>
            {% if condicion_credito %}
            <iIndRec>{{ indicador_recibo }}</iIndRec>
            <dDesIndRec>{{ descripcion_recibo }}</dDesIndRec>
            {% endif %}
        </gCamFE>
        
        <!-- Items -->
        {% include 'partials/_grupo_items.xml' with context %}
    </gDtipDE>
    
    <!-- gTotSub: Totales -->
    {% include 'partials/_grupo_totales.xml' with context %}
    
    <!-- gCamGen: Condiciones -->
    {% include 'partials/_grupo_condiciones.xml' with context %}
{% endblock %}
```

**Variables específicas FE:**
- `indicador_presencia`: 1-4
- `descripcion_presencia`: String
- `condicion_credito`: Boolean
- `indicador_recibo`: 1-2
- `descripcion_recibo`: String

---

### **3. nota_credito_electronica.xml** - Nota Crédito (NCE)
```xml
{% extends "base_document.xml" %}

{% block document_content %}
    <!-- Estructura similar a FE pero con campos específicos NCE -->
    {% include 'partials/_grupo_operacion.xml' with context %}
    {% include 'partials/_grupo_timbrado.xml' with context %}
    {% include 'partials/_grupo_datos_generales.xml' with context %}
    
    <!-- gDtipDE: Específicos Nota Crédito -->
    <gDtipDE>
        <gCamNCE>
            <iMotEmi>{{ motivo_emision | default(1) }}</iMotEmi>
            <dDesMotEmi>{{ descripcion_motivo | default("Devolución de mercadería") }}</dDesMotEmi>
        </gCamNCE>
        
        <!-- Items -->
        {% include 'partials/_grupo_items.xml' with context %}
    </gDtipDE>
    
    {% include 'partials/_grupo_totales.xml' with context %}
    {% include 'partials/_grupo_condiciones.xml' with context %}
    
    <!-- Documentos asociados (OBLIGATORIO para NCE) -->
    {% if documento_referencia %}
    <gCamDEAsoc>
        <iTipDocAso>{{ documento_referencia.tipo }}</iTipDocAso>
        <dDesTipDocAso>{{ documento_referencia.descripcion }}</dDesTipDocAso>
        <dCdCDERef>{{ documento_referencia.cdc }}</dCdCDERef>
        <dNTimDI>{{ documento_referencia.timbrado }}</dNTimDI>
        <dEstDI>{{ documento_referencia.establecimiento }}</dEstDI>
        <dPExpDI>{{ documento_referencia.punto_expedicion }}</dPExpDI>
        <dNumDI>{{ documento_referencia.numero }}</dNumDI>
        <dFecEmiDI>{{ documento_referencia.fecha_emision }}</dFecEmiDI>
    </gCamDEAsoc>
    {% endif %}
{% endblock %}
```

**Variables específicas NCE:**
- `motivo_emision`: 1-9
- `descripcion_motivo`: String
- `documento_referencia`: Object con datos factura original

---

### **4. nota_remision_electronica.xml** - Nota Remisión (NRE)
```xml
{% extends "base_document.xml" %}

{% block document_content %}
    {% include 'partials/_grupo_operacion.xml' with context %}
    {% include 'partials/_grupo_timbrado.xml' with context %}
    {% include 'partials/_grupo_datos_generales.xml' with context %}
    
    <!-- gDtipDE: Específicos Nota Remisión -->
    <gDtipDE>
        <gCamNRE>
            <iMotTras>{{ motivo_traslado | default(1) }}</iMotTras>
            <dDesMotTras>{{ descripcion_traslado | default("Venta") }}</dDesMotTras>
            <iRespFlete>{{ responsable_flete | default(1) }}</iRespFlete>
            <cCondTras>{{ condicion_transporte | default(1) }}</cCondTras>
            
            <!-- Transporte (OBLIGATORIO para NRE) -->
            {% include 'partials/_grupo_transporte.xml' with context %}
        </gCamNRE>
        
        <!-- Items -->
        {% include 'partials/_grupo_items.xml' with context %}
    </gDtipDE>
    
    {% include 'partials/_grupo_totales.xml' with context %}
    {% include 'partials/_grupo_condiciones.xml' with context %}
{% endblock %}
```

**Variables específicas NRE:**
- `motivo_traslado`: 1-9
- `descripcion_traslado`: String
- `responsable_flete`: 1-3
- `condicion_transporte`: 1-3
- `transporte`: Object con datos vehículos/rutas

---

## 🧩 **Templates Partials (Reutilizables)**

### **📄 partials/_grupo_operacion.xml**
```xml
<!-- gOpeDE: Datos de operación -->
<gOpeDE>
    <iTipDE>{{ tipo_documento }}</iTipDE>
    <dDesTipDE>{{ descripcion_tipo_documento }}</dDesTipDE>
    <dNumDoc>{{ numero_documento }}</dNumDoc>
    <dFeEmiDE>{{ fecha_emision }}</dFeEmiDE>
    <iTipEmi>{{ tipo_emision | default(1) }}</iTipEmi>
    <dCodSeg>{{ codigo_seguridad }}</dCodSeg>
    <dCDCDE>{{ cdc }}</dCDCDE>
</gOpeDE>
```

### **📄 partials/_grupo_emisor.xml**
```xml
<!-- gDatEm: Datos del emisor -->
<gDatEm>
    <dRucEm>{{ emisor.ruc }}</dRucEm>
    <dDVEmi>{{ emisor.dv }}</dDVEmi>
    <iTipIDEmi>1</iTipIDEmi>
    <dNomEmi>{{ emisor.razon_social }}</dNomEmi>
    {% if emisor.nombre_fantasia %}
    <dNomFanEmi>{{ emisor.nombre_fantasia }}</dNomFanEmi>
    {% endif %}
    <dDirEmi>{{ emisor.direccion }}</dDirEmi>
    {% if emisor.numero_casa %}
    <dNumCasEmi>{{ emisor.numero_casa }}</dNumCasEmi>
    {% endif %}
    <cDepEmi>{{ emisor.codigo_departamento }}</cDepEmi>
    <dDesDepEmi>{{ emisor.descripcion_departamento }}</dDesDepEmi>
    <cCiuEmi>{{ emisor.codigo_ciudad }}</cCiuEmi>
    <dDesCiuEmi>{{ emisor.descripcion_ciudad }}</dDesCiuEmi>
    {% if emisor.telefono %}
    <dTelEmi>{{ emisor.telefono }}</dTelEmi>
    {% endif %}
    {% if emisor.email %}
    <dEmailEmi>{{ emisor.email }}</dEmailEmi>
    {% endif %}
</gDatEm>
```

### **📄 partials/_grupo_items.xml**
```xml
<!-- gCamItem: Items/Productos -->
{% for item in items %}
<gCamItem>
    <dCodInt>{{ item.codigo }}</dCodInt>
    <dDesProSer>{{ item.descripcion }}</dDesProSer>
    <cUniMed>{{ item.unidad_medida | default(77) }}</cUniMed>
    <dDesUniMed>{{ item.descripcion_unidad | default("Unidad") }}</dDesUniMed>
    <dCantProSer>{{ item.cantidad }}</dCantProSer>
    <dPUniProSer>{{ item.precio_unitario }}</dPUniProSer>
    {% if item.tipo_cambio %}
    <dTiCamIt>{{ item.tipo_cambio }}</dTiCamIt>
    {% endif %}
    <dTotBruOpeItem>{{ item.total_bruto }}</dTotBruOpeItem>
    
    <!-- Valor del item -->
    <gValorItem>
        <dPUniProSer>{{ item.precio_unitario }}</dPUniProSer>
        <dTotBruOpeItem>{{ item.total_bruto }}</dTotBruOpeItem>
        <gValorRestaItem>
            {% if item.descuento %}
            <dDescItem>{{ item.descuento }}</dDescItem>
            <dPorcDesIt>{{ item.porcentaje_descuento }}</dPorcDesIt>
            {% endif %}
            <dTotOpe>{{ item.total_operacion }}</dTotOpe>
        </gValorRestaItem>
    </gValorItem>
    
    <!-- IVA del item -->
    <gCamIVA>
        <iAfecIVA>{{ item.afectacion_iva | default(1) }}</iAfecIVA>
        <dDesAfecIVA>{{ item.descripcion_iva | default("Gravado IVA") }}</dDesAfecIVA>
        {% if item.tasa_iva > 0 %}
        <dPropIVA>{{ item.proporcion_iva | default(100) }}</dPropIVA>
        <dTasaIVA>{{ item.tasa_iva }}</dTasaIVA>
        <dBasGravIVA>{{ item.base_gravada }}</dBasGravIVA>
        <dLiqIVAItem>{{ item.iva_liquidado }}</dLiqIVAItem>
        {% else %}
        <dBasExe>{{ item.base_exenta }}</dBasExe>
        {% endif %}
    </gCamIVA>
</gCamItem>
{% endfor %}
```

---

## 🔧 **Configuración y Uso**

### **Variables de Contexto Comunes (Todos los Templates)**
```python
# Variables obligatorias para todos los templates
context = {
    # Datos del documento
    'cdc': '01800695631001001000000120240101100000123456789',
    'tipo_documento': '1',  # 1,4,5,6,7
    'descripcion_tipo_documento': 'Factura electrónica',
    'numero_documento': '001-001-0000001',
    'fecha_emision': '2024-01-01T10:00:00',
    'codigo_seguridad': '123456789',
    
    # Timbrado
    'timbrado': {
        'numero': '12345678',
        'establecimiento': '001',
        'punto_expedicion': '001',
        'fecha_inicio': '2024-01-01'
    },
    
    # Emisor
    'emisor': {
        'ruc': '80016875',
        'dv': '5',
        'razon_social': 'Empresa Test S.A.',
        'direccion': 'Av. Mariscal López 1234',
        'codigo_departamento': 11,
        'descripcion_departamento': 'CENTRAL',
        'codigo_ciudad': 1,
        'descripcion_ciudad': 'ASUNCIÓN',
        'telefono': '+595981123456',
        'email': 'facturacion@empresa.com.py'
    },
    
    # Receptor
    'receptor': {
        'naturaleza': 1,  # 1=Contribuyente, 2=No contribuyente
        'tipo_operacion': 1,  # 1=B2B, 2=B2C, 3=B2G, 4=B2F
        'pais': 'PRY',
        'ruc': '4444444',
        'dv': '4',
        'razon_social': 'Cliente de Prueba S.A.',
        'direccion': 'Calle Cliente 123',
        'codigo_departamento': 11,
        'codigo_ciudad': 1
    },
    
    # Items
    'items': [
        {
            'codigo': 'PROD001',
            'descripcion': 'Producto de prueba',
            'cantidad': 1.0,
            'precio_unitario': 100000.0,
            'total_bruto': 100000.0,
            'total_operacion': 100000.0,
            'tasa_iva': 10.0,
            'base_gravada': 100000.0,
            'iva_liquidado': 10000.0
        }
    ],
    
    # Totales
    'totales': {
        'sub_exento': 0.0,
        'sub_5': 0.0,
        'sub_10': 100000.0,
        'total_operacion': 100000.0,
        'total_iva': 10000.0,
        'total_general': 110000.0,
        'base_gravada_total': 100000.0
    },
    
    # Condiciones
    'condicion_operacion': 1,  # 1=Contado, 2=Crédito
    'descripcion_condicion': 'Contado',
    
    # Moneda
    'moneda': 'PYG',
    'tipo_cambio': 1.0
}
```

### **Variables Específicas por Tipo**
```python
# Adicionales para Nota de Crédito
nota_credito_context = {
    'motivo_emision': 1,  # 1=Devolución, 2=Descuento, etc.
    'descripcion_motivo': 'Devolución de mercadería',
    'documento_referencia': {
        'tipo': 1,
        'descripcion': 'Factura electrónica',
        'cdc': '01800695631001001000000120240101100000123456788',
        'timbrado': '12345678',
        'establecimiento': '001',
        'punto_expedicion': '001',
        'numero': '0000001',
        'fecha_emision': '2024-01-01'
    }
}

# Adicionales para Nota de Remisión
nota_remision_context = {
    'motivo_traslado': 1,  # 1=Venta, 2=Traslado, etc.
    'descripcion_traslado': 'Venta',
    'responsable_flete': 1,  # 1=Emisor, 2=Receptor, 3=Tercero
    'condicion_transporte': 1,  # 1=Cuenta propia, 2=Terceros
    'transporte': {
        'tipo': 1,  # 1=Terrestre, 2=Aéreo, 3=Acuático
        'modalidad': 1,  # 1=Propio, 2=Tercerizado
        'direccion_salida': 'Depósito Central - Av. Principal 123',
        'direccion_entrega': 'Cliente - Calle Destino 456',
        'fecha_salida': '2024-01-01T08:00:00',
        'vehiculos': [
            {
                'tipo': 2,  # 2=Camión
                'marca': 'Volvo',
                'chapa': 'ABC123',
                'numero_senacsa': 'SEN123456'
            }
        ]
    }
}
```

---

## 🧪 **Testing de Templates**

### **Estructura Tests Templates**
```
backend/app/services/xml_generator/tests/
├── test_templates/
│   ├── test_base_template.py
│   ├── test_factura_template.py
│   ├── test_nota_credito_template.py
│   ├── test_nota_debito_template.py
│   ├── test_nota_remision_template.py
│   └── test_partials/
│       ├── test_grupo_operacion.py
│       ├── test_grupo_emisor.py
│       ├── test_grupo_receptor.py
│       ├── test_grupo_items.py
│       └── test_grupo_totales.py
└── fixtures/
    ├── template_contexts.py
    └── expected_xmls/
        ├── factura_expected.xml
        ├── nota_credito_expected.xml
        └── etc.
```

### **Ejemplo Test Template**
```python
def test_factura_template_generation():
    """Test generación template factura electrónica"""
    context = get_factura_context()
    
    template_engine = TemplateEngine()
    xml = template_engine.render('factura_electronica.xml', context)
    
    # Validar estructura
    assert '<iTipDE>1</iTipDE>' in xml
    assert '<dRucEm>80016875</dRucEm>' in xml
    assert '<dTotGralOpe>110000</dTotGralOpe>' in xml
    
    # Validar contra XSD
    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"XML inválido: {errors}"
```

---

## 🎯 **Plan de Implementación**

### **Fase 1: Base y Factura (Días 1-2)**
1. ✅ `base_document.xml`
2. ✅ `factura_electronica.xml`
3. ✅ Partials básicos: `_grupo_operacion.xml`, `_grupo_emisor.xml`

### **Fase 2: Notas Crédito/Débito (Días 3-4)**
4. ✅ `nota_credito_electronica.xml`
5. ✅ `nota_debito_electronica.xml`  
6. ✅ Partials avanzados: `_grupo_totales.xml`, `_grupo_condiciones.xml`

### **Fase 3: Remisión y Autofactura (Días 5-6)**
7. ✅ `nota_remision_electronica.xml`
8. ✅ `autofactura_electronica.xml`
9. ✅ Partials específicos: `_grupo_transporte.xml`

### **Fase 4: Validación y QR (Día 7)**
10. ✅ `_grupo_qr.xml`
11. ✅ Templates validación
12. ✅ Tests comprehensivos

---

## 📚 **Referencias**

- **Jinja2 Documentation**: https://jinja.palletsprojects.com/
- **Manual SIFEN v150**: Estructura XML oficial
- **XSD Schema**: DE_v150.xsd corregido
- **Template Engine**: `backend/app/services/xml_generator/template_engine.py`

---

## ✅ **Checklist Completitud Templates**

- [ ] **base_document.xml** - Template base con herencia
- [ ] **factura_electronica.xml** - FE completa
- [ ] **nota_credito_electronica.xml** - NCE con referencias
- [ ] **nota_debito_electronica.xml** - NDE específica
- [ ] **nota_remision_electronica.xml** - NRE con transporte
- [ ] **autofactura_electronica.xml** - AFE especializada
- [ ] **Partials reutilizables** - Todos los grupos principales
- [ ] **Tests templates** - Cobertura >90%
- [ ] **Validación XSD** - Todos templates válidos
- [ ] **Documentación uso** - Ejemplos contexto

**META**: Templates modulares, mantenibles y 100% compatibles con XSD corregido.