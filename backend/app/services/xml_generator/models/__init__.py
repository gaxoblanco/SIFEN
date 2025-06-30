"""
models/__init__.py - Módulo models centralizados para XML Generator SIFEN v150

Propósito:
    Punto de entrada unificado para todos los modelos del sistema SIFEN.
    Importa y re-exporta todos los modelos para uso externo simplificado.

Arquitectura Modular:
    - base.py: Modelos reutilizables (Contribuyente, ItemFactura)
    - auxiliary.py: Modelos auxiliares específicos (DocumentoAsociado, DatosAFE, etc.)
    - document_types.py: Documentos principales por tipo (FacturaSimple, NCE, etc.)
    - validators.py: Validadores XML y campos específicos

Uso simplificado:
    from xml_generator.models import (
        FacturaSimple, Contribuyente, ItemFactura,
        NotaCreditoElectronica, DocumentoAsociado
    )

Compatibilidad:
    Mantiene backward compatibility con imports existentes.
    Todos los tests y código existente siguen funcionando.

Autor: Sistema SIFEN Paraguay - Módulo XML Generator
Fecha: Junio 2025
Versión: 1.0.0
Manual: SIFEN v150 - SET Paraguay
"""

# ===============================================
# IMPORTS DE MODELOS BASE REUTILIZABLES
# ===============================================

import os
from .base import (
    # === MODELOS PRINCIPALES ===
    Contribuyente,
    ItemFactura,

    # === VALIDADORES REUTILIZABLES ===
    validate_ruc_paraguayo,
    validate_cdc_format,
    validate_email_format,
    validate_departamento_paraguay,

    # === CONSTANTES PARAGUAY ===
    DEPARTAMENTOS_PARAGUAY,
    IVA_RATES_PARAGUAY,
    MONEDAS_SIFEN,

    # === HELPERS PARA TESTING ===
    create_contribuyente_ejemplo,
    create_item_ejemplo,

    # === INFORMACIÓN DEL MÓDULO ===
    MODULE_INFO as BASE_MODULE_INFO
)

# ===============================================
# IMPORTS DE MODELOS AUXILIARES ESPECÍFICOS
# ===============================================

from .auxiliary import (
    # === MODELOS AUXILIARES PRINCIPALES ===
    DocumentoAsociado,
    ContribuyenteExtranjero,
    DatosAFE,
    DatosVehiculo,
    DatosTransporte,

    # === CONSTANTES ESPECÍFICAS ===
    TIPOS_DOCUMENTO_REF_VALIDOS,
    NATURALEZA_VENDEDOR_AFE,
    TIPOS_OPERACION_AFE,
    TIPOS_VEHICULO,
    TIPOS_TRANSPORTE,
    RESPONSABLES_TRANSPORTE,
    MODALIDADES_TRANSPORTE,

    # === HELPERS PARA TESTING ===
    create_documento_asociado_ejemplo,
    create_contribuyente_extranjero_ejemplo,
    create_datos_afe_ejemplo,
    create_vehiculo_ejemplo,
    create_datos_transporte_ejemplo,

    # === FACTORIES ESPECÍFICAS ===
    create_documento_asociado_factura,
    create_contribuyente_no_contribuyente,
    create_datos_afe_no_contribuyente,
    create_vehiculo_motocicleta,
    create_datos_transporte_tercerizado,

    # === VALIDATORS BUSINESS RULES ===
    validate_documento_asociado_coherencia,
    validate_afe_business_rules,
    validate_transporte_business_rules,

    # === INFORMACIÓN DEL MÓDULO ===
    MODULE_INFO as AUXILIARY_MODULE_INFO
)

# ===============================================
# IMPORTS DE TIPOS DE DOCUMENTOS PRINCIPALES
# ===============================================

from .document_types import (
    # === MODELOS DE DOCUMENTOS PRINCIPALES ===
    FacturaSimple,
    NotaCreditoElectronica,
    NotaDebitoElectronica,
    AutofacturaElectronica,
    NotaRemisionElectronica,

    # === FUNCIONES DE EJEMPLO ESPECÍFICAS ===
    # Nota: Estas sobrescriben las del base.py con ejemplos más completos
    create_factura_ejemplo,
    create_nota_credito_ejemplo,
    create_nota_debito_ejemplo,
    create_autofactura_ejemplo,
    create_nota_remision_ejemplo
)

# ===============================================
# COMPATIBILIDAD BACKWARD Y ALIASES
# ===============================================

# Para mantener compatibilidad con código existente
# que pueda usar nombres alternativos

