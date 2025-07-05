# ===============================================
# ARCHIVO: backend/app/repositories/factura/utils.py
# PROPÓSITO: Utilidades específicas para FacturaRepository
# VERSIÓN: 1.0.0 - Compatible con SIFEN v150
# FASE: 1 - Fundación (40% del módulo)
# ===============================================

"""
Utilidades específicas para el módulo FacturaRepository.

Este módulo contiene funciones helper y constantes específicas de facturas
que son utilizadas por el FacturaRepository y sus mixins.

Incluye:
- Formateo de números SIFEN (EST-PEX-NUM)
- Validaciones específicas de Paraguay (timbrados, CDCs)
- Cálculos automáticos de IVA y totales
- Formateo para displays y UI
- Códigos y constantes SIFEN oficiales
- Validaciones de documentos paraguayos

Integra con:
- models/factura.py (validaciones SQLAlchemy)
- schemas/factura.py (validaciones Pydantic)
- services/xml_generator (datos para XML SIFEN)
- shared/constants/sifen_codes.py (códigos oficiales)

Ejemplos de uso:
    ```python
    from app.repositories.factura.utils import (
        format_numero_factura,
        calculate_factura_totals,
        validate_timbrado_vigency
    )
    
    # Formatear número completo
    numero = format_numero_factura("001", "001", 123)
    # Resultado: "001-001-0000123"
    
    # Calcular totales con IVA
    totales = calculate_factura_totals(items_data)
    # Resultado: {"total_general": 3135000, "total_iva": 285000, ...}
    
    # Validar timbrado vigente
    es_vigente = validate_timbrado_vigency("12345678", "2025-01-01", "2025-12-31")
    ```
"""

import re
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

# Configurar logger específico para facturas
logger = logging.getLogger("factura_repository")


# ===============================================
# CONSTANTES SIFEN OFICIALES
# ===============================================

class SifenConstants:
    """Constantes oficiales SIFEN Paraguay v150"""

    # === CÓDIGOS DE RESPUESTA SIFEN ===
    APROBADO = "0260"                    # Documento aprobado
    APROBADO_CON_OBSERVACIONES = "1005"  # Aprobado con observaciones
    RECHAZADO_ERROR_FORMATO = "0234"     # Error en formato XML
    RECHAZADO_ERROR_FIRMA = "0235"       # Error en firma digital
    RECHAZADO_DUPLICADO = "0236"         # Documento duplicado
    RECHAZADO_TIMBRADO = "0237"          # Timbrado inválido/vencido

    # === TIPOS DE DOCUMENTO ===
    TIPO_FACTURA = "1"
    TIPO_AUTOFACTURA = "4"
    TIPO_NOTA_CREDITO = "5"
    TIPO_NOTA_DEBITO = "6"
    TIPO_NOTA_REMISION = "7"

    # === TIPOS DE EMISIÓN ===
    EMISION_NORMAL = "1"
    EMISION_CONTINGENCIA = "2"

    # === TIPOS DE OPERACIÓN ===
    OPERACION_VENTA = "1"
    OPERACION_PRESTACION_SERVICIOS = "2"
    OPERACION_MIXTA = "3"
    OPERACION_CONSIGNACION = "4"

    # === CONDICIONES DE OPERACIÓN ===
    CONDICION_CONTADO = "1"
    CONDICION_CREDITO = "2"

    # === AFECTACIONES IVA ===
    IVA_EXENTO = "1"                     # 0%
    IVA_GRAVADO_5 = "2"                  # 5%
    IVA_GRAVADO_10 = "3"                 # 10%

    # === TASAS IVA PARAGUAY ===
    TASA_IVA_EXENTO = Decimal("0")
    TASA_IVA_5 = Decimal("5")
    TASA_IVA_10 = Decimal("10")

    # === LÍMITES OFICIALES ===
    CDC_LENGTH = 44                      # Longitud CDC
    ESTABLECIMIENTO_MIN = 1              # Código mínimo establecimiento
    ESTABLECIMIENTO_MAX = 999            # Código máximo establecimiento
    NUMERO_DOCUMENTO_MIN = 1             # Número mínimo documento
    NUMERO_DOCUMENTO_MAX = 9999999       # Número máximo documento
    TIMBRADO_MAX_LENGTH = 8              # Longitud máxima timbrado

    # === MONEDAS SOPORTADAS ===
    MONEDA_GUARANIES = "PYG"
    MONEDA_DOLARES = "USD"
    MONEDA_EUROS = "EUR"
    MONEDA_REALES = "BRL"
    MONEDA_PESOS_ARG = "ARS"


