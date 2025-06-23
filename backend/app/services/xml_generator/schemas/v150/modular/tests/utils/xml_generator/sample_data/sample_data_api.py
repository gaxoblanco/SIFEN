"""
API unificada para datos de testing SIFEN v150

Clase principal SampleData que proporciona acceso unificado a todos los
datos paraguayos para testing de schemas modulares.

Facilita la generación de XMLs realistas combinando:
- Empresas emisoras por sector
- Clientes receptores por tipo  
- Productos/servicios con precios paraguayos
- Escenarios predefinidos de testing

API simple para DocumentTypesGenerator y tests unitarios.
"""

import random
from typing import Dict, List, Any, Optional

# Importar todos los módulos de datos
from .empresas_data import EMPRESAS_TIPICAS, get_empresa_by_sector
from .clientes_data import CLIENTES_FRECUENTES, get_cliente_by_tipo
from .productos_data import PRODUCTOS_POR_SECTOR, get_productos_by_sector, get_producto_by_codigo
from .ubicaciones_data import CIUDADES_PRINCIPALES, DIRECCIONES_TIPICAS
from .validadores_data import RUC_TESTING, TELEFONOS_VALIDOS, MONEDAS_VALIDAS
from .escenarios_testing import ESCENARIOS_TESTING, get_escenario


class SampleData:
    """
    API unificada para datos paraguayos de testing SIFEN v150

    Proporciona métodos simples para obtener datos realistas
    del mercado paraguayo para testing de schemas modulares.
    """

    def get_test_emisor(self, sector: str = "consultora_contable") -> Dict[str, Any]:
        """
        Retorna emisor típico por sector o clave específica

        Args:
            sector: Sector empresarial o clave específica de empresa

        Returns:
            Dict con datos completos del emisor
        """
        # Buscar por clave específica primero
        if sector in EMPRESAS_TIPICAS:
            return EMPRESAS_TIPICAS[sector]

        # Buscar por sector empresarial
        empresa = get_empresa_by_sector(sector)
        if empresa:
            return empresa

        # Default: consultora contable
        return EMPRESAS_TIPICAS["consultora_contable"]

    def get_test_receptor(self, tipo: str = "empresa") -> Dict[str, Any]:
        """
        Retorna receptor típico por tipo

        Args:
            tipo: Tipo de receptor (consumidor_final, empresa, persona_fisica)

        Returns:
            Dict con datos completos del receptor
        """
        cliente = get_cliente_by_tipo(tipo)
        if cliente:
            return cliente

        # Default: empresa distribuidora
        return CLIENTES_FRECUENTES["empresa_distribuidora"]

    def get_test_items(self, sector: str = "servicios_profesionales", cantidad: int = 1) -> List[Dict[str, Any]]:
        """
        Retorna lista de items por sector

        Args:
            sector: Sector de productos/servicios
            cantidad: Número de items a retornar

        Returns:
            Lista de items con datos completos
        """
        productos = get_productos_by_sector(sector)
        if not productos:
            # Default: servicios profesionales
            productos = PRODUCTOS_POR_SECTOR["servicios_profesionales"]

        # Seleccionar hasta 'cantidad' items disponibles
        return productos[:cantidad]

    def get_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        Retorna escenario completo predefinido

        Args:
            scenario_name: Nombre del escenario

        Returns:
            Dict con emisor, receptor, items y configuración
        """
        return get_escenario(scenario_name)

    def get_simple_invoice_data(self) -> Dict[str, Any]:
        """Retorna datos para factura simple típica"""
        return {
            "emisor": self.get_test_emisor("consultora_contable"),
            "receptor": self.get_test_receptor("empresa"),
            "items": self.get_test_items("servicios_profesionales", 1),
            "tipo_documento": "01",
            "condicion_operacion": "1",
            "moneda": "PYG"
        }

    def get_complex_invoice_data(self) -> Dict[str, Any]:
        """Retorna datos para factura compleja con múltiples items"""
        return {
            "emisor": self.get_test_emisor("ferreteria_central"),
            "receptor": self.get_test_receptor("consumidor_final"),
            "items": self.get_test_items("ferreteria", 2),
            "tipo_documento": "01",
            "condicion_operacion": "1",
            "moneda": "PYG"
        }

    def get_random_empresa(self, sector: Optional[str] = None) -> Dict[str, Any]:
        """Retorna empresa aleatoria, opcionalmente filtrada por sector"""
        empresas_disponibles = list(EMPRESAS_TIPICAS.values())

        if sector:
            empresas_disponibles = [
                e for e in empresas_disponibles if e.get("sector") == sector]

        return random.choice(empresas_disponibles) if empresas_disponibles else {}

    def generate_invoice_items(self, count: int = 2) -> List[Dict[str, Any]]:
        """Genera lista aleatoria de items para factura"""
        todos_productos = []
        for productos in PRODUCTOS_POR_SECTOR.values():
            todos_productos.extend(productos)

        return random.sample(todos_productos, min(count, len(todos_productos)))
