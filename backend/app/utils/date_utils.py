"""
Utilidades para manejo de fechas en Paraguay para SIFEN v150.

Este módulo proporciona funcionalidades específicas para el manejo correcto
de fechas y zona horaria de Paraguay según las especificaciones SIFEN v150.
Incluye conversiones, validaciones y formateo adecuado para documentos
electrónicos.

CARACTERÍSTICAS DE FECHA/HORA SIFEN PARAGUAY:
- Zona horaria: America/Asuncion (UTC-3)
- Formato fecha: YYYY-MM-DD  
- Formato fecha-hora: YYYY-MM-DDTHH:MM:SS
- Precisión: Hasta segundos (sin milisegundos)
- Rango válido: 2010-01-01 hasta 2099-12-31
- Restricciones: No fechas futuras para emisión

HORARIO DE VERANO:
- Paraguay NO usa horario de verano desde 2013
- Offset fijo UTC-3 todo el año
- Zona horaria estable para cálculos

CASOS DE USO:
- Formatear fechas para documentos SIFEN
- Validar fechas de emisión y vencimiento
- Convertir entre zonas horarias
- Calcular límites temporales para envío

Autor: Sistema de Gestión de Documentos
Versión: 1.0.0
Fecha: 2025-07-01
"""

import re
from datetime import datetime, date, timezone, timedelta
from typing import Optional, Union, Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum
import pytz


# ===================================================================
# CONSTANTES Y CONFIGURACIÓN
# ===================================================================

# Zona horaria oficial de Paraguay
PARAGUAY_TIMEZONE = pytz.timezone('America/Asuncion')

# Offset fijo de Paraguay (UTC-3, sin horario de verano desde 2013)
PARAGUAY_OFFSET = timedelta(hours=-3)

# Patrones de formato SIFEN
PATTERN_DATE_SIFEN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
PATTERN_DATETIME_SIFEN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')
PATTERN_DATE_CDC = re.compile(r'^\d{8}$')  # YYYYMMDD para CDC

# Límites de fechas SIFEN
MIN_SIFEN_DATE = date(2010, 1, 1)
MAX_SIFEN_DATE = date(2099, 12, 31)

# Límites temporales para envío de documentos (según Manual v150)
SIFEN_TIME_LIMITS = {
    'NORMAL_LIMIT_HOURS': 72,           # Hasta 72h = Normal
    'EXTEMPORANEOUS_LIMIT_HOURS': 720,  # Hasta 720h = Extemporáneo
    'REJECTION_THRESHOLD_HOURS': 720,   # Más de 720h = Rechazado
    'FUTURE_TOLERANCE_MINUTES': 5,      # Tolerancia para fechas futuras
}

# Formatos de entrada comunes
COMMON_DATE_FORMATS = [
    '%Y-%m-%d',           # 2025-07-01
    '%d/%m/%Y',           # 01/07/2025
    '%d-%m-%Y',           # 01-07-2025
    '%Y/%m/%d',           # 2025/07/01
    '%d.%m.%Y',           # 01.07.2025
]

COMMON_DATETIME_FORMATS = [
    '%Y-%m-%dT%H:%M:%S',      # 2025-07-01T14:30:00
    '%Y-%m-%d %H:%M:%S',      # 2025-07-01 14:30:00
    '%d/%m/%Y %H:%M:%S',      # 01/07/2025 14:30:00
    '%d/%m/%Y %H:%M',         # 01/07/2025 14:30
    '%Y-%m-%dT%H:%M:%S.%f',   # 2025-07-01T14:30:00.123456
]


# ===================================================================
# ENUMERACIONES
# ===================================================================

class TipoFecha(Enum):
    """Tipos de fecha según contexto SIFEN."""
    EMISION = "emision"           # Fecha de emisión del documento
    VENCIMIENTO = "vencimiento"   # Fecha de vencimiento
    RECEPCION = "recepcion"       # Fecha de recepción/procesamiento
    EVENTO = "evento"             # Fecha de eventos
    VIGENCIA = "vigencia"         # Fechas de vigencia (timbrado)


class EstadoValidacionFecha(Enum):
    """Estados posibles de validación de fecha."""
    VALIDA = "valida"
    FUTURA = "futura"
    MUY_ANTIGUA = "muy_antigua"
    FORMATO_INVALIDO = "formato_invalido"
    FUERA_DE_RANGO = "fuera_de_rango"


