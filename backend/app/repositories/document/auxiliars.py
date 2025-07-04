# ===============================================
# ARCHIVO: backend/app/repositories/documento/auxiliares.py
# PROPÓSITO: Métodos auxiliares compartidos entre mixins de tipos de documento
# VERSIÓN: 1.0.0
# ===============================================

"""
Métodos auxiliares compartidos para mixins de tipos de documento SIFEN.
Contiene funcionalidades comunes que son utilizadas por DocumentTypesMixin
y DocumentTypesMixinT4 para evitar duplicación de código.

Funciones principales:
- Aplicación de configuraciones por defecto
- Validaciones específicas por tipo de documento
- Gestión de documentos originales
- Validaciones de montos y fechas
- Helpers para items y relaciones
"""

from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.exceptions import (
    SifenValidationError,
    SifenEntityNotFoundError,
    SifenBusinessLogicError
)
from app.models.documento import (
    Documento,
    TipoDocumentoSifenEnum,
    MonedaSifenEnum
)
from .utils import normalize_cdc, get_default_page_size, get_max_page_size, build_date_filter, build_amount_filter

logger = get_logger(__name__)

# ===============================================
# CONFIGURACIONES Y CONSTANTES
# ===============================================

# Configuraciones por defecto por tipo de documento
DEFAULT_CONFIGURATIONS = {
    TipoDocumentoSifenEnum.FACTURA.value: {
        "tipo_operacion": "1",  # Venta
        "condicion_operacion": "1",  # Contado
        "moneda": MonedaSifenEnum.PYG.value,
        "require_items": True,
        "min_amount": Decimal("1.00")
    },
    TipoDocumentoSifenEnum.AUTOFACTURA.value: {
        "tipo_operacion": "3",  # Importación
        "condicion_operacion": "1",  # Contado
        "moneda": MonedaSifenEnum.USD.value,
        "require_items": True,
        "min_amount": Decimal("1.00")
    },
    TipoDocumentoSifenEnum.NOTA_CREDITO.value: {
        "tipo_operacion": "1",  # Venta
        "condicion_operacion": "1",  # Contado
        "moneda": MonedaSifenEnum.PYG.value,
        "require_items": True,
        "min_amount": Decimal("1.00"),
        "require_original": True
    },
    TipoDocumentoSifenEnum.NOTA_DEBITO.value: {
        "tipo_operacion": "1",  # Venta
        "condicion_operacion": "1",  # Contado
        "moneda": MonedaSifenEnum.PYG.value,
        "require_items": True,
        "min_amount": Decimal("1.00"),
        "require_original": True
    },
    TipoDocumentoSifenEnum.NOTA_REMISION.value: {
        "tipo_operacion": "1",  # Venta
        "condicion_operacion": "1",  # Contado
        "moneda": MonedaSifenEnum.PYG.value,
        "require_items": True,
        "exact_amount": Decimal("0.00")
    }
}

# ===============================================
# MÉTODOS AUXILIARES DE CONFIGURACIÓN
# ===============================================


def apply_default_config(document_data: Dict[str, Any], tipo_documento: str) -> None:
    """
    Aplica configuraciones por defecto según el tipo de documento.

    Args:
        document_data: Datos del documento
        tipo_documento: Tipo de documento

    Example:
        >>> data = {"numero_documento": "123"}
        >>> apply_default_config(data, "1")
        >>> # data ahora incluye configuraciones por defecto para facturas
    """
    config = DEFAULT_CONFIGURATIONS.get(tipo_documento, {})

    for key, default_value in config.items():
        if key not in document_data:
            document_data[key] = default_value


# ===============================================
# VALIDACIONES ESPECÍFICAS POR TIPO
# ===============================================

