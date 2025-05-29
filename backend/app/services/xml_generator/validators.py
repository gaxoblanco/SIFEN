"""
Validador XML para documentos SIFEN
"""
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from lxml import etree
from .config import SCHEMAS_DIR


class SifenValidationError(Exception):
    """Error específico de validación SIFEN"""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        self.message = message
        self.errors = errors if errors is not None else []
        super().__init__(self.message)


class XMLValidator:
    def __init__(self):
        self.schema_path = SCHEMAS_DIR / "DE_v150.xsd"
        self.schema = self._load_schema()
        self._error_mappings = self._load_error_mappings()

    def _load_schema(self) -> etree.XMLSchema:
        """Carga el esquema XSD"""
        parser = etree.XMLParser(remove_blank_text=True)
        schema_doc = etree.parse(str(self.schema_path), parser)
        return etree.XMLSchema(schema_doc)

    def _load_error_mappings(self) -> Dict[str, str]:
        """Carga mapeo de errores comunes de SIFEN"""
        return {
            "cvc-pattern-valid": "Formato inválido",
            "cvc-minLength-valid": "Longitud mínima no alcanzada",
            "cvc-maxLength-valid": "Longitud máxima excedida",
            "cvc-type.3.1.3": "Tipo de dato inválido",
            "cvc-enumeration-valid": "Valor no permitido",
            "cvc-complex-type.2.4.a": "Elemento requerido faltante",
            "cvc-complex-type.2.4.b": "Elemento no permitido",
        }

    def _format_error(self, error: etree._LogEntry) -> str:
        """Formatea un error de validación"""
        error_type = error.type_name
        error_msg = error.message

        # Mapear error a mensaje más amigable
        if error_type in self._error_mappings:
            error_msg = f"{self._error_mappings[error_type]}: {error_msg}"

        return f"Línea {error.line}: {error_msg}"

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
            errors = [self._format_error(error)
                      for error in self.schema.error_log]
            return False, errors

        except etree.XMLSyntaxError as e:
            raise SifenValidationError(f"Error de sintaxis XML: {str(e)}")

    def validate_ruc(self, ruc: str) -> bool:
        """
        Valida formato de RUC

        Args:
            ruc: RUC a validar

        Returns:
            bool: True si el RUC es válido
        """
        if not ruc.isdigit() or len(ruc) not in (8, 9):
            return False
        return True

    def validate_dv(self, dv: str) -> bool:
        """
        Valida dígito verificador

        Args:
            dv: Dígito verificador a validar

        Returns:
            bool: True si el DV es válido
        """
        return dv.isdigit() and len(dv) == 1
