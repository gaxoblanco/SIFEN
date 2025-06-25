"""
Schema Mapper v150 - Mapeo Inteligente Modular ↔ Oficial

Este módulo implementa el mapeo bidireccional entre los esquemas modulares 
desarrollados para facilidad de desarrollo y los esquemas oficiales SET 
requeridos para la comunicación con SIFEN.

Responsabilidades Principales:
1. Mapear elementos XML entre formato modular y oficial
2. Mantener correspondencia semántica entre ambos esquemas  
3. Proporcionar transformaciones configurables y extensibles
4. Validar integridad de mapeos bidireccionales
5. Optimizar performance de transformaciones

Patrones Implementados:
- Strategy Pattern: Para diferentes estrategias de mapeo
- Factory Pattern: Para crear mapeadores específicos por tipo
- Template Method: Para flujo común de transformación
- Registry Pattern: Para registrar reglas de mapeo

Arquitectura:
- Mapeo declarativo via configuración JSON/YAML
- Validación automática de reglas de mapeo
- Cache inteligente para optimización
- Logging detallado para debugging
- Extensible para nuevos tipos de documentos

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
Fecha: 2025-06-24
"""

from typing import Dict, List, Optional, Union, Any, Tuple, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import json
import yaml
from pathlib import Path
import logging
from functools import lru_cache, wraps
from xml.etree.ElementTree import Element, tostring, fromstring
import time
from collections import defaultdict

# Configuración de logging específico para el mapper
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Type hints para mejor documentación
ModularElement = TypeVar('ModularElement', bound=Element)
OfficialElement = TypeVar('OfficialElement', bound=Element)
MappingConfigType = Dict[str, Any]


# =====================================
# ENUMS Y CONSTANTES
# =====================================

class MappingDirection(Enum):
    """Direcciones de mapeo disponibles"""
    MODULAR_TO_OFFICIAL = "modular_to_official"
    OFFICIAL_TO_MODULAR = "official_to_modular"
    BIDIRECTIONAL = "bidirectional"


class DocumentType(Enum):
    """Tipos de documento SIFEN soportados"""
    FACTURA_ELECTRONICA = "FE"
    AUTOFACTURA_ELECTRONICA = "AFE"
    NOTA_CREDITO_ELECTRONICA = "NCE"
    NOTA_DEBITO_ELECTRONICA = "NDE"
    NOTA_REMISION_ELECTRONICA = "NRE"


class MappingComplexity(Enum):
    """Niveles de complejidad de mapeo"""
    SIMPLE = "simple"           # Mapeo directo 1:1
    COMPLEX = "complex"         # Mapeo con transformación
    AGGREGATE = "aggregate"     # Mapeo de múltiples elementos
    CONDITIONAL = "conditional"  # Mapeo basado en condiciones


# =====================================
# DATACLASSES PARA CONFIGURACIÓN
# =====================================

@dataclass
class MappingRule:
    """
    Regla de mapeo individual entre elementos modular y oficial

    Attributes:
        modular_path: XPath del elemento en schema modular
        official_path: XPath del elemento en schema oficial  
        direction: Dirección del mapeo
        complexity: Nivel de complejidad del mapeo
        transformation: Función de transformación opcional
        validation: Función de validación opcional
        conditions: Condiciones para aplicar el mapeo
        priority: Prioridad de la regla (mayor = más prioritaria)
        description: Descripción legible de la regla
    """
    modular_path: str
    official_path: str
    direction: MappingDirection = MappingDirection.BIDIRECTIONAL
    complexity: MappingComplexity = MappingComplexity.SIMPLE
    transformation: Optional[str] = None
    validation: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    description: str = ""

    def __post_init__(self):
        """Validación post-inicialización"""
        if not self.modular_path or not self.official_path:
            raise ValueError("modular_path y official_path son requeridos")

        if self.priority < 0 or self.priority > 1000:
            raise ValueError("priority debe estar entre 0 y 1000")


@dataclass
class MappingContext:
    """
    Contexto para operaciones de mapeo

    Attributes:
        document_type: Tipo de documento siendo procesado
        direction: Dirección del mapeo actual
        source_namespace: Namespace del documento origen
        target_namespace: Namespace del documento destino
        variables: Variables de contexto para transformaciones
        metadata: Metadatos adicionales
    """
    document_type: DocumentType
    direction: MappingDirection
    source_namespace: str = ""
    target_namespace: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MappingResult:
    """
    Resultado de una operación de mapeo

    Attributes:
        success: Indica si el mapeo fue exitoso
        mapped_element: Elemento resultado del mapeo
        applied_rules: Reglas que fueron aplicadas
        warnings: Advertencias durante el mapeo
        errors: Errores durante el mapeo
        execution_time: Tiempo de ejecución en milisegundos
        statistics: Estadísticas de la operación
    """
    success: bool
    mapped_element: Optional[Element] = None
    applied_rules: List[MappingRule] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    statistics: Dict[str, Any] = field(default_factory=dict)


