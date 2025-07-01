# ===============================================
# ARCHIVO: backend/app/models/documento.py
# PROPÓSITO: Modelo base padre para documentos electrónicos SIFEN
# VERSIÓN: 1.0.0 - Compatible con SIFEN v150
# ===============================================

from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, Date, DateTime, Numeric
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
from datetime import datetime, date
import re
from typing import Optional
from decimal import Decimal
import enum


class TipoDocumentoSifenEnum(enum.Enum):
    """Tipos de documentos electrónicos según SIFEN v150"""
    FACTURA = "1"                    # Factura Electrónica (FE)
    AUTOFACTURA = "4"               # Autofactura Electrónica (AFE)
    NOTA_CREDITO = "5"              # Nota de Crédito Electrónica (NCE)
    NOTA_DEBITO = "6"               # Nota de Débito Electrónica (NDE)
    NOTA_REMISION = "7"             # Nota de Remisión Electrónica (NRE)


class TipoEmisionSifenEnum(enum.Enum):
    """Tipos de emisión según SIFEN v150"""
    NORMAL = "1"                    # Emisión normal
    CONTINGENCIA = "2"              # Emisión de contingencia


class EstadoDocumentoSifenEnum(enum.Enum):
    """Estados del documento en el flujo SIFEN completo"""
    BORRADOR = "borrador"           # En construcción, datos incompletos
    VALIDADO = "validado"           # Datos validados, listo para generar XML
    GENERADO = "generado"           # XML generado, listo para firmar
    FIRMADO = "firmado"            # Firmado digitalmente, listo para envío
    ENVIADO = "enviado"            # Enviado a SIFEN, esperando respuesta
    APROBADO = "aprobado"          # Aprobado por SIFEN (código 0260)
    # Aprobado con observaciones (código 1005)
    APROBADO_OBSERVACION = "aprobado_observacion"
    RECHAZADO = "rechazado"        # Rechazado por SIFEN
    ERROR_ENVIO = "error_envio"    # Error en el envío
    CANCELADO = "cancelado"        # Cancelado por usuario
    ANULADO = "anulado"           # Anulado oficialmente


class MonedaSifenEnum(enum.Enum):
    """Monedas soportadas por SIFEN"""
    PYG = "PYG"                    # Guaraní paraguayo
    USD = "USD"                    # Dólar estadounidense
    EUR = "EUR"                    # Euro
    BRL = "BRL"                    # Real brasileño
    ARS = "ARS"                    # Peso argentino


class TipoOperacionSifenEnum(enum.Enum):
    """Tipos de operación comercial según SIFEN"""
    VENTA = "1"                    # Venta de bienes/servicios
    EXPORTACION = "2"              # Exportación
    IMPORTACION = "3"              # Importación (para autofacturas)
    OTRO = "4"                     # Otras operaciones


class CondicionOperacionSifenEnum(enum.Enum):
    """Condiciones de pago de la operación"""
    CONTADO = "1"                  # Pago al contado
    CREDITO = "2"                  # Pago a crédito
    OTRO = "9"                     # Otra condición


