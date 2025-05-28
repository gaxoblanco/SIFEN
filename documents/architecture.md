sifen-facturacion/
├── README.md                                # Documentación principal del proyecto
├── .cursorrules                             # Reglas para Cursor AI
├── .gitignore                               # Archivos a ignorar por Git
├── docker-compose.yml                       # Configuración Docker para desarrollo
├── Makefile                                 # Comandos automatizados del proyecto
│
├── backend/                                 # API y lógica de negocio
│   ├── Dockerfile                          # Imagen Docker backend
│   ├── requirements.txt                    # Dependencias Python
│   ├── requirements-dev.txt                # Dependencias desarrollo
│   ├── pyproject.toml                      # Configuración proyecto Python
│   ├── pytest.ini                         # Configuración pytest
│   ├── .env.example                        # Variables de entorno template
│   │
│   ├── app/                                # Código principal aplicación
│   │   ├── __init__.py
│   │   ├── main.py                         # Entry point FastAPI
│   │   ├── config.py                       # Configuración aplicación
│   │   │
│   │   ├── api/                            # Endpoints REST API
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                     # Dependencias comunes
│   │   │   ├── router.py                   # Router principal
│   │   │   │
│   │   │   ├── v1/                         # Versión 1 de la API
│   │   │   │   ├── __init__.py
│   │   │   │   ├── facturas.py             # Endpoints facturas
│   │   │   │   ├── clientes.py             # Endpoints gestión clientes
│   │   │   │   ├── documentos.py           # Endpoints documentos
│   │   │   │   ├── auth.py                 # Endpoints autenticación
│   │   │   │   ├── sifen.py                # Endpoints integración SIFEN
│   │   │   │   └── reportes.py             # Endpoints reportes
│   │   │   │
│   │   │   └── middleware/                 # Middlewares personalizados
│   │   │       ├── __init__.py
│   │   │       ├── auth.py                 # Middleware autenticación
│   │   │       ├── cors.py                 # Middleware CORS
│   │   │       └── logging.py              # Middleware logging
│   │   │
│   │   ├── core/                           # Configuración y seguridad
│   │   │   ├── __init__.py
│   │   │   ├── config.py                   # Configuración central
│   │   │   ├── security.py                 # Funciones seguridad
│   │   │   ├── database.py                 # Configuración base datos
│   │   │   ├── logging.py                  # Configuración logging
│   │   │   └── exceptions.py               # Excepciones personalizadas
│   │   │
│   │   ├── models/                         # Modelos de base de datos
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # Modelo base común
│   │   │   ├── user.py                     # Modelo usuario
│   │   │   ├── empresa.py                  # Modelo empresa
│   │   │   ├── cliente.py                  # Modelo cliente
│   │   │   ├── producto.py                 # Modelo producto/servicio
│   │   │   ├── factura.py                  # Modelo factura
│   │   │   ├── documento.py                # Modelo documento electrónico
│   │   │   └── auditoria.py                # Modelo auditoría
│   │   │
│   │   ├── schemas/                        # Esquemas Pydantic (DTOs)
│   │   │   ├── __init__.py
│   │   │   ├── user.py                     # Schemas usuario
│   │   │   ├── empresa.py                  # Schemas empresa
│   │   │   ├── cliente.py                  # Schemas cliente
│   │   │   ├── producto.py                 # Schemas producto
│   │   │   ├── factura.py                  # Schemas factura
│   │   │   ├── documento.py                # Schemas documento
│   │   │   └── common.py                   # Schemas comunes
│   │   │
│   │   ├── services/                       # Lógica de negocio (MÓDULOS PRINCIPALES)
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── xml_generator/              # 🔥 MÓDULO: Generación XML SIFEN
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md               # Documentación módulo
│   │   │   │   ├── xml_generator.py        # Generador XML principal
│   │   │   │   ├── validators.py           # Validadores XML específicos
│   │   │   │   ├── templates/              # Templates XML por tipo documento
│   │   │   │   │   ├── factura.xml
│   │   │   │   │   ├── nota_credito.xml
│   │   │   │   │   └── nota_remision.xml
│   │   │   │   ├── tests/                  # Tests aislados del módulo
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── test_xml_generator.py
│   │   │   │   │   ├── test_validators.py
│   │   │   │   │   ├── fixtures/           # Datos de prueba
│   │   │   │   │   │   ├── valid_factura.json
│   │   │   │   │   │   └── invalid_data.json
│   │   │   │   │   └── mocks/              # Mocks para dependencias
│   │   │   │   │       └── mock_sifen.py
│   │   │   │   └── config.py               # Configuración módulo
│   │   │   │
│   │   │   ├── digital_sign/               # 🔥 MÓDULO: Firma digital
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── signer.py               # Firmador digital principal
│   │   │   │   ├── certificate_manager.py  # Gestor certificados PFX
│   │   │   │   ├── csc_manager.py          # Gestor CSC
│   │   │   │   ├── tests/
│   │   │   │   │   ├── test_signer.py
│   │   │   │   │   ├── test_certificate_manager.py
│   │   │   │   │   ├── fixtures/
│   │   │   │   │   │   └── test_certificate.pfx
│   │   │   │   │   └── mocks/
│   │   │   │   └── config.py
│   │   │   │
│   │   │   ├── sifen_client/               # 🔥 MÓDULO: Integración SIFEN
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── client.py               # Cliente SOAP SIFEN
│   │   │   │   ├── error_handler.py        # Manejador errores SIFEN
│   │   │   │   ├── retry_manager.py        # Gestor reintentos
│   │   │   │   ├── response_parser.py      # Parser respuestas SIFEN
│   │   │   │   ├── tests/
│   │   │   │   │   ├── test_client.py
│   │   │   │   │   ├── test_error_handler.py
│   │   │   │   │   ├── fixtures/
│   │   │   │   │   │   ├── sifen_responses.xml
│   │   │   │   │   │   └── error_responses.xml
│   │   │   │   │   └── mocks/
│   │   │   │   │       └── mock_soap_client.py
│   │   │   │   └── config.py
│   │   │   │
│   │   │   ├── pdf_generator/              # 🔥 MÓDULO: Generación PDF KuDE
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── kude_generator.py       # Generador PDF KuDE
│   │   │   │   ├── qr_generator.py         # Generador códigos QR
│   │   │   │   ├── templates/              # Templates PDF
│   │   │   │   │   ├── factura_template.html
│   │   │   │   │   └── styles.css
│   │   │   │   ├── tests/
│   │   │   │   │   ├── test_kude_generator.py
│   │   │   │   │   ├── test_qr_generator.py
│   │   │   │   │   ├── fixtures/
│   │   │   │   │   └── mocks/
│   │   │   │   └── config.py
│   │   │   │
│   │   │   ├── validators/                 # MÓDULO: Validaciones de negocio
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── ruc_validator.py        # Validador RUC
│   │   │   │   ├── documento_validator.py  # Validador documentos
│   │   │   │   ├── business_rules.py       # Reglas de negocio Paraguay
│   │   │   │   ├── tests/
│   │   │   │   └── config.py
│   │   │   │
│   │   │   ├── email/                      # MÓDULO: Envío de emails
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── email_service.py
│   │   │   │   ├── templates/
│   │   │   │   ├── tests/
│   │   │   │   └── config.py
│   │   │   │
│   │   │   └── queue/                      # MÓDULO: Sistema de colas
│   │   │       ├── __init__.py
│   │   │       ├── README.md
│   │   │       ├── queue_manager.py
│   │   │       ├── tasks.py
│   │   │       ├── tests/
│   │   │       └── config.py
│   │   │
│   │   ├── repositories/                   # Acceso a datos (Repository Pattern)
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # Repository base
│   │   │   ├── user_repository.py
│   │   │   ├── empresa_repository.py
│   │   │   ├── cliente_repository.py
│   │   │   ├── factura_repository.py
│   │   │   └── documento_repository.py
│   │   │
│   │   └── utils/                          # Utilidades comunes
│   │       ├── __init__.py
│   │       ├── date_utils.py               # Utilidades fechas
│   │       ├── file_utils.py               # Utilidades archivos
│   │       ├── crypto_utils.py             # Utilidades criptografía
│   │       └── helpers.py                  # Helpers generales
│   │
│   ├── alembic/                            # Migraciones base de datos
│   │   ├── versions/                       # Archivos migración
│   │   ├── env.py                          # Configuración Alembic
│   │   └── alembic.ini                     # Configuración Alembic
│   │
│   ├── docs/                               # Documentación técnica backend
│   │   ├── api.md                          # Documentación API
│   │   ├── architecture.md                 # Arquitectura backend
│   │   ├── database.md                     # Esquema base datos
│   │   └── deployment.md                   # Guía deployment
│   │
│   └── tests/                              # Tests de integración backend
│       ├── __init__.py
│       ├── conftest.py                     # Configuración pytest
│       ├── integration/                    # Tests integración
│       │   ├── test_sifen_integration.py
│       │   ├── test_database_integration.py
│       │   └── test_api_integration.py
│       ├── e2e/                           # Tests end-to-end
│       │   └── test_full_workflow.py
│       └── fixtures/                      # Fixtures globales
│           ├── database_fixtures.py
│           └── api_fixtures.py
│
├── frontend/                               # Interfaz de usuario
│   ├── Dockerfile                         # Imagen Docker frontend
│   ├── package.json                       # Dependencias Node.js
│   ├── package-lock.json
│   ├── tsconfig.json                      # Configuración TypeScript
│   ├── .eslintrc.js                       # Configuración ESLint
│   ├── .prettierrc                        # Configuración Prettier
│   ├── jest.config.js                     # Configuración Jest
│   ├── .env.example                       # Variables entorno template
│   │
│   ├── public/                            # Archivos estáticos
│   │   ├── index.html
│   │   ├── favicon.ico
│   │   └── manifest.json
│   │
│   ├── src/                               # Código fuente frontend
│   │   ├── index.tsx                      # Entry point React
│   │   ├── App.tsx                        # Componente principal
│   │   ├── reportWebVitals.ts             # Métricas performance
│   │   │
│   │   ├── components/                    # Componentes reutilizables
│   │   │   ├── common/                    # Componentes comunes
│   │   │   │   ├── Button/
│   │   │   │   │   ├── Button.tsx
│   │   │   │   │   ├── Button.test.tsx
│   │   │   │   │   ├── Button.stories.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── Input/
│   │   │   │   ├── Modal/
│   │   │   │   └── Loading/
│   │   │   │
│   │   │   ├── forms/                     # Componentes formularios
│   │   │   │   ├── FacturaForm/
│   │   │   │   ├── ClienteForm/
│   │   │   │   └── EmpresaForm/
│   │   │   │
│   │   │   └── layout/                    # Componentes layout
│   │   │       ├── Header/
│   │   │       ├── Sidebar/
│   │   │       ├── Footer/
│   │   │       └── Navigation/
│   │   │
│   │   ├── pages/                         # Páginas principales
│   │   │   ├── Dashboard/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Dashboard.test.tsx
│   │   │   │   └── index.ts
│   │   │   ├── Facturas/
│   │   │   │   ├── FacturasList.tsx
│   │   │   │   ├── FacturaDetail.tsx
│   │   │   │   ├── NuevaFactura.tsx
│   │   │   │   └── index.ts
│   │   │   ├── Clientes/
│   │   │   ├── Documentos/
│   │   │   ├── Reportes/
│   │   │   ├── Configuracion/
│   │   │   └── Auth/
│   │   │       ├── Login.tsx
│   │   │       └── Register.tsx
│   │   │
│   │   ├── services/                      # Servicios API
│   │   │   ├── api.ts                     # Configuración axios
│   │   │   ├── auth.service.ts            # Servicios autenticación
│   │   │   ├── facturas.service.ts        # Servicios facturas
│   │   │   ├── clientes.service.ts        # Servicios clientes
│   │   │   ├── sifen.service.ts           # Servicios SIFEN
│   │   │   └── types.ts                   # Tipos TypeScript
│   │   │
│   │   ├── store/                         # Estado global (Redux/Zustand)
│   │   │   ├── index.ts                   # Store principal
│   │   │   ├── slices/                    # Slices de estado
│   │   │   │   ├── auth.slice.ts
│   │   │   │   ├── facturas.slice.ts
│   │   │   │   └── ui.slice.ts
│   │   │   └── middleware/                # Middleware store
│   │   │       └── api.middleware.ts
│   │   │
│   │   ├── hooks/                         # Custom hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── useFacturas.ts
│   │   │   ├── useSifen.ts
│   │   │   └── useLocalStorage.ts
│   │   │
│   │   ├── utils/                         # Utilidades frontend
│   │   │   ├── formatters.ts              # Formateo datos
│   │   │   ├── validators.ts              # Validaciones
│   │   │   ├── constants.ts               # Constantes
│   │   │   └── helpers.ts                 # Helpers generales
│   │   │
│   │   ├── styles/                        # Estilos globales
│   │   │   ├── globals.css
│   │   │   ├── variables.css
│   │   │   └── components.css
│   │   │
│   │   └── assets/                        # Assets estáticos
│   │       ├── images/
│   │       ├── icons/
│   │       └── fonts/
│   │
│   └── tests/                             # Tests frontend
│       ├── __mocks__/                     # Mocks Jest
│       ├── utils/                         # Utilidades testing
│       └── setup.ts                       # Setup testing
│
├── shared/                                # Código compartido
│   ├── types/                            # Definiciones TypeScript
│   │   ├── sifen.types.ts                # Tipos específicos SIFEN
│   │   ├── api.types.ts                  # Tipos API
│   │   ├── business.types.ts             # Tipos de negocio
│   │   └── common.types.ts               # Tipos comunes
│   │
│   ├── constants/                        # Constantes compartidas
│   │   ├── sifen_codes.ts                # Códigos oficiales SIFEN
│   │   ├── error_messages.ts             # Mensajes error
│   │   ├── business_rules.ts             # Reglas negocio
│   │   └── api_endpoints.ts              # Endpoints API
│   │
│   └── schemas/                          # Esquemas validación
│       ├── sifen_schemas.json            # Esquemas XML SIFEN
│       ├── api_schemas.json              # Esquemas API
│       └── validation_rules.json         # Reglas validación
│
├── docs/                                 # Documentación proyecto
│   ├── README.md                         # Documentación principal
│   ├── hoja_de_ruta.pdf                 # Roadmap del proyecto
│   ├── manual_tecnico_v150.pdf          # Manual oficial SIFEN
│   ├── sifen_error_codes.json           # Códigos error oficiales
│   │
│   ├── xml_examples/                    # Ejemplos XML válidos
│   │   ├── factura_simple.xml
│   │   ├── factura_completa.xml
│   │   ├── nota_credito.xml
│   │   └── nota_remision.xml
│   │
│   ├── api/                             # Documentación API
│   │   ├── openapi.yaml                 # Especificación OpenAPI
│   │   ├── postman_collection.json      # Colección Postman
│   │   └── endpoints.md                 # Documentación endpoints
│   │
│   ├── deployment/                      # Documentación deployment
│   │   ├── development.md               # Setup desarrollo
│   │   ├── production.md                # Deploy producción
│   │   ├── docker.md                    # Guía Docker
│   │   └── certificates.md              # Setup certificados
│   │
│   ├── business/                        # Documentación negocio
│   │   ├── business_rules.md            # Reglas negocio Paraguay
│   │   ├── testing_scenarios.md         # Casos prueba críticos
│   │   ├── user_stories.md              # Historias usuario
│   │   └── troubleshooting.md           # Problemas y soluciones
│   │
│   └── architecture/                    # Documentación arquitectura
│       ├── overview.md                  # Visión general
│       ├── backend_architecture.md      # Arquitectura backend
│       ├── frontend_architecture.md     # Arquitectura frontend
│       ├── database_schema.md           # Esquema base datos
│       └── security.md                  # Consideraciones seguridad
│
├── scripts/                             # Scripts automatización
│   ├── setup/                          # Scripts setup
│   │   ├── setup-dev.sh                # Setup desarrollo
│   │   ├── setup-prod.sh               # Setup producción
│   │   └── install-deps.sh             # Instalar dependencias
│   │
│   ├── deployment/                     # Scripts deployment
│   │   ├── deploy.sh                   # Deploy aplicación
│   │   ├── rollback.sh                 # Rollback deployment
│   │   └── health-check.sh             # Health check
│   │
│   ├── database/                       # Scripts base datos
│   │   ├── backup.sh                   # Backup BD
│   │   ├── restore.sh                  # Restore BD
│   │   └── migrate.sh                  # Ejecutar migraciones
│   │
│   └── testing/                        # Scripts testing
│       ├── run-tests.sh                # Ejecutar todos tests
│       ├── coverage.sh                 # Reporte cobertura
│       └── e2e-tests.sh                # Tests end-to-end
│
├── docker/                             # Configuración Docker
│   ├── docker-compose.yml              # Compose desarrollo
│   ├── docker-compose.prod.yml         # Compose producción
│   ├── docker-compose.test.yml         # Compose testing
│   │
│   ├── backend/                        # Docker backend
│   │   ├── Dockerfile                  # Dockerfile backend
│   │   ├── Dockerfile.prod             # Dockerfile producción
│   │   └── entrypoint.sh               # Entrypoint script
│   │
│   ├── frontend/                       # Docker frontend
│   │   ├── Dockerfile                  # Dockerfile frontend
│   │   ├── Dockerfile.prod             # Dockerfile producción
│   │   └── nginx.conf                  # Configuración Nginx
│   │
│   └── database/                       # Docker database
│       ├── init.sql                    # Script inicialización
│       └── postgres.conf               # Configuración PostgreSQL
│
├── infrastructure/                     # Infraestructura como código
│   ├── terraform/                      # Configuración Terraform
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   │
│   ├── kubernetes/                     # Manifiestos Kubernetes
│   │   ├── namespace.yaml
│   │   ├── deployments/
│   │   ├── services/
│   │   └── ingress/
│   │
│   └── monitoring/                     # Configuración monitoreo
│       ├── prometheus/
│       ├── grafana/
│       └── alerts/
│
└── tests/                              # Tests globales proyecto
    ├── integration/                    # Tests integración
    │   ├── test_api_sifen.py          # Test integración API-SIFEN
    │   └── test_full_workflow.py      # Test workflow completo
    │
    ├── performance/                    # Tests performance
    │   ├── load_tests.py              # Tests carga
    │   └── stress_tests.py            # Tests estrés
    │
    ├── security/                       # Tests seguridad
    │   ├── auth_tests.py              # Tests autenticación
    │   └── vulnerability_tests.py     # Tests vulnerabilidades
    │
    └── fixtures/                       # Fixtures globales
        ├── test_data.json             # Datos prueba
        ├── certificates/              # Certificados prueba
        └── responses/                 # Respuestas mock