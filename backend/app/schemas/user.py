# ===============================================
# ARCHIVO: backend/app/schemas/user.py
# PROPÓSITO: DTOs para usuarios y autenticación JWT
# PRIORIDAD: 🟡 CRÍTICO - Base para autenticación APIs
# ===============================================

"""
Esquemas Pydantic para gestión de usuarios y autenticación.

Este módulo define DTOs para:
- Registro de nuevos usuarios
- Login y autenticación JWT
- Gestión de perfiles de usuario
- Respuestas de autenticación

Integra con:
- models/user.py (SQLAlchemy)
- core/security.py (JWT, password hashing)
- api/v1/auth.py (endpoints autenticación)

Flujo de autenticación:
1. UserCreateDTO → registro usuario
2. UserLoginDTO → login con email/password
3. TokenResponseDTO → JWT token
4. UserResponseDTO → datos usuario autenticado
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
import re

# ===============================================
# HELPER FUNCTIONS
# ===============================================


def validate_password_strength(cls, v):
    """
    Valida fortaleza del password según políticas de seguridad.

    Requisitos:
    - Mínimo 8 caracteres
    - Al menos 1 mayúscula
    - Al menos 1 minúscula  
    - Al menos 1 número
    - Al menos 1 carácter especial
    """

    # Validación de fortaleza
    if len(v) < 8:
        raise ValueError('Password debe tener al menos 8 caracteres')
    if len(v) > 128:  # Límite razonable para bcrypt
        raise ValueError('Password no puede ser mayor a 128 caracteres')
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password debe tener al menos 1 mayúscula')

    if not re.search(r'[a-z]', v):
        raise ValueError('Password debe tener al menos 1 minúscula')

    if not re.search(r'\d', v):
        raise ValueError('Password debe tener al menos 1 número')

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError(
            'Password debe tener al menos 1 carácter especial')
    # Patrones comunes inseguros
    patrones_inseguros = [
        r'(123|abc|qwe|asd|zxc)',  # Secuencias comunes
        r'(password|admin|user|login)',  # Palabras comunes
        r'(.)\1{2,}',  # Más de 2 caracteres repetidos
    ]

    for patron in patrones_inseguros:
        if re.search(patron, v.lower()):
            raise ValueError('Password contiene patrones inseguros')
    return v


def validate_full_name(cls, v):
    """Valida formato del nombre completo"""
    # Remover espacios extra y capitalizar
    v = ' '.join(v.strip().split())

    # Validar caracteres válidos (letras, espacios, acentos, ñ)
    if not re.match(r'^[a-zA-ZÀ-ÿñÑ\s\'\-\.]+$', v):
        raise ValueError(
            'Nombre solo puede contener letras, espacios, apostrofes y guiones')

    caracteres_prohibidos = [
        '<', '>', '{', '}', '[', ']', '|', '\\', '^', '~', '`']
    if any(char in v for char in caracteres_prohibidos):
        raise ValueError('Nombre contiene caracteres no permitidos')

    return v.title()  # Capitalizar cada palabra


def passwords_match(cls, v, values):
    """Valida que password y confirm_password coincidan"""
    if 'password' in values and v != values['password']:
        raise ValueError('Passwords no coinciden')
    return v

# ===============================================
# DTOs DE ENTRADA (REQUEST)
# ===============================================


class UserCreateDTO(BaseModel):
    """
    DTO para registro de nuevos usuarios.

    Valida datos de entrada para crear cuenta nueva en el sistema.
    Incluye validaciones de seguridad para password y email único.

    Examples:
        ```python
        # POST /api/v1/auth/register
        user_data = UserCreateDTO(
            email="admin@empresa.com.py",
            password="MiPassword123!",
            full_name="Juan Pérez",
            confirm_password="MiPassword123!"
        )
        ```
    """

    email: EmailStr = Field(
        ...,
        description="Email único para login (será validado)"
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password seguro (mín. 8 caracteres)"
    )

    confirm_password: str = Field(
        ...,
        description="Confirmación de password (debe coincidir)"
    )

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Nombre completo del usuario"
    )

    @validator('password')
    def validate_password_strength(cls, v):
        """
        Valida fortaleza del password según políticas de seguridad.

        Requisitos:
        - Mínimo 8 caracteres
        - Al menos 1 mayúscula
        - Al menos 1 minúscula  
        - Al menos 1 número
        - Al menos 1 carácter especial
        """

        return validate_password_strength(cls, v)

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Valida que password y confirm_password coincidan"""
        return passwords_match(cls, v, values)

    @validator('full_name')
    def validate_full_name(cls, v):
        """Valida formato del nombre completo"""
        return validate_full_name(cls, v)

    @validator('email')
    def validate_email_business(cls, v):
        """Valida email con criterios adicionales"""
        email_str = str(v).lower()
        domain = email_str.split('@')[1] if '@' in email_str else ''

        # Validar que el dominio no sea demasiado corto
        if len(domain) < 4:
            raise ValueError('Dominio de email inválido')

        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "admin@empresa.com.py",
                "password": "MiPassword123!",
                "confirm_password": "MiPassword123!",
                "full_name": "Juan Pérez González"
            }
        }


