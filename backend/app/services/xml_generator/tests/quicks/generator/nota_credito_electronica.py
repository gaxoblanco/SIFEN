#!/usr/bin/env python3
"""
Test simple para generar XML de Nota de Crédito Electrónica (NCE)
Muestra el resultado completo generado usando template modular
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


def crear_template_nce_modular():
    """
    Crear el template nota_credito_electronica.xml modular para testing
    Simula la versión modular que usa partials
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd"
     version="1.5.0"
     Id="{{ cdc }}">

    <dVerFor>{{ version | default('150') }}</dVerFor>
    
    <DE Id="{{ cdc }}">
        <!-- gOpeDE: Datos de la operación (desde _grupo_operacion.xml) -->
        <gOpeDE>
            <iTipDE>5</iTipDE>
            <dDesTipDE>Nota de crédito electrónica</dDesTipDE>
            <dFecEmiDE>{{ fecha_emision }}</dFecEmiDE>
        </gOpeDE>

        <!-- gTimb: Datos del timbrado (desde _grupo_timbrado.xml) -->
        <gTimb>
            <iTiTim>{{ timbrado.tipo | default(1) }}</iTiTim>
            <dDesTiTim>{{ timbrado.descripcion_tipo | default("Timbrado electrónico SET") }}</dDesTiTim>
            <dNumTim>{{ timbrado.numero_timbrado }}</dNumTim>
            <dEst>{{ timbrado.establecimiento }}</dEst>
            <dPunExp>{{ timbrado.punto_expedicion }}</dPunExp>
            <dNumDoc>{{ timbrado.numero_documento }}</dNumDoc>
        </gTimb>

        <!-- gDatGralOpe: Datos generales (desde _grupo_datos_generales.xml) -->
        <gDatGralOpe>
            <dFeEmiDE>{{ fecha_emision }}</dFeEmiDE>
            <iTipEmi>{{ tipo_emision | default(1) }}</iTipEmi>
            <dDesTipEmi>{{ descripcion_tipo_emision | default("Normal") }}</dDesTipEmi>
        </gDatGralOpe>

        <!-- gDocAso: Documento asociado (desde _documento_asociado.xml) - OBLIGATORIO NCE -->
        <gDocAso>
            <iTipDocAso>{{ documento_asociado.tipo_documento_ref }}</iTipDocAso>
            <dDesTipDocAso>{{ documento_asociado.descripcion_tipo_ref }}</dDesTipDocAso>
            <dCDCREf>{{ documento_asociado.cdc_ref }}</dCDCREf>
            <dNTimDI>{{ documento_asociado.numero_timbrado_ref }}</dNTimDI>
            <dEstDI>{{ documento_asociado.establecimiento_ref }}</dEstDI>
            <dPunExpDI>{{ documento_asociado.punto_expedicion_ref }}</dPunExpDI>
            <dNumDocDI>{{ documento_asociado.numero_documento_ref }}</dNumDocDI>
            <dFeEmiDI>{{ documento_asociado.fecha_documento_ref }}</dFeEmiDI>
        </gDocAso>

        <!-- gDtipDE: Campos específicos Nota de Crédito -->
        <gDtipDE>
            <gCamNCE>
                <iMotEmi>{{ datos_nce.motivo_emision }}</iMotEmi>
                <dDesMotEmi>{{ datos_nce.descripcion_motivo }}</dDesMotEmi>
                {% if datos_nce.observaciones_motivo %}
                <dObsNCE>{{ datos_nce.observaciones_motivo }}</dObsNCE>
                {% endif %}
                {% if datos_nce.usuario_responsable %}
                <dUsResp>{{ datos_nce.usuario_responsable }}</dUsResp>
                {% endif %}
            </gCamNCE>
        </gDtipDE>

        <!-- gEmis: Datos del emisor (desde _grupo_emisor.xml) -->
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

        <!-- gDatRec: Datos del receptor (desde _grupo_receptor.xml) -->
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

        <!-- gCamItem: Items devueltos (desde _grupo_items.xml) -->
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

        <!-- gTotSub: Totales (desde _grupo_totales.xml) -->
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

        <!-- gCamGen: Condiciones (desde _grupo_condiciones.xml) -->
        {% if condiciones %}
        <gCamGen>
            {% if condiciones.modalidad_venta %}
            <iFormCancPag>{{ condiciones.modalidad_venta }}</iFormCancPag>
            {% endif %}
            {% if condiciones.descripcion_modalidad %}
            <dDesFormCancPag>{{ condiciones.descripcion_modalidad }}</dDesFormCancPag>
            {% endif %}
        </gCamGen>
        {% endif %}
    </DE>
