"""
Tests para el validador XML
"""
from datetime import datetime
from decimal import Decimal
from ..models import Contribuyente, ItemFactura, FacturaSimple
from ..generator import XMLGenerator
from ..validators import XMLValidator


def test_validate_valid_xml():
    # Crear datos de prueba válidos
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

    # Validar XML
    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido: {errors}"


def test_validate_invalid_xml():
    # XML inválido (falta el elemento gDE)
    invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <DE version="1.0">
        <invalid_element>test</invalid_element>
    </DE>"""

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(invalid_xml)

    assert not is_valid, "El XML debería ser inválido"
    assert len(errors) > 0, "Debería haber errores de validación"


def test_validate_malformed_xml():
    # XML mal formado (falta cerrar un tag)
    malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <DE version="1.0">
        <gDE>
            <invalid_element>test
    </DE>"""

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(malformed_xml)

    assert not is_valid, "El XML debería ser inválido"
    assert len(errors) > 0, "Debería haber errores de sintaxis"