def validate_factura_data(factura_data: Dict[str, Any]) -> None:
    """
    Valida datos específicos de facturas electrónicas.

    Args:
        factura_data: Datos de la factura a validar

    Raises:
        SifenValidationError: Si los datos no son válidos

    Example:
        >>> validate_factura_data({
        ...     "total_general": Decimal("1100000"),
        ...     "moneda": "PYG"
        ... })
    """
    # Validar que tenga monto mayor a 0
    total_general = factura_data.get("total_general", Decimal("0"))
    if isinstance(total_general, (str, int, float)):
        total_general = Decimal(str(total_general))

    if total_general <= 0:
        raise SifenValidationError(
            "Las facturas deben tener un monto mayor a 0",
            field="total_general",
            value=total_general
        )

    # Validar moneda para facturas (generalmente PYG)
    moneda = factura_data.get("moneda", "PYG")
    if moneda not in [e.value for e in MonedaSifenEnum]:
        raise SifenValidationError(
            f"Moneda '{moneda}' no es válida para facturas",
            field="moneda",
            value=moneda
        )


def validate_autofactura_data(autofactura_data: Dict[str, Any],
                              import_data: Optional[Dict[str, Any]]) -> None:
    """
    Valida datos específicos de autofacturas electrónicas.

    Args:
        autofactura_data: Datos de la autofactura
        import_data: Datos de importación (opcional)

    Raises:
        SifenValidationError: Si los datos no son válidos

    Example:
        >>> validate_autofactura_data({
        ...     "tipo_operacion": "3",
        ...     "moneda": "USD"
        ... }, {"aduana": "Aeropuerto", "declaracion_importacion": "DIM-123"})
    """
    # Validar tipo de operación (generalmente importación)
    tipo_operacion = autofactura_data.get("tipo_operacion", "")
    if tipo_operacion != "3":  # Importación
        logger.warning(
            f"Autofactura con tipo de operación {tipo_operacion} - "
            "generalmente se usan para importaciones (tipo 3)"
        )

    # Validar datos de importación si se proporcionan
    if import_data:
        required_import_fields = ["aduana", "declaracion_importacion"]
        for field in required_import_fields:
            if field not in import_data:
                raise SifenValidationError(
                    f"Campo de importación requerido: {field}",
                    field=field
                )


def validate_nota_credito_data(nota_data: Dict[str, Any],
                               documento_original: Documento) -> None:
    """
    Valida datos específicos de notas de crédito electrónicas.

    Args:
        nota_data: Datos de la nota de crédito
        documento_original: Documento original de referencia

    Raises:
        SifenValidationError: Si los datos no son válidos
        SifenBusinessLogicError: Si hay errores de lógica de negocio

    Example:
        >>> validate_nota_credito_data({
        ...     "total_general": Decimal("550000"),
        ...     "motivo_credito": "Devolución producto"
        ... }, documento_original)
    """
    # Validar monto contra documento original
    validate_credit_amounts(nota_data, documento_original)

    # Validar que tenga motivo
    if "motivo_credito" not in nota_data:
        raise SifenValidationError(
            "Notas de crédito requieren motivo específico",
            field="motivo_credito"
        )


def validate_nota_debito_data(nota_data: Dict[str, Any],
                              documento_original: Documento) -> None:
    """
    Valida datos específicos de notas de débito electrónicas.

    Args:
        nota_data: Datos de la nota de débito
        documento_original: Documento original de referencia

    Raises:
        SifenValidationError: Si los datos no son válidos

    Example:
        >>> validate_nota_debito_data({
        ...     "total_general": Decimal("110000"),
        ...     "motivo_debito": "Intereses por mora"
        ... }, documento_original)
    """
    # Validar que tenga motivo
    if "motivo_debito" not in nota_data:
        raise SifenValidationError(
            "Notas de débito requieren motivo específico",
            field="motivo_debito"
        )

    # Validar monto positivo
    total_general = nota_data.get("total_general", Decimal("0"))
    if isinstance(total_general, (str, int, float)):
        total_general = Decimal(str(total_general))

    if total_general <= 0:
        raise SifenValidationError(
            "Las notas de débito deben tener un monto mayor a 0",
            field="total_general",
            value=total_general
        )