# ===================================================================
# CLASES DE DATOS
# ===================================================================

@dataclass
class FechaValidationResult:
    """
    Resultado de validación de fecha.

    Attributes:
        is_valid (bool): True si la fecha es válida
        fecha_parsed (Optional[datetime]): Fecha parseada
        error_message (str): Mensaje de error si no es válida
        error_code (str): Código de error para manejo programático
        estado (EstadoValidacionFecha): Estado específico de validación
        suggestions (List[str]): Sugerencias para corregir errores
    """
    is_valid: bool
    fecha_parsed: Optional[datetime] = None
    error_message: str = ""
    error_code: str = ""
    estado: Optional[EstadoValidacionFecha] = None
    suggestions: Optional[List[str]] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class RangoFechas:
    """
    Rango de fechas para validaciones.

    Attributes:
        fecha_inicio (datetime): Fecha de inicio del rango
        fecha_fin (datetime): Fecha de fin del rango
        incluir_inicio (bool): Si incluir la fecha de inicio
        incluir_fin (bool): Si incluir la fecha de fin
    """
    fecha_inicio: datetime
    fecha_fin: datetime
    incluir_inicio: bool = True
    incluir_fin: bool = True

    def contiene(self, fecha: datetime) -> bool:
        """Verifica si una fecha está dentro del rango."""
        if self.incluir_inicio and self.incluir_fin:
            return self.fecha_inicio <= fecha <= self.fecha_fin
        elif self.incluir_inicio and not self.incluir_fin:
            return self.fecha_inicio <= fecha < self.fecha_fin
        elif not self.incluir_inicio and self.incluir_fin:
            return self.fecha_inicio < fecha <= self.fecha_fin
        else:
            return self.fecha_inicio < fecha < self.fecha_fin


# ===================================================================
# FUNCIONES PRINCIPALES DE ZONA HORARIA
# ===================================================================

def get_paraguay_timezone() -> pytz.BaseTzInfo:
    """
    Obtiene la zona horaria oficial de Paraguay.

    Returns:
        pytz.BaseTzInfo: Zona horaria America/Asuncion

    Examples:
        >>> tz = get_paraguay_timezone()
        >>> print(tz.zone)  # 'America/Asuncion'
    """
    return PARAGUAY_TIMEZONE


def get_current_paraguay_datetime() -> datetime:
    """
    Obtiene la fecha/hora actual en Paraguay.

    Returns:
        datetime: Fecha/hora actual en zona horaria Paraguay

    Examples:
        >>> now_py = get_current_paraguay_datetime()
        >>> print(now_py.tzinfo.zone)  # 'America/Asuncion'
    """
    return datetime.now(PARAGUAY_TIMEZONE)


def get_current_paraguay_date() -> date:
    """
    Obtiene la fecha actual de Paraguay.

    Returns:
        date: Fecha actual en Paraguay

    Examples:
        >>> today = get_current_paraguay_date()
        >>> print(today)  # 2025-07-01
    """
    return get_current_paraguay_datetime().date()


def convert_to_paraguay_time(dt: Union[datetime, str]) -> datetime:
    """
    Convierte una fecha/hora a zona horaria Paraguay.

    Args:
        dt: Fecha/hora a convertir (datetime o string)

    Returns:
        datetime: Fecha/hora en zona horaria Paraguay

    Raises:
        ValueError: Si no se puede parsear la fecha

    Examples:
        >>> utc_time = datetime.now(timezone.utc)
        >>> py_time = convert_to_paraguay_time(utc_time)
        >>> print(py_time.tzinfo.zone)  # 'America/Asuncion'
    """
    if isinstance(dt, str):
        parsed_dt = parse_flexible_datetime(dt)
        if parsed_dt is None:
            raise ValueError(f"No se pudo parsear la fecha: {dt}")
        dt = parsed_dt

    if dt.tzinfo is None:
        # Si no tiene zona horaria, asumir UTC
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(PARAGUAY_TIMEZONE)


