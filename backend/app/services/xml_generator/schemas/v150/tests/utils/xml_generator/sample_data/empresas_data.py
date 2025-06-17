"""
Datos de empresas emisoras típicas paraguayas para testing SIFEN v150

Este módulo contiene datos realistas de empresas paraguayas representativas
del mercado objetivo del proyecto: PyMEs con facturación simple.

Sectores cubiertos:
- Servicios profesionales (consultorías, contadores)
- Comercio minorista (ferreterías, farmacias)
- Servicios técnicos (talleres, reparaciones)
- Gastronomía simple (restaurantes, cafeterías)

Todos los datos son representativos del mercado paraguayo real.
"""

from typing import Dict, Any

# Empresas emisoras típicas del mercado paraguayo
EMPRESAS_TIPICAS: Dict[str, Dict[str, Any]] = {
    # Servicios Profesionales - Consultoría Contable
    "consultora_contable": {
        "ruc": "80012345",
        "dv": "9",
        "razon_social": "Consultores Asociados S.A.",
        "nombre_fantasia": "Consultores Asociados",
        "direccion": "Av. Mariscal López 1234",
        "numero_casa": "1234",
        "telefono": "021123456",
        "email": "contacto@consultores.com.py",
        "ciudad": "Asunción",
        "departamento": "11",
        "codigo_ciudad": "101",
        "sector": "servicios_profesionales",
        "actividad_economica": "Servicios de contabilidad y auditoría",
        "timbrado_numero": "12345678",
        "timbrado_fecha_inicio": "2024-01-01",
        "timbrado_fecha_fin": "2024-12-31"
    },

    # Comercio Minorista - Ferretería
    "ferreteria_central": {
        "ruc": "80023456",
        "dv": "8",
        "razon_social": "Ferretería Central del Paraguay S.R.L.",
        "nombre_fantasia": "Ferretería Central",
        "direccion": "Av. España 890",
        "numero_casa": "890",
        "telefono": "021234567",
        "email": "ventas@ferreteria.com.py",
        "ciudad": "San Lorenzo",
        "departamento": "11",
        "codigo_ciudad": "103",
        "sector": "comercio_minorista",
        "actividad_economica": "Venta al por menor de artículos de ferretería",
        "timbrado_numero": "23456789",
        "timbrado_fecha_inicio": "2024-01-01",
        "timbrado_fecha_fin": "2024-12-31"
    },

    # Salud - Farmacia
    "farmacia_santa_rita": {
        "ruc": "80034567",
        "dv": "7",
        "razon_social": "Farmacia Santa Rita S.R.L.",
        "nombre_fantasia": "Farmacia Santa Rita",
        "direccion": "Calle Palma 567",
        "numero_casa": "567",
        "telefono": "021345678",
        "email": "info@santarita.com.py",
        "ciudad": "Asunción",
        "departamento": "11",
        "codigo_ciudad": "101",
        "sector": "salud",
        "actividad_economica": "Venta al por menor de productos farmacéuticos",
        "timbrado_numero": "34567890",
        "timbrado_fecha_inicio": "2024-01-01",
        "timbrado_fecha_fin": "2024-12-31"
    },

    # Servicios Técnicos - Taller Mecánico
    "taller_san_lorenzo": {
        "ruc": "80045678",
        "dv": "6",
        "razon_social": "Taller Mecánico San Lorenzo E.I.R.L.",
        "nombre_fantasia": "Taller San Lorenzo",
        "direccion": "Ruta 2 Km 7",
        "numero_casa": "S/N",
        "telefono": "021456789",
        "email": "taller@sanlorenzo.com.py",
        "ciudad": "San Lorenzo",
        "departamento": "11",
        "codigo_ciudad": "103",
        "sector": "servicios_tecnicos",
        "actividad_economica": "Reparación y mantenimiento de vehículos",
        "timbrado_numero": "45678901",
        "timbrado_fecha_inicio": "2024-01-01",
        "timbrado_fecha_fin": "2024-12-31"
    }
}


def get_empresa_by_sector(sector: str) -> Dict[str, Any]:
    """
    Retorna empresa típica por sector

    Args:
        sector: Tipo de sector (servicios_profesionales, comercio_minorista, etc.)

    Returns:
        Dict con datos de la empresa o None si no encuentra
    """
    for empresa_key, empresa_data in EMPRESAS_TIPICAS.items():
        if empresa_data.get("sector") == sector:
            return empresa_data
    return {}


def get_empresas_disponibles() -> list:
    """Retorna lista de claves de empresas disponibles"""
    return list(EMPRESAS_TIPICAS.keys())


def get_sectores_disponibles() -> list:
    """Retorna lista de sectores únicos disponibles"""
    sectores = set()
    for empresa_data in EMPRESAS_TIPICAS.values():
        sectores.add(empresa_data.get("sector", ""))
    return list(sectores)
