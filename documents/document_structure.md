# Estructura Detallada de Campos - Documento Electrónico SIFEN v150

## 📋 **Grupos de Campos del Archivo XML**

### **Tabla de Grupos Principales**
| Grupo | Rango | Descripción | Observaciones |
|-------|-------|-------------|---------------|
| **AA** | AA001-AA009 | Campos que identifican el formato electrónico XML | Metadatos del documento |
| **A** | A001-A099 | Campos firmados del Documento Electrónico | Incluidos en firma digital |
| **B** | B001-B099 | Campos inherentes a la operación de DE | Datos de operación |
| **C** | C001-C099 | Campos de datos del Timbrado | Información de timbrado |
| **D** | D001-D299 | Campos Generales del Documento Electrónico | Emisor, receptor, datos generales |
| **E** | E001-E999 | Campos específicos por tipo de DE | Específicos según tipo documento |
| **F** | F001-F099 | Campos de los subtotales | Cálculos e impuestos |
| **G** | G001-G099 | Campos generales | Información adicional |
| **H** | H001-H099 | Campos DE asociado | Documentos relacionados |
| **I** | I001-I099 | Campos de la firma digital | Certificado y firma |
| **J** | J001-J099 | Campos fuera de la firma digital | QR y datos post-firma |

## 🔧 **Convenciones y Tipos de Datos**

### **Tipos de Datos XML**
| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| **XML** | Documento XML con schema | Documento completo |
| **G** | Grupo de elementos | `<gTimb>...</gTimb>` |
| **CG** | Choice Group (excluyente) | Uno u otro grupo |
| **CE** | Choice Element (excluyente) | Uno u otro elemento |
| **A** | Alfanumérico | "Texto123" |
| **N** | Numérico | 12345 |
| **F** | Fecha | 2018-02-01T14:23:00 |
| **B** | Binario Base64 | Para envío de lotes |

### **Formatos de Tamaño**
| Formato | Descripción | Ejemplo |
|---------|-------------|---------|
| **X** | Tamaño exacto | 2 (exactamente 2 caracteres) |
| **x-y** | Tamaño mínimo x, máximo y | 0-10 (entre 0 y 10 caracteres) |
| **Xpn** | Tamaño exacto x con n decimales | 22p4 (22 dígitos, 4 decimales) |
| **xp(n-m)** | Tamaño x con decimales entre n y m | 22p(0-7) |
| **(x-y)p(n-m)** | Tamaño variable con decimales variables | 1-11p(0-6) |

### **Ejemplos de Formato Numérico**
| Valor Original | Formato Campo | Valor XML |
|----------------|---------------|-----------|
| 1.105,13 | 0-11p0-6 | 1105.13 |
| 1.105,137 | 0-11p0-6 | 1105.137 |
| 1.105 | 0-11p0-6 | 1105 |
| 0 | 0-11p0-6 | 0 |

## 📄 **Grupo AA: Campos de Identificación del Formato XML**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia |
|----|-------|-------------|------|----------|------------|
| AA001 | dVerFor | Versión del formato | N | 3 | 1-1 |

## 📄 **Grupo A: Campos Firmados del DE (A001-A099)**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| A002 | Id | Código de Control (CDC) | A | 44 | 1-1 | Atributo ID para firma |
| A003 | dDVId | Dígito verificador del CDC | N | 1 | 1-1 | Módulo 11 |
| A004 | dFecFirma | Fecha y hora de la firma digital | F | 19 | 1-1 | AAAA-MM-DDThh:mm:ss |

## 📄 **Grupo B: Campos de Operación del DE (B001-B099)**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| B001 | gOpeDE | Grupo de operación | G | - | 1-1 | Nodo padre |
| B002 | iTipEmi | Tipo de emisión | N | 1 | 1-1 | 1=Normal, 2=Contingencia |
| B003 | dDesTipEmi | Descripción tipo emisión | A | 10-12 | 1-1 | "Normal" o "Contingencia" |
| B004 | dCodSeg | Código de seguridad | N | 9 | 1-1 | Aleatorio, 9 dígitos |

