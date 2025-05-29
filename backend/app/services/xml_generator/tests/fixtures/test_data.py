"""
Fixtures para tests del generador XML
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from app.services.xml_generator.models import Contribuyente, ItemFactura, FacturaSimple

# Datos base para emisor
EMISOR_BASE = Contribuyente(
    ruc="12345678",
    dv="9",
    razon_social="Empresa de Prueba S.A.",
    direccion="Av. Test 123",
    numero_casa="100",
    codigo_departamento="01",
    codigo_ciudad="001",
    descripcion_ciudad="Asunción",
    telefono="021-123456",
    email="test@empresa.com"
)

# Datos base para receptor
RECEPTOR_BASE = Contribuyente(
    ruc="87654321",
    dv="0",
    razon_social="Cliente de Prueba S.A.",
    direccion="Av. Cliente 456",
    numero_casa="200",
    codigo_departamento="02",
    codigo_ciudad="002",
    descripcion_ciudad="San Lorenzo",
    telefono="021-654321",
    email="test@cliente.com"
)

# Item base para factura
ITEM_BASE = ItemFactura(
    codigo="001",
    descripcion="Producto de prueba",
    cantidad=Decimal("2"),
    precio_unitario=Decimal("100000"),
    iva=Decimal("10"),
    monto_total=Decimal("200000")
)


def create_factura_base(
    tipo_documento: str = "1",
    numero_documento: str = "001-001-0000001",
    fecha_emision: Optional[datetime] = None,
    emisor: Optional[Contribuyente] = None,
    receptor: Optional[Contribuyente] = None,
    items: Optional[List[ItemFactura]] = None,
    total_iva: Optional[Decimal] = None,
    total_gravada: Optional[Decimal] = None,
    total_exenta: Optional[Decimal] = None,
    total_general: Optional[Decimal] = None,
    moneda: str = "PYG",
    tipo_cambio: Optional[Decimal] = None
) -> FacturaSimple:
    """
    Crea una factura base con valores por defecto o personalizados
    """
    if fecha_emision is None:
        fecha_emision = datetime.now()
    if emisor is None:
        emisor = EMISOR_BASE
    if receptor is None:
        receptor = RECEPTOR_BASE
    if items is None:
        items = [ITEM_BASE]
    if total_iva is None:
        total_iva = Decimal("20000")
    if total_gravada is None:
        total_gravada = Decimal("200000")
    if total_exenta is None:
        total_exenta = Decimal("0")
    if total_general is None:
        total_general = Decimal("220000")

    return FacturaSimple(
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        fecha_emision=fecha_emision,
        emisor=emisor,
        receptor=receptor,
        items=items,
        total_iva=total_iva,
        total_gravada=total_gravada,
        total_exenta=total_exenta,
        total_general=total_general,
        moneda=moneda,
        tipo_cambio=tipo_cambio
    )