# === MAPEOS DE CÓDIGOS PARA DISPLAY ===
ESTADO_DESCRIPTIONS = {
    "borrador": "En construcción",
    "generado": "XML generado",
    "firmado": "Firmado digitalmente",
    "enviado": "Enviado a SIFEN",
    "aprobado": "Aprobado por SIFEN",
    "rechazado": "Rechazado por SIFEN",
    "cancelado": "Cancelado por usuario"
}

TIPO_DOCUMENTO_DESCRIPTIONS = {
    "1": "Factura Electrónica",
    "4": "Autofactura Electrónica",
    "5": "Nota de Crédito Electrónica",
    "6": "Nota de Débito Electrónica",
    "7": "Nota de Remisión Electrónica"
}

AFECTACION_IVA_DESCRIPTIONS = {
    "1": "Exento (0%)",
    "2": "Gravado IVA 5%",
    "3": "Gravado IVA 10%"
}


# ===============================================
# FUNCIONES DE FORMATEO SIFEN
# ===============================================

def format_numero_factura(establecimiento: str, punto_expedicion: str, numero: Union[int, str]) -> str:
    """
    Formatear número completo de factura según estándar SIFEN.

    Genera formato: EST-PEX-NUMERO (ej: 001-001-0000123)

    Args:
        establecimiento: Código establecimiento (1-999)
        punto_expedicion: Código punto expedición (1-999)
        numero: Número documento (1-9999999)

    Returns:
        str: Número completo formateado (EST-PEX-NUMERO)

    Raises:
        ValueError: Si algún parámetro está fuera de rango

    Examples:
        >>> format_numero_factura("1", "1", 123)
        "001-001-0000123"
        >>> format_numero_factura("15", "3", "456")
        "015-003-0000456"
    """
    try:
        # Convertir y validar establecimiento
        est_num = int(establecimiento)
        if not (SifenConstants.ESTABLECIMIENTO_MIN <= est_num <= SifenConstants.ESTABLECIMIENTO_MAX):
            raise ValueError(
                f"Establecimiento debe estar entre {SifenConstants.ESTABLECIMIENTO_MIN} y {SifenConstants.ESTABLECIMIENTO_MAX}")

        # Convertir y validar punto expedición
        pex_num = int(punto_expedicion)
        if not (SifenConstants.ESTABLECIMIENTO_MIN <= pex_num <= SifenConstants.ESTABLECIMIENTO_MAX):
            raise ValueError(
                f"Punto expedición debe estar entre {SifenConstants.ESTABLECIMIENTO_MIN} y {SifenConstants.ESTABLECIMIENTO_MAX}")

        # Convertir y validar número documento
        num_doc = int(numero)
        if not (SifenConstants.NUMERO_DOCUMENTO_MIN <= num_doc <= SifenConstants.NUMERO_DOCUMENTO_MAX):
            raise ValueError(
                f"Número documento debe estar entre {SifenConstants.NUMERO_DOCUMENTO_MIN} y {SifenConstants.NUMERO_DOCUMENTO_MAX}")

        # Formatear con ceros a la izquierda
        est_formatted = str(est_num).zfill(3)
        pex_formatted = str(pex_num).zfill(3)
        num_formatted = str(num_doc).zfill(7)

        numero_completo = f"{est_formatted}-{pex_formatted}-{num_formatted}"

        logger.debug(f"Número factura formateado: {numero_completo}")
        return numero_completo

    except ValueError as e:
        logger.error(f"Error formateando número factura: {e}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado formateando número: {e}")
        raise ValueError(f"Error formateando número factura: {str(e)}")


def parse_numero_factura(numero_completo: str) -> Dict[str, str]:
    """
    Parsear número completo de factura en sus componentes.

    Args:
        numero_completo: Número en formato EST-PEX-NUMERO

    Returns:
        dict: Diccionario con establecimiento, punto_expedicion, numero

    Raises:
        ValueError: Si el formato no es válido

    Examples:
        >>> parse_numero_factura("001-001-0000123")
        {"establecimiento": "001", "punto_expedicion": "001", "numero": "0000123"}
    """
    if not numero_completo:
        raise ValueError("Número completo es requerido")

    # Patrón para EST-PEX-NUMERO
    pattern = r'^(\d{3})-(\d{3})-(\d{7})$'
    match = re.match(pattern, numero_completo.strip())

    if not match:
        raise ValueError(
            f"Formato inválido. Esperado: EST-PEX-NUMERO (ej: 001-001-0000123), recibido: {numero_completo}")

    establecimiento, punto_expedicion, numero = match.groups()

    result = {
        "establecimiento": establecimiento,
        "punto_expedicion": punto_expedicion,
        "numero": numero
    }

    logger.debug(f"Número parseado: {result}")
    return result


