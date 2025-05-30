# Manual Técnico SIFEN v150 - Versión Optimizada

## 1. INTRODUCCIÓN
Sistema Integrado de Facturación Electrónica Nacional (SIFEN) - Paraguay
- **Versión**: 150 (Sept 2019)
- **Objetivo**: Emisión, validación y almacenamiento de documentos tributarios electrónicos
- **Alcance**: Contribuyentes de IVA voluntarios u obligatorios

## 2. DOCUMENTOS ELECTRÓNICOS SOPORTADOS

### Tipos de Documentos
1. **Factura Electrónica (FE)** - Código: 1
2. **Autofactura Electrónica (AFE)** - Código: 4  
3. **Nota de Crédito Electrónica (NCE)** - Código: 5
4. **Nota de Débito Electrónica (NDE)** - Código: 6
5. **Nota de Remisión Electrónica (NRE)** - Código: 7

## 3. ARQUITECTURA TÉCNICA

### Comunicación
- **Protocolo**: SOAP 1.2 sobre TLS 1.2
- **Formato**: XML con esquemas XSD v150
- **Firma Digital**: Obligatoria (XML Digital Signature)
- **Certificados**: PSC habilitados por MIC Paraguay

### Web Services Principales
```
Producción: https://sifen.set.gov.py/
Test: https://sifen-test.set.gov.py/

Servicios:
- /de/ws/sync/recibe.wsdl (Envío individual)
- /de/ws/async/recibe-lote.wsdl (Lotes hasta 50 docs)
- /de/ws/consultas/consulta.wsdl (Consultas)
- /de/ws/eventos/evento.wsdl (Eventos)
```

## 4. ESTRUCTURA XML BÁSICA

### Esquemas XSD Críticos
- `DE_v150.xsd` - Estructura principal del documento
- `siRecepDE_v150.xsd` - Envío individual
- `resRecepDE_v150.xsd` - Respuesta envío
- `xmldsig-core-schema-v150.xsd` - Firma digital

### Estructura del Documento Electrónico
```xml
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
  <dVerFor>150</dVerFor>
  <DE Id="CDC_44_DIGITOS">
    <!-- Grupos principales -->
    <gOpeDE>...</gOpeDE>        <!-- B: Operación -->
    <gTimb>...</gTimb>          <!-- C: Timbrado -->
    <gDatGralOpe>...</gDatGralOpe> <!-- D: Datos generales -->
    <gDtipDE>...</gDtipDE>      <!-- E: Específicos por tipo -->
    <gTotSub>...</gTotSub>      <!-- F: Totales -->
    <gCamGen>...</gCamGen>      <!-- G: Campos generales -->
    <gCamDEAsoc>...</gCamDEAsoc> <!-- H: Documentos asociados -->
  </DE>
  <Signature>...</Signature>    <!-- I: Firma digital -->
  <gCamFuFD>...</gCamFuFD>     <!-- J: Fuera de firma (QR) -->
</rDE>
```

## 5. CÓDIGO DE CONTROL (CDC)

### Estructura del CDC (44 caracteres)
```
[RUC_EMISOR][DV][TIPO_DOC][ESTABLECIMIENTO][PUNTO_EXP][NUMERO_DOC][FECHA_EMISION][TIPO_EMISION][COD_SEGURIDAD][DV_CDC]
```

**Ejemplo**: `0144444401700100100145282201701251587326098`

### Generación
- RUC Emisor: 8 dígitos + DV
- Tipo documento: 2 dígitos (01=FE, 04=AFE, etc.)
- Establecimiento: 3 dígitos
- Punto expedición: 3 dígitos  
- Número documento: 7 dígitos
- Fecha emisión: 8 dígitos (YYYYMMDD)
- Tipo emisión: 1 dígito (1=Normal, 2=Contingencia)
- Código seguridad: 9 dígitos aleatorios
- DV: 1 dígito verificador (módulo 11)

## 6. VALIDACIONES CRÍTICAS

### Plazo de Transmisión
- **Normal**: Hasta 72 horas desde firma digital
- **Rechazo**: Más de 720 horas (30 días)
- **Extemporáneo**: Entre 72h y 720h (con observaciones)

### Estados de Respuesta
- **Aprobado (A)**: Código 0260
- **Aprobado con Observaciones (AO)**: Código 1005  
- **Rechazado (R)**: Códigos 1000-4999

### Códigos de Error Comunes
- `1000`: CDC no corresponde con XML
- `1001`: CDC duplicado
- `1101`: Número timbrado inválido
- `1250`: RUC emisor inexistente
- `0141`: Firma digital inválida

## 7. CAMPOS OBLIGATORIOS POR DOCUMENTO

