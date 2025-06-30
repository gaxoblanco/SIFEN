"""
Modelos base reutilizables para todos los documentos SIFEN v150

Este módulo contiene los modelos fundamentales que se reutilizan
en todos los tipos de documentos electrónicos:
- Contribuyente: Emisor/receptor de documentos
- ItemFactura: Items/productos de documentos
- Validadores comunes

Usado en: FacturaSimple, NotaCreditoElectronica, NotaDebitoElectronica,
          AutofacturaElectronica, NotaRemisionElectronica

Arquitectura Modular:
- base.py: Modelos reutilizables (ESTE ARCHIVO)
- auxiliary.py: Modelos auxiliares específicos  
- document_types.py: Documentos principales por tipo
- validators.py: Validadores customizados

Autor: Sistema SIFEN Paraguay - Módulo XML Generator
Fecha: Junio 2025
Versión: 1.0.0
Manual: SIFEN v150 - SET Paraguay
"""

from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional
import re


# ===============================================
# CONSTANTES SIFEN PARAGUAY
# ===============================================

# Códigos de departamento válidos Paraguay (1-17)
DEPARTAMENTOS_PARAGUAY = {
    "1": "CONCEPCIÓN", "2": "SAN PEDRO", "3": "CORDILLERA",
    "4": "GUAIRÁ", "5": "CAAGUAZÚ", "6": "CAAZAPÁ",
    "7": "ITAPÚA", "8": "MISIONES", "9": "PARAGUARÍ",
    "10": "ALTO PARANÁ", "11": "CENTRAL", "12": "ÑEEMBUCÚ",
    "13": "AMAMBAY", "14": "CANINDEYÚ", "15": "PRESIDENTE HAYES",
    "16": "ALTO PARAGUAY", "17": "BOQUERÓN"
}

# Tasas de IVA válidas en Paraguay
IVA_RATES_PARAGUAY = [Decimal("0"), Decimal("5"), Decimal("10")]

# Monedas soportadas por SIFEN
MONEDAS_SIFEN = ["PYG", "USD", "EUR"]


# ===============================================
# VALIDADORES COMUNES
# ===============================================

def validate_ruc_paraguayo(ruc: str) -> str:
    """
    Valida y limpia formato RUC paraguayo

    Args:
        ruc: RUC con o sin guiones

    Returns:
        str: RUC limpio sin guiones

    Raises:
        ValueError: Si formato es inválido
    """
    # Limpiar guiones y espacios
    clean_ruc = re.sub(r'[\s\-]', '', ruc)

    # Validar formato numérico
    if not re.match(r'^\d{8,9}$', clean_ruc):
        raise ValueError('RUC debe contener solo números (8-9 dígitos)')

    # Validar longitud
    if len(clean_ruc) < 8 or len(clean_ruc) > 9:
        raise ValueError('RUC debe tener entre 8 y 9 dígitos')

    return clean_ruc


def validate_cdc_format(cdc: str) -> str:
    """
    Valida formato CDC (Código de Control del Documento)

    Args:
        cdc: CDC de 44 dígitos

    Returns:
        str: CDC validado

    Raises:
        ValueError: Si formato es inválido
    """
    if not cdc:
        raise ValueError('CDC es requerido')

    # Limpiar espacios
    clean_cdc = cdc.strip()

    # Validar formato: exactamente 44 dígitos
    if not re.match(r'^\d{44}$', clean_cdc):
        raise ValueError('CDC debe tener exactamente 44 dígitos numéricos')

    return clean_cdc


def validate_email_format(email: str) -> str:
    """
    Valida formato de email básico

    Args:
        email: Dirección de email

    Returns:
        str: Email validado en minúsculas

    Raises:
        ValueError: Si formato es inválido
    """
    # Patrón básico de email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        raise ValueError('Formato de email inválido')

    return email.lower().strip()


def validate_departamento_paraguay(codigo: str) -> str:
    """
    Valida código de departamento Paraguay

    Args:
        codigo: Código de departamento (1-17)

    Returns:
        str: Código con formato correcto (2 dígitos)

    Raises:
        ValueError: Si código es inválido
    """
    try:
        num_dept = int(codigo)
        if num_dept < 1 or num_dept > 17:
            raise ValueError('Código departamento debe estar entre 1 y 17')
        return str(num_dept).zfill(2)  # Completar con ceros
    except ValueError:
        raise ValueError('Código departamento debe ser numérico')


