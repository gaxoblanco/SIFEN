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
        numero_casa="100",
        codigo_departamento="01",
        codigo_ciudad="001",
        descripcion_ciudad="Asunción",
        telefono="021-123456",
        email="test@empresa.com"
    )

    receptor = Contribuyente(
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

    # Validar contra esquema SIFEN
    from ..validators import XMLValidator
    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"XML inválido: {errors}"

    # Validar estructura básica
    assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in xml
    assert "<rDE xmlns=\"http://ekuatia.set.gov.py/sifen/xsd\" version=\"1.0\">" in xml
    assert "<DE>" in xml
    assert "<gDE>" in xml

    # Validar datos del emisor
    assert f"<dNumID>{emisor.ruc}</dNumID>" in xml
    assert f"<dDV>{emisor.dv}</dDV>" in xml
    assert f"<dNomEmi>{emisor.razon_social}</dNomEmi>" in xml

    # Validar datos del receptor
    assert f"<dNumID>{receptor.ruc}</dNumID>" in xml
    assert f"<dDV>{receptor.dv}</dDV>" in xml
    assert f"<dNomRec>{receptor.razon_social}</dNomRec>" in xml

    # Validar items
    assert "<gItem>" in xml
    assert f"<dCodPro>{item.codigo}</dCodPro>" in xml
    assert f"<dDesPro>{item.descripcion}</dDesPro>" in xml
    assert f"<dCantPro>{item.cantidad}</dCantPro>" in xml
    assert f"<dPreUniPro>{item.precio_unitario}</dPreUniPro>" in xml
    assert f"<dTotPro>{item.monto_total}</dTotPro>" in xml
    assert f"<dPorIVA>{item.iva}</dPorIVA>" in xml

    # Validar totales
    assert "<dTot>" in xml
    assert f"<dTotGralOpe>{factura.total_general}</dTotGralOpe>" in xml
    assert f"<dTotGralOpe>{factura.total_gravada}</dTotGralOpe>" in xml
    assert f"<dTotGralOpe>{factura.total_exenta}</dTotGralOpe>" in xml
    assert f"<dTotGralOpe>{factura.total_iva}</dTotGralOpe>" in xml
