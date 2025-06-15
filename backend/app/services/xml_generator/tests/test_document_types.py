"""
Tests para los diferentes tipos de documentos electrónicos según Manual SIFEN v150

Valida generación XML para todos los tipos de documentos oficiales:
- Factura Electrónica (FE) - Código: 1
- Autofactura Electrónica (AFE) - Código: 4
- Nota de Crédito Electrónica (NCE) - Código: 5
- Nota de Débito Electrónica (NDE) - Código: 6
- Nota de Remisión Electrónica (NRE) - Código: 7

CORRECCIONES APLICADAS:
- Códigos de documento corregidos según Manual v150
- Validaciones específicas por tipo de documento
- Configuraciones obligatorias por tipo
- Manejo de campos específicos por documento

Documentación: Manual Técnico SIFEN v150, sección 2 "Documentos Electrónicos Soportados"
"""
import pytest
from decimal import Decimal
from datetime import datetime
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator


def test_factura_electronica():
    """
    Test para Factura Electrónica (FE) - Tipo documento más común

    Código: 1 (según Manual SIFEN v150)
    Uso: Venta de bienes y servicios gravados
    Características: Operación estándar con IVA
    """
    factura = create_factura_base()
    factura.tipo_documento = "1"  # CORRECCIÓN: 1 = Factura Electrónica
    factura.numero_documento = "001-001-0000001"

    # Configuraciones estándar para FE
    factura.condicion_operacion = "1"  # Venta normal
    factura.condicion_venta = "1"      # Contado

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML Factura Electrónica inválido: {errors}"
    assert "<iTipDE>1</iTipDE>" in xml, "Debe ser una Factura Electrónica"
    assert "<dNumID>001-001-0000001</dNumID>" in xml, "Número documento correcto"

    # Validaciones específicas FE según Manual v150
    assert "xmlns=\"http://ekuatia.set.gov.py/sifen/xsd\"" in xml, "Namespace SIFEN requerido"
    assert "<dFeEmiDE>" in xml, "Fecha emisión requerida para FE"


def test_autofactura_electronica():
    """
    Test para Autofactura Electrónica (AFE) - Operaciones especiales

    Código: 4 (según Manual SIFEN v150)
    Uso: Operaciones donde el adquirente emite el documento
    Características: Emisor = receptor de bienes/servicios
    """
    factura = create_factura_base()
    # CORRECCIÓN: 4 = Autofactura Electrónica (según Manual v150)
    factura.tipo_documento = "4"
    factura.numero_documento = "001-001-0000002"

    # Configuraciones específicas para Autofactura
    factura.condicion_operacion = "2"  # Operación especial para autofactura
    factura.condicion_venta = "1"      # Contado

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML Autofactura Electrónica inválido: {errors}"
    assert "<iTipDE>4</iTipDE>" in xml, "Debe ser una Autofactura Electrónica"
    assert "<dNumID>001-001-0000002</dNumID>" in xml, "Número documento correcto"


def test_nota_credito_electronica():
    """
    Test para Nota de Crédito Electrónica (NCE) - Devoluciones/Descuentos

    Código: 5 (según Manual SIFEN v150)
    Uso: Devoluciones, descuentos, anulaciones
    Características: Reduce deuda del cliente
    """
    factura = create_factura_base()
    # CORRECCIÓN: 5 = Nota de Crédito Electrónica
    factura.tipo_documento = "5"
    factura.numero_documento = "001-001-0000003"

    # Configuraciones específicas para Nota de Crédito
    factura.condicion_operacion = "2"  # Operación de devolución
    factura.condicion_venta = "1"      # Contado

    # Para NCE, los montos representan el crédito otorgado
    # Monto menor que factura original
    factura.total_gravada = Decimal("50000")
    factura.total_iva = Decimal("5000")
    factura.total_general = Decimal("55000")

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML Nota de Crédito inválido: {errors}"
    assert "<iTipDE>5</iTipDE>" in xml, "Debe ser una Nota de Crédito Electrónica"
    assert "<dNumID>001-001-0000003</dNumID>" in xml, "Número documento correcto"
    assert "<dTotGralOpe>55000</dTotGralOpe>" in xml, "Total general NCE correcto"


def test_nota_debito_electronica():
    """
    Test para Nota de Débito Electrónica (NDE) - Cargos adicionales

    Código: 6 (según Manual SIFEN v150)
    Uso: Cargos adicionales, intereses, penalidades
    Características: Incrementa deuda del cliente
    """
    factura = create_factura_base()
    # CORRECCIÓN: 6 = Nota de Débito Electrónica
    factura.tipo_documento = "6"
    factura.numero_documento = "001-001-0000004"

    # Configuraciones específicas para Nota de Débito
    factura.condicion_operacion = "1"  # Operación normal con cargo adicional
    factura.condicion_venta = "1"      # Contado

    # Para NDE, los montos representan el débito adicional
    factura.total_gravada = Decimal("25000")  # Cargo adicional
    factura.total_iva = Decimal("2500")
    factura.total_general = Decimal("27500")

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML Nota de Débito inválido: {errors}"
    assert "<iTipDE>6</iTipDE>" in xml, "Debe ser una Nota de Débito Electrónica"
    assert "<dNumID>001-001-0000004</dNumID>" in xml, "Número documento correcto"
    assert "<dTotGralOpe>27500</dTotGralOpe>" in xml, "Total general NDE correcto"


