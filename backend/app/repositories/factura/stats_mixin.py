# ===============================================
# ARCHIVO: backend/app/repositories/factura/stats_mixin.py
# PROPÓSITO: Mixin para estadísticas específicas de facturas
# VERSIÓN: 1.0.0 - Optimizado con queries SQL directas
# FASE: 4 - Validaciones y Stats (15% del módulo)
# ===============================================

"""
Estadísticas y métricas específicas de facturas SIFEN.

🎯 OPTIMIZACIÓN v1.0:
- Queries SQL directas para mejor performance
- Responses simples Dict[str, Any]
- Métricas específicas facturación Paraguay
- Helper único para manejo fechas/períodos
- Sin caching ni optimizaciones prematuras

Métricas implementadas:
- Facturación: Totales, promedios, tendencias por período
- Productos: Más vendidos, performance, análisis categorías
- Operacional: Tasas cobro, vencimientos, KPIs eficiencia
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union, Callable, Type
from decimal import Decimal
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Imports del proyecto
from app.models.factura import Factura, EstadoDocumentoEnum
from app.core.exceptions import SifenDatabaseError
from .utils import log_repository_operation

logger = logging.getLogger("factura_repository.stats")

# ===============================================
# HELPER PARA FECHAS Y PERÍODOS
# ===============================================


class StatsHelper:
    """Helper para manejo de fechas y períodos en estadísticas."""

    @staticmethod
    def get_period_dates(period_type: str, custom_start: Optional[date] = None,
                         custom_end: Optional[date] = None) -> Tuple[date, date]:
        """
        Obtiene fechas inicio y fin según tipo de período.

        Args:
            period_type: 'day', 'week', 'month', 'quarter', 'year', 'custom'
            custom_start: Fecha inicio para período custom
            custom_end: Fecha fin para período custom

        Returns:
            Tuple[date, date]: (fecha_inicio, fecha_fin)
        """
        today = date.today()

        if period_type == "day":
            return today, today
        elif period_type == "week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, end
        elif period_type == "month":
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1,
                                    month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1,
                                    day=1) - timedelta(days=1)
            return start, end
        elif period_type == "quarter":
            quarter = (today.month - 1) // 3 + 1
            start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            end_month = quarter * 3
            if end_month == 12:
                end = today.replace(year=today.year + 1,
                                    month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=end_month + 1,
                                    day=1) - timedelta(days=1)
            return start, end
        elif period_type == "year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            return start, end
        elif period_type == "custom":
            if not custom_start or not custom_end:
                return today - timedelta(days=30), today
            return custom_start, custom_end
        else:
            # Default: último mes
            start = today - timedelta(days=30)
            return start, today

    @staticmethod
    def format_currency(amount: Union[Decimal, int, float], currency: str = "PYG") -> str:
        """Formatea monto para display."""
        try:
            if isinstance(amount, (Decimal, int, float)):
                if currency == "PYG":
                    return f"₲ {int(amount):,}".replace(",", ".")
                else:
                    return f"{amount:,.2f}"
            return str(amount)
        except:
            return str(amount)

    @staticmethod
    def safe_divide(numerator: Union[Decimal, int, float],
                    denominator: Union[Decimal, int, float]) -> Decimal:
        """División segura que evita división por cero."""
        try:
            if denominator == 0:
                return Decimal("0")
            return Decimal(str(numerator)) / Decimal(str(denominator))
        except:
            return Decimal("0")

# ===============================================
# MIXIN PRINCIPAL
# ===============================================


class FacturaStatsMixin:
    """
    Mixin para estadísticas específicas de facturas SIFEN.

    🎯 OPTIMIZACIÓN v1.0:
    - Queries SQL directas para performance
    - Responses Dict[str, Any] simples
    - Helper único para fechas
    - Métricas específicas Paraguay
    """
    # Type hints para atributos que serán proporcionados por el repository base
    db: Session
    model: Type[Factura]

    # ===============================================
    # ESTADÍSTICAS FACTURACIÓN
    # ===============================================

    async def get_facturacion_stats(self, empresa_id: Optional[int] = None,
                                    period_type: str = "month") -> Dict[str, Any]:
        """
        Estadísticas generales de facturación.

        Args:
            empresa_id: ID empresa (opcional)
            period_type: Tipo período ('day', 'week', 'month', 'quarter', 'year')

        Returns:
            dict: Estadísticas de facturación
        """
        try:
            fecha_inicio, fecha_fin = StatsHelper.get_period_dates(period_type)

            # Query principal con estadísticas básicas
            sql = text("""
                SELECT 
                    COUNT(*) as total_facturas,
                    COUNT(CASE WHEN estado = 'aprobado' THEN 1 END) as facturas_aprobadas,
                    COALESCE(SUM(CASE WHEN estado = 'aprobado' THEN total_general ELSE 0 END), 0) as total_facturado,
                    COALESCE(SUM(CASE WHEN estado = 'aprobado' THEN total_iva ELSE 0 END), 0) as total_iva,
                    COALESCE(AVG(CASE WHEN estado = 'aprobado' THEN total_general ELSE NULL END), 0) as promedio_factura,
                    COALESCE(MAX(CASE WHEN estado = 'aprobado' THEN total_general ELSE 0 END), 0) as factura_maxima,
                    COALESCE(MIN(CASE WHEN estado = 'aprobado' AND total_general > 0 THEN total_general ELSE NULL END), 0) as factura_minima
                FROM factura 
                WHERE fecha_emision BETWEEN :fecha_inicio AND :fecha_fin
                """ + (" AND empresa_id = :empresa_id" if empresa_id else ""))

            params: Dict[str, Any] = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            }
            if empresa_id:
                params["empresa_id"] = empresa_id

            result = self.db.execute(sql, params).fetchone()

            if not result:
                # Retornar estadísticas vacías si no hay datos
                return {
                    "periodo": {
                        "tipo": period_type,
                        "inicio": fecha_inicio.isoformat(),
                        "fin": fecha_fin.isoformat(),
                        "dias": (fecha_fin - fecha_inicio).days + 1
                    },
                    "facturas": {"total": 0, "aprobadas": 0, "pendientes": 0, "tasa_aprobacion": 0.0},
                    "montos": {
                        "total_facturado": "0", "total_iva": "0", "promedio_factura": "0",
                        "factura_maxima": "0", "factura_minima": "0", "promedio_diario": "0"
                    },
                    "formatted": {
                        "total_facturado": "₲ 0", "promedio_factura": "₲ 0", "promedio_diario": "₲ 0"
                    }
                }

            # Calcular métricas adicionales
            dias_periodo = (fecha_fin - fecha_inicio).days + 1
            promedio_diario = StatsHelper.safe_divide(
                result.total_facturado, dias_periodo)

            stats = {
                "periodo": {
                    "tipo": period_type,
                    "inicio": fecha_inicio.isoformat(),
                    "fin": fecha_fin.isoformat(),
                    "dias": dias_periodo
                },
                "facturas": {
                    "total": result.total_facturas,
                    "aprobadas": result.facturas_aprobadas,
                    "pendientes": result.total_facturas - result.facturas_aprobadas,
                    "tasa_aprobacion": float(StatsHelper.safe_divide(result.facturas_aprobadas, result.total_facturas) * 100)
                },
                "montos": {
                    "total_facturado": str(result.total_facturado),
                    "total_iva": str(result.total_iva),
                    "promedio_factura": str(result.promedio_factura),
                    "factura_maxima": str(result.factura_maxima),
                    "factura_minima": str(result.factura_minima),
                    "promedio_diario": str(promedio_diario)
                },
                "formatted": {
                    "total_facturado": StatsHelper.format_currency(result.total_facturado),
                    "promedio_factura": StatsHelper.format_currency(result.promedio_factura),
                    "promedio_diario": StatsHelper.format_currency(promedio_diario)
                }
            }

            log_repository_operation("get_facturacion_stats", details={
                                     "period": period_type})
            return stats

        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo estadísticas facturación: {e}")
            raise SifenDatabaseError(f"Error en estadísticas: {str(e)}")

    async def get_revenue_by_period(self, empresa_id: Optional[int] = None,
                                    period_type: str = "day", days_back: int = 30) -> Dict[str, Any]:
        """
        Ingresos por período de tiempo.

        Args:
            empresa_id: ID empresa (opcional)
            period_type: Granularidad ('day', 'week', 'month')
            days_back: Días hacia atrás para analizar

        Returns:
            dict: Ingresos por período
        """
        try:
            fecha_fin = date.today()
            fecha_inicio = fecha_fin - timedelta(days=days_back)

            # Query según granularidad
            if period_type == "day":
                group_expr = "DATE(fecha_emision)"
                date_format = "%Y-%m-%d"
            elif period_type == "week":
                group_expr = "DATE_TRUNC('week', fecha_emision)"
                date_format = "%Y-W%W"
            else:  # month
                group_expr = "DATE_TRUNC('month', fecha_emision)"
                date_format = "%Y-%m"

            sql = text(f"""
                SELECT 
                    {group_expr} as periodo,
                    COUNT(*) as facturas,
                    COALESCE(SUM(total_general), 0) as ingresos,
                    COALESCE(SUM(total_iva), 0) as iva,
                    COALESCE(AVG(total_general), 0) as promedio
                FROM factura 
                WHERE fecha_emision BETWEEN :fecha_inicio AND :fecha_fin
                AND estado = 'aprobado'
                """ + (" AND empresa_id = :empresa_id" if empresa_id else "") + f"""
                GROUP BY {group_expr}
                ORDER BY periodo ASC
            """)

            params: Dict[str, Any] = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            }
            if empresa_id:
                params["empresa_id"] = empresa_id

            results = self.db.execute(sql, params).fetchall()

            # Procesar resultados
            periodos = []
            total_ingresos = Decimal("0")
            total_facturas = 0

            for row in results:
                periodo_data = {
                    "periodo": row.periodo.strftime(date_format) if hasattr(row.periodo, 'strftime') else str(row.periodo),
                    "facturas": row.facturas,
                    "ingresos": str(row.ingresos),
                    "iva": str(row.iva),
                    "promedio": str(row.promedio),
                    "ingresos_formatted": StatsHelper.format_currency(row.ingresos)
                }
                periodos.append(periodo_data)
                total_ingresos += Decimal(str(row.ingresos))
                total_facturas += row.facturas

            revenue_data = {
                "config": {
                    "period_type": period_type,
                    "days_back": days_back,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": fecha_fin.isoformat()
                },
                "summary": {
                    "total_periodos": len(periodos),
                    "total_facturas": total_facturas,
                    "total_ingresos": str(total_ingresos),
                    "promedio_periodo": str(StatsHelper.safe_divide(total_ingresos, len(periodos))),
                    "total_ingresos_formatted": StatsHelper.format_currency(total_ingresos)
                },
                "periodos": periodos
            }

            log_repository_operation("get_revenue_by_period", details={
                                     "periods": len(periodos)})
            return revenue_data

        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo ingresos por período: {e}")
            raise SifenDatabaseError(f"Error en ingresos: {str(e)}")

    async def get_average_invoice_value(self, empresa_id: Optional[int] = None,
                                        last_days: int = 30) -> Dict[str, Any]:
        """
        Valor promedio de facturas con análisis detallado.

        Args:
            empresa_id: ID empresa (opcional)
            last_days: Días para análisis

        Returns:
            dict: Análisis valor promedio
        """
        try:
            fecha_inicio = date.today() - timedelta(days=last_days)

            sql = text("""
                SELECT 
                    COUNT(*) as total_facturas,
                    COALESCE(AVG(total_general), 0) as promedio_general,
                    COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_general), 0) as mediana,
                    COALESCE(STDDEV(total_general), 0) as desviacion_estandar,
                    COALESCE(MIN(total_general), 0) as minimo,
                    COALESCE(MAX(total_general), 0) as maximo
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio 
                AND estado = 'aprobado'
                AND total_general > 0
                """ + (" AND empresa_id = :empresa_id" if empresa_id else ""))

            params: Dict[str, Any] = {
                "fecha_inicio": fecha_inicio
            }
            if empresa_id:
                params["empresa_id"] = empresa_id

            result = self.db.execute(sql, params).fetchone()

            # Rangos de facturación
            ranges_sql = text("""
                SELECT 
                    CASE 
                        WHEN total_general <= 1000000 THEN 'Hasta 1M'
                        WHEN total_general <= 5000000 THEN '1M - 5M'
                        WHEN total_general <= 10000000 THEN '5M - 10M'
                        WHEN total_general <= 50000000 THEN '10M - 50M'
                        ELSE 'Más de 50M'
                    END as rango,
                    COUNT(*) as cantidad,
                    COALESCE(SUM(total_general), 0) as total_rango
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio 
                AND estado = 'aprobado'
                AND total_general > 0
                """ + (" AND empresa_id = :empresa_id" if empresa_id else "") + """
                GROUP BY 
                    CASE 
                        WHEN total_general <= 1000000 THEN 'Hasta 1M'
                        WHEN total_general <= 5000000 THEN '1M - 5M'
                        WHEN total_general <= 10000000 THEN '5M - 10M'
                        WHEN total_general <= 50000000 THEN '10M - 50M'
                        ELSE 'Más de 50M'
                    END
                ORDER BY total_rango DESC
            """)

            ranges_result = self.db.execute(ranges_sql, params).fetchall()

            if not result:
                return self.handle_empty_result("average_invoice_value", {
                    "dias": last_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                })

            # Procesar rangos
            rangos = []
            for row in ranges_result:
                rangos.append({
                    "rango": row.rango,
                    "cantidad": row.cantidad,
                    "total": str(row.total_rango),
                    "porcentaje": float(StatsHelper.safe_divide(row.cantidad, result.total_facturas) * 100),
                    "total_formatted": StatsHelper.format_currency(row.total_rango)
                })

            average_analysis = {
                "periodo_analisis": {
                    "dias": last_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                },
                "estadisticas": {
                    "total_facturas": result.total_facturas,
                    "promedio": str(result.promedio_general),
                    "mediana": str(result.mediana),
                    "desviacion_estandar": str(result.desviacion_estandar),
                    "minimo": str(result.minimo),
                    "maximo": str(result.maximo)
                },
                "formatted": {
                    "promedio": StatsHelper.format_currency(result.promedio_general),
                    "mediana": StatsHelper.format_currency(result.mediana),
                    "minimo": StatsHelper.format_currency(result.minimo),
                    "maximo": StatsHelper.format_currency(result.maximo)
                },
                "rangos_facturacion": rangos
            }

            log_repository_operation("get_average_invoice_value", details={
                                     "facturas": result.total_facturas})
            return average_analysis

        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo valor promedio: {e}")
            raise SifenDatabaseError(f"Error en valor promedio: {str(e)}")

    async def get_top_clients(self, empresa_id: Optional[int] = None,
                              limit: int = 10, period_days: int = 90) -> Dict[str, Any]:
        """
        Clientes top por facturación.

        Args:
            empresa_id: ID empresa (opcional)
            limit: Número de clientes top
            period_days: Días para análisis

        Returns:
            dict: Top clientes
        """
        try:
            fecha_inicio = date.today() - timedelta(days=period_days)

            sql = text("""
                SELECT 
                    cliente_id,
                    COUNT(*) as total_facturas,
                    COALESCE(SUM(total_general), 0) as total_facturado,
                    COALESCE(AVG(total_general), 0) as promedio_factura,
                    COALESCE(MAX(total_general), 0) as factura_maxima,
                    MIN(fecha_emision) as primera_factura,
                    MAX(fecha_emision) as ultima_factura
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio
                AND estado = 'aprobado'
                """ + (" AND empresa_id = :empresa_id" if empresa_id else "") + """
                GROUP BY cliente_id
                ORDER BY total_facturado DESC
                LIMIT :limit
            """)

            params = {"fecha_inicio": fecha_inicio, "limit": limit}
            if empresa_id:
                params["empresa_id"] = empresa_id

            results = self.db.execute(sql, params).fetchall()

            total_sql = text("""
                SELECT COALESCE(SUM(total_general), 0) as gran_total
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio 
                AND estado = 'aprobado'
                """ + (" AND empresa_id = :empresa_id" if empresa_id else ""))

            total_result = self.db.execute(total_sql, params).fetchone()

            # Verificar si hay resultados
            if not total_result or not results:
                return self.handle_empty_result("top_clients", {
                    "limit": limit,
                    "period_days": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                })

            # Calcular total general para porcentajes
            total_sql = text("""
                SELECT COALESCE(SUM(total_general), 0) as gran_total
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio 
                AND estado = 'aprobado'
                """ + (" AND empresa_id = :empresa_id" if empresa_id else ""))

            total_result = self.db.execute(total_sql, params).fetchone()
            if total_result is None:
                gran_total = Decimal("0")
            else:
                gran_total = Decimal(str(total_result.gran_total))

            # Procesar clientes top
            clientes = []
            total_top_clients = Decimal("0")

            for i, row in enumerate(results, 1):
                cliente_total = Decimal(str(row.total_facturado))
                total_top_clients += cliente_total

                clientes.append({
                    "ranking": i,
                    "cliente_id": row.cliente_id,
                    "total_facturas": row.total_facturas,
                    "total_facturado": str(cliente_total),
                    "promedio_factura": str(row.promedio_factura),
                    "factura_maxima": str(row.factura_maxima),
                    "primera_factura": row.primera_factura.isoformat(),
                    "ultima_factura": row.ultima_factura.isoformat(),
                    "porcentaje_total": float(StatsHelper.safe_divide(cliente_total, gran_total) * 100),
                    "formatted": {
                        "total_facturado": StatsHelper.format_currency(cliente_total),
                        "promedio_factura": StatsHelper.format_currency(row.promedio_factura),
                        "factura_maxima": StatsHelper.format_currency(row.factura_maxima)
                    }
                })

            top_clients_data = {
                "config": {
                    "limit": limit,
                    "period_days": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                },
                "summary": {
                    "total_clientes_top": len(clientes),
                    "total_facturado_top": str(total_top_clients),
                    "gran_total_periodo": str(gran_total),
                    "concentracion_top": float(StatsHelper.safe_divide(total_top_clients, gran_total) * 100),
                    "total_facturado_top_formatted": StatsHelper.format_currency(total_top_clients)
                },
                "clientes": clientes
            }

            log_repository_operation("get_top_clients", details={
                                     "clientes": len(clientes)})
            return top_clients_data

        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo top clientes: {e}")
            raise SifenDatabaseError(f"Error en top clientes: {str(e)}")

    # ===============================================
    # ANÁLISIS PRODUCTOS (Placeholder para futuro)
    # ===============================================

    async def get_top_productos(self, empresa_id: Optional[int] = None,
                                limit: int = 10) -> Dict[str, Any]:
        """
        Productos más vendidos.

        TODO: Implementar cuando esté disponible ItemFactura
        """
        return {
            "message": "Análisis de productos disponible cuando esté implementado ItemFactura",
            "config": {"limit": limit, "empresa_id": empresa_id},
            "productos": []
        }

    async def get_product_performance(self, producto_id: int,
                                      period_days: int = 90) -> Dict[str, Any]:
        """
        Performance por producto específico.

        TODO: Implementar cuando esté disponible ItemFactura
        """
        return {
            "message": "Performance productos disponible cuando esté implementado ItemFactura",
            "producto_id": producto_id,
            "period_days": period_days,
            "performance": {}
        }

    async def get_category_analysis(self, empresa_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Análisis por categoría de productos.

        TODO: Implementar cuando esté disponible relación Producto-Categoría
        """
        return {
            "message": "Análisis categorías disponible cuando esté implementado sistema de categorías",
            "empresa_id": empresa_id,
            "categorias": []
        }

    # ===============================================
    # MÉTRICAS OPERACIONALES
    # ===============================================

    async def get_conversion_rates(self, empresa_id: Optional[int] = None,
                                   period_days: int = 30) -> Dict[str, Any]:
        """
        Tasas de conversión y eficiencia operacional.

        Args:
            empresa_id: ID empresa (opcional)
            period_days: Días para análisis

        Returns:
            dict: Tasas de conversión
        """
        try:
            fecha_inicio = date.today() - timedelta(days=period_days)

            sql = text("""
                SELECT 
                    COUNT(*) as total_documentos,
                    COUNT(CASE WHEN estado = 'borrador' THEN 1 END) as borradores,
                    COUNT(CASE WHEN estado = 'enviado' THEN 1 END) as enviados,
                    COUNT(CASE WHEN estado = 'aprobado' THEN 1 END) as aprobados,
                    COUNT(CASE WHEN estado = 'rechazado' THEN 1 END) as rechazados,
                    COUNT(CASE WHEN estado = 'cancelado' THEN 1 END) as cancelados
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio
                """ + (" AND empresa_id = :empresa_id" if empresa_id else ""))

            params: Dict[str, Any] = {
                "fecha_inicio": fecha_inicio
            }
            if empresa_id:
                params["empresa_id"] = empresa_id

            result = self.db.execute(sql, params).fetchone()

            if not result:
                return self.handle_empty_result("average_invoice_value", {
                    "dias": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                })

            # Calcular tasas
            total = result.total_documentos
            if total == 0:
                return {"message": "No hay datos suficientes para calcular tasas"}

            conversion_data = {
                "periodo": {
                    "dias": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                },
                "volumenes": {
                    "total_documentos": total,
                    "borradores": result.borradores,
                    "enviados": result.enviados,
                    "aprobados": result.aprobados,
                    "rechazados": result.rechazados,
                    "cancelados": result.cancelados
                },
                "tasas": {
                    "tasa_envio": float(StatsHelper.safe_divide(result.enviados + result.aprobados + result.rechazados, total) * 100),
                    "tasa_aprobacion": float(StatsHelper.safe_divide(result.aprobados, total) * 100),
                    "tasa_rechazo": float(StatsHelper.safe_divide(result.rechazados, total) * 100),
                    "tasa_completitud": float(StatsHelper.safe_divide(result.aprobados + result.rechazados, total) * 100),
                    "eficiencia_proceso": float(StatsHelper.safe_divide(result.aprobados, result.enviados + result.aprobados + result.rechazados) * 100) if (result.enviados + result.aprobados + result.rechazados) > 0 else 0
                }
            }

            log_repository_operation(
                "get_conversion_rates", details={"total": total})
            return conversion_data

        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo tasas conversión: {e}")
            raise SifenDatabaseError(f"Error en tasas: {str(e)}")

    async def get_payment_analysis(self, empresa_id: Optional[int] = None,
                                   period_days: int = 90) -> Dict[str, Any]:
        """
        Análisis de condiciones de pago.

        Args:
            empresa_id: ID empresa (opcional)
            period_days: Días para análisis

        Returns:
            dict: Análisis de pagos
        """
        try:
            fecha_inicio = date.today() - timedelta(days=period_days)

            sql = text("""
                SELECT 
                    condicion_operacion,
                    COUNT(*) as cantidad,
                    COALESCE(SUM(total_general), 0) as monto_total,
                    COALESCE(AVG(total_general), 0) as promedio
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio
                AND estado = 'aprobado'
                """ + (" AND empresa_id = :empresa_id" if empresa_id else "") + """
                GROUP BY condicion_operacion
                ORDER BY monto_total DESC
            """)

            params: Dict[str, Any] = {
                "fecha_inicio": fecha_inicio
            }
            if empresa_id:
                params["empresa_id"] = empresa_id
            results = self.db.execute(sql, params).fetchall()

            # Mapear condiciones
            condicion_map = {"1": "Contado", "2": "Crédito"}
            condiciones = []
            total_facturas = sum(row.cantidad for row in results)
            total_monto = sum(Decimal(str(row.monto_total)) for row in results)

            for row in results:
                monto = Decimal(str(row.monto_total))
                condiciones.append({
                    "condicion_codigo": row.condicion_operacion,
                    "condicion_nombre": condicion_map.get(row.condicion_operacion, "Desconocida"),
                    "cantidad": row.cantidad,
                    "monto_total": str(monto),
                    "promedio": str(row.promedio),
                    "porcentaje_cantidad": float(StatsHelper.safe_divide(row.cantidad, total_facturas) * 100),
                    "porcentaje_monto": float(StatsHelper.safe_divide(monto, total_monto) * 100),
                    "formatted": {
                        "monto_total": StatsHelper.format_currency(monto),
                        "promedio": StatsHelper.format_currency(row.promedio)
                    }
                })

            payment_analysis = {
                "periodo": {
                    "dias": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                },
                "resumen": {
                    "total_facturas": total_facturas,
                    "total_monto": str(total_monto),
                    "total_monto_formatted": StatsHelper.format_currency(total_monto)
                },
                "condiciones": condiciones
            }

            log_repository_operation("get_payment_analysis", details={
                                     "condiciones": len(condiciones)})
            return payment_analysis

        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo análisis pagos: {e}")
            raise SifenDatabaseError(f"Error en análisis pagos: {str(e)}")

    async def get_collection_metrics(self, empresa_id: Optional[int] = None,
                                     period_days: int = 60) -> Dict[str, Any]:
        """
        Métricas de cobranza y vencimientos.

        Args:
            empresa_id: ID empresa (opcional)
            period_days: Días para análisis

        Returns:
            dict: Métricas de cobranza
        """
        try:
            fecha_inicio = date.today() - timedelta(days=period_days)
            hoy = date.today()

            # Query principal para métricas de cobranza
            sql = text("""
                SELECT 
                    COUNT(*) as total_facturas,
                    COUNT(CASE WHEN condicion_operacion = '1' THEN 1 END) as facturas_contado,
                    COUNT(CASE WHEN condicion_operacion = '2' THEN 1 END) as facturas_credito,
                    COUNT(CASE WHEN estado = 'aprobado' THEN 1 END) as facturas_aprobadas,
                    COALESCE(SUM(CASE WHEN estado = 'aprobado' THEN total_general ELSE 0 END), 0) as monto_aprobado,
                    COALESCE(SUM(CASE WHEN condicion_operacion = '2' AND estado = 'aprobado' THEN total_general ELSE 0 END), 0) as monto_credito_pendiente
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio
                """ + (" AND empresa_id = :empresa_id" if empresa_id else ""))

            params: Dict[str, Any] = {
                "fecha_inicio": fecha_inicio
            }
            if empresa_id:
                params["empresa_id"] = empresa_id

            result = self.db.execute(sql, params).fetchone()

            # Análisis de antigüedad (simulado basado en fecha emisión)
            antiguedad_sql = text("""
                SELECT 
                    CASE 
                        WHEN :fecha_hoy - fecha_emision <= 30 THEN '0-30 días'
                        WHEN :fecha_hoy - fecha_emision <= 60 THEN '31-60 días'
                        WHEN :fecha_hoy - fecha_emision <= 90 THEN '61-90 días'
                        ELSE 'Más de 90 días'
                    END as rango_antiguedad,
                    COUNT(*) as cantidad,
                    COALESCE(SUM(total_general), 0) as monto
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio
                AND condicion_operacion = '2'
                AND estado = 'aprobado'
                """ + (" AND empresa_id = :empresa_id" if empresa_id else "") + """
                GROUP BY 
                    CASE 
                        WHEN :fecha_hoy - fecha_emision <= 30 THEN '0-30 días'
                        WHEN :fecha_hoy - fecha_emision <= 60 THEN '31-60 días'
                        WHEN :fecha_hoy - fecha_emision <= 90 THEN '61-90 días'
                        ELSE 'Más de 90 días'
                    END
                ORDER BY monto DESC
            """)

            params_antiguedad = params.copy()
            params_antiguedad["fecha_hoy"] = hoy

            antiguedad_results = self.db.execute(
                antiguedad_sql, params_antiguedad).fetchall()
            if not result:
                return self.handle_empty_result("average_invoice_value", {
                    "dias": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                })
            # Procesar antiguedad
            antiguedad = []
            total_credito = Decimal(str(result.monto_credito_pendiente))

            for row in antiguedad_results:
                monto = Decimal(str(row.monto))
                antiguedad.append({
                    "rango": row.rango_antiguedad,
                    "cantidad": row.cantidad,
                    "monto": str(monto),
                    "porcentaje": float(StatsHelper.safe_divide(monto, total_credito) * 100),
                    "monto_formatted": StatsHelper.format_currency(monto)
                })

            collection_metrics = {
                "periodo": {
                    "dias": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": hoy.isoformat()
                },
                "resumen": {
                    "total_facturas": result.total_facturas,
                    "facturas_contado": result.facturas_contado,
                    "facturas_credito": result.facturas_credito,
                    "monto_total_aprobado": str(result.monto_aprobado),
                    "monto_credito_pendiente": str(result.monto_credito_pendiente),
                    "porcentaje_credito": float(StatsHelper.safe_divide(result.facturas_credito, result.total_facturas) * 100)
                },
                "formatted": {
                    "monto_total_aprobado": StatsHelper.format_currency(result.monto_aprobado),
                    "monto_credito_pendiente": StatsHelper.format_currency(result.monto_credito_pendiente)
                },
                "antiguedad_creditos": antiguedad
            }

            log_repository_operation("get_collection_metrics", details={
                                     "facturas_credito": result.facturas_credito})
            return collection_metrics

        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo métricas cobranza: {e}")
            raise SifenDatabaseError(f"Error en métricas cobranza: {str(e)}")

    async def get_operational_kpis(self, empresa_id: Optional[int] = None,
                                   period_days: int = 30) -> Dict[str, Any]:
        """
        KPIs operacionales clave.

        Args:
            empresa_id: ID empresa (opcional)
            period_days: Días para análisis

        Returns:
            dict: KPIs operacionales
        """
        try:
            fecha_inicio = date.today() - timedelta(days=period_days)
            fecha_periodo_anterior = fecha_inicio - timedelta(days=period_days)

            # KPIs período actual
            sql_actual = text("""
                SELECT 
                    COUNT(*) as total_facturas,
                    COUNT(CASE WHEN estado = 'aprobado' THEN 1 END) as facturas_aprobadas,
                    COALESCE(SUM(CASE WHEN estado = 'aprobado' THEN total_general ELSE 0 END), 0) as ingresos,
                    COALESCE(AVG(CASE WHEN estado = 'aprobado' THEN total_general ELSE NULL END), 0) as ticket_promedio,
                    COUNT(DISTINCT cliente_id) as clientes_unicos,
                    COALESCE(AVG(CASE WHEN estado = 'aprobado' THEN total_general ELSE NULL END), 0) / NULLIF(COUNT(DISTINCT cliente_id), 0) as valor_cliente
                FROM factura 
                WHERE fecha_emision >= :fecha_inicio
                """ + (" AND empresa_id = :empresa_id" if empresa_id else ""))

            # KPIs período anterior (para comparación)
            sql_anterior = text("""
                SELECT 
                    COUNT(*) as total_facturas,
                    COUNT(CASE WHEN estado = 'aprobado' THEN 1 END) as facturas_aprobadas,
                    COALESCE(SUM(CASE WHEN estado = 'aprobado' THEN total_general ELSE 0 END), 0) as ingresos,
                    COALESCE(AVG(CASE WHEN estado = 'aprobado' THEN total_general ELSE NULL END), 0) as ticket_promedio,
                    COUNT(DISTINCT cliente_id) as clientes_unicos
                FROM factura 
                WHERE fecha_emision >= :fecha_anterior AND fecha_emision < :fecha_inicio
                """ + (" AND empresa_id = :empresa_id" if empresa_id else ""))

            params_actual: Dict[str, Any] = {"fecha_inicio": fecha_inicio}
            params_anterior: Dict[str, Any] = {
                "fecha_anterior": fecha_periodo_anterior, "fecha_inicio": fecha_inicio}

            if empresa_id:
                params_actual["empresa_id"] = empresa_id
                params_anterior["empresa_id"] = empresa_id

            result_actual = self.db.execute(
                sql_actual, params_actual).fetchone()
            result_anterior = self.db.execute(
                sql_anterior, params_anterior).fetchone()

            if not result_actual or not result_anterior:
                return self.handle_empty_result("operational_kpis", {
                    "dias": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat()
                })

            # Calcular variaciones
            def calcular_variacion(actual, anterior):
                if anterior == 0:
                    return 100.0 if actual > 0 else 0.0
                return float((actual - anterior) / anterior * 100)

            # KPIs con variaciones
            kpis = {
                "periodo": {
                    "dias": period_days,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": date.today().isoformat(),
                    "periodo_comparacion": f"{fecha_periodo_anterior.isoformat()} - {fecha_inicio.isoformat()}"
                },
                "kpis_principales": {
                    "facturas_emitidas": {
                        "actual": result_actual.total_facturas,
                        "anterior": result_anterior.total_facturas,
                        "variacion": calcular_variacion(result_actual.total_facturas, result_anterior.total_facturas)
                    },
                    "tasa_aprobacion": {
                        "actual": float(StatsHelper.safe_divide(result_actual.facturas_aprobadas, result_actual.total_facturas) * 100),
                        "anterior": float(StatsHelper.safe_divide(result_anterior.facturas_aprobadas, result_anterior.total_facturas) * 100),
                        "variacion": calcular_variacion(
                            StatsHelper.safe_divide(
                                result_actual.facturas_aprobadas, result_actual.total_facturas),
                            StatsHelper.safe_divide(
                                result_anterior.facturas_aprobadas, result_anterior.total_facturas)
                        )
                    },
                    "ingresos": {
                        "actual": str(result_actual.ingresos),
                        "anterior": str(result_anterior.ingresos),
                        "variacion": calcular_variacion(result_actual.ingresos, result_anterior.ingresos),
                        "actual_formatted": StatsHelper.format_currency(result_actual.ingresos),
                        "anterior_formatted": StatsHelper.format_currency(result_anterior.ingresos)
                    },
                    "ticket_promedio": {
                        "actual": str(result_actual.ticket_promedio),
                        "anterior": str(result_anterior.ticket_promedio),
                        "variacion": calcular_variacion(result_actual.ticket_promedio, result_anterior.ticket_promedio),
                        "actual_formatted": StatsHelper.format_currency(result_actual.ticket_promedio),
                        "anterior_formatted": StatsHelper.format_currency(result_anterior.ticket_promedio)
                    },
                    "clientes_activos": {
                        "actual": result_actual.clientes_unicos,
                        "anterior": result_anterior.clientes_unicos,
                        "variacion": calcular_variacion(result_actual.clientes_unicos, result_anterior.clientes_unicos)
                    }
                },
                "metricas_calculadas": {
                    "facturas_por_dia": round(result_actual.total_facturas / period_days, 2),
                    "ingresos_por_dia": str(StatsHelper.safe_divide(result_actual.ingresos, period_days)),
                    "facturas_por_cliente": round(StatsHelper.safe_divide(result_actual.total_facturas, result_actual.clientes_unicos), 2) if result_actual.clientes_unicos > 0 else 0,
                    "ingresos_por_dia_formatted": StatsHelper.format_currency(StatsHelper.safe_divide(result_actual.ingresos, period_days))
                }
            }

            log_repository_operation("get_operational_kpis", details={
                                     "period_days": period_days})
            return kpis

        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo KPIs operacionales: {e}")
            raise SifenDatabaseError(f"Error en KPIs: {str(e)}")

    # ===============================================
    # MÉTODO AUXILIAR INFORMACIÓN
    # ===============================================

    def get_stats_summary(self) -> Dict[str, Any]:
        """Información del mixin de estadísticas."""
        return {
            "name": "FacturaStatsMixin",
            "version": "1.0.0 - Optimizado",
            "categories": {
                "facturacion": [
                    "get_facturacion_stats",
                    "get_revenue_by_period",
                    "get_average_invoice_value",
                    "get_top_clients"
                ],
                "productos": [
                    "get_top_productos",
                    "get_product_performance",
                    "get_category_analysis"
                ],
                "operacional": [
                    "get_conversion_rates",
                    "get_payment_analysis",
                    "get_collection_metrics",
                    "get_operational_kpis"
                ]
            },
            "features": [
                "SQL directo para performance",
                "Análisis comparativo períodos",
                "Métricas formateadas para display",
                "Cálculos porcentuales automáticos",
                "Manejo seguro división por cero"
            ],
            "supported_periods": ["day", "week", "month", "quarter", "year", "custom"],
            "currencies_supported": ["PYG", "USD", "EUR", "BRL", "ARS"]
        }
    # ===============================================
    # HELPERS
    # ===============================================

    @staticmethod
    def handle_empty_result(method_name: str, period_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retorna estructura estándar para resultados vacíos.

        Args:
            method_name: Nombre del método que llama
            period_info: Info del período (dias, fecha_inicio, fecha_fin)

        Returns:
            dict: Estructura vacía apropiada para el método
        """
        base_empty = {
            "message": f"No hay datos disponibles para {method_name}",
            "periodo": period_info,
            "datos_vacios": True
        }

        # Estructuras específicas por método
        if "facturacion_stats" in method_name:
            base_empty.update({
                "facturas": {"total": 0, "aprobadas": 0, "pendientes": 0, "tasa_aprobacion": 0.0},
                "montos": {
                    "total_facturado": "0", "total_iva": "0", "promedio_factura": "0",
                    "factura_maxima": "0", "factura_minima": "0", "promedio_diario": "0"
                },
                "formatted": {"total_facturado": "₲ 0", "promedio_factura": "₲ 0", "promedio_diario": "₲ 0"}
            })
        elif "average_invoice" in method_name:
            base_empty.update({
                "estadisticas": {"total_facturas": 0, "promedio": "0", "mediana": "0", "desviacion_estandar": "0", "minimo": "0", "maximo": "0"},
                "formatted": {"promedio": "₲ 0", "mediana": "₲ 0", "minimo": "₲ 0", "maximo": "₲ 0"},
                "rangos_facturacion": []
            })
        elif "top_clients" in method_name:
            base_empty.update({
                "summary": {
                    "total_clientes_top": 0,
                    "total_facturado_top": "0",
                    "gran_total_periodo": "0",
                    "concentracion_top": 0.0,
                    "total_facturado_top_formatted": "₲ 0"
                },
                "clientes": []
            })
        # Agregar más casos según necesidad

        return base_empty
# ===============================================
# EXPORTS
# ===============================================


__all__ = [
    "FacturaStatsMixin",
    "StatsHelper"
]
