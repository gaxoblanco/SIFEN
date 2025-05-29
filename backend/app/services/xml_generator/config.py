"""
Configuración específica del módulo XML Generator
"""
from pathlib import Path

# Directorio base del módulo
MODULE_DIR = Path(__file__).parent

# Directorio de esquemas XSD
SCHEMAS_DIR = MODULE_DIR / "schemas"

# Directorio de templates XML
TEMPLATES_DIR = MODULE_DIR / "templates"

# Versión del Manual Técnico SIFEN
SIFEN_VERSION = "1.5.0"