## 📄 **Grupo C: Campos del Timbrado (C001-C099)**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| C001 | gTimb | Grupo del timbrado | G | - | 1-1 | Nodo padre |
| C002 | iTiDE | Tipo de documento | N | 2 | 1-1 | 01=FE, 04=AFE, etc. |
| C003 | dDesTiDE | Descripción tipo documento | A | 17-28 | 1-1 | "Factura electrónica", etc. |
| C004 | dNumTim | Número del timbrado | N | 8 | 1-1 | SET asignado |
| C005 | dEst | Establecimiento | N | 3 | 1-1 | Completar con ceros |
| C006 | dPunExp | Punto de expedición | N | 3 | 1-1 | Completar con ceros |
| C007 | dNumDoc | Número del documento | N | 7 | 1-1 | Completar con ceros |
| C010 | dSerieNum | Serie | A | 2-3 | 0-1 | Opcional según tipo |

## 📄 **Grupo D: Datos Generales (D001-D299)**

### **D1: Operación Comercial (D010-D099)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia |
|----|-------|-------------|------|----------|------------|
| D001 | gDatGralOpe | Grupo datos generales | G | - | 1-1 |
| D002 | dFeEmiDE | Fecha de emisión del DE | F | 10 | 1-1 |
| D003 | dFeVencPag | Fecha de vencimiento para el pago | F | 10 | 0-1 |

### **D2: Identificación del Emisor (D100-D129)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| D100 | gEmis | Grupo del emisor | G | - | 1-1 | Nodo padre |
| D101 | dRucEm | RUC del emisor | A | 8 | 1-1 | Sin dígito verificador |
| D102 | dDVEmi | DV del RUC emisor | N | 1 | 1-1 | Dígito verificador |
| D103 | iTipCont | Tipo de contribuyente | N | 1 | 1-1 | 1=Persona física, 2=Jurídica |
| D104 | cTipReg | Código tipo régimen | N | 1 | 1-1 | Ver tabla regímenes |
| D105 | dNomEmi | Nombre/razón social emisor | A | 4-60 | 1-1 | - |
| D106 | dNomFanEmi | Nombre de fantasía emisor | A | 4-60 | 0-1 | - |
| D107 | dDirEmi | Dirección del emisor | A | 5-200 | 1-1 | - |
| D108 | dNumCas | Número de casa | A | 1-20 | 0-1 | - |
| D109 | cDepEmi | Código departamento emisor | N | 1-3 | 1-1 | - |
| D110 | cDisEmi | Código distrito emisor | N | 1-3 | 1-1 | - |
| D111 | cCiuEmi | Código ciudad emisor | N | 1-3 | 1-1 | - |
| D112 | dDesCiuEmi | Descripción ciudad emisor | A | 3-100 | 1-1 | - |
| D113 | dTelEmi | Teléfono emisor | A | 6-15 | 0-1 | - |
| D114 | dEmailE | Email emisor | A | 3-80 | 0-1 | - |

### **D2.1: Actividad Económica del Emisor (D130-D139)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia |
|----|-------|-------------|------|----------|------------|
| D130 | gActEco | Grupo actividad económica | G | - | 1-999 |
| D131 | cActEco | Código actividad económica | N | 6 | 1-1 |
| D132 | dDesActEco | Descripción actividad económica | A | 8-200 | 1-1 |

### **D3: Identificación del Receptor (D200-D299)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| D200 | gDatRec | Grupo del receptor | G | - | 0-1 | Opcional para consumidor final |
| D201 | iTiContRec | Tipo de contribuyente receptor | N | 1 | 1-1 | 1=Contribuyente, 2=No contribuyente |
| D202 | iNatRec | Naturaleza del receptor | N | 1 | 0-1 | 1=Nacional, 2=Extranjero |
| D203 | iTiOpe | Tipo de operación | N | 1 | 1-1 | 1=B2B, 2=B2C, 3=B2G, 4=B2F |
| D204 | cPaisRec | Código país receptor | A | 3 | 0-1 | ISO 3166-1 |
| D205 | dDesPaisRe | Descripción país receptor | A | 4-50 | 0-1 | - |
| D206 | iTiContRuc | Tipo de contribuyente RUC | N | 1 | 0-1 | - |
| D207 | dRucRec | RUC del receptor | A | 3-8 | 0-1 | - |
| D208 | dDVRec | DV del RUC receptor | N | 1 | 0-1 | - |
| D209 | iTipIDRec | Tipo de documento identidad | N | 1 | 0-1 | 1=Cédula, 2=Pasaporte, etc. |
| D210 | dNumIDRec | Número documento identidad | A | 1-20 | 0-1 | - |
| D211 | dNomRec | Nombre/razón social receptor | A | 4-60 | 0-1 | - |
| D212 | dNomFanRec | Nombre fantasía receptor | A | 4-60 | 0-1 | - |
| D213 | dDirRec | Dirección receptor | A | 5-200 | 0-1 | - |
| D218 | dNumCasRec | Número casa receptor | A | 1-20 | 0-1 | - |

