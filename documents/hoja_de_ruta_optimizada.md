🚀 Hoja de Ruta - Software Facturación Electrónica Paraguay (SIFEN)

Optimizada para desarrollo incremental con Cursor AI
📋 Información del Proyecto

Campo	Detalle
Objetivo	Desarrollar software SaaS para emisión de facturas electrónicas en Paraguay
Stack Principal	Python (FastAPI) + React + PostgreSQL + Docker
Timeline MVP	12-16 semanas (desarrollo incremental)
Target	PyMEs y empresas medianas paraguayas
Metodología	Desarrollo modular con testing continuo

🎯 Principios de Desarrollo para Cursor
🔄 DESARROLLO INCREMENTAL OBLIGATORIO

    Una funcionalidad a la vez: Completar módulo antes de pasar al siguiente
    Testing inmediato: Tests unitarios después de cada función
    Validación continua: Probar cada componente antes de integrar
    Documentación en paralelo: README.md por módulo completado

📝 ORDEN DE PRIORIDADES CURSOR

    BACKEND CORE → Funcionalidad crítica primero
    TESTING → Validación inmediata de cada módulo
    INTEGRACIÓN → Conexión entre módulos ya probados
    FRONTEND → Interfaz después de backend estable
    DEPLOYMENT → Solo con sistema completamente probado

🔧 FASE 1: Configuración Base (Semanas 1-2)

Objetivo: Ambiente de desarrollo funcionando con primeros tests
📍 Semana 1: Setup del Proyecto

CURSOR: Genera en este orden exacto
🎯 Paso 1.1: Ambiente de Desarrollo Python

bash

# CURSOR: Configurar ambiente Python PRIMERO:
# 1. Verificar Python 3.9+ instalado
# 2. Crear virtual environment
# 3. Activar venv y configurar requirements básicos
# 4. Configurar IDE/Editor para usar venv correcto

    Verificar python --version (mínimo 3.9)
    Crear virtual environment: python -m venv venv
    Activar venv: source venv/bin/activate (Linux/Mac) o venv\Scripts\activate (Windows)
    Upgrade pip: pip install --upgrade pip
    VALIDAR: which python apunta al venv creado

🎯 Paso 1.2: Estructura de Proyecto

bash

# CURSOR: Crear estructura completa de carpetas
# Usar la estructura definida en ./docs/project_structure.md

    Crear estructura de carpetas completa
    Setup git con .gitignore apropiado (incluir venv/, __pycache__/)
    Configurar .cursorrules en raíz del proyecto
    Crear .env.example con variables necesarias
    VALIDAR: Estructura creada correctamente

🎯 Paso 1.3: Backend Base

python

# CURSOR: IMPORTANTE - Activar venv antes de instalar paquetes
# 1. source venv/bin/activate (o equivalent en Windows)
# 2. pip install fastapi uvicorn sqlalchemy psycopg2-binary
# 3. backend/app/main.py - FastAPI básico
# 4. backend/app/core/config.py - Configuración
# 5. backend/app/core/database.py - Conexión BD
# 6. backend/requirements.txt - Generar con pip freeze

    ACTIVAR VENV PRIMERO: Verificar prompt muestra (venv)
    Instalar dependencias básicas: FastAPI, SQLAlchemy, etc.
    FastAPI app básica con endpoint /health
    Configuración de variables de entorno
    Conexión PostgreSQL básica (sin Docker primero)
    Generar requirements.txt con pip freeze > requirements.txt
    TEST: python backend/app/main.py inicia sin errores
    TEST: curl localhost:8000/health responde OK

🎯 Paso 1.4: Docker Setup

dockerfile

# CURSOR: Crear Dockerfiles y docker-compose
# IMPORTANTE: El Dockerfile debe copiar requirements.txt y hacer pip install
# 1. docker/backend/Dockerfile - Usar venv o instalar global
# 2. docker-compose.yml (backend + postgres + redis)  
# 3. .dockerignore - Excluir venv/ local

    Docker backend funcionando (puede usar requirements.txt)
    Docker-compose con servicios básicos
    .dockerignore configurado (excluir venv/, __pycache__/)
    TEST: docker-compose up funciona sin errores
    TEST: Backend en container responde en puerto configurado

