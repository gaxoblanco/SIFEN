"""
Tests para el validador XML
"""
import pytest
from ..validators import XMLValidator, SifenValidationError
from ..generator import XMLGenerator
from ..models import FacturaSimple, Contribuyente, ItemFactura
from datetime import datetime
from decimal import Decimal


@pytest.fixture
def validator():
    """Fixture con el validador XML"""
    return XMLValidator()


@pytest.fixture
def xml_generator():
    """Fixture con el generador XML"""
    return XMLGenerator()


@pytest.fixture
def factura_valida():
    """Fixture con una factura válida"""
    emisor = Contribuyente(
        ruc="12345678",
        dv="9",
        razon_social="EMPRESA DE PRUEBA S.A.",
        direccion="Av. Principal",
        numero_casa="123",
        codigo_departamento="1",
        codigo_ciudad="1",
        descripcion_ciudad="ASUNCION",
        telefono="0981123456",
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
        telefono="0987654321",
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
        )
    ]

    return FacturaSimple(
        tipo_documento="1",
        numero_documento="001-001-0000001",
        fecha_emision=datetime(2024, 1, 1, 12, 0, 0),
        emisor=emisor,
        receptor=receptor,
        items=items,
        total_iva=Decimal("20000"),
        total_gravada=Decimal("200000"),
        total_exenta=Decimal("0"),
        total_general=Decimal("220000"),
        moneda="PYG",
        tipo_cambio=None,
        csc="ABCD1234"
    )


def test_validate_valid_xml(validator, xml_generator, factura_valida):
    """Test validación de XML válido"""
    xml = xml_generator.generate_simple_invoice_xml(factura_valida)
    print("\nXML generado:")
    print(xml)
    try:
        is_valid, errors = validator.validate_xml(xml)
        if not is_valid:
            print("\nErrores de validación:")
            for error in errors:
                print(f"- {error}")
        assert is_valid
        assert not errors
    except SifenValidationError as e:
        pytest.fail(f"XML válido no debería lanzar excepción: {str(e)}")


def test_validate_invalid_xml(validator):
    """Test validación de XML inválido"""
    invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd" version="1.0">
        <DE>
            <gDE>
                <dID>
                    <iTipDE>1</iTipDE>
                    <dNumID>001-001-0000001</dNumID>
                    <dFeEmiDE>2024-01-01T12:00:00</dFeEmiDE>
                </dID>
            </gDE>
        </DE>
    </rDE>"""

    is_valid, errors = validator.validate_xml(invalid_xml)
    assert not is_valid
    assert len(errors) > 0


def test_validate_malformed_xml(validator):
    """Test validación de XML mal formado"""
    malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rDE>
        <DE>
            <gDE>
                <dID>
                    <iTipDE>1</iTipDE>
                    <dNumID>001-001-0000001</dNumID>
                    <dFeEmiDE>2024-01-01T12:00:00</dFeEmiDE>
                </dID>
            </gDE>
        </DE>
    </rDE"""

    with pytest.raises(SifenValidationError) as exc_info:
        validator.validate_xml(malformed_xml)

    assert "Error de sintaxis XML" in str(exc_info.value)


def test_validate_ruc(validator):
    """Test validación de RUC"""
    assert validator.validate_ruc("12345678")  # 8 dígitos
    assert validator.validate_ruc("123456789")  # 9 dígitos
    assert not validator.validate_ruc("1234567")  # 7 dígitos
    assert not validator.validate_ruc("1234567890")  # 10 dígitos
    assert not validator.validate_ruc("1234567a")  # No numérico


def test_validate_dv(validator):
    """Test validación de dígito verificador"""
    assert validator.validate_dv("0")
    assert validator.validate_dv("9")
    assert not validator.validate_dv("10")  # Más de un dígito
    assert not validator.validate_dv("a")  # No numérico
