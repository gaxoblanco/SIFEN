"""
Tests para el módulo basic_types.xsd - SIFEN v150

Este módulo contiene tests exhaustivos para validar todos los tipos básicos
definidos en shared/schemas/v150/common/basic_types.xsd

Categorías de tests:
- Tipos de identificación (RUC, CDC, códigos)
- Tipos de documentos electrónicos  
- Tipos primitivos con validación
- Patrones de validación avanzados
- Tests de integración entre tipos

Autor: Sistema SIFEN-Facturación
Versión: 1.5.0
Fecha: 2024-06-16
"""

from test_helpers import XMLTestHelper
from xml_generator import XMLSampleGenerator
from schema_validator import SchemaValidator
import pytest
import os
from pathlib import Path
from lxml import etree
from typing import List, Tuple, Dict, Any

# Importar utilidades de testing específicas para schemas
import sys
sys.path.append(str(Path(__file__).parent / "utils"))


class TestBasicTypes:
    """
    Test suite principal para tipos básicos de SIFEN v150.

    Organización de tests:
    1. Setup y configuración
    2. Tests de tipos de identificación
    3. Tests de tipos de documentos
    4. Tests de tipos primitivos
    5. Tests de validación avanzada
    6. Tests de integración
    """

    @classmethod
    def setup_class(cls):
        """
        Setup inicial para toda la clase de tests.
        Carga el schema y prepara validadores reutilizables.
        """
        # Ruta base de schemas
        cls.schema_base_path = Path(__file__).parent.parent.parent
        cls.basic_types_path = cls.schema_base_path / "common" / "basic_types.xsd"

        # Verificar que el archivo de schema existe
        assert cls.basic_types_path.exists(
        ), f"Schema no encontrado: {cls.basic_types_path}"

        # Inicializar validador y generador
        cls.validator = SchemaValidator(str(cls.basic_types_path))
        cls.xml_generator = XMLSampleGenerator()
        cls.test_helper = XMLTestHelper()

        # Namespace para testing
        cls.namespace = "http://ekuatia.set.gov.py/sifen/xsd"

    def setup_method(self):
        """Setup antes de cada test individual."""
        # Contador de tests para seguimiento
        self.test_counter = getattr(self, 'test_counter', 0) + 1

    # ========================================================================
    # SECCIÓN 1: TESTS DE TIPOS DE IDENTIFICACIÓN
    # ========================================================================

    class TestTiposIdentificacion:
        """Tests específicos para tipos de identificación (RUC, CDC, etc.)"""

        def test_tipo_version_formato_valido(self, setup_class):
            """
            Test AA001 - dVerFor: Validación de versión del formato.

            Casos de prueba:
            - Valor válido "150"
            - Valores inválidos (otros números, texto, vacío)
            """
            # Caso válido
            xml_valido = self.test_helper.create_simple_element(
                "dVerFor", "150", namespace=self.namespace
            )

            is_valid, errors = self.validator.validate_xml_fragment(
                xml_valido, "tipoVersionFormato"
            )
            assert is_valid, f"Versión formato '150' debe ser válida: {errors}"

            # Casos inválidos
            casos_invalidos = ["140", "160", "1.5.0", "", "abc", "150.0"]

            for caso in casos_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dVerFor", caso, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoVersionFormato"
                )
                assert not is_valid, f"Versión '{caso}' debería ser inválida"

        def test_tipo_ruc_emisor_valido(self):
            """
            Test para tipoRUCEmisor: Validación de RUC del emisor (8 dígitos).

            Casos de prueba:
            - RUCs válidos de 8 dígitos
            - RUCs inválidos (longitud incorrecta, caracteres no numéricos)
            """
            # Casos válidos
            rucs_validos = [
                "12345678",  # RUC estándar
                "80012345",  # RUC empresa
                "00112233",  # RUC con ceros iniciales
                "99887766"   # RUC límite superior
            ]

            for ruc in rucs_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dRUCEmi", ruc, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoRUCEmisor"
                )
                assert is_valid, f"RUC '{ruc}' debe ser válido: {errors}"

            # Casos inválidos
            rucs_invalidos = [
                "1234567",    # 7 dígitos (muy corto)
                "123456789",  # 9 dígitos (muy largo)
                "1234567a",   # Contiene letra
                "12-345678",  # Contiene guión
                "",           # Vacío
                # RUC cero (técnicamente válido en formato pero inválido en negocio)
                "00000000"
            ]

            for ruc in rucs_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dRUCEmi", ruc, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoRUCEmisor"
                )
                assert not is_valid, f"RUC inválido '{ruc}' debería fallar validación"

        def test_tipo_ruc_completo_valido(self):
            """
            Test para tipoRUCCompleto: Validación de RUC completo con DV (9 dígitos).
            """
            # Casos válidos - RUC + DV
            rucs_completos_validos = [
                "123456789",  # RUC + DV válido
                "800123456",  # RUC empresa + DV
                "001122334",  # RUC con ceros + DV
                "998877665"   # RUC límite + DV
            ]

            for ruc_completo in rucs_completos_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dRUCRec", ruc_completo, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoRUCCompleto"
                )
                assert is_valid, f"RUC completo '{ruc_completo}' debe ser válido: {errors}"

        def test_tipo_cdc_valido(self):
            """
            Test para tipoCDC: Validación de Código de Control del Documento (44 dígitos).

            Estructura CDC: [RUC_8][DV_1][TIPO_2][EST_3][PE_3][NUM_7][FECHA_8][EMISION_1][SEG_9][DV_1]
            """
            # CDC válido de ejemplo
            cdc_valido = "01234567890123456789012345678901234567890123"  # 44 dígitos

            xml_valido = self.test_helper.create_simple_element(
                "Id", cdc_valido, namespace=self.namespace
            )

            is_valid, errors = self.validator.validate_xml_fragment(
                xml_valido, "tipoCDC"
            )
            assert is_valid, f"CDC válido debe pasar validación: {errors}"

            # Casos inválidos
            cdcs_invalidos = [
                # 43 dígitos (muy corto)
                "0123456789012345678901234567890123456789012",
                # 45 dígitos (muy largo)
                "012345678901234567890123456789012345678901234",
                "0123456789012345678901234567890123456789012a",  # Contiene letra
                "",                                              # Vacío
                # 44 caracteres pero con letra al final (del caso anterior)
                "01234567890123456789012345678901234567890123"
            ]

            for cdc in cdcs_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "Id", cdc, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoCDC"
                )
                assert not is_valid, f"CDC inválido '{cdc}' debería fallar validación"

        def test_tipo_codigo_seguridad_valido(self):
            """
            Test para tipoCodigoSeguridad: Validación de código de seguridad (9 dígitos).
            """
            # Códigos válidos
            codigos_validos = [
                "123456789",  # Código estándar
                "000000001",  # Con ceros iniciales
                "999999999",  # Código máximo
                "987654321"   # Código aleatorio
            ]

            for codigo in codigos_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dCodSeg", codigo, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoCodigoSeguridad"
                )
                assert is_valid, f"Código seguridad '{codigo}' debe ser válido: {errors}"

            # Códigos inválidos
            codigos_invalidos = [
                "12345678",   # 8 dígitos (muy corto)
                "1234567890",  # 10 dígitos (muy largo)
                "12345678a",  # Contiene letra
                "",           # Vacío
                "123-456789"  # Contiene guión
            ]

            for codigo in codigos_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dCodSeg", codigo, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoCodigoSeguridad"
                )
                assert not is_valid, f"Código inválido '{codigo}' debería fallar validación"

    # ========================================================================
    # SECCIÓN 2: TESTS DE TIPOS DE DOCUMENTOS
    # ========================================================================

    class TestTiposDocumento:
        """Tests específicos para tipos de documentos electrónicos"""

        def test_tipo_documento_valido(self):
            """
            Test para tipoDocumento: Validación de tipos de documentos oficiales.

            Valores válidos: 1, 4, 5, 6, 7
            """
            # Tipos válidos según SIFEN v150
            tipos_validos = {
                "1": "Factura Electrónica (FE)",
                "4": "Autofactura Electrónica (AFE)",
                "5": "Nota de Crédito Electrónica (NCE)",
                "6": "Nota de Débito Electrónica (NDE)",
                "7": "Nota de Remisión Electrónica (NRE)"
            }

            for tipo, descripcion in tipos_validos.items():
                xml_valido = self.test_helper.create_simple_element(
                    "iTiDE", tipo, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoDocumento"
                )
                assert is_valid, f"Tipo documento '{tipo}' ({descripcion}) debe ser válido: {errors}"

            # Tipos inválidos
            tipos_invalidos = ["0", "2", "3", "8",
                               "9", "10", "", "1.0", "FE", "a"]

            for tipo in tipos_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "iTiDE", tipo, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoDocumento"
                )
                assert not is_valid, f"Tipo documento inválido '{tipo}' debería fallar validación"

        def test_tipo_emision_valido(self):
            """
            Test para tipoEmision: Validación de tipos de emisión.

            Valores válidos: 1 (Normal), 2 (Contingencia)
            """
            # Tipos de emisión válidos
            emisiones_validas = {
                "1": "Emisión Normal",
                "2": "Emisión de Contingencia"
            }

            for emision, descripcion in emisiones_validas.items():
                xml_valido = self.test_helper.create_simple_element(
                    "iTipEmi", emision, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoEmision"
                )
                assert is_valid, f"Tipo emisión '{emision}' ({descripcion}) debe ser válido: {errors}"

            # Tipos inválidos
            emisiones_invalidas = ["0", "3", "4", "", "1.0", "Normal", "a"]

            for emision in emisiones_invalidas:
                xml_invalido = self.test_helper.create_simple_element(
                    "iTipEmi", emision, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoEmision"
                )
                assert not is_valid, f"Tipo emisión inválido '{emision}' debería fallar validación"

        def test_tipo_establecimiento_valido(self):
            """
            Test para tipoEstablecimiento: Validación de códigos de establecimiento (3 dígitos).
            """
            # Establecimientos válidos
            establecimientos_validos = [
                "001",  # Casa matriz
                "002",  # Primera sucursal
                "010",  # Sucursal con cero
                "999"   # Máximo permitido
            ]

            for est in establecimientos_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dEst", est, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoEstablecimiento"
                )
                assert is_valid, f"Establecimiento '{est}' debe ser válido: {errors}"

            # Establecimientos inválidos
            establecimientos_invalidos = [
                "000",   # Cero no permitido
                "01",    # 2 dígitos (muy corto)
                "1000",  # 4 dígitos (muy largo)
                "00a",   # Contiene letra
                "",      # Vacío
                "1.0"    # Contiene punto
            ]

            for est in establecimientos_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dEst", est, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoEstablecimiento"
                )
                assert not is_valid, f"Establecimiento inválido '{est}' debería fallar validación"

        def test_tipo_punto_expedicion_valido(self):
            """
            Test para tipoPuntoExpedicion: Validación de puntos de expedición (3 dígitos).
            """
            # Puntos válidos
            puntos_validos = [
                "001",  # Punto principal
                "002",  # Segundo punto
                "010",  # Punto con cero
                "999"   # Máximo permitido
            ]

            for punto in puntos_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dPunExp", punto, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoPuntoExpedicion"
                )
                assert is_valid, f"Punto expedición '{punto}' debe ser válido: {errors}"

    # ========================================================================
    # SECCIÓN 3: TESTS DE TIPOS PRIMITIVOS
    # ========================================================================

    class TestTiposPrimitivos:
        """Tests para tipos primitivos con validación (texto, números, fechas)"""

        def test_tipo_numero_documento_valido(self):
            """
            Test para tipoNumeroDocumento: Validación de números de documento (1-7 dígitos).
            """
            # Números válidos
            numeros_validos = [
                "1",        # Mínimo
                "10",       # Dos dígitos
                "123",      # Tres dígitos
                "1234567",  # Máximo (7 dígitos)
                "0000001",  # Con ceros iniciales
                "9999999"   # Número alto
            ]

            for numero in numeros_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dNumDoc", numero, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoNumeroDocumento"
                )
                assert is_valid, f"Número documento '{numero}' debe ser válido: {errors}"

            # Números inválidos
            numeros_invalidos = [
                "0",         # Cero no permitido
                "12345678",  # 8 dígitos (muy largo)
                "",          # Vacío
                "123a",      # Contiene letra
                "12.34",     # Contiene punto decimal
                "-123"       # Número negativo
            ]

            for numero in numeros_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dNumDoc", numero, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoNumeroDocumento"
                )
                assert not is_valid, f"Número documento inválido '{numero}' debería fallar validación"

        def test_tipo_digito_verificador_valido(self):
            """
            Test para tipoDigitoVerificador: Validación de dígitos verificadores (0-9).
            """
            # Dígitos válidos (0-9)
            for digito in range(10):
                xml_valido = self.test_helper.create_simple_element(
                    "dDV", str(digito), namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoDigitoVerificador"
                )
                assert is_valid, f"Dígito verificador '{digito}' debe ser válido: {errors}"

            # Valores inválidos
            valores_invalidos = ["10", "a", "", "1.0", "-1", "01"]

            for valor in valores_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dDV", valor, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoDigitoVerificador"
                )
                assert not is_valid, f"Dígito verificador inválido '{valor}' debería fallar validación"

        def test_tipo_fecha_valido(self):
            """
            Test para tipoFecha: Validación de fechas en formato YYYY-MM-DD.
            """
            # Fechas válidas
            fechas_validas = [
                "2019-09-15",  # Fecha normal
                "2020-02-29",  # Año bisiesto
                "2010-01-01",  # Fecha mínima
                "2099-12-31"   # Fecha máxima
            ]

            for fecha in fechas_validas:
                xml_valido = self.test_helper.create_simple_element(
                    "dFeEmiDE", fecha, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoFecha"
                )
                assert is_valid, f"Fecha '{fecha}' debe ser válida: {errors}"

            # Fechas inválidas
            fechas_invalidas = [
                "2009-12-31",  # Antes del rango mínimo
                "2100-01-01",  # Después del rango máximo
                "2019-13-01",  # Mes inválido
                "2019-02-30",  # Día inválido para febrero
                "19-09-15",    # Formato incorrecto
                "",            # Vacía
                "2019/09/15"   # Formato con barras
            ]

            for fecha in fechas_invalidas:
                xml_invalido = self.test_helper.create_simple_element(
                    "dFeEmiDE", fecha, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoFecha"
                )
                assert not is_valid, f"Fecha inválida '{fecha}' debería fallar validación"

        def test_tipo_texto_valido(self):
            """
            Test para tipos de texto (tipoTexto, tipoTextoCorto, tipoTextoMedio, tipoTextoLargo).
            """
            # Test tipoTextoCorto (hasta 50 caracteres)
            textos_cortos_validos = [
                "Texto simple",
                "a",  # Un carácter
                "x" * 50,  # Máximo permitido
                "Texto con números 123",
                "TEXTO EN MAYÚSCULAS"
            ]

            for texto in textos_cortos_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dNomEmi", texto, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoTextoCorto"
                )
                assert is_valid, f"Texto corto '{texto[:20]}...' debe ser válido: {errors}"

            # Texto muy largo para tipoTextoCorto
            texto_muy_largo = "x" * 51  # 51 caracteres
            xml_invalido = self.test_helper.create_simple_element(
                "dNomEmi", texto_muy_largo, namespace=self.namespace
            )

            is_valid, errors = self.validator.validate_xml_fragment(
                xml_invalido, "tipoTextoCorto"
            )
            assert not is_valid, "Texto de 51 caracteres debería ser inválido para tipoTextoCorto"

        def test_tipo_timbrado_valido(self):
            """
            Test para tipoTimbrado: Validación de números de timbrado (hasta 8 dígitos).
            """
            # Timbrados válidos
            timbrados_validos = [
                "1",         # Mínimo
                "12345678",  # Máximo (8 dígitos)
                "123456",    # Timbrado típico
                "00001234"   # Con ceros iniciales
            ]

            for timbrado in timbrados_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dNumTim", timbrado, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoTimbrado"
                )
                assert is_valid, f"Timbrado '{timbrado}' debe ser válido: {errors}"

            # Timbrados inválidos
            timbrados_invalidos = [
                "",           # Vacío
                "123456789",  # 9 dígitos (muy largo)
                "1234a",      # Contiene letra
                "12.34",      # Contiene punto
                "-123"        # Negativo
            ]

            for timbrado in timbrados_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dNumTim", timbrado, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoTimbrado"
                )
                assert not is_valid, f"Timbrado inválido '{timbrado}' debería fallar validación"

    # ========================================================================
    # SECCIÓN 4: TESTS DE VALIDACIÓN AVANZADA
    # ========================================================================

    class TestValidacionAvanzada:
        """Tests para patrones de validación avanzados (email, teléfono, etc.)"""

        def test_tipo_email_valido(self):
            """
            Test para tipoEmail: Validación de direcciones de correo electrónico.
            """
            # Emails válidos
            emails_validos = [
                "usuario@ejemplo.com",
                "test.email@dominio.org",
                "user+tag@ejemplo.com.py",
                "123@test.co",
                "a@b.co"  # Mínimo válido
            ]

            for email in emails_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dEmailEmi", email, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoEmail"
                )
                assert is_valid, f"Email '{email}' debe ser válido: {errors}"

            # Emails inválidos
            emails_invalidos = [
                "usuario@",           # Sin dominio
                "@ejemplo.com",       # Sin usuario
                "usuario.ejemplo.com",  # Sin @
                "usuario@ejemplo",    # Sin TLD
                "",                   # Vacío
                "usuario@ejemplo.c"   # TLD muy corto
            ]

            for email in emails_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dEmailEmi", email, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoEmail"
                )
                assert not is_valid, f"Email inválido '{email}' debería fallar validación"

        def test_tipo_telefono_valido(self):
            """
            Test para tipoTelefono: Validación de números de teléfono paraguayos.
            """
            # Teléfonos válidos
            telefonos_validos = [
                "595123456789",   # Con código país
                "+595123456789",  # Con código país y +
                "0123456789",     # Con 0 inicial
                "21234567",       # Fijo Asunción (8 dígitos)
                "981123456"       # Móvil (9 dígitos)
            ]

            for telefono in telefonos_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dTelEmi", telefono, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoTelefono"
                )
                assert is_valid, f"Teléfono '{telefono}' debe ser válido: {errors}"

            # Teléfonos inválidos
            telefonos_invalidos = [
                "123456",       # Muy corto
                "1234567890123456",  # Muy largo
                "12345678a",    # Contiene letra
                "",             # Vacío
                "112345678"     # Empieza con 1 (no válido en Paraguay)
            ]

            for telefono in telefonos_invalidos:
                xml_invalido = self.test_helper.create_simple_element(
                    "dTelEmi", telefono, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoTelefono"
                )
                assert not is_valid, f"Teléfono inválido '{telefono}' debería fallar validación"

    # ========================================================================
    # SECCIÓN 5: TESTS DE INTEGRACIÓN Y PERFORMANCE
    # ========================================================================

    class TestIntegracionYPerformance:
        """Tests de integración entre tipos y performance del schema"""

        def test_carga_schema_performance(self):
            """
            Test de performance: Verificar que el schema se carga rápidamente.
            """
            import time

            start_time = time.time()
            validator = SchemaValidator(str(self.basic_types_path))
            load_time = time.time() - start_time

            # El schema debe cargar en menos de 500ms
            assert load_time < 0.5, f"Schema carga muy lento: {load_time:.3f}s"

        def test_validacion_masiva_performance(self):
            """
            Test de performance: Validar múltiples elementos rápidamente.
            """
            import time

            # Generar 100 elementos para validar
            elementos_test = []
            for i in range(100):
                xml_elemento = self.test_helper.create_simple_element(
                    "dVerFor", "150", namespace=self.namespace
                )
                elementos_test.append(xml_elemento)

            # Medir tiempo de validación masiva
            start_time = time.time()
            for elemento in elementos_test:
                is_valid, errors = self.validator.validate_xml_fragment(
                    elemento, "tipoVersionFormato"
                )
                assert is_valid, "Todos los elementos deben ser válidos"

            validation_time = time.time() - start_time

            # Debe validar 100 elementos en menos de 1 segundo
            assert validation_time < 1.0, f"Validación masiva muy lenta: {validation_time:.3f}s"

        def test_tipos_interdependientes(self):
            """
            Test de integración: Verificar que tipos complejos usan correctamente tipos básicos.
            """
            # Este test verifica que tipos como CDC usan correctamente
            # los tipos básicos como RUC, dígitos, etc.

            # Construir un CDC válido usando componentes válidos
            ruc_emisor = "12345678"      # tipoRUCEmisor
            dv_ruc = "9"                 # tipoDigitoVerificador
            # tipoDocumento (como string de 2 dígitos)
            tipo_doc = "01"
            establecimiento = "001"       # tipoEstablecimiento
            punto_exp = "001"            # tipoPuntoExpedicion
            # tipoNumeroDocumento (como string de 7 dígitos)
            num_doc = "0000001"
            fecha_emision = "20190915"   # Fecha en formato YYYYMMDD
            tipo_emision = "1"           # tipoEmision
            cod_seguridad = "123456789"  # tipoCodigoSeguridad
            dv_cdc = "8"                 # tipoDigitoVerificador

            # Ensamblar CDC completo
            cdc_completo = (ruc_emisor + dv_ruc + tipo_doc + establecimiento +
                            punto_exp + num_doc + fecha_emision + tipo_emision +
                            cod_seguridad + dv_cdc)

            assert len(
                cdc_completo) == 44, f"CDC debe tener 44 dígitos, tiene {len(cdc_completo)}"

            # Validar CDC completo
            xml_cdc = self.test_helper.create_simple_element(
                "Id", cdc_completo, namespace=self.namespace
            )

            is_valid, errors = self.validator.validate_xml_fragment(
                xml_cdc, "tipoCDC"
            )
            assert is_valid, f"CDC integrado debe ser válido: {errors}"

        def test_compatibilidad_tipos_base(self):
            """
            Test de compatibilidad: Verificar que tipos derivados mantienen compatibilidad con tipos base.
            """
            # Verificar que tipoRUCEmisor es compatible con tipoRUC
            ruc_test = "12345678"

            # Debe ser válido para ambos tipos
            xml_ruc_base = self.test_helper.create_simple_element(
                "ruc", ruc_test, namespace=self.namespace
            )

            is_valid_base, _ = self.validator.validate_xml_fragment(
                xml_ruc_base, "tipoRUC"
            )
            is_valid_emisor, _ = self.validator.validate_xml_fragment(
                xml_ruc_base, "tipoRUCEmisor"
            )

            assert is_valid_base, "RUC debe ser válido para tipo base"
            assert is_valid_emisor, "RUC debe ser válido para tipo emisor"

    # ========================================================================
    # SECCIÓN 6: TESTS DE REGRESIÓN Y CASOS EDGE
    # ========================================================================

    class TestRegresionYCasosEdge:
        """Tests de regresión y casos edge específicos"""

        def test_casos_limite_longitud(self):
            """
            Test casos límite de longitud para todos los tipos con restricciones.
            """
            casos_limite = [
                # (tipo, valor_limite_valido, valor_limite_invalido)
                ("tipoRUCEmisor", "12345678", "123456789"),
                ("tipoRUCCompleto", "123456789", "1234567890"),
                ("tipoCDC", "1" * 44, "1" * 45),
                ("tipoCodigoSeguridad", "123456789", "1234567890"),
                ("tipoEstablecimiento", "001", "0001"),
                ("tipoPuntoExpedicion", "001", "0001"),
                ("tipoNumeroDocumento", "1234567", "12345678"),
                ("tipoTextoCorto", "x" * 50, "x" * 51),
                ("tipoTextoMedio", "x" * 255, "x" * 256),
                ("tipoTextoLargo", "x" * 2000, "x" * 2001),
                ("tipoTimbrado", "12345678", "123456789"),
                # Límite 100 chars total
                ("tipoEmail", "a@b." + "c" * 95, "a@b." + "c" * 96)
            ]

            for tipo, valor_valido, valor_invalido in casos_limite:
                # Test valor válido en el límite
                xml_valido = self.test_helper.create_simple_element(
                    "test", valor_valido, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, tipo
                )
                assert is_valid, f"Valor límite válido para {tipo} falló: {valor_valido[:20]}..."

                # Test valor inválido que excede el límite
                xml_invalido = self.test_helper.create_simple_element(
                    "test", valor_invalido, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, tipo
                )
                assert not is_valid, f"Valor que excede límite para {tipo} debería ser inválido: {valor_invalido[:20]}..."

        def test_caracteres_especiales_unicode(self):
            """
            Test manejo de caracteres especiales y Unicode en campos de texto.
            """
            # Caracteres especiales que deben ser válidos
            textos_especiales_validos = [
                "Empresa Ñandutí S.A.",      # Ñ (común en Paraguay)
                "José María & Asociados",     # Acentos y &
                "Distribuidora 100%",         # Números y %
                "Café (Premium)",             # Paréntesis
                "Artículos García-López",     # Guión
                "Informática 'El Byte'"       # Comillas simples
            ]

            for texto in textos_especiales_validos:
                xml_valido = self.test_helper.create_simple_element(
                    "dNomEmi", texto, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoTextoMedio"
                )
                assert is_valid, f"Texto con caracteres especiales debe ser válido: '{texto}'"

            # Caracteres que potencialmente causan problemas en XML
            textos_problematicos = [
                "Empresa <Test>",            # Brackets XML
                "Datos & \"Información\"",   # Comillas dobles con &
                "Control\tTab\nNewline",     # Caracteres de control
                ""                           # String vacío
            ]

            for texto in textos_problematicos:
                xml_test = self.test_helper.create_simple_element(
                    "dNomEmi", texto, namespace=self.namespace
                )

                # Verificar que el XML se puede procesar correctamente
                # (independientemente de si el contenido es válido según el schema)
                try:
                    is_valid, errors = self.validator.validate_xml_fragment(
                        xml_test, "tipoTextoMedio"
                    )
                    # Si llega aquí, el XML está bien formado
                    print(
                        f"Texto problemático procesado OK: '{texto[:20]}...'")
                except Exception as e:
                    pytest.fail(
                        f"Error procesando texto problemático '{texto[:20]}...': {e}")

        def test_valores_frontera_numericos(self):
            """
            Test valores frontera para tipos numéricos.
            """
            # Test tipoEnteroPositivo
            valores_frontera = [
                ("1", True),                    # Mínimo válido
                ("999999999999999", True),      # Máximo válido
                ("0", False),                   # Cero (inválido para positivo)
                ("1000000000000000", False),    # Excede máximo
                ("-1", False)                   # Negativo
            ]

            for valor, debe_ser_valido in valores_frontera:
                xml_test = self.test_helper.create_simple_element(
                    "cantidad", valor, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_test, "tipoEnteroPositivo"
                )

                if debe_ser_valido:
                    assert is_valid, f"Valor frontera '{valor}' debe ser válido: {errors}"
                else:
                    assert not is_valid, f"Valor frontera '{valor}' debe ser inválido"

        def test_fechas_casos_especiales(self):
            """
            Test casos especiales para fechas (años bisiestos, fin de mes, etc.).
            """
            # Casos especiales de fechas válidas
            fechas_especiales_validas = [
                "2020-02-29",  # Año bisiesto válido
                "2019-02-28",  # Último día febrero año no bisiesto
                "2019-04-30",  # Último día de abril (30 días)
                "2019-12-31",  # Último día del año
                "2019-01-01"   # Primer día del año
            ]

            for fecha in fechas_especiales_validas:
                xml_valido = self.test_helper.create_simple_element(
                    "dFeEmiDE", fecha, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_valido, "tipoFecha"
                )
                assert is_valid, f"Fecha especial '{fecha}' debe ser válida: {errors}"

            # Casos especiales de fechas inválidas
            fechas_especiales_invalidas = [
                "2019-02-29",  # 29 feb en año no bisiesto
                "2019-04-31",  # 31 de abril (solo 30 días)
                "2019-13-01",  # Mes 13
                "2019-00-01",  # Mes 0
                "2019-01-00",  # Día 0
                "2019-01-32"   # Día 32
            ]

            for fecha in fechas_especiales_invalidas:
                xml_invalido = self.test_helper.create_simple_element(
                    "dFeEmiDE", fecha, namespace=self.namespace
                )

                is_valid, errors = self.validator.validate_xml_fragment(
                    xml_invalido, "tipoFecha"
                )
                assert not is_valid, f"Fecha especial inválida '{fecha}' debería fallar validación"


