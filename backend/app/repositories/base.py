"""
Módulo base para el patrón Repository en el sistema SIFEN.

Este módulo define el BaseRepository genérico que proporciona operaciones
CRUD comunes y manejo consistente de errores para todas las entidades.

Características principales:
- Patrón Repository genérico con Python Generics
- Operaciones CRUD estándar (Create, Read, Update, Delete)
- Manejo consistente de excepciones SQLAlchemy → SIFEN
- Paginación y filtros dinámicos
- Logging estructurado
- Type hints completos
- Context managers para transacciones

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from contextlib import contextmanager
from typing import (
    Any, Dict, Generic, List, Optional, Type, TypeVar, Union,
    Sequence, Tuple
)

from sqlalchemy import and_, func, select, update, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select
from pydantic import BaseModel

from app.core.database import get_db_context
from app.core.exceptions import (
    SifenDatabaseError,
    SifenEntityNotFoundError,
    SifenDuplicateEntityError,
    handle_database_exception
)
from app.models.base import BaseModel as SQLABaseModel

# Configurar logging
logger = logging.getLogger(__name__)

# === TIPOS GENÉRICOS ===

# T = Tipo de modelo SQLAlchemy (User, Empresa, etc.)
ModelType = TypeVar("ModelType", bound=SQLABaseModel)

# C = Tipo de schema Pydantic para crear
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)

# U = Tipo de schema Pydantic para actualizar
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


# === CLASES DE FILTRADO ===

class RepositoryFilter:
    """
    Clase para construir filtros dinámicos de forma type-safe.

    Permite construir filtros como:
    filter = RepositoryFilter().eq("email", "test@test.com").gt("id", 100)
    """

    def __init__(self):
        self.conditions: List[Any] = []

    def eq(self, field: str, value: Any) -> "RepositoryFilter":
        """Filtro de igualdad: field = value"""
        return self._add_condition(field, "==", value)

    def ne(self, field: str, value: Any) -> "RepositoryFilter":
        """Filtro de desigualdad: field != value"""
        return self._add_condition(field, "!=", value)

    def gt(self, field: str, value: Any) -> "RepositoryFilter":
        """Filtro mayor que: field > value"""
        return self._add_condition(field, ">", value)

    def gte(self, field: str, value: Any) -> "RepositoryFilter":
        """Filtro mayor o igual: field >= value"""
        return self._add_condition(field, ">=", value)

    def lt(self, field: str, value: Any) -> "RepositoryFilter":
        """Filtro menor que: field < value"""
        return self._add_condition(field, "<", value)

    def lte(self, field: str, value: Any) -> "RepositoryFilter":
        """Filtro menor o igual: field <= value"""
        return self._add_condition(field, "<=", value)

    def like(self, field: str, pattern: str) -> "RepositoryFilter":
        """Filtro LIKE: field LIKE pattern (case sensitive)"""
        return self._add_condition(field, "like", pattern)

    def ilike(self, field: str, pattern: str) -> "RepositoryFilter":
        """Filtro ILIKE: field ILIKE pattern (case insensitive)"""
        return self._add_condition(field, "ilike", pattern)

    def in_(self, field: str, values: List[Any]) -> "RepositoryFilter":
        """Filtro IN: field IN (values)"""
        return self._add_condition(field, "in_", values)

    def is_null(self, field: str) -> "RepositoryFilter":
        """Filtro IS NULL: field IS NULL"""
        return self._add_condition(field, "is_null", None)

    def is_not_null(self, field: str) -> "RepositoryFilter":
        """Filtro IS NOT NULL: field IS NOT NULL"""
        return self._add_condition(field, "is_not_null", None)

    def _add_condition(self, field: str, operator: str, value: Any) -> "RepositoryFilter":
        """Añade una condición al filtro"""
        self.conditions.append((field, operator, value))
        return self

    def apply_to_query(self, query: Select, model_class: Type[ModelType]) -> Select:
        """
        Aplica todas las condiciones de filtro a una query SQLAlchemy.

        Args:
            query: Query SQLAlchemy a filtrar
            model_class: Clase del modelo para acceder a los campos

        Returns:
            Select: Query con filtros aplicados
        """
        for field, operator, value in self.conditions:
            # Obtener el atributo del modelo
            if not hasattr(model_class, field):
                logger.warning(
                    f"Campo '{field}' no existe en {model_class.__name__}")
                continue

            model_field = getattr(model_class, field)

            # Aplicar el operador correspondiente
            if operator == "==":
                query = query.where(model_field == value)
            elif operator == "!=":
                query = query.where(model_field != value)
            elif operator == ">":
                query = query.where(model_field > value)
            elif operator == ">=":
                query = query.where(model_field >= value)
            elif operator == "<":
                query = query.where(model_field < value)
            elif operator == "<=":
                query = query.where(model_field <= value)
            elif operator == "like":
                query = query.where(model_field.like(value))
            elif operator == "ilike":
                query = query.where(model_field.ilike(value))
            elif operator == "in_":
                query = query.where(model_field.in_(value))
            elif operator == "is_null":
                query = query.where(model_field.is_(None))
            elif operator == "is_not_null":
                query = query.where(model_field.is_not(None))

        return query


class PaginationResult(Generic[ModelType]):
    """
    Resultado de una consulta paginada.

    Attributes:
        items: Lista de elementos en la página actual
        total: Total de elementos que cumplen el filtro
        page: Página actual (1-based)
        per_page: Elementos por página
        total_pages: Total de páginas
        has_next: True si hay página siguiente
        has_prev: True si hay página anterior
    """

    def __init__(
        self,
        items: List[ModelType],
        total: int,
        page: int,
        per_page: int
    ):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.total_pages = (total + per_page - 1) // per_page
        self.has_next = page < self.total_pages
        self.has_prev = page > 1

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario para APIs"""
        return {
            "items": self.items,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "per_page": self.per_page,
                "total_pages": self.total_pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev
            }
        }


