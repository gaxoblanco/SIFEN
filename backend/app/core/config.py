"""
Configuración centralizada de la aplicación SIFEN.

Este módulo maneja toda la configuración de la aplicación usando Pydantic Settings,
incluyendo variables de entorno, configuración de SIFEN, JWT, CORS, etc.

Configuraciones incluidas:
- Base de datos PostgreSQL
- Autenticación JWT
- Configuración SIFEN (URLs, certificados)
- CORS y seguridad
- Logging
- Configuración por ambiente (dev, test, prod)

Autor: Sistema SIFEN
Fecha: 2024
"""

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):
    """
    Configuración principal de la aplicación.

    Usa Pydantic Settings para validación automática y carga desde
    variables de entorno con fallbacks seguros.
    """

    # === CONFIGURACIÓN GENERAL ===
    PROJECT_NAME: str = "SIFEN Facturación Electrónica"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Ambiente de ejecución
    ENVIRONMENT: str = Field(
        default="development", description="Ambiente: development, testing, production")
    DEBUG: bool = Field(default=False, description="Habilitar modo debug")

    # === CONFIGURACIÓN DE BASE DE DATOS ===
    DATABASE_URL: str = Field(
        default="postgresql://sifen_user:sifen_password@localhost:5432/sifen_dev",
        description="URL de conexión a PostgreSQL"
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Habilitar logging de queries SQL"
    )

    # === CONFIGURACIÓN JWT ===
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Clave secreta para firmar tokens JWT"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="Algoritmo JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Minutos de expiración del access token"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Días de expiración del refresh token"
    )

    # === CONFIGURACIÓN CORS ===
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = Field(
        default_factory=lambda: [
            "http://localhost:3000",    # React dev
            "http://127.0.0.1:3000",   # React dev alternate
            "http://localhost:8080",    # Vue dev
        ],
        description="Orígenes permitidos para CORS"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Convierte string separado por comas en lista."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # === CONFIGURACIÓN SIFEN ===

    # URLs del servicio SIFEN
    SIFEN_BASE_URL_TEST: str = Field(
        default="https://sifen-test.set.gov.py",
        description="URL base SIFEN ambiente test"
    )
    SIFEN_BASE_URL_PROD: str = Field(
        default="https://sifen.set.gov.py",
        description="URL base SIFEN ambiente producción"
    )

    # Configuración ambiente SIFEN actual
    SIFEN_ENVIRONMENT: str = Field(
        default="test",
        description="Ambiente SIFEN: 'test' o 'prod'"
    )

    @field_validator("SIFEN_ENVIRONMENT")
    @classmethod
    def validate_sifen_environment(cls, v):
        """Valida que el ambiente SIFEN sea válido."""
        if v not in ["test", "prod"]:
            raise ValueError("SIFEN_ENVIRONMENT debe ser 'test' o 'prod'")
        return v

    # Configuración de certificados
    CERTIFICATES_PATH: Path = Field(
        default=Path("certificates"),
        description="Directorio de certificados digitales"
    )

    # Timeouts y reintentos
    SIFEN_TIMEOUT_SECONDS: int = Field(
        default=30, description="Timeout SIFEN en segundos")
    SIFEN_MAX_RETRIES: int = Field(
        default=3, description="Máximo reintentos SIFEN")
    SIFEN_RETRY_DELAY: int = Field(
        default=5, description="Delay entre reintentos SIFEN")

    # === CONFIGURACIÓN DE ARCHIVOS ===
    UPLOAD_PATH: Path = Field(
        default=Path("uploads"),
        description="Directorio para archivos subidos"
    )
    MAX_FILE_SIZE_MB: int = Field(
        default=10, description="Tamaño máximo archivo en MB")

    # === CONFIGURACIÓN DE LOGGING ===
    LOG_LEVEL: str = Field(default="INFO", description="Nivel de logging")
    LOG_FILE_PATH: Optional[Path] = Field(
        default=Path("logs/app.log"),
        description="Ruta del archivo de log"
    )
    LOG_ROTATION: str = Field(
        default="1 day",
        description="Rotación de logs (ej: '1 day', '100 MB')"
    )

    # === CONFIGURACIÓN REDIS (para caché y sessions) ===
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="URL de conexión a Redis"
    )
    REDIS_PASSWORD: Optional[str] = Field(
        default=None, description="Password Redis")

    # === CONFIGURACIÓN EMAIL ===
    SMTP_SERVER: Optional[str] = Field(
        default=None, description="Servidor SMTP")
    SMTP_PORT: int = Field(default=587, description="Puerto SMTP")
    SMTP_USERNAME: Optional[str] = Field(
        default=None, description="Usuario SMTP")
    SMTP_PASSWORD: Optional[str] = Field(
        default=None, description="Password SMTP")
    SMTP_TLS: bool = Field(default=True, description="Usar TLS en SMTP")
    FROM_EMAIL: Optional[str] = Field(
        default=None, description="Email remitente")

    # === CONFIGURACIÓN DE SEGURIDAD ===
    PASSWORD_MIN_LENGTH: int = Field(
        default=8, description="Longitud mínima password")
    PASSWORD_REQUIRE_SPECIAL: bool = Field(
        default=True, description="Requerir caracteres especiales")
    SESSION_TIMEOUT_MINUTES: int = Field(
        default=60, description="Timeout sesión en minutos")

    # === CONFIGURACIÓN DE RATE LIMITING ===
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=100, description="Rate limit por minuto")
    RATE_LIMIT_BURST: int = Field(default=200, description="Rate limit burst")

    # === PROPIEDADES COMPUTADAS ===

    @property
    def sifen_base_url(self) -> str:
        """Retorna la URL base de SIFEN según el ambiente configurado."""
        return (
            self.SIFEN_BASE_URL_PROD
            if self.SIFEN_ENVIRONMENT == "prod"
            else self.SIFEN_BASE_URL_TEST
        )

    @property
    def is_development(self) -> bool:
        """Indica si está en ambiente de desarrollo."""
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        """Indica si está en ambiente de testing."""
        return self.ENVIRONMENT == "testing"

    @property
    def is_production(self) -> bool:
        """Indica si está en ambiente de producción."""
        return self.ENVIRONMENT == "production"

    # === VALIDACIONES ===

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Valida que la clave JWT sea segura."""
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY debe tener al menos 32 caracteres")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Valida el formato de la URL de base de datos."""
        if not v.startswith(("postgresql://", "sqlite:///")):
            raise ValueError(
                "DATABASE_URL debe comenzar con postgresql:// o sqlite:///")
        return v

    # === CONFIGURACIÓN DE PATHS ===

    def model_post_init(self, __context: Any) -> None:
        """Inicializa configuración y crea directorios necesarios."""
        self._create_directories()

    def _create_directories(self):
        """Crea directorios necesarios si no existen."""
        directories = [
            self.CERTIFICATES_PATH,
            self.UPLOAD_PATH,
        ]

        # Crear directorio de logs si está configurado
        if self.LOG_FILE_PATH:
            directories.append(self.LOG_FILE_PATH.parent)

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    # === CONFIGURACIÓN PYDANTIC ===

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid"  # No permitir campos extra
    )

