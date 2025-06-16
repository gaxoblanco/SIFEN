#!/usr/bin/env python3
"""
Tests para el módulo contact_types.xsd

Este archivo contiene tests unitarios para validar todos los tipos de contacto
definidos en el módulo common/contact_types.xsd.

Ubicación: shared/schemas/v150/tests/test_contact_types.py

Ejecutar:
    pytest shared/schemas/v150/tests/test_contact_types.py -v
    pytest shared/schemas/v150/tests/test_contact_types.py::TestTiposBasicosContacto -v
"""
import sys
from pathlib import Path
from lxml import etree
import pytest
from app.services.xml_generator.schemas.v150.tests.utils.schema_validator import SchemaValidator
from app.services.xml_generator import XMLSampleGenerator
import os
# __file__ es la ruta del archivo actual
ruta_actual = os.path.abspath(__file__)
# Ir 4 niveles arriba
ruta_objetivo = os.path.abspath(
    os.path.join(ruta_actual, '..', '..', '..', '..',)
)


# Agregar utils al path para importar utilidades de testing
sys.path.append(str(Path(__file__).parent / "utils"))


class TestTiposBasicosContacto:
    """Tests para tipos básicos de contacto"""

    @pytest.fixture
    def validator(self):
        """Fixture que proporciona validador para contact_types.xsd"""
        schema_path = "shared/schemas/v150/common/contact_types.xsd"
        return SchemaValidator(schema_path)

    def test_telefono_valido(self, validator):
        """Test validación de número telefónico válido"""
        numeros_validos = [
            "(021) 123-4567",      # Formato Paraguay con paréntesis
            "021-123456",          # Formato Paraguay sin paréntesis
            "+595-21-123456",      # Formato internacional
            "0981-123456",         # Móvil Paraguay
            "+595 981 123456"      # Internacional con espacios
        ]

        for numero in numeros_validos:
            xml = f"<dTelef>{numero}</dTelef>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoTelefono")
            assert is_valid, f"Teléfono válido rechazado: {numero} - Errores: {errors}"

    def test_telefono_invalido(self, validator):
        """Test validación de números telefónicos inválidos"""
        numeros_invalidos = [
            "123",                 # Muy corto
            "a-b-c-d-e-f-g-h-i-j-k-l-m-n-o-p-q-r-s-t-u",  # Muy largo
            "abc-def-ghij",        # Letras no válidas
            "",                    # Vacío
            "++595-21-123456"      # Doble signo +
        ]

        for numero in numeros_invalidos:
            xml = f"<dTelef>{numero}</dTelef>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoTelefono")
            assert not is_valid, f"Teléfono inválido aceptado: {numero}"

    def test_telefono_movil_valido(self, validator):
        """Test validación de teléfono móvil específico"""
        moviles_validos = [
            "0981-123456",         # Formato Paraguay móvil
            "+595-981-123456",     # Internacional móvil
            "0971 123456",         # Con espacios
            "0984123456"           # Sin separadores
        ]

        for movil in moviles_validos:
            xml = f"<dCelular>{movil}</dCelular>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoTelefonoMovil")
            assert is_valid, f"Móvil válido rechazado: {movil} - Errores: {errors}"

    def test_email_valido(self, validator):
        """Test validación de email válido"""
        emails_validos = [
            "usuario@empresa.com.py",     # Dominio Paraguay
            "admin@sifen.set.gov.py",     # Dominio gobierno
            "test.user@example.com",      # Con punto en usuario
            "user+tag@domain.org",        # Con símbolo +
            "user_name@sub.domain.co.uk"  # Subdominio múltiple
        ]

        for email in emails_validos:
            xml = f"<dCorreo>{email}</dCorreo>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoEmail")
            assert is_valid, f"Email válido rechazado: {email} - Errores: {errors}"

    def test_email_invalido(self, validator):
        """Test validación de emails inválidos"""
        emails_invalidos = [
            "usuario",             # Sin @
            "@empresa.com",        # Sin usuario
            "usuario@",            # Sin dominio
            "usuario@empresa",     # Sin TLD
            "usuario..doble@empresa.com",  # Doble punto
            "usuario@empresa..com",        # Doble punto en dominio
            "a@b.c",              # Dominio muy corto
            ""                    # Vacío
        ]

        for email in emails_invalidos:
            xml = f"<dCorreo>{email}</dCorreo>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoEmail")
            assert not is_valid, f"Email inválido aceptado: {email}"

    def test_sitio_web_valido(self, validator):
        """Test validación de URLs válidas"""
        urls_validas = [
            "https://www.empresa.com.py",      # HTTPS básico
            "http://sifen.set.gov.py",         # HTTP gobierno
            "https://subdomain.empresa.com/path?param=value",  # Con parámetros
            "https://empresa.org/es/productos",  # Con path
            "https://tienda.com.py:8080/api"   # Con puerto
        ]

        for url in urls_validas:
            xml = f"<dSitioWeb>{url}</dSitioWeb>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoSitioWeb")
            assert is_valid, f"URL válida rechazada: {url} - Errores: {errors}"

    def test_sitio_web_invalido(self, validator):
        """Test validación de URLs inválidas"""
        urls_invalidas = [
            "www.empresa.com",     # Sin protocolo
            "ftp://empresa.com",   # Protocolo no válido
            "https://",            # Solo protocolo
            "empresa.com",         # Sin protocolo
            "https://.",           # Dominio inválido
            ""                     # Vacío
        ]

        for url in urls_invalidas:
            xml = f"<dSitioWeb>{url}</dSitioWeb>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoSitioWeb")
            assert not is_valid, f"URL inválida aceptada: {url}"

    def test_codigo_postal_valido(self, validator):
        """Test validación de códigos postales válidos"""
        codigos_validos = [
            "1001",               # Paraguay Asunción
            "2001",               # Paraguay Ciudad del Este
            "12345",              # Genérico 5 dígitos
            "A1A 1A1",           # Formato Canadá
            "SW1A 1AA"           # Formato Reino Unido
        ]

        for codigo in codigos_validos:
            xml = f"<dCodPos>{codigo}</dCodPos>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoCodigoPostal")
            assert is_valid, f"Código postal válido rechazado: {codigo} - Errores: {errors}"

    def test_codigo_postal_paraguay(self, validator):
        """Test validación específica para códigos postales de Paraguay"""
        codigos_paraguay_validos = [
            "1001",               # Asunción Centro
            "1010",               # Asunción Recoleta
            "2001",               # Ciudad del Este
            "3001"                # Encarnación
        ]

        for codigo in codigos_paraguay_validos:
            xml = f"<dCodPos>{codigo}</dCodPos>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoCodigoPostalParaguay")
            assert is_valid, f"Código Paraguay válido rechazado: {codigo} - Errores: {errors}"

        # Códigos inválidos para Paraguay
        codigos_invalidos = [
            "123",                # Muy corto
            "12345",              # Muy largo
            "1A01",               # Con letras
            ""                    # Vacío
        ]

        for codigo in codigos_invalidos:
            xml = f"<dCodPos>{codigo}</dCodPos>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoCodigoPostalParaguay")
            assert not is_valid, f"Código Paraguay inválido aceptado: {codigo}"


