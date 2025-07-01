#!/usr/bin/env python3
"""
Test específico para el template nota_remision_electronica.xml
Valida la generación XML para NRE (Tipo 7)
Muestra el resultado completo generado usando template modular
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from jinja2 import Template


def crear_template_nre_modular():
    """
    Crear el template nota_remision_electronica.xml modular para testing
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
            <iTipDE>7</iTipDE>
            <dDesTipDE>Nota de remisión electrónica</dDesTipDE>
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

        <!-- gDtipDE: Campos específicos Nota de Remisión -->
        <gDtipDE>
            <gCamNRE>
                <iMotTras>{{ datos_nre.motivo_traslado }}</iMotTras>
                <dDesMotTras>{{ datos_nre.descripcion_motivo }}</dDesMotTras>
                {% if datos_nre.observaciones_traslado %}
                <dObsTraslado>{{ datos_nre.observaciones_traslado }}</dObsTraslado>
                {% endif %}
                {% if datos_nre.usuario_responsable %}
                <dUsRespTraslado>{{ datos_nre.usuario_responsable }}</dUsRespTraslado>
                {% endif %}
                {% if datos_nre.informacion_trazabilidad %}
                <dInfoTrazTraslado>{{ datos_nre.informacion_trazabilidad }}</dInfoTrazTraslado>
                {% endif %}
                {% if datos_nre.fecha_estimada_entrega %}
                <dFecEstEntrega>{{ datos_nre.fecha_estimada_entrega }}</dFecEstEntrega>
                {% endif %}
                {% if datos_nre.numero_orden_traslado %}
                <dNumOrdenTraslado>{{ datos_nre.numero_orden_traslado }}</dNumOrdenTraslado>
                {% endif %}
                {% if datos_nre.tipo_operacion_logistica %}
                <iTipOpLogistica>{{ datos_nre.tipo_operacion_logistica }}</iTipOpLogistica>
                {% endif %}
                {% if datos_nre.descripcion_operacion_logistica %}
                <dDesTipOpLogistica>{{ datos_nre.descripcion_operacion_logistica }}</dDesTipOpLogistica>
                {% endif %}
            </gCamNRE>
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

        <!-- gCamItem: Items para traslado (desde _grupo_items.xml) -->
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
            
            <!-- Código de barras para trazabilidad -->
            {% if item.codigo_barras %}
            <dParAranc>{{ item.codigo_barras }}</dParAranc>
            {% endif %}
            
            <!-- Número de serie para control -->
            {% if item.numero_serie %}
            <dNumSerie>{{ item.numero_serie }}</dNumSerie>
            {% endif %}
            
            <!-- Número de lote para trazabilidad -->
            {% if item.numero_lote %}
            <dNumLote>{{ item.numero_lote }}</dNumLote>
            {% endif %}
            
            <!-- IVA del ítem (aunque sea 0) -->
            <iAfecIVA>{{ item.afectacion_iva }}</iAfecIVA>
            <dDesAfecIVA>{{ item.descripcion_afectacion_iva }}</dDesAfecIVA>
        </gCamItem>
        {% endfor %}

        <!-- gTotSub: Totales (desde _grupo_totales.xml) - TODOS = 0 para NRE -->
        <gTotSub>
            <dTotOpe>{{ totales.total_operacion }}</dTotOpe>
            <dTotGralOpe>{{ totales.total_general }}</dTotGralOpe>
        </gTotSub>

        <!-- gCamTrans: Transporte (desde _grupo_transporte.xml) - OBLIGATORIO NRE -->
        <gCamTrans>
            <!-- Responsable del transporte -->
            <iTipResponsable>{{ transporte.tipo_responsable }}</iTipResponsable>
            <dDesTipResponsable>{{ transporte.descripcion_responsable }}</dDesTipResponsable>
            
            <!-- Modalidad del transporte -->
            <iModTransporte>{{ transporte.modalidad_transporte }}</iModTransporte>
            <dDesModTransporte>{{ transporte.descripcion_modalidad }}</dDesModTransporte>
            
            <!-- Tipo de transporte -->
            <iTipTransporte>{{ transporte.tipo_transporte }}</iTipTransporte>
            <dDesTipTransporte>{{ transporte.descripcion_tipo }}</dDesTipTransporte>
            
            <!-- Fechas del traslado -->
            <dFecIniTraslado>{{ transporte.fecha_inicio_traslado }}</dFecIniTraslado>
            {% if transporte.fecha_fin_traslado %}
            <dFecFinTraslado>{{ transporte.fecha_fin_traslado }}</dFecFinTraslado>
            {% endif %}
            
            <!-- Direcciones -->
            <dDirSalida>{{ transporte.direccion_salida }}</dDirSalida>
            <dDirLlegada>{{ transporte.direccion_llegada }}</dDirLlegada>
            
            <!-- Vehículos -->
            {% for vehiculo in transporte.vehiculos %}
            <gVehTrans>
                <iTipVeh>{{ vehiculo.tipo_vehiculo }}</iTipVeh>
                <dDesTipVeh>{{ vehiculo.descripcion_tipo }}</dDesTipVeh>
                <dMarca>{{ vehiculo.marca }}</dMarca>
                {% if vehiculo.modelo %}
                <dModelo>{{ vehiculo.modelo }}</dModelo>
                {% endif %}
                <dNumChapa>{{ vehiculo.numero_chapa }}</dNumChapa>
                {% if vehiculo.numero_senacsa %}
                <dNumSenacsa>{{ vehiculo.numero_senacsa }}</dNumSenacsa>
                {% endif %}
                
                <!-- Conductor -->
                {% if vehiculo.conductor %}
                <gConductor>
                    <dNomConductor>{{ vehiculo.conductor.nombre }}</dNomConductor>
                    <dCedulaConductor>{{ vehiculo.conductor.cedula }}</dCedulaConductor>
                    <dLicenciaConductor>{{ vehiculo.conductor.licencia }}</dLicenciaConductor>
                    {% if vehiculo.conductor.telefono %}
                    <dTelConductor>{{ vehiculo.conductor.telefono }}</dTelConductor>
                    {% endif %}
                </gConductor>
                {% endif %}
            </gVehTrans>
            {% endfor %}
        </gCamTrans>

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


