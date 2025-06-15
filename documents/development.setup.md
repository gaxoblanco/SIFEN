# Guía de Configuración de Desarrollo - SIFEN

## Resumen Ejecutivo

Guía unificada para configurar el ambiente de desarrollo del proyecto SIFEN. Incluye todos los módulos, servicios y herramientas necesarias para desarrollo local eficiente.

## Índice

1. [Pre-requisitos](#pre-requisitos)
2. [Configuración Inicial](#configuración-inicial)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [Base de Datos](#base-de-datos)
6. [Docker Setup](#docker-setup)
7. [Certificados y Firma Digital](#certificados-y-firma-digital)
8. [Testing Setup](#testing-setup)
9. [Scripts de Automatización](#scripts-de-automatización)
10. [Validación del Setup](#validación-del-setup)
11. [Troubleshooting](#troubleshooting)

---

## Pre-requisitos

### Software Base Requerido

```bash
# 1. Python 3.9+ 
python --version  # Debe ser >= 3.9

# 2. Node.js 18+ (para frontend)
node --version    # Debe ser >= 18
npm --version

# 3. Git
git --version

# 4. Docker y Docker Compose (recomendado)
docker --version
docker-compose --version

# 5. PostgreSQL (local o Docker)
psql --version    # Opcional si usas Docker
```

### Variables de Sistema

```bash
# Linux/Mac - Agregar a ~/.bashrc o ~/.zshrc
export SIFEN_PROJECT_ROOT="/path/to/sifen-facturacion"
export PATH="$PATH:$SIFEN_PROJECT_ROOT/scripts"

# Windows - Variables de entorno del sistema
SIFEN_PROJECT_ROOT=C:\path\to\sifen-facturacion
```

---

## Configuración Inicial

### 1. Clonar y Estructura Base

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/sifen-facturacion.git
cd sifen-facturacion

# Verificar estructura (debe coincidir con architecture.md)
tree -L 3
```

### 2. Variables de Entorno

```bash
# Copiar plantilla de variables
cp .env.example .env

# Editar variables principales
nano .env
```

**Contenido del archivo `.env`:**
```bash
# === CONFIGURACIÓN GENERAL ===
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# === BASE DE DATOS ===
DATABASE_URL=postgresql://sifen_user:sifen_password@localhost:5432/sifen_dev
POSTGRES_USER=sifen_user
POSTGRES_PASSWORD=sifen_password
POSTGRES_DB=sifen_dev
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# === BACKEND ===
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
SECRET_KEY=tu-secret-key-super-segura-para-desarrollo

# === SIFEN INTEGRATION ===
SIFEN_ENVIRONMENT=test
SIFEN_TEST_URL=https://sifen-test.set.gov.py
SIFEN_PROD_URL=https://sifen.set.gov.py

# === CERTIFICADOS (ver certificate_setup.md) ===
SIFEN_CERT_PATH=./certificates/test/dev_cert.p12
SIFEN_CERT_PASSWORD=dev123

# === FRONTEND ===
FRONTEND_PORT=3000
REACT_APP_API_URL=http://localhost:8000

# === REDIS (para queues) ===
REDIS_URL=redis://localhost:6379/0

# === MONITORING ===
SENTRY_DSN=  # Opcional para desarrollo
```

---

## Backend Setup

### 1. Ambiente Virtual Python

```bash
# Crear y activar virtual environment
cd backend
python -m venv venv

# Activar (Linux/Mac)
source venv/bin/activate

# Activar (Windows)
venv\Scripts\activate

# Verificar activación - debe mostrar (venv) en prompt
which python  # Debe apuntar al venv
```

### 2. Dependencias Backend

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Generar requirements actualizados
pip freeze > requirements.txt
```

**Dependencias principales (requirements-dev.txt):**
```txt
# === FRAMEWORK ===
fastapi>=0.104.0
uvicorn[standard]>=0.24.0

# === BASE DE DATOS ===
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.0

# === AUTENTICACIÓN ===
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# === VALIDACIÓN ===
pydantic>=2.5.0
pydantic-settings>=2.1.0

# === XML Y FIRMA DIGITAL ===
lxml>=4.9.0
cryptography>=41.0.0
pyOpenSSL>=23.0.0

# === REQUESTS Y SOAP ===
requests>=2.31.0
zeep>=4.2.1

# === PDF GENERATION ===
reportlab>=4.0.0
weasyprint>=60.0

# === TESTING ===
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0

# === DESARROLLO ===
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
mypy>=1.7.0

# === MONITORING ===
structlog>=23.0.0
```

### 3. Configuración Database

```bash
# Inicializar Alembic
alembic init alembic

# Editar alembic.ini
# Cambiar: sqlalchemy.url = postgresql://user:pass@localhost/dbname
```

### 4. Estructura de Módulos

```bash
# Crear estructura de servicios modulares
mkdir -p app/services/{xml_generator,digital_sign,sifen_client,pdf_generator,validators}

# Cada servicio debe tener:
for service in xml_generator digital_sign sifen_client pdf_generator validators; do
    mkdir -p app/services/$service/{tests,examples}
    touch app/services/$service/{__init__.py,README.md}
done
```

---

## Frontend Setup

### 1. Instalación Node.js

```bash
cd frontend

# Instalar dependencias
npm install

# O con yarn
yarn install
```

### 2. Dependencias Frontend

**package.json principales:**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0",
    "@headlessui/react": "^1.7.0",
    "@heroicons/react": "^2.0.0",
    "tailwindcss": "^3.3.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.1.0",
    "typescript": "^5.2.0",
    "vite": "^5.0.0"
  }
}
```

---

## Base de Datos

### Opción A: PostgreSQL Local

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql

# Crear usuario y base de datos
sudo -u postgres psql
CREATE USER sifen_user WITH PASSWORD 'sifen_password';
CREATE DATABASE sifen_dev OWNER sifen_user;
GRANT ALL PRIVILEGES ON DATABASE sifen_dev TO sifen_user;
\q
```

### Opción B: PostgreSQL con Docker (Recomendado)

```bash
# Solo PostgreSQL para desarrollo
docker run --name sifen-postgres \
  -e POSTGRES_USER=sifen_user \
  -e POSTGRES_PASSWORD=sifen_password \
  -e POSTGRES_DB=sifen_dev \
  -p 5432:5432 \
  -v sifen_postgres_data:/var/lib/postgresql/data \
  -d postgres:15

# Verificar conexión
docker exec -it sifen-postgres psql -U sifen_user -d sifen_dev
```

---

## Docker Setup

### 1. Docker Compose para Desarrollo

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: sifen-postgres
    environment:
      POSTGRES_USER: sifen_user
      POSTGRES_PASSWORD: sifen_password
      POSTGRES_DB: sifen_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - sifen-network

  redis:
    image: redis:7-alpine
    container_name: sifen-redis
    ports:
      - "6379:6379"
    networks:
      - sifen-network

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: sifen-backend
    environment:
      - DATABASE_URL=postgresql://sifen_user:sifen_password@postgres:5432/sifen_dev
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./certificates:/app/certificates
    depends_on:
      - postgres
      - redis
    networks:
      - sifen-network

volumes:
  postgres_data:

networks:
  sifen-network:
    driver: bridge
```

### 2. Dockerfile Backend

**backend/Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copiar código
COPY . .

# Crear directorios necesarios
RUN mkdir -p certificates logs

# Comando por defecto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

---

## Certificados y Firma Digital

### 1. Setup Certificados de Desarrollo

```bash
# Generar certificado de prueba
python -c "
from backend.app.services.digital_sign.examples.generate_test_cert import generate_test_certificate
generate_test_certificate(
    './certificates/test/dev_cert.p12',
    'dev123',
    'CN=Desarrollo SIFEN,O=Tu Empresa,C=PY',
    '12345678'
)
"
```

### 2. Validar Configuración

```bash
# Test de firma básica
python -m backend.app.services.digital_sign.tests.test_basic_signing
```

---

## Testing Setup

### 1. Configuración Pytest

**backend/pytest.ini:**
```ini
[tool:pytest]
testpaths = app/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --asyncio-mode=auto
filterwarnings =
    ignore::DeprecationWarning
```

### 2. Estructura de Tests

```bash
# Crear estructura de tests por módulo
for module in xml_generator digital_sign sifen_client pdf_generator; do
    mkdir -p backend/app/services/$module/tests
    touch backend/app/services/$module/tests/{__init__.py,test_${module}.py,conftest.py}
done
```

---

## Scripts de Automatización

### 1. Makefile Principal

**Makefile:**
```makefile
.PHONY: help install dev test lint clean docker-up docker-down

help:  ## Mostrar ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Instalar dependencias completas
	@echo "🚀 Instalando dependencias..."
	cd backend && pip install -r requirements-dev.txt
	cd frontend && npm install

dev:  ## Iniciar desarrollo completo
	@echo "🔧 Iniciando ambiente de desarrollo..."
	docker-compose up -d postgres redis
	cd backend && source venv/bin/activate && uvicorn app.main:app --reload &
	cd frontend && npm run dev

test:  ## Ejecutar todos los tests
	@echo "🧪 Ejecutando tests..."
	cd backend && python -m pytest
	cd frontend && npm run test

lint:  ## Linter y formato
	@echo "🧹 Ejecutando linters..."
	cd backend && black . && flake8 . && isort .
	cd frontend && npm run lint

clean:  ## Limpiar archivos temporales
	@echo "🧹 Limpiando..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	cd frontend && rm -rf node_modules/.cache

docker-up:  ## Levantar servicios Docker
	docker-compose up -d

docker-down:  ## Bajar servicios Docker
	docker-compose down

setup-dev:  ## Setup completo de desarrollo
	@echo "🔧 Configurando ambiente de desarrollo..."
	cp .env.example .env
	cd backend && python -m venv venv
	make install
	make docker-up
	sleep 5
	cd backend && source venv/bin/activate && alembic upgrade head
	@echo "✅ Setup completo!"
```

### 2. Scripts Específicos

**scripts/setup-dev.sh:**
```bash
#!/bin/bash
set -e

echo "🚀 Configurando ambiente de desarrollo SIFEN..."

# Verificar pre-requisitos
echo "📋 Verificando pre-requisitos..."
python --version || { echo "❌ Python no encontrado"; exit 1; }
node --version || { echo "❌ Node.js no encontrado"; exit 1; }
docker --version || { echo "❌ Docker no encontrado"; exit 1; }

# Setup backend
echo "🐍 Configurando backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt

# Setup frontend
echo "⚛️ Configurando frontend..."
cd ../frontend
npm install

# Setup base de datos
echo "🗄️ Configurando base de datos..."
cd ..
docker-compose up -d postgres redis
sleep 10

# Migraciones
echo "📊 Ejecutando migraciones..."
cd backend
source venv/bin/activate
alembic upgrade head

# Certificados de desarrollo
echo "🔐 Configurando certificados..."
python -c "
from app.services.digital_sign.examples.generate_test_cert import generate_test_certificate
generate_test_certificate('./certificates/test/dev_cert.p12', 'dev123', 'CN=Test,C=PY', '12345678')
"

echo "✅ Setup de desarrollo completado!"
echo "🏃 Para iniciar: make dev"
```

---

## Validación del Setup

### 1. Checklist de Validación

```bash
# Backend Health Check
curl http://localhost:8000/health

# Database Connection
cd backend && python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('✅ Database OK')
"

# Frontend Build
cd frontend && npm run build

# Tests básicos
cd backend && python -m pytest app/tests/ -v

# Certificados
ls -la certificates/test/
```

### 2. Script de Validación Automática

**scripts/validate-setup.sh:**
```bash
#!/bin/bash

echo "🔍 Validando configuración de desarrollo..."

# Verificar servicios Docker
echo "📦 Verificando servicios Docker..."
docker-compose ps | grep -q "Up" && echo "✅ Docker services running" || echo "❌ Docker services down"

# Verificar backend
echo "🐍 Verificando backend..."
curl -s http://localhost:8000/health | grep -q "ok" && echo "✅ Backend OK" || echo "❌ Backend down"

# Verificar frontend
echo "⚛️ Verificando frontend..."
curl -s http://localhost:3000 | grep -q "React" && echo "✅ Frontend OK" || echo "❌ Frontend down"

# Verificar base de datos
echo "🗄️ Verificando base de datos..."
cd backend && python -c "
try:
    from app.core.database import engine
    engine.connect()
    print('✅ Database connection OK')
except Exception as e:
    print(f'❌ Database error: {e}')
"

echo "🎉 Validación completa!"
```

---

## Troubleshooting

### Problemas Comunes

#### 1. Error de Puerto Ocupado
```bash
# Verificar qué proceso usa el puerto
lsof -i :8000
lsof -i :3000

# Terminar proceso
kill -9 <PID>
```

#### 2. Error de Dependencias Python
```bash
# Limpiar e reinstalar
cd backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

#### 3. Error de Docker
```bash
# Reset completo Docker
docker-compose down -v
docker system prune -a
docker-compose up -d
```

#### 4. Error de Base de Datos
```bash
# Reset PostgreSQL data
docker-compose down
docker volume rm sifen-facturacion_postgres_data
docker-compose up -d postgres
```

### Logs y Debugging

```bash
# Ver logs backend
tail -f backend/logs/app.log

# Ver logs Docker
docker-compose logs -f backend

# Debug modo interactivo
cd backend
source venv/bin/activate
python -m pdb app/main.py
```

---

## Comandos de Desarrollo Diario

```bash
# Iniciar día de desarrollo
make docker-up
make dev

# Ejecutar tests después de cambios
make test

# Lint antes de commit
make lint

# Fin del día
docker-compose down
```

## Próximos Pasos

Una vez completado este setup:

1. 📖 Revisar `manual_tecnico_v150.md` para entender SIFEN
2. 🏗️ Seguir `hoja_de_ruta_optimizada.md` para desarrollo
3. 🔍 Usar `quick_reference.md` para consultas rápidas
4. 🧪 Ejecutar tests modulares continuamente

**¡Tu ambiente de desarrollo está listo para SIFEN! 🎉**