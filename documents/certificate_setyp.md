# Configuración de Certificados Digitales PSC - SIFEN

## 📋 **Introducción a Certificados PSC**

Los **Proveedores de Servicios de Certificación (PSC)** en Paraguay emiten certificados digitales obligatorios para SIFEN. Este documento cubre la configuración completa desde la obtención hasta la implementación.

### **PSC Autorizados en Paraguay**
- **eKuatia** (SET - Gobierno)
- **Certified SA**
- **Paraguay Seguro**
- **Otros autorizados por MIC**

## 🏆 **Tipos de Certificados**

### **Certificados por Persona**
| Tipo | Descripción | Uso SIFEN | Ubicación RUC |
|------|-------------|-----------|---------------|
| **F1** | Persona Física | ✅ Permitido | SubjectAlternativeName |
| **F2** | Persona Jurídica | ✅ Permitido | SerialNumber |
| **F3** | Representante Legal | ✅ Permitido | SerialNumber |

### **Características Técnicas**
```
Formato: PKCS#12 (.p12/.pfx)
Algoritmo: RSA 2048 bits mínimo
Hash: SHA-256
Vigencia: 1-3 años
Key Usage: Digital Signature + Non Repudiation
```

## 🚀 **Proceso de Obtención**

### **1. Solicitud del Certificado**

#### **Para Persona Física (F1)**
```bash
# Documentos requeridos
- Cédula de Identidad vigente
- Formulario de solicitud PSC
- Comprobante de pago
- Presencia física para verificación
```

#### **Para Persona Jurídica (F2)**
```bash
# Documentos requeridos
- RUC activo de la empresa
- Estatutos sociales
- Poder del representante legal
- Cédula del representante
- Formulario de solicitud PSC
- Comprobante de pago
```

### **2. Proceso de Verificación**
1. **Validación documentos** (1-3 días hábiles)
2. **Verificación identidad** (presencial o video llamada)
3. **Generación del certificado** (1-5 días)
4. **Entrega** (email + portal PSC)

### **3. Costos Aproximados** *(Verificar con PSC)*
| PSC | F1 (Persona Física) | F2 (Persona Jurídica) | Vigencia |
|-----|--------------------|-----------------------|----------|
| **eKuatia** | Gs. 150,000 | Gs. 200,000 | 2 años |
| **Certified** | Gs. 180,000 | Gs. 250,000 | 1-2 años |
| **Paraguay Seguro** | Consultar | Consultar | 1-3 años |

## 💻 **Instalación y Configuración**

### **Estructura de Archivos Recomendada**
```
proyecto/
├── certificates/
│   ├── production/
│   │   ├── empresa_prod.p12        # Certificado producción
│   │   └── backup_prod.p12         # Backup certificado
│   ├── test/
│   │   ├── empresa_test.p12        # Certificado test
│   │   └── sifen_test.p12          # Certificado SET test
│   └── README.md                   # Documentación certificados
├── .env                            # Variables de entorno
├── .env.example                    # Ejemplo de configuración
└── .gitignore                      # NUNCA commitear certificados
```

### **Variables de Entorno**

#### **.env.example**
```bash
# ================================================
# CONFIGURACIÓN CERTIFICADOS DIGITALES PSC
# ================================================

# Ambiente de ejecución
SIFEN_ENVIRONMENT=test  # test | production

# Certificados de Producción
SIFEN_PROD_CERT_PATH=./certificates/production/empresa_prod.p12
SIFEN_PROD_CERT_PASSWORD=contraseña_super_segura_produccion

# Certificados de Test/Desarrollo  
SIFEN_TEST_CERT_PATH=./certificates/test/empresa_test.p12
SIFEN_TEST_CERT_PASSWORD=contraseña_desarrollo

# Certificado SET (para testing)
SIFEN_SET_TEST_CERT_PATH=./certificates/test/sifen_test.p12
SIFEN_SET_TEST_CERT_PASSWORD=test123

# URLs SIFEN
SIFEN_PROD_BASE_URL=https://sifen.set.gov.py
SIFEN_TEST_BASE_URL=https://sifen-test.set.gov.py

# Configuración SSL/TLS
SIFEN_VERIFY_SSL=true
SIFEN_TLS_VERSION=1.2

# Configuración de timeouts (segundos)
SIFEN_CONNECT_TIMEOUT=10
SIFEN_READ_TIMEOUT=60
SIFEN_TOTAL_TIMEOUT=120

# Logging
SIFEN_LOG_LEVEL=INFO
SIFEN_LOG_CERT_INFO=true
SIFEN_LOG_REQUESTS=false  # Solo en desarrollo
```

