# ===============================================
# ARCHIVO: backend/app/repositories/documento/document_relations_mixin.py
# PROPÓSITO: Mixin para gestión de relaciones entre documentos SIFEN
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para gestión de relaciones entre documentos SIFEN.

Este módulo implementa funcionalidades transversales para el manejo de relaciones
entre diferentes tipos de documentos electrónicos, incluyendo:
- Gestión de documentos originales y derivados
- Búsqueda de documentos relacionados (NCE/NDE de facturas)
- Validación de cadenas de documentos
- Análisis de impacto en documentos relacionados
- Historial completo de modificaciones
- Integración total con SIFEN v150

Características principales:
- Relaciones bidireccionales entre documentos
- Validación de coherencia en cadenas de documentos
- Búsquedas optimizadas de documentos relacionados
- Análisis de impacto financiero
- Trazabilidad completa de modificaciones
- Estadísticas de relaciones por cliente/empresa

Clase principal:
- DocumentRelationsMixin: Mixin transversal para gestión de relaciones
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, text, desc, asc, case
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenValidationError,
    SifenEntityNotFoundError,
    SifenBusinessLogicError,
    handle_database_exception
)
from app.models.documento import (
    Documento,
    FacturaElectronica,
    NotaCreditoElectronica,
    NotaDebitoElectronica,
    TipoDocumentoSifenEnum,
    EstadoDocumentoSifenEnum
)
from app.schemas.documento import DocumentoBaseDTO
from .utils import (
    normalize_cdc,
    log_repository_operation,
    log_performance_metric,
    handle_repository_error,
    calculate_percentage,
    get_default_page_size,
    get_max_page_size
)

logger = get_logger(__name__)

# ===============================================
# TIPOS DE RELACIONES
# ===============================================

# Tipos de relaciones entre documentos
TIPOS_RELACION = {
    "origina": "Documento original",
    "credita": "Nota de crédito",
    "debita": "Nota de débito",
    "referencia": "Documento de referencia",
    "anula": "Documento de anulación",
    "corrige": "Documento de corrección"
}

# Estados que permiten crear documentos relacionados
ESTADOS_PERMITE_RELACION = [
    EstadoDocumentoSifenEnum.APROBADO.value,
    EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value
]

# ===============================================
# MIXIN PRINCIPAL
# ===============================================


