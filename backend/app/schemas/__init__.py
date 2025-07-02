# ===============================================
# ARCHIVO: backend/app/schemas/__init__.py
# PROPÓSITO: Exports centralizados y configuración para DTOs Pydantic
# PRIORIDAD: 🟡 CRÍTICO - Punto de entrada para todos los schemas
# ===============================================

"""
Schemas (DTOs) Pydantic para APIs REST del sistema SIFEN.

Este módulo centraliza todos los Data Transfer Objects usados en:
- Validación de entrada API (request validation)
- Serialización de salida API (response serialization)
- Documentación automática OpenAPI/Swagger

Arquitectura:
- common.py: DTOs base reutilizables
- user.py: DTOs autenticación y usuarios
- empresa.py: DTOs empresa/contribuyente emisor
- cliente.py: DTOs cliente/receptor
- producto.py: DTOs productos y servicios
- factura.py: DTOs facturas y documentos fiscales
- documento.py: DTOs documento base electrónico

Integración:
- FastAPI: Validación automática request/response
- OpenAPI: Documentación auto-generada
- Frontend: Contratos de API tipados
"""

# ===============================================
# IMPORTS COMUNES SIEMPRE DISPONIBLES
# ===============================================

from .common import (
    # === PAGINACIÓN ===
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,

    # === RESPUESTAS ESTÁNDAR ===
    SuccessResponse,
    ErrorResponse,
    MessageResponse,

    # === ERRORES ESPECÍFICOS ===
    ValidationErrorResponse,
    NotFoundErrorResponse,

    # === VALIDADORES PARAGUAY ===
    RucValidation,
    MontoParaguay,
    DateTimeValidation,

    # === TIPOS COMUNES ===
    EstadoDocumento,
    EstadoDocumentoEnum,
    CommonQueryParams,

    # === TIPOS GENÉRICOS ===
    DataT
)

# ===============================================
# IMPORTS CONDICIONALES POR MÓDULO
# ===============================================

# Estos imports se cargarán según se vayan implementando los archivos

try:
    from .user import (
        UserCreateDTO,
        UserLoginDTO,
        UserResponseDTO,
        UserUpdateDTO,
        PasswordResetDTO,
        TokenResponseDTO,
        UserListDTO,
        UserStatsDTO
    )
    _user_available = True
except ImportError:
    _user_available = False

try:
    from .empresa import (
        EmpresaCreateDTO,
        EmpresaUpdateDTO,
        EmpresaResponseDTO,
        EmpresaListDTO,
        EmpresaConfigSifenDTO,
        EmpresaStatsDTO,
        AmbienteSifenEnum,
        DepartamentoParaguayEnum
    )
    _empresa_available = True
except ImportError:
    _empresa_available = False

try:
    from .cliente import (
        ClienteCreateDTO,
        ClienteUpdateDTO,
        ClienteResponseDTO,
        ClienteSearchDTO,
        ClienteListDTO,
        ClienteStatsDTO,
        TipoClienteEnum,
        TipoDocumentoEnum,
        DepartamentoParaguayEnum
    )
    _cliente_available = True
except ImportError:
    _cliente_available = False

try:
    from .producto import (
        ProductoCreateDTO,
        ProductoUpdateDTO,
        ProductoResponseDTO,
        ProductoCatalogoDTO,
        ProductoListDTO,
        ProductoStatsDTO,
        TipoProductoEnum,
        AfectacionIvaEnum,
        TasaIvaEnum,
        UnidadMedidaEnum
    )
    _producto_available = True
except ImportError:
    _producto_available = False

try:
    from .factura import (
        ItemFacturaDTO,
        FacturaCreateDTO,
        FacturaResponseDTO,
        FacturaListDTO,
        FacturaSifenDTO,
        FacturaUpdateDTO,
        ItemFacturaResponseDTO,
        FacturaSifenResponseDTO,
        FacturaSearchDTO,
        FacturaStatsDTO,
        TipoDocumentoSifenEnum,
        TipoEmisionEnum,
        EstadoDocumentoEnum,
        TipoOperacionEnum,
        CondicionOperacionEnum,
        MonedaEnum
    )
    _factura_available = True
except ImportError:
    _factura_available = False

try:
    from .documento import (
        DocumentoBaseDTO,
        DocumentoEstadoDTO,
        DocumentoSifenDTO,
        DocumentoConsultaDTO,
        DocumentoStatsDTO,
        TipoDocumentoBaseEnum,
        EstadoDocumentoBaseEnum,
        CodigoRespuestaSifenEnum
    )
    _documento_available = True
except ImportError:
    _documento_available = False


# ===============================================
# CONFIGURACIÓN PYDANTIC GLOBAL
# ===============================================

