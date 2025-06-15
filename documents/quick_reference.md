# Referencia Rápida - SIFEN

## 🚀 Quick Start

### Comandos Esenciales
```bash
# Inicio rápido diario
make dev                  # Backend + Frontend + DB
make docker-up           # Solo servicios Docker
make test               # Ejecutar todos los tests
make lint               # Linter y formato código

# Setup inicial (una sola vez)
make setup-dev          # Configuración completa automática
```

### URLs de Desarrollo
- **Backend API**: `http://localhost:8000`
- **Frontend**: `http://localhost:3000`
- **API Docs**: `http://localhost:8000/docs`
- **Redoc**: `http://localhost:8000/redoc`

---

## 📚 Manual Técnico SIFEN v150

### Tipos de Documento
| Código | Tipo | Descripción |
|--------|------|-------------|
| `1` | FE | Factura Electrónica |
| `4` | AFE | Autofactura Electrónica |
| `5` | NCE | Nota de Crédito Electrónica |
| `6` | NDE | Nota de Débito Electrónica |
| `7` | NRE | Nota de Remisión Electrónica |

### Estados de Respuesta SIFEN
| Código | Estado | Descripción |
|--------|--------|-------------|
| `0260` | A | Aprobado |
| `1005` | AO | Aprobado con Observaciones |
| `1000-4999` | R | Rechazado |

### Códigos de Error Frecuentes
```bash
1000    # CDC no corresponde con XML
1001    # CDC duplicado  
1101    # Número timbrado inválido
1250    # RUC emisor inexistente
0141    # Firma digital inválida
0142    # Certificado inválido
```

### Estructura CDC (44 dígitos)
```
012345678012345678901234567890123456789012
│└─ Tipo emisión (1)
│  └─ Fecha emisión (8)
│     └─ Número documento (7)
│        └─ Punto expedición (3)
│           └─ Establecimiento (3)
│              └─ Tipo documento (2)
│                 └─ DV emisor (1)
│                    └─ RUC emisor (8)
│                       └─ Código seguridad (9)
│                          └─ DV (1)
```

---

## 🏗️ Arquitectura del Proyecto

### Estructura de Servicios Backend
```
backend/app/services/
├── xml_generator/    # 🔥 Generación XML SIFEN
├── digital_sign/     # 🔐 Firma digital certificados
├── sifen_client/     # 🌐 Integración API SIFEN
├── pdf_generator/    # 📄 Generación PDF KuDE
└── validators/       # ✅ Validaciones negocio
```

### Módulos Frontend
```
frontend/src/
├── components/       # Componentes reutilizables
├── pages/           # Páginas principales
├── services/        # Llamadas API
├── store/           # Estado global (Zustand)
└── utils/           # Utilidades
```

---

## 🔧 APIs y Endpoints

### Backend REST API

#### Autenticación
```bash
POST   /auth/login          # Login usuario
POST   /auth/register       # Registro usuario
POST   /auth/refresh        # Refresh token
POST   /auth/logout         # Logout
```

#### Facturas
```bash
GET    /v1/facturas         # Listar facturas
POST   /v1/facturas         # Crear factura
GET    /v1/facturas/{id}    # Obtener factura
PUT    /v1/facturas/{id}    # Actualizar factura
DELETE /v1/facturas/{id}    # Eliminar factura
```

#### SIFEN Integration
```bash
POST   /v1/sifen/enviar                    # Enviar documento a SIFEN
GET    /v1/sifen/consultar/{cdc}           # Consultar estado documento
POST   /v1/sifen/cancelar/{cdc}            # Cancelar documento
GET    /v1/sifen/consultar-ruc/{ruc}/{dv}  # Consultar RUC
```

#### Documentos
```bash
POST   /v1/documentos/generar-xml      # Generar XML SIFEN
POST   /v1/documentos/firmar           # Firmar documento
POST   /v1/documentos/generar-pdf      # Generar PDF KuDE
GET    /v1/documentos/{id}/descargar   # Descargar documento
```

### SIFEN API Endpoints

#### Ambiente Test
```bash
Base URL: https://sifen-test.set.gov.py
```

#### Ambiente Producción  
```bash
Base URL: https://sifen.set.gov.py
```

#### Servicios Principales
```bash
# Envío de documentos
POST /de/ws/sync/recibe-de-json
POST /de/ws/async/recibe-lote

# Consultas
GET  /de/ws/consultas/consulta-de
GET  /de/ws/consultas/consulta-ruc

# Eventos
POST /de/ws/eventos/evento
```

---

## 🗄️ Base de Datos

