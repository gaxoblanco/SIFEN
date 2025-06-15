# 🎯 PROMPT PARA GENERAR ESQUEMA XSD SIFEN v150

------------------------------------------
# Reemplazar en el prompt:
[NOMBRE_ESQUEMA] → ej: "siRecepDE_v150"
------------------------------------------

## CONTEXTO
Sistema de facturación electrónica Paraguay SIFEN v150. Ya tengo `DE_v150.xsd` implementado y necesito crear esquemas de web services paso a paso.

## TAREA
**Genera el esquema XSD: `[NOMBRE_ESQUEMA].xsd`**

## ESPECIFICACIONES TÉCNICAS

### Estructura Base Obligatoria
```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://ekuatia.set.gov.py/sifen/xsd"
           xmlns="http://ekuatia.set.gov.py/sifen/xsd"
           elementFormDefault="qualified"
           version="1.5.0">
    
    <!-- CONTENIDO AQUÍ -->
    
</xs:schema>
```

### Elementos por Tipo de Esquema

#### **Para Requests (siRecep*, siCons*, SiRecep*)**
- Root element: Nombre del servicio
- Elementos obligatorios: `dId`, `dFecFirma`, `dSisFact`
- Contenido específico del request

#### **Para Responses (resRecep*, resCons*, resResult*)**  
- Root element: Nombre de respuesta
- Elementos obligatorios: `dCodRes`, `dMsgRes`, `dFecProceso`
- Datos específicos de respuesta

#### **Para Protocolos (ProtProces*)**
- Root element: Nombre protocolo
- Estado procesamiento y tracking

### Patrones de Validación
```xml
<!-- RUC paraguayo -->
<xs:pattern value="\d{8}-\d"/>

<!-- CDC 44 dígitos -->
<xs:pattern value="\d{44}"/>

<!-- Código SIFEN -->
<xs:pattern value="[0-9]{4}"/>

<!-- Fecha ISO -->
<xs:pattern value="\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"/>
```

### Códigos SIFEN Importantes
- **0260**: Aprobado
- **1005**: Aprobado con observaciones  
- **1000-4999**: Rechazado
- **Tipos documento**: 1=FE, 4=AFE, 5=NCE, 6=NDE, 7=NRE

### Template Base
```xml
<xs:element name="[ELEMENTO_RAIZ]">
    <xs:complexType>
        <xs:sequence>
            <xs:element name="dId" type="xs:string" minOccurs="1">
                <xs:annotation>
                    <xs:documentation>Identificador único</xs:documentation>
                </xs:annotation>
            </xs:element>
            <!-- Elementos específicos -->
        </xs:sequence>
    </xs:complexType>
</xs:element>
```

## REQUERIMIENTOS
1. **Namespace oficial**: `http://ekuatia.set.gov.py/sifen/xsd`
2. **Versión**: 1.5.0
3. **Documentación**: Annotations en español
4. **Tipos**: Usar restricciones apropiadas
5. **Validaciones**: Patterns según Manual Técnico v150

**Genera un esquema XSD completo y funcional siguiendo estas especificaciones.**