"""
API principal (facade) para validadores SIFEN v150

Este módulo proporciona una API unificada que combina todos los validadores
modulares en una interfaz simple y coherente. Implementa el patrón Facade
para ocultar la complejidad interna y ofrecer múltiples niveles de validación.

Responsabilidades:
- Combinar validadores de estructura, formato y XSD
- Proporcionar API simple para validación completa
- Ofrecer funciones de conveniencia para casos específicos
- Exportar clases y funciones públicas del módulo

Uso:
    # Validación completa (recomendado)
    from validators import validate_xml
    is_valid, errors = validate_xml(xml_content)
    
    # Validación con clase principal
    from validators import SifenValidator
    validator = SifenValidator()
    is_valid, errors = validator.validate_xml(xml_content)
    
    # Validaciones específicas
    from validators import validate_xml_structure, validate_sifen_format
    struct_valid, struct_errors = validate_xml_structure(xml_content)
    format_valid, format_errors = validate_sifen_format(xml_content)

Características:
- Facade pattern para API simple
- Validación en cascada con fail-fast
- Múltiples niveles de granularidad
- Manejo unificado de errores

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
"""

from typing import Tuple, List, Optional, Dict, Any, Union

# Imports de los validadores modulares
from .core_validator import CoreXSDValidator
from .structure_validator import StructureValidator
from .format_validator import FormatValidator
from .error_handler import ErrorHandler, ValidationError

# Imports de utilidades individuales para re-export
from .core_validator import (
    quick_xsd_validation,
    get_xsd_errors_only,
    validate_with_performance_metrics
)
from .structure_validator import (
    quick_structure_check,
    get_structure_errors,
    analyze_document_structure
)
from .format_validator import (
    quick_validate_ruc,
    quick_validate_cdc,
    quick_validate_date,
    get_format_errors_only
)
from .error_handler import (
    create_validation_error,
    quick_format_errors
)


# =====================================
# CLASE PRINCIPAL FACADE
# =====================================

