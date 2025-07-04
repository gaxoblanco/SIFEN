# ===============================================
# ARCHIVO: backend/app/repositories/documento/utils.py
# PROPÓSITO: Utilidades compartidas para el módulo DocumentoRepository
# VERSIÓN: 1.0.0
# ===============================================

"""
Utilidades compartidas para el módulo DocumentoRepository.
Funciones helper comunes a todos los mixins.

Este módulo contiene funciones puras y reutilizables que son utilizadas
por diferentes mixins del DocumentoRepository para evitar duplicación
de código y mantener consistencia.

Funciones principales:
- Formateo de datos para display
- Validaciones auxiliares
- Construcción de queries dinámicas
- Utilidades de estados y fechas
- Helpers para estadísticas
"""

import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union, Tuple
from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import Query

from app.core.logging import get_logger
from app.models.documento import EstadoDocumentoSifenEnum
from datetime import timedelta

logger = get_logger(__name__)

# ===============================================
# CONSTANTES Y CONFIGURACIONES
# ===============================================

# Códigos de respuesta SIFEN exitosos
SIFEN_SUCCESS_CODES = ["0260", "1005"]

# Estados que permiten modificación
EDITABLE_STATES = [
    EstadoDocumentoSifenEnum.BORRADOR.value,
    EstadoDocumentoSifenEnum.VALIDADO.value
]

# Estados finales (no se pueden cambiar)
FINAL_STATES = [
    EstadoDocumentoSifenEnum.APROBADO.value,
    EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value,
    EstadoDocumentoSifenEnum.RECHAZADO.value,
    EstadoDocumentoSifenEnum.ANULADO.value
]

# Transiciones de estado válidas
VALID_STATE_TRANSITIONS = {
    EstadoDocumentoSifenEnum.BORRADOR.value: [
        EstadoDocumentoSifenEnum.VALIDADO.value,
        EstadoDocumentoSifenEnum.CANCELADO.value
    ],
    EstadoDocumentoSifenEnum.VALIDADO.value: [
        EstadoDocumentoSifenEnum.GENERADO.value,
        EstadoDocumentoSifenEnum.CANCELADO.value
    ],
    EstadoDocumentoSifenEnum.GENERADO.value: [
        EstadoDocumentoSifenEnum.FIRMADO.value,
        EstadoDocumentoSifenEnum.CANCELADO.value
    ],
    EstadoDocumentoSifenEnum.FIRMADO.value: [
        EstadoDocumentoSifenEnum.ENVIADO.value,
        EstadoDocumentoSifenEnum.CANCELADO.value
    ],
    EstadoDocumentoSifenEnum.ENVIADO.value: [
        EstadoDocumentoSifenEnum.APROBADO.value,
        EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value,
        EstadoDocumentoSifenEnum.RECHAZADO.value,
        EstadoDocumentoSifenEnum.ERROR_ENVIO.value
    ],
    EstadoDocumentoSifenEnum.ERROR_ENVIO.value: [
        EstadoDocumentoSifenEnum.ENVIADO.value,
        EstadoDocumentoSifenEnum.CANCELADO.value
    ],
    # Estados finales no tienen transiciones
    EstadoDocumentoSifenEnum.APROBADO.value: [],
    EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value: [
        EstadoDocumentoSifenEnum.ANULADO.value
    ],
    EstadoDocumentoSifenEnum.RECHAZADO.value: [],
    EstadoDocumentoSifenEnum.CANCELADO.value: [],
    EstadoDocumentoSifenEnum.ANULADO.value: []
}

# ===============================================
# UTILIDADES DE FORMATO
# ===============================================


