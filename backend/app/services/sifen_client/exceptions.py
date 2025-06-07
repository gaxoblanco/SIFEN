"""
Excepciones personalizadas para el módulo SIFEN Client

Define una jerarquía clara de errores específicos para la integración
con SIFEN Paraguay, permitiendo manejo granular de diferentes tipos
de fallos que pueden ocurrir durante la comunicación.

Jerarquía de Excepciones:
    SifenClientError (base)
    ├── SifenConnectionError (problemas de red/conectividad)
    ├── SifenValidationError (datos inválidos)
    ├── SifenAuthenticationError (problemas de autenticación/certificados)
    ├── SifenServerError (errores del servidor SIFEN)
    ├── SifenTimeoutError (timeouts específicos)
    ├── SifenRetryExhaustedError (reintentos agotados)
    └── SifenParsingError (errores al parsear respuestas)

Basado en:
- Manual Técnico SIFEN v150 (códigos de error oficiales)
- Best practices para manejo de errores en clients HTTP/SOAP
- Patrones de error handling según .cursorrules
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


class SifenClientError(Exception):
    """
    Excepción base para todos los errores del cliente SIFEN

    Proporciona estructura común para todos los errores del módulo,
    incluyendo código de error, contexto y timestamp.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Inicializa excepción base

        Args:
            message: Mensaje descriptivo del error
            error_code: Código de error específico (ej: códigos SIFEN)
            details: Información adicional del contexto del error
            original_exception: Excepción original que causó este error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()

        # Agregar información del contexto
        self.details.update({
            'error_type': self.__class__.__name__,
            'timestamp': self.timestamp.isoformat(),
            'has_original_exception': original_exception is not None
        })

    def __str__(self) -> str:
        """Representación string del error"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def __repr__(self) -> str:
        """Representación detallada del error"""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"details={self.details})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la excepción a diccionario para logging/serialización

        Returns:
            Dict con toda la información del error
        """
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'original_exception': str(self.original_exception) if self.original_exception else None
        }


