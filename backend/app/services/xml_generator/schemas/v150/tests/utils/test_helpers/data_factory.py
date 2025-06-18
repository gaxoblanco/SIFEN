"""
Módulo: Data Factory para Tests SIFEN

Propósito:
    Proporciona un sistema robusto para generación de datos de testing
    específicos para el sistema SIFEN v150. Incluye fábricas de datos
    realistas, generadores de casos edge y utilidades para crear
    escenarios de testing complejos.

    Este módulo se enfoca en generar datos que cumplan con las
    especificaciones de SIFEN Paraguay, manteniendo consistencia
    y realismo en los tests.

Funcionalidades principales:
    - Generación de datos empresariales paraguayos realistas
    - Creación de RUCs válidos con dígito verificador
    - Datos de productos y servicios comunes
    - Generación de escenarios de testing específicos
    - Builders para construcción incremental de entidades
    - Factorías especializadas por tipo de documento

Dependencias:
    - faker: Generación de datos ficticios
    - datetime: Manejo de fechas
    - decimal: Cálculos financieros precisos
    - random: Generación aleatoria controlada

Uso:
    from .data_factory import SifenDataFactory
    
    # Crear fábrica de datos
    factory = SifenDataFactory()
    
    # Generar empresa emisora válida
    emisor = factory.crear_empresa_emisora()
    
    # Generar factura completa
    factura = factory.crear_factura_completa()
    
    # Generar caso edge específico
    edge_case = factory.crear_caso_edge("ruc_extranjero")

Autor: Sistema SIFEN
Versión: 1.0.0
Fecha: 2025-06-17
"""

import random
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from faker import Faker
from faker.providers import BaseProvider


# ================================
# CONFIGURACIÓN DEL MÓDULO
# ================================

logger = logging.getLogger(__name__)
faker = Faker('es_PY')  # Locale Paraguay para datos realistas


# ================================
# CONSTANTES SIFEN
# ================================

class TipoDocumento(Enum):
    """Tipos de documentos SIFEN válidos"""
    FACTURA_ELECTRONICA = "01"
    AUTOFACTURA_ELECTRONICA = "04"
    NOTA_CREDITO_ELECTRONICA = "05"
    NOTA_DEBITO_ELECTRONICA = "06"
    NOTA_REMISION_ELECTRONICA = "07"


class TipoContribuyente(Enum):
    """Tipos de contribuyentes según SIFEN"""
    PERSONA_FISICA = "1"
    PERSONA_JURIDICA = "2"
    EXTRANJERO = "3"


class CondicionOperacion(Enum):
    """Condiciones de operación válidas"""
    CONTADO = "01"
    CREDITO = "02"


# Datos reales de Paraguay para testing realista
DEPARTAMENTOS_PARAGUAY = {
    "01": "Capital",
    "02": "San Pedro",
    "03": "Cordillera",
    "04": "Guairá",
    "05": "Caaguazú",
    "06": "Caazapá",
    "07": "Itapúa",
    "08": "Misiones",
    "09": "Paraguarí",
    "10": "Alto Paraná",
    "11": "Central",
    "12": "Ñeembucú",
    "13": "Amambay",
    "14": "Canindeyú",
    "15": "Presidente Hayes",
    "16": "Alto Paraguay",
    "17": "Boquerón"
}

CIUDADES_PRINCIPALES = {
    "01": ["001", "Asunción"],
    "11": ["004", "San Lorenzo"],
    "11": ["005", "Luque"],
    "11": ["006", "Capiatá"],
    "11": ["007", "Lambaré"],
    "10": ["001", "Ciudad del Este"],
    "07": ["001", "Encarnación"],
    "05": ["001", "Coronel Oviedo"]
}

MONEDAS_VALIDAS = {
    "PYG": {"codigo": "PYG", "descripcion": "Guaraní", "simbolo": "₲"},
    "USD": {"codigo": "USD", "descripcion": "Dólar americano", "simbolo": "$"},
    "BRL": {"codigo": "BRL", "descripcion": "Real brasileño", "simbolo": "R$"},
    "ARS": {"codigo": "ARS", "descripcion": "Peso argentino", "simbolo": "$"}
}


# ================================
# MODELOS DE DATOS
# ================================

@dataclass
class EmpresaData:
    """Modelo para datos de empresa emisora/receptora"""
    ruc: str
    dv: str
    razon_social: str
    nombre_fantasia: Optional[str] = None
    direccion: str = ""
    numero_casa: str = ""
    codigo_departamento: str = "01"
    departamento: str = "Capital"
    codigo_ciudad: str = "001"
    ciudad: str = "Asunción"
    telefono: str = ""
    email: str = ""
    codigo_postal: str = ""
    complemento_direccion: str = ""
    actividad_economica: str = "47300"  # Comercio minorista

    @property
    def ruc_completo(self) -> str:
        """Retorna RUC con DV en formato completo"""
        return f"{self.ruc}-{self.dv}"


@dataclass
class ProductoData:
    """Modelo para datos de productos/servicios"""
    codigo: str
    descripcion: str
    precio_unitario: Decimal
    unidad_medida: str = "77"  # Unidad por defecto
    tipo_item: str = "9"  # Producto
    codigo_ncm: str = ""
    codigo_gtin: str = ""
    precio_referencial: Optional[Decimal] = None
    observacion: str = ""

    def calcular_precio_con_iva(self, tasa_iva: Decimal = Decimal("10")) -> Decimal:
        """Calcula precio unitario incluyendo IVA"""
        factor_iva = Decimal("1") + (tasa_iva / Decimal("100"))
        return (self.precio_unitario * factor_iva).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )


