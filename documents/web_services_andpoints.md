# Web Services SIFEN v150

## 📋 **Introducción a Web Services SIFEN**

SIFEN utiliza **protocolo SOAP 1.2** sobre **TLS 1.2** para la comunicación entre contribuyentes y la SET. Todos los servicios requieren **autenticación mutua** con certificados digitales PSC válidos.

### **Características Técnicas**
- **Protocolo**: SOAP 1.2 
- **Transporte**: HTTPS con TLS 1.2 obligatorio
- **Encoding**: UTF-8 únicamente
- **Timeout**: 60 segundos máximo
- **Certificados**: PSC Paraguay (Mutual TLS)
- **Namespace**: `http://ekuatia.set.gov.py/sifen/xsd`

## 🌐 **Endpoints de Servicios**

### **Producción**
```
https://sifen.set.gov.py/de/ws/sync/recibe.wsdl         # Individual
https://sifen.set.gov.py/de/ws/async/recibe-lote.wsdl   # Lotes
https://sifen.set.gov.py/de/ws/consultas/consulta.wsdl  # Consultas
https://sifen.set.gov.py/de/ws/eventos/evento.wsdl      # Eventos
```

### **Test/Desarrollo**
```
https://sifen-test.set.gov.py/de/ws/sync/recibe.wsdl         # Individual
https://sifen-test.set.gov.py/de/ws/async/recibe-lote.wsdl   # Lotes  
https://sifen-test.set.gov.py/de/ws/consultas/consulta.wsdl  # Consultas
https://sifen-test.set.gov.py/de/ws/eventos/evento.wsdl      # Eventos
```

## 📨 **1. WS Recepción Documento Electrónico (siRecepDE)**

### **Información General**
- **Función**: Recibir un documento electrónico individual
- **Proceso**: Síncrono
- **Método**: `SiRecepDE`
- **Límite**: 1000 KB por mensaje
- **Timeout**: 60 segundos

### **Request - siRecepDE_v150.xsd**
```xml
<!-- Schema XML 2: siRecepDE_v150.xsd -->
<rEnviDe>
    <dId>1</dId>                           <!-- ID control envío (1-15 dígitos) -->
    <xDe>                                  <!-- XML del DE firmado -->
        <rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
            <!-- Documento electrónico completo firmado -->
        </rDE>
    </xDe>
</rEnviDe>
```

#### **Estructura del Request**
| Campo | Tipo | Longitud | Ocurrencia | Descripción |
|-------|------|----------|------------|-------------|
| **rEnviDe** | G | - | 1-1 | Elemento raíz |
| **dId** | N | 1-15 | 1-1 | ID secuencial autoincremental del emisor |
| **xDe** | XML | - | 1-1 | XML del DE firmado digitalmente |

### **Response - resRecepDE_v150.xsd**
```xml
<!-- Schema XML 3: resRecepDE_v150.xsd -->
<rRetEnviDe>
    <dFecProc>2019-09-10T14:30:00</dFecProc>  <!-- Fecha procesamiento -->
    <dCodRes>0260</dCodRes>                    <!-- Código resultado -->
    <dMsgRes>Autorización del DE satisfactoria</dMsgRes> <!-- Mensaje -->
    <dProtAut>1234567890</dProtAut>            <!-- Número transacción (si aprobado) -->
    <Id>01234567890123456789012345678901234567890123</Id> <!-- CDC -->
</rRetEnviDe>
```

#### **Códigos de Respuesta Principales**
| Código | Mensaje | Estado | Descripción |
|--------|---------|--------|-------------|
| **0260** | Autorización del DE satisfactoria | A | Documento aprobado |
| **1005** | Transmisión extemporánea del DE | AO | Aprobado con observación |
| **1000** | CDC no correspondiente con XML | R | Error en CDC |
| **1001** | CDC duplicado | R | CDC ya utilizado |
| **0200** | Mensaje superior a 1000 KB | R | Excede límite tamaño |

### **Flujo de Procesamiento**
1. **Validación inicial**: Tamaño, estructura SOAP, certificado TLS
2. **Validación XML**: Schema, encoding UTF-8, namespace
3. **Validación firma**: Certificado PSC, firma digital válida
4. **Validación negocio**: Campos obligatorios, cálculos, códigos
5. **Aprobación**: Generación de número de transacción y almacenamiento

## 📦 **2. WS Recepción Lote DE (siRecepLoteDE)**

### **Información General**
- **Función**: Recibir lote de documentos electrónicos (hasta 50)
- **Proceso**: Asíncrono
- **Método**: `SiRecepLoteDE`
- **Límite**: 10.000 KB por lote
- **Tiempo procesamiento**: 3-15 minutos según tamaño

