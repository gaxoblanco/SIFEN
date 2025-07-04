# ===============================================
# ARCHIVO: backend/app/repositories/documento/document_types_mixin_t6.py
# PROPÓSITO: Mixin para operaciones específicas de Notas de Débito Electrónicas (NDE - Tipo 6)
# VERSIÓN: 1.0.0
# ===============================================

"""
Mixin para operaciones específicas de Notas de Débito Electrónicas (NDE - Tipo 6).

Este módulo implementa funcionalidades especializadas para el manejo de notas
de débito electrónicas, incluyendo:
- Creación con validaciones específicas de NDE
- Validaciones de cargos adicionales y montos positivos
- Vinculación obligatoria con documento original
- Validaciones de motivos específicos de débito
- Búsquedas optimizadas para notas de débito
- Estadísticas específicas de cargos adicionales
- Integración total con SIFEN v150

Características principales:
- Validación de documento original obligatorio
- Cálculo de cargos adicionales (intereses, gastos, multas)
- Aplicación de defaults específicos para NDE
- Búsquedas por criterios comerciales (cliente, monto, tipo cargo)
- Estadísticas de cargos y tendencias
- Conformidad total con SIFEN v150

Clase principal:
- DocumentTypesMixinT6: Mixin especializado para notas de débito electrónicas
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
    NotaDebitoElectronica,
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
    validate_nota_debito_data,
    validate_and_get_original_document,
    get_documents_by_type_and_criteria,
    calculate_totals_from_items,
    create_items_for_document,
    link_original_document
)

logger = get_logger(__name__)

# ===============================================
# CONFIGURACIONES ESPECÍFICAS PARA NDE
# ===============================================

# Defaults específicos para notas de débito electrónicas
NDE_DEFAULTS = {
    "tipo_documento": "6",
    "tipo_operacion": "1",  # Venta
    "condicion_operacion": "1",  # Contado
    "moneda": "PYG",
    "tipo_emision": "1",  # Normal
    "tipo_cambio": Decimal("1.0000")
}

# Motivos de débito válidos según SIFEN v150
MOTIVOS_DEBITO_VALIDOS = {
    "1": "Interés por mora",
    "2": "Gastos de cobranza",
    "3": "Aumento de valor",
    "4": "Recupero de costos",
    "5": "Recupero de gastos",
    "6": "Gastos bancarios",
    "7": "Ajuste de precio",
    "8": "Aumento autorizado",
    "9": "Otro motivo"
}

# Tipos de cargos adicionales
TIPOS_CARGO_ADICIONAL = {
    "interes": "Intereses por mora",
    "gasto_bancario": "Gastos bancarios",
    "gasto_cobranza": "Gastos de cobranza",
    "ajuste_precio": "Ajuste de precio",
    "multa": "Multa contractual",
    "servicio_adicional": "Servicio adicional",
    "recupero_costo": "Recupero de costo",
    "otro": "Otro cargo"
}

# ===============================================
# MIXIN PRINCIPAL
# ===============================================


class DocumentTypesMixinT6:
    """
    Mixin para operaciones específicas de Notas de Débito Electrónicas (NDE - Tipo 6).

    Proporciona métodos especializados para el manejo de notas de débito electrónicas:
    - Creación con validaciones específicas de NDE
    - Vinculación obligatoria con documento original
    - Validaciones de cargos adicionales y montos
    - Búsquedas optimizadas para notas de débito
    - Cálculos de intereses, gastos y multas
    - Estadísticas de cargos específicas
    - Integración completa con SIFEN v150

    Este mixin debe ser usado junto con DocumentoRepositoryBase para
    obtener funcionalidad completa de gestión de documentos.

    Example:
        ```python
        class DocumentoRepository(
            DocumentoRepositoryBase,
            DocumentTypesMixinT6,
            # otros mixins...
        ):
            pass

        repo = DocumentoRepository(db)
        nota_debito = repo.create_nota_debito_electronica(data, original_cdc, items)
        ```
    """

    db: Session
    model: type

    # ===============================================
    # MÉTODOS DE CREACIÓN ESPECÍFICOS
    # ===============================================

    def create_nota_debito_electronica(self,
                                       nota_data: Union[DocumentoCreateDTO, Dict[str, Any]],
                                       documento_original_cdc: str,
                                       items: List[Dict[str, Any]],
                                       apply_defaults: bool = True,
                                       validate_amounts: bool = True,
                                       auto_generate_cdc: bool = True,
                                       empresa_id: Optional[int] = None) -> NotaDebitoElectronica:
        """
        Crea una nota de débito electrónica con validaciones específicas.

        Este método es el punto de entrada principal para crear notas de débito electrónicas,
        aplicando todas las validaciones y configuraciones específicas del tipo de documento.

        Args:
            nota_data: Datos básicos de la nota de débito
            documento_original_cdc: CDC del documento original al que se debita
            items: Lista de items/cargos de la nota de débito
            apply_defaults: Aplicar configuraciones por defecto específicas
            validate_amounts: Validar cálculos de montos automáticamente
            auto_generate_cdc: Generar CDC automáticamente
            empresa_id: ID de empresa (opcional, para validaciones adicionales)

        Returns:
            NotaDebitoElectronica: Instancia de nota de débito creada

        Raises:
            SifenValidationError: Si los datos no son válidos
            SifenBusinessLogicError: Si hay errores de lógica de negocio
            SifenEntityNotFoundError: Si el documento original no existe
            SifenDuplicateEntityError: Si la numeración ya existe

        Example:
            ```python
            nota_data = {
                "establecimiento": "001",
                "punto_expedicion": "001", 
                "numero_documento": "0000125",
                "numero_timbrado": "12345678",
                "fecha_emision": date.today(),
                "motivo_debito": "Intereses por pago tardío",
                "moneda": "PYG"
            }

            items = [{
                "descripcion": "Intereses por mora - 30 días",
                "cantidad": 1,
                "precio_unitario": Decimal("150000"),
                "tipo_iva": "10"
            }]

            nota_debito = repo.create_nota_debito_electronica(
                nota_data, "12345678901234567890123456789012345678901234", items
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

            # 2. Validar y obtener documento original
            documento_original = validate_and_get_original_document(
                self.db, self.model, documento_original_cdc)

            # 3. Aplicar defaults específicos de notas de débito
            if apply_defaults:
                self._apply_nde_defaults(data_dict, documento_original)

            # 4. Validar estructura básica y reglas de negocio específicas NDE
            self.validate_nota_debito_data(
                data_dict, items, documento_original)

            # 5. Validar cálculos de montos si se solicita
            if validate_amounts:
                self.validate_debit_requirements(
                    data_dict, items, documento_original)

            # 6. Calcular totales automáticamente desde items
            calculate_totals_from_items(data_dict, items)

            # 7. Añadir referencia al documento original
            data_dict["documento_original_cdc"] = normalize_cdc(
                documento_original_cdc)

            # 8. Aplicar validaciones adicionales por empresa
            if empresa_id:
                data_dict["empresa_id"] = empresa_id

            # 9. Crear documento usando método base del repository
            nota_debito = getattr(self, 'create')(
                data_dict, auto_generate_fields=auto_generate_cdc)

            # 10. Crear items asociados a la nota de débito
            if items:
                create_items_for_document(self.db, nota_debito, items)

            # 11. Vincular documento original
            link_original_document(nota_debito, documento_original)

            # 12. Log de operación exitosa
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "create_nota_debito_electronica", duration, 1)

            log_repository_operation("create_nota_debito_electronica", "NotaDebitoElectronica",
                                     getattr(nota_debito, 'id', None), {
                                         "numero_completo": getattr(nota_debito, 'numero_completo', None),
                                         "total_general": float(getattr(nota_debito, 'total_general', 0)),
                                         "items_count": len(items),
                                         "documento_original_cdc": documento_original_cdc[:20] + "...",
                                         "motivo_debito": data_dict.get("motivo_debito", "")[:50]
                                     })

            return nota_debito

        except (SifenValidationError, SifenBusinessLogicError,
                SifenEntityNotFoundError, SifenDuplicateEntityError):
            # Re-raise errores de validación/negocio sin modificar
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            handle_repository_error(
                e, "create_nota_debito_electronica", "NotaDebitoElectronica")
            raise handle_database_exception(
                e, "create_nota_debito_electronica")

    def create_nota_debito_interes(self,
                                   numero_documento: str,
                                   documento_original_cdc: str,
                                   monto_interes: Decimal,
                                   dias_mora: int,
                                   tasa_interes_diaria: Optional[Decimal] = None,
                                   empresa_id: Optional[int] = None,
                                   observaciones: Optional[str] = None) -> NotaDebitoElectronica:
        """
        Creación específica de nota de débito por intereses de mora.

        Método de conveniencia para crear notas de débito por intereses,
        con cálculos automáticos y configuraciones predefinidas.

        Args:
            numero_documento: Número secuencial del documento
            documento_original_cdc: CDC del documento original
            monto_interes: Monto de intereses calculado
            dias_mora: Número de días de mora
            tasa_interes_diaria: Tasa de interés diaria (opcional)
            empresa_id: ID de empresa emisora
            observaciones: Observaciones adicionales

        Returns:
            NotaDebitoElectronica: Nota de débito por intereses creada

        Example:
            ```python
            nota_interes = repo.create_nota_debito_interes(
                numero_documento="0000126",
                documento_original_cdc="12345678901234567890123456789012345678901234",
                monto_interes=Decimal("200000"),
                dias_mora=45,
                tasa_interes_diaria=Decimal("0.001"),  # 0.1% diario
                empresa_id=1
            )
            ```
        """
        # TODO: Obtener datos de empresa para establecimiento y timbrado
        nota_data = {
            "establecimiento": "001",  # TODO: Desde configuración empresa
            "punto_expedicion": "001",  # TODO: Desde configuración empresa
            "numero_documento": numero_documento,
            "numero_timbrado": "12345678",  # TODO: Desde timbrado activo
            "fecha_emision": date.today(),
            "fecha_inicio_vigencia_timbrado": date.today(),  # TODO: Desde timbrado
            "fecha_fin_vigencia_timbrado": date.today() + timedelta(days=365),  # TODO: Desde timbrado
            "timbrado_id": 1,  # TODO: Desde timbrado activo
            "motivo_debito": f"Intereses por mora - {dias_mora} días",
            "total_general": monto_interes
        }

        if empresa_id:
            nota_data["empresa_id"] = empresa_id

        if observaciones:
            nota_data["observaciones"] = observaciones

        # Crear item de intereses
        items = [{
            "descripcion": f"Intereses por mora - {dias_mora} días de retraso",
            "cantidad": dias_mora,
            "precio_unitario": monto_interes / dias_mora if dias_mora > 0 else monto_interes,
            "tipo_iva": "10",  # IVA sobre intereses
            "observacion_item": f"Tasa diaria: {tasa_interes_diaria}%" if tasa_interes_diaria else None
        }]

        return self.create_nota_debito_electronica(
            nota_data=nota_data,
            documento_original_cdc=documento_original_cdc,
            items=items,
            apply_defaults=True,
            validate_amounts=True,
            auto_generate_cdc=True
        )

    def create_nota_debito_gastos(self,
                                  numero_documento: str,
                                  documento_original_cdc: str,
                                  gastos_adicionales: List[Dict[str, Any]],
                                  tipo_gasto: str = "gasto_cobranza",
                                  empresa_id: Optional[int] = None) -> NotaDebitoElectronica:
        """
        Creación específica de nota de débito por gastos adicionales.

        Args:
            numero_documento: Número secuencial del documento
            documento_original_cdc: CDC del documento original
            gastos_adicionales: Lista de gastos a incluir
            tipo_gasto: Tipo de gasto (gasto_cobranza, gasto_bancario, etc.)
            empresa_id: ID de empresa emisora

        Returns:
            NotaDebitoElectronica: Nota de débito por gastos creada

        Example:
            ```python
            gastos = [
                {"descripcion": "Gastos de gestión de cobranza", "monto": Decimal("50000")},
                {"descripcion": "Gastos bancarios por transferencia", "monto": Decimal("25000")}
            ]

            nota_gastos = repo.create_nota_debito_gastos(
                numero_documento="0000127",
                documento_original_cdc="12345678901234567890123456789012345678901234",
                gastos_adicionales=gastos,
                tipo_gasto="gasto_cobranza",
                empresa_id=1
            )
            ```
        """
        # Calcular total de gastos
        total_gastos = sum(Decimal(str(gasto.get("monto", 0)))
                           for gasto in gastos_adicionales)

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
            "motivo_debito": TIPOS_CARGO_ADICIONAL.get(tipo_gasto, "Gastos adicionales"),
            "total_general": total_gastos
        }

        if empresa_id:
            nota_data["empresa_id"] = empresa_id

        # Crear items de gastos
        items = []
        for i, gasto in enumerate(gastos_adicionales):
            item = {
                "descripcion": gasto.get("descripcion", f"Gasto adicional {i+1}"),
                "cantidad": 1,
                "precio_unitario": Decimal(str(gasto.get("monto", 0))),
                "tipo_iva": gasto.get("tipo_iva", "10")
            }
            items.append(item)

        return self.create_nota_debito_electronica(
            nota_data=nota_data,
            documento_original_cdc=documento_original_cdc,
            items=items,
            apply_defaults=True,
            validate_amounts=True,
            auto_generate_cdc=True
        )

    # ===============================================
    # VALIDACIONES ESPECÍFICAS
    # ===============================================

    def validate_nota_debito_data(self,
                                  nota_data: Dict[str, Any],
                                  items: List[Dict[str, Any]],
                                  documento_original: Documento) -> None:
        """
        Validaciones comprehensivas específicas para notas de débito electrónicas.

        Aplica todas las validaciones requeridas para una nota de débito según
        las normativas SIFEN y reglas de negocio específicas.

        Args:
            nota_data: Datos de la nota de débito a validar
            items: Items de la nota de débito a validar
            documento_original: Documento original de referencia

        Raises:
            SifenValidationError: Si alguna validación falla

        Example:
            ```python
            try:
                repo.validate_nota_debito_data(nota_data, items, documento_original)
                print("Datos válidos")
            except SifenValidationError as e:
                print(f"Error de validación: {e.message}")
            ```
        """
        # Usar validación de auxiliares como base
        validate_nota_debito_data(nota_data, documento_original)

        # Validaciones adicionales específicas de notas de débito

        # 1. Items obligatorios para NDE
        if not items or len(items) == 0:
            raise SifenValidationError(
                "Notas de débito deben tener al menos 1 item de cargo",
                field="items"
            )

        # 2. Validar cada item específicamente para NDE
        for i, item in enumerate(items):
            self._validate_nota_debito_item(item, i)

        # 3. Validar motivo de débito
        motivo_debito = nota_data.get("motivo_debito", "")
        if not motivo_debito or len(motivo_debito.strip()) < 10:
            raise SifenValidationError(
                "Motivo de débito debe ser específico y tener al menos 10 caracteres",
                field="motivo_debito",
                value=motivo_debito
            )

        # 4. Validar consistencia de partes (emisor/receptor)
        self._validate_parties_consistency(nota_data, documento_original)

        # 5. Validar fecha posterior al documento original
        fecha_emision = nota_data.get("fecha_emision")
        fecha_original = getattr(documento_original, 'fecha_emision', None)

        if fecha_emision and fecha_original and fecha_emision <= fecha_original:
            raise SifenValidationError(
                "Fecha de emisión de NDE debe ser posterior al documento original",
                field="fecha_emision",
                value=fecha_emision,
                details={
                    "fecha_nde": fecha_emision.isoformat(),
                    "fecha_original": fecha_original.isoformat()
                }
            )

    def validate_debit_requirements(self,
                                    nota_data: Dict[str, Any],
                                    items: List[Dict[str, Any]],
                                    documento_original: Documento) -> None:
        """
        Validaciones específicas de cargos adicionales para notas de débito.

        Verifica que los cálculos de cargos sean correctos y coherentes
        con la naturaleza de la nota de débito (aumentar valor).

        Args:
            nota_data: Datos de la nota de débito
            items: Items con información de cargos
            documento_original: Documento original de referencia

        Raises:
            SifenValidationError: Si los cálculos no son correctos
            SifenBusinessLogicError: Si hay inconsistencias de negocio
        """
        # Calcular totales esperados desde items
        totales_calculados = self._calculate_totals_from_items(items)

        # Validar que los montos sean positivos (característico de NDE)
        total_general = totales_calculados["total_general"]
        if total_general <= 0:
            raise SifenValidationError(
                "Notas de débito deben tener montos positivos (aumentan la deuda)",
                field="total_general",
                value=total_general
            )

        # Validar subtotales si están especificados
        campos_a_validar = [
            ("subtotal_exento", "subtotal_exento"),
            ("subtotal_exonerado", "subtotal_exonerado"),
            ("subtotal_gravado_5", "subtotal_5"),
            ("subtotal_gravado_10", "subtotal_10"),
            ("total_iva", "total_iva")
        ]

        for campo_nota, campo_calculado in campos_a_validar:
            if campo_nota in nota_data:
                valor_nota = Decimal(str(nota_data[campo_nota]))
                valor_calculado = totales_calculados[campo_calculado]

                if abs(valor_nota - valor_calculado) > Decimal("0.01"):
                    raise SifenValidationError(
                        f"{campo_nota} no coincide con cálculo desde items. "
                        f"Esperado: {valor_calculado}, Recibido: {valor_nota}",
                        field=campo_nota,
                        value=valor_nota
                    )

        # Validar total general
        if "total_general" in nota_data:
            total_nota = Decimal(str(nota_data["total_general"]))
            total_calculado = totales_calculados["total_general"]

            if abs(total_nota - total_calculado) > Decimal("0.01"):
                raise SifenValidationError(
                    f"Total general no coincide con cálculo desde items. "
                    f"Esperado: {total_calculado}, Recibido: {total_nota}",
                    field="total_general",
                    value=total_nota
                )

        # Validar razonabilidad del cargo vs documento original
        self._validate_reasonable_charges(
            nota_data, documento_original, totales_calculados)

    def calculate_additional_amounts(self,
                                     documento_original: Documento,
                                     tipo_cargo: str,
                                     parametros: Dict[str, Any]) -> Dict[str, Decimal]:
        """
        Calcula montos adicionales para diferentes tipos de cargos.

        Este método proporciona cálculos automáticos para diferentes tipos
        de cargos adicionales en notas de débito.

        Args:
            documento_original: Documento original de referencia
            tipo_cargo: Tipo de cargo a calcular (interes, gasto_bancario, etc.)
            parametros: Parámetros específicos para el cálculo

        Returns:
            Dict[str, Decimal]: Montos calculados detallados

        Raises:
            SifenValidationError: Si los parámetros no son válidos
            SifenBusinessLogicError: Si el cálculo no es posible

        Example:
            ```python
            # Calcular intereses por mora
            montos = repo.calculate_additional_amounts(
                documento_original,
                "interes",
                {
                    "dias_mora": 30,
                    "tasa_diaria": Decimal("0.001"),
                    "aplicar_iva": True
                }
            )
            # Returns: {"subtotal": Decimal("300000"), "iva": Decimal("30000"), "total": Decimal("330000")}
            ```
        """
        start_time = datetime.now()

        try:
            if tipo_cargo not in TIPOS_CARGO_ADICIONAL:
                raise SifenValidationError(
                    f"Tipo de cargo '{tipo_cargo}' no es válido",
                    field="tipo_cargo",
                    value=tipo_cargo
                )

            total_original = getattr(
                documento_original, 'total_general', Decimal("0"))

            if tipo_cargo == "interes":
                return self._calculate_interest_amounts(total_original, parametros)
            elif tipo_cargo == "gasto_bancario":
                return self._calculate_banking_fees(total_original, parametros)
            elif tipo_cargo == "gasto_cobranza":
                return self._calculate_collection_fees(total_original, parametros)
            elif tipo_cargo == "ajuste_precio":
                return self._calculate_price_adjustment(total_original, parametros)
            elif tipo_cargo == "multa":
                return self._calculate_penalty_amounts(total_original, parametros)
            else:
                return self._calculate_generic_charges(total_original, parametros)

        except (SifenValidationError, SifenBusinessLogicError):
            raise
        except Exception as e:
            handle_repository_error(
                e, "calculate_additional_amounts", "NotaDebitoElectronica")
            raise handle_database_exception(e, "calculate_additional_amounts")
        finally:
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric("calculate_additional_amounts", duration, 1)

    # ===============================================
    # BÚSQUEDAS ESPECIALIZADAS
    # ===============================================

    def get_notas_debito_by_criteria(self,
                                     empresa_id: int,
                                     fecha_desde: Optional[date] = None,
                                     fecha_hasta: Optional[date] = None,
                                     cliente_id: Optional[int] = None,
                                     monto_minimo: Optional[Decimal] = None,
                                     monto_maximo: Optional[Decimal] = None,
                                     estados: Optional[List[str]] = None,
                                     tipo_cargo: Optional[str] = None,
                                     documento_original_cdc: Optional[str] = None,
                                     include_items: bool = False,
                                     limit: Optional[int] = None,
                                     offset: int = 0) -> List[NotaDebitoElectronica]:
        """
        Búsqueda avanzada de notas de débito con múltiples criterios.

        Permite filtrar notas de débito por diversos criterios específicos del negocio,
        optimizado para consultas frecuentes en dashboards y reportes.

        Args:
            empresa_id: ID de la empresa emisora
            fecha_desde: Fecha inicio del rango (opcional)
            fecha_hasta: Fecha fin del rango (opcional)
            cliente_id: ID del cliente específico (opcional)
            monto_minimo: Monto mínimo de la nota (opcional)
            monto_maximo: Monto máximo de la nota (opcional)
            estados: Lista de estados a incluir (opcional)
            tipo_cargo: Tipo de cargo específico (opcional)
            documento_original_cdc: CDC del documento original (opcional)
            include_items: Incluir items en el resultado (opcional)
            limit: Número máximo de resultados
            offset: Número de resultados a omitir

        Returns:
            List[NotaDebitoElectronica]: Lista de notas de débito que cumplen criterios

        Example:
            ```python
            # Notas de débito del mes por intereses
            notas_debito = repo.get_notas_debito_by_criteria(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31),
                tipo_cargo="interes",
                estados=["aprobado"]
            )
            ```
        """
        start_time = datetime.now()

        try:
            # Usar helper de auxiliares como base
            query = self.db.query(NotaDebitoElectronica).filter(
                and_(
                    NotaDebitoElectronica.tipo_documento == "6",
                    NotaDebitoElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtros opcionales
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, NotaDebitoElectronica.fecha_emision, fecha_desde, fecha_hasta)

            if monto_minimo or monto_maximo:
                query = build_amount_filter(
                    query, NotaDebitoElectronica.total_general, monto_minimo, monto_maximo)

            if cliente_id:
                query = query.filter(
                    NotaDebitoElectronica.cliente_id == cliente_id)

            if estados:
                query = query.filter(text("estado IN :estados")).params(
                    estados=tuple(estados))

            if tipo_cargo:
                # Filtrar por tipo de cargo en el motivo de débito
                pattern = f"%{TIPOS_CARGO_ADICIONAL.get(tipo_cargo, tipo_cargo)}%"
                query = query.filter(
                    func.lower(NotaDebitoElectronica.motivo_debito).like(pattern.lower()))

            if documento_original_cdc:
                cdc_normalized = normalize_cdc(documento_original_cdc)
                query = query.filter(
                    NotaDebitoElectronica.documento_original_cdc == cdc_normalized)

            # Incluir items si se solicita
            if include_items:
                # TODO: Implementar cuando tabla de items esté disponible
                # query = query.options(joinedload(NotaDebitoElectronica.items))
                pass

            # Aplicar límites y ordenamiento
            if limit is None:
                limit = get_default_page_size()
            elif limit > get_max_page_size():
                limit = get_max_page_size()

            notas_debito = query.order_by(desc(NotaDebitoElectronica.fecha_emision)).offset(
                offset).limit(limit).all()

            # Log de operación
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_notas_debito_by_criteria", duration, len(notas_debito))

            return notas_debito

        except Exception as e:
            handle_repository_error(
                e, "get_notas_debito_by_criteria", "NotaDebitoElectronica")
            raise handle_database_exception(e, "get_notas_debito_by_criteria")

    def get_notas_debito_by_original_document(self,
                                              documento_original_cdc: str,
                                              empresa_id: Optional[int] = None) -> List[NotaDebitoElectronica]:
        """
        Obtiene todas las notas de débito de un documento original específico.

        Args:
            documento_original_cdc: CDC del documento original
            empresa_id: ID de empresa (opcional, para filtrar)

        Returns:
            List[NotaDebitoElectronica]: Notas de débito del documento original
        """
        cdc_normalized = normalize_cdc(documento_original_cdc)

        return self.get_notas_debito_by_criteria(
            empresa_id=empresa_id or 0,  # TODO: Obtener desde contexto
            documento_original_cdc=cdc_normalized
        )

    def get_notas_debito_by_charge_type(self,
                                        tipo_cargo: str,
                                        empresa_id: int,
                                        fecha_desde: Optional[date] = None,
                                        fecha_hasta: Optional[date] = None) -> List[NotaDebitoElectronica]:
        """
        Búsqueda de notas de débito por tipo de cargo.

        Args:
            tipo_cargo: Tipo de cargo (interes, gasto_bancario, etc.)
            empresa_id: ID de empresa
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)

        Returns:
            List[NotaDebitoElectronica]: Notas de débito filtradas por tipo de cargo
        """
        return self.get_notas_debito_by_criteria(
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            tipo_cargo=tipo_cargo
        )

    def get_notas_debito_by_client(self,
                                   cliente_id: int,
                                   empresa_id: Optional[int] = None,
                                   fecha_desde: Optional[date] = None,
                                   fecha_hasta: Optional[date] = None,
                                   limit: Optional[int] = None) -> List[NotaDebitoElectronica]:
        """
        Obtiene todas las notas de débito de un cliente específico.

        Args:
            cliente_id: ID del cliente
            empresa_id: ID de empresa (opcional, para filtrar)
            fecha_desde: Fecha inicio (opcional)
            fecha_hasta: Fecha fin (opcional)
            limit: Límite de resultados

        Returns:
            List[NotaDebitoElectronica]: Notas de débito del cliente
        """
        return self.get_notas_debito_by_criteria(
            empresa_id=empresa_id or 0,  # TODO: Obtener desde contexto
            cliente_id=cliente_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limit=limit
        )

    # ===============================================
    # REPORTES Y ESTADÍSTICAS
    # ===============================================

    def get_nota_debito_stats(self,
                              empresa_id: int,
                              fecha_desde: Optional[date] = None,
                              fecha_hasta: Optional[date] = None,
                              periodo: str = "monthly") -> Dict[str, Any]:
        """
        Estadísticas específicas de notas de débito para una empresa.

        Genera métricas detalladas de notas de débito para reportes ejecutivos
        y análisis de cargos adicionales.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período (opcional)
            fecha_hasta: Fecha fin del período (opcional)
            periodo: Tipo de período para agregación (daily, weekly, monthly)

        Returns:
            Dict[str, Any]: Estadísticas detalladas de notas de débito

        Example:
            ```python
            stats = repo.get_nota_debito_stats(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            print(f"Total cargos adicionales: {stats['monto_total_cargos']}")
            ```
        """
        start_time = datetime.now()

        try:
            # Construir query base
            query = self.db.query(NotaDebitoElectronica).filter(
                and_(
                    NotaDebitoElectronica.tipo_documento == "6",
                    NotaDebitoElectronica.empresa_id == empresa_id
                )
            )

            # Aplicar filtro de fechas
            if fecha_desde or fecha_hasta:
                query = build_date_filter(
                    query, NotaDebitoElectronica.fecha_emision, fecha_desde, fecha_hasta)

            # Obtener todas las notas de débito del período
            notas_debito = query.all()

            # Calcular estadísticas básicas
            total_notas = len(notas_debito)

            if total_notas == 0:
                return self._get_empty_nde_stats()

            # Calcular totales
            monto_total_cargos = sum(getattr(nd, 'total_general', Decimal("0"))
                                     for nd in notas_debito)
            monto_iva_cargos = sum(getattr(nd, 'total_iva', Decimal("0"))
                                   for nd in notas_debito)
            promedio_cargo = monto_total_cargos / \
                total_notas if total_notas > 0 else Decimal("0")

            # Contar por estado
            notas_por_estado = {}
            for nota in notas_debito:
                estado = getattr(nota, 'estado', 'unknown')
                notas_por_estado[estado] = notas_por_estado.get(estado, 0) + 1

            # Análisis por tipo de cargo
            cargos_por_tipo = self._analyze_charges_by_type(notas_debito)

            # Obtener clientes únicos
            clientes_unicos = len(
                set(getattr(nd, 'cliente_id', 0) for nd in notas_debito))

            # Distribución por montos
            distribucion_montos = self._calculate_charge_distribution(
                notas_debito)

            # Agregación por período si se solicita
            datos_por_periodo = {}
            if periodo and notas_debito:
                datos_periodo = [
                    {
                        "fecha": getattr(nd, 'fecha_emision', date.today()),
                        "monto": float(getattr(nd, 'total_general', 0))
                    }
                    for nd in notas_debito
                ]
                datos_por_periodo = aggregate_by_period(
                    datos_periodo, "fecha", "monto", periodo)

            # Estadísticas de performance
            duration = (datetime.now() - start_time).total_seconds()
            log_performance_metric(
                "get_nota_debito_stats", duration, total_notas)

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                    "tipo_periodo": periodo
                },
                "totales": {
                    "total_notas_debito": total_notas,
                    "monto_total_cargos": float(monto_total_cargos),
                    "monto_total_iva_cargos": float(monto_iva_cargos),
                    "promedio_por_nota": float(promedio_cargo)
                },
                "analisis_cargos": cargos_por_tipo,
                "clientes": {
                    "clientes_con_cargos": clientes_unicos,
                    "promedio_notas_por_cliente": round(total_notas / clientes_unicos, 2) if clientes_unicos > 0 else 0
                },
                "estados": notas_por_estado,
                "distribucion_montos": distribucion_montos,
                "datos_por_periodo": datos_por_periodo,
                "metadatos": {
                    "generado_en": datetime.now().isoformat(),
                    "tiempo_procesamiento": round(duration, 3)
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_nota_debito_stats", "NotaDebitoElectronica")
            raise handle_database_exception(e, "get_nota_debito_stats")

    def get_charges_summary(self,
                            empresa_id: int,
                            fecha_desde: date,
                            fecha_hasta: date) -> Dict[str, Any]:
        """
        Resumen de cargos adicionales por período.

        Genera un resumen detallado de todos los cargos adicionales aplicados
        mediante notas de débito para análisis financiero.

        Args:
            empresa_id: ID de la empresa
            fecha_desde: Fecha inicio del período
            fecha_hasta: Fecha fin del período

        Returns:
            Dict[str, Any]: Resumen detallado de cargos

        Example:
            ```python
            resumen_cargos = repo.get_charges_summary(
                empresa_id=1,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2025, 1, 31)
            )
            ```
        """
        try:
            # Obtener notas de débito del período
            notas_debito = self.get_notas_debito_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                estados=["aprobado", "aprobado_observacion"]  # Solo fiscales
            )

            # Analizar por tipo de cargo
            cargos_por_tipo = self._analyze_charges_by_type(notas_debito)

            # Totales generales
            total_cargos = sum(getattr(nd, 'total_general', Decimal("0"))
                               for nd in notas_debito)
            total_iva_cargos = sum(getattr(nd, 'total_iva', Decimal("0"))
                                   for nd in notas_debito)

            # Análisis temporal
            cargos_por_dia = {}
            for nota in notas_debito:
                fecha = getattr(nota, 'fecha_emision', date.today())
                dia_key = fecha.isoformat()

                if dia_key not in cargos_por_dia:
                    cargos_por_dia[dia_key] = {
                        "cantidad": 0,
                        "monto": Decimal("0")
                    }

                cargos_por_dia[dia_key]["cantidad"] += 1
                cargos_por_dia[dia_key]["monto"] += getattr(
                    nota, 'total_general', Decimal("0"))

            return {
                "periodo": {
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat(),
                    "dias": (fecha_hasta - fecha_desde).days + 1
                },
                "totales": {
                    "total_cargos": float(total_cargos),
                    "total_iva_cargos": float(total_iva_cargos),
                    "total_notas": len(notas_debito)
                },
                "cargos_por_tipo": cargos_por_tipo,
                "distribucion_temporal": {
                    dia: {
                        "cantidad": datos["cantidad"],
                        "monto": float(datos["monto"])
                    }
                    for dia, datos in cargos_por_dia.items()
                },
                "promedios": {
                    "cargo_promedio_diario": float(total_cargos / ((fecha_hasta - fecha_desde).days + 1)),
                    "cargo_promedio_por_nota": float(total_cargos / len(notas_debito)) if notas_debito else 0.0
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_charges_summary", "NotaDebitoElectronica")
            raise handle_database_exception(e, "get_charges_summary")

    def get_interest_analysis(self,
                              empresa_id: int,
                              meses_atras: int = 6) -> Dict[str, Any]:
        """
        Análisis de intereses y tendencias de mora.

        Analiza los intereses cobrados por mora en los últimos meses
        para identificar patrones y tendencias de pago.

        Args:
            empresa_id: ID de la empresa
            meses_atras: Número de meses hacia atrás a analizar

        Returns:
            Dict[str, Any]: Análisis de intereses y mora

        Example:
            ```python
            analisis_intereses = repo.get_interest_analysis(empresa_id=1, meses_atras=12)
            ```
        """
        try:
            # Calcular fechas del análisis
            fecha_fin = date.today()
            fecha_inicio = fecha_fin.replace(
                day=1) - timedelta(days=meses_atras*30)

            # Obtener notas de débito por intereses
            notas_interes = self.get_notas_debito_by_criteria(
                empresa_id=empresa_id,
                fecha_desde=fecha_inicio,
                fecha_hasta=fecha_fin,
                tipo_cargo="interes",
                estados=["aprobado", "aprobado_observacion"]
            )

            # Análisis por mes
            intereses_por_mes = {}
            for nota in notas_interes:
                fecha_emision = getattr(nota, 'fecha_emision', date.today())
                mes_key = fecha_emision.strftime("%Y-%m")

                if mes_key not in intereses_por_mes:
                    intereses_por_mes[mes_key] = {
                        "cantidad_notas": 0,
                        "monto_intereses": Decimal("0"),
                        "clientes_afectados": set()
                    }

                intereses_por_mes[mes_key]["cantidad_notas"] += 1
                intereses_por_mes[mes_key]["monto_intereses"] += getattr(
                    nota, 'total_general', Decimal("0"))
                intereses_por_mes[mes_key]["clientes_afectados"].add(
                    getattr(nota, 'cliente_id', 0))

            # Convertir sets a counts
            for mes_data in intereses_por_mes.values():
                mes_data["clientes_afectados"] = len(
                    mes_data["clientes_afectados"])

            # Estadísticas generales
            total_intereses = sum(
                getattr(nd, 'total_general', Decimal("0")) for nd in notas_interes)
            clientes_morosos = len(
                set(getattr(nd, 'cliente_id', 0) for nd in notas_interes))

            return {
                "periodo_analisis": {
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": fecha_fin.isoformat(),
                    "meses_analizados": meses_atras
                },
                "intereses_por_mes": {
                    mes: {
                        "cantidad_notas": datos["cantidad_notas"],
                        "monto_intereses": float(datos["monto_intereses"]),
                        "clientes_afectados": datos["clientes_afectados"]
                    }
                    for mes, datos in intereses_por_mes.items()
                },
                "totales_periodo": {
                    "total_notas_interes": len(notas_interes),
                    "total_intereses_cobrados": float(total_intereses),
                    "clientes_morosos_unicos": clientes_morosos
                },
                "indicadores": {
                    "interes_promedio_mensual": float(total_intereses / meses_atras) if meses_atras > 0 else 0.0,
                    "notas_promedio_mensual": len(notas_interes) / meses_atras if meses_atras > 0 else 0.0,
                    "interes_promedio_por_nota": float(total_intereses / len(notas_interes)) if notas_interes else 0.0
                }
            }

        except Exception as e:
            handle_repository_error(
                e, "get_interest_analysis", "NotaDebitoElectronica")
            raise handle_database_exception(e, "get_interest_analysis")

    # ===============================================
    # HELPERS INTERNOS
    # ===============================================

    def _apply_nde_defaults(self, data: Dict[str, Any], documento_original: Documento) -> None:
        """
        Aplica configuraciones por defecto específicas de notas de débito.

        Args:
            data: Diccionario de datos a modificar in-place
            documento_original: Documento original para heredar datos
        """
        # Aplicar defaults base desde auxiliares
        apply_default_config(data, "6")  # Tipo 6 = Nota Débito

        # Aplicar defaults específicos adicionales
        for key, default_value in NDE_DEFAULTS.items():
            if key not in data or data[key] is None:
                data[key] = default_value

        # Heredar datos del documento original
        if documento_original:
            # Heredar cliente si no se especifica
            if "cliente_id" not in data:
                data["cliente_id"] = getattr(
                    documento_original, 'cliente_id', None)

            # Heredar moneda si no se especifica
            if "moneda" not in data:
                data["moneda"] = getattr(documento_original, 'moneda', 'PYG')

            # Heredar empresa si no se especifica
            if "empresa_id" not in data:
                data["empresa_id"] = getattr(
                    documento_original, 'empresa_id', None)

        # Configuraciones especiales para NDE
        if "fecha_emision" not in data:
            data["fecha_emision"] = date.today()

        if "estado" not in data:
            data["estado"] = EstadoDocumentoSifenEnum.BORRADOR.value

    def _validate_nota_debito_item(self, item: Dict[str, Any], index: int) -> None:
        """
        Valida un item individual de la nota de débito.

        Args:
            item: Datos del item a validar
            index: Índice del item en la lista

        Raises:
            SifenValidationError: Si el item no es válido
        """
        # Campos requeridos en items
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

        # Validar precio unitario positivo (característico de NDE)
        try:
            precio = Decimal(str(item["precio_unitario"]))
            if precio <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise SifenValidationError(
                f"Precio unitario debe ser un número positivo en item {index + 1} (NDE aumenta valor)",
                field=f"items[{index}].precio_unitario",
                value=item.get("precio_unitario")
            )

        # Validar tipo de IVA si está presente
        if "tipo_iva" in item:
            tipo_iva = item["tipo_iva"]
            if tipo_iva not in ["exento", "exonerado", "5", "10"]:
                raise SifenValidationError(
                    f"Tipo de IVA inválido en item {index + 1}. Válidos: exento, exonerado, 5, 10",
                    field=f"items[{index}].tipo_iva",
                    value=tipo_iva
                )

    def _validate_parties_consistency(self, nota_data: Dict[str, Any], documento_original: Documento) -> None:
        """
        Valida consistencia de emisor y receptor entre NDE y documento original.

        Args:
            nota_data: Datos de la nota de débito
            documento_original: Documento original
        """
        # Validar que emisor coincida
        if "empresa_id" in nota_data:
            empresa_nota = nota_data["empresa_id"]
            empresa_original = getattr(documento_original, 'empresa_id', None)

            if empresa_original and empresa_nota != empresa_original:
                raise SifenValidationError(
                    "Emisor de la nota de débito debe coincidir con el documento original",
                    field="empresa_id",
                    details={
                        "empresa_nota": empresa_nota,
                        "empresa_original": empresa_original
                    }
                )

        # Validar que receptor coincida
        if "cliente_id" in nota_data:
            cliente_nota = nota_data["cliente_id"]
            cliente_original = getattr(documento_original, 'cliente_id', None)

            if cliente_original and cliente_nota != cliente_original:
                raise SifenValidationError(
                    "Receptor de la nota de débito debe coincidir con el documento original",
                    field="cliente_id",
                    details={
                        "cliente_nota": cliente_nota,
                        "cliente_original": cliente_original
                    }
                )

    def _validate_reasonable_charges(self, nota_data: Dict[str, Any],
                                     documento_original: Documento,
                                     totales_calculados: Dict[str, Decimal]) -> None:
        """
        Valida que los cargos sean razonables respecto al documento original.

        Args:
            nota_data: Datos de la nota de débito
            documento_original: Documento original
            totales_calculados: Totales calculados desde items
        """
        total_original = getattr(
            documento_original, 'total_general', Decimal("0"))
        total_cargo = totales_calculados["total_general"]

        # Advertir si el cargo es muy alto (más del 50% del original)
        if total_cargo > total_original * Decimal("0.5"):
            logger.warning(
                "NDE_CARGO_ALTO_DETECTADO",
                extra={
                    "modulo": "document_types_t6",
                    "total_cargo": float(total_cargo),
                    "total_original": float(total_original),
                    "porcentaje": float((total_cargo / total_original) * 100),
                    "documento_original_cdc": getattr(documento_original, 'cdc', '')[:20] + "..."
                }
            )

    def _calculate_totals_from_items(self, items: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """
        Calcula totales desde una lista de items de NDE.

        Args:
            items: Lista de items con precios e IVA

        Returns:
            Dict[str, Decimal]: Totales calculados
        """
        totales = {
            "subtotal_exento": Decimal("0"),
            "subtotal_exonerado": Decimal("0"),
            "subtotal_5": Decimal("0"),
            "subtotal_10": Decimal("0"),
            "total_iva": Decimal("0"),
            "total_operacion": Decimal("0"),
            "total_general": Decimal("0")
        }

        for item in items:
            cantidad = Decimal(str(item.get("cantidad", 0)))
            precio_unitario = Decimal(str(item.get("precio_unitario", 0)))
            tipo_iva = item.get("tipo_iva", "10")

            subtotal_item = cantidad * precio_unitario

            if tipo_iva == "exento":
                totales["subtotal_exento"] += subtotal_item
            elif tipo_iva == "exonerado":
                totales["subtotal_exonerado"] += subtotal_item
            elif tipo_iva == "5":
                totales["subtotal_5"] += subtotal_item
                totales["total_iva"] += subtotal_item * Decimal("0.05")
            else:  # "10" por defecto
                totales["subtotal_10"] += subtotal_item
                totales["total_iva"] += subtotal_item * Decimal("0.10")

        totales["total_operacion"] = (
            totales["subtotal_exento"] +
            totales["subtotal_exonerado"] +
            totales["subtotal_5"] +
            totales["subtotal_10"]
        )

        totales["total_general"] = totales["total_operacion"] + \
            totales["total_iva"]

        return totales

    def _calculate_interest_amounts(self, total_original: Decimal, parametros: Dict[str, Any]) -> Dict[str, Decimal]:
        """
        Calcula montos de intereses por mora.

        Args:
            total_original: Monto del documento original
            parametros: Parámetros de cálculo (dias_mora, tasa_diaria, etc.)

        Returns:
            Dict[str, Decimal]: Montos de intereses calculados
        """
        dias_mora = parametros.get("dias_mora", 0)
        tasa_diaria = parametros.get(
            "tasa_diaria", Decimal("0.001"))  # 0.1% por defecto
        aplicar_iva = parametros.get("aplicar_iva", True)

        # Calcular interés simple
        monto_interes = total_original * tasa_diaria * dias_mora

        # Calcular IVA si aplica
        iva_interes = monto_interes * \
            Decimal("0.10") if aplicar_iva else Decimal("0")

        total_con_iva = monto_interes + iva_interes

        return {
            "subtotal": monto_interes,
            "iva": iva_interes,
            "total": total_con_iva,
            "tasa_aplicada": tasa_diaria,
            "dias_calculados": dias_mora
        }

    def _calculate_banking_fees(self, total_original: Decimal, parametros: Dict[str, Any]) -> Dict[str, Decimal]:
        """
        Calcula gastos bancarios.

        Args:
            total_original: Monto del documento original
            parametros: Parámetros de cálculo

        Returns:
            Dict[str, Decimal]: Montos de gastos bancarios
        """
        monto_fijo = parametros.get("monto_fijo", Decimal(
            "25000"))  # Gs. 25.000 por defecto
        porcentaje = parametros.get("porcentaje", Decimal("0"))
        aplicar_iva = parametros.get("aplicar_iva", True)

        # Calcular gasto bancario
        gasto_variable = total_original * \
            porcentaje if porcentaje > 0 else Decimal("0")
        gasto_total = monto_fijo + gasto_variable

        # Calcular IVA si aplica
        iva_gasto = gasto_total * \
            Decimal("0.10") if aplicar_iva else Decimal("0")

        total_con_iva = gasto_total + iva_gasto

        return {
            "subtotal": gasto_total,
            "iva": iva_gasto,
            "total": total_con_iva,
            "gasto_fijo": monto_fijo,
            "gasto_variable": gasto_variable
        }

    def _calculate_collection_fees(self, total_original: Decimal, parametros: Dict[str, Any]) -> Dict[str, Decimal]:
        """
        Calcula gastos de cobranza.

        Args:
            total_original: Monto del documento original
            parametros: Parámetros de cálculo

        Returns:
            Dict[str, Decimal]: Montos de gastos de cobranza
        """
        porcentaje_cobranza = parametros.get(
            "porcentaje_cobranza", Decimal("0.05"))  # 5% por defecto
        monto_minimo = parametros.get(
            "monto_minimo", Decimal("50000"))  # Gs. 50.000 mínimo
        aplicar_iva = parametros.get("aplicar_iva", True)

        # Calcular gasto de cobranza
        gasto_calculado = total_original * porcentaje_cobranza
        gasto_cobranza = max(gasto_calculado, monto_minimo)

        # Calcular IVA si aplica
        iva_gasto = gasto_cobranza * \
            Decimal("0.10") if aplicar_iva else Decimal("0")

        total_con_iva = gasto_cobranza + iva_gasto

        return {
            "subtotal": gasto_cobranza,
            "iva": iva_gasto,
            "total": total_con_iva,
            "porcentaje_aplicado": porcentaje_cobranza,
            "monto_minimo": monto_minimo
        }

    def _calculate_price_adjustment(self, total_original: Decimal, parametros: Dict[str, Any]) -> Dict[str, Decimal]:
        """
        Calcula ajustes de precio.

        Args:
            total_original: Monto del documento original
            parametros: Parámetros de cálculo

        Returns:
            Dict[str, Decimal]: Montos de ajuste de precio
        """
        porcentaje_ajuste = parametros.get(
            "porcentaje_ajuste", Decimal("0.10"))  # 10% por defecto
        aplicar_iva = parametros.get("aplicar_iva", True)

        # Calcular ajuste
        ajuste_precio = total_original * porcentaje_ajuste

        # Calcular IVA si aplica
        iva_ajuste = ajuste_precio * \
            Decimal("0.10") if aplicar_iva else Decimal("0")

        total_con_iva = ajuste_precio + iva_ajuste

        return {
            "subtotal": ajuste_precio,
            "iva": iva_ajuste,
            "total": total_con_iva,
            "porcentaje_ajuste": porcentaje_ajuste
        }

    def _calculate_penalty_amounts(self, total_original: Decimal, parametros: Dict[str, Any]) -> Dict[str, Decimal]:
        """
        Calcula montos de multas contractuales.

        Args:
            total_original: Monto del documento original
            parametros: Parámetros de cálculo

        Returns:
            Dict[str, Decimal]: Montos de multa calculados
        """
        porcentaje_multa = parametros.get(
            "porcentaje_multa", Decimal("0.15"))  # 15% por defecto
        monto_maximo = parametros.get("monto_maximo", None)
        aplicar_iva = parametros.get("aplicar_iva", True)

        # Calcular multa
        multa_calculada = total_original * porcentaje_multa

        # Aplicar tope máximo si está definido
        if monto_maximo:
            multa_calculada = min(multa_calculada, monto_maximo)

        # Calcular IVA si aplica
        iva_multa = multa_calculada * \
            Decimal("0.10") if aplicar_iva else Decimal("0")

        total_con_iva = multa_calculada + iva_multa

        return {
            "subtotal": multa_calculada,
            "iva": iva_multa,
            "total": total_con_iva,
            "porcentaje_multa": porcentaje_multa,
            "monto_maximo": monto_maximo or Decimal("0")
        }

    def _calculate_generic_charges(self, total_original: Decimal, parametros: Dict[str, Any]) -> Dict[str, Decimal]:
        """
        Calcula cargos genéricos.

        Args:
            total_original: Monto del documento original
            parametros: Parámetros de cálculo

        Returns:
            Dict[str, Decimal]: Montos de cargo genérico
        """
        monto_cargo = parametros.get("monto_cargo", Decimal(
            "100000"))  # Gs. 100.000 por defecto
        aplicar_iva = parametros.get("aplicar_iva", True)

        # Calcular IVA si aplica
        iva_cargo = monto_cargo * \
            Decimal("0.10") if aplicar_iva else Decimal("0")

        total_con_iva = monto_cargo + iva_cargo

        return {
            "subtotal": monto_cargo,
            "iva": iva_cargo,
            "total": total_con_iva
        }

    def _analyze_charges_by_type(self, notas_debito: List[NotaDebitoElectronica]) -> Dict[str, Any]:
        """
        Analiza cargos por tipo basado en motivos de débito.

        Args:
            notas_debito: Lista de notas de débito a analizar

        Returns:
            Dict[str, Any]: Análisis por tipo de cargo
        """
        analisis = {}

        for tipo_cargo, descripcion in TIPOS_CARGO_ADICIONAL.items():
            analisis[tipo_cargo] = {
                "descripcion": descripcion,
                "cantidad_notas": 0,
                "monto_total": Decimal("0"),
                "monto_promedio": Decimal("0")
            }

        # Clasificar notas por tipo de cargo
        for nota in notas_debito:
            motivo = getattr(nota, 'motivo_debito', '').lower()
            monto = getattr(nota, 'total_general', Decimal("0"))

            # Clasificar por palabras clave en el motivo
            tipo_identificado = "otro"  # Default

            if "inter" in motivo or "mora" in motivo:
                tipo_identificado = "interes"
            elif "banc" in motivo:
                tipo_identificado = "gasto_bancario"
            elif "cobr" in motivo:
                tipo_identificado = "gasto_cobranza"
            elif "ajust" in motivo or "precio" in motivo:
                tipo_identificado = "ajuste_precio"
            elif "mult" in motivo or "penal" in motivo:
                tipo_identificado = "multa"
            elif "servic" in motivo:
                tipo_identificado = "servicio_adicional"
            elif "recuper" in motivo or "cost" in motivo:
                tipo_identificado = "recupero_costo"

            if tipo_identificado in analisis:
                analisis[tipo_identificado]["cantidad_notas"] += 1
                analisis[tipo_identificado]["monto_total"] += monto

        # Calcular promedios
        for tipo_data in analisis.values():
            if tipo_data["cantidad_notas"] > 0:
                tipo_data["monto_promedio"] = tipo_data["monto_total"] / \
                    tipo_data["cantidad_notas"]

            # Convertir a float para JSON
            tipo_data["monto_total"] = float(tipo_data["monto_total"])
            tipo_data["monto_promedio"] = float(tipo_data["monto_promedio"])

        return analisis

    def _calculate_charge_distribution(self, notas_debito: List[NotaDebitoElectronica]) -> Dict[str, int]:
        """
        Calcula distribución de notas de débito por rangos de montos.

        Args:
            notas_debito: Lista de notas de débito a analizar

        Returns:
            Dict[str, int]: Distribución por rangos
        """
        # Definir rangos de montos para cargos (en guaraníes)
        rangos = {
            "0-50K": (0, 50000),
            "50K-100K": (50000, 100000),
            "100K-250K": (100000, 250000),
            "250K-500K": (250000, 500000),
            "500K-1M": (500000, 1000000),
            "1M+": (1000000, float('inf'))
        }

        distribucion = {rango: 0 for rango in rangos.keys()}

        for nota in notas_debito:
            monto = float(getattr(nota, 'total_general', 0))

            for rango, (minimo, maximo) in rangos.items():
                if minimo <= monto < maximo:
                    distribucion[rango] += 1
                    break

        return distribucion

    def _get_empty_nde_stats(self) -> Dict[str, Any]:
        """
        Retorna estructura de estadísticas vacía para NDE.

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
                "total_notas_debito": 0,
                "monto_total_cargos": 0.0,
                "monto_total_iva_cargos": 0.0,
                "promedio_por_nota": 0.0
            },
            "analisis_cargos": {
                tipo: {
                    "descripcion": desc,
                    "cantidad_notas": 0,
                    "monto_total": 0.0,
                    "monto_promedio": 0.0
                }
                for tipo, desc in TIPOS_CARGO_ADICIONAL.items()
            },
            "clientes": {
                "clientes_con_cargos": 0,
                "promedio_notas_por_cliente": 0.0
            },
            "estados": {},
            "distribucion_montos": {},
            "datos_por_periodo": {},
            "metadatos": {
                "generado_en": datetime.now().isoformat(),
                "tiempo_procesamiento": 0.0
            }
        }

    def _format_nde_response(self, nota_debito: NotaDebitoElectronica, include_details: bool = False) -> Dict[str, Any]:
        """
        Formatea respuesta con datos específicos de notas de débito.

        Args:
            nota_debito: Instancia de nota de débito a formatear
            include_details: Incluir detalles adicionales

        Returns:
            Dict[str, Any]: Nota de débito formateada para respuesta
        """
        response = {
            "id": getattr(nota_debito, 'id', None),
            "cdc": getattr(nota_debito, 'cdc', ''),
            "numero_completo": getattr(nota_debito, 'numero_completo', ''),
            "fecha_emision": getattr(nota_debito, 'fecha_emision', date.today()).isoformat(),
            "cliente_id": getattr(nota_debito, 'cliente_id', None),
            "total_general": float(getattr(nota_debito, 'total_general', 0)),
            "total_iva": float(getattr(nota_debito, 'total_iva', 0)),
            "moneda": getattr(nota_debito, 'moneda', 'PYG'),
            "estado": getattr(nota_debito, 'estado', 'unknown'),
            "tipo_documento": "Nota de Débito Electrónica",
            "motivo_debito": getattr(nota_debito, 'motivo_debito', ''),
            "documento_original_cdc": getattr(nota_debito, 'documento_original_cdc', '')
        }

        if include_details:
            response.update({
                "subtotal_exento": float(getattr(nota_debito, 'subtotal_exento', 0)),
                "subtotal_exonerado": float(getattr(nota_debito, 'subtotal_exonerado', 0)),
                "subtotal_gravado_5": float(getattr(nota_debito, 'subtotal_gravado_5', 0)),
                "subtotal_gravado_10": float(getattr(nota_debito, 'subtotal_gravado_10', 0)),
                "total_operacion": float(getattr(nota_debito, 'total_operacion', 0)),
                "tipo_operacion": getattr(nota_debito, 'tipo_operacion', '1'),
                "condicion_operacion": getattr(nota_debito, 'condicion_operacion', '1'),
                "observaciones": getattr(nota_debito, 'observaciones', ''),
                "numero_protocolo": getattr(nota_debito, 'numero_protocolo', ''),
                "fecha_creacion": getattr(nota_debito, 'created_at', datetime.now()).isoformat(),
                "fecha_actualizacion": getattr(nota_debito, 'updated_at', datetime.now()).isoformat()
            })

        return response

    # ===============================================
    # MÉTODOS DE CONVENIENCIA ADICIONALES
    # ===============================================

    def get_pending_charges_by_client(self, cliente_id: int, empresa_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene cargos pendientes por cliente.

        Args:
            cliente_id: ID del cliente
            empresa_id: ID de la empresa

        Returns:
            List[Dict[str, Any]]: Lista de cargos pendientes

        Example:
            ```python
            cargos_pendientes = repo.get_pending_charges_by_client(cliente_id=456, empresa_id=1)
            ```
        """
        try:
            notas_pendientes = self.get_notas_debito_by_criteria(
                empresa_id=empresa_id,
                cliente_id=cliente_id,
                estados=["borrador", "validado",
                         "generado", "firmado", "enviado"]
            )

            return [self._format_nde_response(nota, include_details=True)
                    for nota in notas_pendientes]

        except Exception as e:
            handle_repository_error(
                e, "get_pending_charges_by_client", "NotaDebitoElectronica")
            raise handle_database_exception(e, "get_pending_charges_by_client")

    def calculate_late_payment_interest(self, documento_original_cdc: str,
                                        fecha_vencimiento: date,
                                        tasa_interes_anual: Decimal = Decimal("36.0")) -> Dict[str, Any]:
        """
        Calcula intereses por pago tardío automáticamente.

        Args:
            documento_original_cdc: CDC del documento original
            fecha_vencimiento: Fecha de vencimiento del pago
            tasa_interes_anual: Tasa de interés anual (default: 36%)

        Returns:
            Dict[str, Any]: Cálculo de intereses detallado

        Example:
            ```python
            calculo = repo.calculate_late_payment_interest(
                "12345678901234567890123456789012345678901234",
                date(2025, 1, 15),
                Decimal("36.0")
            )
            ```
        """
        try:
            # Obtener documento original
            documento_original = validate_and_get_original_document(
                self.db, self.model, documento_original_cdc)

            # Calcular días de mora
            fecha_actual = date.today()
            dias_mora = (fecha_actual - fecha_vencimiento).days

            if dias_mora <= 0:
                return {
                    "dias_mora": 0,
                    "intereses_calculados": 0.0,
                    "mensaje": "El documento no está vencido"
                }

            # Calcular tasa diaria
            tasa_diaria = tasa_interes_anual / Decimal("365")

            # Obtener monto original
            total_original = getattr(
                documento_original, 'total_general', Decimal("0"))

            # Calcular intereses
            parametros = {
                "dias_mora": dias_mora,
                "tasa_diaria": tasa_diaria / 100,  # Convertir porcentaje a decimal
                "aplicar_iva": True
            }

            montos_calculados = self._calculate_interest_amounts(
                total_original, parametros)

            return {
                "documento_original": {
                    "cdc": documento_original_cdc,
                    "monto_original": float(total_original),
                    "fecha_vencimiento": fecha_vencimiento.isoformat()
                },
                "calculo_interes": {
                    "dias_mora": dias_mora,
                    "tasa_anual": float(tasa_interes_anual),
                    "tasa_diaria": float(tasa_diaria),
                    "monto_interes": float(montos_calculados["subtotal"]),
                    "iva_interes": float(montos_calculados["iva"]),
                    "total_con_iva": float(montos_calculados["total"])
                },
                "fecha_calculo": fecha_actual.isoformat()
            }

        except Exception as e:
            handle_repository_error(
                e, "calculate_late_payment_interest", "NotaDebitoElectronica")
            raise handle_database_exception(
                e, "calculate_late_payment_interest")

    def validate_charge_legality(self, tipo_cargo: str, monto_cargo: Decimal,
                                 documento_original: Documento) -> Dict[str, Any]:
        """
        Valida legalidad y razonabilidad de un cargo.

        Args:
            tipo_cargo: Tipo de cargo a validar
            monto_cargo: Monto del cargo
            documento_original: Documento original

        Returns:
            Dict[str, Any]: Resultado de validación de legalidad

        Example:
            ```python
            validacion = repo.validate_charge_legality(
                "interes", Decimal("200000"), documento_original
            )
            ```
        """
        try:
            validacion = {
                "es_legal": True,
                "es_razonable": True,
                "advertencias": [],
                "recomendaciones": []
            }

            total_original = getattr(
                documento_original, 'total_general', Decimal("0"))
            porcentaje_cargo = (monto_cargo / total_original *
                                100) if total_original > 0 else Decimal("0")

            # Validaciones por tipo de cargo
            if tipo_cargo == "interes":
                # Tasa máxima legal en Paraguay: 36% anual
                if porcentaje_cargo > 36:
                    validacion["advertencias"].append(
                        f"Tasa de interés ({porcentaje_cargo:.2f}%) excede límite legal recomendado (36% anual)"
                    )
                    validacion["es_razonable"] = False

            elif tipo_cargo == "gasto_cobranza":
                # Gastos de cobranza razonables: hasta 10%
                if porcentaje_cargo > 10:
                    validacion["advertencias"].append(
                        f"Gastos de cobranza ({porcentaje_cargo:.2f}%) parecen excesivos (>10%)"
                    )
                    validacion["es_razonable"] = False

            elif tipo_cargo == "multa":
                # Multas contractuales: hasta 20%
                if porcentaje_cargo > 20:
                    validacion["advertencias"].append(
                        f"Multa ({porcentaje_cargo:.2f}%) excede límite recomendado (20%)"
                    )
                    validacion["es_razonable"] = False

            # Recomendaciones generales
            if monto_cargo > total_original:
                validacion["recomendaciones"].append(
                    "Considerar dividir cargos muy altos en múltiples notas"
                )

            if not validacion["advertencias"]:
                validacion["recomendaciones"].append(
                    "Cargo dentro de parámetros legales y razonables"
                )

            return validacion

        except Exception as e:
            handle_repository_error(
                e, "validate_charge_legality", "NotaDebitoElectronica")
            raise handle_database_exception(e, "validate_charge_legality")


# ===============================================
# EXPORTS
# ===============================================

__all__ = [
    "DocumentTypesMixinT6",
    "NDE_DEFAULTS",
    "MOTIVOS_DEBITO_VALIDOS",
    "TIPOS_CARGO_ADICIONAL"
]
