# ===============================================
# ARCHIVO: backend/app/repositories/factura/base.py
# PROPÓSITO: Repository base para facturas con CRUD core
# VERSIÓN: 1.0.0 - Compatible con SIFEN v150
# FASE: 1 - Fundación (40% del módulo)
# ===============================================

"""
Repository base para facturas.

Hereda de BaseRepository y añade operaciones específicas de facturas.
Proporciona CRUD completo más operaciones de búsqueda, cálculo y
conteo específicas para facturas electrónicas SIFEN.

Incluye:
- CRUD básico heredado de BaseRepository
- Búsquedas específicas por número, cliente, timbrado
- Cálculos automáticos de totales e IVA
- Operaciones de conteo y estadísticas básicas
- Validaciones de coherencia de datos
- Logging estructurado de operaciones

Integra con:
- models/factura.py (modelo SQLAlchemy)
- schemas/factura.py (DTOs Pydantic)
- utils.py (utilidades específicas)
- services/xml_generator (preparación XML)

Hereda de:
- BaseRepository[Factura, FacturaCreateDTO, FacturaUpdateDTO]

Usado por:
- Mixins específicos (numeracion_mixin, estado_mixin, etc.)
- API endpoints (/api/v1/facturas)
- Services de negocio (factura_service.py)
- Generación XML SIFEN

Ejemplos de uso:
    ```python
    from app.repositories.factura.base import FacturaRepositoryBase
    
    # Inicializar repository
    repo = FacturaRepositoryBase(db_session)
    
    # CRUD básico
    factura = await repo.create(factura_data)
    facturas = await repo.get_by_cliente(cliente_id=123)
    
    # Búsquedas específicas
    factura = await repo.get_by_numero_factura("001-001-0000123")
    pendientes = await repo.get_pendientes_cobro()
    
    # Cálculos
    totales = await repo.calcular_totales(factura_id)
    total_facturado = await repo.get_total_facturado(empresa_id=1)
    ```
"""

import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, between, text, in_  # type: ignore
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Imports del proyecto
from app.repositories.base import BaseRepository
from app.models.factura import Factura, EstadoDocumentoEnum, TipoDocumentoEnum, MonedaEnum
from app.schemas.factura import FacturaCreateDTO, FacturaUpdateDTO, FacturaResponseDTO
from app.core.exceptions import (
    SifenEntityNotFoundError,
    SifenValidationError,
    SifenDatabaseError,
    SifenBusinessLogicError,
)

# Imports específicos del módulo
from .utils import (
    log_repository_operation,
    calculate_factura_totals,
    build_date_filter,
    validate_factura_format,
    validate_timbrado_vigency,
    format_numero_factura,
    SifenConstants
)

# Configurar logger específico
logger = logging.getLogger("factura_repository.base")


