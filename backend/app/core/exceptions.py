"""
Excepciones personalizadas para el sistema SIFEN.

Este módulo define todas las excepciones específicas del dominio de la aplicación,
incluyendo errores de SIFEN, validación, base de datos y lógica de negocio.

Jerarquía de excepciones:
- SifenBaseException (base)
  ├── SifenValidationError
  ├── SifenDatabaseError
  ├── SifenAuthenticationError
  ├── SifenAuthorizationError
  ├── SifenBusinessLogicError
  ├── SifenExternalServiceError
  │   ├── SifenAPIError
  │   ├── SifenXMLError
  │   └── SifenCertificateError
  └── SifenConfigurationError

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# === EXCEPCIONES BASE ===


class SifenBaseException(Exception):
    """
    Excepción base para todas las excepciones del sistema SIFEN.

    Todas las excepciones personalizadas deben heredar de esta clase.
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Inicializa excepción base.

        Args:
            message: Mensaje descriptivo del error
            code: Código de error específico
            details: Detalles adicionales del error
            original_exception: Excepción original que causó este error
        """
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.original_exception = original_exception

        super().__init__(self.message)

        # Log automático de la excepción
        logger.error(
            f"{self.__class__.__name__}: {message}",
            exc_info=original_exception is not None,
            extra={
                "error_code": self.code,
                "error_details": self.details
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la excepción a diccionario para serialización.

        Returns:
            dict: Representación de la excepción
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
            "original_error": str(self.original_exception) if self.original_exception else None
        }

    def to_http_exception(self, status_code: int = status.HTTP_400_BAD_REQUEST) -> HTTPException:
        """
        Convierte a HTTPException para FastAPI.

        Args:
            status_code: Código HTTP de respuesta

        Returns:
            HTTPException: Excepción HTTP para FastAPI
        """
        return HTTPException(
            status_code=status_code,
            detail=self.to_dict()
        )

# === EXCEPCIONES DE VALIDACIÓN ===


class SifenValidationError(SifenBaseException):
    """Errores de validación de datos."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        """
        Error de validación.

        Args:
            message: Mensaje del error
            field: Campo que falló la validación
            value: Valor que falló la validación
            validation_errors: Lista de errores de validación detallados
        """
        details = {
            "field": field,
            "value": str(value) if value is not None else None,
            "validation_errors": validation_errors or []
        }
        super().__init__(message, details=details, **kwargs)

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 422 Unprocessable Entity."""
        return super().to_http_exception(status.HTTP_422_UNPROCESSABLE_ENTITY)


class SifenRUCValidationError(SifenValidationError):
    """Error específico de validación de RUC paraguayo."""

    def __init__(self, ruc: str, reason: str, **kwargs):
        super().__init__(
            f"RUC inválido: {ruc}. {reason}",
            field="ruc",
            value=ruc,
            **kwargs
        )


class SifenCDCValidationError(SifenValidationError):
    """Error específico de validación de CDC (Código de Control)."""

    def __init__(self, cdc: str, reason: str, **kwargs):
        super().__init__(
            f"CDC inválido: {cdc}. {reason}",
            field="cdc",
            value=cdc,
            **kwargs
        )

# === EXCEPCIONES DE BASE DE DATOS ===


class SifenDatabaseError(SifenBaseException):
    """Errores relacionados con operaciones de base de datos."""

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        """
        Error de base de datos.

        Args:
            message: Mensaje del error
            operation: Operación que falló (SELECT, INSERT, UPDATE, DELETE)
        """
        details = {"operation": operation}
        super().__init__(message, details=details, **kwargs)

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 500 Internal Server Error."""
        return super().to_http_exception(status.HTTP_500_INTERNAL_SERVER_ERROR)


class SifenEntityNotFoundError(SifenDatabaseError):
    """Entidad no encontrada en base de datos."""

    def __init__(self, entity_type: str, entity_id: Union[int, str], **kwargs):
        super().__init__(
            f"{entity_type} con ID {entity_id} no encontrado",
            operation="SELECT",
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
            **kwargs
        )

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 404 Not Found."""
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=self.to_dict()
        )