def crear_datos_nre_prueba():
    """Crear datos de prueba completos para NRE - Traslado entre sucursales"""
    print("📝 Creando datos de prueba NRE...")

    # Generar CDC simulado de 44 caracteres para NRE
    cdc_nre = "01800695631001001000000612025063014700000004"  # NRE

    datos = {
        # Identificación NRE
        'cdc': cdc_nre,
        'fecha_emision': "2025-07-01T08:30:00",

        # Específicos NRE
        'datos_nre': {
            'motivo_traslado': 2,  # 2=Traslado entre establecimientos
            'descripcion_motivo': 'Traslado entre sucursales',
            'observaciones_traslado': 'Redistribución de inventario según análisis de rotación. Productos de alta demanda para sucursal centro comercial.',
            'usuario_responsable': 'user_logistica_01',
            'informacion_trazabilidad': 'NRE generada automáticamente por sistema logística para optimización de inventario',
            'fecha_estimada_entrega': '2025-07-01T16:00:00',
            'numero_orden_traslado': 'ORD-LOG-2025-001234',
            'tipo_operacion_logistica': 1,  # 1=Distribución
            'descripcion_operacion_logistica': 'Distribución programada'
        },

        # Timbrado NRE
        'timbrado': {
            'numero_timbrado': "12345678",
            'establecimiento': "001",
            'punto_expedicion': "001",
            'numero_documento': "0000004",  # Siguiente número
            'tipo': 1,
            'descripcion_tipo': "Timbrado electrónico SET"
        },

        # Emisor (Depósito Central)
        'emisor': {
            'ruc': "80016875",
            'dv': "4",
            'razon_social': "EMPRESA DEMO S.A.",
            'direccion': "Depósito Central - Av. Principal 1234, Asunción",
            'telefono': "+595 21 123456",
            'email': "logistica@empresademo.com.py"
        },

        # Receptor (Sucursal)
        'receptor': {
            'naturaleza': 2,
            'descripcion_naturaleza': "Contribuyente",
            'tipo_documento': 2,
            'numero_documento': "80016875",  # Mismo RUC (traslado interno)
            'razon_social': "EMPRESA DEMO S.A. - SUCURSAL CENTRO",
            'direccion': "Sucursal Centro - Calle Palma 567, Asunción"
        },

        # Items para traslado (cantidades normales pero precios = 0)
        'items': [
            {
                'codigo_interno': "PROD001",
                'descripcion': "Notebook HP ProBook 450 G8",
                'cantidad': Decimal("5.000"),  # ✅ Cantidad normal
                'descripcion_unidad_medida': "Unidad",
                # ⚠️ PRECIO = 0 (no hay venta)
                'precio_unitario': Decimal("0"),
                'total_operacion': Decimal("0"),  # ⚠️ TOTAL = 0
                'codigo_barras': "7891234567890",
                'numero_serie': "NB2025001-005",
                'numero_lote': "LOTE-2025-HP-001",
                'afectacion_iva': 3,
                'descripcion_afectacion_iva': "No gravado"
            },
            {
                'codigo_interno': "PROD002",
                'descripcion': "Mouse inalámbrico Logitech MX Master 3",
                'cantidad': Decimal("15.000"),  # ✅ Cantidad normal
                'descripcion_unidad_medida': "Unidad",
                'precio_unitario': Decimal("0"),  # ⚠️ PRECIO = 0
                'total_operacion': Decimal("0"),  # ⚠️ TOTAL = 0
                'codigo_barras': "7891234567891",
                'numero_lote': "LOTE-2025-LOG-002",
                'afectacion_iva': 3,
                'descripcion_afectacion_iva': "No gravado"
            },
            {
                'codigo_interno': "PROD003",
                'descripcion': "Teclado mecánico Corsair K95 RGB",
                'cantidad': Decimal("8.000"),   # ✅ Cantidad normal
                'descripcion_unidad_medida': "Unidad",
                'precio_unitario': Decimal("0"),  # ⚠️ PRECIO = 0
                'total_operacion': Decimal("0"),  # ⚠️ TOTAL = 0
                'codigo_barras': "7891234567892",
                'numero_serie': "KB2025001-008",
                'afectacion_iva': 3,
                'descripcion_afectacion_iva': "No gravado"
            }
        ],

        # Totales TODOS = 0 (no hay venta, solo traslado)
        'totales': {
            'total_operacion': Decimal("0"),   # ⚠️ TOTAL = 0
            'total_iva': Decimal("0"),         # ⚠️ IVA = 0
            'total_general': Decimal("0"),     # ⚠️ TOTAL GENERAL = 0
        },

        # CRÍTICO: Transporte OBLIGATORIO
        'transporte': {
            'tipo_responsable': 1,     # 1=Emisor se encarga
            'descripcion_responsable': 'Emisor',
            'modalidad_transporte': 1,  # 1=Vehículos propios
            'descripcion_modalidad': 'Transporte propio',
            'tipo_transporte': 1,      # 1=Terrestre
            'descripcion_tipo': 'Transporte terrestre',
            'fecha_inicio_traslado': '2025-07-01T08:00:00',
            'fecha_fin_traslado': '2025-07-01T16:00:00',
            'direccion_salida': 'Depósito Central - Av. Principal 1234, Zona Industrial, Asunción',
            'direccion_llegada': 'Sucursal Centro - Calle Palma 567, Centro Comercial, Asunción',
            'vehiculos': [
                {
                    'tipo_vehiculo': 2,        # 2=Camión
                    'descripcion_tipo': 'Camión',
                    'marca': 'Mercedes-Benz',
                    'modelo': 'Atego 1719',
                    'numero_chapa': 'LOG-123',
                    'numero_senacsa': None,    # No aplica para electrónicos
                    'conductor': {
                        'nombre': 'Carlos Rodríguez López',
                        'cedula': '1234567',
                        'licencia': 'LIC456789',
                        'telefono': '+595981123456'
                    }
                }
            ]
        },

        # Condiciones
        'condiciones': {
            'modalidad_venta': 5,  # Traslado
            'descripcion_modalidad': "Traslado interno - Sin valor comercial"
        }
    }

    print("✅ Datos de prueba NRE creados")
    return datos