#### **.env (crear y no commitear)**
```bash
# Copiar de .env.example y completar con valores reales
cp .env.example .env

# Editar con valores reales
nano .env
```

### **Configuración de Seguridad**

#### **.gitignore** (Crítico)
```gitignore
# ================================================
# CERTIFICADOS Y CREDENCIALES - NUNCA COMMITEAR
# ================================================

# Certificados
*.p12
*.pfx
*.pem
*.key
*.crt

# Archivos de configuración con secretos
.env
.env.local
.env.production

# Carpetas de certificados
certificates/production/
certificates/backup/
keys/
secrets/

# Logs que pueden contener información sensible
logs/sifen_*.log
*.log

# Backups que pueden contener certificados
backup_*.zip
backup_*.tar.gz
```

## 🔧 **Configuración por Ambiente**

### **Ambiente de Desarrollo**

#### **1. Certificado de Prueba Automático**
```python
# Generar certificado de prueba
from backend.app.services.digital_sign.examples.generate_test_cert import generate_test_certificate

def setup_development_certificate():
    """Configurar certificado para desarrollo"""
    
    cert_path = "./certificates/test/dev_cert.p12"
    cert_password = "dev123"
    
    # Generar si no existe
    if not os.path.exists(cert_path):
        print("Generando certificado de desarrollo...")
        generate_test_certificate(
            output_path=cert_path,
            password=cert_password,
            subject_name="CN=Desarrollo SIFEN,O=Tu Empresa,C=PY",
            ruc="12345678"  # RUC de prueba
        )
        print(f"✅ Certificado generado: {cert_path}")
    
    return cert_path, cert_password
```

#### **2. Configuración Automática**
```python
# backend/app/core/config.py
import os
from pathlib import Path

class DevelopmentConfig:
    """Configuración para desarrollo"""
    
    def __init__(self):
        self.setup_development_environment()
    
    def setup_development_environment(self):
        """Setup automático para desarrollo"""
        
        # Crear directorios necesarios
        os.makedirs("./certificates/test", exist_ok=True)
        os.makedirs("./logs", exist_ok=True)
        
        # Verificar certificado de desarrollo
        cert_path = "./certificates/test/dev_cert.p12"
        if not os.path.exists(cert_path):
            print("⚠️  Certificado de desarrollo no encontrado")
            print("Ejecutar: python -m backend.app.services.digital_sign.examples.generate_test_cert")
        
        # Configurar variables de entorno por defecto
        os.environ.setdefault('SIFEN_ENVIRONMENT', 'test')
        os.environ.setdefault('SIFEN_TEST_CERT_PATH', cert_path)
        os.environ.setdefault('SIFEN_TEST_CERT_PASSWORD', 'dev123')
```

### **Ambiente de Test/Staging**

#### **1. Certificado SET Oficial**
```bash
# Descargar certificado de prueba oficial de SET
wget https://sifen-test.set.gov.py/certificates/test_cert.p12
mv test_cert.p12 ./certificates/test/sifen_test.p12

# O usar certificado PSC de test
# (Solicitar a tu PSC un certificado específico para testing)
```

