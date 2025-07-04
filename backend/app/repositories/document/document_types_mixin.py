# ===============================================
# ARCHIVO: backend/app/repositories/documento/document_types_mixin.py
# PROPÓSITO: Mixin para operaciones específicas por tipo de documento SIFEN
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para operaciones específicas por tipo de documento SIFEN.
Maneja creación especializada y validaciones por tipo.
"""

from typing import Optional, List, Dict, Any, Callable, Tuple, Union
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
    SifenDatabaseError,
    handle_database_exception
)
from app.models.documento import (
    Documento,
    FacturaElectronica,
    AutofacturaElectronica,
    NotaCreditoElectronica,
    NotaDebitoElectronica,
    NotaRemisionElectronica,
    TipoDocumentoSifenEnum,
    EstadoDocumentoSifenEnum,
    TipoOperacionSifenEnum,
    CondicionOperacionSifenEnum,
    MonedaSifenEnum
)
from app.schemas.documento import (
    DocumentoCreateDTO,
    DocumentoUpdateDTO
)
from .utils import (
    normalize_cdc,
    validate_amount_precision,
    log_repository_operation,
    log_performance_metric,
    handle_repository_error,
    format_numero_completo,
    build_date_filter
)
from .auxiliars import (
    apply_default_config,
    validate_factura_data,
    validate_autofactura_data,
    validate_nota_credito_data,
    validate_nota_debito_data,
    validate_nota_remision_data,
    calculate_totals_from_items,
    create_items_for_document,
)


logger = get_logger(__name__)


# ===============================================
# CONSTANTES ESPECÍFICAS POR TIPO
# ===============================================

# Mapeo de tipos de documento a clases de modelo
DOCUMENT_TYPE_MODELS = {
    TipoDocumentoSifenEnum.FACTURA.value: FacturaElectronica,
    TipoDocumentoSifenEnum.AUTOFACTURA.value: AutofacturaElectronica,
    TipoDocumentoSifenEnum.NOTA_CREDITO.value: NotaCreditoElectronica,
    TipoDocumentoSifenEnum.NOTA_DEBITO.value: NotaDebitoElectronica,
    TipoDocumentoSifenEnum.NOTA_REMISION.value: NotaRemisionElectronica
}

# Tipos que requieren documento original
TYPES_REQUIRING_ORIGINAL = [
    TipoDocumentoSifenEnum.NOTA_CREDITO.value,
    TipoDocumentoSifenEnum.NOTA_DEBITO.value
]

# Tipos que deben tener monto 0
ZERO_AMOUNT_TYPES = [
    TipoDocumentoSifenEnum.NOTA_REMISION.value
]

# Configuraciones por defecto por tipo
DEFAULT_CONFIGURATIONS = {
    TipoDocumentoSifenEnum.FACTURA.value: {
        "tipo_operacion": TipoOperacionSifenEnum.VENTA.value,
        "condicion_operacion": CondicionOperacionSifenEnum.CONTADO.value,
        "moneda": MonedaSifenEnum.PYG.value,
        "require_items": True,
        "min_amount": Decimal("1.00")
    },
    TipoDocumentoSifenEnum.AUTOFACTURA.value: {
        "tipo_operacion": "3",  # Importación
        "condicion_operacion": CondicionOperacionSifenEnum.CONTADO.value,
        "moneda": MonedaSifenEnum.USD.value,
        "require_items": True,
        "min_amount": Decimal("1.00")
    },
    TipoDocumentoSifenEnum.NOTA_CREDITO.value: {
        "tipo_operacion": TipoOperacionSifenEnum.VENTA.value,
        "condicion_operacion": CondicionOperacionSifenEnum.CONTADO.value,
        "moneda": MonedaSifenEnum.PYG.value,
        "require_items": True,
        "min_amount": Decimal("1.00"),
        "require_original": True
    },
    TipoDocumentoSifenEnum.NOTA_DEBITO.value: {
        "tipo_operacion": TipoOperacionSifenEnum.VENTA.value,
        "condicion_operacion": CondicionOperacionSifenEnum.CONTADO.value,
        "moneda": MonedaSifenEnum.PYG.value,
        "require_items": True,
        "min_amount": Decimal("1.00"),
        "require_original": True
    },
    TipoDocumentoSifenEnum.NOTA_REMISION.value: {
        "tipo_operacion": TipoOperacionSifenEnum.VENTA.value,
        "condicion_operacion": CondicionOperacionSifenEnum.CONTADO.value,
        "moneda": MonedaSifenEnum.PYG.value,
        "require_items": True,
        "exact_amount": Decimal("0.00")
    }
}

# ===============================================
# CLASE DOCUMENT TYPES MIXIN
# ===============================================


class DocumentTypesMixin:
    """
    Mixin para operaciones especializadas por tipo de documento.

    Proporciona métodos para:
    - Creación especializada por tipo de documento
    - Validaciones específicas según el tipo
    - Gestión de relaciones entre documentos
    - Cálculos especializados por tipo
    - Factories optimizadas para cada documento

    Requiere que la clase que lo use tenga:
    - self.db: Session SQLAlchemy
    - self.model: Modelo Documento
    - self.validate_document_data: Método de validación
    """

    # Type hints para PyLance
    db: Session
    model: type[Documento]
    validate_document_data: Callable[[str, str, Optional[int]], None]

    # ===============================================
    # FACTURAS ELECTRÓNICAS (FE - Tipo 1)
    # ===============================================

    def create_factura_electronica(self,
                                   factura_data: Dict[str, Any],
                                   items: Optional[List[Dict[str, Any]]] = None,
                                   auto_calculate: bool = True) -> FacturaElectronica:
        """
        Crea una Factura Electrónica con validaciones específicas.

        Args:
            factura_data: Datos de la factura
            items: Lista de items de la factura (opcional)
            auto_calculate: Si calcular automáticamente totales

        Returns:
            FacturaElectronica: Factura creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio
            SifenDatabaseError: Si hay error en la base de datos

        Example:
            >>> factura = mixin.create_factura_electronica({
            ...     "establecimiento": "001",
            ...     "punto_expedicion": "001",
            ...     "numero_documento": "0000123",
            ...     "numero_timbrado": "12345678",
            ...     "fecha_emision": date.today(),
            ...     "empresa_id": 1,
            ...     "cliente_id": 456,
            ...     "total_general": Decimal("1100000")
            ... })
        """
        start_time = datetime.now()

        try:
            # Validar tipo de documento
            factura_data["tipo_documento"] = TipoDocumentoSifenEnum.FACTURA.value

            # Aplicar configuraciones por defecto
            self.apply_default_config(
                factura_data, TipoDocumentoSifenEnum.FACTURA.value)

            # Validaciones específicas de factura
            self.validate_factura_data(factura_data)

            # Calcular totales si se solicita
            if auto_calculate and items:
                self.calculate_totals_from_items(factura_data, items)

            # Validar datos del documento
            self.validate_document_data(
                factura_data["tipo_documento"], factura_data["numero_completo"], factura_data.get("empresa_id"))

            # Crear instancia específica de FacturaElectronica
            factura = FacturaElectronica(**factura_data)

            # Generar CDC
            factura.generar_cdc()

            # Guardar en base de datos
            self.db.add(factura)
            self.db.commit()
            self.db.refresh(factura)

            # Crear items si se proporcionan
            if items:
                self.create_items_for_document(factura, items)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("create_factura_electronica", duration, 1)

            log_repository_operation(
                "create_factura_electronica",
                "FacturaElectronica",
                getattr(factura, 'id', None),
                {
                    "numero_completo": getattr(factura, 'numero_completo', ''),
                    "total_general": float(getattr(factura, 'total_general', 0)),
                    "items_count": len(items) if items else 0,
                    "auto_calculate": auto_calculate
                }
            )

            return factura

        except (SifenValidationError, SifenBusinessLogicError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(
                e, "create_factura_electronica", "FacturaElectronica")
            raise handle_database_exception(e, "create_factura_electronica")

    def validate_factura_data(self, factura_data: Dict[str, Any]) -> None:
        """
        Valida datos específicos de facturas electrónicas.

        Args:
            factura_data: Datos de la factura a validar

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio

        Example:
            >>> mixin.validate_factura_data({
            ...     "total_general": Decimal("1100000"),
            ...     "moneda": "PYG",
            ...     "tipo_operacion": "1"
            ... })
        """
        self.validate_factura_data(factura_data)

    def get_facturas_by_criteria(self,
                                 empresa_id: int,
                                 fecha_desde: Optional[date] = None,
                                 fecha_hasta: Optional[date] = None,
                                 monto_minimo: Optional[Decimal] = None,
                                 monto_maximo: Optional[Decimal] = None,
                                 estados: Optional[List[str]] = None,
                                 limit: Optional[int] = None,
                                 offset: int = 0) -> List[FacturaElectronica]:
        """
        Obtiene facturas electrónicas por criterios específicos.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del rango
            fecha_hasta: Fecha fin del rango
            monto_minimo: Monto mínimo
            monto_maximo: Monto máximo
            estados: Lista de estados
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[FacturaElectronica]: Lista de facturas

        Example:
            >>> facturas = mixin.get_facturas_by_criteria(
            ...     empresa_id=1,
            ...     fecha_desde=date(2025, 1, 1),
            ...     fecha_hasta=date(2025, 1, 31),
            ...     estados=["aprobado"]
            ... )
        """
        documentos = self.get_documents_by_type_and_criteria(
            TipoDocumentoSifenEnum.FACTURA.value,
            empresa_id,
            fecha_desde,
            fecha_hasta,
            monto_minimo,
            monto_maximo,
            estados,
            limit,
            offset
        )
        return [doc for doc in documentos if isinstance(doc, FacturaElectronica)]

    # ===============================================
    # AUTOFACTURAS ELECTRÓNICAS (AFE - Tipo 4)
    # ===============================================

    def create_autofactura_electronica(self,
                                       autofactura_data: Dict[str, Any],
                                       import_data: Optional[Dict[str,
                                                                  Any]] = None,
                                       items: Optional[List[Dict[str, Any]]] = None,
                                       auto_calculate: bool = True) -> AutofacturaElectronica:
        """
        Crea una Autofactura Electrónica con validaciones específicas.

        Las autofacturas son documentos emitidos por el receptor de bienes/servicios
        en lugar del emisor tradicional. Comunes en importaciones y operaciones especiales.

        Args:
            autofactura_data: Datos de la autofactura
            import_data: Datos de importación (opcional)
            items: Lista de items de la autofactura (opcional)
            auto_calculate: Si calcular automáticamente totales

        Returns:
            AutofacturaElectronica: Autofactura creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio
            SifenDatabaseError: Si hay error en la base de datos

        Example:
            >>> autofactura = mixin.create_autofactura_electronica({
            ...     "establecimiento": "001",
            ...     "punto_expedicion": "001",
            ...     "numero_documento": "0000124",
            ...     "numero_timbrado": "12345678",
            ...     "fecha_emision": date.today(),
            ...     "empresa_id": 1,
            ...     "proveedor_id": 456,
            ...     "total_general": Decimal("2500000"),
            ...     "moneda": "USD"
            ... }, import_data={
            ...     "aduana": "Aeropuerto Silvio Pettirossi",
            ...     "declaracion_importacion": "DIM-2025-001234"
            ... })
        """
        start_time = datetime.now()

        try:
            # Validar tipo de documento
            autofactura_data["tipo_documento"] = TipoDocumentoSifenEnum.AUTOFACTURA.value

            # Aplicar configuraciones por defecto
            self.apply_default_config(
                autofactura_data, TipoDocumentoSifenEnum.AUTOFACTURA.value)

            # Validaciones específicas de autofactura
            self.validate_autofactura_data(autofactura_data, import_data)

            # Calcular totales si se solicita
            if auto_calculate and items:
                self.calculate_totals_from_items(autofactura_data, items)

            # Validar datos del documento
            numero_completo = format_numero_completo(
                autofactura_data["establecimiento"],
                autofactura_data["punto_expedicion"],
                autofactura_data["numero_documento"]
            )
            self.validate_document_data(
                autofactura_data["tipo_documento"],
                numero_completo,
                autofactura_data.get("empresa_id")
            )

            # Crear instancia específica de AutofacturaElectronica
            autofactura = AutofacturaElectronica(**autofactura_data)

            # Generar CDC
            autofactura.generar_cdc()

            # Guardar en base de datos
            self.db.add(autofactura)
            self.db.commit()
            self.db.refresh(autofactura)

            # Crear items si se proporcionan
            if items:
                self.create_items_for_document(autofactura, items)

            # Vincular datos de importación si se proporcionan
            if import_data:
                self.link_import_data(autofactura, import_data)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "create_autofactura_electronica", duration, 1)

            log_repository_operation(
                "create_autofactura_electronica",
                "AutofacturaElectronica",
                getattr(autofactura, 'id', None),
                {
                    "numero_completo": getattr(autofactura, 'numero_completo', ''),
                    "total_general": float(getattr(autofactura, 'total_general', 0)),
                    "moneda": getattr(autofactura, 'moneda', ''),
                    "items_count": len(items) if items else 0,
                    "has_import_data": bool(import_data),
                    "auto_calculate": auto_calculate
                }
            )

            return autofactura

        except (SifenValidationError, SifenBusinessLogicError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(
                e, "create_autofactura_electronica", "AutofacturaElectronica")
            raise handle_database_exception(
                e, "create_autofactura_electronica")

    def validate_autofactura_data(self,
                                  autofactura_data: Dict[str, Any],
                                  import_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Valida datos específicos de autofacturas electrónicas.

        Args:
            autofactura_data: Datos de la autofactura a validar
            import_data: Datos de importación (opcional)

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio

        Example:
            >>> mixin.validate_autofactura_data({
            ...     "tipo_operacion": "3",  # Importación
            ...     "moneda": "USD",
            ...     "total_general": Decimal("2500000")
            ... }, import_data={
            ...     "aduana": "Aeropuerto Silvio Pettirossi",
            ...     "declaracion_importacion": "DIM-2025-001234"
            ... })
        """
        self.validate_autofactura_data(autofactura_data, import_data)

    def get_autofacturas_by_criteria(self,
                                     empresa_id: int,
                                     fecha_desde: Optional[date] = None,
                                     fecha_hasta: Optional[date] = None,
                                     monto_minimo: Optional[Decimal] = None,
                                     monto_maximo: Optional[Decimal] = None,
                                     moneda: Optional[str] = None,
                                     estados: Optional[List[str]] = None,
                                     limit: Optional[int] = None,
                                     offset: int = 0) -> List[Documento]:
        """
        Obtiene autofacturas electrónicas por criterios específicos.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del rango
            fecha_hasta: Fecha fin del rango
            monto_minimo: Monto mínimo
            monto_maximo: Monto máximo
            moneda: Código de moneda (USD, EUR, etc.)
            estados: Lista de estados
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[Documento]: Lista de autofacturas

        Example:
            >>> autofacturas = mixin.get_autofacturas_by_criteria(
            ...     empresa_id=1,
            ...     fecha_desde=date(2025, 1, 1),
            ...     fecha_hasta=date(2025, 1, 31),
            ...     moneda="USD",
            ...     estados=["aprobado"]
            ... )
        """
        start_time = datetime.now()

        try:
            # Obtener documentos base
            documentos = self.get_documents_by_type_and_criteria(
                TipoDocumentoSifenEnum.AUTOFACTURA.value,
                empresa_id,
                fecha_desde,
                fecha_hasta,
                monto_minimo,
                monto_maximo,
                estados,
                limit,
                offset
            )

            # Filtrar por moneda si se especifica
            if moneda:
                documentos = [doc for doc in documentos
                              if getattr(doc, 'moneda', None) == moneda]

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_autofacturas_by_criteria", duration, len(documentos))

            log_repository_operation("get_autofacturas_by_criteria", "AutofacturaElectronica", None, {
                "empresa_id": empresa_id,
                "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                "moneda": moneda,
                "count": len(documentos)
            })

            return documentos

        except Exception as e:
            handle_repository_error(
                e, "get_autofacturas_by_criteria", "AutofacturaElectronica")
            raise handle_database_exception(e, "get_autofacturas_by_criteria")

    def get_autofacturas_by_import_data(self,
                                        empresa_id: int,
                                        aduana: Optional[str] = None,
                                        declaracion_importacion: Optional[str] = None,
                                        fecha_desde: Optional[date] = None,
                                        fecha_hasta: Optional[date] = None) -> List[Documento]:
        """
        Obtiene autofacturas por datos de importación.

        Args:
            empresa_id: ID de la empresa
            aduana: Nombre o código de aduana
            declaracion_importacion: Número de declaración de importación
            fecha_desde: Fecha inicio del rango
            fecha_hasta: Fecha fin del rango

        Returns:
            List[Documento]: Lista de autofacturas que coinciden

        Example:
            >>> autofacturas = mixin.get_autofacturas_by_import_data(
            ...     empresa_id=1,
            ...     aduana="Aeropuerto Silvio Pettirossi",
            ...     declaracion_importacion="DIM-2025-001234"
            ... )
        """
        start_time = datetime.now()

        try:
            # Construir query base
            query = self.db.query(self.model).filter(
                and_(
                    self.model.tipo_documento == TipoDocumentoSifenEnum.AUTOFACTURA.value,
                    self.model.empresa_id == empresa_id
                )
            )

            # Aplicar filtros de fechas
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, self.model.fecha_emision, fecha_desde, fecha_hasta)

            # TODO: Implementar filtros por datos de importación cuando estén disponibles
            # Actualmente los datos de importación no están en el modelo base
            # Se necesitaría una tabla relacionada o campos adicionales

            # Aplicar filtros de texto si se proporcionan
            if aduana:
                # Búsqueda en observaciones como alternativa temporal
                query = query.filter(
                    func.lower(self.model.observaciones).like(
                        f"%{aduana.lower()}%")
                )

            if declaracion_importacion:
                # Búsqueda en observaciones como alternativa temporal
                query = query.filter(
                    func.lower(self.model.observaciones).like(
                        f"%{declaracion_importacion.lower()}%")
                )

            documentos = query.order_by(desc(self.model.fecha_emision)).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_autofacturas_by_import_data", duration, len(documentos))

            log_repository_operation("get_autofacturas_by_import_data", "AutofacturaElectronica", None, {
                "empresa_id": empresa_id,
                "aduana": aduana,
                "declaracion_importacion": declaracion_importacion,
                "count": len(documentos)
            })

            return documentos

        except Exception as e:
            handle_repository_error(
                e, "get_autofacturas_by_import_data", "AutofacturaElectronica")
            raise handle_database_exception(
                e, "get_autofacturas_by_import_data")

    # ===============================================
    # NOTAS DE CRÉDITO ELECTRÓNICAS (NCE - Tipo 5)
    # ===============================================

    def create_nota_credito_electronica(self,
                                        nota_data: Dict[str, Any],
                                        documento_original_cdc: str,
                                        items: Optional[List[Dict[str, Any]]] = None,
                                        auto_calculate: bool = True) -> NotaCreditoElectronica:
        """
        Crea una Nota de Crédito Electrónica con validaciones específicas.

        Las notas de crédito reducen el monto adeudado por el cliente,
        generalmente por devoluciones, descuentos o correcciones.

        Args:
            nota_data: Datos de la nota de crédito
            documento_original_cdc: CDC del documento original al que se aplica
            items: Lista de items de la nota (opcional)
            auto_calculate: Si calcular automáticamente totales

        Returns:
            NotaCreditoElectronica: Nota de crédito creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio
            SifenEntityNotFoundError: Si el documento original no existe
            SifenDatabaseError: Si hay error en la base de datos

        Example:
            >>> nota_credito = mixin.create_nota_credito_electronica({
            ...     "establecimiento": "001",
            ...     "punto_expedicion": "001",
            ...     "numero_documento": "0000125",
            ...     "numero_timbrado": "12345678",
            ...     "fecha_emision": date.today(),
            ...     "empresa_id": 1,
            ...     "cliente_id": 456,
            ...     "total_general": Decimal("550000"),
            ...     "motivo_credito": "Devolución por producto defectuoso"
            ... }, documento_original_cdc="12345678901234567890123456789012345678901234")
        """
        start_time = datetime.now()

        try:
            # Validar y obtener documento original
            documento_original = self.validate_and_get_original_document(
                documento_original_cdc)

            # Validar tipo de documento
            nota_data["tipo_documento"] = TipoDocumentoSifenEnum.NOTA_CREDITO.value

            # Aplicar configuraciones por defecto
            self.apply_default_config(
                nota_data, TipoDocumentoSifenEnum.NOTA_CREDITO.value)

            # Asignar CDC del documento original
            nota_data["documento_original_cdc"] = documento_original.cdc

            # Validaciones específicas de nota de crédito
            self.validate_nota_credito_data(nota_data, documento_original)

            # Calcular totales si se solicita
            if auto_calculate and items:
                self.calculate_totals_from_items(nota_data, items)

            # Validar datos del documento
            numero_completo = format_numero_completo(
                nota_data["establecimiento"],
                nota_data["punto_expedicion"],
                nota_data["numero_documento"]
            )
            self.validate_document_data(
                nota_data["tipo_documento"],
                numero_completo,
                nota_data.get("empresa_id")
            )

            # Crear instancia específica de NotaCreditoElectronica
            nota_credito = NotaCreditoElectronica(**nota_data)

            # Generar CDC
            nota_credito.generar_cdc()

            # Guardar en base de datos
            self.db.add(nota_credito)
            self.db.commit()
            self.db.refresh(nota_credito)

            # Crear items si se proporcionan
            if items:
                self.create_items_for_document(nota_credito, items)

            # Vincular documento original
            self.link_original_document(nota_credito, documento_original)

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "create_nota_credito_electronica", duration, 1)

            log_repository_operation(
                "create_nota_credito_electronica",
                "NotaCreditoElectronica",
                getattr(nota_credito, 'id', None),
                {
                    "numero_completo": getattr(nota_credito, 'numero_completo', ''),
                    "total_general": float(getattr(nota_credito, 'total_general', 0)),
                    "documento_original_cdc": documento_original_cdc,
                    "motivo_credito": nota_data.get("motivo_credito", ""),
                    "items_count": len(items) if items else 0,
                    "auto_calculate": auto_calculate
                }
            )

            return nota_credito

        except (SifenValidationError, SifenBusinessLogicError, SifenEntityNotFoundError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(
                e, "create_nota_credito_electronica", "NotaCreditoElectronica")
            raise handle_database_exception(
                e, "create_nota_credito_electronica")

    def validate_nota_credito_data(self,
                                   nota_data: Dict[str, Any],
                                   documento_original: Documento) -> None:
        """
        Valida datos específicos de notas de crédito electrónicas.

        Args:
            nota_data: Datos de la nota de crédito a validar
            documento_original: Documento original de referencia

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio

        Example:
            >>> mixin.validate_nota_credito_data({
            ...     "total_general": Decimal("550000"),
            ...     "motivo_credito": "Devolución por producto defectuoso"
            ... }, documento_original)
        """
        self.validate_nota_credito_data(nota_data, documento_original)

    def get_notas_credito_by_criteria(self,
                                      empresa_id: int,
                                      fecha_desde: Optional[date] = None,
                                      fecha_hasta: Optional[date] = None,
                                      monto_minimo: Optional[Decimal] = None,
                                      monto_maximo: Optional[Decimal] = None,
                                      documento_original_cdc: Optional[str] = None,
                                      estados: Optional[List[str]] = None,
                                      limit: Optional[int] = None,
                                      offset: int = 0) -> List[Documento]:
        """
        Obtiene notas de crédito electrónicas por criterios específicos.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del rango
            fecha_hasta: Fecha fin del rango
            monto_minimo: Monto mínimo
            monto_maximo: Monto máximo
            documento_original_cdc: CDC del documento original
            estados: Lista de estados
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[Documento]: Lista de notas de crédito

        Example:
            >>> notas_credito = mixin.get_notas_credito_by_criteria(
            ...     empresa_id=1,
            ...     fecha_desde=date(2025, 1, 1),
            ...     fecha_hasta=date(2025, 1, 31),
            ...     estados=["aprobado"]
            ... )
        """
        start_time = datetime.now()

        try:
            # Obtener documentos base
            documentos = self.get_documents_by_type_and_criteria(
                TipoDocumentoSifenEnum.NOTA_CREDITO.value,
                empresa_id,
                fecha_desde,
                fecha_hasta,
                monto_minimo,
                monto_maximo,
                estados,
                limit,
                offset
            )

            # Filtrar por documento original si se especifica
            if documento_original_cdc:
                cdc_normalized = normalize_cdc(documento_original_cdc)
                documentos = [doc for doc in documentos
                              if getattr(doc, 'documento_original_cdc', None) == cdc_normalized]

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_notas_credito_by_criteria", duration, len(documentos))

            log_repository_operation("get_notas_credito_by_criteria", "NotaCreditoElectronica", None, {
                "empresa_id": empresa_id,
                "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                "documento_original_cdc": documento_original_cdc,
                "count": len(documentos)
            })

            return documentos

        except Exception as e:
            handle_repository_error(
                e, "get_notas_credito_by_criteria", "NotaCreditoElectronica")
            raise handle_database_exception(e, "get_notas_credito_by_criteria")

    def get_notas_credito_by_original_document(self,
                                               documento_original_cdc: str,
                                               empresa_id: Optional[int] = None) -> List[Documento]:
        """
        Obtiene todas las notas de crédito asociadas a un documento original.

        Args:
            documento_original_cdc: CDC del documento original
            empresa_id: ID de empresa (opcional, para filtrar)

        Returns:
            List[Documento]: Lista de notas de crédito del documento

        Example:
            >>> notas = mixin.get_notas_credito_by_original_document(
            ...     "12345678901234567890123456789012345678901234"
            ... )
        """
        start_time = datetime.now()

        try:
            # Normalizar CDC
            cdc_normalized = normalize_cdc(documento_original_cdc)

            # Construir query
            query = self.db.query(self.model).filter(
                and_(
                    self.model.tipo_documento == TipoDocumentoSifenEnum.NOTA_CREDITO.value,
                    text("documento_original_cdc = :cdc")
                )
            ).params(cdc=cdc_normalized)

            # Filtrar por empresa si se especifica
            if empresa_id:
                query = query.filter(self.model.empresa_id == empresa_id)

            documentos = query.order_by(desc(self.model.fecha_emision)).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_notas_credito_by_original_document", duration, len(documentos))

            log_repository_operation("get_notas_credito_by_original_document", "NotaCreditoElectronica", None, {
                "documento_original_cdc": documento_original_cdc,
                "empresa_id": empresa_id,
                "count": len(documentos)
            })

            return documentos

        except Exception as e:
            handle_repository_error(
                e, "get_notas_credito_by_original_document", "NotaCreditoElectronica")
            raise handle_database_exception(
                e, "get_notas_credito_by_original_document")
