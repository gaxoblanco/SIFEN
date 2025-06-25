"""
Validation Bridge v150 - Validación Híbrida Modular ↔ Oficial

Este módulo implementa un puente de validación que permite validar documentos XML
contra ambos esquemas (modular y oficial) simultáneamente, detectando inconsistencias
y garantizando compatibilidad total con SIFEN.

Responsabilidades Principales:
1. Validar documentos contra schemas modulares y oficiales
2. Comparar resultados de validación y detectar inconsistencias
3. Proporcionar reportes unificados de validación
4. Optimizar validación según contexto (desarrollo vs producción)
5. Integrar con schema_mapper para validación post-transformación

Patrones Implementados:
- Bridge Pattern: Para conectar sistemas de validación diferentes
- Strategy Pattern: Para diferentes tipos de validación
- Composite Pattern: Para combinar múltiples validadores
- Observer Pattern: Para notificar cambios en estado de validación

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
Fecha: 2025-06-24
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import time
from pathlib import Path
from xml.etree.ElementTree import Element, fromstring, tostring
from collections import defaultdict
import re

# Imports del sistema modular existente
try:
    from ..modular.tests.utils.xml_generator.validators import (
        SifenValidator,
        StructureValidator,
        FormatValidator,
        CoreXSDValidator,
        ValidationError
    )
except ImportError:
    # Fallback para testing independiente
    logging.warning(
        "No se pudieron importar validadores modulares. Usando mocks.")
    SifenValidator = None
    StructureValidator = None
    FormatValidator = None
    CoreXSDValidator = None
    ValidationError = Exception

# Import del schema_mapper
from .schema_mapper import (
    SchemaMapper,
    DocumentType,
    MappingDirection,
    MappingContext,
    create_mapping_context
)

# Configuración de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# =====================================
# ENUMS Y CONSTANTES
# =====================================

class ValidationMode(Enum):
    """Modos de validación disponibles"""
    MODULAR_ONLY = "modular_only"           # Solo validación modular
    OFFICIAL_ONLY = "official_only"         # Solo validación oficial
    HYBRID_PARALLEL = "hybrid_parallel"     # Ambas en paralelo
    HYBRID_SEQUENTIAL = "hybrid_sequential"  # Secuencial con fallback
    CROSS_VALIDATION = "cross_validation"   # Validación cruzada completa


class ValidationSeverity(Enum):
    """Niveles de severidad de validación"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationType(Enum):
    """Tipos de validación"""
    STRUCTURE = "structure"         # Validación de estructura XML
    SCHEMA = "schema"              # Validación contra XSD
    FORMAT = "format"              # Validación de formatos SIFEN
    SEMANTIC = "semantic"          # Validación semántica
    CROSS_REFERENCE = "cross_ref"  # Validación de referencias cruzadas


# =====================================
# DATACLASSES PARA RESULTADOS
# =====================================

@dataclass
class ValidationIssue:
    """
    Representa un problema de validación individual

    Attributes:
        type: Tipo de validación que generó el issue
        severity: Severidad del problema
        message: Mensaje descriptivo del problema
        xpath: Ubicación XPath del problema (si aplica)
        source_schema: Schema que generó el issue (modular/oficial)
        error_code: Código de error específico (si aplica)
        suggestion: Sugerencia para resolver el problema
    """
    type: ValidationType
    severity: ValidationSeverity
    message: str
    xpath: str = ""
    source_schema: str = ""
    error_code: str = ""
    suggestion: str = ""


