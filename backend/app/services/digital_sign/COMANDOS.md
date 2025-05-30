# Comandos del Módulo de Firma Digital

## Ejecutar Módulo Completo
Ejecuta en secuencia: generación de certificado de prueba, ejemplo de firma y tests.

```bash
python -m backend.app.services.digital_sign.run_all
```

## Firmar XML
Firma un documento XML usando un certificado PFX.

```bash
python -m backend.app.services.digital_sign.run \
    --cert-path ruta/certificado.pfx \
    --cert-password contraseña \
    --xml-path ruta/factura.xml \
    --output-path ruta/factura_firmada.xml
```

Parámetros:
- `--cert-path`: Ruta al archivo PFX (requerido)
- `--cert-password`: Contraseña del certificado (requerido)
- `--xml-path`: Ruta al XML a firmar (requerido)
- `--output-path`: Ruta donde guardar el XML firmado (opcional)

## Verificar Firma
Verifica la firma de un XML firmado.

```bash
python -m backend.app.services.digital_sign.run \
    --cert-path ruta/certificado.pfx \
    --cert-password contraseña \
    --xml-path ruta/factura_firmada.xml \
    --verify
```

Parámetros:
- `--cert-path`: Ruta al archivo PFX (requerido)
- `--cert-password`: Contraseña del certificado (requerido)
- `--xml-path`: Ruta al XML firmado (requerido)
- `--verify`: Activa modo verificación

## Generar Certificado de Prueba
Genera un certificado PFX de prueba para desarrollo.

```bash
python -m backend.app.services.digital_sign.examples.generate_test_cert
```

El certificado se guarda en `examples/cert.pfx` con contraseña `test123`.

## Ejecutar Ejemplo de Firma
Ejecuta un ejemplo de firma usando el certificado de prueba.

```bash
python -m backend.app.services.digital_sign.examples.sign_example
```

## Ejecutar Tests
Ejecuta los tests del módulo con cobertura.

```bash
python -m backend.app.services.digital_sign.tests.run_tests
```

O directamente con pytest:

```bash
pytest backend/app/services/digital_sign/tests/ -v --cov=.. --cov-report=term-missing
```

## Notas Importantes

1. **Certificados de Prueba**
   - Usar solo para desarrollo
   - No usar en producción
   - Contraseña por defecto: test123

2. **Certificados de Producción**
   - Usar certificados emitidos por SET
   - Mantener contraseñas seguras
   - No compartir archivos PFX

3. **XMLs**
   - Deben ser válidos según esquema SIFEN
   - Usar encoding UTF-8
   - No modificar después de firmar

4. **Errores Comunes**
   - "Certificado no encontrado": Verificar ruta
   - "Contraseña inválida": Verificar contraseña
   - "XML inválido": Verificar sintaxis
   - "Firma inválida": XML modificado 