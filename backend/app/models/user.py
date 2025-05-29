from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Relación con Empresa
    empresas = relationship("Empresa", back_populates="user")
