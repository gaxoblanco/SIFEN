"""
Repository para la gestión de empresas/contribuyentes emisores del sistema SIFEN.

Este módulo maneja todas las operaciones relacionadas con empresas emisoras:
- CRUD de empresas por usuario
- Validación de RUC único
- Búsquedas por RUC, razón social
- Gestión de empresas activas/inactivas
- Configuración SIFEN específica
- Estadísticas de emisión

Características específicas:
- Validación RUC paraguayo obligatorio
- RUC único globalmente (no por usuario)
- Gestión de establecimientos y puntos expedición
- Configuración ambiente SIFEN (test/production)
- Relación 1:N con usuarios (una empresa, múltiples usuarios)
- Integración con módulos SIFEN

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    SifenValidationError,
    SifenEntityNotFoundError,
    SifenRUCValidationError
)
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreateDTO, EmpresaUpdateDTO, AmbienteSifenEnum
from app.utils.ruc_utils import is_valid_ruc
from .base import BaseRepository, RepositoryFilter
from .utils import safe_get, safe_set, safe_bool, safe_str

# Configurar logging
logger = logging.getLogger(__name__)


class EmpresaRepository(BaseRepository[Empresa, EmpresaCreateDTO, EmpresaUpdateDTO]):
    """
    Repository para gestión de empresas/contribuyentes emisores SIFEN.

    Hereda de BaseRepository todas las operaciones CRUD básicas y
    añade funcionalidades específicas para empresas:

    - Búsquedas por RUC (único global)
    - Validaciones específicas de emisor
    - Gestión de configuración SIFEN
    - Estadísticas de emisión
    - Relación con usuarios del sistema
    """

    def __init__(self):
        """Inicializa el repository de empresas."""
        super().__init__(Empresa)
        logger.debug("EmpresaRepository inicializado")

    # === MÉTODOS DE BÚSQUEDA POR IDENTIFICACIÓN ===

    def get_by_ruc(self, db: Session, *, ruc: str) -> Optional[Empresa]:
        """
        Busca una empresa por su RUC.

        Args:
            db: Sesión de base de datos
            ruc: RUC de la empresa (con o sin guion y DV)

        Returns:
            Optional[Empresa]: Empresa encontrada o None

        Note:
            El RUC es único globalmente en todo el sistema
        """
        try:
            # Normalizar RUC
            normalized_ruc = self._normalize_ruc(ruc)

            query = select(Empresa).where(Empresa.ruc == normalized_ruc)
            empresa = db.execute(query).scalar_one_or_none()

            if empresa:
                logger.debug(f"✅ Empresa encontrada por RUC: {ruc}")
            else:
                logger.debug(f"❌ Empresa no encontrada por RUC: {ruc}")

            return empresa

        except Exception as e:
            logger.error(f"❌ Error buscando empresa por RUC {ruc}: {str(e)}")
            raise self._handle_repository_error(e, "get_by_ruc")

    def get_by_razon_social(self, db: Session, *, razon_social: str) -> Optional[Empresa]:
        """
        Busca una empresa por su razón social.

        Args:
            db: Sesión de base de datos
            razon_social: Razón social de la empresa

        Returns:
            Optional[Empresa]: Empresa encontrada o None
        """
        try:
            query = select(Empresa).where(
                func.lower(Empresa.razon_social) == func.lower(
                    razon_social.strip())
            )
            empresa = db.execute(query).scalar_one_or_none()

            if empresa:
                logger.debug(
                    f"✅ Empresa encontrada por razón social: {razon_social}")
            else:
                logger.debug(
                    f"❌ Empresa no encontrada por razón social: {razon_social}")

            return empresa

        except Exception as e:
            logger.error(
                f"❌ Error buscando empresa por razón social {razon_social}: {str(e)}")
            raise self._handle_repository_error(e, "get_by_razon_social")

    # === MÉTODOS DE GESTIÓN POR USUARIO ===

    def get_by_user(self, db: Session, *, user_id: int, active_only: bool = True) -> List[Empresa]:
        """
        Obtiene todas las empresas de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            active_only: Solo empresas activas

        Returns:
            List[Empresa]: Lista de empresas del usuario
        """
        filters = RepositoryFilter().eq("user_id", user_id)

        if active_only:
            filters = filters.eq("is_active", True)

        return self.get_multi(
            db,
            filters=filters,
            order_by="razon_social",
            order_desc=False
        )

    def get_active_empresas(self, db: Session, *, user_id: Optional[int] = None) -> List[Empresa]:
        """
        Obtiene todas las empresas activas.

        Args:
            db: Sesión de base de datos
            user_id: Filtrar por usuario específico (opcional)

        Returns:
            List[Empresa]: Lista de empresas activas
        """
        filters = RepositoryFilter().eq("is_active", True)

        if user_id:
            filters = filters.eq("user_id", user_id)

        return self.get_multi(
            db,
            filters=filters,
            order_by="razon_social",
            order_desc=False
        )

    def get_by_ambiente_sifen(
        self,
        db: Session,
        *,
        ambiente: AmbienteSifenEnum,
        active_only: bool = True
    ) -> List[Empresa]:
        """
        Obtiene empresas por ambiente SIFEN.

        Args:
            db: Sesión de base de datos
            ambiente: Ambiente SIFEN (test/production)
            active_only: Solo empresas activas

        Returns:
            List[Empresa]: Lista de empresas en el ambiente especificado
        """
        filters = RepositoryFilter().eq("ambiente_sifen", ambiente)

        if active_only:
            filters = filters.eq("is_active", True)

        return self.get_multi(
            db,
            filters=filters,
            order_by="razon_social",
            order_desc=False
        )

    # === MÉTODOS DE BÚSQUEDA ===

    def search_by_name(
        self,
        db: Session,
        *,
        query: str,
        user_id: Optional[int] = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Empresa]:
        """
        Busca empresas por nombre o razón social.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            user_id: Filtrar por usuario (opcional)
            active_only: Solo empresas activas
            limit: Máximo número de resultados

        Returns:
            List[Empresa]: Lista de empresas que coinciden
        """
        try:
            search_pattern = f"%{query.strip().lower()}%"

            # Construir condiciones de búsqueda
            search_conditions = [
                func.lower(Empresa.razon_social).like(search_pattern)
            ]

            # Buscar en nombre_fantasia si existe
            if hasattr(Empresa, 'nombre_fantasia'):
                search_conditions.append(
                    func.lower(Empresa.nombre_fantasia).like(search_pattern)
                )

            sql_query = select(Empresa).where(or_(*search_conditions))

            # Filtrar por usuario si se especifica
            if user_id:
                sql_query = sql_query.where(Empresa.user_id == user_id)

            # Filtrar solo activas si se requiere
            if active_only:
                sql_query = sql_query.where(Empresa.is_active == True)

            # Ordenar y limitar
            sql_query = sql_query.order_by(Empresa.razon_social).limit(limit)

            empresas = list(db.execute(sql_query).scalars().all())

            logger.debug(
                f"✅ Búsqueda empresas '{query}': {len(empresas)} resultados")
            return empresas

        except Exception as e:
            logger.error(
                f"❌ Error buscando empresas con query '{query}': {str(e)}")
            raise self._handle_repository_error(e, "search_by_name")

    def search_empresas(
        self,
        db: Session,
        *,
        query: str,
        user_id: Optional[int] = None,
        ambiente: Optional[AmbienteSifenEnum] = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Empresa]:
        """
        Búsqueda completa de empresas por múltiples campos.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            user_id: Filtrar por usuario (opcional)
            ambiente: Filtrar por ambiente SIFEN (opcional)
            active_only: Solo empresas activas
            limit: Máximo número de resultados

        Returns:
            List[Empresa]: Lista de empresas que coinciden
        """
        try:
            search_pattern = f"%{query.strip().lower()}%"

            # Construir condiciones de búsqueda
            search_conditions = [
                func.lower(Empresa.razon_social).like(search_pattern),
                Empresa.ruc.like(f"%{query.strip()}%")
            ]

            # Incluir nombre_fantasia si existe
            if hasattr(Empresa, 'nombre_fantasia'):
                search_conditions.append(
                    func.lower(Empresa.nombre_fantasia).like(search_pattern)
                )

            # Incluir RUC normalizado en búsqueda si tiene formato válido
            if self._is_potential_ruc(query):
                normalized_ruc = self._normalize_ruc(query)
                search_conditions.append(
                    Empresa.ruc.like(f"%{normalized_ruc}%")
                )

            sql_query = select(Empresa).where(or_(*search_conditions))

            # Filtrar por usuario si se especifica
            if user_id:
                sql_query = sql_query.where(Empresa.user_id == user_id)

            # Filtrar por ambiente SIFEN si se especifica
            if ambiente:
                sql_query = sql_query.where(Empresa.ambiente_sifen == ambiente)

            # Filtrar solo activas si se requiere
            if active_only:
                sql_query = sql_query.where(Empresa.is_active == True)

            # Ordenar y limitar
            sql_query = sql_query.order_by(Empresa.razon_social).limit(limit)

            empresas = list(db.execute(sql_query).scalars().all())

            logger.debug(
                f"✅ Búsqueda completa empresas '{query}': {len(empresas)} resultados")
            return empresas

        except Exception as e:
            logger.error(
                f"❌ Error en búsqueda completa empresas '{query}': {str(e)}")
            raise self._handle_repository_error(e, "search_empresas")

    # === VALIDACIONES ESPECÍFICAS ===

    def is_ruc_available(self, db: Session, *, ruc: str, exclude_empresa_id: Optional[int] = None) -> bool:
        """
        Verifica si un RUC está disponible (único globalmente).

        Args:
            db: Sesión de base de datos
            ruc: RUC a verificar
            exclude_empresa_id: ID de empresa a excluir (para updates)

        Returns:
            bool: True si el RUC está disponible

        Raises:
            SifenRUCValidationError: Si el RUC no es válido
        """
        try:
            # Validar formato RUC
            normalized_ruc = self._normalize_ruc(ruc)
            if not is_valid_ruc(normalized_ruc):
                raise SifenRUCValidationError(
                    ruc=ruc,
                    reason="Formato de RUC inválido para Paraguay"
                )

            query = select(func.count()).where(Empresa.ruc == normalized_ruc)

            # Excluir empresa específica si se proporciona
            if exclude_empresa_id:
                query = query.where(Empresa.id != exclude_empresa_id)

            count = db.execute(query).scalar()
            if count is None:
                count = 0

            is_available = count == 0

            logger.debug(
                f"Verificación disponibilidad RUC '{ruc}': {is_available}")
            return is_available

        except SifenRUCValidationError:
            raise
        except Exception as e:
            logger.error(
                f"❌ Error verificando disponibilidad RUC '{ruc}': {str(e)}")
            raise self._handle_repository_error(e, "is_ruc_available")

    def validate_establecimiento_punto(
        self,
        establecimiento: str,
        punto_expedicion: str
    ) -> bool:
        """
        Valida formato de establecimiento y punto de expedición SIFEN.

        Args:
            establecimiento: Código establecimiento (001-999)
            punto_expedicion: Código punto expedición (001-999)

        Returns:
            bool: True si ambos son válidos

        Raises:
            SifenValidationError: Si algún código es inválido
        """
        # Validar establecimiento
        if not establecimiento or len(establecimiento) != 3 or not establecimiento.isdigit():
            raise SifenValidationError(
                "Establecimiento debe ser 3 dígitos (001-999)",
                field="establecimiento",
                value=establecimiento
            )

        if not (1 <= int(establecimiento) <= 999):
            raise SifenValidationError(
                "Establecimiento debe estar entre 001 y 999",
                field="establecimiento",
                value=establecimiento
            )

        # Validar punto expedición
        if not punto_expedicion or len(punto_expedicion) != 3 or not punto_expedicion.isdigit():
            raise SifenValidationError(
                "Punto expedición debe ser 3 dígitos (001-999)",
                field="punto_expedicion",
                value=punto_expedicion
            )

        if not (1 <= int(punto_expedicion) <= 999):
            raise SifenValidationError(
                "Punto expedición debe estar entre 001 y 999",
                field="punto_expedicion",
                value=punto_expedicion
            )

        return True

    # === OVERRIDE DE MÉTODOS BASE ===

    def create(self, db: Session, *, obj_in: EmpresaCreateDTO, user_id: int) -> Empresa:
        """
        Crea una nueva empresa con validaciones específicas.

        Args:
            db: Sesión de base de datos
            obj_in: Datos de la empresa a crear
            user_id: ID del usuario propietario

        Returns:
            Empresa: Empresa creada

        Raises:
            SifenValidationError: Si las validaciones fallan

        Note:
            user_id se pasa por separado porque no está en el DTO,
            se obtiene del usuario autenticado en el endpoint
        """
        # Validar RUC disponible
        if not self.is_ruc_available(db, ruc=obj_in.ruc):
            raise SifenValidationError(
                f"El RUC '{obj_in.ruc}' ya está registrado en el sistema",
                field="ruc",
                value=obj_in.ruc
            )

        # Validar establecimiento y punto expedición
        self.validate_establecimiento_punto(
            obj_in.establecimiento,
            obj_in.punto_expedicion
        )

        # Preparar datos para crear, añadiendo user_id
        obj_data = obj_in.model_dump()
        obj_data['user_id'] = user_id  # Añadir user_id del usuario autenticado

        # Normalizar RUC
        obj_data['ruc'] = self._normalize_ruc(obj_data['ruc'])

        # Llamar al método base para crear
        empresa = super().create(db, obj_in=obj_data)

        logger.info(
            f"✅ Empresa creada exitosamente: ID={empresa.id}, "
            f"RUC={safe_str(empresa, 'ruc')}, user_id={user_id}"
        )

        return empresa

    def update(self, db: Session, *, db_obj: Empresa, obj_in: EmpresaUpdateDTO) -> Empresa:
        """
        Actualiza una empresa con validaciones específicas.

        Args:
            db: Sesión de base de datos
            db_obj: Empresa existente
            obj_in: Datos de actualización

        Returns:
            Empresa: Empresa actualizada

        Note:
            El EmpresaUpdateDTO no permite cambiar RUC por razones de integridad fiscal
        """
        # Nota: EmpresaUpdateDTO no permite cambiar RUC según el schema
        # El RUC es inmutable después de la creación por razones fiscales

        # Validar establecimiento y punto expedición si se están cambiando
        new_establecimiento = getattr(obj_in, 'establecimiento', None)
        new_punto = getattr(obj_in, 'punto_expedicion', None)

        if new_establecimiento or new_punto:
            # Usar valores actuales si no se están cambiando
            establecimiento = new_establecimiento or safe_str(
                db_obj, 'establecimiento')
            punto_expedicion = new_punto or safe_str(
                db_obj, 'punto_expedicion')

            self.validate_establecimiento_punto(
                establecimiento, punto_expedicion)

        # Validaciones adicionales para campos específicos
        if hasattr(obj_in, 'ambiente_sifen') and getattr(obj_in, 'ambiente_sifen', None):
            # Logging del cambio de ambiente (importante para auditoría)
            old_ambiente = safe_str(db_obj, 'ambiente_sifen')
            new_ambiente = obj_in.ambiente_sifen
            if old_ambiente != new_ambiente:
                logger.warning(
                    f"🔄 Cambio de ambiente SIFEN empresa {db_obj.id}: "
                    f"{old_ambiente} → {new_ambiente}"
                )

        # Llamar al método base para actualizar
        empresa = super().update(db, db_obj=db_obj, obj_in=obj_in)

        logger.info(
            f"✅ Empresa actualizada: ID={empresa.id}, RUC={safe_str(empresa, 'ruc')}")

        return empresa

    # === MÉTODOS DE ESTADO ===

    def activate_empresa(self, db: Session, *, empresa_id: int) -> Empresa:
        """
        Activa una empresa previamente desactivada.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa a activar

        Returns:
            Empresa: Empresa activada

        Raises:
            SifenEntityNotFoundError: Si la empresa no existe
        """
        try:
            empresa = self.get_by_id_or_404(db, id=empresa_id)

            # Usar helper type-safe para actualizar
            safe_set(empresa, 'is_active', True)

            db.add(empresa)
            db.commit()
            db.refresh(empresa)

            logger.info(
                f"✅ Empresa activada: ID={empresa_id}, RUC={safe_str(empresa, 'ruc')}")
            return empresa

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error activando empresa {empresa_id}: {str(e)}")
            raise self._handle_repository_error(e, "activate_empresa")

    def deactivate_empresa(self, db: Session, *, empresa_id: int) -> Empresa:
        """
        Desactiva una empresa (soft delete).

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa a desactivar

        Returns:
            Empresa: Empresa desactivada

        Raises:
            SifenEntityNotFoundError: Si la empresa no existe
        """
        try:
            empresa = self.get_by_id_or_404(db, id=empresa_id)

            # Usar helper type-safe para actualizar
            safe_set(empresa, 'is_active', False)

            db.add(empresa)
            db.commit()
            db.refresh(empresa)

            logger.info(
                f"✅ Empresa desactivada: ID={empresa_id}, RUC={safe_str(empresa, 'ruc')}")
            return empresa

        except Exception as e:
            db.rollback()
            logger.error(
                f"❌ Error desactivando empresa {empresa_id}: {str(e)}")
            raise self._handle_repository_error(e, "deactivate_empresa")

    # === MÉTODOS PRIVADOS ===

    def _normalize_ruc(self, ruc: str) -> str:
        """
        Normaliza un RUC eliminando espacios, guiones y caracteres especiales.

        Args:
            ruc: RUC a normalizar

        Returns:
            str: RUC normalizado
        """
        if not ruc:
            return ""

        # Eliminar espacios, guiones y caracteres especiales
        normalized = "".join(c for c in ruc if c.isdigit())
        return normalized

    def _is_potential_ruc(self, text: str) -> bool:
        """
        Verifica si un texto podría ser un RUC.

        Args:
            text: Texto a verificar

        Returns:
            bool: True si parece un RUC
        """
        # RUC paraguayo tiene 8-9 dígitos
        digits_only = "".join(c for c in text if c.isdigit())
        return len(digits_only) >= 7 and len(digits_only) <= 9

    def _handle_repository_error(self, exception: Exception, operation: str):
        """
        Maneja errores específicos del repository de empresas.

        Args:
            exception: Excepción original
            operation: Operación que falló

        Returns:
            Exception: Excepción SIFEN apropiada
        """
        from app.core.exceptions import handle_database_exception

        # Usar el handler genérico de la base
        return handle_database_exception(exception, f"empresa_{operation}")

    # === MÉTODOS DE ESTADÍSTICAS ===

    def get_empresa_stats(self, db: Session, *, empresa_id: int) -> dict:
        """
        Obtiene estadísticas básicas de una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            dict: Estadísticas de la empresa
        """
        try:
            empresa = self.get_by_id_or_404(db, id=empresa_id)

            # Estadísticas básicas
            stats = {
                "empresa_id": empresa_id,
                "ruc": safe_str(empresa, 'ruc'),
                "razon_social": safe_str(empresa, 'razon_social'),
                "ambiente_sifen": safe_str(empresa, 'ambiente_sifen'),
                "is_active": safe_bool(empresa, 'is_active'),
                "establecimiento": safe_str(empresa, 'establecimiento'),
                "punto_expedicion": safe_str(empresa, 'punto_expedicion'),
                "created_at": safe_get(empresa, 'created_at'),
                "updated_at": safe_get(empresa, 'updated_at')
            }

            # TODO: Añadir estadísticas de documentos emitidos cuando
            # estén implementados los repositories de factura/documento

            logger.debug(f"✅ Estadísticas empresa {empresa_id} obtenidas")
            return stats

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo estadísticas empresa {empresa_id}: {str(e)}")
            raise self._handle_repository_error(e, "get_empresa_stats")

    def get_global_stats(self, db: Session) -> dict:
        """
        Obtiene estadísticas globales de empresas en el sistema.

        Args:
            db: Sesión de base de datos

        Returns:
            dict: Estadísticas globales
        """
        try:
            total_empresas = self.count(db)
            active_empresas = self.count(
                db, filters=RepositoryFilter().eq("is_active", True))

            # Estadísticas por ambiente
            test_empresas = self.count(
                db, filters=RepositoryFilter().eq("ambiente_sifen", AmbienteSifenEnum.TEST))
            production_empresas = self.count(
                db, filters=RepositoryFilter().eq("ambiente_sifen", AmbienteSifenEnum.PRODUCTION))

            stats = {
                "total_empresas": total_empresas,
                "active_empresas": active_empresas,
                "inactive_empresas": total_empresas - active_empresas,
                "test_empresas": test_empresas,
                "production_empresas": production_empresas,
                "activity_rate": round((active_empresas / total_empresas * 100) if total_empresas > 0 else 0, 2)
            }

            logger.debug(f"✅ Estadísticas globales empresas: {stats}")
            return stats

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo estadísticas globales empresas: {str(e)}")
            raise self._handle_repository_error(e, "get_global_stats")