def format_numero_completo(establecimiento: str, punto_expedicion: str, numero_documento: str) -> str:
    """
    Formatea número completo de documento: EST-PEX-NUM.

    Args:
        establecimiento: Código establecimiento
        punto_expedicion: Código punto expedición
        numero_documento: Número del documento

    Returns:
        str: Número formateado XXX-XXX-XXXXXXX

    Example:
        >>> format_numero_completo("1", "1", "123")
        "001-001-0000123"
    """
    try:
        est = str(establecimiento).zfill(3)
        pex = str(punto_expedicion).zfill(3)
        num = str(numero_documento).zfill(7)
        return f"{est}-{pex}-{num}"
    except Exception as e:
        logger.error(f"Error formateando número completo: {e}")
        return f"{establecimiento}-{punto_expedicion}-{numero_documento}"


def format_cdc_display(cdc: str) -> str:
    """
    Formatea CDC para display con espacios cada 4 dígitos.

    Args:
        cdc: CDC de 44 dígitos

    Returns:
        str: CDC formateado para display

    Example:
        >>> format_cdc_display("12345678901234567890123456789012345678901234")
        "1234 5678 9012 3456 7890 1234 5678 9012 3456 7890 1234"
    """
    if not cdc or len(cdc) != 44:
        return cdc

    # Insertar espacios cada 4 dígitos
    formatted = ""
    for i in range(0, len(cdc), 4):
        if i > 0:
            formatted += " "
        formatted += cdc[i:i+4]

    return formatted


def format_amounts_for_display(amount: Union[Decimal, float, int, str]) -> str:
    """
    Formatea montos para display con separadores de miles.

    Args:
        amount: Monto a formatear

    Returns:
        str: Monto formateado

    Example:
        >>> format_amounts_for_display(Decimal("1234567.89"))
        "1.234.567,89"
    """
    if not amount:
        return "0,00"

    try:
        # Convertir a Decimal para precisión
        if isinstance(amount, str):
            amount = Decimal(amount)
        elif isinstance(amount, (int, float)):
            amount = Decimal(str(amount))

        # Formatear con separadores paraguayos
        formatted = f"{amount:,.2f}"
        # Cambiar formato americano a paraguayo
        formatted = formatted.replace(",", "X").replace(
            ".", ",").replace("X", ".")

        return formatted
    except Exception as e:
        logger.error(f"Error formateando monto {amount}: {e}")
        return str(amount)


def format_dates_for_api(date_value: Union[datetime, date, str]) -> str:
    """
    Formatea fechas para respuesta API en formato ISO.

    Args:
        date_value: Fecha a formatear

    Returns:
        str: Fecha en formato ISO

    Example:
        >>> format_dates_for_api(date(2025, 1, 15))
        "2025-01-15"
    """
    if not date_value:
        return ""

    try:
        if isinstance(date_value, str):
            return date_value
        elif isinstance(date_value, datetime):
            return date_value.isoformat()
        elif isinstance(date_value, date):
            return date_value.isoformat()
        else:
            return str(date_value)
    except Exception as e:
        logger.error(f"Error formateando fecha {date_value}: {e}")
        return str(date_value)


# ===============================================
# UTILIDADES DE VALIDACIÓN
# ===============================================

def validate_cdc_format(cdc: str) -> bool:
    """
    Valida formato CDC de 44 dígitos.

    Args:
        cdc: CDC a validar

    Returns:
        bool: True si el formato es válido

    Example:
        >>> validate_cdc_format("12345678901234567890123456789012345678901234")
        True
    """
    if not cdc:
        return False

    # Limpiar espacios
    cdc_clean = cdc.replace(" ", "").strip()

    # Validar: exactamente 44 dígitos numéricos
    return bool(re.match(r'^\d{44}$', cdc_clean))


def validate_establishment_code(code: str) -> bool:
    """
    Valida código de establecimiento (001-999).

    Args:
        code: Código a validar

    Returns:
        bool: True si es válido

    Example:
        >>> validate_establishment_code("001")
        True
        >>> validate_establishment_code("000")
        False
    """
    if not code:
        return False

    try:
        num = int(code)
        return 1 <= num <= 999
    except ValueError:
        return False


