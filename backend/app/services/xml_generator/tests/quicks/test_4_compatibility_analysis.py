"""
Test 4: Análisis detallado de compatibilidad
- Análisis de documentos válidos/inválidos
- Scores de compatibilidad
- Recomendaciones del sistema
"""
from app.services.xml_generator.schemas.v150.integration import analyze_document_compatibility


def main():
    print("🔍 TEST 4: ANÁLISIS DE COMPATIBILIDAD")
    print("=" * 50)

    # Documento SIFEN válido
    xml_sifen = '''<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
<DE><gOpeDe><iTipEmi>1</iTipEmi></gOpeDe></DE>
</rDE>'''

    print("1. Analizando documento SIFEN...")
    analysis = analyze_document_compatibility(xml_sifen, detailed=True)
    print(f"   📊 Format: {analysis.get('document_format', 'unknown')}")
    print(f"   📊 Type: {analysis.get('document_type', 'unknown')}")
    print(
        f"   ⭐ Compatibility Score: {analysis.get('integration_analysis', {}).get('compatibility_score', 'N/A')}")

    # Documento no-SIFEN
    xml_custom = '''<invoice><type>factura</type></invoice>'''

    print("\n2. Analizando documento no-SIFEN...")
    analysis = analyze_document_compatibility(xml_custom, detailed=True)
    print(f"   📊 Format: {analysis.get('document_format', 'unknown')}")
    print(
        f"   ⭐ Compatibility Score: {analysis.get('integration_analysis', {}).get('compatibility_score', 'N/A')}")

    # Obtener recomendaciones
    recommendations = analysis.get('recommendations', [])
    if recommendations:
        print(f"   💡 Recomendaciones: {len(recommendations)}")
        for i, rec in enumerate(recommendations[:2], 1):
            print(f"      {i}. {rec}")

    print("\n🔍 ANÁLISIS DE COMPATIBILIDAD: OK")


if __name__ == "__main__":
    main()
