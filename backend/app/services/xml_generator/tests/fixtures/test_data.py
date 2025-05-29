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
    tipo_documento: str = "1",  # 1 = Factura
    numero_documento: str = "001-001-0000001",
    fecha_emision: datetime = datetime.now(),
    ruc_emisor: str = "12345678",
    razon_social_emisor: str = "EMPRESA DE PRUEBA S.A.",
    direccion_emisor: str = "AVENIDA PRINCIPAL 123",
    telefono_emisor: str = "0981123456",
    email_emisor: str = "contacto@empresa.com",
    ruc_receptor: str = "98765432",
    razon_social_receptor: str = "CLIENTE DE PRUEBA S.A.",
    direccion_receptor: str = "CALLE SECUNDARIA 456",
    telefono_receptor: str = "0987654321",
    email_receptor: str = "contacto@cliente.com",
    csc: str = "ABCD1234"
) -> FacturaSimple:
    """Crea una factura base para testing"""
    emisor = Contribuyente(
        ruc=ruc_emisor,
        razon_social=razon_social_emisor,
        direccion=direccion_emisor,
        telefono=telefono_emisor,
        email=email_emisor,
        dv="9",
        numero_casa="123",
        codigo_departamento="11",
        codigo_ciudad="101",
        descripcion_ciudad="ASUNCION"
    )

    receptor = Contribuyente(
        ruc=ruc_receptor,
        razon_social=razon_social_receptor,
        direccion=direccion_receptor,
        telefono=telefono_receptor,
        email=email_receptor,
        dv="1",
        numero_casa="456",
        codigo_departamento="11",
        codigo_ciudad="101",
        descripcion_ciudad="ASUNCION"
    )

    items = [
        ItemFactura(
            codigo="001",
            descripcion="Producto de prueba",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100000"),
            iva=Decimal("10"),
            monto_total=Decimal("100000")
        )
    ]

    return FacturaSimple(
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        fecha_emision=fecha_emision,
        emisor=emisor,
        receptor=receptor,
        items=items,
        total_gravada=Decimal("100000"),
        total_iva=Decimal("10000"),
        total_exenta=Decimal("0"),
        total_general=Decimal("110000"),
        moneda="PYG",
        tipo_cambio=Decimal("1.00"),  # Valor por defecto para PYG
        csc=csc,
        condicion_venta="1",  # 1: Contado
        condicion_operacion="1",  # 1: Normal
        modalidad_transporte="1",  # 1: Terrestre
        categoria_emisor="1"  # 1: Normal
    )
