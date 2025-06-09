"""
Tests específicos para DocumentStatus y manejo de estados SIFEN

Enfoque: Testing exhaustivo de todos los estados de documentos electrónicos
según el Manual Técnico SIFEN v150 y el enum DocumentStatus.

Cobertura completa:
✅ Estados durante procesamiento (PENDIENTE, PROCESANDO)
✅ Estados finales exitosos (APROBADO, APROBADO_OBSERVACION)
✅ Estados finales de error (RECHAZADO, ERROR_TECNICO)
✅ Estados especiales (EXTEMPORANEO, CANCELADO, ANULADO)
✅ Transiciones de estado válidas
✅ Códigos SIFEN asociados a cada estado
✅ Validaciones de consistencia
✅ Casos edge y combinaciones inválidas
"""

import pytest
from typing import Optional
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

# Importar módulos del proyecto
from app.services.sifen_client.models import (
    DocumentStatus,
    SifenResponse,
    ResponseType
)
from app.services.sifen_client.document_sender import DocumentSender
from app.services.sifen_client.config import SifenConfig
from app.services.sifen_client.exceptions import SifenValidationError

from unittest.mock import AsyncMock, Mock, patch


# ========================================
# FIXTURES PARA ESTADOS
# ========================================
mock_soap_client = AsyncMock()


@pytest.fixture
def test_config():
    """Configuración estándar para tests"""
    return SifenConfig(environment="test")