def validate_nota_remision_data(nota_data: Dict[str, Any],
                                datos_transporte: Dict[str, Any]) -> None:
    """
    Valida datos específicos de notas de remisión electrónicas.

    Args:
        nota_data: Datos de la nota de remisión
        datos_transporte: Datos del transporte

    Raises:
        SifenValidationError: Si los datos no son válidos

    Example:
        >>> validate_nota_remision_data({
        ...     "total_general": Decimal("0")
        ... }, {
        ...     "motivo_traslado": "Traslado entre sucursales",
        ...     "fecha_inicio_traslado": date.today()
        ... })
    """
    # Validar que el monto sea 0
    total_general = nota_data.get("total_general", Decimal("0"))
    if isinstance(total_general, (str, int, float)):
        total_general = Decimal(str(total_general))

    if total_general != 0:
        raise SifenValidationError(
            "Las notas de remisión deben tener monto 0",
            field="total_general",
            value=total_general
        )

    # Validar datos de transporte
    validate_transport_data(datos_transporte)


def validate_nota_credito_item(item: Dict[str, Any], index: int) -> None:
    """
    Valida un item individual de la nota de crédito.

    Aplica validaciones específicas para items de NCE según normativa SIFEN v150
    y reglas de negocio Paraguay. Incluye validaciones de estructura y coherencia.

    Args:
        item: Datos del item a validar
        index: Índice del item en la lista (base 0)

    Raises:
        SifenValidationError: Si el item no cumple validaciones NCE

    Example:
        ```python
        item = {
            "descripcion": "Producto devuelto",
            "cantidad": -1,
            "precio_unitario": Decimal("-100000"),
            "tipo_iva": "10"
        }
        self.validate_nota_credito_item(item, 0)  # Validación exitosa
        ```

    Note:
        Validaciones específicas para NCE. Diferentes a validaciones de facturas.
    """
    start_time = datetime.now()

    try:
        # 1. Validar campos requeridos según SIFEN v150
        required_fields = ["descripcion", "cantidad", "precio_unitario"]

        for field in required_fields:
            if field not in item or item[field] is None:
                raise SifenValidationError(
                    f"Campo requerido en item {index + 1}: {field}",
                    field=f"items[{index}].{field}",
                    details={
                        "item_index": index,
                        "campo_faltante": field,
                        "campos_presentes": list(item.keys())
                    }
                )

        # 2. Validar tipos de datos y rangos
        try:
            cantidad = float(item["cantidad"])
            precio = float(Decimal(str(item["precio_unitario"])))
        except (ValueError, TypeError, InvalidOperation) as e:
            raise SifenValidationError(
                f"Valores numéricos inválidos en item {index + 1}",
                field=f"items[{index}]",
                details={
                    "item_index": index,
                    "cantidad": item.get("cantidad"),
                    "precio_unitario": item.get("precio_unitario"),
                    "conversion_error": str(e)
                }
            )

        # 3. Validar descripción no vacía
        descripcion = str(item.get("descripcion", "")).strip()
        if len(descripcion) < 3:
            raise SifenValidationError(
                f"Descripción muy corta en item {index + 1} (mínimo 3 caracteres)",
                field=f"items[{index}].descripcion",
                value=descripcion
            )

        # 4. Advertencia por valores positivos (típicamente negativos en NCE)
        if cantidad > 0 or precio > 0:
            logger.info(
                "NCE_ITEM_VALORES_POSITIVOS",
                extra={
                    "modulo": "document_types_t5",
                    "item_index": index,
                    "cantidad": cantidad,
                    "precio": precio,
                    "mensaje": "Item con valores positivos - verificar si es correcto para NCE"
                }
            )

        # 5. Validar tipo de IVA si está presente
        if "tipo_iva" in item:
            tipo_iva = item["tipo_iva"]
            if tipo_iva not in ["exento", "exonerado", "5", "10"]:
                raise SifenValidationError(
                    f"Tipo de IVA inválido en item {index + 1}",
                    field=f"items[{index}].tipo_iva",
                    value=tipo_iva,
                    details={"tipos_validos": [
                        "exento", "exonerado", "5", "10"]}
                )

        # 6. Log de performance si es lenta
        duration = (datetime.now() - start_time).total_seconds()
        if duration > 0.05:  # Más de 50ms por item
            logger.warning(
                "NCE_ITEM_VALIDATION_SLOW",
                extra={
                    "modulo": "document_types_t5",
                    "operacion": "validate_nota_credito_item",
                    "item_index": index,
                    "duration_ms": duration * 1000
                }
            )

    except SifenValidationError:
        # Re-raise errores de validación sin modificar
        raise
    except Exception as e:
        # Capturar errores inesperados
        logger.error(
            "NCE_ITEM_VALIDATION_ERROR",
            extra={
                "modulo": "document_types_t5",
                "operacion": "validate_nota_credito_item",
                "item_index": index,
                "error": str(e),
                "item_data": item
            }
        )
        raise SifenValidationError(
            f"Error inesperado validando item {index + 1}",
            field=f"items[{index}]",
            details={"error": str(e)}
        )

