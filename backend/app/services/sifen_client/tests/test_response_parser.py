"""
Tests específicos para SifenResponseParser - VERSIÓN CON IMPORTS RELATIVOS

Enfoque: Testing del componente de parsing de respuestas XML SIFEN
que extrae información estructurada de las respuestas de los Web Services.

Uso:
    # Desde el directorio backend:
    python -m pytest app/services/sifen_client/tests/test_response_parser.py -v
    
    # O desde directorio raíz del proyecto:
    cd backend && python -m pytest app/services/sifen_client/tests/test_response_parser.py -v
"""

import pytest
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

# Imports relativos - más robustos para testing
try:
    # Intento 1: Import relativo desde el package
    from ..response_parser import (
        SifenResponseParser,
        parse_sifen_response,
        extract_cdc_from_response,
        extract_response_code,
        is_success_response,
        get_document_status_from_code,
        validate_response_xml_structure
    )
    from ..models import (
        SifenResponse,
        BatchResponse,
        QueryResponse,
        DocumentStatus,
        ResponseType
    )
    from ..exceptions import (
        SifenParsingError,
        SifenValidationError
    )
except ImportError:
    # Intento 2: Import absoluto con path adjustment
    import sys
    import os
    from pathlib import Path

    # Agregar directorios al path
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.parent.parent
    sifen_client_dir = current_dir.parent

    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(sifen_client_dir))

    try:
        from response_parser import (
            SifenResponseParser,
            parse_sifen_response,
            extract_cdc_from_response,
            extract_response_code,
            is_success_response,
            get_document_status_from_code,
            validate_response_xml_structure
        )
        from models import (
            SifenResponse,
            BatchResponse,
            QueryResponse,
            DocumentStatus,
            ResponseType
        )
        from exceptions import (
            SifenParsingError,
            SifenValidationError
        )
    except ImportError:
        # Intento 3: Import desde app completa
        from app.services.sifen_client.response_parser import (
            SifenResponseParser,
            parse_sifen_response,
            extract_cdc_from_response,
            extract_response_code,
            is_success_response,
            get_document_status_from_code,
            validate_response_xml_structure
        )
        from app.services.sifen_client.models import (
            SifenResponse,
            BatchResponse,
            QueryResponse,
            DocumentStatus,
            ResponseType
        )
        from app.services.sifen_client.exceptions import (
            SifenParsingError,
            SifenValidationError
        )


# ========================================
# FUNCIONES HELPER PARA ACCESO SEGURO
# ========================================

def get_exception_attribute(exception: Exception, attr_name: str, default_value=None):
    """
    Obtiene un atributo de excepción de forma segura para evitar warnings de Pylance

    Args:
        exception: Instancia de excepción
        attr_name: Nombre del atributo
        default_value: Valor por defecto si no existe

    Returns:
        Valor del atributo o default_value
    """
    return getattr(exception, attr_name, default_value)


def assert_exception_has_attribute(exception: Exception, attr_name: str, expected_value=None):
    """
    Verifica que una excepción tenga un atributo específico

    Args:
        exception: Instancia de excepción
        attr_name: Nombre del atributo esperado
        expected_value: Valor esperado (opcional)
    """
    if not hasattr(exception, attr_name):
        pytest.fail(
            f"Exception {type(exception).__name__} should have attribute '{attr_name}'")

    if expected_value is not None:
        actual_value = getattr(exception, attr_name)
        assert actual_value == expected_value, f"Expected {attr_name}={expected_value}, got {actual_value}"


# ========================================
# FIXTURES PARA RESPUESTAS XML
# ========================================