### Tablas Principales
```sql
-- Empresas y usuarios
users              # Usuarios del sistema
companies          # Empresas registradas
establishments     # Establecimientos por empresa

-- Documentos electrónicos
documents          # Documentos base
invoices          # Facturas específicas
invoice_items     # Items de facturas
digital_signatures # Firmas digitales

-- Clientes y productos
customers         # Clientes/receptores
products          # Catálogo de productos
tax_rates         # Tasas de impuestos

-- SIFEN integration
sifen_responses   # Respuestas de SIFEN
sifen_logs        # Logs de integración
cdc_sequence      # Secuencia CDC
```

### Comandos Database Útiles
```bash
# Migración nueva
cd backend && alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
alembic upgrade head

# Rollback migración
alembic downgrade -1

# Ver historial
alembic history

# Reset completo (desarrollo)
alembic downgrade base && alembic upgrade head
```

---

## 🧪 Testing

### Comandos de Testing
```bash
# Tests completos
pytest

# Tests específicos
pytest app/services/xml_generator/tests/
pytest app/api/v1/test_facturas.py

# Con cobertura
pytest --cov=app --cov-report=html

# Tests específicos por marca
pytest -m "unit"        # Solo unit tests
pytest -m "integration" # Solo integration tests
pytest -m "slow"        # Tests lentos
```

### Marcadores de Test
```python
# En archivos de test
@pytest.mark.unit
@pytest.mark.integration  
@pytest.mark.slow
@pytest.mark.sifen       # Tests que requieren SIFEN
```

### Fixtures Útiles
```python
# Fixtures disponibles globalmente
@pytest.fixture
def client():            # Cliente HTTP para API
def db_session():        # Sesión DB para tests
def sample_invoice():    # Factura de ejemplo
def test_certificate():  # Certificado de prueba
def mock_sifen():        # Mock respuestas SIFEN
```

---

## 🔐 Certificados y Firma Digital

### Configuración Rápida Desarrollo
```bash
# Generar certificado de prueba
python -c "
from backend.app.services.digital_sign.examples.generate_test_cert import generate_test_certificate
generate_test_certificate('./certificates/test/dev_cert.p12', 'dev123', 'CN=Test,C=PY', '12345678')
"
```

### Variables de Entorno Certificados
```bash
# .env
SIFEN_CERT_PATH=./certificates/test/dev_cert.p12
SIFEN_CERT_PASSWORD=dev123
SIFEN_ENVIRONMENT=test
```

### Validar Certificado
```python
# Python quick test
from cryptography.hazmat.primitives import serialization
with open('cert.p12', 'rb') as f:
    private_key, cert, additional_certs = serialization.pkcs12.load_key_and_certificates(
        f.read(), b'password'
    )
print(f"Certificado válido: {cert.subject}")
```

---

## 🐛 Debug y Troubleshooting

### Logs Útiles
```bash
# Backend logs
tail -f backend/logs/app.log
tail -f backend/logs/sifen.log

# Docker logs
docker-compose logs -f backend
docker-compose logs -f postgres

# Frontend logs (browser)
# Consola del desarrollador F12
```

### Debug Python
```python
# Breakpoint interactivo
import pdb; pdb.set_trace()

# Log estructurado
import structlog
logger = structlog.get_logger()
logger.info("Debug info", user_id=123, action="create_invoice")
```

### Problemas Comunes

#### Puerto ocupado
```bash
# Verificar qué usa el puerto
lsof -i :8000
# Terminar proceso
kill -9 <PID>
```

#### Error de dependencias
```bash
# Limpiar e reinstalar
cd backend && rm -rf venv && python -m venv venv
source venv/bin/activate && pip install -r requirements-dev.txt
```

#### Error Docker
```bash
# Reset completo
docker-compose down -v
docker system prune -a
```

#### Error de certificados
```bash
# Regenerar certificado de desarrollo
rm certificates/test/dev_cert.p12
python scripts/generate_dev_cert.py
```

---

## 📋 Checklists

### ✅ Checklist Deploy Desarrollo
- [ ] Virtual environment activado
- [ ] Variables de entorno configuradas
- [ ] PostgreSQL funcionando
- [ ] Redis funcionando  
- [ ] Certificados configurados
- [ ] Tests pasando
- [ ] Migraciones aplicadas

### ✅ Checklist Antes de Commit
- [ ] Tests unitarios pasando
- [ ] Linter ejecutado (`make lint`)
- [ ] No secrets en código
- [ ] Documentación actualizada
- [ ] Archivos temporales limpiados

