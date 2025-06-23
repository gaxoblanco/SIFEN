"""
Datos geográficos de Paraguay para testing SIFEN v150

Este módulo contiene ubicaciones geográficas oficiales de Paraguay
según la división territorial del país y direcciones típicas.

Incluye:
- Ciudades principales con códigos oficiales
- Departamentos según división administrativa
- Direcciones típicas de zonas comerciales

Datos según códigos oficiales del Gobierno de Paraguay.
"""

from typing import Dict, List, Any

# Ciudades principales con códigos oficiales Paraguay
CIUDADES_PRINCIPALES: Dict[str, Dict[str, Any]] = {
    "101": {
        "nombre": "Asunción",
        "departamento": "11",
        "region": "central",
        "codigo_postal": "1001"
    },
    "103": {
        "nombre": "San Lorenzo",
        "departamento": "11",
        "region": "central",
        "codigo_postal": "2160"
    },
    "104": {
        "nombre": "Luque",
        "departamento": "11",
        "region": "central",
        "codigo_postal": "2060"
    },
    "220": {
        "nombre": "Ciudad del Este",
        "departamento": "22",
        "region": "este",
        "codigo_postal": "7000"
    },
    "180": {
        "nombre": "Encarnación",
        "departamento": "18",
        "region": "sur",
        "codigo_postal": "6000"
    }
}

# Direcciones típicas de zonas comerciales paraguayas
DIRECCIONES_TIPICAS: List[str] = [
    "Av. Mariscal López 1234",      # Asunción - zona comercial
    "Av. España 890",               # Asunción - microcentro
    "Calle Palma 567",              # Asunción - centro histórico
    "Av. Eusebio Ayala 2345",       # Asunción/San Lorenzo
    "Ruta 2 Km 7",                  # San Lorenzo - zona industrial
    "Av. Bernardino Caballero 456",  # Ciudad del Este
    "Calle Chile 123",              # Asunción - barrio residencial
    "Av. San Martín 678"            # Luque - zona comercial
]


def get_ciudad_by_codigo(codigo: str) -> Dict[str, Any]:
    """Retorna datos de ciudad por código oficial"""
    return CIUDADES_PRINCIPALES.get(codigo, {})


def get_ciudades_por_departamento(departamento: str) -> List[Dict[str, Any]]:
    """Retorna ciudades de un departamento específico"""
    return [ciudad for ciudad in CIUDADES_PRINCIPALES.values()
            if ciudad.get("departamento") == departamento]