def validate_document_number(number: str) -> bool:
    """
    Valida número de documento (0000001-9999999).

    Args:
        number: Número a validar

    Returns:
        bool: True si es válido

    Example:
        >>> validate_document_number("0000001")
        True
        >>> validate_document_number("0000000")
        False
    """
    if not number:
        return False

    try:
        num = int(number)
        return 1 <= num <= 9999999
    except ValueError:
        return False


def validate_amount_precision(amount: Union[Decimal, float, str]) -> bool:
    """
    Valida precisión de montos (máximo 4 decimales).

    Args:
        amount: Monto a validar

    Returns:
        bool: True si la precisión es válida

    Example:
        >>> validate_amount_precision(Decimal("123.4567"))
        True
        >>> validate_amount_precision(Decimal("123.45678"))
        False
    """
    if not amount:
        return True

    try:
        decimal_amount = Decimal(str(amount))
        # Verificar que no tenga más de 4 decimales
        # as_tuple() retorna DecimalTuple con exponent que puede ser int o str
        tuple_info = decimal_amount.as_tuple()
        exponent = tuple_info.exponent

        # Si es 'F', 'n', o 'N', es infinito/NaN, no válido para nuestro caso
        if isinstance(exponent, str):
            return False

        # Si es int, verificar que no sea más negativo que -4
        return exponent >= -4
    except Exception:
        return False


def is_potential_cdc(value: str) -> bool:
    """
    Verifica si un string podría ser un CDC.
    Más flexible que validate_cdc_format.

    Args:
        value: Valor a verificar

    Returns:
        bool: True si podría ser un CDC

    Example:
        >>> is_potential_cdc("1234567890123456789012345678901234567890123")
        True
        >>> is_potential_cdc("ABC123")
        False
    """
    if not value:
        return False

    # Limpiar espacios y guiones
    clean_value = value.replace(" ", "").replace("-", "").strip()

    # Verificar si es numérico y tiene longitud apropiada
    return (
        clean_value.isdigit() and
        40 <= len(clean_value) <= 44  # Rango flexible
    )


# ===============================================
# UTILIDADES DE ESTADO
# ===============================================

def get_next_valid_states(current_state: str) -> List[str]:
    """
    Obtiene los estados válidos siguientes para una transición.

    Args:
        current_state: Estado actual del documento

    Returns:
        List[str]: Lista de estados válidos siguientes

    Example:
        >>> get_next_valid_states("borrador")
        ["validado", "cancelado"]
    """
    return VALID_STATE_TRANSITIONS.get(current_state, [])


def is_final_state(state: str) -> bool:
    """
    Verifica si un estado es final (no permite más transiciones).

    Args:
        state: Estado a verificar

    Returns:
        bool: True si es un estado final

    Example:
        >>> is_final_state("aprobado")
        True
        >>> is_final_state("borrador")
        False
    """
    return state in FINAL_STATES


def is_editable_state(state: str) -> bool:
    """
    Verifica si un documento puede ser editado en el estado actual.

    Args:
        state: Estado del documento

    Returns:
        bool: True si el documento puede ser editado

    Example:
        >>> is_editable_state("borrador")
        True
        >>> is_editable_state("aprobado")
        False
    """
    return state in EDITABLE_STATES


def can_transition_to(current_state: str, target_state: str) -> bool:
    """
    Verifica si es posible transicionar de un estado a otro.

    Args:
        current_state: Estado actual
        target_state: Estado objetivo

    Returns:
        bool: True si la transición es válida

    Example:
        >>> can_transition_to("borrador", "validado")
        True
        >>> can_transition_to("aprobado", "borrador")
        False
    """
    valid_targets = get_next_valid_states(current_state)
    return target_state in valid_targets


