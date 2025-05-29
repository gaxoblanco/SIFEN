"""
Tests para casos límite del XML
"""
from decimal import Decimal
from datetime import datetime
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator


def test_montos_cero():
    """Test para validar factura con montos en cero"""
    factura = create_factura_base(
        total_iva=Decimal("0"),
        total_gravada=Decimal("0"),
        total_general=Decimal("0")
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con montos en cero: {errors}"
    assert "<dTotGralOpe>0</dTotGralOpe>" in xml, "Total general debe ser 0"
    # Verificamos que los 5 totales estén presentes y sean 0
    totales = xml.count("<dTotGralOpe>0</dTotGralOpe>")
    assert totales == 5, f"Deben haber 5 totales, se encontraron {totales}"


def test_montos_negativos():
    """Test para validar factura con montos negativos (nota de crédito)"""
    factura = create_factura_base(
        tipo_documento="3",  # 3: Nota de Crédito
        total_iva=Decimal("-10000"),
        total_gravada=Decimal("-100000"),
        total_general=Decimal("-110000")
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con montos negativos: {errors}"
    # Verificamos que los 5 totales estén presentes y sean negativos
    assert "<dTotGralOpe>-110000</dTotGralOpe>" in xml, "Total general debe ser negativo"
    totales = xml.count("<dTotGralOpe>")
    assert totales == 5, f"Deben haber 5 totales, se encontraron {totales}"


def test_montos_grandes():
    """Test para validar factura con montos grandes"""
    factura = create_factura_base(
        total_iva=Decimal("1000000000"),
        total_gravada=Decimal("10000000000"),
        total_general=Decimal("11000000000")
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con montos grandes: {errors}"
    assert "<dTotGralOpe>11000000000</dTotGralOpe>" in xml, "Total general incorrecto"
    totales = xml.count("<dTotGralOpe>")
    assert totales == 5, f"Deben haber 5 totales, se encontraron {totales}"


def test_fecha_limite():
    """Test para validar factura con fecha límite"""
    factura = create_factura_base(
        fecha_emision=datetime(2024, 12, 31, 23, 59, 59)
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con fecha límite: {errors}"
    assert "<dFeEmiDE>2024-12-31T23:59:59</dFeEmiDE>" in xml, "Fecha incorrecta"


def test_ruc_especial():
    """Test para validar factura con RUC especial (consumidor final)"""
    factura = create_factura_base()
    factura.receptor.ruc = "99999999-9"
    factura.receptor.razon_social = "CONSUMIDOR FINAL"

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con RUC especial: {errors}"
    assert "<dNumID>99999999-9</dNumID>" in xml, "RUC especial incorrecto"
    assert "<dNomRec>CONSUMIDOR FINAL</dNomRec>" in xml, "Nombre incorrecto"


def test_descripcion_larga():
    """Test para validar factura con descripción larga"""
    factura = create_factura_base()
    # SIFEN permite máximo 200 caracteres para descripción
    factura.items[0].descripcion = "X" * 200

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con descripción larga: {errors}"
    # Verificar que existe la sección de items/detalles
    assert "<gItem>" in xml, "Debe existir la sección de items"
    # Verificar la descripción dentro de la sección de items
    assert f"<dDesPro>{'X' * 200}</dDesPro>" in xml, "Descripción larga incorrecta"