def get_next_numero_available(ultimo_numero: str) -> str:
    """
    Obtener próximo número disponible en secuencia.

    Args:
        ultimo_numero: Último número usado (formato NNNNNNN)

    Returns:
        str: Próximo número disponible

    Examples:
        >>> get_next_numero_available("0000123")
        "0000124"
        >>> get_next_numero_available("0009999")
        "0010000"
    """
    try:
        if not ultimo_numero:
            return "0000001"

        # Extraer número y convertir
        numero_actual = int(ultimo_numero)

        # Verificar que no exceda límite
        if numero_actual >= SifenConstants.NUMERO_DOCUMENTO_MAX:
            raise ValueError(
                f"Secuencia agotada. Máximo: {SifenConstants.NUMERO_DOCUMENTO_MAX}")

        # Próximo número
        proximo_numero = numero_actual + 1
        numero_formatted = str(proximo_numero).zfill(7)

        logger.debug(f"Próximo número disponible: {numero_formatted}")
        return numero_formatted

    except ValueError as e:
        logger.error(f"Error obteniendo próximo número: {e}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado obteniendo próximo número: {e}")
        raise ValueError(f"Error obteniendo próximo número: {str(e)}")


# ===============================================
# VALIDACIONES ESPECÍFICAS SIFEN
# ===============================================

def validate_factura_format(numero_completo: str) -> bool:
    """
    Validar formato de número de factura.

    Args:
        numero_completo: Número a validar

    Returns:
        bool: True si es válido
    """
    try:
        parse_numero_factura(numero_completo)
        return True
    except ValueError:
        return False


def validate_timbrado_vigency(numero_timbrado: str, fecha_inicio: Union[str, date], fecha_fin: Union[str, date]) -> bool:
    """
    Validar vigencia de timbrado SIFEN.

    Args:
        numero_timbrado: Número del timbrado
        fecha_inicio: Fecha inicio vigencia
        fecha_fin: Fecha fin vigencia

    Returns:
        bool: True si está vigente

    Examples:
        >>> validate_timbrado_vigency("12345678", "2025-01-01", "2025-12-31")
        True  # Si estamos en 2025
    """
    try:
        # Validar timbrado
        if not numero_timbrado or not numero_timbrado.strip():
            logger.warning("Número timbrado vacío")
            return False

        # Limpiar y validar formato
        timbrado_clean = numero_timbrado.strip()
        if not re.match(r'^\d{1,8}$', timbrado_clean):
            logger.warning(f"Formato timbrado inválido: {timbrado_clean}")
            return False

        # Convertir fechas si son strings
        if isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        if isinstance(fecha_fin, str):
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

        # Validar vigencia
        hoy = date.today()
        vigente = fecha_inicio <= hoy <= fecha_fin

        if not vigente:
            logger.warning(
                f"Timbrado {timbrado_clean} no vigente. Vigencia: {fecha_inicio} - {fecha_fin}, Hoy: {hoy}")

        return vigente

    except Exception as e:
        logger.error(f"Error validando timbrado: {e}")
        return False


def validate_cdc_format(cdc: str) -> bool:
    """
    Validar formato CDC de 44 dígitos.

    Args:
        cdc: Código de Control del Documento

    Returns:
        bool: True si es válido

    Examples:
        >>> validate_cdc_format("01234567890123456789012345678901234567890123")
        True
        >>> validate_cdc_format("123")
        False
    """
    if not cdc:
        return False

    # Limpiar espacios
    cdc_clean = cdc.strip()

    # Validar longitud y formato
    if len(cdc_clean) != SifenConstants.CDC_LENGTH:
        logger.warning(
            f"CDC longitud incorrecta. Esperado: {SifenConstants.CDC_LENGTH}, recibido: {len(cdc_clean)}")
        return False

    if not cdc_clean.isdigit():
        logger.warning("CDC debe contener solo dígitos")
        return False

    return True


def validate_fecha_emision(fecha_emision: Union[str, date]) -> bool:
    """
    Validar fecha de emisión según normativa SIFEN.

    No puede ser:
    - Fecha futura
    - Más de 45 días en el pasado

    Args:
        fecha_emision: Fecha a validar

    Returns:
        bool: True si es válida
    """
    try:
        # Convertir si es string
        if isinstance(fecha_emision, str):
            fecha_emision = datetime.strptime(fecha_emision, "%Y-%m-%d").date()

        hoy = date.today()

        # No puede ser futura
        if fecha_emision > hoy:
            logger.warning(f"Fecha emisión futura: {fecha_emision}")
            return False

        # No puede ser muy antigua (45 días según SIFEN)
        dias_atras = (hoy - fecha_emision).days
        if dias_atras > 45:
            logger.warning(
                f"Fecha emisión muy antigua: {fecha_emision} ({dias_atras} días)")
            return False

        return True

    except Exception as e:
        logger.error(f"Error validando fecha emisión: {e}")
        return False