#### **2. Configuración Test**
```python
# backend/app/core/config.py
class TestConfig:
    """Configuración para ambiente de test"""
    
    SIFEN_ENVIRONMENT = "test"
    SIFEN_BASE_URL = "https://sifen-test.set.gov.py"
    
    # Certificado de test
    SIFEN_CERT_PATH = os.getenv(
        'SIFEN_TEST_CERT_PATH', 
        './certificates/test/sifen_test.p12'
    )
    SIFEN_CERT_PASSWORD = os.getenv('SIFEN_TEST_CERT_PASSWORD', 'test123')
    
    # Configuración más permisiva para testing
    SIFEN_VERIFY_SSL = True
    SIFEN_TIMEOUT = 30
    SIFEN_MAX_RETRIES = 1
```

### **Ambiente de Producción**

#### **1. Certificado PSC Real**
```bash
# NUNCA usar certificados de prueba en producción
# Debe ser certificado PSC válido con RUC real de la empresa

# Ubicación segura
sudo mkdir -p /etc/ssl/sifen/
sudo cp empresa_prod.p12 /etc/ssl/sifen/
sudo chown root:root /etc/ssl/sifen/empresa_prod.p12
sudo chmod 600 /etc/ssl/sifen/empresa_prod.p12
```

#### **2. Configuración Producción**
```python
# backend/app/core/config.py
class ProductionConfig:
    """Configuración para producción"""
    
    SIFEN_ENVIRONMENT = "production"
    SIFEN_BASE_URL = "https://sifen.set.gov.py"
    
    # Certificado de producción (ubicación segura)
    SIFEN_CERT_PATH = os.getenv(
        'SIFEN_PROD_CERT_PATH',
        '/etc/ssl/sifen/empresa_prod.p12'
    )
    SIFEN_CERT_PASSWORD = os.getenv('SIFEN_PROD_CERT_PASSWORD')
    
    # Configuración estricta para producción
    SIFEN_VERIFY_SSL = True
    SIFEN_TIMEOUT = 60
    SIFEN_MAX_RETRIES = 3
    SIFEN_LOG_REQUESTS = False  # Por seguridad
    
    def __post_init__(self):
        # Validaciones críticas
        if not self.SIFEN_CERT_PASSWORD:
            raise ValueError("SIFEN_PROD_CERT_PASSWORD es obligatorio en producción")
        
        if not os.path.exists(self.SIFEN_CERT_PATH):
            raise ValueError(f"Certificado no encontrado: {self.SIFEN_CERT_PATH}")
```

## 🔐 **Validación de Certificados**

