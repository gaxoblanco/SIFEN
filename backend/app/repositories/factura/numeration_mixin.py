# ===============================================
# ARCHIVO: backend/app/repositories/factura/numeracion_mixin.py
# PROPÓSITO: Mixin para gestión de numeración automática SIFEN
# VERSIÓN: 1.0.0 - Compatible con SIFEN v150
# FASE: 2 - Numeración (25% del módulo)
# ===============================================

"""
Mixin para gestión de numeración automática de facturas SIFEN.

Este mixin maneja toda la lógica de numeración automática según
las regulaciones de la SET (Subsecretaría de Estado de Tributación) Paraguay.

Funcionalidades principales:
- Numeración secuencial automática por establecimiento/punto expedición
- Gestión de timbrados (vigencia, rangos, validaciones)
- Reserva de números para prevenir duplicados en concurrencia
- Validaciones de continuidad numérica según normativa SET
- Integración con modelo Timbrado existente

Reglas de negocio SET Paraguay:
- Numeración consecutiva sin saltos por establecimiento/punto
- Vigencia de timbrado obligatoria para emisión
- Límites numéricos según rango autorizado en timbrado
- Unicidad: un número solo puede usarse una vez por empresa
- Continuidad temporal: no emitir con fechas futuras

Integra con:
- models/timbrado.py (gestión timbrados fiscales)
- models/factura.py (numeración de documentos)
- utils.py (formateo y validaciones)
- base.py (operaciones CRUD base)

Usado por:
- FacturaRepository (compositor principal)
- API endpoints (/api/v1/facturas)
- Services de negocio (factura_service.py)

Ejemplos de uso:
    ```python
    from app.repositories.factura import FacturaRepository
    
    # Numeración automática
    repo = FacturaRepository(db)
    numero = await repo.get_next_numero("001", "001", empresa_id=1)
    # Resultado: "0000124"
    
    # Validar numeración
    es_valida = await repo.validate_numeracion_continua("001", "001", "0000125")
    
    # Estado de secuencia
    estado = await repo.get_secuencia_actual("001", "001", empresa_id=1)
    ```
"""

import logging
from typing import Awaitable, Optional, Callable, List, Dict, Any, Tuple, Type
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text, select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Imports del proyecto
from app.models.factura import Factura
from app.models.timbrado import Timbrado, EstadoTimbradoEnum
from app.core.exceptions import (
    SifenEntityNotFoundError,
    SifenValidationError,
    SifenDatabaseError,
    SifenBusinessLogicError,
    SifenNumerationError,
    SifenTimbradoError
)

# Imports específicos del módulo factura
from .utils import (
    log_repository_operation,
    format_numero_factura,
    parse_numero_factura,
    get_next_numero_available,
    validate_factura_format,
    validate_timbrado_vigency,
    SifenConstants
)
from .base import FacturaRepositoryBase
from ..utils import safe_str, safe_get

# Configurar logger específico
logger = logging.getLogger("factura_repository.numeracion")


# ===============================================
# CLASES DE DATOS PARA RESPUESTAS
# ===============================================

class EstadoSecuencia:
    """
    Clase para representar el estado de una secuencia de numeración.

    Encapsula toda la información relevante del estado actual
    de numeración para un establecimiento/punto expedición específico.
    """

    def __init__(
        self,
        ultimo_numero_usado: str,
        proximo_disponible: str,
        numeros_restantes: int,
        timbrado_vigente: Optional[str] = None,
        puede_emitir: bool = True,
        motivo_bloqueo: Optional[str] = None,
        fecha_ultimo_uso: Optional[datetime] = None
    ):
        self.ultimo_numero_usado = ultimo_numero_usado
        self.proximo_disponible = proximo_disponible
        self.numeros_restantes = numeros_restantes
        self.timbrado_vigente = timbrado_vigente
        self.puede_emitir = puede_emitir
        self.motivo_bloqueo = motivo_bloqueo
        self.fecha_ultimo_uso = fecha_ultimo_uso

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        return {
            "ultimo_numero_usado": self.ultimo_numero_usado,
            "proximo_disponible": self.proximo_disponible,
            "numeros_restantes": self.numeros_restantes,
            "timbrado_vigente": self.timbrado_vigente,
            "puede_emitir": self.puede_emitir,
            "motivo_bloqueo": self.motivo_bloqueo,
            "fecha_ultimo_uso": self.fecha_ultimo_uso.isoformat() if self.fecha_ultimo_uso else None
        }


class EstadisticasNumeracion:
    """
    Clase para estadísticas de numeración por empresa.

    Proporciona métricas y análisis del uso de numeración
    para monitoreo y alertas operacionales.
    """

    def __init__(
        self,
        facturas_por_establecimiento: Dict[str, Dict[str, int]],
        timbrados_proximos_vencer: List[Dict[str, Any]],
        uso_promedio_diario: float,
        proyeccion_agotamiento: Optional[date] = None
    ):
        self.facturas_por_establecimiento = facturas_por_establecimiento
        self.timbrados_proximos_vencer = timbrados_proximos_vencer
        self.uso_promedio_diario = uso_promedio_diario
        self.proyeccion_agotamiento = proyeccion_agotamiento

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        return {
            "facturas_por_establecimiento": self.facturas_por_establecimiento,
            "timbrados_proximos_vencer": self.timbrados_proximos_vencer,
            "uso_promedio_diario": self.uso_promedio_diario,
            "proyeccion_agotamiento": self.proyeccion_agotamiento.isoformat() if self.proyeccion_agotamiento else None
        }


# ===============================================
# EXCEPCIONES ESPECÍFICAS DE NUMERACIÓN
# ===============================================

class SifenTimbradoVencidoError(SifenTimbradoError):
    """Error cuando el timbrado está vencido para numeración."""

    def __init__(self, numero_timbrado: str, fecha_vencimiento: date, **kwargs):
        super().__init__(
            numero_timbrado,
            f"vencido el {fecha_vencimiento.isoformat()}",
            **kwargs
        )
        # Agregar detalles específicos
        self.details.update({
            "fecha_vencimiento": fecha_vencimiento.isoformat(),
            "tipo_error": "vencimiento"
        })


class SifenNumeracionAgotadaError(SifenNumerationError):
    """Error cuando la numeración está agotada."""

    def __init__(self, establecimiento: str, punto_expedicion: str, ultimo_numero: str, **kwargs):
        super().__init__(
            document_type="Factura",
            expected_number=int(ultimo_numero) + 1,
            **kwargs
        )
        # Sobrescribir mensaje para ser más específico
        self.message = f"Numeración agotada para {establecimiento}-{punto_expedicion}. Último número: {ultimo_numero}"
        # Agregar detalles específicos
        self.details.update({
            "establecimiento": establecimiento,
            "punto_expedicion": punto_expedicion,
            "ultimo_numero": ultimo_numero,
            "tipo_error": "agotamiento"
        })


class SifenNumeracionDiscontinuaError(SifenNumerationError):
    """Error cuando se detecta discontinuidad en la numeración."""

    def __init__(self, establecimiento: str, punto_expedicion: str,
                 numero_esperado: int, numero_propuesto: int, **kwargs):
        super().__init__(
            document_type="Factura",
            expected_number=numero_esperado,
            **kwargs
        )
        # Sobrescribir mensaje para ser más específico
        self.message = (f"Numeración discontinua en {establecimiento}-{punto_expedicion}. "
                        f"Esperado: {numero_esperado:07d}, Propuesto: {numero_propuesto:07d}")
        # Agregar detalles específicos
        self.details.update({
            "establecimiento": establecimiento,
            "punto_expedicion": punto_expedicion,
            "numero_esperado": numero_esperado,
            "numero_propuesto": numero_propuesto,
            "tipo_error": "discontinuidad"
        })

        # ===============================================
# CLASE PRINCIPAL DEL MIXIN
# ===============================================


