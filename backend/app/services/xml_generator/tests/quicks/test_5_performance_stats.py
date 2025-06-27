from app.services.xml_generator.schemas.v150.integration.compatibility_layer import IntegrationRequest
from app.services.xml_generator.schemas.v150.integration import CompatibilityLayer
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


def main():
    print("📊 TEST 5.1: ESTADÍSTICAS REALES ACUMULADAS")
    print("=" * 60)

    # UNA SOLA instancia para acumular estadísticas
    layer = CompatibilityLayer()

    xml_test = '''<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
<DE><gOpeDe><iTipEmi>1</iTipEmi></gOpeDe></DE>
</rDE>'''

    print("Procesando 20 documentos con LA MISMA instancia...")

    # Procesar 20 docs con la MISMA instancia
    for i in range(20):
        request = IntegrationRequest(document=xml_test)
        result = layer.process(request)
        if i % 5 == 0:
            print(f"   Procesado documento {i+1}...")

    print("\n📊 ESTADÍSTICAS ACUMULADAS:")
    stats = layer.get_processing_statistics()

    print(f"   📈 Total requests: {stats['total_requests']}")
    print(f"   ✅ Successful: {stats['successful_requests']}")
    print(f"   ❌ Failed: {stats['failed_requests']}")
    print(f"   ⏱️  Avg time: {stats['avg_processing_time']:.2f}ms")

    # Cache info
    cache_info = stats.get('cache_info', {})
    print(f"   💾 Cache enabled: {cache_info.get('enabled', False)}")
    print(f"   💾 Cache size: {cache_info.get('size', 0)}")
    print(f"   💾 Hit rate: {cache_info.get('hit_rate', 0):.1f}%")

    # Success rate
    if stats['total_requests'] > 0:
        success_rate = stats['successful_requests'] / \
            stats['total_requests'] * 100
        print(f"   🎯 Success rate: {success_rate:.1f}%")

    print("\n🎉 ESTADÍSTICAS REALES FUNCIONANDO!")


if __name__ == "__main__":
    main()
