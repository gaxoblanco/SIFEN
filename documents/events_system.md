# Sistema de Eventos SIFEN v150

## 📋 **Introducción a los Eventos**

Los eventos en SIFEN permiten modificar el estado de los Documentos Tributarios Electrónicos (DTE) después de su aprobación. Los eventos se clasifican según quien los origina y su naturaleza.

### **Tipos de Eventos por Registro**
- **AUTOMÁTICO**: Generados por SIFEN automáticamente
- **REQUERIDO**: Solicitados por consumo de Web Services

### **Clasificación por Actor**
- **Eventos del Emisor**: Cancelación, Inutilización, Endoso
- **Eventos del Receptor**: Conformidad, Disconformidad, Desconocimiento, Notificación
- **Eventos de la SET**: Impugnación (futuro)

## 🎯 **Eventos del Emisor**

### **1. Inutilización de Número de DE**

#### **Descripción**
Evento para comunicar que un número de documento no fue utilizado o debe ser anulado antes de su aprobación.

#### **Situaciones de Uso**
- **Saltos en numeración**: Error en sistema de facturación
- **Errores técnicos**: Detección de errores de llenado
- **Rechazo SIFEN**: Cuando modificar implica cambio de CDC

#### **Reglas de Negocio**
| Concepto | Detalle |
|----------|---------|
| **Plazo** | Hasta 15 días del mes siguiente al hecho |
| **Límite temporal** | Hasta fecha límite de validez del timbrado |
| **Rango máximo** | Hasta 1000 números secuenciales |
| **Condición** | Números no deben existir como aprobados en SIFEN |
| **Estado permitido** | Solo DE no aprobados |

#### **Estructura XML**
```xml
<rGeVeInu>
  <dNumTim>12345678</dNumTim>              <!-- Número timbrado -->
  <dEst>001</dEst>                         <!-- Establecimiento -->
  <dPunExp>001</dPunExp>                   <!-- Punto expedición -->
  <dNumIn>0000001</dNumIn>                 <!-- Número inicial rango -->
  <dNumFin>0000010</dNumFin>               <!-- Número final rango -->
  <iTiDE>1</iTiDE>                         <!-- Tipo DE: 1=FE -->
  <mOtEve>Error en sistema, salto numeración</mOtEve>
</rGeVeInu>
```

### **2. Cancelación**

#### **Descripción**
Evento para cancelar un DTE ya aprobado cuando la transacción no se concreta.

#### **Reglas de Negocio**
| Tipo Documento | Plazo | Observaciones |
|----------------|-------|---------------|
| **Factura Electrónica (FE)** | 48 horas | Desde aprobación SIFEN |
| **Otros (AFE, NCE, NDE, NRE)** | 168 horas | Desde aprobación SIFEN |

#### **Restricciones**
- DTE debe estar aprobado en SIFEN
- No puede tener confirmación del receptor
- Para DTE con documentos asociados: cancelar desde el último hasta el inicial

#### **Motivos Comunes**
- Errores en la emisión del DE
- Mercadería no entregada al cliente
- Servicio no realizado al cliente

#### **Estructura XML**
```xml
<rGeVeCan>
  <Id>01234567890123456789012345678901234567890123</Id>  <!-- CDC del DTE -->
  <mOtEve>Mercadería no entregada por falta de stock</mOtEve>
</rGeVeCan>
```

### **3. Devolución y Ajuste de Precios**
- **Tipo**: Evento AUTOMÁTICO
- **Generado por**: Emisión de Notas de Crédito/Débito asociadas
- **Acción requerida**: Ninguna (automático)

### **4. Endoso de FE** *(Futuro)*
- **Estado**: En desarrollo
- **Propósito**: Transferencia de derechos del documento

## 🎯 **Eventos del Receptor**

### **1. Notificación de Recepción DE/DTE**

#### **Descripción**
Evento informativo para confirmar que el receptor recibió el documento.

#### **Reglas de Negocio**
| Concepto | Detalle |
|----------|---------|
| **Plazo** | 45 días desde fecha de emisión |
| **Alcance** | Todos los DE o DTE |
| **Modalidad** | WS Sincrónico o Portal SIFEN |
| **Tipo** | Evento informativo |

#### **Estructura XML**
```xml
<rGeVeNotRec>
  <Id>01234567890123456789012345678901234567890123</Id>  <!-- CDC -->
  <dFecEmi>2019-09-10T14:30:00</dFecEmi>                 <!-- Fecha emisión -->
  <dFecRecep>2019-09-12T10:15:00</dFecRecep>             <!-- Fecha recepción -->
</rGeVeNotRec>
```

