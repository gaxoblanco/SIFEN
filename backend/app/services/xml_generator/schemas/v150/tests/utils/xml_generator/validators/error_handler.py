"""
Manejador y formateador de errores de validación SIFEN v150

Este módulo centraliza el manejo de errores de validación para documentos
electrónicos SIFEN, proporcionando categorización inteligente, formateo
amigable y resúmenes estadísticos de errores.

Responsabilidades:
- Definir excepción personalizada ValidationError
- Categorizar errores por tipo (sintaxis, XSD, formato, estructura)
- Formatear errores con prefijos informativos
- Generar resúmenes estadísticos para debugging

Uso:
    from .error_handler import ErrorHandler, ValidationError
    
    handler = ErrorHandler()
    formatted_errors = handler.format_errors(raw_errors)
    summary = handler.create_validation_summary(errors)

Autor: Sistema de Facturación Electrónica Paraguay
Versión: 1.0.0
"""

from typing import List, Dict, Optional, Tuple, Any
import re


# =====================================
# EXCEPCIÓN PERSONALIZADA
# =====================================

class ValidationError(Exception):
    """
    Excepción específica para errores de validación SIFEN

    Esta excepción se utiliza para errores críticos que impiden
    la validación normal del documento, como problemas de carga
    de schema o XML completamente malformado.

    Attributes:
        message: Descripción del error
        error_code: Código opcional para categorización
        context: Información adicional de contexto
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa una excepción de validación

        Args:
            message: Mensaje descriptivo del error
            error_code: Código opcional para categorización
            context: Información adicional de contexto
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}

        # Construir mensaje completo para la excepción
        full_message = message
        if error_code:
            full_message = f"[{error_code}] {message}"

        super().__init__(full_message)

    def __str__(self) -> str:
        """Representación string de la excepción"""
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la excepción a diccionario para serialización

        Returns:
            Diccionario con información del error
        """
        return {
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context
        }


# =====================================
# MANEJADOR PRINCIPAL DE ERRORES
# =====================================

