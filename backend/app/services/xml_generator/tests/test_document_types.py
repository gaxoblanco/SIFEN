"""
Tests para los diferentes tipos de documentos electrónicos
"""
from decimal import Decimal
from datetime import datetime
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator


def test_factura_electronica():
    """Test para Factura Electrónica (FE)"""
    factura = create_factura_base(
        tipo_documento="1",  # 1 = Factura Electrónica
        numero_documento="001-001-0000001"
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido: {errors}"
    assert "<iTipDE>1</iTipDE>" in xml, "Debe ser una Factura Electrónica"


def test_autofactura_electronica():
    """Test para Autofactura Electrónica (AFE)"""
    factura = create_factura_base(
        tipo_documento="2",  # 2 = Autofactura Electrónica
        numero_documento="001-001-0000002"
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido: {errors}"
    assert "<iTipDE>2</iTipDE>" in xml, "Debe ser una Autofactura Electrónica"


def test_nota_credito():
    """Test para Nota de Crédito (NCE)"""
    factura = create_factura_base(
        tipo_documento="3",  # 3 = Nota de Crédito
        numero_documento="001-001-0000003"
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido: {errors}"
    assert "<iTipDE>3</iTipDE>" in xml, "Debe ser una Nota de Crédito"


def test_nota_debito():
    """Test para Nota de Débito (NDE)"""
    factura = create_factura_base(
        tipo_documento="4",  # 4 = Nota de Débito
        numero_documento="001-001-0000004"
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido: {errors}"
    assert "<iTipDE>4</iTipDE>" in xml, "Debe ser una Nota de Débito"


def test_nota_remision():
    """Test para Nota de Remisión (NRE)"""
    factura = create_factura_base(
        tipo_documento="5",  # 5 = Nota de Remisión
        numero_documento="001-001-0000005"
    )

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido: {errors}"
    assert "<iTipDE>5</iTipDE>" in xml, "Debe ser una Nota de Remisión"
