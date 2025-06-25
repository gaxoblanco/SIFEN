"""
Procesadores de Documentos SIFEN v150 - Versión Corregida
========================================================

Este módulo contiene toda la lógica de procesamiento de documentos para
la capa de compatibilidad, incluyendo detección de formatos, transformación,
validación y análisis de compatibilidad.

Responsabilidades:
- Detectar formatos y tipos de documentos
- Verificar compatibilidad inicial
- Coordinar transformaciones entre formatos
- Realizar validaciones SIFEN
- Generar análisis de compatibilidad

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.1 (Corregida)
Fecha: 2025-06-25
"""

from typing import Dict, List, Optional, Union, Any, Protocol, runtime_checkable
import logging
from datetime import datetime
import re

# Manejo específico de importaciones XML con tipos correctos
try:
    from lxml import etree as lxml_etree
    from lxml.etree import _Element as LxmlElement
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
    lxml_etree = None
    LxmlElement = None

# Siempre importar ElementTree estándar como fallback
import xml.etree.ElementTree as et_etree
from xml.etree.ElementTree import Element as ETElement

# Imports locales - asumiendo que estos módulos existen basándome en project knowledge
from ..modular.tests.utils.test_helpers.schema_helpers import ValidationResult
from .xml_transformer import XMLTransformer, TransformationResult
from .validation_bridge import ValidationBridge, ValidationMode
from .schema_mapper import SchemaMapper, DocumentType, MappingDirection, create_mapping_context
from .config import (
    CompatibilityMode, DocumentFormat, IntegrationStatus,
    IntegrationConfig, ProcessingContext, CompatibilityResult
)

# Configuración de logging
logger = logging.getLogger(__name__)


# ================================
# PROTOCOLO PARA DOCUMENTOS BASE
# ================================

@runtime_checkable
class DocumentProtocol(Protocol):
    """
    Protocolo que deben implementar los documentos base

    Define la interfaz mínima que debe tener un documento
    para ser procesado por el sistema.
    """

    def to_xml(self) -> str:
        """Convierte el documento a XML string"""
        ...

    def get_document_type(self) -> str:
        """Retorna el tipo de documento"""
        ...


# ================================
# CLASE BASE PARA DOCUMENTOS
# ================================

class BaseDocument:
    """
    Clase base mejorada para documentos SIFEN

    Proporciona funcionalidad básica para manejo de documentos
    con métodos seguros y validaciones.
    """

    def __init__(self, **kwargs):
        """
        Inicializa documento base con datos proporcionados

        Args:
            **kwargs: Datos del documento
        """
        self._data = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_xml(self) -> str:
        """
        Convierte el documento a representación XML básica

        Returns:
            str: Representación XML del documento
        """
        try:
            # Crear elemento raíz
            root = et_etree.Element("documento")

            # Agregar metadatos
            root.set("tipo", self.get_document_type())
            root.set("timestamp", datetime.now().isoformat())

            # Convertir datos a elementos XML
            self._dict_to_xml_elements(root, self._data)

            return et_etree.tostring(root, encoding='unicode', method='xml')

        except Exception as e:
            logger.error(f"Error convirtiendo documento a XML: {e}")
            return f"<documento><error>{str(e)}</error></documento>"

    def get_document_type(self) -> str:
        """
        Obtiene el tipo de documento

        Returns:
            str: Tipo de documento
        """
        return getattr(self, 'tipo_documento', 'documento_generico')

    def _dict_to_xml_elements(self, parent: ETElement, data: Dict[str, Any]) -> None:
        """
        Convierte diccionario a elementos XML recursivamente

        Args:
            parent: Elemento padre
            data: Datos a convertir
        """
        for key, value in data.items():
            if isinstance(value, dict):
                child = et_etree.SubElement(parent, str(key))
                self._dict_to_xml_elements(child, value)
            elif isinstance(value, list):
                for item in value:
                    child = et_etree.SubElement(parent, str(key))
                    if isinstance(item, dict):
                        self._dict_to_xml_elements(child, item)
                    else:
                        child.text = str(item) if item is not None else ""
            else:
                child = et_etree.SubElement(parent, str(key))
                child.text = str(value) if value is not None else ""


# ================================
# DETECTOR DE DOCUMENTOS
# ================================

