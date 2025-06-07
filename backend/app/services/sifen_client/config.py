"""
Configuración específica del módulo SIFEN Client

Maneja toda la configuración para la comunicación con SIFEN:
- Endpoints de producción y testing
- Configuración TLS 1.2 obligatorio
- Timeouts y reintentos
- Certificados SSL
- Parámetros de performance

Basado en:
- Manual Técnico SIFEN v150
- Especificaciones TLS 1.2
- Best practices para clients SOAP
"""

import os
import ssl
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import structlog

# Logger para configuración
logger = structlog.get_logger(__name__)


@dataclass
class SifenEndpoints:
    """
    Endpoints oficiales SIFEN según Manual Técnico v150

    Estructura de URLs:
    - Base: https://sifen.set.gov.py/ (prod) | https://sifen-test.set.gov.py/ (test)
    - Servicios: /de/ws/[tipo]/[servicio].wsdl
    """

    # URLs base
    PRODUCTION_BASE = "https://sifen.set.gov.py"
    TEST_BASE = "https://sifen-test.set.gov.py"

    # Servicios individuales (sync)
    SYNC_RECEIVE = "/de/ws/sync/recibe.wsdl"

    # Servicios de lote (async)
    ASYNC_RECEIVE_BATCH = "/de/ws/async/recibe-lote.wsdl"
    ASYNC_QUERY_BATCH = "/de/ws/async/consulta-lote.wsdl"

    # Servicios de consulta
    QUERY_DOCUMENT = "/de/ws/consultas/consulta.wsdl"
    QUERY_RUC = "/de/ws/consultas/consulta-ruc.wsdl"

    # Servicios de eventos
    EVENTS_RECEIVE = "/de/ws/eventos/evento.wsdl"

    @classmethod
    def get_full_url(cls, base_url: str, service_path: str) -> str:
        """
        Construye URL completa para un servicio

        Args:
            base_url: URL base (prod o test)
            service_path: Path del servicio (ej: /de/ws/sync/recibe.wsdl)

        Returns:
            URL completa del servicio
        """
        return f"{base_url.rstrip('/')}{service_path}"