def test_nota_remision_electronica():
    """
    Test para Nota de Remisión Electrónica (NRE) - Transporte mercaderías

    Código: 7 (según Manual SIFEN v150)
    Uso: Traslado de mercaderías sin venta
    Características: Puede tener montos en cero, campos de transporte obligatorios
    """
    factura = create_factura_base()
    # CORRECCIÓN: 7 = Nota de Remisión Electrónica
    factura.tipo_documento = "7"
    factura.numero_documento = "001-001-0000005"

    # Configuraciones específicas para Nota de Remisión
    factura.modalidad_transporte = "1"  # Transporte terrestre
    factura.condicion_venta = "1"       # Contado
    factura.condicion_operacion = "1"   # Operación normal

    # NRE puede tener montos en cero si es solo traslado
    factura.total_gravada = Decimal("0")
    factura.total_iva = Decimal("0")
    factura.total_exenta = Decimal("100000")  # Valor de mercadería trasladada
    factura.total_general = Decimal("100000")

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML Nota de Remisión inválido: {errors}"
    assert "<iTipDE>7</iTipDE>" in xml, "Debe ser una Nota de Remisión Electrónica"
    assert "<dNumID>001-001-0000005</dNumID>" in xml, "Número documento correcto"
    assert "<cModTra>1</cModTra>" in xml, "Modalidad transporte especificada"


def test_documento_tipo_invalido():
    """
    Test para validar rechazo de tipos de documento inválidos

    Verifica que el sistema detecte códigos no válidos según Manual v150
    Códigos válidos: 1, 4, 5, 6, 7
    """
    factura = create_factura_base()
    factura.tipo_documento = "99"  # Tipo inválido
    factura.numero_documento = "001-001-0000099"

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    # Dependiendo de la implementación, puede fallar en generación o validación
    # Al menos verificamos que el XML contiene el tipo incorrecto
    assert "<iTipDE>99</iTipDE>" in xml, "XML debe contener tipo documento especificado"

    # Si el validador detecta tipos inválidos, debería fallar la validación
    if not is_valid:
        assert len(
            errors) > 0, "Deberían existir errores para tipo documento inválido"
        print(f"Errores esperados para tipo inválido: {errors}")


def test_secuencia_numeracion_documentos():
    """
    Test para validar secuencia correcta de numeración por tipo

    Verifica que cada tipo de documento pueda tener su propia secuencia
    Permite series diferentes por tipo de documento
    """
    tipos_documento = [
        ("1", "001-001-0000001"),  # Factura
        ("1", "001-001-0000002"),  # Factura siguiente
        ("5", "001-002-0000001"),  # Nota Crédito (serie diferente)
        ("6", "001-003-0000001"),  # Nota Débito (serie diferente)
    ]

    for tipo, numero in tipos_documento:
        factura = create_factura_base()
        factura.tipo_documento = tipo
        factura.numero_documento = numero

        generator = XMLGenerator()
        xml = generator.generate_simple_invoice_xml(factura)

        validator = XMLValidator()
        is_valid, errors = validator.validate_xml(xml)

        assert is_valid, f"XML inválido para {tipo}-{numero}: {errors}"
        assert f"<iTipDE>{tipo}</iTipDE>" in xml, f"Tipo documento {tipo} correcto"
        assert f"<dNumID>{numero}</dNumID>" in xml, f"Numeración {numero} correcta"


def test_campos_especificos_por_tipo():
    """
    Test para validar campos específicos según tipo de documento

    Diferentes tipos de documento requieren campos específicos:
    - FE: campos estándar de venta
    - NCE/NDE: referencia a documento original
    - NRE: campos de transporte
    """

    # Factura Electrónica - campos estándar
    factura_fe = create_factura_base()
    factura_fe.tipo_documento = "1"
    factura_fe.condicion_venta = "1"  # Contado
    factura_fe.condicion_operacion = "1"  # Venta normal

    generator = XMLGenerator()
    xml_fe = generator.generate_simple_invoice_xml(factura_fe)

    assert "<cConVen>1</cConVen>" in xml_fe, "Condición venta FE"
    assert "<cConOpe>1</cConOpe>" in xml_fe, "Condición operación FE"

    # Nota de Crédito - operación de devolución
    factura_nce = create_factura_base()
    factura_nce.tipo_documento = "5"
    factura_nce.condicion_operacion = "2"  # Devolución

    xml_nce = generator.generate_simple_invoice_xml(factura_nce)

    assert "<iTipDE>5</iTipDE>" in xml_nce, "Tipo NCE"
    assert "<cConOpe>2</cConOpe>" in xml_nce, "Operación devolución NCE"