📍 Semana 2: Modelos Base y Autenticación
🎯 Paso 2.1: Modelos Base de Datos

python

# CURSOR: Crear modelos en este orden:
# 1. backend/app/models/base.py - Modelo base
# 2. backend/app/models/user.py - Usuario básico
# 3. backend/app/models/empresa.py - Empresa/contribuyente
# 4. Alembic migration inicial

    Modelo Usuario con autenticación JWT
    Modelo Empresa (contribuyente)
    Migración Alembic funcionando
    TEST: Crear usuario y empresa via DB

🎯 Paso 2.2: API Autenticación

python

# CURSOR: Implementar endpoints de auth:
# 1. backend/app/api/v1/auth.py - Login/register
# 2. backend/app/core/security.py - JWT functions
# 3. Tests unitarios para auth

    Endpoint /auth/login y /auth/register
    JWT token generation/validation
    Tests unitarios pasando (>80% cobertura)
    TEST: Login via Postman/curl funciona

⚙️ FASE 2: Módulos Core SIFEN (Semanas 3-8)

Objetivo: Funcionalidad crítica SIFEN completamente probada
📍 Semana 3-4: Módulo XML Generator ⚠️ ALTA FRICCIÓN

CURSOR: Este es el módulo MÁS CRÍTICO - implementar paso a paso
🎯 Paso 3.1: Setup Módulo XML

python

# CURSOR: Crear estructura del módulo:
# 1. backend/app/services/xml_generator/__init__.py
# 2. backend/app/services/xml_generator/README.md
# 3. backend/app/services/xml_generator/config.py
# 4. backend/app/services/xml_generator/tests/__init__.py

    Estructura módulo XML completa
    README.md con propósito y API
    Configuración específica del módulo
    VALIDAR: Estructura correcta según cursorrules

🎯 Paso 3.2: Generador XML Simple

python

# CURSOR: Implementar generación XML básica:
# 1. xml_generator/models.py - Clases para datos SIFEN
# 2. xml_generator/templates/factura_simple.xml - Template básico
# 3. xml_generator/generator.py - Generador principal
# 4. Tests con datos de prueba

    Clases Pydantic para datos SIFEN básicos
    Template XML para factura simple (sin complejidades)
    Función generate_simple_invoice_xml()
    TEST: Generar XML válido con datos de prueba

🎯 Paso 3.3: Validación XML Local

python

# CURSOR: Implementar validador XML:
# 1. xml_generator/validators.py - Validación contra XSD
# 2. xml_generator/schemas/ - Esquemas XSD SIFEN  
# 3. Tests de validación

    Validador XML contra esquemas oficiales
    Manejo de errores de validación específicos
    Tests con XML válidos e inválidos
    TEST: Validar XML generado contra esquema SIFEN

🎯 Paso 3.4: Casos de Prueba Exhaustivos

python

# CURSOR: Crear suite de tests completa:
# 1. tests/fixtures/valid_invoices.json - Datos válidos
# 2. tests/fixtures/invalid_invoices.json - Datos inválidos  
# 3. tests/test_xml_generation.py - Tests exhaustivos

    20+ casos de prueba diferentes
    Tests con datos edge cases
    Tests de performance (generar 100 XMLs < 5seg)
    TEST: 100% tests pasando, >85% cobertura

🚨 CHECKPOINT XML: No continuar hasta que este módulo esté 100% funcional y probado
📍 Semana 5: Módulo Digital Signature ⚠️ ALTA FRICCIÓN
🎯 Paso 5.1: Setup Certificados de Prueba

python

# CURSOR: Configurar manejo de certificados:
# 1. digital_sign/certificate_manager.py - Gestión PFX
# 2. digital_sign/config.py - Config certificados
# 3. tests/fixtures/test_certificate.pfx - Cert de prueba

    Carga y validación de certificados PFX
    Manejo seguro de passwords
    Validación de vigencia de certificados
    TEST: Cargar certificado de prueba exitosamente

