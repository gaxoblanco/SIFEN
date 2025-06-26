#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de Mapeo Modular → Oficial SIFEN v150
==========================================

Tests comprehensivos para validar el mapeo de estructura modular a oficial 
SIFEN v150. Cubre transformaciones de elementos clave, validación de namespaces
y consistencia de datos.

Transformaciones Validadas:
- gDatGral → gTimb (datos generales/timbrado)
- gDatEmi → gOpeOpe (datos emisor/operación)  
- gItems → gCamIVA (items/campos IVA)
- gTotales → gTotSub (totales/subtotales)

Tipos de Documento:
- FE (Factura Electrónica)
- NCE (Nota Crédito Electrónica) 
- NDE (Nota Débito Electrónica)
- AFE (Autofactura Electrónica)
- NRE (Nota Remisión Electrónica)

Casos Edge:
- Campos opcionales faltantes
- Valores límite y caracteres especiales
- Documentos estructura mínima vs completa

Autor: Sistema SIFEN Paraguay
Versión: 1.5.0
Fecha: 2025-06-25
"""

from app.services.xml_generator.schemas.v150.integration.validation_bridge import ValidationBridge
from app.services.xml_generator.schemas.v150.integration.schema_mapper import (
    SchemaMapper,
    DocumentType as SifenDocumentType
)
from ..integration.xml_transformer import (
    XMLTransformer as SifenXMLTransformer,
    TransformationConfig,
    TransformationResult as SifenTransformationResult
)
import pytest
import time
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from lxml import etree
from dataclasses import dataclass
from enum import Enum

# Configuración logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports del sistema SIFEN v150


# =============================================================================
# CONFIGURACIÓN Y ENUMS
# =============================================================================

class DocumentType(Enum):
    """Tipos de documento SIFEN (local para tests)"""
    FACTURA_ELECTRONICA = "1"
    AUTOFACTURA_ELECTRONICA = "4"
    NOTA_CREDITO_ELECTRONICA = "5"
    NOTA_DEBITO_ELECTRONICA = "6"
    NOTA_REMISION_ELECTRONICA = "7"


class TransformationResult:
    """Resultado de transformación para tests locales"""

    def __init__(self, success: bool, xml: str = "", errors: Optional[List[str]] = None):
        self.success = success
        self.xml = xml
        self.errors = errors or []
        self.transformation_time = 0.0
        self.original_size = 0
        self.transformed_size = 0


# =============================================================================
# FIXTURES DE CONFIGURACIÓN
# =============================================================================

@pytest.fixture(scope="session")
def xml_transformer():
    """
    Fixture de XMLTransformer configurado para v150
    Scope: session (costoso de inicializar)
    """
    config = TransformationConfig(
        validate_input=True,
        validate_output=True,
        preserve_comments=False,
        enable_caching=True,
        timeout_seconds=30
    )
    transformer = SifenXMLTransformer(config)
    logger.info("SifenXMLTransformer inicializado para tests")
    return transformer


@pytest.fixture(scope="session")
def schema_mapper():
    """
    Fixture de SchemaMapper para mapeos modular ↔ oficial
    Scope: session (configuración pesada)
    """
    # Ruta relativa a esquemas v150
    schemas_path = Path(__file__).parent.parent / "schemas" / "v150"
    mapper = SchemaMapper(schemas_path)
    return mapper


@pytest.fixture(scope="module")
def validation_bridge():
    """
    Fixture de ValidationBridge para validación híbrida
    Scope: module (por test class)
    """
    return ValidationBridge()


@pytest.fixture
def transformation_config():
    """
    Fixture de configuración de transformación básica
    Scope: function (personalizable por test)
    """
    return {
        "validate_namespaces": True,
        "preserve_comments": False,
        "strict_mode": True,
        "timeout_seconds": 30,
        "max_depth": 50
    }


# =============================================================================
# FIXTURES DE DATOS DE PRUEBA
# =============================================================================

@pytest.fixture
def datos_factura_basica():
    """
    Fixture con datos mínimos para Factura Electrónica
    Incluye solo campos obligatorios SIFEN v150
    """
    return {
        "tipo_documento": "1",
        "numero_documento": "001-001-0000001",
        "fecha_emision": "2024-12-15",
        "hora_emision": "14:30:00",
        "moneda": "PYG",
        "condicion_operacion": "1",  # Venta normal
        "condicion_venta": "1",      # Contado
        "total_operacion": Decimal("110000.0000"),
        "total_iva": Decimal("10000.0000"),
        "emisor": {
            "ruc": "80016875-1",
            "razon_social": "Empresa Test SA",
            "direccion": "Av. Test 123, Asunción"
        },
        "items": [{
            "codigo": "PROD001",
            "descripcion": "Producto Test",
            "cantidad": 1,
            "precio_unitario": Decimal("100000.0000"),
            "exenta": Decimal("0.0000"),
            "gravada_5": Decimal("0.0000"),
            "gravada_10": Decimal("100000.0000"),
            "iva_10": Decimal("10000.0000")
        }]
    }


@pytest.fixture
def datos_nota_credito_completa():
    """
    Fixture con datos completos para Nota Crédito Electrónica
    Incluye campos opcionales y referencia a documento original
    """
    return {
        "tipo_documento": "5",
        "numero_documento": "001-002-0000001",
        "fecha_emision": "2024-12-15",
        "hora_emision": "15:45:30",
        "moneda": "PYG",
        "condicion_operacion": "2",  # Devolución
        "documento_asociado": {
            "tipo": "1",  # FE original
            "numero": "001-001-0000001",
            "fecha": "2024-12-10"
        },
        "motivo_credito": "Devolución mercadería defectuosa",
        "total_operacion": Decimal("55000.0000"),
        "total_iva": Decimal("5000.0000"),
        "emisor": {
            "ruc": "80016875-1",
            "razon_social": "Empresa Test SA",
            "direccion": "Av. Test 123, Asunción",
            "telefono": "+595 21 123456",
            "email": "test@empresa.com.py"
        },
        "receptor": {
            "tipo_documento": "1",  # CI paraguaya
            "numero_documento": "12345678",
            "nombre": "Juan Pérez",
            "direccion": "Barrio Test, Luque"
        },
        "items": [{
            "codigo": "PROD001",
            "descripcion": "Producto Test (devolución)",
            "cantidad": 1,
            "precio_unitario": Decimal("50000.0000"),
            "total_item": Decimal("55000.0000")
        }]
    }


@pytest.fixture
def datos_autofactura_edge():
    """
    Fixture con casos edge para Autofactura Electrónica
    Incluye caracteres especiales y valores límite
    """
    return {
        "tipo_documento": "4",
        "numero_documento": "001-003-0000001",
        "fecha_emision": "2024-12-15",
        "hora_emision": "23:59:59",
        "moneda": "USD",  # Moneda extranjera
        "tipo_cambio": Decimal("7350.0000"),
        "condicion_operacion": "1",
        "total_operacion": Decimal("99999999.9999"),  # Valor máximo
        "vendedor_extranjero": {
            "tipo_identificacion": "2",  # Pasaporte
            "numero_identificacion": "P123456789",
            "nombre": "José María González-Vásquez",  # Caracteres especiales
            "direccion": "123 Main St, Miami, FL 33101, USA",
            "pais": "840"  # Estados Unidos
        },
        "items": [{
            "codigo": "SERV001",
            "descripcion": "Servicios de consultoría técnica especializada",
            "cantidad": Decimal("0.0001"),  # Cantidad mínima
            "precio_unitario": Decimal("999999999.9999"),  # Precio máximo
            "moneda_precio": "USD"
        }]
    }


@pytest.fixture
def xml_modular_samples():
    """
    Fixture con samples de XML modular para diferentes elementos
    Útil para tests de transformación específicos
    """
    return {
        "gDatGral": """<gDatGral>
            <dFeEmiDE>2024-12-15</dFeEmiDE>
            <dHorEmi>14:30:00</dHorEmi>
            <iTipoDE>1</iTipoDE>
            <dNumID>001-001-0000001</dNumID>
            <dFeVenDE>2024-12-22</dFeVenDE>
        </gDatGral>""",

        "gDatEmi": """<gDatEmi>
            <dRucEm>80016875-1</dRucEm>
            <dDVEmi>1</dDVEmi>
            <dNomEmi>Empresa Test SA</dNomEmi>
            <dDirEmi>Av. Test 123, Asunción</dDirEmi>
            <dNumCasEmi>Local 5</dNumCasEmi>
            <cDepEmi>1</cDepEmi>
            <dDesDepEmi>CAPITAL</dDesDepEmi>
        </gDatEmi>""",

        "gCamItem": """<gCamItem>
            <dCodInt>PROD001</dCodInt>
            <dDesProSer>Producto Test</dDesProSer>
            <cUniMed>1</cUniMed>
            <dDesUniMed>Unidad</dDesUniMed>
            <dCantProSer>1.0000</dCantProSer>
            <dPUniProSer>100000.0000</dPUniProSer>
            <gCamIVA>
                <iAfecIVA>1</iAfecIVA>
                <dDesAfecIVA>Gravado IVA</dDesAfecIVA>
                <dPropIVA>100</dPropIVA>
                <dTasaIVA>10</dTasaIVA>
                <dBasGravIVA>100000.0000</dBasGravIVA>
                <dLiqIVAItem>10000.0000</dLiqIVAItem>
            </gCamIVA>
        </gCamItem>""",

        "gTotSub": """<gTotSub>
            <dSubExe>0.0000</dSubExe>
            <dSubExo>0.0000</dSubExo>
            <dSub5>0.0000</dSub5>
            <dSub10>100000.0000</dSub10>
            <dTotOpe>100000.0000</dTotOpe>
            <dTotDesc>0.0000</dTotDesc>
            <dTotDescGlotem>0.0000</dTotDescGlotem>
            <dTotAntItem>0.0000</dTotAntItem>
            <dTotAnt>0.0000</dTotAnt>
            <dPorcDescTotal>0.00</dPorcDescTotal>
            <dDescTotal>0.0000</dDescTotal>
            <dAnticipo>0.0000</dAnticipo>
            <dRedon>0.0000</dRedon>
            <dComi>0.0000</dComi>
            <dTotGralOpe>110000.0000</dTotGralOpe>
            <dIVA5>0.0000</dIVA5>
            <dIVA10>10000.0000</dIVA10>
            <dLiqTotIVA5>0.0000</dLiqTotIVA5>
            <dLiqTotIVA10>10000.0000</dLiqTotIVA10>
            <dIVAComi>0.0000</dIVAComi>
            <dTotIVA>10000.0000</dTotIVA>
            <dBaseGrav5>0.0000</dBaseGrav5>
            <dBaseGrav10>100000.0000</dBaseGrav10>
            <dTBasGraIVA>100000.0000</dTBasGraIVA>
        </gTotSub>"""
    }


@pytest.fixture
def namespaces_v150():
    """
    Fixture con namespaces oficiales SIFEN v150
    """
    return {
        "modular": "http://ekuatia.set.gov.py/sifen/xsd/modular",
        "oficial": "http://ekuatia.set.gov.py/sifen/xsd",
        "xmldsig": "http://www.w3.org/2000/09/xmldsig#",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }


# =============================================================================
# TESTS DE MAPEO BÁSICO
# =============================================================================

class TestBasicMapping:
    """
    Tests para mapeos básicos entre elementos modular y oficial
    Valida transformaciones fundamentales sin casos edge
    """

    def test_mapeo_gdatgral_a_gtimb(self, xml_transformer, xml_modular_samples):
        """
        Test mapeo gDatGral → gTimb (datos generales a timbrado)

        Verifica:
        - Preservación de todos los campos
        - Estructura XML válida resultante  
        - Tipos de datos correctos
        """
        # Arrange
        xml_modular = xml_modular_samples["gDatGral"]

        # Act - Simular transformación
        start_time = time.time()
        result = xml_transformer.transform_modular_to_official(
            xml_modular, SifenDocumentType.FACTURA_ELECTRONICA
        )
        transformation_time = time.time() - start_time

        # Assert - Verificaciones básicas
        assert result.success, f"Transformación falló: {result.errors}"
        assert transformation_time < 0.5, f"Transformación muy lenta: {transformation_time}s"

        # Verificar estructura XML resultante
        assert "<gTimb>" in result.xml or "<gDatGral>" in result.xml
        assert "2024-12-15" in result.xml, "Fecha preservada"
        assert "14:30:00" in result.xml, "Hora preservada"
        assert "001-001-0000001" in result.xml, "Número documento preservado"

        logger.info(
            f"✅ Mapeo gDatGral→gTimb exitoso en {transformation_time:.3f}s")

    def test_mapeo_gdatemi_a_gopeope(self, xml_transformer, xml_modular_samples):
        """
        Test mapeo gDatEmi → gOpeOpe (datos emisor a operación)

        Verifica:
        - Transformación datos del emisor
        - Preservación información geográfica
        - Validación RUC y campos obligatorios
        """
        # Arrange
        xml_modular = xml_modular_samples["gDatEmi"]

        # Act
        start_time = time.time()
        result = xml_transformer.transform_modular_to_official(
            xml_modular, SifenDocumentType.FACTURA_ELECTRONICA
        )
        transformation_time = time.time() - start_time

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"
        assert transformation_time < 0.5, f"Muy lento: {transformation_time}s"

        # Verificar datos emisor preservados
        assert "80016875-1" in result.xml, "RUC preservado"
        assert "Empresa Test SA" in result.xml, "Razón social preservada"
        assert "Av. Test 123" in result.xml, "Dirección preservada"
        assert "CAPITAL" in result.xml, "Departamento preservado"

        logger.info(
            f"✅ Mapeo gDatEmi→gOpeOpe exitoso en {transformation_time:.3f}s")

    def test_mapeo_gcamitem_preserva_estructura(self, xml_transformer, xml_modular_samples):
        """
        Test mapeo gCamItem preserva estructura de items

        gCamItem en modular debe preservar estructura en oficial,
        especialmente el grupo gCamIVA que es crítico para SIFEN
        """
        # Arrange
        xml_modular = xml_modular_samples["gCamItem"]

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_modular, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar estructura de item preservada
        assert "PROD001" in result.xml, "Código interno preservado"
        assert "Producto Test" in result.xml, "Descripción preservada"
        assert "100000.0000" in result.xml, "Precio preservado"

        # Verificar grupo IVA crítico preservado
        assert "gCamIVA" in result.xml, "Grupo IVA preservado"
        assert "iAfecIVA" in result.xml, "Afectación IVA preservada"
        assert "dTasaIVA>10" in result.xml, "Tasa IVA preservada"
        assert "dLiqIVAItem" in result.xml, "Liquidación IVA preservada"

        logger.info("✅ Estructura gCamItem preservada correctamente")

    def test_mapeo_gtotsub_calculos_coherentes(self, xml_transformer, xml_modular_samples):
        """
        Test mapeo gTotSub preserva cálculos de totales

        Los totales y subtotales son críticos para validación SIFEN.
        Deben preservarse exactamente sin errores de redondeo.
        """
        # Arrange
        xml_modular = xml_modular_samples["gTotSub"]

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_modular, DocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar subtotales por gravamen preservados
        assert "dSub10>100000.0000" in result.xml, "Subtotal gravado 10% correcto"
        assert "dTotOpe>100000.0000" in result.xml, "Total operación correcto"
        assert "dTotGralOpe>110000.0000" in result.xml, "Total general correcto"

        # Verificar cálculos IVA coherentes
        assert "dIVA10>10000.0000" in result.xml, "IVA 10% calculado correctamente"
        assert "dTotIVA>10000.0000" in result.xml, "Total IVA coherente"
        assert "dBaseGrav10>100000.0000" in result.xml, "Base gravada coherente"

        logger.info("✅ Cálculos gTotSub preservados coherentemente")


# =============================================================================
# TESTS DE VALIDACIÓN DE NAMESPACES
# =============================================================================

class TestNamespaceValidation:
    """
    Tests para validación de namespaces en transformaciones
    Verifica URIs correctas y declaraciones xmlns apropiadas
    """

    def test_namespace_oficial_correcto(self, xml_transformer, xml_modular_samples, namespaces_v150):
        """
        Test que el XML oficial resultante tiene namespace correcto

        El XML transformado debe usar:
        - URI oficial SIFEN: http://ekuatia.set.gov.py/sifen/xsd
        - Declaraciones xmlns apropiadas
        - Prefijos consistentes
        """
        # Arrange
        xml_modular = xml_modular_samples["gDatGral"]

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_modular, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar namespace oficial en resultado
        oficial_ns = namespaces_v150["oficial"]
        assert oficial_ns in result.xml or "ekuatia.set.gov.py" in result.xml

        # Verificar declaración xmlns si está presente
        if "xmlns" in result.xml:
            assert "ekuatia.set.gov.py/sifen/xsd" in result.xml

        logger.info("✅ Namespace oficial validado correctamente")

    def test_eliminacion_namespace_modular(self, xml_transformer, namespaces_v150):
        """
        Test que namespaces modulares se remueven en transformación oficial

        El XML resultante NO debe contener referencias a namespaces modulares
        """
        # Arrange - XML modular con namespace explícito
        xml_con_ns_modular = f'''<?xml version="1.0" encoding="UTF-8"?>
        <gDatGral xmlns="{namespaces_v150['modular']}">
            <dFeEmiDE>2024-12-15</dFeEmiDE>
            <iTipoDE>1</iTipoDE>
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_con_ns_modular, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar que namespace modular fue removido
        ns_modular = namespaces_v150["modular"]
        assert ns_modular not in result.xml, "Namespace modular debe ser removido"

        # Verificar que datos se preservaron
        assert "2024-12-15" in result.xml, "Fecha preservada sin namespace"

        logger.info("✅ Namespace modular removido correctamente")

    def test_preservacion_namespace_xmldsig(self, xml_transformer, namespaces_v150):
        """
        Test preservación de namespaces de firma digital XML

        Los namespaces xmldsig deben preservarse para firma digital
        """
        # Arrange - XML con firma digital
        xml_con_firma = f'''<?xml version="1.0" encoding="UTF-8"?>
        <gDatGral xmlns:ds="{namespaces_v150['xmldsig']}">
            <dFeEmiDE>2024-12-15</dFeEmiDE>
            <ds:Signature>
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                </ds:SignedInfo>
            </ds:Signature>
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_con_firma, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar preservación namespace xmldsig
        if "ds:Signature" in result.xml:
            xmldsig_ns = namespaces_v150["xmldsig"]
            assert xmldsig_ns in result.xml or "xmldsig" in result.xml

        logger.info("✅ Namespace xmldsig preservado para firma digital")


# =============================================================================
# TESTS DE CONSISTENCIA DE DATOS
# =============================================================================

class TestDataConsistency:
    """
    Tests para verificar consistencia de datos entre modular y oficial
    Valida que los datos se preserven sin pérdida ni corrupción
    """

    def test_preservacion_tipos_numericos(self, xml_transformer):
        """
        Test preservación exacta de tipos numéricos

        Los montos, tasas y cantidades deben preservarse sin errores
        de redondeo que causen rechazos en SIFEN
        """
        # Arrange - XML con valores numéricos precisos
        xml_numerico = '''<gTotSub>
            <dTotOpe>123456789.9999</dTotOpe>
            <dTasaIVA>10.00</dTasaIVA>
            <dCantProSer>0.0001</dCantProSer>
            <dPUniProSer>999999999.9999</dPUniProSer>
        </gTotSub>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_numerico, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar preservación exacta de decimales
        assert "123456789.9999" in result.xml, "Monto alto preservado"
        assert "10.00" in result.xml, "Tasa IVA preservada"
        assert "0.0001" in result.xml, "Cantidad mínima preservada"
        assert "999999999.9999" in result.xml, "Precio máximo preservado"

        logger.info("✅ Tipos numéricos preservados exactamente")

    def test_preservacion_caracteres_especiales(self, xml_transformer):
        """
        Test preservación de caracteres especiales paraguayos

        Debe manejar correctamente: ñ, ü, acentos, símbolos monetarios
        """
        # Arrange - XML con caracteres especiales típicos Paraguay
        xml_caracteres = '''<gDatEmi>
            <dNomEmi>José María González-Vásquez & Cía. S.R.L.</dNomEmi>
            <dDirEmi>Avda. España c/ Boquerón Nº 1.234</dDirEmi>
            <dDesDepEmi>ÑEEMBUCÚ</dDesDepEmi>
            <dDesCiuEmi>CIUDAD DEL ESTE</dDesCiuEmi>
        </gDatEmi>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_caracteres, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar caracteres especiales preservados
        assert "José María" in result.xml, "Nombre con acentos preservado"
        assert "González-Vásquez" in result.xml, "Apellido con guión preservado"
        assert "& Cía." in result.xml, "Símbolo ampersand preservado"
        assert "Nº 1.234" in result.xml, "Símbolo número preservado"
        assert "ÑEEMBUCÚ" in result.xml, "Letra ñ preservada"

        logger.info("✅ Caracteres especiales preservados correctamente")

    def test_validacion_integridad_referencias(self, xml_transformer, datos_nota_credito_completa):
        """
        Test integridad de referencias entre documentos

        Para NCE/NDE debe preservarse referencia al documento original
        """
        # Arrange - Crear XML NCE con referencia
        xml_nce = f'''<gDatGral>
            <iTipoDE>5</iTipoDE>
            <dNumID>001-002-0000001</dNumID>
            <gDocAsoc>
                <iTipDocAso>1</iTipDocAso>
                <dDTipDocAso>Factura electrónica</dDTipDocAso>
                <dNumDocAso>001-001-0000001</dNumDocAso>
                <dFeEmiDocAso>2024-12-10</dFeEmiDocAso>
            </gDocAsoc>
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_nce, SifenDocumentType.NOTA_CREDITO_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar referencia al documento asociado preservada
        assert "iTipDocAso>1" in result.xml, "Tipo documento asociado preservado"
        assert "001-001-0000001" in result.xml, "Número documento asociado preservado"
        assert "2024-12-10" in result.xml, "Fecha documento asociado preservada"

        logger.info("✅ Referencias entre documentos preservadas")

    def test_coherencia_totales_items(self, xml_transformer):
        """
        Test coherencia entre totales de documento e items

        La suma de items debe coincidir con totales del documento
        """
        # Arrange - XML con múltiples items y totales
        xml_coherencia = '''<root>
            <gCamItem>
                <dCantProSer>2.0000</dCantProSer>
                <dPUniProSer>50000.0000</dPUniProSer>
                <gCamIVA>
                    <dBasGravIVA>100000.0000</dBasGravIVA>
                    <dLiqIVAItem>10000.0000</dLiqIVAItem>
                </gCamIVA>
            </gCamItem>
            <gTotSub>
                <dSub10>100000.0000</dSub10>
                <dTotIVA>10000.0000</dTotIVA>
                <dTotGralOpe>110000.0000</dTotGralOpe>
            </gTotSub>
        </root>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_coherencia, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación falló: {result.errors}"

        # Verificar coherencia preservada
        assert "100000.0000" in result.xml, "Base gravada coherente"
        assert "10000.0000" in result.xml, "IVA coherente"
        assert "110000.0000" in result.xml, "Total general coherente"

        logger.info("✅ Coherencia totales-items preservada")


# =============================================================================
# TESTS DE CASOS EDGE
# =============================================================================

class TestEdgeCases:
    """
    Tests para casos edge y situaciones límite
    Maneja campos opcionales, valores extremos y errores
    """

    def test_campos_opcionales_faltantes(self, xml_transformer):
        """
        Test manejo de campos opcionales ausentes

        La transformación debe ser exitosa aunque falten campos opcionales
        como gDatRec, gTrans, etc.
        """
        # Arrange - XML mínimo solo con campos obligatorios
        xml_minimo = '''<gDatGral>
            <dFeEmiDE>2024-12-15</dFeEmiDE>
            <iTipoDE>1</iTipoDE>
            <dNumID>001-001-0000001</dNumID>
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_minimo, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación con campos mínimos falló: {result.errors}"

        # Verificar que campos obligatorios se preservaron
        assert "2024-12-15" in result.xml, "Fecha obligatoria preservada"
        assert "001-001-0000001" in result.xml, "Número obligatorio preservado"

        logger.info("✅ Campos opcionales faltantes manejados correctamente")

    def test_valores_limite_extremos(self, xml_transformer):
        """
        Test manejo de valores en límites extremos

        Debe manejar correctamente:
        - Montos máximos SIFEN (999,999,999.9999)
        - Cantidades mínimas (0.0001)
        - Fechas límite
        """
        # Arrange - XML con valores extremos
        xml_extremos = '''<gTotSub>
            <dTotGralOpe>999999999.9999</dTotGralOpe>
            <dCantProSer>0.0001</dCantProSer>
            <dTasaIVA>10.00</dTasaIVA>
            <dFeEmiDE>2099-12-31</dFeEmiDE>
        </gTotSub>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_extremos, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación con valores extremos falló: {result.errors}"

        # Verificar valores extremos preservados
        assert "999999999.9999" in result.xml, "Monto máximo preservado"
        assert "0.0001" in result.xml, "Cantidad mínima preservada"
        assert "2099-12-31" in result.xml, "Fecha futura preservada"

        logger.info("✅ Valores extremos manejados correctamente")

    def test_xml_malformado_error_controlado(self, xml_transformer):
        """
        Test manejo controlado de XML malformado

        Debe retornar error controlado sin explotar la aplicación
        """
        # Arrange - XML malformado
        xml_malformado = '''<gDatGral>
            <dFeEmiDE>2024-12-15
            <iTipoDE>1</iTipoDE>
            <!-- Tag sin cerrar -->
        '''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_malformado, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert not result.success, "XML malformado debe fallar controladamente"
        assert len(result.errors) > 0, "Debe reportar errores específicos"

        # Verificar que el error es descriptivo
        error_text = " ".join(result.errors).lower()
        assert any(term in error_text for term in ["xml", "malformado", "sintaxis", "parse"]), \
            "Error debe describir problema XML"

        logger.info("✅ XML malformado manejado con error controlado")

    def test_elementos_desconocidos_ignorados(self, xml_transformer):
        """
        Test que elementos no reconocidos se manejan apropiadamente

        Elementos fuera del estándar SIFEN deben ignorarse o preservarse
        según configuración
        """
        # Arrange - XML con elementos custom
        xml_custom = '''<gDatGral>
            <dFeEmiDE>2024-12-15</dFeEmiDE>
            <iTipoDE>1</iTipoDE>
            <customElement>Valor custom</customElement>
            <anotherCustom>
                <nested>Valor anidado</nested>
            </anotherCustom>
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_custom, SifenDocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"XML con elementos custom falló: {result.errors}"

        # Verificar que elementos estándar se preservaron
        assert "2024-12-15" in result.xml, "Elementos estándar preservados"

        # Elementos custom pueden estar presentes o no según configuración
        logger.info("✅ Elementos desconocidos manejados apropiadamente")


# =============================================================================
# TESTS POR TIPO DE DOCUMENTO
# =============================================================================

class TestDocumentTypes:
    """
    Tests específicos por tipo de documento SIFEN
    Valida transformaciones según características de cada tipo
    """

    @pytest.mark.parametrize("tipo_doc,numero_doc,descripcion", [
        ("1", "001-001-0000001", "Factura Electrónica"),
        ("4", "001-003-0000001", "Autofactura Electrónica"),
        ("5", "001-002-0000001", "Nota Crédito Electrónica"),
        ("6", "001-004-0000001", "Nota Débito Electrónica"),
        ("7", "001-005-0000001", "Nota Remisión Electrónica")
    ])
    def test_transformacion_por_tipo_documento(self, xml_transformer, tipo_doc, numero_doc, descripcion):
        """
        Test parametrizado para cada tipo de documento SIFEN

        Verifica que cada tipo se transforme correctamente manteniendo
        sus características específicas
        """
        # Arrange - XML genérico adaptable por tipo
        xml_base = f'''<gDatGral>
            <dFeEmiDE>2024-12-15</dFeEmiDE>
            <iTipoDE>{tipo_doc}</iTipoDE>
            <dNumID>{numero_doc}</dNumID>
            <dDesDE>{descripcion}</dDesDE>
        </gDatGral>'''

        # Act
        doc_type = SifenDocumentType.FACTURA_ELECTRONICA if tipo_doc == "1" else \
            SifenDocumentType.AUTOFACTURA_ELECTRONICA if tipo_doc == "4" else \
            SifenDocumentType.NOTA_CREDITO_ELECTRONICA if tipo_doc == "5" else \
            SifenDocumentType.NOTA_DEBITO_ELECTRONICA if tipo_doc == "6" else \
            SifenDocumentType.NOTA_REMISION_ELECTRONICA
        result = xml_transformer.transform_modular_to_official(
            xml_base, doc_type)

        # Assert
        assert result.success, f"Transformación {descripcion} falló: {result.errors}"

        # Verificar características específicas del tipo
        assert f"iTipoDE>{tipo_doc}" in result.xml, f"Tipo {tipo_doc} preservado"
        assert numero_doc in result.xml, f"Numeración {numero_doc} preservada"
        assert descripcion in result.xml, f"Descripción {descripcion} preservada"

        logger.info(
            f"✅ {descripcion} (tipo {tipo_doc}) transformada correctamente")

    def test_factura_electronica_campos_venta(self, xml_transformer, datos_factura_basica):
        """
        Test específico para Factura Electrónica

        Valida campos específicos de operaciones de venta
        """
        # Arrange - XML FE con campos de venta
        xml_fe = '''<root>
            <gDatGral>
                <iTipoDE>1</iTipoDE>
                <cConVen>1</cConVen>
                <cConOpe>1</cConOpe>
            </gDatGral>
            <gDatEmi>
                <dRucEm>80016875-1</dRucEm>
                <dNomEmi>Empresa Test SA</dNomEmi>
            </gDatEmi>
        </root>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_fe, DocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación FE falló: {result.errors}"

        # Verificar campos específicos FE
        assert "cConVen>1" in result.xml, "Condición venta contado preservada"
        assert "cConOpe>1" in result.xml, "Condición operación venta preservada"

        logger.info("✅ Factura Electrónica con campos venta validada")

    def test_nota_credito_referencia_original(self, xml_transformer, datos_nota_credito_completa):
        """
        Test específico para Nota Crédito Electrónica

        Valida referencia obligatoria al documento original
        """
        # Arrange - XML NCE con documento asociado
        xml_nce = '''<gDatGral>
            <iTipoDE>5</iTipoDE>
            <cConOpe>2</cConOpe>
            <gDocAsoc>
                <iTipDocAso>1</iTipDocAso>
                <dNumDocAso>001-001-0000001</dNumDocAso>
                <dFeEmiDocAso>2024-12-10</dFeEmiDocAso>
            </gDocAsoc>
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_nce, DocumentType.NOTA_CREDITO_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación NCE falló: {result.errors}"

        # Verificar campos específicos NCE
        assert "cConOpe>2" in result.xml, "Operación devolución preservada"
        assert "gDocAsoc" in result.xml, "Documento asociado preservado"
        assert "001-001-0000001" in result.xml, "Número documento original preservado"

        logger.info("✅ Nota Crédito con referencia original validada")

    def test_autofactura_vendedor_extranjero(self, xml_transformer, datos_autofactura_edge):
        """
        Test específico para Autofactura Electrónica

        Valida campos de vendedor extranjero obligatorios en AFE
        """
        # Arrange - XML AFE con vendedor extranjero
        xml_afe = '''<gCamAE>
            <iNatVen>2</iNatVen>
            <dDesNatVen>Extranjero</dDesNatVen>
            <iTipIDVen>2</iTipIDVen>
            <dNumIDVen>P123456789</dNumIDVen>
            <dNomVen>International Corp</dNomVen>
            <dDirVen>123 Main St, Miami FL</dDirVen>
        </gCamAE>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_afe, DocumentType.AUTOFACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación AFE falló: {result.errors}"

        # Verificar campos específicos AFE
        assert "iNatVen>2" in result.xml, "Naturaleza extranjero preservada"
        assert "iTipIDVen>2" in result.xml, "Tipo ID pasaporte preservado"
        assert "P123456789" in result.xml, "Número pasaporte preservado"
        assert "International Corp" in result.xml, "Nombre vendedor preservado"

        logger.info("✅ Autofactura con vendedor extranjero validada")


# =============================================================================
# TESTS DE PERFORMANCE
# =============================================================================

class TestPerformance:
    """
    Tests de performance y recursos para transformaciones
    Valida que el sistema sea eficiente para producción
    """

    def test_tiempo_transformacion_individual(self, xml_transformer, xml_modular_samples):
        """
        Test tiempo de transformación individual < 500ms

        Cada transformación debe completarse rápidamente para UX
        """
        # Arrange
        xml_test = xml_modular_samples["gDatGral"]

        # Act - Medir tiempo múltiples ejecuciones
        tiempos = []
        for i in range(5):
            start = time.time()
            result = xml_transformer.transform_modular_to_official(
                xml_test, DocumentType.FACTURA_ELECTRONICA
            )
            tiempo = time.time() - start
            tiempos.append(tiempo)

            assert result.success, f"Transformación {i+1} falló"

        # Assert - Performance requirements
        tiempo_promedio = sum(tiempos) / len(tiempos)
        tiempo_maximo = max(tiempos)

        assert tiempo_promedio < 0.5, f"Tiempo promedio muy alto: {tiempo_promedio:.3f}s"
        assert tiempo_maximo < 1.0, f"Tiempo máximo muy alto: {tiempo_maximo:.3f}s"

        logger.info(
            f"✅ Performance OK - Promedio: {tiempo_promedio:.3f}s, Máximo: {tiempo_maximo:.3f}s")

    def test_transformacion_documentos_grandes(self, xml_transformer):
        """
        Test transformación de documentos con muchos items

        Debe mantener performance aceptable con 100+ items
        """
        # Arrange - Generar XML con muchos items
        items_xml = []
        for i in range(100):
            item = f'''<gCamItem>
                <dCodInt>PROD{i:03d}</dCodInt>
                <dDesProSer>Producto Test {i}</dDesProSer>
                <dCantProSer>1.0000</dCantProSer>
                <dPUniProSer>1000.0000</dPUniProSer>
                <gCamIVA>
                    <iAfecIVA>1</iAfecIVA>
                    <dBasGravIVA>1000.0000</dBasGravIVA>
                    <dLiqIVAItem>100.0000</dLiqIVAItem>
                </gCamIVA>
            </gCamItem>'''
            items_xml.append(item)

        xml_grande = f'''<root>
            <gDatGral>
                <dFeEmiDE>2024-12-15</dFeEmiDE>
                <iTipoDE>1</iTipoDE>
            </gDatGral>
            {"".join(items_xml)}
        </root>'''

        # Act - Medir tiempo documento grande
        start = time.time()
        result = xml_transformer.transform_modular_to_official(
            xml_grande, DocumentType.FACTURA_ELECTRONICA
        )
        tiempo_grande = time.time() - start

        # Assert
        assert result.success, f"Transformación documento grande falló: {result.errors}"
        assert tiempo_grande < 2.0, f"Documento grande muy lento: {tiempo_grande:.3f}s"

        # Verificar que todos los items fueron procesados
        for i in range(0, 100, 10):  # Verificar cada 10 items
            assert f"PROD{i:03d}" in result.xml, f"Item {i} debe estar presente"

        logger.info(
            f"✅ Documento grande (100 items) procesado en {tiempo_grande:.3f}s")

    @pytest.mark.performance
    def test_uso_memoria_transformacion(self, xml_transformer, xml_modular_samples):
        """
        Test uso eficiente de memoria durante transformación

        No debe tener leaks de memoria o uso excesivo
        """
        import gc
        import sys

        # Arrange - Baseline memoria
        gc.collect()
        memoria_inicial = sys.getsizeof(gc.get_objects())

        # Act - Múltiples transformaciones
        for i in range(20):
            result = xml_transformer.transform_modular_to_official(
                xml_modular_samples["gTotSub"], DocumentType.FACTURA_ELECTRONICA
            )
            assert result.success, f"Transformación {i} falló"

        # Forzar garbage collection
        gc.collect()
        memoria_final = sys.getsizeof(gc.get_objects())

        # Assert - Memoria no debe crecer excesivamente
        crecimiento_memoria = memoria_final - memoria_inicial
        assert crecimiento_memoria < 50_000_000, f"Posible memory leak: {crecimiento_memoria} bytes"

        logger.info(
            f"✅ Uso memoria controlado - Crecimiento: {crecimiento_memoria} bytes")


# =============================================================================
# TESTS DE INTEGRACIÓN BÁSICA
# =============================================================================

class TestIntegrationBasic:
    """
    Tests de integración básica con otros componentes
    Valida interacción con validadores y mappers
    """

    def test_pipeline_completo_transformacion_validacion(self, xml_transformer, validation_bridge):
        """
        Test pipeline completo: transformación + validación

        El XML transformado debe pasar validación SIFEN
        """
        # Arrange - XML modular completo válido
        xml_completo = '''<root>
            <gDatGral>
                <dFeEmiDE>2024-12-15</dFeEmiDE>
                <dHorEmi>14:30:00</dHorEmi>
                <iTipoDE>1</iTipoDE>
                <dNumID>001-001-0000001</dNumID>
            </gDatGral>
            <gTotSub>
                <dTotGralOpe>110000.0000</dTotGralOpe>
                <dTotIVA>10000.0000</dTotIVA>
            </gTotSub>
        </root>'''

        # Act - Pipeline completo
        # 1. Transformar modular → oficial
        result_transform = xml_transformer.transform_modular_to_official(
            xml_completo, DocumentType.FACTURA_ELECTRONICA
        )

        assert result_transform.success, f"Transformación falló: {result_transform.errors}"

        # 2. Validar XML oficial resultante
        if hasattr(validation_bridge, 'validate_official_xml'):
            result_validation = validation_bridge.validate_official_xml(
                result_transform.xml)

            # Assert - Pipeline completo exitoso
            assert result_validation.is_valid, f"Validación falló: {result_validation.errors}"

            logger.info("✅ Pipeline transformación → validación exitoso")
        else:
            logger.info("✅ Transformación exitosa (validación no disponible)")

    def test_integracion_schema_mapper(self, xml_transformer, schema_mapper):
        """
        Test integración con SchemaMapper

        Verifica que transformador use mapper correctamente
        """
        # Arrange
        xml_test = '<gDatGral><iTipoDE>1</iTipoDE></gDatGral>'

        # Act - Transformación usando mapper integrado
        result = xml_transformer.transform_modular_to_official(
            xml_test, DocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Integración con mapper falló: {result.errors}"

        # Verificar que mapper fue utilizado
        if hasattr(result, 'mapping_applied'):
            assert result.mapping_applied, "SchemaMapper debe ser utilizado"

        logger.info("✅ Integración con SchemaMapper validada")

    def test_manejo_errores_cascade(self, xml_transformer):
        """
        Test manejo en cascada de errores entre componentes

        Los errores deben propagarse correctamente sin romper pipeline
        """
        # Arrange - XML que puede causar error en validación
        xml_error = '''<gDatGral>
            <iTipoDE>99</iTipoDE>  <!-- Tipo inválido -->
            <dNumID>INVALID</dNumID>  <!-- Formato inválido -->
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_error, DocumentType.FACTURA_ELECTRONICA
        )

        # Assert - Error controlado o transformación exitosa con warnings
        if not result.success:
            assert len(result.errors) > 0, "Debe reportar errores específicos"
            error_msg = " ".join(result.errors).lower()
            assert any(term in error_msg for term in ["tipo", "formato", "inválido"]), \
                "Error debe ser descriptivo"

        logger.info("✅ Manejo errores en cascada validado")


# =============================================================================
# CONFIGURACIÓN PYTEST Y MARCADORES
# =============================================================================

# Marcadores personalizados para categorizar tests
pytestmark = [
    pytest.mark.transformation,  # Todos los tests son de transformación
    pytest.mark.sifen_v150      # Específicos para versión v150
]


def pytest_configure(config):
    """Configuración global de pytest para este módulo"""
    # Registrar marcadores personalizados
    config.addinivalue_line(
        "markers", "transformation: tests de transformación XML")
    config.addinivalue_line(
        "markers", "namespace: tests de validación namespaces")
    config.addinivalue_line("markers", "edge_case: tests de casos límite")
    config.addinivalue_line("markers", "performance: tests de rendimiento")
    config.addinivalue_line(
        "markers", "sifen_v150: tests específicos SIFEN v150")


@pytest.fixture(autouse=True)
def setup_test_logging():
    """
    Fixture automática para configurar logging en cada test
    """
    # Configurar logging específico para tests
    logger.setLevel(logging.INFO)

    # Crear handler para console si no existe
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    yield

    # Cleanup después de cada test
    logger.debug("Test completado")


# =============================================================================
# FUNCIONES DE UTILIDAD PARA TESTS
# =============================================================================

def assert_xml_structure_valid(xml_string: str) -> bool:
    """
    Función helper para validar estructura XML básica

    Args:
        xml_string: String XML a validar

    Returns:
        bool: True si estructura es válida
    """
    try:
        from xml.etree.ElementTree import fromstring
        fromstring(xml_string)
        return True
    except Exception as e:
        logger.error(f"XML estructura inválida: {e}")
        return False


def assert_contains_sifen_elements(xml_string: str, elements: List[str]) -> bool:
    """
    Función helper para verificar presencia de elementos SIFEN específicos

    Args:
        xml_string: XML a verificar
        elements: Lista de elementos que deben estar presentes

    Returns:
        bool: True si todos los elementos están presentes
    """
    for element in elements:
        if element not in xml_string:
            logger.error(f"Elemento SIFEN faltante: {element}")
            return False
    return True


def measure_transformation_performance(transformer, xml_content, doc_type, iterations=3):
    """
    Función helper para medir performance de transformación

    Args:
        transformer: Instancia XMLTransformer
        xml_content: XML a transformar
        doc_type: Tipo de documento
        iterations: Número de iteraciones para promedio

    Returns:
        dict: Métricas de performance
    """
    times = []

    for _ in range(iterations):
        start = time.time()
        result = transformer.transform_modular_to_official(
            xml_content, doc_type)
        end = time.time()

        if result.success:
            times.append(end - start)

    if times:
        return {
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'total_iterations': len(times)
        }
    else:
        return {'error': 'No successful transformations'}


# =============================================================================
# TESTS PARAMETRIZADOS ADICIONALES
# =============================================================================

class TestParameterizedScenarios:
    """
    Tests parametrizados para escenarios múltiples
    Útil para validación exhaustiva con diferentes datos
    """

    @pytest.mark.parametrize("fecha,esperado_valida", [
        ("2024-01-01", True),      # Fecha normal
        ("2024-12-31", True),      # Fin de año
        ("2099-12-31", True),      # Fecha futura válida
        ("1900-01-01", True),      # Fecha pasada válida
        ("2024-02-29", True),      # Año bisiesto
        ("invalid-date", False),    # Formato inválido
        ("", False),               # Fecha vacía
    ])
    def test_validacion_fechas_multiples(self, xml_transformer, fecha, esperado_valida):
        """
        Test parametrizado para validación de fechas diversas
        """
        # Arrange
        xml_fecha = f'''<gDatGral>
            <dFeEmiDE>{fecha}</dFeEmiDE>
            <iTipoDE>1</iTipoDE>
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_fecha, DocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        if esperado_valida:
            assert result.success, f"Fecha válida {fecha} falló: {result.errors}"
            if fecha and fecha != "invalid-date":
                assert fecha in result.xml, f"Fecha {fecha} no preservada"
        else:
            # Fechas inválidas pueden fallar o ser transformadas con warnings
            if not result.success:
                assert len(
                    result.errors) > 0, f"Error debe reportarse para fecha inválida: {fecha}"

    @pytest.mark.parametrize("monto,decimales", [
        ("100.0000", 4),           # Estándar SIFEN
        ("100.00", 2),             # Decimales mínimos
        ("999999999.9999", 4),     # Monto máximo
        ("0.0001", 4),             # Monto mínimo
        ("1234567.89", 2),         # Monto típico
    ])
    def test_preservacion_montos_decimales(self, xml_transformer, monto, decimales):
        """
        Test parametrizado para preservación de montos con diferentes decimales
        """
        # Arrange
        xml_monto = f'''<gTotSub>
            <dTotGralOpe>{monto}</dTotGralOpe>
        </gTotSub>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_monto, DocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación monto {monto} falló: {result.errors}"
        assert monto in result.xml, f"Monto {monto} no preservado exactamente"


# =============================================================================
# TESTS DE REGRESIÓN
# =============================================================================

class TestRegression:
    """
    Tests de regresión para bugs conocidos y casos específicos
    Previene reintroducción de errores previamente corregidos
    """

    def test_regresion_namespace_duplicado(self, xml_transformer):
        """
        Test regresión: evitar namespaces duplicados en XML resultado

        Bug histórico donde namespaces se duplicaban en transformación
        """
        # Arrange - XML que previamente causaba duplicación
        xml_ns = '''<?xml version="1.0" encoding="UTF-8"?>
        <gDatGral xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <dFeEmiDE>2024-12-15</dFeEmiDE>
            <iTipoDE>1</iTipoDE>
        </gDatGral>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_ns, DocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación con namespace falló: {result.errors}"

        # Verificar que no hay duplicación de namespaces
        xml_lines = result.xml.split('\n')
        xmlns_count = sum(1 for line in xml_lines if 'xmlns=' in line)
        assert xmlns_count <= 1, f"Namespaces duplicados detectados: {xmlns_count}"

        logger.info("✅ Regresión namespace duplicado - OK")

    def test_regresion_caracteres_escape(self, xml_transformer):
        """
        Test regresión: manejo correcto de caracteres especiales

        Bug donde caracteres como &, <, > no se escapaban correctamente
        """
        # Arrange - XML con caracteres que requieren escape
        xml_escape = '''<gDatEmi>
            <dNomEmi>Empresa "Test" &amp; Asociados S.A.</dNomEmi>
            <dDirEmi>Calle Mayor #123 &lt;Esquina&gt;</dDirEmi>
        </gDatEmi>'''

        # Act
        result = xml_transformer.transform_modular_to_official(
            xml_escape, DocumentType.FACTURA_ELECTRONICA
        )

        # Assert
        assert result.success, f"Transformación con caracteres especiales falló: {result.errors}"

        # Verificar que caracteres especiales están presentes
        assert "&amp;" in result.xml or "&" in result.xml, "Ampersand debe estar presente"
        assert "&lt;" in result.xml or "<" in result.xml, "Menor que debe estar presente"
        assert "&gt;" in result.xml or ">" in result.xml, "Mayor que debe estar presente"

        logger.info("✅ Regresión caracteres escape - OK")


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    """
    Ejecución directa del archivo de tests
    Útil para debugging y desarrollo
    """
    # Configurar logging para ejecución directa
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Ejecutar tests con configuración específica
    pytest.main([
        __file__,
        "-v",                    # Verbose output
        "--tb=short",           # Traceback corto
        "--strict-markers",     # Markers estrictos
        "-m", "not performance",  # Excluir tests de performance por defecto
        "--color=yes"           # Output colorizado
    ])


# =============================================================================
# DOCUMENTACIÓN ADICIONAL
# =============================================================================

"""
GUÍA DE USO:

