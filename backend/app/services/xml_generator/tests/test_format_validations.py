"""
Tests para validaciones de formato específicas del XML SIFEN
"""
import pytest
from decimal import Decimal
from datetime import datetime
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator
from ..models import ItemFactura


def test_formato_fecha():
    """Test para validar formato de fecha"""
    factura = create_factura_base()
    factura.fecha_emision = datetime(2024, 1, 1, 12, 0, 0)

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con formato de fecha: {errors}"
    assert "<dFeEmiDE>2024-01-01T12:00:00</dFeEmiDE>" in xml


def test_formato_numero_documento():
    """Test para validar formato de número de documento"""
    factura = create_factura_base()
    factura.numero_documento = "001-001-0000001"

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con formato de número: {errors}"
    assert "<dNumID>001-001-0000001</dNumID>" in xml


def test_codigos_departamento_ciudad():
    """Test para validar códigos de departamento y ciudad"""
    factura = create_factura_base()
    factura.emisor.codigo_departamento = "001"
    factura.emisor.codigo_ciudad = "001"
    factura.receptor.codigo_departamento = "002"
    factura.receptor.codigo_ciudad = "002"

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con códigos de ubicación: {errors}"
    assert "<cDepEmi>001</cDepEmi>" in xml
    assert "<cCiuEmi>001</cCiuEmi>" in xml
    assert "<cDepRec>002</cDepRec>" in xml
    assert "<cCiuRec>002</cCiuRec>" in xml


def test_formato_telefono():
    """Test para validar formato de teléfono"""
    factura = create_factura_base()
    factura.emisor.telefono = "+595981123456"
    factura.receptor.telefono = "0981123456"

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con formato de teléfono: {errors}"
    assert "<dTelEmi>+595981123456</dTelEmi>" in xml
    assert "<dTelRec>0981123456</dTelRec>" in xml


def test_formato_email():
    """Test para validar formato de email"""
    factura = create_factura_base()
    factura.emisor.email = "contacto@empresa.com.py"
    factura.receptor.email = "cliente@empresa.com.py"

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con formato de email: {errors}"
    assert "<dEmailE>contacto@empresa.com.py</dEmailE>" in xml
    assert "<dEmailRec>cliente@empresa.com.py</dEmailRec>" in xml


def test_longitud_maxima_campos():
    """Test para validar longitudes máximas de campos"""
    factura = create_factura_base()
    # Nombre máximo permitido (100 caracteres)
    factura.emisor.razon_social = "A" * 100
    # Dirección máxima permitida (200 caracteres)
    factura.emisor.direccion = "Calle " + "A" * 194  # Ajustado para no exceder 200
    # Descripción de ciudad máxima (100 caracteres)
    factura.emisor.descripcion_ciudad = "Ciudad " + \
        "A" * 93  # Ajustado para no exceder 100

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con longitudes máximas: {errors}"


def test_montos_maximos():
    """Test para validar montos máximos permitidos"""
    factura = create_factura_base()
    # Monto máximo permitido (999999999.99)
    factura.total_gravada = Decimal("999999999.99")
    factura.total_iva = Decimal("99999999.99")
    # Ajustado al máximo permitido
    factura.total_general = Decimal("999999999.99")

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con montos máximos: {errors}"
    assert "<dTotGralOpe>999999999.99</dTotGralOpe>" in xml


def test_cantidad_maxima_items():
    """Test para validar cantidad máxima de items"""
    factura = create_factura_base()
    # Crear 100 items (límite razonable)
    items = []
    for i in range(100):
        items.append(ItemFactura(
            codigo=f"PROD{i:03d}",
            descripcion=f"Producto {i}",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            iva=Decimal("10"),
            monto_total=Decimal("1000")
        ))
    factura.items = items

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML inválido con cantidad máxima de items: {errors}"
    # Verificar que todos los items están en el XML
    for i in range(100):
        assert f"<dCodPro>PROD{i:03d}</dCodPro>" in xml
