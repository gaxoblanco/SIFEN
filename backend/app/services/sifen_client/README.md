# 🎯 Plan de Implementación: sifen_client/

## 📋 Objetivos del Módulo

### Propósito Principal
Crear un cliente robusto para interactuar con los Web Services SOAP de SIFEN Paraguay, manejando el envío de documentos electrónicos firmados y procesando las respuestas del sistema.

### Funcionalidades Críticas
1. **Envío de documentos individuales** a SIFEN (sync)
2. **Envío de lotes** de documentos (async, hasta 50 docs)
3. **Consulta de estados** de documentos por CDC
4. **Manejo robusto de errores** SIFEN con retry automático
5. **Parsing de respuestas** XML de SIFEN
6. **Logging estructurado** de todas las interacciones

---

## 🏗️ Arquitectura del Módulo

### Estructura de Archivos Planificada
```
backend/app/services/sifen_client/
├── __init__.py
├── README.md                    # ← Documentación completa
├── config.py                    # ← Configuración endpoints/timeouts
├── models.py                    # ← Request/Response models
├── client.py                    # ← Cliente SOAP principal  
├── document_sender.py           # ← Lógica envío documentos
├── response_parser.py           # ← Parser respuestas SIFEN
├── error_handler.py             # ← Mapeo códigos error
├── retry_manager.py             # ← Sistema reintentos
├── exceptions.py                # ← Excepciones personalizadas
├── tests/                       # ← Tests exhaustivos
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_document_sender.py
│   ├── test_response_parser.py
│   ├── test_error_handler.py
│   ├── test_retry_manager.py
│   ├── fixtures/
│   │   ├── sifen_responses.xml   # ← Respuestas reales SIFEN
│   │   ├── error_responses.xml   # ← Errores típicos
│   │   └── test_documents.xml    # ← Documentos de prueba
│   └── mocks/
│       └── mock_soap_client.py   # ← Mock cliente SOAP
└── schemas/                     # ← Esquemas request/response
    ├── siRecepDE_v150.xsd
    ├── resRecepDE_v150.xsd
    └── error_schemas.xsd
```

---

## 🔧 Componentes Detallados

### 1. **config.py** - Configuración Central
```python
"""
Configuración específica para cliente SIFEN
Manejo de endpoints, timeouts, certificados
"""

@dataclass
class SifenConfig:
    # Endpoints
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    
    # TLS/SSL
    verify_ssl: bool = True
    cert_path: Optional[str] = None
    
    # Retry configuration
    backoff_factor: float = 1.0
    retry_status_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
```

### 2. **models.py** - Modelos Pydantic
```python
"""
Modelos para requests/responses SIFEN
Validación automática de datos
"""

class DocumentRequest(BaseModel):
    """Request para envío de documento individual"""
    xml_content: str
    certificate_serial: str
    timestamp: datetime

class SifenResponse(BaseModel):
    """Respuesta estándar de SIFEN"""
    success: bool
    code: str
    message: str
    cdc: Optional[str] = None
    protocol_number: Optional[str] = None
    errors: List[str] = []

class BatchRequest(BaseModel):
    """Request para envío de lote"""
    documents: List[DocumentRequest]
    batch_id: str
```

### 3. **client.py** - Cliente SOAP Principal
```python
"""
Cliente SOAP principal para SIFEN
Maneja la comunicación de bajo nivel
"""

class SifenSOAPClient:
    def __init__(self, config: SifenConfig):
        """Inicializa cliente con configuración TLS 1.2"""
        
    async def send_document(self, request: DocumentRequest) -> SifenResponse:
        """Envía documento individual a SIFEN"""
        
    async def send_batch(self, batch: BatchRequest) -> SifenResponse:
        """Envía lote de documentos"""
        
    async def query_document(self, cdc: str) -> SifenResponse:
        """Consulta estado de documento por CDC"""
```

### 4. **document_sender.py** - Orquestador Alto Nivel
```python
"""
Orquestador de envío de documentos
Combina validación, envío y manejo de errores
"""

class DocumentSender:
    def __init__(self, soap_client: SifenSOAPClient, 
                 retry_manager: RetryManager,
                 error_handler: ErrorHandler):
        """Inicializa con dependencias inyectadas"""
    
    async def send_signed_document(self, 
                                   xml_content: str, 
                                   certificate_serial: str) -> SifenResponse:
        """
        Flujo completo: Validar → Enviar → Retry si falla → Parse respuesta
        """
```

