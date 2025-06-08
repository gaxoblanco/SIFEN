"""
Configuración del cliente SIFEN

Maneja configuración centralizadas para:
- URLs de ambiente (test/producción)  
- Timeouts y reintentos
- Configuración SSL/TLS
- Variables de entorno
- Parámetros de conexión HTTP
"""

import os
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
from pydantic import BaseModel, Field, field_validator


class SifenConfig(BaseModel):
    """
    Configuración central del cliente SIFEN

    Soporta tanto configuración manual como desde variables de entorno.
    """

    # Ambiente SIFEN
    environment: str = Field(
        "test", description="Ambiente SIFEN (test/production)")
    base_url: Optional[str] = Field(
        None, description="URL base manual (opcional)")

    # Timeouts
    timeout: float = Field(30.0, description="Timeout general en segundos")
    connect_timeout: float = Field(10.0, description="Timeout de conexión")
    read_timeout: float = Field(30.0, description="Timeout de lectura")

    # Reintentos
    max_retries: int = Field(3, description="Máximo número de reintentos")
    backoff_factor: float = Field(
        1.0, description="Factor de backoff exponencial")
    retry_status_codes: List[int] = Field(
        default=[500, 502, 503, 504], description="Códigos HTTP para retry")

    # SSL/TLS
    verify_ssl: bool = Field(True, description="Verificar certificados SSL")
    client_cert_path: Optional[str] = Field(
        None, description="Path del certificado cliente")
    client_cert_password: Optional[str] = Field(
        None, description="Password del certificado cliente")

    # Pool de conexiones HTTP
    pool_connections: int = Field(10, description="Conexiones en pool")
    pool_maxsize: int = Field(20, description="Tamaño máximo del pool")

    # Headers HTTP
    user_agent: str = Field("SIFEN-Client-Python/1.0",
                            description="User-Agent")
    content_type: str = Field(
        "text/xml; charset=utf-8", description="Content-Type")

    # Logging y debugging
    log_level: str = Field("INFO", description="Nivel de logging")
    log_requests: bool = Field(True, description="Loggear requests HTTP")
    log_responses: bool = Field(False, description="Loggear responses HTTP")

    # Performance
    enable_compression: bool = Field(
        True, description="Habilitar compresión gzip")

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validar que el ambiente sea válido"""
        valid_envs = ['test', 'production', 'development', 'staging']
        if v.lower() not in valid_envs:
            raise ValueError(f"Ambiente debe ser uno de: {valid_envs}")
        return v.lower()

    @field_validator('timeout', 'connect_timeout', 'read_timeout')
    @classmethod
    def validate_timeouts(cls, v: float) -> float:
        """Validar que los timeouts sean positivos"""
        if v <= 0:
            raise ValueError("Timeouts deben ser positivos")
        if v > 300:  # 5 minutos máximo
            raise ValueError("Timeout máximo es 300 segundos")
        return v

    @field_validator('max_retries')
    @classmethod
    def validate_retries(cls, v: int) -> int:
        """Validar número de reintentos"""
        if v < 0:
            raise ValueError("Reintentos no pueden ser negativos")
        if v > 10:
            raise ValueError("Máximo 10 reintentos permitidos")
        return v

    @property
    def effective_base_url(self) -> str:
        """
        URL base efectiva según ambiente o configuración manual
        """
        if self.base_url:
            return self.base_url

        # URLs oficiales SIFEN
        urls = {
            'test': 'https://sifen-test.set.gov.py',
            'production': 'https://sifen.set.gov.py',
            'development': 'http://localhost:8080',  # Para mocks locales
            'staging': 'https://sifen-staging.set.gov.py'  # Si existe
        }

        return urls.get(self.environment, urls['test'])

    @property
    def send_document_url(self) -> str:
        """URL para envío de documentos individuales"""
        return urljoin(self.effective_base_url, '/de/ws/sync/recibe.wsdl')

    @property
    def send_batch_url(self) -> str:
        """URL para envío de lotes de documentos"""
        return urljoin(self.effective_base_url, '/de/ws/async/recibe-lote.wsdl')

    @property
    def query_document_url(self) -> str:
        """URL para consulta de documentos"""
        return urljoin(self.effective_base_url, '/de/ws/consultas/consulta.wsdl')

    @property
    def query_ruc_url(self) -> str:
        """URL para consulta de RUC"""
        return urljoin(self.effective_base_url, '/de/ws/consultas/consulta-ruc.wsdl')

    @property
    def is_production(self) -> bool:
        """Indica si está en ambiente de producción"""
        return self.environment == 'production'

    @property
    def is_test(self) -> bool:
        """Indica si está en ambiente de test"""
        return self.environment == 'test'

    def get_request_headers(self) -> Dict[str, str]:
        """
        Headers estándar para requests HTTP
        """
        headers = {
            'User-Agent': self.user_agent,
            'Content-Type': self.content_type,
            'Accept': 'text/xml, application/xml',
            'Accept-Charset': 'utf-8',
            'Connection': 'keep-alive'
        }

        if self.enable_compression:
            headers['Accept-Encoding'] = 'gzip, deflate'

        return headers

    def get_ssl_context(self):
        """
        Configuración SSL/TLS para requests
        """
        import ssl

        if not self.verify_ssl:
            # Para tests - SSL permisivo
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context

        # Para producción - SSL estricto
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Certificado cliente si está configurado
        if self.client_cert_path:
            context.load_cert_chain(
                self.client_cert_path,
                password=self.client_cert_password
            )

        return context

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario"""
        return self.model_dump()

    @classmethod
    def from_env(cls, env_prefix: str = "SIFEN_") -> "SifenConfig":
        """
        Crea configuración desde variables de entorno

        Args:
            env_prefix: Prefijo para variables de entorno

        Examples:
            SIFEN_ENVIRONMENT=test
            SIFEN_TIMEOUT=60
            SIFEN_MAX_RETRIES=5
        """
        config_data = {}

        # Mapeo de variables de entorno a campos del modelo
        env_mapping = {
            'ENVIRONMENT': 'environment',
            'BASE_URL': 'base_url',
            'TIMEOUT': 'timeout',
            'CONNECT_TIMEOUT': 'connect_timeout',
            'READ_TIMEOUT': 'read_timeout',
            'MAX_RETRIES': 'max_retries',
            'BACKOFF_FACTOR': 'backoff_factor',
            'VERIFY_SSL': 'verify_ssl',
            'CLIENT_CERT_PATH': 'client_cert_path',
            'CLIENT_CERT_PASSWORD': 'client_cert_password',
            'POOL_CONNECTIONS': 'pool_connections',
            'POOL_MAXSIZE': 'pool_maxsize',
            'USER_AGENT': 'user_agent',
            'LOG_LEVEL': 'log_level',
            'LOG_REQUESTS': 'log_requests',
            'LOG_RESPONSES': 'log_responses',
            'ENABLE_COMPRESSION': 'enable_compression'
        }

        for env_key, field_name in env_mapping.items():
            env_var = f"{env_prefix}{env_key}"
            value = os.getenv(env_var)

            if value is not None:
                # Convertir tipos según el campo
                if field_name in ['timeout', 'connect_timeout', 'read_timeout', 'backoff_factor']:
                    config_data[field_name] = float(value)
                elif field_name in ['max_retries', 'pool_connections', 'pool_maxsize']:
                    config_data[field_name] = int(value)
                elif field_name in ['verify_ssl', 'log_requests', 'log_responses', 'enable_compression']:
                    config_data[field_name] = value.lower() in (
                        'true', '1', 'yes', 'on')
                else:
                    config_data[field_name] = value

        return cls(**config_data)

    def __str__(self) -> str:
        """Representación string de la configuración (sin datos sensibles)"""
        safe_fields = [
            'environment', 'effective_base_url', 'timeout',
            'max_retries', 'verify_ssl', 'log_level'
        ]

        safe_data = {field: getattr(self, field) for field in safe_fields}
        return f"SifenConfig({safe_data})"


