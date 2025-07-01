# ===============================================
# ARCHIVO: backend/app/models/base.py
# PROPÓSITO: Modelo base con timestamps para todas las entidades
# ===============================================
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declared_attr
from ..core.database import Base


class BaseModel(Base):
    """
    Modelo base abstracto para todas las entidades del sistema.

    Proporciona:
    - ID autoincremental como primary key
    - Timestamps automáticos created_at/updated_at
    - Nomenclatura automática de tablas en lowercase
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True,
                doc="ID único autoincremental")
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now,
        nullable=False,
        doc="Fecha y hora de creación"
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
        doc="Fecha y hora de última actualización"
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Genera nombre de tabla automáticamente en lowercase"""
        return cls.__name__.lower()

    def __repr__(self) -> str:
        """Representación string básica del modelo"""
        return f"<{self.__class__.__name__}(id={self.id})>"
