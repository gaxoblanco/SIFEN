"""
Tests unitarios para MockSoapClient del módulo sifen_client

Valida que el mock funciona correctamente y simula
todos los escenarios esperados de SIFEN.

Ubicación: backend/app/services/sifen_client/tests/test_mock_soap_client.py
"""

import pytest
import time
from datetime import datetime
from unittest.mock import patch

# Imports del mock y fixtures
from app.services.sifen_client.tests.mocks.mock_soap_client import (
    MockSoapClient,
    create_mock_with_success_behavior,
    create_mock_with_error_behavior,
    create_mock_with_timeout_behavior,
    create_mock_with_realistic_behavior
)

from app.services.sifen_client.tests.fixtures.test_documents import (
    get_valid_factura_xml,
    get_xml_with_error,
    ADDITIONAL_TEST_RUCS,
    MOCK_TEST_CDCS,
    SIFEN_CODES,
    SIFEN_MESSAGES
)

from app.services.sifen_client.tests.fixtures.test_config import get_test_environment

# Imports de modelos
from app.services.sifen_client.models import DocumentStatus


class TestMockSoapClientBasic:
    """Tests básicos del MockSoapClient"""

    def test_mock_initialization(self):
        """Test inicialización del mock"""
        mock = MockSoapClient()

        assert mock.call_count == 0
        assert len(mock.call_history) == 0
        assert mock.last_request is None
        assert mock.last_response is None
        assert mock.simulate_latency == True
        assert mock.failure_rate == 0.0
        assert mock.timeout_rate == 0.0

    def test_mock_basic_success_response(self):
        """Test respuesta exitosa básica"""
        mock = MockSoapClient()
        # Sin latencia para test rápido
        mock.configure_behavior(simulate_latency=False)

        xml = get_valid_factura_xml()
        response = mock.send_document(xml)

        # Verificar respuesta exitosa
        assert response.success == True
        assert response.code == SIFEN_CODES['SUCCESS']
        assert response.message == SIFEN_MESSAGES[SIFEN_CODES['SUCCESS']]
        assert response.document_status == DocumentStatus.APROBADO
        assert response.cdc is not None
        assert response.protocol_number is not None

        # Verificar estado del mock
        assert mock.call_count == 1
        assert len(mock.call_history) == 1
        assert mock.last_request == xml
        assert mock.last_response == response

    def test_mock_error_response_ruc_invalid(self):
        """Test respuesta de error por RUC inválido"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)

        xml = get_xml_with_error('ruc_invalido')
        response = mock.send_document(xml)

        # Verificar respuesta de error
        assert response.success == False
        assert response.code == SIFEN_CODES['RUC_NOT_FOUND']
        assert response.document_status == DocumentStatus.RECHAZADO
        assert len(response.errors) > 0
        assert response.cdc == ""
        assert response.protocol_number == ""

    def test_mock_cdc_extraction(self):
        """Test extracción correcta de CDC del XML"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)

        # Generar XML base y reemplazar CDC
        xml = get_valid_factura_xml()
        test_cdc = MOCK_TEST_CDCS['success']

        # Reemplazar CDC en el XML usando regex
        import re
        xml_with_cdc = re.sub(
            r'<DE Id="[^"]*"',
            f'<DE Id="{test_cdc}"',
            xml
        )

        response = mock.send_document(xml_with_cdc)

        # Verificar que el CDC se extrajo correctamente
        assert response.cdc == test_cdc
        assert response.success == True

        # Verificar en historial - CON VALIDACIÓN
        assert mock.get_call_count() > 0, "No se registraron llamadas en el historial"

        last_call = mock.get_last_call()
        assert last_call is not None, "get_last_call() retornó None"
        assert last_call.cdc == test_cdc, f"CDC esperado: {test_cdc}, obtenido: {last_call.cdc}"
        assert last_call.success == True, f"Llamada no fue exitosa: {last_call.error_message}"


