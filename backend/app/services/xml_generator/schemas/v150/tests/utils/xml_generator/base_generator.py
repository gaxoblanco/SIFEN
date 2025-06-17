"""
Generador base para XMLs de prueba SIFEN Paraguay v150.

Este módulo proporciona una clase base abstracta que implementa funcionalidades
comunes para generar documentos electrónicos de prueba compatibles con el 
sistema SIFEN (Sistema Integrado de Facturación Electrónica) de Paraguay.

Versión: 150 (septiembre 2019)
Namespace: http://ekuatia.set.gov.py/sifen/xsd
Patrón: Template Method + Abstract Base Class

Autor: Sistema de Testing SIFEN v150
Fecha: 2025
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from xml.etree.ElementTree import Element
import random
import string


@dataclass
class GeneratorConfig:
    """
    Configuración para los generadores XML SIFEN.

    Attributes:
        namespace: Namespace oficial SIFEN v150
        version: Versión del formato SIFEN
        encoding: Codificación de caracteres
        validate_on_generate: Si validar XML al generar (False para testing)
        random_seed: Semilla para generación aleatoria reproducible
    """
    namespace: str = "http://ekuatia.set.gov.py/sifen/xsd"
    version: str = "150"
    encoding: str = "UTF-8"
    validate_on_generate: bool = False
    random_seed: Optional[int] = None


class BaseXMLGenerator(ABC):
    """
    Clase base abstracta para generadores de XML SIFEN v150.

    Proporciona funcionalidades comunes para generar documentos electrónicos
    de prueba compatibles con SIFEN Paraguay. Implementa el patrón Template Method
    donde las subclases deben implementar el método generate().

    Attributes:
        config: Configuración del generador
        _random: Generador de números aleatorios

    Constants:
        DOCUMENT_TYPES: Tipos de documentos oficiales SIFEN
        XML_NAMESPACES: Namespaces y atributos XML requeridos
        PARAGUAY_TZ: Zona horaria de Paraguay (UTC-3)
    """

    # Tipos de documentos según Manual Técnico SIFEN v150
    DOCUMENT_TYPES = {
        "01": "Factura electrónica",
        "04": "Autofactura electrónica",
        "05": "Nota de crédito electrónica",
        "06": "Nota de débito electrónica",
        "07": "Nota de remisión electrónica"
    }

    # Namespace y atributos XML oficiales
    XML_NAMESPACES = {
        'xmlns': "http://ekuatia.set.gov.py/sifen/xsd",
        'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
        'xsi:schemaLocation': "http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd"
    }

    # Zona horaria Paraguay (UTC-3)
    PARAGUAY_TZ = timezone(timedelta(hours=-3))

    def __init__(self, config: Optional[GeneratorConfig] = None):
        """
        Inicializa el generador base.

        Args:
            config: Configuración del generador. Si es None, usa configuración por defecto.
        """
        self.config = config or GeneratorConfig()

        # Inicializar generador aleatorio con semilla si se especifica
        if self.config.random_seed is not None:
            self._random = random.Random(self.config.random_seed)
        else:
            self._random = random.Random()

    @abstractmethod
    def generate(self, **kwargs) -> str:
        """
        Método abstracto principal para generar XML.

        Las subclases deben implementar este método para generar el XML específico
        del tipo de documento que manejan.

        Args:
            **kwargs: Parámetros específicos del tipo de documento

        Returns:
            str: XML generado como string

        Raises:
            NotImplementedError: Si la subclase no implementa este método
        """
        pass

    def wrap_element(self, tag: str, content: str, attrs: Optional[Dict[str, str]] = None) -> str:
        """
        Envuelve contenido en un elemento XML con atributos opcionales.

        Args:
            tag: Nombre del elemento XML
            content: Contenido interno del elemento
            attrs: Diccionario de atributos opcionales

        Returns:
            str: Elemento XML formateado

        Example:
            >>> gen.wrap_element("dVerFor", "150")
            '<dVerFor>150</dVerFor>'
            >>> gen.wrap_element("DE", "contenido", {"Id": "CDC123"})
            '<DE Id="CDC123">contenido</DE>'
        """
        # Construir atributos si existen
        attr_str = ""
        if attrs:
            attr_parts = [f'{key}="{value}"' for key, value in attrs.items()]
            attr_str = " " + " ".join(attr_parts)

        return f"<{tag}{attr_str}>{content}</{tag}>"

    def add_namespace_attributes(self, root_element: Element) -> None:
        """
        Agrega los atributos de namespace SIFEN a un elemento raíz.

        Args:
            root_element: Elemento XML raíz al que agregar namespaces
        """
        for attr_name, attr_value in self.XML_NAMESPACES.items():
            root_element.set(attr_name, attr_value)

        # Agregar atributo version
        root_element.set("version", self.config.version)

    def generate_cdc(self, doc_type: str, doc_number: str) -> str:
        """
        Genera un CDC (Código de Control) de 44 caracteres según estructura SET.

        Estructura CDC: RUC(8) + DV(1) + TipoDoc(2) + Estab(3) + PuntoExp(3) + 
                       NumDoc(7) + TipoEmi(1) + Fecha(8) + TipoContrib(1) + 
                       CodSeg(9) + DV_CDC(1) = 44 caracteres

        Args:
            doc_type: Tipo de documento (01-07)
            doc_number: Número de documento

        Returns:
            str: CDC de 44 caracteres
        """
        # RUC base de prueba (8 dígitos)
        ruc_base = self.generate_random_digits(7)  # 7 dígitos + 1 DV
        dv_ruc = self.calculate_dv_ruc(ruc_base)
        ruc_completo = ruc_base + dv_ruc

        # Completar estructura CDC
        tipo_doc = doc_type.zfill(2)[:2]  # 2 caracteres
        establecimiento = self.generate_random_digits(3)  # 3 dígitos
        punto_expedicion = self.generate_random_digits(3)  # 3 dígitos
        numero_doc = str(doc_number).zfill(7)[:7]  # 7 dígitos
        tipo_emision = "1"  # 1 carácter (normal)
        fecha = datetime.now(self.PARAGUAY_TZ).strftime("%Y%m%d")  # 8 dígitos
        tipo_contribuyente = "1"  # 1 carácter
        codigo_seguridad = self.generate_random_digits(9)  # 9 dígitos

        # Construir CDC sin DV final
        cdc_sin_dv = (ruc_completo + tipo_doc + establecimiento +
                      punto_expedicion + numero_doc + tipo_emision +
                      fecha + tipo_contribuyente + codigo_seguridad)

        # Calcular DV del CDC (simplificado para testing)
        dv_cdc = str(sum(int(d) for d in cdc_sin_dv) % 10)

        return cdc_sin_dv + dv_cdc

    def generate_random_digits(self, length: int) -> str:
        """
        Genera una cadena de dígitos aleatorios de longitud específica.

        Args:
            length: Cantidad de dígitos a generar

        Returns:
            str: Cadena de dígitos aleatorios
        """
        return ''.join(self._random.choices(string.digits, k=length))

    def format_sifen_datetime(self, dt: Optional[datetime] = None) -> str:
        """
        Formatea fecha/hora según estándar SIFEN (zona horaria Paraguay).

        Args:
            dt: Fecha/hora a formatear. Si es None, usa fecha/hora actual.

        Returns:
            str: Fecha/hora formateada como YYYY-MM-DDTHH:MM:SS
        """
        if dt is None:
            dt = datetime.now(self.PARAGUAY_TZ)
        elif dt.tzinfo is None:
            # Si no tiene zona horaria, asumir Paraguay
            dt = dt.replace(tzinfo=self.PARAGUAY_TZ)

        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    def validate_ruc_format(self, ruc: str) -> bool:
        """
        Valida formato básico de RUC paraguayo.

        Args:
            ruc: RUC a validar (8-9 dígitos)

        Returns:
            bool: True si el formato es válido
        """
        # RUC debe tener 8-9 dígitos y ser numérico
        return ruc.isdigit() and 7 <= len(ruc) <= 9

    def calculate_dv_ruc(self, ruc: str) -> str:
        """
        Calcula dígito verificador de RUC usando algoritmo módulo 11 paraguayo.

        Args:
            ruc: RUC base (7-8 dígitos sin DV)

        Returns:
            str: Dígito verificador (0-9 o K)
        """
        # Implementación simplificada del algoritmo módulo 11
        if not ruc.isdigit():
            return "0"

        # Factores de multiplicación
        factores = [2, 3, 4, 5, 6, 7, 2, 3]
        ruc_padded = ruc.zfill(8)  # Completar a 8 dígitos

        # Calcular suma ponderada
        suma = sum(int(digit) * factor for digit, factor
                   in zip(reversed(ruc_padded), factores))

        # Calcular dígito verificador
        resto = suma % 11
        dv = 11 - resto

        if dv == 10:
            return "K"
        elif dv == 11:
            return "0"
        else:
            return str(dv)
