# ===============================================
# ARCHIVO: backend/app/models/producto.py
# PROPÓSITO: Catálogo de productos/servicios para SIFEN
# VERSIÓN: 1.0.0 - Compatible con SIFEN v150
# ===============================================

from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, Enum, Numeric
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
import re
from typing import Optional
from decimal import Decimal
import enum


class TipoProductoEnum(enum.Enum):
    """Tipos de productos/servicios según normativa SIFEN"""
    PRODUCTO = "producto"          # Producto físico
    SERVICIO = "servicio"          # Servicio profesional/técnico
    BIEN_USO = "bien_uso"          # Bien de uso/activo fijo
    OTROS = "otros"                # Otros tipos


class AfectacionIvaEnum(enum.Enum):
    """Afectación de IVA según SIFEN Paraguay"""
    GRAVADO = "1"                  # Gravado con IVA (10% estándar, 5% reducido)
    EXONERADO = "2"                # Exonerado de IVA
    EXENTO = "3"                   # Exento de IVA


class UnidadMedidaEnum(enum.Enum):
    """Unidades de medida comunes en Paraguay"""
    UNIDAD = "Unidad"              # Unidad por defecto
    KILOGRAMO = "Kilogramo"        # Peso
    METRO = "Metro"                # Longitud
    METRO_CUADRADO = "Metro cuadrado"  # Superficie
    METRO_CUBICO = "Metro cúbico"  # Volumen
    LITRO = "Litro"                # Líquidos
    BOLSA = "Bolsa"                # Cemento, harinas
    CAJA = "Caja"                  # Medicamentos, productos
    BALDE = "Balde"                # Pinturas, químicos
    SERVICIO = "Servicio"          # Servicios profesionales
    HORA = "Hora"                  # Servicios por tiempo
    PACK = "Pack"                  # Paquetes/conjuntos