# ===============================================
# MODELOS BASE REUTILIZABLES
# ===============================================

class Contribuyente(BaseModel):
    """
    Datos del contribuyente (emisor o receptor)

    Modelo base reutilizable para todos los tipos de documentos SIFEN.
    Contiene validaciones específicas para Paraguay.

    Usado en:
    - FacturaSimple (emisor, receptor)
    - NotaCreditoElectronica (emisor, receptor)
    - NotaDebitoElectronica (emisor, receptor)
    - AutofacturaElectronica (emisor, receptor - mismo RUC)
    - NotaRemisionElectronica (emisor, receptor)

    Validaciones incluidas:
    - RUC paraguayo (8-9 dígitos)
    - Dígito verificador (0-9)
    - Código departamento Paraguay (1-17)
    - Email formato válido
    - Conversión automática a mayúsculas
    """

    # === DATOS FISCALES ===
    ruc: str = Field(
        ...,
        min_length=8,
        max_length=9,
        description="RUC sin guiones (8-9 dígitos)"
    )

    dv: str = Field(
        ...,
        min_length=1,
        max_length=1,
        description="Dígito verificador (0-9)"
    )

    # === DATOS IDENTIFICACIÓN ===
    razon_social: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Razón social o nombre completo"
    )

    # === DATOS UBICACIÓN ===
    direccion: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Dirección principal"
    )

    numero_casa: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Número de casa/oficina"
    )

    codigo_departamento: str = Field(
        ...,
        min_length=1,
        max_length=2,
        description="Código departamento Paraguay (1-17)"
    )

    codigo_ciudad: str = Field(
        ...,
        min_length=1,
        max_length=3,
        description="Código ciudad"
    )

    descripcion_ciudad: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Nombre de la ciudad"
    )

    # === DATOS CONTACTO ===
    telefono: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Teléfono de contacto"
    )

    email: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Email de contacto"
    )

    # === VALIDADORES ===

    @field_validator('ruc')
    @classmethod
    def validate_ruc(cls, v: str) -> str:
        """Valida formato RUC paraguayo"""
        return validate_ruc_paraguayo(v)

    @field_validator('dv')
    @classmethod
    def validate_dv(cls, v: str) -> str:
        """Valida dígito verificador"""
        if not re.match(r'^\d$', v):
            raise ValueError('DV debe ser un dígito (0-9)')
        return v

    @field_validator('razon_social')
    @classmethod
    def validate_razon_social(cls, v: str) -> str:
        """Normaliza razón social"""
        # Convertir a mayúsculas y limpiar espacios
        normalized = v.upper().strip()
        if not normalized:
            raise ValueError('Razón social no puede estar vacía')
        return normalized

    @field_validator('codigo_departamento')
    @classmethod
    def validate_codigo_departamento(cls, v: str) -> str:
        """Valida código de departamento Paraguay"""
        return validate_departamento_paraguay(v)

    @field_validator('descripcion_ciudad')
    @classmethod
    def validate_descripcion_ciudad(cls, v: str) -> str:
        """Normaliza descripción de ciudad"""
        return v.upper().strip()

    @field_validator('telefono')
    @classmethod
    def validate_telefono(cls, v: str) -> str:
        """Limpia formato teléfono"""
        # Remover espacios, guiones y paréntesis
        clean_phone = re.sub(r'[\s\-\(\)]', '', v)
        return clean_phone

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Valida formato email"""
        return validate_email_format(v)

    # === PROPERTIES ===

    @property
    def ruc_completo(self) -> str:
        """Retorna RUC con dígito verificador"""
        return f"{self.ruc}-{self.dv}"

    @property
    def nombre_departamento(self) -> str:
        """Retorna nombre del departamento"""
        return DEPARTAMENTOS_PARAGUAY.get(str(int(self.codigo_departamento)), "DESCONOCIDO")


class ItemFactura(BaseModel):
    """
    Item de factura/documento electrónico

    Modelo base reutilizable para items de todos los tipos de documentos.
    Incluye cálculos automáticos de IVA y validaciones Paraguay.

    Usado en:
    - FacturaSimple (items de venta)
    - NotaCreditoElectronica (items devueltos)
    - NotaDebitoElectronica (items con cargos)
    - AutofacturaElectronica (items importados)
    - NotaRemisionElectronica (items trasladados - precios en 0)

    Validaciones incluidas:
    - IVA válido Paraguay (0%, 5%, 10%)
    - Cálculos exactos de montos
    - Precisión decimal correcta
    - Consistencia cantidad × precio = total

    Casos especiales:
    - NRE: precio_unitario y monto_total deben ser 0
    """

    # === IDENTIFICACIÓN PRODUCTO ===
    codigo: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Código interno del producto/servicio"
    )

    descripcion: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Descripción del producto/servicio"
    )

    # === CANTIDAD Y PRECIOS ===
    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad del producto (mayor a 0)"
    )

    precio_unitario: Decimal = Field(
        ...,
        ge=0,
        description="Precio por unidad (>= 0, = 0 para NRE)"
    )

    iva: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Porcentaje de IVA (0, 5 o 10 para Paraguay)"
    )

    monto_total: Decimal = Field(
        ...,
        ge=0,
        description="Monto total del item (>= 0, = 0 para NRE)"
    )

    # === VALIDADORES ===

    @field_validator('descripcion')
    @classmethod
    def validate_descripcion(cls, v: str) -> str:
        """Normaliza descripción del item"""
        normalized = v.upper().strip()
        if not normalized:
            raise ValueError('Descripción no puede estar vacía')
        return normalized

    @field_validator('cantidad')
    @classmethod
    def validate_cantidad(cls, v: Decimal) -> Decimal:
        """Valida cantidad positiva con máximo 3 decimales"""
        if v <= 0:
            raise ValueError('Cantidad debe ser mayor a 0')

        # Validar máximo 3 decimales
        # Convertir a string y contar decimales después del punto
        str_val = str(v)
        if '.' in str_val:
            decimal_places = len(str_val.split('.')[1])
            if decimal_places > 3:
                raise ValueError('Cantidad: máximo 3 decimales permitidos')

        return v

    @field_validator('precio_unitario')
    @classmethod
    def validate_precio_unitario(cls, v: Decimal) -> Decimal:
        """Valida precio unitario con máximo 8 decimales"""
        # Validar máximo 8 decimales
        str_val = str(v)
        if '.' in str_val:
            decimal_places = len(str_val.split('.')[1])
            if decimal_places > 8:
                raise ValueError(
                    'Precio unitario: máximo 8 decimales permitidos')

        return v

    @field_validator('iva')
    @classmethod
    def validate_iva(cls, v: Decimal) -> Decimal:
        """Valida porcentaje IVA Paraguay"""
        if v not in IVA_RATES_PARAGUAY:
            raise ValueError(
                f'IVA debe ser uno de: {[float(rate) for rate in IVA_RATES_PARAGUAY]}% (Paraguay)')
        return v

    @field_validator('monto_total')
    @classmethod
    def validate_monto_total(cls, v: Decimal, info) -> Decimal:
        """Valida consistencia del monto total"""
        # Validar máximo 8 decimales
        str_val = str(v)
        if '.' in str_val:
            decimal_places = len(str_val.split('.')[1])
            if decimal_places > 8:
                raise ValueError('Monto total: máximo 8 decimales permitidos')

        # Validar consistencia cantidad × precio = total
        if 'cantidad' in info.data and 'precio_unitario' in info.data:
            expected = info.data['cantidad'] * info.data['precio_unitario']
            tolerance = Decimal('0.01')  # Tolerancia para redondeo

            if abs(v - expected) > tolerance:
                raise ValueError(
                    f'Monto total ({v}) no coincide con cantidad × precio unitario ({expected}). '
                    f'Diferencia: {abs(v - expected)}'
                )

        return v

    # === PROPERTIES CALCULADAS ===

    @property
    def monto_iva(self) -> Decimal:
        """
        Calcula el monto de IVA del item

        Returns:
            Decimal: Monto de IVA con 2 decimales
        """
        if self.iva == Decimal('0'):
            return Decimal('0.00')

        # Calcular IVA: monto_total - monto_gravado
        monto_gravado = self.monto_total / (1 + (self.iva / 100))
        monto_iva = self.monto_total - monto_gravado

        return round(monto_iva, 2)

    @property
    def monto_gravado(self) -> Decimal:
        """
        Calcula el monto gravado del item (base para IVA)

        Returns:
            Decimal: Monto gravado con 2 decimales
        """
        if self.iva == Decimal('0'):
            return Decimal('0.00')

        # Calcular base gravada
        monto_gravado = self.monto_total / (1 + (self.iva / 100))

        return round(monto_gravado, 2)

    @property
    def monto_exento(self) -> Decimal:
        """
        Calcula el monto exento del item

        Returns:
            Decimal: Monto exento con 2 decimales
        """
        if self.iva == Decimal('0'):
            return self.monto_total

        return Decimal('0.00')

    @property
    def descripcion_iva(self) -> str:
        """
        Retorna descripción del tipo de IVA

        Returns:
            str: Descripción del IVA aplicado
        """
        if self.iva == Decimal('0'):
            return "Exento"
        elif self.iva == Decimal('5'):
            return "IVA 5%"
        elif self.iva == Decimal('10'):
            return "IVA 10%"
        else:
            return f"IVA {self.iva}%"


# ===============================================
# FUNCIONES HELPER PARA EJEMPLOS
# ===============================================

def create_contribuyente_ejemplo(tipo: str = "emisor") -> Contribuyente:
    """
    Crea un contribuyente de ejemplo para testing

    Args:
        tipo: "emisor" o "receptor"

    Returns:
        Contribuyente: Datos de ejemplo válidos
    """
    if tipo == "emisor":
        return Contribuyente(
            ruc="80016875",
            dv="9",
            razon_social="EMPRESA EJEMPLO S.A.",
            direccion="AV. MARISCAL LÓPEZ 1234",
            numero_casa="1234",
            codigo_departamento="11",  # Central
            codigo_ciudad="001",
            descripcion_ciudad="ASUNCIÓN",
            telefono="021555123",
            email="facturacion@empresa.com.py"
        )
    else:  # receptor
        return Contribuyente(
            ruc="80087654",
            dv="3",
            razon_social="CLIENTE EJEMPLO S.R.L.",
            direccion="AV. ESPAÑA 567",
            numero_casa="567",
            codigo_departamento="11",  # Central
            codigo_ciudad="002",
            descripcion_ciudad="SAN LORENZO",
            telefono="021555456",
            email="compras@cliente.com.py"
        )


def create_item_ejemplo(tipo: str = "producto") -> ItemFactura:
    """
    Crea un item de ejemplo para testing

    Args:
        tipo: "producto", "servicio", "exento", o "remision"

    Returns:
        ItemFactura: Item de ejemplo válido
    """
    if tipo == "producto":
        return ItemFactura(
            codigo="PROD001",
            descripcion="NOTEBOOK LENOVO THINKPAD",
            cantidad=Decimal("1.000"),
            precio_unitario=Decimal("5000000.00"),
            iva=Decimal("10"),
            monto_total=Decimal("5000000.00")
        )
    elif tipo == "servicio":
        return ItemFactura(
            codigo="SERV001",
            descripcion="CONSULTORIA SISTEMAS",
            cantidad=Decimal("8.0"),  # 8 horas
            precio_unitario=Decimal("125000.00"),
            iva=Decimal("10"),
            monto_total=Decimal("1000000.00")  # 8 × 125,000
        )
    elif tipo == "exento":
        return ItemFactura(
            codigo="EXEN001",
            descripcion="MEDICAMENTO ESENCIAL",
            cantidad=Decimal("2.000"),
            precio_unitario=Decimal("50000.00"),
            iva=Decimal("0"),  # Exento
            monto_total=Decimal("100000.00")
        )
    else:  # remision (sin precios)
        return ItemFactura(
            codigo="REMI001",
            descripcion="PRODUCTO PARA TRASLADO",
            cantidad=Decimal("5.000"),
            precio_unitario=Decimal("0.00"),  # Sin precio en NRE
            iva=Decimal("0"),
            monto_total=Decimal("0.00")  # Sin monto en NRE
        )


# ===============================================
# EXPORTS - Según Plan de Modularización
# ===============================================

__all__ = [
    # === MODELOS PRINCIPALES ===
    "Contribuyente",
    "ItemFactura",

    # === VALIDADORES REUTILIZABLES ===
    "validate_ruc_paraguayo",
    "validate_cdc_format",
    "validate_email_format",
    "validate_departamento_paraguay",

    # === CONSTANTES PARAGUAY ===
    "DEPARTAMENTOS_PARAGUAY",
    "IVA_RATES_PARAGUAY",
    "MONEDAS_SIFEN",

    # === HELPERS PARA TESTING ===
    "create_contribuyente_ejemplo",
    "create_item_ejemplo"
]

# Información del módulo para __init__.py
MODULE_INFO = {
    "name": "base",
    "description": "Modelos base reutilizables",
    "version": "1.0.0",
    "models": ["Contribuyente", "ItemFactura"],
    "validators": 4,
    "constants": 3,
    "helpers": 2
}