# Alias de modelos principales
FacturaElectronica = FacturaSimple
NotaCredito = NotaCreditoElectronica
NotaDebito = NotaDebitoElectronica
Autofactura = AutofacturaElectronica
NotaRemision = NotaRemisionElectronica

# Alias de helpers comunes
crear_contribuyente = create_contribuyente_ejemplo
crear_item = create_item_ejemplo
crear_factura = create_factura_ejemplo

# ===============================================
# MAPEO DE TIPOS DE DOCUMENTO
# ===============================================

# Mapeo código SIFEN -> Clase del modelo
TIPOS_DOCUMENTO_CLASSES = {
    "1": FacturaSimple,          # Factura Electrónica
    "4": AutofacturaElectronica,  # Autofactura Electrónica
    "5": NotaCreditoElectronica,  # Nota de Crédito Electrónica
    "6": NotaDebitoElectronica,  # Nota de Débito Electrónica
    "7": NotaRemisionElectronica  # Nota de Remisión Electrónica
}

# Mapeo inverso: Clase -> código SIFEN
CLASSES_TIPO_DOCUMENTO = {
    FacturaSimple: "1",
    AutofacturaElectronica: "4",
    NotaCreditoElectronica: "5",
    NotaDebitoElectronica: "6",
    NotaRemisionElectronica: "7"
}

# Descripción de tipos de documento
TIPOS_DOCUMENTO_DESCRIPCION = {
    "1": "Factura Electrónica",
    "4": "Autofactura Electrónica",
    "5": "Nota de Crédito Electrónica",
    "6": "Nota de Débito Electrónica",
    "7": "Nota de Remisión Electrónica"
}

# ===============================================
# FUNCIONES DE UTILIDAD DEL MÓDULO
# ===============================================


def get_model_class(tipo_documento: str):
    """
    Obtiene la clase del modelo según el tipo de documento SIFEN

    Args:
        tipo_documento: Código de tipo documento ("1", "4", "5", "6", "7")

    Returns:
        Class: Clase del modelo correspondiente

    Raises:
        ValueError: Si el tipo de documento no es válido

    Example:
        >>> ModelClass = get_model_class("1")  # FacturaSimple
        >>> factura = ModelClass(...)
    """
    if tipo_documento not in TIPOS_DOCUMENTO_CLASSES:
        tipos_validos = list(TIPOS_DOCUMENTO_CLASSES.keys())
        raise ValueError(
            f"Tipo documento '{tipo_documento}' inválido. Válidos: {tipos_validos}")

    return TIPOS_DOCUMENTO_CLASSES[tipo_documento]


def get_document_type_code(model_instance) -> str:
    """
    Obtiene el código de tipo documento desde una instancia del modelo

    Args:
        model_instance: Instancia de cualquier modelo de documento

    Returns:
        str: Código de tipo documento SIFEN

    Raises:
        ValueError: Si la instancia no es un modelo válido

    Example:
        >>> factura = FacturaSimple(...)
        >>> codigo = get_document_type_code(factura)  # "1"
    """
    model_class = type(model_instance)
    if model_class not in CLASSES_TIPO_DOCUMENTO:
        clases_validas = list(CLASSES_TIPO_DOCUMENTO.keys())
        raise ValueError(
            f"Clase '{model_class.__name__}' no es un documento válido. Válidas: {[c.__name__ for c in clases_validas]}")

    return CLASSES_TIPO_DOCUMENTO[model_class]


def get_document_description(tipo_documento: str) -> str:
    """
    Obtiene la descripción del tipo de documento

    Args:
        tipo_documento: Código de tipo documento

    Returns:
        str: Descripción del tipo de documento

    Example:
        >>> desc = get_document_description("1")  # "Factura Electrónica"
    """
    return TIPOS_DOCUMENTO_DESCRIPCION.get(tipo_documento, f"Tipo {tipo_documento} desconocido")


def list_available_models() -> dict:
    """
    Lista todos los modelos disponibles con información

    Returns:
        dict: Información de todos los modelos disponibles
    """
    return {
        "tipos_documento": {
            codigo: {
                "clase": clase.__name__,
                "descripcion": get_document_description(codigo),
                "modulo": clase.__module__
            }
            for codigo, clase in TIPOS_DOCUMENTO_CLASSES.items()
        },
        "modelos_base": [
            {"nombre": "Contribuyente", "descripcion": "Emisor/receptor de documentos"},
            {"nombre": "ItemFactura", "descripcion": "Items/productos de documentos"}
        ],
        "modelos_auxiliares": [
            {"nombre": "DocumentoAsociado",
                "descripcion": "Referencias a documentos (NCE/NDE)"},
            {"nombre": "ContribuyenteExtranjero",
                "descripcion": "Vendedor extranjero (AFE)"},
            {"nombre": "DatosAFE", "descripcion": "Sección específica autofactura"},
            {"nombre": "DatosTransporte",
                "descripcion": "Información transporte (NRE)"},
            {"nombre": "DatosVehiculo",
                "descripcion": "Vehículos de transporte (NRE)"}
        ]
    }