class Documento(BaseModel):
    """
    Modelo base padre para todos los documentos electrónicos SIFEN.

    Esta clase abstracta contiene todos los campos comunes que comparten
    los diferentes tipos de documentos electrónicos:
    - Factura Electrónica (FE)
    - Autofactura Electrónica (AFE)  
    - Nota de Crédito Electrónica (NCE)
    - Nota de Débito Electrónica (NDE)
    - Nota de Remisión Electrónica (NRE)

    Implementa la funcionalidad común:
    - Generación de CDC (Código de Control del Documento)
    - Gestión de estados en el flujo SIFEN
    - Validaciones básicas según normativa SET
    - Cálculos fiscales comunes
    - Integración con servicios SIFEN
    """

    # === DISCRIMINADOR DE HERENCIA ===
    tipo_documento = Column(
        String(1),
        nullable=False,
        doc="Tipo de documento SIFEN (1=FE, 4=AFE, 5=NCE, 6=NDE, 7=NRE)"
    )

    # SQLAlchemy herencia - definir el discriminador
    __mapper_args__ = {
        'polymorphic_identity': 'documento',
        'polymorphic_on': tipo_documento
    }

    # === IDENTIFICACIÓN SIFEN ===
    cdc = Column(
        String(44),
        unique=True,
        index=True,
        doc="Código de Control del Documento SIFEN (44 dígitos)"
    )

    version_formato = Column(
        String(3),
        default="150",
        doc="Versión del formato SIFEN (150)"
    )

    # === NUMERACIÓN FISCAL ===
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
        doc="Número secuencial del documento (0000001-9999999)"
    )

    # === TIMBRADO FISCAL ===
    numero_timbrado = Column(
        String(8),
        nullable=False,
        doc="Número de timbrado SET"
    )

    fecha_inicio_vigencia_timbrado = Column(
        Date,
        nullable=False,
        doc="Fecha inicio vigencia del timbrado"
    )

    fecha_fin_vigencia_timbrado = Column(
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

    fecha_hora_emision = Column(
        DateTime,
        default=datetime.now,
        doc="Fecha y hora de emisión (timestamp completo)"
    )

    tipo_emision = Column(
        String(1),
        nullable=False,
        default="1",
        doc="Tipo de emisión (1=Normal, 2=Contingencia)"
    )

    # === INFORMACIÓN COMERCIAL ===
    tipo_operacion = Column(
        String(1),
        nullable=False,
        default="1",
        doc="Tipo de operación (1=Venta, 2=Exportación, etc.)"
    )

    condicion_operacion = Column(
        String(1),
        nullable=False,
        default="1",
        doc="Condición de pago (1=Contado, 2=Crédito)"
    )

    descripcion_operacion = Column(
        Text,
        doc="Descripción de la operación comercial"
    )

    # === MONEDA Y CAMBIO ===
    moneda = Column(
        String(3),
        nullable=False,
        default="PYG",
        doc="Código de moneda ISO (PYG, USD, EUR, etc.)"
    )

    tipo_cambio = Column(
        Numeric(10, 4),
        default=Decimal("1.0000"),
        doc="Tipo de cambio aplicado"
    )

    # === TOTALES CALCULADOS ===
    subtotal_exento = Column(
        Numeric(15, 4),
        default=Decimal("0.0000"),
        doc="Subtotal exento de IVA"
    )

    subtotal_exonerado = Column(
        Numeric(15, 4),
        default=Decimal("0.0000"),
        doc="Subtotal exonerado de IVA"
    )

    subtotal_gravado_5 = Column(
        Numeric(15, 4),
        default=Decimal("0.0000"),
        doc="Subtotal gravado al 5%"
    )

    subtotal_gravado_10 = Column(
        Numeric(15, 4),
        default=Decimal("0.0000"),
        doc="Subtotal gravado al 10%"
    )

    total_iva = Column(
        Numeric(15, 4),
        default=Decimal("0.0000"),
        doc="Total IVA liquidado"
    )

    total_operacion = Column(
        Numeric(15, 4),
        default=Decimal("0.0000"),
        doc="Total de la operación sin IVA"
    )

    total_general = Column(
        Numeric(15, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Total general del documento"
    )

    # === ESTADO Y PROCESAMIENTO SIFEN ===
    estado = Column(
        String(25),
        nullable=False,
        default="borrador",
        doc="Estado actual del documento en el flujo"
    )

    codigo_respuesta_sifen = Column(
        String(10),
        doc="Código de respuesta de SIFEN (0260=Aprobado, etc.)"
    )

    mensaje_sifen = Column(
        Text,
        doc="Mensaje descriptivo de SIFEN"
    )

    numero_protocolo = Column(
        String(50),
        doc="Número de protocolo asignado por SIFEN"
    )

    url_consulta_publica = Column(
        String(200),
        doc="URL para consulta pública del documento"
    )

    # === TIMESTAMPS DEL FLUJO ===
    fecha_generacion_xml = Column(
        DateTime,
        doc="Fecha y hora de generación del XML"
    )

    fecha_firma_digital = Column(
        DateTime,
        doc="Fecha y hora de firma digital"
    )

    fecha_envio_sifen = Column(
        DateTime,
        doc="Fecha y hora de envío a SIFEN"
    )

    fecha_respuesta_sifen = Column(
        DateTime,
        doc="Fecha y hora de respuesta de SIFEN"
    )

    # === CONTENIDO XML Y FIRMA ===
    xml_generado = Column(
        Text,
        doc="XML del documento generado"
    )

    xml_firmado = Column(
        Text,
        doc="XML con firma digital aplicada"
    )

    hash_documento = Column(
        String(64),
        doc="Hash SHA-256 del documento firmado"
    )

    codigo_qr = Column(
        Text,
        doc="Código QR para consulta pública"
    )

    # === INFORMACIÓN ADICIONAL ===
    motivo_emision = Column(
        String(500),
        doc="Motivo o descripción de la emisión"
    )

    observaciones = Column(
        Text,
        doc="Observaciones adicionales del documento"
    )

    observaciones_sifen = Column(
        Text,
        doc="Observaciones devueltas por SIFEN"
    )

    datos_adicionales = Column(
        Text,
        doc="Datos adicionales en formato JSON"
    )

    # === CONTROL INTERNO ===
    usuario_creacion = Column(
        String(100),
        doc="Usuario que creó el documento"
    )

    usuario_modificacion = Column(
        String(100),
        doc="Usuario que modificó por última vez"
    )

    ip_creacion = Column(
        String(45),
        doc="IP desde donde se creó"
    )

    # === RELACIONES ===
    empresa_id = Column(
        Integer,
        ForeignKey('empresa.id'),
        nullable=False,
        doc="Empresa emisora del documento"
    )
    # empresa = relationship("Empresa", back_populates="documentos")

    cliente_id = Column(
        Integer,
        ForeignKey('cliente.id'),
        nullable=False,
        doc="Cliente receptor del documento"
    )
    # cliente = relationship("Cliente", back_populates="documentos_recibidos")

    timbrado_id = Column(
        Integer,
        ForeignKey('timbrado.id'),
        nullable=False,
        doc="Timbrado utilizado para el documento"
    )
    # timbrado = relationship("Timbrado", back_populates="documentos")

    # Relaciones futuras (comentadas para no crear dependencias aún)
    # items = relationship("ItemDocumento", back_populates="documento", cascade="all, delete-orphan")
    # documentos_asociados = relationship("DocumentoAsociado", back_populates="documento_origen")
    # eventos = relationship("EventoDocumento", back_populates="documento")

    @validates('tipo_documento')
    def validate_tipo_documento(self, key: str, value: str) -> str:
        """Validar tipo de documento SIFEN"""
        if value not in ["1", "4", "5", "6", "7"]:
            raise ValueError("Tipo documento debe ser 1, 4, 5, 6 o 7")
        return value

    @validates('establecimiento', 'punto_expedicion')
    def validate_codigo_3_digitos(self, key: str, value: str) -> str:
        """Validar códigos de 3 dígitos para establecimiento y punto expedición"""
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
        """Validar número de timbrado SET"""
        if not value:
            raise ValueError("Número de timbrado es requerido")

        clean_timbrado = value.strip()
        if not re.match(r'^\d{1,8}$', clean_timbrado):
            raise ValueError("Timbrado debe tener entre 1 y 8 dígitos")

        return clean_timbrado

    @validates('cdc')
    def validate_cdc(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validar formato CDC de 44 dígitos"""
        if value:
            clean_cdc = value.strip()
            if not re.match(r'^\d{44}$', clean_cdc):
                raise ValueError(
                    "CDC debe tener exactamente 44 dígitos numéricos")
            return clean_cdc
        return value

    @validates('moneda')
    def validate_moneda(self, key: str, value: str) -> str:
        """Validar código de moneda ISO"""
        if value not in ["PYG", "USD", "EUR", "BRL", "ARS", "CLP", "UYU"]:
            raise ValueError("Moneda debe ser un código ISO válido")
        return value.upper()

    @validates('tipo_emision', 'tipo_operacion', 'condicion_operacion')
    def validate_codigos_sifen(self, key: str, value: str) -> str:
        """Validar códigos SIFEN de 1 dígito"""
        if not value or not re.match(r'^\d{1}$', value):
            raise ValueError(f"{key} debe ser un dígito del 1-9")
        return value

    def __repr__(self) -> str:
        numero = getattr(self, 'numero_documento', 'unknown')
        tipo_value = getattr(self, 'tipo_documento', 'unknown')
        estado_value = getattr(self, 'estado', 'unknown')
        return f"<Documento(id={self.id}, tipo='{tipo_value}', numero='{numero}', estado='{estado_value}')>"

    @property
    def numero_completo(self) -> str:
        """Retorna numeración completa: EST-PEX-NUMERO"""
        establecimiento_value = getattr(self, 'establecimiento', '001')
        punto_expedicion_value = getattr(self, 'punto_expedicion', '001')
        numero_value = getattr(self, 'numero_documento', '0000001')

        return f"{establecimiento_value}-{punto_expedicion_value}-{numero_value}"

    @property
    def descripcion_tipo_documento(self) -> str:
        """Retorna descripción del tipo de documento"""
        tipo_value = getattr(self, 'tipo_documento', '')

        descripciones = {
            "1": "Factura Electrónica",
            "4": "Autofactura Electrónica",
            "5": "Nota de Crédito Electrónica",
            "6": "Nota de Débito Electrónica",
            "7": "Nota de Remisión Electrónica"
        }

        return descripciones.get(tipo_value, "Documento Electrónico")

    @property
    def esta_vigente_timbrado(self) -> bool:
        """Verifica si el timbrado está vigente para la fecha de emisión"""
        fecha_inicio = getattr(self, 'fecha_inicio_vigencia_timbrado', None)
        fecha_fin = getattr(self, 'fecha_fin_vigencia_timbrado', None)
        fecha_emision_value = getattr(self, 'fecha_emision', date.today())

        if not fecha_inicio or not fecha_fin:
            return False

        return fecha_inicio <= fecha_emision_value <= fecha_fin

    @property
    def puede_ser_enviado(self) -> bool:
        """Verifica si el documento puede ser enviado a SIFEN"""
        estado_value = getattr(self, 'estado', '')

        return (
            estado_value == EstadoDocumentoSifenEnum.FIRMADO.value and
            self.esta_vigente_timbrado and
            bool(getattr(self, 'cdc', None)) and
            bool(getattr(self, 'xml_firmado', None))
        )

    @property
    def esta_aprobado(self) -> bool:
        """Verifica si el documento está aprobado por SIFEN"""
        estado_value = getattr(self, 'estado', '')
        codigo_respuesta = getattr(self, 'codigo_respuesta_sifen', '')

        return (
            estado_value in [EstadoDocumentoSifenEnum.APROBADO.value,
                             EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value] and
            codigo_respuesta in ["0260", "1005"]
        )

    @property
    def es_documento_fiscal(self) -> bool:
        """Verifica si es un documento con validez fiscal"""
        return self.esta_aprobado and bool(getattr(self, 'numero_protocolo', None))

    def generar_cdc(self, codigo_seguridad: Optional[str] = None) -> str:
        """
        Genera el Código de Control del Documento (CDC) de 44 dígitos

        Args:
            codigo_seguridad: Código de seguridad de 9 dígitos (opcional, se genera automático)

        Returns:
            str: CDC de 44 dígitos
        """
        # TODO: Obtener datos de empresa relacionada
        ruc_emisor = "12345678"  # Placeholder - debe venir de self.empresa.ruc_sin_dv
        dv_emisor = "9"          # Placeholder - debe venir de self.empresa.dv

        # Componentes del CDC
        tipo_doc = getattr(self, 'tipo_documento', '1').zfill(2)
        establecimiento_value = getattr(self, 'establecimiento', '001')
        punto_expedicion_value = getattr(self, 'punto_expedicion', '001')
        numero_value = getattr(self, 'numero_documento', '0000001')

        fecha_emision_value = getattr(self, 'fecha_emision', date.today())
        fecha_str = fecha_emision_value.strftime("%Y%m%d")

        tipo_emision_value = getattr(self, 'tipo_emision', '1')

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
        """Calcula dígito verificador usando módulo 11 (algoritmo SET)"""
        pesos = [2, 3, 4, 5, 6, 7, 8, 9]
        suma = 0

        for i, digito in enumerate(reversed(numero)):
            peso = pesos[i % len(pesos)]
            suma += int(digito) * peso

        resto = suma % 11

        if resto < 2:
            return 0
        else:
            return 11 - resto

    def actualizar_estado(self, nuevo_estado: str,
                          codigo_respuesta: Optional[str] = None,
                          mensaje: Optional[str] = None,
                          numero_protocolo: Optional[str] = None) -> None:
        """
        Actualiza el estado del documento con información adicional

        Args:
            nuevo_estado: Nuevo estado del documento
            codigo_respuesta: Código de respuesta SIFEN (opcional)
            mensaje: Mensaje descriptivo (opcional)
            numero_protocolo: Número de protocolo SIFEN (opcional)
        """
        self.estado = nuevo_estado

        if codigo_respuesta:
            self.codigo_respuesta_sifen = codigo_respuesta

        if mensaje:
            self.mensaje_sifen = mensaje

        if numero_protocolo:
            self.numero_protocolo = numero_protocolo

        # Actualizar timestamps según el estado
        now = datetime.now()

        if nuevo_estado == EstadoDocumentoSifenEnum.GENERADO.value:
            self.fecha_generacion_xml = now
        elif nuevo_estado == EstadoDocumentoSifenEnum.FIRMADO.value:
            self.fecha_firma_digital = now
        elif nuevo_estado == EstadoDocumentoSifenEnum.ENVIADO.value:
            self.fecha_envio_sifen = now
        elif nuevo_estado in [EstadoDocumentoSifenEnum.APROBADO.value,
                              EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value,
                              EstadoDocumentoSifenEnum.RECHAZADO.value]:
            self.fecha_respuesta_sifen = now

    def calcular_totales(self) -> dict:
        """
        Calcula todos los totales del documento

        Returns:
            dict: Diccionario con todos los totales calculados
        """
        # TODO: Calcular basado en items del documento
        # Por ahora retorna valores actuales de las columnas

        def get_decimal_value(field_name: str) -> Decimal:
            value = getattr(self, field_name, Decimal("0"))
            if not isinstance(value, Decimal):
                value = Decimal(str(value))
            return value

        subtotal_exento = get_decimal_value('subtotal_exento')
        subtotal_exonerado = get_decimal_value('subtotal_exonerado')
        subtotal_5 = get_decimal_value('subtotal_gravado_5')
        subtotal_10 = get_decimal_value('subtotal_gravado_10')
        total_iva = get_decimal_value('total_iva')

        total_operacion_calc = subtotal_exento + \
            subtotal_exonerado + subtotal_5 + subtotal_10
        total_general_calc = total_operacion_calc + total_iva

        return {
            "subtotal_exento": subtotal_exento,
            "subtotal_exonerado": subtotal_exonerado,
            "subtotal_gravado_5": subtotal_5,
            "subtotal_gravado_10": subtotal_10,
            "total_iva": total_iva,
            "total_operacion": total_operacion_calc,
            "total_general": total_general_calc,
            "moneda": getattr(self, 'moneda', 'PYG'),
            "tipo_cambio": get_decimal_value('tipo_cambio')
        }

    def to_dict_sifen(self) -> dict:
        """Retorna datos en formato requerido por SIFEN"""
        return {
            "cdc": getattr(self, 'cdc', ''),
            "version_formato": getattr(self, 'version_formato', '150'),
            "tipo_documento": getattr(self, 'tipo_documento', '1'),
            "descripcion_tipo": self.descripcion_tipo_documento,
            "numero_completo": self.numero_completo,
            "establecimiento": getattr(self, 'establecimiento', '001'),
            "punto_expedicion": getattr(self, 'punto_expedicion', '001'),
            "numero_documento": getattr(self, 'numero_documento', '0000001'),
            "numero_timbrado": getattr(self, 'numero_timbrado', ''),
            "fecha_emision": getattr(self, 'fecha_emision', date.today()).isoformat(),
            "fecha_hora_emision": getattr(self, 'fecha_hora_emision', datetime.now()).isoformat(),
            "tipo_emision": getattr(self, 'tipo_emision', '1'),
            "tipo_operacion": getattr(self, 'tipo_operacion', '1'),
            "condicion_operacion": getattr(self, 'condicion_operacion', '1'),
            "moneda": getattr(self, 'moneda', 'PYG'),
            "tipo_cambio": float(getattr(self, 'tipo_cambio', Decimal("1.0000"))),
            "totales": self.calcular_totales(),
            "estado": getattr(self, 'estado', 'borrador'),
            "esta_vigente_timbrado": self.esta_vigente_timbrado,
            "puede_ser_enviado": self.puede_ser_enviado,
            "esta_aprobado": self.esta_aprobado,
            "es_documento_fiscal": self.es_documento_fiscal,
            "motivo_emision": getattr(self, 'motivo_emision', ''),
            "observaciones": getattr(self, 'observaciones', ''),
            "url_consulta_publica": getattr(self, 'url_consulta_publica', '')
        }

    def get_resumen_completo(self) -> dict:
        """Retorna resumen completo del estado del documento"""
        return {
            "identificacion": {
                "cdc": getattr(self, 'cdc', ''),
                "tipo_documento": self.descripcion_tipo_documento,
                "numero_completo": self.numero_completo,
                "fecha_emision": getattr(self, 'fecha_emision', date.today()).isoformat()
            },
            "estado_actual": {
                "estado": getattr(self, 'estado', 'unknown'),
                "puede_ser_enviado": self.puede_ser_enviado,
                "esta_aprobado": self.esta_aprobado,
                "es_documento_fiscal": self.es_documento_fiscal
            },
            "sifen": {
                "codigo_respuesta": getattr(self, 'codigo_respuesta_sifen', ''),
                "mensaje": getattr(self, 'mensaje_sifen', ''),
                "numero_protocolo": getattr(self, 'numero_protocolo', ''),
                "url_consulta": getattr(self, 'url_consulta_publica', '')
            },
            "totales": self.calcular_totales(),
            "timbrado": {
                "numero": getattr(self, 'numero_timbrado', ''),
                "esta_vigente": self.esta_vigente_timbrado,
                "fecha_inicio": getattr(self, 'fecha_inicio_vigencia_timbrado', None),
                "fecha_fin": getattr(self, 'fecha_fin_vigencia_timbrado', None)
            },
            "timestamps": {
                "generacion_xml": getattr(self, 'fecha_generacion_xml', None),
                "firma_digital": getattr(self, 'fecha_firma_digital', None),
                "envio_sifen": getattr(self, 'fecha_envio_sifen', None),
                "respuesta_sifen": getattr(self, 'fecha_respuesta_sifen', None)
            }
        }


# ===============================================
# MODELOS HIJOS - Herencia de Documento
# ===============================================

class FacturaElectronica(Documento):
    """
    Factura Electrónica (FE) - Tipo 1
    Hereda de Documento y especializa para facturas de venta
    """

    __mapper_args__ = {
        'polymorphic_identity': '1'
    }

    # Campos específicos de facturas (si los hay)
    # Por ejemplo: forma_pago, plazo_credito, etc.


class AutofacturaElectronica(Documento):
    """
    Autofactura Electrónica (AFE) - Tipo 4
    Hereda de Documento y especializa para autofacturas (importaciones)
    """

    __mapper_args__ = {
        'polymorphic_identity': '4'
    }

    # Campos específicos de autofacturas
    # Por ejemplo: datos_importacion, aduana, etc.


class NotaCreditoElectronica(Documento):
    """
    Nota de Crédito Electrónica (NCE) - Tipo 5
    Hereda de Documento y especializa para notas de crédito
    """

    __mapper_args__ = {
        'polymorphic_identity': '5'
    }

    # Relación con documento original
    documento_original_cdc = Column(
        String(44),
        doc="CDC del documento original que se está creditando"
    )

    motivo_credito = Column(
        Text,
        doc="Motivo específico de la nota de crédito"
    )


class NotaDebitoElectronica(Documento):
    """
    Nota de Débito Electrónica (NDE) - Tipo 6
    Hereda de Documento y especializa para notas de débito
    """

    __mapper_args__ = {
        'polymorphic_identity': '6'
    }

    # Relación con documento original
    documento_original_cdc = Column(
        String(44),
        doc="CDC del documento original que se está debitando"
    )

    motivo_debito = Column(
        Text,
        doc="Motivo específico de la nota de débito"
    )


class NotaRemisionElectronica(Documento):
    """
    Nota de Remisión Electrónica (NRE) - Tipo 7
    Hereda de Documento y especializa para notas de remisión
    """

    __mapper_args__ = {
        'polymorphic_identity': '7'
    }

    # Campos específicos de remisión
    motivo_traslado = Column(
        String(500),
        doc="Motivo del traslado de mercaderías"
    )

    fecha_inicio_traslado = Column(
        Date,
        doc="Fecha de inicio del traslado"
    )

    fecha_fin_traslado = Column(
        Date,
        doc="Fecha estimada de finalización del traslado"
    )

    transportista_ruc = Column(
        String(20),
        doc="RUC del transportista"
    )

    transportista_nombre = Column(
        String(200),
        doc="Nombre del transportista"
    )


# ===============================================
# EJEMPLO DE USO - Factorías para crear documentos
# ===============================================

def crear_factura_electronica(**kwargs) -> FacturaElectronica:
    """Factory para crear facturas electrónicas"""
    defaults = {
        'tipo_documento': '1',
        'tipo_operacion': '1',  # Venta
        'condicion_operacion': '1',  # Contado
        'estado': EstadoDocumentoSifenEnum.BORRADOR.value
    }
    defaults.update(kwargs)
    return FacturaElectronica(**defaults)


def crear_nota_credito(**kwargs) -> NotaCreditoElectronica:
    """Factory para crear notas de crédito"""
    defaults = {
        'tipo_documento': '5',
        'tipo_operacion': '1',
        'condicion_operacion': '1',
        'estado': EstadoDocumentoSifenEnum.BORRADOR.value
    }
    defaults.update(kwargs)
    return NotaCreditoElectronica(**defaults)


def crear_nota_remision(**kwargs) -> NotaRemisionElectronica:
    """Factory para crear notas de remisión"""
    defaults = {
        'tipo_documento': '7',
        'tipo_operacion': '1',
        'condicion_operacion': '1',
        'total_general': Decimal("0.0000"),  # NRE siempre en 0
        'estado': EstadoDocumentoSifenEnum.BORRADOR.value
    }
    defaults.update(kwargs)
    return NotaRemisionElectronica(**defaults)
