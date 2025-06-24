# SIFEN Client Service

**Ubicación del archivo**: `backend/app/services/sifen_client/`

## 🏗️ Arquitectura del Sistema

### Estructura de Archivos
```
backend/app/services/sifen_client/
├── __init__.py                    # ✅ API principal (DocumentSender, SifenSOAPClient, Config)
├── config.py                      # ✅ SifenConfig con timeouts y endpoints
├── models.py                      # ✅ DocumentRequest, SifenResponse, BatchRequest (Pydantic)
├── client.py                      # ✅ SifenSOAPClient con TLS 1.2 y zeep
├── document_sender.py             # ✅ Orquestador principal DocumentSender
├── response_parser.py             # ❌ SifenResponseParser para XML responses (FALTA)
├── error_handler.py               # ❌ SifenErrorHandler con códigos SET oficiales (FALTA)
├── retry_manager.py               # ❌ RetryManager con backoff exponencial (FALTA)
├── exceptions.py                  # ✅ Jerarquía completa de excepciones SIFEN
└── tests/                         # ✅ Suite de testing comprehensiva
    ├── __init__.py
    ├── conftest.py                # ✅ Configuración pytest con auto-setup
    ├── run_sifen_tests.py         # ✅ Runner personalizado con opciones
    ├── test_client.py             # ✅ Tests cliente SOAP básico (100%)
    ├── test_document_sender.py    # ✅ Tests orquestador principal (100%)
    ├── test_document_status.py    # ✅ Tests estados documento (100%)
    ├── test_mock_soap_client.py   # ✅ Tests mock SOAP (100%)
    ├── test_sifen_error_codes.py  # ✅ Tests códigos error v150 (100%)
    ├── test_time_limits_validation.py # ✅ Tests límites 72h/720h (100%)
    ├── test_certificate_validation.py # ✅ Tests certificados PSC (100%)
    ├── test_document_size_limits.py   # ✅ Tests tamaños máximos (100%)
    ├── test_concurrency_rate_limits.py # ✅ Tests rate limiting (100%)
    ├── test_currency_amount_validation.py # ✅ Tests monedas/montos (100%)
    ├── test_contingency_mode.py   # ✅ Tests modo contingencia (100%)
    ├── test_response_parser.py    # ❌ Tests parser respuestas (FALTA)
    ├── test_error_handler.py      # ❌ Tests mapeo errores (FALTA)
    ├── test_retry_manager.py      # ❌ Tests lógica reintentos (FALTA)
    ├── fixtures/                  # ✅ Datos de prueba y configuración
    │   ├── test_documents.py      # ✅ XMLs válidos para testing
    │   ├── test_config.py         # ✅ Configuración automática tests
    │   ├── sifen_responses.xml    # ❌ Respuestas reales SIFEN (FALTA)
    │   └── error_responses.xml    # ❌ Errores típicos SIFEN (FALTA)
    └── mocks/                     # ✅ Mocks para testing offline
        └── mock_soap_client.py    # ✅ Mock cliente SOAP realista
```

### Flujo de Envío de Documentos
```
1. XML Firmado Input
   ↓
2. DocumentSender.send_signed_document()
   ↓
3. Pre-validación (tamaño, estructura, certificado)
   ↓
4. SifenSOAPClient.send_document() [TLS 1.2]
   ↓
5. RetryManager → Reintentos automáticos si falla
   ↓
6. SifenResponseParser.parse_response()
   ↓
7. SifenErrorHandler.get_user_friendly_message()
   ↓
8. SifenResponse con resultado final
```

### Componentes Internos
- **client.py**: Comunicación SOAP de bajo nivel con TLS 1.2 obligatorio
- **document_sender.py**: Orquestador que combina todos los componentes
- **response_parser.py**: Extrae CDC, códigos error, mensajes de respuestas XML
- **error_handler.py**: Mapea códigos SIFEN a mensajes user-friendly
- **retry_manager.py**: Sistema inteligente de reintentos con circuit breaker
- **config.py**: Configuración endpoints, timeouts, certificados, reintentos
- **models.py**: Validación Pydantic para requests/responses
- **exceptions.py**: Jerarquía específica de errores SIFEN

### Estándares y Protocolos
- **SOAP**: Web Services según Manual Técnico SIFEN v150
- **TLS 1.2+**: Obligatorio para comunicación con SET Paraguay
- **XML**: Parsing de respuestas con lxml y validación XSD
- **UTF-8**: Encoding para caracteres especiales y guaraní
- **Timeouts**: Conexión (30s), lectura (60s), operación total (120s)

