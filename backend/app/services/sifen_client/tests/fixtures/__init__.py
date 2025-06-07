"""
Fixtures para tests del módulo sifen_client

Este paquete contiene todas las fixtures, datos de prueba,
configuraciones y mocks necesarios para testing.

Módulos disponibles:
- test_config: Configuración automática de ambiente
- test_documents: Documentos XML de prueba
- test_certificates: Certificados mock
- test_responses: Respuestas SIFEN simuladas

Uso rápido:
    from .test_config import get_test_environment
    from .test_documents import get_valid_factura_xml
"""

# Exports principales para fácil acceso
from .test_config import (
    get_test_environment,
    get_mock_responses,
    get_test_certificates,
    cleanup_test_environment,
    TEST_RUC_EMISOR,
    COMMON_SIFEN_CODES
)

try:
    from .test_documents import (
        get_valid_factura_xml,
        get_valid_nota_credito_xml,
        validate_xml_structure,
        TEST_CERTIFICATE_DATA
    )
except ImportError:
    # test_documents.py puede no estar disponible aún
    pass

__all__ = [
    # Configuración
    'get_test_environment',
    'cleanup_test_environment',

    # Mocks y respuestas
    'get_mock_responses',
    'get_test_certificates',

    # Documentos (si disponible)
    'get_valid_factura_xml',
    'get_valid_nota_credito_xml',
    'validate_xml_structure',

    # Constantes
    'TEST_RUC_EMISOR',
    'COMMON_SIFEN_CODES'
]