def create_example_document(tipo_documento: str, **kwargs):
    """
    Crea un documento de ejemplo del tipo especificado

    Args:
        tipo_documento: Código de tipo documento ("1", "4", "5", "6", "7")
        **kwargs: Parámetros adicionales para el documento

    Returns:
        Instancia del documento de ejemplo

    Raises:
        ValueError: Si el tipo de documento no es válido

    Example:
        >>> factura = create_example_document("1")  # FacturaSimple de ejemplo
        >>> nce = create_example_document("5")     # NotaCreditoElectronica de ejemplo
    """
    # Funciones de ejemplo disponibles
    example_functions = {
        "1": create_factura_ejemplo,
        "4": create_autofactura_ejemplo,
        "5": create_nota_credito_ejemplo,
        "6": create_nota_debito_ejemplo,
        "7": create_nota_remision_ejemplo
    }

    if tipo_documento not in example_functions:
        tipos_validos = list(example_functions.keys())
        raise ValueError(
            f"Tipo documento '{tipo_documento}' inválido. Válidos: {tipos_validos}")

    return example_functions[tipo_documento]()


def validate_model_consistency(model_instance) -> tuple[bool, list[str]]:
    """
    Valida consistencia interna de un modelo de documento

    Args:
        model_instance: Instancia de cualquier modelo de documento

    Returns:
        tuple[bool, list[str]]: (es_válido, lista_errores)

    Example:
        >>> factura = FacturaSimple(...)
        >>> is_valid, errors = validate_model_consistency(factura)
        >>> if not is_valid:
        ...     print(f"Errores: {errors}")
    """
    errors = []

    try:
        # Validar que sea una instancia válida
        if not hasattr(model_instance, 'model_validate'):
            errors.append(
                f"'{type(model_instance).__name__}' no es un modelo Pydantic válido")
            return False, errors

        # Re-validar el modelo para asegurar consistencia
        model_instance.model_validate(model_instance.model_dump())

        # Validaciones específicas por tipo
        if isinstance(model_instance, (NotaCreditoElectronica, NotaDebitoElectronica)):
            # Validar documento asociado
            if hasattr(model_instance, 'documento_asociado'):
                doc_type = get_document_type_code(model_instance)
                try:
                    validate_documento_asociado_coherencia(
                        model_instance.documento_asociado, doc_type)
                except ValueError as e:
                    errors.append(f"Error documento asociado: {str(e)}")

        elif isinstance(model_instance, AutofacturaElectronica):
            # Validar reglas AFE
            if hasattr(model_instance, 'datos_afe'):
                try:
                    validate_afe_business_rules(model_instance.datos_afe)
                except ValueError as e:
                    errors.append(f"Error reglas AFE: {str(e)}")

        elif isinstance(model_instance, NotaRemisionElectronica):
            # Validar reglas transporte
            if hasattr(model_instance, 'datos_transporte'):
                try:
                    validate_transporte_business_rules(
                        model_instance.datos_transporte)
                except ValueError as e:
                    errors.append(f"Error reglas transporte: {str(e)}")

    except Exception as e:
        errors.append(f"Error validando modelo: {str(e)}")

    return len(errors) == 0, errors


# ===============================================
# INFORMACIÓN DEL MÓDULO CONSOLIDADA
# ===============================================

MODELS_MODULE_INFO = {
    "name": "models",
    "description": "Módulo unificado de modelos SIFEN v150",
    "version": "1.0.0",
    "architecture": "modular",
    "submodules": {
        "base": BASE_MODULE_INFO,
        "auxiliary": AUXILIARY_MODULE_INFO,
        "document_types": {
            "name": "document_types",
            "description": "Documentos principales por tipo",
            "models": 5,
            "examples": 5
        }
    },
    "total_models": 10,
    "total_validators": 7,
    "total_constants": 10,
    "total_helpers": 17,
    "supported_documents": list(TIPOS_DOCUMENTO_DESCRIPCION.values()),
    "compatibility": "backward_compatible"
}

# ===============================================
# EXPORTACIONES PRINCIPALES
# ===============================================

