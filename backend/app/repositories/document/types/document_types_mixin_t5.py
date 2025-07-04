# ===============================================
# ARCHIVO: backend/app/repositories/documento/document_types_t5.py
# PROPÓSITO: Mixin para operaciones específicas de Notas de Crédito Electrónicas (NCE - Tipo 5)
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para operaciones específicas de Notas de Crédito Electrónicas (NCE - Tipo 5).

Este módulo implementa funcionalidades especializadas para el manejo de notas de crédito
electrónicas, incluyendo:
- Creación con validaciones específicas de NCE
- Referencia obligatoria a documentos originales
- Validaciones de montos contra documento original
- Búsquedas optimizadas para notas de crédito
- Estadísticas específicas de devoluciones y ajustes

Características principales:
- Documento asociado OBLIGATORIO (factura/documento original)
- Motivos específicos de emisión (1-8 según SIFEN)
- Montos típicamente negativos (crédito al cliente)
- Validaciones de coherencia con documento original
- Análisis de devoluciones y tendencias de crédito

Casos de uso típicos:
- Devoluciones de mercadería
- Descuentos posteriores a la venta
- Anulaciones parciales o totales
- Correcciones de errores en facturación
- Bonificaciones comerciales

Clase principal:
- DocumentTypesT5Mixin: Mixin especializado para notas de crédito electrónicas
"""

from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy import and_, or_, func, text, desc, asc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenValidationError,
    SifenEntityNotFoundError,
    SifenBusinessLogicError,
    SifenDuplicateEntityError,
    handle_database_exception
)
from app.models.documento import (
    NotaCreditoElectronica,
    Documento,
    TipoDocumentoSifenEnum,
    EstadoDocumentoSifenEnum,
    MonedaSifenEnum
)
from app.schemas.documento import (
    DocumentoCreateDTO,
    DocumentoBaseDTO
)
from ..utils import (
    normalize_cdc,
    format_numero_completo,
    log_repository_operation,
    log_performance_metric,
    handle_repository_error,
    build_date_filter,
    build_amount_filter,
    calculate_percentage,
    get_date_range_for_period,
    aggregate_by_period,
    format_stats_for_chart,
    get_default_page_size,
    get_max_page_size
)
from ..auxiliars import (
    apply_default_config,
    validate_nota_credito_data,
    validate_and_get_original_document,
    validate_credit_amounts,
    get_documents_by_type_and_criteria,
    calculate_totals_from_items,
    create_items_for_document,
    link_original_document,
    validate_nota_credito_item
)

# Type hints para Pylance
if TYPE_CHECKING:
    from ..base import DocumentoRepositoryBase

logger = get_logger(__name__)

# ===============================================
# CONFIGURACIONES ESPECÍFICAS PARA NOTAS DE CRÉDITO
# ===============================================

# Defaults específicos para notas de crédito electrónicas
NOTA_CREDITO_DEFAULTS = {
    "tipo_documento": "5",
    "tipo_operacion": "1",  # Venta (hereda del documento original)
    "condicion_operacion": "1",  # Contado típico
    "moneda": "PYG",  # Hereda del documento original
    "tipo_emision": "1"  # Normal
}

# Motivos de emisión NCE según SIFEN v150
MOTIVOS_EMISION_NCE = {
    "1": "Anulación",
    "2": "Devolución",
    "3": "Descuento",
    "4": "Bonificación",
    "5": "Crédito incobrable",
    "6": "Ajuste de precio",
    "7": "Corrección",
    "8": "Otros"
}

# Tipos de documento que pueden ser referenciados por NCE
TIPOS_DOCUMENTO_REFERENCIABLES = ["1", "4", "6"]  # FE, AFE, NDE

# Estados válidos del documento original para generar NCE
ESTADOS_VALIDOS_DOCUMENTO_ORIGINAL = [
    "aprobado",
    "aprobado_observacion"
]

# ===============================================
# MIXIN PRINCIPAL
# ===============================================


class DocumentTypesT5Mixin:
    """
    Mixin para operaciones específicas de Notas de Crédito Electrónicas (NCE - Tipo 5).

    Proporciona métodos especializados para el manejo de notas de crédito electrónicas:
    - Creación con validaciones específicas de NCE
    - Referencia obligatoria a documentos originales
    - Validaciones de montos y coherencia
    - Búsquedas optimizadas para notas de crédito
    - Estadísticas de devoluciones y ajustes
    - Integración con SIFEN v150

    CARACTERÍSTICAS CRÍTICAS NCE:
    - Documento asociado OBLIGATORIO
    - Montos típicamente negativos (crédito al cliente)
    - Motivo específico de emisión obligatorio
    - Validaciones de coherencia con documento original
    - Fecha emisión posterior al documento original

    Este mixin debe ser usado junto con DocumentoRepositoryBase para
    obtener funcionalidad completa de gestión de documentos.

    Example:
        ```python
        class DocumentoRepository(
            DocumentoRepositoryBase,
            DocumentTypesT5Mixin,
            # otros mixins...
        ):
            pass

        repo = DocumentoRepository(db)
        nota_credito = repo.create_nota_credito_electronica(data, items, cdc_original)
        ```
    """

    def _apply_nota_credito_defaults(self, data: Dict[str, Any], documento_original: Documento) -> None:
        """
        Aplica configuraciones por defecto específicas de notas de crédito.

        Hereda datos del documento original y aplica configuraciones específicas
        para NCE según normativa SIFEN v150 y reglas de negocio Paraguay.

        Args:
            data: Diccionario de datos a modificar in-place
            documento_original: Documento original para heredar valores

        Example:
            ```python
            data = {"numero_documento": "0000123"}
            self._apply_nota_credito_defaults(data, factura_original)
            # data ahora incluye moneda, tipo_cambio, empresa_id del original
            ```

        Note:
            Esta función modifica el diccionario data in-place para optimizar performance.
        """
        start_time = datetime.now()

        try:
            # 1. Aplicar defaults base desde auxiliares
            apply_default_config(data, "5")  # Tipo 5 = Nota de Crédito

            # 2. Aplicar defaults específicos adicionales de NCE
            for key, default_value in NOTA_CREDITO_DEFAULTS.items():
                if key not in data or data[key] is None:
                    data[key] = default_value

            # 3. Heredar valores críticos del documento original
            campos_a_heredar = ["moneda", "tipo_cambio",
                                "empresa_id", "cliente_id"]
            for campo in campos_a_heredar:
                if campo not in data and hasattr(documento_original, campo):
                    valor_original = getattr(documento_original, campo)
                    if valor_original is not None:
                        data[campo] = valor_original

            # 4. Configuraciones especiales NCE
            if "fecha_emision" not in data:
                data["fecha_emision"] = date.today()

            if "estado" not in data:
                data["estado"] = EstadoDocumentoSifenEnum.BORRADOR.value

            # 5. Log de performance si es lenta
            duration = (datetime.now() - start_time).total_seconds()
            if duration > 0.1:  # Más de 100ms
                logger.warning(
                    "NCE_DEFAULTS_SLOW",
                    extra={
                        "modulo": "document_types_t5",
                        "operacion": "_apply_nota_credito_defaults",
                        "duration_ms": duration * 1000,
                        "campos_heredados": len(campos_a_heredar)
                    }
                )

        except Exception as e:
            logger.error(
                "NCE_DEFAULTS_ERROR",
                extra={
                    "modulo": "document_types_t5",
                    "operacion": "_apply_nota_credito_defaults",
                    "error": str(e),
                    "documento_original_id": getattr(documento_original, 'id', None)
                }
            )
            raise

    def _ensure_negative_amounts(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Asegura que los montos de los items sean negativos para NCE.

        Las notas de crédito requieren montos negativos según normativa SIFEN
        para representar créditos al cliente. Esta función convierte automáticamente
        valores positivos a negativos.

        Args:
            items: Lista de items originales

        Returns:
            List[Dict[str, Any]]: Items con montos negativos garantizados

        Example:
            ```python
            items_originales = [{
                "cantidad": 2,
                "precio_unitario": Decimal("100000")
            }]
            items_ajustados = self._ensure_negative_amounts(items_originales)
            # items_ajustados = [{
            #     "cantidad": -2,
            #     "precio_unitario": Decimal("-100000")
            # }]
            ```

        Note:
            Función específica para NCE. No aplicar a otros tipos de documento.
        """
        start_time = datetime.now()
        items_ajustados = []
        items_modificados = 0

        try:
            for i, item in enumerate(items):
                item_copy = item.copy()

                # 1. Procesar cantidad - debe ser negativa
                cantidad = item_copy.get("cantidad", 0)
                if cantidad != 0:
                    try:
                        cantidad_float = float(cantidad)
                        if cantidad_float > 0:
                            item_copy["cantidad"] = -abs(cantidad_float)
                            items_modificados += 1
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            "NCE_CANTIDAD_CONVERSION_ERROR",
                            extra={
                                "modulo": "document_types_t5",
                                "item_index": i,
                                "cantidad_original": cantidad,
                                "error": str(e)
                            }
                        )

                # 2. Procesar precio unitario - debe ser negativo
                precio = item_copy.get("precio_unitario", 0)
                if precio != 0:
                    try:
                        if isinstance(precio, (str, int, float)):
                            precio_decimal = Decimal(str(precio))
                        elif isinstance(precio, Decimal):
                            precio_decimal = precio
                        else:
                            precio_decimal = Decimal("0")

                        if precio_decimal > 0:
                            item_copy["precio_unitario"] = -abs(precio_decimal)
                            items_modificados += 1

                    except (ValueError, TypeError, InvalidOperation) as e:
                        logger.warning(
                            "NCE_PRECIO_CONVERSION_ERROR",
                            extra={
                                "modulo": "document_types_t5",
                                "item_index": i,
                                "precio_original": precio,
                                "error": str(e)
                            }
                        )

                items_ajustados.append(item_copy)

            # 3. Log de operación para auditoría
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                "NCE_NEGATIVE_AMOUNTS_APPLIED",
                extra={
                    "modulo": "document_types_t5",
                    "operacion": "_ensure_negative_amounts",
                    "total_items": len(items),
                    "items_modificados": items_modificados,
                    "duration_ms": duration * 1000
                }
            )

            return items_ajustados

        except Exception as e:
            logger.error(
                "NCE_NEGATIVE_AMOUNTS_ERROR",
                extra={
                    "modulo": "document_types_t5",
                    "operacion": "_ensure_negative_amounts",
                    "error": str(e),
                    "total_items": len(items)
                }
            )
            raise SifenValidationError(
                "Error procesando montos negativos para NCE",
                field="items",
                details={"error": str(e)}
            )

    # Type hints para Pylance - estos métodos/atributos vienen del repository base
    if TYPE_CHECKING:
        db: Session
        model: type
        def create(self, obj_data, auto_generate_fields: bool = True): ...
        def get_by_id(self, entity_id: int): ...
        def get_by_cdc(self, cdc: str): ...

    # ===============================================
    # MÉTODOS DE CREACIÓN ESPECÍFICOS
    # ===============================================

    def create_nota_credito_electronica(self,
                                        nota_credito_data: Union[DocumentoCreateDTO, Dict[str, Any]],
                                        items: List[Dict[str, Any]],
                                        documento_original_cdc: str,
                                        motivo_emision: str,
                                        descripcion_motivo: Optional[str] = None,
                                        apply_defaults: bool = True,
                                        validate_amounts: bool = True,
                                        auto_generate_cdc: bool = True) -> NotaCreditoElectronica:
        """
        Crea una nota de crédito electrónica con validaciones específicas.

        Este método es el punto de entrada principal para crear notas de crédito electrónicas,
        aplicando todas las validaciones y configuraciones específicas del tipo de documento.

        Args:
            nota_credito_data: Datos básicos de la nota de crédito
            items: Lista de items/productos de la nota de crédito
            documento_original_cdc: CDC del documento original (factura) a creditar
            motivo_emision: Motivo de emisión (1-8 según SIFEN)
            descripcion_motivo: Descripción personalizada del motivo (opcional)
            apply_defaults: Aplicar configuraciones por defecto específicas
            validate_amounts: Validar montos contra documento original
            auto_generate_cdc: Generar CDC automáticamente

        Returns:
            NotaCreditoElectronica: Instancia de nota de crédito creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio NCE
            SifenEntityNotFoundError: Si el documento original no existe

        Example:
            ```python
            nota_credito_data = {
                "establecimiento": "001",
                "punto_expedicion": "001",
                "numero_documento": "0000789",
                "cliente_id": 456,  # Mismo cliente de la factura original
                "numero_timbrado": "12345678",
                "fecha_emision": date.today(),
                "moneda": "PYG"
            }

            items_devolucion = [{
                "descripcion": "Producto defectuoso - DEVOLUCIÓN",
                "cantidad": -1,  # Cantidad negativa
                "precio_unitario": Decimal("-550000"),  # Precio negativo
                "tipo_iva": "10"
            }]

            nota_credito = repo.create_nota_credito_electronica(
                nota_credito_data=nota_credito_data,
                items=items_devolucion,
                documento_original_cdc="12345678901234567890123456789012345678901234",
                motivo_emision="2",  # Devolución
                descripcion_motivo="Producto defectuoso devuelto por cliente"
            )
            ```
        """
        start_time = datetime.now()

        try:
            # 1. Preparar datos base
            if isinstance(nota_credito_data, DocumentoCreateDTO):
                data_dict = nota_credito_data.dict()
            else:
                data_dict = nota_credito_data.copy()

            # 2. Validar y obtener documento original
            documento_original = validate_and_get_original_document(
                self.db, self.model, documento_original_cdc
            )

            # 3. Aplicar defaults específicos de notas de crédito
            if apply_defaults:
                self._apply_nota_credito_defaults(
                    data_dict, documento_original)

            # 4. Validar estructura básica y reglas NCE
            self.validate_nota_credito_data(
                data_dict, items, documento_original)

            # 5. Validar motivo de emisión
            self.validate_motivo_emision(motivo_emision, descripcion_motivo)

            # 6. Validar montos contra documento original si se solicita
            if validate_amounts:
                validate_credit_amounts(data_dict, documento_original)

            # 7. Validar coherencia emisor/receptor con documento original
            self.validate_coherencia_con_original(
                data_dict, documento_original)

            # 8. Calcular totales automáticamente desde items
            calculate_totals_from_items(data_dict, items)

            # 9. Incluir datos específicos de NCE
            data_dict.update({
                "documento_original_cdc": documento_original_cdc,
                "motivo_credito": descripcion_motivo or MOTIVOS_EMISION_NCE.get(motivo_emision, "Otros"),
                "motivo_emision_codigo": motivo_emision
            })

            # 10. Crear documento usando método base del repository
            nota_credito = getattr(self, 'create')(
                data_dict, auto_generate_fields=auto_generate_cdc)

            # 11. Crear items asociados a la nota de crédito
            if items:
                create_items_for_document(
                    getattr(self, 'db'), nota_credito, items)

            # 12. Vincular documento original
            link_original_document(nota_credito, documento_original)

            # 13. Log de operación exitosa
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "create_nota_credito_electronica", duration, 1)

            log_repository_operation("create_nota_credito_electronica", "NotaCreditoElectronica",
                                     getattr(nota_credito, 'id', None), {
                                         "numero_completo": getattr(nota_credito, 'numero_completo', None),
                                         "total_general": float(getattr(nota_credito, 'total_general', 0)),
                                         "items_count": len(items),
                                         "motivo_emision": motivo_emision,
                                         "documento_original_cdc": documento_original_cdc
                                     })

            return nota_credito

        except (SifenValidationError, SifenBusinessLogicError, SifenEntityNotFoundError):
            # Re-raise errores de validación/negocio sin modificar
            getattr(self, 'db').rollback()
            raise
        except Exception as e:
            getattr(self, 'db').rollback()
            handle_repository_error(
                e, "create_nota_credito_electronica", "NotaCreditoElectronica")
            raise handle_database_exception(
                e, "create_nota_credito_electronica")

    def create_nota_credito_devolucion(self,
                                       numero_documento: str,
                                       documento_original_cdc: str,
                                       items_devueltos: List[Dict[str, Any]],
                                       empresa_id: Optional[int] = None,
                                       motivo_detallado: Optional[str] = None) -> NotaCreditoElectronica:
        """
        Creación específica para notas de crédito por devolución.

        Método de conveniencia para crear notas de crédito típicas por devolución
        de mercadería con configuraciones optimizadas.

        Args:
            numero_documento: Número secuencial del documento
            documento_original_cdc: CDC del documento original
            items_devueltos: Items devueltos (con cantidades/precios negativos)
            empresa_id: ID de la empresa emisora (opcional)
            motivo_detallado: Descripción detallada de la devolución

        Returns:
            NotaCreditoElectronica: Nota de crédito por devolución creada

        Example:
            ```python
            items_devueltos = [{
                "descripcion": "Laptop HP Pavilion - DEVOLUCIÓN por defecto",
                "cantidad": -1,
                "precio_unitario": Decimal("-1200000"),
                "motivo_devolucion": "Producto defectuoso de fábrica",
                "tipo_iva": "10"
            }]

            nota_credito = repo.create_nota_credito_devolucion(
                numero_documento="0000123",
                documento_original_cdc="12345678901234567890123456789012345678901234",
                items_devueltos=items_devueltos,
                empresa_id=1,
                motivo_detallado="Devolución por producto defectuoso según reclamo #789"
            )
            ```
        """
        # Obtener documento original para extraer datos
        documento_original = validate_and_get_original_document(
            self.db, self.model, documento_original_cdc
        )

        # TODO: Obtener datos de empresa y timbrado activo
        nota_credito_data = {
            "establecimiento": "001",  # TODO: Desde configuración empresa
            "punto_expedicion": "001",  # TODO: Desde configuración empresa
            "numero_documento": numero_documento,
            "cliente_id": getattr(documento_original, 'cliente_id'),
            "empresa_id": empresa_id or getattr(documento_original, 'empresa_id'),
            "numero_timbrado": "12345678",  # TODO: Desde timbrado activo
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),
            "timbrado_id": 1,  # TODO: Desde timbrado activo
            "moneda": getattr(documento_original, 'moneda', 'PYG'),
            "tipo_cambio": getattr(documento_original, 'tipo_cambio', Decimal("1.0000"))
        }

        # Asegurar que los items tienen cantidades/precios negativos
        items_ajustados = self._ensure_negative_amounts(items_devueltos)

        return self.create_nota_credito_electronica(
            nota_credito_data=nota_credito_data,
            items=items_ajustados,
            documento_original_cdc=documento_original_cdc,
            motivo_emision="2",  # Devolución
            descripcion_motivo=motivo_detallado or "Devolución de mercadería",
            apply_defaults=True,
            validate_amounts=True,
            auto_generate_cdc=True
        )

    def create_nota_credito_descuento(self,
                                      numero_documento: str,
                                      documento_original_cdc: str,
                                      monto_descuento: Decimal,
                                      motivo_descuento: str,
                                      empresa_id: Optional[int] = None,
                                      aplicar_iva: bool = True) -> NotaCreditoElectronica:
        """
        Creación específica para notas de crédito por descuento.

        Args:
            numero_documento: Número secuencial del documento
            documento_original_cdc: CDC del documento original
            monto_descuento: Monto del descuento (positivo, se convertirá a negativo)
            motivo_descuento: Motivo específico del descuento
            empresa_id: ID de la empresa emisora (opcional)
            aplicar_iva: Si debe aplicar IVA al descuento

        Returns:
            NotaCreditoElectronica: Nota de crédito por descuento creada
        """
        # Obtener documento original
        documento_original = validate_and_get_original_document(
            self.db, self.model, documento_original_cdc
        )

        # Crear item del descuento
        monto_negativo = -abs(monto_descuento)

        items_descuento = [{
            "descripcion": f"Descuento aplicado: {motivo_descuento}",
            "cantidad": -1,
            "precio_unitario": monto_negativo,
            "tipo_iva": "10" if aplicar_iva else "exento"
        }]

        nota_credito_data = {
            "establecimiento": "001",
            "punto_expedicion": "001",
            "numero_documento": numero_documento,
            "cliente_id": getattr(documento_original, 'cliente_id'),
            "empresa_id": empresa_id or getattr(documento_original, 'empresa_id'),
            "numero_timbrado": "12345678",
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),
            "timbrado_id": 1,
            "moneda": getattr(documento_original, 'moneda', 'PYG'),
            "tipo_cambio": getattr(documento_original, 'tipo_cambio', Decimal("1.0000"))
        }

        return self.create_nota_credito_electronica(
            nota_credito_data=nota_credito_data,
            items=items_descuento,
            documento_original_cdc=documento_original_cdc,
            motivo_emision="3",  # Descuento
            descripcion_motivo=motivo_descuento,
            apply_defaults=True,
            validate_amounts=True
        )

    def create_nota_credito_anulacion(self,
                                      numero_documento: str,
                                      documento_original_cdc: str,
                                      motivo_anulacion: str,
                                      empresa_id: Optional[int] = None,
                                      anulacion_total: bool = True) -> NotaCreditoElectronica:
        """
        Creación específica para notas de crédito por anulación.

        Args:
            numero_documento: Número secuencial del documento
            documento_original_cdc: CDC del documento original
            motivo_anulacion: Motivo específico de la anulación
            empresa_id: ID de la empresa emisora (opcional)
            anulacion_total: Si es anulación total (100% del monto original)

        Returns:
            NotaCreditoElectronica: Nota de crédito por anulación creada
        """
        # Obtener documento original
        documento_original = validate_and_get_original_document(
            self.db, self.model, documento_original_cdc
        )

        if anulacion_total:
            # Anulación total - tomar montos del documento original y convertir a negativos
            total_original = getattr(
                documento_original, 'total_general', Decimal("0"))

            items_anulacion = [{
                "descripcion": f"Anulación total del documento {getattr(documento_original, 'numero_completo', '')}",
                "cantidad": -1,
                "precio_unitario": -total_original,
                "tipo_iva": "10"  # Asumir IVA por defecto
            }]
        else:
            # TODO: Implementar anulación parcial cuando se requiera
            raise NotImplementedError("Anulación parcial no implementada aún")

        nota_credito_data = {
            "establecimiento": "001",
            "punto_expedicion": "001",
            "numero_documento": numero_documento,
            "cliente_id": getattr(documento_original, 'cliente_id'),
            "empresa_id": empresa_id or getattr(documento_original, 'empresa_id'),
            "numero_timbrado": "12345678",
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),
            "timbrado_id": 1,
            "moneda": getattr(documento_original, 'moneda', 'PYG'),
            "tipo_cambio": getattr(documento_original, 'tipo_cambio', Decimal("1.0000"))
        }

        return self.create_nota_credito_electronica(
            nota_credito_data=nota_credito_data,
            items=items_anulacion,
            documento_original_cdc=documento_original_cdc,
            motivo_emision="1",  # Anulación
            descripcion_motivo=motivo_anulacion,
            apply_defaults=True,
            validate_amounts=True
        )

    # ===============================================
    # VALIDACIONES ESPECÍFICAS
    # ===============================================

    def validate_nota_credito_data(self,
                                   nota_credito_data: Dict[str, Any],
                                   items: List[Dict[str, Any]],
                                   documento_original: Documento) -> None:
        """
        Validaciones comprehensivas específicas para notas de crédito electrónicas.

        Aplica todas las validaciones requeridas para una nota de crédito según
        las normativas SIFEN y reglas de negocio específicas de NCE.

        Args:
            nota_credito_data: Datos de la nota de crédito a validar
            items: Items de la nota de crédito a validar
            documento_original: Documento original de referencia

        Raises:
            SifenValidationError: Si alguna validación falla

        Example:
            ```python
            try:
                repo.validate_nota_credito_data(nce_data, items, doc_original)
                print("Datos NCE válidos")
            except SifenValidationError as e:
                print(f"Error de validación NCE: {e.message}")
            ```
        """
        # Usar validación de auxiliares como base
        validate_nota_credito_data(nota_credito_data, documento_original)

        # Validaciones adicionales específicas de NCE

        # 1. Items obligatorios
        if not items or len(items) == 0:
            raise SifenValidationError(
                "Notas de crédito deben tener al menos 1 item",
                field="items"
            )

        # 2. Validar cada item
        for i, item in enumerate(items):
            validate_nota_credito_item(item, i)

        # 3. Validar fecha posterior al documento original
        fecha_emision = nota_credito_data.get("fecha_emision")
        fecha_original = getattr(documento_original, 'fecha_emision', None)

        if fecha_emision and fecha_original and fecha_emision <= fecha_original:
            raise SifenValidationError(
                "Fecha de emisión de NCE debe ser posterior al documento original",
                field="fecha_emision",
                value=fecha_emision
            )

        # 4. Validar estado del documento original
        estado_original = getattr(documento_original, 'estado', '')
        if estado_original not in ESTADOS_VALIDOS_DOCUMENTO_ORIGINAL:
            raise SifenValidationError(
                f"Documento original debe estar en estado válido para NCE. "
                f"Estado actual: {estado_original}, válidos: {ESTADOS_VALIDOS_DOCUMENTO_ORIGINAL}",
                field="documento_original_estado",
                value=estado_original
            )

    def validate_motivo_emision(self, motivo_codigo: str, descripcion: Optional[str] = None) -> None:
        """
        Valida motivo de emisión de la nota de crédito.

        Args:
            motivo_codigo: Código del motivo (1-8)
            descripcion: Descripción del motivo (opcional)

        Raises:
            SifenValidationError: Si el motivo no es válido
        """
        if motivo_codigo not in MOTIVOS_EMISION_NCE:
            raise SifenValidationError(
                f"Motivo de emisión debe ser uno de: {list(MOTIVOS_EMISION_NCE.keys())}",
                field="motivo_emision",
                value=motivo_codigo
            )

        # Validar coherencia de descripción con motivo
        if descripcion and motivo_codigo in ["1", "2", "3", "4"]:
            motivo_esperado = MOTIVOS_EMISION_NCE[motivo_codigo].lower()
            if motivo_esperado not in descripcion.lower():
                logger.warning(
                    f"Descripción del motivo no es coherente con código {motivo_codigo} ({MOTIVOS_EMISION_NCE[motivo_codigo]})"
                )

    def validate_coherencia_con_original(self,
                                         nota_credito_data: Dict[str, Any],
                                         documento_original: Documento) -> None:
        """
        Valida coherencia entre NCE y documento original.

        Args:
            nota_credito_data: Datos de la nota de crédito
            documento_original: Documento original

        Raises:
            SifenBusinessLogicError: Si hay inconsistencias
        """
        # Validar mismo emisor
        empresa_nce = nota_credito_data.get("empresa_id")
        empresa_original = getattr(documento_original, 'empresa_id', None)

        if empresa_nce != empresa_original:
            raise SifenBusinessLogicError(
                "NCE debe tener el mismo emisor que el documento original",
                details={
                    "empresa_nce": empresa_nce,
                    "empresa_original": empresa_original
                }
            )

        # Validar mismo cliente
        cliente_nce = nota_credito_data.get("cliente_id")
        cliente_original = getattr(documento_original, 'cliente_id', None)

        if cliente_nce != cliente_original:
            raise SifenBusinessLogicError(
                "NCE debe tener el mismo cliente que el documento original",
                details={
                    "cliente_nce": cliente_nce,
                    "cliente_original": cliente_original
                }
            )

        # Validar coherencia de moneda
        moneda_nce = nota_credito_data.get("moneda")
        moneda_original = getattr(documento_original, 'moneda', 'PYG')

        if moneda_nce != moneda_original:
            logger.warning(
                f"Moneda de NCE ({moneda_nce}) difiere del documento original ({moneda_original})"
            )

    def validate_document_reference_eligibility(self, documento_original: Documento) -> None:
        """
        Valida que el documento original sea elegible para NCE.

        Args:
            documento_original: Documento a validar

        Raises:
            SifenValidationError: Si el documento no es elegible
        """
        tipo_documento = getattr(documento_original, 'tipo_documento', '')

        if tipo_documento not in TIPOS_DOCUMENTO_REFERENCIABLES:
            raise SifenValidationError(
                f"Tipo de documento {tipo_documento} no puede ser referenciado por NCE. "
                f"Tipos válidos: {TIPOS_DOCUMENTO_REFERENCIABLES}",
                field="tipo_documento_original",
                value=tipo_documento
            )

    # ===============================================
    # BÚSQUEDAS ESPECIALIZADAS
    # ===============================================

    def get_notas_credito_by_criteria(self,
                                      empresa_id: int,
                                      fecha_desde: Optional[date] = None,
                                      fecha_hasta: Optional[date] = None,
                                      motivo_emision: Optional[str] = None,
                                      cliente_id: Optional[int] = None,
                                      monto_minimo: Optional[Decimal] = None,
                                      monto_maximo: Optional[Decimal] = None,
                                      estados: Optional[List[str]] = None,
                                      documento_original_cdc: Optional[str] = None,
                                      include_items: bool = False,
                                      limit: Optional[int] = None,
                                      offset: int = 0) -> List[NotaCreditoElectronica]:
        """
        Búsqueda avanzada de notas de crédito con múltiples criterios.

        Permite filtrar notas de crédito por diversos criterios específicos del negocio,
        optimizado para consultas frecuentes en dashboards de devoluciones.

        Args:
            empresa_id: ID de la empresa emisora
            fecha_desde: Fecha inicio del rango (opcional)
            fecha_hasta: Fecha fin del rango (opcional)
            motivo_emision: Motivo específico de emisión (1-8)
            cliente_id: ID del cliente específico (opcional)
            monto_minimo: Monto mínimo de la nota de crédito (opcional)
            monto_maximo: Monto máximo de la nota de crédito (opcional)
            estados: Lista de estados a incluir (opcional)
            documento_original_cdc: CDC del documento original (opcional)
            include_items: Incluir items en el resultado (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[NotaCreditoElectronica]: Lista de notas de crédito que cumplen criterios

        Example:
            ```python
            # Devoluciones del mes
            notas_credito = repo.get_notas_credito_by_criteria(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31),
                motivo_emision="2",  # Devolución
                estados=["aprobado"]
            )
            ```
        """
        start_time = datetime.now()

        try:
            # Verificar acceso a db
            if not hasattr(self, 'db'):
                raise AttributeError(
                    "Este mixin requiere DocumentoRepositoryBase con atributo db")

            # Construir query base
            query = getattr(self, 'db').query(NotaCreditoElectronica).filter(
                and_(
                    NotaCreditoElectronica.tipo_documento == "5",
                    NotaCreditoElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtros opcionales
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, NotaCreditoElectronica.fecha_emision, fecha_desde, fecha_hasta)

            if monto_minimo or monto_maximo:
                query = build_amount_filter(
                    query, NotaCreditoElectronica.total_general, monto_minimo, monto_maximo)

            if motivo_emision:
                query = query.filter(text("motivo_emision_codigo = :motivo")).params(
                    motivo=motivo_emision)

            if cliente_id:
                query = query.filter(
                    NotaCreditoElectronica.cliente_id == cliente_id)

            if estados:
                query = query.filter(text("estado IN :estados")).params(
                    estados=tuple(estados))

            if documento_original_cdc:
                query = query.filter(text("documento_original_cdc = :cdc")).params(
                    cdc=documento_original_cdc)

            # Incluir items si se solicita
            if include_items:
                # TODO: Implementar cuando tabla de items esté disponible
                # query = query.options(joinedload(NotaCreditoElectronica.items))
                pass

            # Aplicar límites y ordenamiento
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            notas_credito = query.order_by(
                desc(NotaCreditoElectronica.fecha_emision)).offset(offset).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_notas_credito_by_criteria", duration, len(notas_credito))

            return notas_credito

        except Exception as e:
            handle_repository_error(
                e, "get_notas_credito_by_criteria", "NotaCreditoElectronica")
            raise handle_database_exception(e, "get_notas_credito_by_criteria")

    def get_notas_credito_by_original_document(self,
                                               documento_original_cdc: str,
                                               empresa_id: Optional[int] = None) -> List[NotaCreditoElectronica]:
        """
        Obtiene todas las notas de crédito asociadas a un documento original.

        Args:
            documento_original_cdc: CDC del documento original
            empresa_id: ID de empresa (opcional, para filtrar)

        Returns:
            List[NotaCreditoElectronica]: Notas de crédito del documento
        """
        return self.get_notas_credito_by_criteria(
            empresa_id=empresa_id or 0,  # TODO: Obtener desde contexto
            documento_original_cdc=documento_original_cdc
        )

    def get_notas_credito_by_motivo(self,
                                    motivo_emision: str,
                                    empresa_id: int,
                                    fecha_desde: Optional[date] = None,
                                    fecha_hasta: Optional[date] = None) -> List[NotaCreditoElectronica]:
        """
        Filtra notas de crédito por motivo específico.

        Args:
            motivo_emision: Código del motivo (1-8)
            empresa_id: ID de empresa
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)

        Returns:
            List[NotaCreditoElectronica]: Notas de crédito del motivo
        """
        return self.get_notas_credito_by_criteria(
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            motivo_emision=motivo_emision
        )

    def get_devoluciones_periodo(self,
                                 empresa_id: int,
                                 fecha_desde: date,
                                 fecha_hasta: date) -> List[NotaCreditoElectronica]:
        """
        Obtiene todas las devoluciones (motivo 2) de un período.

        Args:
            empresa_id: ID de empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            List[NotaCreditoElectronica]: Devoluciones del período
        """
        return self.get_notas_credito_by_motivo(
            motivo_emision="2",  # Devolución
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )

    def get_descuentos_periodo(self,
                               empresa_id: int,
                               fecha_desde: date,
                               fecha_hasta: date) -> List[NotaCreditoElectronica]:
        """
        Obtiene todos los descuentos (motivo 3) de un período.

        Args:
            empresa_id: ID de empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            List[NotaCreditoElectronica]: Descuentos del período
        """
        return self.get_notas_credito_by_motivo(
            motivo_emision="3",  # Descuento
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
