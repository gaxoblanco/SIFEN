# ===============================================
# ARCHIVO: backend/app/models/user.py
# PROPÓSITO: Usuario del sistema con autenticación JWT
# ===============================================

from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class User(BaseModel):
    """
    Usuario del sistema para autenticación y autorización.

    Soporta:
    - Autenticación JWT
    - Control de activación/desactivación
    - Permisos de superusuario
    - Relación 1:N con empresas
    """

    # Datos de autenticación
    email = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="Email único para login"
    )
    hashed_password = Column(
        String(255),
        nullable=False,
        doc="Password hasheado con bcrypt"
    )

    # Información personal
    full_name = Column(
        String(100),
        doc="Nombre completo del usuario"
    )

    # Flags de control
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Usuario activo en el sistema"
    )
    is_superuser = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Permisos de administrador"
    )

    # Metadata adicional
    last_login = Column(
        DateTime(timezone=True),
        doc="Último login registrado"
    )

    # Relaciones
    empresas = relationship(
        "Empresa",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Empresas asociadas al usuario"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
