"""
Script para ejecutar el módulo completo de firma digital
"""
import sys
from pathlib import Path
from .examples.generate_test_cert import generate_test_cert
from .examples.sign_example import main as sign_example
from .tests.run_tests import main as run_tests


def main():
    """Función principal"""
    try:
        # Generar certificado de prueba
        print("Generando certificado de prueba...")
        generate_test_cert()

        # Ejecutar ejemplo de firma
        print("\nEjecutando ejemplo de firma...")
        sign_example()

        # Ejecutar tests
        print("\nEjecutando tests...")
        run_tests()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
