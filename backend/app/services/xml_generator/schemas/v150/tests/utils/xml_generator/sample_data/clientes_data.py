"""
Datos de clientes/receptores típicos paraguayos para testing SIFEN v150

Este módulo contiene datos realistas de receptores de documentos electrónicos
según los casos más frecuentes en PyMEs paraguayas.

Tipos de receptores cubiertos:
- Consumidor final (sin RUC específico)
- Empresas cliente (contribuyentes registrados)
- Personas físicas (RUC personal)

Todos los datos siguen formatos oficiales paraguayos.
"""

from typing import Dict, Any

# Clientes/receptores típicos del mercado paraguayo
CLIENTES_FRECUENTES: Dict[str, Dict[str, Any]] = {
    # Consumidor Final - Caso más común en retail
    "consumidor_final": {
        "ruc": "99999999",
        "dv": "9",
        "razon_social": "CONSUMIDOR FINAL",
        "nombre_fantasia": "CONSUMIDOR FINAL",
        "direccion": "NO DISPONIBLE",
        "numero_casa": "S/N",
        "telefono": "NO DISPONIBLE",
        "email": "consumidor@final.com",
        "ciudad": "NO DISPONIBLE",
        "departamento": "00",
        "codigo_ciudad": "000",
        "tipo_receptor": "consumidor_final"
    },

    # Empresa Cliente - Distribuidora típica
    "empresa_distribuidora": {
        "ruc": "87654321",
        "dv": "0",
        "razon_social": "Distribuidora Nacional S.A.",
        "nombre_fantasia": "Distribuidora Nacional",
        "direccion": "Av. Eusebio Ayala 2345",
        "numero_casa": "2345",
        "telefono": "021987654",
        "email": "compras@distribuidora.com.py",
        "ciudad": "Asunción",
        "departamento": "11",
        "codigo_ciudad": "101",
        "tipo_receptor": "empresa"
    },

    # Persona Física - Cliente individual con RUC
    "cliente_persona": {
        "ruc": "12345678",
        "dv": "1",
        "razon_social": "Juan Carlos González López",
        "nombre_fantasia": "Juan González",
        "direccion": "Calle Chile 123",
        "numero_casa": "123",
        "telefono": "0981123456",
        "email": "juan.gonzalez@gmail.com",
        "ciudad": "Asunción",
        "departamento": "11",
        "codigo_ciudad": "101",
        "tipo_receptor": "persona_fisica"
    }
}


def get_cliente_by_tipo(tipo: str) -> Dict[str, Any]:
    """Retorna cliente por tipo (consumidor_final, empresa, persona_fisica)"""
    for cliente_key, cliente_data in CLIENTES_FRECUENTES.items():
        if cliente_data.get("tipo_receptor") == tipo:
            return cliente_data
    return {}


def get_clientes_disponibles() -> list:
    """Retorna lista de claves de clientes disponibles"""
    return list(CLIENTES_FRECUENTES.keys())