class ErrorHandler:
    """
    Manejador central de errores de validación SIFEN

    Proporciona funcionalidades para categorizar, formatear y analizar
    errores de validación de documentos electrónicos.
    """

    def __init__(self):
        """Inicializa el manejador de errores"""
        # Categorías de errores con sus identificadores
        self.error_categories = {
            'xml_syntax': 'Error de Sintaxis XML',
            'xsd_validation': 'Error de Validación XSD',
            'sifen_format': 'Error de Formato SIFEN',
            'structure': 'Error de Estructura',
            'business_rule': 'Error de Regla de Negocio',
            'system': 'Error del Sistema'
        }

        # Patrones para categorización automática
        self._category_patterns = self._initialize_category_patterns()

        # Mapeo de códigos de error XSD comunes
        self._xsd_error_codes = {
            'cvc-pattern-valid': 'sifen_format',
            'cvc-minLength-valid': 'sifen_format',
            'cvc-maxLength-valid': 'sifen_format',
            'cvc-type.3.1.3': 'xsd_validation',
            'cvc-enumeration-valid': 'sifen_format',
            'cvc-complex-type.2.4.a': 'structure',
            'cvc-complex-type.2.4.b': 'structure',
            'cvc-complex-type.4': 'structure'
        }

    def _initialize_category_patterns(self) -> Dict[str, List[str]]:
        """
        Inicializa patrones para categorización automática de errores

        Returns:
            Diccionario con patrones por categoría
        """
        return {
            'xml_syntax': [
                'xml mal formado',
                'sintaxis xml',
                'not well-formed',
                'xmlsyntaxerror',
                'premature end of data',
                'mismatched tag',
                'unclosed token'
            ],
            'xsd_validation': [
                'xsd',
                'schema',
                'validación',
                'cvc-',
                'element not found',
                'invalid element',
                'not valid'
            ],
            'sifen_format': [
                'cdc',
                'ruc',
                'fecha',
                'formato',
                'patrón',
                'pattern',
                'longitud',
                'length',
                'dígitos',
                'digits',
                'código',
                'timbrado',
                'establecimiento'
            ],
            'structure': [
                'namespace',
                'elemento raíz',
                'root element',
                'elemento faltante',
                'missing element',
                'atributo',
                'attribute',
                'estructura',
                'required'
            ],
            'business_rule': [
                'regla de negocio',
                'business rule',
                'condición',
                'constraint',
                'validación de negocio',
                'operación',
                'emisor',
                'receptor'
            ],
            'system': [
                'error del sistema',
                'system error',
                'internal error',
                'timeout',
                'conexión',
                'connection',
                'memoria',
                'memory'
            ]
        }

    def format_errors(self, errors: List[str]) -> List[str]:
        """
        Formatea una lista de errores para mejor legibilidad

        Args:
            errors: Lista de errores sin formatear

        Returns:
            Lista de errores formateados con prefijos de categoría

        Example:
            >>> handler = ErrorHandler()
            >>> errors = ["RUC inválido", "XML mal formado"]
            >>> formatted = handler.format_errors(errors)
            >>> print(formatted)
            ['[Error de Formato SIFEN] RUC inválido', '[Error de Sintaxis XML] XML mal formado']
        """
        if not errors:
            return []

        formatted_errors = []

        for error in errors:
            category = self._categorize_error(error)
            formatted_error = self._format_single_error(error, category)
            formatted_errors.append(formatted_error)

        return formatted_errors

    def _categorize_error(self, error: str) -> str:
        """
        Categoriza un error según su contenido

        Args:
            error: Mensaje de error a categorizar

        Returns:
            Categoría del error
        """
        error_lower = error.lower()

        # Verificar códigos de error XSD específicos primero
        for xsd_code, category in self._xsd_error_codes.items():
            if xsd_code in error_lower:
                return category

        # Verificar patrones de texto por orden de prioridad
        # XML syntax tiene prioridad porque si hay error de sintaxis,
        # no se pueden hacer otras validaciones
        for category in ['xml_syntax', 'structure', 'sifen_format', 'xsd_validation', 'business_rule', 'system']:
            patterns = self._category_patterns[category]
            for pattern in patterns:
                if pattern in error_lower:
                    return category

        # Si no se puede categorizar, asumir error de validación XSD
        return 'xsd_validation'

    def _format_single_error(self, error: str, category: str) -> str:
        """
        Formatea un error individual con su categoría

        Args:
            error: Mensaje de error original
            category: Categoría del error

        Returns:
            Error formateado con prefijo de categoría
        """
        category_label = self.error_categories.get(category, 'Error')

        # Limpiar el error de códigos XSD internos si es necesario
        cleaned_error = self._clean_error_message(error)

        # Agregar información de línea si está disponible
        formatted_error = self._enhance_error_with_location(cleaned_error)

        return f"[{category_label}] {formatted_error}"

    def _clean_error_message(self, error: str) -> str:
        """
        Limpia mensajes de error de códigos internos innecesarios

        Args:
            error: Mensaje de error original

        Returns:
            Mensaje de error limpio
        """
        # Remover códigos de error de lxml muy técnicos
        # Ejemplo: "Element '{http://...}rDE': ..." -> "Element 'rDE': ..."
        cleaned = re.sub(r'\{[^}]*\}', '', error)

        # Remover paths de archivos temporales
        cleaned = re.sub(r'file:///[^\s,]+', '<archivo>', cleaned)

        # Simplificar mensajes de validación comunes
        replacements = {
            'The value is not a valid value for the facet': 'Valor no válido para el campo',
            'is not a valid value of the atomic type': 'no es un valor válido',
            'Missing child element(s)': 'Elemento(s) hijo faltante(s)',
            'Invalid content was found starting with element': 'Contenido inválido encontrado en elemento'
        }

        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        return cleaned.strip()

    def _enhance_error_with_location(self, error: str) -> str:
        """
        Mejora el error con información de ubicación si está disponible

        Args:
            error: Mensaje de error

        Returns:
            Error mejorado con ubicación
        """
        # Buscar números de línea en el mensaje
        line_match = re.search(r'line (\d+)', error, re.IGNORECASE)
        if line_match:
            line_num = line_match.group(1)
            if f'Línea {line_num}:' not in error:
                error = f"Línea {line_num}: {error}"

        return error

    def create_validation_summary(self, errors: List[str]) -> Dict[str, Any]:
        """
        Crea un resumen estadístico de errores para debugging

        Args:
            errors: Lista de errores a analizar

        Returns:
            Diccionario con estadísticas y análisis de errores

        Example:
            >>> handler = ErrorHandler()
            >>> errors = ["RUC inválido", "XML mal formado", "CDC incorrecto"]
            >>> summary = handler.create_validation_summary(errors)
            >>> print(summary)
            {
                'total_errors': 3,
                'is_valid': False,
                'categories': {'sifen_format': 2, 'xml_syntax': 1},
                'most_common_category': 'sifen_format',
                'severity': 'high',
                'recommendations': [...]
            }
        """
        if not errors:
            return {
                'total_errors': 0,
                'is_valid': True,
                'categories': {},
                'most_common_category': None,
                'severity': 'none',
                'recommendations': []
            }

        # Categorizar todos los errores
        categories = {}
        for error in errors:
            category = self._categorize_error(error)
            categories[category] = categories.get(category, 0) + 1

        # Encontrar categoría más común
        most_common_category = max(categories.items(), key=lambda x: x[1])[
            0] if categories else None

        # Determinar severidad
        severity = self._determine_severity(categories, len(errors))

        # Generar recomendaciones
        recommendations = self._generate_recommendations(
            categories, most_common_category)

        return {
            'total_errors': len(errors),
            'is_valid': False,
            'categories': categories,
            'most_common_category': most_common_category,
            'severity': severity,
            'recommendations': recommendations,
            'detailed_analysis': self._create_detailed_analysis(errors, categories)
        }

    def _determine_severity(self, categories: Dict[str, int], total_errors: int) -> str:
        """
        Determina la severidad de los errores

        Args:
            categories: Categorías de errores con conteos
            total_errors: Total de errores

        Returns:
            Nivel de severidad: 'low', 'medium', 'high', 'critical'
        """
        # Errores críticos que impiden cualquier validación
        if 'xml_syntax' in categories or 'system' in categories:
            return 'critical'

        # Muchos errores indican problemas serios
        if total_errors > 20:
            return 'critical'
        elif total_errors > 10:
            return 'high'
        elif total_errors > 5:
            return 'medium'
        else:
            return 'low'

    def _generate_recommendations(
        self,
        categories: Dict[str, int],
        most_common_category: Optional[str]
    ) -> List[str]:
        """
        Genera recomendaciones basadas en los tipos de errores

        Args:
            categories: Categorías de errores
            most_common_category: Categoría más común

        Returns:
            Lista de recomendaciones
        """
        recommendations = []

        if 'xml_syntax' in categories:
            recommendations.append(
                "Verificar que el XML esté bien formado (etiquetas cerradas, caracteres válidos)")

        if 'structure' in categories:
            recommendations.append(
                "Revisar elementos obligatorios y estructura del documento SIFEN")

        if 'sifen_format' in categories:
            recommendations.append(
                "Validar formatos de campos específicos (RUC, CDC, fechas)")

        if 'xsd_validation' in categories:
            recommendations.append(
                "Consultar el esquema XSD oficial SIFEN v150")

        if most_common_category == 'sifen_format':
            recommendations.append(
                "Enfocar en corregir formatos de datos antes de revalidar")

        if len(categories) > 3:
            recommendations.append(
                "Revisar múltiples aspectos del documento - considerar regenerar desde plantilla")

        return recommendations

    def _create_detailed_analysis(
        self,
        errors: List[str],
        categories: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Crea análisis detallado de errores para debugging avanzado

        Args:
            errors: Lista de errores originales
            categories: Categorías con conteos

        Returns:
            Análisis detallado
        """
        # Encontrar errores más comunes
        error_frequency = {}
        for error in errors:
            error_frequency[error] = error_frequency.get(error, 0) + 1

        # Errores más frecuentes
        most_frequent = sorted(
            error_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Análisis de patrones
        patterns_found = []
        for error in errors:
            if 'cdc' in error.lower():
                patterns_found.append('Problemas con CDC')
            if 'ruc' in error.lower():
                patterns_found.append('Problemas con RUC')
            if 'fecha' in error.lower():
                patterns_found.append('Problemas con fechas')

        return {
            'most_frequent_errors': most_frequent,
            'unique_errors': len(set(errors)),
            'patterns_detected': list(set(patterns_found)),
            'category_distribution': {
                cat: round((count / len(errors)) * 100, 1)
                for cat, count in categories.items()
            }
        }

    def get_error_by_category(self, errors: List[str], category: str) -> List[str]:
        """
        Filtra errores por categoría específica

        Args:
            errors: Lista de errores
            category: Categoría a filtrar

        Returns:
            Errores de la categoría especificada
        """
        if category not in self.error_categories:
            available = ', '.join(self.error_categories.keys())
            raise ValueError(
                f"Categoría '{category}' no válida. Disponibles: {available}")

        filtered_errors = []
        for error in errors:
            if self._categorize_error(error) == category:
                filtered_errors.append(error)

        return filtered_errors

    def format_error_report(self, errors: List[str]) -> str:
        """
        Genera un reporte formateado de errores para logging o display

        Args:
            errors: Lista de errores

        Returns:
            Reporte formateado como string
        """
        if not errors:
            return "✅ No se encontraron errores de validación"

        summary = self.create_validation_summary(errors)
        formatted_errors = self.format_errors(errors)

        report_lines = [
            "❌ REPORTE DE ERRORES DE VALIDACIÓN SIFEN",
            "=" * 50,
            f"Total de errores: {summary['total_errors']}",
            f"Severidad: {summary['severity'].upper()}",
            ""
        ]

        # Agregar errores por categoría
        for category, count in summary['categories'].items():
            category_name = self.error_categories[category]
            report_lines.append(f"📋 {category_name}: {count} error(es)")

        report_lines.extend([
            "",
            "🔍 ERRORES DETALLADOS:",
            "-" * 30
        ])

        # Agregar errores formateados
        for i, error in enumerate(formatted_errors, 1):
            report_lines.append(f"{i}. {error}")

        # Agregar recomendaciones
        if summary['recommendations']:
            report_lines.extend([
                "",
                "💡 RECOMENDACIONES:",
                "-" * 20
            ])
            for rec in summary['recommendations']:
                report_lines.append(f"• {rec}")

        return "\n".join(report_lines)


# =====================================
# UTILIDADES ADICIONALES
# =====================================

def create_validation_error(
    message: str,
    error_code: Optional[str] = None,
    **context
) -> ValidationError:
    """
    Factory function para crear errores de validación

    Args:
        message: Mensaje del error
        error_code: Código opcional
        **context: Contexto adicional

    Returns:
        Nueva instancia de ValidationError
    """
    return ValidationError(message, error_code, context)


def quick_format_errors(errors: List[str]) -> List[str]:
    """
    Función de conveniencia para formateo rápido de errores

    Args:
        errors: Lista de errores

    Returns:
        Errores formateados
    """
    handler = ErrorHandler()
    return handler.format_errors(errors)


# =====================================
# EXPORTS PÚBLICOS
# =====================================

__all__ = [
    'ValidationError',
    'ErrorHandler',
    'create_validation_error',
    'quick_format_errors'
]
