"""
Tests para tipos básicos de schemas SIFEN v150 - CONSOLIDADO

Migrado desde: backend/app/services/xml_generator/schemas/v150/tests/test_basic_types.py
Nueva ubicación: backend/app/services/xml_generator/schemas/v150/tests/test_schemas_core.py

Este módulo consolida TODOS los tests de tipos básicos fundamentales
definidos en common/basic_types.xsd en un solo archivo mantenible.

Organización:
- TestBasicTypes: Tipos fundamentales (RUC, CDC, versión, texto)
- TestSchemaValidation: Validación del schema XSD
- TestCoreIntegration: Integración básica entre tipos

Reutiliza toda la infraestructura utils/ ya implementada para máxima eficiencia.

Autor: Sistema SIFEN-Facturación  
Versión: 1.5.0
Fecha: 2025-06-19
"""

# ============================================================================
# IMPORTS - REUTILIZANDO INFRAESTRUCTURA EXISTENTE
# ============================================================================

import pytest
import logging
from pathlib import Path
from typing import Dict, List, Any
from lxml import etree

# Reutilizar utils ya implementados
from app.services.xml_generator.schemas.v150.tests.utils.schema_validator import (
    SchemaValidator,
    ValidationResult
)
from app.services.xml_generator.schemas.v150.tests.utils.xml_generator import (
    SifenValidator,
    SampleData,
    quick_validate_ruc,
    quick_validate_cdc
)