class DocumentRelationsMixin:
    """
    Mixin para gestión de relaciones entre documentos SIFEN.

    Proporciona métodos transversales para el manejo de relaciones entre
    diferentes tipos de documentos electrónicos:
    - Búsqueda de documentos relacionados
    - Validación de cadenas de documentos
    - Análisis de impacto financiero
    - Gestión de documentos originales y derivados
    - Trazabilidad completa de modificaciones

    Este mixin debe ser usado junto con DocumentoRepositoryBase para
    obtener funcionalidad completa de gestión de documentos.

    Example:
        ```python
        class DocumentoRepository(
            DocumentoRepositoryBase,
            DocumentRelationsMixin,
            # otros mixins...
        ):
            pass

        repo = DocumentoRepository(db)
        relacionados = repo.get_document_relations(documento_id=123)
        ```
    """

    db: Session
    model: type

    # ===============================================
    # MÉTODOS PRINCIPALES DE RELACIONES
    # ===============================================

    def get_document_relations(self,
                               documento_id: int,
                               include_details: bool = True,
                               include_amounts: bool = True) -> Dict[str, Any]:
        """
        Obtiene todas las relaciones de un documento específico.

        Este método es el punto de entrada principal para obtener el grafo completo
        de relaciones de un documento, incluyendo documentos originales y derivados.

        Args:
            documento_id: ID del documento base
            include_details: Incluir detalles completos de documentos relacionados
            include_amounts: Incluir análisis de montos e impacto financiero

        Returns:
            Dict[str, Any]: Estructura completa de relaciones del documento

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenDatabaseError: Si hay error en la consulta

        Example:
            ```python
            relaciones = repo.get_document_relations(
                documento_id=123,
                include_details=True,
                include_amounts=True
            )

            print(f"Documento original: {relaciones['documento_base']['numero_completo']}")
            print(f"Notas de crédito: {len(relaciones['notas_credito'])}")
            print(f"Impacto neto: {relaciones['analisis_financiero']['impacto_neto']}")
            ```
        """
        start_time = datetime.now()

        try:
            # 1. Obtener documento base
            documento_base = getattr(self, 'get_by_id')(documento_id)
            if not documento_base:
                raise SifenEntityNotFoundError("Documento", documento_id)

            # 2. Obtener documento original si es NCE/NDE
            documento_original = None
            if getattr(documento_base, 'tipo_documento', '') in ["5", "6"]:
                documento_original = self.get_original_document(documento_id)

            # 3. Obtener notas de crédito y débito
            notas_credito = self.get_related_credits_debits(
                documento_id, tipo="credito")
            notas_debito = self.get_related_credits_debits(
                documento_id, tipo="debito")

            # 4. Buscar documentos que referencian a este
            documentos_referenciadores = self._get_referencing_documents(
                documento_id)

            # 5. Análisis financiero si se solicita
            analisis_financiero = {}
            if include_amounts:
                analisis_financiero = self._calculate_financial_impact(
                    documento_base, notas_credito, notas_debito)

            # 6. Construir respuesta
            relaciones = {
                "documento_base": self._format_document_summary(documento_base, include_details),
                "documento_original": self._format_document_summary(documento_original, include_details) if documento_original else None,
                "notas_credito": [self._format_document_summary(nc, include_details) for nc in notas_credito],
                "notas_debito": [self._format_document_summary(nd, include_details) for nd in notas_debito],
                "documentos_referenciadores": [self._format_document_summary(dr, include_details) for dr in documentos_referenciadores],
                "resumen": {
                    "total_notas_credito": len(notas_credito),
                    "total_notas_debito": len(notas_debito),
                    "total_documentos_relacionados": len(notas_credito) + len(notas_debito) + len(documentos_referenciadores),
                    "tiene_documento_original": documento_original is not None
                },
                "analisis_financiero": analisis_financiero,
                "metadatos": {
                    "generado_en": datetime.now().isoformat(),
                    "tiempo_procesamiento": (datetime.now() - start_time).total_seconds()
                }
            }

            # 7. Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("get_document_relations", duration, 1)

            log_repository_operation("get_document_relations", "Documento", documento_id, {
                "notas_credito": len(notas_credito),
                "notas_debito": len(notas_debito),
                "total_relacionados": relaciones["resumen"]["total_documentos_relacionados"]
            })

            return relaciones

        except (SifenEntityNotFoundError, SifenValidationError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_document_relations", "Documento", documento_id)
            raise handle_database_exception(e, "get_document_relations")

    def get_original_document(self, documento_id: int) -> Optional[Documento]:
        """
        Obtiene el documento original para NCE/NDE.

        Este método busca el documento original al que hace referencia
        una nota de crédito o débito electrónica.

        Args:
            documento_id: ID de la nota de crédito/débito

        Returns:
            Optional[Documento]: Documento original encontrado o None

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenValidationError: Si el documento no es NCE/NDE

        Example:
            ```python
            # Para una nota de crédito
            original = repo.get_original_document(nota_credito_id=456)
            if original:
                print(f"Factura original: {original.numero_completo}")
            ```
        """
        start_time = datetime.now()

        try:
            # Obtener el documento
            documento = getattr(self, 'get_by_id')(documento_id)
            if not documento:
                raise SifenEntityNotFoundError("Documento", documento_id)

            # Verificar que sea NCE o NDE
            tipo_documento = getattr(documento, 'tipo_documento', '')
            if tipo_documento not in ["5", "6"]:
                raise SifenValidationError(
                    f"Documento tipo {tipo_documento} no tiene documento original. Solo NCE (5) y NDE (6) tienen documentos originales.",
                    field="tipo_documento",
                    value=tipo_documento
                )

            # Obtener CDC del documento original
            documento_original_cdc = getattr(
                documento, 'documento_original_cdc', None)
            if not documento_original_cdc:
                logger.warning(
                    "DOCUMENTO_SIN_CDC_ORIGINAL",
                    extra={
                        "modulo": "document_relations",
                        "documento_id": documento_id,
                        "tipo_documento": tipo_documento
                    }
                )
                return None

            # Buscar documento original por CDC
            documento_original = getattr(
                self, 'get_by_cdc')(documento_original_cdc)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_original_document", duration, 1 if documento_original else 0)

            return documento_original

        except (SifenEntityNotFoundError, SifenValidationError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_original_document", "Documento", documento_id)
            raise handle_database_exception(e, "get_original_document")

    def get_related_credits_debits(self,
                                   documento_id: int,
                                   tipo: str = "ambos",
                                   estados: Optional[List[str]] = None,
                                   fecha_desde: Optional[date] = None,
                                   fecha_hasta: Optional[date] = None,
                                   limit: Optional[int] = None) -> List[Documento]:
        """
        Obtiene notas de crédito y/o débito relacionadas con un documento.

        Busca todas las NCE y/o NDE que referencian al documento especificado
        como documento original.

        Args:
            documento_id: ID del documento original
            tipo: Tipo de notas a buscar ("credito", "debito", "ambos")
            estados: Lista de estados a incluir (opcional)
            fecha_desde: Fecha inicio del rango (opcional)
            fecha_hasta: Fecha fin del rango (opcional)
            limit: Número máximo de resultados

        Returns:
            List[Documento]: Lista de notas de crédito/débito relacionadas

        Raises:
            SifenEntityNotFoundError: Si el documento no existe
            SifenValidationError: Si los parámetros no son válidos

        Example:
            ```python
            # Obtener solo notas de crédito aprobadas
            notas_credito = repo.get_related_credits_debits(
                documento_id=123,
                tipo="credito",
                estados=["aprobado", "aprobado_observacion"]
            )

            # Obtener todas las notas del último mes
            todas_notas = repo.get_related_credits_debits(
                documento_id=123,
                tipo="ambos",
                fecha_desde=date.today() - timedelta(days=30)
            )
            ```
        """
        start_time = datetime.now()

        try:
            # Validar parámetros
            if tipo not in ["credito", "debito", "ambos"]:
                raise SifenValidationError(
                    "Tipo debe ser 'credito', 'debito' o 'ambos'",
                    field="tipo",
                    value=tipo
                )

            # Obtener documento base para validar que existe
            documento_base = getattr(self, 'get_by_id')(documento_id)
            if not documento_base:
                raise SifenEntityNotFoundError("Documento", documento_id)

            # Obtener CDC del documento base
            cdc_documento = getattr(documento_base, 'cdc', None)
            if not cdc_documento:
                logger.warning(
                    "DOCUMENTO_SIN_CDC",
                    extra={
                        "modulo": "document_relations",
                        "documento_id": documento_id
                    }
                )
                return []

            # Determinar tipos de documento a buscar
            tipos_busqueda = []
            if tipo in ["credito", "ambos"]:
                tipos_busqueda.append("5")  # NCE
            if tipo in ["debito", "ambos"]:
                tipos_busqueda.append("6")  # NDE

            # Construir query
            query = self.db.query(self.model).filter(
                and_(
                    self.model.tipo_documento.in_(tipos_busqueda),
                    self.model.documento_original_cdc == cdc_documento
                )
            )

            # Aplicar filtros opcionales
            if estados:
                query = query.filter(text("estado IN :estados")).params(
                    estados=tuple(estados))

            if fecha_desde:
                query = query.filter(self.model.fecha_emision >= fecha_desde)

            if fecha_hasta:
                query = query.filter(self.model.fecha_emision <= fecha_hasta)

            # Aplicar límite
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            # Ejecutar query con ordenamiento
            documentos_relacionados = query.order_by(
                desc(self.model.fecha_emision)
            ).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_related_credits_debits", duration, len(documentos_relacionados))

            return documentos_relacionados

        except (SifenEntityNotFoundError, SifenValidationError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "get_related_credits_debits", "Documento", documento_id)
            raise handle_database_exception(e, "get_related_credits_debits")

    # ===============================================
    # MÉTODOS DE ANÁLISIS Y VALIDACIÓN
    # ===============================================

    def validate_document_chain(self, documento_id: int) -> Dict[str, Any]:
        """
        Valida la coherencia de la cadena de documentos relacionados.

        Verifica que la cadena de documentos (original → NCE/NDE) sea coherente
        en términos de montos, fechas, estados y reglas de negocio.

        Args:
            documento_id: ID del documento a validar

        Returns:
            Dict[str, Any]: Resultado de validación de la cadena

        Example:
            ```python
            validacion = repo.validate_document_chain(documento_id=123)

            if validacion["es_valida"]:
                print("Cadena de documentos válida")
            else:
                print(f"Errores: {validacion['errores']}")
            ```
        """
        try:
            # Obtener relaciones completas
            relaciones = self.get_document_relations(
                documento_id, include_amounts=True)

            validacion = {
                "es_valida": True,
                "errores": [],
                "advertencias": [],
                "resumen_validacion": {}
            }

            documento_base = relaciones["documento_base"]
            notas_credito = relaciones["notas_credito"]
            notas_debito = relaciones["notas_debito"]

            # 1. Validar estados de documentos
            self._validate_document_states(
                documento_base, notas_credito, notas_debito, validacion)

            # 2. Validar coherencia de fechas
            self._validate_date_consistency(
                documento_base, notas_credito, notas_debito, validacion)

            # 3. Validar coherencia de montos
            if relaciones["analisis_financiero"]:
                self._validate_amount_consistency(
                    relaciones["analisis_financiero"], validacion)

            # 4. Validar reglas de negocio específicas
            self._validate_business_rules(
                documento_base, notas_credito, notas_debito, validacion)

            # 5. Resumen final
            validacion["resumen_validacion"] = {
                "total_errores": len(validacion["errores"]),
                "total_advertencias": len(validacion["advertencias"]),
                "documentos_validados": 1 + len(notas_credito) + len(notas_debito),
                "fecha_validacion": datetime.now().isoformat()
            }

            validacion["es_valida"] = len(validacion["errores"]) == 0

            return validacion

        except Exception as e:
            handle_repository_error(
                e, "validate_document_chain", "Documento", documento_id)
            raise handle_database_exception(e, "validate_document_chain")

    def get_document_impact_analysis(self,
                                     documento_id: int,
                                     include_projections: bool = False) -> Dict[str, Any]:
        """
        Analiza el impacto financiero completo de un documento y sus relaciones.

        Calcula el impacto neto de un documento considerando todas sus
        notas de crédito y débito asociadas.

        Args:
            documento_id: ID del documento a analizar
            include_projections: Incluir proyecciones y tendencias

        Returns:
            Dict[str, Any]: Análisis detallado de impacto financiero

        Example:
            ```python
            impacto = repo.get_document_impact_analysis(
                documento_id=123,
                include_projections=True
            )

            print(f"Impacto neto: {impacto['impacto_neto']}")
            print(f"Porcentaje creditado: {impacto['porcentaje_creditado']}%")
            ```
        """
        try:
            # Obtener relaciones con análisis financiero
            relaciones = self.get_document_relations(
                documento_id, include_amounts=True)

            if not relaciones["analisis_financiero"]:
                raise SifenValidationError(
                    "No se pudo calcular análisis financiero para el documento",
                    field="documento_id",
                    value=documento_id
                )

            analisis_base = relaciones["analisis_financiero"]
            documento_base = relaciones["documento_base"]

            # Análisis extendido
            impacto = {
                **analisis_base,
                "documento_base": {
                    "id": documento_base["id"],
                    "numero_completo": documento_base["numero_completo"],
                    "fecha_emision": documento_base["fecha_emision"],
                    "monto_original": float(documento_base.get("total_general", 0))
                },
                "detalle_movimientos": [],
                "indicadores": {},
                "tendencias": {} if include_projections else None
            }

            # Detalle de movimientos
            for nc in relaciones["notas_credito"]:
                impacto["detalle_movimientos"].append({
                    "tipo": "credito",
                    "documento_id": nc["id"],
                    "numero_completo": nc["numero_completo"],
                    "fecha": nc["fecha_emision"],
                    "monto": float(nc.get("total_general", 0)),
                    "estado": nc["estado"]
                })

            for nd in relaciones["notas_debito"]:
                impacto["detalle_movimientos"].append({
                    "tipo": "debito",
                    "documento_id": nd["id"],
                    "numero_completo": nd["numero_completo"],
                    "fecha": nd["fecha_emision"],
                    "monto": float(nd.get("total_general", 0)),
                    "estado": nd["estado"]
                })

            # Ordenar movimientos por fecha
            impacto["detalle_movimientos"].sort(key=lambda x: x["fecha"])

            # Indicadores adicionales
            monto_original = impacto["documento_base"]["monto_original"]

            impacto["indicadores"] = {
                "frecuencia_modificaciones": len(impacto["detalle_movimientos"]),
                "tiempo_desde_emision": (date.today() - datetime.fromisoformat(documento_base["fecha_emision"]).date()).days,
                "promedio_monto_por_modificacion": abs(impacto["total_ajustes"]) / len(impacto["detalle_movimientos"]) if impacto["detalle_movimientos"] else 0,
                "volatilidad": abs(impacto["total_ajustes"]) / monto_original * 100 if monto_original > 0 else 0
            }

            # Proyecciones si se solicitan
            if include_projections:
                impacto["tendencias"] = self._calculate_impact_trends(impacto)

            return impacto

        except Exception as e:
            handle_repository_error(
                e, "get_document_impact_analysis", "Documento", documento_id)
            raise handle_database_exception(e, "get_document_impact_analysis")

    # ===============================================
    # MÉTODOS DE BÚSQUEDA ESPECIALIZADA
    # ===============================================

    def find_documents_by_relationship_pattern(self,
                                               empresa_id: int,
                                               patron: str,
                                               fecha_desde: Optional[date] = None,
                                               fecha_hasta: Optional[date] = None,
                                               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Busca documentos que siguen un patrón específico de relaciones.

        Args:
            empresa_id: ID de la empresa
            patron: Patrón a buscar ("con_creditos", "con_debitos", "sin_modificaciones", "muy_modificados")
            fecha_desde: Fecha inicio del rango (opcional)
            fecha_hasta: Fecha fin del rango (opcional)
            limit: Número máximo de resultados

        Returns:
            List[Dict[str, Any]]: Lista de documentos que cumplen el patrón

        Example:
            ```python
            # Facturas muy modificadas (muchas NCE/NDE)
            muy_modificadas = repo.find_documents_by_relationship_pattern(
                empresa_id=1,
                patron="muy_modificados",
                fecha_desde=date(2025, 1, 1)
            )
            ```
        """
        try:
            patrones_validos = ["con_creditos", "con_debitos",
                                "sin_modificaciones", "muy_modificados"]

            if patron not in patrones_validos:
                raise SifenValidationError(
                    f"Patrón debe ser uno de: {patrones_validos}",
                    field="patron",
                    value=patron
                )

            if patron == "con_creditos":
                return self._find_documents_with_credits(empresa_id, fecha_desde, fecha_hasta, limit)
            elif patron == "con_debitos":
                return self._find_documents_with_debits(empresa_id, fecha_desde, fecha_hasta, limit)
            elif patron == "sin_modificaciones":
                return self._find_documents_without_modifications(empresa_id, fecha_desde, fecha_hasta, limit)
            elif patron == "muy_modificados":
                return self._find_heavily_modified_documents(empresa_id, fecha_desde, fecha_hasta, limit)
            else:
                raise SifenValidationError(
                    f"Patrón no implementado: {patron}",
                    field="patron",
                    value=patron
                )
        except Exception as e:
            handle_repository_error(
                e, "find_documents_by_relationship_pattern", "Documento")
            raise handle_database_exception(
                e, "find_documents_by_relationship_pattern")

    def get_relationship_statistics(self,
                                    empresa_id: int,
                                    fecha_desde: Optional[date] = None,
                                    fecha_hasta: Optional[date] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de relaciones entre documentos.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período (opcional)
            fecha_hasta: Fecha fin del período (opcional)

        Returns:
            Dict[str, Any]: Estadísticas detalladas de relaciones

        Example:
            ```python
            stats = repo.get_relationship_statistics(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            ```
        """
        try:
            # Query base para documentos del período
            query = self.db.query(self.model).filter(
                self.model.empresa_id == empresa_id
            )

            if fecha_desde:
                query = query.filter(self.model.fecha_emision >= fecha_desde)
            if fecha_hasta:
                query = query.filter(self.model.fecha_emision <= fecha_hasta)

            documentos = query.all()

            # Calcular estadísticas
            stats = {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None
                },
                "totales": {
                    "total_documentos": len(documentos),
                    "facturas": 0,
                    "notas_credito": 0,
                    "notas_debito": 0,
                    "autofacturas": 0,
                    "notas_remision": 0
                },
                "relaciones": {
                    "documentos_con_creditos": 0,
                    "documentos_con_debitos": 0,
                    "documentos_sin_modificaciones": 0,
                    "documentos_muy_modificados": 0
                },
                "impacto_financiero": {
                    "total_creditos": Decimal("0"),
                    "total_debitos": Decimal("0"),
                    "impacto_neto": Decimal("0")
                },
                "tendencias": {
                    "porcentaje_con_modificaciones": 0.0,
                    "promedio_modificaciones_por_documento": 0.0
                }
            }

            # Contar por tipo de documento
            for doc in documentos:
                tipo = getattr(doc, 'tipo_documento', '')
                if tipo == "1":
                    stats["totales"]["facturas"] += 1
                elif tipo == "4":
                    stats["totales"]["autofacturas"] += 1
                elif tipo == "5":
                    stats["totales"]["notas_credito"] += 1
                elif tipo == "6":
                    stats["totales"]["notas_debito"] += 1
                elif tipo == "7":
                    stats["totales"]["notas_remision"] += 1

            # Análisis de relaciones (simplificado por performance)
            self._analyze_relationship_patterns(documentos, stats)

            return stats

        except Exception as e:
            handle_repository_error(
                e, "get_relationship_statistics", "Documento")
            raise handle_database_exception(e, "get_relationship_statistics")

    def get_document_lineage(self,
                             documento_id: int,
                             max_depth: int = 5) -> Dict[str, Any]:
        """
        Obtiene el linaje completo de un documento (ancestros y descendientes).

        Args:
            documento_id: ID del documento base
            max_depth: Profundidad máxima de búsqueda

        Returns:
            Dict[str, Any]: Árbol completo de linaje del documento

        Example:
            ```python
            linaje = repo.get_document_lineage(documento_id=123, max_depth=3)

            # Estructura jerárquica de documentos relacionados
            print(f"Documento raíz: {linaje['documento_raiz']['numero_completo']}")
            print(f"Niveles de descendencia: {len(linaje['niveles'])}")
            ```
        """
        try:
            linaje = {
                "documento_base": None,
                "documento_raiz": None,
                "niveles": [],
                "resumen": {
                    "total_documentos": 0,
                    "profundidad_maxima": 0,
                    "tipos_documentos": {}
                }
            }

            # Obtener documento base
            documento_base = getattr(self, 'get_by_id')(documento_id)
            if not documento_base:
                raise SifenEntityNotFoundError("Documento", documento_id)

            linaje["documento_base"] = self._format_document_summary(
                documento_base, True)

            # Buscar hacia arriba (documento raíz)
            documento_raiz = self._find_root_document(
                documento_base, max_depth)
            linaje["documento_raiz"] = self._format_document_summary(
                documento_raiz, True)

            # Construir árbol de descendientes desde la raíz
            arbol_descendientes = self._build_descendant_tree(
                documento_raiz, max_depth)
            linaje["niveles"] = arbol_descendientes

            # Calcular estadísticas del linaje
            self._calculate_lineage_stats(linaje)

            return linaje

        except Exception as e:
            handle_repository_error(
                e, "get_document_lineage", "Documento", documento_id)
            raise handle_database_exception(e, "get_document_lineage")

    # ===============================================
    # MÉTODOS DE ANÁLISIS AVANZADO
    # ===============================================

    def analyze_modification_patterns(self,
                                      empresa_id: int,
                                      meses_atras: int = 6) -> Dict[str, Any]:
        """
        Analiza patrones de modificación de documentos.

        Args:
            empresa_id: ID de la empresa
            meses_atras: Número de meses hacia atrás a analizar

        Returns:
            Dict[str, Any]: Análisis de patrones de modificación

        Example:
            ```python
            patrones = repo.analyze_modification_patterns(empresa_id=1, meses_atras=12)

            print(f"Tasa de modificación promedio: {patrones['tasa_modificacion']}%")
            print(f"Cliente más modificaciones: {patrones['clientes_top'][0]}")
            ```
        """
        try:
            # Calcular fechas del análisis
            fecha_fin = date.today()
            fecha_inicio = fecha_fin.replace(
                day=1) - timedelta(days=meses_atras*30)

            # Obtener documentos del período
            documentos = self.db.query(self.model).filter(
                and_(
                    self.model.empresa_id == empresa_id,
                    self.model.fecha_emision >= fecha_inicio,
                    self.model.fecha_emision <= fecha_fin
                )
            ).all()

            analisis = {
                "periodo": {
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": fecha_fin.isoformat(),
                    "meses_analizados": meses_atras
                },
                "resumen": {
                    "total_documentos": len(documentos),
                    "documentos_modificados": 0,
                    "total_modificaciones": 0,
                    "tasa_modificacion": 0.0
                },
                "patrones_temporales": {},
                "patrones_por_tipo": {},
                "clientes_top": [],
                "tendencias": {}
            }

            # Análisis de modificaciones
            modificaciones_por_documento = {}
            modificaciones_por_mes = {}
            modificaciones_por_tipo = {}
            modificaciones_por_cliente = {}

            for doc in documentos:
                doc_id = getattr(doc, 'id', 0)
                tipo = getattr(doc, 'tipo_documento', '')
                cliente_id = getattr(doc, 'cliente_id', 0)
                fecha_emision = getattr(doc, 'fecha_emision', date.today())
                mes_key = fecha_emision.strftime("%Y-%m")

                # Solo contar documentos principales (no NCE/NDE)
                if tipo in ["1", "4", "7"]:  # FE, AFE, NRE
                    # Contar notas de crédito y débito
                    relacionados = self.get_related_credits_debits(
                        doc_id, tipo="ambos")
                    num_modificaciones = len(relacionados)

                    if num_modificaciones > 0:
                        analisis["resumen"]["documentos_modificados"] += 1
                        analisis["resumen"]["total_modificaciones"] += num_modificaciones

                        modificaciones_por_documento[doc_id] = num_modificaciones

                        # Por mes
                        if mes_key not in modificaciones_por_mes:
                            modificaciones_por_mes[mes_key] = 0
                        modificaciones_por_mes[mes_key] += num_modificaciones

                        # Por tipo
                        if tipo not in modificaciones_por_tipo:
                            modificaciones_por_tipo[tipo] = 0
                        modificaciones_por_tipo[tipo] += num_modificaciones

                        # Por cliente
                        if cliente_id not in modificaciones_por_cliente:
                            modificaciones_por_cliente[cliente_id] = 0
                        modificaciones_por_cliente[cliente_id] += num_modificaciones

            # Calcular tasa de modificación
            if len([d for d in documentos if getattr(d, 'tipo_documento', '') in ["1", "4", "7"]]) > 0:
                analisis["resumen"]["tasa_modificacion"] = (
                    analisis["resumen"]["documentos_modificados"] /
                    len([d for d in documentos if getattr(
                        d, 'tipo_documento', '') in ["1", "4", "7"]]) * 100
                )

            # Patrones temporales
            analisis["patrones_temporales"] = modificaciones_por_mes

            # Patrones por tipo
            analisis["patrones_por_tipo"] = {
                tipo: {
                    "modificaciones": count,
                    "descripcion": self._get_tipo_descripcion(tipo)
                }
                for tipo, count in modificaciones_por_tipo.items()
            }

            # Top clientes con más modificaciones
            clientes_ordenados = sorted(
                modificaciones_por_cliente.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            analisis["clientes_top"] = [
                {"cliente_id": cliente_id, "modificaciones": count}
                for cliente_id, count in clientes_ordenados
            ]

            # Tendencias
            analisis["tendencias"] = {
                "promedio_modificaciones_por_documento": (
                    analisis["resumen"]["total_modificaciones"] /
                    analisis["resumen"]["documentos_modificados"]
                ) if analisis["resumen"]["documentos_modificados"] > 0 else 0,
                "mes_mas_modificaciones": max(modificaciones_por_mes.items(), key=lambda x: x[1])[0] if modificaciones_por_mes else None
            }

            return analisis

        except Exception as e:
            handle_repository_error(
                e, "analyze_modification_patterns", "Documento")
            raise handle_database_exception(e, "analyze_modification_patterns")

    def get_complex_relationship_report(self,
                                        empresa_id: int,
                                        include_financial_impact: bool = True) -> Dict[str, Any]:
        """
        Genera reporte completo de relaciones complejas entre documentos.

        Args:
            empresa_id: ID de la empresa
            include_financial_impact: Incluir análisis de impacto financiero

        Returns:
            Dict[str, Any]: Reporte completo de relaciones

        Example:
            ```python
            reporte = repo.get_complex_relationship_report(
                empresa_id=1,
                include_financial_impact=True
            )
            ```
        """
        try:
            reporte = {
                "empresa_id": empresa_id,
                "fecha_generacion": datetime.now().isoformat(),
                "resumen_ejecutivo": {},
                "relaciones_complejas": [],
                "anomalias_detectadas": [],
                "impacto_financiero": {} if include_financial_impact else None,
                "recomendaciones": []
            }

            # Buscar documentos con patrones complejos
            documentos_complejos = self._identify_complex_relationships(
                empresa_id)

            # Analizar cada documento complejo
            for doc_info in documentos_complejos:
                analisis_doc = self.get_document_relations(
                    doc_info["id"], include_amounts=True)

                if self._is_complex_relationship(analisis_doc):
                    reporte["relaciones_complejas"].append({
                        "documento": doc_info,
                        "analisis": analisis_doc,
                        "complejidad_score": self._calculate_complexity_score(analisis_doc)
                    })

            # Detectar anomalías
            reporte["anomalias_detectadas"] = self._detect_relationship_anomalies(
                documentos_complejos)

            # Resumen ejecutivo
            reporte["resumen_ejecutivo"] = {
                "total_documentos_analizados": len(documentos_complejos),
                "relaciones_complejas_detectadas": len(reporte["relaciones_complejas"]),
                "anomalias_detectadas": len(reporte["anomalias_detectadas"]),
                "nivel_complejidad_promedio": self._calculate_average_complexity(reporte["relaciones_complejas"])
            }

            # Impacto financiero si se solicita
            if include_financial_impact:
                reporte["impacto_financiero"] = self._calculate_total_financial_impact(
                    reporte["relaciones_complejas"])

            # Generar recomendaciones
            reporte["recomendaciones"] = self._generate_relationship_recommendations(
                reporte)

            return reporte

        except Exception as e:
            handle_repository_error(
                e, "get_complex_relationship_report", "Documento")
            raise handle_database_exception(
                e, "get_complex_relationship_report")

    # ===============================================
    # HELPERS INTERNOS
    # ===============================================

    def _get_referencing_documents(self, documento_id: int) -> List[Documento]:
        """
        Obtiene documentos que referencian al documento especificado.

        Args:
            documento_id: ID del documento referenciado

        Returns:
            List[Documento]: Lista de documentos que referencian
        """
        try:
            # Obtener CDC del documento
            documento = getattr(self, 'get_by_id')(documento_id)
            if not documento:
                return []

            cdc = getattr(documento, 'cdc', None)
            if not cdc:
                return []

            # Buscar documentos que referencian este CDC
            documentos_ref = self.db.query(self.model).filter(
                and_(
                    self.model.documento_original_cdc == cdc,
                    self.model.id != documento_id  # Excluir el mismo documento
                )
            ).all()

            return documentos_ref

        except Exception:
            return []

    def _calculate_financial_impact(self,
                                    documento_base: Documento,
                                    notas_credito: List[Documento],
                                    notas_debito: List[Documento]) -> Dict[str, Any]:
        """
        Calcula el impacto financiero neto de un documento.

        Args:
            documento_base: Documento original
            notas_credito: Lista de notas de crédito
            notas_debito: Lista de notas de débito

        Returns:
            Dict[str, Any]: Análisis de impacto financiero
        """
        monto_original = getattr(documento_base, 'total_general', Decimal("0"))

        total_creditos = sum(
            getattr(nc, 'total_general', Decimal("0")) for nc in notas_credito
            if getattr(nc, 'estado', '') in ESTADOS_PERMITE_RELACION
        )

        total_debitos = sum(
            getattr(nd, 'total_general', Decimal("0")) for nd in notas_debito
            if getattr(nd, 'estado', '') in ESTADOS_PERMITE_RELACION
        )

        impacto_neto = monto_original - total_creditos + total_debitos
        total_ajustes = total_debitos - total_creditos

        return {
            "monto_original": float(monto_original),
            "total_creditos": float(total_creditos),
            "total_debitos": float(total_debitos),
            "total_ajustes": float(total_ajustes),
            "impacto_neto": float(impacto_neto),
            "porcentaje_creditado": float((total_creditos / monto_original * 100)) if monto_original > 0 else 0.0,
            "porcentaje_debitado": float((total_debitos / monto_original * 100)) if monto_original > 0 else 0.0,
            "porcentaje_ajuste_neto": float((abs(total_ajustes) / monto_original * 100)) if monto_original > 0 else 0.0
        }

    def _format_document_summary(self, documento: Optional[Documento], include_details: bool = False) -> Optional[Dict[str, Any]]:
        """
        Formatea un documento para respuesta API.

        Args:
            documento: Documento a formatear
            include_details: Incluir detalles adicionales

        Returns:
            Optional[Dict[str, Any]]: Documento formateado o None
        """
        if not documento:
            return None

        summary = {
            "id": getattr(documento, 'id', None),
            "tipo_documento": getattr(documento, 'tipo_documento', ''),
            "numero_completo": getattr(documento, 'numero_completo', ''),
            "cdc": getattr(documento, 'cdc', ''),
            "fecha_emision": getattr(documento, 'fecha_emision', date.today()).isoformat(),
            "total_general": float(getattr(documento, 'total_general', 0)),
            "moneda": getattr(documento, 'moneda', 'PYG'),
            "estado": getattr(documento, 'estado', 'unknown')
        }

        if include_details:
            summary.update({
                "empresa_id": getattr(documento, 'empresa_id', None),
                "cliente_id": getattr(documento, 'cliente_id', None),
                "total_iva": float(getattr(documento, 'total_iva', 0)),
                "numero_protocolo": getattr(documento, 'numero_protocolo', ''),
                "observaciones": getattr(documento, 'observaciones', ''),
                "documento_original_cdc": getattr(documento, 'documento_original_cdc', ''),
                "fecha_creacion": getattr(documento, 'created_at', datetime.now()).isoformat()
            })

        return summary

    def _validate_document_states(self, documento_base: Dict[str, Any],
                                  notas_credito: List[Dict[str, Any]],
                                  notas_debito: List[Dict[str, Any]],
                                  validacion: Dict[str, Any]) -> None:
        """Valida estados de documentos en la cadena."""
        # El documento base debe estar aprobado para tener notas
        if documento_base["estado"] not in ESTADOS_PERMITE_RELACION:
            if notas_credito or notas_debito:
                validacion["errores"].append(
                    f"Documento base en estado '{documento_base['estado']}' no debería tener notas asociadas"
                )

        # Validar estados de notas
        for nc in notas_credito:
            if nc["estado"] not in ["aprobado", "aprobado_observacion", "rechazado", "cancelado"]:
                validacion["advertencias"].append(
                    f"Nota de crédito {nc['numero_completo']} en estado inusual: {nc['estado']}"
                )

        for nd in notas_debito:
            if nd["estado"] not in ["aprobado", "aprobado_observacion", "rechazado", "cancelado"]:
                validacion["advertencias"].append(
                    f"Nota de débito {nd['numero_completo']} en estado inusual: {nd['estado']}"
                )

    def _validate_date_consistency(self, documento_base: Dict[str, Any],
                                   notas_credito: List[Dict[str, Any]],
                                   notas_debito: List[Dict[str, Any]],
                                   validacion: Dict[str, Any]) -> None:
        """Valida coherencia de fechas en la cadena."""
        fecha_base = datetime.fromisoformat(
            documento_base["fecha_emision"]).date()

        # Las notas deben ser posteriores al documento base
        for nc in notas_credito:
            fecha_nc = datetime.fromisoformat(nc["fecha_emision"]).date()
            if fecha_nc < fecha_base:
                validacion["errores"].append(
                    f"Nota de crédito {nc['numero_completo']} anterior al documento base"
                )

        for nd in notas_debito:
            fecha_nd = datetime.fromisoformat(nd["fecha_emision"]).date()
            if fecha_nd < fecha_base:
                validacion["errores"].append(
                    f"Nota de débito {nd['numero_completo']} anterior al documento base"
                )

    def _validate_amount_consistency(self, analisis_financiero: Dict[str, Any],
                                     validacion: Dict[str, Any]) -> None:
        """Valida coherencia de montos."""
        total_creditos = analisis_financiero.get("total_creditos", 0)
        monto_original = analisis_financiero.get("monto_original", 0)

        # Créditos no pueden superar el monto original
        if total_creditos > monto_original:
            validacion["errores"].append(
                f"Total de créditos ({total_creditos}) supera monto original ({monto_original})"
            )

        # Advertencia si créditos son muy altos
        if monto_original > 0 and (total_creditos / monto_original) > 0.8:
            validacion["advertencias"].append(
                f"Alto porcentaje creditado: {(total_creditos/monto_original)*100:.1f}%"
            )

    def _validate_business_rules(self, documento_base: Dict[str, Any],
                                 notas_credito: List[Dict[str, Any]],
                                 notas_debito: List[Dict[str, Any]],
                                 validacion: Dict[str, Any]) -> None:
        """Valida reglas de negocio específicas."""
        # Verificar límites razonables de modificaciones
        total_modificaciones = len(notas_credito) + len(notas_debito)

        if total_modificaciones > 10:
            validacion["advertencias"].append(
                f"Documento con muchas modificaciones ({total_modificaciones}) - revisar proceso"
            )

        # Verificar si hay tanto créditos como débitos (inusual)
        if notas_credito and notas_debito:
            validacion["advertencias"].append(
                "Documento con tanto créditos como débitos - verificar coherencia"
            )

    def _find_documents_with_credits(self, empresa_id: int, fecha_desde: Optional[date],
                                     fecha_hasta: Optional[date], limit: Optional[int]) -> List[Dict[str, Any]]:
        """Busca documentos que tienen notas de crédito."""
        # Subquery para documentos con créditos
        subquery = self.db.query(self.model.documento_original_cdc).filter(
            self.model.tipo_documento == "5"  # NCE
        ).subquery()

        query = self.db.query(self.model).filter(
            and_(
                self.model.empresa_id == empresa_id,
                self.model.cdc.in_(subquery)
            )
        )

        if fecha_desde:
            query = query.filter(self.model.fecha_emision >= fecha_desde)
        if fecha_hasta:
            query = query.filter(self.model.fecha_emision <= fecha_hasta)

        if limit:
            query = query.limit(limit)

        documentos = query.all()
        summaries = [self._format_document_summary(
            doc, True) for doc in documentos]
        return [summary for summary in summaries if summary is not None]

    def _find_documents_with_debits(self, empresa_id: int, fecha_desde: Optional[date],
                                    fecha_hasta: Optional[date], limit: Optional[int]) -> List[Dict[str, Any]]:
        """Busca documentos que tienen notas de débito."""
        # Subquery para documentos con débitos
        subquery = self.db.query(self.model.documento_original_cdc).filter(
            self.model.tipo_documento == "6"  # NDE
        ).subquery()

        query = self.db.query(self.model).filter(
            and_(
                self.model.empresa_id == empresa_id,
                self.model.cdc.in_(subquery)
            )
        )

        if fecha_desde:
            query = query.filter(self.model.fecha_emision >= fecha_desde)
        if fecha_hasta:
            query = query.filter(self.model.fecha_emision <= fecha_hasta)

        if limit:
            query = query.limit(limit)

        documentos = query.all()
        summaries = [self._format_document_summary(
            doc, True) for doc in documentos]
        return [summary for summary in summaries if summary is not None]

    def _find_documents_without_modifications(self, empresa_id: int, fecha_desde: Optional[date],
                                              fecha_hasta: Optional[date], limit: Optional[int]) -> List[Dict[str, Any]]:
        """Busca documentos sin modificaciones (sin NCE/NDE)."""
        # Subquery para documentos con modificaciones
        subquery = self.db.query(self.model.documento_original_cdc).filter(
            self.model.tipo_documento.in_(["5", "6"])  # NCE y NDE
        ).subquery()

        query = self.db.query(self.model).filter(
            and_(
                self.model.empresa_id == empresa_id,
                self.model.tipo_documento.in_(["1", "4"]),  # Solo FE y AFE
                ~self.model.cdc.in_(subquery)  # Sin modificaciones
            )
        )

        if fecha_desde:
            query = query.filter(self.model.fecha_emision >= fecha_desde)
        if fecha_hasta:
            query = query.filter(self.model.fecha_emision <= fecha_hasta)

        if limit:
            query = query.limit(limit)

        documentos = query.all()
        summaries = [self._format_document_summary(
            doc, True) for doc in documentos]
        return [summary for summary in summaries if summary is not None]

    def _find_heavily_modified_documents(self, empresa_id: int, fecha_desde: Optional[date],
                                         fecha_hasta: Optional[date], limit: Optional[int]) -> List[Dict[str, Any]]:
        """Busca documentos muy modificados (más de 3 NCE/NDE)."""
        # Query compleja para contar modificaciones por documento
        modificaciones_query = self.db.query(
            self.model.documento_original_cdc,
            func.count(self.model.id).label('total_modificaciones')
        ).filter(
            self.model.tipo_documento.in_(["5", "6"])
        ).group_by(self.model.documento_original_cdc).having(
            func.count(self.model.id) > 3
        ).subquery()

        query = self.db.query(self.model).filter(
            and_(
                self.model.empresa_id == empresa_id,
                self.model.cdc.in_(
                    self.db.query(
                        modificaciones_query.c.documento_original_cdc)
                )
            )
        )

        if fecha_desde:
            query = query.filter(self.model.fecha_emision >= fecha_desde)
        if fecha_hasta:
            query = query.filter(self.model.fecha_emision <= fecha_hasta)

        if limit:
            query = query.limit(limit)

        documentos = query.all()
        summaries = [self._format_document_summary(
            doc, True) for doc in documentos]
        return [summary for summary in summaries if summary is not None]

    def _get_tipo_descripcion(self, tipo: str) -> str:
        """Obtiene descripción del tipo de documento."""
        descripciones = {
            "1": "Factura Electrónica",
            "4": "Autofactura Electrónica",
            "5": "Nota de Crédito Electrónica",
            "6": "Nota de Débito Electrónica",
            "7": "Nota de Remisión Electrónica"
        }
        return descripciones.get(tipo, f"Tipo {tipo}")

    def _analyze_relationship_patterns(self, documentos: List[Documento], stats: Dict[str, Any]) -> None:
        """Analiza patrones de relaciones en los documentos."""
        documentos_principales = [d for d in documentos if getattr(
            d, 'tipo_documento', '') in ["1", "4", "7"]]

        for doc in documentos_principales:
            doc_id = getattr(doc, 'id', 0)
            relacionados = self.get_related_credits_debits(
                doc_id, tipo="ambos")

            if relacionados:
                if any(getattr(r, 'tipo_documento', '') == "5" for r in relacionados):
                    stats["relaciones"]["documentos_con_creditos"] += 1
                if any(getattr(r, 'tipo_documento', '') == "6" for r in relacionados):
                    stats["relaciones"]["documentos_con_debitos"] += 1
                if len(relacionados) > 3:
                    stats["relaciones"]["documentos_muy_modificados"] += 1
            else:
                stats["relaciones"]["documentos_sin_modificaciones"] += 1

        # Calcular tendencias
        total_principales = len(documentos_principales)
        if total_principales > 0:
            stats["tendencias"]["porcentaje_con_modificaciones"] = (
                (total_principales - stats["relaciones"]["documentos_sin_modificaciones"]) /
                total_principales * 100
            )

    def _find_root_document(self, documento: Documento, max_depth: int) -> Documento:
        """Encuentra el documento raíz siguiendo la cadena hacia arriba."""
        documento_actual = documento
        depth = 0

        while depth < max_depth:
            # Si es NCE o NDE, buscar su documento original
            tipo = getattr(documento_actual, 'tipo_documento', '')
            if tipo in ["5", "6"]:
                original_cdc = getattr(
                    documento_actual, 'documento_original_cdc', None)
                if original_cdc:
                    documento_original = getattr(
                        self, 'get_by_cdc')(original_cdc)
                    if documento_original:
                        documento_actual = documento_original
                        depth += 1
                        continue

            # No hay más niveles hacia arriba
            break

        return documento_actual

    def _build_descendant_tree(self, documento_raiz: Documento, max_depth: int) -> List[Dict[str, Any]]:
        """Construye árbol de descendientes desde un documento raíz."""
        niveles = []

        def procesar_nivel(documentos_padre: List[Documento], nivel: int):
            if nivel >= max_depth or not documentos_padre:
                return

            nivel_actual = []

            for doc_padre in documentos_padre:
                doc_id = getattr(doc_padre, 'id', 0)
                descendientes = self.get_related_credits_debits(
                    doc_id, tipo="ambos")

                if descendientes:
                    nivel_actual.extend([
                        {
                            "documento": self._format_document_summary(desc, True),
                            "padre_id": doc_id,
                            "nivel": nivel
                        }
                        for desc in descendientes
                    ])

            if nivel_actual:
                niveles.append({
                    "nivel": nivel,
                    "documentos": nivel_actual
                })

                # Procesar siguiente nivel
                docs_siguiente_nivel = [item["documento"]
                                        for item in nivel_actual]
                procesar_nivel(docs_siguiente_nivel, nivel + 1)

        # Iniciar desde el documento raíz
        procesar_nivel([documento_raiz], 1)

        return niveles

    def _calculate_lineage_stats(self, linaje: Dict[str, Any]) -> None:
        """Calcula estadísticas del linaje."""
        total_docs = 1  # Documento base
        tipos_docs = {}

        for nivel in linaje["niveles"]:
            total_docs += len(nivel["documentos"])
            for doc_info in nivel["documentos"]:
                tipo = doc_info["documento"]["tipo_documento"]
                tipos_docs[tipo] = tipos_docs.get(tipo, 0) + 1

        linaje["resumen"]["total_documentos"] = total_docs
        linaje["resumen"]["profundidad_maxima"] = len(linaje["niveles"])
        linaje["resumen"]["tipos_documentos"] = tipos_docs

    def _identify_complex_relationships(self, empresa_id: int) -> List[Dict[str, Any]]:
        """Identifica documentos con relaciones complejas."""
        # Query para documentos con múltiples modificaciones
        modificaciones_query = self.db.query(
            self.model.documento_original_cdc,
            func.count(self.model.id).label('total_modificaciones')
        ).filter(
            self.model.tipo_documento.in_(["5", "6"])
        ).group_by(self.model.documento_original_cdc).having(
            func.count(self.model.id) >= 2  # 2 o más modificaciones
        ).subquery()

        # Documentos base con modificaciones
        documentos_complejos = self.db.query(self.model).filter(
            and_(
                self.model.empresa_id == empresa_id,
                self.model.cdc.in_(
                    self.db.query(
                        modificaciones_query.c.documento_original_cdc)
                )
            )
        ).all()

        return [
            {
                "id": getattr(doc, 'id', 0),
                "numero_completo": getattr(doc, 'numero_completo', ''),
                "tipo_documento": getattr(doc, 'tipo_documento', ''),
                "fecha_emision": getattr(doc, 'fecha_emision', date.today()).isoformat()
            }
            for doc in documentos_complejos
        ]

    def _is_complex_relationship(self, analisis_doc: Dict[str, Any]) -> bool:
        """Determina si una relación es compleja."""
        total_relacionados = analisis_doc["resumen"]["total_documentos_relacionados"]
        tiene_ambos_tipos = (
            analisis_doc["resumen"]["total_notas_credito"] > 0 and
            analisis_doc["resumen"]["total_notas_debito"] > 0
        )

        return total_relacionados >= 3 or tiene_ambos_tipos

    def _calculate_complexity_score(self, analisis_doc: Dict[str, Any]) -> float:
        """Calcula un score de complejidad para un documento."""
        score = 0.0

        # Puntos por cantidad de documentos relacionados
        score += analisis_doc["resumen"]["total_documentos_relacionados"] * 1.0

        # Puntos extra si tiene tanto créditos como débitos
        if (analisis_doc["resumen"]["total_notas_credito"] > 0 and
                analisis_doc["resumen"]["total_notas_debito"] > 0):
            score += 2.0

        # Puntos por impacto financiero alto
        if analisis_doc.get("analisis_financiero"):
            porcentaje_ajuste = abs(
                analisis_doc["analisis_financiero"].get("porcentaje_ajuste_neto", 0))
            if porcentaje_ajuste > 50:
                score += 3.0
            elif porcentaje_ajuste > 25:
                score += 1.5

        return score

    def _calculate_average_complexity(self, relaciones_complejas: List[Dict[str, Any]]) -> float:
        """Calcula complejidad promedio."""
        if not relaciones_complejas:
            return 0.0

        total_score = sum(rel["complejidad_score"]
                          for rel in relaciones_complejas)
        return total_score / len(relaciones_complejas)

    def _detect_relationship_anomalies(self, documentos_complejos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detecta anomalías en las relaciones."""
        anomalias = []

        for doc_info in documentos_complejos:
            try:
                relaciones = self.get_document_relations(
                    doc_info["id"], include_amounts=True)

                # Anomalía: Créditos superan el monto original
                if relaciones.get("analisis_financiero"):
                    af = relaciones["analisis_financiero"]
                    if af["total_creditos"] > af["monto_original"]:
                        anomalias.append({
                            "tipo": "creditos_excesivos",
                            "documento": doc_info,
                            "descripcion": f"Créditos ({af['total_creditos']}) superan monto original ({af['monto_original']})",
                            "severidad": "alta"
                        })

                # Anomalía: Muchas modificaciones en poco tiempo
                modificaciones = relaciones["resumen"]["total_documentos_relacionados"]
                if modificaciones > 5:
                    anomalias.append({
                        "tipo": "muchas_modificaciones",
                        "documento": doc_info,
                        "descripcion": f"Documento con {modificaciones} modificaciones",
                        "severidad": "media"
                    })

            except Exception as e:
                logger.warning(
                    f"Error analizando documento {doc_info['id']}: {e}")

        return anomalias

    def _calculate_total_financial_impact(self, relaciones_complejas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula impacto financiero total."""
        impacto_total = {
            "monto_total_original": 0.0,
            "total_creditos_aplicados": 0.0,
            "total_debitos_aplicados": 0.0,
            "impacto_neto_total": 0.0,
            "documentos_analizados": len(relaciones_complejas)
        }

        for rel in relaciones_complejas:
            af = rel.get("analisis", {}).get("analisis_financiero", {})
            if af:
                impacto_total["monto_total_original"] += af.get(
                    "monto_original", 0)
                impacto_total["total_creditos_aplicados"] += af.get(
                    "total_creditos", 0)
                impacto_total["total_debitos_aplicados"] += af.get(
                    "total_debitos", 0)
                impacto_total["impacto_neto_total"] += af.get(
                    "impacto_neto", 0)

        return impacto_total

    def _generate_relationship_recommendations(self, reporte: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en el reporte."""
        recomendaciones = []

        # Recomendaciones por anomalías
        anomalias_altas = [
            a for a in reporte["anomalias_detectadas"] if a["severidad"] == "alta"]
        if anomalias_altas:
            recomendaciones.append(
                f"Revisar urgentemente {len(anomalias_altas)} documentos con anomalías de alta severidad")

        # Recomendaciones por complejidad
        complejidad_promedio = reporte["resumen_ejecutivo"]["nivel_complejidad_promedio"]
        if complejidad_promedio > 5.0:
            recomendaciones.append(
                "Nivel de complejidad alto - revisar procesos de modificación de documentos")

        # Recomendaciones por volumen
        total_complejas = reporte["resumen_ejecutivo"]["relaciones_complejas_detectadas"]
        if total_complejas > 50:
            recomendaciones.append(
                "Alto volumen de relaciones complejas - considerar optimización de procesos")

        if not recomendaciones:
            recomendaciones.append(
                "Las relaciones entre documentos están dentro de parámetros normales")

        return recomendaciones

    def _calculate_impact_trends(self, impacto: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula tendencias de impacto."""
        movimientos = impacto["detalle_movimientos"]

        if len(movimientos) < 2:
            return {"tendencia": "insuficientes_datos"}

        # Análisis temporal de movimientos
        movimientos_por_mes = {}
        for mov in movimientos:
            fecha = datetime.fromisoformat(mov["fecha"])
            mes_key = fecha.strftime("%Y-%m")

            if mes_key not in movimientos_por_mes:
                movimientos_por_mes[mes_key] = {"creditos": 0, "debitos": 0}

            if mov["tipo"] == "credito":
                movimientos_por_mes[mes_key]["creditos"] += mov["monto"]
            else:
                movimientos_por_mes[mes_key]["debitos"] += mov["monto"]

        return {
            "movimientos_por_mes": movimientos_por_mes,
            "patron_temporal": "creciente" if len(movimientos_por_mes) > 1 else "estable",
            "frecuencia_modificaciones": len(movimientos) / max(1, len(movimientos_por_mes))
        }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "DocumentRelationsMixin",
    "TIPOS_RELACION",
    "ESTADOS_PERMITE_RELACION"
]