### 5. **response_parser.py** - Parser Respuestas
```python
"""
Parser especializado para respuestas XML de SIFEN
Extrae información estructurada
"""

class SifenResponseParser:
    def parse_response(self, xml_response: str) -> SifenResponse:
        """Parsea respuesta XML a modelo Pydantic"""
        
    def extract_cdc(self, xml_response: str) -> Optional[str]:
        """Extrae CDC de respuesta exitosa"""
        
    def extract_errors(self, xml_response: str) -> List[str]:
        """Extrae errores de respuesta fallida"""
```

### 6. **error_handler.py** - Mapeo de Errores
```python
"""
Mapeo de códigos de error SIFEN a mensajes user-friendly
Según Manual Técnico v150
"""

class SifenErrorHandler:
    # Mapeo de códigos según documentación
    ERROR_CODES = {
        "0260": "Documento aprobado",
        "1000": "CDC no corresponde con XML",
        "1001": "CDC duplicado", 
        "1101": "Número timbrado inválido",
        "1250": "RUC emisor inexistente",
        "0141": "Firma digital inválida",
        # ... más códigos del manual
    }
    
    def get_user_friendly_message(self, error_code: str) -> str:
        """Convierte código SIFEN a mensaje comprensible"""
```

### 7. **retry_manager.py** - Sistema de Reintentos
```python
"""
Sistema de reintentos con backoff exponencial
Maneja fallos temporales de red/SIFEN
"""

class RetryManager:
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
        """Configuración de reintentos"""
    
    async def execute_with_retry(self, 
                                operation: Callable,
                                *args, **kwargs) -> Any:
        """
        Ejecuta operación con reintentos automáticos
        Backoff: 1s, 2s, 4s, 8s...
        """
```

### 8. **exceptions.py** - Excepciones Personalizadas
```python
"""
Excepciones específicas del módulo SIFEN
Jerarquía clara de errores
"""

class SifenClientError(Exception):
    """Error base del cliente SIFEN"""

class SifenConnectionError(SifenClientError):
    """Error de conexión con SIFEN"""

class SifenValidationError(SifenClientError):
    """Error de validación de datos"""

class SifenServerError(SifenClientError):
    """Error del servidor SIFEN"""
```

---

## 🧪 Estrategia de Testing

### Tipos de Tests Planificados

#### 1. **Tests Unitarios** (>80% cobertura)
- ✅ `test_client.py` - Cliente SOAP básico
- ✅ `test_response_parser.py` - Parsing respuestas
- ✅ `test_error_handler.py` - Mapeo errores
- ✅ `test_retry_manager.py` - Lógica reintentos
- ✅ `test_models.py` - Validación Pydantic

#### 2. **Tests de Integración**
- ✅ `test_document_sender.py` - Flujo completo
- ✅ `test_sifen_integration.py` - Contra SIFEN test
- ✅ `test_error_scenarios.py` - Escenarios de error

#### 3. **Mocks y Fixtures**
```python
# fixtures/sifen_responses.xml
"""Respuestas reales de SIFEN test para testing"""

# mocks/mock_soap_client.py  
"""Mock del cliente SOAP para tests unitarios"""

class MockSifenSOAPClient:
    def __init__(self, mock_responses: Dict[str, str]):
        """Configura respuestas mockeadas"""
    
    async def send_document(self, request: DocumentRequest) -> str:
        """Retorna respuesta mockeada según request"""
```

#### 4. **Tests de Casos Límite**
- 🔄 Timeouts y reconexión
- 🔄 Documentos muy grandes  
- 🔄 Lotes con 50 documentos
- 🔄 Errores de certificado
- 🔄 Respuestas malformadas

---

## 🔐 Consideraciones de Seguridad

### TLS y Certificados
```python
"""
Configuración TLS 1.2 obligatorio según SIFEN
Validación de certificados SSL
"""

# En client.py
ssl_context = ssl.create_default_context()
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
```

### Logging Seguro
```python
"""
Logging sin datos sensibles
Enmascarar información confidencial
"""

def safe_log_request(xml_content: str) -> str:
    """
    Loggea request ocultando datos sensibles:
    - RUC parcial: 1234567* 
    - Certificados: [HIDDEN]
    - Firmas: [SIGNATURE_REDACTED]
    """
```

---

## 📊 Métricas y Monitoreo

### KPIs del Módulo
- ⏱️ **Tiempo de respuesta**: < 10 segundos (95percentil)
- 🎯 **Tasa de éxito**: > 99% (excluyendo errores de datos)
- 🔄 **Reintentos efectivos**: < 5% de requests
- 📈 **Throughput**: 100+ documentos/hora por instancia

