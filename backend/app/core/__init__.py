"""
Módulo core del sistema SIFEN.

Este módulo contiene la funcionalidad central de la aplicación:
- Configuración de la aplicación
- Conexión a base de datos
- Autenticación y seguridad
- Manejo de excepciones

Componentes principales:
- config: Configuración centralizada con Pydantic
- database: Conexión SQLAlchemy y sesiones
- security: JWT, hashing, autenticación
- exceptions: Jerarquía de errores del dominio SIFEN

Autor: Sistema SIFEN
Fecha: 2024
"""

# Importaciones principales para facilitar el uso
from .config import settings, get_settings
from .database import (
    Base,
    SessionLocal,
    engine,
    get_db,
    get_db_context,
    test_connection,
    get_db_health,
    create_all_tables,
    drop_all_tables
)
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_user_tokens,
    get_current_user_token,
    get_current_user_optional,
    require_scopes,
    require_admin,
    require_user,
    TokenData,
    Token,
    UserInToken,
    security_health_check
)
from .exceptions import (
    # Excepciones base
    SifenBaseException,

    # Validación
    SifenValidationError,
    SifenRUCValidationError,
    SifenCDCValidationError,

    # Base de datos
    SifenDatabaseError,
    SifenEntityNotFoundError,
    SifenDuplicateEntityError,

    # Autenticación/Autorización
    SifenAuthenticationError,
    SifenAuthorizationError,
    SifenInvalidTokenError,
    SifenTokenExpiredError,

    # Lógica de negocio
    SifenBusinessLogicError,
    SifenDocumentStateError,
    SifenTimbradoError,
    SifenNumerationError,

    # Servicios externos
    SifenExternalServiceError,
    SifenAPIError,
    SifenXMLError,
    SifenCertificateError,
    SifenSignatureError,

    # Configuración
    SifenConfigurationError,
    SifenEnvironmentError,

    # Utilidades
    handle_database_exception,
    handle_validation_exception,
    handle_external_service_exception,
    handle_exceptions,
    get_http_status_for_exception
)

# Versión del módulo core
__version__ = "1.0.0"

# Exports para import directo
__all__ = [
    # Config
    "settings",
    "get_settings",

    # Database
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "get_db_context",
    "test_connection",
    "get_db_health",
    "create_all_tables",
    "drop_all_tables",

    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "create_user_tokens",
    "get_current_user_token",
    "get_current_user_optional",
    "require_scopes",
    "require_admin",
    "require_user",
    "TokenData",
    "Token",
    "UserInToken",
    "security_health_check",

    # Exceptions - Base
    "SifenBaseException",

    # Exceptions - Validación
    "SifenValidationError",
    "SifenRUCValidationError",
    "SifenCDCValidationError",

    # Exceptions - Database
    "SifenDatabaseError",
    "SifenEntityNotFoundError",
    "SifenDuplicateEntityError",

    # Exceptions - Auth
    "SifenAuthenticationError",
    "SifenAuthorizationError",
    "SifenInvalidTokenError",
    "SifenTokenExpiredError",

    # Exceptions - Business
    "SifenBusinessLogicError",
    "SifenDocumentStateError",
    "SifenTimbradoError",
    "SifenNumerationError",

    # Exceptions - External
    "SifenExternalServiceError",
    "SifenAPIError",
    "SifenXMLError",
    "SifenCertificateError",
    "SifenSignatureError",

    # Exceptions - Config
    "SifenConfigurationError",
    "SifenEnvironmentError",

    # Exception utilities
    "handle_database_exception",
    "handle_validation_exception",
    "handle_external_service_exception",
    "handle_exceptions",
    "get_http_status_for_exception",
]

# Funciones de inicialización del módulo


def initialize_core():
    """
    Inicializa el módulo core.

    Ejecuta verificaciones básicas y setup necesario.
    """
    # Verificar configuración crítica
    if not test_connection():
        raise SifenConfigurationError("No se pudo conectar a la base de datos")

    # Verificar sistema de seguridad
    health = security_health_check()
    if health["status"] != "healthy":
        raise SifenConfigurationError(
            f"Sistema de seguridad no saludable: {health}")

    print("✅ Módulo core inicializado correctamente")


def get_core_health() -> dict:
    """
    Obtiene el estado de salud de todos los componentes core.

    Returns:
        dict: Estado de salud completo del módulo core
    """
    return {
        "database": get_db_health(),
        "security": security_health_check(),
        "config": {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "sifen_environment": settings.SIFEN_ENVIRONMENT
        }
    }
