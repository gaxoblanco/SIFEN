"""
Módulo de seguridad y autenticación para el sistema SIFEN.

Este módulo maneja:
- Autenticación JWT (access y refresh tokens)
- Hashing de contraseñas con bcrypt
- Validación de tokens
- Middleware de seguridad
- Utilidades de autorización

Funcionalidades principales:
- Generar y validar tokens JWT
- Hash y verificación de contraseñas
- Decoradores para proteger endpoints
- Manejo de refresh tokens
- Rate limiting por usuario

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings

# Configurar logging
logger = logging.getLogger(__name__)

# === CONFIGURACIÓN DE HASHING ===

# Context para hashing de contraseñas
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Mayor seguridad, más lento
)

# Bearer token scheme para FastAPI
security_scheme = HTTPBearer(
    scheme_name="JWT Bearer Token",
    description="Token JWT para autenticación",
    auto_error=False  # Manejo manual de errores
)

# === MODELOS PYDANTIC ===


class TokenData(BaseModel):
    """Datos contenidos en el token JWT."""
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    scopes: List[str] = []
    token_type: str = "access"


class Token(BaseModel):
    """Respuesta de autenticación con tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Segundos hasta expiración


class TokenPayload(BaseModel):
    """Payload del token JWT."""
    sub: str  # Subject (user_id)
    username: str
    email: str
    scopes: List[str] = []
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    token_type: str = "access"


class UserInToken(BaseModel):
    """Datos del usuario extraídos del token."""
    id: int
    username: str
    email: str
    scopes: List[str] = []
    is_active: bool = True

# === FUNCIONES DE HASHING ===


def hash_password(password: str) -> str:
    """
    Genera hash de contraseña usando bcrypt.

    Args:
        password: Contraseña en texto plano

    Returns:
        str: Hash de la contraseña

    Example:
        >>> hashed = hash_password("mi_password_123")
        >>> len(hashed) > 50  # bcrypt genera hashes largos
        True
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hasheando password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno procesando contraseña"
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica contraseña contra hash.

    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash almacenado

    Returns:
        bool: True si coincide, False en caso contrario

    Example:
        >>> hashed = hash_password("test123")
        >>> verify_password("test123", hashed)
        True
        >>> verify_password("wrong", hashed)
        False
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verificando password: {str(e)}")
        return False

# === FUNCIONES JWT ===


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea token de acceso JWT.

    Args:
        data: Datos a incluir en el token
        expires_delta: Tiempo de expiración personalizado

    Returns:
        str: Token JWT firmado

    Example:
        >>> token = create_access_token({"sub": "123", "username": "user"})
        >>> isinstance(token, str)
        True
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "token_type": "access"
    })

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(
            f"Token creado para usuario: {data.get('username', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creando access token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generando token de acceso"
        )


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea token de refresh JWT.

    Args:
        data: Datos a incluir en el token
        expires_delta: Tiempo de expiración personalizado

    Returns:
        str: Refresh token JWT firmado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "token_type": "refresh"
    })

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        logger.debug(
            f"Refresh token creado para usuario: {data.get('username', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creando refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generando refresh token"
        )


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """
    Verifica y decodifica token JWT.

    Args:
        token: Token JWT a verificar
        token_type: Tipo esperado ("access" o "refresh")

    Returns:
        TokenData: Datos extraídos del token

    Raises:
        HTTPException: Si el token es inválido
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Verificar tipo de token
        if payload.get("token_type") != token_type:
            logger.warning(
                f"Tipo de token incorrecto. Esperado: {token_type}, Recibido: {payload.get('token_type')}")
            raise credentials_exception

        # Extraer datos
        user_id: Optional[str] = payload.get("sub")
        username: Optional[str] = payload.get("username")
        email: Optional[str] = payload.get("email")
        scopes: List[str] = payload.get("scopes", [])

        if user_id is None or username is None:
            raise credentials_exception

        token_data = TokenData(
            user_id=int(user_id),
            username=username,
            email=email,  # Puede ser None, el modelo lo acepta
            scopes=scopes,
            token_type=token_type
        )

        logger.debug(f"Token válido para usuario: {username}")
        return token_data

    except JWTError as e:
        logger.warning(f"Error JWT: {str(e)}")
        raise credentials_exception
    except ValueError as e:
        logger.warning(f"Error convirtiendo user_id: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error inesperado verificando token: {str(e)}")
        raise credentials_exception

