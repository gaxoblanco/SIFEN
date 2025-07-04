# ===============================================
# ARCHIVO: backend/app/repositories/documento/validation_mixin.py
# PROPÓSITO: Mixin para validaciones específicas de documentos SIFEN
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para validaciones específicas de documentos SIFEN.
Maneja integridad, unicidad y reglas de negocio.

Este mixin implementa todas las validaciones necesarias para documentos
electrónicos SIFEN:
- Validaciones de unicidad (CDC, numeración)
- Validaciones de transiciones de estado
- Validaciones de contenido y datos
- Validaciones de reglas de negocio específicas

Clase principal:
- DocumentoValidationMixin: Mixin con todas las validaciones
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenValidationError,
    SifenDuplicateEntityError,
    SifenEntityNotFoundError,
    SifenBusinessLogicError,
    SifenDocumentStateError,
    SifenTimbradoError,
    SifenDatabaseError,
    handle_database_exception
)
from app.models.documento import (
    Documento,
    EstadoDocumentoSifenEnum,
    TipoDocumentoSifenEnum,
    TipoOperacionSifenEnum,
    CondicionOperacionSifenEnum,
    MonedaSifenEnum
)
from app.schemas.documento import (
    DocumentoCreateDTO,
    DocumentoUpdateDTO
)
from .utils import (
    VALID_STATE_TRANSITIONS,
    EDITABLE_STATES,
    FINAL_STATES,
    SIFEN_SUCCESS_CODES,
    validate_cdc_format,
    validate_establishment_code,
    validate_document_number,
    validate_amount_precision,
    can_transition_to,
    is_editable_state,
    is_final_state,
    get_next_valid_states,
    get_state_description,
    is_within_sifen_time_limit,
    format_numero_completo,
    normalize_cdc,
    normalize_numero_completo,
    log_repository_operation,
    log_performance_metric,
    handle_repository_error
)

logger = get_logger(__name__)

# ===============================================
# CONSTANTES ESPECÍFICAS DE VALIDACIÓN
# ===============================================

# Tipos de documento que requieren documento original
DOCUMENT_TYPES_REQUIRING_ORIGINAL = ["5", "6"]  # NCE, NDE

# Tipos de operación que requieren datos específicos
OPERATION_TYPES_REQUIRING_EXPORT_DATA = ["2"]  # Exportación
OPERATION_TYPES_REQUIRING_IMPORT_DATA = ["3"]  # Importación (AFE)

# Montos mínimos y máximos permitidos
MIN_DOCUMENT_AMOUNT = Decimal("0.01")
MAX_DOCUMENT_AMOUNT = Decimal("999999999999.99")

# Tiempo límite para envío a SIFEN (72 horas)
SIFEN_SUBMISSION_LIMIT_HOURS = 72

# Límites de caracteres para campos de texto
MAX_LENGTH_DESCRIPCION = 500
MAX_LENGTH_OBSERVACIONES = 1000
MAX_LENGTH_MOTIVO = 500

# ===============================================
# CLASE VALIDATION MIXIN
# ===============================================


