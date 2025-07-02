# ===============================================
# ARCHIVO: backend/app/schemas/common.py
# PROPÓSITO: DTOs comunes para APIs REST - Paginación, Respuestas Estándar
# PRIORIDAD: 🟡 CRÍTICO - Base para todos los demás DTOs
# ===============================================

"""
Esquemas Pydantic comunes para APIs REST del sistema SIFEN.

Este módulo define DTOs base reutilizables en todas las APIs:
- Paginación estándar
- Respuestas exitosas/error uniformes
- Tipos base para responses
- Validadores comunes Paraguay

Usado por:
- api/v1/facturas.py
- api/v1/clientes.py
- api/v1/productos.py
- api/v1/empresas.py
"""

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from pydantic.generics import GenericModel
import re


# ===============================================
# TIPOS GENÉRICOS
# ===============================================

# Tipo genérico para responses paginadas
DataT = TypeVar('DataT')


class DepartamentoParaguayEnum(str, Enum):
    """
    Departamentos oficiales de Paraguay según SET.

    Códigos oficiales utilizados en documentos fiscales y SIFEN.
    Total: 17 departamentos + Asunción (incluida en Central).

    Fuente: Ministerio del Interior, SET Paraguay
    Última actualización: 2024
    """
    CONCEPCION = "01"           # Concepción
    SAN_PEDRO = "02"            # San Pedro
    CORDILLERA = "03"           # Cordillera
    GUAIRA = "04"               # Guairá
    CAAGUAZU = "05"             # Caaguazú
    CAAZAPA = "06"              # Caazapá
    ITAPUA = "07"               # Itapúa
    MISIONES = "08"             # Misiones
    PARAGUARI = "09"            # Paraguarí
    ALTO_PARANA = "10"          # Alto Paraná
    CENTRAL = "11"              # Central (incluye Asunción)
    NEEMBUCU = "12"             # Ñeembucú
    AMAMBAY = "13"              # Amambay
    CANINDEYU = "14"            # Canindeyú
    PRESIDENTE_HAYES = "15"     # Presidente Hayes
    ALTO_PARAGUAY = "16"        # Alto Paraguay
    BOQUERON = "17"             # Boquerón


class MonedaEnum(str, Enum):
    """Monedas soportadas por SIFEN"""
    PYG = "PYG"                      # Guaraní paraguayo
    USD = "USD"                      # Dólar americano
    EUR = "EUR"                      # Euro
    BRL = "BRL"                      # Real brasileño


# ===============================================
# PAGINACIÓN
# ===============================================


class PaginationParams(BaseModel):
    """
    Parámetros de paginación estándar para APIs.

    Usado en query parameters de endpoints que retornan listas.
    Implementa paginación estándar con límites razonables.

    Examples:
        ```python
        # GET /api/v1/facturas?page=2&size=50
        params = PaginationParams(page=2, size=50)
        ```
    """

    page: int = Field(
        default=1,
        ge=1,
        description="Número de página (base 1)"
    )

    size: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Elementos por página (máx. 50)"
    )

    class Config:
        # Permitir populate by name para compatibilidad frontend
        allow_population_by_field_name = True
        # Schema extra para documentación
        schema_extra = {
            "example": {
                "page": 1,
                "size": 20
            }
        }


class PaginationMeta(BaseModel):
    """
    Metadatos de paginación para respuestas.

    Información adicional sobre el estado de la paginación
    para facilitar navegación en frontend.
    """

    page: int = Field(..., description="Página actual")
    size: int = Field(..., description="Elementos por página")
    total: int = Field(..., description="Total de elementos")
    pages: int = Field(..., description="Total de páginas")
    has_next: bool = Field(..., description="Tiene página siguiente")
    has_prev: bool = Field(..., description="Tiene página anterior")

    class Config:
        schema_extra = {
            "example": {
                "page": 1,
                "size": 20,
                "total": 150,
                "pages": 8,
                "has_next": True,
                "has_prev": False
            }
        }


class PaginatedResponse(GenericModel, Generic[DataT]):
    """
    Response paginada genérica.

    Estructura estándar para todas las respuestas que incluyen listas
    paginadas de datos. Mantiene consistencia en formato de respuesta.

    Type Parameters:
        DataT: Tipo de los elementos en la lista de datos

    Examples:
        ```python
        # Response de lista de facturas
        response: PaginatedResponse[FacturaResponseDTO] = PaginatedResponse(
            data=[factura1, factura2, ...],
            meta=PaginationMeta(page=1, size=20, total=150, ...)
        )
        ```
    """

    data: List[DataT] = Field(..., description="Lista de elementos")
    meta: PaginationMeta = Field(..., description="Metadatos de paginación")


