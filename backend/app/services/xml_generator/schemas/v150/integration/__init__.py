
"""
Módulo de integración SIFEN v150
Capa de compatibilidad híbrida
"""

from .compatibility_layer import (
    CompatibilityLayer,
    quick_process_document,
    batch_process_documents,
    analyze_document_compatibility
)

__all__ = [
    'CompatibilityLayer',
    'quick_process_document',
    'batch_process_documents',
    'analyze_document_compatibility'
]
