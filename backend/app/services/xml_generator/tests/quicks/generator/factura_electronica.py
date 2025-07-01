#!/usr/bin/env python3
"""
Test simple para generar XML de factura electrónica
Muestra el resultado completo generado
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, Template


def setup_paths():
    """Configurar paths para encontrar el proyecto"""
    current_dir = Path(__file__).parent.absolute()

    # Buscar la carpeta backend o app
    search_path = current_dir
    for _ in range(10):
        if (search_path / "app").exists():
            return search_path
        elif (search_path / "backend").exists():
            return search_path / "backend"
        search_path = search_path.parent

    raise Exception("No se encontró la estructura del proyecto")


def crear_template_inline():
    """
    Crear el template factura_electronica.xml inline para testing
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd"
     version="1.5.0"
     Id="{{ cdc }}">

    <dVerFor>{{ version | default('150') }}</dVerFor>
    
    <DE Id="{{ cdc }}">
        <!-- gOpeDE: Datos de la operación -->
        <gOpeDE>
            <iTipDE>1</iTipDE>
            <dDesTipDE>Factura electrónica</dDesTipDE>
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

        <!-- gEmis: Datos del emisor -->
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

        <!-- gDatRec: Datos del receptor -->
        <gDatRec>
            <iNatRec>{{ receptor.naturaleza | default(1) }}</iNatRec>
            <dDesNatRec>{{ receptor.descripcion_naturaleza | default("No contribuyente") }}</dDesNatRec>
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
        </gTotSub>

        <!-- gDtipDE: Campos específicos Factura Electrónica -->
        <gDtipDE>
            <gCamFE>
                <iIndPres>{{ indicador_presencia | default(1) }}</iIndPres>
                <dDesIndPres>{{ descripcion_presencia | default("Operación presencial") }}</dDesIndPres>
                {% if indicador_entrega %}
                <iIndRec>{{ indicador_entrega }}</iIndRec>
                {% endif %}
                {% if descripcion_entrega %}
                <dDesIndRec>{{ descripcion_entrega }}</dDesIndRec>
                {% endif %}
            </gCamFE>
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


def crear_datos_prueba():
    """Crear datos de prueba completos"""
    print("📝 Creando datos de prueba...")

    # Generar CDC simulado de 44 caracteres
    cdc = "01800695631001001000000612025063014300000001"

    datos = {
        # Identificación
        'cdc': cdc,
        'fecha_emision': "2025-06-30T14:30:00",

        # Timbrado
        'timbrado': {
            'numero_timbrado': "12345678",
            'establecimiento': "001",
            'punto_expedicion': "001",
            'numero_documento': "0000001",
            'tipo': 1,
            'descripcion_tipo': "Timbrado electrónico SET"
        },

        # Emisor
        'emisor': {
            'ruc': "80016875",
            'dv': "4",
            'razon_social': "EMPRESA DEMO S.A.",
            'direccion': "Av. España 1234, Asunción",
            'telefono': "+595 21 123456",
            'email': "factura@empresademo.com.py"
        },

        # Receptor
        'receptor': {
            'naturaleza': 1,
            'descripcion_naturaleza': "No contribuyente",
            'tipo_documento': 1,
            'numero_documento': "12345678",
            'razon_social': "JUAN PÉREZ",
            'direccion': "Calle Demo 567, Asunción"
        },

        # Items
        'items': [
            {
                'codigo_interno': "PROD001",
                'descripcion': "Producto Demo Gravado IVA 10%",
                'cantidad': Decimal("2.000"),
                'descripcion_unidad_medida': "Unidad",
                'precio_unitario': Decimal("50000"),
                'total_operacion': Decimal("100000"),
                'afectacion_iva': 1,
                'descripcion_afectacion_iva': "Gravado IVA 10%",
                'tasa_iva': Decimal("10.00"),
                'base_gravable': Decimal("100000"),
                'liquidacion_iva': Decimal("10000")
            },
            {
                'codigo_interno': "SERV001",
                'descripcion': "Servicio Profesional",
                'cantidad': Decimal("1.000"),
                'descripcion_unidad_medida': "Servicio",
                'precio_unitario': Decimal("150000"),
                'total_operacion': Decimal("150000"),
                'afectacion_iva': 1,
                'descripcion_afectacion_iva': "Gravado IVA 10%",
                'tasa_iva': Decimal("10.00"),
                'base_gravable': Decimal("150000"),
                'liquidacion_iva': Decimal("15000")
            }
        ],

        # Totales
        'totales': {
            'subtotal_gravado': Decimal("250000"),
            'total_operacion': Decimal("250000"),
            'total_iva': Decimal("25000"),
            'liquidacion_iva_10': Decimal("25000"),
            'total_general': Decimal("275000")
        },

        # Específicos FE
        'indicador_presencia': 1,
        'descripcion_presencia': "Operación presencial",

        # Condiciones
        'condiciones': {
            'modalidad_venta': 1,
            'descripcion_modalidad': "Contado",
            'pagos_contado': [
                {
                    'modalidad': 1,
                    'descripcion': "Efectivo",
                    'monto': Decimal("275000")
                }
            ]
        }
    }

    print("✅ Datos de prueba creados")
    return datos