def get_state_description(state: str) -> str:
    """
    Obtiene descripción humana del estado.

    Args:
        state: Estado del documento

    Returns:
        str: Descripción del estado

    Example:
        >>> get_state_description("aprobado")
        "Documento aprobado por SIFEN"
    """
    descriptions = {
        EstadoDocumentoSifenEnum.BORRADOR.value: "Documento en construcción",
        EstadoDocumentoSifenEnum.VALIDADO.value: "Datos validados, listo para generar XML",
        EstadoDocumentoSifenEnum.GENERADO.value: "XML generado, listo para firma",
        EstadoDocumentoSifenEnum.FIRMADO.value: "Documento firmado digitalmente",
        EstadoDocumentoSifenEnum.ENVIADO.value: "Enviado a SIFEN, esperando respuesta",
        EstadoDocumentoSifenEnum.APROBADO.value: "Documento aprobado por SIFEN",
        EstadoDocumentoSifenEnum.APROBADO_OBSERVACION.value: "Aprobado por SIFEN con observaciones",
        EstadoDocumentoSifenEnum.RECHAZADO.value: "Documento rechazado por SIFEN",
        EstadoDocumentoSifenEnum.ERROR_ENVIO.value: "Error en el envío a SIFEN",
        EstadoDocumentoSifenEnum.CANCELADO.value: "Documento cancelado por usuario",
        EstadoDocumentoSifenEnum.ANULADO.value: "Documento anulado oficialmente"
    }
    return descriptions.get(state, f"Estado desconocido: {state}")


# ===============================================
# UTILIDADES DE QUERIES
# ===============================================

def build_date_filter(query: Query, date_field, fecha_desde: Optional[date] = None,
                      fecha_hasta: Optional[date] = None) -> Query:
    """
    Construye filtro de fechas para queries.

    Args:
        query: Query SQLAlchemy
        date_field: Campo de fecha en el modelo
        fecha_desde: Fecha inicio (inclusive)
        fecha_hasta: Fecha fin (inclusive)

    Returns:
        Query: Query con filtro de fechas aplicado

    Example:
        >>> query = build_date_filter(query, Documento.fecha_emision, 
        ...                          date(2025, 1, 1), date(2025, 1, 31))
    """
    if fecha_desde:
        query = query.filter(date_field >= fecha_desde)

    if fecha_hasta:
        query = query.filter(date_field <= fecha_hasta)

    return query


def build_amount_filter(query: Query, amount_field, monto_minimo: Optional[Decimal] = None,
                        monto_maximo: Optional[Decimal] = None) -> Query:
    """
    Construye filtro de montos para queries.

    Args:
        query: Query SQLAlchemy
        amount_field: Campo de monto en el modelo
        monto_minimo: Monto mínimo (inclusive)
        monto_maximo: Monto máximo (inclusive)

    Returns:
        Query: Query con filtro de montos aplicado

    Example:
        >>> query = build_amount_filter(query, Documento.total_general, 
        ...                            Decimal("100000"), Decimal("1000000"))
    """
    if monto_minimo is not None:
        query = query.filter(amount_field >= monto_minimo)

    if monto_maximo is not None:
        query = query.filter(amount_field <= monto_maximo)

    return query


def build_search_conditions(model, search_fields: List[str], search_term: str):
    """
    Construye condiciones de búsqueda para múltiples campos.

    Args:
        model: Modelo SQLAlchemy
        search_fields: Lista de campos donde buscar
        search_term: Término de búsqueda

    Returns:
        Condiciones OR para búsqueda (SQLAlchemy expression)

    Example:
        >>> conditions = build_search_conditions(
        ...     Documento, 
        ...     ["numero_documento", "observaciones"], 
        ...     "factura"
        ... )
        >>> query = query.filter(conditions)
    """
    conditions = []
    search_pattern = f"%{search_term.lower()}%"

    for field_name in search_fields:
        if hasattr(model, field_name):
            field = getattr(model, field_name)
            conditions.append(func.lower(field).like(search_pattern))

    return or_(*conditions) if conditions else text("1=1")


def optimize_query_performance(query: Query) -> Query:
    """
    Aplica optimizaciones comunes a queries de documentos.

    Args:
        query: Query SQLAlchemy

    Returns:
        Query: Query optimizada

    Example:
        >>> optimized_query = optimize_query_performance(query)
    """
    # Aplicar índices sugeridos y optimizaciones
    return query.order_by(text("id DESC"))  # Uso de índice en ID


