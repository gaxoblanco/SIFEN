"""
Escenarios de testing predefinidos para schemas SIFEN v150

Este módulo contiene casos de prueba completos que combinan:
- Emisor (empresa típica)
- Receptor (cliente frecuente)  
- Items (productos/servicios)
- Tipo de documento

Escenarios representativos del 85% de casos de PyMEs paraguayas.
"""

from typing import Dict, Any

# Escenarios de testing predefinidos
ESCENARIOS_TESTING: Dict[str, Dict[str, Any]] = {
    # Factura simple de servicios profesionales
    "factura_consultora_simple": {
        "emisor": "consultora_contable",
        "receptor": "empresa_distribuidora",
        "items": ["SER001"],  # Consultoría contable mensual
        "tipo_documento": "01",
        "condicion_operacion": "1",  # Contado
        "moneda": "PYG",
        "descripcion": "Factura simple de servicios profesionales"
    },

    # Factura retail con múltiples productos
    "factura_ferreteria_multiple": {
        "emisor": "ferreteria_central",
        "receptor": "consumidor_final",
        "items": ["FER001", "FER002"],  # Cemento + Pintura
        "tipo_documento": "01",
        "condicion_operacion": "1",  # Contado
        "moneda": "PYG",
        "descripcion": "Factura retail con múltiples productos"
    },

    # Factura farmacia con productos exentos
    "factura_farmacia_mixta": {
        "emisor": "farmacia_santa_rita",
        "receptor": "cliente_persona",
        "items": ["FAR001", "FAR002"],  # Paracetamol (exento) + Alcohol gel
        "tipo_documento": "01",
        "condicion_operacion": "1",  # Contado
        "moneda": "PYG",
        "descripcion": "Factura farmacia con IVA mixto (exento + gravado)"
    },

    # Servicios técnicos a crédito
    "factura_taller_credito": {
        "emisor": "taller_san_lorenzo",
        "receptor": "empresa_distribuidora",
        "items": ["TAL001", "TAL002"],  # Cambio aceite + Alineación
        "tipo_documento": "01",
        "condicion_operacion": "2",  # Crédito
        "moneda": "PYG",
        "descripcion": "Factura servicios técnicos a crédito"
    }
}


def get_escenario(nombre: str) -> Dict[str, Any]:
    """Retorna escenario completo por nombre"""
    return ESCENARIOS_TESTING.get(nombre, {})


def get_escenarios_disponibles() -> list:
    """Retorna lista de nombres de escenarios disponibles"""
    return list(ESCENARIOS_TESTING.keys())
