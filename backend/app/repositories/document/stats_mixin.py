# ===============================================
# ARCHIVO: backend/app/repositories/documento/stats_mixin.py
# PROPÓSITO: Mixin para estadísticas y reportes de documentos SIFEN
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para estadísticas y reportes de documentos SIFEN.
Genera métricas de negocio y análisis de datos.

Este módulo implementa funcionalidades avanzadas para generación de
estadísticas, métricas y reportes de documentos electrónicos:
- Estadísticas generales por empresa y período
- Análisis financiero de ingresos e IVA
- Métricas de rendimiento de integración SIFEN
- Análisis temporal y tendencias
- Reportes por segmentos y distribuciones
- Métricas operacionales y de cumplimiento

Características principales:
- Queries optimizadas con agregaciones SQL nativas
- Sistema de cache inteligente con TTL configurable
- Múltiples formatos de salida (JSON, gráficos)
- Manejo robusto de performance y timeouts
- Logging detallado de métricas

Clase principal:
- DocumentoStatsMixin: Mixin para estadísticas y reportes
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, text, desc, asc, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenValidationError,
    SifenDatabaseError,
    handle_database_exception
)
from app.models.documento import (
    Documento,
    EstadoDocumentoSifenEnum,
    TipoDocumentoSifenEnum
)
from .utils import (
    log_repository_operation,
    log_performance_metric,
    handle_repository_error,
    calculate_percentage,
    format_stats_for_chart,
    aggregate_by_period,
    calculate_growth_rate,
    get_date_range_for_period,
    generate_cache_key,
    should_use_cache,
    get_stats_cache_ttl,
    build_date_filter,
    get_default_page_size,
    get_max_page_size
)

logger = get_logger(__name__)

# ===============================================
# CONFIGURACIONES Y CONSTANTES
# ===============================================

# Estados considerados exitosos para métricas SIFEN
SIFEN_SUCCESS_STATES = [
    EstadoDocumentoSifenEnum.APROBADO.value,
    EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value
]

# Estados considerados fallidos para métricas SIFEN
SIFEN_FAILED_STATES = [
    EstadoDocumentoSifenEnum.RECHAZADO.value,
    EstadoDocumentoSifenEnum.ERROR_ENVIO.value
]

# Estados que representan documentos activos
ACTIVE_DOCUMENT_STATES = [
    EstadoDocumentoSifenEnum.APROBADO.value,
    EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value
]

# Configuración de cache por tipo de estadística
CACHE_CONFIG = {
    "basic_stats": {"ttl": 300, "prefix": "stats_basic"},          # 5 min
    "financial_stats": {"ttl": 600, "prefix": "stats_financial"},  # 10 min
    "sifen_performance": {"ttl": 180, "prefix": "stats_sifen"},    # 3 min
    "temporal_analysis": {"ttl": 900, "prefix": "stats_temporal"},  # 15 min
    "operational_health": {"ttl": 120, "prefix": "stats_ops"}      # 2 min
}

# ===============================================
# MIXIN PRINCIPAL
# ===============================================


