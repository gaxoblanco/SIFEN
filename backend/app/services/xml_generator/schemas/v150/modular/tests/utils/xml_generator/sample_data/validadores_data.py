"""
Datos para validación paraguaya en testing SIFEN v150

Este módulo contiene datos válidos según formatos oficiales paraguayos
para testing de validaciones y casos edge.

Incluye:
- RUCs válidos por tipo de contribuyente
- Teléfonos según formato paraguayo
- Códigos oficiales para validación

Todos los datos siguen normativas paraguayas vigentes.
"""

from typing import Dict, List

# RUCs paraguayos válidos para testing
RUC_TESTING: Dict[str, List[str]] = {
    "empresas_validas": [
        "80012345",  # Consultora contable
        "80023456",  # Ferretería central
        "80034567",  # Farmacia Santa Rita
        "80045678",  # Taller San Lorenzo
        "80056789"   # Empresa adicional para tests
    ],
    "personas_fisicas": [
        "12345678",  # Juan González
        "23456789",  # Cliente persona 2
        "34567890",  # Cliente persona 3
        "45678901"   # Cliente persona 4
    ],
    "especiales": [
        "99999999"   # Consumidor final
    ]
}

# Teléfonos formato paraguayo válidos
TELEFONOS_VALIDOS: List[str] = [
    "021123456",    # Fijo Asunción
    "021234567",    # Fijo Asunción 2
    "061234567",    # Fijo Ciudad del Este
    "0981123456",   # Celular Personal
    "0985234567",   # Celular Tigo
    "0982345678",   # Celular Personal 2
    "0986456789"    # Celular Claro
]

# Códigos de moneda soportados SIFEN
MONEDAS_VALIDAS: List[str] = ["PYG", "USD", "EUR", "BRL", "ARS"]

# Tipos de documento electrónico
TIPOS_DOCUMENTO_VALIDOS: List[str] = ["01", "02", "03", "04", "05"]


def validar_ruc_formato(ruc: str) -> bool:
    """Valida formato básico de RUC paraguayo (8 dígitos)"""
    return len(ruc) == 8 and ruc.isdigit()


def validar_telefono_formato(telefono: str) -> bool:
    """Valida formato básico de teléfono paraguayo"""
    return len(telefono) >= 9 and telefono.startswith(("021", "061", "098"))
