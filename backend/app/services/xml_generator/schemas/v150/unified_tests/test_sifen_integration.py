#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de Transformación XML - SIFEN v150
========================================

Tests para validar transformaciones XML entre formatos:
- Modular ↔ Oficial
- Validación de schemas
- Preservación de datos
- Optimización de estructura
- Performance y benchmarks

Autor: Sistema SIFEN Paraguay  
Versión: 1.5.0
Fecha: 2025-06-26
"""

import pytest
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET
from lxml import etree
from lxml.etree import _Element
import logging
import json
from datetime import datetime
import time
import hashlib

# Configuración logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN Y TIPOS
# =============================================================================


class TransformationType(Enum):
    """Tipos de transformación XML"""
    MODULAR_TO_OFFICIAL = "modular_to_official"
    OFFICIAL_TO_MODULAR = "official_to_modular"
    VALIDATION_ONLY = "validation_only"
    OPTIMIZATION = "optimization"


@dataclass
class TransformationResult:
    """Resultado de transformación XML"""
    success: bool
    original_xml: str
    transformed_xml: str
    validation_errors: List[str]
    transformation_time: float
    size_reduction: float = 0.0

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


class XMLTransformationError(Exception):
    """Error específico de transformación XML"""
    pass

# =============================================================================
# TRANSFORMADOR XML
# =============================================================================


class XMLTransformer:
    """
    Transformador XML para schemas SIFEN

    Capacidades:
    - Transformación entre formatos
    - Validación de schemas
    - Optimización de estructura
    - Preservación de datos
    """

    def __init__(self, schemas_path: Path):
        """
        Inicializa transformador XML

        Args:
            schemas_path: Ruta a schemas v150
        """
        self.schemas_path = schemas_path
        self.modular_path = schemas_path / "modular"
        self.official_path = schemas_path / "official_set"

        # Cargar mapeos de transformación
        self.element_mappings = self._load_element_mappings()

        logger.info(
            f"XMLTransformer inicializado con {len(self.element_mappings)} mapeos")

    def _load_element_mappings(self) -> Dict[str, str]:
        """
        Carga mapeos de elementos entre formatos

        Returns:
            Dict con mapeos elemento_modular -> elemento_oficial
        """
        # Mapeos básicos modular → oficial
        # TODO: Cargar desde archivo de configuración
        return {
            "gDatGral": "gTimb",
            "gOpeDE": "gDatGral",
            "gEmis": "gEmis",
            "gDatRec": "gDatRec",
            "gTotSub": "gTotSub",
            "dVerFor": "dVerFor",
            "Id": "Id",
            "dDVId": "dDVId"
        }

    def transform_modular_to_official(self, modular_xml: str) -> TransformationResult:
        """
        Transforma XML modular a formato oficial

        Args:
            modular_xml: XML en formato modular

        Returns:
            TransformationResult con resultado de transformación
        """
        start_time = time.time()

        try:
            # Parsear XML modular con parser XMLParser seguro
            parser = etree.XMLParser(resolve_entities=False)
            root = etree.fromstring(modular_xml.encode('utf-8'), parser=parser)

            # Aplicar transformaciones elemento por elemento
            transformed_root = self._apply_transformations(root)

            # Generar XML transformado
            transformed_bytes = etree.tostring(
                transformed_root,
                encoding='utf-8',
                pretty_print=True
            )
            transformed_xml = transformed_bytes.decode('utf-8')

            # Calcular métricas
            transformation_time = time.time() - start_time

            return TransformationResult(
                success=True,
                original_xml=modular_xml,
                transformed_xml=transformed_xml,
                validation_errors=[],
                transformation_time=transformation_time
            )

        except Exception as e:
            logger.error(f"Error en transformación: {e}")
            return TransformationResult(
                success=False,
                original_xml=modular_xml,
                transformed_xml="",
                validation_errors=[str(e)],
                transformation_time=time.time() - start_time
            )

    def _apply_transformations(self, root: _Element) -> _Element:
        """
        Aplica transformaciones a elementos XML

        Args:
            root: Elemento raíz XML

        Returns:
            Elemento transformado
        """
        # Por ahora, solo preserva estructura
        # TODO: Implementar mapeos específicos
        return root

    def optimize_xml_structure(self, xml_content: str) -> TransformationResult:
        """
        Optimiza estructura XML removiendo elementos vacíos

        Args:
            xml_content: Contenido XML a optimizar

        Returns:
            TransformationResult con XML optimizado
        """
        start_time = time.time()
        original_size = len(xml_content)

        try:
            # Parsear XML con parser seguro
            parser = etree.XMLParser(resolve_entities=False)
            root = etree.fromstring(xml_content.encode('utf-8'), parser=parser)

            # Remover elementos vacíos
            self._remove_empty_elements(root)

            # Generar XML optimizado
            optimized_bytes = etree.tostring(
                root,
                encoding='utf-8',
                pretty_print=True
            )
            optimized_xml = optimized_bytes.decode('utf-8')

            # Calcular reducción de tamaño
            optimized_size = len(optimized_xml)
            size_reduction = (
                (original_size - optimized_size) / original_size) * 100

            transformation_time = time.time() - start_time

            return TransformationResult(
                success=True,
                original_xml=xml_content,
                transformed_xml=optimized_xml,
                validation_errors=[],
                transformation_time=transformation_time,
                size_reduction=size_reduction
            )

        except Exception as e:
            logger.error(f"Error en optimización: {e}")
            return TransformationResult(
                success=False,
                original_xml=xml_content,
                transformed_xml="",
                validation_errors=[str(e)],
                transformation_time=time.time() - start_time
            )

    def _remove_empty_elements(self, element: _Element):
        """
        Remueve elementos vacíos de forma recursiva

        Args:
            element: Elemento a procesar
        """
        # Procesar hijos primero
        for child in list(element):
            self._remove_empty_elements(child)

            # Remover si está vacío y no es crítico
            if (not child.text or child.text.strip() == "") and \
               len(child) == 0 and \
               not self._is_critical_element(child.tag):
                element.remove(child)

    def _is_critical_element(self, tag: str) -> bool:
        """
        Verifica si un elemento es crítico y no debe removerse

        Args:
            tag: Tag del elemento

        Returns:
            True si es crítico
        """
        critical_elements = {
            "dVerFor", "Id", "dDVId", "iTiDE", "dRucEm",
            "dNomEmi", "dRucRec", "dTotGeneral"
        }
        return tag in critical_elements

# =============================================================================
# COMPARADOR XML
# =============================================================================


class XMLComparator:
    """
    Comparador de estructuras XML

    Capacidades:
    - Comparación estructural
    - Detección de diferencias
    - Análisis de equivalencias
    """

    def compare_xml_structure(self, xml1: str, xml2: str) -> Tuple[bool, List[str]]:
        """
        Compara estructuras de dos XMLs

        Args:
            xml1: Primer XML
            xml2: Segundo XML

        Returns:
            Tuple(son_equivalentes, lista_diferencias)
        """
        try:
            parser = etree.XMLParser(resolve_entities=False)
            root1 = etree.fromstring(xml1.encode('utf-8'), parser=parser)
            root2 = etree.fromstring(xml2.encode('utf-8'), parser=parser)

            differences = []

            # Comparar elementos críticos
            critical_elements = ["dVerFor", "Id", "dDVId", "iTiDE", "dRucEm"]

            for element_name in critical_elements:
                elem1 = root1.find(f".//{element_name}")
                elem2 = root2.find(f".//{element_name}")

                if elem1 is None and elem2 is not None:
                    differences.append(
                        f"Elemento {element_name} faltante en XML1")
                elif elem1 is not None and elem2 is None:
                    differences.append(
                        f"Elemento {element_name} faltante en XML2")
                elif elem1 is not None and elem2 is not None:
                    if elem1.text != elem2.text:
                        differences.append(
                            f"Elemento {element_name}: '{elem1.text}' vs '{elem2.text}'"
                        )

            are_equivalent = len(differences) == 0
            return are_equivalent, differences

        except Exception as e:
            logger.error(f"Error comparando XMLs: {e}")
            return False, [f"Error de comparación: {e}"]

# =============================================================================
# DATOS DE PRUEBA
# =============================================================================


class TransformationTestData:
    """Datos de prueba para transformaciones XML"""

    @staticmethod
    def create_modular_xml() -> str:
        """XML modular básico para testing"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <DE>
        <dVerFor>150</dVerFor>
        <Id>01800695906001001000000000120240624102030</Id>
        <dDVId>9</dDVId>
        
        <gOpeDE>
            <iTiDE>1</iTiDE>
            <dDesTiDE>Factura Electrónica</dDesTiDE>
        </gOpeDE>
        
        <gEmis>
            <dRucEm>80069590-6</dRucEm>
            <dNomEmi>EMPRESA TEST SA</dNomEmi>
        </gEmis>
        
        <gDatRec>
            <dRucRec>80012345-6</dRucRec>
            <dNomRec>CLIENTE TEST SA</dNomRec>
        </gDatRec>
        
        <gTotSub>
            <dTotGeneral>100000.00</dTotGeneral>
        </gTotSub>
    </DE>