### Logging Estructurado
```python
"""
Logging JSON para análisis posterior
Incluye métricas de performance
"""

logger.info("sifen_request_sent", extra={
    "cdc": cdc,
    "operation": "send_document",
    "response_time_ms": 1250,
    "retry_count": 0,
    "success": True,
    "sifen_code": "0260"
})
```

---

## 🚀 Plan de Implementación por Pasos

### **Paso 1: Setup Base** (2 horas)
1. ✅ Crear estructura de archivos
2. ✅ Configurar `__init__.py` y `config.py`
3. ✅ Definir modelos Pydantic básicos
4. ✅ Setup tests con fixtures iniciales

### **Paso 2: Cliente SOAP** (4 horas)
1. ✅ Implementar `client.py` con TLS 1.2
2. ✅ Método `send_document()` básico
3. ✅ Tests unitarios del cliente
4. ✅ Mock para testing offline

### **Paso 3: Parser y Errores** (3 horas)  
1. ✅ Implementar `response_parser.py`
2. ✅ Implementar `error_handler.py` con códigos del manual
3. ✅ Tests con respuestas reales de SIFEN
4. ✅ Validación contra esquemas XSD

### **Paso 4: Sistema de Reintentos** (2 horas)
1. ✅ Implementar `retry_manager.py`
2. ✅ Integrar con cliente SOAP
3. ✅ Tests de fallos simulados
4. ✅ Configuración de timeouts

### **Paso 5: Orquestador Alto Nivel** (3 horas)
1. ✅ Implementar `document_sender.py`
2. ✅ Integración con módulos anteriores
3. ✅ Tests de flujo completo E2E
4. ✅ Documentación README.md

### **Paso 6: Integración Real** (2 horas)
1. ✅ Tests contra SIFEN test environment
2. ✅ Validación con documentos reales
3. ✅ Ajustes basados en respuestas reales
4. ✅ Documentación de troubleshooting

---

## 🎯 Criterios de Completitud

### Según .cursorrules
- [ ] **Tests unitarios**: >80% cobertura
- [ ] **Tests integración**: Contra SIFEN test
- [ ] **Documentación**: README.md completo
- [ ] **Ejemplos uso**: Código funcional
- [ ] **Error handling**: Mapeo completo códigos SIFEN
- [ ] **Logging**: Estructurado y seguro
- [ ] **Sin dependencias circulares**: Validado

### Funcionalidades Mínimas
- [ ] ✅ Enviar documento individual exitosamente
- [ ] ✅ Manejar errores comunes de SIFEN
- [ ] ✅ Sistema de reintentos funcionando
- [ ] ✅ Parsing de respuestas XML
- [ ] ✅ Logging de requests/responses
- [ ] ✅ Configuración TLS 1.2

### Checkpoint Crítico
**🎯 META**: Enviar factura completa: XML Generator → Digital Sign → SIFEN Client → Respuesta OK

---

## ⚠️ Riesgos y Mitigaciones

### Riesgos Identificados
1. **🔴 Alta Fricción**: Integración SOAP compleja
   - **Mitigación**: Implementar mocks desde el inicio
   - **Plan B**: Usar cliente HTTP directo si SOAP falla

2. **🟡 Certificados TLS**: Problemas con SIFEN test
   - **Mitigación**: Configuración SSL flexible
   - **Plan B**: Ambiente local con mocks

3. **🟡 Timeouts Variables**: SIFEN puede ser lento
   - **Mitigación**: Timeouts configurables
   - **Plan B**: Queue asíncrona para documentos

4. **🟡 Códigos de Error**: Mapeo incompleto
   - **Mitigación**: Logging exhaustivo para nuevos códigos
   - **Plan B**: Error genérico + logging para análisis

---

## 📚 Referencias Técnicas

### Documentación Base
- 📖 Manual Técnico SIFEN v150 (códigos error, endpoints)
- 📖 Esquemas XSD v150 (requests/responses)
- 📖 W3C SOAP 1.2 Specification
- 📖 TLS 1.2 Requirements

### Librerías Python Sugeridas
```python
# requirements.txt additions
zeep>=4.2.1          # Cliente SOAP robusto
aiohttp>=3.8.0       # HTTP async client
lxml>=4.9.0          # XML processing
pydantic>=2.0.0      # Data validation
structlog>=23.1.0    # Structured logging
```

---

**¿Estás de acuerdo con este plan?** Una vez confirmado, procederemos a implementar paso a paso siguiendo esta estructura.