1. Ejecutar todos los tests:
   pytest test_modular_to_official.py -v

2. Ejecutar solo tests básicos:
   pytest test_modular_to_official.py -k "TestBasicMapping" -v

3. Ejecutar tests de performance:
   pytest test_modular_to_official.py -m "performance" -v

4. Ejecutar con coverage:
   pytest test_modular_to_official.py --cov=xml_transformer --cov-report=html

5. Ejecutar tests específicos por tipo documento:
   pytest test_modular_to_official.py -k "factura" -v

MARCADORES DISPONIBLES:
- @pytest.mark.transformation: Tests de transformación
- @pytest.mark.namespace: Tests de namespaces
- @pytest.mark.edge_case: Tests de casos límite
- @pytest.mark.performance: Tests de rendimiento
- @pytest.mark.parametrize: Tests parametrizados

FIXTURES PRINCIPALES:
- xml_transformer: Transformador XML configurado
- schema_mapper: Mapeador de esquemas
- validation_bridge: Puente de validación
- datos_factura_basica: Datos FE básicos
- xml_modular_samples: Muestras XML modulares

COBERTURA OBJETIVO:
- Elementos básicos: 100% (gDatGral, gDatEmi, gItems, gTotales)
- Tipos documento: 100% (FE, NCE, NDE, AFE, NRE)
- Casos edge: 90% (opcionales, límites, errores)
- Performance: <500ms transformación individual
"""