@pytest.fixture
def success_response_xml():
    """XML de respuesta exitosa (código 0260)"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:sifen="http://ekuatia.set.gov.py/sifen/xsd">
    <soap:Body>
        <sifen:respuestaEnvio>
            <sifen:success>true</sifen:success>
            <sifen:codigo>0260</sifen:codigo>
            <sifen:mensaje>Documento aprobado satisfactoriamente</sifen:mensaje>
            <sifen:cdc>01800695631001001000000612021112917595714694</sifen:cdc>
            <sifen:protocolo>PROT_2025_123456789</sifen:protocolo>
            <sifen:timestamp>2025-06-27T14:30:00Z</sifen:timestamp>
        </sifen:respuestaEnvio>
    </soap:Body>
</soap:Envelope>'''


@pytest.fixture
def error_response_xml():
    """XML de respuesta con error (código 1000)"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:sifen="http://ekuatia.set.gov.py/sifen/xsd">
    <soap:Body>
        <sifen:respuestaEnvio>
            <sifen:success>false</sifen:success>
            <sifen:codigo>1000</sifen:codigo>
            <sifen:mensaje>CDC no corresponde con XML</sifen:mensaje>
            <sifen:error codigo="1000" campo="cdc">CDC calculado no coincide con el proporcionado</sifen:error>
        </sifen:respuestaEnvio>
    </soap:Body>
</soap:Envelope>'''


@pytest.fixture
def malformed_xml():
    """XML malformado para testing de errores"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <sifen:respuestaEnvio>
            <sifen:codigo>0260</sifen:codigo>
            <sifen:mensaje>Test sin cerrar etiqueta
        </sifen:respuestaEnvio>
    </soap:Body>
<!-- XML intencionalmente malformado -->'''