### **Request - SiRecepLoteDE_v150.xsd**
```xml
<!-- Schema XML 5: SiRecepLoteDE_v150.xsd -->
<rEnviLoteDe>
    <dId>1</dId>                           <!-- ID control envío -->
    <dFecEnvio>2019-09-10T14:30:00</dFecEnvio> <!-- Fecha envío lote -->
    <xDe>                                  <!-- Contenedor documentos -->
        <!-- Hasta 50 documentos electrónicos firmados -->
        <rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">...</rDE>
        <rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">...</rDE>
        <!-- ... más documentos ... -->
    </xDe>
</rEnviLoteDe>
```

#### **Estructura del Request**
| Campo | Tipo | Longitud | Ocurrencia | Descripción |
|-------|------|----------|------------|-------------|
| **rEnviLoteDe** | G | - | 1-1 | Elemento raíz |
| **dId** | N | 1-15 | 1-1 | ID control del lote |
| **dFecEnvio** | F | 19 | 1-1 | Fecha y hora de envío |
| **xDe** | XML | - | 1-50 | Contenedor con documentos |

### **Response - resRecepLoteDE_v150.xsd**
```xml
<!-- Schema XML 6: resRecepLoteDE_v150.xsd -->
<rRetEnviLoteDe>
    <dFecProc>2019-09-10T14:35:00</dFecProc>   <!-- Fecha procesamiento -->
    <dCodRes>0300</dCodRes>                     <!-- Código resultado -->
    <dMsgRes>Lote recibido con éxito</dMsgRes>  <!-- Mensaje -->
    <dProtAut>LOT123456789</dProtAut>           <!-- Número de lote -->
</rRetEnviLoteDe>
```

#### **Códigos de Respuesta del Lote**
| Código | Mensaje | Estado | Descripción |
|--------|---------|--------|-------------|
| **0300** | Lote recibido con éxito | A | Lote encolado para procesamiento |
| **0301** | Lote no encolado para procesamiento | R | Error al encolar |
| **0270** | Mensaje superior a 10.000 KB | R | Excede límite tamaño |

### **Flujo Asíncrono**
1. **Envío del lote** → Respuesta inmediata con número de lote
2. **Procesamiento** → SIFEN procesa cada documento (3-15 min)
3. **Consulta resultado** → Usar `siResultLoteDE` con número de lote

## 🔍 **3. WS Consulta Resultado Lote (siResultLoteDE)**

### **Información General**
- **Función**: Consultar estado y resultados de un lote enviado
- **Proceso**: Síncrono
- **Método**: `SiResultLoteDE`

### **Request - SiResultLoteDE_v150.xsd**
```xml
<!-- Schema XML 7: SiResultLoteDE_v150.xsd -->
<rEnviConsLoteDe>
    <dId>1</dId>                    <!-- ID control -->
    <dProtAut>LOT123456789</dProtAut> <!-- Número de lote -->
</rEnviConsLoteDe>
```

### **Response - resResultLoteDE_v150.xsd**
```xml
<!-- Schema XML 8: resResultLoteDE_v150.xsd -->
<rResEnviConsLoteDe>
    <dFecProc>2019-09-10T14:45:00</dFecProc>    <!-- Fecha procesamiento -->
    <dCodResLot>0362</dCodResLot>                <!-- Código resultado lote -->
    <dMsgResLot>Lote procesado correctamente</dMsgResLot>
    
    <!-- Resultado por cada documento -->
    <gResProcLote>
        <id>01234567890123456789012345678901234567890123</id> <!-- CDC -->
        <dEstRes>Aprobado</dEstRes>              <!-- Estado -->
        <dProtAut>1234567890</dProtAut>          <!-- Número transacción -->
        <gResProc>
            <dCodRes>0260</dCodRes>              <!-- Código resultado -->
            <dMsgRes>Autorización del DE satisfactoria</dMsgRes>
        </gResProc>
    </gResProcLote>
    
    <!-- Más documentos... -->
</rResEnviConsLoteDe>
```

#### **Estados del Lote**
| Código | Estado | Descripción |
|--------|--------|-------------|
| **0360** | En procesamiento | Lote en cola de procesamiento |
| **0361** | Procesamiento finalizado con errores | Algunos documentos rechazados |
| **0362** | Procesamiento finalizado exitosamente | Todos los documentos procesados |

## 📄 **4. WS Consulta DE (siConsDE)**

### **Información General**
- **Función**: Consultar un documento electrónico por CDC
- **Proceso**: Síncrono  
- **Método**: `SiConsDE`

### **Request - siConsDE_v150.xsd**
```xml
<!-- Schema XML 9: siConsDE_v150.xsd -->
<rEnviConsDe>
    <dId>1</dId>                                      <!-- ID control -->
    <dCDC>01234567890123456789012345678901234567890123</dCDC> <!-- CDC consulta -->
</rEnviConsDe>
```

