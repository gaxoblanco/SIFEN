#!/usr/bin/env python3
"""
Test específico para el template autofactura_electronica.xml
Valida la generación XML para AFE (Tipo 4)
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from jinja2 import Template


def crear_template_inline():
    """
    Template autofactura_electronica.xml inline para testing
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd"
     version="1.5.0"
     Id="{{ cdc }}">

    <dVerFor>{{ version | default('150') }}</dVerFor>
    
    <DE Id="{{ cdc }}">
        <!-- gOpeDE: Datos de la operación AFE -->
        <gOpeDE>
            <iTipDE>4</iTipDE>
            <dDesTipDE>Autofactura electrónica</dDesTipDE>
            <dFecEmiDE>{{ fecha_emision }}</dFecEmiDE>
        </gOpeDE>

        <!-- gTimb: Datos del timbrado -->
        <gTimb>
            <iTiTim>{{ timbrado.tipo | default(1) }}</iTiTim>
            <dDesTiTim>{{ timbrado.descripcion_tipo | default("Timbrado electrónico SET") }}</dDesTiTim>
            <dNumTim>{{ timbrado.numero_timbrado }}</dNumTim>
            <dEst>{{ timbrado.establecimiento }}</dEst>
            <dPunExp>{{ timbrado.punto_expedicion }}</dPunExp>
            <dNumDoc>{{ timbrado.numero_documento }}</dNumDoc>
        </gTimb>

        <!-- gDatGralOpe: Datos generales de la operación -->
        <gDatGralOpe>
            <dFeEmiDE>{{ fecha_emision }}</dFeEmiDE>
            <iTipEmi>{{ tipo_emision | default(1) }}</iTipEmi>
            <dDesTipEmi>{{ descripcion_tipo_emision | default("Normal") }}</dDesTipEmi>
        </gDatGralOpe>

        <!-- gEmis: Datos del emisor (= receptor en AFE) -->
        <gEmis>
            <dRucEm>{{ emisor.ruc }}{{ emisor.dv }}</dRucEm>
            <dDVEmi>{{ emisor.dv }}</dDVEmi>
            <dNomEmi>{{ emisor.razon_social }}</dNomEmi>
            <dDirEmi>{{ emisor.direccion }}</dDirEmi>
            {% if emisor.telefono %}
            <dTelEmi>{{ emisor.telefono }}</dTelEmi>
            {% endif %}
            {% if emisor.email %}
            <dEmailE>{{ emisor.email }}</dEmailE>
            {% endif %}
        </gEmis>

        <!-- gDatRec: Datos del receptor (= emisor en AFE) -->
        <gDatRec>
            <iNatRec>{{ receptor.naturaleza | default(2) }}</iNatRec>
            <dDesNatRec>{{ receptor.descripcion_naturaleza | default("Contribuyente") }}</dDesNatRec>
            {% if receptor.tipo_documento %}
            <iTiContRec>{{ receptor.tipo_documento }}</iTiContRec>
            {% endif %}
            {% if receptor.numero_documento %}
            <dNumIDRec>{{ receptor.numero_documento }}</dNumIDRec>
            {% endif %}
            <dNomRec>{{ receptor.razon_social }}</dNomRec>
            {% if receptor.direccion %}
            <dDirRec>{{ receptor.direccion }}</dDirRec>
            {% endif %}
        </gDatRec>

        <!-- gCamItem: Items/productos -->
        {% for item in items %}
        <gCamItem>
            {% if item.codigo_interno %}
            <dCodInt>{{ item.codigo_interno }}</dCodInt>
            {% endif %}
            <dDesProSer>{{ item.descripcion }}</dDesProSer>
            <dDesUniMed>{{ item.descripcion_unidad_medida | default("Unidad") }}</dDesUniMed>
            <dCantProSer>{{ item.cantidad }}</dCantProSer>
            <dPUniProSer>{{ item.precio_unitario }}</dPUniProSer>
            <dTotOpeIt>{{ item.total_operacion }}</dTotOpeIt>
            
            <!-- Código NCM para importaciones -->
            {% if item.codigo_ncm %}
            <dNCM>{{ item.codigo_ncm }}</dNCM>
            {% endif %}
            
            <!-- País de origen para importaciones -->
            {% if item.codigo_pais_origen %}
            <cPaisOrig>{{ item.codigo_pais_origen }}</cPaisOrig>
            {% endif %}
            {% if item.descripcion_pais_origen %}
            <dDesPaisOrig>{{ item.descripcion_pais_origen }}</dDesPaisOrig>
            {% endif %}
            
            <!-- IVA del ítem -->
            <iAfecIVA>{{ item.afectacion_iva }}</iAfecIVA>
            <dDesAfecIVA>{{ item.descripcion_afectacion_iva }}</dDesAfecIVA>
            {% if item.tasa_iva %}
            <dTasaIVA>{{ item.tasa_iva }}</dTasaIVA>
            {% endif %}
            {% if item.base_gravable %}
            <dBasGravIVA>{{ item.base_gravable }}</dBasGravIVA>
            {% endif %}
            {% if item.liquidacion_iva %}
            <dLiqIVAItem>{{ item.liquidacion_iva }}</dLiqIVAItem>
            {% endif %}
        </gCamItem>
        {% endfor %}

        <!-- gTotSub: Totales y subtotales -->
        <gTotSub>
            {% if totales.subtotal_gravado %}
            <dSubGrav>{{ totales.subtotal_gravado }}</dSubGrav>
            {% endif %}
            {% if totales.subtotal_exento %}
            <dSubExe>{{ totales.subtotal_exento }}</dSubExe>
            {% endif %}
            <dTotOpe>{{ totales.total_operacion }}</dTotOpe>
            {% if totales.total_iva %}
            <dTotIVA>{{ totales.total_iva }}</dTotIVA>
            {% endif %}
            {% if totales.liquidacion_iva_10 %}
            <dLiqTotIVA10>{{ totales.liquidacion_iva_10 }}</dLiqTotIVA10>
            {% endif %}
            <dTotGralOpe>{{ totales.total_general }}</dTotGralOpe>
            
            <!-- Moneda y tipo de cambio para importaciones -->
            {% if totales.codigo_moneda %}
            <cMoneOpe>{{ totales.codigo_moneda }}</cMoneOpe>
            {% endif %}
            {% if totales.descripcion_moneda %}
            <dDesMoneOpe>{{ totales.descripcion_moneda }}</dDesMoneOpe>
            {% endif %}
            {% if totales.tipo_cambio %}
            <dTiCam>{{ totales.tipo_cambio }}</dTiCam>
            {% endif %}
            {% if totales.total_moneda_extranjera %}
            <dTotGralOpeME>{{ totales.total_moneda_extranjera }}</dTotGralOpeME>
            {% endif %}
        </gTotSub>

        <!-- gDtipDE: Campos específicos Autofactura -->
        <gDtipDE>
            <gCamAE>
                <!-- Naturaleza del vendedor -->
                <iNatVen>{{ vendedor.naturaleza_vendedor }}</iNatVen>
                <dDesNatVen>{{ vendedor.descripcion_naturaleza_vendedor }}</dDesNatVen>
                
                <!-- Identificación del vendedor -->
                <iTipIDVen>{{ vendedor.tipo_documento_vendedor }}</iTipIDVen>
                <dDTipIDVen>{{ vendedor.descripcion_tipo_documento_vendedor }}</dDTipIDVen>
                <dNumIDVen>{{ vendedor.numero_documento_vendedor }}</dNumIDVen>
                
                <!-- Datos personales del vendedor -->
                <dNomVen>{{ vendedor.nombre_vendedor }}</dNomVen>
                <dDirVen>{{ vendedor.direccion_vendedor }}</dDirVen>
                {% if vendedor.numero_casa_vendedor %}
                <dNumCasVen>{{ vendedor.numero_casa_vendedor }}</dNumCasVen>
                {% endif %}
                
                <!-- Ubicación geográfica del vendedor -->
                <cDepVen>{{ vendedor.codigo_departamento_vendedor }}</cDepVen>
                <dDesDepVen>{{ vendedor.descripcion_departamento_vendedor }}</dDesDepVen>
                <cDisVen>{{ vendedor.codigo_distrito_vendedor }}</cDisVen>
                <dDesDisVen>{{ vendedor.descripcion_distrito_vendedor }}</dDesDisVen>
                <cCiuVen>{{ vendedor.codigo_ciudad_vendedor }}</cCiuVen>
                <dDesCiuVen>{{ vendedor.descripcion_ciudad_vendedor }}</dDesCiuVen>
                
                <!-- Email del vendedor (opcional) -->
                {% if vendedor.email_vendedor %}
                <dDirEmailVen>{{ vendedor.email_vendedor }}</dDirEmailVen>
                {% endif %}
                
                <!-- Ubicación de la transacción -->
                <cDepTrans>{{ vendedor.codigo_departamento_transaccion }}</cDepTrans>
                <dDesDepTrans>{{ vendedor.descripcion_departamento_transaccion }}</dDesDepTrans>
                <cDisTrans>{{ vendedor.codigo_distrito_transaccion }}</cDisTrans>
                <dDesDisTrans>{{ vendedor.descripcion_distrito_transaccion }}</dDesDisTrans>
                <cCiuTrans>{{ vendedor.codigo_ciudad_transaccion }}</cCiuTrans>
                <dDesCiuTrans>{{ vendedor.descripcion_ciudad_transaccion }}</dDesCiuTrans>
            </gCamAE>
        </gDtipDE>

        <!-- gCamGen: Condiciones de la operación (opcional) -->
        {% if condiciones %}
        <gCamGen>
            {% if condiciones.modalidad_venta %}
            <iFormCancPag>{{ condiciones.modalidad_venta }}</iFormCancPag>
            {% endif %}
            {% if condiciones.descripcion_modalidad %}
            <dDesFormCancPag>{{ condiciones.descripcion_modalidad }}</dDesFormCancPag>
            {% endif %}
            
            <!-- Pagos al contado -->
            {% if condiciones.pagos_contado %}
            {% for pago in condiciones.pagos_contado %}
            <gPagCont>
                <iTiPago>{{ pago.modalidad }}</iTiPago>
                <dDesTiPag>{{ pago.descripcion }}</dDesTiPag>
                <dMonTiPag>{{ pago.monto }}</dMonTiPag>
            </gPagCont>
            {% endfor %}
            {% endif %}
        </gCamGen>
        {% endif %}
    </DE>
