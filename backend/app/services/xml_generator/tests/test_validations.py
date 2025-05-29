"""
Tests para validaciones específicas del XML
"""
from decimal import Decimal
from datetime import datetime
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator


def test_namespace_correcto():
    """Test para validar que el namespace es correcto"""
    factura = create_factura_base()
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    assert 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml, "Namespace incorrecto"


def test_encoding_utf8():
    """Test para validar que el encoding es UTF-8"""
    factura = create_factura_base()
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml, "Encoding incorrecto"


def test_version_documento():
    """Test para validar la versión del documento"""
    factura = create_factura_base()
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    assert '<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd" version="1.0">' in xml, "Versión o namespace del documento incorrecto"


def test_estructura_cdc():
    """Test para validar la estructura del CDC"""
    factura = create_factura_base(
        numero_documento="001-001-0000001"  # Formato: XXX-XXX-XXXXXXXXXX
    )
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    # Validar que el número de documento tiene el formato correcto
    assert "<dNumID>001-001-0000001</dNumID>" in xml, "Formato de CDC incorrecto"


def test_caracteres_especiales():
    """Test para validar que los caracteres especiales se manejan correctamente"""
    factura = create_factura_base()
    factura.emisor.razon_social = "Empresa & Compañía S.A."
    factura.receptor.razon_social = "Cliente & Asociados S.A."

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con caracteres especiales: {errors}"
    assert "&amp;" in xml, "Caracteres especiales no escapados correctamente"


def test_multiple_items():
    """Test para validar factura con múltiples items"""
    from ..models import ItemFactura

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
            iva=Decimal("5"),
            monto_total=Decimal("52500")
        )
    ]

    factura = create_factura_base(
        items=items,
        total_iva=Decimal("25250"),
        total_gravada=Decimal("250000"),
        total_general=Decimal("275250")
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con múltiples items: {errors}"
    assert xml.count("<gItem>") == 2, "Debe tener 2 items"
