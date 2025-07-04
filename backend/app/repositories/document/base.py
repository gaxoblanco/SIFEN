# ===============================================
# ARCHIVO: backend/app/repositories/documento/base.py
# PROPÓSITO: Repository base para documentos SIFEN - Core CRUD
# VERSIÓN: 1.0.0
# ===============================================

"""
Repository base para documentos SIFEN.
Hereda de BaseRepository y añade funcionalidad core de documentos.

Este módulo implementa las operaciones CRUD fundamentales para documentos
electrónicos SIFEN, incluyendo:
- Búsquedas por identificación (CDC, número completo, protocolo)
- Gestión por empresa y tipo de documento
- Filtrado temporal y por estado
- Validaciones específicas para create/update
- Manejo de errores específico para documentos

Clase principal:
- DocumentoRepositoryBase: Repository base con operaciones CRUD core
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import text

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenEntityNotFoundError,
    SifenDuplicateEntityError,
    SifenValidationError,
    SifenDatabaseError,
    handle_database_exception
)
from app.models.documento import (
    Documento,
    FacturaElectronica,
    AutofacturaElectronica,
    NotaCreditoElectronica,
    NotaDebitoElectronica,
    NotaRemisionElectronica,
    EstadoDocumentoSifenEnum,
    TipoDocumentoSifenEnum
)
from app.schemas.documento import (
    DocumentoCreateDTO,
    DocumentoUpdateDTO,
    DocumentoBaseDTO
)
from .utils import (
    normalize_cdc,
    normalize_numero_completo,
    is_potential_cdc,
    validate_cdc_format,
    log_repository_operation,
    log_performance_metric,
    handle_repository_error,
    get_default_page_size,
    get_max_page_size,
    build_date_filter,
    format_numero_completo
)

logger = get_logger(__name__)

# ===============================================
# CLASE BASE REPOSITORY
# ===============================================


class DocumentoRepositoryBase:
    """
    Repository base con operaciones CRUD fundamentales para documentos.

    Esta clase implementa operaciones CRUD básicas para documentos
    electrónicos SIFEN:
    - Búsquedas por identificadores únicos
    - Gestión por empresa y tipo
    - Filtrado temporal y por estado
    - Validaciones específicas
    - Manejo de errores especializado

    Attributes:
        db: Sesión de base de datos
        model: Modelo base Documento
        create_dto: DocumentoCreateDTO
        update_dto: DocumentoUpdateDTO
    """

    def __init__(self, db: Session):
        """
        Inicializa el repository base.

        Args:
            db: Sesión de base de datos SQLAlchemy
        """
        self.db = db
        self.model = Documento
        self.create_dto = DocumentoCreateDTO
        self.update_dto = DocumentoUpdateDTO

    # Método básico get_by_id que puede ser usado por otros métodos
    def get_by_id(self, entity_id: int) -> Optional[Documento]:
        """
        Obtiene documento por ID.

        Args:
            entity_id: ID del documento

        Returns:
            Optional[Documento]: Documento encontrado o None
        """
        try:
            return self.db.query(self.model).filter(self.model.id == entity_id).first()
        except Exception as e:
            handle_repository_error(e, "get_by_id", "Documento", entity_id)
            raise handle_database_exception(e, "get_by_id")

    # ===============================================
    # MÉTODOS DE BÚSQUEDA POR IDENTIFICACIÓN
    # ===============================================

    def get_by_cdc(self, cdc: str) -> Optional[Documento]:
        """
        Busca documento por CDC (Código de Control del Documento).

        Args:
            cdc: CDC de 44 dígitos

        Returns:
            Optional[Documento]: Documento encontrado o None

        Raises:
            SifenValidationError: Si el CDC no tiene formato válido
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> documento = repo.get_by_cdc("12345678901234567890123456789012345678901234")
        """
        start_time = datetime.now()

        try:
            # Validar formato CDC
            if not cdc:
                raise SifenValidationError("CDC es requerido", field="cdc")

            # Normalizar CDC
            cdc_normalized = normalize_cdc(cdc)

            # Validar formato
            if not validate_cdc_format(cdc_normalized):
                raise SifenValidationError(
                    "CDC debe tener exactamente 44 dígitos numéricos",
                    field="cdc",
                    value=cdc
                )

            # Consultar en base de datos
            documento = self.db.query(self.model).filter(
                text("cdc = :cdc")
            ).params(cdc=cdc_normalized).first()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_by_cdc", duration, 1 if documento else 0)

            if documento:
                log_repository_operation(
                    "get_by_cdc", "Documento", getattr(documento, 'id', None))

            return documento

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "get_by_cdc", "Documento")
            raise handle_database_exception(e, "get_by_cdc")

    def get_by_numero_completo(self, numero_completo: str, empresa_id: Optional[int] = None) -> Optional[Documento]:
        """
        Busca documento por número completo (EST-PEX-NUM).

        Args:
            numero_completo: Número en formato XXX-XXX-XXXXXXX
            empresa_id: ID de empresa (opcional, filtra por empresa)

        Returns:
            Optional[Documento]: Documento encontrado o None

        Raises:
            SifenValidationError: Si el número no tiene formato válido
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> documento = repo.get_by_numero_completo("001-001-0000123")
            >>> documento = repo.get_by_numero_completo("001-001-0000123", empresa_id=1)
        """
        start_time = datetime.now()

        try:
            # Validar entrada
            if not numero_completo:
                raise SifenValidationError(
                    "Número completo es requerido", field="numero_completo")

            # Normalizar número
            numero_normalized = normalize_numero_completo(numero_completo)

            # Parsear componentes
            parts = numero_normalized.split("-")
            if len(parts) != 3:
                raise SifenValidationError(
                    "Número completo debe tener formato XXX-XXX-XXXXXXX",
                    field="numero_completo",
                    value=numero_completo
                )

            establecimiento, punto_expedicion, numero_documento = parts

            # Construir query
            query = self.db.query(self.model).filter(
                and_(
                    self.model.establecimiento == establecimiento,
                    self.model.punto_expedicion == punto_expedicion,
                    self.model.numero_documento == numero_documento
                )
            )

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            documento = query.first()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_by_numero_completo", duration, 1 if documento else 0)

            if documento:
                log_repository_operation(
                    "get_by_cdc", "Documento", getattr(documento, 'id', None))
            return documento

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "get_by_numero_completo", "Documento")
            raise handle_database_exception(e, "get_by_numero_completo")

    def get_by_numero_protocolo(self, numero_protocolo: str) -> Optional[Documento]:
        """
        Busca documento por número de protocolo SIFEN.

        Args:
            numero_protocolo: Número de protocolo asignado por SIFEN

        Returns:
            Optional[Documento]: Documento encontrado o None

        Raises:
            SifenValidationError: Si el protocolo está vacío
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> documento = repo.get_by_numero_protocolo("PROT123456789")
        """
        start_time = datetime.now()

        try:
            # Validar entrada
            if not numero_protocolo:
                raise SifenValidationError(
                    "Número de protocolo es requerido", field="numero_protocolo")

            # Limpiar protocolo
            protocolo_clean = numero_protocolo.strip()

            # Consultar en base de datos
            documento = self.db.query(self.model).filter(
                text("numero_protocolo = :protocolo")
            ).params(protocolo=protocolo_clean).first()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_by_numero_protocolo", duration, 1 if documento else 0)

            if documento:
                log_repository_operation(
                    "get_by_numero_protocolo", "Documento", getattr(documento, 'id', None))

            return documento

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "get_by_numero_protocolo", "Documento")
            raise handle_database_exception(e, "get_by_numero_protocolo")

    # ===============================================
    # MÉTODOS DE GESTIÓN POR EMPRESA
    # ===============================================

    def get_by_empresa(self, empresa_id: int,
                       limit: Optional[int] = None,
                       offset: int = 0,
                       order_by: str = "id",
                       order_direction: str = "desc") -> List[Documento]:
        """
        Obtiene documentos por empresa.

        Args:
            empresa_id: ID de la empresa
            limit: Número máximo de resultados
            offset: Número de resultados a omitir
            order_by: Campo para ordenar
            order_direction: Dirección del ordenamiento (asc/desc)

        Returns:
            List[Documento]: Lista de documentos

        Raises:
            SifenValidationError: Si empresa_id no es válido
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> documentos = repo.get_by_empresa(1, limit=10)
            >>> documentos = repo.get_by_empresa(1, order_by="fecha_emision", order_direction="desc")
        """
        start_time = datetime.now()

        try:
            # Validar entrada
            if not empresa_id or empresa_id <= 0:
                raise SifenValidationError(
                    "ID de empresa debe ser mayor a 0", field="empresa_id")

            # Aplicar límite por defecto
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            # Construir query
            query = self.db.query(self.model).filter(
                self.model.empresa_id == empresa_id
            )

            # Aplicar ordenamiento
            if hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_direction.lower() == "asc":
                    query = query.order_by(asc(order_field))
                else:
                    query = query.order_by(desc(order_field))

            # Aplicar paginación
            if offset > 0:
                query = query.offset(offset)

            documentos = query.limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("get_by_empresa", duration, len(documentos))

            log_repository_operation("get_by_empresa", "Documento", empresa_id, {
                "count": len(documentos),
                "limit": limit,
                "offset": offset
            })

            return documentos

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_by_empresa", "Documento", empresa_id)
            raise handle_database_exception(e, "get_by_empresa")

    def get_by_tipo_documento(self, tipo_documento: str,
                              empresa_id: Optional[int] = None,
                              limit: Optional[int] = None,
                              offset: int = 0) -> List[Documento]:
        """
        Obtiene documentos por tipo de documento.

        Args:
            tipo_documento: Tipo de documento SIFEN (1,4,5,6,7)
            empresa_id: ID de empresa (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[Documento]: Lista de documentos

        Raises:
            SifenValidationError: Si tipo_documento no es válido
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> facturas = repo.get_by_tipo_documento("1")  # Facturas
            >>> notas_credito = repo.get_by_tipo_documento("5", empresa_id=1)
        """
        start_time = datetime.now()

        try:
            # Validar tipo de documento
            if tipo_documento not in ["1", "4", "5", "6", "7"]:
                raise SifenValidationError(
                    "Tipo de documento debe ser 1, 4, 5, 6 o 7",
                    field="tipo_documento",
                    value=tipo_documento
                )

            # Aplicar límite por defecto
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            # Construir query
            query = self.db.query(self.model).filter(
                self.model.tipo_documento == tipo_documento
            )

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Aplicar paginación y ordenamiento
            documentos = query.order_by(desc(self.model.id)).offset(
                offset).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_by_tipo_documento", duration, len(documentos))

            log_repository_operation("get_by_tipo_documento", "Documento", None, {
                "tipo_documento": tipo_documento,
                "empresa_id": empresa_id,
                "count": len(documentos)
            })

            return documentos

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "get_by_tipo_documento", "Documento")
            raise handle_database_exception(e, "get_by_tipo_documento")

    def get_by_estado(self, estado: str,
                      empresa_id: Optional[int] = None,
                      limit: Optional[int] = None,
                      offset: int = 0) -> List[Documento]:
        """
        Obtiene documentos por estado actual.

        Args:
            estado: Estado del documento
            empresa_id: ID de empresa (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[Documento]: Lista de documentos

        Raises:
            SifenValidationError: Si estado no es válido
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> borradores = repo.get_by_estado("borrador")
            >>> aprobados = repo.get_by_estado("aprobado", empresa_id=1)
        """
        start_time = datetime.now()

        try:
            # Validar estado
            if not estado:
                raise SifenValidationError(
                    "Estado es requerido", field="estado")

            # Verificar que el estado existe en el enum
            valid_states = [e.value for e in EstadoDocumentoSifenEnum]
            if estado not in valid_states:
                raise SifenValidationError(
                    f"Estado debe ser uno de: {', '.join(valid_states)}",
                    field="estado",
                    value=estado
                )

            # Aplicar límite por defecto
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            # Construir query
            query = self.db.query(self.model).filter(
                text("estado = :estado")
            ).params(estado=estado)

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Aplicar paginación y ordenamiento
            documentos = query.order_by(desc(self.model.updated_at)).offset(
                offset).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("get_by_estado", duration, len(documentos))

            log_repository_operation("get_by_estado", "Documento", None, {
                "estado": estado,
                "empresa_id": empresa_id,
                "count": len(documentos)
            })

            return documentos

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "get_by_estado", "Documento")
            raise handle_database_exception(e, "get_by_estado")

    # ===============================================
    # MÉTODOS DE FILTRADO TEMPORAL
    # ===============================================

    def get_by_fecha_emision(self, fecha_desde: Optional[date] = None,
                             fecha_hasta: Optional[date] = None,
                             empresa_id: Optional[int] = None,
                             limit: Optional[int] = None,
                             offset: int = 0) -> List[Documento]:
        """
        Obtiene documentos por rango de fechas de emisión.

        Args:
            fecha_desde: Fecha inicio (inclusive)
            fecha_hasta: Fecha fin (inclusive)
            empresa_id: ID de empresa (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[Documento]: Lista de documentos

        Raises:
            SifenValidationError: Si el rango de fechas no es válido
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> documentos = repo.get_by_fecha_emision(
            ...     fecha_desde=date(2025, 1, 1),
            ...     fecha_hasta=date(2025, 1, 31)
            ... )
        """
        start_time = datetime.now()

        try:
            # Validar rango de fechas
            if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
                raise SifenValidationError(
                    "Fecha desde no puede ser mayor a fecha hasta",
                    field="fecha_desde"
                )

            # Aplicar límite por defecto
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            # Construir query base
            query = self.db.query(self.model)

            # Aplicar filtro de fechas
            query = build_date_filter(
                query, self.model.fecha_emision, fecha_desde, fecha_hasta)

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Aplicar paginación y ordenamiento
            documentos = query.order_by(desc(self.model.fecha_emision)).offset(
                offset).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_by_fecha_emision", duration, len(documentos))

            log_repository_operation("get_by_fecha_emision", "Documento", None, {
                "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                "empresa_id": empresa_id,
                "count": len(documentos)
            })

            return documentos

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "get_by_fecha_emision", "Documento")
            raise handle_database_exception(e, "get_by_fecha_emision")

    def get_pendientes_envio(self, empresa_id: Optional[int] = None,
                             tiempo_limite_horas: int = 72) -> List[Documento]:
        """
        Obtiene documentos pendientes de envío a SIFEN (dentro del límite de 72 horas).

        Args:
            empresa_id: ID de empresa (opcional)
            tiempo_limite_horas: Tiempo límite en horas (default: 72)

        Returns:
            List[Documento]: Lista de documentos pendientes

        Raises:
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> pendientes = repo.get_pendientes_envio()
            >>> pendientes = repo.get_pendientes_envio(empresa_id=1, tiempo_limite_horas=48)
        """
        start_time = datetime.now()

        try:
            # Calcular fecha límite
            fecha_limite = datetime.now() - timedelta(hours=tiempo_limite_horas)

            # Construir query
            query = self.db.query(self.model).filter(
                text(
                    "estado = :estado AND fecha_firma_digital >= :fecha_limite AND fecha_envio_sifen IS NULL")
            ).params(estado=EstadoDocumentoSifenEnum.FIRMADO.value, fecha_limite=fecha_limite)

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            documentos = query.order_by("fecha_firma_digital").all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_pendientes_envio", duration, len(documentos))

            log_repository_operation("get_pendientes_envio", "Documento", None, {
                "empresa_id": empresa_id,
                "tiempo_limite_horas": tiempo_limite_horas,
                "count": len(documentos)
            })

            return documentos

        except Exception as e:
            handle_repository_error(e, "get_pendientes_envio", "Documento")
            raise handle_database_exception(e, "get_pendientes_envio")

    # ===============================================
    # OVERRIDE DE MÉTODOS BASE - CREATE/UPDATE
    # ===============================================

    def create(self, obj_data: Union[DocumentoCreateDTO, Dict[str, Any]],
               auto_generate_fields: bool = True) -> Documento:
        """
        Crea un nuevo documento con validaciones específicas.

        Args:
            obj_data: Datos del documento a crear
            auto_generate_fields: Si debe auto-generar campos como CDC

        Returns:
            Documento: Documento creado

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenDuplicateEntityError: Si hay duplicados
            SifenDatabaseError: Si hay error en la base de datos

        Example:
            >>> documento_data = DocumentoCreateDTO(
            ...     tipo_documento="1",
            ...     establecimiento="001",
            ...     numero_documento="0000123",
            ...     ...
            ... )
            >>> documento = repo.create(documento_data)
        """
        start_time = datetime.now()

        try:
            # Convertir DTO a dict si es necesario
            if isinstance(obj_data, DocumentoCreateDTO):
                data_dict = obj_data.dict()
            else:
                data_dict = obj_data.copy()

            # Validaciones pre-creación
            self._validate_create_data(data_dict)

            # Verificar unicidad de numeración
            self._check_numero_uniqueness(data_dict)

            # Formatear campos
            if auto_generate_fields:
                self._format_document_fields(data_dict)

            # Crear instancia del modelo
            documento = self.model(**data_dict)

            # Generar CDC si es necesario
            if auto_generate_fields and not getattr(documento, 'cdc', None):
                documento.generar_cdc()

            # Guardar en base de datos
            self.db.add(documento)
            self.db.commit()
            self.db.refresh(documento)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("create", duration, 1)

            log_repository_operation("create", "Documento", getattr(documento, 'id', None), {
                "tipo_documento": getattr(documento, 'tipo_documento', None),
                "numero_completo": getattr(documento, 'numero_completo', None),
                "empresa_id": getattr(documento, 'empresa_id', None)
            })

            return documento

        except (SifenValidationError, SifenDuplicateEntityError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(e, "create", "Documento")
            raise handle_database_exception(e, "create")

    def update(self, entity_id: int, obj_data: Union[DocumentoUpdateDTO, Dict[str, Any]]) -> Documento:
        """
        Actualiza un documento existente con validaciones específicas.

        Args:
            entity_id: ID del documento a actualizar
            obj_data: Datos a actualizar

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenValidationError: Si los datos no son válidos
            SifenDatabaseError: Si hay error en la base de datos

        Example:
            >>> update_data = DocumentoUpdateDTO(
            ...     observaciones="Observaciones actualizadas"
            ... )
            >>> documento = repo.update(123, update_data)
        """
        start_time = datetime.now()

        try:
            # Obtener documento existente
            documento = self.get_by_id(entity_id)
            if not documento:
                raise SifenEntityNotFoundError("Documento", entity_id)

            # Convertir DTO a dict si es necesario
            if isinstance(obj_data, DocumentoUpdateDTO):
                data_dict = obj_data.dict(exclude_unset=True)
            else:
                data_dict = {k: v for k, v in obj_data.items()
                             if v is not None}

            # Validaciones pre-actualización
            self._validate_update_data(documento, data_dict)

            # Aplicar cambios
            for key, value in data_dict.items():
                if hasattr(documento, key):
                    setattr(documento, key, value)

            # Actualizar timestamp
            setattr(documento, 'updated_at', datetime.now())

            # Guardar cambios
            self.db.commit()
            self.db.refresh(documento)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("update", duration, 1)

            log_repository_operation("update", "Documento", getattr(documento, 'id', None), {
                "fields_updated": list(data_dict.keys()),
                "estado": getattr(documento, 'estado', None)
            })

            return documento

        except (SifenEntityNotFoundError, SifenValidationError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(e, "update", "Documento", entity_id)
            raise handle_database_exception(e, "update")

    # ===============================================
    # UTILIDADES BÁSICAS
    # ===============================================

    def _normalize_cdc(self, cdc: str) -> str:
        """
        Normaliza un CDC removiendo espacios y caracteres especiales.

        Args:
            cdc: CDC a normalizar

        Returns:
            str: CDC normalizado
        """
        return normalize_cdc(cdc)

    def _is_potential_cdc(self, value: str) -> bool:
        """
        Verifica si un string podría ser un CDC.

        Args:
            value: Valor a verificar

        Returns:
            bool: True si podría ser un CDC
        """
        return is_potential_cdc(value)

    def _handle_repository_error(self, error: Exception, operation: str, entity_id: Optional[int] = None) -> None:
        """
        Maneja errores específicos del repository.

        Args:
            error: Excepción capturada
            operation: Operación que falló
            entity_id: ID de la entidad (opcional)
        """
        handle_repository_error(error, operation, "Documento", entity_id)

    # ===============================================
    # VALIDACIONES PRIVADAS
    # ===============================================

    def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """
        Valida datos antes de crear documento.

        Args:
            data: Datos a validar

        Raises:
            SifenValidationError: Si los datos no son válidos
        """
        # Validar campos requeridos
        required_fields = [
            "tipo_documento", "establecimiento", "punto_expedicion",
            "numero_documento", "numero_timbrado", "fecha_emision",
            "empresa_id", "cliente_id", "total_general"
        ]

        for field in required_fields:
            if field not in data or data[field] is None:
                raise SifenValidationError(
                    f"Campo requerido: {field}",
                    field=field
                )

        # Validar tipo de documento
        if data["tipo_documento"] not in ["1", "4", "5", "6", "7"]:
            raise SifenValidationError(
                "Tipo de documento debe ser 1, 4, 5, 6 o 7",
                field="tipo_documento",
                value=data["tipo_documento"]
            )

        # Validar fecha de emisión
        if isinstance(data["fecha_emision"], str):
            try:
                fecha = datetime.strptime(
                    data["fecha_emision"], "%Y-%m-%d").date()
                data["fecha_emision"] = fecha
            except ValueError:
                raise SifenValidationError(
                    "Formato de fecha inválido. Use YYYY-MM-DD",
                    field="fecha_emision",
                    value=data["fecha_emision"]
                )

        # Validar que la fecha no sea futura
        if data["fecha_emision"] > date.today():
            raise SifenValidationError(
                "La fecha de emisión no puede ser futura",
                field="fecha_emision",
                value=data["fecha_emision"]
            )

        # Validar monto total
        if isinstance(data["total_general"], str):
            try:
                data["total_general"] = Decimal(data["total_general"])
            except (ValueError, TypeError):
                raise SifenValidationError(
                    "Total general debe ser un número válido",
                    field="total_general",
                    value=data["total_general"]
                )

        if data["total_general"] < 0:
            raise SifenValidationError(
                "Total general no puede ser negativo",
                field="total_general",
                value=data["total_general"]
            )

    def _validate_update_data(self, documento: Documento, data: Dict[str, Any]) -> None:
        """
        Valida datos antes de actualizar documento.

        Args:
            documento: Documento existente
            data: Datos a actualizar

        Raises:
            SifenValidationError: Si los datos no son válidos
        """
        # Verificar si el documento puede ser modificado
        from .utils import is_editable_state

        if not is_editable_state(getattr(documento, 'estado', '')):
            raise SifenValidationError(
                f"Documento en estado '{getattr(documento, 'estado', '')}' no puede ser modificado",
                field="estado",
                value=getattr(documento, 'estado', '')
            )

        # Validar que no se modifiquen campos críticos
        protected_fields = ["id", "cdc",
                            "tipo_documento", "empresa_id", "created_at"]

        for field in protected_fields:
            if field in data:
                raise SifenValidationError(
                    f"Campo '{field}' no puede ser modificado",
                    field=field
                )

        # Validar fecha de emisión si se actualiza
        if "fecha_emision" in data:
            if isinstance(data["fecha_emision"], str):
                try:
                    fecha = datetime.strptime(
                        data["fecha_emision"], "%Y-%m-%d").date()
                    data["fecha_emision"] = fecha
                except ValueError:
                    raise SifenValidationError(
                        "Formato de fecha inválido. Use YYYY-MM-DD",
                        field="fecha_emision",
                        value=data["fecha_emision"]
                    )

            if data["fecha_emision"] > date.today():
                raise SifenValidationError(
                    "La fecha de emisión no puede ser futura",
                    field="fecha_emision",
                    value=data["fecha_emision"]
                )

    def _check_numero_uniqueness(self, data: Dict[str, Any]) -> None:
        """
        Verifica unicidad del número de documento.

        Args:
            data: Datos del documento

        Raises:
            SifenDuplicateEntityError: Si el número ya existe
        """
        # Construir número completo
        numero_completo = format_numero_completo(
            data["establecimiento"],
            data["punto_expedicion"],
            data["numero_documento"]
        )

        # Verificar si ya existe
        existing = self.get_by_numero_completo(
            numero_completo, data["empresa_id"])

        if existing:
            raise SifenDuplicateEntityError(
                "Documento",
                "numero_completo",
                numero_completo
            )

    def _format_document_fields(self, data: Dict[str, Any]) -> None:
        """
        Formatea campos del documento antes de crear.

        Args:
            data: Datos del documento a formatear
        """
        # Formatear códigos con ceros a la izquierda
        if "establecimiento" in data:
            data["establecimiento"] = str(data["establecimiento"]).zfill(3)

        if "punto_expedicion" in data:
            data["punto_expedicion"] = str(data["punto_expedicion"]).zfill(3)

        if "numero_documento" in data:
            data["numero_documento"] = str(data["numero_documento"]).zfill(7)

        # Formatear montos como Decimal
        amount_fields = [
            "total_general", "total_operacion", "total_iva",
            "subtotal_exento", "subtotal_exonerado",
            "subtotal_gravado_5", "subtotal_gravado_10"
        ]

        for field in amount_fields:
            if field in data and data[field] is not None:
                if isinstance(data[field], str):
                    data[field] = Decimal(data[field])
                elif isinstance(data[field], (int, float)):
                    data[field] = Decimal(str(data[field]))

    # ===============================================
    # MÉTODOS DE CONTEO
    # ===============================================

    def count_by_empresa(self, empresa_id: int) -> int:
        """
        Cuenta documentos por empresa.

        Args:
            empresa_id: ID de la empresa

        Returns:
            int: Número de documentos
        """
        try:
            count = self.db.query(func.count(self.model.id)).filter(
                self.model.empresa_id == empresa_id
            ).scalar()

            return count or 0

        except Exception as e:
            handle_repository_error(
                e, "count_by_empresa", "Documento", empresa_id)
            raise handle_database_exception(e, "count_by_empresa")

    def count_by_estado(self, estado: str, empresa_id: Optional[int] = None) -> int:
        """
        Cuenta documentos por estado.

        Args:
            estado: Estado del documento
            empresa_id: ID de empresa (opcional)

        Returns:
            int: Número de documentos
        """
        try:
            query = self.db.query(func.count(self.model.id)).filter(
                text("estado = :estado")
            ).params(estado=estado)

            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            count = query.scalar()

            return count or 0

        except Exception as e:
            handle_repository_error(e, "count_by_estado", "Documento")
            raise handle_database_exception(e, "count_by_estado")

    def count_by_fecha_emision(self, fecha_desde: date, fecha_hasta: date,
                               empresa_id: Optional[int] = None) -> int:
        """
        Cuenta documentos por rango de fechas.

        Args:
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            empresa_id: ID de empresa (opcional)

        Returns:
            int: Número de documentos
        """
        try:
            query = self.db.query(func.count(self.model.id))

            # Aplicar filtro de fechas
            query = build_date_filter(
                query, self.model.fecha_emision, fecha_desde, fecha_hasta)

            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            count = query.scalar()

            return count or 0

        except Exception as e:
            handle_repository_error(e, "count_by_fecha_emision", "Documento")
            raise handle_database_exception(e, "count_by_fecha_emision")
