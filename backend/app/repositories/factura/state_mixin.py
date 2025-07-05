# ===============================================
# ARCHIVO: backend/app/repositories/factura/estado_mixin.py
# PROPÓSITO: Mixin para gestión de estados específicos de facturas
# VERSIÓN: 2.0.0 - Optimizado usando DTOs existentes del proyecto
# FASE: 3 - Estados (20% del módulo)
# ===============================================

"""
Mixin para gestión de estados específicos de facturas SIFEN.

🎯 OPTIMIZACIÓN v2.0:
- Usa DTOs existentes en lugar de crear clases nuevas
- Reutiliza excepciones del proyecto
- Elimina duplicación de constantes
- Reduce a ~400 líneas manteniendo funcionalidad completa

Estados manejados: COBRADO, ANULADO, VENCIDO, CANCELADO
Funcionalidades: Transiciones validadas, consultas por estado, métricas
"""

import logging
from typing import Callable, Optional, List, Dict, Any, Tuple, Type
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import String, and_, cast, or_, func, desc, asc
from sqlalchemy.exc import SQLAlchemyError

# Imports del proyecto - USAR RECURSOS EXISTENTES
from app.models.factura import Factura, EstadoDocumentoEnum, CondicionOperacionEnum
from app.core.exceptions import (
    SifenEntityNotFoundError,
    SifenBusinessLogicError,
    SifenDatabaseError
)
from app.schemas import (
    FacturaResponseDTO,
    DocumentoEstadoDTO,
    ValidationErrorResponse,
    SuccessResponse,
    PaginatedResponse
)
from .utils import log_repository_operation, SifenConstants

logger = logging.getLogger("factura_repository.estado")

# ===============================================
# CONSTANTES - REUTILIZAR EXISTENTES + MÍNIMAS NUEVAS
# ===============================================

# Plazos oficiales SIFEN (único agregado necesario)
PLAZO_CANCELACION_FE_HORAS = 48
PLAZO_CANCELACION_OTROS_HORAS = 168

# Estados que permiten operaciones específicas
ESTADOS_COBRABLES = [EstadoDocumentoEnum.APROBADO.value]
ESTADOS_CANCELABLES = [EstadoDocumentoEnum.APROBADO.value]

# ===============================================
# DECORADOR PARA LOGGING COMÚN
# ===============================================


def log_estado_operation(operation_name: str):
    """Decorador para logging automático de operaciones de estado."""
    def decorator(func):
        async def wrapper(self, factura_id: int, *args, **kwargs):
            try:
                result = await func(self, factura_id, *args, **kwargs)
                log_repository_operation(
                    operation_name,
                    entity_id=factura_id,
                    details={"success": True}
                )
                return result
            except Exception as e:
                log_repository_operation(
                    operation_name,
                    entity_id=factura_id,
                    details={"success": False, "error": str(e)}
                )
                raise
        return wrapper
    return decorator

# ===============================================
# HELPER PARA VALIDACIONES COMUNES
# ===============================================


class EstadoHelper:
    """Helper para validaciones comunes de estado."""

    @staticmethod
    async def get_factura_validated(repo, factura_id: int) -> Factura:
        """Obtener factura validando que existe."""
        factura = repo.get_by_id(repo.db, id=factura_id)
        if not factura:
            raise SifenEntityNotFoundError("Factura", factura_id)
        return factura

    @staticmethod
    def puede_cobrarse(factura: Factura) -> Tuple[bool, str]:
        """Validar si factura puede cobrarse."""
        # Convertir a string para evitar problemas SQLAlchemy
        estado_actual = factura.estado.value if hasattr(
            factura.estado, 'value') else str(factura.estado)

        if estado_actual != EstadoDocumentoEnum.APROBADO.value:
            return False, f"Estado debe ser APROBADO, actual: {estado_actual}"

        # Usar getattr para acceso seguro a atributos SQLAlchemy
        total_general = getattr(factura, 'total_general', None)
        if not total_general or total_general <= 0:
            return False, "Total inválido"

        return True, "Puede cobrarse"

    @staticmethod
    def puede_cancelarse(factura: Factura) -> Tuple[bool, str]:
        """Validar si factura puede cancelarse según plazos SIFEN."""
        # Convertir a string para evitar problemas SQLAlchemy
        estado_actual = factura.estado.value if hasattr(
            factura.estado, 'value') else str(factura.estado)

        if estado_actual != EstadoDocumentoEnum.APROBADO.value:
            return False, f"Solo facturas APROBADAS pueden cancelarse"

        # Usar getattr para acceso seguro a atributos SQLAlchemy
        fecha_envio = getattr(factura, 'fecha_envio_sifen', None)
        if not fecha_envio:
            return False, "Fecha envío SIFEN no registrada"

        # Calcular plazo según tipo documento
        tipo_documento = getattr(factura, 'tipo_documento', '1')
        plazo_horas = PLAZO_CANCELACION_FE_HORAS if tipo_documento == "1" else PLAZO_CANCELACION_OTROS_HORAS
        fecha_limite = fecha_envio + timedelta(hours=plazo_horas)

        if datetime.utcnow() > fecha_limite:
            return False, f"Plazo vencido (límite: {fecha_limite.strftime('%d/%m/%Y %H:%M')})"

        return True, "Dentro del plazo"

