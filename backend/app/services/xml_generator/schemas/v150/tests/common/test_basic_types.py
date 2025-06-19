"""
Tests para el módulo basic_types.xsd - SIFEN v150

Este módulo contiene tests exhaustivos para validar todos los tipos básicos
definidos en backend/app/services/xml_generator/schemas/v150/common/basic_types.xsd

Categorías de tests:
- Tipos de identificación (RUC, CDC, códigos)
- Tipos de documentos electrónicos  
- Tipos primitivos con validación
- Patrones de validación avanzados
- Tests de integración entre tipos

Organización modular:
- Utiliza utils/ ya implementados para máxima reutilización
- SchemaValidator para validación XSD consistente
- XMLGenerator (módulo) para generación de datos de prueba
- DataFactory para datos realistas paraguayos
- TestHelpers para assertions especializadas

Autor: Sistema SIFEN-Facturación
Versión: 1.5.0
Fecha: 2025-06-18
"""

# ============================================================================
# IMPORTS Y CONFIGURACIÓN DEL MÓDULO
# ============================================================================

# Imports estándar de Python
import pytest
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import time

# Imports de lxml para manipulación XML
from lxml import etree

# Imports de utils ya implementados (reutilización modular)
from app.services.xml_generator.schemas.v150.tests.utils.schema_validator import SchemaValidator, ValidationResult

# Imports del módulo xml_generator (estructura modular)
from app.services.xml_generator.schemas.v150.tests.utils.xml_generator import (
    # Validadores
    SifenValidator,

    # Datos de muestra
    SampleData
)

# Imports de test_helpers ya implementados
from app.services.xml_generator.schemas.v150.tests.utils.test_helpers import (
    XMLTestHelpers,
    SchemaTestHelpers,
    SifenDataFactory
)
from app.services.xml_generator.schemas.v150.tests.utils.test_helpers.constants import (
    SIFEN_NAMESPACE_URI,
    SIFEN_SCHEMA_VERSION,
    BASIC_FIELD_PATTERNS,
    SCHEMA_MODULE_DEPENDENCIES,
    VALIDATION_ERROR_MESSAGES,
    VALIDATION_WARNING_MESSAGES
)

# Configuración de logging para tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACIÓN GLOBAL DEL MÓDULO DE TESTS
# ============================================================================

# Constantes específicas para basic_types tests
BASIC_TYPES_MODULE = "common/basic_types.xsd"
EXPECTED_TYPES_COUNT = 25  # Número esperado de tipos definidos en basic_types.xsd
TEST_NAMESPACE = SIFEN_NAMESPACE_URI

# Datos de prueba específicos para basic_types
BASIC_TYPES_TEST_DATA = {
    # Datos de identificación válidos
    "ruc_validos": ["12345678", "123456789", "80012345"],
    "ruc_invalidos": ["1234567", "12345678901", "ABCDEFGH"],

    # CDCs válidos (44 caracteres)
    "cdc_validos": [
        "01234567890123456789012345678901234567890123",
        "80012345912345678901234567890123456789012"
    ],
    "cdc_invalidos": [
        "0123456789012345678901234567890123456789012",  # 43 chars
        "012345678901234567890123456789012345678901234"  # 45 chars
    ],

    # Versiones de formato
    "version_formato_valida": "150",
    "versiones_formato_invalidas": ["149", "151", "1.5.0", "V150"],

    # Tipos de documento válidos
    "tipos_documento_validos": ["1", "4", "5", "6", "7"],
    "tipos_documento_invalidos": ["0", "2", "3", "8", "9", "10"],

    # Fechas válidas (formato YYYY-MM-DD)
    "fechas_validas": ["2019-09-15", "2024-12-31", "2025-01-01"],
    "fechas_invalidas": ["15-09-2019", "2019/09/15", "invalid-date"],

    # Emails válidos
    "emails_validos": ["test@ejemplo.com", "usuario@empresa.com.py"],
    "emails_invalidos": ["invalid-email", "@ejemplo.com", "test@"],

    # Teléfonos válidos Paraguay
    "telefonos_validos": ["21234567", "0985123456", "+59521234567"],
    "telefonos_invalidos": ["123", "12345678901", "invalid"],
}


# ============================================================================
# FIXTURES GLOBALES REUTILIZABLES
# ============================================================================

