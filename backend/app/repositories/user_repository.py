"""
Repository para la gestión de usuarios del sistema SIFEN.

Este módulo maneja todas las operaciones relacionadas con usuarios:
- Autenticación y verificación de credenciales
- Gestión de usuarios activos/inactivos
- Búsquedas por email, username
- Actualización de información de usuario
- Logging de actividad de usuarios

Características específicas:
- Validación de email único
- Validación de username único
- Hashing de contraseñas con bcrypt
- Manejo de estado de usuario (activo/inactivo)
- Tracking de último login
- Búsquedas case-insensitive

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    SifenAuthenticationError,
    SifenEntityNotFoundError,
    SifenValidationError
)
from app.core.security import verify_password
from app.models.user import User
from app.schemas.user import UserCreateDTO, UserUpdateDTO
from .base import BaseRepository, RepositoryFilter
from .utils import safe_get, safe_set, safe_bool, safe_str

# Configurar logging
logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User, UserCreateDTO, UserUpdateDTO]):
    """
    Repository para gestión de usuarios del sistema SIFEN.

    Hereda de BaseRepository todas las operaciones CRUD básicas y
    añade funcionalidades específicas para usuarios:

    - Autenticación con email/password
    - Búsquedas por email y username únicos
    - Gestión de estados de usuario
    - Tracking de actividad
    - Validaciones específicas de usuario
    """

    def __init__(self):
        """Inicializa el repository de usuarios."""
        super().__init__(User)
        logger.debug("UserRepository inicializado")

    # === MÉTODOS DE AUTENTICACIÓN ===

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """
        Busca un usuario por su email.

        Args:
            db: Sesión de base de datos
            email: Email del usuario (case-insensitive)

        Returns:
            Optional[User]: Usuario encontrado o None

        Note:
            El email se busca de forma case-insensitive para mejorar UX
        """
        try:
            query = select(User).where(
                func.lower(User.email) == func.lower(email.strip())
            )
            user = db.execute(query).scalar_one_or_none()

            if user:
                logger.debug(f"✅ Usuario encontrado por email: {email}")
            else:
                logger.debug(f"❌ Usuario no encontrado por email: {email}")

            return user

        except Exception as e:
            logger.error(
                f"❌ Error buscando usuario por email {email}: {str(e)}")
            raise self._handle_repository_error(e, "get_by_email")

    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """
        Busca un usuario por su username.

        Args:
            db: Sesión de base de datos
            username: Username del usuario (case-insensitive)

        Returns:
            Optional[User]: Usuario encontrado o None
        """
        try:
            query = select(User).where(
                func.lower(User.username) == func.lower(username.strip())
            )
            user = db.execute(query).scalar_one_or_none()

            if user:
                logger.debug(f"✅ Usuario encontrado por username: {username}")
            else:
                logger.debug(
                    f"❌ Usuario no encontrado por username: {username}")

            return user

        except Exception as e:
            logger.error(
                f"❌ Error buscando usuario por username {username}: {str(e)}")
            raise self._handle_repository_error(e, "get_by_username")

    def verify_credentials(
        self,
        db: Session,
        *,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Verifica las credenciales de un usuario.

        Args:
            db: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano

        Returns:
            Optional[User]: Usuario si las credenciales son válidas, None en caso contrario

        Raises:
            SifenAuthenticationError: Si el usuario está inactivo
        """
        try:
            # Buscar usuario por email
            user = self.get_by_email(db, email=email)
            if not user:
                logger.warning(
                    f"🔒 Intento de login con email inexistente: {email}")
                return None

            # Verificar que el usuario esté activo
            if not safe_bool(user, 'is_active', True):
                logger.warning(
                    f"🔒 Intento de login con usuario inactivo: {email}")
                raise SifenAuthenticationError(
                    f"Usuario {email} está inactivo",
                    details={"email": email, "reason": "user_inactive"}
                )

            # Verificar contraseña
            user_hashed_password = safe_str(user, 'hashed_password', '')
            if not verify_password(password, user_hashed_password):
                logger.warning(
                    f"🔒 Contraseña incorrecta para usuario: {email}")
                return None

            logger.info(f"✅ Credenciales válidas para usuario: {email}")
            return user

        except SifenAuthenticationError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            logger.error(
                f"❌ Error verificando credenciales para {email}: {str(e)}")
            raise self._handle_repository_error(e, "verify_credentials")

    def authenticate(
        self,
        db: Session,
        *,
        identifier: str,
        password: str
    ) -> Optional[User]:
        """
        Autentica un usuario usando email o username.

        Args:
            db: Sesión de base de datos
            identifier: Email o username del usuario
            password: Contraseña en texto plano

        Returns:
            Optional[User]: Usuario autenticado o None

        Note:
            Intenta primero con email, luego con username para flexibilidad
        """
        try:
            # Primero intentar como email
            user = self.verify_credentials(
                db, email=identifier, password=password)
            if user:
                return user

            # Si no funciona como email, intentar como username
            user_by_username = self.get_by_username(db, username=identifier)
            if user_by_username:
                # Usar helper type-safe para obtener el email
                user_email = safe_str(user_by_username, 'email', '')
                return self.verify_credentials(
                    db,
                    email=user_email,
                    password=password
                )

            logger.warning(
                f"🔒 Autenticación fallida para identificador: {identifier}")
            return None

        except Exception as e:
            logger.error(
                f"❌ Error en autenticación para {identifier}: {str(e)}")
            raise self._handle_repository_error(e, "authenticate")

    # === MÉTODOS DE GESTIÓN DE USUARIOS ===

    def update_last_login(self, db: Session, *, user_id: int) -> User:
        """
        Actualiza la fecha de último login de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            User: Usuario actualizado

        Raises:
            SifenEntityNotFoundError: Si el usuario no existe
        """
        try:
            user = self.get_by_id_or_404(db, id=user_id)

            # Usar helper type-safe para actualizar
            safe_set(user, 'last_login', datetime.utcnow())

            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(
                f"✅ Último login actualizado para usuario ID: {user_id}")
            return user

        except Exception as e:
            db.rollback()
            logger.error(
                f"❌ Error actualizando último login para usuario {user_id}: {str(e)}")
            raise self._handle_repository_error(e, "update_last_login")

    def deactivate_user(self, db: Session, *, user_id: int) -> User:
        """
        Desactiva un usuario (soft delete).

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario a desactivar

        Returns:
            User: Usuario desactivado

        Raises:
            SifenEntityNotFoundError: Si el usuario no existe
        """
        try:
            user = self.get_by_id_or_404(db, id=user_id)

            # Usar helper type-safe para actualizar
            safe_set(user, 'is_active', False)

            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(
                f"✅ Usuario desactivado: ID={user_id}, email={safe_str(user, 'email', 'N/A')}")
            return user

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error desactivando usuario {user_id}: {str(e)}")
            raise self._handle_repository_error(e, "deactivate_user")

    def activate_user(self, db: Session, *, user_id: int) -> User:
        """
        Activa un usuario previamente desactivado.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario a activar

        Returns:
            User: Usuario activado

        Raises:
            SifenEntityNotFoundError: Si el usuario no existe
        """
        try:
            user = self.get_by_id_or_404(db, id=user_id)

            # Usar helper type-safe para actualizar
            safe_set(user, 'is_active', True)

            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(
                f"✅ Usuario activado: ID={user_id}, email={safe_str(user, 'email', 'N/A')}")
            return user

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error activando usuario {user_id}: {str(e)}")
            raise self._handle_repository_error(e, "activate_user")

    # === MÉTODOS DE BÚSQUEDA ===

    def get_active_users(self, db: Session) -> List[User]:
        """
        Obtiene todos los usuarios activos.

        Args:
            db: Sesión de base de datos

        Returns:
            List[User]: Lista de usuarios activos
        """
        filter_active = RepositoryFilter().eq("is_active", True)
        return self.get_multi(
            db,
            filters=filter_active,
            order_by="created_at",
            order_desc=True
        )

    def get_inactive_users(self, db: Session) -> List[User]:
        """
        Obtiene todos los usuarios inactivos.

        Args:
            db: Sesión de base de datos

        Returns:
            List[User]: Lista de usuarios inactivos
        """
        filter_inactive = RepositoryFilter().eq("is_active", False)
        return self.get_multi(
            db,
            filters=filter_inactive,
            order_by="updated_at",
            order_desc=True
        )

    def search_users(
        self,
        db: Session,
        *,
        query: str,
        active_only: bool = True,
        limit: int = 50
    ) -> List[User]:
        """
        Busca usuarios por nombre, email o username.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            active_only: Solo buscar usuarios activos
            limit: Máximo número de resultados

        Returns:
            List[User]: Lista de usuarios que coinciden
        """
        try:
            # Construir filtros de búsqueda
            search_pattern = f"%{query.strip().lower()}%"

            sql_query = select(User).where(
                or_(
                    func.lower(User.first_name).like(search_pattern),
                    func.lower(User.last_name).like(search_pattern),
                    func.lower(User.email).like(search_pattern),
                    func.lower(User.username).like(search_pattern)
                )
            )

            # Filtrar solo activos si se requiere
            if active_only:
                sql_query = sql_query.where(User.is_active == True)

            # Ordenar y limitar
            sql_query = sql_query.order_by(
                User.first_name, User.last_name).limit(limit)

            users = list(db.execute(sql_query).scalars().all())

            logger.debug(
                f"✅ Búsqueda usuarios '{query}': {len(users)} resultados")
            return users

        except Exception as e:
            logger.error(
                f"❌ Error buscando usuarios con query '{query}': {str(e)}")
            raise self._handle_repository_error(e, "search_users")

    def get_users_by_role(
        self,
        db: Session,
        *,
        role: str,
        active_only: bool = True
    ) -> List[User]:
        """
        Obtiene usuarios por su rol.

        Args:
            db: Sesión de base de datos
            role: Rol a buscar
            active_only: Solo usuarios activos

        Returns:
            List[User]: Lista de usuarios con el rol especificado
        """
        filters = RepositoryFilter().eq("role", role)

        if active_only:
            filters = filters.eq("is_active", True)

        return self.get_multi(
            db,
            filters=filters,
            order_by="created_at",
            order_desc=True
        )

    # === MÉTODOS DE VALIDACIÓN ===

    def is_email_available(self, db: Session, *, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        Verifica si un email está disponible para uso.

        Args:
            db: Sesión de base de datos
            email: Email a verificar
            exclude_user_id: ID de usuario a excluir de la búsqueda (para updates)

        Returns:
            bool: True si el email está disponible, False si ya está en uso
        """
        try:
            query = select(func.count()).where(
                func.lower(User.email) == func.lower(email.strip())
            )

            # Excluir usuario específico si se proporciona (útil para updates)
            if exclude_user_id:
                query = query.where(User.id != exclude_user_id)

            count = db.execute(query).scalar()
            if count is None:
                count = 0
            is_available = count == 0

            logger.debug(
                f"Verificación disponibilidad email '{email}': {is_available}")
            return is_available

        except Exception as e:
            logger.error(
                f"❌ Error verificando disponibilidad email '{email}': {str(e)}")
            raise self._handle_repository_error(e, "is_email_available")

    def is_username_available(self, db: Session, *, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        Verifica si un username está disponible para uso.

        Args:
            db: Sesión de base de datos
            username: Username a verificar
            exclude_user_id: ID de usuario a excluir de la búsqueda

        Returns:
            bool: True si el username está disponible, False si ya está en uso
        """
        try:
            query = select(func.count()).where(
                func.lower(User.username) == func.lower(username.strip())
            )

            # Excluir usuario específico si se proporciona
            if exclude_user_id:
                query = query.where(User.id != exclude_user_id)

            count = db.execute(query).scalar()
            if count is None:
                count = 0
            is_available = count == 0

            logger.debug(
                f"Verificación disponibilidad username '{username}': {is_available}")
            return is_available

        except Exception as e:
            logger.error(
                f"❌ Error verificando disponibilidad username '{username}': {str(e)}")
            raise self._handle_repository_error(e, "is_username_available")

    # === OVERRIDE DE MÉTODOS BASE ===

    def create(self, db: Session, *, obj_in: UserCreateDTO) -> User:
        """
        Crea un nuevo usuario con validaciones específicas.

        Args:
            db: Sesión de base de datos
            obj_in: Datos del usuario a crear

        Returns:
            User: Usuario creado

        Raises:
            SifenValidationError: Si el email o username ya existen
        """
        # Validar email único
        if not self.is_email_available(db, email=obj_in.email):
            raise SifenValidationError(
                f"El email '{obj_in.email}' ya está en uso",
                field="email",
                value=obj_in.email
            )

        # Nota: UserCreateDTO no tiene campo 'username', solo email y full_name
        # Si en el futuro se añade username al DTO, descomentar:
        # if hasattr(obj_in, 'username') and obj_in.username:
        #     if not self.is_username_available(db, username=obj_in.username):
        #         raise SifenValidationError(
        #             f"El username '{obj_in.username}' ya está en uso",
        #             field="username",
        #             value=obj_in.username
        #         )

        # Llamar al método base para crear
        user = super().create(db, obj_in=obj_in)

        logger.info(
            f"✅ Usuario creado exitosamente: ID={user.id}, "
            f"email={safe_str(user, 'email')}"
        )

        return user

    def update(self, db: Session, *, db_obj: User, obj_in: UserUpdateDTO) -> User:
        """
        Actualiza un usuario con validaciones específicas.

        Args:
            db: Sesión de base de datos
            db_obj: Usuario existente
            obj_in: Datos de actualización

        Returns:
            User: Usuario actualizado

        Raises:
            SifenValidationError: Si el email o username ya existen
        """
        # Nota: UserUpdateDTO no permite cambiar email según el schema actual
        # Solo permite actualizar: full_name, password, confirm_password
        # Si en el futuro se añade email al UserUpdateDTO, descomentar:
        # if hasattr(obj_in, 'email') and obj_in.email and obj_in.email != safe_str(db_obj, 'email'):
        #     if not self.is_email_available(db, email=obj_in.email, exclude_user_id=db_obj.id):
        #         raise SifenValidationError(
        #             f"El email '{obj_in.email}' ya está en uso",
        #             field="email",
        #             value=obj_in.email
        #         )

        # Validaciones para campos que SÍ existen en UserUpdateDTO:
        # - full_name: Validado por Pydantic en el DTO
        # - password: Validado por Pydantic en el DTO
        # - confirm_password: Validado por Pydantic en el DTO

        # Nota: UserUpdateDTO no tiene campo 'username' según el schema actual
        # Si en el futuro se añade username al DTO, descomentar y ajustar:
        # if (hasattr(obj_in, 'username') and
        #     obj_in.username and
        #     obj_in.username != safe_str(db_obj, 'username')):
        #
        #     if not self.is_username_available(db, username=obj_in.username, exclude_user_id=db_obj.id):
        #         raise SifenValidationError(
        #             f"El username '{obj_in.username}' ya está en uso",
        #             field="username",
        #             value=obj_in.username
        #         )

        # Llamar al método base para actualizar
        user = super().update(db, db_obj=db_obj, obj_in=obj_in)

        logger.info(
            f"✅ Usuario actualizado: ID={user.id}, email={safe_str(user, 'email')}")

        return user

    # === MÉTODOS DE UTILIDAD PRIVADOS ===

    def _handle_repository_error(self, exception: Exception, operation: str):
        """
        Maneja errores específicos del repository de usuarios.

        Args:
            exception: Excepción original
            operation: Operación que falló

        Returns:
            Exception: Excepción SIFEN apropiada
        """
        from app.core.exceptions import handle_database_exception

        # Usar el handler genérico de la base
        return handle_database_exception(exception, f"user_{operation}")

    # === MÉTODOS DE ESTADÍSTICAS ===

    def get_user_stats(self, db: Session) -> dict:
        """
        Obtiene estadísticas básicas de usuarios.

        Args:
            db: Sesión de base de datos

        Returns:
            dict: Estadísticas de usuarios
        """
        try:
            total_users = self.count(db)
            active_users = self.count(
                db, filters=RepositoryFilter().eq("is_active", True))
            inactive_users = total_users - active_users

            # Contar por roles si existe el campo
            stats = {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": inactive_users,
                "activity_rate": round((active_users / total_users * 100) if total_users > 0 else 0, 2)
            }

            logger.debug(f"✅ Estadísticas usuarios obtenidas: {stats}")
            return stats

        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas usuarios: {str(e)}")
            raise self._handle_repository_error(e, "get_user_stats")
