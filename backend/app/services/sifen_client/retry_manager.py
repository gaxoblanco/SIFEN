"""
Sistema de reintentos con backoff exponencial para SIFEN Paraguay

Maneja reintentos automáticos para errores temporales de SIFEN,
implementando estrategias inteligentes de backoff y circuito de corte.

Funcionalidades:
- Backoff exponencial configurable con jitter
- Circuito de corte para evitar cascadas de fallos
- Análisis de patrones de error para optimización
- Logging detallado del historial de reintentos
- Integración con error_handler para determinar retryabilidad

Estrategias de retry:
- Exponential backoff: 1s → 2s → 4s → 8s
- Jitter aleatorio para evitar thundering herd
- Circuit breaker pattern para protección
- Timeout progresivo para operaciones lentas

Basado en:
- Best practices de sistemas distribuidos
- Patrones de resiliencia para APIs
- Configuración específica para SIFEN
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import Callable, Any, List, Dict, Optional, Union, TypeVar, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import structlog

# Módulos internos
from .config import SifenConfig
from .exceptions import (
    SifenClientError,
    SifenConnectionError,
    SifenTimeoutError,
    SifenServerError,
    SifenRetryExhaustedError
)
from .error_handler import SifenErrorHandler, ErrorCategory

# Logger para el retry manager
logger = structlog.get_logger(__name__)

# Type variables para funciones genéricas
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Awaitable[Any]])


class RetryStrategy(str, Enum):
    """
    Estrategias de retry disponibles
    """
    EXPONENTIAL = "exponential"          # Backoff exponencial (default)
    LINEAR = "linear"                    # Incremento lineal
    FIXED = "fixed"                      # Intervalo fijo
    FIBONACCI = "fibonacci"              # Secuencia Fibonacci


class CircuitState(str, Enum):
    """
    Estados del circuit breaker
    """
    CLOSED = "closed"                    # Funcionando normalmente
    OPEN = "open"                        # Circuito abierto (fallos detectados)
    HALF_OPEN = "half_open"             # Probando si se recuperó


@dataclass
class RetryAttempt:
    """
    Información de un intento de retry
    """
    attempt_number: int
    timestamp: datetime
    delay_seconds: float
    error_type: str
    error_message: str
    elapsed_time_ms: Optional[float] = None
    success: bool = False


@dataclass
class RetryResult:
    """
    Resultado final de una operación con reintentos
    """
    success: bool
    final_result: Optional[Any]
    total_attempts: int
    total_elapsed_time_ms: float
    retry_history: List[RetryAttempt]
    final_error: Optional[Exception] = None


@dataclass
class CircuitBreakerState:
    """
    Estado del circuit breaker
    """
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None


class RetryManager:
    """
    Gestor de reintentos con múltiples estrategias y circuit breaker

    Proporciona reintentos inteligentes para operaciones que pueden
    fallar temporalmente, especialmente para comunicación con SIFEN.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        jitter: bool = True,
        enable_circuit_breaker: bool = True,
        circuit_failure_threshold: int = 5,
        circuit_timeout: float = 30.0,
        error_handler: Optional[SifenErrorHandler] = None
    ):
        """
        Inicializa el gestor de reintentos

        Args:
            max_retries: Número máximo de reintentos
            base_delay: Delay base en segundos
            max_delay: Delay máximo en segundos
            backoff_factor: Factor de backoff exponencial
            strategy: Estrategia de retry a usar
            jitter: Agregar jitter aleatorio
            enable_circuit_breaker: Habilitar circuit breaker
            circuit_failure_threshold: Fallos para abrir circuito
            circuit_timeout: Tiempo antes de probar half-open
            error_handler: Handler de errores SIFEN
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.strategy = strategy
        self.jitter = jitter
        self.enable_circuit_breaker = enable_circuit_breaker
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_timeout = circuit_timeout
        self.error_handler = error_handler or SifenErrorHandler()

        # Estado del circuit breaker
        self.circuit_state = CircuitBreakerState()

        # Estadísticas
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'circuit_opens': 0,
            'avg_retry_count': 0.0
        }

        logger.info(
            "retry_manager_initialized",
            max_retries=max_retries,
            strategy=strategy.value,
            base_delay=base_delay,
            circuit_breaker_enabled=enable_circuit_breaker
        )

    async def execute_with_retry(
        self,
        operation: Callable[..., Awaitable[T]],
        *args,
        operation_name: str = "sifen_operation",
        **kwargs
    ) -> T:
        """
        Ejecuta una operación con reintentos automáticos

        Args:
            operation: Función asíncrona a ejecutar
            *args: Argumentos posicionales para la operación
            operation_name: Nombre de la operación para logging
            **kwargs: Argumentos con nombre para la operación

        Returns:
            Resultado de la operación

        Raises:
            SifenRetryExhaustedError: Si se agotan los reintentos
            SifenClientError: Si el circuito está abierto
        """
        start_time = time.perf_counter()
        retry_history: List[RetryAttempt] = []

        # Verificar circuit breaker
        if self.enable_circuit_breaker:
            await self._check_circuit_breaker(operation_name)

        self.stats['total_operations'] += 1

        for attempt in range(self.max_retries + 1):  # +1 para el intento inicial
            attempt_start = time.perf_counter()

            try:
                # Log del intento
                logger.debug(
                    "retry_attempt_start",
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_retries=self.max_retries + 1
                )

                # Ejecutar operación
                result = await operation(*args, **kwargs)

                # Éxito - actualizar estadísticas
                elapsed = (time.perf_counter() - attempt_start) * 1000

                if attempt > 0:
                    # Fue un retry exitoso
                    retry_history.append(RetryAttempt(
                        attempt_number=attempt + 1,
                        timestamp=datetime.now(),
                        delay_seconds=0,
                        error_type="none",
                        error_message="success",
                        elapsed_time_ms=elapsed,
                        success=True
                    ))

                # Actualizar circuit breaker
                if self.enable_circuit_breaker:
                    await self._record_success()

                # Actualizar estadísticas
                self.stats['successful_operations'] += 1
                self.stats['total_retries'] += attempt

                total_elapsed = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "retry_operation_success",
                    operation=operation_name,
                    attempts=attempt + 1,
                    total_time_ms=total_elapsed,
                    retries_used=attempt
                )

                return result

            except Exception as e:
                elapsed = (time.perf_counter() - attempt_start) * 1000

                # Registrar el intento fallido
                retry_attempt = RetryAttempt(
                    attempt_number=attempt + 1,
                    timestamp=datetime.now(),
                    delay_seconds=0,  # Se actualiza antes del delay
                    error_type=type(e).__name__,
                    error_message=str(e),
                    elapsed_time_ms=elapsed,
                    success=False
                )
                retry_history.append(retry_attempt)

                # Verificar si el error es retryable
                is_retryable = self._is_retryable_error(e)

                # Si es el último intento o el error no es retryable
                if attempt >= self.max_retries or not is_retryable:
                    # Registrar fallo final
                    if self.enable_circuit_breaker:
                        await self._record_failure()

                    self.stats['failed_operations'] += 1
                    self.stats['total_retries'] += attempt

                    total_elapsed = (time.perf_counter() - start_time) * 1000

                    logger.error(
                        "retry_operation_failed",
                        operation=operation_name,
                        attempts=attempt + 1,
                        total_time_ms=total_elapsed,
                        final_error=str(e),
                        is_retryable=is_retryable
                    )

                    # Lanzar excepción de reintentos agotados
                    raise SifenRetryExhaustedError(
                        message=f"Operación '{operation_name}' falló después de {attempt + 1} intentos",
                        max_retries=self.max_retries,
                        retry_history=[self._attempt_to_dict(
                            attempt) for attempt in retry_history],
                        last_exception=e
                    )

                # Calcular delay para el próximo intento
                delay = self._calculate_delay(attempt + 1)
                retry_attempt.delay_seconds = delay

                logger.warning(
                    "retry_attempt_failed",
                    operation=operation_name,
                    attempt=attempt + 1,
                    error=str(e),
                    next_delay_seconds=delay,
                    is_retryable=is_retryable
                )

                # Esperar antes del próximo intento
                await asyncio.sleep(delay)

        # Este punto no debería alcanzarse, pero por seguridad
        raise SifenRetryExhaustedError(
            message=f"Operación '{operation_name}' falló inesperadamente",
            max_retries=self.max_retries,
            retry_history=[self._attempt_to_dict(
                attempt) for attempt in retry_history],
            last_exception=Exception("Error inesperado en retry loop")
        )

    def _attempt_to_dict(self, attempt: RetryAttempt) -> Dict[str, Any]:
        """
        Convierte un RetryAttempt a diccionario para compatibilidad

        Args:
            attempt: RetryAttempt a convertir

        Returns:
            Diccionario con los datos del intento
        """
        return {
            'attempt_number': attempt.attempt_number,
            'timestamp': attempt.timestamp.isoformat(),
            'delay_seconds': attempt.delay_seconds,
            'error_type': attempt.error_type,
            'error_message': attempt.error_message,
            'elapsed_time_ms': attempt.elapsed_time_ms,
            'success': attempt.success
        }

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determina si un error es retryable

        Args:
            error: Excepción a evaluar

        Returns:
            True si el error es retryable, False si no
        """
        # Errores que nunca son retryables
        non_retryable_types = (
            SifenRetryExhaustedError,  # Ya se agotaron los reintentos
        )

        if isinstance(error, non_retryable_types):
            return False

        # Errores siempre retryables
        retryable_types = (
            SifenConnectionError,
            SifenTimeoutError,
            SifenServerError,
            asyncio.TimeoutError,
            ConnectionError,
            OSError  # Errores de red
        )

        if isinstance(error, retryable_types):
            return True

        # Para errores SIFEN específicos, consultar al error handler
        if isinstance(error, SifenClientError):
            if hasattr(error, 'error_code') and error.error_code:
                return self.error_handler.is_retryable_error(error.error_code)

            # Si es un error del sistema, probablemente retryable
            if hasattr(error, 'details'):
                category = error.details.get('error_category')
                if category == ErrorCategory.SYSTEM.value:
                    return True

        # Por defecto, errores de red/conexión son retryables
        error_message = str(error).lower()
        retryable_keywords = [
            'timeout', 'connection', 'network', 'temporarily',
            'unavailable', 'busy', 'overloaded', 'rate limit'
        ]

        return any(keyword in error_message for keyword in retryable_keywords)

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calcula el delay para un intento específico

        Args:
            attempt: Número de intento (1-based)

        Returns:
            Delay en segundos
        """
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        elif self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.FIBONACCI:
            delay = self.base_delay * self._fibonacci(attempt)
        else:
            delay = self.base_delay

        # Aplicar límite máximo
        delay = min(delay, self.max_delay)

        # Agregar jitter si está habilitado
        if self.jitter:
            jitter_amount = delay * 0.1  # 10% de jitter
            jitter_offset = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay + jitter_offset)  # Mínimo 100ms

        return delay

    def _fibonacci(self, n: int) -> int:
        """Calcula el número Fibonacci para posición n"""
        if n <= 1:
            return 1
        elif n == 2:
            return 1
        else:
            a, b = 1, 1
            for _ in range(2, n):
                a, b = b, a + b
            return b

    async def _check_circuit_breaker(self, operation_name: str) -> None:
        """
        Verifica el estado del circuit breaker

        Args:
            operation_name: Nombre de la operación

        Raises:
            SifenClientError: Si el circuito está abierto
        """
        now = datetime.now()

        if self.circuit_state.state == CircuitState.OPEN:
            # Verificar si es tiempo de probar half-open
            if (self.circuit_state.next_attempt_time and
                    now >= self.circuit_state.next_attempt_time):

                self.circuit_state.state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker_half_open",
                    operation=operation_name,
                    failure_count=self.circuit_state.failure_count
                )
            else:
                # Circuito aún cerrado
                raise SifenClientError(
                    message=f"Circuit breaker abierto para '{operation_name}'",
                    details={
                        'circuit_state': self.circuit_state.state.value,
                        'failure_count': self.circuit_state.failure_count,
                        'next_attempt_time': self.circuit_state.next_attempt_time.isoformat() if self.circuit_state.next_attempt_time else None
                    }
                )

    async def _record_success(self) -> None:
        """Registra un éxito en el circuit breaker"""
        if self.circuit_state.state == CircuitState.HALF_OPEN:
            # Recuperación exitosa
            self.circuit_state.state = CircuitState.CLOSED
            self.circuit_state.failure_count = 0
            self.circuit_state.next_attempt_time = None

            logger.info(
                "circuit_breaker_recovered",
                new_state=self.circuit_state.state.value
            )

        self.circuit_state.last_success_time = datetime.now()

    async def _record_failure(self) -> None:
        """Registra un fallo en el circuit breaker"""
        self.circuit_state.failure_count += 1
        self.circuit_state.last_failure_time = datetime.now()

        # Verificar si debe abrir el circuito
        if (self.circuit_state.failure_count >= self.circuit_failure_threshold and
                self.circuit_state.state != CircuitState.OPEN):

            self.circuit_state.state = CircuitState.OPEN
            self.circuit_state.next_attempt_time = (
                datetime.now() + timedelta(seconds=self.circuit_timeout)
            )
            self.stats['circuit_opens'] += 1

            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.circuit_state.failure_count,
                next_attempt_time=self.circuit_state.next_attempt_time.isoformat()
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del retry manager

        Returns:
            Diccionario con estadísticas de uso
        """
        total_ops = self.stats['total_operations']
        if total_ops > 0:
            self.stats['avg_retry_count'] = self.stats['total_retries'] / total_ops
            self.stats['success_rate'] = (
                self.stats['successful_operations'] / total_ops) * 100

        return {
            **self.stats,
            'circuit_state': self.circuit_state.state.value,
            'circuit_failure_count': self.circuit_state.failure_count,
            'configuration': {
                'max_retries': self.max_retries,
                'strategy': self.strategy.value,
                'base_delay': self.base_delay,
                'max_delay': self.max_delay,
                'circuit_breaker_enabled': self.enable_circuit_breaker
            }
        }

    def reset_circuit_breaker(self) -> None:
        """Resetea manualmente el circuit breaker"""
        old_state = self.circuit_state.state
        self.circuit_state = CircuitBreakerState()

        logger.info(
            "circuit_breaker_manual_reset",
            old_state=old_state.value,
            new_state=self.circuit_state.state.value
        )

    def reset_stats(self) -> None:
        """Resetea las estadísticas del retry manager"""
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'circuit_opens': 0,
            'avg_retry_count': 0.0
        }

        logger.info("retry_manager_stats_reset")


