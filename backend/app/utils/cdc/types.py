"""
Tipos de datos, enumeraciones y constantes para el módulo CDC SIFEN.

Este módulo centraliza todas las definiciones de tipos, enumeraciones,
constantes y clases de datos utilizadas en la generación y validación
de Códigos de Control de Documentos (CDC).

RESPONSABILIDADES:
- Definir enumeraciones para tipos de documentos y emisión
- Especificar clases de datos para componentes y requests
- Centralizar constantes y patrones de validación
- Proporcionar utilidades de introspección de tipos

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

import re
from datetime import datetime, date
from typing import Dict, Optional, Union, List, Any
from dataclasses import dataclass
from enum import Enum


# ===================================================================
# CONSTANTES DE CONFIGURACIÓN
# ===================================================================

# Longitud total del CDC
CDC_LENGTH = 44

# Longitudes de cada componente del CDC
CDC_COMPONENT_LENGTHS = {
    'ruc': 8,       # RUC base sin DV
    'dv_ruc': 1,    # Dígito verificador RUC
    'tipo': 2,      # Tipo documento
    'est': 3,       # Establecimiento
    'pe': 3,        # Punto expedición
    'num': 7,       # Número documento
    'fecha': 8,     # Fecha YYYYMMDD
    'emision': 1,   # Tipo emisión
    'seguridad': 9,  # Código seguridad
    'dv_cdc': 1,    # Dígito verificador CDC
}

# Factores para el algoritmo módulo 11 del CDC (cíclicos)
CDC_MODULO_11_BASE_FACTORS = [2, 3, 4, 5, 6, 7]

# Patrones de validación
PATTERN_CDC = re.compile(r'^[0-9]{44}$')
PATTERN_FECHA_CDC = re.compile(r'^[0-9]{8}$')
PATTERN_CODIGO_SEGURIDAD = re.compile(r'^[0-9]{9}$')

# Límites para generación aleatoria
MIN_SECURITY_CODE = 100000000  # 9 dígitos mínimos
MAX_SECURITY_CODE = 999999999  # 9 dígitos máximos


# ===================================================================
# ENUMERACIONES
# ===================================================================

class TipoDocumento(Enum):
    """Tipos de documentos electrónicos SIFEN v150."""
    FACTURA_ELECTRONICA = "01"
    AUTOFACTURA_ELECTRONICA = "04"
    NOTA_CREDITO_ELECTRONICA = "05"
    NOTA_DEBITO_ELECTRONICA = "06"
    NOTA_REMISION_ELECTRONICA = "07"

    @classmethod
    def get_descripcion(cls, codigo: str) -> Optional[str]:
        """Obtiene la descripción de un tipo de documento."""
        descriptions = {
            "01": "Factura Electrónica",
            "04": "Autofactura Electrónica",
            "05": "Nota de Crédito Electrónica",
            "06": "Nota de Débito Electrónica",
            "07": "Nota de Remisión Electrónica",
        }
        return descriptions.get(codigo)

    @classmethod
    def is_valid(cls, codigo: str) -> bool:
        """Verifica si un código de tipo de documento es válido."""
        return codigo in [item.value for item in cls]

    @classmethod
    def get_all_codes(cls) -> List[str]:
        """Obtiene todos los códigos válidos."""
        return [item.value for item in cls]

    @classmethod
    def get_all_descriptions(cls) -> Dict[str, str]:
        """Obtiene un mapeo completo código -> descripción."""
        result = {}
        for item in cls:
            descripcion = cls.get_descripcion(item.value)
            if descripcion is not None:  # Solo incluir si tiene descripción
                result[item.value] = descripcion
        return result


class TipoEmision(Enum):
    """Tipos de emisión de documentos."""
    NORMAL = "1"
    CONTINGENCIA = "2"

    @classmethod
    def get_descripcion(cls, codigo: str) -> Optional[str]:
        """Obtiene la descripción de un tipo de emisión."""
        descriptions = {
            "1": "Emisión Normal",
            "2": "Emisión de Contingencia",
        }
        return descriptions.get(codigo)

    @classmethod
    def is_valid(cls, codigo: str) -> bool:
        """Verifica si un código de tipo de emisión es válido."""
        return codigo in [item.value for item in cls]

    @classmethod
    def get_all_codes(cls) -> List[str]:
        """Obtiene todos los códigos válidos."""
        return [item.value for item in cls]


# ===================================================================
# CLASES DE DATOS
# ===================================================================

@dataclass
class CdcComponents:
    """
    Componentes individuales de un CDC.

    Representa la descomposición de un CDC en sus partes constituyentes
    según la especificación SIFEN v150.

    Attributes:
        ruc_emisor (str): RUC del emisor (8 dígitos)
        dv_ruc (str): Dígito verificador del RUC (1 dígito)
        tipo_documento (str): Tipo de documento (2 dígitos)
        establecimiento (str): Código establecimiento (3 dígitos)
        punto_expedicion (str): Punto de expedición (3 dígitos)
        numero_documento (str): Número de documento (7 dígitos)
        fecha_emision (str): Fecha emisión YYYYMMDD (8 dígitos)
        tipo_emision (str): Tipo emisión (1 dígito)
        codigo_seguridad (str): Código seguridad (9 dígitos)
        dv_cdc (str): Dígito verificador CDC (1 dígito)
    """
    ruc_emisor: str
    dv_ruc: str
    tipo_documento: str
    establecimiento: str
    punto_expedicion: str
    numero_documento: str
    fecha_emision: str
    tipo_emision: str
    codigo_seguridad: str
    dv_cdc: str

    def to_cdc(self) -> str:
        """Convierte los componentes a un CDC completo."""
        return (
            self.ruc_emisor + self.dv_ruc + self.tipo_documento +
            self.establecimiento + self.punto_expedicion + self.numero_documento +
            self.fecha_emision + self.tipo_emision + self.codigo_seguridad +
            self.dv_cdc
        )

    def validate_lengths(self) -> bool:
        """Valida que todos los componentes tengan la longitud correcta."""
        return (
            len(self.ruc_emisor) == CDC_COMPONENT_LENGTHS['ruc'] and
            len(self.dv_ruc) == CDC_COMPONENT_LENGTHS['dv_ruc'] and
            len(self.tipo_documento) == CDC_COMPONENT_LENGTHS['tipo'] and
            len(self.establecimiento) == CDC_COMPONENT_LENGTHS['est'] and
            len(self.punto_expedicion) == CDC_COMPONENT_LENGTHS['pe'] and
            len(self.numero_documento) == CDC_COMPONENT_LENGTHS['num'] and
            len(self.fecha_emision) == CDC_COMPONENT_LENGTHS['fecha'] and
            len(self.tipo_emision) == CDC_COMPONENT_LENGTHS['emision'] and
            len(self.codigo_seguridad) == CDC_COMPONENT_LENGTHS['seguridad'] and
            len(self.dv_cdc) == CDC_COMPONENT_LENGTHS['dv_cdc']
        )

    def get_tipo_documento_descripcion(self) -> Optional[str]:
        """Obtiene la descripción del tipo de documento."""
        return TipoDocumento.get_descripcion(self.tipo_documento)

    def get_tipo_emision_descripcion(self) -> Optional[str]:
        """Obtiene la descripción del tipo de emisión."""
        return TipoEmision.get_descripcion(self.tipo_emision)

    def get_ruc_completo(self) -> str:
        """Obtiene el RUC completo (base + DV)."""
        return self.ruc_emisor + self.dv_ruc

    def get_numero_documento_int(self) -> int:
        """Obtiene el número de documento como entero."""
        return int(self.numero_documento)

    def to_dict(self) -> Dict[str, str]:
        """Convierte los componentes a un diccionario."""
        return {
            'ruc_emisor': self.ruc_emisor,
            'dv_ruc': self.dv_ruc,
            'tipo_documento': self.tipo_documento,
            'establecimiento': self.establecimiento,
            'punto_expedicion': self.punto_expedicion,
            'numero_documento': self.numero_documento,
            'fecha_emision': self.fecha_emision,
            'tipo_emision': self.tipo_emision,
            'codigo_seguridad': self.codigo_seguridad,
            'dv_cdc': self.dv_cdc,
        }


@dataclass
class CdcGenerationRequest:
    """
    Parámetros para generar un CDC.

    Encapsula todos los datos necesarios para generar un CDC válido
    según las especificaciones SIFEN.

    Attributes:
        ruc_emisor (str): RUC del emisor (8 o 9 dígitos)
        tipo_documento (str): Tipo de documento (TipoDocumento)
        establecimiento (str): Código establecimiento 
        punto_expedicion (str): Punto de expedición
        numero_documento (int): Número secuencial del documento
        fecha_emision (Union[datetime, date, str]): Fecha de emisión
        tipo_emision (str): Tipo de emisión (TipoEmision)
        codigo_seguridad (Optional[str]): Código seguridad (auto-generado si None)
    """
    ruc_emisor: str
    tipo_documento: str
    establecimiento: str
    punto_expedicion: str
    numero_documento: int
    fecha_emision: Union[datetime, date, str]
    tipo_emision: str = TipoEmision.NORMAL.value
    codigo_seguridad: Optional[str] = None

    def __post_init__(self):
        """Validaciones básicas post-inicialización."""
        # Convertir numero_documento a int si es string
        if isinstance(self.numero_documento, str):
            self.numero_documento = int(self.numero_documento)

        # Validar que numero_documento sea positivo
        if self.numero_documento <= 0:
            raise ValueError("El número de documento debe ser mayor a cero")

    def validate_basic(self) -> List[str]:
        """
        Realiza validaciones básicas de los parámetros.

        Returns:
            List[str]: Lista de errores encontrados (vacía si es válido)
        """
        errors = []

        # Validar RUC emisor
        if not self.ruc_emisor or not self.ruc_emisor.strip():
            errors.append("RUC emisor no puede estar vacío")

        # Validar tipo de documento
        if not TipoDocumento.is_valid(self.tipo_documento):
            errors.append(f"Tipo de documento inválido: {self.tipo_documento}")

        # Validar establecimiento
        if not self.establecimiento or not self.establecimiento.strip():
            errors.append("Establecimiento no puede estar vacío")

        # Validar punto expedición
        if not self.punto_expedicion or not self.punto_expedicion.strip():
            errors.append("Punto de expedición no puede estar vacío")

        # Validar número documento
        if self.numero_documento <= 0:
            errors.append("Número de documento debe ser mayor a cero")

        # Validar fecha emisión
        if not self.fecha_emision:
            errors.append("Fecha de emisión no puede estar vacía")

        # Validar tipo emisión
        if not TipoEmision.is_valid(self.tipo_emision):
            errors.append(f"Tipo de emisión inválido: {self.tipo_emision}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el request a diccionario para logging/debug."""
        return {
            'ruc_emisor': self.ruc_emisor,
            'tipo_documento': self.tipo_documento,
            'establecimiento': self.establecimiento,
            'punto_expedicion': self.punto_expedicion,
            'numero_documento': self.numero_documento,
            'fecha_emision': str(self.fecha_emision),
            'tipo_emision': self.tipo_emision,
            'codigo_seguridad': self.codigo_seguridad,
        }