class SifenConnectionError(SifenClientError):
    """
    Error de conexión con SIFEN

    Se lanza cuando hay problemas de conectividad de red, DNS,
    SSL/TLS o timeouts de conexión.

    Ejemplos:
    - No se puede resolver el hostname de SIFEN
    - Timeout al establecer conexión TCP
    - Error de handshake SSL/TLS
    - Conexión rechazada por el servidor
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs
    ):
        """
        Inicializa error de conexión

        Args:
            message: Descripción del error de conexión
            url: URL que falló al conectar
            timeout: Timeout configurado cuando falló
            **kwargs: Argumentos adicionales para SifenClientError
        """
        # Agregar contexto específico de conexión
        details = kwargs.get('details', {})
        details.update({
            'url': url,
            'timeout': timeout,
            'connection_type': 'SOAP over HTTPS'
        })
        kwargs['details'] = details

        super().__init__(message, **kwargs)


class SifenValidationError(SifenClientError):
    """
    Error de validación de datos

    Se lanza cuando los datos enviados a SIFEN no cumplen con
    las validaciones requeridas según el Manual Técnico v150.

    Ejemplos:
    - XML mal formado o inválido contra XSD
    - CDC con formato incorrecto
    - RUC inexistente o inválido
    - Certificado digital inválido o expirado
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Inicializa error de validación

        Args:
            message: Descripción del error de validación
            field: Campo específico que falló la validación
            value: Valor que causó el error (será enmascarado si es sensible)
            validation_errors: Lista de errores de validación específicos
            **kwargs: Argumentos adicionales para SifenClientError
        """
        # Agregar contexto específico de validación
        details = kwargs.get('details', {})
        details.update({
            'field': field,
            'value': self._mask_sensitive_value(field, value),
            'validation_errors': validation_errors or [],
            'validation_type': 'SIFEN_Schema'
        })
        kwargs['details'] = details

        super().__init__(message, **kwargs)

    @staticmethod
    def _mask_sensitive_value(field: Optional[str], value: Optional[str]) -> Optional[str]:
        """
        Enmascara valores sensibles para logging seguro

        Args:
            field: Nombre del campo
            value: Valor a enmascarar

        Returns:
            Valor enmascarado si es sensible, original si no
        """
        if not field or not value:
            return value

        # Campos que contienen información sensible
        sensitive_fields = {
            'ruc', 'documento', 'certificado', 'serial',
            'password', 'key', 'signature', 'token'
        }

        if any(sensitive in field.lower() for sensitive in sensitive_fields):
            if len(value) > 4:
                return f"{value[:2]}***{value[-2:]}"
            else:
                return "***"

        return value


class SifenAuthenticationError(SifenClientError):
    """
    Error de autenticación/autorización con SIFEN

    Se lanza cuando hay problemas con certificados digitales,
    firmas inválidas o credenciales incorrectas.

    Ejemplos:
    - Certificado digital expirado
    - Firma digital inválida
    - RUC no autorizado para emisión
    - Certificado revocado o suspendido
    """

    def __init__(
        self,
        message: str,
        certificate_info: Optional[Dict[str, Any]] = None,
        auth_type: str = "digital_certificate",
        **kwargs
    ):
        """
        Inicializa error de autenticación

        Args:
            message: Descripción del error de autenticación
            certificate_info: Información del certificado (será enmascarada)
            auth_type: Tipo de autenticación que falló
            **kwargs: Argumentos adicionales para SifenClientError
        """
        # Agregar contexto específico de autenticación
        details = kwargs.get('details', {})
        details.update({
            'auth_type': auth_type,
            'certificate_info': self._mask_certificate_info(certificate_info),
            'requires_certificate_renewal': 'expirado' in message.lower() or 'expired' in message.lower()
        })
        kwargs['details'] = details

        super().__init__(message, **kwargs)

    @staticmethod
    def _mask_certificate_info(cert_info: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Enmascara información sensible del certificado

        Args:
            cert_info: Información del certificado

        Returns:
            Información del certificado con datos sensibles enmascarados
        """
        if not cert_info:
            return None

        masked = cert_info.copy()

        # Enmascarar campos sensibles
        sensitive_keys = ['serial_number', 'private_key', 'certificate_data']
        for key in sensitive_keys:
            if key in masked and masked[key]:
                value = str(masked[key])
                if len(value) > 8:
                    masked[key] = f"{value[:4]}***{value[-4:]}"
                else:
                    masked[key] = "***"

        return masked