def convert_from_paraguay_time(dt: datetime, target_tz: Union[timezone, pytz.BaseTzInfo]) -> datetime:
    """
    Convierte desde zona horaria Paraguay a otra zona.

    Args:
        dt: Fecha/hora en Paraguay
        target_tz: Zona horaria destino

    Returns:
        datetime: Fecha/hora en zona horaria destino

    Examples:
        >>> py_time = get_current_paraguay_datetime()
        >>> utc_time = convert_from_paraguay_time(py_time, timezone.utc)
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARAGUAY_TIMEZONE)
    elif dt.tzinfo != PARAGUAY_TIMEZONE:
        dt = dt.astimezone(PARAGUAY_TIMEZONE)

    return dt.astimezone(target_tz)


# ===================================================================
# FUNCIONES DE FORMATEO SIFEN
# ===================================================================

def format_sifen_date(dt: Union[datetime, date, str]) -> str:
    """
    Formatea una fecha para SIFEN (YYYY-MM-DD).

    Args:
        dt: Fecha a formatear

    Returns:
        str: Fecha en formato SIFEN

    Raises:
        ValueError: Si no se puede formatear la fecha

    Examples:
        >>> formatted = format_sifen_date(datetime.now())
        >>> print(formatted)  # "2025-07-01"
    """
    if isinstance(dt, str):
        parsed_dt = parse_flexible_datetime(dt)
        if parsed_dt is None:
            raise ValueError(f"No se pudo parsear la fecha: {dt}")
        dt = parsed_dt

    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d')
    elif isinstance(dt, date):
        return dt.strftime('%Y-%m-%d')
    else:
        raise ValueError(f"Tipo de fecha no soportado: {type(dt)}")


def format_sifen_datetime(dt: Union[datetime, str]) -> str:
    """
    Formatea una fecha/hora para SIFEN (YYYY-MM-DDTHH:MM:SS).

    Args:
        dt: Fecha/hora a formatear

    Returns:
        str: Fecha/hora en formato SIFEN

    Raises:
        ValueError: Si no se puede formatear la fecha

    Examples:
        >>> formatted = format_sifen_datetime(datetime.now())
        >>> print(formatted)  # "2025-07-01T14:30:00"
    """
    if isinstance(dt, str):
        parsed_dt = parse_flexible_datetime(dt)
        if parsed_dt is None:
            raise ValueError(f"No se pudo parsear la fecha: {dt}")
        dt = parsed_dt

    if not isinstance(dt, datetime):
        raise ValueError(f"Se requiere datetime, recibido: {type(dt)}")

    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def format_cdc_date(dt: Union[datetime, date, str]) -> str:
    """
    Formatea una fecha para CDC (YYYYMMDD).

    Args:
        dt: Fecha a formatear

    Returns:
        str: Fecha en formato CDC

    Examples:
        >>> formatted = format_cdc_date(datetime.now())
        >>> print(formatted)  # "20250701"
    """
    if isinstance(dt, str):
        parsed_dt = parse_flexible_datetime(dt)
        if parsed_dt is None:
            raise ValueError(f"No se pudo parsear la fecha: {dt}")
        dt = parsed_dt

    if isinstance(dt, datetime):
        return dt.strftime('%Y%m%d')
    elif isinstance(dt, date):
        return dt.strftime('%Y%m%d')
    else:
        raise ValueError(f"Tipo de fecha no soportado: {type(dt)}")


# ===================================================================
# FUNCIONES DE PARSING
# ===================================================================

def parse_sifen_date(date_str: str) -> Optional[date]:
    """
    Parsea una fecha en formato SIFEN (YYYY-MM-DD).

    Args:
        date_str: String de fecha a parsear

    Returns:
        date: Fecha parseada o None si es inválida

    Examples:
        >>> parsed = parse_sifen_date("2025-07-01")
        >>> print(parsed)  # 2025-07-01
    """
    if not PATTERN_DATE_SIFEN.match(date_str):
        return None

    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def parse_sifen_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Parsea una fecha/hora en formato SIFEN (YYYY-MM-DDTHH:MM:SS).

    Args:
        datetime_str: String de fecha/hora a parsear

    Returns:
        datetime: Fecha/hora parseada o None si es inválida

    Examples:
        >>> parsed = parse_sifen_datetime("2025-07-01T14:30:00")
        >>> print(parsed)  # 2025-07-01 14:30:00
    """
    if not PATTERN_DATETIME_SIFEN.match(datetime_str):
        return None

    try:
        return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return None


def parse_cdc_date(date_str: str) -> Optional[date]:
    """
    Parsea una fecha en formato CDC (YYYYMMDD).

    Args:
        date_str: String de fecha a parsear

    Returns:
        date: Fecha parseada o None si es inválida

    Examples:
        >>> parsed = parse_cdc_date("20250701")
        >>> print(parsed)  # 2025-07-01
    """
    if not PATTERN_DATE_CDC.match(date_str):
        return None

    try:
        return datetime.strptime(date_str, '%Y%m%d').date()
    except ValueError:
        return None