class SifenDuplicateEntityError(SifenDatabaseError):
    """Entidad duplicada en base de datos."""

    def __init__(self, entity_type: str, field: str, value: Any, **kwargs):
        super().__init__(
            f"{entity_type} con {field}='{value}' ya existe",
            operation="INSERT",
            details={"entity_type": entity_type,
                     "field": field, "value": str(value)},
            **kwargs
        )

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 409 Conflict."""
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=self.to_dict()
        )

# === EXCEPCIONES DE AUTENTICACIÓN Y AUTORIZACIÓN ===


class SifenAuthenticationError(SifenBaseException):
    """Errores de autenticación."""

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 401 Unauthorized."""
        return super().to_http_exception(status.HTTP_401_UNAUTHORIZED)


class SifenAuthorizationError(SifenBaseException):
    """Errores de autorización (permisos insuficientes)."""

    def __init__(
        self,
        message: str,
        required_permission: Optional[str] = None,
        user_permissions: Optional[List[str]] = None,
        **kwargs
    ):
        details = {
            "required_permission": required_permission,
            "user_permissions": user_permissions or []
        }
        super().__init__(message, details=details, **kwargs)

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 403 Forbidden."""
        return super().to_http_exception(status.HTTP_403_FORBIDDEN)


class SifenInvalidTokenError(SifenAuthenticationError):
    """Token JWT inválido o expirado."""

    def __init__(self, reason: str = "Token inválido", **kwargs):
        super().__init__(
            f"Token de autenticación inválido: {reason}", **kwargs)


class SifenTokenExpiredError(SifenAuthenticationError):
    """Token JWT expirado."""

    def __init__(self, **kwargs):
        super().__init__("Token de autenticación expirado", **kwargs)

# === EXCEPCIONES DE LÓGICA DE NEGOCIO ===


class SifenBusinessLogicError(SifenBaseException):
    """Errores de lógica de negocio específicos del dominio."""

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 422 Unprocessable Entity."""
        return super().to_http_exception(status.HTTP_422_UNPROCESSABLE_ENTITY)


class SifenDocumentStateError(SifenBusinessLogicError):
    """Error de estado de documento (ej: intentar modificar documento aprobado)."""

    def __init__(
        self,
        document_type: str,
        document_id: Union[int, str],
        current_state: str,
        required_state: str,
        **kwargs
    ):
        super().__init__(
            f"{document_type} {document_id} en estado '{current_state}' "
            f"no puede realizar operación que requiere estado '{required_state}'",
            details={
                "document_type": document_type,
                "document_id": str(document_id),
                "current_state": current_state,
                "required_state": required_state
            },
            **kwargs
        )


class SifenTimbradoError(SifenBusinessLogicError):
    """Errores relacionados con timbrados."""

    def __init__(self, timbrado: str, reason: str, **kwargs):
        super().__init__(
            f"Error en timbrado {timbrado}: {reason}",
            details={"timbrado": timbrado, "reason": reason},
            **kwargs
        )


class SifenNumerationError(SifenBusinessLogicError):
    """Errores de numeración de documentos."""

    def __init__(self, document_type: str, expected_number: int, **kwargs):
        super().__init__(
            f"Error de numeración en {document_type}. Número esperado: {expected_number}",
            details={"document_type": document_type,
                     "expected_number": expected_number},
            **kwargs
        )

# === EXCEPCIONES DE SERVICIOS EXTERNOS ===