# ========================================
# FUNCIONES HELPER
# ========================================

def create_retry_manager_from_config(config: SifenConfig) -> RetryManager:
    """
    Crea un RetryManager desde configuración SIFEN

    Args:
        config: Configuración SIFEN

    Returns:
        RetryManager configurado
    """
    return RetryManager(
        max_retries=config.max_retries,
        base_delay=config.backoff_factor,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter=True,
        enable_circuit_breaker=True,
        circuit_failure_threshold=5,
        circuit_timeout=30.0
    )


async def retry_operation(
    operation: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    *args,
    **kwargs
) -> T:
    """
    Función helper para retry simple sin configuración compleja

    Args:
        operation: Función a ejecutar
        max_retries: Número máximo de reintentos
        base_delay: Delay base en segundos
        *args: Argumentos para la operación
        **kwargs: Argumentos con nombre para la operación

    Returns:
        Resultado de la operación
    """
    retry_manager = RetryManager(
        max_retries=max_retries,
        base_delay=base_delay,
        enable_circuit_breaker=False  # Simplificado
    )

    return await retry_manager.execute_with_retry(
        operation,
        *args,
        operation_name="simple_retry",
        **kwargs
    )


class RetryDecorator:
    """
    Decorador para agregar reintentos a funciones asíncronas
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        operation_name: Optional[str] = None
    ):
        self.retry_manager = RetryManager(
            max_retries=max_retries,
            base_delay=base_delay,
            strategy=strategy,
            enable_circuit_breaker=False  # Para decorador simple
        )
        self.operation_name = operation_name

    def __call__(self, func: F) -> F:
        async def wrapper(*args, **kwargs):
            operation_name = self.operation_name or func.__name__
            return await self.retry_manager.execute_with_retry(
                func,
                *args,
                operation_name=operation_name,
                **kwargs
            )

        return wrapper  # type: ignore


# Decorador helper
def retry_on_failure(
    max_retries: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    operation_name: Optional[str] = None
) -> Callable[[F], F]:
    """
    Decorador para agregar reintentos a funciones

    Args:
        max_retries: Número máximo de reintentos
        base_delay: Delay base en segundos
        strategy: Estrategia de retry
        operation_name: Nombre de la operación para logging

    Returns:
        Decorador configurado
    """
    return RetryDecorator(max_retries, base_delay, strategy, operation_name)


logger.info(
    "retry_manager_module_loaded",
    features=[
        "exponential_backoff",
        "circuit_breaker",
        "multiple_strategies",
        "jitter_support",
        "detailed_logging",
        "statistics_tracking"
    ]
)
