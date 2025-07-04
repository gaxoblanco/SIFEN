# ===============================================
# ARCHIVO: backend/app/repositories/documento/sifen_state_mixin.py
# PROPÓSITO: Mixin para gestión del flujo de estados de documentos en SIFEN
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para gestión del flujo de estados de documentos en SIFEN.
Maneja transiciones, timestamps y respuestas SIFEN.

Este mixin implementa la gestión completa del flujo de estados para documentos
electrónicos SIFEN:
- Transiciones de estado con validaciones
- Procesamiento de respuestas SIFEN
- Gestión de timestamps del workflow
- Consultas por estado y estadísticas
- Detección de documentos atascados

Flujo completo:
borrador → validado → generado → firmado → enviado → aprobado/rechazado
     ↓         ↓         ↓         ↓
  cancelado  cancelado  cancelado  cancelado

Clase principal:
- SifenStateMixin: Mixin con gestión completa de estados
"""

from typing import Optional, List, Dict, Any, Callable, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, text, desc, asc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenValidationError,
    SifenEntityNotFoundError,
    SifenDocumentStateError,
    SifenBusinessLogicError,
    SifenDatabaseError,
    handle_database_exception
)
from app.models.documento import (
    Documento,
    EstadoDocumentoSifenEnum,
    TipoDocumentoSifenEnum
)
from app.schemas.documento import (
    DocumentoEstadoDTO,
    DocumentoSifenDTO
)
from .utils import (
    VALID_STATE_TRANSITIONS,
    EDITABLE_STATES,
    FINAL_STATES,
    SIFEN_SUCCESS_CODES,
    can_transition_to,
    is_editable_state,
    is_final_state,
    get_next_valid_states,
    get_state_description,
    log_repository_operation,
    log_performance_metric,
    handle_repository_error
)

logger = get_logger(__name__)

# ===============================================
# CONSTANTES ESPECÍFICAS DE ESTADOS
# ===============================================

# Códigos de respuesta SIFEN por estado
SIFEN_RESPONSE_CODES = {
    # Códigos de éxito
    "0260": EstadoDocumentoSifenEnum.APROBADO.value,
    "1005": EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value,

    # Códigos de error más comunes
    "1000": EstadoDocumentoSifenEnum.RECHAZADO.value,
    "1001": EstadoDocumentoSifenEnum.RECHAZADO.value,
    "1101": EstadoDocumentoSifenEnum.RECHAZADO.value,
    "1250": EstadoDocumentoSifenEnum.RECHAZADO.value,
    "1251": EstadoDocumentoSifenEnum.RECHAZADO.value,
    "0141": EstadoDocumentoSifenEnum.RECHAZADO.value,
    "0142": EstadoDocumentoSifenEnum.RECHAZADO.value,
    "5000": EstadoDocumentoSifenEnum.ERROR_ENVIO.value,
}

# Tiempo máximo para detectar documentos atascados (en horas)
MAX_TIME_IN_STATE = {
    EstadoDocumentoSifenEnum.BORRADOR.value: 24,        # 1 día
    EstadoDocumentoSifenEnum.VALIDADO.value: 2,         # 2 horas
    EstadoDocumentoSifenEnum.GENERADO.value: 1,         # 1 hora
    EstadoDocumentoSifenEnum.FIRMADO.value: 72,         # 3 días (límite SIFEN)
    EstadoDocumentoSifenEnum.ENVIADO.value: 1,          # 1 hora para respuesta
    EstadoDocumentoSifenEnum.ERROR_ENVIO.value: 24,     # 1 día para reintento
}

# Estados que requieren información SIFEN
STATES_REQUIRING_SIFEN_DATA = [
    EstadoDocumentoSifenEnum.APROBADO.value,
    EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value,
    EstadoDocumentoSifenEnum.RECHAZADO.value,
]

# ===============================================
# CLASE SIFEN STATE MIXIN
# ===============================================


class SifenStateMixin:
    """
    Mixin para gestión del flujo de estados y procesamiento SIFEN.

    Proporciona métodos para:
    - Cambios de estado con validaciones
    - Procesamiento de respuestas SIFEN
    - Gestión de timestamps del workflow
    - Consultas por estado y estadísticas
    - Detección de problemas en el flujo

    Requiere que la clase que lo use tenga:
    - self.db: Session SQLAlchemy
    - self.model: Modelo Documento
    - self.validate_estado_transition: Método de validación
    """

    # Type hints para PyLance
    db: Session
    model: type[Documento]
    validate_estado_transition: Callable[[str, str, Optional[int]], None]

    # ===============================================
    # GESTIÓN DE ESTADOS
    # ===============================================

    def actualizar_estado_documento(self,
                                    documento_id: int,
                                    nuevo_estado: str,
                                    datos_adicionales: Optional[Dict[str, Any]] = None,
                                    validar_transicion: bool = True) -> Documento:
        """
        Actualiza el estado de un documento con validaciones completas.

        Args:
            documento_id: ID del documento
            nuevo_estado: Nuevo estado del documento
            datos_adicionales: Datos adicionales (código SIFEN, mensaje, etc.)
            validar_transicion: Si validar la transición de estado

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenDocumentStateError: Si la transición no es válida
            SifenDatabaseError: Si hay error en la base de datos

        Example:
            >>> documento = mixin.actualizar_estado_documento(
            ...     123,
            ...     "aprobado",
            ...     {
            ...         "codigo_respuesta_sifen": "0260",
            ...         "mensaje_sifen": "Aprobado",
            ...         "numero_protocolo": "PROT123456"
            ...     }
            ... )
        """
        start_time = datetime.now()

        try:
            # Obtener documento existente
            documento = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento:
                raise SifenEntityNotFoundError("Documento", documento_id)

            estado_actual = getattr(documento, 'estado', '')

            # Validar transición si se solicita
            if validar_transicion:
                self.validate_estado_transition(
                    estado_actual, nuevo_estado, documento_id)

            # Actualizar estado
            setattr(documento, 'estado', nuevo_estado)

            # Procesar datos adicionales
            if datos_adicionales:
                self._aplicar_datos_adicionales(documento, datos_adicionales)

            # Actualizar timestamps según el estado
            self._actualizar_timestamps_por_estado(documento, nuevo_estado)

            # Actualizar timestamp de modificación
            setattr(documento, 'updated_at', datetime.now())

            # Guardar cambios
            self.db.commit()
            self.db.refresh(documento)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("actualizar_estado_documento", duration, 1)

            log_repository_operation(
                "actualizar_estado_documento",
                "Documento",
                documento_id,
                {
                    "estado_anterior": estado_actual,
                    "estado_nuevo": nuevo_estado,
                    "datos_adicionales": bool(datos_adicionales),
                    "validar_transicion": validar_transicion
                }
            )

            return documento

        except (SifenEntityNotFoundError, SifenDocumentStateError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(
                e, "actualizar_estado_documento", "Documento", documento_id)
            raise handle_database_exception(e, "actualizar_estado_documento")

    def marcar_como_generado(self,
                             documento_id: int,
                             xml_generado: str,
                             hash_documento: Optional[str] = None) -> Documento:
        """
        Marca un documento como generado (XML creado).

        Args:
            documento_id: ID del documento
            xml_generado: Contenido XML generado
            hash_documento: Hash del documento (opcional)

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenDocumentStateError: Si no puede ser generado

        Example:
            >>> documento = mixin.marcar_como_generado(
            ...     123,
            ...     "<?xml version='1.0'?>...",
            ...     "abc123def456"
            ... )
        """
        start_time = datetime.now()

        try:
            datos_adicionales = {
                "xml_generado": xml_generado,
                "fecha_generacion_xml": datetime.now()
            }

            if hash_documento:
                datos_adicionales["hash_documento"] = hash_documento

            documento = self.actualizar_estado_documento(
                documento_id,
                EstadoDocumentoSifenEnum.GENERADO.value,
                datos_adicionales
            )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("marcar_como_generado", duration, 1)

            log_repository_operation(
                "marcar_como_generado",
                "Documento",
                documento_id,
                {
                    "xml_size": len(xml_generado),
                    "has_hash": bool(hash_documento)
                }
            )

            return documento

        except Exception as e:
            handle_repository_error(
                e, "marcar_como_generado", "Documento", documento_id)
            raise

    def marcar_como_firmado(self,
                            documento_id: int,
                            xml_firmado: str,
                            certificado_serial: Optional[str] = None) -> Documento:
        """
        Marca un documento como firmado digitalmente.

        Args:
            documento_id: ID del documento
            xml_firmado: XML con firma digital
            certificado_serial: Serial del certificado usado

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenDocumentStateError: Si no puede ser firmado

        Example:
            >>> documento = mixin.marcar_como_firmado(
            ...     123,
            ...     "<?xml version='1.0'?>...firma...",
            ...     "CERT123456789"
            ... )
        """
        start_time = datetime.now()

        try:
            datos_adicionales = {
                "xml_firmado": xml_firmado,
                "fecha_firma_digital": datetime.now()
            }

            if certificado_serial:
                datos_adicionales["certificado_serial"] = certificado_serial

            documento = self.actualizar_estado_documento(
                documento_id,
                EstadoDocumentoSifenEnum.FIRMADO.value,
                datos_adicionales
            )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("marcar_como_firmado", duration, 1)

            log_repository_operation(
                "marcar_como_firmado",
                "Documento",
                documento_id,
                {
                    "xml_firmado_size": len(xml_firmado),
                    "has_certificado": bool(certificado_serial)
                }
            )

            return documento

        except Exception as e:
            handle_repository_error(
                e, "marcar_como_firmado", "Documento", documento_id)
            raise

    def marcar_como_enviado(self,
                            documento_id: int,
                            request_id: Optional[str] = None) -> Documento:
        """
        Marca un documento como enviado a SIFEN.

        Args:
            documento_id: ID del documento
            request_id: ID interno del request

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenDocumentStateError: Si no puede ser enviado

        Example:
            >>> documento = mixin.marcar_como_enviado(123, "REQ-123456")
        """
        start_time = datetime.now()

        try:
            datos_adicionales: Dict[str, Any] = {
                "fecha_envio_sifen": datetime.now()
            }

            if request_id:
                datos_adicionales["request_id"] = request_id

            documento = self.actualizar_estado_documento(
                documento_id,
                EstadoDocumentoSifenEnum.ENVIADO.value,
                datos_adicionales
            )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("marcar_como_enviado", duration, 1)

            log_repository_operation(
                "marcar_como_enviado",
                "Documento",
                documento_id,
                {
                    "request_id": request_id,
                    "enviado_at": datetime.now().isoformat()
                }
            )

            return documento

        except Exception as e:
            handle_repository_error(
                e, "marcar_como_enviado", "Documento", documento_id)
            raise

    def marcar_como_cancelado(self,
                              documento_id: int,
                              motivo: str,
                              usuario_id: Optional[int] = None) -> Documento:
        """
        Marca un documento como cancelado por el usuario.

        Args:
            documento_id: ID del documento
            motivo: Motivo de la cancelación
            usuario_id: ID del usuario que cancela

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenDocumentStateError: Si no puede ser cancelado

        Example:
            >>> documento = mixin.marcar_como_cancelado(
            ...     123,
            ...     "Cancelado por error en datos",
            ...     456
            ... )
        """
        start_time = datetime.now()

        try:
            datos_adicionales = {
                "motivo_cancelacion": motivo,
                "fecha_cancelacion": datetime.now()
            }

            if usuario_id:
                datos_adicionales["usuario_cancelacion"] = usuario_id

            documento = self.actualizar_estado_documento(
                documento_id,
                EstadoDocumentoSifenEnum.CANCELADO.value,
                datos_adicionales
            )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("marcar_como_cancelado", duration, 1)

            log_repository_operation(
                "marcar_como_cancelado",
                "Documento",
                documento_id,
                {
                    "motivo": motivo,
                    "usuario_id": usuario_id,
                    "cancelado_at": datetime.now().isoformat()
                }
            )

            return documento

        except Exception as e:
            handle_repository_error(
                e, "marcar_como_cancelado", "Documento", documento_id)
            raise

    # ===============================================
    # PROCESAMIENTO RESPUESTAS SIFEN
    # ===============================================

    def procesar_respuesta_sifen(self,
                                 documento_id: int,
                                 codigo_respuesta: str,
                                 mensaje: str,
                                 numero_protocolo: Optional[str] = None,
                                 url_consulta: Optional[str] = None,
                                 observaciones: Optional[str] = None,
                                 tiempo_respuesta: Optional[float] = None) -> Documento:
        """
        Procesa una respuesta completa de SIFEN.

        Args:
            documento_id: ID del documento
            codigo_respuesta: Código de respuesta SIFEN
            mensaje: Mensaje de respuesta
            numero_protocolo: Número de protocolo asignado
            url_consulta: URL de consulta pública
            observaciones: Observaciones SIFEN
            tiempo_respuesta: Tiempo de respuesta en segundos

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenValidationError: Si la respuesta no es válida

        Example:
            >>> documento = mixin.procesar_respuesta_sifen(
            ...     123,
            ...     "0260",
            ...     "Aprobado",
            ...     "PROT123456789",
            ...     "https://sifen.set.gov.py/consulta/...",
            ...     "Sin observaciones",
            ...     2.5
            ... )
        """
        start_time = datetime.now()

        try:
            # Validar código de respuesta
            if not codigo_respuesta:
                raise SifenValidationError(
                    "Código de respuesta es requerido",
                    field="codigo_respuesta"
                )

            # Determinar nuevo estado basado en código
            nuevo_estado = self._determinar_estado_por_codigo(codigo_respuesta)

            # Preparar datos adicionales
            datos_adicionales = {
                "codigo_respuesta_sifen": codigo_respuesta,
                "mensaje_sifen": mensaje,
                "fecha_respuesta_sifen": datetime.now()
            }

            if numero_protocolo:
                datos_adicionales["numero_protocolo"] = numero_protocolo

            if url_consulta:
                datos_adicionales["url_consulta_publica"] = url_consulta

            if observaciones:
                datos_adicionales["observaciones_sifen"] = observaciones

            if tiempo_respuesta:
                datos_adicionales["tiempo_respuesta"] = tiempo_respuesta

            # Actualizar estado
            documento = self.actualizar_estado_documento(
                documento_id,
                nuevo_estado,
                datos_adicionales
            )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("procesar_respuesta_sifen", duration, 1)

            log_repository_operation(
                "procesar_respuesta_sifen",
                "Documento",
                documento_id,
                {
                    "codigo_respuesta": codigo_respuesta,
                    "nuevo_estado": nuevo_estado,
                    "has_protocolo": bool(numero_protocolo),
                    "has_url_consulta": bool(url_consulta),
                    "tiempo_respuesta": tiempo_respuesta
                }
            )

            return documento

        except Exception as e:
            handle_repository_error(
                e, "procesar_respuesta_sifen", "Documento", documento_id)
            raise

    def marcar_como_aprobado(self,
                             documento_id: int,
                             numero_protocolo: str,
                             url_consulta: Optional[str] = None) -> Documento:
        """
        Marca un documento como aprobado por SIFEN (código 0260).

        Args:
            documento_id: ID del documento
            numero_protocolo: Número de protocolo SIFEN
            url_consulta: URL de consulta pública

        Returns:
            Documento: Documento actualizado

        Example:
            >>> documento = mixin.marcar_como_aprobado(
            ...     123,
            ...     "PROT123456789",
            ...     "https://sifen.set.gov.py/consulta/..."
            ... )
        """
        return self.procesar_respuesta_sifen(
            documento_id,
            "0260",
            "Aprobado",
            numero_protocolo,
            url_consulta
        )

    def marcar_como_aprobado_observacion(self,
                                         documento_id: int,
                                         numero_protocolo: str,
                                         observaciones: str,
                                         url_consulta: Optional[str] = None) -> Documento:
        """
        Marca un documento como aprobado con observaciones (código 1005).

        Args:
            documento_id: ID del documento
            numero_protocolo: Número de protocolo SIFEN
            observaciones: Observaciones SIFEN
            url_consulta: URL de consulta pública

        Returns:
            Documento: Documento actualizado

        Example:
            >>> documento = mixin.marcar_como_aprobado_observacion(
            ...     123,
            ...     "PROT123456789",
            ...     "Documento aprobado con observaciones menores"
            ... )
        """
        return self.procesar_respuesta_sifen(
            documento_id,
            "1005",
            "Aprobado con observaciones",
            numero_protocolo,
            url_consulta,
            observaciones
        )

    def marcar_como_rechazado(self,
                              documento_id: int,
                              codigo_error: str,
                              mensaje_error: str,
                              detalles_error: Optional[str] = None) -> Documento:
        """
        Marca un documento como rechazado por SIFEN.

        Args:
            documento_id: ID del documento
            codigo_error: Código de error SIFEN
            mensaje_error: Mensaje de error
            detalles_error: Detalles adicionales del error

        Returns:
            Documento: Documento actualizado

        Example:
            >>> documento = mixin.marcar_como_rechazado(
            ...     123,
            ...     "1000",
            ...     "CDC no corresponde con XML",
            ...     "El CDC calculado no coincide con el proporcionado"
            ... )
        """
        observaciones = detalles_error if detalles_error else None

        return self.procesar_respuesta_sifen(
            documento_id,
            codigo_error,
            mensaje_error,
            None,  # No hay protocolo en rechazos
            None,  # No hay URL consulta en rechazos
            observaciones
        )

    # ===============================================
    # GESTIÓN DE TIMESTAMPS
    # ===============================================

    def update_workflow_timestamps(self,
                                   documento_id: int,
                                   timestamps: Dict[str, datetime]) -> Documento:
        """
        Actualiza timestamps específicos del workflow.

        Args:
            documento_id: ID del documento
            timestamps: Diccionario con timestamps a actualizar

        Returns:
            Documento: Documento actualizado

        Raises:
            SifenEntityNotFoundError: Si el documento no existe

        Example:
            >>> documento = mixin.update_workflow_timestamps(123, {
            ...     "fecha_generacion_xml": datetime.now(),
            ...     "fecha_firma_digital": datetime.now()
            ... })
        """
        start_time = datetime.now()

        try:
            documento = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento:
                raise SifenEntityNotFoundError("Documento", documento_id)

            # Actualizar timestamps
            for field, timestamp in timestamps.items():
                if hasattr(documento, field):
                    setattr(documento, field, timestamp)

            # Actualizar timestamp de modificación
            setattr(documento, 'updated_at', datetime.now())

            self.db.commit()
            self.db.refresh(documento)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("update_workflow_timestamps", duration, 1)

            log_repository_operation(
                "update_workflow_timestamps",
                "Documento",
                documento_id,
                {
                    "timestamps_updated": list(timestamps.keys()),
                    "count": len(timestamps)
                }
            )

            return documento

        except SifenEntityNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(
                e, "update_workflow_timestamps", "Documento", documento_id)
            raise handle_database_exception(e, "update_workflow_timestamps")

    def get_processing_duration(self, documento_id: int) -> Optional[timedelta]:
        """
        Obtiene la duración total del procesamiento del documento.

        Args:
            documento_id: ID del documento

        Returns:
            Optional[timedelta]: Duración del procesamiento o None si no está completo

        Example:
            >>> duration = mixin.get_processing_duration(123)
            >>> if duration:
            ...     print(f"Procesamiento tomó: {duration.total_seconds()} segundos")
        """
        try:
            documento = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento:
                return None

            created_at = getattr(documento, 'created_at', None)
            fecha_respuesta = getattr(documento, 'fecha_respuesta_sifen', None)

            if created_at and fecha_respuesta:
                return fecha_respuesta - created_at

            return None

        except Exception as e:
            handle_repository_error(
                e, "get_processing_duration", "Documento", documento_id)
            return None

    def get_time_since_creation(self, documento_id: int) -> Optional[timedelta]:
        """
        Obtiene el tiempo transcurrido desde la creación del documento.

        Args:
            documento_id: ID del documento

        Returns:
            Optional[timedelta]: Tiempo transcurrido o None si no existe

        Example:
            >>> time_since = mixin.get_time_since_creation(123)
            >>> if time_since:
            ...     print(f"Documento creado hace: {time_since.total_seconds()} segundos")
        """
        try:
            documento = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento:
                return None

            created_at = getattr(documento, 'created_at', None)

            if created_at:
                return datetime.now() - created_at

            return None

        except Exception as e:
            handle_repository_error(
                e, "get_time_since_creation", "Documento", documento_id)
            return None

    # ===============================================
    # CONSULTAS DE ESTADO
    # ===============================================

    def get_documentos_by_workflow_stage(self,
                                         stage: str,
                                         empresa_id: Optional[int] = None,
                                         limit: Optional[int] = None,
                                         offset: int = 0) -> List[Documento]:
        """
        Obtiene documentos por etapa específica del workflow.

        Args:
            stage: Etapa del workflow (estado)
            empresa_id: ID de empresa (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[Documento]: Lista de documentos en la etapa

        Raises:
            SifenValidationError: Si el stage no es válido

        Example:
            >>> documentos = mixin.get_documentos_by_workflow_stage(
            ...     "firmado",
            ...     empresa_id=1,
            ...     limit=10
            ... )
        """
        start_time = datetime.now()

        try:
            # Validar stage
            valid_stages = [e.value for e in EstadoDocumentoSifenEnum]
            if stage not in valid_stages:
                raise SifenValidationError(
                    f"Stage '{stage}' no es válido",
                    field="stage",
                    value=stage
                )

            # Construir query
            query = self.db.query(self.model).filter(
                text("estado = :estado")
            ).params(estado=stage)

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Aplicar paginación
            if limit:
                query = query.limit(limit)
            if offset > 0:
                query = query.offset(offset)

            # Ordenar por fecha de actualización (más recientes primero)
            documentos = query.order_by(desc(self.model.updated_at)).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_documentos_by_workflow_stage", duration, len(documentos))

            log_repository_operation(
                "get_documentos_by_workflow_stage",
                "Documento",
                None,
                {
                    "stage": stage,
                    "empresa_id": empresa_id,
                    "count": len(documentos),
                    "limit": limit,
                    "offset": offset
                }
            )

            return documentos

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_documentos_by_workflow_stage", "Documento")
            raise handle_database_exception(
                e, "get_documentos_by_workflow_stage")

    def get_stuck_documents(self,
                            empresa_id: Optional[int] = None,
                            check_time_limits: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene documentos que pueden estar "atascados" en el workflow.

        Args:
            empresa_id: ID de empresa (opcional)
            check_time_limits: Si verificar límites de tiempo por estado

        Returns:
            List[Dict]: Lista de documentos atascados con detalles

        Example:
            >>> stuck_docs = mixin.get_stuck_documents(empresa_id=1)
            >>> for doc in stuck_docs:
            ...     print(f"Doc {doc['id']}: {doc['reason']}")
        """
        start_time = datetime.now()

        try:
            stuck_documents = []

            # Obtener documentos por estado no final
            estados_no_finales = [
                EstadoDocumentoSifenEnum.BORRADOR.value,
                EstadoDocumentoSifenEnum.VALIDADO.value,
                EstadoDocumentoSifenEnum.GENERADO.value,
                EstadoDocumentoSifenEnum.FIRMADO.value,
                EstadoDocumentoSifenEnum.ENVIADO.value,
                EstadoDocumentoSifenEnum.ERROR_ENVIO.value
            ]

            for estado in estados_no_finales:
                query = self.db.query(self.model).filter(
                    text("estado = :estado")
                ).params(estado=estado)

                if empresa_id:
                    query = query.filter(self.model.empresa_id == empresa_id)

                documentos = query.all()

                for documento in documentos:
                    stuck_info = self._check_if_stuck(
                        documento, check_time_limits)
                    if stuck_info:
                        stuck_documents.append(stuck_info)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("get_stuck_documents",
                                   duration, len(stuck_documents))

            log_repository_operation(
                "get_stuck_documents",
                "Documento",
                None,
                {
                    "empresa_id": empresa_id,
                    "stuck_count": len(stuck_documents),
                    "check_time_limits": check_time_limits
                }
            )

            return stuck_documents

        except Exception as e:
            handle_repository_error(e, "get_stuck_documents", "Documento")
            raise handle_database_exception(e, "get_stuck_documents")

    def get_processing_statistics(self,
                                  empresa_id: Optional[int] = None,
                                  fecha_desde: Optional[date] = None,
                                  fecha_hasta: Optional[date] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas del procesamiento de documentos.

        Args:
            empresa_id: ID de empresa (opcional)
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict: Estadísticas completas del procesamiento

        Example:
            >>> stats = mixin.get_processing_statistics(
            ...     empresa_id=1,
            ...     fecha_desde=date(2025, 1, 1),
            ...     fecha_hasta=date(2025, 1, 31)
            ... )
            >>> print(f"Tasa de aprobación: {stats['approval_rate']}%")
        """
        start_time = datetime.now()

        try:
            # Construir query base
            query = self.db.query(self.model)

            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            if fecha_desde:
                query = query.filter(self.model.created_at >= fecha_desde)

            if fecha_hasta:
                query = query.filter(self.model.created_at <= fecha_hasta)

            # Obtener todos los documentos del período
            documentos = query.all()

            # Calcular estadísticas
            stats = {
                "total_documentos": len(documentos),
                "por_estado": {},
                "por_tipo": {},
                "tiempos_procesamiento": {},
                "approval_rate": 0.0,
                "avg_processing_time": None,
                "documentos_atascados": 0,
                "período": {
                    "desde": fecha_desde.isoformat() if fecha_desde else None,
                    "hasta": fecha_hasta.isoformat() if fecha_hasta else None
                }
            }

            # Estadísticas por estado
            for estado in EstadoDocumentoSifenEnum:
                count = sum(1 for doc in documentos if getattr(
                    doc, 'estado', '') == estado.value)
                stats["por_estado"][estado.value] = count

            # Estadísticas por tipo
            for tipo in TipoDocumentoSifenEnum:
                count = sum(1 for doc in documentos if getattr(
                    doc, 'tipo_documento', '') == tipo.value)
                stats["por_tipo"][tipo.value] = count

            # Calcular tasa de aprobación
            documentos_procesados = sum(1 for doc in documentos
                                        if getattr(doc, 'estado', '') in [
                                            EstadoDocumentoSifenEnum.APROBADO.value,
                                            EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value,
                                            EstadoDocumentoSifenEnum.RECHAZADO.value
                                        ])

            if documentos_procesados > 0:
                documentos_aprobados = sum(1 for doc in documentos
                                           if getattr(doc, 'estado', '') in [
                                               EstadoDocumentoSifenEnum.APROBADO.value,
                                               EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value
                                           ])
                stats["approval_rate"] = (
                    documentos_aprobados / documentos_procesados) * 100

            # Calcular tiempo promedio de procesamiento
            tiempos_procesamiento = []
            for documento in documentos:
                created_at = getattr(documento, 'created_at', None)
                fecha_respuesta = getattr(
                    documento, 'fecha_respuesta_sifen', None)

                if created_at and fecha_respuesta:
                    duration = (fecha_respuesta - created_at).total_seconds()
                    tiempos_procesamiento.append(duration)

            if tiempos_procesamiento:
                stats["avg_processing_time"] = sum(
                    tiempos_procesamiento) / len(tiempos_procesamiento)
                stats["tiempos_procesamiento"] = {
                    "promedio": stats["avg_processing_time"],
                    "minimo": min(tiempos_procesamiento),
                    "maximo": max(tiempos_procesamiento),
                    "documentos_con_tiempo": len(tiempos_procesamiento)
                }

            # Contar documentos atascados
            stuck_docs = self.get_stuck_documents(
                empresa_id, check_time_limits=True)
            stats["documentos_atascados"] = len(stuck_docs)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("get_processing_statistics", duration, 1)

            log_repository_operation(
                "get_processing_statistics",
                "Documento",
                None,
                {
                    "empresa_id": empresa_id,
                    "total_documentos": stats["total_documentos"],
                    "approval_rate": stats["approval_rate"],
                    "documentos_atascados": stats["documentos_atascados"]
                }
            )

            return stats

        except Exception as e:
            handle_repository_error(
                e, "get_processing_statistics", "Documento")
            raise handle_database_exception(e, "get_processing_statistics")

    # ===============================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ===============================================

    def _aplicar_datos_adicionales(self,
                                   documento: Documento,
                                   datos: Dict[str, Any]) -> None:
        """
        Aplica datos adicionales al documento.

        Args:
            documento: Documento a actualizar
            datos: Datos adicionales a aplicar
        """
        for key, value in datos.items():
            if hasattr(documento, key):
                setattr(documento, key, value)

    def _actualizar_timestamps_por_estado(self,
                                          documento: Documento,
                                          estado: str) -> None:
        """
        Actualiza timestamps específicos según el estado.

        Args:
            documento: Documento a actualizar
            estado: Nuevo estado del documento
        """
        now = datetime.now()

        # Mapeo de estados a campos de timestamp
        timestamp_mapping = {
            EstadoDocumentoSifenEnum.GENERADO.value: "fecha_generacion_xml",
            EstadoDocumentoSifenEnum.FIRMADO.value: "fecha_firma_digital",
            EstadoDocumentoSifenEnum.ENVIADO.value: "fecha_envio_sifen",
            EstadoDocumentoSifenEnum.APROBADO.value: "fecha_respuesta_sifen",
            EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value: "fecha_respuesta_sifen",
            EstadoDocumentoSifenEnum.RECHAZADO.value: "fecha_respuesta_sifen",
        }

        timestamp_field = timestamp_mapping.get(estado)
        if timestamp_field and hasattr(documento, timestamp_field):
            # Solo actualizar si no tiene valor previo
            if not getattr(documento, timestamp_field, None):
                setattr(documento, timestamp_field, now)

    def _determinar_estado_por_codigo(self, codigo: str) -> str:
        """
        Determina el estado del documento basado en código SIFEN.

        Args:
            codigo: Código de respuesta SIFEN

        Returns:
            str: Estado correspondiente
        """
        return SIFEN_RESPONSE_CODES.get(
            codigo,
            EstadoDocumentoSifenEnum.RECHAZADO.value
        )

    def _check_if_stuck(self,
                        documento: Documento,
                        check_time_limits: bool) -> Optional[Dict[str, Any]]:
        """
        Verifica si un documento está atascado.

        Args:
            documento: Documento a verificar
            check_time_limits: Si verificar límites de tiempo

        Returns:
            Optional[Dict]: Información del documento atascado o None
        """
        documento_id = getattr(documento, 'id', None)
        estado = getattr(documento, 'estado', '')
        updated_at = getattr(documento, 'updated_at', None)

        if not all([documento_id, estado, updated_at]):
            return None
        if updated_at is None:
            return None

        stuck_info = {
            "id": documento_id,
            "estado": estado,
            "updated_at": updated_at.isoformat(),
            "time_in_state": None,
            "reason": None,
            "severity": "low"
        }

        # Calcular tiempo en estado actual
        time_in_state = datetime.now() - updated_at
        stuck_info["time_in_state"] = time_in_state.total_seconds()

        # Verificar límites de tiempo si se solicita
        if check_time_limits and estado in MAX_TIME_IN_STATE:
            max_hours = MAX_TIME_IN_STATE[estado]
            if time_in_state > timedelta(hours=max_hours):
                stuck_info["reason"] = f"Documento lleva {time_in_state.total_seconds()/3600:.1f}h en estado '{estado}' (límite: {max_hours}h)"
                stuck_info["severity"] = "high" if time_in_state > timedelta(
                    hours=max_hours * 2) else "medium"
                return stuck_info

        # Verificar otros criterios de documento atascado
        # Documento enviado hace más de 1 hora sin respuesta
        if estado == EstadoDocumentoSifenEnum.ENVIADO.value:
            if time_in_state > timedelta(hours=1):
                stuck_info["reason"] = f"Documento enviado hace {time_in_state.total_seconds()/3600:.1f}h sin respuesta de SIFEN"
                stuck_info["severity"] = "medium"
                return stuck_info

        # Documento firmado hace más de 72 horas (límite SIFEN)
        if estado == EstadoDocumentoSifenEnum.FIRMADO.value:
            if time_in_state > timedelta(hours=72):
                stuck_info["reason"] = f"Documento firmado hace {time_in_state.total_seconds()/3600:.1f}h (límite SIFEN: 72h)"
                stuck_info["severity"] = "high"
                return stuck_info

        return None

    # ===============================================
    # MÉTODOS DE UTILIDAD PARA DTOS
    # ===============================================

    def get_documento_estado_dto(self, documento_id: int) -> Optional[DocumentoEstadoDTO]:
        """
        Obtiene DTO completo del estado de un documento.

        Args:
            documento_id: ID del documento

        Returns:
            Optional[DocumentoEstadoDTO]: DTO del estado o None si no existe

        Example:
            >>> estado_dto = mixin.get_documento_estado_dto(123)
            >>> if estado_dto:
            ...     print(f"Estado: {estado_dto.estado_actual}")
        """
        try:
            documento = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento:
                return None

            # Obtener datos del documento
            estado_actual = getattr(documento, 'estado', '')
            fecha_emision = getattr(documento, 'fecha_emision', None)

            # Verificar capacidades
            from .validation_mixin import DocumentoValidationMixin

            # Crear una instancia temporal para usar los métodos de validación
            temp_validator = type('TempValidator', (DocumentoValidationMixin,), {
                'db': self.db,
                'model': self.model,
                'validate_estado_transition': self.validate_estado_transition
            })()

            puede_ser_editado = temp_validator.can_be_modified(documento)
            puede_ser_enviado = temp_validator.can_be_sent(documento)
            puede_ser_cancelado = temp_validator.can_be_cancelled(documento)

            # Determinar próxima acción
            proxima_accion = self._get_next_action(documento)

            # Calcular tiempo límite para envío
            tiempo_limite_envio = None
            if fecha_emision and estado_actual == EstadoDocumentoSifenEnum.FIRMADO.value:
                tiempo_limite_envio = datetime.combine(
                    fecha_emision, datetime.min.time()) + timedelta(hours=72)

            return DocumentoEstadoDTO(
                documento_id=documento_id,
                estado_actual=estado_actual,
                descripcion_estado=get_state_description(estado_actual),
                fecha_cambio_estado=getattr(
                    documento, 'updated_at', datetime.now()),
                puede_ser_editado=puede_ser_editado,
                puede_ser_enviado=puede_ser_enviado,
                puede_ser_cancelado=puede_ser_cancelado,
                puede_ser_anulado=estado_actual in [
                    EstadoDocumentoSifenEnum.APROBADO.value, EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value],
                esta_en_sifen=estado_actual in [EstadoDocumentoSifenEnum.ENVIADO.value, EstadoDocumentoSifenEnum.APROBADO.value,
                                                EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value, EstadoDocumentoSifenEnum.RECHAZADO.value],
                esta_aprobado=estado_actual in [
                    EstadoDocumentoSifenEnum.APROBADO.value, EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value],
                es_documento_fiscal=estado_actual in [EstadoDocumentoSifenEnum.APROBADO.value, EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value] and bool(
                    getattr(documento, 'numero_protocolo', None)),
                fecha_creacion=getattr(
                    documento, 'created_at', datetime.now()),
                fecha_generacion_xml=getattr(
                    documento, 'fecha_generacion_xml', None),
                fecha_firma_digital=getattr(
                    documento, 'fecha_firma_digital', None),
                fecha_envio_sifen=getattr(
                    documento, 'fecha_envio_sifen', None),
                fecha_respuesta_sifen=getattr(
                    documento, 'fecha_respuesta_sifen', None),
                proxima_accion=proxima_accion,
                tiempo_limite_envio=tiempo_limite_envio
            )

        except Exception as e:
            handle_repository_error(
                e, "get_documento_estado_dto", "Documento", documento_id)
            return None

    def get_documento_sifen_dto(self, documento_id: int) -> Optional[DocumentoSifenDTO]:
        """
        Obtiene DTO completo de información SIFEN de un documento.

        Args:
            documento_id: ID del documento

        Returns:
            Optional[DocumentoSifenDTO]: DTO SIFEN o None si no existe

        Example:
            >>> sifen_dto = mixin.get_documento_sifen_dto(123)
            >>> if sifen_dto:
            ...     print(f"Protocolo: {sifen_dto.numero_protocolo}")
        """
        try:
            documento = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento:
                return None

            # Calcular tiempo de respuesta
            fecha_envio = getattr(documento, 'fecha_envio_sifen', None)
            fecha_respuesta = getattr(documento, 'fecha_respuesta_sifen', None)
            tiempo_respuesta = None

            if fecha_envio and fecha_respuesta:
                tiempo_respuesta = (
                    fecha_respuesta - fecha_envio).total_seconds()

            # Obtener errores y observaciones
            observaciones_sifen = getattr(
                documento, 'observaciones_sifen', None)
            errores_sifen = []
            observaciones_list = []

            if observaciones_sifen:
                # Separar errores de observaciones (simplificado)
                if getattr(documento, 'estado', '') == EstadoDocumentoSifenEnum.RECHAZADO.value:
                    errores_sifen = [observaciones_sifen]
                else:
                    observaciones_list = [observaciones_sifen]

            return DocumentoSifenDTO(
                documento_id=documento_id,
                codigo_respuesta=getattr(
                    documento, 'codigo_respuesta_sifen', None),
                mensaje_respuesta=getattr(documento, 'mensaje_sifen', None),
                numero_protocolo=getattr(documento, 'numero_protocolo', None),
                url_consulta_publica=getattr(
                    documento, 'url_consulta_publica', None),
                url_kude=None,  # TODO: Implementar generación URL KuDE
                qr_code_data=getattr(documento, 'codigo_qr', None),
                ambiente_sifen="test",  # TODO: Obtener de configuración
                version_sifen="150",
                request_id=getattr(documento, 'request_id', None),
                tiempo_respuesta=tiempo_respuesta,
                intentos_envio=1,  # TODO: Implementar contador de intentos
                ultimo_intento=getattr(documento, 'fecha_envio_sifen', None),
                errores_sifen=errores_sifen,
                observaciones_sifen=observaciones_list,
                certificado_serial=getattr(
                    documento, 'certificado_serial', None),
                certificado_emisor=None  # TODO: Obtener de certificado
            )

        except Exception as e:
            handle_repository_error(
                e, "get_documento_sifen_dto", "Documento", documento_id)
            return None

    def _get_next_action(self, documento: Documento) -> Optional[str]:
        """
        Determina la próxima acción recomendada para un documento.

        Args:
            documento: Documento a analizar

        Returns:
            Optional[str]: Descripción de la próxima acción
        """
        estado = getattr(documento, 'estado', '')

        action_mapping = {
            EstadoDocumentoSifenEnum.BORRADOR.value: "Completar datos y validar",
            EstadoDocumentoSifenEnum.VALIDADO.value: "Generar XML",
            EstadoDocumentoSifenEnum.GENERADO.value: "Firmar digitalmente",
            EstadoDocumentoSifenEnum.FIRMADO.value: "Enviar a SIFEN",
            EstadoDocumentoSifenEnum.ENVIADO.value: "Esperando respuesta SIFEN",
            EstadoDocumentoSifenEnum.ERROR_ENVIO.value: "Reintentar envío",
            EstadoDocumentoSifenEnum.APROBADO.value: "Documento fiscal válido",
            EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value: "Revisar observaciones",
            EstadoDocumentoSifenEnum.RECHAZADO.value: "Revisar errores y corregir",
            EstadoDocumentoSifenEnum.CANCELADO.value: "Documento cancelado",
            EstadoDocumentoSifenEnum.ANULADO.value: "Documento anulado"
        }

        return action_mapping.get(estado)


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "SifenStateMixin",

    # Constantes
    "SIFEN_RESPONSE_CODES",
    "MAX_TIME_IN_STATE",
    "STATES_REQUIRING_SIFEN_DATA"
]
