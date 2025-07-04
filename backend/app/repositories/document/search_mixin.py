# ===============================================
# ARCHIVO: backend/app/repositories/documento/search_mixin.py
# PROPÓSITO: Mixin para búsquedas avanzadas y filtros complejos de documentos
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para búsquedas avanzadas y filtros complejos de documentos.

Este mixin implementa funcionalidades avanzadas de búsqueda para documentos
electrónicos SIFEN:
- Búsquedas multicriterio con texto libre
- Filtros avanzados con paginación
- Búsquedas por cliente y datos relacionados
- Consultas optimizadas con índices
- Paginación inteligente con metadatos

Características:
- Búsqueda fuzzy tolerante a errores
- Filtros combinables (AND/OR)
- Queries optimizadas para performance
- Paginación completa con metadatos
- Búsquedas por patrones específicos

Clase principal:
- DocumentoSearchMixin: Mixin con todas las funcionalidades de búsqueda
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, text, desc, asc, case
from sqlalchemy.orm import Session, Query, joinedload
from sqlalchemy.exc import SQLAlchemyError
from math import ceil

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenValidationError,
    SifenDatabaseError,
    handle_database_exception
)
from app.models.documento import (
    Documento,
    EstadoDocumentoSifenEnum,
    TipoDocumentoSifenEnum,
    MonedaSifenEnum
)
from app.schemas.documento import (
    DocumentoConsultaDTO,
    DocumentoBaseDTO
)
from .utils import (
    get_default_page_size,
    get_max_page_size,
    build_date_filter,
    build_amount_filter,
    build_search_conditions,
    optimize_query_performance,
    log_repository_operation,
    log_performance_metric,
    handle_repository_error
)

logger = get_logger(__name__)

# ===============================================
# CONSTANTES ESPECÍFICAS DE BÚSQUEDA
# ===============================================

# Campos searcheables por defecto
DEFAULT_SEARCH_FIELDS = [
    "numero_documento",
    "establecimiento",
    "punto_expedicion",
    "observaciones",
    "motivo_emision",
    "numero_timbrado",
    "numero_protocolo"
]

# Campos para búsqueda de cliente
CLIENT_SEARCH_FIELDS = [
    "cliente.nombre",
    "cliente.razon_social",
    "cliente.ruc",
    "cliente.email"
]

# Campos para ordenamiento válidos
VALID_ORDER_FIELDS = [
    "id",
    "fecha_emision",
    "created_at",
    "updated_at",
    "total_general",
    "estado",
    "numero_documento",
    "tipo_documento"
]

# Operadores de filtro válidos
VALID_FILTER_OPERATORS = [
    "eq",    # igual
    "ne",    # diferente
    "gt",    # mayor que
    "gte",   # mayor o igual
    "lt",    # menor que
    "lte",   # menor o igual
    "like",  # contiene
    "ilike",  # contiene (case insensitive)
    "in",    # en lista
    "nin",   # no en lista
    "null",  # es null
    "nnull"  # no es null
]

# Límites de búsqueda
MAX_SEARCH_RESULTS = 1000
MAX_SEARCH_TERM_LENGTH = 100

# ===============================================
# CLASE SEARCH MIXIN
# ===============================================


