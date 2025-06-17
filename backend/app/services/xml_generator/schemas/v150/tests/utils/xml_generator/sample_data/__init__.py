"""
Módulo de datos paraguayos para testing SIFEN v150

Este módulo proporciona datos realistas del mercado paraguayo para testing
de schemas modulares SIFEN. Incluye empresas, clientes, productos y escenarios
típicos de PyMEs paraguayas.

Uso principal:
    from sample_data import SampleData
    
    sample = SampleData()
    emisor = sample.get_test_emisor("consultora_contable")
    receptor = sample.get_test_receptor("empresa")
    items = sample.get_test_items("servicios_profesionales")

Módulos incluidos:
- empresas_data: Emisores típicos por sector
- clientes_data: Receptores frecuentes  
- productos_data: Catálogo con precios paraguayos
- ubicaciones_data: Geografía y direcciones Paraguay
- validadores_data: RUCs, teléfonos y códigos válidos
- escenarios_testing: Casos predefinidos completos
- sample_data_api: API unificada principal
"""

# Importaciones principales - API pública
from .sample_data_api import SampleData

# Datos específicos para casos avanzados
from .empresas_data import EMPRESAS_TIPICAS, get_empresa_by_sector
from .clientes_data import CLIENTES_FRECUENTES, get_cliente_by_tipo
from .productos_data import PRODUCTOS_POR_SECTOR, get_productos_by_sector, get_producto_by_codigo
from .ubicaciones_data import CIUDADES_PRINCIPALES, DIRECCIONES_TIPICAS
from .validadores_data import RUC_TESTING, TELEFONOS_VALIDOS, MONEDAS_VALIDAS
from .escenarios_testing import ESCENARIOS_TESTING, get_escenario

# API pública del módulo
__all__ = [
    # Clase principal
    "SampleData",

    # Datos por categoría
    "EMPRESAS_TIPICAS",
    "CLIENTES_FRECUENTES",
    "PRODUCTOS_POR_SECTOR",
    "CIUDADES_PRINCIPALES",
    "DIRECCIONES_TIPICAS",
    "RUC_TESTING",
    "TELEFONOS_VALIDOS",
    "MONEDAS_VALIDAS",
    "ESCENARIOS_TESTING",

    # Funciones auxiliares
    "get_empresa_by_sector",
    "get_cliente_by_tipo",
    "get_productos_by_sector",
    "get_producto_by_codigo",
    "get_escenario"
]

# Metadata del módulo
__version__ = "1.0.0"
__author__ = "Sistema Facturación SIFEN Paraguay"
__description__ = "Datos paraguayos realistas para testing schemas SIFEN v150"

# Instancia por defecto para uso rápido
default_sample_data = SampleData()

# Funciones de conveniencia para acceso rápido


def quick_emisor(sector: str = "consultora_contable"):
    """Acceso rápido a emisor típico"""
    return default_sample_data.get_test_emisor(sector)


def quick_receptor(tipo: str = "empresa"):
    """Acceso rápido a receptor típico"""
    return default_sample_data.get_test_receptor(tipo)


def quick_items(sector: str = "servicios_profesionales", cantidad: int = 1):
    """Acceso rápido a items por sector"""
    return default_sample_data.get_test_items(sector, cantidad)


def quick_scenario(nombre: str):
    """Acceso rápido a escenario predefinido"""
    return default_sample_data.get_test_scenario(nombre)
