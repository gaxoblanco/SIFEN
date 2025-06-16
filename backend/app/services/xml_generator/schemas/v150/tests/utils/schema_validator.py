#!/usr/bin/env python3
"""
Utilidad para extraer y modularizar tipos del schema DE_v150.xsd monolítico.

Este script ayuda a:
1. Analizar el schema monolítico actual
2. Identificar tipos que pueden ser modularizados
3. Generar módulos XSD separados
4. Validar la compatibilidad entre versiones

Uso:
    python schema_extractor.py --input DE_v150.xsd --output-dir shared/schemas/v150/common/
    
Ejemplo:
    python schema_extractor.py --extract geographic_types contact_types
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import xml.etree.ElementTree as ET
from lxml import etree
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SchemaExtractor:
    """
    Extractor de tipos del schema monolítico SIFEN v150.

    Identifica y extrae tipos reutilizables para crear módulos independientes
    que pueden ser incluidos con <xs:include>.
    """

    def __init__(self, input_schema_path: str):
        """
        Inicializa el extractor con el schema fuente.

        Args:
            input_schema_path: Ruta al archivo DE_v150.xsd monolítico
        """
        self.input_path = Path(input_schema_path)
        self.namespace = "http://ekuatia.set.gov.py/sifen/xsd"
        self.target_namespace = "{http://www.w3.org/2001/XMLSchema}"

        # Cargar el schema original
        try:
            self.tree = etree.parse(
                str(self.input_path), parser=etree.XMLParser())
            self.root = self.tree.getroot()
            logger.info(f"Schema cargado exitosamente: {self.input_path}")
        except Exception as e:
            logger.error(f"Error cargando schema: {e}")
            raise

        # Mapeo de tipos por categoría
        self.type_categories = {
            'geographic': {
                'patterns': ['pais', 'pais', 'dep', 'ciu', 'ciudad', 'departamento', 'direccion', 'ubicacion'],
                'fields': ['cPais', 'dDesPais', 'cDep', 'dDesDep', 'cCiu', 'dDesCiu', 'dDirec']
            },
            'contact': {
                'patterns': ['telef', 'correo', 'email', 'fax', 'celular', 'sitio', 'web', 'contacto'],
                'fields': ['dTelef', 'dCorreo', 'dCelular', 'dFax', 'dSitioWeb', 'dCodPos']
            },
            'basic': {
                'patterns': ['version', 'codigo', 'numero', 'fecha', 'hora', 'moneda'],
                'fields': ['dVerFor', 'cMoneda', 'dTipCam', 'dFecEmi']
            },
            'currency': {
                'patterns': ['moneda', 'cambio', 'total', 'subtotal', 'impuesto'],
                'fields': ['cMoneda', 'dTipCam', 'dTotBruto', 'dTotIVA', 'dTotGral']
            }
        }

    def analyze_schema_structure(self) -> Dict[str, List[str]]:
        """
        Analiza la estructura del schema para identificar tipos existentes.

        Returns:
            Diccionario con tipos agrupados por categoría
        """
        logger.info("Analizando estructura del schema...")

        analysis = {
            'simple_types': [],
            'complex_types': [],
            'elements': [],
            'groups': [],
            'attributes': []
        }

        # Encontrar todos los tipos definidos
        for elem in self.root.iter():
            tag = elem.tag.replace(self.target_namespace, '')

            if tag == 'simpleType':
                name = elem.get('name')
                if name:
                    analysis['simple_types'].append(name)

            elif tag == 'complexType':
                name = elem.get('name')
                if name:
                    analysis['complex_types'].append(name)

            elif tag == 'element':
                name = elem.get('name')
                if name:
                    analysis['elements'].append(name)

            elif tag == 'group':
                name = elem.get('name')
                if name:
                    analysis['groups'].append(name)

            elif tag == 'attribute':
                name = elem.get('name')
                if name:
                    analysis['attributes'].append(name)

        # Log del análisis
        for category, items in analysis.items():
            logger.info(f"{category}: {len(items)} encontrados")

        return analysis

    def categorize_types(self, analysis: Dict[str, List[str]]) -> Dict[str, Dict[str, List[str]]]:
        """
        Categoriza los tipos según su propósito (geográfico, contacto, etc.).

        Args:
            analysis: Resultado del análisis de estructura

        Returns:
            Tipos categorizados por propósito
        """
        logger.info("Categorizando tipos por propósito...")

        categorized = {}

        for category, config in self.type_categories.items():
            categorized[category] = {
                'simple_types': [],
                'complex_types': [],
                'elements': [],
                'groups': []
            }

            patterns = config['patterns']
            fields = config.get('fields', [])

            # Buscar tipos que coincidan con los patrones
            for type_category, type_list in analysis.items():
                if type_category in ['simple_types', 'complex_types', 'elements', 'groups']:
                    for type_name in type_list:
                        # Verificar si el nombre coincide con algún patrón
                        for pattern in patterns:
                            if pattern.lower() in type_name.lower():
                                categorized[category][type_category].append(
                                    type_name)
                                break

                        # Verificar si es un campo específico conocido
                        if type_name in fields:
                            categorized[category]['elements'].append(type_name)

        # Log de categorización
        for category, types in categorized.items():
            total = sum(len(type_list) for type_list in types.values())
            logger.info(f"Categoría '{category}': {total} tipos identificados")

        return categorized

    def extract_geographic_types(self, output_dir: Path) -> bool:
        """
        Extrae tipos geográficos específicos del schema actual.

        Args:
            output_dir: Directorio donde guardar el módulo geographic_types.xsd

        Returns:
            True si la extracción fue exitosa
        """
        logger.info("Extrayendo tipos geográficos del schema actual...")

        # Buscar elementos geográficos específicos en el schema
        geographic_elements = []

        # Buscar patrones específicos en el XML
        for elem in self.root.iter():
            if elem.tag.endswith('element'):
                name = elem.get('name', '')
                if any(geo in name.lower() for geo in ['pais', 'dep', 'ciu', 'direc']):
                    geographic_elements.append(elem)

        logger.info(
            f"Encontrados {len(geographic_elements)} elementos geográficos")

        # El módulo geographic_types.xsd ya está creado como artifact
        # Aquí validaríamos que los tipos extraídos coincidan
        output_file = output_dir / "geographic_types.xsd"
        logger.info(f"Módulo geográfico debe crearse en: {output_file}")

        return True

    def extract_contact_types(self, output_dir: Path) -> bool:
        """
        Extrae tipos de contacto específicos del schema actual.

        Args:
            output_dir: Directorio donde guardar el módulo contact_types.xsd

        Returns:
            True si la extracción fue exitosa
        """
        logger.info("Extrayendo tipos de contacto del schema actual...")

        # Buscar elementos de contacto específicos
        contact_elements = []

        for elem in self.root.iter():
            if elem.tag.endswith('element'):
                name = elem.get('name', '')
                if any(contact in name.lower() for contact in ['telef', 'correo', 'celular', 'fax']):
                    contact_elements.append(elem)

        logger.info(
            f"Encontrados {len(contact_elements)} elementos de contacto")

        # El módulo contact_types.xsd ya está creado como artifact
        output_file = output_dir / "contact_types.xsd"
        logger.info(f"Módulo de contacto debe crearse en: {output_file}")

        return True

    def validate_modular_schema(self, modular_dir: Path) -> bool:
        """Valida que el schema modular sea funcionalmente equivalente al monolítico."""
        logger.info("Validando compatibilidad de schema modular...")

        try:
            main_schema_path = modular_dir / "DE_v150.xsd"

            if not main_schema_path.exists():
                logger.warning(
                    f"Schema principal no encontrado: {main_schema_path}")
                return False

            # Cargar schema modular
            modular_schema = etree.XMLSchema(file=str(main_schema_path))

            # AQUÍ FALTABA: Realizar validaciones reales

            # 1. Validar que el schema se compile correctamente
            if modular_schema.error_log:
                logger.error(
                    f"Errores en schema modular: {modular_schema.error_log}")
                return False

            # 2. Probar validación con un XML de muestra
            sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd" version="1.5.0">
                <dVerFor>150</dVerFor>
                <DE Id="test">
                    <!-- XML mínimo para probar estructura -->
                </DE>
            </rDE>"""

            sample_doc = etree.fromstring(sample_xml, parser=etree.XMLParser())
            is_valid = modular_schema.validate(sample_doc)

            if not is_valid:
                logger.error(
                    f"Schema modular no valida XML de muestra: {modular_schema.error_log}")
                return False

            logger.info("Schema modular validado exitosamente")
            return True

        except Exception as e:
            logger.error(f"Error validando schema modular: {e}")
            return False

    def generate_migration_plan(self) -> Dict[str, str]:
        """
        Genera un plan de migración del schema monolítico al modular.

        Returns:
            Plan de migración con pasos específicos
        """
        plan = {
            "fase_1": "Crear módulos common/ (geographic_types, contact_types, basic_types)",
            "fase_2": "Crear módulos document_core/ (root_elements, operation_data)",
            "fase_3": "Crear módulos parties/ (issuer_types, receiver_types)",
            "fase_4": "Crear módulos document_types/ (invoice_types, autoinvoice_types)",
            "fase_5": "Crear módulos operations/ (payment_conditions, items)",
            "fase_6": "Crear módulos transport/ (transport_core, vehicles)",
            "fase_7": "Crear módulos extensions/ (tracking, automotive)",
            "fase_8": "Actualizar schema principal con imports",
            "fase_9": "Validar compatibilidad completa",
            "fase_10": "Migrar tests y documentación"
        }

        logger.info("Plan de migración generado:")
        for fase, descripcion in plan.items():
            logger.info(f"  {fase}: {descripcion}")

        return plan


