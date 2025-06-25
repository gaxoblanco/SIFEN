"""
Configuraciones de Integración SIFEN v150
=========================================

Este módulo centraliza todas las configuraciones, enums y modelos de datos
para la capa de compatibilidad entre schemas modulares y oficiales.

Responsabilidades:
- Definir enums para modos y estados de integración
- Proporcionar dataclasses para configuración y contexto
- Centralizar constantes de integración
- Definir modelos de resultado y respuesta

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
Fecha: 2025-06-25
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


# ================================
# ENUMS DE CONFIGURACIÓN
# ================================

class CompatibilityMode(Enum):
    """Modos de operación de la capa de compatibilidad"""
    DEVELOPMENT = "development"      # Usa schemas modulares para desarrollo
    TESTING = "testing"             # Valida ambos: modular + oficial
    PRODUCTION = "production"       # Usa solo schemas oficiales para SIFEN
    HYBRID = "hybrid"               # Inteligente: modular en dev, oficial en prod


class DocumentFormat(Enum):
    """Formatos de documento soportados"""
    MODULAR = "modular"            # Formato interno modular
    OFFICIAL = "official"          # Formato oficial SIFEN
    BOTH = "both"                  # Ambos formatos


class IntegrationStatus(Enum):
    """Estados de integración"""
    COMPATIBLE = "compatible"       # Totalmente compatible
    NEEDS_TRANSFORMATION = "needs_transformation"  # Requiere transformación
    VALIDATION_FAILED = "validation_failed"        # Falla validación
    ERROR = "error"                # Error crítico


# ================================
# MODELOS DE CONFIGURACIÓN
# ================================

@dataclass
class IntegrationConfig:
    """
    Configuración de la capa de integración

    Attributes:
        mode: Modo de compatibilidad (development, testing, production, hybrid)
        auto_transform: Transformar automáticamente cuando sea necesario
        validate_both: Validar contra ambos schemas (modular y oficial)
        preserve_modular: Mantener estructura modular como referencia
        log_transformations: Registrar transformaciones en logs
        performance_tracking: Habilitar tracking de métricas de performance
        cache_schemas: Habilitar cache de schemas XSD
        max_retries: Número máximo de reintentos en operaciones
        timeout_seconds: Timeout en segundos para operaciones
    """
    mode: CompatibilityMode
    auto_transform: bool = True
    validate_both: bool = True
    preserve_modular: bool = True
    log_transformations: bool = True
    performance_tracking: bool = True
    cache_schemas: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30


@dataclass
class ProcessingContext:
    """
    Contexto de procesamiento de documentos

    Attributes:
        document_type: Tipo de documento siendo procesado
        source_format: Formato del documento de entrada
        target_format: Formato del documento de salida
        mode: Modo de compatibilidad para esta operación
        timestamp: Momento de inicio del procesamiento
        request_id: Identificador único de la petición (opcional)
        user_context: Contexto adicional del usuario (opcional)
    """
    document_type: str
    source_format: DocumentFormat
    target_format: DocumentFormat
    mode: CompatibilityMode
    timestamp: datetime
    request_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None


# ================================
# MODELOS DE RESULTADO
# ================================

@dataclass
class CompatibilityResult:
    """
    Resultado de verificación de compatibilidad

    Attributes:
        status: Estado de la verificación de compatibilidad
        is_compatible: Indica si el documento es compatible
        modular_valid: Resultado de validación modular
        official_valid: Resultado de validación oficial
        transformation_required: Indica si se requiere transformación
        errors: Lista de errores encontrados
        warnings: Lista de advertencias
        recommendations: Lista de recomendaciones para resolver problemas
        performance_metrics: Métricas de tiempo de ejecución
    """
    status: IntegrationStatus
    is_compatible: bool
    modular_valid: bool
    official_valid: bool
    transformation_required: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]
    performance_metrics: Dict[str, float]


# ================================
# CONFIGURACIONES AVANZADAS
# ================================

@dataclass
class PerformanceConfig:
    """
    Configuración específica para optimización de performance

    Attributes:
        enable_parallel_validation: Ejecutar validaciones en paralelo
        cache_size_limit: Límite de tamaño del cache en MB
        batch_processing_size: Tamaño de lotes para procesamiento masivo
        memory_optimization: Habilitar optimizaciones de memoria
        lazy_loading: Cargar schemas solo cuando se necesiten
    """
    enable_parallel_validation: bool = True
    cache_size_limit: int = 100  # MB
    batch_processing_size: int = 50
    memory_optimization: bool = True
    lazy_loading: bool = True


@dataclass
class ValidationConfig:
    """
    Configuración específica para validación

    Attributes:
        strict_mode: Modo estricto de validación
        skip_warnings: Omitir advertencias en resultados
        validate_namespaces: Validar namespaces XML
        validate_encoding: Validar codificación de caracteres
        custom_rules: Reglas de validación personalizadas
    """
    strict_mode: bool = True
    skip_warnings: bool = False
    validate_namespaces: bool = True
    validate_encoding: bool = True
    custom_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityConfig:
    """
    Configuración de seguridad para procesamiento

    Attributes:
        validate_signatures: Validar firmas digitales
        check_certificates: Verificar certificados
        sanitize_input: Sanitizar entrada XML
        max_xml_size: Tamaño máximo de XML en bytes
        allowed_schemas: Lista de schemas XSD permitidos
    """
    validate_signatures: bool = True
    check_certificates: bool = True
    sanitize_input: bool = True
    max_xml_size: int = 10_000_000  # 10MB
    allowed_schemas: List[str] = field(default_factory=list)


# ================================
# CONFIGURACIONES PREDEFINIDAS
# ================================

class IntegrationConfigPresets:
    """
    Configuraciones predefinidas para diferentes escenarios
    """

    @staticmethod
    def development() -> IntegrationConfig:
        """Configuración optimizada para desarrollo"""
        return IntegrationConfig(
            mode=CompatibilityMode.DEVELOPMENT,
            auto_transform=True,
            validate_both=True,
            preserve_modular=True,
            log_transformations=True,
            performance_tracking=True,
            cache_schemas=False,  # Sin cache para ver cambios inmediatos
            max_retries=3,
            timeout_seconds=60
        )

    @staticmethod
    def testing() -> IntegrationConfig:
        """Configuración optimizada para testing automatizado"""
        return IntegrationConfig(
            mode=CompatibilityMode.TESTING,
            auto_transform=True,
            validate_both=True,
            preserve_modular=True,
            log_transformations=False,  # Logs mínimos en tests
            performance_tracking=True,
            cache_schemas=True,
            max_retries=1,
            timeout_seconds=30
        )

    @staticmethod
    def production() -> IntegrationConfig:
        """Configuración optimizada para producción"""
        return IntegrationConfig(
            mode=CompatibilityMode.PRODUCTION,
            auto_transform=False,  # Control manual en producción
            validate_both=False,   # Solo validación oficial
            preserve_modular=False,  # Optimizar memoria
            log_transformations=False,  # Sin logging para performance
            performance_tracking=False,  # Sin tracking para performance
            cache_schemas=True,
            max_retries=1,
            timeout_seconds=10
        )

    @staticmethod
    def hybrid() -> IntegrationConfig:
        """Configuración híbrida inteligente"""
        return IntegrationConfig(
            mode=CompatibilityMode.HYBRID,
            auto_transform=True,
            validate_both=True,
            preserve_modular=True,
            log_transformations=True,
            performance_tracking=True,
            cache_schemas=True,
            max_retries=2,
            timeout_seconds=30
        )

    @staticmethod
    def high_performance() -> IntegrationConfig:
        """Configuración optimizada para alto rendimiento"""
        return IntegrationConfig(
            mode=CompatibilityMode.PRODUCTION,
            auto_transform=False,
            validate_both=False,
            preserve_modular=False,
            log_transformations=False,
            performance_tracking=True,  # Solo para optimización
            cache_schemas=True,
            max_retries=1,
            timeout_seconds=5
        )


# ================================
# CONFIGURACIONES COMPUESTAS
# ================================

@dataclass
class AdvancedIntegrationConfig:
    """
    Configuración avanzada que combina todos los aspectos

    Attributes:
        integration: Configuración básica de integración
        performance: Configuración de performance
        validation: Configuración de validación
        security: Configuración de seguridad
        custom_settings: Configuraciones personalizadas adicionales
    """
    integration: IntegrationConfig
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_preset(cls, preset: str) -> 'AdvancedIntegrationConfig':
        """
        Crea configuración avanzada desde un preset

        Args:
            preset: Nombre del preset ('development', 'testing', 'production', etc.)

        Returns:
            AdvancedIntegrationConfig: Configuración avanzada
        """
        preset_map = {
            'development': IntegrationConfigPresets.development(),
            'testing': IntegrationConfigPresets.testing(),
            'production': IntegrationConfigPresets.production(),
            'hybrid': IntegrationConfigPresets.hybrid(),
            'high_performance': IntegrationConfigPresets.high_performance()
        }

        base_config = preset_map.get(preset, IntegrationConfigPresets.hybrid())

        return cls(
            integration=base_config,
            performance=PerformanceConfig(),
            validation=ValidationConfig(),
            security=SecurityConfig()
        )


# ================================
# CONSTANTES DE CONFIGURACIÓN
# ================================

class IntegrationConstants:
    """Constantes para la integración"""

    # Timeouts por defecto
    DEFAULT_TIMEOUT = 30
    FAST_TIMEOUT = 5
    SLOW_TIMEOUT = 60

    # Límites de memoria
    DEFAULT_CACHE_SIZE_MB = 100
    MAX_XML_SIZE_MB = 10
    MAX_BATCH_SIZE = 50

    # Códigos de error
    ERROR_VALIDATION_FAILED = "VALIDATION_FAILED"
    ERROR_TRANSFORMATION_FAILED = "TRANSFORMATION_FAILED"
    ERROR_COMPATIBILITY_FAILED = "COMPATIBILITY_FAILED"
    ERROR_TIMEOUT = "TIMEOUT_ERROR"
    ERROR_MEMORY_LIMIT = "MEMORY_LIMIT_EXCEEDED"

    # Métricas de performance
    PERFORMANCE_METRICS = [
        "validation_time",
        "transformation_time",
        "total_processing_time",
        "cache_hit_rate",
        "memory_usage"
    ]

    # Formatos soportados
    SUPPORTED_XML_ENCODINGS = ["utf-8", "utf-16", "latin1"]
    SUPPORTED_NAMESPACES = [
        "http://ekuatia.set.gov.py/sifen/xsd",
        "http://modular.sifen.local/xsd"
    ]


# ================================
# UTILIDADES DE CONFIGURACIÓN
# ================================

def create_integration_config(
    mode: str = "hybrid",
    auto_transform: bool = True,
    validate_both: bool = True,
    **kwargs
) -> IntegrationConfig:
    """
    Función helper para crear configuración de integración

    Args:
        mode: Modo de compatibilidad
        auto_transform: Habilitar transformación automática
        validate_both: Validar contra ambos schemas
        **kwargs: Configuraciones adicionales

    Returns:
        IntegrationConfig: Configuración creada
    """
    mode_enum = CompatibilityMode(mode.lower())

    config = IntegrationConfig(
        mode=mode_enum,
        auto_transform=auto_transform,
        validate_both=validate_both
    )

    # Aplicar configuraciones adicionales
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return config


def create_processing_context(
    document_type: str,
    source_format: str = "modular",
    target_format: str = "official",
    mode: str = "hybrid",
    **kwargs
) -> ProcessingContext:
    """
    Función helper para crear contexto de procesamiento

    Args:
        document_type: Tipo de documento
        source_format: Formato de origen
        target_format: Formato de destino
        mode: Modo de compatibilidad
        **kwargs: Contexto adicional

    Returns:
        ProcessingContext: Contexto creado
    """
    return ProcessingContext(
        document_type=document_type,
        source_format=DocumentFormat(source_format.lower()),
        target_format=DocumentFormat(target_format.lower()),
        mode=CompatibilityMode(mode.lower()),
        timestamp=datetime.now(),
        **kwargs
    )


def validate_config(config: IntegrationConfig) -> List[str]:
    """
    Valida una configuración de integración

    Args:
        config: Configuración a validar

    Returns:
        List[str]: Lista de errores encontrados (vacía si es válida)
    """
    errors = []

    # Validar timeouts
    if config.timeout_seconds <= 0:
        errors.append("timeout_seconds debe ser mayor a 0")

    if config.timeout_seconds > 300:  # 5 minutos max
        errors.append("timeout_seconds no debe exceder 300 segundos")

    # Validar retries
    if config.max_retries < 0:
        errors.append("max_retries no puede ser negativo")

    if config.max_retries > 10:
        errors.append("max_retries no debería exceder 10")

    # Validaciones lógicas
    if config.mode == CompatibilityMode.PRODUCTION and config.validate_both:
        errors.append("En modo PRODUCTION no se recomienda validate_both=True")

    if config.mode == CompatibilityMode.DEVELOPMENT and not config.log_transformations:
        errors.append(
            "En modo DEVELOPMENT se recomienda log_transformations=True")

    return errors


# ================================
# EXPORTS PÚBLICOS
# ================================

__all__ = [
    # Enums
    'CompatibilityMode',
    'DocumentFormat',
    'IntegrationStatus',

    # Modelos de configuración
    'IntegrationConfig',
    'ProcessingContext',
    'CompatibilityResult',

    # Configuraciones avanzadas
    'PerformanceConfig',
    'ValidationConfig',
    'SecurityConfig',
    'AdvancedIntegrationConfig',

    # Presets
    'IntegrationConfigPresets',

    # Constantes
    'IntegrationConstants',

    # Utilidades
    'create_integration_config',
    'create_processing_context',
    'validate_config'
]


# ================================
# EJEMPLO DE USO
# ================================

if __name__ == "__main__":
    # Ejemplos de uso de las configuraciones

    print("🚀 Ejemplos de Configuraciones SIFEN v150")
    print("=" * 50)

    # 1. Configuración básica para desarrollo
    dev_config = IntegrationConfigPresets.development()
    print(f"📝 Configuración desarrollo: {dev_config}")

    # 2. Configuración avanzada desde preset
    advanced_config = AdvancedIntegrationConfig.from_preset('production')
    print(f"⚙️  Configuración avanzada: {advanced_config.integration.mode}")

    # 3. Configuración personalizada
    custom_config = create_integration_config(
        mode="hybrid",
        auto_transform=True,
        timeout_seconds=45
    )
    print(f"🎛️  Configuración personalizada: {custom_config}")

    # 4. Contexto de procesamiento
    context = create_processing_context(
        document_type="factura_electronica",
        source_format="modular",
        target_format="official",
        request_id="REQ_001"
    )
    print(f"📋 Contexto de procesamiento: {context.document_type}")

    # 5. Validación de configuración
    errors = validate_config(custom_config)
    if errors:
        print(f"❌ Errores de configuración: {errors}")
    else:
        print("✅ Configuración válida")

    # 6. Constantes disponibles
    print(f"⏱️  Timeout por defecto: {IntegrationConstants.DEFAULT_TIMEOUT}s")
    print(
        f"📊 Métricas disponibles: {len(IntegrationConstants.PERFORMANCE_METRICS)}")

    print("\n🎯 Configuraciones listas para usar en CompatibilityLayer")