# ===============================================
# RESPUESTAS ESTÁNDAR
# ===============================================

class SuccessResponse(BaseModel):
    """
    Respuesta exitosa estándar.

    Usado para operaciones que no retornan datos específicos
    pero necesitan confirmar éxito de la operación.

    Examples:
        ```python
        # DELETE /api/v1/facturas/123
        return SuccessResponse(
            success=True,
            message="Factura eliminada exitosamente",
            data={"factura_id": 123}
        )
        ```
    """

    success: bool = Field(
        default=True,
        description="Indica si la operación fue exitosa"
    )

    message: str = Field(
        ...,
        description="Mensaje descriptivo de la operación"
    )

    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Datos adicionales opcionales"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de la respuesta"
    )

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Factura creada exitosamente",
                "data": {"factura_id": 123, "numero": "001-001-0000123"},
                "timestamp": "2025-01-15T10:30:00"
            }
        }


class ErrorResponse(BaseModel):
    """
    Respuesta de error estándar.

    Estructura uniforme para todos los errores de la API.
    Incluye códigos de error específicos y detalles para debugging.

    Examples:
        ```python
        # Error de validación
        return ErrorResponse(
            success=False,
            error_code="VALIDATION_ERROR",
            message="Datos de entrada inválidos",
            details={"ruc": ["Formato RUC inválido"]}
        )
        ```
    """

    success: bool = Field(
        default=False,
        description="Indica que la operación falló"
    )

    error_code: str = Field(
        ...,
        description="Código de error específico"
    )

    message: str = Field(
        ...,
        description="Mensaje de error legible"
    )

    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detalles adicionales del error"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp del error"
    )

    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "message": "Error en validación de datos de entrada",
                "details": {
                    "ruc": ["Formato RUC inválido"],
                    "email": ["Email requerido"]
                },
                "timestamp": "2025-01-15T10:30:00"
            }
        }


class MessageResponse(BaseModel):
    """
    Respuesta simple con mensaje.

    Para operaciones simples que solo necesitan retornar un mensaje
    de confirmación sin datos adicionales.

    Examples:
        ```python
        # Ping endpoint
        return MessageResponse(message="API funcionando correctamente")
        ```
    """

    message: str = Field(
        ...,
        description="Mensaje de respuesta"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de la respuesta"
    )

    class Config:
        schema_extra = {
            "example": {
                "message": "Sistema funcionando correctamente",
                "timestamp": "2025-01-15T10:30:00"
            }
        }


# ===============================================
# VALIDADORES PARAGUAY
# ===============================================

class RucValidation(BaseModel):
    """
    Validador especializado para RUC Paraguay.

    Valida formato RUC con dígito verificador según normativa
    de la SET (Subsecretaría de Estado de Tributación).

    Formatos válidos:
        - 12345678-9 (8 dígitos + DV)

    Algoritmo dígito verificador: Módulo 11 SET Paraguay
        - Factores: [2, 3, 4, 5, 6, 7, 2, 3]
        - Si resto < 2: DV = 0, sino DV = 11 - resto
    """

    ruc: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="RUC Paraguay con dígito verificador (formato: 12345678-9)"
    )

    @validator('ruc')
    def validate_ruc_format(cls, v):
        """
        Valida formato básico de RUC Paraguay.

        TODO: Implementar validación completa de dígito verificador
        usando algoritmo oficial de la SET.
        """
        # Remover espacios y convertir a mayúsculas
        v = v.strip().upper()

        # Validar formato con regex
        if not re.match(r'^\d{8}-\d$', v):
            raise ValueError('Formato RUC inválido. Debe ser: 12345678-9')

        # Extraer partes del RUC
        ruc_parts = v.split('-')
        ruc_number = ruc_parts[0]
        dv = ruc_parts[1]

        # Validar que no sea RUC de prueba inválido
        if ruc_number == "00000000":
            raise ValueError("RUC 00000000 no es válido")

        # Validar que el primer dígito no sea 0 (excepto casos especiales)
        if ruc_number.startswith("0") and ruc_number != "00000000":
            raise ValueError("RUC no puede empezar con 0")

        return v

    class Config:
        schema_extra = {
            "example": {
                "ruc": "80016875-4"
            }
        }


class MontoParaguay(BaseModel):
    """
    Validador para montos en Guaraníes Paraguay.

    Valida que los montos sean válidos para el sistema
    tributario paraguayo (sin centavos, rangos apropiados).
    """

    monto: Decimal = Field(
        ...,
        ge=0,
        description="Monto en Guaraníes (sin centavos)"
    )

    @validator('monto')
    def validate_monto_paraguay(cls, v):
        """
        Valida monto según reglas Paraguay.

        - No centavos (Guaraníes son enteros)
        - Rango razonable (0 a 999,999,999,999)
        """
        if v < 0:
            raise ValueError('Monto no puede ser negativo')

        if v > 999999999999:  # 999 mil millones (más realista)
            raise ValueError('Monto excede límite máximo permitido')

        # Verificar que no tenga decimales (centavos)
        if v != int(v):
            raise ValueError('Guaraníes no admiten centavos')

        return v

    class Config:
        schema_extra = {
            "example": {
                "monto": "1500000"
            }
        }


