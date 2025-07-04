# ===============================================
# ARCHIVO: backend/app/repositories/documento/document_types_t4.py
# PROPÓSITO: Mixin para operaciones específicas de Autofacturas Electrónicas (AFE - Tipo 4)
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para operaciones específicas de Autofacturas Electrónicas (AFE - Tipo 4).

Este módulo implementa funcionalidades especializadas para el manejo de autofacturas
electrónicas, incluyendo:
- Creación con validaciones específicas de autofacturas
- Manejo de datos de importación y vendedores extranjeros
- Validaciones de conformidad para operaciones AFE
- Búsquedas optimizadas para autofacturas
- Estadísticas específicas de importaciones

Características principales:
- Validación de emisor = receptor (crítico en AFE)
- Manejo de vendedores extranjeros y no contribuyentes
- Datos geográficos completos obligatorios
- Soporte para monedas extranjeras (USD, EUR)
- Integración con datos de importación/aduana

Casos de uso típicos:
- Importaciones de mercaderías (vendedor extranjero)
- Compras a no contribuyentes nacionales
- Operaciones donde el receptor debe emitir la factura

Clase principal:
- DocumentTypesT4Mixin: Mixin especializado para autofacturas electrónicas
"""

from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime, date, timedelta
from decimal import Decimal
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
    AutofacturaElectronica,
    TipoDocumentoSifenEnum,
    EstadoDocumentoSifenEnum,
    MonedaSifenEnum,
    TipoOperacionSifenEnum
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
    validate_autofactura_data,
    get_documents_by_type_and_criteria,
    calculate_totals_from_items,
    create_items_for_document,
    link_import_data
)

# Type hints para Pylance
if TYPE_CHECKING:
    from ..base import DocumentoRepositoryBase

logger = get_logger(__name__)

# ===============================================
# CONFIGURACIONES ESPECÍFICAS PARA AUTOFACTURAS
# ===============================================

# Defaults específicos para autofacturas electrónicas
AUTOFACTURA_DEFAULTS = {
    "tipo_documento": "4",
    "tipo_operacion": "3",  # Importación (típico para AFE)
    "condicion_operacion": "1",  # Contado
    "moneda": "USD",  # USD típico para importaciones
    "tipo_emision": "1",  # Normal
    "tipo_cambio": Decimal("7300.0000")  # Aproximado PYG/USD
}

# Naturalezas de vendedor válidas para AFE
NATURALEZAS_VENDEDOR_VALIDAS = {
    "1": "No contribuyente nacional",
    "2": "Extranjero"
}

# Tipos de documento de identidad para vendedores AFE
TIPOS_DOCUMENTO_VENDEDOR = {
    "1": "Cédula de identidad",
    "2": "Pasaporte",
    "3": "Otros documentos de identidad"
}

# Monedas típicas para importaciones
MONEDAS_IMPORTACION = ["USD", "EUR", "BRL", "ARS"]

# Campos geográficos obligatorios para vendedor AFE
CAMPOS_GEOGRAFICOS_OBLIGATORIOS = [
    "codigo_departamento_vendedor",
    "descripcion_departamento_vendedor",
    "codigo_distrito_vendedor",
    "descripcion_distrito_vendedor",
    "codigo_ciudad_vendedor",
    "descripcion_ciudad_vendedor",
    "codigo_departamento_transaccion",
    "descripcion_departamento_transaccion",
    "codigo_distrito_transaccion",
    "descripcion_distrito_transaccion",
    "codigo_ciudad_transaccion",
    "descripcion_ciudad_transaccion"
]

# ===============================================
# MIXIN PRINCIPAL
# ===============================================


class DocumentTypesT4Mixin:
    """
    Mixin para operaciones específicas de Autofacturas Electrónicas (AFE - Tipo 4).

    Proporciona métodos especializados para el manejo de autofacturas electrónicas:
    - Creación con validaciones específicas de AFE
    - Manejo de datos de importación
    - Validaciones de vendedores extranjeros/no contribuyentes
    - Búsquedas optimizadas para autofacturas
    - Estadísticas de importaciones específicas
    - Integración con SIFEN v150

    CARACTERÍSTICAS CRÍTICAS AFE:
    - Emisor = Receptor (mismo RUC obligatorio)
    - Vendedor original diferente al emisor/receptor
    - Datos geográficos completos obligatorios
    - Monedas extranjeras para importaciones

    Este mixin debe ser usado junto con DocumentoRepositoryBase para
    obtener funcionalidad completa de gestión de documentos.

    Example:
        ```python
        class DocumentoRepository(
            DocumentoRepositoryBase,
            DocumentTypesT4Mixin,
            # otros mixins...
        ):
            pass

        repo = DocumentoRepository(db)
        autofactura = repo.create_autofactura_electronica(data, items, import_data)
        ```
    """

    # Type hints para Pylance - estos métodos/atributos vienen del repository base
    if TYPE_CHECKING:
        db: Session
        model: type
        def create(self, obj_data, auto_generate_fields: bool = True): ...
        def get_by_id(self, entity_id: int): ...

    # ===============================================
    # MÉTODOS DE CREACIÓN ESPECÍFICOS
    # ===============================================

    def create_autofactura_electronica(self,
                                       autofactura_data: Union[DocumentoCreateDTO, Dict[str, Any]],
                                       items: List[Dict[str, Any]],
                                       vendedor_data: Dict[str, Any],
                                       import_data: Optional[Dict[str,
                                                                  Any]] = None,
                                       apply_defaults: bool = True,
                                       validate_geography: bool = True,
                                       auto_generate_cdc: bool = True) -> AutofacturaElectronica:
        """
        Crea una autofactura electrónica con validaciones específicas.

        Este método es el punto de entrada principal para crear autofacturas electrónicas,
        aplicando todas las validaciones y configuraciones específicas del tipo de documento.

        Args:
            autofactura_data: Datos básicos de la autofactura
            items: Lista de items/productos de la autofactura
            vendedor_data: Datos del vendedor original (extranjero/no contribuyente)
            import_data: Datos de importación (opcional, para aduanas)
            apply_defaults: Aplicar configuraciones por defecto específicas
            validate_geography: Validar datos geográficos completos
            auto_generate_cdc: Generar CDC automáticamente

        Returns:
            AutofacturaElectronica: Instancia de autofactura creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio AFE

        Example:
            ```python
            autofactura_data = {
                "establecimiento": "001",
                "punto_expedicion": "001",
                "numero_documento": "0000456",
                "cliente_id": 123,  # Cliente = Emisor en AFE
                "numero_timbrado": "12345678",
                "fecha_emision": date.today(),
                "moneda": "USD",
                "tipo_cambio": Decimal("7300.00")
            }

            vendedor_data = {
                "naturaleza_vendedor": "2",  # Extranjero
                "tipo_documento_vendedor": "2",  # Pasaporte
                "numero_documento_vendedor": "P123456789",
                "nombre_vendedor": "International Supplies Inc.",
                "direccion_vendedor": "Miami Trade Center 123",
                # ... datos geográficos completos
            }

            items = [{
                "descripcion": "Equipos electrónicos importados",
                "cantidad": 5,
                "precio_unitario": Decimal("800.00"),  # En USD
                "tipo_iva": "10"
            }]

            autofactura = repo.create_autofactura_electronica(
                autofactura_data, items, vendedor_data
            )
            ```
        """
        start_time = datetime.now()

        try:
            # 1. Preparar datos base
            if isinstance(autofactura_data, DocumentoCreateDTO):
                data_dict = autofactura_data.dict()
            else:
                data_dict = autofactura_data.copy()

            # 2. Aplicar defaults específicos de autofacturas
            if apply_defaults:
                self._apply_autofactura_defaults(data_dict)

            # 3. Validar estructura básica y reglas AFE
            self.validate_autofactura_data(data_dict, items, vendedor_data)

            # 4. Validar datos geográficos si se solicita
            if validate_geography:
                self.validate_geography_requirements(vendedor_data)

            # 5. Validar coherencia emisor = receptor
            self.validate_emisor_receptor_coherence(data_dict)

            # 6. Calcular totales automáticamente desde items
            calculate_totals_from_items(data_dict, items)

            # 7. Incluir datos del vendedor en el documento
            data_dict.update({
                "vendedor_naturaleza": vendedor_data.get("naturaleza_vendedor"),
                "vendedor_tipo_documento": vendedor_data.get("tipo_documento_vendedor"),
                "vendedor_numero_documento": vendedor_data.get("numero_documento_vendedor"),
                "vendedor_nombre": vendedor_data.get("nombre_vendedor"),
                "vendedor_direccion": vendedor_data.get("direccion_vendedor")
            })

            # 8. Crear documento usando método base del repository
            autofactura = getattr(self, 'create')(
                data_dict, auto_generate_fields=auto_generate_cdc)

            # 9. Crear items asociados a la autofactura
            if items:
                create_items_for_document(
                    getattr(self, 'db'), autofactura, items)

            # 10. Vincular datos de importación si se proporcionan
            if import_data:
                link_import_data(autofactura, import_data)

            # 11. Log de operación exitosa
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "create_autofactura_electronica", duration, 1)

            log_repository_operation("create_autofactura_electronica", "AutofacturaElectronica",
                                     getattr(autofactura, 'id', None), {
                                         "numero_completo": getattr(autofactura, 'numero_completo', None),
                                         "total_general": float(getattr(autofactura, 'total_general', 0)),
                                         "items_count": len(items),
                                         "moneda": getattr(autofactura, 'moneda', 'USD'),
                                         "vendedor_naturaleza": vendedor_data.get("naturaleza_vendedor")
                                     })

            return autofactura

        except (SifenValidationError, SifenBusinessLogicError, SifenDuplicateEntityError):
            # Re-raise errores de validación/negocio sin modificar
            getattr(self, 'db').rollback()
            raise
        except Exception as e:
            getattr(self, 'db').rollback()
            handle_repository_error(
                e, "create_autofactura_electronica", "AutofacturaElectronica")
            raise handle_database_exception(
                e, "create_autofactura_electronica")

    def create_autofactura_importacion(self,
                                       numero_documento: str,
                                       empresa_id: int,
                                       vendedor_extranjero: Dict[str, Any],
                                       items_importacion: List[Dict[str, Any]],
                                       datos_aduana: Optional[Dict[str,
                                                                   Any]] = None,
                                       moneda: str = "USD",
                                       tipo_cambio: Optional[Decimal] = None) -> AutofacturaElectronica:
        """
        Creación específica para autofacturas de importación.

        Método de conveniencia para crear autofacturas típicas de importación
        con vendedor extranjero y configuraciones optimizadas.

        Args:
            numero_documento: Número secuencial del documento
            empresa_id: ID de la empresa importadora (emisor = receptor)
            vendedor_extranjero: Datos del proveedor extranjero
            items_importacion: Items importados con códigos arancelarios
            datos_aduana: Información de aduana (opcional)
            moneda: Moneda de la operación (default: USD)
            tipo_cambio: Tipo de cambio a aplicar (opcional)

        Returns:
            AutofacturaElectronica: Autofactura de importación creada

        Example:
            ```python
            vendedor = {
                "naturaleza_vendedor": "2",  # Extranjero
                "nombre_vendedor": "International Tech Corp",
                "numero_documento_vendedor": "P987654321",
                "direccion_vendedor": "Silicon Valley, CA, USA",
                # ... datos geográficos completos
            }

            items = [{
                "descripcion": "Laptop Dell XPS 13",
                "cantidad": 10,
                "precio_unitario": Decimal("1200.00"),
                "codigo_arancelario": "8471301000",
                "tipo_iva": "10"
            }]

            autofactura = repo.create_autofactura_importacion(
                numero_documento="0000789",
                empresa_id=1,
                vendedor_extranjero=vendedor,
                items_importacion=items
            )
            ```
        """
        # TODO: Obtener datos de empresa y timbrado activo
        autofactura_data = {
            "establecimiento": "001",  # TODO: Desde configuración empresa
            "punto_expedicion": "001",  # TODO: Desde configuración empresa
            "numero_documento": numero_documento,
            "cliente_id": empresa_id,  # En AFE: cliente = empresa emisora
            "empresa_id": empresa_id,
            "numero_timbrado": "12345678",  # TODO: Desde timbrado activo
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),
            "timbrado_id": 1,  # TODO: Desde timbrado activo
            "moneda": moneda,
            "tipo_operacion": "3",  # Importación
            "condicion_operacion": "1"  # Contado típico
        }

        if tipo_cambio:
            autofactura_data["tipo_cambio"] = tipo_cambio

        # Asegurar datos geográficos mínimos para vendedor extranjero
        if "codigo_departamento_vendedor" not in vendedor_extranjero:
            # Asignar valores por defecto para vendor extranjero
            vendedor_extranjero.update({
                "naturaleza_vendedor": "2",  # Extranjero
                "tipo_documento_vendedor": "2",  # Pasaporte
                # Capital (transacción en Paraguay)
                "codigo_departamento_vendedor": "1",
                "descripcion_departamento_vendedor": "CAPITAL",
                "codigo_distrito_vendedor": "1",
                "descripcion_distrito_vendedor": "ASUNCION",
                "codigo_ciudad_vendedor": "1",
                "descripcion_ciudad_vendedor": "ASUNCION",
                "codigo_departamento_transaccion": "1",
                "descripcion_departamento_transaccion": "CAPITAL",
                "codigo_distrito_transaccion": "1",
                "descripcion_distrito_transaccion": "ASUNCION",
                "codigo_ciudad_transaccion": "1",
                "descripcion_ciudad_transaccion": "ASUNCION"
            })

        return self.create_autofactura_electronica(
            autofactura_data=autofactura_data,
            items=items_importacion,
            vendedor_data=vendedor_extranjero,
            import_data=datos_aduana,
            apply_defaults=True,
            validate_geography=True,
            auto_generate_cdc=True
        )

    def create_autofactura_no_contribuyente(self,
                                            numero_documento: str,
                                            empresa_id: int,
                                            vendedor_nacional: Dict[str, Any],
                                            items: List[Dict[str, Any]],
                                            moneda: str = "PYG") -> AutofacturaElectronica:
        """
        Creación específica para autofacturas con vendedor no contribuyente nacional.

        Args:
            numero_documento: Número secuencial del documento
            empresa_id: ID de la empresa compradora
            vendedor_nacional: Datos del vendedor no contribuyente
            items: Items de la compra
            moneda: Moneda de la operación (default: PYG)

        Returns:
            AutofacturaElectronica: Autofactura creada
        """
        autofactura_data = {
            "establecimiento": "001",
            "punto_expedicion": "001",
            "numero_documento": numero_documento,
            "cliente_id": empresa_id,
            "empresa_id": empresa_id,
            "numero_timbrado": "12345678",  # TODO: Desde timbrado activo
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),
            "timbrado_id": 1,
            "moneda": moneda,
            "tipo_operacion": "1",  # Venta (nacional)
            "condicion_operacion": "1"
        }

        # Asegurar que el vendedor es no contribuyente
        vendedor_nacional["naturaleza_vendedor"] = "1"  # No contribuyente
        if "tipo_documento_vendedor" not in vendedor_nacional:
            vendedor_nacional["tipo_documento_vendedor"] = "1"  # Cédula

        return self.create_autofactura_electronica(
            autofactura_data=autofactura_data,
            items=items,
            vendedor_data=vendedor_nacional,
            apply_defaults=True,
            validate_geography=True
        )

    # ===============================================
    # VALIDACIONES ESPECÍFICAS
    # ===============================================

    def validate_autofactura_data(self,
                                  autofactura_data: Dict[str, Any],
                                  items: List[Dict[str, Any]],
                                  vendedor_data: Dict[str, Any]) -> None:
        """
        Validaciones comprehensivas específicas para autofacturas electrónicas.

        Aplica todas las validaciones requeridas para una autofactura según
        las normativas SIFEN y reglas de negocio específicas de AFE.

        Args:
            autofactura_data: Datos de la autofactura a validar
            items: Items de la autofactura a validar
            vendedor_data: Datos del vendedor original a validar

        Raises:
            SifenValidationError: Si alguna validación falla

        Example:
            ```python
            try:
                repo.validate_autofactura_data(afe_data, items, vendedor)
                print("Datos AFE válidos")
            except SifenValidationError as e:
                print(f"Error de validación AFE: {e.message}")
            ```
        """
        # Usar validación de auxiliares como base
        validate_autofactura_data(autofactura_data, vendedor_data)

        # Validaciones adicionales específicas de AFE

        # 1. Items obligatorios
        if not items or len(items) == 0:
            raise SifenValidationError(
                "Autofacturas deben tener al menos 1 item",
                field="items"
            )

        # 2. Validar cada item
        for i, item in enumerate(items):
            self._validate_autofactura_item(item, i)

        # 3. Validar naturaleza del vendedor
        naturaleza = vendedor_data.get("naturaleza_vendedor")
        if naturaleza not in NATURALEZAS_VENDEDOR_VALIDAS:
            raise SifenValidationError(
                f"Naturaleza de vendedor debe ser una de: {list(NATURALEZAS_VENDEDOR_VALIDAS.keys())}",
                field="naturaleza_vendedor",
                value=naturaleza
            )

        # 4. Validar tipo de documento del vendedor
        tipo_doc = vendedor_data.get("tipo_documento_vendedor")
        if tipo_doc not in TIPOS_DOCUMENTO_VENDEDOR:
            raise SifenValidationError(
                f"Tipo de documento de vendedor debe ser uno de: {list(TIPOS_DOCUMENTO_VENDEDOR.keys())}",
                field="tipo_documento_vendedor",
                value=tipo_doc
            )

        # 5. Validar moneda para extranjeros
        if naturaleza == "2" and autofactura_data.get("moneda") == "PYG":
            logger.warning(
                "Autofactura con vendedor extranjero en PYG - "
                "considere usar moneda extranjera (USD, EUR, etc.)"
            )

        # 6. Validar tipo de operación para AFE
        tipo_operacion = autofactura_data.get("tipo_operacion", "3")
        if tipo_operacion not in ["1", "3"]:  # Venta o Importación
            raise SifenValidationError(
                "Autofacturas típicamente son tipo Venta (1) o Importación (3)",
                field="tipo_operacion",
                value=tipo_operacion
            )

    def validate_geography_requirements(self, vendedor_data: Dict[str, Any]) -> None:
        """
        Valida que los datos geográficos del vendedor estén completos.

        AFE requiere datos geográficos completos tanto del vendedor
        como del lugar de la transacción según SIFEN.

        Args:
            vendedor_data: Datos del vendedor a validar

        Raises:
            SifenValidationError: Si faltan datos geográficos obligatorios
        """
        missing_fields = []

        for field in CAMPOS_GEOGRAFICOS_OBLIGATORIOS:
            if field not in vendedor_data or not vendedor_data[field]:
                missing_fields.append(field)

        if missing_fields:
            raise SifenValidationError(
                f"Campos geográficos obligatorios faltantes en vendedor AFE: {', '.join(missing_fields)}",
                field="vendedor_data",
                details={"missing_fields": missing_fields}
            )

    def validate_emisor_receptor_coherence(self, autofactura_data: Dict[str, Any]) -> None:
        """
        Valida que emisor y receptor sean la misma entidad (crítico en AFE).

        En autofacturas, el emisor y receptor deben ser la misma empresa,
        ya que la empresa se "autofactura" por compras a no contribuyentes o extranjeros.

        Args:
            autofactura_data: Datos de la autofactura

        Raises:
            SifenBusinessLogicError: Si emisor != receptor
        """
        empresa_id = autofactura_data.get("empresa_id")
        cliente_id = autofactura_data.get("cliente_id")

        if empresa_id != cliente_id:
            raise SifenBusinessLogicError(
                "En autofacturas, emisor y receptor deben ser la misma empresa",
                details={
                    "empresa_id": empresa_id,
                    "cliente_id": cliente_id,
                    "sugerencia": "Asigne cliente_id = empresa_id para AFE"
                }
            )

    def validate_import_requirements(self,
                                     vendedor_data: Dict[str, Any],
                                     items: List[Dict[str, Any]],
                                     import_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Valida requisitos específicos para importaciones.

        Args:
            vendedor_data: Datos del vendedor extranjero
            items: Items importados
            import_data: Datos de importación/aduana (opcional)

        Raises:
            SifenValidationError: Si faltan requisitos de importación
        """
        # Validar vendedor extranjero
        if vendedor_data.get("naturaleza_vendedor") != "2":
            raise SifenValidationError(
                "Para importaciones, el vendedor debe ser extranjero (naturaleza=2)",
                field="naturaleza_vendedor",
                value=vendedor_data.get("naturaleza_vendedor")
            )

        # Validar códigos arancelarios en items (recomendado)
        for i, item in enumerate(items):
            if "codigo_arancelario" not in item:
                logger.warning(
                    f"Item {i+1} sin código arancelario - "
                    "recomendado para importaciones"
                )

        # Validar datos de aduana si se proporcionan
        if import_data:
            required_import_fields = ["declaracion_importacion", "aduana"]
            for field in required_import_fields:
                if field not in import_data:
                    logger.warning(
                        f"Campo de importación recomendado: {field}"
                    )

    # ===============================================
    # BÚSQUEDAS ESPECIALIZADAS
    # ===============================================

    def get_autofacturas_by_criteria(self,
                                     empresa_id: int,
                                     fecha_desde: Optional[date] = None,
                                     fecha_hasta: Optional[date] = None,
                                     naturaleza_vendedor: Optional[str] = None,
                                     moneda: Optional[str] = None,
                                     monto_minimo: Optional[Decimal] = None,
                                     monto_maximo: Optional[Decimal] = None,
                                     estados: Optional[List[str]] = None,
                                     solo_importaciones: bool = False,
                                     include_items: bool = False,
                                     limit: Optional[int] = None,
                                     offset: int = 0) -> List[AutofacturaElectronica]:
        """
        Búsqueda avanzada de autofacturas con múltiples criterios.

        Permite filtrar autofacturas por diversos criterios específicos del negocio,
        optimizado para consultas frecuentes en dashboards de importaciones.

        Args:
            empresa_id: ID de la empresa emisora/receptora
            fecha_desde: Fecha inicio del rango (opcional)
            fecha_hasta: Fecha fin del rango (opcional)
            naturaleza_vendedor: Naturaleza del vendedor (1=Nacional, 2=Extranjero)
            moneda: Filtrar por tipo de moneda (opcional)
            monto_minimo: Monto mínimo de la autofactura (opcional)
            monto_maximo: Monto máximo de la autofactura (opcional)
            estados: Lista de estados a incluir (opcional)
            solo_importaciones: Filtrar solo operaciones de importación
            include_items: Incluir items en el resultado (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[AutofacturaElectronica]: Lista de autofacturas que cumplen criterios

        Example:
            ```python
            # Importaciones del mes en USD
            autofacturas = repo.get_autofacturas_by_criteria(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31),
                naturaleza_vendedor="2",  # Extranjero
                moneda="USD",
                solo_importaciones=True,
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
            query = getattr(self, 'db').query(AutofacturaElectronica).filter(
                and_(
                    AutofacturaElectronica.tipo_documento == "4",
                    AutofacturaElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtros opcionales
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, AutofacturaElectronica.fecha_emision, fecha_desde, fecha_hasta)

            if monto_minimo or monto_maximo:
                query = build_amount_filter(
                    query, AutofacturaElectronica.total_general, monto_minimo, monto_maximo)

            if naturaleza_vendedor:
                query = query.filter(text("vendedor_naturaleza = :naturaleza")).params(
                    naturaleza=naturaleza_vendedor)

            if moneda:
                query = query.filter(AutofacturaElectronica.moneda == moneda)

            if estados:
                query = query.filter(text("estado IN :estados")).params(
                    estados=tuple(estados))

            if solo_importaciones:
                query = query.filter(
                    AutofacturaElectronica.tipo_operacion == "3")

            # Incluir items si se solicita
            if include_items:
                # TODO: Implementar cuando tabla de items esté disponible
                # query = query.options(joinedload(AutofacturaElectronica.items))
                pass

            # Aplicar límites y ordenamiento
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            autofacturas = query.order_by(
                desc(AutofacturaElectronica.fecha_emision)).offset(offset).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_autofacturas_by_criteria", duration, len(autofacturas))

            return autofacturas

        except Exception as e:
            handle_repository_error(
                e, "get_autofacturas_by_criteria", "AutofacturaElectronica")
            raise handle_database_exception(e, "get_autofacturas_by_criteria")

    def get_autofacturas_importacion(self,
                                     empresa_id: int,
                                     fecha_desde: Optional[date] = None,
                                     fecha_hasta: Optional[date] = None,
                                     moneda: str = "USD") -> List[AutofacturaElectronica]:
        """
        Obtiene autofacturas de importación específicamente.

        Args:
            empresa_id: ID de la empresa importadora
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)
            moneda: Moneda de importación (default: USD)

        Returns:
            List[AutofacturaElectronica]: Autofacturas de importación
        """
        return self.get_autofacturas_by_criteria(
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            naturaleza_vendedor="2",  # Extranjero
            moneda=moneda,
            solo_importaciones=True,
            estados=["aprobado", "aprobado_observacion"]
        )

    def get_autofacturas_by_vendor(self,
                                   empresa_id: int,
                                   vendedor_documento: str,
                                   fecha_desde: Optional[date] = None,
                                   fecha_hasta: Optional[date] = None) -> List[AutofacturaElectronica]:
        """
        Obtiene autofacturas por vendedor específico.

        Args:
            empresa_id: ID de la empresa
            vendedor_documento: Número de documento del vendedor
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)

        Returns:
            List[AutofacturaElectronica]: Autofacturas del vendedor
        """
        try:
            if not hasattr(self, 'db'):
                raise AttributeError(
                    "Este mixin requiere DocumentoRepositoryBase con atributo db")

            query = getattr(self, 'db').query(AutofacturaElectronica).filter(
                and_(
                    AutofacturaElectronica.tipo_documento == "4",
                    AutofacturaElectronica.empresa_id == empresa_id,
                    text("vendedor_numero_documento = :vendor_doc")
                )
            ).params(vendor_doc=vendedor_documento)

            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, AutofacturaElectronica.fecha_emision, fecha_desde, fecha_hasta)

            return query.order_by(desc(AutofacturaElectronica.fecha_emision)).all()

        except Exception as e:
            handle_repository_error(
                e, "get_autofacturas_by_vendor", "AutofacturaElectronica")
            raise handle_database_exception(e, "get_autofacturas_by_vendor")

    def get_autofacturas_by_currency(self,
                                     empresa_id: int,
                                     moneda: str,
                                     fecha_desde: Optional[date] = None,
                                     fecha_hasta: Optional[date] = None) -> List[AutofacturaElectronica]:
        """
        Filtra autofacturas por moneda específica.

        Args:
            empresa_id: ID de la empresa
            moneda: Código de moneda (USD, EUR, etc.)
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)

        Returns:
            List[AutofacturaElectronica]: Autofacturas en la moneda especificada
        """
        return self.get_autofacturas_by_criteria(
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            moneda=moneda
        )

    # ===============================================
    # REPORTES Y ESTADÍSTICAS
    # ===============================================

    def get_autofactura_stats(self,
                              empresa_id: int,
                              fecha_desde: Optional[date] = None,
                              fecha_hasta: Optional[date] = None,
                              periodo: str = "monthly") -> Dict[str, Any]:
        """
        Estadísticas específicas de autofacturas para una empresa.

        Genera métricas detalladas de autofacturas para reportes de importaciones
        y análisis de proveedores.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período (opcional)
            fecha_hasta: Fecha fin del período (opcional)
            periodo: Tipo de período para agregación (daily, weekly, monthly)

        Returns:
            Dict[str, Any]: Estadísticas detalladas de autofacturas

        Example:
            ```python
            stats = repo.get_autofactura_stats(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            print(f"Total importado: {stats['totales']['monto_total_importado']}")
            ```
        """
        start_time = datetime.now()

        try:
            if not hasattr(self, 'db'):
                raise AttributeError(
                    "Este mixin requiere DocumentoRepositoryBase con atributo db")

            # Construir query base
            query = getattr(self, 'db').query(AutofacturaElectronica).filter(
                and_(
                    AutofacturaElectronica.tipo_documento == "4",
                    AutofacturaElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtro de fechas
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, AutofacturaElectronica.fecha_emision, fecha_desde, fecha_hasta)

            # Obtener todas las autofacturas del período
            autofacturas = query.all()

            # Calcular estadísticas básicas
            total_autofacturas = len(autofacturas)

            if total_autofacturas == 0:
                return self._get_empty_autofactura_stats()

            # Calcular totales
            monto_total = sum(getattr(afe, 'total_general', Decimal("0"))
                              for afe in autofacturas)
            promedio_autofactura = monto_total / \
                total_autofacturas if total_autofacturas > 0 else Decimal("0")

            # Separar por naturaleza de vendedor
            importaciones = [afe for afe in autofacturas if getattr(
                afe, 'vendedor_naturaleza', '') == "2"]
            no_contribuyentes = [afe for afe in autofacturas if getattr(
                afe, 'vendedor_naturaleza', '') == "1"]

            # Calcular montos por tipo
            monto_importaciones = sum(
                getattr(afe, 'total_general', Decimal("0")) for afe in importaciones)
            monto_no_contribuyentes = sum(
                getattr(afe, 'total_general', Decimal("0")) for afe in no_contribuyentes)

            # Análisis por moneda
            distribución_monedas = {}
            for afe in autofacturas:
                moneda = getattr(afe, 'moneda', 'PYG')
                if moneda not in distribución_monedas:
                    distribución_monedas[moneda] = {
                        "cantidad": 0, "monto": Decimal("0")}
                distribución_monedas[moneda]["cantidad"] += 1
                distribución_monedas[moneda]["monto"] += getattr(
                    afe, 'total_general', Decimal("0"))

            # Contar por estado
            autofacturas_por_estado = {}
            for afe in autofacturas:
                estado = getattr(afe, 'estado', 'unknown')
                autofacturas_por_estado[estado] = autofacturas_por_estado.get(
                    estado, 0) + 1

            # Obtener proveedores únicos
            proveedores_unicos = len(set(getattr(afe, 'vendedor_numero_documento', '')
                                     for afe in autofacturas if getattr(afe, 'vendedor_numero_documento', '')))

            # Agregación por período si se solicita
            datos_por_periodo = {}
            if periodo and autofacturas:
                datos_periodo = [
                    {
                        "fecha": getattr(afe, 'fecha_emision', date.today()),
                        "monto": float(getattr(afe, 'total_general', 0))
                    }
                    for afe in autofacturas
                ]
                datos_por_periodo = aggregate_by_period(
                    datos_periodo, "fecha", "monto", periodo)

            # Estadísticas de performance
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_autofactura_stats", duration, total_autofacturas)

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                    "tipo_periodo": periodo
                },
                "totales": {
                    "total_autofacturas": total_autofacturas,
                    "monto_total": float(monto_total),
                    "promedio_por_autofactura": float(promedio_autofactura),
                    "monto_total_importaciones": float(monto_importaciones),
                    "monto_total_no_contribuyentes": float(monto_no_contribuyentes)
                },
                "distribucion_tipo": {
                    "importaciones": len(importaciones),
                    "no_contribuyentes": len(no_contribuyentes),
                    "porcentaje_importaciones": calculate_percentage(len(importaciones), total_autofacturas),
                    "porcentaje_no_contribuyentes": calculate_percentage(len(no_contribuyentes), total_autofacturas)
                },
                "proveedores": {
                    "proveedores_unicos": proveedores_unicos,
                    "promedio_autofacturas_por_proveedor": round(total_autofacturas / proveedores_unicos, 2) if proveedores_unicos > 0 else 0
                },
                "distribución_monedas": {
                    moneda: {
                        "cantidad": datos["cantidad"],
                        "monto": float(datos["monto"]),
                        "porcentaje": calculate_percentage(datos["cantidad"], total_autofacturas)
                    }
                    for moneda, datos in distribución_monedas.items()
                },
                "estados": autofacturas_por_estado,
                "datos_por_periodo": datos_por_periodo,
                "metadatos": {
                    "generado_en": datetime.now().isoformat(),
                    "tiempo_procesamiento": round(duration, 3)
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_autofactura_stats", "AutofacturaElectronica")
            raise handle_database_exception(e, "get_autofactura_stats")

    def get_import_summary(self,
                           empresa_id: int,
                           fecha_desde: date,
                           fecha_hasta: date) -> Dict[str, Any]:
        """
        Resumen de importaciones por período.

        Genera un resumen detallado de las importaciones realizadas
        mediante autofacturas para análisis de comercio exterior.

        Args:
            empresa_id: ID de la empresa importadora
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Resumen detallado de importaciones

        Example:
            ```python
            resumen = repo.get_import_summary(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            ```
        """
        try:
            # Obtener solo importaciones (vendedor extranjero)
            importaciones = self.get_autofacturas_importacion(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )

            # Análisis por moneda extranjera
            análisis_monedas = {}
            for importacion in importaciones:
                moneda = getattr(importacion, 'moneda', 'USD')
                monto = getattr(importacion, 'total_general', Decimal("0"))
                tipo_cambio = getattr(importacion, 'tipo_cambio', Decimal("1"))

                if moneda not in análisis_monedas:
                    análisis_monedas[moneda] = {
                        "cantidad_operaciones": 0,
                        "monto_moneda_extranjera": Decimal("0"),
                        "monto_guaranies": Decimal("0"),
                        "tipo_cambio_promedio": Decimal("0")
                    }

                análisis_monedas[moneda]["cantidad_operaciones"] += 1
                análisis_monedas[moneda]["monto_guaranies"] += monto

                # Calcular monto en moneda extranjera
                if moneda != "PYG":
                    monto_extranjera = monto / \
                        tipo_cambio if tipo_cambio > 0 else Decimal("0")
                    análisis_monedas[moneda]["monto_moneda_extranjera"] += monto_extranjera

            # Calcular tipo de cambio promedio ponderado
            for moneda, datos in análisis_monedas.items():
                if datos["cantidad_operaciones"] > 0 and datos["monto_moneda_extranjera"] > 0:
                    datos["tipo_cambio_promedio"] = datos["monto_guaranies"] / \
                        datos["monto_moneda_extranjera"]

            # Análisis de proveedores
            proveedores = {}
            for importacion in importaciones:
                proveedor = getattr(
                    importacion, 'vendedor_nombre', 'Desconocido')
                monto = getattr(importacion, 'total_general', Decimal("0"))

                if proveedor not in proveedores:
                    proveedores[proveedor] = {
                        "operaciones": 0,
                        "monto_total": Decimal("0")
                    }

                proveedores[proveedor]["operaciones"] += 1
                proveedores[proveedor]["monto_total"] += monto

            # Top 5 proveedores por monto
            top_proveedores = sorted(
                proveedores.items(),
                key=lambda x: x[1]["monto_total"],
                reverse=True
            )[:5]

            # Totales generales
            total_importaciones = len(importaciones)
            monto_total_importado = sum(
                getattr(imp, 'total_general', Decimal("0")) for imp in importaciones)

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "dias": (fecha_hasta - fecha_desde).days + 1
                },
                "resumen_general": {
                    "total_importaciones": total_importaciones,
                    "monto_total_importado_pyg": float(monto_total_importado),
                    "promedio_por_importacion": float(monto_total_importado / total_importaciones) if total_importaciones > 0 else 0.0,
                    "proveedores_unicos": len(proveedores)
                },
                "análisis_por_moneda": {
                    moneda: {
                        "cantidad_operaciones": datos["cantidad_operaciones"],
                        "monto_moneda_extranjera": float(datos["monto_moneda_extranjera"]),
                        "monto_guaranies": float(datos["monto_guaranies"]),
                        "tipo_cambio_promedio": float(datos["tipo_cambio_promedio"])
                    }
                    for moneda, datos in análisis_monedas.items()
                },
                "top_proveedores": [
                    {
                        "nombre": proveedor,
                        "operaciones": datos["operaciones"],
                        "monto_total": float(datos["monto_total"])
                    }
                    for proveedor, datos in top_proveedores
                ],
                "promedios": {
                    "importaciones_por_dia": round(total_importaciones / ((fecha_hasta - fecha_desde).days + 1), 2),
                    "monto_diario": float(monto_total_importado / ((fecha_hasta - fecha_desde).days + 1))
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_import_summary", "AutofacturaElectronica")
            raise handle_database_exception(e, "get_import_summary")

    def get_vendor_analysis(self,
                            empresa_id: int,
                            meses_atras: int = 12) -> Dict[str, Any]:
        """
        Análisis de proveedores y tendencias de importación.

        Analiza los proveedores más frecuentes y las tendencias de compras
        para optimización de la cadena de suministro.

        Args:
            empresa_id: ID de la empresa
            meses_atras: Número de meses hacia atrás a analizar

        Returns:
            Dict[str, Any]: Análisis de proveedores y tendencias
        """
        try:
            # Calcular fechas del análisis
            fecha_fin = date.today()
            fecha_inicio = fecha_fin.replace(
                day=1) - timedelta(days=meses_atras*30)

            # Obtener autofacturas del período
            autofacturas = self.get_autofacturas_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_inicio,
                fecha_hasta=fecha_fin,
                estados=["aprobado", "aprobado_observacion"]
            )

            # Análisis por proveedor
            proveedores = {}
            for afe in autofacturas:
                proveedor_id = getattr(
                    afe, 'vendedor_numero_documento', 'UNKNOWN')
                proveedor_nombre = getattr(
                    afe, 'vendedor_nombre', 'Desconocido')
                naturaleza = getattr(afe, 'vendedor_naturaleza', '1')
                monto = getattr(afe, 'total_general', Decimal("0"))
                fecha = getattr(afe, 'fecha_emision', date.today())

                if proveedor_id not in proveedores:
                    proveedores[proveedor_id] = {
                        "nombre": proveedor_nombre,
                        "naturaleza": "Extranjero" if naturaleza == "2" else "Nacional",
                        "operaciones": 0,
                        "monto_total": Decimal("0"),
                        "primera_operacion": fecha,
                        "ultima_operacion": fecha,
                        "monedas_usadas": set()
                    }

                proveedor_data = proveedores[proveedor_id]
                proveedor_data["operaciones"] += 1
                proveedor_data["monto_total"] += monto
                proveedor_data["primera_operacion"] = min(
                    proveedor_data["primera_operacion"], fecha)
                proveedor_data["ultima_operacion"] = max(
                    proveedor_data["ultima_operacion"], fecha)
                proveedor_data["monedas_usadas"].add(
                    getattr(afe, 'moneda', 'PYG'))

            # Convertir sets a listas para serialización
            for proveedor_data in proveedores.values():
                proveedor_data["monedas_usadas"] = list(
                    proveedor_data["monedas_usadas"])

            # Top proveedores por diferentes criterios
            top_por_monto = sorted(
                proveedores.items(),
                key=lambda x: x[1]["monto_total"],
                reverse=True
            )[:10]

            top_por_frecuencia = sorted(
                proveedores.items(),
                key=lambda x: x[1]["operaciones"],
                reverse=True
            )[:10]

            # Análisis de tendencias
            extranjeros = [p for p in proveedores.values(
            ) if p["naturaleza"] == "Extranjero"]
            nacionales = [p for p in proveedores.values(
            ) if p["naturaleza"] == "Nacional"]

            return {
                "periodo_analisis": {
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": fecha_fin.isoformat(),
                    "meses_analizados": meses_atras
                },
                "resumen_proveedores": {
                    "total_proveedores": len(proveedores),
                    "proveedores_extranjeros": len(extranjeros),
                    "proveedores_nacionales": len(nacionales),
                    "total_operaciones": len(autofacturas)
                },
                "top_proveedores_por_monto": [
                    {
                        "documento": doc,
                        "nombre": datos["nombre"],
                        "naturaleza": datos["naturaleza"],
                        "monto_total": float(datos["monto_total"]),
                        "operaciones": datos["operaciones"],
                        "monto_promedio": float(datos["monto_total"] / datos["operaciones"]),
                        "monedas": datos["monedas_usadas"]
                    }
                    for doc, datos in top_por_monto
                ],
                "top_proveedores_por_frecuencia": [
                    {
                        "documento": doc,
                        "nombre": datos["nombre"],
                        "naturaleza": datos["naturaleza"],
                        "operaciones": datos["operaciones"],
                        "monto_total": float(datos["monto_total"]),
                        "frecuencia_mensual": round(datos["operaciones"] / meses_atras, 2)
                    }
                    for doc, datos in top_por_frecuencia
                ],
                "análisis_concentración": {
                    "top_5_representa_pct": calculate_percentage(
                        sum(datos["monto_total"]
                            for _, datos in top_por_monto[:5]),
                        sum(datos["monto_total"]
                            for _, datos in proveedores.items())
                    ),
                    "proveedor_principal_pct": calculate_percentage(
                        float(top_por_monto[0][1]["monto_total"]
                              ) if top_por_monto else 0.0,
                        float(sum(datos["monto_total"]
                              for _, datos in proveedores.items()))
                    ) if top_por_monto else 0.0
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_vendor_analysis", "AutofacturaElectronica")
            raise handle_database_exception(e, "get_vendor_analysis")

    # ===============================================
    # HELPERS INTERNOS
    # ===============================================

    def _apply_autofactura_defaults(self, data: Dict[str, Any]) -> None:
        """
        Aplica configuraciones por defecto específicas de autofacturas.

        Args:
            data: Diccionario de datos a modificar in-place
        """
        # Aplicar defaults base desde auxiliares
        apply_default_config(data, "4")  # Tipo 4 = Autofactura

        # Aplicar defaults específicos adicionales
        for key, default_value in AUTOFACTURA_DEFAULTS.items():
            if key not in data or data[key] is None:
                data[key] = default_value

        # Configuraciones especiales
        if "fecha_emision" not in data:
            data["fecha_emision"] = date.today()

        if "estado" not in data:
            data["estado"] = EstadoDocumentoSifenEnum.BORRADOR.value

        # Asegurar coherencia emisor = receptor para AFE
        if "empresa_id" in data and "cliente_id" not in data:
            data["cliente_id"] = data["empresa_id"]

    def _validate_autofactura_item(self, item: Dict[str, Any], index: int) -> None:
        """
        Valida un item individual de la autofactura.

        Args:
            item: Datos del item a validar
            index: Índice del item en la lista

        Raises:
            SifenValidationError: Si el item no es válido
        """
        # Campos requeridos en items de autofactura
        required_fields = ["descripcion", "cantidad", "precio_unitario"]

        for field in required_fields:
            if field not in item or item[field] is None:
                raise SifenValidationError(
                    f"Campo requerido en item {index + 1}: {field}",
                    field=f"items[{index}].{field}"
                )

        # Validar cantidad positiva
        try:
            cantidad = Decimal(str(item["cantidad"]))
            if cantidad <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise SifenValidationError(
                f"Cantidad debe ser un número positivo en item {index + 1}",
                field=f"items[{index}].cantidad",
                value=item.get("cantidad")
            )

        # Validar precio unitario no negativo
        try:
            precio = Decimal(str(item["precio_unitario"]))
            if precio < 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise SifenValidationError(
                f"Precio unitario debe ser un número no negativo en item {index + 1}",
                field=f"items[{index}].precio_unitario",
                value=item.get("precio_unitario")
            )

        # Recomendar código arancelario para importaciones
        if "codigo_arancelario" not in item:
            logger.info(
                f"Item {index + 1} sin código arancelario - "
                "recomendado para autofacturas de importación"
            )

    def _get_empty_autofactura_stats(self) -> Dict[str, Any]:
        """
        Retorna estructura de estadísticas vacía para autofacturas.

        Returns:
            Dict[str, Any]: Estadísticas con valores en cero
        """
        return {
            "periodo": {
                "fecha_desde": None,
                "fecha_hasta": None,
                "tipo_periodo": "monthly"
            },
            "totales": {
                "total_autofacturas": 0,
                "monto_total": 0.0,
                "promedio_por_autofactura": 0.0,
                "monto_total_importaciones": 0.0,
                "monto_total_no_contribuyentes": 0.0
            },
            "distribucion_tipo": {
                "importaciones": 0,
                "no_contribuyentes": 0,
                "porcentaje_importaciones": 0.0,
                "porcentaje_no_contribuyentes": 0.0
            },
            "proveedores": {
                "proveedores_unicos": 0,
                "promedio_autofacturas_por_proveedor": 0.0
            },
            "distribución_monedas": {},
            "estados": {},
            "datos_por_periodo": {},
            "metadatos": {
                "generado_en": datetime.now().isoformat(),
                "tiempo_procesamiento": 0.0
            }
        }

    def _format_autofactura_response(self, autofactura: AutofacturaElectronica, include_details: bool = False) -> Dict[str, Any]:
        """
        Formatea respuesta con datos específicos de autofacturas.

        Args:
            autofactura: Instancia de autofactura a formatear
            include_details: Incluir detalles adicionales

        Returns:
            Dict[str, Any]: Autofactura formateada para respuesta
        """
        response = {
            "id": getattr(autofactura, 'id', None),
            "cdc": getattr(autofactura, 'cdc', ''),
            "numero_completo": getattr(autofactura, 'numero_completo', ''),
            "fecha_emision": getattr(autofactura, 'fecha_emision', date.today()).isoformat(),
            "empresa_id": getattr(autofactura, 'empresa_id', None),
            "total_general": float(getattr(autofactura, 'total_general', 0)),
            "moneda": getattr(autofactura, 'moneda', 'USD'),
            "tipo_cambio": float(getattr(autofactura, 'tipo_cambio', 1)),
            "estado": getattr(autofactura, 'estado', 'unknown'),
            "tipo_documento": "Autofactura Electrónica",
            "vendedor_nombre": getattr(autofactura, 'vendedor_nombre', ''),
            "vendedor_naturaleza": getattr(autofactura, 'vendedor_naturaleza', ''),
            "vendedor_numero_documento": getattr(autofactura, 'vendedor_numero_documento', '')
        }

        if include_details:
            response.update({
                "subtotal_exento": float(getattr(autofactura, 'subtotal_exento', 0)),
                "subtotal_exonerado": float(getattr(autofactura, 'subtotal_exonerado', 0)),
                "subtotal_gravado_5": float(getattr(autofactura, 'subtotal_gravado_5', 0)),
                "subtotal_gravado_10": float(getattr(autofactura, 'subtotal_gravado_10', 0)),
                "total_operacion": float(getattr(autofactura, 'total_operacion', 0)),
                "total_iva": float(getattr(autofactura, 'total_iva', 0)),
                "tipo_operacion": getattr(autofactura, 'tipo_operacion', '3'),
                "condicion_operacion": getattr(autofactura, 'condicion_operacion', '1'),
                "observaciones": getattr(autofactura, 'observaciones', ''),
                "numero_protocolo": getattr(autofactura, 'numero_protocolo', ''),
                "vendedor_direccion": getattr(autofactura, 'vendedor_direccion', ''),
                "vendedor_tipo_documento": getattr(autofactura, 'vendedor_tipo_documento', ''),
                "fecha_creacion": getattr(autofactura, 'created_at', datetime.now()).isoformat(),
                "fecha_actualizacion": getattr(autofactura, 'updated_at', datetime.now()).isoformat()
            })

        return response


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "DocumentTypesT4Mixin",
    "AUTOFACTURA_DEFAULTS",
    "NATURALEZAS_VENDEDOR_VALIDAS",
    "TIPOS_DOCUMENTO_VENDEDOR",
    "MONEDAS_IMPORTACION",
    "CAMPOS_GEOGRAFICOS_OBLIGATORIOS"
]