class SifenExternalServiceError(SifenBaseException):
    """Errores de servicios externos (base)."""

    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs
    ):
        details = {
            "service_name": service_name,
            "status_code": status_code,
            "response_body": response_body
        }
        super().__init__(message, details=details, **kwargs)

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 502 Bad Gateway."""
        return super().to_http_exception(status.HTTP_502_BAD_GATEWAY)


class SifenAPIError(SifenExternalServiceError):
    """Errores específicos de la API de SIFEN."""

    def __init__(
        self,
        message: str,
        endpoint: str,
        sifen_error_code: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({
            "endpoint": endpoint,
            "sifen_error_code": sifen_error_code
        })
        kwargs["details"] = details

        super().__init__(
            message,
            service_name="SIFEN API",
            **kwargs
        )


class SifenXMLError(SifenExternalServiceError):
    """Errores de generación o validación de XML."""

    def __init__(self, message: str, xml_type: str, validation_errors: Optional[List[str]] = None, **kwargs):
        details = {
            "xml_type": xml_type,
            "validation_errors": validation_errors or []
        }
        super().__init__(
            message,
            service_name="XML Generator",
            details=details,
            **kwargs
        )


class SifenCertificateError(SifenExternalServiceError):
    """Errores de certificados digitales."""

    def __init__(
        self,
        message: str,
        certificate_path: Optional[str] = None,
        certificate_type: Optional[str] = None,
        **kwargs
    ):
        details = {
            "certificate_path": certificate_path,
            "certificate_type": certificate_type
        }
        super().__init__(
            message,
            service_name="Digital Certificate",
            details=details,
            **kwargs
        )


class SifenSignatureError(SifenExternalServiceError):
    """Errores de firma digital."""

    def __init__(self, message: str, document_id: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            service_name="Digital Signature",
            details={"document_id": document_id},
            **kwargs
        )

# === EXCEPCIONES DE CONFIGURACIÓN ===


class SifenConfigurationError(SifenBaseException):
    """Errores de configuración de la aplicación."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        details = {
            "config_key": config_key,
            "config_value": str(config_value) if config_value is not None else None
        }
        super().__init__(message, details=details, **kwargs)

    def to_http_exception(self) -> HTTPException:
        """Convierte a HTTP 500 Internal Server Error."""
        return super().to_http_exception(status.HTTP_500_INTERNAL_SERVER_ERROR)


class SifenEnvironmentError(SifenConfigurationError):
    """Errores de configuración de ambiente."""

    def __init__(self, env_var: str, **kwargs):
        super().__init__(
            f"Variable de entorno requerida no configurada: {env_var}",
            config_key=env_var,
            **kwargs
        )

# === UTILIDADES DE MANEJO DE EXCEPCIONES ===


def handle_database_exception(exc: Exception, operation: str = "database") -> SifenDatabaseError:
    """
    Convierte excepciones de SQLAlchemy en excepciones SIFEN.

    Args:
        exc: Excepción original
        operation: Tipo de operación que falló

    Returns:
        SifenDatabaseError: Excepción SIFEN apropiada
    """
    from sqlalchemy.exc import IntegrityError, SQLAlchemyError

    if isinstance(exc, IntegrityError):
        # Detectar si es un error de clave duplicada
        error_msg = str(exc.orig).lower()
        if "duplicate" in error_msg or "unique" in error_msg:
            return SifenDuplicateEntityError(
                entity_type="Record",
                field="unknown",
                value="unknown",
                original_exception=exc
            )
        else:
            return SifenDatabaseError(
                f"Error de integridad en base de datos: {str(exc.orig)}",
                operation=operation,
                original_exception=exc
            )
    elif isinstance(exc, SQLAlchemyError):
        return SifenDatabaseError(
            f"Error de base de datos: {str(exc)}",
            operation=operation,
            original_exception=exc
        )
    else:
        return SifenDatabaseError(
            f"Error inesperado en base de datos: {str(exc)}",
            operation=operation,
            original_exception=exc
        )