### ✅ Checklist Integration Test
- [ ] XML válido generado
- [ ] Firma digital exitosa
- [ ] Envío a SIFEN test exitoso
- [ ] PDF KuDE generado correctamente
- [ ] CDC válido obtenido

### ✅ Checklist Pre-Producción
- [ ] Certificado PSC válido configurado
- [ ] Ambiente SIFEN producción configurado
- [ ] Backup de base de datos
- [ ] Monitoreo configurado
- [ ] Tests end-to-end pasando

---

## 🚀 Flujo de Desarrollo

### Workflow Típico
```bash
# 1. Inicio del día
make docker-up
source backend/venv/bin/activate

# 2. Desarrollo de feature
git checkout -b feature/nueva-funcionalidad

# 3. Desarrollo modular (una función a la vez)
# Escribir función → Test → Validar → Commit

# 4. Testing continuo
pytest app/services/xml_generator/tests/test_nueva_funcionalidad.py -v

# 5. Antes de commit
make lint
make test

# 6. Commit y push
git add .
git commit -m "feat: agregar nueva funcionalidad"
git push origin feature/nueva-funcionalidad
```

### Patrón de Desarrollo Modular
```python
# 1. Crear módulo
# backend/app/services/nuevo_modulo/
#   ├── __init__.py
#   ├── nuevo_modulo.py      # Implementación principal
#   ├── models.py            # Modelos Pydantic
#   ├── exceptions.py        # Excepciones custom
#   ├── README.md           # Documentación del módulo
#   └── tests/
#       ├── __init__.py
#       ├── test_nuevo_modulo.py
#       └── conftest.py

# 2. Implementar función básica
def nueva_funcion(param: str) -> str:
    """Docstring descriptivo"""
    # Implementación
    return resultado

# 3. Escribir test inmediatamente
def test_nueva_funcion():
    resultado = nueva_funcion("test")
    assert resultado == "esperado"

# 4. Ejecutar test
pytest app/services/nuevo_modulo/tests/ -v

# 5. Refactorizar si es necesario
# 6. Documentar en README.md del módulo
```

---

## 📊 Métricas y Monitoreo

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# Database health  
curl http://localhost:8000/health/db

# SIFEN connectivity
curl http://localhost:8000/health/sifen

# Redis health
curl http://localhost:8000/health/redis
```

### Métricas de Performance
```python
# En código backend - usar decoradores
from functools import wraps
import time

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} tomó {end - start:.2f}s")
        return result
    return wrapper

@measure_time
def generar_xml_factura(data):
    # Implementación
    pass
```

---

## 🔧 Utilidades y Helpers

### Generadores de Datos de Prueba
```python
# backend/app/utils/test_data.py

def generar_factura_test():
    """Genera factura de prueba válida"""
    return {
        "ruc_emisor": "12345678",
        "dv_emisor": "9",
        "nombre_emisor": "Empresa Test",
        "establecimiento": "001",
        "punto_expedicion": "001",
        "numero_documento": "0000001",
        "tipo_documento": 1,
        "moneda": "PYG",
        "items": [
            {
                "descripcion": "Producto Test",
                "cantidad": 1,
                "precio_unitario": 100000,
                "iva": 10
            }
        ]
    }

def generar_cdc_test():
    """Genera CDC de prueba válido"""
    import random
    return f"01{random.randint(10000000, 99999999)}7001001{random.randint(1000000, 9999999)}202501011{random.randint(100000000, 999999999)}{random.randint(0, 9)}"
```

### Validadores Rápidos
```python
# Validar RUC paraguayo
def validar_ruc(ruc: str, dv: str) -> bool:
    """Valida RUC paraguayo con DV"""
    # Implementación algoritmo módulo 11
    pass

# Validar CDC
def validar_cdc(cdc: str) -> bool:
    """Valida formato CDC SIFEN"""
    return len(cdc) == 44 and cdc.isdigit()

# Validar fecha emisión
def validar_fecha_emision(fecha: str) -> bool:
    """Valida que fecha esté dentro de 72h"""
    from datetime import datetime, timedelta
    try:
        fecha_emision = datetime.strptime(fecha, "%Y-%m-%dT%H:%M:%S")
        ahora = datetime.now()
        return (ahora - fecha_emision).total_seconds() <= 72 * 3600
    except:
        return False
```

---

## 🎯 Comandos por Módulo

### XML Generator
```bash
# Tests específicos
pytest app/services/xml_generator/tests/ -v

# Generar XML de prueba
python -m app.services.xml_generator.examples.generate_sample_xml