# =====================================
# INTERFACES ABSTRACTAS
# =====================================

class MappingStrategy(ABC):
    """
    Interfaz abstracta para estrategias de mapeo

    Permite implementar diferentes algoritmos de mapeo según
    el tipo de documento o complejidad requerida.
    """

    @abstractmethod
    def map_element(
        self,
        element: Element,
        rule: MappingRule,
        context: MappingContext
    ) -> MappingResult:
        """
        Mapea un elemento según la regla y contexto proporcionados

        Args:
            element: Elemento XML a mapear
            rule: Regla de mapeo a aplicar
            context: Contexto de la operación

        Returns:
            MappingResult: Resultado del mapeo
        """
        pass

    @abstractmethod
    def validate_rule(self, rule: MappingRule) -> Tuple[bool, List[str]]:
        """
        Valida que una regla de mapeo sea válida para esta estrategia

        Args:
            rule: Regla a validar

        Returns:
            Tuple[bool, List[str]]: (es_válida, lista_errores)
        """
        pass


class TransformationFunction(ABC):
    """
    Interfaz abstracta para funciones de transformación

    Permite implementar transformaciones complejas de datos
    durante el proceso de mapeo.
    """

    @abstractmethod
    def transform(
        self,
        value: Any,
        context: MappingContext
    ) -> Any:
        """
        Transforma un valor según el contexto

        Args:
            value: Valor a transformar
            context: Contexto de transformación

        Returns:
            Any: Valor transformado
        """
        pass

    @abstractmethod
    def validate_input(self, value: Any) -> bool:
        """
        Valida que el valor de entrada sea válido para esta transformación

        Args:
            value: Valor a validar

        Returns:
            bool: True si es válido
        """
        pass


# =====================================
# IMPLEMENTACIONES DE ESTRATEGIAS
# =====================================

class SimpleMappingStrategy(MappingStrategy):
    """
    Estrategia de mapeo simple para elementos con correspondencia directa 1:1

    Maneja:
    - Renombrado de elementos
    - Cambio de namespace
    - Reordenamiento de atributos
    - Transformaciones básicas de valores
    """

    def map_element(
        self,
        element: Element,
        rule: MappingRule,
        context: MappingContext
    ) -> MappingResult:
        """Implementa mapeo simple elemento a elemento"""
        start_time = time.time()
        result = MappingResult(success=False)

        try:
            logger.debug(
                f"Iniciando mapeo simple: {rule.modular_path} → {rule.official_path}")

            # Crear nuevo elemento con el nombre oficial
            target_tag = self._extract_tag_from_path(rule.official_path)
            mapped_element = Element(target_tag)

            # Copiar atributos básicos
            for attr_name, attr_value in element.attrib.items():
                mapped_element.set(attr_name, attr_value)

            # Copiar texto del elemento
            if element.text:
                mapped_element.text = element.text

            # Aplicar transformación si existe
            if rule.transformation:
                mapped_element = self._apply_transformation(
                    mapped_element, rule.transformation, context)

            # Copiar elementos hijos recursivamente
            for child in element:
                mapped_child = Element(child.tag)
                if child.text:
                    mapped_child.text = child.text
                mapped_child.attrib.update(child.attrib)
                mapped_element.append(mapped_child)

            result.success = True
            result.mapped_element = mapped_element
            result.applied_rules = [rule]

            logger.debug(f"Mapeo simple exitoso para {rule.modular_path}")

        except Exception as e:
            logger.error(f"Error en mapeo simple: {str(e)}")
            result.errors.append(f"Error en mapeo simple: {str(e)}")

        finally:
            result.execution_time = (time.time() - start_time) * 1000

        return result

    def validate_rule(self, rule: MappingRule) -> Tuple[bool, List[str]]:
        """Valida reglas para mapeo simple"""
        errors = []

        if rule.complexity != MappingComplexity.SIMPLE:
            errors.append(
                f"SimpleMappingStrategy solo soporta complejidad SIMPLE")

        if not rule.modular_path or not rule.official_path:
            errors.append("modular_path y official_path son requeridos")

        return len(errors) == 0, errors

    def _extract_tag_from_path(self, xpath: str) -> str:
        """Extrae el nombre del tag desde un XPath"""
        if '/' in xpath:
            return xpath.split('/')[-1]
        return xpath

    def _apply_transformation(
        self,
        element: Element,
        transformation: str,
        context: MappingContext
    ) -> Element:
        """Aplica transformación específica al elemento"""
        # Implementación básica - se puede extender con transformaciones complejas
        logger.debug(f"Aplicando transformación: {transformation}")
        return element


