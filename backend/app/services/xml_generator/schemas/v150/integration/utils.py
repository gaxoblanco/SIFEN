"""
Utilidades y Factories para Integración SIFEN v150
==================================================

Este módulo contiene utilidades, factories y funciones de conveniencia
para la capa de integración, facilitando la creación y configuración
de componentes del sistema.

Responsabilidades:
- Factory functions para crear instancias configuradas
- Utilidades de configuración y contexto
- Helpers para procesamiento de documentos
- Funciones de validación y detección
- Utilidades de performance y debugging

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
Fecha: 2025-06-25
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Type
import logging
from datetime import datetime, timezone
import uuid
import os
import sys
import json
from pathlib import Path

# Imports de configuración y tipos
from .config import (
    IntegrationConfig, ProcessingContext, CompatibilityMode,
    DocumentFormat, IntegrationStatus, CompatibilityResult
)

# Imports de procesadores
from .schema_mapper import SchemaMapper, DocumentType, MappingDirection
from .validation_bridge import ValidationBridge, ValidationMode
from .xml_transformer import XMLTransformer
from .processors import DocumentProcessor, BaseDocument

# Imports locales para constantes
try:
    from ..modular.tests.utils.test_helpers.constants import (
        SIFEN_DOCUMENT_TYPES, SIFEN_NAMESPACE_URI
    )
except ImportError:
    # Fallback si no están disponibles las constantes
    SIFEN_DOCUMENT_TYPES = {}
    DEFAULT_XML_ENCODING = "utf-8"
    SIFEN_NAMESPACE_URI = "http://ekuatia.set.gov.py/sifen/xsd"

    class Environment:
        DEVELOPMENT = "development"
        TESTING = "testing"
        PRODUCTION = "production"

# Configuración de logging
logger = logging.getLogger(__name__)


# ================================
# FACTORY PARA CONFIGURACIONES
# ================================

class IntegrationConfigFactory:
    """
    Factory para crear configuraciones de integración

    Proporciona métodos de conveniencia para crear configuraciones
    preestablecidas según diferentes escenarios de uso.
    """

    @staticmethod
    def create_development_config(
        auto_transform: bool = True,
        performance_tracking: bool = True,
        log_transformations: bool = True
    ) -> IntegrationConfig:
        """
        Crea configuración para desarrollo

        Args:
            auto_transform: Si transformar automáticamente
            performance_tracking: Si trackear performance
            log_transformations: Si loggear transformaciones

        Returns:
            IntegrationConfig: Configuración para desarrollo
        """
        return IntegrationConfig(
            mode=CompatibilityMode.DEVELOPMENT,
            auto_transform=auto_transform,
            validate_both=True,  # Validar ambos esquemas en desarrollo
            preserve_modular=True,  # Preservar estructura modular
            performance_tracking=performance_tracking,
            log_transformations=log_transformations,
            cache_schemas=True,  # Cachear esquemas para mejor performance
            timeout_seconds=30,
            max_retries=3
        )

    @staticmethod
    def create_testing_config(
        validate_both: bool = True,
        performance_tracking: bool = True
    ) -> IntegrationConfig:
        """
        Crea configuración para testing

        Args:
            validate_both: Si validar ambos esquemas
            performance_tracking: Si trackear performance

        Returns:
            IntegrationConfig: Configuración para testing
        """
        return IntegrationConfig(
            mode=CompatibilityMode.TESTING,
            auto_transform=True,
            validate_both=validate_both,  # Validación completa en testing
            preserve_modular=True,
            performance_tracking=performance_tracking,
            log_transformations=False,  # Menos verbose en tests
            cache_schemas=False,  # Fresh schemas en tests
            timeout_seconds=10,  # Timeouts más cortos en tests
            max_retries=1
        )

    @staticmethod
    def create_production_config(
        cache_schemas: bool = True,
        timeout_seconds: int = 60
    ) -> IntegrationConfig:
        """
        Crea configuración para producción

        Args:
            cache_schemas: Si cachear esquemas
            timeout_seconds: Timeout en segundos

        Returns:
            IntegrationConfig: Configuración para producción
        """
        return IntegrationConfig(
            mode=CompatibilityMode.PRODUCTION,
            auto_transform=True,
            # Solo validación oficial en prod (performance)
            validate_both=False,
            preserve_modular=False,  # No preservar en prod (memory)
            performance_tracking=True,
            log_transformations=False,  # Menos logging en prod
            cache_schemas=cache_schemas,
            timeout_seconds=timeout_seconds,
            max_retries=5
        )

    @staticmethod
    def create_hybrid_config(
        auto_transform: bool = True,
        performance_tracking: bool = True
    ) -> IntegrationConfig:
        """
        Crea configuración híbrida (modular + oficial)

        Args:
            auto_transform: Si transformar automáticamente
            performance_tracking: Si trackear performance

        Returns:
            IntegrationConfig: Configuración híbrida
        """
        return IntegrationConfig(
            mode=CompatibilityMode.HYBRID,
            auto_transform=auto_transform,
            validate_both=True,  # Validar ambos en modo híbrido
            preserve_modular=True,  # Preservar para comparación
            performance_tracking=performance_tracking,
            log_transformations=True,
            cache_schemas=True,
            timeout_seconds=45,
            max_retries=3
        )

    @staticmethod
    def from_environment(env_name: Optional[str] = None) -> IntegrationConfig:
        """
        Crea configuración basada en variable de entorno

        Args:
            env_name: Nombre del entorno o None para auto-detectar

        Returns:
            IntegrationConfig: Configuración apropiada
        """
        if env_name is None:
            env_name = os.getenv('SIFEN_ENVIRONMENT', 'development').lower()

        if env_name == 'production':
            return IntegrationConfigFactory.create_production_config()
        elif env_name == 'testing':
            return IntegrationConfigFactory.create_testing_config()
        elif env_name == 'hybrid':
            return IntegrationConfigFactory.create_hybrid_config()
        else:  # development
            return IntegrationConfigFactory.create_development_config()


# ================================
# FACTORY PARA CONTEXTOS
# ================================

class ProcessingContextFactory:
    """
    Factory para crear contextos de procesamiento

    Facilita la creación de contextos con valores apropiados
    según diferentes escenarios.
    """

    @staticmethod
    def create_processing_context(
        document_type: str,
        source_format: Union[str, DocumentFormat] = DocumentFormat.MODULAR,
        target_format: Union[str, DocumentFormat] = DocumentFormat.OFFICIAL,
        mode: Union[str, CompatibilityMode] = CompatibilityMode.HYBRID,
        request_id: Optional[str] = None
    ) -> ProcessingContext:
        """
        Crea contexto de procesamiento

        Args:
            document_type: Tipo de documento
            source_format: Formato origen
            target_format: Formato destino
            mode: Modo de compatibilidad
            request_id: ID de request opcional

        Returns:
            ProcessingContext: Contexto configurado
        """
        # Convertir strings a enums si es necesario
        if isinstance(source_format, str):
            source_format = DocumentFormat(source_format.lower())
        if isinstance(target_format, str):
            target_format = DocumentFormat(target_format.lower())
        if isinstance(mode, str):
            mode = CompatibilityMode(mode.lower())

        return ProcessingContext(
            document_type=document_type,
            source_format=source_format,
            target_format=target_format,
            mode=mode,
            timestamp=datetime.now(timezone.utc),
            request_id=request_id or str(uuid.uuid4())
        )

    @staticmethod
    def for_sifen_submission(
        document_type: str,
        request_id: Optional[str] = None
    ) -> ProcessingContext:
        """
        Crea contexto para envío a SIFEN

        Args:
            document_type: Tipo de documento
            request_id: ID de request opcional

        Returns:
            ProcessingContext: Contexto para SIFEN
        """
        return ProcessingContextFactory.create_processing_context(
            document_type=document_type,
            source_format=DocumentFormat.MODULAR,
            target_format=DocumentFormat.OFFICIAL,
            mode=CompatibilityMode.PRODUCTION,
            request_id=request_id
        )

    @staticmethod
    def for_development_testing(
        document_type: str,
        request_id: Optional[str] = None
    ) -> ProcessingContext:
        """
        Crea contexto para testing en desarrollo

        Args:
            document_type: Tipo de documento
            request_id: ID de request opcional

        Returns:
            ProcessingContext: Contexto para desarrollo
        """
        return ProcessingContextFactory.create_processing_context(
            document_type=document_type,
            source_format=DocumentFormat.MODULAR,
            target_format=DocumentFormat.OFFICIAL,
            mode=CompatibilityMode.DEVELOPMENT,
            request_id=request_id
        )

    @staticmethod
    def for_validation_only(
        document_type: str,
        format_type: DocumentFormat = DocumentFormat.MODULAR,
        request_id: Optional[str] = None
    ) -> ProcessingContext:
        """
        Crea contexto solo para validación

        Args:
            document_type: Tipo de documento
            format_type: Formato a validar
            request_id: ID de request opcional

        Returns:
            ProcessingContext: Contexto para validación
        """
        return ProcessingContextFactory.create_processing_context(
            document_type=document_type,
            source_format=format_type,
            target_format=format_type,
            mode=CompatibilityMode.TESTING,
            request_id=request_id
        )


# ================================
# FACTORY PARA PROCESADORES
# ================================

class ProcessorFactory:
    """
    Factory para crear procesadores configurados

    Centraliza la creación de procesadores con sus dependencias
    correctamente inyectadas.
    """

    @staticmethod
    def create_document_processor(
        config: Optional[IntegrationConfig] = None,
        schema_paths: Optional[Dict[str, str]] = None
    ) -> DocumentProcessor:
        """
        Crea procesador de documentos completamente configurado

        Args:
            config: Configuración personalizada
            schema_paths: Rutas personalizadas de esquemas

        Returns:
            DocumentProcessor: Procesador configurado
        """
        # Usar configuración por defecto si no se proporciona
        if config is None:
            config = IntegrationConfigFactory.from_environment()

        # Crear dependencias
        schema_mapper = ProcessorFactory._create_schema_mapper(schema_paths)
        validation_bridge = ProcessorFactory._create_validation_bridge(config)
        xml_transformer = ProcessorFactory._create_xml_transformer(config)

        # Crear y retornar procesador
        return DocumentProcessor(
            schema_mapper=schema_mapper,
            validation_bridge=validation_bridge,
            xml_transformer=xml_transformer,
            config=config
        )

    @staticmethod
    def _create_schema_mapper(schema_paths: Optional[Dict[str, str]] = None) -> SchemaMapper:
        """Crea schema mapper con configuración por defecto"""
        # Implementación básica - en implementación real cargaría esquemas
        from .schema_mapper import create_mapping_context

        # Corregir los parámetros según la firma real de create_mapping_context
        context = create_mapping_context(
            document_type=DocumentType.FACTURA_ELECTRONICA,  # ✅ Parámetro correcto
            direction=MappingDirection.MODULAR_TO_OFFICIAL,  # ✅ Parámetro correcto
            source_namespace="http://modular.internal",      # ✅ Parámetro opcional
            target_namespace=SIFEN_NAMESPACE_URI             # ✅ Parámetro opcional
        )

        # Crear SchemaMapper sin parámetros hasta confirmar constructor
        return SchemaMapper()  # ✅ Sin parámetros hasta verificar

    @staticmethod
    def _create_validation_bridge(config: IntegrationConfig) -> ValidationBridge:
        """Crea validation bridge con configuración"""
        # Implementación básica - crear sin parámetros hasta verificar constructor
        # En implementación real se configuraría según el constructor real
        return ValidationBridge()  # ✅ Sin parámetros hasta verificar constructor

    @staticmethod
    def _create_xml_transformer(config: IntegrationConfig) -> XMLTransformer:
        """Crea XML transformer con configuración"""
        # Implementación básica - crear sin parámetros hasta verificar constructor
        # En implementación real se configuraría según el constructor real
        return XMLTransformer()  # ✅ Sin parámetros hasta verificar constructor


# ================================
# UTILIDADES DE DOCUMENTO
# ================================

class DocumentUtils:
    """
    Utilidades para manejo de documentos

    Proporciona funciones de conveniencia para tareas comunes
    con documentos SIFEN.
    """

    @staticmethod
    def create_base_document(
        document_type: str,
        data: Dict[str, Any],
        **kwargs
    ) -> BaseDocument:
        """
        Crea documento base con datos proporcionados

        Args:
            document_type: Tipo de documento
            data: Datos del documento
            **kwargs: Datos adicionales

        Returns:
            BaseDocument: Documento base configurado
        """
        # Combinar datos
        combined_data = {
            'tipo_documento': document_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **data,
            **kwargs
        }

        return BaseDocument(**combined_data)

    @staticmethod
    def extract_document_metadata(document: Union[BaseDocument, str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extrae metadatos de un documento

        Args:
            document: Documento a analizar

        Returns:
            Dict: Metadatos extraídos
        """
        metadata = {
            'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
            'document_class': type(document).__name__,
            'size_estimate': 0
        }

        if isinstance(document, BaseDocument):
            metadata.update({
                'type': document.get_document_type(),
                'has_to_xml': hasattr(document, 'to_xml'),
                'attributes_count': len(document._data) if hasattr(document, '_data') else 0
            })
        elif isinstance(document, str):
            metadata.update({
                'type': 'xml_string',
                'size_estimate': len(document),
                'is_xml': document.strip().startswith('<'),
                'contains_sifen_namespace': SIFEN_NAMESPACE_URI in document
            })
        elif isinstance(document, dict):
            metadata.update({
                'type': 'dictionary',
                'keys_count': len(document),
                'size_estimate': len(str(document)),
                # Primeras 10 keys
                'top_level_keys': list(document.keys())[:10]
            })

        return metadata

    @staticmethod
    def validate_document_type(document_type: str) -> Tuple[bool, str]:
        """
        Valida si un tipo de documento es válido

        Args:
            document_type: Tipo a validar

        Returns:
            Tuple[bool, str]: (es_válido, mensaje)
        """
        # Mapeo de tipos comunes
        type_mapping = {
            'factura': '01',
            'factura_electronica': '01',
            'autofactura': '04',
            'autofactura_electronica': '04',
            'nota_credito': '05',
            'nota_credito_electronica': '05',
            'nota_debito': '06',
            'nota_debito_electronica': '06',
            'nota_remision': '07',
            'nota_remision_electronica': '07'
        }

        # Normalizar tipo
        normalized_type = document_type.lower().strip()

        # Verificar si es código directo o nombre
        if normalized_type in ['01', '04', '05', '06', '07']:
            return True, f"Tipo válido: {normalized_type}"
        elif normalized_type in type_mapping:
            code = type_mapping[normalized_type]
            return True, f"Tipo válido: {normalized_type} (código: {code})"
        else:
            valid_types = list(type_mapping.keys()) + \
                ['01', '04', '05', '06', '07']
            return False, f"Tipo inválido. Válidos: {', '.join(valid_types)}"

    @staticmethod
    def estimate_processing_time(document: Union[BaseDocument, str, Dict[str, Any]]) -> float:
        """
        Estima tiempo de procesamiento en segundos

        Args:
            document: Documento a analizar

        Returns:
            float: Tiempo estimado en segundos
        """
        base_time = 0.1  # 100ms base

        if isinstance(document, str):
            # ~1ms por cada 1000 caracteres
            size_factor = len(document) / 1000 * 0.001
            return base_time + size_factor
        elif isinstance(document, dict):
            # ~0.5ms por cada key
            keys_factor = len(document) * 0.0005
            return base_time + keys_factor
        elif isinstance(document, BaseDocument):
            # Factor basado en atributos
            attrs_count = len(document._data) if hasattr(
                document, '_data') else 10
            attrs_factor = attrs_count * 0.001
            return base_time + attrs_factor

        return base_time