### **2. Conformidad con el DTE**

#### **Descripción**
El receptor confirma estar conforme con el documento recibido.

#### **Tipos de Conformidad**
- **Conformidad Total**: Acepta completamente el DTE
- **Conformidad Parcial**: Acepta parcialmente (con observaciones)

#### **Reglas de Negocio**
| Concepto | Detalle |
|----------|---------|
| **Plazo** | 45 días desde fecha de emisión |
| **Alcance** | Todos los DTE |
| **Modalidad** | WS Sincrónico o Portal SIFEN |
| **Tipo** | Evento conclusivo |

### **3. Disconformidad con el DTE**

#### **Descripción**
El receptor manifiesta disconformidad con el documento recibido.

#### **Reglas de Negocio**
- **Plazo**: 45 días desde fecha de emisión
- **Justificación**: Campo de texto libre obligatorio
- **Efecto**: Bloquea cancelación por parte del emisor

### **4. Desconocimiento con el DE o DTE**

#### **Descripción**
El receptor declara no conocer el documento o no haber participado en la operación.

#### **Reglas de Negocio**
- **Plazo**: 45 días desde fecha de emisión
- **Gravedad**: Evento de mayor impacto
- **Investigación**: Puede generar investigación por parte de SET

## 🔄 **Relaciones entre Eventos del Receptor**

### **Matriz de Compatibilidad**
| Evento Inicial | Puede seguir con |
|----------------|------------------|
| **Notificación Recepción** | Conformidad Total/Parcial, Disconformidad, Desconocimiento |
| **Conformidad Parcial** | Conformidad Total, Disconformidad, Desconocimiento |
| **Conformidad Total** | ❌ Ningún evento adicional |
| **Disconformidad** | ❌ Ningún evento adicional |
| **Desconocimiento** | ❌ Ningún evento adicional |

### **Correcciones de Eventos** *(Tabla K)*
| Corrección | Actor | Modalidad | Plazo | Condiciones |
|------------|-------|-----------|-------|-------------|
| **Conformidad → Disconformidad** | Receptor | WS/Portal | 15 días del primer evento | DTE Aprobado + Justificación |
| **Disconformidad → Conformidad** | Receptor | WS/Portal | 15 días del primer evento | DTE Aprobado + Justificación |
| **Desconocimiento → Otro** | Receptor | WS/Portal | 15 días del primer evento | Solo un evento corrección |

## 📋 **Códigos de Tipo de Evento**

### **Eventos del Emisor**
| Código | Descripción | Estado |
|--------|-------------|--------|
| 1 | Cancelación | Activo |
| 2 | Inutilización | Activo |
| 3 | Endoso | Futuro |

### **Eventos del Receptor**
| Código | Descripción | Estado |
|--------|-------------|--------|
| 10 | Acuse del DE | Futuro |
| 11 | Conformidad del DE | Futuro |
| 12 | Disconformidad del DE | Futuro |
| 13 | Desconocimiento del DE | Futuro |

## 🔧 **Validaciones de Eventos**

### **Validaciones para Cancelación (4000-4010)**
| Código | Validación | Estado |
|--------|------------|--------|
| 4000 | Versión no corresponde | R |
| 4001 | CDC inválido | R |
| 4002 | CDC no existente en SIFEN | R |
| 4003 | CDC ya tiene el mismo evento | R |
| 4004 | CDC ya confirmado por receptor | R |
| 4006 | Firmador no autorizado | R |
| 4007 | Certificado revocado | R |
| 4008 | Fecha firma inválida | R |
| 4009 | Plazo FE extemporáneo (>48h) | R |
| 4010 | Plazo otros DE extemporáneo (>168h) | R |

### **Validaciones para Inutilización (4050-4099)**
| Código | Validación | Estado |
|--------|------------|--------|
| 4051 | Timbrado inválido para ambiente pruebas | R |
| 4052 | Rango excede máximo permitido (1000) | R |
| 4053 | Números ya utilizados en rango | R |
| 4054 | Fecha límite timbrado excedida | R |

## 💻 **Implementación en Código**

