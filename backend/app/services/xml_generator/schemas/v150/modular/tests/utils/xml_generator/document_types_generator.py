"""
Document Types Generator - SIFEN v150

Genera XMLs específicos para cada tipo de documento del alcance SIFEN v150.
Hereda de BaseXMLGenerator y proporciona templates realistas para testing.

TIPOS DE DOCUMENTOS SOPORTADOS:
01 - Factura Electrónica (FE) ✅ COMPLETO
04 - Autofactura Electrónica (AFE) 🔄 PENDIENTE
05 - Nota de Crédito (NCE) 🔄 PENDIENTE  
06 - Nota de Débito (NDE) 🔄 PENDIENTE
07 - Nota de Remisión (NRE) 🔄 PENDIENTE

Autor: Generado para testing schemas modulares XSD v150
Ubicación: schemas/v150/tests/utils/xml_generator/document_types_generator.py
"""

from typing import Dict, Union
from datetime import datetime
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class BaseXMLGenerator(ABC):
    """Clase base abstracta para generadores XML"""

    def __init__(self):
        self.namespace = "http://ekuatia.set.gov.py/sifen/xsd"
        self.version = "150"

    @abstractmethod
    def generate(self, doc_type: str, **kwargs) -> str:
        """Método abstracto para generar XML"""
        pass


class SampleData:
    """Datos de ejemplo paraguayos para testing"""

    # Empresas ejemplo con datos realistas paraguayos
    EMPRESAS_EJEMPLO = {
        "emisor_consultora": {
            "ruc": "80012345", "dv": "9",
            "razon_social": "Consultores Asociados S.A.",
            "direccion": "Av. Mariscal López 1234",
            "ciudad": "Asunción",
            "telefono": "021-555-0123",
            "email": "facturacion@consultores.com.py"
        },
        "emisor_ferreteria": {
            "ruc": "80023456", "dv": "8",
            "razon_social": "Ferretería Central del Paraguay",
            "direccion": "Av. España 890",
            "ciudad": "Asunción",
            "telefono": "021-555-0456",
            "email": "ventas@ferreteria.com.py"
        },
        "receptor_empresa": {
            "ruc": "80087654", "dv": "3",
            "razon_social": "Construcciones del Sur S.R.L.",
            "direccion": "Av. Eusebio Ayala 2456",
            "ciudad": "Asunción",
            "telefono": "021-555-0789",
            "email": "compras@construcciones.com.py"
        }
    }

    # Productos típicos del mercado paraguayo
    PRODUCTOS_TIPICOS = [
        {
            "codigo": "SER001",
            "descripcion": "Consultoría contable mensual",
            "precio": 800000,
            "iva_tipo": 10,
            "unidad": "47"  # Unidad de servicio
        },
        {
            "codigo": "ALM001",
            "descripcion": "Yerba mate Kurupí x 500g",
            "precio": 25000,
            "iva_tipo": 10,
            "unidad": "01"  # Unidad
        },
        {
            "codigo": "FAR001",
            "descripcion": "Paracetamol 500mg x 20 comp",
            "precio": 8500,
            "iva_tipo": 0,  # Exento
            "unidad": "01"  # Unidad
        },
        {
            "codigo": "FER001",
            "descripcion": "Martillo carpintero mango madera",
            "precio": 45000,
            "iva_tipo": 10,
            "unidad": "01"  # Unidad
        },
        {
            "codigo": "SER002",
            "descripcion": "Reparación de equipo informático",
            "precio": 150000,
            "iva_tipo": 10,
            "unidad": "47"  # Unidad de servicio
        }
    ]