## 📄 **Grupo E: Campos Específicos por Tipo DE (E001-E999)**

### **E1: Factura Electrónica (E010-E099)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia |
|----|-------|-------------|------|----------|------------|
| E010 | gDtipDE | Grupo tipo DE | G | - | 1-1 |
| E011 | gCamFE | Grupo campos FE | G | - | 0-1 |

### **E4: Autofactura Electrónica (E300-E399)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia |
|----|-------|-------------|------|----------|------------|
| E300 | gCamAE | Grupo campos AFE | G | - | 0-1 |

### **E7: Condición de la Operación (E600-E699)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| E600 | gCamCond | Grupo condición operación | G | - | 1-1 | - |
| E601 | iCondOpe | Condición de la operación | N | 1 | 1-1 | 1=Contado, 2=Crédito |
| E602 | dDCondOpe | Descripción condición | A | 7 | 1-1 | "Contado" o "Crédito" |

### **E8: Items de la Operación (E700-E899)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| E700 | gCamItem | Grupo de ítems | G | - | 1-9999 | Lista de productos/servicios |
| E701 | dCodInt | Código interno del ítem | A | 1-20 | 0-1 | Código del emisor |
| E702 | dParAranc | Partida arancelaria | N | 2-10 | 0-1 | - |
| E703 | dNCM | Código NCM | N | 2-8 | 0-1 | - |
| E704 | dDncpG | Código DNCP (General) | A | 8-19 | 0-1 | - |
| E705 | dDncpE | Código DNCP (Específico) | A | 8-19 | 0-1 | - |
| E706 | dGtin | Código GTIN | N | 8-14 | 0-1 | Código de barras |
| E707 | dGtinPq | GTIN del paquete | N | 8-14 | 0-1 | - |
| E708 | dDesProSer | Descripción producto/servicio | A | 1-120 | 1-1 | - |
| E709 | cUniMed | Código unidad medida | N | 1-4 | 1-1 | - |
| E710 | dDesUniMed | Descripción unidad medida | A | 1-20 | 1-1 | - |
| E711 | dCantProSer | Cantidad | N | 1-11p(0-6) | 1-1 | - |
| E712 | cPaisOrig | País de origen | A | 3 | 0-1 | ISO 3166-1 |
| E713 | dDesPaisOrig | Descripción país origen | A | 4-50 | 0-1 | - |

## 📄 **Grupo F: Campos de Subtotales (F001-F099)**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| F001 | gTotSub | Grupo de subtotales | G | - | 1-1 | - |
| F008 | dSubExe | Subtotal exento | N | 1-15p(0-4) | 0-1 | - |
| F009 | dSubExo | Subtotal exonerado | N | 1-15p(0-4) | 0-1 | - |
| F010 | dSub5 | Subtotal IVA 5% | N | 1-15p(0-4) | 0-1 | - |
| F011 | dSub10 | Subtotal IVA 10% | N | 1-15p(0-4) | 0-1 | - |
| F013 | dTotOpe | Total de la operación | N | 1-15p(0-4) | 1-1 | - |
| F014 | dTotDesc | Total descuentos | N | 1-15p(0-4) | 0-1 | - |
| F018 | dTotDescGlotem | Descuentos globales sobre ítems | N | 1-15p(0-4) | 0-1 | - |
| F019 | dTotAntItem | Anticipos sobre ítems | N | 1-15p(0-4) | 0-1 | - |
| F020 | dTotAnt | Total anticipos | N | 1-15p(0-4) | 0-1 | - |
| F025 | dPorcDescTotal | Porcentaje descuento total | N | 1-3p(0-2) | 0-1 | - |
| F027 | dDescTotal | Descuento total | N | 1-15p(0-4) | 0-1 | - |
| F033 | dTotGralOpe | Total general operación | N | 1-15p(0-4) | 1-1 | - |
| F034 | dTotIVA | Total IVA | N | 1-15p(0-4) | 1-1 | - |

