# 🚀 v150/integration - Guía de Uso para Desarrollo SaaS

## 🎯 Para qué sirve

El módulo `v150/integration/` es tu **capa de abstracción principal** para trabajar con documentos SIFEN. Te permite desarrollar usando esquemas modulares simples y automáticamente los convierte al formato oficial para envío a SIFEN.

## ⚡ Quick Start

### Importación básica
```python
from schemas.v150.integration import (
    CompatibilityLayer,
    quick_process_document,
    batch_process_documents,
    analyze_document_compatibility
)
```

### Uso más común (procesamiento individual)
```python
# Crear documento con tu lógica de negocio
factura_xml = generar_factura_xml(datos_cliente)

# Procesar para SIFEN (un solo comando)
response = quick_process_document(
    document=factura_xml,
    target_format="official",     # Para envío a SIFEN
    optimization="production"     # Para máxima velocidad
)

if response.success:
    # XML listo para enviar a SIFEN
    sifen_xml = response.result_xml
    enviar_a_sifen(sifen_xml)
else:
    # Manejar errores
    logger.error("Documento inválido", extra={"errors": response.errors})
```

## 📦 Funciones Principales

### 1. `quick_process_document()` - Uso Individual
```python
# Configuraciones disponibles
response = quick_process_document(
    document=xml_content,
    target_format="official",  # "modular" | "official"
    optimization="production"  # "development" | "testing" | "production"
)

# Response contiene:
response.success          # bool: Si fue exitoso
response.result_xml       # str: XML transformado
response.errors          # List[str]: Errores si los hay
response.processing_time # float: Tiempo en ms
```

### 2. `batch_process_documents()` - Procesamiento Masivo
```python
# Lista de XMLs para procesar
facturas = [xml1, xml2, xml3, ...]

# Procesamiento paralelo
batch_response = batch_process_documents(
    documents=facturas,
    parallel=True,
    max_workers=4
)

# Resultados
total = batch_response.total_documents
exitosos = batch_response.successful_documents
throughput = batch_response.batch_performance['throughput_docs_per_second']

# Procesar resultados individuales
for i, result in enumerate(batch_response.results):
    if result.success:
        guardar_xml_procesado(i, result.result_xml)
    else:
        log_error_factura(i, result.errors)
```

### 3. `analyze_document_compatibility()` - Diagnóstico
```python
# Analizar antes de procesar (útil para debugging)
analysis = analyze_document_compatibility(
    document=xml_problematico,
    detailed=True
)

print(f"Score de compatibilidad: {analysis['compatibility_score']:.2f}")
print(f"Tiempo estimado: {analysis['processing_estimates']['size_estimate']:.0f}ms")
print(f"Issues encontrados: {len(analysis.get('issues', []))}")
```

## 🔧 Configuraciones por Entorno

### Development (máximo debugging)
```python
# Para desarrollo local con máximo logging
response = quick_process_document(
    document=xml,
    optimization="development"  # Logging detallado, validación exhaustiva
)
```

### Production (máxima velocidad)
```python
# Para producción con máxima performance
response = quick_process_document(
    document=xml,
    optimization="production"   # Mínimo logging, máxima velocidad
)
```

### Testing (balance)
```python
# Para testing con métricas detalladas
response = quick_process_document(
    document=xml,
    optimization="testing"      # Balance debug/performance
)
```

## 🎛️ API Avanzada (CompatibilityLayer)

### Para casos complejos con configuración personalizada
```python
# Crear layer con configuración específica
layer = CompatibilityLayer(
    config=custom_config,
    enable_events=True,
    enable_caching=True
)

# Procesar con control total
request = IntegrationRequest(
    document=xml_content,
    target_format=DocumentFormat.OFFICIAL,
    optimization_level=OptimizationLevel.PRODUCTION,
    metadata={"origen": "pos", "sucursal": "001"}
)

response = layer.process(request)
```

### Context manager para configuración temporal
```python
# Usar configuración específica temporalmente
with layer.processing_context(OptimizationLevel.DEVELOPMENT) as dev_layer:
    response = dev_layer.process(request)
    # Automáticamente vuelve a configuración original
```

## 📊 Monitoreo y Estadísticas