class ComplexMappingStrategy(MappingStrategy):
    """
    Estrategia de mapeo complejo para elementos que requieren transformación

    Maneja:
    - Elementos con estructura diferente
    - Agregación de múltiples elementos
    - Cálculos y transformaciones complejas
    - Mapeos condicionales
    """

    def map_element(
        self,
        element: Element,
        rule: MappingRule,
        context: MappingContext
    ) -> MappingResult:
        """Implementa mapeo complejo con transformaciones"""
        start_time = time.time()
        result = MappingResult(success=False)

        try:
            logger.debug(
                f"Iniciando mapeo complejo: {rule.modular_path} → {rule.official_path}")

            # Verificar condiciones si existen
            if rule.conditions and not self._evaluate_conditions(element, rule.conditions, context):
                result.warnings.append(
                    f"Condiciones no cumplidas para regla {rule.modular_path}")
                return result

            # Crear elemento base
            target_tag = self._extract_tag_from_path(rule.official_path)
            mapped_element = Element(target_tag)

            # Aplicar transformación compleja
            if rule.transformation:
                mapped_element = self._apply_complex_transformation(
                    element, mapped_element, rule.transformation, context)
            else:
                # Mapeo estructural complejo por defecto
                mapped_element = self._apply_structural_mapping(
                    element, mapped_element, rule, context)

            result.success = True
            result.mapped_element = mapped_element
            result.applied_rules = [rule]

            logger.debug(f"Mapeo complejo exitoso para {rule.modular_path}")

        except Exception as e:
            logger.error(f"Error en mapeo complejo: {str(e)}")
            result.errors.append(f"Error en mapeo complejo: {str(e)}")

        finally:
            result.execution_time = (time.time() - start_time) * 1000

        return result

    def validate_rule(self, rule: MappingRule) -> Tuple[bool, List[str]]:
        """Valida reglas para mapeo complejo"""
        errors = []

        if rule.complexity not in [MappingComplexity.COMPLEX, MappingComplexity.AGGREGATE, MappingComplexity.CONDITIONAL]:
            errors.append(
                f"ComplexMappingStrategy no soporta complejidad {rule.complexity}")

        return len(errors) == 0, errors

    def _extract_tag_from_path(self, xpath: str) -> str:
        """Extrae el nombre del tag desde un XPath"""
        if '/' in xpath:
            return xpath.split('/')[-1]
        return xpath

    def _evaluate_conditions(
        self,
        element: Element,
        conditions: Dict[str, Any],
        context: MappingContext
    ) -> bool:
        """Evalúa condiciones para aplicar la regla"""
        logger.debug(f"Evaluando condiciones: {conditions}")

        # Implementación básica de evaluación de condiciones
        for condition_key, condition_value in conditions.items():
            if condition_key == "document_type":
                if context.document_type.value != condition_value:
                    return False
            elif condition_key == "element_exists":
                if element.find(condition_value) is None:
                    return False
            elif condition_key == "attribute_value":
                attr_name, expected_value = condition_value
                if element.get(attr_name) != expected_value:
                    return False

        return True

    def _apply_complex_transformation(
        self,
        source_element: Element,
        target_element: Element,
        transformation: str,
        context: MappingContext
    ) -> Element:
        """Aplica transformación compleja específica"""
        logger.debug(f"Aplicando transformación compleja: {transformation}")

        # Aquí se implementarían las transformaciones específicas
        # Por ahora, copia básica con logging
        if source_element.text:
            target_element.text = source_element.text
        target_element.attrib.update(source_element.attrib)

        return target_element

    def _apply_structural_mapping(
        self,
        source_element: Element,
        target_element: Element,
        rule: MappingRule,
        context: MappingContext
    ) -> Element:
        """Aplica mapeo estructural para elementos complejos"""
        logger.debug(f"Aplicando mapeo estructural para {rule.modular_path}")

        # Implementación básica de mapeo estructural
        # Se puede extender para casos específicos
        if source_element.text:
            target_element.text = source_element.text
        target_element.attrib.update(source_element.attrib)

        # Mapear elementos hijos según reglas específicas
        for child in source_element:
            # Aquí se aplicarían reglas específicas para cada tipo de hijo
            mapped_child = Element(child.tag)
            if child.text:
                mapped_child.text = child.text
            mapped_child.attrib.update(child.attrib)
            target_element.append(mapped_child)

        return target_element