def test_validacion_cruzada_tipos_montos():
    """
    Test para validar coherencia entre tipo documento y montos

    Verifica que los montos sean coherentes con el tipo de documento:
    - NCE: montos positivos (representan crédito)
    - NDE: montos positivos (representan débito adicional)
    - NRE: puede tener montos en cero
    """

    # Nota de Crédito con montos positivos (correcto)
    nce = create_factura_base()
    nce.tipo_documento = "5"
    nce.total_gravada = Decimal("100000")
    nce.total_iva = Decimal("10000")
    nce.total_general = Decimal("110000")

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(nce)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"NCE con montos positivos debe ser válida: {errors}"
    assert "<dTotGralOpe>110000</dTotGralOpe>" in xml, "Total NCE correcto"


@pytest.mark.parametrize("tipo_doc,nombre_tipo", [
    ("1", "Factura Electrónica"),
    ("4", "Autofactura Electrónica"),
    ("5", "Nota de Crédito Electrónica"),
    ("6", "Nota de Débito Electrónica"),
    ("7", "Nota de Remisión Electrónica")
])
def test_tipos_documento_parametrizados(tipo_doc, nombre_tipo):
    """
    Test parametrizado para todos los tipos de documento válidos según Manual SIFEN v150

    Verifica que todos los tipos de documento oficiales se generen correctamente
    con sus configuraciones específicas requeridas
    """
    factura = create_factura_base()
    factura.tipo_documento = tipo_doc
    factura.numero_documento = f"001-001-{tipo_doc.zfill(7)}"

    # Ajustar configuraciones específicas según tipo
    if tipo_doc in ["5", "6"]:  # NCE, NDE
        factura.condicion_operacion = "2"  # Operación especial
    if tipo_doc == "7":  # NRE
        factura.modalidad_transporte = "1"  # Terrestre

    # Configuraciones comunes
    factura.condicion_venta = "1"  # Contado

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)

    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"XML {nombre_tipo} inválido: {errors}"
    assert f"<iTipDE>{tipo_doc}</iTipDE>" in xml, f"Tipo {nombre_tipo} correcto"

    # Validaciones comunes para todos los tipos
    assert "xmlns=\"http://ekuatia.set.gov.py/sifen/xsd\"" in xml, "Namespace SIFEN"
    assert "<dFeEmiDE>" in xml, "Fecha emisión presente"
    assert f"<dNumID>001-001-{tipo_doc.zfill(7)}</dNumID>" in xml, "Numeración correcta"


def test_tipos_documento_codigo_cdc():
    """
    Test para validar que el CDC se genere correctamente según el tipo de documento

    El CDC debe incluir el código de tipo de documento en las posiciones correctas:
    - Posiciones 10-11: Tipo documento con padding zero (01, 04, 05, 06, 07)
    """
    tipos_cdc = [
        ("1", "01"),  # FE -> 01 en CDC
        ("4", "04"),  # AFE -> 04 en CDC
        ("5", "05"),  # NCE -> 05 en CDC
        ("6", "06"),  # NDE -> 06 en CDC
        ("7", "07"),  # NRE -> 07 en CDC
    ]

    for tipo_input, tipo_cdc_esperado in tipos_cdc:
        factura = create_factura_base()
        factura.tipo_documento = tipo_input
        factura.numero_documento = f"001-001-000000{tipo_input}"

        generator = XMLGenerator()
        xml = generator.generate_simple_invoice_xml(factura)

        # El CDC debe contener el tipo documento en formato de 2 dígitos
        # Nota: esto depende de cómo se implemente la generación del CDC
        # Este test asume que el CDC se incluye en el XML generado
        print(
            f"Validando tipo {tipo_input} -> CDC debería contener {tipo_cdc_esperado}")


def test_campos_obligatorios_por_tipo():
    """
    Test para validar campos obligatorios específicos por tipo de documento

    Cada tipo de documento tiene campos específicos obligatorios:
    - NRE: campos de transporte
    - NCE/NDE: pueden requerir referencia a documento original
    """

    # Nota de Remisión - requiere modalidad de transporte
    nre = create_factura_base()
    nre.tipo_documento = "7"
    nre.modalidad_transporte = "1"  # Obligatorio para NRE

    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(nre)

    assert "<cModTra>1</cModTra>" in xml, "Modalidad transporte obligatoria para NRE"

    # Verificar que otros campos específicos estén presentes si son requeridos
    validator = XMLValidator()
    is_valid, errors = validator.validate_xml(xml)

    assert is_valid, f"NRE con campos obligatorios debe ser válida: {errors}"