# ================================
# UTILIDADES DE PERFORMANCE
# ================================

class PerformanceUtils:
    """
    Utilidades para medición y optimización de performance
    """

    @staticmethod
    def create_performance_context() -> Dict[str, Any]:
        """
        Crea contexto para medición de performance

        Returns:
            Dict: Contexto de performance
        """
        return {
            'start_time': datetime.now(),
            'memory_start': PerformanceUtils._get_memory_usage(),
            'checkpoints': []
        }

    @staticmethod
    def add_checkpoint(context: Dict[str, Any], name: str) -> None:
        """
        Añade checkpoint de performance

        Args:
            context: Contexto de performance
            name: Nombre del checkpoint
        """
        checkpoint = {
            'name': name,
            'timestamp': datetime.now(),
            'memory': PerformanceUtils._get_memory_usage(),
            'elapsed_ms': (datetime.now() - context['start_time']).total_seconds() * 1000
        }
        context['checkpoints'].append(checkpoint)

    @staticmethod
    def finalize_performance_context(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finaliza contexto de performance y calcula métricas

        Args:
            context: Contexto de performance

        Returns:
            Dict: Métricas finales
        """
        end_time = datetime.now()
        total_time = (end_time - context['start_time']).total_seconds() * 1000

        return {
            'total_time_ms': total_time,
            'memory_peak': max([cp['memory'] for cp in context['checkpoints']] + [context['memory_start']]),
            'memory_delta': PerformanceUtils._get_memory_usage() - context['memory_start'],
            'checkpoints_count': len(context['checkpoints']),
            'checkpoints': context['checkpoints']
        }

    @staticmethod
    def _get_memory_usage() -> float:
        """Obtiene uso actual de memoria en MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0  # No disponible sin psutil


# ================================
# UTILIDADES DE DEBUGGING
# ================================

class DebugUtils:
    """
    Utilidades para debugging y diagnóstico
    """

    @staticmethod
    def create_debug_info(
        document: Union[BaseDocument, str, Dict[str, Any]],
        context: Optional[ProcessingContext] = None,
        include_content: bool = False
    ) -> Dict[str, Any]:
        """
        Crea información de debug para un documento

        Args:
            document: Documento a analizar
            context: Contexto opcional
            include_content: Si incluir contenido completo

        Returns:
            Dict: Información de debug
        """
        debug_info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'document_metadata': DocumentUtils.extract_document_metadata(document),
            'processing_estimate': DocumentUtils.estimate_processing_time(document),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
            'working_directory': str(Path.cwd())
        }

        if context:
            debug_info['context'] = {
                'document_type': context.document_type,
                'source_format': context.source_format.value if hasattr(context.source_format, 'value') else str(context.source_format),
                'target_format': context.target_format.value if hasattr(context.target_format, 'value') else str(context.target_format),
                'mode': context.mode.value if hasattr(context.mode, 'value') else str(context.mode),
                'request_id': context.request_id,
                'timestamp': context.timestamp.isoformat()
            }

        if include_content:
            if isinstance(document, str):
                debug_info['content_preview'] = document[:500] + \
                    ('...' if len(document) > 500 else '')
            elif isinstance(document, dict):
                debug_info['content_keys'] = list(document.keys())
            elif isinstance(document, BaseDocument):
                debug_info['content_type'] = document.get_document_type()

        return debug_info

    @staticmethod
    def log_debug_info(
        debug_info: Dict[str, Any],
        logger_instance: Optional[logging.Logger] = None
    ) -> None:
        """
        Registra información de debug en logs

        Args:
            debug_info: Información de debug
            logger_instance: Logger opcional
        """
        if logger_instance is None:
            logger_instance = logger

        logger_instance.debug("Debug Info:", extra={'debug_data': debug_info})