# === REPOSITORY BASE ===

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Repository base genérico que proporciona operaciones CRUD estándar.

    Este repository maneja:
    - Operaciones CRUD básicas
    - Manejo consistente de errores
    - Paginación y filtros
    - Logging de operaciones
    - Validaciones básicas

    Type Parameters:
        ModelType: Tipo del modelo SQLAlchemy (ej: User, Empresa)
        CreateSchemaType: Schema Pydantic para creación
        UpdateSchemaType: Schema Pydantic para actualización

    Ejemplo:
        class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
            pass
    """

    def __init__(self, model: Type[ModelType]):
        """
        Inicializa el repository.

        Args:
            model: Clase del modelo SQLAlchemy
        """
        self.model = model
        self.model_name = model.__name__
        logger.debug(f"Inicializando repository para {self.model_name}")

    # === OPERACIONES CRUD BÁSICAS ===

    def create(
        self,
        db: Session,
        *,
        obj_in: Union[CreateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Crea una nueva entidad en la base de datos.

        Args:
            db: Sesión de base de datos
            obj_in: Datos para crear la entidad (Pydantic model o dict)

        Returns:
            ModelType: Entidad creada

        Raises:
            SifenDuplicateEntityError: Si la entidad ya existe
            SifenDatabaseError: Error de base de datos
        """
        try:
            # Convertir Pydantic model a dict si es necesario
            if isinstance(obj_in, dict):
                obj_data = obj_in
            elif hasattr(obj_in, 'model_dump'):
                obj_data = obj_in.model_dump(exclude_unset=True)
            else:
                # Fallback para otros tipos de BaseModel
                obj_data = obj_in.__dict__

            # Crear instancia del modelo
            db_obj = self.model(**obj_data)

            # Guardar en BD
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            logger.info(f"✅ {self.model_name} creado: ID={db_obj.id}")
            return db_obj

        except IntegrityError as e:
            db.rollback()
            logger.error(
                f"❌ Error de integridad creando {self.model_name}: {str(e)}")
            raise SifenDuplicateEntityError(
                entity_type=self.model_name,
                field="unknown",
                value="unknown",
                original_exception=e
            )
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"❌ Error BD creando {self.model_name}: {str(e)}")
            raise handle_database_exception(
                e, f"create_{self.model_name.lower()}")
        except Exception as e:
            db.rollback()
            logger.error(
                f"❌ Error inesperado creando {self.model_name}: {str(e)}")
            raise SifenDatabaseError(
                f"Error inesperado creando {self.model_name}: {str(e)}",
                operation=f"create_{self.model_name.lower()}",
                original_exception=e
            )

    def get_by_id(self, db: Session, *, id: int) -> Optional[ModelType]:
        """
        Obtiene una entidad por su ID.

        Args:
            db: Sesión de base de datos
            id: ID de la entidad

        Returns:
            Optional[ModelType]: Entidad encontrada o None
        """
        try:
            query = select(self.model).where(self.model.id == id)
            result = db.execute(query).scalar_one_or_none()

            if result:
                logger.debug(f"✅ {self.model_name} encontrado: ID={id}")
            else:
                logger.debug(f"❌ {self.model_name} no encontrado: ID={id}")

            return result

        except SQLAlchemyError as e:
            logger.error(
                f"❌ Error BD obteniendo {self.model_name} ID={id}: {str(e)}")
            raise handle_database_exception(
                e, f"get_{self.model_name.lower()}_by_id")

    def get_by_id_or_404(self, db: Session, *, id: int) -> ModelType:
        """
        Obtiene una entidad por ID o lanza excepción si no existe.

        Args:
            db: Sesión de base de datos
            id: ID de la entidad

        Returns:
            ModelType: Entidad encontrada

        Raises:
            SifenEntityNotFoundError: Si la entidad no existe
        """
        obj = self.get_by_id(db, id=id)
        if not obj:
            raise SifenEntityNotFoundError(
                entity_type=self.model_name,
                entity_id=id
            )
        return obj

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[RepositoryFilter] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        Obtiene múltiples entidades con paginación y filtros.

        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar
            filters: Filtros a aplicar
            order_by: Campo por el cual ordenar
            order_desc: True para orden descendente

        Returns:
            List[ModelType]: Lista de entidades
        """
        try:
            query = select(self.model)

            # Aplicar filtros
            if filters:
                query = filters.apply_to_query(query, self.model)

            # Aplicar ordenamiento
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(order_field.desc())
                else:
                    query = query.order_by(order_field.asc())

            # Aplicar paginación
            query = query.offset(skip).limit(limit)

            # Ejecutar query
            result = db.execute(query).scalars().all()

            logger.debug(
                f"✅ {self.model_name} obtenidos: {len(result)} registros")
            return list(result)

        except SQLAlchemyError as e:
            logger.error(f"❌ Error BD obteniendo {self.model_name}: {str(e)}")
            raise handle_database_exception(
                e, f"get_multi_{self.model_name.lower()}")

    def get_paginated(
        self,
        db: Session,
        *,
        page: int = 1,
        per_page: int = 20,
        filters: Optional[RepositoryFilter] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> PaginationResult[ModelType]:
        """
        Obtiene entidades con paginación completa.

        Args:
            db: Sesión de base de datos
            page: Número de página (1-based)
            per_page: Elementos por página
            filters: Filtros a aplicar
            order_by: Campo por el cual ordenar
            order_desc: True para orden descendente

        Returns:
            PaginationResult[ModelType]: Resultado paginado
        """
        # Validar parámetros
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        if per_page > 100:
            per_page = 100

        try:
            # Query base para contar
            count_query = select(func.count()).select_from(self.model)

            # Query para obtener datos
            data_query = select(self.model)

            # Aplicar filtros a ambas queries
            if filters:
                count_query = filters.apply_to_query(count_query, self.model)
                data_query = filters.apply_to_query(data_query, self.model)

            # Obtener total de registros
            total = db.execute(count_query).scalar()
            if total is None:
                total = 0

            # Aplicar ordenamiento y paginación a query de datos
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_desc:
                    data_query = data_query.order_by(order_field.desc())
                else:
                    data_query = data_query.order_by(order_field.asc())

            # Calcular offset
            offset = (page - 1) * per_page
            data_query = data_query.offset(offset).limit(per_page)

            # Ejecutar query de datos
            items = list(db.execute(data_query).scalars().all())

            logger.debug(
                f"✅ {self.model_name} paginados: página {page}, "
                f"{len(items)} de {total} total"
            )

            return PaginationResult(
                items=items,
                total=total,
                page=page,
                per_page=per_page
            )

        except SQLAlchemyError as e:
            logger.error(f"❌ Error BD paginando {self.model_name}: {str(e)}")
            raise handle_database_exception(
                e, f"paginate_{self.model_name.lower()}")

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Actualiza una entidad existente.

        Args:
            db: Sesión de base de datos
            db_obj: Entidad existente a actualizar
            obj_in: Datos para actualizar (Pydantic model o dict)

        Returns:
            ModelType: Entidad actualizada

        Raises:
            SifenDatabaseError: Error de base de datos
        """
        try:
            # Convertir Pydantic model a dict si es necesario
            if isinstance(obj_in, dict):
                update_data = obj_in
            elif hasattr(obj_in, 'model_dump'):
                update_data = obj_in.model_dump(exclude_unset=True)
            else:
                # Fallback para otros tipos de BaseModel
                update_data = obj_in.__dict__

            # Actualizar solo campos proporcionados
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Guardar cambios
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            logger.info(f"✅ {self.model_name} actualizado: ID={db_obj.id}")
            return db_obj

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                f"❌ Error BD actualizando {self.model_name}: {str(e)}")
            raise handle_database_exception(
                e, f"update_{self.model_name.lower()}")
        except Exception as e:
            db.rollback()
            logger.error(
                f"❌ Error inesperado actualizando {self.model_name}: {str(e)}")
            raise SifenDatabaseError(
                f"Error inesperado actualizando {self.model_name}: {str(e)}",
                operation=f"update_{self.model_name.lower()}",
                original_exception=e
            )

    def delete(self, db: Session, *, id: int) -> bool:
        """
        Elimina una entidad por su ID.

        Args:
            db: Sesión de base de datos
            id: ID de la entidad a eliminar

        Returns:
            bool: True si se eliminó, False si no existía

        Raises:
            SifenDatabaseError: Error de base de datos
        """
        try:
            # Verificar si existe
            obj = self.get_by_id(db, id=id)
            if not obj:
                logger.debug(
                    f"❌ {self.model_name} no encontrado para eliminar: ID={id}")
                return False

            # Eliminar
            db.delete(obj)
            db.commit()

            logger.info(f"✅ {self.model_name} eliminado: ID={id}")
            return True

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"❌ Error BD eliminando {self.model_name}: {str(e)}")
            raise handle_database_exception(
                e, f"delete_{self.model_name.lower()}")
        except Exception as e:
            db.rollback()
            logger.error(
                f"❌ Error inesperado eliminando {self.model_name}: {str(e)}")
            raise SifenDatabaseError(
                f"Error inesperado eliminando {self.model_name}: {str(e)}",
                operation=f"delete_{self.model_name.lower()}",
                original_exception=e
            )

    # === OPERACIONES DE UTILIDAD ===

    def exists(self, db: Session, *, id: int) -> bool:
        """
        Verifica si existe una entidad con el ID dado.

        Args:
            db: Sesión de base de datos
            id: ID a verificar

        Returns:
            bool: True si existe, False en caso contrario
        """
        try:
            query = select(func.count()).where(self.model.id == id)
            count = db.execute(query).scalar()
            if count is None:
                count = 0
            exists = count > 0

            logger.debug(
                f"Verificación existencia {self.model_name} ID={id}: {exists}")
            return exists

        except SQLAlchemyError as e:
            logger.error(
                f"❌ Error BD verificando existencia {self.model_name}: {str(e)}")
            raise handle_database_exception(
                e, f"exists_{self.model_name.lower()}")

    def count(
        self,
        db: Session,
        *,
        filters: Optional[RepositoryFilter] = None
    ) -> int:
        """
        Cuenta el número de entidades que cumplen los filtros.

        Args:
            db: Sesión de base de datos
            filters: Filtros a aplicar

        Returns:
            int: Número de entidades
        """
        try:
            query = select(func.count()).select_from(self.model)

            # Aplicar filtros
            if filters:
                query = filters.apply_to_query(query, self.model)

            count = db.execute(query).scalar()
            if count is None:
                count = 0

            logger.debug(f"Conteo {self.model_name}: {count} registros")
            return count

        except SQLAlchemyError as e:
            logger.error(f"❌ Error BD contando {self.model_name}: {str(e)}")
            raise handle_database_exception(
                e, f"count_{self.model_name.lower()}")

    def find_by(
        self,
        db: Session,
        *,
        filters: Optional[RepositoryFilter] = None,
        limit: Optional[int] = None,
        **field_filters
    ) -> List[ModelType]:
        """
        Busca entidades usando filtros dinámicos.

        Args:
            db: Sesión de base de datos
            filters: Filtros estructurados
            limit: Límite de resultados
            **field_filters: Filtros de igualdad por campo

        Returns:
            List[ModelType]: Entidades encontradas

        Ejemplo:
            # Buscar usuarios activos con email específico
            users = repo.find_by(db, is_active=True, email="test@test.com", limit=10)
        """
        try:
            query = select(self.model)

            # Aplicar filtros estructurados
            if filters:
                query = filters.apply_to_query(query, self.model)

            # Aplicar filtros de campo directo
            for field, value in field_filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
                else:
                    logger.warning(
                        f"Campo '{field}' no existe en {self.model_name}")

            # Aplicar límite
            if limit:
                query = query.limit(limit)

            result = list(db.execute(query).scalars().all())

            logger.debug(
                f"✅ Búsqueda {self.model_name}: {len(result)} resultados "
                f"con filtros {field_filters}"
            )
            return result

        except SQLAlchemyError as e:
            logger.error(f"❌ Error BD buscando {self.model_name}: {str(e)}")
            raise handle_database_exception(
                e, f"find_{self.model_name.lower()}")

    # === CONTEXT MANAGERS ===

    def transaction(self):
        """
        Context manager para transacciones manuales.

        Uso:
            with repo.transaction() as db:
                repo.create(db, obj_in=data1)
                repo.create(db, obj_in=data2)
                # Auto commit al final, rollback en excepción
        """
        return get_db_context()

    # === MÉTODOS DE INFORMACIÓN ===

    def get_model_name(self) -> str:
        """Retorna el nombre del modelo"""
        return self.model_name

    def get_model_class(self) -> Type[ModelType]:
        """Retorna la clase del modelo"""
        return self.model

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(model={self.model_name})>"


# === EXPORTS ===

__all__ = [
    # Clases principales
    "BaseRepository",
    "RepositoryFilter",
    "PaginationResult",

    # Type hints
    "ModelType",
    "CreateSchemaType",
    "UpdateSchemaType"
]
