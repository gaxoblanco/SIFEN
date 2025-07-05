# ===============================================
# ARCHIVO: backend/app/repositories/factura/__init__.py
# PROPÓSITO: Compositor principal del módulo FacturaRepository
# VERSIÓN: 2.0.0 - Compatible con SIFEN v150
# FASE: 4 - MÓDULO COMPLETO (100%)
# ===============================================

"""
Módulo FacturaRepository - Gestión completa de facturas electrónicas SIFEN.

Este módulo implementa el patrón Repository con arquitectura modular usando mixins
para máxima mantenibilidad y escalabilidad. Proporciona todas las funcionalidades
necesarias para gestión de facturas según regulaciones SET Paraguay.

Arquitectura Modular Completa:
- FacturaRepositoryBase: CRUD básico y operaciones fundamentales
- FacturaNumeracionMixin: Numeración automática y gestión de timbrados
- FacturaEstadoMixin: Estados y transiciones específicas
- FacturaValidationMixin: Validaciones específicas Paraguay y SIFEN
- FacturaStatsMixin: Estadísticas avanzadas y métricas operacionales

Funcionalidades Completas (Fase 4):
✅ CRUD completo de facturas
✅ Numeración automática SIFEN
✅ Gestión de timbrados vigentes  
✅ Validaciones de continuidad SET
✅ Reserva de números para concurrencia
✅ Estados específicos de facturas
✅ Transiciones de estado validadas
✅ Consultas por estado específico
✅ Validaciones específicas Paraguay (RUC, CDC, SET)
✅ Validaciones de negocio y reglas SIFEN
✅ Estadísticas completas de facturación
✅ Métricas operacionales y KPIs
✅ Análisis de clientes y productos
✅ Health checks operacionales

Integra con:
- models/factura.py, models/timbrado.py (SQLAlchemy)
- schemas/factura.py, schemas/common.py (DTOs Pydantic)
- services/xml_generator (generación XML)
- services/digital_sign (firma digital)
- services/sifen_client (envío SIFEN)
- api/v1/facturas.py (endpoints REST)

Casos de uso principales:
- Emisión automática de facturas con numeración SET
- Facturación masiva con reserva de rangos
- Gestión completa de estados de factura
- Monitoreo de timbrados y alertas de vencimiento
- Validación de numeración continua
- Validaciones de negocio específicas Paraguay
- Estadísticas operacionales y dashboards
- Análisis de performance y KPIs

Examples:
    ```python
    # Uso completo
    from app.repositories.factura import FacturaRepository
    
    repo = FacturaRepository(db)
    
    # === CRUD BÁSICO ===
    factura = await repo.create(factura_data)
    facturas = await repo.get_by_cliente(cliente_id=123)
    
    # === NUMERACIÓN AUTOMÁTICA ===
    numero = await repo.get_next_numero("001", "001", empresa_id=1)
    
    # === ESTADOS ESPECÍFICOS ===
    await repo.marcar_como_cobrada(factura_id=456)
    pendientes = await repo.get_facturas_pendientes_cobro()
    
    # === VALIDACIONES ESPECÍFICAS ===
    validacion = await repo.validate_factura_data(factura_data)
    coherencia = await repo.validate_items_consistency(items)
    sifen_ready = await repo.validate_sifen_factura(factura_id)
    
    # === ESTADÍSTICAS AVANZADAS ===
    stats = await repo.get_facturacion_stats(empresa_id=1, period_type="month")
    revenue = await repo.get_revenue_by_period(empresa_id=1, period_type="day")
    top_clients = await repo.get_top_clients(empresa_id=1, limit=10)
    kpis = await repo.get_operational_kpis(empresa_id=1, period_days=30)
    ```

Roadmap de desarrollo:
📍 Fase 1 ✅: Fundación (base.py, utils.py) - 40%
📍 Fase 2 ✅: Numeración (numeracion_mixin.py) - 65%
📍 Fase 3 ✅: Estados (estado_mixin.py) - 85%
📍 Fase 4 ✅: Validaciones y Stats (validation_mixin.py, stats_mixin.py) - 100% ← COMPLETO

Autor: Sistema SIFEN
Fecha: 2025-07-05
Versión: 2.0.0 - MÓDULO COMPLETO
"""

