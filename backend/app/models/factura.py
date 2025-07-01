# ===============================================
# ARCHIVO: backend/app/models/factura.py
# PROPÓSITO: Facturas electrónicas específicas SIFEN
# VERSIÓN: 1.0.0 - Compatible con SIFEN v150
# ===============================================

from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, Enum, Numeric, DateTime, Date
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
from datetime import datetime, date
import re
from typing import Optional, List
from decimal import Decimal
import enum


class TipoDocumentoEnum(enum.Enum):
    """Tipos de documentos electrónicos SIFEN"""
    FACTURA = "1"                    # Factura Electrónica
    AUTOFACTURA = "4"               # Autofactura Electrónica
    NOTA_CREDITO = "5"              # Nota de Crédito Electrónica
    NOTA_DEBITO = "6"               # Nota de Débito Electrónica
    NOTA_REMISION = "7"             # Nota de Remisión Electrónica


class TipoEmisionEnum(enum.Enum):
    """Tipos de emisión según SIFEN"""
    NORMAL = "1"                    # Emisión normal
    CONTINGENCIA = "2"              # Emisión de contingencia


class EstadoDocumentoEnum(enum.Enum):
    """Estados del documento en el proceso SIFEN"""
    BORRADOR = "borrador"           # En construcción
    GENERADO = "generado"           # XML generado, listo para firmar
    FIRMADO = "firmado"            # Firmado digitalmente
    ENVIADO = "enviado"            # Enviado a SIFEN
    APROBADO = "aprobado"          # Aprobado por SIFEN
    RECHAZADO = "rechazado"        # Rechazado por SIFEN
    CANCELADO = "cancelado"        # Cancelado por usuario


class TipoOperacionEnum(enum.Enum):
    """Tipos de operación comercial"""
    VENTA = "1"                    # Venta de bienes/servicios
    EXPORTACION = "2"              # Exportación
    COMPRA = "3"                   # Compra (para autofacturas)
    OTRO = "4"                     # Otras operaciones


class CondicionOperacionEnum(enum.Enum):
    """Condiciones de pago de la operación"""
    CONTADO = "1"                  # Pago al contado
    CREDITO = "2"                  # Pago a crédito


class MonedaEnum(enum.Enum):
    """Monedas soportadas por SIFEN"""
    PYG = "PYG"                    # Guaraní paraguayo
    USD = "USD"                    # Dólar estadounidense
    EUR = "EUR"                    # Euro
    BRL = "BRL"                    # Real brasileño
    ARS = "ARS"                    # Peso argentino