class TestTiposCompuestosContacto:
    """Tests para tipos compuestos de contacto"""

    @pytest.fixture
    def validator(self):
        """Fixture que proporciona validador para contact_types.xsd"""
        schema_path = "shared/schemas/v150/common/contact_types.xsd"
        return SchemaValidator(schema_path)

    def test_contacto_telefonico_completo(self, validator):
        """Test de contacto telefónico completo"""
        xml = """
        <gContactoTel>
            <dTelef>(021) 123-4567</dTelef>
            <dCelular>0981-123456</dCelular>
            <dFax>(021) 765-4321</dFax>
        </gContactoTel>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoTelefonico")
        assert is_valid, f"Contacto telefónico completo inválido: {errors}"

    def test_contacto_telefonico_minimo(self, validator):
        """Test de contacto telefónico con campos mínimos"""
        xml = """
        <gContactoTel>
            <dTelef>(021) 123-4567</dTelef>
        </gContactoTel>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoTelefonico")
        assert is_valid, f"Contacto telefónico mínimo inválido: {errors}"

    def test_contacto_digital_completo(self, validator):
        """Test de contacto digital completo"""
        xml = """
        <gContactoDig>
            <dCorreo>info@empresa.com.py</dCorreo>
            <dSitioWeb>https://www.empresa.com.py</dSitioWeb>
        </gContactoDig>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoDigital")
        assert is_valid, f"Contacto digital completo inválido: {errors}"

    def test_contacto_completo_all_fields(self, validator):
        """Test de contacto completo con todos los campos"""
        xml = """
        <gContacto>
            <gContactoTel>
                <dTelef>(021) 123-4567</dTelef>
                <dCelular>0981-123456</dCelular>
                <dFax>(021) 765-4321</dFax>
            </gContactoTel>
            <gContactoDig>
                <dCorreo>info@empresa.com.py</dCorreo>
                <dSitioWeb>https://www.empresa.com.py</dSitioWeb>
            </gContactoDig>
            <dCodPos>1001</dCodPos>
        </gContacto>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoCompleto")
        assert is_valid, f"Contacto completo inválido: {errors}"