@dataclass
class CdcValidationResult:
    """
    Resultado de la validación de un CDC.

    Encapsula el resultado completo de la validación de un CDC,
    incluyendo componentes extraídos, errores y detalles adicionales.

    Attributes:
        is_valid (bool): True si el CDC es válido
        cdc (str): CDC validado
        components (Optional[CdcComponents]): Componentes extraídos
        error_message (str): Mensaje de error si no es válido
        error_code (str): Código de error para manejo programático
        validation_details (Dict): Detalles adicionales de validación
    """
    is_valid: bool
    cdc: str = ""
    components: Optional[CdcComponents] = None
    error_message: str = ""
    error_code: str = ""
    validation_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.validation_details is None:
            self.validation_details = {}

    def has_components(self) -> bool:
        """Verifica si tiene componentes extraídos."""
        return self.components is not None

    def get_error_summary(self) -> str:
        """Obtiene un resumen del error."""
        if self.is_valid:
            return "Válido"
        return f"[{self.error_code}] {self.error_message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario."""
        result: Dict[str, Any] = {
            'is_valid': self.is_valid,
            'cdc': self.cdc,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'validation_details': self.validation_details or {},
        }

        if self.components:
            result['components'] = self.components.to_dict()

        return result


# ===================================================================
# CÓDIGOS DE ERROR ESTÁNDARES
# ===================================================================