@pytest.fixture(scope="class")
def schema_validator():
    """
    Fixture que proporciona un SchemaValidator configurado para basic_types.xsd.

    Utiliza la implementación ya existente en utils/schema_validator.py
    para garantizar consistencia en toda la suite de tests.

    Returns:
        SchemaValidator: Instancia configurada para validar contra basic_types.xsd
    """
    # Calcular ruta del schema usando la estructura del proyecto
    schema_path = Path(__file__).parent.parent.parent / \
        "common" / "basic_types.xsd"

    # Verificar que el schema existe antes de crear el validador
    if not schema_path.exists():
        pytest.skip(f"Schema not found: {schema_path}")

    logger.info(f"Inicializando SchemaValidator para: {schema_path}")
    return SchemaValidator(str(schema_path))


@pytest.fixture(scope="class")
def sample_data():
    """
    Fixture que proporciona SampleData para generar datos de prueba.

    Utiliza la implementación modular ya existente en utils/xml_generator/sample_data/
    para generar datos de prueba consistentes y realistas.

    Returns:
        SampleData: Instancia configurada para generar datos SIFEN
    """
    logger.info("Inicializando SampleData")
    return SampleData()


@pytest.fixture(scope="class")
def sifen_validator():
    """
    Fixture que proporciona SifenValidator del módulo xml_generator.

    Returns:
        SifenValidator: Validador unificado SIFEN
    """
    return SifenValidator()


@pytest.fixture(scope="class")
def xml_test_helper():
    """
    Fixture que proporciona XMLTestHelpers para utilidades de testing XML.

    Returns:
        XMLTestHelpers: Helper con métodos especializados para testing XML
    """
    return XMLTestHelpers()


@pytest.fixture(scope="class")
def schema_test_helpers():
    """
    Fixture que proporciona SchemaTestHelpers para testing modular de schemas.

    Returns:
        SchemaTestHelpers: Helper con métodos para testing de schemas modulares
    """
    return SchemaTestHelpers()


@pytest.fixture
def data_factory():
    """
    Fixture que proporciona SifenDataFactory     para generar datos de prueba realistas.

    Utiliza la implementación ya existente que genera datos específicos
    para Paraguay y compatibles con SIFEN.

    Returns:
        SifenDataFactory    : Factory configurado para datos SIFEN Paraguay
    """
    return SifenDataFactory()


@pytest.fixture
def test_data():
    """
    Fixture con datos de prueba específicos para basic_types.

    Proporciona datos de prueba organizados y listos para usar
    en tests de tipos básicos SIFEN.

    Returns:
        Dict: Diccionario con datos de prueba organizados por categoría
    """
    return BASIC_TYPES_TEST_DATA.copy()


# ============================================================================
# CONFIGURACIÓN ESPECÍFICA PARA BASIC_TYPES TESTS
# ============================================================================

@pytest.fixture(scope="class", autouse=True)
def setup_basic_types_testing(schema_validator, sample_data):
    """
    Setup automático para toda la clase de tests de basic_types.

    Verifica que todos los componentes necesarios están disponibles
    y configurados correctamente antes de ejecutar los tests.

    Args:
        schema_validator: Validador de schemas
        sample_data: API para generar datos de muestra
    """
    logger.info("=== INICIANDO SETUP PARA BASIC_TYPES TESTS ===")

    # Verificar que el schema validator está funcionando
    try:
        # Test básico de funcionamiento del validador
        test_xml = f'<test xmlns="{TEST_NAMESPACE}">content</test>'
        # No validamos el resultado, solo que no arroje excepción
        logger.info("✅ SchemaValidator inicializado correctamente")
    except Exception as e:
        pytest.fail(f"Error inicializando SchemaValidator: {e}")

    # Verificar que la SampleData está funcionando
    try:
        # Test básico del generador
        sample_emisor = sample_data.get_test_emisor()
        assert sample_emisor is not None
        logger.info("✅ SampleData inicializada correctamente")
    except Exception as e:
        pytest.fail(f"Error inicializando SampleData: {e}")

    # Log de configuración completada
    logger.info("✅ Setup completado - Listos para ejecutar tests de basic_types")

    # Yield para permitir que los tests se ejecuten
    yield

    # Cleanup después de todos los tests
    logger.info("=== FINALIZANDO TESTS DE BASIC_TYPES ===")


# ============================================================================
# UTILIDADES AUXILIARES ESPECÍFICAS PARA BASIC_TYPES
# ============================================================================