# === DEPENDENCIES PARA FASTAPI ===


async def get_current_user_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security_scheme)
) -> TokenData:
    """
    Dependency para obtener usuario actual desde token.

    Args:
        credentials: Credenciales HTTP Bearer

    Returns:
        TokenData: Datos del usuario del token

    Raises:
        HTTPException: Si no hay token o es inválido
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorización requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(credentials.credentials, "access")


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security_scheme)
) -> Optional[TokenData]:
    """
    Dependency para obtener usuario actual (opcional).

    Útil para endpoints que pueden funcionar con o sin autenticación.

    Args:
        credentials: Credenciales HTTP Bearer (opcional)

    Returns:
        Optional[TokenData]: Datos del usuario o None
    """
    if not credentials:
        return None

    try:
        return verify_token(credentials.credentials, "access")
    except HTTPException:
        return None

# === VALIDACIÓN DE PERMISOS ===


def require_scopes(required_scopes: List[str]):
    """
    Decorator factory para requerir scopes específicos.

    Args:
        required_scopes: Lista de scopes requeridos

    Returns:
        Dependency function para FastAPI

    Example:
        >>> @app.get("/admin")
        >>> async def admin_endpoint(user: TokenData = Depends(require_scopes(["admin"]))):
        >>>     return {"message": "Admin access granted"}
    """
    async def check_scopes(
        current_user: TokenData = Depends(get_current_user_token)
    ) -> TokenData:
        """Verifica que el usuario tenga los scopes requeridos."""
        user_scopes = set(current_user.scopes)
        required_scopes_set = set(required_scopes)

        if not required_scopes_set.issubset(user_scopes):
            missing_scopes = required_scopes_set - user_scopes
            logger.warning(
                f"Usuario {current_user.username} sin permisos suficientes. "
                f"Requeridos: {required_scopes}, Faltantes: {list(missing_scopes)}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Requeridos: {', '.join(missing_scopes)}"
            )

        return current_user

    return check_scopes


def require_admin():
    """
    Dependency para requerir permisos de administrador.

    Returns:
        TokenData: Usuario con permisos de admin
    """
    return require_scopes(["admin"])


def require_user():
    """
    Dependency para requerir usuario autenticado (cualquier scope).

    Returns:
        TokenData: Usuario autenticado
    """
    return get_current_user_token

# === UTILIDADES DE AUTENTICACIÓN ===


def create_user_tokens(user_data: Dict[str, Any]) -> Token:
    """
    Crea ambos tokens (access y refresh) para un usuario.

    Args:
        user_data: Diccionario con datos del usuario

    Returns:
        Token: Objeto con ambos tokens

    Example:
        >>> user_data = {
        ...     "sub": "123",
        ...     "username": "usuario",
        ...     "email": "user@example.com",
        ...     "scopes": ["user"]
        ... }
        >>> tokens = create_user_tokens(user_data)
        >>> len(tokens.access_token) > 0
        True
    """
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token(user_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


def refresh_access_token(refresh_token: str) -> str:
    """
    Genera nuevo access token usando refresh token.

    Args:
        refresh_token: Refresh token válido

    Returns:
        str: Nuevo access token

    Raises:
        HTTPException: Si refresh token es inválido
    """
    # Verificar refresh token
    token_data = verify_token(refresh_token, "refresh")

    # Crear nuevo access token con los mismos datos
    new_token_data = {
        "sub": str(token_data.user_id),
        "username": token_data.username,
        "email": token_data.email,
        "scopes": token_data.scopes
    }

    return create_access_token(new_token_data)

# === VALIDACIÓN DE CONTRASEÑAS ===


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Valida la fortaleza de una contraseña.

    Args:
        password: Contraseña a validar

    Returns:
        dict: Resultado de validación con detalles

    Example:
        >>> result = validate_password_strength("Password123!")
        >>> result["is_valid"]
        True
    """
    result = {
        "is_valid": True,
        "errors": [],
        "score": 0,
        "suggestions": []
    }

    # Longitud mínima
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        result["errors"].append(
            f"Mínimo {settings.PASSWORD_MIN_LENGTH} caracteres")
        result["is_valid"] = False
    else:
        result["score"] += 1

    # Mayúsculas
    if not any(c.isupper() for c in password):
        result["errors"].append("Debe contener al menos una mayúscula")
        result["is_valid"] = False
    else:
        result["score"] += 1

    # Minúsculas
    if not any(c.islower() for c in password):
        result["errors"].append("Debe contener al menos una minúscula")
        result["is_valid"] = False
    else:
        result["score"] += 1

    # Números
    if not any(c.isdigit() for c in password):
        result["errors"].append("Debe contener al menos un número")
        result["is_valid"] = False
    else:
        result["score"] += 1

    # Caracteres especiales
    if settings.PASSWORD_REQUIRE_SPECIAL:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            result["errors"].append(
                "Debe contener al menos un carácter especial")
            result["is_valid"] = False
        else:
            result["score"] += 1

    # Sugerencias según score
    if result["score"] < 3:
        result["suggestions"].append(
            "Considera usar una contraseña más compleja")
    elif result["score"] < 5:
        result["suggestions"].append(
            "Buena contraseña, pero podría ser más fuerte")

    return result