# ===============================================
# UTILIDADES DE ESTADÍSTICAS
# ===============================================

def calculate_percentage(numerator: Union[int, float], denominator: Union[int, float]) -> float:
    """
    Calcula porcentaje de forma segura.

    Args:
        numerator: Numerador
        denominator: Denominador

    Returns:
        float: Porcentaje calculado

    Example:
        >>> calculate_percentage(25, 100)
        25.0
        >>> calculate_percentage(25, 0)
        0.0
    """
    if not denominator or denominator == 0:
        return 0.0

    try:
        return (numerator / denominator) * 100
    except (ZeroDivisionError, TypeError):
        return 0.0


def format_stats_for_chart(data: List[Dict[str, Any]],
                           value_field: str,
                           label_field: str) -> List[Dict[str, Any]]:
    """
    Formatea datos estadísticos para gráficos.

    Args:
        data: Lista de diccionarios con datos
        value_field: Campo con el valor numérico
        label_field: Campo con la etiqueta

    Returns:
        List[Dict]: Datos formateados para gráficos

    Example:
        >>> data = [{"tipo": "factura", "cantidad": 10}]
        >>> formatted = format_stats_for_chart(data, "cantidad", "tipo")
        >>> # [{"label": "factura", "value": 10}]
    """
    formatted_data = []

    for item in data:
        if value_field in item and label_field in item:
            formatted_data.append({
                "label": item[label_field],
                "value": item[value_field]
            })

    return formatted_data


def aggregate_by_period(data: List[Dict[str, Any]],
                        date_field: str,
                        value_field: str,
                        period: str = "monthly") -> Dict[str, Any]:
    """
    Agrega datos por período temporal.

    Args:
        data: Lista de datos
        date_field: Campo de fecha
        value_field: Campo de valor a agregar
        period: Tipo de período (daily, weekly, monthly, yearly)

    Returns:
        Dict: Datos agregados por período

    Example:
        >>> data = [{"fecha": "2025-01-15", "monto": 1000}]
        >>> result = aggregate_by_period(data, "fecha", "monto", "monthly")
        >>> # {"2025-01": 1000}
    """
    aggregated = {}

    for item in data:
        if date_field not in item or value_field not in item:
            continue

        try:
            # Parsear fecha
            if isinstance(item[date_field], str):
                date_value = datetime.fromisoformat(
                    item[date_field].replace('Z', '+00:00'))
            else:
                date_value = item[date_field]

            # Generar clave del período
            if period == "daily":
                period_key = date_value.strftime("%Y-%m-%d")
            elif period == "weekly":
                period_key = f"{date_value.year}-W{date_value.isocalendar()[1]:02d}"
            elif period == "monthly":
                period_key = date_value.strftime("%Y-%m")
            elif period == "yearly":
                period_key = str(date_value.year)
            else:
                period_key = date_value.strftime("%Y-%m-%d")

            # Agregar valor
            if period_key not in aggregated:
                aggregated[period_key] = 0
            aggregated[period_key] += item[value_field]

        except Exception as e:
            logger.error(f"Error agregando datos por período: {e}")
            continue

    return aggregated


def calculate_growth_rate(current_value: Union[int, float],
                          previous_value: Union[int, float]) -> float:
    """
    Calcula tasa de crecimiento entre dos valores.

    Args:
        current_value: Valor actual
        previous_value: Valor anterior

    Returns:
        float: Tasa de crecimiento en porcentaje

    Example:
        >>> calculate_growth_rate(120, 100)
        20.0
        >>> calculate_growth_rate(80, 100)
        -20.0
    """
    if not previous_value or previous_value == 0:
        return 0.0 if current_value == 0 else 100.0

    try:
        return ((current_value - previous_value) / previous_value) * 100
    except (ZeroDivisionError, TypeError):
        return 0.0


# ===============================================
# UTILIDADES DE FECHAS
# ===============================================