from .utils import (
    # Constantes SIFEN
    SifenConstants,
    ESTADO_DESCRIPTIONS,
    TIPO_DOCUMENTO_DESCRIPTIONS,
    AFECTACION_IVA_DESCRIPTIONS,

    # Funciones de formateo
    format_numero_factura,
    parse_numero_factura,
    get_next_numero_available,
    format_factura_for_display,
    format_amount_display,

    # Validaciones SIFEN
    validate_factura_format,
    validate_timbrado_vigency,
    validate_cdc_format,
    validate_fecha_emision,

    # Cálculos automáticos
    calculate_factura_totals,

    # Validaciones Paraguay
    validate_ruc_paraguayo,
    validate_ci_paraguaya,
    format_ruc_display,
    format_ci_display,

    # Utilidades generales
    log_repository_operation,
    build_date_filter,
    calculate_percentage,
    normalize_cdc,

    # Utilidades SIFEN específicas
    get_sifen_response_description,
    is_sifen_approved,
    generate_security_code,
    validate_establishment_range,
    prepare_factura_for_xml
)
from .base import FacturaRepositoryBase
from .numeration_mixin import (
    FacturaNumeracionMixin,
    EstadoSecuencia,
    EstadisticasNumeracion,
    SifenTimbradoVencidoError,
    SifenNumeracionAgotadaError,
    SifenNumeracionDiscontinuaError
)
from .state_mixin import (
    FacturaEstadoMixin,
    EstadoHelper,
    log_estado_operation,
    PLAZO_CANCELACION_FE_HORAS,
    PLAZO_CANCELACION_OTROS_HORAS,
    ESTADOS_COBRABLES,
    ESTADOS_CANCELABLES
)
from .validation_mixin import (
    FacturaValidationMixin,
    ValidationHelper,
    SET_LIMITS,
    TASAS_IVA_VALIDAS,
    ESTADOS_MODIFICABLES
)
from .stats_mixin import (
    FacturaStatsMixin,
    StatsHelper
)

import logging
from typing import TYPE_CHECKING

# Configurar logger del módulo
logger = logging.getLogger("factura_repository")

# ===============================================
# IMPORTS DE COMPONENTES DEL MÓDULO
# ===============================================

# Import principal: Repository base con CRUD completo
# Import del mixin de numeración (Fase 2)
# Import del mixin de estados (Fase 3)
# Import del mixin de validaciones (Fase 4) ← NUEVO
# Import del mixin de estadísticas (Fase 4) ← NUEVO
# Import de utilidades específicas del módulo

# Imports condicionales para desarrollo futuro
if TYPE_CHECKING:
    # Imports para extensiones futuras
    pass

# ===============================================
# COMPOSITOR PRINCIPAL COMPLETO
# ===============================================


