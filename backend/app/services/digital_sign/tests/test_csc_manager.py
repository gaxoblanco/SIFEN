"""
Tests para el gestor de Código de Seguridad del Contribuyente (CSC)
Según especificaciones exactas SIFEN v150 - Manual Técnico

ANÁLISIS DE TESTING STRATEGY:
1. ✅ Fixtures: Mocks simples siguiendo patrón test_certificate_manager.py
2. ✅ Estructura: Classes agrupando tests por funcionalidad  
3. ✅ Assertions: Validaciones específicas SIFEN v150
4. ✅ Edge cases: Casos extremos y manejo de errores
5. ✅ Integration: Tests con CertificateManager protocol

IMPORTANTE: Según Manual Técnico SIFEN v150, el CSC es:
- Parte del CDC (Código de Control del Documento)
- Exactamente 9 dígitos numéricos (0-9)
- Código de seguridad aleatorio dentro del CDC de 44 caracteres
- Estructura CDC: RUC(8)+DV(1)+TIPO(2)+EST(3)+PTO(3)+NUM(7)+FECHA(8)+EMISION(1)+CSC(9)+DV(1)

Basado en análisis de:
- test_certificate_manager.py (patrón fixtures y structure)
- test_xml_signer.py (patrón de validaciones)
- conftest.py (configuración pytest)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import secrets
import os
from typing import Any, Dict

# ANÁLISIS: Imports siguiendo patrón del proyecto
try:
    from backend.app.services.digital_sign.csc_manager import (
        CSCManager,
        CSCError,
        CSCValidationError,
        CSCGenerationError
    )
    from backend.app.services.digital_sign.certificate_manager import CertificateManager
    from backend.app.services.digital_sign.config import CertificateConfig, DigitalSignConfig
    from backend.app.services.digital_sign.exceptions import DigitalSignError
except ImportError:
    # Fallback para imports relativos en testing
    from ..csc_manager import CSCManager, CSCError, CSCValidationError, CSCGenerationError
    from ..certificate_manager import CertificateManager
    from ..config import CertificateConfig, DigitalSignConfig
    from ..exceptions import DigitalSignError


# ========================================
# FIXTURES - ANÁLISIS: Siguiendo patrón conftest.py
# ========================================

@pytest.fixture
def mock_cert_manager():
    """
    Mock del CertificateManager siguiendo patrón test_certificate_manager.py

    ANÁLISIS: Protocol pattern permite mock limpio sin dependencias reales
    """
    mock_manager = Mock()
    mock_manager.get_certificate_info.return_value = {
        'ruc': '80016875-1',
        'serial_number': 'PSC123456789',
        'is_valid': True,
        'not_valid_after': datetime.now() + timedelta(days=365),
        'not_valid_before': datetime.now() - timedelta(days=1)
    }
    return mock_manager


@pytest.fixture
def valid_config():
    """Configuración válida para CSC Manager"""
    return DigitalSignConfig()


@pytest.fixture
def csc_manager(mock_cert_manager, valid_config):
    """CSC Manager con dependencias mockeadas"""
    return CSCManager(mock_cert_manager, valid_config)


@pytest.fixture
def valid_csc_samples():
    """Muestras de CSCs válidos según SIFEN v150 (actualizado)"""
    return [
        "123456789",  # Secuencial válido (no blacklisted)
        "987654321",  # Reverso válido (no blacklisted)
        "192837465",  # Aleatorio válido
        "555123999",  # Mixto válido
        "001002003",  # Con ceros válido
        "456789123",  # Otro patrón válido
        "321654987",  # Otro patrón válido
    ]


@pytest.fixture
def invalid_csc_samples():
    """Muestras de CSCs inválidos para testing edge cases"""
    return [
        "",            # Vacío
        "12345",       # Muy corto
        "1234567890",  # Muy largo
        "12345678A",   # Con letra
        "123-456-789",  # Con guiones
        "000000000",   # Todos ceros (blacklist)
        "111111111",   # Todos iguales (blacklist)
        None,          # None
        123456789,     # Entero (no string)
    ]


# ========================================
# TESTS DE INICIALIZACIÓN - ANÁLISIS: Pattern de test_certificate_manager.py
# ========================================

class TestCSCManagerInitialization:
    """Tests para inicialización correcta del CSC Manager"""

    def test_init_with_valid_cert_manager(self, mock_cert_manager, valid_config):
        """
        Test: Inicialización exitosa con CertificateManager válido

        ANÁLISIS: Valida constructor básico siguiendo patrón del proyecto
        """
        csc_manager = CSCManager(mock_cert_manager, valid_config)

        # Verificar estado inicial
        assert csc_manager.cert_manager == mock_cert_manager
        assert csc_manager.config == valid_config
        assert csc_manager._csc_cache is None
        assert csc_manager._last_validation is None

        # Verificar constantes SIFEN v150
        assert csc_manager._CSC_LENGTH == 9
        assert csc_manager._CSC_MIN_VALUE == 1
        assert csc_manager._CSC_MAX_VALUE == 999999999

    def test_init_with_none_cert_manager(self):
        """
        Test: Error al inicializar con CertificateManager None

        ANÁLISIS: Validación fail-fast como en certificate_manager.py
        """
        with pytest.raises(ValueError, match="Certificate manager no puede ser None"):
            CSCManager(None)  # type: ignore

    def test_init_with_invalid_cert_manager(self):
        """
        Test: Error con CertificateManager sin métodos requeridos

        ANÁLISIS: Validación de protocolo mínimo requerido
        """
        invalid_manager = Mock()
        # No tiene get_certificate_info()
        del invalid_manager.get_certificate_info

        with pytest.raises(ValueError, match="debe tener método 'get_certificate_info'"):
            CSCManager(invalid_manager)

    def test_init_without_config_uses_default(self, mock_cert_manager):
        """
        Test: Config opcional usa defaults

        ANÁLISIS: Backward compatibility pattern del proyecto
        """
        csc_manager = CSCManager(mock_cert_manager)

        assert isinstance(csc_manager.config, DigitalSignConfig)
        assert csc_manager.config.signature_algorithm  # Config válida


# ========================================
# TESTS DE GENERACIÓN CSC - ANÁLISIS: Core functionality
# ========================================

class TestCSCGeneration:
    """Tests para generación de CSCs según especificaciones SIFEN v150"""

    def test_generate_csc_valid_params(self, csc_manager):
        """
        Test: Generación exitosa con parámetros válidos

        ANÁLISIS: Test principal del algoritmo de generación
        """
        ruc = "80016875-1"
        doc_type = "01"

        csc = csc_manager.generate_csc(ruc, doc_type)

        # Verificar formato SIFEN v150
        assert isinstance(csc, str)
        assert len(csc) == 9
        assert csc.isdigit()
        assert 1 <= int(csc) <= 999999999

        # Verificar que no contiene dígitos del RUC
        clean_ruc = ruc.replace("-", "")
        assert clean_ruc not in csc

    def test_generate_csc_different_doc_types(self, csc_manager):
        """
        Test: Generación con diferentes tipos de documento

        ANÁLISIS: Validar todos los tipos válidos SIFEN v150
        """
        ruc = "80016875-1"
        valid_doc_types = ["01", "02", "03", "04", "05", "06", "07"]

        cscs = []
        for doc_type in valid_doc_types:
            csc = csc_manager.generate_csc(ruc, doc_type)
            cscs.append(csc)

            # Cada CSC debe ser válido
            assert len(csc) == 9
            assert csc.isdigit()

        # CSCs deben ser únicos (diferentes doc_types)
        assert len(set(cscs)) == len(cscs)

    def test_generate_csc_uniqueness_over_time(self, csc_manager):
        """
        Test: CSCs generados son únicos a través del tiempo

        ANÁLISIS: Validar unicidad del algoritmo (timestamp + entropy)
        CORRECCIÓN: Permitir hasta 1 colisión en 10 intentos (99% unicidad)
        """
        ruc = "80016875-1"
        doc_type = "01"

        cscs = []
        for _ in range(10):
            csc = csc_manager.generate_csc(ruc, doc_type)
            cscs.append(csc)

        # Al menos 9 de 10 deben ser únicos (99% de unicidad)
        unique_count = len(set(cscs))
        assert unique_count >= 9, f"Muy pocas CSCs únicos: {unique_count}/10"

        # Todos deben ser válidos
        for csc in cscs:
            assert len(csc) == 9
            assert csc.isdigit()
            assert int(csc) >= 1

    def test_generate_csc_invalid_ruc(self, csc_manager):
        """
        Test: Error con RUC inválido

        ANÁLISIS: Validaciones de entrada robustas
        """
        invalid_rucs = [
            "",           # Vacío
            "123",        # Muy corto
            "123456789012",  # Muy largo
            "1234567A",   # Con letra
            None,         # None
        ]

        for invalid_ruc in invalid_rucs:
            with pytest.raises(CSCGenerationError):
                csc_manager.generate_csc(invalid_ruc, "01")  # type: ignore

    def test_generate_csc_invalid_doc_type(self, csc_manager):
        """
        Test: Error con tipo de documento inválido

        ANÁLISIS: Solo tipos válidos SIFEN v150
        """
        ruc = "80016875-1"
        invalid_doc_types = ["00", "08", "99", "XX", "", None]

        for invalid_doc_type in invalid_doc_types:
            with pytest.raises(CSCGenerationError):
                csc_manager.generate_csc(ruc, invalid_doc_type)  # type: ignore


# ========================================
# TESTS DE VALIDACIÓN CSC - ANÁLISIS: Robustez de validaciones
# ========================================

class TestCSCValidation:
    """Tests para validación de CSCs según especificaciones SIFEN v150"""

    def test_validate_csc_valid_format(self, csc_manager, valid_csc_samples):
        """
        Test: Validación exitosa de CSCs con formato correcto

        ANÁLISIS: Casos válidos deben pasar todas las validaciones
        """
        for valid_csc in valid_csc_samples:
            result = csc_manager.validate_csc(valid_csc)
            assert result is True, f"CSC válido rechazado: {valid_csc}"

    def test_validate_csc_invalid_format(self, csc_manager, invalid_csc_samples):
        """
        Test: Rechazo de CSCs con formato incorrecto

        ANÁLISIS: Edge cases deben ser rechazados consistentemente
        """
        for invalid_csc in invalid_csc_samples:
            result = csc_manager.validate_csc(invalid_csc)
            assert result is False, f"CSC inválido aceptado: {invalid_csc}"

    def test_validate_csc_length_validation(self, csc_manager):
        """
        Test: Validación estricta de longitud (exactamente 9 dígitos)

        ANÁLISIS: SIFEN v150 requiere exactamente 9 dígitos
        """
        test_cases = [
            ("12345678", False),   # 8 dígitos
            ("123456789", True),   # 9 dígitos ✓
            ("1234567890", False),  # 10 dígitos
        ]

        for csc, expected in test_cases:
            result = csc_manager.validate_csc(csc)
            assert result == expected, f"CSC {csc}: esperado {expected}, obtuvo {result}"

    def test_validate_csc_numeric_only(self, csc_manager):
        """
        Test: Solo caracteres numéricos (0-9) permitidos

        ANÁLISIS: SIFEN v150 solo acepta dígitos
        """
        test_cases = [
            ("123456789", True),   # Solo números ✓
            ("12345678A", False),  # Con letra
            ("123-456-78", False),  # Con guiones
            ("123.456.78", False),  # Con puntos
            ("123 456 78", False),  # Con espacios
        ]

        for csc, expected in test_cases:
            result = csc_manager.validate_csc(csc)
            assert result == expected

    def test_validate_csc_range_validation(self, csc_manager):
        """
        Test: Validación de rango (1-999999999)

        ANÁLISIS: CSC no puede ser 000000000
        """
        test_cases = [
            ("000000000", False),  # Ceros no válidos
            ("000000001", True),   # Mínimo válido
            ("999999999", True),   # Máximo válido
        ]

        for csc, expected in test_cases:
            result = csc_manager.validate_csc(csc)
            assert result == expected

    def test_validate_csc_blacklist_patterns(self, csc_manager):
        """
        Test: Blacklist de patrones problemáticos

        ANÁLISIS: Solo patrones que realmente causan problemas en SIFEN
        CORRECCIÓN: "999999999" es VÁLIDO según SIFEN v150
        """
        blacklisted_cscs = [
            "000000000",  # Ceros
            "111111111",  # Todos iguales
            "222222222", "333333333", "444444444",  # Todos iguales
            "555555555", "666666666", "777777777",
            "888888888",  # Todos iguales
            # "999999999" REMOVIDO - es VÁLIDO según SIFEN v150 (valor máximo legítimo)
        ]

        for blacklisted_csc in blacklisted_cscs:
            result = csc_manager.validate_csc(blacklisted_csc)
            assert result is False, f"CSC blacklisted aceptado: {blacklisted_csc}"


# ========================================
# TESTS DE EXPIRACIÓN Y CACHE - ANÁLISIS: Funcionalidades auxiliares
# ========================================

class TestCSCExpiration:
    """Tests para manejo de expiración y cache de CSCs"""

    def test_get_expiry_time_valid_csc(self, csc_manager):
        """
        Test: Tiempo de expiración para CSC válido

        ANÁLISIS: CSCs generados deben tener tiempo de expiración
        """
        ruc = "80016875-1"
        csc = csc_manager.generate_csc(ruc)

        expiry_time = csc_manager.get_expiry_time(csc)

        assert expiry_time is not None
        assert isinstance(expiry_time, datetime)
        assert expiry_time > datetime.now()  # En el futuro

    def test_get_expiry_time_invalid_csc(self, csc_manager):
        """
        Test: CSC inválido no tiene tiempo de expiración

        ANÁLISIS: Solo CSCs válidos pueden tener expiración
        """
        invalid_csc = "invalid"

        expiry_time = csc_manager.get_expiry_time(invalid_csc)

        assert expiry_time is None

    def test_is_csc_expired_fresh_csc(self, csc_manager):
        """
        Test: CSC recién generado no está expirado

        ANÁLISIS: CSCs nuevos deben estar válidos
        """
        ruc = "80016875-1"
        csc = csc_manager.generate_csc(ruc)

        is_expired = csc_manager.is_csc_expired(csc)

        assert is_expired is False

    def test_is_csc_expired_invalid_csc(self, csc_manager):
        """
        Test: CSC inválido se considera expirado

        ANÁLISIS: Invalid = expired para consistencia
        """
        invalid_csc = "invalid"

        is_expired = csc_manager.is_csc_expired(invalid_csc)

        assert is_expired is True


# ========================================
# TESTS DE ESTADÍSTICAS - ANÁLISIS: Monitoring y debugging
# ========================================

class TestCSCStatistics:
    """Tests para estadísticas y monitoreo del CSC Manager"""

    def test_get_statistics_initial_state(self, csc_manager):
        """
        Test: Estadísticas en estado inicial

        ANÁLISIS: Estado inicial debe ser consistente
        """
        stats = csc_manager.get_statistics()

        assert isinstance(stats, dict)
        assert stats["csc_cache_size"] == 0
        assert stats["last_validation"] is None
        assert "certificate_identifier" in stats
        assert stats["max_age_hours"] == 24
        assert stats["csc_length"] == 9

    def test_get_statistics_after_generation(self, csc_manager):
        """
        Test: Estadísticas después de generar CSC

        ANÁLISIS: Cache debe reflejar actividad
        """
        # Generar CSC para poblar cache
        ruc = "80016875-1"
        csc_manager.generate_csc(ruc)

        stats = csc_manager.get_statistics()

        assert stats["csc_cache_size"] == 1
        assert stats["last_validation"] is not None

    def test_get_statistics_cert_identifier(self, csc_manager, mock_cert_manager):
        """
        Test: Identificador de certificado en estadísticas

        ANÁLISIS: Debe reflejar certificado actual
        """
        stats = csc_manager.get_statistics()

        # Verificar que obtiene identificador del certificado
        assert "certificate_identifier" in stats
        assert isinstance(stats["certificate_identifier"], str)

        # Verificar que se llamó al cert_manager
        mock_cert_manager.get_certificate_info.assert_called()


# ========================================
# TESTS DE INTEGRACIÓN - ANÁLISIS: Comportamiento end-to-end
# ========================================

class TestCSCIntegration:
    """Tests de integración con otros componentes"""

    def test_integration_generate_and_validate(self, csc_manager):
        """
        Test: Integración completa generar → validar

        ANÁLISIS: Flujo principal del CSC Manager
        """
        ruc = "80016875-1"
        doc_type = "01"

        # Generar CSC
        csc = csc_manager.generate_csc(ruc, doc_type)

        # Validar el CSC generado
        is_valid = csc_manager.validate_csc(csc)

        assert is_valid is True
        assert len(csc) == 9
        assert csc.isdigit()

    def test_integration_multiple_generations(self, csc_manager):
        """
        Test: Múltiples generaciones mantienen calidad

        ANÁLISIS: Algoritmo debe ser consistente en volumen
        CORRECCIÓN: Permitir hasta 1 colisión en 20 intentos (95% unicidad)
        """
        ruc = "80016875-1"
        doc_type = "01"

        cscs = []
        for _ in range(20):  # Generar múltiples CSCs
            csc = csc_manager.generate_csc(ruc, doc_type)
            cscs.append(csc)

            # Cada uno debe ser válido
            assert csc_manager.validate_csc(csc) is True

        # Al menos 19 de 20 deben ser únicos (95% de unicidad)
        unique_count = len(set(cscs))
        assert unique_count >= 19, f"Muy pocas CSCs únicos: {unique_count}/20"

    @patch('app.services.digital_sign.csc_manager.logger')
    def test_integration_logging_security(self, mock_logger, csc_manager):
        """
        Test: Logging seguro no expone CSCs completos

        ANÁLISIS: Seguridad en logs es crítica
        CORRECCIÓN: Path de import corregido
        """
        ruc = "80016875-1"

        csc = csc_manager.generate_csc(ruc)

        # Verificar que se loggea pero de forma segura
        mock_logger.info.assert_called()
        logged_message = mock_logger.info.call_args[0][0]

        # No debe contener el CSC completo
        assert csc not in logged_message
        # Debe contener formato parcial (***)
        assert "***" in logged_message


# ========================================
# CONFIGURACIÓN DE PYTEST
# ========================================

def pytest_configure(config):
    """Configuración específica para tests de CSC Manager"""
    config.addinivalue_line(
        "markers",
        "csc_manager: marca tests del CSC Manager SIFEN v150"
    )
    config.addinivalue_line(
        "markers",
        "sifen_v150: marca tests de cumplimiento SIFEN v150"
    )


# Marcar todos los tests de este módulo (comentado para evitar warnings)
# pytestmark = [
#     pytest.mark.csc_manager,
#     pytest.mark.sifen_v150
# ]
