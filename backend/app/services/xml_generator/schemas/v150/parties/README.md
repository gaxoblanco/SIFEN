# 🏢 Módulo parties/ - Emisores y Receptores SIFEN v150

Módulo especializado para la definición de tipos de emisores y receptores de documentos electrónicos según especificación SIFEN v150 del Paraguay.

## 🎯 Propósito

Centralizar y modularizar los tipos relacionados con las partes involucradas en los documentos electrónicos (emisores y receptores), implementando completamente los Grupos D2 y D3 del Manual Técnico SIFEN.

## 📁 Estructura del Módulo

```
parties/
├── common_party_types.xsd     # Tipos base compartidos
├── issuer_types.xsd           # Tipos específicos de emisores
├── receiver_types.xsd         # Tipos específicos de receptores
└── README.md                  # Esta documentación
```

## 🧩 Arquitectura Modular

### **Dependencias entre Módulos**
```
common_party_types.xsd ← common/basic_types.xsd
                       ← common/geographic_types.xsd
                       ← common/contact_types.xsd

issuer_types.xsd ← common_party_types.xsd
                 ← common/basic_types.xsd
                 ← common/geographic_types.xsd
                 ← common/contact_types.xsd

receiver_types.xsd ← common_party_types.xsd
                   ← common/basic_types.xsd
                   ← common/geographic_types.xsd
                   ← common/contact_types.xsd
```

### **Reutilización de Tipos**
- **basic_types.xsd**: `tipoRUC`, `tipoDigitoVerificador`
- **geographic_types.xsd**: códigos de departamento, distrito, ciudad, país
- **contact_types.xsd**: `tipoTelefono`, `tipoEmail`

## 📋 Cobertura SIFEN

### **Grupo D2: Identificación del Emisor (D100-D139)**
| Campo SIFEN | Elemento XSD | Descripción |
|-------------|--------------|-------------|
| D100 | `gEmis` | Grupo del emisor |
| D101 | `dRucEm` | RUC del emisor |
| D102 | `dDVEmi` | DV del RUC emisor |
| D103 | `iTipCont` | Tipo de contribuyente |
| D104 | `cTipReg` | Código tipo régimen |
| D105 | `dNomEmi` | Nombre/razón social emisor |
| D106 | `dNomFanEmi` | Nombre de fantasía emisor |
| D107 | `dDirEmi` | Dirección del emisor |
| D108 | `dNumCas` | Número de casa |
| D109-D112 | `cDepEmi`, `cDisEmi`, `cCiuEmi`, `dDesCiuEmi` | Ubicación geográfica |
| D113 | `dTelEmi` | Teléfono emisor |
| D114 | `dEmailE` | Email emisor |
| D130-D132 | `gActEco`, `cActEco`, `dDesActEco` | Actividades económicas |

### **Grupo D3: Identificación del Receptor (D200-D299)**
| Campo SIFEN | Elemento XSD | Descripción |
|-------------|--------------|-------------|
| D200 | `gDatRec` | Grupo del receptor |
| D201 | `iTiContRec` | Tipo de contribuyente receptor |
| D202 | `iNatRec` | Naturaleza del receptor |
| D203 | `iTiOpe` | Tipo de operación |
| D204-D205 | `cPaisRec`, `dDesPaisRe` | País receptor |
| D206-D208 | `iTiContRuc`, `dRucRec`, `dDVRec` | RUC receptor |
| D209-D210 | `iTipIDRec`, `dNumIDRec` | Documento identidad |
| D211-D212 | `dNomRec`, `dNomF