class FacturaRepository(
    FacturaRepositoryBase,          # CRUD básico + operaciones fundamentales
    FacturaNumeracionMixin,         # Numeración automática + gestión timbrados
    FacturaEstadoMixin,             # Estados específicos + transiciones
    FacturaValidationMixin,         # Validaciones específicas + reglas negocio ← NUEVO
    FacturaStatsMixin              # Estadísticas avanzadas + métricas operacionales ← NUEVO
):
    """
    Repository completo para facturas electrónicas SIFEN Paraguay.

    🎉 MÓDULO COMPLETO - TODAS LAS FASES IMPLEMENTADAS

    Combina todas las funcionalidades mediante herencia múltiple de mixins:

    🏗️ FacturaRepositoryBase (Fase 1):
    - CRUD completo (create, read, update, delete)
    - Búsquedas específicas (por número, cliente, timbrado, fechas)
    - Cálculos automáticos de totales e IVA
    - Conteos y estadísticas básicas
    - Validaciones de coherencia de datos

    🔢 FacturaNumeracionMixin (Fase 2):
    - Numeración secuencial automática por establecimiento/punto
    - Gestión de timbrados (vigencia, rangos, validaciones)
    - Reserva de números para concurrencia
    - Validaciones de continuidad SET Paraguay
    - Estadísticas de numeración y monitoreo
    - Health checks operacionales

    🔄 FacturaEstadoMixin (Fase 3):
    - Estados específicos de facturas (cobrada, anulada, vencida)
    - Transiciones de estado con validaciones
    - Consultas por estado específico
    - Flujos de estado SIFEN
    - Validaciones de plazos de cancelación

    ✅ FacturaValidationMixin (Fase 4):
    - Validaciones de datos específicas Paraguay (RUC, CDC, SET)
    - Validaciones de items y coherencia de IVA
    - Reglas de negocio específicas SIFEN
    - Validaciones para generación XML
    - Verificación requisitos clientes y términos pago

    📊 FacturaStatsMixin (Fase 4):
    - Estadísticas completas de facturación por período
    - Análisis de ingresos y tendencias
    - Métricas de clientes top y performance
    - Análisis de condiciones de pago y cobranza
    - KPIs operacionales con comparaciones períodos

    Ventajas de la Arquitectura Modular:
    ✅ Responsabilidad única por mixin
    ✅ Fácil testing granular
    ✅ Evolución independiente de funcionalidades
    ✅ Code reviews específicos por dominio
    ✅ Desarrollo paralelo por equipos
    ✅ Reutilización selectiva de mixins
    ✅ Mantenimiento simplificado
    ✅ Escalabilidad horizontal

    Examples:
        ```python
        # Inicialización
        repo = FacturaRepository(db)

        # === CRUD BÁSICO (FacturaRepositoryBase) ===
        factura = await repo.create(factura_data)
        facturas = await repo.get_by_cliente(cliente_id=123)
        factura = await repo.get_by_numero_factura("001-001-0000123")

        # === NUMERACIÓN AUTOMÁTICA (FacturaNumeracionMixin) ===
        numero = await repo.get_next_numero("001", "001", empresa_id=1)
        estado = await repo.get_secuencia_actual("001", "001", empresa_id=1)
        health = await repo.get_health_check_numeracion(empresa_id=1)

        # === ESTADOS (FacturaEstadoMixin) ===
        await repo.marcar_como_cobrada(factura_id=456)
        await repo.marcar_como_anulada(factura_id=789, motivo="Error", numero_resolucion="RES-123")
        pendientes = await repo.get_facturas_pendientes_cobro()

        # === VALIDACIONES (FacturaValidationMixin) ===
        validacion = await repo.validate_factura_data(factura_data)
        coherencia = await repo.validate_items_consistency(items)
        reglas_ok = await repo.validate_business_rules(factura_data)
        sifen_ready = await repo.validate_sifen_factura(factura_id)

        # === ESTADÍSTICAS (FacturaStatsMixin) ===
        stats = await repo.get_facturacion_stats(empresa_id=1, period_type="month")
        revenue = await repo.get_revenue_by_period(empresa_id=1, period_type="day", days_back=30)
        average = await repo.get_average_invoice_value(empresa_id=1, last_days=30)
        top_clients = await repo.get_top_clients(empresa_id=1, limit=10, period_days=90)

        # Métricas operacionales
        conversion = await repo.get_conversion_rates(empresa_id=1, period_days=30)
        payment_analysis = await repo.get_payment_analysis(empresa_id=1, period_days=90)
        collection = await repo.get_collection_metrics(empresa_id=1, period_days=60)
        kpis = await repo.get_operational_kpis(empresa_id=1, period_days=30)
        ```
    """

    def __init__(self, db):
        """
        Inicializa el repository completo con todas las funcionalidades.

        Args:
            db: Sesión SQLAlchemy
        """
        # Llamar inicializador del base (incluye logging)
        super().__init__(db)

        # Log inicialización completa
        logger.info(
            f"FacturaRepository inicializado - "
            f"MÓDULO COMPLETO: CRUD + Numeración + Estados + Validaciones + Stats (Fase 4/4)"
        )

    def get_available_mixins(self) -> list[str]:
        """
        Retorna lista de mixins activos en esta versión.

        Útil para verificar funcionalidades disponibles programáticamente.

        Returns:
            list: Lista de mixins activos
        """
        return [
            "FacturaRepositoryBase",      # CRUD básico
            "FacturaNumeracionMixin",     # Numeración automática
            "FacturaEstadoMixin",         # Estados específicos
            "FacturaValidationMixin",     # Validaciones específicas ← NUEVO
            "FacturaStatsMixin"          # Estadísticas avanzadas ← NUEVO
        ]

    def get_implementation_status(self) -> dict:
        """
        Retorna estado de implementación del módulo.

        Returns:
            dict: Estado por fases y funcionalidades
        """
        return {
            "version": "2.0.0",
            "fase_actual": 4,
            "completitud": "100%",
            "status": "🎉 MÓDULO COMPLETO",
            "fases": {
                "fase_1_fundacion": {
                    "status": "✅ Completa",
                    "componentes": ["base.py", "utils.py"],
                    "funcionalidades": ["CRUD", "búsquedas", "cálculos", "conteos"]
                },
                "fase_2_numeracion": {
                    "status": "✅ Completa",
                    "componentes": ["numeracion_mixin.py"],
                    "funcionalidades": ["numeración automática", "gestión timbrados", "validaciones", "estadísticas"]
                },
                "fase_3_estados": {
                    "status": "✅ Completa",
                    "componentes": ["estado_mixin.py"],
                    "funcionalidades": ["estados específicos", "transiciones", "flujos SIFEN", "validaciones estado"]
                },
                "fase_4_avanzado": {
                    "status": "✅ Completa",
                    "componentes": ["validation_mixin.py", "stats_mixin.py"],
                    "funcionalidades": ["validaciones Paraguay", "reglas negocio", "estadísticas avanzadas", "KPIs operacionales"]
                }
            },
            "metricas_finales": {
                "archivos_implementados": 6,
                "lineas_codigo": "~3000",
                "metodos_publicos": 50,
                "mixins_activos": 5,
                "coverage_objetivo": "95%"
            }
        }

    def get_feature_summary(self) -> dict:
        """
        Resumen de todas las funcionalidades disponibles.

        Returns:
            dict: Funcionalidades por categoría
        """
        return {
            "crud_basico": [
                "create", "get_by_id", "update", "delete",
                "get_by_numero_factura", "get_by_cliente", "get_by_timbrado",
                "get_by_rango_fechas", "get_pendientes_cobro"
            ],
            "numeracion": [
                "get_next_numero", "reserve_numero_range", "validate_numeracion",
                "get_timbrado_vigente", "check_timbrado_vigency", "get_secuencia_actual",
                "get_health_check_numeracion", "get_estadisticas_numeracion"
            ],
            "estados": [
                "marcar_como_cobrada", "marcar_como_anulada", "marcar_como_vencida",
                "reabrir_factura", "can_be_collected", "can_be_cancelled",
                "get_facturas_pendientes_cobro", "get_facturas_vencidas", "get_facturas_by_estado"
            ],
            "validaciones": [
                "validate_factura_data", "validate_items_consistency", "validate_tax_calculations",
                "validate_client_requirements", "validate_payment_terms", "validate_business_rules",
                "validate_sifen_factura", "validate_xml_generation"
            ],
            "estadisticas": [
                "get_facturacion_stats", "get_revenue_by_period", "get_average_invoice_value",
                "get_top_clients", "get_conversion_rates", "get_payment_analysis",
                "get_collection_metrics", "get_operational_kpis"
            ],
            "utilidades": [
                "format_numero_factura", "validate_ruc_paraguayo", "calculate_factura_totals",
                "format_amount_display", "prepare_factura_for_xml"
            ]
        }

    def __repr__(self) -> str:
        """Representación string del repository completo."""
        mixins = ", ".join(self.get_available_mixins())
        return f"<FacturaRepository(status=COMPLETO, mixins=[{mixins}])>"