</rDE>'''


def crear_datos_prueba_importacion():
    """Crear datos de prueba para AFE de importación (vendedor extranjero)"""
    print("📝 Creando datos de prueba AFE - Importación...")

    # Generar CDC simulado de 44 caracteres
    cdc = "01800695631001001000000612025063015100000001"

    datos = {
        # Identificación
        'cdc': cdc,
        'fecha_emision': "2025-06-30T15:10:00",

        # Timbrado
        'timbrado': {
            'numero_timbrado': "87654321",
            'establecimiento': "001",
            'punto_expedicion': "001",
            'numero_documento': "0000001",
            'tipo': 1,
            'descripcion_tipo': "Timbrado electrónico SET"
        },

        # Emisor (= Receptor en AFE)
        'emisor': {
            'ruc': "80016875",
            'dv': "4",
            'razon_social': "IMPORTADORA DEMO S.A.",
            'direccion': "Av. Artigas 850, Asunción",
            'telefono': "+595 21 654321",
            'email': "importacion@demo.com.py"
        },

        # Receptor (= Emisor en AFE)
        'receptor': {
            'naturaleza': 2,
            'descripcion_naturaleza': "Contribuyente",
            'tipo_documento': 2,
            'numero_documento': "80016875",
            'razon_social': "IMPORTADORA DEMO S.A.",
            'direccion': "Av. Artigas 850, Asunción"
        },

        # Items (productos importados)
        'items': [
            {
                'codigo_interno': "IMP001",
                'descripcion': "Notebook HP ProBook 450 G8 - Importado",
                'cantidad': Decimal("10.000"),
                'descripcion_unidad_medida': "Unidad",
                'precio_unitario': Decimal("800"),  # En USD
                'total_operacion': Decimal("8000"),  # 10 x 800 USD
                'codigo_ncm': "8471301000",  # NCM para notebooks
                'codigo_pais_origen': "US",
                'descripcion_pais_origen': "Estados Unidos",
                'afectacion_iva': 1,
                'descripcion_afectacion_iva': "Gravado IVA 10%",
                'tasa_iva': Decimal("10.00"),
                # 8000 USD * 7300 PYG/USD
                'base_gravable': Decimal("58400000"),
                'liquidacion_iva': Decimal("5840000")  # 10% de base gravable
            },
            {
                'codigo_interno': "IMP002",
                'descripcion': "Mouse inalámbrico Logitech MX Master 3",
                'cantidad': Decimal("25.000"),
                'descripcion_unidad_medida': "Unidad",
                'precio_unitario': Decimal("80"),  # En USD
                'total_operacion': Decimal("2000"),  # 25 x 80 USD
                'codigo_ncm': "8471606000",  # NCM para mouse
                'codigo_pais_origen': "CN",
                'descripcion_pais_origen': "China",
                'afectacion_iva': 1,
                'descripcion_afectacion_iva': "Gravado IVA 10%",
                'tasa_iva': Decimal("10.00"),
                # 2000 USD * 7300 PYG/USD
                'base_gravable': Decimal("14600000"),
                'liquidacion_iva': Decimal("1460000")  # 10% de base gravable
            },
            {
                'codigo_interno': "SER001",
                'descripcion': "Flete internacional y seguro de importación",
                'cantidad': Decimal("1.000"),
                'descripcion_unidad_medida': "Servicio",
                'precio_unitario': Decimal("500"),  # En USD
                'total_operacion': Decimal("500"),  # Flete
                'afectacion_iva': 2,
                'descripcion_afectacion_iva': "Exento",
                'base_gravable': Decimal("0"),
                'liquidacion_iva': Decimal("0")
            }
        ],

        # Totales
        'totales': {
            'subtotal_gravado': Decimal("73000000"),  # Items gravados en PYG
            'subtotal_exento': Decimal("3650000"),   # Flete en PYG
            'total_operacion': Decimal("76650000"),  # Total en PYG
            'total_iva': Decimal("7300000"),         # IVA total
            'liquidacion_iva_10': Decimal("7300000"),
            'total_general': Decimal("83950000"),    # Total final en PYG

            # Moneda extranjera
            'codigo_moneda': "USD",
            'descripcion_moneda': "Dólar estadounidense",
            'tipo_cambio': Decimal("7300.00"),       # Tipo cambio PYG/USD
            'total_moneda_extranjera': Decimal("10500")  # Total en USD
        },

        # Vendedor original (extranjero)
        'vendedor': {
            'naturaleza_vendedor': "2",  # Extranjero
            'descripcion_naturaleza_vendedor': "Extranjero",
            'tipo_documento_vendedor': "2",  # Pasaporte
            'descripcion_tipo_documento_vendedor': "Pasaporte",
            'numero_documento_vendedor': "P123456789USA",
            'nombre_vendedor': "International Tech Supplies Inc.",
            'direccion_vendedor': "Miami Trade Center, 123 Biscayne Blvd",
            'numero_casa_vendedor': "Suite 505",

            # Ubicación del vendedor (simulada en Paraguay para el ejemplo)
            'codigo_departamento_vendedor': "1",
            'descripcion_departamento_vendedor': "CAPITAL",
            'codigo_distrito_vendedor': "1",
            'descripcion_distrito_vendedor': "ASUNCION",
            'codigo_ciudad_vendedor': "1",
            'descripcion_ciudad_vendedor': "ASUNCION",

            'email_vendedor': "sales@inttechsupplies.com",

            # Ubicación de la transacción (en Paraguay)
            'codigo_departamento_transaccion': "1",
            'descripcion_departamento_transaccion': "CAPITAL",
            'codigo_distrito_transaccion': "1",
            'descripcion_distrito_transaccion': "ASUNCION",
            'codigo_ciudad_transaccion': "1",
            'descripcion_ciudad_transaccion': "ASUNCION"
        },

        # Condiciones
        'condiciones': {
            'modalidad_venta': 1,
            'descripcion_modalidad': "Contado",
            'pagos_contado': [
                {
                    'modalidad': 4,  # Transferencia bancaria
                    'descripcion': "Transferencia bancaria internacional",
                    'monto': Decimal("83950000")
                }
            ]
        }
    }

    print("✅ Datos de prueba AFE importación creados")
    return datos


def validar_afe_datos(datos):
    """Validaciones específicas para AFE"""
    print("🔍 Validando datos AFE...")

    errores = []

    # 1. Emisor = Receptor (crítico)
    if datos['emisor']['ruc'] != datos['receptor']['numero_documento']:
        errores.append("AFE: Emisor y receptor deben tener mismo RUC")

    # 2. Naturaleza vendedor válida
    if datos['vendedor']['naturaleza_vendedor'] not in ["1", "2"]:
        errores.append("AFE: Naturaleza vendedor debe ser 1 o 2")

    # 3. Datos geográficos completos
    campos_geo_requeridos = [
        'codigo_departamento_vendedor',
        'descripcion_departamento_vendedor',
        'codigo_distrito_vendedor',
        'descripcion_distrito_vendedor',
        'codigo_ciudad_vendedor',
        'descripcion_ciudad_vendedor',
        'codigo_departamento_transaccion',
        'descripcion_departamento_transaccion',
        'codigo_distrito_transaccion',
        'descripcion_distrito_transaccion',
        'codigo_ciudad_transaccion',
        'descripcion_ciudad_transaccion',
    ]

    for campo in campos_geo_requeridos:
        if campo not in datos['vendedor'] or not datos['vendedor'][campo]:
            errores.append(f"AFE: Campo {campo} es obligatorio")

    # 4. Moneda extranjera para importaciones
    if datos['vendedor']['naturaleza_vendedor'] == "2":  # Extranjero
        if 'codigo_moneda' not in datos['totales']:
            print("⚠️ ADVERTENCIA: Importación sin moneda extranjera especificada")

    if errores:
        print("❌ Errores de validación:")
        for error in errores:
            print(f"   - {error}")
        return False

    print("✅ Validaciones AFE pasadas")
    return True


def test_generar_xml_afe():
    """Test principal para generar XML AFE"""
    print("🚀 GENERANDO XML DE AUTOFACTURA ELECTRÓNICA (AFE)")
    print("=" * 70)

    try:
        # 1. Crear template
        print("🔧 Creando template AFE...")
        template_content = crear_template_inline()
        template = Template(template_content)
        print("✅ Template AFE creado")

        # 2. Crear datos
        datos = crear_datos_prueba_importacion()

        # 3. Validar datos AFE
        if not validar_afe_datos(datos):
            return False, "Validación de datos falló"

        # 4. Renderizar
        print("⚙️ Renderizando XML AFE...")
        xml_content = template.render(**datos)
        print("✅ XML AFE renderizado exitosamente")

        # 5. Guardar archivo
        output_file = "autofactura_electronica_generada.xml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"💾 XML guardado en: {output_file}")

        # 6. Mostrar estadísticas
        lines = xml_content.split('\n')
        print(f"\n📊 ESTADÍSTICAS AFE:")
        print(f"   - Tamaño: {len(xml_content):,} caracteres")
        print(f"   - Líneas: {len(lines):,}")
        print(f"   - Elementos XML: {xml_content.count('<'):,}")

        # 7. Validaciones específicas AFE
        print(f"\n🔍 VALIDACIONES BÁSICAS AFE:")

        validaciones = [
            ('Declaración XML', '<?xml version="1.0"' in xml_content),
            ('Namespace SIFEN', 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml_content),
            ('CDC AFE presente', datos['cdc'] in xml_content),
            ('Tipo documento AFE', '<iTipDE>4</iTipDE>' in xml_content),
            ('Campos específicos AFE', '<gCamAE>' in xml_content),
            ('Naturaleza vendedor',
             f"<iNatVen>{datos['vendedor']['naturaleza_vendedor']}</iNatVen>" in xml_content),
            ('Nombre vendedor', datos['vendedor']
             ['nombre_vendedor'] in xml_content),
            ('RUC emisor/receptor',
             f"<dRucEm>{datos['emisor']['ruc']}{datos['emisor']['dv']}</dRucEm>" in xml_content),
            ('Moneda extranjera', datos['totales']
             ['codigo_moneda'] in xml_content),
            ('Tipo cambio', str(datos['totales']
             ['tipo_cambio']) in xml_content),
            ('Códigos NCM', any(item.get('codigo_ncm', '')
             in xml_content for item in datos['items'])),
            ('País origen', any(item.get('codigo_pais_origen', '')
             in xml_content for item in datos['items']))
        ]

        for nombre, resultado in validaciones:
            status = "✅" if resultado else "❌"
            print(f"   {status} {nombre}")

        # 8. Mostrar XML completo
        print(f"\n📄 XML AFE GENERADO COMPLETO:")
        print("=" * 80)

        for i, line in enumerate(lines, 1):
            print(f"{i:3d}: {line}")

        print("=" * 80)

        # 9. Mostrar resumen de datos AFE
        print(f"\n📋 RESUMEN DE DATOS AFE:")
        print(f"   - CDC AFE: {datos['cdc']}")
        print(f"   - Fecha AFE: {datos['fecha_emision']}")
        print(f"   - Tipo: Importación de vendedor extranjero")
        print(
            f"   - Importador: {datos['emisor']['razon_social']} (RUC: {datos['emisor']['ruc']}-{datos['emisor']['dv']})")
        print(f"   - Vendedor: {datos['vendedor']['nombre_vendedor']}")
        print(
            f"   - País vendedor: Según pasaporte {datos['vendedor']['numero_documento_vendedor']}")
        print(f"   - Items importados: {len(datos['items'])}")
        print(
            f"   - Total USD: ${datos['totales']['total_moneda_extranjera']:,}")
        print(f"   - Total PYG: Gs. {datos['totales']['total_general']:,}")
        print(f"   - Tipo cambio: {datos['totales']['tipo_cambio']} PYG/USD")

        # 10. Análisis específico AFE
        print(f"\n🎯 ANÁLISIS ESPECÍFICO AFE:")
        print(
            f"   - Es importación: {'✅' if datos['vendedor']['naturaleza_vendedor'] == '2' else '❌'}")
        print(
            f"   - Emisor = Receptor: {'✅' if datos['emisor']['ruc'] == datos['receptor']['numero_documento'] else '❌'}")
        print(
            f"   - Vendedor extranjero: {'✅' if datos['vendedor']['tipo_documento_vendedor'] == '2' else '❌'}")
        print(
            f"   - Moneda extranjera: {'✅' if 'codigo_moneda' in datos['totales'] else '❌'}")
        print(
            f"   - Códigos NCM: {'✅' if any('codigo_ncm' in item for item in datos['items']) else '❌'}")
        print(
            f"   - Ubicación completa: {'✅' if datos['vendedor']['codigo_departamento_vendedor'] else '❌'}")

        # 11. Mostrar items detallados
        print(f"\n📦 ITEMS IMPORTADOS:")
        for i, item in enumerate(datos['items'], 1):
            print(f"   {i}. {item['descripcion']}")
            print(f"      - Cantidad: {item['cantidad']}")
            print(f"      - Precio USD: ${item['precio_unitario']}")
            if 'codigo_ncm' in item:
                print(f"      - NCM: {item['codigo_ncm']}")
            if 'codigo_pais_origen' in item:
                print(
                    f"      - Origen: {item['descripcion_pais_origen']} ({item['codigo_pais_origen']})")

        return True, xml_content

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


def mostrar_comparacion_fe_vs_afe():
    """Mostrar diferencias clave entre FE y AFE"""
    print(f"\n📊 COMPARACIÓN: FACTURA vs AUTOFACTURA")
    print("=" * 60)

    comparacion = [
        ("Tipo documento", "FE: iTipDE = 1", "AFE: iTipDE = 4"),
        ("Emisor/Receptor", "FE: Diferentes", "AFE: Mismo RUC"),
        ("Casos uso", "FE: Ventas normales", "AFE: Importaciones"),
        ("Vendedor", "FE: Emisor vende", "AFE: Tercero vende"),
        ("Campos específicos", "FE: gCamFE", "AFE: gCamAE"),
        ("Datos vendedor", "FE: No aplica", "AFE: Obligatorio"),
        ("Ubicación geo", "FE: Opcional", "AFE: Obligatoria"),
        ("Moneda extranjera", "FE: Opcional", "AFE: Común"),
        ("Códigos NCM", "FE: Opcional", "AFE: Recomendado"),
        ("Complejidad", "FE: Baja", "AFE: Alta")
    ]

    for aspecto, fe, afe in comparacion:
        print(f"   {aspecto:17} | {fe:20} | {afe}")


if __name__ == "__main__":
    # Ejecutar test AFE
    success, result = test_generar_xml_afe()

    print(f"\n🎯 RESULTADO FINAL AFE:")
    if success:
        print("✅ XML AFE GENERADO EXITOSAMENTE")
        print("💡 Archivo guardado: autofactura_electronica_generada.xml")
        print("💡 Puedes abrir el archivo para ver el XML completo")

        # Mostrar comparación
        mostrar_comparacion_fe_vs_afe()

    else:
        print(f"❌ ERROR EN GENERACIÓN AFE: {result}")

    print(f"\n📝 PRÓXIMOS PASOS AFE:")
    print("   1. Revisar el XML AFE generado")
    print("   2. Validar estructura gCamAE (datos vendedor)")
    print("   3. Verificar emisor = receptor (mismo RUC)")
    print("   4. Validar códigos NCM para importaciones")
    print("   5. Verificar tipo cambio y moneda extranjera")
    print("   6. Validar ubicaciones geográficas completas")
    print("   7. Integrar con sistema de importaciones")
    print("   8. Probar validaciones SIFEN contra XSD")