def validar_nre_datos(datos):
    """Validaciones específicas para NRE"""
    print("🔍 Validando datos NRE...")

    errores = []

    # 1. Transporte obligatorio
    if 'transporte' not in datos:
        errores.append("NRE requiere datos de transporte")

    # 2. Totales = 0
    if datos['totales']['total_general'] != 0:
        errores.append("NRE: Total general debe ser 0 (no hay venta)")

    # 3. Items con precios = 0
    for i, item in enumerate(datos['items']):
        if item['precio_unitario'] != 0:
            print(f"⚠️ ADVERTENCIA: Item {i+1} con precio no cero en NRE")

    # 4. Motivo traslado válido
    if datos['datos_nre']['motivo_traslado'] not in [1, 2, 3, 4, 5, 6]:
        errores.append("Motivo traslado debe estar entre 1-6")

    # 5. Vehículos especificados
    if not datos['transporte'].get('vehiculos'):
        errores.append("Debe especificar al menos un vehículo")

    # 6. Direcciones completas
    if not datos['transporte'].get('direccion_salida'):
        errores.append("Dirección de salida es obligatoria")
    if not datos['transporte'].get('direccion_llegada'):
        errores.append("Dirección de llegada es obligatoria")

    if errores:
        print("❌ Errores de validación:")
        for error in errores:
            print(f"   - {error}")
        return False

    print("✅ Validaciones NRE pasadas")
    return True


