"""
Mock SOAP client para tests offline del módulo sifen_client

Simula las respuestas del servidor SIFEN sin requerir conectividad real,
permitiendo tests rápidos, confiables y repetibles.

Funcionalidades:
- Mock completo del cliente SOAP integrado con fixtures existentes
- Respuestas realistas basadas en análisis de contenido XML
- Simulación de errores específicos de SIFEN según manual v150
- Métricas de performance simuladas realistas
- Estados configurables para diferentes escenarios
- Integración total con test_documents.py

Uso:
    from .mocks.mock_soap_client import MockSoapClient
    
    # En tests unitarios
    @patch('app.services.sifen_client.client.SoapClient', MockSoapClient)
    def test_envio_documento():
        # Test usa mock automáticamente

Ubicación: backend/app/services/sifen_client/tests/mocks/mock_soap_client.py
"""

import time
import random
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass, field

# Imports de nuestros módulos
from app.services.sifen_client.models import SifenResponse, SifenError, DocumentStatus

# Imports de nuestras fixtures
from ..fixtures.test_documents import (
    ADDITIONAL_TEST_RUCS, MOCK_TEST_CDCS, SIFEN_CODES, SIFEN_MESSAGES,
    get_sifen_mock_response, MOCK_RESPONSES,
    is_valid_cdc, extract_ruc_from_cdc, extract_document_type_from_cdc
)


@dataclass
class MockCallInfo:
    """Información de una llamada al mock para análisis posterior"""
    timestamp: datetime = field(default_factory=datetime.now)
    xml_content: str = ""
    method: str = ""
    cdc: str = ""
    ruc_emisor: str = ""
    response_code: str = ""
    response_time_ms: int = 0
    success: bool = False
    error_message: str = ""
    call_number: int = 0