def test_generar_xml():
    """Test principal para generar XML"""
    print("🚀 GENERANDO XML DE FACTURA ELECTRÓNICA")
    print("=" * 60)

    try:
        # 1. Crear template
        print("🔧 Creando template...")
        template_content = crear_template_inline()
        template = Template(template_content)
        print("✅ Template creado")

        # 2. Crear datos
        datos = crear_datos_prueba()

        # 3. Renderizar
        print("⚙️ Renderizando XML...")
        xml_content = template.render(**datos)
        print("✅ XML renderizado exitosamente")

        # 4. Guardar archivo
        output_file = "factura_electronica_generada.xml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"💾 XML guardado en: {output_file}")

        # 5. Mostrar estadísticas
        lines = xml_content.split('\n')
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   - Tamaño: {len(xml_content):,} caracteres")
        print(f"   - Líneas: {len(lines):,}")
        print(f"   - Elementos XML: {xml_content.count('<'):,}")

        # 6. Validaciones básicas
        print(f"\n🔍 VALIDACIONES BÁSICAS:")

        validaciones = [
            ('Declaración XML', '<?xml version="1.0"' in xml_content),
            ('Namespace SIFEN', 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml_content),
            ('CDC presente', datos['cdc'] in xml_content),
            ('Tipo documento FE', '<iTipDE>1</iTipDE>' in xml_content),
            ('RUC emisor',
             f"<dRucEm>{datos['emisor']['ruc']}{datos['emisor']['dv']}</dRucEm>" in xml_content),
            ('Nombre receptor',
             f"<dNomRec>{datos['receptor']['razon_social']}</dNomRec>" in xml_content),
            ('Items presentes', '<gCamItem>' in xml_content),
            ('Total general',
             f"<dTotGralOpe>{datos['totales']['total_general']}</dTotGralOpe>" in xml_content),
            ('Específicos FE', '<gCamFE>' in xml_content)
        ]

        for nombre, resultado in validaciones:
            status = "✅" if resultado else "❌"
            print(f"   {status} {nombre}")

        # 7. Mostrar XML completo
        print(f"\n📄 XML GENERADO COMPLETO:")
        print("=" * 80)

        for i, line in enumerate(lines, 1):
            print(f"{i:3d}: {line}")

        print("=" * 80)

        # 8. Mostrar resumen de datos
        print(f"\n📋 RESUMEN DE DATOS:")
        print(f"   - CDC: {datos['cdc']}")
        print(f"   - Fecha: {datos['fecha_emision']}")
        print(f"   - Timbrado: {datos['timbrado']['numero_timbrado']}")
        print(
            f"   - Documento: {datos['timbrado']['establecimiento']}-{datos['timbrado']['punto_expedicion']}-{datos['timbrado']['numero_documento']}")
        print(
            f"   - Emisor: {datos['emisor']['razon_social']} (RUC: {datos['emisor']['ruc']}-{datos['emisor']['dv']})")
        print(f"   - Receptor: {datos['receptor']['razon_social']}")
        print(f"   - Items: {len(datos['items'])}")
        print(f"   - Total: Gs. {datos['totales']['total_general']:,}")

        return True, xml_content

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


if __name__ == "__main__":
    # Ejecutar test
    success, result = test_generar_xml()

    print(f"\n🎯 RESULTADO FINAL:")
    if success:
        print("✅ XML GENERADO EXITOSAMENTE")
        print("💡 Archivo guardado: factura_electronica_generada.xml")
        print("💡 Puedes abrir el archivo para ver el XML completo")
    else:
        print(f"❌ ERROR EN GENERACIÓN: {result}")

    print(f"\n📝 PRÓXIMOS PASOS:")
    print("   1. Revisar el XML generado")
    print("   2. Validar contra XSD si está disponible")
    print("   3. Integrar con XMLGenerator existente")
    print("   4. Crear partials reutilizables")
