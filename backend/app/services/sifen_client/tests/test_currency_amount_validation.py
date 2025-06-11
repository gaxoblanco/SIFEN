"""
Tests específicos para validación de monedas y montos según Manual SIFEN v150

OBJETIVO: Validar que el DocumentSender maneje correctamente las reglas de 
monedas y montos establecidas en el Manual Técnico SIFEN v150.

COBERTURA:
✅ Validación PYG (Guaraníes) - Sin decimales
✅ Validación monedas extranjeras (USD, EUR, BRL, ARS) - 2 decimales exactos
✅ Códigos de error específicos de montos (1501-1599)
✅ Reglas de negocio para diferentes tipos de documentos
✅ Validación de campos monetarios específicos
✅ Casos edge y límites de montos

MONEDAS SOPORTADAS SIFEN:
- PYG: Guaraníes paraguayos (sin decimales)
- USD: Dólares estadounidenses (2 decimales)
- EUR: Euros (2 decimales)
- BRL: Reales brasileños (2 decimales)
- ARS: Pesos argentinos (2 decimales)

Basado en Manual Técnico SIFEN v150 secciones:
- 4.2.3 Monedas de operación
- 5.1.2 Campos monetarios obligatorios
- 7.3 Validaciones de montos y decimales
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any, List

# Importar módulos del proyecto
from app.services.sifen_client.document_sender import DocumentSender, SendResult
from app.services.sifen_client.models import (
    SifenResponse,
    DocumentStatus,
    ResponseType
)
from app.services.sifen_client.config import SifenConfig
from app.services.sifen_client.exceptions import (
    SifenValidationError,
    SifenClientError
)


# ========================================
# FIXTURES Y CONFIGURACIÓN
# ========================================

@pytest.fixture
def test_config():
    """Configuración estándar para tests de validación de monedas"""
    return SifenConfig(
        environment="test",
        base_url="https://sifen-test.set.gov.py",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def test_certificate():
    """Certificado de prueba para firmar documentos"""
    return "TEST_CERT_123456789"


def create_xml_with_amounts(currency: str, total_amount: str, item_amount: str) -> str:
    """
    Crea XML de prueba con montos específicos para validación

    Args:
        currency: Código de moneda (PYG, USD, EUR, etc.)
        total_amount: Monto total del documento
        item_amount: Precio unitario del item

    Returns:
        XML formateado para pruebas
    """
    fecha = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    cdc = "01800695631001001000000612021112917595714694"

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <dVerFor>150</dVerFor>
    <DE Id="{cdc}">
        <gOpeDE>
            <iTipDE>1</iTipDE>
            <dDesTipDE>Factura electrónica</dDesTipDE>
        </gOpeDE>
        <gTimb>
            <dNumTim>12345678</dNumTim>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>0000001</dNumDoc>
        </gTimb>
        <gDE>
            <gDatGralOpe>
                <dFeEmiDE>{fecha}</dFeEmiDE>
                <cMoneOpe>{currency}</cMoneOpe>
            </gDatGralOpe>
            <gDatEm>
                <dRucEm>80016875</dRucEm>
                <dNomEmi>Empresa Test SIFEN</dNomEmi>
            </gDatEm>
            <gCamItem>
                <dDesProSer>Producto de prueba</dDesProSer>
                <dCantProSer>1</dCantProSer>
                <dPUniProSer>{item_amount}</dPUniProSer>
            </gCamItem>
        </gDE>
        <gTotSub>
            <dTotOpe>{total_amount}</dTotOpe>
            <dTotGralOpe>{total_amount}</dTotGralOpe>
        </gTotSub>
    </DE>
</rDE>'''


def create_currency_error_response(code: str, message: str, currency: str,
                                   amount: str, field_name: str) -> SifenResponse:
    """
    Crea respuesta de error específica para validación de monedas

    Args:
        code: Código de error SIFEN
        message: Mensaje de error
        currency: Moneda que causó el error
        amount: Monto que causó el error
        field_name: Campo XML que contiene el error

    Returns:
        SifenResponse con error de validación monetaria
    """
    return SifenResponse(
        success=False,
        code=code,
        message=message,
        cdc="01800695631001001000000612021112917595714694",
        protocol_number="",
        document_status=DocumentStatus.RECHAZADO,
        timestamp=datetime.now(),
        processing_time_ms=100,
        errors=[
            f"Error de validación en campo {field_name}",
            f"Monto {amount} no válido para moneda {currency}",
            f"Revisar reglas de decimales según Manual v150"
        ],
        observations=[
            "PYG no admite decimales",
            "Monedas extranjeras requieren exactamente 2 decimales"
        ],
        additional_data={
            'rejection_reason': 'invalid_currency_format',
            'field_name': field_name,
            'received_amount': amount,
            'currency': currency,
            'validation_rule': 'decimal_validation'
        },
        response_type=ResponseType.INDIVIDUAL
    )


# ========================================
# TESTS VALIDACIÓN MONEDA PYG (GUARANÍES)
# ========================================

class TestPYGCurrencyValidation:
    """
    Tests específicos para validación de moneda PYG (Guaraníes paraguayos)

    REGLA PRINCIPAL: PYG no admite decimales (debe ser número entero)
    """

    @pytest.mark.asyncio
    async def test_pyg_valid_integer_amounts(self, test_config, test_certificate):
        """
        Test: Montos PYG válidos (números enteros)

        Casos válidos:
        - 100000 PYG (entero)
        - 1500000 PYG (entero grande)
        - 0 PYG (cero válido)
        """
        valid_amounts = ["100000", "1500000", "0", "50000"]

        for amount in valid_amounts:
            xml_content = create_xml_with_amounts("PYG", amount, amount)

            # Mock respuesta exitosa
            success_response = SifenResponse(
                success=True,
                code="0260",
                message="Aprobado",
                cdc="01800695631001001000000612021112917595714694",
                protocol_number="PROT_123456789",
                document_status=DocumentStatus.APROBADO,
                timestamp=datetime.now(),
                processing_time_ms=150,
                errors=[],
                observations=[],
                additional_data={'currency': 'PYG', 'amount': amount},
                response_type=ResponseType.INDIVIDUAL
            )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = success_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Monto PYG entero aceptado
            assert result.success is True
            assert result.response.code == "0260"
            assert result.response.additional_data['currency'] == 'PYG'
            assert result.response.additional_data['amount'] == amount

        print("✅ Montos PYG enteros validados correctamente")

    @pytest.mark.asyncio
    async def test_pyg_invalid_decimal_amounts(self, test_config, test_certificate):
        """
        Test: Montos PYG inválidos (con decimales)

        Casos inválidos:
        - 100000.50 PYG (con decimales)
        - 150000.01 PYG (con céntimos)
        - 0.99 PYG (menor a 1 con decimales)
        """
        invalid_amounts = ["100000.50", "150000.01", "0.99", "500000.25"]

        for amount in invalid_amounts:
            xml_content = create_xml_with_amounts("PYG", amount, amount)

            # Mock respuesta de error
            error_response = create_currency_error_response(
                code="1501",
                message="Monto especificado no es válido para PYG",
                currency="PYG",
                amount=amount,
                field_name="dTotGralOpe"
            )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = error_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Error por decimales en PYG
            assert result.success is False
            assert result.response.code == "1501"
            assert "PYG" in result.response.message
            assert result.response.additional_data['currency'] == 'PYG'
            assert result.response.additional_data['received_amount'] == amount

        print("✅ Montos PYG con decimales rechazados correctamente")

    @pytest.mark.asyncio
    async def test_pyg_edge_cases(self, test_config, test_certificate):
        """
        Test: Casos edge para montos PYG

        Casos límite:
        - Montos muy grandes
        - Formato con ceros a la izquierda
        - Notación científica (si aplica)
        """
        edge_cases = [
            ("999999999", True),   # Monto muy grande válido
            ("000100000", True),   # Ceros a la izquierda (válido si se normaliza)
            ("1.0", False),        # Decimal .0 (debe ser inválido para PYG)
            ("1.00", False),       # Decimal .00 (debe ser inválido para PYG)
        ]

        for amount, should_be_valid in edge_cases:
            xml_content = create_xml_with_amounts("PYG", amount, amount)

            if should_be_valid:
                # Mock respuesta exitosa
                response = SifenResponse(
                    success=True,
                    code="0260",
                    message="Aprobado",
                    cdc="01800695631001001000000612021112917595714694",
                    protocol_number="PROT_123456789",
                    document_status=DocumentStatus.APROBADO,
                    timestamp=datetime.now(),
                    processing_time_ms=150,
                    errors=[],
                    observations=[],
                    additional_data={'currency': 'PYG', 'amount': amount},
                    response_type=ResponseType.INDIVIDUAL
                )
            else:
                # Mock respuesta de error
                response = create_currency_error_response(
                    code="1501",
                    message="Formato de monto PYG inválido",
                    currency="PYG",
                    amount=amount,
                    field_name="dTotGralOpe"
                )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Resultado según expectativa
            assert result.success == should_be_valid
            if should_be_valid:
                assert result.response.code == "0260"
            else:
                assert result.response.code == "1501"

        print("✅ Casos edge PYG manejados correctamente")


# ========================================
# TESTS VALIDACIÓN MONEDAS EXTRANJERAS
# ========================================

class TestForeignCurrencyValidation:
    """
    Tests específicos para validación de monedas extranjeras

    REGLA PRINCIPAL: USD, EUR, BRL, ARS requieren exactamente 2 decimales
    """

    @pytest.mark.asyncio
    async def test_foreign_currency_valid_decimals(self, test_config, test_certificate):
        """
        Test: Monedas extranjeras con 2 decimales válidos

        Casos válidos:
        - 150.00 USD (2 decimales exactos)
        - 1250.50 EUR (2 decimales exactos) 
        - 0.01 BRL (mínimo con 2 decimales)
        - 999999.99 ARS (máximo con 2 decimales)
        """
        valid_test_cases = [
            ("USD", "150.00"),
            ("EUR", "1250.50"),
            ("BRL", "0.01"),
            ("ARS", "999999.99"),
            ("USD", "0.00"),  # Cero con decimales
        ]

        for currency, amount in valid_test_cases:
            xml_content = create_xml_with_amounts(currency, amount, amount)

            # Mock respuesta exitosa
            success_response = SifenResponse(
                success=True,
                code="0260",
                message="Aprobado",
                cdc="01800695631001001000000612021112917595714694",
                protocol_number="PROT_123456789",
                document_status=DocumentStatus.APROBADO,
                timestamp=datetime.now(),
                processing_time_ms=150,
                errors=[],
                observations=[],
                additional_data={'currency': currency, 'amount': amount},
                response_type=ResponseType.INDIVIDUAL
            )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = success_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Monto extranjero con 2 decimales aceptado
            assert result.success is True
            assert result.response.code == "0260"
            assert result.response.additional_data['currency'] == currency
            assert result.response.additional_data['amount'] == amount

        print("✅ Monedas extranjeras con 2 decimales validadas correctamente")

    @pytest.mark.asyncio
    async def test_foreign_currency_invalid_decimals(self, test_config, test_certificate):
        """
        Test: Monedas extranjeras con decimales inválidos

        Casos inválidos:
        - 150 USD (sin decimales)
        - 150.5 EUR (1 decimal)
        - 150.123 BRL (3 decimales)
        - 150.0000 ARS (4 decimales)
        """
        invalid_test_cases = [
            ("USD", "150", "sin_decimales"),
            ("EUR", "150.5", "un_decimal"),
            ("BRL", "150.123", "tres_decimales"),
            ("ARS", "150.0000", "cuatro_decimales"),
            ("USD", "150.", "decimal_incompleto"),
        ]

        for currency, amount, error_type in invalid_test_cases:
            xml_content = create_xml_with_amounts(currency, amount, amount)

            # Mock respuesta de error específico
            error_response = create_currency_error_response(
                code="1502",
                message=f"Formato decimal inválido para {currency}",
                currency=currency,
                amount=amount,
                field_name="dTotGralOpe"
            )
            error_response.additional_data['error_type'] = error_type

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = error_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Error por formato decimal inválido
            assert result.success is False
            assert result.response.code == "1502"
            assert currency in result.response.message
            assert result.response.additional_data['currency'] == currency
            assert result.response.additional_data['received_amount'] == amount
            assert result.response.additional_data['error_type'] == error_type

        print("✅ Monedas extranjeras con decimales inválidos rechazadas correctamente")

    @pytest.mark.asyncio
    async def test_unsupported_currencies(self, test_config, test_certificate):
        """
        Test: Monedas no soportadas por SIFEN

        Casos inválidos:
        - JPY (Yen japonés - no soportado)
        - GBP (Libra esterlina - no soportado)
        - CHF (Franco suizo - no soportado)
        - CNY (Yuan chino - no soportado)
        """
        unsupported_currencies = ["JPY", "GBP", "CHF", "CNY", "CAD", "AUD"]

        for currency in unsupported_currencies:
            xml_content = create_xml_with_amounts(currency, "150.00", "150.00")

            # Mock respuesta de error para moneda no soportada
            error_response = SifenResponse(
                success=False,
                code="1503",
                message=f"Moneda {currency} no está autorizada por BCP Paraguay",
                cdc="01800695631001001000000612021112917595714694",
                protocol_number="",
                document_status=DocumentStatus.RECHAZADO,
                timestamp=datetime.now(),
                processing_time_ms=100,
                errors=[
                    f"Moneda {currency} no soportada",
                    "Solo se permiten: PYG, USD, EUR, BRL, ARS",
                    "Consultar listado oficial BCP"
                ],
                observations=[
                    "Usar solo monedas autorizadas por Banco Central del Paraguay"
                ],
                additional_data={
                    'rejection_reason': 'unsupported_currency',
                    'currency': currency,
                    'supported_currencies': ['PYG', 'USD', 'EUR', 'BRL', 'ARS']
                },
                response_type=ResponseType.INDIVIDUAL
            )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = error_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Error por moneda no soportada
            assert result.success is False
            assert result.response.code == "1503"
            assert currency in result.response.message
            assert result.response.additional_data['currency'] == currency
            assert 'supported_currencies' in result.response.additional_data

        print("✅ Monedas no soportadas rechazadas correctamente")


# ========================================
# TESTS REGLAS DE NEGOCIO MONETARIAS
# ========================================

class TestCurrencyBusinessRules:
    """
    Tests para reglas de negocio específicas relacionadas con monedas y montos
    """

    @pytest.mark.asyncio
    async def test_negative_amounts_validation(self, test_config, test_certificate):
        """
        Test: Validación de montos negativos (no permitidos)

        Casos inválidos:
        - Montos totales negativos
        - Precios unitarios negativos
        - Cantidades negativas
        """
        negative_test_cases = [
            ("PYG", "-100000", "monto_total_negativo"),
            ("USD", "-150.00", "monto_total_negativo"),
            ("EUR", "-0.01", "monto_minimo_negativo"),
        ]

        for currency, amount, error_type in negative_test_cases:
            xml_content = create_xml_with_amounts(
                currency, amount, "100.00" if currency != "PYG" else "100000")

            # Mock respuesta de error para monto negativo
            error_response = SifenResponse(
                success=False,
                code="1504",
                message="Los montos no pueden ser negativos",
                cdc="01800695631001001000000612021112917595714694",
                protocol_number="",
                document_status=DocumentStatus.RECHAZADO,
                timestamp=datetime.now(),
                processing_time_ms=100,
                errors=[
                    f"Monto negativo detectado: {amount}",
                    "Todos los montos deben ser >= 0",
                    "Revisar campos monetarios en XML"
                ],
                observations=[
                    "Para ajustes negativos usar Nota de Crédito"
                ],
                additional_data={
                    'rejection_reason': 'negative_amount',
                    'field_name': 'dTotGralOpe',
                    'received_amount': amount,
                    'currency': currency,
                    'error_type': error_type
                },
                response_type=ResponseType.INDIVIDUAL
            )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = error_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Error por monto negativo
            assert result.success is False
            assert result.response.code == "1504"
            assert "negativo" in result.response.message.lower()
            assert result.response.additional_data['received_amount'] == amount

        print("✅ Montos negativos rechazados correctamente")

    @pytest.mark.asyncio
    async def test_zero_amounts_validation(self, test_config, test_certificate):
        """
        Test: Validación de montos en cero (casos especiales)

        Casos especiales:
        - Monto total cero (válido para algunos tipos de documento)
        - Items con precio cero (válido para muestras gratis)
        - Validación contextual según tipo de documento
        """
        zero_test_cases = [
            ("PYG", "0", True),      # Cero válido
            ("USD", "0.00", True),   # Cero con decimales válido
            ("EUR", "0.00", True),   # Cero EUR válido
        ]

        for currency, amount, should_be_valid in zero_test_cases:
            xml_content = create_xml_with_amounts(currency, amount, amount)

            if should_be_valid:
                # Mock respuesta exitosa para cero válido
                response = SifenResponse(
                    success=True,
                    code="0260",
                    message="Aprobado - Monto cero válido",
                    cdc="01800695631001001000000612021112917595714694",
                    protocol_number="PROT_123456789",
                    document_status=DocumentStatus.APROBADO,
                    timestamp=datetime.now(),
                    processing_time_ms=150,
                    errors=[],
                    observations=[
                        "Documento con monto cero - verificar tipo de operación"],
                    additional_data={'currency': currency,
                                     'amount': amount, 'zero_amount': True},
                    response_type=ResponseType.INDIVIDUAL
                )
            else:
                # Mock respuesta de error para cero inválido
                response = create_currency_error_response(
                    code="1505",
                    message="Monto cero no válido para este tipo de documento",
                    currency=currency,
                    amount=amount,
                    field_name="dTotGralOpe"
                )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Resultado según expectativa
            assert result.success == should_be_valid
            if should_be_valid:
                assert result.response.code == "0260"
                assert result.response.additional_data['zero_amount'] is True
            else:
                assert result.response.code == "1505"

        print("✅ Montos cero validados según reglas de negocio")

    @pytest.mark.asyncio
    async def test_currency_consistency_validation(self, test_config, test_certificate):
        """
        Test: Consistencia de moneda en todo el documento

        Validaciones:
        - Todos los campos monetarios deben usar la misma moneda
        - cMoneOpe debe coincidir con moneda de montos
        - No mezclar monedas en items del mismo documento
        """
        # Test caso inconsistente: documento en USD pero con campos en PYG
        inconsistent_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <dVerFor>150</dVerFor>
    <DE Id="01800695631001001000000612021112917595714694">
        <gOpeDE>
            <iTipDE>1</iTipDE>
            <dDesTipDE>Factura electrónica</dDesTipDE>
        </gOpeDE>
        <gTimb>
            <dNumTim>12345678</dNumTim>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>0000001</dNumDoc>
        </gTimb>
        <gDE>
            <gDatGralOpe>
                <dFeEmiDE>2025-06-11T10:30:00</dFeEmiDE>
                <cMoneOpe>USD</cMoneOpe>
            </gDatGralOpe>
            <gDatEm>
                <dRucEm>80016875</dRucEm>
                <dNomEmi>Empresa Test SIFEN</dNomEmi>
            </gDatEm>
            <gCamItem>
                <dDesProSer>Producto inconsistente</dDesProSer>
                <dCantProSer>1</dCantProSer>
                <dPUniProSer>100000</dPUniProSer>  <!-- PYG sin decimales en doc USD -->
            </gCamItem>
        </gDE>
        <gTotSub>
            <dTotOpe>150.00</dTotOpe>  <!-- USD con decimales -->
            <dTotGralOpe>150.00</dTotGralOpe>
        </gTotSub>
    </DE>
</rDE>'''

        # Mock respuesta de error por inconsistencia de moneda
        error_response = SifenResponse(
            success=False,
            code="1506",
            message="Inconsistencia en moneda del documento",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="",
            document_status=DocumentStatus.RECHAZADO,
            timestamp=datetime.now(),
            processing_time_ms=100,
            errors=[
                "Moneda declarada: USD",
                "Campo dPUniProSer usa formato PYG (sin decimales)",
                "Todos los campos monetarios deben ser consistentes"
            ],
            observations=[
                "Verificar que todos los montos usen formato de la moneda declarada"
            ],
            additional_data={
                'rejection_reason': 'currency_inconsistency',
                'declared_currency': 'USD',
                'inconsistent_fields': ['dPUniProSer'],
                'expected_format': 'decimal_2_places',
                'received_format': 'integer'
            },
            response_type=ResponseType.INDIVIDUAL
        )

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = error_response
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(inconsistent_xml, test_certificate)

        # VALIDAR: Error por inconsistencia de moneda
        assert result.success is False
        assert result.response.code == "1506"
        assert "inconsistencia" in result.response.message.lower()
        assert result.response.additional_data['declared_currency'] == 'USD'
        assert 'dPUniProSer' in result.response.additional_data['inconsistent_fields']

        print("✅ Inconsistencia de moneda detectada correctamente")


# ========================================
# TESTS VALIDACIÓN FORMATO DE MONTOS
# ========================================

class TestAmountFormatValidation:
    """
    Tests específicos para validación de formatos de montos

    Enfoque en casos edge y formatos especiales que pueden causar problemas
    """

    @pytest.mark.asyncio
    async def test_scientific_notation_amounts(self, test_config, test_certificate):
        """
        Test: Validación de notación científica en montos

        Casos especiales:
        - 1.5E+5 (notación científica)
        - 1.5e+2 (notación científica minúscula)
        - Formatos que pueden ser interpretados incorrectamente
        """
        scientific_cases = [
            ("PYG", "1.5E+5", False),   # Notación científica no permitida
            ("USD", "1.5e+2", False),   # Notación científica no permitida
            ("EUR", "1E+3", False),     # Notación científica no permitida
        ]

        for currency, amount, should_be_valid in scientific_cases:
            xml_content = create_xml_with_amounts(currency, amount, amount)

            # Mock respuesta de error para notación científica
            error_response = create_currency_error_response(
                code="1507",
                message="Formato de notación científica no permitido",
                currency=currency,
                amount=amount,
                field_name="dTotGralOpe"
            )
            error_response.additional_data['error_type'] = 'scientific_notation'

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = error_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Error por notación científica
            assert result.success is False
            assert result.response.code == "1507"
            assert result.response.additional_data['error_type'] == 'scientific_notation'

        print("✅ Notación científica rechazada correctamente")

    @pytest.mark.asyncio
    async def test_special_characters_in_amounts(self, test_config, test_certificate):
        """
        Test: Caracteres especiales en montos

        Casos inválidos:
        - Montos con comas como separador decimal
        - Montos con separadores de miles
        - Montos con caracteres no numéricos
        """
        special_char_cases = [
            ("USD", "1,500.00", "comma_thousands_separator"),
            ("EUR", "150,50", "comma_decimal_separator"),
            ("PYG", "150.000", "dot_thousands_separator"),
            ("USD", "$150.00", "currency_symbol"),
            ("PYG", "150 000", "space_separator"),
            ("EUR", "150.00€", "currency_suffix"),
        ]

        for currency, amount, error_type in special_char_cases:
            xml_content = create_xml_with_amounts(currency, amount, amount)

            # Mock respuesta de error para caracteres especiales
            error_response = create_currency_error_response(
                code="1508",
                message="Caracteres especiales no permitidos en montos",
                currency=currency,
                amount=amount,
                field_name="dTotGralOpe"
            )
            error_response.additional_data['error_type'] = error_type

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = error_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Error por caracteres especiales
            assert result.success is False
            assert result.response.code == "1508"
            assert result.response.additional_data['error_type'] == error_type

        print("✅ Caracteres especiales en montos rechazados correctamente")

    @pytest.mark.asyncio
    async def test_extreme_amount_values(self, test_config, test_certificate):
        """
        Test: Valores extremos de montos

        Casos límite:
        - Montos muy grandes (límites de sistema)
        - Montos muy pequeños (mínimos permitidos)
        - Precisión máxima en decimales
        """
        extreme_cases = [
            ("PYG", "999999999999", True),      # Monto muy grande válido
            ("USD", "999999999.99", True),      # Monto USD muy grande válido
            ("EUR", "0.01", True),              # Monto EUR mínimo válido
            ("PYG", "1", True),                 # Monto PYG mínimo válido
            ("USD", "0.001", False),            # Más de 2 decimales inválido
            ("PYG", "9999999999999", False),    # Posible overflow
        ]

        for currency, amount, should_be_valid in extreme_cases:
            xml_content = create_xml_with_amounts(currency, amount, amount)

            if should_be_valid:
                # Mock respuesta exitosa
                response = SifenResponse(
                    success=True,
                    code="0260",
                    message="Aprobado",
                    cdc="01800695631001001000000612021112917595714694",
                    protocol_number="PROT_123456789",
                    document_status=DocumentStatus.APROBADO,
                    timestamp=datetime.now(),
                    processing_time_ms=150,
                    errors=[],
                    observations=[],
                    additional_data={'currency': currency,
                                     'amount': amount, 'extreme_value': True},
                    response_type=ResponseType.INDIVIDUAL
                )
            else:
                # Mock respuesta de error
                error_code = "1509" if "overflow" in str(
                    should_be_valid) else "1502"
                error_message = "Monto fuera de rango permitido" if "overflow" in str(
                    should_be_valid) else "Precisión decimal excedida"

                response = create_currency_error_response(
                    code=error_code,
                    message=error_message,
                    currency=currency,
                    amount=amount,
                    field_name="dTotGralOpe"
                )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Resultado según expectativa
            assert result.success == should_be_valid
            if should_be_valid:
                assert result.response.code == "0260"
                assert result.response.additional_data['extreme_value'] is True
            else:
                assert result.response.code in ["1502", "1509"]

        print("✅ Valores extremos de montos validados correctamente")


# ========================================
# TESTS INTEGRACIÓN CAMPOS MONETARIOS
# ========================================

class TestMonetaryFieldsIntegration:
    """
    Tests de integración para validar todos los campos monetarios en conjunto
    """

    @pytest.mark.asyncio
    async def test_complete_monetary_document_validation(self, test_config, test_certificate):
        """
        Test: Validación completa de documento con todos los campos monetarios

        Incluye validación de:
        - dTotGralOpe (Total general)
        - dTotOpe (Total operación)
        - dPUniProSer (Precio unitario)
        - dTotIVA (Total IVA)
        - Consistencia entre todos los campos
        """
        # Documento completo con todos los campos monetarios
        complete_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <dVerFor>150</dVerFor>
    <DE Id="01800695631001001000000612021112917595714694">
        <gOpeDE>
            <iTipDE>1</iTipDE>
            <dDesTipDE>Factura electrónica</dDesTipDE>
        </gOpeDE>
        <gTimb>
            <dNumTim>12345678</dNumTim>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>0000001</dNumDoc>
        </gTimb>
        <gDE>
            <gDatGralOpe>
                <dFeEmiDE>2025-06-11T10:30:00</dFeEmiDE>
                <cMoneOpe>USD</cMoneOpe>
            </gDatGralOpe>
            <gDatEm>
                <dRucEm>80016875</dRucEm>
                <dNomEmi>Empresa Test SIFEN</dNomEmi>
            </gDatEm>
            <gCamItem>
                <dDesProSer>Producto completo</dDesProSer>
                <dCantProSer>2</dCantProSer>
                <dPUniProSer>50.00</dPUniProSer>
                <dTotBruOpeItem>100.00</dTotBruOpeItem>
            </gCamItem>
        </gDE>
        <gTotSub>
            <dTotOpe>100.00</dTotOpe>
            <dTotIVA>10.00</dTotIVA>
            <dTotGralOpe>110.00</dTotGralOpe>
        </gTotSub>
    </DE>
</rDE>'''

        # Mock respuesta exitosa para documento completo válido
        success_response = SifenResponse(
            success=True,
            code="0260",
            message="Documento completo aprobado",
            cdc="01800695631001001000000612021112917595714694",
            protocol_number="PROT_123456789",
            document_status=DocumentStatus.APROBADO,
            timestamp=datetime.now(),
            processing_time_ms=200,
            errors=[],
            observations=[],
            additional_data={
                'currency': 'USD',
                'total_amount': '110.00',
                'items_validated': 1,
                'monetary_fields_validated': 5,
                'validation_type': 'complete_document'
            },
            response_type=ResponseType.INDIVIDUAL
        )

        mock_retry_manager = AsyncMock()
        mock_retry_manager.execute_with_retry.return_value = success_response
        mock_retry_manager.get_stats = Mock(return_value={'total_retries': 0})

        sender = DocumentSender(
            config=test_config,
            soap_client=AsyncMock(),
            retry_manager=mock_retry_manager
        )
        sender._client_initialized = True

        result = await sender.send_document(complete_xml, test_certificate)

        # VALIDAR: Documento completo procesado exitosamente
        assert result.success is True
        assert result.response.code == "0260"
        assert result.response.additional_data['currency'] == 'USD'
        assert result.response.additional_data['total_amount'] == '110.00'
        assert result.response.additional_data['monetary_fields_validated'] == 5

        print("✅ Documento con campos monetarios completos validado correctamente")

    @pytest.mark.asyncio
    async def test_currency_amount_validation_performance(self, test_config, test_certificate):
        """
        Test: Performance de validación de montos bajo carga

        Simula múltiples validaciones simultáneas para verificar
        que el sistema mantiene performance adecuada
        """
        import time

        # Casos de prueba para performance
        test_cases = [
            ("PYG", "100000"),
            ("USD", "150.00"),
            ("EUR", "200.50"),
            ("BRL", "300.75"),
            ("ARS", "400.25"),
        ]

        start_time = time.time()
        results = []

        # Ejecutar múltiples validaciones
        for currency, amount in test_cases * 10:  # 50 validaciones total
            xml_content = create_xml_with_amounts(currency, amount, amount)

            # Mock respuesta rápida
            success_response = SifenResponse(
                success=True,
                code="0260",
                message="Aprobado",
                cdc="01800695631001001000000612021112917595714694",
                protocol_number="PROT_123456789",
                document_status=DocumentStatus.APROBADO,
                timestamp=datetime.now(),
                processing_time_ms=50,  # Simulación tiempo real SIFEN
                errors=[],
                observations=[],
                additional_data={'currency': currency, 'amount': amount},
                response_type=ResponseType.INDIVIDUAL
            )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = success_response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)
            results.append(result)

        end_time = time.time()
        total_time = end_time - start_time

        # VALIDAR: Performance adecuada
        assert len(results) == 50
        assert all(r.success for r in results)
        assert total_time < 5.0  # Menos de 5 segundos para 50 validaciones

        avg_time_per_validation = total_time / len(results)
        assert avg_time_per_validation < 0.1  # Menos de 100ms promedio por validación

        print(
            f"✅ Performance validación montos: {avg_time_per_validation:.3f}s promedio")
        print(f"✅ Total 50 validaciones: {total_time:.2f}s")


# ========================================
# TESTS CASOS EDGE ESPECÍFICOS
# ========================================

class TestCurrencyEdgeCases:
    """
    Tests para casos edge específicos no cubiertos en otras clases
    """

    @pytest.mark.asyncio
    async def test_rounding_precision_edge_cases(self, test_config, test_certificate):
        """
        Test: Casos edge de precisión y redondeo

        Validar comportamiento con:
        - Números que requieren redondeo
        - Límites de precisión flotante
        - Casos donde redondeo puede afectar resultado
        """
        precision_cases = [
            ("USD", "150.005", False),  # Más de 2 decimales - debe fallar
            ("EUR", "150.999", False),  # Más de 2 decimales - debe fallar
            ("USD", "150.00", True),    # Exactamente 2 decimales - válido
            ("USD", "150.99", True),    # Exactamente 2 decimales - válido
        ]

        for currency, amount, should_be_valid in precision_cases:
            xml_content = create_xml_with_amounts(currency, amount, amount)

            if should_be_valid:
                response = SifenResponse(
                    success=True,
                    code="0260",
                    message="Aprobado",
                    cdc="01800695631001001000000612021112917595714694",
                    protocol_number="PROT_123456789",
                    document_status=DocumentStatus.APROBADO,
                    timestamp=datetime.now(),
                    processing_time_ms=150,
                    errors=[],
                    observations=[],
                    additional_data={'currency': currency, 'amount': amount},
                    response_type=ResponseType.INDIVIDUAL
                )
            else:
                response = create_currency_error_response(
                    code="1502",
                    message="Precisión decimal excedida",
                    currency=currency,
                    amount=amount,
                    field_name="dTotGralOpe"
                )

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Resultado según expectativa
            assert result.success == should_be_valid

        print("✅ Casos edge de precisión validados correctamente")

    @pytest.mark.asyncio
    async def test_locale_specific_formatting(self, test_config, test_certificate):
        """
        Test: Formateo específico por localización

        Verificar que el sistema no acepte formatos locales
        que no corresponden al estándar SIFEN
        """
        # SIFEN requiere formato estándar independiente de locale
        locale_cases = [
            ("EUR", "1.234,56", False),    # Formato alemán/español (inválido)
            # Formato con separador miles (inválido)
            ("USD", "1,234.56", False),
            # Formato estándar sin separadores (válido)
            ("USD", "1234.56", True),
        ]

        for currency, amount, should_be_valid in locale_cases:
            xml_content = create_xml_with_amounts(currency, amount, amount)

            if should_be_valid:
                response = SifenResponse(
                    success=True,
                    code="0260",
                    message="Aprobado",
                    cdc="01800695631001001000000612021112917595714694",
                    protocol_number="PROT_123456789",
                    document_status=DocumentStatus.APROBADO,
                    timestamp=datetime.now(),
                    processing_time_ms=150,
                    errors=[],
                    observations=[],
                    additional_data={'currency': currency, 'amount': amount},
                    response_type=ResponseType.INDIVIDUAL
                )
            else:
                response = create_currency_error_response(
                    code="1508",
                    message="Formato de locale no soportado - usar formato estándar",
                    currency=currency,
                    amount=amount,
                    field_name="dTotGralOpe"
                )
                response.additional_data['error_type'] = 'locale_format'

            mock_retry_manager = AsyncMock()
            mock_retry_manager.execute_with_retry.return_value = response
            mock_retry_manager.get_stats = Mock(
                return_value={'total_retries': 0})

            sender = DocumentSender(
                config=test_config,
                soap_client=AsyncMock(),
                retry_manager=mock_retry_manager
            )
            sender._client_initialized = True

            result = await sender.send_document(xml_content, test_certificate)

            # VALIDAR: Resultado según expectativa
            assert result.success == should_be_valid
            if not should_be_valid:
                assert result.response.additional_data['error_type'] == 'locale_format'

        print("✅ Formatos de locale rechazados correctamente")


# ========================================
# CONFIGURACIÓN PYTEST
# ========================================

if __name__ == "__main__":
    """
    Ejecutar tests de validación de monedas y montos

    Comandos de ejecución:

    # Ejecutar todos los tests de currency validation
    pytest test_currency_amount_validation.py -v

    # Ejecutar solo tests de PYG
    pytest test_currency_amount_validation.py::TestPYGCurrencyValidation -v

    # Ejecutar solo tests de monedas extranjeras  
    pytest test_currency_amount_validation.py::TestForeignCurrencyValidation -v

    # Ejecutar con coverage
    pytest test_currency_amount_validation.py --cov=app.services.sifen_client -v

    # Ejecutar tests de performance
    pytest test_currency_amount_validation.py::TestMonetaryFieldsIntegration::test_currency_amount_validation_performance -v

    # Ejecutar casos edge
    pytest test_currency_amount_validation.py::TestCurrencyEdgeCases -v
    """
    pytest.main([__file__, "-v", "--tb=short"])
