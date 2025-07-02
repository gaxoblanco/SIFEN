# ===============================================
# ARCHIVO: backend/app/schemas/cliente.py
# PROPÓSITO: DTOs para clientes/receptores de documentos SIFEN
# PRIORIDAD: 🟡 CRÍTICO - Receptores de documentos electrónicos
# ===============================================

"""
Esquemas Pydantic para gestión de clientes/receptores.

Este módulo define DTOs para:
- Registro de clientes/receptores de documentos
- Validación de documentos Paraguay (RUC, CI, Pasaporte)
- Clasificación de tipos de cliente
- Integración como receptor en documentos SIFEN

Integra con:
- models/cliente.py (SQLAlchemy)
- services/xml_generator (receptor XML)
- api/v1/clientes.py (endpoints CRUD)

Regulaciones Paraguay:
- RUC con dígito verificador (contribuyentes)
- Cédula de identidad paraguaya
- Pasaportes extranjeros
- Clasificación fiscal según SET
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator
import re
from .common import DepartamentoParaguayEnum


# ===============================================
# ENUMS PARAGUAY
# ===============================================

class TipoClienteEnum(str, Enum):
    """Tipos de clientes según normativa fiscal Paraguay"""
    PERSONA_FISICA = "persona_fisica"
    PERSONA_JURIDICA = "persona_juridica"
    EXTRANJERO = "extranjero"
    EXENTO = "exento"


class TipoDocumentoEnum(str, Enum):
    """Tipos de documentos de identidad válidos en Paraguay"""
    RUC = "ruc"                    # RUC paraguayo (contribuyente)
    CI = "cedula_identidad"        # Cédula de identidad paraguaya
    PASAPORTE = "pasaporte"        # Pasaporte extranjero
    OTROS = "otros"                # Otros documentos


# ===============================================
# DTOs DE ENTRADA (REQUEST)
# ===============================================

class ClienteCreateDTO(BaseModel):
    """
    DTO para registro de nuevos clientes/receptores.

    Valida datos requeridos para clientes receptores de documentos
    electrónicos SIFEN según normativa paraguaya.

    Examples:
        ```python
        # POST /api/v1/clientes
        cliente_data = ClienteCreateDTO(
            tipo_cliente="persona_juridica",
            tipo_documento="ruc",
            numero_documento="80087654-3",
            razon_social="CLIENTE EJEMPLO S.R.L.",
            direccion="Av. España 567",
            ciudad="San Lorenzo",
            departamento="11",
            telefono="021-555456",
            email="compras@cliente.com.py"
        )
        ```
    """

    # === CLASIFICACIÓN OBLIGATORIA ===
    tipo_cliente: TipoClienteEnum = Field(
        ...,
        description="Tipo de cliente según normativa fiscal"
    )

    tipo_documento: TipoDocumentoEnum = Field(
        ...,
        description="Tipo de documento de identidad"
    )

    numero_documento: str = Field(
        ...,
        min_length=7,   # ✅ CI mínimo 7 dígitos
        max_length=15,  # ✅ Pasaporte máximo ~10, RUC 10
        description="Número de documento (RUC, CI, Pasaporte, etc.)"
    )

    # === INFORMACIÓN PERSONAL/EMPRESARIAL ===
    # Para personas jurídicas
    razon_social: Optional[str] = Field(
        None,
        max_length=200,
        description="Razón social (para personas jurídicas)"
    )

    # Para personas físicas
    nombres: Optional[str] = Field(
        None,
        max_length=100,
        description="Nombres (para personas físicas)"
    )

    apellidos: Optional[str] = Field(
        None,
        max_length=100,
        description="Apellidos (para personas físicas)"
    )

    nombre_fantasia: Optional[str] = Field(
        None,
        max_length=200,
        description="Nombre comercial o fantasía"
    )

    # === LOCALIZACIÓN ===
    direccion: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Dirección completa del cliente"
    )

    ciudad: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Ciudad de residencia/ubicación"
    )

    departamento: DepartamentoParaguayEnum = Field(
        ...,
        description="Departamento Paraguay (01-17)"
    )

    codigo_postal: Optional[str] = Field(
        None,
        max_length=10,
        description="Código postal"
    )

    pais: str = Field(
        default="PRY",
        min_length=3,
        max_length=3,
        description="Código país ISO (PRY para Paraguay)"
    )

    # === CONTACTO ===
    telefono: str = Field(
        ...,
        min_length=7,
        max_length=20,
        description="Teléfono principal"
    )

    celular: Optional[str] = Field(
        None,
        max_length=20,
        description="Teléfono celular"
    )

    email: Optional[EmailStr] = Field(
        None,
        description="Email para envío de documentos electrónicos"
    )

    # === INFORMACIÓN FISCAL ===
    contribuyente: bool = Field(
        default=False,
        description="Si es contribuyente registrado en SET"
    )

    exento_iva: bool = Field(
        default=False,
        description="Si está exento de IVA"
    )

    # === INFORMACIÓN ADICIONAL ===
    observaciones: Optional[str] = Field(
        None,
        max_length=1000,
        description="Observaciones adicionales del cliente"
    )

    @validator('numero_documento')
    def validate_numero_documento(cls, v, values):
        """
        Valida número de documento según tipo específico.
        """
        if not v:
            raise ValueError("Número de documento es requerido")

        v = v.strip()
        tipo_doc = values.get('tipo_documento')

        if tipo_doc == TipoDocumentoEnum.RUC:
            return cls._validate_ruc_format(v)
        elif tipo_doc == TipoDocumentoEnum.CI:
            return cls._validate_ci_format(v)
        elif tipo_doc == TipoDocumentoEnum.PASAPORTE:
            return cls._validate_pasaporte_format(v)

        return v

    @validator('tipo_documento', always=True)
    def validate_coherencia_cliente_documento(cls, v, values):
        """Valida coherencia entre tipo cliente y tipo documento"""
        tipo_cliente = values.get('tipo_cliente')

        if tipo_cliente == TipoClienteEnum.EXTRANJERO:
            if v not in [TipoDocumentoEnum.PASAPORTE, TipoDocumentoEnum.OTROS]:
                raise ValueError(
                    'Cliente extranjero debe usar pasaporte u otros documentos'
                )

        elif tipo_cliente == TipoClienteEnum.PERSONA_JURIDICA:
            if v != TipoDocumentoEnum.RUC:
                raise ValueError(
                    'Persona jurídica debe usar RUC'
                )

        return v

    @classmethod
    def _validate_ruc_format(cls, ruc: str) -> str:
        """Validar formato RUC Paraguay específicamente"""
        # Limpiar espacios y guiones
        clean_ruc = re.sub(r'[-\s]', '', ruc.strip())

        # Validar formato: 7-8 dígitos + guión + 1 dígito verificador
        if not re.match(r'^\d{8}-?\d{1}$', ruc):
            raise ValueError("RUC debe tener formato XXXXXXX-X o XXXXXXXX-X")

        # Extraer número y dígito verificador
        if '-' in ruc:
            ruc_number, dv = ruc.split('-')
        else:
            ruc_number = clean_ruc[:-1]
            dv = clean_ruc[-1]

        # Validar longitud del número base
        if len(ruc_number) != 8:
            raise ValueError(
                "Número base del RUC debe tener exactamente 8 dígitos")

        # Validar que no sea RUC de prueba inválido
        if ruc_number == "00000000":
            raise ValueError("RUC 00000000 no es válido")

        # Validar que el primer dígito no sea 0 (excepto casos especiales)
        if ruc_number.startswith("0") and ruc_number != "00000000":
            raise ValueError(
                "RUC no puede empezar con 0 - Salvos casos especiales (schemas/client.py)")
        # TODO: Implementar validación completa del dígito verificador
        # usando algoritmo oficial de la SET

        # Retornar RUC formateado
        return f"{ruc_number}-{dv}"

    @classmethod
    def _validate_ci_format(cls, ci: str) -> str:
        """Validar formato Cédula de Identidad Paraguay"""
        # Limpiar puntos y espacios
        clean_ci = re.sub(r'[.\s]', '', ci.strip())

        # Validar formato: 6-8 dígitos numéricos
        if not re.match(r'^\d{7,8}$', clean_ci):
            raise ValueError("CI debe tener entre 7 y 8 dígitos")

        return clean_ci

    @classmethod
    def _validate_pasaporte_format(cls, pasaporte: str) -> str:
        """Validar formato básico de pasaporte"""
        clean_passport = pasaporte.strip().upper()

        # Validar longitud básica
        if len(clean_passport) < 8 or len(clean_passport) > 15:
            raise ValueError("Pasaporte debe tener entre 8 y 15 caracteres")

        # Validar caracteres alfanuméricos
        if not re.match(r'^[A-Z0-9]+$', clean_passport):
            raise ValueError("Pasaporte debe contener solo letras y números")

        return clean_passport

    @validator('razon_social')
    def validate_razon_social(cls, v, values):
        """Valida razón social para personas jurídicas"""
        tipo_cliente = values.get('tipo_cliente')

        if tipo_cliente == TipoClienteEnum.PERSONA_JURIDICA:
            if not v or not v.strip():
                raise ValueError(
                    "Razón social es requerida para personas jurídicas")

            # Limpiar y normalizar
            v = ' '.join(v.strip().split())

            # Validar caracteres permitidos
            if not re.match(r'^[A-ZÁÉÍÓÚÜÑ0-9\s\.\-\(\)&]+$', v.upper()):
                raise ValueError(
                    "Razón social contiene caracteres no permitidos")

            return v.upper()

        return v

    @validator('nombres')
    def validate_nombres(cls, v, values):
        """Valida nombres para personas físicas"""
        tipo_cliente = values.get('tipo_cliente')

        if tipo_cliente == TipoClienteEnum.PERSONA_FISICA:
            if not v or not v.strip():
                raise ValueError(
                    "Nombres son requeridos para personas físicas")

            # Validar caracteres permitidos (letras, espacios, acentos)
            v = v.strip()
            if not re.match(r'^[a-zA-ZÀ-ÿñÑ\s]+$', v):
                raise ValueError(
                    "Nombres solo pueden contener letras y espacios")

            return v.title()  # Capitalizar

        return v

    @validator('apellidos')
    def validate_apellidos(cls, v, values):
        """Valida apellidos para personas físicas"""
        tipo_cliente = values.get('tipo_cliente')

        if tipo_cliente == TipoClienteEnum.PERSONA_FISICA:
            if not v or not v.strip():
                raise ValueError(
                    "Apellidos son requeridos para personas físicas")

            # Validar caracteres permitidos
            v = v.strip()
            if not re.match(r'^[a-zA-ZÀ-ÿñÑ\s]+$', v):
                raise ValueError(
                    "Apellidos solo pueden contener letras y espacios")

            return v.title()  # Capitalizar

        return v

    @validator('telefono')
    def validate_telefono_cliente(cls, v):
        """Valida formato de teléfono - acepta Paraguay e internacionales"""
        clean_phone = re.sub(r'[^\d\-\s\+\(\)]', '', v.strip())

        # Patrones Paraguay (preferidos)
        patterns_paraguay = [
            r'^0(21|61|71|31|41|51|81|91|331|336|343|351|981|982|983|984|985|986|991|992|994|995|996)-?\d{6}$',
            r'^595-?(21|61|71|31|41|51|81|91|9[0-9]{2})-?\d{6}$',
            r'^(021|061|071|031|041|051|081|091|0981|0982|0983|0984|0985|0986)\d{6}$'
        ]

        # Verificar si es paraguayo
        if any(re.match(pattern, clean_phone) for pattern in patterns_paraguay):
            return clean_phone

        # Si no es paraguayo, validar formato internacional básico
        if re.match(r'^\+[1-9]\d{6,14}$', clean_phone):
            return clean_phone

        # Formato sin + internacional
        if re.match(r'^[1-9]\d{6,14}$', clean_phone):
            return clean_phone

        raise ValueError('Formato de teléfono inválido')

    @validator('contribuyente', always=True)
    def validate_contribuyente_consistency(cls, v, values):
        """Valida consistencia de contribuyente con tipo documento"""
        tipo_doc = values.get('tipo_documento')

        # Si tiene RUC, automáticamente es contribuyente
        if tipo_doc == TipoDocumentoEnum.RUC:
            return True

        # Si no tiene RUC pero dice ser contribuyente, es inconsistente
        if v and tipo_doc != TipoDocumentoEnum.RUC:
            raise ValueError(
                'Solo clientes con RUC pueden ser marcados como contribuyentes'
            )

        return v

    @validator('pais')
    def validate_pais_codigo(cls, v):
        """Valida código de país ISO"""
        if v:
            v = v.strip().upper()
            if len(v) != 3:
                raise ValueError(
                    "Código país debe tener exactamente 3 caracteres")

            if not re.match(r'^[A-Z]{3}$', v):
                raise ValueError("Código país debe contener solo letras")

            # Lista básica de países válidos comunes
            paises_comunes = ['PRY', 'ARG', 'BRA',
                              'URY', 'BOL', 'CHL', 'USA', 'ESP', 'COL']
            if v not in paises_comunes:
                # Solo warning, no error - puede ser país menos común
                pass

        return v

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "tipo_cliente": "persona_juridica",
                "tipo_documento": "ruc",
                "numero_documento": "80087654-3",
                "razon_social": "CLIENTE EJEMPLO S.R.L.",
                "direccion": "Av. España 567",
                "ciudad": "San Lorenzo",
                "departamento": "11",
                "telefono": "021-555456",
                "email": "compras@cliente.com.py",
                "contribuyente": True,
                "exento_iva": False,
                "pais": "PRY"
            }
        }


class ClienteUpdateDTO(BaseModel):
    """
    DTO para actualización de clientes existentes.

    Permite modificar datos del cliente excepto tipo y número de documento.
    Todos los campos son opcionales para updates parciales.

    Examples:
        ```python
        # PUT /api/v1/clientes/{id}
        update_data = ClienteUpdateDTO(
            telefono="021-555999",
            email="nuevoemail@cliente.com.py",
            direccion="Nueva dirección actualizada"
        )
        ```
    """

    # === TIPO Y NÚMERO DOCUMENTO NO SE PUEDEN CAMBIAR (OMITIDOS) ===

    # Información personal/empresarial
    razon_social: Optional[str] = Field(
        None,
        max_length=200,
        description="Nueva razón social"
    )

    nombres: Optional[str] = Field(
        None,
        max_length=100,
        description="Nuevos nombres"
    )

    apellidos: Optional[str] = Field(
        None,
        max_length=100,
        description="Nuevos apellidos"
    )

    nombre_fantasia: Optional[str] = Field(
        None,
        max_length=200,
        description="Nuevo nombre comercial"
    )

    # Localización
    direccion: Optional[str] = Field(
        None,
        min_length=10,
        max_length=500,
        description="Nueva dirección"
    )

    ciudad: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Nueva ciudad"
    )

    departamento: Optional[DepartamentoParaguayEnum] = Field(
        None,
        description="Nuevo departamento"
    )

    codigo_postal: Optional[str] = Field(
        None,
        max_length=10,
        description="Nuevo código postal"
    )

    pais: Optional[str] = Field(
        None,
        min_length=3,
        max_length=3,
        description="Nuevo código país"
    )

    # Contacto
    telefono: Optional[str] = Field(
        None,
        min_length=7,
        max_length=20,
        description="Nuevo teléfono"
    )

    celular: Optional[str] = Field(
        None,
        max_length=20,
        description="Nuevo celular"
    )

    email: Optional[EmailStr] = Field(
        None,
        description="Nuevo email"
    )

    # Información fiscal
    exento_iva: Optional[bool] = Field(
        None,
        description="Cambiar exención IVA"
    )

    # Información adicional
    observaciones: Optional[str] = Field(
        None,
        max_length=1000,
        description="Nuevas observaciones"
    )

    # Validadores con lógica duplicada
    @validator('razon_social')
    def validate_razon_social(cls, v):
        if v is not None:
            v = ' '.join(v.strip().split())
            if not re.match(r'^[A-ZÁÉÍÓÚÜÑ0-9\s\.\-\(\)&]+$', v.upper()):
                raise ValueError(
                    "Razón social contiene caracteres no permitidos")
            return v.upper()
        return v

    @validator('nombres', 'apellidos')
    def validate_nombres_apellidos(cls, v):
        if v is not None:
            v = v.strip()
            if not re.match(r'^[a-zA-ZÀ-ÿñÑ\s]+$', v):
                raise ValueError("Solo pueden contener letras y espacios")
            return v.title()
        return v

    @validator('telefono')
    def validate_telefono_cliente(cls, v):
        """Valida formato de teléfono - acepta Paraguay e internacionales"""
        clean_phone = re.sub(r'[^\d\-\s\+\(\)]', '', v.strip())

        # Patrones Paraguay (preferidos)
        patterns_paraguay = [
            r'^0(21|61|71|31|41|51|81|91|331|336|343|351|981|982|983|984|985|986|991|992|994|995|996)-?\d{6}$',
            r'^595-?(21|61|71|31|41|51|81|91|9[0-9]{2})-?\d{6}$',
            r'^(021|061|071|031|041|051|081|091|0981|0982|0983|0984|0985|0986)\d{6}$'
        ]

        # Verificar si es paraguayo
        if any(re.match(pattern, clean_phone) for pattern in patterns_paraguay):
            return clean_phone

        # Si no es paraguayo, validar formato internacional básico
        if re.match(r'^\+[1-9]\d{6,14}$', clean_phone):
            return clean_phone

        # Formato sin + internacional
        if re.match(r'^[1-9]\d{6,14}$', clean_phone):
            return clean_phone

        raise ValueError('Formato de teléfono inválido')

    @validator('pais')
    def validate_pais_codigo(cls, v):
        """Valida código de país ISO"""
        if v:
            v = v.strip().upper()
            if len(v) != 3:
                raise ValueError(
                    "Código país debe tener exactamente 3 caracteres")

            if not re.match(r'^[A-Z]{3}$', v):
                raise ValueError("Código país debe contener solo letras")

            # Lista básica de países válidos comunes
            paises_comunes = ['PRY', 'ARG', 'BRA',
                              'URY', 'BOL', 'CHL', 'USA', 'ESP', 'COL']
            if v not in paises_comunes:
                # Solo warning, no error - puede ser país menos común
                pass

        return v

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "telefono": "021-555999",
                "email": "nuevoemail@cliente.com.py",
                "direccion": "Nueva dirección actualizada",
                "observaciones": "Cliente preferencial - descuento 5%"
            }
        }


# ===============================================
# DTOs DE SALIDA (RESPONSE)
# ===============================================

class ClienteResponseDTO(BaseModel):
    """
    DTO para respuesta con datos completos de cliente.

    Información completa del cliente para APIs y frontend.
    Incluye datos fiscales, contacto y metadata.

    Examples:
        ```python
        # GET /api/v1/clientes/{id} response
        cliente_response = ClienteResponseDTO(
            id=1,
            tipo_cliente="persona_juridica",
            numero_documento="80087654-3",
            nombre_completo="CLIENTE EJEMPLO S.R.L.",
            # ... resto de campos
        )
        ```
    """

    # === IDENTIFICACIÓN ===
    id: int = Field(..., description="ID único del cliente")

    tipo_cliente: str = Field(..., description="Tipo de cliente")

    tipo_documento: str = Field(..., description="Tipo de documento")

    numero_documento: str = Field(..., description="Número de documento")

    dv: Optional[str] = Field(None, description="Dígito verificador (RUC)")

    # === INFORMACIÓN PERSONAL/EMPRESARIAL ===
    razon_social: Optional[str] = Field(None, description="Razón social")

    nombres: Optional[str] = Field(None, description="Nombres")

    apellidos: Optional[str] = Field(None, description="Apellidos")

    nombre_fantasia: Optional[str] = Field(
        None, description="Nombre comercial")

    # Campo calculado
    nombre_completo: Optional[str] = Field(
        None, description="Nombre completo calculado"
    )

    documento_formateado: Optional[str] = Field(
        None, description="Documento con formato apropiado"
    )

    # === LOCALIZACIÓN ===
    direccion: str = Field(..., description="Dirección completa")

    ciudad: str = Field(..., description="Ciudad")

    departamento: str = Field(..., description="Código departamento")

    departamento_nombre: Optional[str] = Field(
        None, description="Nombre del departamento"
    )

    codigo_postal: Optional[str] = Field(None, description="Código postal")

    pais: str = Field(..., description="Código país")

    # === CONTACTO ===
    telefono: str = Field(..., description="Teléfono principal")

    celular: Optional[str] = Field(None, description="Teléfono celular")

    email: Optional[str] = Field(None, description="Email")

    # === INFORMACIÓN FISCAL ===
    contribuyente: bool = Field(..., description="Si es contribuyente")

    exento_iva: bool = Field(..., description="Si está exento de IVA")

    # === METADATA ===
    is_active: bool = Field(..., description="Si está activo")

    created_at: datetime = Field(..., description="Fecha de creación")

    updated_at: datetime = Field(..., description="Última actualización")

    empresa_id: int = Field(..., description="ID empresa propietaria")

    observaciones: Optional[str] = Field(None, description="Observaciones")

    # === INFORMACIÓN ADICIONAL ===
    documentos_recibidos: Optional[int] = Field(
        None, description="Total documentos recibidos"
    )

    ultimo_documento: Optional[datetime] = Field(
        None, description="Fecha último documento recibido"
    )

    monto_total_compras: Optional[float] = Field(
        None, description="Monto total de compras (Guaraníes)"
    )

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "tipo_cliente": "persona_juridica",
                "tipo_documento": "ruc",
                "numero_documento": "80087654-3",
                "dv": "3",
                "razon_social": "CLIENTE EJEMPLO S.R.L.",
                "nombre_completo": "CLIENTE EJEMPLO S.R.L.",
                "documento_formateado": "80087654-3",
                "direccion": "Av. España 567",
                "ciudad": "San Lorenzo",
                "departamento": "11",
                "departamento_nombre": "Central",
                "telefono": "021-555456",
                "email": "compras@cliente.com.py",
                "contribuyente": True,
                "exento_iva": False,
                "is_active": True,
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:30:00",
                "empresa_id": 1,
                "documentos_recibidos": 45,
                "ultimo_documento": "2025-01-14T15:20:00",
                "monto_total_compras": 125000000.0,
                "pais": "PRY"
            }
        }


class ClienteListDTO(BaseModel):
    """
    DTO para elemento en lista de clientes.

    Versión compacta de ClienteResponseDTO para listados
    que requieren menos información por performance.

    Examples:
        ```python
        # GET /api/v1/clientes response (lista)
        clientes_list = [
            ClienteListDTO(
                id=1,
                numero_documento="80087654-3",
                nombre_completo="CLIENTE EJEMPLO S.R.L.",
                ciudad="San Lorenzo",
                contribuyente=True,
                is_active=True
            )
        ]
        ```
    """

    id: int = Field(..., description="ID único del cliente")

    tipo_cliente: str = Field(..., description="Tipo de cliente")

    numero_documento: str = Field(..., description="Número de documento")

    nombre_completo: str = Field(..., description="Nombre completo")

    ciudad: str = Field(..., description="Ciudad")

    telefono: str = Field(..., description="Teléfono")

    email: Optional[str] = Field(None, description="Email")

    contribuyente: bool = Field(..., description="Si es contribuyente")

    is_active: bool = Field(..., description="Si está activo")

    created_at: datetime = Field(..., description="Fecha de creación")

    documentos_recibidos: Optional[int] = Field(
        None, description="Total documentos"
    )

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "tipo_cliente": "persona_juridica",
                "numero_documento": "80087654-3",
                "nombre_completo": "CLIENTE EJEMPLO S.R.L.",
                "ciudad": "San Lorenzo",
                "telefono": "021-555456",
                "email": "compras@cliente.com.py",
                "contribuyente": True,
                "is_active": True,
                "created_at": "2025-01-15T10:30:00",
                "documentos_recibidos": 45
            }
        }


# ===============================================
# DTOs ESPECIALIZADOS
# ===============================================

class ClienteSearchDTO(BaseModel):
    """
    DTO para búsqueda de clientes.

    Parámetros de búsqueda flexibles para encontrar clientes
    por diferentes criterios.

    Examples:
        ```python
        # GET /api/v1/clientes/search?q=cliente&tipo=persona_juridica
        search_params = ClienteSearchDTO(
            q="cliente ejemplo",
            tipo_cliente="persona_juridica",
            contribuyente=True,
            departamento="11"
        )
        ```
    """

    q: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Búsqueda general (nombre, razón social, documento)"
    )

    tipo_cliente: Optional[TipoClienteEnum] = Field(
        None,
        description="Filtrar por tipo de cliente"
    )

    tipo_documento: Optional[TipoDocumentoEnum] = Field(
        None,
        description="Filtrar por tipo de documento"
    )

    contribuyente: Optional[bool] = Field(
        None,
        description="Filtrar por contribuyente"
    )

    departamento: Optional[DepartamentoParaguayEnum] = Field(
        None,
        description="Filtrar por departamento"
    )

    ciudad: Optional[str] = Field(
        None,
        max_length=100,
        description="Filtrar por ciudad"
    )

    is_active: Optional[bool] = Field(
        default=True,
        description="Filtrar por activos/inactivos"
    )

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "q": "cliente ejemplo",
                "tipo_cliente": "persona_juridica",
                "contribuyente": True,
                "departamento": "11",
                "is_active": True
            }
        }


class ClienteStatsDTO(BaseModel):
    """
    DTO para estadísticas de cliente.

    Métricas y estadísticas de documentos recibidos por el cliente
    útiles para análisis de relación comercial.

    Examples:
        ```python
        # GET /api/v1/clientes/{id}/stats response
        cliente_stats = ClienteStatsDTO(
            cliente_id=1,
            documentos_totales=45,
            facturas_recibidas=40,
            monto_total_compras=125000000,
            promedio_mensual=8750000
        )
        ```
    """

    cliente_id: int = Field(..., description="ID del cliente")

    # === CONTADORES DOCUMENTOS ===
    documentos_totales: int = Field(
        default=0,
        description="Total documentos recibidos"
    )

    facturas_recibidas: int = Field(
        default=0,
        description="Facturas recibidas"
    )

    notas_credito: int = Field(
        default=0,
        description="Notas de crédito recibidas"
    )

    notas_debito: int = Field(
        default=0,
        description="Notas de débito recibidas"
    )

    # === MONTOS ===
    monto_total_compras: float = Field(
        default=0.0,
        description="Monto total de compras (Guaraníes)"
    )

    monto_mes_actual: float = Field(
        default=0.0,
        description="Monto compras mes actual (Guaraníes)"
    )

    promedio_mensual: float = Field(
        default=0.0,
        description="Promedio de compras mensual (Guaraníes)"
    )

    monto_promedio_documento: float = Field(
        default=0.0,
        description="Monto promedio por documento (Guaraníes)"
    )

    # === FECHAS ===
    primera_compra: Optional[datetime] = Field(
        None,
        description="Fecha de primera compra"
    )

    ultima_compra: Optional[datetime] = Field(
        None,
        description="Fecha de última compra"
    )

    # === FRECUENCIA ===
    compras_por_mes: float = Field(
        default=0.0,
        description="Promedio de compras por mes"
    )

    dias_desde_ultima_compra: Optional[int] = Field(
        None,
        description="Días desde última compra"
    )

    # === CLASIFICACIÓN CLIENTE ===
    clasificacion: Optional[str] = Field(
        None,
        description="Clasificación del cliente (A/B/C según compras)"
    )

    es_cliente_frecuente: bool = Field(
        default=False,
        description="Si es cliente frecuente (>= 1 compra por mes)"
    )

    class Config:
        schema_extra = {
            "example": {
                "cliente_id": 1,
                "documentos_totales": 45,
                "facturas_recibidas": 40,
                "notas_credito": 3,
                "notas_debito": 2,
                "monto_total_compras": 125000000.0,
                "monto_mes_actual": 8750000.0,
                "promedio_mensual": 8333333.0,
                "monto_promedio_documento": 2777777.0,
                "primera_compra": "2024-06-15T10:30:00",
                "ultima_compra": "2025-01-14T15:20:00",
                "compras_por_mes": 6.2,
                "dias_desde_ultima_compra": 1,
                "clasificacion": "A",
                "es_cliente_frecuente": True
            }
        }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # === ENUMS ===
    "TipoClienteEnum",
    "TipoDocumentoEnum",

    # === DTOs DE ENTRADA ===
    "ClienteCreateDTO",
    "ClienteUpdateDTO",

    # === DTOs DE SALIDA ===
    "ClienteResponseDTO",
    "ClienteListDTO",

    # === DTOs ESPECIALIZADOS ===
    "ClienteSearchDTO",
    "ClienteStatsDTO"
]