class DocumentDetector:
    """
    Detector de formatos y tipos de documentos XML

    Analiza documentos XML para determinar:
    - Formato (modular vs oficial)
    - Tipo de documento (factura, nota crédito, etc.)
    - Características del documento
    """

    @staticmethod
    def detect_document_format(document: Union[BaseDocument, str, Dict[str, Any]]) -> DocumentFormat:
        """
        Detecta el formato de un documento

        Args:
            document: Documento a analizar (objeto, XML string, o dict)

        Returns:
            DocumentFormat: Formato detectado (MODULAR, OFFICIAL, BOTH)
        """
        if isinstance(document, BaseDocument):
            return DocumentFormat.MODULAR

        if isinstance(document, str):
            try:
                # Parsear XML usando lxml si está disponible, sino ElementTree
                if LXML_AVAILABLE and lxml_etree:
                    # Usar bytes para lxml con parser explícito
                    xml_bytes = document.encode(
                        'utf-8') if isinstance(document, str) else document
                    parser = lxml_etree.XMLParser(recover=True)
                    root = lxml_etree.fromstring(xml_bytes, parser)
                    # Obtener namespace usando nsmap de lxml
                    namespace = root.nsmap.get(None, "") if root.nsmap else ""
                else:
                    root = et_etree.fromstring(document)
                    # Obtener namespace del tag para ElementTree estándar
                    namespace = root.tag.split(
                        '}')[0][1:] if root.tag.startswith('{') else ""

                if "sifen" in namespace or "ekuatia.set.gov.py" in namespace:
                    return DocumentFormat.OFFICIAL
                else:
                    return DocumentFormat.MODULAR

            except Exception as e:
                logger.debug(f"Error parseando XML para detectar formato: {e}")
                # No es XML válido o error de parsing, asumir modular
                return DocumentFormat.MODULAR

        if isinstance(document, dict):
            # Detectar estructura de diccionario
            if any(key.startswith('d') and key[1:].isupper() for key in document.keys()):
                return DocumentFormat.OFFICIAL
            else:
                return DocumentFormat.MODULAR

        return DocumentFormat.MODULAR

    @staticmethod
    def detect_document_type(document: Any) -> str:
        """
        Detecta el tipo de documento (factura, nota_crédito, etc.)

        Args:
            document: Documento a analizar

        Returns:
            str: Tipo de documento detectado
        """
        if isinstance(document, BaseDocument):
            return document.get_document_type()

        if isinstance(document, str):
            try:
                # Parsear XML según librería disponible
                if LXML_AVAILABLE and lxml_etree:
                    xml_bytes = document.encode(
                        'utf-8') if isinstance(document, str) else document
                    parser = lxml_etree.XMLParser(recover=True)
                    root = lxml_etree.fromstring(xml_bytes, parser)
                    # Usar xpath si está disponible (lxml)
                    tipo_elements = root.xpath(".//iTiDE")
                    if tipo_elements:
                        tipo_code = tipo_elements[0].text
                        return DocumentDetector._map_tipo_code_to_name(tipo_code)
                else:
                    root = et_etree.fromstring(document)
                    # Usar findall para ElementTree estándar
                    tipo_element = root.find(".//iTiDE")
                    if tipo_element is not None and tipo_element.text:
                        return DocumentDetector._map_tipo_code_to_name(tipo_element.text)

                # Detectar por elemento raíz si no hay iTiDE
                return DocumentDetector._detect_by_root_element(root)

            except Exception as e:
                logger.debug(f"Error detectando tipo de documento: {e}")

        return "documento_generico"

    @staticmethod
    def _map_tipo_code_to_name(tipo_code: str) -> str:
        """Mapea código de tipo a nombre legible"""
        tipo_map = {
            "1": "factura_electronica",
            "4": "autofactura_electronica",
            "5": "nota_credito_electronica",
            "6": "nota_debito_electronica",
            "7": "nota_remision_electronica"
        }
        return tipo_map.get(tipo_code, f"tipo_desconocido_{tipo_code}")

    @staticmethod
    def _detect_by_root_element(root: Union[ETElement, Any]) -> str:
        """
        Detecta tipo por elemento raíz

        Args:
            root: Elemento raíz del XML

        Returns:
            str: Tipo de documento detectado
        """
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag

        if root_tag == "rDE":
            return "documento_electronico_sifen"
        elif "factura" in root_tag.lower():
            return "factura_electronica"
        elif "nota" in root_tag.lower():
            return "nota_electronica"

        return "documento_generico"


# ================================
# VERIFICADOR DE COMPATIBILIDAD
# ================================

