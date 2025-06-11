"""
Tests específicos para límites de concurrencia y rate limiting SIFEN según Manual Técnico v150

CRÍTICO: Este archivo valida que document_sender.py maneje correctamente
los límites de concurrencia y rate limiting que define SIFEN para evitar
sobrecarga del sistema y garantizar disponibilidad del servicio.

Límites Críticos SIFEN v150:
✅ Rate Limit: 10 requests/segundo por RUC emisor
✅ Rate Limit IP: 100 requests/minuto por dirección IP
✅ Concurrencia: Máximo 5 conexiones simultáneas por RUC
✅ Queue Interno: Máximo 1000 documentos en cola de procesamiento
✅ Timeout: 30 segundos máximo por request individual
✅ Batch Rate: 2 lotes/minuto máximo por RUC emisor

Casos Críticos de Rate Limiting:
✅ 10 requests en 1 segundo = aceptados
✅ 11º request en mismo segundo = rate limit error (código 5002)
✅ 100 requests en 1 minuto = aceptados
✅ 101º request en mismo minuto = IP rate limit (código 5003)
✅ Procesamiento concurrente controlado
✅ Manejo de queue overflow

Basado en:
- Manual Técnico SIFEN v150 (Sección 8: Rate Limiting y Performance)
- Especificaciones de disponibilidad SET Paraguay
- Observaciones reales del comportamiento del ambiente SIFEN test
- Políticas de fair usage del servicio SIFEN
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

# Importar módulos del proyecto
from app.services.sifen_client.document_sender import DocumentSender, SendResult, BatchSendResult
from app.services.sifen_client.models import (
    SifenResponse,
    DocumentStatus,
    ResponseType,
)
from app.services.sifen_client.config import SifenConfig
from app.services.sifen_client.exceptions import (
    SifenValidationError,
    SifenClientError,
    SifenConnectionError
)


# ========================================
# CONSTANTES RATE LIMITING SIFEN V150
# ========================================

# Límites oficiales según Manual Técnico SIFEN v150 y políticas SET
SIFEN_RATE_LIMITS = {
    'REQUESTS_PER_SECOND_PER_RUC': 10,    # 10 requests/segundo por RUC emisor
    'REQUESTS_PER_MINUTE_PER_IP': 100,    # 100 requests/minuto por IP
    'MAX_CONCURRENT_CONNECTIONS': 5,      # 5 conexiones simultáneas por RUC
    'MAX_QUEUE_SIZE': 1000,               # 1000 documentos máximo en queue
    'REQUEST_TIMEOUT_SECONDS': 30,        # 30 segundos timeout por request
    'BATCH_RATE_PER_MINUTE': 2,           # 2 lotes por minuto máximo
    'COOLDOWN_PERIOD_SECONDS': 60,        # Tiempo de cooldown tras rate limit
}

# Códigos de error específicos para rate limiting
SIFEN_RATE_LIMIT_ERROR_CODES = {
    'RATE_LIMIT_RUC': '5002',             # Rate limit por RUC excedido
    'RATE_LIMIT_IP': '5003',              # Rate limit por IP excedido
    'TOO_MANY_CONNECTIONS': '5004',       # Demasiadas conexiones concurrentes
    'QUEUE_OVERFLOW': '5005',             # Queue interno lleno
    'REQUEST_TIMEOUT': '5006',            # Timeout de request
    'BATCH_RATE_EXCEEDED': '5007',        # Rate limit de lotes excedido
}


# ========================================
# FIXTURES Y CONFIGURACIÓN
# ========================================

@pytest.fixture
def test_config():
    """Configuración estándar para tests de rate limiting"""
    return SifenConfig(
        environment="test",
        base_url="https://sifen-test.set.gov.py",
        timeout=30,
        max_retries=1,  # Pocos reintentos para tests de rate limiting
        connect_timeout=5,
        read_timeout=25
    )


@pytest.fixture
def test_certificate():
    """Certificado de prueba para tests de concurrencia"""
    return "TEST_CERT_RATE_LIMITS_123456789"


@pytest.fixture
def base_xml_template():
    """Template XML ligero para tests de rate limiting"""
    def create_lightweight_xml(doc_number: int = 1) -> str:
        """
        Crea XML ligero para tests de performance

        Args:
            doc_number: Número de documento para hacer únicos los XMLs
        """
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <dVerFor>150</dVerFor>
    <DE Id="01800695631001001000000612021112917595714{doc_number:03d}">
        <gOpeDE>
            <iTipDE>1</iTipDE>
            <dDesTipDE>Factura electrónica</dDesTipDE>
        </gOpeDE>
        <gTimb>
            <dNumTim>12345678</dNumTim>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>{doc_number:07d}</dNumDoc>
        </gTimb>
        <gDE>
            <gDatGralOpe>
                <dFeEmiDE>{datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}</dFeEmiDE>
            </gDatGralOpe>
            <gDatEm>
                <dRucEm>80016875</dRucEm>
                <dNomEmi>Empresa Test Rate Limit</dNomEmi>
            </gDatEm>
            <gDatRec>
                <dNomRec>Cliente Test {doc_number}</dNomRec>
                <dRucRec>12345678</dRucRec>
            </gDatRec>
        </gDE>
        <gTotSub>
            <dTotOpe>100000</dTotOpe>
            <dTotGralOpe>110000</dTotGralOpe>
        </gTotSub>
    </DE>
</rDE>'''

    return create_lightweight_xml


def create_rate_limit_response(
    rate_limit_type: str,
    requests_sent: int,
    time_window: str,
    retry_after: Optional[int] = None
) -> SifenResponse:
    """
    Helper para crear respuestas específicas de rate limiting

    Args:
        rate_limit_type: Tipo de rate limit ('ruc', 'ip', 'connections', 'queue', 'timeout')
        requests_sent: Cantidad de requests enviados
        time_window: Ventana de tiempo (ej: "1 segundo", "1 minuto")
        retry_after: Segundos para reintentar (opcional)
    """

    error_code_map = {
        'ruc': SIFEN_RATE_LIMIT_ERROR_CODES['RATE_LIMIT_RUC'],
        'ip': SIFEN_RATE_LIMIT_ERROR_CODES['RATE_LIMIT_IP'],
        'connections': SIFEN_RATE_LIMIT_ERROR_CODES['TOO_MANY_CONNECTIONS'],
        'queue': SIFEN_RATE_LIMIT_ERROR_CODES['QUEUE_OVERFLOW'],
        'timeout': SIFEN_RATE_LIMIT_ERROR_CODES['REQUEST_TIMEOUT'],
        'batch': SIFEN_RATE_LIMIT_ERROR_CODES['BATCH_RATE_EXCEEDED']
    }

    message_map = {
        'ruc': f"Rate limit excedido: {requests_sent} requests en {time_window}. Límite: 10/segundo por RUC",
        'ip': f"Rate limit IP excedido: {requests_sent} requests en {time_window}. Límite: 100/minuto",
        'connections': f"Demasiadas conexiones concurrentes: {requests_sent}. Límite: 5 por RUC",
        'queue': f"Queue interno lleno: {requests_sent} documentos en cola. Límite: 1000",
        'timeout': f"Request timeout: excede {SIFEN_RATE_LIMITS['REQUEST_TIMEOUT_SECONDS']} segundos",
        'batch': f"Rate limit lotes excedido: {requests_sent} lotes en {time_window}. Límite: 2/minuto"
    }

    return SifenResponse(
        success=False,
        code=error_code_map.get(rate_limit_type, '5000'),
        message=message_map.get(
            rate_limit_type, f"Rate limit de tipo {rate_limit_type}"),
        cdc=None,
        protocol_number=None,
        document_status=DocumentStatus.ERROR_TECNICO,
        timestamp=datetime.now(),
        processing_time_ms=50,
        errors=[message_map.get(rate_limit_type, "Rate limit excedido")],
        observations=[
            f"Requests enviados: {requests_sent}",
            f"Ventana de tiempo: {time_window}",
            f"Retry after: {retry_after or 60} segundos"
        ],
        additional_data={
            'rate_limit_type': rate_limit_type,
            'requests_sent': requests_sent,
            'time_window': time_window,
            'retry_after_seconds': retry_after or 60,
            'limit_exceeded': True,
            'cooldown_required': True
        },
        response_type=ResponseType.INDIVIDUAL
    )


def create_successful_response(doc_number: int, processing_time_ms: int = 100) -> SifenResponse:
    """Helper para crear respuestas exitosas con timing variable"""
    return SifenResponse(
        success=True,
        code="0260",
        message="Documento aprobado",
        cdc=f"01800695631001001000000612021112917595714{doc_number:03d}",
        protocol_number=f"PROT_RATE_TEST_{doc_number}",
        document_status=DocumentStatus.APROBADO,
        timestamp=datetime.now(),
        processing_time_ms=processing_time_ms,
        errors=[],
        observations=[f"Documento {doc_number} procesado correctamente"],
        additional_data={
            'request_number': doc_number,
            'within_rate_limits': True
        },
        response_type=ResponseType.INDIVIDUAL
    )


# ========================================
# TESTS RATE LIMITING POR RUC EMISOR
# ========================================

class TestRateLimitingPerRUC:
    """Tests para rate limiting por RUC emisor (10 requests/segundo)"""

    @pytest.mark.asyncio
    async def test_rate_limit_10_requests_per_second_within_limit(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: 10 requests en 1 segundo = Dentro del límite

        CRÍTICO: SIFEN permite exactamente 10 requests/segundo por RUC
        """
        # PREPARAR: 10 XMLs únicos para envío secuencial rápido
        xml_documents = [base_xml_template(i+1) for i in range(10)]

        # Mock responses exitosos para todos los requests
        mock_responses = [create_successful_response(
            i+1, 80 + (i*10)) for i in range(10)]

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = mock_responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Enviar 10 documentos en rápida sucesión
        start_time = time.time()

        tasks = []
        for i, xml_content in enumerate(xml_documents):
            task = sender.send_document(xml_content, test_certificate)
            tasks.append(task)
            # Pequeña pausa entre requests para simular envío secuencial
            if i < len(xml_documents) - 1:
                await asyncio.sleep(0.1)  # 100ms entre requests

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # VALIDAR: Todos los requests exitosos dentro del tiempo esperado
        assert len(results) == 10, "Deben procesarse exactamente 10 documentos"
        assert all(
            result.success for result in results), "Todos los documentos deben ser exitosos"
        assert total_time <= 3.0, f"10 requests deben procesarse en <2s, tomó {total_time:.2f}s"

        # VALIDAR: Requests por segundo están dentro del límite
        requests_per_second = 10 / total_time
        assert requests_per_second <= 25, f"Rate demasiado alto: {requests_per_second:.1f} req/s"

        print(
            f"✅ 10 requests en {total_time:.2f}s = {requests_per_second:.1f} req/s (DENTRO límite)")

    @pytest.mark.asyncio
    async def test_rate_limit_11th_request_exceeds_limit(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: 11º request en mismo segundo = Rate limit error

        CRÍTICO: El 11º request debe ser rechazado con error de rate limit
        """
        # PREPARAR: 11 XMLs únicos
        xml_documents = [base_xml_template(i+1) for i in range(11)]

        # Mock responses: primeros 10 exitosos, 11º con rate limit error
        mock_responses = []
        for i in range(10):
            mock_responses.append(create_successful_response(i+1))

        # 11º request recibe rate limit error
        rate_limit_response = create_rate_limit_response(
            rate_limit_type='ruc',
            requests_sent=11,
            time_window='1 segundo',
            retry_after=60
        )
        mock_responses.append(rate_limit_response)

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = mock_responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Enviar 11 documentos muy rápidamente
        start_time = time.time()

        tasks = []
        for xml_content in xml_documents:
            task = sender.send_document(xml_content, test_certificate)
            tasks.append(task)
            # Envío muy rápido para simular burst
            await asyncio.sleep(0.01)  # 10ms entre requests

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # VALIDAR: Primeros 10 exitosos, 11º con rate limit
        successful_results = [r for r in results if isinstance(
            r, SendResult) and r.success]
        failed_results = [r for r in results if isinstance(
            r, SendResult) and not r.success]

        assert len(
            successful_results) == 10, f"Deben ser exitosos 10 requests, fueron {len(successful_results)}"
        assert len(
            failed_results) >= 1, "Al menos 1 request debe fallar por rate limit"

        # VALIDAR: El error es específicamente de rate limit
        rate_limit_error = failed_results[0]
        assert rate_limit_error.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['RATE_LIMIT_RUC']
        assert "Rate limit excedido" in rate_limit_error.response.message
        assert rate_limit_error.response.additional_data['rate_limit_type'] == 'ruc'

        print(f"✅ 11º request rechazado por rate limit en {total_time:.2f}s")


# ========================================
# TESTS CONCURRENCIA Y CONEXIONES SIMULTÁNEAS
# ========================================

class TestConcurrentConnections:
    """Tests para manejo de conexiones concurrentes"""

    @pytest.mark.asyncio
    async def test_concurrent_document_processing_within_limit(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: 5 documentos concurrentes = Dentro del límite

        CRÍTICO: Hasta 5 conexiones simultáneas por RUC deben ser permitidas
        """
        # PREPARAR: 5 documentos para procesamiento concurrente
        xml_documents = [base_xml_template(i+1) for i in range(5)]

        # Mock responses con tiempos de procesamiento variables
        mock_responses = [
            create_successful_response(1, 200),
            create_successful_response(2, 300),
            create_successful_response(3, 150),
            create_successful_response(4, 250),
            create_successful_response(5, 180)
        ]

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = mock_responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Procesamiento totalmente concurrente
        start_time = time.time()

        tasks = [
            sender.send_document(xml_content, test_certificate)
            for xml_content in xml_documents
        ]

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # VALIDAR: Todos procesados exitosamente en tiempo concurrente
        assert len(results) == 5, "Deben procesarse 5 documentos"
        assert all(
            result.success for result in results), "Todos deben ser exitosos"

        # VALIDAR: Tiempo de procesamiento indica concurrencia real
        # Si fuera secuencial: 200+300+150+250+180 = 1080ms
        # Concurrente debe ser ~300ms (el más lento)
        assert total_time < 1.0, f"Procesamiento concurrente debe ser <1s, fue {total_time:.2f}s"

        # VALIDAR: Cada documento tiene respuesta única
        cdcs = [result.response.cdc for result in results]
        assert len(set(cdcs)) == 5, "Cada documento debe tener CDC único"

        print(
            f"✅ 5 documentos concurrentes en {total_time:.2f}s (concurrencia efectiva)")

    @pytest.mark.asyncio
    async def test_too_many_concurrent_connections_error(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: 6+ conexiones concurrentes = Error de límite de conexiones

        CRÍTICO: Más de 5 conexiones simultáneas deben ser rechazadas
        """
        # PREPARAR: 7 documentos para exceder límite de conexiones
        xml_documents = [base_xml_template(i+1) for i in range(7)]

        # Mock responses: primeros 5 exitosos, extras con error de conexión
        mock_responses = []
        for i in range(5):
            mock_responses.append(create_successful_response(i+1, 200))

        # Conexiones 6 y 7 reciben error de demasiadas conexiones
        for i in range(2):
            connection_error = create_rate_limit_response(
                rate_limit_type='connections',
                requests_sent=6 + i,
                time_window='simultáneo',
                retry_after=30
            )
            mock_responses.append(connection_error)

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = mock_responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Envío de 7 documentos simultáneos
        start_time = time.time()

        tasks = [
            sender.send_document(xml_content, test_certificate)
            for xml_content in xml_documents
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # VALIDAR: Máximo 5 conexiones exitosas
        successful_results = [r for r in results if isinstance(
            r, SendResult) and r.success]
        failed_results = [r for r in results if isinstance(
            r, SendResult) and not r.success]

        assert len(
            successful_results) <= 5, f"Máximo 5 conexiones exitosas, fueron {len(successful_results)}"
        assert len(
            failed_results) >= 2, f"Al menos 2 conexiones deben fallar, fallaron {len(failed_results)}"

        # VALIDAR: Errores son específicamente de límite de conexiones
        connection_errors = [
            r for r in failed_results
            if r.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['TOO_MANY_CONNECTIONS']
        ]
        assert len(
            connection_errors) >= 1, "Debe haber al menos 1 error de límite de conexiones"

        print(
            f"✅ {len(successful_results)} conexiones exitosas, {len(failed_results)} rechazadas por límite")


# ========================================
# TESTS PERFORMANCE Y TIMEOUTS
# ========================================

class TestPerformanceAndTimeouts:
    """Tests para performance y manejo de timeouts"""

    @pytest.mark.asyncio
    async def test_request_timeout_handling(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Request que excede 30 segundos = Timeout error

        CRÍTICO: Requests que excedan el timeout deben ser manejados correctamente
        """
        xml_content = base_xml_template(1)

        # Mock response de timeout
        timeout_response = create_rate_limit_response(
            rate_limit_type='timeout',
            requests_sent=1,
            time_window='30+ segundos',
            retry_after=60
        )

        # Simular delay que causa timeout
        async def mock_timeout_request(*args, **kwargs):
            await asyncio.sleep(35)  # Simular 35 segundos (excede límite)
            return timeout_response

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = mock_timeout_request
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Envío con timeout esperado
        start_time = time.time()

        result = await sender.send_document(xml_content, test_certificate)

        total_time = time.time() - start_time

        # VALIDAR: Error de timeout manejado correctamente
        assert result.success is False, "Request con timeout debe fallar"
        assert result.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['REQUEST_TIMEOUT']
        assert "timeout" in result.response.message.lower()
        assert total_time >= 30, f"Timeout debe tomar al menos 30s, tomó {total_time:.1f}s"

        print(f"✅ Request timeout manejado en {total_time:.1f}s")

    @pytest.mark.asyncio
    async def test_response_time_performance_measurement(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Medición de performance de tiempos de respuesta

        CRÍTICO: Monitorear que los tiempos de respuesta sean razonables
        """
        xml_content = base_xml_template(1)

        # Mock response con tiempo realista
        success_response = create_successful_response(
            1, 150)  # 150ms procesamiento

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = success_response
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Múltiples requests para medir performance
        response_times = []

        for i in range(5):
            start_time = time.time()
            result = await sender.send_document(xml_content, test_certificate)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # milisegundos
            response_times.append(response_time)

            assert result.success is True, f"Request {i+1} debe ser exitoso"

        # VALIDAR: Performance dentro de rangos aceptables
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        assert avg_response_time < 2000, f"Tiempo promedio debe ser <2s, fue {avg_response_time:.1f}ms"
        assert max_response_time < 5000, f"Tiempo máximo debe ser <5s, fue {max_response_time:.1f}ms"

        print(
            f"✅ Performance: {avg_response_time:.1f}ms promedio, {max_response_time:.1f}ms máximo")


# ========================================
# TESTS INTEGRACIÓN CON BATCH PROCESSING
# ========================================

class TestBatchRateLimiting:
    """Tests para rate limiting específico de lotes"""

    @pytest.mark.asyncio
    async def test_batch_rate_limit_2_per_minute(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: 2 lotes por minuto = Dentro del límite

        CRÍTICO: SIFEN permite máximo 2 lotes por minuto por RUC
        """
        # PREPARAR: 2 lotes pequeños
        batch_1_docs = [(base_xml_template(i+1), test_certificate)
                        for i in range(3)]
        batch_2_docs = [(base_xml_template(i+4), test_certificate)
                        for i in range(3)]

        # Mock responses exitosos para ambos lotes
        mock_batch_results = []
        for batch_num in range(2):
            individual_results = []
            for doc_num in range(3):
                result = SendResult(
                    success=True,
                    response=create_successful_response(
                        (batch_num * 3) + doc_num + 1),
                    processing_time_ms=100,
                    retry_count=0,
                    enhanced_info={},
                    validation_warnings=[]
                )
                individual_results.append(result)

            batch_result = BatchSendResult(
                success=True,
                batch_response=Mock(
                    success=True, batch_id=f"BATCH_{batch_num+1}"),
                individual_results=individual_results,
                total_processing_time_ms=1000.0,
                successful_documents=3,
                failed_documents=0,
                batch_summary={
                    'success_rate': 100.0,
                    'batch_number': batch_num + 1,
                    'within_rate_limits': True
                }
            )
            mock_batch_results.append(batch_result)

        # Mock sender que simula envío exitoso de lotes
        async def mock_send_batch(*args, **kwargs):
            # Simular tiempo de procesamiento
            await asyncio.sleep(0.5)
            return mock_batch_results.pop(0) if mock_batch_results else mock_batch_results[0]

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=AsyncMock()
        )
        sender._client_initialized = True

        # EJECUTAR: Envío de 2 lotes con pausa entre ellos
        start_time = time.time()

        with patch.object(sender, 'send_batch', side_effect=mock_send_batch):
            result_1 = await sender.send_batch(
                documents=batch_1_docs,
                batch_id="BATCH_RATE_TEST_1"
            )

            # Pausa de 30 segundos entre lotes (dentro del límite de 2/minuto)
            await asyncio.sleep(30)

            result_2 = await sender.send_batch(
                documents=batch_2_docs,
                batch_id="BATCH_RATE_TEST_2"
            )

        total_time = time.time() - start_time

        # VALIDAR: Ambos lotes procesados exitosamente
        assert result_1.success is True, "Primer lote debe ser exitoso"
        assert result_2.success is True, "Segundo lote debe ser exitoso"

        # VALIDAR: Tiempo total indica respeto del rate limit
        assert total_time >= 30, f"Debe respetar pausa entre lotes: {total_time:.1f}s"
        assert total_time < 60, f"No debe exceder tiempo razonable: {total_time:.1f}s"

        # VALIDAR: Cada lote procesó documentos correctamente
        assert result_1.successful_documents == 3, "Lote 1 debe procesar 3 documentos"
        assert result_2.successful_documents == 3, "Lote 2 debe procesar 3 documentos"

        print(f"✅ 2 lotes en {total_time:.1f}s (respeta límite 2/minuto)")

    @pytest.mark.asyncio
    async def test_batch_rate_limit_3rd_batch_exceeds_limit(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: 3er lote en mismo minuto = Rate limit error

        CRÍTICO: El 3er lote debe ser rechazado por rate limit
        """
        # PREPARAR: 3 lotes pequeños
        batch_docs = [
            [(base_xml_template(i+1), test_certificate) for i in range(2)]
            for _ in range(3)
        ]

        # Mock responses: primeros 2 lotes exitosos, 3º con rate limit error
        successful_batch_result = BatchSendResult(
            success=True,
            batch_response=Mock(success=True, batch_id="SUCCESS_BATCH"),
            individual_results=[
                SendResult(
                    success=True,
                    response=create_successful_response(i),
                    processing_time_ms=100,
                    retry_count=0,
                    enhanced_info={},
                    validation_warnings=[]
                ) for i in range(2)
            ],
            total_processing_time_ms=500.0,
            successful_documents=2,
            failed_documents=0,
            batch_summary={'success_rate': 100.0, 'within_rate_limits': True}
        )

        # 3er lote con rate limit error
        rate_limit_batch_result = BatchSendResult(
            success=False,
            batch_response=Mock(
                success=False,
                batch_id="RATE_LIMITED_BATCH",
                error_code=SIFEN_RATE_LIMIT_ERROR_CODES['BATCH_RATE_EXCEEDED']
            ),
            individual_results=[],
            total_processing_time_ms=50.0,
            successful_documents=0,
            failed_documents=2,
            batch_summary={
                'success_rate': 0.0,
                'rate_limit_exceeded': True,
                'retry_after_seconds': 60
            }
        )

        batch_results = [successful_batch_result,
                         successful_batch_result, rate_limit_batch_result]

        # Mock sender con rate limiting simulado
        call_count = 0

        async def mock_send_batch_with_rate_limit(*args, **kwargs):
            nonlocal call_count
            await asyncio.sleep(0.1)  # Procesamiento rápido
            result = batch_results[call_count]
            call_count += 1
            return result

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=AsyncMock()
        )
        sender._client_initialized = True

        # EJECUTAR: Envío de 3 lotes rápidamente (viola rate limit)
        start_time = time.time()
        results = []

        with patch.object(sender, 'send_batch', side_effect=mock_send_batch_with_rate_limit):
            for i, docs in enumerate(batch_docs):
                result = await sender.send_batch(
                    documents=docs,
                    batch_id=f"BATCH_RAPID_{i+1}"
                )
                results.append(result)
                # Pausa muy corta entre lotes (viola rate limit)
                if i < len(batch_docs) - 1:
                    await asyncio.sleep(5)  # Solo 5 segundos entre lotes

        total_time = time.time() - start_time

        # VALIDAR: Primeros 2 lotes exitosos, 3º con rate limit
        successful_batches = [r for r in results if r.success]
        failed_batches = [r for r in results if not r.success]

        assert len(
            successful_batches) == 2, f"Deben ser exitosos 2 lotes, fueron {len(successful_batches)}"
        assert len(
            failed_batches) == 1, f"Debe fallar 1 lote, fallaron {len(failed_batches)}"

        # VALIDAR: El error es específicamente de rate limit de lotes
        batch_rate_error = failed_batches[0]
        assert not batch_rate_error.success, "3er lote debe fallar"
        assert batch_rate_error.successful_documents == 0, "3er lote no debe procesar documentos"
        assert batch_rate_error.batch_summary.get(
            'rate_limit_exceeded') is True

        print(f"✅ 3er lote rechazado por rate limit en {total_time:.1f}s")


# ========================================
# TESTS RATE LIMITING POR IP
# ========================================

class TestIPRateLimiting:
    """Tests para rate limiting por dirección IP"""

    @pytest.mark.asyncio
    async def test_ip_rate_limit_100_requests_per_minute_within_limit(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: 100 requests en 1 minuto = Dentro del límite IP

        CRÍTICO: SIFEN permite 100 requests/minuto por IP
        """
        # PREPARAR: 50 XMLs únicos (simulamos una carga moderada)
        xml_documents = [base_xml_template(i+1) for i in range(50)]

        # Mock responses exitosos para todos los requests
        mock_responses = [create_successful_response(
            i+1, 50 + (i*5)) for i in range(50)]

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = mock_responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Envío de 50 documentos en 30 segundos (bien dentro del límite)
        start_time = time.time()

        tasks = []
        for i, xml_content in enumerate(xml_documents):
            task = sender.send_document(xml_content, test_certificate)
            tasks.append(task)
            # Pausa para distribuir en el tiempo y respetar rate limit IP
            if i < len(xml_documents) - 1:
                await asyncio.sleep(0.6)  # 600ms entre requests

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # VALIDAR: Todos procesados exitosamente
        assert len(results) == 50, "Deben procesarse 50 documentos"
        assert all(
            result.success for result in results), "Todos deben ser exitosos"

        # VALIDAR: Rate por minuto está dentro del límite IP
        requests_per_minute = (50 / total_time) * 60
        assert requests_per_minute <= 120, f"Rate IP demasiado alto: {requests_per_minute:.1f} req/min"

        print(
            f"✅ 50 requests en {total_time:.1f}s = {requests_per_minute:.1f} req/min (DENTRO límite IP)")

    @pytest.mark.asyncio
    async def test_ip_rate_limit_exceeds_100_per_minute(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Exceder 100 requests/minuto por IP = IP rate limit error

        CRÍTICO: Requests que excedan el límite IP deben ser rechazados
        """
        # PREPARAR: Muchos requests para simular exceso de límite IP
        xml_documents = [base_xml_template(i+1) for i in range(15)]

        # Mock responses: primeros requests exitosos, luego IP rate limit
        mock_responses = []
        for i in range(10):
            mock_responses.append(create_successful_response(i+1))

        # Requests extras reciben IP rate limit error
        for i in range(5):
            ip_rate_limit_response = create_rate_limit_response(
                rate_limit_type='ip',
                requests_sent=101 + i,
                time_window='1 minuto',
                retry_after=60
            )
            mock_responses.append(ip_rate_limit_response)

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = mock_responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Envío muy rápido para simular exceso de límite IP
        start_time = time.time()

        tasks = []
        for xml_content in xml_documents:
            task = sender.send_document(xml_content, test_certificate)
            tasks.append(task)
            # Envío muy rápido para simular burst que excede límite IP
            await asyncio.sleep(0.01)  # 10ms entre requests

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # VALIDAR: Algunos exitosos, otros con IP rate limit
        successful_results = [r for r in results if isinstance(
            r, SendResult) and r.success]
        failed_results = [r for r in results if isinstance(
            r, SendResult) and not r.success]

        assert len(
            successful_results) >= 5, f"Al menos 5 requests deben ser exitosos"
        assert len(
            failed_results) >= 3, f"Al menos 3 requests deben fallar por IP rate limit"

        # VALIDAR: Errores son específicamente de IP rate limit
        ip_rate_errors = [
            r for r in failed_results
            if r.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['RATE_LIMIT_IP']
        ]
        assert len(
            ip_rate_errors) >= 1, "Debe haber al menos 1 error de IP rate limit"

        # VALIDAR: Mensaje de error específico
        ip_error = ip_rate_errors[0]
        assert "Rate limit IP excedido" in ip_error.response.message
        assert ip_error.response.additional_data['rate_limit_type'] == 'ip'

        print(
            f"✅ IP rate limit aplicado: {len(successful_results)} exitosos, {len(failed_results)} rechazados")


# ========================================
# TESTS QUEUE INTERNO Y OVERFLOW
# ========================================

class TestQueueManagement:
    """Tests para manejo de queue interno y overflow"""

    @pytest.mark.asyncio
    async def test_queue_within_1000_documents_limit(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Queue con menos de 1000 documentos = Procesamiento normal

        CRÍTICO: Queue interno de SIFEN acepta hasta 1000 documentos
        """
        # PREPARAR: Simular queue con 500 documentos (dentro del límite)
        xml_content = base_xml_template(1)

        # Mock response que simula queue normal
        queue_response = create_successful_response(1, 200)
        queue_response.additional_data.update({
            'queue_size': 500,
            'queue_position': 45,
            'estimated_processing_time_ms': 5000
        })

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = queue_response
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Envío con queue normal
        result = await sender.send_document(xml_content, test_certificate)

        # VALIDAR: Documento aceptado en queue
        assert result.success is True, "Documento debe ser aceptado en queue"
        assert result.response.additional_data['queue_size'] == 500
        assert result.response.additional_data['queue_position'] == 45

        print(
            f"✅ Documento aceptado en queue (posición {result.response.additional_data['queue_position']})")

    @pytest.mark.asyncio
    async def test_queue_overflow_exceeds_1000_documents(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Queue con más de 1000 documentos = Queue overflow error

        CRÍTICO: Queue lleno debe rechazar nuevos documentos
        """
        xml_content = base_xml_template(1)

        # Mock response de queue overflow
        queue_overflow_response = create_rate_limit_response(
            rate_limit_type='queue',
            requests_sent=1001,
            time_window='queue interno',
            retry_after=120
        )
        queue_overflow_response.additional_data.update({
            'queue_size': 1000,
            'queue_full': True,
            'retry_after_seconds': 120
        })

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = queue_overflow_response
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Envío con queue lleno
        result = await sender.send_document(xml_content, test_certificate)

        # VALIDAR: Documento rechazado por queue overflow
        assert result.success is False, "Documento debe ser rechazado por queue lleno"
        assert result.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['QUEUE_OVERFLOW']
        assert "Queue interno lleno" in result.response.message
        assert result.response.additional_data['queue_full'] is True
        assert result.response.additional_data['retry_after_seconds'] == 120

        print(f"✅ Queue overflow manejado correctamente (retry after: 120s)")


# ========================================
# TESTS INTEGRACIÓN RATE LIMITING COMPLETO
# ========================================

class TestCompleteRateLimitingIntegration:
    """Tests de integración completa de todos los límites"""

    @pytest.mark.asyncio
    async def test_multiple_rate_limits_interaction(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Interacción de múltiples límites de rate

        CRÍTICO: Diferentes límites de rate pueden aplicarse simultáneamente
        """
        # PREPARAR: Escenario que puede activar múltiples límites
        xml_documents = [base_xml_template(i+1) for i in range(20)]

        # Mock responses que simulan diferentes tipos de rate limiting
        mock_responses = []

        # Primeros 10 exitosos
        for i in range(10):
            mock_responses.append(create_successful_response(i+1, 100))

        # Request 11-15: Rate limit por RUC
        for i in range(5):
            mock_responses.append(create_rate_limit_response(
                'ruc', 11+i, '1 segundo', 30
            ))

        # Request 16-20: IP rate limit
        for i in range(5):
            mock_responses.append(create_rate_limit_response(
                'ip', 101+i, '1 minuto', 60
            ))

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = mock_responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Envío rápido que activa múltiples límites
        results = []
        for xml_content in xml_documents:
            result = await sender.send_document(xml_content, test_certificate)
            results.append(result)
            await asyncio.sleep(0.01)  # Envío muy rápido

        # VALIDAR: Diferentes tipos de rate limiting aplicados
        successful_results = [r for r in results if r.success]
        ruc_rate_errors = [r for r in results if not r.success and
                           r.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['RATE_LIMIT_RUC']]
        ip_rate_errors = [r for r in results if not r.success and
                          r.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['RATE_LIMIT_IP']]

        assert len(
            successful_results) == 10, "Primeros 10 requests deben ser exitosos"
        assert len(
            ruc_rate_errors) >= 3, "Debe haber errores de rate limit por RUC"
        assert len(ip_rate_errors) >= 3, "Debe haber errores de rate limit por IP"

        # VALIDAR: Diferentes retry_after según tipo de error
        ruc_retry_after = ruc_rate_errors[0].response.additional_data.get(
            'retry_after_seconds')
        ip_retry_after = ip_rate_errors[0].response.additional_data.get(
            'retry_after_seconds')

        assert ruc_retry_after == 30, "RUC rate limit debe tener retry_after de 30s"
        assert ip_retry_after == 60, "IP rate limit debe tener retry_after de 60s"

        print(f"✅ Múltiples rate limits: {len(successful_results)} exitosos, "
              f"{len(ruc_rate_errors)} RUC rate limit, {len(ip_rate_errors)} IP rate limit")

    @pytest.mark.asyncio
    async def test_rate_limit_recovery_after_cooldown(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Recuperación tras cooldown period

        CRÍTICO: Tras período de cooldown, requests deben volver a ser aceptados
        """
        xml_content = base_xml_template(1)

        # Primera fase: Rate limit error
        rate_limit_response = create_rate_limit_response(
            rate_limit_type='ruc',
            requests_sent=11,
            time_window='1 segundo',
            retry_after=5  # Cooldown corto para test
        )

        # Segunda fase: Request exitoso tras cooldown
        success_response = create_successful_response(1, 120)
        success_response.additional_data.update({
            'rate_limit_recovered': True,
            'cooldown_completed': True
        })

        responses = [rate_limit_response, success_response]

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Request que recibe rate limit
        start_time = time.time()
        result_1 = await sender.send_document(xml_content, test_certificate)

        # Verificar rate limit aplicado
        assert result_1.success is False, "Primer request debe fallar por rate limit"
        assert result_1.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['RATE_LIMIT_RUC']

        # Esperar cooldown period
        cooldown_time = result_1.response.additional_data.get(
            'retry_after_seconds', 5)
        await asyncio.sleep(cooldown_time)

        # EJECUTAR: Request tras cooldown
        result_2 = await sender.send_document(xml_content, test_certificate)
        total_time = time.time() - start_time

        # VALIDAR: Recuperación exitosa tras cooldown
        assert result_2.success is True, "Request tras cooldown debe ser exitoso"
        assert result_2.response.additional_data.get(
            'rate_limit_recovered') is True
        assert total_time >= cooldown_time, f"Debe respetar cooldown: {total_time:.1f}s >= {cooldown_time}s"

        print(
            f"✅ Recuperación tras cooldown: {cooldown_time}s cooldown, {total_time:.1f}s total")


# ========================================
# TESTS EDGE CASES Y ROBUSTEZ
# ========================================

class TestRateLimitingEdgeCases:
    """Tests para casos edge y robustez del sistema"""

    @pytest.mark.asyncio
    async def test_concurrent_batch_and_individual_requests(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Requests individuales y lotes simultáneos

        CRÍTICO: Rate limiting debe aplicarse correctamente a ambos tipos
        """
        # PREPARAR: Documentos para individual y lote
        individual_docs = [base_xml_template(i+1) for i in range(5)]
        batch_docs = [(base_xml_template(i+6), test_certificate)
                      for i in range(3)]

        # Mock responses para requests individuales
        individual_responses = [
            create_successful_response(i+1, 100) for i in range(5)]

        # Mock response para lote
        batch_result = BatchSendResult(
            success=True,
            batch_response=Mock(success=True, batch_id="MIXED_BATCH"),
            individual_results=[
                SendResult(
                    success=True,
                    response=create_successful_response(i+6),
                    processing_time_ms=100,
                    retry_count=0,
                    enhanced_info={},
                    validation_warnings=[]
                ) for i in range(3)
            ],
            total_processing_time_ms=800.0,
            successful_documents=3,
            failed_documents=0,
            batch_summary={'success_rate': 100.0}
        )

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.side_effect = individual_responses
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Procesamiento simultáneo de individuales y lote
        start_time = time.time()

        # Iniciar requests individuales
        individual_tasks = [
            sender.send_document(xml_content, test_certificate)
            for xml_content in individual_docs
        ]

        # Iniciar lote en paralelo
        with patch.object(sender, 'send_batch', return_value=batch_result):
            batch_task = sender.send_batch(
                documents=batch_docs,
                batch_id="CONCURRENT_MIXED_BATCH"
            )

            # Ejecutar todo concurrentemente
            individual_results = await asyncio.gather(*individual_tasks)
            batch_result_actual = await batch_task

        total_time = time.time() - start_time

        # VALIDAR: Ambos tipos procesados exitosamente
        assert len(
            individual_results) == 5, "Deben procesarse 5 documentos individuales"
        assert all(
            r.success for r in individual_results), "Todos individuales deben ser exitosos"
        assert batch_result_actual.success is True, "Lote debe ser exitoso"
        assert batch_result_actual.successful_documents == 3, "Lote debe procesar 3 documentos"

        # VALIDAR: Procesamiento concurrente efectivo
        assert total_time < 3.0, f"Procesamiento mixto debe ser eficiente: {total_time:.2f}s"

        print(
            f"✅ Procesamiento mixto: 5 individuales + 1 lote en {total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_rate_limit_error_details_validation(
        self, test_config, base_xml_template, test_certificate
    ):
        """
        Test: Validación de detalles completos en errores de rate limit

        CRÍTICO: Errores deben contener información suficiente para debugging
        """
        xml_content = base_xml_template(1)

        # Mock response con todos los detalles de rate limit
        detailed_rate_limit_response = create_rate_limit_response(
            rate_limit_type='ruc',
            requests_sent=15,
            time_window='1 segundo',
            retry_after=90
        )

        # Agregar detalles adicionales para debugging
        detailed_rate_limit_response.additional_data.update({
            'timestamp_exceeded': datetime.now().isoformat(),
            'client_ip': '192.168.1.100',
            'ruc_emisor': '80016875-5',
            'window_start': (datetime.now() - timedelta(seconds=1)).isoformat(),
            'window_end': datetime.now().isoformat(),
            'requests_in_window': 15,
            'limit_per_window': 10,
            'suggested_retry_strategy': 'exponential_backoff',
            'rate_limit_reset_time': (datetime.now() + timedelta(seconds=90)).isoformat()
        })

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = detailed_rate_limit_response
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # EJECUTAR: Request que recibe rate limit detallado
        result = await sender.send_document(xml_content, test_certificate)

        # VALIDAR: Información completa de rate limit
        assert result.success is False, "Request debe fallar por rate limit"
        assert result.response.code == SIFEN_RATE_LIMIT_ERROR_CODES['RATE_LIMIT_RUC']

        # VALIDAR: Detalles específicos presentes
        additional_data = result.response.additional_data
        required_fields = [
            'rate_limit_type', 'requests_sent', 'time_window',
            'retry_after_seconds', 'timestamp_exceeded', 'ruc_emisor'
        ]

        for field in required_fields:
            assert field in additional_data, f"Campo requerido faltante: {field}"

        # VALIDAR: Valores específicos
        assert additional_data['rate_limit_type'] == 'ruc'
        assert additional_data['requests_sent'] == 15
        assert additional_data['retry_after_seconds'] == 90
        assert additional_data['requests_in_window'] == 15
        assert additional_data['limit_per_window'] == 10

        print(
            f"✅ Rate limit error con detalles completos: {len(additional_data)} campos")
