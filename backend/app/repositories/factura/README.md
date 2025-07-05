# 📁 FacturaRepository - Plan de Implementación

## 🎯 Objetivo

Implementar un módulo de gestión de facturas usando la **arquitectura modular exitosa** del DocumentoRepository, con composición de mixins para máxima mantenibilidad y escalabilidad.

---

## 🏗️ Arquitectura Propuesta

### **Estructura de Archivos**
```
backend/app/repositories/factura/
├── __init__.py                    # Compositor principal
├── base.py                       # FacturaRepositoryBase (CRUD core)
├── numeracion_mixin.py           # Gestión de numeración automática
├── estado_mixin.py               # Estados y transiciones específicas
├── stats_mixin.py                # Estadísticas específicas de facturas
├── validation_mixin.py           # Validaciones específicas de facturas
├── utils.py                      #- Utilidades compartidas de facturas
└── README.md                     # Documentación del módulo
```

### **Patrón de Composición**
```python
# En __init__.py
class FacturaRepository(
    FacturaRepositoryBase,         # CRUD core
    FacturaNumeracionMixin,        # Numeración automática
    FacturaEstadoMixin,            # Estados específicos
    FacturaStatsMixin,             # Estadísticas de facturas
    FacturaValidationMixin         # Validaciones específicas
):
    """Repository completo para facturas con todos los mixins"""
    pass
```

---

## 📋 Plan de Implementación

### **Fase 1: Fundación (Día 1-2) - 40%**

#### **1.1 utils.py - Utilidades Específicas**
```python
"""
Utilidades específicas para el módulo FacturaRepository.
Funciones helper y constantes específicas de facturas.
"""

# Funciones principales:
- format_numero_factura()         # Formatear número EST-PEX-NUM
- validate_factura_format()       # Validar formato específico facturas
- calculate_factura_totals()      # Cálculos de totales y IVA
- get_next_numero_available()     # Próximo número disponible
- validate_timbrado_vigency()     # Validar vigencia timbrado
- format_factura_for_display()    # Formatear para UI
```

#### **1.2 base.py - FacturaRepositoryBase**
```python
"""
Repository base para facturas.
Hereda de BaseRepository y añade operaciones específicas de facturas.
"""

class FacturaRepositoryBase(BaseRepository[Factura, FacturaCreateDTO, FacturaUpdateDTO]):
    
    # === MÉTODOS DE BÚSQUEDA ===
    def get_by_numero_factura()      # Buscar por número factura
    def get_by_rango_fechas()        # Facturas en rango fechas
    def get_by_cliente()             # Facturas por cliente
    def get_by_timbrado()            # Facturas por timbrado
    def get_pendientes_cobro()       # Facturas pendientes cobro
    
    # === MÉTODOS DE CÁLCULO ===
    def calcular_totales()           # Calcular totales automáticamente
    def recalcular_impuestos()       # Recalcular IVA
    def validate_amounts()           # Validar coherencia montos
    
    # === MÉTODOS DE CONTEO ===
    def count_by_cliente()           # Contar facturas por cliente
    def count_by_periodo()           # Contar por período
    def get_total_facturado()        # Total facturado en período
```

#### **1.3 __init__.py - Compositor Básico**
```python
"""
Compositor principal del FacturaRepository.
Combina todos los mixins usando herencia múltiple.
"""

from .base import FacturaRepositoryBase
# TODO: Importar otros mixins cuando estén listos

class FacturaRepository(FacturaRepositoryBase):
    """Repository básico para facturas (Fase 1)"""
    pass

# Export principal
__all__ = ["FacturaRepository"]
```

#### **1.4 README.md - Documentación**
- Propósito del módulo
- Estado de implementación por fases
- Ejemplos de uso
- Roadmap de desarrollo

**Entregable Fase 1**: Repository básico funcional para facturas

---

### **Fase 2: Numeración (Día 3-4) - 25%**

#### **2.1 numeracion_mixin.py - Gestión de Numeración**
```python
"""
Mixin para gestión de numeración automática de facturas.
Maneja secuencias, rangos, timbrados y validaciones de numeración.
"""

class FacturaNumeracionMixin:
    
    # === NUMERACIÓN AUTOMÁTICA ===
    def get_next_numero()            # Obtener próximo número en secuencia
    def reserve_numero_range()       # Reservar rango de números
    def validate_numeracion()        # Validar numeración disponible
    def check_numero_duplicado()     # Verificar duplicados
    
    # === GESTIÓN TIMBRADOS ===
    def get_timbrado_vigente()       # Obtener timbrado vigente
    def check_timbrado_vigency()     # Verificar vigencia timbrado
    def validate_timbrado_range()    # Validar rango permitido
    def get_timbrados_by_empresa()   # Timbrados de empresa
    
    # === SECUENCIAS ===
    def get_ultima_factura()         # Última factura emitida
    def get_secuencia_actual()       # Secuencia actual por establishment
    def reset_secuencia()            # Reset secuencia (nuevo año)
    def validate_secuencia_continua() # Validar continuidad
```

