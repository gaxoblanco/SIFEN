"""
Módulo cliente SIFEN para Paraguay

Proporciona integración con el Sistema Integrado de Facturación Electrónica Nacional (SIFEN).

Componentes principales:
- SifenClient: Cliente principal para envío de documentos
- SifenConfig: Configuración del cliente
- Modelos: Estructuras de datos para requests/responses
- Validadores: Validación de documentos y respuestas

Ejemplo de uso:
    from app.services.sifen_client import SifenClient, SifenConfig
    
    config = SifenConfig(environment="test")
    client = SifenClient(config)
    
    # Enviar documento
    response = client.send_document(request)
"""

from .client import SifenClient, create_sifen_client
from .config import SifenConfig, create_default_config, load_config, get_config
from .models import (
    # Request/Response models
    SifenRequest,
    SifenResponse,
    BatchSifenRequest,
    BatchSifenResponse,
    QueryDocumentRequest,
    QueryDocumentResponse,

    # Configuration models
    SifenClientConfig,
    RetryConfig,

    # Enums
    SifenEnvironment,
    DocumentType,
    SifenResponseCode,

    # Exceptions
    SifenError,
    SifenConnectionError,
    SifenTimeoutError,
    SifenValidationError,
    SifenAuthenticationError
)

# Versión del módulo
__version__ = "1.0.0"

# Exportar componentes principales
__all__ = [
    # Client
    "SifenClient",
    "create_sifen_client",

    # Configuration
    "SifenConfig",
    "SifenClientConfig",
    "RetryConfig",
    "create_default_config",
    "load_config",
    "get_config",

    # Request/Response Models
    "SifenRequest",
    "SifenResponse",
    "BatchSifenRequest",
    "BatchSifenResponse",
    "QueryDocumentRequest",
    "QueryDocumentResponse",

    # Enums
    "SifenEnvironment",
    "DocumentType",
    "SifenResponseCode",

    # Exceptions
    "SifenError",
    "SifenConnectionError",
    "SifenTimeoutError",
    "SifenValidationError",
    "SifenAuthenticationError",

    # Metadata
    "__version__"
]