## 📄 **Grupo G: Campos Generales (G001-G099)**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| G001 | gCamGen | Grupo campos generales | G | - | 0-1 | - |
| G002 | dOrdCompra | Orden de compra | A | 1-15 | 0-1 | - |
| G003 | dOrdVta | Orden de venta | A | 1-15 | 0-1 | - |
| G004 | dAsiento | Número de asiento | A | 1-15 | 0-1 | - |

## 📄 **Grupo H: Campos DE Asociado (H001-H099)**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| H001 | gCamDEAsoc | Grupo DE asociado | G | - | 0-1 | - |
| H002 | iTipDocAso | Tipo documento asociado | N | 1 | 1-1 | 1=Electrónico, 2=Impreso, 3=Constancia |
| H003 | dDesTipDocAso | Descripción tipo documento | A | 10-18 | 1-1 | - |
| H004 | dCdCDERef | CDC del DE referenciado | A | 44 | 0-1 | Solo si H002=1 |
| H005 | dNTimDI | Número timbrado documento impreso | N | 8 | 0-1 | Solo si H002=2 |
| H006 | dEstDocAso | Establecimiento | A | 3 | 0-1 | Solo si H002=2 |
| H007 | dPExpDocAso | Punto de expedición | A | 3 | 0-1 | Solo si H002=2 |
| H008 | dNumDocAso | Número del documento | A | 7 | 0-1 | Solo si H002=2 |
| H009 | iTipoDocAso | Tipo de documento impreso | N | 1 | 0-1 | 1=Factura, 2=NC, 3=ND, 4=NR, 5=Retención |
| H010 | dDTipoDocAso | Descripción tipo documento impreso | A | 7-16 | 0-1 | - |
| H011 | dFecEmiDI | Fecha emisión documento impreso | F | 10 | 0-1 | AAAA-MM-DD |
| H012 | dNumComRet | Número comprobante retención | A | 15 | 0-1 | - |

## 📄 **Grupo I: Campos de Firma Digital (I001-I099)**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| I001 | Signature | Firma digital | XML | - | 1-1 | XML Digital Signature estándar W3C |
| I002 | SignedInfo | Información firmada | XML | - | 1-1 | - |
| I003 | CanonicalizationMethod | Método de canonicalización | XML | - | 1-1 | - |
| I004 | SignatureMethod | Método de firma | XML | - | 1-1 | - |
| I005 | Reference | Referencia | XML | - | 1-1 | - |
| I006 | DigestMethod | Método de digest | XML | - | 1-1 | - |
| I007 | DigestValue | Valor del digest | XML | - | 1-1 | - |
| I008 | SignatureValue | Valor de la firma | XML | - | 1-1 | - |
| I009 | KeyInfo | Información de la clave | XML | - | 1-1 | - |
| I010 | X509Data | Datos del certificado X509 | XML | - | 1-1 | - |
| I011 | X509Certificate | Certificado X509 | XML | - | 1-1 | - |

## 📄 **Grupo J: Campos Fuera de la Firma Digital (J001-J099)**

| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| J001 | gCamFuFD | Grupo fuera de firma digital | G | - | 0-1 | - |
| J002 | dCarQR | Caracteres que conforman el QR | A | 1-500 | 1-1 | URL del código QR |

## 🔧 **Campos Específicos por Sector**