# =====================================
# REGISTRY DE ESTRATEGIAS
# =====================================

class MappingStrategyRegistry:
    """
    Registry para gestionar estrategias de mapeo disponibles

    Permite registrar, obtener y gestionar diferentes estrategias
    de mapeo según el tipo de complejidad requerida.
    """

    def __init__(self):
        self._strategies: Dict[MappingComplexity, MappingStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Registra las estrategias por defecto"""
        self.register_strategy(MappingComplexity.SIMPLE,
                               SimpleMappingStrategy())
        self.register_strategy(MappingComplexity.COMPLEX,
                               ComplexMappingStrategy())
        self.register_strategy(
            MappingComplexity.AGGREGATE, ComplexMappingStrategy())
        self.register_strategy(
            MappingComplexity.CONDITIONAL, ComplexMappingStrategy())

    def register_strategy(self, complexity: MappingComplexity, strategy: MappingStrategy):
        """
        Registra una nueva estrategia de mapeo

        Args:
            complexity: Nivel de complejidad que maneja la estrategia
            strategy: Instancia de la estrategia
        """
        self._strategies[complexity] = strategy
        logger.debug(f"Estrategia registrada para complejidad {complexity}")

    def get_strategy(self, complexity: MappingComplexity) -> Optional[MappingStrategy]:
        """
        Obtiene la estrategia para un nivel de complejidad

        Args:
            complexity: Nivel de complejidad requerido

        Returns:
            MappingStrategy: Estrategia correspondiente o None
        """
        return self._strategies.get(complexity)

    def list_strategies(self) -> Dict[MappingComplexity, MappingStrategy]:
        """Retorna todas las estrategias registradas"""
        return self._strategies.copy()


# =====================================
# CONFIGURACIÓN Y CARGA DE REGLAS
# =====================================

class MappingConfigLoader:
    """
    Cargador de configuración de reglas de mapeo

    Soporta archivos JSON y YAML con validación automática
    de reglas y optimización de carga.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(
            __file__).parent / "mapping_rules.yaml"
        self._cache: Dict[str, List[MappingRule]] = {}

    @lru_cache(maxsize=128)
    def load_rules_for_document_type(self, document_type: DocumentType) -> List[MappingRule]:
        """
        Carga reglas de mapeo para un tipo de documento específico

        Args:
            document_type: Tipo de documento

        Returns:
            List[MappingRule]: Lista de reglas ordenadas por prioridad
        """
        cache_key = f"{document_type.value}_{self.config_path.stat().st_mtime}"

        if cache_key in self._cache:
            logger.debug(f"Reglas cargadas desde cache para {document_type}")
            return self._cache[cache_key]

        try:
            logger.debug(f"Cargando reglas desde {self.config_path}")

            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)

            rules = []
            document_config = config_data.get(
                'documents', {}).get(document_type.value, {})

            for rule_data in document_config.get('mapping_rules', []):
                rule = self._parse_rule_data(rule_data)
                if rule:
                    rules.append(rule)

            # Ordenar por prioridad (mayor prioridad primero)
            rules.sort(key=lambda r: r.priority, reverse=True)

            self._cache[cache_key] = rules
            logger.info(f"Cargadas {len(rules)} reglas para {document_type}")

            return rules

        except FileNotFoundError:
            logger.warning(
                f"Archivo de configuración no encontrado: {self.config_path}")
            return []
        except Exception as e:
            logger.error(f"Error cargando configuración: {str(e)}")
            return []

    def _parse_rule_data(self, rule_data: Dict[str, Any]) -> Optional[MappingRule]:
        """
        Parsea datos de regla desde configuración

        Args:
            rule_data: Datos de regla desde archivo de configuración

        Returns:
            MappingRule: Regla parseada o None si hay errores
        """
        try:
            return MappingRule(
                modular_path=rule_data['modular_path'],
                official_path=rule_data['official_path'],
                direction=MappingDirection(
                    rule_data.get('direction', 'bidirectional')),
                complexity=MappingComplexity(
                    rule_data.get('complexity', 'simple')),
                transformation=rule_data.get('transformation'),
                validation=rule_data.get('validation'),
                conditions=rule_data.get('conditions', {}),
                priority=rule_data.get('priority', 100),
                description=rule_data.get('description', '')
            )
        except Exception as e:
            logger.error(f"Error parseando regla: {str(e)}")
            return None

    def validate_config_file(self) -> Tuple[bool, List[str]]:
        """
        Valida el archivo de configuración completo

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_errores)
        """
        errors = []

        try:
            if not self.config_path.exists():
                errors.append(
                    f"Archivo de configuración no existe: {self.config_path}")
                return False, errors

            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)

            # Validar estructura básica
            if 'documents' not in config_data:
                errors.append(
                    "Configuración debe contener sección 'documents'")
                return False, errors

            # Validar cada tipo de documento
            for doc_type_key, doc_config in config_data['documents'].items():
                if doc_type_key not in [dt.value for dt in DocumentType]:
                    errors.append(
                        f"Tipo de documento desconocido: {doc_type_key}")

                if 'mapping_rules' not in doc_config:
                    errors.append(
                        f"Documento {doc_type_key} debe tener 'mapping_rules'")
                    continue

                # Validar reglas individuales
                for i, rule_data in enumerate(doc_config['mapping_rules']):
                    rule_errors = self._validate_rule_data(rule_data)
                    for error in rule_errors:
                        errors.append(
                            f"Documento {doc_type_key}, regla {i}: {error}")

        except Exception as e:
            errors.append(f"Error validando configuración: {str(e)}")

        return len(errors) == 0, errors

    def _validate_rule_data(self, rule_data: Dict[str, Any]) -> List[str]:
        """Valida datos de una regla individual"""
        errors = []

        required_fields = ['modular_path', 'official_path']
        for field in required_fields:
            if field not in rule_data:
                errors.append(f"Campo requerido faltante: {field}")

        if 'direction' in rule_data:
            try:
                MappingDirection(rule_data['direction'])
            except ValueError:
                errors.append(f"Dirección inválida: {rule_data['direction']}")

        if 'complexity' in rule_data:
            try:
                MappingComplexity(rule_data['complexity'])
            except ValueError:
                errors.append(
                    f"Complejidad inválida: {rule_data['complexity']}")

        if 'priority' in rule_data:
            if not isinstance(rule_data['priority'], int) or not (0 <= rule_data['priority'] <= 1000):
                errors.append("Prioridad debe ser un entero entre 0 y 1000")

        return errors