# ===============================================
# VALIDACIONES DE TRANSPORTE Y FECHAS
# ===============================================


def validate_transport_data(datos_transporte: Dict[str, Any]) -> None:
    """
    Valida datos de transporte para notas de remisión.

    Args:
        datos_transporte: Datos del transporte

    Raises:
        SifenValidationError: Si los datos no son válidos

    Example:
        >>> validate_transport_data({
        ...     "motivo_traslado": "Traslado entre sucursales",
        ...     "fecha_inicio_traslado": date.today()
        ... })
    """
    required_fields = ["motivo_traslado", "fecha_inicio_traslado"]

    for field in required_fields:
        if field not in datos_transporte:
            raise SifenValidationError(
                f"Campo de transporte requerido: {field}",
                field=field
            )

    # Validar fechas
    fecha_inicio = datos_transporte.get("fecha_inicio_traslado")
    fecha_fin = datos_transporte.get("fecha_fin_traslado")

    if fecha_inicio and fecha_fin:
        validate_movement_dates(fecha_inicio, fecha_fin)


def validate_movement_dates(fecha_inicio: date, fecha_fin: Optional[date]) -> None:
    """
    Valida fechas de movimiento para traslados.

    Args:
        fecha_inicio: Fecha de inicio del traslado
        fecha_fin: Fecha de fin del traslado (opcional)

    Raises:
        SifenValidationError: Si las fechas no son válidas

    Example:
        >>> validate_movement_dates(date.today(), date.today() + timedelta(days=1))
    """
    if fecha_inicio < date.today():
        raise SifenValidationError(
            "La fecha de inicio no puede ser anterior a hoy",
            field="fecha_inicio_traslado",
            value=fecha_inicio
        )

    if fecha_fin and fecha_fin < fecha_inicio:
        raise SifenValidationError(
            "La fecha de fin no puede ser anterior a la fecha de inicio",
            field="fecha_fin_traslado",
            value=fecha_fin
        )


# ===============================================
# GESTIÓN DE DOCUMENTOS ORIGINALES
# ===============================================

def validate_and_get_original_document(db: Session, model: type,
                                       documento_original_cdc: str) -> Documento:
    """
    Valida y obtiene el documento original para notas de crédito/débito.

    Args:
        db: Sesión de base de datos
        model: Modelo Documento
        documento_original_cdc: CDC del documento original

    Returns:
        Documento: Documento original encontrado

    Raises:
        SifenValidationError: Si el CDC no es válido
        SifenEntityNotFoundError: Si el documento no existe

    Example:
        >>> doc_original = validate_and_get_original_document(
        ...     db, Documento, "12345678901234567890123456789012345678901234"
        ... )
    """
    if not documento_original_cdc:
        raise SifenValidationError(
            "CDC del documento original es requerido",
            field="documento_original_cdc"
        )

    # Normalizar CDC
    cdc_normalized = normalize_cdc(documento_original_cdc)

    # Buscar documento original
    documento_original = db.query(model).filter(
        text("cdc = :cdc")
    ).params(cdc=cdc_normalized).first()

    if not documento_original:
        raise SifenEntityNotFoundError(
            "Documento original", documento_original_cdc)

    return documento_original