### Obtener métricas del sistema
```python
layer = CompatibilityLayer()

# Procesar algunos documentos...
# ...

# Obtener estadísticas
stats = layer.get_processing_statistics()

print(f"Total procesados: {stats['total_requests']}")
print(f"Tasa de éxito: {stats['successful_requests']/stats['total_requests']*100:.1f}%")
print(f"Tiempo promedio: {stats['avg_processing_time']:.2f}ms")
print(f"Cache hit rate: {stats['cache_info']['hit_rate']:.1f}%")
```

### Limpiar cache
```python
# Si necesitas limpiar cache del sistema
layer.clear_cache()
```

## 🚨 Casos de Uso SaaS Típicos

### 1. Endpoint de API para crear factura
```python
@app.post("/api/facturas")
async def crear_factura(datos: FacturaRequest):
    try:
        # Generar XML desde datos de negocio
        xml_modular = generar_xml_desde_datos(datos)
        
        # Procesar para SIFEN
        response = quick_process_document(
            document=xml_modular,
            target_format="official",
            optimization="production"
        )
        
        if response.success:
            # Enviar a SIFEN
            resultado_sifen = await enviar_a_sifen(response.result_xml)
            return {"success": True, "cdc": resultado_sifen.cdc}
        else:
            return {"success": False, "errors": response.errors}
            
    except Exception as e:
        logger.error(f"Error creando factura: {e}")
        return {"success": False, "error": str(e)}
```

### 2. Procesamiento de lote nocturno
```python
async def procesar_lote_nocturno():
    # Obtener facturas pendientes de envío
    facturas_pendientes = await db.get_facturas_pendientes()
    
    # Generar XMLs
    xmls = [generar_xml_factura(f) for f in facturas_pendientes]
    
    # Procesar en lote
    batch_response = batch_process_documents(
        documents=xmls,
        parallel=True,
        max_workers=8
    )
    
    # Actualizar base de datos
    for i, result in enumerate(batch_response.results):
        factura_id = facturas_pendientes[i].id
        if result.success:
            await db.marcar_factura_procesada(factura_id, result.result_xml)
        else:
            await db.marcar_factura_error(factura_id, result.errors)
    
    logger.info(f"Lote procesado: {batch_response.successful_documents}/{batch_response.total_documents}")
```

### 3. Validación antes de guardar
```python
@app.post("/api/facturas/validate")
async def validar_factura(datos: FacturaRequest):
    # Generar XML
    xml_draft = generar_xml_desde_datos(datos)
    
    # Analizar compatibilidad
    analysis = analyze_document_compatibility(xml_draft, detailed=True)
    
    return {
        "valid": analysis['compatibility_score'] > 0.8,
        "score": analysis['compatibility_score'],
        "issues": analysis.get('issues', []),
        "estimated_processing_time": analysis['processing_estimates']['size_estimate']
    }
```

## 🐛 Debugging y Troubleshooting

### Análisis detallado de problemas
```python
# Si un documento falla, analizar en detalle
if not response.success:
    # Obtener análisis completo
    analysis = analyze_document_compatibility(
        document=documento_problematico,
        detailed=True
    )
    
    print("Análisis detallado:")
    print(f"- Compatibility score: {analysis['compatibility_score']}")
    print(f"- Issues: {analysis.get('issues', [])}")
    print(f"- Transformation analysis: {analysis.get('transformation_analysis', {})}")
    print(f"- Validation preview: {analysis.get('validation_preview', {})}")
```

### Logging detallado para debugging
```python
import logging

# Habilitar logging detallado del módulo
logging.getLogger('schemas.v150.integration').setLevel(logging.DEBUG)

# Procesar con máximo debug
response = quick_process_document(
    document=xml,
    optimization="development"  # Máximo logging
)

# Revisar debug info
print("Debug info:", response.debug_info)
```

---

## 💡 Tips para Desarrollo SaaS

1. **Usa `production` para APIs en vivo**: Máxima velocidad, mínimo logging
2. **Usa `development` para debugging**: Máximo detalle cuando algo falle
3. **Procesa en lotes** para operaciones nocturnas: Mejor throughput
4. **Analiza compatibilidad** antes de procesar documentos complejos
5. **Monitorea estadísticas** para optimizar performance del sistema

**¡Eso es todo! Con estas funciones tienes todo lo necesario para integrar SIFEN en tu SaaS. 🚀**