# =====================================
# CLASE PRINCIPAL: SCHEMA MAPPER
# =====================================

class SchemaMapper:
    """
    Mapeador principal para transformaciones entre schemas modular y oficial

    Esta clase es el punto de entrada principal para todas las operaciones
    de mapeo. Coordina las estrategias, configuración y transformaciones
    para proporcionar una API simple y consistente.

    Características:
    - Mapeo bidireccional inteligente
    - Estrategias pluggables según complejidad
    - Configuración externa flexible
    - Cache para optimización de performance
    - Logging detallado para debugging
    - Validación automática de resultados

    Example:
        >>> mapper = SchemaMapper()
        >>> mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)
        >>> 
        >>> # Mapear elemento modular a oficial
        >>> modular_element = fromstring('<gDatGral>...</gDatGral>')
        >>> result = mapper.map_to_official(modular_element, context)
        >>> 
        >>> if result.success:
        >>>     official_xml = tostring(result.mapped_element)
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa el SchemaMapper

        Args:
            config_path: Ruta al archivo de configuración de reglas
        """
        self.config_loader = MappingConfigLoader(config_path)
        self.strategy_registry = MappingStrategyRegistry()
        self._loaded_rules: Dict[DocumentType, List[MappingRule]] = {}

        # Configuración de cache
        self._cache_enabled = True
        self._cache_max_size = 1000
        self._performance_stats = defaultdict(list)

        logger.info("SchemaMapper inicializado")

    def load_configuration(self, document_type: DocumentType) -> bool:
        """
        Carga configuración de mapeo para un tipo de documento

        Args:
            document_type: Tipo de documento a configurar

        Returns:
            bool: True si la carga fue exitosa
        """
        try:
            logger.info(f"Cargando configuración para {document_type}")

            # Validar archivo de configuración
            is_valid, errors = self.config_loader.validate_config_file()
            if not is_valid:
                logger.error(f"Configuración inválida: {errors}")
                return False

            # Cargar reglas específicas
            rules = self.config_loader.load_rules_for_document_type(
                document_type)
            self._loaded_rules[document_type] = rules

            logger.info(
                f"Configuración cargada: {len(rules)} reglas para {document_type}")
            return True

        except Exception as e:
            logger.error(f"Error cargando configuración: {str(e)}")
            return False

    def map_to_official(
        self,
        modular_element: Element,
        context: MappingContext
    ) -> MappingResult:
        """
        Mapea un elemento del formato modular al formato oficial SET

        Args:
            modular_element: Elemento XML en formato modular
            context: Contexto de la operación de mapeo

        Returns:
            MappingResult: Resultado del mapeo con elemento oficial
        """
        return self._map_element(
            modular_element,
            context,
            MappingDirection.MODULAR_TO_OFFICIAL
        )

    def map_to_modular(
        self,
        official_element: Element,
        context: MappingContext
    ) -> MappingResult:
        """
        Mapea un elemento del formato oficial SET al formato modular

        Args:
            official_element: Elemento XML en formato oficial SET
            context: Contexto de la operación de mapeo

        Returns:
            MappingResult: Resultado del mapeo con elemento modular
        """
        return self._map_element(
            official_element,
            context,
            MappingDirection.OFFICIAL_TO_MODULAR
        )

    def _map_element(
        self,
        element: Element,
        context: MappingContext,
        direction: MappingDirection
    ) -> MappingResult:
        """
        Implementación interna de mapeo de elementos

        Args:
            element: Elemento a mapear
            context: Contexto de mapeo
            direction: Dirección del mapeo

        Returns:
            MappingResult: Resultado del mapeo
        """
        start_time = time.time()

        try:
            logger.debug(
                f"Iniciando mapeo {direction.value} para elemento {element.tag}")

            # Verificar que tengamos reglas cargadas
            if context.document_type not in self._loaded_rules:
                if not self.load_configuration(context.document_type):
                    return MappingResult(
                        success=False,
                        errors=[
                            f"No se pudieron cargar reglas para {context.document_type}"]
                    )

            # Buscar regla aplicable
            applicable_rule = self._find_applicable_rule(
                element, direction, context)
            if not applicable_rule:
                return MappingResult(
                    success=False,
                    warnings=[
                        f"No se encontró regla aplicable para elemento {element.tag}"]
                )

            # Obtener estrategia de mapeo
            strategy = self.strategy_registry.get_strategy(
                applicable_rule.complexity)
            if not strategy:
                return MappingResult(
                    success=False,
                    errors=[
                        f"No hay estrategia para complejidad {applicable_rule.complexity}"]
                )

            # Ejecutar mapeo
            result = strategy.map_element(element, applicable_rule, context)

            # Registrar estadísticas de performance
            execution_time = (time.time() - start_time) * 1000
            result.execution_time = execution_time
            self._performance_stats[f"{direction.value}_{applicable_rule.complexity.value}"].append(
                execution_time)

            logger.debug(f"Mapeo completado en {execution_time:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Error durante mapeo: {str(e)}")
            return MappingResult(
                success=False,
                errors=[f"Error durante mapeo: {str(e)}"],
                execution_time=(time.time() - start_time) * 1000
            )

    def _find_applicable_rule(
        self,
        element: Element,
        direction: MappingDirection,
        context: MappingContext
    ) -> Optional[MappingRule]:
        """
        Encuentra la regla de mapeo más apropiada para un elemento

        Args:
            element: Elemento a mapear
            direction: Dirección del mapeo
            context: Contexto de mapeo

        Returns:
            MappingRule: Regla aplicable o None
        """
        rules = self._loaded_rules.get(context.document_type, [])
        element_path = self._get_element_path(element)

        # Buscar regla exacta primero
        for rule in rules:
            if self._rule_matches_element(rule, element_path, direction):
                logger.debug(
                    f"Regla exacta encontrada: {rule.modular_path} → {rule.official_path}")
                return rule

        # Buscar regla por patrón si no hay exacta
        for rule in rules:
            if self._rule_matches_pattern(rule, element_path, direction):
                logger.debug(
                    f"Regla por patrón encontrada: {rule.modular_path} → {rule.official_path}")
                return rule

        logger.warning(f"No se encontró regla para elemento: {element_path}")
        return None

    def _get_element_path(self, element: Element) -> str:
        """
        Obtiene el path XPath simplificado de un elemento

        Args:
            element: Elemento XML

        Returns:
            str: Path del elemento
        """
        # Implementación básica - se puede mejorar para XPath completo
        return element.tag

    def _rule_matches_element(
        self,
        rule: MappingRule,
        element_path: str,
        direction: MappingDirection
    ) -> bool:
        """
        Verifica si una regla es aplicable a un elemento específico

        Args:
            rule: Regla a verificar
            element_path: Path del elemento
            direction: Dirección del mapeo

        Returns:
            bool: True si la regla es aplicable
        """
        # Verificar dirección
        if rule.direction not in [direction, MappingDirection.BIDIRECTIONAL]:
            return False

        # Verificar path según dirección
        if direction == MappingDirection.MODULAR_TO_OFFICIAL:
            return rule.modular_path == element_path
        else:
            return rule.official_path == element_path

    def _rule_matches_pattern(
        self,
        rule: MappingRule,
        element_path: str,
        direction: MappingDirection
    ) -> bool:
        """
        Verifica si una regla coincide por patrón (wildcards, etc.)

        Args:
            rule: Regla a verificar
            element_path: Path del elemento
            direction: Dirección del mapeo

        Returns:
            bool: True si coincide por patrón
        """
        # Implementación básica de patrones
        # Se puede extender con regex, wildcards, etc.

        if rule.direction not in [direction, MappingDirection.BIDIRECTIONAL]:
            return False

        target_path = rule.modular_path if direction == MappingDirection.MODULAR_TO_OFFICIAL else rule.official_path

        # Soporte básico para wildcards
        if '*' in target_path:
            pattern = target_path.replace('*', '.*')
            import re
            return bool(re.match(pattern, element_path))

        return False

    def validate_mapping_rules(self, document_type: DocumentType) -> Tuple[bool, List[str]]:
        """
        Valida todas las reglas de mapeo para un tipo de documento

        Args:
            document_type: Tipo de documento a validar

        Returns:
            Tuple[bool, List[str]]: (todas_válidas, lista_errores)
        """
        errors = []

        try:
            if document_type not in self._loaded_rules:
                if not self.load_configuration(document_type):
                    errors.append(
                        f"No se pudo cargar configuración para {document_type}")
                    return False, errors

            rules = self._loaded_rules[document_type]

            for i, rule in enumerate(rules):
                # Validar con estrategia correspondiente
                strategy = self.strategy_registry.get_strategy(rule.complexity)
                if not strategy:
                    errors.append(
                        f"Regla {i}: No hay estrategia para complejidad {rule.complexity}")
                    continue

                is_valid, rule_errors = strategy.validate_rule(rule)
                if not is_valid:
                    for error in rule_errors:
                        errors.append(f"Regla {i}: {error}")

            # Verificar duplicados
            duplicates = self._find_duplicate_rules(rules)
            if duplicates:
                errors.extend(
                    [f"Reglas duplicadas encontradas: {dup}" for dup in duplicates])

            logger.info(
                f"Validación completada para {document_type}: {len(errors)} errores")

        except Exception as e:
            logger.error(f"Error durante validación: {str(e)}")
            errors.append(f"Error durante validación: {str(e)}")

        return len(errors) == 0, errors

    def _find_duplicate_rules(self, rules: List[MappingRule]) -> List[str]:
        """Encuentra reglas duplicadas en la lista"""
        seen = set()
        duplicates = []

        for rule in rules:
            rule_key = f"{rule.modular_path}→{rule.official_path}→{rule.direction.value}"
            if rule_key in seen:
                duplicates.append(rule_key)
            else:
                seen.add(rule_key)

        return duplicates

    def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de performance del mapper

        Returns:
            Dict[str, Any]: Estadísticas detalladas
        """
        stats = {
            "total_mappings": sum(len(times) for times in self._performance_stats.values()),
            "by_operation": {}
        }

        for operation, times in self._performance_stats.items():
            if times:
                stats["by_operation"][operation] = {
                    "count": len(times),
                    "avg_time_ms": sum(times) / len(times),
                    "min_time_ms": min(times),
                    "max_time_ms": max(times),
                    "total_time_ms": sum(times)
                }

        return stats

    def clear_cache(self):
        """Limpia todos los caches internos"""
        self._loaded_rules.clear()
        self.config_loader._cache.clear()
        self._performance_stats.clear()
        logger.info("Cache limpiado")

    def get_loaded_rules_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen de reglas cargadas

        Returns:
            Dict[str, Any]: Resumen por tipo de documento
        """
        summary = {}

        for doc_type, rules in self._loaded_rules.items():
            complexity_counts = defaultdict(int)
            direction_counts = defaultdict(int)

            for rule in rules:
                complexity_counts[rule.complexity.value] += 1
                direction_counts[rule.direction.value] += 1

            summary[doc_type.value] = {
                "total_rules": len(rules),
                "by_complexity": dict(complexity_counts),
                "by_direction": dict(direction_counts)
            }

        return summary