@pytest.fixture
def security_threat_xml():
    """XML con amenazas de seguridad (DOCTYPE, ENTITY)"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE root [
    <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<soap:Envelope>
    <soap:Body>
        <respuesta>&xxe;</respuesta>
    </soap:Body>
</soap:Envelope>'''


# ========================================
# TESTS BÁSICOS DE PARSING
# ========================================

class TestSifenResponseParserBasic:
    """Tests básicos de funcionalidad del parser"""

    def test_parser_initialization(self):
        """Test: Inicialización correcta del parser"""
        parser = SifenResponseParser()

        # Verificar namespaces
        assert 'sifen' in parser.namespaces
        assert 'soap' in parser.namespaces
        assert parser.namespaces['sifen'] == 'http://ekuatia.set.gov.py/sifen/xsd'

        # Verificar códigos de estado
        assert '0260' in parser.status_codes
        assert '1005' in parser.status_codes
        assert '1000' in parser.status_codes

        # Verificar mapeo correcto a enums
        assert parser.status_codes['0260'][0] == DocumentStatus.APROBADO
        assert parser.status_codes['1005'][0] == DocumentStatus.APROBADO_OBSERVACION
        assert parser.status_codes['1000'][0] == DocumentStatus.RECHAZADO

    def test_parse_success_response(self, success_response_xml):
        """Test: Parse de respuesta exitosa (código 0260)"""
        parser = SifenResponseParser()

        response = parser.parse_response(
            success_response_xml, ResponseType.INDIVIDUAL)

        # Verificar campos básicos
        assert isinstance(response, SifenResponse)
        assert response.success is True
        assert response.code == "0260"
        assert response.message == "Documento aprobado satisfactoriamente"
        assert response.cdc == "01800695631001001000000612021112917595714694"
        assert response.protocol_number == "PROT_2025_123456789"
        assert response.document_status == DocumentStatus.APROBADO
        assert response.response_type == ResponseType.INDIVIDUAL
        assert len(response.errors) == 0

    def test_parse_error_response(self, error_response_xml):
        """Test: Parse de respuesta con errores (código 1000)"""
        parser = SifenResponseParser()

        response = parser.parse_response(
            error_response_xml, ResponseType.INDIVIDUAL)

        # Verificar campos de error
        assert response.success is False
        assert response.code == "1000"
        assert response.document_status == DocumentStatus.RECHAZADO
        assert len(response.errors) >= 1


# ========================================
# TESTS DE VALIDACIÓN Y SEGURIDAD
# ========================================

class TestSifenResponseParserSecurity:
    """Tests de validaciones de seguridad"""

    def test_empty_xml_handling(self):
        """Test: Manejo de XML vacío - Versión robusta"""
        parser = SifenResponseParser()

        # Test con string vacío
        with pytest.raises(SifenParsingError) as exc_info:
            parser.parse_response("", ResponseType.INDIVIDUAL)

        exception = exc_info.value
        assert "Respuesta XML vacía" in str(exception)

        # Verificación robusta de atributos
        assert_exception_has_attribute(
            exception, 'parsing_stage', "initial_validation")

        # Verificación adicional usando helper
        xml_content = get_exception_attribute(exception, 'xml_content')
        assert xml_content == ""

    def test_malformed_xml_handling(self, malformed_xml):
        """Test: Manejo de XML malformado - Versión robusta"""
        parser = SifenResponseParser()

        with pytest.raises(SifenParsingError) as exc_info:
            parser.parse_response(malformed_xml, ResponseType.INDIVIDUAL)

        exception = exc_info.value
        assert "XML malformado" in str(exception)

        # Verificación robusta de atributos
        assert_exception_has_attribute(
            exception, 'parsing_stage', "xml_parsing")

        # Verificar original_exception si existe
        original_exception = get_exception_attribute(
            exception, 'original_exception')
        if original_exception:
            assert isinstance(original_exception, ET.ParseError)

    def test_security_threat_detection(self, security_threat_xml):
        """Test: Detección de amenazas de seguridad - Versión robusta"""
        parser = SifenResponseParser()

        with pytest.raises(SifenParsingError) as exc_info:
            parser.parse_response(security_threat_xml, ResponseType.INDIVIDUAL)

        exception = exc_info.value
        assert "DOCTYPE" in str(
            exception) or "entidades externas" in str(exception)

        # Verificación robusta de parsing_stage
        assert_exception_has_attribute(
            exception, 'parsing_stage', "security_validation")


# ========================================
# TESTS DE FUNCIONES HELPER
# ========================================

class TestSifenResponseParserHelpers:
    """Tests de funciones helper públicas"""

    def test_parse_sifen_response_function(self, success_response_xml):
        """Test: Función helper parse_sifen_response"""
        response = parse_sifen_response(
            success_response_xml, ResponseType.INDIVIDUAL)

        assert isinstance(response, SifenResponse)
        assert response.code == "0260"
        assert response.success is True

    def test_extract_cdc_from_response_function(self, success_response_xml):
        """Test: Función helper extract_cdc_from_response"""
        cdc = extract_cdc_from_response(success_response_xml)

        assert cdc == "01800695631001001000000612021112917595714694"

    def test_extract_cdc_from_response_invalid_xml(self):
        """Test: extract_cdc_from_response con XML inválido"""
        cdc = extract_cdc_from_response("invalid xml")

        assert cdc is None

    def test_is_success_response_function(self, success_response_xml, error_response_xml):
        """Test: Función helper is_success_response"""
        # Test con respuesta exitosa
        assert is_success_response(success_response_xml) is True

        # Test con respuesta de error
        assert is_success_response(error_response_xml) is False

        # Test con XML inválido
        assert is_success_response("invalid xml") is False


# ========================================
# RUNNER PRINCIPAL
# ========================================

if __name__ == "__main__":
    """
    Ejecutor principal para tests de SifenResponseParser
    """
    print("🧪 Ejecutando tests de SifenResponseParser")
    print("=" * 50)

    # Verificar imports
    try:
        parser = SifenResponseParser()
        print("✅ Imports exitosos")
        print("✅ Parser inicializado correctamente")
        print(f"✅ Códigos de estado soportados: {len(parser.status_codes)}")
    except Exception as e:
        print(f"❌ Error en imports: {e}")
        exit(1)

    # Ejecutar tests básicos
    try:
        import pytest
        pytest.main([__file__, "-v", "--tb=short"])
    except ImportError:
        print("⚠️  pytest no disponible, ejecutando tests básicos...")

        # Tests mínimos sin pytest
        test_class = TestSifenResponseParserBasic()
        test_class.test_parser_initialization()
        print("✅ test_parser_initialization")

        # Test con XML de ejemplo
        success_xml = '''<?xml version="1.0"?>
        <response>
            <codigo>0260</codigo>
            <mensaje>Test exitoso</mensaje>
        </response>'''

        response = parser.parse_response(success_xml, ResponseType.INDIVIDUAL)
        assert response.code == "0260"
        print("✅ test_basic_parsing")

        print("\n🎉 Tests básicos completados exitosamente")