### **Script de Validación**
```python
#!/usr/bin/env python3
"""
Script de validación de certificados PSC para SIFEN
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

def validate_psc_certificate(cert_path: str, password: str) -> dict:
    """Validar certificado PSC para SIFEN"""
    
    results = {
        'valid': False,
        'errors': [],
        'warnings': [],
        'info': {}
    }
    
    try:
        # 1. Verificar archivo existe
        if not os.path.exists(cert_path):
            results['errors'].append(f"Archivo no encontrado: {cert_path}")
            return results
        
        # 2. Cargar certificado
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        
        try:
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                cert_data, password.encode('utf-8')
            )
        except Exception as e:
            results['errors'].append(f"Error cargando certificado: {e}")
            return results
        
        # 3. Información básica
        subject = certificate.subject
        issuer = certificate.issuer
        
        results['info'].update({
            'subject': str(subject),
            'issuer': str(issuer),
            'serial_number': str(certificate.serial_number),
            'not_valid_before': certificate.not_valid_before.isoformat(),
            'not_valid_after': certificate.not_valid_after.isoformat()
        })
        
        # 4. Verificar vigencia
        now = datetime.now()
        if certificate.not_valid_before > now:
            results['errors'].append("Certificado aún no es válido")
        elif certificate.not_valid_after < now:
            results['errors'].append("Certificado expirado")
        elif certificate.not_valid_after < (now + timedelta(days=30)):
            results['warnings'].append("Certificado expira en menos de 30 días")
        
        # 5. Verificar Key Usage
        try:
            key_usage = certificate.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.KEY_USAGE
            ).value
            
            if not key_usage.digital_signature:
                results['errors'].append("Key Usage no incluye Digital Signature")
            
            if not key_usage.content_commitment:
                results['errors'].append("Key Usage no incluye Non Repudiation")
                
        except x509.ExtensionNotFound:
            results['errors'].append("Extensión Key Usage no encontrada")
        
        # 6. Extraer RUC
        ruc = extract_ruc_from_certificate(certificate)
        if ruc:
            results['info']['ruc'] = ruc
        else:
            results['warnings'].append("No se pudo extraer RUC del certificado")
        
        # 7. Verificar PSC
        psc_name = extract_psc_name(issuer)
        results['info']['psc'] = psc_name
        
        if not is_authorized_psc(psc_name):
            results['warnings'].append(f"PSC no reconocido: {psc_name}")
        
        # 8. Verificar algoritmos
        if certificate.signature_algorithm_oid.dotted_string not in [
            '1.2.840.113549.1.1.11',  # SHA256WithRSAEncryption
            '1.2.840.113549.1.1.12',  # SHA384WithRSAEncryption  
            '1.2.840.113549.1.1.13'   # SHA512WithRSAEncryption
        ]:
            results['warnings'].append("Algoritmo de firma no recomendado")
        
        # 9. Verificar tamaño de clave
        public_key = certificate.public_key()
        key_size = public_key.key_size
        
        if key_size < 2048:
            results['errors'].append(f"Tamaño de clave insuficiente: {key_size} bits")
        elif key_size < 4096:
            results['warnings'].append(f"Considerar clave más grande: {key_size} bits")
        
        results['info']['key_size'] = key_size
        
        # 10. Resultado final
        results['valid'] = len(results['errors']) == 0
        
    except Exception as e:
        results['errors'].append(f"Error inesperado: {e}")
    
    return results

def extract_ruc_from_certificate(certificate) -> str:
    """Extraer RUC del certificado según estándar PSC Paraguay"""
    
    # Método 1: SerialNumber (Persona Jurídica)
    try:
        serial_attrs = certificate.subject.get_attributes_for_oid(
            x509.oid.NameOID.SERIAL_NUMBER
        )
        if serial_attrs:
            serial = serial_attrs[0].value
            # Buscar patrón RUC en serial number
            if len(serial) >= 8 and serial.replace('-', '').isdigit():
                return serial.replace('-', '')[:8]
    except:
        pass
    
    # Método 2: SubjectAlternativeName (Persona Física)
    try:
        san_extension = certificate.extensions.get_extension_for_oid(
            x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        )
        
        for san in san_extension.value:
            if isinstance(san, x509.OtherName):
                # OID específico para RUC en Paraguay
                if san.type_id.dotted_string in ['1.3.6.1.4.1.30.1', '2.16.858.1.1.1']:
                    try:
                        ruc_value = san.value.decode('utf-8')
                        if len(ruc_value) >= 8 and ruc_value.replace('-', '').isdigit():
                            return ruc_value.replace('-', '')[:8]
                    except:
                        pass
    except:
        pass
    
    return None

def extract_psc_name(issuer) -> str:
    """Extraer nombre del PSC del issuer"""
    
    try:
        org_attrs = issuer.get_attributes_for_oid(x509.oid.NameOID.ORGANIZATION_NAME)
        if org_attrs:
            return org_attrs[0].value
    except:
        pass
    
    try:
        cn_attrs = issuer.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
        if cn_attrs:
            return cn_attrs[0].value
    except:
        pass
    
    return "Desconocido"

def is_authorized_psc(psc_name: str) -> bool:
    """Verificar si el PSC está autorizado"""
    
    authorized_pscs = [
        'eKuatia',
        'Paraguay Seguro',
        'Certified',
        'SET',
        'Subsecretaría de Estado de Tributación'
    ]
    
    return any(authorized in psc_name for authorized in authorized_pscs)

def main():
    """Función principal del validador"""
    
    if len(sys.argv) < 3:
        print("Uso: python validate_cert.py <path_certificado> <password>")
        sys.exit(1)
    
    cert_path = sys.argv[1]
    password = sys.argv[2]
    
    print(f"🔍 Validando certificado: {cert_path}")
    print("=" * 60)
    
    results = validate_psc_certificate(cert_path, password)
    
    # Mostrar información
    if results['info']:
        print("\n📋 INFORMACIÓN DEL CERTIFICADO:")
        for key, value in results['info'].items():
            print(f"   {key.replace('_', ' ').title()}: {value}")
    
    # Mostrar warnings
    if results['warnings']:
        print("\n⚠️  ADVERTENCIAS:")
        for warning in results['warnings']:
            print(f"   • {warning}")
    
    # Mostrar errores
    if results['errors']:
        print("\n❌ ERRORES:")
        for error in results['errors']:
            print(f"   • {error}")
    
    # Resultado final
    print("\n" + "=" * 60)
    if results['valid']:
        print("✅ CERTIFICADO VÁLIDO PARA SIFEN")
    else:
        print("❌ CERTIFICADO NO VÁLIDO")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### **Uso del Validador**
```bash
# Hacer ejecutable
chmod +x validate_cert.py