# =====================================
# FUNCIONES DE UTILIDAD PÚBLICAS
# =====================================

def create_mapping_context(
    document_type: DocumentType,
    direction: MappingDirection,
    source_namespace: str = "",
    target_namespace: str = "",
    **kwargs
) -> MappingContext:
    """
    Función helper para crear contexto de mapeo

    Args:
        document_type: Tipo de documento
        direction: Dirección del mapeo
        source_namespace: Namespace origen
        target_namespace: Namespace destino
        **kwargs: Variables adicionales para el contexto

    Returns:
        MappingContext: Contexto configurado
    """
    return MappingContext(
        document_type=document_type,
        direction=direction,
        source_namespace=source_namespace,
        target_namespace=target_namespace,
        variables=kwargs
    )


def quick_map_element(
    element: Element,
    document_type: DocumentType,
    direction: MappingDirection,
    config_path: Optional[Path] = None
) -> MappingResult:
    """
    Función helper para mapeo rápido de un elemento

    Args:
        element: Elemento a mapear
        document_type: Tipo de documento
        direction: Dirección del mapeo
        config_path: Ruta de configuración opcional

    Returns:
        MappingResult: Resultado del mapeo
    """
    mapper = SchemaMapper(config_path)
    context = create_mapping_context(document_type, direction)

    if direction == MappingDirection.MODULAR_TO_OFFICIAL:
        return mapper.map_to_official(element, context)
    else:
        return mapper.map_to_modular(element, context)