class MockSoapClient:
    """
    Cliente SOAP mock que simula el comportamiento real de SIFEN

    Analiza el contenido del XML enviado y retorna respuestas
    apropiadas basadas en los datos contenidos, usando las fixtures
    y configuraciones ya definidas en test_documents.py.
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa el mock client

        Args:
            *args: Argumentos posicionales ignorados (para compatibilidad)
            **kwargs: Argumentos de palabra clave ignorados
        """
        # Configuración base del mock
        self.session = Mock()
        self.transport = Mock()
        self.call_count = 0
        self.last_request = None
        self.last_response = None

        # Configuración del comportamiento del mock
        self.simulate_latency = True
        self.latency_range = (200, 2000)  # milisegundos
        self.failure_rate = 0.0  # 0.0 = nunca falla, 1.0 = siempre falla
        self.timeout_rate = 0.0  # Probabilidad de timeout

        # Estados específicos para forzar comportamientos
        self.force_error = None
        self.force_timeout = False
        self._force_slow_response = False
        self.maintenance_mode = False

        # Historial de llamadas para validación en tests
        self.call_history: List[MockCallInfo] = []

        # Configuración de respuestas personalizadas por CDC
        self.custom_responses: Dict[str, Dict[str, Any]] = {}

        # Configuración de respuestas por RUC
        self.ruc_behaviors: Dict[str, str] = {}

        # Simulación de estado del servidor SIFEN
        self.server_load = 0.1  # 0.0 = sin carga, 1.0 = sobrecargado
        self.server_uptime = datetime.now()

        # Configurar comportamientos predefinidos
        self._setup_predefined_behaviors()

    def _setup_predefined_behaviors(self):
        """Configura comportamientos predefinidos basados en fixtures"""
        # Configurar comportamientos por RUC según fixtures
        for ruc_key, ruc_value in ADDITIONAL_TEST_RUCS.items():
            if ruc_key == 'always_success':
                self.ruc_behaviors[ruc_value] = 'success'
            elif ruc_key == 'always_error_1250':
                self.ruc_behaviors[ruc_value] = 'error_1250'
            elif ruc_key == 'always_timeout':
                self.ruc_behaviors[ruc_value] = 'timeout'
            elif ruc_key == 'slow_response':
                self.ruc_behaviors[ruc_value] = 'slow'

        # Configurar respuestas específicas por CDC
        for cdc_key, cdc_value in MOCK_TEST_CDCS.items():
            if cdc_key == 'success':
                self.custom_responses[cdc_value] = {
                    'type': 'success', 'code': '0260'}
            elif cdc_key == 'duplicate':
                self.custom_responses[cdc_value] = {
                    'type': 'error', 'code': '1001'}
            elif cdc_key == 'timeout':
                self.custom_responses[cdc_value] = {'type': 'timeout'}
            elif cdc_key == 'server_error':
                self.custom_responses[cdc_value] = {
                    'type': 'error', 'code': '5000'}

    def configure_behavior(
        self,
        failure_rate: float = 0.0,
        timeout_rate: float = 0.0,
        latency_range: Tuple[int, int] = (200, 2000),
        simulate_latency: bool = True,
        server_load: float = 0.1
    ):
        """
        Configura el comportamiento general del mock

        Args:
            failure_rate: Probabilidad de falla aleatoria (0.0-1.0)
            timeout_rate: Probabilidad de timeout (0.0-1.0)
            latency_range: Rango de latencia en milisegundos
            simulate_latency: Si simular latencia de red
            server_load: Carga simulada del servidor (0.0-1.0)
        """
        self.failure_rate = max(0.0, min(1.0, failure_rate))
        self.timeout_rate = max(0.0, min(1.0, timeout_rate))
        self.latency_range = latency_range
        self.simulate_latency = simulate_latency
        self.server_load = max(0.0, min(1.0, server_load))

    def force_error_response(
        self,
        error_code: str,
        error_message: Optional[str] = None
    ):
        """
        Fuerza una respuesta de error específica para la próxima llamada

        Args:
            error_code: Código de error SIFEN (ej: '1250', '1000')
            error_message: Mensaje personalizado (opcional)
        """
        self.force_error = {
            'code': error_code,
            'message': error_message or SIFEN_MESSAGES.get(error_code, 'Error desconocido')
        }

    def force_timeout_response(self, enable: bool = True):
        """
        Fuerza respuesta de timeout para la próxima llamada

        Args:
            enable: Si habilitar el timeout forzado
        """
        self.force_timeout = enable

    def force_slow_response(self, enable: bool = True, multiplier: int = 5):
        """
        Fuerza respuesta lenta para la próxima llamada

        Args:
            enable: Si habilitar respuesta lenta
            multiplier: Multiplicador de tiempo de respuesta
        """
        self._force_slow_response = enable
        self._slow_multiplier = multiplier

    def set_maintenance_mode(self, enable: bool = True):
        """
        Simula modo de mantenimiento del servidor SIFEN

        Args:
            enable: Si habilitar modo mantenimiento
        """
        self.maintenance_mode = enable

    def set_custom_response_for_cdc(
        self,
        cdc: str,
        response_type: str,
        code: str = "0260",
        message: Optional[str] = None
    ):
        """
        Define respuesta personalizada para un CDC específico

        Args:
            cdc: CDC del documento (44 caracteres)
            response_type: Tipo de respuesta ('success', 'error', 'timeout')
            code: Código de respuesta SIFEN
            message: Mensaje personalizado
        """
        if not is_valid_cdc(cdc):
            raise ValueError(f"CDC inválido: {cdc}")

        self.custom_responses[cdc] = {
            'type': response_type,
            'code': code,
            'message': message or SIFEN_MESSAGES.get(code, 'Respuesta personalizada')
        }

    def send_document(self, xml_content: str, **kwargs) -> SifenResponse:
        """
        Simula envío de documento a SIFEN

        Args:
            xml_content: Contenido XML del documento
            **kwargs: Parámetros adicionales (cert_serial, etc.)

        Returns:
            SifenResponse simulada basada en análisis del contenido

        Raises:
            TimeoutError: Si se simula timeout
            ConnectionError: Si se simula error de conexión
            SifenError: Si se simula error específico de SIFEN
        """
        start_time = time.time()
        self.call_count += 1
        self.last_request = xml_content

        # Crear información de la llamada
        call_info = MockCallInfo(
            xml_content=xml_content,
            method="send_document",
            call_number=self.call_count
        )

        try:
            # Analizar XML para extraer información
            cdc, ruc_emisor = self._extract_xml_info(xml_content)
            call_info.cdc = cdc
            call_info.ruc_emisor = ruc_emisor

            # Simular latencia si está habilitada
            response_time_ms = self._simulate_latency()
            call_info.response_time_ms = response_time_ms

            # Verificar condiciones de falla antes de procesar
            self._check_failure_conditions()

            # Generar respuesta basada en análisis del XML
            response = self._analyze_xml_and_respond(
                xml_content, cdc, ruc_emisor)

            # Actualizar información de la llamada
            call_info.response_code = response.code
            call_info.success = response.success
            call_info.error_message = response.message if not response.success else ""

            self.last_response = response
            return response

        except (TimeoutError, ConnectionError, SifenError) as e:
            # Registrar error en el historial
            call_info.success = False
            call_info.error_message = str(e)
            call_info.response_time_ms = int((time.time() - start_time) * 1000)
            raise

        finally:
            # Registrar llamada en historial
            self.call_history.append(call_info)

            # Limpiar flags de forzado (solo para la próxima llamada)
            self.force_error = None
            self.force_timeout = False
            self._force_slow_response = False

    def _extract_xml_info(self, xml_content: str) -> Tuple[str, str]:
        """
        Extrae información clave del XML (CDC y RUC emisor)

        Args:
            xml_content: Contenido XML

        Returns:
            Tuple con (cdc, ruc_emisor) - siempre strings, vacíos si hay error
        """
        try:
            root = ET.fromstring(xml_content)

            # Extraer CDC del atributo Id del elemento DE
            de_element = root.find(
                './/{http://ekuatia.set.gov.py/sifen/xsd}DE')
            cdc = de_element.get('Id', '') if de_element is not None else ''

            # Extraer RUC emisor - asegurar que siempre sea string
            ruc_element = root.find(
                './/{http://ekuatia.set.gov.py/sifen/xsd}dRucEm')
            ruc_emisor = (
                ruc_element.text or '') if ruc_element is not None else ''

            return cdc, ruc_emisor

        except ET.ParseError:
            # XML malformado
            return '', ''
        except Exception:
            # Cualquier otro error en parsing
            return '', ''

    def _simulate_latency(self) -> int:
        """
        Simula latencia de red realista

        Returns:
            Tiempo de respuesta en milisegundos
        """
        if not self.simulate_latency:
            return 50  # Respuesta instantánea simulada

        # Calcular latencia base
        base_latency = random.randint(*self.latency_range)

        # Ajustar por carga del servidor
        # Hasta 3x más lento si está sobrecargado
        load_factor = 1 + (self.server_load * 2)
        latency = int(base_latency * load_factor)

        # Aplicar multiplicador si está forzado
        if self.force_slow_response:
            latency *= getattr(self, '_slow_multiplier', 5)

        # Simular latencia (convertir a segundos)
        time.sleep(latency / 1000.0)

        return latency

    def _check_failure_conditions(self):
        """
        Verifica condiciones de falla y lanza excepciones según corresponda

        Raises:
            TimeoutError: Si debe simular timeout
            ConnectionError: Si debe simular error de conexión
        """
        # Modo mantenimiento
        if self.maintenance_mode:
            raise ConnectionError("Servidor SIFEN en mantenimiento")

        # Timeout forzado
        if self.force_timeout:
            raise TimeoutError("Timeout simulado del servidor SIFEN")

        # Timeout aleatorio
        if random.random() < self.timeout_rate:
            raise TimeoutError("Timeout aleatorio simulado")

        # Falla de conexión aleatoria
        if random.random() < self.failure_rate:
            raise ConnectionError("Error de conexión simulado")

    def _analyze_xml_and_respond(
        self,
        xml_content: str,
        cdc: str,
        ruc_emisor: str
    ) -> SifenResponse:
        """
        Analiza el XML y genera respuesta apropiada

        Args:
            xml_content: Contenido XML completo
            cdc: CDC extraído del XML
            ruc_emisor: RUC emisor extraído del XML

        Returns:
            SifenResponse apropiada según el contenido y configuración
        """
        # Verificar si hay error forzado
        if self.force_error:
            return self._create_error_response(
                self.force_error['code'],
                self.force_error['message']
            )

        # Verificar respuesta personalizada por CDC
        if cdc and cdc in self.custom_responses:
            custom = self.custom_responses[cdc]
            if custom['type'] == 'success':
                return self._create_success_response(cdc)
            elif custom['type'] == 'error':
                error_code = custom['code']
                error_message = custom.get('message')

                # Si no hay mensaje personalizado, usar el mensaje por defecto del código
                if not error_message:
                    error_message = SIFEN_MESSAGES.get(
                        error_code, f'Error SIFEN {error_code}')

                return self._create_error_response(error_code, error_message)
            elif custom['type'] == 'timeout':
                raise TimeoutError("Timeout configurado para CDC específico")

        # 1 Verificar comportamiento por RUC
        full_ruc = f"{ruc_emisor}-{self._calculate_dv(ruc_emisor)}"
        if full_ruc in self.ruc_behaviors:
            behavior = self.ruc_behaviors[full_ruc]
            if behavior == 'success':
                return self._create_success_response(cdc)
            elif behavior == 'error_1250':
                return self._create_error_response('1250', 'RUC emisor inexistente')
            elif behavior == 'timeout':
                raise TimeoutError("Timeout configurado para RUC específico")
            elif behavior == 'slow':
                # Ya se aplicó latencia extra en _simulate_latency
                return self._create_success_response(cdc)

        # Validaciones basadas en el contenido XML
        validation_result = self._validate_xml_content(
            xml_content, cdc, ruc_emisor)
        if not validation_result['valid']:
            return self._create_error_response(
                validation_result['error_code'],
                validation_result['error_message']
            )

        # Si todo está bien, respuesta exitosa
        return self._create_success_response(cdc)

    def _validate_xml_content(
        self,
        xml_content: str,
        cdc: str,
        ruc_emisor: str
    ) -> Dict[str, Any]:
        """
        Valida el contenido XML simulando validaciones de SIFEN

        Args:
            xml_content: Contenido XML
            cdc: CDC del documento
            ruc_emisor: RUC del emisor

        Returns:
            Dict con resultado de validación
        """
        try:
            # Validar estructura XML básica
            root = ET.fromstring(xml_content)

            # 1 Verificar si debe usar validación específica por RUC ANTES de validaciones generales
            full_ruc = f"{ruc_emisor}-{self._calculate_dv(ruc_emisor)}"
            if full_ruc in self.ruc_behaviors:
                behavior = self.ruc_behaviors[full_ruc]
                if behavior == 'error_1250':
                    return {
                        'valid': False,
                        'error_code': '1250',
                        'error_message': 'RUC emisor inexistente'
                    }
            # 2. NUEVA: Validar RUCs específicos que sabemos que son inválidos
            # RUC usado en get_xml_with_error('ruc_invalido')
            if ruc_emisor == '99999999':
                return {
                    'valid': False,
                    'error_code': '1250',
                    'error_message': 'RUC emisor inexistente'
                }

            # 3. Validar RUC emisor básico (longitud, etc.)
            if not ruc_emisor or len(ruc_emisor) < 7:
                return {
                    'valid': False,
                    'error_code': '1250',
                    'error_message': 'RUC emisor inexistente'
                }
            # 4 Validar namespace
            if 'http://ekuatia.set.gov.py/sifen/xsd' not in xml_content:
                return {
                    'valid': False,
                    'error_code': '1000',
                    'error_message': 'Namespace inválido'
                }

            # 5 Validar CDC
            if not is_valid_cdc(cdc):
                return {
                    'valid': False,
                    'error_code': '1000',
                    'error_message': 'CDC no corresponde con XML'
                }

            # Simular validación de RUC duplicado
            if cdc in MOCK_TEST_CDCS.values():
                cdc_key = next(
                    k for k, v in MOCK_TEST_CDCS.items() if v == cdc)
                if cdc_key == 'duplicate':
                    return {
                        'valid': False,
                        'error_code': '1001',
                        'error_message': 'CDC duplicado'
                    }

            # Validar elementos requeridos
            required_elements = [
                'gOpeDE', 'gTimb', 'gDatGralOpe', 'gDatRec', 'gDatEm', 'gTotSub'
            ]

            for element in required_elements:
                if root.find(f'.//{root.tag.split("}")[0][1:]}{element}') is None:
                    return {
                        'valid': False,
                        'error_code': '1000',
                        'error_message': f'Elemento requerido faltante: {element}'
                    }

            return {'valid': True, 'error_code': None, 'error_message': None}

        except ET.ParseError:
            return {
                'valid': False,
                'error_code': '1000',
                'error_message': 'XML malformado'
            }
        except Exception as e:
            return {
                'valid': False,
                'error_code': '5000',
                'error_message': f'Error interno: {str(e)}'
            }

    def _create_success_response(self, cdc: str) -> SifenResponse:
        """
        Crea respuesta exitosa simulada

        Args:
            cdc: CDC del documento

        Returns:
            SifenResponse exitosa
        """
        return SifenResponse(
            success=True,
            code=SIFEN_CODES['SUCCESS'],
            message=SIFEN_MESSAGES[SIFEN_CODES['SUCCESS']],
            protocol_number=f"PROT_MOCK_{int(time.time())}",
            cdc=cdc,
            processing_time_ms=self.call_history[-1].response_time_ms if self.call_history else 1000,
            errors=[],
            document_status=DocumentStatus.APROBADO,
        )

    def _create_error_response(self, error_code: str, error_message: str) -> SifenResponse:
        """
        Crea respuesta de error simulada

        Args:
            error_code: Código de error SIFEN
            error_message: Mensaje de error

        Returns:
            SifenResponse con error
        """
        return SifenResponse(
            success=False,
            code=error_code,
            message=error_message,
            protocol_number="",
            cdc="",
            processing_time_ms=self.call_history[-1].response_time_ms if self.call_history else 1000,
            errors=[error_message],
            document_status=DocumentStatus.RECHAZADO,
        )

    def _calculate_dv(self, ruc: str) -> str:
        """
        Calcula dígito verificador del RUC (simplificado para mock)

        Args:
            ruc: RUC sin dígito verificador

        Returns:
            Dígito verificador calculado
        """
        if not ruc or not ruc.isdigit():
            return "0"

        # Algoritmo simplificado para mock
        return str(sum(int(d) for d in ruc) % 10)

    # Métodos de utilidad para tests

    def get_call_history(self) -> List[MockCallInfo]:
        """Retorna historial completo de llamadas"""
        return self.call_history.copy()

    def get_last_call(self) -> Optional[MockCallInfo]:
        """Retorna información de la última llamada"""
        return self.call_history[-1] if self.call_history else None

    def get_call_count(self) -> int:
        """Retorna número total de llamadas realizadas"""
        return self.call_count

    def get_successful_calls(self) -> List[MockCallInfo]:
        """Retorna solo las llamadas exitosas"""
        return [call for call in self.call_history if call.success]

    def get_failed_calls(self) -> List[MockCallInfo]:
        """Retorna solo las llamadas fallidas"""
        return [call for call in self.call_history if not call.success]

    def get_average_response_time(self) -> float:
        """Retorna tiempo promedio de respuesta en ms"""
        if not self.call_history:
            return 0.0

        total_time = sum(call.response_time_ms for call in self.call_history)
        return total_time / len(self.call_history)

    def clear_history(self):
        """Limpia el historial de llamadas"""
        self.call_history.clear()
        self.call_count = 0
        self.last_request = None
        self.last_response = None

    def reset_to_defaults(self):
        """Resetea el mock a configuración por defecto"""
        self.clear_history()
        self.force_error = None
        self.force_timeout = False
        self._force_slow_response = False
        self.maintenance_mode = False
        self.failure_rate = 0.0
        self.timeout_rate = 0.0
        self.simulate_latency = True
        self.latency_range = (200, 2000)
        self.server_load = 0.1
        self.custom_responses.clear()
        self._setup_predefined_behaviors()

    # Métodos para compatibilidad con diferentes interfaces

    def __call__(self, *args, **kwargs):
        """Permite usar el mock como callable"""
        if args and isinstance(args[0], str):
            return self.send_document(args[0], **kwargs)
        return self

    def __enter__(self):
        """Soporte para context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup al salir del context manager"""
        pass


