"""
Tests modulares para validación de schemas XSD DE_v150.xsd

Este módulo implementa tests unitarios y de integración para validar
los diferentes fragmentos modulares del schema principal DE_v150.xsd,
asegurando que cada componente funcione correctamente tanto de forma
individual como integrada.

Funcionalidades:
- Tests unitarios por módulo de schema
- Tests de integración entre módulos  
- Validación de tipos de datos específicos
- Tests de compatibilidad y resolución de dependencias

Autor: Sistema de Facturación Electrónica
Versión: 1.5.0
"""

import pytest
import os
from lxml import etree
from typing import Tuple, List, Dict, Any
from pathlib import Path


class SchemaModuleValidator:
    """Validador específico para testing de módulos de schema"""

    def __init__(self, schema_base_path: str | Path | None = None):
        """
        Inicializa el validador con la ruta base de los schemas

        Args:
            schema_base_path: Ruta base donde se encuentran los schemas XSD
        """
        if schema_base_path is None:
            # Obtener ruta desde el directorio actual del test
            current_dir = Path(__file__).parent.parent
            schema_base_path = current_dir

        self.schema_base_path = Path(schema_base_path)
        self.main_schema_path = self.schema_base_path / "DE_v150.xsd"
        self._schema_cache = {}

    def load_schema(self, schema_file: str | None = None) -> etree.XMLSchema:
        """
        Carga un schema XSD específico con cache

        Args:
            schema_file: Archivo de schema específico o None para el principal

        Returns:
            XMLSchema: Schema cargado y parseado

        Raises:
            FileNotFoundError: Si el archivo de schema no existe
            etree.XMLSyntaxError: Si hay errores de sintaxis en el schema
        """
        if schema_file is None:
            schema_file = "DE_v150.xsd"

        schema_path = self.schema_base_path / schema_file

        if schema_file not in self._schema_cache:
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema no encontrado: {schema_path}")

            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_doc = etree.parse(f, etree.XMLParser())
                self._schema_cache[schema_file] = etree.XMLSchema(schema_doc)
            except etree.XMLSyntaxError as e:
                raise ValueError(
                    f"Error de sintaxis en schema {schema_file}: {e}")

        return self._schema_cache[schema_file]

    def validate_xml_fragment(self, xml_content: str, wrap_element: str | None = None) -> Tuple[bool, List[str]]:
        """
        Valida un fragmento XML contra el schema principal

        Args:
            xml_content: Contenido XML a validar
            wrap_element: Elemento contenedor si es necesario

        Returns:
            Tuple[bool, List[str]]: (es_valido, lista_errores)
        """
        try:
            # Envolver el fragmento si es necesario
            if wrap_element:
                xml_content = f'<{wrap_element} xmlns="http://ekuatia.set.gov.py/sifen/xsd">{xml_content}</{wrap_element}>'

            # Parsear el XML
            doc = etree.fromstring(
                xml_content.encode('utf-8'), etree.XMLParser())

            # Cargar y validar con el schema principal
            schema = self.load_schema()
            is_valid = schema.validate(doc)

            # Extraer errores detallados
            errors = [str(error) for error in schema.error_log]

            return is_valid, errors

        except etree.XMLSyntaxError as e:
            return False, [f"Error de sintaxis XML: {e}"]
        except Exception as e:
            return False, [f"Error inesperado: {e}"]

    def validate_complete_document(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Valida un documento XML completo

        Args:
            xml_content: Documento XML completo

        Returns:
            Tuple[bool, List[str]]: (es_valido, lista_errores)
        """
        return self.validate_xml_fragment(xml_content)


class TestSchemaModules:
    """Suite de tests para módulos de schema XSD"""

    @pytest.fixture
    def validator(self):
        """Fixture que proporciona un validador de schemas"""
        return SchemaModuleValidator()

    @pytest.fixture
    def namespace(self):
        """Fixture que proporciona el namespace SIFEN"""
        return "http://ekuatia.set.gov.py/sifen/xsd"


class TestBasicSchemaStructure(TestSchemaModules):
    """Tests para estructura básica del schema"""

    def test_main_schema_loads_successfully(self, validator):
        """
        Test que verifica que el schema principal se carga correctamente
        """
        # Cargar el schema principal
        schema = validator.load_schema()

        # Verificar que se cargó correctamente
        assert schema is not None, "El schema principal no se pudo cargar"

        # Verificar que es una instancia válida de XMLSchema
        assert isinstance(
            schema, etree.XMLSchema), "El objeto cargado no es un XMLSchema válido"

    def test_schema_namespace_is_correct(self, validator, namespace):
        """
        Test que verifica el namespace correcto del schema
        """
        schema_doc = etree.parse(
            str(validator.main_schema_path), etree.XMLParser())
        root = schema_doc.getroot()

        # Verificar namespace target
        target_ns = root.get("targetNamespace")
        assert target_ns == namespace, f"Namespace incorrecto: esperado {namespace}, obtenido {target_ns}"

        # Verificar namespace por defecto
        default_ns = root.nsmap.get(None)
        assert default_ns == "http://www.w3.org/2001/XMLSchema", "Namespace de XMLSchema incorrecto"


class TestDocumentIdentificationTypes(TestSchemaModules):
    """Tests para tipos de identificación de documentos"""

    def test_document_type_valid_values(self, validator):
        """
        Test que valida los tipos de documento permitidos
        """
        valid_types = ["1", "2", "3", "4",
                       "5"]  # Factura, Autofactura, NC, ND, NR

        for doc_type in valid_types:
            xml_fragment = f"""
            <tipoID xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <iTipDE>{doc_type}</iTipDE>
                <dSerieDE>001</dSerieDE>
                <dNumDE>123456</dNumDE>
                <dCoOpe>2025</dCoOpe>
                <dFecEmiDE>2025-06-16</dFecEmiDE>
            </tipoID>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Tipo de documento {doc_type} debería ser válido. Errores: {errors}"

    def test_document_type_invalid_values(self, validator):
        """
        Test que verifica rechazo de tipos de documento inválidos
        """
        invalid_types = ["0", "6", "10", "abc", ""]

        for doc_type in invalid_types:
            xml_fragment = f"""
            <tipoID xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <iTipDE>{doc_type}</iTipDE>
                <dSerieDE>001</dSerieDE>
                <dNumDE>123456</dNumDE>
                <dCoOpe>2025</dCoOpe>
                <dFecEmiDE>2025-06-16</dFecEmiDE>
            </tipoID>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert not is_valid, f"Tipo de documento inválido {doc_type} no debería ser aceptado"

    def test_serie_format_validation(self, validator):
        """
        Test que valida el formato de serie del documento
        """
        # Test series válidas
        valid_series = ["001", "999", "ABC"]
        for serie in valid_series:
            xml_fragment = f"""
            <tipoID xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <iTipDE>1</iTipDE>
                <dSerieDE>{serie}</dSerieDE>
                <dNumDE>123456</dNumDE>
                <dCoOpe>2025</dCoOpe>
                <dFecEmiDE>2025-06-16</dFecEmiDE>
            </tipoID>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Serie {serie} debería ser válida. Errores: {errors}"

    def test_date_format_validation(self, validator):
        """
        Test que valida el formato de fecha
        """
        # Test fechas válidas
        valid_dates = ["2025-06-16", "2024-12-31", "2025-01-01"]
        for date in valid_dates:
            xml_fragment = f"""
            <tipoID xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <iTipDE>1</iTipDE>
                <dSerieDE>001</dSerieDE>
                <dNumDE>123456</dNumDE>
                <dCoOpe>2025</dCoOpe>
                <dFecEmiDE>{date}</dFecEmiDE>
            </tipoID>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Fecha {date} debería ser válida. Errores: {errors}"

        # Test fechas inválidas
        invalid_dates = ["16-06-2025", "2025/06/16", "invalid-date", ""]
        for date in invalid_dates:
            xml_fragment = f"""
            <tipoID xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <iTipDE>1</iTipDE>
                <dSerieDE>001</dSerieDE>
                <dNumDE>123456</dNumDE>
                <dCoOpe>2025</dCoOpe>
                <dFecEmiDE>{date}</dFecEmiDE>
            </tipoID>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert not is_valid, f"Fecha inválida {date} no debería ser aceptada"


class TestIssuerTypes(TestSchemaModules):
    """Tests para tipos de emisor"""

    def test_ruc_format_validation(self, validator):
        """
        Test que valida el formato de RUC del emisor
        """
        # RUCs válidos (8 dígitos con verificador)
        valid_rucs = ["12345678", "87654321", "11111111"]

        for ruc in valid_rucs:
            xml_fragment = f"""
            <tipoEmi xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <dRUCEmi>{ruc}</dRUCEmi>
                <dDVEmi>9</dDVEmi>
                <dNomEmi>Empresa Test SA</dNomEmi>
                <dDirEmi>Calle Falsa 123</dDirEmi>
                <cDepEmi>1</cDepEmi>
                <cCiuEmi>1</cCiuEmi>
                <dDesCiuEmi>Asunción</dDesCiuEmi>
            </tipoEmi>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"RUC {ruc} debería ser válido. Errores: {errors}"

    def test_issuer_name_validation(self, validator):
        """
        Test que valida el nombre del emisor
        """
        # Nombres válidos
        valid_names = [
            "Empresa S.A.",
            "Juan Pérez",
            "Comercial Ñandutí S.R.L.",
            "ABC-123 Distribuidora"
        ]

        for name in valid_names:
            xml_fragment = f"""
            <tipoEmi xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <dRUCEmi>12345678</dRUCEmi>
                <dDVEmi>9</dDVEmi>
                <dNomEmi>{name}</dNomEmi>
                <dDirEmi>Calle Falsa 123</dDirEmi>
                <cDepEmi>1</cDepEmi>
                <cCiuEmi>1</cCiuEmi>
                <dDesCiuEmi>Asunción</dDesCiuEmi>
            </tipoEmi>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Nombre '{name}' debería ser válido. Errores: {errors}"

    def test_address_validation(self, validator):
        """
        Test que valida la dirección del emisor
        """
        valid_addresses = [
            "Av. España 1234",
            "Calle Palma, esquina Estrella",
            "Ruta 2 Km 15.5",
            "Barrio San Roque, Manzana 10"
        ]

        for address in valid_addresses:
            xml_fragment = f"""
            <tipoEmi xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <dRUCEmi>12345678</dRUCEmi>
                <dDVEmi>9</dDVEmi>
                <dNomEmi>Empresa Test</dNomEmi>
                <dDirEmi>{address}</dDirEmi>
                <cDepEmi>1</cDepEmi>
                <cCiuEmi>1</cCiuEmi>
                <dDesCiuEmi>Asunción</dDesCiuEmi>
            </tipoEmi>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Dirección '{address}' debería ser válida. Errores: {errors}"

    def test_phone_format_validation(self, validator):
        """
        Test que valida el formato de teléfono paraguayo
        """
        valid_phones = ["+595981123456", "0981123456", "0212345678"]

        for phone in valid_phones:
            xml_fragment = f"""
            <tipoEmi xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <dRUCEmi>12345678</dRUCEmi>
                <dDVEmi>9</dDVEmi>
                <dNomEmi>Empresa Test</dNomEmi>
                <dDirEmi>Calle Falsa 123</dDirEmi>
                <cDepEmi>1</cDepEmi>
                <cCiuEmi>1</cCiuEmi>
                <dDesCiuEmi>Asunción</dDesCiuEmi>
                <dTelEmi>{phone}</dTelEmi>
            </tipoEmi>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Teléfono {phone} debería ser válido. Errores: {errors}"

    def test_email_format_validation(self, validator):
        """
        Test que valida el formato de email
        """
        valid_emails = [
            "test@empresa.com.py",
            "contacto@example.com",
            "info.ventas@test.com.py"
        ]

        for email in valid_emails:
            xml_fragment = f"""
            <tipoEmi xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <dRUCEmi>12345678</dRUCEmi>
                <dDVEmi>9</dDVEmi>
                <dNomEmi>Empresa Test</dNomEmi>
                <dDirEmi>Calle Falsa 123</dDirEmi>
                <cDepEmi>1</cDepEmi>
                <cCiuEmi>1</cCiuEmi>
                <dDesCiuEmi>Asunción</dDesCiuEmi>
                <dEmailE>{email}</dEmailE>
            </tipoEmi>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Email {email} debería ser válido. Errores: {errors}"


class TestReceiverTypes(TestSchemaModules):
    """Tests para tipos de receptor"""

    def test_receiver_basic_structure(self, validator):
        """
        Test que valida la estructura básica del receptor
        """
        xml_fragment = """
        <tipoRec xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <iTipIDRec>1</iTipIDRec>
            <dNumIDRec>12345678</dNumIDRec>
            <dNomRec>Cliente Test</dNomRec>
            <dDirRec>Dirección Cliente 456</dDirRec>
            <cDepRec>2</cDepRec>
            <cCiuRec>5</cCiuRec>
            <dDesCiuRec>Ciudad del Este</dDesCiuRec>
        </tipoRec>
        """

        is_valid, errors = validator.validate_xml_fragment(xml_fragment)
        assert is_valid, f"Estructura básica de receptor debería ser válida. Errores: {errors}"

    def test_receiver_identification_types(self, validator):
        """
        Test que valida los tipos de identificación del receptor
        """
        # Tipos válidos: 1=RUC, 2=CI, 3=Pasaporte, 4=Extranjero
        valid_id_types = ["1", "2", "3", "4"]

        for id_type in valid_id_types:
            xml_fragment = f"""
            <tipoRec xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <iTipIDRec>{id_type}</iTipIDRec>
                <dNumIDRec>12345678</dNumIDRec>
                <dNomRec>Cliente Test</dNomRec>
                <dDirRec>Dirección Cliente 456</dDirRec>
                <cDepRec>2</cDepRec>
                <cCiuRec>5</cCiuRec>
                <dDesCiuRec>Ciudad del Este</dDesCiuRec>
            </tipoRec>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Tipo de ID {id_type} debería ser válido. Errores: {errors}"


class TestItemTypes(TestSchemaModules):
    """Tests para tipos de items/productos"""

    def test_item_basic_structure(self, validator):
        """
        Test que valida la estructura básica de un item
        """
        xml_fragment = """
        <tipoItem xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dCodPro>PROD-001</dCodPro>
            <dDesPro>Producto de prueba</dDesPro>
            <dCantPro>10.50</dCantPro>
            <dPUniPro>150000</dPUniPro>
            <dTotBruOpe>1575000</dTotBruOpe>
        </tipoItem>
        """

        is_valid, errors = validator.validate_xml_fragment(xml_fragment)
        assert is_valid, f"Estructura básica de item debería ser válida. Errores: {errors}"

    def test_product_code_validation(self, validator):
        """
        Test que valida el código de producto
        """
        valid_codes = ["PROD-001", "ABC123", "X", "A1B2C3D4E5F6G7H8I9J0"]

        for code in valid_codes:
            xml_fragment = f"""
            <tipoItem xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <dCodPro>{code}</dCodPro>
                <dDesPro>Producto de prueba</dDesPro>
                <dCantPro>1.00</dCantPro>
                <dPUniPro>100000</dPUniPro>
                <dTotBruOpe>100000</dTotBruOpe>
            </tipoItem>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Código de producto {code} debería ser válido. Errores: {errors}"

    def test_quantity_validation(self, validator):
        """
        Test que valida las cantidades de productos
        """
        valid_quantities = ["1.00", "0.01", "999999999.99", "123.45"]

        for quantity in valid_quantities:
            xml_fragment = f"""
            <tipoItem xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <dCodPro>PROD-001</dCodPro>
                <dDesPro>Producto de prueba</dDesPro>
                <dCantPro>{quantity}</dCantPro>
                <dPUniPro>100000</dPUniPro>
                <dTotBruOpe>100000</dTotBruOpe>
            </tipoItem>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert is_valid, f"Cantidad {quantity} debería ser válida. Errores: {errors}"

    def test_invalid_quantities(self, validator):
        """
        Test que verifica rechazo de cantidades inválidas
        """
        invalid_quantities = ["0", "-1", "abc", "1000000000.00", ""]

        for quantity in invalid_quantities:
            xml_fragment = f"""
            <tipoItem xmlns="http://ekuatia.set.gov.py/sifen/xsd">
                <dCodPro>PROD-001</dCodPro>
                <dDesPro>Producto de prueba</dDesPro>
                <dCantPro>{quantity}</dCantPro>
                <dPUniPro>100000</dPUniPro>
                <dTotBruOpe>100000</dTotBruOpe>
            </tipoItem>
            """

            is_valid, errors = validator.validate_xml_fragment(xml_fragment)
            assert not is_valid, f"Cantidad inválida {quantity} no debería ser aceptada"


class TestTotalTypes(TestSchemaModules):
    """Tests para tipos de totales"""

    def test_totals_basic_structure(self, validator):
        """
        Test que valida la estructura básica de totales
        """
        xml_fragment = """
        <tipoTot xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dSubExe>0</dSubExe>
            <dSubExo>0</dSubExo>
            <dSub5>500000</dSub5>
            <dSub10>1000000</dSub10>
            <dTotOpe>1500000</dTotOpe>
            <dTotDesc>0</dTotDesc>
            <dTotDescGloItem>0</dTotDescGloItem>
            <dTotAntItem>0</dTotAntItem>
            <dTotAnt>0</dTotAnt>
            <dPorcDescTotal>0</dPorcDescTotal>
            <dDescTotal>0</dDescTotal>
            <dAnticipo>0</dAnticipo>
            <dRedon>0</dRedon>
            <dComi>0</dComi>
            <dTotGralOpe>1500000</dTotGralOpe>
            <dIVA5>50000</dIVA5>
            <dIVA10>100000</dIVA10>
            <dLiqTotIVA5>50000</dLiqTotIVA5>
            <dLiqTotIVA10>100000</dLiqTotIVA10>
            <dIVAComi>0</dIVAComi>
            <dTotIVA>150000</dTotIVA>
            <dBaseGrav5>500000</dBaseGrav5>
            <dBaseGrav10>1000000</dBaseGrav10>
            <dTBasGraIVA>1500000</dTBasGraIVA>
            <dTotalGs>1650000</dTotalGs>
        </tipoTot>
        """

        is_valid, errors = validator.validate_xml_fragment(xml_fragment)
        assert is_valid, f"Estructura básica de totales debería ser válida. Errores: {errors}"


class TestSchemaIntegration(TestSchemaModules):
    """Tests de integración entre módulos"""

    def test_complete_minimal_document(self, validator):
        """
        Test que valida un documento mínimo completo
        """
        complete_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rDE version="1.5.0" xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <DE>
                <gDE>
                    <dID>
                        <iTipDE>1</iTipDE>
                        <dSerieDE>001</dSerieDE>
                        <dNumDE>123456</dNumDE>
                        <dCoOpe>2025</dCoOpe>
                        <dFecEmiDE>2025-06-16</dFecEmiDE>
                    </dID>
                    <dDatG>
                        <iTipOpe>1</iTipOpe>
                        <dMonOpe>PYG</dMonOpe>
                    </dDatG>
                    <dEmi>
                        <dRUCEmi>12345678</dRUCEmi>
                        <dDVEmi>9</dDVEmi>
                        <dNomEmi>Empresa Test</dNomEmi>
                        <dDirEmi>Calle Falsa 123</dDirEmi>
                        <cDepEmi>1</cDepEmi>
                        <cCiuEmi>1</cCiuEmi>
                        <dDesCiuEmi>Asunción</dDesCiuEmi>
                    </dEmi>
                    <dRec>
                        <iTipIDRec>1</iTipIDRec>
                        <dNumIDRec>87654321</dNumIDRec>
                        <dNomRec>Cliente Test</dNomRec>
                        <dDirRec>Dirección Cliente</dDirRec>
                        <cDepRec>1</cDepRec>
                        <cCiuRec>1</cCiuRec>
                        <dDesCiuRec>Asunción</dDesCiuRec>
                    </dRec>
                    <gItem>
                        <dCodPro>PROD-001</dCodPro>
                        <dDesPro>Producto de prueba</dDesPro>
                        <dCantPro>1.00</dCantPro>
                        <dPUniPro>100000</dPUniPro>
                        <dTotBruOpe>100000</dTotBruOpe>
                    </gItem>
                    <dTot>
                        <dSubExe>0</dSubExe>
                        <dSubExo>0</dSubExo>
                        <dSub5>0</dSub5>
                        <dSub10>100000</dSub10>
                        <dTotOpe>100000</dTotOpe>
                        <dTotDesc>0</dTotDesc>
                        <dTotDescGloItem>0</dTotDescGloItem>
                        <dTotAntItem>0</dTotAntItem>
                        <dTotAnt>0</dTotAnt>
                        <dPorcDescTotal>0</dPorcDescTotal>
                        <dDescTotal>0</dDescTotal>
                        <dAnticipo>0</dAnticipo>
                        <dRedon>0</dRedon>
                        <dComi>0</dComi>
                        <dTotGralOpe>100000</dTotGralOpe>
                        <dIVA5>0</dIVA5>
                        <dIVA10>10000</dIVA10>
                        <dLiqTotIVA5>0</dLiqTotIVA5>
                        <dLiqTotIVA10>10000</dLiqTotIVA10>
                        <dIVAComi>0</dIVAComi>
                        <dTotIVA>10000</dTotIVA>
                        <dBaseGrav5>0</dBaseGrav5>
                        <dBaseGrav10>100000</dBaseGrav10>
                        <dTBasGraIVA>100000</dTBasGraIVA>
                        <dTotalGs>110000</dTotalGs>
                    </dTot>
                </gDE>
            </DE>
        </rDE>
        """

        is_valid, errors = validator.validate_complete_document(complete_xml)
        assert is_valid, f"Documento mínimo completo debería ser válido. Errores: {errors}"

    def test_cross_module_type_resolution(self, validator):
        """
        Test que verifica la resolución de tipos entre módulos
        """
        # Este test verifica que los tipos definidos en diferentes partes
        # del schema se resuelvan correctamente cuando se usan juntos

        # Fragmento que usa tipos de múltiples módulos
        xml_fragment = """
        <gDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dID>
                <iTipDE>1</iTipDE>
                <dSerieDE>001</dSerieDE>
                <dNumDE>123456</dNumDE>
                <dCoOpe>2025</dCoOpe>
                <dFecEmiDE>2025-06-16</dFecEmiDE>
            </dID>
            <dDatG>
                <iTipOpe>1</iTipOpe>
                <dMonOpe>PYG</dMonOpe>
            </dDatG>
            <dEmi>
                <dRUCEmi>12345678</dRUCEmi>
                <dDVEmi>9</dDVEmi>
                <dNomEmi>Empresa Test</dNomEmi>
                <dDirEmi>Calle Test 123</dDirEmi>
                <cDepEmi>1</cDepEmi>
                <cCiuEmi>1</cCiuEmi>
                <dDesCiuEmi>Asunción</dDesCiuEmi>
            </dEmi>
            <dRec>
                <iTipIDRec>2</iTipIDRec>
                <dNumIDRec>1234567</dNumIDRec>
                <dNomRec>Juan Pérez</dNomRec>
                <dDirRec>Av. España 456</dDirRec>
                <cDepRec>1</cDepRec>
                <cCiuRec>1</cCiuRec>
                <dDesCiuRec>Asunción</dDesCiuRec>
            </dRec>
            <gItem>
                <dCodPro>SERV-001</dCodPro>
                <dDesPro>Servicio de consultoría</dDesPro>
                <dCantPro>5.00</dCantPro>
                <dPUniPro>200000</dPUniPro>
                <dTotBruOpe>1000000</dTotBruOpe>
            </gItem>
            <dTot>
                <dSubExe>0</dSubExe>
                <dSubExo>0</dSubExo>
                <dSub5>0</dSub5>
                <dSub10>1000000</dSub10>
                <dTotOpe>1000000</dTotOpe>
                <dTotDesc>0</dTotDesc>
                <dTotDescGloItem>0</dTotDescGloItem>
                <dTotAntItem>0</dTotAntItem>
                <dTotAnt>0</dTotAnt>
                <dPorcDescTotal>0</dPorcDescTotal>
                <dDescTotal>0</dDescTotal>
                <dAnticipo>0</dAnticipo>
                <dRedon>0</dRedon>
                <dComi>0</dComi>
                <dTotGralOpe>1000000</dTotGralOpe>
                <dIVA5>0</dIVA5>
                <dIVA10>100000</dIVA10>
                <dLiqTotIVA5>0</dLiqTotIVA5>
                <dLiqTotIVA10>100000</dLiqTotIVA10>
                <dIVAComi>0</dIVAComi>
                <dTotIVA>100000</dTotIVA>
                <dBaseGrav5>0</dBaseGrav5>
                <dBaseGrav10>1000000</dBaseGrav10>
                <dTBasGraIVA>1000000</dTBasGraIVA>
                <dTotalGs>1100000</dTotalGs>
            </dTot>
        </gDE>
        """

        is_valid, errors = validator.validate_xml_fragment(
            xml_fragment, wrap_element="DE")
        assert is_valid, f"Resolución de tipos entre módulos falló. Errores: {errors}"

    def test_multiple_items_validation(self, validator):
        """
        Test que valida documentos con múltiples items
        """
        xml_fragment = """
        <gDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dID>
                <iTipDE>1</iTipDE>
                <dSerieDE>001</dSerieDE>
                <dNumDE>789012</dNumDE>
                <dCoOpe>2025</dCoOpe>
                <dFecEmiDE>2025-06-16</dFecEmiDE>
            </dID>
            <dDatG>
                <iTipOpe>1</iTipOpe>
                <dMonOpe>PYG</dMonOpe>
            </dDatG>
            <dEmi>
                <dRUCEmi>12345678</dRUCEmi>
                <dDVEmi>9</dDVEmi>
                <dNomEmi>Comercial ABC</dNomEmi>
                <dDirEmi>Av. Principal 789</dDirEmi>
                <cDepEmi>1</cDepEmi>
                <cCiuEmi>1</cCiuEmi>
                <dDesCiuEmi>Asunción</dDesCiuEmi>
            </dEmi>
            <dRec>
                <iTipIDRec>1</iTipIDRec>
                <dNumIDRec>98765432</dNumIDRec>
                <dNomRec>Distribuidora XYZ</dNomRec>
                <dDirRec>Ruta 1 Km 20</dDirRec>
                <cDepRec>2</cDepRec>
                <cCiuRec>10</cCiuRec>
                <dDesCiuRec>San Lorenzo</dDesCiuRec>
            </dRec>
            <gItem>
                <dCodPro>PROD-A001</dCodPro>
                <dDesPro>Producto Alpha</dDesPro>
                <dCantPro>2.00</dCantPro>
                <dPUniPro>250000</dPUniPro>
                <dTotBruOpe>500000</dTotBruOpe>
            </gItem>
            <gItem>
                <dCodPro>PROD-B002</dCodPro>
                <dDesPro>Producto Beta</dDesPro>
                <dCantPro>3.50</dCantPro>
                <dPUniPro>180000</dPUniPro>
                <dTotBruOpe>630000</dTotBruOpe>
            </gItem>
            <gItem>
                <dCodPro>SERV-C003</dCodPro>
                <dDesPro>Servicio Gamma</dDesPro>
                <dCantPro>1.00</dCantPro>
                <dPUniPro>370000</dPUniPro>
                <dTotBruOpe>370000</dTotBruOpe>
            </gItem>
            <dTot>
                <dSubExe>0</dSubExe>
                <dSubExo>370000</dSubExo>
                <dSub5>500000</dSub5>
                <dSub10>630000</dSub10>
                <dTotOpe>1500000</dTotOpe>
                <dTotDesc>0</dTotDesc>
                <dTotDescGloItem>0</dTotDescGloItem>
                <dTotAntItem>0</dTotAntItem>
                <dTotAnt>0</dTotAnt>
                <dPorcDescTotal>0</dPorcDescTotal>
                <dDescTotal>0</dDescTotal>
                <dAnticipo>0</dAnticipo>
                <dRedon>0</dRedon>
                <dComi>0</dComi>
                <dTotGralOpe>1500000</dTotGralOpe>
                <dIVA5>25000</dIVA5>
                <dIVA10>63000</dIVA10>
                <dLiqTotIVA5>25000</dLiqTotIVA5>
                <dLiqTotIVA10>63000</dLiqTotIVA10>
                <dIVAComi>0</dIVAComi>
                <dTotIVA>88000</dTotIVA>
                <dBaseGrav5>500000</dBaseGrav5>
                <dBaseGrav10>630000</dBaseGrav10>
                <dTBasGraIVA>1130000</dTBasGraIVA>
                <dTotalGs>1588000</dTotalGs>
            </dTot>
        </gDE>
        """

        is_valid, errors = validator.validate_xml_fragment(
            xml_fragment, wrap_element="DE")
        assert is_valid, f"Documento con múltiples items debería ser válido. Errores: {errors}"


class TestSchemaPerformance(TestSchemaModules):
    """Tests de performance para schemas modulares"""

    def test_schema_loading_performance(self, validator):
        """
        Test que verifica el tiempo de carga del schema
        """
        import time

        start_time = time.time()
        schema = validator.load_schema()
        load_time = time.time() - start_time

        # El schema debería cargar en menos de 2 segundos
        assert load_time < 2.0, f"Schema se demora demasiado en cargar: {load_time:.2f}s"
        assert schema is not None, "Schema no se cargó correctamente"

    def test_validation_performance(self, validator):
        """
        Test que verifica el tiempo de validación
        """
        import time

        # XML de prueba completo
        test_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rDE version="1.5.0" xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <DE>
                <gDE>
                    <dID>
                        <iTipDE>1</iTipDE>
                        <dSerieDE>001</dSerieDE>
                        <dNumDE>999999</dNumDE>
                        <dCoOpe>2025</dCoOpe>
                        <dFecEmiDE>2025-06-16</dFecEmiDE>
                    </dID>
                    <dDatG>
                        <iTipOpe>1</iTipOpe>
                        <dMonOpe>PYG</dMonOpe>
                    </dDatG>
                    <dEmi>
                        <dRUCEmi>80012345</dRUCEmi>
                        <dDVEmi>6</dDVEmi>
                        <dNomEmi>Test Performance SA</dNomEmi>
                        <dDirEmi>Av. Performance 1000</dDirEmi>
                        <cDepEmi>1</cDepEmi>
                        <cCiuEmi>1</cCiuEmi>
                        <dDesCiuEmi>Asunción</dDesCiuEmi>
                    </dEmi>
                    <dRec>
                        <iTipIDRec>1</iTipIDRec>
                        <dNumIDRec>80098765</dNumIDRec>
                        <dNomRec>Cliente Performance</dNomRec>
                        <dDirRec>Calle Test 500</dDirRec>
                        <cDepRec>1</cDepRec>
                        <cCiuRec>1</cCiuRec>
                        <dDesCiuRec>Asunción</dDesCiuRec>
                    </dRec>
                    <gItem>
                        <dCodPro>PERF-001</dCodPro>
                        <dDesPro>Item de performance</dDesPro>
                        <dCantPro>1.00</dCantPro>
                        <dPUniPro>500000</dPUniPro>
                        <dTotBruOpe>500000</dTotBruOpe>
                    </gItem>
                    <dTot>
                        <dSubExe>0</dSubExe>
                        <dSubExo>0</dSubExo>
                        <dSub5>0</dSub5>
                        <dSub10>500000</dSub10>
                        <dTotOpe>500000</dTotOpe>
                        <dTotDesc>0</dTotDesc>
                        <dTotDescGloItem>0</dTotDescGloItem>
                        <dTotAntItem>0</dTotAntItem>
                        <dTotAnt>0</dTotAnt>
                        <dPorcDescTotal>0</dPorcDescTotal>
                        <dDescTotal>0</dDescTotal>
                        <dAnticipo>0</dAnticipo>
                        <dRedon>0</dRedon>
                        <dComi>0</dComi>
                        <dTotGralOpe>500000</dTotGralOpe>
                        <dIVA5>0</dIVA5>
                        <dIVA10>50000</dIVA10>
                        <dLiqTotIVA5>0</dLiqTotIVA5>
                        <dLiqTotIVA10>50000</dLiqTotIVA10>
                        <dIVAComi>0</dIVAComi>
                        <dTotIVA>50000</dTotIVA>
                        <dBaseGrav5>0</dBaseGrav5>
                        <dBaseGrav10>500000</dBaseGrav10>
                        <dTBasGraIVA>500000</dTBasGraIVA>
                        <dTotalGs>550000</dTotalGs>
                    </dTot>
                </gDE>
            </DE>
        </rDE>
        """

        # Medir tiempo de validación
        start_time = time.time()
        is_valid, errors = validator.validate_complete_document(test_xml)
        validation_time = time.time() - start_time

        # La validación debería tomar menos de 1 segundo
        assert validation_time < 1.0, f"Validación muy lenta: {validation_time:.2f}s"
        assert is_valid, f"El XML de prueba debería ser válido. Errores: {errors}"


class TestSchemaErrorHandling(TestSchemaModules):
    """Tests para manejo de errores en schemas"""

    def test_missing_required_elements(self, validator):
        """
        Test que verifica detección de elementos requeridos faltantes
        """
        # XML sin elemento requerido (dNomEmi)
        invalid_xml = """
        <tipoEmi xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dRUCEmi>12345678</dRUCEmi>
            <dDVEmi>9</dDVEmi>
            <!-- dNomEmi faltante -->
            <dDirEmi>Calle Test 123</dDirEmi>
            <cDepEmi>1</cDepEmi>
            <cCiuEmi>1</cCiuEmi>
            <dDesCiuEmi>Asunción</dDesCiuEmi>
        </tipoEmi>
        """

        is_valid, errors = validator.validate_xml_fragment(invalid_xml)
        assert not is_valid, "XML con elemento faltante debería ser inválido"
        assert len(errors) > 0, "Deberían reportarse errores específicos"

    def test_invalid_data_types(self, validator):
        """
        Test que verifica detección de tipos de datos inválidos
        """
        # XML con tipo de dato inválido (fecha mal formateada)
        invalid_xml = """
        <tipoID xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <iTipDE>1</iTipDE>
            <dSerieDE>001</dSerieDE>
            <dNumDE>123456</dNumDE>
            <dCoOpe>2025</dCoOpe>
            <dFecEmiDE>16/06/2025</dFecEmiDE> <!-- Formato incorrecto -->
        </tipoID>
        """

        is_valid, errors = validator.validate_xml_fragment(invalid_xml)
        assert not is_valid, "XML con formato de fecha incorrecto debería ser inválido"
        assert len(errors) > 0, "Deberían reportarse errores de formato"

    def test_pattern_validation_errors(self, validator):
        """
        Test que verifica errores de validación de patrones
        """
        # XML con patrón inválido (RUC con caracteres no numéricos)
        invalid_xml = """
        <tipoEmi xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dRUCEmi>ABC12345</dRUCEmi> <!-- Patrón inválido -->
            <dDVEmi>9</dDVEmi>
            <dNomEmi>Empresa Test</dNomEmi>
            <dDirEmi>Calle Test 123</dDirEmi>
            <cDepEmi>1</cDepEmi>
            <cCiuEmi>1</cCiuEmi>
            <dDesCiuEmi>Asunción</dDesCiuEmi>
        </tipoEmi>
        """

        is_valid, errors = validator.validate_xml_fragment(invalid_xml)
        assert not is_valid, "XML con patrón inválido debería ser rechazado"
        assert len(errors) > 0, "Deberían reportarse errores de patrón"


class TestSchemaEdgeCases(TestSchemaModules):
    """Tests para casos límite en schemas"""

    def test_maximum_length_values(self, validator):
        """
        Test que verifica valores en el límite máximo permitido
        """
        # Descripción de producto con máximo de caracteres permitidos (200)
        max_description = "A" * 200

        xml_fragment = f"""
        <tipoItem xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dCodPro>MAX-TEST</dCodPro>
            <dDesPro>{max_description}</dDesPro>
            <dCantPro>1.00</dCantPro>
            <dPUniPro>100000</dPUniPro>
            <dTotBruOpe>100000</dTotBruOpe>
        </tipoItem>
        """

        is_valid, errors = validator.validate_xml_fragment(xml_fragment)
        assert is_valid, f"Descripción de máxima longitud debería ser válida. Errores: {errors}"

    def test_minimum_length_values(self, validator):
        """
        Test que verifica valores en el límite mínimo permitido
        """
        # Código de producto con mínimo de caracteres (1)
        xml_fragment = """
        <tipoItem xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dCodPro>A</dCodPro>
            <dDesPro>Producto mínimo</dDesPro>
            <dCantPro>0.01</dCantPro>
            <dPUniPro>100</dPUniPro>
            <dTotBruOpe>1</dTotBruOpe>
        </tipoItem>
        """

        is_valid, errors = validator.validate_xml_fragment(xml_fragment)
        assert is_valid, f"Valores mínimos deberían ser válidos. Errores: {errors}"

    def test_decimal_precision_limits(self, validator):
        """
        Test que verifica límites de precisión decimal
        """
        # Cantidad con máxima precisión decimal (2 dígitos)
        xml_fragment = """
        <tipoItem xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dCodPro>DECIMAL-TEST</dCodPro>
            <dDesPro>Test precisión decimal</dDesPro>
            <dCantPro>999999999.99</dCantPro>
            <dPUniPro>1</dPUniPro>
            <dTotBruOpe>999999999</dTotBruOpe>
        </tipoItem>
        """

        is_valid, errors = validator.validate_xml_fragment(xml_fragment)
        assert is_valid, f"Máxima precisión decimal debería ser válida. Errores: {errors}"


# Configuración para pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# Fixtures adicionales para uso en otros tests
@pytest.fixture(scope="session")
def schema_validator():
    """Fixture de sesión que proporciona un validador de schemas reutilizable"""
    return SchemaModuleValidator()


@pytest.fixture(scope="session")
def sample_valid_invoice():
    """Fixture que proporciona un XML de factura válida de muestra"""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rDE version="1.5.0" xmlns="http://ekuatia.set.gov.py/sifen/xsd">
        <DE>
            <gDE>
                <dID>
                    <iTipDE>1</iTipDE>
                    <dSerieDE>001</dSerieDE>
                    <dNumDE>555666</dNumDE>
                    <dCoOpe>2025</dCoOpe>
                    <dFecEmiDE>2025-06-16</dFecEmiDE>
                </dID>
                <dDatG>
                    <iTipOpe>1</iTipOpe>
                    <dMonOpe>PYG</dMonOpe>
                </dDatG>
                <dEmi>
                    <dRUCEmi>80012345</dRUCEmi>
                    <dDVEmi>6</dDVEmi>
                    <dNomEmi>Empresa Sample SRL</dNomEmi>
                    <dDirEmi>Av. Sample 123, Local 10</dDirEmi>
                    <cDepEmi>1</cDepEmi>
                    <cCiuEmi>1</cCiuEmi>
                    <dDesCiuEmi>Asunción</dDesCiuEmi>
                    <dTelEmi>+595212345678</dTelEmi>
                    <dEmailE>ventas@sample.com.py</dEmailE>
                </dEmi>
                <dRec>
                    <iTipIDRec>1</iTipIDRec>
                    <dNumIDRec>80098765</dNumIDRec>
                    <dNomRec>Cliente Sample SA</dNomRec>
                    <dDirRec>Calle Cliente 456</dDirRec>
                    <cDepRec>1</cDepRec>
                    <cCiuRec>1</cCiuRec>
                    <dDesCiuRec>Asunción</dDesCiuRec>
                    <dTelRec>+595981234567</dTelRec>
                    <dEmailRec>compras@cliente.com.py</dEmailRec>
                </dRec>
                <gItem>
                    <dCodPro>SAMPLE-001</dCodPro>
                    <dDesPro>Producto de muestra para testing</dDesPro>
                    <dCantPro>2.50</dCantPro>
                    <dPUniPro>400000</dPUniPro>
                    <dTotBruOpe>1000000</dTotBruOpe>
                </gItem>
                <dTot>
                    <dSubExe>0</dSubExe>
                    <dSubExo>0</dSubExo>
                    <dSub5>0</dSub5>
                    <dSub10>1000000</dSub10>
                    <dTotOpe>1000000</dTotOpe>
                    <dTotDesc>0</dTotDesc>
                    <dTotDescGloItem>0</dTotDescGloItem>
                    <dTotAntItem>0</dTotAntItem>
                    <dTotAnt>0</dTotAnt>
                    <dPorcDescTotal>0</dPorcDescTotal>
                    <dDescTotal>0</dDescTotal>
                    <dAnticipo>0</dAnticipo>
                    <dRedon>0</dRedon>
                    <dComi>0</dComi>
                    <dTotGralOpe>1000000</dTotGralOpe>
                    <dIVA5>0</dIVA5>
                    <dIVA10>100000</dIVA10>
                    <dLiqTotIVA5>0</dLiqTotIVA5>
                    <dLiqTotIVA10>100000</dLiqTotIVA10>
                    <dIVAComi>0</dIVAComi>
                    <dTotIVA>100000</dTotIVA>
                    <dBaseGrav5>0</dBaseGrav5>
                    <dBaseGrav10>1000000</dBaseGrav10>
                    <dTBasGraIVA>1000000</dTBasGraIVA>
                    <dTotalGs>1100000</dTotalGs>
                </dTot>
            </gDE>
        </DE>
    </rDE>
    """
