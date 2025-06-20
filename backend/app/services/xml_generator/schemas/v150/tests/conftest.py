"""
Configuración compartida para tests de schemas SIFEN v150

Este conftest.py proporciona fixtures reutilizables, configuración de pytest
y utilidades comunes para todos los tests de validación de schemas XSD.

Responsabilidades:
- Configurar markers de pytest
- Proporcionar fixtures de validators
- Gestionar paths de schemas
- Configurar logging para tests
- Proporcionar datos de prueba comunes

Autor: Sistema SIFEN
Versión: 1.0.0
Fecha: 2025-06-20
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pytest

# =====================================================================
# CONFIGURACIÓN DE PATHS Y IMPORTS
# =====================================================================

# Resolver paths de importación automáticamente
current_file = Path(__file__)
# Subir a la raíz del proyecto: tests/ -> v150/ -> schemas/ -> xml_generator/ -> services/ -> app/ -> backend/
backend_root = current_file.parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_root))

# Agregar path específico para imports
utils_path = current_file.parent / "utils"
sys.path.insert(0, str(utils_path))

# =====================================================================
# CONFIGURACIÓN DE PYTEST
# =====================================================================


def pytest_configure(config):
    """Configuración de markers y settings de pytest para schemas"""
    # Markers para categorizar tests de schemas
    config.addinivalue_line("markers", "basic: tests de tipos básicos")
    config.addinivalue_line("markers", "contact: tests de tipos de contacto")
    config.addinivalue_line(
        "markers", "geographic: tests de tipos geográficos")
    config.addinivalue_line("markers", "currency: tests de tipos monetarios")
    config.addinivalue_line("markers", "business: tests de lógica de negocio")
    config.addinivalue_line("markers", "core: tests del schema principal")

    # Markers por velocidad/complejidad
    config.addinivalue_line("markers", "fast: tests rápidos < 100ms")
    config.addinivalue_line("markers", "slow: tests lentos > 1s")
    config.addinivalue_line(
        "markers", "integration: tests de integración entre schemas")
    config.addinivalue_line("markers", "regression: tests de regresión")

    # Markers por tipo de validación
    config.addinivalue_line("markers", "xsd: tests de validación XSD")
    config.addinivalue_line("markers", "pattern: tests de patrones regex")
    config.addinivalue_line("markers", "structure: tests de estructura XML")


def pytest_collection_modifyitems(config, items):
    """Configuración automática de items de test"""
    for item in items:
        # Auto-marcar tests por nombre del archivo
        if "basic" in item.fspath.basename:
            item.add_marker(pytest.mark.basic)
        elif "contact" in item.fspath.basename:
            item.add_marker(pytest.mark.contact)
        elif "geographic" in item.fspath.basename:
            item.add_marker(pytest.mark.geographic)
        elif "currency" in item.fspath.basename:
            item.add_marker(pytest.mark.currency)
        elif "business" in item.fspath.basename:
            item.add_marker(pytest.mark.business)
        elif "core" in item.fspath.basename:
            item.add_marker(pytest.mark.core)


# =====================================================================
# CONFIGURACIÓN DE LOGGING
# =====================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Configuración automática de logging para tests de schemas"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Logger específico para tests de schemas
    logger = logging.getLogger("schemas_tests")
    logger.setLevel(logging.INFO)

    return logger


# =====================================================================
# FIXTURES DE PATHS Y CONFIGURACIÓN
# =====================================================================

@pytest.fixture(scope="session")
def schemas_base_path():
    """Ruta base a los schemas SIFEN v150"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def schemas_common_path(schemas_base_path):
    """Ruta a schemas comunes (common/)"""
    return schemas_base_path / "common"


@pytest.fixture(scope="session")
def schemas_document_path(schemas_base_path):
    """Ruta a schemas de documentos (document_core/)"""
    return schemas_base_path / "document_core"


@pytest.fixture(scope="session")
def main_schema_path(schemas_base_path):
    """Ruta al schema principal DE_v150.xsd"""
    return schemas_base_path / "DE_v150.xsd"


# =====================================================================
# FIXTURES DE VALIDADORES
# =====================================================================