class SifenValidator:
    """
    Validador unificado para documentos XML SIFEN v150

    Combina todos los validadores modulares en una API simple que
    realiza validación completa en el orden óptimo:
    1. Estructura básica (fail-fast para errores críticos)
    2. Validación XSD (autoritativa contra esquemas oficiales)  
    3. Formatos SIFEN (validaciones específicas complementarias)

    La validación sigue el principio fail-fast para errores estructurales
    críticos, pero acumula errores de XSD y formato para reporte completo.

    Example:
        >>> validator = SifenValidator()
        >>> is_valid, errors = validator.validate_xml(xml_content)
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(error)
    """

    def __init__(self, xsd_path: Optional[str] = None):
        """
        Inicializa el validador unificado

        Args:
            xsd_path: Ruta opcional al archivo XSD personalizado.
                     Si no se proporciona, usa el XSD por defecto de SIFEN v150

        Example:
            >>> # Usar XSD por defecto
            >>> validator = SifenValidator()
            >>> 
            >>> # Usar XSD personalizado
            >>> validator = SifenValidator("/path/to/custom.xsd")
        """
        # Inicializar validadores modulares
        self.core_validator = CoreXSDValidator(xsd_path)
        self.structure_validator = StructureValidator()
        self.format_validator = FormatValidator()
        self.error_handler = ErrorHandler()

        # Configuración de validación
        self._fail_fast_on_structure = True
        self._accumulate_all_errors = True

        # Estadísticas de uso
        self._validation_stats: Dict[str, Any] = {
            'total_validations': 0,
            'structure_failures': 0,
            'xsd_failures': 0,
            'format_failures': 0,
            'completely_valid': 0
        }

    def validate_xml(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Validación completa de XML SIFEN v150

        Realiza validación completa en cascada:
        1. Estructura básica (fail-fast si es crítico)
        2. Validación XSD (autoritativa)
        3. Formatos SIFEN específicos (complementaria)

        Args:
            xml_content: Contenido XML a validar como string

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores_formateados)

        Example:
            >>> validator = SifenValidator()
            >>> xml = '<?xml version="1.0"?><rDE xmlns="...">...</rDE>'
            >>> is_valid, errors = validator.validate_xml(xml)
            >>> print(f"Válido: {is_valid}, Errores: {len(errors)}")
        """
        self._validation_stats['total_validations'] += 1
        all_errors = []

        # 1. VALIDACIÓN DE ESTRUCTURA BÁSICA (fail-fast)
        is_structure_valid, structure_errors = self.structure_validator.validate(
            xml_content)

        if not is_structure_valid:
            self._validation_stats['structure_failures'] += 1
            all_errors.extend(structure_errors)

            # Fail-fast para errores estructurales críticos
            if self._fail_fast_on_structure and self._is_critical_structure_error(structure_errors):
                formatted_errors = self.error_handler.format_errors(all_errors)
                return False, formatted_errors

        # 2. VALIDACIÓN XSD (autoritativa)
        is_xsd_valid, xsd_errors = self.core_validator.validate(xml_content)

        if not is_xsd_valid:
            self._validation_stats['xsd_failures'] += 1
            all_errors.extend(xsd_errors)

        # 3. VALIDACIÓN DE FORMATOS SIFEN (complementaria)
        is_format_valid, format_errors = self.format_validator.validate(
            xml_content)

        if not is_format_valid:
            self._validation_stats['format_failures'] += 1
            all_errors.extend(format_errors)

        # Formatear errores finales
        final_errors = self.error_handler.format_errors(all_errors)

        # Actualizar estadísticas
        is_completely_valid = len(final_errors) == 0
        if is_completely_valid:
            self._validation_stats['completely_valid'] += 1

        return is_completely_valid, final_errors

    def _is_critical_structure_error(self, errors: List[str]) -> bool:
        """
        Determina si hay errores estructurales críticos que justifican fail-fast

        Args:
            errors: Lista de errores estructurales

        Returns:
            True si hay errores críticos que impiden validación posterior
        """
        critical_keywords = [
            'xml mal formado',
            'namespace incorrecto',
            'elemento raíz incorrecto',
            'error parseando xml'
        ]

        for error in errors:
            error_lower = error.lower()
            for keyword in critical_keywords:
                if keyword in error_lower:
                    return True

        return False

    def validate_structure_only(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Validación solo de estructura básica (rápida)

        Args:
            xml_content: Contenido XML a validar

        Returns:
            Tuple[bool, List[str]]: (es_válido, errores_de_estructura)
        """
        is_valid, errors = self.structure_validator.validate(xml_content)
        formatted_errors = self.error_handler.format_errors(errors)
        return is_valid, formatted_errors

    def validate_xsd_only(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Validación solo contra XSD (autoritativa)

        Args:
            xml_content: Contenido XML a validar

        Returns:
            Tuple[bool, List[str]]: (es_válido, errores_de_xsd)
        """
        is_valid, errors = self.core_validator.validate(xml_content)
        formatted_errors = self.error_handler.format_errors(errors)
        return is_valid, formatted_errors

    def validate_format_only(self, xml_content: str) -> Tuple[bool, List[str]]:
        """
        Validación solo de formatos SIFEN (complementaria)

        Args:
            xml_content: Contenido XML a validar

        Returns:
            Tuple[bool, List[str]]: (es_válido, errores_de_formato)
        """
        is_valid, errors = self.format_validator.validate(xml_content)
        formatted_errors = self.error_handler.format_errors(errors)
        return is_valid, formatted_errors

    def get_validation_report(self, xml_content: str) -> Dict[str, Any]:
        """
        Genera reporte completo de validación con detalles por categoría

        Args:
            xml_content: Contenido XML a validar

        Returns:
            Diccionario con reporte detallado de validación
        """
        # Realizar validaciones individuales
        struct_valid, struct_errors = self.structure_validator.validate(
            xml_content)
        xsd_valid, xsd_errors = self.core_validator.validate(xml_content)
        format_valid, format_errors = self.format_validator.validate(
            xml_content)

        # Combinar todos los errores
        all_errors = struct_errors + xsd_errors + format_errors
        formatted_errors = self.error_handler.format_errors(all_errors)

        # Crear resumen de errores
        error_summary = self.error_handler.create_validation_summary(
            all_errors)

        # Reporte completo
        report = {
            'overall_valid': len(formatted_errors) == 0,
            'total_errors': len(formatted_errors),
            'validation_results': {
                'structure': {
                    'valid': struct_valid,
                    'errors': self.error_handler.format_errors(struct_errors),
                    'error_count': len(struct_errors)
                },
                'xsd': {
                    'valid': xsd_valid,
                    'errors': self.error_handler.format_errors(xsd_errors),
                    'error_count': len(xsd_errors)
                },
                'format': {
                    'valid': format_valid,
                    'errors': self.error_handler.format_errors(format_errors),
                    'error_count': len(format_errors)
                }
            },
            'error_summary': error_summary,
            'all_errors': formatted_errors,
            'schema_info': self.core_validator.get_schema_info(),
            'validation_order': ['structure', 'xsd', 'format']
        }

        return report

    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso del validador

        Returns:
            Diccionario con estadísticas de validación
        """
        stats = self._validation_stats.copy()

        # Calcular porcentajes si hay validaciones
        if stats['total_validations'] > 0:
            total = stats['total_validations']
            stats['success_rate'] = round(
                (stats['completely_valid'] / total) * 100, 1)
            stats['structure_failure_rate'] = round(
                (stats['structure_failures'] / total) * 100, 1)
            stats['xsd_failure_rate'] = round(
                (stats['xsd_failures'] / total) * 100, 1)
            stats['format_failure_rate'] = round(
                (stats['format_failures'] / total) * 100, 1)

        return stats


# =====================================
# FUNCIONES DE CONVENIENCIA PRINCIPALES
# =====================================

def validate_xml(xml_content: str, xsd_path: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Función principal de validación completa SIFEN v150

    Esta es la función recomendada para la mayoría de casos de uso.
    Realiza validación completa: estructura + XSD + formato.

    Args:
        xml_content: Contenido XML a validar como string
        xsd_path: Ruta opcional al archivo XSD personalizado

    Returns:
        Tuple[bool, List[str]]: (es_válido, lista_de_errores)

    Example:
        >>> is_valid, errors = validate_xml(xml_content)
        >>> if not is_valid:
        ...     print(f"Errores encontrados: {len(errors)}")
        ...     for error in errors:
        ...         print(f"- {error}")
    """
    validator = SifenValidator(xsd_path)
    return validator.validate_xml(xml_content)


def validate_xml_structure(xml_content: str) -> Tuple[bool, List[str]]:
    """
    Validación rápida solo de estructura básica

    Útil para verificación inicial antes de procesamiento más pesado.
    Valida namespace, elemento raíz, atributos y elementos obligatorios.

    Args:
        xml_content: Contenido XML a validar

    Returns:
        Tuple[bool, List[str]]: (estructura_válida, errores_estructura)

    Example:
        >>> is_struct_ok, struct_errors = validate_xml_structure(xml_content)
        >>> if is_struct_ok:
        ...     print("Estructura básica correcta")
    """
    validator = StructureValidator()
    is_valid, errors = validator.validate(xml_content)
    error_handler = ErrorHandler()
    formatted_errors = error_handler.format_errors(errors)
    return is_valid, formatted_errors


def validate_sifen_format(xml_content: str) -> Tuple[bool, List[str]]:
    """
    Validación solo de formatos específicos SIFEN

    Valida formatos de campos como RUC, CDC, fechas, códigos de documento.
    Útil para verificar datos antes de generar XML final.

    Args:
        xml_content: Contenido XML a validar

    Returns:
        Tuple[bool, List[str]]: (formatos_válidos, errores_formato)

    Example:
        >>> is_format_ok, format_errors = validate_sifen_format(xml_content)
        >>> if not is_format_ok:
        ...     print("Errores de formato encontrados")
    """
    validator = FormatValidator()
    is_valid, errors = validator.validate(xml_content)
    error_handler = ErrorHandler()
    formatted_errors = error_handler.format_errors(errors)
    return is_valid, formatted_errors


def validate_with_detailed_report(xml_content: str, xsd_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Validación completa con reporte detallado para debugging

    Proporciona información completa de validación incluyendo estadísticas,
    errores por categoría y recomendaciones.

    Args:
        xml_content: Contenido XML a validar
        xsd_path: Ruta opcional al XSD personalizado

    Returns:
        Diccionario con reporte completo de validación

    Example:
        >>> report = validate_with_detailed_report(xml_content)
        >>> print(f"Válido: {report['overall_valid']}")
        >>> print(f"Errores por categoría: {report['error_summary']['categories']}")
    """
    validator = SifenValidator(xsd_path)
    return validator.get_validation_report(xml_content)


def quick_validate(xml_content: str) -> bool:
    """
    Validación rápida que retorna solo resultado booleano

    Útil para casos donde solo necesitas saber si es válido o no,
    sin detalles de errores.

    Args:
        xml_content: Contenido XML a validar

    Returns:
        True si el XML es completamente válido

    Example:
        >>> if quick_validate(xml_content):
        ...     print("XML válido")
        ... else:
        ...     print("XML inválido")
    """
    is_valid, _ = validate_xml(xml_content)
    return is_valid


def get_validation_errors_only(xml_content: str, xsd_path: Optional[str] = None) -> List[str]:
    """
    Obtiene solo la lista de errores sin el resultado booleano

    Args:
        xml_content: Contenido XML a validar
        xsd_path: Ruta opcional al XSD

    Returns:
        Lista de errores formateados (vacía si es válido)
    """
    _, errors = validate_xml(xml_content, xsd_path)
    return errors


# =====================================
# UTILIDADES DE DEBUGGING Y ANÁLISIS
# =====================================

def analyze_xml_quality(xml_content: str) -> Dict[str, Any]:
    """
    Análisis completo de calidad del XML SIFEN

    Proporciona información detallada sobre la calidad del documento
    incluyendo estructura, formatos, y cumplimiento XSD.

    Args:
        xml_content: Contenido XML a analizar

    Returns:
        Diccionario con análisis de calidad completo
    """
    # Análisis estructural detallado
    struct_analysis = analyze_document_structure(xml_content)

    # Resumen de formatos
    validator = FormatValidator()
    format_summary = validator.get_field_validation_summary(xml_content)

    # Validación completa
    validation_report = validate_with_detailed_report(xml_content)

    # Compilar análisis de calidad
    quality_analysis = {
        'structure_analysis': struct_analysis,
        'format_analysis': format_summary,
        'validation_report': validation_report,
        'quality_score': _calculate_quality_score(validation_report, format_summary),
        'recommendations': _generate_quality_recommendations(validation_report, format_summary)
    }

    return quality_analysis


def _calculate_quality_score(validation_report: Dict[str, Any], format_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula puntaje de calidad del documento

    Args:
        validation_report: Reporte de validación
        format_summary: Resumen de formatos

    Returns:
        Diccionario con puntajes de calidad
    """
    # Puntajes por categoría (0-100)
    structure_score = 100 if validation_report['validation_results']['structure']['valid'] else 0
    xsd_score = 100 if validation_report['validation_results']['xsd']['valid'] else 0

    # Puntaje de formato basado en tipos de campo válidos
    if '_statistics' in format_summary:
        format_stats = format_summary['_statistics']
        if format_stats['total_field_types'] > 0:
            format_score = (
                format_stats['valid_field_types'] / format_stats['total_field_types']) * 100
        else:
            format_score = 100
    else:
        format_score = 0

    # Puntaje general (promedio ponderado)
    overall_score = (structure_score * 0.4 +
                     xsd_score * 0.4 + format_score * 0.2)

    return {
        'overall_score': round(overall_score, 1),
        'structure_score': structure_score,
        'xsd_score': xsd_score,
        'format_score': round(format_score, 1),
        'quality_level': _get_quality_level(overall_score)
    }


def _get_quality_level(score: float) -> str:
    """Determina nivel de calidad basado en puntaje"""
    if score >= 95:
        return 'Excelente'
    elif score >= 85:
        return 'Bueno'
    elif score >= 70:
        return 'Aceptable'
    elif score >= 50:
        return 'Deficiente'
    else:
        return 'Inaceptable'


def _generate_quality_recommendations(validation_report: Dict[str, Any], format_summary: Dict[str, Any]) -> List[str]:
    """
    Genera recomendaciones para mejorar calidad del documento

    Args:
        validation_report: Reporte de validación
        format_summary: Resumen de formatos

    Returns:
        Lista de recomendaciones
    """
    recommendations = []

    # Recomendaciones basadas en errores de validación
    if validation_report['error_summary']['recommendations']:
        recommendations.extend(
            validation_report['error_summary']['recommendations'])

    # Recomendaciones específicas de formato
    if '_statistics' in format_summary and format_summary['_statistics']['total_errors'] > 0:
        recommendations.append(
            "Revisar y corregir formatos de campos específicos SIFEN")

    # Recomendación general si hay muchos errores
    if validation_report['total_errors'] > 10:
        recommendations.append(
            "Considerar regenerar el documento desde una plantilla validada")

    return recommendations


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    # Clase principal
    'SifenValidator',

    # Funciones principales de validación
    'validate_xml',
    'validate_xml_structure',
    'validate_sifen_format',
    'validate_with_detailed_report',
    'quick_validate',
    'get_validation_errors_only',

    # Análisis y debugging
    'analyze_xml_quality',

    # Clases para uso avanzado
    'CoreXSDValidator',
    'StructureValidator',
    'FormatValidator',
    'ErrorHandler',
    'ValidationError',

    # Utilidades específicas re-exportadas
    'quick_xsd_validation',
    'get_xsd_errors_only',
    'validate_with_performance_metrics',
    'quick_structure_check',
    'get_structure_errors',
    'analyze_document_structure',
    'quick_validate_ruc',
    'quick_validate_cdc',
    'quick_validate_date',
    'get_format_errors_only',
    'create_validation_error',
    'quick_format_errors'
]