class CompatibilityChecker:
    """
    Verificador de compatibilidad inicial de documentos

    Analiza documentos para determinar su estado de compatibilidad
    antes de realizar transformaciones.
    """

    def __init__(self, validation_bridge: ValidationBridge):
        """
        Inicializa el verificador de compatibilidad

        Args:
            validation_bridge: Puente de validación híbrida
        """
        self.validation_bridge = validation_bridge

    def check_initial_compatibility(
        self,
        document: Union[BaseDocument, str, Dict[str, Any]],
        context: Optional[ProcessingContext]
    ) -> CompatibilityResult:
        """
        Verifica compatibilidad inicial del documento

        Args:
            document: Documento a verificar
            context: Contexto de procesamiento

        Returns:
            CompatibilityResult: Resultado de verificación de compatibilidad
        """
        try:
            start_time = datetime.now()

            # Detectar formato del documento
            document_format = DocumentDetector.detect_document_format(document)
            document_type = DocumentDetector.detect_document_type(document)

            logger.debug(
                f"Verificando compatibilidad: formato={document_format.value}, tipo={document_type}")

            # Validar con esquemas modulares si es posible
            modular_valid = False
            modular_errors = []

            if isinstance(document, str):
                try:
                    modular_result = self.validation_bridge.validate_hybrid(
                        document,
                        self._map_document_type(document_type),
                        ValidationMode.MODULAR_ONLY
                    )
                    modular_valid = modular_result.overall_valid
                    if not modular_valid:
                        # Obtener errores de manera segura
                        issues = modular_result.get_total_issues()
                        modular_errors = [
                            issue.message for issue in issues[:5]]
                except Exception as e:
                    logger.debug(f"Error en validación modular: {e}")
                    modular_errors = [f"Error validación modular: {str(e)}"]

            # Intentar validar con esquemas oficiales
            official_valid = False
            official_errors = []

            if isinstance(document, str):
                try:
                    official_result = self.validation_bridge.validate_hybrid(
                        document,
                        self._map_document_type(document_type),
                        ValidationMode.OFFICIAL_ONLY
                    )
                    official_valid = official_result.overall_valid
                    if not official_valid:
                        # Obtener errores de manera segura
                        issues = official_result.get_total_issues()
                        official_errors = [
                            issue.message for issue in issues[:5]]
                except Exception as e:
                    logger.debug(f"Error en validación oficial: {e}")
                    official_errors = [f"Error validación oficial: {str(e)}"]

            # Determinar si se requiere transformación
            needs_transformation = (
                modular_valid and
                not official_valid and
                document_format == DocumentFormat.MODULAR
            )

            # Determinar estado general
            if official_valid:
                status = IntegrationStatus.COMPATIBLE
            elif needs_transformation:
                status = IntegrationStatus.NEEDS_TRANSFORMATION
            elif not modular_valid and not official_valid:
                status = IntegrationStatus.VALIDATION_FAILED
            else:
                status = IntegrationStatus.COMPATIBLE if modular_valid else IntegrationStatus.VALIDATION_FAILED

            # Generar recomendaciones
            recommendations = self._generate_compatibility_recommendations(
                modular_valid, official_valid, needs_transformation, document_format
            )

            # Calcular métricas de performance
            processing_time = (
                datetime.now() - start_time).total_seconds() * 1000

            return CompatibilityResult(
                status=status,
                is_compatible=official_valid or (
                    modular_valid and not needs_transformation),
                modular_valid=modular_valid,
                official_valid=official_valid,
                transformation_required=needs_transformation,
                errors=modular_errors + official_errors,
                warnings=[],
                recommendations=recommendations,
                performance_metrics={
                    "compatibility_check_time": processing_time}
            )

        except Exception as e:
            logger.error(f"Error en verificación de compatibilidad: {e}")
            return CompatibilityResult(
                status=IntegrationStatus.ERROR,
                is_compatible=False,
                modular_valid=False,
                official_valid=False,
                transformation_required=False,
                errors=[f"Error verificando compatibilidad: {str(e)}"],
                warnings=[],
                recommendations=[
                    "Verificar formato y estructura del documento"],
                performance_metrics={}
            )

    def _map_document_type(self, document_type: str) -> DocumentType:
        """Mapea string de tipo a enum DocumentType"""
        type_map = {
            "factura_electronica": DocumentType.FACTURA_ELECTRONICA,
            "autofactura_electronica": DocumentType.AUTOFACTURA_ELECTRONICA,
            "nota_credito_electronica": DocumentType.NOTA_CREDITO_ELECTRONICA,
            "nota_debito_electronica": DocumentType.NOTA_DEBITO_ELECTRONICA,
            "nota_remision_electronica": DocumentType.NOTA_REMISION_ELECTRONICA
        }
        return type_map.get(document_type, DocumentType.FACTURA_ELECTRONICA)

    def _generate_compatibility_recommendations(
        self,
        modular_valid: bool,
        official_valid: bool,
        needs_transformation: bool,
        document_format: DocumentFormat
    ) -> List[str]:
        """Genera recomendaciones basadas en el estado de compatibilidad"""
        recommendations = []

        if not modular_valid and not official_valid:
            recommendations.append(
                "Documento no válido en ningún formato - revisar estructura")
        elif not modular_valid:
            recommendations.append(
                "Documento no válido en formato modular - verificar contra esquemas internos")
        elif not official_valid:
            recommendations.append(
                "Documento no válido en formato oficial - verificar compliance SIFEN")

        if needs_transformation:
            recommendations.append(
                "Documento requiere transformación para envío a SIFEN")

        if document_format == DocumentFormat.MODULAR and official_valid:
            recommendations.append(
                "Documento modular compatible con SIFEN - listo para envío")

        return recommendations


# ================================
# PROCESADOR DE TRANSFORMACIONES
# ================================

