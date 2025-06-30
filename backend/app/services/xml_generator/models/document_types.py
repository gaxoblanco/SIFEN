"""
models/document_types.py - Documentos Principales SIFEN v150
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Literal
from .base import Contribuyente, ItemFactura
from .auxiliary import DocumentoAsociado, DatosAFE, ContribuyenteExtranjero, DatosTransporte, DatosVehiculo


class FacturaSimple(BaseModel):
    """Factura Electrónica Simple - Tipo de Documento 1"""

    numero_documento: str = Field(..., min_length=15, max_length=15)
    emisor: Contribuyente = Field(...)
    receptor: Contribuyente = Field(...)
    items: List[ItemFactura] = Field(..., min_length=1, max_length=999)
    total_gravada: Decimal = Field(..., ge=Decimal("0"))
    total_iva: Decimal = Field(..., ge=Decimal("0"))
    total_exenta: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    total_general: Decimal = Field(..., ge=Decimal("0"))
    fecha_emision: datetime = Field(default_factory=datetime.now)
    csc: str = Field(..., min_length=9, max_length=9)

    @property
    def cantidad_total(self) -> Decimal:
        """Calcula la cantidad total de items"""
        if not self.items:
            return Decimal("0")
        total = sum(item.cantidad for item in self.items)
        return Decimal(str(total)) if not isinstance(total, Decimal) else total

    @property
    def items_count(self) -> int:
        """Retorna el número de items"""
        return len(self.items)

    @field_validator('numero_documento')
    @classmethod
    def validate_numero_documento(cls, v: str) -> str:
        import re
        if not re.match(r'^\d{3}-\d{3}-\d{7}$', v):
            raise ValueError("Formato debe ser XXX-XXX-XXXXXXX")
        return v

    @model_validator(mode='after')
    def validate_totals_consistency(self):
        calculated_total = self.total_gravada + self.total_exenta + self.total_iva
        if abs(calculated_total - self.total_general) > Decimal("0.01"):
            raise ValueError("Los totales no son consistentes")
        return self


class NotaCreditoElectronica(BaseModel):
    """Nota de Crédito Electrónica - Tipo de Documento 5"""

    numero_documento: str = Field(..., min_length=15, max_length=15)
    emisor: Contribuyente = Field(...)
    receptor: Contribuyente = Field(...)
    items: List[ItemFactura] = Field(..., min_length=1)
    total_gravada: Decimal = Field(..., ge=Decimal("0"))
    total_iva: Decimal = Field(..., ge=Decimal("0"))
    total_exenta: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    total_general: Decimal = Field(..., ge=Decimal("0"))
    fecha_emision: datetime = Field(default_factory=datetime.now)
    csc: str = Field(..., min_length=9, max_length=9)

    # Campos específicos de Nota de Crédito
    documento_asociado: DocumentoAsociado = Field(...)
    motivo_credito: str = Field(..., min_length=5, max_length=500)
    tipo_credito: Literal["1", "2", "3"] = Field(...)
    condicion_operacion: Literal["1", "2", "3", "4"] = Field(...)
    observaciones_credito: Optional[str] = Field(default=None, max_length=500)

    @property
    def cantidad_total(self) -> Decimal:
        """Calcula cantidad total de items creditados"""
        if not self.items:
            return Decimal("0")
        total = sum(item.cantidad for item in self.items)
        return Decimal(str(total)) if not isinstance(total, Decimal) else total


class NotaDebitoElectronica(BaseModel):
    """Nota de Débito Electrónica - Tipo de Documento 6"""

    numero_documento: str = Field(..., min_length=15, max_length=15)
    emisor: Contribuyente = Field(...)
    receptor: Contribuyente = Field(...)
    items: List[ItemFactura] = Field(..., min_length=1)
    total_gravada: Decimal = Field(..., ge=Decimal("0"))
    total_iva: Decimal = Field(..., ge=Decimal("0"))
    total_exenta: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    total_general: Decimal = Field(..., ge=Decimal("0"))
    fecha_emision: datetime = Field(default_factory=datetime.now)
    csc: str = Field(..., min_length=9, max_length=9)

    # Campos específicos de Nota de Débito
    documento_asociado: DocumentoAsociado = Field(...)
    motivo_debito: str = Field(..., min_length=5, max_length=500)
    tipo_debito: Literal["1", "2", "3"] = Field(...)
    condicion_operacion: Literal["5", "6", "7"] = Field(...)
    observaciones_debito: Optional[str] = Field(default=None, max_length=500)

    @property
    def cantidad_total(self) -> Decimal:
        """Calcula cantidad total de items debitados"""
        if not self.items:
            return Decimal("0")
        total = sum(item.cantidad for item in self.items)
        return Decimal(str(total)) if not isinstance(total, Decimal) else total


class AutofacturaElectronica(BaseModel):
    """Autofactura Electrónica - Tipo de Documento 4"""

    numero_documento: str = Field(..., min_length=15, max_length=15)
    emisor: Contribuyente = Field(...)
    items: List[ItemFactura] = Field(..., min_length=1)
    total_gravada: Decimal = Field(..., ge=Decimal("0"))
    total_iva: Decimal = Field(..., ge=Decimal("0"))
    total_exenta: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    total_general: Decimal = Field(..., ge=Decimal("0"))
    fecha_emision: datetime = Field(default_factory=datetime.now)
    csc: str = Field(..., min_length=9, max_length=9)

    # Campos específicos de AFE
    datos_afe: DatosAFE = Field(...)
    vendedor_extranjero: ContribuyenteExtranjero = Field(...)
    motivo_afe: str = Field(..., min_length=10, max_length=500)
    condicion_operacion: Literal["8", "9"] = Field(...)
    observaciones_afe: Optional[str] = Field(default=None, max_length=500)

    @property
    def cantidad_total(self) -> Decimal:
        """Calcula cantidad total de items en autofactura"""
        if not self.items:
            return Decimal("0")
        total = sum(item.cantidad for item in self.items)
        return Decimal(str(total)) if not isinstance(total, Decimal) else total


class NotaRemisionElectronica(BaseModel):
    """Nota de Remisión Electrónica - Tipo de Documento 7"""

    numero_documento: str = Field(..., min_length=15, max_length=15)
    emisor: Contribuyente = Field(...)
    receptor: Contribuyente = Field(...)
    items: List[ItemFactura] = Field(..., min_length=1)
    total_gravada: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    total_iva: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    total_exenta: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    total_general: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    fecha_emision: datetime = Field(default_factory=datetime.now)
    csc: str = Field(..., min_length=9, max_length=9)

    # Campos específicos de NRE
    datos_transporte: DatosTransporte = Field(...)
    datos_vehiculo: Optional[DatosVehiculo] = Field(default=None)
    motivo_traslado: str = Field(..., min_length=10, max_length=500)
    tipo_traslado: Literal["1", "2", "3", "4"] = Field(...)
    condicion_operacion: Literal["10", "11", "12"] = Field(...)
    observaciones_traslado: Optional[str] = Field(default=None, max_length=500)

    @property
    def cantidad_total(self) -> Decimal:
        """Calcula cantidad total de items trasladados"""
        if not self.items:
            return Decimal("0")
        total = sum(item.cantidad for item in self.items)
        return Decimal(str(total)) if not isinstance(total, Decimal) else total


# Funciones de ejemplo para testing
def create_contribuyente_ejemplo(tipo: str = "emisor") -> Contribuyente:
    """Crea un contribuyente de ejemplo para testing"""
    if tipo == "emisor":
        return Contribuyente(
            ruc="80012345",
            dv="1",
            razon_social="EMPRESA EMISORA S.A.",
            direccion="Av. Principal 123",
            numero_casa="100",
            codigo_departamento="11",
            codigo_ciudad="1",
            descripcion_ciudad="Asunción",
            telefono="021-123456",
            email="emisor@ejemplo.com.py"
        )
    else:
        return Contribuyente(
            ruc="80087654",
            dv="2",
            razon_social="EMPRESA RECEPTORA S.R.L.",
            direccion="Calle Secundaria 456",
            numero_casa="200",
            codigo_departamento="11",
            codigo_ciudad="1",
            descripcion_ciudad="Asunción",
            telefono="021-654321",
            email="receptor@ejemplo.com.py"
        )


def create_item_ejemplo(tipo: str = "producto") -> ItemFactura:
    """Crea un item de ejemplo para testing"""
    if tipo == "producto":
        return ItemFactura(
            codigo="PROD001",
            descripcion="PRODUCTO DE EJEMPLO",
            cantidad=Decimal("10.0000"),
            precio_unitario=Decimal("90909.09"),
            iva=Decimal("10.0"),
            monto_total=Decimal("909090.90")
        )
    else:
        return ItemFactura(
            codigo="SERV001",
            descripcion="SERVICIO DE CONSULTORÍA",
            cantidad=Decimal("5.0000"),
            precio_unitario=Decimal("90909.09"),
            iva=Decimal("10.0"),
            monto_total=Decimal("454545.45")
        )


def create_documento_asociado_ejemplo() -> DocumentoAsociado:
    """Crea un documento asociado de ejemplo para NCE/NDE"""
    return DocumentoAsociado(
        tipo_documento_ref="1",
        numero_documento_ref="001-001-0000123",
        fecha_documento_ref=datetime(2025, 6, 15, 10, 30, 0),
        cdc_ref="01234567890123456789012345678901234567890123",
        numero_timbrado_ref="12345678",
        monto_original=Decimal("1000000.00")
    )


def create_factura_ejemplo() -> FacturaSimple:
    """Crea una factura de ejemplo completa"""
    return FacturaSimple(
        numero_documento="001-001-0000001",
        emisor=create_contribuyente_ejemplo("emisor"),
        receptor=create_contribuyente_ejemplo("receptor"),
        items=[create_item_ejemplo("producto")],
        total_gravada=Decimal("909090.91"),
        total_iva=Decimal("90909.09"),
        total_general=Decimal("1000000.00"),
        csc="CSC123ABC"
    )


def create_nota_credito_ejemplo() -> NotaCreditoElectronica:
    """Crea una nota de crédito de ejemplo completa"""
    return NotaCreditoElectronica(
        numero_documento="001-002-0000001",
        emisor=create_contribuyente_ejemplo("emisor"),
        receptor=create_contribuyente_ejemplo("receptor"),
        items=[create_item_ejemplo("producto")],
        total_gravada=Decimal("909090.91"),
        total_iva=Decimal("90909.09"),
        total_general=Decimal("1000000.00"),
        csc="CSC456DEF",
        documento_asociado=create_documento_asociado_ejemplo(),
        motivo_credito="DEVOLUCIÓN PARCIAL DE MERCADERÍA CON DEFECTOS",
        tipo_credito="2",
        condicion_operacion="2",
        observaciones_credito="Devolución autorizada por control de calidad"
    )


def create_nota_debito_ejemplo() -> NotaDebitoElectronica:
    """Crea una nota de débito de ejemplo completa"""
    return NotaDebitoElectronica(
        numero_documento="001-003-0000001",
        emisor=create_contribuyente_ejemplo("emisor"),
        receptor=create_contribuyente_ejemplo("receptor"),
        items=[create_item_ejemplo("servicio")],
        total_gravada=Decimal("454545.45"),
        total_iva=Decimal("45454.55"),
        total_general=Decimal("500000.00"),
        csc="CSC789GHI",
        documento_asociado=create_documento_asociado_ejemplo(),
        motivo_debito="INTERESES POR MORA EN PAGO DE FACTURA",
        tipo_debito="1",
        condicion_operacion="6",
        observaciones_debito="Intereses calculados según contrato comercial"
    )


def create_autofactura_ejemplo() -> AutofacturaElectronica:
    """Crea una autofactura de ejemplo completa"""
    return AutofacturaElectronica(
        numero_documento="001-004-0000001",
        emisor=create_contribuyente_ejemplo("emisor"),
        items=[create_item_ejemplo("servicio")],
        total_gravada=Decimal("454545.45"),
        total_iva=Decimal("45454.55"),
        total_general=Decimal("500000.00"),
        csc="CSC012JKL",
        datos_afe=DatosAFE(
            tipo_operacion_afe="1",
            vendedor="INTERNATIONAL SOFTWARE LLC",
            moneda_extranjera="USD",
            tipo_cambio_extranjero=Decimal("7300.00"),
            observaciones_afe="Licencias de software empresarial"
        ),
        vendedor_extranjero=ContribuyenteExtranjero(
            naturaleza_vendedor="2",
            tipo_documento_vendedor="2",
            numero_documento_vendedor="TAX123456789",
            nombre_vendedor="INTERNATIONAL SOFTWARE LLC",
            direccion_vendedor="123 Tech Street, Silicon Valley",
            pais_vendedor="USA",
            telefono_vendedor="+1-555-0123",
            email_vendedor="contact@intsoftware.com"
        ),
        motivo_afe="LICENCIAS DE SOFTWARE EMPRESARIAL",
        condicion_operacion="9",
        observaciones_afe="Licencias anuales renovadas según contrato master"
    )


def create_nota_remision_ejemplo() -> NotaRemisionElectronica:
    """Crea una nota de remisión de ejemplo completa"""
    return NotaRemisionElectronica(
        numero_documento="001-005-0000001",
        emisor=create_contribuyente_ejemplo("emisor"),
        receptor=create_contribuyente_ejemplo("receptor"),
        items=[create_item_ejemplo("producto")],
        csc="CSC345MNO",
        datos_transporte=DatosTransporte(
            tipo_responsable="1",
            modalidad_transporte="1",
            tipo_transporte="1",
            fecha_inicio_traslado=datetime(2025, 6, 30, 8, 0, 0),
            fecha_fin_estimada=datetime(2025, 6, 30, 18, 0, 0),
            direccion_salida="Av. Principal 123, Asunción",
            direccion_llegada="Calle Secundaria 456, Asunción",
            vehiculos=["ABC123"],
            observaciones_transporte="Traslado programado con carga completa"
        ),
        datos_vehiculo=DatosVehiculo(
            numero_chapa="ABC123",
            numero_senacsa="SEN123456",
            marca="MERCEDES",
            tipo_vehiculo="1",
            conductor_nombre="JUAN PEREZ",
            conductor_documento="12345678",
            conductor_telefono="0981567890"
        ),
        motivo_traslado="TRASLADO ENTRE SUCURSALES PARA RESTOCK",
        tipo_traslado="1",
        condicion_operacion="10",
        observaciones_traslado="Traslado programado para reposición de stock sucursal centro"
    )


__all__ = [
    "FacturaSimple",
    "NotaCreditoElectronica",
    "NotaDebitoElectronica",
    "AutofacturaElectronica",
    "NotaRemisionElectronica",
    "create_contribuyente_ejemplo",
    "create_item_ejemplo",
    "create_documento_asociado_ejemplo",
    "create_factura_ejemplo",
    "create_nota_credito_ejemplo",
    "create_nota_debito_ejemplo",
    "create_autofactura_ejemplo",
    "create_nota_remision_ejemplo"
]
