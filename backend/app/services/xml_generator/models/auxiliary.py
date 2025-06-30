"""
Modelos auxiliares específicos para documentos SIFEN v150

Este módulo contiene modelos auxiliares especializados que se usan
en tipos específicos de documentos electrónicos:

- DocumentoAsociado: Para NCE/NDE (referencias a documentos originales)
- ContribuyenteExtranjero: Para AFE (vendedor extranjero)
- DatosAFE: Para AFE (sección específica autofactura)
- DatosTransporte: Para NRE (información de transporte)
- DatosVehiculo: Para NRE (vehículos de transporte)

Arquitectura Modular:
- base.py: Modelos reutilizables (Contribuyente, ItemFactura)
- auxiliary.py: Modelos auxiliares específicos (ESTE ARCHIVO)
- document_types.py: Documentos principales por tipo  
- validators.py: Validadores customizados

Autor: Sistema SIFEN Paraguay - Módulo XML Generator
Fecha: Junio 2025
Versión: 1.0.0
Manual: SIFEN v150 - SET Paraguay
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import re

# Imports de modelos base
from .base import validate_ruc_paraguayo, validate_cdc_format, validate_email_format


# ===============================================
# CONSTANTES ESPECÍFICAS AUXILIARES
# ===============================================

# Tipos de documento válidos para referencias
TIPOS_DOCUMENTO_REF_VALIDOS = ["1", "4", "5", "6", "7"]

# Naturaleza de vendedor AFE
NATURALEZA_VENDEDOR_AFE = {
    "1": "NO_CONTRIBUYENTE",
    "2": "EXTRANJERO"
}

# Tipos de operación AFE
TIPOS_OPERACION_AFE = {
    "1": "IMPORTACION",
    "2": "NO_CONTRIBUYENTE"
}

# Tipos de vehículo para transporte
TIPOS_VEHICULO = {
    "1": "AUTOMÓVIL",
    "2": "CAMIÓN",
    "3": "MOTOCICLETA",
    "4": "EMBARCACIÓN",
    "5": "AERONAVE"
}

# Tipos de transporte
TIPOS_TRANSPORTE = {
    "1": "TERRESTRE",
    "2": "AÉREO",
    "3": "ACUÁTICO"
}

# Responsables de transporte
RESPONSABLES_TRANSPORTE = {
    "1": "EMISOR",
    "2": "RECEPTOR",
    "3": "TERCERO"
}

# Modalidades de transporte
MODALIDADES_TRANSPORTE = {
    "1": "PROPIO",
    "2": "TERCERIZADO"
}


# ===============================================
# MODELOS AUXILIARES PARA NCE/NDE
# ===============================================

class DocumentoAsociado(BaseModel):
    """
    Referencias a documentos originales para NCE/NDE

    Usado en:
    - NotaCreditoElectronica: Referencia al documento que se está devolviendo
    - NotaDebitoElectronica: Referencia al documento al que se le agregan cargos

    Validaciones incluidas:
    - Tipo documento válido (1,4,5,6,7)
    - CDC 44 dígitos si se proporciona
    - Fecha no futura
    - Número documento formato correcto

    Características:
    - CDC opcional pero recomendado
    - Fecha obligatoria para validar vigencia
    - Número timbrado para verificación adicional
    """

    # === IDENTIFICACIÓN DOCUMENTO ORIGINAL ===
    tipo_documento_ref: str = Field(
        ...,
        pattern="^[1-7]$",
        description="Tipo documento original (1=FE, 4=AFE, 5=NCE, 6=NDE, 7=NRE)"
    )

    numero_documento_ref: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Número del documento original (ej: 001-001-0000123)"
    )

    fecha_documento_ref: datetime = Field(
        ...,
        description="Fecha de emisión del documento original"
    )

    # === CÓDIGOS DE CONTROL ===
    cdc_ref: Optional[str] = Field(
        None,
        min_length=44,
        max_length=44,
        description="CDC del documento original (44 dígitos)"
    )

    numero_timbrado_ref: Optional[str] = Field(
        None,
        min_length=8,
        max_length=8,
        description="Número de timbrado del documento original"
    )

    # === INFORMACIÓN ADICIONAL ===
    monto_original: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Monto total del documento original (para validación)"
    )

    # === VALIDADORES ===

    @field_validator('tipo_documento_ref')
    @classmethod
    def validate_tipo_documento_ref(cls, v: str) -> str:
        """Valida tipo de documento de referencia"""
        if v not in TIPOS_DOCUMENTO_REF_VALIDOS:
            raise ValueError(
                f'Tipo documento debe ser uno de: {TIPOS_DOCUMENTO_REF_VALIDOS}')
        return v

    @field_validator('numero_documento_ref')
    @classmethod
    def validate_numero_documento_ref(cls, v: str) -> str:
        """Valida formato número de documento"""
        # Formato típico: 001-001-0000123
        if not re.match(r'^\d{3}-\d{3}-\d{7}$', v):
            # Permitir también formatos alternativos
            if not re.match(r'^[A-Z0-9\-]{1,50}$', v):
                raise ValueError('Formato de número documento inválido')
        return v.upper()

    @field_validator('fecha_documento_ref')
    @classmethod
    def validate_fecha_documento_ref(cls, v: datetime) -> datetime:
        """Valida fecha del documento de referencia"""
        # No puede ser futura
        if v > datetime.now():
            raise ValueError(
                'Fecha del documento original no puede ser futura')

        # No puede ser muy antigua (más de 10 años)
        limite_antiguo = datetime.now().replace(year=datetime.now().year - 10)
        if v < limite_antiguo:
            raise ValueError(
                'Fecha del documento original muy antigua (>10 años)')

        return v

    @field_validator('cdc_ref')
    @classmethod
    def validate_cdc_ref(cls, v: Optional[str]) -> Optional[str]:
        """Valida formato CDC de referencia"""
        if v is None:
            return v
        return validate_cdc_format(v)

    @field_validator('numero_timbrado_ref')
    @classmethod
    def validate_numero_timbrado_ref(cls, v: Optional[str]) -> Optional[str]:
        """Valida número de timbrado"""
        if v is None:
            return v

        if not re.match(r'^\d{8}$', v):
            raise ValueError('Número timbrado debe tener 8 dígitos')
        return v

    # === PROPERTIES ===

    @property
    def descripcion_tipo_documento(self) -> str:
        """Retorna descripción del tipo de documento"""
        tipos = {
            "1": "Factura Electrónica",
            "4": "Autofactura Electrónica",
            "5": "Nota de Crédito Electrónica",
            "6": "Nota de Débito Electrónica",
            "7": "Nota de Remisión Electrónica"
        }
        return tipos.get(self.tipo_documento_ref, "Tipo Desconocido")


# ===============================================
# MODELOS AUXILIARES PARA AFE (AUTOFACTURA)
# ===============================================

class ContribuyenteExtranjero(BaseModel):
    """
    Datos de vendedor extranjero o no contribuyente para AFE

    Usado en:
    - AutofacturaElectronica: Datos del vendedor real en importaciones

    Validaciones incluidas:
    - Naturaleza vendedor (1=No contribuyente, 2=Extranjero)
    - Tipo documento según naturaleza
    - País ISO cuando es extranjero
    - Formato dirección internacional

    Casos de uso:
    - Importaciones: vendedor extranjero con país
    - Compras locales: no contribuyente sin país
    """

    # === NATURALEZA DEL VENDEDOR ===
    naturaleza_vendedor: str = Field(
        ...,
        pattern="^[1-2]$",
        description="1=No contribuyente nacional, 2=Extranjero"
    )

    # === IDENTIFICACIÓN VENDEDOR ===
    tipo_documento_vendedor: str = Field(
        ...,
        pattern="^[1-9]$",
        description="Tipo documento: 1=Cédula, 2=Pasaporte, 3=RUC extranjero, etc."
    )

    numero_documento_vendedor: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Número del documento de identificación"
    )

    nombre_vendedor: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nombre completo o razón social del vendedor"
    )

    # === UBICACIÓN VENDEDOR ===
    direccion_vendedor: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Dirección completa del vendedor"
    )

    pais_vendedor: Optional[str] = Field(
        None,
        min_length=2,
        max_length=3,
        description="Código ISO del país (requerido para extranjeros)"
    )

    # === CONTACTO VENDEDOR ===
    telefono_vendedor: Optional[str] = Field(
        None,
        max_length=20,
        description="Teléfono del vendedor"
    )

    email_vendedor: Optional[str] = Field(
        None,
        max_length=100,
        description="Email del vendedor"
    )

    # === VALIDADORES ===

    @field_validator('naturaleza_vendedor')
    @classmethod
    def validate_naturaleza_vendedor(cls, v: str) -> str:
        """Valida naturaleza del vendedor"""
        if v not in NATURALEZA_VENDEDOR_AFE:
            raise ValueError(
                f'Naturaleza vendedor debe ser: {list(NATURALEZA_VENDEDOR_AFE.keys())}')
        return v

    @field_validator('nombre_vendedor')
    @classmethod
    def validate_nombre_vendedor(cls, v: str) -> str:
        """Normaliza nombre del vendedor"""
        return v.upper().strip()

    @field_validator('pais_vendedor')
    @classmethod
    def validate_pais_vendedor(cls, v: Optional[str], info) -> Optional[str]:
        """Valida país del vendedor"""
        if v is None:
            return v

        # Validar formato ISO
        if len(v) not in [2, 3]:
            raise ValueError('Código país debe ser ISO 2 o 3 caracteres')

        # Si es extranjero (naturaleza=2), país es obligatorio
        if 'naturaleza_vendedor' in info.data and info.data['naturaleza_vendedor'] == "2":
            if not v:
                raise ValueError('País requerido para vendedor extranjero')

        return v.upper()

    @field_validator('email_vendedor')
    @classmethod
    def validate_email_vendedor(cls, v: Optional[str]) -> Optional[str]:
        """Valida email del vendedor"""
        if v is None:
            return v
        return validate_email_format(v)

    # === PROPERTIES ===

    @property
    def descripcion_naturaleza(self) -> str:
        """Retorna descripción de la naturaleza"""
        return NATURALEZA_VENDEDOR_AFE.get(self.naturaleza_vendedor, "Desconocido")

    @property
    def es_extranjero(self) -> bool:
        """Retorna True si es vendedor extranjero"""
        return self.naturaleza_vendedor == "2"


class DatosAFE(BaseModel):
    """
    Datos específicos de la sección AFE (Autofactura)

    Usado en:
    - AutofacturaElectronica: Sección gCamAE obligatoria

    Validaciones incluidas:
    - Tipo operación válido (1=Importación, 2=No contribuyente)
    - Consistencia naturaleza vendedor vs tipo operación
    - Moneda extranjera y tipo cambio cuando aplica
    - Datos vendedor completos

    Características:
    - Operación importación requiere moneda extranjera
    - No contribuyente solo acepta PYG
    - Validaciones cruzadas entre campos
    """

    # === TIPO DE OPERACIÓN AFE ===
    tipo_operacion_afe: str = Field(
        ...,
        pattern="^[1-2]$",
        description="1=Importación, 2=Compra a no contribuyente"
    )

    # === DATOS DEL VENDEDOR ===
    vendedor: ContribuyenteExtranjero = Field(
        ...,
        description="Datos completos del vendedor"
    )

    # === MONEDA Y CAMBIO ===
    moneda_extranjera: Optional[str] = Field(
        None,
        pattern="^(USD|EUR|BRL|ARS|CLP|BOB)$",
        description="Moneda extranjera para importaciones"
    )

    tipo_cambio_extranjero: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Tipo de cambio a guaraníes"
    )

    # === INFORMACIÓN ADICIONAL ===
    observaciones_afe: Optional[str] = Field(
        None,
        max_length=500,
        description="Observaciones específicas de la AFE"
    )

    # === VALIDADORES ===

    @field_validator('tipo_operacion_afe')
    @classmethod
    def validate_tipo_operacion_afe(cls, v: str) -> str:
        """Valida tipo de operación AFE"""
        if v not in TIPOS_OPERACION_AFE:
            raise ValueError(
                f'Tipo operación AFE debe ser: {list(TIPOS_OPERACION_AFE.keys())}')
        return v

    @field_validator('vendedor')
    @classmethod
    def validate_vendedor_consistency(cls, v: ContribuyenteExtranjero, info) -> ContribuyenteExtranjero:
        """Valida consistencia entre tipo operación y vendedor"""
        if 'tipo_operacion_afe' in info.data:
            tipo_operacion = info.data['tipo_operacion_afe']

            # Importación (1) debe tener vendedor extranjero (2)
            if tipo_operacion == "1" and v.naturaleza_vendedor != "2":
                raise ValueError('Importación requiere vendedor extranjero')

            # No contribuyente (2) debe tener vendedor no contribuyente (1)
            if tipo_operacion == "2" and v.naturaleza_vendedor != "1":
                raise ValueError(
                    'Operación no contribuyente requiere vendedor no contribuyente')

        return v

    @field_validator('tipo_cambio_extranjero')
    @classmethod
    def validate_tipo_cambio_extranjero(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Valida tipo de cambio para moneda extranjera"""
        if 'moneda_extranjera' in info.data and info.data['moneda_extranjera']:
            if not v:
                raise ValueError(
                    'Tipo cambio requerido para moneda extranjera')
            if v <= 0:
                raise ValueError('Tipo cambio debe ser mayor a 0')

        return v

    # === PROPERTIES ===

    @property
    def descripcion_tipo_operacion(self) -> str:
        """Retorna descripción del tipo de operación"""
        return TIPOS_OPERACION_AFE.get(self.tipo_operacion_afe, "Desconocido")

    @property
    def requiere_moneda_extranjera(self) -> bool:
        """Retorna True si requiere moneda extranjera"""
        return self.tipo_operacion_afe == "1"  # Importación