### Factura Electrónica (FE)
```xml
<!-- Datos del emisor -->
<dRucEm>12345678</dRucEm>
<dDVEmi>9</dDVEmi>
<dNomEmi>Empresa SAE</dNomEmi>

<!-- Datos del receptor -->
<dNomRec>Cliente XYZ</dNomRec>
<dRucRec>87654321</dRucRec> <!-- Si es contribuyente -->

<!-- Datos de la operación -->
<iTipTra>1</iTipTra> <!-- Tipo transacción -->
<cMoneOpe>PYG</cMoneOpe>
<iTImp>1</iTImp> <!-- IVA -->

<!-- Items -->
<gCamItem>
  <dCodInt>PROD001</dCodInt>
  <dDesProSer>Producto ejemplo</dDesProSer>
  <dCantProSer>1</dCantProSer>
  <dPUniProSer>100000</dPUniProSer>
</gCamItem>

<!-- Totales -->
<dTotGralOpe>110000</dTotGralOpe>
<dTotIVA>10000</dTotIVA>
```

## 8. FIRMA DIGITAL

### Certificados Requeridos
- **Emisor**: PSC Paraguay, tipo F1 o F2
- **RUC**: En SerialNumber (jurídica) o SubjectAlternativeName (física)
- **Vigencia**: Válido al momento de firma

### Estructura de Firma
```xml
<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
  <SignedInfo>
    <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
    <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
    <Reference URI="#CDC_DEL_DOCUMENTO">
      <Transforms>
        <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
        <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
      </Transforms>
      <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
      <DigestValue>...</DigestValue>
    </Reference>
  </SignedInfo>
  <SignatureValue>...</SignatureValue>
  <KeyInfo>
    <X509Data>
      <X509Certificate>...</X509Certificate>
    </X509Data>
  </KeyInfo>
</Signature>
```

## 9. REPRESENTACIÓN GRÁFICA (KuDE)

### Componentes Obligatorios
1. **Encabezado**: Datos emisor, receptor, documento
2. **Items**: Descripción, cantidad, precios, impuestos
3. **Totales**: Subtotales por tasa IVA, total general
4. **Código QR**: Para consulta pública
5. **CDC**: En formato 0000-0000-0000-0000-0000-0000-0000-0000-0000-0000-0000

### Código QR
```
URL: https://ekuatia.set.gov.py/consultas/qr?
Parámetros: nVersion, Id(CDC), dFeEmiDE, dRucRec, dTotGralOpe, dTotIVA, cItems, DigestValue, IdCSC, cHashQR
```

## 10. EVENTOS DEL SISTEMA

### Eventos del Emisor
- **Cancelación**: Hasta 48h (FE) / 168h (otros)
- **Inutilización**: Hasta 15 días del mes siguiente

### Eventos del Receptor  
- **Conformidad/Disconformidad**: Hasta 45 días
- **Desconocimiento**: Hasta 45 días
- **Notificación recepción**: Hasta 45 días

## 11. IMPLEMENTACIÓN TÉCNICA

### Stack Recomendado
```python
# Backend
- FastAPI (Python)
- SQLAlchemy (ORM)
- Cryptography (Firma digital)
- lxml (XML processing)
- requests (HTTP client)

# Frontend
- React/Angular (TypeScript)
- Axios (API client)
- React Hook Form (Formularios)
```

### Flujo de Desarrollo
1. **Generar XML** según esquemas XSD
2. **Firmar digitalmente** con certificado PSC
3. **Validar localmente** contra esquemas
4. **Enviar a SIFEN** vía Web Service
5. **Procesar respuesta** y manejar errores
6. **Generar KuDE** con código QR

### Librerías de Referencia
- `pysifen` (Python)
- `rshk-jsifenlib` (Java)
- Validación XSD local antes de envío

## 12. CONFIGURACIÓN DE DESARROLLO

### Ambiente de Pruebas
```
URL: https://sifen-test.set.gov.py/
RUC Prueba: 80016875-5
Timbrado: 12345678
Certificado: Usar certificado de pruebas PSC
```

### Variables de Entorno
```bash
SIFEN_ENVIRONMENT=test|production
SIFEN_BASE_URL=https://sifen-test.set.gov.py/
SIFEN_CERT_PATH=/path/to/certificate.p12
SIFEN_CERT_PASSWORD=password
SIFEN_CSC=codigo_seguridad_32_caracteres
```

---

**Documentación completa**: Manual Técnico SIFEN v150
**Esquemas XSD**: http://ekuatia.set.gov.py/sifen/xsd
**Portal consultas**: https://ekuatia.set.gov.py