def get_date_range_for_period(period: str,
                              reference_date: Optional[date] = None) -> Tuple[date, date]:
    """
    Obtiene rango de fechas para un período específico.

    Args:
        period: Tipo de período (today, yesterday, this_week, this_month, this_year)
        reference_date: Fecha de referencia (default: hoy)

    Returns:
        Tuple[date, date]: Fecha inicio y fecha fin

    Example:
        >>> start, end = get_date_range_for_period("this_month")
        >>> # (date(2025, 1, 1), date(2025, 1, 31))
    """
    if reference_date is None:
        reference_date = date.today()

    if period == "today":
        return reference_date, reference_date

    elif period == "yesterday":
        yesterday = reference_date - timedelta(days=1)
        return yesterday, yesterday

    elif period == "this_week":
        # Lunes a domingo
        days_since_monday = reference_date.weekday()
        monday = reference_date - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        return monday, sunday

    elif period == "this_month":
        # Primer día del mes hasta último día
        first_day = reference_date.replace(day=1)
        if reference_date.month == 12:
            last_day = reference_date.replace(
                year=reference_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = reference_date.replace(
                month=reference_date.month + 1, day=1) - timedelta(days=1)
        return first_day, last_day

    elif period == "this_year":
        # Primer día del año hasta último día
        first_day = reference_date.replace(month=1, day=1)
        last_day = reference_date.replace(month=12, day=31)
        return first_day, last_day

    else:
        # Por defecto, retornar el día actual
        return reference_date, reference_date


def is_within_sifen_time_limit(fecha_emision: date,
                               tiempo_limite_horas: int = 72) -> bool:
    """
    Verifica si un documento está dentro del tiempo límite para envío a SIFEN.

    Args:
        fecha_emision: Fecha de emisión del documento
        tiempo_limite_horas: Tiempo límite en horas (default: 72)

    Returns:
        bool: True si está dentro del límite

    Example:
        >>> is_within_sifen_time_limit(date.today())
        True
        >>> is_within_sifen_time_limit(date.today() - timedelta(days=4))
        False
    """
    if not fecha_emision:
        return False

    # Calcular tiempo transcurrido
    now = datetime.now()
    fecha_emision_dt = datetime.combine(fecha_emision, datetime.min.time())
    tiempo_transcurrido = now - fecha_emision_dt

    # Verificar si está dentro del límite
    return tiempo_transcurrido.total_seconds() <= (tiempo_limite_horas * 3600)


# ===============================================
# UTILIDADES DE NORMALIZACIÓN
# ===============================================

def normalize_cdc(cdc: str) -> str:
    """
    Normaliza un CDC removiendo espacios y caracteres especiales.

    Args:
        cdc: CDC a normalizar

    Returns:
        str: CDC normalizado

    Example:
        >>> normalize_cdc("1234 5678 9012 3456 7890 1234 5678 9012 3456 7890 1234")
        "12345678901234567890123456789012345678901234"
    """
    if not cdc:
        return ""

    # Remover espacios, guiones y otros caracteres no numéricos
    return re.sub(r'[^\d]', '', cdc)


def normalize_numero_completo(numero: str) -> str:
    """
    Normaliza un número completo a formato EST-PEX-NUM.

    Args:
        numero: Número a normalizar

    Returns:
        str: Número normalizado

    Example:
        >>> normalize_numero_completo("1-1-123")
        "001-001-0000123"
    """
    if not numero:
        return ""

    # Separar partes
    parts = numero.replace("-", "/").replace(".", "/").split("/")

    if len(parts) == 3:
        try:
            est = str(int(parts[0])).zfill(3)
            pex = str(int(parts[1])).zfill(3)
            num = str(int(parts[2])).zfill(7)
            return f"{est}-{pex}-{num}"
        except ValueError:
            pass

    return numero


# ===============================================
# UTILIDADES DE LOGGING
# ===============================================

def log_repository_operation(operation: str,
                             entity_type: str,
                             entity_id: Optional[Union[int, str]] = None,
                             details: Optional[Dict[str, Any]] = None) -> None:
    """
    Log estandarizado para operaciones del repository.

    Args:
        operation: Tipo de operación (create, update, delete, etc.)
        entity_type: Tipo de entidad
        entity_id: ID de la entidad (opcional)
        details: Detalles adicionales (opcional)

    Example:
        >>> log_repository_operation("create", "Documento", 123, {"tipo": "factura"})
    """
    message = f"Repository operation: {operation} {entity_type}"

    if entity_id:
        message += f" (ID: {entity_id})"

    extra_data = {"operation": operation, "entity_type": entity_type}

    if entity_id:
        # Convertir a string para evitar error de tipos
        extra_data["entity_id"] = str(entity_id)

    if details:
        extra_data.update(details)

    logger.info(message, extra=extra_data)


def log_performance_metric(operation: str,
                           duration: float,
                           record_count: Optional[int] = None,
                           details: Optional[Dict[str, Any]] = None) -> None:
    """
    Log de métricas de performance para operaciones del repository.

    Args:
        operation: Nombre de la operación
        duration: Duración en segundos
        record_count: Número de registros procesados (opcional)
        details: Detalles adicionales (opcional)

    Example:
        >>> log_performance_metric("search_documentos", 0.234, 50)
    """
    message = f"Performance metric: {operation} took {duration:.3f}s"

    if record_count:
        message += f" ({record_count} records)"

    extra_data = {
        "operation": operation,
        "duration": duration,
        "performance_category": "repository"
    }

    if record_count:
        extra_data["record_count"] = record_count

    if details:
        extra_data.update(details)

    # Log warning si la operación es muy lenta
    if duration > 5.0:
        logger.warning(f"Slow operation detected: {message}", extra=extra_data)
    else:
        logger.info(message, extra=extra_data)


# ===============================================
# UTILIDADES DE MANEJO DE ERRORES
# ===============================================

def handle_repository_error(error: Exception,
                            operation: str,
                            entity_type: str = "Documento",
                            entity_id: Optional[Union[int, str]] = None) -> None:
    """
    Manejo estandarizado de errores del repository.

    Args:
        error: Excepción capturada
        operation: Operación que falló
        entity_type: Tipo de entidad
        entity_id: ID de la entidad (opcional)

    Example:
        >>> try:
        ...     # operación repository
        ... except Exception as e:
        ...     handle_repository_error(e, "create", "Documento", 123)
    """
    message = f"Repository error in {operation} {entity_type}"

    if entity_id:
        message += f" (ID: {entity_id})"

    message += f": {str(error)}"

    extra_data = {
        "operation": operation,
        "entity_type": entity_type,
        "error_type": type(error).__name__,
        "error_message": str(error)
    }

    if entity_id:
        # Convertir a string para evitar error de tipos
        extra_data["entity_id"] = str(entity_id)

    logger.error(message, extra=extra_data, exc_info=True)


# ===============================================
# UTILIDADES DE CACHE
# ===============================================

def generate_cache_key(prefix: str, *args: Any) -> str:
    """
    Genera clave de cache consistente.

    Args:
        prefix: Prefijo de la clave
        *args: Argumentos para la clave

    Returns:
        str: Clave de cache

    Example:
        >>> generate_cache_key("documento_stats", "empresa", 123, "monthly")
        "documento_stats:empresa:123:monthly"
    """
    key_parts = [prefix]

    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))

    return ":".join(key_parts)