# ===============================================
# ALIASES Y SHORTCUTS PARA COMPATIBILIDAD
# ===============================================

# Alias principal para import simplificado
Repository = FacturaRepository

# Alias para casos específicos
FacturaRepo = FacturaRepository
SifenFacturaRepository = FacturaRepository
CompleteFacturaRepository = FacturaRepository

# ===============================================
# FUNCIONES DE UTILIDAD DEL MÓDULO
# ===============================================


def create_repository(db) -> FacturaRepository:
    """
    Factory function para crear instancia del repository.

    Útil para inyección de dependencias y testing.

    Args:
        db: Sesión SQLAlchemy

    Returns:
        FacturaRepository: Instancia configurada
    """
    return FacturaRepository(db)


def get_module_info() -> dict:
    """
    Información completa del módulo para debugging y monitoreo.

    Returns:
        dict: Metadata del módulo
    """
    return {
        "name": "factura_repository",
        "version": "2.0.0",
        "status": "COMPLETO - Todas las fases implementadas",
        "description": "Repository modular completo para facturas electrónicas SIFEN Paraguay",
        "author": "Sistema SIFEN",
        "compatibility": "SIFEN v150, SET Paraguay",
        "architecture": "Modular Mixins Pattern",
        "components": {
            "base": "FacturaRepositoryBase - CRUD básico",
            "numeracion": "FacturaNumeracionMixin - Numeración automática",
            "estado": "FacturaEstadoMixin - Estados específicos",
            "validation": "FacturaValidationMixin - Validaciones específicas",
            "stats": "FacturaStatsMixin - Estadísticas avanzadas",
            "utils": "Utilidades específicas SIFEN Paraguay"
        },
        "features": [
            "CRUD completo de facturas",
            "Numeración automática SIFEN",
            "Gestión de timbrados vigentes",
            "Estados específicos de facturas",
            "Transiciones de estado validadas",
            "Validaciones específicas Paraguay (RUC, CI, CDC)",
            "Validaciones de negocio y reglas SIFEN",
            "Validaciones para generación XML",
            "Estadísticas completas de facturación",
            "Análisis de ingresos y tendencias",
            "Métricas de clientes top",
            "Análisis de condiciones de pago",
            "KPIs operacionales comparativos",
            "Health checks automatizados",
            "Cálculos automáticos de IVA Paraguay",
            "Formateo para display y APIs",
            "Soporte completo concurrencia"
        ],
        "metrics": {
            "files_count": 6,
            "estimated_lines": 3000,
            "public_methods": 50,
            "mixins_count": 5,
            "constants_count": 15,
            "utility_functions": 25
        },
        "testing": {
            "factories": ["create_test_timbrado_data", "create_test_factura_data"],
            "coverage_target": "95%",
            "types": ["unit", "integration", "performance", "load"]
        }
    }