class CdcErrorCode:
    """Códigos de error estándares para validación CDC."""

    # Errores de formato básico
    INVALID_TYPE = "INVALID_TYPE"
    INVALID_LENGTH = "INVALID_LENGTH"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Errores de componentes
    COMPONENT_EXTRACTION_ERROR = "COMPONENT_EXTRACTION_ERROR"
    INVALID_RUC_IN_CDC = "INVALID_RUC_IN_CDC"
    INVALID_DOCUMENT_TYPE = "INVALID_DOCUMENT_TYPE"
    INVALID_DATE_FORMAT = "INVALID_DATE_FORMAT"
    INVALID_EMISSION_TYPE = "INVALID_EMISSION_TYPE"
    INVALID_CDC_DV = "INVALID_CDC_DV"

    # Errores de generación
    GENERATION_ERROR = "GENERATION_ERROR"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"

    # Errores inesperados
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


# ===================================================================
# CONSTANTES PARA EXPORT
# ===================================================================

__all__ = [
    # Enumeraciones
    'TipoDocumento',
    'TipoEmision',

    # Clases de datos
    'CdcComponents',
    'CdcGenerationRequest',
    'CdcValidationResult',

    # Códigos de error
    'CdcErrorCode',

    # Constantes
    'CDC_LENGTH',
    'CDC_COMPONENT_LENGTHS',
    'CDC_MODULO_11_BASE_FACTORS',
    'PATTERN_CDC',
    'PATTERN_FECHA_CDC',
    'PATTERN_CODIGO_SEGURIDAD',
    'MIN_SECURITY_CODE',
    'MAX_SECURITY_CODE',
]