def parse_flexible_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Intenta parsear una fecha/hora usando múltiples formatos.

    Args:
        datetime_str: String de fecha/hora a parsear

    Returns:
        datetime: Fecha/hora parseada o None si no se puede parsear

    Examples:
        >>> parsed = parse_flexible_datetime("01/07/2025 14:30")
        >>> print(parsed)  # 2025-07-01 14:30:00
    """
    datetime_str = datetime_str.strip()

    # Intentar formatos datetime primero
    for fmt in COMMON_DATETIME_FORMATS:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue

    # Intentar formatos de fecha (agregan 00:00:00)
    for fmt in COMMON_DATE_FORMATS:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue

    return None


# ===================================================================
# FUNCIONES DE VALIDACIÓN
# ===================================================================

def validate_fecha_emision(fecha: Union[datetime, str], tipo_fecha: TipoFecha = TipoFecha.EMISION) -> FechaValidationResult:
    """
    Valida una fecha según las reglas SIFEN.

    Args:
        fecha: Fecha a validar
        tipo_fecha: Tipo de fecha para aplicar reglas específicas

    Returns:
        FechaValidationResult: Resultado de la validación

    Examples:
        >>> result = validate_fecha_emision("2025-07-01T14:30:00")
        >>> print(result.is_valid)  # True o False
    """
    # Parsear fecha si es string
    if isinstance(fecha, str):
        fecha_parsed = parse_flexible_datetime(fecha)
        if fecha_parsed is None:
            return FechaValidationResult(
                is_valid=False,
                error_message=f"Formato de fecha inválido: {fecha}",
                error_code="INVALID_FORMAT",
                estado=EstadoValidacionFecha.FORMATO_INVALIDO,
                suggestions=[
                    "Use formato YYYY-MM-DD para fechas",
                    "Use formato YYYY-MM-DDTHH:MM:SS para fecha/hora",
                    "Verifique que la fecha sea válida"
                ]
            )
    else:
        fecha_parsed = fecha

    # Convertir a zona horaria Paraguay si no tiene zona horaria
    if fecha_parsed.tzinfo is None:
        fecha_parsed = fecha_parsed.replace(tzinfo=PARAGUAY_TIMEZONE)
    else:
        fecha_parsed = fecha_parsed.astimezone(PARAGUAY_TIMEZONE)

    # Obtener fecha/hora actual en Paraguay
    now_paraguay = get_current_paraguay_datetime()

    # Validar según tipo de fecha
    if tipo_fecha == TipoFecha.EMISION:
        # Fechas de emisión no pueden ser futuras (tolerancia 5 min)
        tolerancia = timedelta(
            minutes=SIFEN_TIME_LIMITS['FUTURE_TOLERANCE_MINUTES'])
        if fecha_parsed > now_paraguay + tolerancia:
            return FechaValidationResult(
                is_valid=False,
                fecha_parsed=fecha_parsed,
                error_message=f"Fecha de emisión no puede ser futura: {fecha_parsed}",
                error_code="FUTURE_DATE",
                estado=EstadoValidacionFecha.FUTURA,
                suggestions=[
                    "Verifique la fecha/hora del sistema",
                    "Use fecha actual o anterior para emisión"
                ]
            )

    elif tipo_fecha == TipoFecha.VENCIMIENTO:
        # Fechas de vencimiento pueden ser futuras pero no muy antiguas
        if fecha_parsed < now_paraguay - timedelta(days=365):
            return FechaValidationResult(
                is_valid=False,
                fecha_parsed=fecha_parsed,
                error_message=f"Fecha de vencimiento muy antigua: {fecha_parsed}",
                error_code="TOO_OLD",
                estado=EstadoValidacionFecha.MUY_ANTIGUA
            )

    # Validar rango general SIFEN
    fecha_date = fecha_parsed.date()
    if fecha_date < MIN_SIFEN_DATE or fecha_date > MAX_SIFEN_DATE:
        return FechaValidationResult(
            is_valid=False,
            fecha_parsed=fecha_parsed,
            error_message=f"Fecha fuera del rango SIFEN ({MIN_SIFEN_DATE} - {MAX_SIFEN_DATE}): {fecha_date}",
            error_code="OUT_OF_RANGE",
            estado=EstadoValidacionFecha.FUERA_DE_RANGO,
            suggestions=[
                f"Use fechas entre {MIN_SIFEN_DATE} y {MAX_SIFEN_DATE}",
                "Verifique que la fecha sea correcta"
            ]
        )

    # Si llegamos aquí, la fecha es válida
    return FechaValidationResult(
        is_valid=True,
        fecha_parsed=fecha_parsed,
        estado=EstadoValidacionFecha.VALIDA
    )


def is_valid_sifen_date_format(date_str: str) -> bool:
    """
    Verifica si un string tiene formato de fecha SIFEN válido.

    Args:
        date_str: String a validar

    Returns:
        bool: True si el formato es válido

    Examples:
        >>> is_valid_sifen_date_format("2025-07-01")  # True
        >>> is_valid_sifen_date_format("01/07/2025")  # False
    """
    return PATTERN_DATE_SIFEN.match(date_str) is not None


def is_valid_sifen_datetime_format(datetime_str: str) -> bool:
    """
    Verifica si un string tiene formato de fecha/hora SIFEN válido.

    Args:
        datetime_str: String a validar

    Returns:
        bool: True si el formato es válido

    Examples:
        >>> is_valid_sifen_datetime_format("2025-07-01T14:30:00")  # True
        >>> is_valid_sifen_datetime_format("2025-07-01 14:30:00")  # False
    """
    return PATTERN_DATETIME_SIFEN.match(datetime_str) is not None


# ===================================================================
# FUNCIONES DE CÁLCULO TEMPORAL
# ===================================================================

def calculate_document_delay(fecha_emision: datetime, fecha_envio: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Calcula el retraso en el envío de un documento.

    Args:
        fecha_emision: Fecha de emisión del documento
        fecha_envio: Fecha de envío (actual si es None)

    Returns:
        Dict: Información sobre el retraso y estado según límites SIFEN

    Examples:
        >>> info = calculate_document_delay(datetime.now() - timedelta(hours=25))
        >>> print(info['status'])  # 'NORMAL', 'EXTEMPORANEOUS', o 'REJECTED'
    """
    if fecha_envio is None:
        fecha_envio = get_current_paraguay_datetime()

    # Asegurar que ambas fechas estén en zona horaria Paraguay
    if fecha_emision.tzinfo is None:
        fecha_emision = fecha_emision.replace(tzinfo=PARAGUAY_TIMEZONE)
    else:
        fecha_emision = fecha_emision.astimezone(PARAGUAY_TIMEZONE)

    if fecha_envio.tzinfo is None:
        fecha_envio = fecha_envio.replace(tzinfo=PARAGUAY_TIMEZONE)
    else:
        fecha_envio = fecha_envio.astimezone(PARAGUAY_TIMEZONE)

    # Calcular diferencia
    diff = fecha_envio - fecha_emision
    delay_hours = diff.total_seconds() / 3600
    delay_days = delay_hours / 24

    # Determinar estado según límites SIFEN
    if delay_hours <= SIFEN_TIME_LIMITS['NORMAL_LIMIT_HOURS']:
        status = 'NORMAL'
        description = 'Documento dentro del plazo normal'
    elif delay_hours <= SIFEN_TIME_LIMITS['EXTEMPORANEOUS_LIMIT_HOURS']:
        status = 'EXTEMPORANEOUS'
        description = 'Documento extemporáneo (fuera de plazo normal)'
    else:
        status = 'REJECTED'
        description = 'Documento fuera de plazo (será rechazado)'

    return {
        'delay_hours': round(delay_hours, 2),
        'delay_days': round(delay_days, 2),
        'status': status,
        'description': description,
        'fecha_emision': fecha_emision,
        'fecha_envio': fecha_envio,
        'within_normal_limit': delay_hours <= SIFEN_TIME_LIMITS['NORMAL_LIMIT_HOURS'],
        'within_extemporaneous_limit': delay_hours <= SIFEN_TIME_LIMITS['EXTEMPORANEOUS_LIMIT_HOURS'],
    }