# Validar XML contra XSD
python -m app.services.xml_generator.validators.validate_xml sample.xml
```

### Digital Sign
```bash
# Tests de firma
pytest app/services/digital_sign/tests/ -v

# Firmar documento de prueba
python -m app.services.digital_sign.examples.sign_sample_document

# Validar certificado
python -m app.services.digital_sign.utils.validate_certificate cert.p12
```

### SIFEN Client
```bash
# Tests de integración
pytest app/services/sifen_client/tests/ -v -m integration

# Test de conectividad
python -m app.services.sifen_client.examples.test_connectivity

# Enviar documento de prueba
python -m app.services.sifen_client.examples.send_test_document
```

---

## 🔍 Debugging Específico SIFEN

### Logs Estructura JSON
```python
# Configuración structlog
import structlog

logger = structlog.get_logger("sifen")

# Log de request SIFEN
logger.info(
    "sifen_request",
    method="POST",
    url="/de/ws/sync/recibe-de-json",
    cdc="01234567890123456789012345678901234567890123",
    size_kb=len(xml_content) / 1024
)

# Log de response SIFEN
logger.info(
    "sifen_response", 
    cdc="01234567890123456789012345678901234567890123",
    codigo="0260",
    estado="Aprobado",
    tiempo_respuesta_ms=response_time
)
```

### Debug XML
```python
# Formatear XML para debug
from lxml import etree

def pretty_print_xml(xml_string):
    """Formatea XML para debugging"""
    root = etree.fromstring(xml_string)
    return etree.tostring(root, pretty_print=True, encoding='unicode')

# Validar estructura XML
def debug_xml_structure(xml_path):
    """Debug estructura XML"""
    tree = etree.parse(xml_path)
    for elem in tree.iter():
        print(f"{elem.tag}: {elem.text}")
```

---

## 📱 Frontend Quick Commands

### React + TypeScript
```bash
# Iniciar desarrollo
cd frontend && npm run dev

# Build producción
npm run build

# Tests
npm run test

# Lint
npm run lint

# Type check
npm run type-check
```

### Estado Global (Zustand)
```typescript
// stores/useInvoiceStore.ts
import { create } from 'zustand'

interface InvoiceState {
  invoices: Invoice[]
  currentInvoice: Invoice | null
  loading: boolean
  fetchInvoices: () => Promise<void>
  createInvoice: (invoice: CreateInvoiceRequest) => Promise<void>
}

export const useInvoiceStore = create<InvoiceState>((set, get) => ({
  invoices: [],
  currentInvoice: null,
  loading: false,
  
  fetchInvoices: async () => {
    set({ loading: true })
    try {
      const response = await api.get('/v1/facturas')
      set({ invoices: response.data })
    } finally {
      set({ loading: false })
    }
  }
}))
```

---

## 🚨 Alerts y Notificaciones

### Códigos de Error Críticos
```bash
# Monitorear estos errores en logs
grep -E "(1250|0141|0142)" backend/logs/sifen.log

# Alertas automáticas
# En producción configurar alertas para:
- RUC inexistente (1250)
- Firma inválida (0141) 
- Certificado inválido (0142)
- Timeout SIFEN (>30s)
- Tasa de error >5%
```

### Health Check Automation
```bash
# Script de monitoreo
#!/bin/bash
# scripts/health-check.sh

check_service() {
    local url=$1
    local service=$2
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
        echo "✅ $service OK"
    else
        echo "❌ $service DOWN"
        # Enviar alerta
    fi
}

check_service "http://localhost:8000/health" "Backend"
check_service "http://localhost:3000" "Frontend"
```

---

## 🎉 Finalización

### **Documentos de Referencia Completados:**

1. ✅ **certificate_setup.md** - Ya existía
2. ✅ **development_setup.md** - Guía unificada de configuración  
3. ✅ **quick_reference.md** - Referencia rápida completa

### **Próximos Pasos Recomendados:**

1. **Validar el setup** usando `scripts/validate-setup.sh`
2. **Seguir la hoja de ruta** paso a paso según `hoja_de_ruta_optimizada.md`
3. **Consultar esta referencia** durante desarrollo diario
4. **Mantener actualizada** la documentación conforme avances

### **Para Máxima Eficiencia:**

```bash
# Bookmark estos comandos
alias sifen-dev="cd /path/to/sifen-facturacion && make dev"
alias sifen-test="cd /path/to/sifen-facturacion && make test"
alias sifen-logs="cd /path/to/sifen-facturacion && docker-compose logs -f"
```

**¡Tu documentación técnica v150 está completa y lista para desarrollo eficiente! 🚀**