### **Response - resConsDE_v150.xsd**
```xml
<!-- Schema XML 10: resConsDE_v150.xsd -->
<rRetEnviConsDe>
    <dFecProc>2019-09-10T14:30:00</dFecProc>     <!-- Fecha procesamiento -->
    <dCodRes>0280</dCodRes>                       <!-- Código resultado -->
    <dMsgRes>Consulta realizada correctamente</dMsgRes>
    
    <!-- Datos del documento (si encontrado) -->
    <gResProcCons>
        <dFecEmi>2019-09-10</dFecEmi>             <!-- Fecha emisión -->
        <dRucEm>12345678</dRucEm>                 <!-- RUC emisor -->
        <dDVEm>9</dDVEm>                          <!-- DV emisor -->
        <dNomEm>Empresa Ejemplo SAE</dNomEm>       <!-- Nombre emisor -->
        <iTiDE>1</iTiDE>                          <!-- Tipo documento -->
        <dNumDoc>0000001</dNumDoc>                <!-- Número documento -->
        <dTotGralOpe>110000</dTotGralOpe>         <!-- Total operación -->
        <dTotIVA>10000</dTotIVA>                  <!-- Total IVA -->
        <cEstDE>1</cEstDE>                        <!-- Estado DE -->
        <dDesEstDE>Aprobado</dDesEstDE>           <!-- Descripción estado -->
    </gResProcCons>
</rRetEnviConsDe>
```

#### **Estados del Documento**
| Código | Estado | Descripción |
|--------|--------|-------------|
| **1** | Aprobado | Documento aprobado y válido |
| **2** | Aprobado con observación | Aprobado pero con observaciones |
| **3** | Rechazado | Documento rechazado |
| **4** | Cancelado | Documento cancelado por emisor |

## 👤 **5. WS Consulta RUC (siConsRUC)**

### **Información General**
- **Función**: Consultar datos de un RUC contribuyente
- **Proceso**: Síncrono
- **Método**: `SiConsRUC`

### **Request - siConsRUC_v150.xsd**
```xml
<!-- Schema XML 15: siConsRUC_v150.xsd -->
<rEnviConsRUC>
    <dId>1</dId>                    <!-- ID control -->
    <dRUC>12345678</dRUC>           <!-- RUC a consultar -->
    <dDV>9</dDV>                    <!-- Dígito verificador -->
</rEnviConsRUC>
```

### **Response - resConsRUC_v150.xsd**
```xml
<!-- Schema XML 16: resConsRUC_v150.xsd -->
<rRetEnviConsRUC>
    <dFecProc>2019-09-10T14:30:00</dFecProc>     <!-- Fecha procesamiento -->
    <dCodRes>0420</dCodRes>                       <!-- Código resultado -->
    <dMsgRes>Consulta realizada correctamente</dMsgRes>
    
    <!-- Datos del RUC (si encontrado) -->
    <gResProcConsRUC>
        <dRUC>12345678</dRUC>                     <!-- RUC -->
        <dDV>9</dDV>                              <!-- DV -->
        <dNomCont>Empresa Ejemplo SAE</dNomCont>   <!-- Nombre contribuyente -->
        <cEstCont>1</cEstCont>                    <!-- Estado contribuyente -->
        <dDesEstCont>Activo</dDesEstCont>         <!-- Descripción estado -->
        <cTipCont>2</cTipCont>                    <!-- Tipo contribuyente -->
        <dDesTipCont>Persona Jurídica</dDesTipCont>
        <dFecActEst>2019-01-15</dFecActEst>       <!-- Fecha actualización estado -->
    </gResProcConsRUC>
</rRetEnviConsRUC>
```

#### **Estados del Contribuyente**
| Código | Estado | Descripción |
|--------|--------|-------------|
| **1** | Activo | Contribuyente activo |
| **2** | Suspendido | Contribuyente suspendido temporalmente |
| **3** | Cancelado | Contribuyente dado de baja |
| **4** | Bloqueado | Contribuyente bloqueado |

## 📋 **6. WS Recepción Evento (siRecepEvento)**

### **Información General**
- **Función**: Registrar eventos (cancelación, inutilización, etc.)
- **Proceso**: Síncrono
- **Método**: `siRecepEvento`  
- **Límite**: 1000 KB por mensaje

### **Request - siRecepEvento_v150.xsd**
```xml
<!-- Schema XML 13: siRecepEvento_v150.xsd -->
<rEnviEventoDe>
    <dId>1</dId>                    <!-- ID control -->
    <dEvReg>                        <!-- Evento a registrar -->
        <rGesEve>
            <rEve Id="12345">
                <dFecFirma>2019-09-10T14:30:00</dFecFirma>
                <dVerFor>150</dVerFor>
                <dTiGDE>1</dTiGDE>   <!-- Tipo evento: 1=Cancelación -->
                <gGroupTiEvt>
                    <rGeVeCan>
                        <Id>01234567890123456789012345678901234567890123</Id>
                        <mOtEve>Error en facturación</mOtEve>
                    </rGeVeCan>
                </gGroupTiEvt>
            </rEve>
            <Signature>...</Signature> <!-- Firma digital del evento -->
        </rGesEve>
    </dEvReg>
</rEnviEventoDe>
```