def create_default_config(environment: str = "test") -> SifenConfig:
    """
    Crea una configuración por defecto para el ambiente especificado

    Args:
        environment: Ambiente SIFEN (test/production)

    Returns:
        SifenConfig configurado con valores por defecto
    """
    # Configuraciones específicas por ambiente
    env_configs = {
        'test': {
            'environment': 'test',
            'timeout': 30.0,
            'max_retries': 2,
            'verify_ssl': False,  # Más permisivo en test
            'log_level': 'DEBUG',
            'log_requests': True,
            'log_responses': True
        },
        'production': {
            'environment': 'production',
            'timeout': 60.0,
            'max_retries': 3,
            'verify_ssl': True,
            'log_level': 'INFO',
            'log_requests': True,
            'log_responses': False  # No loggear responses en prod
        }
    }

    config_data = env_configs.get(environment, env_configs['test'])
    return SifenConfig(**config_data)


def load_config() -> SifenConfig:
    """
    Carga configuración automáticamente desde variables de entorno
    con fallback a valores por defecto

    Returns:
        SifenConfig configurado desde env o defaults
    """
    try:
        # Intentar cargar desde variables de entorno
        config = SifenConfig.from_env()

        # Si no hay variables de entorno, usar defaults
        if config.environment == "test":  # Default value
            env = os.getenv('SIFEN_ENVIRONMENT', 'test')
            config = create_default_config(env)

        return config

    except Exception:
        # Fallback total a configuración de test
        return create_default_config('test')