🎯 Paso 5.2: Firmado XML

python

# CURSOR: Implementar firma digital:
# 1. digital_sign/signer.py - Firmador XML
# 2. digital_sign/csc_manager.py - Gestión CSC
# 3. Tests de firma

    Función sign_xml_document()
    Gestión de CSC (Código Seguridad Contribuyente)
    Validación de XML firmado
    TEST: Firmar XML y validar firma

🚨 CHECKPOINT FIRMA: Firmar XML generado en paso anterior
📍 Semana 6-7: Módulo SIFEN Client ⚠️ MUY ALTA FRICCIÓN
🎯 Paso 6.1: Cliente SOAP Básico

python

# CURSOR: Implementar cliente SIFEN:
# 1. sifen_client/client.py - Cliente SOAP
# 2. sifen_client/config.py - Endpoints SIFEN
# 3. sifen_client/models.py - Request/Response models

    Cliente SOAP para ambiente TEST
    Configuración endpoints SIFEN
    Modelos para requests/responses
    TEST: Conectar a SIFEN test (sin enviar docs)

🎯 Paso 6.2: Envío de Documentos

python

# CURSOR: Implementar envío a SIFEN:
# 1. sifen_client/document_sender.py - Envío documentos
# 2. sifen_client/response_parser.py - Parser respuestas
# 3. sifen_client/error_handler.py - Manejo errores SIFEN

    Función send_document_to_sifen()
    Parser de respuestas SIFEN (éxito/error)
    Mapeo códigos de error SIFEN
    TEST: Enviar documento de prueba a SIFEN test

🎯 Paso 6.3: Sistema de Retry y Logging

python

# CURSOR: Implementar robustez:
# 1. sifen_client/retry_manager.py - Sistema reintentos
# 2. sifen_client/logger.py - Logging específico
# 3. Tests de resiliencia

    Retry con backoff exponencial
    Logging estructurado de requests/responses
    Manejo de timeouts y errores de red
    TEST: Simular fallos de red y validar retry

🚨 CHECKPOINT SIFEN: Enviar factura completa (XML → Firma → SIFEN) exitosamente
📍 Semana 8: Módulo PDF Generator
🎯 Paso 8.1: Generador PDF KuDE

python

# CURSOR: Implementar generación PDF:
# 1. pdf_generator/kude_generator.py - Generador PDF
# 2. pdf_generator/templates/kude_template.html - Template oficial
# 3. pdf_generator/qr_generator.py - Códigos QR

    Template HTML para PDF KuDE oficial
    Generación de códigos QR con validación
    Conversión HTML → PDF
    TEST: Generar PDF KuDE válido

🏗️ FASE 3: APIs y Funcionalidades (Semanas 9-11)

Objetivo: APIs REST funcionales con todos los módulos integrados
📍 Semana 9: APIs de Negocio
🎯 Paso 9.1: API Facturas

python

# CURSOR: Crear endpoints facturas:
# 1. api/v1/facturas.py - CRUD facturas
# 2. schemas/factura.py - DTOs facturas
# 3. repositories/factura_repository.py - Acceso datos

    Endpoints: POST, GET, PUT, DELETE facturas
    Validaciones de negocio Paraguay
    Integración con módulos XML/SIFEN
    TEST: CRUD completo via API

🎯 Paso 9.2: API Integrada SIFEN

python

# CURSOR: Endpoint procesamiento completo:
# 1. api/v1/sifen.py - Endpoints SIFEN integration
# 2. services/factura_service.py - Orquestador servicios
# 3. Tests integración completa

    Endpoint /facturas/{id}/enviar-sifen
    Orquestación: Generar XML → Firmar → Enviar → PDF
    Manejo de estados de documentos
    TEST: Proceso completo end-to-end

📍 Semana 10-11: Gestión de Datos
🎯 Paso 10.1: APIs Soporte

python