#### **2.2 Integración en Compositor**
```python
# Actualizar __init__.py
class FacturaRepository(
    FacturaRepositoryBase,
    FacturaNumeracionMixin
):
    """Repository con numeración automática"""
    pass
```

**Entregable Fase 2**: Numeración automática funcionando

---

### **Fase 3: Estados (Día 5-6) - 20%**

#### **3.1 estado_mixin.py - Estados Específicos**
```python
"""
Mixin para gestión de estados específicos de facturas.
Extiende los estados base con lógica específica de facturas.
"""

class FacturaEstadoMixin:
    
    # === ESTADOS ESPECÍFICOS FACTURAS ===
    def marcar_como_cobrada()        # Marcar factura como cobrada
    def marcar_como_anulada()        # Anular factura
    def marcar_como_vencida()        # Marcar como vencida
    def reabrir_factura()            # Reabrir factura cancelada
    
    # === TRANSICIONES ESPECÍFICAS ===
    def validate_factura_transition() # Validar transición específica
    def can_be_collected()           # Verificar si puede cobrarse
    def can_be_cancelled()           # Verificar si puede anularse
    def get_estado_cobranza()        # Estado específico de cobranza
    
    # === CONSULTAS POR ESTADO ===
    def get_facturas_pendientes_cobro() # Facturas pendientes cobro
    def get_facturas_vencidas()      # Facturas vencidas
    def get_facturas_anuladas()      # Facturas anuladas
    def get_facturas_en_proceso()    # Facturas en proceso
```

**Entregable Fase 3**: Gestión de estados completa

---

### **Fase 4: Validaciones y Stats (Día 7-8) - 15%**

#### **4.1 validation_mixin.py - Validaciones Específicas**
```python
"""
Validaciones de negocio específicas para facturas.
Complementa las validaciones base con reglas específicas.
"""

class FacturaValidationMixin:
    
    # === VALIDACIONES DATOS ===
    def validate_factura_data()      # Validar estructura factura
    def validate_items_consistency() # Validar coherencia items
    def validate_tax_calculations()  # Validar cálculos IVA
    def validate_totals()            # Validar totales calculados
    
    # === VALIDACIONES NEGOCIO ===
    def validate_client_requirements() # Validar requisitos cliente
    def validate_payment_terms()     # Validar términos pago
    def validate_credit_limit()      # Validar límite crédito
    def validate_business_rules()    # Reglas negocio específicas
    
    # === VALIDACIONES SIFEN ===
    def validate_sifen_factura()     # Validaciones SIFEN específicas
    def validate_factura_export()    # Validar para exportación
    def validate_xml_generation()    # Validar antes generar XML
```

#### **4.2 stats_mixin.py - Estadísticas Específicas**
```python
"""
Estadísticas y métricas específicas de facturas.
Complementa las estadísticas generales con análisis de facturas.
"""

class FacturaStatsMixin:
    
    # === ESTADÍSTICAS FACTURACIÓN ===
    def get_facturacion_stats()      # Estadísticas generales facturación
    def get_revenue_by_period()      # Ingresos por período
    def get_average_invoice_value()  # Valor promedio facturas
    def get_top_clients()            # Clientes top por facturación
    
    # === ANÁLISIS PRODUCTOS ===
    def get_top_productos()          # Productos más vendidos
    def get_product_performance()    # Performance por producto
    def get_category_analysis()      # Análisis por categoría
    
    # === MÉTRICAS OPERACIONALES ===
    def get_conversion_rates()       # Tasas conversión
    def get_payment_analysis()       # Análisis de pagos
    def get_collection_metrics()     # Métricas de cobranza
    def get_operational_kpis()       # KPIs operacionales
```

**Entregable Fase 4**: Módulo completo y funcional

---

## 🔗 Integración con DocumentoRepository

