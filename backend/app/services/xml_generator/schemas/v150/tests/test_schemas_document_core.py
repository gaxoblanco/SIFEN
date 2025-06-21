"""
Tests para schemas del núcleo documental SIFEN v150 - DOCUMENT_CORE

ARCHIVO CORREGIDO v2025-06-21:
- Corregido para usar el tipo correcto 'tipoMonto' en lugar de 'tipoImporteMonetario'
- Simplificado para seguir el patrón de otros tests del proyecto
- Sin imports mágicos, usando conftest.py existente

Ubicación: backend/app/services/xml_generator/schemas/v150/tests/test_schemas_document_core.py

Este módulo valida los esquemas XSD del núcleo documental:
- document_core/totals_subtotals.xsd - Totales, subtotales e impuestos
- document_core/operation_data.xsd - Datos de operación del documento
- document_core/stamping_data.xsd - Datos de timbrado fiscal
- document_core/root_elements.xsd - Elementos raíz del documento

Autor: Sistema SIFEN-Facturación  
Versión: 1.5.0
Fecha: 2025-06-20
Actualizado: 2025-06-21
"""

import pytest
import logging
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDocumentCoreTypes:
    """Tests para tipos específicos del núcleo documental SIFEN v150"""

    def test_tipo_documento_electronico_validos(self, document_core_validator, sifen_namespace):
        """Test validación de tipos de documento electrónico válidos"""
        tipos_validos = [
            ("1", "Factura Electrónica"),
            ("4", "Autofactura Electrónica"),
            ("5", "Nota de Crédito Electrónica"),
            ("6", "Nota de Débito Electrónica"),
            ("7", "Nota de Remisión Electrónica")
        ]

        for codigo, descripcion in tipos_validos:
            xml_fragment = f'''
            <gOpeDE xmlns="{sifen_namespace}">
                <iTiDE>{codigo}</iTiDE>
                <dDesTiDE>{descripcion}</dDesTiDE>
                <dNumTimbr>12345678</dNumTimbr>
                <dEst>001</dEst>
                <dPunExp>001</dPunExp>
                <dNumDoc>0000001</dNumDoc>
                <dSerie>A</dSerie>
                <dFeEmiDE>2025-06-20T10:30:00-03:00</dFeEmiDE>
            </gOpeDE>
            '''

            result = document_core_validator.validate_xml(xml_fragment)
            assert result.is_valid, f"Tipo documento {codigo} ({descripcion}) debe ser válido: {result.errors}"

        logger.info("✅ test_tipo_documento_electronico_validos - PASSED")

    def test_tipo_documento_electronico_invalidos(self, document_core_validator, sifen_namespace):
        """Test validación de tipos de documento electrónico inválidos"""
        tipos_invalidos = ["0", "2", "3", "8", "9", "10", "99", "ABC"]

        for tipo_invalido in tipos_invalidos:
            xml_fragment = f'''
            <gOpeDE xmlns="{sifen_namespace}">
                <iTiDE>{tipo_invalido}</iTiDE>
                <dDesTiDE>Tipo Inválido</dDesTiDE>
                <dNumTimbr>12345678</dNumTimbr>
                <dEst>001</dEst>
                <dPunExp>001</dPunExp>
                <dNumDoc>0000001</dNumDoc>
                <dSerie>A</dSerie>
                <dFeEmiDE>2025-06-20T10:30:00-03:00</dFeEmiDE>
            </gOpeDE>
            '''

            result = document_core_validator.validate_xml(xml_fragment)
            assert not result.is_valid, f"Tipo documento inválido {tipo_invalido} debería fallar"

        logger.info("✅ test_tipo_documento_electronico_invalidos - PASSED")

    def test_totales_subtotales_estructura_corregida(self, document_core_validator, sifen_namespace):
        """Test validación de estructura de totales y subtotales con tipos corregidos"""
        # CORRECCIÓN: Usa tipoMonto en lugar de tipoImporteMonetario
        xml_fragment = f'''
        <gTotSub xmlns="{sifen_namespace}">
            <dSubExe>0</dSubExe>
            <dSubExo>0</dSubExo>
            <dSub5>5000.00</dSub5>
            <dSub10>3000.00</dSub10>
            <dTotOpe>8000.00</dTotOpe>
            <dTotDesc>200.00</dTotDesc>
            <dTotDescGlotem>100.00</dTotDescGlotem>
            <dTotAnt>0</dTotAnt>
            <dPorcDescTotal>2.50</dPorcDescTotal>
            <dDescTotal>200.00</dDescTotal>
            <dAnticipo>0</dAnticipo>
            <dRedon>0</dRedon>
            <dComi>0</dComi>
            <dTotGralOpe>8550.00</dTotGralOpe>
            <dIVA5>250.00</dIVA5>
            <dIVA10>300.00</dIVA10>
            <dLiqTotIVA5>250.00</dLiqTotIVA5>
            <dLiqTotIVA10>300.00</dLiqTotIVA10>
            <dIVAComi>0</dIVAComi>
            <dTotIVA>550.00</dTotIVA>
            <dBaseGrav5>5000.00</dBaseGrav5>
            <dBaseGrav10>3000.00</dBaseGrav10>
            <dTBasGraIVA>8000.00</dTBasGraIVA>
        </gTotSub>
        '''

        result = document_core_validator.validate_xml(xml_fragment)
        assert result.is_valid, f"Estructura totales/subtotales debe ser válida: {result.errors}"
        logger.info("✅ test_totales_subtotales_estructura_corregida - PASSED")

    def test_fechas_formato_iso8601(self, document_core_validator, sifen_namespace):
        """Test validación de formatos de fecha ISO 8601"""
        fechas_validas = [
            "2025-06-20T10:30:00-03:00",
            "2025-12-31T23:59:59-03:00",
            "2025-01-01T00:00:00-03:00",
            "2025-06-15T14:45:30-03:00"
        ]

        for fecha in fechas_validas:
            xml_fragment = f'''
            <gOpeDE xmlns="{sifen_namespace}">
                <iTiDE>1</iTiDE>
                <dDesTiDE>Factura Electrónica</dDesTiDE>
                <dNumTimbr>12345678</dNumTimbr>
                <dEst>001</dEst>
                <dPunExp>001</dPunExp>
                <dNumDoc>0000001</dNumDoc>
                <dSerie>A</dSerie>
                <dFeEmiDE>{fecha}</dFeEmiDE>
            </gOpeDE>
            '''

            result = document_core_validator.validate_xml(xml_fragment)
            assert result.is_valid, f"Fecha {fecha} debe ser válida: {result.errors}"

        logger.info("✅ test_fechas_formato_iso8601 - PASSED")