def get_document_deadline(fecha_emision: datetime, tipo_limite: str = 'normal') -> datetime:
    """
    Calcula la fecha límite para envío de un documento.

    Args:
        fecha_emision: Fecha de emisión del documento
        tipo_limite: 'normal' o 'extemporaneous'

    Returns:
        datetime: Fecha límite en zona horaria Paraguay

    Examples:
        >>> deadline = get_document_deadline(datetime.now(), 'normal')
        >>> print(deadline)  # 72 horas después de emisión
    """
    if fecha_emision.tzinfo is None:
        fecha_emision = fecha_emision.replace(tzinfo=PARAGUAY_TIMEZONE)
    else:
        fecha_emision = fecha_emision.astimezone(PARAGUAY_TIMEZONE)

    if tipo_limite == 'normal':
        hours_limit = SIFEN_TIME_LIMITS['NORMAL_LIMIT_HOURS']
    elif tipo_limite == 'extemporaneous':
        hours_limit = SIFEN_TIME_LIMITS['EXTEMPORANEOUS_LIMIT_HOURS']
    else:
        raise ValueError(f"Tipo de límite inválido: {tipo_limite}")

    return fecha_emision + timedelta(hours=hours_limit)


def is_within_normal_deadline(fecha_emision: datetime, fecha_envio: Optional[datetime] = None) -> bool:
    """
    Verifica si un documento está dentro del plazo normal.

    Args:
        fecha_emision: Fecha de emisión
        fecha_envio: Fecha de envío (actual si es None)

    Returns:
        bool: True si está dentro del plazo normal (72 horas)
    """
    info = calculate_document_delay(fecha_emision, fecha_envio)
    return info['within_normal_limit']


