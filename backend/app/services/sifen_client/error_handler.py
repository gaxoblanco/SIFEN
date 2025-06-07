"""
Manejador de errores SIFEN Paraguay

Mapea códigos de error oficiales de SIFEN a mensajes user-friendly
y proporciona recomendaciones de solución para cada tipo de error.

Funcionalidades:
- Mapeo completo de códigos según Manual Técnico v150
- Mensajes en español adaptados al contexto paraguayo
- Recomendaciones específicas de solución
- Categorización por tipo de error (datos, sistema, certificados)
- Logging estructurado para análisis de errores

Basado en:
- Manual Técnico SIFEN v150
- Códigos de error oficiales SET Paraguay
- Experiencia con errores comunes en producción
"""

from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import structlog

# Módulos internos
from .models import SifenResponse, DocumentStatus
from .exceptions import SifenClientError, create_sifen_error_from_response

# Logger para el manejador de errores
logger = structlog.get_logger(__name__)


class ErrorCategory(str, Enum):
    """
    Categorías de errores SIFEN para mejor organización
    """
    SUCCESS = "success"                    # Códigos exitosos
    VALIDATION = "validation"              # Errores de validación de datos
    AUTHENTICATION = "authentication"     # Errores de certificados/firma
    BUSINESS_RULES = "business_rules"     # Errores de reglas de negocio
    SYSTEM = "system"                     # Errores del sistema SIFEN
    NETWORK = "network"                   # Errores de conectividad
    UNKNOWN = "unknown"                   # Errores no categorizados


class ErrorSeverity(str, Enum):
    """
    Severidad de los errores para priorización
    """
    INFO = "info"                         # Información (códigos exitosos)
    WARNING = "warning"                   # Advertencias (con observaciones)
    ERROR = "error"                       # Errores recuperables
    CRITICAL = "critical"                 # Errores críticos del sistema


@dataclass
class ErrorInfo:
    """
    Información detallada de un error SIFEN
    """
    code: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    recommendations: List[str]
    is_retryable: bool
    requires_user_action: bool
    technical_details: Optional[str] = None


