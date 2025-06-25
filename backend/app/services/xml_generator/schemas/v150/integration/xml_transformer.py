"""
XML Transformer v150 - Transformación XML Bidireccional Modular ↔ Oficial

Este módulo implementa la transformación completa de documentos XML entre el formato
modular (optimizado para desarrollo) y el formato oficial SET (requerido por SIFEN),
manteniendo la integridad semántica y la compatibilidad total.

Responsabilidades Principales:
1. Transformar XML modular a formato oficial SET
2. Transformar XML oficial SET a formato modular
3. Preservar integridad semántica durante transformaciones
4. Aplicar namespace y validaciones apropiadas
5. Optimizar transformaciones para performance
6. Proporcionar transformaciones idempotentes (A→B→A = A)

Patrones Implementados:
- Transformer Pattern: Para transformaciones estructuradas
- Template Method: Para flujo común de transformación
- Chain of Responsibility: Para pipeline de transformaciones
- Visitor Pattern: Para procesamiento de elementos XML

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
Fecha: 2025-06-24
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import time
import hashlib
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring, ElementTree
from collections import defaultdict
import re

# Imports de módulos de integración
from .schema_mapper import (
    SchemaMapper,
    DocumentType,
    MappingDirection,
    MappingContext,
    MappingResult,
    create_mapping_context
)
from .validation_bridge import (
    ValidationBridge,
    ValidationMode,
    HybridValidationResult,
    create_validation_config
)

# Configuración de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# =====================================
# ENUMS Y CONSTANTES
# =====================================

class TransformationDirection(Enum):
    """Direcciones de transformación disponibles"""
    MODULAR_TO_OFFICIAL = "modular_to_official"
    OFFICIAL_TO_MODULAR = "official_to_modular"
    BIDIRECTIONAL = "bidirectional"


class TransformationMode(Enum):
    """Modos de transformación"""
    STRICT = "strict"                # Transformación estricta con validación
    LENIENT = "lenient"             # Transformación permisiva
    PRESERVE_UNKNOWN = "preserve"    # Preservar elementos desconocidos
    OPTIMIZED = "optimized"         # Optimizada para performance


class TransformationStrategy(Enum):
    """Estrategias de transformación"""
    DIRECT_MAPPING = "direct"       # Mapeo directo usando schema_mapper
    TEMPLATE_BASED = "template"     # Basado en plantillas XML
    SEMANTIC_ANALYSIS = "semantic"  # Análisis semántico profundo
    HYBRID = "hybrid"               # Combinación de estrategias


class NamespaceMode(Enum):
    """Modos de manejo de namespaces"""
    PRESERVE = "preserve"           # Preservar namespaces originales
    TRANSFORM = "transform"         # Transformar según destino
    STRIP = "strip"                # Remover namespaces
    NORMALIZE = "normalize"         # Normalizar namespaces


# =====================================
# DATACLASSES PARA CONFIGURACIÓN
# =====================================

@dataclass
class TransformationConfig:
    """
    Configuración para transformaciones XML

    Attributes:
        strategy: Estrategia de transformación a usar
        mode: Modo de transformación
        namespace_mode: Manejo de namespaces
        validate_input: Validar XML de entrada
        validate_output: Validar XML de salida
        preserve_comments: Preservar comentarios XML
        preserve_processing_instructions: Preservar PIs
        enable_caching: Habilitar cache de transformaciones
        timeout_seconds: Timeout para transformaciones
        max_depth: Profundidad máxima de elementos
    """
    strategy: TransformationStrategy = TransformationStrategy.HYBRID
    mode: TransformationMode = TransformationMode.STRICT
    namespace_mode: NamespaceMode = NamespaceMode.TRANSFORM
    validate_input: bool = True
    validate_output: bool = True
    preserve_comments: bool = False
    preserve_processing_instructions: bool = False
    enable_caching: bool = True
    timeout_seconds: int = 30
    max_depth: int = 50


@dataclass
class TransformationContext:
    """
    Contexto para operaciones de transformación

    Attributes:
        document_type: Tipo de documento siendo transformado
        direction: Dirección de la transformación
        source_encoding: Codificación del XML origen
        target_encoding: Codificación del XML destino
        preserve_formatting: Preservar formato del XML
        custom_variables: Variables personalizadas
        metadata: Metadatos adicionales
    """
    document_type: DocumentType
    direction: TransformationDirection
    source_encoding: str = "utf-8"
    target_encoding: str = "utf-8"
    preserve_formatting: bool = False
    custom_variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationResult:
    """
    Resultado de una operación de transformación

    Attributes:
        success: Indica si la transformación fue exitosa
        transformed_xml: XML resultante de la transformación
        original_xml: XML original (para referencia)
        validation_result: Resultado de validación del XML transformado
        transformation_log: Log detallado de la transformación
        performance_metrics: Métricas de performance (solo números)
        metadata: Metadatos adicionales (strings, etc.)
        warnings: Advertencias durante la transformación
        errors: Errores durante la transformación
    """
    success: bool
    transformed_xml: str = ""
    original_xml: str = ""
    validation_result: Optional[HybridValidationResult] = None
    transformation_log: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def get_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del resultado de transformación"""
        return {
            "success": self.success,
            "has_transformed_xml": bool(self.transformed_xml),
            "validation_passed": self.validation_result.overall_valid if self.validation_result else None,
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "execution_time_ms": self.performance_metrics.get("total_time", 0),
            "xml_size_bytes": len(self.transformed_xml.encode('utf-8')) if self.transformed_xml else 0
        }