# ===============================================
# CÁLCULOS AUTOMÁTICOS DE TOTALES
# ===============================================

def calculate_factura_totals(items_data: List[Dict[str, Any]]) -> Dict[str, Decimal]:
    """
    Calcular totales automáticos de factura con IVA paraguayo.

    Calcula:
    - Subtotales por tasa IVA (0%, 5%, 10%)
    - Montos IVA por tasa
    - Total operación (sin IVA)
    - Total general (con IVA)

    Args:
        items_data: Lista de items con estructura:
            {
                "cantidad": Decimal,
                "precio_unitario": Decimal,
                "descuento_unitario": Decimal (opcional),
                "descuento_porcentual": Decimal (opcional),
                "tasa_iva": Decimal,  # 0, 5, o 10
                "afectacion_iva": str  # "1", "2", o "3"
            }

    Returns:
        dict: Totales calculados
        {
            "subtotal_exento": Decimal,      # Subtotal 0%
            "subtotal_iva5": Decimal,        # Subtotal 5%
            "subtotal_iva10": Decimal,       # Subtotal 10%
            "monto_iva5": Decimal,           # IVA 5%
            "monto_iva10": Decimal,          # IVA 10%
            "total_operacion": Decimal,      # Total sin IVA
            "total_iva": Decimal,            # Total IVA
            "total_general": Decimal,        # Total con IVA
            "items_procesados": int,         # Cantidad items
            "total_descuentos": Decimal      # Total descuentos aplicados
        }

    Examples:
        >>> items = [
        ...     {
        ...         "cantidad": Decimal("2"),
        ...         "precio_unitario": Decimal("1500000"),
        ...         "tasa_iva": Decimal("10"),
        ...         "afectacion_iva": "3"
        ...     }
        ... ]
        >>> totales = calculate_factura_totals(items)
        >>> totales["total_general"]
        Decimal("3300000")  # 3.000.000 + 300.000 IVA
    """
    # Inicializar totales
    subtotal_exento = Decimal("0")
    subtotal_iva5 = Decimal("0")
    subtotal_iva10 = Decimal("0")
    total_descuentos = Decimal("0")

    logger.debug(f"Calculando totales para {len(items_data)} items")

    try:
        for i, item in enumerate(items_data):
            # Extraer datos del item
            cantidad = _to_decimal(item.get("cantidad", 0))
            precio_unitario = _to_decimal(item.get("precio_unitario", 0))
            descuento_unitario = _to_decimal(item.get("descuento_unitario", 0))
            descuento_porcentual = _to_decimal(
                item.get("descuento_porcentual", 0))
            tasa_iva = _to_decimal(item.get("tasa_iva", 0))
            afectacion_iva = item.get("afectacion_iva", "1")

            # Validar datos básicos
            if cantidad <= 0:
                logger.warning(f"Item {i}: cantidad inválida: {cantidad}")
                continue

            if precio_unitario < 0:
                logger.warning(
                    f"Item {i}: precio unitario negativo: {precio_unitario}")
                continue

            # Calcular subtotal del item
            subtotal_item = cantidad * precio_unitario

            # Aplicar descuentos
            descuento_total_item = Decimal("0")

            if descuento_unitario > 0:
                descuento_total_item = cantidad * descuento_unitario
            elif descuento_porcentual > 0:
                descuento_total_item = (subtotal_item * descuento_porcentual / 100).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )

            # Subtotal después de descuentos
            subtotal_item_final = subtotal_item - descuento_total_item
            total_descuentos += descuento_total_item

            # Validar que no sea negativo
            if subtotal_item_final < 0:
                logger.warning(
                    f"Item {i}: subtotal negativo después de descuentos")
                subtotal_item_final = Decimal("0")

            # Clasificar por afectación IVA
            if afectacion_iva == SifenConstants.IVA_EXENTO:  # Exento 0%
                subtotal_exento += subtotal_item_final
            elif afectacion_iva == SifenConstants.IVA_GRAVADO_5:  # 5%
                subtotal_iva5 += subtotal_item_final
            elif afectacion_iva == SifenConstants.IVA_GRAVADO_10:  # 10%
                subtotal_iva10 += subtotal_item_final
            else:
                logger.warning(
                    f"Item {i}: afectación IVA inválida: {afectacion_iva}, asumiendo exento")
                subtotal_exento += subtotal_item_final

            logger.debug(f"Item {i}: cantidad={cantidad}, precio={precio_unitario}, "
                         f"subtotal={subtotal_item_final}, afectacion={afectacion_iva}")

        # Calcular montos IVA (en Guaraníes, sin centavos)
        monto_iva5 = (subtotal_iva5 * SifenConstants.TASA_IVA_5 / 100).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        monto_iva10 = (subtotal_iva10 * SifenConstants.TASA_IVA_10 / 100).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

        # Totales finales
        total_operacion = subtotal_exento + subtotal_iva5 + subtotal_iva10
        total_iva = monto_iva5 + monto_iva10
        total_general = total_operacion + total_iva

        resultado = {
            "subtotal_exento": subtotal_exento,
            "subtotal_iva5": subtotal_iva5,
            "subtotal_iva10": subtotal_iva10,
            "monto_iva5": monto_iva5,
            "monto_iva10": monto_iva10,
            "total_operacion": total_operacion,
            "total_iva": total_iva,
            "total_general": total_general,
            "items_procesados": len(items_data),
            "total_descuentos": total_descuentos
        }

        logger.info(f"Totales calculados: Total general={total_general}, "
                    f"IVA={total_iva}, Items={len(items_data)}")

        return resultado

    except Exception as e:
        logger.error(f"Error calculando totales: {e}")
        raise ValueError(f"Error en cálculo de totales: {str(e)}")