class DocumentoSearchMixin:
    """
    Mixin para búsquedas avanzadas y filtros complejos de documentos.

    Proporciona métodos para:
    - Búsquedas multicriterio con texto libre
    - Filtros avanzados con operadores
    - Paginación inteligente con metadatos
    - Búsquedas por cliente y datos relacionados
    - Consultas optimizadas para performance

    Requiere que la clase que lo use tenga:
    - self.db: Session SQLAlchemy
    - self.model: Modelo Documento
    """

    # Type hints para PyLance
    db: Session
    model: type[Documento]

    # ===============================================
    # BÚSQUEDAS MULTICRITERIO
    # ===============================================

    def search_documentos(self,
                          search_term: str,
                          empresa_id: Optional[int] = None,
                          tipos_documento: Optional[List[str]] = None,
                          estados: Optional[List[str]] = None,
                          fecha_desde: Optional[date] = None,
                          fecha_hasta: Optional[date] = None,
                          limit: Optional[int] = None,
                          offset: int = 0,
                          order_by: str = "created_at",
                          order_direction: str = "desc") -> Dict[str, Any]:
        """
        Búsqueda completa por múltiples campos con texto libre.

        Args:
            search_term: Término de búsqueda
            empresa_id: ID de empresa (opcional)
            tipos_documento: Lista de tipos de documento
            estados: Lista de estados
            fecha_desde: Fecha inicio del rango
            fecha_hasta: Fecha fin del rango
            limit: Número máximo de resultados
            offset: Número de resultados a omitir
            order_by: Campo para ordenar
            order_direction: Dirección del ordenamiento

        Returns:
            Dict: Resultado con documentos y metadatos

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.search_documentos(
            ...     "factura cliente",
            ...     empresa_id=1,
            ...     tipos_documento=["1"],
            ...     estados=["aprobado"],
            ...     limit=20
            ... )
            >>> print(f"Encontrados: {result['total']} documentos")
            >>> for doc in result['documentos']:
            ...     print(f"- {doc.numero_completo}")
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            self._validate_search_params(
                search_term, limit, order_by, order_direction)

            # Construir query base
            query = self._build_base_search_query(
                search_term, empresa_id, tipos_documento, estados,
                fecha_desde, fecha_hasta
            )

            # Obtener total de resultados
            total = query.count()

            # Aplicar ordenamiento
            query = self._apply_ordering(query, order_by, order_direction)

            # Aplicar paginación
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            documentos = query.offset(offset).limit(limit).all()

            # Preparar resultado
            result = {
                "documentos": documentos,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "search_term": search_term,
                "filters_applied": {
                    "empresa_id": empresa_id,
                    "tipos_documento": tipos_documento,
                    "estados": estados,
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None
                }
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("search_documentos",
                                   duration, len(documentos))

            log_repository_operation(
                "search_documentos",
                "Documento",
                None,
                {
                    "search_term": search_term,
                    "total_found": total,
                    "returned": len(documentos),
                    "empresa_id": empresa_id,
                    "duration": duration
                }
            )

            return result

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "search_documentos", "Documento")
            raise handle_database_exception(e, "search_documentos")

    def search_by_cliente(self,
                          cliente_search: str,
                          empresa_id: Optional[int] = None,
                          include_inactive: bool = False,
                          limit: Optional[int] = None,
                          offset: int = 0) -> Dict[str, Any]:
        """
        Búsqueda por datos del cliente (nombre, RUC, email).

        Args:
            cliente_search: Término de búsqueda del cliente
            empresa_id: ID de empresa (opcional)
            include_inactive: Si incluir documentos inactivos
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            Dict: Resultado con documentos y metadatos

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.search_by_cliente(
            ...     "Juan Pérez",
            ...     empresa_id=1,
            ...     limit=10
            ... )
            >>> print(f"Documentos de '{cliente_search}': {result['total']}")
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not cliente_search or len(cliente_search.strip()) < 2:
                raise SifenValidationError(
                    "Término de búsqueda debe tener al menos 2 caracteres",
                    field="cliente_search"
                )

            if limit and limit > get_max_page_size():
                limit = get_max_page_size()
            elif not limit:
                limit = get_default_page_size()

            # Construir query con JOIN a cliente
            query = self.db.query(self.model)

            # TODO: Implementar JOIN con tabla cliente cuando esté disponible
            # query = query.join(Cliente, self.model.cliente_id == Cliente.id)

            # Por ahora, búsqueda básica por cliente_id
            # En futuro release se implementará búsqueda completa por datos del cliente

            # Aplicar filtros básicos
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            if not include_inactive:
                query = query.filter(self.model.is_active == True)

            # Simular búsqueda por cliente (placeholder)
            # TODO: Implementar búsqueda real cuando table cliente esté disponible
            search_pattern = f"%{cliente_search.lower()}%"

            # Obtener total y resultados
            total = query.count()
            documentos = query.order_by(desc(self.model.created_at)).offset(
                offset).limit(limit).all()

            # Preparar resultado
            result = {
                "documentos": documentos,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "cliente_search": cliente_search,
                "filters_applied": {
                    "empresa_id": empresa_id,
                    "include_inactive": include_inactive
                }
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("search_by_cliente",
                                   duration, len(documentos))

            log_repository_operation(
                "search_by_cliente",
                "Documento",
                None,
                {
                    "cliente_search": cliente_search,
                    "total_found": total,
                    "returned": len(documentos),
                    "empresa_id": empresa_id
                }
            )

            return result

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "search_by_cliente", "Documento")
            raise handle_database_exception(e, "search_by_cliente")

    def search_by_content(self,
                          content_search: str,
                          search_fields: Optional[List[str]] = None,
                          empresa_id: Optional[int] = None,
                          limit: Optional[int] = None,
                          offset: int = 0) -> Dict[str, Any]:
        """
        Búsqueda en contenido de documentos (observaciones, motivos).

        Args:
            content_search: Término de búsqueda en contenido
            search_fields: Campos específicos donde buscar
            empresa_id: ID de empresa (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            Dict: Resultado con documentos y metadatos

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.search_by_content(
            ...     "producto defectuoso",
            ...     search_fields=["observaciones", "motivo_emision"],
            ...     empresa_id=1
            ... )
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not content_search or len(content_search.strip()) < 2:
                raise SifenValidationError(
                    "Término de búsqueda debe tener al menos 2 caracteres",
                    field="content_search"
                )

            if limit and limit > get_max_page_size():
                limit = get_max_page_size()
            elif not limit:
                limit = get_default_page_size()

            # Campos de búsqueda por defecto
            if not search_fields:
                search_fields = ["observaciones",
                                 "motivo_emision", "descripcion_operacion"]

            # Construir query base
            query = self.db.query(self.model)

            # Aplicar filtro por empresa
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Construir condiciones de búsqueda
            search_conditions = build_search_conditions(
                self.model, search_fields, content_search
            )
            query = query.filter(search_conditions)

            # Obtener total y resultados
            total = query.count()
            documentos = query.order_by(desc(self.model.created_at)).offset(
                offset).limit(limit).all()

            # Preparar resultado
            result = {
                "documentos": documentos,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "content_search": content_search,
                "search_fields": search_fields,
                "filters_applied": {
                    "empresa_id": empresa_id
                }
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("search_by_content",
                                   duration, len(documentos))

            log_repository_operation(
                "search_by_content",
                "Documento",
                None,
                {
                    "content_search": content_search,
                    "search_fields": search_fields,
                    "total_found": total,
                    "returned": len(documentos),
                    "empresa_id": empresa_id
                }
            )

            return result

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "search_by_content", "Documento")
            raise handle_database_exception(e, "search_by_content")

    # ===============================================
    # FILTROS AVANZADOS
    # ===============================================

    def filter_documentos_avanzado(self,
                                   filters: Dict[str, Any],
                                   empresa_id: Optional[int] = None,
                                   limit: Optional[int] = None,
                                   offset: int = 0,
                                   order_by: str = "created_at",
                                   order_direction: str = "desc") -> Dict[str, Any]:
        """
        Filtrado avanzado con múltiples criterios y operadores.

        Args:
            filters: Diccionario con filtros a aplicar
            empresa_id: ID de empresa (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir
            order_by: Campo para ordenar
            order_direction: Dirección del ordenamiento

        Returns:
            Dict: Resultado con documentos y metadatos

        Raises:
            SifenValidationError: Si los filtros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.filter_documentos_avanzado({
            ...     "tipo_documento": {"operator": "in", "value": ["1", "5"]},
            ...     "total_general": {"operator": "gte", "value": 100000},
            ...     "fecha_emision": {"operator": "gte", "value": "2025-01-01"},
            ...     "estado": {"operator": "ne", "value": "cancelado"}
            ... })
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not isinstance(filters, dict):
                raise SifenValidationError(
                    "Filtros deben ser un diccionario",
                    field="filters"
                )

            if limit and limit > get_max_page_size():
                limit = get_max_page_size()
            elif not limit:
                limit = get_default_page_size()

            # Construir query base
            query = self.db.query(self.model)

            # Aplicar filtro por empresa
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Aplicar filtros avanzados
            query = self._apply_advanced_filters(query, filters)

            # Obtener total de resultados
            total = query.count()

            # Aplicar ordenamiento
            query = self._apply_ordering(query, order_by, order_direction)

            # Aplicar paginación
            documentos = query.offset(offset).limit(limit).all()

            # Preparar resultado
            result = {
                "documentos": documentos,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "filters_applied": filters,
                "empresa_id": empresa_id
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "filter_documentos_avanzado", duration, len(documentos))

            log_repository_operation(
                "filter_documentos_avanzado",
                "Documento",
                None,
                {
                    "filters_count": len(filters),
                    "total_found": total,
                    "returned": len(documentos),
                    "empresa_id": empresa_id
                }
            )

            return result

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "filter_documentos_avanzado", "Documento")
            raise handle_database_exception(e, "filter_documentos_avanzado")

    def filter_by_montos(self,
                         monto_minimo: Optional[Decimal] = None,
                         monto_maximo: Optional[Decimal] = None,
                         moneda: Optional[str] = None,
                         empresa_id: Optional[int] = None,
                         limit: Optional[int] = None,
                         offset: int = 0) -> Dict[str, Any]:
        """
        Filtrado por rangos de montos.

        Args:
            monto_minimo: Monto mínimo (inclusive)
            monto_maximo: Monto máximo (inclusive)
            moneda: Código de moneda (opcional)
            empresa_id: ID de empresa (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            Dict: Resultado con documentos y metadatos

        Raises:
            SifenValidationError: Si los montos no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.filter_by_montos(
            ...     monto_minimo=Decimal("100000"),
            ...     monto_maximo=Decimal("1000000"),
            ...     moneda="PYG",
            ...     empresa_id=1
            ... )
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if monto_minimo is not None and monto_maximo is not None:
                if monto_minimo > monto_maximo:
                    raise SifenValidationError(
                        "Monto mínimo no puede ser mayor al monto máximo",
                        field="monto_minimo"
                    )

            if moneda and moneda not in [e.value for e in MonedaSifenEnum]:
                raise SifenValidationError(
                    f"Moneda '{moneda}' no es válida",
                    field="moneda",
                    value=moneda
                )

            if limit and limit > get_max_page_size():
                limit = get_max_page_size()
            elif not limit:
                limit = get_default_page_size()

            # Construir query base
            query = self.db.query(self.model)

            # Aplicar filtro por empresa
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Aplicar filtros de monto
            query = build_amount_filter(
                query, self.model.total_general, monto_minimo, monto_maximo
            )

            # Aplicar filtro por moneda
            if moneda:
                query = query.filter(self.model.moneda == moneda)

            # Obtener total y resultados
            total = query.count()
            documentos = query.order_by(desc(self.model.total_general)).offset(
                offset).limit(limit).all()

            # Preparar resultado
            result = {
                "documentos": documentos,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total,
                "has_prev": offset > 0,
                "filters_applied": {
                    "monto_minimo": float(monto_minimo) if monto_minimo else None,
                    "monto_maximo": float(monto_maximo) if monto_maximo else None,
                    "moneda": moneda,
                    "empresa_id": empresa_id
                }
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "filter_by_montos", duration, len(documentos))

            log_repository_operation(
                "filter_by_montos",
                "Documento",
                None,
                {
                    "monto_minimo": float(monto_minimo) if monto_minimo else None,
                    "monto_maximo": float(monto_maximo) if monto_maximo else None,
                    "moneda": moneda,
                    "total_found": total,
                    "returned": len(documentos)
                }
            )

            return result

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "filter_by_montos", "Documento")
            raise handle_database_exception(e, "filter_by_multiple_criteria")

    # ===============================================
    # PAGINACIÓN ESPECIALIZADA
    # ===============================================

    def get_paginated_with_filters(self,
                                   page: int = 1,
                                   page_size: int = 20,
                                   filters: Optional[Dict[str, Any]] = None,
                                   search_term: Optional[str] = None,
                                   empresa_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtiene resultados paginados con filtros aplicados.

        Args:
            page: Número de página (base 1)
            page_size: Elementos por página
            filters: Filtros a aplicar (opcional)
            search_term: Término de búsqueda (opcional)
            empresa_id: ID de empresa (opcional)

        Returns:
            Dict: Resultado paginado con metadatos completos

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.get_paginated_with_filters(
            ...     page=2,
            ...     page_size=25,
            ...     filters={"tipo_documento": "1"},
            ...     search_term="cliente",
            ...     empresa_id=1
            ... )
            >>> print(f"Página {result['pagination']['page']} de {result['pagination']['pages']}")
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if page < 1:
                raise SifenValidationError(
                    "Número de página debe ser mayor a 0",
                    field="page",
                    value=page
                )

            if page_size < 1 or page_size > get_max_page_size():
                raise SifenValidationError(
                    f"Tamaño de página debe estar entre 1 y {get_max_page_size()}",
                    field="page_size",
                    value=page_size
                )

            # Construir query base
            query = self.db.query(self.model)

            # Aplicar filtro por empresa
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Aplicar filtros si se proporcionan
            if filters:
                query = self._apply_advanced_filters(query, filters)

            # Aplicar búsqueda si se proporciona
            if search_term:
                search_conditions = build_search_conditions(
                    self.model, DEFAULT_SEARCH_FIELDS, search_term
                )
                query = query.filter(search_conditions)

            # Obtener total de resultados
            total = query.count()

            # Calcular metadatos de paginación
            total_pages = ceil(total / page_size) if total > 0 else 1
            offset = (page - 1) * page_size

            # Aplicar ordenamiento por defecto
            query = query.order_by(desc(self.model.created_at))

            # Aplicar paginación
            documentos = query.offset(offset).limit(page_size).all()

            # Preparar resultado con metadatos completos
            result = {
                "documentos": documentos,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                    "next_page": page + 1 if page < total_pages else None,
                    "prev_page": page - 1 if page > 1 else None,
                    "offset": offset,
                    "limit": page_size
                },
                "filters_applied": filters or {},
                "search_term": search_term,
                "empresa_id": empresa_id
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_paginated_with_filters", duration, len(documentos))

            log_repository_operation(
                "get_paginated_with_filters",
                "Documento",
                None,
                {
                    "page": page,
                    "page_size": page_size,
                    "total_found": total,
                    "returned": len(documentos),
                    "has_filters": bool(filters),
                    "has_search": bool(search_term)
                }
            )

            return result

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_paginated_with_filters", "Documento")
            raise handle_database_exception(e, "get_paginated_with_filters")

    def get_paginated_search(self,
                             search_params: Dict[str, Any],
                             page: int = 1,
                             page_size: int = 20) -> Dict[str, Any]:
        """
        Búsqueda paginada con parámetros complejos.

        Args:
            search_params: Parámetros de búsqueda
            page: Número de página (base 1)
            page_size: Elementos por página

        Returns:
            Dict: Resultado paginado de búsqueda

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.get_paginated_search({
            ...     "q": "factura",
            ...     "tipo_documento": ["1"],
            ...     "fecha_desde": "2025-01-01",
            ...     "monto_minimo": 100000
            ... }, page=1, page_size=20)
        """
        start_time = datetime.now()

        try:
            # Validar parámetros de paginación
            if page < 1:
                raise SifenValidationError(
                    "Número de página debe ser mayor a 0",
                    field="page",
                    value=page
                )

            if page_size < 1 or page_size > get_max_page_size():
                raise SifenValidationError(
                    f"Tamaño de página debe estar entre 1 y {get_max_page_size()}",
                    field="page_size",
                    value=page_size
                )

            # Extraer parámetros de búsqueda
            search_term = search_params.get("q", "")
            empresa_id = search_params.get("empresa_id")
            tipos_documento = search_params.get("tipos_documento", [])
            estados = search_params.get("estados", [])

            # Procesar fechas
            fecha_desde = search_params.get("fecha_desde")
            fecha_hasta = search_params.get("fecha_hasta")

            if isinstance(fecha_desde, str):
                fecha_desde = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
            if isinstance(fecha_hasta, str):
                fecha_hasta = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()

            # Procesar montos
            monto_minimo = search_params.get("monto_minimo")
            monto_maximo = search_params.get("monto_maximo")

            if isinstance(monto_minimo, (str, int, float)):
                monto_minimo = Decimal(str(monto_minimo))
            if isinstance(monto_maximo, (str, int, float)):
                monto_maximo = Decimal(str(monto_maximo))

            # Calcular offset
            offset = (page - 1) * page_size

            # Realizar búsqueda usando método existente
            if search_term:
                result = self.search_documentos(
                    search_term=search_term,
                    empresa_id=empresa_id,
                    tipos_documento=tipos_documento,
                    estados=estados,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                    limit=page_size,
                    offset=offset
                )
            else:
                # Usar filtros avanzados si no hay término de búsqueda
                filters = {}
                if tipos_documento:
                    filters["tipo_documento"] = {
                        "operator": "in", "value": tipos_documento}
                if estados:
                    filters["estado"] = {"operator": "in", "value": estados}
                if monto_minimo:
                    filters["total_general"] = {
                        "operator": "gte", "value": monto_minimo}
                if monto_maximo:
                    if "total_general" in filters:
                        # Combinar con filtro existente
                        filters["total_general_max"] = {
                            "operator": "lte", "value": monto_maximo}
                    else:
                        filters["total_general"] = {
                            "operator": "lte", "value": monto_maximo}

                result = self.filter_documentos_avanzado(
                    filters=filters,
                    empresa_id=empresa_id,
                    limit=page_size,
                    offset=offset
                )

            # Transformar resultado para incluir metadatos de paginación estándar
            total = result["total"]
            total_pages = ceil(total / page_size) if total > 0 else 1

            paginated_result = {
                "documentos": result["documentos"],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                    "next_page": page + 1 if page < total_pages else None,
                    "prev_page": page - 1 if page > 1 else None,
                    "offset": offset,
                    "limit": page_size
                },
                "search_params": search_params,
                "search_type": "text" if search_term else "filters"
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_paginated_search", duration, len(result["documentos"]))

            log_repository_operation(
                "get_paginated_search",
                "Documento",
                None,
                {
                    "page": page,
                    "page_size": page_size,
                    "total_found": total,
                    "search_type": "text" if search_term else "filters",
                    "params_count": len(search_params)
                }
            )

            return paginated_result

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "get_paginated_search", "Documento")
            raise handle_database_exception(e, "get_paginated_search")

    # ===============================================
    # CONSULTAS ESPECIALIZADAS
    # ===============================================

    def get_documentos_relacionados(self,
                                    documento_id: int,
                                    incluir_referencias: bool = True,
                                    incluir_referenciados: bool = True,
                                    limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtiene documentos relacionados (NCE/NDE con documento original).

        Args:
            documento_id: ID del documento base
            incluir_referencias: Si incluir documentos que este referencia
            incluir_referenciados: Si incluir documentos que referencian a este
            limit: Número máximo de resultados

        Returns:
            Dict: Documentos relacionados organizados por tipo

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.get_documentos_relacionados(123)
            >>> print(f"Referencias: {len(result['referencias'])}")
            >>> print(f"Referenciados: {len(result['referenciados'])}")
        """
        start_time = datetime.now()

        try:
            # Obtener documento base
            documento_base = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento_base:
                from app.core.exceptions import SifenEntityNotFoundError
                raise SifenEntityNotFoundError("Documento", documento_id)

            resultado = {
                "documento_base": documento_base,
                "referencias": [],
                "referenciados": [],
                "total_relacionados": 0
            }

            cdc_documento = getattr(documento_base, 'cdc', None)

            if not cdc_documento:
                return resultado

            # Aplicar límite
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            # Buscar documentos que este documento referencia
            if incluir_referencias:
                documento_original_cdc = getattr(
                    documento_base, 'documento_original_cdc', None)
                if documento_original_cdc:
                    documento_original = self.db.query(self.model).filter(
                        text("cdc = :cdc")
                    ).params(cdc=documento_original_cdc).first()

                    if documento_original:
                        resultado["referencias"].append(documento_original)

            # Buscar documentos que referencian a este documento
            if incluir_referenciados:
                # Buscar notas de crédito/débito que referencian este documento
                documentos_referenciados = self.db.query(self.model).filter(
                    text("documento_original_cdc = :cdc")
                ).params(cdc=cdc_documento).limit(limit).all()

                resultado["referenciados"] = documentos_referenciados

            # Calcular total
            resultado["total_relacionados"] = len(
                resultado["referencias"]) + len(resultado["referenciados"])

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_documentos_relacionados", duration, resultado["total_relacionados"])

            log_repository_operation(
                "get_documentos_relacionados",
                "Documento",
                documento_id,
                {
                    "total_relacionados": resultado["total_relacionados"],
                    "referencias": len(resultado["referencias"]),
                    "referenciados": len(resultado["referenciados"])
                }
            )

            return resultado

        except Exception as e:
            handle_repository_error(
                e, "get_documentos_relacionados", "Documento", documento_id)
            raise handle_database_exception(e, "get_documentos_relacionados")

    def get_documentos_by_patron(self,
                                 patron: str,
                                 campo: str = "numero_completo",
                                 empresa_id: Optional[int] = None,
                                 limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Búsqueda por patrones específicos en campos.

        Args:
            patron: Patrón de búsqueda (SQL LIKE)
            campo: Campo donde buscar el patrón
            empresa_id: ID de empresa (opcional)
            limit: Número máximo de resultados

        Returns:
            Dict: Documentos que coinciden con el patrón

        Raises:
            SifenValidationError: Si el patrón o campo no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> result = mixin.get_documentos_by_patron(
            ...     patron="001-001-%",
            ...     campo="numero_completo",
            ...     empresa_id=1
            ... )
            >>> print(f"Documentos con patrón: {result['total']}")
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not patron or len(patron.strip()) < 2:
                raise SifenValidationError(
                    "Patrón debe tener al menos 2 caracteres",
                    field="patron"
                )

            # Verificar que el campo existe en el modelo
            if not hasattr(self.model, campo):
                raise SifenValidationError(
                    f"Campo '{campo}' no existe en el modelo",
                    field="campo",
                    value=campo
                )

            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            # Construir query
            query = self.db.query(self.model)

            # Aplicar filtro por empresa
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Aplicar patrón
            field_attr = getattr(self.model, campo)
            query = query.filter(field_attr.like(patron))

            # Obtener resultados
            total = query.count()
            documentos = query.order_by(
                desc(self.model.created_at)).limit(limit).all()

            # Preparar resultado
            result = {
                "documentos": documentos,
                "total": total,
                "patron": patron,
                "campo": campo,
                "empresa_id": empresa_id,
                "limit": limit
            }

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_documentos_by_patron", duration, len(documentos))

            log_repository_operation(
                "get_documentos_by_patron",
                "Documento",
                None,
                {
                    "patron": patron,
                    "campo": campo,
                    "total_found": total,
                    "returned": len(documentos),
                    "empresa_id": empresa_id
                }
            )

            return result

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "get_documentos_by_patron", "Documento")
            raise handle_database_exception(e, "get_documentos_by_patron")

    # ===============================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ===============================================

    def _validate_search_params(self,
                                search_term: str,
                                limit: Optional[int],
                                order_by: str,
                                order_direction: str) -> None:
        """
        Valida parámetros de búsqueda.

        Args:
            search_term: Término de búsqueda
            limit: Límite de resultados
            order_by: Campo de ordenamiento
            order_direction: Dirección de ordenamiento

        Raises:
            SifenValidationError: Si los parámetros no son válidos
        """
        # Validar término de búsqueda
        if not search_term or len(search_term.strip()) < 2:
            raise SifenValidationError(
                "Término de búsqueda debe tener al menos 2 caracteres",
                field="search_term"
            )

        if len(search_term) > MAX_SEARCH_TERM_LENGTH:
            raise SifenValidationError(
                f"Término de búsqueda no puede exceder {MAX_SEARCH_TERM_LENGTH} caracteres",
                field="search_term"
            )

        # Validar límite
        if limit is not None and limit > MAX_SEARCH_RESULTS:
            raise SifenValidationError(
                f"Límite no puede exceder {MAX_SEARCH_RESULTS} resultados",
                field="limit",
                value=limit
            )

        # Validar campo de ordenamiento
        if order_by not in VALID_ORDER_FIELDS:
            raise SifenValidationError(
                f"Campo de ordenamiento '{order_by}' no es válido",
                field="order_by",
                value=order_by
            )

        # Validar dirección de ordenamiento
        if order_direction not in ["asc", "desc"]:
            raise SifenValidationError(
                f"Dirección de ordenamiento '{order_direction}' no es válida",
                field="order_direction",
                value=order_direction
            )

    def _build_base_search_query(self,
                                 search_term: str,
                                 empresa_id: Optional[int],
                                 tipos_documento: Optional[List[str]],
                                 estados: Optional[List[str]],
                                 fecha_desde: Optional[date],
                                 fecha_hasta: Optional[date]) -> Query:
        """
        Construye query base para búsqueda.

        Args:
            search_term: Término de búsqueda
            empresa_id: ID de empresa
            tipos_documento: Tipos de documento
            estados: Estados
            fecha_desde: Fecha desde
            fecha_hasta: Fecha hasta

        Returns:
            Query: Query base construida
        """
        # Query base
        query = self.db.query(self.model)

        # Filtro por empresa
        if empresa_id:
            query = query.filter(self.model.empresa_id == empresa_id)

        # Filtros por tipo
        if tipos_documento:
            query = query.filter(
                self.model.tipo_documento.in_(tipos_documento))

        # Filtros por estado
        if estados:
            query = query.filter(text("estado IN :estados")).params(
                estados=tuple(estados))

        # Filtros por fecha
        if fecha_desde or fecha_hasta:
            query = build_date_filter(
                query, self.model.fecha_emision, fecha_desde, fecha_hasta)

        # Condiciones de búsqueda
        if search_term:
            search_conditions = build_search_conditions(
                self.model, DEFAULT_SEARCH_FIELDS, search_term
            )
            query = query.filter(search_conditions)

        return query

    def _apply_advanced_filters(self,
                                query: Query,
                                filters: Dict[str, Any]) -> Query:
        """
        Aplica filtros avanzados con operadores.

        Args:
            query: Query base
            filters: Filtros a aplicar

        Returns:
            Query: Query con filtros aplicados
        """
        for field, filter_config in filters.items():
            if not isinstance(filter_config, dict):
                # Filtro simple (valor directo)
                if hasattr(self.model, field):
                    field_attr = getattr(self.model, field)
                    query = query.filter(field_attr == filter_config)
                continue

            operator = filter_config.get("operator", "eq")
            value = filter_config.get("value")

            if operator not in VALID_FILTER_OPERATORS:
                continue

            if not hasattr(self.model, field):
                continue

            field_attr = getattr(self.model, field)

            # Aplicar operador
            if operator == "eq":
                query = query.filter(field_attr == value)
            elif operator == "ne":
                query = query.filter(field_attr != value)
            elif operator == "gt":
                query = query.filter(field_attr > value)
            elif operator == "gte":
                query = query.filter(field_attr >= value)
            elif operator == "lt":
                query = query.filter(field_attr < value)
            elif operator == "lte":
                query = query.filter(field_attr <= value)
            elif operator == "like":
                query = query.filter(field_attr.like(f"%{value}%"))
            elif operator == "ilike":
                query = query.filter(field_attr.ilike(f"%{value}%"))
            elif operator == "in":
                if isinstance(value, list):
                    query = query.filter(field_attr.in_(value))
            elif operator == "nin":
                if isinstance(value, list):
                    query = query.filter(~field_attr.in_(value))
            elif operator == "null":
                query = query.filter(field_attr.is_(None))
            elif operator == "nnull":
                query = query.filter(field_attr.isnot(None))

        return query

    def _apply_ordering(self,
                        query: Query,
                        order_by: str,
                        order_direction: str) -> Query:
        """
        Aplica ordenamiento a la query.

        Args:
            query: Query base
            order_by: Campo de ordenamiento
            order_direction: Dirección de ordenamiento

        Returns:
            Query: Query con ordenamiento aplicado
        """
        if hasattr(self.model, order_by):
            field_attr = getattr(self.model, order_by)

            if order_direction == "asc":
                query = query.order_by(asc(field_attr))
            else:
                query = query.order_by(desc(field_attr))

        return query


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "DocumentoSearchMixin",

    # Constantes
    "DEFAULT_SEARCH_FIELDS",
    "CLIENT_SEARCH_FIELDS",
    "VALID_ORDER_FIELDS",
    "VALID_FILTER_OPERATORS",
    "MAX_SEARCH_RESULTS",
    "MAX_SEARCH_TERM_LENGTH"
]