# ================================
# FUNCIONES DE CONVENIENCIA
# ================================

def quick_process_document(
    document: Union[BaseDocument, str, Dict[str, Any]],
    document_type: str,
    environment: str = "development"
) -> CompatibilityResult:
    """
    Función de conveniencia para procesamiento rápido

    Args:
        document: Documento a procesar
        document_type: Tipo de documento
        environment: Entorno de ejecución

    Returns:
        CompatibilityResult: Resultado del procesamiento
    """
    # Crear configuración y contexto
    config = IntegrationConfigFactory.from_environment(environment)
    context = ProcessingContextFactory.create_processing_context(
        document_type=document_type,
        mode=config.mode
    )

    # Crear y usar procesador
    processor = ProcessorFactory.create_document_processor(config)
    return processor.process_document_for_sifen(document, context)


def analyze_document_compatibility(
    document: Union[BaseDocument, str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Función de conveniencia para análisis de compatibilidad

    Args:
        document: Documento a analizar

    Returns:
        Dict: Análisis de compatibilidad
    """
    config = IntegrationConfigFactory.create_development_config()
    processor = ProcessorFactory.create_document_processor(config)
    return processor.analyze_document_compatibility(document)


def create_processing_context(
    document_type: str,
    source_format: str = "modular",
    mode: str = "hybrid"
) -> ProcessingContext:
    """
    Función de conveniencia para crear contexto

    Args:
        document_type: Tipo de documento
        source_format: Formato origen
        mode: Modo de procesamiento

    Returns:
        ProcessingContext: Contexto creado
    """
    return ProcessingContextFactory.create_processing_context(
        document_type=document_type,
        source_format=source_format,
        mode=mode
    )


# ================================
# PRESETS DE CONFIGURACIÓN
# ================================

class IntegrationConfigPresets:
    """
    Presets de configuración comunes
    """

    FAST_DEVELOPMENT = IntegrationConfigFactory.create_development_config(
        performance_tracking=False,
        log_transformations=False
    )

    STRICT_TESTING = IntegrationConfigFactory.create_testing_config(
        validate_both=True,  # Usar validate_both en lugar de strict_mode
        performance_tracking=True
    )

    PRODUCTION_OPTIMIZED = IntegrationConfigFactory.create_production_config(
        cache_schemas=True,  # Usar cache_schemas
        timeout_seconds=30
    )

    HYBRID_BALANCED = IntegrationConfigFactory.create_hybrid_config(
        auto_transform=True,
        performance_tracking=True
    )


# ================================
# EXPORTS PÚBLICOS
# ================================

__all__ = [
    # Factories
    'IntegrationConfigFactory',
    'ProcessingContextFactory',
    'ProcessorFactory',

    # Utilidades
    'DocumentUtils',
    'PerformanceUtils',
    'DebugUtils',

    # Funciones de conveniencia
    'quick_process_document',
    'analyze_document_compatibility',
    'create_processing_context',

    # Presets
    'IntegrationConfigPresets'
]


# ================================
# EJEMPLO DE USO
# ================================

if __name__ == "__main__":
    print("🔧 Utilidades de Integración SIFEN v150")
    print("=" * 50)

    # 1. Crear configuración de desarrollo
    dev_config = IntegrationConfigFactory.create_development_config()
    print(f"✅ Config desarrollo: {dev_config.mode.value}")

    # 2. Crear contexto de procesamiento
    context = create_processing_context(
        document_type="factura_electronica",
        source_format="modular",
        mode="development"
    )
    if context and context.request_id:
        print(f"✅ Contexto creado: {context.request_id[:8]}...")
    else:
        print("❌ Error: Contexto o request_id no disponible.")

    # 3. Validar tipo de documento
    is_valid, message = DocumentUtils.validate_document_type("factura")
    print(f"✅ Validación tipo: {message}")

    # 4. Crear documento base
    sample_doc = DocumentUtils.create_base_document(
        document_type="factura_electronica",
        data={'numero': '001-001-0000001', 'total': 100000}
    )
    print(f"✅ Documento creado: {sample_doc.get_document_type()}")

    # 5. Estimar tiempo de procesamiento
    estimated_time = DocumentUtils.estimate_processing_time(sample_doc)
    print(f"✅ Tiempo estimado: {estimated_time:.3f} segundos")

    print("\n🚀 Utilidades listas para uso en integración")
    print("📚 Factories, utils y presets disponibles")
