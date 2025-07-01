# ===============================================
# ARCHIVO: backend/app/models/cliente.py
# PROPÓSITO: Cliente/Receptor de documentos electrónicos SIFEN
# ===============================================

from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, Enum
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
import re
from typing import Optional
import enum


class TipoClienteEnum(enum.Enum):
    """Tipos de clientes según normativa fiscal Paraguay"""
    PERSONA_FISICA = "persona_fisica"
    PERSONA_JURIDICA = "persona_juridica"
    EXTRANJERO = "extranjero"
    EXENTO = "exento"


class TipoDocumentoEnum(enum.Enum):
    """Tipos de documentos de identidad válidos en Paraguay"""
    RUC = "ruc"                    # RUC paraguayo (contribuyente)
    CI = "cedula_identidad"        # Cédula de identidad paraguaya
    PASAPORTE = "pasaporte"        # Pasaporte extranjero
    OTROS = "otros"                # Otros documentos


class Cliente(BaseModel):
    """
    Cliente/Receptor de documentos electrónicos SIFEN.

    Modelo que almacena información de clientes/receptores para:
    - Facturas electrónicas
    - Notas de crédito/débito  
    - Notas de remisión
    - Autofacturas

    Cumple con regulaciones de Paraguay:
    - Validación RUC con dígito verificador
    - Soporte para contribuyentes y no contribuyentes
    - Datos requeridos por SIFEN según tipo de cliente
    """

    # === IDENTIFICACIÓN ===
    tipo_cliente = Column(
        Enum(TipoClienteEnum),
        nullable=False,
        default=TipoClienteEnum.PERSONA_FISICA,
        doc="Tipo de cliente según normativa fiscal"
    )

    tipo_documento = Column(
        Enum(TipoDocumentoEnum),
        nullable=False,
        default=TipoDocumentoEnum.CI,
        doc="Tipo de documento de identidad"
    )

    numero_documento = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Número de documento (RUC, CI, Pasaporte, etc.)"
    )

    dv = Column(
        String(1),
        doc="Dígito verificador (solo para RUC)"
    )

    # === INFORMACIÓN PERSONAL/EMPRESARIAL ===
    razon_social = Column(
        String(200),
        doc="Razón social (para personas jurídicas)"
    )

    nombres = Column(
        String(100),
        doc="Nombres (para personas físicas)"
    )

    apellidos = Column(
        String(100),
        doc="Apellidos (para personas físicas)"
    )

    nombre_fantasia = Column(
        String(200),
        doc="Nombre comercial o fantasía"
    )

    # === LOCALIZACIÓN ===
    direccion = Column(
        Text,
        doc="Dirección completa del cliente"
    )

    ciudad = Column(
        String(100),
        doc="Ciudad de residencia/ubicación"
    )

    departamento = Column(
        String(2),
        doc="Código departamento Paraguay (01-17)"
    )

    codigo_postal = Column(
        String(10),
        doc="Código postal"
    )

    pais = Column(
        String(3),
        default="PRY",
        doc="Código país ISO (PRY para Paraguay)"
    )

    # === CONTACTO ===
    telefono = Column(
        String(20),
        doc="Teléfono principal"
    )

    celular = Column(
        String(20),
        doc="Teléfono celular"
    )

    email = Column(
        String(100),
        doc="Email para envío de documentos electrónicos"
    )

    # === INFORMACIÓN FISCAL ===
    contribuyente = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="True si es contribuyente registrado en SET"
    )

    exento_iva = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="True si está exento de IVA"
    )

    # === CONFIGURACIÓN ===
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Cliente activo en el sistema"
    )

    observaciones = Column(
        Text,
        doc="Observaciones adicionales del cliente"
    )

    # === RELACIONES ===
    empresa_id = Column(
        Integer,
        ForeignKey('empresa.id'),
        nullable=False,
        doc="Empresa propietaria del cliente"
    )
    # empresa = relationship("Empresa", back_populates="clientes")

    # Relaciones futuras (comentadas para no crear dependencias aún)
    # facturas_emitidas = relationship("Factura", back_populates="cliente")
    # documentos_recibidos = relationship("Documento", back_populates="receptor")

    @validates('numero_documento')
    def validate_numero_documento(self, key: str, value: str) -> str:
        """Validar número de documento según tipo"""
        if not value:
            raise ValueError("Número de documento es requerido")

        value = value.strip()

        # Validación específica según tipo de documento
        tipo_doc = getattr(self, 'tipo_documento', None)

        if tipo_doc == TipoDocumentoEnum.RUC:
            return self._validate_ruc_format(value)
        elif tipo_doc == TipoDocumentoEnum.CI:
            return self._validate_ci_format(value)
        elif tipo_doc == TipoDocumentoEnum.PASAPORTE:
            return self._validate_pasaporte_format(value)

        return value

    def _validate_ruc_format(self, ruc: str) -> str:
        """Validar formato RUC Paraguay específicamente"""
        # Limpiar espacios y guiones
        clean_ruc = re.sub(r'[-\s]', '', ruc.strip())

        # Validar formato: 7-8 dígitos + guión + 1 dígito verificador
        if not re.match(r'^\d{7,8}-?\d{1}$', ruc):
            raise ValueError("RUC debe tener formato XXXXXXX-X o XXXXXXXX-X")

        # Extraer número y dígito verificador
        if '-' in ruc:
            ruc_number, dv = ruc.split('-')
        else:
            ruc_number = clean_ruc[:-1]
            dv = clean_ruc[-1]

        # Validar longitud del número base
        if len(ruc_number) < 7 or len(ruc_number) > 8:
            raise ValueError("Número base del RUC debe tener 7 u 8 dígitos")

        # Guardar el dígito verificador por separado
        self.dv = dv

        # Marcar como contribuyente automáticamente
        self.contribuyente = True

        # Retornar RUC formateado
        return f"{ruc_number}-{dv}"

    def _validate_ci_format(self, ci: str) -> str:
        """Validar formato Cédula de Identidad Paraguay"""
        # Limpiar puntos y espacios
        clean_ci = re.sub(r'[.\s]', '', ci.strip())

        # Validar formato: 6-8 dígitos numéricos
        if not re.match(r'^\d{6,8}$', clean_ci):
            raise ValueError("CI debe tener entre 6 y 8 dígitos")

        return clean_ci

    def _validate_pasaporte_format(self, pasaporte: str) -> str:
        """Validar formato básico de pasaporte"""
        clean_passport = pasaporte.strip().upper()

        # Validar longitud básica
        if len(clean_passport) < 6 or len(clean_passport) > 15:
            raise ValueError("Pasaporte debe tener entre 6 y 15 caracteres")

        return clean_passport

    @validates('departamento')
    def validate_departamento(self, key: str, value: Optional[str]) -> Optional[str]:
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

    @validates('email')
    def validate_email(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validar formato de email"""
        if value:
            # Patrón básico de email
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, value):
                raise ValueError("Formato de email inválido")
            return value.lower().strip()
        return value

    @validates('pais')
    def validate_pais(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validar código de país ISO"""
        if value:
            if len(value) != 3:
                raise ValueError("Código país debe tener 3 caracteres")
            return value.upper()
        return value

    def __repr__(self) -> str:
        numero_doc = getattr(self, 'numero_documento', 'unknown')
        return f"<Cliente(id={self.id}, doc='{numero_doc}', tipo='{self.tipo_cliente}')>"

    @property
    def nombre_completo(self) -> str:
        """Retorna nombre completo según tipo de cliente"""
        tipo_cliente_value = getattr(self, 'tipo_cliente', None)
        if tipo_cliente_value == TipoClienteEnum.PERSONA_JURIDICA:
            return getattr(self, 'razon_social', '') or ''
        else:
            nombres = getattr(self, 'nombres', '') or ''
            apellidos = getattr(self, 'apellidos', '') or ''
            if nombres and apellidos:
                return f"{nombres} {apellidos}"
            return nombres or apellidos or ''

    @property
    def documento_formateado(self) -> str:
        """Retorna documento con formato apropiado"""
        numero_doc = getattr(self, 'numero_documento', '')
        if not numero_doc:
            return ""
        tipo_documento_value = getattr(self, 'tipo_documento', None)
        if tipo_documento_value == TipoDocumentoEnum.RUC:
            return self.ruc_completo
        elif tipo_documento_value == TipoDocumentoEnum.CI:
            # Formatear CI con puntos: 1.234.567
            if len(numero_doc) >= 6:
                return f"{numero_doc[:-3]}.{numero_doc[-3:]}"

        return numero_doc

    @property
    def ruc_sin_dv(self) -> str:
        """Retorna RUC sin dígito verificador (solo si es RUC)"""
        tipo_documento_value = getattr(self, 'tipo_documento', None)
        if tipo_documento_value != TipoDocumentoEnum.RUC:
            return ""

        numero_doc = getattr(self, 'numero_documento', '')
        if numero_doc and '-' in numero_doc:
            return numero_doc.split('-')[0]
        return numero_doc[:-1] if numero_doc else ""

    @property
    def ruc_completo(self) -> str:
        """Retorna RUC con formato completo XXX.XXX.XXX-X (solo si es RUC)"""
        tipo_documento_value = getattr(self, 'tipo_documento', None)
        if tipo_documento_value != TipoDocumentoEnum.RUC:
            return ""

        ruc_num = self.ruc_sin_dv
        dv_value = getattr(self, 'dv', '')

        if len(ruc_num) >= 7 and dv_value:
            if len(ruc_num) == 8:
                formatted = f"{ruc_num[0]}.{ruc_num[1:4]}.{ruc_num[4:]}-{dv_value}"
                return formatted
            else:  # 7 dígitos
                formatted = f"{ruc_num[:3]}.{ruc_num[3:]}-{dv_value}"
                return formatted

        # Fallback al valor original
        numero_doc = getattr(self, 'numero_documento', '')
        return numero_doc if isinstance(numero_doc, str) else ""

    def to_dict_sifen(self) -> dict:
        """Retorna datos en formato requerido por SIFEN"""
        tipo_cliente_value = getattr(self, 'tipo_cliente', None)
        tipo_documento_value = getattr(self, 'tipo_documento', None)
        base_data = {
            "tipo_cliente": tipo_cliente_value.value if tipo_cliente_value else "",
            "tipo_documento": tipo_documento_value.value if tipo_documento_value else "",
            "numero_documento": getattr(self, 'numero_documento', ''),
            "nombre_completo": self.nombre_completo,
            "direccion": getattr(self, 'direccion', ''),
            "ciudad": getattr(self, 'ciudad', ''),
            "departamento": getattr(self, 'departamento', ''),
            "pais": getattr(self, 'pais', 'PRY'),
            "telefono": getattr(self, 'telefono', ''),
            "email": getattr(self, 'email', ''),
            "contribuyente": getattr(self, 'contribuyente', False),
            "exento_iva": getattr(self, 'exento_iva', False)
        }

        # Agregar campos específicos para RUC
        if tipo_documento_value == TipoDocumentoEnum.RUC:
            base_data.update({
                "ruc": self.ruc_sin_dv,
                "dv": getattr(self, 'dv', ''),
                "razon_social": getattr(self, 'razon_social', '')
            })
        else:
            base_data.update({
                "nombres": getattr(self, 'nombres', ''),
                "apellidos": getattr(self, 'apellidos', '')
            })

        return base_data

    def is_contribuyente_valido(self) -> bool:
        """Verifica si es un contribuyente válido para SIFEN"""
        # CORRECCIÓN: Extraer valores y hacer comparaciones explícitas
        contribuyente_value = getattr(self, 'contribuyente', False)
        tipo_documento_value = getattr(self, 'tipo_documento', None)
        numero_documento_value = getattr(self, 'numero_documento', '')
        dv_value = getattr(self, 'dv', '')

        return (
            bool(contribuyente_value) and
            tipo_documento_value == TipoDocumentoEnum.RUC and
            bool(numero_documento_value) and
            bool(dv_value)
        )

    def get_nombre_para_sifen(self) -> str:
        """Retorna nombre según requerimientos SIFEN"""
        tipo_cliente_value = getattr(self, 'tipo_cliente', None)

        if tipo_cliente_value == TipoClienteEnum.PERSONA_JURIDICA:
            return getattr(self, 'razon_social', '') or self.nombre_completo
        return self.nombre_completo