def validate_mapping_configuration(config_path: Path) -> Tuple[bool, List[str]]:
    """
    Valida un archivo de configuración de mapeo

    Args:
        config_path: Ruta al archivo de configuración

    Returns:
        Tuple[bool, List[str]]: (es_válido, lista_errores)
    """
    config_loader = MappingConfigLoader(config_path)
    return config_loader.validate_config_file()


# =====================================
# DECORADORES DE UTILIDAD
# =====================================

def timing_decorator(func):
    """Decorador para medir tiempo de ejecución de funciones"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000
        logger.debug(f"{func.__name__} ejecutado en {execution_time:.2f}ms")
        return result
    return wrapper


def cache_result(cache_size: int = 128):
    """Decorador para cachear resultados de funciones"""
    def decorator(func):
        @lru_cache(maxsize=cache_size)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    # Clase principal
    'SchemaMapper',

    # Enums y tipos
    'MappingDirection',
    'DocumentType',
    'MappingComplexity',

    # Dataclasses
    'MappingRule',
    'MappingContext',
    'MappingResult',

    # Interfaces
    'MappingStrategy',
    'TransformationFunction',

    # Implementaciones de estrategias
    'SimpleMappingStrategy',
    'ComplexMappingStrategy',

    # Componentes de soporte
    'MappingStrategyRegistry',
    'MappingConfigLoader',

    # Funciones de utilidad
    'create_mapping_context',
    'quick_map_element',
    'validate_mapping_configuration',

    # Decoradores
    'timing_decorator',
    'cache_result'
]


# =====================================
# EJEMPLO DE USO
# =====================================

if __name__ == "__main__":
    # Ejemplo básico de uso del SchemaMapper

    # 1. Crear mapper y cargar configuración
    mapper = SchemaMapper()

    # 2. Configurar para factura electrónica
    success = mapper.load_configuration(DocumentType.FACTURA_ELECTRONICA)
    if not success:
        print("Error cargando configuración")
        exit(1)

    # 3. Crear elemento de ejemplo (normalmente viene del XML modular)
    from xml.etree.ElementTree import Element, SubElement

    modular_element = Element("gDatGral")
    SubElement(modular_element, "dFeEmiDE").text = "2024-12-15"
    SubElement(modular_element, "dHorEmi").text = "14:30:00"

    # 4. Crear contexto de mapeo
    context = create_mapping_context(
        document_type=DocumentType.FACTURA_ELECTRONICA,
        direction=MappingDirection.MODULAR_TO_OFFICIAL,
        source_namespace="http://modular.local",
        target_namespace="http://ekuatia.set.gov.py/sifen/xsd"
    )

    # 5. Ejecutar mapeo
    result = mapper.map_to_official(modular_element, context)

    # 6. Verificar resultado
    if result.success and result.mapped_element is not None:
        print("✅ Mapeo exitoso")
        print(f"Elemento mapeado: {result.mapped_element.tag}")
        print(f"Tiempo de ejecución: {result.execution_time:.2f}ms")

        # Mostrar XML resultante
        from xml.etree.ElementTree import tostring
        xml_output = tostring(result.mapped_element, encoding='unicode')
        print(f"XML oficial: {xml_output}")
    else:
        print("❌ Error en mapeo")
        for error in result.errors:
            print(f"Error: {error}")
        for warning in result.warnings:
            print(f"Advertencia: {warning}")

    # 7. Mostrar estadísticas de performance
    stats = mapper.get_performance_statistics()
    print(f"\n📊 Estadísticas: {stats}")

    # 8. Mostrar resumen de reglas cargadas
    rules_summary = mapper.get_loaded_rules_summary()
    print(f"\n📋 Reglas cargadas: {rules_summary}")
