"""
Gestor de Código de Seguridad del Contribuyente (CSC) para SIFEN v150
Según especificaciones exactas del Manual Técnico v150

IMPORTANTE: Según Manual Técnico SIFEN v150, el CSC es:
- Parte del CDC (Código de Control del Documento)
- 9 dígitos aleatorios (no 32 caracteres como otras implementaciones)
- Se usa para generar el CDC completo de 44 caracteres
- Estructura CDC: RUC(8)+DV(1)+TIPO(2)+EST(3)+PTO(3)+NUM(7)+FECHA(8)+EMISION(1)+CSC(9)+DV(1)

El CSC se utiliza en:
1. Generación del CDC (9 dígitos dentro del CDC de 44 caracteres)
2. Parámetro IdCSC en el código QR del KuDE
3. Validación por parte de SIFEN

Basado en:
- Manual Técnico SIFEN v150 (Sección 5: CDC)
- Especificaciones oficiales SET Paraguay
- Estructura real CDC verificada en producción
"""
import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Protocol
from pathlib import Path
import logging

from .certificate_manager import CertificateManager


logger = logging.getLogger(__name__)


class CertificateManagerProtocol(Protocol):
    """Protocolo que define la interfaz mínima requerida para un certificate manager"""

    def get_certificate_info(self) -> Dict[str, Any]:
        """Obtiene información del certificado"""
        ...


class CSCError(Exception):
    """Excepción base para errores del CSC"""
    pass


class CSCValidationError(CSCError):
    """Excepción para errores de validación del CSC"""
    pass


