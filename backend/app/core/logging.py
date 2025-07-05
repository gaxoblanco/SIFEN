# ===============================================
# ARCHIVO: backend/app/core/logging.py
# PROPÓSITO: Sistema de logging unificado para toda la aplicación
# VERSIÓN: 1.0.0
# ===============================================

"""
Sistema de logging unificado para la aplicación SIFEN.

Este módulo proporciona una configuración centralizada de logging que:
- Unifica todos los sistemas de logging existentes
- Proporciona loggers específicos por módulo
- Configura formatos consistentes
- Maneja diferentes niveles según el ambiente
- Integra con structlog para logging estructurado
- Proporciona utilidades para logging de performance y debugging

Uso:
    from app.core.logging import get_logger
    
    logger = get_logger(__name__)
    logger.info("Mensaje informativo")
    logger.error("Error crítico", extra={"context": "additional_data"})

Características:
- Configuración automática según ambiente
- Formatos JSON para producción
- Formatos legibles para desarrollo
- Rotating file handlers
- Filtros por módulo y nivel
- Métricas de performance integradas
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Optional, Union
import json

# Intentar importar structlog si está disponible
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

# Importar configuración de la aplicación
try:
    from app.core.config import settings
except ImportError:
    # Fallback si no existe la configuración
    class _FallbackSettings:
        ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        PROJECT_NAME = os.getenv("PROJECT_NAME", "SIFEN")

    settings = _FallbackSettings()

# ===============================================
# CONFIGURACIÓN DE LOGGING
# ===============================================

# Niveles de logging
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Formatos de logging
LOG_FORMATS = {
    "development": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "production": "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d",
    "testing": "%(levelname)s - %(name)s - %(message)s",
    "json": None  # Se maneja con JSONFormatter
}

# Colores para consola (desarrollo)
LOG_COLORS = {
    "DEBUG": "\033[36m",      # Cyan
    "INFO": "\033[32m",       # Green
    "WARNING": "\033[33m",    # Yellow
    "ERROR": "\033[31m",      # Red
    "CRITICAL": "\033[35m",   # Magenta
    "RESET": "\033[0m"        # Reset
}

# ===============================================
# FORMATTERS PERSONALIZADOS
# ===============================================


class ColoredFormatter(logging.Formatter):
    """Formatter con colores para desarrollo."""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.base_format = fmt or LOG_FORMATS["development"]

    def format(self, record):
        # Aplicar color según el nivel
        color = LOG_COLORS.get(record.levelname, LOG_COLORS["RESET"])
        reset = LOG_COLORS["RESET"]

        # Formatear el mensaje base
        original_format = self._style._fmt
        self._style._fmt = f"{color}{self.base_format}{reset}"

        formatted = super().format(record)

        # Restaurar formato original
        self._style._fmt = original_format

        return formatted


class JSONFormatter(logging.Formatter):
    """Formatter JSON para producción."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread
        }

        # Añadir información extra específica si existe
        for attr in ['user_id', 'request_id', 'session_id', 'operation_id']:
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)

        # Añadir información de excepción si existe
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Añadir stack trace si existe
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info

        return json.dumps(log_entry, ensure_ascii=False)


class SifenFormatter(logging.Formatter):
    """Formatter específico para SIFEN con contexto adicional."""

    def format(self, record):
        # Añadir contexto SIFEN si no existe
        if not hasattr(record, 'sifen_context'):
            record.sifen_context = {
                "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
                "project": getattr(settings, 'PROJECT_NAME', 'SIFEN')
            }

        return super().format(record)


# ===============================================
# CONFIGURACIÓN DE HANDLERS
# ===============================================

def get_console_handler() -> logging.StreamHandler:
    """Crea handler para salida por consola."""
    handler = logging.StreamHandler(sys.stdout)

    # Seleccionar formatter según ambiente
    environment = getattr(settings, 'ENVIRONMENT', 'development')

    if environment == 'development':
        formatter = ColoredFormatter()
    elif environment == 'production':
        formatter = JSONFormatter()
    else:
        formatter = SifenFormatter(LOG_FORMATS.get(
            environment, LOG_FORMATS["development"]))

    handler.setFormatter(formatter)
    return handler


