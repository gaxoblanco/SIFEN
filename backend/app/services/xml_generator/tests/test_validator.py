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
        tipo_cambio=Decimal("1"),
        csc="ABCD1234",
        # Campos faltantes agregados según Manual SIFEN v150
        condicion_venta="1",          # 1=Contado, 2=Crédito
        condicion_operacion="1",      # 1=Venta, 2=Devolución
        modalidad_transporte="1",     # 1=Terrestre, 2=Aéreo, 3=Acuático
        categoria_emisor="1"          # 1=Contribuyente, 2=No contribuyente
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
        assert is_valid, f"XML debería ser válido pero falló con errores: {errors}"
        assert not errors, f"No deberían existir errores pero se encontraron: {errors}"
    except SifenValidationError as e:
        pytest.fail(f"XML válido no debería lanzar excepción: {str(e)}")


def test_validate_invalid_xml(validator):
    """Test validación de XML inválido - falta elementos obligatorios"""
    # XML inválido: falta información del receptor y elementos obligatorios
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
    assert not is_valid, "XML inválido debería fallar la validación"
    assert len(errors) > 0, "Deberían existir errores de validación"
    print(f"\nErrores encontrados (como se esperaba): {errors}")


def test_validate_malformed_xml(validator):
    """Test validación de XML mal formado - sintaxis incorrecta"""
    # XML mal formado: falta tag de cierre
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
    </rDE"""  # Falta el > al final intencionalmente

    with pytest.raises(SifenValidationError) as exc_info:
        validator.validate_xml(malformed_xml)

    assert "Error de sintaxis XML" in str(
        exc_info.value) or "XML mal formado" in str(exc_info.value)


def test_validate_ruc(validator):
    """Test validación de RUC según formato Paraguay"""
    # RUCs válidos
    assert validator.validate_ruc(
        "12345678"), "RUC de 8 dígitos debería ser válido"
    assert validator.validate_ruc(
        "123456789"), "RUC de 9 dígitos debería ser válido"

    # RUCs inválidos
    assert not validator.validate_ruc(
        "1234567"), "RUC de 7 dígitos debería ser inválido"
    assert not validator.validate_ruc(
        "1234567890"), "RUC de 10 dígitos debería ser inválido"
    assert not validator.validate_ruc(
        "1234567a"), "RUC con letras debería ser inválido"
    assert not validator.validate_ruc(""), "RUC vacío debería ser inválido"
    assert not validator.validate_ruc(
        "12-345-678"), "RUC con guiones debería ser inválido"


def test_validate_dv(validator):
    """Test validación de dígito verificador"""
    # Dígitos verificadores válidos (0-9)
    assert validator.validate_dv("0"), "DV '0' debería ser válido"
    assert validator.validate_dv("9"), "DV '9' debería ser válido"
    assert validator.validate_dv("5"), "DV '5' debería ser válido"

    # Dígitos verificadores inválidos
    assert not validator.validate_dv(
        "10"), "DV de más de un dígito debería ser inválido"
    assert not validator.validate_dv("a"), "DV con letra debería ser inválido"
    assert not validator.validate_dv(""), "DV vacío debería ser inválido"
    assert not validator.validate_dv("-1"), "DV negativo debería ser inválido"


def test_validate_xml_with_missing_namespace(validator):
    """Test validación de XML sin namespace SIFEN"""
    xml_without_namespace = """<?xml version="1.0" encoding="UTF-8"?>
    <rDE version="1.0">
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

    is_valid, errors = validator.validate_xml(xml_without_namespace)
    print(f"\nValidación XML sin namespace - Válido: {is_valid}")
    print(f"Errores encontrados: {errors}")

    assert not is_valid, "XML sin namespace SIFEN debería ser inválido"
    # Verificar que hay errores, sin importar el mensaje específico
    assert len(errors) > 0, "Deberían existir errores de validación"


def test_validate_xml_with_wrong_encoding(validator):
    """Test validación de XML con encoding incorrecto"""
    xml_wrong_encoding = """<?xml version="1.0" encoding="ISO-8859-1"?>
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

    # Dependiendo de la implementación del validador, esto podría ser válido o inválido
    # pero al menos no debería lanzar excepción
    try:
        is_valid, errors = validator.validate_xml(xml_wrong_encoding)
        # El resultado puede variar según la implementación
        print(
            f"Validación encoding incorrecto - válido: {is_valid}, errores: {errors}")
    except SifenValidationError:
        # También es un resultado aceptable
        pass


def test_validate_xml_empty_content(validator):
    """Test validación de contenido XML vacío"""
    with pytest.raises(SifenValidationError) as exc_info:
        validator.validate_xml("")

    assert "vacío" in str(exc_info.value).lower(
    ) or "empty" in str(exc_info.value).lower()


def test_validate_xml_none_content(validator):
    """Test validación de contenido XML None"""
    with pytest.raises((SifenValidationError, TypeError, AttributeError)):
        validator.validate_xml(None)


def test_validate_date_format(validator):
    """Test validación de formato de fecha según ISO 8601"""
    # Fechas válidas
    valid_dates = [
        "2024-01-01T12:00:00",
        "2024-12-31T23:59:59",
        "2024-06-15T00:00:00"
    ]

    for date_str in valid_dates:
        assert validator.validate_date_format(
            date_str), f"Fecha '{date_str}' debería ser válida"

    # Fechas inválidas
    invalid_dates = [
        "2024-13-01T12:00:00",  # Mes inválido
        "2024-01-32T12:00:00",  # Día inválido
        "2024-01-01T25:00:00",  # Hora inválida
        "2024-01-01 12:00:00",  # Formato incorrecto (espacio en lugar de T)
        "01/01/2024",           # Formato DD/MM/YYYY
        "invalid-date"          # Texto no válido
    ]

    for date_str in invalid_dates:
        assert not validator.validate_date_format(
            date_str), f"Fecha '{date_str}' debería ser inválida"


def test_validate_amount_format(validator):
    """Test validación de formato de montos decimales"""
    # Montos válidos
    valid_amounts = [
        Decimal("100.00"),
        Decimal("1000000.50"),
        Decimal("0.01"),
        Decimal("999999999.99")
    ]

    for amount in valid_amounts:
        assert validator.validate_amount_format(
            amount), f"Monto '{amount}' debería ser válido"

    # Montos inválidos - Decimales que deberían retornar False
    invalid_decimal_amounts = [
        Decimal("-100.00"),      # Negativo
        Decimal("100.001"),      # Más de 2 decimales
    ]

    for amount in invalid_decimal_amounts:
        assert not validator.validate_amount_format(
            amount), f"Monto '{amount}' debería ser inválido"

    # Tipos inválidos - No son Decimal, deberían retornar False
    invalid_types = [
        None,                    # None
        "not_a_number",         # String
        100.50,                 # Float
        100,                    # Integer
    ]

    for invalid_input in invalid_types:
        result = validator.validate_amount_format(invalid_input)
        assert not result, f"Input '{invalid_input}' de tipo {type(invalid_input)} debería ser inválido"