# ============================================================================
# FIXTURES Y UTILIDADES COMPARTIDAS
# ============================================================================

@pytest.fixture(scope="class")
def schema_validator():
    """Fixture que proporciona un validador de schema reutilizable."""
    schema_path = Path(__file__).parent.parent.parent / \
        "common" / "basic_types.xsd"
    return SchemaValidator(str(schema_path))


@pytest.fixture(scope="class")
def xml_sample_generator():
    """Fixture que proporciona un generador de XMLs de muestra."""
    return XMLSampleGenerator()


@pytest.fixture
def test_data():
    """Fixture con datos de prueba comunes."""
    return {
        "ruc_valido": "12345678",
        "ruc_completo_valido": "123456789",
        "cdc_valido": "01234567890123456789012345678901234567890123",
        "version_formato": "150",
        "tipos_documento": ["1", "4", "5", "6", "7"],
        "tipos_emision": ["1", "2"],
        "fecha_valida": "2019-09-15",
        "email_valido": "test@ejemplo.com",
        "telefono_valido": "21234567"
    }


# ============================================================================
# UTILIDADES DE TESTING ESPECÍFICAS
# ============================================================================

class XMLElementBuilder:
    """
    Clase auxiliar para construir elementos XML de prueba de forma programática.
    """

    def __init__(self, namespace: str):
        self.namespace = namespace

    def build_element(self, tag: str, value: str, attributes: Dict[str, str] = None) -> str:
        """
        Construye un elemento XML simple con el namespace correcto.

        Args:
            tag: Nombre del elemento
            value: Valor del elemento
            attributes: Atributos opcionales del elemento

        Returns:
            String XML del elemento
        """
        attrs = ""
        if attributes:
            attrs = " ".join([f'{k}="{v}"' for k, v in attributes.items()])
            attrs = " " + attrs

        return f'<{tag} xmlns="{self.namespace}"{attrs}>{value}</{tag}>'

    def build_cdc_element(self, cdc_parts: Dict[str, str]) -> str:
        """
        Construye un CDC válido a partir de sus componentes.

        Args:
            cdc_parts: Diccionario con componentes del CDC

        Returns:
            String XML con el CDC completo
        """
        cdc_completo = (
            cdc_parts["ruc_emisor"] +
            cdc_parts["dv_ruc"] +
            cdc_parts["tipo_doc"] +
            cdc_parts["establecimiento"] +
            cdc_parts["punto_exp"] +
            cdc_parts["num_doc"] +
            cdc_parts["fecha_emision"] +
            cdc_parts["tipo_emision"] +
            cdc_parts["cod_seguridad"] +
            cdc_parts["dv_cdc"]
        )

        return self.build_element("Id", cdc_completo)


