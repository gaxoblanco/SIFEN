from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class Empresa(BaseModel):
    ruc = Column(String(20), unique=True, index=True, nullable=False)
    razon_social = Column(String(100), nullable=False)
    nombre_fantasia = Column(String(100))
    direccion = Column(String(200))
    telefono = Column(String(20))
    email = Column(String(100))

    # Relación con Usuario
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship("User", back_populates="empresas")
