# 🧩 **Partials SIFEN - Guía Simple**

**Concepto**: Componentes XML reutilizables para evitar duplicar código.

---

## 📁 **Partials Disponibles**

| Partial | Para qué sirve | Cuándo usarlo |
|---------|----------------|---------------|
| `_grupo_operacion.xml` | Datos básicos del documento | **Siempre** |
| `_grupo_timbrado.xml` | Datos del timbrado SET | **Siempre** |
| `_grupo_emisor.xml` | Datos de quien emite | **Siempre** |
| `_grupo_receptor.xml` | Datos de quien recibe | **Siempre** |
| `_grupo_items.xml` | Productos/servicios | **Siempre** (en loop) |
| `_grupo_totales.xml` | Montos y totales | **Siempre** |
| `_grupo_condiciones.xml` | Formas de pago | **Opcional** |
| `_seccion_afe.xml` | Datos vendedor AFE | **Solo AFE** |
| `_documento_asociado.xml` | Referencia a otro doc | **Solo NCE/NDE** |
| `_grupo_transporte.xml` | Datos de transporte | **Solo NRE** |

---

## 🔥 **Uso Básico**

### **Template sin partials (MALO)**
```xml
<!-- Repetir 500 líneas en cada template -->
<gOpeDE>
    <iTipDE>1</iTipDE>
    <dDesTipDE>Factura electrónica</dDesTipDE>
    <!-- ... 50 líneas más ... -->
</gOpeDE>
<gTimb>
    <!-- ... 30 líneas más ... -->
</gTimb>
<!-- etc... -->
```

### **Template con partials (BUENO)**
```xml
{% include '_grupo_operacion.xml' %}
{% include '_grupo_timbrado.xml' %}
{% include '_grupo_emisor.xml' %}
{% include '_grupo_receptor.xml' %}

{% for item in items %}
    {% include '_grupo_items.xml' %}
{% endfor %}

{% include '_grupo_totales.xml' %}
```

---

## 🎯 **Plantillas por Tipo**

### **Factura Electrónica (FE)**
```xml
<?xml version="1.0" encoding="UTF-8"?>
{% extends "base_document.xml" %}

{% block document_content %}
    {% include '_grupo_operacion.xml' %}
    {% include '_grupo_timbrado.xml' %}
    {% include '_grupo_emisor.xml' %}
    {% include '_grupo_receptor.xml' %}
    
    {% for item in items %}
        {% include '_grupo_items.xml' %}
    {% endfor %}
    
    {% include '_grupo_totales.xml' %}
    
    <!-- FE específico -->
    <gDtipDE>
        <gCamFE>
            <iIndPres>{{ indicador_presencia | default(1) }}</iIndPres>
            <dDesIndPres>{{ descripcion_presencia | default("Operación presencial") }}</dDesIndPres>
        </gCamFE>
    </gDtipDE>
    
    {% include '_grupo_condiciones.xml' %}
{% endblock %}
```

### **Autofactura Electrónica (AFE)**
```xml
{% extends "base_document.xml" %}

{% block document_content %}
    {% include '_grupo_operacion.xml' %}
    {% include '_grupo_timbrado.xml' %}
    {% include '_grupo_emisor.xml' %}
    {% include '_grupo_receptor.xml' %}
    
    {% for item in items %}
        {% include '_grupo_items.xml' %}
    {% endfor %}
    
    {% include '_grupo_totales.xml' %}
    
    <!-- AFE específico -->
    <gDtipDE>
        {% include '_seccion_afe.xml' %}
    </gDtipDE>
    
    {% include '_grupo_condiciones.xml' %}
{% endblock %}
```