# ===============================================
# MODELOS AUXILIARES PARA NRE (NOTA REMISIÓN)
# ===============================================

class DatosVehiculo(BaseModel):
    """
    Datos de vehículo para transporte en NRE

    Usado en:
    - NotaRemisionElectronica: Vehículos que realizan el transporte

    Validaciones incluidas:
    - Tipo vehículo válido (1-5)
    - Chapa formato paraguayo
    - SENACSA para alimentos cuando aplica
    - Datos conductor cuando se requiere

    Características:
    - SENACSA opcional pero recomendado para alimentos
    - Conductor requerido para ciertos tipos transporte
    - Validaciones específicas por tipo vehículo
    """

    # === IDENTIFICACIÓN VEHÍCULO ===
    tipo_vehiculo: str = Field(
        ...,
        pattern="^[1-5]$",
        description="1=Auto, 2=Camión, 3=Moto, 4=Embarcación, 5=Aeronave"
    )

    marca: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Marca del vehículo"
    )

    numero_chapa: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Número de chapa/matrícula"
    )

    # === PERMISOS Y REGISTROS ===
    numero_senacsa: Optional[str] = Field(
        None,
        min_length=1,
        max_length=20,
        description="Número registro SENACSA (para transporte alimentos)"
    )

    # === DATOS CONDUCTOR ===
    conductor_nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Nombre completo del conductor"
    )

    conductor_documento: Optional[str] = Field(
        None,
        min_length=1,
        max_length=15,
        description="Documento del conductor (cédula/licencia)"
    )

    conductor_telefono: Optional[str] = Field(
        None,
        max_length=20,
        description="Teléfono del conductor"
    )

    # === VALIDADORES ===

    @field_validator('tipo_vehiculo')
    @classmethod
    def validate_tipo_vehiculo(cls, v: str) -> str:
        """Valida tipo de vehículo"""
        if v not in TIPOS_VEHICULO:
            raise ValueError(
                f'Tipo vehículo debe ser: {list(TIPOS_VEHICULO.keys())}')
        return v

    @field_validator('marca')
    @classmethod
    def validate_marca(cls, v: str) -> str:
        """Normaliza marca del vehículo"""
        return v.upper().strip()

    @field_validator('numero_chapa')
    @classmethod
    def validate_numero_chapa(cls, v: str) -> str:
        """Valida formato chapa paraguaya"""
        # Formato típico paraguayo: ABC123 o ABC1234
        clean_chapa = v.upper().replace('-', '').replace(' ', '')
        if not re.match(r'^[A-Z]{2,3}\d{3,4}$', clean_chapa):
            # Permitir otros formatos internacionales
            if not re.match(r'^[A-Z0-9\-]{1,10}$', clean_chapa):
                raise ValueError('Formato de chapa inválido')
        return clean_chapa

    @field_validator('conductor_nombre')
    @classmethod
    def validate_conductor_nombre(cls, v: Optional[str]) -> Optional[str]:
        """Normaliza nombre del conductor"""
        if v is None:
            return v
        return v.upper().strip()

    # === PROPERTIES ===

    @property
    def descripcion_tipo_vehiculo(self) -> str:
        """Retorna descripción del tipo de vehículo"""
        return TIPOS_VEHICULO.get(self.tipo_vehiculo, "Desconocido")

    @property
    def requiere_senacsa(self) -> bool:
        """Retorna True si típicamente requiere SENACSA"""
        # Camiones típicamente transportan alimentos
        return self.tipo_vehiculo == "2"