# Validar certificado
python validate_cert.py ./certificates/production/empresa.p12 mi_password

# Ejemplo de salida
🔍 Validando certificado: ./certificates/production/empresa.p12
============================================================

📋 INFORMACIÓN DEL CERTIFICADO:
   Subject: CN=Juan Pérez,O=Mi Empresa SA,C=PY
   Issuer: CN=eKuatia CA,O=SET,C=PY
   Serial Number: 123456789
   Not Valid Before: 2023-01-01T00:00:00
   Not Valid After: 2025-01-01T23:59:59
   Ruc: 12345678
   Psc: eKuatia
   Key Size: 2048

⚠️  ADVERTENCIAS:
   • Certificado expira en menos de 30 días

============================================================
✅ CERTIFICADO VÁLIDO PARA SIFEN
```

## 🔧 **Comandos Útiles**

### **Gestión de Certificados**
```bash
# 1. Validar certificado
python validate_cert.py ./certificates/production/empresa.p12 password

# 2. Extraer información del certificado
openssl pkcs12 -in empresa.p12 -nokeys -out cert.pem
openssl x509 -in cert.pem -text -noout

# 3. Verificar expiración
openssl x509 -in cert.pem -noout -dates

# 4. Extraer clave pública
openssl pkcs12 -in empresa.p12 -nokeys -nodes -out public.pem

# 5. Cambiar password de certificado
openssl pkcs12 -in empresa.p12 -out empresa_new.p12 -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES

# 6. Convertir formatos
openssl pkcs12 -in empresa.p12 -out empresa.pem -nodes  # A PEM
openssl pkcs12 -export -in cert.pem -inkey key.pem -out empresa.p12  # A P12
```

### **Testing de Conectividad**
```python
#!/usr/bin/env python3
"""Test de conectividad con certificado"""

import requests
from backend.app.services.sifen_client import SifenClient