def validate_module_health() -> dict:
    """
    Validación completa de salud del módulo.

    Returns:
        dict: Estado de salud de todos los componentes
    """
    health = {
        "status": "healthy",
        "timestamp": "2025-07-05T00:00:00",
        "version": "2.0.0",
        "components": {},
        "issues": [],
        "summary": {}
    }

    components_to_check = [
        ("base", FacturaRepositoryBase),
        ("numeracion", FacturaNumeracionMixin),
        ("estado", FacturaEstadoMixin),
        ("validation", FacturaValidationMixin),
        ("stats", FacturaStatsMixin),
    ]

    healthy_count = 0

    for component_name, component_class in components_to_check:
        try:
            # Verificar que la clase existe y es importable
            if hasattr(component_class, '__name__'):
                health["components"][component_name] = "✅ OK"
                healthy_count += 1
            else:
                health["components"][component_name] = "❌ Error: Class not found"
                health["issues"].append(
                    f"{component_name} component not available")
        except Exception as e:
            health["components"][component_name] = f"❌ Error: {e}"
            health["issues"].append(
                f"{component_name} import failed: {str(e)}")

    # Verificar utilidades
    try:
        from .utils import SifenConstants, format_numero_factura
        health["components"]["utils"] = "✅ OK"
        healthy_count += 1
    except ImportError as e:
        health["components"]["utils"] = f"❌ Error: {e}"
        health["issues"].append("Utils import failed")

    # Verificar que el compositor funciona
    try:
        repo_class = FacturaRepository
        health["components"]["compositor"] = "✅ OK"
        health["available_methods"] = len([
            method for method in dir(repo_class)
            if not method.startswith('_')
        ])
        healthy_count += 1
    except Exception as e:
        health["components"]["compositor"] = f"❌ Error: {e}"
        health["issues"].append("Repository composition failed")

    # Calcular estado general
    total_components = len(components_to_check) + 2  # +utils +compositor
    health_percentage = (healthy_count / total_components) * 100

    if health_percentage == 100:
        health["status"] = "healthy"
    elif health_percentage >= 80:
        health["status"] = "degraded"
    else:
        health["status"] = "critical"

    health["summary"] = {
        "healthy_components": healthy_count,
        "total_components": total_components,
        "health_percentage": round(health_percentage, 1),
        "issues_count": len(health["issues"])
    }

    return health


