"""
Repository para la gestión de clientes/receptores del sistema SIFEN.

Este módulo maneja todas las operaciones relacionadas con clientes:
- CRUD de clientes por empresa
- Validación de RUC si es contribuyente
- Búsquedas por nombre, RUC, documento
- Gestión de clientes activos/inactivos
- Estadísticas de clientes por empresa

Características específicas:
- Validación RUC paraguayo (opcional para clientes)
- Búsquedas case-insensitive por múltiples campos
- Filtros por empresa propietaria
- Gestión de tipos de cliente (contribuyente/no contribuyente)
- Relación con facturas emitidas
- Historial de transacciones

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
from app.models.cliente import Cliente, TipoClienteEnum, TipoDocumentoEnum
from app.schemas.cliente import ClienteCreateDTO, ClienteUpdateDTO
from app.utils.ruc_utils import is_valid_ruc
from .base import BaseRepository, RepositoryFilter
from .utils import safe_get, safe_set, safe_bool, safe_str

# Configurar logging
logger = logging.getLogger(__name__)


class ClienteRepository(BaseRepository[Cliente, ClienteCreateDTO, ClienteUpdateDTO]):
    """
    Repository para gestión de clientes/receptores del sistema SIFEN.

    Hereda de BaseRepository todas las operaciones CRUD básicas y
    añade funcionalidades específicas para clientes:

    - Búsquedas por RUC, nombre, documento
    - Filtros por empresa propietaria
    - Validaciones específicas de cliente
    - Gestión de tipos de cliente
    - Estadísticas por empresa
    """

    def __init__(self):
        """Inicializa el repository de clientes."""
        super().__init__(Cliente)
        logger.debug("ClienteRepository inicializado")

    # === MÉTODOS DE BÚSQUEDA POR IDENTIFICACIÓN ===

    def get_by_numero_documento(
        self,
        db: Session,
        *,
        numero_documento: str,
        empresa_id: Optional[int] = None
    ) -> Optional[Cliente]:
        """
        Busca un cliente por su número de documento.

        Args:
            db: Sesión de base de datos
            numero_documento: Número de documento del cliente
            empresa_id: Filtrar por empresa específica (opcional)

        Returns:
            Optional[Cliente]: Cliente encontrado o None

        Note:
            Busca en cualquier tipo de documento (RUC, CI, Pasaporte, etc.)
        """
        try:
            # Normalizar número de documento
            numero_normalizado = numero_documento.strip()

            query = select(Cliente).where(
                Cliente.numero_documento == numero_normalizado)

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.where(Cliente.empresa_id == empresa_id)

            cliente = db.execute(query).scalar_one_or_none()

            if cliente:
                logger.debug(
                    f"✅ Cliente encontrado por documento: {numero_documento}")
            else:
                logger.debug(
                    f"❌ Cliente no encontrado por documento: {numero_documento}")

            return cliente

        except Exception as e:
            logger.error(
                f"❌ Error buscando cliente por documento {numero_documento}: {str(e)}")
            raise self._handle_repository_error(e, "get_by_numero_documento")

    def get_by_ruc(self, db: Session, *, ruc: str, empresa_id: Optional[int] = None) -> Optional[Cliente]:
        """
        Busca un cliente por su RUC (solo si es contribuyente).

        Args:
            db: Sesión de base de datos
            ruc: RUC del cliente (con o sin guion y DV)
            empresa_id: Filtrar por empresa específica (opcional)

        Returns:
            Optional[Cliente]: Cliente encontrado o None

        Note:
            Busca solo en clientes con tipo_documento = RUC
        """
        try:
            # Normalizar RUC
            normalized_ruc = self._normalize_ruc(ruc)

            query = select(Cliente).where(
                and_(
                    Cliente.numero_documento == normalized_ruc,
                    Cliente.tipo_documento == TipoDocumentoEnum.RUC
                )
            )

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.where(Cliente.empresa_id == empresa_id)

            cliente = db.execute(query).scalar_one_or_none()

            if cliente:
                logger.debug(f"✅ Cliente encontrado por RUC: {ruc}")
            else:
                logger.debug(f"❌ Cliente no encontrado por RUC: {ruc}")

            return cliente

        except Exception as e:
            logger.error(f"❌ Error buscando cliente por RUC {ruc}: {str(e)}")
            raise self._handle_repository_error(e, "get_by_ruc")

    # === MÉTODOS DE GESTIÓN POR EMPRESA ===

    def get_by_empresa(
        self,
        db: Session,
        *,
        empresa_id: int,
        active_only: bool = True,
        limit: Optional[int] = None
    ) -> List[Cliente]:
        """
        Obtiene todos los clientes de una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            active_only: Solo clientes activos
            limit: Límite de resultados (opcional)

        Returns:
            List[Cliente]: Lista de clientes de la empresa
        """
        filters = RepositoryFilter().eq("empresa_id", empresa_id)

        if active_only:
            filters = filters.eq("is_active", True)

        return self.get_multi(
            db,
            filters=filters,
            order_by="created_at",
            order_desc=True,
            limit=limit or 100
        )

    def get_active_clientes(self, db: Session, *, empresa_id: int) -> List[Cliente]:
        """
        Obtiene todos los clientes activos de una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            List[Cliente]: Lista de clientes activos
        """
        return self.get_by_empresa(db, empresa_id=empresa_id, active_only=True)

    def get_clientes_by_tipo(
        self,
        db: Session,
        *,
        tipo_cliente: TipoClienteEnum,
        empresa_id: int,
        active_only: bool = True
    ) -> List[Cliente]:
        """
        Obtiene clientes por su tipo.

        Args:
            db: Sesión de base de datos
            tipo_cliente: Tipo de cliente a filtrar
            empresa_id: ID de la empresa
            active_only: Solo clientes activos

        Returns:
            List[Cliente]: Lista de clientes del tipo especificado
        """
        filters = (RepositoryFilter()
                   .eq("empresa_id", empresa_id)
                   .eq("tipo_cliente", tipo_cliente))

        if active_only:
            filters = filters.eq("is_active", True)

        return self.get_multi(
            db,
            filters=filters,
            order_by="created_at",
            order_desc=True
        )

    # === MÉTODOS DE BÚSQUEDA ===

    def search_by_name(
        self,
        db: Session,
        *,
        query: str,
        empresa_id: int,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Cliente]:
        """
        Busca clientes por nombre o razón social.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            empresa_id: ID de la empresa
            active_only: Solo clientes activos
            limit: Máximo número de resultados

        Returns:
            List[Cliente]: Lista de clientes que coinciden
        """
        try:
            search_pattern = f"%{query.strip().lower()}%"

            # Construir condiciones de búsqueda en múltiples campos
            search_conditions = []

            # Buscar en razon_social si existe
            if hasattr(Cliente, 'razon_social'):
                search_conditions.append(
                    func.lower(Cliente.razon_social).like(search_pattern)
                )

            # Buscar en nombres si existe
            if hasattr(Cliente, 'nombres'):
                search_conditions.append(
                    func.lower(Cliente.nombres).like(search_pattern)
                )

            # Buscar en apellidos si existe
            if hasattr(Cliente, 'apellidos'):
                search_conditions.append(
                    func.lower(Cliente.apellidos).like(search_pattern)
                )

            # Buscar en nombre_fantasia si existe
            if hasattr(Cliente, 'nombre_fantasia'):
                search_conditions.append(
                    func.lower(Cliente.nombre_fantasia).like(search_pattern)
                )

            # Si no hay campos de nombre, salir temprano
            if not search_conditions:
                logger.warning(
                    "No se encontraron campos de nombre para buscar")
                return []

            sql_query = select(Cliente).where(
                and_(
                    Cliente.empresa_id == empresa_id,
                    or_(*search_conditions)
                )
            )

            # Filtrar solo activos si se requiere
            if active_only:
                sql_query = sql_query.where(Cliente.is_active == True)

            # Ordenar y limitar
            sql_query = sql_query.order_by(
                Cliente.created_at.desc()).limit(limit)

            clientes = list(db.execute(sql_query).scalars().all())

            logger.debug(
                f"✅ Búsqueda clientes '{query}': {len(clientes)} resultados")
            return clientes

        except Exception as e:
            logger.error(
                f"❌ Error buscando clientes con query '{query}': {str(e)}")
            raise self._handle_repository_error(e, "search_by_name")

    def search_clientes(
        self,
        db: Session,
        *,
        query: str,
        empresa_id: int,
        tipo_cliente: Optional[TipoClienteEnum] = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Cliente]:
        """
        Búsqueda completa de clientes por múltiples campos.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            empresa_id: ID de la empresa
            tipo_cliente: Filtrar por tipo de cliente (opcional)
            active_only: Solo clientes activos
            limit: Máximo número de resultados

        Returns:
            List[Cliente]: Lista de clientes que coinciden
        """
        try:
            search_pattern = f"%{query.strip().lower()}%"

            # Construir condiciones de búsqueda básicas
            search_conditions = [
                Cliente.numero_documento.like(f"%{query.strip()}%")
            ]

            # Añadir búsquedas en campos de nombre si existen
            if hasattr(Cliente, 'razon_social'):
                search_conditions.append(
                    func.lower(Cliente.razon_social).like(search_pattern)
                )
            if hasattr(Cliente, 'nombres'):
                search_conditions.append(
                    func.lower(Cliente.nombres).like(search_pattern)
                )
            if hasattr(Cliente, 'apellidos'):
                search_conditions.append(
                    func.lower(Cliente.apellidos).like(search_pattern)
                )

            # Incluir RUC en búsqueda si tiene formato válido
            if self._is_potential_ruc(query):
                normalized_ruc = self._normalize_ruc(query)
                search_conditions.append(
                    Cliente.numero_documento.like(f"%{normalized_ruc}%")
                )

            sql_query = select(Cliente).where(
                and_(
                    Cliente.empresa_id == empresa_id,
                    or_(*search_conditions)
                )
            )

            # Filtrar por tipo de cliente si se especifica
            if tipo_cliente:
                sql_query = sql_query.where(
                    Cliente.tipo_cliente == tipo_cliente)

            # Filtrar solo activos si se requiere
            if active_only:
                sql_query = sql_query.where(Cliente.is_active == True)

            # Ordenar y limitar
            sql_query = sql_query.order_by(
                Cliente.created_at.desc()).limit(limit)

            clientes = list(db.execute(sql_query).scalars().all())

            logger.debug(
                f"✅ Búsqueda completa clientes '{query}': {len(clientes)} resultados")
            return clientes

        except Exception as e:
            logger.error(
                f"❌ Error en búsqueda completa clientes '{query}': {str(e)}")
            raise self._handle_repository_error(e, "search_clientes")

    # === MÉTODOS DE FILTRADO POR TIPO ===

    def get_contribuyentes(self, db: Session, *, empresa_id: int) -> List[Cliente]:
        """
        Obtiene solo los clientes que son contribuyentes.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            List[Cliente]: Lista de clientes contribuyentes
        """
        filters = (RepositoryFilter()
                   .eq("empresa_id", empresa_id)
                   .eq("contribuyente", True)
                   .eq("is_active", True))

        return self.get_multi(
            db,
            filters=filters,
            order_by="created_at",
            order_desc=True
        )

    def get_no_contribuyentes(self, db: Session, *, empresa_id: int) -> List[Cliente]:
        """
        Obtiene solo los clientes que no son contribuyentes.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            List[Cliente]: Lista de clientes no contribuyentes
        """
        filters = (RepositoryFilter()
                   .eq("empresa_id", empresa_id)
                   .eq("contribuyente", False)
                   .eq("is_active", True))

        return self.get_multi(
            db,
            filters=filters,
            order_by="created_at",
            order_desc=True
        )

    # === VALIDACIONES ESPECÍFICAS ===

    def is_documento_available_in_empresa(
        self,
        db: Session,
        *,
        numero_documento: str,
        empresa_id: int,
        exclude_cliente_id: Optional[int] = None
    ) -> bool:
        """
        Verifica si un documento está disponible dentro de una empresa.

        Args:
            db: Sesión de base de datos
            numero_documento: Número del documento
            empresa_id: ID de la empresa
            exclude_cliente_id: ID de cliente a excluir

        Returns:
            bool: True si el documento está disponible
        """
        try:
            query = select(func.count()).where(
                and_(
                    Cliente.numero_documento == numero_documento.strip(),
                    Cliente.empresa_id == empresa_id
                )
            )

            if exclude_cliente_id:
                query = query.where(Cliente.id != exclude_cliente_id)

            count = db.execute(query).scalar()
            if count is None:
                count = 0

            is_available = count == 0

            logger.debug(
                f"Verificación documento {numero_documento} empresa {empresa_id}: {is_available}")
            return is_available

        except Exception as e:
            logger.error(f"❌ Error verificando documento: {str(e)}")
            raise self._handle_repository_error(
                e, "is_documento_available_in_empresa")

    def validate_ruc_if_contribuyente(self, numero_documento: str, es_contribuyente: bool) -> bool:
        """
        Valida RUC si el cliente es contribuyente.

        Args:
            numero_documento: Número de documento a validar
            es_contribuyente: Si el cliente es contribuyente

        Returns:
            bool: True si es válido

        Raises:
            SifenRUCValidationError: Si es contribuyente y el RUC no es válido
        """
        if not es_contribuyente:
            return True  # No contribuyentes no necesitan RUC válido

        # Normalizar RUC
        normalized_ruc = self._normalize_ruc(numero_documento)

        if not is_valid_ruc(normalized_ruc):
            raise SifenRUCValidationError(
                ruc=numero_documento,
                reason="Formato de RUC inválido para Paraguay"
            )

        return True

    # === OVERRIDE DE MÉTODOS BASE ===

    def create(self, db: Session, *, obj_in: ClienteCreateDTO, empresa_id: int) -> Cliente:
        """
        Crea un nuevo cliente con validaciones específicas.

        Args:
            db: Sesión de base de datos
            obj_in: Datos del cliente a crear
            empresa_id: ID de la empresa (del usuario autenticado)

        Returns:
            Cliente: Cliente creado

        Raises:
            SifenValidationError: Si las validaciones fallan

        Note:
            empresa_id se pasa por separado porque no está en el DTO,
            se obtiene del usuario autenticado en el endpoint
        """
        # Validar documento disponible
        if not self.is_documento_available_in_empresa(
            db,
            numero_documento=obj_in.numero_documento,
            empresa_id=empresa_id
        ):
            raise SifenValidationError(
                f"El documento '{obj_in.numero_documento}' ya está registrado para esta empresa",
                field="numero_documento",
                value=obj_in.numero_documento
            )

        # Validar RUC si es contribuyente
        es_contribuyente = getattr(obj_in, 'contribuyente', False)
        self.validate_ruc_if_contribuyente(
            obj_in.numero_documento, es_contribuyente)

        # Preparar datos para crear, añadiendo empresa_id
        obj_data = obj_in.model_dump()
        # Añadir empresa_id del usuario autenticado
        obj_data['empresa_id'] = empresa_id

        # Normalizar RUC si es contribuyente
        if es_contribuyente and getattr(obj_in, 'tipo_documento', None) == TipoDocumentoEnum.RUC:
            obj_data['numero_documento'] = self._normalize_ruc(
                obj_data['numero_documento'])

        # Llamar al método base para crear
        cliente = super().create(db, obj_in=obj_data)

        logger.info(
            f"✅ Cliente creado exitosamente: ID={cliente.id}, "
            f"documento={safe_str(cliente, 'numero_documento')}, empresa_id={empresa_id}"
        )

        return cliente

    def update(self, db: Session, *, db_obj: Cliente, obj_in: ClienteUpdateDTO) -> Cliente:
        """
        Actualiza un cliente con validaciones específicas.

        Args:
            db: Sesión de base de datos
            db_obj: Cliente existente
            obj_in: Datos de actualización

        Returns:
            Cliente: Cliente actualizado

        Note:
            El ClienteUpdateDTO no permite cambiar tipo_documento ni numero_documento
            por razones de integridad fiscal
        """
        # Validar documento disponible si se está cambiando
        # Nota: ClienteUpdateDTO no permite cambiar numero_documento según el schema
        # Si en el futuro se permite, descomentar y ajustar:
        # if (hasattr(obj_in, 'numero_documento') and
        #     getattr(obj_in, 'numero_documento', None) and
        #     obj_in.numero_documento != safe_str(db_obj, 'numero_documento')):
        #
        #     if not self.is_documento_available_in_empresa(
        #         db,
        #         numero_documento=obj_in.numero_documento,
        #         empresa_id=safe_get(db_obj, 'empresa_id'),
        #         exclude_cliente_id=db_obj.id
        #     ):
        #         raise SifenValidationError(
        #             f"El documento '{obj_in.numero_documento}' ya está registrado para esta empresa",
        #             field="numero_documento",
        #             value=obj_in.numero_documento
        #         )

        # Validar RUC si se está cambiando el estado de contribuyente
        # Nota: ClienteUpdateDTO probablemente no permite cambiar 'contribuyente'
        # pero lo dejamos por si se añade en el futuro
        new_contribuyente = getattr(obj_in, 'contribuyente', None)

        if new_contribuyente is not None:
            documento_actual = safe_str(db_obj, 'numero_documento')
            self.validate_ruc_if_contribuyente(
                documento_actual, new_contribuyente)

        # Nota: No se normalizan RUCs en updates porque numero_documento no se puede cambiar

        # Llamar al método base para actualizar
        cliente = super().update(db, db_obj=db_obj, obj_in=obj_in)

        logger.info(
            f"✅ Cliente actualizado: ID={cliente.id}, documento={safe_str(cliente, 'numero_documento')}")

        return cliente

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
        Maneja errores específicos del repository de clientes.

        Args:
            exception: Excepción original
            operation: Operación que falló

        Returns:
            Exception: Excepción SIFEN apropiada
        """
        from app.core.exceptions import handle_database_exception

        # Usar el handler genérico de la base
        return handle_database_exception(exception, f"cliente_{operation}")

    # === MÉTODOS DE ESTADÍSTICAS ===

    def get_cliente_stats(self, db: Session, *, empresa_id: int) -> dict:
        """
        Obtiene estadísticas básicas de clientes para una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa

        Returns:
            dict: Estadísticas de clientes
        """
        try:
            base_filter = RepositoryFilter().eq("empresa_id", empresa_id)

            total_clientes = self.count(db, filters=base_filter)

            active_filter = base_filter.eq("is_active", True)
            active_clientes = self.count(db, filters=active_filter)

            # Estadísticas por tipo contribuyente
            contribuyentes_filter = active_filter.eq("contribuyente", True)
            contribuyentes = self.count(db, filters=contribuyentes_filter)
            no_contribuyentes = active_clientes - contribuyentes

            stats = {
                "total_clientes": total_clientes,
                "active_clientes": active_clientes,
                "inactive_clientes": total_clientes - active_clientes,
                "contribuyentes": contribuyentes,
                "no_contribuyentes": no_contribuyentes,
                "activity_rate": round((active_clientes / total_clientes * 100) if total_clientes > 0 else 0, 2)
            }

            logger.debug(
                f"✅ Estadísticas clientes empresa {empresa_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(
                f"❌ Error obteniendo estadísticas clientes empresa {empresa_id}: {str(e)}")
            raise self._handle_repository_error(e, "get_cliente_stats")
