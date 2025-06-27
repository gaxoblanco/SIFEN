"""
Test 2: Operaciones de Certificados PSC
- Validación de certificados
- Información de certificados  
- Verificación de expiración
- Gestión de errores comunes
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# ========================================
# CONFIGURACIÓN DE PATHS - IGUAL QUE TEST 1
# ========================================


def setup_paths():
    """Configurar paths para importaciones desde cualquier directorio"""
    current_dir = Path(__file__).parent.absolute()

    # Buscar el directorio backend/ subiendo en la jerarquía
    backend_dir = current_dir
    while backend_dir.name != "backend" and backend_dir.parent != backend_dir:
        backend_dir = backend_dir.parent

    if backend_dir.name == "backend":
        # Agregar backend al path para imports con 'app.'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        return True, backend_dir
    else:
        return False, None


# Configurar paths al inicio
paths_ok, backend_path = setup_paths()

# ========================================
# IMPORTS CON ESTRATEGIAS MÚLTIPLES
# ========================================

IMPORTS_SUCCESS = False
IMPORT_ERROR = None

# Estrategia 1: Import directo desde app
try:
    from app.services.digital_sign import (
        CertificateManager,
        CertificateConfig,
        DigitalSignConfig,
    )
    IMPORTS_SUCCESS = True
except ImportError as e:
    IMPORT_ERROR = e


def test_certificate_operations():
    """Test function for pytest compatibility"""
    main()


def main():
    print("🔐 TEST 2: OPERACIONES DE CERTIFICADOS PSC")
    print("=" * 55)

    if not IMPORTS_SUCCESS:
        print(f"❌ Error en importaciones: {IMPORT_ERROR}")
        return

    # ======================================
    # SECCIÓN 1: CONFIGURACIONES DE PRUEBA
    # ======================================
    print("\n📋 CONFIGURACIONES DE CERTIFICADOS")
    print("-" * 40)

    # Config 1: Certificado válido (simulado)
    valid_config = CertificateConfig(
        cert_path=Path("test_valid.pfx"),
        cert_password="password123",
        cert_expiry_days=30
    )
    print("✅ Config Válida:")
    print(f"   📁 cert_path: {valid_config.cert_path}")
    print(f"   🔒 cert_password: {'*' * len(valid_config.cert_password)}")
    print(f"   ⏰ cert_expiry_days: {valid_config.cert_expiry_days}")

    # Config 2: Certificado inexistente
    missing_config = CertificateConfig(
        cert_path=Path("certificado_no_existe.pfx"),
        cert_password="wrong_password",
        cert_expiry_days=15
    )
    print("\n⚠️ Config Archivo Inexistente:")
    print(f"   📁 cert_path: {missing_config.cert_path}")
    print(f"   🔒 cert_password: {'*' * len(missing_config.cert_password)}")

    # Config 3: Password incorrecta
    wrong_password_config = CertificateConfig(
        cert_path=Path("test.pfx"),  # Puede existir pero password mala
        cert_password="password_incorrecto",
        cert_expiry_days=60
    )
    print("\n⚠️ Config Password Incorrecta:")
    print(f"   📁 cert_path: {wrong_password_config.cert_path}")
    print(
        f"   🔒 cert_password: {'*' * len(wrong_password_config.cert_password)}")

    # ======================================
    # SECCIÓN 2: CREACIÓN DE MANAGERS
    # ======================================
    print("\n\n🔧 CREACIÓN DE CERTIFICATE MANAGERS")
    print("-" * 45)

    managers_results = []

    # Manager 1: Con config válida
    try:
        manager_valid = CertificateManager(valid_config)
        print("✅ Manager con config válida creado")
        print(f"   📊 TIPO: {type(manager_valid)}")
        print(f"   🆔 ID: {id(manager_valid)}")
        managers_results.append(("valid", manager_valid, None))
    except Exception as e:
        print(f"⚠️ Manager válido con error: {type(e).__name__}: {e}")
        managers_results.append(("valid", None, e))

    # Manager 2: Con archivo inexistente
    try:
        manager_missing = CertificateManager(missing_config)
        print("\n✅ Manager con archivo inexistente creado")
        print(f"   📊 TIPO: {type(manager_missing)}")
        managers_results.append(("missing", manager_missing, None))
    except Exception as e:
        print(f"\n⚠️ Manager inexistente con error: {type(e).__name__}: {e}")
        managers_results.append(("missing", None, e))

    # Manager 3: Con password incorrecta
    try:
        manager_wrong = CertificateManager(wrong_password_config)
        print("\n✅ Manager con password incorrecta creado")
        print(f"   📊 TIPO: {type(manager_wrong)}")
        managers_results.append(("wrong_password", manager_wrong, None))
    except Exception as e:
        print(
            f"\n⚠️ Manager password incorrecta con error: {type(e).__name__}: {e}")
        managers_results.append(("wrong_password", None, e))

    # ======================================
    # SECCIÓN 3: OPERACIONES DE CERTIFICADOS
    # ======================================
    print("\n\n🧪 OPERACIONES DE CERTIFICADOS - RESULTADOS REALES")
    print("-" * 55)

    for config_name, manager, creation_error in managers_results:
        print(f"\n🔍 PROBANDO: Manager {config_name.upper()}")
        print("=" * 50)

        if creation_error:
            print(f"   ❌ No se pudo crear manager: {creation_error}")
            continue

        # ===== OPERACIÓN 1: validate_certificate() =====
        print("\n1️⃣ validate_certificate():")
        try:
            is_valid = manager.validate_certificate()
            print(f"   📤 DEVUELVE: {is_valid}")
            print(f"   📊 TIPO: {type(is_valid)}")

            if is_valid:
                print("   ✅ SIGNIFICA: Certificado válido y usable")
            else:
                print("   ❌ SIGNIFICA: Certificado inválido o no encontrado")

        except FileNotFoundError as e:
            print(f"   📁 ARCHIVO NO ENCONTRADO: {e}")
            print("   💡 SIGNIFICA: El archivo .pfx no existe en la ruta")
        except Exception as e:
            print(f"   ⚠️ ERROR: {type(e).__name__}: {e}")
            print(f"   💡 SIGNIFICA: Problema con certificado o contraseña")

        # ===== OPERACIÓN 2: check_expiry() =====
        print("\n2️⃣ check_expiry():")
        try:
            expiry_result = manager.check_expiry()
            print(f"   📤 DEVUELVE: {expiry_result}")
            print(f"   📊 TIPO: {type(expiry_result)}")

            # Analizar contenido del resultado
            if isinstance(expiry_result, tuple) and len(expiry_result) == 2:
                is_expiring, days_or_delta = expiry_result
                print(f"   🟡 is_expiring: {is_expiring} (bool)")
                print(f"   📅 days_remaining: {days_or_delta}")

                if is_expiring:
                    print("   ⚠️ SIGNIFICA: Certificado próximo a vencer")
                else:
                    print("   ✅ SIGNIFICA: Certificado tiene tiempo válido")
            else:
                print(f"   📋 FORMATO INESPERADO: {expiry_result}")

        except Exception as e:
            print(f"   ⚠️ ERROR: {type(e).__name__}: {e}")
            print(f"   💡 SIGNIFICA: No se pudo verificar expiración")

        # ===== OPERACIÓN 3: get_certificate_info() =====
        print("\n3️⃣ get_certificate_info():")
        try:
            cert_info = manager.get_certificate_info()
            print(f"   📤 DEVUELVE: {cert_info}")
            print(f"   📊 TIPO: {type(cert_info)}")

            # Analizar diccionario de información
            if isinstance(cert_info, dict):
                print("   📋 CONTENIDO:")
                for key, value in cert_info.items():
                    print(f"      🔑 {key}: {value}")

                # Información crítica para SIFEN
                if 'ruc_emisor' in cert_info:
                    print(f"   🏢 RUC EMISOR: {cert_info['ruc_emisor']}")
                if 'serial_number' in cert_info:
                    print(f"   🔢 SERIAL: {cert_info['serial_number']}")
                if 'not_valid_after' in cert_info:
                    print(f"   📅 VENCE: {cert_info['not_valid_after']}")
            else:
                print(f"   📋 FORMATO INESPERADO: {cert_info}")

        except Exception as e:
            print(f"   ⚠️ ERROR: {type(e).__name__}: {e}")
            print(f"   💡 SIGNIFICA: No se pudo obtener info del certificado")

        # ===== OPERACIÓN 4: load_certificate() =====
        print("\n4️⃣ load_certificate():")
        try:
            loaded_cert = manager.load_certificate()
            print(f"   📤 DEVUELVE: {loaded_cert}")
            print(f"   📊 TIPO: {type(loaded_cert)}")

            # Verificar si devuelve objeto Certificate o certificado crudo
            if hasattr(loaded_cert, 'ruc_emisor'):
                print(f"   🏢 loaded_cert.ruc_emisor: {loaded_cert.ruc_emisor}")
            if hasattr(loaded_cert, 'serial_number'):
                print(
                    f"   🔢 loaded_cert.serial_number: {loaded_cert.serial_number}")
            if hasattr(loaded_cert, 'not_valid_after'):
                print(
                    f"   📅 loaded_cert.not_valid_after: {loaded_cert.not_valid_after}")

        except Exception as e:
            print(f"   ⚠️ ERROR: {type(e).__name__}: {e}")
            print(f"   💡 SIGNIFICA: No se pudo cargar certificado")

    # ======================================
    # SECCIÓN 4: CASOS DE USO COMUNES
    # ======================================
    print("\n\n💡 CASOS DE USO COMUNES")
    print("-" * 35)

    print("\n🎯 PATRÓN DE VALIDACIÓN COMPLETA:")
    print("""
    try:
        cert_manager = CertificateManager(config)
        
        # 1. Verificar que certificado es válido
        if not cert_manager.validate_certificate():
            print("❌ Certificado inválido")
            return False
            
        # 2. Verificar expiración
        is_expiring, days_left = cert_manager.check_expiry()
        if is_expiring:
            print(f"⚠️ Certificado expira en {days_left} días")
            
        # 3. Obtener información para SIFEN
        info = cert_manager.get_certificate_info()
        ruc_emisor = info.get('ruc_emisor')
        
        print(f"✅ Certificado válido para RUC: {ruc_emisor}")
        return True
        
    except FileNotFoundError:
        print("❌ Archivo certificado no encontrado")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    """)

    print("\n🎯 MANEJO DE ERRORES TÍPICOS:")
    error_cases = [
        "FileNotFoundError → Archivo .pfx no existe",
        "ValueError → Contraseña incorrecta",
        "CertificateError → Certificado corrupto o formato inválido",
        "ExpirationError → Certificado vencido",
        "PSCValidationError → No es certificado PSC válido"
    ]

    for case in error_cases:
        print(f"   📋 {case}")

    print("\n🎉 TEST 2 COMPLETADO")
    print("📝 Para probar con certificado real:")
    print("   1. Obtener certificado PSC (.pfx)")
    print("   2. Actualizar cert_path en configuración")
    print("   3. Proporcionar contraseña correcta")
    print("   4. Re-ejecutar este test")


if __name__ == "__main__":
    main()