### **Estructura Base de Eventos**
```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional

class TipoEvento(Enum):
    CANCELACION = 1
    INUTILIZACION = 2
    ENDOSO = 3  # Futuro
    ACUSE_DE = 10  # Futuro
    CONFORMIDAD_DE = 11  # Futuro
    DISCONFORMIDAD_DE = 12  # Futuro
    DESCONOCIMIENTO_DE = 13  # Futuro

class ActorEvento(Enum):
    EMISOR = "emisor"
    RECEPTOR = "receptor"
    SET = "set"

class EstadoEvento(Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"

class EventoBase:
    def __init__(self, tipo: TipoEvento, cdc: str, motivo: str):
        self.id = self._generar_id()
        self.tipo = tipo
        self.cdc = cdc
        self.motivo = motivo
        self.fecha_firma = datetime.now()
        self.version_formato = "150"
        self.estado = EstadoEvento.PENDIENTE
    
    def _generar_id(self) -> str:
        """Generar ID único para el evento"""
        import uuid
        return str(uuid.uuid4().int)[:10]
```

### **Evento de Cancelación**
```python
class EventoCancelacion(EventoBase):
    def __init__(self, cdc: str, motivo: str):
        super().__init__(TipoEvento.CANCELACION, cdc, motivo)
        self.actor = ActorEvento.EMISOR
    
    def validar_plazo(self, fecha_aprobacion_dte: datetime, tipo_documento: str) -> bool:
        """Validar si está dentro del plazo permitido"""
        tiempo_transcurrido = self.fecha_firma - fecha_aprobacion_dte
        
        if tipo_documento.startswith("01"):  # Factura Electrónica
            return tiempo_transcurrido <= timedelta(hours=48)
        else:  # AFE, NCE, NDE, NRE
            return tiempo_transcurrido <= timedelta(hours=168)
    
    def generar_xml(self) -> str:
        """Generar XML del evento de cancelación"""
        return f"""
        <rGeVeCan>
            <Id>{self.cdc}</Id>
            <mOtEve>{self.motivo}</mOtEve>
        </rGeVeCan>
        """
```

### **Evento de Inutilización**
```python
class EventoInutilizacion(EventoBase):
    def __init__(self, timbrado: str, establecimiento: str, punto_expedicion: str, 
                 numero_inicio: str, numero_fin: str, tipo_de: int, motivo: str):
        # Para inutilización no se usa CDC individual
        super().__init__(TipoEvento.INUTILIZACION, "", motivo)
        self.timbrado = timbrado
        self.establecimiento = establecimiento.zfill(3)
        self.punto_expedicion = punto_expedicion.zfill(3)
        self.numero_inicio = numero_inicio.zfill(7)
        self.numero_fin = numero_fin.zfill(7)
        self.tipo_de = tipo_de
        self.actor = ActorEvento.EMISOR
    
    def validar_rango(self) -> tuple[bool, str]:
        """Validar que el rango sea válido"""
        inicio = int(self.numero_inicio)
        fin = int(self.numero_fin)
        
        if inicio > fin:
            return False, "Número inicio mayor que número fin"
        
        if (fin - inicio + 1) > 1000:
            return False, "Rango excede máximo de 1000 números"
        
        if inicio <= 0 or fin <= 0:
            return False, "Números deben ser positivos"
            
        return True, "Rango válido"
    
    def validar_plazo_mes_siguiente(self) -> bool:
        """Validar que esté dentro de los primeros 15 días del mes siguiente"""
        hoy = datetime.now()
        primer_dia_mes = hoy.replace(day=1)
        limite = primer_dia_mes.replace(day=15)
        
        return hoy <= limite
    
    def generar_xml(self) -> str:
        """Generar XML del evento de inutilización"""
        return f"""
        <rGeVeInu>
            <dNumTim>{self.timbrado}</dNumTim>
            <dEst>{self.establecimiento}</dEst>
            <dPunExp>{self.punto_expedicion}</dPunExp>
            <dNumIn>{self.numero_inicio}</dNumIn>
            <dNumFin>{self.numero_fin}</dNumFin>
            <iTiDE>{self.tipo_de}</iTiDE>
            <mOtEve>{self.motivo}</mOtEve>
        </rGeVeInu>
        """
```