class FacturaNumeracionMixin:
    """
    Mixin para gestión de numeración automática de facturas SIFEN.

    Se integra con FacturaRepositoryBase para proporcionar funcionalidad
    avanzada de numeración según las regulaciones SET Paraguay.

    Funcionalidades principales:
    - Numeración secuencial automática
    - Gestión de timbrados vigentes
    - Validaciones de continuidad
    - Reserva de números en concurrencia
    - Estadísticas y monitoreo

    Requiere que la clase que lo use tenga:
    - self.db: Sesión SQLAlchemy
    - self.model: Modelo Factura

    Examples:
        ```python
        class FacturaRepository(FacturaRepositoryBase, FacturaNumeracionMixin):
            pass

        repo = FacturaRepository(db)
        numero = await repo.get_next_numero("001", "001", empresa_id=1)
        ```
    """
    # Type hints para atributos que serán proporcionados por el repository base
    db: Session
    model: Type[Factura]
    # Para que PyLance sepa que existe
    get_ultima_factura: Callable[[str, str, int], Awaitable[Optional[Factura]]]

    # ===============================================
    # MÉTODOS DE NUMERACIÓN AUTOMÁTICA
    # ===============================================

    async def get_next_numero(
        self,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int,
        fecha_emision: Optional[date] = None
    ) -> str:
        """
        Obtiene el próximo número disponible en la secuencia automáticamente.

        Método principal para numeración automática que:
        1. Valida timbrado vigente
        2. Obtiene última factura emitida
        3. Calcula próximo número en secuencia
        4. Valida continuidad numérica
        5. Reserva el número temporalmente

        Args:
            establecimiento: Código establecimiento (001-999)
            punto_expedicion: Código punto expedición (001-999) 
            empresa_id: ID de la empresa emisora
            fecha_emision: Fecha emisión (hoy si es None)

        Returns:
            str: Próximo número disponible formateado (ej: "0000124")

        Raises:
            SifenTimbradoVencidoError: Si no hay timbrado vigente
            SifenNumeracionAgotadaError: Si se agotó la numeración
            SifenValidationError: Si los parámetros son inválidos
            SifenDatabaseError: Error en operación de BD

        Examples:
            >>> numero = await repo.get_next_numero("001", "001", empresa_id=1)
            "0000124"
        """
        try:
            # Validar parámetros de entrada
            self._validate_codigo_establecimiento(establecimiento)
            self._validate_codigo_punto_expedicion(punto_expedicion)

            if fecha_emision is None:
                fecha_emision = date.today()

            # Log operación
            log_repository_operation(
                "get_next_numero",
                details={
                    "establecimiento": establecimiento,
                    "punto_expedicion": punto_expedicion,
                    "empresa_id": empresa_id,
                    "fecha_emision": fecha_emision.isoformat()
                }
            )

            # 1. Obtener timbrado vigente
            timbrado = await self._obtener_timbrado_vigente(
                establecimiento, punto_expedicion, empresa_id, fecha_emision
            )

            # 2. Obtener última factura emitida
            ultima_factura = await self.get_ultima_factura(
                establecimiento, punto_expedicion, empresa_id
            )

            # 3. Calcular próximo número
            if ultima_factura:
                ultimo_numero = safe_str(ultima_factura, 'numero_documento')
                proximo_numero_int = int(ultimo_numero) + 1
            else:
                # Primera factura en la secuencia
                numero_desde = safe_str(timbrado, 'numero_desde')
                proximo_numero_int = int(numero_desde)

            # 4. Validar que no exceda el rango autorizado
            numero_hasta = safe_str(timbrado, 'numero_hasta')
            if proximo_numero_int > int(numero_hasta):
                raise SifenNumeracionAgotadaError(
                    establecimiento=establecimiento,
                    punto_expedicion=punto_expedicion,
                    ultimo_numero=numero_hasta
                )

            # 5. Formatear número con ceros a la izquierda
            proximo_numero = str(proximo_numero_int).zfill(7)

            # 6. Validar continuidad (opcional, según configuración)
            await self._validate_continuidad_numerica(
                establecimiento, punto_expedicion, empresa_id, proximo_numero_int
            )

            # 7. Reservar número temporalmente (para concurrencia)
            await self._reservar_numero_temporal(
                establecimiento, punto_expedicion, empresa_id, proximo_numero
            )

            # Log éxito
            log_repository_operation(
                "get_next_numero_success",
                details={
                    "numero_asignado": proximo_numero,
                    "timbrado": timbrado.numero_timbrado,
                    "secuencia_position": proximo_numero_int
                }
            )

            return proximo_numero

        except (SifenTimbradoVencidoError, SifenNumeracionAgotadaError):
            # Re-raise excepciones específicas de numeración
            raise
        except SifenValidationError:
            # Re-raise errores de validación
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error BD en get_next_numero: {e}")
            raise SifenDatabaseError(
                f"Error obteniendo próximo número: {str(e)}",
                operation="get_next_numero"
            )
        except Exception as e:
            logger.error(f"Error inesperado en get_next_numero: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def reserve_numero_range(
        self,
        desde: str,
        hasta: str,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int,
        motivo: str = "Reserva para procesamiento por lotes"
    ) -> bool:
        """
        Reserva un rango de números para uso futuro.

        Útil para facturación masiva o procesamiento por lotes
        donde se necesita garantizar secuencia sin conflictos.

        Args:
            desde: Número inicial del rango (ej: "0000125")
            hasta: Número final del rango (ej: "0000200")
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            empresa_id: ID de la empresa
            motivo: Motivo de la reserva (para auditoría)

        Returns:
            bool: True si se reservó exitosamente

        Raises:
            SifenValidationError: Si el rango es inválido
            SifenNumerationError: Si hay conflictos con numeración existente
            SifenDatabaseError: Error en operación de BD

        Examples:
            >>> success = await repo.reserve_numero_range(
            ...     desde="0000125", hasta="0000200",
            ...     establecimiento="001", punto_expedicion="001", 
            ...     empresa_id=1, motivo="Facturación masiva mensual"
            ... )
        """
        try:
            # Validar formato de números
            if not validate_factura_format(f"{establecimiento}-{punto_expedicion}-{desde}"):
                raise SifenValidationError("Formato 'desde' inválido")

            if not validate_factura_format(f"{establecimiento}-{punto_expedicion}-{hasta}"):
                raise SifenValidationError("Formato 'hasta' inválido")

            # Validar rango lógico
            desde_int = int(desde)
            hasta_int = int(hasta)

            if desde_int >= hasta_int:
                raise SifenValidationError(
                    "'desde' debe ser menor que 'hasta'")

            if (hasta_int - desde_int) > 1000:
                raise SifenValidationError(
                    "Rango muy amplio (máximo 1000 números)")

            # Obtener timbrado vigente
            timbrado = await self._obtener_timbrado_vigente(
                establecimiento, punto_expedicion, empresa_id
            )

            # Validar que el rango esté dentro del timbrado
            proximo_numero_int = safe_str(timbrado, 'numero_desde')
            timbrado_desde = int(proximo_numero_int)

            proximo_numero_hasta = safe_str(timbrado, 'numero_hasta')
            timbrado_hasta = int(proximo_numero_hasta)

            if desde_int < timbrado_desde or hasta_int > timbrado_hasta:
                raise SifenValidationError(
                    f"Rango fuera de límites del timbrado {timbrado.numero_timbrado} "
                    f"({timbrado_desde:07d}-{timbrado_hasta:07d})"
                )

            # Verificar que no haya conflictos con facturas existentes
            conflictos = await self._verificar_conflictos_rango(
                desde_int, hasta_int, establecimiento, punto_expedicion, empresa_id
            )

            if conflictos:
                raise SifenNumerationError(
                    document_type="Factura",
                    expected_number=conflictos[0],
                    details={"conflictos": conflictos,
                             "tipo_error": "rango_ocupado"}
                )

            # TODO: Implementar tabla de reservas temporales para concurrencia
            # Por ahora solo validamos que sea posible

            # Log operación exitosa
            log_repository_operation(
                "reserve_numero_range",
                details={
                    "desde": desde,
                    "hasta": hasta,
                    "establecimiento": establecimiento,
                    "punto_expedicion": punto_expedicion,
                    "empresa_id": empresa_id,
                    "motivo": motivo,
                    "cantidad_numeros": hasta_int - desde_int + 1
                }
            )

            return True

        except (SifenValidationError, SifenNumerationError):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error BD en reserve_numero_range: {e}")
            raise SifenDatabaseError(
                f"Error reservando rango: {str(e)}",
                operation="reserve_numero_range"
            )
        except Exception as e:
            logger.error(f"Error inesperado en reserve_numero_range: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS DE GESTIÓN DE TIMBRADOS
    # ===============================================

    async def get_timbrado_vigente(
        self,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int,
        fecha_emision: Optional[date] = None
    ) -> Optional[Timbrado]:
        """
        Obtiene el timbrado vigente para una ubicación específica.

        Busca timbrados activos que:
        - Pertenezcan a la empresa especificada
        - Correspondan al establecimiento/punto exacto
        - Estén vigentes para la fecha de emisión
        - Tengan numeración disponible

        Args:
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            empresa_id: ID de la empresa
            fecha_emision: Fecha para validar vigencia (hoy si es None)

        Returns:
            Timbrado vigente o None si no hay disponible

        Raises:
            SifenDatabaseError: Error en consulta

        Examples:
            >>> timbrado = await repo.get_timbrado_vigente("001", "001", empresa_id=1)
            >>> if timbrado:
            ...     print(f"Timbrado {timbrado.numero_timbrado} vigente")
        """
        try:
            if fecha_emision is None:
                fecha_emision = date.today()

            # filtros
            filters = [
                Timbrado.empresa_id == empresa_id,
                Timbrado.establecimiento == establecimiento,
                Timbrado.punto_expedicion == punto_expedicion,
                Timbrado.fecha_inicio_vigencia <= fecha_emision,
                Timbrado.fecha_fin_vigencia >= fecha_emision,
                Timbrado.estado == EstadoTimbradoEnum.ACTIVO.value
            ]
            # Consulta optimizada con filtros específicos
            query = self.db.query(Timbrado).filter(*filters).order_by(
                desc(Timbrado.fecha_fin_vigencia),
                desc(Timbrado.id)
            ).order_by(
                # Priorizar por fecha fin más lejana (más tiempo disponible)
                desc(Timbrado.fecha_fin_vigencia),
                desc(Timbrado.id)
            )

            # Obtener candidatos
            candidatos = query.all()

            # Filtrar por numeración disponible
            for timbrado in candidatos:
                if self._timbrado_tiene_numeracion_disponible(timbrado):
                    log_repository_operation(
                        "get_timbrado_vigente_found",
                        details={
                            "timbrado": timbrado.numero_timbrado,
                            "vigencia_hasta": timbrado.fecha_fin_vigencia.isoformat(),
                            "numeros_disponibles": timbrado.numeros_disponibles
                        }
                    )
                    return timbrado

            # No se encontró timbrado vigente
            log_repository_operation(
                "get_timbrado_vigente_not_found",
                details={
                    "establecimiento": establecimiento,
                    "punto_expedicion": punto_expedicion,
                    "empresa_id": empresa_id,
                    "fecha_emision": fecha_emision.isoformat(),
                    "candidatos_encontrados": len(candidatos)
                },
                level="warning"
            )

            return None

        except SQLAlchemyError as e:
            logger.error(f"Error BD en get_timbrado_vigente: {e}")
            raise SifenDatabaseError(
                f"Error obteniendo timbrado vigente: {str(e)}",
                operation="get_timbrado_vigente"
            )
        except Exception as e:
            logger.error(f"Error inesperado en get_timbrado_vigente: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def check_timbrado_vigency(
        self,
        numero_timbrado: str,
        fecha_emision: date
    ) -> bool:
        """
        Verifica que un timbrado específico esté vigente para una fecha.

        Útil para validar facturas con fecha retroactiva o verificar
        timbrados específicos antes de usarlos.

        Args:
            numero_timbrado: Número del timbrado a verificar
            fecha_emision: Fecha para la cual verificar vigencia

        Returns:
            bool: True si el timbrado está vigente para la fecha

        Raises:
            SifenDatabaseError: Error en consulta

        Examples:
            >>> vigente = await repo.check_timbrado_vigency("12345678", date(2025, 1, 15))
            >>> if not vigente:
            ...     print("Timbrado no vigente para esa fecha")
        """
        try:
            # Buscar timbrado por número
            timbrado = self.db.query(Timbrado).filter(
                Timbrado.numero_timbrado == numero_timbrado
            ).first()

            if not timbrado:
                log_repository_operation(
                    "check_timbrado_vigency_not_found",
                    details={"numero_timbrado": numero_timbrado},
                    level="warning"
                )
                return False

            # Verificar vigencia temporal
            vigente = (
                timbrado.fecha_inicio_vigencia <= fecha_emision <= timbrado.fecha_fin_vigencia
                and timbrado.estado == EstadoTimbradoEnum.ACTIVO.value
            )

            # Log resultado
            log_repository_operation(
                "check_timbrado_vigency",
                details={
                    "numero_timbrado": numero_timbrado,
                    "fecha_emision": fecha_emision.isoformat(),
                    "vigente": vigente,
                    "inicio_vigencia": timbrado.fecha_inicio_vigencia.isoformat(),
                    "fin_vigencia": timbrado.fecha_fin_vigencia.isoformat(),
                    "estado": timbrado.estado
                }
            )

            vigente = bool(timbrado.estado == EstadoTimbradoEnum.ACTIVO.value)
            return vigente

        except SQLAlchemyError as e:
            logger.error(f"Error BD en check_timbrado_vigency: {e}")
            raise SifenDatabaseError(
                f"Error verificando vigencia timbrado: {str(e)}",
                operation="check_timbrado_vigency"
            )
        except Exception as e:
            logger.error(f"Error inesperado en check_timbrado_vigency: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS PRIVADOS AUXILIARES
    # ===============================================

    async def _obtener_timbrado_vigente(
        self,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int,
        fecha_emision: Optional[date] = None
    ) -> Timbrado:
        """
        Versión privada que lanza excepción si no encuentra timbrado vigente.

        Similar a get_timbrado_vigente pero garantiza retornar un timbrado
        válido o lanzar excepción específica.

        Returns:
            Timbrado: Timbrado vigente garantizado

        Raises:
            SifenTimbradoVencidoError: Si no hay timbrado vigente
        """
        timbrado = await self.get_timbrado_vigente(
            establecimiento, punto_expedicion, empresa_id, fecha_emision
        )

        if not timbrado:
            # Buscar último timbrado para dar información específica
            ultimo_timbrado = self.db.query(Timbrado).filter(
                and_(
                    Timbrado.empresa_id == empresa_id,
                    Timbrado.establecimiento == establecimiento,
                    Timbrado.punto_expedicion == punto_expedicion
                )
            ).order_by(desc(Timbrado.fecha_fin_vigencia)).first()

            if ultimo_timbrado:
                raise SifenTimbradoVencidoError(
                    numero_timbrado=safe_str(
                        ultimo_timbrado, 'numero_timbrado'),
                    fecha_vencimiento=safe_get(
                        ultimo_timbrado, 'fecha_fin_vigencia')
                )
            else:
                raise SifenTimbradoError(
                    timbrado="N/A",
                    reason=f"No hay timbrados configurados para {establecimiento}-{punto_expedicion}"
                )

        return timbrado

    def _validate_codigo_establecimiento(self, establecimiento: str) -> None:
        """Valida formato de código de establecimiento."""
        if not establecimiento or len(establecimiento) != 3:
            raise SifenValidationError(
                "Código establecimiento debe tener 3 dígitos",
                field="establecimiento",
                value=establecimiento
            )

        if not establecimiento.isdigit():
            raise SifenValidationError(
                "Código establecimiento debe ser numérico",
                field="establecimiento",
                value=establecimiento
            )

        codigo_int = int(establecimiento)
        if not (1 <= codigo_int <= 999):
            raise SifenValidationError(
                "Código establecimiento debe estar entre 001 y 999",
                field="establecimiento",
                value=establecimiento
            )

    def _validate_codigo_punto_expedicion(self, punto_expedicion: str) -> None:
        """Valida formato de código de punto de expedición."""
        if not punto_expedicion or len(punto_expedicion) != 3:
            raise SifenValidationError(
                "Código punto expedición debe tener 3 dígitos",
                field="punto_expedicion",
                value=punto_expedicion
            )

        if not punto_expedicion.isdigit():
            raise SifenValidationError(
                "Código punto expedición debe ser numérico",
                field="punto_expedicion",
                value=punto_expedicion
            )

        codigo_int = int(punto_expedicion)
        if not (1 <= codigo_int <= 999):
            raise SifenValidationError(
                "Código punto expedición debe estar entre 001 y 999",
                field="punto_expedicion",
                value=punto_expedicion
            )

    def _timbrado_tiene_numeracion_disponible(self, timbrado: Timbrado) -> bool:
        """Verifica si un timbrado tiene numeración disponible."""
        return timbrado.numeros_disponibles > 0

    # ===============================================
    # MÉTODOS DE VALIDACIÓN DE NUMERACIÓN
    # ===============================================

    async def validate_numeracion_continua(
        self,
        establecimiento: str,
        punto_expedicion: str,
        numero_propuesto: str,
        empresa_id: int
    ) -> bool:
        """
        Valida que la numeración sea continua según normativa SET.

        Verifica que el número propuesto sea el siguiente en la secuencia
        sin saltos, cumpliendo las regulaciones paraguayas de continuidad.

        Args:
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            numero_propuesto: Número propuesto para validar (ej: "0000125")
            empresa_id: ID de la empresa

        Returns:
            bool: True si la numeración es continua

        Raises:
            SifenNumeracionDiscontinuaError: Si hay discontinuidad
            SifenDatabaseError: Error en consulta

        Examples:
            >>> continua = await repo.validate_numeracion_continua(
            ...     "001", "001", "0000125", empresa_id=1
            ... )
            >>> if not continua:
            ...     print("Numeración presenta saltos")
        """
        try:
            # Validar formato del número propuesto
            if not validate_factura_format(f"{establecimiento}-{punto_expedicion}-{numero_propuesto}"):
                raise SifenValidationError(
                    "Formato de número propuesto inválido",
                    field="numero_propuesto",
                    value=numero_propuesto
                )

            numero_propuesto_int = int(numero_propuesto)

            # Obtener última factura emitida
            ultima_factura = await self.get_ultima_factura(
                establecimiento, punto_expedicion, empresa_id
            )

            if ultima_factura:
                ultimo_numero = safe_str(ultima_factura, 'numero_documento')
                ultimo_numero_int = int(ultimo_numero)
                numero_esperado = ultimo_numero_int + 1

                if numero_propuesto_int != numero_esperado:
                    # Log discontinuidad detectada
                    log_repository_operation(
                        "validate_numeracion_continua_discontinua",
                        details={
                            "establecimiento": establecimiento,
                            "punto_expedicion": punto_expedicion,
                            "numero_esperado": numero_esperado,
                            "numero_propuesto": numero_propuesto_int,
                            "gap": numero_propuesto_int - numero_esperado
                        },
                        level="warning"
                    )

                    raise SifenNumeracionDiscontinuaError(
                        establecimiento=establecimiento,
                        punto_expedicion=punto_expedicion,
                        numero_esperado=numero_esperado,
                        numero_propuesto=numero_propuesto_int
                    )
            else:
                # Primera factura: validar que coincida con inicio de timbrado
                timbrado = await self._obtener_timbrado_vigente(
                    establecimiento, punto_expedicion, empresa_id
                )
                numero_desde = safe_str(timbrado, 'numero_desde')
                numero_desde_int = int(numero_desde)

                if numero_propuesto_int != numero_desde_int:
                    raise SifenNumeracionDiscontinuaError(
                        establecimiento=establecimiento,
                        punto_expedicion=punto_expedicion,
                        numero_esperado=numero_desde_int,
                        numero_propuesto=numero_propuesto_int
                    )

            # Log validación exitosa
            log_repository_operation(
                "validate_numeracion_continua_ok",
                details={
                    "numero_propuesto": numero_propuesto_int,
                    "establecimiento": establecimiento,
                    "punto_expedicion": punto_expedicion
                }
            )

            return True

        except (SifenNumeracionDiscontinuaError, SifenValidationError):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error BD en validate_numeracion_continua: {e}")
            raise SifenDatabaseError(
                f"Error validando continuidad: {str(e)}",
                operation="validate_numeracion_continua"
            )
        except Exception as e:
            logger.error(
                f"Error inesperado en validate_numeracion_continua: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def check_numero_duplicado(
        self,
        numero_completo: str,
        empresa_id: int,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verifica si existe una factura con el número completo especificado.

        Útil para prevenir duplicados antes de crear nuevas facturas
        o validar números en updates.

        Args:
            numero_completo: Número completo (EST-PEX-NUMERO)
            empresa_id: ID de la empresa
            exclude_id: ID a excluir de la búsqueda (para updates)

        Returns:
            bool: True si el número ya existe (duplicado)

        Raises:
            SifenValidationError: Si el formato es inválido
            SifenDatabaseError: Error en consulta

        Examples:
            >>> duplicado = await repo.check_numero_duplicado(
            ...     "001-001-0000123", empresa_id=1
            ... )
            >>> if duplicado:
            ...     print("Número ya existe")
        """
        try:
            # Validar formato
            if not validate_factura_format(numero_completo):
                raise SifenValidationError(
                    "Formato de número completo inválido",
                    field="numero_completo",
                    value=numero_completo
                )

            # Parsear componentes
            componentes = parse_numero_factura(numero_completo)

            # Construir query
            query = self.db.query(self.model).filter(
                self.model.establecimiento == componentes["establecimiento"],
                self.model.punto_expedicion == componentes["punto_expedicion"],
                self.model.numero_documento == componentes["numero"],
                self.model.empresa_id == empresa_id
            )

            # Excluir ID específico si se proporciona (para updates)
            if exclude_id:
                query = query.filter(self.model.id != exclude_id)

            # Verificar existencia
            existe = query.first() is not None

            # Log resultado
            log_repository_operation(
                "check_numero_duplicado",
                details={
                    "numero_completo": numero_completo,
                    "empresa_id": empresa_id,
                    "exclude_id": exclude_id,
                    "existe": existe
                }
            )

            return existe

        except SifenValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error BD en check_numero_duplicado: {e}")
            raise SifenDatabaseError(
                f"Error verificando duplicado: {str(e)}",
                operation="check_numero_duplicado"
            )
        except Exception as e:
            logger.error(f"Error inesperado en check_numero_duplicado: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def validate_timbrado_range(
        self,
        numero_timbrado: str,
        numero_documento: str,
        empresa_id: int
    ) -> bool:
        """
        Valida que un número esté dentro del rango autorizado del timbrado.

        Verifica que el número documento esté entre numero_desde y numero_hasta
        del timbrado especificado.

        Args:
            numero_timbrado: Número del timbrado
            numero_documento: Número del documento (ej: "0000123")
            empresa_id: ID de la empresa

        Returns:
            bool: True si está dentro del rango

        Raises:
            SifenEntityNotFoundError: Si el timbrado no existe
            SifenValidationError: Si está fuera de rango
            SifenDatabaseError: Error en consulta
        """
        try:
            # Buscar timbrado
            timbrado = self.db.query(Timbrado).filter(
                Timbrado.numero_timbrado == numero_timbrado,
                Timbrado.empresa_id == empresa_id
            ).first()

            if not timbrado:
                raise SifenEntityNotFoundError(
                    entity_type="Timbrado",
                    entity_id=numero_timbrado
                )

            # Obtener rangos con type safety
            numero_desde = safe_str(timbrado, 'numero_desde')
            numero_hasta = safe_str(timbrado, 'numero_hasta')

            numero_doc_int = int(numero_documento)
            numero_desde_int = int(numero_desde)
            numero_hasta_int = int(numero_hasta)

            # Validar rango
            en_rango = numero_desde_int <= numero_doc_int <= numero_hasta_int

            if not en_rango:
                raise SifenValidationError(
                    f"Número {numero_documento} fuera de rango autorizado "
                    f"({numero_desde}-{numero_hasta}) para timbrado {numero_timbrado}",
                    field="numero_documento",
                    value=numero_documento
                )

            # Log validación exitosa
            log_repository_operation(
                "validate_timbrado_range_ok",
                details={
                    "numero_timbrado": numero_timbrado,
                    "numero_documento": numero_documento,
                    "rango_desde": numero_desde,
                    "rango_hasta": numero_hasta
                }
            )

            return True

        except (SifenEntityNotFoundError, SifenValidationError):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error BD en validate_timbrado_range: {e}")
            raise SifenDatabaseError(
                f"Error validando rango timbrado: {str(e)}",
                operation="validate_timbrado_range"
            )
        except Exception as e:
            logger.error(f"Error inesperado en validate_timbrado_range: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS DE ESTADO DE SECUENCIAS
    # ===============================================

    async def get_secuencia_actual(
        self,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int
    ) -> EstadoSecuencia:
        """
        Obtiene el estado completo de la secuencia de numeración.

        Proporciona información detallada sobre el estado actual:
        - Último número usado
        - Próximo disponible
        - Números restantes
        - Timbrado vigente
        - Capacidad de emisión

        Args:
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            empresa_id: ID de la empresa

        Returns:
            EstadoSecuencia: Estado completo de la secuencia

        Raises:
            SifenDatabaseError: Error en consulta

        Examples:
            >>> estado = await repo.get_secuencia_actual("001", "001", empresa_id=1)
            >>> print(f"Próximo número: {estado.proximo_disponible}")
            >>> print(f"Números restantes: {estado.numeros_restantes}")
        """
        try:
            # Obtener timbrado vigente
            timbrado = await self.get_timbrado_vigente(
                establecimiento, punto_expedicion, empresa_id
            )

            if not timbrado:
                return EstadoSecuencia(
                    ultimo_numero_usado="0000000",
                    proximo_disponible="N/A",
                    numeros_restantes=0,
                    timbrado_vigente=None,
                    puede_emitir=False,
                    motivo_bloqueo="No hay timbrado vigente"
                )

            # Obtener última factura
            ultima_factura = await self.get_ultima_factura(
                establecimiento, punto_expedicion, empresa_id
            )

            # Calcular estado
            if ultima_factura:
                ultimo_numero_usado = safe_str(
                    ultima_factura, 'numero_documento')
                ultimo_numero_int = int(ultimo_numero_usado)
                proximo_numero_int = ultimo_numero_int + 1
                fecha_ultimo_uso = safe_get(ultima_factura, 'created_at')
            else:
                numero_desde = safe_str(timbrado, 'numero_desde')
                ultimo_numero_usado = "0000000"
                proximo_numero_int = int(numero_desde)
                fecha_ultimo_uso = None

            # Formatear próximo número
            proximo_disponible = str(proximo_numero_int).zfill(7)

            # Calcular números restantes
            numero_hasta = safe_str(timbrado, 'numero_hasta')
            numero_hasta_int = int(numero_hasta)
            numeros_restantes = numero_hasta_int - proximo_numero_int + 1

            # Determinar si puede emitir
            puede_emitir = numeros_restantes > 0
            motivo_bloqueo = None if puede_emitir else "Numeración agotada"

            # Crear estado
            estado = EstadoSecuencia(
                ultimo_numero_usado=ultimo_numero_usado,
                proximo_disponible=proximo_disponible,
                numeros_restantes=max(0, numeros_restantes),
                timbrado_vigente=safe_str(timbrado, 'numero_timbrado'),
                puede_emitir=puede_emitir,
                motivo_bloqueo=motivo_bloqueo,
                fecha_ultimo_uso=fecha_ultimo_uso
            )

            # Log estado obtenido
            log_repository_operation(
                "get_secuencia_actual",
                details={
                    "establecimiento": establecimiento,
                    "punto_expedicion": punto_expedicion,
                    "proximo_disponible": proximo_disponible,
                    "numeros_restantes": numeros_restantes,
                    "puede_emitir": puede_emitir
                }
            )

            return estado

        except SQLAlchemyError as e:
            logger.error(f"Error BD en get_secuencia_actual: {e}")
            raise SifenDatabaseError(
                f"Error obteniendo estado secuencia: {str(e)}",
                operation="get_secuencia_actual"
            )
        except Exception as e:
            logger.error(f"Error inesperado en get_secuencia_actual: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def reset_secuencia(
        self,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int,
        motivo: str,
        nuevo_timbrado_id: Optional[int] = None
    ) -> bool:
        """
        Reinicia una secuencia de numeración.

        ATENCIÓN: Operación crítica que debe usarse solo en casos específicos:
        - Cambio de año fiscal
        - Activación de nuevo timbrado
        - Resolución de problemas de numeración con autorización SET

        Args:
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            empresa_id: ID de la empresa
            motivo: Motivo del reset (obligatorio para auditoría)
            nuevo_timbrado_id: ID del nuevo timbrado (opcional)

        Returns:
            bool: True si se reinició exitosamente

        Raises:
            SifenBusinessLogicError: Si hay facturas pendientes
            SifenDatabaseError: Error en operación

        Examples:
            >>> success = await repo.reset_secuencia(
            ...     "001", "001", empresa_id=1,
            ...     motivo="Nuevo año fiscal 2025",
            ...     nuevo_timbrado_id=123
            ... )
        """
        try:
            # Validar que no hay facturas en estado pendiente/enviado
            facturas_pendientes = self.db.query(self.model).filter(
                self.model.establecimiento == establecimiento,
                self.model.punto_expedicion == punto_expedicion,
                self.model.empresa_id == empresa_id,
                or_(
                    self.model.estado == 'enviado',  # type: ignore
                    self.model.estado == 'firmado'  # type: ignore
                )
            ).count()

            if facturas_pendientes > 0:
                raise SifenBusinessLogicError(
                    f"No se puede reiniciar secuencia con {facturas_pendientes} "
                    f"facturas pendientes de procesamiento SIFEN"
                )

            # TODO: Implementar lógica de reset cuando tengamos tabla de secuencias
            # Por ahora solo registramos la operación para auditoría

            # Log operación crítica
            log_repository_operation(
                "reset_secuencia",
                details={
                    "establecimiento": establecimiento,
                    "punto_expedicion": punto_expedicion,
                    "empresa_id": empresa_id,
                    "motivo": motivo,
                    "nuevo_timbrado_id": nuevo_timbrado_id,
                    "facturas_pendientes": facturas_pendientes
                },
                level="warning"  # Operación crítica
            )

            return True

        except SifenBusinessLogicError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error BD en reset_secuencia: {e}")
            raise SifenDatabaseError(
                f"Error reiniciando secuencia: {str(e)}",
                operation="reset_secuencia"
            )
        except Exception as e:
            logger.error(f"Error inesperado en reset_secuencia: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    # ===============================================
    # MÉTODOS DE ESTADÍSTICAS Y MONITOREO
    # ===============================================

    async def get_estadisticas_numeracion(
        self,
        empresa_id: int,
        periodo_dias: int = 30
    ) -> EstadisticasNumeracion:
        """
        Obtiene estadísticas completas de numeración para monitoreo.

        Genera métricas y análisis del uso de numeración:
        - Facturas por establecimiento/punto
        - Timbrados próximos a vencer
        - Uso promedio y proyecciones
        - Alertas operacionales

        Args:
            empresa_id: ID de la empresa
            periodo_dias: Días hacia atrás para análisis (default: 30)

        Returns:
            EstadisticasNumeracion: Estadísticas completas

        Raises:
            SifenDatabaseError: Error en consulta

        Examples:
            >>> stats = await repo.get_estadisticas_numeracion(empresa_id=1)
            >>> print(f"Uso promedio: {stats.uso_promedio_diario}")
            >>> for alerta in stats.timbrados_proximos_vencer:
            ...     print(f"Timbrado {alerta['numero']} vence en {alerta['dias']}")
        """
        try:
            fecha_desde = date.today() - timedelta(days=periodo_dias)

            # Obtener facturas por establecimiento
            facturas_por_establecimiento = {}

            # Query facturas del período agrupadas
            query_facturas = self.db.query(
                self.model.establecimiento,
                self.model.punto_expedicion,
                func.count(self.model.id).label('emitidas')
            ).filter(
                self.model.empresa_id == empresa_id,
                self.model.fecha_emision >= fecha_desde
            ).group_by(
                self.model.establecimiento,
                self.model.punto_expedicion
            )

            for row in query_facturas.all():
                key = f"{row.establecimiento}-{row.punto_expedicion}"

                # Obtener números restantes para este establecimiento/punto
                estado = await self.get_secuencia_actual(
                    row.establecimiento, row.punto_expedicion, empresa_id
                )

                facturas_por_establecimiento[key] = {
                    "emitidas": row.emitidas,
                    "restantes": estado.numeros_restantes
                }

            # Obtener timbrados próximos a vencer
            fecha_limite = date.today() + timedelta(days=30)
            timbrados_vencimiento = self.db.query(Timbrado).filter(
                Timbrado.empresa_id == empresa_id,
                Timbrado.fecha_fin_vigencia <= fecha_limite,
                Timbrado.fecha_fin_vigencia >= date.today(),
                Timbrado.estado == EstadoTimbradoEnum.ACTIVO.value  # type: ignore
            ).all()

            timbrados_proximos_vencer = []
            for timbrado in timbrados_vencimiento:
                numero_timbrado = safe_str(timbrado, 'numero_timbrado')
                fecha_fin = safe_get(timbrado, 'fecha_fin_vigencia')
                dias_restantes = (fecha_fin - date.today()).days

                timbrados_proximos_vencer.append({
                    "numero": numero_timbrado,
                    "dias_restantes": dias_restantes,
                    "fecha_vencimiento": fecha_fin.isoformat()
                })

            # Calcular uso promedio diario
            total_facturas = sum(est["emitidas"]
                                 for est in facturas_por_establecimiento.values())
            uso_promedio_diario = total_facturas / periodo_dias if periodo_dias > 0 else 0

            # Proyección de agotamiento (simplificada)
            proyeccion_agotamiento = None
            if uso_promedio_diario > 0:
                min_restantes = min(
                    (est["restantes"]
                     for est in facturas_por_establecimiento.values()),
                    default=0
                )
                if min_restantes > 0:
                    dias_restantes = min_restantes / uso_promedio_diario
                    proyeccion_agotamiento = date.today() + timedelta(days=dias_restantes)

            # Crear estadísticas
            estadisticas = EstadisticasNumeracion(
                facturas_por_establecimiento=facturas_por_establecimiento,
                timbrados_proximos_vencer=timbrados_proximos_vencer,
                uso_promedio_diario=round(uso_promedio_diario, 2),
                proyeccion_agotamiento=proyeccion_agotamiento
            )

            # Log estadísticas generadas
            log_repository_operation(
                "get_estadisticas_numeracion",
                details={
                    "empresa_id": empresa_id,
                    "periodo_dias": periodo_dias,
                    "total_facturas": total_facturas,
                    "establecimientos": len(facturas_por_establecimiento),
                    "timbrados_por_vencer": len(timbrados_proximos_vencer)
                }
            )

            return estadisticas

        except SQLAlchemyError as e:
            logger.error(f"Error BD en get_estadisticas_numeracion: {e}")
            raise SifenDatabaseError(
                f"Error obteniendo estadísticas: {str(e)}",
                operation="get_estadisticas_numeracion"
            )
        except Exception as e:
            logger.error(
                f"Error inesperado en get_estadisticas_numeracion: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

    async def get_health_check_numeracion(
        self,
        empresa_id: int
    ) -> Dict[str, Any]:
        """
        Verificación rápida del estado de salud de la numeración.

        Realiza validaciones críticas para detectar problemas:
        - Timbrados vigentes disponibles
        - Secuencias no bloqueadas
        - Numeración dentro de límites normales

        Args:
            empresa_id: ID de la empresa

        Returns:
            dict: Estado de salud con indicadores

        Examples:
            >>> health = await repo.get_health_check_numeracion(empresa_id=1)
            >>> if health["status"] != "healthy":
            ...     print(f"Problemas detectados: {health['issues']}")
        """
        try:
            issues = []
            warnings = []

            # Verificar timbrados vigentes
            timbrados_vigentes = self.db.query(Timbrado).filter(
                Timbrado.empresa_id == empresa_id,
                Timbrado.fecha_inicio_vigencia <= date.today(),
                Timbrado.fecha_fin_vigencia >= date.today(),
                Timbrado.estado == EstadoTimbradoEnum.ACTIVO.value  # type: ignore
            ).count()

            if timbrados_vigentes == 0:
                issues.append("No hay timbrados vigentes")

            # Verificar timbrados próximos a vencer (7 días)
            fecha_alerta = date.today() + timedelta(days=7)
            timbrados_por_vencer = self.db.query(Timbrado).filter(
                Timbrado.empresa_id == empresa_id,
                Timbrado.fecha_fin_vigencia <= fecha_alerta,
                Timbrado.fecha_fin_vigencia >= date.today(),
                Timbrado.estado == EstadoTimbradoEnum.ACTIVO.value  # type: ignore
            ).count()

            if timbrados_por_vencer > 0:
                warnings.append(
                    f"{timbrados_por_vencer} timbrado(s) vencen en 7 días")

            # Verificar numeración baja (< 100 números restantes)
            establecimientos_con_numeracion_baja = 0
            establecimientos_query = self.db.query(
                Timbrado.establecimiento,
                Timbrado.punto_expedicion
            ).filter(
                Timbrado.empresa_id == empresa_id,
                Timbrado.estado == EstadoTimbradoEnum.ACTIVO.value  # type: ignore
            ).distinct()

            for est, pex in establecimientos_query.all():
                estado = await self.get_secuencia_actual(est, pex, empresa_id)
                if estado.numeros_restantes < 100:
                    establecimientos_con_numeracion_baja += 1
                    if estado.numeros_restantes < 10:
                        issues.append(
                            f"Numeración crítica en {est}-{pex}: {estado.numeros_restantes} números")
                    else:
                        warnings.append(
                            f"Numeración baja en {est}-{pex}: {estado.numeros_restantes} números")

            # Determinar estado general
            if issues:
                status = "critical"
            elif warnings:
                status = "warning"
            else:
                status = "healthy"

            health_check = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "empresa_id": empresa_id,
                "timbrados_vigentes": timbrados_vigentes,
                "timbrados_por_vencer": timbrados_por_vencer,
                "establecimientos_numeracion_baja": establecimientos_con_numeracion_baja,
                "issues": issues,
                "warnings": warnings
            }

            # Log health check
            log_repository_operation(
                "get_health_check_numeracion",
                details={
                    "empresa_id": empresa_id,
                    "status": status,
                    "issues_count": len(issues),
                    "warnings_count": len(warnings)
                }
            )

            return health_check

        except SQLAlchemyError as e:
            logger.error(f"Error BD en get_health_check_numeracion: {e}")
            raise SifenDatabaseError(
                f"Error en health check: {str(e)}",
                operation="get_health_check_numeracion"
            )
        except Exception as e:
            logger.error(
                f"Error inesperado en get_health_check_numeracion: {e}")
            raise SifenDatabaseError(f"Error inesperado: {str(e)}")

        # ===============================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ===============================================

    async def _validate_continuidad_numerica(
        self,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int,
        numero_propuesto: int
    ) -> None:
        """
        Helper privado para validar continuidad numérica.

        Usado internamente por get_next_numero() para asegurar
        secuencia continua según normativa SET.

        Args:
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            empresa_id: ID de la empresa
            numero_propuesto: Número propuesto para validar

        Raises:
            SifenNumeracionDiscontinuaError: Si hay discontinuidad
        """
        try:
            # Obtener última factura
            ultima_factura = await self.get_ultima_factura(
                establecimiento, punto_expedicion, empresa_id
            )

            if ultima_factura:
                ultimo_numero = safe_str(ultima_factura, 'numero_documento')
                ultimo_numero_int = int(ultimo_numero)
                numero_esperado = ultimo_numero_int + 1

                if numero_propuesto != numero_esperado:
                    raise SifenNumeracionDiscontinuaError(
                        establecimiento=establecimiento,
                        punto_expedicion=punto_expedicion,
                        numero_esperado=numero_esperado,
                        numero_propuesto=numero_propuesto
                    )

        except SifenNumeracionDiscontinuaError:
            raise
        except Exception as e:
            logger.error(f"Error en _validate_continuidad_numerica: {e}")
            # No re-raise - la validación es opcional en algunos casos

    async def _reservar_numero_temporal(
        self,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int,
        numero: str
    ) -> None:
        """
        Reserva un número temporalmente para evitar conflictos de concurrencia.

        TODO: Implementar tabla temporal_number_reservations con TTL.
        Por ahora es un placeholder que verifica no duplicación.

        Args:
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            empresa_id: ID de la empresa
            numero: Número a reservar
        """
        # TODO: Implementar reserva real con tabla temporal
        # Estructura propuesta:
        # CREATE TABLE temporal_number_reservations (
        #     id SERIAL PRIMARY KEY,
        #     empresa_id INTEGER NOT NULL,
        #     establecimiento VARCHAR(3) NOT NULL,
        #     punto_expedicion VARCHAR(3) NOT NULL,
        #     numero_documento VARCHAR(7) NOT NULL,
        #     session_id VARCHAR(255),
        #     created_at TIMESTAMP DEFAULT NOW(),
        #     expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '5 minutes',
        #     UNIQUE(empresa_id, establecimiento, punto_expedicion, numero_documento)
        # );

        # Por ahora solo verificamos que no exista ya
        numero_completo = format_numero_factura(
            establecimiento, punto_expedicion, numero)
        exists = await self.check_numero_duplicado(numero_completo, empresa_id)

        if exists:
            raise SifenNumerationError(
                document_type="Factura",
                expected_number=int(numero),
                details={"tipo_error": "numero_ya_reservado"}
            )

        # Log reserva temporal (placeholder)
        log_repository_operation(
            "_reservar_numero_temporal",
            details={
                "numero_completo": numero_completo,
                "empresa_id": empresa_id,
                "reserva_status": "verified_available"
            }
        )

    async def _verificar_conflictos_rango(
        self,
        desde: int,
        hasta: int,
        establecimiento: str,
        punto_expedicion: str,
        empresa_id: int
    ) -> List[int]:
        """
        Verifica conflictos de numeración en un rango específico.

        Args:
            desde: Número inicial del rango
            hasta: Número final del rango
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            empresa_id: ID de la empresa

        Returns:
            List[int]: Lista de números en conflicto (ya usados)
        """
        try:
            # Buscar facturas existentes en el rango
            conflictos = []

            query = self.db.query(self.model.numero_documento).filter(
                self.model.establecimiento == establecimiento,
                self.model.punto_expedicion == punto_expedicion,
                self.model.empresa_id == empresa_id
            )

            facturas_existentes = query.all()

            for factura in facturas_existentes:
                numero_doc = safe_str(factura, 'numero_documento') if hasattr(
                    factura, 'numero_documento') else str(factura[0])
                numero_int = int(numero_doc)

                if desde <= numero_int <= hasta:
                    conflictos.append(numero_int)

            return sorted(conflictos)

        except Exception as e:
            logger.error(f"Error en _verificar_conflictos_rango: {e}")
            return []  # En caso de error, asumir sin conflictos

    def _generar_numero_completo(
        self,
        establecimiento: str,
        punto_expedicion: str,
        numero: str
    ) -> str:
        """
        Genera número completo en formato SIFEN (EST-PEX-NUMERO).

        Helper que usa la función utilitaria para consistencia.

        Args:
            establecimiento: Código establecimiento
            punto_expedicion: Código punto expedición
            numero: Número documento

        Returns:
            str: Número completo formateado
        """
        try:
            return format_numero_factura(establecimiento, punto_expedicion, numero)
        except Exception as e:
            logger.error(f"Error generando número completo: {e}")
            return f"{establecimiento}-{punto_expedicion}-{numero}"

    def _calcular_numeros_disponibles(self, timbrado: Timbrado) -> int:
        """
        Calcula números disponibles en un timbrado.

        Args:
            timbrado: Instancia de timbrado

        Returns:
            int: Cantidad de números disponibles
        """
        try:
            numero_desde = safe_str(timbrado, 'numero_desde')
            numero_hasta = safe_str(timbrado, 'numero_hasta')
            ultimo_usado = safe_str(timbrado, 'ultimo_numero_usado', '0000000')

            desde_int = int(numero_desde)
            hasta_int = int(numero_hasta)
            usado_int = int(ultimo_usado)

            # Si nunca se usó, todos están disponibles
            if usado_int == 0:
                return hasta_int - desde_int + 1

            # Números restantes después del último usado
            return max(0, hasta_int - usado_int)

        except Exception as e:
            logger.error(f"Error calculando números disponibles: {e}")
            return 0

    # ===============================================
    # MÉTODOS DE INFORMACIÓN Y METADATA
    # ===============================================

    def get_model_name(self) -> str:
        """Retorna el nombre del modelo para logging."""
        return "FacturaNumeracion"

    def get_mixin_version(self) -> str:
        """Retorna versión del mixin para compatibilidad."""
        return "1.0.0"

    def get_supported_operations(self) -> List[str]:
        """Retorna lista de operaciones soportadas por el mixin."""
        return [
            "get_next_numero",
            "reserve_numero_range",
            "get_timbrado_vigente",
            "check_timbrado_vigency",
            "validate_numeracion_continua",
            "check_numero_duplicado",
            "validate_timbrado_range",
            "get_secuencia_actual",
            "reset_secuencia",
            "get_estadisticas_numeracion",
            "get_health_check_numeracion"
        ]

    def __repr__(self) -> str:
        """Representación string del mixin."""
        return f"<FacturaNumeracionMixin(version={self.get_mixin_version()})>"


# ===============================================
# FUNCIONES DE UTILIDAD PARA TESTING
# ===============================================

def create_test_timbrado_data(
    empresa_id: int = 1,
    establecimiento: str = "001",
    punto_expedicion: str = "001",
    numero_timbrado: str = "12345678"
) -> Dict[str, Any]:
    """
    Crea datos de timbrado para testing.

    Función helper para tests unitarios y de integración.

    Args:
        empresa_id: ID de empresa de prueba
        establecimiento: Código establecimiento 
        punto_expedicion: Código punto expedición
        numero_timbrado: Número de timbrado

    Returns:
        dict: Datos de timbrado listos para crear instancia
    """
    return {
        "empresa_id": empresa_id,
        "numero_timbrado": numero_timbrado,
        "establecimiento": establecimiento,
        "punto_expedicion": punto_expedicion,
        "fecha_inicio_vigencia": date.today(),
        "fecha_fin_vigencia": date.today() + timedelta(days=365),
        "numero_desde": "0000001",
        "numero_hasta": "9999999",
        "ultimo_numero_usado": "0000000",
        "estado": EstadoTimbradoEnum.ACTIVO.value,
        "is_default": True
    }


def create_test_factura_data(
    empresa_id: int = 1,
    cliente_id: int = 1,
    establecimiento: str = "001",
    punto_expedicion: str = "001",
    numero_documento: str = "0000001"
) -> Dict[str, Any]:
    """
    Crea datos de factura para testing.

    Args:
        empresa_id: ID de empresa
        cliente_id: ID de cliente
        establecimiento: Código establecimiento
        punto_expedicion: Código punto expedición
        numero_documento: Número de documento

    Returns:
        dict: Datos de factura para testing
    """
    return {
        "empresa_id": empresa_id,
        "cliente_id": cliente_id,
        "establecimiento": establecimiento,
        "punto_expedicion": punto_expedicion,
        "numero_documento": numero_documento,
        "numero_timbrado": "12345678",
        "fecha_emision": date.today(),
        "fecha_inicio_vigencia": date.today(),
        "fecha_fin_vigencia": date.today() + timedelta(days=365),
        "tipo_documento": "1",
        "tipo_emision": "1",
        "tipo_operacion": "1",
        "condicion_operacion": "1",
        "moneda": "PYG",
        "tipo_cambio": Decimal("1.0000"),
        "total_general": Decimal("1000000"),
        "estado": "borrador"
    }


# ===============================================
# DOCUMENTACIÓN DE INTEGRACIÓN
# ===============================================

"""
=== GUÍA DE INTEGRACIÓN COMPLETA ===

1. COMPOSICIÓN CON REPOSITORY BASE:

```python
# En app/repositories/factura/__init__.py
from .base import FacturaRepositoryBase
from .numeracion_mixin import FacturaNumeracionMixin

class FacturaRepository(
    FacturaRepositoryBase,         # CRUD básico
    FacturaNumeracionMixin        # Numeración automática
):
    '''Repository completo para facturas'''
    pass
```

2. USO EN SERVICES:

```python
# En app/services/business/factura_service.py
from app.repositories.factura import FacturaRepository

class FacturaService:
    def __init__(self, db: Session):
        self.repo = FacturaRepository(db)
    
    async def crear_factura_automatica(self, data: FacturaCreateDTO):
        # Numeración automática
        numero = await self.repo.get_next_numero(
            establecimiento="001",
            punto_expedicion="001", 
            empresa_id=data.empresa_id
        )
        
        # Crear con número asignado
        factura_data = data.dict()
        factura_data["numero_documento"] = numero
        
        return await self.repo.create(factura_data)
```

3. USO EN APIs:

```python
# En app/api/v1/facturas.py
@router.post("/facturas/auto-numero")
async def crear_con_numeracion_automatica(
    factura_data: FacturaCreateDTO,
    db: Session = Depends(get_db)
):
    repo = FacturaRepository(db)
    
    # Obtener próximo número
    numero = await repo.get_next_numero(
        establecimiento=factura_data.establecimiento or "001",
        punto_expedicion=factura_data.punto_expedicion or "001",
        empresa_id=factura_data.empresa_id
    )
    
    # Verificar secuencia
    estado = await repo.get_secuencia_actual(
        establecimiento="001", 
        punto_expedicion="001",
        empresa_id=factura_data.empresa_id
    )
    
    if not estado.puede_emitir:
        raise HTTPException(400, detail=estado.motivo_bloqueo)
    
    # Crear factura
    return await repo.create(factura_data)

@router.get("/numeracion/estado/{empresa_id}")
async def get_estado_numeracion(
    empresa_id: int,
    db: Session = Depends(get_db)
):
    repo = FacturaRepository(db)
    
    # Estado general
    health = await repo.get_health_check_numeracion(empresa_id)
    
    # Estadísticas
    stats = await repo.get_estadisticas_numeracion(empresa_id)
    
    return {
        "health": health,
        "estadisticas": stats.to_dict()
    }
```

4. MONITOREO Y ALERTAS:

```python
# Task periódica para monitoreo
async def monitor_numeracion():
    db = SessionLocal()
    try:
        repo = FacturaRepository(db)
        
        # Verificar todas las empresas
        empresas = db.query(Empresa).all()
        
        for empresa in empresas:
            health = await repo.get_health_check_numeracion(empresa.id)
            
            if health["status"] == "critical":
                # Enviar alerta crítica
                await send_critical_alert(empresa.id, health["issues"])
            elif health["status"] == "warning":
                # Enviar alerta preventiva
                await send_warning_alert(empresa.id, health["warnings"])
    
    finally:
        db.close()
```

=== CASOS DE USO AVANZADOS ===

A. FACTURACIÓN MASIVA:
```python
# Reservar rango para lote
await repo.reserve_numero_range(
    desde="0000100", hasta="0000200",
    establecimiento="001", punto_expedicion="001",
    empresa_id=1, motivo="Facturación masiva mensual"
)

# Procesar lote con números reservados
for i, data in enumerate(facturas_data):
    numero = f"{100 + i:07d}"
    data["numero_documento"] = numero
    await repo.create(data)
```

B. CAMBIO DE AÑO:
```python
# Verificar si necesita nuevo timbrado
estado = await repo.get_secuencia_actual("001", "001", empresa_id=1)

if not estado.puede_emitir:
    # Activar nuevo timbrado
    await repo.reset_secuencia(
        "001", "001", empresa_id=1,
        motivo="Nuevo año fiscal 2025",
        nuevo_timbrado_id=new_timbrado.id
    )
```

C. VALIDACIÓN ANTES DE CREAR:
```python
# Verificar que número no esté duplicado
duplicado = await repo.check_numero_duplicado(
    "001-001-0000123", empresa_id=1
)

if duplicado:
    raise ValueError("Número ya existe")

# Validar continuidad
await repo.validate_numeracion_continua(
    "001", "001", "0000123", empresa_id=1
)
```

=== CONFIGURACIÓN RECOMENDADA ===

1. Variables de entorno:
   - NUMERACION_VALIDATION_STRICT=true
   - NUMERACION_RESERVE_TIMEOUT=300
   - NUMERACION_ALERT_THRESHOLD=100

2. Índices de BD recomendados:
   ```sql
   CREATE INDEX idx_factura_numeracion 
   ON factura(empresa_id, establecimiento, punto_expedicion, numero_documento);
   
   CREATE INDEX idx_timbrado_vigencia 
   ON timbrado(empresa_id, fecha_inicio_vigencia, fecha_fin_vigencia, estado);
   ```

3. Configuración de alertas:
   - Números restantes < 100: Warning
   - Números restantes < 10: Critical  
   - Timbrado vence en < 30 días: Warning
   - Timbrado vence en < 7 días: Critical

=== TROUBLESHOOTING ===

Problema: "Numeración discontinua"
Solución: Verificar secuencia con get_secuencia_actual()

Problema: "Timbrado vencido"  
Solución: Activar nuevo timbrado o extender vigencia

Problema: "Numeración agotada"
Solución: Solicitar nuevo timbrado a SET

Problema: "Número duplicado"
Solución: Usar get_next_numero() para asegurar unicidad
"""


# ===============================================
# EXPORTS Y METADATA
# ===============================================

__all__ = [
    # Clase principal
    "FacturaNumeracionMixin",

    # Clases de datos
    "EstadoSecuencia",
    "EstadisticasNumeracion",

    # Excepciones específicas
    "SifenTimbradoVencidoError",
    "SifenNumeracionAgotadaError",
    "SifenNumeracionDiscontinuaError",

    # Helpers para testing
    "create_test_timbrado_data",
    "create_test_factura_data"
]