def is_within_extemporaneous_deadline(fecha_emision: datetime, fecha_envio: Optional[datetime] = None) -> bool:
    """
    Verifica si un documento está dentro del plazo extemporáneo.

    Args:
        fecha_emision: Fecha de emisión
        fecha_envio: Fecha de envío (actual si es None)

    Returns:
        bool: True si está dentro del plazo extemporáneo (720 horas)
    """
    info = calculate_document_delay(fecha_emision, fecha_envio)
    return info['within_extemporaneous_limit']


# ===================================================================
# FUNCIONES DE UTILIDAD
# ===================================================================

def get_business_days_between(start_date: date, end_date: date) -> int:
    """
    Calcula días hábiles entre dos fechas (excluyendo sábados y domingos).

    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin

    Returns:
        int: Número de días hábiles

    Examples:
        >>> days = get_business_days_between(date(2025, 7, 1), date(2025, 7, 10))
        >>> print(days)  # Días hábiles entre las fechas
    """
    if start_date > end_date:
        return 0

    business_days = 0
    current_date = start_date

    while current_date <= end_date:
        # 0 = Lunes, 6 = Domingo
        if current_date.weekday() < 5:  # Lunes a Viernes
            business_days += 1
        current_date += timedelta(days=1)

    return business_days


def format_relative_time(dt: datetime, base_dt: Optional[datetime] = None) -> str:
    """
    Formatea una fecha como tiempo relativo.

    Args:
        dt: Fecha a formatear
        base_dt: Fecha base (actual si es None)

    Returns:
        str: Tiempo relativo (ej: "hace 2 horas", "en 3 días")

    Examples:
        >>> relative = format_relative_time(datetime.now() - timedelta(hours=2))
        >>> print(relative)  # "hace 2 horas"
    """
    if base_dt is None:
        base_dt = get_current_paraguay_datetime()

    # Asegurar zona horaria Paraguay
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARAGUAY_TIMEZONE)
    else:
        dt = dt.astimezone(PARAGUAY_TIMEZONE)

    if base_dt.tzinfo is None:
        base_dt = base_dt.replace(tzinfo=PARAGUAY_TIMEZONE)
    else:
        base_dt = base_dt.astimezone(PARAGUAY_TIMEZONE)

    diff = base_dt - dt
    total_seconds = abs(diff.total_seconds())

    # Determinar si es pasado o futuro
    is_past = diff.total_seconds() > 0
    prefix = "hace" if is_past else "en"

    # Calcular unidades
    if total_seconds < 60:
        return f"{prefix} {int(total_seconds)} segundos"
    elif total_seconds < 3600:
        minutes = int(total_seconds / 60)
        return f"{prefix} {minutes} minuto{'s' if minutes != 1 else ''}"
    elif total_seconds < 86400:
        hours = int(total_seconds / 3600)
        return f"{prefix} {hours} hora{'s' if hours != 1 else ''}"
    else:
        days = int(total_seconds / 86400)
        return f"{prefix} {days} día{'s' if days != 1 else ''}"