class DatosTransporte(BaseModel):
    """
    Datos de transporte para Nota de Remisión

    Usado en:
    - NotaRemisionElectronica: Información completa del transporte

    Validaciones incluidas:
    - Responsable transporte válido (1-3)
    - Modalidad y tipo transporte coherentes
    - Fechas lógicas (inicio no pasado)
    - Direcciones completas
    - Al menos un vehículo

    Características:
    - Múltiples vehículos permitidos
    - Validaciones de fecha inicio traslado
    - Direcciones origen y destino obligatorias
    """

    # === RESPONSABILIDAD TRANSPORTE ===
    tipo_responsable: str = Field(
        ...,
        pattern="^[1-3]$",
        description="1=Emisor, 2=Receptor, 3=Tercero"
    )

    modalidad_transporte: str = Field(
        ...,
        pattern="^[1-2]$",
        description="1=Propio, 2=Tercerizado"
    )

    tipo_transporte: str = Field(
        ...,
        pattern="^[1-3]$",
        description="1=Terrestre, 2=Aéreo, 3=Acuático"
    )

    # === FECHAS Y TIEMPOS ===
    fecha_inicio_traslado: datetime = Field(
        ...,
        description="Fecha y hora de inicio del traslado"
    )

    fecha_fin_estimada: Optional[datetime] = Field(
        None,
        description="Fecha estimada de finalización"
    )

    # === DIRECCIONES ===
    direccion_salida: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Dirección completa de origen"
    )

    direccion_llegada: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Dirección completa de destino"
    )

    # === VEHÍCULOS ===
    vehiculos: List[DatosVehiculo] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Lista de vehículos (mínimo 1, máximo 10)"
    )

    # === INFORMACIÓN ADICIONAL ===
    observaciones_transporte: Optional[str] = Field(
        None,
        max_length=500,
        description="Observaciones del transporte"
    )

    # === VALIDADORES ===

    @field_validator('tipo_responsable')
    @classmethod
    def validate_tipo_responsable(cls, v: str) -> str:
        """Valida responsable del transporte"""
        if v not in RESPONSABLES_TRANSPORTE:
            raise ValueError(
                f'Responsable debe ser: {list(RESPONSABLES_TRANSPORTE.keys())}')
        return v

    @field_validator('modalidad_transporte')
    @classmethod
    def validate_modalidad_transporte(cls, v: str) -> str:
        """Valida modalidad del transporte"""
        if v not in MODALIDADES_TRANSPORTE:
            raise ValueError(
                f'Modalidad debe ser: {list(MODALIDADES_TRANSPORTE.keys())}')
        return v

    @field_validator('tipo_transporte')
    @classmethod
    def validate_tipo_transporte(cls, v: str) -> str:
        """Valida tipo de transporte"""
        if v not in TIPOS_TRANSPORTE:
            raise ValueError(
                f'Tipo transporte debe ser: {list(TIPOS_TRANSPORTE.keys())}')
        return v

    @field_validator('fecha_inicio_traslado')
    @classmethod
    def validate_fecha_inicio_traslado(cls, v: datetime) -> datetime:
        """Valida fecha de inicio del traslado"""
        # No puede ser más de 1 día en el pasado
        limite_pasado = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0)
        if v < limite_pasado:
            raise ValueError(
                'Fecha inicio traslado no puede ser pasada (máximo hoy)')

        # No puede ser más de 30 días en el futuro
        limite_futuro = datetime.now().replace(day=datetime.now().day + 30)
        if v > limite_futuro:
            raise ValueError(
                'Fecha inicio traslado muy lejana (máximo 30 días)')

        return v

    @field_validator('fecha_fin_estimada')
    @classmethod
    def validate_fecha_fin_estimada(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Valida fecha fin estimada"""
        if v is None:
            return v

        if 'fecha_inicio_traslado' in info.data:
            if v <= info.data['fecha_inicio_traslado']:
                raise ValueError('Fecha fin debe ser posterior a fecha inicio')

        return v

    @field_validator('direccion_salida')
    @classmethod
    def validate_direccion_salida(cls, v: str) -> str:
        """Normaliza dirección de salida"""
        return v.upper().strip()

    @field_validator('direccion_llegada')
    @classmethod
    def validate_direccion_llegada(cls, v: str) -> str:
        """Normaliza dirección de llegada"""
        return v.upper().strip()

    # === PROPERTIES ===

    @property
    def descripcion_responsable(self) -> str:
        """Retorna descripción del responsable"""
        return RESPONSABLES_TRANSPORTE.get(self.tipo_responsable, "Desconocido")

    @property
    def descripcion_modalidad(self) -> str:
        """Retorna descripción de la modalidad"""
        return MODALIDADES_TRANSPORTE.get(self.modalidad_transporte, "Desconocido")

    @property
    def descripcion_tipo_transporte(self) -> str:
        """Retorna descripción del tipo de transporte"""
        return TIPOS_TRANSPORTE.get(self.tipo_transporte, "Desconocido")

    @property
    def total_vehiculos(self) -> int:
        """Retorna número total de vehículos"""
        return len(self.vehiculos)

    @property
    def duracion_estimada_horas(self) -> Optional[float]:
        """Retorna duración estimada en horas"""
        if self.fecha_fin_estimada:
            delta = self.fecha_fin_estimada - self.fecha_inicio_traslado
            return delta.total_seconds() / 3600
        return None


# ===============================================
# FUNCIONES HELPER PARA EJEMPLOS
# ===============================================

def create_documento_asociado_ejemplo() -> DocumentoAsociado:
    """Crea documento asociado de ejemplo para testing"""
    return DocumentoAsociado(
        tipo_documento_ref="1",  # Factura Electrónica
        numero_documento_ref="001-001-0000123",
        fecha_documento_ref=datetime(2024, 6, 15, 14, 30, 0),
        cdc_ref="01234567890123456789012345678901234567890123",
        numero_timbrado_ref="12345678",
        monto_original=Decimal("1500000.00")
    )


def create_contribuyente_extranjero_ejemplo() -> ContribuyenteExtranjero:
    """Crea contribuyente extranjero de ejemplo para testing"""
    return ContribuyenteExtranjero(
        naturaleza_vendedor="2",  # Extranjero
        tipo_documento_vendedor="2",  # Pasaporte
        numero_documento_vendedor="A12345678",
        nombre_vendedor="EMPRESA INTERNACIONAL LLC",
        direccion_vendedor="123 MAIN STREET, MIAMI, FL 33101",
        pais_vendedor="US",
        telefono_vendedor="+1-305-555-0123",
        email_vendedor="ventas@empresaintl.com"
    )


def create_datos_afe_ejemplo() -> DatosAFE:
    """Crea datos AFE de ejemplo para testing"""
    return DatosAFE(
        tipo_operacion_afe="1",  # Importación
        vendedor=create_contribuyente_extranjero_ejemplo(),
        moneda_extranjera="USD",
        tipo_cambio_extranjero=Decimal("7350.00"),
        observaciones_afe="IMPORTACIÓN DE EQUIPOS ELECTRÓNICOS"
    )


def create_vehiculo_ejemplo() -> DatosVehiculo:
    """Crea vehículo de ejemplo para testing"""
    return DatosVehiculo(
        tipo_vehiculo="2",  # Camión
        marca="VOLVO",
        numero_chapa="ABC123",
        numero_senacsa="SEN123456",
        conductor_nombre="JUAN PÉREZ CHOFER",
        conductor_documento="12345678",
        conductor_telefono="0981123456"
    )


def create_datos_transporte_ejemplo() -> DatosTransporte:
    """Crea datos transporte de ejemplo para testing"""
    return DatosTransporte(
        tipo_responsable="1",  # Emisor
        modalidad_transporte="1",  # Propio
        tipo_transporte="1",  # Terrestre
        fecha_inicio_traslado=datetime.now().replace(
            hour=8, minute=0, second=0, microsecond=0),
        fecha_fin_estimada=datetime.now().replace(
            hour=16, minute=0, second=0, microsecond=0),
        direccion_salida="DEPÓSITO CENTRAL - AV. PRINCIPAL 123, ASUNCIÓN",
        direccion_llegada="CLIENTE DESTINO - AV. ESPAÑA 456, SAN LORENZO",
        vehiculos=[create_vehiculo_ejemplo()],
        observaciones_transporte="TRASLADO DE MERCADERÍA GENERAL"
    )


# ===============================================
# FUNCIONES FACTORY PARA DIFERENTES CASOS
# ===============================================

def create_documento_asociado_factura() -> DocumentoAsociado:
    """Documento asociado para NCE/NDE basado en factura"""
    return DocumentoAsociado(
        tipo_documento_ref="1",
        numero_documento_ref="001-001-0000500",
        fecha_documento_ref=datetime.now().replace(day=datetime.now().day - 5),
        cdc_ref="01234567890123456789012345678901234567890500",
        numero_timbrado_ref="87654321",
        monto_original=Decimal("2500000.00")
    )


def create_contribuyente_no_contribuyente() -> ContribuyenteExtranjero:
    """Contribuyente no contribuyente nacional para AFE"""
    return ContribuyenteExtranjero(
        naturaleza_vendedor="1",  # No contribuyente
        tipo_documento_vendedor="1",  # Cédula
        numero_documento_vendedor="1234567",
        nombre_vendedor="JUAN ARTESANO INDEPENDIENTE",
        direccion_vendedor="BARRIO SAN PABLO, CASA 123, ASUNCIÓN",
        pais_vendedor=None,  # Nacional, no requiere país
        telefono_vendedor="0981234567",
        email_vendedor=None
    )


def create_datos_afe_no_contribuyente() -> DatosAFE:
    """Datos AFE para compra a no contribuyente"""
    return DatosAFE(
        tipo_operacion_afe="2",  # No contribuyente
        vendedor=create_contribuyente_no_contribuyente(),
        moneda_extranjera=None,  # Solo PYG para no contribuyentes
        tipo_cambio_extranjero=None,
        observaciones_afe="COMPRA A ARTESANO LOCAL"
    )


def create_vehiculo_motocicleta() -> DatosVehiculo:
    """Vehículo motocicleta para transporte liviano"""
    return DatosVehiculo(
        tipo_vehiculo="3",  # Motocicleta
        marca="HONDA",
        numero_chapa="XYZ789",
        numero_senacsa=None,  # No requerido para moto
        conductor_nombre="CARLOS DELIVERY",
        conductor_documento="98765432",
        conductor_telefono="0987654321"
    )


def create_datos_transporte_tercerizado() -> DatosTransporte:
    """Datos transporte tercerizado con múltiples vehículos"""
    fecha_inicio = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
    fecha_fin = fecha_inicio.replace(hour=18, minute=0)  # 12 horas después

    return DatosTransporte(
        tipo_responsable="3",  # Tercero
        modalidad_transporte="2",  # Tercerizado
        tipo_transporte="1",  # Terrestre
        fecha_inicio_traslado=fecha_inicio,
        fecha_fin_estimada=fecha_fin,
        direccion_salida="FÁBRICA ORIGEN - RUTA 2 KM 25, CAPIATÁ",
        direccion_llegada="DISTRIBUIDOR - AV. EUSEBIO AYALA 2500, ASUNCIÓN",
        vehiculos=[
            create_vehiculo_ejemplo(),  # Camión principal
            create_vehiculo_motocicleta()  # Vehículo acompañante
        ],
        observaciones_transporte="TRANSPORTE ESPECIALIZADO CON ESCOLTA"
    )


# ===============================================
# VALIDATORS HELPERS ESPECÍFICOS
# ===============================================

def validate_documento_asociado_coherencia(
    doc_asociado: DocumentoAsociado,
    tipo_documento_actual: str
) -> bool:
    """
    Valida coherencia entre documento asociado y documento actual

    Args:
        doc_asociado: Documento asociado a validar
        tipo_documento_actual: Tipo del documento actual (5=NCE, 6=NDE)

    Returns:
        bool: True si es coherente

    Raises:
        ValueError: Si hay incoherencia
    """
    # NCE solo puede referenciar FE, AFE o NDE
    if tipo_documento_actual == "5":  # NCE
        if doc_asociado.tipo_documento_ref not in ["1", "4", "6"]:
            raise ValueError(
                "NCE solo puede referenciar Factura (1), Autofactura (4) o Nota Débito (6)")

    # NDE solo puede referenciar FE, AFE o NCE
    if tipo_documento_actual == "6":  # NDE
        if doc_asociado.tipo_documento_ref not in ["1", "4", "5"]:
            raise ValueError(
                "NDE solo puede referenciar Factura (1), Autofactura (4) o Nota Crédito (5)")

    return True


def validate_afe_business_rules(datos_afe: DatosAFE) -> bool:
    """
    Valida reglas de negocio específicas para AFE

    Args:
        datos_afe: Datos AFE a validar

    Returns:
        bool: True si cumple reglas de negocio

    Raises:
        ValueError: Si viola reglas de negocio
    """
    # Importación debe tener moneda extranjera
    if datos_afe.tipo_operacion_afe == "1":  # Importación
        if not datos_afe.moneda_extranjera:
            raise ValueError(
                "Importación requiere especificar moneda extranjera")
        if not datos_afe.tipo_cambio_extranjero:
            raise ValueError("Importación requiere tipo de cambio")
        if not datos_afe.vendedor.pais_vendedor:
            raise ValueError("Importación requiere país del vendedor")

    # No contribuyente no debe tener moneda extranjera
    if datos_afe.tipo_operacion_afe == "2":  # No contribuyente
        if datos_afe.moneda_extranjera:
            raise ValueError("Compra a no contribuyente debe ser en guaraníes")
        if datos_afe.vendedor.pais_vendedor:
            raise ValueError("No contribuyente debe ser nacional")

    return True


def validate_transporte_business_rules(datos_transporte: DatosTransporte) -> bool:
    """
    Valida reglas de negocio para transporte

    Args:
        datos_transporte: Datos transporte a validar

    Returns:
        bool: True si cumple reglas de negocio

    Raises:
        ValueError: Si viola reglas de negocio
    """
    # Transporte aéreo/acuático requiere información especial
    if datos_transporte.tipo_transporte in ["2", "3"]:  # Aéreo/Acuático
        for vehiculo in datos_transporte.vehiculos:
            if datos_transporte.tipo_transporte == "2" and vehiculo.tipo_vehiculo != "5":
                raise ValueError("Transporte aéreo requiere aeronave")
            if datos_transporte.tipo_transporte == "3" and vehiculo.tipo_vehiculo != "4":
                raise ValueError("Transporte acuático requiere embarcación")

    # Tercerizado requiere datos conductor
    if datos_transporte.modalidad_transporte == "2":  # Tercerizado
        for vehiculo in datos_transporte.vehiculos:
            if not vehiculo.conductor_nombre:
                raise ValueError(
                    "Transporte tercerizado requiere datos del conductor")

    return True


# ===============================================
# EXPORTS - Según Plan de Modularización
# ===============================================

__all__ = [
    # === MODELOS AUXILIARES PRINCIPALES ===
    "DocumentoAsociado",
    "ContribuyenteExtranjero",
    "DatosAFE",
    "DatosVehiculo",
    "DatosTransporte",

    # === CONSTANTES ESPECÍFICAS ===
    "TIPOS_DOCUMENTO_REF_VALIDOS",
    "NATURALEZA_VENDEDOR_AFE",
    "TIPOS_OPERACION_AFE",
    "TIPOS_VEHICULO",
    "TIPOS_TRANSPORTE",
    "RESPONSABLES_TRANSPORTE",
    "MODALIDADES_TRANSPORTE",

    # === HELPERS PARA TESTING ===
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

    # === VALIDATORS BUSINESS RULES ===
    "validate_documento_asociado_coherencia",
    "validate_afe_business_rules",
    "validate_transporte_business_rules"
]

# Información del módulo para __init__.py
MODULE_INFO = {
    "name": "auxiliary",
    "description": "Modelos auxiliares específicos por tipo documento",
    "version": "1.0.0",
    "models": ["DocumentoAsociado", "ContribuyenteExtranjero", "DatosAFE", "DatosVehiculo", "DatosTransporte"],
    "constants": 7,
    "helpers": 10,
    "validators": 3,
    "use_cases": {
        "DocumentoAsociado": ["NCE", "NDE"],
        "ContribuyenteExtranjero": ["AFE"],
        "DatosAFE": ["AFE"],
        "DatosVehiculo": ["NRE"],
        "DatosTransporte": ["NRE"]
    }
}