class SchemaConfig:
    """
    Configuración global para todos los schemas Pydantic.

    Define comportamientos estándar que se heredan en todos
    los DTOs del sistema para mantener consistencia.
    """

    # === CONFIGURACIÓN GENERAL ===
    # Permitir validación de atributos por nombre y alias
    populate_by_name = True

    # Validar tipos estrictamente
    validate_assignment = True

    # Usar enum values en lugar de nombres
    use_enum_values = True

    # Permitir reutilización de modelos en schema JSON
    validate_all = True

    # === CONFIGURACIÓN JSON ===
    # Serializar fechas en formato ISO
    json_encoders = {
        # datetime se serializa en formato ISO 8601
        "datetime": lambda dt: dt.isoformat() if dt else None,
        # Decimal como string para preservar precisión
        "Decimal": lambda d: str(d) if d is not None else None
    }

    # === CONFIGURACIÓN OPENAPI ===
    # Generar ejemplos en documentación
    schema_extra = {
        "additionalProperties": False  # No permitir campos extras
    }


# ===============================================
# HELPERS PARA DESARROLLO
# ===============================================

def get_available_schemas() -> dict:
    """
    Retorna información sobre qué schemas están disponibles.

    Útil para debugging y verificar el estado de implementación
    durante el desarrollo incremental.

    Returns:
        dict: Estado de cada módulo de schemas

    Examples:
        ```python
        from app.schemas import get_available_schemas
        print(get_available_schemas())
        # {
        #     "common": True,
        #     "user": False,
        #     "empresa": False,
        #     ...
        # }
        ```
    """
    return {
        "common": True,  # Siempre disponible
        "user": _user_available,
        "empresa": _empresa_available,
        "cliente": _cliente_available,
        "producto": _producto_available,
        "factura": _factura_available,
        "documento": _documento_available
    }


def get_schema_stats() -> dict:
    """
    Estadísticas de implementación de schemas.

    Returns:
        dict: Estadísticas de progreso
    """
    available = get_available_schemas()
    total_modules = len(available)
    implemented = sum(available.values())

    return {
        "total_modules": total_modules,
        "implemented": implemented,
        "pending": total_modules - implemented,
        "completion_percentage": round((implemented / total_modules) * 100, 1),
        "status_by_module": available
    }


# ===============================================
# EXPORTS PRINCIPALES
# ===============================================

# Exports que siempre están disponibles (common.py)
__all__ = [
    # === COMUNES (SIEMPRE DISPONIBLES) ===
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "MessageResponse",
    "ValidationErrorResponse",
    "NotFoundErrorResponse",
    "RucValidation",
    "MontoParaguay",
    "DateTimeValidation",
    "EstadoDocumento",
    "EstadoDocumentoEnum",
    "CommonQueryParams",
    "DataT",

    # === CONFIGURACIÓN ===
    "SchemaConfig",

    # === HELPERS ===
    "get_available_schemas",
    "get_schema_stats"
]

# Agregar exports condicionales según disponibilidad
if _user_available:
    __all__.extend([
        "UserCreateDTO",
        "UserLoginDTO",
        "UserResponseDTO",
        "UserUpdateDTO",
        "PasswordResetDTO",
        "TokenResponseDTO",
        "UserListDTO",
        "UserStatsDTO"
    ])

if _empresa_available:
    __all__.extend([
        "EmpresaCreateDTO",
        "EmpresaUpdateDTO",
        "EmpresaResponseDTO",
        "EmpresaListDTO",
        "EmpresaConfigSifenDTO",
        "EmpresaStatsDTO",
        "AmbienteSifenEnum",
        "DepartamentoParaguayEnum"
    ])

if _cliente_available:
    __all__.extend([
        "ClienteCreateDTO",
        "ClienteUpdateDTO",
        "ClienteResponseDTO",
        "ClienteSearchDTO",
        "ClienteListDTO",
        "ClienteStatsDTO",
        "TipoClienteEnum",
        "TipoDocumentoEnum",
        "DepartamentoParaguayEnum"
    ])

if _producto_available:
    __all__.extend([
        "ProductoCreateDTO",
        "ProductoUpdateDTO",
        "ProductoResponseDTO",
        "ProductoCatalogoDTO",
        "ProductoListDTO",
        "ProductoStatsDTO",
        "TipoProductoEnum",
        "AfectacionIvaEnum",
        "TasaIvaEnum",
        "UnidadMedidaEnum"
    ])

if _factura_available:
    __all__.extend([
        "ItemFacturaDTO",
        "FacturaCreateDTO",
        "FacturaResponseDTO",
        "FacturaListDTO",
        "FacturaSifenDTO",
        "FacturaUpdateDTO",
        "ItemFacturaResponseDTO",
        "FacturaSifenResponseDTO",
        "FacturaSearchDTO",
        "FacturaStatsDTO",
        "TipoDocumentoSifenEnum",
        "TipoEmisionEnum",
        "EstadoDocumentoEnum",
        "TipoOperacionEnum",
        "CondicionOperacionEnum",
        "MonedaEnum"
    ])

if _documento_available:
    __all__.extend([
        "DocumentoBaseDTO",
        "DocumentoEstadoDTO",
        "DocumentoSifenDTO",
        "DocumentoConsultaDTO",
        "DocumentoStatsDTO",
        "TipoDocumentoBaseEnum",
        "EstadoDocumentoBaseEnum",
        "CodigoRespuestaSifenEnum"
    ])
