# 📋 Sistema de Gestión de Documentos - Plan de Implementación

**Objetivo**: Implementar el sistema completo de gestión de documentos electrónicos SIFEN
**Estado Base**: ✅ Modelos base, empresa, user ya implementados
**Ubicación**: `backend/app/`
**Prioridad**: FASE 3 según hoja de ruta optimizada

---

## 🏗️ **Estructura de Archivos a Crear**

### **📁 Estado Actual (Ya Implementado)**
```
backend/app/
├── ✅ models/
│   ├── ✅ __init__.py
│   ├── ✅ base.py                          # BaseModel con timestamps
│   ├── ✅ user.py                          # Usuario del sistema
│   ├── ✅ empresa.py                       # Empresa/contribuyente emisor
│   ├── ✅ cliente.py                       # Clientes/receptores
│   ├── ✅ producto.py                      # Catálogo productos/servicios
│   ├── ✅ documento.py                     # Documentos electrónicos (padre)
│   ├── ✅ factura.py                       # Facturas específicas
│   └── ✅ timbrado.py                      # Gestión de timbrados
│
│
├── ✅ core/
│   ├── ✅ database.py                      # Conexión SQLAlchemy
│   ├── ✅ config.py                        # Configuración aplicación
│   ├── ✅ security.py                      # JWT, hashing, autenticación
│   ├── ✅ exceptions.py                    # Excepciones personalizadas
│   └── ✅ __init__.py
│
├── ✅ services/                            # Módulos SIFEN completados
│   ├── ✅ xml_generator/                   # Generación XML completa
│   ├── ✅ digital_sign/                    # Firma digital completa
│   ├── ✅ sifen_client/                    # Cliente SIFEN completo
│   └── ✅ pdf_generator/                   # Generación PDF completa
└── 🆕 utils/
    ├── ✅ __init__.py
    ├── ✅ ruc_utils.py          # Validación RUC + DV Paraguay
    ├── ✅ cdc/                  # Generador CDC (44 dígitos)
    │   ├── __init__.py          # Punto de entrada público
    │   ├── types.py             # Enums y clases de datos
    │   ├── generator.py         # Generación de CDC
    │   ├── validator.py         # Validación de CDC
    │   ├── components.py        # Extracción y manejo de componentes
    │   ├── utils.py             # Utilidades y formateo
    │   └── testing.py           # Funciones de testing y debugging
    ├── ✅ date_utils.py         # Utilidades fechas Paraguay
    └── ✅ constants.py          # Constantes SIFEN
│
└── ✅ main.py                              # FastAPI base con /health
```

### **🆕 Archivos a Implementar**



#### **🟡 PRIORIDAD 2 - DTOs y Validación (Semana 2)**
```
backend/app/
├── 🆕 schemas/                             # DTOs Pydantic
│   ├── 🟡 __init__.py
│   ├── 🟡 user.py                         # DTOs usuario
│   ├── 🟡 empresa.py                      # DTOs empresa
│   ├── 🟡 cliente.py                      # DTOs cliente
│   ├── 🟡 producto.py                     # DTOs producto
│   ├── 🟡 factura.py                      # DTOs factura
│   ├── 🟡 documento.py                    # DTOs documento
│   └── 🟡 common.py                       # DTOs comunes (paginación, etc.)
```

#### **🟢 PRIORIDAD 3 - Repositories (Semana 2-3)**
```
backend/app/
├── 🆕 repositories/                        # Acceso a datos
│   ├── 🟢 __init__.py
│   ├── 🟢 base.py                         # Repository base genérico
│   ├── 🟢 user_repository.py              # CRUD usuario
│   ├── 🟢 empresa_repository.py           # CRUD empresa
│   ├── 🟢 cliente_repository.py           # CRUD cliente
│   ├── 🟢 producto_repository.py          # CRUD producto
│   ├── 🟢 factura_repository.py           # CRUD factura
│   └── 🟢 documento_repository.py         # CRUD documento
```

#### **🔵 PRIORIDAD 4 - APIs REST (Semana 3-4)**
```
backend/app/
├── 🆕 api/                                # Endpoints REST
│   ├── 🔵 __init__.py
│   ├── 🔵 dependencies.py                 # Dependencias comunes (auth, db)
│   └── 🔵 v1/                             # Versión 1 de la API
│       ├── 🔵 __init__.py
│       ├── 🔵 router.py                   # Router principal v1
│       ├── 🔵 auth.py                     # Autenticación JWT
│       ├── 🔵 empresas.py                 # CRUD empresas
│       ├── 🔵 clientes.py                 # CRUD clientes
│       ├── 🔵 productos.py                # CRUD productos
│       ├── 🔵 facturas.py                 # CRUD facturas + envío SIFEN
│       └── 🔵 consultas.py                # Consultas RUC, estados
```

#### **⚪ PRIORIDAD 5 - Servicios de Negocio (Semana 4-5)**
```
backend/app/
├── 🆕 services/
│   └── 🆕 business/                       # Lógica de negocio
│       ├── ⚪ __init__.py
│       ├── ⚪ factura_service.py          # Orquestador facturas
│       ├── ⚪ sifen_service.py            # Orquestador SIFEN
│       ├── ⚪ validation_service.py       # Validaciones de negocio
│       └── ⚪ numbering_service.py        # Numeración automática
```