class UserLoginDTO(BaseModel):
    """
    DTO para login de usuarios existentes.

    Credenciales para autenticación via email/password.
    Genera JWT token si las credenciales son válidas.

    Examples:
        ```python
        # POST /api/v1/auth/login
        login_data = UserLoginDTO(
            email="admin@empresa.com.py",
            password="MiPassword123!"
        )
        ```
    """

    email: EmailStr = Field(
        ...,
        description="Email registrado en el sistema"
    )

    password: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Password del usuario"
    )

    class Config:
        schema_extra = {
            "example": {
                "email": "admin@empresa.com.py",
                "password": "MiPassword123!"
            }
        }


class UserUpdateDTO(BaseModel):
    """
    DTO para actualización de perfil de usuario.

    Permite modificar datos del usuario autenticado.
    Todos los campos son opcionales para updates parciales.

    Examples:
        ```python
        # PUT /api/v1/users/me
        update_data = UserUpdateDTO(
            full_name="Juan Carlos Pérez",
            password="NuevoPassword456!"
        )
        ```
    """

    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Nuevo nombre completo (opcional)"
    )

    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=100,
        description="Nuevo password (opcional)"
    )

    confirm_password: Optional[str] = Field(
        None,
        description="Confirmación nuevo password (si se cambia password)"
    )

    @validator('password')
    def validate_password_strength(cls, v):
        """Valida fortaleza del password si se proporciona"""
        if v is not None:
            return validate_password_strength(cls, v)
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        return passwords_match(cls, v, values)

    @validator('full_name')
    def validate_full_name(cls, v):
        """Valida formato del nombre completo"""
        return validate_full_name(cls, v)

    class Config:
        schema_extra = {
            "example": {
                "full_name": "Juan Carlos Pérez González",
                "password": "NuevoPassword456!",
                "confirm_password": "NuevoPassword456!"
            }
        }


class PasswordResetDTO(BaseModel):
    """
    DTO para reset de password.

    Usado cuando el usuario olvida su password y necesita
    generar uno nuevo via email de recuperación.

    Examples:
        ```python
        # POST /api/v1/auth/reset-password
        reset_data = PasswordResetDTO(
            email="admin@empresa.com.py"
        )
        ```
    """

    email: EmailStr = Field(
        ...,
        description="Email del usuario para enviar reset link"
    )

    @validator('email')
    def validate_email_reset(cls, v):
        """Validador para email de reset"""
        email_str = str(v).lower()
        domain = email_str.split('@')[1] if '@' in email_str else ''

        # Validar que no sea un email obviamente falso
        dominios_invalidos = ['test.com', 'example.com', 'invalid.com']
        if domain in dominios_invalidos:
            raise ValueError('Email inválido')

        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "admin@empresa.com.py"
            }
        }


# ===============================================
# DTOs DE SALIDA (RESPONSE)
# ===============================================

class UserResponseDTO(BaseModel):
    """
    DTO para respuesta con datos de usuario.

    Información segura del usuario (sin password) para APIs.
    Usado en respuestas de autenticación y perfil.

    Examples:
        ```python
        # GET /api/v1/users/me response
        user_response = UserResponseDTO(
            id=1,
            email="admin@empresa.com.py",
            full_name="Juan Pérez",
            is_active=True,
            is_superuser=False,
            created_at="2025-01-15T10:30:00",
            last_login="2025-01-15T09:15:00"
        )
        ```
    """

    id: int = Field(..., description="ID único del usuario")

    email: str = Field(..., description="Email del usuario")

    full_name: Optional[str] = Field(
        None,
        description="Nombre completo del usuario"
    )

    is_active: bool = Field(
        ...,
        description="Si el usuario está activo"
    )

    is_superuser: bool = Field(
        ...,
        description="Si tiene permisos de administrador"
    )

    created_at: datetime = Field(
        ...,
        description="Fecha de creación de la cuenta"
    )

    updated_at: datetime = Field(
        ...,
        description="Fecha de última actualización"
    )

    last_login: Optional[datetime] = Field(
        None,
        description="Fecha del último login"
    )

    # Información adicional útil para frontend
    empresas_count: Optional[int] = Field(
        None,
        description="Número de empresas asociadas al usuario"
    )
    timezone: Optional[str] = Field(
        default="America/Asuncion",
        description="Zona horaria del usuario"
    )

    class Config:
        # Permitir creación desde ORM objects
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "email": "admin@empresa.com.py",
                "full_name": "Juan Pérez González",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:30:00",
                "last_login": "2025-01-15T09:15:00",
                "empresas_count": 2
            }
        }