__all__ = [
    # === MODELOS BASE REUTILIZABLES ===
    "Contribuyente",
    "ItemFactura",

    # === MODELOS AUXILIARES ESPECÍFICOS ===
    "DocumentoAsociado",
    "ContribuyenteExtranjero",
    "DatosAFE",
    "DatosVehiculo",
    "DatosTransporte",

    # === MODELOS DE DOCUMENTOS PRINCIPALES ===
    "FacturaSimple",
    "NotaCreditoElectronica",
    "NotaDebitoElectronica",
    "AutofacturaElectronica",
    "NotaRemisionElectronica",

    # === ALIASES BACKWARD COMPATIBILITY ===
    "FacturaElectronica",  # Alias de FacturaSimple
    "NotaCredito",         # Alias de NotaCreditoElectronica
    "NotaDebito",          # Alias de NotaDebitoElectronica
    "Autofactura",         # Alias de AutofacturaElectronica
    "NotaRemision",        # Alias de NotaRemisionElectronica

    # === VALIDADORES REUTILIZABLES ===
    "validate_ruc_paraguayo",
    "validate_cdc_format",
    "validate_email_format",
    "validate_departamento_paraguay",
    "validate_documento_asociado_coherencia",
    "validate_afe_business_rules",
    "validate_transporte_business_rules",

    # === CONSTANTES PRINCIPALES ===
    "DEPARTAMENTOS_PARAGUAY",
    "IVA_RATES_PARAGUAY",
    "MONEDAS_SIFEN",
    "TIPOS_DOCUMENTO_REF_VALIDOS",
    "TIPOS_DOCUMENTO_CLASSES",
    "TIPOS_DOCUMENTO_DESCRIPCION",

    # === HELPERS PARA TESTING (BASE) ===
    "create_contribuyente_ejemplo",
    "create_item_ejemplo",

    # === HELPERS AUXILIARES ===
    "create_documento_asociado_ejemplo",
    "create_contribuyente_extranjero_ejemplo",
    "create_datos_afe_ejemplo",
    "create_vehiculo_ejemplo",
    "create_datos_transporte_ejemplo",

    # === FACTORIES ESPECÍFICAS ===
    "create_documento_asociado_factura",
    "create_contribuyente_no_contribuyente",
    "create_datos_afe_no_contribuyente",
    "create_vehiculo_motocicleta",
    "create_datos_transporte_tercerizado",

    # === HELPERS PARA DOCUMENTOS COMPLETOS ===
    "create_factura_ejemplo",
    "create_nota_credito_ejemplo",
    "create_nota_debito_ejemplo",
    "create_autofactura_ejemplo",
    "create_nota_remision_ejemplo",

    # === ALIASES HELPERS ===
    "crear_contribuyente",     # Alias de create_contribuyente_ejemplo
    "crear_item",              # Alias de create_item_ejemplo
    "crear_factura",           # Alias de create_factura_ejemplo

    # === FUNCIONES DE UTILIDAD DEL MÓDULO ===
    "get_model_class",
    "get_document_type_code",
    "get_document_description",
    "list_available_models",
    "create_example_document",
    "validate_model_consistency",

    # === INFORMACIÓN DEL MÓDULO ===
    "MODELS_MODULE_INFO"
]

# ===============================================
# VERIFICACIÓN DE IMPORTACIONES AL CARGAR
# ===============================================


def _verify_module_integrity():
    """Verifica que todas las importaciones sean correctas"""
    try:
        # Verificar que todos los modelos principales estén disponibles
        required_models = [
            Contribuyente, ItemFactura, DocumentoAsociado,
            FacturaSimple, NotaCreditoElectronica, NotaDebitoElectronica,
            AutofacturaElectronica, NotaRemisionElectronica
        ]

        for model in required_models:
            if not hasattr(model, 'model_validate'):
                raise ImportError(f"Modelo {model.__name__} no es válido")

        # Verificar funciones de ejemplo
        test_docs = [
            create_factura_ejemplo(),
            create_nota_credito_ejemplo(),
            create_autofactura_ejemplo()
        ]

        for doc in test_docs:
            if not hasattr(doc, 'model_dump'):
                raise ImportError(
                    f"Documento de ejemplo {type(doc).__name__} no es válido")

        return True

    except Exception as e:
        print(f"⚠️ Advertencia: Error en verificación del módulo models: {e}")
        return False


# Ejecutar verificación al importar (solo en desarrollo)
if os.getenv('ENVIRONMENT') != 'production':
    _verify_module_integrity()

# ===============================================
# METADATA PARA __init__.py PRINCIPAL
# ===============================================

# Para que el __init__.py principal pueda importar información del módulo
__version__ = "1.0.0"
__author__ = "Sistema SIFEN Paraguay"
__description__ = "Modelos unificados para documentos electrónicos SIFEN v150"
__compatibility__ = "backward_compatible"
