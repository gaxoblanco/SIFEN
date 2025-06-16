"""
Tests de integración con esquemas XSD SIFEN v150

Valida la integración completa entre el generador XML y los esquemas XSD oficiales,
asegurando que el XML generado cumple perfectamente con las especificaciones SIFEN.

Tests incluidos:
- Validación contra esquemas XSD oficiales
- Compatibilidad con diferentes tipos de documento
- Integridad de namespaces y referencias
- Validaciones complejas de estructura
- Casos de integración schema-generator
"""
import pytest
from decimal import Decimal
from datetime import datetime
from lxml import etree
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator, SifenValidationError
from ..models import ItemFactura


@pytest.fixture
def validator():
    """Fixture del validador XML"""
    return XMLValidator()


@pytest.fixture
def xml_generator():
    """Fixture del generador XML"""
    return XMLGenerator()


def test_schema_validation_complete_document(xml_generator, validator):
    """Test para validación completa del documento contra schema XSD"""
    factura = create_factura_base()
    xml = xml_generator.generate_simple_invoice_xml(factura)

    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"Documento no válido contra schema XSD: {errors}"
    assert len(errors) == 0, "No debe haber errores de validación"


def test_schema_namespace_integration(xml_generator, validator):
    """Test para validar integración completa de namespaces"""
    factura = create_factura_base()
    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar namespaces requeridos por schema
    assert 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml
    assert 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' in xml
    assert 'xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd"' in xml

    # Validar que el documento es válido con estos namespaces
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Namespaces causan invalidez: {errors}"


def test_schema_version_compatibility(xml_generator, validator):
    """Test para validar compatibilidad con versión de schema"""
    factura = create_factura_base()
    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar versión específica SIFEN v150
    assert '<dVerFor>150</dVerFor>' in xml, "Versión de formato incorrecta"

    # Validar que la versión es compatible con el schema
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Versión incompatible con schema: {errors}"


def test_schema_document_type_integration():
    """Test para validar integración de tipos de documento con schema"""
    xml_generator = XMLGenerator()
    validator = XMLValidator()

    # Test diferentes tipos de documento según SIFEN v150
    tipos_documento = {
        "1": "Factura Electrónica",
        "4": "Autofactura Electrónica",
        "5": "Nota de Crédito Electrónica",
        "6": "Nota de Débito Electrónica",
        "7": "Nota de Remisión Electrónica"
    }

    for tipo_codigo, tipo_nombre in tipos_documento.items():
        factura = create_factura_base(
            tipo_documento=tipo_codigo,
            fecha_emision=datetime(2024, 1, 1, 12, 0, 0)
        )
        xml = xml_generator.generate_simple_invoice_xml(factura)

        # Validar que el tipo se genera correctamente
        assert f'<iTipDE>{tipo_codigo}</iTipDE>' in xml, f"Tipo {tipo_nombre} mal generado"

        # Validar contra schema
        is_valid, errors = validator.validate_xml(xml)
        assert is_valid, f"Tipo {tipo_nombre} inválido contra schema: {errors}"


def test_schema_cdc_structure_integration(xml_generator, validator):
    """Test para validar integración completa de estructura CDC"""
    factura = create_factura_base()
    factura.numero_documento = "001-001-0000001"

    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar estructura CDC en XML generado
    assert '<dNumID>001-001-0000001</dNumID>' in xml

    # Validar que la estructura es válida según schema
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Estructura CDC inválida según schema: {errors}"

    # Validar elementos CDC específicos que requiere el schema
    assert '<dEst>001</dEst>' in xml, "Establecimiento faltante"
    assert '<dPunExp>001</dPunExp>' in xml, "Punto expedición faltante"
    assert '<dNumDoc>0000001</dNumDoc>' in xml, "Número documento faltante"


