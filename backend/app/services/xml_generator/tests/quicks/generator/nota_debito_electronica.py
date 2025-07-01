#!/usr/bin/env python3
"""
Test específico para el template nota_debito_electronica.xml
Valida la generación XML para NDE (Tipo 6)
Muestra el resultado completo generado usando template modular
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from jinja2 import Template


def crear_template_nde_modular():
    """
    Crear el template nota_debito_electronica.xml modular para testing
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
            <iTipDE>6</iTipDE>
            <dDesTipDE>Nota de débito electrónica</dDesTipDE>
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

        <!-- gDocAso: Documento asociado (desde _documento_asociado.xml) - OBLIGATORIO NDE -->
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

        <!-- gDtipDE: Campos específicos Nota de Débito -->
        <gDtipDE>
            <gCamNDE>
                <iMotEmi>{{ datos_nde.motivo_emision }}</iMotEmi>
                <dDesMotEmi>{{ datos_nde.descripcion_motivo }}</dDesMotEmi>
                {% if datos_nde.observaciones_motivo %}
                <dObsNDE>{{ datos_nde.observaciones_motivo }}</dObsNDE>
                {% endif %}
                {% if datos_nde.usuario_responsable %}
                <dUsResp>{{ datos_nde.usuario_responsable }}</dUsResp>
                {% endif %}
                {% if datos_nde.informacion_trazabilidad %}
                <dInfoTraz>{{ datos_nde.informacion_trazabilidad }}</dInfoTraz>
                {% endif %}
                {% if datos_nde.fecha_vencimiento_cargo %}
                <dFecVencCargo>{{ datos_nde.fecha_vencimiento_cargo }}</dFecVencCargo>
                {% endif %}
                {% if datos_nde.tipo_cargo %}
                <iTipCargo>{{ datos_nde.tipo_cargo }}</iTipCargo>
                {% endif %}
                {% if datos_nde.descripcion_tipo_cargo %}
                <dDesTipCargo>{{ datos_nde.descripcion_tipo_cargo }}</dDesTipCargo>
                {% endif %}
            </gCamNDE>
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

        <!-- gCamItem: Items con cargos adicionales (desde _grupo_items.xml) -->
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