### **Response - resRecepEvento_v150.xsd**
```xml
<!-- Schema XML 14: resRecepEvento_v150.xsd -->
<rRetEnviEventoDe>
    <dFecProc>2019-09-10T14:35:00</dFecProc>     <!-- Fecha procesamiento -->
    <gResProcEVe>
        <dEstRes>Aprobado</dEstRes>               <!-- Estado resultado -->
        <dProtAut>1234567890</dProtAut>           <!-- Número transacción -->
        <id>12345</id>                            <!-- ID evento -->
        <gResProc>
            <dCodRes>0600</dCodRes>               <!-- Código resultado -->
            <dMsgRes>Evento registrado correctamente</dMsgRes>
        </gResProc>
    </gResProcEVe>
</rRetEnviEventoDe>
```

#### **Códigos de Evento**
| Código | Evento | Actor | Descripción |
|--------|--------|-------|-------------|
| **1** | Cancelación | Emisor | Cancelar DTE aprobado |
| **2** | Inutilización | Emisor | Inutilizar numeración |
| **10** | Notificación recepción | Receptor | Confirmar recepción |
| **11** | Conformidad | Receptor | Conformidad con DTE |
| **12** | Disconformidad | Receptor | Disconformidad con DTE |

## 💻 **Implementación en Código**

### **Cliente SOAP Base**
```python
import zeep
from zeep.wsse.username import UsernameToken
import ssl
import requests
from datetime import datetime
from typing import Dict, Optional, Any

class SifenSOAPClient:
    """Cliente SOAP para servicios SIFEN"""
    
    def __init__(self, ambiente: str = "test", cert_path: str = None, 
                 cert_password: str = None):
        self.ambiente = ambiente
        self.cert_path = cert_path
        self.cert_password = cert_password
        
        # URLs según ambiente
        if ambiente == "prod":
            self.base_url = "https://sifen.set.gov.py"
        else:
            self.base_url = "https://sifen-test.set.gov.py"
        
        # Configurar sesión con certificados
        self.session = self._configure_session()
    
    def _configure_session(self) -> requests.Session:
        """Configurar sesión HTTP con certificados y TLS 1.2"""
        session = requests.Session()
        
        # Configurar certificado cliente
        if self.cert_path:
            session.cert = (self.cert_path, self.cert_password)
        
        # Forzar TLS 1.2
        session.mount('https://', self._get_tls_adapter())
        
        # Headers obligatorios
        session.headers.update({
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '',
            'User-Agent': 'SIFEN-Client/1.0'
        })
        
        return session
    
    def _get_tls_adapter(self):
        """Adapter para forzar TLS 1.2"""
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context
        
        class TLS12HTTPAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                context = create_urllib3_context()
                context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                kwargs['ssl_context'] = context
                return super().init_poolmanager(*args, **kwargs)
        
        return TLS12HTTPAdapter()
    
    def _create_client(self, wsdl_url: str) -> zeep.Client:
        """Crear cliente Zeep con configuración SIFEN"""
        transport = zeep.Transport(session=self.session)
        settings = zeep.Settings(
            strict=False,
            xml_huge_tree=True,
            force_https=True
        )
        
        return zeep.Client(wsdl_url, transport=transport, settings=settings)
```

### **Servicio de Envío Individual**
```python
class SifenEnvioIndividual(SifenSOAPClient):
    """Servicio para envío individual de documentos"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wsdl_url = f"{self.base_url}/de/ws/sync/recibe.wsdl"
        self.client = self._create_client(self.wsdl_url)
    
    async def enviar_documento(self, xml_de_firmado: str, 
                              id_control: int = None) -> Dict[str, Any]:
        """Enviar documento electrónico individual"""
        
        # Generar ID de control si no se proporciona
        if id_control is None:
            id_control = int(datetime.now().timestamp())
        
        # Preparar request
        request_data = {
            'rEnviDe': {
                'dId': id_control,
                'xDe': xml_de_firmado
            }
        }
        
        try:
            # Llamar al servicio
            response = self.client.service.SiRecepDE(**request_data)
            
            # Procesar respuesta
            return self._procesar_respuesta_individual(response)
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error en envío: {str(e)}",
                'codigo': 'CLIENT_ERROR'
            }
    
    def _procesar_respuesta_individual(self, response) -> Dict[str, Any]:
        """Procesar respuesta del servicio individual"""
        try:
            return {
                'success': response.dCodRes == '0260',
                'codigo': response.dCodRes,
                'mensaje': response.dMsgRes,
                'fecha_procesamiento': response.dFecProc,
                'numero_transaccion': getattr(response, 'dProtAut', None),
                'cdc': getattr(response, 'Id', None),
                'aprobado': response.dCodRes in ['0260'],
                'aprobado_con_observacion': response.dCodRes in ['1005'],
                'rechazado': not response.dCodRes in ['0260', '1005']
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error procesando respuesta: {str(e)}",
                'raw_response': str(response)
            }
```