def _to_decimal(value: Any) -> Decimal:
    """Convertir valor a Decimal de forma segura."""
    if value is None:
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except:
        return Decimal("0")


# ===============================================
# FUNCIONES DE FORMATEO PARA DISPLAY
# ===============================================

def format_factura_for_display(factura_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Formatear datos de factura para mostrar en UI.

    Args:
        factura_data: Datos de la factura

    Returns:
        dict: Datos formateados para display
    """
    try:
        # Datos básicos
        numero_completo = factura_data.get("numero_completo", "")
        estado = factura_data.get("estado", "")
        fecha_emision = factura_data.get("fecha_emision")

        # Totales
        total_general = _to_decimal(factura_data.get("total_general", 0))
        total_iva = _to_decimal(factura_data.get("total_iva", 0))
        moneda = factura_data.get("moneda", "PYG")

        # Formatear
        display_data = {
            "numero_completo": numero_completo,
            "estado_descripcion": ESTADO_DESCRIPTIONS.get(estado, estado),
            "fecha_emision_formatted": _format_date_display(fecha_emision) if fecha_emision else "",
            "total_general_formatted": format_amount_display(total_general, moneda),
            "total_iva_formatted": format_amount_display(total_iva, moneda),
            "moneda_simbolo": _get_currency_symbol(moneda),
            "estado_color": _get_estado_color(estado),
            "cdc_masked": _mask_cdc(factura_data.get("cdc", "")),
            "tipo_documento_descripcion": TIPO_DOCUMENTO_DESCRIPTIONS.get(
                factura_data.get("tipo_documento",
                                 "1"), "Documento Electrónico"
            )
        }

        return display_data

    except Exception as e:
        logger.error(f"Error formateando factura para display: {e}")
        return {"error": "Error formateando datos"}


def format_amount_display(amount: Union[Decimal, int, str], currency: str = "PYG") -> str:
    """
    Formatear monto para mostrar con separadores de miles.

    Args:
        amount: Monto a formatear
        currency: Código de moneda

    Returns:
        str: Monto formateado

    Examples:
        >>> format_amount_display(1500000, "PYG")
        "₲ 1.500.000"
        >>> format_amount_display(1500.50, "USD")
        "$ 1.500,50"
    """
    try:
        # Convertir a Decimal
        decimal_amount = _to_decimal(amount)

        # Símbolo de moneda
        symbol = _get_currency_symbol(currency)

        # Formatear según moneda
        if currency == "PYG":
            # Guaraníes: sin decimales, punto como separador de miles
            formatted = f"{int(decimal_amount):,}".replace(",", ".")
        else:
            # Otras monedas: con 2 decimales
            formatted = f"{float(decimal_amount):,.2f}".replace(
                ",", "X").replace(".", ",").replace("X", ".")

        return f"{symbol} {formatted}"

    except Exception as e:
        logger.error(f"Error formateando monto: {e}")
        return f"{amount}"


def _format_date_display(fecha: Union[str, date, datetime]) -> str:
    """Formatear fecha para display."""
    try:
        if not fecha:
            return ""

        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha.split("T")[0], "%Y-%m-%d").date()
        elif isinstance(fecha, datetime):
            fecha = fecha.date()

        # Formato paraguayo: DD/MM/YYYY
        return fecha.strftime("%d/%m/%Y")

    except:
        return str(fecha) if fecha else ""


def _get_currency_symbol(currency: str) -> str:
    """Obtener símbolo de moneda."""
    symbols = {
        "PYG": "₲",
        "USD": "$",
        "EUR": "€",
        "BRL": "R$",
        "ARS": "$"
    }
    return symbols.get(currency, currency)


def _get_estado_color(estado: str) -> str:
    """Obtener color para estado en UI."""
    colors = {
        "borrador": "gray",
        "generado": "blue",
        "firmado": "orange",
        "enviado": "yellow",
        "aprobado": "green",
        "rechazado": "red",
        "cancelado": "gray"
    }
    return colors.get(estado, "gray")


def _mask_cdc(cdc: str) -> str:
    """Enmascarar CDC para mostrar solo inicio y fin."""
    if not cdc or len(cdc) != SifenConstants.CDC_LENGTH:
        return cdc

    # Mostrar primeros 6 y últimos 6 dígitos
    return f"{cdc[:6]}{'*' * 32}{cdc[-6:]}"

# ===============================================
# VALIDACIONES DE DOCUMENTOS PARAGUAYOS
# ===============================================


def validate_ruc_paraguayo(ruc: str) -> bool:
    """
    Validar RUC paraguayo con dígito verificador.

    Formato: NNNNNNNN-D (8 dígitos + guión + dígito verificador)

    Args:
        ruc: RUC a validar

    Returns:
        bool: True si es válido

    Examples:
        >>> validate_ruc_paraguayo("80087654-3")
        True
        >>> validate_ruc_paraguayo("12345678-9")
        False  # DV incorrecto
    """
    try:
        if not ruc:
            return False

        # Limpiar espacios
        ruc_clean = ruc.strip()

        # Validar formato básico
        if not re.match(r'^\d{8}-\d$', ruc_clean):
            logger.warning(f"RUC formato inválido: {ruc_clean}")
            return False

        # Separar número y DV
        numero_ruc, dv_str = ruc_clean.split('-')
        dv_recibido = int(dv_str)

        # Calcular DV
        dv_calculado = _calcular_dv_ruc_paraguayo(numero_ruc)

        # Validar
        if dv_calculado != dv_recibido:
            logger.warning(
                f"RUC DV incorrecto. Calculado: {dv_calculado}, Recibido: {dv_recibido}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error validando RUC: {e}")
        return False


def _calcular_dv_ruc_paraguayo(numero_ruc: str) -> int:
    """
    Calcular dígito verificador de RUC paraguayo.

    Algoritmo oficial del SET Paraguay.
    """
    # Multiplicadores del 2 al 9
    multiplicadores = [2, 3, 4, 5, 6, 7, 8, 9]
    suma = 0

    # Multiplicar cada dígito por su multiplicador correspondiente
    for i, digito in enumerate(reversed(numero_ruc)):
        multiplicador = multiplicadores[i % len(multiplicadores)]
        suma += int(digito) * multiplicador

    # Calcular resto
    resto = suma % 11

    # DV según resto
    if resto < 2:
        return 0
    else:
        return 11 - resto


def validate_ci_paraguaya(ci: str) -> bool:
    """
    Validar Cédula de Identidad paraguaya.

    Formato: NNNNNNN (1-9999999) o NNNNNNNN (con ceros)

    Args:
        ci: CI a validar

    Returns:
        bool: True si es válida
    """
    try:
        if not ci:
            return False

        # Limpiar espacios y puntos
        ci_clean = ci.strip().replace(".", "")

        # Validar que sean solo números
        if not ci_clean.isdigit():
            return False

        # Validar longitud (máximo 8 dígitos)
        if len(ci_clean) > 8:
            return False

        # Convertir a número
        ci_num = int(ci_clean)

        # Validar rango (1 a 99999999)
        if not (1 <= ci_num <= 99999999):
            return False

        return True

    except Exception as e:
        logger.error(f"Error validando CI: {e}")
        return False


def format_ruc_display(ruc: str) -> str:
    """
    Formatear RUC para display.

    Args:
        ruc: RUC sin formato

    Returns:
        str: RUC formateado

    Examples:
        >>> format_ruc_display("800876543")
        "80087654-3"
    """
    try:
        if not ruc:
            return ""

        # Limpiar
        ruc_clean = ruc.strip().replace("-", "")

        # Si ya tiene 9 dígitos (8 + DV)
        if len(ruc_clean) == 9 and ruc_clean.isdigit():
            return f"{ruc_clean[:8]}-{ruc_clean[8]}"

        # Si tiene 8 dígitos, calcular DV
        if len(ruc_clean) == 8 and ruc_clean.isdigit():
            dv = _calcular_dv_ruc_paraguayo(ruc_clean)
            return f"{ruc_clean}-{dv}"

        # Retornar sin cambios si no se puede formatear
        return ruc

    except Exception as e:
        logger.error(f"Error formateando RUC: {e}")
        return ruc


def format_ci_display(ci: str) -> str:
    """
    Formatear CI para display con puntos separadores.

    Args:
        ci: CI sin formato

    Returns:
        str: CI formateada

    Examples:
        >>> format_ci_display("1234567")
        "1.234.567"
    """
    try:
        if not ci:
            return ""

        # Limpiar
        ci_clean = ci.strip().replace(".", "")

        if not ci_clean.isdigit():
            return ci

        # Formatear con puntos
        ci_num = int(ci_clean)
        return f"{ci_num:,}".replace(",", ".")

    except Exception as e:
        logger.error(f"Error formateando CI: {e}")
        return ci

# ===============================================
# UTILIDADES DE LOGGING Y OPERACIONES
# ===============================================


def log_repository_operation(operation: str, entity_id: Optional[int] = None,
                             details: Optional[Dict[str, Any]] = None,
                             level: str = "info") -> None:
    """
    Registrar operación de repository con formato estándar.

    Args:
        operation: Nombre de la operación
        entity_id: ID de la entidad (opcional)
        details: Detalles adicionales (opcional)
        level: Nivel de log (info, warning, error)
    """
    try:
        # Construir mensaje
        message_parts = [f"FacturaRepository.{operation}"]

        if entity_id:
            message_parts.append(f"(id={entity_id})")

        message = " ".join(message_parts)

        # Agregar detalles si existen
        if details:
            details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message += f" - {details_str}"

        # Log según nivel
        if level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        else:
            logger.info(message)

    except Exception as e:
        logger.error(f"Error logging operación: {e}")


def build_date_filter(fecha_desde: Optional[date] = None,
                      fecha_hasta: Optional[date] = None) -> Dict[str, Any]:
    """
    Construir filtro de fechas para queries.

    Args:
        fecha_desde: Fecha inicio (opcional)
        fecha_hasta: Fecha fin (opcional)

    Returns:
        dict: Filtro para SQLAlchemy
    """
    filtro = {}

    if fecha_desde:
        filtro["fecha_desde"] = fecha_desde

    if fecha_hasta:
        filtro["fecha_hasta"] = fecha_hasta

    return filtro


def calculate_percentage(parte: Union[Decimal, int], total: Union[Decimal, int]) -> Decimal:
    """
    Calcular porcentaje de forma segura.

    Args:
        parte: Parte del total
        total: Total

    Returns:
        Decimal: Porcentaje (0-100)
    """
    try:
        parte_decimal = _to_decimal(parte)
        total_decimal = _to_decimal(total)

        if total_decimal == 0:
            return Decimal("0")

        porcentaje = (parte_decimal / total_decimal * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return porcentaje

    except Exception as e:
        logger.error(f"Error calculando porcentaje: {e}")
        return Decimal("0")


def normalize_cdc(cdc: str) -> str:
    """
    Normalizar CDC removiendo espacios y caracteres especiales.

    Args:
        cdc: CDC a normalizar

    Returns:
        str: CDC normalizado
    """
    if not cdc:
        return ""

    # Remover espacios, guiones, puntos
    normalized = re.sub(r'[^0-9]', '', cdc.strip())

    return normalized


# ===============================================
# UTILIDADES ESPECÍFICAS PARA SIFEN
# ===============================================

def get_sifen_response_description(codigo: str) -> str:
    """
    Obtener descripción de código de respuesta SIFEN.

    Args:
        codigo: Código de respuesta

    Returns:
        str: Descripción del código
    """
    descriptions = {
        "0260": "Documento electrónico aprobado",
        "1005": "Documento electrónico aprobado con observaciones",
        "0234": "Error en el formato del documento",
        "0235": "Error en la firma digital",
        "0236": "Documento duplicado",
        "0237": "Timbrado inválido o vencido",
        "0238": "Error en la secuencia de numeración",
        "0239": "Establecimiento inválido",
        "0240": "Punto de expedición inválido",
        "0241": "Error en datos del emisor",
        "0242": "Error en datos del receptor",
        "0243": "Error en los totales del documento",
        "0244": "Error en los items del documento",
        "0245": "Error en los impuestos del documento"
    }

    return descriptions.get(codigo, f"Código desconocido: {codigo}")


def is_sifen_approved(codigo_respuesta: Optional[str]) -> bool:
    """
    Verificar si un código de respuesta SIFEN indica aprobación.

    Args:
        codigo_respuesta: Código de respuesta SIFEN

    Returns:
        bool: True si está aprobado
    """
    if not codigo_respuesta:
        return False

    # Códigos de aprobación
    codigos_aprobados = [
        SifenConstants.APROBADO,
        SifenConstants.APROBADO_CON_OBSERVACIONES
    ]

    return codigo_respuesta in codigos_aprobados


def generate_security_code() -> str:
    """
    Generar código de seguridad de 9 dígitos para CDC.

    Returns:
        str: Código de seguridad
    """
    import random
    return str(random.randint(100000000, 999999999))


def validate_establishment_range(establecimiento: str, punto_expedicion: str) -> bool:
    """
    Validar que establecimiento y punto expedición estén en rango válido.

    Args:
        establecimiento: Código establecimiento
        punto_expedicion: Código punto expedición

    Returns:
        bool: True si ambos están en rango válido
    """
    try:
        est_num = int(establecimiento)
        pex_num = int(punto_expedicion)

        est_valid = SifenConstants.ESTABLECIMIENTO_MIN <= est_num <= SifenConstants.ESTABLECIMIENTO_MAX
        pex_valid = SifenConstants.ESTABLECIMIENTO_MIN <= pex_num <= SifenConstants.ESTABLECIMIENTO_MAX

        return est_valid and pex_valid

    except ValueError:
        return False


# ===============================================
# UTILIDADES DE CONVERSIÓN PARA XML
# ===============================================

def prepare_factura_for_xml(factura_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preparar datos de factura para generación XML SIFEN.

    Convierte tipos y formatos para compatibilidad con XML generator.

    Args:
        factura_data: Datos de la factura

    Returns:
        dict: Datos preparados para XML
    """
    try:
        # Copiar datos
        xml_data = factura_data.copy()

        # Convertir fechas a string ISO
        if "fecha_emision" in xml_data and xml_data["fecha_emision"]:
            fecha = xml_data["fecha_emision"]
            if isinstance(fecha, (date, datetime)):
                xml_data["fecha_emision"] = fecha.strftime("%Y-%m-%d")

        # Convertir Decimales a string
        decimal_fields = [
            "total_general", "total_operacion", "total_iva",
            "subtotal_exento", "subtotal_iva5", "subtotal_iva10",
            "monto_iva5", "monto_iva10", "tipo_cambio"
        ]

        for field in decimal_fields:
            if field in xml_data and xml_data[field] is not None:
                xml_data[field] = str(xml_data[field])

        # Procesar items
        if "items" in xml_data:
            for item in xml_data["items"]:
                item_decimal_fields = [
                    "cantidad", "precio_unitario", "descuento_unitario",
                    "descuento_porcentual", "subtotal", "monto_iva", "total_item"
                ]

                for field in item_decimal_fields:
                    if field in item and item[field] is not None:
                        item[field] = str(item[field])

        logger.debug("Datos preparados para XML exitosamente")
        return xml_data

    except Exception as e:
        logger.error(f"Error preparando datos para XML: {e}")
        raise ValueError(f"Error preparando datos para XML: {str(e)}")


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # === CONSTANTES ===
    "SifenConstants",
    "ESTADO_DESCRIPTIONS",
    "TIPO_DOCUMENTO_DESCRIPTIONS",
    "AFECTACION_IVA_DESCRIPTIONS",

    # === FORMATEO SIFEN ===
    "format_numero_factura",
    "parse_numero_factura",
    "get_next_numero_available",

    # === VALIDACIONES SIFEN ===
    "validate_factura_format",
    "validate_timbrado_vigency",
    "validate_cdc_format",
    "validate_fecha_emision",

    # === CÁLCULOS ===
    "calculate_factura_totals",

    # === FORMATEO DISPLAY ===
    "format_factura_for_display",
    "format_amount_display",

    # === VALIDACIONES PARAGUAYAS ===
    "validate_ruc_paraguayo",
    "validate_ci_paraguaya",
    "format_ruc_display",
    "format_ci_display",

    # === UTILIDADES GENERALES ===
    "log_repository_operation",
    "build_date_filter",
    "calculate_percentage",
    "normalize_cdc",

    # === UTILIDADES SIFEN ===
    "get_sifen_response_description",
    "is_sifen_approved",
    "generate_security_code",
    "validate_establishment_range",
    "prepare_factura_for_xml"
]