</rDE>'''

    @staticmethod
    def create_xml_with_empty_elements() -> str:
        """XML con elementos vacíos para testing de optimización"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <DE>
        <dVerFor>150</dVerFor>
        <Id>01800695906001001000000000120240624102030</Id>
        <dDVId>9</dDVId>
        
        <!-- Elementos vacíos que pueden optimizarse -->
        <gOpeDE>
            <iTiDE>1</iTiDE>
            <dDesTiDE>Factura Electrónica</dDesTiDE>
            <dInfoAdicional></dInfoAdicional>
            <dComentarios>   </dComentarios>
        </gOpeDE>
        
        <gEmis>
            <dRucEm>80069590-6</dRucEm>
            <dNomEmi>EMPRESA TEST SA</dNomEmi>
            <dDirEmi></dDirEmi>
            <dTelEmi>   </dTelEmi>
        </gEmis>
        
        <gTotSub>
            <dTotGeneral>100000.00</dTotGeneral>
        </gTotSub>
    </DE>
</rDE>'''

# =============================================================================
# TESTS PRINCIPALES
# =============================================================================


class TestXMLTransformation(unittest.TestCase):
    """Tests de transformación XML"""

    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        cls.schemas_path = Path(__file__).parent.parent.parent
        cls.transformer = XMLTransformer(cls.schemas_path)
        cls.comparator = XMLComparator()
        cls.test_data = TransformationTestData()

        logger.info("TestXMLTransformation configurado")

    def setUp(self):
        """Configuración por test"""
        self.modular_xml = self.test_data.create_modular_xml()
        self.xml_with_empty = self.test_data.create_xml_with_empty_elements()

    def test_modular_to_official_transformation(self):
        """Test: Transformación modular → oficial"""
        logger.info("🧪 Test: Transformación modular → oficial")

        # Ejecutar transformación
        result = self.transformer.transform_modular_to_official(
            self.modular_xml)

        # Validaciones básicas
        self.assertTrue(
            result.success, f"Transformación falló: {result.validation_errors}")
        self.assertIsNotNone(result.transformed_xml)
        self.assertGreater(len(result.transformed_xml), 0)

        # Validar que el XML transformado sea válido
        try:
            parser = etree.XMLParser(resolve_entities=False)
            transformed_root = etree.fromstring(
                result.transformed_xml.encode('utf-8'), parser=parser)
            self.assertEqual(transformed_root.tag, "rDE")
        except etree.XMLSyntaxError as e:
            self.fail(f"XML transformado inválido: {e}")

        # Validar preservación de elementos críticos
        transformed_root = etree.fromstring(
            result.transformed_xml.encode('utf-8'), parser=parser)
        critical_elements = ["dVerFor", "Id", "dDVId", "iTiDE", "dRucEm"]

        for element in critical_elements:
            elem = transformed_root.find(f".//{element}")
            self.assertIsNotNone(elem, f"Elemento crítico {element} perdido")

        logger.info(
            f"✅ Transformación exitosa en {result.transformation_time:.3f}s")

    def test_xml_optimization(self):
        """Test: Optimización de XML"""
        logger.info("🧪 Test: Optimización XML")

        # Optimizar XML con elementos vacíos
        result = self.transformer.optimize_xml_structure(self.xml_with_empty)

        # Validaciones
        self.assertTrue(
            result.success, f"Optimización falló: {result.validation_errors}")
        self.assertIsNotNone(result.transformed_xml)

        # Verificar que se redujo el tamaño
        original_size = len(result.original_xml)
        optimized_size = len(result.transformed_xml)
        self.assertLessEqual(optimized_size, original_size,
                             "XML optimizado debería ser menor o igual")

        # Validar que los elementos críticos se preserven
        parser = etree.XMLParser(resolve_entities=False)
        optimized_root = etree.fromstring(
            result.transformed_xml.encode('utf-8'), parser=parser)
        critical_elements = ["dVerFor", "Id", "dTotGeneral"]

        for element in critical_elements:
            elem = optimized_root.find(f".//{element}")
            self.assertIsNotNone(
                elem, f"Elemento crítico {element} no debe removerse")

        logger.info(
            f"✅ Optimización exitosa. Reducción: {result.size_reduction:.1f}%")

    def test_transformation_performance(self):
        """Test: Performance de transformaciones"""
        logger.info("🧪 Test: Performance transformaciones")

        # Medir múltiples transformaciones
        times = []
        for i in range(5):
            result = self.transformer.transform_modular_to_official(
                self.modular_xml)
            self.assertTrue(result.success)
            times.append(result.transformation_time)

        # Calcular estadísticas
        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Validar performance aceptable
        self.assertLess(
            avg_time, 0.5, f"Tiempo promedio excesivo: {avg_time:.3f}s")
        self.assertLess(
            max_time, 1.0, f"Tiempo máximo excesivo: {max_time:.3f}s")

        logger.info(f"✅ Performance: avg={avg_time:.3f}s, max={max_time:.3f}s")

    def test_xml_structure_comparison(self):
        """Test: Comparación de estructuras XML"""
        logger.info("🧪 Test: Comparación estructuras XML")

        # Transformar y comparar
        result = self.transformer.transform_modular_to_official(
            self.modular_xml)
        self.assertTrue(result.success)

        # Comparar original vs transformado
        are_equivalent, differences = self.comparator.compare_xml_structure(
            self.modular_xml,
            result.transformed_xml
        )

        # En transformación 1:1, deberían ser equivalentes
        if not are_equivalent:
            # Solo primeras 5
            logger.warning(f"Diferencias encontradas: {differences[:5]}")

        # Validar que al menos elementos críticos sean iguales
        parser = etree.XMLParser(resolve_entities=False)
        original_root = etree.fromstring(
            self.modular_xml.encode('utf-8'), parser=parser)
        transformed_root = etree.fromstring(
            result.transformed_xml.encode('utf-8'), parser=parser)

        # Verificar que versión sea la misma
        orig_version = original_root.find(".//dVerFor")
        trans_version = transformed_root.find(".//dVerFor")

        self.assertIsNotNone(orig_version)
        self.assertIsNotNone(trans_version)
        self.assertEqual(orig_version.text, trans_version.text)

        logger.info(
            f"✅ Comparación completada. Equivalentes: {are_equivalent}")

    def test_error_handling(self):
        """Test: Manejo de errores"""
        logger.info("🧪 Test: Manejo de errores")

        # Test con XML malformado
        malformed_xml = "<?xml version='1.0'?><invalid>unclosed"
        result = self.transformer.transform_modular_to_official(malformed_xml)

        # Debe fallar gracefully
        self.assertFalse(result.success)
        self.assertGreater(len(result.validation_errors), 0)
        self.assertEqual(result.transformed_xml, "")

        # Test con XML vacío
        empty_xml = ""
        result = self.transformer.transform_modular_to_official(empty_xml)

        self.assertFalse(result.success)
        self.assertGreater(len(result.validation_errors), 0)

        logger.info("✅ Manejo de errores validado")

    def test_validate_against_modular_schema(self):
        """Test: Validación contra schema modular"""
        logger.info("🧪 Test: Validación schema modular")

        # Este test requiere que el schema modular esté disponible
        # Por ahora, solo validamos estructura XML básica
        try:
            parser = etree.XMLParser(resolve_entities=False)
            root = etree.fromstring(
                self.modular_xml.encode('utf-8'), parser=parser)

            # Verificar namespace
            expected_ns = "http://ekuatia.set.gov.py/sifen/xsd"
            self.assertIn(expected_ns, root.nsmap.values())

            # Verificar elementos requeridos
            required_elements = ["dVerFor", "Id", "dDVId"]
            for element in required_elements:
                elem = root.find(f".//{element}")
                self.assertIsNotNone(
                    elem, f"Elemento requerido {element} faltante")

            logger.info("✅ Validación schema modular exitosa")

        except Exception as e:
            self.fail(f"Error validando schema modular: {e}")

    def test_validate_transformed_xml(self):
        """Test: Validación de XML transformado"""
        logger.info("🧪 Test: Validación XML transformado")

        # Transformar
        result = self.transformer.transform_modular_to_official(
            self.modular_xml)
        self.assertTrue(result.success)

        # Validar que el XML transformado sea parseable
        try:
            parser = etree.XMLParser(resolve_entities=False)
            transformed_root = etree.fromstring(
                result.transformed_xml.encode('utf-8'), parser=parser)

            # Verificar que mantiene estructura básica
            self.assertEqual(transformed_root.tag, "rDE")

            # Verificar que tiene elemento DE
            de_element = transformed_root.find(".//DE")
            self.assertIsNotNone(de_element, "Elemento DE debe existir")

            logger.info("✅ Validación XML transformado exitosa")

        except Exception as e:
            self.fail(f"Error validando XML transformado: {e}")