### **Servicio de Lotes**
```python
class SifenEnvioLotes(SifenSOAPClient):
    """Servicio para envío por lotes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wsdl_url_envio = f"{self.base_url}/de/ws/async/recibe-lote.wsdl"
        self.wsdl_url_consulta = f"{self.base_url}/de/ws/consultas/consulta.wsdl"
    
    async def enviar_lote(self, documentos_xml: list, 
                         id_control: int = None) -> Dict[str, Any]:
        """Enviar lote de documentos (máximo 50)"""
        
        if len(documentos_xml) > 50:
            return {
                'success': False,
                'error': 'Lote excede máximo de 50 documentos',
                'codigo': 'LOTE_EXCEDE_LIMITE'
            }
        
        if id_control is None:
            id_control = int(datetime.now().timestamp())
        
        # Crear cliente para envío
        client_envio = self._create_client(self.wsdl_url_envio)
        
        # Preparar request
        request_data = {
            'rEnviLoteDe': {
                'dId': id_control,
                'dFecEnvio': datetime.now().isoformat(),
                'xDe': documentos_xml
            }
        }
        
        try:
            response = client_envio.service.SiRecepLoteDE(**request_data)
            
            return {
                'success': response.dCodRes == '0300',
                'codigo': response.dCodRes,
                'mensaje': response.dMsgRes,
                'numero_lote': getattr(response, 'dProtAut', None),
                'fecha_procesamiento': response.dFecProc
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error enviando lote: {str(e)}",
                'codigo': 'CLIENT_ERROR'
            }
    
    async def consultar_resultado_lote(self, numero_lote: str) -> Dict[str, Any]:
        """Consultar resultado de procesamiento de lote"""
        
        # Crear cliente para consulta
        client_consulta = self._create_client(self.wsdl_url_consulta)
        
        request_data = {
            'rEnviConsLoteDe': {
                'dId': int(datetime.now().timestamp()),
                'dProtAut': numero_lote
            }
        }
        
        try:
            response = client_consulta.service.SiResultLoteDE(**request_data)
            
            # Procesar resultados por documento
            resultados_documentos = []
            if hasattr(response, 'gResProcLote'):
                for resultado in response.gResProcLote:
                    resultados_documentos.append({
                        'cdc': resultado.id,
                        'estado': resultado.dEstRes,
                        'numero_transaccion': getattr(resultado, 'dProtAut', None),
                        'codigo_resultado': resultado.gResProc.dCodRes,
                        'mensaje_resultado': resultado.gResProc.dMsgRes,
                        'aprobado': resultado.dEstRes == 'Aprobado'
                    })
            
            return {
                'success': True,
                'codigo_lote': response.dCodResLot,
                'mensaje_lote': response.dMsgResLot,
                'fecha_procesamiento': response.dFecProc,
                'estado_procesamiento': self._determinar_estado_lote(response.dCodResLot),
                'documentos': resultados_documentos,
                'total_documentos': len(resultados_documentos),
                'aprobados': len([d for d in resultados_documentos if d['aprobado']]),
                'rechazados': len([d for d in resultados_documentos if not d['aprobado']])
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error consultando lote: {str(e)}",
                'codigo': 'CLIENT_ERROR'
            }
    
    def _determinar_estado_lote(self, codigo: str) -> str:
        """Determinar estado de procesamiento del lote"""
        estados = {
            '0360': 'En procesamiento',
            '0361': 'Finalizado con errores', 
            '0362': 'Finalizado exitosamente'
        }
        return estados.get(codigo, 'Estado desconocido')
```

