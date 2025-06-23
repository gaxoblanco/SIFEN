"""
Catálogo de productos y servicios por sector para testing SIFEN v150

Este módulo contiene productos y servicios típicos del mercado paraguayo
con precios reales y configuración de IVA según normativa vigente.

Sectores incluidos:
- Servicios profesionales (consultoría, contabilidad)
- Ferretería (construcción, herramientas)
- Farmacia (medicamentos, higiene)
- Servicios técnicos (reparaciones, mantenimiento)

Precios actualizados según mercado paraguayo 2024.
"""

from typing import Dict, List, Any

# Catálogo de productos por sector empresarial
PRODUCTOS_POR_SECTOR: Dict[str, List[Dict[str, Any]]] = {
    # Servicios Profesionales
    "servicios_profesionales": [
        {
            "codigo": "SER001",
            "descripcion": "Consultoría contable mensual",
            "precio_unitario": 800000,  # Gs. 800.000
            "unidad_medida": "Servicio",
            "iva_porcentaje": 10,
            "categoria": "servicios_gravados",
            "ncm": "",  # No aplica para servicios
            "tipo": "servicio"
        },
        {
            "codigo": "SER002",
            "descripcion": "Declaración jurada anual",
            "precio_unitario": 500000,  # Gs. 500.000
            "unidad_medida": "Servicio",
            "iva_porcentaje": 10,
            "categoria": "servicios_gravados",
            "ncm": "",
            "tipo": "servicio"
        }
    ],

    # Ferretería - Materiales de construcción
    "ferreteria": [
        {
            "codigo": "FER001",
            "descripcion": "Cemento Portland x bolsa 50kg",
            "precio_unitario": 45000,  # Gs. 45.000
            "unidad_medida": "Bolsa",
            "iva_porcentaje": 10,
            "categoria": "construccion",
            "ncm": "25231000",
            "tipo": "producto"
        },
        {
            "codigo": "FER002",
            "descripcion": "Pintura látex blanca x 20L",
            "precio_unitario": 320000,  # Gs. 320.000
            "unidad_medida": "Balde",
            "iva_porcentaje": 10,
            "categoria": "pintura",
            "ncm": "32082000",
            "tipo": "producto"
        }
    ],

    # Farmacia - Medicamentos y productos de higiene
    "farmacia": [
        {
            "codigo": "FAR001",
            "descripcion": "Paracetamol 500mg x 20 comprimidos",
            "precio_unitario": 8500,   # Gs. 8.500
            "unidad_medida": "Caja",
            "iva_porcentaje": 0,       # Medicamentos exentos
            "categoria": "medicamentos",
            "ncm": "30049099",
            "tipo": "producto"
        },
        {
            "codigo": "FAR002",
            "descripcion": "Alcohol en gel x 250ml",
            "precio_unitario": 15000,  # Gs. 15.000
            "unidad_medida": "Frasco",
            "iva_porcentaje": 10,
            "categoria": "higiene",
            "ncm": "33059000",
            "tipo": "producto"
        }
    ],

    # Servicios Técnicos - Talleres y reparaciones
    "servicios_tecnicos": [
        {
            "codigo": "TAL001",
            "descripcion": "Cambio de aceite y filtros",
            "precio_unitario": 180000,  # Gs. 180.000
            "unidad_medida": "Servicio",
            "iva_porcentaje": 10,
            "categoria": "reparacion_vehiculos",
            "ncm": "",
            "tipo": "servicio"
        },
        {
            "codigo": "TAL002",
            "descripcion": "Alineación y balanceo",
            "precio_unitario": 250000,  # Gs. 250.000
            "unidad_medida": "Servicio",
            "iva_porcentaje": 10,
            "categoria": "reparacion_vehiculos",
            "ncm": "",
            "tipo": "servicio"
        }
    ]
}


def get_productos_by_sector(sector: str) -> List[Dict[str, Any]]:
    """Retorna lista de productos por sector"""
    return PRODUCTOS_POR_SECTOR.get(sector, [])


def get_sectores_productos() -> List[str]:
    """Retorna lista de sectores disponibles"""
    return list(PRODUCTOS_POR_SECTOR.keys())


def get_producto_by_codigo(codigo: str) -> Dict[str, Any]:
    """Busca producto por código en todos los sectores"""
    for productos in PRODUCTOS_POR_SECTOR.values():
        for producto in productos:
            if producto.get("codigo") == codigo:
                return producto
    return {}