### **E8.5: Sector Automotores (E770-E789)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| E770 | gVehNuevo | Grupo vehículos nuevos | G | - | 0-1 | - |
| E771 | iTipOpVN | Tipo operación venta vehículos | N | 1 | 0-1 | 1=Representante, 2=Consumidor, 3=Gobierno, 4=Flota |
| E772 | dDesTipOpVN | Descripción tipo operación | A | 16-30 | 0-1 | - |
| E773 | dChasis | Chasis del vehículo | A | 17 | 0-1 | - |
| E774 | dColor | Color del vehículo | A | 1-10 | 0-1 | - |
| E775 | dPotencia | Potencia del motor (CV) | N | 1-4 | 0-1 | - |
| E776 | dCapMot | Capacidad del motor (cc) | N | 1-4 | 0-1 | - |
| E777 | dPNet | Peso neto (toneladas) | N | 1-6p(0-4) | 0-1 | - |
| E778 | dPBruto | Peso bruto (toneladas) | N | 1-6p(0-4) | 0-1 | - |
| E779 | iTipCom | Tipo de combustible | N | 1 | 0-1 | 1=Gasolina, 2=Diésel, 3=Etanol, 4=GNV, 5=Flex, 9=Otro |
| E780 | dDesTipCom | Descripción tipo combustible | A | 3-20 | 0-1 | - |
| E781 | dNroMotor | Número del motor | A | 1-21 | 0-1 | - |
| E782 | dCapTracc | Capacidad máxima tracción (ton) | N | 1-6p(0-4) | 0-1 | - |
| E783 | dAnoFab | Año de fabricación | N | 4 | 0-1 | - |
| E784 | cTipVeh | Tipo de vehículo | A | 4-10 | 0-1 | - |
| E785 | dCapac | Capacidad máxima pasajeros | N | 1-3 | 0-1 | - |
| E786 | dCilin | Cilindradas del motor | A | 4 | 0-1 | - |

### **E9.2: Sector Energía Eléctrica (E791-E799)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| E791 | gGrupEner | Grupo sector energía eléctrica | G | - | 0-1 | - |
| E792 | dNroMed | Número de medidor | A | 1-50 | 0-1 | - |
| E793 | dActiv | Código de actividad | N | 2 | 0-1 | - |
| E794 | dCateg | Código de categoría | A | 3 | 0-1 | - |
| E795 | dLecAnt | Lectura anterior | N | 1-11p2 | 0-1 | - |
| E796 | dLecAct | Lectura actual | N | 1-11p2 | 0-1 | - |
| E797 | dConKwh | Consumo (diferencia E796-E795) | N | 1-11p2 | 0-1 | - |

### **E9.3: Sector Seguros (E800-E809)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| E800 | gGrupSeg | Grupo sector seguros | G | - | 0-1 | - |
| E801 | dCodEmpSeg | Código empresa seguros | A | 20 | 0-1 | Superintendencia de Seguros |

### **E9.3.1: Póliza de Seguros (EA790-EA799)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| EA790 | gGrupPolSeg | Grupo póliza seguros | G | - | 1-999 | - |
| EA791 | dPoliza | Código de la póliza | A | 1-20 | 1-1 | - |
| EA792 | dUnidVig | Unidad tiempo vigencia | A | 3-15 | 1-1 | Ej: hora, día, mes, año |
| EA793 | dVigencia | Vigencia de la póliza | N | 1-5p1 | 1-1 | - |
| EA794 | dNumPoliza | Número de la póliza | A | 1-25 | 1-1 | - |
| EA795 | dFecIniVig | Fecha inicio vigencia | F | 19 | 0-1 | AAAA-MM-DDThh:mm:ss |
| EA796 | dFecFinVig | Fecha fin vigencia | F | 19 | 0-1 | AAAA-MM-DDThh:mm:ss |
| EA797 | dCodInt | Código interno del ítem | A | 1-20 | 0-1 | Referencia a E701 |

### **E9.4: Sector Supermercados (E810-E819)**
| ID | Campo | Descripción | Tipo | Longitud | Ocurrencia | Observaciones |
|----|-------|-------------|------|----------|------------|---------------|
| E810 | gGrupSup | Grupo sector supermercados | G | - | 0-1 | - |
| E811 | dNomCaj | Nombre del cajero | A | 1-20 | 0-1 | - |
| E812 | dEfectivo | Efectivo | N | 1-15p(0-4) | 0-1 | - |
| E813 | dVuelto | Vuelto | N | 1-6p(0-4) | 0-1 | - |
| E814 | dDonac | Monto de la donación | N | 1-6p(0-4) | 0-1 | - |
| E815 | dDesDonac | Descripción de la donación | A | 1-20 | 0-1 | - |

## 💡 **Recomendaciones de Implementación**

### **Validaciones Críticas**
1. **Completar con ceros**: Campos numéricos de tamaño exacto
2. **Sin espacios**: No incluir espacios al inicio/final de campos
3. **Formato fecha**: Siempre AAAA-MM-DD o AAAA-MM-DDThh:mm:ss
4. **Punto decimal**: Usar punto (.) no coma (,) para decimales
5. **UTF-8**: Codificación obligatoria