@pytest.fixture(scope="session")
def schema_validator_factory():
    """Factory para crear SchemaValidators para diferentes schemas"""
    def _create_validator(schema_name: str):
        """
        Crea un SchemaValidator para el schema especificado

        Args:
            schema_name: Nombre del archivo schema (ej: "common/basic_types.xsd")

        Returns:
            SchemaValidator inicializado
        """
        try:
            from app.services.xml_generator.schemas.v150.tests.utils.schema_validator import SchemaValidator

            # Construir path completo
            if not schema_name.startswith("app/"):
                schema_path = f"app/services/xml_generator/schemas/v150/{schema_name}"
            else:
                schema_path = schema_name

            return SchemaValidator(schema_path)
        except ImportError as e:
            pytest.skip(f"SchemaValidator no disponible: {e}")

    return _create_validator


@pytest.fixture(scope="class")
def basic_types_validator(schema_validator_factory):
    """Validator específico para basic_types.xsd"""
    return schema_validator_factory("common/basic_types.xsd")


@pytest.fixture(scope="class")
def contact_types_validator(schema_validator_factory):
    """Validator específico para contact_types.xsd"""
    return schema_validator_factory("common/contact_types.xsd")


@pytest.fixture(scope="class")
def geographic_types_validator(schema_validator_factory):
    """Validator específico para geographic_types.xsd"""
    return schema_validator_factory("common/geographic_types.xsd")


@pytest.fixture(scope="class")
def main_schema_validator(schema_validator_factory):
    """Validator para el schema principal DE_v150.xsd"""
    return schema_validator_factory("DE_v150.xsd")


# =====================================================================
# FIXTURES DE DATOS DE PRUEBA
# =====================================================================

@pytest.fixture(scope="session")
def sifen_namespace():
    """Namespace oficial SIFEN v150"""
    return "http://ekuatia.set.gov.py/sifen/xsd"


@pytest.fixture(scope="session")
def common_test_data():
    """Datos de prueba comunes para todos los schemas"""
    return {
        "version_valida": "150",
        "version_invalida": "140",
        "versiones_invalidas": ["140", "149", "151", "1.5.0", "V150"],
        "ruc_valido": "12345678",
        "ruc_invalido": "123",
        "ruc_validos": ["12345678", "80012345", "87654321", "123456789"],
        "ruc_invalidos": ["1234567", "12345678901", "ABCDEFGH", ""],
        "cdc_validos": [
            "01234567890123456789012345678901234567890123",
            "80012345912345678901234567890123456789012345"
        ],
        "cdc_invalidos": [
            "0123456789012345678901234567890123456789012",
            "012345678901234567890123456789012345678901234",
            "01234567890123456789012345678901234567890X23"
        ],
        "texto_valido": "Texto de prueba válido",
        "textos_invalidos": ["", "   ", "\t\n"],
        "fecha_valida": "2025-06-20T10:30:00-03:00",
        "fecha_invalida": "2025-13-45",
        "telefono_valido": "(021) 123-4567",
        "telefono_invalido": "abc",
        "email_valido": "test@empresa.com.py",
        "email_invalido": "not-an-email",
        "url_valida": "https://www.empresa.com.py",
        "url_invalida": "not-a-url",
        "codigo_postal_valido": "1001",
        "codigo_postal_invalido": "A"
    }


@pytest.fixture(scope="session")
def paraguay_specific_data():
    """Datos específicos de Paraguay para tests"""
    return {
        "departamentos_validos": ["1", "10", "16", "17"],
        "ciudades_validas": ["1", "101", "1601", "1701"],
        "telefonos_asuncion": ["(021) 123-4567", "(021) 987-6543"],
        "telefonos_moviles": ["0981-123456", "0971-987654", "0983-147258"],
        "emails_gov": ["info@set.gov.py", "contacto@sifen.set.gov.py"],
        "sitios_institucionales": [
            "https://www.sifen.set.gov.py",
            "https://www.set.gov.py"
        ]
    }


# =====================================================================
# FIXTURES DE UTILIDADES
# =====================================================================