def test_certificate_connectivity():
    """Probar conectividad con certificado"""
    
    try:
        # Configurar cliente
        client = SifenClient(
            environment="test",
            cert_path="./certificates/test/empresa_test.p12",
            cert_password="test123"
        )
        
        # Test básico de conectividad
        result = client.validate_connectivity()
        
        if result['success']:
            print("✅ Conectividad exitosa")
            for service, status in result['services'].items():
                icon = "✅" if status['connectivity'] else "❌"
                print(f"   {icon} {service}: {status}")
        else:
            print("❌ Error de conectividad")
            print(f"   Error: {result['error']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_certificate_connectivity()
```

## 🔒 **Mejores Prácticas de Seguridad**

### **1. Almacenamiento Seguro**
```bash
# Producción: Usar ubicaciones seguras del sistema
/etc/ssl/sifen/                    # Linux
C:\ProgramData\SSL\SIFEN\          # Windows

# Permisos restrictivos
chmod 600 certificado.p12         # Solo propietario
chown app:app certificado.p12      # Usuario específico de aplicación
```

### **2. Gestión de Passwords**
```python
# Usar gestores de secretos en producción
import os
from pathlib import Path

def get_certificate_password():
    """Obtener password de certificado de forma segura"""
    
    # Orden de prioridad:
    # 1. Variable de entorno
    password = os.getenv('SIFEN_CERT_PASSWORD')
    if password:
        return password
    
    # 2. Archivo de secretos (Docker/K8s)
    secret_file = Path('/run/secrets/sifen_cert_password')
    if secret_file.exists():
        return secret_file.read_text().strip()
    
    # 3. Gestor de secretos (AWS/Azure/GCP)
    try:
        # Ejemplo con AWS Secrets Manager
        import boto3
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId='sifen/cert/password')
        return response['SecretString']
    except:
        pass
    
    # 4. Último recurso: input interactivo (solo desarrollo)
    if os.getenv('ENVIRONMENT') == 'development':
        import getpass
        return getpass.getpass("Password del certificado: ")
    
    raise ValueError("No se pudo obtener password del certificado")
```

### **3. Rotación de Certificados**
```python
class CertificateManager:
    """Gestor de certificados con rotación automática"""
    
    def __init__(self):
        self.cert_path = os.getenv('SIFEN_CERT_PATH')
        self.backup_path = os.getenv('SIFEN_CERT_BACKUP_PATH')
        self.notification_days = 30  # Notificar 30 días antes
    
    def check_expiration(self):
        """Verificar expiración y notificar"""
        
        results = validate_psc_certificate(self.cert_path, self.get_password())
        
        if results['warnings']:
            for warning in results['warnings']:
                if '30 días' in warning:
                    self.send_expiration_alert()
        
        if results['errors']:
            for error in results['errors']:
                if 'expirado' in error:
                    self.send_expired_alert()
    
    def backup_certificate(self):
        """Crear backup del certificado actual"""
        
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{self.backup_path}/cert_backup_{timestamp}.p12"
        
        shutil.copy2(self.cert_path, backup_file)
        print(f"✅ Backup creado: {backup_file}")
    
    def deploy_new_certificate(self, new_cert_path: str):
        """Desplegar nuevo certificado"""
        
        # 1. Validar nuevo certificado
        results = validate_psc_certificate(new_cert_path, self.get_password())
        if not results['valid']:
            raise ValueError("Nuevo certificado no es válido")
        
        # 2. Backup del actual
        self.backup_certificate()
        
        # 3. Reemplazar certificado
        import shutil
        shutil.copy2(new_cert_path, self.cert_path)
        
        # 4. Verificar funcionamiento
        self.test_new_certificate()
        
        print("✅ Certificado actualizado exitosamente")
    
    def test_new_certificate(self):
        """Probar nuevo certificado"""
        
        try:
            client = SifenClient()
            result = client.validate_connectivity()
            
            if not result['success']:
                raise Exception("Conectividad falló con nuevo certificado")
                
        except Exception as e:
            # Restaurar backup si falla
            self.restore_backup()
            raise Exception(f"Nuevo certificado falló: {e}")
