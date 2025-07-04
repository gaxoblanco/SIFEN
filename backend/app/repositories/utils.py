"""
Utilidades type-safe para trabajar con modelos SQLAlchemy en repositories.

Este módulo proporciona helpers para evitar errores de tipado cuando
se accede a atributos de instancias SQLAlchemy, ya que PyLance/mypy
confunde las definiciones Column[T] con los valores reales T.

Funciones principales:
- safe_get(): Lectura type-safe de atributos SQLAlchemy
- safe_set(): Escritura type-safe de atributos SQLAlchemy  
- safe_bool(): Evaluación booleana type-safe
- safe_update(): Actualización masiva type-safe

Uso:
    from .utils import safe_get, safe_set, safe_bool
    
    # En lugar de: if user.is_active  # Error tipado
    if safe_bool(user, 'is_active'):  # Type-safe
    
    # En lugar de: user.last_login = datetime.now()  # Error tipado  
    safe_set(user, 'last_login', datetime.now())  # Type-safe

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from typing import Any, Optional, Dict, Union, TypeVar
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

# Type variable para modelos SQLAlchemy
ModelType = TypeVar('ModelType')

# ===============================================
# HELPERS TYPE-SAFE PARA SQLALCHEMY
# ===============================================


def safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """
    Obtiene un atributo de manera type-safe desde una instancia SQLAlchemy.

    Args:
        obj: Instancia del modelo SQLAlchemy
        attr: Nombre del atributo a obtener
        default: Valor por defecto si el atributo no existe

    Returns:
        Any: Valor del atributo o default

    Examples:
        ```python
        # En lugar de: email = user.email  # Puede dar error tipado
        email = safe_get(user, 'email', 'unknown@example.com')

        # Para campos opcionales:
        last_login = safe_get(user, 'last_login')  # None si no existe
        ```
    """
    try:
        return getattr(obj, attr, default)
    except AttributeError:
        logger.warning(
            f"Atributo '{attr}' no encontrado en {type(obj).__name__}")
        return default


def safe_set(obj: Any, attr: str, value: Any) -> None:
    """
    Establece un atributo de manera type-safe en una instancia SQLAlchemy.

    Args:
        obj: Instancia del modelo SQLAlchemy
        attr: Nombre del atributo a establecer
        value: Valor a asignar

    Examples:
        ```python
        # En lugar de: user.is_active = False  # Puede dar error tipado
        safe_set(user, 'is_active', False)

        # Para fechas:
        safe_set(user, 'last_login', datetime.utcnow())
        ```
    """
    try:
        setattr(obj, attr, value)
    except AttributeError as e:
        logger.error(
            f"Error estableciendo {attr} en {type(obj).__name__}: {e}")
        raise


def safe_bool(obj: Any, attr: str, default: bool = False) -> bool:
    """
    Evalúa un atributo booleano de manera type-safe.

    Args:
        obj: Instancia del modelo SQLAlchemy
        attr: Nombre del atributo booleano
        default: Valor por defecto si el atributo no existe o es None

    Returns:
        bool: Valor booleano del atributo

    Examples:
        ```python
        # En lugar de: if user.is_active  # Error tipado con Column[bool]
        if safe_bool(user, 'is_active'):

        # Con default explícito:
        if safe_bool(user, 'is_superuser', False):
        ```
    """
    value = safe_get(obj, attr, default)

    # Manejar casos None o valores falsy
    if value is None:
        return default

    # Convertir a bool de manera segura
    try:
        return bool(value)
    except (ValueError, TypeError):
        logger.warning(
            f"No se pudo convertir {attr}={value} a bool, usando default={default}")
        return default


def safe_str(obj: Any, attr: str, default: str = "") -> str:
    """
    Obtiene un atributo string de manera type-safe.

    Args:
        obj: Instancia del modelo SQLAlchemy
        attr: Nombre del atributo string
        default: Valor por defecto si el atributo no existe

    Returns:
        str: Valor string del atributo

    Examples:
        ```python
        # Para campos que pueden ser None:
        email = safe_str(user, 'email', 'unknown@example.com')

        # Para logging seguro:
        logger.info(f"Usuario: {safe_str(user, 'full_name', 'Sin nombre')}")
        ```
    """
    value = safe_get(obj, attr, default)

    if value is None:
        return default

    try:
        return str(value)
    except (ValueError, TypeError):
        logger.warning(
            f"No se pudo convertir {attr}={value} a string, usando default='{default}'")
        return default


def safe_int(obj: Any, attr: str, default: int = 0) -> int:
    """
    Obtiene un atributo entero de manera type-safe.

    Args:
        obj: Instancia del modelo SQLAlchemy
        attr: Nombre del atributo entero
        default: Valor por defecto si el atributo no existe

    Returns:
        int: Valor entero del atributo
    """
    value = safe_get(obj, attr, default)

    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(
            f"No se pudo convertir {attr}={value} a int, usando default={default}")
        return default


def safe_update(obj: Any, updates: Dict[str, Any]) -> None:
    """
    Actualiza múltiples atributos de manera type-safe.

    Args:
        obj: Instancia del modelo SQLAlchemy
        updates: Diccionario con atributo -> valor

    Examples:
        ```python
        # Actualización masiva:
        safe_update(user, {
            'is_active': True,
            'last_login': datetime.utcnow(),
            'full_name': 'Juan Pérez'
        })
        ```
    """
    for attr, value in updates.items():
        try:
            safe_set(obj, attr, value)
        except Exception as e:
            logger.error(f"Error actualizando {attr}={value}: {e}")
            # Continuar con los otros atributos
            continue

# ===============================================
# HELPERS ESPECIALIZADOS
# ===============================================


def safe_datetime(obj: Any, attr: str, default: Optional[datetime] = None) -> Optional[datetime]:
    """
    Obtiene un atributo datetime de manera type-safe.

    Args:
        obj: Instancia del modelo SQLAlchemy
        attr: Nombre del atributo datetime
        default: Valor por defecto (puede ser None)

    Returns:
        Optional[datetime]: Valor datetime o None/default
    """
    value = safe_get(obj, attr, default)

    if value is None:
        return default

    if isinstance(value, datetime):
        return value

    # Intentar convertir si es string o timestamp
    try:
        if isinstance(value, str):
            # Intentar parsear ISO format
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        elif isinstance(value, (int, float)):
            # Timestamp
            return datetime.fromtimestamp(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"No se pudo convertir {attr}={value} a datetime: {e}")

    return default


def is_field_set(obj: Any, attr: str) -> bool:
    """
    Verifica si un campo está establecido (no None) en el objeto.

    Args:
        obj: Instancia del modelo SQLAlchemy
        attr: Nombre del atributo

    Returns:
        bool: True si el campo tiene valor (no None)
    """
    try:
        value = getattr(obj, attr, None)
        return value is not None
    except AttributeError:
        return False


def get_model_values(obj: Any, attrs: list[str]) -> Dict[str, Any]:
    """
    Obtiene múltiples valores del modelo de forma segura.

    Args:
        obj: Instancia del modelo SQLAlchemy
        attrs: Lista de nombres de atributos

    Returns:
        Dict[str, Any]: Diccionario con valores obtenidos

    Examples:
        ```python
        # Obtener varios campos para logging:
        user_data = get_model_values(user, ['id', 'email', 'is_active'])
        logger.info(f"Usuario: {user_data}")
        ```
    """
    result = {}
    for attr in attrs:
        try:
            result[attr] = safe_get(obj, attr)
        except Exception as e:
            logger.warning(f"Error obteniendo {attr}: {e}")
            result[attr] = None

    return result

# ===============================================
# DECORADORES PARA REPOSITORIES
# ===============================================


def handle_sqlalchemy_access(func):
    """
    Decorador para manejar errores de acceso a atributos SQLAlchemy.

    Examples:
        ```python
        @handle_sqlalchemy_access
        def some_repository_method(self, db, user):
            # Cualquier error de atributo se logea pero no crashea
            return safe_get(user, 'email')
        ```
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttributeError as e:
            logger.error(f"Error de acceso a atributo en {func.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado en {func.__name__}: {e}")
            raise

    return wrapper

# ===============================================
# ALIASES PARA COMPATIBILIDAD
# ===============================================


# Aliases más cortos para uso frecuente
get = safe_get
set = safe_set
bool_val = safe_bool
str_val = safe_str
int_val = safe_int
update = safe_update

# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # Funciones principales
    "safe_get",
    "safe_set",
    "safe_bool",
    "safe_str",
    "safe_int",
    "safe_update",

    # Helpers especializados
    "safe_datetime",
    "is_field_set",
    "get_model_values",

    # Decoradores
    "handle_sqlalchemy_access",

    # Aliases cortos
    "get",
    "set",
    "bool_val",
    "str_val",
    "int_val",
    "update"
]