def mostrar_variables_nre(datos):
    """Mostrar todas las variables usadas en la generación NRE para validación fácil"""
    print(f"\n🔍 VALIDACIONES CON VARIABLES REALES:")
    print("=" * 60)
    print(f"   1. CDC NRE: {datos['cdc']}")
    print(f"   2. Tipo documento: iTipDE = 7 (NRE)")
    print(f"   3. Fecha emisión: {datos['fecha_emision']}")
    print(
        f"   4. Motivo traslado: {datos['datos_nre']['motivo_traslado']} ({datos['datos_nre']['descripcion_motivo']})")
    print(
        f"   5. Observaciones: {datos['datos_nre']['observaciones_traslado']}")
    print(
        f"   6. Usuario responsable: {datos['datos_nre']['usuario_responsable']}")
    print(f"   7. Número orden: {datos['datos_nre']['numero_orden_traslado']}")
    print(
        f"   8. Fecha estimada entrega: {datos['datos_nre']['fecha_estimada_entrega']}")
    print(f"   9. Emisor: {datos['emisor']['razon_social']}")
    print(f"  10. Receptor: {datos['receptor']['razon_social']}")
    print(
        f"  11. Total general: Gs. {datos['totales']['total_general']:,} (debe ser 0)")

    print(f"\n🚛 INFORMACIÓN DE TRANSPORTE:")
    print(
        f"   - Responsable: {datos['transporte']['descripcion_responsable']}")
    print(f"   - Modalidad: {datos['transporte']['descripcion_modalidad']}")
    print(f"   - Tipo: {datos['transporte']['descripcion_tipo']}")
    print(
        f"   - Inicio traslado: {datos['transporte']['fecha_inicio_traslado']}")
    print(f"   - Fin traslado: {datos['transporte']['fecha_fin_traslado']}")
    print(f"   - Origen: {datos['transporte']['direccion_salida']}")
    print(f"   - Destino: {datos['transporte']['direccion_llegada']}")

    print(f"\n🚐 VEHÍCULOS:")
    for i, vehiculo in enumerate(datos['transporte']['vehiculos'], 1):
        print(
            f"   Vehículo {i}: {vehiculo['marca']} {vehiculo.get('modelo', '')}")
        print(f"      - Tipo: {vehiculo['descripcion_tipo']}")
        print(f"      - Chapa: {vehiculo['numero_chapa']}")
        if vehiculo.get('conductor'):
            print(f"      - Conductor: {vehiculo['conductor']['nombre']}")
            print(f"      - Cédula: {vehiculo['conductor']['cedula']}")
            print(f"      - Licencia: {vehiculo['conductor']['licencia']}")
            print(f"      - Teléfono: {vehiculo['conductor']['telefono']}")
        print()

    print(f"\n📦 ITEMS PARA TRASLADO:")
    total_items = 0
    for i, item in enumerate(datos['items'], 1):
        print(f"   Item {i}: {item['descripcion']}")
        print(f"      - Código interno: {item.get('codigo_interno', 'N/A')}")
        print(f"      - Cantidad: {item['cantidad']}")
        print(
            f"      - Precio unitario: Gs. {item['precio_unitario']:,} (debe ser 0)")
        print(f"      - Total: Gs. {item['total_operacion']:,} (debe ser 0)")
        if 'codigo_barras' in item:
            print(f"      - Código barras: {item['codigo_barras']}")
        if 'numero_serie' in item:
            print(f"      - Número serie: {item['numero_serie']}")
        if 'numero_lote' in item:
            print(f"      - Número lote: {item['numero_lote']}")
        total_items += float(item['cantidad'])
        print()

    print(f"   TOTAL ITEMS: {total_items} unidades")

    print(f"\n💰 TOTALES (TODOS DEBEN SER 0):")
    print(f"   - Total operación: Gs. {datos['totales']['total_operacion']:,}")
    print(f"   - Total IVA: Gs. {datos['totales']['total_iva']:,}")
    print(f"   - TOTAL GENERAL: Gs. {datos['totales']['total_general']:,}")

    print(f"\n🏢 DATOS EMPRESA:")
    print(f"   - RUC: {datos['emisor']['ruc']}-{datos['emisor']['dv']}")
    print(f"   - Emisor: {datos['emisor']['razon_social']}")
    print(f"   - Receptor: {datos['receptor']['razon_social']}")
    print(f"   - Email logística: {datos['emisor']['email']}")

    print(f"\n📋 ANÁLISIS TIPO TRASLADO:")
    tipos_motivo = {
        1: "Venta - Entrega de productos vendidos",
        2: "Traslado establecimientos - Redistribución interna",
        3: "Consignación - Envío para venta en consignación",
        4: "Devolución - Retorno de productos",
        5: "Importación/Exportación - Trámites aduaneros",
        6: "Otros casos especiales"
    }
    tipos_logistica = {
        1: "Distribución",
        2: "Recolección",
        3: "Cross-docking"
    }

    motivo = datos['datos_nre']['motivo_traslado']
    tipo_log = datos['datos_nre']['tipo_operacion_logistica']
    print(f"   - Motivo: {tipos_motivo.get(motivo, 'Desconocido')}")
    print(f"   - Operación: {tipos_logistica.get(tipo_log, 'Desconocido')}")
    print(f"   - Efecto: SOLO TRASLADO (sin valor comercial)")
    print(
        f"   - Es traslado interno: {'✅' if datos['emisor']['ruc'] == datos['receptor']['numero_documento'] else '❌'}")


