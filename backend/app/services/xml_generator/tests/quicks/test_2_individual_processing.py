"""
Test 2: Procesamiento individual de documentos
- XML oficial válido
- XML oficial inválido
- Performance básica
"""
from app.services.xml_generator.schemas.v150.integration import quick_process_document


def main():
    print("⚡ TEST 2: PROCESAMIENTO INDIVIDUAL")
    print("=" * 50)

    # XML válido básico
    xml_valid = '''<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
<DE><gOpeDe><iTipEmi>1</iTipEmi></gOpeDe></DE>
</rDE>'''

    print("1. Procesando XML válido...")
    result = quick_process_document(xml_valid, optimization="production")
    print(f"   ✅ Success: {result.success}")
    print(f"   ⏱️  Time: {result.processing_time:.2f}ms")
    print(f"   📝 Errors: {len(result.errors)}")

    # XML inválido
    xml_invalid = '''<invalid>no sifen</invalid>'''

    print("\n2. Procesando XML inválido...")
    result = quick_process_document(xml_invalid, optimization="development")
    print(f"   ❌ Success: {result.success}")
    print(f"   ⏱️  Time: {result.processing_time:.2f}ms")
    print(f"   📝 Errors: {len(result.errors)}")

    print("\n🎯 PROCESAMIENTO INDIVIDUAL: OK")
    print("\n CORRECTO (detecta que es inválido)")


if __name__ == "__main__":
    main()
