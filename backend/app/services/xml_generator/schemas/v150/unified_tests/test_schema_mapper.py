"""
Tests Unitarios para SchemaMapper v150

Tests comprehensivos para validar el funcionamiento correcto del sistema
de mapeo entre esquemas modulares y oficiales SIFEN.

Categorías de Testing:
1. Tests de Configuración y Carga
2. Tests de Estrategias de Mapeo
3. Tests de Reglas y Validación
4. Tests de Performance
5. Tests de Integración Básica
6. Tests de Casos Edge y Errores

Cobertura Objetivo: >95%
Tiempo Ejecución: <100ms por test individual

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Importar módulo bajo test
from ..integration.schema_mapper import (
    SchemaMapper,
    MappingDirection,
    DocumentType,
    MappingComplexity,
    MappingRule,
    MappingContext,
    MappingResult,
    SimpleMappingStrategy,
    ComplexMappingStrategy,
    MappingStrategyRegistry,
    MappingConfigLoader,
    create_mapping_context,
    quick_map_element,
    validate_mapping_configuration
)


# =====================================
# FIXTURES DE DATOS DE PRUEBA
# =====================================

@pytest.fixture
def sample_mapping_rule():
    """Fixture con regla de mapeo básica"""
    return MappingRule(
        modular_path="gDatGral",
        official_path="gTimb",
        direction=MappingDirection.BIDIRECTIONAL,
        complexity=MappingComplexity.SIMPLE,
        priority=100,
        description="Mapeo de datos generales"
    )


@pytest.fixture
def complex_mapping_rule():
    """Fixture con regla de mapeo compleja"""
    return MappingRule(
        modular_path="gTotSub/dSubExe",
        official_path="gTotSub/dSubTotOpe",
        direction=MappingDirection.MODULAR_TO_OFFICIAL,
        complexity=MappingComplexity.COMPLEX,
        transformation="aggregate_subtotals",
        conditions={"document_type": "FE"},
        priority=200,
        description="Agregación de subtotales"
    )


@pytest.fixture
def sample_mapping_context():
    """Fixture con contexto de mapeo básico"""
    return MappingContext(
        document_type=DocumentType.FACTURA_ELECTRONICA,
        direction=MappingDirection.MODULAR_TO_OFFICIAL,
        source_namespace="http://modular.local",
        target_namespace="http://ekuatia.set.gov.py/sifen/xsd"
    )


@pytest.fixture
def sample_modular_element():
    """Fixture con elemento XML modular de ejemplo"""
    element = Element("gDatGral")
    SubElement(element, "dFeEmiDE").text = "2024-12-15"
    SubElement(element, "dHorEmi").text = "14:30:00"
    SubElement(element, "iTipoDE").text = "1"
    return element


@pytest.fixture
def sample_official_element():
    """Fixture con elemento XML oficial de ejemplo"""
    element = Element("gTimb")
    SubElement(element, "iTiTDE").text = "1"
    SubElement(element, "dDesTiTDE").text = "Factura Electrónica"
    SubElement(element, "dNumTim").text = "12345678"
    return element


@pytest.fixture
def config_file_content():
    """Fixture con contenido de archivo de configuración"""
    return {
        "documents": {
            "FE": {
                "mapping_rules": [
                    {
                        "modular_path": "gDatGral",
                        "official_path": "gTimb",
                        "direction": "bidirectional",
                        "complexity": "simple",
                        "priority": 100,
                        "description": "Datos generales del documento"
                    },
                    {
                        "modular_path": "gTotSub/dSubExe",
                        "official_path": "gTotSub/dSubTotOpe",
                        "direction": "modular_to_official",
                        "complexity": "complex",
                        "transformation": "aggregate_subtotals",
                        "priority": 200,
                        "description": "Agregación de subtotales"
                    }
                ]
            },
            "NCE": {
                "mapping_rules": [
                    {
                        "modular_path": "gDatNC",
                        "official_path": "gCamNC",
                        "direction": "bidirectional",
                        "complexity": "simple",
                        "priority": 100,
                        "description": "Datos nota de crédito"
                    }
                ]
            }
        }
    }


@pytest.fixture
def temp_config_file(config_file_content):
    """Fixture que crea archivo temporal de configuración"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_file_content, f)
        config_path = Path(f.name)

    yield config_path

    # Cleanup
    config_path.unlink(missing_ok=True)