# =====================================
# INTERFACES ABSTRACTAS
# =====================================

class XMLTransformationStrategy(ABC):
    """
    Interfaz abstracta para estrategias de transformación XML

    Define el contrato que deben cumplir todas las estrategias
    de transformación implementadas en el sistema.
    """

    @abstractmethod
    def transform(
        self,
        xml_content: str,
        context: TransformationContext,
        config: TransformationConfig
    ) -> TransformationResult:
        """
        Transforma XML según la estrategia implementada

        Args:
            xml_content: Contenido XML a transformar
            context: Contexto de la transformación
            config: Configuración de transformación

        Returns:
            TransformationResult: Resultado de la transformación
        """
        pass

    @abstractmethod
    def validate_compatibility(
        self,
        context: TransformationContext
    ) -> Tuple[bool, List[str]]:
        """
        Valida si esta estrategia es compatible con el contexto

        Args:
            context: Contexto de transformación

        Returns:
            Tuple[bool, List[str]]: (es_compatible, lista_errores)
        """
        pass


class XMLProcessor(ABC):
    """
    Interfaz abstracta para procesadores XML especializados

    Permite implementar procesadores específicos para diferentes
    aspectos de la transformación (namespaces, elementos, atributos).
    """

    @abstractmethod
    def process(
        self,
        element: Element,
        context: TransformationContext
    ) -> Element:
        """
        Procesa un elemento XML

        Args:
            element: Elemento a procesar
            context: Contexto de transformación

        Returns:
            Element: Elemento procesado
        """
        pass


# =====================================
# PROCESADORES ESPECIALIZADOS
# =====================================

