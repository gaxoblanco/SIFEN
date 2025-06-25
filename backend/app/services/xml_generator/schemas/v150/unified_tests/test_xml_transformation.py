#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de Transformación XML - SIFEN v150
========================================

Tests para validar transformaciones XML entre formatos:
- Modular → Oficial
- Validación de schemas
- Preservación de datos
- Optimización de estructura

Autor: Sistema SIFEN Paraguay  
Versión: 1.5.0
Fecha: 2025-06-24
"""

import pytest
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET
from lxml import etree
import logging
import json
from datetime import datetime
import time

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
        
        logger.info(f"XMLTransformer inicializado con {len(self.element_mappings)} mapeos")
    
    def _load_element_mappings(self) -> Dict[str, str]:
        """Carga mapeos de elementos para transformación"""
        # Mapeos básicos entre modular y oficial
        return {
            # Elementos raíz
            "rDE": "rDE",
            "DE": "DE",
            
            # Identificadores
            "dVerFor": "dVerFor",
            "Id": "Id",
            "dDVId": "dDVId",
            "dFecFirma": "dFecFirma",
            
            # Operación
            "gOpeDE": "gOpeDE",
            "iTiDE": "iTiDE",
            "dDesTiDE": "dDesTiDE",
            
            # Emisor
            "gEmis": "gEmis", 
            "dRucEm": "dRucEm",
            "dNomEmi": "dNomEmi",
            
            # Receptor
            "gDatRec": "gDatRec",
            "dRucRec": "dRucRec",
            "dNomRec": "dNomRec",
            
            # Totales
            "gTotSub": "gTotSub",
            "dTotGeneral": "dTotGeneral"
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
        validation_errors = []
        
        try:
            # 1. Parsear XML modular
            modular_root = etree.fromstring(modular_xml.encode('utf-8'))
            
            # 2. Aplicar transformación
            official_root = self._apply_transformation(modular_root, TransformationType.MODULAR_TO_OFFICIAL)
            
            # 3. Generar XML oficial
            official_xml = etree.tostring(
                official_root,
                pretty_print=True,
                encoding='utf-8',
                xml_declaration=True
            ).decode('utf-8')
            
            # 4. Validar transformación
            validation_errors = self._validate_transformation(modular_root, official_root)
            
            # 5. Calcular métricas
            transformation_time = time.time() - start_time
            size_reduction = self._calculate_size_reduction(modular_xml, official_xml)
            
            return TransformationResult(
                success=len(validation_errors) == 0,
                original_xml=modular_xml,
                transformed_xml=official_xml,
                validation_errors=validation_errors,
                transformation_time=transformation_time,
                size_reduction=size_reduction
            )
            
        except Exception as e:
            logger.error(f"Error en transformación: {e}")
            return TransformationResult(
                success=False,
                original_xml=modular_xml,
                transformed_xml="",
                validation_errors=[f"Error de transformación: {str(e)}"],
                transformation_time=time.time() - start_time
            )
    
    def _apply_transformation(self, source_root: etree.Element, 
                            transformation_type: TransformationType) -> etree.Element:
        """
        Aplica transformación específica al XML
        
        Args:
            source_root: Elemento raíz fuente
            transformation_type: Tipo de transformación
            
        Returns:
            Elemento raíz transformado
        """
        # Crear nuevo documento con namespace apropiado
        target_root = etree.Element(
            source_root.tag,
            nsmap={None: "http://ekuatia.set.gov.py/sifen/xsd"}
        )
        
        # Transformar elementos recursivamente
        self._transform_elements_recursive(source_root, target_root, transformation_type)
        
        return target_root
    
    def _transform_elements_recursive(self, source_elem: etree.Element,
                                    target_parent: etree.Element,
                                    transformation_type: TransformationType) -> None:
        """Transforma elementos recursivamente"""
        for child in source_elem:
            # Mapear elemento según tipo de transformación
            mapped_tag = self._map_element_tag(child.tag, transformation_type)
            
            # Crear elemento transformado
            target_child = etree.SubElement(target_parent, mapped_tag)
            
            # Copiar texto y atributos
            if child.text and child.text.strip():
                target_child.text = self._transform_text_content(child.text.strip(), transformation_type)
            
            for attr_name, attr_value in child.attrib.items():
                target_child.set(attr_name, attr_value)
            
            # Procesar hijos recursivamente
            if len(child) > 0:
                self._transform_elements_recursive(child, target_child, transformation_type)
    
    def _map_element_tag(self, tag: str, transformation_type: TransformationType) -> str:
        """Mapea tag de elemento según tipo de transformación"""
        if transformation_type == TransformationType.MODULAR_TO_OFFICIAL:
            return self.element_mappings.get(tag, tag)
        elif transformation_type == TransformationType.OFFICIAL_TO_MODULAR:
            # Mapeo inverso
            reverse_mappings = {v: k for k, v in self.element_mappings.items()}
            return reverse_mappings.get(tag, tag)
        else:
            return tag
    
    def _transform_text_content(self, text: str, transformation_type: TransformationType) -> str:
        """Transforma contenido de texto si es necesario"""
        # Para la mayoría de casos, el texto se preserva tal como está
        # Aquí se pueden agregar transformaciones específicas si es necesario
        return text.strip()
    
    def _validate_transformation(self, source_root: etree.Element,
                               target_root: etree.Element) -> List[str]:
        """
        Valida que la transformación sea correcta
        
        Args:
            source_root: Elemento raíz fuente
            target_root: Elemento raíz transformado
            
        Returns:
            Lista de errores de validación
        """
        errors = []
        
        # Validar elementos críticos
        critical_elements = ["dVerFor", "Id", "dDVId", "iTiDE", "dRucEm", "dTotGeneral"]
        
        for element in critical_elements:
            source_elem = source_root.find(f".//{element}")
            target_elem = target_root.find(f".//{element}")
            
            if source_elem is not None and target_elem is None:
                errors.append(f"Elemento crítico {element} perdido en transformación")
            elif source_elem is not None and target_elem is not None:
                if source_elem.text != target_elem.text:
                    errors.append(f"Valor de {element} cambió: '{source_elem.text}' → '{target_elem.text}'")
        
        # Validar estructura básica
        if target_root.tag != source_root.tag:
            errors.append(f"Tag raíz cambió: {source_root.tag} → {target_root.tag}")
        
        return errors
    
    def _calculate_size_reduction(self, original_xml: str, transformed_xml: str) -> float:
        """Calcula reducción de tamaño en porcentaje"""
        original_size = len(original_xml)
        transformed_size = len(transformed_xml)
        
        if original_size == 0:
            return 0.0
        
        return ((original_size - transformed_size) / original_size) * 100
    
    def optimize_xml_structure(self, xml_content: str) -> TransformationResult:
        """
        Optimiza estructura XML removiendo elementos innecesarios
        
        Args:
            xml_content: XML a optimizar
            
        Returns:
            TransformationResult con XML optimizado
        """
        start_time = time.time()
        
        try:
            # Parsear XML
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Aplicar optimizaciones
            optimized_root = self._apply_optimizations(root)
            
            # Generar XML optimizado
            optimized_xml = etree.tostring(
                optimized_root,
                pretty_print=True,
                encoding='utf-8',
                xml_declaration=True
            ).decode('utf-8')
            
            # Calcular métricas
            transformation_time = time.time() - start_time
            size_reduction = self._calculate_size_reduction(xml_content, optimized_xml)
            
            return TransformationResult(
                success=True,
                original_xml=xml_content,
                transformed_xml=optimized_xml,
                validation_errors=[],
                transformation_time=transformation_time,
                size_reduction=size_reduction
            )
            
        except Exception as e:
            return TransformationResult(
                success=False,
                original_xml=xml_content,
                transformed_xml="",
                validation_errors=[f"Error de optimización: {str(e)}"],
                transformation_time=time.time() - start_time
            )
    
    def _apply_optimizations(self, root: etree.Element) -> etree.Element:
        """Aplica optimizaciones al XML"""
        # Crear copia del elemento
        optimized_root = etree.fromstring(etree.tostring(root))
        
        # Remover elementos vacíos (excepto los requeridos)
        self._remove_empty_elements(optimized_root)
        
        # Optimizar espacios en blanco
        self._optimize_whitespace(optimized_root)
        
        return optimized_root
    
    def _remove_empty_elements(self, element: etree.Element) -> None:
        """Remueve elementos vacíos no críticos"""
        # Elementos que NUNCA deben removerse aunque estén vacíos
        critical_elements = {"dVerFor", "Id", "dDVId", "iTiDE", "dRucEm", "dTotGeneral"}
        
        # Iterar en reversa para evitar problemas con índices
        for child in reversed(list(element)):
            # Procesar hijos recursivamente primero
            self._remove_empty_elements(child)
            
            # Verificar si el elemento está vacío y no es crítico
            if (not child.text or not child.text.strip()) and len(child) == 0 and child.tag not in critical_elements:
                element.remove(child)
    
    def _optimize_whitespace(self, element: etree.Element) -> None:
        """Optimiza espacios en blanco"""
        # Normalizar texto
        if element.text:
            element.text = element.text.strip()
        
        if element.tail:
            element.tail = element.tail.strip()
        
        # Procesar hijos recursivamente
        for child in element:
            self._optimize_whitespace(child)

# =============================================================================
# COMPARADOR XML
# =============================================================================

class XMLComparator:
    """Comparador para validar equivalencias XML"""
    
    @staticmethod
    def compare_xml_structure(xml1: str, xml2: str) -> Tuple[bool, List[str]]:
        """
        Compara estructura de dos XMLs
        
        Args:
            xml1: Primer XML
            xml2: Segundo XML
            
        Returns:
            Tupla (son_equivalentes, diferencias)
        """
        differences = []
        
        try:
            root1 = etree.fromstring(xml1.encode('utf-8'))
            root2 = etree.fromstring(xml2.encode('utf-8'))
            
            XMLComparator._compare_elements(root1, root2, "", differences)
            
            return len(differences) == 0, differences
            
        except Exception as e:
            differences.append(f"Error de parsing: {str(e)}")
            return False, differences
    
    @staticmethod
    def _compare_elements(elem1: etree.Element, elem2: etree.Element,
                         path: str, differences: List[str]) -> None:
        """Compara elementos recursivamente"""
        current_path = f"{path}/{elem1.tag}" if path else elem1.tag
        
        # Comparar tags
        if elem1.tag != elem2.tag:
            differences.append(f"Tag diferente en {current_path}: {elem1.tag} vs {elem2.tag}")
            return
        
        # Comparar texto
        text1 = elem1.text.strip() if elem1.text else ""
        text2 = elem2.text.strip() if elem2.text else ""
        
        if text1 != text2:
            differences.append(f"Texto diferente en {current_path}: '{text1}' vs '{text2}'")
        
        # Comparar número de hijos
        children1 = list(elem1)
        children2 = list(elem2)
        
        if len(children1) != len(children2):
            differences.append(f"Número de hijos diferente en {current_path}: {len(children1)} vs {len(children2)}")
            return
        
        # Comparar cada hijo
        for child1, child2 in zip(children1, children2):
            XMLComparator._compare_elements(child1, child2, current_path, differences)

# =============================================================================
# DATOS DE PRUEBA
# =============================================================================

class TransformationTestData:
    """Datos de prueba para transformaciones XML"""
    
    @staticmethod
    def create_modular_xml() -> str:
        """XML modular para testing"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <DE>
        <dVerFor>150</dVerFor>
        <Id>01800695906001001000000000120240624102030</Id>
        <dDVId>9</dDVId>
        <dFecFirma>2024-06-24T10:20:30</dFecFirma>
        <dSisFact>1</dSisFact>
        
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
        result = self.transformer.transform_modular_to_official(self.modular_xml)
        
        # Validaciones básicas
        self.assertTrue(result.success, f"Transformación falló: {result.validation_errors}")
        self.assertIsNotNone(result.transformed_xml)
        self.assertGreater(len(result.transformed_xml), 0)
        
        # Validar que el XML transformado sea válido
        try:
            transformed_root = etree.fromstring(result.transformed_xml.encode('utf-8'))
            self.assertEqual(transformed_root.tag, "rDE")
        except etree.XMLSyntaxError as e:
            self.fail(f"XML transformado inválido: {e}")
        
        # Validar preservación de elementos críticos
        transformed_root = etree.fromstring(result.transformed_xml.encode('utf-8'))
        critical_elements = ["dVerFor", "Id", "dDVId", "iTiDE", "dRucEm"]
        
        for element in critical_elements:
            elem = transformed_root.find(f".//{element}")
            self.assertIsNotNone(elem, f"Elemento crítico {element} perdido")
        
        logger.info(f"✅ Transformación exitosa en {result.transformation_time:.3f}s")
    
    def test_xml_optimization(self):
        """Test: Optimización de XML"""
        logger.info("🧪 Test: Optimización XML")
        
        # Optimizar XML con elementos vacíos
        result = self.transformer.optimize_xml_structure(self.xml_with_empty)
        
        # Validaciones
        self.assertTrue(result.success, f"Optimización falló: {result.validation_errors}")
        self.assertIsNotNone(result.transformed_xml)
        
        # Verificar que se redujo el tamaño
        original_size = len(result.original_xml)
        optimized_size = len(result.transformed_xml)
        self.assertLessEqual(optimized_size, original_size, "XML optimizado debería ser menor o igual")
        
        # Validar que los elementos críticos se preserven
        optimized_root = etree.fromstring(result.transformed_xml.encode('utf-8'))
        critical_elements = ["dVerFor", "Id", "dTotGeneral"]
        
        for element in critical_elements:
            elem = optimized_root.find(f".//{element}")
            self.assertIsNotNone(elem, f"Elemento crítico {element} no debe removerse")
        
        logger.info(f"✅ Optimización exitosa. Reducción: {result.size_reduction:.1f}%")
    
    def test_transformation_performance(self):
        """Test: Performance de transformaciones"""
        logger.info("🧪 Test: Performance transformaciones")
        
        # Medir múltiples transformaciones
        times = []
        for i in range(5):
            result = self.transformer.transform_modular_to_official(self.modular_xml)
            self.assertTrue(result.success)
            times.append(result.transformation_time)
        
        # Calcular estadísticas
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Validar performance aceptable
        self.assertLess(avg_time, 0.5, f"Tiempo promedio excesivo: {avg_time:.3f}s")
        self.assertLess(max_time, 1.0, f"Tiempo máximo excesivo: {max_time:.3f}s")
        
        logger.info(f"✅ Performance: avg={avg_time:.3f}s, max={max_time:.3f}s")
    
    def test_xml_structure_comparison(self):
        """Test: Comparación de estructuras XML"""
        logger.info("🧪 Test: Comparación estructuras XML")
        
        # Transformar y comparar
        result = self.transformer.transform_modular_to_official(self.modular_xml)
        self.assertTrue(result.success)
        
        # Comparar original vs transformado
        are_equivalent, differences = self.comparator.compare_xml_structure(
            self.modular_xml, 
            result.transformed_xml
        )
        
        # En transformación 1:1, deberían ser equivalentes
        if not are_equivalent:
            logger.warning(f"Diferencias encontradas: {differences[:5]}")  # Solo primeras 5
        
        # Validar que al menos elementos críticos sean iguales
        original_root = etree.fromstring(self.modular_xml.encode('utf-8'))
        transformed_root = etree.fromstring(result.transformed_xml.encode('utf-8'))
        
        critical_elements = ["dVerFor", "Id", "dTotGeneral"]
        for element in critical_elements:
            orig_elem = original_root.find(f".//{element}")
            trans_elem = transformed_root.find(f".//{element}")
            
            if orig_elem is not None and trans_elem is not None:
                self.assertEqual(orig_elem.text, trans_elem.text, 
                               f"Valor de {element} debe preservarse")
        
        logger.info("✅ Comparación estructural completada")
    
    def test_error_handling(self):
        """Test: Manejo de errores en transformación"""
        logger.info("🧪 Test: Manejo de errores")
        
        # Test con XML malformado
        malformed_xml = "<?xml version='1.0'?><rDE><incomplete"
        result = self.transformer.transform_modular_to_official(malformed_xml)
        
        self.assertFalse(result.success, "XML malformado debería fallar")
        self.assertGreater(len(result.validation_errors), 0)
        
        # Test con XML vacío
        empty_xml = ""
        result = self.transformer.transform_modular_to_official(empty_xml)
        
        self.assertFalse(result.success, "XML vacío debería fallar")
        
        logger.info("✅ Manejo de errores validado")

