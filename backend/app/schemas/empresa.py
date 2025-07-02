# ===============================================
# ARCHIVO: backend/app/schemas/empresa.py
# PROPÓSITO: DTOs para empresa/contribuyente emisor SIFEN
# PRIORIDAD: 🟡 CRÍTICO - Emisor de documentos electrónicos
# ===============================================

"""
Esquemas Pydantic para gestión de empresas/contribuyentes emisores.

Este módulo define DTOs para:
- Registro de empresas emisoras
- Configuración datos fiscales Paraguay
- Configuración SIFEN (establecimientos, puntos expedición)
- Gestión de datos tributarios SET

Integra con:
- models/empresa.py (SQLAlchemy)
- utils/ruc_utils.py (validación RUC)
- services/xml_generator (emisor XML)
- api/v1/empresas.py (endpoints CRUD)

Regulaciones Paraguay:
- RUC con dígito verificador válido
- Departamentos Paraguay (01-17)
- Establecimientos SIFEN (001-999)
- Puntos expedición (001-999)
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


class AmbienteSifenEnum(str, Enum):
    """Ambientes SIFEN disponibles"""
    TEST = "test"
    PRODUCTION = "production"


# ===============================================
# DTOs DE ENTRADA (REQUEST)
# ===============================================

class EmpresaCreateDTO(BaseModel):
    """
    DTO para registro de nuevas empresas/contribuyentes.

    Valida datos fiscales requeridos por SET Paraguay y
    configuración inicial para emisión de documentos SIFEN.

    Examples:
        ```python
        # POST /api/v1/empresas
        empresa_data = EmpresaCreateDTO(
            ruc="80016875-5",
            razon_social="MI EMPRESA S.A.",
            nombre_fantasia="Mi Empresa",
            direccion="Av. Mariscal López 1234",
            ciudad="Asunción",
            departamento="11",
            telefono="021-555123",
            email="facturacion@miempresa.com.py"
        )
        ```
    """

    # === IDENTIFICACIÓN FISCAL OBLIGATORIA ===
    ruc: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="RUC Paraguay con dígito verificador (ej: formato: 12345678-9)"
    )

    razon_social: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Razón social registrada en SET"
    )

    # === INFORMACIÓN EMPRESARIAL ===
    nombre_fantasia: Optional[str] = Field(
        None,
        max_length=200,
        description="Nombre comercial o fantasía (opcional)"
    )

    # === LOCALIZACIÓN ===
    direccion: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Dirección fiscal completa"
    )

    ciudad: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Ciudad de ubicación"
    )

    departamento: DepartamentoParaguayEnum = Field(
        ...,
        description="Departamento Paraguay (01-17)"
    )

    # === CONTACTO ===
    telefono: str = Field(
        ...,
        min_length=7,
        max_length=20,
        description="Teléfono principal (formato Paraguay)"
    )

    email: EmailStr = Field(
        ...,
        description="Email para notificaciones y documentos"
    )

    # === CONFIGURACIÓN SIFEN (OPCIONAL EN CREACIÓN) ===
    ambiente_sifen: AmbienteSifenEnum = Field(
        default=AmbienteSifenEnum.TEST,
        description="Ambiente SIFEN inicial (test por defecto)"
    )

    establecimiento: str = Field(
        default="001",
        min_length=3,
        max_length=3,
        description="Código establecimiento SIFEN (001-999)"
    )

    punto_expedicion: str = Field(
        default="001",
        min_length=3,
        max_length=3,
        description="Punto de expedición SIFEN (001-999)"
    )

    @validator('ruc')
    def validate_ruc_paraguay(cls, v):
        """
        Valida formato RUC Paraguay con dígito verificador.

        Formato esperado: XXXXXXXX-X (8 dígitos + DV)
        Algoritmo dígito verificador: Módulo 11 SET Paraguay
        - Factores: [2, 3, 4, 5, 6, 7, 2, 3]
        - Si resto < 2: DV = 0, sino DV = 11 - resto

        Validaciones:
        - Exactamente 8 dígitos antes del guión
        - 1 dígito verificador después del guión
        - No puede ser 00000000-X
        - No puede empezar con 0 (salvo excepciones)
        """
        # Limpiar espacios
        v = v.strip().upper()

        # Validar formato básico
        if not re.match(r'^\d{8}-\d$', v):
            raise ValueError(
                'RUC debe tener formato XXXXXXXX-X (8 dígitos + DV)')

        # Extraer partes
        ruc_parts = v.split('-')
        ruc_number = ruc_parts[0]
        dv = ruc_parts[1]

        # Validar longitud del número base
        if len(ruc_number) != 8:
            raise ValueError(
                'Número base del RUC debe tener exactamente 8 dígitos')

        # Validar que no sea RUC de prueba inválido
        if ruc_number == "00000000":
            raise ValueError("RUC 00000000 no es válido")

        # Validar que el primer dígito no sea 0 (excepto casos especiales)
        if ruc_number.startswith("0") and ruc_number != "00000000":
            raise ValueError("RUC no puede empezar con 0")
        # TODO: Implementar validación completa del dígito verificador
        # usando algoritmo oficial de la SET

        return v

    @validator('razon_social')
    def validate_razon_social(cls, v):
        """Valida formato de razón social según normativa paraguaya"""
        # Limpiar espacios extra
        v = ' '.join(v.strip().split())

        # Validar caracteres permitidos (letras, números, espacios, algunos especiales)
        if not re.match(r'^[A-ZÁÉÍÓÚÜÑ0-9\s\.\-&()]+$', v.upper()):
            raise ValueError('Razón social contiene caracteres no permitidos')

        return v.upper()  # Normalizar a mayúsculas

    @validator('telefono')
    def validate_telefono_paraguay(cls, v):
        """Valida formato de teléfono Paraguay"""
        # Limpiar caracteres no numéricos excepto guiones y espacios
        clean_phone = re.sub(r'[^\d\-\s]', '', v.strip())

        # Formatos válidos Paraguay:
        # 021-123456 (línea fija Asunción)
        # 0981-123456 (celular)
        # 595-21-123456 (internacional)
        patterns = [
            # Específicos Paraguay
            r'^0(21|61|71|31|41|51|81|91|331|336|343|351|981|982|983|984|985|986|991|992|994|995|996)-?\d{6}$',
            # Internacional Paraguay
            r'^595-?(21|61|71|31|41|51|81|91|9[0-9]{2})-?\d{6}$',
            # Sin guiones
            r'^(021|061|071|031|041|051|081|091|0331|0336|0343|0351|0981|0982|0983|0984|0985|0986|0991|0992|0994|0995|0996)\d{6}$'
        ]

        if not any(re.match(pattern, clean_phone) for pattern in patterns):
            raise ValueError('Formato de teléfono inválido para Paraguay')

        return clean_phone

    @validator('email')
    def validate_email_empresa(cls, v):
        """Valida email empresarial"""
        email_str = str(v).lower()
        domain = email_str.split('@')[1] if '@' in email_str else ''

        # Lista de dominios personales
        dominios_personales = ['gmail.com',
                               'hotmail.com', 'yahoo.com', 'outlook.com']

        # OPCIÓN A: Error estricto
        # if domain in dominios_personales:
        #     raise ValueError(f'Email empresarial requerido. {domain} es dominio personal')

        # OPCIÓN B: Warning pero permitir (más flexible)
        if domain in dominios_personales:
            import warnings
            warnings.warn(f'Usando dominio personal {domain} para empresa')

        return v

    @validator('ambiente_sifen', always=True)
    def validate_coherencia_produccion(cls, v, values):
        """Valida coherencia para ambiente producción"""
        if v == AmbienteSifenEnum.PRODUCTION:
            email = values.get('email')
            if email:
                email_str = str(email).lower()
                dominios_personales = ['gmail.com', 'hotmail.com']

                if any(domain in email_str for domain in dominios_personales):
                    raise ValueError(
                        'Ambiente PRODUCTION requiere email corporativo, '
                        'no se permite gmail/hotmail en producción'
                    )
        return v

    @validator('establecimiento', 'punto_expedicion')
    def validate_codigo_sifen(cls, v):
        """Valida códigos de establecimiento y punto expedición SIFEN"""
        # Debe ser exactamente 3 dígitos
        if not re.match(r'^\d{3}$', v):
            raise ValueError('Código debe ser exactamente 3 dígitos (001-999)')

        # Validar rango
        num = int(v)
        if num < 1 or num > 999:
            raise ValueError('Código debe estar entre 001 y 999')

        # No puede ser 000
        if v == "000":
            raise ValueError('Código no puede ser 000')
        return v.zfill(3)  # Asegurar formato 001, 002, etc.

    class Config:
        # Usar valores de enum
        use_enum_values = True
        schema_extra = {
            "example": {
                "ruc": "80016875-4",
                "razon_social": "MI EMPRESA S.A.",
                "nombre_fantasia": "Mi Empresa",
                "direccion": "Av. Mariscal López 1234",
                "ciudad": "Asunción",
                "departamento": "11",
                "telefono": "021-555123",
                "email": "facturacion@miempresa.com.py",
                "ambiente_sifen": "test",
                "establecimiento": "001",
                "punto_expedicion": "001"
            }
        }


class EmpresaUpdateDTO(BaseModel):
    """
    DTO para actualización de empresas existentes.

    Permite modificar datos empresariales excepto RUC.
    Todos los campos son opcionales para updates parciales.

    Examples:
        ```python
        # PUT /api/v1/empresas/{id}
        update_data = EmpresaUpdateDTO(
            nombre_fantasia="Nuevo Nombre Comercial",
            telefono="021-555999",
            ambiente_sifen="production"
        )
        ```
    """

    # === RUC NO SE PUEDE CAMBIAR (OMITIDO) ===

    razon_social: Optional[str] = Field(
        None,
        min_length=3,
        max_length=200,
        description="Nueva razón social"
    )

    nombre_fantasia: Optional[str] = Field(
        None,
        max_length=200,
        description="Nuevo nombre comercial"
    )

    direccion: Optional[str] = Field(
        None,
        min_length=10,
        max_length=500,
        description="Nueva dirección fiscal"
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

    telefono: Optional[str] = Field(
        None,
        min_length=7,
        max_length=20,
        description="Nuevo teléfono"
    )

    email: Optional[EmailStr] = Field(
        None,
        description="Nuevo email"
    )

    ambiente_sifen: Optional[AmbienteSifenEnum] = Field(
        None,
        description="Cambiar ambiente SIFEN"
    )

    establecimiento: Optional[str] = Field(
        None,
        min_length=3,
        max_length=3,
        description="Nuevo código establecimiento"
    )

    punto_expedicion: Optional[str] = Field(
        None,
        min_length=3,
        max_length=3,
        description="Nuevo punto de expedición"
    )

    # Reutilizar validadores de EmpresaCreateDTO
    @validator('razon_social')
    def validate_razon_social(cls, v):
        """Valida formato de razón social según normativa paraguaya"""
        # Limpiar espacios extra
        v = ' '.join(v.strip().split())

        # Validar caracteres permitidos (letras, números, espacios, algunos especiales)
        if not re.match(r'^[A-ZÁÉÍÓÚÜÑ0-9\s\.\-&()]+$', v.upper()):
            raise ValueError('Razón social contiene caracteres no permitidos')

        return v.upper()

    @validator('telefono')
    def validate_telefono_paraguay(cls, v):
        """Valida formato de teléfono Paraguay"""
        # Limpiar caracteres no numéricos excepto guiones y espacios
        clean_phone = re.sub(r'[^\d\-\s]', '', v.strip())

        # Formatos válidos Paraguay:
        # 021-123456 (línea fija Asunción)
        # 0981-123456 (celular)
        # 595-21-123456 (internacional)
        patterns = [
            # Específicos Paraguay
            r'^0(21|61|71|31|41|51|81|91|331|336|343|351|981|982|983|984|985|986|991|992|994|995|996)-?\d{6}$',
            # Internacional Paraguay
            r'^595-?(21|61|71|31|41|51|81|91|9[0-9]{2})-?\d{6}$',
            # Sin guiones
            r'^(021|061|071|031|041|051|081|091|0331|0336|0343|0351|0981|0982|0983|0984|0985|0986|0991|0992|0994|0995|0996)\d{6}$'
        ]

        if not any(re.match(pattern, clean_phone) for pattern in patterns):
            raise ValueError('Formato de teléfono inválido para Paraguay')

        return clean_phone

    @validator('email')
    def validate_email_empresa(cls, v):
        """Valida email empresarial"""
        if v is not None:  # Solo si se está actualizando
            email_str = str(v).lower()
            domain = email_str.split('@')[1] if '@' in email_str else ''

            dominios_personales = ['gmail.com',
                                   'hotmail.com', 'yahoo.com', 'outlook.com']

            if domain in dominios_personales:
                raise ValueError(
                    f'Email empresarial preferible. {domain} es dominio personal')

        return v

    @validator('ambiente_sifen', always=True)
    def validate_coherencia_produccion(cls, v, values):
        """Valida coherencia para ambiente producción"""
        if v == AmbienteSifenEnum.PRODUCTION:
            email = values.get('email')
            if email:
                email_str = str(email).lower()
                dominios_personales = ['gmail.com', 'hotmail.com']

                if any(domain in email_str for domain in dominios_personales):
                    raise ValueError(
                        'Ambiente PRODUCTION requiere email corporativo, '
                        'no se permite gmail/hotmail en producción'
                    )
        return v

    @validator('establecimiento', 'punto_expedicion')
    def validate_codigo_sifen(cls, v):
        """Valida códigos de establecimiento y punto expedición SIFEN"""
        # Debe ser exactamente 3 dígitos
        if not re.match(r'^\d{3}$', v):
            raise ValueError('Código debe ser exactamente 3 dígitos (001-999)')

        # Validar rango
        num = int(v)
        if num < 1 or num > 999:
            raise ValueError('Código debe estar entre 001 y 999')

        # No puede ser 000
        if v == "000":
            raise ValueError('Código no puede ser 000')
        return v.zfill(3)

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "nombre_fantasia": "Nuevo Nombre Comercial",
                "telefono": "021-555999",
                "email": "nuevoemail@empresa.com.py",
                "ambiente_sifen": "production"
            }
        }


# ===============================================
# DTOs DE SALIDA (RESPONSE)
# ===============================================

class EmpresaResponseDTO(BaseModel):
    """
    DTO para respuesta con datos completos de empresa.

    Información completa de la empresa para APIs y frontend.
    Incluye datos fiscales, configuración SIFEN y metadata.

    Examples:
        ```python
        # GET /api/v1/empresas/{id} response
        empresa_response = EmpresaResponseDTO(
            id=1,
            ruc="80016875-5",
            dv="5",
            razon_social="MI EMPRESA S.A.",
            # ... resto de campos
        )
        ```
    """

    # === IDENTIFICACIÓN ===
    id: int = Field(..., description="ID único de la empresa")

    ruc: str = Field(..., description="RUC Paraguay")

    dv: str = Field(..., description="Dígito verificador del RUC")

    # === INFORMACIÓN EMPRESARIAL ===
    razon_social: str = Field(..., description="Razón social")

    nombre_fantasia: Optional[str] = Field(
        None, description="Nombre comercial"
    )

    # === LOCALIZACIÓN ===
    direccion: str = Field(..., description="Dirección fiscal")

    ciudad: str = Field(..., description="Ciudad")

    departamento: str = Field(..., description="Código departamento")

    departamento_nombre: Optional[str] = Field(
        None, description="Nombre del departamento"
    )

    # === CONTACTO ===
    telefono: str = Field(..., description="Teléfono principal")

    email: str = Field(..., description="Email de contacto")

    # === CONFIGURACIÓN SIFEN ===
    ambiente_sifen: str = Field(..., description="Ambiente SIFEN actual")

    establecimiento: str = Field(..., description="Código establecimiento")

    punto_expedicion: str = Field(..., description="Punto de expedición")

    # === ESTADO Y METADATA ===
    is_active: bool = Field(..., description="Si la empresa está activa")

    created_at: datetime = Field(..., description="Fecha de creación")

    updated_at: datetime = Field(..., description="Última actualización")

    # === INFORMACIÓN ADICIONAL ===
    user_id: int = Field(..., description="ID del usuario propietario")

    documentos_count: Optional[int] = Field(
        None, description="Total documentos emitidos"
    )

    ultimo_documento: Optional[datetime] = Field(
        None, description="Fecha último documento emitido"
    )

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "ruc": "80016875-4",
                "dv": "4",
                "razon_social": "MI EMPRESA S.A.",
                "nombre_fantasia": "Mi Empresa",
                "direccion": "Av. Mariscal López 1234",
                "ciudad": "Asunción",
                "departamento": "11",
                "departamento_nombre": "Central",
                "telefono": "021-555123",
                "email": "facturacion@miempresa.com.py",
                "ambiente_sifen": "test",
                "establecimiento": "001",
                "punto_expedicion": "001",
                "is_active": True,
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:30:00",
                "user_id": 1,
                "documentos_count": 156,
                "ultimo_documento": "2025-01-15T09:15:00"
            }
        }


class EmpresaListDTO(BaseModel):
    """
    DTO para elemento en lista de empresas.

    Versión compacta de EmpresaResponseDTO para listados
    que requieren menos información por performance.

    Examples:
        ```python
        # GET /api/v1/empresas response (lista)
        empresas_list = [
            EmpresaListDTO(
                id=1,
                ruc="80016875-5",
                razon_social="MI EMPRESA S.A.",
                is_active=True,
                ambiente_sifen="test"
            )
        ]
        ```
    """

    id: int = Field(..., description="ID único de la empresa")

    ruc: str = Field(..., description="RUC Paraguay")

    razon_social: str = Field(..., description="Razón social")

    nombre_fantasia: Optional[str] = Field(
        None, description="Nombre comercial"
    )

    ciudad: str = Field(..., description="Ciudad")

    ambiente_sifen: str = Field(..., description="Ambiente SIFEN")

    is_active: bool = Field(..., description="Si está activa")

    created_at: datetime = Field(..., description="Fecha de creación")

    documentos_count: Optional[int] = Field(
        None, description="Total documentos"
    )

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "ruc": "80016875-4",
                "razon_social": "MI EMPRESA S.A.",
                "nombre_fantasia": "Mi Empresa",
                "ciudad": "Asunción",
                "ambiente_sifen": "test",
                "is_active": True,
                "created_at": "2025-01-15T10:30:00",
                "documentos_count": 156
            }
        }


# ===============================================
# DTOs ESPECIALIZADOS
# ===============================================

class EmpresaConfigSifenDTO(BaseModel):
    """
    DTO para configuración específica SIFEN.

    Configuración avanzada para emisión de documentos
    electrónicos y integración con SET Paraguay.

    Examples:
        ```python
        # PUT /api/v1/empresas/{id}/sifen-config
        config_data = EmpresaConfigSifenDTO(
            ambiente_sifen="production",
            establecimiento="002",
            punto_expedicion="003",
            certificado_activo=True
        )
        ```
    """

    ambiente_sifen: AmbienteSifenEnum = Field(
        ...,
        description="Ambiente SIFEN (test/production)"
    )

    establecimiento: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Código establecimiento (001-999)"
    )

    punto_expedicion: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Punto de expedición (001-999)"
    )

    # Configuraciones adicionales SIFEN
    certificado_activo: bool = Field(
        default=False,
        description="Si tiene certificado digital activo"
    )

    ultimo_numero_usado: Optional[str] = Field(
        None,
        description="Último número de documento usado"
    )

    timbrado_vigente: Optional[str] = Field(
        None,
        description="Timbrado SET vigente"
    )

    fecha_inicio_timbrado: Optional[datetime] = Field(
        None,
        description="Inicio vigencia timbrado"
    )

    fecha_fin_timbrado: Optional[datetime] = Field(
        None,
        description="Fin vigencia timbrado"
    )

    @validator('establecimiento', 'punto_expedicion')
    def validate_codigo_sifen(cls, v, values):
        return EmpresaCreateDTO.validate_codigo_sifen(v)  # type: ignore

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "ambiente_sifen": "production",
                "establecimiento": "002",
                "punto_expedicion": "001",
                "certificado_activo": True,
                "ultimo_numero_usado": "002-001-0000156",
                "timbrado_vigente": "12345678",
                "fecha_inicio_timbrado": "2025-01-01T00:00:00",
                "fecha_fin_timbrado": "2025-12-31T23:59:59"
            }
        }


class EmpresaStatsDTO(BaseModel):
    """
    DTO para estadísticas de empresa.

    Métricas y estadísticas de emisión de documentos
    útiles para dashboards y reportes.

    Examples:
        ```python
        # GET /api/v1/empresas/{id}/stats response
        empresa_stats = EmpresaStatsDTO(
            empresa_id=1,
            documentos_totales=156,
            facturas_mes=23,
            aprobadas_sifen=145,
            rechazadas_sifen=11
        )
        ```
    """

    empresa_id: int = Field(..., description="ID de la empresa")

    # === CONTADORES GENERALES ===
    documentos_totales: int = Field(
        default=0,
        description="Total documentos emitidos"
    )

    facturas_mes: int = Field(
        default=0,
        description="Facturas emitidas este mes"
    )

    # === ESTADO SIFEN ===
    aprobadas_sifen: int = Field(
        default=0,
        description="Documentos aprobados por SIFEN"
    )

    rechazadas_sifen: int = Field(
        default=0,
        description="Documentos rechazados por SIFEN"
    )

    pendientes_sifen: int = Field(
        default=0,
        description="Documentos pendientes en SIFEN"
    )

    # === MÉTRICAS TIEMPO ===
    ultimo_documento: Optional[datetime] = Field(
        None,
        description="Fecha último documento emitido"
    )

    promedio_documentos_dia: float = Field(
        default=0.0,
        description="Promedio documentos por día"
    )

    # === MONTOS ===
    monto_total_mes: Optional[float] = Field(
        None,
        description="Monto total facturado este mes (Guaraníes)"
    )

    monto_promedio_documento: Optional[float] = Field(
        None,
        description="Monto promedio por documento (Guaraníes)"
    )

    class Config:
        schema_extra = {
            "example": {
                "empresa_id": 1,
                "documentos_totales": 156,
                "facturas_mes": 23,
                "aprobadas_sifen": 145,
                "rechazadas_sifen": 11,
                "pendientes_sifen": 0,
                "ultimo_documento": "2025-01-15T10:30:00",
                "promedio_documentos_dia": 5.2,
                "monto_total_mes": 45000000.0,
                "monto_promedio_documento": 1956521.0
            }
        }


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    # === ENUMS ===
    "AmbienteSifenEnum",

    # === DTOs DE ENTRADA ===
    "EmpresaCreateDTO",
    "EmpresaUpdateDTO",

    # === DTOs DE SALIDA ===
    "EmpresaResponseDTO",
    "EmpresaListDTO",

    # === DTOs ESPECIALIZADOS ===
    "EmpresaConfigSifenDTO",
    "EmpresaStatsDTO"
]
