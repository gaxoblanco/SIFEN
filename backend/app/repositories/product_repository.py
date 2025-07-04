"""
Repository para la gestión de productos/servicios del sistema SIFEN.

Este módulo maneja todas las operaciones relacionadas con el catálogo de productos:
- CRUD de productos/servicios por empresa
- Validación de códigos únicos por empresa
- Búsquedas por código, descripción, categoría
- Gestión de precios e IVA
- Control de stock (opcional)
- Productos activos/inactivos

Características específicas:
- Código único por empresa
- Validación de tasas de IVA Paraguay (0%, 5%, 10%)
- Búsquedas case-insensitive por múltiples campos
- Gestión de categorías de productos
- Control de precios mínimos/máximos
- Historial de cambios de precios
- Integración con facturación

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    SifenValidationError,
    SifenEntityNotFoundError
)
from app.models.producto import Producto, TipoProductoEnum, AfectacionIvaEnum, UnidadMedidaEnum
from app.schemas.producto import ProductoCreateDTO, ProductoUpdateDTO, TasaIvaEnum
from .base import BaseRepository, RepositoryFilter
from .utils import safe_get, safe_set, safe_bool, safe_str

# Configurar logging
logger = logging.getLogger(__name__)

# Constantes de validación
IVA_RATES_PARAGUAY = [Decimal("0"), Decimal("5"), Decimal("10")]
MIN_PRICE = Decimal("0.01")
MAX_PRICE = Decimal("999999999.99")


class ProductoRepository(BaseRepository[Producto, ProductoCreateDTO, ProductoUpdateDTO]):
    """
    Repository para gestión de productos/servicios del sistema SIFEN.

    Hereda de BaseRepository todas las operaciones CRUD básicas y
    añade funcionalidades específicas para productos:

    - Búsquedas por código, descripción, categoría
    - Validaciones de precios e IVA
    - Gestión de stock y unidades de medida
    - Filtros por empresa y estado
    - Estadísticas de catálogo
    """

    def __init__(self):
        """Inicializa el repository de productos."""
        super().__init__(Producto)
        logger.debug("ProductoRepository inicializado")

    # === MÉTODOS DE BÚSQUEDA POR IDENTIFICACIÓN ===

    def get_by_codigo_interno(self, db: Session, *, codigo_interno: str, empresa_id: int) -> Optional[Producto]:
        """
        Busca un producto por su código interno dentro de una empresa.

        Args:
            db: Sesión de base de datos
            codigo_interno: Código interno del producto
            empresa_id: ID de la empresa

        Returns:
            Optional[Producto]: Producto encontrado o None

        Note:
            El código interno debe ser único por empresa
        """
        try:
            query = select(Producto).where(
                and_(
                    Producto.codigo_interno == codigo_interno.strip().upper(),
                    Producto.empresa_id == empresa_id
                )
            )

            producto = db.execute(query).scalar_one_or_none()

            if producto:
                logger.debug(
                    f"✅ Producto encontrado por código: {codigo_interno}")
            else:
                logger.debug(
                    f"❌ Producto no encontrado por código: {codigo_interno}")

            return producto

        except Exception as e:
            logger.error(
                f"❌ Error buscando producto por código {codigo_interno}: {str(e)}")
            raise self._handle_repository_error(e, "get_by_codigo_interno")

    def get_by_codigo_barras(self, db: Session, *, codigo_barras: str, empresa_id: int) -> Optional[Producto]:
        """
        Busca un producto por su código de barras.

        Args:
            db: Sesión de base de datos
            codigo_barras: Código de barras del producto
            empresa_id: ID de la empresa

        Returns:
            Optional[Producto]: Producto encontrado o None
        """
        try:
            query = select(Producto).where(
                and_(
                    Producto.codigo_barras == codigo_barras.strip(),
                    Producto.empresa_id == empresa_id
                )
            )

            producto = db.execute(query).scalar_one_or_none()

            if producto:
                logger.debug(
                    f"✅ Producto encontrado por código de barras: {codigo_barras}")
            else:
                logger.debug(
                    f"❌ Producto no encontrado por código de barras: {codigo_barras}")

            return producto

        except Exception as e:
            logger.error(
                f"❌ Error buscando producto por código de barras: {str(e)}")
            raise self._handle_repository_error(e, "get_by_codigo_barras")

    # === MÉTODOS DE GESTIÓN POR EMPRESA ===

    def get_by_empresa(
        self,
        db: Session,
        *,
        empresa_id: int,
        active_only: bool = True,
        tipo_producto: Optional[TipoProductoEnum] = None,
        limit: Optional[int] = None
    ) -> List[Producto]:
        """
        Obtiene todos los productos de una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            active_only: Solo productos activos
            tipo_producto: Filtrar por tipo (PRODUCTO/SERVICIO)
            limit: Límite de resultados

        Returns:
            List[Producto]: Lista de productos de la empresa
        """
        filters = RepositoryFilter().eq("empresa_id", empresa_id)

        if active_only:
            filters = filters.eq("is_active", True)

        if tipo_producto:
            filters = filters.eq("tipo_producto", tipo_producto)

        return self.get_multi(
            db,
            filters=filters,
            order_by="descripcion",
            order_desc=False,
            limit=limit or 100
        )

    def get_productos_activos(self, db: Session, *, empresa_id: int) -> List[Producto]:
        """
        Obtiene todos los productos activos de una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            List[Producto]: Lista de productos activos
        """
        return self.get_by_empresa(db, empresa_id=empresa_id, active_only=True)

    def get_productos_by_tipo(
        self,
        db: Session,
        *,
        tipo_producto: TipoProductoEnum,
        empresa_id: int,
        active_only: bool = True
    ) -> List[Producto]:
        """
        Obtiene productos por su tipo.

        Args:
            db: Sesión de base de datos
            tipo_producto: Tipo de producto a filtrar
            empresa_id: ID de la empresa
            active_only: Solo productos activos

        Returns:
            List[Producto]: Lista de productos del tipo especificado
        """
        filters = (RepositoryFilter()
                   .eq("empresa_id", empresa_id)
                   .eq("tipo_producto", tipo_producto))

        if active_only:
            filters = filters.eq("is_active", True)

        return self.get_multi(
            db,
            filters=filters,
            order_by="descripcion",
            order_desc=False
        )

    def get_low_stock_productos(
        self,
        db: Session,
        *,
        empresa_id: int,
        threshold: Optional[Decimal] = None
    ) -> List[Producto]:
        """
        Obtiene productos con stock bajo.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            threshold: Umbral de stock mínimo (opcional, usa stock_minimo del producto)

        Returns:
            List[Producto]: Lista de productos con stock bajo

        Note:
            Solo aplica a productos que controlan stock
        """
        try:
            query = select(Producto).where(
                and_(
                    Producto.empresa_id == empresa_id,
                    Producto.is_active.is_(True),
                    Producto.controla_stock.is_(True)
                )
            )

            # Filtrar por stock bajo usando threshold o stock_minimo del producto
            if threshold is not None:
                query = query.where(
                    func.coalesce(Producto.stock_actual, 0) <= threshold
                )
            else:
                # Usar stock_minimo de cada producto
                query = query.where(Producto.stock_actual <=
                                    Producto.stock_minimo)

            query = query.order_by(Producto.descripcion)

            productos = list(db.execute(query).scalars().all())

            logger.debug(f"✅ Productos con stock bajo: {len(productos)}")
            return productos

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo productos con stock bajo: {str(e)}")
            raise self._handle_repository_error(e, "get_low_stock_productos")

    # === MÉTODOS DE BÚSQUEDA ===

    def search_by_description(
        self,
        db: Session,
        *,
        query: str,
        empresa_id: int,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Producto]:
        """
        Busca productos por descripción.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            empresa_id: ID de la empresa
            active_only: Solo productos activos
            limit: Máximo número de resultados

        Returns:
            List[Producto]: Lista de productos que coinciden
        """
        try:
            search_pattern = f"%{query.strip().lower()}%"

            sql_query = select(Producto).where(
                and_(
                    Producto.empresa_id == empresa_id,
                    func.lower(Producto.descripcion).like(search_pattern)
                )
            )

            # Filtrar solo activos si se requiere
            if active_only:
                sql_query = sql_query.where(Producto.is_active.is_(True))

            # Ordenar y limitar
            sql_query = sql_query.order_by(Producto.descripcion).limit(limit)

            productos = list(db.execute(sql_query).scalars().all())

            logger.debug(
                f"✅ Búsqueda productos '{query}': {len(productos)} resultados")
            return productos

        except Exception as e:
            logger.error(
                f"❌ Error buscando productos con query '{query}': {str(e)}")
            raise self._handle_repository_error(e, "search_by_description")

    def search_productos(
        self,
        db: Session,
        *,
        query: str,
        empresa_id: int,
        tipo_producto: Optional[TipoProductoEnum] = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Producto]:
        """
        Búsqueda completa de productos por múltiples campos.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            empresa_id: ID de la empresa
            tipo_producto: Filtrar por tipo (opcional)
            active_only: Solo productos activos
            limit: Máximo número de resultados

        Returns:
            List[Producto]: Lista de productos que coinciden
        """
        try:
            search_pattern = f"%{query.strip().lower()}%"

            # Construir condiciones de búsqueda
            search_conditions = [
                func.lower(Producto.descripcion).like(search_pattern),
                Producto.codigo_interno.like(f"%{query.strip().upper()}%")
            ]

            # Incluir código de barras si existe
            if hasattr(Producto, 'codigo_barras'):
                search_conditions.append(
                    Producto.codigo_barras.like(f"%{query.strip()}%"))

            # Incluir código NCM si existe
            if hasattr(Producto, 'codigo_ncm'):
                search_conditions.append(
                    Producto.codigo_ncm.like(f"%{query.strip()}%"))

            sql_query = select(Producto).where(
                and_(
                    Producto.empresa_id == empresa_id,
                    or_(*search_conditions)
                )
            )

            # Filtrar por tipo si se especifica
            if tipo_producto:
                sql_query = sql_query.where(
                    Producto.tipo_producto == tipo_producto)

            # Filtrar solo activos si se requiere
            if active_only:
                sql_query = sql_query.where(Producto.is_active.is_(True))

            # Ordenar y limitar
            sql_query = sql_query.order_by(Producto.descripcion).limit(limit)

            productos = list(db.execute(sql_query).scalars().all())

            logger.debug(
                f"✅ Búsqueda completa productos '{query}': {len(productos)} resultados")
            return productos

        except Exception as e:
            logger.error(
                f"❌ Error en búsqueda completa productos '{query}': {str(e)}")
            raise self._handle_repository_error(e, "search_productos")

    # === MÉTODOS DE FILTRADO POR TIPO ===

    def get_productos(self, db: Session, *, empresa_id: int, active_only: bool = True) -> List[Producto]:
        """
        Obtiene solo los productos (no servicios).

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            active_only: Solo productos activos

        Returns:
            List[Producto]: Lista de productos
        """
        return self.get_productos_by_tipo(
            db,
            tipo_producto=TipoProductoEnum.PRODUCTO,
            empresa_id=empresa_id,
            active_only=active_only
        )

    def get_servicios(self, db: Session, *, empresa_id: int, active_only: bool = True) -> List[Producto]:
        """
        Obtiene solo los servicios.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            active_only: Solo servicios activos

        Returns:
            List[Producto]: Lista de servicios
        """
        return self.get_productos_by_tipo(
            db,
            tipo_producto=TipoProductoEnum.SERVICIO,
            empresa_id=empresa_id,
            active_only=active_only
        )

    def get_by_afectacion_iva(
        self,
        db: Session,
        *,
        afectacion_iva: AfectacionIvaEnum,
        empresa_id: int,
        active_only: bool = True
    ) -> List[Producto]:
        """
        Obtiene productos por su afectación de IVA.

        Args:
            db: Sesión de base de datos
            afectacion_iva: Tipo de afectación IVA
            empresa_id: ID de la empresa
            active_only: Solo productos activos

        Returns:
            List[Producto]: Lista de productos con la afectación especificada
        """
        filters = (RepositoryFilter()
                   .eq("empresa_id", empresa_id)
                   .eq("afectacion_iva", afectacion_iva))

        if active_only:
            filters = filters.eq("is_active", True)

        return self.get_multi(
            db,
            filters=filters,
            order_by="descripcion",
            order_desc=False
        )

    # === MÉTODOS DE PRECIOS ===

    def get_by_precio_range(
        self,
        db: Session,
        *,
        precio_min: Decimal,
        precio_max: Decimal,
        empresa_id: int,
        active_only: bool = True
    ) -> List[Producto]:
        """
        Obtiene productos en un rango de precios.

        Args:
            db: Sesión de base de datos
            precio_min: Precio mínimo
            precio_max: Precio máximo
            empresa_id: ID de la empresa
            active_only: Solo productos activos

        Returns:
            List[Producto]: Lista de productos en el rango
        """
        try:
            query = select(Producto).where(
                and_(
                    Producto.empresa_id == empresa_id,
                    Producto.precio_unitario >= precio_min,
                    Producto.precio_unitario <= precio_max
                )
            )

            if active_only:
                query = query.where(Producto.is_active.is_(True))

            query = query.order_by(Producto.precio_unitario.asc())

            productos = list(db.execute(query).scalars().all())

            logger.debug(
                f"✅ Productos en rango ${precio_min}-${precio_max}: {len(productos)}")
            return productos

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo productos por rango de precio: {str(e)}")
            raise self._handle_repository_error(e, "get_by_precio_range")

    def get_productos_mas_caros(
        self,
        db: Session,
        *,
        empresa_id: int,
        limit: int = 10
    ) -> List[Producto]:
        """
        Obtiene los productos más caros.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            limit: Número de productos a retornar

        Returns:
            List[Producto]: Lista de productos más caros
        """
        try:
            query = select(Producto).where(
                and_(
                    Producto.empresa_id == empresa_id,
                    Producto.is_active.is_(True)
                )
            ).order_by(Producto.precio_unitario.desc()).limit(limit)

            productos = list(db.execute(query).scalars().all())

            logger.debug(f"✅ Top {limit} productos más caros obtenidos")
            return productos

        except Exception as e:
            logger.error(f"❌ Error obteniendo productos más caros: {str(e)}")
            raise self._handle_repository_error(e, "get_productos_mas_caros")

    # === VALIDACIONES ESPECÍFICAS ===

    def is_codigo_available(
        self,
        db: Session,
        *,
        codigo_interno: str,
        empresa_id: int,
        exclude_producto_id: Optional[int] = None
    ) -> bool:
        """
        Verifica si un código interno está disponible dentro de una empresa.

        Args:
            db: Sesión de base de datos
            codigo_interno: Código a verificar
            empresa_id: ID de la empresa
            exclude_producto_id: ID de producto a excluir (para updates)

        Returns:
            bool: True si el código está disponible
        """
        try:
            query = select(func.count()).where(
                and_(
                    Producto.codigo_interno == codigo_interno.strip().upper(),
                    Producto.empresa_id == empresa_id
                )
            )

            if exclude_producto_id:
                query = query.where(Producto.id != exclude_producto_id)

            count = db.execute(query).scalar()
            if count is None:
                count = 0

            is_available = count == 0

            logger.debug(
                f"Verificación código '{codigo_interno}' empresa {empresa_id}: {is_available}")
            return is_available

        except Exception as e:
            logger.error(
                f"❌ Error verificando código '{codigo_interno}': {str(e)}")
            raise self._handle_repository_error(e, "is_codigo_available")

    def validate_precio(self, precio: Union[Decimal, float, int]) -> bool:
        """
        Valida que un precio esté dentro de los rangos permitidos.

        Args:
            precio: Precio a validar

        Returns:
            bool: True si el precio es válido
        """
        try:
            precio_decimal = Decimal(str(precio))
            return MIN_PRICE <= precio_decimal <= MAX_PRICE
        except (ValueError, TypeError):
            return False

    def validate_iva_rate(self, iva_rate: Union[str, int]) -> bool:
        """
        Valida que una tasa de IVA sea válida para Paraguay.

        Args:
            iva_rate: Tasa de IVA a validar (puede ser string "10" o int 10)

        Returns:
            bool: True si la tasa es válida (0, 5, 10)
        """
        try:
            # Convertir a entero para comparar
            rate_int = int(str(iva_rate))
            return rate_int in [0, 5, 10]
        except (ValueError, TypeError):
            return False

    def update_stock(
        self,
        db: Session,
        *,
        producto_id: int,
        cantidad_cambio: Decimal,
        observacion: Optional[str] = None
    ) -> Producto:
        """
        Actualiza el stock de un producto.

        Args:
            db: Sesión de base de datos
            producto_id: ID del producto
            cantidad_cambio: Cantidad a sumar/restar (puede ser negativa)
            observacion: Observación del cambio (opcional)

        Returns:
            Producto: Producto con stock actualizado

        Raises:
            SifenEntityNotFoundError: Si el producto no existe
            SifenValidationError: Si el producto no controla stock o resultado sería negativo
        """
        try:
            producto = self.get_by_id_or_404(db, id=producto_id)

            # Verificar que el producto controle stock
            if not safe_bool(producto, 'controla_stock'):
                raise SifenValidationError(
                    "El producto no controla stock",
                    field="controla_stock",
                    value=False
                )

            # Calcular nuevo stock
            stock_actual = Decimal(str(safe_get(producto, 'stock_actual', 0)))
            nuevo_stock = stock_actual + cantidad_cambio

            # Validar que no sea negativo
            if nuevo_stock < 0:
                raise SifenValidationError(
                    f"El stock no puede ser negativo. Stock actual: {stock_actual}, cambio: {cantidad_cambio}",
                    field="stock_actual",
                    value=str(nuevo_stock)
                )

            # Actualizar stock
            safe_set(producto, 'stock_actual', nuevo_stock)

            # Actualizar observaciones si se proporciona
            if observacion:
                observaciones_actuales = safe_str(
                    producto, 'observaciones', '')
                nuevas_observaciones = f"{observaciones_actuales}\n{observacion}".strip(
                )
                safe_set(producto, 'observaciones', nuevas_observaciones)

            db.add(producto)
            db.commit()
            db.refresh(producto)

            logger.info(
                f"✅ Stock actualizado producto {producto_id}: {stock_actual} → {nuevo_stock}")
            return producto

        except (SifenEntityNotFoundError, SifenValidationError):
            raise
        except Exception as e:
            db.rollback()
            logger.error(
                f"❌ Error actualizando stock producto {producto_id}: {str(e)}")
            raise self._handle_repository_error(e, "update_stock")

    # === OVERRIDE DE MÉTODOS BASE ===

    def create(self, db: Session, *, obj_in: ProductoCreateDTO, empresa_id: int) -> Producto:
        """
        Crea un nuevo producto con validaciones específicas.

        Args:
            db: Sesión de base de datos
            obj_in: Datos del producto a crear
            empresa_id: ID de la empresa propietaria

        Returns:
            Producto: Producto creado

        Raises:
            SifenValidationError: Si las validaciones fallan

        Note:
            empresa_id se pasa por separado porque no está en el DTO
        """
        # Validar código disponible
        if not self.is_codigo_available(
            db,
            codigo_interno=obj_in.codigo_interno,
            empresa_id=empresa_id
        ):
            raise SifenValidationError(
                f"El código '{obj_in.codigo_interno}' ya está registrado para esta empresa",
                field="codigo_interno",
                value=obj_in.codigo_interno
            )

        # Validar precio
        if not self.validate_precio(obj_in.precio_unitario):
            raise SifenValidationError(
                f"Precio inválido: debe estar entre {MIN_PRICE} y {MAX_PRICE}",
                field="precio_unitario",
                value=str(obj_in.precio_unitario)
            )

        # Validar tasa IVA
        # Convertir TasaIvaEnum a su valor para validación
        tasa_value = obj_in.tasa_iva.value if hasattr(
            obj_in.tasa_iva, 'value') else obj_in.tasa_iva
        if not self.validate_iva_rate(tasa_value):
            raise SifenValidationError(
                f"Tasa de IVA inválida: debe ser 0, 5 o 10",
                field="tasa_iva",
                value=str(tasa_value)
            )

        # Preparar datos para crear, añadiendo empresa_id
        obj_data = obj_in.model_dump()
        # Añadir empresa_id del usuario autenticado
        obj_data['empresa_id'] = empresa_id

        # Normalizar código a mayúsculas
        obj_data['codigo_interno'] = obj_data['codigo_interno'].strip().upper()

        # Llamar al método base para crear
        producto = super().create(db, obj_in=obj_data)

        logger.info(
            f"✅ Producto creado exitosamente: ID={producto.id}, "
            f"código={safe_str(producto, 'codigo_interno')}, empresa_id={empresa_id}"
        )

        return producto

    def update(self, db: Session, *, db_obj: Producto, obj_in: ProductoUpdateDTO) -> Producto:
        """
        Actualiza un producto con validaciones específicas.

        Args:
            db: Sesión de base de datos
            db_obj: Producto existente
            obj_in: Datos de actualización

        Returns:
            Producto: Producto actualizado

        Note:
            ProductoUpdateDTO no permite cambiar codigo_interno por razones de integridad
        """
        # Nota: ProductoUpdateDTO no permite cambiar codigo_interno según el schema
        # El código interno es inmutable después de la creación

        # Validar precio si se está cambiando
        if hasattr(obj_in, 'precio_unitario'):
            new_precio = getattr(obj_in, 'precio_unitario', None)
            if new_precio is not None and not self.validate_precio(new_precio):
                raise SifenValidationError(
                    f"Precio inválido: debe estar entre {MIN_PRICE} y {MAX_PRICE}",
                    field="precio_unitario",
                    value=str(new_precio)
                )

        # Validar tasa IVA si se está cambiando
        if hasattr(obj_in, 'tasa_iva'):
            new_tasa = getattr(obj_in, 'tasa_iva', None)
            if new_tasa is not None:
                # Convertir TasaIvaEnum a su valor string/int para validación
                tasa_value = new_tasa.value if hasattr(
                    new_tasa, 'value') else new_tasa
                if not self.validate_iva_rate(tasa_value):
                    raise SifenValidationError(
                        f"Tasa de IVA inválida: debe ser 0, 5 o 10",
                        field="tasa_iva",
                        value=str(tasa_value)
                    )

            raise SifenValidationError(
                f"Tasa de IVA inválida: debe ser 0, 5 o 10",
                field="tasa_iva",
                value=str(obj_in.tasa_iva)
            )

        # Llamar al método base para actualizar
        producto = super().update(db, db_obj=db_obj, obj_in=obj_in)

        logger.info(
            f"✅ Producto actualizado: ID={producto.id}, código={safe_str(producto, 'codigo_interno')}")

        return producto

    # === MÉTODOS PRIVADOS ===

    def _handle_repository_error(self, exception: Exception, operation: str):
        """
        Maneja errores específicos del repository de productos.

        Args:
            exception: Excepción original
            operation: Operación que falló

        Returns:
            Exception: Excepción SIFEN apropiada
        """
        from app.core.exceptions import handle_database_exception

        # Usar el handler genérico de la base
        return handle_database_exception(exception, f"producto_{operation}")

    # === MÉTODOS DE ESTADÍSTICAS ===

    def get_producto_stats(self, db: Session, *, empresa_id: int) -> dict:
        """
        Obtiene estadísticas básicas de productos para una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            dict: Estadísticas de productos
        """
        try:
            base_filter = RepositoryFilter().eq("empresa_id", empresa_id)

            total_productos = self.count(db, filters=base_filter)

            active_filter = base_filter.eq("is_active", True)
            active_productos = self.count(db, filters=active_filter)

            # Estadísticas por tipo
            productos_filter = active_filter.eq(
                "tipo_producto", TipoProductoEnum.PRODUCTO)
            productos_count = self.count(db, filters=productos_filter)

            servicios_count = active_productos - productos_count

            # Productos con stock bajo
            productos_stock_bajo = len(
                self.get_low_stock_productos(db, empresa_id=empresa_id))

            # Precio promedio
            try:
                query = select(func.avg(Producto.precio_unitario)).where(
                    and_(
                        Producto.empresa_id == empresa_id,
                        Producto.is_active.is_(True)
                    )
                )
                precio_promedio = db.execute(query).scalar()
                if precio_promedio is None:
                    precio_promedio = 0
                else:
                    precio_promedio = float(precio_promedio)
            except Exception:
                precio_promedio = 0

            stats = {
                "total_productos": total_productos,
                "active_productos": active_productos,
                "inactive_productos": total_productos - active_productos,
                "productos_count": productos_count,
                "servicios_count": servicios_count,
                "productos_stock_bajo": productos_stock_bajo,
                "precio_promedio": precio_promedio,
                "activity_rate": round((active_productos / total_productos * 100) if total_productos > 0 else 0, 2)
            }

            logger.debug(
                f"✅ Estadísticas productos empresa {empresa_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo estadísticas productos empresa {empresa_id}: {str(e)}")
            raise self._handle_repository_error(e, "get_producto_stats")

    def get_stock_summary(self, db: Session, *, empresa_id: int) -> dict:
        """
        Obtiene resumen de stock para una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            dict: Resumen de stock
        """
        try:
            # Productos que controlan stock
            query_stock = select(Producto).where(
                and_(
                    Producto.empresa_id == empresa_id,
                    Producto.is_active.is_(True),
                    Producto.controla_stock.is_(True)
                )
            )

            productos_con_stock = list(db.execute(query_stock).scalars().all())

            total_con_stock = len(productos_con_stock)

            if total_con_stock == 0:
                return {
                    "total_productos_con_stock": 0,
                    "productos_stock_bajo": 0,
                    "productos_sin_stock": 0,
                    "valor_total_inventario": 0.0,
                    "productos_mas_rotativos": []
                }

            # Calcular métricas
            productos_stock_bajo = 0
            productos_sin_stock = 0
            valor_total_inventario = Decimal("0")

            for producto in productos_con_stock:
                stock_actual = Decimal(
                    str(safe_get(producto, 'stock_actual', 0)))
                stock_minimo = Decimal(
                    str(safe_get(producto, 'stock_minimo', 0)))
                precio = Decimal(str(safe_get(producto, 'precio_unitario', 0)))

                # Contadores
                if stock_actual <= 0:
                    productos_sin_stock += 1
                elif stock_actual <= stock_minimo:
                    productos_stock_bajo += 1

                # Valor inventario
                valor_total_inventario += stock_actual * precio

            summary = {
                "total_productos_con_stock": total_con_stock,
                "productos_stock_bajo": productos_stock_bajo,
                "productos_sin_stock": productos_sin_stock,
                "valor_total_inventario": float(valor_total_inventario),
                "porcentaje_stock_bajo": round((productos_stock_bajo / total_con_stock * 100), 2),
                "porcentaje_sin_stock": round((productos_sin_stock / total_con_stock * 100), 2)
            }

            logger.debug(f"✅ Resumen stock empresa {empresa_id}: {summary}")
            return summary

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo resumen stock empresa {empresa_id}: {str(e)}")
            raise self._handle_repository_error(e, "get_stock_summary")

    def get_productos_mas_vendidos(
        self,
        db: Session,
        *,
        empresa_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los productos más vendidos (placeholder para integración futura).

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            limit: Número de productos a retornar

        Returns:
            List[Dict]: Lista de productos con estadísticas de venta

        Note:
            Esta función será implementada completamente cuando esté
            disponible el repository de facturas/items
        """
        try:
            # TODO: Implementar cuando FacturaRepository e ItemFactura estén disponibles
            # Por ahora retornamos productos ordenados por precio (placeholder)

            productos = self.get_productos_mas_caros(
                db, empresa_id=empresa_id, limit=limit)

            productos_stats = []
            for producto in productos:
                productos_stats.append({
                    'producto_id': producto.id,
                    'codigo_interno': safe_str(producto, 'codigo_interno'),
                    'descripcion': safe_str(producto, 'descripcion'),
                    'precio_unitario': float(safe_get(producto, 'precio_unitario', 0)),
                    # Placeholders para futuras estadísticas de venta
                    'veces_vendido': 0,
                    'cantidad_total_vendida': 0.0,
                    'monto_total_vendido': 0.0
                })

            logger.debug(f"✅ Top {limit} productos (placeholder) obtenidos")
            return productos_stats

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo productos más vendidos: {str(e)}")
            raise self._handle_repository_error(
                e, "get_productos_mas_vendidos")

    def get_categorias(self, db: Session, *, empresa_id: int) -> List[str]:
        """
        Obtiene todas las categorías/tipos de productos de una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            List[str]: Lista de tipos de productos únicos
        """
        try:
            query = select(Producto.tipo_producto).where(
                and_(
                    Producto.empresa_id == empresa_id,
                    Producto.is_active.is_(True)
                )
            ).distinct().order_by(Producto.tipo_producto)

            tipos = list(db.execute(query).scalars().all())

            # Convertir enums a strings de forma type-safe
            categorias = []
            for tipo in tipos:
                if hasattr(tipo, 'value'):
                    # Es un enum, extraer el valor
                    categorias.append(tipo.value)  # type: ignore
                else:
                    # Ya es string o compatible
                    categorias.append(str(tipo))

            logger.debug(
                f"✅ Categorías productos empresa {empresa_id}: {len(categorias)}")
            return categorias

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo categorías empresa {empresa_id}: {str(e)}")
            raise self._handle_repository_error(e, "get_categorias")

    # === MÉTODOS DE UTILIDAD ===

    def bulk_update_prices(
        self,
        db: Session,
        *,
        empresa_id: int,
        factor_multiplicador: Decimal,
        tipo_producto: Optional[TipoProductoEnum] = None,
        observacion: str = "Actualización masiva de precios"
    ) -> int:
        """
        Actualiza precios de múltiples productos de forma masiva.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            factor_multiplicador: Factor por el cual multiplicar los precios (ej: 1.1 para +10%)
            tipo_producto: Filtrar por tipo (opcional)
            observacion: Observación del cambio

        Returns:
            int: Número de productos actualizados

        Raises:
            SifenValidationError: Si el factor es inválido
        """
        try:
            # Validar factor multiplicador
            if factor_multiplicador <= 0:
                raise SifenValidationError(
                    "El factor multiplicador debe ser mayor a 0",
                    field="factor_multiplicador",
                    value=str(factor_multiplicador)
                )

            # Construir query de productos a actualizar
            query = select(Producto).where(
                and_(
                    Producto.empresa_id == empresa_id,
                    Producto.is_active.is_(True)
                )
            )

            # Filtrar por tipo si se especifica
            if tipo_producto:
                query = query.where(Producto.tipo_producto == tipo_producto)

            productos = list(db.execute(query).scalars().all())

            # Actualizar cada producto
            productos_actualizados = 0
            for producto in productos:
                precio_actual = Decimal(
                    str(safe_get(producto, 'precio_unitario', 0)))
                nuevo_precio = precio_actual * factor_multiplicador

                # Validar que el nuevo precio esté en rango válido
                if self.validate_precio(nuevo_precio):
                    safe_set(producto, 'precio_unitario', nuevo_precio)

                    # Actualizar observaciones
                    obs_actuales = safe_str(producto, 'observaciones', '')
                    nuevas_obs = f"{obs_actuales}\n{observacion} ({precio_actual} → {nuevo_precio})".strip(
                    )
                    safe_set(producto, 'observaciones', nuevas_obs)

                    productos_actualizados += 1
                else:
                    logger.warning(
                        f"Precio resultante inválido para producto {producto.id}: {nuevo_precio}")

            # Confirmar cambios
            db.commit()

            logger.info(
                f"✅ Actualización masiva precios empresa {empresa_id}: "
                f"{productos_actualizados} productos actualizados"
            )
            return productos_actualizados

        except SifenValidationError:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error en actualización masiva precios: {str(e)}")
            raise self._handle_repository_error(e, "bulk_update_prices")
