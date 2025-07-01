"""
Generador principal de XML para documentos SIFEN v150
Arquitectura escalable para múltiples tipos de documentos
"""
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from typing import Union, Dict, Any, Optional
from .models import (
    FacturaSimple, NotaCreditoElectronica, NotaDebitoElectronica,
    AutofacturaElectronica, NotaRemisionElectronica,
    get_document_type_code, get_document_description
)
from .config import TEMPLATES_DIR, SIFEN_VERSION


class XMLGenerator:
    """
    Generador XML escalable para todos los tipos de documentos SIFEN v150

    Arquitectura:
    - Template base común (base_document.xml)
    - Templates específicos por tipo de documento
    - Partials reutilizables para grupos comunes
    - Context builders especializados por tipo
    """

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True
        )

        # Mapeo de tipos de documento a templates específicos
        self.document_templates = {
            "1": "factura_electronica.xml",           # Factura Electrónica
            "4": "autofactura_electronica.xml",       # Autofactura Electrónica
            "5": "nota_credito_electronica.xml",      # Nota de Crédito
            "6": "nota_debito_electronica.xml",       # Nota de Débito
            "7": "nota_remision_electronica.xml"      # Nota de Remisión
        }

        # Templates fallback (para compatibilidad)
        self.fallback_templates = {
            "1": "factura_simple.xml"  # Template actual existente
        }

    def generate_document_xml(self,
                              document: Union[FacturaSimple, NotaCreditoElectronica,
                                              NotaDebitoElectronica, AutofacturaElectronica,
                                              NotaRemisionElectronica],
                              cdc: Optional[str] = None,
                              use_base_template: bool = True) -> str:
        """
        Genera XML para cualquier tipo de documento SIFEN

        Args:
            document: Instancia del modelo de documento
            cdc: Código de Control (44 dígitos). Si no se proporciona, se genera automáticamente
            use_base_template: Si usar base_document.xml + partials (True) o template monolítico (False)

        Returns:
            str: XML generado

        Raises:
            ValueError: Si el tipo de documento no es soportado
            RuntimeError: Si hay errores en la generación
        """
        try:
            # 1. Determinar tipo de documento
            document_type = get_document_type_code(document)

            # 2. Generar CDC si no se proporciona
            if not cdc:
                cdc = self._generate_cdc(document, document_type)

            # 3. Validar CDC
            self._validate_cdc(cdc)

            # 4. Construir contexto específico del documento
            context = self._build_document_context(
                document, document_type, cdc)

            # 5. Generar XML según arquitectura elegida
            if use_base_template:
                return self._generate_with_base_template(context, document_type)
            else:
                return self._generate_with_specific_template(context, document_type)

        except Exception as e:
            raise RuntimeError(
                f"Error generando XML para documento tipo {document_type}: {e}")

    def generate_simple_invoice_xml(self, factura: FacturaSimple) -> str:
        """
        Método de compatibilidad para generar facturas simples

        Args:
            factura: Datos de la factura validados por Pydantic

        Returns:
            str: XML generado
        """
        return self.generate_document_xml(factura, use_base_template=False)

    def _build_document_context(self, document: Any, document_type: str, cdc: str) -> Dict[str, Any]:
        """
        Construye el contexto específico para el tipo de documento

        Args:
            document: Instancia del modelo
            document_type: Código del tipo de documento
            cdc: Código de Control

        Returns:
            Dict con contexto para el template
        """
        # Contexto base común para todos los documentos
        fecha_emision = document.fecha_emision.strftime("%Y-%m-%dT%H:%M:%S")

        base_context = {
            # === DATOS BÁSICOS DEL DOCUMENTO ===
            "cdc": cdc,
            "version": "150",
            "fecha_firma": fecha_emision,
            "tipo_documento": document_type,
            "descripcion_tipo": get_document_description(document_type),

            # === DATOS COMUNES ===
            "numero_documento": document.numero_documento,
            "fecha_emision": fecha_emision,
            "csc": document.csc,

            # === PARTICIPANTES ===
            "emisor": document.emisor.model_dump(),
            "items": [item.model_dump() for item in document.items],

            # === TOTALES ===
            "total_exenta": str(document.total_exenta),
            "total_gravada": str(document.total_gravada),
            "total_iva": str(document.total_iva),
            "total_general": str(document.total_general),
        }

        # Agregar receptor si existe (no todas las AFE lo tienen)
        if hasattr(document, 'receptor') and document.receptor:
            base_context["receptor"] = document.receptor.model_dump()

        # Contexto específico por tipo de documento
        if document_type == "1":  # Factura Electrónica
            return self._build_factura_context(document, base_context)
        elif document_type == "4":  # Autofactura Electrónica
            return self._build_autofactura_context(document, base_context)
        elif document_type == "5":  # Nota de Crédito
            return self._build_nota_credito_context(document, base_context)
        elif document_type == "6":  # Nota de Débito
            return self._build_nota_debito_context(document, base_context)
        elif document_type == "7":  # Nota de Remisión
            return self._build_nota_remision_context(document, base_context)
        else:
            raise ValueError(
                f"Tipo de documento no soportado: {document_type}")

    def _build_factura_context(self, factura: FacturaSimple, base_context: Dict) -> Dict[str, Any]:
        """Construye contexto específico para Factura Electrónica"""
        context = base_context.copy()

        # Valores por defecto para campos no presentes en FacturaSimple
        context.update({
            "moneda": "PYG",
            "tipo_cambio": "1.00",
            "condicion_venta": "1",  # Contado
            "condicion_operacion": "1",  # Venta de mercaderías
            "modalidad_transporte": "1",  # Propio
            "categoria_emisor": "1",  # Contribuyente
            "ambiente": "2",  # Producción (1=Test, 2=Producción)
            "tipo_emision": "1",  # Normal
        })

        return context

    def _build_autofactura_context(self, autofactura: AutofacturaElectronica, base_context: Dict) -> Dict[str, Any]:
        """Construye contexto específico para Autofactura Electrónica"""
        context = base_context.copy()

        # Datos específicos de AFE
        context.update({
            "datos_afe": autofactura.datos_afe.model_dump(),
            "vendedor_extranjero": autofactura.vendedor_extranjero.model_dump(),
            "motivo_afe": autofactura.motivo_afe,
            "condicion_operacion": autofactura.condicion_operacion,
            "moneda": "USD",  # Común en importaciones
            "tipo_cambio": "7500.00",  # Ejemplo
        })

        return context

    def _build_nota_credito_context(self, nota_credito: NotaCreditoElectronica, base_context: Dict) -> Dict[str, Any]:
        """Construye contexto específico para Nota de Crédito"""
        context = base_context.copy()

        # Datos específicos de NCE
        context.update({
            "documento_asociado": nota_credito.documento_asociado.model_dump(),
            "motivo_credito": nota_credito.motivo_credito,
            "tipo_credito": nota_credito.tipo_credito,
            "condicion_operacion": nota_credito.condicion_operacion,
            # Los totales en NCE pueden ser negativos
            "total_credito": str(nota_credito.total_general),
        })

        return context

    def _build_nota_debito_context(self, nota_debito: NotaDebitoElectronica, base_context: Dict) -> Dict[str, Any]:
        """Construye contexto específico para Nota de Débito"""
        context = base_context.copy()

        # Datos específicos de NDE
        context.update({
            "documento_asociado": nota_debito.documento_asociado.model_dump(),
            "motivo_debito": nota_debito.motivo_debito,
            "tipo_debito": nota_debito.tipo_debito,
            "condicion_operacion": nota_debito.condicion_operacion,
            "total_debito": str(nota_debito.total_general),
        })

        return context

    def _build_nota_remision_context(self, nota_remision: NotaRemisionElectronica, base_context: Dict) -> Dict[str, Any]:
        """Construye contexto específico para Nota de Remisión"""
        context = base_context.copy()

        # Datos específicos de NRE
        context.update({
            "datos_transporte": nota_remision.datos_transporte.model_dump(),
            "datos_vehiculo": nota_remision.datos_vehiculo.model_dump() if nota_remision.datos_vehiculo else None,
            "motivo_traslado": nota_remision.motivo_traslado,
            "tipo_traslado": nota_remision.tipo_traslado,
            "condicion_operacion": nota_remision.condicion_operacion,
            "observaciones_traslado": nota_remision.observaciones_traslado,
            # NRE tiene totales en 0
            "total_gravada": "0",
            "total_iva": "0",
            "total_general": "0",
        })

        return context

    def _generate_with_base_template(self, context: Dict[str, Any], document_type: str) -> str:
        """
        Genera XML usando base_document.xml + template específico

        Args:
            context: Contexto del documento
            document_type: Tipo de documento

        Returns:
            str: XML generado
        """
        try:
            # Obtener template específico del tipo de documento
            template_name = self.document_templates.get(document_type)

            if not template_name:
                raise ValueError(
                    f"No hay template para tipo de documento {document_type}")

            # Intentar cargar template específico
            try:
                template = self.env.get_template(template_name)
            except Exception:
                # Fallback a template simple si el específico no existe
                fallback_name = self.fallback_templates.get(document_type)
                if fallback_name:
                    template = self.env.get_template(fallback_name)
                else:
                    raise RuntimeError(
                        f"No se encontró template para tipo {document_type}")

            # Renderizar
            xml = template.render(**context)
            return xml

        except Exception as e:
            raise RuntimeError(f"Error generando con base template: {e}")

    def _generate_with_specific_template(self, context: Dict[str, Any], document_type: str) -> str:
        """
        Genera XML usando template específico monolítico (compatibilidad)

        Args:
            context: Contexto del documento
            document_type: Tipo de documento

        Returns:
            str: XML generado
        """
        # Para compatibilidad con factura_simple.xml actual
        if document_type == "1":
            template = self.env.get_template('factura_simple.xml')
            return template.render(**context)
        else:
            # Para otros tipos, usar la arquitectura base
            return self._generate_with_base_template(context, document_type)

    def _generate_cdc(self, document: Any, document_type: str) -> str:
        """
        Genera un CDC básico para testing

        Args:
            document: Instancia del documento
            document_type: Tipo de documento

        Returns:
            str: CDC de 44 caracteres
        """
        # CDC básico para testing: TipDoc + RUC + Timestamp + Secuencial
        ruc_emisor = document.emisor.ruc.zfill(8)
        timestamp = document.fecha_emision.strftime("%Y%m%d%H%M%S")
        secuencial = "0000001"

        # Construir CDC: 01 + RUC(8) + DV(1) + 001(Est) + 001(Punto) + 0000001(Sec) + Timestamp(14) + 01(Tipo)
        cdc = f"{document_type.zfill(2)}{ruc_emisor}9001001{secuencial}{timestamp}{document_type.zfill(2)}"

        # Asegurar 44 caracteres
        return cdc.ljust(44, '0')[:44]

    def _validate_cdc(self, cdc: str) -> None:
        """
        Valida que el CDC tenga el formato correcto

        Args:
            cdc: Código de Control a validar

        Raises:
            ValueError: Si el CDC no es válido
        """
        if not cdc or len(cdc) != 44:
            raise ValueError(
                f"CDC debe tener exactamente 44 caracteres. Actual: {len(cdc) if cdc else 0}")

        if not cdc.isdigit():
            raise ValueError("CDC debe contener solo dígitos")

    def list_available_templates(self) -> Dict[str, list]:
        """
        Lista todos los templates disponibles organizados por categoría

        Returns:
            Dict con templates disponibles
        """
        try:
            all_templates = self.env.list_templates()

            categorized = {
                "base": [],
                "specific": [],
                "partials": [],
                "fallback": [],
                "other": []
            }

            for template in all_templates:
                if template == "base_document.xml":
                    categorized["base"].append(template)
                elif template.startswith("_"):
                    categorized["partials"].append(template)
                elif template in self.document_templates.values():
                    categorized["specific"].append(template)
                elif template in self.fallback_templates.values():
                    categorized["fallback"].append(template)
                else:
                    categorized["other"].append(template)

            return categorized

        except Exception:
            return {"error": "No se pudieron listar templates"}  # type: ignore

    def get_document_info(self, document: Any) -> Dict[str, Any]:
        """
        Obtiene información completa sobre un documento

        Args:
            document: Instancia del modelo

        Returns:
            Dict con información del documento
        """
        try:
            document_type = get_document_type_code(document)
            description = get_document_description(document_type)

            return {
                "model_type": type(document).__name__,
                "document_type_code": document_type,
                "document_type_description": description,
                "template_available": document_type in self.document_templates,
                "fallback_available": document_type in self.fallback_templates,
                "suggested_template": self.document_templates.get(document_type, "No disponible"),
                "estimated_cdc": self._generate_cdc(document, document_type),
                "has_required_fields": self._check_required_fields(document),
            }

        except Exception as e:
            return {"error": str(e)}

    def _check_required_fields(self, document: Any) -> Dict[str, bool]:
        """
        Verifica si el documento tiene todos los campos requeridos

        Args:
            document: Instancia del modelo

        Returns:
            Dict con estado de campos requeridos
        """
        required_fields = [
            'numero_documento', 'fecha_emision', 'emisor',
            'items', 'total_general', 'csc'
        ]

        field_status = {}
        for field in required_fields:
            field_status[field] = hasattr(document, field) and getattr(
                document, field) is not None

        return field_status
