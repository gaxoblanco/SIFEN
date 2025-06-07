"""
Módulo SIFEN Client para integración con Web Services SIFEN Paraguay

Este módulo maneja la comunicación con los servicios SOAP de SIFEN para:
- Envío de documentos electrónicos individuales
- Envío de lotes de documentos (hasta 50)
- Consulta de estados de documentos por CDC
- Manejo robusto de errores y reintentos

Arquitectura:
- client.py: Cliente SOAP principal (TLS 1.2)
- document_sender.py: Orquestador de alto nivel
- response_parser.py: Parser de respuestas XML SIFEN
- error_handler.py: Mapeo códigos error a mensajes user-friendly
- retry_manager.py: Sistema reintentos con backoff exponencial

Uso básico:
    from .document_sender import DocumentSender
    from .config import SifenConfig
    
    config = SifenConfig(base_url="https://sifen-test.set.gov.py/")
    sender = DocumentSender(config)
    
    result = await sender.send_signed_document(xml_content, cert_serial)

Dependencias:
- zeep: Cliente SOAP robusto
- aiohttp: HTTP async client  
- lxml: Procesamiento XML
- pydantic: Validación de datos
- structlog: Logging estructurado

Cumplimiento:
- Manual Técnico SIFEN v150
- TLS 1.2 obligatorio
- Códigos de error oficiales SET
- Logging sin datos sensibles
"""

from .client import SifenSOAPClient
from .document_sender import DocumentSender
from .response_parser import SifenResponseParser
from .error_handler import SifenErrorHandler
from .retry_manager import RetryManager
from .models import (
    DocumentRequest,
    SifenResponse,
    BatchRequest,
    DocumentStatus
)
from .exceptions import (
    SifenClientError,
    SifenConnectionError,
    SifenValidationError,
    SifenServerError,
    SifenRetryExhaustedError
)
from .config import SifenConfig

# Versión del módulo alineada con SIFEN v150
__version__ = "1.5.0"

# Exportaciones principales para uso externo
__all__ = [
    # Cliente principal
    "DocumentSender",
    "SifenSOAPClient",

    # Configuración
    "SifenConfig",

    # Modelos de datos
    "DocumentRequest",
    "SifenResponse",
    "BatchRequest",
    "DocumentStatus",

    # Componentes internos (para testing/extensión)
    "SifenResponseParser",
    "SifenErrorHandler",
    "RetryManager",

    # Excepciones
    "SifenClientError",
    "SifenConnectionError",
    "SifenValidationError",
    "SifenServerError",
    "SifenRetryExhaustedError",

    # Metadatos
    "__version__"
]

# Configuración de logging por defecto
import logging
import structlog

# Configurar structlog para el módulo
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Logger para el módulo
logger = structlog.get_logger(__name__)

# Log de inicialización del módulo
logger.info(
    "sifen_client_module_loaded",
    version=__version__,
    components=[
        "SifenSOAPClient",
        "DocumentSender",
        "ResponseParser",
        "ErrorHandler",
        "RetryManager"
    ]
)