### **Servicio de Consultas**
```python
class SifenConsultas(SifenSOAPClient):
    """Servicio para consultas de documentos y RUC"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wsdl_url = f"{self.base_url}/de/ws/consultas/consulta.wsdl"
        self.client = self._create_client(self.wsdl_url)
    
    async def consultar_documento(self, cdc: str) -> Dict[str, Any]:
        """Consultar documento por CDC"""
        
        request_data = {
            'rEnviConsDe': {
                'dId': int(datetime.now().timestamp()),
                'dCDC': cdc
            }
        }
        
        try:
            response = self.client.service.SiConsDE(**request_data)
            
            # Procesar datos del documento si existe
            documento = None
            if hasattr(response, 'gResProcCons'):
                doc = response.gResProcCons
                documento = {
                    'fecha_emision': doc.dFecEmi,
                    'ruc_emisor': doc.dRucEm,
                    'dv_emisor': doc.dDVEm,
                    'nombre_emisor': doc.dNomEm,
                    'tipo_documento': doc.iTiDE,
                    'numero_documento': doc.dNumDoc,
                    'total_operacion': doc.dTotGralOpe,
                    'total_iva': doc.dTotIVA,
                    'estado_codigo': doc.cEstDE,
                    'estado_descripcion': doc.dDesEstDE,
                    'existe': True,
                    'valido': doc.cEstDE in ['1', '2']  # Aprobado o Aprobado con observación
                }
            
            return {
                'success': response.dCodRes == '0280',
                'codigo': response.dCodRes,
                'mensaje': response.dMsgRes,
                'fecha_procesamiento': response.dFecProc,
                'documento': documento,
                'encontrado': documento is not None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error consultando documento: {str(e)}",
                'codigo': 'CLIENT_ERROR'
            }
    
    async def consultar_ruc(self, ruc: str, dv: str) -> Dict[str, Any]:
        """Consultar datos de RUC"""
        
        request_data = {
            'rEnviConsRUC': {
                'dId': int(datetime.now().timestamp()),
                'dRUC': ruc,
                'dDV': dv
            }
        }
        
        try:
            response = self.client.service.SiConsRUC(**request_data)
            
            # Procesar datos del RUC si existe
            contribuyente = None
            if hasattr(response, 'gResProcConsRUC'):
                cont = response.gResProcConsRUC
                contribuyente = {
                    'ruc': cont.dRUC,
                    'dv': cont.dDV,
                    'nombre': cont.dNomCont,
                    'estado_codigo': cont.cEstCont,
                    'estado_descripcion': cont.dDesEstCont,
                    'tipo_contribuyente_codigo': cont.cTipCont,
                    'tipo_contribuyente_descripcion': cont.dDesTipCont,
                    'fecha_actualizacion': cont.dFecActEst,
                    'activo': cont.cEstCont == '1',
                    'existe': True
                }
            
            return {
                'success': response.dCodRes == '0420',
                'codigo': response.dCodRes,
                'mensaje': response.dMsgRes,
                'fecha_procesamiento': response.dFecProc,
                'contribuyente': contribuyente,
                'encontrado': contribuyente is not None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error consultando RUC: {str(e)}",
                'codigo': 'CLIENT_ERROR'
            }
```

### **Servicio de Eventos**
```python
class SifenEventos(SifenSOAPClient):
    """Servicio para registro de eventos"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wsdl_url = f"{self.base_url}/de/ws/eventos/evento.wsdl"
        self.client = self._create_client(self.wsdl_url)
    
    async def registrar_evento(self, xml_evento_firmado: str, 
                              id_control: int = None) -> Dict[str, Any]:
        """Registrar evento (cancelación, inutilización, etc.)"""
        
        if id_control is None:
            id_control = int(datetime.now().timestamp())
        
        request_data = {
            'rEnviEventoDe': {
                'dId': id_control,
                'dEvReg': xml_evento_firmado
            }
        }
        
        try:
            response = self.client.service.siRecepEvento(**request_data)
            
            # Procesar respuesta del evento
            evento_resultado = None
            if hasattr(response, 'gResProcEVe'):
                evt = response.gResProcEVe
                evento_resultado = {
                    'estado': evt.dEstRes,
                    'numero_transaccion': getattr(evt, 'dProtAut', None),
                    'id_evento': evt.id,
                    'codigo_resultado': evt.gResProc.dCodRes,
                    'mensaje_resultado': evt.gResProc.dMsgRes,
                    'registrado': evt.dEstRes == 'Aprobado'
                }
            
            return {
                'success': evento_resultado and evento_resultado['registrado'],
                'fecha_procesamiento': response.dFecProc,
                'evento': evento_resultado
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error registrando evento: {str(e)}",
                'codigo': 'CLIENT_ERROR'
            }
```

## 🔧 **Cliente Unificado SIFEN**