class TestMockSoapClientBehaviors:
    """Tests de comportamientos configurables del mock"""

    def test_mock_force_error(self):
        """Test forzar error específico"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)
        mock.force_error_response('1250', 'RUC forzado inexistente')

        xml = get_valid_factura_xml()
        response = mock.send_document(xml)

        assert response.success == False
        assert response.code == '1250'
        assert response.message == 'RUC forzado inexistente'

    def test_mock_force_timeout(self):
        """Test forzar timeout"""
        mock = MockSoapClient()
        mock.force_timeout_response(True)

        xml = get_valid_factura_xml()

        with pytest.raises(TimeoutError):
            mock.send_document(xml)

    def test_mock_custom_response_by_cdc(self):
        """Test respuesta personalizada por CDC"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)

        test_cdc = MOCK_TEST_CDCS['duplicate']
        mock.set_custom_response_for_cdc(
            test_cdc,
            'error',
            '1001',
            'CDC duplicado personalizado'
        )

        # Generar XML y reemplazar CDC
        xml = get_valid_factura_xml()
        import re
        xml_with_cdc = re.sub(
            r'<DE Id="[^"]*"',
            f'<DE Id="{test_cdc}"',
            xml
        )

        response = mock.send_document(xml_with_cdc)

        assert response.success == False
        assert response.code == '1001'
        assert response.message == 'CDC duplicado personalizado'

    def test_mock_ruc_behaviors(self):
        """Test comportamientos predefinidos por RUC"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)

        # Test RUC que siempre falla
        error_ruc = ADDITIONAL_TEST_RUCS['always_error_1250'].replace('-', '')

        # Generar XML y reemplazar RUC emisor
        xml = get_valid_factura_xml()
        import re
        xml_with_error_ruc = re.sub(
            r'<dRucEm>[^<]*</dRucEm>',
            f'<dRucEm>{error_ruc}</dRucEm>',
            xml
        )

        response = mock.send_document(xml_with_error_ruc)

        assert response.success == False
        assert response.code == '1000'

    def test_mock_maintenance_mode(self):
        """Test modo mantenimiento"""
        mock = MockSoapClient()
        mock.set_maintenance_mode(True)

        xml = get_valid_factura_xml()

        with pytest.raises(ConnectionError, match="mantenimiento"):
            mock.send_document(xml)


class TestMockSoapClientHistory:
    """Tests del historial y métricas del mock"""

    def test_mock_call_history(self):
        """Test registro de historial de llamadas"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)

        # Hacer varias llamadas
        xml1 = get_valid_factura_xml(numero_documento='001-001-0000001')
        xml2 = get_valid_factura_xml(numero_documento='001-001-0000002')

        response1 = mock.send_document(xml1)
        response2 = mock.send_document(xml2)

        # Verificar historial
        history = mock.get_call_history()
        assert len(history) == 2
        assert history[0].call_number == 1
        assert history[1].call_number == 2
        assert history[0].success == True
        assert history[1].success == True

    def test_mock_call_statistics(self):
        """Test estadísticas de llamadas"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)

        # Llamadas exitosas
        for i in range(3):
            xml = get_valid_factura_xml(numero_documento=f'001-001-{i+1:07d}')
            mock.send_document(xml)

        # Llamada con error
        mock.force_error_response('1000', 'Error forzado')
        xml_error = get_valid_factura_xml()
        mock.send_document(xml_error)

        # Verificar estadísticas
        successful_calls = mock.get_successful_calls()
        failed_calls = mock.get_failed_calls()

        assert len(successful_calls) == 3
        assert len(failed_calls) == 1
        assert mock.get_call_count() == 4

    def test_mock_response_time_simulation(self):
        """Test simulación de tiempos de respuesta"""
        mock = MockSoapClient()
        mock.configure_behavior(
            simulate_latency=True,
            latency_range=(100, 200)  # 100-200ms
        )

        start_time = time.time()
        xml = get_valid_factura_xml()
        response = mock.send_document(xml)
        end_time = time.time()

        # Verificar que se respetó la latencia mínima
        actual_time_ms = (end_time - start_time) * 1000
        assert actual_time_ms >= 100  # Al menos 100ms

        # Verificar que se registró en el historial - CON VALIDACIONES
        assert mock.get_call_count() > 0, "No se registraron llamadas en el historial"

        last_call = mock.get_last_call()
        assert last_call is not None, "get_last_call() retornó None"
        assert hasattr(
            last_call, 'response_time_ms'), "MockCallInfo no tiene atributo response_time_ms"
        assert last_call.response_time_ms >= 100, f"Tiempo registrado muy bajo: {last_call.response_time_ms}ms"

    def test_mock_clear_and_reset(self):
        """Test limpieza y reset del mock"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)

        # Hacer algunas llamadas
        xml = get_valid_factura_xml()
        mock.send_document(xml)
        mock.force_error_response('1000', 'Error')

        # Verificar estado antes del reset
        assert mock.get_call_count() > 0
        assert mock.force_error is not None

        # Limpiar historial
        mock.clear_history()
        assert mock.get_call_count() == 0
        assert len(mock.get_call_history()) == 0

        # Reset completo
        mock.reset_to_defaults()
        assert mock.force_error is None
        assert mock.failure_rate == 0.0