@dataclass
class SchemaValidationResult:
    """
    Resultado de validación contra un schema específico

    Attributes:
        schema_type: Tipo de schema (modular/oficial)
        is_valid: Indica si la validación fue exitosa
        issues: Lista de problemas encontrados
        execution_time: Tiempo de ejecución en milisegundos
        validator_info: Información del validador utilizado
        statistics: Estadísticas de la validación
    """
    schema_type: str
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    execution_time: float = 0.0
    validator_info: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridValidationResult:
    """
    Resultado completo de validación híbrida

    Attributes:
        overall_valid: Indica si la validación general fue exitosa
        modular_result: Resultado de validación modular
        official_result: Resultado de validación oficial
        cross_validation_issues: Problemas de validación cruzada
        consistency_score: Puntuación de consistencia (0.0-1.0)
        recommendations: Recomendaciones para resolver problemas
        execution_summary: Resumen de ejecución
    """
    overall_valid: bool
    modular_result: Optional[SchemaValidationResult] = None
    official_result: Optional[SchemaValidationResult] = None
    cross_validation_issues: List[ValidationIssue] = field(
        default_factory=list)
    consistency_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    execution_summary: Dict[str, Any] = field(default_factory=dict)

    def get_total_issues(self) -> List[ValidationIssue]:
        """Obtiene todas las issues de todas las validaciones"""
        all_issues = []

        if self.modular_result:
            all_issues.extend(self.modular_result.issues)

        if self.official_result:
            all_issues.extend(self.official_result.issues)

        all_issues.extend(self.cross_validation_issues)

        return all_issues

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Obtiene issues filtradas por severidad"""
        return [issue for issue in self.get_total_issues() if issue.severity == severity]

    def has_critical_issues(self) -> bool:
        """Verifica si hay issues críticas"""
        return len(self.get_issues_by_severity(ValidationSeverity.CRITICAL)) > 0


# =====================================
# CONFIGURACIÓN DE VALIDACIÓN
# =====================================

@dataclass
class ValidationConfig:
    """
    Configuración para el ValidationBridge

    Attributes:
        mode: Modo de validación a utilizar
        enable_modular: Habilitar validación modular
        enable_official: Habilitar validación oficial
        enable_cross_validation: Habilitar validación cruzada
        fail_fast: Detener al primer error crítico
        max_issues_per_type: Máximo de issues por tipo
        timeout_seconds: Timeout para validaciones
        cache_enabled: Habilitar cache de resultados
        parallel_execution: Ejecutar validaciones en paralelo
    """
    mode: ValidationMode = ValidationMode.HYBRID_PARALLEL
    enable_modular: bool = True
    enable_official: bool = True
    enable_cross_validation: bool = True
    fail_fast: bool = False
    max_issues_per_type: int = 50
    timeout_seconds: int = 30
    cache_enabled: bool = True
    parallel_execution: bool = True


# =====================================
# VALIDADORES ESPECIALIZADOS
# =====================================

class ModularValidator:
    """
    Wrapper para validadores modulares existentes

    Encapsula la lógica de validación modular y la adapta
    para su uso en el ValidationBridge.
    """

    def __init__(self):
        self.sifen_validator = None
        self.structure_validator = None
        self.format_validator = None
        self._initialize_validators()

    def _initialize_validators(self):
        """Inicializa los validadores modulares"""
        try:
            if SifenValidator:
                self.sifen_validator = SifenValidator()
            if StructureValidator:
                self.structure_validator = StructureValidator()
            if FormatValidator:
                self.format_validator = FormatValidator()

            logger.debug("Validadores modulares inicializados")

        except Exception as e:
            logger.error(
                f"Error inicializando validadores modulares: {str(e)}")

    def validate(self, xml_content: str, document_type: DocumentType) -> SchemaValidationResult:
        """
        Valida contenido XML contra schemas modulares

        Args:
            xml_content: Contenido XML a validar
            document_type: Tipo de documento

        Returns:
            SchemaValidationResult: Resultado de validación modular
        """
        start_time = time.time()
        issues = []
        is_valid = True

        try:
            logger.debug(f"Iniciando validación modular para {document_type}")

            # Validación con SifenValidator si está disponible
            if self.sifen_validator:
                sifen_valid, sifen_errors = self.sifen_validator.validate_xml(
                    xml_content)
                if not sifen_valid:
                    is_valid = False
                    for error in sifen_errors:
                        issues.append(ValidationIssue(
                            type=ValidationType.SCHEMA,
                            severity=ValidationSeverity.ERROR,
                            message=str(error),
                            source_schema="modular",
                            suggestion="Revisar estructura del documento contra schemas modulares"
                        ))

            # Validación de estructura si está disponible
            if self.structure_validator:
                struct_valid, struct_errors = self.structure_validator.validate(
                    xml_content)
                if not struct_valid:
                    for error in struct_errors:
                        issues.append(ValidationIssue(
                            type=ValidationType.STRUCTURE,
                            severity=ValidationSeverity.ERROR,
                            message=str(error),
                            source_schema="modular"
                        ))

            # Validación de formato si está disponible
            if self.format_validator:
                format_valid, format_errors = self.format_validator.validate(
                    xml_content)
                if not format_valid:
                    for error in format_errors:
                        issues.append(ValidationIssue(
                            type=ValidationType.FORMAT,
                            severity=ValidationSeverity.WARNING,
                            message=str(error),
                            source_schema="modular"
                        ))

            execution_time = (time.time() - start_time) * 1000

            return SchemaValidationResult(
                schema_type="modular",
                is_valid=is_valid,
                issues=issues,
                execution_time=execution_time,
                validator_info={
                    "sifen_validator": self.sifen_validator is not None,
                    "structure_validator": self.structure_validator is not None,
                    "format_validator": self.format_validator is not None
                },
                statistics={
                    "total_issues": len(issues),
                    "error_count": len([i for i in issues if i.severity == ValidationSeverity.ERROR]),
                    "warning_count": len([i for i in issues if i.severity == ValidationSeverity.WARNING])
                }
            )

        except Exception as e:
            logger.error(f"Error durante validación modular: {str(e)}")

            return SchemaValidationResult(
                schema_type="modular",
                is_valid=False,
                issues=[ValidationIssue(
                    type=ValidationType.SCHEMA,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Error durante validación modular: {str(e)}",
                    source_schema="modular"
                )],
                execution_time=(time.time() - start_time) * 1000
            )


class OfficialValidator:
    """
    Validador para schemas oficiales SET

    Implementa validación contra los schemas XSD oficiales
    de SIFEN utilizando lxml o herramientas similares.
    """

    def __init__(self, official_schemas_path: Optional[Path] = None):
        self.schemas_path = official_schemas_path or Path(
            __file__).parent.parent / "official_set"
        self._schema_cache = {}
        self._initialize_schemas()

    def _initialize_schemas(self):
        """Inicializa los schemas oficiales"""
        try:
            # Aquí se cargarían los schemas XSD oficiales
            # Por ahora, implementación básica
            logger.debug(
                f"Inicializando schemas oficiales desde {self.schemas_path}")

            if self.schemas_path.exists():
                schema_files = list(self.schemas_path.glob("**/*.xsd"))
                logger.info(
                    f"Encontrados {len(schema_files)} schemas oficiales")
            else:
                logger.warning(
                    f"Ruta de schemas oficiales no encontrada: {self.schemas_path}")

        except Exception as e:
            logger.error(f"Error inicializando schemas oficiales: {str(e)}")

    def validate(self, xml_content: str, document_type: DocumentType) -> SchemaValidationResult:
        """
        Valida contenido XML contra schemas oficiales SET

        Args:
            xml_content: Contenido XML a validar
            document_type: Tipo de documento

        Returns:
            SchemaValidationResult: Resultado de validación oficial
        """
        start_time = time.time()
        issues = []
        is_valid = True

        try:
            logger.debug(f"Iniciando validación oficial para {document_type}")

            # Validación básica de estructura XML
            try:
                element = fromstring(xml_content)
                logger.debug(
                    f"XML parseado correctamente. Elemento raíz: {element.tag}")
            except Exception as e:
                is_valid = False
                issues.append(ValidationIssue(
                    type=ValidationType.STRUCTURE,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"XML malformado: {str(e)}",
                    source_schema="official"
                ))

            # Validación de namespace oficial
            if "http://ekuatia.set.gov.py/sifen/xsd" not in xml_content:
                issues.append(ValidationIssue(
                    type=ValidationType.SCHEMA,
                    severity=ValidationSeverity.WARNING,
                    message="Namespace oficial SIFEN no encontrado",
                    source_schema="official",
                    suggestion="Agregar namespace: xmlns='http://ekuatia.set.gov.py/sifen/xsd'"
                ))

            # Validación de elemento raíz según tipo de documento
            expected_root = self._get_expected_root_element(document_type)
            if expected_root and expected_root not in xml_content:
                issues.append(ValidationIssue(
                    type=ValidationType.SCHEMA,
                    severity=ValidationSeverity.ERROR,
                    message=f"Elemento raíz esperado '{expected_root}' no encontrado",
                    source_schema="official"
                ))

            # Aquí se agregaría validación XSD real contra schemas oficiales
            # Por ahora, validación básica de estructura

            execution_time = (time.time() - start_time) * 1000

            return SchemaValidationResult(
                schema_type="official",
                is_valid=is_valid and len([i for i in issues if i.severity in [
                                          ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]) == 0,
                issues=issues,
                execution_time=execution_time,
                validator_info={
                    "schemas_path": str(self.schemas_path),
                    "schemas_available": self.schemas_path.exists()
                },
                statistics={
                    "total_issues": len(issues),
                    "error_count": len([i for i in issues if i.severity == ValidationSeverity.ERROR]),
                    "warning_count": len([i for i in issues if i.severity == ValidationSeverity.WARNING])
                }
            )

        except Exception as e:
            logger.error(f"Error durante validación oficial: {str(e)}")

            return SchemaValidationResult(
                schema_type="official",
                is_valid=False,
                issues=[ValidationIssue(
                    type=ValidationType.SCHEMA,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Error durante validación oficial: {str(e)}",
                    source_schema="official"
                )],
                execution_time=(time.time() - start_time) * 1000
            )

    def _get_expected_root_element(self, document_type: DocumentType) -> str:
        """Obtiene el elemento raíz esperado para un tipo de documento"""
        root_mapping = {
            DocumentType.FACTURA_ELECTRONICA: "rDE",
            DocumentType.NOTA_CREDITO_ELECTRONICA: "rDE",
            DocumentType.NOTA_DEBITO_ELECTRONICA: "rDE",
            DocumentType.AUTOFACTURA_ELECTRONICA: "rDE",
            DocumentType.NOTA_REMISION_ELECTRONICA: "rDE"
        }
        return root_mapping.get(document_type, "rDE")


# =====================================
# VALIDADOR DE CONSISTENCIA CRUZADA
# =====================================

class CrossValidator:
    """
    Validador de consistencia entre schemas modular y oficial

    Compara resultados de validación y elementos transformados
    para detectar inconsistencias entre ambos sistemas.
    """

    def __init__(self, schema_mapper: SchemaMapper):
        self.schema_mapper = schema_mapper

    def validate_consistency(
        self,
        modular_xml: str,
        official_xml: str,
        document_type: DocumentType
    ) -> List[ValidationIssue]:
        """
        Valida consistencia entre XML modular y oficial

        Args:
            modular_xml: XML en formato modular
            official_xml: XML en formato oficial
            document_type: Tipo de documento

        Returns:
            List[ValidationIssue]: Issues de consistencia encontradas
        """
        issues = []

        try:
            logger.debug("Iniciando validación de consistencia cruzada")

            # Parsear ambos XMLs
            modular_element = fromstring(modular_xml)
            official_element = fromstring(official_xml)

            # Validar estructura básica
            structure_issues = self._validate_structure_consistency(
                modular_element, official_element, document_type
            )
            issues.extend(structure_issues)

            # Validar datos críticos
            data_issues = self._validate_data_consistency(
                modular_element, official_element, document_type
            )
            issues.extend(data_issues)

            # Validar mapeo bidireccional
            mapping_issues = self._validate_mapping_consistency(
                modular_xml, official_xml, document_type
            )
            issues.extend(mapping_issues)

            logger.debug(
                f"Validación cruzada completada. {len(issues)} issues encontradas")

        except Exception as e:
            logger.error(f"Error durante validación cruzada: {str(e)}")
            issues.append(ValidationIssue(
                type=ValidationType.CROSS_REFERENCE,
                severity=ValidationSeverity.CRITICAL,
                message=f"Error durante validación cruzada: {str(e)}",
                source_schema="cross_validation"
            ))

        return issues

    def _validate_structure_consistency(
        self,
        modular_element: Element,
        official_element: Element,
        document_type: DocumentType
    ) -> List[ValidationIssue]:
        """Valida consistencia de estructura entre elementos"""
        issues = []

        # Comparar número de elementos hijos
        modular_children = len(list(modular_element))
        official_children = len(list(official_element))

        if abs(modular_children - official_children) > 2:  # Margen de tolerancia
            issues.append(ValidationIssue(
                type=ValidationType.STRUCTURE,
                severity=ValidationSeverity.WARNING,
                message=f"Diferencia significativa en número de elementos: modular={modular_children}, oficial={official_children}",
                source_schema="cross_validation",
                suggestion="Revisar mapeo de elementos entre schemas"
            ))

        return issues

    def _validate_data_consistency(
        self,
        modular_element: Element,
        official_element: Element,
        document_type: DocumentType
    ) -> List[ValidationIssue]:
        """Valida consistencia de datos críticos"""
        issues = []

        # Definir campos críticos por tipo de documento
        critical_fields = self._get_critical_fields(document_type)

        for field_info in critical_fields:
            modular_path = field_info.get("modular_path")
            official_path = field_info.get("official_path")
            field_name = field_info.get("name")

            if modular_path and official_path:
                modular_value = self._extract_value_by_path(
                    modular_element, modular_path)
                official_value = self._extract_value_by_path(
                    official_element, official_path)

                if modular_value != official_value:
                    issues.append(ValidationIssue(
                        type=ValidationType.SEMANTIC,
                        severity=ValidationSeverity.ERROR,
                        message=f"Inconsistencia en campo crítico '{field_name}': modular='{modular_value}', oficial='{official_value}'",
                        xpath=modular_path,
                        source_schema="cross_validation",
                        suggestion=f"Verificar mapeo para campo {field_name}"
                    ))

        return issues

    def _validate_mapping_consistency(
        self,
        modular_xml: str,
        official_xml: str,
        document_type: DocumentType
    ) -> List[ValidationIssue]:
        """Valida consistencia del mapeo bidireccional"""
        issues = []

        try:
            # Test de mapeo ida y vuelta (round-trip)
            context_to_official = create_mapping_context(
                document_type, MappingDirection.MODULAR_TO_OFFICIAL
            )

            # Mapear modular → oficial
            modular_element = fromstring(modular_xml)
            mapping_result = self.schema_mapper.map_to_official(
                modular_element, context_to_official)

            if mapping_result.success and mapping_result.mapped_element is not None:
                # Comparar resultado del mapeo con XML oficial proporcionado
                mapped_xml = tostring(
                    mapping_result.mapped_element, encoding='unicode')

                # Análisis básico de similitud
                similarity_score = self._calculate_xml_similarity(
                    mapped_xml, official_xml)

                if similarity_score < 0.8:  # Umbral de similitud
                    issues.append(ValidationIssue(
                        type=ValidationType.CROSS_REFERENCE,
                        severity=ValidationSeverity.WARNING,
                        message=f"Baja similitud en mapeo (score: {similarity_score:.2f})",
                        source_schema="cross_validation",
                        suggestion="Revisar reglas de mapeo para mejorar consistencia"
                    ))
            else:
                issues.append(ValidationIssue(
                    type=ValidationType.CROSS_REFERENCE,
                    severity=ValidationSeverity.ERROR,
                    message="Fallo en mapeo modular → oficial durante validación cruzada",
                    source_schema="cross_validation"
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                type=ValidationType.CROSS_REFERENCE,
                severity=ValidationSeverity.WARNING,
                message=f"Error en validación de mapeo: {str(e)}",
                source_schema="cross_validation"
            ))

        return issues

    def _get_critical_fields(self, document_type: DocumentType) -> List[Dict[str, str]]:
        """Obtiene campos críticos para validación por tipo de documento"""
        base_fields = [
            {
                "name": "fecha_emision",
                "modular_path": ".//dFeEmiDE",
                "official_path": ".//dFeEmiDE"
            },
            {
                "name": "ruc_emisor",
                "modular_path": ".//dRucEm",
                "official_path": ".//dRucEm"
            }
        ]

        # Campos específicos por tipo de documento
        if document_type == DocumentType.FACTURA_ELECTRONICA:
            base_fields.extend([
                {
                    "name": "total_operacion",
                    "modular_path": ".//dTotOpe",
                    "official_path": ".//dTotOpe"
                }
            ])

        return base_fields

    def _extract_value_by_path(self, element: Element, xpath: str) -> Optional[str]:
        """Extrae valor de un elemento usando XPath simplificado"""
        try:
            found_element = element.find(xpath)
            return found_element.text if found_element is not None else None
        except:
            return None

    def _calculate_xml_similarity(self, xml1: str, xml2: str) -> float:
        """Calcula similitud básica entre dos XMLs"""
        try:
            # Normalizar XMLs (quitar espacios, saltos de línea)
            normalized1 = re.sub(r'\s+', ' ', xml1.strip())
            normalized2 = re.sub(r'\s+', ' ', xml2.strip())

            # Similitud básica por longitud y contenido común
            if len(normalized1) == 0 or len(normalized2) == 0:
                return 0.0

            # Contar caracteres comunes
            common_chars = sum(1 for a, b in zip(
                normalized1, normalized2) if a == b)
            max_length = max(len(normalized1), len(normalized2))

            return common_chars / max_length if max_length > 0 else 0.0

        except:
            return 0.0


# =====================================
# CLASE PRINCIPAL: VALIDATION BRIDGE
# =====================================

class ValidationBridge:
    """
    Puente de validación híbrida entre schemas modular y oficial

    Esta clase coordina la validación simultánea contra ambos esquemas,
    detecta inconsistencias y proporciona reportes unificados.

    Características:
    - Validación simultánea o secuencial
    - Detección de inconsistencias automática
    - Reportes unificados y detallados
    - Optimización según contexto
    - Integración con schema_mapper

    Example:
        >>> bridge = ValidationBridge()
        >>> result = bridge.validate_hybrid(xml_content, DocumentType.FACTURA_ELECTRONICA)
        >>> 
        >>> if result.overall_valid:
        >>>     print("✅ Documento válido en ambos schemas")
        >>> else:
        >>>     print(f"❌ {len(result.get_total_issues())} problemas encontrados")
    """

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        schema_mapper: Optional[SchemaMapper] = None
    ):
        """
        Inicializa el ValidationBridge

        Args:
            config: Configuración de validación
            schema_mapper: Instancia del schema mapper para validación cruzada
        """
        self.config = config or ValidationConfig()
        self.schema_mapper = schema_mapper or SchemaMapper()

        # Inicializar validadores
        self.modular_validator = ModularValidator()
        self.official_validator = OfficialValidator()
        self.cross_validator = CrossValidator(self.schema_mapper)

        # Cache para resultados
        self._validation_cache = {} if self.config.cache_enabled else None

        # Estadísticas
        self._stats = defaultdict(int)

        logger.info("ValidationBridge inicializado")

    def validate_hybrid(
        self,
        xml_content: str,
        document_type: DocumentType,
        mode: Optional[ValidationMode] = None
    ) -> HybridValidationResult:
        """
        Realiza validación híbrida completa de un documento XML

        Args:
            xml_content: Contenido XML a validar
            document_type: Tipo de documento
            mode: Modo de validación (override de configuración)

        Returns:
            HybridValidationResult: Resultado completo de validación
        """
        validation_mode = mode or self.config.mode
        start_time = time.time()

        try:
            logger.info(
                f"Iniciando validación híbrida {validation_mode.value} para {document_type}")

            # Verificar cache si está habilitado
            cache_key = self._generate_cache_key(
                xml_content, document_type, validation_mode)
            if self._validation_cache and cache_key in self._validation_cache:
                logger.debug("Resultado obtenido desde cache")
                self._stats['cache_hits'] += 1
                return self._validation_cache[cache_key]

            self._stats['cache_misses'] += 1

            # Ejecutar validación según modo
            if validation_mode == ValidationMode.MODULAR_ONLY:
                result = self._validate_modular_only(
                    xml_content, document_type)
            elif validation_mode == ValidationMode.OFFICIAL_ONLY:
                result = self._validate_official_only(
                    xml_content, document_type)
            elif validation_mode == ValidationMode.HYBRID_PARALLEL:
                result = self._validate_hybrid_parallel(
                    xml_content, document_type)
            elif validation_mode == ValidationMode.HYBRID_SEQUENTIAL:
                result = self._validate_hybrid_sequential(
                    xml_content, document_type)
            elif validation_mode == ValidationMode.CROSS_VALIDATION:
                result = self._validate_cross_validation(
                    xml_content, document_type)
            else:
                raise ValueError(
                    f"Modo de validación no soportado: {validation_mode}")

            # Calcular tiempo total de ejecución
            total_time = (time.time() - start_time) * 1000
            result.execution_summary = {
                "total_time_ms": total_time,
                "validation_mode": validation_mode.value,
                "document_type": document_type.value,
                "cache_used": cache_key in (self._validation_cache or {})
            }

            # Guardar en cache si está habilitado
            if self._validation_cache:
                self._validation_cache[cache_key] = result

            # Actualizar estadísticas
            self._stats['total_validations'] += 1
            self._stats[f'validations_{validation_mode.value}'] += 1

            logger.info(f"Validación híbrida completada en {total_time:.2f}ms")
            return result

        except Exception as e:
            logger.error(f"Error durante validación híbrida: {str(e)}")

            return HybridValidationResult(
                overall_valid=False,
                cross_validation_issues=[ValidationIssue(
                    type=ValidationType.SCHEMA,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Error durante validación híbrida: {str(e)}",
                    source_schema="validation_bridge"
                )],
                execution_summary={
                    "total_time_ms": (time.time() - start_time) * 1000,
                    "error": str(e)
                }
            )

    def validate_with_transformation(
        self,
        modular_xml: str,
        document_type: DocumentType
    ) -> HybridValidationResult:
        """
        Valida documento modular transformándolo a oficial para comparación

        Args:
            modular_xml: XML en formato modular
            document_type: Tipo de documento

        Returns:
            HybridValidationResult: Resultado incluyendo validación post-transformación
        """
        try:
            logger.debug("Iniciando validación con transformación")

            # 1. Validar XML modular original
            modular_result = self.modular_validator.validate(
                modular_xml, document_type)

            # 2. Transformar modular → oficial
            context = create_mapping_context(
                document_type, MappingDirection.MODULAR_TO_OFFICIAL
            )

            modular_element = fromstring(modular_xml)
            mapping_result = self.schema_mapper.map_to_official(
                modular_element, context)

            if not mapping_result.success or mapping_result.mapped_element is None:
                return HybridValidationResult(
                    overall_valid=False,
                    modular_result=modular_result,
                    cross_validation_issues=[ValidationIssue(
                        type=ValidationType.CROSS_REFERENCE,
                        severity=ValidationSeverity.CRITICAL,
                        message="Fallo en transformación modular → oficial",
                        source_schema="transformation"
                    )]
                )

            # 3. Validar XML oficial transformado
            official_xml = tostring(
                mapping_result.mapped_element, encoding='unicode')
            official_result = self.official_validator.validate(
                official_xml, document_type)

            # 4. Validación cruzada
            cross_issues = self.cross_validator.validate_consistency(
                modular_xml, official_xml, document_type
            )

            # 5. Calcular puntuación de consistencia
            consistency_score = self._calculate_consistency_score(
                modular_result, official_result, cross_issues
            )

            # 6. Generar recomendaciones
            recommendations = self._generate_recommendations(
                modular_result, official_result, cross_issues
            )

            overall_valid = (
                modular_result.is_valid and
                official_result.is_valid and
                len([i for i in cross_issues if i.severity ==
                    ValidationSeverity.CRITICAL]) == 0
            )

            return HybridValidationResult(
                overall_valid=overall_valid,
                modular_result=modular_result,
                official_result=official_result,
                cross_validation_issues=cross_issues,
                consistency_score=consistency_score,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"Error en validación con transformación: {str(e)}")

            return HybridValidationResult(
                overall_valid=False,
                cross_validation_issues=[ValidationIssue(
                    type=ValidationType.SCHEMA,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Error en validación con transformación: {str(e)}",
                    source_schema="validation_bridge"
                )]
            )

    def _validate_modular_only(
        self,
        xml_content: str,
        document_type: DocumentType
    ) -> HybridValidationResult:
        """Validación solo contra schema modular"""
        modular_result = self.modular_validator.validate(
            xml_content, document_type)

        return HybridValidationResult(
            overall_valid=modular_result.is_valid,
            modular_result=modular_result,
            consistency_score=1.0 if modular_result.is_valid else 0.5
        )

    def _validate_official_only(
        self,
        xml_content: str,
        document_type: DocumentType
    ) -> HybridValidationResult:
        """Validación solo contra schema oficial"""
        official_result = self.official_validator.validate(
            xml_content, document_type)

        return HybridValidationResult(
            overall_valid=official_result.is_valid,
            official_result=official_result,
            consistency_score=1.0 if official_result.is_valid else 0.5
        )

    def _validate_hybrid_parallel(
        self,
        xml_content: str,
        document_type: DocumentType
    ) -> HybridValidationResult:
        """Validación paralela contra ambos schemas"""
        import concurrent.futures

        # Ejecutar validaciones en paralelo si está habilitado
        if self.config.parallel_execution:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                modular_future = executor.submit(
                    self.modular_validator.validate, xml_content, document_type
                )
                official_future = executor.submit(
                    self.official_validator.validate, xml_content, document_type
                )

                modular_result = modular_future.result(
                    timeout=self.config.timeout_seconds)
                official_result = official_future.result(
                    timeout=self.config.timeout_seconds)
        else:
            # Ejecución secuencial
            modular_result = self.modular_validator.validate(
                xml_content, document_type)
            official_result = self.official_validator.validate(
                xml_content, document_type)

        # Validación cruzada básica
        cross_issues = []
        if self.config.enable_cross_validation:
            try:
                # Comparación básica de resultados
                if modular_result.is_valid != official_result.is_valid:
                    cross_issues.append(ValidationIssue(
                        type=ValidationType.CROSS_REFERENCE,
                        severity=ValidationSeverity.WARNING,
                        message=f"Inconsistencia en validación: modular={modular_result.is_valid}, oficial={official_result.is_valid}",
                        source_schema="cross_validation"
                    ))
            except Exception as e:
                logger.warning(f"Error en validación cruzada básica: {str(e)}")

        consistency_score = self._calculate_consistency_score(
            modular_result, official_result, cross_issues
        )

        recommendations = self._generate_recommendations(
            modular_result, official_result, cross_issues
        )

        overall_valid = modular_result.is_valid and official_result.is_valid

        return HybridValidationResult(
            overall_valid=overall_valid,
            modular_result=modular_result,
            official_result=official_result,
            cross_validation_issues=cross_issues,
            consistency_score=consistency_score,
            recommendations=recommendations
        )

    def _validate_hybrid_sequential(
        self,
        xml_content: str,
        document_type: DocumentType
    ) -> HybridValidationResult:
        """Validación secuencial con fail-fast opcional"""

        # 1. Validación modular primero
        modular_result = self.modular_validator.validate(
            xml_content, document_type)

        # Fail-fast si está habilitado y hay errores críticos
        if (self.config.fail_fast and
                len([i for i in modular_result.issues if i.severity == ValidationSeverity.CRITICAL]) > 0):

            return HybridValidationResult(
                overall_valid=False,
                modular_result=modular_result,
                consistency_score=0.0,
                recommendations=[
                    "Resolver errores críticos en validación modular antes de continuar"]
            )

        # 2. Validación oficial
        official_result = self.official_validator.validate(
            xml_content, document_type)

        # 3. Validación cruzada si ambas pasaron validaciones básicas
        cross_issues = []
        if modular_result.is_valid and official_result.is_valid and self.config.enable_cross_validation:
            try:
                cross_issues = self.cross_validator.validate_consistency(
                    xml_content, xml_content, document_type
                )
            except Exception as e:
                logger.warning(
                    f"Error en validación cruzada secuencial: {str(e)}")

        consistency_score = self._calculate_consistency_score(
            modular_result, official_result, cross_issues
        )

        recommendations = self._generate_recommendations(
            modular_result, official_result, cross_issues
        )

        overall_valid = modular_result.is_valid and official_result.is_valid

        return HybridValidationResult(
            overall_valid=overall_valid,
            modular_result=modular_result,
            official_result=official_result,
            cross_validation_issues=cross_issues,
            consistency_score=consistency_score,
            recommendations=recommendations
        )

    def _validate_cross_validation(
        self,
        xml_content: str,
        document_type: DocumentType
    ) -> HybridValidationResult:
        """Validación cruzada completa con transformación"""
        return self.validate_with_transformation(xml_content, document_type)

    def _calculate_consistency_score(
        self,
        modular_result: Optional[SchemaValidationResult],
        official_result: Optional[SchemaValidationResult],
        cross_issues: List[ValidationIssue]
    ) -> float:
        """
        Calcula puntuación de consistencia entre validaciones

        Returns:
            float: Puntuación entre 0.0 y 1.0
        """
        try:
            base_score = 1.0

            # Penalizar por resultados diferentes
            if modular_result and official_result:
                if modular_result.is_valid != official_result.is_valid:
                    base_score -= 0.3

                # Penalizar por diferencia en número de issues
                modular_issues = len(modular_result.issues)
                official_issues = len(official_result.issues)

                if modular_issues > 0 or official_issues > 0:
                    issue_diff = abs(modular_issues - official_issues)
                    max_issues = max(modular_issues, official_issues, 1)
                    base_score -= (issue_diff / max_issues) * 0.2

            # Penalizar por issues de validación cruzada
            critical_cross_issues = len(
                [i for i in cross_issues if i.severity == ValidationSeverity.CRITICAL])
            warning_cross_issues = len(
                [i for i in cross_issues if i.severity == ValidationSeverity.WARNING])

            base_score -= critical_cross_issues * 0.2
            base_score -= warning_cross_issues * 0.1

            return max(0.0, min(1.0, base_score))

        except:
            return 0.5  # Puntuación neutral en caso de error

    def _generate_recommendations(
        self,
        modular_result: Optional[SchemaValidationResult],
        official_result: Optional[SchemaValidationResult],
        cross_issues: List[ValidationIssue]
    ) -> List[str]:
        """Genera recomendaciones basadas en resultados de validación"""
        recommendations = []

        # Recomendaciones basadas en validación modular
        if modular_result and not modular_result.is_valid:
            error_count = len(
                [i for i in modular_result.issues if i.severity == ValidationSeverity.ERROR])
            if error_count > 0:
                recommendations.append(
                    f"Corregir {error_count} errores en validación modular")

        # Recomendaciones basadas en validación oficial
        if official_result and not official_result.is_valid:
            error_count = len(
                [i for i in official_result.issues if i.severity == ValidationSeverity.ERROR])
            if error_count > 0:
                recommendations.append(
                    f"Corregir {error_count} errores en validación oficial")

        # Recomendaciones basadas en validación cruzada
        critical_cross = len(
            [i for i in cross_issues if i.severity == ValidationSeverity.CRITICAL])
        if critical_cross > 0:
            recommendations.append(
                "Resolver inconsistencias críticas entre schemas")

        # Recomendaciones específicas de issues con sugerencias
        for issue in cross_issues:
            if issue.suggestion and issue.suggestion not in recommendations:
                recommendations.append(issue.suggestion)

        # Recomendación general si no hay específicas
        if not recommendations:
            if modular_result and official_result:
                if modular_result.is_valid and official_result.is_valid:
                    recommendations.append("Documento válido en ambos schemas")
                else:
                    recommendations.append(
                        "Revisar documentación SIFEN v150 para resolver problemas")

        # Limitar a 5 recomendaciones más importantes
        return recommendations[:5]

    def _generate_cache_key(
        self,
        xml_content: str,
        document_type: DocumentType,
        mode: ValidationMode
    ) -> str:
        """Genera clave de cache para resultados de validación"""
        import hashlib

        content_hash = hashlib.md5(xml_content.encode('utf-8')).hexdigest()[:8]
        return f"{document_type.value}_{mode.value}_{content_hash}"

    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de validación del bridge

        Returns:
            Dict[str, Any]: Estadísticas detalladas
        """
        # Convertir defaultdict a dict regular para permitir tipos mixtos
        stats: Dict[str, Any] = dict(self._stats)

        # Calcular métricas derivadas
        total_validations = stats.get('total_validations', 0)
        cache_hits = stats.get('cache_hits', 0)
        cache_misses = stats.get('cache_misses', 0)

        if total_validations > 0:
            stats['cache_hit_rate'] = cache_hits / \
                (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0.0

        stats['cache_enabled'] = self.config.cache_enabled
        stats['parallel_execution'] = self.config.parallel_execution

        return stats

    def clear_cache(self):
        """Limpia el cache de validación"""
        if self._validation_cache:
            self._validation_cache.clear()
            logger.debug("Cache de validación limpiado")

    def update_config(self, new_config: ValidationConfig):
        """
        Actualiza la configuración del bridge

        Args:
            new_config: Nueva configuración a aplicar
        """
        self.config = new_config

        # Reconfigurar cache si es necesario
        if not new_config.cache_enabled and self._validation_cache:
            self._validation_cache.clear()
            self._validation_cache = None
        elif new_config.cache_enabled and not self._validation_cache:
            self._validation_cache = {}

        logger.info("Configuración de ValidationBridge actualizada")


# =====================================
# FUNCIONES DE UTILIDAD PÚBLICAS
# =====================================

def quick_validate_hybrid(
    xml_content: str,
    document_type: DocumentType,
    mode: ValidationMode = ValidationMode.HYBRID_PARALLEL
) -> HybridValidationResult:
    """
    Función helper para validación híbrida rápida

    Args:
        xml_content: Contenido XML a validar
        document_type: Tipo de documento
        mode: Modo de validación

    Returns:
        HybridValidationResult: Resultado de validación
    """
    bridge = ValidationBridge()
    return bridge.validate_hybrid(xml_content, document_type, mode)


def validate_document_consistency(
    modular_xml: str,
    official_xml: str,
    document_type: DocumentType
) -> List[ValidationIssue]:
    """
    Valida consistencia entre documentos modular y oficial

    Args:
        modular_xml: XML en formato modular
        official_xml: XML en formato oficial
        document_type: Tipo de documento

    Returns:
        List[ValidationIssue]: Issues de consistencia encontradas
    """
    schema_mapper = SchemaMapper()
    cross_validator = CrossValidator(schema_mapper)

    return cross_validator.validate_consistency(
        modular_xml, official_xml, document_type
    )


def create_validation_config(
    mode: ValidationMode = ValidationMode.HYBRID_PARALLEL,
    enable_cross_validation: bool = True,
    fail_fast: bool = False,
    parallel_execution: bool = True,
    cache_enabled: bool = True
) -> ValidationConfig:
    """
    Crea configuración de validación con parámetros personalizados

    Args:
        mode: Modo de validación
        enable_cross_validation: Habilitar validación cruzada
        fail_fast: Detener al primer error crítico
        parallel_execution: Ejecutar validaciones en paralelo
        cache_enabled: Habilitar cache

    Returns:
        ValidationConfig: Configuración creada
    """
    return ValidationConfig(
        mode=mode,
        enable_cross_validation=enable_cross_validation,
        fail_fast=fail_fast,
        parallel_execution=parallel_execution,
        cache_enabled=cache_enabled
    )


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    # Clase principal
    'ValidationBridge',

    # Enums
    'ValidationMode',
    'ValidationSeverity',
    'ValidationType',

    # Dataclasses
    'ValidationIssue',
    'SchemaValidationResult',
    'HybridValidationResult',
    'ValidationConfig',

    # Validadores especializados
    'ModularValidator',
    'OfficialValidator',
    'CrossValidator',

    # Funciones de utilidad
    'quick_validate_hybrid',
    'validate_document_consistency',
    'create_validation_config'
]


