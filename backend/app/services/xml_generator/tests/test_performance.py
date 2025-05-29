"""
Tests de rendimiento para el generador XML
"""
import time
from decimal import Decimal
from datetime import datetime
from .fixtures.test_data import create_factura_base
from ..generator import XMLGenerator
from ..validators import XMLValidator


def test_tiempo_generacion_xml():
    """Test para medir el tiempo de generación de XML"""
    factura = create_factura_base()
    generator = XMLGenerator()

    start_time = time.time()
    xml = generator.generate_simple_invoice_xml(factura)
    end_time = time.time()

    tiempo_generacion = end_time - start_time
    assert tiempo_generacion < 0.1, f"Tiempo de generación excesivo: {tiempo_generacion} segundos"


def test_tiempo_validacion_xml():
    """Test para medir el tiempo de validación de XML"""
    factura = create_factura_base()
    generator = XMLGenerator()
    xml = generator.generate_simple_invoice_xml(factura)
    validator = XMLValidator()

    start_time = time.time()
    is_valid, errors = validator.validate_xml(xml)
    end_time = time.time()

    tiempo_validacion = end_time - start_time
    assert tiempo_validacion < 0.2, f"Tiempo de validación excesivo: {tiempo_validacion} segundos"
    assert is_valid, f"XML inválido: {errors}"


def test_rendimiento_multiple_items():
    """Test para medir el rendimiento con múltiples items"""
    from ..models import ItemFactura

    # Crear 100 items
    items = []
    for i in range(100):
        items.append(
            ItemFactura(
                codigo=f"ITEM{i:03d}",
                descripcion=f"Producto {i}",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("1000"),
                iva=Decimal("10"),
                monto_total=Decimal("1100")
            )
        )

    factura = create_factura_base(
        items=items,
        total_iva=Decimal("10000"),
        total_gravada=Decimal("100000"),
        total_general=Decimal("110000")
    )

    generator = XMLGenerator()
    validator = XMLValidator()

    # Medir tiempo de generación
    start_time = time.time()
    xml = generator.generate_simple_invoice_xml(factura)
    tiempo_generacion = time.time() - start_time

    # Medir tiempo de validación
    start_time = time.time()
    is_valid, errors = validator.validate_xml(xml)
    tiempo_validacion = time.time() - start_time

    assert tiempo_generacion < 1.0, f"Tiempo de generación excesivo: {tiempo_generacion} segundos"
    assert tiempo_validacion < 2.0, f"Tiempo de validación excesivo: {tiempo_validacion} segundos"
    assert is_valid, f"XML inválido: {errors}"
    assert xml.count("<gItem>") == 100, "Debe tener 100 items"


def test_rendimiento_concurrente():
    """Test para medir el rendimiento con generación concurrente"""
    import concurrent.futures

    def generar_y_validar():
        factura = create_factura_base()
        generator = XMLGenerator()
        validator = XMLValidator()

        xml = generator.generate_simple_invoice_xml(factura)
        is_valid, errors = validator.validate_xml(xml)

        return is_valid, errors

    # Generar 10 documentos concurrentemente
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generar_y_validar) for _ in range(10)]
        results = [f.result() for f in futures]
    end_time = time.time()

    tiempo_total = end_time - start_time
    assert tiempo_total < 2.0, f"Tiempo total excesivo: {tiempo_total} segundos"

    # Verificar que todos los documentos son válidos
    for is_valid, errors in results:
        assert is_valid, f"XML inválido: {errors}"
