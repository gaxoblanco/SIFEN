# Representación Gráfica KuDE y Código QR SIFEN v150

## 📋 **Definición del KuDE**

**KuDE** (Kuatia'i Digital Electrónico) es la representación gráfica física o digital de un Documento Electrónico (DE) aprobado por SIFEN. Es un documento tributario auxiliar que expresa de manera simplificada una transacción respaldada por un DE.

### **Propósitos del KuDE**
1. **Documento tributario físico** para receptores no electrónicos o consumidor final
2. **Amparo del traslado** de mercaderías entre locales
3. **Respaldo de créditos fiscales** para receptores no facturadores electrónicos

### **Características Principales**
- ✅ **Consulta pública** del DTE mediante CDC o QR Code
- ✅ **Generación directa** desde sistemas de facturación
- ✅ **Durabilidad mínima** de 6 meses (papel e impresión)
- ❌ **Prohibido incluir** información no presente en el DE firmado
- ❌ **No enviar a SIFEN** información adicional del emisor

## 📄 **Tipos de KuDE por Documento**

| Tipo DE | Denominación KuDE | Código |
|---------|-------------------|--------|
| Factura Electrónica | KuDE de Factura Electrónica | FE |
| Autofactura Electrónica | KuDE de Autofactura Electrónica | AFE |
| Nota de Crédito Electrónica | KuDE de Nota de Crédito Electrónica | NCE |
| Nota de Débito Electrónica | KuDE de Nota de Débito Electrónica | NDE |
| Nota de Remisión Electrónica | KuDE de Nota de Remisión Electrónica | NRE |

## 🏗️ **Estructura del KuDE**

### **1. Campos del Encabezado**

#### **Datos del Emisor**
| Campo | Origen XML | Descripción | Obligatorio |
|-------|------------|-------------|-------------|
| **Logo** | - | Espacio reservado (opcional) | ❌ |
| **Nombre/Razón Social** | D105 | Nombre del emisor | ✅ |
| **Nombre Fantasía** | D106 | Nombre comercial | ❌ |
| **Actividad** | D131 | Descripción actividad económica | ✅ |
| **Dirección** | D107 | Dirección del emisor | ✅ |
| **Ciudad** | D116 | Descripción ciudad | ✅ |

#### **Datos del Timbrado**
| Campo | Origen XML | Descripción | Obligatorio |
|-------|------------|-------------|-------------|
| **RUC** | D101 | RUC del emisor | ✅ |
| **Timbrado N°** | C004 | Número del timbrado | ✅ |
| **Vigencia Inicio** | C008 | Fecha inicio vigencia | ✅ |
| **Vigencia Fin** | C009 | Fecha fin vigencia | ✅ |
| **N° Documento** | C007 | Número del documento | ✅ |

#### **Datos Generales**
| Campo | Origen XML | Descripción | Obligatorio |
|-------|------------|-------------|-------------|
| **Fecha/Hora Emisión** | D002 | AAAA-MM-DDThh:mm:ss | ✅ |
| **Condición Operación** | E602 | Contado/Crédito | ✅ |
| **N° Cuotas** | E644 | Solo para crédito | ❌ |
| **Moneda** | D016 | Descripción moneda | ✅ |
| **Tipo Cambio** | D018 | Solo si moneda ≠ PYG | ❌ |

#### **Datos del Receptor** (Opcional)
| Campo | Origen XML | Descripción | Obligatorio |
|-------|------------|-------------|-------------|
| **RUC/Doc Identidad** | D206/D210 | Según tipo contribuyente | ❌ |
| **Nombre/Razón Social** | D211 | Nombre del receptor | ❌ |
| **Dirección** | D213 | Dirección del receptor | ❌ |
| **Teléfono** | D214 | Teléfono del receptor | ❌ |
| **Email** | D216 | Correo electrónico | ❌ |
| **Tipo Operación** | D012 | Descripción tipo transacción | ✅ |

### **2. Campos de Items de la Operación**

| Campo | Origen XML | Descripción | Ancho Sugerido |
|-------|------------|-------------|----------------|
| **Código** | E701-E707 | Código interno/GTIN/NCM | 10% |
| **Descripción** | E708 | Producto/servicio | 30% |
| **Unidad** | E710 | Descripción unidad medida | 8% |
| **Cantidad** | E711 | Cantidad | 8% |
| **Precio Unitario** | E721 | Precio unitario | 12% |
| **Descuento** | EA002 | Descuento por ítem | 10% |
| **Exentas** | E732 (0%) | Valor exento IVA | 7% |
| **IVA 5%** | E732 (5%) | Valor gravado 5% | 7% |
| **IVA 10%** | E732 (10%) | Valor gravado 10% | 8% |

### **3. Campos de Subtotales y Totales**

| Campo | Origen XML | Descripción |
|-------|------------|-------------|
| **Subtotal Exentas** | F002 | Subtotal operaciones exentas |
| **Subtotal 5%** | F004 | Subtotal gravado IVA 5% |
| **Subtotal 10%** | F005 | Subtotal gravado IVA 10% |
| **Total Operación** | F007 | Total general de la operación |
| **Total Guaraníes** | F022 | Total en moneda nacional |
| **Liquidación IVA 5%** | F014 | IVA liquidado 5% |
| **Liquidación IVA 10%** | F015 | IVA liquidado 10% |
| **Total IVA** | F016 | Total IVA de la operación |

### **4. Información de Consulta SIFEN**

#### **Portal de Consulta**
- **Producción**: https://ekuatia.set.gov.py/consultas/
- **Test**: https://ekuatia.set.gov.py/consultas-test/

#### **CDC Formato**
El CDC debe mostrarse en **11 grupos de 4 dígitos**:
```
0123-4567-8901-2345-6789-0123-4567-8901-2345-6789-0123
```

### **5. Código QR**

**Obligatorio** en todos los KuDE, debe incluir toda la información necesaria para consulta pública.

### **6. Información Adicional del Emisor** (Campo J003)

- **Espacio libre** para información comercial, promocional o mensajes personalizados
- **Prohibido enviar** esta información en el XML a SIFEN
- **No debe incluir** información operacional que no esté en el DE firmado

## 📐 **Formatos de KuDE**

### **Formato 1: Papel Convencional**
- **Tamaños**: Carta, A4, Legal, o cualquier estándar
- **Uso**: Operaciones B2B, documentos formales
- **Páginas**: Múltiples páginas permitidas
- **Numeración**: "Página X de Y"
- **QR**: Al menos en la primera página
- **Totales**: En la última página

### **Formato 2: Cinta de Papel**
- **Uso**: Ventas al consumidor final (supermercados, farmacias, restaurantes)
- **Ancho**: Variable según impresora térmica
- **Longitud**: Ajustable al contenido
- **QR**: Al final del documento

### **Formato 3: Cinta Resumen**
- **Uso**: Cuando el consumidor solicita resumen
- **Contenido**: Solo cantidad total de ítems y monto total
- **Sin detalle**: No incluye detalle de ítems ni impuestos
- **Consulta completa**: Disponible vía QR o CDC en portal

## 📱 **Especificación del Código QR**

### **Estándar**
- **Norma**: ISO/IEC 18004 (QR Code estándar internacional)
- **Versión**: Compatible con lectores estándar
- **Codificación**: UTF-8

### **Dimensiones Físicas**
| Concepto | Medida Mínima | Recomendación |
|----------|---------------|---------------|
| **Ancho total** | 25 mm | 30 mm o más |
| **Área contenido** | 22 mm | Proporcional |
| **Margen seguro** | 3 mm | 10% del ancho total |

### **Contenido del QR (Campo J002)**

#### **Estructura de la URL**
```
https://ekuatia.set.gov.py/consultas/qr?nVersion=150&Id={CDC}&dFeEmiDE={FECHA}&dRucRec={RUC_RECEPTOR}&dTotGralOpe={TOTAL}&dTotIVA={IVA}&cItems={CANTIDAD_ITEMS}&DigestValue={HASH_DE}&IdCSC={ID_CSC}&cHashQR={HASH_QR}
```

#### **Parámetros del QR**
| Parámetro | Descripción | Formato | Ejemplo |
|-----------|-------------|---------|---------|
| **nVersion** | Versión formato | Numérico | 150 |
| **Id** | CDC del documento | 44 caracteres | 01234567890... |
| **dFeEmiDE** | Fecha emisión | YYYY-MM-DD | 2019-09-10 |
| **dRucRec** | RUC receptor | Numérico | 80016875 |
| **dTotGralOpe** | Total general | Decimal | 110000.00 |
| **dTotIVA** | Total IVA | Decimal | 10000.00 |
| **cItems** | Cantidad ítems | Numérico | 5 |
| **DigestValue** | Hash del DE | Base64 | abc123def... |
| **IdCSC** | ID CSC | 32 caracteres | A1B2C3D4E5F6... |
| **cHashQR** | Hash validación QR | Hex | 1a2b3c4d... |

### **Código de Seguridad (CSC)**

#### **Características**
- **Longitud**: 32 dígitos alfanuméricos
- **Generación**: Por SIFEN al autorizar facturador electrónico
- **Uso**: Validación de autenticidad del QR
- **Seguridad**: Privado, no mostrar en KuDE

#### **Generación del Hash QR**
```python
import hashlib

def generar_hash_qr(cdc: str, fecha_emision: str, ruc_receptor: str, 
                   total_operacion: str, total_iva: str, cantidad_items: str,
                   digest_value: str, csc: str) -> str:
    """Generar hash de validación del QR"""
    
    # Concatenar parámetros
    cadena = f"{cdc}{fecha_emision}{ruc_receptor}{total_operacion}{total_iva}{cantidad_items}{digest_value}{csc}"
    
    # Calcular hash SHA-256
    hash_obj = hashlib.sha256(cadena.encode('utf-8'))
    return hash_obj.hexdigest()[:8]  # Primeros 8 caracteres
```

## 💻 **Implementación en Código**

### **Generador de KuDE**
```python
from datetime import datetime
from typing import Optional, List, Dict
import qrcode
from io import BytesIO
import base64

class ItemKuDE:
    def __init__(self, codigo: str, descripcion: str, unidad: str, 
                 cantidad: float, precio_unitario: float, descuento: float = 0,
                 valor_exenta: float = 0, valor_5: float = 0, valor_10: float = 0):
        self.codigo = codigo
        self.descripcion = descripcion
        self.unidad = unidad
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario
        self.descuento = descuento
        self.valor_exenta = valor_exenta
        self.valor_5 = valor_5
        self.valor_10 = valor_10

class DatosEmisor:
    def __init__(self, ruc: str, nombre: str, direccion: str, ciudad: str,
                 nombre_fantasia: str = "", actividad: str = ""):
        self.ruc = ruc
        self.nombre = nombre
        self.nombre_fantasia = nombre_fantasia
        self.actividad = actividad
        self.direccion = direccion
        self.ciudad = ciudad

class DatosReceptor:
    def __init__(self, ruc_doc: str = "", nombre: str = "", direccion: str = "",
                 telefono: str = "", email: str = ""):
        self.ruc_doc = ruc_doc
        self.nombre = nombre
        self.direccion = direccion
        self.telefono = telefono
        self.email = email

class KuDEGenerator:
    def __init__(self, ambiente: str = "test"):
        self.ambiente = ambiente
        self.base_url_qr = (
            "https://ekuatia.set.gov.py/consultas/qr" if ambiente == "prod" 
            else "https://ekuatia.set.gov.py/consultas-test/qr"
        )
    
    def generar_kude_html(self, 
                         tipo_documento: str,
                         cdc: str,
                         numero_documento: str,
                         fecha_emision: datetime,
                         emisor: DatosEmisor,
                         receptor: Optional[DatosReceptor],
                         items: List[ItemKuDE],
                         totales: Dict[str, float],
                         timbrado: Dict[str, str],
                         csc: str) -> str:
        """Generar HTML del KuDE"""
        
        # Generar QR
        qr_url = self._generar_url_qr(cdc, fecha_emision, receptor, totales, len(items), csc)
        qr_b64 = self._generar_qr_base64(qr_url)
        
        # Formatear CDC para mostrar
        cdc_formateado = self._formatear_cdc(cdc)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 12px; margin: 20px; }}
                .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; }}
                .logo {{ float: left; width: 100px; height: 80px; }}
                .company-info {{ text-align: center; margin-bottom: 10px; }}
                .document-info {{ background-color: #f0f0f0; padding: 10px; margin: 10px 0; }}
                .customer-info {{ border: 1px solid #ccc; padding: 10px; margin: 10px 0; }}
                .items-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .items-table th, .items-table td {{ border: 1px solid #000; padding: 5px; text-align: center; }}
                .items-table th {{ background-color: #f0f0f0; font-weight: bold; }}
                .totals {{ float: right; width: 300px; margin: 20px 0; }}
                .totals table {{ width: 100%; border-collapse: collapse; }}
                .totals td {{ border: 1px solid #000; padding: 5px; }}
                .qr-section {{ text-align: center; margin: 20px 0; }}
                .qr-info {{ font-size: 10px; margin-top: 10px; }}
                .clear {{ clear: both; }}
            </style>
        </head>
        <body>
            <!-- Encabezado -->
            <div class="header">
                <div class="logo">
                    <!-- Espacio para logo -->
                </div>
                <div class="company-info">
                    <h2>{emisor.nombre}</h2>
                    <p><strong>{emisor.nombre_fantasia}</strong></p>
                    <p>{emisor.actividad}</p>
                    <p>{emisor.direccion}</p>
                    <p>Ciudad: {emisor.ciudad}</p>
                </div>
                <div class="clear"></div>
            </div>
            
            <!-- Información del documento -->
            <div class="document-info">
                <h3>KuDE DE {tipo_documento.upper()}</h3>
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <p><strong>RUC:</strong> {emisor.ruc}</p>
                        <p><strong>Timbrado N°:</strong> {timbrado.get('numero', '')}</p>
                        <p><strong>Vigencia:</strong> {timbrado.get('inicio', '')} - {timbrado.get('fin', '')}</p>
                    </div>
                    <div>
                        <p><strong>{tipo_documento} N°:</strong> {numero_documento}</p>
                        <p><strong>Fecha y Hora:</strong> {fecha_emision.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p><strong>Condición:</strong> {totales.get('condicion', 'Contado')}</p>
                    </div>
                </div>
            </div>
            
            <!-- Información del receptor -->
            {self._generar_seccion_receptor(receptor) if receptor else ''}
            
            <!-- Items -->
            <table class="items-table">
                <thead>
                    <tr>
                        <th>Cód.</th>
                        <th>Descripción</th>
                        <th>Unidad</th>
                        <th>Cant.</th>
                        <th>Precio Unit.</th>
                        <th>Descuento</th>
                        <th>Exentas</th>
                        <th>5%</th>
                        <th>10%</th>
                    </tr>
                </thead>
                <tbody>
                    {self._generar_filas_items(items)}
                </tbody>
            </table>
            
            <!-- Totales -->
            <div class="totals">
                <table>
                    <tr><td><strong>Subtotal Exentas:</strong></td><td>{totales.get('subtotal_exentas', 0):,.0f}</td></tr>
                    <tr><td><strong>Subtotal 5%:</strong></td><td>{totales.get('subtotal_5', 0):,.0f}</td></tr>
                    <tr><td><strong>Subtotal 10%:</strong></td><td>{totales.get('subtotal_10', 0):,.0f}</td></tr>
                    <tr><td><strong>Total Operación:</strong></td><td>{totales.get('total_operacion', 0):,.0f}</td></tr>
                    <tr><td><strong>Total Guaraníes:</strong></td><td>{totales.get('total_guaranies', 0):,.0f}</td></tr>
                    <tr><td><strong>Liquidación IVA 5%:</strong></td><td>{totales.get('iva_5', 0):,.0f}</td></tr>
                    <tr><td><strong>Liquidación IVA 10%:</strong></td><td>{totales.get('iva_10', 0):,.0f}</td></tr>
                    <tr><td><strong>Total IVA:</strong></td><td>{totales.get('total_iva', 0):,.0f}</td></tr>
                </table>
            </div>
            <div class="clear"></div>
            
            <!-- Código QR y consulta -->
            <div class="qr-section">
                <img src="data:image/png;base64,{qr_b64}" alt="Código QR" style="width: 150px; height: 150px;">
                <div class="qr-info">
                    <p><strong>Para consultas, ingrese a:</strong></p>
                    <p><strong>Producción:</strong> https://ekuatia.set.gov.py/consultas/</p>
                    <p><strong>Test:</strong> https://ekuatia.set.gov.py/consultas-test/</p>
                    <p><strong>CDC:</strong> {cdc_formateado}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generar_seccion_receptor(self, receptor: DatosReceptor) -> str:
        """Generar sección de información del receptor"""
        if not receptor.nombre:
            return ""
            
        return f"""
        <div class="customer-info">
            <h4>Datos del Receptor:</h4>
            <p><strong>RUC/Doc:</strong> {receptor.ruc_doc}</p>
            <p><strong>Nombre:</strong> {receptor.nombre}</p>
            <p><strong>Dirección:</strong> {receptor.direccion}</p>
            <p><strong>Teléfono:</strong> {receptor.telefono} <strong>Email:</strong> {receptor.email}</p>
        </div>
        """
    
    def _generar_filas_items(self, items: List[ItemKuDE]) -> str:
        """Generar filas HTML para los items"""
        filas = []
        for item in items:
            fila = f"""
            <tr>
                <td>{item.codigo}</td>
                <td style="text-align: left;">{item.descripcion}</td>
                <td>{item.unidad}</td>
                <td>{item.cantidad:,.2f}</td>
                <td>{item.precio_unitario:,.0f}</td>
                <td>{item.descuento:,.0f}</td>
                <td>{item.valor_exenta:,.0f}</td>
                <td>{item.valor_5:,.0f}</td>
                <td>{item.valor_10:,.0f}</td>
            </tr>
            """
            filas.append(fila)
        return "".join(filas)
    
    def _formatear_cdc(self, cdc: str) -> str:
        """Formatear CDC en grupos de 4 dígitos"""
        grupos = [cdc[i:i+4] for i in range(0, len(cdc), 4)]
        return "-".join(grupos)
    
    def _generar_url_qr(self, cdc: str, fecha_emision: datetime, 
                       receptor: Optional[DatosReceptor], totales: Dict[str, float],
                       cantidad_items: int, csc: str) -> str:
        """Generar URL para el código QR"""
        
        # Extraer datos necesarios
        fecha_str = fecha_emision.strftime('%Y-%m-%d')
        ruc_receptor = receptor.ruc_doc if receptor and receptor.ruc_doc else ""
        total_operacion = totales.get('total_operacion', 0)
        total_iva = totales.get('total_iva', 0)
        
        # Simular DigestValue (en implementación real viene de la firma)
        digest_value = "simulado_hash_de_documento"
        
        # Simular ID CSC (en implementación real es asignado por SIFEN)
        id_csc = "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6"
        
        # Generar hash QR
        hash_qr = self._generar_hash_qr(cdc, fecha_str, ruc_receptor, 
                                       str(total_operacion), str(total_iva),
                                       str(cantidad_items), digest_value, csc)
        
        # Construir URL
        url = f"{self.base_url_qr}?nVersion=150&Id={cdc}&dFeEmiDE={fecha_str}"
        url += f"&dRucRec={ruc_receptor}&dTotGralOpe={total_operacion}"
        url += f"&dTotIVA={total_iva}&cItems={cantidad_items}"
        url += f"&DigestValue={digest_value}&IdCSC={id_csc}&cHashQR={hash_qr}"
        
        return url
    
    def _generar_hash_qr(self, cdc: str, fecha: str, ruc_receptor: str,
                        total_operacion: str, total_iva: str, cantidad_items: str,
                        digest_value: str, csc: str) -> str:
        """Generar hash de validación del QR"""
        import hashlib
        
        cadena = f"{cdc}{fecha}{ruc_receptor}{total_operacion}{total_iva}{cantidad_items}{digest_value}{csc}"
        hash_obj = hashlib.sha256(cadena.encode('utf-8'))
        return hash_obj.hexdigest()[:8]
    
    def _generar_qr_base64(self, url: str) -> str:
        """Generar imagen QR en base64"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return img_base64
```

### **Generador de KuDE para Cinta de Papel**
```python
class KuDECintaGenerator(KuDEGenerator):
    def generar_kude_cinta_html(self, 
                               tipo_documento: str,
                               cdc: str,
                               numero_documento: str,
                               fecha_emision: datetime,
                               emisor: DatosEmisor,
                               items: List[ItemKuDE],
                               totales: Dict[str, float],
                               csc: str,
                               ancho_mm: int = 80) -> str:
        """Generar KuDE formato cinta de papel"""
        
        qr_url = self._generar_url_qr(cdc, fecha_emision, None, totales, len(items), csc)
        qr_b64 = self._generar_qr_base64(qr_url)
        cdc_formateado = self._formatear_cdc(cdc)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ 
                    font-family: 'Courier New', monospace; 
                    font-size: 10px; 
                    margin: 0; 
                    padding: 10px;
                    width: {ancho_mm}mm;
                }}
                .center {{ text-align: center; }}
                .line {{ border-bottom: 1px dashed #000; margin: 5px 0; }}
                .item {{ margin: 3px 0; }}
                .total {{ font-weight: bold; }}
                .qr {{ text-align: center; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="center">
                <strong>{emisor.nombre}</strong><br>
                {emisor.nombre_fantasia}<br>
                {emisor.direccion}<br>
                RUC: {emisor.ruc}<br>
                Timbrado: {timbrado.get('numero', '')}<br>
                {tipo_documento} N°: {numero_documento}<br>
                {fecha_emision.strftime('%Y-%m-%d %H:%M:%S')}
            </div>
            
            <div class="line"></div>
            
            {self._generar_items_cinta(items)}
            
            <div class="line"></div>
            
            <div class="total">
                Subtotal: {totales.get('total_operacion', 0):,.0f}<br>
                IVA: {totales.get('total_iva', 0):,.0f}<br>
                TOTAL: {totales.get('total_guaranies', 0):,.0f}
            </div>
            
            <div class="qr">
                <img src="data:image/png;base64,{qr_b64}" alt="QR" style="width: 60px; height: 60px;"><br>
                <small>CDC: {cdc_formateado}</small>
            </div>
            
            <div class="center">
                <small>Consulte en: ekuatia.set.gov.py</small>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generar_items_cinta(self, items: List[ItemKuDE]) -> str:
        """Generar items para formato cinta"""
        items_html = []
        for item in items:
            item_html = f"""
            <div class="item">
                {item.descripcion}<br>
                {item.cantidad} x {item.precio_unitario:,.0f} = {(item.cantidad * item.precio_unitario):,.0f}
            </div>
            """
            items_html.append(item_html)
        return "".join(items_html)
```

## 📋 **Validaciones del KuDE y QR**

### **Códigos de Error QR (J002)**
| Código | Descripción | Validación |
|--------|-------------|------------|
| **2500** | Cadena QR no coincidente con XML | Verificar parámetros QR vs campos XML |
| **2501** | Hash del código QR inválido | Recalcular hash con CSC correcto |
| **2502** | URL de consulta QR inválida | Verificar formato de URL |

### **Validaciones Obligatorias**
```python
def validar_kude(kude_data: dict) -> list:
    """Validar datos del KuDE antes de generar"""
    errores = []
    
    # Validar campos obligatorios
    campos_obligatorios = [
        'cdc', 'fecha_emision', 'emisor_nombre', 'emisor_ruc',
        'numero_documento', 'total_operacion', 'total_iva'
    ]
    
    for campo in campos_obligatorios:
        if not kude_data.get(campo):
            errores.append(f"Campo obligatorio faltante: {campo}")
    
    # Validar formato CDC
    cdc = kude_data.get('cdc', '')
    if len(cdc) != 44 or not cdc.isdigit():
        errores.append("CDC debe tener exactamente 44 dígitos")
    
    # Validar totales
    total_items = sum(item.valor_exenta + item.valor_5 + item.valor_10 
                     for item in kude_data.get('items', []))
    if abs(total_items - kude_data.get('total_operacion', 0)) > 1:
        errores.append("Total de ítems no coincide con total operación")
    
    return errores

def validar_qr_url(url: str, csc: str) -> bool:
    """Validar que la URL del QR sea correcta"""
    try:
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Verificar parámetros obligatorios
        required_params = ['nVersion', 'Id', 'dFeEmiDE', 'cHashQR']
        for param in required_params:
            if param not in params:
                return False
        
        # Verificar hash QR
        # En implementación real, recalcular hash y comparar
        
        return True
    except:
        return False
```

## 🚀 **Ejemplo de Uso Completo**

### **Generar KuDE de Factura Electrónica**
```python
from datetime import datetime

# Configurar datos
emisor = DatosEmisor(
    ruc="23654388",
    nombre="Marta Anahi Bordon Vidal",
    nombre_fantasia="Soluciones Informáticas",
    actividad="Reparación de Equipos Informáticos",
    direccion="Avenida González Vidal #1434",
    ciudad="Asunción"
)

receptor = DatosReceptor(
    ruc_doc="1131421-4",
    nombre="Belén Bosco",
    direccion="Mcal. López y Yegros",
    telefono="021 123 456",
    email="belbosco@gmail.com"
)

items = [
    ItemKuDE(
        codigo="INF012",
        descripcion="Disco duro",
        unidad="UNI",
        cantidad=1,
        precio_unitario=110000,
        descuento=0,
        valor_exenta=0,
        valor_5=0,
        valor_10=110000
    )
]

totales = {
    'subtotal_exentas': 0,
    'subtotal_5': 0,
    'subtotal_10': 110000,
    'total_operacion': 110000,
    'total_guaranies': 121000,
    'iva_5': 0,
    'iva_10': 11000,
    'total_iva': 11000,
    'condicion': 'Contado'
}

timbrado = {
    'numero': '1000332',
    'inicio': '01/07/2018',
    'fin': '31/07/2019'
}

# Generar KuDE
generator = KuDEGenerator(ambiente="test")
html_kude = generator.generar_kude_html(
    tipo_documento="Factura Electrónica",
    cdc="01234567890123456789012345678901234567890123",
    numero_documento="001-001-0000001",
    fecha_emision=datetime.now(),
    emisor=emisor,
    receptor=receptor,
    items=items,
    totales=totales,
    timbrado=timbrado,
    csc="A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0"
)

# Convertir a PDF si es necesario
# from weasyprint import HTML
# HTML(string=html_kude).write_pdf("factura.pdf")

print("KuDE generado exitosamente")
```

## ⚠️ **Consideraciones Importantes**

### **Requisitos Legales**
- **Durabilidad**: Papel e impresión deben durar mínimo 6 meses
- **Legibilidad**: Texto y QR deben ser perfectamente legibles
- **Integridad**: No alterar información del DE original
- **Consulta**: Facilitar consulta pública del DTE

### **Buenas Prácticas**
- **Diseño responsivo**: Adaptable a diferentes tamaños de papel
- **Contraste adecuado**: Asegurar legibilidad en copias
- **QR grande**: Mínimo 25mm para garantizar lectura
- **Información clara**: Organizar datos de forma intuitiva

### **Limitaciones Técnicas**
- **Sin información adicional**: Solo campos del DE firmado
- **No enviar J003**: Información adicional no va a SIFEN
- **Validación obligatoria**: QR debe validar correctamente
- **Formato estándar**: Cumplir estructura mínima definida

---

**📝 Notas de Implementación:**
- Implementar validación local del QR antes de imprimir
- Mantener plantillas flexibles para diferentes tipos de documento
- Considerar impresoras térmicas para formato cinta
- Integrar con sistema de consulta pública para verificación

**🔄 Última actualización**: Basado en Manual Técnico SIFEN v150