# Instancia global de configuración (lazy-loaded)
_config_instance: Optional[SifenConfig] = None


def get_config() -> SifenConfig:
    """
    Obtiene la instancia global de configuración

    Returns:
        SifenConfig: Configuración global cargada
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = load_config()

    return _config_instance


def set_config(config: SifenConfig) -> None:
    """
    Establece una configuración personalizada globalmente

    Args:
        config: Nueva configuración a usar
    """
    global _config_instance
    _config_instance = config


def reset_config() -> None:
    """
    Resetea la configuración global (útil para tests)
    """
    global _config_instance
    _config_instance = None


# Configuraciones predefinidas para casos comunes
DEVELOPMENT_CONFIG = SifenConfig(
    environment="development",
    base_url="http://localhost:8080",
    timeout=10.0,
    max_retries=1,
    verify_ssl=False,
    log_level="DEBUG",
    connect_timeout=5.0,
    read_timeout=10.0,
    backoff_factor=1.0,
    pool_connections=5,
    pool_maxsize=10,
    user_agent="SIFEN-Client-Python/1.0",
    content_type="text/xml; charset=utf-8",
    log_requests=True,
    log_responses=True,
    enable_compression=True,
    client_cert_path=None,
    client_cert_password=None
)

INTEGRATION_TEST_CONFIG = SifenConfig(
    environment="test",
    timeout=60.0,
    max_retries=3,
    verify_ssl=True,
    log_level="INFO",
    base_url=None,
    connect_timeout=10.0,
    read_timeout=30.0,
    backoff_factor=1.0,
    pool_connections=10,
    pool_maxsize=20,
    user_agent="SIFEN-Client-Python/1.0",
    content_type="text/xml; charset=utf-8",
    log_requests=True,
    log_responses=True,
    enable_compression=True,
    client_cert_path=None,
    client_cert_password=None
)

UNIT_TEST_CONFIG = SifenConfig(
    environment="test",
    base_url="http://localhost:8080",
    timeout=5.0,
    max_retries=0,
    verify_ssl=False,
    log_level="ERROR",
    connect_timeout=2.0,
    read_timeout=5.0,
    backoff_factor=1.0,
    pool_connections=1,
    pool_maxsize=1,
    user_agent="SIFEN-Client-Python/1.0",
    content_type="text/xml; charset=utf-8",
    log_requests=True,
    log_responses=True,
    enable_compression=False,
    client_cert_path=None,
    client_cert_password=None
)

PRODUCTION_CONFIG = SifenConfig(
    environment="production",
    timeout=90.0,
    max_retries=5,
    verify_ssl=True,
    log_level="WARNING",
    log_responses=False,
    base_url=None,
    connect_timeout=15.0,
    read_timeout=60.0,
    backoff_factor=2.0,
    pool_connections=20,
    pool_maxsize=40,
    user_agent="SIFEN-Client-Python/1.0",
    content_type="text/xml; charset=utf-8",
    log_requests=True,
    enable_compression=True,
    client_cert_path=None,
    client_cert_password=None
)