class SifenServerError(SifenClientError):
    """
    Error del servidor SIFEN

    Se lanza cuando SIFEN retorna errores 5xx o códigos de error
    específicos que indican problemas del lado del servidor.

    Ejemplos:
    - Error 500 Internal Server Error
    - Servicio SIFEN temporalmente no disponible
    - Error en procesamiento interno de SIFEN
    - Mantenimiento programado
    """

    def __init__(
        self,
        message: str,
        http_status: Optional[int] = None,
        sifen_code: Optional[str] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        """
        Inicializa error del servidor

        Args:
            message: Descripción del error del servidor
            http_status: Código de estado HTTP (500, 502, 503, etc.)
            sifen_code: Código específico de error SIFEN
            retry_after: Segundos sugeridos antes de reintentar
            **kwargs: Argumentos adicionales para SifenClientError
        """
        # Agregar contexto específico del servidor
        details = kwargs.get('details', {})
        details.update({
            'http_status': http_status,
            'sifen_code': sifen_code,
            'retry_after': retry_after,
            'is_temporary': http_status in [502, 503, 504] if http_status else False,
            'server_type': 'SIFEN_Paraguay'
        })
        kwargs['details'] = details
        kwargs['error_code'] = sifen_code or str(
            http_status) if http_status else None

        super().__init__(message, **kwargs)


class SifenTimeoutError(SifenClientError):
    """
    Error de timeout específico

    Se lanza cuando las operaciones exceden los timeouts configurados.
    Diferencia entre timeouts de conexión, lectura y operación total.

    Ejemplos:
    - Timeout al establecer conexión
    - Timeout al leer respuesta
    - Timeout total de operación
    """

    def __init__(
        self,
        message: str,
        timeout_type: str,
        timeout_value: int,
        elapsed_time: Optional[float] = None,
        **kwargs
    ):
        """
        Inicializa error de timeout

        Args:
            message: Descripción del timeout
            timeout_type: Tipo de timeout (connection, read, total)
            timeout_value: Valor del timeout configurado (segundos)
            elapsed_time: Tiempo transcurrido antes del timeout
            **kwargs: Argumentos adicionales para SifenClientError
        """
        # Agregar contexto específico de timeout
        details = kwargs.get('details', {})
        details.update({
            'timeout_type': timeout_type,
            'timeout_value': timeout_value,
            'elapsed_time': elapsed_time,
            'timeout_ratio': elapsed_time / timeout_value if elapsed_time else None,
            'is_retryable': True
        })
        kwargs['details'] = details

        super().__init__(message, **kwargs)


class SifenRetryExhaustedError(SifenClientError):
    """
    Error cuando se agotaron todos los reintentos

    Se lanza cuando una operación falla repetidamente y se
    agotaron todos los reintentos configurados.

    Incluye historial de todos los intentos fallidos.
    """

    def __init__(
        self,
        message: str,
        max_retries: int,
        retry_history: List[Dict[str, Any]],
        last_exception: Optional[Exception] = None,
        **kwargs
    ):
        """
        Inicializa error de reintentos agotados

        Args:
            message: Descripción del error
            max_retries: Número máximo de reintentos configurado
            retry_history: Historial de todos los intentos
            last_exception: Última excepción que causó el fallo
            **kwargs: Argumentos adicionales para SifenClientError
        """
        # Agregar contexto específico de reintentos
        details = kwargs.get('details', {})
        details.update({
            'max_retries': max_retries,
            'actual_attempts': len(retry_history),
            'retry_history': retry_history,
            'total_elapsed_time': sum(
                attempt.get('elapsed_time', 0) for attempt in retry_history
            ),
            'most_common_error': self._get_most_common_error(retry_history)
        })
        kwargs['details'] = details
        kwargs['original_exception'] = last_exception

        super().__init__(message, **kwargs)

    @staticmethod
    def _get_most_common_error(retry_history: List[Dict[str, Any]]) -> Optional[str]:
        """
        Obtiene el tipo de error más común en el historial de reintentos

        Args:
            retry_history: Historial de intentos fallidos

        Returns:
            Tipo de error más común
        """
        if not retry_history:
            return None

        error_counts: Dict[str, int] = {}
        for attempt in retry_history:
            error_type = attempt.get('error_type', 'unknown')
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        if not error_counts:
            return None

        # Encontrar el error con mayor conteo
        most_common_error = None
        max_count = 0
        for error_type, count in error_counts.items():
            if count > max_count:
                max_count = count
                most_common_error = error_type

        return most_common_error


class SifenParsingError(SifenClientError):
    """
    Error al parsear respuestas de SIFEN

    Se lanza cuando no se puede parsear correctamente la respuesta
    XML de SIFEN o cuando la estructura no es la esperada.

    Ejemplos:
    - XML malformado en respuesta
    - Estructura XML no esperada
    - Encoding incorrecto
    - Campos obligatorios faltantes
    """

    def __init__(
        self,
        message: str,
        xml_content: Optional[str] = None,
        parsing_stage: str = "unknown",
        expected_structure: Optional[str] = None,
        **kwargs
    ):
        """
        Inicializa error de parsing

        Args:
            message: Descripción del error de parsing
            xml_content: Contenido XML que falló (será truncado para logs)
            parsing_stage: Etapa donde falló el parsing
            expected_structure: Estructura esperada vs encontrada
            **kwargs: Argumentos adicionales para SifenClientError
        """
        # Agregar contexto específico de parsing
        details = kwargs.get('details', {})
        details.update({
            'parsing_stage': parsing_stage,
            'expected_structure': expected_structure,
            'xml_preview': self._get_safe_xml_preview(xml_content),
            'xml_length': len(xml_content) if xml_content else 0,
            'is_xml_empty': not xml_content or xml_content.strip() == ""
        })
        kwargs['details'] = details

        super().__init__(message, **kwargs)

    @staticmethod
    def _get_safe_xml_preview(xml_content: Optional[str], max_length: int = 200) -> Optional[str]:
        """
        Obtiene preview seguro del XML para logging

        Args:
            xml_content: Contenido XML completo
            max_length: Longitud máxima del preview

        Returns:
            Preview del XML sin datos sensibles
        """
        if not xml_content:
            return None

        # Truncar y limpiar contenido sensible
        preview = xml_content[:max_length]

        # Enmascarar posibles datos sensibles en el preview
        sensitive_patterns = [
            ('ruc="[0-9-]+"', 'ruc="***"'),
            ('<dNumID>[0-9-]+</dNumID>', '<dNumID>***</dNumID>'),
            ('<SignatureValue>.*?</SignatureValue>',
             '<SignatureValue>***</SignatureValue>'),
            ('<X509Certificate>.*?</X509Certificate>',
             '<X509Certificate>***</X509Certificate>')
        ]

        for pattern, replacement in sensitive_patterns:
            import re
            preview = re.sub(pattern, replacement, preview,
                             flags=re.IGNORECASE | re.DOTALL)

        if len(xml_content) > max_length:
            preview += "...[truncated]"

        return preview


# ========================================
# FUNCIONES HELPER PARA MANEJO DE ERRORES
# ========================================

def create_sifen_error_from_response(
    response_data: Dict[str, Any],
    original_exception: Optional[Exception] = None
) -> SifenClientError:
    """
    Crea la excepción apropiada basada en los datos de respuesta de SIFEN

    Args:
        response_data: Datos de respuesta de SIFEN
        original_exception: Excepción original si existe

    Returns:
        Instancia de la excepción SIFEN apropiada
    """
    # Extraer información común
    message = response_data.get('message', 'Error desconocido de SIFEN')
    error_code = response_data.get('code')
    http_status = response_data.get('http_status')

    # Determinar tipo de error basado en código/contexto
    if error_code:
        # Errores de validación (códigos 1000-4999)
        if error_code.startswith(('1', '2', '3', '4')):
            return SifenValidationError(
                message=message,
                error_code=error_code,
                details=response_data,
                original_exception=original_exception
            )

        # Errores de autenticación (códigos específicos)
        # Firma inválida, RUC inexistente, etc.
        auth_codes = ['0141', '1250', '0142']
        if error_code in auth_codes:
            return SifenAuthenticationError(
                message=message,
                error_code=error_code,
                details=response_data,
                original_exception=original_exception
            )

    # Errores HTTP 5xx
    if http_status and 500 <= http_status < 600:
        return SifenServerError(
            message=message,
            http_status=http_status,
            sifen_code=error_code,
            details=response_data,
            original_exception=original_exception
        )

    # Error genérico si no se puede determinar el tipo específico
    return SifenClientError(
        message=message,
        error_code=error_code,
        details=response_data,
        original_exception=original_exception
    )


def is_retryable_error(exception: Exception) -> bool:
    """
    Determina si un error es recuperable mediante reintentos

    Args:
        exception: Excepción a evaluar

    Returns:
        True si el error es retryable, False si no
    """
    # Errores siempre retryables
    retryable_types = (
        SifenConnectionError,
        SifenTimeoutError,
        SifenServerError
    )

    if isinstance(exception, retryable_types):
        return True

    # Errores específicos retryables
    if isinstance(exception, SifenClientError):
        # Verificar si es un error temporal del servidor
        if exception.details.get('is_temporary'):
            return True

        # Códigos HTTP retryables
        http_status = exception.details.get('http_status')
        if http_status in [429, 502, 503, 504, 408]:
            return True

    return False
