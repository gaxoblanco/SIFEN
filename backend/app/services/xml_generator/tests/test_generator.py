"""
Tests para el generador XML
"""
import pytest
from datetime import datetime
from decimal import Decimal
from ..models import FacturaSimple, Contribuyente, ItemFactura
from ..generator import XMLGenerator


@pytest.fixture
def factura_simple():
    """Fixture con datos de prueba para una factura simple"""
    emisor = Contribuyente(
        ruc="12345678",
        dv="9",
        razon_social="EMPRESA DE PRUEBA S.A.",
        direccion="Av. Principal",
        numero_casa="123",
        codigo_departamento="1",
        codigo_ciudad="1",
        descripcion_ciudad="ASUNCION",
        telefono="021123456",
        email="test@empresa.com"
    )

    receptor = Contribuyente(
        ruc="87654321",
        dv="0",
        razon_social="CLIENTE DE PRUEBA S.A.",
        direccion="Av. Secundaria",
        numero_casa="456",
        codigo_departamento="1",
        codigo_ciudad="1",
        descripcion_ciudad="ASUNCION",
        telefono="021654321",
        email="test@cliente.com"
    )

    items = [
        ItemFactura(
            codigo="001",
            descripcion="Producto 1",
            cantidad=Decimal("2"),
            precio_unitario=Decimal("100000"),
            iva=Decimal("10"),
            monto_total=Decimal("200000")
        ),
        ItemFactura(
            codigo="002",
            descripcion="Producto 2",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("50000"),
            iva=Decimal("10"),
            monto_total=Decimal("50000")
        )
    ]

    return FacturaSimple(
        tipo_documento="1",
        numero_documento="001-001-0000001",
        fecha_emision=datetime(2024, 1, 1, 12, 0, 0),
        emisor=emisor,
        receptor=receptor,
        items=items,
        total_iva=Decimal("25000"),
        total_gravada=Decimal("250000"),
        total_exenta=Decimal("0"),
        total_general=Decimal("275000"),
        moneda="PYG",
        tipo_cambio=Decimal("1.00"),
        csc="ABCD1234",
        condicion_venta="1",
        condicion_operacion="1",
        modalidad_transporte="1",
        categoria_emisor="1"
    )


def test_generate_simple_invoice_xml(factura_simple):
    """Test generación XML factura simple"""
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura_simple)

    # Validaciones básicas del XML generado
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
    assert 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml
    assert 'version="1.5.0"' in xml
    assert factura_simple.numero_documento in xml
    assert factura_simple.emisor.ruc in xml
    assert factura_simple.receptor.ruc in xml
    assert str(factura_simple.total_general) in xml
    assert factura_simple.csc in xml

    # Validar estructura de items
    for item in factura_simple.items:
        assert item.codigo in xml
        assert item.descripcion in xml
        assert str(item.cantidad) in xml
        assert str(item.precio_unitario) in xml
        assert str(item.monto_total) in xml
        assert str(item.iva) in xml
