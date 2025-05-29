"""
Generador principal de XML para documentos SIFEN
"""
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from .models import FacturaSimple
from .config import TEMPLATES_DIR, SIFEN_VERSION


class XMLGenerator:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True
        )
        self.template = self.env.get_template('factura_simple.xml')

    def generate_simple_invoice_xml(self, factura: FacturaSimple) -> str:
        """
        Genera el XML para una factura simple

        Args:
            factura: Datos de la factura validados por Pydantic

        Returns:
            str: XML generado
        """
        # Convertir datetime a formato SIFEN
        fecha_emision = factura.fecha_emision.strftime("%Y-%m-%dT%H:%M:%S")

        # Preparar datos para el template
        template_data = {
            "fecha_emision": fecha_emision,
            "tipo_documento": factura.tipo_documento,
            "numero_documento": factura.numero_documento,
            "moneda": factura.moneda,
            "tipo_cambio": factura.tipo_cambio,
            "emisor": factura.emisor.model_dump(),
            "receptor": factura.receptor.model_dump(),
            "items": [item.model_dump() for item in factura.items],
            "total_exenta": str(factura.total_exenta),
            "total_gravada": str(factura.total_gravada),
            "total_iva": str(factura.total_iva),
            "total_general": str(factura.total_general),
            "csc": factura.csc
        }

        # Generar XML
        xml = self.template.render(**template_data)
        return xml