class NamespaceProcessor(XMLProcessor):
    """
    Procesador especializado para manejo de namespaces

    Maneja la transformación y normalización de namespaces
    según las reglas SIFEN y el modo configurado.
    """

    # Namespaces oficiales SIFEN
    OFFICIAL_NAMESPACES = {
        "default": "http://ekuatia.set.gov.py/sifen/xsd",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "ds": "http://www.w3.org/2000/09/xmldsig#"
    }

    # Namespaces modulares (para desarrollo)
    MODULAR_NAMESPACES = {
        "default": "http://modular.sifen.local/xsd",
        "mod": "http://modular.sifen.local/extensions"
    }

    def process(
        self,
        element: Element,
        context: TransformationContext
    ) -> Element:
        """Procesa namespaces según el contexto de transformación"""

        if context.direction == TransformationDirection.MODULAR_TO_OFFICIAL:
            return self._apply_official_namespaces(element)
        elif context.direction == TransformationDirection.OFFICIAL_TO_MODULAR:
            return self._apply_modular_namespaces(element)
        else:
            return element

    def _apply_official_namespaces(self, element: Element) -> Element:
        """Aplica namespaces oficiales SIFEN"""

        # Establecer namespace por defecto
        if not element.tag.startswith("{"):
            element.tag = f"{{{self.OFFICIAL_NAMESPACES['default']}}}{element.tag}"

        # Agregar declaraciones de namespace en elemento raíz
        # En ElementTree, asumimos que el elemento pasado es el raíz si no tiene prefijo
        element.set("xmlns", self.OFFICIAL_NAMESPACES["default"])
        element.set("{http://www.w3.org/2000/xmlns/}xsi",
                    self.OFFICIAL_NAMESPACES["xsi"])

        # Agregar schemaLocation si no existe
        schema_location = f"{self.OFFICIAL_NAMESPACES['default']} DE_v150.xsd"
        element.set(
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", schema_location)

        return element

    def _apply_modular_namespaces(self, element: Element) -> Element:
        """Aplica namespaces modulares"""

        # Remover namespace oficial y aplicar modular
        if element.tag.startswith(f"{{{self.OFFICIAL_NAMESPACES['default']}}}"):
            local_name = element.tag.split("}")[-1]
            element.tag = f"{{{self.MODULAR_NAMESPACES['default']}}}{local_name}"

        return element


class ElementStructureProcessor(XMLProcessor):
    """
    Procesador para transformación de estructura de elementos

    Maneja la reorganización y transformación de elementos XML
    según las reglas de mapeo entre schemas.
    """

    def __init__(self, schema_mapper: SchemaMapper):
        self.schema_mapper = schema_mapper

    def process(
        self,
        element: Element,
        context: TransformationContext
    ) -> Element:
        """Procesa estructura de elementos usando schema mapper"""

        try:
            # Crear contexto de mapeo
            mapping_direction = (
                MappingDirection.MODULAR_TO_OFFICIAL
                if context.direction == TransformationDirection.MODULAR_TO_OFFICIAL
                else MappingDirection.OFFICIAL_TO_MODULAR
            )

            mapping_context = create_mapping_context(
                document_type=context.document_type,
                direction=mapping_direction
            )

            # Ejecutar mapeo
            if mapping_direction == MappingDirection.MODULAR_TO_OFFICIAL:
                mapping_result = self.schema_mapper.map_to_official(
                    element, mapping_context)
            else:
                mapping_result = self.schema_mapper.map_to_modular(
                    element, mapping_context)

            if mapping_result.success and mapping_result.mapped_element is not None:
                return mapping_result.mapped_element
            else:
                logger.warning(f"Mapeo falló para elemento {element.tag}")
                return element

        except Exception as e:
            logger.error(f"Error procesando estructura de elemento: {str(e)}")
            return element


class DataIntegrityProcessor(XMLProcessor):
    """
    Procesador para garantizar integridad de datos

    Valida y corrige datos durante la transformación para
    mantener consistencia semántica.
    """

    def process(
        self,
        element: Element,
        context: TransformationContext
    ) -> Element:
        """Procesa integridad de datos en elemento"""

        # Validar formatos de fecha
        self._validate_date_formats(element)

        # Validar formatos numéricos
        self._validate_numeric_formats(element)

        # Validar códigos SIFEN
        self._validate_sifen_codes(element)

        return element

    def _validate_date_formats(self, element: Element):
        """Valida y normaliza formatos de fecha"""
        date_patterns = {
            r'dFe.*DE': r'\d{4}-\d{2}-\d{2}',  # Fechas de emisión
            r'dHor.*': r'\d{2}:\d{2}:\d{2}'    # Horas
        }

        for child in element:
            for pattern, expected_format in date_patterns.items():
                if re.match(pattern, child.tag) and child.text:
                    if not re.match(expected_format, child.text):
                        logger.warning(
                            f"Formato de fecha inválido en {child.tag}: {child.text}")

    def _validate_numeric_formats(self, element: Element):
        """Valida formatos numéricos"""
        numeric_tags = ['dRucEm', 'dVerEmi', 'dTotOpe', 'dCantProSer']

        for child in element:
            if child.tag in numeric_tags and child.text:
                try:
                    # Intentar convertir a número
                    if '.' in child.text:
                        float(child.text)
                    else:
                        int(child.text)
                except ValueError:
                    logger.warning(
                        f"Formato numérico inválido en {child.tag}: {child.text}")

    def _validate_sifen_codes(self, element: Element):
        """Valida códigos específicos SIFEN"""
        # Códigos de tipo de documento
        tipo_documento_validos = ['1', '4', '5', '6', '7']

        for child in element:
            if child.tag in ['iTipoDE', 'iTipDocAso'] and child.text:
                if child.text not in tipo_documento_validos:
                    logger.warning(
                        f"Código de tipo documento inválido: {child.text}")


# =====================================
# ESTRATEGIAS DE TRANSFORMACIÓN
# =====================================

class DirectMappingStrategy(XMLTransformationStrategy):
    """
    Estrategia de transformación basada en mapeo directo

    Utiliza el SchemaMapper para transformar elementos
    de forma directa y eficiente.
    """

    def __init__(self, schema_mapper: SchemaMapper):
        self.schema_mapper = schema_mapper

    def transform(
        self,
        xml_content: str,
        context: TransformationContext,
        config: TransformationConfig
    ) -> TransformationResult:
        """Transforma XML usando mapeo directo"""
        start_time = time.time()
        result = TransformationResult(success=False, original_xml=xml_content)

        try:
            logger.debug(
                f"Iniciando transformación directa {context.direction.value}")

            # Parsear XML de entrada
            root_element = fromstring(xml_content)
            result.transformation_log.append(
                f"XML parseado. Elemento raíz: {root_element.tag}")

            # Cargar configuración del mapper
            if not self.schema_mapper.load_configuration(context.document_type):
                result.errors.append(
                    "Error cargando configuración del schema mapper")
                return result

            # Crear contexto de mapeo
            mapping_direction = (
                MappingDirection.MODULAR_TO_OFFICIAL
                if context.direction == TransformationDirection.MODULAR_TO_OFFICIAL
                else MappingDirection.OFFICIAL_TO_MODULAR
            )

            mapping_context = create_mapping_context(
                document_type=context.document_type,
                direction=mapping_direction
            )

            # Ejecutar transformación
            if mapping_direction == MappingDirection.MODULAR_TO_OFFICIAL:
                mapping_result = self.schema_mapper.map_to_official(
                    root_element, mapping_context)
            else:
                mapping_result = self.schema_mapper.map_to_modular(
                    root_element, mapping_context)

            if mapping_result.success and mapping_result.mapped_element is not None:
                # Aplicar procesadores adicionales
                processed_element = self._apply_processors(
                    mapping_result.mapped_element, context, config
                )

                # Generar XML final
                result.transformed_xml = tostring(
                    processed_element, encoding='unicode')
                result.success = True
                result.transformation_log.append(
                    "Transformación directa completada exitosamente")

            else:
                result.errors.extend(
                    [f"Error en mapeo: {error}" for error in mapping_result.errors])
                result.warnings.extend(mapping_result.warnings)

        except Exception as e:
            logger.error(f"Error en transformación directa: {str(e)}")
            result.errors.append(f"Error durante transformación: {str(e)}")

        finally:
            execution_time = (time.time() - start_time) * 1000
            result.performance_metrics["total_time"] = execution_time
            result.metadata["strategy"] = "direct_mapping"

        return result

    def validate_compatibility(
        self,
        context: TransformationContext
    ) -> Tuple[bool, List[str]]:
        """Valida compatibilidad con transformación directa"""
        errors = []

        # Verificar que el tipo de documento sea soportado
        supported_types = [DocumentType.FACTURA_ELECTRONICA,
                           DocumentType.NOTA_CREDITO_ELECTRONICA]
        if context.document_type not in supported_types:
            errors.append(
                f"Tipo de documento no soportado: {context.document_type}")

        # Verificar dirección de transformación
        if context.direction not in [TransformationDirection.MODULAR_TO_OFFICIAL, TransformationDirection.OFFICIAL_TO_MODULAR]:
            errors.append(f"Dirección no soportada: {context.direction}")

        return len(errors) == 0, errors

    def _apply_processors(
        self,
        element: Element,
        context: TransformationContext,
        config: TransformationConfig
    ) -> Element:
        """Aplica procesadores adicionales al elemento transformado"""

        # Aplicar procesador de namespaces
        if config.namespace_mode != NamespaceMode.PRESERVE:
            namespace_processor = NamespaceProcessor()
            element = namespace_processor.process(element, context)

        # Aplicar procesador de integridad de datos
        integrity_processor = DataIntegrityProcessor()
        element = integrity_processor.process(element, context)

        return element


class HybridTransformationStrategy(XMLTransformationStrategy):
    """
    Estrategia híbrida que combina múltiples enfoques

    Utiliza mapeo directo cuando es posible y fallback
    a otros métodos para casos complejos.
    """

    def __init__(self, schema_mapper: SchemaMapper):
        self.direct_strategy = DirectMappingStrategy(schema_mapper)
        self.schema_mapper = schema_mapper

    def transform(
        self,
        xml_content: str,
        context: TransformationContext,
        config: TransformationConfig
    ) -> TransformationResult:
        """Transforma XML usando estrategia híbrida"""
        start_time = time.time()
        result = TransformationResult(success=False, original_xml=xml_content)

        try:
            logger.debug(
                f"Iniciando transformación híbrida {context.direction.value}")

            # Intentar transformación directa primero
            direct_result = self.direct_strategy.transform(
                xml_content, context, config)

            if direct_result.success:
                # Transformación directa exitosa
                result = direct_result
                result.transformation_log.append(
                    "Estrategia directa utilizada exitosamente")

            else:
                # Fallback a transformación manual/template
                result = self._manual_transformation(
                    xml_content, context, config)
                result.transformation_log.append(
                    "Fallback a transformación manual")
                # Agregar errores como warnings
                result.warnings.extend(direct_result.errors)

        except Exception as e:
            logger.error(f"Error en transformación híbrida: {str(e)}")
            result.errors.append(
                f"Error durante transformación híbrida: {str(e)}")

        finally:
            execution_time = (time.time() - start_time) * 1000
            result.performance_metrics["total_time"] = execution_time
            result.metadata["strategy"] = "hybrid"

        return result

    def validate_compatibility(
        self,
        context: TransformationContext
    ) -> Tuple[bool, List[str]]:
        """Estrategia híbrida es compatible con todos los contextos"""
        return True, []

    def _manual_transformation(
        self,
        xml_content: str,
        context: TransformationContext,
        config: TransformationConfig
    ) -> TransformationResult:
        """Transformación manual para casos donde el mapeo directo falla"""
        result = TransformationResult(success=False, original_xml=xml_content)

        try:
            # Parsear XML
            root_element = fromstring(xml_content)

            # Crear elemento raíz del destino
            if context.direction == TransformationDirection.MODULAR_TO_OFFICIAL:
                new_root = Element("rDE")
                # Agregar namespaces oficiales
                new_root.set("xmlns", "http://ekuatia.set.gov.py/sifen/xsd")
                new_root.set("{http://www.w3.org/2000/xmlns/}xsi",
                             "http://www.w3.org/2001/XMLSchema-instance")
            else:
                new_root = Element("gDocModular")

            # Copiar elementos esenciales
            self._copy_essential_elements(root_element, new_root, context)

            # Generar XML final
            result.transformed_xml = tostring(new_root, encoding='unicode')
            result.success = True
            result.transformation_log.append(
                "Transformación manual completada")

        except Exception as e:
            result.errors.append(f"Error en transformación manual: {str(e)}")

        return result

    def _copy_essential_elements(
        self,
        source: Element,
        target: Element,
        context: TransformationContext
    ):
        """Copia elementos esenciales entre documentos"""

        # Mapeo básico de elementos esenciales
        essential_mappings = {
            TransformationDirection.MODULAR_TO_OFFICIAL: {
                "gDatGral": "gTimb",
                "gDatEmi": "gOpeOpe",
                "gDatRec": "gOpeDe"
            },
            TransformationDirection.OFFICIAL_TO_MODULAR: {
                "gTimb": "gDatGral",
                "gOpeOpe": "gDatEmi",
                "gOpeDe": "gDatRec"
            }
        }

        mappings = essential_mappings.get(context.direction, {})

        for child in source:
            local_tag = child.tag.split(
                "}")[-1] if "}" in child.tag else child.tag

            if local_tag in mappings:
                # Crear elemento mapeado
                new_child = SubElement(target, mappings[local_tag])
                if child.text:
                    new_child.text = child.text

                # Copiar atributos
                for attr, value in child.attrib.items():
                    new_child.set(attr, value)

                # Recursivamente copiar hijos
                self._copy_essential_elements(child, new_child, context)
            else:
                # Copiar elemento tal como está
                new_child = SubElement(target, local_tag)
                if child.text:
                    new_child.text = child.text

                for attr, value in child.attrib.items():
                    new_child.set(attr, value)


# =====================================
# CLASE PRINCIPAL: XML TRANSFORMER
# =====================================

class XMLTransformer:
    """
    Transformador principal para conversión XML bidireccional

    Esta clase coordina todas las transformaciones entre formatos modular
    y oficial, utilizando estrategias configurables y validación integrada.

    Características:
    - Transformación bidireccional modular ↔ oficial
    - Múltiples estrategias de transformación
    - Validación integrada pre y post transformación
    - Cache inteligente para performance
    - Manejo robusto de errores
    - Métricas de performance detalladas

    Example:
        >>> transformer = XMLTransformer()
        >>> result = transformer.transform_to_official(modular_xml, DocumentType.FACTURA_ELECTRONICA)
        >>> 
        >>> if result.success:
        >>>     official_xml = result.transformed_xml
        >>>     print("✅ Transformación exitosa")
    """

    def __init__(
        self,
        config: Optional[TransformationConfig] = None,
        schema_mapper: Optional[SchemaMapper] = None,
        validation_bridge: Optional[ValidationBridge] = None
    ):
        """
        Inicializa el XMLTransformer

        Args:
            config: Configuración de transformación
            schema_mapper: Instancia del schema mapper
            validation_bridge: Instancia del validation bridge
        """
        self.config = config or TransformationConfig()
        self.schema_mapper = schema_mapper or SchemaMapper()
        self.validation_bridge = validation_bridge or ValidationBridge()

        # Inicializar estrategias
        self.strategies = self._initialize_strategies()

        # Cache para transformaciones
        self._transformation_cache = {} if self.config.enable_caching else None

        # Estadísticas
        self._stats = defaultdict(int)

        logger.info("XMLTransformer inicializado")

    def _initialize_strategies(self) -> Dict[TransformationStrategy, XMLTransformationStrategy]:
        """Inicializa las estrategias de transformación disponibles"""
        return {
            TransformationStrategy.DIRECT_MAPPING: DirectMappingStrategy(self.schema_mapper),
            TransformationStrategy.HYBRID: HybridTransformationStrategy(
                self.schema_mapper)
        }

    def transform_to_official(
        self,
        modular_xml: str,
        document_type: DocumentType,
        config: Optional[TransformationConfig] = None
    ) -> TransformationResult:
        """
        Transforma XML modular a formato oficial SET

        Args:
            modular_xml: XML en formato modular
            document_type: Tipo de documento
            config: Configuración específica (override)

        Returns:
            TransformationResult: Resultado de la transformación
        """
        context = TransformationContext(
            document_type=document_type,
            direction=TransformationDirection.MODULAR_TO_OFFICIAL
        )

        return self._execute_transformation(modular_xml, context, config)

    def transform_to_modular(
        self,
        official_xml: str,
        document_type: DocumentType,
        config: Optional[TransformationConfig] = None
    ) -> TransformationResult:
        """
        Transforma XML oficial SET a formato modular

        Args:
            official_xml: XML en formato oficial SET
            document_type: Tipo de documento
            config: Configuración específica (override)

        Returns:
            TransformationResult: Resultado de la transformación
        """
        context = TransformationContext(
            document_type=document_type,
            direction=TransformationDirection.OFFICIAL_TO_MODULAR
        )

        return self._execute_transformation(official_xml, context, config)

    def transform_bidirectional(
        self,
        xml_content: str,
        document_type: DocumentType,
        source_format: str = "modular"
    ) -> Tuple[TransformationResult, TransformationResult]:
        """
        Realiza transformación bidireccional para verificar consistencia

        Args:
            xml_content: XML a transformar
            document_type: Tipo de documento
            source_format: Formato de origen ("modular" o "official")

        Returns:
            Tuple[TransformationResult, TransformationResult]: (ida, vuelta)
        """
        if source_format == "modular":
            # Modular → Oficial → Modular
            to_official = self.transform_to_official(
                xml_content, document_type)

            if to_official.success:
                to_modular = self.transform_to_modular(
                    to_official.transformed_xml, document_type)
                return to_official, to_modular
            else:
                return to_official, TransformationResult(success=False, errors=["Primera transformación falló"])

        else:
            # Oficial → Modular → Oficial
            to_modular = self.transform_to_modular(xml_content, document_type)

            if to_modular.success:
                to_official = self.transform_to_official(
                    to_modular.transformed_xml, document_type)
                return to_modular, to_official
            else:
                return to_modular, TransformationResult(success=False, errors=["Primera transformación falló"])

    def _execute_transformation(
        self,
        xml_content: str,
        context: TransformationContext,
        config: Optional[TransformationConfig] = None
    ) -> TransformationResult:
        """
        Ejecuta la transformación usando la estrategia configurada

        Args:
            xml_content: XML a transformar
            context: Contexto de transformación
            config: Configuración específica

        Returns:
            TransformationResult: Resultado de la transformación
        """
        transformation_config = config or self.config
        start_time = time.time()

        try:
            logger.info(
                f"Ejecutando transformación {context.direction.value} para {context.document_type}")

            # Verificar cache si está habilitado
            cache_key = self._generate_cache_key(
                xml_content, context, transformation_config)
            if self._transformation_cache and cache_key in self._transformation_cache:
                logger.debug("Resultado obtenido desde cache")
                self._stats['cache_hits'] += 1
                return self._transformation_cache[cache_key]

            self._stats['cache_misses'] += 1

            # Validación de entrada si está habilitada
            if transformation_config.validate_input:
                input_validation = self._validate_input(xml_content, context)
                if not input_validation.success:
                    return input_validation

            # Seleccionar y ejecutar estrategia
            strategy = self.strategies.get(transformation_config.strategy)
            if not strategy:
                return TransformationResult(
                    success=False,
                    errors=[
                        f"Estrategia no disponible: {transformation_config.strategy}"]
                )

            # Validar compatibilidad de estrategia
            is_compatible, compatibility_errors = strategy.validate_compatibility(
                context)
            if not is_compatible:
                return TransformationResult(
                    success=False,
                    errors=[
                        f"Estrategia incompatible: {', '.join(compatibility_errors)}"]
                )

            # Ejecutar transformación
            result = strategy.transform(
                xml_content, context, transformation_config)

            # Validación de salida si está habilitada
            if result.success and transformation_config.validate_output:
                output_validation = self._validate_output(result, context)
                if output_validation:
                    result.validation_result = output_validation

            # Guardar en cache si está habilitado
            if self._transformation_cache and result.success:
                self._transformation_cache[cache_key] = result

            # Actualizar estadísticas
            self._stats['total_transformations'] += 1
            self._stats[f'transformations_{context.direction.value}'] += 1
            self._stats[f'strategy_{transformation_config.strategy.value}'] += 1

            total_time = (time.time() - start_time) * 1000
            result.performance_metrics["total_execution_time"] = total_time

            logger.info(f"Transformación completada en {total_time:.2f}ms")
            return result

        except Exception as e:
            logger.error(
                f"Error durante ejecución de transformación: {str(e)}")
            return TransformationResult(
                success=False,
                errors=[f"Error durante ejecución: {str(e)}"],
                performance_metrics={"total_execution_time": (
                    time.time() - start_time) * 1000}
            )

    def _validate_input(
        self,
        xml_content: str,
        context: TransformationContext
    ) -> TransformationResult:
        """
        Valida XML de entrada antes de transformación

        Args:
            xml_content: XML a validar
            context: Contexto de transformación

        Returns:
            TransformationResult: Resultado con validación o error
        """
        try:
            # Validación básica XML
            fromstring(xml_content)

            # Validación específica según origen
            if context.direction == TransformationDirection.MODULAR_TO_OFFICIAL:
                # Validar formato modular
                validation_result = self.validation_bridge.validate_hybrid(
                    xml_content, context.document_type, ValidationMode.MODULAR_ONLY
                )
            else:
                # Validar formato oficial
                validation_result = self.validation_bridge.validate_hybrid(
                    xml_content, context.document_type, ValidationMode.OFFICIAL_ONLY
                )

            if not validation_result.overall_valid:
                return TransformationResult(
                    success=False,
                    errors=["XML de entrada no válido"],
                    validation_result=validation_result
                )

            return TransformationResult(success=True)

        except Exception as e:
            return TransformationResult(
                success=False,
                errors=[f"Error validando entrada: {str(e)}"]
            )

    def _validate_output(
        self,
        result: TransformationResult,
        context: TransformationContext
    ) -> Optional[HybridValidationResult]:
        """
        Valida XML de salida después de transformación

        Args:
            result: Resultado de transformación
            context: Contexto de transformación

        Returns:
            HybridValidationResult: Resultado de validación o None
        """
        try:
            if not result.transformed_xml:
                return None

            # Validación según destino
            if context.direction == TransformationDirection.MODULAR_TO_OFFICIAL:
                # Validar formato oficial generado
                validation_mode = ValidationMode.OFFICIAL_ONLY
            else:
                # Validar formato modular generado
                validation_mode = ValidationMode.MODULAR_ONLY

            validation_result = self.validation_bridge.validate_hybrid(
                result.transformed_xml, context.document_type, validation_mode
            )

            if not validation_result.overall_valid:
                result.warnings.append(
                    "XML transformado tiene problemas de validación")
                result.warnings.extend([
                    issue.message for issue in validation_result.get_total_issues()[:3]
                ])

            return validation_result

        except Exception as e:
            logger.warning(f"Error validando salida: {str(e)}")
            return None

    def _generate_cache_key(
        self,
        xml_content: str,
        context: TransformationContext,
        config: TransformationConfig
    ) -> str:
        """Genera clave de cache para transformación"""
        content_hash = hashlib.md5(xml_content.encode('utf-8')).hexdigest()[:8]
        context_hash = hashlib.md5(
            f"{context.document_type.value}_{context.direction.value}".encode(
                'utf-8')
        ).hexdigest()[:8]
        config_hash = hashlib.md5(
            f"{config.strategy.value}_{config.mode.value}".encode('utf-8')
        ).hexdigest()[:8]

        return f"{content_hash}_{context_hash}_{config_hash}"

    def validate_transformation_consistency(
        self,
        xml_content: str,
        document_type: DocumentType,
        source_format: str = "modular"
    ) -> Dict[str, Any]:
        """
        Valida la consistencia de transformación bidireccional

        Args:
            xml_content: XML original
            document_type: Tipo de documento
            source_format: Formato de origen

        Returns:
            Dict[str, Any]: Reporte de consistencia
        """
        try:
            # Ejecutar transformación bidireccional
            first_result, second_result = self.transform_bidirectional(
                xml_content, document_type, source_format
            )

            # Analizar consistencia
            consistency_report = {
                "original_xml": xml_content,
                "first_transformation": {
                    "success": first_result.success,
                    "direction": "to_official" if source_format == "modular" else "to_modular",
                    "errors": first_result.errors,
                    "warnings": first_result.warnings
                },
                "second_transformation": {
                    "success": second_result.success,
                    "direction": "to_modular" if source_format == "modular" else "to_official",
                    "errors": second_result.errors,
                    "warnings": second_result.warnings
                },
                "consistency_score": 0.0,
                "issues": [],
                "recommendations": []
            }

            # Calcular score de consistencia
            if first_result.success and second_result.success:
                similarity_score = self._calculate_xml_similarity(
                    xml_content, second_result.transformed_xml
                )
                consistency_report["consistency_score"] = similarity_score

                if similarity_score < 0.8:
                    consistency_report["issues"].append(
                        f"Baja similitud en transformación bidireccional: {similarity_score:.2f}"
                    )
                    consistency_report["recommendations"].append(
                        "Revisar reglas de mapeo para mejorar consistencia"
                    )
                else:
                    consistency_report["recommendations"].append(
                        "Transformación bidireccional es consistente"
                    )
            else:
                consistency_report["issues"].append(
                    "Una o ambas transformaciones fallaron")
                consistency_report["recommendations"].append(
                    "Resolver errores de transformación antes de evaluar consistencia"
                )

            return consistency_report

        except Exception as e:
            return {
                "error": f"Error validando consistencia: {str(e)}",
                "consistency_score": 0.0,
                "issues": [str(e)]
            }

    def _calculate_xml_similarity(self, xml1: str, xml2: str) -> float:
        """Calcula similitud entre dos XMLs"""
        try:
            # Normalizar XMLs
            normalized1 = re.sub(r'\s+', ' ', xml1.strip())
            normalized2 = re.sub(r'\s+', ' ', xml2.strip())

            # Similitud básica
            if len(normalized1) == 0 or len(normalized2) == 0:
                return 0.0

            # Comparar elementos y estructura
            try:
                elem1 = fromstring(normalized1)
                elem2 = fromstring(normalized2)

                # Comparar número de elementos
                count1 = len(list(elem1.iter()))
                count2 = len(list(elem2.iter()))

                if count1 == 0 and count2 == 0:
                    return 1.0

                count_similarity = 1.0 - \
                    abs(count1 - count2) / max(count1, count2)

                # Comparar contenido textual
                text1 = ''.join(elem.text or '' for elem in elem1.iter())
                text2 = ''.join(elem.text or '' for elem in elem2.iter())

                if len(text1) == 0 and len(text2) == 0:
                    text_similarity = 1.0
                elif len(text1) == 0 or len(text2) == 0:
                    text_similarity = 0.0
                else:
                    common_chars = sum(
                        1 for a, b in zip(text1, text2) if a == b)
                    text_similarity = common_chars / \
                        max(len(text1), len(text2))

                # Promedio ponderado
                return (count_similarity * 0.3 + text_similarity * 0.7)

            except:
                # Fallback a comparación de strings
                common_chars = sum(1 for a, b in zip(
                    normalized1, normalized2) if a == b)
                return common_chars / max(len(normalized1), len(normalized2))

        except:
            return 0.0

    def get_transformation_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de transformación

        Returns:
            Dict[str, Any]: Estadísticas detalladas
        """
        stats: Dict[str, Any] = dict(self._stats)

        # Calcular métricas derivadas
        total_transformations = stats.get('total_transformations', 0)
        cache_hits = stats.get('cache_hits', 0)
        cache_misses = stats.get('cache_misses', 0)

        if total_transformations > 0:
            stats['cache_hit_rate'] = cache_hits / \
                (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0.0

            # Distribución por dirección
            to_official = stats.get('transformations_modular_to_official', 0)
            to_modular = stats.get('transformations_official_to_modular', 0)

            stats['direction_distribution'] = {
                'to_official_percentage': (to_official / total_transformations) * 100,
                'to_modular_percentage': (to_modular / total_transformations) * 100
            }

        stats['cache_enabled'] = self.config.enable_caching
        stats['current_strategy'] = self.config.strategy.value

        return stats

    def clear_cache(self):
        """Limpia el cache de transformaciones"""
        if self._transformation_cache:
            self._transformation_cache.clear()
            logger.debug("Cache de transformaciones limpiado")

    def update_config(self, new_config: TransformationConfig):
        """
        Actualiza la configuración del transformer

        Args:
            new_config: Nueva configuración
        """
        self.config = new_config

        # Reconfigurar cache
        if not new_config.enable_caching and self._transformation_cache:
            self._transformation_cache.clear()
            self._transformation_cache = None
        elif new_config.enable_caching and not self._transformation_cache:
            self._transformation_cache = {}

        logger.info("Configuración de XMLTransformer actualizada")


# =====================================
# FUNCIONES DE UTILIDAD PÚBLICAS
# =====================================

def transform_modular_to_official(
    modular_xml: str,
    document_type: DocumentType,
    strategy: TransformationStrategy = TransformationStrategy.HYBRID
) -> TransformationResult:
    """
    Función helper para transformación rápida modular → oficial

    Args:
        modular_xml: XML en formato modular
        document_type: Tipo de documento
        strategy: Estrategia de transformación

    Returns:
        TransformationResult: Resultado de la transformación
    """
    config = TransformationConfig(strategy=strategy)
    transformer = XMLTransformer(config)
    return transformer.transform_to_official(modular_xml, document_type)


def transform_official_to_modular(
    official_xml: str,
    document_type: DocumentType,
    strategy: TransformationStrategy = TransformationStrategy.HYBRID
) -> TransformationResult:
    """
    Función helper para transformación rápida oficial → modular

    Args:
        official_xml: XML en formato oficial SET
        document_type: Tipo de documento
        strategy: Estrategia de transformación

    Returns:
        TransformationResult: Resultado de la transformación
    """
    config = TransformationConfig(strategy=strategy)
    transformer = XMLTransformer(config)
    return transformer.transform_to_modular(official_xml, document_type)


def validate_transformation_pipeline(
    xml_content: str,
    document_type: DocumentType,
    source_format: str = "modular"
) -> Dict[str, Any]:
    """
    Valida pipeline completo de transformación

    Args:
        xml_content: XML a validar
        document_type: Tipo de documento
        source_format: Formato de origen

    Returns:
        Dict[str, Any]: Reporte de validación del pipeline
    """
    transformer = XMLTransformer()
    return transformer.validate_transformation_consistency(
        xml_content, document_type, source_format
    )


def create_transformation_config(
    strategy: TransformationStrategy = TransformationStrategy.HYBRID,
    mode: TransformationMode = TransformationMode.STRICT,
    validate_input: bool = True,
    validate_output: bool = True,
    enable_caching: bool = True
) -> TransformationConfig:
    """
    Crea configuración de transformación con parámetros personalizados

    Args:
        strategy: Estrategia de transformación
        mode: Modo de transformación
        validate_input: Validar entrada
        validate_output: Validar salida
        enable_caching: Habilitar cache

    Returns:
        TransformationConfig: Configuración creada
    """
    return TransformationConfig(
        strategy=strategy,
        mode=mode,
        validate_input=validate_input,
        validate_output=validate_output,
        enable_caching=enable_caching
    )


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    # Clase principal
    'XMLTransformer',

    # Enums
    'TransformationDirection',
    'TransformationMode',
    'TransformationStrategy',
    'NamespaceMode',

    # Dataclasses
    'TransformationConfig',
    'TransformationContext',
    'TransformationResult',

    # Interfaces
    'XMLTransformationStrategy',
    'XMLProcessor',

    # Estrategias
    'DirectMappingStrategy',
    'HybridTransformationStrategy',

    # Procesadores
    'NamespaceProcessor',
    'ElementStructureProcessor',
    'DataIntegrityProcessor',

    # Funciones de utilidad
    'transform_modular_to_official',
    'transform_official_to_modular',
    'validate_transformation_pipeline',
    'create_transformation_config'
]


# =====================================
# EJEMPLO DE USO
# =====================================

if __name__ == "__main__":
    # Ejemplo de uso del XMLTransformer

    # 1. Crear configuración
    config = create_transformation_config(
        strategy=TransformationStrategy.HYBRID,
        mode=TransformationMode.STRICT,
        validate_input=True,
        validate_output=True
    )

    # 2. Inicializar transformer
    transformer = XMLTransformer(config)

    # 3. XML modular de ejemplo
    modular_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <gDatGral>
        <dFeEmiDE>2024-12-15</dFeEmiDE>
        <dHorEmi>14:30:00</dHorEmi>
        <iTipoDE>1</iTipoDE>
    </gDatGral>"""

    # 4. Transformar a formato oficial
    result = transformer.transform_to_official(
        modular_xml, DocumentType.FACTURA_ELECTRONICA
    )

    # 5. Verificar resultado
    if result.success:
        print("✅ Transformación exitosa")
        print(
            f"XML oficial generado: {len(result.transformed_xml)} caracteres")
        print(
            f"Tiempo de ejecución: {result.performance_metrics.get('total_time', 0):.2f}ms")

        # Mostrar fragmento del XML transformado
        if result.transformed_xml:
            preview = result.transformed_xml[:200] + "..." if len(
                result.transformed_xml) > 200 else result.transformed_xml
            print(f"Preview: {preview}")
    else:
        print("❌ Error en transformación")
        for error in result.errors:
            print(f"Error: {error}")
        for warning in result.warnings:
            print(f"Advertencia: {warning}")

    # 6. Validar consistencia bidireccional
    consistency_report = transformer.validate_transformation_consistency(
        modular_xml, DocumentType.FACTURA_ELECTRONICA, "modular"
    )

    print(
        f"\n🔄 Consistencia bidireccional: {consistency_report.get('consistency_score', 0):.2f}")

    # 7. Mostrar estadísticas
    stats = transformer.get_transformation_statistics()
    print(f"\n📊 Estadísticas: {stats}")

    # 8. Ejemplo de función helper
    quick_result = transform_modular_to_official(
        modular_xml, DocumentType.FACTURA_ELECTRONICA
    )
    print(f"\n⚡ Transformación rápida: {'✅' if quick_result.success else '❌'}")