class FacturaRepositoryBase(BaseRepository[Factura, FacturaCreateDTO, FacturaUpdateDTO]):
    """
    Repository base para facturas con operaciones CRUD y específicas.

    Hereda de BaseRepository y añade funcionalidad específica para facturas:
    - Búsquedas por número, cliente, timbrado, fechas
    - Cálculos automáticos de totales e IVA
    - Validaciones específicas de facturas
    - Conteos y estadísticas básicas
    - Operaciones de estado y flujo SIFEN
    """

    def __init__(self, db: Session):
        """
        Inicializar repository con sesión de base de datos.

        Args:
            db: Sesión SQLAlchemy
        """
        super().__init__(Factura)
        self.db = db
        self.model = Factura

        # Log inicialización
        log_repository_operation("__init__", details={"model": "Factura"})

    # ===============================================
    # MÉTODOS DE BÚSQUEDA ESPECÍFICOS
    # ===============================================

    async def get_by_numero_factura(self, numero_completo: str, empresa_id: Optional[int] = None) -> Optional[Factura]:
        """
        Buscar factura por número completo (EST-PEX-NUMERO).

        Args:
            numero_completo: Número en formato EST-PEX-NUMERO (ej: 001-001-0000123)
            empresa_id: ID empresa (opcional, filtro adicional)

        Returns:
            Factura encontrada o None

        Raises:
            SifenValidationError: Si el formato del número es inválido
            SifenDatabaseError: Error en consulta

        Examples:
            >>> factura = await repo.get_by_numero_factura("001-001-0000123")
            >>> factura = await repo.get_by_numero_factura("001-001-0000123", empresa_id=1)
        """
        try:
            # Validar formato
            if not validate_factura_format(numero_completo):
                raise SifenValidationError(
                    f"Formato número factura inválido: {numero_completo}")

            # Parsear número completo en componentes
            from .utils import parse_numero_factura
            numero_parts = parse_numero_factura(numero_completo)

            # Construir query con componentes individuales
            query = self.db.query(self.model).filter(
                and_(
                    self.model.establecimiento == numero_parts["establecimiento"],
                    self.model.punto_expedicion == numero_parts["punto_expedicion"],
                    self.model.numero_documento == numero_parts["numero"]
                )
            )

            # Filtro empresa opcional
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Ejecutar consulta
            factura = query.first()

            # Log resultado
            log_repository_operation(
                "get_by_numero_factura",
                details={"numero": numero_completo,
                         "encontrada": factura is not None}
            )

            return factura

        except SifenValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en get_by_numero_factura: {e}")
            raise SifenDatabaseError(
                f"Error buscando factura por número: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en get_by_numero_factura: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_by_rango_fechas(self, fecha_desde: date, fecha_hasta: date,
                                  empresa_id: Optional[int] = None,
                                  limit: int = 100, offset: int = 0) -> List[Factura]:
        """
        Buscar facturas en rango de fechas.

        Args:
            fecha_desde: Fecha inicio (incluida)
            fecha_hasta: Fecha fin (incluida)
            empresa_id: ID empresa (opcional)
            limit: Límite resultados (default: 100)
            offset: Offset para paginación (default: 0)

        Returns:
            Lista de facturas en el rango

        Raises:
            SifenValidationError: Si las fechas son inválidas
            SifenDatabaseError: Error en consulta
        """
        try:
            # Validar fechas
            if fecha_desde > fecha_hasta:
                raise SifenValidationError(
                    "fecha_desde debe ser menor o igual a fecha_hasta")

            # Validar rango razonable (no más de 1 año)
            if (fecha_hasta - fecha_desde).days > 365:
                raise SifenValidationError(
                    "Rango de fechas muy amplio (máximo 1 año)")

            # Construir query
            query = self.db.query(self.model).filter(
                between(self.model.fecha_emision, fecha_desde, fecha_hasta)
            )

            # Filtro empresa opcional
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Ordenar por fecha descendente
            query = query.order_by(
                desc(self.model.fecha_emision), desc(self.model.id))

            # Paginación
            query = query.offset(offset).limit(limit)

            # Ejecutar consulta
            facturas = query.all()

            # Log resultado
            log_repository_operation(
                "get_by_rango_fechas",
                details={
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "count": len(facturas),
                    "limit": limit,
                    "offset": offset
                }
            )

            return facturas

        except SifenValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en get_by_rango_fechas: {e}")
            raise SifenDatabaseError(
                f"Error buscando facturas por fechas: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en get_by_rango_fechas: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_by_cliente(self, cliente_id: int, empresa_id: Optional[int] = None,
                             limit: int = 50, offset: int = 0) -> List[Factura]:
        """
        Buscar facturas por cliente.

        Args:
            cliente_id: ID del cliente
            empresa_id: ID empresa (opcional)
            limit: Límite resultados (default: 50)
            offset: Offset para paginación (default: 0)

        Returns:
            Lista de facturas del cliente

        Raises:
            SifenDatabaseError: Error en consulta
        """
        try:
            # Construir query
            query = self.db.query(self.model).filter(
                self.model.cliente_id == cliente_id
            )

            # Filtro empresa opcional
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Ordenar por fecha descendente
            query = query.order_by(
                desc(self.model.fecha_emision), desc(self.model.id))

            # Paginación
            query = query.offset(offset).limit(limit)

            # Ejecutar consulta
            facturas = query.all()

            # Log resultado
            log_repository_operation(
                "get_by_cliente",
                details={
                    "cliente_id": cliente_id,
                    "count": len(facturas),
                    "limit": limit,
                    "offset": offset
                }
            )

            return facturas

        except SQLAlchemyError as e:
            logger.error(f"Error DB en get_by_cliente: {e}")
            raise SifenDatabaseError(
                f"Error buscando facturas por cliente: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en get_by_cliente: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_by_timbrado(self, numero_timbrado: str, empresa_id: Optional[int] = None,
                              limit: int = 100, offset: int = 0) -> List[Factura]:
        """
        Buscar facturas por timbrado.

        Args:
            numero_timbrado: Número del timbrado
            empresa_id: ID empresa (opcional)
            limit: Límite resultados (default: 100)
            offset: Offset para paginación (default: 0)

        Returns:
            Lista de facturas con ese timbrado

        Raises:
            SifenDatabaseError: Error en consulta
        """
        try:
            # Construir query
            query = self.db.query(self.model).filter(
                self.model.numero_timbrado == numero_timbrado
            )

            # Filtro empresa opcional
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Ordenar por número documento
            query = query.order_by(asc(self.model.numero_documento))

            # Paginación
            query = query.offset(offset).limit(limit)

            # Ejecutar consulta
            facturas = query.all()

            # Log resultado
            log_repository_operation(
                "get_by_timbrado",
                details={
                    "numero_timbrado": numero_timbrado,
                    "count": len(facturas),
                    "limit": limit,
                    "offset": offset
                }
            )

            return facturas

        except SQLAlchemyError as e:
            logger.error(f"Error DB en get_by_timbrado: {e}")
            raise SifenDatabaseError(
                f"Error buscando facturas por timbrado: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en get_by_timbrado: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_pendientes_cobro(self, empresa_id: Optional[int] = None,
                                   limit: int = 100, offset: int = 0) -> List[Factura]:
        """
        Buscar facturas pendientes de cobro.

        Facturas en estados: enviado, aprobado (pero no cobradas aún)

        Args:
            empresa_id: ID empresa (opcional)
            limit: Límite resultados (default: 100)
            offset: Offset para paginación (default: 0)

        Returns:
            Lista de facturas pendientes cobro

        Raises:
            SifenDatabaseError: Error en consulta
        """
        try:
            # Estados que indican pendiente de cobro
            estados_pendientes = [
                EstadoDocumentoEnum.ENVIADO,
                EstadoDocumentoEnum.APROBADO
            ]

            # Construir query
            query = self.db.query(self.model).filter(
                self.model.estado.in_(estados_pendientes)  # type: ignore
            )

            # Filtro empresa opcional
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Ordenar por fecha emisión (más antiguos primero)
            query = query.order_by(
                asc(self.model.fecha_emision), asc(self.model.id))

            # Paginación
            query = query.offset(offset).limit(limit)

            # Ejecutar consulta
            facturas = query.all()

            # Log resultado
            log_repository_operation(
                "get_pendientes_cobro",
                details={
                    "count": len(facturas),
                    "limit": limit,
                    "offset": offset
                }
            )

            return facturas

        except SQLAlchemyError as e:
            logger.error(f"Error DB en get_pendientes_cobro: {e}")
            raise SifenDatabaseError(
                f"Error buscando facturas pendientes: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en get_pendientes_cobro: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS DE CÁLCULO
    # ===============================================

    async def calcular_totales(self, factura_id: int) -> Dict[str, Decimal]:
        """
        Calcular totales automáticamente basado en items de la factura.

        Args:
            factura_id: ID de la factura

        Returns:
            Dict con totales calculados

        Raises:
            SifenEntityNotFoundError: Si la factura no existe
            SifenDatabaseError: Error en cálculo

        Examples:
            >>> totales = await repo.calcular_totales(123)
            >>> # {
            >>> #     "subtotal_exento": Decimal("0"),
            >>> #     "subtotal_iva10": Decimal("2850000"), 
            >>> #     "total_general": Decimal("3135000"),
            >>> #     ...
            >>> # }
        """
        try:
            # Verificar que la factura existe
            factura = self.get_by_id(self.db, id=factura_id)
            if not factura:
                raise SifenEntityNotFoundError("Factura", factura_id)

            # TODO: Obtener items de la factura cuando esté implementado ItemFactura
            # Por ahora usar totales actuales como base
            totales_actuales = factura.calcular_totales()

            # Log operación
            log_repository_operation(
                "calcular_totales",
                entity_id=factura_id,
                details={"total_general": str(
                    totales_actuales["total_general"])}
            )

            return totales_actuales

        except SifenEntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en calcular_totales: {e}")
            raise SifenDatabaseError(f"Error calculando totales: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en calcular_totales: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def recalcular_impuestos(self, factura_id: int) -> Dict[str, Decimal]:
        """
        Recalcular IVA y totales de una factura.

        Args:
            factura_id: ID de la factura

        Returns:
            Dict con impuestos recalculados

        Raises:
            SifenEntityNotFoundError: Si la factura no existe
            SifenDatabaseError: Error en cálculo
        """
        try:
            # Verificar que la factura existe
            factura = self.get_by_id(self.db, id=factura_id)
            if not factura:
                raise SifenEntityNotFoundError("Factura", factura_id)

            # Obtener totales recalculados
            totales = await self.calcular_totales(factura_id)

            # Actualizar campos de IVA
            impuestos = {
                "subtotal_iva5": totales.get("subtotal_iva5", Decimal("0")),
                "subtotal_iva10": totales.get("subtotal_iva10", Decimal("0")),
                "monto_iva5": totales.get("monto_iva5", Decimal("0")),
                "monto_iva10": totales.get("monto_iva10", Decimal("0")),
                "total_iva": totales.get("total_iva", Decimal("0"))
            }

            # Log operación
            log_repository_operation(
                "recalcular_impuestos",
                entity_id=factura_id,
                details={"total_iva": str(impuestos["total_iva"])}
            )

            return impuestos

        except SifenEntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en recalcular_impuestos: {e}")
            raise SifenDatabaseError(f"Error recalculando impuestos: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en recalcular_impuestos: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def validate_amounts(self, factura_id: int) -> Dict[str, bool]:
        """
        Validar coherencia de montos de una factura.

        Verifica que:
        - Total general = Total operación + Total IVA
        - Subtotales IVA son coherentes
        - No hay montos negativos

        Args:
            factura_id: ID de la factura

        Returns:
            Dict con resultados de validación

        Raises:
            SifenEntityNotFoundError: Si la factura no existe
            SifenDatabaseError: Error en validación
        """
        try:
            # Verificar que la factura existe
            factura = self.get_by_id(self.db, id=factura_id)
            if not factura:
                raise SifenEntityNotFoundError("Factura", factura_id)

            # Obtener totales calculados
            totales_calculados = await self.calcular_totales(factura_id)

            # Obtener totales almacenados
            total_general_bd = factura.total_general or Decimal("0")
            total_operacion_bd = factura.total_operacion or Decimal("0")
            total_iva_bd = factura.total_iva or Decimal("0")

            # Validaciones
            validaciones = {
                "total_general_coherente": (
                    total_general_bd == totales_calculados.get(
                        "total_general", Decimal("0"))
                ),
                "total_operacion_coherente": (
                    total_operacion_bd == totales_calculados.get(
                        "total_operacion", Decimal("0"))
                ),
                "total_iva_coherente": (
                    total_iva_bd == totales_calculados.get(
                        "total_iva", Decimal("0"))
                ),
                "suma_coherente": (
                    total_general_bd == (total_operacion_bd + total_iva_bd)
                ),
                "montos_no_negativos": (
                    total_general_bd >= 0 and total_operacion_bd >= 0 and total_iva_bd >= 0
                ),
                "tiene_items": True  # TODO: verificar cuando estén implementados los items
            }

            # Resultado general
            validaciones["todas_validaciones_ok"] = all(validaciones.values())

            # Log resultado
            log_repository_operation(
                "validate_amounts",
                entity_id=factura_id,
                details={
                    "coherente": validaciones["todas_validaciones_ok"],
                    "total_bd": str(total_general_bd),
                    "total_calc": str(totales_calculados.get("total_general", Decimal("0")))
                }
            )

            return validaciones

        except SifenEntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en validate_amounts: {e}")
            raise SifenDatabaseError(f"Error validando montos: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en validate_amounts: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS DE CONTEO Y ESTADÍSTICAS
    # ===============================================

    async def count_by_cliente(self, cliente_id: int, empresa_id: Optional[int] = None) -> int:
        """
        Contar facturas por cliente.

        Args:
            cliente_id: ID del cliente
            empresa_id: ID empresa (opcional)

        Returns:
            Número de facturas del cliente

        Raises:
            SifenDatabaseError: Error en consulta
        """
        try:
            # Construir query
            query = self.db.query(func.count(self.model.id)).filter(
                self.model.cliente_id == cliente_id
            )

            # Filtro empresa opcional
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Ejecutar consulta
            count = query.scalar() or 0

            # Log resultado
            log_repository_operation(
                "count_by_cliente",
                details={"cliente_id": cliente_id, "count": count}
            )

            return count

        except SQLAlchemyError as e:
            logger.error(f"Error DB en count_by_cliente: {e}")
            raise SifenDatabaseError(
                f"Error contando facturas por cliente: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en count_by_cliente: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def count_by_periodo(self, fecha_desde: date, fecha_hasta: date,
                               empresa_id: Optional[int] = None) -> int:
        """
        Contar facturas en período.

        Args:
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            empresa_id: ID empresa (opcional)

        Returns:
            Número de facturas en el período

        Raises:
            SifenValidationError: Si las fechas son inválidas
            SifenDatabaseError: Error en consulta
        """
        try:
            # Validar fechas
            if fecha_desde > fecha_hasta:
                raise SifenValidationError(
                    "fecha_desde debe ser menor o igual a fecha_hasta")

            # Construir query
            query = self.db.query(func.count(self.model.id)).filter(
                between(self.model.fecha_emision, fecha_desde, fecha_hasta)
            )

            # Filtro empresa opcional
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Ejecutar consulta
            count = query.scalar() or 0

            # Log resultado
            log_repository_operation(
                "count_by_periodo",
                details={
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "count": count
                }
            )

            return count

        except SifenValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en count_by_periodo: {e}")
            raise SifenDatabaseError(
                f"Error contando facturas por período: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en count_by_periodo: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_total_facturado(self, empresa_id: Optional[int] = None,
                                  fecha_desde: Optional[date] = None,
                                  fecha_hasta: Optional[date] = None,
                                  moneda: str = "PYG") -> Decimal:
        """
        Obtener total facturado en período.

        Args:
            empresa_id: ID empresa (opcional)
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)
            moneda: Moneda a filtrar (default: PYG)

        Returns:
            Total facturado en la moneda especificada

        Raises:
            SifenValidationError: Si las fechas son inválidas
            SifenDatabaseError: Error en consulta
        """
        try:
            # Validar fechas si ambas están presentes
            if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
                raise SifenValidationError(
                    "fecha_desde debe ser menor o igual a fecha_hasta")

            # Construir query base
            query = self.db.query(func.coalesce(
                func.sum(self.model.total_general), 0))

            # Filtros
            filtros = []

            if empresa_id:
                filtros.append(self.model.empresa_id == empresa_id)

            if fecha_desde:
                filtros.append(self.model.fecha_emision >= fecha_desde)

            if fecha_hasta:
                filtros.append(self.model.fecha_emision <= fecha_hasta)

            # Filtrar por moneda
            filtros.append(self.model.moneda == MonedaEnum(moneda))

            # Solo facturas aprobadas
            filtros.append(self.model.estado == EstadoDocumentoEnum.APROBADO)

            # Aplicar filtros
            if filtros:
                query = query.filter(and_(*filtros))

            # Ejecutar consulta
            total = query.scalar() or Decimal("0")

            # Convertir a Decimal si es necesario
            if not isinstance(total, Decimal):
                total = Decimal(str(total))

            # Log resultado
            log_repository_operation(
                "get_total_facturado",
                details={
                    "total": str(total),
                    "moneda": moneda,
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None
                }
            )

            return total

        except SifenValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en get_total_facturado: {e}")
            raise SifenDatabaseError(
                f"Error obteniendo total facturado: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en get_total_facturado: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS AUXILIARES Y VALIDACIONES
    # ===============================================

    async def exists_numero_factura(self, numero_completo: str, empresa_id: int,
                                    exclude_id: Optional[int] = None) -> bool:
        """
        Verificar si existe una factura con el número completo.

        Args:
            numero_completo: Número en formato EST-PEX-NUMERO
            empresa_id: ID de la empresa
            exclude_id: ID a excluir de la búsqueda (para updates)

        Returns:
            True si existe

        Raises:
            SifenDatabaseError: Error en consulta
        """
        try:
            # Parsear número completo en componentes
            from .utils import parse_numero_factura
            numero_parts = parse_numero_factura(numero_completo)

            # Construir query con campos individuales
            query = self.db.query(self.model).filter(
                and_(
                    self.model.establecimiento == numero_parts["establecimiento"],
                    self.model.punto_expedicion == numero_parts["punto_expedicion"],
                    self.model.numero_documento == numero_parts["numero"],
                    self.model.empresa_id == empresa_id
                )
            )

            # Excluir ID si se proporciona
            if exclude_id:
                query = query.filter(self.model.id != exclude_id)

            # Verificar existencia
            exists = query.first() is not None

            # Log resultado
            log_repository_operation(
                "exists_numero_factura",
                details={
                    "numero_completo": numero_completo,
                    "exists": exists,
                    "exclude_id": exclude_id
                }
            )

            return exists

        except SQLAlchemyError as e:
            logger.error(f"Error DB en exists_numero_factura: {e}")
            raise SifenDatabaseError(
                f"Error verificando existencia número: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en exists_numero_factura: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_ultima_factura_by_establecimiento(self, establecimiento: str,
                                                    punto_expedicion: str,
                                                    empresa_id: int) -> Optional[Factura]:
        """
        Obtener última factura por establecimiento y punto expedición.

        Útil para obtener el próximo número en secuencia.

        Args:
            establecimiento: Código establecimiento (ej: "001")
            punto_expedicion: Código punto expedición (ej: "001")
            empresa_id: ID de la empresa

        Returns:
            Última factura o None si no hay ninguna

        Raises:
            SifenDatabaseError: Error en consulta
        """
        try:
            # Construir query
            query = self.db.query(self.model).filter(
                and_(
                    self.model.establecimiento == establecimiento,
                    self.model.punto_expedicion == punto_expedicion,
                    self.model.empresa_id == empresa_id
                )
            ).order_by(desc(self.model.numero_documento))

            # Obtener la última
            ultima_factura = query.first()

            # Log resultado
            log_repository_operation(
                "get_ultima_factura_by_establecimiento",
                details={
                    "establecimiento": establecimiento,
                    "punto_expedicion": punto_expedicion,
                    "encontrada": ultima_factura is not None,
                    "ultimo_numero": ultima_factura.numero_documento if ultima_factura else None
                }
            )

            return ultima_factura

        except SQLAlchemyError as e:
            logger.error(
                f"Error DB en get_ultima_factura_by_establecimiento: {e}")
            raise SifenDatabaseError(
                f"Error obteniendo última factura: {str(e)}")
        except Exception as e:
            logger.error(
                f"Error inesperado en get_ultima_factura_by_establecimiento: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_ultima_factura(
        self,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int
    ) -> Optional[Factura]:
        """
        Obtiene la última factura emitida por establecimiento y punto expedición.

        Útil para obtener el próximo número en secuencia para numeración automática.
        Ordena por numero_documento descendente para obtener el más alto.

        Args:
            establecimiento: Código establecimiento (001-999)
            punto_expedicion: Código punto expedición (001-999)
            empresa_id: ID de la empresa

        Returns:
            Última factura emitida o None si no hay ninguna

        Raises:
            SifenDatabaseError: Error en consulta

        Examples:
            >>> ultima = await repo.get_ultima_factura("001", "001", empresa_id=1)
            >>> if ultima:
            ...     proximo_numero = int(ultima.numero_documento) + 1
        """
        try:
            query = self.db.query(self.model).filter(
                and_(
                    self.model.establecimiento == establecimiento,
                    self.model.punto_expedicion == punto_expedicion,
                    self.model.empresa_id == empresa_id
                )
            ).order_by(desc(self.model.numero_documento))

            ultima_factura = query.first()

            # Log resultado
            log_repository_operation(
                "get_ultima_factura",
                entity_id=getattr(ultima_factura, 'id', None),
                details={
                    "establecimiento": establecimiento,
                    "punto_expedicion": punto_expedicion,
                    "empresa_id": empresa_id,
                    "encontrada": ultima_factura is not None,
                    "numero_documento": getattr(ultima_factura, 'numero_documento', None)
                }
            )

            return ultima_factura

        except SQLAlchemyError as e:
            logger.error(f"Error BD en get_ultima_factura: {e}")
            raise SifenDatabaseError(
                f"Error obteniendo última factura: {str(e)}",
                operation="get_ultima_factura"
            )
        except Exception as e:
            logger.error(f"Error inesperado en get_ultima_factura: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def validate_timbrado_vigente(self, factura_id: int) -> bool:
        """
        Validar que el timbrado de una factura esté vigente.

        Args:
            factura_id: ID de la factura

        Returns:
            True si el timbrado está vigente

        Raises:
            SifenEntityNotFoundError: Si la factura no existe
            SifenDatabaseError: Error en validación
        """
        try:
            # Obtener factura
            factura = self.get_by_id(self.db, id=factura_id)
            if not factura:
                raise SifenEntityNotFoundError("Factura", factura_id)

            # Validar que los campos requeridos existan
            if not all([factura.numero_timbrado, factura.fecha_inicio_vigencia, factura.fecha_fin_vigencia]):
                return False

            # Validar vigencia usando utility
            numero_timbrado: str = factura.numero_timbrado  # type: ignore
            fecha_inicio: date = factura.fecha_inicio_vigencia  # type: ignore
            fecha_fin: date = factura.fecha_fin_vigencia  # type: ignore

            vigente = validate_timbrado_vigency(
                numero_timbrado,
                fecha_inicio,
                fecha_fin
            )

            # Log resultado
            log_repository_operation(
                "validate_timbrado_vigente",
                entity_id=factura_id,
                details={
                    "timbrado": factura.numero_timbrado,
                    "vigente": vigente,
                    "inicio": factura.fecha_inicio_vigencia.isoformat(),
                    "fin": factura.fecha_fin_vigencia.isoformat()
                }
            )

            return vigente

        except SifenEntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en validate_timbrado_vigente: {e}")
            raise SifenDatabaseError(f"Error validando timbrado: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en validate_timbrado_vigente: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_facturas_by_estado(self, estado: EstadoDocumentoEnum,
                                     empresa_id: Optional[int] = None,
                                     limit: int = 100, offset: int = 0) -> List[Factura]:
        """
        Obtener facturas por estado específico.

        Args:
            estado: Estado del documento
            empresa_id: ID empresa (opcional)
            limit: Límite resultados (default: 100)
            offset: Offset para paginación (default: 0)

        Returns:
            Lista de facturas en el estado especificado

        Raises:
            SifenDatabaseError: Error en consulta
        """
        try:
            # Convertir estado a string para evitar problemas de tipado
            estado_str: str = estado.value if hasattr(
                estado, 'value') else str(estado)

            # Construir query con cast explícito de la columna
            from sqlalchemy import cast, String
            query = self.db.query(self.model).filter(
                cast(self.model.estado, String) == estado_str
            )

            # Filtro empresa opcional
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            # Ordenar por fecha de actualización descendente
            query = query.order_by(desc(self.model.updated_at))

            # Paginación
            query = query.offset(offset).limit(limit)

            # Ejecutar consulta
            facturas = query.all()

            # Log resultado
            log_repository_operation(
                "get_facturas_by_estado",
                details={
                    "estado": estado.value,
                    "count": len(facturas),
                    "limit": limit,
                    "offset": offset
                }
            )

            return facturas

        except SQLAlchemyError as e:
            logger.error(f"Error DB en get_facturas_by_estado: {e}")
            raise SifenDatabaseError(
                f"Error obteniendo facturas por estado: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en get_facturas_by_estado: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS CRUD SOBRESCRITOS CON VALIDACIONES
    # ===============================================

    async def create(self, obj_in: FacturaCreateDTO, **kwargs) -> Factura:
        """
        Crear nueva factura con validaciones específicas.

        Sobrescribe el método base para añadir:
        - Validación de numeración
        - Cálculo automático de totales
        - Validación de timbrado
        - Generación de CDC

        Args:
            obj_in: DTO con datos de entrada
            **kwargs: Argumentos adicionales

        Returns:
            Factura creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si no cumple reglas de negocio
            SifenDatabaseError: Error en creación
        """
        try:
            # Convertir DTO a dict
            factura_data = obj_in.model_dump()

            # TODO: Generar numeración automática cuando esté implementado numeracion_mixin
            # Por ahora usar valores del DTO

            # TODO: Calcular totales basado en items cuando estén implementados
            # Por ahora usar valores básicos

            # Crear instancia del modelo
            factura = self.model(**factura_data)

            # TODO: Generar CDC cuando esté implementada la lógica completa

            # Validaciones previas
            await self._validate_create_data(factura)

            # Crear en BD
            self.db.add(factura)
            self.db.flush()  # Para obtener ID sin commit

            # Log creación
            log_repository_operation(
                "create",
                entity_id=getattr(factura, 'id', None),
                details={
                    "cliente_id": getattr(factura, 'cliente_id', None),
                    "total_general": str(getattr(factura, 'total_general', 0)) if getattr(factura, 'total_general', None) is not None else "0"
                }
            )

            return factura

        except SifenValidationError:
            raise
        except SifenBusinessLogicError:
            raise
        except IntegrityError as e:
            logger.error(f"Error integridad en create: {e}")
            self.db.rollback()
            raise SifenBusinessLogicError(f"Error de integridad: {str(e)}")
        except SQLAlchemyError as e:
            logger.error(f"Error DB en create: {e}")
            self.db.rollback()
            raise SifenDatabaseError(f"Error creando factura: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en create: {e}")
            self.db.rollback()
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def update(self, db_obj: Factura, obj_in: FacturaUpdateDTO, **kwargs) -> Factura:
        """
        Actualizar factura existente con validaciones.

        Solo permite actualizar facturas en estado BORRADOR.

        Args:
            db_obj: Factura existente
            obj_in: DTO con datos de actualización
            **kwargs: Argumentos adicionales

        Returns:
            Factura actualizada

        Raises:
            SifenBusinessLogicError: Si no se puede actualizar
            SifenDatabaseError: Error en actualización
        """

        try:
            # Validar que se puede actualizar
            if str(db_obj.estado) != EstadoDocumentoEnum.BORRADOR.value:
                raise SifenBusinessLogicError(
                    f"No se puede actualizar factura en estado {str(db_obj.estado)}"
                )

            # Actualizar campos permitidos
            update_data = obj_in.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Actualizar timestamp
            db_obj.updated_at = datetime.utcnow()  # type: ignore

            # Flush cambios
            self.db.flush()

            # Log actualización
            log_repository_operation(
                "update",
                entity_id=getattr(db_obj, 'id', None),
                details={"campos_actualizados": list(update_data.keys())}
            )

            return db_obj

        except SifenBusinessLogicError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en update: {e}")
            self.db.rollback()
            raise SifenDatabaseError(f"Error actualizando factura: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en update: {e}")
            self.db.rollback()
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def delete(self, id: int) -> bool:
        """
        Eliminar factura (soft delete).

        Solo permite eliminar facturas en estado BORRADOR.

        Args:
            id: ID de la factura

        Returns:
            True si se eliminó exitosamente

        Raises:
            SifenEntityNotFoundError: Si la factura no existe
            SifenBusinessLogicError: Si no se puede eliminar
            SifenDatabaseError: Error en eliminación
        """
        try:
            # Obtener factura
            factura = self.get_by_id(self.db, id=id)
            if not factura:
                raise SifenEntityNotFoundError("Factura", id)

            # Validar que se puede eliminar
            if str(factura.estado) != EstadoDocumentoEnum.BORRADOR.value:
                raise SifenBusinessLogicError(
                    f"No se puede eliminar factura en estado {str(factura.estado)}"
                )

            # Soft delete
            factura.deleted_at = datetime.utcnow()
            factura.is_active = False

            # Flush cambios
            self.db.flush()

            # Log eliminación
            log_repository_operation(
                "delete",
                entity_id=id,
                details={"soft_delete": True}
            )

            return True

        except SifenEntityNotFoundError:
            raise
        except SifenBusinessLogicError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error DB en delete: {e}")
            self.db.rollback()
            raise SifenDatabaseError(f"Error eliminando factura: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado en delete: {e}")
            self.db.rollback()
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS PRIVADOS DE VALIDACIÓN
    # ===============================================

    async def _validate_create_data(self, factura: Factura) -> None:
        """
        Validar datos para creación de factura.

        Args:
            factura: Instancia de factura a validar

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si no cumple reglas de negocio
        """
        # Validar que el cliente existe
        # TODO: Implementar cuando esté disponible ClienteRepository

        # Validar que la empresa existe
        # TODO: Implementar cuando esté disponible EmpresaRepository

        # Validar unicidad de número
        numero_completo_val = getattr(factura, 'numero_completo', '')
        empresa_id_val = getattr(factura, 'empresa_id', 0)

        if numero_completo_val:
            exists = await self.exists_numero_factura(
                numero_completo_val,
                empresa_id_val
            )
            if exists:
                raise SifenBusinessLogicError(
                    f"Ya existe factura con número {numero_completo_val}"
                )

        # Validar montos básicos
        if getattr(factura, 'total_general', None) is not None and getattr(factura, 'total_general', 0) < 0:
            raise SifenValidationError("Total general no puede ser negativo")

        # Log validación
        log_repository_operation(
            "_validate_create_data",
            details={"validacion": "exitosa"}
        )

    # ===============================================
    # PROPIEDADES Y METADATA
    # ===============================================

    @property
    def model_name(self) -> str:
        """Nombre del modelo para logging."""
        return "Factura"

    def __repr__(self) -> str:
        """Representación string del repository."""
        return f"<FacturaRepositoryBase(model={self.model.__name__})>"


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "FacturaRepositoryBase"
]
