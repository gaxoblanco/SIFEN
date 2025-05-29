"""
Tests para casos límite del generador XML
"""
from decimal import Decimal
from datetime import datetime
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator


def test_montos_cero():
    """Test para validar factura con montos mínimos permitidos"""
    factura = create_factura_base()
    factura.total_iva = Decimal("0.01")
    factura.total_gravada = Decimal("0.01")
    factura.total_general = Decimal("0.01")

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con montos mínimos: {errors}"
    assert "<dTotGralOpe>0.01</dTotGralOpe>" in xml, "Total general debe ser el mínimo permitido"


def test_montos_negativos():
    """Test para validar nota de crédito con montos positivos"""
    factura = create_factura_base()
    factura.tipo_documento = "3"  # 3: Nota de Crédito
    factura.total_iva = Decimal("10000")
    factura.total_gravada = Decimal("100000")
    factura.total_general = Decimal("110000")

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido para nota de crédito: {errors}"
    assert "<iTipDE>3</iTipDE>" in xml, "Debe ser una Nota de Crédito"
    assert "<dTotGralOpe>110000</dTotGralOpe>" in xml, "Total general debe ser positivo"


def test_montos_grandes():
    """Test para validar factura con montos grandes (máximo permitido)"""
    factura = create_factura_base()
    factura.total_iva = Decimal("999999.99")
    factura.total_gravada = Decimal("9999999.99")
    factura.total_general = Decimal("10999999.98")

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con montos grandes: {errors}"
    assert "<dTotGralOpe>10999999.98</dTotGralOpe>" in xml, "Total general debe ser el monto máximo permitido"


def test_ruc_especial():
    """Test para validar factura con RUC especial (consumidor final)"""
    factura = create_factura_base()
    factura.receptor.ruc = "99999999"  # Sin guión para cumplir con el patrón
    factura.receptor.razon_social = "CONSUMIDOR FINAL"

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con RUC especial: {errors}"
    assert "<dNumID>99999999</dNumID>" in xml, "Debe tener el RUC especial"


def test_fecha_limite():
    """Test para validar factura con fecha límite"""
    factura = create_factura_base()
    factura.fecha_emision = datetime(2100, 12, 31, 23, 59, 59)

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con fecha límite: {errors}"
    assert "2100-12-31T23:59:59" in xml, "Debe tener la fecha límite"


def test_caracteres_especiales():
    """Test para validar factura con caracteres permitidos en nombres"""
    factura = create_factura_base()
    factura.emisor.razon_social = "EMPRESA Y CIA. S.A."
    factura.receptor.razon_social = "CLIENTE Y ASOCIADOS S.A."

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con caracteres especiales: {errors}"
    assert "EMPRESA Y CIA. S.A." in xml, "Debe contener el nombre del emisor"
    assert "CLIENTE Y ASOCIADOS S.A." in xml, "Debe contener el nombre del receptor"