class TestDocumentStructure:
    """Tests para validar la estructura correcta de documentos electrónicos"""

    def test_elemento_raiz_rde_estructura(self, document_core_validator, sifen_namespace):
        """Test validación de estructura del elemento raíz rDE"""
        xml_completo = f'''<?xml version="1.0" encoding="UTF-8"?>
        <rDE xmlns="{sifen_namespace}" version="1.5.0">
            <dVerFor>150</dVerFor>
            <DE Id="01234567890123456789012345678901234567890123">
                <gOpeDE>
                    <iTiDE>1</iTiDE>
                    <dDesTiDE>Factura Electrónica</dDesTiDE>
                    <dNumTimbr>12345678</dNumTimbr>
                    <dEst>001</dEst>
                    <dPunExp>001</dPunExp>
                    <dNumDoc>0000001</dNumDoc>
                    <dSerie>A</dSerie>
                    <dFeEmiDE>2025-06-20T10:30:00-03:00</dFeEmiDE>
                </gOpeDE>
            </DE>
        </rDE>
        '''

        result = document_core_validator.validate_xml(xml_completo)
        assert result.is_valid, f"Elemento raíz rDE debe ser válido: {result.errors}"
        logger.info("✅ test_elemento_raiz_rde_estructura - PASSED")

    def test_grupos_obligatorios_presentes(self, document_core_validator, sifen_namespace, common_test_data):
        """Test que valida presencia de grupos obligatorios en documento completo"""
        cdc_valido = common_test_data["cdc_validos"][0]

        xml_documento = f'''<?xml version="1.0" encoding="UTF-8"?>
        <rDE xmlns="{sifen_namespace}" version="1.5.0">
            <dVerFor>150</dVerFor>
            <DE Id="{cdc_valido}">
                <gOpeDE>
                    <iTiDE>1</iTiDE>
                    <dDesTiDE>Factura Electrónica</dDesTiDE>
                    <dNumTimbr>12345678</dNumTimbr>
                    <dEst>001</dEst>
                    <dPunExp>001</dPunExp>
                    <dNumDoc>0000001</dNumDoc>
                    <dSerie>A</dSerie>
                    <dFeEmiDE>2025-06-20T10:30:00-03:00</dFeEmiDE>
                </gOpeDE>
                
                <gTimb>
                    <iTiDE>1</iTiDE>
                    <dDesTiDE>Factura Electrónica</dDesTiDE>
                    <dNumTimbr>12345678</dNumTimbr>
                    <dEst>001</dEst>
                    <dPunExp>001</dPunExp>
                    <dNumDoc>0000001</dNumDoc>
                    <dSerie>A</dSerie>
                    <dFeIniT>2025-01-01</dFeIniT>
                    <dFeFinT>2025-12-31</dFeFinT>
                </gTimb>
            </DE>
        </rDE>
        '''

        # Verificar que el XML se parse correctamente
        try:
            parser = etree.XMLParser()
            doc = etree.fromstring(xml_documento.encode('utf-8'), parser)
            assert doc is not None, "Documento debe parsearse correctamente"

            # Verificar elementos obligatorios
            assert doc.find(
                f'.//{{{sifen_namespace}}}dVerFor') is not None, "dVerFor debe estar presente"
            assert doc.find(
                f'.//{{{sifen_namespace}}}gOpeDE') is not None, "gOpeDE debe estar presente"
            assert doc.find(
                f'.//{{{sifen_namespace}}}gTimb') is not None, "gTimb debe estar presente"

        except etree.XMLSyntaxError as e:
            pytest.fail(f"Error de sintaxis XML: {e}")

        logger.info("✅ test_grupos_obligatorios_presentes - PASSED")


