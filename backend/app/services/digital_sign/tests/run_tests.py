"""
Script para ejecutar los tests del módulo de firma digital
"""
import pytest
import sys
from pathlib import Path


def main():
    """Función principal"""
    # Obtener directorio de tests
    tests_dir = Path(__file__).parent

    # Ejecutar tests
    result = pytest.main([
        str(tests_dir),
        "-v",
        "--cov=..",
        "--cov-report=term-missing"
    ])

    # Salir con código de error si hay fallos
    sys.exit(result)


if __name__ == "__main__":
    main()