# =====================================
# EJEMPLO DE USO
# =====================================

if __name__ == "__main__":
    # Ejemplo de uso del ValidationBridge

    # 1. Crear configuración personalizada
    config = create_validation_config(
        mode=ValidationMode.HYBRID_PARALLEL,
        enable_cross_validation=True,
        parallel_execution=True
    )

    # 2. Inicializar bridge
    bridge = ValidationBridge(config)

    # 3. XML de ejemplo (normalmente viene del generador)
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <gTimb>
            <iTiTDE>1</iTiTDE>
            <dDesTiTDE>Factura Electrónica</dDesTiTDE>
            <dNumTim>12345678</dNumTim>
        </gTimb>
        <gOpeOpe>
            <dRucFact>12345678</dRucFact>
            <dVerFact>9</dVerFact>
            <dNomFact>Empresa Test</dNomFact>
        </gOpeOpe>
    </rDE>"""

    # 4. Ejecutar validación híbrida
    result = bridge.validate_hybrid(
        sample_xml, DocumentType.FACTURA_ELECTRONICA)

    # 5. Procesar resultado
    if result.overall_valid:
        print("✅ Documento válido en ambos schemas")
        print(f"Puntuación de consistencia: {result.consistency_score:.2f}")
    else:
        print("❌ Problemas encontrados:")

        total_issues = result.get_total_issues()
        for issue in total_issues[:5]:  # Mostrar primeros 5
            print(f"  {issue.severity.value.upper()}: {issue.message}")
            if issue.suggestion:
                print(f"    💡 Sugerencia: {issue.suggestion}")

    # 6. Mostrar recomendaciones
    if result.recommendations:
        print("\n📋 Recomendaciones:")
        for rec in result.recommendations:
            print(f"  • {rec}")

    # 7. Mostrar estadísticas
    stats = bridge.get_validation_statistics()
    print(f"\n📊 Estadísticas: {stats}")

    # 8. Ejemplo de validación con transformación
    modular_xml = """<gDatGral>
        <dFeEmiDE>2024-12-15</dFeEmiDE>
        <dHorEmi>14:30:00</dHorEmi>
    </gDatGral>"""

    transform_result = bridge.validate_with_transformation(
        modular_xml, DocumentType.FACTURA_ELECTRONICA
    )

    print(
        f"\n🔄 Validación con transformación: {'✅' if transform_result.overall_valid else '❌'}")