class TransformationProcessor:
    """
    Procesador de transformaciones entre formatos modular y oficial

    Coordina las transformaciones usando XMLTransformer y maneja
    los resultados y errores.
    """

    def __init__(self, xml_transformer: XMLTransformer, config: IntegrationConfig):
        """
        Inicializa el procesador de transformaciones

        Args:
            xml_transformer: Transformador XML
            config: Configuración de integración
        """
        self.xml_transformer = xml_transformer
        self.config = config

    def transform_to_official(
        self,
        document: Union[BaseDocument, str, Dict[str, Any]],
        context: ProcessingContext
    ) -> TransformationResult:
        """
        Transforma documento a formato oficial

        Args:
            document: Documento a transformar
            context: Contexto de procesamiento

        Returns:
            TransformationResult: Resultado de la transformación
        """
        try:
            start_time = datetime.now()

            # Convertir documento a string si es necesario
            xml_content = self._prepare_document_for_transformation(document)

            if not xml_content:
                return TransformationResult(
                    success=False,
                    errors=["No se pudo preparar documento para transformación"],
                    warnings=[],
                    metadata={}
                )

            # Mapear tipo de documento
            document_type = self._map_document_type(context.document_type)

            # Ejecutar transformación
            result = self.xml_transformer.transform_to_official(
                xml_content, document_type)

            # Registrar tiempo de transformación si el config lo permite
            if self.config.performance_tracking:
                transform_time = (
                    datetime.now() - start_time).total_seconds() * 1000
                if not hasattr(result, 'performance_metrics'):
                    result.performance_metrics = {}
                result.performance_metrics["transformation_time"] = transform_time

            if self.config.log_transformations:
                logger.info(f"Transformación a oficial: éxito={result.success}, "
                            f"tiempo={result.performance_metrics.get('transformation_time', 0):.2f}ms")

            return result

        except Exception as e:
            logger.error(f"Error en transformación a oficial: {e}")
            return TransformationResult(
                success=False,
                errors=[f"Error durante transformación: {str(e)}"],
                warnings=[],
                metadata={"error_type": "transformation_error"}
            )

    def transform_to_modular(
        self,
        document: Union[BaseDocument, str, Dict[str, Any]],
        context: ProcessingContext
    ) -> TransformationResult:
        """
        Transforma documento a formato modular

        Args:
            document: Documento a transformar
            context: Contexto de procesamiento

        Returns:
            TransformationResult: Resultado de la transformación
        """
        try:
            start_time = datetime.now()

            # Convertir documento a string si es necesario
            xml_content = self._prepare_document_for_transformation(document)

            if not xml_content:
                return TransformationResult(
                    success=False,
                    errors=["No se pudo preparar documento para transformación"],
                    warnings=[],
                    metadata={}
                )

            # Mapear tipo de documento
            document_type = self._map_document_type(context.document_type)

            # Ejecutar transformación
            result = self.xml_transformer.transform_to_modular(
                xml_content, document_type)

            # Registrar tiempo de transformación si el config lo permite
            if self.config.performance_tracking:
                transform_time = (
                    datetime.now() - start_time).total_seconds() * 1000
                if not hasattr(result, 'performance_metrics'):
                    result.performance_metrics = {}
                result.performance_metrics["transformation_time"] = transform_time

            if self.config.log_transformations:
                logger.info(f"Transformación a modular: éxito={result.success}, "
                            f"tiempo={result.performance_metrics.get('transformation_time', 0):.2f}ms")

            return result

        except Exception as e:
            logger.error(f"Error en transformación a modular: {e}")
            return TransformationResult(
                success=False,
                errors=[f"Error durante transformación: {str(e)}"],
                warnings=[],
                metadata={"error_type": "transformation_error"}
            )

    def _prepare_document_for_transformation(self, document: Union[BaseDocument, str, Dict[str, Any]]) -> Optional[str]:
        """
        Prepara documento para transformación

        Args:
            document: Documento a preparar

        Returns:
            Contenido XML como string o None si no se puede preparar
        """
        if isinstance(document, str):
            return document
        elif isinstance(document, BaseDocument):
            # Usar el método to_xml() de la clase base
            return document.to_xml()
        elif isinstance(document, dict):
            # Convertir dict a XML básico
            return self._dict_to_xml(document)
        else:
            logger.error(f"Tipo de documento no soportado: {type(document)}")
            return None

    def _dict_to_xml(self, data: Dict[str, Any]) -> str:
        """
        Convierte diccionario a XML básico

        Args:
            data: Diccionario a convertir

        Returns:
            XML string
        """
        try:
            root = et_etree.Element("documento")

            def add_elements(parent, data_dict):
                for key, value in data_dict.items():
                    if isinstance(value, dict):
                        child = et_etree.SubElement(parent, key)
                        add_elements(child, value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                child = et_etree.SubElement(parent, key)
                                add_elements(child, item)
                            else:
                                child = et_etree.SubElement(parent, key)
                                child.text = str(item)
                    else:
                        child = et_etree.SubElement(parent, key)
                        child.text = str(value)

            add_elements(root, data)
            return et_etree.tostring(root, encoding='unicode')

        except Exception as e:
            logger.error(f"Error convirtiendo dict a XML: {e}")
            return ""

    def _map_document_type(self, document_type: str) -> DocumentType:
        """Mapea string de tipo a enum DocumentType"""
        type_map = {
            "factura_electronica": DocumentType.FACTURA_ELECTRONICA,
            "autofactura_electronica": DocumentType.AUTOFACTURA_ELECTRONICA,
            "nota_credito_electronica": DocumentType.NOTA_CREDITO_ELECTRONICA,
            "nota_debito_electronica": DocumentType.NOTA_DEBITO_ELECTRONICA,
            "nota_remision_electronica": DocumentType.NOTA_REMISION_ELECTRONICA
        }
        return type_map.get(document_type, DocumentType.FACTURA_ELECTRONICA)


# ================================
# PROCESADOR DE VALIDACIÓN
# ================================

class ValidationProcessor:
    """
    Procesador de validaciones SIFEN

    Coordina las validaciones usando ValidationBridge y proporciona
    resultados unificados.
    """

    def __init__(self, validation_bridge: ValidationBridge, config: IntegrationConfig):
        """
        Inicializa el procesador de validación

        Args:
            validation_bridge: Puente de validación
            config: Configuración de integración
        """
        self.validation_bridge = validation_bridge
        self.config = config

    def validate_for_sifen(
        self,
        document: Union[str, BaseDocument, Dict[str, Any]],
        context: ProcessingContext
    ) -> ValidationResult:
        """
        Valida documento para envío a SIFEN

        Args:
            document: Documento a validar
            context: Contexto de procesamiento

        Returns:
            ValidationResult: Resultado de validación
        """
        try:
            start_time = datetime.now()

            # Preparar documento para validación
            xml_content = self._prepare_document_for_validation(document)

            if not xml_content:
                return ValidationResult(
                    is_valid=False,
                    errors=["No se pudo preparar documento para validación"],
                    warnings=[],
                    module="validation_processor"
                )

            # Mapear tipo de documento
            document_type = self._map_document_type(context.document_type)

            # Determinar modo de validación según configuración
            validation_mode = self._determine_validation_mode(context.mode)

            # Ejecutar validación
            result = self.validation_bridge.validate_hybrid(
                xml_content, document_type, validation_mode
            )

            # Convertir resultado híbrido a ValidationResult
            validation_result = self._convert_hybrid_to_validation_result(
                result)

            # Registrar tiempo de validación si el config lo permite
            if self.config.performance_tracking:
                validation_time = (
                    datetime.now() - start_time).total_seconds() * 1000
                # Agregar tiempo como atributo personalizado
                setattr(validation_result, 'validation_time', validation_time)

            logger.debug(
                f"Validación SIFEN completada: válido={validation_result.is_valid}")

            return validation_result

        except Exception as e:
            logger.error(f"Error en validación SIFEN: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Error durante validación: {str(e)}"],
                warnings=[],
                module="validation_processor"
            )

    def _prepare_document_for_validation(self, document: Union[str, BaseDocument, Dict[str, Any]]) -> Optional[str]:
        """
        Prepara documento para validación

        Args:
            document: Documento a preparar

        Returns:
            Contenido XML como string o None
        """
        if isinstance(document, str):
            return document
        elif isinstance(document, BaseDocument):
            return document.to_xml()
        elif isinstance(document, dict):
            # Convertir dict a XML básico para validación
            try:
                import json
                # Crear XML simple desde dict
                root = et_etree.Element("documento")
                root.text = json.dumps(document)
                return et_etree.tostring(root, encoding='unicode')
            except Exception as e:
                logger.error(f"Error convirtiendo dict para validación: {e}")
                return None
        else:
            logger.error(
                f"Tipo de documento no soportado para validación: {type(document)}")
            return None

    def _determine_validation_mode(self, compatibility_mode: CompatibilityMode) -> ValidationMode:
        """Determina modo de validación según configuración"""
        if compatibility_mode == CompatibilityMode.DEVELOPMENT:
            return ValidationMode.MODULAR_ONLY
        elif compatibility_mode == CompatibilityMode.PRODUCTION:
            return ValidationMode.OFFICIAL_ONLY
        elif compatibility_mode == CompatibilityMode.TESTING:
            return ValidationMode.HYBRID_PARALLEL
        else:  # HYBRID
            return ValidationMode.HYBRID_PARALLEL

    def _convert_hybrid_to_validation_result(self, hybrid_result) -> ValidationResult:
        """
        Convierte resultado híbrido a ValidationResult estándar

        Args:
            hybrid_result: Resultado de validación híbrida

        Returns:
            ValidationResult: Resultado convertido
        """
        all_errors = []
        all_warnings = []

        # Recopilar errores y warnings de todos los resultados de manera segura
        try:
            issues = hybrid_result.get_total_issues()
            for issue in issues:
                if hasattr(issue, 'severity') and hasattr(issue.severity, 'value'):
                    if issue.severity.value in ['error', 'critical']:
                        all_errors.append(issue.message)
                    else:
                        all_warnings.append(issue.message)
                else:
                    # Fallback si no tiene estructura esperada
                    all_errors.append(str(issue))
        except Exception as e:
            logger.warning(f"Error procesando issues de validación: {e}")
            all_errors.append("Error procesando resultados de validación")

        return ValidationResult(
            is_valid=hybrid_result.overall_valid,
            errors=all_errors,
            warnings=all_warnings,
            module="validation_bridge"
        )

    def _map_document_type(self, document_type: str) -> DocumentType:
        """Mapea string de tipo a enum DocumentType"""
        type_map = {
            "factura_electronica": DocumentType.FACTURA_ELECTRONICA,
            "autofactura_electronica": DocumentType.AUTOFACTURA_ELECTRONICA,
            "nota_credito_electronica": DocumentType.NOTA_CREDITO_ELECTRONICA,
            "nota_debito_electronica": DocumentType.NOTA_DEBITO_ELECTRONICA,
            "nota_remision_electronica": DocumentType.NOTA_REMISION_ELECTRONICA
        }
        return type_map.get(document_type, DocumentType.FACTURA_ELECTRONICA)