# === UTILIDADES DE DEBUGGING ===


def decode_token_without_verification(token: str) -> Dict[str, Any]:
    """
    Decodifica token sin verificar (solo para debugging).

    ⚠️ SOLO USAR PARA DEBUGGING - NO VALIDAR AUTENTICACIÓN CON ESTO

    Args:
        token: Token JWT

    Returns:
        dict: Payload del token (sin verificar)
    """
    try:
        # En python-jose, se usa jwt.get_unverified_claims() para decodificar sin verificar
        return jwt.get_unverified_claims(token)
    except Exception as e:
        logger.error(f"Error decodificando token: {str(e)}")
        return {}


def get_token_info(token: str) -> Dict[str, Any]:
    """
    Obtiene información del token para debugging.

    Args:
        token: Token JWT

    Returns:
        dict: Información del token
    """
    try:
        payload = decode_token_without_verification(token)

        exp_timestamp = payload.get("exp", 0)
        iat_timestamp = payload.get("iat", 0)

        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "scopes": payload.get("scopes", []),
            "token_type": payload.get("token_type"),
            "issued_at": datetime.fromtimestamp(iat_timestamp) if iat_timestamp else None,
            "expires_at": datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None,
            "is_expired": exp_timestamp < datetime.utcnow().timestamp() if exp_timestamp else True,
            "time_to_expire": max(0, exp_timestamp - datetime.utcnow().timestamp()) if exp_timestamp else 0
        }
    except Exception as e:
        return {"error": str(e)}

# === HEALTH CHECK DE SEGURIDAD ===


def security_health_check() -> Dict[str, Any]:
    """
    Verifica el estado de salud del sistema de seguridad.

    Returns:
        dict: Estado de salud de la seguridad
    """
    health = {
        "status": "healthy",
        "checks": {}
    }

    try:
        # Test de hashing
        test_password = "test_password_123"
        hashed = hash_password(test_password)
        verify_result = verify_password(test_password, hashed)
        health["checks"]["password_hashing"] = verify_result

        # Test de JWT
        test_data = {"sub": "1", "username": "test", "email": "test@test.com"}
        test_token = create_access_token(test_data)
        token_data = verify_token(test_token)
        health["checks"]["jwt_creation"] = token_data.username == "test"

        # Configuración JWT
        health["checks"]["jwt_secret_length"] = len(
            settings.JWT_SECRET_KEY) >= 32
        health["checks"]["jwt_algorithm"] = settings.JWT_ALGORITHM == "HS256"

        # Verificar que todos los checks pasaron
        all_passed = all(health["checks"].values())
        if not all_passed:
            health["status"] = "degraded"

    except Exception as e:
        health["status"] = "unhealthy"
        health["error"] = str(e)

    return health
