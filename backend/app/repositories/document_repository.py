"""
Repository para la gestión de documentos electrónicos SIFEN.

Este módulo maneja todas las operaciones relacionadas con documentos electrónicos:
- CRUD de documentos por empresa
- Filtros por tipo, estado, fecha
- Búsquedas por CDC, número, cliente
- Gestión de estados del flujo SIFEN
- Validaciones específicas de documentos
- Estadísticas y reportes

Tipos de documentos soportados:
- Factura Electrónica (FE) - Tipo 1
- Autofactura Electrónica (AFE) - Tipo 4
- Nota de Crédito Electrónica (NCE) - Tipo 5
- Nota de Débito Electrónica (NDE) - Tipo 6
- Nota de Remisión Electrónica (NRE) - Tipo 7

Flujo de estados:
borrador → validado → generado → firmado → enviado → aprobado/rechazado

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.exceptions import (
    SifenValidationError,
    SifenEntityNotFoundError,
    SifenDuplicateEntityError,
    SifenBusinessError
)
from app.models.documento import (
    Documento,
    FacturaElectronica,
    AutofacturaElectronica,
    NotaCreditoElectronica,
    NotaDebitoElectronica,
    NotaRemisionElectronica,
    TipoDocumentoSifenEnum,
    EstadoDocumentoSifenEnum,
    MonedaSifenEnum,
    TipoOperacionSifenEnum,
    CondicionOperacionSifenEnum
)
from app.schemas.documento import DocumentoCreateDTO, DocumentoUpdateDTO
from .base import BaseRepository, RepositoryFilter
from .utils import safe_get, safe_set, safe_bool, safe_str, safe_datetime

# Configurar logging
logger = logging.getLogger(__name__)


class DocumentoRepository(BaseRepository[Documento, DocumentoCreateDTO, DocumentoUpdateDTO]):
    """
    Repository para gestión de documentos electrónicos SIFEN.

    Hereda de BaseRepository todas las operaciones CRUD básicas y
    añade funcionalidades específicas para documentos:

    - Búsquedas por CDC, número, cliente, fecha
    - Filtros por tipo de documento, estado, empresa
    - Gestión de estados del flujo SIFEN
    - Validaciones específicas de documentos
    - Estadísticas por empresa y período
    - Operaciones especializadas por tipo
    """

    def __init__(self):
        """Inicializa el repository de documentos."""
        super().__init__(Documento)
        logger.debug("DocumentoRepository inicializado")

    # ===============================================
    # MÉTODOS DE BÚSQUEDA POR IDENTIFICACIÓN
    # ===============================================

    def get_by_cdc(
        self,
        db: Session,
        *,
        cdc: str,
        empresa_id: Optional[int] = None
    ) -> Optional[Documento]:
        """
        Busca un documento por su CDC (Código de Control del Documento).

        Args:
            db: Sesión de base de datos
            cdc: CDC de 44 dígitos del documento
            empresa_id: Filtrar por empresa específica (opcional)

        Returns:
            Optional[Documento]: Documento encontrado o None

        Note:
            CDC es único a nivel nacional según normativa SIFEN
        """
        try:
            # Normalizar CDC (eliminar espacios y guiones)
            cdc_normalizado = self._normalize_cdc(cdc)

            query = select(Documento).where(
                Documento.cdc == cdc_normalizado)

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.where(Documento.empresa_id == empresa_id)

            documento = db.execute(query).scalar_one_or_none()

            if documento:
                logger.debug(f"✅ Documento encontrado por CDC: {cdc[:8]}...")
            else:
                logger.debug(
                    f"❌ Documento no encontrado por CDC: {cdc[:8]}...")

            return documento

        except Exception as e:
            logger.error(
                f"❌ Error buscando documento por CDC {cdc[:8]}...: {str(e)}")
            raise self._handle_repository_error(e, "get_by_cdc")

    def get_by_numero_completo(
        self,
        db: Session,
        *,
        establecimiento: str,
        punto_expedicion: str,
        numero_documento: str,
        empresa_id: int
    ) -> Optional[Documento]:
        """
        Busca un documento por su numeración completa.

        Args:
            db: Sesión de base de datos
            establecimiento: Código establecimiento (001-999)
            punto_expedicion: Punto expedición (001-999)
            numero_documento: Número documento (0000001-9999999)
            empresa_id: ID de la empresa emisora

        Returns:
            Optional[Documento]: Documento encontrado o None
        """
        try:
            query = select(Documento).where(
                and_(
                    Documento.establecimiento == establecimiento.zfill(3),
                    Documento.punto_expedicion == punto_expedicion.zfill(3),
                    Documento.numero_documento == numero_documento.zfill(7),
                    Documento.empresa_id == empresa_id
                )
            )

            documento = db.execute(query).scalar_one_or_none()
            numero_completo = f"{establecimiento}-{punto_expedicion}-{numero_documento}"

            if documento:
                logger.debug(
                    f"✅ Documento encontrado por número: {numero_completo}")
            else:
                logger.debug(
                    f"❌ Documento no encontrado por número: {numero_completo}")

            return documento

        except Exception as e:
            logger.error(f"❌ Error buscando documento por número: {str(e)}")
            raise self._handle_repository_error(e, "get_by_numero_completo")

    def get_by_numero_protocolo(
        self,
        db: Session,
        *,
        numero_protocolo: str,
        empresa_id: Optional[int] = None
    ) -> Optional[Documento]:
        """
        Busca un documento por su número de protocolo SIFEN.

        Args:
            db: Sesión de base de datos
            numero_protocolo: Número de protocolo asignado por SIFEN
            empresa_id: Filtrar por empresa específica (opcional)

        Returns:
            Optional[Documento]: Documento encontrado o None
        """
        try:
            query = select(Documento).where(
                Documento.numero_protocolo == numero_protocolo.strip())

            if empresa_id:
                query = query.where(Documento.empresa_id == empresa_id)

            documento = db.execute(query).scalar_one_or_none()

            if documento:
                logger.debug(
                    f"✅ Documento encontrado por protocolo: {numero_protocolo}")
            else:
                logger.debug(
                    f"❌ Documento no encontrado por protocolo: {numero_protocolo}")

            return documento

        except Exception as e:
            logger.error(f"❌ Error buscando documento por protocolo: {str(e)}")
            raise self._handle_repository_error(e, "get_by_numero_protocolo")

    # ===============================================
    # MÉTODOS DE GESTIÓN POR EMPRESA Y TIPO
    # ===============================================

    def get_by_empresa(
        self,
        db: Session,
        *,
        empresa_id: int,
        active_only: bool = True,
        limit: Optional[int] = None
    ) -> List[Documento]:
        """
        Obtiene todos los documentos de una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            active_only: Solo documentos activos
            limit: Límite de resultados (opcional)

        Returns:
            List[Documento]: Lista de documentos de la empresa
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

    def get_by_tipo_documento(
        self,
        db: Session,
        *,
        tipo_documento: str,
        empresa_id: int,
        active_only: bool = True,
        limit: Optional[int] = 50
    ) -> List[Documento]:
        """
        Obtiene documentos por su tipo específico.

        Args:
            db: Sesión de base de datos
            tipo_documento: Tipo documento SIFEN (1=FE, 4=AFE, 5=NCE, 6=NDE, 7=NRE)
            empresa_id: ID de la empresa
            active_only: Solo documentos activos
            limit: Límite de resultados

        Returns:
            List[Documento]: Lista de documentos del tipo especificado
        """
        filters = (RepositoryFilter()
                   .eq("empresa_id", empresa_id)
                   .eq("tipo_documento", tipo_documento))

        if active_only:
            filters = filters.eq("is_active", True)

        return self.get_multi(
            db,
            filters=filters,
            order_by="created_at",
            order_desc=True,
            limit=limit
        )

    def get_by_estado(
        self,
        db: Session,
        *,
        estado: str,
        empresa_id: int,
        limit: Optional[int] = 50
    ) -> List[Documento]:
        """
        Obtiene documentos por su estado actual.

        Args:
            db: Sesión de base de datos
            estado: Estado del documento
            empresa_id: ID de la empresa
            limit: Límite de resultados

        Returns:
            List[Documento]: Lista de documentos en el estado especificado
        """
        filters = (RepositoryFilter()
                   .eq("empresa_id", empresa_id)
                   .eq("estado", estado)
                   .eq("is_active", True))

        return self.get_multi(
            db,
            filters=filters,
            order_by="created_at",
            order_desc=True,
            limit=limit
        )

    # ===============================================
    # MÉTODOS DE FILTRADO POR FECHA Y PERÍODO
    # ===============================================

    def get_by_fecha_emision(
        self,
        db: Session,
        *,
        fecha_desde: date,
        fecha_hasta: date,
        empresa_id: int,
        tipo_documento: Optional[str] = None,
        estado: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> List[Documento]:
        """
        Obtiene documentos por rango de fechas de emisión.

        Args:
            db: Sesión de base de datos
            fecha_desde: Fecha inicio del rango
            fecha_hasta: Fecha fin del rango (inclusive)
            empresa_id: ID de la empresa
            tipo_documento: Filtrar por tipo específico (opcional)
            estado: Filtrar por estado específico (opcional)
            limit: Límite de resultados

        Returns:
            List[Documento]: Lista de documentos en el rango de fechas
        """
        try:
            query = select(Documento).where(
                and_(
                    Documento.empresa_id == empresa_id,
                    Documento.fecha_emision >= fecha_desde,
                    Documento.fecha_emision <= fecha_hasta,
                    Documento.is_active == True
                )
            )

            # Aplicar filtros opcionales
            if tipo_documento:
                query = query.where(Documento.tipo_documento == tipo_documento)

            if estado:
                query = query.where(Documento.estado == estado)

            # Ordenar por fecha de emisión descendente
            query = query.order_by(
                Documento.fecha_emision.desc(), Documento.created_at.desc())

            if limit:
                query = query.limit(limit)

            documentos = list(db.execute(query).scalars().all())

            logger.debug(
                f"✅ Documentos por fecha {fecha_desde} - {fecha_hasta}: {len(documentos)} encontrados")
            return documentos

        except Exception as e:
            logger.error(f"❌ Error obteniendo documentos por fecha: {str(e)}")
            raise self._handle_repository_error(e, "get_by_fecha_emision")

    def get_pendientes_envio(
        self,
        db: Session,
        *,
        empresa_id: int,
        horas_limite: int = 72
    ) -> List[Documento]:
        """
        Obtiene documentos pendientes de envío a SIFEN.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            horas_limite: Horas límite desde creación (default 72h SIFEN)

        Returns:
            List[Documento]: Lista de documentos pendientes de envío
        """
        try:
            # Calcular fecha límite
            from datetime import timedelta
            fecha_limite = datetime.now() - timedelta(hours=horas_limite)

            query = select(Documento).where(
                and_(
                    Documento.empresa_id == empresa_id,
                    Documento.estado == EstadoDocumentoSifenEnum.FIRMADO.value,
                    Documento.created_at >= fecha_limite,
                    Documento.is_active == True,
                    Documento.cdc.is_not(None),
                    Documento.xml_firmado.is_not(None)
                )
            ).order_by(Documento.created_at.asc())

            documentos = list(db.execute(query).scalars().all())

            logger.debug(
                f"✅ Documentos pendientes envío empresa {empresa_id}: {len(documentos)}")
            return documentos

        except Exception as e:
            logger.error(f"❌ Error obteniendo documentos pendientes: {str(e)}")
            raise self._handle_repository_error(e, "get_pendientes_envio")

    # ===============================================
    # MÉTODOS DE BÚSQUEDA Y FILTROS AVANZADOS
    # ===============================================

    def search_documentos(
        self,
        db: Session,
        *,
        query: str,
        empresa_id: int,
        tipos_documento: Optional[List[str]] = None,
        estados: Optional[List[str]] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        cliente_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Documento]:
        """
        Búsqueda completa de documentos por múltiples criterios.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda (CDC, número, observaciones)
            empresa_id: ID de la empresa
            tipos_documento: Lista de tipos a incluir (opcional)
            estados: Lista de estados a incluir (opcional)
            fecha_desde: Fecha inicio rango (opcional)
            fecha_hasta: Fecha fin rango (opcional)
            cliente_id: Filtrar por cliente específico (opcional)
            limit: Máximo número de resultados

        Returns:
            List[Documento]: Lista de documentos que coinciden
        """
        try:
            search_pattern = f"%{query.strip().lower()}%"

            # Construir condiciones de búsqueda en múltiples campos
            search_conditions = []

            # Buscar en CDC (primeros 8 caracteres para logging)
            if self._is_potential_cdc(query):
                normalized_cdc = self._normalize_cdc(query)
                search_conditions.append(
                    Documento.cdc.like(f"%{normalized_cdc}%")
                )

            # Buscar en número de documento
            if query.strip().isdigit():
                search_conditions.append(
                    Documento.numero_documento.like(f"%{query.strip()}%")
                )

            # Buscar en número completo (formato XXX-XXX-XXXXXXX)
            if "-" in query:
                search_conditions.append(
                    func.concat(
                        Documento.establecimiento, "-",
                        Documento.punto_expedicion, "-",
                        Documento.numero_documento
                    ).like(f"%{query.strip()}%")
                )

            # Buscar en observaciones y motivo
            search_conditions.extend([
                func.lower(Documento.observaciones).like(search_pattern),
                func.lower(Documento.motivo_emision).like(search_pattern),
                func.lower(Documento.descripcion_operacion).like(
                    search_pattern)
            ])

            # Si no hay condiciones de búsqueda específicas, salir
            if not search_conditions:
                logger.warning(
                    f"Término de búsqueda '{query}' no genera condiciones válidas")
                return []

            sql_query = select(Documento).where(
                and_(
                    Documento.empresa_id == empresa_id,
                    Documento.is_active == True,
                    or_(*search_conditions)
                )
            )

            # Aplicar filtros adicionales
            if tipos_documento:
                sql_query = sql_query.where(
                    Documento.tipo_documento.in_(tipos_documento))

            if estados:
                sql_query = sql_query.where(Documento.estado.in_(estados))

            if fecha_desde:
                sql_query = sql_query.where(
                    Documento.fecha_emision >= fecha_desde)

            if fecha_hasta:
                sql_query = sql_query.where(
                    Documento.fecha_emision <= fecha_hasta)

            if cliente_id:
                sql_query = sql_query.where(Documento.cliente_id == cliente_id)

            # Ordenar por relevancia: CDC exacto > número > fecha reciente
            sql_query = sql_query.order_by(
                Documento.created_at.desc()).limit(limit)

            documentos = list(db.execute(sql_query).scalars().all())

            logger.debug(
                f"✅ Búsqueda documentos '{query}': {len(documentos)} resultados")
            return documentos

        except Exception as e:
            logger.error(f"❌ Error en búsqueda documentos '{query}': {str(e)}")
            raise self._handle_repository_error(e, "search_documentos")

    def filter_documentos_avanzado(
        self,
        db: Session,
        *,
        empresa_id: int,
        tipos_documento: Optional[List[str]] = None,
        estados: Optional[List[str]] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        cliente_id: Optional[int] = None,
        moneda: Optional[str] = None,
        monto_minimo: Optional[Decimal] = None,
        monto_maximo: Optional[Decimal] = None,
        solo_aprobados: bool = False,
        solo_fiscales: bool = False,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Filtrado avanzado de documentos con paginación.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            tipos_documento: Lista de tipos a incluir
            estados: Lista de estados a incluir
            fecha_desde: Fecha inicio rango
            fecha_hasta: Fecha fin rango
            cliente_id: Filtrar por cliente específico
            moneda: Filtrar por moneda
            monto_minimo: Monto mínimo del documento
            monto_maximo: Monto máximo del documento
            solo_aprobados: Solo documentos aprobados por SIFEN
            solo_fiscales: Solo documentos con validez fiscal
            page: Número de página (1-based)
            per_page: Elementos por página

        Returns:
            Dict[str, Any]: Diccionario con documentos y metadatos de paginación
        """
        try:
            # Query base
            base_query = select(Documento).where(
                and_(
                    Documento.empresa_id == empresa_id,
                    Documento.is_active == True
                )
            )

            # Aplicar filtros específicos
            if tipos_documento:
                base_query = base_query.where(
                    Documento.tipo_documento.in_(tipos_documento))

            if estados:
                base_query = base_query.where(Documento.estado.in_(estados))

            if fecha_desde:
                base_query = base_query.where(
                    Documento.fecha_emision >= fecha_desde)

            if fecha_hasta:
                base_query = base_query.where(
                    Documento.fecha_emision <= fecha_hasta)

            if cliente_id:
                base_query = base_query.where(
                    Documento.cliente_id == cliente_id)

            if moneda:
                base_query = base_query.where(
                    Documento.moneda == moneda.upper())

            if monto_minimo is not None:
                base_query = base_query.where(
                    Documento.total_general >= monto_minimo)

            if monto_maximo is not None:
                base_query = base_query.where(
                    Documento.total_general <= monto_maximo)

            if solo_aprobados:
                base_query = base_query.where(
                    Documento.estado.in_([
                        EstadoDocumentoSifenEnum.APROBADO.value,
                        EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value
                    ])
                )

            if solo_fiscales:
                base_query = base_query.where(
                    and_(
                        Documento.numero_protocolo.is_not(None),
                        Documento.codigo_respuesta_sifen.in_(["0260", "1005"])
                    )
                )

            # Contar total de registros
            count_query = select(func.count()).select_from(
                base_query.subquery())
            total_count = db.execute(count_query).scalar() or 0

            # Calcular paginación
            offset = (page - 1) * per_page
            total_pages = (total_count + per_page - 1) // per_page

            # Obtener datos paginados
            data_query = base_query.order_by(
                Documento.fecha_emision.desc(),
                Documento.created_at.desc()
            ).offset(offset).limit(per_page)

            documentos = list(db.execute(data_query).scalars().all())

            result = {
                "items": documentos,
                "pagination": {
                    "total": total_count,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "filters_applied": {
                    "tipos_documento": tipos_documento,
                    "estados": estados,
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                    "cliente_id": cliente_id,
                    "moneda": moneda,
                    "monto_minimo": float(monto_minimo) if monto_minimo else None,
                    "monto_maximo": float(monto_maximo) if monto_maximo else None,
                    "solo_aprobados": solo_aprobados,
                    "solo_fiscales": solo_fiscales
                }
            }

            logger.debug(
                f"✅ Filtrado avanzado: {len(documentos)} de {total_count} documentos "
                f"(página {page}/{total_pages})"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error en filtrado avanzado: {str(e)}")
            raise self._handle_repository_error(
                e, "filter_documentos_avanzado")

    # ===============================================
    # VALIDACIONES ESPECÍFICAS DE DOCUMENTOS
    # ===============================================

    def is_numero_disponible(
        self,
        db: Session,
        *,
        establecimiento: str,
        punto_expedicion: str,
        numero_documento: str,
        empresa_id: int,
        exclude_documento_id: Optional[int] = None
    ) -> bool:
        """
        Verifica si una numeración está disponible en la empresa.

        Args:
            db: Sesión de base de datos
            establecimiento: Código establecimiento
            punto_expedicion: Punto expedición
            numero_documento: Número documento
            empresa_id: ID de la empresa
            exclude_documento_id: ID de documento a excluir (para updates)

        Returns:
            bool: True si la numeración está disponible
        """
        try:
            query = select(func.count()).where(
                and_(
                    Documento.establecimiento == establecimiento.zfill(3),
                    Documento.punto_expedicion == punto_expedicion.zfill(3),
                    Documento.numero_documento == numero_documento.zfill(7),
                    Documento.empresa_id == empresa_id
                )
            )

            if exclude_documento_id:
                query = query.where(Documento.id != exclude_documento_id)

            count = db.execute(query).scalar() or 0
            is_available = count == 0

            numero_completo = f"{establecimiento}-{punto_expedicion}-{numero_documento}"
            logger.debug(
                f"Verificación numeración {numero_completo} empresa {empresa_id}: {is_available}")
            return is_available

        except Exception as e:
            logger.error(f"❌ Error verificando numeración: {str(e)}")
            raise self._handle_repository_error(e, "is_numero_disponible")

    def is_cdc_disponible(
        self,
        db: Session,
        *,
        cdc: str,
        exclude_documento_id: Optional[int] = None
    ) -> bool:
        """
        Verifica si un CDC está disponible a nivel nacional.

        Args:
            db: Sesión de base de datos
            cdc: CDC de 44 dígitos
            exclude_documento_id: ID de documento a excluir (para updates)

        Returns:
            bool: True si el CDC está disponible

        Note:
            CDC debe ser único a nivel nacional según SIFEN
        """
        try:
            cdc_normalizado = self._normalize_cdc(cdc)

            query = select(func.count()).where(
                Documento.cdc == cdc_normalizado
            )

            if exclude_documento_id:
                query = query.where(Documento.id != exclude_documento_id)

            count = db.execute(query).scalar() or 0
            is_available = count == 0

            logger.debug(f"Verificación CDC {cdc[:8]}...: {is_available}")
            return is_available

        except Exception as e:
            logger.error(f"❌ Error verificando CDC: {str(e)}")
            raise self._handle_repository_error(e, "is_cdc_disponible")

    def validate_estado_transition(
        self,
        estado_actual: str,
        estado_nuevo: str
    ) -> bool:
        """
        Valida si una transición de estado es permitida.

        Args:
            estado_actual: Estado actual del documento
            estado_nuevo: Estado al que se quiere cambiar

        Returns:
            bool: True si la transición es válida

        Raises:
            SifenBusinessError: Si la transición no es permitida
        """
        # Definir transiciones válidas
        transiciones_permitidas = {
            EstadoDocumentoSifenEnum.BORRADOR.value: [
                EstadoDocumentoSifenEnum.VALIDADO.value,
                EstadoDocumentoSifenEnum.CANCELADO.value
            ],
            EstadoDocumentoSifenEnum.VALIDADO.value: [
                EstadoDocumentoSifenEnum.GENERADO.value,
                EstadoDocumentoSifenEnum.BORRADOR.value,
                EstadoDocumentoSifenEnum.CANCELADO.value
            ],
            EstadoDocumentoSifenEnum.GENERADO.value: [
                EstadoDocumentoSifenEnum.FIRMADO.value,
                EstadoDocumentoSifenEnum.VALIDADO.value,
                EstadoDocumentoSifenEnum.CANCELADO.value
            ],
            EstadoDocumentoSifenEnum.FIRMADO.value: [
                EstadoDocumentoSifenEnum.ENVIADO.value,
                EstadoDocumentoSifenEnum.CANCELADO.value
            ],
            EstadoDocumentoSifenEnum.ENVIADO.value: [
                EstadoDocumentoSifenEnum.APROBADO.value,
                EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value,
                EstadoDocumentoSifenEnum.RECHAZADO.value,
                EstadoDocumentoSifenEnum.ERROR_ENVIO.value: [
                EstadoDocumentoSifenEnum.ENVIADO.value,
                EstadoDocumentoSifenEnum.CANCELADO.value
            ],
            EstadoDocumentoSifenEnum.APROBADO.value: [
                EstadoDocumentoSifenEnum.ANULADO.value
            ],
            EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value: [
                EstadoDocumentoSifenEnum.ANULADO.value
            ],
            EstadoDocumentoSifenEnum.RECHAZADO.value: [
                EstadoDocumentoSifenEnum.CANCELADO.value
            ]
            # Estados finales: CANCELADO, ANULADO no pueden cambiar
        }

        estados_permitidos = transiciones_permitidas.get(estado_actual, [])

        if estado_nuevo not in estados_permitidos:
            raise SifenBusinessError(
                f"Transición de estado no permitida: {estado_actual} → {estado_nuevo}. "
                f"Estados permitidos desde {estado_actual}: {estados_permitidos}",
                details={
                    "estado_actual": estado_actual,
                    "estado_nuevo": estado_nuevo,
                    "estados_permitidos": estados_permitidos
                }
            )

        logger.debug(
            f"✅ Transición de estado válida: {estado_actual} → {estado_nuevo}")
        return True

    # ===============================================
    # OPERACIONES ESPECIALIZADAS POR TIPO
    # ===============================================

    def create_factura_electronica(
        self,
        db: Session,
        *,
        obj_in: DocumentoCreateDTO,
        empresa_id: int
    ) -> FacturaElectronica:
        """
        Crea una nueva Factura Electrónica con validaciones específicas.

        Args:
            db: Sesión de base de datos
            obj_in: Datos de la factura a crear
            empresa_id: ID de la empresa (del usuario autenticado)

        Returns:
            FacturaElectronica: Factura creada

        Raises:
            SifenValidationError: Si las validaciones fallan
        """
        # Validar que el tipo sea correcto
        if obj_in.tipo_documento != TipoDocumentoSifenEnum.FACTURA.value:
            raise SifenValidationError(
                f"Tipo documento debe ser '{TipoDocumentoSifenEnum.FACTURA.value}' para facturas",
                field="tipo_documento",
                value=obj_in.tipo_documento
            )

        # Validar numeración disponible
        if not self.is_numero_disponible(
            db,
            establecimiento=obj_in.establecimiento,
            punto_expedicion=obj_in.punto_expedicion,
            numero_documento=obj_in.numero_documento,
            empresa_id=empresa_id
        ):
            numero_completo = f"{obj_in.establecimiento}-{obj_in.punto_expedicion}-{obj_in.numero_documento}"
            raise SifenDuplicateEntityError(
                entity_type="Factura",
                field="numero_completo",
                value=numero_completo,
                message=f"El número {numero_completo} ya existe para esta empresa"
            )

        # Preparar datos para crear
        obj_data = obj_in.model_dump()
        obj_data['empresa_id'] = empresa_id
        obj_data['estado'] = EstadoDocumentoSifenEnum.BORRADOR.value

        # Normalizar campos numéricos
        obj_data['establecimiento'] = obj_data['establecimiento'].zfill(3)
        obj_data['punto_expedicion'] = obj_data['punto_expedicion'].zfill(3)
        obj_data['numero_documento'] = obj_data['numero_documento'].zfill(7)

        # Crear instancia específica de FacturaElectronica
        try:
            factura = FacturaElectronica(**obj_data)
            db.add(factura)
            db.commit()
            db.refresh(factura)

            logger.info(
                f"✅ Factura Electrónica creada: ID={factura.id}, "
                f"número={factura.numero_completo}, empresa_id={empresa_id}"
            )
            return factura

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error creando factura electrónica: {str(e)}")
            raise self._handle_repository_error(
                e, "create_factura_electronica")

    def create_nota_credito(
        self,
        db: Session,
        *,
        obj_in: DocumentoCreateDTO,
        documento_original_cdc: str,
        motivo_credito: str,
        empresa_id: int
    ) -> NotaCreditoElectronica:
        """
        Crea una nueva Nota de Crédito Electrónica.

        Args:
            db: Sesión de base de datos
            obj_in: Datos de la nota de crédito
            documento_original_cdc: CDC del documento que se está creditando
            motivo_credito: Motivo específico de la nota de crédito
            empresa_id: ID de la empresa

        Returns:
            NotaCreditoElectronica: Nota de crédito creada
        """
        # Validar que el tipo sea correcto
        if obj_in.tipo_documento != TipoDocumentoSifenEnum.NOTA_CREDITO.value:
            raise SifenValidationError(
                f"Tipo documento debe ser '{TipoDocumentoSifenEnum.NOTA_CREDITO.value}' para notas de crédito",
                field="tipo_documento",
                value=obj_in.tipo_documento
            )

        # Validar que el documento original existe
        documento_original = self.get_by_cdc(db, cdc=documento_original_cdc, empresa_id=empresa_id)
        if not documento_original:
            raise SifenEntityNotFoundError(
                entity_type="Documento",
                entity_id=documento_original_cdc,
                message=f"Documento original con CDC {documento_original_cdc} no encontrado"
            )

        # Validar que el documento original esté aprobado
        if not safe_get(documento_original, 'esta_aprobado'):
            raise SifenBusinessError(
                "Solo se pueden crear notas de crédito para documentos aprobados por SIFEN",
                details={"documento_original_cdc": documento_original_cdc}
            )

        # Validar numeración disponible
        if not self.is_numero_disponible(
            db,
            establecimiento=obj_in.establecimiento,
            punto_expedicion=obj_in.punto_expedicion,
            numero_documento=obj_in.numero_documento,
            empresa_id=empresa_id
        ):
            numero_completo = f"{obj_in.establecimiento}-{obj_in.punto_expedicion}-{obj_in.numero_documento}"
            raise SifenDuplicateEntityError(
                entity_type="NotaCredito",
                field="numero_completo",
                value=numero_completo
            )

        # Preparar datos
        obj_data = obj_in.model_dump()
        obj_data.update({
            'empresa_id': empresa_id,
            'estado': EstadoDocumentoSifenEnum.BORRADOR.value,
            'documento_original_cdc': self._normalize_cdc(documento_original_cdc),
            'motivo_credito': motivo_credito,
            'establecimiento': obj_data['establecimiento'].zfill(3),
            'punto_expedicion': obj_data['punto_expedicion'].zfill(3),
            'numero_documento': obj_data['numero_documento'].zfill(7)
        })

        try:
            nota_credito = NotaCreditoElectronica(**obj_data)
            db.add(nota_credito)
            db.commit()
            db.refresh(nota_credito)

            logger.info(
                f"✅ Nota de Crédito creada: ID={nota_credito.id}, "
                f"número={nota_credito.numero_completo}, original_cdc={documento_original_cdc[:8]}..."
            )
            return nota_credito

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error creando nota de crédito: {str(e)}")
            raise self._handle_repository_error(e, "create_nota_credito")

    # ===============================================
    # GESTIÓN DE ESTADOS Y FLUJO SIFEN
    # ===============================================

    def actualizar_estado_documento(
        self,
        db: Session,
        *,
        documento_id: int,
        nuevo_estado: str,
        codigo_respuesta: Optional[str]=None,
        mensaje: Optional[str]=None,
        numero_protocolo: Optional[str]=None,
        observaciones_sifen: Optional[str]=None
    ) -> Documento:
        """
        Actualiza el estado de un documento con información SIFEN.

        Args:
            db: Sesión de base de datos
            documento_id: ID del documento
            nuevo_estado: Nuevo estado del documento
            codigo_respuesta: Código de respuesta SIFEN (opcional)
            mensaje: Mensaje descriptivo (opcional)
            numero_protocolo: Número de protocolo SIFEN (opcional)
            observaciones_sifen: Observaciones SIFEN (opcional)

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenBusinessError: Si la transición de estado no es válida
        """
        # Obtener documento
        documento = self.get_by_id_or_404(db, id=documento_id)
        estado_actual = safe_str(documento, 'estado', 'unknown')

        # Validar transición de estado
        self.validate_estado_transition(estado_actual, nuevo_estado)

        try:
            # Actualizar estado básico
            safe_set(documento, 'estado', nuevo_estado)

            # Actualizar información SIFEN si se proporciona
            if codigo_respuesta:
                safe_set(documento, 'codigo_respuesta_sifen', codigo_respuesta)

            if mensaje:
                safe_set(documento, 'mensaje_sifen', mensaje)

            if numero_protocolo:
                safe_set(documento, 'numero_protocolo', numero_protocolo)

            if observaciones_sifen:
                safe_set(documento, 'observaciones_sifen', observaciones_sifen)

            # Actualizar timestamps según el estado
            now = datetime.now()

            if nuevo_estado == EstadoDocumentoSifenEnum.GENERADO.value:
                safe_set(documento, 'fecha_generacion_xml', now)
            elif nuevo_estado == EstadoDocumentoSifenEnum.FIRMADO.value:
                safe_set(documento, 'fecha_firma_digital', now)
            elif nuevo_estado == EstadoDocumentoSifenEnum.ENVIADO.value:
                safe_set(documento, 'fecha_envio_sifen', now)
            elif nuevo_estado in [
                EstadoDocumentoSifenEnum.APROBADO.value,
                EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value,
                EstadoDocumentoSifenEnum.RECHAZADO.value
            ]:
                safe_set(documento, 'fecha_respuesta_sifen', now)

            # Guardar cambios
            db.add(documento)
            db.commit()
            db.refresh(documento)

            logger.info(
                f"✅ Estado actualizado: Documento ID={documento_id}, "
                f"{estado_actual} → {nuevo_estado}"
            )
            return documento

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error actualizando estado documento: {str(e)}")
            raise self._handle_repository_error(
                e, "actualizar_estado_documento")

    def marcar_como_enviado(
        self,
        db: Session,
        *,
        documento_id: int,
        request_id: Optional[str]=None
    ) -> Documento:
        """
        Marca un documento como enviado a SIFEN.

        Args:
            db: Sesión de base de datos
            documento_id: ID del documento
            request_id: ID interno del request (opcional)

        Returns:
            Documento: Documento actualizado
        """
        documento = self.get_by_id_or_404(db, id=documento_id)

        # Validar que esté en estado firmado
        estado_actual = safe_str(documento, 'estado')
        if estado_actual != EstadoDocumentoSifenEnum.FIRMADO.value:
            raise SifenBusinessError(
                f"Documento debe estar en estado '{EstadoDocumentoSifenEnum.FIRMADO.value}' para enviar",
                details={"estado_actual": estado_actual}
            )

        # Validar que tenga CDC y XML firmado
        if not safe_get(documento, 'cdc') or not safe_get(documento, 'xml_firmado'):
            raise SifenBusinessError(
                "Documento debe tener CDC y XML firmado para enviar",
                details={
                    "tiene_cdc": bool(safe_get(documento, 'cdc')),
                    "tiene_xml_firmado": bool(safe_get(documento, 'xml_firmado'))
                }
            )

        return self.actualizar_estado_documento(
            db,
            documento_id=documento_id,
            nuevo_estado=EstadoDocumentoSifenEnum.ENVIADO.value
        )

    def procesar_respuesta_sifen(
        self,
        db: Session,
        *,
        documento_id: int,
        codigo_respuesta: str,
        mensaje_respuesta: str,
        numero_protocolo: Optional[str]=None,
        url_consulta_publica: Optional[str]=None,
        observaciones: Optional[str]=None
    ) -> Documento:
        """
        Procesa la respuesta de SIFEN y actualiza el documento.

        Args:
            db: Sesión de base de datos
            documento_id: ID del documento
            codigo_respuesta: Código de respuesta SIFEN
            mensaje_respuesta: Mensaje de respuesta SIFEN
            numero_protocolo: Número de protocolo (si fue aprobado)
            url_consulta_publica: URL de consulta pública (opcional)
            observaciones: Observaciones SIFEN (opcional)

        Returns:
            Documento: Documento actualizado
        """
        # Determinar nuevo estado basado en código de respuesta
        if codigo_respuesta == "0260":
            nuevo_estado = EstadoDocumentoSifenEnum.APROBADO.value
        elif codigo_respuesta == "1005":
            nuevo_estado = EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value
        else:
            nuevo_estado = EstadoDocumentoSifenEnum.RECHAZADO.value

        try:
            documento = self.actualizar_estado_documento(
                db,
                documento_id=documento_id,
                nuevo_estado=nuevo_estado,
                codigo_respuesta=codigo_respuesta,
                mensaje=mensaje_respuesta,
                numero_protocolo=numero_protocolo,
                observaciones_sifen=observaciones
            )

            # Actualizar URL de consulta pública si se proporciona
            if url_consulta_publica:
                safe_set(documento, 'url_consulta_publica',
                         url_consulta_publica)
                db.add(documento)
                db.commit()
                db.refresh(documento)

            logger.info(
                f"✅ Respuesta SIFEN procesada: Documento ID={documento_id}, "
                f"código={codigo_respuesta}, estado={nuevo_estado}"
            )
            return documento

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error procesando respuesta SIFEN: {str(e)}")
            raise self._handle_repository_error(e, "procesar_respuesta_sifen")

    # ===============================================
    # ESTADÍSTICAS Y REPORTES
    # ===============================================

    def get_documento_stats(
        self,
        db: Session,
        *,
        empresa_id: int,
        fecha_desde: Optional[date]=None,
        fecha_hasta: Optional[date]=None
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas de documentos para una empresa.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período (opcional)
            fecha_hasta: Fecha fin del período (opcional)

        Returns:
            Dict[str, Any]: Estadísticas completas de documentos
        """
        try:
            base_filter = RepositoryFilter().eq("empresa_id", empresa_id).eq("is_active", True)

            # Aplicar filtros de fecha si se proporcionan
            additional_filters = []
            if fecha_desde:
                additional_filters.append(('fecha_emision', '>=', fecha_desde))
            if fecha_hasta:
                additional_filters.append(('fecha_emision', '<=', fecha_hasta))

            # Estadísticas generales
            total_documentos = self.count(db, filters=base_filter)

            # Estadísticas por tipo de documento
            tipos_stats = {}
            for tipo_enum in TipoDocumentoSifenEnum:
                tipo_filter = base_filter.eq("tipo_documento", tipo_enum.value)
                count = self.count(db, filters=tipo_filter)
                tipos_stats[tipo_enum.name.lower()] = count

            # Estadísticas por estado
            estados_stats = {}
            for estado_enum in EstadoDocumentoSifenEnum:
                estado_filter = base_filter.eq("estado", estado_enum.value)
                count = self.count(db, filters=estado_filter)
                estados_stats[estado_enum.value] = count

            # Calcular montos totales
            query_montos = select(
                func.sum(Documento.total_general).label('total_facturado'),
                func.sum(Documento.total_iva).label('total_iva'),
                func.avg(Documento.total_general).label('promedio_documento'),
                func.count().label('docs_con_monto')
            ).where(
                and_(
                    Documento.empresa_id == empresa_id,
                    Documento.is_active == True,
                    Documento.total_general > 0
                )
            )

            if fecha_desde:
                query_montos = query_montos.where(Documento.fecha_emision >= fecha_desde)
            if fecha_hasta:
                query_montos = query_montos.where(Documento.fecha_emision <= fecha_hasta)

            result_montos = db.execute(query_montos).first()

            # Documentos aprobados y rechazados
            aprobados = estados_stats.get(EstadoDocumentoSifenEnum.APROBADO.value, 0)
            aprobados_obs = estados_stats.get(EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value, 0)
            rechazados = estados_stats.get(EstadoDocumentoSifenEnum.RECHAZADO.value, 0)
            total_enviados = aprobados + aprobados_obs + rechazados

            # Calcular tasa de aprobación
            tasa_aprobacion = 0.0
            if total_enviados > 0:
                tasa_aprobacion = ((aprobados + aprobados_obs) / total_enviados) * 100

            stats = {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None
                },
                "totales": {
                    "total_documentos": total_documentos,
                    "total_facturado": float(result_montos.total_facturado or 0),
                    "total_iva": float(result_montos.total_iva or 0),
                    "promedio_documento": float(result_montos.promedio_documento or 0),
                    "docs_con_monto": int(result_montos.docs_con_monto or 0)
                },
                "por_tipo": tipos_stats,
                "por_estado": estados_stats,
                "sifen": {
                    "total_enviados": total_enviados,
                    "aprobados": aprobados,
                    "aprobados_con_observaciones": aprobados_obs,
                    "rechazados": rechazados,
                    "tasa_aprobacion": round(tasa_aprobacion, 2),
                    "documentos_fiscales": aprobados + aprobados_obs
                }
            }

            logger.debug(
                f"✅ Estadísticas documentos empresa {empresa_id}: {stats['totales']['total_documentos']} docs")
            return stats

        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {str(e)}")
            raise self._handle_repository_error(e, "get_documento_stats")

    def get_resumen_diario(
        self,
        db: Session,
        *,
        empresa_id: int,
        fecha: date
    ) -> Dict[str, Any]:
        """
        Obtiene resumen de documentos para un día específico.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            fecha: Fecha específica

        Returns:
            Dict[str, Any]: Resumen del día
        """
        try:
            query = select(
                Documento.tipo_documento,
                Documento.estado,
                func.count().label('cantidad'),
                func.sum(Documento.total_general).label('monto_total')
            ).where(
                and_(
                    Documento.empresa_id == empresa_id,
                    Documento.fecha_emision == fecha,
                    Documento.is_active == True
                )
            ).group_by(
                Documento.tipo_documento,
                Documento.estado
            )

            resultados = db.execute(query).all()

            resumen = {
                "fecha": fecha.isoformat(),
                "empresa_id": empresa_id,
                "por_tipo_estado": [],
                "totales": {
                    "documentos": 0,
                    "monto": Decimal("0.00")
                }
            }

            for row in resultados:
                item = {
                    "tipo_documento": row.tipo_documento,
                    "estado": row.estado,
                    "cantidad": row.cantidad,
                    "monto_total": float(row.monto_total or 0)
                }
                resumen["por_tipo_estado"].append(item)
                resumen["totales"]["documentos"] += row.cantidad
                resumen["totales"]["monto"] += Decimal(
                    str(row.monto_total or 0))

            resumen["totales"]["monto"] = float(resumen["totales"]["monto"])

            logger.debug(
                f"✅ Resumen diario {fecha}: {resumen['totales']['documentos']} documentos")
            return resumen

        except Exception as e:
            logger.error(f"❌ Error obteniendo resumen diario: {str(e)}")
            raise self._handle_repository_error(e, "get_resumen_diario")

    # ===============================================
    # MÉTODOS OVERRIDE DE BASE
    # ===============================================

    def create(
        self,
        db: Session,
        *,
        obj_in: Union[DocumentoCreateDTO, Dict[str, Any]],
        empresa_id: int
    ) -> Documento:
        """
        Crea un nuevo documento con validaciones específicas.

        Args:
            db: Sesión de base de datos
            obj_in: Datos del documento a crear
            empresa_id: ID de la empresa (del usuario autenticado)

        Returns:
            Documento: Documento creado

        Note:
            Se recomienda usar los métodos específicos por tipo:
            - create_factura_electronica()
            - create_nota_credito()
            etc.
        """
        # Convertir a DTO si es dict
        if isinstance(obj_in, dict):
            obj_in = DocumentoCreateDTO(**obj_in)

        # Determinar tipo específico y crear usando método apropiado
        if obj_in.tipo_documento == TipoDocumentoSifenEnum.FACTURA.value:
            return self.create_factura_electronica(db, obj_in=obj_in, empresa_id=empresa_id)
        else:
            # Para otros tipos, usar creación genérica por ahora
            return super().create(db, obj_in=obj_in)

    def update(
        self,
        db: Session,
        *,
        db_obj: Documento,
        obj_in: Union[DocumentoUpdateDTO, Dict[str, Any]]
    ) -> Documento:
        """
        Actualiza un documento con validaciones específicas.

        Args:
            db: Sesión de base de datos
            db_obj: Documento existente
            obj_in: Datos de actualización

        Returns:
            Documento: Documento actualizado

        Note:
            Solo se pueden modificar documentos en estados específicos
        """
        estado_actual = safe_str(db_obj, 'estado')

        # Validar que el documento pueda ser modificado
        estados_modificables = [
            EstadoDocumentoSifenEnum.BORRADOR.value,
            EstadoDocumentoSifenEnum.VALIDADO.value
        ]

        if estado_actual not in estados_modificables:
            raise SifenBusinessError(
                f"No se puede modificar documento en estado '{estado_actual}'",
                details={
                    "estado_actual": estado_actual,
                    "estados_modificables": estados_modificables
                }
            )

        # Validar CDC si se está actualizando
        if isinstance(obj_in, dict):
            cdc_nuevo = obj_in.get('cdc')
        else:
            cdc_nuevo = getattr(obj_in, 'cdc', None)

        if cdc_nuevo:
            cdc_actual = safe_str(db_obj, 'cdc')
            if cdc_nuevo != cdc_actual:
                if not self.is_cdc_disponible(db, cdc=cdc_nuevo, exclude_documento_id=db_obj.id):
                    raise SifenDuplicateEntityError(
                        entity_type="Documento",
                        field="cdc",
                        value=cdc_nuevo,
                        message=f"CDC {cdc_nuevo} ya existe"
                    )

        # Llamar al método base para actualizar
        documento = super().update(db, db_obj=db_obj, obj_in=obj_in)

        logger.info(f"✅ Documento actualizado: ID={documento.id}")
        return documento

    # ===============================================
    # MÉTODOS PRIVADOS Y UTILIDADES
    # ===============================================

    def _normalize_cdc(self, cdc: str) -> str:
        """
        Normaliza un CDC eliminando espacios y caracteres especiales.

        Args:
            cdc: CDC a normalizar

        Returns:
            str: CDC normalizado de 44 dígitos
        """
        if not cdc:
            return ""

        # Eliminar espacios, guiones y caracteres especiales
        normalized = "".join(c for c in cdc if c.isdigit())

        # Validar longitud
        if len(normalized) != 44:
            raise SifenValidationError(
                f"CDC debe tener exactamente 44 dígitos, recibido: {len(normalized)}",
                field="cdc",
                value=cdc
            )

        return normalized

    def _is_potential_cdc(self, text: str) -> bool:
        """
        Verifica si un texto podría ser un CDC.

        Args:
            text: Texto a verificar

        Returns:
            bool: True si parece un CDC
        """
        # CDC paraguayo tiene exactamente 44 dígitos
        digits_only = "".join(c for c in text if c.isdigit())
        return len(digits_only) >= 40  # Permitir búsquedas parciales

    def _handle_repository_error(self, exception: Exception, operation: str):
        """
        Maneja errores específicos del repository de documentos.

        Args:
            exception: Excepción original
            operation: Operación que falló

        Returns:
            Exception: Excepción SIFEN apropiada
        """
        from app.core.exceptions import handle_database_exception

        # Usar el handler genérico de la base
        return handle_database_exception(exception, f"documento_{operation}")

    # ===============================================
    # MÉTODOS DE CONSULTA ESPECIALIZADOS
    # ===============================================

    def get_documentos_vencidos_envio(
        self,
        db: Session,
        *,
        empresa_id: int,
        horas_limite: int=72
    ) -> List[Documento]:
        """
        Obtiene documentos que han vencido el plazo de envío (72 horas SIFEN).

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            horas_limite: Horas límite desde creación

        Returns:
            List[Documento]: Lista de documentos vencidos
        """
        try:
            from datetime import timedelta
            fecha_limite = datetime.now() - timedelta(hours=horas_limite)

            query = select(Documento).where(
                and_(
                    Documento.empresa_id == empresa_id,
                    Documento.estado.in_([
                        EstadoDocumentoSifenEnum.FIRMADO.value,
                        EstadoDocumentoSifenEnum.ERROR_ENVIO.value
                    ]),
                    Documento.created_at < fecha_limite,
                    Documento.is_active == True
                )
            ).order_by(Documento.created_at.asc())

            documentos = list(db.execute(query).scalars().all())

            logger.debug(
                f"✅ Documentos vencidos empresa {empresa_id}: {len(documentos)}")
            return documentos

        except Exception as e:
            logger.error(f"❌ Error obteniendo documentos vencidos: {str(e)}")
            raise self._handle_repository_error(
                e, "get_documentos_vencidos_envio")

    def get_documentos_para_reenvio(
        self,
        db: Session,
        *,
        empresa_id: int,
        max_intentos: int=3
    ) -> List[Documento]:
        """
        Obtiene documentos que pueden ser reenviados después de errores.

        Args:
            db: Sesión de base de datos
            empresa_id: ID de la empresa
            max_intentos
            ],
            EstadoDocumentoSifenEnum.ERROR_ENVIO.value