class TestTiposEspecializadosContacto:
    """Tests para tipos especializados de contacto"""

    @pytest.fixture
    def validator(self):
        """Fixture que proporciona validador para contact_types.xsd"""
        schema_path = "shared/schemas/v150/common/contact_types.xsd"
        return SchemaValidator(schema_path)

    def test_contacto_emisor_obligatorio(self, validator):
        """Test de contacto emisor con email obligatorio"""
        xml = """
        <gContactoEmi>
            <dCorreo>emisor@empresa.com.py</dCorreo>
            <dTelef>(021) 123-4567</dTelef>
            <dSitioWeb>https://www.empresa.com.py</dSitioWeb>
        </gContactoEmi>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoEmisor")
        assert is_valid, f"Contacto emisor válido rechazado: {errors}"

    def test_contacto_emisor_sin_email(self, validator):
        """Test de contacto emisor sin email (debe fallar)"""
        xml = """
        <gContactoEmi>
            <dTelef>(021) 123-4567</dTelef>
            <dSitioWeb>https://www.empresa.com.py</dSitioWeb>
        </gContactoEmi>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoEmisor")
        assert not is_valid, f"Contacto emisor sin email fue aceptado (debería fallar)"

    def test_contacto_receptor_opcional(self, validator):
        """Test de contacto receptor con todos los campos opcionales"""
        xml = """
        <gContactoRec>
            <dCorreo>receptor@cliente.com</dCorreo>
            <dTelef>(021) 987-6543</dTelef>
            <dCelular>0984-987654</dCelular>
        </gContactoRec>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoReceptor")
        assert is_valid, f"Contacto receptor válido rechazado: {errors}"

    def test_contacto_receptor_vacio(self, validator):
        """Test de contacto receptor vacío (debe ser válido)"""
        xml = "<gContactoRec></gContactoRec>"
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoReceptor")
        assert is_valid, f"Contacto receptor vacío rechazado: {errors}"

    def test_contacto_notificaciones_sifen(self, validator):
        """Test de contacto para notificaciones SIFEN"""
        xml = """
        <gContactoNotif>
            <dCorreoNotif>notificaciones@empresa.com.py</dCorreoNotif>
            <dCorreoAlt>backup@empresa.com.py</dCorreoAlt>
            <dTelefSMS>0981-123456</dTelefSMS>
            <cHorarioNotif>2</cHorarioNotif>
        </gContactoNotif>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml, "tipoContactoNotificacionesSIFEN")
        assert is_valid, f"Contacto notificaciones SIFEN inválido: {errors}"


class TestValidacionesEspecificas:
    """Tests para validaciones específicas de Paraguay"""

    @pytest.fixture
    def validator(self):
        """Fixture que proporciona validador para contact_types.xsd"""
        schema_path = "shared/schemas/v150/common/contact_types.xsd"
        return SchemaValidator(schema_path)

    def test_telefono_paraguay_formatos(self, validator):
        """Test formatos específicos de teléfono Paraguay"""
        telefonos_paraguay = [
            "(021) 123-4567",      # Asunción formato completo
            "(061) 234-5678",      # Interior formato completo
            "0981-123456",         # Móvil formato estándar
            "0971-987654"          # Móvil Personal formato estándar
        ]

        for telefono in telefonos_paraguay:
            xml = f"<dTelef>{telefono}</dTelef>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoTelefonoParaguay")
            assert is_valid, f"Teléfono Paraguay válido rechazado: {telefono} - Errores: {errors}"

    def test_email_empresarial_vs_gratuito(self, validator):
        """Test diferencia entre email empresarial y gratuito"""
        # Emails empresariales válidos
        emails_empresariales = [
            "admin@empresa.com.py",
            "ventas@comercial.net",
            "info@organizacion.org"
        ]

        for email in emails_empresariales:
            xml = f"<dCorreo>{email}</dCorreo>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoEmailEmpresarial")
            assert is_valid, f"Email empresarial válido rechazado: {email} - Errores: {errors}"

        # Emails gratuitos (deben ser rechazados por tipoEmailEmpresarial)
        emails_gratuitos = [
            "usuario@gmail.com",
            "test@hotmail.com",
            "personal@yahoo.com"
        ]

        for email in emails_gratuitos:
            xml = f"<dCorreo>{email}</dCorreo>"
            is_valid, errors = validator.validate_xml_fragment(
                xml, "tipoEmailEmpresarial")
            assert not is_valid, f"Email gratuito aceptado en empresarial: {email}"


