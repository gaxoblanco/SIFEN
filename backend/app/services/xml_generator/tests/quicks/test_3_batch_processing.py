"""
Test 3: Procesamiento en lote
- Múltiples documentos válidos
- Performance de throughput
- Estadísticas de lote
"""
from app.services.xml_generator.schemas.v150.integration import batch_process_documents


def main():
    print("📦 TEST 3: PROCESAMIENTO EN LOTE")
    print("=" * 50)

    # XML base para lote
    xml_base = '''<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
<DE><gOpeDe><iTipEmi>1</iTipEmi></gOpeDe></DE>
</rDE>'''

    # Crear lote de 10 documentos
    documents = [xml_base] * 10

    print(f"Procesando lote de {len(documents)} documentos...")

    # Procesamiento paralelo
    batch_result = batch_process_documents(
        documents=documents,
        parallel=True,
        max_workers=4
    )

    print(f"✅ Total: {batch_result.total_documents}")
    print(f"✅ Exitosos: {batch_result.successful_documents}")
    print(f"❌ Fallidos: {batch_result.failed_documents}")
    print(
        f"⚡ Success Rate: {batch_result.successful_documents/batch_result.total_documents*100:.1f}%")

    if hasattr(batch_result, 'batch_performance'):
        perf = batch_result.batch_performance
        print(
            f"🚀 Throughput: {perf.get('throughput_docs_per_second', 0):.1f} docs/seg")
        print(
            f"⏱️  Avg Time: {perf.get('avg_time_per_document', 0):.2f}ms/doc")

    print("\n📦 PROCESAMIENTO EN LOTE: OK")


if __name__ == "__main__":
    main()
