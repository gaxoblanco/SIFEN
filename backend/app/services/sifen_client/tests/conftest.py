"""
Configuración de pytest para tests del módulo sifen_client

Resuelve problemas de importación, configura el entorno de testing
automáticamente y proporciona fixtures robustas.
"""

import logging
import asyncio
import sys
import os
from pathlib import Path
import pytest

# Resolver path de importación
# Agregar la raíz del proyecto al sys.path
current_file = Path(__file__)
# Subir 5 niveles hasta la raíz
project_root = current_file.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# También agregar el directorio backend al path
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))


def pytest_configure(config):
    """Configuración personalizada de pytest"""
    config.addinivalue_line(
        "markers", "integration: marca tests de integración con SIFEN"
    )
    config.addinivalue_line(
        "markers", "slow: marca tests lentos que pueden tardar >30s"
    )
    config.addinivalue_line(
        "markers", "unit: marca tests unitarios rápidos"
    )
    config.addinivalue_line(
        "markers", "asyncio: marca tests asíncronos"
    )


def pytest_collection_modifyitems(config, items):
    """Configurar pytest-asyncio automáticamente"""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Configuración automática del ambiente de tests

    Se ejecuta una vez por sesión de tests y configura todo
    automáticamente sin requerir variables de entorno externas.
    """
    print(f"\n🔧 Configurando ambiente de tests automáticamente...")
    print(f"   Directorio actual: {os.getcwd()}")
    print(f"   Raíz del proyecto: {project_root}")

    # Verificar que podemos importar los módulos
    try:
        from app.services.sifen_client.config import SifenConfig
        print("   ✅ Importación de módulos exitosa")
    except ImportError as e:
        print(f"   ❌ Error importando módulos: {e}")
        pytest.skip("No se pueden importar los módulos del proyecto")

    # Configurar ambiente de test automáticamente
    try:
        from app.services.sifen_client.tests.fixtures.test_config import get_test_environment

        # Crear ambiente de test
        test_env = get_test_environment("pytest_session")

        print(f"   ✅ Ambiente de test configurado:")
        print(f"      RUC: {test_env.ruc_emisor}")
        print(f"      Certificado: {test_env.mock_cert_path.name}")
        print(f"      Ambiente SIFEN: {test_env.sifen_config.environment}")
        print(f"      Base URL: {test_env.sifen_config.effective_base_url}")

        # El ambiente se limpia automáticamente al final
        yield test_env

        # Cleanup al final de la sesión
        test_env.cleanup()
        print("   🧹 Ambiente de test limpiado")

    except ImportError as e:
        print(f"   ⚠️ No se pudo configurar ambiente automático: {e}")
        print("   📝 Usando configuración manual de variables de entorno")

        # Fallback: configurar variables mínimas si no existen
        if not os.getenv('SIFEN_TEST_RUC'):
            os.environ['SIFEN_TEST_RUC'] = '80016875-5'
        if not os.getenv('SIFEN_TEST_CERT_SERIAL'):
            os.environ['SIFEN_TEST_CERT_SERIAL'] = '1A2B3C4D5E6F7890ABCDEF1234567890'
        if not os.getenv('SIFEN_TEST_CERT_PATH'):
            os.environ['SIFEN_TEST_CERT_PATH'] = '/tmp/mock_cert.p12'

        yield None


@pytest.fixture
def test_environment(setup_test_environment):
    """
    Fixture que proporciona ambiente de test a los tests individuales

    Uso:
        def test_algo(test_environment):
            config = test_environment.sifen_config
            ruc = test_environment.ruc_emisor
    """
    if setup_test_environment:
        return setup_test_environment
    else:
        # Fallback: crear ambiente mínimo
        from app.services.sifen_client.tests.fixtures.test_config import get_test_environment
        return get_test_environment("individual_test")


@pytest.fixture
def sifen_test_config(test_environment):
    """Configuración SIFEN optimizada para tests"""
    if test_environment:
        return test_environment.sifen_config
    else:
        # Fallback
        from app.services.sifen_client.config import SifenConfig
        return SifenConfig(environment="test")


@pytest.fixture
def test_certificate_info(test_environment):
    """Información del certificado de prueba"""
    if test_environment:
        return {
            'serial_number': test_environment.cert_serial,
            'cert_path': test_environment.cert_path,
            'password': test_environment.cert_password,
            'ruc_emisor': test_environment.ruc_emisor
        }
    else:
        # Fallback
        return {
            'serial_number': os.getenv('SIFEN_TEST_CERT_SERIAL', '1A2B3C4D5E6F7890'),
            'cert_path': os.getenv('SIFEN_TEST_CERT_PATH', '/tmp/test.p12'),
            'password': os.getenv('SIFEN_TEST_CERT_PASSWORD', 'test123'),
            'ruc_emisor': os.getenv('SIFEN_TEST_RUC', '80016875-5')
        }


@pytest.fixture
def mock_responses(test_environment):
    """Respuestas mock de SIFEN para tests"""
    if test_environment:
        from app.services.sifen_client.tests.fixtures.test_config import get_mock_responses
        return get_mock_responses()
    else:
        # Fallback: respuestas básicas
        return {
            'send_document_success': {
                'success': True,
                'code': '0260',
                'message': 'Aprobado',
                'cdc': '01800695631001001000000612021112917595714694'
            }
        }


@pytest.fixture
def skip_integration_if_no_connection():
    """
    Skip tests de integración si no hay conectividad con SIFEN

    Uso:
        @pytest.mark.integration
        def test_real_sifen(skip_integration_if_no_connection):
            # Test que requiere SIFEN real
    """
    try:
        import requests
        response = requests.get("https://sifen-test.set.gov.py", timeout=5)
        if response.status_code not in [200, 403, 404]:
            pytest.skip("No hay conectividad con SIFEN test")
    except Exception:
        pytest.skip("No hay conectividad con SIFEN test")


# Configuración de logging para tests
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Suprimir logs verbosos durante tests
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Configurar logging específico para tests
test_logger = logging.getLogger('sifen_tests')
test_logger.setLevel(logging.DEBUG)