def crear_datos_nde_prueba():
    """Crear datos de prueba completos para NDE - Intereses por pago tardío"""
    print("📝 Creando datos de prueba NDE...")

    # Generar CDC simulado de 44 caracteres para NDE
    cdc_nde = "01800695631001001000000612025063014600000003"  # NDE
    cdc_original = "01800695631001001000000612025063014100000001"  # FE original

    datos = {
        # Identificación NDE
        'cdc': cdc_nde,
        'fecha_emision': "2025-07-30T16:20:00",

        # Documento asociado (OBLIGATORIO para NDE)
        'documento_asociado': {
            'tipo_documento_ref': '1',  # Factura Electrónica
            'descripcion_tipo_ref': 'Factura electrónica',
            'cdc_ref': cdc_original,
            'numero_timbrado_ref': "12345678",
            'establecimiento_ref': "001",
            'punto_expedicion_ref': "001",
            'numero_documento_ref': "0000001",
            'fecha_documento_ref': "2025-06-30T10:30:00"  # 30 días antes que NDE
        },

        # Específicos NDE
        'datos_nde': {
            'motivo_emision': 1,  # 1=Intereses
            'descripcion_motivo': 'Intereses por pago tardío',
            'observaciones_motivo': 'Factura vencida hace 30 días. Tasa aplicada: 2% mensual según contrato comercial. Cliente notificado múltiples veces.',
            'usuario_responsable': 'user_cobranzas_01',
            'informacion_trazabilidad': 'NDE generada automáticamente por sistema cobranzas tras vencimiento',
            'fecha_vencimiento_cargo': '2025-08-30T23:59:59',
            'tipo_cargo': 1,  # 1=Financiero
            'descripcion_tipo_cargo': 'Cargo financiero por mora'
        },

        # Timbrado NDE
        'timbrado': {
            'numero_timbrado': "12345678",
            'establecimiento': "001",
            'punto_expedicion': "001",
            'numero_documento': "0000003",  # Siguiente número
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
            'email': "cobranzas@empresademo.com.py"
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

        # Items con cargos adicionales (cantidades/montos POSITIVOS)
        'items': [
            {
                'codigo_interno': "INT001",
                'descripcion': "Intereses por pago tardío - 30 días",
                'cantidad': Decimal("1.000"),  # ✅ POSITIVO
                'descripcion_unidad_medida': "Servicio",
                # ✅ POSITIVO (2% de Gs. 5,500,000)
                'precio_unitario': Decimal("110000"),
                'total_operacion': Decimal("110000"),  # ✅ POSITIVO
                'afectacion_iva': 1,
                'descripcion_afectacion_iva': "Gravado IVA 10%",
                'tasa_iva': Decimal("10.00"),
                'base_gravable': Decimal("110000"),  # ✅ POSITIVO
                'liquidacion_iva': Decimal("11000")  # ✅ POSITIVO
            },
            {
                'codigo_interno': "ADM001",
                'descripcion': "Gastos administrativos de cobranza",
                'cantidad': Decimal("1.000"),  # ✅ POSITIVO
                'descripcion_unidad_medida': "Servicio",
                'precio_unitario': Decimal("50000"),  # ✅ POSITIVO
                'total_operacion': Decimal("50000"),  # ✅ POSITIVO
                'afectacion_iva': 1,
                'descripcion_afectacion_iva': "Gravado IVA 10%",
                'tasa_iva': Decimal("10.00"),
                'base_gravable': Decimal("50000"),   # ✅ POSITIVO
                'liquidacion_iva': Decimal("5000")   # ✅ POSITIVO
            }
        ],

        # Totales (POSITIVOS - aumentan deuda del cliente)
        'totales': {
            'subtotal_gravado': Decimal("160000"),  # ✅ POSITIVO
            'total_operacion': Decimal("160000"),   # ✅ POSITIVO
            'total_iva': Decimal("16000"),          # ✅ POSITIVO
            'liquidacion_iva_10': Decimal("16000"),  # ✅ POSITIVO
            'total_general': Decimal("176000")      # ✅ POSITIVO
        },

        # Condiciones (pago del cargo)
        'condiciones': {
            'modalidad_venta': 2,  # Crédito
            'descripcion_modalidad': "Crédito - Pago de intereses"
        }
    }

    print("✅ Datos de prueba NDE creados")
    return datos


def validar_nde_datos(datos):
    """Validaciones específicas para NDE"""
    print("🔍 Validando datos NDE...")

    errores = []

    # 1. Documento asociado obligatorio
    if 'documento_asociado' not in datos:
        errores.append("NDE requiere documento_asociado")

    # 2. CDC documento original
    if len(datos['documento_asociado']['cdc_ref']) != 44:
        errores.append("CDC documento original debe tener 44 caracteres")

    # 3. Motivo válido
    if datos['datos_nde']['motivo_emision'] not in [1, 2, 3, 4, 5, 6]:
        errores.append("Motivo emisión debe estar entre 1-6")

    # 4. Montos positivos típicos
    if datos['totales']['total_general'] <= 0:
        print("⚠️ ADVERTENCIA: Total general no positivo (inusual para NDE)")

    # 5. Fecha documento original anterior
    fecha_original = datetime.fromisoformat(
        datos['documento_asociado']['fecha_documento_ref'].replace('Z', '+00:00'))
    fecha_nde = datetime.fromisoformat(
        datos['fecha_emision'].replace('Z', '+00:00'))
    if fecha_original >= fecha_nde:
        errores.append("Documento original debe ser anterior a NDE")

    if errores:
        print("❌ Errores de validación:")
        for error in errores:
            print(f"   - {error}")
        return False

    print("✅ Validaciones NDE pasadas")
    return True


def mostrar_variables_nde(datos):
    """Mostrar todas las variables usadas en la generación NDE para validación fácil"""
    print(f"\n🔍 VALIDACIONES CON VARIABLES REALES:")
    print("=" * 60)
    print(f"   1. CDC NDE: {datos['cdc']}")
    print(f"   2. Tipo documento: iTipDE = 6 (NDE)")
    print(f"   3. CDC Original: {datos['documento_asociado']['cdc_ref']}")
    print(
        f"   4. Fecha Original: {datos['documento_asociado']['fecha_documento_ref']}")
    print(f"   5. Fecha NDE: {datos['fecha_emision']}")
    print(
        f"   6. Motivo emisión: {datos['datos_nde']['motivo_emision']} ({datos['datos_nde']['descripcion_motivo']})")
    print(
        f"   7. Tipo cargo: {datos['datos_nde']['tipo_cargo']} ({datos['datos_nde']['descripcion_tipo_cargo']})")
    print(f"   8. Observaciones: {datos['datos_nde']['observaciones_motivo']}")
    print(
        f"   9. Usuario responsable: {datos['datos_nde']['usuario_responsable']}")
    print(
        f"  10. Fecha vencimiento cargo: {datos['datos_nde']['fecha_vencimiento_cargo']}")
    print(
        f"  11. Emisor: {datos['emisor']['razon_social']} (RUC: {datos['emisor']['ruc']}-{datos['emisor']['dv']})")
    print(f"  12. Receptor: {datos['receptor']['razon_social']}")
    print(
        f"  13. Total cargos: Gs. {datos['totales']['total_general']:,} (positivo)")

    print(f"\n📦 ITEMS CON CARGOS:")
    for i, item in enumerate(datos['items'], 1):
        print(f"   Item {i}: {item['descripcion']}")
        print(f"      - Código interno: {item.get('codigo_interno', 'N/A')}")
        print(f"      - Cantidad: {item['cantidad']}")
        print(f"      - Precio unitario: Gs. {item['precio_unitario']:,}")
        print(f"      - Total: Gs. {item['total_operacion']:,}")
        print(
            f"      - IVA: {item['descripcion_afectacion_iva']} ({item['tasa_iva']}%)")
        print()

    print(f"\n💰 TOTALES DETALLADOS:")
    print(
        f"   - Subtotal gravado: Gs. {datos['totales']['subtotal_gravado']:,}")
    print(f"   - Total operación: Gs. {datos['totales']['total_operacion']:,}")
    print(f"   - Total IVA: Gs. {datos['totales']['total_iva']:,}")
    print(f"   - IVA 10%: Gs. {datos['totales']['liquidacion_iva_10']:,}")
    print(f"   - TOTAL GENERAL: Gs. {datos['totales']['total_general']:,}")

    print(f"\n🏢 DATOS EMPRESA:")
    print(f"   - RUC: {datos['emisor']['ruc']}-{datos['emisor']['dv']}")
    print(f"   - Razón Social: {datos['emisor']['razon_social']}")
    print(f"   - Dirección: {datos['emisor']['direccion']}")
    print(f"   - Teléfono: {datos['emisor']['telefono']}")
    print(f"   - Email: {datos['emisor']['email']}")

    print(f"\n📋 ANÁLISIS TIPO CARGO:")
    tipos_motivo = {
        1: "Intereses por mora",
        2: "Gastos adicionales",
        3: "Multas y penalizaciones",
        4: "Ajustes de precio",
        5: "Servicios adicionales",
        6: "Otros cargos"
    }
    tipos_cargo = {
        1: "Financiero",
        2: "Administrativo",
        3: "Operativo"
    }

    motivo = datos['datos_nde']['motivo_emision']
    tipo = datos['datos_nde']['tipo_cargo']
    print(f"   - Motivo: {tipos_motivo.get(motivo, 'Desconocido')}")
    print(f"   - Tipo cargo: {tipos_cargo.get(tipo, 'Desconocido')}")
    print(f"   - Efecto: AUMENTA deuda del cliente")
    print(f"   - Días transcurridos: ~30 días desde factura original")


def test_generar_xml_nde():
    """Test principal para generar XML NDE"""
    print("🚀 GENERANDO XML DE NOTA DE DÉBITO ELECTRÓNICA (NDE)")
    print("=" * 70)

    try:
        # 1. Crear template
        print("🔧 Creando template NDE modular...")
        template_content = crear_template_nde_modular()
        template = Template(template_content)
        print("✅ Template NDE creado")

        # 2. Crear datos
        datos = crear_datos_nde_prueba()

        # 3. Validar datos NDE
        if not validar_nde_datos(datos):
            return False, "Validación de datos falló"

        # 4. Renderizar
        print("⚙️ Renderizando XML NDE...")
        xml_content = template.render(**datos)
        print("✅ XML NDE renderizado exitosamente")

        # 5. Guardar archivo
        output_file = "nota_debito_electronica_generada.xml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"💾 XML guardado en: {output_file}")

        # 6. Mostrar estadísticas
        lines = xml_content.split('\n')
        print(f"\n📊 ESTADÍSTICAS NDE:")
        print(f"   - Tamaño: {len(xml_content):,} caracteres")
        print(f"   - Líneas: {len(lines):,}")
        print(f"   - Elementos XML: {xml_content.count('<'):,}")

        # 7. Validaciones específicas NDE
        print(f"\n🔍 VALIDACIONES BÁSICAS NDE:")

        validaciones = [
            ('Declaración XML', '<?xml version="1.0"' in xml_content),
            ('Namespace SIFEN', 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml_content),
            ('CDC NDE presente', datos['cdc'] in xml_content),
            ('Tipo documento NDE', '<iTipDE>6</iTipDE>' in xml_content),
            ('Documento asociado', '<gDocAso>' in xml_content),
            ('CDC documento original',
             datos['documento_asociado']['cdc_ref'] in xml_content),
            ('Motivo débito',
             f"<iMotEmi>{datos['datos_nde']['motivo_emision']}</iMotEmi>" in xml_content),
            ('Descripción motivo', datos['datos_nde']
             ['descripcion_motivo'] in xml_content),
            ('RUC emisor',
             f"<dRucEm>{datos['emisor']['ruc']}{datos['emisor']['dv']}</dRucEm>" in xml_content),
            ('Totales positivos', str(
                datos['totales']['total_general']) in xml_content),
            ('Específicos NDE', '<gCamNDE>' in xml_content),
            ('Tipo cargo',
             f"<iTipCargo>{datos['datos_nde']['tipo_cargo']}</iTipCargo>" in xml_content)
        ]

        for nombre, resultado in validaciones:
            status = "✅" if resultado else "❌"
            print(f"   {status} {nombre}")

        # 8. Mostrar XML completo
        print(f"\n📄 XML NDE GENERADO COMPLETO:")
        print("=" * 80)

        for i, line in enumerate(lines, 1):
            print(f"{i:3d}: {line}")

        print("=" * 80)

        # 9. Mostrar resumen de datos NDE
        print(f"\n📋 RESUMEN DE DATOS NDE:")
        print(f"   - CDC NDE: {datos['cdc']}")
        print(f"   - Fecha NDE: {datos['fecha_emision']}")
        print(f"   - CDC Original: {datos['documento_asociado']['cdc_ref']}")
        print(
            f"   - Fecha Original: {datos['documento_asociado']['fecha_documento_ref']}")
        print(
            f"   - Tipo Doc Original: {datos['documento_asociado']['descripcion_tipo_ref']}")
        print(f"   - Motivo: {datos['datos_nde']['descripcion_motivo']}")
        print(
            f"   - Emisor: {datos['emisor']['razon_social']} (RUC: {datos['emisor']['ruc']}-{datos['emisor']['dv']})")
        print(f"   - Receptor: {datos['receptor']['razon_social']}")
        print(f"   - Items con cargos: {len(datos['items'])}")
        print(
            f"   - Total cargos: Gs. {datos['totales']['total_general']:,} (positivo)")
        print(
            f"   - Observaciones: {datos['datos_nde']['observaciones_motivo']}")

        # 10. Análisis específico NDE
        print(f"\n🎯 ANÁLISIS ESPECÍFICO NDE:")
        print(
            f"   - Es cargo por intereses: {'✅' if datos['datos_nde']['motivo_emision'] == 1 else '❌'}")
        print(
            f"   - Montos positivos: {'✅' if datos['totales']['total_general'] > 0 else '❌'}")
        print(
            f"   - Documento referenciado: {'✅' if datos['documento_asociado']['cdc_ref'] else '❌'}")
        print(
            f"   - Aumenta deuda cliente: {'✅' if datos['totales']['total_general'] > 0 else '❌'}")
        print(
            f"   - Tipo cargo financiero: {'✅' if datos['datos_nde']['tipo_cargo'] == 1 else '❌'}")

        # 11. Mostrar todas las variables usadas para validación
        mostrar_variables_nde(datos)

        return True, xml_content

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


def mostrar_comparacion_ncg_vs_nde():
    """Mostrar diferencias clave entre NCE y NDE"""
    print(f"\n📊 COMPARACIÓN: NOTA CRÉDITO vs NOTA DÉBITO")
    print("=" * 60)

    comparacion = [
        ("Tipo documento", "NCE: iTipDE = 5", "NDE: iTipDE = 6"),
        ("Propósito", "NCE: Reduce deuda", "NDE: Aumenta deuda"),
        ("Doc. asociado", "NCE: OBLIGATORIO", "NDE: OBLIGATORIO"),
        ("Montos", "NCE: Negativos", "NDE: Positivos"),
        ("Efecto cliente", "NCE: Recibe crédito", "NDE: Debe pagar más"),
        ("Casos típicos", "NCE: Devoluciones", "NDE: Intereses/gastos"),
        ("Motivo específico", "NCE: Devolución (1-6)", "NDE: Intereses (1-6)"),
        ("Template", "NCE: gCamNCE", "NDE: gCamNDE"),
        ("Uso frecuencia", "NCE: Común", "NDE: Menos común"),
        ("Complejidad", "NCE: Media", "NDE: Media")
    ]

    for aspecto, nce, nde in comparacion:
        print(f"   {aspecto:15} | {nce:20} | {nde}")


if __name__ == "__main__":
    # Ejecutar test NDE
    success, result = test_generar_xml_nde()

    print(f"\n🎯 RESULTADO FINAL NDE:")
    if success:
        print("✅ XML NDE GENERADO EXITOSAMENTE")
        print("💡 Archivo guardado: nota_debito_electronica_generada.xml")
        print("💡 Puedes abrir el archivo para ver el XML completo")

        # Mostrar comparación
        mostrar_comparacion_ncg_vs_nde()

    else:
        print(f"❌ ERROR EN GENERACIÓN NDE: {result}")

    print(f"\n📝 PRÓXIMOS PASOS NDE:")
    print("   1. Revisar el XML NDE generado")
    print("   2. Validar estructura gCamNDE (campos específicos débito)")
    print("   3. Verificar documento asociado obligatorio")
    print("   4. Validar montos positivos y consistencia")
    print("   5. Verificar tipo de cargo y motivo")
    print("   6. Integrar con sistema de cobranzas")
    print("   7. Probar validaciones SIFEN contra XSD")
    print("   8. Configurar cálculo automático de intereses")