## 📊 Estado de Implementación

### ✅ IMPLEMENTADO Y FUNCIONAL
- **Config** (`config.py`): Configuración completa con validación - **100%**
- **Models** (`models.py`): Modelos Pydantic para todos los casos - **100%**
- **SOAP Client** (`client.py`): Cliente con TLS 1.2 y pooling - **100%**
- **Document Sender** (`document_sender.py`): Orquestador principal - **85%** ⚠️
- **Exceptions** (`exceptions.py`): Jerarquía completa de errores - **100%**

### ✅ TESTING COMPLETADO
- **test_client.py**: Tests cliente SOAP básico - **100%**
- **test_document_sender.py**: Tests orquestador (limitados por dependencias faltantes) - **70%**
- **test_sifen_error_codes.py**: Tests códigos error v150 - **100%**
- **test_time_limits_validation.py**: Tests límites temporales - **100%**
- **test_certificate_validation.py**: Tests certificados PSC - **100%**
- **test_document_size_limits.py**: Tests límites tamaño - **100%**
- **test_concurrency_rate_limits.py**: Tests rate limiting - **100%**
- **test_currency_amount_validation.py**: Tests monedas/montos - **100%**
- **test_contingency_mode.py**: Tests modo contingencia - **100%**

### ❌ PENDIENTE (Archivos Críticos Faltantes)
- **Response Parser** (`response_parser.py`): Parser XML respuestas SIFEN - **0%**
- **Error Handler** (`error_handler.py`): Mapeo códigos error a mensajes - **0%**
- **Retry Manager** (`retry_manager.py`): Sistema reintentos con backoff - **0%**
- **Tests de componentes faltantes**: test_response_parser.py, test_error_handler.py, test_retry_manager.py - **0%**
- **Fixtures XML**: sifen_responses.xml, error_responses.xml - **0%**

## 🚀 Próximos Pasos

### Fase 1: Completar Componentes Core (Crítico - 3 días)
```python
# Implementar archivos faltantes críticos:
# 1. response_parser.py - Parser respuestas XML SIFEN
class SifenResponseParser:
    def parse_response(self, xml_response: str) -> SifenResponse
    def extract_cdc(self, xml_response: str) -> Optional[str]
    def extract_errors(self, xml_response: str) -> List[str]

# 2. error_handler.py - Mapeo códigos error oficiales SET
class SifenErrorHandler:
    ERROR_CODES = {"0260": "Aprobado", "1000": "CDC inválido", ...}
    def get_user_friendly_message(self, error_code: str) -> str

# 3. retry_manager.py - Sistema reintentos con backoff exponencial
class RetryManager:
    async def execute_with_retry(self, operation: Callable) -> Any
```

### Fase 2: Completar Testing (Necesario - 2 días)
- Tests para response_parser.py, error_handler.py, retry_manager.py
- Fixtures XML con respuestas reales de SIFEN
- Integración completa con DocumentSender

### Fase 3: Funcionalidad Adicional (Opcional - 1 semana)
- Tipos de documento específicos (AFE, NCE, NDE, NRE)
- Workflow avanzado de lotes asíncronos
- Encoding especial para caracteres guaraní

## 🔧 Configuración Básica

### Variables de Entorno
```bash
# Ambiente SIFEN
SIFEN_ENVIRONMENT=test  # test | production
SIFEN_BASE_URL=https://sifen-test.set.gov.py/

# Timeouts y reintentos
SIFEN_TIMEOUT=30
SIFEN_MAX_RETRIES=3
SIFEN_BACKOFF_FACTOR=1.0

# TLS y certificados
SIFEN_VERIFY_SSL=true
SIFEN_TLS_VERSION=1.2

# Logging
SIFEN_LOG_LEVEL=INFO
SIFEN_LOG_REQUESTS=true
```

### Uso Directo
```python
from backend.app.services.sifen_client import DocumentSender, SifenConfig

# Configuración automática desde variables de entorno
config = SifenConfig.from_env()

# Envío de documento individual
async with DocumentSender(config) as sender:
    result = await sender.send_signed_document(
        xml_content=signed_xml,
        certificate_serial="1234567890"
    )
    
    if result.success:
        print(f"Documento enviado: CDC {result.response.cdc}")
    else:
        print(f"Error: {result.response.message}")
```