@pytest.fixture
def xml_wrapper_factory(sifen_namespace):
    """Factory para crear XML wrappers con namespace correcto"""
    def _create_xml(fragment: str, root_element: str = "test") -> str:
        """
        Envuelve un fragmento XML en un elemento raíz con namespace

        Args:
            fragment: Fragmento XML a envolver
            root_element: Nombre del elemento raíz

        Returns:
            XML completo con namespace
        """
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<{root_element} xmlns="{sifen_namespace}">
    {fragment}
</{root_element}>"""

    return _create_xml


@pytest.fixture
def validation_helper():
    """Helper para operaciones comunes de validación"""
    class ValidationHelper:
        @staticmethod
        def assert_valid(result, context: str = ""):
            """Assert que un resultado de validación sea válido"""
            assert result is not None, f"Resultado None en {context}"
            assert hasattr(
                result, 'is_valid'), f"Resultado sin is_valid en {context}"
            assert result.is_valid, f"Validación falló en {context}: {getattr(result, 'errors', 'Sin errores')}"

        @staticmethod
        def assert_invalid(result, context: str = ""):
            """Assert que un resultado de validación sea inválido"""
            assert result is not None, f"Resultado None en {context}"
            assert hasattr(
                result, 'is_valid'), f"Resultado sin is_valid en {context}"
            assert not result.is_valid, f"Validación pasó cuando debería fallar en {context}"

        @staticmethod
        def collect_validation_stats(results: list) -> Dict[str, Any]:
            """Recopila estadísticas de múltiples validaciones"""
            total = len(results)
            valid = sum(1 for r in results if hasattr(
                r, 'is_valid') and r.is_valid)
            invalid = total - valid

            return {
                "total": total,
                "valid": valid,
                "invalid": invalid,
                "success_rate": valid / total if total > 0 else 0.0
            }

    return ValidationHelper()


# =====================================================================
# FIXTURES DE MANEJO DE ERRORES
# =====================================================================

@pytest.fixture
def error_analyzer():
    """Analizador de errores de validación para debugging"""
    class ErrorAnalyzer:
        @staticmethod
        def categorize_errors(errors: list) -> Dict[str, list]:
            """Categoriza errores por tipo"""
            categories = {
                "syntax": [],
                "namespace": [],
                "type": [],
                "pattern": [],
                "structure": [],
                "other": []
            }

            for error in errors:
                error_str = str(error).lower()
                if "syntax" in error_str or "parsing" in error_str:
                    categories["syntax"].append(error)
                elif "namespace" in error_str or "xmlns" in error_str:
                    categories["namespace"].append(error)
                elif "type" in error_str or "datatype" in error_str:
                    categories["type"].append(error)
                elif "pattern" in error_str or "regex" in error_str:
                    categories["pattern"].append(error)
                elif "element" in error_str or "structure" in error_str:
                    categories["structure"].append(error)
                else:
                    categories["other"].append(error)

            return categories

        @staticmethod
        def suggest_fixes(errors: list) -> list:
            """Sugiere posibles soluciones para errores"""
            suggestions = []

            for error in errors:
                error_str = str(error).lower()
                if "namespace" in error_str:
                    suggestions.append(
                        "Verificar namespace correcto: http://ekuatia.set.gov.py/sifen/xsd")
                elif "pattern" in error_str:
                    suggestions.append(
                        "Verificar formato de datos según especificación SIFEN")
                elif "element" in error_str:
                    suggestions.append(
                        "Verificar estructura XML y elementos requeridos")
                else:
                    suggestions.append("Revisar documentación SIFEN v150")

            return list(set(suggestions))  # Remover duplicados

    return ErrorAnalyzer()


# =====================================================================
# CLEANUP Y TEARDOWN
# =====================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_after_tests():
    """Cleanup automático después de todos los tests"""
    yield

    # Limpiar archivos temporales si se crearon
    temp_files = Path("/tmp").glob("sifen_test_*")
    for temp_file in temp_files:
        try:
            temp_file.unlink()
        except:
            pass

    # Log final
    logger = logging.getLogger("schemas_tests")
    logger.info("✅ Tests de schemas completados - cleanup realizado")