### **Orquestador Principal**
```python
class SifenClient:
    """Cliente principal para todos los servicios SIFEN"""
    
    def __init__(self, ambiente: str = "test", cert_path: str = None, 
                 cert_password: str = None, timeout: int = 60):
        
        # Configuración
        self.ambiente = ambiente
        self.timeout = timeout
        
        # Servicios especializados
        self.envio_individual = SifenEnvioIndividual(ambiente, cert_path, cert_password)
        self.envio_lotes = SifenEnvioLotes(ambiente, cert_path, cert_password)
        self.consultas = SifenConsultas(ambiente, cert_path, cert_password)
        self.eventos = SifenEventos(ambiente, cert_path, cert_password)
        
        # Cache para consultas frecuentes
        self._cache_ruc = {}
        self._cache_documentos = {}
    
    # Métodos de envío
    async def enviar_documento(self, xml_firmado: str) -> Dict[str, Any]:
        """Enviar documento individual"""
        return await self.envio_individual.enviar_documento(xml_firmado)
    
    async def enviar_lote(self, documentos_xml: list) -> Dict[str, Any]:
        """Enviar lote de documentos"""
        return await self.envio_lotes.enviar_lote(documentos_xml)
    
    async def consultar_lote(self, numero_lote: str) -> Dict[str, Any]:
        """Consultar resultado de lote"""
        return await self.envio_lotes.consultar_resultado_lote(numero_lote)
    
    # Métodos de consulta con cache
    async def consultar_documento(self, cdc: str, usar_cache: bool = True) -> Dict[str, Any]:
        """Consultar documento con cache opcional"""
        if usar_cache and cdc in self._cache_documentos:
            return self._cache_documentos[cdc]
        
        resultado = await self.consultas.consultar_documento(cdc)
        
        if usar_cache and resultado['success']:
            self._cache_documentos[cdc] = resultado
        
        return resultado
    
    async def consultar_ruc(self, ruc: str, dv: str, usar_cache: bool = True) -> Dict[str, Any]:
        """Consultar RUC con cache opcional"""
        clave_cache = f"{ruc}-{dv}"
        
        if usar_cache and clave_cache in self._cache_ruc:
            return self._cache_ruc[clave_cache]
        
        resultado = await self.consultas.consultar_ruc(ruc, dv)
        
        if usar_cache and resultado['success']:
            self._cache_ruc[clave_cache] = resultado
        
        return resultado
    
    # Métodos de eventos
    async def cancelar_documento(self, cdc: str, motivo: str) -> Dict[str, Any]:
        """Cancelar documento (requiere XML de evento firmado)"""
        # En implementación real, generar XML de cancelación y firmarlo
        xml_evento = self._generar_evento_cancelacion(cdc, motivo)
        return await self.eventos.registrar_evento(xml_evento)
    
    async def inutilizar_numeracion(self, timbrado: str, establecimiento: str,
                                  punto_expedicion: str, numero_inicio: str,
                                  numero_fin: str, tipo_documento: int, 
                                  motivo: str) -> Dict[str, Any]:
        """Inutilizar numeración (requiere XML de evento firmado)"""
        # En implementación real, generar XML de inutilización y firmarlo
        xml_evento = self._generar_evento_inutilizacion(
            timbrado, establecimiento, punto_expedicion,
            numero_inicio, numero_fin, tipo_documento, motivo
        )
        return await self.eventos.registrar_evento(xml_evento)
    
    # Métodos de utilidad
    def validar_conectividad(self) -> Dict[str, Any]:
        """Validar conectividad con SIFEN"""
        try:
            # Intentar conectar a cada servicio
            resultados = {}
            
            # Test de conectividad básica
            import requests
            for servicio, url in self._get_urls_servicios().items():
                try:
                    response = requests.get(url, timeout=10, verify=True)
                    resultados[servicio] = {
                        'conectividad': True,
                        'codigo_http': response.status_code
                    }
                except Exception as e:
                    resultados[servicio] = {
                        'conectividad': False,
                        'error': str(e)
                    }
            
            return {
                'success': all(r['conectividad'] for r in resultados.values()),
                'servicios': resultados,
                'ambiente': self.ambiente
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error validando conectividad: {str(e)}"
            }
    
    def _get_urls_servicios(self) -> Dict[str, str]:
        """Obtener URLs de todos los servicios"""
        base = "https://sifen.set.gov.py" if self.ambiente == "prod" else "https://sifen-test.set.gov.py"
        
        return {
            'individual': f"{base}/de/ws/sync/recibe.wsdl",
            'lotes': f"{base}/de/ws/async/recibe-lote.wsdl",
            'consultas': f"{base}/de/ws/consultas/consulta.wsdl",
            'eventos': f"{base}/de/ws/eventos/evento.wsdl"
        }
    
    def _generar_evento_cancelacion(self, cdc: str, motivo: str) -> str:
        """Generar XML de evento de cancelación (placeholder)"""
        # En implementación real, usar generador de eventos con firma
        return f"<!-- XML evento cancelación para {cdc}: {motivo} -->"
    
    def _generar_evento_inutilizacion(self, *args) -> str:
        """Generar XML de evento de inutilización (placeholder)"""
        # En implementación real, usar generador de eventos con firma
        return f"<!-- XML evento inutilización: {args} -->"
```

## 🧪 **Ejemplos de Uso Completo**