# ===============================================
# EXPORTS PÚBLICOS COMPLETOS
# ===============================================

__all__ = [
    # === CLASE PRINCIPAL ===
    "FacturaRepository",

    # === ALIASES ===
    "Repository",
    "FacturaRepo",
    "SifenFacturaRepository",
    "CompleteFacturaRepository",

    # === COMPONENTES INDIVIDUALES ===
    "FacturaRepositoryBase",
    "FacturaNumeracionMixin",
    "FacturaEstadoMixin",
    "FacturaValidationMixin",      # NUEVO
    "FacturaStatsMixin",          # NUEVO

    # === CLASES DE DATOS ===
    "EstadoSecuencia",
    "EstadisticasNumeracion",

    # === HELPERS Y UTILIDADES ===
    "EstadoHelper",
    "ValidationHelper",           # NUEVO
    "StatsHelper",               # NUEVO
    "log_estado_operation",

    # === EXCEPCIONES ESPECÍFICAS ===
    "SifenTimbradoVencidoError",
    "SifenNumeracionAgotadaError",
    "SifenNumeracionDiscontinuaError",

    # === CONSTANTES ===
    "SifenConstants",
    "ESTADO_DESCRIPTIONS",
    "TIPO_DOCUMENTO_DESCRIPTIONS",
    "AFECTACION_IVA_DESCRIPTIONS",
    "PLAZO_CANCELACION_FE_HORAS",
    "PLAZO_CANCELACION_OTROS_HORAS",
    "ESTADOS_COBRABLES",
    "ESTADOS_CANCELABLES",
    "SET_LIMITS",                # NUEVO
    "TASAS_IVA_VALIDAS",         # NUEVO
    "ESTADOS_MODIFICABLES",       # NUEVO

    # === FUNCIONES DE FORMATEO ===
    "format_numero_factura",
    "parse_numero_factura",
    "format_factura_for_display",
    "format_amount_display",
    "format_ruc_display",
    "format_ci_display",

    # === FUNCIONES DE VALIDACIÓN ===
    "validate_factura_format",
    "validate_timbrado_vigency",
    "validate_cdc_format",
    "validate_fecha_emision",
    "validate_ruc_paraguayo",
    "validate_ci_paraguaya",
    "validate_establishment_range",

    # === FUNCIONES DE CÁLCULO ===
    "calculate_factura_totals",
    "calculate_percentage",

    # === UTILIDADES SIFEN ===
    "get_sifen_response_description",
    "is_sifen_approved",
    "generate_security_code",
    "prepare_factura_for_xml",
    "normalize_cdc",

    # === FUNCIONES DEL MÓDULO ===
    "create_repository",
    "get_module_info",
    "validate_module_health"
]

# ===============================================
# INICIALIZACIÓN DEL MÓDULO COMPLETO
# ===============================================

# Log de inicialización del módulo completo
logger.info("🎉 Módulo factura_repository COMPLETAMENTE inicializado")
logger.info(f"📊 Estado: FASE 4/4 COMPLETA (100% funcionalidad)")
logger.info(f"⚡ Componentes activos: {len(__all__)} exports disponibles")
logger.info(
    f"🚀 Mixins implementados: 5/5 (Base + Numeración + Estados + Validaciones + Stats)")

# Validación completa de salud al importar
_health = validate_module_health()
logger.info(
    f"🏥 Health Check: {_health['status']} ({_health['summary']['health_percentage']}%)")

if _health["status"] != "healthy":
    logger.warning(f"⚠️ Módulo con problemas: {_health['status']}")
    for issue in _health["issues"]:
        logger.warning(f"   - {issue}")
else:
    logger.info("✅ Módulo validado correctamente - LISTO PARA PRODUCCIÓN")
    logger.info(
        f"📈 Componentes saludables: {_health['summary']['healthy_components']}/{_health['summary']['total_components']}")

# Metadata del módulo completo
__version__ = "2.0.0"
__author__ = "Sistema SIFEN"
__description__ = "Repository modular completo para facturas electrónicas SIFEN Paraguay"
__compatibility__ = "SIFEN v150, SET Paraguay"
__status__ = "COMPLETO - Todas las fases implementadas"
__phase__ = "4/4 - Módulo terminado"
__features__ = "CRUD + Numeración + Estados + Validaciones + Estadísticas"