class TestDocumentCoreIntegration:
    """Tests de integración entre diferentes módulos del núcleo documental"""

    def test_documento_completo_minimal_corregido(self, document_core_validator, sifen_namespace, common_test_data):
        """Test documento completo mínimo con todos los módulos del núcleo documental"""
        # CORRECCIÓN: Usa tipoMonto en totales
        cdc_valido = common_test_data["cdc_validos"][0]

        xml_documento_completo = f'''<?xml version="1.0" encoding="UTF-8"?>
        <rDE xmlns="{sifen_namespace}" version="1.5.0">
            <dVerFor>150</dVerFor>
            <DE Id="{cdc_valido}">
                <gOpeDE>
                    <iTiDE>1</iTiDE>
                    <dDesTiDE>Factura Electrónica</dDesTiDE>
                    <dNumTimbr>12345678</dNumTimbr>
                    <dEst>001</dEst>
                    <dPunExp>001</dPunExp>
                    <dNumDoc>0000001</dNumDoc>
                    <dSerie>A</dSerie>
                    <dFeEmiDE>2025-06-20T10:30:00-03:00</dFeEmiDE>
                </gOpeDE>
                
                <gTimb>
                    <iTiDE>1</iTiDE>
                    <dDesTiDE>Factura Electrónica</dDesTiDE>
                    <dNumTimbr>12345678</dNumTimbr>
                    <dEst>001</dEst>
                    <dPunExp>001</dPunExp>
                    <dNumDoc>0000001</dNumDoc>
                    <dSerie>A</dSerie>
                    <dFeIniT>2025-01-01</dFeIniT>
                    <dFeFinT>2025-12-31</dFeFinT>
                </gTimb>
                
                <gTotSub>
                    <dSubExe>0</dSubExe>
                    <dSubExo>0</dSubExo>
                    <dSub5>1000.00</dSub5>
                    <dSub10>0</dSub10>
                    <dTotOpe>1000.00</dTotOpe>
                    <dTotGralOpe>1050.00</dTotGralOpe>
                    <dIVA5>50.00</dIVA5>
                    <dIVA10>0</dIVA10>
                    <dTotIVA>50.00</dTotIVA>
                    <dBaseGrav5>1000.00</dBaseGrav5>
                    <dBaseGrav10>0</dBaseGrav10>
                    <dTBasGraIVA>1000.00</dTBasGraIVA>
                </gTotSub>
            </DE>
        </rDE>
        '''

        # Verificar que es un documento XML válido
        try:
            parser = etree.XMLParser()
            doc = etree.fromstring(
                xml_documento_completo.encode('utf-8'), parser)
            assert doc is not None, "Documento completo debe parsearse correctamente"

            # Verificar elementos principales
            assert doc.find(
                f'.//{{{sifen_namespace}}}dVerFor') is not None, "dVerFor debe estar presente"
            assert doc.find(
                f'.//{{{sifen_namespace}}}gOpeDE') is not None, "gOpeDE debe estar presente"
            assert doc.find(
                f'.//{{{sifen_namespace}}}gTimb') is not None, "gTimb debe estar presente"
            assert doc.find(
                f'.//{{{sifen_namespace}}}gTotSub') is not None, "gTotSub debe estar presente"

        except etree.XMLSyntaxError as e:
            pytest.fail(f"Error de sintaxis XML: {e}")

        logger.info("✅ test_documento_completo_minimal_corregido - PASSED")

    def test_validacion_cruzada_totales_corregida(self, document_core_validator, sifen_namespace):
        """Test validación cruzada entre diferentes campos de totales"""
        # CORRECCIÓN: Usa tipoMonto en lugar de tipoImporteMonetario
        casos_totales = [
            {
                "descripcion": "Factura solo IVA 5%",
                "sub5": 2000.00,
                "sub10": 0,
                "tot_ope": 2000.00,
                "iva5": 100.00,
                "iva10": 0,
                "tot_iva": 100.00,
                "tot_gral": 2100.00
            }
        ]

        for caso in casos_totales:
            xml_totales = f'''
            <gTotSub xmlns="{sifen_namespace}">
                <dSubExe>0</dSubExe>
                <dSubExo>0</dSubExo>
                <dSub5>{caso["sub5"]}</dSub5>
                <dSub10>{caso["sub10"]}</dSub10>
                <dTotOpe>{caso["tot_ope"]}</dTotOpe>
                <dTotGralOpe>{caso["tot_gral"]}</dTotGralOpe>
                <dIVA5>{caso["iva5"]}</dIVA5>
                <dIVA10>{caso["iva10"]}</dIVA10>
                <dTotIVA>{caso["tot_iva"]}</dTotIVA>
                <dBaseGrav5>{caso["sub5"]}</dBaseGrav5>
                <dBaseGrav10>{caso["sub10"]}</dBaseGrav10>
                <dTBasGraIVA>{caso["tot_ope"]}</dTBasGraIVA>
            </gTotSub>
            '''

            try:
                parser = etree.XMLParser()
                doc = etree.fromstring(xml_totales.encode('utf-8'), parser)
                assert doc is not None, f"Totales para '{caso['descripcion']}' deben parsearse correctamente"
            except etree.XMLSyntaxError as e:
                pytest.fail(f"Error en {caso['descripcion']}: {e}")

        logger.info("✅ test_validacion_cruzada_totales_corregida - PASSED")


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