### Envío de Lote
```python
# Envío de múltiples documentos
async with DocumentSender(config) as sender:
    batch_result = await sender.send_document_batch([
        DocumentRequest(xml_content=xml1, certificate_serial=cert1),
        DocumentRequest(xml_content=xml2, certificate_serial=cert2),
        # ... hasta 50 documentos
    ])
    
    print(f"Enviados: {batch_result.successful_documents}")
    print(f"Fallidos: {batch_result.failed_documents}")
```

## 🧪 Testing y Desarrollo

### Ejecutar Tests Completos
```bash
# Tests específicos módulo
pytest backend/app/services/sifen_client/tests/ -v

# Tests con cobertura
pytest backend/app/services/sifen_client/tests/ -v --cov=backend.app.services.sifen_client

# Tests críticos solamente (códigos error, límites, certificados)
pytest -k "error_codes or time_limits or certificate_validation" -v

# Runner integrado con opciones
cd backend/app/services/sifen_client/tests/
python run_sifen_tests.py --all --coverage
```

### Tests por Categoría
```bash
# Tests unitarios rápidos (sin conexión SIFEN)
pytest backend/app/services/sifen_client/tests/ -v -m "not integration"

# Tests de integración (requieren conectividad)
pytest backend/app/services/sifen_client/tests/ -v -m integration

# Tests de performance
pytest backend/app/services/sifen_client/tests/ -v -m slow

# Tests específicos de funcionalidad
pytest backend/app/services/sifen_client/tests/test_document_sender.py -v
pytest backend/app/services/sifen_client/tests/test_sifen_error_codes.py -v
```

### Validación de Conectividad
```python
# Test rápido de conectividad
from backend.app.services.sifen_client.client import test_connection

async def validate_sifen():
    is_connected = await test_connection()
    print(f"SIFEN conectado: {is_connected}")

# asyncio.run(validate_sifen())
```

## 🔒 Estándares y Seguridad

### Comunicación Segura
- **TLS 1.2+**: Obligatorio según SET Paraguay
- **Validación certificados**: Verificación cadena de confianza
- **Timeouts robustos**: Prevención de conexiones colgadas
- **Rate limiting**: Respeto a límites de SIFEN (5 req/segundo)

### Logging Seguro
- **Sin datos sensibles**: RUC/certificados enmascarados en logs
- **Structured logging**: JSON para análisis posterior  
- **Niveles configurables**: DEBUG, INFO, WARNING, ERROR
- **Rotación automática**: Prevención de logs gigantes

### Códigos de Error SIFEN v150
```python
# Códigos críticos implementados:
"0260": "Documento aprobado",           # ✅ Éxito
"1000": "CDC no corresponde con XML",   # ❌ Error crítico
"1001": "CDC duplicado",                # ❌ Error de negocio
"1101": "Número timbrado inválido",     # ❌ Error de configuración
"1250": "RUC emisor inexistente",       # ❌ Error de certificado
"0141": "Firma digital inválida",       # ❌ Error de firma
# ... 50+ códigos más según manual v150
```

## ⚠️ Consideraciones Críticas

### Bloqueos de Producción
1. **Componentes faltantes**: response_parser, error_handler, retry_manager bloquean funcionalidad core
2. **DocumentSender incompleto**: Depende de componentes faltantes para funcionar
3. **Testing limitado**: Sin tests de componentes críticos
4. **Conectividad TLS**: Debe ser TLS 1.2+ o SET rechaza
5. **Certificados PSC**: Solo certificados SET Paraguay válidos

### Recomendaciones Inmediatas
- **CRÍTICO**: Implementar response_parser.py, error_handler.py, retry_manager.py antes de cualquier deploy
- Completar tests de componentes faltantes
- Validar integración completa DocumentSender con componentes
- Testing exhaustivo contra ambiente test de SET
- Configurar timeouts apropiados (30-60 segundos)

### Rendimiento Esperado
- **Latencia promedio**: <5 segundos por documento
- **Throughput**: 100+ documentos/hora por instancia
- **Disponibilidad**: >99% (depende de SIFEN)
- **Rate limit**: Máximo 5 requests/segundo

---
**Estado**: 65% funcional - Faltan componentes críticos para producción  
**Última actualización**: Junio 2025  
**Mantenedor**: Equipo Backend SIFEN

**⚠️ IMPORTANTE**: Este módulo requiere completar 3 archivos críticos (response_parser.py, error_handler.py, retry_manager.py) antes de poder usarse en producción. El DocumentSender actualmente depende de estos componentes faltantes.