```

## 📋 **Troubleshooting Común**

### **Errores Frecuentes**

#### **1. "Certificado no encontrado"**
```bash
# Verificar ruta y permisos
ls -la ./certificates/production/empresa.p12
# Si no existe, verificar variables de entorno
echo $SIFEN_CERT_PATH
```

#### **2. "Password incorrecto"**
```bash
# Probar password manualmente
openssl pkcs12 -in empresa.p12 -nokeys -out test.pem
# Si falla, contactar al PSC para reset
```

#### **3. "Certificado expirado"**
```bash
# Verificar fechas
openssl x509 -in cert.pem -noout -dates
# Renovar con PSC antes de expiración
```

#### **4. "RUC no encontrado en certificado"**
```python
# Script para debuggear extracción de RUC
cert_path = "./certificates/empresa.p12"
password = "mi_password"

results = validate_psc_certificate(cert_path, password)
print(f"RUC extraído: {results['info'].get('ruc', 'NO ENCONTRADO')}")

# Si no se encuentra, verificar con PSC el formato correcto
```

#### **5. "PSC no autorizado"**
```bash
# Verificar que el PSC esté en la lista de autorizados
# Contactar a SET si hay dudas sobre autorización
```

### **Logs de Debugging**
```python
import logging

# Configurar logging para certificados
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sifen_cert_debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('sifen.certificates')

# Usar en validación
def debug_certificate_loading(cert_path, password):
    """Debug carga de certificado"""
    
    logger.info(f"Intentando cargar certificado: {cert_path}")
    
    try:
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        logger.info(f"Archivo leído: {len(cert_data)} bytes")
        
        private_key, certificate, additional = pkcs12.load_key_and_certificates(
            cert_data, password.encode('utf-8')
        )
        logger.info("Certificado cargado exitosamente")
        
        # Log información del certificado
        logger.info(f"Subject: {certificate.subject}")
        logger.info(f"Issuer: {certificate.issuer}")
        logger.info(f"Serial: {certificate.serial_number}")
        logger.info(f"Valid from: {certificate.not_valid_before}")
        logger.info(f"Valid until: {certificate.not_valid_after}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error cargando certificado: {e}")
        return False
```

## 📞 **Contactos y Soporte**

### **PSC Principales**

#### **eKuatia (SET)**
```
Website: https://ekuatia.set.gov.py
Email: soporte@ekuatia.set.gov.py
Teléfono: (021) 414-3000
Horarios: Lunes a Viernes 7:00-15:00
```

#### **Certified SA**
```
Website: https://www.certified.com.py
Email: soporte@certified.com.py
Teléfono: (021) 123-4567
```

#### **Paraguay Seguro**
```
Website: https://paraguayseguro.com.py
Email: info@paraguayseguro.com.py
```

### **Soporte Técnico SIFEN**
```
Portal: https://sifen.set.gov.py/soporte
Email: sifen@set.gov.py
Documentación: https://www.dnit.gov.py/web/e-kuatia/documentacion
```

## 🎯 **Checklist de Configuración**

### **Desarrollo** ✅
```bash
□ Variables de entorno configuradas (.env)
□ Certificado de prueba generado
□ Validador de certificados funciona
□ Test de conectividad exitoso
□ Logs configurados
□ .gitignore actualizado
```

### **Test/Staging** ✅
```bash
□ Certificado PSC de test obtenido
□ Variables de entorno específicas
□ Validación automática configurada
□ Test de integración funciona
□ Backup configurado
□ Monitoreo de expiración activo
```

### **Producción** ✅
```bash
□ Certificado PSC real configurado
□ Ubicación segura (/etc/ssl/sifen/)
□ Permisos restrictivos (600)
□ Password en gestor de secretos
□ Backup automático configurado
□ Alertas de expiración activas
□ Plan de rotación documentado
□ Contactos PSC actualizados
```

---

**🔐 Nota Crítica de Seguridad:**
- **NUNCA** commitear certificados al repositorio
- **SIEMPRE** usar passwords fuertes y únicos
- **ROTAR** certificados antes de expiración
- **BACKUP** regular de certificados
- **MONITOREAR** logs de seguridad

**🔄 Última actualización**: Configuración completa PSC Paraguay