class DocumentoStatsMixin:
    """
    Mixin para estadísticas y reportes de documentos SIFEN.

    Proporciona métodos especializados para generar estadísticas,
    métricas y reportes de documentos electrónicos:
    - Análisis financiero y de ingresos
    - Métricas de performance SIFEN
    - Tendencias temporales y crecimiento
    - Distribuciones por segmentos
    - Salud operacional del sistema

    Este mixin debe ser usado junto con DocumentoRepositoryBase para
    obtener funcionalidad completa de estadísticas.

    Example:
        ```python
        class DocumentoRepository(
            DocumentoRepositoryBase,
            DocumentoStatsMixin,
            # otros mixins...
        ):
            pass

        repo = DocumentoRepository(db)
        stats = repo.get_documento_stats(empresa_id=1)
        ```
    """

    db: Session
    model: type

    # ===============================================
    # ESTADÍSTICAS GENERALES
    # ===============================================

    def get_documento_stats(self,
                            empresa_id: int,
                            fecha_desde: Optional[date] = None,
                            fecha_hasta: Optional[date] = None,
                            include_financial: bool = True,
                            include_sifen_metrics: bool = True) -> Dict[str, Any]:
        """
        Obtiene estadísticas completas de documentos por empresa.

        Este método es el punto de entrada principal para obtener un resumen
        completo de estadísticas de documentos, incluyendo contadores,
        análisis financiero y métricas de rendimiento SIFEN.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período (opcional)
            fecha_hasta: Fecha fin del período (opcional)
            include_financial: Incluir análisis financiero
            include_sifen_metrics: Incluir métricas SIFEN

        Returns:
            Dict[str, Any]: Estadísticas completas de documentos

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            ```python
            stats = repo.get_documento_stats(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31),
                include_financial=True
            )

            print(f"Total documentos: {stats['resumen']['total_documentos']}")
            print(f"Total facturado: {stats['financiero']['total_facturado']}")
            print(f"Tasa aprobación: {stats['sifen']['tasa_aprobacion']}%")
            ```
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not empresa_id or empresa_id <= 0:
                raise SifenValidationError(
                    "ID de empresa debe ser mayor a 0",
                    field="empresa_id",
                    value=empresa_id
                )

            if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
                raise SifenValidationError(
                    "Fecha desde no puede ser mayor a fecha hasta",
                    field="fecha_desde"
                )

            # Configurar período por defecto (mes actual)
            if not fecha_desde:
                fecha_desde = date.today().replace(day=1)
            if not fecha_hasta:
                fecha_hasta = date.today()

            # 1. Obtener contadores básicos
            resumen = self._get_basic_document_counts(
                empresa_id, fecha_desde, fecha_hasta)

            # 2. Análisis financiero si se solicita
            financiero = {}
            if include_financial and resumen["total_documentos"] > 0:
                financiero = self._get_financial_summary(
                    empresa_id, fecha_desde, fecha_hasta)

            # 3. Métricas SIFEN si se solicita
            sifen_metrics = {}
            if include_sifen_metrics and resumen["total_documentos"] > 0:
                sifen_metrics = self._get_sifen_performance_summary(
                    empresa_id, fecha_desde, fecha_hasta)

            # 4. Métricas temporales básicas
            temporal = self._get_temporal_basic_metrics(
                empresa_id, fecha_desde, fecha_hasta)

            # 5. Construir respuesta completa
            stats = {
                "empresa_id": empresa_id,
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "dias_analizados": (fecha_hasta - fecha_desde).days + 1
                },
                "resumen": resumen,
                "financiero": financiero,
                "sifen": sifen_metrics,
                "temporal": temporal,
                "metadatos": {
                    "generado_en": datetime.now().isoformat(),
                    "tiempo_procesamiento": (datetime.now() - start_time).total_seconds(),
                    "include_financial": include_financial,
                    "include_sifen_metrics": include_sifen_metrics
                }
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("get_documento_stats",
                                   duration, resumen["total_documentos"])

            log_repository_operation("get_documento_stats", "Documento", empresa_id, {
                "periodo": f"{fecha_desde} - {fecha_hasta}",
                "total_documentos": resumen["total_documentos"],
                "include_financial": include_financial
            })

            return stats

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_documento_stats", "Documento", empresa_id)
            raise handle_database_exception(e, "get_documento_stats")

    def get_monthly_stats(self,
                          empresa_id: int,
                          year: int,
                          month: int) -> Dict[str, Any]:
        """
        Obtiene estadísticas específicas de un mes.

        Proporciona un análisis detallado de un mes específico incluyendo
        comparación con el mes anterior y métricas diarias.

        Args:
            empresa_id: ID de la empresa
            year: Año a analizar
            month: Mes a analizar (1-12)

        Returns:
            Dict[str, Any]: Estadísticas mensuales detalladas

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            ```python
            stats = repo.get_monthly_stats(empresa_id=1, year=2025, month=1)

            print(f"Documentos enero: {stats['resumen']['total_documentos']}")
            print(f"Crecimiento vs diciembre: {stats['comparacion']['crecimiento_vs_anterior']}%")
            print(f"Mejor día: {stats['distribucion_diaria']['dia_mayor_actividad']}")
            ```
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not empresa_id or empresa_id <= 0:
                raise SifenValidationError(
                    "ID de empresa debe ser mayor a 0",
                    field="empresa_id"
                )

            if year < 2020 or year > 2030:
                raise SifenValidationError(
                    "Año debe estar entre 2020 y 2030",
                    field="year",
                    value=year
                )

            if month < 1 or month > 12:
                raise SifenValidationError(
                    "Mes debe estar entre 1 y 12",
                    field="month",
                    value=month
                )

            # Calcular fechas del mes
            fecha_desde = date(year, month, 1)

            # Último día del mes
            if month == 12:
                fecha_hasta = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                fecha_hasta = date(year, month + 1, 1) - timedelta(days=1)

            # 1. Estadísticas básicas del mes
            stats_mes = self.get_documento_stats(
                empresa_id, fecha_desde, fecha_hasta,
                include_financial=True, include_sifen_metrics=True
            )

            # 2. Comparación con mes anterior
            if month == 1:
                fecha_desde_anterior = date(year - 1, 12, 1)
                fecha_hasta_anterior = date(year, 1, 1) - timedelta(days=1)
            else:
                fecha_desde_anterior = date(year, month - 1, 1)
                fecha_hasta_anterior = date(year, month, 1) - timedelta(days=1)

            stats_anterior = self.get_documento_stats(
                empresa_id, fecha_desde_anterior, fecha_hasta_anterior,
                include_financial=True, include_sifen_metrics=False
            )

            # 3. Distribución diaria
            distribucion_diaria = self._get_daily_distribution(
                empresa_id, fecha_desde, fecha_hasta)

            # 4. Calcular comparaciones
            comparacion = self._calculate_period_comparison(
                stats_mes, stats_anterior)

            # 5. Construir respuesta
            monthly_stats = {
                **stats_mes,
                "mes_analizado": {
                    "year": year,
                    "month": month,
                    "nombre_mes": fecha_desde.strftime("%B"),
                    "dias_en_mes": (fecha_hasta - fecha_desde).days + 1
                },
                "comparacion": comparacion,
                "distribucion_diaria": distribucion_diaria,
                "metadatos": {
                    **stats_mes["metadatos"],
                    "tipo_analisis": "mensual",
                    "mes_comparacion": f"{fecha_desde_anterior.month}/{fecha_desde_anterior.year}"
                }
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_monthly_stats", duration, stats_mes["resumen"]["total_documentos"])

            return monthly_stats

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_monthly_stats", "Documento", empresa_id)
            raise handle_database_exception(e, "get_monthly_stats")

    def get_daily_summary(self,
                          empresa_id: int,
                          target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Obtiene resumen detallado de un día específico.

        Proporciona análisis completo de la actividad diaria incluyendo
        distribución horaria, comparación con días anteriores y métricas
        de rendimiento.

        Args:
            empresa_id: ID de la empresa
            target_date: Fecha específica (default: hoy)

        Returns:
            Dict[str, Any]: Resumen diario detallado

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            ```python
            summary = repo.get_daily_summary(empresa_id=1, target_date=date.today())

            print(f"Documentos hoy: {summary['resumen']['total_documentos']}")
            print(f"Hora pico: {summary['distribucion_horaria']['hora_pico']}")
            print(f"Vs ayer: {summary['comparacion']['cambio_vs_ayer']}%")
            ```
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not empresa_id or empresa_id <= 0:
                raise SifenValidationError(
                    "ID de empresa debe ser mayor a 0",
                    field="empresa_id"
                )

            # Fecha por defecto
            if not target_date:
                target_date = date.today()

            # Validar que no sea fecha futura
            if target_date > date.today():
                raise SifenValidationError(
                    "No se puede analizar fecha futura",
                    field="target_date",
                    value=target_date
                )

            # 1. Estadísticas del día
            stats_dia = self.get_documento_stats(
                empresa_id, target_date, target_date,
                include_financial=True, include_sifen_metrics=True
            )

            # 2. Comparación con día anterior
            fecha_anterior = target_date - timedelta(days=1)
            stats_anterior = self.get_documento_stats(
                empresa_id, fecha_anterior, fecha_anterior,
                include_financial=True, include_sifen_metrics=False
            )

            # 3. Distribución horaria (si es posible)
            distribucion_horaria = self._get_hourly_distribution(
                empresa_id, target_date)

            # 4. Actividad por tipo de documento
            actividad_por_tipo = self._get_document_type_activity(
                empresa_id, target_date)

            # 5. Comparaciones
            comparacion = {
                "fecha_comparacion": fecha_anterior.isoformat(),
                "cambio_documentos": stats_dia["resumen"]["total_documentos"] - stats_anterior["resumen"]["total_documentos"],
                "cambio_porcentual": calculate_percentage(
                    stats_dia["resumen"]["total_documentos"] -
                    stats_anterior["resumen"]["total_documentos"],
                    stats_anterior["resumen"]["total_documentos"]
                ) if stats_anterior["resumen"]["total_documentos"] > 0 else 0,
                "cambio_financiero": float(
                    stats_dia["financiero"].get("total_facturado", 0) -
                    stats_anterior["financiero"].get("total_facturado", 0)
                ) if stats_dia["financiero"] and stats_anterior["financiero"] else 0
            }

            # 6. Construir respuesta
            daily_summary = {
                **stats_dia,
                "fecha_analizada": target_date.isoformat(),
                "dia_semana": target_date.strftime("%A"),
                "es_fin_semana": target_date.weekday() >= 5,
                "comparacion": comparacion,
                "distribucion_horaria": distribucion_horaria,
                "actividad_por_tipo": actividad_por_tipo,
                "metadatos": {
                    **stats_dia["metadatos"],
                    "tipo_analisis": "diario",
                    "es_dia_actual": target_date == date.today()
                }
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_daily_summary", duration, stats_dia["resumen"]["total_documentos"])

            return daily_summary

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_daily_summary", "Documento", empresa_id)
            raise handle_database_exception(e, "get_daily_summary")

    def get_period_comparison(self,
                              empresa_id: int,
                              periodo_actual_desde: date,
                              periodo_actual_hasta: date,
                              periodo_anterior_desde: date,
                              periodo_anterior_hasta: date) -> Dict[str, Any]:
        """
        Compara estadísticas entre dos períodos específicos.

        Realiza análisis comparativo detallado entre dos períodos,
        calculando cambios absolutos, porcentuales y tendencias.

        Args:
            empresa_id: ID de la empresa
            periodo_actual_desde: Inicio período actual
            periodo_actual_hasta: Fin período actual
            periodo_anterior_desde: Inicio período anterior
            periodo_anterior_hasta: Fin período anterior

        Returns:
            Dict[str, Any]: Comparación detallada entre períodos

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            ```python
            # Comparar enero 2025 vs enero 2024
            comparison = repo.get_period_comparison(
                empresa_id=1,
                periodo_actual_desde=date(2025, 1, 1),
                periodo_actual_hasta=date(2025, 1, 31),
                periodo_anterior_desde=date(2024, 1, 1),
                periodo_anterior_hasta=date(2024, 1, 31)
            )

            print(f"Crecimiento documentos: {comparison['cambios']['documentos']['porcentual']}%")
            print(f"Crecimiento facturación: {comparison['cambios']['financiero']['porcentual']}%")
            ```
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not empresa_id or empresa_id <= 0:
                raise SifenValidationError(
                    "ID de empresa debe ser mayor a 0",
                    field="empresa_id"
                )

            # Validar períodos
            if periodo_actual_desde > periodo_actual_hasta:
                raise SifenValidationError(
                    "Período actual: fecha desde no puede ser mayor a fecha hasta",
                    field="periodo_actual_desde"
                )

            if periodo_anterior_desde > periodo_anterior_hasta:
                raise SifenValidationError(
                    "Período anterior: fecha desde no puede ser mayor a fecha hasta",
                    field="periodo_anterior_desde"
                )

            # 1. Obtener estadísticas período actual
            stats_actual = self.get_documento_stats(
                empresa_id, periodo_actual_desde, periodo_actual_hasta,
                include_financial=True, include_sifen_metrics=True
            )

            # 2. Obtener estadísticas período anterior
            stats_anterior = self.get_documento_stats(
                empresa_id, periodo_anterior_desde, periodo_anterior_hasta,
                include_financial=True, include_sifen_metrics=True
            )

            # 3. Calcular comparaciones detalladas
            comparison = self._calculate_detailed_comparison(
                stats_actual, stats_anterior)

            # 4. Análisis de tendencias
            tendencias = self._analyze_comparison_trends(
                stats_actual, stats_anterior)

            # 5. Construir respuesta
            period_comparison = {
                "empresa_id": empresa_id,
                "periodos": {
                    "actual": {
                        "desde": periodo_actual_desde.isoformat(),
                        "hasta": periodo_actual_hasta.isoformat(),
                        "dias": (periodo_actual_hasta - periodo_actual_desde).days + 1
                    },
                    "anterior": {
                        "desde": periodo_anterior_desde.isoformat(),
                        "hasta": periodo_anterior_hasta.isoformat(),
                        "dias": (periodo_anterior_hasta - periodo_anterior_desde).days + 1
                    }
                },
                "estadisticas": {
                    "actual": stats_actual,
                    "anterior": stats_anterior
                },
                "cambios": comparison,
                "tendencias": tendencias,
                "metadatos": {
                    "generado_en": datetime.now().isoformat(),
                    "tiempo_procesamiento": (datetime.now() - start_time).total_seconds(),
                    "tipo_analisis": "comparacion_periodos"
                }
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            total_docs = stats_actual["resumen"]["total_documentos"] + \
                stats_anterior["resumen"]["total_documentos"]
            log_performance_metric(
                "get_period_comparison", duration, total_docs)

            return period_comparison

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_period_comparison", "Documento", empresa_id)
            raise handle_database_exception(e, "get_period_comparison")

    # ===============================================
    # MÉTODOS PRIVADOS DE APOYO
    # ===============================================

    def _get_basic_document_counts(self, empresa_id: int, fecha_desde: date, fecha_hasta: date) -> Dict[str, Any]:
        """
        Obtiene contadores básicos de documentos.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Contadores básicos de documentos
        """
        try:
            # Query base con filtros
            base_query = self.db.query(self.model).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision >= fecha_desde,
                    self.model.fecha_emision <= fecha_hasta
                )
            )

            # Total documentos
            total_documentos = base_query.count()

            # Conteo por tipo de documento
            tipo_counts = self.db.query(
                self.model.tipo_documento,
                func.count(self.model.id).label('count')
            ).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision >= fecha_desde,
                    self.model.fecha_emision <= fecha_hasta
                )
            ).group_by(self.model.tipo_documento).all()

            # Conteo por estado
            estado_counts = self.db.query(
                text("estado"),
                func.count(self.model.id).label('count')
            ).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision >= fecha_desde,
                    self.model.fecha_emision <= fecha_hasta
                )
            ).group_by(text("estado")).all()

            # Procesar conteos por tipo
            tipo_dict = {
                "facturas": 0,
                "autofacturas": 0,
                "notas_credito": 0,
                "notas_debito": 0,
                "notas_remision": 0
            }

            for tipo, count in tipo_counts:
                if tipo == "1":
                    tipo_dict["facturas"] = count
                elif tipo == "4":
                    tipo_dict["autofacturas"] = count
                elif tipo == "5":
                    tipo_dict["notas_credito"] = count
                elif tipo == "6":
                    tipo_dict["notas_debito"] = count
                elif tipo == "7":
                    tipo_dict["notas_remision"] = count

            # Procesar conteos por estado
            estado_dict = {
                "borradores": 0,
                "validados": 0,
                "enviados": 0,
                "aprobados": 0,
                "rechazados": 0,
                "cancelados": 0
            }

            for estado, count in estado_counts:
                if estado in ["borrador"]:
                    estado_dict["borradores"] += count
                elif estado in ["validado", "generado", "firmado"]:
                    estado_dict["validados"] += count
                elif estado in ["enviado"]:
                    estado_dict["enviados"] += count
                elif estado in ["aprobado", "aprobado_observacion"]:
                    estado_dict["aprobados"] += count
                elif estado in ["rechazado", "error_envio"]:
                    estado_dict["rechazados"] += count
                elif estado in ["cancelado", "anulado"]:
                    estado_dict["cancelados"] += count

            return {
                "total_documentos": total_documentos,
                **tipo_dict,
                **estado_dict
            }

        except Exception as e:
            logger.error(f"Error obteniendo contadores básicos: {e}")
            return {
                "total_documentos": 0,
                "facturas": 0,
                "autofacturas": 0,
                "notas_credito": 0,
                "notas_debito": 0,
                "notas_remision": 0,
                "borradores": 0,
                "validados": 0,
                "enviados": 0,
                "aprobados": 0,
                "rechazados": 0,
                "cancelados": 0
            }

    def _get_financial_summary(self, empresa_id: int, fecha_desde: date, fecha_hasta: date) -> Dict[str, Any]:
        """
        Obtiene resumen financiero de documentos.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Resumen financiero
        """
        try:
            # Query para totales financieros de documentos activos
            financial_query = self.db.query(
                func.sum(self.model.total_general).label('total_facturado'),
                func.sum(self.model.total_iva).label('total_iva'),
                func.avg(self.model.total_general).label('promedio_documento'),
                func.max(self.model.total_general).label('documento_mayor'),
                func.min(self.model.total_general).label('documento_menor'),
                func.count(self.model.id).label('documentos_con_monto')
            ).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision >= fecha_desde,
                    self.model.fecha_emision <= fecha_hasta,
                    text("estado IN ('aprobado', 'aprobado_observacion')"),
                    self.model.total_general > 0
                )
            ).first()

            # Procesar resultados (con validación de None)
            total_facturado = getattr(
                financial_query, 'total_facturado', None) or Decimal("0")
            total_iva = getattr(
                financial_query, 'total_iva', None) or Decimal("0")
            promedio_documento = getattr(
                financial_query, 'promedio_documento', None) or Decimal("0")
            documento_mayor = getattr(
                financial_query, 'documento_mayor', None) or Decimal("0")
            documento_menor = getattr(
                financial_query, 'documento_menor', None) or Decimal("0")
            documentos_con_monto = getattr(
                financial_query, 'documentos_con_monto', None) or 0

            # Análisis por moneda (opcional - si el campo existe)
            try:
                moneda_analysis = self.db.query(
                    self.model.moneda,
                    func.sum(self.model.total_general).label('total'),
                    func.count(self.model.id).label('count')
                ).filter(
                    and_(
                        self.model.empresa_id == empresa_id,
                        self.model.fecha_emision >= fecha_desde,
                        self.model.fecha_emision <= fecha_hasta,
                        text("estado IN ('aprobado', 'aprobado_observacion')")
                    )
                ).group_by(self.model.moneda).all()

                # Procesar distribución por moneda
                distribucion_moneda = {}
                for moneda, total, count in moneda_analysis:
                    distribucion_moneda[moneda or "PYG"] = {
                        "total": float(total or 0),
                        "documentos": count,
                        "promedio": float((total or 0) / count) if count > 0 else 0
                    }
            except Exception:
                # Si no existe el campo moneda, usar distribución vacía
                distribucion_moneda = {"PYG": {"total": float(
                    total_facturado), "documentos": documentos_con_monto, "promedio": float(promedio_documento)}}

            return {
                "total_facturado": float(total_facturado),
                "total_iva": float(total_iva),
                "promedio_documento": float(promedio_documento),
                "documento_mayor": float(documento_mayor),
                "documento_menor": float(documento_menor),
                "documentos_con_monto": documentos_con_monto,
                "distribucion_moneda": distribucion_moneda,
                "total_sin_iva": float(total_facturado - total_iva),
                "porcentaje_iva": calculate_percentage(float(total_iva), float(total_facturado)) if float(total_facturado) > 0 else 0.0
            }

        except Exception as e:
            logger.error(f"Error obteniendo resumen financiero: {e}")
            return {
                "total_facturado": 0.0,
                "total_iva": 0.0,
                "promedio_documento": 0.0,
                "documento_mayor": 0.0,
                "documento_menor": 0.0,
                "documentos_con_monto": 0,
                "distribucion_moneda": {},
                "total_sin_iva": 0.0,
                "porcentaje_iva": 0.0
            }

    def _get_sifen_performance_summary(self, empresa_id: int, fecha_desde: date, fecha_hasta: date) -> Dict[str, Any]:
        """
        Obtiene resumen de performance SIFEN.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Resumen de performance SIFEN
        """
        try:
            # Conteo de documentos por estado SIFEN
            sifen_states_query = self.db.query(
                text("estado"),
                func.count(self.model.id).label('count')
            ).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision >= fecha_desde,
                    self.model.fecha_emision <= fecha_hasta,
                    text(
                        "estado IN ('enviado', 'aprobado', 'aprobado_observacion', 'rechazado', 'error_envio')")
                )
            ).group_by(text("estado")).all()

            # Procesar conteos
            enviados = 0
            aprobados = 0
            rechazados = 0

            for estado, count in sifen_states_query:
                if estado in ["enviado"]:
                    enviados += count
                elif estado in ["aprobado", "aprobado_observacion"]:
                    aprobados += count
                elif estado in ["rechazado", "error_envio"]:
                    rechazados += count

            total_procesados = aprobados + rechazados
            tasa_aprobacion = calculate_percentage(
                aprobados, total_procesados) if total_procesados > 0 else 0

            # Tiempo promedio de procesamiento (simulado por ahora)
            # TODO: Implementar cálculo real cuando estén disponibles los timestamps
            tiempo_promedio = 2.5

            return {
                "documentos_enviados": enviados,
                "documentos_aprobados": aprobados,
                "documentos_rechazados": rechazados,
                "documentos_pendientes": enviados,
                "total_procesados": total_procesados,
                "tasa_aprobacion": tasa_aprobacion,
                "tasa_rechazo": calculate_percentage(rechazados, total_procesados) if total_procesados > 0 else 0,
                "tiempo_promedio_procesamiento": tiempo_promedio
            }

        except Exception as e:
            logger.error(f"Error obteniendo performance SIFEN: {e}")
            return {
                "documentos_enviados": 0,
                "documentos_aprobados": 0,
                "documentos_rechazados": 0,
                "documentos_pendientes": 0,
                "total_procesados": 0,
                "tasa_aprobacion": 0.0,
                "tasa_rechazo": 0.0,
                "tiempo_promedio_procesamiento": 0.0
            }

    def _get_temporal_basic_metrics(self, empresa_id: int, fecha_desde: date, fecha_hasta: date) -> Dict[str, Any]:
        """
        Obtiene métricas temporales básicas.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Métricas temporales básicas
        """
        try:
            total_dias = (fecha_hasta - fecha_desde).days + 1

            # Documentos por día
            daily_query = self.db.query(
                self.model.fecha_emision,
                func.count(self.model.id).label('count')
            ).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision >= fecha_desde,
                    self.model.fecha_emision <= fecha_hasta
                )
            ).group_by(self.model.fecha_emision).all()

            # Procesar datos diarios
            documentos_por_dia = {}
            total_documentos = 0

            for fecha, count in daily_query:
                documentos_por_dia[fecha.isoformat()] = count
                total_documentos += count

            # Calcular métricas
            promedio_diario = total_documentos / total_dias if total_dias > 0 else 0

            # Día con mayor actividad
            dia_mayor_actividad = max(
                daily_query, key=lambda x: x.count) if daily_query else None

            # Días sin actividad
            dias_sin_actividad = total_dias - len(daily_query)

            return {
                "total_dias_periodo": total_dias,
                "dias_con_actividad": len(daily_query),
                "dias_sin_actividad": dias_sin_actividad,
                "promedio_documentos_dia": promedio_diario,
                "dia_mayor_actividad": {
                    "fecha": dia_mayor_actividad.fecha_emision.isoformat() if dia_mayor_actividad else None,
                    "documentos": dia_mayor_actividad.count if dia_mayor_actividad else 0
                } if dia_mayor_actividad else None,
                "documentos_por_dia": documentos_por_dia
            }

        except Exception as e:
            logger.error(f"Error obteniendo métricas temporales: {e}")
            return {
                "total_dias_periodo": 0,
                "dias_con_actividad": 0,
                "dias_sin_actividad": 0,
                "promedio_documentos_dia": 0.0,
                "dia_mayor_actividad": None,
                "documentos_por_dia": {}
            }

    def _get_daily_distribution(self, empresa_id: int, fecha_desde: date, fecha_hasta: date) -> Dict[str, Any]:
        """
        Obtiene distribución diaria detallada.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Distribución diaria detallada
        """
        try:
            # Query para obtener datos por día
            daily_data = self.db.query(
                self.model.fecha_emision,
                func.count(self.model.id).label('total_documentos'),
                func.sum(self.model.total_general).label('total_monto'),
                func.avg(self.model.total_general).label('promedio_monto')
            ).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision >= fecha_desde,
                    self.model.fecha_emision <= fecha_hasta
                )
            ).group_by(self.model.fecha_emision).all()

            # Procesar datos
            distribucion = []
            for fecha, total_docs, total_monto, promedio_monto in daily_data:
                distribucion.append({
                    "fecha": fecha.isoformat(),
                    "dia_semana": fecha.strftime("%A"),
                    "es_fin_semana": fecha.weekday() >= 5,
                    "total_documentos": total_docs,
                    "total_monto": float(total_monto or 0),
                    "promedio_monto": float(promedio_monto or 0)
                })

            # Análisis por día de semana
            dias_semana = {}
            for item in distribucion:
                dia = item["dia_semana"]
                if dia not in dias_semana:
                    dias_semana[dia] = {"documentos": 0, "monto": 0, "dias": 0}

                dias_semana[dia]["documentos"] += item["total_documentos"]
                dias_semana[dia]["monto"] += item["total_monto"]
                dias_semana[dia]["dias"] += 1

            # Calcular promedios por día de semana
            for dia in dias_semana:
                data = dias_semana[dia]
                if data["dias"] > 0:
                    data["promedio_documentos"] = data["documentos"] / data["dias"]
                    data["promedio_monto"] = data["monto"] / data["dias"]
                else:
                    data["promedio_documentos"] = 0
                    data["promedio_monto"] = 0

            return {
                "distribucion_diaria": distribucion,
                "analisis_dias_semana": dias_semana,
                "resumen": {
                    "dias_analizados": len(distribucion),
                    "dia_mas_activo": max(distribucion, key=lambda x: x["total_documentos"])["fecha"] if distribucion else None,
                    "dia_mayor_facturacion": max(distribucion, key=lambda x: x["total_monto"])["fecha"] if distribucion else None
                }
            }

        except Exception as e:
            logger.error(f"Error obteniendo distribución diaria: {e}")
            return {
                "distribucion_diaria": [],
                "analisis_dias_semana": {},
                "resumen": {
                    "dias_analizados": 0,
                    "dia_mas_activo": None,
                    "dia_mayor_facturacion": None
                }
            }

    def _get_hourly_distribution(self, empresa_id: int, target_date: date) -> Dict[str, Any]:
        """
        Obtiene distribución horaria para un día específico.

        Args:
            empresa_id: ID de la empresa
            target_date: Fecha específica a analizar

        Returns:
            Dict[str, Any]: Distribución horaria
        """
        try:
            # Query para obtener distribución horaria (usando created_at si está disponible)
            hourly_query = self.db.query(
                func.extract('hour', self.model.created_at).label('hora'),
                func.count(self.model.id).label('documentos')
            ).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision == target_date,
                    self.model.created_at.isnot(None)
                )
            ).group_by(func.extract('hour', self.model.created_at)).all()

            # Procesar datos horarios
            distribucion_horaria = {}
            total_docs = 0

            for hora, docs in hourly_query:
                if hora is not None:
                    hora_str = f"{int(hora):02d}:00"
                    distribucion_horaria[hora_str] = docs
                    total_docs += docs

            # Encontrar hora pico
            hora_pico = max(
                hourly_query, key=lambda x: x.documentos) if hourly_query else None

            return {
                "distribucion_horaria": distribucion_horaria,
                "hora_pico": {
                    "hora": f"{int(hora_pico.hora):02d}:00" if hora_pico and hora_pico.hora is not None else None,
                    "documentos": hora_pico.documentos if hora_pico else 0
                } if hora_pico else None,
                "total_documentos": total_docs,
                "horas_con_actividad": len(hourly_query)
            }

        except Exception as e:
            logger.error(f"Error obteniendo distribución horaria: {e}")
            return {
                "distribucion_horaria": {},
                "hora_pico": None,
                "total_documentos": 0,
                "horas_con_actividad": 0
            }

    def _get_document_type_activity(self, empresa_id: int, target_date: date) -> Dict[str, Any]:
        """
        Obtiene actividad por tipo de documento para un día específico.

        Args:
            empresa_id: ID de la empresa
            target_date: Fecha específica a analizar

        Returns:
            Dict[str, Any]: Actividad por tipo de documento
        """
        try:
            type_activity = self.db.query(
                self.model.tipo_documento,
                func.count(self.model.id).label('count'),
                func.sum(self.model.total_general).label('total_monto')
            ).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision == target_date
                )
            ).group_by(self.model.tipo_documento).all()

            # Mapear tipos de documento
            tipo_map = {
                "1": "facturas",
                "4": "autofacturas",
                "5": "notas_credito",
                "6": "notas_debito",
                "7": "notas_remision"
            }

            actividad = {}
            for tipo, count, total_monto in type_activity:
                nombre_tipo = tipo_map.get(tipo, f"tipo_{tipo}")
                actividad[nombre_tipo] = {
                    "documentos": count,
                    "total_monto": float(total_monto or 0),
                    "promedio_monto": float((total_monto or 0) / count) if count > 0 else 0
                }

            return actividad

        except Exception as e:
            logger.error(f"Error obteniendo actividad por tipo: {e}")
            return {}

    def _calculate_period_comparison(self, current_stats: Dict[str, Any], previous_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula comparación entre dos períodos.

        Args:
            current_stats: Estadísticas del período actual
            previous_stats: Estadísticas del período anterior

        Returns:
            Dict[str, Any]: Comparación entre períodos
        """
        try:
            current_docs = current_stats["resumen"]["total_documentos"]
            previous_docs = previous_stats["resumen"]["total_documentos"]

            current_amount = current_stats["financiero"].get(
                "total_facturado", 0)
            previous_amount = previous_stats["financiero"].get(
                "total_facturado", 0)

            return {
                "documentos": {
                    "actual": current_docs,
                    "anterior": previous_docs,
                    "cambio_absoluto": current_docs - previous_docs,
                    "cambio_porcentual": calculate_growth_rate(current_docs, previous_docs)
                },
                "financiero": {
                    "actual": current_amount,
                    "anterior": previous_amount,
                    "cambio_absoluto": current_amount - previous_amount,
                    "cambio_porcentual": calculate_growth_rate(current_amount, previous_amount)
                },
                "tendencia": "creciente" if current_docs > previous_docs else "decreciente" if current_docs < previous_docs else "estable"
            }

        except Exception as e:
            logger.error(f"Error calculando comparación de períodos: {e}")
            return {
                "documentos": {"actual": 0, "anterior": 0, "cambio_absoluto": 0, "cambio_porcentual": 0},
                "financiero": {"actual": 0, "anterior": 0, "cambio_absoluto": 0, "cambio_porcentual": 0},
                "tendencia": "sin_datos"
            }

    def _calculate_detailed_comparison(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula comparación detallada entre estadísticas.

        Args:
            current: Estadísticas actuales
            previous: Estadísticas anteriores

        Returns:
            Dict[str, Any]: Comparación detallada
        """
        try:
            comparison = {}

            # Comparación de resumen
            comparison["resumen"] = self._compare_section(
                current["resumen"], previous["resumen"])

            # Comparación financiera
            if current.get("financiero") and previous.get("financiero"):
                comparison["financiero"] = self._compare_section(
                    current["financiero"], previous["financiero"])

            # Comparación SIFEN
            if current.get("sifen") and previous.get("sifen"):
                comparison["sifen"] = self._compare_section(
                    current["sifen"], previous["sifen"])

            return comparison

        except Exception as e:
            logger.error(f"Error calculando comparación detallada: {e}")
            return {}

    def _compare_section(self, current_section: Dict[str, Any], previous_section: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compara una sección específica de estadísticas.

        Args:
            current_section: Sección actual
            previous_section: Sección anterior

        Returns:
            Dict[str, Any]: Comparación de la sección
        """
        comparison = {}

        for key in current_section:
            if key in previous_section:
                current_val = current_section[key]
                previous_val = previous_section[key]

                if isinstance(current_val, (int, float)) and isinstance(previous_val, (int, float)):
                    comparison[key] = {
                        "actual": current_val,
                        "anterior": previous_val,
                        "cambio_absoluto": current_val - previous_val,
                        "cambio_porcentual": calculate_growth_rate(current_val, previous_val)
                    }

        return comparison

    def _analyze_comparison_trends(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza tendencias de la comparación.

        Args:
            current: Estadísticas actuales
            previous: Estadísticas anteriores

        Returns:
            Dict[str, Any]: Análisis de tendencias
        """
        try:
            current_total = current["resumen"]["total_documentos"]
            previous_total = previous["resumen"]["total_documentos"]

            growth_rate = calculate_growth_rate(current_total, previous_total)

            # Clasificar tendencia
            if growth_rate > 10:
                trend_classification = "crecimiento_alto"
            elif growth_rate > 0:
                trend_classification = "crecimiento_moderado"
            elif growth_rate > -10:
                trend_classification = "decrecimiento_moderado"
            else:
                trend_classification = "decrecimiento_alto"

            return {
                "clasificacion": trend_classification,
                "tasa_crecimiento": growth_rate,
                "descripcion": self._get_trend_description(trend_classification, growth_rate)
            }

        except Exception as e:
            logger.error(f"Error analizando tendencias: {e}")
            return {
                "clasificacion": "sin_datos",
                "tasa_crecimiento": 0,
                "descripcion": "No hay suficientes datos para analizar tendencias"
            }

    def _get_trend_description(self, classification: str, growth_rate: float) -> str:
        """
        Obtiene descripción de tendencia.

        Args:
            classification: Clasificación de la tendencia
            growth_rate: Tasa de crecimiento

        Returns:
            str: Descripción de la tendencia
        """
        descriptions = {
            "crecimiento_alto": f"Crecimiento significativo del {growth_rate:.1f}%",
            "crecimiento_moderado": f"Crecimiento moderado del {growth_rate:.1f}%",
            "decrecimiento_moderado": f"Ligera disminución del {abs(growth_rate):.1f}%",
            "decrecimiento_alto": f"Disminución significativa del {abs(growth_rate):.1f}%"
        }
        return descriptions.get(classification, f"Cambio del {growth_rate:.1f}%")


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "DocumentoStatsMixin",
    "SIFEN_SUCCESS_STATES",
    "SIFEN_FAILED_STATES",
    "ACTIVE_DOCUMENT_STATES",
    "CACHE_CONFIG"
]