# ============================================================================
# TESTS DE DOCUMENTACIÓN Y METADATOS
# ============================================================================

class TestDocumentacionSchema:
    """Tests que verifican la documentación y metadatos del schema."""

    def test_schema_tiene_documentacion(self):
        """Verificar que el schema tiene documentación adecuada."""
        schema_path = Path(__file__).parent.parent.parent / \
            "common" / "basic_types.xsd"

        with open(schema_path, 'r', encoding='utf-8') as f:
            contenido_schema = f.read()

        # Verificar elementos de documentación críticos
        elementos_requeridos = [
            "xs:documentation",
            "Sistema Integrado de Facturación Electrónica",
            "version=\"1.5.0\"",
            "http://ekuatia.set.gov.py/sifen/xsd",
            "TIPOS DE IDENTIFICACIÓN",
            "TIPOS DE DOCUMENTOS ELECTRÓNICOS"
        ]

        for elemento in elementos_requeridos:
            assert elemento in contenido_schema, f"Schema debe contener: {elemento}"

    def test_namespace_correcto(self):
        """Verificar que el namespace es correcto."""
        schema_path = Path(__file__).parent.parent.parent / \
            "common" / "basic_types.xsd"
        schema_doc = etree.parse(str(schema_path))

        # Verificar namespace target
        root = schema_doc.getroot()
        target_namespace = root.get("targetNamespace")

        assert target_namespace == "http://ekuatia.set.gov.py/sifen/xsd", \
            f"Namespace incorrecto: {target_namespace}"

        # Verificar versión
        version = root.get("version")
        assert version == "1.5.0", f"Versión incorrecta: {version}"