# CURSOR: Crear APIs auxiliares:
# 1. api/v1/clientes.py - Gestión clientes
# 2. api/v1/productos.py - Catálogo productos
# 3. api/v1/consultas.py - Consultas RUC, estados

    CRUD clientes con validación RUC
    Catálogo productos/servicios
    Consulta RUC automática vs SIFEN
    TEST: APIs auxiliares funcionando

🎨 FASE 4: Frontend (Semanas 12-14)

Objetivo: Interfaz funcional y accesible
📍 Semana 12: Setup Frontend
🎯 Paso 12.1: Base React

typescript

# CURSOR: Setup frontend base:
# 1. frontend/src/App.tsx - App principal
# 2. frontend/src/services/api.ts - Cliente API
# 3. frontend/src/store/ - Estado global

    React app con TypeScript
    Cliente Axios configurado
    Estado global (Redux/Zustand)
    TEST: Frontend conecta con backend

🎯 Paso 12.2: Componentes Base

typescript

# CURSOR: Crear componentes básicos:
# 1. components/common/Button/ - Botón accesible
# 2. components/common/Input/ - Input validado
# 3. components/layout/Header/ - Header principal

    Componentes con accesibilidad WCAG 2.1
    Design system básico
    Layout responsive
    TEST: Componentes renderizan correctamente

📍 Semana 13-14: Interfaces Principales
🎯 Paso 13.1: Dashboard

typescript

# CURSOR: Crear dashboard principal:
# 1. pages/Dashboard/Dashboard.tsx - Vista principal
# 2. components/charts/ - Gráficos estados
# 3. services/dashboard.service.ts - Datos dashboard

    Dashboard con métricas principales
    Estados de documentos en tiempo real
    Gráficos de facturas enviadas/pendientes
    TEST: Dashboard carga datos correctamente

🎯 Paso 13.2: Formulario Facturación

typescript

# CURSOR: Crear formulario facturación:
# 1. pages/Facturas/NuevaFactura.tsx - Formulario
# 2. components/forms/FacturaForm/ - Form components
# 3. Validación en tiempo real

    Formulario completo de facturación
    Validaciones en tiempo real
    Integración con APIs backend
    TEST: Crear factura desde frontend

🧪 FASE 5: Testing y Deploy (Semanas 15-16)

Objetivo: Sistema completamente probado y desplegado
📍 Semana 15: Testing Integral
🎯 Paso 15.1: Tests End-to-End

python

# CURSOR: Crear tests E2E:
# 1. tests/e2e/test_full_workflow.py - Flujo completo
# 2. tests/integration/test_sifen_integration.py - Integración SIFEN
# 3. tests/performance/test_load.py - Tests carga

    Test flujo completo: Crear factura → SIFEN → PDF
    Tests integración con SIFEN real (ambiente test)
    Tests de carga (100 facturas simultáneas)
    TEST: Todos los tests E2E pasando

📍 Semana 16: Deploy y Go-Live
🎯 Paso 16.1: Deploy Producción

bash

# CURSOR: Scripts de deployment:
# 1. scripts/deployment/deploy.sh - Deploy script
# 2. docker/docker-compose.prod.yml - Config producción
# 3. infrastructure/terraform/ - IaC setup

    Deploy en servidor de producción
    Certificados SSL configurados
    Monitoreo y logging configurado
    TEST: Aplicación funcionando en producción

📊 Control de Calidad por Fase
✅ Criterios de Completitud por Módulo

Cada módulo debe cumplir TODOS estos criterios antes de continuar:

python

# CURSOR: Validar estos puntos antes de continuar:
MODULO_COMPLETO = {
    "tests_unitarios": ">80% cobertura",
    "tests_integracion": "Todos pasando", 
    "documentacion": "README.md actualizado",
    "ejemplos_uso": "Funcionando",
    "error_handling": "Implementado",
    "logging": "Configurado",
    "sin_dependencias_circulares": True
}

🎯 Métricas de Éxito MVP
Funcionales ✅

    Generar factura electrónica válida según Manual v150
    Enviar documento a SIFEN y recibir respuesta exitosa
    Generar PDF KuDE con formato oficial SET
    Dashboard con estados de documentos en tiempo real
    Gestión completa de clientes y productos