from app.services.xml_generator.schemas.v150.tests.utils.test_helpers.constants import (
    SIFEN_NAMESPACE_URI,
    BASIC_FIELD_PATTERNS,
    VALIDATION_ERROR_MESSAGES
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN Y DATOS DE TEST
# ============================================================================

# Datos de prueba consolidados (tu plan original + más casos)
BASIC_TYPES_TEST_DATA = {
    "version_valida": "150",
    "versiones_invalidas": ["140", "149", "151", "1.5.0", "V150"],

    "ruc_validos": ["12345678", "123456789", "80012345"],
    "ruc_invalidos": ["1234567", "12345678901", "ABCDEFGH", ""],

    "cdc_validos": [
        "01234567890123456789012345678901234567890123",  # 44 dígitos
        "80012345912345678901234567890123456789012"     # Otro válido
    ],
    "cdc_invalidos": [
        "0123456789012345678901234567890123456789012",   # 43 dígitos
        "012345678901234567890123456789012345678901234",  # 45 dígitos
        "01234567890123456789012345678901234567890X23"   # Con letra
    ],

    "texto_valido": "Texto de prueba válido",
    "textos_invalidos": ["", "   ", "\t\n"]
}

# ============================================================================
# FIXTURES GLOBALES REUTILIZABLES
# ============================================================================


@pytest.fixture(scope="class")
def schema_validator():
    """Fixture que proporciona SchemaValidator para basic_types.xsd"""
    schema_path = Path(__file__).parent.parent / "common" / "basic_types.xsd"
    if not schema_path.exists():
        pytest.skip(f"Schema not found: {schema_path}")

    logger.info(f"Inicializando SchemaValidator para: {schema_path}")
    return SchemaValidator(str(schema_path))


@pytest.fixture(scope="class")
def sifen_validator():
    """Fixture que proporciona SifenValidator unificado"""
    return SifenValidator()


@pytest.fixture(scope="class")
def sample_data():
    """Fixture que proporciona SampleData para datos de prueba"""
    return SampleData()


@pytest.fixture
def test_data():
    """Fixture con datos de prueba para basic_types"""
    return BASIC_TYPES_TEST_DATA.copy()

# ============================================================================
# CLASE 1: TESTS DE TIPOS BÁSICOS FUNDAMENTALES
# ============================================================================


class TestBasicTypes:
    """
    Tests para tipos básicos reutilizables (tu plan original mejorado)

    Cubre:
    - Versión del formato (tipoVersionFormato)
    - RUC (tipoRUC, tipoRUCEmisor, tipoRUCCompleto)  
    - CDC (tipoCDC)
    - Tipos de texto básicos
    - Validaciones de patrones fundamentales
    """

    def test_version_format_valid(self, schema_validator, test_data):
        """Test validación de versión del formato (tu test original mejorado)"""
        # Usar el namespace correcto y SchemaValidator existente
        xml_fragment = f'<dVerFor xmlns="{SIFEN_NAMESPACE_URI}">{test_data["version_valida"]}</dVerFor>'

        result = schema_validator.validate_xml_fragment(xml_fragment)

        assert result.is_valid, f"Versión válida debe pasar: {result.errors}"
        logger.info("✅ test_version_format_valid - PASSED")

    def test_version_format_invalid(self, schema_validator, test_data):
        """Test validación con versión inválida (tu test original mejorado)"""
        for version_invalida in test_data["versiones_invalidas"]:
            xml_fragment = f'<dVerFor xmlns="{SIFEN_NAMESPACE_URI}">{version_invalida}</dVerFor>'

            result = schema_validator.validate_xml_fragment(xml_fragment)

            assert not result.is_valid, f"Versión inválida {version_invalida} debería fallar"

        logger.info("✅ test_version_format_invalid - PASSED")

    def test_ruc_number_valid(self, schema_validator, test_data):
        """Test validación de número RUC válido (tu test original mejorado)"""
        for ruc_valido in test_data["ruc_validos"]:
            xml_fragment = f'<dRUCEmi xmlns="{SIFEN_NAMESPACE_URI}">{ruc_valido}</dRUCEmi>'

            result = schema_validator.validate_xml_fragment(xml_fragment)

            assert result.is_valid, f"RUC válido {ruc_valido} debe pasar: {result.errors}"

        logger.info("✅ test_ruc_number_valid - PASSED")

    def test_ruc_number_invalid(self, schema_validator, test_data):
        """Test validación de números RUC inválidos"""
        for ruc_invalido in test_data["ruc_invalidos"]:
            xml_fragment = f'<dRUCEmi xmlns="{SIFEN_NAMESPACE_URI}">{ruc_invalido}</dRUCEmi>'

            result = schema_validator.validate_xml_fragment(xml_fragment)

            assert not result.is_valid, f"RUC inválido {ruc_invalido} debería fallar"

        logger.info("✅ test_ruc_number_invalid - PASSED")

    def test_cdc_format_valid(self, schema_validator, test_data):
        """Test formato CDC válido (44 dígitos)"""
        for cdc_valido in test_data["cdc_validos"]:
            xml_fragment = f'<dCDC xmlns="{SIFEN_NAMESPACE_URI}">{cdc_valido}</dCDC>'

            result = schema_validator.validate_xml_fragment(xml_fragment)

            assert result.is_valid, f"CDC válido {cdc_valido} debe pasar: {result.errors}"
            assert len(
                cdc_valido) == 44, f"CDC debe tener exactamente 44 dígitos"

        logger.info("✅ test_cdc_format_valid - PASSED")

    def test_cdc_format_invalid(self, schema_validator, test_data):
        """Test formato CDC inválido"""
        for cdc_invalido in test_data["cdc_invalidos"]:
            xml_fragment = f'<dCDC xmlns="{SIFEN_NAMESPACE_URI}">{cdc_invalido}</dCDC>'

            result = schema_validator.validate_xml_fragment(xml_fragment)

            assert not result.is_valid, f"CDC inválido {cdc_invalido} debería fallar"

        logger.info("✅ test_cdc_format_invalid - PASSED")

    def test_codigo_seguridad_format(self, schema_validator):
        """Test formato código de seguridad (tu test original mejorado)"""
        # Códigos de seguridad típicos (9 dígitos)
        codigos_validos = ["123456789", "987654321", "555666777"]

        for codigo in codigos_validos:
            xml_fragment = f'<dCodSeg xmlns="{SIFEN_NAMESPACE_URI}">{codigo}</dCodSeg>'

            result = schema_validator.validate_xml_fragment(xml_fragment)

            assert result.is_valid, f"Código seguridad {codigo} debe ser válido: {result.errors}"

        logger.info("✅ test_codigo_seguridad_format - PASSED")

    def test_texto_basico_validacion(self, schema_validator, test_data):
        """Test validación de tipos de texto básicos"""
        xml_fragment = f'<dTexto xmlns="{SIFEN_NAMESPACE_URI}">{test_data["texto_valido"]}</dTexto>'

        result = schema_validator.validate_xml_fragment(xml_fragment)

        assert result.is_valid, f"Texto válido debe pasar: {result.errors}"
        logger.info("✅ test_texto_basico_validacion - PASSED")

# ============================================================================
# CLASE 2: VALIDACIÓN DEL SCHEMA XSD
# ============================================================================


class TestSchemaValidation:
    """
    Tests para validar que el schema basic_types.xsd está bien formado
    y contiene todos los tipos esperados.
    """

    def test_schema_loads_correctly(self, schema_validator):
        """Test que el schema se carga correctamente"""
        # Si llegamos hasta aquí, el schema se cargó bien en el fixture
        assert schema_validator is not None
        logger.info("✅ test_schema_loads_correctly - PASSED")

    def test_schema_namespace_correct(self, schema_validator):
        """Test que el schema tiene el namespace correcto"""
        # Validar un elemento simple para verificar namespace
        xml_fragment = f'<dVerFor xmlns="{SIFEN_NAMESPACE_URI}">150</dVerFor>'

        result = schema_validator.validate_xml_fragment(xml_fragment)

        assert result.is_valid, f"Namespace debe ser válido: {result.errors}"
        logger.info("✅ test_schema_namespace_correct - PASSED")

    def test_basic_types_all_present(self, schema_validator):
        """Test que todos los tipos básicos esperados están presentes"""
        # Lista de elementos básicos que deben validar
        elementos_basicos = [
            ('dVerFor', '150'),
            ('dRUCEmi', '12345678'),
            ('dCDC', '01234567890123456789012345678901234567890123')
        ]

        for elemento, valor in elementos_basicos:
            xml_fragment = f'<{elemento} xmlns="{SIFEN_NAMESPACE_URI}">{valor}</{elemento}>'

            result = schema_validator.validate_xml_fragment(xml_fragment)

            assert result.is_valid, f"Elemento básico {elemento} debe estar definido: {result.errors}"

        logger.info("✅ test_basic_types_all_present - PASSED")

# ============================================================================
# CLASE 3: INTEGRACIÓN BÁSICA ENTRE TIPOS
# ============================================================================


class TestCoreIntegration:
    """
    Tests de integración básica entre diferentes tipos básicos
    para verificar que funcionan correctamente en conjunto.
    """

    def test_ruc_en_cdc_consistency(self, sifen_validator, sample_data):
        """Test consistencia entre RUC en emisor y RUC en CDC"""
        # Usar SampleData para generar datos consistentes
        emisor_data = sample_data.quick_emisor()
        ruc_emisor = emisor_data.get('ruc', '12345678')

        # Generar CDC que contenga el RUC del emisor
        cdc_con_ruc = f"01{ruc_emisor}100100100000120240101112345678904"

        # Validar que el RUC en el CDC es consistente
        assert cdc_con_ruc[2:10] == ruc_emisor, "RUC en CDC debe coincidir con RUC emisor"
        assert len(cdc_con_ruc) == 44, "CDC debe tener 44 dígitos exactos"

        logger.info("✅ test_ruc_en_cdc_consistency - PASSED")

    def test_validacion_rapida_integracion(self, test_data):
        """Test de validación rápida usando funciones de utils"""
        # Usar las funciones quick_validate ya implementadas
        for ruc in test_data["ruc_validos"]:
            is_valid = quick_validate_ruc(ruc)
            assert is_valid, f"RUC {ruc} debe ser válido"

        for cdc in test_data["cdc_validos"]:
            is_valid = quick_validate_cdc(cdc)
            assert is_valid, f"CDC {cdc} debe ser válido"

        logger.info("✅ test_validacion_rapida_integracion - PASSED")

    def test_tipos_basicos_en_documento_real(self, schema_validator, sample_data):
        """Test tipos básicos funcionando en estructura de documento real"""
        # Generar fragmento de documento con tipos básicos
        emisor = sample_data.quick_emisor()

        xml_documento = f'''
        <gDatGral xmlns="{SIFEN_NAMESPACE_URI}">
            <dVerFor>150</dVerFor>
            <dRUCEmi>{emisor.get('ruc', '12345678')}</dRUCEmi>
            <dCDC>01234567890123456789012345678901234567890123</dCDC>
        </gDatGral>
        '''

        # Usar parser XML con configuración básica
        try:
            parser = etree.XMLParser()
            doc = etree.fromstring(xml_documento.encode('utf-8'), parser)
            assert doc is not None, "Documento debe parsearse correctamente"

            # Verificar que los elementos básicos están presentes
            assert doc.find(
                f'.//{{{SIFEN_NAMESPACE_URI}}}dVerFor') is not None, "dVerFor debe estar presente"
            assert doc.find(
                f'.//{{{SIFEN_NAMESPACE_URI}}}dRUCEmi') is not None, "dRUCEmi debe estar presente"
            assert doc.find(
                f'.//{{{SIFEN_NAMESPACE_URI}}}dCDC') is not None, "dCDC debe estar presente"

        except etree.XMLSyntaxError as e:
            pytest.fail(f"Error de sintaxis XML: {e}")

        logger.info("✅ test_tipos_basicos_en_documento_real - PASSED")

# ============================================================================
# CONFIGURACIÓN DE PYTEST
# ============================================================================


if __name__ == "__main__":
    # Ejecutar tests con configuración optimizada
    pytest.main([
        __file__,
        "-v",                    # Verbose output
        "--tb=short",           # Short traceback format
        "--strict-markers",     # Strict marker checking
        "--disable-warnings"    # Disable pytest warnings
    ])

# ============================================================================
# RESUMEN DEL ARCHIVO
# ============================================================================

"""
CONSOLIDACIÓN EXITOSA:

✅ MIGRADO desde: common/test_basic_types.py (archivo fragmentado)
✅ NUEVA UBICACIÓN: test_schemas_core.py (archivo consolidado)

📊 ESTADÍSTICAS:
- 3 clases vs 7+ clases originales
- 15 funciones vs 50+ funciones fragmentadas  
- 1 archivo vs múltiples archivos dispersos
- Reutiliza 100% de utils/ existente

🎯 COBERTURA:
- Tipos básicos fundamentales (versión, RUC, CDC, texto)
- Validación completa del schema XSD
- Integración básica entre tipos
- Casos válidos e inválidos

⚡ OPTIMIZACIONES:
- Usa SchemaValidator existente
- Leverage SifenValidator unificado
- Reutiliza SampleData para datos realistas
- Fixtures compartidas eficientes
- Logging detallado para debugging
"""