class SifenErrorHandler:
    """
    Manejador principal de errores SIFEN

    Centraliza el mapeo de códigos de error a información
    estructurada y mensajes user-friendly.
    """

    def __init__(self):
        """Inicializa el manejador con el catálogo completo de errores"""

        # Catálogo completo de errores SIFEN según Manual Técnico v150
        self.error_catalog: Dict[str, ErrorInfo] = {

            # ========================================
            # CÓDIGOS EXITOSOS (0xxx)
            # ========================================

            "0260": ErrorInfo(
                code="0260",
                category=ErrorCategory.SUCCESS,
                severity=ErrorSeverity.INFO,
                message="Documento electrónico aprobado",
                user_message="✅ Su documento ha sido aprobado por SIFEN exitosamente",
                recommendations=[
                    "El documento está listo para uso comercial",
                    "Puede generar e imprimir el KuDE (representación gráfica)",
                    "Conserve el CDC para futuras consultas"
                ],
                is_retryable=False,
                requires_user_action=False,
                technical_details="El documento cumple con todos los requisitos técnicos y de negocio"
            ),

            "1005": ErrorInfo(
                code="1005",
                category=ErrorCategory.SUCCESS,
                severity=ErrorSeverity.WARNING,
                message="Documento aprobado con observaciones",
                user_message="⚠️ Su documento ha sido aprobado pero tiene observaciones",
                recommendations=[
                    "Revise las observaciones específicas en la respuesta",
                    "Corrija los aspectos observados para futuros documentos",
                    "El documento es válido y puede utilizarse comercialmente"
                ],
                is_retryable=False,
                requires_user_action=True,
                technical_details="El documento es válido pero presenta aspectos mejorables"
            ),

            # ========================================
            # ERRORES DE VALIDACIÓN CDC (1000-1099)
            # ========================================

            "1000": ErrorInfo(
                code="1000",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message="CDC no corresponde con el contenido del XML",
                user_message="❌ El código de control (CDC) no coincide con los datos del documento",
                recommendations=[
                    "Verifique que el CDC se haya generado correctamente",
                    "Asegúrese de no modificar el XML después de generar el CDC",
                    "Regenere el CDC con los datos actuales del documento",
                    "Verifique la configuración del algoritmo de generación"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="El CDC calculado no coincide con el proporcionado en el XML"
            ),

            "1001": ErrorInfo(
                code="1001",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message="CDC duplicado - ya existe en el sistema",
                user_message="❌ Este documento ya fue enviado anteriormente",
                recommendations=[
                    "Verifique si el documento ya fue procesado",
                    "Use un nuevo número de documento si es una factura diferente",
                    "Si es el mismo documento, consulte su estado en SIFEN",
                    "No reenvíe documentos ya aprobados"
                ],
                is_retryable=False,
                requires_user_action=True,
                technical_details="CDC duplicado en base de datos SIFEN"
            ),

            # ========================================
            # ERRORES DE TIMBRADO (1100-1199)
            # ========================================

            "1101": ErrorInfo(
                code="1101",
                category=ErrorCategory.BUSINESS_RULES,
                severity=ErrorSeverity.ERROR,
                message="Número de timbrado inválido",
                user_message="❌ El número de timbrado no es válido",
                recommendations=[
                    "Verifique que el timbrado esté activo en SET",
                    "Confirme que el número de timbrado sea correcto",
                    "Solicite un nuevo timbrado si el actual está vencido",
                    "Contacte a su contador para verificar el estado del timbrado"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="Timbrado no encontrado o inválido en base de datos SET"
            ),

            "1110": ErrorInfo(
                code="1110",
                category=ErrorCategory.BUSINESS_RULES,
                severity=ErrorSeverity.ERROR,
                message="Timbrado vencido",
                user_message="❌ Su timbrado ha vencido y no puede emitir documentos",
                recommendations=[
                    "Solicite la renovación del timbrado ante SET",
                    "Suspenda la emisión de documentos hasta renovar",
                    "Consulte con su contador sobre el proceso de renovación",
                    "Verifique las fechas de vigencia del timbrado"
                ],
                is_retryable=False,
                requires_user_action=True,
                technical_details="Fecha de vencimiento del timbrado superada"
            ),

            "1111": ErrorInfo(
                code="1111",
                category=ErrorCategory.BUSINESS_RULES,
                severity=ErrorSeverity.ERROR,
                message="Timbrado inactivo",
                user_message="❌ Su timbrado está inactivo",
                recommendations=[
                    "Contacte a SET para activar el timbrado",
                    "Verifique el estado del timbrado en el portal SET",
                    "Asegúrese de cumplir con todos los requisitos",
                    "Consulte con su contador sobre posibles causas"
                ],
                is_retryable=False,
                requires_user_action=True,
                technical_details="Timbrado marcado como inactivo en sistema SET"
            ),

            # ========================================
            # ERRORES DE FIRMA DIGITAL (0140-0149)
            # ========================================

            "0141": ErrorInfo(
                code="0141",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.CRITICAL,
                message="Firma digital inválida",
                user_message="❌ La firma digital del documento no es válida",
                recommendations=[
                    "Verifique que el certificado digital esté vigente",
                    "Confirme que el certificado pertenezca al RUC emisor",
                    "Asegúrese de firmar correctamente el XML",
                    "Contacte al proveedor del certificado si persiste el error"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="Verificación de firma digital falló"
            ),

            # ========================================
            # ERRORES DE RUC (1250-1299)
            # ========================================

            "1250": ErrorInfo(
                code="1250",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message="RUC del emisor inexistente",
                user_message="❌ El RUC del emisor no existe en el sistema SET",
                recommendations=[
                    "Verifique que el RUC esté escrito correctamente",
                    "Confirme que el RUC esté activo en SET",
                    "Asegúrese de incluir el dígito verificador",
                    "Consulte el estado del RUC en el portal SET"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="RUC emisor no encontrado en base de datos SET"
            ),

            "1255": ErrorInfo(
                code="1255",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message="RUC del receptor inexistente",
                user_message="❌ El RUC del receptor no existe en el sistema SET",
                recommendations=[
                    "Verifique que el RUC del cliente esté correcto",
                    "Confirme el RUC con el cliente",
                    "Use RUC genérico si es consumidor final",
                    "Asegúrese de incluir el dígito verificador"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="RUC receptor no encontrado en base de datos SET"
            ),

            # ========================================
            # ERRORES DE DATOS EMISOR (2000-2999)
            # ========================================

            "2001": ErrorInfo(
                code="2001",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message="Error en datos del emisor",
                user_message="❌ Los datos del emisor contienen errores",
                recommendations=[
                    "Verifique la razón social del emisor",
                    "Confirme la dirección y datos de contacto",
                    "Asegúrese que coincidan con los datos registrados en SET",
                    "Revise el formato de campos como teléfono y email"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="Validación de datos del emisor falló"
            ),

            "2002": ErrorInfo(
                code="2002",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message="Error en datos del receptor",
                user_message="❌ Los datos del receptor contienen errores",
                recommendations=[
                    "Verifique la razón social del receptor",
                    "Confirme la dirección y datos de contacto",
                    "Revise el formato de campos como teléfono y email",
                    "Asegúrese que los datos sean válidos"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="Validación de datos del receptor falló"
            ),

            # ========================================
            # ERRORES DE ITEMS (3000-3999)
            # ========================================

            "3001": ErrorInfo(
                code="3001",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message="Error en items del documento",
                user_message="❌ Los items del documento contienen errores",
                recommendations=[
                    "Verifique las cantidades y precios de los items",
                    "Confirme que los cálculos de IVA sean correctos",
                    "Asegúrese que las descripciones sean válidas",
                    "Revise que no haya campos obligatorios vacíos"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="Validación de items del documento falló"
            ),

            # ========================================
            # ERRORES DE TOTALES (4000-4999)
            # ========================================

            "4001": ErrorInfo(
                code="4001",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message="Error en totales del documento",
                user_message="❌ Los totales del documento no son correctos",
                recommendations=[
                    "Verifique que la suma de items coincida con el total",
                    "Confirme que el cálculo de IVA sea correcto",
                    "Asegúrese que no haya errores de redondeo",
                    "Revise los totales gravados y exentos"
                ],
                is_retryable=True,
                requires_user_action=True,
                technical_details="Validación de totales del documento falló"
            ),

            # ========================================
            # ERRORES DEL SISTEMA (5000+)
            # ========================================

            "5000": ErrorInfo(
                code="5000",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message="Error interno del sistema SIFEN",
                user_message="🔧 Error temporal del sistema. Intente nuevamente en unos minutos",
                recommendations=[
                    "Espere unos minutos y reintente el envío",
                    "Verifique el estado del servicio SIFEN",
                    "Si persiste, contacte al soporte técnico",
                    "Mantenga una copia del documento para reenvío"
                ],
                is_retryable=True,
                requires_user_action=False,
                technical_details="Error interno no especificado del sistema SIFEN"
            ),

            "5001": ErrorInfo(
                code="5001",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message="Servicio SIFEN temporalmente no disponible",
                user_message="🔧 El servicio SIFEN está temporalmente no disponible",
                recommendations=[
                    "Espere unos minutos antes de reintentar",
                    "Verifique los avisos oficiales de SET",
                    "Mantenga los documentos para envío posterior",
                    "Configure reintento automático si es posible"
                ],
                is_retryable=True,
                requires_user_action=False,
                technical_details="Servicio SIFEN en mantenimiento o sobrecargado"
            ),

            "5002": ErrorInfo(
                code="5002",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message="Error de base de datos en SIFEN",
                user_message="🔧 Error temporal de base de datos. Reintente en unos minutos",
                recommendations=[
                    "Espere unos minutos y reintente",
                    "No modifique el documento durante los reintentos",
                    "Si persiste, reporte el problema a SET",
                    "Mantenga evidencia del error para soporte"
                ],
                is_retryable=True,
                requires_user_action=False,
                technical_details="Error de acceso a base de datos SIFEN"
            ),

            "5003": ErrorInfo(
                code="5003",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message="Error de comunicación interna en SIFEN",
                user_message="🔧 Error de comunicación del sistema. Reintente en unos minutos",
                recommendations=[
                    "Reintente el envío después de unos minutos",
                    "Verifique su conexión a internet",
                    "Si persiste, puede ser un problema temporal de SIFEN",
                    "Contacte soporte si el error es recurrente"
                ],
                is_retryable=True,
                requires_user_action=False,
                technical_details="Error de comunicación entre componentes SIFEN"
            )
        }

        logger.info(
            "sifen_error_handler_initialized",
            total_error_codes=len(self.error_catalog),
            categories=list(ErrorCategory),
            severities=list(ErrorSeverity)
        )

    def get_error_info(self, error_code: str) -> ErrorInfo:
        """
        Obtiene información detallada de un código de error

        Args:
            error_code: Código de error SIFEN

        Returns:
            ErrorInfo con detalles del error
        """
        # Buscar en catálogo
        if error_code in self.error_catalog:
            return self.error_catalog[error_code]

        # Si no está en catálogo, crear error genérico
        return self._create_generic_error(error_code)

    def get_user_friendly_message(self, error_code: str) -> str:
        """
        Obtiene mensaje user-friendly para un código de error

        Args:
            error_code: Código de error SIFEN

        Returns:
            Mensaje comprensible para el usuario final
        """
        error_info = self.get_error_info(error_code)
        return error_info.user_message

    def get_recommendations(self, error_code: str) -> List[str]:
        """
        Obtiene recomendaciones de solución para un error

        Args:
            error_code: Código de error SIFEN

        Returns:
            Lista de recomendaciones específicas
        """
        error_info = self.get_error_info(error_code)
        return error_info.recommendations

    def is_retryable_error(self, error_code: str) -> bool:
        """
        Determina si un error es recuperable mediante reintentos

        Args:
            error_code: Código de error SIFEN

        Returns:
            True si el error es retryable, False si no
        """
        error_info = self.get_error_info(error_code)
        return error_info.is_retryable

    def requires_user_action(self, error_code: str) -> bool:
        """
        Determina si un error requiere acción del usuario

        Args:
            error_code: Código de error SIFEN

        Returns:
            True si requiere acción del usuario, False si no
        """
        error_info = self.get_error_info(error_code)
        return error_info.requires_user_action

    def get_error_category(self, error_code: str) -> ErrorCategory:
        """
        Obtiene la categoría de un error

        Args:
            error_code: Código de error SIFEN

        Returns:
            Categoría del error
        """
        error_info = self.get_error_info(error_code)
        return error_info.category

    def get_error_severity(self, error_code: str) -> ErrorSeverity:
        """
        Obtiene la severidad de un error

        Args:
            error_code: Código de error SIFEN

        Returns:
            Severidad del error
        """
        error_info = self.get_error_info(error_code)
        return error_info.severity

    def create_enhanced_response(self, response: SifenResponse) -> Dict[str, Any]:
        """
        Enriquece una respuesta SIFEN con información adicional de error

        Args:
            response: Respuesta SIFEN original

        Returns:
            Diccionario con información enriquecida
        """
        error_info = self.get_error_info(response.code)

        enhanced = {
            # Datos originales
            'original_response': response.model_dump(),

            # Información enriquecida
            'error_info': {
                'code': error_info.code,
                'category': error_info.category.value,
                'severity': error_info.severity.value,
                'user_message': error_info.user_message,
                'recommendations': error_info.recommendations,
                'is_retryable': error_info.is_retryable,
                'requires_user_action': error_info.requires_user_action,
                'technical_details': error_info.technical_details
            },

            # Metadatos adicionales
            'processing_guidance': {
                'should_retry': error_info.is_retryable and error_info.category == ErrorCategory.SYSTEM,
                'should_notify_user': error_info.requires_user_action,
                'priority_level': self._get_priority_level(error_info.severity),
                'estimated_resolution_time': self._estimate_resolution_time(error_info)
            }
        }

        # Log del enriquecimiento
        logger.info(
            "response_enhanced",
            code=response.code,
            category=error_info.category.value,
            severity=error_info.severity.value,
            is_retryable=error_info.is_retryable
        )

        return enhanced

    def analyze_error_pattern(self, error_codes: List[str]) -> Dict[str, Any]:
        """
        Analiza patrones en una lista de códigos de error

        Args:
            error_codes: Lista de códigos de error para analizar

        Returns:
            Análisis de patrones y recomendaciones
        """
        if not error_codes:
            return {'pattern': 'no_errors', 'analysis': 'No hay errores para analizar'}

        # Contadores por categoría
        category_counts = {}
        severity_counts = {}
        retryable_count = 0
        user_action_count = 0

        for code in error_codes:
            error_info = self.get_error_info(code)

            # Contar por categoría
            category = error_info.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

            # Contar por severidad
            severity = error_info.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Contadores especiales
            if error_info.is_retryable:
                retryable_count += 1
            if error_info.requires_user_action:
                user_action_count += 1

        # Determinar patrón dominante
        dominant_category = None
        max_category_count = 0
        for category, count in category_counts.items():
            if count > max_category_count:
                max_category_count = count
                dominant_category = category

        dominant_severity = None
        max_severity_count = 0
        for severity, count in severity_counts.items():
            if count > max_severity_count:
                max_severity_count = count
                dominant_severity = severity

        # Generar análisis
        analysis = {
            'total_errors': len(error_codes),
            'dominant_category': dominant_category or 'unknown',
            'dominant_severity': dominant_severity or 'error',
            'category_distribution': category_counts,
            'severity_distribution': severity_counts,
            'retryable_percentage': (retryable_count / len(error_codes)) * 100,
            'user_action_percentage': (user_action_count / len(error_codes)) * 100,
            'recommendations': self._generate_pattern_recommendations(dominant_category or 'unknown', error_codes)
        }

        logger.info(
            "error_pattern_analyzed",
            total_errors=len(error_codes),
            dominant_category=dominant_category or 'unknown',
            retryable_percentage=analysis['retryable_percentage']
        )

        return analysis

    def _create_generic_error(self, error_code: str) -> ErrorInfo:
        """Crea información genérica para códigos no catalogados"""

        # Inferir categoría por rango de código
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.ERROR

        if error_code.startswith('0'):
            category = ErrorCategory.SUCCESS if error_code in [
                '0260'] else ErrorCategory.AUTHENTICATION
        elif error_code.startswith('1'):
            category = ErrorCategory.VALIDATION
        elif error_code.startswith(('2', '3', '4')):
            category = ErrorCategory.BUSINESS_RULES
        elif error_code.startswith('5'):
            category = ErrorCategory.SYSTEM
            severity = ErrorSeverity.CRITICAL

        return ErrorInfo(
            code=error_code,
            category=category,
            severity=severity,
            message=f"Error SIFEN no catalogado: {error_code}",
            user_message=f"❓ Error {error_code}: Consulte con soporte técnico",
            recommendations=[
                "Contacte al soporte técnico con el código de error",
                "Proporcione el XML completo y la respuesta recibida",
                "Documente las condiciones que causaron el error",
                "Verifique si hay actualizaciones disponibles del sistema"
            ],
            is_retryable=category == ErrorCategory.SYSTEM,
            requires_user_action=True,
            technical_details=f"Código de error {error_code} no está en el catálogo oficial"
        )

    def _get_priority_level(self, severity: ErrorSeverity) -> str:
        """Determina nivel de prioridad basado en severidad"""
        mapping = {
            ErrorSeverity.INFO: "low",
            ErrorSeverity.WARNING: "medium",
            ErrorSeverity.ERROR: "high",
            ErrorSeverity.CRITICAL: "urgent"
        }
        return mapping.get(severity, "medium")

    def _estimate_resolution_time(self, error_info: ErrorInfo) -> str:
        """Estima tiempo de resolución basado en tipo de error"""
        if error_info.category == ErrorCategory.SUCCESS:
            return "immediate"
        elif error_info.category == ErrorCategory.SYSTEM:
            return "5-30 minutes"
        elif error_info.requires_user_action:
            return "user dependent"
        elif error_info.is_retryable:
            return "1-5 minutes"
        else:
            return "requires investigation"

    def _generate_pattern_recommendations(self, dominant_category: str, error_codes: List[str]) -> List[str]:
        """Genera recomendaciones basadas en patrones de error"""
        recommendations = []

        if dominant_category == ErrorCategory.VALIDATION.value:
            recommendations.extend([
                "Revise la configuración de validación de datos",
                "Implemente validación local antes del envío a SIFEN",
                "Verifique los formatos de campos requeridos"
            ])
        elif dominant_category == ErrorCategory.SYSTEM.value:
            recommendations.extend([
                "Configure reintentos automáticos para errores del sistema",
                "Monitore el estado del servicio SIFEN",
                "Implemente colas de reenvío para casos de falla"
            ])
        elif dominant_category == ErrorCategory.AUTHENTICATION.value:
            recommendations.extend([
                "Verifique la validez y configuración de certificados",
                "Revise el proceso de firma digital",
                "Confirme la asociación RUC-Certificado"
            ])

        return recommendations


# ========================================
# FUNCIONES HELPER
# ========================================

def get_user_friendly_error(error_code: str) -> str:
    """
    Función helper para obtener mensaje user-friendly de un error

    Args:
        error_code: Código de error SIFEN

    Returns:
        Mensaje comprensible para el usuario
    """
    handler = SifenErrorHandler()
    return handler.get_user_friendly_message(error_code)


def is_retryable_sifen_error(error_code: str) -> bool:
    """
    Función helper para determinar si un error SIFEN es retryable

    Args:
        error_code: Código de error SIFEN

    Returns:
        True si el error es retryable, False si no
    """
    handler = SifenErrorHandler()
    return handler.is_retryable_error(error_code)


def create_enhanced_sifen_response(response: SifenResponse) -> Dict[str, Any]:
    """
    Función helper para enriquecer una respuesta SIFEN

    Args:
        response: Respuesta SIFEN original

    Returns:
        Respuesta enriquecida con información adicional
    """
    handler = SifenErrorHandler()
    return handler.create_enhanced_response(response)


# Instancia global del manejador para uso eficiente
_global_error_handler = SifenErrorHandler()


def get_error_handler() -> SifenErrorHandler:
    """
    Obtiene la instancia global del manejador de errores

    Returns:
        Instancia del SifenErrorHandler
    """
    return _global_error_handler


logger.info(
    "sifen_error_handler_module_loaded",
    features=[
        "complete_error_catalog",
        "user_friendly_messages",
        "retry_guidance",
        "pattern_analysis",
        "enhanced_responses"
    ]
)