class DocumentoValidationMixin:
    """
    Mixin para validaciones específicas de documentos SIFEN.

    Proporciona métodos para validar:
    - Unicidad de datos (CDC, numeración)
    - Transiciones de estado válidas
    - Contenido y estructura de documentos
    - Reglas de negocio específicas SIFEN
    - Requisitos por tipo de documento

    Requiere que la clase que lo use tenga:
    - self.db: Session SQLAlchemy
    - self.model: Modelo Documento
    """

    db: Session
    model: type[Documento]

    # ===============================================
    # VALIDACIONES DE UNICIDAD
    # ===============================================

    def is_numero_disponible(self,
                             establecimiento: str,
                             punto_expedicion: str,
                             numero_documento: str,
                             empresa_id: int,
                             exclude_id: Optional[int] = None) -> bool:
        """
        Verifica si un número de documento está disponible.

        Args:
            establecimiento: Código establecimiento (001-999)
            punto_expedicion: Código punto expedición (001-999)
            numero_documento: Número del documento (0000001-9999999)
            empresa_id: ID de la empresa
            exclude_id: ID del documento a excluir (para updates)

        Returns:
            bool: True si el número está disponible

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> disponible = mixin.is_numero_disponible("001", "001", "0000123", 1)
            >>> if not disponible:
            ...     raise SifenDuplicateEntityError("Documento", "numero", "001-001-0000123")
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not all([establecimiento, punto_expedicion, numero_documento, empresa_id]):
                raise SifenValidationError(
                    "Todos los parámetros son requeridos para verificar unicidad",
                    field="numero_completo"
                )

            # Validar formato de códigos
            if not validate_establishment_code(establecimiento):
                raise SifenValidationError(
                    "Código de establecimiento inválido",
                    field="establecimiento",
                    value=establecimiento
                )

            if not validate_establishment_code(punto_expedicion):
                raise SifenValidationError(
                    "Código de punto expedición inválido",
                    field="punto_expedicion",
                    value=punto_expedicion
                )

            if not validate_document_number(numero_documento):
                raise SifenValidationError(
                    "Número de documento inválido",
                    field="numero_documento",
                    value=numero_documento
                )

            # Construir query
            query = self.db.query(self.model).filter(
                and_(
                    self.model.establecimiento == establecimiento,
                    self.model.punto_expedicion == punto_expedicion,
                    self.model.numero_documento == numero_documento,
                    self.model.empresa_id == empresa_id
                )
            )

            # Excluir documento específico si se proporciona
            if exclude_id:
                query = query.filter(self.model.id != exclude_id)

            # Verificar existencia
            existing = query.first()
            is_available = existing is None

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("is_numero_disponible", duration, 1)

            numero_completo = format_numero_completo(
                establecimiento, punto_expedicion, numero_documento)

            log_repository_operation(
                "is_numero_disponible",
                "Documento",
                None,
                {
                    "numero_completo": numero_completo,
                    "empresa_id": empresa_id,
                    "disponible": is_available,
                    "exclude_id": exclude_id
                }
            )

            return is_available

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "is_numero_disponible", "Documento")
            raise handle_database_exception(e, "is_numero_disponible")

    def is_cdc_disponible(self,
                          cdc: str,
                          exclude_id: Optional[int] = None) -> bool:
        """
        Verifica si un CDC está disponible a nivel nacional.

        Args:
            cdc: CDC de 44 dígitos
            exclude_id: ID del documento a excluir (para updates)

        Returns:
            bool: True si el CDC está disponible

        Raises:
            SifenValidationError: Si el CDC no es válido
            SifenDatabaseError: Si hay error en la consulta

        Example:
            >>> disponible = mixin.is_cdc_disponible("12345678901234567890123456789012345678901234")
            >>> if not disponible:
            ...     raise SifenDuplicateEntityError("Documento", "cdc", cdc)
        """
        start_time = datetime.now()

        try:
            # Validar CDC
            if not cdc:
                raise SifenValidationError(
                    "CDC es requerido para verificar unicidad",
                    field="cdc"
                )

            # Normalizar CDC
            cdc_normalized = normalize_cdc(cdc)

            # Validar formato
            if not validate_cdc_format(cdc_normalized):
                raise SifenValidationError(
                    "CDC debe tener exactamente 44 dígitos numéricos",
                    field="cdc",
                    value=cdc
                )

            # Construir query
            query = self.db.query(self.model).filter(
                text("cdc = :cdc")
            ).params(cdc=cdc_normalized)

            # Excluir documento específico si se proporciona
            if exclude_id:
                query = query.filter(self.model.id != exclude_id)

            # Verificar existencia
            existing = query.first()
            is_available = existing is None

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("is_cdc_disponible", duration, 1)

            log_repository_operation(
                "is_cdc_disponible",
                "Documento",
                None,
                {
                    "cdc": cdc_normalized,
                    "disponible": is_available,
                    "exclude_id": exclude_id
                }
            )

            return is_available

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(e, "is_cdc_disponible", "Documento")
            raise handle_database_exception(e, "is_cdc_disponible")

    def validate_unique_constraints(self,
                                    document_data: Dict[str, Any],
                                    exclude_id: Optional[int] = None) -> None:
        """
        Valida todas las restricciones de unicidad de un documento.

        Args:
            document_data: Datos del documento a validar
            exclude_id: ID del documento a excluir (para updates)

        Raises:
            SifenValidationError: Si faltan campos requeridos
            SifenDuplicateEntityError: Si hay duplicados
            SifenDatabaseError: Si hay error en consultas

        Example:
            >>> mixin.validate_unique_constraints({
            ...     "establecimiento": "001",
            ...     "punto_expedicion": "001", 
            ...     "numero_documento": "0000123",
            ...     "empresa_id": 1,
            ...     "cdc": "12345678901234567890123456789012345678901234"
            ... })
        """
        start_time = datetime.now()

        try:
            # Validar numeración única
            if all(k in document_data for k in ["establecimiento", "punto_expedicion", "numero_documento", "empresa_id"]):
                if not self.is_numero_disponible(
                    document_data["establecimiento"],
                    document_data["punto_expedicion"],
                    document_data["numero_documento"],
                    document_data["empresa_id"],
                    exclude_id
                ):
                    numero_completo = format_numero_completo(
                        document_data["establecimiento"],
                        document_data["punto_expedicion"],
                        document_data["numero_documento"]
                    )
                    raise SifenDuplicateEntityError(
                        "Documento",
                        "numero_completo",
                        numero_completo
                    )

            # Validar CDC único (si se proporciona)
            if "cdc" in document_data and document_data["cdc"]:
                if not self.is_cdc_disponible(document_data["cdc"], exclude_id):
                    raise SifenDuplicateEntityError(
                        "Documento",
                        "cdc",
                        document_data["cdc"]
                    )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_unique_constraints", duration, 1)

            log_repository_operation(
                "validate_unique_constraints",
                "Documento",
                exclude_id,
                {
                    "validations_passed": True,
                    "has_cdc": "cdc" in document_data and bool(document_data["cdc"]),
                    "has_numeracion": all(k in document_data for k in ["establecimiento", "punto_expedicion", "numero_documento"])
                }
            )

        except (SifenValidationError, SifenDuplicateEntityError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "validate_unique_constraints", "Documento")
            raise handle_database_exception(e, "validate_unique_constraints")

    # ===============================================
    # VALIDACIONES DE ESTADO
    # ===============================================

    def validate_estado_transition(self,
                                   current_state: str,
                                   target_state: str,
                                   documento_id: Optional[int] = None) -> None:
        """
        Valida si una transición de estado es válida.

        Args:
            current_state: Estado actual del documento
            target_state: Estado objetivo
            documento_id: ID del documento (para logs)

        Raises:
            SifenValidationError: Si los estados no son válidos
            SifenDocumentStateError: Si la transición no es permitida

        Example:
            >>> mixin.validate_estado_transition("borrador", "validado", 123)
            >>> # Válida
            >>> mixin.validate_estado_transition("aprobado", "borrador", 123)
            >>> # Raises SifenDocumentStateError
        """
        start_time = datetime.now()

        try:
            # Validar estados
            if not current_state:
                raise SifenValidationError(
                    "Estado actual es requerido",
                    field="current_state"
                )

            if not target_state:
                raise SifenValidationError(
                    "Estado objetivo es requerido",
                    field="target_state"
                )

            # Verificar que ambos estados existen
            valid_states = [e.value for e in EstadoDocumentoSifenEnum]

            if current_state not in valid_states:
                raise SifenValidationError(
                    f"Estado actual '{current_state}' no es válido",
                    field="current_state",
                    value=current_state
                )

            if target_state not in valid_states:
                raise SifenValidationError(
                    f"Estado objetivo '{target_state}' no es válido",
                    field="target_state",
                    value=target_state
                )

            # Verificar transición permitida
            if not can_transition_to(current_state, target_state):
                valid_next_states = get_next_valid_states(current_state)
                raise SifenDocumentStateError(
                    f"No se puede transicionar de '{current_state}' a '{target_state}'. "
                    f"Estados válidos: {', '.join(valid_next_states) if valid_next_states else 'ninguno'}",
                    document_id=documento_id or "unknown",
                    current_state=current_state,
                    required_state=target_state
                )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_estado_transition", duration, 1)

            log_repository_operation(
                "validate_estado_transition",
                "Documento",
                documento_id,
                {
                    "current_state": current_state,
                    "target_state": target_state,
                    "transition_valid": True
                }
            )

        except (SifenValidationError, SifenDocumentStateError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "validate_estado_transition", "Documento")
            raise handle_database_exception(e, "validate_estado_transition")

    def can_be_modified(self, documento: Documento) -> bool:
        """
        Verifica si un documento puede ser modificado.

        Args:
            documento: Documento a verificar

        Returns:
            bool: True si puede ser modificado

        Example:
            >>> if mixin.can_be_modified(documento):
            ...     # Proceder con modificación
            ... else:
            ...     raise SifenDocumentStateError("Documento no puede ser modificado")
        """
        if not documento:
            return False

        estado_actual = getattr(documento, 'estado', '')

        # Verificar estado editable
        can_edit = is_editable_state(estado_actual)

        # Log de operación
        log_repository_operation(
            "can_be_modified",
            "Documento",
            getattr(documento, 'id', None),
            {
                "estado": estado_actual,
                "can_modify": can_edit
            }
        )

        return can_edit

    def can_be_sent(self, documento: Documento) -> bool:
        """
        Verifica si un documento puede ser enviado a SIFEN.

        Args:
            documento: Documento a verificar

        Returns:
            bool: True si puede ser enviado

        Example:
            >>> if mixin.can_be_sent(documento):
            ...     # Proceder con envío
            ... else:
            ...     raise SifenDocumentStateError("Documento no puede ser enviado")
        """
        if not documento:
            return False

        estado_actual = getattr(documento, 'estado', '')

        # Debe estar firmado
        if estado_actual != EstadoDocumentoSifenEnum.FIRMADO.value:
            return False

        # Debe tener CDC
        if not getattr(documento, 'cdc', None):
            return False

        # Debe tener XML firmado
        if not getattr(documento, 'xml_firmado', None):
            return False

        # Debe estar dentro del límite de tiempo
        fecha_emision = getattr(documento, 'fecha_emision', None)
        if not fecha_emision or not is_within_sifen_time_limit(fecha_emision):
            return False

        # Verificar vigencia del timbrado
        if not self._is_timbrado_vigente(documento):
            return False

        can_send = True

        # Log de operación
        log_repository_operation(
            "can_be_sent",
            "Documento",
            getattr(documento, 'id', None),
            {
                "estado": estado_actual,
                "has_cdc": bool(getattr(documento, 'cdc', None)),
                "has_xml_firmado": bool(getattr(documento, 'xml_firmado', None)),
                "timbrado_vigente": self._is_timbrado_vigente(documento),
                "can_send": can_send
            }
        )

        return can_send

    def can_be_cancelled(self, documento: Documento) -> bool:
        """
        Verifica si un documento puede ser cancelado.

        Args:
            documento: Documento a verificar

        Returns:
            bool: True si puede ser cancelado

        Example:
            >>> if mixin.can_be_cancelled(documento):
            ...     # Proceder con cancelación
            ... else:
            ...     raise SifenDocumentStateError("Documento no puede ser cancelado")
        """
        if not documento:
            return False

        estado_actual = getattr(documento, 'estado', '')

        # No se pueden cancelar documentos en estados finales
        if is_final_state(estado_actual):
            return False

        # No se pueden cancelar documentos ya enviados a SIFEN
        if estado_actual == EstadoDocumentoSifenEnum.ENVIADO.value:
            return False

        # Verificar si es un documento aprobado (requiere anulación, no cancelación)
        if estado_actual in [EstadoDocumentoSifenEnum.APROBADO.value,
                             EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value]:
            return False

        can_cancel = True

        # Log de operación
        log_repository_operation(
            "can_be_cancelled",
            "Documento",
            getattr(documento, 'id', None),
            {
                "estado": estado_actual,
                "is_final": is_final_state(estado_actual),
                "can_cancel": can_cancel
            }
        )

        return can_cancel

    # ===============================================
    # VALIDACIONES DE CONTENIDO
    # ===============================================

    def validate_document_data(self,
                               document_data: Dict[str, Any],
                               documento_id: Optional[int] = None) -> None:
        """
        Valida los datos de un documento según reglas específicas.

        Args:
            document_data: Datos del documento a validar
            documento_id: ID del documento (para logs)

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio

        Example:
            >>> mixin.validate_document_data({
            ...     "tipo_documento": "1",
            ...     "total_general": Decimal("1100000"),
            ...     "fecha_emision": date.today(),
            ...     "empresa_id": 1,
            ...     "cliente_id": 456
            ... })
        """
        start_time = datetime.now()

        try:
            # Validar campos requeridos básicos
            required_fields = [
                "tipo_documento", "establecimiento", "punto_expedicion",
                "numero_documento", "numero_timbrado", "fecha_emision",
                "empresa_id", "cliente_id", "total_general"
            ]

            for field in required_fields:
                if field not in document_data or document_data[field] is None:
                    raise SifenValidationError(
                        f"Campo requerido: {field}",
                        field=field
                    )

            # Validar tipo de documento
            tipo_documento = document_data["tipo_documento"]
            if tipo_documento not in [e.value for e in TipoDocumentoSifenEnum]:
                raise SifenValidationError(
                    f"Tipo de documento '{tipo_documento}' no es válido",
                    field="tipo_documento",
                    value=tipo_documento
                )

            # Validaciones específicas por tipo de documento
            self._validate_by_document_type(document_data)

            # Validar fechas
            self.validate_dates(document_data)

            # Validar montos
            self.validate_amounts(document_data)

            # Validar requisitos SIFEN
            self.validate_sifen_requirements(document_data)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_document_data", duration, 1)

            log_repository_operation(
                "validate_document_data",
                "Documento",
                documento_id,
                {
                    "tipo_documento": tipo_documento,
                    "validation_passed": True,
                    "has_amounts": "total_general" in document_data,
                    "has_dates": "fecha_emision" in document_data
                }
            )

        except (SifenValidationError, SifenBusinessLogicError):
            raise
        except Exception as e:
            handle_repository_error(e, "validate_document_data", "Documento")
            raise handle_database_exception(e, "validate_document_data")

    def validate_amounts(self, document_data: Dict[str, Any]) -> None:
        """
        Valida consistencia de montos y cálculos.

        Args:
            document_data: Datos del documento con montos a validar

        Raises:
            SifenValidationError: Si los montos no son válidos
            SifenBusinessLogicError: Si hay inconsistencias en cálculos

        Example:
            >>> mixin.validate_amounts({
            ...     "total_general": Decimal("1100000"),
            ...     "total_operacion": Decimal("1000000"),
            ...     "total_iva": Decimal("100000"),
            ...     "subtotal_gravado_10": Decimal("1000000")
            ... })
        """
        start_time = datetime.now()

        try:
            # Validar monto total requerido
            if "total_general" not in document_data:
                raise SifenValidationError(
                    "Total general es requerido",
                    field="total_general"
                )

            total_general = document_data["total_general"]

            # Convertir a Decimal si es necesario
            if isinstance(total_general, str):
                total_general = Decimal(total_general)
            elif isinstance(total_general, (int, float)):
                total_general = Decimal(str(total_general))

            # Validar rango de monto
            if total_general < MIN_DOCUMENT_AMOUNT or total_general > MAX_DOCUMENT_AMOUNT:
                raise SifenValidationError(
                    f"Total general debe estar entre {MIN_DOCUMENT_AMOUNT} y {MAX_DOCUMENT_AMOUNT}",
                    field="total_general",
                    value=total_general
                )

            # Validar precisión decimal
            if not validate_amount_precision(total_general):
                raise SifenValidationError(
                    "Total general no puede tener más de 4 decimales",
                    field="total_general",
                    value=total_general
                )

            # Validar montos individuales si se proporcionan
            amount_fields = [
                "total_operacion", "total_iva", "subtotal_exento",
                "subtotal_exonerado", "subtotal_gravado_5", "subtotal_gravado_10"
            ]

            for field in amount_fields:
                if field in document_data and document_data[field] is not None:
                    amount = document_data[field]

                    # Convertir a Decimal
                    if isinstance(amount, str):
                        amount = Decimal(amount)
                    elif isinstance(amount, (int, float)):
                        amount = Decimal(str(amount))

                    # Validar que no sea negativo
                    if amount < 0:
                        raise SifenValidationError(
                            f"{field} no puede ser negativo",
                            field=field,
                            value=amount
                        )

                    # Validar precisión
                    if not validate_amount_precision(amount):
                        raise SifenValidationError(
                            f"{field} no puede tener más de 4 decimales",
                            field=field,
                            value=amount
                        )

            # Validar consistencia de cálculos si se proporcionan todos los campos
            self._validate_amount_calculations(document_data)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_amounts", duration, 1)

            log_repository_operation(
                "validate_amounts",
                "Documento",
                None,
                {
                    "total_general": float(total_general),
                    "validation_passed": True,
                    "fields_validated": len([f for f in amount_fields if f in document_data])
                }
            )

        except (SifenValidationError, SifenBusinessLogicError):
            raise
        except Exception as e:
            handle_repository_error(e, "validate_amounts", "Documento")
            raise handle_database_exception(e, "validate_amounts")

    def validate_dates(self, document_data: Dict[str, Any]) -> None:
        """
        Valida fechas y vigencias del documento.

        Args:
            document_data: Datos del documento con fechas a validar

        Raises:
            SifenValidationError: Si las fechas no son válidas
            SifenTimbradoError: Si hay problemas con vigencia del timbrado

        Example:
            >>> mixin.validate_dates({
            ...     "fecha_emision": date.today(),
            ...     "fecha_inicio_vigencia_timbrado": date(2025, 1, 1),
            ...     "fecha_fin_vigencia_timbrado": date(2025, 12, 31)
            ... })
        """
        start_time = datetime.now()

        try:
            # Validar fecha de emisión
            if "fecha_emision" not in document_data:
                raise SifenValidationError(
                    "Fecha de emisión es requerida",
                    field="fecha_emision"
                )

            fecha_emision = document_data["fecha_emision"]

            # Convertir string a date si es necesario
            if isinstance(fecha_emision, str):
                try:
                    fecha_emision = datetime.strptime(
                        fecha_emision, "%Y-%m-%d").date()
                    document_data["fecha_emision"] = fecha_emision
                except ValueError:
                    raise SifenValidationError(
                        "Formato de fecha de emisión inválido. Use YYYY-MM-DD",
                        field="fecha_emision",
                        value=fecha_emision
                    )

            # Validar que la fecha no sea futura
            if fecha_emision > date.today():
                raise SifenValidationError(
                    "La fecha de emisión no puede ser futura",
                    field="fecha_emision",
                    value=fecha_emision
                )

            # Validar que la fecha no sea muy antigua (más de 1 año)
            fecha_limite = date.today() - timedelta(days=365)
            if fecha_emision < fecha_limite:
                raise SifenValidationError(
                    "La fecha de emisión no puede ser anterior a un año",
                    field="fecha_emision",
                    value=fecha_emision
                )

            # Validar vigencia del timbrado si se proporciona
            if all(k in document_data for k in ["fecha_inicio_vigencia_timbrado", "fecha_fin_vigencia_timbrado"]):
                self._validate_timbrado_dates(document_data)

            # Validar límite de tiempo para envío a SIFEN
            if not is_within_sifen_time_limit(fecha_emision, SIFEN_SUBMISSION_LIMIT_HOURS):
                # Solo warning, no error crítico
                logger.warning(
                    f"Documento con fecha {fecha_emision} está cerca o fuera del límite de 72 horas para envío a SIFEN"
                )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_dates", duration, 1)

            log_repository_operation(
                "validate_dates",
                "Documento",
                None,
                {
                    "fecha_emision": fecha_emision.isoformat(),
                    "validation_passed": True,
                    "within_sifen_limit": is_within_sifen_time_limit(fecha_emision)
                }
            )

        except (SifenValidationError, SifenTimbradoError):
            raise
        except Exception as e:
            handle_repository_error(e, "validate_dates", "Documento")
            raise handle_database_exception(e, "validate_dates")

    def validate_sifen_requirements(self, document_data: Dict[str, Any]) -> None:
        """
        Valida requisitos específicos de SIFEN.

        Args:
            document_data: Datos del documento a validar

        Raises:
            SifenValidationError: Si no cumple requisitos SIFEN
            SifenBusinessLogicError: Si hay errores de lógica de negocio

        Example:
            >>> mixin.validate_sifen_requirements({
            ...     "tipo_documento": "1",
            ...     "moneda": "PYG",
            ...     "tipo_operacion": "1",
            ...     "condicion_operacion": "1"
            ... })
        """
        start_time = datetime.now()

        try:
            # Validar moneda
            if "moneda" in document_data:
                moneda = document_data["moneda"]
                if moneda not in [e.value for e in MonedaSifenEnum]:
                    raise SifenValidationError(
                        f"Moneda '{moneda}' no es válida para SIFEN",
                        field="moneda",
                        value=moneda
                    )

            # Validar tipo de operación
            if "tipo_operacion" in document_data:
                tipo_operacion = document_data["tipo_operacion"]
                if tipo_operacion not in [e.value for e in TipoOperacionSifenEnum]:
                    raise SifenValidationError(
                        f"Tipo de operación '{tipo_operacion}' no es válido",
                        field="tipo_operacion",
                        value=tipo_operacion
                    )

            # Validar condición de operación
            if "condicion_operacion" in document_data:
                condicion = document_data["condicion_operacion"]
                if condicion not in [e.value for e in CondicionOperacionSifenEnum]:
                    raise SifenValidationError(
                        f"Condición de operación '{condicion}' no es válida",
                        field="condicion_operacion",
                        value=condicion
                    )

            # Validar limitaciones de caracteres
            self._validate_text_field_limits(document_data)

            # Validar requisitos específicos por tipo de documento
            tipo_documento = document_data.get("tipo_documento", "")
            if tipo_documento in DOCUMENT_TYPES_REQUIRING_ORIGINAL:
                self._validate_original_document_requirements(document_data)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_sifen_requirements", duration, 1)

            log_repository_operation(
                "validate_sifen_requirements",
                "Documento",
                None,
                {
                    "tipo_documento": tipo_documento,
                    "validation_passed": True,
                    "has_moneda": "moneda" in document_data,
                    "has_tipo_operacion": "tipo_operacion" in document_data
                }
            )

        except (SifenValidationError, SifenBusinessLogicError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "validate_sifen_requirements", "Documento")
            raise handle_database_exception(e, "validate_sifen_requirements")

    # ===============================================
    # VALIDACIONES DE NEGOCIO
    # ===============================================

    def validate_timbrado_vigency(self,
                                  numero_timbrado: str,
                                  fecha_emision: date,
                                  fecha_inicio: date,
                                  fecha_fin: date) -> None:
        """
        Valida vigencia del timbrado para la fecha de emisión.

        Args:
            numero_timbrado: Número de timbrado
            fecha_emision: Fecha de emisión del documento
            fecha_inicio: Fecha inicio vigencia timbrado
            fecha_fin: Fecha fin vigencia timbrado

        Raises:
            SifenTimbradoError: Si el timbrado no está vigente
            SifenValidationError: Si las fechas no son válidas

        Example:
            >>> mixin.validate_timbrado_vigency(
            ...     "12345678",
            ...     date(2025, 6, 15),
            ...     date(2025, 1, 1),
            ...     date(2025, 12, 31)
            ... )
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if not all([numero_timbrado, fecha_emision, fecha_inicio, fecha_fin]):
                raise SifenValidationError(
                    "Todos los parámetros son requeridos para validar vigencia de timbrado",
                    field="timbrado"
                )

            # Validar que fecha_fin >= fecha_inicio
            if fecha_fin < fecha_inicio:
                raise SifenValidationError(
                    "Fecha fin de vigencia debe ser mayor o igual a fecha inicio",
                    field="fecha_fin_vigencia_timbrado",
                    value=fecha_fin
                )

            # Validar vigencia
            if not (fecha_inicio <= fecha_emision <= fecha_fin):
                raise SifenTimbradoError(
                    timbrado=numero_timbrado,
                    reason=f"Timbrado no está vigente para la fecha {fecha_emision}. Vigencia: {fecha_inicio} a {fecha_fin}",
                    fecha_emision=fecha_emision,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                )

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_timbrado_vigency", duration, 1)

            log_repository_operation(
                "validate_timbrado_vigency",
                "Documento",
                None,
                {
                    "numero_timbrado": numero_timbrado,
                    "fecha_emision": fecha_emision.isoformat(),
                    "vigencia_valida": True,
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": fecha_fin.isoformat()
                }
            )

        except (SifenTimbradoError, SifenValidationError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "validate_timbrado_vigency", "Documento")
            raise handle_database_exception(e, "validate_timbrado_vigency")

    def validate_client_requirements(self,
                                     cliente_id: int,
                                     tipo_documento: str) -> None:
        """
        Valida requisitos específicos del cliente.

        Args:
            cliente_id: ID del cliente
            tipo_documento: Tipo de documento

        Raises:
            SifenValidationError: Si el cliente no cumple requisitos
            SifenEntityNotFoundError: Si el cliente no existe

        Example:
            >>> mixin.validate_client_requirements(456, "1")
        """
        start_time = datetime.now()

        try:
            # Validar que el cliente existe
            # Nota: Aquí se haría una consulta a la tabla de clientes
            # Por ahora solo validamos que el ID sea válido
            if not cliente_id or cliente_id <= 0:
                raise SifenValidationError(
                    "ID de cliente debe ser mayor a 0",
                    field="cliente_id",
                    value=cliente_id
                )

            # TODO: Implementar validaciones específicas del cliente
            # - Verificar que el cliente esté activo
            # - Verificar documentos requeridos según tipo de operación
            # - Verificar límites de crédito si aplica

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_client_requirements", duration, 1)

            log_repository_operation(
                "validate_client_requirements",
                "Documento",
                None,
                {
                    "cliente_id": cliente_id,
                    "tipo_documento": tipo_documento,
                    "validation_passed": True
                }
            )

        except (SifenValidationError, SifenEntityNotFoundError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "validate_client_requirements", "Documento")
            raise handle_database_exception(e, "validate_client_requirements")

    def validate_company_permissions(self,
                                     empresa_id: int,
                                     tipo_documento: str,
                                     operation: str = "create") -> None:
        """
        Valida permisos de la empresa para la operación.

        Args:
            empresa_id: ID de la empresa
            tipo_documento: Tipo de documento
            operation: Tipo de operación (create, update, delete)

        Raises:
            SifenValidationError: Si la empresa no tiene permisos
            SifenEntityNotFoundError: Si la empresa no existe

        Example:
            >>> mixin.validate_company_permissions(1, "1", "create")
        """
        start_time = datetime.now()

        try:
            # Validar que la empresa existe
            if not empresa_id or empresa_id <= 0:
                raise SifenValidationError(
                    "ID de empresa debe ser mayor a 0",
                    field="empresa_id",
                    value=empresa_id
                )

            # TODO: Implementar validaciones específicas de la empresa
            # - Verificar que la empresa esté activa
            # - Verificar permisos para el tipo de documento
            # - Verificar certificados digitales válidos
            # - Verificar configuración SIFEN

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_company_permissions", duration, 1)

            log_repository_operation(
                "validate_company_permissions",
                "Documento",
                None,
                {
                    "empresa_id": empresa_id,
                    "tipo_documento": tipo_documento,
                    "operation": operation,
                    "validation_passed": True
                }
            )

        except (SifenValidationError, SifenEntityNotFoundError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "validate_company_permissions", "Documento")
            raise handle_database_exception(e, "validate_company_permissions")

    # ===============================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ===============================================

    def _validate_by_document_type(self, document_data: Dict[str, Any]) -> None:
        """
        Valida datos específicos según el tipo de documento.

        Args:
            document_data: Datos del documento

        Raises:
            SifenValidationError: Si hay errores específicos del tipo
        """
        tipo_documento = document_data.get("tipo_documento", "")

        if tipo_documento == TipoDocumentoSifenEnum.FACTURA.value:
            # Validaciones específicas para facturas
            self._validate_factura_data(document_data)

        elif tipo_documento == TipoDocumentoSifenEnum.NOTA_CREDITO.value:
            # Validaciones específicas para notas de crédito
            self._validate_nota_credito_data(document_data)

        elif tipo_documento == TipoDocumentoSifenEnum.NOTA_DEBITO.value:
            # Validaciones específicas para notas de débito
            self._validate_nota_debito_data(document_data)

        elif tipo_documento == TipoDocumentoSifenEnum.NOTA_REMISION.value:
            # Validaciones específicas para notas de remisión
            self._validate_nota_remision_data(document_data)

        elif tipo_documento == TipoDocumentoSifenEnum.AUTOFACTURA.value:
            # Validaciones específicas para autofacturas
            self._validate_autofactura_data(document_data)

    def _validate_factura_data(self, document_data: Dict[str, Any]) -> None:
        """Valida datos específicos de facturas."""
        # Facturas deben tener monto mayor a 0
        total_general = document_data.get("total_general", 0)
        if isinstance(total_general, (str, int, float)):
            total_general = Decimal(str(total_general))

        if total_general <= 0:
            raise SifenValidationError(
                "Las facturas deben tener un monto mayor a 0",
                field="total_general",
                value=total_general
            )

    def _validate_nota_credito_data(self, document_data: Dict[str, Any]) -> None:
        """Valida datos específicos de notas de crédito."""
        # Notas de crédito requieren referencia al documento original
        if "documento_original_cdc" not in document_data:
            raise SifenValidationError(
                "Notas de crédito requieren CDC del documento original",
                field="documento_original_cdc"
            )

        # Validar que el monto no exceda el documento original
        # TODO: Implementar validación contra documento original

    def _validate_nota_debito_data(self, document_data: Dict[str, Any]) -> None:
        """Valida datos específicos de notas de débito."""
        # Notas de débito requieren referencia al documento original
        if "documento_original_cdc" not in document_data:
            raise SifenValidationError(
                "Notas de débito requieren CDC del documento original",
                field="documento_original_cdc"
            )

    def _validate_nota_remision_data(self, document_data: Dict[str, Any]) -> None:
        """Valida datos específicos de notas de remisión."""
        # Notas de remisión deben tener monto 0
        total_general = document_data.get("total_general", 0)
        if isinstance(total_general, (str, int, float)):
            total_general = Decimal(str(total_general))

        if total_general != 0:
            raise SifenValidationError(
                "Las notas de remisión deben tener monto 0",
                field="total_general",
                value=total_general
            )

    def _validate_autofactura_data(self, document_data: Dict[str, Any]) -> None:
        """Valida datos específicos de autofacturas."""
        # Autofacturas generalmente para importaciones
        tipo_operacion = document_data.get("tipo_operacion", "")
        if tipo_operacion not in OPERATION_TYPES_REQUIRING_IMPORT_DATA:
            logger.warning(
                f"Autofactura con tipo de operación {tipo_operacion} - "
                "generalmente se usan para importaciones (tipo 3)"
            )

    def _validate_amount_calculations(self, document_data: Dict[str, Any]) -> None:
        """
        Valida consistencia de cálculos de montos.

        Args:
            document_data: Datos con montos a validar

        Raises:
            SifenBusinessLogicError: Si hay inconsistencias
        """
        # Obtener montos con valores por defecto
        total_general = self._get_decimal_value(
            document_data, "total_general", Decimal("0"))
        total_operacion = self._get_decimal_value(
            document_data, "total_operacion", Decimal("0"))
        total_iva = self._get_decimal_value(
            document_data, "total_iva", Decimal("0"))

        subtotal_exento = self._get_decimal_value(
            document_data, "subtotal_exento", Decimal("0"))
        subtotal_exonerado = self._get_decimal_value(
            document_data, "subtotal_exonerado", Decimal("0"))
        subtotal_5 = self._get_decimal_value(
            document_data, "subtotal_gravado_5", Decimal("0"))
        subtotal_10 = self._get_decimal_value(
            document_data, "subtotal_gravado_10", Decimal("0"))

        # Validar que total_operacion = suma de subtotales
        if total_operacion > 0:
            suma_subtotales = subtotal_exento + subtotal_exonerado + subtotal_5 + subtotal_10
            if abs(total_operacion - suma_subtotales) > Decimal("0.01"):
                raise SifenBusinessLogicError(
                    f"Total operación ({total_operacion}) no coincide con suma de subtotales ({suma_subtotales})",
                    details={
                        "total_operacion": float(total_operacion),
                        "suma_subtotales": float(suma_subtotales),
                        "diferencia": float(abs(total_operacion - suma_subtotales))
                    }
                )

        # Validar que total_general = total_operacion + total_iva
        if total_operacion > 0 and total_iva >= 0:
            expected_total = total_operacion + total_iva
            if abs(total_general - expected_total) > Decimal("0.01"):
                raise SifenBusinessLogicError(
                    f"Total general ({total_general}) no coincide con total operación + IVA ({expected_total})",
                    details={
                        "total_general": float(total_general),
                        "total_operacion": float(total_operacion),
                        "total_iva": float(total_iva),
                        "expected_total": float(expected_total)
                    }
                )

    def _validate_timbrado_dates(self, document_data: Dict[str, Any]) -> None:
        """
        Valida fechas de vigencia del timbrado.

        Args:
            document_data: Datos con fechas de timbrado

        Raises:
            SifenTimbradoError: Si las fechas del timbrado no son válidas
        """
        fecha_emision = document_data.get("fecha_emision")
        fecha_inicio = document_data.get("fecha_inicio_vigencia_timbrado")
        fecha_fin = document_data.get("fecha_fin_vigencia_timbrado")
        numero_timbrado = document_data.get("numero_timbrado", "")

        if all([fecha_emision, fecha_inicio, fecha_fin]):
            # Type assertions para Pylance
            assert fecha_emision is not None
            assert fecha_inicio is not None
            assert fecha_fin is not None

            self.validate_timbrado_vigency(
                numero_timbrado,
                fecha_emision,
                fecha_inicio,
                fecha_fin
            )

    def _validate_text_field_limits(self, document_data: Dict[str, Any]) -> None:
        """
        Valida límites de caracteres en campos de texto.

        Args:
            document_data: Datos con campos de texto

        Raises:
            SifenValidationError: Si algún campo excede el límite
        """
        text_limits = {
            "descripcion_operacion": MAX_LENGTH_DESCRIPCION,
            "observaciones": MAX_LENGTH_OBSERVACIONES,
            "motivo_emision": MAX_LENGTH_MOTIVO,
            "motivo_credito": MAX_LENGTH_MOTIVO,
            "motivo_debito": MAX_LENGTH_MOTIVO,
            "motivo_traslado": MAX_LENGTH_MOTIVO
        }

        for field, max_length in text_limits.items():
            if field in document_data and document_data[field]:
                text_value = str(document_data[field])
                if len(text_value) > max_length:
                    raise SifenValidationError(
                        f"{field} no puede exceder {max_length} caracteres",
                        field=field,
                        value=len(text_value)
                    )

    def _validate_original_document_requirements(self, document_data: Dict[str, Any]) -> None:
        """
        Valida requisitos para documentos que requieren documento original.

        Args:
            document_data: Datos del documento

        Raises:
            SifenValidationError: Si faltan requisitos
        """
        tipo_documento = document_data.get("tipo_documento", "")

        if tipo_documento == TipoDocumentoSifenEnum.NOTA_CREDITO.value:
            if "documento_original_cdc" not in document_data:
                raise SifenValidationError(
                    "Notas de crédito requieren CDC del documento original",
                    field="documento_original_cdc"
                )

            if "motivo_credito" not in document_data:
                raise SifenValidationError(
                    "Notas de crédito requieren motivo específico",
                    field="motivo_credito"
                )

        elif tipo_documento == TipoDocumentoSifenEnum.NOTA_DEBITO.value:
            if "documento_original_cdc" not in document_data:
                raise SifenValidationError(
                    "Notas de débito requieren CDC del documento original",
                    field="documento_original_cdc"
                )

            if "motivo_debito" not in document_data:
                raise SifenValidationError(
                    "Notas de débito requieren motivo específico",
                    field="motivo_debito"
                )

    def _get_decimal_value(self,
                           data: Dict[str, Any],
                           field: str,
                           default: Decimal) -> Decimal:
        """
        Obtiene valor decimal de un campo con manejo de tipos.

        Args:
            data: Diccionario de datos
            field: Nombre del campo
            default: Valor por defecto

        Returns:
            Decimal: Valor convertido a Decimal
        """
        value = data.get(field, default)

        if value is None:
            return default

        if isinstance(value, Decimal):
            return value
        elif isinstance(value, str):
            try:
                return Decimal(value)
            except (ValueError, TypeError):
                return default
        elif isinstance(value, (int, float)):
            return Decimal(str(value))
        else:
            return default

    def _is_timbrado_vigente(self, documento: Documento) -> bool:
        """
        Verifica si el timbrado del documento está vigente.

        Args:
            documento: Documento a verificar

        Returns:
            bool: True si el timbrado está vigente
        """
        if not documento:
            return False

        fecha_emision = getattr(documento, 'fecha_emision', None)
        fecha_inicio = getattr(
            documento, 'fecha_inicio_vigencia_timbrado', None)
        fecha_fin = getattr(documento, 'fecha_fin_vigencia_timbrado', None)

        if not all([fecha_emision, fecha_inicio, fecha_fin]):
            return False

        return fecha_inicio <= fecha_emision <= fecha_fin  # type: ignore

    def _log_validation_result(self,
                               operation: str,
                               success: bool,
                               details: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra el resultado de una validación.

        Args:
            operation: Nombre de la operación de validación
            success: Si la validación fue exitosa
            details: Detalles adicionales
        """
        log_data = {
            "operation": operation,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }

        if details:
            log_data.update(details)

        if success:
            logger.info(f"Validación exitosa: {operation}", extra=log_data)
        else:
            logger.warning(f"Validación fallida: {operation}", extra=log_data)

    # ===============================================
    # MÉTODOS DE VALIDACIÓN BATCH
    # ===============================================

    def validate_multiple_documents(self,
                                    documents_data: List[Dict[str, Any]],
                                    stop_on_first_error: bool = True) -> List[Dict[str, Any]]:
        """
        Valida múltiples documentos en lote.

        Args:
            documents_data: Lista de datos de documentos
            stop_on_first_error: Si detener en el primer error

        Returns:
            List[Dict]: Lista de resultados de validación

        Raises:
            SifenValidationError: Si stop_on_first_error=True y hay error

        Example:
            >>> results = mixin.validate_multiple_documents([
            ...     {"tipo_documento": "1", "total_general": 1000000, ...},
            ...     {"tipo_documento": "5", "total_general": 500000, ...}
            ... ])
        """
        start_time = datetime.now()
        results = []

        try:
            for i, document_data in enumerate(documents_data):
                result = {
                    "index": i,
                    "valid": False,
                    "errors": [],
                    "warnings": []
                }

                try:
                    # Validar documento individual
                    self.validate_document_data(document_data)
                    result["valid"] = True

                except (SifenValidationError, SifenBusinessLogicError) as e:
                    result["errors"].append({
                        "type": type(e).__name__,
                        "message": str(e),
                        "field": getattr(e, 'field', None),
                        "value": getattr(e, 'value', None)
                    })

                    if stop_on_first_error:
                        raise

                except Exception as e:
                    result["errors"].append({
                        "type": "UnexpectedError",
                        "message": str(e)
                    })

                    if stop_on_first_error:
                        raise handle_database_exception(
                            e, "validate_multiple_documents")

                results.append(result)

            # Estadísticas del lote
            valid_count = sum(1 for r in results if r["valid"])
            error_count = len(results) - valid_count

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "validate_multiple_documents", duration, len(documents_data))

            log_repository_operation(
                "validate_multiple_documents",
                "Documento",
                None,
                {
                    "total_documents": len(documents_data),
                    "valid_documents": valid_count,
                    "error_documents": error_count,
                    "success_rate": (valid_count / len(documents_data)) * 100 if documents_data else 0
                }
            )

            return results

        except Exception as e:
            handle_repository_error(
                e, "validate_multiple_documents", "Documento")
            raise

    def validate_document_consistency(self,
                                      documento_id: int,
                                      check_references: bool = True) -> Dict[str, Any]:
        """
        Valida consistencia completa de un documento existente.

        Args:
            documento_id: ID del documento a validar
            check_references: Si verificar referencias a otros documentos

        Returns:
            Dict: Resultado completo de la validación

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenDatabaseError: Si hay error en consultas

        Example:
            >>> result = mixin.validate_document_consistency(123)
            >>> if not result["valid"]:
            ...     print(f"Errores: {result['errors']}")
        """
        start_time = datetime.now()

        try:
            # Obtener documento
            documento = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento:
                raise SifenEntityNotFoundError("Documento", documento_id)

            result = {
                "documento_id": documento_id,
                "valid": True,
                "errors": [],
                "warnings": [],
                "checks": {
                    "basic_data": False,
                    "amounts": False,
                    "dates": False,
                    "state": False,
                    "uniqueness": False,
                    "references": False
                }
            }

            # Convertir documento a dict para validaciones
            document_data = {
                "tipo_documento": getattr(documento, 'tipo_documento', ''),
                "establecimiento": getattr(documento, 'establecimiento', ''),
                "punto_expedicion": getattr(documento, 'punto_expedicion', ''),
                "numero_documento": getattr(documento, 'numero_documento', ''),
                "numero_timbrado": getattr(documento, 'numero_timbrado', ''),
                "fecha_emision": getattr(documento, 'fecha_emision', None),
                "fecha_inicio_vigencia_timbrado": getattr(documento, 'fecha_inicio_vigencia_timbrado', None),
                "fecha_fin_vigencia_timbrado": getattr(documento, 'fecha_fin_vigencia_timbrado', None),
                "empresa_id": getattr(documento, 'empresa_id', None),
                "cliente_id": getattr(documento, 'cliente_id', None),
                "total_general": getattr(documento, 'total_general', Decimal("0")),
                "total_operacion": getattr(documento, 'total_operacion', Decimal("0")),
                "total_iva": getattr(documento, 'total_iva', Decimal("0")),
                "cdc": getattr(documento, 'cdc', None),
                "estado": getattr(documento, 'estado', '')
            }

            # Validar datos básicos
            try:
                self.validate_document_data(document_data, documento_id)
                result["checks"]["basic_data"] = True
            except Exception as e:
                result["valid"] = False
                result["errors"].append({
                    "check": "basic_data",
                    "message": str(e)
                })

            # Validar montos
            try:
                self.validate_amounts(document_data)
                result["checks"]["amounts"] = True
            except Exception as e:
                result["valid"] = False
                result["errors"].append({
                    "check": "amounts",
                    "message": str(e)
                })

            # Validar fechas
            try:
                self.validate_dates(document_data)
                result["checks"]["dates"] = True
            except Exception as e:
                result["valid"] = False
                result["errors"].append({
                    "check": "dates",
                    "message": str(e)
                })

            # Validar estado
            try:
                estado = getattr(documento, 'estado', '')
                if estado not in [e.value for e in EstadoDocumentoSifenEnum]:
                    raise SifenValidationError(
                        f"Estado '{estado}' no es válido")
                result["checks"]["state"] = True
            except Exception as e:
                result["valid"] = False
                result["errors"].append({
                    "check": "state",
                    "message": str(e)
                })

            # Validar unicidad
            try:
                self.validate_unique_constraints(document_data, documento_id)
                result["checks"]["uniqueness"] = True
            except Exception as e:
                result["valid"] = False
                result["errors"].append({
                    "check": "uniqueness",
                    "message": str(e)
                })

            # Validar referencias (si se solicita)
            if check_references:
                try:
                    self._validate_document_references(documento, result)
                    result["checks"]["references"] = True
                except Exception as e:
                    result["valid"] = False
                    result["errors"].append({
                        "check": "references",
                        "message": str(e)
                    })

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "validate_document_consistency", duration, 1)

            log_repository_operation(
                "validate_document_consistency",
                "Documento",
                documento_id,
                {
                    "valid": result["valid"],
                    "errors_count": len(result["errors"]),
                    "warnings_count": len(result["warnings"]),
                    "checks_passed": sum(1 for check in result["checks"].values() if check)
                }
            )

            return result

        except SifenEntityNotFoundError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "validate_document_consistency", "Documento")
            raise handle_database_exception(e, "validate_document_consistency")

    def _validate_document_references(self,
                                      documento: Documento,
                                      result: Dict[str, Any]) -> None:
        """
        Valida referencias a otros documentos.

        Args:
            documento: Documento a validar
            result: Resultado de validación donde añadir warnings/errors
        """
        tipo_documento = getattr(documento, 'tipo_documento', '')

        # Validar referencias para notas de crédito/débito
        if tipo_documento in ["5", "6"]:  # NCE, NDE
            documento_original_cdc = getattr(
                documento, 'documento_original_cdc', None)

            if not documento_original_cdc:
                result["warnings"].append({
                    "check": "references",
                    "message": f"Documento tipo {tipo_documento} debería tener CDC del documento original"
                })
            else:
                # Verificar que el documento original existe
                original_exists = self.db.query(self.model).filter(
                    text("cdc = :cdc")
                ).params(cdc=documento_original_cdc).first()

                if not original_exists:
                    result["warnings"].append({
                        "check": "references",
                        "message": f"Documento original con CDC {documento_original_cdc} no encontrado"
                    })

    # ===============================================
    # MÉTODOS DE VALIDACIÓN AVANZADA
    # ===============================================

    def validate_business_rules(self,
                                document_data: Dict[str, Any],
                                context: Optional[Dict[str, Any]] = None) -> None:
        """
        Valida reglas de negocio avanzadas.

        Args:
            document_data: Datos del documento
            context: Contexto adicional (usuario, empresa, etc.)

        Raises:
            SifenBusinessLogicError: Si hay violaciones de reglas de negocio

        Example:
            >>> mixin.validate_business_rules(
            ...     document_data,
            ...     context={"user_id": 123, "empresa_config": {...}}
            ... )
        """
        start_time = datetime.now()

        try:
            # Validar límites de montos por tipo de documento
            self._validate_amount_limits(document_data)

            # Validar restricciones temporales
            self._validate_temporal_restrictions(document_data)

            # Validar coherencia de datos comerciales
            self._validate_commercial_coherence(document_data)

            # Validar restricciones específicas del contexto
            if context:
                self._validate_context_restrictions(document_data, context)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("validate_business_rules", duration, 1)

            log_repository_operation(
                "validate_business_rules",
                "Documento",
                None,
                {
                    "validation_passed": True,
                    "has_context": bool(context),
                    "tipo_documento": document_data.get("tipo_documento", "")
                }
            )

        except SifenBusinessLogicError:
            raise
        except Exception as e:
            handle_repository_error(e, "validate_business_rules", "Documento")
            raise handle_database_exception(e, "validate_business_rules")

    def _validate_amount_limits(self, document_data: Dict[str, Any]) -> None:
        """Valida límites de montos según reglas de negocio."""
        total_general = self._get_decimal_value(
            document_data, "total_general", Decimal("0"))
        tipo_documento = document_data.get("tipo_documento", "")

        # Límites específicos por tipo de documento
        limits = {
            "1": {"min": Decimal("1"), "max": Decimal("999999999")},  # Factura
            "5": {"min": Decimal("1"), "max": Decimal("999999999")},  # NCE
            "6": {"min": Decimal("1"), "max": Decimal("999999999")},  # NDE
            "7": {"min": Decimal("0"), "max": Decimal("0")},          # NRE
            "4": {"min": Decimal("1"), "max": Decimal("999999999")}   # AFE
        }

        if tipo_documento in limits:
            limit = limits[tipo_documento]
            if total_general < limit["min"] or total_general > limit["max"]:
                raise SifenBusinessLogicError(
                    f"Monto {total_general} fuera del rango permitido para tipo {tipo_documento} "
                    f"(min: {limit['min']}, max: {limit['max']})"
                )

    def _validate_temporal_restrictions(self, document_data: Dict[str, Any]) -> None:
        """Valida restricciones temporales del documento."""
        fecha_emision = document_data.get("fecha_emision")

        if fecha_emision:
            # No permitir documentos de fines de semana para ciertos tipos
            # (ejemplo de regla de negocio específica)
            if fecha_emision.weekday() >= 5:  # Sábado = 5, Domingo = 6
                tipo_documento = document_data.get("tipo_documento", "")
                if tipo_documento in ["4"]:  # Autofacturas
                    logger.warning(
                        f"Documento tipo {tipo_documento} emitido en fin de semana: {fecha_emision}"
                    )

    def _validate_commercial_coherence(self, document_data: Dict[str, Any]) -> None:
        """Valida coherencia de datos comerciales."""
        tipo_operacion = document_data.get("tipo_operacion", "")
        condicion_operacion = document_data.get("condicion_operacion", "")
        moneda = document_data.get("moneda", "PYG")

        # Validar coherencia entre tipo y condición de operación
        if tipo_operacion == "2" and moneda == "PYG":  # Exportación en guaraníes
            logger.warning(
                "Exportación en guaraníes - verificar si es correcto"
            )

        # Validar plazos de crédito
        if condicion_operacion == "2":  # Crédito
            # Aquí se podrían validar plazos, límites de crédito, etc.
            pass

    def _validate_context_restrictions(self,
                                       document_data: Dict[str, Any],
                                       context: Dict[str, Any]) -> None:
        """Valida restricciones específicas del contexto."""
        # Validaciones basadas en usuario, empresa, configuración, etc.
        user_id = context.get("user_id")
        empresa_config = context.get("empresa_config", {})

        # Ejemplo: Validar límites por usuario
        if user_id and "max_document_amount" in empresa_config:
            max_amount = Decimal(str(empresa_config["max_document_amount"]))
            total_general = self._get_decimal_value(
                document_data, "total_general", Decimal("0"))

            if total_general > max_amount:
                raise SifenBusinessLogicError(
                    f"Monto {total_general} excede el límite del usuario ({max_amount})"
                )

    # ===============================================
    # MÉTODOS DE UTILIDAD FINAL
    # ===============================================

    def get_validation_summary(self, documento_id: int) -> Dict[str, Any]:
        """
        Obtiene resumen completo de validación de un documento.

        Args:
            documento_id: ID del documento

        Returns:
            Dict: Resumen de validación

        Example:
            >>> summary = mixin.get_validation_summary(123)
            >>> print(f"Estado: {summary['status']}")
            >>> print(f"Puede enviarse: {summary['can_be_sent']}")
        """
        try:
            documento = self.db.query(self.model).filter(
                self.model.id == documento_id
            ).first()

            if not documento:
                return {
                    "documento_id": documento_id,
                    "status": "not_found",
                    "error": "Documento no encontrado"
                }

            # Obtener validaciones
            consistency_result = self.validate_document_consistency(
                documento_id, check_references=True)

            # Obtener capacidades
            can_modify = self.can_be_modified(documento)
            can_send = self.can_be_sent(documento)
            can_cancel = self.can_be_cancelled(documento)

            return {
                "documento_id": documento_id,
                "status": "valid" if consistency_result["valid"] else "invalid",
                "consistency": consistency_result,
                "capabilities": {
                    "can_be_modified": can_modify,
                    "can_be_sent": can_send,
                    "can_be_cancelled": can_cancel
                },
                "document_info": {
                    "tipo_documento": getattr(documento, 'tipo_documento', ''),
                    "numero_completo": getattr(documento, 'numero_completo', ''),
                    "estado": getattr(documento, 'estado', ''),
                    "fecha_emision": getattr(documento, 'fecha_emision', None),
                    "total_general": float(getattr(documento, 'total_general', 0))
                }
            }

        except Exception as e:
            return {
                "documento_id": documento_id,
                "status": "error",
                "error": str(e)
            }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "DocumentoValidationMixin",

    # Constantes
    "DOCUMENT_TYPES_REQUIRING_ORIGINAL",
    "OPERATION_TYPES_REQUIRING_EXPORT_DATA",
    "OPERATION_TYPES_REQUIRING_IMPORT_DATA",
    "MIN_DOCUMENT_AMOUNT",
    "MAX_DOCUMENT_AMOUNT",
    "SIFEN_SUBMISSION_LIMIT_HOURS",
    "MAX_LENGTH_DESCRIPCION",
    "MAX_LENGTH_OBSERVACIONES",
    "MAX_LENGTH_MOTIVO"
]