def test_schema_monetary_fields_integration(xml_generator, validator):
    """Test para validar integración de campos monetarios con schema"""
    factura = create_factura_base()
    factura.total_gravada = Decimal("250000")
    factura.total_iva = Decimal("25000")
    factura.total_general = Decimal("275000")

    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar formato monetario según schema (sin separadores)
    assert '<dTotGralOpe>275000</dTotGralOpe>' in xml
    assert '<dTotIVA>25000</dTotIVA>' in xml

    # Validar contra schema
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Campos monetarios inválidos según schema: {errors}"


def test_schema_date_format_integration(xml_generator, validator):
    """Test para validar integración de formato de fechas con schema"""
    factura = create_factura_base()
    factura.fecha_emision = datetime(2024, 12, 25, 14, 30, 0)

    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar formato ISO 8601 requerido por schema
    assert '<dFeEmiDE>2024-12-25T14:30:00</dFeEmiDE>' in xml

    # Validar contra schema
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Formato de fecha inválido según schema: {errors}"


def test_schema_currency_integration(xml_generator, validator):
    """Test para validar integración de moneda con schema"""
    factura = create_factura_base()
    factura.moneda = "PYG"
    factura.tipo_cambio = Decimal("1.00")

    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar códigos de moneda según schema
    assert '<cMoneOpe>PYG</cMoneOpe>' in xml
    assert '<dTiCam>1.00</dTiCam>' in xml

    # Validar contra schema
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Configuración de moneda inválida según schema: {errors}"


def test_schema_complex_items_integration(xml_generator, validator):
    """Test para validar integración de items complejos con schema"""
    factura = create_factura_base()

    # Crear items con diferentes configuraciones
    items_complejos = [
        ItemFactura(
            codigo="PROD001",
            descripcion="Producto gravado con IVA 10%",
            cantidad=Decimal("2.5"),
            precio_unitario=Decimal("40000"),
            iva=Decimal("10"),
            monto_total=Decimal("100000")
        ),
        ItemFactura(
            codigo="SERV001",
            descripcion="Servicio exento de IVA",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("50000"),
            iva=Decimal("0"),
            monto_total=Decimal("50000")
        ),
        ItemFactura(
            codigo="PROD002",
            descripcion="Producto con IVA 5%",
            cantidad=Decimal("3"),
            precio_unitario=Decimal("20000"),
            iva=Decimal("5"),
            monto_total=Decimal("60000")
        )
    ]

    factura.items = items_complejos
    factura.total_gravada = Decimal("160000")
    factura.total_iva = Decimal("13000")  # 10000 + 0 + 3000
    factura.total_exenta = Decimal("50000")
    factura.total_general = Decimal("210000")

    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar que todos los items se procesan según schema
    for item in items_complejos:
        assert item.codigo in xml, f"Código {item.codigo} faltante"
        assert item.descripcion in xml, f"Descripción {item.descripcion} faltante"

    # Validar contra schema
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Items complejos inválidos según schema: {errors}"


def test_schema_contributor_data_integration(xml_generator, validator):
    """Test para validar integración de datos de contribuyentes con schema"""
    factura = create_factura_base()

    # Configurar datos específicos que requiere el schema
    factura.emisor.ruc = "12345678"
    factura.emisor.dv = "9"
    factura.emisor.razon_social = "EMPRESA DE PRUEBA S.A."
    factura.emisor.codigo_departamento = "11"
    factura.emisor.codigo_ciudad = "101"

    factura.receptor.ruc = "87654321"
    factura.receptor.dv = "0"
    factura.receptor.razon_social = "CLIENTE DE PRUEBA S.A."
    factura.receptor.codigo_departamento = "11"
    factura.receptor.codigo_ciudad = "101"

    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar estructura de contribuyentes según schema
    assert '<dRucEmi>12345678</dRucEmi>' in xml
    assert '<dDVEmi>9</dDVEmi>' in xml
    assert '<dRucRec>87654321</dRucRec>' in xml
    assert '<dDVRec>0</dDVRec>' in xml

    # Validar contra schema
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Datos de contribuyentes inválidos según schema: {errors}"


