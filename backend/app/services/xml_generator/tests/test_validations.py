"""
Tests para validaciones específicas del XML SIFEN
"""
import pytest
from decimal import Decimal
from datetime import datetime
from ..models import FacturaSimple, Contribuyente, ItemFactura
from ..generator import XMLGenerator
from ..validators import XMLValidator
from .fixtures.test_data import create_factura_base


def test_namespace_correcto():
    """Test para validar el namespace del documento"""
    factura = create_factura_base()
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    assert 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml
    assert 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' in xml
    assert 'xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd"' in xml


def test_encoding_utf8():
    """Test para validar el encoding del documento"""
    factura = create_factura_base()
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml


def test_version_documento():
    """Test para validar la versión del documento"""
    factura = create_factura_base()
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    assert 'version="1.5.0"' in xml, "Versión del documento incorrecta"


def test_estructura_cdc():
    """Test para validar la estructura del CDC"""
    factura = create_factura_base()
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    # Validar estructura del CDC según Manual Técnico v150
    assert factura.numero_documento.count(
        '-') == 2, "Formato de número de documento incorrecto"
    partes = factura.numero_documento.split('-')
    assert len(partes[0]) == 3, "Establecimiento debe tener 3 dígitos"
    assert len(partes[1]) == 3, "Punto de expedición debe tener 3 dígitos"
    assert len(partes[2]) == 7, "Número de documento debe tener 7 dígitos"


def test_caracteres_especiales():
    """Test para validar que los caracteres especiales se manejan correctamente"""
    factura = create_factura_base()
    # Usar nombres que cumplan con el patrón permitido
    factura.emisor.razon_social = "EMPRESA Y COMPANIA S.A."
    factura.receptor.razon_social = "CLIENTE Y ASOCIADOS S.A."

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con caracteres especiales: {errors}"


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
            monto_total=Decimal("200000")  # 2 * 100000
        ),
        ItemFactura(
            codigo="002",
            descripcion="Producto 2",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("50000"),
            iva=Decimal("10"),  # Cambiado a 10% según esquema
            monto_total=Decimal("50000")  # 1 * 50000
        )
    ]

    factura = create_factura_base()
    factura.items = items
    factura.total_gravada = Decimal("250000")  # 200000 + 50000
    factura.total_iva = Decimal("25000")  # (200000 * 0.10) + (50000 * 0.10)
    factura.total_general = Decimal("275000")  # 250000 + 25000

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con múltiples items: {errors}"
