"""
Configuración del entorno de pruebas
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al PYTHONPATH
root_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(root_dir))