# ===============================================
# TIPOS DE DATOS COMUNES
# ===============================================

class EstadoDocumento(BaseModel):
    """
    Estado de documentos electrónicos SIFEN.

    Representa el estado actual de un documento en el flujo
    de procesamiento desde creación hasta aprobación SIFEN.
    """

    estado: str = Field(
        ...,
        description="Estado actual del documento"
    )

    descripcion: str = Field(
        ...,
        description="Descripción del estado"
    )

    fecha_cambio: datetime = Field(
        ...,
        description="Fecha del último cambio de estado"
    )

    puede_modificar: bool = Field(
        ...,
        description="Si el documento puede ser modificado"
    )

    class Config:
        schema_extra = {
            "example": {
                "estado": "aprobado",
                "descripcion": "Documento aprobado por SIFEN",
                "fecha_cambio": "2025-01-15T10:30:00",
                "puede_modificar": False
            }
        }

# ===============================================
# validación de errores HTTP
# ===============================================


class ValidationErrorResponse(ErrorResponse):
    """Respuesta específica para errores de validación"""

    error_code: str = Field(
        default="VALIDATION_ERROR",
        description="Código específico de validación"
    )

    field_errors: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Errores específicos por campo"
    )


class NotFoundErrorResponse(ErrorResponse):
    """Respuesta específica para recursos no encontrados"""

    error_code: str = Field(
        default="NOT_FOUND",
        description="Recurso no encontrado"
    )

    resource_type: Optional[str] = Field(
        default=None,
        description="Tipo de recurso buscado"
    )

    resource_id: Optional[str] = Field(
        default=None,
        description="ID del recurso buscado"
    )
# ===============================================
# validación de timestamp
# ===============================================


class DateTimeValidation(BaseModel):
    """Validador para fechas y timestamps Paraguay"""

    fecha: datetime = Field(
        ...,
        description="Fecha y hora"
    )

    @validator('fecha')
    def validate_fecha_paraguay(cls, v):
        """Valida fecha según zona horaria Paraguay"""
        # Paraguay está en UTC-3 (o UTC-4 en verano)
        # Validar que la fecha no sea futura más de 1 día
        from datetime import datetime, timedelta

        now = datetime.now()
        if v > now + timedelta(days=1):
            raise ValueError('Fecha no puede estar más de 1 día en el futuro')

        # Validar que no sea muy antigua (más de 10 años)
        if v < now - timedelta(days=3650):
            raise ValueError('Fecha no puede ser mayor a 10 años')

        return v

# ===============================================
# validación de códigos de estado específicos
# ===============================================


class EstadoDocumentoEnum(str, Enum):
    """Estados válidos de documentos SIFEN"""
    BORRADOR = "borrador"
    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    CANCELADO = "cancelado"


class CommonQueryParams(BaseModel):
    """Parámetros de query comunes para búsquedas"""

    q: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Término de búsqueda general"
    )

    fecha_desde: Optional[datetime] = Field(
        None,
        description="Filtrar desde fecha"
    )

    fecha_hasta: Optional[datetime] = Field(
        None,
        description="Filtrar hasta fecha"
    )

    ordenar_por: Optional[str] = Field(
        default="created_at",
        description="Campo para ordenar"
    )

    orden: Optional[str] = Field(
        default="desc",
        description="Dirección del orden (asc/desc)"
    )

    @validator('orden')
    def validate_orden(cls, v):
        """Valida dirección del orden"""
        if v not in ['asc', 'desc']:
            raise ValueError('Orden debe ser "asc" o "desc"')
        return v

# ===============================================
# EXPORTS
# ===============================================


__all__ = [
    # === PAGINACIÓN ===
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",

    # === RESPUESTAS ESTÁNDAR ===
    "SuccessResponse",
    "ErrorResponse",
    "MessageResponse",

    # === ERRORES ESPECÍFICOS ===
    "ValidationErrorResponse",
    "NotFoundErrorResponse",

    # === VALIDADORES PARAGUAY ===
    "RucValidation",
    "MontoParaguay",
    "DateTimeValidation",

    # === TIPOS COMUNES ===
    "EstadoDocumento",
    "EstadoDocumentoEnum",
    "CommonQueryParams",

    # === TIPOS GENÉRICOS ===
    "DataT"
]