class Factura(BaseModel):
    """
    Factura electrónica para SIFEN Paraguay.

    Modelo principal que representa un documento electrónico que cumple
    con todas las regulaciones del SET (Subsecretaría de Estado de Tributación).

    Incluye:
    - Numeración automática según establecimiento y punto expedición
    - Generación de CDC (Código de Control del Documento) de 44 dígitos
    - Cálculos automáticos de IVA y totales
    - Estados del documento en el flujo SIFEN
    - Relaciones con cliente, empresa e items
    """

    # === IDENTIFICACIÓN SIFEN ===
    cdc = Column(
        String(44),
        unique=True,
        index=True,
        doc="Código de Control del Documento (44 dígitos)"
    )

    tipo_documento = Column(
        Enum(TipoDocumentoEnum),
        nullable=False,
        default=TipoDocumentoEnum.FACTURA,
        doc="Tipo de documento electrónico SIFEN"
    )

    # === NUMERACIÓN OFICIAL ===
    establecimiento = Column(
        String(3),
        nullable=False,
        doc="Código de establecimiento (001-999)"
    )

    punto_expedicion = Column(
        String(3),
        nullable=False,
        doc="Punto de expedición (001-999)"
    )

    numero_documento = Column(
        String(7),
        nullable=False,
        doc="Número del documento (0000001-9999999)"
    )

    # === TIMBRADO ===
    numero_timbrado = Column(
        String(8),
        nullable=False,
        doc="Número de timbrado autorizado por SET"
    )

    fecha_inicio_vigencia = Column(
        Date,
        nullable=False,
        doc="Fecha inicio vigencia del timbrado"
    )

    fecha_fin_vigencia = Column(
        Date,
        nullable=False,
        doc="Fecha fin vigencia del timbrado"
    )

    # === FECHAS Y EMISIÓN ===
    fecha_emision = Column(
        Date,
        nullable=False,
        default=date.today,
        doc="Fecha de emisión del documento"
    )

    tipo_emision = Column(
        Enum(TipoEmisionEnum),
        nullable=False,
        default=TipoEmisionEnum.NORMAL,
        doc="Tipo de emisión (normal/contingencia)"
    )

    # === INFORMACIÓN COMERCIAL ===
    tipo_operacion = Column(
        Enum(TipoOperacionEnum),
        nullable=False,
        default=TipoOperacionEnum.VENTA,
        doc="Tipo de operación comercial"
    )

    condicion_operacion = Column(
        Enum(CondicionOperacionEnum),
        nullable=False,
        default=CondicionOperacionEnum.CONTADO,
        doc="Condición de pago"
    )

    moneda = Column(
        Enum(MonedaEnum),
        nullable=False,
        default=MonedaEnum.PYG,
        doc="Moneda de la operación"
    )

    tipo_cambio = Column(
        Numeric(10, 4),
        default=Decimal("1.0000"),
        doc="Tipo de cambio (1.0000 para PYG)"
    )

    # === TOTALES CALCULADOS ===
    subtotal_exento = Column(
        Numeric(15, 4),
        default=Decimal("0"),
        doc="Subtotal exento de IVA"
    )

    subtotal_gravado_5 = Column(
        Numeric(15, 4),
        default=Decimal("0"),
        doc="Subtotal gravado al 5%"
    )

    subtotal_gravado_10 = Column(
        Numeric(15, 4),
        default=Decimal("0"),
        doc="Subtotal gravado al 10%"
    )

    total_iva = Column(
        Numeric(15, 4),
        default=Decimal("0"),
        doc="Total IVA liquidado"
    )

    total_operacion = Column(
        Numeric(15, 4),
        default=Decimal("0"),
        doc="Total de la operación sin IVA"
    )

    total_general = Column(
        Numeric(15, 4),
        nullable=False,
        doc="Total general de la factura"
    )

    # === ESTADO Y PROCESAMIENTO ===
    estado = Column(
        Enum(EstadoDocumentoEnum),
        nullable=False,
        default=EstadoDocumentoEnum.BORRADOR,
        doc="Estado actual del documento"
    )

    codigo_respuesta_sifen = Column(
        String(10),
        doc="Código de respuesta de SIFEN"
    )

    mensaje_sifen = Column(
        Text,
        doc="Mensaje de respuesta de SIFEN"
    )

    numero_protocolo = Column(
        String(50),
        doc="Número de protocolo asignado por SIFEN"
    )

    fecha_envio_sifen = Column(
        DateTime,
        doc="Fecha y hora de envío a SIFEN"
    )

    fecha_respuesta_sifen = Column(
        DateTime,
        doc="Fecha y hora de respuesta de SIFEN"
    )

    # === INFORMACIÓN ADICIONAL ===
    observaciones = Column(
        Text,
        doc="Observaciones adicionales"
    )

    motivo_emision = Column(
        String(500),
        doc="Motivo de emisión del documento"
    )

    # === XML Y FIRMA ===
    xml_generado = Column(
        Text,
        doc="XML del documento generado"
    )

    xml_firmado = Column(
        Text,
        doc="XML con firma digital"
    )

    hash_documento = Column(
        String(64),
        doc="Hash SHA-256 del documento"
    )

    # === RELACIONES ===
    empresa_id = Column(
        Integer,
        ForeignKey('empresa.id'),
        nullable=False,
        doc="Empresa emisora"
    )
    # empresa = relationship("Empresa", back_populates="facturas")

    cliente_id = Column(
        Integer,
        ForeignKey('cliente.id'),
        nullable=False,
        doc="Cliente receptor"
    )
    # cliente = relationship("Cliente", back_populates="facturas_recibidas")

    # Relaciones futuras (comentadas para no crear dependencias aún)
    # items = relationship("ItemFactura", back_populates="factura", cascade="all, delete-orphan")
    # documentos_asociados = relationship("DocumentoAsociado", back_populates="factura")

    @validates('establecimiento', 'punto_expedicion')
    def validate_codigo_3_digitos(self, key: str, value: str) -> str:
        """Validar códigos de 3 dígitos"""
        if not value:
            raise ValueError(f"{key} es requerido")

        try:
            num = int(value)
            if num < 1 or num > 999:
                raise ValueError(f"{key} debe estar entre 001 y 999")
            return str(num).zfill(3)
        except ValueError:
            raise ValueError(f"{key} debe ser numérico")

    @validates('numero_documento')
    def validate_numero_documento(self, key: str, value: str) -> str:
        """Validar número de documento de 7 dígitos"""
        if not value:
            raise ValueError("Número de documento es requerido")

        try:
            num = int(value)
            if num < 1 or num > 9999999:
                raise ValueError(
                    "Número documento debe estar entre 0000001 y 9999999")
            return str(num).zfill(7)
        except ValueError:
            raise ValueError("Número documento debe ser numérico")

    @validates('numero_timbrado')
    def validate_numero_timbrado(self, key: str, value: str) -> str:
        """Validar número de timbrado"""
        if not value:
            raise ValueError("Número de timbrado es requerido")

        # Limpiar espacios
        clean_timbrado = value.strip()

        # Validar formato: 1-8 dígitos
        if not re.match(r'^\d{1,8}$', clean_timbrado):
            raise ValueError("Timbrado debe tener entre 1 y 8 dígitos")

        return clean_timbrado

    @validates('cdc')
    def validate_cdc(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validar formato CDC"""
        if value:
            # Limpiar espacios
            clean_cdc = value.strip()

            # Validar formato: exactamente 44 dígitos
            if not re.match(r'^\d{44}$', clean_cdc):
                raise ValueError(
                    "CDC debe tener exactamente 44 dígitos numéricos")

            return clean_cdc
        return value

    @validates('fecha_inicio_vigencia', 'fecha_fin_vigencia')
    def validate_fechas_vigencia(self, key: str, value: date) -> date:
        """Validar fechas de vigencia del timbrado"""
        if not value:
            raise ValueError(f"{key} es requerida")

        # Validar que no sea fecha muy antigua (más de 10 años)
        from datetime import date, timedelta
        fecha_limite = date.today() - timedelta(days=3650)  # 10 años

        if value < fecha_limite:
            raise ValueError(f"{key} no puede ser anterior a 10 años")

        return value

    def __repr__(self) -> str:
        numero = getattr(self, 'numero_documento', 'unknown')
        estado_value = getattr(self, 'estado', None)
        estado_str = estado_value.value if estado_value else 'unknown'
        return f"<Factura(id={self.id}, numero='{numero}', estado='{estado_str}')>"

    @property
    def numero_completo(self) -> str:
        """Retorna número completo: EST-PEX-NUMERO"""
        establecimiento_value = getattr(self, 'establecimiento', '001')
        punto_expedicion_value = getattr(self, 'punto_expedicion', '001')
        numero_value = getattr(self, 'numero_documento', '0000001')

        return f"{establecimiento_value}-{punto_expedicion_value}-{numero_value}"

    @property
    def timbrado_vigente(self) -> bool:
        """Verifica si el timbrado está vigente"""
        fecha_inicio_value = getattr(self, 'fecha_inicio_vigencia', None)
        fecha_fin_value = getattr(self, 'fecha_fin_vigencia', None)

        if not fecha_inicio_value or not fecha_fin_value:
            return False

        hoy = date.today()
        return fecha_inicio_value <= hoy <= fecha_fin_value

    @property
    def descripcion_tipo_documento(self) -> str:
        """Retorna descripción del tipo de documento"""
        tipo_value = getattr(self, 'tipo_documento', None)

        if tipo_value == TipoDocumentoEnum.FACTURA:
            return "Factura Electrónica"
        elif tipo_value == TipoDocumentoEnum.AUTOFACTURA:
            return "Autofactura Electrónica"
        elif tipo_value == TipoDocumentoEnum.NOTA_CREDITO:
            return "Nota de Crédito Electrónica"
        elif tipo_value == TipoDocumentoEnum.NOTA_DEBITO:
            return "Nota de Débito Electrónica"
        elif tipo_value == TipoDocumentoEnum.NOTA_REMISION:
            return "Nota de Remisión Electrónica"
        return "Documento Electrónico"

    @property
    def puede_ser_enviado(self) -> bool:
        """Verifica si el documento puede ser enviado a SIFEN"""
        estado_value = getattr(self, 'estado', None)
        return (
            estado_value == EstadoDocumentoEnum.FIRMADO and
            self.timbrado_vigente and
            bool(getattr(self, 'cdc', None)) and
            bool(getattr(self, 'xml_firmado', None))
        )

    @property
    def esta_aprobado(self) -> bool:
        """Verifica si el documento está aprobado por SIFEN"""
        estado_value = getattr(self, 'estado', None)
        codigo_respuesta = getattr(self, 'codigo_respuesta_sifen', None)
        return (
            estado_value == EstadoDocumentoEnum.APROBADO and
            # Aprobado o Aprobado con observaciones
            codigo_respuesta in ["0260", "1005"]
        )

    def generar_cdc(self, codigo_seguridad: Optional[str] = None) -> str:
        """
        Genera el Código de Control del Documento (CDC) de 44 dígitos

        Args:
            codigo_seguridad: Código de seguridad de 9 dígitos (opcional, se genera automático)

        Returns:
            str: CDC de 44 dígitos
        """
        # Obtener datos de la empresa
        # TODO: Acceder a empresa.ruc_sin_dv y empresa.dv
        ruc_emisor = "12345678"  # Placeholder - debe venir de self.empresa.ruc_sin_dv
        dv_emisor = "9"          # Placeholder - debe venir de self.empresa.dv

        # Componentes del CDC
        tipo_doc = getattr(self, 'tipo_documento',
                           TipoDocumentoEnum.FACTURA).value.zfill(2)
        establecimiento_value = getattr(self, 'establecimiento', '001')
        punto_expedicion_value = getattr(self, 'punto_expedicion', '001')
        numero_value = getattr(self, 'numero_documento', '0000001')

        fecha_emision_value = getattr(self, 'fecha_emision', date.today())
        fecha_str = fecha_emision_value.strftime("%Y%m%d")

        tipo_emision_value = getattr(
            self, 'tipo_emision', TipoEmisionEnum.NORMAL).value

        # Generar código de seguridad si no se proporciona
        if not codigo_seguridad:
            import random
            codigo_seguridad = str(random.randint(100000000, 999999999))

        # Construir CDC sin dígito verificador
        cdc_sin_dv = (
            ruc_emisor.zfill(8) +
            dv_emisor +
            tipo_doc +
            establecimiento_value +
            punto_expedicion_value +
            numero_value +
            fecha_str +
            tipo_emision_value +
            codigo_seguridad.zfill(9)
        )

        # Calcular dígito verificador (algoritmo módulo 11)
        dv_cdc = self._calcular_dv_modulo_11(cdc_sin_dv)

        # CDC completo
        cdc_completo = cdc_sin_dv + str(dv_cdc)

        # Actualizar el campo
        self.cdc = cdc_completo

        return cdc_completo

    def _calcular_dv_modulo_11(self, numero: str) -> int:
        """Calcula dígito verificador usando módulo 11"""
        # Pesos del 2 al 9, cíclicos
        pesos = [2, 3, 4, 5, 6, 7, 8, 9]
        suma = 0

        # Recorrer de derecha a izquierda
        for i, digito in enumerate(reversed(numero)):
            peso = pesos[i % len(pesos)]
            suma += int(digito) * peso

        resto = suma % 11

        if resto < 2:
            return 0
        else:
            return 11 - resto

    def calcular_totales(self) -> dict:
        """
        Calcula todos los totales de la factura

        Returns:
            dict: Diccionario con todos los totales calculados
        """
        # TODO: Calcular basado en items de la factura
        # Por ahora retorna valores actuales

        subtotal_exento_value = getattr(self, 'subtotal_exento', Decimal("0"))
        subtotal_5_value = getattr(self, 'subtotal_gravado_5', Decimal("0"))
        subtotal_10_value = getattr(self, 'subtotal_gravado_10', Decimal("0"))
        total_iva_value = getattr(self, 'total_iva', Decimal("0"))

        if not isinstance(subtotal_exento_value, Decimal):
            subtotal_exento_value = Decimal(str(subtotal_exento_value))
        if not isinstance(subtotal_5_value, Decimal):
            subtotal_5_value = Decimal(str(subtotal_5_value))
        if not isinstance(subtotal_10_value, Decimal):
            subtotal_10_value = Decimal(str(subtotal_10_value))
        if not isinstance(total_iva_value, Decimal):
            total_iva_value = Decimal(str(total_iva_value))

        total_operacion_calc = subtotal_exento_value + \
            subtotal_5_value + subtotal_10_value
        total_general_calc = total_operacion_calc + total_iva_value

        return {
            "subtotal_exento": subtotal_exento_value,
            "subtotal_gravado_5": subtotal_5_value,
            "subtotal_gravado_10": subtotal_10_value,
            "total_iva": total_iva_value,
            "total_operacion": total_operacion_calc,
            "total_general": total_general_calc
        }

    def actualizar_estado(self, nuevo_estado: EstadoDocumentoEnum, codigo_respuesta: Optional[str] = None, mensaje: Optional[str] = None) -> None:
        """
        Actualiza el estado del documento

        Args:
            nuevo_estado: Nuevo estado del documento
            codigo_respuesta: Código de respuesta de SIFEN (opcional)
            mensaje: Mensaje descriptivo (opcional)
        """
        self.estado = nuevo_estado

        if codigo_respuesta:
            self.codigo_respuesta_sifen = codigo_respuesta

        if mensaje:
            self.mensaje_sifen = mensaje

        # Actualizar timestamps según el estado
        if nuevo_estado == EstadoDocumentoEnum.ENVIADO:
            self.fecha_envio_sifen = datetime.now()
        elif nuevo_estado in [EstadoDocumentoEnum.APROBADO, EstadoDocumentoEnum.RECHAZADO]:
            self.fecha_respuesta_sifen = datetime.now()

    def to_dict_sifen(self) -> dict:
        """Retorna datos en formato requerido por SIFEN"""
        tipo_documento_value = getattr(self, 'tipo_documento', None)
        tipo_operacion_value = getattr(self, 'tipo_operacion', None)
        condicion_operacion_value = getattr(self, 'condicion_operacion', None)
        moneda_value = getattr(self, 'moneda', None)
        tipo_emision_value = getattr(self, 'tipo_emision', None)

        return {
            "cdc": getattr(self, 'cdc', ''),
            "tipo_documento": tipo_documento_value.value if tipo_documento_value else "1",
            "numero_completo": self.numero_completo,
            "establecimiento": getattr(self, 'establecimiento', '001'),
            "punto_expedicion": getattr(self, 'punto_expedicion', '001'),
            "numero_documento": getattr(self, 'numero_documento', '0000001'),
            "numero_timbrado": getattr(self, 'numero_timbrado', ''),
            "fecha_emision": getattr(self, 'fecha_emision', date.today()).isoformat(),
            "tipo_emision": tipo_emision_value.value if tipo_emision_value else "1",
            "tipo_operacion": tipo_operacion_value.value if tipo_operacion_value else "1",
            "condicion_operacion": condicion_operacion_value.value if condicion_operacion_value else "1",
            "moneda": moneda_value.value if moneda_value else "PYG",
            "tipo_cambio": float(getattr(self, 'tipo_cambio', Decimal("1.0000"))),
            "totales": self.calcular_totales(),
            "estado": getattr(self, 'estado', EstadoDocumentoEnum.BORRADOR).value,
            "observaciones": getattr(self, 'observaciones', ''),
            "motivo_emision": getattr(self, 'motivo_emision', '')
        }


# ===============================================
# ACTUALIZACIÓN: backend/app/models/__init__.py
# ===============================================

"""
Agregar al final del archivo __init__.py:

from .factura import (
    Factura,
    TipoDocumentoEnum,
    TipoEmisionEnum,
    EstadoDocumentoEnum,
    TipoOperacionEnum,
    CondicionOperacionEnum,
    MonedaEnum
)

__all__ = [
    "BaseModel",
    "User", 
    "Empresa",
    "Cliente",
    "TipoClienteEnum",
    "TipoDocumentoEnum",
    "Producto",
    "TipoProductoEnum",
    "AfectacionIvaEnum", 
    "UnidadMedidaEnum",
    "Factura",
    "TipoDocumentoEnum",
    "TipoEmisionEnum",
    "EstadoDocumentoEnum",
    "TipoOperacionEnum",
    "CondicionOperacionEnum",
    "MonedaEnum"
]
"""
