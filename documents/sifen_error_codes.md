# Códigos de Error SIFEN v150

## 📋 **Estructura de Códigos de Validación**

Los códigos de validación están compuestos de **4 dígitos numéricos** que corresponden a los campos de los Schemas XML.

### **Estados de Validación**
- **A**: Aprobado
- **R**: Rechazo  
- **AO**: Aprobado con observaciones
- **N**: Notificación

## 🔧 **Códigos de Respuesta - Servicios Web**

### **AA - Certificado de Transmisión (TLS)**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| AA01-AA100 | 0000-0099 | Protocolo TLS | - |

### **AB - Forma del Área de Datos**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| AB01 | 0100 | Fallo de schema XML del área de datos | R |
| AB02 | 0101 | Fallo de schema: no existe el campo raíz esperado para el mensaje | R |
| AB03 | 0102 | Fallo de schema: no existe el atributo versión para el campo raíz esperado | R |
| AB05 | 0104 | Existe algún namespace diferente del namespace estándar del DE | R |
| AB06 | 0105 | Existe(n) carácter(es) de edición en el inicio o en el final del mensaje, o entre los campos XML | R |
| AB07 | 0106 | Utilizado prefijo en el namespace | R |
| AB08 | 0107 | Utilizada codificación diferente de UTF-8 | R |

### **AC - Certificado Digital**
| ID | Código | Descripción | Estado | Observaciones |
|---|---|---|---|---|
| AC01 | 0120 | Certificado inválido | R | • No existe certificado de firma<br>• No se aceptan certificados del PSC<br>• KeyUsage no define firma digital y no Repudio |
| AC02 | 0121 | Fechas del certificado inválidas (inicio o final de validez) | R | - |
| AC03 | 0122 | No existe la extensión del RUC en el certificado | R | • Persona Física: en OID SubjectAlternativeName<br>• Persona Jurídica: en OID SerialNumber |
| AC04 | 0123 | Cadena de certificación inválida | R | • Certificado del PSC no habilitado por el MIC<br>• Certificado del PSC revocado<br>• Certificado no está firmado por el PSC |
| AC05 | 0124 | Problema en la LCR del certificado de firma | R | • Dirección de la LCR no informada<br>• Error en el acceso a la LCR<br>• LCR inexistente |
| AC06 | 0125 | Certificado de firma revocado | R | - |
| AC07 | 0126 | Certificado raíz no corresponde al MIC | R | - |

### **AD - Firma Digital**
| ID | Código | Descripción | Estado | Observaciones |
|---|---|---|---|---|
| AD01 | 0140 | Firma difiere del estándar | R | • No fue firmado el documento completo<br>• Transform Algorithm no informado |
| AD02 | 0141 | Valor de la firma (SignatureValue) diferente del calculado por el PKI | R | • Certificado del PSC no habilitado<br>• Certificado revocado<br>• Error en LCR, etc. |
| AD03 | 0142 | RUC del certificado utilizado para firmar no pertenece al Contribuyente emisor | R | - |

### **AE - Validaciones Genéricas**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| AE01 | 0160 | XML malformado | R |
| AE02 | 0161 | Servidor de procesamiento momentáneamente sin respuesta | R |
| AE03 | 0162 | Servidor de procesamiento paralizado, sin tiempo de regreso | R |
| AE04 | 0163 | Versión del formato del WS no soportada | R |

### **AF - Mensajes de Control**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| AF01 | 0180 | Elemento deHeaderMsg inexistente en el SOAP Header | R |
| AF04 | 0183 | RUC del certificado utilizado en la conexión no pertenece a un contribuyente activo | R |

## 📡 **Códigos de Web Services Específicos**

### **BA - WS siRecepDE**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| BA01 | 0200 | Mensaje de datos de entrada del WS siRecepDE superior a 1000 KB | R |

### **BC - Área de Datos siRecepDE**  
| ID | Código | Descripción | Estado |
|---|---|---|---|
| BC01 | 0260 | Autorización del DE satisfactoria | N |

### **BD - WS siRecepLoteDE**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| BD01 | 0270 | Mensaje de datos de entrada del WS siRecepLoteDE superior a 10.000 KB | R |