def test_schema_validation_error_handling(xml_generator):
    """Test para validar manejo de errores de schema"""
    # Crear documento intencionalmente inválido
    factura = create_factura_base()
    factura.numero_documento = "INVALID"  # Formato inválido

    xml = xml_generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    # Debe detectar el error de formato
    assert not is_valid, "Debe detectar documento inválido"
    assert len(errors) > 0, "Debe reportar errores específicos"
    assert any("pattern" in error.lower() or "formato" in error.lower()
               for error in errors), "Debe detectar error de formato"


def test_schema_encoding_integration(xml_generator, validator):
    """Test para validar integración de encoding con schema"""
    factura = create_factura_base()

    # Usar caracteres especiales permitidos
    factura.emisor.razon_social = "EMPRESA ÑANDÚ & COMPAÑÍA S.A."
    factura.receptor.razon_social = "CLIENTE GÜEMBÉ Y ASOCIADOS S.A."

    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar declaración de encoding
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml

    # Validar que caracteres especiales se manejan correctamente
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Encoding UTF-8 causa problemas con schema: {errors}"


def test_schema_root_element_integration(xml_generator, validator):
    """Test para validar integración del elemento raíz con schema"""
    factura = create_factura_base()
    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Parsear XML para validar estructura
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml.encode('utf-8'), parser)
    except etree.XMLSyntaxError as e:
        pytest.fail(f"XML mal formado: {e}")

    # Validar elemento raíz según schema
    assert root.tag.endswith('}rDE'), "Elemento raíz incorrecto"
    assert root.get('Id'), "Atributo Id faltante en elemento raíz"

    # Validar contra schema completo
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Elemento raíz inválido según schema: {errors}"


def test_schema_conditional_elements_integration(xml_generator, validator):
    """Test para validar elementos condicionales según schema"""
    factura = create_factura_base()

    # Configurar condiciones específicas
    factura.condicion_venta = "2"  # Crédito
    factura.condicion_operacion = "1"  # Normal

    xml = xml_generator.generate_simple_invoice_xml(factura)

    # Validar elementos condicionales generados
    assert '<iCondVent>2</iCondVent>' in xml
    assert '<iCondOpe>1</iCondOpe>' in xml

    # Validar contra schema
    is_valid, errors = validator.validate_xml(xml)
    assert is_valid, f"Elementos condicionales inválidos según schema: {errors}"


def test_schema_full_integration_stress():
    """Test de integración completa bajo estrés"""
    xml_generator = XMLGenerator()
    validator = XMLValidator()

    # Generar múltiples documentos con configuraciones diferentes
    configuraciones = [
        {"tipo_documento": "1", "moneda": "PYG",
            "fecha_emision": datetime(2024, 1, 1, 12, 0, 0)},
        {"tipo_documento": "5", "moneda": "USD",
            "fecha_emision": datetime(2024, 1, 2, 12, 0, 0)},
        {"tipo_documento": "6", "moneda": "EUR",
            "fecha_emision": datetime(2024, 1, 3, 12, 0, 0)},
    ]

    for config in configuraciones:
        factura = create_factura_base(**config)

        # Agregar múltiples items
        for i in range(10):
            factura.items.append(
                ItemFactura(
                    codigo=f"ITEM{i:03d}",
                    descripcion=f"Producto de prueba {i}",
                    cantidad=Decimal("1"),
                    precio_unitario=Decimal("10000"),
                    iva=Decimal("10"),
                    monto_total=Decimal("10000")
                )
            )

        # Recalcular totales
        factura.total_gravada = Decimal("110000")  # 10 items + 1 original
        factura.total_iva = Decimal("11000")
        factura.total_general = Decimal("121000")

        xml = xml_generator.generate_simple_invoice_xml(factura)

        # Validar cada documento contra schema
        is_valid, errors = validator.validate_xml(xml)
        assert is_valid, f"Configuración {config} inválida: {errors}"