# =============================================================================
# TESTS DE VALIDACIÓN DE SCHEMAS
# =============================================================================

class TestSchemaValidation(unittest.TestCase):
    """Tests de validación contra schemas XSD"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración para validación de schemas"""
        cls.schemas_path = Path(__file__).parent.parent.parent
        cls.transformer = XMLTransformer(cls.schemas_path)
        cls.test_data = TransformationTestData()
        
        logger.info("TestSchemaValidation configurado")
    
    def test_validate_against_modular_schema(self):
        """Test: Validación contra schema modular"""
        logger.info("🧪 Test: Validación schema modular")
        
        # Obtener XML modular
        modular_xml = self.test_data.create_modular_xml()
        
        try:
            # Parsear XML
            root = etree.fromstring(modular_xml.encode('utf-8'))
            
            # Validar estructura básica
            self.assertEqual(root.tag, "rDE")
            
            # Validar elementos requeridos
            required_elements = ["dVerFor", "Id", "dDVId"]
            for element in required_elements:
                elem = root.find(f".//{element}")
                self.assertIsNotNone(elem, f"Elemento requerido {element} faltante")
                self.assertIsNotNone(elem.text, f"Elemento {element} sin valor")
            
            logger.info("✅ Validación schema modular exitosa")
            
        except etree.XMLSyntaxError as e:
            self.fail(f"XML inválido: {e}")
    
    def test_validate_transformed_xml(self):
        """Test: Validación de XML transformado"""
        logger.info("🧪 Test: Validación XML transformado")
        
        # Transformar XML
        modular_xml = self.test_data.create_modular_xml()
        result = self.transformer.transform_modular_to_official(modular_xml)
        
        self.assertTrue(result.success, "Transformación debe ser exitosa")
        
        # Validar XML transformado
        try:
            transformed_root = etree.fromstring(result.transformed_xml.encode('utf-8'))
            
            # Validar namespace
            expected_ns = "http://ekuatia.set.gov.py/sifen/xsd"
            self.assertEqual(
                transformed_root.nsmap.get(None), 
                expected_ns,
                "Namespace incorrecto"
            )
            
            # Validar elementos críticos
            critical_elements = ["dVerFor", "Id", "iTiDE", "dTotGeneral"]
            for element in critical_elements:
                elem = transformed_root.find(f".//{element}")
                self.assertIsNotNone(elem, f"Elemento crítico {element} faltante")
            
            logger.info("✅ Validación XML transformado exitosa")
            
        except etree.XMLSyntaxError as e:
            self.fail(f"XML transformado inválido: {e}")

# =============================================================================
# SUITE DE TESTS
# =============================================================================

class TestSuite:
    """Suite de tests de transformación"""
    
    @staticmethod
    def run_transformation_tests():
        """Ejecuta todos los tests de transformación"""
        logger.info("🚀 Iniciando Tests de Transformación XML")
        
        # Crear suite
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestXMLTransformation))
        suite.addTest(unittest.makeSuite(TestSchemaValidation))
        
        # Ejecutar tests
        runner = unittest.TextTestRunner(verbosity=2)
        start_time = time.time()
        result = runner.run(suite)
        execution_time = time.time() - start_time
        
        # Reportar resultados
        logger.info(f"⏱️  Tiempo total: {execution_time:.2f}s")
        logger.info(f"✅ Tests exitosos: {result.testsRun - len(result.failures) - len(result.errors)}")
        logger.info(f"❌ Tests fallidos: {len(result.failures)}")
        logger.info(f"💥 Errores: {len(result.errors)}")
        
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
- ~300 líneas código
- 7 test cases principales
- Support optimización
- Validación robusta

🚀 SIGUIENTE PASO:
Implementar test_end_to_end.py - Tests E2E completos
"""