### **Envío Individual**
```python
async def ejemplo_envio_individual():
    """Ejemplo completo de envío individual"""
    
    # Configurar cliente
    client = SifenClient(
        ambiente="test",
        cert_path="/path/to/certificate.p12",
        cert_password="password"
    )
    
    # XML del documento firmado (generado previamente)
    xml_documento = """<?xml version="1.0" encoding="UTF-8"?>
    <rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
        <!-- Documento completo firmado -->
    </rDE>"""
    
    # Enviar documento
    resultado = await client.enviar_documento(xml_documento)
    
    if resultado['success']:
        print(f"✅ Documento aprobado")
        print(f"CDC: {resultado['cdc']}")
        print(f"Número transacción: {resultado['numero_transaccion']}")
    else:
        print(f"❌ Error: {resultado['mensaje']} (Código: {resultado['codigo']})")
```

### **Envío por Lotes**
```python
async def ejemplo_envio_lotes():
    """Ejemplo completo de envío por lotes"""
    
    client = SifenClient(ambiente="test")
    
    # Lista de documentos XML firmados
    documentos = [
        "<!-- XML documento 1 -->",
        "<!-- XML documento 2 -->",
        "<!-- XML documento 3 -->"
    ]
    
    # Enviar lote
    resultado_envio = await client.enviar_lote(documentos)
    
    if resultado_envio['success']:
        numero_lote = resultado_envio['numero_lote']
        print(f"✅ Lote enviado: {numero_lote}")
        
        # Esperar procesamiento (en producción usar polling)
        import asyncio
        await asyncio.sleep(60)  # Esperar 1 minuto
        
        # Consultar resultado
        resultado_consulta = await client.consultar_lote(numero_lote)
        
        if resultado_consulta['success']:
            print(f"📊 Procesamiento completado:")
            print(f"   Aprobados: {resultado_consulta['aprobados']}")
            print(f"   Rechazados: {resultado_consulta['rechazados']}")
            
            # Mostrar detalle por documento
            for doc in resultado_consulta['documentos']:
                estado = "✅" if doc['aprobado'] else "❌"
                print(f"   {estado} {doc['cdc']}: {doc['mensaje_resultado']}")
        else:
            print(f"❌ Error consultando lote: {resultado_consulta['error']}")
    else:
        print(f"❌ Error enviando lote: {resultado_envio['mensaje']}")
```

### **Consultas**
```python
async def ejemplo_consultas():
    """Ejemplo de consultas"""
    
    client = SifenClient(ambiente="test")
    
    # Consultar documento
    cdc = "01234567890123456789012345678901234567890123"
    doc_resultado = await client.consultar_documento(cdc)
    
    if doc_resultado['encontrado']:
        doc = doc_resultado['documento']
        print(f"📄 Documento encontrado:")
        print(f"   Emisor: {doc['nombre_emisor']} (RUC: {doc['ruc_emisor']})")
        print(f"   Total: {doc['total_operacion']}")
        print(f"   Estado: {doc['estado_descripcion']}")
    else:
        print(f"❌ Documento no encontrado")
    
    # Consultar RUC
    ruc_resultado = await client.consultar_ruc("12345678", "9")
    
    if ruc_resultado['encontrado']:
        contrib = ruc_resultado['contribuyente']
        print(f"👤 Contribuyente: {contrib['nombre']}")
        print(f"   Estado: {contrib['estado_descripcion']}")
        print(f"   Tipo: {contrib['tipo_contribuyente_descripcion']}")
    else:
        print(f"❌ RUC no encontrado")
```

## ⚠️ **Consideraciones de Implementación**

### **Seguridad**
- **Certificados PSC**: Obligatorios para producción
- **TLS 1.2**: Versión mínima requerida
- **Mutual Authentication**: Cliente y servidor validan certificados
- **Timeouts**: Configurar timeouts apropiados (60s recomendado)

### **Performance**
- **Cache**: Implementar cache para consultas RUC frecuentes
- **Retry Logic**: Para errores temporales de conectividad
- **Connection Pooling**: Reutilizar conexiones HTTPS
- **Async/Await**: Para operaciones no bloqueantes

### **Manejo de Errores**
- **Validación local**: Antes de envío a SIFEN
- **Códigos específicos**: Mapear códigos a acciones específicas
- **Logging estructurado**: Para debugging y auditoría
- **Fallback strategies**: Para fallos de conectividad

### **Monitoreo**
- **Health checks**: Validar conectividad periódicamente
- **Métricas**: Tiempo de respuesta, tasa de éxito/fallo
- **Alertas**: Para errores críticos o caídas de servicio
- **Auditoría**: Log de todas las transacciones

---

**📝 Notas de Implementación:**
- Validar certificados PSC antes de producción
- Implementar retry con backoff exponencial
- Mantener logs detallados para debugging
- Usar ambiente de test para desarrollo completo

**🔄 Última actualización**: Basado en Manual Técnico SIFEN v150