# Funciones helper para usar en tests

def create_mock_with_success_behavior() -> MockSoapClient:
    """
    Crea mock configurado para siempre responder exitosamente

    Returns:
        MockSoapClient configurado para éxito
    """
    mock = MockSoapClient()
    mock.configure_behavior(
        failure_rate=0.0,
        timeout_rate=0.0,
        simulate_latency=False
    )
    return mock


def create_mock_with_error_behavior(error_code: str = "1250") -> MockSoapClient:
    """
    Crea mock configurado para siempre fallar con código específico

    Args:
        error_code: Código de error SIFEN a simular

    Returns:
        MockSoapClient configurado para error
    """
    mock = MockSoapClient()
    mock.force_error_response(error_code)
    return mock


def create_mock_with_timeout_behavior() -> MockSoapClient:
    """
    Crea mock configurado para simular timeouts

    Returns:
        MockSoapClient configurado para timeout
    """
    mock = MockSoapClient()
    mock.configure_behavior(timeout_rate=1.0)
    return mock


def create_mock_with_realistic_behavior() -> MockSoapClient:
    """
    Crea mock con comportamiento realista (latencia, fallos ocasionales)

    Returns:
        MockSoapClient con comportamiento realista
    """
    mock = MockSoapClient()
    mock.configure_behavior(
        failure_rate=0.02,  # 2% de fallos
        timeout_rate=0.01,  # 1% de timeouts
        latency_range=(500, 3000),  # 0.5 a 3 segundos
        simulate_latency=True,
        server_load=0.3  # Carga moderada
    )
    return mock


# Decoradores para tests

def with_mock_sifen_client(mock_type: str = "success"):
    """
    Decorador para aplicar mock SIFEN client automáticamente

    Args:
        mock_type: Tipo de mock ('success', 'error', 'timeout', 'realistic')
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            if mock_type == "success":
                mock = create_mock_with_success_behavior()
            elif mock_type == "error":
                mock = create_mock_with_error_behavior()
            elif mock_type == "timeout":
                mock = create_mock_with_timeout_behavior()
            elif mock_type == "realistic":
                mock = create_mock_with_realistic_behavior()
            else:
                mock = MockSoapClient()

            # Inyectar mock en kwargs si no está presente
            if 'mock_client' not in kwargs:
                kwargs['mock_client'] = mock

            return test_func(*args, **kwargs)
        return wrapper
    return decorator


# Constantes para tests

MOCK_PERFORMANCE_BENCHMARKS = {
    'response_time_p95': 2000,  # 95% bajo 2 segundos
    'response_time_p99': 5000,  # 99% bajo 5 segundos
    'success_rate_min': 0.98,   # Mínimo 98% éxito
    'timeout_rate_max': 0.02,   # Máximo 2% timeouts
    'max_concurrent': 10        # Máximo 10 requests concurrentes
}