def should_use_cache(operation: str, record_count: Optional[int] = None) -> bool:
    """
    Determina si una operación debe usar cache.

    Args:
        operation: Tipo de operación
        record_count: Número de registros (opcional)

    Returns:
        bool: True si debe usar cache

    Example:
        >>> should_use_cache("get_stats", 1000)
        True
        >>> should_use_cache("create")
        False
    """
    # Operaciones que no deben usar cache
    no_cache_operations = ["create", "update", "delete"]

    if operation in no_cache_operations:
        return False

    # Operaciones de estadísticas siempre usan cache
    if "stats" in operation or "report" in operation:
        return True

    # Búsquedas grandes usan cache
    if record_count and record_count > 100:
        return True

    return False


# ===============================================
# UTILIDADES DE CONFIGURACIÓN
# ===============================================

def get_default_page_size() -> int:
    """
    Obtiene el tamaño de página por defecto para paginación.

    Returns:
        int: Tamaño de página por defecto
    """
    return 20


def get_max_page_size() -> int:
    """
    Obtiene el tamaño máximo de página permitido.

    Returns:
        int: Tamaño máximo de página
    """
    return 100


def get_search_timeout() -> int:
    """
    Obtiene el timeout para operaciones de búsqueda en segundos.

    Returns:
        int: Timeout en segundos
    """
    return 30