# ============================================================================
# CONFIGURACIÓN DE PYTEST
# ============================================================================

def pytest_configure(config):
    """Configuración personalizada de pytest para estos tests."""
    # Agregar marcadores personalizados
    config.addinivalue_line(
        "markers",
        "slow: marca tests que tardan más de 1 segundo"
    )
    config.addinivalue_line(
        "markers",
        "integration: marca tests de integración que requieren múltiples componentes"
    )
    config.addinivalue_line(
        "markers",
        "regression: marca tests de regresión para casos específicos"
    )


def pytest_collection_modifyitems(config, items):
    """Modificar la colección de tests para agregar marcadores automáticamente."""
    for item in items:
        # Marcar tests de performance como 'slow'
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.slow)

        # Marcar tests de integración
        if "integracion" in item.name.lower() or "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)

        # Marcar tests de regresión
        if "regresion" in item.name.lower() or "regression" in item.name.lower():
            item.add_marker(pytest.mark.regression)


# ============================================================================
# EJECUCIÓN PRINCIPAL (para testing directo del módulo)
# ============================================================================

if __name__ == "__main__":
    """
    Ejecución directa del módulo de tests.
    Útil para desarrollo y debugging.
    """
    import sys

    # Configurar logging para debugging
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Ejecutar tests con configuración de desarrollo
    pytest.main([
        __file__,
        "-v",                    # Verbose
        "--tb=short",           # Traceback corto
        "--strict-markers",     # Markers estrictos
        "--disable-warnings",   # Deshabilitar warnings de deprecación
        "-x"                    # Parar en primer fallo
    ])