class DocumentTypesGenerator(BaseXMLGenerator):
    """
    Generador de XMLs para todos los tipos de documentos SIFEN v150

    Proporciona métodos específicos para cada tipo de documento
    con datos realistas del mercado paraguayo para testing.
    """

    def __init__(self, sample_data: Optional[SampleData] = None):
        super().__init__()
        self.sample_data = sample_data or SampleData()

    def generate(self, doc_type: str, **kwargs) -> str:
        """
        Router principal para generar XML según tipo de documento

        Args:
            doc_type: Código del tipo de documento ('01', '04', '05', '06', '07')
            **kwargs: Parámetros específicos del documento

        Returns:
            str: XML completo del documento

        Raises:
            ValueError: Si el tipo de documento no está soportado
        """
        generators = {
            '01': self.generate_factura_xml,
            '04': self.generate_autofactura_xml,
            '05': self.generate_nota_credito_xml,
            '06': self.generate_nota_debito_xml,
            '07': self.generate_nota_remision_xml
        }

        if doc_type not in generators:
            raise ValueError(f"Tipo de documento '{doc_type}' no soportado. "
                             f"Tipos válidos: {list(generators.keys())}")

        return generators[doc_type](**kwargs)

    def generate_factura_xml(self, valid: bool = True, **kwargs) -> str:
        """
        Genera XML de Factura Electrónica (FE) - Tipo 01

        Caso principal del proyecto con estructura completa:
        - Múltiples items con diferentes tipos de IVA
        - Monedas PYG y USD soportadas
        - Cálculos exactos de totales
        - Datos realistas paraguayos

        Args:
            valid: Si True, genera XML válido. Si False, introduce errores para testing
            **kwargs: Parámetros opcionales (emisor, receptor, items, etc.)

        Returns:
            str: XML completo de factura electrónica
        """
        # Obtener datos base
        emisor = kwargs.get(
            'emisor', self.sample_data.EMPRESAS_EJEMPLO['emisor_consultora'])
        receptor = kwargs.get(
            'receptor', self.sample_data.EMPRESAS_EJEMPLO['receptor_empresa'])
        items = kwargs.get('items', self._get_default_factura_items())
        fecha_emision = kwargs.get(
            'fecha_emision', datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

        # Generar CDC (44 dígitos)
        cdc = self._generate_cdc('01', emisor['ruc'], fecha_emision)

        # Calcular totales
        totales = self._calculate_totals(items)

        # Introducir errores si valid=False
        if not valid:
            error_type = kwargs.get('error_type', 'missing_ruc')
            emisor, receptor, items, totales = self._introduce_factura_errors(
                error_type, emisor, receptor, items, totales
            )

        # Construir XML
        xml_parts = [
            self._build_xml_header(),
            self._build_document_root(cdc),
            self._build_document_header('01', fecha_emision),
            self._build_timbrado_section(),
            self._build_datos_generales_section(fecha_emision),
            self._build_emisor_section(emisor),
            self._build_receptor_section(receptor),
            self._build_items_section(items, include_amounts=True),
            self._build_totals_section(totales),
            self._build_document_footer()
        ]

        return '\n'.join(xml_parts)

    # =============================================
    # MÉTODOS PRIVADOS - CONSTRUCCIÓN XML
    # =============================================

    def _build_xml_header(self) -> str:
        """Construye header XML con declaración y namespace"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="{self.namespace}" version="{self.version}">'''

    def _build_document_root(self, cdc: str) -> str:
        """Construye elemento raíz DE con CDC"""
        return f'''    <DE Id="{cdc}">
        <dVerFor>{self.version}</dVerFor>
        <dCodSeg>{cdc[-9:]}</dCodSeg>'''

    def _build_document_header(self, doc_type: str, fecha_emision: str) -> str:
        """Construye sección de datos generales de operación"""
        tipo_desc = {
            '01': 'Factura Electrónica',
            '04': 'Autofactura Electrónica',
            '05': 'Nota de Crédito Electrónica',
            '06': 'Nota de Débito Electrónica',
            '07': 'Nota de Remisión Electrónica'
        }

        return f'''        
        <!-- Datos generales -->
        <gDatGralOpe>
            <dFeEmiDE>{fecha_emision}</dFeEmiDE>
        </gDatGralOpe>
        
        <!-- Operación -->
        <gOpDE>
            <iTipDE>{doc_type}</iTipDE>
            <dDesTipDE>{tipo_desc[doc_type]}</dDesTipDE>
            <dNumTimbDE>12345678</dNumTimbDE>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>0000001</dNumDoc>
            <dFeEmiDE>{fecha_emision}</dFeEmiDE>
        </gOpDE>'''

    def _build_timbrado_section(self) -> str:
        """Construye sección de timbrado"""
        return '''        
        <!-- Timbrado -->
        <gTimb>
            <iTiDE>1</iTiDE>
            <dNumTim>12345678</dNumTim>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>0000001</dNumDoc>
            <dSerieNum>A</dSerieNum>
            <dFeIniT>2024-01-01</dFeIniT>
        </gTimb>'''

    def _build_datos_generales_section(self, fecha_emision: str) -> str:
        """Construye sección de datos generales detallada"""
        return f'''        
        <!-- Datos generales operación -->
        <gDatGralOpe>
            <dFeEmiDE>{fecha_emision}</dFeEmiDE>
            <iTipTra>1</iTipTra>
            <iTImp>1</iTImp>
            <cMoneOpe>PYG</cMoneOpe>
            <dCondTiCam>1</dCondTiCam>
            <dTiCam>1</dTiCam>
            <iCondAnt>1</iCondAnt>
        </gDatGralOpe>'''

    def _build_emisor_section(self, emisor: Dict[str, str]) -> str:
        """Construye sección del emisor"""
        return f'''        
        <!-- Emisor -->
        <gEmis>
            <dRUCEmi>{emisor['ruc']}</dRUCEmi>
            <dDVEmi>{emisor['dv']}</dDVEmi>
            <dNomEmi>{emisor['razon_social']}</dNomEmi>
            <dDirEmi>{emisor['direccion']}</dDirEmi>
            <dNumCasEmi>0</dNumCasEmi>
            <dTelEmi>{emisor['telefono']}</dTelEmi>
            <dEmailE>{emisor['email']}</dEmailE>
        </gEmis>'''

    def _build_receptor_section(self, receptor: Dict[str, str]) -> str:
        """Construye sección del receptor"""
        return f'''        
        <!-- Receptor -->
        <gDatRec>
            <iNatRec>1</iNatRec>
            <iTiOpe>1</iTiOpe>
            <dNomRec>{receptor['razon_social']}</dNomRec>
            <dRUCRec>{receptor['ruc']}</dRUCRec>
            <dDVRec>{receptor['dv']}</dDVRec>
            <dDirRec>{receptor['direccion']}</dDirRec>
            <dNumCasRec>0</dNumCasRec>
            <dTelRec>{receptor['telefono']}</dTelRec>
            <dEmailRec>{receptor['email']}</dEmailRec>
        </gDatRec>'''

    def _build_items_section(self, items: List[Dict], include_amounts: bool = True) -> str:
        """Construye sección de items"""
        items_xml = []

        for i, item in enumerate(items, 1):
            # Calcular montos del item
            cantidad = item.get('cantidad', 1.0)
            precio_unit = item.get('precio', 0) if include_amounts else 0
            total_bruto = cantidad * precio_unit

            # Configurar IVA
            iva_config = self._get_iva_config(item.get('iva_tipo', 10))
            base_gravada = total_bruto if iva_config['gravado'] else 0
            monto_iva = base_gravada * \
                (iva_config['tasa'] / 100) if include_amounts else 0

            item_xml = f'''        
        <!-- Item {i} -->
        <gCamItem>
            <iCorrelItem>{i}</iCorrelItem>
            <dDesProSer>{item['descripcion']}</dDesProSer>
            <dCodProSer>{item['codigo']}</dCodProSer>
            <dCantProSer>{cantidad:.2f}</dCantProSer>
            <dPUniProSer>{precio_unit:.2f}</dPUniProSer>
            <dTotBruOpeItem>{total_bruto:.2f}</dTotBruOpeItem>
            
            <!-- IVA por item -->
            <gCamIVA>
                <iAfecIVA>{iva_config['codigo']}</iAfecIVA>
                <dDesAfecIVA>{iva_config['descripcion']}</dDesAfecIVA>
                <dPropIVA>{iva_config['tasa']:.2f}</dPropIVA>
                <dTasaIVA>{iva_config['tasa']:.2f}</dTasaIVA>
                <dBasGravIVA>{base_gravada:.2f}</dBasGravIVA>
                <dLiqIVAItem>{monto_iva:.2f}</dLiqIVAItem>
            </gCamIVA>
        </gCamItem>'''

            items_xml.append(item_xml)

        return '\n'.join(items_xml)

    def _build_totals_section(self, totales: Dict[str, float]) -> str:
        """Construye sección de totales"""
        return f'''        
        <!-- Totales -->
        <gTotSub>
            <dSubExe>{totales['total_exento']:.2f}</dSubExe>
            <dSubExo>0.00</dSubExo>
            <dSub5>{totales['total_iva5']:.2f}</dSub5>
            <dSub10>{totales['total_gravado10']:.2f}</dSub10>
            <dTotOpe>{totales['total_operacion']:.2f}</dTotOpe>
            <dTotGralOpe>{totales['total_general']:.2f}</dTotGralOpe>
            <dIVA5>{totales['iva_5']:.2f}</dIVA5>
            <dIVA10>{totales['iva_10']:.2f}</dIVA10>
            <dTotIVA>{totales['total_iva']:.2f}</dTotIVA>
            <dBaseGrav5>{totales['base_gravada5']:.2f}</dBaseGrav5>
            <dBaseGrav10>{totales['base_gravada10']:.2f}</dBaseGrav10>
            <dTBasGraIVA>{totales['total_base_gravada']:.2f}</dTBasGraIVA>
        </gTotSub>'''

    def _build_document_footer(self) -> str:
        """Construye cierre del documento"""
        return '''    </DE>
</rDE>'''

    # =============================================
    # MÉTODOS PRIVADOS - DATOS Y CÁLCULOS
    # =============================================

    def _get_default_factura_items(self) -> List[Dict]:
        """Obtiene items por defecto para una factura típica"""
        return [
            {
                'codigo': 'SER001',
                'descripcion': 'Consultoría contable mensual',
                'cantidad': 1.0,
                'precio': 800000,
                'iva_tipo': 10,
                'unidad': '47'
            },
            {
                'codigo': 'ALM001',
                'descripcion': 'Yerba mate Kurupí x 500g',
                'cantidad': 2.0,
                'precio': 25000,
                'iva_tipo': 10,
                'unidad': '01'
            },
            {
                'codigo': 'FAR001',
                'descripcion': 'Paracetamol 500mg x 20 comp',
                'cantidad': 1.0,
                'precio': 8500,
                'iva_tipo': 0,  # Exento
                'unidad': '01'
            }
        ]

    def _calculate_totals(self, items: List[Dict]) -> Dict[str, float]:
        """
        Calcula totales según reglas SIFEN v150

        Reglas:
        - Total Gravado IVA 10%: Base imponible 10%
        - Total Gravado IVA 5%: Base imponible 5%  
        - Total Exento: Sin IVA
        - Total IVA: Suma de todos los IVAs
        - Total General: Base + IVA
        """
        totales = {
            'total_exento': 0.0,
            'total_iva5': 0.0,
            'total_gravado10': 0.0,
            'base_gravada5': 0.0,
            'base_gravada10': 0.0,
            'iva_5': 0.0,
            'iva_10': 0.0,
            'total_iva': 0.0,
            'total_operacion': 0.0,
            'total_base_gravada': 0.0,
            'total_general': 0.0
        }

        for item in items:
            cantidad = item.get('cantidad', 1.0)
            precio = item.get('precio', 0)
            total_item = cantidad * precio
            iva_tipo = item.get('iva_tipo', 10)

            if iva_tipo == 0:  # Exento
                totales['total_exento'] += total_item
            elif iva_tipo == 5:  # IVA 5%
                totales['total_iva5'] += total_item
                totales['base_gravada5'] += total_item
                totales['iva_5'] += total_item * 0.05
            elif iva_tipo == 10:  # IVA 10%
                totales['total_gravado10'] += total_item
                totales['base_gravada10'] += total_item
                totales['iva_10'] += total_item * 0.10

        # Cálculos finales
        totales['total_iva'] = totales['iva_5'] + totales['iva_10']
        totales['total_base_gravada'] = totales['base_gravada5'] + \
            totales['base_gravada10']
        totales['total_operacion'] = totales['total_exento'] + \
            totales['total_iva5'] + totales['total_gravado10']
        totales['total_general'] = totales['total_operacion'] + \
            totales['total_iva']

        return totales

    def _get_iva_config(self, iva_tipo: int) -> Dict[str, Any]:
        """Obtiene configuración de IVA según tipo"""
        configs = {
            0: {'codigo': '1', 'descripcion': 'Exenta', 'tasa': 0.0, 'gravado': False},
            5: {'codigo': '2', 'descripcion': 'Gravada 5%', 'tasa': 5.0, 'gravado': True},
            10: {'codigo': '3', 'descripcion': 'Gravada 10%', 'tasa': 10.0, 'gravado': True}
        }
        return configs.get(iva_tipo, configs[10])

    def _generate_cdc(self, doc_type: str, ruc: str, fecha: str) -> str:
        """
        Genera CDC (Código de Control) de 44 dígitos

        Formato: TTRRRRRRRRDDVEEEPPPNNNNNNNAAAAMMDDHHMMSSSSSSSSD
        - TT: Tipo documento (01)
        - RRRRRRRR: RUC emisor (8 dígitos)
        - DD: DV RUC
        - V: Dígito verificador
        - EEE: Establecimiento (001)
        - PPP: Punto expedición (001)
        - NNNNNNN: Número documento (7 dígitos)
        - AAAA: Año (2024)
        - MM: Mes
        - DD: Día
        - HH: Hora
        - MM: Minuto
        - SSSSSSS: Número secuencial
        - D: Dígito verificador final
        """
        import random
        fecha_dt = datetime.strptime(fecha[:10], "%Y-%m-%d")

        cdc_parts = [
            doc_type,                                    # Tipo (2)
            ruc.ljust(8, '0')[:8],                      # RUC (8)
            '1',                                         # DV (1)
            '0',                                         # Verificador (1)
            '001',                                       # Establecimiento (3)
            '001',                                       # Punto exp (3)
            str(random.randint(1, 9999999)).zfill(7),   # Num doc (7)
            fecha_dt.strftime("%Y%m%d%H%M"),            # Fecha/hora (12)
            str(random.randint(1000000, 9999999)),      # Secuencial (7)
        ]

        cdc_base = ''.join(cdc_parts)
        # Agregar dígito verificador simple
        cdc_final = cdc_base + str(sum(int(d) for d in cdc_base) % 10)

        return cdc_final

    def _introduce_factura_errors(self, error_type: str, emisor: Dict, receptor: Dict,
                                  items: List[Dict], totales: Dict) -> tuple:
        """Introduce errores específicos para testing negativo"""
        if error_type == 'missing_ruc':
            emisor = emisor.copy()
            emisor['ruc'] = ''
        elif error_type == 'invalid_amounts':
            for item in items:
                item['precio'] = -abs(item['precio'])  # Precios negativos
        elif error_type == 'missing_items':
            items = []
        elif error_type == 'wrong_totals':
            totales['total_general'] = 999999.99  # Total incorrecto

        return emisor, receptor, items, totales

    # =============================================
    # ---- Autofactura Electrónica (AFE) - Tipo 04 ----
    # =============================================

    def generate_autofactura_xml(self, valid: bool = True, **kwargs) -> str:
        """🔄 PENDIENTE: Genera AFE donde receptor = emisor"""
        raise NotImplementedError("Autofactura pendiente - próxima iteración")

    def generate_nota_credito_xml(self, valid: bool = True, ref_doc: Optional[str] = None, **kwargs) -> str:
        """🔄 PENDIENTE: Genera NCE con montos negativos"""
        raise NotImplementedError(
            "Nota de crédito pendiente - próxima iteración")

    def generate_nota_debito_xml(self, valid: bool = True, ref_doc: Optional[str] = None, **kwargs) -> str:
        """🔄 PENDIENTE: Genera NDE con cargos adicionales"""
        raise NotImplementedError(
            "Nota de débito pendiente - próxima iteración")

    def generate_nota_remision_xml(self, valid: bool = True, **kwargs) -> str:
        """🔄 PENDIENTE: Genera NRE sin valores monetarios"""
        raise NotImplementedError(
            "Nota de remisión pendiente - próxima iteración")


def generate_autofactura_xml(self, valid: bool = True, **kwargs) -> str:
    """
    Genera XML de Autofactura Electrónica (AFE) - Tipo 04

    Caso específico para importaciones donde receptor = emisor.
    Incluye sección AFE obligatoria con datos del vendedor.

    CASOS DE USO TÍPICOS:
    - Importación de mercaderías (vendedor extranjero)
    - Compra a no contribuyentes nacionales
    - Operaciones donde el comprador debe emitir la factura

    Args:
        valid: Si True, genera XML válido. Si False, introduce errores para testing
        **kwargs: Parámetros opcionales
            - emisor: Datos del emisor (será también el receptor)
            - vendedor: Datos del vendedor original
            - items: Items de la autofactura
            - moneda: 'PYG' o 'USD' (por defecto 'USD' para importaciones)
            - tipo_cambio: Tasa de cambio si moneda es USD

    Returns:
        str: XML completo de autofactura electrónica
    """
    # Obtener datos base
    emisor = kwargs.get(
        'emisor', self.sample_data.EMPRESAS_EJEMPLO['emisor_ferreteria'])
    receptor = emisor.copy()  # En AFE: receptor = emisor
    vendedor = kwargs.get('vendedor', self._get_default_afe_vendedor())
    items = kwargs.get('items', self._get_default_afe_items())
    fecha_emision = kwargs.get(
        'fecha_emision', datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    moneda = kwargs.get('moneda', 'USD')  # USD típico para importaciones
    # Tasa USD a PYG aproximada
    tipo_cambio = kwargs.get('tipo_cambio', 7300.0)

    # Generar CDC para tipo 04
    cdc = self._generate_cdc('04', emisor['ruc'], fecha_emision)

    # Calcular totales (convertir USD a PYG si es necesario)
    totales = self._calculate_afe_totals(items, moneda, tipo_cambio)

    # Introducir errores si valid=False
    if not valid:
        error_type = kwargs.get('error_type', 'receptor_different_ruc')
        emisor, receptor, vendedor, items, totales = self._introduce_afe_errors(
            error_type, emisor, receptor, vendedor, items, totales
        )

    # Construir XML
    xml_parts = [
        self._build_xml_header(),
        self._build_document_root(cdc),
        self._build_document_header('04', fecha_emision),
        self._build_timbrado_section(),
        self._build_afe_datos_generales_section(
            fecha_emision, moneda, tipo_cambio),
        self._build_emisor_section(emisor),
        self._build_receptor_section(receptor),
        self._build_afe_specific_section(vendedor),  # Sección específica AFE
        self._build_items_section(items, include_amounts=True),
        self._build_totals_section(totales),
        self._build_document_footer()
    ]

    return '\n'.join(xml_parts)


def _get_default_afe_vendedor(self) -> Dict[str, str]:
    """
    Obtiene datos por defecto del vendedor para AFE

    Casos típicos:
    - Proveedor extranjero (importación)
    - No contribuyente nacional
    """
    return {
        'naturaleza': '2',  # 2 = Extranjero
        'tipo_documento': '2',  # 2 = Pasaporte
        'numero_documento': 'P1234567890',
        'nombre': 'International Supplies Inc.',
        'direccion': 'Miami Trade Center 123',
        'numero_casa': '123',
        'departamento': '1',  # Asunción (donde se realizó la transacción)
        'departamento_desc': 'CAPITAL',
        'distrito': '1',
        'distrito_desc': 'ASUNCION',
        'ciudad': '1',
        'ciudad_desc': 'ASUNCION',
        'telefono': '+1-305-555-0123',
        'email': 'sales@internationalsupplies.com'
    }


def _get_default_afe_items(self) -> List[Dict]:
    """Obtiene items por defecto para una autofactura típica (importación)"""
    return [
        {
            'codigo': 'IMP001',
            'descripcion': 'Equipos electrónicos importados - Notebook HP',
            'cantidad': 5.0,
            'precio': 800.00,  # En USD
            'iva_tipo': 10,
            'unidad': '01',
            'codigo_arancelario': '8471301000'  # Código NCM para importación
        },
        {
            'codigo': 'IMP002',
            'descripcion': 'Accesorios informáticos - Mouse inalámbrico',
            'cantidad': 10.0,
            'precio': 25.00,  # En USD
            'iva_tipo': 10,
            'unidad': '01',
            'codigo_arancelario': '8471606000'
        },
        {
            'codigo': 'SER001',
            'descripcion': 'Flete internacional y seguro',
            'cantidad': 1.0,
            'precio': 150.00,  # En USD
            'iva_tipo': 0,  # Exento
            'unidad': '47',
            'codigo_arancelario': ''  # No aplica para servicios
        }
    ]


def _build_afe_datos_generales_section(self, fecha_emision: str, moneda: str, tipo_cambio: float) -> str:
    """Construye sección de datos generales específica para AFE"""
    return f'''        
    <!-- Datos generales operación AFE -->
    <gDatGralOpe>
        <dFeEmiDE>{fecha_emision}</dFeEmiDE>
        <iTipTra>1</iTipTra>
        <iTImp>1</iTImp>
        <cMoneOpe>{moneda}</cMoneOpe>
        <dCondTiCam>{"1" if moneda == "PYG" else "2"}</dCondTiCam>
        <dTiCam>{tipo_cambio:.2f}</dTiCam>
        <iCondAnt>1</iCondAnt>
        <dDCondAnt>Contado</dDCondAnt>
    </gDatGralOpe>'''


def _build_afe_specific_section(self, vendedor: Dict[str, str]) -> str:
    """
    Construye sección específica AFE (gCamAE - E300-E399)

    Obligatoria para tipo de documento 04.
    Contiene información del vendedor original.
    """
    naturaleza_desc = {
        '1': 'No contribuyente',
        '2': 'Extranjero'
    }

    tipo_doc_desc = {
        '1': 'Cédula paraguaya',
        '2': 'Pasaporte',
        '3': 'Cédula extranjera',
        '4': 'Carnet de residencia'
    }

    return f'''        
    <!-- Campos específicos AFE (E300-E399) -->
    <gCamAE>
        <!-- Naturaleza del vendedor -->
        <iNatVen>{vendedor['naturaleza']}</iNatVen>
        <dDesNatVen>{naturaleza_desc.get(vendedor['naturaleza'], 'Extranjero')}</dDesNatVen>
        
        <!-- Identificación del vendedor -->
        <iTipIDVen>{vendedor['tipo_documento']}</iTipIDVen>
        <dDTipIDVen>{tipo_doc_desc.get(vendedor['tipo_documento'], 'Pasaporte')}</dDTipIDVen>
        <dNumIDVen>{vendedor['numero_documento']}</dNumIDVen>
        <dNomVen>{vendedor['nombre']}</dNomVen>
        
        <!-- Dirección del vendedor -->
        <dDirVen>{vendedor['direccion']}</dDirVen>
        <dNumCasVen>{vendedor['numero_casa']}</dNumCasVen>
        
        <!-- Ubicación geográfica del vendedor -->
        <cDepVen>{vendedor['departamento']}</cDepVen>
        <dDesDepVen>{vendedor['departamento_desc']}</dDesDepVen>
        <cDisVen>{vendedor['distrito']}</cDisVen>
        <dDesDisVen>{vendedor['distrito_desc']}</dDesDisVen>
        <cCiuVen>{vendedor['ciudad']}</cCiuVen>
        <dDesCiuVen>{vendedor['ciudad_desc']}</dDesCiuVen>
        
        <!-- Ubicación donde se realiza la transacción -->
        <cDepTrans>{vendedor['departamento']}</cDepTrans>
        <dDesDepTrans>{vendedor['departamento_desc']}</dDesDepTrans>
        <cDisTrans>{vendedor['distrito']}</cDisTrans>
        <dDesDisTrans>{vendedor['distrito_desc']}</dDesDisTrans>
        <cCiuTrans>{vendedor['ciudad']}</cCiuTrans>
        <dDesCiuTrans>{vendedor['ciudad_desc']}</dDesCiuTrans>
    </gCamAE>'''


def _calculate_afe_totals(self, items: List[Dict], moneda: str, tipo_cambio: float) -> Dict[str, float]:
    """
    Calcula totales para AFE considerando conversión de moneda

    Para importaciones típicamente en USD, se convierte a PYG.
    Los totales siempre deben expresarse en PYG en el XML.
    """
    totales = {
        'total_exento': 0.0,
        'total_iva5': 0.0,
        'total_gravado10': 0.0,
        'base_gravada5': 0.0,
        'base_gravada10': 0.0,
        'iva_5': 0.0,
        'iva_10': 0.0,
        'total_iva': 0.0,
        'total_operacion': 0.0,
        'total_base_gravada': 0.0,
        'total_general': 0.0
    }

    for item in items:
        cantidad = item.get('cantidad', 1.0)
        precio_usd = item.get('precio', 0)
        iva_tipo = item.get('iva_tipo', 10)

        # Convertir a PYG si el precio está en USD
        precio_pyg = precio_usd * tipo_cambio if moneda == 'USD' else precio_usd
        total_item_pyg = cantidad * precio_pyg

        if iva_tipo == 0:  # Exento
            totales['total_exento'] += total_item_pyg
        elif iva_tipo == 5:  # IVA 5%
            totales['total_iva5'] += total_item_pyg
            totales['base_gravada5'] += total_item_pyg
            totales['iva_5'] += total_item_pyg * 0.05
        elif iva_tipo == 10:  # IVA 10%
            totales['total_gravado10'] += total_item_pyg
            totales['base_gravada10'] += total_item_pyg
            totales['iva_10'] += total_item_pyg * 0.10

    # Cálculos finales
    totales['total_iva'] = totales['iva_5'] + totales['iva_10']
    totales['total_base_gravada'] = totales['base_gravada5'] + \
        totales['base_gravada10']
    totales['total_operacion'] = totales['total_exento'] + \
        totales['total_iva5'] + totales['total_gravado10']
    totales['total_general'] = totales['total_operacion'] + \
        totales['total_iva']

    return totales


def _introduce_afe_errors(self, error_type: str, emisor: Dict, receptor: Dict,
                          vendedor: Dict, items: List[Dict], totales: Dict) -> tuple:
    """Introduce errores específicos de AFE para testing negativo"""

    if error_type == 'receptor_different_ruc':
        # Error: receptor debe tener mismo RUC que emisor
        receptor = receptor.copy()
        receptor['ruc'] = '80099999'  # RUC diferente al emisor

    elif error_type == 'missing_afe_section':
        # Error: falta sección AFE obligatoria
        vendedor = {}  # Sección AFE vacía

    elif error_type == 'invalid_vendedor_contrib':
        # Error: vendedor no puede ser contribuyente
        vendedor = vendedor.copy()
        vendedor['naturaleza'] = '1'  # No contribuyente
        vendedor['numero_documento'] = '80012345-9'  # Formato RUC (inválido)

    elif error_type == 'invalid_currency_conversion':
        # Error: conversión de moneda incorrecta
        for item in items:
            item['precio'] = -abs(item['precio'])  # Precios negativos

    elif error_type == 'missing_geographic_data':
        # Error: datos geográficos incompletos
        vendedor = vendedor.copy()
        vendedor['departamento'] = ''
        vendedor['ciudad'] = ''

    return emisor, receptor, vendedor, items, totales

# =============================================
# DATOS DE EJEMPLO ESPECÍFICOS PARA AFE
# =============================================


def get_afe_sample_data():
    """Datos de ejemplo específicos para testing de AFE"""
    return {
        'importador_electronica': {
            'ruc': '80087654', 'dv': '3',
            'razon_social': 'Importadora Electrónica del Paraguay S.A.',
            'direccion': 'Av. Aviadores del Chaco 2456',
            'ciudad': 'Asunción',
            'telefono': '021-555-0987',
            'email': 'importacion@electronica.com.py'
        },
        'proveedor_miami': {
            'naturaleza': '2',  # Extranjero
            'tipo_documento': '2',  # Pasaporte
            'numero_documento': 'US123456789',
            'nombre': 'Miami Electronics Wholesale LLC',
            'direccion': '8400 NW 36th St, Suite 450',
            'numero_casa': '450',
            'departamento': '1',  # Asunción (lugar de transacción)
            'ciudad': '1',
            'telefono': '+1-305-555-8888',
            'email': 'sales@miamielectronics.com'
        },
        'items_importacion_tipica': [
            {
                'codigo': 'LAP001',
                'descripcion': 'Laptop Dell Inspiron 15 3000',
                'cantidad': 10.0,
                'precio': 650.00,  # USD
                'iva_tipo': 10,
                'codigo_arancelario': '8471301000'
            },
            {
                'codigo': 'MON001',
                'descripcion': 'Monitor LED 24 pulgadas',
                'cantidad': 15.0,
                'precio': 180.00,  # USD
                'iva_tipo': 10,
                'codigo_arancelario': '8528721000'
            },
            {
                'codigo': 'FLE001',
                'descripcion': 'Flete marítimo y seguro internacional',
                'cantidad': 1.0,
                'precio': 450.00,  # USD
                'iva_tipo': 0,  # Exento
                'codigo_arancelario': ''
            }
        ]
    }

# =============================================
# VALIDACIONES ESPECÍFICAS AFE
# =============================================


def validate_afe_specific_rules(xml_content: str) -> tuple[bool, List[str]]:
    """
    Valida reglas específicas de AFE según Manual v150

    Validaciones:
    - Receptor = Emisor (mismo RUC)
    - Sección gCamAE presente
    - Datos del vendedor completos
    - Naturaleza del vendedor válida

    Returns:
        tuple: (es_valido, lista_errores)
    """
    errors = []

    try:
        # Validar que es tipo 04
        if '<iTipDE>04</iTipDE>' not in xml_content:
            errors.append("Documento debe ser tipo 04 (AFE)")

        # Validar receptor = emisor
        import re
        ruc_emisor_match = re.search(r'<dRUCEmi>(\d+)</dRUCEmi>', xml_content)
        ruc_receptor_match = re.search(
            r'<dRUCRec>(\d+)</dRUCRec>', xml_content)

        if ruc_emisor_match and ruc_receptor_match:
            ruc_emisor = ruc_emisor_match.group(1)
            ruc_receptor = ruc_receptor_match.group(1)

            if ruc_emisor != ruc_receptor:
                errors.append(
                    f"AFE: RUC receptor ({ruc_receptor}) debe ser igual al emisor ({ruc_emisor})")
        else:
            errors.append("No se pudieron extraer RUCs para validación")

        # Validar sección AFE presente
        if '<gCamAE>' not in xml_content:
            errors.append("AFE: Sección gCamAE obligatoria faltante")

        # Validar datos del vendedor
        required_vendor_fields = ['<iNatVen>', '<dNomVen>', '<dDirVen>']
        for field in required_vendor_fields:
            if field not in xml_content:
                errors.append(
                    f"AFE: Campo obligatorio del vendedor faltante: {field}")

        # Validar naturaleza del vendedor
        nat_ven_match = re.search(r'<iNatVen>(\d)</iNatVen>', xml_content)
        if nat_ven_match:
            naturaleza = nat_ven_match.group(1)
            if naturaleza not in ['1', '2']:
                errors.append(
                    f"AFE: Naturaleza del vendedor inválida: {naturaleza}")

    except Exception as e:
        errors.append(f"Error en validación AFE: {str(e)}")

    return len(errors) == 0, errors

# =============================================
# CASOS DE TESTING ESPECÍFICOS
# =============================================


def get_afe_test_cases():
    """Casos de testing específicos para AFE"""
    return {
        'importacion_electronica_valida': {
            'descripcion': 'Importación típica de electrónicos desde Miami',
            'emisor': 'importador_electronica',
            'vendedor': 'proveedor_miami',
            'items': 'items_importacion_tipica',
            'moneda': 'USD',
            'tipo_cambio': 7350.0,
            'valid': True
        },
        'compra_no_contribuyente_valida': {
            'descripcion': 'Compra a no contribuyente nacional',
            'emisor': 'emisor_ferreteria',
            'vendedor': {
                'naturaleza': '1',  # No contribuyente
                'tipo_documento': '1',  # Cédula paraguaya
                'numero_documento': '1234567',
                'nombre': 'Juan Pérez Artesano'
            },
            'moneda': 'PYG',
            'valid': True
        },
        'error_receptor_diferente': {
            'descripcion': 'Error: receptor con RUC diferente al emisor',
            'valid': False,
            'error_type': 'receptor_different_ruc'
        },
        'error_seccion_afe_faltante': {
            'descripcion': 'Error: sección AFE obligatoria faltante',
            'valid': False,
            'error_type': 'missing_afe_section'
        }
    }

# =============================================
# ---- Nota de Crédito Electrónica (NCE) - Tipo 05 ----
# =============================================


def generate_nota_credito_xml(self, valid: bool = True, ref_doc: Optional[str] = None, **kwargs) -> str:
    """
    Genera XML de Nota de Crédito Electrónica (NCE) - Tipo 05

    Caso específico para devoluciones, descuentos y ajustes.
    Debe referenciar un documento original válido.

    CASOS DE USO TÍPICOS:
    - Devolución total o parcial de mercaderías
    - Descuentos por defectos en productos
    - Bonificaciones por volumen
    - Ajustes de precios
    - Créditos incobrables

    Args:
        valid: Si True, genera XML válido. Si False, introduce errores para testing
        ref_doc: CDC del documento original a referenciar (44 dígitos)
        **kwargs: Parámetros opcionales
            - emisor: Datos del emisor (mismo de la factura original)
            - receptor: Datos del receptor (mismo de la factura original)
            - items: Items de la nota de crédito
            - motivo: Código del motivo (1-8)
            - monto_original: Monto del documento original para validación

    Returns:
        str: XML completo de nota de crédito electrónica
    """
    # Obtener datos base
    emisor = kwargs.get(
        'emisor', self.sample_data.EMPRESAS_EJEMPLO['emisor_consultora'])
    receptor = kwargs.get(
        'receptor', self.sample_data.EMPRESAS_EJEMPLO['receptor_empresa'])
    items = kwargs.get('items', self._get_default_nce_items())
    fecha_emision = kwargs.get(
        'fecha_emision', datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    motivo = kwargs.get('motivo', '2')  # 2 = Devolución (más común)
    ref_doc_cdc = ref_doc or kwargs.get(
        'ref_doc_cdc', self._generate_sample_ref_cdc())
    monto_original = kwargs.get(
        'monto_original', 1000000.0)  # Monto factura original

    # Generar CDC para tipo 05
    cdc = self._generate_cdc('05', emisor['ruc'], fecha_emision)

    # Calcular totales de la nota de crédito
    totales = self._calculate_nce_totals(items, monto_original)

    # Introducir errores si valid=False
    if not valid:
        error_type = kwargs.get('error_type', 'exceeds_original_amount')
        emisor, receptor, items, totales, ref_doc_cdc = self._introduce_nce_errors(
            error_type, emisor, receptor, items, totales, ref_doc_cdc
        )

    # Construir XML
    xml_parts = [
        self._build_xml_header(),
        self._build_document_root(cdc),
        self._build_document_header('05', fecha_emision),
        self._build_timbrado_section(),
        self._build_datos_generales_section(fecha_emision),
        self._build_emisor_section(emisor),
        self._build_receptor_section(receptor),
        self._build_nce_specific_section(motivo),  # Sección específica NCE
        self._build_associated_document_section(
            ref_doc_cdc),  # Documento asociado
        self._build_items_section_nce(items, include_amounts=True),
        self._build_totals_section(totales),
        self._build_document_footer()
    ]

    return '\n'.join(xml_parts)


def _get_default_nce_items(self) -> List[Dict]:
    """
    Obtiene items por defecto para una nota de crédito típica

    Representa devolución parcial de productos con defectos.
    """
    return [
        {
            'codigo': 'SER001',
            'descripcion': 'Devolución: Consultoría contable - Servicios no conformes',
            'cantidad': 1.0,
            'precio_unitario': -200000,  # Precio negativo para devolución
            'iva_tipo': 10,
            'unidad': '47',
            'motivo_item': 'Servicios no prestados según contrato'
        },
        {
            'codigo': 'ALM001',
            'descripcion': 'Devolución: Yerba mate vencida x 500g',
            'cantidad': 1.0,
            'precio_unitario': -25000,  # Precio negativo
            'iva_tipo': 10,
            'unidad': '01',
            'motivo_item': 'Producto vencido al momento de entrega'
        },
        {
            'codigo': 'DESC001',
            'descripcion': 'Descuento por inconvenientes en entrega',
            'cantidad': 1.0,
            'precio_unitario': -15000,  # Descuento adicional
            'iva_tipo': 10,
            'unidad': '47',
            'motivo_item': 'Compensación por retraso en entrega'
        }
    ]


def _build_nce_specific_section(self, motivo: str) -> str:
    """
    Construye sección específica NCE (gCamNCDE - E400-E499)

    Obligatoria para tipo de documento 05.
    Define el motivo de emisión de la nota de crédito.
    """
    motivos_desc = {
        '1': 'Devolución y Ajuste de precios',
        '2': 'Devolución',
        '3': 'Descuento',
        '4': 'Bonificación',
        '5': 'Crédito incobrable',
        '6': 'Recupero de costo',
        '7': 'Recupero de gasto',
        '8': 'Ajuste de precio'
    }

    return f'''        
    <!-- Campos específicos NCE (E400-E499) -->
    <gCamNCDE>
        <!-- Motivo de emisión -->
        <iMotEmi>{motivo}</iMotEmi>
        <dDesMotEmi>{motivos_desc.get(motivo, 'Devolución')}</dDesMotEmi>
    </gCamNCDE>'''


def _build_associated_document_section(self, ref_doc_cdc: str) -> str:
    """
    Construye sección de documento asociado (gCamDEAsoc - H001-H999)

    Obligatoria para NCE. Referencia al documento original.
    """
    return f'''        
    <!-- Documento asociado (referencia) -->
    <gCamDEAsoc>
        <iTipDocAso>1</iTipDocAso>
        <dDesTipDocAso>Electrónico</dDesTipDocAso>
        <dCDCRef>{ref_doc_cdc}</dCDCRef>
        <dNTimDI></dNTimDI>
        <dEstDocAso>001</dEstDocAso>
        <dPExpDocAso>001</dPExpDocAso>
        <dNumDocAso>0000001</dNumDocAso>
        <iTipDocAsoImp></iTipDocAsoImp>
        <dDesTipDocAsoImp></dDesTipDocAsoImp>
        <dFecEmiDI></dFecEmiDI>
        <dNumComRet></dNumComRet>
        <dNumResCF></dNumResCF>
        <iTipCons></iTipCons>
        <dDesTipCons></dDesTipCons>
        <dNumCons></dNumCons>
        <dNumControl></dNumControl>
    </gCamDEAsoc>'''


def _build_items_section_nce(self, items: List[Dict], include_amounts: bool = True) -> str:
    """
    Construye sección de items específica para NCE

    Precios negativos o de ajuste, con descripción del motivo.
    """
    items_xml = []

    for i, item in enumerate(items, 1):
        # Calcular montos del item (pueden ser negativos)
        cantidad = item.get('cantidad', 1.0)
        precio_unit = item.get('precio_unitario', 0) if include_amounts else 0
        total_bruto = cantidad * precio_unit

        # Configurar IVA
        iva_config = self._get_iva_config(item.get('iva_tipo', 10))
        base_gravada = abs(total_bruto) if iva_config['gravado'] else 0
        monto_iva = base_gravada * \
            (iva_config['tasa'] / 100) if include_amounts else 0

        # Para NCE, el IVA también puede ser negativo
        if total_bruto < 0:
            monto_iva = -monto_iva
            base_gravada = -base_gravada

        item_xml = f'''        
        <!-- Item NCE {i} -->
        <gCamItem>
            <iCorrelItem>{i}</iCorrelItem>
            <dDesProSer>{item['descripcion']}</dDesProSer>
            <dCodProSer>{item['codigo']}</dCodProSer>
            <dCantProSer>{cantidad:.2f}</dCantProSer>
            <dPUniProSer>{precio_unit:.2f}</dPUniProSer>
            <dTotBruOpeItem>{total_bruto:.2f}</dTotBruOpeItem>
            
            <!-- IVA por item (puede ser negativo) -->
            <gCamIVA>
                <iAfecIVA>{iva_config['codigo']}</iAfecIVA>
                <dDesAfecIVA>{iva_config['descripcion']}</dDesAfecIVA>
                <dPropIVA>{iva_config['tasa']:.2f}</dPropIVA>
                <dTasaIVA>{iva_config['tasa']:.2f}</dTasaIVA>
                <dBasGravIVA>{base_gravada:.2f}</dBasGravIVA>
                <dLiqIVAItem>{monto_iva:.2f}</dLiqIVAItem>
            </gCamIVA>
            
            <!-- Información adicional del item NCE -->
            <gCamEsp>
                <dMotDevItem>{item.get('motivo_item', 'Devolución según solicitud cliente')}</dMotDevItem>
            </gCamEsp>
        </gCamItem>'''

        items_xml.append(item_xml)

    return '\n'.join(items_xml)


def _calculate_nce_totals(self, items: List[Dict], monto_original: float) -> Dict[str, float]:
    """
    Calcula totales para NCE considerando montos negativos

    Validaciones:
    - Los totales pueden ser negativos (devoluciones)
    - No pueden superar el monto del documento original
    - IVA se calcula sobre montos negativos
    """
    totales = {
        'total_exento': 0.0,
        'total_iva5': 0.0,
        'total_gravado10': 0.0,
        'base_gravada5': 0.0,
        'base_gravada10': 0.0,
        'iva_5': 0.0,
        'iva_10': 0.0,
        'total_iva': 0.0,
        'total_operacion': 0.0,
        'total_base_gravada': 0.0,
        'total_general': 0.0
    }

    for item in items:
        cantidad = item.get('cantidad', 1.0)
        precio = item.get('precio_unitario', 0)
        total_item = cantidad * precio
        iva_tipo = item.get('iva_tipo', 10)

        if iva_tipo == 0:  # Exento
            totales['total_exento'] += total_item
        elif iva_tipo == 5:  # IVA 5%
            totales['total_iva5'] += total_item
            totales['base_gravada5'] += total_item
            totales['iva_5'] += total_item * 0.05
        elif iva_tipo == 10:  # IVA 10%
            totales['total_gravado10'] += total_item
            totales['base_gravada10'] += total_item
            totales['iva_10'] += total_item * 0.10

    # Cálculos finales
    totales['total_iva'] = totales['iva_5'] + totales['iva_10']
    totales['total_base_gravada'] = totales['base_gravada5'] + \
        totales['base_gravada10']
    totales['total_operacion'] = totales['total_exento'] + \
        totales['total_iva5'] + totales['total_gravado10']
    totales['total_general'] = totales['total_operacion'] + \
        totales['total_iva']

    # Validar que no supere el monto original
    if abs(totales['total_general']) > monto_original:
        # En caso de error, ajustar totales (se reportará en validación)
        factor = monto_original / abs(totales['total_general'])
        for key in totales:
            totales[key] *= factor

    return totales


def _generate_sample_ref_cdc(self) -> str:
    """
    Genera CDC de ejemplo para documento de referencia

    Simula una factura electrónica previa (tipo 01).
    """
    import random
    from datetime import datetime, timedelta

    # Fecha anterior (factura original de hace unos días)
    fecha_anterior = datetime.now() - timedelta(days=random.randint(1, 30))

    cdc_parts = [
        '01',  # Tipo factura
        '80012345',  # RUC emisor (mismo que emite la NCE)
        '1',  # DV
        '0',  # Verificador
        '001',  # Establecimiento
        '001',  # Punto exp
        str(random.randint(1, 999999)).zfill(7),  # Num doc
        fecha_anterior.strftime("%Y%m%d%H%M"),  # Fecha/hora
        str(random.randint(1000000, 9999999)),  # Secuencial
    ]

    cdc_base = ''.join(cdc_parts)
    cdc_final = cdc_base + str(sum(int(d) for d in cdc_base) % 10)

    return cdc_final


def _introduce_nce_errors(self, error_type: str, emisor: Dict, receptor: Dict,
                          items: List[Dict], totales: Dict, ref_doc_cdc: str) -> tuple:
    """Introduce errores específicos de NCE para testing negativo"""

    if error_type == 'exceeds_original_amount':
        # Error: monto NCE supera monto original
        for item in items:
            item['precio_unitario'] = -1000000  # Monto excesivo

    elif error_type == 'missing_reference_document':
        # Error: falta referencia a documento original
        ref_doc_cdc = ''  # CDC vacío

    elif error_type == 'invalid_cdc_reference':
        # Error: CDC de referencia inválido
        ref_doc_cdc = '123456789'  # CDC inválido (muy corto)

    elif error_type == 'positive_amounts':
        # Error: montos positivos en nota de crédito
        for item in items:
            item['precio_unitario'] = abs(
                item['precio_unitario'])  # Cambiar a positivo

    elif error_type == 'missing_nce_section':
        # Error: falta sección NCE obligatoria
        # Se manejará en la construcción del XML
        pass

    elif error_type == 'invalid_motivo':
        # Error: motivo de emisión inválido
        # Se pasará un motivo inválido en la construcción
        pass

    elif error_type == 'different_currency':
        # Error: moneda diferente al documento original
        # Para este generador, asumimos que siempre es PYG
        pass

    return emisor, receptor, items, totales, ref_doc_cdc

# =============================================
# DATOS DE EJEMPLO ESPECÍFICOS PARA NCE
# =============================================


def get_nce_sample_data():
    """Datos de ejemplo específicos para testing de NCE"""
    return {
        'escenarios_tipicos': {
            'devolucion_productos_defectuosos': {
                'motivo': '2',  # Devolución
                'descripcion': 'Productos con defectos de fábrica',
                'items': [
                    {
                        'codigo': 'PROD001',
                        'descripcion': 'Devolución: Televisor LED 32" - Pantalla defectuosa',
                        'cantidad': 1.0,
                        'precio_unitario': -450000,
                        'iva_tipo': 10,
                        'motivo_item': 'Pantalla con pixeles muertos'
                    }
                ]
            },
            'descuento_por_retraso': {
                'motivo': '3',  # Descuento
                'descripcion': 'Descuento por entrega tardía',
                'items': [
                    {
                        'codigo': 'DESC001',
                        'descripcion': 'Descuento: Compensación por retraso entrega',
                        'cantidad': 1.0,
                        'precio_unitario': -50000,
                        'iva_tipo': 10,
                        'motivo_item': 'Entrega realizada 5 días después de lo acordado'
                    }
                ]
            },
            'bonificacion_volumen': {
                'motivo': '4',  # Bonificación
                'descripcion': 'Bonificación por volumen de compra',
                'items': [
                    {
                        'codigo': 'BON001',
                        'descripcion': 'Bonificación: Descuento por compra mayor a 100 unidades',
                        'cantidad': 1.0,
                        'precio_unitario': -120000,
                        'iva_tipo': 10,
                        'motivo_item': 'Bonificación según política comercial'
                    }
                ]
            },
            'credito_incobrable': {
                'motivo': '5',  # Crédito incobrable
                'descripcion': 'Ajuste por crédito incobrable',
                'items': [
                    {
                        'codigo': 'CRED001',
                        'descripcion': 'Ajuste: Factura incobrable por quiebra cliente',
                        'cantidad': 1.0,
                        'precio_unitario': -800000,
                        'iva_tipo': 10,
                        'motivo_item': 'Cliente declarado en quiebra'
                    }
                ]
            }
        }
    }

# =============================================
# VALIDACIONES ESPECÍFICAS NCE
# =============================================


def validate_nce_specific_rules(xml_content: str, monto_original: Optional[float] = None) -> tuple[bool, List[str]]:
    """
    Valida reglas específicas de NCE según Manual v150

    Validaciones:
    - Tipo 05 correcto
    - Sección gCamNCDE presente
    - Documento asociado presente
    - CDC de referencia válido
    - Montos no superan original
    - Motivo de emisión válido

    Args:
        xml_content: Contenido XML a validar
        monto_original: Monto del documento original para validación

    Returns:
        tuple: (es_valido, lista_errores)
    """
    errors = []

    try:
        # Validar que es tipo 05
        if '<iTipDE>05</iTipDE>' not in xml_content:
            errors.append("Documento debe ser tipo 05 (NCE)")

        # Validar sección NCE presente
        if '<gCamNCDE>' not in xml_content:
            errors.append("NCE: Sección gCamNCDE obligatoria faltante")

        # Validar documento asociado presente
        if '<gCamDEAsoc>' not in xml_content:
            errors.append("NCE: Documento asociado obligatorio faltante")

        # Validar CDC de referencia
        import re
        cdc_ref_match = re.search(r'<dCDCRef>(\d{44})</dCDCRef>', xml_content)
        if not cdc_ref_match:
            errors.append("NCE: CDC de referencia inválido o faltante")

        # Validar motivo de emisión
        motivo_match = re.search(r'<iMotEmi>(\d+)</iMotEmi>', xml_content)
        if motivo_match:
            motivo = motivo_match.group(1)
            if motivo not in ['1', '2', '3', '4', '5', '6', '7', '8']:
                errors.append(f"NCE: Motivo de emisión inválido: {motivo}")
        else:
            errors.append("NCE: Motivo de emisión faltante")

        # Validar montos si se proporciona monto original
        if monto_original:
            total_match = re.search(
                r'<dTotGralOpe>([+-]?\d+\.?\d*)</dTotGralOpe>', xml_content)
            if total_match:
                total_nce = abs(float(total_match.group(1)))
                if total_nce > monto_original:
                    errors.append(
                        f"NCE: Monto ({total_nce}) supera monto original ({monto_original})")

        # Validar que los montos sean negativos o cero para devoluciones
        precio_matches = re.findall(
            r'<dPUniProSer>([+-]?\d+\.?\d*)</dPUniProSer>', xml_content)
        for precio in precio_matches:
            if float(precio) > 0:
                errors.append(
                    f"NCE: Precio unitario positivo detectado: {precio} (debería ser negativo para devolución)")

    except Exception as e:
        errors.append(f"Error en validación NCE: {str(e)}")

    return len(errors) == 0, errors

# =============================================
# CASOS DE TESTING ESPECÍFICOS
# =============================================


def get_nce_test_cases():
    """Casos de testing específicos para NCE"""
    return {
        'devolucion_parcial_valida': {
            'descripcion': 'Devolución parcial de productos defectuosos',
            'motivo': '2',
            'ref_doc_cdc': '01800123451001001000001202412151200012345678',
            'monto_original': 1000000.0,
            'items': 'devolucion_productos_defectuosos',
            'valid': True
        },
        'descuento_comercial_valido': {
            'descripcion': 'Descuento por inconvenientes en entrega',
            'motivo': '3',
            'ref_doc_cdc': '01800123451001001000002202412151300012345679',
            'monto_original': 500000.0,
            'items': 'descuento_por_retraso',
            'valid': True
        },
        'bonificacion_volumen_valida': {
            'descripcion': 'Bonificación por compra en volumen',
            'motivo': '4',
            'ref_doc_cdc': '01800123451001001000003202412151400012345680',
            'monto_original': 2000000.0,
            'items': 'bonificacion_volumen',
            'valid': True
        },
        'error_supera_monto_original': {
            'descripcion': 'Error: NCE supera monto del documento original',
            'valid': False,
            'error_type': 'exceeds_original_amount'
        },
        'error_sin_documento_referencia': {
            'descripcion': 'Error: falta referencia a documento original',
            'valid': False,
            'error_type': 'missing_reference_document'
        },
        'error_cdc_invalido': {
            'descripcion': 'Error: CDC de referencia inválido',
            'valid': False,
            'error_type': 'invalid_cdc_reference'
        },
        'error_montos_positivos': {
            'descripcion': 'Error: montos positivos en nota de crédito',
            'valid': False,
            'error_type': 'positive_amounts'
        }
    }

# =============================================
# UTILIDADES ESPECÍFICAS NCE
# =============================================


def calculate_max_credit_amount(factura_xml: str) -> float:
    """
    Calcula el monto máximo permitido para NCE basado en factura original

    Args:
        factura_xml: XML de la factura original

    Returns:
        float: Monto máximo permitido para nota de crédito
    """
    import re

    try:
        # Extraer total general de la factura original
        total_match = re.search(
            r'<dTotGralOpe>(\d+\.?\d*)</dTotGralOpe>', factura_xml)
        if total_match:
            return float(total_match.group(1))
        else:
            return 0.0
    except:
        return 0.0


def get_motivos_nce():
    """Obtiene lista de motivos válidos para NCE"""
    return {
        '1': 'Devolución y Ajuste de precios',
        '2': 'Devolución',
        '3': 'Descuento',
        '4': 'Bonificación',
        '5': 'Crédito incobrable',
        '6': 'Recupero de costo',
        '7': 'Recupero de gasto',
        '8': 'Ajuste de precio'
    }

# =============================================
# ---- Nota de Débito Electrónica (NDE) - Tipo 06 ----
# =============================================


def generate_nota_debito_xml(self, valid: bool = True, ref_doc: Optional[str] = None, **kwargs) -> str:
    """
    Genera XML de Nota de Débito Electrónica (NDE) - Tipo 06

    Caso específico para cargos adicionales, intereses y recupero de costos.
    Debe referenciar un documento original válido.

    CASOS DE USO TÍPICOS:
    - Intereses por mora en pagos
    - Gastos bancarios por gestión de cobranza
    - Recupero de costos operativos
    - Ajustes de precio por incrementos
    - Cargos por servicios adicionales no facturados
    - Penalidades contractuales

    Args:
        valid: Si True, genera XML válido. Si False, introduce errores para testing
        ref_doc: CDC del documento original a referenciar (44 dígitos)
        **kwargs: Parámetros opcionales
            - emisor: Datos del emisor (mismo de la factura original)
            - receptor: Datos del receptor (mismo de la factura original)
            - items: Items de la nota de débito
            - motivo: Código del motivo (1-8, típicamente 6-8 para NDE)
            - monto_original: Monto del documento original para validación

    Returns:
        str: XML completo de nota de débito electrónica
    """
    # Obtener datos base
    emisor = kwargs.get(
        'emisor', self.sample_data.EMPRESAS_EJEMPLO['emisor_ferreteria'])
    receptor = kwargs.get(
        'receptor', self.sample_data.EMPRESAS_EJEMPLO['receptor_empresa'])
    items = kwargs.get('items', self._get_default_nde_items())
    fecha_emision = kwargs.get(
        'fecha_emision', datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    # 6 = Recupero de costo (típico para NDE)
    motivo = kwargs.get('motivo', '6')
    ref_doc_cdc = ref_doc or kwargs.get(
        'ref_doc_cdc', self._generate_sample_ref_cdc())
    monto_original = kwargs.get(
        'monto_original', 1000000.0)  # Monto factura original

    # Generar CDC para tipo 06
    cdc = self._generate_cdc('06', emisor['ruc'], fecha_emision)

    # Calcular totales de la nota de débito
    totales = self._calculate_nde_totals(items)

    # Introducir errores si valid=False
    if not valid:
        error_type = kwargs.get('error_type', 'negative_amounts')
        emisor, receptor, items, totales, ref_doc_cdc = self._introduce_nde_errors(
            error_type, emisor, receptor, items, totales, ref_doc_cdc
        )

    # Construir XML
    xml_parts = [
        self._build_xml_header(),
        self._build_document_root(cdc),
        self._build_document_header('06', fecha_emision),
        self._build_timbrado_section(),
        self._build_datos_generales_section(fecha_emision),
        self._build_emisor_section(emisor),
        self._build_receptor_section(receptor),
        self._build_nde_specific_section(motivo),  # Sección específica NDE
        self._build_associated_document_section(
            ref_doc_cdc),  # Documento asociado
        self._build_items_section_nde(items, include_amounts=True),
        self._build_totals_section(totales),
        self._build_document_footer()
    ]

    return '\n'.join(xml_parts)


def _get_default_nde_items(self) -> List[Dict]:
    """
    Obtiene items por defecto para una nota de débito típica

    Representa cargos adicionales por mora, gastos e intereses.
    """
    return [
        {
            'codigo': 'INT001',
            'descripcion': 'Intereses por mora - Pago fuera de término',
            'cantidad': 1.0,
            'precio_unitario': 85000,  # Precio positivo para cargo adicional
            'iva_tipo': 10,
            'unidad': '47',
            'concepto_cargo': 'Interés 2% mensual sobre saldo vencido',
            'periodo_mora': '15 días'
        },
        {
            'codigo': 'GAS001',
            'descripcion': 'Gastos bancarios - Gestión de cobranza',
            'cantidad': 1.0,
            'precio_unitario': 45000,  # Precio positivo
            'iva_tipo': 10,
            'unidad': '47',
            'concepto_cargo': 'Comisión bancaria por gestión de cobranza',
            'periodo_mora': ''
        },
        {
            'codigo': 'ADM001',
            'descripcion': 'Gastos administrativos - Procesos de cobro',
            'cantidad': 1.0,
            'precio_unitario': 35000,  # Precio positivo
            'iva_tipo': 10,
            'unidad': '47',
            'concepto_cargo': 'Gastos operativos por gestión de cobranza',
            'periodo_mora': ''
        }
    ]


def _build_nde_specific_section(self, motivo: str) -> str:
    """
    Construye sección específica NDE (gCamNCDE - E400-E499)

    Obligatoria para tipo de documento 06.
    Define el motivo de emisión de la nota de débito.

    NOTA: NDE comparte la misma sección que NCE (E400-E499)
    pero con motivos típicamente diferentes (6-8).
    """
    motivos_desc = {
        '1': 'Devolución y Ajuste de precios',  # Más común en NCE
        '2': 'Devolución',                      # Más común en NCE
        '3': 'Descuento',                       # Más común en NCE
        '4': 'Bonificación',                    # Más común en NCE
        '5': 'Crédito incobrable',              # Puede ser NCE o NDE
        '6': 'Recupero de costo',               # Típico NDE
        '7': 'Recupero de gasto',               # Típico NDE
        '8': 'Ajuste de precio'                 # Típico NDE (incremento)
    }

    return f'''        
    <!-- Campos específicos NDE (E400-E499) -->
    <gCamNCDE>
        <!-- Motivo de emisión -->
        <iMotEmi>{motivo}</iMotEmi>
        <dDesMotEmi>{motivos_desc.get(motivo, 'Recupero de costo')}</dDesMotEmi>
    </gCamNCDE>'''


def _build_items_section_nde(self, items: List[Dict], include_amounts: bool = True) -> str:
    """
    Construye sección de items específica para NDE

    Precios positivos para cargos adicionales, con descripción del concepto.
    """
    items_xml = []

    for i, item in enumerate(items, 1):
        # Calcular montos del item (siempre positivos para NDE)
        cantidad = item.get('cantidad', 1.0)
        precio_unit = item.get('precio_unitario', 0) if include_amounts else 0
        total_bruto = cantidad * precio_unit

        # Validar que el precio sea positivo (característica de NDE)
        if precio_unit < 0:
            precio_unit = abs(precio_unit)  # Convertir a positivo
            total_bruto = cantidad * precio_unit

        # Configurar IVA
        iva_config = self._get_iva_config(item.get('iva_tipo', 10))
        base_gravada = total_bruto if iva_config['gravado'] else 0
        monto_iva = base_gravada * \
            (iva_config['tasa'] / 100) if include_amounts else 0

        item_xml = f'''        
        <!-- Item NDE {i} -->
        <gCamItem>
            <iCorrelItem>{i}</iCorrelItem>
            <dDesProSer>{item['descripcion']}</dDesProSer>
            <dCodProSer>{item['codigo']}</dCodProSer>
            <dCantProSer>{cantidad:.2f}</dCantProSer>
            <dPUniProSer>{precio_unit:.2f}</dPUniProSer>
            <dTotBruOpeItem>{total_bruto:.2f}</dTotBruOpeItem>
            
            <!-- IVA por item (siempre positivo) -->
            <gCamIVA>
                <iAfecIVA>{iva_config['codigo']}</iAfecIVA>
                <dDesAfecIVA>{iva_config['descripcion']}</dDesAfecIVA>
                <dPropIVA>{iva_config['tasa']:.2f}</dPropIVA>
                <dTasaIVA>{iva_config['tasa']:.2f}</dTasaIVA>
                <dBasGravIVA>{base_gravada:.2f}</dBasGravIVA>
                <dLiqIVAItem>{monto_iva:.2f}</dLiqIVAItem>
            </gCamIVA>
            
            <!-- Información adicional del item NDE -->
            <gCamEsp>
                <dConceptoCargo>{item.get('concepto_cargo', 'Cargo adicional según contrato')}</dConceptoCargo>
                <dPeriodoMora>{item.get('periodo_mora', '')}</dPeriodoMora>
                <dFecVencOrig>{item.get('fecha_vencimiento_original', '')}</dFecVencOrig>
            </gCamEsp>
        </gCamItem>'''

        items_xml.append(item_xml)

    return '\n'.join(items_xml)


def _calculate_nde_totals(self, items: List[Dict]) -> Dict[str, float]:
    """
    Calcula totales para NDE considerando montos positivos

    Características:
    - Todos los montos son positivos (cargos adicionales)
    - Se suman al documento original
    - IVA se calcula normalmente sobre montos positivos
    """
    totales = {
        'total_exento': 0.0,
        'total_iva5': 0.0,
        'total_gravado10': 0.0,
        'base_gravada5': 0.0,
        'base_gravada10': 0.0,
        'iva_5': 0.0,
        'iva_10': 0.0,
        'total_iva': 0.0,
        'total_operacion': 0.0,
        'total_base_gravada': 0.0,
        'total_general': 0.0
    }

    for item in items:
        cantidad = item.get('cantidad', 1.0)
        precio = item.get('precio_unitario', 0)

        # Asegurar que el precio sea positivo (característica de NDE)
        precio = abs(precio)

        total_item = cantidad * precio
        iva_tipo = item.get('iva_tipo', 10)

        if iva_tipo == 0:  # Exento
            totales['total_exento'] += total_item
        elif iva_tipo == 5:  # IVA 5%
            totales['total_iva5'] += total_item
            totales['base_gravada5'] += total_item
            totales['iva_5'] += total_item * 0.05
        elif iva_tipo == 10:  # IVA 10%
            totales['total_gravado10'] += total_item
            totales['base_gravada10'] += total_item
            totales['iva_10'] += total_item * 0.10

    # Cálculos finales
    totales['total_iva'] = totales['iva_5'] + totales['iva_10']
    totales['total_base_gravada'] = totales['base_gravada5'] + \
        totales['base_gravada10']
    totales['total_operacion'] = totales['total_exento'] + \
        totales['total_iva5'] + totales['total_gravado10']
    totales['total_general'] = totales['total_operacion'] + \
        totales['total_iva']

    return totales


def _introduce_nde_errors(self, error_type: str, emisor: Dict, receptor: Dict,
                          items: List[Dict], totales: Dict, ref_doc_cdc: str) -> tuple:
    """Introduce errores específicos de NDE para testing negativo"""

    if error_type == 'negative_amounts':
        # Error: montos negativos en nota de débito
        for item in items:
            item['precio_unitario'] = - \
                abs(item['precio_unitario'])  # Cambiar a negativo

    elif error_type == 'missing_reference_document':
        # Error: falta referencia a documento original
        ref_doc_cdc = ''  # CDC vacío

    elif error_type == 'invalid_cdc_reference':
        # Error: CDC de referencia inválido
        ref_doc_cdc = '123456789'  # CDC inválido (muy corto)

    elif error_type == 'zero_amounts':
        # Error: montos en cero (no tiene sentido para cargos)
        for item in items:
            item['precio_unitario'] = 0.0

    elif error_type == 'missing_nde_section':
        # Error: falta sección NDE obligatoria
        # Se manejará en la construcción del XML
        pass

    elif error_type == 'invalid_motivo_nce':
        # Error: usar motivo típico de NCE en NDE
        # Motivo 2 (Devolución) no tiene sentido en NDE
        pass

    elif error_type == 'excessive_amounts':
        # Error: montos excesivos sin justificación
        for item in items:
            item['precio_unitario'] = 10000000  # Monto excesivo

    return emisor, receptor, items, totales, ref_doc_cdc

# =============================================
# DATOS DE EJEMPLO ESPECÍFICOS PARA NDE
# =============================================


def get_nde_sample_data():
    """Datos de ejemplo específicos para testing de NDE"""
    return {
        'escenarios_tipicos': {
            'intereses_mora_pago': {
                'motivo': '6',  # Recupero de costo
                'descripcion': 'Intereses por mora en pago de factura',
                'items': [
                    {
                        'codigo': 'INT001',
                        'descripcion': 'Intereses por mora - Factura vencida hace 30 días',
                        'cantidad': 1.0,
                        'precio_unitario': 120000,  # 2% sobre 6.000.000
                        'iva_tipo': 10,
                        'concepto_cargo': 'Interés mensual 2% sobre saldo vencido',
                        'periodo_mora': '30 días'
                    }
                ]
            },
            'gastos_cobranza_judicial': {
                'motivo': '7',  # Recupero de gasto
                'descripcion': 'Gastos por gestión de cobranza judicial',
                'items': [
                    {
                        'codigo': 'GJU001',
                        'descripcion': 'Honorarios profesionales - Gestión judicial',
                        'cantidad': 1.0,
                        'precio_unitario': 500000,
                        'iva_tipo': 10,
                        'concepto_cargo': 'Honorarios abogado por gestión de cobranza',
                        'periodo_mora': ''
                    },
                    {
                        'codigo': 'GJU002',
                        'descripcion': 'Gastos administrativos - Trámites judiciales',
                        'cantidad': 1.0,
                        'precio_unitario': 150000,
                        'iva_tipo': 10,
                        'concepto_cargo': 'Gastos por trámites y gestiones judiciales',
                        'periodo_mora': ''
                    }
                ]
            },
            'ajuste_precio_incremento': {
                'motivo': '8',  # Ajuste de precio
                'descripcion': 'Ajuste por incremento de precios no facturado',
                'items': [
                    {
                        'codigo': 'AJU001',
                        'descripcion': 'Ajuste: Incremento precio combustible',
                        'cantidad': 1.0,
                        'precio_unitario': 75000,
                        'iva_tipo': 10,
                        'concepto_cargo': 'Diferencia por incremento precio combustible 5%',
                        'periodo_mora': ''
                    }
                ]
            },
            'recupero_costos_operativos': {
                'motivo': '6',  # Recupero de costo
                'descripcion': 'Recupero de costos operativos adicionales',
                'items': [
                    {
                        'codigo': 'COP001',
                        'descripcion': 'Gastos de envío extraordinario - Entrega urgente',
                        'cantidad': 1.0,
                        'precio_unitario': 80000,
                        'iva_tipo': 10,
                        'concepto_cargo': 'Costo adicional por entrega urgente fuera de horario',
                        'periodo_mora': ''
                    },
                    {
                        'codigo': 'COP002',
                        'descripcion': 'Seguro adicional - Mercadería de alto valor',
                        'cantidad': 1.0,
                        'precio_unitario': 45000,
                        'iva_tipo': 0,  # Exento
                        'concepto_cargo': 'Prima adicional seguro para mercadería especial',
                        'periodo_mora': ''
                    }
                ]
            }
        }
    }

# =============================================
# VALIDACIONES ESPECÍFICAS NDE
# =============================================


def validate_nde_specific_rules(xml_content: str) -> tuple[bool, List[str]]:
    """
    Valida reglas específicas de NDE según Manual v150

    Validaciones:
    - Tipo 06 correcto
    - Sección gCamNCDE presente
    - Documento asociado presente
    - CDC de referencia válido
    - Montos positivos (característica NDE)
    - Motivo de emisión válido

    Args:
        xml_content: Contenido XML a validar

    Returns:
        tuple: (es_valido, lista_errores)
    """
    errors = []

    try:
        # Validar que es tipo 06
        if '<iTipDE>06</iTipDE>' not in xml_content:
            errors.append("Documento debe ser tipo 06 (NDE)")

        # Validar sección NDE presente (comparte con NCE)
        if '<gCamNCDE>' not in xml_content:
            errors.append("NDE: Sección gCamNCDE obligatoria faltante")

        # Validar documento asociado presente
        if '<gCamDEAsoc>' not in xml_content:
            errors.append("NDE: Documento asociado obligatorio faltante")

        # Validar CDC de referencia
        import re
        cdc_ref_match = re.search(r'<dCDCRef>(\d{44})</dCDCRef>', xml_content)
        if not cdc_ref_match:
            errors.append("NDE: CDC de referencia inválido o faltante")

        # Validar motivo de emisión
        motivo_match = re.search(r'<iMotEmi>(\d+)</iMotEmi>', xml_content)
        if motivo_match:
            motivo = motivo_match.group(1)
            if motivo not in ['1', '2', '3', '4', '5', '6', '7', '8']:
                errors.append(f"NDE: Motivo de emisión inválido: {motivo}")
            # Advertencia para motivos típicos de NCE en NDE
            elif motivo in ['2', '3', '4']:  # Devolución, Descuento, Bonificación
                errors.append(
                    f"NDE: Motivo '{motivo}' es más típico de NCE (considerar validar lógica de negocio)")
        else:
            errors.append("NDE: Motivo de emisión faltante")

        # Validar que los montos sean positivos (característica NDE)
        precio_matches = re.findall(
            r'<dPUniProSer>([+-]?\d+\.?\d*)</dPUniProSer>', xml_content)
        for precio in precio_matches:
            if float(precio) < 0:
                errors.append(
                    f"NDE: Precio unitario negativo detectado: {precio} (debería ser positivo para cargo adicional)")
            elif float(precio) == 0:
                errors.append(
                    f"NDE: Precio unitario en cero: {precio} (sin sentido para cargo adicional)")

        # Validar total general positivo
        total_match = re.search(
            r'<dTotGralOpe>([+-]?\d+\.?\d*)</dTotGralOpe>', xml_content)
        if total_match:
            total_nde = float(total_match.group(1))
            if total_nde <= 0:
                errors.append(
                    f"NDE: Total general debe ser positivo: {total_nde}")

    except Exception as e:
        errors.append(f"Error en validación NDE: {str(e)}")

    return len(errors) == 0, errors

# =============================================
# CASOS DE TESTING ESPECÍFICOS
# =============================================


def get_nde_test_cases():
    """Casos de testing específicos para NDE"""
    return {
        'intereses_mora_validos': {
            'descripcion': 'Intereses por mora en pago de factura',
            'motivo': '6',
            'ref_doc_cdc': '01800234561001001000001202412151200012345678',
            'monto_original': 6000000.0,
            'items': 'intereses_mora_pago',
            'valid': True
        },
        'gastos_cobranza_validos': {
            'descripcion': 'Gastos por gestión de cobranza judicial',
            'motivo': '7',
            'ref_doc_cdc': '01800234561001001000002202412151300012345679',
            'monto_original': 2000000.0,
            'items': 'gastos_cobranza_judicial',
            'valid': True
        },
        'ajuste_precio_valido': {
            'descripcion': 'Ajuste por incremento de precios',
            'motivo': '8',
            'ref_doc_cdc': '01800234561001001000003202412151400012345680',
            'monto_original': 1500000.0,
            'items': 'ajuste_precio_incremento',
            'valid': True
        },
        'recupero_costos_valido': {
            'descripcion': 'Recupero de costos operativos adicionales',
            'motivo': '6',
            'ref_doc_cdc': '01800234561001001000004202412151500012345681',
            'monto_original': 800000.0,
            'items': 'recupero_costos_operativos',
            'valid': True
        },
        'error_montos_negativos': {
            'descripcion': 'Error: montos negativos en nota de débito',
            'valid': False,
            'error_type': 'negative_amounts'
        },
        'error_sin_documento_referencia': {
            'descripcion': 'Error: falta referencia a documento original',
            'valid': False,
            'error_type': 'missing_reference_document'
        },
        'error_cdc_invalido': {
            'descripcion': 'Error: CDC de referencia inválido',
            'valid': False,
            'error_type': 'invalid_cdc_reference'
        },
        'error_montos_cero': {
            'descripcion': 'Error: montos en cero (sin sentido para cargos)',
            'valid': False,
            'error_type': 'zero_amounts'
        },
        'error_montos_excesivos': {
            'descripcion': 'Error: montos excesivos sin justificación',
            'valid': False,
            'error_type': 'excessive_amounts'
        }
    }

# =============================================
# UTILIDADES ESPECÍFICAS NDE
# =============================================


def calculate_interest_amount(principal: float, rate_monthly: float, days_overdue: int) -> float:
    """
    Calcula monto de intereses por mora

    Args:
        principal: Monto principal vencido
        rate_monthly: Tasa de interés mensual (ej: 0.02 para 2%)
        days_overdue: Días de atraso

    Returns:
        float: Monto de intereses calculado
    """
    daily_rate = rate_monthly / 30  # Tasa diaria
    interest = principal * daily_rate * days_overdue
    return round(interest, 2)


def get_motivos_nde_tipicos():
    """Obtiene motivos más comunes para NDE"""
    return {
        '6': 'Recupero de costo',     # Más común para NDE
        '7': 'Recupero de gasto',     # Muy común para NDE
        '8': 'Ajuste de precio',      # Común para NDE (incrementos)
        '5': 'Crédito incobrable',    # Puede ser NDE o NCE
        '1': 'Devolución y Ajuste de precios',  # Menos común para NDE
    }


def validate_business_logic_nde(motivo: str, items: List[Dict]) -> tuple[bool, List[str]]:
    """
    Valida lógica de negocio específica para NDE

    Args:
        motivo: Código del motivo de emisión
        items: Lista de items de la NDE

    Returns:
        tuple: (es_valido, lista_advertencias)
    """
    warnings = []

    # Validar coherencia entre motivo e items
    if motivo == '6':  # Recupero de costo
        cost_keywords = ['costo', 'gasto', 'envío', 'transporte', 'seguro']
        for item in items:
            desc = item.get('descripcion', '').lower()
            if not any(keyword in desc for keyword in cost_keywords):
                warnings.append(
                    f"Item '{item.get('codigo')}': descripción no parece relacionada con recupero de costo")

    elif motivo == '7':  # Recupero de gasto
        expense_keywords = ['honorario', 'judicial',
                            'administrativo', 'gestión', 'trámite']
        for item in items:
            desc = item.get('descripcion', '').lower()
            if not any(keyword in desc for keyword in expense_keywords):
                warnings.append(
                    f"Item '{item.get('codigo')}': descripción no parece relacionada con recupero de gasto")

    elif motivo == '8':  # Ajuste de precio
        adjustment_keywords = ['ajuste', 'incremento', 'diferencia', 'aumento']
        for item in items:
            desc = item.get('descripcion', '').lower()
            if not any(keyword in desc for keyword in adjustment_keywords):
                warnings.append(
                    f"Item '{item.get('codigo')}': descripción no parece relacionada con ajuste de precio")

    # Validar montos razonables
    for item in items:
        precio = item.get('precio_unitario', 0)
        if precio > 1000000:  # Más de 1 millón PYG
            warnings.append(
                f"Item '{item.get('codigo')}': monto elevado ({precio}) - verificar justificación")

    return len(warnings) == 0, warnings

# =============================================
# ---- Nota de Remisión Electrónica (NRE) - Tipo 07 ----
# =============================================


def generate_nota_remision_xml(self, valid: bool = True, **kwargs) -> str:
    """
    Genera XML de Nota de Remisión Electrónica (NRE) - Tipo 07

    Caso específico para traslado de mercaderías sin facturación.
    Enfoque en logística y transporte, sin valores monetarios.

    CASOS DE USO TÍPICOS:
    - Traslado entre sucursales de la misma empresa
    - Envío por venta (antes de facturar)
    - Traslado por consignación
    - Exportación/Importación (trámites aduaneros)
    - Traslado para reparación o transformación
    - Exhibición en ferias o demostraciones
    - Decomiso de mercaderías

    Args:
        valid: Si True, genera XML válido. Si False, introduce errores para testing
        **kwargs: Parámetros opcionales
            - emisor: Datos del emisor
            - receptor: Datos del receptor (puede ser = emisor para traslados internos)
            - items: Items a trasladar (sin precios unitarios)
            - motivo: Código del motivo de traslado (1-14, 99)
            - transporte: Datos del transporte y vehículo
            - fechas: Inicio y fin estimado del traslado

    Returns:
        str: XML completo de nota de remisión electrónica
    """
    # Obtener datos base
    emisor = kwargs.get(
        'emisor', self.sample_data.EMPRESAS_EJEMPLO['emisor_ferreteria'])
    motivo = kwargs.get('motivo', '1')  # 1 = Traslado por venta (más común)

    # Para motivo 7 (traslado entre locales), receptor = emisor
    if motivo == '7':
        receptor = emisor.copy()  # Mismo RUC para traslados internos
    else:
        receptor = kwargs.get(
            'receptor', self.sample_data.EMPRESAS_EJEMPLO['receptor_empresa'])

    items = kwargs.get('items', self._get_default_nre_items())
    fecha_emision = kwargs.get(
        'fecha_emision', datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    transporte = kwargs.get('transporte', self._get_default_transport_data())
    fechas_traslado = kwargs.get(
        'fechas_traslado', self._get_default_transfer_dates())

    # Generar CDC para tipo 07
    cdc = self._generate_cdc('07', emisor['ruc'], fecha_emision)

    # Para NRE, todos los totales son 0
    totales = self._calculate_nre_totals()  # Siempre retorna 0

    # Introducir errores si valid=False
    if not valid:
        error_type = kwargs.get('error_type', 'invalid_transport_data')
        emisor, receptor, items, transporte, fechas_traslado = self._introduce_nre_errors(
            error_type, emisor, receptor, items, transporte, fechas_traslado, motivo
        )

    # Construir XML
    xml_parts = [
        self._build_xml_header(),
        self._build_document_root(cdc),
        self._build_document_header('07', fecha_emision),
        self._build_timbrado_section(),
        self._build_datos_generales_section(fecha_emision),
        self._build_emisor_section(emisor),
        self._build_receptor_section(receptor),
        self._build_nre_specific_section(
            motivo, fechas_traslado),  # Sección específica NRE
        self._build_items_section_nre(
            items, include_amounts=False),  # Sin montos
        self._build_transport_section(
            transporte, fechas_traslado),  # Transporte obligatorio
        # Nota: NO incluir sección de totales para NRE
        self._build_document_footer()
    ]

    return '\n'.join(xml_parts)


def _get_default_nre_items(self) -> List[Dict]:
    """
    Obtiene items por defecto para una nota de remisión típica

    Solo cantidades y descripciones, SIN precios unitarios.
    """
    return [
        {
            'codigo': 'FER001',
            'descripcion': 'Martillo carpintero mango madera - Traslado a sucursal',
            'cantidad': 25.0,
            'unidad': '01',  # Unidad
            'datos_relevancia': '1',  # Sin particularidades
            'peso_bruto': 0.8,  # kg por unidad
            'observaciones': 'Herramientas para nueva sucursal Centro'
        },
        {
            'codigo': 'FER002',
            'descripcion': 'Destornillador cruz juego 6 piezas',
            'cantidad': 15.0,
            'unidad': '86',  # Juego
            'datos_relevancia': '1',  # Sin particularidades
            'peso_bruto': 0.3,  # kg por juego
            'observaciones': 'Herramientas básicas para técnicos'
        },
        {
            'codigo': 'FER003',
            'descripcion': 'Alambre galvanizado rollo 100m',
            'cantidad': 8.0,
            'unidad': '01',  # Unidad
            'datos_relevancia': '1',  # Sin particularidades
            'peso_bruto': 12.5,  # kg por rollo
            'observaciones': 'Material para construcción'
        }
    ]


def _get_default_transport_data(self) -> Dict[str, str]:
    """
    Obtiene datos por defecto del transporte

    Información completa del vehículo y transportista.
    """
    return {
        # Datos del transporte
        'tipo_transporte': '1',  # 1 = Terrestre
        'modalidad_transporte': '1',  # 1 = Transporte propio
        'responsable_emision': '1',  # 1 = Emisor de la factura
        'km_estimados': '85',  # Kilómetros del recorrido

        # Datos del vehículo
        'tipo_identificacion_vehiculo': '2',  # 2 = Matrícula
        'matricula_vehiculo': 'ABC123',
        'marca_vehiculo': 'Ford',
        'modelo_vehiculo': 'Transit',
        'año_vehiculo': '2018',
        'capacidad_carga': '1500',  # kg

        # Datos del transportista/conductor
        'nombre_transportista': 'Carlos Rodríguez Mendoza',
        'documento_transportista': '2345678',
        'tipo_documento_transportista': '1',  # 1 = Cédula paraguaya
        'nacionalidad_transportista': '1',  # 1 = Paraguayo
        'telefono_transportista': '0981-555-123',

        # Dirección origen y destino
        'direccion_origen': 'Av. España 890, Asunción',
        'direccion_destino': 'Av. Mariscal López 2456, Asunción',
        'departamento_origen': '1',  # Asunción
        'departamento_destino': '1',  # Asunción
        'ciudad_origen': '1',
        'ciudad_destino': '1'
    }


def _get_default_transfer_dates(self) -> Dict[str, str]:
    """
    Obtiene fechas por defecto del traslado

    Fecha inicio: mañana, Fecha fin: pasado mañana
    """
    from datetime import datetime, timedelta

    inicio = datetime.now() + timedelta(days=1)
    fin = inicio + timedelta(days=1)

    return {
        'fecha_inicio_traslado': inicio.strftime("%Y-%m-%d"),
        'fecha_fin_traslado': fin.strftime("%Y-%m-%d"),
        'hora_inicio': '08:00',
        'hora_fin': '17:00'
    }


def _build_nre_specific_section(self, motivo: str, fechas_traslado: Dict[str, str]) -> str:
    """
    Construye sección específica NRE (gCamNRE - E500-E599)

    Obligatoria para tipo de documento 07.
    Define motivo y responsable del traslado.
    """
    motivos_desc = {
        '1': 'Traslado por venta',
        '2': 'Traslado por consignación',
        '3': 'Exportación',
        '4': 'Traslado por compra',
        '5': 'Importación',
        '6': 'Traslado por devolución',
        '7': 'Traslado entre locales de la empresa',
        '8': 'Traslado de bienes por transformación',
        '9': 'Traslado de bienes por reparación',
        '10': 'Traslado por emisor móvil',
        '11': 'Exhibición o demostración',
        '12': 'Participación en ferias',
        '13': 'Traslado de encomienda',
        '14': 'Decomiso',
        '99': 'Otro'
    }

    responsables_desc = {
        '1': 'Emisor de la factura',
        '2': 'Poseedor de la factura y bienes',
        '3': 'Empresa transportista',
        '4': 'Despachante de Aduanas',
        '5': 'Agente de transporte o intermediario'
    }

    responsable = '1'  # Por defecto: Emisor de la factura

    return f'''        
    <!-- Campos específicos NRE (E500-E599) -->
    <gCamNRE>
        <!-- Motivo de emisión -->
        <iMotEmiNR>{motivo}</iMotEmiNR>
        <dDesMotEmiNR>{motivos_desc.get(motivo, 'Traslado por venta')}</dDesMotEmiNR>
        
        <!-- Responsable de la emisión -->
        <iRespEmiNR>{responsable}</iRespEmiNR>
        <dDesRespEmiNR>{responsables_desc.get(responsable, 'Emisor de la factura')}</dDesRespEmiNR>
        
        <!-- Kilómetros estimados -->
        <dKmR>85</dKmR>
        
        <!-- Fecha futura de emisión de factura (si aplica) -->
        {self._build_future_invoice_date(motivo)}
    </gCamNRE>'''


def _build_future_invoice_date(self, motivo: str) -> str:
    """
    Construye fecha futura de factura si es necesaria

    Solo para motivo 1 (Traslado por venta) sin documento asociado.
    """
    if motivo == '1':
        from datetime import datetime, timedelta
        fecha_futura = datetime.now() + timedelta(days=3)
        return f'<dFecEm>{fecha_futura.strftime("%Y-%m-%d")}</dFecEm>'
    return ''


def _build_items_section_nre(self, items: List[Dict], include_amounts: bool = False) -> str:
    """
    Construye sección de items específica para NRE

    Solo cantidades y descripciones, SIN montos.
    Incluye datos de relevancia de mercaderías obligatorios.
    """
    items_xml = []

    for i, item in enumerate(items, 1):
        cantidad = item.get('cantidad', 1.0)

        item_xml = f'''        
        <!-- Item NRE {i} -->
        <gCamItem>
            <iCorrelItem>{i}</iCorrelItem>
            <dDesProSer>{item['descripcion']}</dDesProSer>
            <dCodProSer>{item['codigo']}</dCodProSer>
            <dCantProSer>{cantidad:.2f}</dCantProSer>
            <cUniMed>{item.get('unidad', '01')}</cUniMed>
            <dDesUniMed>{self._get_unidad_desc(item.get('unidad', '01'))}</dDesUniMed>
            
            <!-- Datos de relevancia obligatorios para NRE -->
            <gCamEsp>
                <cRelMerc>{item.get('datos_relevancia', '1')}</cRelMerc>
                <dDesRelMerc>{self._get_relevancia_desc(item.get('datos_relevancia', '1'))}</dDesRelMerc>
                <dCanQuiMer>{item.get('cantidad_quiebra', 0.0):.2f}</dCanQuiMer>
                <dPorQuiMer>{item.get('porcentaje_quiebra', 0.0):.2f}</dPorQuiMer>
                <dPesBruMerc>{item.get('peso_bruto', 0.0):.2f}</dPesBruMerc>
            </gCamEsp>
            
            <!-- Observaciones del item -->
            <gCamObs>
                <dObsItem>{item.get('observaciones', '')}</dObsItem>
            </gCamObs>
        </gCamItem>'''

        items_xml.append(item_xml)

    return '\n'.join(items_xml)


def _build_transport_section(self, transporte: Dict[str, str], fechas_traslado: Dict[str, str]) -> str:
    """
    Construye sección de transporte obligatoria para NRE (E900-E999)

    Incluye datos del transporte, vehículo y transportista.
    """
    tipos_transporte = {
        '1': 'Terrestre',
        '2': 'Marítimo',
        '3': 'Aéreo'
    }

    modalidades_transporte = {
        '1': 'Transporte propio',
        '2': 'Transporte contratado',
        '3': 'Transporte público'
    }

    return f'''        
    <!-- Datos del transporte (E900-E999) -->
    <gCamTrans>
        <!-- Tipo y modalidad de transporte -->
        <iTipTrans>{transporte.get('tipo_transporte', '1')}</iTipTrans>
        <dDesTipTrans>{tipos_transporte.get(transporte.get('tipo_transporte', '1'), 'Terrestre')}</dDesTipTrans>
        <iModTrans>{transporte.get('modalidad_transporte', '1')}</iModTrans>
        <dDesModTrans>{modalidades_transporte.get(transporte.get('modalidad_transporte', '1'), 'Transporte propio')}</dDesModTrans>
        
        <!-- Fechas de traslado -->
        <dFecIniTrans>{fechas_traslado.get('fecha_inicio_traslado')}T{fechas_traslado.get('hora_inicio', '08:00')}:00</dFecIniTrans>
        <dFecFinTrans>{fechas_traslado.get('fecha_fin_traslado')}T{fechas_traslado.get('hora_fin', '17:00')}:00</dFecFinTrans>
        
        <!-- País de destino -->
        <cPaisDest>PRY</cPaisDest>
        <dDesPaisDest>Paraguay</dDesPaisDest>
        
        <!-- Datos del vehículo -->
        <gCamVeh>
            <iTipIdeVeh>{transporte.get('tipo_identificacion_vehiculo', '2')}</iTipIdeVeh>
            <dMatVeh>{transporte.get('matricula_vehiculo', 'ABC123')}</dMatVeh>
            <dMarcaVeh>{transporte.get('marca_vehiculo', 'Ford')}</dMarcaVeh>
            <dTipVeh>{transporte.get('modelo_vehiculo', 'Transit')}</dTipVeh>
            <dAnoVeh>{transporte.get('año_vehiculo', '2018')}</dAnoVeh>
            <dCapacVeh>{transporte.get('capacidad_carga', '1500')}</dCapacVeh>
        </gCamVeh>
        
        <!-- Datos del transportista -->
        <gCamTrans>
            <dNomTrans>{transporte.get('nombre_transportista', 'Carlos Rodríguez')}</dNomTrans>
            <dRucTrans>{transporte.get('documento_transportista', '2345678')}</dRucTrans>
            <dDVTrans>{transporte.get('dv_transportista', '9')}</dDVTrans>
            <iTipDocTrans>{transporte.get('tipo_documento_transportista', '1')}</iTipDocTrans>
            <dNumDocTrans>{transporte.get('documento_transportista', '2345678')}</dNumDocTrans>
            <iNacTrans>{transporte.get('nacionalidad_transportista', '1')}</iNacTrans>
            <dDesNacTrans>Paraguayo</dDesNacTrans>
            <dTelTrans>{transporte.get('telefono_transportista', '0981-555-123')}</dTelTrans>
        </gCamTrans>
        
        <!-- Direcciones origen y destino -->
        <gCamOrigen>
            <dDirOrigen>{transporte.get('direccion_origen', 'Av. España 890')}</dDirOrigen>
            <cDepOrigen>{transporte.get('departamento_origen', '1')}</cDepOrigen>
            <dDesDepOrigen>CAPITAL</dDesDepOrigen>
            <cCiuOrigen>{transporte.get('ciudad_origen', '1')}</cCiuOrigen>
            <dDesCiuOrigen>ASUNCION</dDesCiuOrigen>
        </gCamOrigen>
        
        <gCamDestino>
            <dDirDestino>{transporte.get('direccion_destino', 'Av. Mariscal López 2456')}</dDirDestino>
            <cDepDestino>{transporte.get('departamento_destino', '1')}</cDepDestino>
            <dDesDepDestino>CAPITAL</dDesDepDestino>
            <cCiuDestino>{transporte.get('ciudad_destino', '1')}</cCiuDestino>
            <dDesCiuDestino>ASUNCION</dDesCiuDestino>
        </gCamDestino>
    </gCamTrans>'''


def _calculate_nre_totals(self) -> Dict[str, float]:
    """
    Calcula totales para NRE (siempre 0)

    NRE no tiene valores monetarios, todos los totales son 0.
    """
    return {
        'total_exento': 0.0,
        'total_iva5': 0.0,
        'total_gravado10': 0.0,
        'base_gravada5': 0.0,
        'base_gravada10': 0.0,
        'iva_5': 0.0,
        'iva_10': 0.0,
        'total_iva': 0.0,
        'total_operacion': 0.0,
        'total_base_gravada': 0.0,
        'total_general': 0.0
    }


def _get_unidad_desc(self, codigo_unidad: str) -> str:
    """Obtiene descripción de unidad de medida"""
    unidades = {
        '01': 'Unidad',
        '47': 'Unidad de servicio',
        '86': 'Juego',
        '87': 'Paquete',
        '88': 'Rollo',
        '89': 'Metro',
        '90': 'Kilogramo'
    }
    return unidades.get(codigo_unidad, 'Unidad')


def _get_relevancia_desc(self, codigo_relevancia: str) -> str:
    """Obtiene descripción de datos de relevancia"""
    relevancias = {
        '1': 'Sin particularidades',
        '2': 'Con quiebra',
        '3': 'Con merma',
        '4': 'Con faltante',
        '5': 'Con sobrante'
    }
    return relevancias.get(codigo_relevancia, 'Sin particularidades')


def _introduce_nre_errors(self, error_type: str, emisor: Dict, receptor: Dict,
                          items: List[Dict], transporte: Dict, fechas_traslado: Dict, motivo: str) -> tuple:
    """Introduce errores específicos de NRE para testing negativo"""

    if error_type == 'invalid_transport_data':
        # Error: datos de transporte incompletos
        transporte = transporte.copy()
        transporte['matricula_vehiculo'] = ''  # Matrícula vacía

    elif error_type == 'invalid_transfer_dates':
        # Error: fechas de traslado inválidas
        fechas_traslado = fechas_traslado.copy()
        # Fecha anterior al inicio
        fechas_traslado['fecha_fin_traslado'] = '2020-01-01'

    elif error_type == 'missing_nre_section':
        # Error: falta sección NRE obligatoria
        # Se manejará en la construcción del XML
        pass

    elif error_type == 'invalid_motivo_interno':
        # Error: motivo 7 (traslado interno) pero receptor diferente
        if motivo == '7':
            receptor = receptor.copy()
            receptor['ruc'] = '80099999'  # RUC diferente al emisor

    elif error_type == 'with_monetary_amounts':
        # Error: incluir montos en NRE (no permitido)
        for item in items:
            item['precio_unitario'] = 50000  # Agregar precio (incorrecto)

    elif error_type == 'missing_future_invoice_date':
        # Error: falta fecha futura de factura para motivo 1
        # Se manejará en la construcción del XML
        pass

    elif error_type == 'invalid_vehicle_data':
        # Error: datos de vehículo inconsistentes
        transporte = transporte.copy()
        transporte['tipo_identificacion_vehiculo'] = '3'  # Tipo no válido

    elif error_type == 'missing_relevance_data':
        # Error: falta datos de relevancia obligatorios
        for item in items:
            item.pop('datos_relevancia', None)

    return emisor, receptor, items, transporte, fechas_traslado

# =============================================
# DATOS DE EJEMPLO ESPECÍFICOS PARA NRE
# =============================================


def get_nre_sample_data():
    """Datos de ejemplo específicos para testing de NRE"""
    return {
        'escenarios_tipicos': {
            'traslado_entre_sucursales': {
                'motivo': '7',  # Traslado entre locales de la empresa
                'descripcion': 'Traslado de herramientas entre sucursales',
                'emisor_receptor_iguales': True,
                'items': [
                    {
                        'codigo': 'TOOL001',
                        'descripcion': 'Set herramientas básicas - Traslado a sucursal Centro',
                        'cantidad': 10.0,
                        'unidad': '86',  # Juego
                        'peso_bruto': 2.5,
                        'datos_relevancia': '1',
                        'observaciones': 'Herramientas para nueva sucursal'
                    }
                ]
            },
            'traslado_por_venta': {
                'motivo': '1',  # Traslado por venta
                'descripcion': 'Envío de mercadería vendida (pre-facturación)',
                'emisor_receptor_diferentes': True,
                'requiere_fecha_futura_factura': True,
                'items': [
                    {
                        'codigo': 'PROD001',
                        'descripcion': 'Televisor LED 32" para entrega a cliente',
                        'cantidad': 2.0,
                        'unidad': '01',  # Unidad
                        'peso_bruto': 8.5,
                        'datos_relevancia': '1',
                        'observaciones': 'Entrega a domicilio - Venta confirmada'
                    }
                ]
            },
            'traslado_reparacion': {
                'motivo': '9',  # Traslado de bienes por reparación
                'descripcion': 'Envío de equipos a taller de reparación',
                'emisor_receptor_diferentes': True,
                'items': [
                    {
                        'codigo': 'EQUI001',
                        'descripcion': 'Computadora desktop para reparación - Placa madre',
                        'cantidad': 1.0,
                        'unidad': '01',  # Unidad
                        'peso_bruto': 12.0,
                        'datos_relevancia': '4',  # Con faltante (componentes)
                        'observaciones': 'Equipo con falla en placa madre'
                    }
                ]
            },
            'traslado_feria': {
                'motivo': '12',  # Participación en ferias
                'descripcion': 'Envío de productos para exhibición en feria',
                'emisor_receptor_diferentes': True,
                'items': [
                    {
                        'codigo': 'DEMO001',
                        'descripcion': 'Muestras de productos - Feria Expo 2024',
                        'cantidad': 50.0,
                        'unidad': '01',  # Unidad
                        'peso_bruto': 25.0,
                        'datos_relevancia': '1',
                        'observaciones': 'Productos para demostración en stand'
                    }
                ]
            }
        },
        'datos_transporte': {
            'transporte_propio_local': {
                'tipo_transporte': '1',  # Terrestre
                'modalidad_transporte': '1',  # Propio
                'vehiculo': {
                    'matricula': 'FER123',
                    'marca': 'Mitsubishi',
                    'modelo': 'L200',
                    'año': '2020',
                    'capacidad': '1000'
                },
                'conductor': {
                    'nombre': 'Roberto Silva Fernández',
                    'cedula': '3456789',
                    'telefono': '0985-444-567'
                }
            },
            'transporte_contratado': {
                'tipo_transporte': '1',  # Terrestre
                'modalidad_transporte': '2',  # Contratado
                'vehiculo': {
                    'matricula': 'LOG456',
                    'marca': 'Scania',
                    'modelo': 'P320',
                    'año': '2019',
                    'capacidad': '8000'
                },
                'conductor': {
                    'nombre': 'Mario Logística S.A.',
                    'ruc': '80098765-4',
                    'telefono': '021-555-9999'
                }
            }
        }
    }

# =============================================
# VALIDACIONES ESPECÍFICAS NRE
# =============================================


def validate_nre_specific_rules(xml_content: str) -> tuple[bool, List[str]]:
    """
    Valida reglas específicas de NRE según Manual v150

    Validaciones:
    - Tipo 07 correcto
    - Sección gCamNRE presente
    - Datos de transporte presentes
    - Fechas de traslado válidas
    - NO debe tener sección de totales
    - Datos de relevancia obligatorios en items
    - Para motivo 7: emisor = receptor

    Args:
        xml_content: Contenido XML a validar

    Returns:
        tuple: (es_valido, lista_errores)
    """
    errors = []

    try:
        # Validar que es tipo 07
        if '<iTipDE>07</iTipDE>' not in xml_content:
            errors.append("Documento debe ser tipo 07 (NRE)")

        # Validar sección NRE presente
        if '<gCamNRE>' not in xml_content:
            errors.append("NRE: Sección gCamNRE obligatoria faltante")

        # Validar datos de transporte presentes
        if '<gCamTrans>' not in xml_content:
            errors.append(
                "NRE: Sección de transporte gCamTrans obligatoria faltante")

        # Validar que NO tenga sección de totales (característica NRE)
        if '<gTotSub>' in xml_content:
            errors.append(
                "NRE: No debe incluir sección de totales (documento sin montos)")

        # Validar motivo de emisión
        import re
        motivo_match = re.search(r'<iMotEmiNR>(\d+)</iMotEmiNR>', xml_content)
        if motivo_match:
            motivo = motivo_match.group(1)
            motivos_validos = ['1', '2', '3', '4', '5', '6',
                               '7', '8', '9', '10', '11', '12', '13', '14', '99']
            if motivo not in motivos_validos:
                errors.append(f"NRE: Motivo de emisión inválido: {motivo}")
        else:
            errors.append("NRE: Motivo de emisión faltante")

        # Validar fechas de traslado
        fecha_inicio_match = re.search(
            r'<dFecIniTrans>([^<]+)</dFecIniTrans>', xml_content)
        fecha_fin_match = re.search(
            r'<dFecFinTrans>([^<]+)</dFecFinTrans>', xml_content)

        if not fecha_inicio_match:
            errors.append(
                "NRE: Fecha de inicio de traslado obligatoria faltante")
        if not fecha_fin_match:
            errors.append("NRE: Fecha de fin de traslado obligatoria faltante")

        if fecha_inicio_match and fecha_fin_match:
            try:
                from datetime import datetime
                fecha_inicio = datetime.fromisoformat(
                    fecha_inicio_match.group(1).replace('T', ' ').replace('Z', ''))
                fecha_fin = datetime.fromisoformat(
                    fecha_fin_match.group(1).replace('T', ' ').replace('Z', ''))

                if fecha_fin <= fecha_inicio:
                    errors.append(
                        "NRE: Fecha fin de traslado debe ser posterior al inicio")

                # Validar que las fechas sean futuras
                ahora = datetime.now()
                if fecha_inicio <= ahora:
                    errors.append("NRE: Fecha de inicio debe ser futura")

            except Exception as e:
                errors.append(
                    f"NRE: Error al validar fechas de traslado: {str(e)}")

        # Validar datos del vehículo
        if '<gCamVeh>' not in xml_content:
            errors.append("NRE: Datos del vehículo obligatorios faltantes")

        # Validar datos de relevancia en items
        relevancia_matches = re.findall(
            r'<cRelMerc>(\d+)</cRelMerc>', xml_content)
        if not relevancia_matches:
            errors.append(
                "NRE: Datos de relevancia de mercaderías obligatorios faltantes en items")

        # Validar coherencia motivo 7 (traslado interno)
        if motivo_match and motivo_match.group(1) == '7':
            ruc_emisor_match = re.search(
                r'<dRUCEmi>(\d+)</dRUCEmi>', xml_content)
            ruc_receptor_match = re.search(
                r'<dRUCRec>(\d+)</dRUCRec>', xml_content)

            if ruc_emisor_match and ruc_receptor_match:
                ruc_emisor = ruc_emisor_match.group(1)
                ruc_receptor = ruc_receptor_match.group(1)

                if ruc_emisor != ruc_receptor:
                    errors.append(
                        f"NRE: Para motivo 7 (traslado interno), emisor y receptor deben tener mismo RUC")

        # Validar que no tenga precios unitarios (característica NRE)
        precio_matches = re.findall(
            r'<dPUniProSer>([+-]?\d+\.?\d*)</dPUniProSer>', xml_content)
        for precio in precio_matches:
            if float(precio) != 0:
                errors.append(
                    f"NRE: No debe tener precios unitarios (encontrado: {precio})")

        # Validar matrícula del vehículo
        matricula_match = re.search(r'<dMatVeh>([^<]+)</dMatVeh>', xml_content)
        if not matricula_match or not matricula_match.group(1).strip():
            errors.append("NRE: Matrícula del vehículo obligatoria")

    except Exception as e:
        errors.append(f"Error en validación NRE: {str(e)}")

    return len(errors) == 0, errors

# =============================================
# CASOS DE TESTING ESPECÍFICOS
# =============================================


def get_nre_test_cases():
    """Casos de testing específicos para NRE"""
    return {
        'traslado_entre_sucursales_valido': {
            'descripcion': 'Traslado de herramientas entre sucursales de la empresa',
            'motivo': '7',
            'emisor_igual_receptor': True,
            'items': 'traslado_entre_sucursales',
            'transporte': 'transporte_propio_local',
            'valid': True
        },
        'traslado_por_venta_valido': {
            'descripcion': 'Envío de mercadería vendida (pre-facturación)',
            'motivo': '1',
            'requiere_fecha_futura': True,
            'items': 'traslado_por_venta',
            'transporte': 'transporte_contratado',
            'valid': True
        },
        'traslado_reparacion_valido': {
            'descripcion': 'Envío de equipos a taller de reparación',
            'motivo': '9',
            'items': 'traslado_reparacion',
            'transporte': 'transporte_propio_local',
            'valid': True
        },
        'traslado_feria_valido': {
            'descripcion': 'Productos para exhibición en feria comercial',
            'motivo': '12',
            'items': 'traslado_feria',
            'transporte': 'transporte_contratado',
            'valid': True
        },
        'error_datos_transporte_faltantes': {
            'descripcion': 'Error: datos de transporte incompletos',
            'valid': False,
            'error_type': 'invalid_transport_data'
        },
        'error_fechas_traslado_invalidas': {
            'descripcion': 'Error: fecha fin anterior a fecha inicio',
            'valid': False,
            'error_type': 'invalid_transfer_dates'
        },
        'error_motivo_interno_ruc_diferente': {
            'descripcion': 'Error: motivo 7 pero emisor ≠ receptor',
            'valid': False,
            'error_type': 'invalid_motivo_interno',
            'motivo': '7'
        },
        'error_con_montos_monetarios': {
            'descripcion': 'Error: NRE con valores monetarios (no permitido)',
            'valid': False,
            'error_type': 'with_monetary_amounts'
        },
        'error_datos_vehiculo_invalidos': {
            'descripcion': 'Error: datos del vehículo inconsistentes',
            'valid': False,
            'error_type': 'invalid_vehicle_data'
        },
        'error_sin_datos_relevancia': {
            'descripcion': 'Error: falta datos de relevancia en items',
            'valid': False,
            'error_type': 'missing_relevance_data'
        }
    }

# =============================================
# UTILIDADES ESPECÍFICAS NRE
# =============================================


def get_motivos_nre():
    """Obtiene lista completa de motivos para NRE"""
    return {
        '1': 'Traslado por venta',
        '2': 'Traslado por consignación',
        '3': 'Exportación',
        '4': 'Traslado por compra',
        '5': 'Importación',
        '6': 'Traslado por devolución',
        '7': 'Traslado entre locales de la empresa',
        '8': 'Traslado de bienes por transformación',
        '9': 'Traslado de bienes por reparación',
        '10': 'Traslado por emisor móvil',
        '11': 'Exhibición o demostración',
        '12': 'Participación en ferias',
        '13': 'Traslado de encomienda',
        '14': 'Decomiso',
        '99': 'Otro (especificar)'
    }


def get_tipos_transporte():
    """Obtiene tipos de transporte válidos"""
    return {
        '1': 'Terrestre',
        '2': 'Marítimo',
        '3': 'Aéreo'
    }


def get_modalidades_transporte():
    """Obtiene modalidades de transporte válidas"""
    return {
        '1': 'Transporte propio',
        '2': 'Transporte contratado',
        '3': 'Transporte público'
    }


def get_responsables_emision():
    """Obtiene responsables de emisión válidos"""
    return {
        '1': 'Emisor de la factura',
        '2': 'Poseedor de la factura y bienes',
        '3': 'Empresa transportista',
        '4': 'Despachante de Aduanas',
        '5': 'Agente de transporte o intermediario'
    }


def calculate_total_weight(items: List[Dict]) -> float:
    """
    Calcula peso total del envío

    Args:
        items: Lista de items con peso_bruto por unidad

    Returns:
        float: Peso total en kilogramos
    """
    peso_total = 0.0
    for item in items:
        cantidad = item.get('cantidad', 0)
        peso_unitario = item.get('peso_bruto', 0)
        peso_total += cantidad * peso_unitario

    return round(peso_total, 2)


def validate_transport_capacity(items: List[Dict], vehiculo_capacidad: float) -> tuple[bool, str]:
    """
    Valida que el peso total no exceda la capacidad del vehículo

    Args:
        items: Items a transportar
        vehiculo_capacidad: Capacidad del vehículo en kg

    Returns:
        tuple: (es_valido, mensaje)
    """
    peso_total = calculate_total_weight(items)

    if peso_total > vehiculo_capacidad:
        return False, f"Peso total ({peso_total} kg) excede capacidad del vehículo ({vehiculo_capacidad} kg)"

    margen_seguridad = vehiculo_capacidad * 0.9  # 90% de la capacidad
    if peso_total > margen_seguridad:
        return True, f"Advertencia: Peso total ({peso_total} kg) cerca del límite (capacidad: {vehiculo_capacidad} kg)"

    return True, f"Peso total válido: {peso_total} kg de {vehiculo_capacidad} kg"


def estimate_transfer_time(
    km_distancia: int,
    tipo_transporte: str = '1'
) -> Dict[str, Union[float, int, str]]:
    """
    Estima tiempo de traslado según distancia y tipo de transporte

    Args:
        km_distancia: Distancia en kilómetros
        tipo_transporte: '1'=Terrestre, '2'=Marítimo, '3'=Aéreo

    Returns:
        dict: {
            'horas_estimadas': float,        # puede tener decimales
            'velocidad_promedio': int,
            'tipo_transporte': str
        }
    """
    # Defino velocidades promedio por tipo
    velocidades_promedio = {
        '1': 60,   # Terrestre: 60 km/h
        '2': 25,   # Marítimo: 25 km/h
        '3': 800   # Aéreo: 800 km/h
    }

    # Obtengo la velocidad, si no existe el tipo uso terrestre
    velocidad = velocidades_promedio.get(tipo_transporte, 60)

    # Calculo horas y lo redondeo a un decimal
    horas_estimadas = round(km_distancia / velocidad, 1)

    return {
        'horas_estimadas': horas_estimadas,    # float
        'velocidad_promedio': velocidad,       # int
        'tipo_transporte': tipo_transporte     # str
    }