def get_stats_cache_ttl() -> int:
    """
    Obtiene el TTL del cache para estadísticas en segundos.

    Returns:
        int: TTL en segundos
    """
    return 300  # 5 minutos


# ===============================================
# UTILIDADES DE TESTING
# ===============================================

def create_test_cdc(sequence: int = 1) -> str:
    """
    Crea un CDC válido para testing.

    Args:
        sequence: Número de secuencia

    Returns:
        str: CDC válido para testing

    Example:
        >>> cdc = create_test_cdc(1)
        >>> # "12345678901234567890123456789012345678901234"
    """
    # Generar CDC base con patrón repetitivo
    base = "1234567890"
    cdc_base = (base * 5)[:44]  # 44 caracteres

    # Modificar últimos dígitos con secuencia
    sequence_str = str(sequence).zfill(4)
    cdc = cdc_base[:-4] + sequence_str

    return cdc


def create_test_numero_completo(sequence: int = 1) -> str:
    """
    Crea un número completo válido para testing.

    Args:
        sequence: Número de secuencia

    Returns:
        str: Número completo para testing

    Example:
        >>> numero = create_test_numero_completo(1)
        >>> # "001-001-0000001"
    """
    return f"001-001-{str(sequence).zfill(7)}"


def is_test_environment() -> bool:
    """
    Detecta si el código está ejecutándose en ambiente de testing.

    Returns:
        bool: True si es ambiente de testing
    """
    import sys
    return "pytest" in sys.modules or "unittest" in sys.modules


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # Constantes
    "SIFEN_SUCCESS_CODES",
    "EDITABLE_STATES",
    "FINAL_STATES",
    "VALID_STATE_TRANSITIONS",

    # Utilidades de formato
    "format_numero_completo",
    "format_cdc_display",
    "format_amounts_for_display",
    "format_dates_for_api",

    # Utilidades de validación
    "validate_cdc_format",
    "validate_establishment_code",
    "validate_document_number",
    "validate_amount_precision",
    "is_potential_cdc",

    # Utilidades de estado
    "get_next_valid_states",
    "is_final_state",
    "is_editable_state",
    "can_transition_to",
    "get_state_description",

    # Utilidades de queries
    "build_date_filter",
    "build_amount_filter",
    "build_search_conditions",
    "optimize_query_performance",

    # Utilidades de estadísticas
    "calculate_percentage",
    "format_stats_for_chart",
    "aggregate_by_period",
    "calculate_growth_rate",

    # Utilidades de fechas
    "get_date_range_for_period",
    "is_within_sifen_time_limit",

    # Utilidades de normalización
    "normalize_cdc",
    "normalize_numero_completo",

    # Utilidades de logging
    "log_repository_operation",
    "log_performance_metric",
    "handle_repository_error",

    # Utilidades de cache
    "generate_cache_key",
    "should_use_cache",

    # Utilidades de configuración
    "get_default_page_size",
    "get_max_page_size",
    "get_search_timeout",
    "get_stats_cache_ttl",

    # Utilidades de testing
    "create_test_cdc",
    "create_test_numero_completo",
    "is_test_environment"
]