# ================================
# ANALIZADOR DE COMPATIBILIDAD
# ================================

class CompatibilityAnalyzer:
    """
    Analizador de compatibilidad de documentos

    Proporciona análisis detallado de compatibilidad y recomendaciones
    para resolver problemas.
    """

    def __init__(self, validation_bridge: ValidationBridge):
        """
        Inicializa el analizador de compatibilidad

        Args:
            validation_bridge: Puente de validación híbrida
        """
        self.validation_bridge = validation_bridge

    def analyze_compatibility(
        self,
        document: Union[BaseDocument, str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analiza la compatibilidad de un documento con detalle

        Args:
            document: Documento a analizar

        Returns:
            Dict con análisis detallado de compatibilidad
        """
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "document_format": DocumentDetector.detect_document_format(document).value,
            "document_type": DocumentDetector.detect_document_type(document),
            "modular_analysis": {},
            "official_analysis": {},
            "integration_analysis": {},
            "recommendations": []
        }

        try:
            # Preparar documento para análisis
            xml_content = self._prepare_document_for_analysis(document)

            if not xml_content:
                analysis["error"] = "No se pudo preparar documento para análisis"
                return analysis

            # Mapear tipo de documento
            document_type = self._map_document_type(analysis["document_type"])

            # Análisis modular
            try:
                modular_result = self.validation_bridge.validate_hybrid(
                    xml_content, document_type, ValidationMode.MODULAR_ONLY
                )

                # Extraer errores y warnings de manera segura
                modular_errors = []
                modular_warnings = []

                try:
                    issues = modular_result.get_total_issues()
                    for issue in issues:
                        if hasattr(issue, 'severity') and hasattr(issue.severity, 'value'):
                            if issue.severity.value in ['error', 'critical']:
                                modular_errors.append(issue.message)
                            elif issue.severity.value == 'warning':
                                modular_warnings.append(issue.message)
                        else:
                            modular_errors.append(str(issue))
                except Exception as e:
                    logger.warning(f"Error extrayendo issues modulares: {e}")
                    modular_errors.append(
                        "Error procesando issues de validación")

                analysis["modular_analysis"] = {
                    "valid": modular_result.overall_valid,
                    "errors": modular_errors,
                    "warnings": modular_warnings,
                    "consistency_score": getattr(modular_result, 'consistency_score', 0.0)
                }

            except Exception as e:
                logger.error(f"Error en análisis modular: {e}")
                analysis["modular_analysis"] = {
                    "valid": False,
                    "errors": [f"Error ejecutando análisis modular: {str(e)}"],
                    "warnings": [],
                    "consistency_score": 0.0
                }

            # Análisis oficial
            try:
                official_result = self.validation_bridge.validate_hybrid(
                    xml_content, document_type, ValidationMode.OFFICIAL_ONLY
                )

                # Extraer errores y warnings de manera segura
                official_errors = []
                official_warnings = []

                try:
                    issues = official_result.get_total_issues()
                    for issue in issues:
                        if hasattr(issue, 'severity') and hasattr(issue.severity, 'value'):
                            if issue.severity.value in ['error', 'critical']:
                                official_errors.append(issue.message)
                            elif issue.severity.value == 'warning':
                                official_warnings.append(issue.message)
                        else:
                            official_errors.append(str(issue))
                except Exception as e:
                    logger.warning(f"Error extrayendo issues oficiales: {e}")
                    official_errors.append(
                        "Error procesando issues de validación")

                analysis["official_analysis"] = {
                    "valid": official_result.overall_valid,
                    "errors": official_errors,
                    "warnings": official_warnings,
                    "sifen_compliance": official_result.overall_valid
                }

            except Exception as e:
                logger.error(f"Error en análisis oficial: {e}")
                analysis["official_analysis"] = {
                    "valid": False,
                    "errors": [f"Error ejecutando análisis oficial: {str(e)}"],
                    "warnings": [],
                    "sifen_compliance": False
                }

            # Análisis de integración
            modular_valid = analysis["modular_analysis"].get("valid", False)
            official_valid = analysis["official_analysis"].get("valid", False)
            needs_transformation = modular_valid and not official_valid

            analysis["integration_analysis"] = {
                "transformation_required": needs_transformation,
                "both_schemas_valid": modular_valid and official_valid,
                "compatibility_score": self._calculate_compatibility_score(
                    analysis["modular_analysis"], analysis["official_analysis"]
                )
            }

            # Generar recomendaciones
            analysis["recommendations"] = self._generate_detailed_recommendations(
                analysis["modular_analysis"],
                analysis["official_analysis"],
                needs_transformation
            )

        except Exception as e:
            logger.error(f"Error en análisis de compatibilidad: {e}")
            analysis["error"] = str(e)

        return analysis

    def _prepare_document_for_analysis(self, document: Union[BaseDocument, str, Dict[str, Any]]) -> Optional[str]:
        """
        Prepara documento para análisis

        Args:
            document: Documento a preparar

        Returns:
            Contenido XML como string o None
        """
        if isinstance(document, str):
            return document
        elif isinstance(document, BaseDocument):
            return document.to_xml()
        elif isinstance(document, dict):
            # Análisis básico de estructura
            return f"<analysis_dict>{len(document)} keys</analysis_dict>"
        else:
            return None

    def _calculate_compatibility_score(self, modular_analysis: Dict[str, Any], official_analysis: Dict[str, Any]) -> float:
        """
        Calcula score de compatibilidad entre 0.0 y 1.0

        Args:
            modular_analysis: Resultado de análisis modular
            official_analysis: Resultado de análisis oficial

        Returns:
            Score de compatibilidad
        """
        score = 0.0

        if modular_analysis.get("valid", False):
            score += 0.4
        if official_analysis.get("valid", False):
            score += 0.6

        # Penalizar por número de errores
        total_errors = len(modular_analysis.get("errors", [])) + \
            len(official_analysis.get("errors", []))
        if total_errors > 0:
            # Máximo 30% de penalización
            penalty = min(0.3, total_errors * 0.05)
            score -= penalty

        return max(0.0, min(1.0, score))

    def _generate_detailed_recommendations(
        self,
        modular_analysis: Dict[str, Any],
        official_analysis: Dict[str, Any],
        needs_transformation: bool
    ) -> List[str]:
        """
        Genera recomendaciones detalladas basadas en análisis

        Args:
            modular_analysis: Análisis modular
            official_analysis: Análisis oficial
            needs_transformation: Si requiere transformación

        Returns:
            Lista de recomendaciones
        """
        recommendations = []

        # Recomendaciones basadas en validación modular
        if not modular_analysis.get("valid", False):
            modular_errors = len(modular_analysis.get("errors", []))
            recommendations.append(
                f"Corregir {modular_errors} problemas en esquema modular")

        # Recomendaciones basadas en validación oficial
        if not official_analysis.get("valid", False):
            official_errors = len(official_analysis.get("errors", []))
            recommendations.append(
                f"Corregir {official_errors} problemas en esquema oficial SIFEN")

        # Recomendaciones sobre transformación
        if needs_transformation:
            recommendations.append(
                "Aplicar transformación modular → oficial antes del envío a SIFEN")
        elif modular_analysis.get("valid", False) and official_analysis.get("valid", False):
            recommendations.append(
                "Documento compatible con ambos esquemas - listo para envío")

        # Recomendaciones específicas
        if not modular_analysis.get("valid", False) and not official_analysis.get("valid", False):
            recommendations.append(
                "Revisar estructura fundamental del documento")

        # Recomendación general si no hay específicas
        if not recommendations:
            recommendations.append(
                "Documento analizado - revisar detalles específicos")

        return recommendations[:5]  # Limitar a 5 recomendaciones

    def _map_document_type(self, document_type: str) -> DocumentType:
        """Mapea string de tipo a enum DocumentType"""
        type_map = {
            "factura_electronica": DocumentType.FACTURA_ELECTRONICA,
            "autofactura_electronica": DocumentType.AUTOFACTURA_ELECTRONICA,
            "nota_credito_electronica": DocumentType.NOTA_CREDITO_ELECTRONICA,
            "nota_debito_electronica": DocumentType.NOTA_DEBITO_ELECTRONICA,
            "nota_remision_electronica": DocumentType.NOTA_REMISION_ELECTRONICA
        }
        return type_map.get(document_type, DocumentType.FACTURA_ELECTRONICA)


# ================================
# COORDINADOR PRINCIPAL
# ================================

class DocumentProcessor:
    """
    Coordinador principal de procesamiento de documentos

    Orquesta todos los procesadores especializados para proporcionar
    una interfaz unificada de procesamiento.
    """

    def __init__(
        self,
        schema_mapper: SchemaMapper,
        validation_bridge: ValidationBridge,
        xml_transformer: XMLTransformer,
        config: IntegrationConfig
    ):
        """
        Inicializa el procesador de documentos

        Args:
            schema_mapper: Mapeador de esquemas
            validation_bridge: Puente de validación
            xml_transformer: Transformador XML
            config: Configuración de integración
        """
        self.config = config

        # Inicializar procesadores especializados
        self.compatibility_checker = CompatibilityChecker(validation_bridge)
        self.transformation_processor = TransformationProcessor(
            xml_transformer, config)
        self.validation_processor = ValidationProcessor(
            validation_bridge, config)
        self.compatibility_analyzer = CompatibilityAnalyzer(validation_bridge)

        # Métricas de performance
        self._performance_metrics = {
            "documents_processed": 0,
            "successful_transformations": 0,
            "failed_transformations": 0,
            "successful_validations": 0,
            "failed_validations": 0
        }

        logger.info("DocumentProcessor inicializado")

    def process_document_for_sifen(
        self,
        document: Union[BaseDocument, str, Dict[str, Any]],
        context: ProcessingContext
    ) -> CompatibilityResult:
        """
        Procesa un documento completo para envío a SIFEN

        Args:
            document: Documento a procesar
            context: Contexto de procesamiento

        Returns:
            CompatibilityResult: Resultado completo del procesamiento
        """
        start_time = datetime.now()

        try:
            logger.info(
                f"Procesando documento para SIFEN: tipo={context.document_type}")

            # 1. Verificar compatibilidad inicial
            compatibility_result = self.compatibility_checker.check_initial_compatibility(
                document, context)

            if not compatibility_result.is_compatible and not self.config.auto_transform:
                self._update_metrics("failed_validations")
                return compatibility_result

            # 2. Transformar si es necesario
            final_document = document
            transformation_result = None

            if compatibility_result.transformation_required or context.source_format == DocumentFormat.MODULAR:
                transformation_result = self.transformation_processor.transform_to_official(
                    document, context)

                if transformation_result.success:
                    final_document = transformation_result.transformed_xml
                    self._update_metrics("successful_transformations")
                else:
                    self._update_metrics("failed_transformations")
                    return CompatibilityResult(
                        status=IntegrationStatus.ERROR,
                        is_compatible=False,
                        modular_valid=compatibility_result.modular_valid,
                        official_valid=False,
                        transformation_required=True,
                        errors=transformation_result.errors,
                        warnings=transformation_result.warnings,
                        recommendations=[
                            "Revisar estructura del documento para transformación"],
                        performance_metrics=self._calculate_final_metrics(
                            start_time)
                    )

            # 3. Validar documento final
            context_for_validation = ProcessingContext(
                document_type=context.document_type,
                source_format=DocumentFormat.OFFICIAL,
                target_format=DocumentFormat.OFFICIAL,
                mode=context.mode,
                timestamp=datetime.now(),
                request_id=context.request_id
            )

            validation_result = self.validation_processor.validate_for_sifen(
                final_document, context_for_validation)

            if validation_result.is_valid:
                self._update_metrics("successful_validations")
            else:
                self._update_metrics("failed_validations")

            # 4. Construir resultado final
            final_result = CompatibilityResult(
                status=IntegrationStatus.COMPATIBLE if validation_result.is_valid else IntegrationStatus.VALIDATION_FAILED,
                is_compatible=validation_result.is_valid,
                modular_valid=compatibility_result.modular_valid,
                official_valid=validation_result.is_valid,
                transformation_required=transformation_result is not None,
                errors=validation_result.errors,
                warnings=validation_result.warnings + compatibility_result.warnings,
                recommendations=self._generate_final_recommendations(
                    compatibility_result, transformation_result, validation_result
                ),
                performance_metrics=self._calculate_final_metrics(start_time)
            )

            # Adjuntar XML final si está disponible
            if isinstance(final_document, str):
                setattr(final_result, 'final_xml', final_document)

            self._update_metrics("documents_processed")

            if self.config.log_transformations:
                logger.info(f"Procesamiento completado: éxito={final_result.is_compatible}, "
                            f"tiempo={final_result.performance_metrics.get('total_time', 0):.2f}ms")

            return final_result

        except Exception as e:
            logger.error(f"Error procesando documento para SIFEN: {e}")
            return CompatibilityResult(
                status=IntegrationStatus.ERROR,
                is_compatible=False,
                modular_valid=False,
                official_valid=False,
                transformation_required=False,
                errors=[f"Error crítico durante procesamiento: {str(e)}"],
                warnings=[],
                recommendations=["Contactar soporte técnico"],
                performance_metrics=self._calculate_final_metrics(start_time)
            )

    def analyze_document_compatibility(
        self,
        document: Union[BaseDocument, str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analiza la compatibilidad de un documento

        Args:
            document: Documento a analizar

        Returns:
            Dict: Análisis detallado de compatibilidad
        """
        return self.compatibility_analyzer.analyze_compatibility(document)

    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de procesamiento

        Returns:
            Dict: Estadísticas detalladas
        """
        total_processed = self._performance_metrics["documents_processed"]

        # Copiar métricas básicas
        stats: Dict[str, Any] = dict(self._performance_metrics)

        if total_processed > 0:
            # Calcular tasas de éxito como float y almacenar en Dict[str, Any]
            transformation_success_rate = (
                self._performance_metrics["successful_transformations"] /
                max(1, self._performance_metrics["successful_transformations"] +
                    self._performance_metrics["failed_transformations"])
            ) * 100

            validation_success_rate = (
                self._performance_metrics["successful_validations"] /
                max(1, self._performance_metrics["successful_validations"] +
                    self._performance_metrics["failed_validations"])
            ) * 100

            # Asignar valores float a dict con type Any
            stats["transformation_success_rate"] = transformation_success_rate
            stats["validation_success_rate"] = validation_success_rate

        return stats

    def reset_statistics(self):
        """Reinicia las estadísticas de procesamiento"""
        for key in self._performance_metrics:
            self._performance_metrics[key] = 0
        logger.debug("Estadísticas de procesamiento reiniciadas")

    def _update_metrics(self, metric: str):
        """Actualiza métricas de performance"""
        if metric in self._performance_metrics:
            self._performance_metrics[metric] += 1

    def _calculate_final_metrics(self, start_time: datetime) -> Dict[str, float]:
        """Calcula métricas finales de performance"""
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        return {
            "total_time": total_time,
            "processing_timestamp": start_time.timestamp()
        }

    def _generate_final_recommendations(
        self,
        compatibility_result: CompatibilityResult,
        transformation_result: Optional[TransformationResult],
        validation_result: ValidationResult
    ) -> List[str]:
        """Genera recomendaciones finales basadas en todos los resultados"""
        recommendations = []

        # Incluir recomendaciones de compatibilidad
        recommendations.extend(compatibility_result.recommendations[:2])

        # Recomendaciones basadas en transformación
        if transformation_result and not transformation_result.success:
            recommendations.append("Resolver errores de transformación")
        elif transformation_result and transformation_result.success:
            recommendations.append(
                "Transformación exitosa - documento listo para SIFEN")

        # Recomendaciones basadas en validación final
        if not validation_result.is_valid:
            recommendations.append(
                "Corregir errores de validación antes del envío")
        elif validation_result.is_valid:
            recommendations.append(
                "Documento válido - proceder con envío a SIFEN")

        # Limitar y filtrar duplicados
        unique_recommendations = list(dict.fromkeys(recommendations))
        return unique_recommendations[:5]


# ================================
# FUNCIONES DE UTILIDAD
# ================================

def create_document_processor(
    schema_mapper: SchemaMapper,
    validation_bridge: ValidationBridge,
    xml_transformer: XMLTransformer,
    config: IntegrationConfig
) -> DocumentProcessor:
    """
    Factory function para crear DocumentProcessor

    Args:
        schema_mapper: Instancia del schema mapper
        validation_bridge: Instancia del validation bridge
        xml_transformer: Instancia del XML transformer
        config: Configuración de integración

    Returns:
        DocumentProcessor: Procesador configurado
    """
    return DocumentProcessor(schema_mapper, validation_bridge, xml_transformer, config)


def quick_compatibility_check(
    document: Union[BaseDocument, str, Dict[str, Any]],
    validation_bridge: ValidationBridge
) -> bool:
    """
    Verificación rápida de compatibilidad

    Args:
        document: Documento a verificar
        validation_bridge: Bridge de validación

    Returns:
        bool: True si es compatible
    """
    try:
        checker = CompatibilityChecker(validation_bridge)
        result = checker.check_initial_compatibility(document, None)
        return result.is_compatible
    except Exception as e:
        logger.error(f"Error en verificación rápida: {e}")
        return False


def detect_document_info(document: Union[BaseDocument, str, Dict[str, Any]]) -> Dict[str, str]:
    """
    Detecta información básica del documento

    Args:
        document: Documento a analizar

    Returns:
        Dict: Información detectada (formato, tipo)
    """
    return {
        "format": DocumentDetector.detect_document_format(document).value,
        "type": DocumentDetector.detect_document_type(document)
    }


# ================================
# EXPORTS PÚBLICOS
# ================================

__all__ = [
    # Clases principales
    'DocumentProcessor',
    'DocumentDetector',
    'CompatibilityChecker',
    'TransformationProcessor',
    'ValidationProcessor',
    'CompatibilityAnalyzer',

    # Clase base y protocolo
    'BaseDocument',
    'DocumentProtocol',

    # Funciones de utilidad
    'create_document_processor',
    'quick_compatibility_check',
    'detect_document_info'
]


# ================================
# EJEMPLO DE USO
# ================================

if __name__ == "__main__":
    print("🔧 Procesadores SIFEN v150 - Versión Corregida")
    print("=" * 50)

    # 1. Detectar información de documento
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
        <gTimb><iTiDE>1</iTiDE></gTimb>
    </rDE>"""

    doc_info = detect_document_info(sample_xml)
    print(f"📄 Información del documento: {doc_info}")

    # 2. Crear documento base de ejemplo
    sample_doc = BaseDocument(
        tipo_documento="factura_electronica",
        numero="001-001-0000001",
        fecha="2025-06-25"
    )

    print(f"📋 Documento base creado: {sample_doc.get_document_type()}")
    print(f"🔍 XML generado: {len(sample_doc.to_xml())} caracteres")

    # 3. Verificar detección de formato
    print(
        f"🔍 Formato detectado (XML): {DocumentDetector.detect_document_format(sample_xml).value}")
    print(
        f"🔍 Formato detectado (Objeto): {DocumentDetector.detect_document_format(sample_doc).value}")

    print("\n🚀 Procesadores corregidos y listos para integración")
    print("✅ Type hints corregidos")
    print("✅ Manejo de errores mejorado")
    print("✅ Métodos seguros implementados")
    print("✅ Protocolo DocumentProtocol añadido")
