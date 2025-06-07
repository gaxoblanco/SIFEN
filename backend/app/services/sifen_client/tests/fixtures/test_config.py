"""
Configuración automática para tests del módulo sifen_client

Proporciona configuración de test robusta que funciona sin variables
de entorno externas, simulando un ambiente de desarrollo real.

Funcionalidades:
- Variables de entorno automáticas para tests
- Configuración SIFEN optimizada para testing
- Certificados mock realistas
- Paths de archivos simulados
- Configuración de timeouts rápidos para tests

Uso:
    # Los tests automáticamente usan esta configuración
    from .fixtures.test_config import get_test_environment
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Imports del módulo
from app.services.sifen_client.config import SifenConfig


@dataclass
class SifenTestEnvironment:
    """
    Ambiente de test completo con todos los datos necesarios
    """
    # Variables de entorno simuladas
    cert_serial: str
    ruc_emisor: str
    cert_path: str
    cert_password: str

    # Configuración SIFEN optimizada
    sifen_config: SifenConfig

    # Paths y archivos de test
    temp_dir: Path
    mock_cert_path: Path

    # Metadatos del test
    test_name: str
    created_at: datetime

    def cleanup(self):
        """Limpia archivos temporales creados para el test"""
        try:
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass  # Ignorar errores de cleanup


class SifenTestConfigManager:
    """
    Gestor de configuración para tests

    Proporciona configuración automática y realista para tests
    sin requerir variables de entorno externas.
    """

    def __init__(self):
        self._current_env: Optional[SifenTestEnvironment] = None
        self._base_temp_dir = Path(tempfile.gettempdir()) / "sifen_tests"
        self._base_temp_dir.mkdir(exist_ok=True)

    def get_test_environment(self, test_name: str = "default") -> SifenTestEnvironment:
        """
        Crea un ambiente de test completo y realista

        Args:
            test_name: Nombre del test para identificación

        Returns:
            TestEnvironment configurado y listo para usar
        """
        # Crear directorio temporal único para este test
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        test_dir = self._base_temp_dir / f"{test_name}_{timestamp}"
        test_dir.mkdir(exist_ok=True)

        # Crear archivo de certificado mock
        mock_cert_path = test_dir / "test_certificate.p12"
        self._create_mock_certificate_file(mock_cert_path)

        # Datos de test realistas (basados en ambiente SIFEN test oficial)
        cert_serial = "1A2B3C4D5E6F7890ABCDEF1234567890"  # Formato real
        ruc_emisor = "80016875-5"  # RUC oficial para ambiente test SIFEN
        cert_password = "test123456"

        # Configuración SIFEN optimizada para tests
        sifen_config = SifenConfig(
            environment="test",
            base_url="https://sifen-test.set.gov.py",
            timeout=10,  # Timeout corto para tests rápidos
            connect_timeout=5,
            read_timeout=15,
            max_retries=1,  # Menos reintentos en tests
            backoff_factor=0.1,  # Retry rápido
            verify_ssl=False,  # Más permisivo en tests
            log_level="DEBUG",
            pool_connections=5,
            pool_maxsize=10,
            enable_compression=False  # Menos overhead en tests
        )

        # Crear ambiente completo
        env = SifenTestEnvironment(
            cert_serial=cert_serial,
            ruc_emisor=ruc_emisor,
            cert_path=str(mock_cert_path),
            cert_password=cert_password,
            sifen_config=sifen_config,
            temp_dir=test_dir,
            mock_cert_path=mock_cert_path,
            test_name=test_name,
            created_at=datetime.now()
        )

        # Configurar variables de entorno automáticamente
        self._set_environment_variables(env)

        self._current_env = env
        return env

    def _create_mock_certificate_file(self, cert_path: Path):
        """
        Crea un archivo de certificado mock para tests

        No es un certificado real, pero simula la estructura
        necesaria para que los tests no fallen.
        """
        # Contenido mock que simula un archivo PKCS#12
        mock_cert_content = b"""