### **Nota de Crédito (NCE)**
```xml
{% extends "base_document.xml" %}

{% block document_content %}
    {% include '_grupo_operacion.xml' %}
    {% include '_grupo_timbrado.xml' %}
    {% include '_grupo_emisor.xml' %}
    {% include '_grupo_receptor.xml' %}
    
    <!-- OBLIGATORIO en NCE -->
    {% include '_documento_asociado.xml' %}
    
    {% for item in items %}
        {% include '_grupo_items.xml' %}
    {% endfor %}
    
    {% include '_grupo_totales.xml' %}
    
    <!-- NCE específico -->
    <gDtipDE>
        <gCamNCE>
            <iMotEmiNC>{{ motivo_nota_credito }}</iMotEmiNC>
            <dDesMotEmiNC>{{ descripcion_motivo }}</dDesMotEmiNC>
        </gCamNCE>
    </gDtipDE>
    
    {% include '_grupo_condiciones.xml' %}
{% endblock %}
```

### **Nota de Remisión (NRE)**
```xml
{% extends "base_document.xml" %}

{% block document_content %}
    {% include '_grupo_operacion.xml' %}
    {% include '_grupo_timbrado.xml' %}
    {% include '_grupo_emisor.xml' %}
    {% include '_grupo_receptor.xml' %}
    
    {% for item in items %}
        {% include '_grupo_items.xml' %}
    {% endfor %}
    
    {% include '_grupo_totales.xml' %}
    
    <!-- OBLIGATORIO en NRE -->
    {% include '_grupo_transporte.xml' %}
{% endblock %}
```

---

## 💡 **Ventajas**

### **Antes (sin partials)**
- ❌ **2,500 líneas** de código duplicado
- ❌ **5 templates** con el mismo código
- ❌ **Mantenimiento** pesadilla
- ❌ **Inconsistencias** entre templates

### **Después (con partials)**
- ✅ **650 líneas** total
- ✅ **74% menos código**
- ✅ **Un cambio** = actualiza todos
- ✅ **Consistencia** garantizada

---

## 🚀 **Variables por Partial**

### **Obligatorias (siempre)**
```python
context = {
    'tipo_documento': "1",  # 1=FE, 4=AFE, 5=NCE, 6=NDE, 7=NRE
    'descripcion_tipo_documento': "Factura electrónica",
    'fecha_emision': "2025-06-30T14:30:00",
    'timbrado': {...},
    'emisor': {...},
    'receptor': {...},
    'items': [...],
    'totales': {...}
}
```

### **Específicas AFE**
```python
context.update({
    'vendedor': {
        'naturaleza_vendedor': "2",  # 1=No contribuyente, 2=Extranjero
        'nombre_vendedor': "International Corp",
        # ... más campos vendedor
    }
})
```

### **Específicas NCE/NDE**
```python
context.update({
    'documento_asociado': {
        'tipo_documento_ref': "1",
        'cdc_ref': "01234567890123456789012345678901234567890123",
        'numero_documento_ref': "001-001-0000123",
        'fecha_documento_ref': "2025-06-29T10:00:00"
    }
})
```

### **Específicas NRE**
```python
context.update({
    'transporte': {
        'tipo_responsable': "1",  # 1=Emisor, 2=Receptor, 3=Tercero
        'modalidad_transporte': "1",  # 1=Propio, 2=Tercerizado
        'tipo_transporte': "1",  # 1=Terrestre, 2=Aéreo, 3=Acuático
        'fecha_inicio_traslado': "2025-06-30T08:00:00",
        'direccion_salida': "Depósito Central",
        'direccion_llegada': "Sucursal Norte"
    },
    'vehiculos': [...],
    'conductores': [...]
})
```

---

## ⚡ **Test Rápido**

```python
from jinja2 import Environment, FileSystemLoader

# Configurar Jinja2
env = Environment(loader=FileSystemLoader('templates/'))

# Cargar template
template = env.get_template('factura_electronica.xml')

# Renderizar con datos
xml = template.render(context)

# ¡Listo! XML generado con partials
```

---

## 🎯 **Próximo Paso**

1. **Crear** templates NCE, NDE, NRE usando estos partials
2. **Refactorizar** templates existentes
3. **Testing** de cada partial por separado

**Resultado**: Sistema modular, mantenible y consistente 🚀