class CSCManager:
    """
    Gestor de Código de Seguridad del Contribuyente (CSC) según SIFEN v150

    El CSC es un componente crítico del CDC que consta de:
    - 9 dígitos aleatorios
    - Solo números (0-9)
    - Único por contribuyente
    - Debe mantenerse seguro y confidencial

    Responsabilidades:
    - Generar CSCs de 9 dígitos según especificaciones v150
    - Validar formato y unicidad del CSC
    - Gestionar almacenamiento seguro
    - Integrar con generación de CDC
    - Proporcionar CSC para código QR del KuDE
    """

    def __init__(self, certificate_manager: CertificateManagerProtocol):
        """
        Inicializa el gestor CSC

        Args:
            certificate_manager: Gestor de certificados digitales

        Raises:
            ValueError: Si certificate_manager es None o no tiene métodos necesarios
        """
        if certificate_manager is None:
            raise ValueError("Certificate manager no puede ser None")

        # Validar que tenga los métodos necesarios (duck typing)
        if not hasattr(certificate_manager, 'get_certificate_info'):
            raise ValueError(
                "Certificate manager debe tener método 'get_certificate_info'")

        self.cert_manager = certificate_manager
        self._csc_cache: Optional[str] = None
        self._last_validation: Optional[datetime] = None
        self._validation_cache_duration = timedelta(hours=1)

        logger.info("CSC Manager inicializado correctamente")

    def validate_csc(self, csc: Optional[str]) -> bool:
        """
        Valida un CSC según especificaciones SIFEN v150

        Reglas de validación según Manual Técnico v150:
        - Exactamente 9 dígitos
        - Solo números (0-9)
        - Sin caracteres especiales, letras o espacios

        Args:
            csc: Código CSC a validar

        Returns:
            True si el CSC es válido según v150, False en caso contrario
        """
        try:
            if not csc:
                logger.debug("CSC es None o vacío")
                return False

            if not isinstance(csc, str):
                logger.debug(f"CSC no es string: {type(csc)}")
                return False

            # Verificar longitud exacta: 9 dígitos según v150
            if len(csc) != 9:
                logger.debug(
                    f"CSC longitud incorrecta: {len(csc)}, esperado: 9")
                return False

            # Verificar que solo contenga dígitos (0-9)
            if not csc.isdigit():
                logger.debug(f"CSC contiene caracteres no numéricos: {csc}")
                return False

            # Verificar que no sea un patrón obvio (todos iguales)
            if len(set(csc)) == 1:
                logger.warning("CSC con patrón obvio (todos dígitos iguales)")
                return False

            return True

        except Exception as e:
            logger.warning(f"Error validando CSC: {e}")
            return False

    def generate_csc(self, for_testing: bool = False) -> str:
        """
        Genera un CSC nuevo según especificaciones SIFEN v150

        Genera exactamente 9 dígitos aleatorios criptográficamente seguros
        según las especificaciones del Manual Técnico v150.

        Args:
            for_testing: Si es True, genera CSC con prefijo para testing

        Returns:
            CSC de 9 dígitos numéricos
        """
        try:
            if for_testing:
                # Para testing, usar patrón específico pero válido
                # Formato: "TEST" (como dígitos) + 5 aleatorios
                # T=8, E=3, S=1, T=8 = "8318" + 5 aleatorios
                test_prefix = "8318"  # TEST en dígitos
                random_suffix = ''.join(secrets.choice(
                    '0123456789') for _ in range(5))
                csc = test_prefix + random_suffix
            else:
                # Generar 9 dígitos completamente aleatorios
                csc = ''.join(secrets.choice('0123456789') for _ in range(9))

            # Verificar que el CSC generado sea válido
            if not self.validate_csc(csc):
                raise CSCError(
                    "Error interno: CSC generado no es válido según v150")

            logger.info(
                f"CSC generado correctamente (hash: {self._get_csc_hash(csc)[:8]})")
            return csc

        except Exception as e:
            logger.error(f"Error generando CSC: {e}")
            raise CSCError(f"No se pudo generar CSC: {e}")

    def generate_csc_batch(self, count: int) -> List[str]:
        """
        Genera múltiples CSCs únicos

        Args:
            count: Número de CSCs a generar

        Returns:
            Lista de CSCs únicos de 9 dígitos cada uno

        Raises:
            ValueError: Si count es inválido
            CSCError: Si no se pueden generar CSCs únicos
        """
        if count <= 0:
            raise ValueError("Count debe ser mayor a 0")

        if count > 10000:
            raise ValueError("Count muy alto, máximo 10000 CSCs por lote")

        cscs = set()
        max_attempts = count * 10  # Evitar bucle infinito
        attempts = 0

        while len(cscs) < count and attempts < max_attempts:
            csc = self.generate_csc()
            cscs.add(csc)
            attempts += 1

        if len(cscs) < count:
            raise CSCError(f"No se pudieron generar {count} CSCs únicos")

        logger.info(f"Generados {count} CSCs únicos exitosamente")
        return list(cscs)

    def set_csc(self, csc: str) -> None:
        """
        Establece el CSC para el contribuyente

        Args:
            csc: Código CSC de 9 dígitos a establecer

        Raises:
            CSCValidationError: Si el CSC no es válido según v150
        """
        if not self.validate_csc(csc):
            raise CSCValidationError(
                "CSC inválido según especificaciones SIFEN v150")

        self._csc_cache = csc
        self._last_validation = datetime.now()
        logger.info(
            f"CSC establecido correctamente (hash: {self._get_csc_hash(csc)[:8]})")

    def get_csc(self) -> Optional[str]:
        """
        Obtiene el CSC almacenado en memoria

        Returns:
            CSC de 9 dígitos si está disponible, None en caso contrario
        """
        return self._csc_cache

    def get_csc_from_environment(self, env_var: str = 'SIFEN_CSC') -> Optional[str]:
        """
        Obtiene CSC desde variables de entorno

        Args:
            env_var: Nombre de la variable de entorno

        Returns:
            CSC válido desde variable de entorno o None
        """
        csc = os.getenv(env_var)

        if csc and self.validate_csc(csc):
            logger.info(f"CSC obtenido desde variable de entorno {env_var}")
            return csc
        elif csc:
            logger.warning(
                f"CSC en variable {env_var} no es válido según v150")

        return None

    def get_or_generate_csc(self, prefer_env: bool = True) -> str:
        """
        Obtiene CSC existente o genera uno nuevo

        Orden de prioridad:
        1. CSC en memoria (cache)
        2. CSC desde variable de entorno (si prefer_env=True)
        3. Generar nuevo CSC

        Args:
            prefer_env: Si preferir CSC desde variable de entorno

        Returns:
            CSC válido de 9 dígitos
        """
        # 1. Verificar cache en memoria
        if self._csc_cache:
            logger.debug("CSC obtenido desde cache en memoria")
            return self._csc_cache

        # 2. Verificar variable de entorno
        if prefer_env:
            env_csc = self.get_csc_from_environment()
            if env_csc:
                self.set_csc(env_csc)  # Cachear en memoria
                return env_csc

        # 3. Generar nuevo CSC
        logger.info("Generando nuevo CSC")
        new_csc = self.generate_csc()
        self.set_csc(new_csc)
        return new_csc

    def clear_cache(self) -> None:
        """Limpia el cache interno del CSC"""
        self._csc_cache = None
        self._last_validation = None
        logger.info("Cache CSC limpiado")

    def validate_csc_for_certificate(self, csc: str) -> bool:
        """
        Valida CSC en contexto del certificado actual

        Args:
            csc: CSC de 9 dígitos a validar

        Returns:
            True si es válido para el certificado

        Raises:
            CSCValidationError: Si el certificado es inválido
        """
        # Validar formato básico según v150
        if not self.validate_csc(csc):
            return False

        # Obtener información del certificado
        try:
            cert_info = self.cert_manager.get_certificate_info()

            if not cert_info.get('is_valid', False):
                raise CSCValidationError(
                    "Certificado inválido para validación CSC")

            # Verificar que el certificado tenga RUC válido
            ruc_emisor = cert_info.get('ruc_emisor')
            if not ruc_emisor:
                raise CSCValidationError("Certificado sin RUC válido")

            logger.debug(f"CSC válido para certificado RUC: {ruc_emisor}")
            return True

        except Exception as e:
            if "Network error" in str(e) or "Connection" in str(e):
                raise CSCError("Error de conectividad durante validación CSC")
            raise

    def generate_csc_for_ruc(self, ruc: str) -> str:
        """
        Genera CSC específico basado en RUC (para reproducibilidad en testing)

        NOTA: Solo para ambiente de testing. En producción usar generate_csc()

        Args:
            ruc: RUC del emisor (8 dígitos)

        Returns:
            CSC de 9 dígitos basado en RUC
        """
        if not ruc or len(ruc) != 8 or not ruc.isdigit():
            raise ValueError("RUC debe ser exactamente 8 dígitos")

        # Usar RUC como seed para generar CSC reproducible (solo testing)
        import hashlib
        ruc_hash = hashlib.sha256(ruc.encode()).hexdigest()

        # Tomar primeros 9 caracteres numéricos del hash
        numeric_chars = ''.join(c for c in ruc_hash if c.isdigit())[:9]

        # Si no hay suficientes dígitos, completar con el RUC
        if len(numeric_chars) < 9:
            numeric_chars += (ruc * 2)[:9-len(numeric_chars)]

        csc = numeric_chars[:9]

        if not self.validate_csc(csc):
            raise CSCError("No se pudo generar CSC válido para el RUC")

        logger.info(
            f"CSC generado para RUC {ruc} (hash: {self._get_csc_hash(csc)[:8]})")
        return csc

    def format_csc_for_cdc(self, csc: str) -> str:
        """
        Formatea CSC para inclusión en CDC

        El CSC se incluye directamente en el CDC como 9 dígitos
        sin formateo adicional según especificaciones v150.

        Args:
            csc: CSC de 9 dígitos

        Returns:
            CSC formateado para CDC (mismo CSC, validado)
        """
        if not self.validate_csc(csc):
            raise CSCValidationError("CSC inválido para formateo CDC")

        return csc

    def format_csc_for_qr(self, csc: str) -> str:
        """
        Formatea CSC para parámetro IdCSC en código QR del KuDE

        Args:
            csc: CSC de 9 dígitos

        Returns:
            CSC formateado para código QR
        """
        if not self.validate_csc(csc):
            raise CSCValidationError("CSC inválido para código QR")

        # En el QR se usa directamente el CSC de 9 dígitos
        return csc

    def get_csc_metadata(self) -> Dict[str, Any]:
        """
        Obtiene metadatos del CSC actual

        Returns:
            Diccionario con metadatos del CSC
        """
        # Las reglas de validación siempre están disponibles
        validation_rules = {
            'length': 9,
            'format': 'numeric_only',
            'charset': '0123456789'
        }

        csc = self.get_csc()
        if not csc:
            return {
                'has_csc': False,
                'last_validation': None,
                'specification_version': '150',
                'validation_rules': validation_rules
            }

        return {
            'has_csc': True,
            'csc_length': len(csc),
            # Hash parcial por seguridad
            'csc_hash': self._get_csc_hash(csc)[:16],
            'last_validation': self._last_validation,
            'specification_version': '150',
            'validation_rules': validation_rules
        }

    def _get_csc_hash(self, csc: str) -> str:
        """
        Obtiene hash SHA256 del CSC para logging seguro

        Args:
            csc: CSC a hashear

        Returns:
            Hash SHA256 del CSC
        """
        return hashlib.sha256(csc.encode()).hexdigest()

    def _secure_compare_csc(self, csc1: str, csc2: str) -> bool:
        """
        Comparación segura de CSCs para evitar timing attacks

        Args:
            csc1: Primer CSC
            csc2: Segundo CSC

        Returns:
            True si son iguales
        """
        if not csc1 or not csc2:
            return False

        return hmac.compare_digest(csc1, csc2)

    def __str__(self) -> str:
        """Representación string del CSC Manager (sin exponer el CSC)"""
        has_csc = "Sí" if self._csc_cache else "No"
        return f"CSCManager(has_csc={has_csc}, spec_version=150)"

    def __repr__(self) -> str:
        """Representación detallada del CSC Manager"""
        return (f"CSCManager(certificate_manager={self.cert_manager}, "
                f"has_cached_csc={bool(self._csc_cache)}, "
                f"last_validation={self._last_validation})")