@dataclass
class ItemFacturaData:
    """Modelo para items de factura"""
    codigo_interno: str
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    descuento_unitario: Decimal = Decimal("0")
    precio_total_bruto: Decimal = Decimal("0")  # Cambiar a no opcional
    descuento_global: Decimal = Decimal("0")
    anticipo_global: Decimal = Decimal("0")
    precio_total_operacion: Decimal = Decimal("0")  # Cambiar a no opcional
    iva_tipo: str = "1"  # IVA gravado
    iva_tasa: Decimal = Decimal("10")
    iva_base_gravada: Decimal = Decimal("0")  # Cambiar a no opcional
    iva_liquidado: Decimal = Decimal("0")  # Cambiar a no opcional

    def __post_init__(self):
        """Calcula campos derivados automáticamente"""
        # Asegurar que todos los valores sean Decimal válidos
        self.cantidad = self.cantidad or Decimal("1")
        self.precio_unitario = self.precio_unitario or Decimal("0")
        self.descuento_unitario = self.descuento_unitario or Decimal("0")

        # Calcular precio total bruto
        if self.precio_total_bruto == Decimal("0"):
            self.precio_total_bruto = self.cantidad * self.precio_unitario

        # Calcular descuentos y precio final
        descuento_total = self.descuento_unitario * self.cantidad
        precio_con_descuento = self.precio_total_bruto - descuento_total

        if self.precio_total_operacion == Decimal("0"):
            self.precio_total_operacion = precio_con_descuento

        # Calcular base gravada para IVA
        if self.iva_base_gravada == Decimal("0"):
            self.iva_base_gravada = self.precio_total_operacion

        # Calcular IVA liquidado
        if self.iva_liquidado == Decimal("0"):
            self.iva_liquidado = (
                self.iva_base_gravada * self.iva_tasa / Decimal("100")
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@dataclass
class DocumentoData:
    """Modelo base para documentos electrónicos"""
    tipo_documento: str
    numero_timbrado: str
    establecimiento: str = "001"
    punto_expedicion: str = "001"
    numero_documento: str = "0000001"
    fecha_emision: datetime = field(default_factory=datetime.now)
    condicion_operacion: str = CondicionOperacion.CONTADO.value
    moneda: str = "PYG"
    tipo_cambio: Decimal = Decimal("1")

    # Datos calculados
    total_operacion: Decimal = Decimal("0")
    total_descuento: Decimal = Decimal("0")
    total_anticipo: Decimal = Decimal("0")
    total_iva: Decimal = Decimal("0")
    total_general: Decimal = Decimal("0")

    def generar_numero_completo(self) -> str:
        """Genera número de documento en formato SIFEN"""
        return f"{self.establecimiento}-{self.punto_expedicion}-{self.numero_documento}"


# ================================
# PROVIDER PERSONALIZADO FAKER
# ================================

class SifenProvider(BaseProvider):
    """Provider personalizado para datos específicos de SIFEN Paraguay"""

    def ruc_paraguayo(self) -> str:
        """Genera RUC paraguayo válido de 8 dígitos"""
        # Generar 7 dígitos aleatorios
        ruc_base = ''.join([str(random.randint(0, 9)) for _ in range(7)])

        # Calcular dígito verificador usando algoritmo RUC Paraguay
        dv = self._calcular_dv_ruc(ruc_base)

        return f"{ruc_base}{dv}"

    def _calcular_dv_ruc(self, ruc_base: str) -> str:
        """Calcula dígito verificador para RUC paraguayo"""
        if len(ruc_base) != 7:
            raise ValueError("RUC base debe tener 7 dígitos")

        # Multiplicadores para cada posición
        multiplicadores = [2, 3, 4, 5, 6, 7, 2]

        suma = 0
        for i, digito in enumerate(ruc_base):
            suma += int(digito) * multiplicadores[i]

        resto = suma % 11

        if resto < 2:
            return str(resto)
        else:
            return str(11 - resto)

    def numero_timbrado(self) -> str:
        """Genera número de timbrado válido"""
        return str(random.randint(10000000, 99999999))

    def codigo_seguridad(self) -> str:
        """Genera código de seguridad de 9 dígitos"""
        return ''.join([str(random.randint(0, 9)) for _ in range(9)])

    def telefono_paraguayo(self) -> str:
        """Genera número de teléfono paraguayo válido"""
        prefijos_movil = ['0981', '0982', '0983',
                          '0984', '0985', '0986', '0987']
        prefijos_fijo = ['021', '0336', '0537', '0528']

        if random.choice([True, False]):
            # Teléfono móvil
            prefijo = random.choice(prefijos_movil)
            numero = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            return f"{prefijo}{numero}"
        else:
            # Teléfono fijo
            prefijo = random.choice(prefijos_fijo)
            numero = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            return f"{prefijo}{numero}"

    def email_paraguayo(self) -> str:
        """Genera email con dominios paraguayos comunes"""
        dominios = ['gmail.com', 'hotmail.com', 'yahoo.com', 'gmail.com.py',
                    'hotmail.com.py', 'paraguayos.com', 'tigo.com.py']
        usuario = faker.user_name()
        dominio = random.choice(dominios)
        return f"{usuario}@{dominio}"


# Registrar provider personalizado
faker.add_provider(SifenProvider)


# ================================
# CLASE PRINCIPAL: SifenDataFactory
# ================================

class SifenDataFactory:
    """
    Fábrica principal para generación de datos de testing SIFEN

    Proporciona métodos para generar entidades completas y consistentes
    que cumplan con las especificaciones del sistema SIFEN v150.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Inicializa la fábrica de datos

        Args:
            seed: Semilla para reproducibilidad en tests (opcional)
        """
        if seed is not None:
            random.seed(seed)
            faker.seed_instance(seed)

        self._contadores_documento = {
            tipo.value: 1 for tipo in TipoDocumento
        }

        logger.debug(f"SifenDataFactory inicializada con seed: {seed}")

    # ===== MÉTODOS DE EMPRESAS =====

    def crear_empresa_emisora(
        self,
        ruc: Optional[str] = None,
        tipo_contribuyente: TipoContribuyente = TipoContribuyente.PERSONA_JURIDICA
    ) -> EmpresaData:
        """
        Crea datos de empresa emisora válida

        Args:
            ruc: RUC específico a usar (opcional, se genera uno válido)
            tipo_contribuyente: Tipo de contribuyente

        Returns:
            EmpresaData: Datos completos de empresa emisora

        Examples:
            >>> factory = SifenDataFactory(seed=123)
            >>> emisor = factory.crear_empresa_emisora()
            >>> assert len(emisor.ruc) == 7
            >>> assert emisor.dv.isdigit()
            >>> assert emisor.codigo_departamento in DEPARTAMENTOS_PARAGUAY
        """
        # Asegurar que ruc y dv sean strings válidos
        ruc_final: str
        dv_final: str

        if ruc is None:
            # Generar RUC completo nuevo
            ruc_completo = faker.ruc_paraguayo()
            ruc_final = ruc_completo[:-1]  # 7 dígitos
            dv_final = ruc_completo[-1]    # 1 dígito
        else:
            # Validar RUC proporcionado
            ruc_clean = ruc.strip().replace('-', '')

            if len(ruc_clean) == 8:
                # RUC incluye DV
                ruc_final = ruc_clean[:-1]
                dv_final = ruc_clean[-1]
            elif len(ruc_clean) == 7:
                # RUC sin DV, calcularlo
                ruc_final = ruc_clean
                # Usar provider directamente para calcular DV
                provider = SifenProvider(None)
                dv_final = provider._calcular_dv_ruc(ruc_final)
            else:
                # RUC inválido, generar uno nuevo
                logger.warning(
                    f"RUC inválido proporcionado: {ruc}, generando uno nuevo")
                ruc_completo = faker.ruc_paraguayo()
                ruc_final = ruc_completo[:-1]
                dv_final = ruc_completo[-1]

        # Seleccionar ubicación aleatoria
        codigo_depto = random.choice(list(DEPARTAMENTOS_PARAGUAY.keys()))
        departamento = DEPARTAMENTOS_PARAGUAY[codigo_depto]

        if codigo_depto in ["01", "11"]:  # Capital o Central
            codigo_ciudad, ciudad = random.choice(
                list(CIUDADES_PRINCIPALES.values()))
        else:
            codigo_ciudad, ciudad = "001", departamento

        razon_social = self._generar_razon_social_realista()

        return EmpresaData(
            ruc=ruc_final,
            dv=dv_final,
            razon_social=razon_social,
            nombre_fantasia=self._generar_nombre_fantasia(razon_social),
            direccion=self._generar_direccion_paraguaya(),
            numero_casa=str(random.randint(1, 9999)),
            codigo_departamento=codigo_depto,
            departamento=departamento,
            codigo_ciudad=codigo_ciudad,
            ciudad=ciudad,
            telefono=faker.telefono_paraguayo(),
            email=faker.email_paraguayo(),
            codigo_postal=self._generar_codigo_postal(),
            actividad_economica=self._generar_actividad_economica()
        )

    def crear_empresa_receptora(
        self,
        es_extranjero: bool = False
    ) -> EmpresaData:
        """
        Crea datos de empresa receptora (cliente)

        Args:
            es_extranjero: Si es contribuyente extranjero

        Returns:
            EmpresaData: Datos completos de empresa receptora
        """
        if es_extranjero:
            ruc = "0"  # RUC especial para extranjeros
            dv = "0"
        else:
            ruc_completo = faker.ruc_paraguayo()
            ruc = ruc_completo[:-1]
            dv = ruc_completo[-1]

        # Clientes pueden estar en cualquier parte del país
        codigo_depto = random.choice(list(DEPARTAMENTOS_PARAGUAY.keys()))
        departamento = DEPARTAMENTOS_PARAGUAY[codigo_depto]

        return EmpresaData(
            ruc=ruc,
            dv=dv,
            razon_social=self._generar_razon_social_cliente(),
            direccion=self._generar_direccion_paraguaya(),
            numero_casa=str(random.randint(1, 999)),
            codigo_departamento=codigo_depto,
            departamento=departamento,
            codigo_ciudad="001",
            ciudad=departamento,
            telefono=faker.telefono_paraguayo(),
            email=faker.email_paraguayo()
        )

    # ===== MÉTODOS DE PRODUCTOS =====

    def crear_producto_simple(self, precio_base: Optional[Decimal] = None) -> ProductoData:
        """
        Crea datos de producto simple para testing

        Args:
            precio_base: Precio base del producto (opcional)

        Returns:
            ProductoData: Datos completos del producto
        """
        productos_comunes = [
            "Producto de prueba básico",
            "Servicio de consultoría",
            "Artículo de oficina",
            "Producto tecnológico",
            "Servicio profesional",
            "Material de construcción",
            "Producto alimenticio",
            "Artículo de limpieza"
        ]

        if precio_base is None:
            precio_base = Decimal(str(random.randint(1000, 500000)))

        return ProductoData(
            codigo=f"PROD{random.randint(1000, 9999)}",
            descripcion=random.choice(productos_comunes),
            precio_unitario=precio_base,
            unidad_medida="77",  # Unidad
            codigo_ncm=f"{random.randint(1000, 9999)}.{random.randint(10, 99)}.{random.randint(10, 99)}"
        )

    def crear_lista_productos(self, cantidad: int = 3) -> List[ProductoData]:
        """
        Crea lista de productos para factura

        Args:
            cantidad: Número de productos a generar

        Returns:
            List[ProductoData]: Lista de productos generados
        """
        productos = []
        for i in range(cantidad):
            precio = Decimal(str(random.randint(10000, 1000000)))
            producto = self.crear_producto_simple(precio)
            producto.codigo = f"PROD{i+1:03d}"
            productos.append(producto)

        return productos

    # ===== MÉTODOS DE ITEMS DE FACTURA =====

    def crear_item_factura(
        self,
        producto: Optional[ProductoData] = None,
        cantidad: Optional[Decimal] = None
    ) -> ItemFacturaData:
        """
        Crea item de factura con cálculos automáticos

        Args:
            producto: Datos del producto (opcional, se genera uno)
            cantidad: Cantidad del item (opcional, se genera aleatoria)

        Returns:
            ItemFacturaData: Item de factura con cálculos completos
        """
        if producto is None:
            producto = self.crear_producto_simple()

        if cantidad is None:
            cantidad = Decimal(str(random.randint(1, 10)))

        # Generar descuentos ocasionales
        descuento_unitario = Decimal("0")
        if random.random() < 0.3:  # 30% chance de descuento
            descuento_unitario = producto.precio_unitario * \
                Decimal("0.05")  # 5% descuento

        return ItemFacturaData(
            codigo_interno=producto.codigo,
            descripcion=producto.descripcion,
            cantidad=cantidad,
            precio_unitario=producto.precio_unitario,
            descuento_unitario=descuento_unitario,
            iva_tasa=Decimal("10")  # IVA estándar Paraguay
        )

    def crear_items_factura(self, cantidad_items: int = 3) -> List[ItemFacturaData]:
        """
        Crea lista de items para factura con variedad realista

        Args:
            cantidad_items: Número de items a generar

        Returns:
            List[ItemFacturaData]: Lista de items generados
        """
        items = []
        productos = self.crear_lista_productos(cantidad_items)

        for i, producto in enumerate(productos):
            cantidad = Decimal(str(random.randint(1, 5)))
            item = self.crear_item_factura(producto, cantidad)
            items.append(item)

        return items

    # ===== MÉTODOS DE DOCUMENTOS =====

    def crear_factura_simple(
        self,
        emisor: Optional[EmpresaData] = None,
        receptor: Optional[EmpresaData] = None,
        items: Optional[List[ItemFacturaData]] = None
    ) -> Dict[str, Any]:
        """
        Crea datos completos para factura electrónica simple

        Args:
            emisor: Datos del emisor (opcional)
            receptor: Datos del receptor (opcional) 
            items: Items de la factura (opcional)

        Returns:
            Dict[str, Any]: Datos completos de factura lista para generar XML
        """
        if emisor is None:
            emisor = self.crear_empresa_emisora()

        if receptor is None:
            receptor = self.crear_empresa_receptora()

        if items is None:
            items = self.crear_items_factura(random.randint(1, 5))

        # Generar datos del documento
        numero_doc = self._obtener_siguiente_numero(
            TipoDocumento.FACTURA_ELECTRONICA)

        documento = DocumentoData(
            tipo_documento=TipoDocumento.FACTURA_ELECTRONICA.value,
            numero_timbrado=faker.numero_timbrado(),
            numero_documento=f"{numero_doc:07d}",
            fecha_emision=self._generar_fecha_reciente()
        )

        # Calcular totales
        self._calcular_totales_documento(documento, items)

        return {
            "documento": documento,
            "emisor": emisor,
            "receptor": receptor,
            "items": items,
            "condiciones_pago": self._generar_condiciones_pago(documento.total_general),
            "metadatos": {
                "codigo_seguridad": faker.codigo_seguridad(),
                "cdc": self._generar_cdc_preliminar(documento, emisor),
                "version_formato": "150"
            }
        }

    def crear_autofactura_completa(self) -> Dict[str, Any]:
        """Crea autofactura electrónica completa"""
        return self._crear_documento_tipo(TipoDocumento.AUTOFACTURA_ELECTRONICA)

    def crear_nota_credito(self, factura_referencia: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crea nota de crédito electrónica"""
        nota = self._crear_documento_tipo(
            TipoDocumento.NOTA_CREDITO_ELECTRONICA)

        if factura_referencia:
            nota["documento_referencia"] = {
                "tipo_documento": factura_referencia["documento"].tipo_documento,
                "numero_documento": factura_referencia["documento"].generar_numero_completo(),
                "fecha_emision": factura_referencia["documento"].fecha_emision
            }

        return nota

    # ===== MÉTODOS DE CASOS EDGE =====

    def crear_caso_edge(self, tipo_caso: str) -> Dict[str, Any]:
        """
        Crea casos edge específicos para testing

        Args:
            tipo_caso: Tipo de caso edge a generar

        Returns:
            Dict[str, Any]: Datos del caso edge

        Casos disponibles:
            - "ruc_extranjero": Cliente extranjero
            - "monto_alto": Factura con monto muy alto
            - "muchos_items": Factura con muchos items
            - "descuentos_complejos": Múltiples tipos de descuentos
            - "moneda_extranjera": Factura en moneda extranjera
        """
        casos_edge = {
            "ruc_extranjero": self._caso_ruc_extranjero,
            "monto_alto": self._caso_monto_alto,
            "muchos_items": self._caso_muchos_items,
            "descuentos_complejos": self._caso_descuentos_complejos,
            "moneda_extranjera": self._caso_moneda_extranjera,
            "fecha_limite": self._caso_fecha_limite,
            "items_sin_iva": self._caso_items_sin_iva
        }

        if tipo_caso not in casos_edge:
            raise ValueError(f"Tipo de caso edge no válido: {tipo_caso}")

        logger.debug(f"Generando caso edge: {tipo_caso}")
        return casos_edge[tipo_caso]()

    def crear_lote_documentos(self, cantidad: int = 10) -> List[Dict[str, Any]]:
        """
        Crea lote de documentos para testing de envío masivo

        Args:
            cantidad: Número de documentos a generar

        Returns:
            List[Dict[str, Any]]: Lista de documentos generados
        """
        documentos = []

        for i in range(cantidad):
            # Variar tipos de documentos
            if i % 3 == 0:
                doc = self.crear_autofactura_completa()
            elif i % 5 == 0:
                doc = self.crear_nota_credito()
            else:
                doc = self.crear_factura_simple()

            documentos.append(doc)

        logger.debug(f"Generados {cantidad} documentos para lote")
        return documentos

    # ===== MÉTODOS PRIVADOS DE APOYO =====

    def _generar_razon_social_realista(self) -> str:
        """Genera razón social realista para empresa paraguaya"""
        tipos_empresa = ["S.A.", "S.R.L.", "LTDA.", "E.I.R.L."]
        prefijos = ["Comercial", "Industrial", "Servicios", "Distribuidora",
                    "Importadora", "Exportadora", "Constructora", "Consultora"]
        nombres = ["Paraguaya", "del Este", "Central", "Sur", "Norte",
                   "Internacional", "Nacional", "Regional"]

        prefijo = random.choice(prefijos)
        nombre = random.choice(nombres)
        tipo = random.choice(tipos_empresa)

        return f"{prefijo} {nombre} {tipo}"

    def _generar_nombre_fantasia(self, razon_social: str) -> str:
        """Genera nombre fantasía basado en razón social"""
        # Tomar primera palabra de razón social
        primera_palabra = razon_social.split()[0]
        sufijos = ["Store", "Shop", "Center", "Express", "Plus", "Pro"]
        sufijo = random.choice(sufijos)

        return f"{primera_palabra} {sufijo}"

    def _generar_razon_social_cliente(self) -> str:
        """Genera razón social para clientes"""
        if random.random() < 0.3:  # 30% personas físicas
            return faker.name()
        else:
            return self._generar_razon_social_realista()

    def _generar_direccion_paraguaya(self) -> str:
        """Genera dirección realista para Paraguay"""
        tipos_via = ["Av.", "Calle", "Ruta", "Avda.", "C/"]
        nombres_via = ["España", "Brasil", "Argentina", "Mcal. López", "Gral. Santos",
                       "15 de Agosto", "Independencia Nacional", "Capiatá", "Luque"]

        tipo = random.choice(tipos_via)
        nombre = random.choice(nombres_via)

        return f"{tipo} {nombre}"

    def _generar_codigo_postal(self) -> str:
        """Genera código postal paraguayo"""
        return f"{random.randint(1000, 9999)}"

    def _generar_actividad_economica(self) -> str:
        """Genera código de actividad económica común"""
        actividades_comunes = [
            "47300",  # Comercio minorista
            "47110",  # Comercio en supermercados
            "46900",  # Comercio mayorista
            "62010",  # Programación informática
            "68100",  # Actividades inmobiliarias
            "70220",  # Consultoría de gestión
            "43220",  # Construcción
            "56100"   # Restaurantes
        ]
        return random.choice(actividades_comunes)

    def _generar_fecha_reciente(self) -> datetime:
        """Genera fecha de emisión reciente (últimos 30 días)"""
        ahora = datetime.now()
        dias_atras = random.randint(0, 30)
        fecha = ahora - timedelta(days=dias_atras)

        # Asegurar que sea día hábil (lunes a viernes)
        while fecha.weekday() > 4:  # 5=sábado, 6=domingo
            fecha = fecha - timedelta(days=1)

        return fecha

    def _obtener_siguiente_numero(self, tipo_doc: TipoDocumento) -> int:
        """Obtiene siguiente número de documento para el tipo especificado"""
        numero = self._contadores_documento[tipo_doc.value]
        self._contadores_documento[tipo_doc.value] += 1
        return numero

    def _calcular_totales_documento(self, documento: DocumentoData, items: List[ItemFacturaData]) -> None:
        """Calcula totales del documento basado en los items"""
        total_operacion = Decimal("0")
        total_descuento = Decimal("0")
        total_iva = Decimal("0")

        for item in items:
            # Asegurar que precio_total_operacion no sea None
            precio_operacion = item.precio_total_operacion or Decimal("0")
            total_operacion += precio_operacion

            # Calcular descuento total del item
            descuento_item = (item.descuento_unitario or Decimal(
                "0")) * (item.cantidad or Decimal("1"))
            total_descuento += descuento_item

            # Asegurar que iva_liquidado no sea None
            iva_item = item.iva_liquidado or Decimal("0")
            total_iva += iva_item

        # Asignar totales calculados
        documento.total_operacion = total_operacion
        documento.total_descuento = total_descuento
        documento.total_iva = total_iva
        documento.total_general = total_operacion + total_iva

    def _generar_condiciones_pago(self, monto_total: Decimal) -> Dict[str, Any]:
        """Genera condiciones de pago según el monto"""
        if monto_total < Decimal("100000"):  # Menos de 100k
            return {
                "condicion": CondicionOperacion.CONTADO.value,
                "descripcion": "Contado",
                "plazo": 0
            }
        else:
            # Pagos a crédito ocasionales
            if random.random() < 0.3:
                plazo_dias = random.choice([30, 60, 90])
                return {
                    "condicion": CondicionOperacion.CREDITO.value,
                    "descripcion": f"Crédito {plazo_dias} días",
                    "plazo": plazo_dias,
                    "cuotas": [
                        {
                            "numero": 1,
                            "vencimiento": datetime.now() + timedelta(days=plazo_dias),
                            "monto": monto_total
                        }
                    ]
                }
            else:
                return {
                    "condicion": CondicionOperacion.CONTADO.value,
                    "descripcion": "Contado",
                    "plazo": 0
                }

    def _generar_cdc_preliminar(self, documento: DocumentoData, emisor: EmpresaData) -> str:
        """Genera CDC preliminar para testing (44 caracteres)"""
        # Estructura CDC: dTipDTE(2) + dRucEm(8) + dDVEmi(1) + dEst(3) + dPunExp(3) + dNumDoc(7) + dTipEmis(1) + fecha(8) + dCodSeg(9) + checksum(2)

        fecha_str = documento.fecha_emision.strftime("%Y%m%d")
        codigo_seg = faker.codigo_seguridad()

        # Construir CDC sin checksum
        cdc_parcial = (
            documento.tipo_documento.zfill(2) +
            emisor.ruc.zfill(8) +
            emisor.dv +
            documento.establecimiento.zfill(3) +
            documento.punto_expedicion.zfill(3) +
            documento.numero_documento.zfill(7) +
            "1" +  # Tipo emisión: Normal
            fecha_str +
            codigo_seg
        )

        # Generar checksum simple para testing
        checksum = str(sum(int(c)
                       for c in cdc_parcial if c.isdigit()) % 100).zfill(2)

        return cdc_parcial + checksum

    def _crear_documento_tipo(self, tipo_doc: TipoDocumento) -> Dict[str, Any]:
        """Método genérico para crear cualquier tipo de documento"""
        emisor = self.crear_empresa_emisora()
        receptor = self.crear_empresa_receptora()
        items = self.crear_items_factura(random.randint(1, 4))

        numero_doc = self._obtener_siguiente_numero(tipo_doc)

        documento = DocumentoData(
            tipo_documento=tipo_doc.value,
            numero_timbrado=faker.numero_timbrado(),
            numero_documento=f"{numero_doc:07d}",
            fecha_emision=self._generar_fecha_reciente()
        )

        self._calcular_totales_documento(documento, items)

        return {
            "documento": documento,
            "emisor": emisor,
            "receptor": receptor,
            "items": items,
            "condiciones_pago": self._generar_condiciones_pago(documento.total_general),
            "metadatos": {
                "codigo_seguridad": faker.codigo_seguridad(),
                "cdc": self._generar_cdc_preliminar(documento, emisor),
                "version_formato": "150"
            }
        }

    # ===== CASOS EDGE ESPECÍFICOS =====

    def _caso_ruc_extranjero(self) -> Dict[str, Any]:
        """Caso edge: Cliente extranjero"""
        factura = self.crear_factura_simple()

        # Modificar receptor para ser extranjero
        receptor_extranjero = self.crear_empresa_receptora(es_extranjero=True)
        receptor_extranjero.razon_social = "CLIENTE EXTRANJERO S.A."
        receptor_extranjero.codigo_departamento = "01"
        receptor_extranjero.ciudad = "Asunción"

        factura["receptor"] = receptor_extranjero
        factura["metadatos"]["caso_edge"] = "ruc_extranjero"

        return factura

    def _caso_monto_alto(self) -> Dict[str, Any]:
        """Caso edge: Factura con monto muy alto"""
        factura = self.crear_factura_simple()

        # Modificar items para tener precios muy altos
        for item in factura["items"]:
            item.precio_unitario = Decimal("10000000")  # 10 millones
            item.cantidad = Decimal("5")
            # Recalcular campos derivados
            item.__post_init__()

        # Recalcular totales del documento
        self._calcular_totales_documento(
            factura["documento"], factura["items"])

        factura["metadatos"]["caso_edge"] = "monto_alto"

        return factura

    def _caso_muchos_items(self) -> Dict[str, Any]:
        """Caso edge: Factura con muchos items (máximo permitido)"""
        emisor = self.crear_empresa_emisora()
        receptor = self.crear_empresa_receptora()

        # Crear muchos items (cerca del límite)
        items = []
        for i in range(50):  # 50 items
            producto = ProductoData(
                codigo=f"ITEM{i+1:03d}",
                descripcion=f"Producto múltiple número {i+1}",
                precio_unitario=Decimal(str(random.randint(1000, 50000)))
            )
            item = self.crear_item_factura(producto, Decimal("1"))
            items.append(item)

        numero_doc = self._obtener_siguiente_numero(
            TipoDocumento.FACTURA_ELECTRONICA)

        documento = DocumentoData(
            tipo_documento=TipoDocumento.FACTURA_ELECTRONICA.value,
            numero_timbrado=faker.numero_timbrado(),
            numero_documento=f"{numero_doc:07d}",
            fecha_emision=self._generar_fecha_reciente()
        )

        self._calcular_totales_documento(documento, items)

        return {
            "documento": documento,
            "emisor": emisor,
            "receptor": receptor,
            "items": items,
            "condiciones_pago": self._generar_condiciones_pago(documento.total_general),
            "metadatos": {
                "codigo_seguridad": faker.codigo_seguridad(),
                "cdc": self._generar_cdc_preliminar(documento, emisor),
                "version_formato": "150",
                "caso_edge": "muchos_items"
            }
        }

    def _caso_descuentos_complejos(self) -> Dict[str, Any]:
        """Caso edge: Múltiples tipos de descuentos"""
        factura = self.crear_factura_simple()

        # Aplicar descuentos complejos
        for i, item in enumerate(factura["items"]):
            if i % 2 == 0:
                # Descuento por item
                item.descuento_unitario = item.precio_unitario * \
                    Decimal("0.10")  # 10%

            # Descuento global ocasional
            if i == 0:
                item.descuento_global = Decimal("5000")  # Descuento fijo

            # Recalcular
            item.__post_init__()

        # Recalcular totales
        self._calcular_totales_documento(
            factura["documento"], factura["items"])

        factura["metadatos"]["caso_edge"] = "descuentos_complejos"

        return factura

    def _caso_moneda_extranjera(self) -> Dict[str, Any]:
        """Caso edge: Factura en moneda extranjera"""
        factura = self.crear_factura_simple()

        # Cambiar a dólares
        factura["documento"].moneda = "USD"
        factura["documento"].tipo_cambio = Decimal(
            "7300")  # Tipo de cambio aproximado

        # Ajustar precios a dólares
        for item in factura["items"]:
            precio_usd = item.precio_unitario / \
                factura["documento"].tipo_cambio
            item.precio_unitario = precio_usd.quantize(Decimal('0.01'))
            item.__post_init__()

        # Recalcular totales
        self._calcular_totales_documento(
            factura["documento"], factura["items"])

        factura["metadatos"]["caso_edge"] = "moneda_extranjera"

        return factura

    def _caso_fecha_limite(self) -> Dict[str, Any]:
        """Caso edge: Factura con fecha límite (31 de diciembre)"""
        factura = self.crear_factura_simple()

        # Establecer fecha 31 de diciembre del año actual
        año_actual = datetime.now().year
        factura["documento"].fecha_emision = datetime(
            año_actual, 12, 31, 23, 59, 59)

        # Regenerar CDC con nueva fecha
        factura["metadatos"]["cdc"] = self._generar_cdc_preliminar(
            factura["documento"],
            factura["emisor"]
        )

        factura["metadatos"]["caso_edge"] = "fecha_limite"

        return factura

    def _caso_items_sin_iva(self) -> Dict[str, Any]:
        """Caso edge: Items exentos de IVA"""
        factura = self.crear_factura_simple()

        # Modificar items para estar exentos
        for item in factura["items"]:
            item.iva_tipo = "2"  # Exento
            item.iva_tasa = Decimal("0")
            item.iva_liquidado = Decimal("0")

        # Recalcular totales
        self._calcular_totales_documento(
            factura["documento"], factura["items"])

        factura["metadatos"]["caso_edge"] = "items_sin_iva"

        return factura


# ================================
# BUILDER PATTERNS
# ================================

class FacturaBuilder:
    """
    Builder pattern para construcción incremental de facturas

    Permite construir facturas paso a paso con mayor control
    sobre cada aspecto de los datos generados.
    """

    def __init__(self, factory: SifenDataFactory):
        """
        Inicializa el builder con una fábrica de datos

        Args:
            factory: Instancia de SifenDataFactory
        """
        self.factory = factory
        self.reset()

    def reset(self) -> 'FacturaBuilder':
        """Reinicia el builder para crear nueva factura"""
        self._emisor = None
        self._receptor = None
        self._items = []
        self._documento_data = {}
        self._metadatos = {}
        return self

    def con_emisor(self, ruc: Optional[str] = None, razon_social: Optional[str] = None) -> 'FacturaBuilder':
        """
        Configura emisor de la factura

        Args:
            ruc: RUC específico del emisor
            razon_social: Razón social específica

        Returns:
            FacturaBuilder: Instancia del builder para encadenamiento
        """
        self._emisor = self.factory.crear_empresa_emisora(ruc=ruc)
        if razon_social:
            self._emisor.razon_social = razon_social
        return self

    def con_receptor(self, ruc: Optional[str] = None, es_extranjero: bool = False) -> 'FacturaBuilder':
        """Configura receptor de la factura"""
        self._receptor = self.factory.crear_empresa_receptora(
            es_extranjero=es_extranjero)

        if ruc and not es_extranjero:
            # Limpiar y validar RUC
            ruc_clean = ruc.strip().replace('-', '')

            if len(ruc_clean) == 8:
                # RUC con DV incluido
                self._receptor.ruc = ruc_clean[:-1]
                self._receptor.dv = ruc_clean[-1]
            elif len(ruc_clean) == 7:
                # RUC sin DV, calcularlo
                self._receptor.ruc = ruc_clean
                # Usar el provider global faker en lugar del atributo de instancia
                provider = SifenProvider(None)
                self._receptor.dv = provider._calcular_dv_ruc(ruc_clean)
            else:
                # RUC inválido, mantener el generado por defecto
                logger.warning(
                    f"RUC inválido para receptor: {ruc}, usando RUC generado")

        return self

    def agregar_item(
        self,
        descripcion: str,
        precio: Decimal,
        cantidad: Decimal = Decimal("1")
    ) -> 'FacturaBuilder':
        """Agrega item específico a la factura"""
        producto = ProductoData(
            codigo=f"CUSTOM{len(self._items)+1:03d}",
            descripcion=descripcion,
            precio_unitario=precio
        )
        item = self.factory.crear_item_factura(producto, cantidad)
        self._items.append(item)
        return self

    def con_items_aleatorios(self, cantidad: int = 3) -> 'FacturaBuilder':
        """Agrega items aleatorios a la factura"""
        items_aleatorios = self.factory.crear_items_factura(cantidad)
        self._items.extend(items_aleatorios)
        return self

    def con_fecha(self, fecha: datetime) -> 'FacturaBuilder':
        """Establece fecha específica de emisión"""
        self._documento_data['fecha_emision'] = fecha
        return self

    def con_moneda(self, codigo_moneda: str, tipo_cambio: Decimal = Decimal("1")) -> 'FacturaBuilder':
        """Establece moneda y tipo de cambio"""
        self._documento_data['moneda'] = codigo_moneda
        self._documento_data['tipo_cambio'] = tipo_cambio
        return self

    def con_numero_timbrado(self, timbrado: str) -> 'FacturaBuilder':
        """Establece número de timbrado específico"""
        self._documento_data['numero_timbrado'] = timbrado
        return self

    def construir(self) -> Dict[str, Any]:
        """
        Construye la factura final con todos los datos configurados

        Returns:
            Dict[str, Any]: Factura completa construida
        """
        # Usar valores por defecto si no se especificaron
        if self._emisor is None:
            self._emisor = self.factory.crear_empresa_emisora()

        if self._receptor is None:
            self._receptor = self.factory.crear_empresa_receptora()

        if not self._items:
            self._items = self.factory.crear_items_factura(3)

        # Crear documento con datos especificados
        numero_doc = self.factory._obtener_siguiente_numero(
            TipoDocumento.FACTURA_ELECTRONICA)

        documento = DocumentoData(
            tipo_documento=TipoDocumento.FACTURA_ELECTRONICA.value,
            numero_timbrado=self._documento_data.get(
                'numero_timbrado', faker.numero_timbrado()),
            numero_documento=f"{numero_doc:07d}",
            fecha_emision=self._documento_data.get(
                'fecha_emision', self.factory._generar_fecha_reciente()),
            moneda=self._documento_data.get('moneda', 'PYG'),
            tipo_cambio=self._documento_data.get('tipo_cambio', Decimal("1"))
        )

        # Calcular totales
        self.factory._calcular_totales_documento(documento, self._items)

        return {
            "documento": documento,
            "emisor": self._emisor,
            "receptor": self._receptor,
            "items": self._items,
            "condiciones_pago": self.factory._generar_condiciones_pago(documento.total_general),
            "metadatos": {
                "codigo_seguridad": faker.codigo_seguridad(),
                "cdc": self.factory._generar_cdc_preliminar(documento, self._emisor),
                "version_formato": "150",
                "builder_used": True,
                **self._metadatos
            }
        }


# ================================
# UTILIDADES Y HELPERS
# ================================

def validar_ruc_paraguayo(ruc: str) -> bool:
    """
    Valida formato y dígito verificador de RUC paraguayo

    Args:
        ruc: RUC a validar (puede incluir o no el DV)

    Returns:
        bool: True si el RUC es válido

    Examples:
        >>> validar_ruc_paraguayo("12345678")  # Con DV
        True
        >>> validar_ruc_paraguayo("1234567")   # Sin DV, se calcula
        True
        >>> validar_ruc_paraguayo("123")       # Muy corto
        False
    """
    if not ruc or not ruc.replace('-', '').isdigit():
        return False

    # Limpiar RUC
    ruc_clean = ruc.replace('-', '')

    if len(ruc_clean) < 7 or len(ruc_clean) > 8:
        return False

    # Crear provider para cálculos
    provider = SifenProvider(None)

    if len(ruc_clean) == 7:
        # Calcular DV y validar
        try:
            dv_calculado = provider._calcular_dv_ruc(ruc_clean)
            return True  # Si no hay excepción, el formato es válido
        except:
            return False
    else:
        # Validar DV existente
        ruc_base = ruc_clean[:-1]
        dv_actual = ruc_clean[-1]
        try:
            dv_calculado = provider._calcular_dv_ruc(ruc_base)
            return dv_calculado == dv_actual
        except:
            return False


def generar_datos_testing_rapido(
    cantidad_facturas: int = 5,
    seed: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Función de conveniencia para generar datos de testing rápido

    Args:
        cantidad_facturas: Número de facturas a generar
        seed: Semilla para reproducibilidad

    Returns:
        List[Dict[str, Any]]: Lista de facturas generadas

    Examples:
        >>> facturas = generar_datos_testing_rapido(3, seed=123)
        >>> assert len(facturas) == 3
        >>> assert all('documento' in f for f in facturas)
    """
    factory = SifenDataFactory(seed=seed)

    facturas = []
    for i in range(cantidad_facturas):
        if i % 4 == 0:
            # Caso especial cada 4 facturas
            factura = factory.crear_caso_edge("ruc_extranjero")
        else:
            factura = factory.crear_factura_simple()

        facturas.append(factura)

    logger.info(f"Generadas {cantidad_facturas} facturas para testing rápido")
    return facturas


def extraer_datos_para_xml(datos_factura: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae y formatea datos de factura para generación XML

    Args:
        datos_factura: Datos completos de factura del factory

    Returns:
        Dict[str, Any]: Datos formateados para XML generator

    Examples:
        >>> factory = SifenDataFactory()
        >>> factura = factory.crear_factura_simple()
        >>> datos_xml = extraer_datos_para_xml(factura)
        >>> assert 'dRUCEmi' in datos_xml
        >>> assert 'items' in datos_xml
    """
    factura_data = datos_factura
    doc = factura_data["documento"]
    emisor = factura_data["emisor"]
    receptor = factura_data["receptor"]
    items = factura_data["items"]
    metadatos = factura_data["metadatos"]

    return {
        # Datos del documento
        "dVerFor": metadatos["version_formato"],
        "iTipDE": doc.tipo_documento,
        "dNumTim": doc.numero_timbrado,
        "dEst": doc.establecimiento,
        "dPunExp": doc.punto_expedicion,
        "dNumDoc": doc.numero_documento,
        "dFeEmiDE": doc.fecha_emision.isoformat(),
        "dCodSeg": metadatos["codigo_seguridad"],

        # Datos del emisor
        "dRUCEmi": emisor.ruc,
        "dDVEmi": emisor.dv,
        "dNomEmi": emisor.razon_social,
        "dNomFanEmi": emisor.nombre_fantasia,
        "dDirEmi": emisor.direccion,
        "dNumCasEmi": emisor.numero_casa,
        "cDepEmi": emisor.codigo_departamento,
        "dDesDepEmi": emisor.departamento,
        "cCiuEmi": emisor.codigo_ciudad,
        "dDesCiuEmi": emisor.ciudad,
        "dTelEmi": emisor.telefono,
        "dEmailE": emisor.email,

        # Datos del receptor
        "dRUCRec": receptor.ruc,
        "dDVRec": receptor.dv,
        "dNomRec": receptor.razon_social,
        "dDirRec": receptor.direccion,
        "dNumCasRec": receptor.numero_casa,
        "cDepRec": receptor.codigo_departamento,
        "dDesDepRec": receptor.departamento,
        "cCiuRec": receptor.codigo_ciudad,
        "dDesCiuRec": receptor.ciudad,
        "dTelRec": receptor.telefono,
        "dEmailR": receptor.email,

        # Condiciones de operación
        "iTiOpe": factura_data["condiciones_pago"]["condicion"],
        "dDesTiOpe": factura_data["condiciones_pago"]["descripcion"],
        "cMoneOpe": doc.moneda,
        "dTiCam": str(doc.tipo_cambio),

        # Items
        "items": [
            {
                "dCodInt": item.codigo_interno,
                "dDesProSer": item.descripcion,
                "cUniMed": "77",  # Unidad por defecto
                "dCantProSer": str(item.cantidad),
                "dPUniProSer": str(item.precio_unitario),
                "dTotBruXIt": str(item.precio_total_bruto),
                "dDescItem": str((item.descuento_unitario or Decimal("0")) * (item.cantidad or Decimal("1"))),
                "dTotOpeItem": str(item.precio_total_operacion),
                "dTasaIVA": str(item.iva_tasa),
                "dBasGravIVA": str(item.iva_base_gravada),
                "dLiqIVAItem": str(item.iva_liquidado)
            }
            for item in items
        ],

        # Totales
        "dTotOpe": str(doc.total_operacion),
        "dTotDesc": str(doc.total_descuento),
        "dTotDescGlotem": "0",
        "dTotAntItem": "0",
        "dTotAnt": "0",
        "dPorcDescTotal": "0",
        "dDescTotal": str(doc.total_descuento),
        "dAnticipo": "0",
        "dRedon": "0",
        "dTotGralOpe": str(doc.total_general),
        "dLiqTotIVA5": "0",
        "dLiqTotIVA10": str(doc.total_iva),
        "dTotIVA": str(doc.total_iva),
        "dBaseGrav5": "0",
        "dBaseGrav10": str(doc.total_operacion),
        "dTBaseGraIVA": str(doc.total_operacion),

        # Metadatos adicionales
        "cdc_preliminar": metadatos["cdc"]
    }


# ================================
# EXPORT API
# ================================

__all__ = [
    # Clases principales
    'SifenDataFactory',
    'FacturaBuilder',

    # Modelos de datos
    'EmpresaData',
    'ProductoData',
    'ItemFacturaData',
    'DocumentoData',

    # Enums
    'TipoDocumento',
    'TipoContribuyente',
    'CondicionOperacion',

    # Utilidades
    'validar_ruc_paraguayo',
    'generar_datos_testing_rapido',
    'extraer_datos_para_xml',

    # Constantes
    'DEPARTAMENTOS_PARAGUAY',
    'CIUDADES_PRINCIPALES',
    'MONEDAS_VALIDAS'
]
