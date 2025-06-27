from app.services.xml_generator.schemas.v150.integration import analyze_document_compatibility
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


# Documento no-SIFEN para ver todas las recomendaciones
xml_custom = '''<invoice><type>factura</type></invoice>'''

print("🔍 ANÁLISIS COMPLETO DE RECOMENDACIONES")
print("=" * 50)

analysis = analyze_document_compatibility(xml_custom, detailed=True)

# Ver TODAS las recomendaciones
recommendations = analysis.get('recommendations', [])
print(f"📋 Total recomendaciones: {len(recommendations)}")
for i, rec in enumerate(recommendations, 1):
    print(f"{i:2d}. {rec}")

# Ver errores específicos si los hay
modular_analysis = analysis.get('modular_analysis', {})
errors = modular_analysis.get('errors', [])
if errors:
    print(f"\n❌ Errores específicos ({len(errors)}):")
    for i, error in enumerate(errors[:5], 1):  # Primeros 5
        print(f"{i:2d}. {error}")
    if len(errors) > 5:
        print(f"    ... y {len(errors)-5} más")