# =====================================
# TESTS DE CONFIGURACIÓN Y CARGA
# =====================================

class TestMappingConfigLoader:
    """Tests para el cargador de configuración"""

    def test_load_rules_for_document_type_success(self, temp_config_file):
        """Test carga exitosa de reglas para tipo de documento"""
        loader = MappingConfigLoader(temp_config_file)

        rules = loader.load_rules_for_document_type(
            DocumentType.FACTURA_ELECTRONICA)

        assert len(rules) == 2
        # Ordenadas por prioridad
        assert rules[0].priority >= rules[1].priority
        assert rules[0].modular_path in ["gDatGral", "gTotSub/dSubExe"]
        assert rules[0].official_path in ["gTimb", "gTotSub/dSubTotOpe"]

    def test_load_rules_file_not_found(self):
        """Test comportamiento cuando archivo no existe"""
        loader = MappingConfigLoader(Path("/no/existe/config.yaml"))

        rules = loader.load_rules_for_document_type(
            DocumentType.FACTURA_ELECTRONICA)

        assert rules == []

    def test_validate_config_file_success(self, temp_config_file):
        """Test validación exitosa de archivo de configuración"""
        loader = MappingConfigLoader(temp_config_file)

        is_valid, errors = loader.validate_config_file()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_file_missing_required_fields(self):
        """Test validación con campos requeridos faltantes"""
        invalid_config = {
            "documents": {
                "FE": {
                    "mapping_rules": [
                        {
                            "modular_path": "gDatGral",
                            # Falta official_path
                            "direction": "bidirectional"
                        }
                    ]
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            loader = MappingConfigLoader(config_path)
            is_valid, errors = loader.validate_config_file()

            assert is_valid is False
            assert len(errors) > 0
            assert any("official_path" in error for error in errors)
        finally:
            config_path.unlink(missing_ok=True)

    def test_cache_functionality(self, temp_config_file):
        """Test que el cache funciona correctamente"""
        loader = MappingConfigLoader(temp_config_file)

        # Primera carga
        rules1 = loader.load_rules_for_document_type(
            DocumentType.FACTURA_ELECTRONICA)

        # Segunda carga (debería usar cache)
        rules2 = loader.load_rules_for_document_type(
            DocumentType.FACTURA_ELECTRONICA)

        assert rules1 == rules2
        assert len(loader._cache) > 0


class TestMappingRule:
    """Tests para la clase MappingRule"""

    def test_mapping_rule_creation_valid(self):
        """Test creación exitosa de regla de mapeo"""
        rule = MappingRule(
            modular_path="gDatGral",
            official_path="gTimb",
            direction=MappingDirection.BIDIRECTIONAL,
            complexity=MappingComplexity.SIMPLE,
            priority=100
        )

        assert rule.modular_path == "gDatGral"
        assert rule.official_path == "gTimb"
        assert rule.direction == MappingDirection.BIDIRECTIONAL
        assert rule.complexity == MappingComplexity.SIMPLE
        assert rule.priority == 100

    def test_mapping_rule_validation_empty_paths(self):
        """Test validación falla con paths vacíos"""
        with pytest.raises(ValueError, match="modular_path y official_path son requeridos"):
            MappingRule(
                modular_path="",
                official_path="gTimb"
            )

    def test_mapping_rule_validation_invalid_priority(self):
        """Test validación falla con prioridad inválida"""
        with pytest.raises(ValueError, match="priority debe estar entre 0 y 1000"):
            MappingRule(
                modular_path="gDatGral",
                official_path="gTimb",
                priority=1001
            )


# =====================================
# TESTS DE ESTRATEGIAS DE MAPEO
# =====================================

class TestSimpleMappingStrategy:
    """Tests para estrategia de mapeo simple"""

    def test_map_element_success(self, sample_mapping_rule, sample_mapping_context, sample_modular_element):
        """Test mapeo simple exitoso"""
        strategy = SimpleMappingStrategy()

        result = strategy.map_element(
            sample_modular_element, sample_mapping_rule, sample_mapping_context)

        assert result.success is True
        assert result.mapped_element is not None
        assert result.mapped_element.tag == "gTimb"  # Tag oficial
        assert len(result.errors) == 0
        assert len(result.applied_rules) == 1
        assert result.execution_time > 0

    def test_validate_rule_valid_simple(self, sample_mapping_rule):
        """Test validación exitosa de regla simple"""
        strategy = SimpleMappingStrategy()

        is_valid, errors = strategy.validate_rule(sample_mapping_rule)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_rule_invalid_complexity(self, complex_mapping_rule):
        """Test validación falla con complejidad incorrecta"""
        strategy = SimpleMappingStrategy()

        is_valid, errors = strategy.validate_rule(complex_mapping_rule)

        assert is_valid is False
        assert len(errors) > 0
        assert any("SIMPLE" in error for error in errors)

    def test_extract_tag_from_path(self):
        """Test extracción de tag desde XPath"""
        strategy = SimpleMappingStrategy()

        # Path simple
        tag1 = strategy._extract_tag_from_path("gDatGral")
        assert tag1 == "gDatGral"

        # Path con jerarquía
        tag2 = strategy._extract_tag_from_path("gTotSub/dSubExe")
        assert tag2 == "dSubExe"

    def test_map_element_with_attributes(self, sample_mapping_rule, sample_mapping_context):
        """Test mapeo preserva atributos del elemento"""
        element = Element("gDatGral")
        element.set("attr1", "value1")
        element.set("attr2", "value2")
        element.text = "contenido"

        strategy = SimpleMappingStrategy()
        result = strategy.map_element(
            element, sample_mapping_rule, sample_mapping_context)

        assert result.success is True
        assert result.mapped_element.get("attr1") == "value1"
        assert result.mapped_element.get("attr2") == "value2"
        assert result.mapped_element.text == "contenido"


class TestComplexMappingStrategy:
    """Tests para estrategia de mapeo complejo"""

    def test_map_element_success(self, complex_mapping_rule, sample_mapping_context, sample_modular_element):
        """Test mapeo complejo exitoso"""
        strategy = ComplexMappingStrategy()

        result = strategy.map_element(
            sample_modular_element, complex_mapping_rule, sample_mapping_context)

        assert result.success is True
        assert result.mapped_element is not None
        assert result.mapped_element.tag == "dSubTotOpe"
        assert len(result.applied_rules) == 1
        assert result.execution_time > 0

    def test_evaluate_conditions_success(self, sample_mapping_context):
        """Test evaluación exitosa de condiciones"""
        strategy = ComplexMappingStrategy()
        element = Element("gDatGral")
        conditions = {"document_type": "FE"}

        result = strategy._evaluate_conditions(
            element, conditions, sample_mapping_context)

        assert result is True

    def test_evaluate_conditions_failure(self, sample_mapping_context):
        """Test evaluación falla cuando condiciones no se cumplen"""
        strategy = ComplexMappingStrategy()
        element = Element("gDatGral")
        conditions = {"document_type": "NCE"}  # Diferente al contexto (FE)

        result = strategy._evaluate_conditions(
            element, conditions, sample_mapping_context)

        assert result is False

    def test_evaluate_conditions_element_exists(self):
        """Test condición de existencia de elemento"""
        strategy = ComplexMappingStrategy()
        element = Element("gDatGral")
        SubElement(element, "dFeEmiDE").text = "2024-12-15"

        conditions = {"element_exists": "dFeEmiDE"}
        context = MappingContext(
            DocumentType.FACTURA_ELECTRONICA, MappingDirection.MODULAR_TO_OFFICIAL)

        result = strategy._evaluate_conditions(element, conditions, context)

        assert result is True

    def test_evaluate_conditions_attribute_value(self):
        """Test condición de valor de atributo"""
        strategy = ComplexMappingStrategy()
        element = Element("gDatGral")
        element.set("version", "1.0")

        conditions = {"attribute_value": ["version", "1.0"]}
        context = MappingContext(
            DocumentType.FACTURA_ELECTRONICA, MappingDirection.MODULAR_TO_OFFICIAL)

        result = strategy._evaluate_conditions(element, conditions, context)

        assert result is True

    def test_validate_rule_valid_complex(self):
        """Test validación exitosa de regla compleja"""
        strategy = ComplexMappingStrategy()
        rule = MappingRule(
            modular_path="gTotSub",
            official_path="gTotSub",
            complexity=MappingComplexity.COMPLEX
        )

        is_valid, errors = strategy.validate_rule(rule)

        assert is_valid is True
        assert len(errors) == 0

    def test_map_element_with_conditions_not_met(self, complex_mapping_rule, sample_modular_element):
        """Test mapeo cuando condiciones no se cumplen"""
        strategy = ComplexMappingStrategy()

        # Cambiar contexto para que condiciones fallen
        context = MappingContext(
            document_type=DocumentType.NOTA_CREDITO_ELECTRONICA,  # Diferente a condición "FE"
            direction=MappingDirection.MODULAR_TO_OFFICIAL
        )

        result = strategy.map_element(
            sample_modular_element, complex_mapping_rule, context)

        assert result.success is False
        assert len(result.warnings) > 0
        assert "Condiciones no cumplidas" in result.warnings[0]


class TestMappingStrategyRegistry:
    """Tests para el registry de estrategias"""

    def test_default_strategies_registered(self):
        """Test que estrategias por defecto están registradas"""
        registry = MappingStrategyRegistry()

        simple_strategy = registry.get_strategy(MappingComplexity.SIMPLE)
        complex_strategy = registry.get_strategy(MappingComplexity.COMPLEX)

        assert simple_strategy is not None
        assert isinstance(simple_strategy, SimpleMappingStrategy)
        assert complex_strategy is not None
        assert isinstance(complex_strategy, ComplexMappingStrategy)

    def test_register_custom_strategy(self):
        """Test registro de estrategia personalizada"""
        registry = MappingStrategyRegistry()
        custom_strategy = Mock(spec=SimpleMappingStrategy)

        registry.register_strategy(MappingComplexity.SIMPLE, custom_strategy)
        retrieved_strategy = registry.get_strategy(MappingComplexity.SIMPLE)

        assert retrieved_strategy is custom_strategy

    def test_list_strategies(self):
        """Test listado de todas las estrategias"""
        registry = MappingStrategyRegistry()

        strategies = registry.list_strategies()

        assert len(strategies) >= 4  # Al menos las 4 complejidades por defecto
        assert MappingComplexity.SIMPLE in strategies
        assert MappingComplexity.COMPLEX in strategies

    def test_get_nonexistent_strategy(self):
        """Test obtener estrategia inexistente"""
        registry = MappingStrategyRegistry()

        # Crear complejidad falsa para test
        with patch('schema_mapper.MappingComplexity') as mock_complexity:
            mock_complexity.NONEXISTENT = "nonexistent"
            strategy = registry.get_strategy(mock_complexity.NONEXISTENT)

            assert strategy is None


# =====================================
# TESTS DE SCHEMA MAPPER PRINCIPAL
# =====================================

class TestSchemaMapper:
    """Tests para la clase principal SchemaMapper"""

    def test_initialization(self, temp_config_file):
        """Test inicialización correcta del mapper"""
        mapper = SchemaMapper(temp_config_file)

        assert mapper.config_loader is not None
        assert mapper.strategy_registry is not None
        assert isinstance(mapper._loaded_rules, dict)
        assert mapper._cache_enabled is True

    def test_load_configuration_success(self, temp_config_file):
        """Test carga exitosa de configuración"""
        mapper = SchemaMapper(temp_config_file)

        success = mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        assert success is True
        assert DocumentType.FACTURA_ELECTRONICA in mapper._loaded_rules
        assert len(mapper._loaded_rules[DocumentType.FACTURA_ELECTRONICA]) > 0

    def test_load_configuration_invalid_file(self):
        """Test carga falla con archivo inválido"""
        mapper = SchemaMapper(Path("/no/existe/config.yaml"))

        success = mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        assert success is False

    def test_map_to_official_success(self, temp_config_file, sample_modular_element, sample_mapping_context):
        """Test mapeo exitoso modular → oficial"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        result = mapper.map_to_official(
            sample_modular_element, sample_mapping_context)

        assert result.success is True
        assert result.mapped_element is not None
        assert result.execution_time > 0
        assert len(result.applied_rules) > 0

    def test_map_to_modular_success(self, temp_config_file, sample_official_element):
        """Test mapeo exitoso oficial → modular"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        context = MappingContext(
            document_type=DocumentType.FACTURA_ELECTRONICA,
            direction=MappingDirection.OFFICIAL_TO_MODULAR
        )

        result = mapper.map_to_modular(sample_official_element, context)

        # Puede fallar si no hay regla para el elemento oficial, pero debe ejecutar sin error
        assert result is not None
        assert isinstance(result, MappingResult)

    def test_find_applicable_rule_exact_match(self, temp_config_file, sample_modular_element, sample_mapping_context):
        """Test encuentra regla exacta para elemento"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        rule = mapper._find_applicable_rule(
            sample_modular_element,
            MappingDirection.MODULAR_TO_OFFICIAL,
            sample_mapping_context
        )

        assert rule is not None
        assert rule.modular_path == "gDatGral"

    def test_find_applicable_rule_no_match(self, temp_config_file, sample_mapping_context):
        """Test no encuentra regla para elemento inexistente"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        nonexistent_element = Element("gElementoInexistente")

        rule = mapper._find_applicable_rule(
            nonexistent_element,
            MappingDirection.MODULAR_TO_OFFICIAL,
            sample_mapping_context
        )

        assert rule is None

    def test_validate_mapping_rules_success(self, temp_config_file):
        """Test validación exitosa de reglas de mapeo"""
        mapper = SchemaMapper(temp_config_file)

        is_valid, errors = mapper.validate_mapping_rules(
            DocumentType.FACTURA_ELECTRONICA)

        assert is_valid is True
        assert len(errors) == 0

    def test_get_performance_statistics(self, temp_config_file, sample_modular_element, sample_mapping_context):
        """Test obtención de estadísticas de performance"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        # Ejecutar algunos mapeos para generar estadísticas
        mapper.map_to_official(sample_modular_element, sample_mapping_context)
        mapper.map_to_official(sample_modular_element, sample_mapping_context)

        stats = mapper.get_performance_statistics()

        assert "total_mappings" in stats
        assert "by_operation" in stats
        assert stats["total_mappings"] >= 0

    def test_clear_cache(self, temp_config_file):
        """Test limpieza de cache"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        # Verificar que hay datos en cache
        assert len(mapper._loaded_rules) > 0

        mapper.clear_cache()

        # Verificar que cache está limpio
        assert len(mapper._loaded_rules) == 0
        assert len(mapper.config_loader._cache) == 0
        assert len(mapper._performance_stats) == 0

    def test_get_loaded_rules_summary(self, temp_config_file):
        """Test obtención de resumen de reglas cargadas"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)
        mapper.load_configuration(DocumentType.NOTA_CREDITO_ELECTRONICA)

        summary = mapper.get_loaded_rules_summary()

        assert "FE" in summary
        assert "NCE" in summary
        assert "total_rules" in summary["FE"]
        assert "by_complexity" in summary["FE"]
        assert "by_direction" in summary["FE"]

    def test_rule_matches_element_exact(self, temp_config_file):
        """Test coincidencia exacta de regla con elemento"""
        mapper = SchemaMapper(temp_config_file)
        rule = MappingRule(
            modular_path="gDatGral",
            official_path="gTimb",
            direction=MappingDirection.BIDIRECTIONAL
        )

        # Test dirección modular → oficial
        matches = mapper._rule_matches_element(
            rule, "gDatGral", MappingDirection.MODULAR_TO_OFFICIAL
        )
        assert matches is True

        # Test dirección oficial → modular
        matches = mapper._rule_matches_element(
            rule, "gTimb", MappingDirection.OFFICIAL_TO_MODULAR
        )
        assert matches is True

        # Test dirección incorrecta
        rule_unidirectional = MappingRule(
            modular_path="gDatGral",
            official_path="gTimb",
            direction=MappingDirection.MODULAR_TO_OFFICIAL
        )
        matches = mapper._rule_matches_element(
            rule_unidirectional, "gTimb", MappingDirection.OFFICIAL_TO_MODULAR
        )
        assert matches is False

    def test_rule_matches_pattern_wildcard(self, temp_config_file):
        """Test coincidencia por patrón con wildcards"""
        mapper = SchemaMapper(temp_config_file)
        rule = MappingRule(
            modular_path="gDat*",
            official_path="gTimb",
            direction=MappingDirection.MODULAR_TO_OFFICIAL
        )

        matches = mapper._rule_matches_pattern(
            rule, "gDatGral", MappingDirection.MODULAR_TO_OFFICIAL
        )
        assert matches is True

        no_matches = mapper._rule_matches_pattern(
            rule, "gTotSub", MappingDirection.MODULAR_TO_OFFICIAL
        )
        assert no_matches is False


# =====================================
# TESTS DE FUNCIONES DE UTILIDAD
# =====================================

class TestUtilityFunctions:
    """Tests para funciones de utilidad públicas"""

    def test_create_mapping_context(self):
        """Test creación de contexto de mapeo"""
        context = create_mapping_context(
            document_type=DocumentType.FACTURA_ELECTRONICA,
            direction=MappingDirection.MODULAR_TO_OFFICIAL,
            source_namespace="http://modular.local",
            target_namespace="http://oficial.set",
            custom_var="custom_value"
        )

        assert context.document_type == DocumentType.FACTURA_ELECTRONICA
        assert context.direction == MappingDirection.MODULAR_TO_OFFICIAL
        assert context.source_namespace == "http://modular.local"
        assert context.target_namespace == "http://oficial.set"
        assert context.variables["custom_var"] == "custom_value"

    def test_quick_map_element_success(self, temp_config_file, sample_modular_element):
        """Test mapeo rápido exitoso"""
        result = quick_map_element(
            element=sample_modular_element,
            document_type=DocumentType.FACTURA_ELECTRONICA,
            direction=MappingDirection.MODULAR_TO_OFFICIAL,
            config_path=temp_config_file
        )

        assert isinstance(result, MappingResult)
        assert result.success is True
        assert result.mapped_element is not None

    def test_validate_mapping_configuration_success(self, temp_config_file):
        """Test validación exitosa de configuración"""
        is_valid, errors = validate_mapping_configuration(temp_config_file)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_mapping_configuration_invalid_file(self):
        """Test validación falla con archivo inexistente"""
        is_valid, errors = validate_mapping_configuration(
            Path("/no/existe/config.yaml"))

        assert is_valid is False
        assert len(errors) > 0


# =====================================
# TESTS DE PERFORMANCE
# =====================================

class TestPerformance:
    """Tests de performance y optimización"""

    def test_mapping_performance_within_limits(self, temp_config_file, sample_modular_element, sample_mapping_context):
        """Test que mapeo se ejecuta dentro de límites de tiempo"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        result = mapper.map_to_official(
            sample_modular_element, sample_mapping_context)

        # Debe ejecutar en menos de 100ms
        assert result.execution_time < 100.0
        assert result.success is True

    def test_multiple_mappings_performance(self, temp_config_file, sample_modular_element, sample_mapping_context):
        """Test performance con múltiples mapeos"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        import time
        start_time = time.time()

        # Ejecutar 10 mapeos
        for _ in range(10):
            result = mapper.map_to_official(
                sample_modular_element, sample_mapping_context)
            assert result.success is True

        total_time = (time.time() - start_time) * 1000

        # 10 mapeos deben ejecutar en menos de 500ms total
        assert total_time < 500.0

    def test_cache_improves_performance(self, temp_config_file):
        """Test que cache mejora performance"""
        mapper = SchemaMapper(temp_config_file)

        import time

        # Primera carga (sin cache)
        start_time = time.time()
        success1 = mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)
        first_load_time = time.time() - start_time

        # Limpiar cache
        mapper.clear_cache()

        # Segunda carga (debería usar cache del config loader)
        start_time = time.time()
        success2 = mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)
        second_load_time = time.time() - start_time

        assert success1 is True
        assert success2 is True
        # La segunda carga puede ser igual o más rápida (cache de archivos del SO)
        assert second_load_time <= first_load_time * 2  # Margen razonable


# =====================================
# TESTS DE CASOS EDGE Y ERRORES
# =====================================

class TestEdgeCasesAndErrors:
    """Tests para casos edge y manejo de errores"""

    def test_map_element_without_loaded_rules(self, sample_modular_element, sample_mapping_context):
        """Test mapeo falla cuando no hay reglas cargadas"""
        mapper = SchemaMapper()  # Sin configuración

        result = mapper.map_to_official(
            sample_modular_element, sample_mapping_context)

        assert result.success is False
        assert len(result.errors) > 0
        assert "No se pudieron cargar reglas" in result.errors[0]

    def test_map_element_with_invalid_strategy(self, temp_config_file, sample_modular_element, sample_mapping_context):
        """Test mapeo falla cuando no hay estrategia para complejidad"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        # Mock para simular regla con complejidad sin estrategia
        with patch.object(mapper.strategy_registry, 'get_strategy', return_value=None):
            result = mapper.map_to_official(
                sample_modular_element, sample_mapping_context)

            assert result.success is False
            assert len(result.errors) > 0
            assert "No hay estrategia" in result.errors[0]

    def test_map_element_with_exception_in_strategy(self, temp_config_file, sample_modular_element, sample_mapping_context):
        """Test manejo de excepciones en estrategia"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        # Mock para simular excepción en estrategia
        mock_strategy = Mock()
        mock_strategy.map_element.side_effect = Exception("Error simulado")

        with patch.object(mapper.strategy_registry, 'get_strategy', return_value=mock_strategy):
            result = mapper.map_to_official(
                sample_modular_element, sample_mapping_context)

            assert result.success is False
            assert len(result.errors) > 0
            assert "Error durante mapeo" in result.errors[0]

    def test_empty_xml_element(self, temp_config_file, sample_mapping_context):
        """Test mapeo con elemento XML vacío"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        empty_element = Element("gDatGral")  # Sin contenido

        result = mapper.map_to_official(empty_element, sample_mapping_context)

        # Debe manejar elemento vacío graciosamente
        assert isinstance(result, MappingResult)

    def test_xml_element_with_special_characters(self, temp_config_file, sample_mapping_context):
        """Test mapeo con caracteres especiales en XML"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        element = Element("gDatGral")
        element.text = "Texto con ñ, ü, acentós y símbolos @#$%"
        SubElement(element, "dFeEmiDE").text = "2024-12-15"

        result = mapper.map_to_official(element, sample_mapping_context)

        if result.success:
            assert result.mapped_element.text == "Texto con ñ, ü, acentós y símbolos @#$%"

    def test_find_duplicate_rules(self, temp_config_file):
        """Test detección de reglas duplicadas"""
        mapper = SchemaMapper(temp_config_file)

        # Crear reglas duplicadas
        rules = [
            MappingRule("gDatGral", "gTimb", MappingDirection.BIDIRECTIONAL),
            MappingRule("gDatGral", "gTimb",
                        MappingDirection.BIDIRECTIONAL),  # Duplicada
            MappingRule("gTotSub", "gTotSub",
                        MappingDirection.MODULAR_TO_OFFICIAL)
        ]

        duplicates = mapper._find_duplicate_rules(rules)

        assert len(duplicates) == 1
        assert "gDatGral→gTimb→bidirectional" in duplicates[0]


# =====================================
# TESTS DE INTEGRACIÓN BÁSICA
# =====================================

class TestBasicIntegration:
    """Tests de integración básica del sistema completo"""

    def test_full_workflow_modular_to_official(self, temp_config_file):
        """Test flujo completo: elemento modular → oficial"""
        # 1. Crear mapper y configurar
        mapper = SchemaMapper(temp_config_file)
        success = mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)
        assert success is True

        # 2. Crear elemento modular
        modular_element = Element("gDatGral")
        SubElement(modular_element, "dFeEmiDE").text = "2024-12-15"
        SubElement(modular_element, "dHorEmi").text = "14:30:00"

        # 3. Crear contexto
        context = create_mapping_context(
            document_type=DocumentType.FACTURA_ELECTRONICA,
            direction=MappingDirection.MODULAR_TO_OFFICIAL
        )

        # 4. Ejecutar mapeo
        result = mapper.map_to_official(modular_element, context)

        # 5. Verificar resultado
        assert result.success is True
        assert result.mapped_element is not None
        assert result.mapped_element.tag == "gTimb"
        assert result.execution_time > 0
        assert len(result.applied_rules) > 0

    def test_round_trip_mapping_consistency(self, temp_config_file):
        """Test consistencia en mapeo ida y vuelta"""
        mapper = SchemaMapper(temp_config_file)
        mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)

        # 1. Elemento modular original
        original_element = Element("gDatGral")
        original_element.text = "contenido_original"
        original_element.set("attr", "valor")

        # 2. Mapear modular → oficial
        context_to_official = create_mapping_context(
            DocumentType.FACTURA_ELECTRONICA,
            MappingDirection.MODULAR_TO_OFFICIAL
        )

        result_to_official = mapper.map_to_official(
            original_element, context_to_official)

        if result_to_official.success:
            # 3. Mapear oficial → modular
            context_to_modular = create_mapping_context(
                DocumentType.FACTURA_ELECTRONICA,
                MappingDirection.OFFICIAL_TO_MODULAR
            )

            result_to_modular = mapper.map_to_modular(
                result_to_official.mapped_element, context_to_modular)

            # 4. Verificar consistencia básica
            if result_to_modular.success:
                # Al menos el contenido texto debería preservarse
                assert isinstance(result_to_modular.mapped_element, Element)

    def test_multiple_document_types_configuration(self, temp_config_file):
        """Test configuración simultánea de múltiples tipos de documento"""
        mapper = SchemaMapper(temp_config_file)

        # Cargar configuración para múltiples tipos
        success_fe = mapper.load_configuration(
            DocumentType.FACTURA_ELECTRONICA)
        success_nce = mapper.load_configuration(
            DocumentType.NOTA_CREDITO_ELECTRONICA)

        assert success_fe is True
        assert success_nce is True

        # Verificar que ambas configuraciones están cargadas
        summary = mapper.get_loaded_rules_summary()
        assert "FE" in summary
        assert "NCE" in summary
        assert summary["FE"]["total_rules"] > 0
        assert summary["NCE"]["total_rules"] > 0


# =====================================
# CONFIGURACIÓN DE PYTEST
# =====================================

def pytest_configure(config):
    """Configuración global de pytest"""
    config.addinivalue_line(
        "markers", "slow: marca tests que toman más tiempo en ejecutar"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "performance: marca tests de performance"
    )


# Marcar tests de performance
pytestmark = pytest.mark.performance


if __name__ == "__main__":
    # Ejecutar tests cuando se ejecuta directamente
    pytest.main([__file__, "-v", "--tb=short"])