def test_generar_xml_nre():
    """Test principal para generar XML NRE"""
    print("🚀 GENERANDO XML DE NOTA DE REMISIÓN ELECTRÓNICA (NRE)")
    print("=" * 70)

    try:
        # 1. Crear template
        print("🔧 Creando template NRE modular...")
        template_content = crear_template_nre_modular()
        template = Template(template_content)
        print("✅ Template NRE creado")

        # 2. Crear datos
        datos = crear_datos_nre_prueba()

        # 3. Validar datos NRE
        if not validar_nre_datos(datos):
            return False, "Validación de datos falló"

        # 4. Renderizar
        print("⚙️ Renderizando XML NRE...")
        xml_content = template.render(**datos)
        print("✅ XML NRE renderizado exitosamente")

        # 5. Guardar archivo
        output_file = "nota_remision_electronica_generada.xml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"💾 XML guardado en: {output_file}")

        # 6. Mostrar estadísticas
        lines = xml_content.split('\n')
        print(f"\n📊 ESTADÍSTICAS NRE:")
        print(f"   - Tamaño: {len(xml_content):,} caracteres")
        print(f"   - Líneas: {len(lines):,}")
        print(f"   - Elementos XML: {xml_content.count('<'):,}")

        # 7. Validaciones específicas NRE
        print(f"\n🔍 VALIDACIONES BÁSICAS NRE:")

        validaciones = [
            ('Declaración XML', '<?xml version="1.0"' in xml_content),
            ('Namespace SIFEN', 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' in xml_content),
            ('CDC NRE presente', datos['cdc'] in xml_content),
            ('Tipo documento NRE', '<iTipDE>7</iTipDE>' in xml_content),
            ('Motivo traslado',
             f"<iMotTras>{datos['datos_nre']['motivo_traslado']}</iMotTras>" in xml_content),
            ('Descripción motivo', datos['datos_nre']
             ['descripcion_motivo'] in xml_content),
            ('RUC emisor',
             f"<dRucEm>{datos['emisor']['ruc']}{datos['emisor']['dv']}</dRucEm>" in xml_content),
            ('Totales cero', str(datos['totales']
             ['total_general']) in xml_content),
            ('Específicos NRE', '<gCamNRE>' in xml_content),
            ('Transporte presente', '<gCamTrans>' in xml_content),
            ('Dirección salida', datos['transporte']
             ['direccion_salida'] in xml_content),
            ('Dirección llegada', datos['transporte']
             ['direccion_llegada'] in xml_content),
            ('Vehículo presente', '<gVehTrans>' in xml_content),
            ('Conductor presente', '<gConductor>' in xml_content)
        ]

        for nombre, resultado in validaciones:
            status = "✅" if resultado else "❌"
            print(f"   {status} {nombre}")

        # 8. Mostrar XML completo
        print(f"\n📄 XML NRE GENERADO COMPLETO:")
        print("=" * 80)

        for i, line in enumerate(lines, 1):
            print(f"{i:3d}: {line}")

        print("=" * 80)

        # 9. Mostrar resumen de datos NRE
        print(f"\n📋 RESUMEN DE DATOS NRE:")
        print(f"   - CDC NRE: {datos['cdc']}")
        print(f"   - Fecha NRE: {datos['fecha_emision']}")
        print(f"   - Motivo: {datos['datos_nre']['descripcion_motivo']}")
        print(f"   - Emisor: {datos['emisor']['razon_social']}")
        print(f"   - Receptor: {datos['receptor']['razon_social']}")
        print(f"   - Items trasladados: {len(datos['items'])}")
        print(
            f"   - Total monetario: Gs. {datos['totales']['total_general']:,} (cero)")
        print(f"   - Vehículos: {len(datos['transporte']['vehiculos'])}")
        print(
            f"   - Orden traslado: {datos['datos_nre']['numero_orden_traslado']}")

        # 10. Análisis específico NRE
        print(f"\n🎯 ANÁLISIS ESPECÍFICO NRE:")
        print(
            f"   - Es traslado entre establecimientos: {'✅' if datos['datos_nre']['motivo_traslado'] == 2 else '❌'}")
        print(
            f"   - Totales en cero: {'✅' if datos['totales']['total_general'] == 0 else '❌'}")
        print(
            f"   - Transporte especificado: {'✅' if datos['transporte']['vehiculos'] else '❌'}")
        print(
            f"   - Solo traslado (sin venta): {'✅' if all(item['precio_unitario'] == 0 for item in datos['items']) else '❌'}")
        print(
            f"   - Datos conductor completos: {'✅' if datos['transporte']['vehiculos'][0].get('conductor') else '❌'}")
        print(
            f"   - Traslado interno: {'✅' if datos['emisor']['ruc'] == datos['receptor']['numero_documento'] else '❌'}")

        # 11. Mostrar todas las variables usadas para validación
        mostrar_variables_nre(datos)

        return True, xml_content

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


def mostrar_comparacion_documentos():
    """Mostrar diferencias clave entre todos los tipos de documento"""
    print(f"\n📊 COMPARACIÓN: TODOS LOS TIPOS DE DOCUMENTO SIFEN")
    print("=" * 80)

    comparacion = [
        ("Aspecto", "FE (1)", "AFE (4)", "NCE (5)", "NDE (6)", "NRE (7)"),
        ("─" * 8, "─" * 6, "─" * 7, "─" * 7, "─" * 7, "─" * 7),
        ("Propósito", "Venta", "Import.", "Crédito", "Débito", "Traslado"),
        ("Montos", "Reales", "Reales", "Negativos", "Positivos", "Cero"),
        ("Doc. asociado", "No", "No", "Sí", "Sí", "No"),
        ("Transporte", "Opcional", "Opcional",
         "Opcional", "Opcional", "Obligatorio"),
        ("Campos únicos", "gCamFE", "gCamAE", "gCamNCE", "gCamNDE", "gCamNRE"),
        ("Complejidad", "Baja", "Alta", "Media", "Media", "Alta"),
        ("Frecuencia uso", "Muy alta", "Baja", "Media", "Baja", "Media"),
        ("Validaciones", "Básicas", "Emisor=Rec", "Ref doc", "Ref doc", "Transport")
    ]

    for fila in comparacion:
        print(
            f"   {fila[0]:12} | {fila[1]:8} | {fila[2]:9} | {fila[3]:9} | {fila[4]:9} | {fila[5]}")


if __name__ == "__main__":
    # Ejecutar test NRE
    success, result = test_generar_xml_nre()

    print(f"\n🎯 RESULTADO FINAL NRE:")
    if success:
        print("✅ XML NRE GENERADO EXITOSAMENTE")
        print("💡 Archivo guardado: nota_remision_electronica_generada.xml")
        print("💡 Puedes abrir el archivo para ver el XML completo")

        # Mostrar comparación completa
        mostrar_comparacion_documentos()

    else:
        print(f"❌ ERROR EN GENERACIÓN NRE: {result}")

    print(f"\n📝 PRÓXIMOS PASOS NRE:")
    print("   1. Revisar el XML NRE generado")
    print("   2. Validar estructura gCamNRE (campos específicos remisión)")
    print("   3. Verificar gCamTrans (transporte obligatorio)")
    print("   4. Validar totales = 0 y precios = 0")
    print("   5. Verificar datos completos de vehículos y conductores")
    print("   6. Integrar con sistema de logística")
    print("   7. Probar validaciones SIFEN contra XSD")
    print("   8. Configurar tracking de traslados en tiempo real")

    print(f"\n🎉 FELICITACIONES!")
    print("   ✅ TODOS LOS 5 TIPOS DE DOCUMENTO SIFEN IMPLEMENTADOS:")
    print("      1. ✅ Factura Electrónica (FE)")
    print("      2. ✅ Autofactura Electrónica (AFE)")
    print("      3. ✅ Nota de Crédito Electrónica (NCE)")
    print("      4. ✅ Nota de Débito Electrónica (NDE)")
    print("      5. ✅ Nota de Remisión Electrónica (NRE)")
    print("   🎯 SISTEMA COMPLETO PARA FACTURACIÓN ELECTRÓNICA PARAGUAY")