class TestMockSoapClientFactories:
    """Tests de las funciones factory para crear mocks"""

    def test_create_success_mock(self):
        """Test factory para mock siempre exitoso"""
        mock = create_mock_with_success_behavior()

        xml = get_valid_factura_xml()
        response = mock.send_document(xml)

        assert response.success == True
        assert mock.failure_rate == 0.0
        assert mock.timeout_rate == 0.0
        assert mock.simulate_latency == False

    def test_create_error_mock(self):
        """Test factory para mock con error"""
        mock = create_mock_with_error_behavior('1250')

        xml = get_valid_factura_xml()
        response = mock.send_document(xml)

        assert response.success == False
        assert response.code == '1250'

    def test_create_timeout_mock(self):
        """Test factory para mock con timeout"""
        mock = create_mock_with_timeout_behavior()

        xml = get_valid_factura_xml()

        with pytest.raises(TimeoutError):
            mock.send_document(xml)

    def test_create_realistic_mock(self):
        """Test factory para mock realista"""
        mock = create_mock_with_realistic_behavior()

        # Verificar configuración realista
        assert mock.failure_rate > 0.0
        assert mock.timeout_rate > 0.0
        assert mock.simulate_latency == True
        assert mock.server_load > 0.0


class TestMockSoapClientIntegration:
    """Tests de integración del mock con otros componentes"""

    # def test_mock_with_test_environment(self):
    #     """Test mock con ambiente de test completo"""
    #     test_env = get_test_environment("test_mock_integration")
    #     mock = MockSoapClient()
    #     mock.configure_behavior(simulate_latency=False)

    #     xml = get_valid_factura_xml(
    #         ruc_emisor=test_env.ruc_emisor.replace('-', '')
    #     )
    #     response = mock.send_document(xml)

    #     assert response.success == True

    #     # Cleanup
    #     test_env.cleanup()

    def test_mock_xml_validation_errors(self):
        """Test validación de XML malformado"""
        mock = MockSoapClient()
        mock.configure_behavior(simulate_latency=False)

        # XML malformado
        malformed_xml = get_xml_with_error('xml_malformado')
        response = mock.send_document(malformed_xml)

        assert response.success == False
        assert 'XML' in response.message or 'malformado' in response.message

    # @patch('app.services.sifen_client.client.SoapClient', MockSoapClient)
    # def test_mock_as_patch(self):
    #     """Test usando el mock como patch para client real"""
    #     # Este test simula cómo se usaría en tests reales
    #     xml = get_valid_factura_xml()

    #     # Crear instancia que sería del cliente real pero usa mock
    #     mock = MockSoapClient()
    #     mock.configure_behavior(simulate_latency=False)

    #     response = mock.send_document(xml)

    #     assert response.success == True
    #     assert isinstance(response.processing_time_ms, int)


# Fixtures para todos los tests
@pytest.fixture
def basic_mock():
    """Mock básico para tests rápidos"""
    mock = MockSoapClient()
    mock.configure_behavior(simulate_latency=False)
    return mock


@pytest.fixture
def realistic_mock():
    """Mock con comportamiento realista"""
    return create_mock_with_realistic_behavior()


@pytest.fixture
def valid_xml():
    """XML válido para tests"""
    return get_valid_factura_xml()


@pytest.fixture(autouse=True)
def cleanup_test_environment():
    """Cleanup automático después de cada test"""
    yield
    # Cualquier cleanup necesario aquí
    pass


# Tests con fixtures
def test_mock_with_fixtures(basic_mock, valid_xml):
    """Test usando fixtures"""
    response = basic_mock.send_document(valid_xml)

    assert response.success == True
    assert basic_mock.get_call_count() == 1


if __name__ == "__main__":
    # Permitir ejecutar el archivo directamente
    pytest.main([__file__, "-v"])