class Producto(BaseModel):
    """
    Catálogo de productos y servicios para documentos electrónicos SIFEN.

    Modelo que almacena información de productos/servicios para:
    - Facturación electrónica
    - Control de inventario básico
    - Cálculos automáticos de IVA
    - Generación de documentos SIFEN

    Cumple con regulaciones Paraguay:
    - IVA: 0% (exento), 5% (reducido), 10% (estándar)
    - Códigos NCM para productos físicos
    - Validaciones específicas SIFEN
    """

    # === IDENTIFICACIÓN ===
    codigo_interno = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Código interno del producto/servicio"
    )

    codigo_barras = Column(
        String(50),
        doc="Código de barras (EAN, UPC, etc.)"
    )

    codigo_ncm = Column(
        String(12),
        doc="Código NCM/Partida arancelaria (para productos físicos)"
    )

    # === DESCRIPCIÓN ===
    descripcion = Column(
        String(200),
        nullable=False,
        doc="Descripción del producto/servicio"
    )

    descripcion_adicional = Column(
        Text,
        doc="Descripción adicional o características técnicas"
    )

    # === CLASIFICACIÓN ===
    tipo_producto = Column(
        Enum(TipoProductoEnum),
        nullable=False,
        default=TipoProductoEnum.PRODUCTO,
        doc="Tipo de producto/servicio"
    )

    categoria = Column(
        String(50),
        doc="Categoría o familia del producto"
    )

    marca = Column(
        String(50),
        doc="Marca del producto"
    )

    # === UNIDAD Y MEDIDAS ===
    unidad_medida = Column(
        Enum(UnidadMedidaEnum),
        nullable=False,
        default=UnidadMedidaEnum.UNIDAD,
        doc="Unidad de medida"
    )

    # === PRECIOS ===
    precio_unitario = Column(
        Numeric(15, 4),
        nullable=False,
        doc="Precio unitario en guaraníes"
    )

    precio_costo = Column(
        Numeric(15, 4),
        doc="Precio de costo (para control interno)"
    )

    # === CONFIGURACIÓN IVA ===
    afectacion_iva = Column(
        Enum(AfectacionIvaEnum),
        nullable=False,
        default=AfectacionIvaEnum.GRAVADO,
        doc="Afectación de IVA según SIFEN"
    )

    porcentaje_iva = Column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("10.00"),
        doc="Porcentaje de IVA (0, 5 o 10 para Paraguay)"
    )

    # === ORIGEN Y REGULACIONES ===
    pais_origen = Column(
        String(3),
        default="PRY",
        doc="Código país de origen (ISO 3166)"
    )

    requiere_senacsa = Column(
        Boolean,
        default=False,
        doc="Requiere número SENACSA (productos alimentarios)"
    )

    requiere_senave = Column(
        Boolean,
        default=False,
        doc="Requiere número SENAVE (productos agrícolas)"
    )

    # === INVENTARIO BÁSICO ===
    controla_stock = Column(
        Boolean,
        default=True,
        doc="Controla stock del producto"
    )

    stock_actual = Column(
        Numeric(10, 3),
        default=Decimal("0"),
        doc="Stock actual (solo referencial)"
    )

    stock_minimo = Column(
        Numeric(10, 3),
        default=Decimal("0"),
        doc="Stock mínimo de alerta"
    )

    # === ESTADO ===
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Producto activo en el catálogo"
    )

    observaciones = Column(
        Text,
        doc="Observaciones adicionales del producto"
    )

    # === RELACIONES ===
    empresa_id = Column(
        Integer,
        ForeignKey('empresa.id'),
        nullable=False,
        doc="Empresa propietaria del producto"
    )
    # empresa = relationship("Empresa", back_populates="productos")

    # Relaciones futuras (comentadas para no crear dependencias aún)
    # items_factura = relationship("ItemFactura", back_populates="producto")

    @validates('codigo_interno')
    def validate_codigo_interno(self, key: str, value: str) -> str:
        """Validar código interno del producto"""
        if not value:
            raise ValueError("Código interno es requerido")

        # Limpiar espacios
        clean_code = value.strip().upper()

        # Validar formato básico: alfanumérico, guiones, puntos
        if not re.match(r'^[A-Z0-9\-\.\_]{1,20}$', clean_code):
            raise ValueError(
                "Código interno debe ser alfanumérico (máx 20 caracteres)")

        return clean_code

    @validates('codigo_ncm')
    def validate_codigo_ncm(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validar código NCM (nomenclatura común del mercosur)"""
        if value:
            # Limpiar puntos y espacios
            clean_ncm = re.sub(r'[.\s]', '', value.strip())

            # Validar formato: 8 dígitos
            if not re.match(r'^\d{8}$', clean_ncm):
                raise ValueError("Código NCM debe tener 8 dígitos")

            return clean_ncm
        return value

    @validates('porcentaje_iva')
    def validate_porcentaje_iva(self, key: str, value: Decimal) -> Decimal:
        """Validar porcentaje de IVA según normativa Paraguay"""
        # Convertir a Decimal si viene como otro tipo
        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        # Valores válidos en Paraguay
        valid_rates = [Decimal("0"), Decimal("5"), Decimal("10")]

        if value not in valid_rates:
            raise ValueError("IVA debe ser 0%, 5% o 10% en Paraguay")

        # Sincronizar con afectación IVA
        if value == Decimal("0"):
            self.afectacion_iva = AfectacionIvaEnum.EXENTO
        else:
            self.afectacion_iva = AfectacionIvaEnum.GRAVADO

        return value

    @validates('precio_unitario')
    def validate_precio_unitario(self, key: str, value: Decimal) -> Decimal:
        """Validar precio unitario"""
        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        if value < 0:
            raise ValueError("Precio unitario no puede ser negativo")

        # CORRECCIÓN: Validar máximo 4 decimales de forma más robusta
        # Convertir a string y verificar decimales después del punto
        str_value = str(value)

        if '.' in str_value:
            decimal_part = str_value.split('.')[1]
            if len(decimal_part) > 4:
                raise ValueError(
                    "Precio unitario: máximo 4 decimales permitidos")

        return value

    @validates('pais_origen')
    def validate_pais_origen(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validar código de país ISO"""
        if value:
            if len(value) != 3:
                raise ValueError(
                    "Código país debe tener 3 caracteres (ISO 3166)")
            return value.upper()
        return value

    @validates('descripcion')
    def validate_descripcion(self, key: str, value: str) -> str:
        """Validar descripción del producto"""
        if not value or not value.strip():
            raise ValueError("Descripción es requerida")

        clean_desc = value.strip()

        if len(clean_desc) < 3:
            raise ValueError("Descripción debe tener al menos 3 caracteres")

        return clean_desc

    def __repr__(self) -> str:
        codigo = getattr(self, 'codigo_interno', 'unknown')
        descripcion = getattr(self, 'descripcion', 'unknown')
        return f"<Producto(id={self.id}, codigo='{codigo}', desc='{descripcion[:30]}')>"

    @property
    def precio_con_iva(self) -> Decimal:
        """Calcula precio unitario incluyendo IVA"""
        precio_base = getattr(self, 'precio_unitario', Decimal("0"))
        iva_porcentaje = getattr(self, 'porcentaje_iva', Decimal("0"))

        if not isinstance(precio_base, Decimal):
            precio_base = Decimal(str(precio_base))
        if not isinstance(iva_porcentaje, Decimal):
            iva_porcentaje = Decimal(str(iva_porcentaje))

        multiplicador_iva = Decimal("1") + (iva_porcentaje / Decimal("100"))
        return precio_base * multiplicador_iva

    @property
    def monto_iva_unitario(self) -> Decimal:
        """Calcula monto de IVA por unidad"""
        precio_base = getattr(self, 'precio_unitario', Decimal("0"))
        iva_porcentaje = getattr(self, 'porcentaje_iva', Decimal("0"))

        if not isinstance(precio_base, Decimal):
            precio_base = Decimal(str(precio_base))
        if not isinstance(iva_porcentaje, Decimal):
            iva_porcentaje = Decimal(str(iva_porcentaje))

        return precio_base * (iva_porcentaje / Decimal("100"))

    @property
    def descripcion_afectacion_iva(self) -> str:
        """Retorna descripción de afectación IVA según SIFEN"""
        afectacion_value = getattr(self, 'afectacion_iva', None)

        if afectacion_value == AfectacionIvaEnum.GRAVADO:
            return "Gravado IVA"
        elif afectacion_value == AfectacionIvaEnum.EXONERADO:
            return "Exonerado IVA"
        elif afectacion_value == AfectacionIvaEnum.EXENTO:
            return "Exento IVA"
        return "Gravado IVA"  # Default

    @property
    def codigo_afectacion_iva(self) -> str:
        """Retorna código de afectación IVA según SIFEN"""
        afectacion_value = getattr(self, 'afectacion_iva', None)

        if afectacion_value:
            return afectacion_value.value
        return "1"  # Default: Gravado

    @property
    def tasa_iva_decimal(self) -> Decimal:
        """Retorna tasa de IVA en formato decimal (0.10 para 10%)"""
        iva_porcentaje = getattr(self, 'porcentaje_iva', Decimal("0"))

        if not isinstance(iva_porcentaje, Decimal):
            iva_porcentaje = Decimal(str(iva_porcentaje))

        return iva_porcentaje / Decimal("100")

    @property
    def es_producto_fisico(self) -> bool:
        """Verifica si es un producto físico (no servicio)"""
        tipo_value = getattr(self, 'tipo_producto', None)
        return tipo_value == TipoProductoEnum.PRODUCTO

    @property
    def es_servicio(self) -> bool:
        """Verifica si es un servicio"""
        tipo_value = getattr(self, 'tipo_producto', None)
        return tipo_value == TipoProductoEnum.SERVICIO

    def calcular_totales_item(self, cantidad: Decimal) -> dict:
        """
        Calcula totales para un item en factura

        Args:
            cantidad: Cantidad del producto

        Returns:
            dict: Diccionario con cálculos SIFEN
        """
        if not isinstance(cantidad, Decimal):
            cantidad = Decimal(str(cantidad))

        precio_base = getattr(self, 'precio_unitario', Decimal("0"))
        if not isinstance(precio_base, Decimal):
            precio_base = Decimal(str(precio_base))

        # Cálculos base
        subtotal = precio_base * cantidad
        monto_iva = subtotal * self.tasa_iva_decimal
        total_item = subtotal + monto_iva

        return {
            "cantidad": cantidad,
            "precio_unitario": precio_base,
            "subtotal_sin_iva": subtotal,
            "porcentaje_iva": getattr(self, 'porcentaje_iva', Decimal("0")),
            "monto_iva": monto_iva,
            "total_item": total_item,
            "afectacion_iva": self.codigo_afectacion_iva,
            "descripcion_afectacion": self.descripcion_afectacion_iva
        }

    def to_dict_sifen(self) -> dict:
        """Retorna datos en formato requerido por SIFEN"""
        tipo_producto_value = getattr(self, 'tipo_producto', None)
        unidad_medida_value = getattr(self, 'unidad_medida', None)

        return {
            "codigo_interno": getattr(self, 'codigo_interno', ''),
            "codigo_barras": getattr(self, 'codigo_barras', ''),
            "codigo_ncm": getattr(self, 'codigo_ncm', ''),
            "descripcion": getattr(self, 'descripcion', ''),
            "descripcion_adicional": getattr(self, 'descripcion_adicional', ''),
            "tipo_producto": tipo_producto_value.value if tipo_producto_value else "producto",
            "categoria": getattr(self, 'categoria', ''),
            "marca": getattr(self, 'marca', ''),
            "unidad_medida": unidad_medida_value.value if unidad_medida_value else "Unidad",
            "precio_unitario": float(getattr(self, 'precio_unitario', 0)),
            "afectacion_iva": self.codigo_afectacion_iva,
            "descripcion_afectacion_iva": self.descripcion_afectacion_iva,
            "porcentaje_iva": float(getattr(self, 'porcentaje_iva', 0)),
            "tasa_iva": float(self.tasa_iva_decimal),
            "pais_origen": getattr(self, 'pais_origen', 'PRY'),
            "requiere_senacsa": getattr(self, 'requiere_senacsa', False),
            "requiere_senave": getattr(self, 'requiere_senave', False)
        }

    def is_stock_bajo(self) -> bool:
        """Verifica si el stock está por debajo del mínimo"""
        if not getattr(self, 'controla_stock', True):
            return False

        stock_actual_value = getattr(self, 'stock_actual', Decimal("0"))
        stock_minimo_value = getattr(self, 'stock_minimo', Decimal("0"))

        if not isinstance(stock_actual_value, Decimal):
            stock_actual_value = Decimal(str(stock_actual_value))
        if not isinstance(stock_minimo_value, Decimal):
            stock_minimo_value = Decimal(str(stock_minimo_value))

        return stock_actual_value <= stock_minimo_value

    def ajustar_stock(self, cantidad: Decimal, operacion: str = "venta") -> None:
        """
        Ajusta el stock del producto

        Args:
            cantidad: Cantidad a ajustar
            operacion: 'venta' (resta) o 'compra' (suma)
        """
        if not getattr(self, 'controla_stock', True):
            return

        if not isinstance(cantidad, Decimal):
            cantidad = Decimal(str(cantidad))

        stock_actual_value = getattr(self, 'stock_actual', Decimal("0"))
        if not isinstance(stock_actual_value, Decimal):
            stock_actual_value = Decimal(str(stock_actual_value))

        if operacion == "venta":
            self.stock_actual = stock_actual_value - cantidad
        elif operacion == "compra":
            self.stock_actual = stock_actual_value + cantidad