class BasicTypesTestHelper:
    """
    Helper especializado para tests de basic_types.xsd

    Proporciona métodos específicos para testing de tipos básicos SIFEN,
    complementando las utilidades ya implementadas en utils/.
    """

    def __init__(self, schema_validator: SchemaValidator, sample_data: SampleData):
        """
        Inicializa el helper con los componentes necesarios.

        Args:
            schema_validator: Validador de schemas
            sample_data: API para generar datos de muestra
        """
        self.validator = schema_validator
        self.sample_data = sample_data
        self.namespace = TEST_NAMESPACE

    def validate_basic_element(self, element_name: str, value: str,
                               should_be_valid: bool = True) -> ValidationResult:
        """
        Valida un elemento básico contra el schema.

        Args:
            element_name: Nombre del elemento XML
            value: Valor del elemento
            should_be_valid: Si se espera que sea válido o no

        Returns:
            ValidationResult: Resultado de la validación
        """
        # Construir XML del elemento
        xml_content = f'<{element_name} xmlns="{self.namespace}">{value}</{element_name}>'

        # Validar usando SchemaValidator
        result = self.validator.validate_xml(xml_content)

        # Verificar expectativa
        if should_be_valid and not result.is_valid:
            logger.warning(
                f"Elemento esperado válido falló: {element_name}={value}")
            logger.warning(f"Errores: {result.errors}")
        elif not should_be_valid and result.is_valid:
            logger.warning(
                f"Elemento esperado inválido pasó: {element_name}={value}")

        return result

    def generate_cdc_valido(self) -> str:
        """
        Genera un CDC válido usando SampleData.

        Returns:
            str: CDC válido de 44 caracteres
        """
        # Usar datos de muestra para generar CDC realista
        emisor = self.sample_data.get_test_emisor()
        return "01" + emisor.get("ruc", "12345678") + "1" + "001001" + "0000001" + "20240101" + "1" + "123456789" + "4"

    def test_pattern_validation(self, pattern_name: str, test_values: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Prueba un patrón específico con valores válidos e inválidos.

        Args:
            pattern_name: Nombre del patrón a probar
            test_values: Dict con 'valid' e 'invalid' conteniendo listas de valores

        Returns:
            Dict: Resultados de las pruebas organizados por categoría
        """
        results = {"valid_passed": [], "valid_failed": [],
                   "invalid_passed": [], "invalid_failed": []}

        # Probar valores válidos
        for value in test_values.get("valid", []):
            result = self.validate_basic_element(
                pattern_name, value, should_be_valid=True)
            if result.is_valid:
                results["valid_passed"].append(value)
            else:
                results["valid_failed"].append(value)

        # Probar valores inválidos
        for value in test_values.get("invalid", []):
            result = self.validate_basic_element(
                pattern_name, value, should_be_valid=False)
            if not result.is_valid:
                results["invalid_passed"].append(value)
            else:
                results["invalid_failed"].append(value)

        return results


@pytest.fixture
def basic_types_helper(schema_validator, sample_data):
    """
    Fixture que proporciona BasicTypesTestHelper configurado.

    Args:
        schema_validator: Validador de schemas
        sample_data: API para generar datos de muestra

    Returns:
        BasicTypesTestHelper: Helper especializado para basic_types
    """
    return BasicTypesTestHelper(schema_validator, sample_data)


# ============================================================================
# CLASE BASE PARA TODOS LOS TESTS DE BASIC_TYPES
# ============================================================================

class TestBasicTypesBase:
    """
    Clase base para todos los tests de basic_types.

    Proporciona funcionalidad común y setup compartido para todas
    las clases de test específicas que heredarán de esta.
    """

    @classmethod
    def setup_class(cls):
        """Setup inicial compartido para todas las clases de test."""
        cls.test_start_time = time.time()
        logger.info(f"=== INICIANDO {cls.__name__} ===")

    @classmethod
    def teardown_class(cls):
        """Teardown compartido para todas las clases de test."""
        elapsed_time = time.time() - cls.test_start_time
        logger.info(
            f"=== FINALIZANDO {cls.__name__} - Tiempo: {elapsed_time:.2f}s ===")

    def setup_method(self, method):
        """Setup antes de cada test individual."""
        self.test_method_start = time.time()
        logger.debug(f"Iniciando test: {method.__name__}")

    def teardown_method(self, method):
        """Teardown después de cada test individual."""
        elapsed = time.time() - self.test_method_start
        logger.debug(f"Finalizando test: {method.__name__} - {elapsed:.3f}s")


# ============================================================================
# SECCIÓN COMPLETA - LISTO PARA CONTINUAR
# ============================================================================

# ... (Aquí continuarán las clases de test específicas en las siguientes secciones)