def validate_credit_amounts(nota_data: Dict[str, Any],
                            documento_original: Documento) -> None:
    """
    Valida montos de nota de crédito contra documento original.

    Args:
        nota_data: Datos de la nota de crédito
        documento_original: Documento original

    Raises:
        SifenBusinessLogicError: Si el monto es mayor al original

    Example:
        >>> validate_credit_amounts({
        ...     "total_general": Decimal("550000")
        ... }, documento_original)
    """
    total_nota = nota_data.get("total_general", Decimal("0"))
    if isinstance(total_nota, (str, int, float)):
        total_nota = Decimal(str(total_nota))

    total_original = getattr(documento_original, 'total_general', Decimal("0"))

    if total_nota > total_original:
        raise SifenBusinessLogicError(
            f"El monto de la nota de crédito ({total_nota}) no puede ser mayor "
            f"al monto del documento original ({total_original})",
            details={
                "total_nota": float(total_nota),
                "total_original": float(total_original)
            }
        )


# ===============================================
# HELPERS PARA QUERIES Y FILTROS
# ===============================================

def get_documents_by_type_and_criteria(db: Session, model: type,
                                       tipo_documento: str,
                                       empresa_id: int,
                                       fecha_desde: Optional[date],
                                       fecha_hasta: Optional[date],
                                       monto_minimo: Optional[Decimal],
                                       monto_maximo: Optional[Decimal],
                                       estados: Optional[List[str]],
                                       limit: Optional[int],
                                       offset: int) -> List[Documento]:
    """
    Obtiene documentos por tipo y criterios diversos.

    Args:
        db: Sesión de base de datos
        model: Modelo Documento
        tipo_documento: Tipo de documento SIFEN
        empresa_id: ID de la empresa
        fecha_desde: Fecha inicio del rango (opcional)
        fecha_hasta: Fecha fin del rango (opcional)
        monto_minimo: Monto mínimo (opcional)
        monto_maximo: Monto máximo (opcional)
        estados: Lista de estados (opcional)
        limit: Número máximo de resultados (opcional)
        offset: Número de resultados a omitir

    Returns:
        List[Documento]: Lista de documentos que cumplen los criterios

    Example:
        >>> docs = get_documents_by_type_and_criteria(
        ...     db, Documento, "1", 1, 
        ...     date(2025, 1, 1), date(2025, 1, 31),
        ...     None, None, ["aprobado"], 20, 0
        ... )
    """
    # Construir query
    query = db.query(model).filter(
        and_(
            model.tipo_documento == tipo_documento,
            model.empresa_id == empresa_id
        )
    )

    # Aplicar filtros
    if fecha_desde or fecha_hasta:
        query = build_date_filter(
            query, model.fecha_emision, fecha_desde, fecha_hasta)

    if monto_minimo or monto_maximo:
        query = build_amount_filter(
            query, model.total_general, monto_minimo, monto_maximo)

    if estados:
        query = query.filter(text("estado IN :estados")).params(
            estados=tuple(estados))

    # Aplicar paginación
    if limit is None:
        limit = get_default_page_size()
    elif limit > get_max_page_size():
        limit = get_max_page_size()

    return query.order_by(model.created_at.desc()).offset(offset).limit(limit).all()


# ===============================================
# HELPERS PARA ITEMS Y CÁLCULOS
# ===============================================

def calculate_totals_from_items(document_data: Dict[str, Any],
                                items: List[Dict[str, Any]]) -> None:
    """
    Calcula totales automáticamente desde items.

    Args:
        document_data: Datos del documento
        items: Lista de items

    Note:
        Por ahora mantiene los totales proporcionados.
        TODO: Implementar cálculo automático de totales cuando sea necesario.

    Example:
        >>> calculate_totals_from_items(document_data, items_list)
    """
    # TODO: Implementar cálculo automático de totales
    # Por ahora, mantener los totales proporcionados
    pass