</rDE>'''


def crear_datos_nce_prueba():
    """Crear datos de prueba completos para NCE"""
    print("📝 Creando datos de prueba NCE...")

    # Generar CDC simulado de 44 caracteres para NCE
    cdc_nce = "01800695631001001000000612025063014500000002"  # NCE
    cdc_original = "01800695631001001000000612025063014100000001"  # FE original

    datos = {
        # Identificación NCE
        'cdc': cdc_nce,
        'fecha_emision': "2025-06-30T15:45:00",

        # Documento asociado (OBLIGATORIO para NCE)
        'documento_asociado': {
            'tipo_documento_ref': '1',  # Factura Electrónica
            'descripcion_tipo_ref': 'Factura electrónica',
            'cdc_ref': cdc_original,
            'numero_timbrado_ref': "12345678",
            'establecimiento_ref': "001",
            'punto_expedicion_ref': "001",
            'numero_documento_ref': "0000001",
            'fecha_documento_ref': "2025-06-30T10:30:00"  # Anterior a NCE
        },

        # Específicos NCE
        'datos_nce': {
            'motivo_emision': 1,  # 1=Devolución
            'descripcion_motivo': 'Devolución de mercadería defectuosa',
            'observaciones_motivo': 'Cliente reportó falla en producto, lote #789. Autorizado por gerencia.',
            'usuario_responsable': 'user_devoluciones_01'
        },

        # Timbrado NCE
        'timbrado': {
            'numero_timbrado': "12345678",
            'establecimiento': "001",
            'punto_expedicion': "001",
            'numero_documento': "0000002",  # Siguiente número
            'tipo': 1,
            'descripcion_tipo': "Timbrado electrónico SET"
        },

        # Emisor (mismo que factura original)
        'emisor': {
            'ruc': "80016875",
            'dv': "4",
            'razon_social': "EMPRESA DEMO S.A.",
            'direccion': "Av. España 1234, Asunción",
            'telefono': "+595 21 123456",
            'email': "devoluciones@empresademo.com.py"
        },

        # Receptor (mismo que factura original)
        'receptor': {
            'naturaleza': 1,
            'descripcion_naturaleza': "No contribuyente",
            'tipo_documento': 1,
            'numero_documento': "12345678",
            'razon_social': "JUAN PÉREZ",
            'direccion': "Calle Demo 567, Asunción"
        },

        # Items devueltos (cantidades/montos NEGATIVOS)
        'items': [
            {
                'codigo_interno': "PROD001",
                'descripcion': "Producto Demo Defectuoso - DEVOLUCIÓN",
                'cantidad': Decimal("-1.000"),  # ⚠️ NEGATIVO
                'descripcion_unidad_medida': "Unidad",
                'precio_unitario': Decimal("-50000"),  # ⚠️ NEGATIVO
                'total_operacion': Decimal("-50000"),  # ⚠️ NEGATIVO
                'afectacion_iva': 1,
                'descripcion_afectacion_iva': "Gravado IVA 10%",
                'tasa_iva': Decimal("10.00"),
                'base_gravable': Decimal("-50000"),  # ⚠️ NEGATIVO
                'liquidacion_iva': Decimal("-5000")  # ⚠️ NEGATIVO
            }
        ],

        # Totales (NEGATIVOS - reducen deuda del cliente)
        'totales': {
            'subtotal_gravado': Decimal("-50000"),  # ⚠️ NEGATIVO
            'total_operacion': Decimal("-50000"),   # ⚠️ NEGATIVO
            'total_iva': Decimal("-5000"),          # ⚠️ NEGATIVO
            'liquidacion_iva_10': Decimal("-5000"),  # ⚠️ NEGATIVO
            'total_general': Decimal("-55000")      # ⚠️ NEGATIVO
        },

        # Condiciones (reembolso)
        'condiciones': {
            'modalidad_venta': 4,  # Devolución
            'descripcion_modalidad': "Devolución - Reembolso efectivo"
        }
    }

    print("✅ Datos de prueba NCE creados")
    return datos


def validar_nce_datos(datos):
    """Validaciones específicas para NCE"""
    print("🔍 Validando datos NCE...")

    errores = []

    # 1. Documento asociado obligatorio
    if 'documento_asociado' not in datos:
        errores.append("NCE requiere documento_asociado")

    # 2. CDC documento original
    if len(datos['documento_asociado']['cdc_ref']) != 44:
        errores.append("CDC documento original debe tener 44 caracteres")

    # 3. Motivo válido
    if datos['datos_nce']['motivo_emision'] not in [1, 2, 3, 4, 5, 6]:
        errores.append("Motivo emisión debe estar entre 1-6")

    # 4. Montos negativos típicos
    if datos['totales']['total_general'] > 0:
        print("⚠️ ADVERTENCIA: Total general positivo (inusual para NCE)")

    # 5. Fecha documento original anterior
    fecha_original = datetime.fromisoformat(
        datos['documento_asociado']['fecha_documento_ref'].replace('Z', '+00:00'))
    fecha_nce = datetime.fromisoformat(
        datos['fecha_emision'].replace('Z', '+00:00'))
    if fecha_original >= fecha_nce:
        errores.append("Documento original debe ser anterior a NCE")

    if errores:
        print("❌ Errores de validación:")
        for error in errores:
            print(f"   - {error}")
        return False

    print("✅ Validaciones NCE pasadas")
    return True


def test_generar_xml_nce():
    """Test principal para generar XML NCE"""
    print("🚀 GENERANDO XML DE NOTA DE CRÉDITO ELECTRÓNICA (NCE)")
    print("=" * 70)

    try:
        # 1. Crear template
        print("🔧 Creando template NCE modular...")
        template_content = crear_template_nce_modular()
        template = Template(template_content)
        print("✅ Template NCE creado")

        # 2. Crear datos
        datos = crear_datos_nce_prueba()

        # 3. Validar datos NCE
        if not validar_nce_datos(datos):
            return False, "Validación de datos falló"

        # 4. Renderizar
        print("⚙️ Renderizando XML NCE...")
        xml_content = template.render(**datos)
        print("✅ XML NCE renderizado exitosamente")

        # 5. Guardar archivo
        output_file = "nota_credito_electronica_generada.xml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"💾 XML guardado en: {output_file}")

        # 6. Mostrar estadísticas
        lines = xml_content.split('\n')
        print(f"\n📊 ESTADÍSTICAS NCE:")
        print(f"   - Tamaño: {len(xml_content):,} caracteres")
        print(f"   - Líneas: {len(lines):,}")
        print(f"   - Elementos XML: {xml_content.count('<'):,}")

        # 7. Validaciones específicas NCE
        print(f"\n🔍 VALIDACIONES BÁSICAS NCE:")

        validaciones = [
            ('Declaración XML', '<?xml version="1.0"' in xml_content),
            ('Namespace SIFEN', 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml_content),
            ('CDC NCE presente', datos['cdc'] in xml_content),
            ('Tipo documento NCE', '<iTipDE>5</iTipDE>' in xml_content),
            ('Documento asociado', '<gDocAso>' in xml_content),
            ('CDC documento original',
             datos['documento_asociado']['cdc_ref'] in xml_content),
            ('Motivo crédito',
             f"<iMotEmi>{datos['datos_nce']['motivo_emision']}</iMotEmi>" in xml_content),
            ('Descripción motivo', datos['datos_nce']
             ['descripcion_motivo'] in xml_content),
            ('RUC emisor',
             f"<dRucEm>{datos['emisor']['ruc']}{datos['emisor']['dv']}</dRucEm>" in xml_content),
            ('Totales negativos', str(
                datos['totales']['total_general']) in xml_content),
            ('Específicos NCE', '<gCamNCE>' in xml_content)
        ]

        for nombre, resultado in validaciones:
            status = "✅" if resultado else "❌"
            print(f"   {status} {nombre}")

        # 8. Mostrar XML completo
        print(f"\n📄 XML NCE GENERADO COMPLETO:")
        print("=" * 80)

        for i, line in enumerate(lines, 1):
            print(f"{i:3d}: {line}")

        print("=" * 80)

        # 9. Mostrar resumen de datos NCE
        print(f"\n📋 RESUMEN DE DATOS NCE:")
        print(f"   - CDC NCE: {datos['cdc']}")
        print(f"   - Fecha NCE: {datos['fecha_emision']}")
        print(f"   - CDC Original: {datos['documento_asociado']['cdc_ref']}")
        print(
            f"   - Fecha Original: {datos['documento_asociado']['fecha_documento_ref']}")
        print(
            f"   - Tipo Doc Original: {datos['documento_asociado']['descripcion_tipo_ref']}")
        print(f"   - Motivo: {datos['datos_nce']['descripcion_motivo']}")
        print(
            f"   - Emisor: {datos['emisor']['razon_social']} (RUC: {datos['emisor']['ruc']}-{datos['emisor']['dv']})")
        print(f"   - Receptor: {datos['receptor']['razon_social']}")
        print(f"   - Items devueltos: {len(datos['items'])}")
        print(
            f"   - Total crédito: Gs. {datos['totales']['total_general']:,} (negativo)")
        print(
            f"   - Observaciones: {datos['datos_nce']['observaciones_motivo']}")

        # 10. Análisis específico NCE
        print(f"\n🎯 ANÁLISIS ESPECÍFICO NCE:")
        print(
            f"   - Es devolución: {'✅' if datos['datos_nce']['motivo_emision'] == 1 else '❌'}")
        print(
            f"   - Montos negativos: {'✅' if datos['totales']['total_general'] < 0 else '❌'}")
        print(
            f"   - Documento referenciado: {'✅' if datos['documento_asociado']['cdc_ref'] else '❌'}")
        print(
            f"   - Reduce deuda cliente: {'✅' if datos['totales']['total_general'] < 0 else '❌'}")

        return True, xml_content

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


def mostrar_comparacion_fe_vs_nce():
    """Mostrar diferencias clave entre FE y NCE"""
    print(f"\n📊 COMPARACIÓN: FACTURA vs NOTA CRÉDITO")
    print("=" * 60)

    comparacion = [
        ("Tipo documento", "FE: iTipDE = 1", "NCE: iTipDE = 5"),
        ("Propósito", "FE: Venta original", "NCE: Devolución/crédito"),
        ("Doc. asociado", "FE: No requiere", "NCE: OBLIGATORIO"),
        ("Montos", "FE: Positivos", "NCE: Típicamente negativos"),
        ("Efecto deuda", "FE: Aumenta deuda", "NCE: Reduce deuda"),
        ("Motivo específico", "FE: No aplica", "NCE: Obligatorio (1-6)"),
        ("Template", "FE: gCamFE", "NCE: gCamNCE + gDocAso"),
        ("Uso típico", "FE: Ventas diarias", "NCE: Devoluciones/ajustes")
    ]

    for aspecto, fe, nce in comparacion:
        print(f"   {aspecto:15} | {fe:20} | {nce}")


if __name__ == "__main__":
    # Ejecutar test NCE
    success, result = test_generar_xml_nce()

    print(f"\n🎯 RESULTADO FINAL NCE:")
    if success:
        print("✅ XML NCE GENERADO EXITOSAMENTE")
        print("💡 Archivo guardado: nota_credito_electronica_generada.xml")
        print("💡 Puedes abrir el archivo para ver el XML completo")

        # Mostrar comparación
        mostrar_comparacion_fe_vs_nce()

    else:
        print(f"❌ ERROR EN GENERACIÓN NCE: {result}")
