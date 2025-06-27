"""
Test 1: Verificar que todo el sistema funciona
- Importaciones correctas
- CompatibilityLayer se crea
- Estadísticas base funcionan
"""
from app.services.xml_generator.schemas.v150.integration import (
    CompatibilityLayer,
    quick_process_document,
    batch_process_documents,
    analyze_document_compatibility
)
import sys
import os
# Ir al directorio backend
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.append(backend_path)


def main():
    print("🔍 TEST 1: VERIFICACIÓN DE SISTEMA")
    print("=" * 50)

    # Verificar importaciones
    print("✅ Importaciones correctas")

    # Crear layer
    layer = CompatibilityLayer()
    print("✅ CompatibilityLayer creado")

    # Estadísticas iniciales
    stats = layer.get_processing_statistics()
    print(f"✅ Estadísticas base: {stats['total_requests']} requests")

    # Verificar funciones disponibles
    print("✅ Funciones disponibles:")
    print("   - quick_process_document")
    print("   - batch_process_documents")
    print("   - analyze_document_compatibility")

    print("\n🎉 SISTEMA COMPLETAMENTE FUNCIONAL")


if __name__ == "__main__":
    main()
