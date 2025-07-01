# ===============================================
# ARCHIVO: backend/app/models/empresa.py
# PROPÓSITO: Empresa/contribuyente emisor para SIFEN
# ===============================================

from .user import User
from .empresa import Empresa
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
import re


class Empresa(BaseModel):
    """
    Empresa/Contribuyente emisor de documentos electrónicos SIFEN.

    Cumple con regulaciones tributarias de Paraguay:
    - RUC con dígito verificador validado
    - Datos fiscales requeridos por SET
    - Información para generación de documentos electrónicos
    """

    # === IDENTIFICACIÓN FISCAL ===
    ruc = Column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
        doc="RUC con dígito verificador (ej: 80016875-5)"
    )
    dv = Column(
        String(1),
        nullable=False,
        doc="Dígito verificador del RUC"
    )

    # === INFORMACIÓN EMPRESARIAL ===
    razon_social = Column(
        String(200),
        nullable=False,
        doc="Razón social registrada en SET"
    )
    nombre_fantasia = Column(
        String(200),
        doc="Nombre comercial o fantasía"
    )

    # === LOCALIZACIÓN ===
    direccion = Column(
        Text,
        doc="Dirección fiscal completa"
    )
    ciudad = Column(
        String(100),
        doc="Ciudad de ubicación"
    )
    departamento = Column(
        String(2),
        doc="Código departamento Paraguay (01-17)"
    )

    # === CONTACTO ===
    telefono = Column(
        String(20),
        doc="Teléfono principal"
    )
    email = Column(
        String(100),
        doc="Email para notificaciones"
    )

    # === CONFIGURACIÓN SIFEN ===
    ambiente_sifen = Column(
        String(10),
        default="test",
        doc="Ambiente SIFEN: 'test' o 'production'"
    )
    establecimiento = Column(
        String(3),
        default="001",
        doc="Código establecimiento (001-999)"
    )
    punto_expedicion = Column(
        String(3),
        default="001",
        doc="Punto de expedición (001-999)"
    )

    # === ESTADO ===
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Empresa activa en el sistema"
    )

    # === RELACIONES ===
    user_id = Column(
        Integer,
        ForeignKey('user.id'),
        nullable=False,
        doc="Usuario propietario de la empresa"
    )
    user = relationship("User", back_populates="empresas")

    # Relaciones futuras (comentadas para no crear dependencias aún)
    # facturas = relationship("Factura", back_populates="empresa")
    # documentos = relationship("Documento", back_populates="empresa")

    @validates('ruc')
    def validate_ruc(self, key, value):
        """Validar formato RUC Paraguay con dígito verificador"""
        if not value:
            raise ValueError("RUC es requerido")

        # Limpiar espacios y guiones
        clean_ruc = re.sub(r'[-\s]', '', value.strip())

        # Validar formato: 7-8 dígitos + guión + 1 dígito verificador
        if not re.match(r'^\d{7,8}-?\d{1}$', value):
            raise ValueError("RUC debe tener formato XXXXXXX-X o XXXXXXXX-X")

        # Extraer número y dígito verificador
        if '-' in value:
            ruc_number, dv = value.split('-')
        else:
            ruc_number = clean_ruc[:-1]
            dv = clean_ruc[-1]

        # Validar longitud del número base
        if len(ruc_number) < 7 or len(ruc_number) > 8:
            raise ValueError("Número base del RUC debe tener 7 u 8 dígitos")

        # Guardar el dígito verificador por separado
        self.dv = dv

        # Retornar RUC formateado
        return f"{ruc_number}-{dv}"

    @validates('departamento')
    def validate_departamento(self, key, value):
        """Validar código de departamento Paraguay (01-17)"""
        if value:
            try:
                dept_num = int(value)
                if dept_num < 1 or dept_num > 17:
                    raise ValueError("Departamento debe estar entre 01 y 17")
                return str(dept_num).zfill(2)  # Formato 01, 02, etc.
            except ValueError:
                raise ValueError("Departamento debe ser numérico")
        return value

    @validates('establecimiento', 'punto_expedicion')
    def validate_codigo_3_digitos(self, key, value):
        """Validar códigos de 3 dígitos para establecimiento y punto expedición"""
        if value:
            try:
                num = int(value)
                if num < 1 or num > 999:
                    raise ValueError(f"{key} debe estar entre 001 y 999")
                return str(num).zfill(3)  # Formato 001, 002, etc.
            except ValueError:
                raise ValueError(f"{key} debe ser numérico")
        return value

    @validates('ambiente_sifen')
    def validate_ambiente(self, key, value):
        """Validar ambiente SIFEN"""
        if value and value not in ['test', 'production']:
            raise ValueError("Ambiente debe ser 'test' o 'production'")
        return value

    def __repr__(self) -> str:
        return f"<Empresa(id={self.id}, ruc='{self.ruc}', razon_social='{self.razon_social}')>"

    @property
    def ruc_sin_dv(self) -> str:
        """Retorna RUC sin dígito verificador"""
        # CORRECCIÓN: Acceder al valor de la columna correctamente
        ruc_value = getattr(self, 'ruc', '')
        if isinstance(ruc_value, str) and ruc_value:
            if '-' in ruc_value:
                return ruc_value.split('-')[0]
            return ruc_value[:-1]
        return ""

    @property
    def ruc_completo(self) -> str:
        """Retorna RUC con formato completo XXX.XXX.XXX-X"""
        ruc_num = self.ruc_sin_dv
        dv_value = getattr(self, 'dv', '')

        if len(ruc_num) >= 7 and dv_value:
            # Formatear con puntos: 80.016.875-5
            if len(ruc_num) == 8:
                formatted = f"{ruc_num[0]}.{ruc_num[1:4]}.{ruc_num[4:]}-{dv_value}"
                return formatted
            else:  # 7 dígitos
                formatted = f"{ruc_num[:3]}.{ruc_num[3:]}-{dv_value}"
                return formatted

        # Fallback al valor original - ASEGURAR RETURN EN TODOS LOS PATHS
        ruc_value = getattr(self, 'ruc', '')
        return ruc_value if isinstance(ruc_value, str) else ""

    def to_dict_sifen(self) -> dict:
        """Retorna datos en formato requerido por SIFEN"""
        return {
            "ruc": self.ruc_sin_dv,
            "dv": self.dv,
            "razon_social": self.razon_social,
            "nombre_fantasia": self.nombre_fantasia,
            "direccion": self.direccion,
            "ciudad": self.ciudad,
            "departamento": self.departamento,
            "telefono": self.telefono,
            "email": self.email,
            "establecimiento": self.establecimiento,
            "punto_expedicion": self.punto_expedicion
        }


# ===============================================
# ARCHIVO: backend/app/models/__init__.py
# PROPÓSITO: Exportaciones centralizadas de modelos
# ===============================================


__all__ = [
    "BaseModel",
    "User",
    "Empresa"
]