class SifenConfig(BaseModel):
    """
    Configuración principal del cliente SIFEN

    Maneja todos los parámetros necesarios para la comunicación
    segura y robusta con SIFEN Paraguay.
    """

    # ==========================================
    # CONFIGURACIÓN DE AMBIENTE
    # ==========================================

    environment: str = Field(
        default="test",
        description="Ambiente: 'test' o 'production'"
    )

    base_url: Optional[str] = Field(
        default=None,
        description="URL base personalizada (sobrescribe environment)"
    )

    # ==========================================
    # CONFIGURACIÓN DE RED
    # ==========================================

    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout en segundos para requests HTTP"
    )

    connect_timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Timeout en segundos para establecer conexión"
    )

    read_timeout: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Timeout en segundos para leer respuesta"
    )

    # ==========================================
    # CONFIGURACIÓN TLS/SSL
    # ==========================================

    verify_ssl: bool = Field(
        default=True,
        description="Verificar certificados SSL (obligatorio para producción)"
    )

    ssl_cert_path: Optional[str] = Field(
        default=None,
        description="Path al certificado cliente SSL (si requerido)"
    )

    ssl_key_path: Optional[str] = Field(
        default=None,
        description="Path a la clave privada SSL (si requerido)"
    )

    tls_version: str = Field(
        default="1.2",
        description="Versión TLS mínima (SIFEN requiere 1.2+)"
    )

    # ==========================================
    # CONFIGURACIÓN DE REINTENTOS
    # ==========================================

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Número máximo de reintentos"
    )

    backoff_factor: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Factor de backoff exponencial (segundos base)"
    )

    retry_status_codes: List[int] = Field(
        default_factory=lambda: [500, 502, 503, 504, 408],
        description="Códigos HTTP que activan retry"
    )

    retry_on_timeout: bool = Field(
        default=True,
        description="Reintentar en caso de timeout"
    )

    # ==========================================
    # CONFIGURACIÓN DE LOGGING
    # ==========================================

    log_requests: bool = Field(
        default=True,
        description="Loggear requests HTTP (sin datos sensibles)"
    )

    log_responses: bool = Field(
        default=True,
        description="Loggear responses HTTP (sin datos sensibles)"
    )

    log_level: str = Field(
        default="INFO",
        description="Nivel de logging: DEBUG, INFO, WARNING, ERROR"
    )

    # ==========================================
    # CONFIGURACIÓN DE PERFORMANCE
    # ==========================================

    pool_connections: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Número de conexiones en pool"
    )

    pool_maxsize: int = Field(
        default=20,
        ge=1,
        le=200,
        description="Tamaño máximo del pool de conexiones"
    )

    enable_compression: bool = Field(
        default=True,
        description="Habilitar compresión gzip en requests"
    )

    # ==========================================
    # VALIDADORES
    # ==========================================

    @field_validator('environment')
    def validate_environment(cls, v):
        """Valida que el ambiente sea correcto"""
        if v not in ['test', 'production']:
            raise ValueError("environment debe ser 'test' o 'production'")
        return v

    @field_validator('tls_version')
    def validate_tls_version(cls, v):
        """Valida versión TLS (SIFEN requiere 1.2+)"""
        valid_versions = ['1.2', '1.3']
        if v not in valid_versions:
            raise ValueError(f"tls_version debe ser una de: {valid_versions}")
        return v

    @field_validator('verify_ssl')
    def validate_ssl_for_production(cls, v, info):
        """SSL verificación obligatoria en producción"""
        if info.data.get('environment') == 'production' and not v:
            raise ValueError("verify_ssl debe ser True en producción")
        return v

    # ==========================================
    # PROPIEDADES COMPUTADAS
    # ==========================================

    @property
    def effective_base_url(self) -> str:
        """
        Retorna la URL base efectiva según configuración

        Prioridad:
        1. base_url personalizada
        2. URL según environment
        """
        if self.base_url:
            return self.base_url

        if self.environment == "production":
            return SifenEndpoints.PRODUCTION_BASE
        else:
            return SifenEndpoints.TEST_BASE

    @property
    def ssl_context(self) -> ssl.SSLContext:
        """
        Crea contexto SSL configurado según especificaciones SIFEN

        Returns:
            Contexto SSL con TLS 1.2+ y validaciones apropiadas
        """
        context = ssl.create_default_context()

        # TLS 1.2 mínimo (requerido por SIFEN)
        if self.tls_version == "1.2":
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        elif self.tls_version == "1.3":
            context.minimum_version = ssl.TLSVersion.TLSv1_3

        # Configuración de verificación
        if self.verify_ssl:
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        # Certificado cliente (si está configurado)
        if self.ssl_cert_path and self.ssl_key_path:
            context.load_cert_chain(
                certfile=self.ssl_cert_path,
                keyfile=self.ssl_key_path
            )

        return context

    def get_service_url(self, service_path: str) -> str:
        """
        Obtiene URL completa para un servicio específico

        Args:
            service_path: Path del servicio (ej: SifenEndpoints.SYNC_RECEIVE)

        Returns:
            URL completa del servicio
        """
        return SifenEndpoints.get_full_url(self.effective_base_url, service_path)

    def get_retry_delays(self) -> List[float]:
        """
        Calcula los delays para reintentos con backoff exponencial

        Returns:
            Lista de delays en segundos: [1.0, 2.0, 4.0] para max_retries=3
        """
        return [
            self.backoff_factor * (2 ** i)
            for i in range(self.max_retries)
        ]

    # ==========================================
    # CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
    # ==========================================

    @classmethod
    def from_env(cls) -> 'SifenConfig':
        """
        Crea configuración desde variables de entorno

        Variables soportadas:
        - SIFEN_ENVIRONMENT: test|production
        - SIFEN_BASE_URL: URL base personalizada
        - SIFEN_TIMEOUT: timeout en segundos
        - SIFEN_MAX_RETRIES: número máximo de reintentos
        - SIFEN_VERIFY_SSL: true|false
        - SIFEN_LOG_LEVEL: DEBUG|INFO|WARNING|ERROR

        Returns:
            Instancia configurada desde environment
        """
        env_config = {
            'environment': os.getenv('SIFEN_ENVIRONMENT', 'test'),
            'base_url': os.getenv('SIFEN_BASE_URL'),
            'timeout': int(os.getenv('SIFEN_TIMEOUT', '30')),
            'max_retries': int(os.getenv('SIFEN_MAX_RETRIES', '3')),
            'verify_ssl': os.getenv('SIFEN_VERIFY_SSL', 'true').lower() == 'true',
            'log_level': os.getenv('SIFEN_LOG_LEVEL', 'INFO'),
            'ssl_cert_path': os.getenv('SIFEN_SSL_CERT_PATH'),
            'ssl_key_path': os.getenv('SIFEN_SSL_KEY_PATH'),
        }

        # Filtrar valores None
        env_config = {k: v for k, v in env_config.items() if v is not None}

        logger.info(
            "sifen_config_from_env",
            environment=env_config.get('environment'),
            has_custom_url=bool(env_config.get('base_url')),
            verify_ssl=env_config.get('verify_ssl'),
            timeout=env_config.get('timeout')
        )

        return cls(**env_config)

    def model_dump_safe(self) -> Dict[str, Any]:
        """
        Serializa configuración ocultando datos sensibles

        Returns:
            Dict con configuración sin passwords/paths sensibles
        """
        data = self.model_dump()

        # Ocultar paths sensibles
        if data.get('ssl_cert_path'):
            data['ssl_cert_path'] = f"***{Path(data['ssl_cert_path']).name}"
        if data.get('ssl_key_path'):
            data['ssl_key_path'] = f"***{Path(data['ssl_key_path']).name}"

        return data


# ==========================================
# CONFIGURACIONES PREDEFINIDAS
# ==========================================

def get_test_config() -> SifenConfig:
    """
    Configuración optimizada para ambiente de testing

    Returns:
        SifenConfig configurado para SIFEN test
    """
    return SifenConfig(
        environment="test",
        timeout=30,
        max_retries=2,
        verify_ssl=True,  # Mantener SSL en test también
        log_level="DEBUG",
        backoff_factor=0.5  # Retry más rápido en test
    )


def get_production_config() -> SifenConfig:
    """
    Configuración optimizada para ambiente de producción

    Returns:
        SifenConfig configurado para SIFEN producción
    """
    return SifenConfig(
        environment="production",
        timeout=60,
        max_retries=3,
        verify_ssl=True,  # Obligatorio en producción
        log_level="INFO",
        backoff_factor=1.0,
        pool_connections=20,
        pool_maxsize=50
    )


# Configuración por defecto
DEFAULT_CONFIG = get_test_config()

logger.info(
    "sifen_config_module_loaded",
    default_environment=DEFAULT_CONFIG.environment,
    endpoints_available=[
        "sync_receive",
        "async_batch",
        "query_document",
        "query_ruc",
        "events"
    ]
)