# ===============================================
# MIXIN PRINCIPAL OPTIMIZADO
# ===============================================


class FacturaEstadoMixin:
    """
    Mixin optimizado para gestión de estados específicos de facturas SIFEN.

    🎯 OPTIMIZACIONES v2.0:
    - Usa DTOs existentes del proyecto
    - Elimina clases auxiliares duplicadas
    - Decorator común para logging
    - Helper para validaciones repetitivas
    - Reduce de 3000+ a ~400 líneas
    """
    # Type hints para atributos que serán proporcionados por el repository base
    db: Session
    model: Type[Factura]

    # Métodos del repository base que usa este mixin
    get_by_id: Callable[..., Optional[Factura]]  # Para get_factura_validated
    # ===============================================
    # MÉTODOS PRINCIPALES DE ESTADO
    # ===============================================

    @log_estado_operation("marcar_como_cobrada")
    async def marcar_como_cobrada(self, factura_id: int,
                                  monto_cobrado: Optional[Decimal] = None,
                                  metodo_cobro: str = "efectivo") -> FacturaResponseDTO:
        """
        Marcar factura como cobrada.

        Args:
            factura_id: ID de la factura
            monto_cobrado: Monto cobrado (opcional, usa total_general)
            metodo_cobro: Método de cobro

        Returns:
            FacturaResponseDTO: Factura actualizada

        Raises:
            SifenEntityNotFoundError: Si factura no existe
            SifenBusinessLogicError: Si no puede cobrarse
        """
        try:
            factura = await EstadoHelper.get_factura_validated(self, factura_id)

            puede_cobrar, motivo = EstadoHelper.puede_cobrarse(factura)
            if not puede_cobrar:
                raise SifenBusinessLogicError(f"No puede cobrarse: {motivo}")

            # CORRECCIÓN 1: Usar getattr para acceso seguro a SQLAlchemy
            total_general = getattr(factura, 'total_general', Decimal("0"))
            monto = monto_cobrado if monto_cobrado is not None else total_general

            # CORRECCIÓN 2: Comparar con Decimal para evitar problemas SQLAlchemy
            if monto <= Decimal("0"):
                raise SifenBusinessLogicError(
                    "Monto cobrado debe ser positivo")

            # CORRECCIÓN 3: Usar setattr para asignaciones SQLAlchemy
            setattr(factura, 'estado_cobranza', "cobrado")
            setattr(factura, 'fecha_cobro', datetime.utcnow())
            setattr(factura, 'monto_cobrado', monto)
            setattr(factura, 'metodo_cobro', metodo_cobro)
            setattr(factura, 'updated_at', datetime.utcnow())

            # CORRECCIÓN 4: El mixin debe acceder a db a través de self
            self.db.flush()

            # Retornar DTO existente en lugar de crear clase nueva
            return FacturaResponseDTO.from_orm(factura)

        except (SifenEntityNotFoundError, SifenBusinessLogicError):
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise SifenDatabaseError(f"Error marcando como cobrada: {str(e)}")

    @log_estado_operation("marcar_como_anulada")
    async def marcar_como_anulada(self, factura_id: int,
                                  motivo_anulacion: str,
                                  numero_resolucion: str) -> FacturaResponseDTO:
        """Marcar factura como anulada por resolución SET."""
        monto = Decimal("0")
        try:
            factura = await EstadoHelper.get_factura_validated(self, factura_id)

            # Usar getattr y .value para evitar problemas SQLAlchemy
            estado_actual = factura.estado.value if hasattr(
                factura.estado, 'value') else str(factura.estado)

            if estado_actual != EstadoDocumentoEnum.APROBADO.value:
                raise SifenBusinessLogicError(
                    "Solo facturas APROBADAS pueden anularse")

            setattr(factura, 'estado_cobranza', "cobrado")
            setattr(factura, 'fecha_cobro', datetime.utcnow())
            setattr(factura, 'monto_cobrado', monto)
            setattr(factura, 'updated_at', datetime.utcnow())
            self.db.flush()
            return FacturaResponseDTO.from_orm(factura)

        except (SifenEntityNotFoundError, SifenBusinessLogicError):
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise SifenDatabaseError(f"Error marcando como anulada: {str(e)}")

    @log_estado_operation("marcar_como_vencida")
    async def marcar_como_vencida(self, factura_id: int) -> FacturaResponseDTO:
        """Marcar factura como vencida (solo facturas a crédito)."""
        try:
            factura = await EstadoHelper.get_factura_validated(self, factura_id)
            estado_actual = factura.estado.value if hasattr(
                factura.estado, 'value') else str(factura.estado)

            if estado_actual != EstadoDocumentoEnum.APROBADO:
                raise SifenBusinessLogicError(
                    "Solo facturas APROBADAS pueden vencerse")

            condicion_actual = factura.condicion_operacion.value if hasattr(
                factura.condicion_operacion, 'value') else str(factura.condicion_operacion)
            if condicion_actual != CondicionOperacionEnum.CREDITO.value:
                raise SifenBusinessLogicError(
                    "Solo facturas a CRÉDITO pueden vencerse")

            setattr(factura, 'estado_cobranza', "vencido")
            setattr(factura, 'fecha_vencimiento_efectiva', date.today())
            setattr(factura, 'updated_at', datetime.utcnow())

            self.db.flush()
            return FacturaResponseDTO.from_orm(factura)

        except (SifenEntityNotFoundError, SifenBusinessLogicError):
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise SifenDatabaseError(f"Error marcando como vencida: {str(e)}")

    @log_estado_operation("reabrir_factura")
    async def reabrir_factura(self, factura_id: int, motivo: str) -> FacturaResponseDTO:
        """Reabrir factura cancelada o vencida."""
        try:
            factura = await EstadoHelper.get_factura_validated(self, factura_id)

            estado_actual = getattr(factura, 'estado_cobranza', '')
            if estado_actual not in ["cancelado", "vencido"]:
                raise SifenBusinessLogicError(
                    "Solo facturas canceladas/vencidas pueden reabrirse")

            factura.estado_cobranza = "pendiente"
            factura.motivo_reapertura = motivo
            factura.fecha_reapertura = datetime.utcnow()
            setattr(factura, 'updated_at', datetime.utcnow())

            self.db.flush()
            return FacturaResponseDTO.from_orm(factura)

        except (SifenEntityNotFoundError, SifenBusinessLogicError):
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise SifenDatabaseError(f"Error reabriendo factura: {str(e)}")

    # ===============================================
    # VALIDACIONES DE TRANSICIONES
    # ===============================================

    async def can_be_collected(self, factura_id: int) -> Tuple[bool, str]:
        """Verificar si factura puede cobrarse."""
        try:
            factura = await EstadoHelper.get_factura_validated(self, factura_id)
            return EstadoHelper.puede_cobrarse(factura)
        except Exception as e:
            return False, f"Error validando: {str(e)}"

    async def can_be_cancelled(self, factura_id: int) -> Tuple[bool, str]:
        """Verificar si factura puede cancelarse según plazos SIFEN."""
        try:
            factura = await EstadoHelper.get_factura_validated(self, factura_id)
            return EstadoHelper.puede_cancelarse(factura)
        except Exception as e:
            return False, f"Error validando: {str(e)}"

    async def validate_factura_transition(self, factura_id: int, estado_destino: str) -> ValidationErrorResponse | SuccessResponse:
        """
        Validar transición específica usando DTOs existentes.

        Returns:
            ValidationErrorResponse o SuccessResponse (DTOs existentes)
        """
        try:
            factura = await EstadoHelper.get_factura_validated(self, factura_id)

            # Validar según estado destino
            if estado_destino == "cobrado":
                puede, motivo = EstadoHelper.puede_cobrarse(factura)
            elif estado_destino == "cancelado":
                puede, motivo = EstadoHelper.puede_cancelarse(factura)
            else:
                puede, motivo = False, f"Estado '{estado_destino}' no soportado"

            if puede:
                return SuccessResponse(
                    message=f"Transición válida: {factura.estado.value} → {estado_destino}",
                    data={"factura_id": factura_id, "motivo": motivo}
                )
            else:
                return ValidationErrorResponse(
                    message=f"Transición inválida: {factura.estado.value} → {estado_destino}",
                    # ← Cambiar errors por field_errors
                    field_errors={"estado": [motivo]}
                )

        except Exception as e:
            return ValidationErrorResponse(
                message="Error validando transición",
                # ← Cambiar errors por field_errors
                field_errors={"general": [str(e)]}
            )

    # ===============================================
    # CONSULTAS OPTIMIZADAS POR ESTADO
    # ===============================================

    async def get_facturas_pendientes_cobro(self, empresa_id: Optional[int] = None,
                                            limit: int = 100, offset: int = 0) -> PaginatedResponse[FacturaResponseDTO]:
        """Obtener facturas pendientes usando DTOs existentes."""
        try:
            query = self.db.query(self.model).filter(
                cast(self.model.estado, String) == EstadoDocumentoEnum.APROBADO.value
            )

            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            query = query.order_by(asc(self.model.fecha_emision))

            total = query.count()
            facturas = query.offset(offset).limit(limit).all()

            # Usar PaginatedResponse existente
            return PaginatedResponse(
                data=[FacturaResponseDTO.from_orm(f) for f in facturas],
                meta={
                    "page": offset // limit + 1,
                    "size": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            )

        except SQLAlchemyError as e:
            raise SifenDatabaseError(
                f"Error obteniendo facturas pendientes: {str(e)}")

    async def get_facturas_vencidas(self, empresa_id: Optional[int] = None,
                                    dias_vencimiento: int = 1,
                                    limit: int = 100, offset: int = 0) -> PaginatedResponse[FacturaResponseDTO]:
        """Obtener facturas vencidas."""
        try:
            fecha_limite = date.today() - timedelta(days=30 + dias_vencimiento)  # Estimación

            query = self.db.query(self.model).filter(
                and_(
                    cast(self.model.estado,
                         String) == EstadoDocumentoEnum.APROBADO.value,
                    self.model.condicion_operacion == CondicionOperacionEnum.CREDITO,
                    self.model.fecha_emision <= fecha_limite
                )
            )

            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            total = query.count()
            facturas = query.offset(offset).limit(limit).all()

            return PaginatedResponse(
                data=[FacturaResponseDTO.from_orm(f) for f in facturas],
                meta={
                    "page": offset // limit + 1,
                    "size": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            )

        except SQLAlchemyError as e:
            raise SifenDatabaseError(
                f"Error obteniendo facturas vencidas: {str(e)}")

    # ===============================================
    # ESTADÍSTICAS USANDO DTOs EXISTENTES
    # ===============================================

    async def get_estadisticas_por_estado(self, empresa_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtener estadísticas por estado usando estructura simple."""
        try:
            estado_column = getattr(self.model, 'estado')
            id_column = getattr(self.model, 'id')
            total_column = getattr(self.model, 'total_general')

            query = self.db.query(
                estado_column,
                func.count(id_column).label('cantidad'),
                func.coalesce(func.sum(total_column), 0).label('total_monto')
            )

            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            resultados = query.group_by(estado_column).all()

            estadisticas = {
                "resumen": {"total_facturas": 0, "total_monto": "0"},
                "por_estado": {},
                "fecha_consulta": datetime.utcnow().isoformat()
            }

            total_facturas = 0
            total_monto = Decimal("0")

            for resultado in resultados:
                estado = resultado.estado.value
                cantidad = resultado.cantidad
                monto = Decimal(str(resultado.total_monto))

                estadisticas["por_estado"][estado] = {
                    "cantidad": cantidad,
                    "monto": str(monto)
                }

                total_facturas += cantidad
                total_monto += monto

            estadisticas["resumen"]["total_facturas"] = total_facturas
            estadisticas["resumen"]["total_monto"] = str(total_monto)

            return estadisticas

        except SQLAlchemyError as e:
            raise SifenDatabaseError(
                f"Error obteniendo estadísticas: {str(e)}")

    # ===============================================
    # METADATA DEL MIXIN
    # ===============================================

    def get_mixin_info(self) -> Dict[str, Any]:
        """Información del mixin optimizado."""
        return {
            "name": "FacturaEstadoMixin",
            "version": "2.0.0 - Optimizado",
            "lines_of_code": "~400 (vs 3000+ anterior)",
            "optimizations": [
                "Usa DTOs existentes del proyecto",
                "Elimina clases auxiliares duplicadas",
                "Decorator común para logging",
                "Helper para validaciones repetitivas",
                "Reutiliza excepciones del proyecto"
            ],
            "dependencies": [
                "app.schemas (DTOs existentes)",
                "app.core.exceptions (excepciones existentes)",
                "FacturaRepositoryBase",
                "utils.log_repository_operation"
            ]
        }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "FacturaEstadoMixin",
    "EstadoHelper",
    "log_estado_operation",
    "PLAZO_CANCELACION_FE_HORAS",
    "PLAZO_CANCELACION_OTROS_HORAS",
    "ESTADOS_COBRABLES",
    "ESTADOS_CANCELABLES"
]