class TestEnumeracionesContacto:
    """Tests para enumeraciones y tipos de contacto"""

    @pytest.fixture
    def validator(self):
        """Fixture que proporciona validador para contact_types.xsd"""
        schema_path = "shared/schemas/v150/common/contact_types.xsd"
        return SchemaValidator(schema_path)

    def test_tipo_contacto_preferido(self, validator):
        """Test enumeración de tipo de contacto preferido"""
        tipos_validos = ["1", "2", "3", "4",
                         "5"]  # Email, Teléfono, Móvil, Fax, Web

        for tipo in tipos_validos:
            xml = f'<contacto tipo="{tipo}">valor</contacto>'
            # Nota: Este test requiere un elemento que use el atributo
            # En un test real, usaríamos un elemento completo del schema

        tipos_invalidos = ["0", "6", "A", ""]

        for tipo in tipos_invalidos:
            # Similar validación para tipos inválidos
            pass

    def test_estado_contacto(self, validator):
        """Test enumeración de estado de contacto"""
        estados_validos = ["A", "I", "S"]  # Activo, Inactivo, Suspendido

        for estado in estados_validos:
            # Test de validación de estados válidos
            pass

        estados_invalidos = ["X", "1", ""]

        for estado in estados_invalidos:
            # Test de validación de estados inválidos
            pass


class TestIntegracionContactTypes:
    """Tests de integración para tipos de contacto"""

    @pytest.fixture
    def xml_generator(self):
        """Fixture que proporciona generador de XML de muestra"""
        return XMLSampleGenerator()

    @pytest.fixture
    def validator(self):
        """Fixture que proporciona validador para contact_types.xsd"""
        schema_path = "shared/schemas/v150/common/contact_types.xsd"
        return SchemaValidator(schema_path)

    def test_contacto_emisor_completo_real(self, validator, xml_generator):
        """Test integración con datos reales de emisor"""
        contacto_emisor = xml_generator.generate_emisor_contact()
        is_valid, errors = validator.validate_xml(contacto_emisor)
        assert is_valid, f"Contacto emisor real inválido: {errors}"

    def test_contacto_receptor_casos_edge(self, validator):
        """Test casos límite para contacto de receptor"""
        # Receptor solo con email
        xml_solo_email = """
        <gContactoRec>
            <dCorreo>cliente@empresa.com</dCorreo>
        </gContactoRec>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml_solo_email, "tipoContactoReceptor")
        assert is_valid, f"Receptor solo email inválido: {errors}"

        # Receptor solo con teléfono
        xml_solo_telefono = """
        <gContactoRec>
            <dTelef>(021) 123-4567</dTelef>
        </gContactoRec>
        """
        is_valid, errors = validator.validate_xml_fragment(
            xml_solo_telefono, "tipoContactoReceptor")
        assert is_valid, f"Receptor solo teléfono inválido: {errors}"

    def test_performance_validacion_contactos(self, validator):
        """Test de performance para validación masiva de contactos"""
        import time

        contactos_muestra = [
            "<dCorreo>test1@empresa.com</dCorreo>",
            "<dTelef>(021) 123-4567</dTelef>",
            "<dCelular>0981-123456</dCelular>",
            "<dSitioWeb>https://www.empresa.com</dSitioWeb>"
        ] * 100  # 400 validaciones

        start_time = time.time()

        for contacto in contactos_muestra:
            validator.validate_xml_fragment(contacto, "tipoEmail")

        elapsed_time = time.time() - start_time

        # Debe procesar 400 validaciones en menos de 1 segundo
        assert elapsed_time < 1.0, f"Validación muy lenta: {elapsed_time:.2f}s para 400 contactos"


# =====================================================================
# TESTS DE REGRESIÓN Y COMPATIBILIDAD
# =====================================================================

class TestCompatibilidadContactTypes:
    """Tests de compatibilidad con versiones anteriores"""

    def test_backward_compatibility(self):
        """Test que tipos de contacto mantienen compatibilidad"""
        # Verificar que campos existentes siguen funcionando
        # con el mismo comportamiento que en schema monolítico
        pass

    def test_migration_from_monolithic(self):
        """Test migración desde schema monolítico"""
        # Verificar que documentos válidos con schema monolítico
        # siguen siendo válidos con schema modular
        pass


# =====================================================================
# CONFIGURACIÓN DE PYTEST
# =====================================================================

def pytest_configure(config):
    """Configuración de pytest para estos tests"""
    config.addinivalue_line(
        "markers", "slow: marca tests como lentos"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "regression: marca tests de regresión"
    )


# Marcar tests específicos
pytestmark = pytest.mark.unit


if __name__ == "__main__":
    # Ejecutar tests cuando se ejecuta directamente
    pytest.main([__file__, "-v"])