def create_items_for_document(db: Session, documento: Documento,
                              items: List[Dict[str, Any]]) -> None:
    """
    Crea items para un documento.

    Args:
        db: Sesión de base de datos
        documento: Documento al que pertenecen los items
        items: Lista de items a crear

    Note:
        TODO: Implementar creación de items cuando tabla esté disponible.

    Example:
        >>> create_items_for_document(db, documento, items_list)
    """
    # TODO: Implementar creación de items cuando tabla esté disponible
    pass


def adjust_items_for_remision(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ajusta items para nota de remisión (precios en 0).

    Args:
        items: Lista de items originales

    Returns:
        List[Dict[str, Any]]: Items ajustados con precios en 0

    Example:
        >>> items_ajustados = adjust_items_for_remision([
        ...     {"precio_unitario": Decimal("100"), "cantidad": 1}
        ... ])
        >>> # [{"precio_unitario": Decimal("0"), "cantidad": 1, "total_item": Decimal("0")}]
    """
    items_adjusted = []
    for item in items:
        item_copy = item.copy()
        item_copy["precio_unitario"] = Decimal("0.00")
        item_copy["total_item"] = Decimal("0.00")
        items_adjusted.append(item_copy)
    return items_adjusted


# ===============================================
# HELPERS PARA VINCULACIONES
# ===============================================

def link_import_data(autofactura: Any, import_data: Dict[str, Any]) -> None:
    """
    Vincula datos de importación a una autofactura.

    Args:
        autofactura: Instancia de AutofacturaElectronica
        import_data: Datos de importación

    Note:
        TODO: Implementar vinculación de datos de importación cuando esté disponible.

    Example:
        >>> link_import_data(autofactura, {
        ...     "aduana": "Aeropuerto Silvio Pettirossi",
        ...     "declaracion_importacion": "DIM-2025-001234"
        ... })
    """
    # TODO: Implementar vinculación de datos de importación
    pass


def link_original_document(nota: Any, documento_original: Documento) -> None:
    """
    Vincula documento original a una nota de crédito/débito.

    Args:
        nota: Instancia de NotaCreditoElectronica o NotaDebitoElectronica
        documento_original: Documento original

    Note:
        El CDC ya está asignado en documento_original_cdc del objeto nota.

    Example:
        >>> link_original_document(nota_credito, factura_original)
    """
    # El CDC ya está asignado en documento_original_cdc
    pass


def link_transport_info(nota: Any, datos_transporte: Dict[str, Any]) -> None:
    """
    Vincula información de transporte a una nota de remisión.

    Args:
        nota: Instancia de NotaRemisionElectronica
        datos_transporte: Datos del transporte

    Note:
        Los datos ya están incorporados en el objeto nota.

    Example:
        >>> link_transport_info(nota_remision, {
        ...     "motivo_traslado": "Traslado entre sucursales",
        ...     "transportista": "Transportes SA"
        ... })
    """
    # Los datos ya están en el objeto nota
    pass


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # Configuraciones
    "DEFAULT_CONFIGURATIONS",

    # Configuración y aplicación
    "apply_default_config",

    # Validaciones por tipo
    "validate_factura_data",
    "validate_autofactura_data",
    "validate_nota_credito_data",
    "validate_nota_debito_data",
    "validate_nota_remision_data",

    # Validaciones de transporte y fechas
    "validate_transport_data",
    "validate_movement_dates",

    # Gestión de documentos originales
    "validate_and_get_original_document",
    "validate_credit_amounts",

    # Helpers para queries
    "get_documents_by_type_and_criteria",

    # Helpers para items y cálculos
    "calculate_totals_from_items",
    "create_items_for_document",
    "adjust_items_for_remision",

    # Helpers para vinculaciones
    "link_import_data",
    "link_original_document",
    "link_transport_info"
]
