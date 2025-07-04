# ===============================================
# ARCHIVO: backend/app/repositories/documento/document_types_mixin_t7.py
# PROPÓSITO: Mixin para operaciones específicas de Notas de Remisión Electrónicas (NRE - Tipo 7)
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para operaciones específicas de Notas de Remisión Electrónicas (NRE - Tipo 7).

Este módulo implementa funcionalidades especializadas para el manejo de notas
de remisión electrónicas, incluyendo:
- Creación con validaciones específicas de NRE
- Validaciones de datos de transporte obligatorios
- Gestión de traslados sin valor comercial (totales = 0)
- Validaciones de motivos de traslado específicos
- Búsquedas optimizadas para notas de remisión
- Estadísticas específicas de logística y transporte
- Integración total con SIFEN v150

Características principales:
- Totales monetarios siempre en cero (documento logístico)
- Datos de transporte obligatorios y completos
- Validación de fechas de traslado lógicas
- Aplicación de defaults específicos para NRE
- Búsquedas por criterios logísticos (transportista, vehículo, ruta)
- Estadísticas de movimientos y trazabilidad
- Conformidad total con SIFEN v150

Clase principal:
- DocumentTypesMixinT7: Mixin especializado para notas de remisión electrónicas
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func, text, desc, asc
from sqlalchemy.orm import Session, joinedload
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
    NotaRemisionElectronica,
    Documento,
    TipoDocumentoSifenEnum,
    EstadoDocumentoSifenEnum,
    MonedaSifenEnum,
    TipoOperacionSifenEnum,
    CondicionOperacionSifenEnum
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
    validate_nota_remision_data,
    validate_transport_data,
    validate_movement_dates,
    get_documents_by_type_and_criteria,
    adjust_items_for_remision,
    create_items_for_document,
    link_transport_info
)

logger = get_logger(__name__)

# ===============================================
# CONFIGURACIONES ESPECÍFICAS PARA NRE
# ===============================================

# Defaults específicos para notas de remisión electrónicas
NRE_DEFAULTS = {
    "tipo_documento": "7",
    "tipo_operacion": "1",  # Venta (traslado por venta)
    "condicion_operacion": "1",  # Contado
    "moneda": "PYG",
    "tipo_emision": "1",  # Normal
    "tipo_cambio": Decimal("1.0000"),
    # Totales siempre en cero para NRE
    "total_general": Decimal("0.00"),
    "total_operacion": Decimal("0.00"),
    "total_iva": Decimal("0.00"),
    "subtotal_exento": Decimal("0.00"),
    "subtotal_exonerado": Decimal("0.00"),
    "subtotal_gravado_5": Decimal("0.00"),
    "subtotal_gravado_10": Decimal("0.00")
}

# Motivos de traslado válidos según SIFEN v150
MOTIVOS_TRASLADO_VALIDOS = {
    "1": "Traslado por venta",
    "2": "Traslado entre establecimientos de la empresa",
    "3": "Traslado por importación",
    "4": "Traslado por exportación",
    "5": "Traslado por transformación",
    "6": "Traslado por exhibición",
    "7": "Traslado por demostración",
    "8": "Traslado por consignación",
    "9": "Traslado por reparación",
    "10": "Traslado por devolución",
    "11": "Traslado por decomiso",
    "12": "Traslado por donación",
    "13": "Traslado por préstamo",
    "14": "Traslado por reorganización empresarial",
    "99": "Otro motivo"
}

# Responsables del flete según SIFEN
RESPONSABLES_FLETE = {
    "1": "Emisor",
    "2": "Receptor",
    "3": "Tercero"
}

# Condiciones de transporte
CONDICIONES_TRANSPORTE = {
    "1": "Transporte propio",
    "2": "Transporte contratado",
    "3": "Retiro por cuenta del receptor"
}

# Modalidades de transporte
MODALIDADES_TRANSPORTE = {
    "1": "Terrestre",
    "2": "Fluvial",
    "3": "Aéreo",
    "4": "Marítimo"
}

# ===============================================
# MIXIN PRINCIPAL
# ===============================================


