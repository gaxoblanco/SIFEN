# ===============================================
# ARCHIVO: backend/app/models/timbrado.py
# PROPÓSITO: Gestión de timbrados fiscales SET Paraguay
# VERSIÓN: 1.0.0 - Compatible con SIFEN v150
# ===============================================

from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, Date, Numeric
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
from datetime import date, timedelta
import re
from typing import Optional
from decimal import Decimal
import enum


class EstadoTimbradoEnum(enum.Enum):
    """Estados del timbrado"""
    ACTIVO = "activo"              # Timbrado vigente y en uso
    INACTIVO = "inactivo"          # Timbrado no en uso pero válido
    VENCIDO = "vencido"            # Timbrado fuera de vigencia
    AGOTADO = "agotado"            # Numeración agotada
    CANCELADO = "cancelado"        # Cancelado manualmente


class TipoTimbradoEnum(enum.Enum):
    """Tipos de timbrado según SET"""
    ELECTRONICO = "1"              # Timbrado electrónico SIFEN
    IMPRESO = "2"                  # Timbrado para documentos impresos
    CONTINGENCIA = "3"             # Timbrado de contingencia


class Timbrado(BaseModel):
    """
    Gestión de timbrados fiscales autorizados por la SET Paraguay.

    Modelo que administra los timbrados fiscales que habilitan a los 
    contribuyentes para emitir documentos electrónicos y físicos.

    Incluye:
    - Numeración automática por establecimiento y punto expedición
    - Control de vigencia temporal
    - Seguimiento de numeración utilizada
    - Validaciones específicas SET
    - Alertas de vencimiento y agotamiento
    """

    # === IDENTIFICACIÓN FISCAL ===
    numero_timbrado = Column(
        String(8),
        nullable=False,
        unique=True,
        index=True,
        doc="Número de timbrado asignado por SET (1-8 dígitos)"
    )

    tipo_timbrado = Column(
        String(1),
        nullable=False,
        default="1",
        doc="Tipo de timbrado según SET (1=Electrónico, 2=Impreso, 3=Contingencia)"
    )

    descripcion_tipo = Column(
        String(100),
        default="Timbrado electrónico SET",
        doc="Descripción del tipo de timbrado"
    )

    # === UBICACIÓN FISCAL ===
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

    # === VIGENCIA TEMPORAL ===
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

    # === NUMERACIÓN AUTORIZADA ===
    numero_desde = Column(
        String(7),
        nullable=False,
        default="0000001",
        doc="Número inicial autorizado (0000001)"
    )

    numero_hasta = Column(
        String(7),
        nullable=False,
        default="9999999",
        doc="Número final autorizado (9999999)"
    )

    ultimo_numero_usado = Column(
        String(7),
        default="0000000",
        doc="Último número utilizado del timbrado"
    )

    # === CONFIGURACIÓN NUMÉRICA ===
    incremento = Column(
        Integer,
        default=1,
        doc="Incremento de numeración (normalmente 1)"
    )

    # === OBSERVACIONES Y NOTAS ===
    observaciones = Column(
        Text,
        doc="Observaciones adicionales del timbrado"
    )

    resolucion_set = Column(
        String(50),
        doc="Número de resolución SET que autoriza el timbrado"
    )

    motivo_solicitud = Column(
        Text,
        doc="Motivo por el cual se solicitó el timbrado"
    )

    # === ESTADO Y CONTROL ===
    estado = Column(
        String(20),
        nullable=False,
        default="activo",
        doc="Estado actual del timbrado"
    )

    is_default = Column(
        Boolean,
        default=False,
        doc="Timbrado por defecto para la empresa"
    )

    alertar_vencimiento = Column(
        Boolean,
        default=True,
        doc="Alertar antes del vencimiento"
    )

    dias_alerta_vencimiento = Column(
        Integer,
        default=30,
        doc="Días antes del vencimiento para alertar"
    )

    alertar_agotamiento = Column(
        Boolean,
        default=True,
        doc="Alertar cuando queden pocos números"
    )

    numeros_alerta_agotamiento = Column(
        Integer,
        default=100,
        doc="Cantidad de números restantes para alertar"
    )

    # === RELACIONES ===
    empresa_id = Column(
        Integer,
        ForeignKey('empresa.id'),
        nullable=False,
        doc="Empresa propietaria del timbrado"
    )
    # empresa = relationship("Empresa", back_populates="timbrados")

    # Relaciones futuras (comentadas para no crear dependencias aún)
    # facturas = relationship("Factura", back_populates="timbrado")
    # documentos = relationship("Documento", back_populates="timbrado")

    @validates('numero_timbrado')
    def validate_numero_timbrado(self, key: str, value: str) -> str:
        """Validar número de timbrado SET"""
        if not value:
            raise ValueError("Número de timbrado es requerido")

        # Limpiar espacios
        clean_timbrado = value.strip()

        # Validar formato: 1-8 dígitos numéricos
        if not re.match(r'^\d{1,8}$', clean_timbrado):
            raise ValueError(
                "Timbrado debe tener entre 1 y 8 dígitos numéricos")

        return clean_timbrado

    @validates('establecimiento', 'punto_expedicion')
    def validate_codigo_3_digitos(self, key: str, value: str) -> str:
        """Validar códigos de establecimiento y punto expedición"""
        if not value:
            raise ValueError(f"{key} es requerido")

        try:
            num = int(value)
            if num < 1 or num > 999:
                raise ValueError(f"{key} debe estar entre 001 y 999")
            return str(num).zfill(3)  # Completar con ceros
        except ValueError:
            raise ValueError(f"{key} debe ser numérico")

    @validates('numero_desde', 'numero_hasta', 'ultimo_numero_usado')
    def validate_numeracion(self, key: str, value: str) -> str:
        """Validar números de documentos (7 dígitos)"""
        if not value:
            if key == 'ultimo_numero_usado':
                return "0000000"  # Default para último usado
            raise ValueError(f"{key} es requerido")

        try:
            num = int(value)
            if num < 0 or num > 9999999:
                raise ValueError(f"{key} debe estar entre 0000000 y 9999999")
            return str(num).zfill(7)  # Completar con ceros
        except ValueError:
            raise ValueError(f"{key} debe ser numérico")

    @validates('fecha_inicio_vigencia', 'fecha_fin_vigencia')
    def validate_fechas_vigencia(self, key: str, value: date) -> date:
        """Validar fechas de vigencia"""
        if not value:
            raise ValueError(f"{key} es requerida")

        # Validar que las fechas no sean muy antiguas (más de 20 años)
        fecha_limite_pasado = date.today() - timedelta(days=7300)  # 20 años
        fecha_limite_futuro = date.today() + timedelta(days=3650)   # 10 años al futuro

        if value < fecha_limite_pasado:
            raise ValueError(f"{key} no puede ser anterior a 20 años")

        if value > fecha_limite_futuro:
            raise ValueError(f"{key} no puede ser posterior a 10 años")

        return value

    @validates('tipo_timbrado')
    def validate_tipo_timbrado(self, key: str, value: str) -> str:
        """Validar tipo de timbrado"""
        if value not in ["1", "2", "3"]:
            raise ValueError(
                "Tipo timbrado debe ser 1 (Electrónico), 2 (Impreso) o 3 (Contingencia)")
        return value

    def __repr__(self) -> str:
        numero = getattr(self, 'numero_timbrado', 'unknown')
        estado_value = getattr(self, 'estado', 'unknown')
        return f"<Timbrado(id={self.id}, numero='{numero}', estado='{estado_value}')>"

    @property
    def codigo_completo(self) -> str:
        """Retorna código completo: TIMBRADO-EST-PEX"""
        numero_value = getattr(self, 'numero_timbrado', '')
        establecimiento_value = getattr(self, 'establecimiento', '001')
        punto_expedicion_value = getattr(self, 'punto_expedicion', '001')

        return f"{numero_value}-{establecimiento_value}-{punto_expedicion_value}"

    @property
    def esta_vigente(self) -> bool:
        """Verifica si el timbrado está dentro del período de vigencia"""
        fecha_inicio = getattr(self, 'fecha_inicio_vigencia', None)
        fecha_fin = getattr(self, 'fecha_fin_vigencia', None)

        if not fecha_inicio or not fecha_fin:
            return False

        hoy = date.today()
        return fecha_inicio <= hoy <= fecha_fin

    @property
    def dias_para_vencer(self) -> int:
        """Retorna días restantes hasta el vencimiento"""
        fecha_fin = getattr(self, 'fecha_fin_vigencia', None)

        if not fecha_fin:
            return -1

        delta = fecha_fin - date.today()
        return delta.days

    @property
    def numeros_disponibles(self) -> int:
        """Retorna cantidad de números disponibles"""
        numero_hasta_value = getattr(self, 'numero_hasta', '9999999')
        ultimo_usado_value = getattr(self, 'ultimo_numero_usado', '0000000')

        try:
            hasta = int(numero_hasta_value)
            ultimo = int(ultimo_usado_value)
            return hasta - ultimo
        except ValueError:
            return 0

    @property
    def porcentaje_usado(self) -> float:
        """Retorna porcentaje de numeración utilizada"""
        numero_desde_value = getattr(self, 'numero_desde', '0000001')
        numero_hasta_value = getattr(self, 'numero_hasta', '9999999')
        ultimo_usado_value = getattr(self, 'ultimo_numero_usado', '0000000')

        try:
            desde = int(numero_desde_value)
            hasta = int(numero_hasta_value)
            ultimo = int(ultimo_usado_value)

            total_disponible = hasta - desde + 1
            total_usado = ultimo - desde + 1

            if total_disponible <= 0:
                return 100.0

            return (total_usado / total_disponible) * 100.0
        except ValueError:
            return 0.0

    @property
    def necesita_alerta_vencimiento(self) -> bool:
        """Verifica si necesita alerta por vencimiento próximo"""
        if not getattr(self, 'alertar_vencimiento', True):
            return False

        dias_alerta = getattr(self, 'dias_alerta_vencimiento', 30)
        return 0 <= self.dias_para_vencer <= dias_alerta

    @property
    def necesita_alerta_agotamiento(self) -> bool:
        """Verifica si necesita alerta por agotamiento próximo"""
        if not getattr(self, 'alertar_agotamiento', True):
            return False

        numeros_alerta = getattr(self, 'numeros_alerta_agotamiento', 100)
        return self.numeros_disponibles <= numeros_alerta

    def obtener_proximo_numero(self) -> str:
        """
        Obtiene el próximo número disponible para usar

        Returns:
            str: Próximo número en formato 7 dígitos (ej: "0000001")

        Raises:
            ValueError: Si no hay números disponibles
        """
        ultimo_usado_value = getattr(self, 'ultimo_numero_usado', '0000000')
        numero_hasta_value = getattr(self, 'numero_hasta', '9999999')
        incremento_value = getattr(self, 'incremento', 1)

        try:
            ultimo_usado = int(ultimo_usado_value)
            numero_hasta = int(numero_hasta_value)

            proximo_numero = ultimo_usado + incremento_value

            if proximo_numero > numero_hasta:
                raise ValueError(
                    f"Numeración agotada. Último disponible: {numero_hasta_value}")

            return str(proximo_numero).zfill(7)
        except ValueError as e:
            if "Numeración agotada" in str(e):
                raise e
            raise ValueError("Error calculando próximo número")

    def usar_numero(self, numero: Optional[str] = None) -> str:
        """
        Marca un número como usado y actualiza el contador

        Args:
            numero: Número específico a usar (opcional, usa próximo disponible)

        Returns:
            str: Número que fue marcado como usado

        Raises:
            ValueError: Si el número no es válido o ya fue usado
        """
        if numero is None:
            numero = self.obtener_proximo_numero()

        # Validar formato
        if not re.match(r'^\d{7}$', numero):
            raise ValueError("Número debe tener 7 dígitos")

        numero_int = int(numero)
        ultimo_usado_value = getattr(self, 'ultimo_numero_usado', '0000000')
        ultimo_usado_int = int(ultimo_usado_value)
        numero_hasta_value = getattr(self, 'numero_hasta', '9999999')
        numero_hasta_int = int(numero_hasta_value)

        # Validar que el número esté en rango
        if numero_int > numero_hasta_int:
            raise ValueError(f"Número {numero} excede el rango autorizado")

        # Validar que el número no haya sido usado
        if numero_int <= ultimo_usado_int:
            raise ValueError(f"Número {numero} ya fue utilizado")

        # Actualizar último número usado
        self.ultimo_numero_usado = numero

        # Actualizar estado si se agotó
        if numero_int >= numero_hasta_int:
            self.estado = EstadoTimbradoEnum.AGOTADO.value

        return numero

    def actualizar_estado_automatico(self) -> str:
        """
        Actualiza el estado del timbrado automáticamente según las condiciones

        Returns:
            str: Nuevo estado del timbrado
        """
        # Verificar vencimiento
        if not self.esta_vigente:
            self.estado = EstadoTimbradoEnum.VENCIDO.value
            return self.estado

        # Verificar agotamiento
        if self.numeros_disponibles <= 0:
            self.estado = EstadoTimbradoEnum.AGOTADO.value
            return self.estado

        # Si estaba vencido o agotado pero ahora está OK, activar
        estado_actual = getattr(self, 'estado', '')
        if estado_actual in [EstadoTimbradoEnum.VENCIDO.value, EstadoTimbradoEnum.AGOTADO.value]:
            if self.esta_vigente and self.numeros_disponibles > 0:
                self.estado = EstadoTimbradoEnum.ACTIVO.value

        return getattr(self, 'estado', EstadoTimbradoEnum.ACTIVO.value)

    def puede_emitir_documento(self) -> tuple[bool, str]:
        """
        Verifica si puede emitir un documento con este timbrado

        Returns:
            tuple: (puede_emitir: bool, motivo: str)
        """
        # Actualizar estado primero
        self.actualizar_estado_automatico()

        estado_actual = getattr(self, 'estado', '')

        # Verificaciones en orden de prioridad
        if estado_actual == EstadoTimbradoEnum.CANCELADO.value:
            return False, "Timbrado cancelado"

        if not self.esta_vigente:
            return False, f"Timbrado vencido (válido hasta {getattr(self, 'fecha_fin_vigencia', 'N/A')})"

        if self.numeros_disponibles <= 0:
            return False, "Numeración agotada"

        if estado_actual == EstadoTimbradoEnum.INACTIVO.value:
            return False, "Timbrado inactivo"

        return True, "Timbrado disponible para emisión"

    def to_dict_sifen(self) -> dict:
        """Retorna datos en formato requerido por SIFEN"""
        return {
            "numero_timbrado": getattr(self, 'numero_timbrado', ''),
            "tipo_timbrado": getattr(self, 'tipo_timbrado', '1'),
            "descripcion_tipo": getattr(self, 'descripcion_tipo', 'Timbrado electrónico SET'),
            "establecimiento": getattr(self, 'establecimiento', '001'),
            "punto_expedicion": getattr(self, 'punto_expedicion', '001'),
            "fecha_inicio_vigencia": getattr(self, 'fecha_inicio_vigencia', date.today()).isoformat(),
            "fecha_fin_vigencia": getattr(self, 'fecha_fin_vigencia', date.today()).isoformat(),
            "numero_desde": getattr(self, 'numero_desde', '0000001'),
            "numero_hasta": getattr(self, 'numero_hasta', '9999999'),
            "ultimo_numero_usado": getattr(self, 'ultimo_numero_usado', '0000000'),
            "estado": getattr(self, 'estado', 'activo'),
            "codigo_completo": self.codigo_completo,
            "esta_vigente": self.esta_vigente,
            "numeros_disponibles": self.numeros_disponibles,
            "porcentaje_usado": round(self.porcentaje_usado, 2)
        }

    def get_resumen_estado(self) -> dict:
        """Retorna resumen completo del estado del timbrado"""
        puede_emitir, motivo = self.puede_emitir_documento()

        return {
            "puede_emitir": puede_emitir,
            "motivo": motivo,
            "estado": getattr(self, 'estado', 'unknown'),
            "vigencia": {
                "esta_vigente": self.esta_vigente,
                "dias_para_vencer": self.dias_para_vencer,
                "necesita_alerta": self.necesita_alerta_vencimiento
            },
            "numeracion": {
                "numeros_disponibles": self.numeros_disponibles,
                "porcentaje_usado": round(self.porcentaje_usado, 2),
                "necesita_alerta": self.necesita_alerta_agotamiento,
                "proximo_numero": self.obtener_proximo_numero() if puede_emitir else None
            },
            "ubicacion": {
                "establecimiento": getattr(self, 'establecimiento', '001'),
                "punto_expedicion": getattr(self, 'punto_expedicion', '001'),
                "codigo_completo": self.codigo_completo
            }
        }