### **Estructura de Clases Python**
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class GrupoOperacion(BaseModel):
    """Grupo B: Campos de operación del DE"""
    iTipEmi: int = Field(..., ge=1, le=2, description="Tipo emisión: 1=Normal, 2=Contingencia")
    dDesTipEmi: str = Field(..., min_length=10, max_length=12)
    dCodSeg: str = Field(..., regex=r"^\d{9}$", description="Código seguridad 9 dígitos")

class GrupoTimbrado(BaseModel):
    """Grupo C: Campos del timbrado"""
    iTiDE: int = Field(..., description="Tipo documento: 01=FE, 04=AFE, etc.")
    dDesTiDE: str = Field(..., min_length=17, max_length=28)
    dNumTim: str = Field(..., regex=r"^\d{8}$", description="Número timbrado")
    dEst: str = Field(..., regex=r"^\d{3}$", description="Establecimiento")
    dPunExp: str = Field(..., regex=r"^\d{3}$", description="Punto expedición")
    dNumDoc: str = Field(..., regex=r"^\d{7}$", description="Número documento")
    dSerieNum: Optional[str] = Field(None, min_length=2, max_length=3)

class DatosEmisor(BaseModel):
    """Grupo D2: Identificación del emisor"""
    dRucEm: str = Field(..., regex=r"^\d{8}$", description="RUC sin DV")
    dDVEmi: int = Field(..., ge=0, le=9, description="Dígito verificador")
    iTipCont: int = Field(..., ge=1, le=2, description="1=Física, 2=Jurídica")
    cTipReg: int = Field(..., description="Código tipo régimen")
    dNomEmi: str = Field(..., min_length=4, max_length=60, description="Nombre/razón social")
    dNomFanEmi: Optional[str] = Field(None, min_length=4, max_length=60)
    dDirEmi: str = Field(..., min_length=5, max_length=200, description="Dirección")
    dNumCas: Optional[str] = Field(None, min_length=1, max_length=20)
    # ... resto de campos del emisor

class ItemOperacion(BaseModel):
    """Grupo E8: Items de la operación"""
    dCodInt: Optional[str] = Field(None, min_length=1, max_length=20)
    dDesProSer: str = Field(..., min_length=1, max_length=120, description="Descripción producto/servicio")
    cUniMed: int = Field(..., description="Código unidad medida")
    dDesUniMed: str = Field(..., min_length=1, max_length=20)
    dCantProSer: float = Field(..., description="Cantidad")
    # ... resto de campos del ítem

class DocumentoElectronico(BaseModel):
    """Estructura completa del DE"""
    # Metadatos
    dVerFor: str = Field("150", description="Versión formato")
    
    # Grupos principales
    gOpeDE: GrupoOperacion
    gTimb: GrupoTimbrado
    gDatGralOpe: dict  # Grupo D completo
    gDtipDE: dict      # Grupo E específico por tipo
    gTotSub: dict      # Grupo F totales
    gCamGen: Optional[dict] = None  # Grupo G opcional
    gCamDEAsoc: Optional[dict] = None  # Grupo H opcional
```

### **Validaciones de Negocio**
```python
def validar_cdc(cdc: str, datos_documento: dict) -> bool:
    """Validar que CDC coincida con datos del documento"""
    # Extraer componentes del CDC
    ruc_cdc = cdc[:8]
    dv_cdc = cdc[8]
    tipo_doc_cdc = cdc[9:11]
    # ... validar cada componente
    
def calcular_dv_cdc(cdc_sin_dv: str) -> str:
    """Calcular dígito verificador del CDC usando módulo 11"""
    # Implementar algoritmo módulo 11
    pass

def generar_codigo_seguridad() -> str:
    """Generar código de seguridad aleatorio de 9 dígitos"""
    import random
    return f"{random.randint(1, 999999999):09d}"
```

---

**📝 Notas de Implementación:**
- Usar validación local antes de envío a SIFEN
- Implementar generación automática de campos calculados (CDC, DV, etc.)
- Mantener tablas de códigos actualizadas (países, unidades, etc.)
- Validar dependencias entre campos (ej: H004 solo si H002=1)

**🔄 Última actualización**: Basado en Manual Técnico SIFEN v150