class DocumentTypesMixinT7:
    """
    Mixin para operaciones específicas de Notas de Remisión Electrónicas (NRE - Tipo 7).

    Proporciona métodos especializados para el manejo de notas de remisión electrónicas:
    - Creación con validaciones específicas de NRE
    - Validaciones de datos de transporte obligatorios
    - Gestión de traslados sin valor comercial
    - Búsquedas optimizadas para notas de remisión
    - Validaciones de fechas y rutas de traslado
    - Estadísticas logísticas específicas
    - Integración completa con SIFEN v150

    Este mixin debe ser usado junto con DocumentoRepositoryBase para
    obtener funcionalidad completa de gestión de documentos.

    Example:
        ```python
        class DocumentoRepository(
            DocumentoRepositoryBase,
            DocumentTypesMixinT7,
            # otros mixins...
        ):
            pass

        repo = DocumentoRepository(db)
        nota_remision = repo.create_nota_remision_electronica(data, transporte, items)
        ```
    """

    db: Session
    model: type

    # ===============================================
    # MÉTODOS DE CREACIÓN ESPECÍFICOS
    # ===============================================

    def create_nota_remision_electronica(self,
                                         nota_data: Union[DocumentoCreateDTO, Dict[str, Any]],
                                         datos_transporte: Dict[str, Any],
                                         items: List[Dict[str, Any]],
                                         apply_defaults: bool = True,
                                         validate_transport: bool = True,
                                         auto_generate_cdc: bool = True,
                                         empresa_id: Optional[int] = None) -> NotaRemisionElectronica:
        """
        Crea una nota de remisión electrónica con validaciones específicas.

        Este método es el punto de entrada principal para crear notas de remisión electrónicas,
        aplicando todas las validaciones y configuraciones específicas del tipo de documento.

        Args:
            nota_data: Datos básicos de la nota de remisión
            datos_transporte: Datos obligatorios del transporte
            items: Lista de items/productos a trasladar (sin precios)
            apply_defaults: Aplicar configuraciones por defecto específicas
            validate_transport: Validar datos de transporte automáticamente
            auto_generate_cdc: Generar CDC automáticamente
            empresa_id: ID de empresa (opcional, para validaciones adicionales)

        Returns:
            NotaRemisionElectronica: Instancia de nota de remisión creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio
            SifenDuplicateEntityError: Si la numeración ya existe

        Example:
            ```python
            nota_data = {
                "establecimiento": "001",
                "punto_expedicion": "001",
                "numero_documento": "0000128",
                "numero_timbrado": "12345678",
                "fecha_emision": date.today(),
                "motivo_traslado": "Traslado entre sucursales",
                "moneda": "PYG"
            }

            datos_transporte = {
                "motivo_traslado": "2",  # Traslado entre establecimientos
                "fecha_inicio_traslado": date.today(),
                "fecha_fin_traslado": date.today() + timedelta(days=1),
                "transportista_ruc": "12345678-9",
                "transportista_nombre": "Transportes SA",
                "vehiculo_chapa": "ABC123",
                "conductor_nombre": "Juan Pérez",
                "conductor_ci": "1234567"
            }

            items = [{
                "descripcion": "Equipos de oficina",
                "cantidad": 5,
                "precio_unitario": Decimal("0"),  # Sin valor comercial
                "tipo_iva": "exento"
            }]

            nota_remision = repo.create_nota_remision_electronica(
                nota_data, datos_transporte, items
            )
            ```
        """
        start_time = datetime.now()

        try:
            # 1. Preparar datos base
            if isinstance(nota_data, DocumentoCreateDTO):
                data_dict = nota_data.dict()
            else:
                data_dict = nota_data.copy()

            # 2. Aplicar defaults específicos de notas de remisión
            if apply_defaults:
                self._apply_nre_defaults(data_dict)

            # 3. Validar estructura básica y reglas de negocio específicas NRE
            self.validate_nota_remision_data(
                data_dict, items, datos_transporte)

            # 4. Validar datos de transporte si se solicita
            if validate_transport:
                self.validate_transport_requirements(
                    datos_transporte, data_dict)

            # 5. Ajustar items para remisión (precios en 0)
            items_adjusted = adjust_items_for_remision(items)

            # 6. Integrar datos de transporte en el documento
            self._integrate_transport_data(data_dict, datos_transporte)

            # 7. Aplicar validaciones adicionales por empresa
            if empresa_id:
                data_dict["empresa_id"] = empresa_id

            # 8. Crear documento usando método base del repository
            nota_remision = getattr(self, 'create')(
                data_dict, auto_generate_fields=auto_generate_cdc)

            # 9. Crear items asociados a la nota de remisión
            if items_adjusted:
                create_items_for_document(
                    self.db, nota_remision, items_adjusted)

            # 10. Vincular información de transporte
            link_transport_info(nota_remision, datos_transporte)

            # 11. Log de operación exitosa
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "create_nota_remision_electronica", duration, 1)

            log_repository_operation("create_nota_remision_electronica", "NotaRemisionElectronica",
                                     getattr(nota_remision, 'id', None), {
                                         "numero_completo": getattr(nota_remision, 'numero_completo', None),
                                         "items_count": len(items_adjusted),
                                         "motivo_traslado": datos_transporte.get("motivo_traslado", ""),
                                         "transportista": datos_transporte.get("transportista_nombre", "")[:50],
                                         "fecha_inicio_traslado": str(datos_transporte.get("fecha_inicio_traslado", ""))
                                     })

            return nota_remision

        except (SifenValidationError, SifenBusinessLogicError, SifenDuplicateEntityError):
            # Re-raise errores de validación/negocio sin modificar
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(
                e, "create_nota_remision_electronica", "NotaRemisionElectronica")
            raise handle_database_exception(
                e, "create_nota_remision_electronica")

    def create_nota_remision_traslado_interno(self,
                                              numero_documento: str,
                                              items: List[Dict[str, Any]],
                                              establecimiento_origen: str,
                                              establecimiento_destino: str,
                                              fecha_traslado: Optional[date] = None,
                                              empresa_id: Optional[int] = None,
                                              observaciones: Optional[str] = None) -> NotaRemisionElectronica:
        """
        Creación específica para traslados internos entre establecimientos.

        Método de conveniencia para crear notas de remisión por traslados internos,
        con configuraciones predefinidas para este caso específico.

        Args:
            numero_documento: Número secuencial del documento
            items: Lista de items a trasladar
            establecimiento_origen: Código establecimiento origen
            establecimiento_destino: Código establecimiento destino
            fecha_traslado: Fecha del traslado (opcional, default: hoy)
            empresa_id: ID de empresa emisora
            observaciones: Observaciones adicionales

        Returns:
            NotaRemisionElectronica: Nota de remisión para traslado interno

        Example:
            ```python
            items = [{
                "descripcion": "Productos varios",
                "cantidad": 10,
                "precio_unitario": Decimal("0")
            }]

            nota_traslado = repo.create_nota_remision_traslado_interno(
                numero_documento="0000129",
                items=items,
                establecimiento_origen="001",
                establecimiento_destino="002",
                fecha_traslado=date.today(),
                empresa_id=1
            )
            ```
        """
        if fecha_traslado is None:
            fecha_traslado = date.today()

        # TODO: Obtener datos de empresa para establecimiento y timbrado
        nota_data = {
            "establecimiento": establecimiento_origen,
            "punto_expedicion": "001",  # TODO: Desde configuración empresa
            "numero_documento": numero_documento,
            "numero_timbrado": "12345678",  # TODO: Desde timbrado activo
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),  # TODO: Desde timbrado
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),  # TODO: Desde timbrado
            "timbrado_id": 1,  # TODO: Desde timbrado activo
            "motivo_traslado": "Traslado entre establecimientos de la empresa"
        }

        # Para traslado interno, emisor = receptor
        datos_transporte = {
            "motivo_traslado": "2",  # Traslado entre establecimientos
            "fecha_inicio_traslado": fecha_traslado,
            "fecha_fin_traslado": fecha_traslado,  # Mismo día para traslados internos
            "responsable_flete": "1",  # Emisor
            "condicion_transporte": "1",  # Transporte propio
            "modalidad_transporte": "1",  # Terrestre
            "establecimiento_origen": establecimiento_origen,
            "establecimiento_destino": establecimiento_destino,
            # Datos simplificados para traslado interno
            "transportista_nombre": "Traslado interno",
            "vehiculo_chapa": "INTERNO",
            "conductor_nombre": "Personal interno"
        }

        if empresa_id:
            nota_data["empresa_id"] = empresa_id
            # Para traslado interno, receptor = emisor
            nota_data["cliente_id"] = empresa_id

        if observaciones:
            nota_data["observaciones"] = observaciones

        return self.create_nota_remision_electronica(
            nota_data=nota_data,
            datos_transporte=datos_transporte,
            items=items,
            apply_defaults=True,
            validate_transport=True,
            auto_generate_cdc=True
        )

    def create_nota_remision_entrega(self,
                                     numero_documento: str,
                                     cliente_id: int,
                                     items: List[Dict[str, Any]],
                                     datos_transporte: Dict[str, Any],
                                     direccion_entrega: str,
                                     empresa_id: Optional[int] = None) -> NotaRemisionElectronica:
        """
        Creación específica para entregas de productos vendidos.

        Args:
            numero_documento: Número secuencial del documento
            cliente_id: ID del cliente que recibe
            items: Lista de items a entregar
            datos_transporte: Datos del transporte para entrega
            direccion_entrega: Dirección de entrega
            empresa_id: ID de empresa emisora

        Returns:
            NotaRemisionElectronica: Nota de remisión para entrega

        Example:
            ```python
            datos_transporte = {
                "fecha_inicio_traslado": date.today(),
                "fecha_fin_traslado": date.today(),
                "transportista_ruc": "87654321-0",
                "transportista_nombre": "Delivery Express",
                "vehiculo_chapa": "DEL456",
                "conductor_nombre": "Carlos García",
                "conductor_ci": "7654321"
            }

            nota_entrega = repo.create_nota_remision_entrega(
                numero_documento="0000130",
                cliente_id=456,
                items=items,
                datos_transporte=datos_transporte,
                direccion_entrega="Av. Principal 123, Asunción",
                empresa_id=1
            )
            ```
        """
        # TODO: Obtener datos de empresa
        nota_data = {
            "establecimiento": "001",
            "punto_expedicion": "001",
            "numero_documento": numero_documento,
            "numero_timbrado": "12345678",
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),
            "timbrado_id": 1,
            "cliente_id": cliente_id,
            "motivo_traslado": "Traslado por venta",
            "observaciones": f"Entrega en: {direccion_entrega}"
        }

        # Completar datos de transporte
        datos_transporte_completos = {
            "motivo_traslado": "1",  # Traslado por venta
            "responsable_flete": "1",  # Emisor
            "condicion_transporte": "2",  # Transporte contratado
            "modalidad_transporte": "1",  # Terrestre
            "direccion_destino": direccion_entrega,
            **datos_transporte
        }

        if empresa_id:
            nota_data["empresa_id"] = empresa_id

        return self.create_nota_remision_electronica(
            nota_data=nota_data,
            datos_transporte=datos_transporte_completos,
            items=items,
            apply_defaults=True,
            validate_transport=True,
            auto_generate_cdc=True
        )

    # ===============================================
    # VALIDACIONES ESPECÍFICAS
    # ===============================================

    def validate_nota_remision_data(self,
                                    nota_data: Dict[str, Any],
                                    items: List[Dict[str, Any]],
                                    datos_transporte: Dict[str, Any]) -> None:
        """
        Validaciones comprehensivas específicas para notas de remisión electrónicas.

        Aplica todas las validaciones requeridas para una nota de remisión según
        las normativas SIFEN y reglas de negocio específicas.

        Args:
            nota_data: Datos de la nota de remisión a validar
            items: Items de la nota de remisión a validar
            datos_transporte: Datos de transporte a validar

        Raises:
            SifenValidationError: Si alguna validación falla

        Example:
            ```python
            try:
                repo.validate_nota_remision_data(nota_data, items, datos_transporte)
                print("Datos válidos")
            except SifenValidationError as e:
                print(f"Error de validación: {e.message}")
            ```
        """
        # Usar validación de auxiliares como base
        validate_nota_remision_data(nota_data, datos_transporte)

        # Validaciones adicionales específicas de notas de remisión

        # 1. Items obligatorios para NRE
        if not items or len(items) == 0:
            raise SifenValidationError(
                "Notas de remisión deben tener al menos 1 item para trasladar",
                field="items"
            )

        # 2. Validar cada item específicamente para NRE
        for i, item in enumerate(items):
            self._validate_nota_remision_item(item, i)

        # 3. Validar totales en cero (característica principal de NRE)
        self._validate_zero_amounts(nota_data)

        # 4. Validar motivo de traslado
        motivo_traslado = datos_transporte.get("motivo_traslado", "")
        if motivo_traslado not in MOTIVOS_TRASLADO_VALIDOS:
            raise SifenValidationError(
                f"Motivo de traslado debe ser uno de: {list(MOTIVOS_TRASLADO_VALIDOS.keys())}",
                field="motivo_traslado",
                value=motivo_traslado
            )

        # 5. Validaciones específicas por motivo
        self._validate_motivo_specific_rules(
            motivo_traslado, nota_data, datos_transporte)

    def validate_transport_requirements(self,
                                        datos_transporte: Dict[str, Any],
                                        nota_data: Dict[str, Any]) -> None:
        """
        Validaciones específicas de datos de transporte para notas de remisión.

        Verifica que los datos de transporte sean completos y coherentes
        con la naturaleza logística de la nota de remisión.

        Args:
            datos_transporte: Datos de transporte a validar
            nota_data: Datos de la nota para validaciones cruzadas

        Raises:
            SifenValidationError: Si los datos de transporte no son válidos
        """
        # Usar validación de auxiliares como base
        validate_transport_data(datos_transporte)

        # Validaciones adicionales específicas

        # 1. Campos obligatorios de transporte
        required_transport_fields = [
            "motivo_traslado", "fecha_inicio_traslado", "responsable_flete", "condicion_transporte"
        ]

        for field in required_transport_fields:
            if field not in datos_transporte or not datos_transporte[field]:
                raise SifenValidationError(
                    f"Campo de transporte obligatorio: {field}",
                    field=field
                )

        # 2. Validar responsable del flete
        responsable_flete = datos_transporte.get("responsable_flete", "")
        if responsable_flete not in RESPONSABLES_FLETE:
            raise SifenValidationError(
                f"Responsable del flete debe ser uno de: {list(RESPONSABLES_FLETE.keys())}",
                field="responsable_flete",
                value=responsable_flete
            )

        # 3. Validar condición de transporte
        condicion_transporte = datos_transporte.get("condicion_transporte", "")
        if condicion_transporte not in CONDICIONES_TRANSPORTE:
            raise SifenValidationError(
                f"Condición de transporte debe ser una de: {list(CONDICIONES_TRANSPORTE.keys())}",
                field="condicion_transporte",
                value=condicion_transporte
            )

        # 4. Validar fechas de traslado
        fecha_inicio = datos_transporte.get("fecha_inicio_traslado")
        fecha_fin = datos_transporte.get("fecha_fin_traslado")
        if fecha_inicio and fecha_fin:
            validate_movement_dates(fecha_inicio, fecha_fin)

        # 5. Validaciones específicas por condición de transporte
        self._validate_transport_condition_requirements(datos_transporte)

    def validate_delivery_route(self,
                                origen: Dict[str, Any],
                                destino: Dict[str, Any],
                                modalidad_transporte: str = "1") -> Dict[str, Any]:
        """
        Valida la ruta de entrega y calcula estimaciones.

        Args:
            origen: Datos del punto de origen
            destino: Datos del punto de destino
            modalidad_transporte: Modalidad de transporte

        Returns:
            Dict[str, Any]: Información validada de la ruta

        Raises:
            SifenValidationError: Si la ruta no es válida

        Example:
            ```python
            origen = {"direccion": "Av. España 123", "ciudad": "Asunción"}
            destino = {"direccion": "Ruta 2 Km 15", "ciudad": "San Lorenzo"}

            ruta = repo.validate_delivery_route(origen, destino, "1")
            ```
        """
        try:
            validacion = {
                "es_valida": True,
                "advertencias": [],
                "estimaciones": {}
            }

            # Validar datos básicos de origen
            if not origen.get("direccion"):
                raise SifenValidationError(
                    "Dirección de origen es requerida",
                    field="origen.direccion"
                )

            # Validar datos básicos de destino
            if not destino.get("direccion"):
                raise SifenValidationError(
                    "Dirección de destino es requerida",
                    field="destino.direccion"
                )

            # Validar modalidad de transporte
            if modalidad_transporte not in MODALIDADES_TRANSPORTE:
                raise SifenValidationError(
                    f"Modalidad de transporte debe ser una de: {list(MODALIDADES_TRANSPORTE.keys())}",
                    field="modalidad_transporte",
                    value=modalidad_transporte
                )

            # Estimaciones básicas (placeholder - implementar lógica real)
            distancia_estimada = self._estimate_distance(origen, destino)
            tiempo_estimado = self._estimate_delivery_time(
                distancia_estimada, modalidad_transporte)

            validacion["estimaciones"] = {
                "distancia_km": distancia_estimada,
                "tiempo_horas": tiempo_estimado,
                "modalidad": MODALIDADES_TRANSPORTE[modalidad_transporte]
            }

            # Advertencias por distancia
            if distancia_estimada > 500:
                validacion["advertencias"].append(
                    f"Distancia muy larga ({distancia_estimada} km) - considerar modalidad aérea"
                )

            return validacion

        except SifenValidationError:
            raise
        except Exception as e:
            handle_repository_error(
                e, "validate_delivery_route", "NotaRemisionElectronica")
            raise handle_database_exception(e, "validate_delivery_route")

    # ===============================================
    # BÚSQUEDAS ESPECIALIZADAS
    # ===============================================

    def get_notas_remision_by_criteria(self,
                                       empresa_id: int,
                                       fecha_desde: Optional[date] = None,
                                       fecha_hasta: Optional[date] = None,
                                       cliente_id: Optional[int] = None,
                                       motivo_traslado: Optional[str] = None,
                                       transportista: Optional[str] = None,
                                       estados: Optional[List[str]] = None,
                                       include_transport: bool = False,
                                       limit: Optional[int] = None,
                                       offset: int = 0) -> List[NotaRemisionElectronica]:
        """
        Búsqueda avanzada de notas de remisión con múltiples criterios.

        Permite filtrar notas de remisión por diversos criterios específicos del negocio,
        optimizado para consultas frecuentes en dashboards logísticos.

        Args:
            empresa_id: ID de la empresa emisora
            fecha_desde: Fecha inicio del rango (opcional)
            fecha_hasta: Fecha fin del rango (opcional)
            cliente_id: ID del cliente específico (opcional)
            motivo_traslado: Motivo específico de traslado (opcional)
            transportista: Nombre o RUC del transportista (opcional)
            estados: Lista de estados a incluir (opcional)
            include_transport: Incluir datos de transporte en el resultado (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[NotaRemisionElectronica]: Lista de notas de remisión que cumplen criterios

        Example:
            ```python
            # Notas de remisión del mes por traslados internos
            notas_remision = repo.get_notas_remision_by_criteria(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31),
                motivo_traslado="2",  # Traslado entre establecimientos
                estados=["aprobado"]
            )
            ```
        """
        start_time = datetime.now()

        try:
            # Construir query base
            query = self.db.query(NotaRemisionElectronica).filter(
                and_(
                    NotaRemisionElectronica.tipo_documento == "7",
                    NotaRemisionElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtros opcionales
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, NotaRemisionElectronica.fecha_emision, fecha_desde, fecha_hasta)

            if cliente_id:
                query = query.filter(
                    NotaRemisionElectronica.cliente_id == cliente_id)

            if estados:
                query = query.filter(text("estado IN :estados")).params(
                    estados=tuple(estados))

            if motivo_traslado:
                # Filtrar por motivo en el campo motivo_traslado
                query = query.filter(
                    NotaRemisionElectronica.motivo_traslado.like(f"%{MOTIVOS_TRASLADO_VALIDOS.get(motivo_traslado, motivo_traslado)}%"))

            if transportista:
                # Filtrar por transportista en el campo transportista_nombre
                query = query.filter(
                    func.lower(NotaRemisionElectronica.transportista_nombre).like(f"%{transportista.lower()}%"))

            # Incluir datos de transporte si se solicita
            if include_transport:
                # TODO: Implementar cuando relaciones de transporte estén disponibles
                # query = query.options(joinedload(NotaRemisionElectronica.transporte))
                pass

            # Aplicar límites y ordenamiento
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            notas_remision = query.order_by(desc(NotaRemisionElectronica.fecha_emision)).offset(
                offset).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_notas_remision_by_criteria", duration, len(notas_remision))

            return notas_remision

        except Exception as e:
            handle_repository_error(
                e, "get_notas_remision_by_criteria", "NotaRemisionElectronica")
            raise handle_database_exception(
                e, "get_notas_remision_by_criteria")

    def get_notas_remision_by_transport_route(self,
                                              empresa_id: int,
                                              ruta_origen: str,
                                              ruta_destino: str,
                                              fecha_desde: Optional[date] = None,
                                              fecha_hasta: Optional[date] = None) -> List[NotaRemisionElectronica]:
        """
        Obtiene notas de remisión por ruta de transporte específica.

        Args:
            empresa_id: ID de la empresa
            ruta_origen: Origen de la ruta
            ruta_destino: Destino de la ruta
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)

        Returns:
            List[NotaRemisionElectronica]: Notas de remisión de la ruta
        """
        return self.get_notas_remision_by_criteria(
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
            # TODO: Implementar filtros por ruta cuando campos estén disponibles
        )

    def get_notas_remision_by_transportista(self,
                                            transportista: str,
                                            empresa_id: int,
                                            fecha_desde: Optional[date] = None,
                                            fecha_hasta: Optional[date] = None) -> List[NotaRemisionElectronica]:
        """
        Obtiene notas de remisión por transportista específico.

        Args:
            transportista: Nombre o RUC del transportista
            empresa_id: ID de empresa
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)

        Returns:
            List[NotaRemisionElectronica]: Notas de remisión del transportista
        """
        return self.get_notas_remision_by_criteria(
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            transportista=transportista
        )

    def get_traslados_internos(self,
                               empresa_id: int,
                               establecimiento_origen: Optional[str] = None,
                               establecimiento_destino: Optional[str] = None,
                               fecha_desde: Optional[date] = None,
                               fecha_hasta: Optional[date] = None) -> List[NotaRemisionElectronica]:
        """
        Obtiene traslados internos entre establecimientos.

        Args:
            empresa_id: ID de la empresa
            establecimiento_origen: Código establecimiento origen (opcional)
            establecimiento_destino: Código establecimiento destino (opcional)
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)

        Returns:
            List[NotaRemisionElectronica]: Traslados internos
        """
        return self.get_notas_remision_by_criteria(
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            motivo_traslado="2"  # Traslado entre establecimientos
        )

    # ===============================================
    # REPORTES Y ESTADÍSTICAS
    # ===============================================

    def get_nota_remision_stats(self,
                                empresa_id: int,
                                fecha_desde: Optional[date] = None,
                                fecha_hasta: Optional[date] = None,
                                periodo: str = "monthly") -> Dict[str, Any]:
        """
        Estadísticas específicas de notas de remisión para una empresa.

        Genera métricas detalladas de notas de remisión para reportes logísticos
        y análisis de movimientos de mercaderías.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período (opcional)
            fecha_hasta: Fecha fin del período (opcional)
            periodo: Tipo de período para agregación (daily, weekly, monthly)

        Returns:
            Dict[str, Any]: Estadísticas detalladas de notas de remisión

        Example:
            ```python
            stats = repo.get_nota_remision_stats(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            print(f"Total traslados: {stats['movimientos']['total_traslados']}")
            ```
        """
        start_time = datetime.now()

        try:
            # Construir query base
            query = self.db.query(NotaRemisionElectronica).filter(
                and_(
                    NotaRemisionElectronica.tipo_documento == "7",
                    NotaRemisionElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtro de fechas
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, NotaRemisionElectronica.fecha_emision, fecha_desde, fecha_hasta)

            # Obtener todas las notas de remisión del período
            notas_remision = query.all()

            # Calcular estadísticas básicas
            total_notas = len(notas_remision)

            if total_notas == 0:
                return self._get_empty_nre_stats()

            # Contar por estado
            notas_por_estado = {}
            for nota in notas_remision:
                estado = getattr(nota, 'estado', 'unknown')
                notas_por_estado[estado] = notas_por_estado.get(estado, 0) + 1

            # Análisis por motivo de traslado
            traslados_por_motivo = self._analyze_transfers_by_motive(
                notas_remision)

            # Análisis por transportista
            traslados_por_transportista = self._analyze_transfers_by_transporter(
                notas_remision)

            # Análisis temporal
            datos_por_periodo = {}
            if periodo and notas_remision:
                datos_periodo = [
                    {
                        "fecha": getattr(nr, 'fecha_emision', date.today()),
                        "cantidad": 1
                    }
                    for nr in notas_remision
                ]
                datos_por_periodo = aggregate_by_period(
                    datos_periodo, "fecha", "cantidad", periodo)

            # Estadísticas de performance
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_nota_remision_stats", duration, total_notas)

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                    "tipo_periodo": periodo
                },
                "movimientos": {
                    "total_traslados": total_notas,
                    "traslados_por_motivo": traslados_por_motivo,
                    "traslados_por_transportista": traslados_por_transportista
                },
                "estados": notas_por_estado,
                "datos_por_periodo": datos_por_periodo,
                "metadatos": {
                    "generado_en": datetime.now().isoformat(),
                    "tiempo_procesamiento": round(duration, 3)
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_nota_remision_stats", "NotaRemisionElectronica")
            raise handle_database_exception(e, "get_nota_remision_stats")

    def get_logistics_summary(self,
                              empresa_id: int,
                              fecha_desde: date,
                              fecha_hasta: date) -> Dict[str, Any]:
        """
        Resumen logístico por período.

        Genera un resumen detallado de todos los movimientos logísticos
        mediante notas de remisión para análisis operacional.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Resumen detallado logístico

        Example:
            ```python
            resumen_logistico = repo.get_logistics_summary(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            ```
        """
        try:
            # Obtener notas de remisión del período
            notas_remision = self.get_notas_remision_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                # Solo documentos válidos
                estados=["aprobado", "aprobado_observacion"]
            )

            # Análisis por motivo
            traslados_por_motivo = self._analyze_transfers_by_motive(
                notas_remision)

            # Análisis temporal
            traslados_por_dia = {}
            for nota in notas_remision:
                fecha = getattr(nota, 'fecha_emision', date.today())
                dia_key = fecha.isoformat()

                if dia_key not in traslados_por_dia:
                    traslados_por_dia[dia_key] = 0

                traslados_por_dia[dia_key] += 1

            # Estadísticas de transportistas
            transportistas_stats = self._analyze_transporter_performance(
                notas_remision)

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "dias": (fecha_hasta - fecha_desde).days + 1
                },
                "totales": {
                    "total_traslados": len(notas_remision),
                    "promedio_diario": len(notas_remision) / ((fecha_hasta - fecha_desde).days + 1)
                },
                "traslados_por_motivo": traslados_por_motivo,
                "distribucion_temporal": traslados_por_dia,
                "transportistas": transportistas_stats,
                "indicadores": {
                    "dia_mas_activo": max(traslados_por_dia.items(), key=lambda x: x[1])[0] if traslados_por_dia else None,
                    "promedio_traslados_por_transportista": len(notas_remision) / len(transportistas_stats) if transportistas_stats else 0
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_logistics_summary", "NotaRemisionElectronica")
            raise handle_database_exception(e, "get_logistics_summary")

    def get_transport_efficiency_analysis(self,
                                          empresa_id: int,
                                          meses_atras: int = 6) -> Dict[str, Any]:
        """
        Análisis de eficiencia de transporte y tendencias logísticas.

        Analiza la eficiencia de los transportes en los últimos meses
        para identificar patrones y optimizaciones.

        Args:
            empresa_id: ID de la empresa
            meses_atras: Número de meses hacia atrás a analizar

        Returns:
            Dict[str, Any]: Análisis de eficiencia de transporte

        Example:
            ```python
            analisis_eficiencia = repo.get_transport_efficiency_analysis(empresa_id=1, meses_atras=12)
            ```
        """
        try:
            # Calcular fechas del análisis
            fecha_fin = date.today()
            fecha_inicio = fecha_fin.replace(
                day=1) - timedelta(days=meses_atras*30)

            # Obtener notas de remisión del período
            notas_remision = self.get_notas_remision_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_inicio,
                fecha_hasta=fecha_fin,
                estados=["aprobado", "aprobado_observacion"]
            )

            # Análisis por mes
            traslados_por_mes = {}
            for nota in notas_remision:
                fecha_emision = getattr(nota, 'fecha_emision', date.today())
                mes_key = fecha_emision.strftime("%Y-%m")

                if mes_key not in traslados_por_mes:
                    traslados_por_mes[mes_key] = {
                        "cantidad_traslados": 0,
                        "transportistas_unicos": set()
                    }

                traslados_por_mes[mes_key]["cantidad_traslados"] += 1
                transportista = getattr(
                    nota, 'transportista_nombre', 'Sin especificar')
                traslados_por_mes[mes_key]["transportistas_unicos"].add(
                    transportista)

            # Convertir sets a counts
            for mes_data in traslados_por_mes.values():
                mes_data["transportistas_unicos"] = len(
                    mes_data["transportistas_unicos"])

            # Análisis de eficiencia por transportista
            eficiencia_transportistas = self._analyze_transporter_efficiency(
                notas_remision)

            # Tendencias generales
            total_traslados = len(notas_remision)
            transportistas_unicos = len(set(getattr(
                nr, 'transportista_nombre', 'Sin especificar') for nr in notas_remision))

            return {
                "periodo_analisis": {
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": fecha_fin.isoformat(),
                    "meses_analizados": meses_atras
                },
                "traslados_por_mes": {
                    mes: {
                        "cantidad_traslados": datos["cantidad_traslados"],
                        "transportistas_unicos": datos["transportistas_unicos"]
                    }
                    for mes, datos in traslados_por_mes.items()
                },
                "eficiencia_transportistas": eficiencia_transportistas,
                "totales_periodo": {
                    "total_traslados": total_traslados,
                    "transportistas_unicos": transportistas_unicos
                },
                "indicadores": {
                    "traslados_promedio_mensual": total_traslados / meses_atras if meses_atras > 0 else 0,
                    "traslados_promedio_por_transportista": total_traslados / transportistas_unicos if transportistas_unicos > 0 else 0
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_transport_efficiency_analysis", "NotaRemisionElectronica")
            raise handle_database_exception(
                e, "get_transport_efficiency_analysis")


# ===============================================
    # HELPERS INTERNOS
    # ===============================================

    def _apply_nre_defaults(self, data: Dict[str, Any]) -> None:
        """
        Aplica configuraciones por defecto específicas de notas de remisión.

        Args:
            data: Diccionario de datos a modificar in-place
        """
        # Aplicar defaults base desde auxiliares
        apply_default_config(data, "7")  # Tipo 7 = Nota Remisión

        # Aplicar defaults específicos adicionales
        for key, default_value in NRE_DEFAULTS.items():
            if key not in data or data[key] is None:
                data[key] = default_value

        # Configuraciones especiales para NRE
        if "fecha_emision" not in data:
            data["fecha_emision"] = date.today()

        if "estado" not in data:
            data["estado"] = EstadoDocumentoSifenEnum.BORRADOR.value

    def _validate_nota_remision_item(self, item: Dict[str, Any], index: int) -> None:
        """
        Valida un item individual de la nota de remisión.

        Args:
            item: Datos del item a validar
            index: Índice del item en la lista

        Raises:
            SifenValidationError: Si el item no es válido
        """
        # Campos requeridos en items de NRE
        required_fields = ["descripcion", "cantidad"]

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

        # Validar precio unitario en cero (característico de NRE)
        if "precio_unitario" in item:
            try:
                precio = Decimal(str(item["precio_unitario"]))
                if precio != 0:
                    logger.warning(
                        "NRE_ITEM_PRECIO_NO_CERO",
                        extra={
                            "modulo": "document_types_t7",
                            "item_index": index,
                            "precio": float(precio),
                            "mensaje": "Item con precio no cero - NRE debe tener precios = 0"
                        }
                    )
            except (ValueError, TypeError):
                # Si no se puede convertir, se ajustará a 0 en adjust_items_for_remision
                pass

    def _validate_zero_amounts(self, nota_data: Dict[str, Any]) -> None:
        """
        Valida que todos los montos estén en cero (característica de NRE).

        Args:
            nota_data: Datos de la nota de remisión

        Raises:
            SifenValidationError: Si hay montos no cero
        """
        amount_fields = [
            "total_general", "total_operacion", "total_iva",
            "subtotal_exento", "subtotal_exonerado",
            "subtotal_gravado_5", "subtotal_gravado_10"
        ]

        for field in amount_fields:
            if field in nota_data:
                try:
                    monto = Decimal(str(nota_data[field]))
                    if monto != 0:
                        raise SifenValidationError(
                            f"Notas de remisión deben tener {field} = 0 (documento logístico sin valor comercial)",
                            field=field,
                            value=monto
                        )
                except (ValueError, TypeError):
                    raise SifenValidationError(
                        f"Formato inválido para {field}",
                        field=field,
                        value=nota_data[field]
                    )

    def _validate_motivo_specific_rules(self, motivo_traslado: str,
                                        nota_data: Dict[str, Any],
                                        datos_transporte: Dict[str, Any]) -> None:
        """
        Valida reglas específicas según el motivo de traslado.

        Args:
            motivo_traslado: Código del motivo de traslado
            nota_data: Datos de la nota
            datos_transporte: Datos de transporte
        """
        # Motivo 2: Traslado entre establecimientos - emisor = receptor
        if motivo_traslado == "2":
            if "cliente_id" in nota_data and "empresa_id" in nota_data:
                if nota_data["cliente_id"] != nota_data["empresa_id"]:
                    logger.warning(
                        "NRE_TRASLADO_INTERNO_DIFERENTE_RECEPTOR",
                        extra={
                            "modulo": "document_types_t7",
                            "motivo": motivo_traslado,
                            "empresa_id": nota_data["empresa_id"],
                            "cliente_id": nota_data["cliente_id"]
                        }
                    )

        # Motivo 1: Traslado por venta - debe tener datos de entrega
        elif motivo_traslado == "1":
            if not datos_transporte.get("direccion_destino") and not datos_transporte.get("transportista_nombre"):
                raise SifenValidationError(
                    "Traslados por venta requieren datos de entrega (dirección destino o transportista)",
                    field="datos_transporte"
                )

    def _validate_transport_condition_requirements(self, datos_transporte: Dict[str, Any]) -> None:
        """
        Valida requisitos específicos según la condición de transporte.

        Args:
            datos_transporte: Datos de transporte a validar
        """
        condicion = datos_transporte.get("condicion_transporte", "")

        # Transporte contratado (2) - requiere datos del transportista
        if condicion == "2":
            required_fields = ["transportista_nombre",
                               "vehiculo_chapa", "conductor_nombre"]
            for field in required_fields:
                if not datos_transporte.get(field):
                    raise SifenValidationError(
                        f"Transporte contratado requiere: {field}",
                        field=field
                    )

        # Transporte propio (1) - puede requerir menos datos
        elif condicion == "1":
            if not datos_transporte.get("vehiculo_chapa"):
                logger.warning(
                    "NRE_TRANSPORTE_PROPIO_SIN_VEHICULO",
                    extra={
                        "modulo": "document_types_t7",
                        "mensaje": "Transporte propio sin datos de vehículo especificados"
                    }
                )

    def _integrate_transport_data(self, data_dict: Dict[str, Any], datos_transporte: Dict[str, Any]) -> None:
        """
        Integra datos de transporte en el documento principal.

        Args:
            data_dict: Datos del documento a modificar
            datos_transporte: Datos de transporte a integrar
        """
        # Integrar campos principales de transporte
        transport_mapping = {
            "motivo_traslado": "motivo_traslado",
            "fecha_inicio_traslado": "fecha_inicio_traslado",
            "fecha_fin_traslado": "fecha_fin_traslado",
            "transportista_ruc": "transportista_ruc",
            "transportista_nombre": "transportista_nombre"
        }

        for source_field, target_field in transport_mapping.items():
            if source_field in datos_transporte:
                data_dict[target_field] = datos_transporte[source_field]

    def _estimate_distance(self, origen: Dict[str, Any], destino: Dict[str, Any]) -> float:
        """
        Estima distancia entre origen y destino (placeholder).

        Args:
            origen: Datos del origen
            destino: Datos del destino

        Returns:
            float: Distancia estimada en kilómetros
        """
        # TODO: Implementar cálculo real de distancia usando APIs de mapas
        # Por ahora retornar estimación básica
        return 50.0  # 50 km por defecto

    def _estimate_delivery_time(self, distancia_km: float, modalidad_transporte: str) -> float:
        """
        Estima tiempo de entrega basado en distancia y modalidad.

        Args:
            distancia_km: Distancia en kilómetros
            modalidad_transporte: Modalidad de transporte

        Returns:
            float: Tiempo estimado en horas
        """
        # Velocidades promedio por modalidad (km/h)
        velocidades = {
            "1": 60,  # Terrestre
            "2": 25,  # Fluvial
            "3": 500,  # Aéreo
            "4": 30   # Marítimo
        }

        velocidad = velocidades.get(modalidad_transporte, 60)
        return distancia_km / velocidad

    def _analyze_transfers_by_motive(self, notas_remision: List[NotaRemisionElectronica]) -> Dict[str, Any]:
        """
        Analiza traslados por motivo.

        Args:
            notas_remision: Lista de notas de remisión a analizar

        Returns:
            Dict[str, Any]: Análisis por motivo
        """
        analisis = {}

        for motivo_codigo, motivo_desc in MOTIVOS_TRASLADO_VALIDOS.items():
            analisis[motivo_codigo] = {
                "descripcion": motivo_desc,
                "cantidad": 0,
                "porcentaje": 0.0
            }

        total_notas = len(notas_remision)

        # Contar por motivo (análisis del campo motivo_traslado)
        for nota in notas_remision:
            motivo_texto = getattr(nota, 'motivo_traslado', '').lower()

            # Clasificar por palabras clave
            motivo_identificado = "99"  # Otro por defecto

            if "venta" in motivo_texto:
                motivo_identificado = "1"
            elif "establecimiento" in motivo_texto or "interno" in motivo_texto:
                motivo_identificado = "2"
            elif "importac" in motivo_texto:
                motivo_identificado = "3"
            elif "exportac" in motivo_texto:
                motivo_identificado = "4"
            elif "entrega" in motivo_texto or "delivery" in motivo_texto:
                motivo_identificado = "1"  # Considerar como venta

            if motivo_identificado in analisis:
                analisis[motivo_identificado]["cantidad"] += 1

        # Calcular porcentajes
        for motivo_data in analisis.values():
            if total_notas > 0:
                motivo_data["porcentaje"] = (
                    motivo_data["cantidad"] / total_notas) * 100

        return analisis

    def _analyze_transfers_by_transporter(self, notas_remision: List[NotaRemisionElectronica]) -> Dict[str, Any]:
        """
        Analiza traslados por transportista.

        Args:
            notas_remision: Lista de notas de remisión a analizar

        Returns:
            Dict[str, Any]: Análisis por transportista
        """
        transportistas = {}

        for nota in notas_remision:
            transportista = getattr(
                nota, 'transportista_nombre', 'Sin especificar')

            if transportista not in transportistas:
                transportistas[transportista] = {
                    "cantidad_traslados": 0,
                    "ruc": getattr(nota, 'transportista_ruc', '')
                }

            transportistas[transportista]["cantidad_traslados"] += 1

        return transportistas

    def _analyze_transporter_performance(self, notas_remision: List[NotaRemisionElectronica]) -> Dict[str, Any]:
        """
        Analiza performance de transportistas.

        Args:
            notas_remision: Lista de notas de remisión a analizar

        Returns:
            Dict[str, Any]: Análisis de performance
        """
        performance = {}

        for nota in notas_remision:
            transportista = getattr(
                nota, 'transportista_nombre', 'Sin especificar')

            if transportista not in performance:
                performance[transportista] = {
                    "total_traslados": 0,
                    "estados": {},
                    "eficiencia": 0.0
                }

            performance[transportista]["total_traslados"] += 1

            estado = getattr(nota, 'estado', 'unknown')
            if estado not in performance[transportista]["estados"]:
                performance[transportista]["estados"][estado] = 0
            performance[transportista]["estados"][estado] += 1

        # Calcular eficiencia (% de documentos aprobados)
        for transportista, data in performance.items():
            total = data["total_traslados"]
            aprobados = data["estados"].get(
                "aprobado", 0) + data["estados"].get("aprobado_observacion", 0)
            data["eficiencia"] = (aprobados / total *
                                  100) if total > 0 else 0.0

        return performance

    def _analyze_transporter_efficiency(self, notas_remision: List[NotaRemisionElectronica]) -> Dict[str, Any]:
        """
        Analiza eficiencia detallada de transportistas.

        Args:
            notas_remision: Lista de notas de remisión a analizar

        Returns:
            Dict[str, Any]: Análisis de eficiencia detallado
        """
        eficiencia = {}

        for nota in notas_remision:
            transportista = getattr(
                nota, 'transportista_nombre', 'Sin especificar')

            if transportista not in eficiencia:
                eficiencia[transportista] = {
                    "traslados_exitosos": 0,
                    "traslados_totales": 0,
                    "tasa_exito": 0.0,
                    "tiempo_promedio_procesamiento": 0.0
                }

            eficiencia[transportista]["traslados_totales"] += 1

            estado = getattr(nota, 'estado', 'unknown')
            if estado in ["aprobado", "aprobado_observacion"]:
                eficiencia[transportista]["traslados_exitosos"] += 1

        # Calcular tasas de éxito
        for transportista, data in eficiencia.items():
            total = data["traslados_totales"]
            exitosos = data["traslados_exitosos"]
            data["tasa_exito"] = (exitosos / total * 100) if total > 0 else 0.0

        return eficiencia

    def _get_empty_nre_stats(self) -> Dict[str, Any]:
        """
        Retorna estructura de estadísticas vacía para NRE.

        Returns:
            Dict[str, Any]: Estadísticas con valores en cero
        """
        return {
            "periodo": {
                "fecha_desde": None,
                "fecha_hasta": None,
                "tipo_periodo": "monthly"
            },
            "movimientos": {
                "total_traslados": 0,
                "traslados_por_motivo": {
                    motivo: {
                        "descripcion": desc,
                        "cantidad": 0,
                        "porcentaje": 0.0
                    }
                    for motivo, desc in MOTIVOS_TRASLADO_VALIDOS.items()
                },
                "traslados_por_transportista": {}
            },
            "estados": {},
            "datos_por_periodo": {},
            "metadatos": {
                "generado_en": datetime.now().isoformat(),
                "tiempo_procesamiento": 0.0
            }
        }

    def _format_nre_response(self, nota_remision: NotaRemisionElectronica, include_details: bool = False) -> Dict[str, Any]:
        """
        Formatea respuesta con datos específicos de notas de remisión.

        Args:
            nota_remision: Instancia de nota de remisión a formatear
            include_details: Incluir detalles adicionales

        Returns:
            Dict[str, Any]: Nota de remisión formateada para respuesta
        """
        response = {
            "id": getattr(nota_remision, 'id', None),
            "cdc": getattr(nota_remision, 'cdc', ''),
            "numero_completo": getattr(nota_remision, 'numero_completo', ''),
            "fecha_emision": getattr(nota_remision, 'fecha_emision', date.today()).isoformat(),
            "cliente_id": getattr(nota_remision, 'cliente_id', None),
            # Siempre 0 para NRE
            "total_general": float(getattr(nota_remision, 'total_general', 0)),
            "moneda": getattr(nota_remision, 'moneda', 'PYG'),
            "estado": getattr(nota_remision, 'estado', 'unknown'),
            "tipo_documento": "Nota de Remisión Electrónica",
            "motivo_traslado": getattr(nota_remision, 'motivo_traslado', ''),
            "transportista_nombre": getattr(nota_remision, 'transportista_nombre', ''),
            "fecha_inicio_traslado": getattr(nota_remision, 'fecha_inicio_traslado', date.today()).isoformat() if getattr(nota_remision, 'fecha_inicio_traslado', None) else None
        }

        if include_details:
            response.update({
                "tipo_operacion": getattr(nota_remision, 'tipo_operacion', '1'),
                "condicion_operacion": getattr(nota_remision, 'condicion_operacion', '1'),
                "observaciones": getattr(nota_remision, 'observaciones', ''),
                "numero_protocolo": getattr(nota_remision, 'numero_protocolo', ''),
                "fecha_creacion": getattr(nota_remision, 'created_at', datetime.now()).isoformat(),
                "fecha_actualizacion": getattr(nota_remision, 'updated_at', datetime.now()).isoformat(),
                "transportista_ruc": getattr(nota_remision, 'transportista_ruc', ''),
                "fecha_fin_traslado": getattr(nota_remision, 'fecha_fin_traslado', date.today()).isoformat() if getattr(nota_remision, 'fecha_fin_traslado', None) else None
            })

        return response

    # ===============================================
    # MÉTODOS DE CONVENIENCIA ADICIONALES
    # ===============================================

    def get_active_transports_by_date(self, fecha_traslado: date, empresa_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene transportes activos por fecha específica.

        Args:
            fecha_traslado: Fecha de traslado a consultar
            empresa_id: ID de la empresa

        Returns:
            List[Dict[str, Any]]: Lista de transportes activos

        Example:
            ```python
            transportes_activos = repo.get_active_transports_by_date(date.today(), empresa_id=1)
            ```
        """
        try:
            # Buscar notas con traslados en la fecha especificada
            notas_traslado = self.db.query(NotaRemisionElectronica).filter(
                and_(
                    NotaRemisionElectronica.tipo_documento == "7",
                    NotaRemisionElectronica.empresa_id == empresa_id,
                    NotaRemisionElectronica.fecha_inicio_traslado <= fecha_traslado,
                    or_(
                        NotaRemisionElectronica.fecha_fin_traslado >= fecha_traslado,
                        NotaRemisionElectronica.fecha_fin_traslado.is_(None)
                    )
                )
            ).all()

            return [self._format_nre_response(nota, include_details=True)
                    for nota in notas_traslado]

        except Exception as e:
            handle_repository_error(
                e, "get_active_transports_by_date", "NotaRemisionElectronica")
            raise handle_database_exception(e, "get_active_transports_by_date")

    def calculate_transport_capacity(self, transportista: str,
                                     fecha_desde: date,
                                     fecha_hasta: date,
                                     empresa_id: int) -> Dict[str, Any]:
        """
        Calcula capacidad de transporte de un transportista.

        Args:
            transportista: Nombre del transportista
            fecha_desde: Fecha inicio del análisis
            fecha_hasta: Fecha fin del análisis
            empresa_id: ID de la empresa

        Returns:
            Dict[str, Any]: Análisis de capacidad de transporte

        Example:
            ```python
            capacidad = repo.calculate_transport_capacity(
                "Transportes SA",
                date(2025, 1, 1),
                date(2025, 1, 31),
                empresa_id=1
            )
            ```
        """
        try:
            # Obtener traslados del transportista en el período
            traslados = self.get_notas_remision_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                transportista=transportista,
                estados=["aprobado", "aprobado_observacion"]
            )

            # Calcular métricas de capacidad
            total_traslados = len(traslados)
            dias_periodo = (fecha_hasta - fecha_desde).days + 1

            # Análisis por día
            traslados_por_dia = {}
            for traslado in traslados:
                fecha = getattr(traslado, 'fecha_inicio_traslado', getattr(
                    traslado, 'fecha_emision', date.today()))
                dia_key = fecha.isoformat()

                if dia_key not in traslados_por_dia:
                    traslados_por_dia[dia_key] = 0
                traslados_por_dia[dia_key] += 1

            # Métricas de capacidad
            dia_mas_activo = max(traslados_por_dia.values()
                                 ) if traslados_por_dia else 0
            promedio_diario = total_traslados / dias_periodo if dias_periodo > 0 else 0

            return {
                "transportista": transportista,
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "dias_analizados": dias_periodo
                },
                "capacidad": {
                    "total_traslados": total_traslados,
                    "promedio_traslados_diario": round(promedio_diario, 2),
                    "dia_mas_activo": dia_mas_activo,
                    # Asumiendo capacidad de 10 traslados/día
                    "utilizacion_porcentaje": round((total_traslados / (dias_periodo * 10)) * 100, 2)
                },
                "distribucion_diaria": traslados_por_dia,
                "recomendaciones": self._generate_capacity_recommendations(promedio_diario, dia_mas_activo)
            }

        except Exception as e:
            handle_repository_error(
                e, "calculate_transport_capacity", "NotaRemisionElectronica")
            raise handle_database_exception(e, "calculate_transport_capacity")

    def validate_transport_schedule(self, transportista: str,
                                    fecha_traslado: date,
                                    empresa_id: int) -> Dict[str, Any]:
        """
        Valida disponibilidad de transportista para una fecha.

        Args:
            transportista: Nombre del transportista
            fecha_traslado: Fecha propuesta para traslado
            empresa_id: ID de la empresa

        Returns:
            Dict[str, Any]: Resultado de validación de disponibilidad

        Example:
            ```python
            disponibilidad = repo.validate_transport_schedule(
                "Transportes SA", 
                date.today(), 
                empresa_id=1
            )
            ```
        """
        try:
            # Obtener traslados existentes del transportista en la fecha
            traslados_existentes = self.db.query(NotaRemisionElectronica).filter(
                and_(
                    NotaRemisionElectronica.tipo_documento == "7",
                    NotaRemisionElectronica.empresa_id == empresa_id,
                    func.lower(NotaRemisionElectronica.transportista_nombre).like(
                        f"%{transportista.lower()}%"),
                    NotaRemisionElectronica.fecha_inicio_traslado == fecha_traslado
                )
            ).count()

            # Capacidad máxima asumida por día
            capacidad_maxima = 5  # TODO: Configurar por transportista

            disponible = traslados_existentes < capacidad_maxima

            return {
                "transportista": transportista,
                "fecha_consulta": fecha_traslado.isoformat(),
                "disponibilidad": {
                    "disponible": disponible,
                    "traslados_programados": traslados_existentes,
                    "capacidad_maxima": capacidad_maxima,
                    "espacios_disponibles": max(0, capacidad_maxima - traslados_existentes)
                },
                "recomendacion": "Disponible para programar" if disponible else "Capacidad completa - considerar otra fecha",
                "fechas_alternativas": self._suggest_alternative_dates(transportista, fecha_traslado, empresa_id) if not disponible else []
            }

        except Exception as e:
            handle_repository_error(
                e, "validate_transport_schedule", "NotaRemisionElectronica")
            raise handle_database_exception(e, "validate_transport_schedule")

    def _generate_capacity_recommendations(self, promedio_diario: float, dia_mas_activo: int) -> List[str]:
        """
        Genera recomendaciones basadas en análisis de capacidad.

        Args:
            promedio_diario: Promedio de traslados por día
            dia_mas_activo: Máximo traslados en un día

        Returns:
            List[str]: Lista de recomendaciones
        """
        recomendaciones = []

        if promedio_diario < 2:
            recomendaciones.append(
                "Baja utilización - considerar consolidar rutas")
        elif promedio_diario > 8:
            recomendaciones.append(
                "Alta utilización - evaluar capacidad adicional")

        if dia_mas_activo > 10:
            recomendaciones.append(
                "Picos de alta demanda - planificar mejor distribución")

        if not recomendaciones:
            recomendaciones.append("Utilización óptima del transportista")

        return recomendaciones

    def _suggest_alternative_dates(self, transportista: str, fecha_original: date, empresa_id: int) -> List[str]:
        """
        Sugiere fechas alternativas cuando un transportista no está disponible.

        Args:
            transportista: Nombre del transportista
            fecha_original: Fecha original solicitada
            empresa_id: ID de la empresa

        Returns:
            List[str]: Fechas alternativas disponibles
        """
        alternativas = []

        # Revisar 7 días siguientes
        for i in range(1, 8):
            fecha_alternativa = fecha_original + timedelta(days=i)

            disponibilidad = self.validate_transport_schedule(
                transportista, fecha_alternativa, empresa_id)

            if disponibilidad["disponibilidad"]["disponible"]:
                alternativas.append(fecha_alternativa.isoformat())

            if len(alternativas) >= 3:  # Máximo 3 alternativas
                break

        return alternativas

    def get_transport_routes_summary(self, empresa_id: int,
                                     fecha_desde: date,
                                     fecha_hasta: date) -> Dict[str, Any]:
        """
        Resumen de rutas de transporte más utilizadas.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del análisis
            fecha_hasta: Fecha fin del análisis

        Returns:
            Dict[str, Any]: Resumen de rutas de transporte

        Example:
            ```python
            rutas = repo.get_transport_routes_summary(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            ```
        """
        try:
            # Obtener notas de remisión del período
            notas_remision = self.get_notas_remision_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                estados=["aprobado", "aprobado_observacion"]
            )

            # Análisis de rutas (simplificado por ahora)
            rutas_populares = {}

            for nota in notas_remision:
                # Crear clave de ruta basada en establecimiento y motivo
                establecimiento = getattr(nota, 'establecimiento', 'N/A')
                motivo = getattr(nota, 'motivo_traslado', 'Sin especificar')

                ruta_key = f"{establecimiento} - {motivo}"

                if ruta_key not in rutas_populares:
                    rutas_populares[ruta_key] = {
                        "cantidad_traslados": 0,
                        "transportistas_usados": set()
                    }

                rutas_populares[ruta_key]["cantidad_traslados"] += 1
                transportista = getattr(
                    nota, 'transportista_nombre', 'Sin especificar')
                rutas_populares[ruta_key]["transportistas_usados"].add(
                    transportista)

            # Convertir sets a listas para serialización
            for ruta_data in rutas_populares.values():
                ruta_data["transportistas_usados"] = list(
                    ruta_data["transportistas_usados"])
                ruta_data["cantidad_transportistas"] = len(
                    ruta_data["transportistas_usados"])

            # Ordenar por popularidad
            rutas_ordenadas = dict(sorted(rutas_populares.items(),
                                          key=lambda x: x[1]["cantidad_traslados"],
                                          reverse=True))

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat()
                },
                "resumen": {
                    "total_rutas_identificadas": len(rutas_ordenadas),
                    "total_traslados": len(notas_remision)
                },
                "rutas_populares": rutas_ordenadas,
                "recomendaciones": self._generate_route_recommendations(rutas_ordenadas)
            }

        except Exception as e:
            handle_repository_error(
                e, "get_transport_routes_summary", "NotaRemisionElectronica")
            raise handle_database_exception(e, "get_transport_routes_summary")

    def _generate_route_recommendations(self, rutas_ordenadas: Dict[str, Any]) -> List[str]:
        """
        Genera recomendaciones basadas en análisis de rutas.

        Args:
            rutas_ordenadas: Rutas ordenadas por popularidad

        Returns:
            List[str]: Lista de recomendaciones
        """
        recomendaciones = []

        if not rutas_ordenadas:
            return ["No hay datos suficientes para generar recomendaciones"]

        # Ruta más popular
        ruta_top = list(rutas_ordenadas.items())[0]
        recomendaciones.append(
            f"Ruta más utilizada: {ruta_top[0]} ({ruta_top[1]['cantidad_traslados']} traslados)")

        # Rutas con pocos transportistas
        rutas_monotransportista = [ruta for ruta, data in rutas_ordenadas.items()
                                   if data["cantidad_transportistas"] == 1 and data["cantidad_traslados"] > 5]

        if rutas_monotransportista:
            recomendaciones.append(
                f"Considerar diversificar transportistas en rutas frecuentes: {len(rutas_monotransportista)} rutas identificadas")

        return recomendaciones


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "DocumentTypesMixinT7",
    "NRE_DEFAULTS",
    "MOTIVOS_TRASLADO_VALIDOS",
    "RESPONSABLES_FLETE",
    "CONDICIONES_TRANSPORTE",
    "MODALIDADES_TRANSPORTE"
]
