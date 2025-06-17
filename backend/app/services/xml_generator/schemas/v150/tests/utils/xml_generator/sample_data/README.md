# 📊 Sample Data - Datos Paraguayos para Testing SIFEN v150

Módulo de datos realistas del mercado paraguayo para testing de schemas modulares SIFEN.

## 🎯 Propósito

Proporciona datos verificables de PyMEs paraguayas para generar XMLs de prueba que representen el 85-95% de casos reales de facturación electrónica en Paraguay.

## 🚀 Uso Rápido

```python
from sample_data import SampleData

# Instanciar API
sample = SampleData()

# Datos básicos
emisor = sample.get_test_emisor("ferreteria_central")
receptor = sample.get_test_receptor("consumidor_final")
items = sample.get_test_items("ferreteria", 2)

# Escenarios predefinidos
escenario = sample.get_test_scenario("factura_farmacia_mixta")

# Facturas listas para usar
factura_simple = sample.get_simple_invoice_data()
factura_compleja = sample.get_complex_invoice_data()
```

## 📂 Módulos Incluidos

| Módulo | Descripción | Datos |
|--------|-------------|-------|
| `empresas_data` | Emisores típicos paraguayos | 4 empresas por sector |
| `clientes_data` | Receptores frecuentes | 3 tipos de clientes |
| `productos_data` | Catálogo con precios PY | 8 productos/servicios |
| `ubicaciones_data` | Geografía Paraguay | 5 ciudades principales |
| `validadores_data` | Datos de validación | RUCs, teléfonos válidos |
| `escenarios_testing` | Casos predefinidos | 4 escenarios típicos |

## 🏢 Sectores Cubiertos

- **Servicios Profesionales**: Consultorías, contadores
- **Comercio Minorista**: Ferreterías, farmacias  
- **Servicios Técnicos**: Talleres, reparaciones
- **Salud**: Farmacia con productos exentos/gravados

## 💰 Datos Realistas

- ✅ Precios mercado paraguayo 2024
- ✅ RUCs formato oficial Paraguay
- ✅ IVA según normativa (0%, 10%)
- ✅ Direcciones zonas comerciales reales
- ✅ Teléfonos formato paraguayo

## 🎭 Escenarios Disponibles

```python
# Casos típicos PyMEs
"factura_consultora_simple"     # Servicios profesionales
"factura_ferreteria_multiple"   # Retail múltiples productos  
"factura_farmacia_mixta"        # IVA mixto (0% + 10%)
"factura_taller_credito"        # Servicios técnicos a crédito
```

## 📋 Compatibilidad

- **SIFEN v150**: Manual Técnico oficial
- **PyMEs Target**: 10-50 facturas/día
- **Cobertura**: 85% casos básicos Paraguay
- **Testing**: Schemas modulares + DocumentTypesGenerator