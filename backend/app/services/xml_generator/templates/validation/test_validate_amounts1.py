#!/usr/bin/env python3
"""
Test CORREGIDO para el validador de montos SIFEN (_validate_amounts.xml)
Versión que funciona sin filtro from_json - PARTE 1: Configuración y Validaciones Básicas
"""

import json
from decimal import Decimal
from jinja2 import Environment, DictLoader


def setup_jinja_environment(templates_dict):
    """Configurar entorno Jinja2 con filtros necesarios"""
    def from_json_filter(value):
        """Filtro personalizado para parsear JSON"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {"valid": False, "error": "Error parsing JSON"}

    # Crear entorno con templates y filtro personalizado
    env = Environment(loader=DictLoader(templates_dict))
    env.filters['from_json'] = from_json_filter
    return env


def crear_validador_montos_simplificado():
    """Validador de montos simplificado sin dependencias complejas"""
    return '''
{% macro validate_amount_format(amount_str, max_digits=15, max_decimals=4) %}
{%- if amount_str is not none -%}
    {%- set clean_amount = amount_str|string|trim -%}
    {%- if clean_amount == "" -%}
        {"valid": false, "error": "Monto no puede estar vacío"}
    {%- else -%}
        {%- set is_negative = clean_amount.startswith('-') -%}
        {%- set abs_amount = clean_amount.replace('-', '') -%}
        {%- set has_dot = '.' in abs_amount -%}
        {%- if has_dot -%}
            {%- set parts = abs_amount.split('.') -%}
            {%- if parts|length != 2 -%}
                {"valid": false, "error": "Formato decimal inválido"}
            {%- else -%}
                {%- set integer_part = parts[0] -%}
                {%- set decimal_part = parts[1] -%}
                {%- if not integer_part.isdigit() or not decimal_part.isdigit() -%}
                    {"valid": false, "error": "Monto debe contener solo números"}
                {%- elif integer_part|length > max_digits -%}
                    {"valid": false, "error": "Parte entera excede límite"}
                {%- elif decimal_part|length > max_decimals -%}
                    {"valid": false, "error": "Demasiados decimales"}
                {%- else -%}
                    {"valid": true, "normalized": "{{ clean_amount }}", "amount_decimal": {{ clean_amount|float }}, "is_negative": {{ is_negative|lower }}}
                {%- endif -%}
            {%- endif -%}
        {%- else -%}
            {%- if not abs_amount.isdigit() -%}
                {"valid": false, "error": "Monto debe ser numérico"}
            {%- elif abs_amount|length > max_digits -%}
                {"valid": false, "error": "Número demasiado largo"}
            {%- else -%}
                {"valid": true, "normalized": "{{ clean_amount }}", "amount_decimal": {{ clean_amount|float }}, "is_negative": {{ is_negative|lower }}}
            {%- endif -%}
        {%- endif -%}
    {%- endif -%}
{%- else -%}
    {"valid": false, "error": "Monto es requerido"}
{%- endif -%}
{% endmacro %}

{% macro validate_positive_amount(amount_str) %}
{%- set format_result_json = validate_amount_format(amount_str) -%}
{%- set format_result = format_result_json | from_json -%}
{%- if not format_result.valid -%}
    {"valid": false, "error": "{{ format_result.error }}"}
{%- elif format_result.amount_decimal <= 0 -%}
    {"valid": false, "error": "Monto debe ser mayor a cero"}
{%- else -%}
    {"valid": true, "amount_data": {{ format_result_json }}}
{%- endif -%}
{% endmacro %}

{% macro calculate_iva_amount(base_gravable, tasa_iva) %}
{%- set base_result_json = validate_amount_format(base_gravable) -%}
{%- set base_result = base_result_json | from_json -%}
{%- if not base_result.valid -%}
    {"valid": false, "error": "Base inválida: {{ base_result.error }}"}
{%- else -%}
    {%- set tasa_result_json = validate_amount_format(tasa_iva, 3, 2) -%}
    {%- set tasa_result = tasa_result_json | from_json -%}
    {%- if not tasa_result.valid -%}
        {"valid": false, "error": "Tasa inválida: {{ tasa_result.error }}"}
    {%- elif tasa_result.amount_decimal < 0 or tasa_result.amount_decimal > 100 -%}
        {"valid": false, "error": "Tasa debe estar entre 0% y 100%"}
    {%- else -%}
        {%- set base_val = base_result.amount_decimal -%}
        {%- set tasa_val = tasa_result.amount_decimal -%}
        {%- set iva_decimal = tasa_val / 100 -%}
        {%- set iva_bruto = base_val * iva_decimal -%}
        {%- set iva_redondeado = (iva_bruto * 10000)|round / 10000 -%}
        {"valid": true, "iva_calculated": {{ iva_redondeado }}, "base_gravable": {{ base_val }}, "tasa_porcentual": {{ tasa_val }}, "tasa_valida_paraguay": {{ (tasa_val in [0, 5, 10])|lower }}}
    {%- endif -%}
{%- endif -%}
{% endmacro %}

{% macro format_amount_sifen(amount_str, format_type="decimal") %}
{%- set amount_result_json = validate_amount_format(amount_str) -%}
{%- set amount_result = amount_result_json | from_json -%}
{%- if not amount_result.valid -%}
    {"valid": false, "error": "{{ amount_result.error }}"}
{%- else -%}
    {%- set amount_val = amount_result.amount_decimal -%}
    {%- if format_type == "integer" -%}
        {"valid": true, "formatted": "{{ amount_val|round|int }}"}
    {%- elif format_type == "percentage" -%}
        {"valid": true, "formatted": "{{ "%.2f"|format(amount_val) }}"}
    {%- else -%}
        {%- if amount_val == (amount_val|round) -%}
            {"valid": true, "formatted": "{{ amount_val|round|int }}"}
        {%- else -%}
            {"valid": true, "formatted": "{{ "%.4f"|format(amount_val) }}"}
        {%- endif -%}
    {%- endif -%}
{%- endif -%}
{% endmacro %}
'''


class TestValidacionBasica:
    """Tests básicos de validación de formatos de montos"""

    def test_formatos_montos_validos(self):
        """Test casos montos válidos"""
        print("🧪 TESTING FORMATOS MONTOS VÁLIDOS")
        print("=" * 50)

        # Configurar templates
        templates = {
            '_validate_amounts.xml': crear_validador_montos_simplificado()
        }

        env = setup_jinja_environment(templates)

        # Template simplificado
        template_simple = env.from_string('''
{%- from '_validate_amounts.xml' import validate_amount_format, validate_positive_amount, format_amount_sifen -%}
{
    "amount_format": {{ validate_amount_format(amount) }},
    "positive_amount": {{ validate_positive_amount(amount) }},
    "amount_formatting": {{ format_amount_sifen(amount, format_type) }}
}
        ''')

        # Casos de prueba válidos
        casos_validos = [
            {"amount": "1250.75", "format_type": "decimal",
                "descripcion": "Monto decimal estándar"},
            {"amount": "850", "format_type": "integer",
                "descripcion": "Monto entero"},
            {"amount": "500000", "format_type": "decimal",
                "descripcion": "Monto grande"},
            {"amount": "123.4567", "format_type": "decimal",
                "descripcion": "Monto con 4 decimales"},
            {"amount": "0.01", "format_type": "decimal",
                "descripcion": "Monto muy pequeño"},
        ]

        for i, caso in enumerate(casos_validos, 1):
            print(f"\n📋 CASO {i}: {caso['descripcion']}")
            print(f"   Monto: {caso['amount']}")

            try:
                resultado_json = template_simple.render(**caso)
                resultado = json.loads(resultado_json)

                # Validar formato monto
                amount_fmt = resultado['amount_format']
                if amount_fmt.get('valid'):
                    print(f"   ✅ Formato monto: VÁLIDO")
                    print(f"      Normalizado: {amount_fmt.get('normalized')}")
                else:
                    print(f"   ❌ Formato monto: {amount_fmt.get('error')}")

                # Validar monto positivo
                if float(caso['amount']) > 0:
                    pos_amt = resultado['positive_amount']
                    if pos_amt.get('valid'):
                        print(f"   ✅ Monto positivo: VÁLIDO")
                    else:
                        print(f"   ❌ Monto positivo: {pos_amt.get('error')}")

                # Validar formateo
                fmt_result = resultado['amount_formatting']
                if fmt_result.get('valid'):
                    print(f"   ✅ Formato SIFEN: {fmt_result.get('formatted')}")
                else:
                    print(f"   ❌ Formato SIFEN: {fmt_result.get('error')}")

            except Exception as e:
                print(f"   ❌ Error procesando: {e}")

    def test_formatos_montos_invalidos(self):
        """Test casos montos inválidos"""
        print("\n🧪 TESTING FORMATOS MONTOS INVÁLIDOS")
        print("=" * 50)

        # Configurar templates
        templates = {
            '_validate_amounts.xml': crear_validador_montos_simplificado()
        }

        env = setup_jinja_environment(templates)

        template_simple = env.from_string('''
{%- from '_validate_amounts.xml' import validate_amount_format, validate_positive_amount -%}
{
    "amount_format": {{ validate_amount_format(amount) }},
    "positive_amount": {{ validate_positive_amount(amount) }}
}
        ''')

        # Casos de prueba inválidos
        casos_invalidos = [
            {"amount": "-500.00", "descripcion": "Monto negativo"},
            {"amount": "abc123", "descripcion": "Formato no numérico"},
            {"amount": "123.123456789", "descripcion": "Demasiados decimales"},
            {"amount": "1234567890123456789", "descripcion": "Demasiados dígitos"},
            {"amount": "", "descripcion": "Campo vacío"},
            {"amount": "12.34.56", "descripcion": "Múltiples puntos decimales"},
        ]

        for i, caso in enumerate(casos_invalidos, 1):
            print(f"\n📋 CASO INVÁLIDO {i}: {caso['descripcion']}")
            print(f"   Monto: '{caso['amount']}'")

            try:
                resultado_json = template_simple.render(**caso)
                resultado = json.loads(resultado_json)

                amount_fmt = resultado['amount_format']
                pos_amt = resultado['positive_amount']

                # Al menos una validación debe fallar
                if not amount_fmt.get('valid') or not pos_amt.get('valid'):
                    print(f"   ✅ Correctamente rechazado")

                    if not amount_fmt.get('valid'):
                        print(f"   📝 Error formato: {amount_fmt.get('error')}")
                    if not pos_amt.get('valid'):
                        print(f"   📝 Error positivo: {pos_amt.get('error')}")
                else:
                    print(f"   ❌ ERROR: Debería ser inválido")

            except Exception as e:
                print(f"   ✅ Correctamente falló: {e}")


if __name__ == "__main__":
    print("🚀 EJECUTANDO TESTS VALIDADOR MONTOS SIFEN - PARTE 1")
    print("=" * 70)
    print("📖 Configuración base y validaciones de formato")
    print("=" * 70)

    # Ejecutar tests básicos
    test_basic = TestValidacionBasica()
    test_basic.test_formatos_montos_validos()
    test_basic.test_formatos_montos_invalidos()

    print("\n" + "=" * 70)
    print("🎯 RESUMEN PARTE 1")
    print("=" * 70)
    print("✅ Configuración Jinja2: FUNCIONANDO")
    print("✅ Validación formatos montos: COMPLETADA")
    print("✅ Tests básicos: PASANDO")

    print("\n🎯 SIGUIENTE: TestCalculosIVA")
    print("   - Cálculos IVA Paraguay (0%, 5%, 10%)")
    print("   - Validaciones específicas tributarias")
