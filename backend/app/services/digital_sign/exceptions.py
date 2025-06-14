"""
Excepciones personalizadas para el módulo de firma digital SIFEN v150

Este módulo define todas las excepciones específicas para el manejo de errores
en el proceso de firma digital según las especificaciones de SIFEN Paraguay.

CRÍTICO: Estas excepciones mapean directamente a los códigos de error de SIFEN
y permiten el manejo adecuado de errores en el flujo de facturación electrónica.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


# ========================================
# EXCEPCIÓN BASE
# ========================================

class DigitalSignError(Exception):
    """
    Excepción base para todos los errores del módulo de firma digital

    Esta clase base proporciona funcionalidad común para todas las excepciones
    específicas del módulo de firma digital.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Inicializa la excepción base

        Args:
            message: Mensaje descriptivo del error
            error_code: Código de error específico (si aplica)
            details: Detalles adicionales del error
            original_exception: Excepción original que causó este error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        """Representación en string de la excepción"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para logging/serialización"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'original_exception': str(self.original_exception) if self.original_exception else None
        }


# ========================================
# EXCEPCIONES DE CERTIFICADOS
# ========================================

class CertificateError(DigitalSignError):
    """
    Excepción para errores relacionados con certificados digitales

    Maneja todos los errores de carga, validación y uso de certificados PSC Paraguay.
    Mapea a códigos de error SIFEN 0141-0149.
    """

    def __init__(
        self,
        message: str,
        certificate_path: Optional[str] = None,
        certificate_serial: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)
        self.certificate_path = certificate_path
        self.certificate_serial = certificate_serial


class CertificateNotFoundError(CertificateError):
    """Excepción cuando no se encuentra el archivo de certificado"""

    def __init__(self, certificate_path: str, **kwargs):
        message = f"Archivo de certificado no encontrado: {certificate_path}"
        super().__init__(
            message=message,
            certificate_path=certificate_path,
            error_code="CERT_FILE_NOT_FOUND",
            **kwargs
        )


class CertificatePasswordError(CertificateError):
    """Excepción para errores de contraseña del certificado"""

    def __init__(self, certificate_path: str, **kwargs):
        message = f"Contraseña incorrecta para certificado: {certificate_path}"
        super().__init__(
            message=message,
            certificate_path=certificate_path,
            error_code="CERT_INVALID_PASSWORD",
            **kwargs
        )


class CertificateExpiredError(CertificateError):
    """
    Excepción para certificados vencidos

    CRÍTICO: SIFEN rechaza documentos con certificados vencidos (código 0142)
    """

    def __init__(
        self,
        certificate_serial: str,
        expiry_date: datetime,
        **kwargs
    ):
        message = f"Certificado vencido (serial: {certificate_serial}, expiró: {expiry_date})"
        super().__init__(
            message=message,
            certificate_serial=certificate_serial,
            error_code="0142",  # Código SIFEN para certificado vencido
            details={'expiry_date': expiry_date.isoformat()},
            **kwargs
        )


class CertificateNotValidYetError(CertificateError):
    """Excepción para certificados que aún no son válidos"""

    def __init__(
        self,
        certificate_serial: str,
        valid_from: datetime,
        **kwargs
    ):
        message = f"Certificado no válido aún (serial: {certificate_serial}, válido desde: {valid_from})"
        super().__init__(
            message=message,
            certificate_serial=certificate_serial,
            error_code="CERT_NOT_VALID_YET",
            details={'valid_from': valid_from.isoformat()},
            **kwargs
        )


class CertificateRevokedError(CertificateError):
    """
    Excepción para certificados revocados

    CRÍTICO: SIFEN rechaza documentos con certificados revocados (código 0143)
    """

    def __init__(self, certificate_serial: str, **kwargs):
        message = f"Certificado revocado (serial: {certificate_serial})"
        super().__init__(
            message=message,
            certificate_serial=certificate_serial,
            error_code="0143",  # Código SIFEN para certificado revocado
            **kwargs
        )


class CertificateNotAuthorizedError(CertificateError):
    """
    Excepción para certificados sin permisos de firma

    CRÍTICO: Certificado debe tener KeyUsage con digital_signature habilitado
    """

    def __init__(self, certificate_serial: str, **kwargs):
        message = f"Certificado no autorizado para firma digital (serial: {certificate_serial})"
        super().__init__(
            message=message,
            certificate_serial=certificate_serial,
            error_code="0144",  # Código SIFEN para certificado no autorizado
            **kwargs
        )


class InvalidPSCCertificateError(CertificateError):
    """
    Excepción para certificados que no son de PSC Paraguay

    CRÍTICO: SIFEN solo acepta certificados emitidos por PSC Paraguay
    """

    def __init__(self, certificate_serial: str, issuer: str, **kwargs):
        message = f"Certificado no es de PSC Paraguay (serial: {certificate_serial}, emisor: {issuer})"
        super().__init__(
            message=message,
            certificate_serial=certificate_serial,
            error_code="CERT_NOT_PSC",
            details={'issuer': issuer},
            **kwargs
        )


# ========================================
# EXCEPCIONES DE FIRMA DIGITAL
# ========================================

class SignatureValidationError(DigitalSignError):
    """
    Excepción para errores de validación de firma digital

    Maneja errores en el proceso de firma y verificación de documentos XML.
    Mapea principalmente al código SIFEN 0141.
    """

    def __init__(
        self,
        message: str,
        xml_content: Optional[str] = None,
        signature_algorithm: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.xml_content = xml_content
        self.signature_algorithm = signature_algorithm


class InvalidSignatureError(SignatureValidationError):
    """
    Excepción para firmas digitales inválidas

    CRÍTICO: Mapea al código SIFEN 0141 - Firma digital no válida
    """

    def __init__(self, signature_value: Optional[str] = None, **kwargs):
        message = "La firma digital no es válida"
        super().__init__(
            message=message,
            error_code="0141",  # Código SIFEN para firma inválida
            details={
                'signature_value': signature_value} if signature_value else None,
            **kwargs
        )


class SignatureVerificationError(SignatureValidationError):
    """
    Excepción para errores en verificación de firma

    CRÍTICO: Mapea al código SIFEN 0145 - Error en verificación de firma
    """

    def __init__(self, verification_details: Optional[str] = None, **kwargs):
        message = f"Error en la verificación de la firma digital: {verification_details or 'Detalles no disponibles'}"
        super().__init__(
            message=message,
            error_code="0145",  # Código SIFEN para error de verificación
            **kwargs
        )


class XMLSignatureFormatError(SignatureValidationError):
    """Excepción para errores de formato en la firma XML"""

    def __init__(self, format_issue: str, **kwargs):
        message = f"Formato de firma XML inválido: {format_issue}"
        super().__init__(
            message=message,
            error_code="XML_SIGNATURE_FORMAT_ERROR",
            **kwargs
        )


# ========================================
# EXCEPCIONES DE XML
# ========================================

class XMLProcessingError(DigitalSignError):
    """Excepción base para errores de procesamiento XML"""

    def __init__(
        self,
        message: str,
        xml_content: Optional[str] = None,
        line_number: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.xml_content = xml_content
        self.line_number = line_number


class InvalidXMLError(XMLProcessingError):
    """Excepción para XML malformado o inválido"""

    def __init__(self, xml_error: str, **kwargs):
        message = f"XML malformado: {xml_error}"
        super().__init__(
            message=message,
            error_code="INVALID_XML",
            **kwargs
        )


class MissingSifenNamespaceError(XMLProcessingError):
    """
    Excepción para XML sin namespace SIFEN

    CRÍTICO: SIFEN requiere namespace exacto para validación
    """

    def __init__(self, **kwargs):
        message = "XML debe contener el namespace SIFEN: http://ekuatia.set.gov.py/sifen/xsd"
        super().__init__(
            message=message,
            error_code="MISSING_SIFEN_NAMESPACE",
            **kwargs
        )


class InvalidCDCError(XMLProcessingError):
    """
    Excepción para CDC (Código de Control) inválido

    CRÍTICO: CDC debe tener exactamente 44 caracteres y formato específico
    """

    def __init__(self, cdc: str, **kwargs):
        message = f"CDC inválido: {cdc} (debe tener 44 caracteres y formato específico)"
        super().__init__(
            message=message,
            error_code="INVALID_CDC",
            details={'provided_cdc': cdc},
            **kwargs
        )


# ========================================
# EXCEPCIONES DE CONFIGURACIÓN
# ========================================

class ConfigurationError(DigitalSignError):
    """Excepción para errores de configuración del módulo"""

    def __init__(self, config_field: str, issue: str, **kwargs):
        message = f"Error de configuración en {config_field}: {issue}"
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={'config_field': config_field, 'issue': issue},
            **kwargs
        )


class MissingConfigurationError(ConfigurationError):
    """Excepción para configuración faltante"""

    def __init__(self, missing_fields: List[str], **kwargs):
        fields_str = ", ".join(missing_fields)
        super().__init__(
            config_field="multiple",
            issue=f"Campos requeridos faltantes: {fields_str}",
            **kwargs
        )


# ========================================
# EXCEPCIONES DE ALGORITMOS
# ========================================

class UnsupportedAlgorithmError(DigitalSignError):
    """
    Excepción para algoritmos no soportados

    CRÍTICO: SIFEN requiere algoritmos específicos (RSA-SHA256)
    """

    def __init__(self, algorithm: str, supported_algorithms: List[str], **kwargs):
        supported_str = ", ".join(supported_algorithms)
        message = f"Algoritmo no soportado: {algorithm}. Soportados: {supported_str}"
        super().__init__(
            message=message,
            error_code="UNSUPPORTED_ALGORITHM",
            details={
                'requested_algorithm': algorithm,
                'supported_algorithms': supported_algorithms
            },
            **kwargs
        )


# ========================================
# FUNCIONES HELPER
# ========================================

def map_sifen_error_code_to_exception(
    error_code: str,
    message: str,
    **kwargs
) -> DigitalSignError:
    """
    Mapea códigos de error SIFEN a excepciones específicas

    Args:
        error_code: Código de error de SIFEN
        message: Mensaje de error
        **kwargs: Argumentos adicionales para la excepción

    Returns:
        Instancia de la excepción apropiada
    """
    error_mapping = {
        "0141": InvalidSignatureError,
        "0142": CertificateExpiredError,
        "0143": CertificateRevokedError,
        "0144": CertificateNotAuthorizedError,
        "0145": SignatureVerificationError,
    }

    exception_class = error_mapping.get(error_code, DigitalSignError)

    # Ajustar argumentos según el tipo de excepción
    if error_code in ["0142", "0143", "0144"] and 'certificate_serial' not in kwargs:
        kwargs['certificate_serial'] = "unknown"

    if error_code == "0142" and 'expiry_date' not in kwargs:
        kwargs['expiry_date'] = datetime.now()

    return exception_class(message=message, error_code=error_code, **kwargs)


def create_certificate_error(
    error_type: str,
    certificate_path: Optional[str] = None,
    certificate_serial: Optional[str] = None,
    **kwargs
) -> CertificateError:
    """
    Factory function para crear errores de certificado

    Args:
        error_type: Tipo de error (not_found, invalid_password, expired, etc.)
        certificate_path: Ruta del certificado
        certificate_serial: Serial del certificado
        **kwargs: Argumentos adicionales

    Returns:
        Instancia de la excepción de certificado apropiada
    """
    error_classes = {
        'not_found': CertificateNotFoundError,
        'invalid_password': CertificatePasswordError,
        'expired': CertificateExpiredError,
        'not_valid_yet': CertificateNotValidYetError,
        'revoked': CertificateRevokedError,
        'not_authorized': CertificateNotAuthorizedError,
        'not_psc': InvalidPSCCertificateError,
    }

    exception_class = error_classes.get(error_type, CertificateError)

    # Preparar argumentos según el tipo de excepción
    init_kwargs = kwargs.copy()
    if certificate_path:
        init_kwargs['certificate_path'] = certificate_path
    if certificate_serial:
        init_kwargs['certificate_serial'] = certificate_serial

    # Casos especiales que requieren argumentos específicos
    if error_type == 'not_found' and certificate_path:
        return CertificateNotFoundError(certificate_path, **kwargs)
    elif error_type == 'invalid_password' and certificate_path:
        return CertificatePasswordError(certificate_path, **kwargs)
    elif error_type == 'expired' and certificate_serial:
        expiry_date = kwargs.get('expiry_date', datetime.now())
        return CertificateExpiredError(certificate_serial, expiry_date, **kwargs)
    elif error_type == 'not_valid_yet' and certificate_serial:
        valid_from = kwargs.get('valid_from', datetime.now())
        return CertificateNotValidYetError(certificate_serial, valid_from, **kwargs)
    elif error_type == 'revoked' and certificate_serial:
        return CertificateRevokedError(certificate_serial, **kwargs)
    elif error_type == 'not_authorized' and certificate_serial:
        return CertificateNotAuthorizedError(certificate_serial, **kwargs)
    elif error_type == 'not_psc' and certificate_serial:
        issuer = kwargs.get('issuer', 'Unknown')
        return InvalidPSCCertificateError(certificate_serial, issuer, **kwargs)
    else:
        # Fallback a CertificateError genérico
        message = kwargs.get('message', f"Error de certificado: {error_type}")
        return CertificateError(
            message=message,
            certificate_path=certificate_path,
            certificate_serial=certificate_serial,
            **kwargs
        )


# ========================================
# CONSTANTES
# ========================================

# Códigos de error SIFEN relacionados con firma digital
SIFEN_SIGNATURE_ERROR_CODES = {
    "0141": "La firma digital no es válida",
    "0142": "El certificado digital está vencido",
    "0143": "El certificado digital está revocado",
    "0144": "El certificado no está autorizado para firmar",
    "0145": "Error en la verificación de la firma digital",
}

# Algoritmos soportados por SIFEN
SUPPORTED_SIGNATURE_ALGORITHMS = [
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    "RSA-SHA256"
]

SUPPORTED_DIGEST_ALGORITHMS = [
    "http://www.w3.org/2001/04/xmlenc#sha256",
    "SHA256"
]

SUPPORTED_CANONICALIZATION_METHODS = [
    "http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    "http://www.w3.org/2001/10/xml-exc-c14n#"
]