class TokenResponseDTO(BaseModel):
    """
    DTO para respuesta de autenticación con JWT.

    Token y metadata de autenticación exitosa.
    Incluye información del usuario y tiempo de expiración.

    Examples:
        ```python
        # POST /api/v1/auth/login response
        token_response = TokenResponseDTO(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            token_type="bearer",
            expires_in=1800,
            user=UserResponseDTO(...)
        )
        ```
    """

    access_token: str = Field(
        ...,
        description="JWT access token"
    )

    token_type: str = Field(
        default="bearer",
        description="Tipo de token (siempre 'bearer')"
    )

    expires_in: int = Field(
        ...,
        description="Tiempo de expiración en segundos"
    )

    user: UserResponseDTO = Field(
        ...,
        description="Información del usuario autenticado"
    )

    @validator('expires_in')
    def validate_expires_in(cls, v):
        """Valida tiempo de expiración del token"""
        if v <= 0:
            raise ValueError('Tiempo de expiración debe ser positivo')

        if v > 86400:  # 24 horas máximo
            raise ValueError(
                'Tiempo de expiración no puede ser mayor a 24 horas')

        return v

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE2NzM5NzI4MDB9.xyz123",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "email": "admin@empresa.com.py",
                    "full_name": "Juan Pérez González",
                    "is_active": True,
                    "is_superuser": False,
                    "created_at": "2025-01-15T10:30:00",
                    "updated_at": "2025-01-15T10:30:00",
                    "last_login": "2025-01-15T09:15:00",
                    "empresas_count": 2
                }
            }
        }


class UserListDTO(BaseModel):
    """
    DTO para elemento en lista de usuarios.

    Versión compacta de UserResponseDTO para listados
    que requieren menos información por performance.

    Examples:
        ```python
        # GET /api/v1/users response (lista)
        users_list = [
            UserListDTO(
                id=1,
                email="admin@empresa.com.py",
                full_name="Juan Pérez",
                is_active=True,
                created_at="2025-01-15T10:30:00"
            )
        ]
        ```
    """

    id: int = Field(..., description="ID único del usuario")

    email: str = Field(..., description="Email del usuario")

    full_name: Optional[str] = Field(
        None,
        description="Nombre completo del usuario"
    )

    is_active: bool = Field(
        ...,
        description="Si el usuario está activo"
    )

    is_superuser: bool = Field(
        ...,
        description="Si tiene permisos de administrador"
    )

    created_at: datetime = Field(
        ...,
        description="Fecha de creación de la cuenta"
    )

    last_login: Optional[datetime] = Field(
        None,
        description="Fecha del último login"
    )

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "email": "admin@empresa.com.py",
                "full_name": "Juan Pérez González",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2025-01-15T10:30:00",
                "last_login": "2025-01-15T09:15:00"
            }
        }


# ===============================================
# DTOs ESPECIALIZADOS
# ===============================================

class UserStatsDTO(BaseModel):
    """
    DTO para estadísticas de usuario.

    Información agregada sobre la actividad del usuario
    útil para dashboards y reportes administrativos.

    Examples:
        ```python
        # GET /api/v1/users/{id}/stats response
        user_stats = UserStatsDTO(
            user_id=1,
            empresas_count=2,
            documentos_count=156,
            ultimo_documento="2025-01-15T10:30:00",
            documentos_mes_actual=23
        )
        ```
    """

    user_id: int = Field(..., description="ID del usuario")

    empresas_count: int = Field(
        default=0,
        description="Número de empresas registradas"
    )

    documentos_count: int = Field(
        default=0,
        description="Total documentos emitidos"
    )

    ultimo_documento: Optional[datetime] = Field(
        None,
        description="Fecha del último documento emitido"
    )

    documentos_mes_actual: int = Field(
        default=0,
        description="Documentos emitidos en el mes actual"
    )

    facturas_aprobadas: int = Field(
        default=0,
        description="Facturas aprobadas por SIFEN"
    )

    facturas_rechazadas: int = Field(
        default=0,
        description="Facturas rechazadas por SIFEN"
    )

    @validator('facturas_rechazadas', always=True)
    def validate_stats_consistency(cls, v, values):
        """Valida consistencia de estadísticas"""
        documentos_count = values.get('documentos_count', 0)
        facturas_aprobadas = values.get('facturas_aprobadas', 0)

        total_facturas = facturas_aprobadas + v
        if total_facturas > documentos_count:
            raise ValueError(
                'Total facturas no puede ser mayor a documentos totales')

        return v

    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "empresas_count": 2,
                "documentos_count": 156,
                "ultimo_documento": "2025-01-15T10:30:00",
                "documentos_mes_actual": 23,
                "facturas_aprobadas": 145,
                "facturas_rechazadas": 11
            }
        }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # === DTOs DE ENTRADA ===
    "UserCreateDTO",
    "UserLoginDTO",
    "UserUpdateDTO",
    "PasswordResetDTO",

    # === DTOs DE SALIDA ===
    "UserResponseDTO",
    "TokenResponseDTO",
    "UserListDTO",
    "UserStatsDTO"
]