---

## 🎯 **Plan de Prioridades por Semana**

### **📅 Semana 2 - Validación y DTOs**
| Orden | Archivo | Propósito | Dependencias |
|-------|---------|-----------|--------------|
| 1 | `schemas/common.py` | DTOs comunes | Ninguna |
| 2 | `schemas/cliente.py` | DTOs cliente | common.py |
| 3 | `schemas/producto.py` | DTOs producto | common.py |
| 4 | `schemas/factura.py` | DTOs factura | cliente.py, producto.py |
| 5 | `repositories/base.py` | Repository base | models/ |
| 6 | `repositories/cliente_repository.py` | CRUD cliente | base.py |
| 7 | `repositories/factura_repository.py` | CRUD factura | base.py |

### **📅 Semana 3 - APIs Básicas**
| Orden | Archivo | Propósito | Dependencias |
|-------|---------|-----------|--------------|
| 1 | `api/dependencies.py` | Dependencias auth/db | security.py |
| 2 | `api/v1/auth.py` | Endpoints autenticación | dependencies.py |
| 3 | `api/v1/clientes.py` | CRUD clientes | repositories/, schemas/ |
| 4 | `api/v1/productos.py` | CRUD productos | repositories/, schemas/ |
| 5 | `api/v1/facturas.py` | CRUD facturas básico | repositories/, schemas/ |
| 6 | `api/v1/router.py` | Router principal | todos los endpoints |

### **📅 Semana 4 - Integración SIFEN**
| Orden | Archivo | Propósito | Dependencias |
|-------|---------|-----------|--------------|
| 1 | `services/business/factura_service.py` | Orquestador facturas | xml_generator/, digital_sign/ |
| 2 | `services/business/sifen_service.py` | Orquestador SIFEN | sifen_client/ |
| 3 | Actualizar `api/v1/facturas.py` | Endpoints envío SIFEN | business/ |
| 4 | `api/v1/consultas.py` | Consultas RUC/estados | sifen_client/ |

### **📅 Semana 5 - Refinamiento**
| Orden | Archivo | Propósito | Dependencias |
|-------|---------|-----------|--------------|
| 1 | `services/business/validation_service.py` | Validaciones negocio | Todos |
| 2 | `services/business/numbering_service.py` | Numeración automática | utils/ |
| 3 | Tests de integración | Validar flujo completo | Todos |
| 4 | Documentación | README.md por módulo | Todos |

---

## 🎯 **Criterios de Completitud por Archivo**

### **🔴 Prioridad 1 - Archivos Críticos**
Cada archivo debe cumplir:
- ✅ Implementación funcional completa
- ✅ Validaciones básicas
- ✅ Manejo de errores
- ✅ Tests unitarios >80% cobertura
- ✅ Documentación con docstrings

### **🟡 Prioridad 2 - Archivos Importantes**
Cada archivo debe cumplir:
- ✅ DTOs completos con validación Pydantic
- ✅ Ejemplos de uso
- ✅ Tests de validación
- ✅ Documentación

### **🟢 Prioridad 3 - Archivos Soporte**
Cada archivo debe cumplir:
- ✅ CRUD operations completas
- ✅ Manejo de excepciones
- ✅ Tests de repository
- ✅ Documentación

### **🔵 Prioridad 4 - APIs**
Cada archivo debe cumplir:
- ✅ Endpoints REST completos
- ✅ Autenticación implementada
- ✅ Validación de entrada
- ✅ Tests de endpoints
- ✅ Documentación OpenAPI

### **⚪ Prioridad 5 - Servicios**
Cada archivo debe cumplir:
- ✅ Lógica de negocio completa
- ✅ Integración con módulos SIFEN
- ✅ Manejo de errores robustos
- ✅ Tests de integración
- ✅ Documentación de flujos

---

## 🚀 **Resultado Final Esperado**

Al completar esta implementación tendrás:

### **📊 Base de Datos Completa**
- ✅ Modelos para todos los documentos SIFEN
- ✅ Relaciones correctas entre entidades
- ✅ Validaciones a nivel de BD

### **🌐 API REST Funcional**
- ✅ CRUD completo para todas las entidades
- ✅ Autenticación JWT
- ✅ Documentación automática (Swagger)

### **⚙️ Integración SIFEN**
- ✅ Flujo completo: Crear → XML → Firmar → SIFEN
- ✅ Consultas RUC automáticas
- ✅ Manejo de estados de documentos

### **🔄 Servicios de Negocio**
- ✅ Orquestación de módulos existentes
- ✅ Validaciones de negocio Paraguay
- ✅ Numeración automática

---

## 🏃‍♂️ **Comando para Iniciar**

```bash
# Primer archivo a implementar
touch backend/app/utils/constants.py
echo "# Constantes SIFEN Paraguay" > backend/app/utils/constants.py

# Continuar según orden de prioridades
```

---

**Versión**: 1.0  
**Próxima revisión**: Al completar Prioridad 1  
**Objetivo**: Sistema funcional de gestión de documentos en 5 semanas