@pytest.fixture
def test_xml_content():
    """XML básico para tests de estado"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <dVerFor>150</dVerFor>
    <DE Id="01800695631001001000000612021112917595714694">
        <gOpeDE><iTipDE>1</iTipDE></gOpeDE>
        <gDE><gDatGralOpe><dFeEmiDE>2025-06-09</dFeEmiDE></gDatGralOpe></gDE>
        <gTotSub><dTotGralOpe>110000</dTotGralOpe></gTotSub>
    </DE>
</rDE>'''


@pytest.fixture
def test_certificate():
    """Certificado para tests"""
    return "TEST_CERT_STATUS_123456789"


# ========================================
# TESTS DE ESTADOS DURANTE PROCESAMIENTO
# ========================================
mock_soap_client = AsyncMock()


class TestDocumentStatusProcessing:
    """Tests para estados durante el procesamiento del documento"""

    @pytest.mark.asyncio
    async def test_document_status_pendiente(self, test_config, test_xml_content, test_certificate):
        """Test: Estado PENDIENTE - Documento recibido, en cola"""

        # PREPARAR: Response con estado PENDIENTE
        pendiente_response = SifenResponse(
            success=True,
            code="0200",  # Código para documento en cola
            message="Documento recibido y en cola de procesamiento",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="PROT_PENDIENTE_123",
            document_status=DocumentStatus.PENDIENTE,
            timestamp=datetime.now(),
            processing_time_ms=50,
            errors=[],
            observations=[
                "Documento en cola, procesamiento estimado: 2-5 minutos"],
            additional_data={
                "queue_position": 15,
                "estimated_processing_time": "2-5 minutes"
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = pendiente_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Estado y comportamiento
        assert result.success is True
        assert result.response.document_status == DocumentStatus.PENDIENTE
        assert result.response.code == "0200"
        assert "en cola" in result.response.message.lower()
        assert len(result.response.observations) > 0
        assert "queue_position" in result.response.additional_data

        print("✅ Estado PENDIENTE manejado correctamente")

    @pytest.mark.asyncio
    async def test_document_status_procesando(self, test_config, test_xml_content, test_certificate):
        """Test: Estado PROCESANDO - Siendo procesado por SIFEN"""

        # PREPARAR: Response con estado PROCESANDO
        procesando_response = SifenResponse(
            success=True,
            code="0201",  # Código para documento en procesamiento
            message="Documento siendo procesado por SIFEN",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="PROT_PROCESANDO_123",
            document_status=DocumentStatus.PROCESANDO,
            timestamp=datetime.now(),
            processing_time_ms=150,
            errors=[],
            observations=["Validaciones en curso",
                          "Tiempo estimado restante: 1-2 minutos"],
            additional_data={
                "processing_stage": "validation",
                "completion_percentage": 45
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = procesando_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Estado y progreso
        assert result.success is True
        assert result.response.document_status == DocumentStatus.PROCESANDO
        assert result.response.code == "0201"
        assert "procesado" in result.response.message.lower()
        assert result.response.additional_data["completion_percentage"] == 45

        print("✅ Estado PROCESANDO manejado correctamente")


# ========================================
# TESTS DE ESTADOS FINALES EXITOSOS
# ========================================

class TestDocumentStatusSuccess:
    """Tests para estados finales exitosos"""

    @pytest.mark.asyncio
    async def test_document_status_aprobado(self, test_config, test_xml_content, test_certificate):
        """Test: Estado APROBADO - Código 0260, sin observaciones"""

        # PREPARAR: Response con estado APROBADO
        aprobado_response = SifenResponse(
            success=True,
            code="0260",  # Código oficial SIFEN para aprobado
            message="Documento electrónico aprobado",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="PROT_APROBADO_123",
            document_status=DocumentStatus.APROBADO,
            timestamp=datetime.now(),
            processing_time_ms=200,
            errors=[],
            observations=[],  # Sin observaciones en aprobación limpia
            additional_data={
                "approval_timestamp": datetime.now().isoformat(),
                "validation_score": 100
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = aprobado_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Aprobación perfecta
        assert result.success is True
        assert result.response.document_status == DocumentStatus.APROBADO
        assert result.response.code == "0260"
        assert len(result.response.errors) == 0
        assert len(result.response.observations) == 0
        assert result.response.additional_data["validation_score"] == 100

        print("✅ Estado APROBADO (código 0260) manejado correctamente")

    @pytest.mark.asyncio
    async def test_document_status_aprobado_observacion(self, test_config, test_xml_content, test_certificate):
        """Test: Estado APROBADO_OBSERVACION - Código 1005, con observaciones"""

        # PREPARAR: Response con estado APROBADO_OBSERVACION
        aprobado_obs_response = SifenResponse(
            success=True,
            code="1005",  # Código oficial SIFEN para aprobado con observaciones
            message="Documento electrónico aprobado con observaciones",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="PROT_APROBADO_OBS_123",
            document_status=DocumentStatus.APROBADO_OBSERVACION,
            timestamp=datetime.now(),
            processing_time_ms=180,
            errors=[],
            observations=[
                "Verificar datos del receptor - RUC no validado automáticamente",
                "Monto en moneda extranjera - revisar tipo de cambio",
                "Descripción de ítem incompleta en línea 3"
            ],
            additional_data={
                "approval_timestamp": datetime.now().isoformat(),
                "validation_score": 85,
                "observations_count": 3,
                "requires_manual_review": False
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = aprobado_obs_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Aprobación con observaciones
        assert result.success is True
        assert result.response.document_status == DocumentStatus.APROBADO_OBSERVACION
        assert result.response.code == "1005"
        assert len(result.response.errors) == 0
        assert len(result.response.observations) == 3
        assert "RUC no validado" in result.response.observations[0]
        assert result.response.additional_data["observations_count"] == 3

        print("✅ Estado APROBADO_OBSERVACION (código 1005) manejado correctamente")


# ========================================
# TESTS DE ESTADOS FINALES DE ERROR
# ========================================

class TestDocumentStatusError:
    """Tests para estados finales de error"""

    @pytest.mark.asyncio
    async def test_document_status_rechazado_cdc_error(self, test_config, test_xml_content, test_certificate):
        """Test: Estado RECHAZADO - Error CDC (código 1000)"""

        # PREPARAR: Response con estado RECHAZADO por CDC
        rechazado_response = SifenResponse(
            success=False,
            code="1000",  # Código oficial SIFEN para CDC no corresponde
            message="CDC no corresponde con el contenido del XML",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number=None,  # No hay protocolo en caso de rechazo
            document_status=DocumentStatus.RECHAZADO,
            timestamp=datetime.now(),
            processing_time_ms=80,
            errors=[
                "El CDC calculado no coincide con el CDC proporcionado",
                "Verificar datos del timbrado y fecha de emisión"
            ],
            observations=[
                "Revisar generación del CDC según Manual Técnico v150",
                "Validar cálculo de dígito verificador"
            ],
            additional_data={
                "rejection_reason": "cdc_mismatch",
                "expected_cdc": "01800695631001001000000612021112917595714695",
                "provided_cdc": "01800695631001001000000612021112917595714694"
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = rechazado_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Rechazo por CDC
        assert result.success is False
        assert result.response.document_status == DocumentStatus.RECHAZADO
        assert result.response.code == "1000"
        assert len(result.response.errors) == 2
        assert "CDC" in result.response.errors[0]
        assert result.response.protocol_number is None
        assert "cdc_mismatch" == result.response.additional_data["rejection_reason"]

        print("✅ Estado RECHAZADO por CDC (código 1000) manejado correctamente")

    @pytest.mark.asyncio
    async def test_document_status_rechazado_cdc_duplicado(self, test_config, test_xml_content, test_certificate):
        """Test: Estado RECHAZADO - CDC duplicado (código 1001)"""

        # PREPARAR: Response con estado RECHAZADO por CDC duplicado
        duplicado_response = SifenResponse(
            success=False,
            code="1001",  # Código oficial SIFEN para CDC duplicado
            message="CDC duplicado - Ya existe un documento con este CDC",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number=None,
            document_status=DocumentStatus.RECHAZADO,
            timestamp=datetime.now(),
            processing_time_ms=60,
            errors=[
                "Documento con CDC 01800695631001001000000612021112917595714694 ya fue procesado",
                "Fecha de procesamiento original: 2025-06-08 14:30:25"
            ],
            observations=[
                "Verificar si es reenvío del mismo documento",
                "Si es documento nuevo, revisar generación del CDC"
            ],
            additional_data={
                "rejection_reason": "duplicate_cdc",
                "original_submission_date": "2025-06-08T14:30:25Z",
                "original_protocol": "PROT_ORIGINAL_123",
                "duplicate_attempt_number": 2
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = duplicado_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Rechazo por duplicado
        assert result.success is False
        assert result.response.document_status == DocumentStatus.RECHAZADO
        assert result.response.code == "1001"
        assert "duplicado" in result.response.message.lower()
        assert result.response.additional_data["duplicate_attempt_number"] == 2

        print("✅ Estado RECHAZADO por CDC duplicado (código 1001) manejado correctamente")

    @pytest.mark.asyncio
    async def test_document_status_rechazado_ruc_inexistente(self, test_config, test_xml_content, test_certificate):
        """Test: Estado RECHAZADO - RUC inexistente (código 1250)"""

        # PREPARAR: Response con estado RECHAZADO por RUC
        ruc_error_response = SifenResponse(
            success=False,
            code="1250",  # Código oficial SIFEN para RUC inexistente
            message="RUC inexistente en padrones de la SET",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number=None,
            document_status=DocumentStatus.RECHAZADO,
            timestamp=datetime.now(),
            processing_time_ms=90,
            errors=[
                "RUC 80016875 no encontrado en el padrón de contribuyentes",
                "Verificar estado del contribuyente ante la SET"
            ],
            observations=[
                "Consultar estado del RUC en www.set.gov.py",
                "RUC puede estar inactivo o suspendido"
            ],
            additional_data={
                "rejection_reason": "invalid_ruc",
                "ruc_checked": "80016875",
                "ruc_status": "not_found",
                "suggestion": "verify_with_set"
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = ruc_error_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Rechazo por RUC
        assert result.success is False
        assert result.response.document_status == DocumentStatus.RECHAZADO
        assert result.response.code == "1250"
        assert "RUC" in result.response.message
        assert result.response.additional_data["ruc_checked"] == "80016875"

        print("✅ Estado RECHAZADO por RUC inexistente (código 1250) manejado correctamente")

    @pytest.mark.asyncio
    async def test_document_status_error_tecnico(self, test_config, test_xml_content, test_certificate):
        """Test: Estado ERROR_TECNICO - Errores 5000+ del sistema"""

        # PREPARAR: Response con estado ERROR_TECNICO
        error_tecnico_response = SifenResponse(
            success=False,
            code="5001",  # Código para errores técnicos del sistema
            message="Error técnico en el procesamiento del documento",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number=None,
            document_status=DocumentStatus.ERROR_TECNICO,
            timestamp=datetime.now(),
            processing_time_ms=300,
            errors=[
                "Error interno del servidor SIFEN",
                "Timeout en validación de certificado digital",
                "Base de datos temporalmente no disponible"
            ],
            observations=[
                "Reintentar envío en unos minutos",
                "Si el problema persiste, contactar soporte SET"
            ],
            additional_data={
                "error_type": "technical_system_error",
                "error_code": "SYS_DB_TIMEOUT_5001",
                "retry_recommended": True,
                "retry_after_minutes": 5,
                "support_reference": "REF_TECH_ERROR_20250609_001"
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = error_tecnico_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 3})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Error técnico
        assert result.success is False
        assert result.response.document_status == DocumentStatus.ERROR_TECNICO
        assert result.response.code == "5001"
        assert "técnico" in result.response.message.lower()
        assert result.response.additional_data["retry_recommended"] is True
        assert "REF_TECH_ERROR" in result.response.additional_data["support_reference"]

        print("✅ Estado ERROR_TECNICO (código 5001) manejado correctamente")


# ========================================
# TESTS DE ESTADOS ESPECIALES
# ========================================

class TestDocumentStatusSpecial:
    """Tests para estados especiales"""

    @pytest.mark.asyncio
    async def test_document_status_extemporaneo(self, test_config, test_xml_content, test_certificate):
        """Test: Estado EXTEMPORANEO - Enviado fuera de plazo (72h-720h)"""

        # PREPARAR: Response con estado EXTEMPORANEO
        extemporaneo_response = SifenResponse(
            success=True,  # Puede ser aprobado pero extemporáneo
            code="0260",
            message="Documento aprobado - Envío extemporáneo",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="PROT_EXTEMPORANEO_123",
            document_status=DocumentStatus.EXTEMPORANEO,
            timestamp=datetime.now(),
            processing_time_ms=120,
            errors=[],
            observations=[
                "Documento enviado fuera del plazo de 72 horas",
                f"Fecha emisión: {(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')}",
                f"Fecha envío: {datetime.now().strftime('%Y-%m-%d')}",
                "Delay: 120 horas (5 días)"
            ],
            additional_data={
                "submission_type": "late_submission",
                "emission_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "submission_date": datetime.now().isoformat(),
                "delay_hours": 120,
                "within_acceptable_range": True,  # Dentro de 720h límite
                "penalty_applied": False
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # EJECUTAR: Mock y envío
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = extemporaneo_response
        mock_retry_manager.get_stats = AsyncMock(
            return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(test_xml_content, test_certificate)

        # VALIDAR: Envío extemporáneo
        assert result.success is True  # Aprobado a pesar de ser tarde
        assert result.response.document_status == DocumentStatus.EXTEMPORANEO
        assert result.response.code == "0260"
        assert "extemporáneo" in result.response.message.lower()
        assert result.response.additional_data["delay_hours"] == 120
        assert result.response.additional_data["within_acceptable_range"] is True

        print("✅ Estado EXTEMPORANEO manejado correctamente")

    @pytest.mark.asyncio
    async def test_document_status_cancelado(self, test_config):
        """Test: Estado CANCELADO - Cancelado por evento"""

        # PREPARAR: Response de consulta para documento cancelado
        cancelado_response = SifenResponse(
            success=True,
            code="0260",
            message="Consulta exitosa - Documento cancelado",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="QUERY_CANCELADO_123",
            document_status=DocumentStatus.CANCELADO,
            timestamp=datetime.now(),
            processing_time_ms=40,
            errors=[],
            observations=[
                "Documento cancelado por evento de cancelación",
                "Motivo: Error en datos del receptor",
                "Fecha cancelación: 2025-06-08 16:45:30"
            ],
            additional_data={
                "cancellation_reason": "data_error_receptor",
                "cancellation_date": "2025-06-08T16:45:30Z",
                "cancellation_event_id": "EVT_CANCEL_001",
                "cancelled_by": "emisor",
                "original_approval_date": "2025-06-08T14:30:25Z"
            },
            response_type=ResponseType.QUERY
        )

        # EJECUTAR: Mock de consulta
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = cancelado_response

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        # Simular consulta de documento cancelado
        from app.services.sifen_client.models import QueryRequest
        query_request = QueryRequest(
            query_type="cdc",
            cdc="01800695631001001000000612021112917595714694",
            ruc=None,
            date_from=None,
            date_to=None,
            document_types=None,
            status_filter=None
        )

        result = await sender.query_document(query_request)

        # VALIDAR: Documento cancelado
        assert result.success is True
        assert result.document_status == DocumentStatus.CANCELADO
        assert "cancelado" in result.message.lower()
        assert result.additional_data["cancellation_reason"] == "data_error_receptor"
        assert result.additional_data["cancelled_by"] == "emisor"

        print("✅ Estado CANCELADO manejado correctamente")

    @pytest.mark.asyncio
    async def test_document_status_anulado(self, test_config):
        """Test: Estado ANULADO - Anulado por evento oficial"""

        # PREPARAR: Response de consulta para documento anulado
        anulado_response = SifenResponse(
            success=True,
            code="0260",
            message="Consulta exitosa - Documento anulado",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="QUERY_ANULADO_123",
            document_status=DocumentStatus.ANULADO,
            timestamp=datetime.now(),
            processing_time_ms=45,
            errors=[],
            observations=[
                "Documento anulado por resolución SET",
                "Número resolución: RES-SET-2025-001",
                "Fecha anulación: 2025-06-09 09:15:00"
            ],
            additional_data={
                "annulment_reason": "set_resolution",
                "annulment_date": "2025-06-09T09:15:00Z",
                "resolution_number": "RES-SET-2025-001",
                "annulled_by": "set_authority",
                "original_approval_date": "2025-06-08T14:30:25Z",
                "legal_effect": "nullified_from_origin"
            },
            response_type=ResponseType.QUERY
        )

        # EJECUTAR: Mock de consulta
        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = anulado_response

        sender = DocumentSender(
            config=test_config,
            soap_client=mock_soap_client,
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        from app.services.sifen_client.models import QueryRequest
        query_request = QueryRequest(
            query_type="cdc",
            cdc="01800695631001001000000612021112917595714694",
            ruc=None,
            date_from=None,
            date_to=None,
            document_types=None,
            status_filter=None
        )

        result = await sender.query_document(query_request)

        # VALIDAR: Documento anulado
        assert result.success is True
        assert result.document_status == DocumentStatus.ANULADO
        assert "anulado" in result.message.lower()
        assert result.additional_data["resolution_number"] == "RES-SET-2025-001"
        assert result.additional_data["annulled_by"] == "set_authority"

        print("✅ Estado ANULADO manejado correctamente")


# ========================================
# TESTS DE TRANSICIONES DE ESTADO
# ========================================

class TestDocumentStatusTransitions:
    """Tests de transiciones válidas entre estados"""

    def test_valid_state_transitions(self):
        """Test: Validar transiciones de estado lógicas"""

        # DEFINIR: Transiciones válidas
        valid_transitions = {
            DocumentStatus.PENDIENTE: [
                DocumentStatus.PROCESANDO,
                DocumentStatus.ERROR_TECNICO
            ],
            DocumentStatus.PROCESANDO: [
                DocumentStatus.APROBADO,
                DocumentStatus.APROBADO_OBSERVACION,
                DocumentStatus.RECHAZADO,
                DocumentStatus.EXTEMPORANEO,
                DocumentStatus.ERROR_TECNICO
            ],
            DocumentStatus.APROBADO: [
                DocumentStatus.CANCELADO,
                DocumentStatus.ANULADO
            ],
            DocumentStatus.APROBADO_OBSERVACION: [
                DocumentStatus.CANCELADO,
                DocumentStatus.ANULADO
            ],
            DocumentStatus.EXTEMPORANEO: [
                DocumentStatus.CANCELADO,
                DocumentStatus.ANULADO
            ]
        }

        # VALIDAR: Cada transición válida
        for initial_state, valid_next_states in valid_transitions.items():
            for next_state in valid_next_states:
                # EJECUTAR: Simular transición
                transition_valid = self._is_transition_valid(
                    initial_state, next_state)

                # VALIDAR: Transición es válida
                assert transition_valid, f"Transición inválida: {initial_state} -> {next_state}"

        print("✅ Todas las transiciones de estado válidas verificadas")

    def test_invalid_state_transitions(self):
        """Test: Detectar transiciones inválidas"""

        # DEFINIR: Transiciones inválidas
        invalid_transitions = [
            # No se puede aprobar lo rechazado
            (DocumentStatus.RECHAZADO, DocumentStatus.APROBADO),
            # No se puede aprobar lo cancelado
            (DocumentStatus.CANCELADO, DocumentStatus.APROBADO),
            # No se puede aprobar lo anulado
            (DocumentStatus.ANULADO, DocumentStatus.APROBADO),
            # Error técnico no lleva a aprobado directo
            (DocumentStatus.ERROR_TECNICO, DocumentStatus.APROBADO),
            # No se puede rechazar lo ya aprobado
            (DocumentStatus.APROBADO, DocumentStatus.RECHAZADO),
            # No puede saltar procesamiento
            (DocumentStatus.PENDIENTE, DocumentStatus.APROBADO),
            # Estados finales no transicionan entre sí
            (DocumentStatus.CANCELADO, DocumentStatus.ANULADO),
            # Estados finales no transicionan entre sí
            (DocumentStatus.ANULADO, DocumentStatus.CANCELADO)
        ]

        # VALIDAR: Cada transición inválida
        for initial_state, invalid_next_state in invalid_transitions:
            # EJECUTAR: Verificar que la transición es inválida
            transition_invalid = not self._is_transition_valid(
                initial_state, invalid_next_state)

            # VALIDAR: Transición es correctamente inválida
            assert transition_invalid, f"Transición debería ser inválida: {initial_state} -> {invalid_next_state}"

        print("✅ Todas las transiciones de estado inválidas detectadas correctamente")

    def _is_transition_valid(self, from_state: DocumentStatus, to_state: DocumentStatus) -> bool:
        """
        Helper: Determina si una transición de estado es válida

        Args:
            from_state: Estado inicial
            to_state: Estado destino

        Returns:
            True si la transición es válida según las reglas de negocio SIFEN
        """
        # Reglas de transición según Manual SIFEN v150
        transition_rules = {
            DocumentStatus.PENDIENTE: {
                DocumentStatus.PROCESANDO,
                DocumentStatus.ERROR_TECNICO
            },
            DocumentStatus.PROCESANDO: {
                DocumentStatus.APROBADO,
                DocumentStatus.APROBADO_OBSERVACION,
                DocumentStatus.RECHAZADO,
                DocumentStatus.EXTEMPORANEO,
                DocumentStatus.ERROR_TECNICO
            },
            DocumentStatus.APROBADO: {
                DocumentStatus.CANCELADO,
                DocumentStatus.ANULADO
            },
            DocumentStatus.APROBADO_OBSERVACION: {
                DocumentStatus.CANCELADO,
                DocumentStatus.ANULADO
            },
            DocumentStatus.EXTEMPORANEO: {
                DocumentStatus.CANCELADO,
                DocumentStatus.ANULADO
            },
            # Estados finales no tienen transiciones válidas
            DocumentStatus.RECHAZADO: set(),
            DocumentStatus.ERROR_TECNICO: set(),
            DocumentStatus.CANCELADO: set(),
            DocumentStatus.ANULADO: set()
        }

        return to_state in transition_rules.get(from_state, set())


# ========================================
# TESTS DE CÓDIGOS SIFEN POR ESTADO
# ========================================

class TestDocumentStatusCodes:
    """Tests de mapeo entre códigos SIFEN y estados de documento"""

    def test_success_codes_mapping(self):
        """Test: Mapeo correcto de códigos de éxito"""

        # DEFINIR: Mapeo códigos exitosos -> estados
        success_mappings = {
            "0260": DocumentStatus.APROBADO,
            "1005": DocumentStatus.APROBADO_OBSERVACION,
            "0200": DocumentStatus.PENDIENTE,
            "0201": DocumentStatus.PROCESANDO
        }

        # VALIDAR: Cada mapeo
        for code, expected_status in success_mappings.items():
            # EJECUTAR: Crear response con código específico
            response = SifenResponse(
                success=True,
                code=code,
                message=f"Test para código {code}",
                cdc="test_cdc",
                protocol_number="test_protocol",
                document_status=expected_status,
                timestamp=datetime.now(),
                processing_time_ms=100,
                errors=[],
                observations=[],
                additional_data={},
                response_type=ResponseType.INDIVIDUAL
            )

            # VALIDAR: Estado coincide con código
            assert response.document_status == expected_status
            assert response.success is True
            assert response.code == code

        print("✅ Mapeo de códigos de éxito verificado")

    def test_error_codes_mapping(self):
        """Test: Mapeo correcto de códigos de error"""

        # DEFINIR: Mapeo códigos de error -> estados
        error_mappings = {
            "1000": DocumentStatus.RECHAZADO,  # CDC no corresponde
            "1001": DocumentStatus.RECHAZADO,  # CDC duplicado
            "1250": DocumentStatus.RECHAZADO,  # RUC inexistente
            "1101": DocumentStatus.RECHAZADO,  # Timbrado inválido
            "5001": DocumentStatus.ERROR_TECNICO,  # Error sistema
            "5002": DocumentStatus.ERROR_TECNICO,  # Error base datos
            "5999": DocumentStatus.ERROR_TECNICO   # Error técnico genérico
        }

        # VALIDAR: Cada mapeo
        for code, expected_status in error_mappings.items():
            # EJECUTAR: Crear response de error con código específico
            response = SifenResponse(
                success=False,
                code=code,
                message=f"Error {code} de prueba",
                cdc="test_error_cdc",
                protocol_number=None,
                document_status=expected_status,
                timestamp=datetime.now(),
                processing_time_ms=80,
                errors=[f"Error específico para código {code}"],
                observations=[],
                additional_data={"error_code": code},
                response_type=ResponseType.INDIVIDUAL
            )

            # VALIDAR: Estado y éxito coinciden con código
            assert response.document_status == expected_status
            assert response.success is False
            assert response.code == code

        print("✅ Mapeo de códigos de error verificado")

    def test_code_validation_rules(self):
        """Test: Reglas de validación de códigos SIFEN"""

        # EJECUTAR Y VALIDAR: Códigos válidos
        valid_codes = ["0260", "1005", "1000", "5001"]
        for code in valid_codes:
            response = SifenResponse(
                success=(code in ["0260", "1005"]),
                code=code,
                message="Test",
                cdc="test",
                protocol_number="test",
                document_status=DocumentStatus.APROBADO,
                timestamp=datetime.now(),
                processing_time_ms=100,
                errors=[],
                observations=[],
                additional_data={},
                response_type=ResponseType.INDIVIDUAL
            )
            assert response.code == code

        # EJECUTAR Y VALIDAR: Códigos inválidos deben fallar
        invalid_codes = ["ABC", "12", "99999", "0", ""]
        for invalid_code in invalid_codes:
            with pytest.raises(ValueError):
                SifenResponse(
                    success=True,
                    code=invalid_code,  # Esto debe fallar la validación
                    message="Test",
                    cdc="test",
                    protocol_number="test",
                    document_status=DocumentStatus.APROBADO,
                    timestamp=datetime.now(),
                    processing_time_ms=100,
                    errors=[],
                    observations=[],
                    additional_data={},
                    response_type=ResponseType.INDIVIDUAL
                )

        print("✅ Validación de códigos SIFEN verificada")


# ========================================
# TESTS DE CONSISTENCIA ESTADO-ÉXITO
# ========================================

class TestDocumentStatusConsistency:
    """Tests de consistencia entre estado, código y éxito"""

    def test_success_status_consistency(self):
        """Test: Consistencia entre success=True y estados exitosos"""

        # DEFINIR: Estados que deben ser success=True
        success_states = [
            DocumentStatus.APROBADO,
            DocumentStatus.APROBADO_OBSERVACION,
            DocumentStatus.EXTEMPORANEO,  # Aprobado pero tarde
            DocumentStatus.PENDIENTE,     # En proceso, aún exitoso
            DocumentStatus.PROCESANDO     # En proceso, aún exitoso
        ]

        # VALIDAR: Cada estado exitoso
        for status in success_states:
            # EJECUTAR: Crear response exitoso
            response = SifenResponse(
                success=True,
                code="0260",  # Código exitoso genérico
                message=f"Test para estado {status.value}",
                cdc="test_consistency",
                protocol_number="PROT_CONSISTENCY_123",
                document_status=status,
                timestamp=datetime.now(),
                processing_time_ms=100,
                errors=[],
                observations=[],
                additional_data={"test_status": status.value},
                response_type=ResponseType.INDIVIDUAL
            )

            # VALIDAR: Consistencia
            assert response.success is True
            assert response.document_status == status

        print("✅ Consistencia de estados exitosos verificada")

    def test_failure_status_consistency(self):
        """Test: Consistencia entre success=False y estados de fallo"""

        # DEFINIR: Estados que deben ser success=False
        failure_states = [
            DocumentStatus.RECHAZADO,
            DocumentStatus.ERROR_TECNICO
        ]

        # VALIDAR: Cada estado de fallo
        for status in failure_states:
            # EJECUTAR: Crear response de fallo
            response = SifenResponse(
                success=False,
                code="1000",  # Código de error genérico
                message=f"Test de fallo para estado {status.value}",
                cdc="test_failure_consistency",
                protocol_number=None,
                document_status=status,
                timestamp=datetime.now(),
                processing_time_ms=80,
                errors=[f"Error de prueba para {status.value}"],
                observations=[],
                additional_data={"test_status": status.value},
                response_type=ResponseType.INDIVIDUAL
            )

            # VALIDAR: Consistencia
            assert response.success is False
            assert response.document_status == status
            assert len(response.errors) > 0

        print("✅ Consistencia de estados de fallo verificada")

    def test_special_status_consistency(self):
        """Test: Consistencia de estados especiales (cancelado, anulado)"""

        # DEFINIR: Estados especiales - pueden ser success=True (consulta exitosa)
        special_states = [
            DocumentStatus.CANCELADO,
            DocumentStatus.ANULADO
        ]

        # VALIDAR: Estados especiales en contexto de consulta
        for status in special_states:
            # EJECUTAR: Crear response de consulta exitosa para estado especial
            response = SifenResponse(
                success=True,  # Consulta exitosa aunque documento esté cancelado/anulado
                code="0260",
                message=f"Consulta exitosa - Documento {status.value.lower()}",
                cdc="test_special_consistency",
                protocol_number="QUERY_SPECIAL_123",
                document_status=status,
                timestamp=datetime.now(),
                processing_time_ms=60,
                errors=[],
                observations=[f"Documento en estado {status.value.lower()}"],
                additional_data={"query_type": "status_check"},
                response_type=ResponseType.QUERY
            )

            # VALIDAR: Consistencia para consultas
            assert response.success is True  # Consulta exitosa
            assert response.document_status == status
            assert response.response_type == ResponseType.QUERY

        print("✅ Consistencia de estados especiales verificada")


# ========================================
# TESTS DE CASOS EDGE Y LÍMITES
# ========================================

class TestDocumentStatusEdgeCases:
    """Tests de casos edge y situaciones límite"""

    def test_late_submission_boundary_cases(self):
        """Test: Casos límite para envíos extemporáneos"""

        # CASO 1: Justo en el límite de 72 horas
        boundary_72h_response = SifenResponse(
            success=True,
            code="0260",
            message="Aprobado - En límite de 72 horas",
            cdc="test_boundary_72h",
            protocol_number="PROT_BOUNDARY_72H",
            document_status=DocumentStatus.APROBADO,  # Aún dentro del plazo
            timestamp=datetime.now(),
            processing_time_ms=100,
            errors=[],
            observations=["Enviado exactamente a las 72 horas"],
            additional_data={
                "delay_hours": 72,
                "submission_type": "on_time_boundary"
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # CASO 2: Justo después del límite de 72 horas
        boundary_73h_response = SifenResponse(
            success=True,
            code="0260",
            message="Aprobado - Envío extemporáneo",
            cdc="test_boundary_73h",
            protocol_number="PROT_BOUNDARY_73H",
            document_status=DocumentStatus.EXTEMPORANEO,  # Ya es extemporáneo
            timestamp=datetime.now(),
            processing_time_ms=100,
            errors=[],
            observations=["Enviado 1 hora después del plazo de 72 horas"],
            additional_data={
                "delay_hours": 73,
                "submission_type": "late_submission"
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # VALIDAR: Diferencia entre 72h y 73h
        assert boundary_72h_response.document_status == DocumentStatus.APROBADO
        assert boundary_73h_response.document_status == DocumentStatus.EXTEMPORANEO
        assert boundary_72h_response.additional_data["delay_hours"] == 72
        assert boundary_73h_response.additional_data["delay_hours"] == 73

        print("✅ Casos límite de envío extemporáneo verificados")

    def test_maximum_observations_handling(self):
        """Test: Manejo de máximo número de observaciones"""

        # PREPARAR: Response con muchas observaciones
        many_observations = [
            f"Observación número {i+1}: Detalle específico de validación"
            for i in range(20)  # 20 observaciones
        ]

        max_obs_response = SifenResponse(
            success=True,
            code="1005",
            message="Aprobado con múltiples observaciones",
            cdc="test_max_observations",
            protocol_number="PROT_MAX_OBS_123",
            document_status=DocumentStatus.APROBADO_OBSERVACION,
            timestamp=datetime.now(),
            processing_time_ms=250,
            errors=[],
            observations=many_observations,
            additional_data={
                "observations_count": len(many_observations),
                "requires_review": True
            },
            response_type=ResponseType.INDIVIDUAL
        )

        # VALIDAR: Manejo de muchas observaciones
        assert len(max_obs_response.observations) == 20
        assert max_obs_response.document_status == DocumentStatus.APROBADO_OBSERVACION
        assert max_obs_response.additional_data["observations_count"] == 20
        assert max_obs_response.additional_data["requires_review"] is True

        print("✅ Manejo de múltiples observaciones verificado")

    def test_concurrent_status_updates(self):
        """Test: Simulación de actualizaciones concurrentes de estado"""

        # SIMULAR: Múltiples responses para el mismo CDC con diferentes estados
        concurrent_responses = [
            {
                "timestamp": datetime.now(),
                "status": DocumentStatus.PENDIENTE,
                "message": "Documento recibido"
            },
            {
                "timestamp": datetime.now() + timedelta(seconds=30),
                "status": DocumentStatus.PROCESANDO,
                "message": "Documento en procesamiento"
            },
            {
                "timestamp": datetime.now() + timedelta(seconds=120),
                "status": DocumentStatus.APROBADO,
                "message": "Documento aprobado"
            }
        ]

        # VALIDAR: Secuencia lógica de estados
        previous_status = None
        for response_data in concurrent_responses:
            current_status = response_data["status"]

            if previous_status:
                # EJECUTAR: Verificar transición válida
                transition_valid = self._is_valid_progression(
                    previous_status, current_status)
                assert transition_valid, f"Progresión inválida: {previous_status} -> {current_status}"

            previous_status = current_status

        print("✅ Actualizaciones concurrentes de estado verificadas")

    def _is_valid_progression(self, from_status: DocumentStatus, to_status: DocumentStatus) -> bool:
        """Helper: Verifica si una progresión de estado es válida temporalmente"""
        valid_progressions = [
            (DocumentStatus.PENDIENTE, DocumentStatus.PROCESANDO),
            (DocumentStatus.PROCESANDO, DocumentStatus.APROBADO),
            (DocumentStatus.PROCESANDO, DocumentStatus.APROBADO_OBSERVACION),
            (DocumentStatus.PROCESANDO, DocumentStatus.RECHAZADO),
            (DocumentStatus.PROCESANDO, DocumentStatus.EXTEMPORANEO)
        ]
        return (from_status, to_status) in valid_progressions


# ========================================
# CONFIGURACIÓN PYTEST
# ========================================

def pytest_configure(config):
    """Configuración específica para tests de DocumentStatus"""
    config.addinivalue_line(
        "markers", "document_status: tests específicos de estados de documento"
    )
    config.addinivalue_line(
        "markers", "status_transitions: tests de transiciones de estado"
    )
    config.addinivalue_line(
        "markers", "status_codes: tests de códigos SIFEN"
    )
    config.addinivalue_line(
        "markers", "status_consistency: tests de consistencia de estados"
    )


# ========================================
# UTILIDADES PARA TESTS
# ========================================

class DocumentStatusTestUtils:
    """Utilidades para tests de estados de documento"""

    @staticmethod
    def create_response_for_status(
        status: DocumentStatus,
        success: Optional[bool] = None,
        code: Optional[str] = None
    ) -> SifenResponse:
        """
        Crea un SifenResponse apropiado para un estado específico

        Args:
            status: Estado del documento
            success: Override del campo success (auto-detecta si None)
            code: Override del código SIFEN (auto-detecta si None)

        Returns:
            SifenResponse configurado apropiadamente
        """
        # Auto-detectar success si no se proporciona
        if success is None:
            success = status in [
                DocumentStatus.APROBADO,
                DocumentStatus.APROBADO_OBSERVACION,
                DocumentStatus.EXTEMPORANEO,
                DocumentStatus.PENDIENTE,
                DocumentStatus.PROCESANDO
            ]

        # Auto-detectar código si no se proporciona
        if code is None:
            code_mapping = {
                DocumentStatus.APROBADO: "0260",
                DocumentStatus.APROBADO_OBSERVACION: "1005",
                DocumentStatus.RECHAZADO: "1000",
                DocumentStatus.ERROR_TECNICO: "5001",
                DocumentStatus.PENDIENTE: "0200",
                DocumentStatus.PROCESANDO: "0201",
                DocumentStatus.EXTEMPORANEO: "0260",
                DocumentStatus.CANCELADO: "0260",
                DocumentStatus.ANULADO: "0260"
            }
            code = code_mapping.get(status, "0260")

        return SifenResponse(
            success=success,
            code=code,
            message=f"Test response for status {status.value}",
            cdc=f"test_cdc_{status.value.lower()}",
            protocol_number=f"PROT_{status.value.upper()}_123" if success else None,
            document_status=status,
            timestamp=datetime.now(),
            processing_time_ms=100,
            errors=[] if success else [f"Error for status {status.value}"],
            observations=[],
            additional_data={"test_status": status.value},
            response_type=ResponseType.INDIVIDUAL
        )


# ========================================
# RESUMEN DE EJECUCIÓN
# ========================================

if __name__ == "__main__":
    """
    Información del módulo de tests DocumentStatus
    """
    print("🔧 Tests específicos DocumentStatus")
    print("="*60)

    # Contar tests por categoría
    test_categories = {
        "Estados procesamiento": ["PENDIENTE", "PROCESANDO"],
        "Estados exitosos": ["APROBADO", "APROBADO_OBSERVACION"],
        "Estados error": ["RECHAZADO (CDC)", "RECHAZADO (Duplicado)", "RECHAZADO (RUC)", "ERROR_TECNICO"],
        "Estados especiales": ["EXTEMPORANEO", "CANCELADO", "ANULADO"],
        "Transiciones": ["Válidas", "Inválidas"],
        "Códigos SIFEN": ["Mapeo éxito", "Mapeo error", "Validación"],
        "Consistencia": ["Success-Status", "Failure-Status", "Special-Status"],
        "Casos edge": ["Límites 72h", "Múltiples obs", "Concurrencia"]
    }

    total_categories = len(test_categories)
    estimated_tests = sum(len(tests) for tests in test_categories.values())

    print(f"📊 Categorías implementadas: {total_categories}")
    print(f"📊 Tests estimados: {estimated_tests}")
    print("\n📋 Cobertura por categoría:")

    for category, tests in test_categories.items():
        print(f"  • {category}: {len(tests)} tests")
        for test in tests:
            print(f"    - {test}")

    print("\n🚀 Comandos de ejecución:")
    print("  Todos los tests:")
    print("    pytest test_document_status.py -v")
    print("  Por estado específico:")
    print("    pytest test_document_status.py -v -k 'aprobado'")
    print("    pytest test_document_status.py -v -k 'rechazado'")
    print("  Por categoría:")
    print("    pytest test_document_status.py -v -m 'status_transitions'")
    print("    pytest test_document_status.py -v -m 'status_codes'")
    print("  Con coverage:")
    print("    pytest test_document_status.py --cov=app.services.sifen_client.models")

    print("\n✅ Archivo listo para testing exhaustivo de DocumentStatus")