def get_file_handler(log_file: Optional[str] = None) -> logging.handlers.RotatingFileHandler:
    """Crea handler para archivos con rotación."""
    if not log_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = str(
            log_dir / f"sifen_{datetime.now().strftime('%Y%m%d')}.log")

    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )

    # Usar formato JSON para archivos
    formatter = JSONFormatter()
    handler.setFormatter(formatter)

    return handler


def get_error_handler() -> logging.handlers.RotatingFileHandler:
    """Crea handler específico para errores."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    error_file = log_dir / \
        f"sifen_errors_{datetime.now().strftime('%Y%m%d')}.log"

    handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )

    # Solo errores y críticos
    handler.setLevel(logging.ERROR)

    # Formato detallado para errores
    formatter = JSONFormatter()
    handler.setFormatter(formatter)

    return handler


# ===============================================
# CONFIGURACIÓN PRINCIPAL
# ===============================================

def configure_logging():
    """Configura el sistema de logging de la aplicación."""

    # Obtener nivel de logging
    log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
    level = LOG_LEVELS.get(log_level.upper(), logging.INFO)

    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Limpiar handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Añadir handlers según el ambiente
    environment = getattr(settings, 'ENVIRONMENT', 'development')

    # Handler de consola (siempre presente)
    console_handler = get_console_handler()
    root_logger.addHandler(console_handler)

    # Handlers de archivo (solo en producción y testing)
    if environment in ['production', 'testing']:
        file_handler = get_file_handler()
        root_logger.addHandler(file_handler)

        error_handler = get_error_handler()
        root_logger.addHandler(error_handler)

    # Configurar loggers específicos
    configure_specific_loggers()

    # Configurar structlog si está disponible
    if HAS_STRUCTLOG:
        configure_structlog()

    # Log de inicialización
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configurado para ambiente: {environment}, nivel: {log_level}")


def configure_specific_loggers():
    """Configura loggers específicos para módulos."""

    # Logger para SQLAlchemy
    sqlalchemy_logger = logging.getLogger('sqlalchemy')
    if getattr(settings, 'DATABASE_ECHO', False):
        sqlalchemy_logger.setLevel(logging.INFO)
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)

    # Logger para requests HTTP
    requests_logger = logging.getLogger('urllib3')
    requests_logger.setLevel(logging.WARNING)

    # Logger para servicios SIFEN
    sifen_logger = logging.getLogger('app.services')
    sifen_logger.setLevel(logging.INFO)

    # Logger para repositorios
    repo_logger = logging.getLogger('app.repositories')
    repo_logger.setLevel(logging.INFO)

    # Logger para APIs
    api_logger = logging.getLogger('app.api')
    api_logger.setLevel(logging.INFO)


def configure_structlog():
    """Configura structlog para logging estructurado."""

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Añadir processor JSON para producción
    environment = getattr(settings, 'ENVIRONMENT', 'development')
    if environment == 'production':
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# ===============================================
# FUNCIONES PRINCIPALES
# ===============================================

@lru_cache(maxsize=128)
def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado para el módulo especificado.

    Args:
        name: Nombre del módulo (usar __name__)

    Returns:
        logging.Logger: Logger configurado

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Mensaje de información")
    """
    return logging.getLogger(name)


def get_structured_logger(name: str) -> Union[logging.Logger, Any]:
    """
    Obtiene un logger estructurado si structlog está disponible.

    Args:
        name: Nombre del módulo

    Returns:
        Logger estructurado o logger estándar

    Example:
        >>> logger = get_structured_logger(__name__)
        >>> logger.info("Mensaje estructurado", extra={"user_id": 123})
    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    else:
        return get_logger(name)


def log_performance(operation: str, duration: float,
                    extra_context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log especializado para métricas de performance.

    Args:
        operation: Nombre de la operación
        duration: Duración en segundos
        extra_context: Contexto adicional

    Example:
        >>> log_performance("database_query", 0.045, {"table": "usuarios"})
    """
    logger = get_logger("performance")

    context = {
        "operation": operation,
        "duration_seconds": duration,
        "performance_category": "timing"
    }

    if extra_context:
        context.update(extra_context)

    # Determinar nivel según duración
    if duration > 5.0:
        logger.warning(
            f"Operación lenta detectada: {operation}", extra=context)
    elif duration > 1.0:
        logger.info(f"Operación: {operation}", extra=context)
    else:
        logger.debug(f"Operación rápida: {operation}", extra=context)