### **Herencia y Reutilización**
```python
# Reutilizar validaciones comunes
from ..documento.validation_mixin import DocumentoValidationMixin

class FacturaValidationMixin(DocumentoValidationMixin):
    """Extiende validaciones de documento con específicas de factura"""
    
    def validate_factura_data(self, data):
        # Primero validaciones base de documento
        super().validate_document_data(data)
        # Luego validaciones específicas de factura
        self._validate_factura_specific(data)
```

### **Utilidades Compartidas**
```python
# Reutilizar utilidades donde tenga sentido
from ..documento.utils import (
    normalize_cdc,
    format_amounts_for_display,
    calculate_percentage,
    build_date_filter,
    log_repository_operation
)

# Específicas de facturas
from .utils import (
    format_numero_factura,
    calculate_factura_totals,
    validate_timbrado_vigency
)
```

---

## ✅ Ventajas de Este Enfoque

### **🔧 Mantenibilidad**
- **Responsabilidad única**: Cada archivo tiene un propósito claro
- **Fácil testing**: Tests granulares por funcionalidad
- **Evolución independiente**: Cambiar numeración sin afectar estados
- **Code review granular**: Review por funcionalidad específica

### **🚀 Escalabilidad**
- **Composición flexible**: Agregar/quitar mixins según necesidad
- **Reutilización**: Aprovechar código de documento repository
- **Extensibilidad**: Fácil agregar nuevos mixins (ej: factura_export_mixin.py)
- **Performance**: Solo cargar funcionalidad necesaria

### **👥 Colaboración**
- **Desarrollo paralelo**: Diferentes devs en diferentes mixins
- **Merge conflicts mínimos**: Archivos separados
- **Especialización**: Devs pueden especializarse en áreas específicas
- **Onboarding**: Nuevos devs pueden empezar con un mixin específico

---

## 🎯 Uso Proyectado

### **Import Limpio**
```python
from app.repositories.factura import FacturaRepository

# Inicialización
factura_repo = FacturaRepository(db)

# Uso de diferentes funcionalidades
# === CRUD BÁSICO ===
factura = factura_repo.create(factura_data)
facturas = factura_repo.get_by_cliente(cliente_id=123)

# === NUMERACIÓN ===
numero = factura_repo.get_next_numero(establecimiento="001", punto="001")
factura_repo.validate_numeracion(numero)

# === ESTADOS ===
factura_repo.marcar_como_cobrada(factura_id=456)
pendientes = factura_repo.get_facturas_pendientes_cobro()

# === ESTADÍSTICAS ===
stats = factura_repo.get_facturacion_stats(empresa_id=1, mes=1, año=2025)
top_clients = factura_repo.get_top_clients(limit=10)
```

### **Autocomplete Completo**
El IDE mostrará todos los métodos organizados por funcionalidad:
- **Base**: CRUD básico y búsquedas
- **Numeración**: Gestión de secuencias y timbrados  
- **Estados**: Transiciones y consultas por estado
- **Validaciones**: Validaciones específicas de facturas
- **Stats**: Estadísticas y análisis específicos

---

## 📊 Cronograma Detallado

| Fase | Duración | Archivos | Funcionalidad | % Completitud |
|------|----------|----------|---------------|---------------|
| **Fase 1** | 2 días | `utils.py`, `base.py`, `__init__.py`, `README.md` | CRUD básico funcional | 40% |
| **Fase 2** | 2 días | `numeracion_mixin.py` | Numeración automática | 65% |
| **Fase 3** | 2 días | `estado_mixin.py` | Estados específicos | 85% |
| **Fase 4** | 2 días | `validation_mixin.py`, `stats_mixin.py` | Módulo completo | 100% |

**Total: 8 días de desarrollo para módulo completo**

---

## 🚀 Estado de Desarrollo

```
📊 Progreso Actual: 0% - Listo para comenzar Fase 1
📁 Archivos Planificados: 7
🎯 Objetivo: Repository completo y modular para facturas
⏱️ Tiempo Estimado: 8 días de desarrollo
```

---

## 🎯 Próximos Pasos

### **Inmediato (Hoy)**
1. Crear estructura de carpetas
2. Implementar `utils.py` con utilidades básicas
3. Implementar `base.py` con CRUD core

### **Esta Semana (Fase 1)**
1. Completar `__init__.py` básico
2. Documentar `README.md` del módulo
3. Tests básicos funcionando
4. Integración con API funcionando

### **Próximas 2 Semanas (Fases 2-4)**
1. Numeración automática (Fase 2)
2. Estados específicos (Fase 3)
3. Validaciones y estadísticas (Fase 4)
4. Testing completo e integración final

---

**🎯 Listo para comenzar Fase 1 - Fundación**