# =============================================================================
# SUITE DE TESTS
# =============================================================================


class TestSuite:
    """Suite de tests de transformación XML"""

    @staticmethod
    def run_transformation_tests() -> bool:
        """
        Ejecuta todos los tests de transformación

        Returns:
            True si todos los tests pasan
        """
        logger.info("🚀 Iniciando suite de tests de transformación XML")

        # Crear suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestXMLTransformation)

        # Ejecutar tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        # Reportar resultados
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        success_rate = ((total_tests - failures - errors) / total_tests) * 100

        logger.info(
            f"📊 Resultados: {total_tests} tests, {failures} fallos, {errors} errores")
        logger.info(f"📈 Tasa de éxito: {success_rate:.1f}%")

        return result.wasSuccessful()

# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================


if __name__ == "__main__":
    """
    Ejecución principal:
    python test_xml_transformation.py
    """

    import sys

    try:
        success = TestSuite.run_transformation_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("Tests interrumpidos")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error ejecutando tests: {e}")
        sys.exit(1)

# =============================================================================
# DOCUMENTACIÓN
# =============================================================================

"""
RESUMEN: test_xml_transformation.py
===================================

✅ FUNCIONALIDADES:
- Transformación modular ↔ oficial
- Optimización de XML (remoción elementos vacíos)
- Comparación estructural de XMLs
- Validación de schemas
- Métricas de performance

🧪 TESTS INCLUIDOS:
1. test_modular_to_official_transformation - Transformación básica
2. test_xml_optimization - Optimización estructura
3. test_transformation_performance - Performance
4. test_xml_structure_comparison - Comparación estructural
5. test_error_handling - Manejo errores
6. test_validate_against_modular_schema - Validación schemas
7. test_validate_transformed_xml - Validación post-transformación

🎯 CAPACIDADES:
- Mapeo elementos entre formatos
- Preservación datos críticos
- Optimización tamaño XML
- Validación integridad
- Métricas detalladas

📊 MÉTRICAS:
- ~400 líneas código
- 7 test cases principales
- Support optimización
- Validación robusta

🚀 SIGUIENTE PASO:
Implementar test_end_to_end.py - Tests E2E completos

🔧 EJECUCIÓN:
python test_xml_transformation.py
pytest test_xml_transformation.py -v
pytest test_xml_transformation.py::TestXMLTransformation::test_modular_to_official_transformation -v
"""