Técnicas 🔧

    API response time < 2 segundos (95percentil)
    99.5% uptime en producción
    0 vulnerabilidades críticas de seguridad
    Soporte para 100+ facturas/día por cliente
    Cobertura tests >85% en módulos críticos

Negocio 💼

    3-5 empresas beta usando el sistema exitosamente
    100+ facturas procesadas sin errores críticos
    Feedback usabilidad >4/5 estrellas
    Validación modelo de precios con clientes

🚨 Puntos de Alta Fricción - Plan de Mitigación
1. Generación XML Compleja (Semana 3-4)

python

# CURSOR: Si encuentras problemas con XML:
# 1. Usar librerías existentes como referencia (pysifen)
# 2. Implementar validación local ANTES de enviar a SIFEN
# 3. Crear casos de prueba del Manual Técnico v150
# 4. NO avanzar hasta que XML sea 100% válido

2. Integración SIFEN SOAP (Semana 6-7)

python

# CURSOR: Para problemas con SIFEN:
# 1. Implementar logging exhaustivo de requests/responses
# 2. Manejar TODOS los códigos de error del manual
# 3. Sistema de retry con backoff exponencial
# 4. Ambiente de prueba dedicado con certificados válidos

3. Certificación Producción (Semana 15)

bash

# CURSOR: Preparar certificación desde Semana 8:
# 1. Documentar todos los casos de prueba ejecutados
# 2. Mantener logs de pruebas con SIFEN test
# 3. Preparar certificados de producción con anticipación
# 4. Plan B: Ambiente sandbox extendido si hay retrasos

📚 Recursos y Referencias para Cursor
Documentos Obligatorios 📋

    ./docs/manual_tecnico_v150.pdf - Manual oficial SIFEN
    ./docs/sifen_error_codes.json - Códigos de error oficiales
    ./docs/xml_examples/ - Ejemplos XML válidos por tipo
    ./shared/constants/sifen_codes.ts - Constantes SIFEN

Librerías de Referencia 🔗

    pysifen - Implementación Python existente
    rshk-jsifenlib - Implementación Java de referencia
    FacturaSend API - Referencia comercial

Ambientes y URLs 🌐

    SIFEN Test: https://sifen-test.set.gov.py
    eKuatia Portal: https://ekuatia.set.gov.py
    Documentación: https://www.dnit.gov.py/web/e-kuatia/documentacion

🎯 Comandos Cursor para Cada Fase
Iniciar Proyecto (PRIMER PASO)

bash

# CURSOR: ANTES QUE NADA - Setup ambiente Python:
1. Verificar: python --version (mínimo 3.9)
2. Crear: python -m venv venv
3. Activar: source venv/bin/activate (Linux/Mac) o venv\Scripts\activate (Windows)
4. Validar: which python (debe apuntar al venv)
5. Upgrade: pip install --upgrade pip

Iniciar Nueva Fase

bash

# CURSOR: Antes de empezar cada fase:
1. ACTIVAR VENV: source venv/bin/activate
2. Revisar ./docs/hoja_de_ruta_optimizada.md
3. Validar que fase anterior esté 100% completa
4. Crear branch específico para la fase
5. Ejecutar tests de la fase anterior

Completar Módulo

bash

# CURSOR: Al completar cada módulo:
1. VENV ACTIVO: Verificar prompt (venv)
2. Ejecutar tests unitarios (>80% cobertura)
3. Ejecutar tests de integración
4. Actualizar README.md del módulo
5. Actualizar requirements.txt si es necesario
6. Validar criterios de completitud
7. Commit con mensaje descriptivo

Validación Continua

python

# CURSOR: Ejecutar después de cada cambio significativo:
# IMPORTANTE: Asegurar venv activo antes de ejecutar
source venv/bin/activate  # Si no está activo
pytest backend/app/services/[modulo]/tests/ -v --cov

📝 Documento optimizado para desarrollo incremental con Cursor AI
🔄 Actualizar según progreso del proyecto