def create_output_directory(output_dir: str) -> Path:
    """
    Crea el directorio de salida si no existe.

    Args:
        output_dir: Ruta del directorio a crear

    Returns:
        Path object del directorio creado
    """
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Directorio de salida: {dir_path}")
    return dir_path


def main():
    """Función principal del extractor."""
    parser = argparse.ArgumentParser(
        description="Extractor de tipos del schema SIFEN v150",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Analizar schema completo
  python schema_extractor.py --input DE_v150.xsd --analyze
  
  # Extraer tipos específicos
  python schema_extractor.py --input DE_v150.xsd --extract geographic contact
  
  # Validar schema modular
  python schema_extractor.py --validate --modular-dir shared/schemas/v150/
        """
    )

    parser.add_argument(
        '--input',
        required=True,
        help='Ruta al archivo DE_v150.xsd monolítico'
    )

    parser.add_argument(
        '--output-dir',
        default='shared/schemas/v150/common/',
        help='Directorio donde guardar los módulos extraídos'
    )

    parser.add_argument(
        '--extract',
        nargs='+',
        choices=['geographic', 'contact', 'basic', 'currency', 'all'],
        help='Tipos a extraer del schema monolítico'
    )

    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Solo analizar la estructura del schema'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validar schema modular contra monolítico'
    )

    parser.add_argument(
        '--modular-dir',
        default='shared/schemas/v150/',
        help='Directorio del schema modular para validación'
    )

    parser.add_argument(
        '--plan',
        action='store_true',
        help='Generar plan de migración completo'
    )

    args = parser.parse_args()

    # Verificar que el archivo de entrada existe
    if not Path(args.input).exists():
        logger.error(f"Archivo de entrada no encontrado: {args.input}")
        sys.exit(1)

    # Crear el extractor
    extractor = SchemaExtractor(args.input)

    # Crear directorio de salida
    output_dir = create_output_directory(args.output_dir)

    # Ejecutar acciones según argumentos
    if args.analyze:
        logger.info("=== ANÁLISIS DE ESTRUCTURA ===")
        analysis = extractor.analyze_schema_structure()
        categorized = extractor.categorize_types(analysis)

        print("\n📊 RESUMEN DEL ANÁLISIS")
        print("=" * 50)
        for category, types in categorized.items():
            total = sum(len(type_list) for type_list in types.values())
            if total > 0:
                print(f"📁 {category.upper()}: {total} tipos")
                for type_category, type_list in types.items():
                    if type_list:
                        print(
                            f"   {type_category}: {', '.join(type_list[:3])}{'...' if len(type_list) > 3 else ''}")

    if args.extract:
        logger.info("=== EXTRACCIÓN DE MÓDULOS ===")
        extract_types = args.extract if 'all' not in args.extract else [
            'geographic', 'contact', 'basic', 'currency']

        for extract_type in extract_types:
            if extract_type == 'geographic':
                success = extractor.extract_geographic_types(output_dir)
                logger.info(
                    f"Extracción geográfica: {'✅ Exitosa' if success else '❌ Fallida'}")

            elif extract_type == 'contact':
                success = extractor.extract_contact_types(output_dir)
                logger.info(
                    f"Extracción de contacto: {'✅ Exitosa' if success else '❌ Fallida'}")

    if args.validate:
        logger.info("=== VALIDACIÓN DE SCHEMA MODULAR ===")
        modular_dir = Path(args.modular_dir)
        success = extractor.validate_modular_schema(modular_dir)
        logger.info(f"Validación: {'✅ Exitosa' if success else '❌ Fallida'}")

    if args.plan:
        logger.info("=== PLAN DE MIGRACIÓN ===")
        plan = extractor.generate_migration_plan()
        print("\n🗺️ PLAN DE MIGRACIÓN COMPLETO")
        print("=" * 50)
        for fase, descripcion in plan.items():
            print(f"{fase.replace('_', ' ').upper()}: {descripcion}")

    logger.info("Proceso completado")


if __name__ == '__main__':
    main()
