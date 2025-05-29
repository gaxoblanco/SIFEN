"""
Validador XML para documentos SIFEN
"""
from pathlib import Path
from typing import List, Tuple
from lxml import etree
from .config import SCHEMAS_DIR


class XMLValidator:
    def __init__(self):
        self.schema_path = SCHEMAS_DIR / "DE_v150.xsd"
        self.schema = self._load_schema()

    def _load_schema(self) -> etree.XMLSchema:
        """Carga el esquema XSD"""
        parser = etree.XMLParser(remove_blank_text=True)
        schema_doc = etree.parse(str(self.schema_path), parser)
        return etree.XMLSchema(schema_doc)

    def validate_xml(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Valida un documento XML contra el esquema XSD de SIFEN

        Args:
            xml_content: Contenido XML a validar

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores)
        """
        try:
            # Parsear el XML
            parser = etree.XMLParser(remove_blank_text=True)
            xml_doc = etree.fromstring(xml_content.encode('utf-8'), parser)

            # Validar contra el esquema
            is_valid = self.schema.validate(xml_doc)

            if is_valid:
                return True, []

            # Si no es válido, recolectar errores
            errors = []
            for error in self.schema.error_log:
                errors.append(f"Línea {error.line}: {error.message}")

            return False, errors

        except etree.XMLSyntaxError as e:
            return False, [f"Error de sintaxis XML: {str(e)}"]
        except Exception as e:
            return False, [f"Error inesperado: {str(e)}"]
