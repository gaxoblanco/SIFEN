# ===============================================
# ARCHIVO: backend/app/repositories/documento/document_types_t1.py
# PROPÓSITO: Mixin para operaciones específicas de Facturas Electrónicas (FE - Tipo 1)
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para operaciones específicas de Facturas Electrónicas (FE - Tipo 1).

Este módulo implementa funcionalidades especializadas para el manejo de facturas
electrónicas, incluyendo:
- Creación con validaciones específicas de facturas
- Validaciones de IVA y cálculos fiscales
- Búsquedas optimizadas para facturas
- Estadísticas específicas de ventas
- Integración con validaciones SIFEN

Características principales:
- Validación automática de IVA (5% y 10%)
- Aplicación de defaults específicos para facturas
- Búsquedas por criterios comerciales (cliente, monto, IVA)
- Estadísticas de ventas y tendencias
- Conformidad total con SIFEN v150

Clase principal:
- DocumentTypesT1Mixin: Mixin especializado para facturas electrónicas
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, text, desc, asc
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenValidationError,
    SifenEntityNotFoundError,
    SifenBusinessLogicError,
    SifenDuplicateEntityError,
    handle_database_exception
)
from app.models.documento import (
    FacturaElectronica,
    TipoDocumentoSifenEnum,
    EstadoDocumentoSifenEnum,
    MonedaSifenEnum,
    TipoOperacionSifenEnum,
    CondicionOperacionSifenEnum
)
from app.schemas.documento import (
    DocumentoCreateDTO,
    DocumentoBaseDTO
)
from ..utils import (
    normalize_cdc,
    format_numero_completo,
    log_repository_operation,
    log_performance_metric,
    handle_repository_error,
    build_date_filter,
    build_amount_filter,
    calculate_percentage,
    get_date_range_for_period,
    aggregate_by_period,
    format_stats_for_chart,
    get_default_page_size,
    get_max_page_size
)
from ..auxiliars import (
    apply_default_config,
    validate_factura_data,
    get_documents_by_type_and_criteria,
    calculate_totals_from_items,
    create_items_for_document
)

logger = get_logger(__name__)

# ===============================================
# CONFIGURACIONES ESPECÍFICAS PARA FACTURAS
# ===============================================

# Defaults específicos para facturas electrónicas
FACTURA_DEFAULTS = {
    "tipo_documento": "1",
    "tipo_operacion": "1",  # Venta
    "condicion_operacion": "1",  # Contado
    "moneda": "PYG",
    "tipo_emision": "1",  # Normal
    "indicador_presencia": "1",  # Presencial
    "tipo_cambio": Decimal("1.0000")
}

# Indicadores de presencia válidos según SIFEN
INDICADORES_PRESENCIA_VALIDOS = {
    "1": "Operación presencial",
    "2": "No presencial - Entrega domicilio",
    "3": "No presencial - Punto fijo",
    "4": "No presencial - Otro tipo"
}

# Tipos de IVA válidos
TIPOS_IVA_VALIDOS = ["exento", "exonerado", "5", "10"]

# ===============================================
# MIXIN PRINCIPAL
# ===============================================