### **Evento de Notificación Recepción**
```python
class EventoNotificacionRecepcion(EventoBase):
    def __init__(self, cdc: str, fecha_emision: datetime, fecha_recepcion: datetime):
        super().__init__(TipoEvento.ACUSE_DE, cdc, "Notificación de recepción")
        self.fecha_emision = fecha_emision
        self.fecha_recepcion = fecha_recepcion
        self.actor = ActorEvento.RECEPTOR
    
    def validar_plazo_45_dias(self) -> bool:
        """Validar que esté dentro de 45 días desde emisión"""
        tiempo_transcurrido = self.fecha_firma - self.fecha_emision
        return tiempo_transcurrido <= timedelta(days=45)
    
    def generar_xml(self) -> str:
        """Generar XML del evento de notificación"""
        return f"""
        <rGeVeNotRec>
            <Id>{self.cdc}</Id>
            <dFecEmi>{self.fecha_emision.strftime('%Y-%m-%dT%H:%M:%S')}</dFecEmi>
            <dFecRecep>{self.fecha_recepcion.strftime('%Y-%m-%dT%H:%M:%S')}</dFecRecep>
        </rGeVeNotRec>
        """
```

### **Gestor de Eventos**
```python
class GestorEventos:
    def __init__(self, sifen_client):
        self.client = sifen_client
        self.eventos_enviados = []
    
    async def cancelar_dte(self, cdc: str, motivo: str, 
                          fecha_aprobacion: datetime, tipo_documento: str) -> dict:
        """Enviar evento de cancelación"""
        evento = EventoCancelacion(cdc, motivo)
        
        # Validaciones
        if not evento.validar_plazo(fecha_aprobacion, tipo_documento):
            return {
                "success": False, 
                "error": "Fuera de plazo para cancelación",
                "codigo": "4009" if tipo_documento.startswith("01") else "4010"
            }
        
        # Generar XML completo del evento
        xml_evento = self._generar_xml_completo(evento)
        
        # Enviar a SIFEN
        try:
            response = await self.client.enviar_evento(xml_evento)
            evento.estado = EstadoEvento.APROBADO if response.success else EstadoEvento.RECHAZADO
            self.eventos_enviados.append(evento)
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def inutilizar_numeracion(self, timbrado: str, establecimiento: str, 
                                  punto_expedicion: str, numero_inicio: str, 
                                  numero_fin: str, tipo_de: int, motivo: str) -> dict:
        """Enviar evento de inutilización"""
        evento = EventoInutilizacion(
            timbrado, establecimiento, punto_expedicion,
            numero_inicio, numero_fin, tipo_de, motivo
        )
        
        # Validaciones
        rango_valido, mensaje = evento.validar_rango()
        if not rango_valido:
            return {"success": False, "error": mensaje, "codigo": "4052"}
        
        if not evento.validar_plazo_mes_siguiente():
            return {"success": False, "error": "Fuera de plazo (primeros 15 días del mes)", "codigo": "4054"}
        
        # Generar XML completo del evento
        xml_evento = self._generar_xml_completo(evento)
        
        # Enviar a SIFEN
        try:
            response = await self.client.enviar_evento(xml_evento)
            evento.estado = EstadoEvento.APROBADO if response.success else EstadoEvento.RECHAZADO
            self.eventos_enviados.append(evento)
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def notificar_recepcion(self, cdc: str, fecha_emision: datetime, 
                                fecha_recepcion: datetime) -> dict:
        """Enviar notificación de recepción (receptor)"""
        evento = EventoNotificacionRecepcion(cdc, fecha_emision, fecha_recepcion)
        
        # Validaciones
        if not evento.validar_plazo_45_dias():
            return {"success": False, "error": "Fuera de plazo (45 días)", "codigo": "4100"}
        
        # Generar XML completo del evento
        xml_evento = self._generar_xml_completo(evento)
        
        # Enviar a SIFEN
        try:
            response = await self.client.enviar_evento(xml_evento)
            evento.estado = EstadoEvento.APROBADO if response.success else EstadoEvento.RECHAZADO
            self.eventos_enviados.append(evento)
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generar_xml_completo(self, evento: EventoBase) -> str:
        """Generar XML completo del evento con estructura base"""
        xml_evento_especifico = evento.generar_xml()
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <rGesEve xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <rEve Id="{evento.id}">
                <dFecFirma>{evento.fecha_firma.strftime('%Y-%m-%dT%H:%M:%S')}</dFecFirma>
                <dVerFor>{evento.version_formato}</dVerFor>
                <dTiGDE>{evento.tipo.value}</dTiGDE>
                <gGroupTiEvt>
                    {xml_evento_especifico}
                </gGroupTiEvt>
            </rEve>
            <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
                <!-- Firma digital aquí -->
            </Signature>
        </rGesEve>
        """
```