def log_sifen_operation(operation: str, document_type: str,
                        result: str, extra_context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log especializado para operaciones SIFEN.

    Args:
        operation: Tipo de operación (generate_xml, send_document, etc.)
        document_type: Tipo de documento (factura, nota_credito, etc.)
        result: Resultado (success, error, warning)
        extra_context: Contexto adicional

    Example:
        >>> log_sifen_operation("generate_xml", "factura", "success", {"cdc": "123..."})
    """
    logger = get_logger("sifen_operations")

    context = {
        "operation": operation,
        "document_type": document_type,
        "result": result,
        "sifen_category": "document_processing"
    }

    if extra_context:
        context.update(extra_context)

    # Determinar nivel según resultado
    if result == "error":
        logger.error(f"Error en operación SIFEN: {operation}", extra=context)
    elif result == "warning":
        logger.warning(
            f"Advertencia en operación SIFEN: {operation}", extra=context)
    else:
        logger.info(f"Operación SIFEN exitosa: {operation}", extra=context)


def log_repository_operation(operation: str, entity_type: str,
                             entity_id: Optional[Union[int, str]] = None,
                             extra_context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log especializado para operaciones de repositorio.

    Args:
        operation: Tipo de operación (create, update, delete, etc.)
        entity_type: Tipo de entidad (Documento, Cliente, etc.)
        entity_id: ID de la entidad
        extra_context: Contexto adicional

    Example:
        >>> log_repository_operation("create", "Documento", 123, {"tipo": "factura"})
    """
    logger = get_logger("repository_operations")

    context = {
        "operation": operation,
        "entity_type": entity_type,
        "repository_category": "data_access"
    }

    if entity_id:
        context["entity_id"] = str(entity_id)

    if extra_context:
        context.update(extra_context)

    logger.info(
        f"Operación repository: {operation} {entity_type}", extra=context)


# ===============================================
# UTILIDADES DE DEBUGGING
# ===============================================

def enable_debug_logging():
    """Habilita logging de debug temporalmente."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    debug_logger = get_logger("debug")
    debug_logger.info("Debug logging habilitado")


def disable_debug_logging():
    """Deshabilita logging de debug."""
    log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
    level = LOG_LEVELS.get(log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    debug_logger = get_logger("debug")
    debug_logger.info("Debug logging deshabilitado")


def log_exception(logger: logging.Logger, exception: Exception,
                  context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log una excepción con contexto adicional.

    Args:
        logger: Logger a usar
        exception: Excepción a loggear
        context: Contexto adicional

    Example:
        >>> try:
        ...     # código que puede fallar
        ... except Exception as e:
        ...     log_exception(logger, e, {"user_id": 123})
    """
    log_context = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception)
    }

    if context:
        log_context.update(context)

    logger.error(f"Excepción capturada: {type(exception).__name__}",
                 extra=log_context, exc_info=True)


# ===============================================
# INICIALIZACIÓN AUTOMÁTICA
# ===============================================

# Configurar logging al importar el módulo
configure_logging()

# Logger principal del módulo
logger = get_logger(__name__)

# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # Funciones principales
    "get_logger",
    "get_structured_logger",
    "configure_logging",

    # Logging especializado
    "log_performance",
    "log_sifen_operation",
    "log_repository_operation",

    # Utilidades
    "enable_debug_logging",
    "disable_debug_logging",
    "log_exception",

    # Constantes
    "LOG_LEVELS",
    "LOG_FORMATS",
    "HAS_STRUCTLOG"
]
