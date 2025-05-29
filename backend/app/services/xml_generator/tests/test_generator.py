"""
Tests para el generador XML
"""
from datetime import datetime
from decimal import Decimal
from ..models import Contribuyente, ItemFactura, FacturaSimple
from ..generator import XMLGenerator


def test_generate_simple_invoice_xml():
    # Crear datos de prueba
    emisor = Contribuyente(
        ruc="12345678",
        dv="9",
        razon_social="Empresa de Prueba S.A.",
        direccion="Av. Test 123",
        telefono="021-123456",
        email="test@empresa.com"
    )

    receptor = Contribuyente(
        ruc="87654321",
        dv="0",
        razon_social="Cliente de Prueba S.A.",
        direccion="Av. Cliente 456",
        telefono="021-654321",
        email="test@cliente.com"
    )

    item = ItemFactura(
        codigo="001",
        descripcion="Producto de prueba",
        cantidad=Decimal("2"),
        precio_unitario=Decimal("100000"),
        iva=Decimal("10"),
        monto_total=Decimal("200000")
    )

    factura = FacturaSimple(
        tipo_documento="1",
        numero_documento="001-001-0000001",
        fecha_emision=datetime.now(),
        emisor=emisor,
        receptor=receptor,
        items=[item],
        total_iva=Decimal("20000"),
        total_gravada=Decimal("200000"),
        total_exenta=Decimal("0"),
        total_general=Decimal("220000"),
        moneda="PYG",
        tipo_cambio=None
    )

    # Generar XML
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    # Validaciones básicas
    assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in xml
    assert "<DE version=\"1.0\">" in xml
    assert emisor.ruc in xml
    assert receptor.ruc in xml
    assert item.descripcion in xml
    assert str(item.cantidad) in xml
    assert str(item.precio_unitario) in xml