class DocumentTypesT1Mixin:
    """
    Mixin para operaciones específicas de Facturas Electrónicas (FE - Tipo 1).

    Proporciona métodos especializados para el manejo de facturas electrónicas:
    - Creación con validaciones específicas
    - Búsquedas optimizadas para facturas
    - Validaciones de IVA y reglas fiscales
    - Estadísticas de ventas específicas
    - Integración con SIFEN v150

    Este mixin debe ser usado junto con DocumentoRepositoryBase para
    obtener funcionalidad completa de gestión de documentos.

    Example:
        ```python
        class DocumentoRepository(
            DocumentoRepositoryBase,
            DocumentTypesT1Mixin,
            # otros mixins...
        ):
            pass

        repo = DocumentoRepository(db)
        factura = repo.create_factura_electronica(data, items)
        ```
    """

    db: Session
    model: type

    # ===============================================
    # MÉTODOS DE CREACIÓN ESPECÍFICOS
    # ===============================================

    def create_factura_electronica(self,
                                   factura_data: Union[DocumentoCreateDTO, Dict[str, Any]],
                                   items: List[Dict[str, Any]],
                                   apply_defaults: bool = True,
                                   validate_iva: bool = True,
                                   auto_generate_cdc: bool = True,
                                   empresa_id: Optional[int] = None) -> FacturaElectronica:
        """
        Crea una factura electrónica con validaciones específicas.

        Este método es el punto de entrada principal para crear facturas electrónicas,
        aplicando todas las validaciones y configuraciones específicas del tipo de documento.

        Args:
            factura_data: Datos básicos de la factura
            items: Lista de items/productos de la factura
            apply_defaults: Aplicar configuraciones por defecto específicas
            validate_iva: Validar cálculos de IVA automáticamente
            auto_generate_cdc: Generar CDC automáticamente
            empresa_id: ID de empresa (opcional, para validaciones adicionales)

        Returns:
            FacturaElectronica: Instancia de factura creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio
            SifenDuplicateEntityError: Si la numeración ya existe

        Example:
            ```python
            factura_data = {
                "establecimiento": "001",
                "punto_expedicion": "001",
                "numero_documento": "0000123",
                "cliente_id": 456,
                "numero_timbrado": "12345678",
                "fecha_emision": date.today(),
                "moneda": "PYG"
            }

            items = [{
                "descripcion": "Producto A",
                "cantidad": 2,
                "precio_unitario": Decimal("550000"),
                "tipo_iva": "10"
            }]

            factura = repo.create_factura_electronica(factura_data, items)
            ```
        """
        start_time = datetime.now()

        try:
            # 1. Preparar datos base
            if isinstance(factura_data, DocumentoCreateDTO):
                data_dict = factura_data.dict()
            else:
                data_dict = factura_data.copy()

            # 2. Aplicar defaults específicos de facturas
            if apply_defaults:
                self._apply_factura_defaults(data_dict)

            # 3. Validar estructura básica y reglas de negocio
            self.validate_factura_data(data_dict, items)

            # 4. Validar cálculos de IVA si se solicita
            if validate_iva:
                self.validate_iva_requirements(data_dict, items)

            # 5. Calcular totales automáticamente desde items
            calculate_totals_from_items(data_dict, items)

            # 6. Aplicar validaciones adicionales por empresa
            if empresa_id:
                data_dict["empresa_id"] = empresa_id

            # 7. Crear documento usando método base del repository
            factura = getattr(self, 'create')(
                data_dict, auto_generate_fields=auto_generate_cdc)

            # 8. Crear items asociados a la factura
            if items:
                create_items_for_document(self.db, factura, items)

            # 9. Log de operación exitosa
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("create_factura_electronica", duration, 1)

            log_repository_operation("create_factura_electronica", "FacturaElectronica",
                                     getattr(factura, 'id', None), {
                                         "numero_completo": getattr(factura, 'numero_completo', None),
                                         "total_general": float(getattr(factura, 'total_general', 0)),
                                         "items_count": len(items),
                                         "cliente_id": getattr(factura, 'cliente_id', None)
                                     })

            return factura

        except (SifenValidationError, SifenBusinessLogicError, SifenDuplicateEntityError):
            # Re-raise errores de validación/negocio sin modificar
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(
                e, "create_factura_electronica", "FacturaElectronica")
            raise handle_database_exception(e, "create_factura_electronica")

    def create_factura_with_defaults(self,
                                     numero_documento: str,
                                     cliente_id: int,
                                     items: List[Dict[str, Any]],
                                     empresa_id: Optional[int] = None,
                                     observaciones: Optional[str] = None) -> FacturaElectronica:
        """
        Creación rápida de factura con configuraciones estándar.

        Método de conveniencia para crear facturas con configuraciones por defecto,
        ideal para operaciones simples y comunes.

        Args:
            numero_documento: Número secuencial del documento
            cliente_id: ID del cliente receptor
            items: Lista de items de la factura
            empresa_id: ID de empresa emisora
            observaciones: Observaciones opcionales

        Returns:
            FacturaElectronica: Factura creada con defaults

        Example:
            ```python
            items = [{
                "descripcion": "Servicio estándar",
                "cantidad": 1,
                "precio_unitario": Decimal("1100000"),
                "tipo_iva": "10"
            }]

            factura = repo.create_factura_with_defaults(
                numero_documento="0000124",
                cliente_id=789,
                items=items,
                empresa_id=1
            )
            ```
        """
        # TODO: Obtener datos de empresa para establecimiento y timbrado
        factura_data = {
            "establecimiento": "001",  # TODO: Desde configuración empresa
            "punto_expedicion": "001",  # TODO: Desde configuración empresa
            "numero_documento": numero_documento,
            "cliente_id": cliente_id,
            "numero_timbrado": "12345678",  # TODO: Desde timbrado activo
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),  # TODO: Desde timbrado
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),  # TODO: Desde timbrado
            "timbrado_id": 1,  # TODO: Desde timbrado activo
        }

        if empresa_id:
            factura_data["empresa_id"] = empresa_id

        if observaciones:
            factura_data["observaciones"] = observaciones

        return self.create_factura_electronica(
            factura_data=factura_data,
            items=items,
            apply_defaults=True,
            validate_iva=True,
            auto_generate_cdc=True
        )

    def create_factura_from_template(self,
                                     template_id: int,
                                     nuevo_numero: str,
                                     cliente_id: Optional[int] = None,
                                     modificaciones: Optional[Dict[str, Any]] = None) -> FacturaElectronica:
        """
        Crea una factura basada en una plantilla o factura anterior.

        Útil para operaciones recurrentes donde se quiere reutilizar
        la estructura de una factura anterior.

        Args:
            template_id: ID de la factura plantilla
            nuevo_numero: Nuevo número de documento
            cliente_id: Nuevo cliente (opcional, usa el de la plantilla)
            modificaciones: Campos a modificar del template

        Returns:
            FacturaElectronica: Nueva factura basada en template

        Raises:
            SifenEntityNotFoundError: Si la plantilla no existe
        """
        try:
            # Obtener factura plantilla
            template = getattr(self, 'get_by_id')(template_id)
            if not template or getattr(template, 'tipo_documento', '') != "1":
                raise SifenEntityNotFoundError("Factura template", template_id)

            # Copiar datos básicos
            factura_data = {
                "establecimiento": getattr(template, 'establecimiento', '001'),
                "punto_expedicion": getattr(template, 'punto_expedicion', '001'),
                "numero_documento": nuevo_numero,
                "cliente_id": cliente_id or getattr(template, 'cliente_id'),
                "numero_timbrado": getattr(template, 'numero_timbrado', ''),
                "fecha_emision": date.today(),
                "empresa_id": getattr(template, 'empresa_id'),
                "moneda": getattr(template, 'moneda', 'PYG'),
                "tipo_operacion": getattr(template, 'tipo_operacion', '1'),
                "condicion_operacion": getattr(template, 'condicion_operacion', '1'),
                "observaciones": getattr(template, 'observaciones', ''),
                # TODO: Obtener timbrado activo actual
                "timbrado_id": getattr(template, 'timbrado_id', 1),
                "fecha_inicio_vigencia_timbrado": date.today(),
                "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365)
            }

            # Aplicar modificaciones si se especifican
            if modificaciones:
                factura_data.update(modificaciones)

            # TODO: Obtener items del template
            items = []  # Por ahora vacío hasta implementar tabla de items

            return self.create_factura_electronica(factura_data, items)

        except SifenEntityNotFoundError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "create_factura_from_template", "FacturaElectronica", template_id)
            raise handle_database_exception(e, "create_factura_from_template")

    # ===============================================
    # VALIDACIONES ESPECÍFICAS
    # ===============================================

    def validate_factura_data(self,
                              factura_data: Dict[str, Any],
                              items: List[Dict[str, Any]]) -> None:
        """
        Validaciones comprehensivas específicas para facturas electrónicas.

        Aplica todas las validaciones requeridas para una factura según
        las normativas SIFEN y reglas de negocio específicas.

        Args:
            factura_data: Datos de la factura a validar
            items: Items de la factura a validar

        Raises:
            SifenValidationError: Si alguna validación falla

        Example:
            ```python
            try:
                repo.validate_factura_data(factura_data, items)
                print("Datos válidos")
            except SifenValidationError as e:
                print(f"Error de validación: {e.message}")
            ```
        """
        # Usar validación de auxiliares como base
        validate_factura_data(factura_data)

        # Validaciones adicionales específicas de facturas

        # 1. Cliente obligatorio
        if not factura_data.get("cliente_id"):
            raise SifenValidationError(
                "Cliente es obligatorio para facturas electrónicas",
                field="cliente_id"
            )

        # 2. Items obligatorios
        if not items or len(items) == 0:
            raise SifenValidationError(
                "Facturas deben tener al menos 1 item",
                field="items"
            )

        # 3. Validar cada item
        for i, item in enumerate(items):
            self._validate_factura_item(item, i)

        # 4. Validar indicador de presencia
        indicador_presencia = factura_data.get("indicador_presencia", "1")
        if indicador_presencia not in INDICADORES_PRESENCIA_VALIDOS:
            raise SifenValidationError(
                f"Indicador de presencia debe ser uno de: {list(INDICADORES_PRESENCIA_VALIDOS.keys())}",
                field="indicador_presencia",
                value=indicador_presencia
            )

        # 5. Validar tipo de operación para facturas
        tipo_operacion = factura_data.get("tipo_operacion", "1")
        if tipo_operacion not in ["1", "2"]:  # Venta o Exportación
            raise SifenValidationError(
                "Facturas solo pueden ser de tipo Venta (1) o Exportación (2)",
                field="tipo_operacion",
                value=tipo_operacion
            )

    def validate_iva_requirements(self,
                                  factura_data: Dict[str, Any],
                                  items: List[Dict[str, Any]]) -> None:
        """
        Validaciones específicas de IVA para facturas electrónicas.

        Verifica que los cálculos de IVA sean correctos y coherentes
        con los items de la factura.

        Args:
            factura_data: Datos de la factura
            items: Items con información de IVA

        Raises:
            SifenValidationError: Si los cálculos de IVA no son correctos
        """
        # Calcular totales esperados desde items
        totales_calculados = self._calculate_totals_from_items(items)

        # Validar subtotales si están especificados
        campos_a_validar = [
            ("subtotal_exento", "subtotal_exento"),
            ("subtotal_exonerado", "subtotal_exonerado"),
            ("subtotal_gravado_5", "subtotal_5"),
            ("subtotal_gravado_10", "subtotal_10"),
            ("total_iva", "total_iva")
        ]

        for campo_factura, campo_calculado in campos_a_validar:
            if campo_factura in factura_data:
                valor_factura = Decimal(str(factura_data[campo_factura]))
                valor_calculado = totales_calculados[campo_calculado]

                if abs(valor_factura - valor_calculado) > Decimal("0.01"):
                    raise SifenValidationError(
                        f"{campo_factura} no coincide con cálculo desde items. "
                        f"Esperado: {valor_calculado}, Recibido: {valor_factura}",
                        field=campo_factura,
                        value=valor_factura
                    )

        # Validar total general
        if "total_general" in factura_data:
            total_factura = Decimal(str(factura_data["total_general"]))
            total_calculado = totales_calculados["total_general"]

            if abs(total_factura - total_calculado) > Decimal("0.01"):
                raise SifenValidationError(
                    f"Total general no coincide con cálculo desde items. "
                    f"Esperado: {total_calculado}, Recibido: {total_factura}",
                    field="total_general",
                    value=total_factura
                )

    def validate_presence_indicator(self, indicador: str) -> bool:
        """
        Valida indicador de presencia del comprador según SIFEN.

        Args:
            indicador: Código de indicador de presencia

        Returns:
            bool: True si es válido

        Example:
            ```python
            is_valid = repo.validate_presence_indicator("1")  # True
            is_valid = repo.validate_presence_indicator("5")  # False
            ```
        """
        return indicador in INDICADORES_PRESENCIA_VALIDOS

    def validate_commercial_conditions(self, factura_data: Dict[str, Any]) -> None:
        """
        Valida condiciones comerciales específicas de facturas.

        Args:
            factura_data: Datos de la factura a validar

        Raises:
            SifenValidationError: Si las condiciones no son válidas
        """
        # Validar condición de operación
        condicion = factura_data.get("condicion_operacion", "1")
        if condicion not in ["1", "2"]:  # Contado o Crédito
            raise SifenValidationError(
                "Condición de operación debe ser Contado (1) o Crédito (2)",
                field="condicion_operacion",
                value=condicion
            )

        # Si es a crédito, validar información adicional
        if condicion == "2":
            # TODO: Validar información de crédito cuando esté disponible
            pass

    # ===============================================
    # BÚSQUEDAS ESPECIALIZADAS
    # ===============================================

    def get_facturas_by_criteria(self,
                                 empresa_id: int,
                                 fecha_desde: Optional[date] = None,
                                 fecha_hasta: Optional[date] = None,
                                 cliente_id: Optional[int] = None,
                                 monto_minimo: Optional[Decimal] = None,
                                 monto_maximo: Optional[Decimal] = None,
                                 estados: Optional[List[str]] = None,
                                 con_iva: Optional[bool] = None,
                                 moneda: Optional[str] = None,
                                 include_items: bool = False,
                                 limit: Optional[int] = None,
                                 offset: int = 0) -> List[FacturaElectronica]:
        """
        Búsqueda avanzada de facturas con múltiples criterios.

        Permite filtrar facturas por diversos criterios específicos del negocio,
        optimizado para consultas frecuentes en dashboards y reportes.

        Args:
            empresa_id: ID de la empresa emisora
            fecha_desde: Fecha inicio del rango (opcional)
            fecha_hasta: Fecha fin del rango (opcional)
            cliente_id: ID del cliente específico (opcional)
            monto_minimo: Monto mínimo de la factura (opcional)
            monto_maximo: Monto máximo de la factura (opcional)
            estados: Lista de estados a incluir (opcional)
            con_iva: Filtrar solo facturas con IVA > 0 (opcional)
            moneda: Filtrar por tipo de moneda (opcional)
            include_items: Incluir items en el resultado (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[FacturaElectronica]: Lista de facturas que cumplen criterios

        Example:
            ```python
            # Facturas del mes con IVA en PYG
            facturas = repo.get_facturas_by_criteria(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31),
                con_iva=True,
                moneda="PYG",
                estados=["aprobado"]
            )
            ```
        """
        start_time = datetime.now()

        try:
            # Usar helper de auxiliares como base
            facturas = get_documents_by_type_and_criteria(
                self.db, self.model, "1", empresa_id,
                fecha_desde, fecha_hasta, monto_minimo, monto_maximo,
                estados, limit, offset
            )

            # Aplicar filtros específicos de facturas
            query = self.db.query(FacturaElectronica).filter(
                and_(
                    FacturaElectronica.tipo_documento == "1",
                    FacturaElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtros opcionales
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, FacturaElectronica.fecha_emision, fecha_desde, fecha_hasta)

            if monto_minimo or monto_maximo:
                query = build_amount_filter(
                    query, FacturaElectronica.total_general, monto_minimo, monto_maximo)

            if cliente_id:
                query = query.filter(
                    FacturaElectronica.cliente_id == cliente_id)

            if estados:
                query = query.filter(text("estado IN :estados")).params(
                    estados=tuple(estados))

            if con_iva is not None:
                if con_iva:
                    query = query.filter(FacturaElectronica.total_iva > 0)
                else:
                    query = query.filter(FacturaElectronica.total_iva == 0)

            if moneda:
                query = query.filter(FacturaElectronica.moneda == moneda)

            # Incluir items si se solicita
            if include_items:
                # TODO: Implementar cuando tabla de items esté disponible
                # query = query.options(joinedload(FacturaElectronica.items))
                pass

            # Aplicar límites y ordenamiento
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            facturas = query.order_by(desc(FacturaElectronica.fecha_emision)).offset(
                offset).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_facturas_by_criteria", duration, len(facturas))

            return facturas

        except Exception as e:
            handle_repository_error(
                e, "get_facturas_by_criteria", "FacturaElectronica")
            raise handle_database_exception(e, "get_facturas_by_criteria")

    def get_facturas_by_client(self,
                               cliente_id: int,
                               empresa_id: Optional[int] = None,
                               fecha_desde: Optional[date] = None,
                               fecha_hasta: Optional[date] = None,
                               limit: Optional[int] = None) -> List[FacturaElectronica]:
        """
        Obtiene todas las facturas de un cliente específico.

        Args:
            cliente_id: ID del cliente
            empresa_id: ID de empresa (opcional, para filtrar)
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)
            limit: Límite de resultados

        Returns:
            List[FacturaElectronica]: Facturas del cliente
        """
        return self.get_facturas_by_criteria(
            empresa_id=empresa_id or 0,  # TODO: Obtener desde contexto
            cliente_id=cliente_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limit=limit
        )

    def get_facturas_by_amount_range(self,
                                     monto_minimo: Decimal,
                                     monto_maximo: Decimal,
                                     empresa_id: int,
                                     moneda: str = "PYG") -> List[FacturaElectronica]:
        """
        Búsqueda de facturas por rango de montos.

        Args:
            monto_minimo: Monto mínimo
            monto_maximo: Monto máximo
            empresa_id: ID de empresa
            moneda: Tipo de moneda

        Returns:
            List[FacturaElectronica]: Facturas en el rango
        """
        return self.get_facturas_by_criteria(
            empresa_id=empresa_id,
            monto_minimo=monto_minimo,
            monto_maximo=monto_maximo,
            moneda=moneda
        )

    def get_facturas_by_iva_type(self,
                                 tipo_iva: str,
                                 empresa_id: int,
                                 fecha_desde: Optional[date] = None,
                                 fecha_hasta: Optional[date] = None) -> List[FacturaElectronica]:
        """
        Filtra facturas por tipo de IVA.

        Args:
            tipo_iva: Tipo de IVA ("gravadas", "exentas", "exoneradas")
            empresa_id: ID de empresa
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)

        Returns:
            List[FacturaElectronica]: Facturas filtradas por IVA
        """
        if tipo_iva == "gravadas":
            return self.get_facturas_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                con_iva=True
            )
        elif tipo_iva == "exentas":
            # TODO: Implementar filtro para facturas exentas
            return self.get_facturas_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                con_iva=False
            )
        else:
            # Todas las facturas
            return self.get_facturas_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )

    # ===============================================
    # REPORTES Y ESTADÍSTICAS
    # ===============================================

    def get_factura_stats(self,
                          empresa_id: int,
                          fecha_desde: Optional[date] = None,
                          fecha_hasta: Optional[date] = None,
                          periodo: str = "monthly") -> Dict[str, Any]:
        """
        Estadísticas específicas de facturas para una empresa.

        Genera métricas detalladas de facturas para reportes ejecutivos
        y análisis de ventas.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período (opcional)
            fecha_hasta: Fecha fin del período (opcional)
            periodo: Tipo de período para agregación (daily, weekly, monthly)

        Returns:
            Dict[str, Any]: Estadísticas detalladas de facturas

        Example:
            ```python
            stats = repo.get_factura_stats(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            print(f"Total facturado: {stats['monto_total_facturado']}")
            ```
        """
        start_time = datetime.now()

        try:
            # Construir query base
            query = self.db.query(FacturaElectronica).filter(
                and_(
                    FacturaElectronica.tipo_documento == "1",
                    FacturaElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtro de fechas
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, FacturaElectronica.fecha_emision, fecha_desde, fecha_hasta)

            # Obtener todas las facturas del período
            facturas = query.all()

            # Calcular estadísticas básicas
            total_facturas = len(facturas)

            if total_facturas == 0:
                return self._get_empty_stats()

            # Calcular totales
            monto_total = sum(getattr(f, 'total_general', Decimal("0"))
                              for f in facturas)
            monto_iva = sum(getattr(f, 'total_iva', Decimal("0"))
                            for f in facturas)
            promedio_factura = monto_total / \
                total_facturas if total_facturas > 0 else Decimal("0")

            # Contar por estado
            facturas_por_estado = {}
            for factura in facturas:
                estado = getattr(factura, 'estado', 'unknown')
                facturas_por_estado[estado] = facturas_por_estado.get(
                    estado, 0) + 1

            # Contar facturas gravadas vs exentas
            facturas_gravadas = sum(
                1 for f in facturas if getattr(f, 'total_iva', 0) > 0)
            facturas_exentas = total_facturas - facturas_gravadas

            # Obtener clientes únicos
            clientes_unicos = len(
                set(getattr(f, 'cliente_id', 0) for f in facturas))

            # Distribución por montos (rangos)
            distribucion_montos = self._calculate_amount_distribution(facturas)

            # Agregación por período si se solicita
            datos_por_periodo = {}
            if periodo and facturas:
                datos_periodo = [
                    {
                        "fecha": getattr(f, 'fecha_emision', date.today()),
                        "monto": float(getattr(f, 'total_general', 0))
                    }
                    for f in facturas
                ]
                datos_por_periodo = aggregate_by_period(
                    datos_periodo, "fecha", "monto", periodo)

            # Estadísticas de performance
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("get_factura_stats",
                                   duration, total_facturas)

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                    "tipo_periodo": periodo
                },
                "totales": {
                    "total_facturas": total_facturas,
                    "monto_total_facturado": float(monto_total),
                    "monto_total_iva": float(monto_iva),
                    "promedio_por_factura": float(promedio_factura)
                },
                "distribucion_iva": {
                    "facturas_gravadas": facturas_gravadas,
                    "facturas_exentas": facturas_exentas,
                    "porcentaje_gravadas": calculate_percentage(facturas_gravadas, total_facturas),
                    "iva_promedio": float(monto_iva / facturas_gravadas) if facturas_gravadas > 0 else 0.0
                },
                "clientes": {
                    "clientes_unicos": clientes_unicos,
                    "promedio_facturas_por_cliente": round(total_facturas / clientes_unicos, 2) if clientes_unicos > 0 else 0
                },
                "estados": facturas_por_estado,
                "distribucion_montos": distribucion_montos,
                "datos_por_periodo": datos_por_periodo,
                "metadatos": {
                    "generado_en": datetime.now().isoformat(),
                    "tiempo_procesamiento": round(duration, 3)
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_factura_stats", "FacturaElectronica")
            raise handle_database_exception(e, "get_factura_stats")

    def get_iva_summary(self,
                        empresa_id: int,
                        fecha_desde: date,
                        fecha_hasta: date) -> Dict[str, Any]:
        """
        Resumen de IVA facturado por período.

        Genera un resumen detallado del IVA liquidado en facturas
        para reportes fiscales y declaraciones.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Resumen detallado de IVA

        Example:
            ```python
            resumen_iva = repo.get_iva_summary(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            ```
        """
        try:
            # Obtener facturas del período
            facturas = self.get_facturas_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                estados=["aprobado", "aprobado_observacion"]  # Solo fiscales
            )

            # Calcular totales por tipo de IVA
            subtotal_5 = sum(getattr(f, 'subtotal_gravado_5',
                             Decimal("0")) for f in facturas)
            subtotal_10 = sum(getattr(f, 'subtotal_gravado_10',
                              Decimal("0")) for f in facturas)
            subtotal_exento = sum(
                getattr(f, 'subtotal_exento', Decimal("0")) for f in facturas)
            subtotal_exonerado = sum(
                getattr(f, 'subtotal_exonerado', Decimal("0")) for f in facturas)

            # Calcular IVA por tasa
            iva_5 = subtotal_5 * Decimal("0.05")
            iva_10 = subtotal_10 * Decimal("0.10")
            total_iva = iva_5 + iva_10

            # Totales generales
            total_operaciones = subtotal_5 + subtotal_10 + \
                subtotal_exento + subtotal_exonerado
            total_con_iva = total_operaciones + total_iva

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "dias": (fecha_hasta - fecha_desde).days + 1
                },
                "subtotales": {
                    "gravado_5": float(subtotal_5),
                    "gravado_10": float(subtotal_10),
                    "exento": float(subtotal_exento),
                    "exonerado": float(subtotal_exonerado),
                    "total_operaciones": float(total_operaciones)
                },
                "iva_liquidado": {
                    "iva_5_porciento": float(iva_5),
                    "iva_10_porciento": float(iva_10),
                    "total_iva": float(total_iva)
                },
                "totales": {
                    "total_con_iva": float(total_con_iva),
                    "total_facturas": len(facturas)
                },
                "promedios": {
                    "iva_promedio_diario": float(total_iva / ((fecha_hasta - fecha_desde).days + 1)),
                    "operaciones_promedio_diario": float(total_operaciones / ((fecha_hasta - fecha_desde).days + 1))
                }
            }

        except Exception as e:
            handle_repository_error(e, "get_iva_summary", "FacturaElectronica")
            raise handle_database_exception(e, "get_iva_summary")

    def get_sales_trends(self,
                         empresa_id: int,
                         meses_atras: int = 6) -> Dict[str, Any]:
        """
        Tendencias de ventas y análisis temporal.

        Analiza las tendencias de ventas de facturas en los últimos meses
        para identificar patrones y proyecciones.

        Args:
            empresa_id: ID de la empresa
            meses_atras: Número de meses hacia atrás a analizar

        Returns:
            Dict[str, Any]: Análisis de tendencias

        Example:
            ```python
            tendencias = repo.get_sales_trends(empresa_id=1, meses_atras=12)
            ```
        """
        try:
            # Calcular fechas del análisis
            fecha_fin = date.today()
            fecha_inicio = fecha_fin.replace(
                day=1) - timedelta(days=meses_atras*30)

            # Obtener facturas del período
            facturas = self.get_facturas_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_inicio,
                fecha_hasta=fecha_fin,
                estados=["aprobado", "aprobado_observacion"]
            )

            # Agrupar por mes
            ventas_por_mes = {}
            for factura in facturas:
                fecha_emision = getattr(factura, 'fecha_emision', date.today())
                mes_key = fecha_emision.strftime("%Y-%m")

                if mes_key not in ventas_por_mes:
                    ventas_por_mes[mes_key] = {
                        "cantidad": 0,
                        "monto": Decimal("0"),
                        "iva": Decimal("0")
                    }

                ventas_por_mes[mes_key]["cantidad"] += 1
                ventas_por_mes[mes_key]["monto"] += getattr(
                    factura, 'total_general', Decimal("0"))
                ventas_por_mes[mes_key]["iva"] += getattr(
                    factura, 'total_iva', Decimal("0"))

            # Calcular tendencias
            meses_ordenados = sorted(ventas_por_mes.keys())

            # Crecimiento mes a mes
            crecimiento_cantidad = []
            crecimiento_monto = []

            for i in range(1, len(meses_ordenados)):
                mes_actual = meses_ordenados[i]
                mes_anterior = meses_ordenados[i-1]

                cant_actual = ventas_por_mes[mes_actual]["cantidad"]
                cant_anterior = ventas_por_mes[mes_anterior]["cantidad"]

                monto_actual = ventas_por_mes[mes_actual]["monto"]
                monto_anterior = ventas_por_mes[mes_anterior]["monto"]

                crec_cant = calculate_percentage(
                    cant_actual - cant_anterior, cant_anterior) if cant_anterior > 0 else 0
                crec_monto = float((monto_actual - monto_anterior) /
                                   monto_anterior * 100) if monto_anterior > 0 else 0

                crecimiento_cantidad.append(
                    {"mes": mes_actual, "crecimiento": crec_cant})
                crecimiento_monto.append(
                    {"mes": mes_actual, "crecimiento": crec_monto})

            # Promedios
            total_meses = len(meses_ordenados)
            promedio_cantidad = sum(v["cantidad"] for v in ventas_por_mes.values(
            )) / total_meses if total_meses > 0 else 0
            promedio_monto = sum(v["monto"] for v in ventas_por_mes.values(
            )) / total_meses if total_meses > 0 else Decimal("0")

            return {
                "periodo_analisis": {
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": fecha_fin.isoformat(),
                    "meses_analizados": total_meses
                },
                "ventas_por_mes": {
                    mes: {
                        "cantidad": datos["cantidad"],
                        "monto": float(datos["monto"]),
                        "iva": float(datos["iva"])
                    }
                    for mes, datos in ventas_por_mes.items()
                },
                "tendencias": {
                    "crecimiento_cantidad": crecimiento_cantidad,
                    "crecimiento_monto": crecimiento_monto
                },
                "promedios": {
                    "cantidad_mensual": round(promedio_cantidad, 2),
                    "monto_mensual": float(promedio_monto)
                },
                "totales_periodo": {
                    "total_facturas": len(facturas),
                    "total_facturado": float(sum(getattr(f, 'total_general', 0) for f in facturas)),
                    "total_iva": float(sum(getattr(f, 'total_iva', 0) for f in facturas))
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_sales_trends", "FacturaElectronica")
            raise handle_database_exception(e, "get_sales_trends")

    # ===============================================
    # HELPERS INTERNOS
    # ===============================================

    def _apply_factura_defaults(self, data: Dict[str, Any]) -> None:
        """
        Aplica configuraciones por defecto específicas de facturas.

        Args:
            data: Diccionario de datos a modificar in-place
        """
        # Aplicar defaults base desde auxiliares
        apply_default_config(data, "1")  # Tipo 1 = Factura

        # Aplicar defaults específicos adicionales
        for key, default_value in FACTURA_DEFAULTS.items():
            if key not in data or data[key] is None:
                data[key] = default_value

        # Configuraciones especiales
        if "fecha_emision" not in data:
            data["fecha_emision"] = date.today()

        if "estado" not in data:
            data["estado"] = EstadoDocumentoSifenEnum.BORRADOR.value

    def _validate_factura_item(self, item: Dict[str, Any], index: int) -> None:
        """
        Valida un item individual de la factura.

        Args:
            item: Datos del item a validar
            index: Índice del item en la lista

        Raises:
            SifenValidationError: Si el item no es válido
        """
        # Campos requeridos en items
        required_fields = ["descripcion", "cantidad", "precio_unitario"]

        for field in required_fields:
            if field not in item or item[field] is None:
                raise SifenValidationError(
                    f"Campo requerido en item {index + 1}: {field}",
                    field=f"items[{index}].{field}"
                )

        # Validar cantidad positiva
        try:
            cantidad = Decimal(str(item["cantidad"]))
            if cantidad <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise SifenValidationError(
                f"Cantidad debe ser un número positivo en item {index + 1}",
                field=f"items[{index}].cantidad",
                value=item.get("cantidad")
            )

        # Validar precio unitario
        try:
            precio = Decimal(str(item["precio_unitario"]))
            if precio < 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise SifenValidationError(
                f"Precio unitario debe ser un número no negativo en item {index + 1}",
                field=f"items[{index}].precio_unitario",
                value=item.get("precio_unitario")
            )

        # Validar tipo de IVA si está presente
        if "tipo_iva" in item:
            tipo_iva = item["tipo_iva"]
            if tipo_iva not in TIPOS_IVA_VALIDOS:
                raise SifenValidationError(
                    f"Tipo de IVA inválido en item {index + 1}. Válidos: {TIPOS_IVA_VALIDOS}",
                    field=f"items[{index}].tipo_iva",
                    value=tipo_iva
                )

    def _calculate_totals_from_items(self, items: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """
        Calcula totales desde una lista de items.

        Args:
            items: Lista de items con precios e IVA

        Returns:
            Dict[str, Decimal]: Totales calculados
        """
        totales = {
            "subtotal_exento": Decimal("0"),
            "subtotal_exonerado": Decimal("0"),
            "subtotal_5": Decimal("0"),
            "subtotal_10": Decimal("0"),
            "total_iva": Decimal("0"),
            "total_operacion": Decimal("0"),
            "total_general": Decimal("0")
        }

        for item in items:
            cantidad = Decimal(str(item.get("cantidad", 0)))
            precio_unitario = Decimal(str(item.get("precio_unitario", 0)))
            tipo_iva = item.get("tipo_iva", "10")

            subtotal_item = cantidad * precio_unitario

            if tipo_iva == "exento":
                totales["subtotal_exento"] += subtotal_item
            elif tipo_iva == "exonerado":
                totales["subtotal_exonerado"] += subtotal_item
            elif tipo_iva == "5":
                totales["subtotal_5"] += subtotal_item
                totales["total_iva"] += subtotal_item * Decimal("0.05")
            else:  # "10" por defecto
                totales["subtotal_10"] += subtotal_item
                totales["total_iva"] += subtotal_item * Decimal("0.10")

        totales["total_operacion"] = (
            totales["subtotal_exento"] +
            totales["subtotal_exonerado"] +
            totales["subtotal_5"] +
            totales["subtotal_10"]
        )

        totales["total_general"] = totales["total_operacion"] + \
            totales["total_iva"]

        return totales

    def _get_empty_stats(self) -> Dict[str, Any]:
        """
        Retorna estructura de estadísticas vacía.

        Returns:
            Dict[str, Any]: Estadísticas con valores en cero
        """
        return {
            "periodo": {
                "fecha_desde": None,
                "fecha_hasta": None,
                "tipo_periodo": "monthly"
            },
            "totales": {
                "total_facturas": 0,
                "monto_total_facturado": 0.0,
                "monto_total_iva": 0.0,
                "promedio_por_factura": 0.0
            },
            "distribucion_iva": {
                "facturas_gravadas": 0,
                "facturas_exentas": 0,
                "porcentaje_gravadas": 0.0,
                "iva_promedio": 0.0
            },
            "clientes": {
                "clientes_unicos": 0,
                "promedio_facturas_por_cliente": 0.0
            },
            "estados": {},
            "distribucion_montos": {},
            "datos_por_periodo": {},
            "metadatos": {
                "generado_en": datetime.now().isoformat(),
                "tiempo_procesamiento": 0.0
            }
        }

    def _calculate_amount_distribution(self, facturas: List[FacturaElectronica]) -> Dict[str, int]:
        """
        Calcula distribución de facturas por rangos de montos.

        Args:
            facturas: Lista de facturas a analizar

        Returns:
            Dict[str, int]: Distribución por rangos
        """
        # Definir rangos de montos (en guaraníes)
        rangos = {
            "0-100K": (0, 100000),
            "100K-500K": (100000, 500000),
            "500K-1M": (500000, 1000000),
            "1M-5M": (1000000, 5000000),
            "5M-10M": (5000000, 10000000),
            "10M+": (10000000, float('inf'))
        }

        distribucion = {rango: 0 for rango in rangos.keys()}

        for factura in facturas:
            monto = float(getattr(factura, 'total_general', 0))

            for rango, (minimo, maximo) in rangos.items():
                if minimo <= monto < maximo:
                    distribucion[rango] += 1
                    break

        return distribucion

    def _format_factura_response(self, factura: FacturaElectronica, include_details: bool = False) -> Dict[str, Any]:
        """
        Formatea respuesta con datos específicos de facturas.

        Args:
            factura: Instancia de factura a formatear
            include_details: Incluir detalles adicionales

        Returns:
            Dict[str, Any]: Factura formateada para respuesta
        """
        response = {
            "id": getattr(factura, 'id', None),
            "cdc": getattr(factura, 'cdc', ''),
            "numero_completo": getattr(factura, 'numero_completo', ''),
            "fecha_emision": getattr(factura, 'fecha_emision', date.today()).isoformat(),
            "cliente_id": getattr(factura, 'cliente_id', None),
            "total_general": float(getattr(factura, 'total_general', 0)),
            "total_iva": float(getattr(factura, 'total_iva', 0)),
            "moneda": getattr(factura, 'moneda', 'PYG'),
            "estado": getattr(factura, 'estado', 'unknown'),
            "tipo_documento": "Factura Electrónica"
        }

        if include_details:
            response.update({
                "subtotal_exento": float(getattr(factura, 'subtotal_exento', 0)),
                "subtotal_exonerado": float(getattr(factura, 'subtotal_exonerado', 0)),
                "subtotal_gravado_5": float(getattr(factura, 'subtotal_gravado_5', 0)),
                "subtotal_gravado_10": float(getattr(factura, 'subtotal_gravado_10', 0)),
                "total_operacion": float(getattr(factura, 'total_operacion', 0)),
                "tipo_operacion": getattr(factura, 'tipo_operacion', '1'),
                "condicion_operacion": getattr(factura, 'condicion_operacion', '1'),
                "observaciones": getattr(factura, 'observaciones', ''),
                "numero_protocolo": getattr(factura, 'numero_protocolo', ''),
                "fecha_creacion": getattr(factura, 'created_at', datetime.now()).isoformat(),
                "fecha_actualizacion": getattr(factura, 'updated_at', datetime.now()).isoformat()
            })

        return response


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "DocumentTypesT1Mixin",
    "FACTURA_DEFAULTS",
    "INDICADORES_PRESENCIA_VALIDOS",
    "TIPOS_IVA_VALIDOS"
]