-----BEGIN MOCK CERTIFICATE-----
MIIDMjCCAhqgAwIBAgIJAK+eYZ5FZGAAMA0GCSqGSIb3DQEBCwUAMDExCzAJBgNV
BAYTAlBZMQwwCgYDVQQIDANBU1AxFDAKBgNVBAcMA0FTVTEOMAwGA1UECgwFVEVT
VDEPMA0GA1UEAwwGVEVTVF9DQTAUFRQMA1VFU1QxCzAJBgNVBAYTAlBZMB4XDTI0
MDEwMTAwMDAwMFoXDTI1MTIzMTIzNTk1OVowMTELMAkGA1UEBhMCUFkxDDAKBgNV
BAgMA0FTUDEPMA0GA1UEBwwGQVNVTkNJT04xDjAMBgNVBAoMBVRFU1QxDzANBgNV
BAMMBlRFU1RfQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC+TEST
CERTIFICATE+FOR+SIFEN+TESTING+ONLY+DO+NOT+USE+IN+PRODUCTION
-----END MOCK CERTIFICATE-----
""".strip()

        cert_path.write_bytes(mock_cert_content)

    def _set_environment_variables(self, env: SifenTestEnvironment):
        """
        Configura las variables de entorno necesarias para los tests
        """
        env_vars = {
            'SIFEN_TEST_CERT_SERIAL': env.cert_serial,
            'SIFEN_TEST_RUC': env.ruc_emisor,
            'SIFEN_TEST_CERT_PATH': env.cert_path,
            'SIFEN_TEST_CERT_PASSWORD': env.cert_password,
            'SIFEN_ENVIRONMENT': 'test',
            'SIFEN_BASE_URL': env.sifen_config.effective_base_url,
            'SIFEN_TIMEOUT': str(env.sifen_config.timeout),
            'SIFEN_MAX_RETRIES': str(env.sifen_config.max_retries),
            'SIFEN_VERIFY_SSL': str(env.sifen_config.verify_ssl).lower(),
            'SIFEN_LOG_LEVEL': env.sifen_config.log_level
        }

        for key, value in env_vars.items():
            os.environ[key] = value

    def cleanup_current_environment(self):
        """Limpia el ambiente actual"""
        if self._current_env:
            self._current_env.cleanup()
            self._current_env = None

    def get_mock_responses(self) -> Dict[str, Any]:
        """
        Retorna respuestas mock de SIFEN para diferentes escenarios

        Returns:
            Dict con respuestas simuladas por tipo de operación
        """
        return {
            'send_document_success': {
                'success': True,
                'code': '0260',
                'message': 'Aprobado',
                'cdc': '01800695631001001000000612021112917595714694',
                'protocol_number': 'PROT_TEST_123456',
                'document_status': 'APPROVED',
                'processing_time_ms': 1500
            },
            'send_document_error_ruc': {
                'success': False,
                'code': '1250',
                'message': 'RUC emisor inexistente',
                'errors': ['El RUC del emisor no existe en la base de datos']
            },
            'send_document_error_cdc': {
                'success': False,
                'code': '1000',
                'message': 'CDC no corresponde con XML',
                'errors': ['El CDC generado no coincide con el contenido del XML']
            },
            'query_document_success': {
                'success': True,
                'code': '0260',
                'message': 'Consulta exitosa',
                'documents': [
                    {
                        'cdc': '01800695631001001000000612021112917595714694',
                        'status': 'approved',
                        'emission_date': '2024-01-01T10:00:00',
                        'total_amount': 110000
                    }
                ],
                'total_found': 1
            },
            'batch_success': {
                'success': True,
                'code': '0260',
                'message': 'Lote procesado exitosamente',
                'batch_id': 'BATCH_TEST_123',
                'total_documents': 3,
                'processed_documents': 3,
                'failed_documents': 0
            }
        }

    def get_test_certificates(self) -> Dict[str, Any]:
        """
        Retorna información de certificados de test

        Returns:
            Dict con datos de certificados simulados
        """
        return {
            'valid_certificate': {
                'serial_number': self._current_env.cert_serial if self._current_env else "1A2B3C4D5E6F7890",
                'subject': 'CN=TEST CERTIFICATE, O=TESTING, C=PY',
                'issuer': 'CN=PSC TEST CA, O=PSC, C=PY',
                'valid_from': '2024-01-01T00:00:00Z',
                'valid_to': '2025-12-31T23:59:59Z',
                'key_usage': ['digital_signature', 'key_encipherment'],
                'is_valid': True
            },
            'expired_certificate': {
                'serial_number': 'EXPIRED123456789',
                'subject': 'CN=EXPIRED CERT, O=TESTING, C=PY',
                'valid_from': '2020-01-01T00:00:00Z',
                'valid_to': '2023-12-31T23:59:59Z',
                'is_valid': False,
                'error': 'Certificate has expired'
            },
            'invalid_certificate': {
                'serial_number': 'INVALID123456789',
                'subject': 'CN=INVALID CERT, O=TESTING, C=PY',
                'is_valid': False,
                'error': 'Certificate not issued by authorized CA'
            }
        }


# ========================================
# INSTANCIA GLOBAL PARA FÁCIL USO
# ========================================

_test_config_manager = SifenTestConfigManager()


def get_test_environment(test_name: str = "default") -> SifenTestEnvironment:
    """
    Función helper para obtener ambiente de test configurado

    Args:
        test_name: Nombre identificador del test

    Returns:
        TestEnvironment listo para usar
    """
    return _test_config_manager.get_test_environment(test_name)


def cleanup_test_environment():
    """Limpia el ambiente de test actual"""
    _test_config_manager.cleanup_current_environment()


def get_mock_responses() -> Dict[str, Any]:
    """Obtiene respuestas mock de SIFEN"""
    return _test_config_manager.get_mock_responses()


def get_test_certificates() -> Dict[str, Any]:
    """Obtiene certificados de test"""
    return _test_config_manager.get_test_certificates()


# ========================================
# CONFIGURACIONES PREDEFNIDAS
# ========================================

def get_integration_test_config() -> SifenConfig:
    """
    Configuración optimizada para tests de integración

    Returns:
        SifenConfig con parámetros seguros para tests
    """
    return SifenConfig(
        environment="test",
        base_url="https://sifen-test.set.gov.py",
        timeout=30,  # Más tiempo para tests de integración real
        max_retries=2,
        verify_ssl=True,  # Más estricto para integración
        log_level="INFO",
        backoff_factor=0.5
    )


def get_unit_test_config() -> SifenConfig:
    """
    Configuración optimizada para tests unitarios

    Returns:
        SifenConfig con parámetros rápidos para tests unitarios
    """
    return SifenConfig(
        environment="test",
        base_url="http://localhost:8080",  # Mock server local
        timeout=5,
        max_retries=0,  # Sin reintentos en tests unitarios
        verify_ssl=False,
        log_level="ERROR",  # Menos logs en tests unitarios
        backoff_factor=0.1
    )


def get_performance_test_config() -> SifenConfig:
    """
    Configuración optimizada para tests de rendimiento

    Returns:
        SifenConfig optimizado para medir performance
    """
    return SifenConfig(
        environment="test",
        timeout=60,
        max_retries=0,  # Sin reintentos para medir tiempo real
        pool_connections=50,
        pool_maxsize=100,
        enable_compression=True,
        log_level="WARNING"
    )


# ========================================
# CONSTANTES ÚTILES PARA TESTS
# ========================================

# RUC oficial para ambiente test de SIFEN
TEST_RUC_EMISOR = "80016875-5"

# Número de timbrado de prueba
TEST_TIMBRADO = "12345678"

# CDCs de ejemplo válidos
TEST_CDCS = [
    "01800695631001001000000612021112917595714694",
    "01800695631001001000000612021112917595714695",
    "01800695631001001000000612021112917595714696"
]

# URLs de servicios SIFEN test
SIFEN_TEST_ENDPOINTS = {
    'sync_receive': 'https://sifen-test.set.gov.py/de/ws/sync/recibe.wsdl',
    'async_batch': 'https://sifen-test.set.gov.py/de/ws/async/recibe-lote.wsdl',
    'query_document': 'https://sifen-test.set.gov.py/de/ws/consultas/consulta.wsdl',
    'query_ruc': 'https://sifen-test.set.gov.py/de/ws/consultas/consulta-ruc.wsdl'
}

# Códigos de respuesta SIFEN más comunes en tests
COMMON_SIFEN_CODES = {
    'success': '0260',           # Aprobado
    'success_with_obs': '1005',  # Aprobado con observaciones
    'cdc_mismatch': '1000',      # CDC no corresponde
    'duplicate_cdc': '1001',     # CDC duplicado
    'invalid_timbrado': '1101',  # Timbrado inválido
    'ruc_not_found': '1250',     # RUC inexistente
    'invalid_signature': '0141',  # Firma digital inválida
    'server_error': '5000'       # Error interno del servidor
}