## 🔍 **Web Services de Eventos**

### **Endpoint Principal**
```
Producción: https://sifen.set.gov.py/de/ws/eventos/evento.wsdl
Test: https://sifen-test.set.gov.py/de/ws/eventos/evento.wsdl
```

### **Método**: `siRecepEvento`
- **Input**: XML del evento firmado digitalmente
- **Output**: Respuesta con código de resultado
- **Tamaño máximo**: 1000 KB
- **Protocolo**: SOAP 1.2 sobre TLS 1.2

### **Estructura de Respuesta**
```xml
<resRecepEvento>
    <dCodRes>0600</dCodRes>        <!-- Código resultado -->
    <dMsgRes>Evento registrado correctamente</dMsgRes>
    <dFecProcEve>2019-09-10T15:30:00</dFecProcEve>  <!-- Fecha procesamiento -->
    <dIdEve>1234567890</dIdEve>    <!-- ID del evento en SIFEN -->
</resRecepEvento>
```

## 🎯 **Casos de Uso Comunes**

### **Caso 1: Error en Facturación**
```python
# Detectar error después de envío
async def manejar_error_facturacion():
    # 1. Verificar si el DE fue aprobado
    estado_de = await consultar_estado_documento(cdc)
    
    if estado_de == "APROBADO":
        # 2. Cancelar el DTE
        resultado = await gestor.cancelar_dte(
            cdc=cdc,
            motivo="Error en cálculo de impuestos detectado",
            fecha_aprobacion=estado_de.fecha_aprobacion,
            tipo_documento="01"  # FE
        )
        
        if resultado["success"]:
            print(f"DTE cancelado: {resultado}")
            # 3. Emitir nuevo documento corregido
            await emitir_documento_corregido()
        else:
            print(f"Error en cancelación: {resultado['error']}")
    else:
        # Si no está aprobado, inutilizar el número
        await gestor.inutilizar_numeracion(
            timbrado="12345678",
            establecimiento="001", 
            punto_expedicion="001",
            numero_inicio="0001234",
            numero_fin="0001234",
            tipo_de=1,  # FE
            motivo="Error en sistema antes de aprobación"
        )
```

### **Caso 2: Salto en Numeración**
```python
async def manejar_salto_numeracion():
    # Detectar salto: último usado 0001230, próximo 0001235
    numeros_perdidos = ["0001231", "0001232", "0001233", "0001234"]
    
    resultado = await gestor.inutilizar_numeracion(
        timbrado="12345678",
        establecimiento="001",
        punto_expedicion="001", 
        numero_inicio="0001231",
        numero_fin="0001234",
        tipo_de=1,  # FE
        motivo="Salto en numeración por error en sistema de facturación"
    )
    
    if resultado["success"]:
        print("Numeración inutilizada correctamente")
        # Continuar con próximo número: 0001235
    else:
        print(f"Error: {resultado['error']}")
```

### **Caso 3: Receptor Notifica Recepción**
```python
async def receptor_notifica_recepcion():
    # Receptor confirma haber recibido el documento
    resultado = await gestor.notificar_recepcion(
        cdc="01234567890123456789012345678901234567890123",
        fecha_emision=datetime(2019, 9, 10, 14, 30, 0),
        fecha_recepcion=datetime(2019, 9, 12, 10, 15, 0)
    )
    
    if resultado["success"]:
        print("Recepción notificada exitosamente")
    else:
        print(f"Error: {resultado['error']}")
```

## ⚠️ **Consideraciones Importantes**

### **Plazos Críticos**
- **Cancelación FE**: 48 horas máximo
- **Cancelación otros**: 168 horas máximo  
- **Inutilización**: Primeros 15 días del mes siguiente
- **Eventos receptor**: 45 días desde emisión

### **Validaciones Clave**
- CDC debe existir y estar aprobado para cancelación
- Números no deben existir para inutilización
- Firmador debe ser el emisor original
- Certificado debe estar vigente en fecha de firma

### **Limitaciones**
- Máximo 1000 números por inutilización
- Solo un evento de corrección por evento receptor
- No se puede cancelar DTE con confirmación del receptor

---

**📝 Notas de Implementación:**
- Implementar validaciones locales antes de envío
- Mantener registro de eventos enviados para auditoría
- Manejar códigos de error específicos para cada tipo de evento
- Integrar con sistema de notificaciones para eventos críticos

**🔄 Última actualización**: Basado en Manual Técnico SIFEN v150