# === CONFIGURACIONES ESPECÍFICAS POR AMBIENTE ===


class DevelopmentSettings(Settings):
    """Configuración específica para desarrollo."""
    DEBUG: bool = True
    DATABASE_ECHO: bool = True
    LOG_LEVEL: str = "DEBUG"


class TestingSettings(Settings):
    """Configuración específica para testing."""
    ENVIRONMENT: str = "testing"
    DATABASE_URL: str = "sqlite:///./test.db"
    JWT_SECRET_KEY: str = "test-secret-key-32-characters-long"
    RATE_LIMIT_PER_MINUTE: int = 1000  # Sin límites en testing


class ProductionSettings(Settings):
    """Configuración específica para producción."""
    DEBUG: bool = False
    DATABASE_ECHO: bool = False
    SIFEN_ENVIRONMENT: str = "prod"
    LOG_LEVEL: str = "INFO"

# === FACTORY DE CONFIGURACIÓN ===


@lru_cache()
def get_settings() -> Settings:
    """
    Factory para obtener configuración según ambiente.

    Usa @lru_cache para singleton pattern.

    Returns:
        Settings: Instancia de configuración apropiada
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    elif environment == "development":
        return DevelopmentSettings()
    else:
        return Settings()

# === INSTANCIA GLOBAL ===


# Instancia principal de configuración
settings = get_settings()

# === UTILIDADES DE CONFIGURACIÓN ===


def get_database_url_for_environment(env: str) -> str:
    """
    Obtiene la URL de BD para un ambiente específico.

    Args:
        env: Ambiente (development, testing, production)

    Returns:
        str: URL de conexión a BD
    """
    urls = {
        "development": "postgresql://sifen_user:sifen_password@localhost:5432/sifen_dev",
        "testing": "sqlite:///./test.db",
        "production": os.getenv("DATABASE_URL_PROD", "")
    }
    return urls.get(env, urls["development"])


def print_config_summary():
    """Imprime un resumen de la configuración actual (sin datos sensibles)."""
    print(f"""
🔧 CONFIGURACIÓN SIFEN
=====================
Proyecto: {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}
Ambiente: {settings.ENVIRONMENT}
Debug: {settings.DEBUG}
Base de Datos: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'SQLite'}
SIFEN Ambiente: {settings.SIFEN_ENVIRONMENT}
SIFEN URL: {settings.sifen_base_url}
Log Level: {settings.LOG_LEVEL}
CORS Origins: {len(settings.BACKEND_CORS_ORIGINS)} configurados
    """)

# === VALIDACIÓN AL IMPORTAR ===


if __name__ == "__main__":
    # Ejecutar al importar para validar configuración
    print_config_summary()

    # Validar configuraciones críticas
    critical_settings = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
    ]

    for setting in critical_settings:
        value = getattr(settings, setting)
        if not value:
            raise ValueError(f"Configuración crítica faltante: {setting}")

    print("✅ Configuración validada correctamente")