def handle_validation_exception(exc: Exception, field: Optional[str] = None) -> SifenValidationError:
    """
    Convierte excepciones de validación en excepciones SIFEN.

    Args:
        exc: Excepción original
        field: Campo que falló la validación

    Returns:
        SifenValidationError: Excepción SIFEN de validación
    """
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        validation_errors = []
        for error in exc.errors():
            validation_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })

        return SifenValidationError(
            f"Errores de validación: {len(validation_errors)} campo(s)",
            validation_errors=validation_errors,
            original_exception=exc
        )
    else:
        return SifenValidationError(
            f"Error de validación: {str(exc)}",
            field=field,
            original_exception=exc
        )


def handle_external_service_exception(
    exc: Exception,
    service_name: str,
    endpoint: Optional[str] = None
) -> SifenExternalServiceError:
    """
    Convierte excepciones de servicios externos en excepciones SIFEN.

    Args:
        exc: Excepción original
        service_name: Nombre del servicio externo
        endpoint: Endpoint que falló (opcional)

    Returns:
        SifenExternalServiceError: Excepción SIFEN apropiada
    """
    import requests

    if isinstance(exc, requests.exceptions.RequestException):
        status_code = None
        response_body = None

        if hasattr(exc, 'response') and exc.response is not None:
            status_code = exc.response.status_code
            try:
                response_body = exc.response.text
            except:
                response_body = "No se pudo leer el cuerpo de la respuesta"

        if service_name.lower() == "sifen api":
            return SifenAPIError(
                f"Error en API SIFEN: {str(exc)}",
                endpoint=endpoint or "unknown",
                status_code=status_code,
                response_body=response_body,
                original_exception=exc
            )
        else:
            return SifenExternalServiceError(
                f"Error en servicio externo {service_name}: {str(exc)}",
                service_name=service_name,
                status_code=status_code,
                response_body=response_body,
                original_exception=exc
            )
    else:
        return SifenExternalServiceError(
            f"Error inesperado en servicio {service_name}: {str(exc)}",
            service_name=service_name,
            original_exception=exc
        )

# === DECORADOR PARA MANEJO AUTOMÁTICO ===


def handle_exceptions(
    default_exception: type = SifenBaseException,
    log_level: str = "error"
):
    """
    Decorador para manejo automático de excepciones.

    Args:
        default_exception: Tipo de excepción por defecto
        log_level: Nivel de logging

    Returns:
        Decorador de función

    Example:
        >>> @handle_exceptions(SifenDatabaseError)
        >>> def database_operation():
        >>>     # operación que puede fallar
        >>>     pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SifenBaseException:
                # Re-raise excepciones SIFEN
                raise
            except Exception as e:
                # Convertir otras excepciones
                logger.log(
                    getattr(logging, log_level.upper()),
                    f"Excepción no manejada en {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise default_exception(
                    f"Error en {func.__name__}: {str(e)}",
                    original_exception=e
                )
        return wrapper
    return decorator

# === MAPA DE EXCEPCIONES HTTP ===


EXCEPTION_HTTP_STATUS_MAP = {
    SifenValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SifenRUCValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SifenCDCValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SifenEntityNotFoundError: status.HTTP_404_NOT_FOUND,
    SifenDuplicateEntityError: status.HTTP_409_CONFLICT,
    SifenAuthenticationError: status.HTTP_401_UNAUTHORIZED,
    SifenInvalidTokenError: status.HTTP_401_UNAUTHORIZED,
    SifenTokenExpiredError: status.HTTP_401_UNAUTHORIZED,
    SifenAuthorizationError: status.HTTP_403_FORBIDDEN,
    SifenBusinessLogicError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SifenDocumentStateError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SifenExternalServiceError: status.HTTP_502_BAD_GATEWAY,
    SifenAPIError: status.HTTP_502_BAD_GATEWAY,
    SifenConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    SifenDatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def get_http_status_for_exception(exception: SifenBaseException) -> int:
    """
    Obtiene el código HTTP apropiado para una excepción.

    Args:
        exception: Excepción SIFEN

    Returns:
        int: Código de estado HTTP
    """
    return EXCEPTION_HTTP_STATUS_MAP.get(
        type(exception),
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