### **BF - Área de Datos siRecepLoteDE**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| BF01 | 0300 | Lote recibido con éxito | A |
| BF02 | 0301 | Lote no encolado para procesamiento | R |

### **BS - WS siRecepEvento**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| BS01 | 0560 | Mensaje de datos de entrada del WS siRecepEvento superior a 1000 KB | R |

### **BU - Área de Datos siRecepEvento**
| ID | Código | Descripción | Estado |
|---|---|---|---|
| BU01 | 0600 | Evento registrado correctamente | A |

## 📄 **Códigos de Validación de Documentos Electrónicos**

### **Grupo A - Campos Firmados del DE (A001-A099)**
| N° | Val ID | Código | Mensaje | Estado | Observación |
|---|---|---|---|---|---|
| 1 | A002 | 1000 | CDC no correspondiente con las informaciones del XML | R | El CDC no es compatible con los campos C002, D101, D102, C005, C006, C007, D103, D002, B002, B004, A003 |
| 2 | A002a | 1001 | CDC duplicado | R | Ya fue autorizado otro documento con coincidencia simultánea de contenido de los campos del CDC |
| 3 | A002b | 1002 | Documento electrónico duplicado | R | Ya fue autorizado otro documento con coincidencia de Timbrado, Tipo de documento, Número, etc. |
| 4 | A003 | 1003 | DV del CDC inválido | R | Valor incorrecto del dígito verificador según algoritmo módulo 11 |
| 5 | A004a | 1004 | La fecha y hora de la firma digital es adelantada | R | La fecha y hora de la firma digital no debe ser posterior a la fecha y hora de SIFEN |
| 6 | A004b | 1005 | Transmisión extemporánea del DE | R | La transmisión del DE no debe exceder el tiempo de validación posterior parametrizado |

## 🔗 **Rangos de Códigos por Categoría**

### **Servicios Web (0000-0999)**
- **0000-0099**: Certificado de Transmisión (TLS)
- **0100-0139**: Forma del área de datos  
- **0140-0159**: Certificado digital y firma
- **0160-0199**: Validaciones genéricas
- **0200-0999**: Web Services específicos

### **Documentos Electrónicos (1000-2999)**
- **1000-1099**: Campos firmados del DE (Grupo A)
- **1100-1199**: Campos identificación del DE (Grupo AA)
- **1200-1299**: Campos operación del DE (Grupo B)
- **1300-1399**: Campos del timbrado (Grupo C)
- **1400-1999**: Datos generales (Grupo D)
- **2000-2399**: Campos específicos por tipo (Grupo E)
- **2400-2499**: Campos de subtotales (Grupo F)
- **2500-2599**: Campos generales (Grupo G)
- **2600-2699**: Campos DE asociado (Grupo H)

### **Eventos (3000-3999)**
- **3000-3099**: Eventos de cancelación
- **3100-3199**: Eventos de inutilización
- **3200-3299**: Eventos de conformidad/disconformidad
- **3300-3399**: Eventos de desconocimiento

## 💡 **Uso en Implementación**

```python
# Ejemplo de manejo de códigos de error
class SifenError(Exception):
    def __init__(self, codigo: str, mensaje: str, detalle: str = None):
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalle = detalle
        
    @classmethod
    def from_response_code(cls, codigo: str):
        """Crear error desde código de respuesta SIFEN"""
        error_map = {
            "0100": "Fallo de schema XML del área de datos",
            "0120": "Certificado inválido",
            "1000": "CDC no correspondiente con las informaciones del XML",
            "1001": "CDC duplicado",
            # ... mapeo completo
        }
        mensaje = error_map.get(codigo, f"Error desconocido: {codigo}")
        return cls(codigo, mensaje)

# Verificar si es error crítico
def es_error_critico(codigo: str) -> bool:
    """Determinar si el código representa un error crítico"""
    return codigo.startswith(("0100", "0120", "1000", "1001", "1002"))
```

---

**📝 Notas de Implementación:**
- Validar localmente antes de enviar a SIFEN para evitar errores comunes
- Implementar retry logic solo para errores temporales (016x, AE02, AE03)
- Los errores de certificado (AC) requieren intervención manual
- Los errores de schema (AB) indican problemas en la generación XML

**🔄 Última actualización**: Basado en Manual Técnico SIFEN v150