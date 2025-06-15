# Tablas de Codificación SIFEN v150

## 📋 **Introducción**

Este archivo contiene todas las tablas de codificación oficiales de SIFEN para su utilización en los archivos XML. Estas tablas son **críticas** para la validación y generación correcta de documentos electrónicos.

## 🏛️ **TABLA 1 - TIPOS DE RÉGIMEN**

### **Códigos de Régimen Tributario**
| Código | Descripción |
|--------|-------------|
| 1 | Régimen de Turismo |
| 2 | Importador |
| 3 | Exportador |
| 4 | Maquila |
| 5 | Ley N° 60/90 |
| 6 | Régimen del Pequeño Productor |
| 7 | Régimen del Mediano Productor |
| 8 | Régimen Contable |

### **Uso en XML**
```xml
<!-- Campo D104: cTipReg -->
<cTipReg>8</cTipReg>  <!-- Régimen Contable -->
<dDesTipReg>Régimen Contable</dDesTipReg>
```

## 🌍 **TABLA 2 - REFERENCIAS GEOGRÁFICAS**

### **TABLA 2.1 - Departamentos, Distritos y Ciudades**
- **Fuente Oficial**: https://ekuatia.set.gov.py/portal/ekuatia/documentacion/documentaciontecnica
- **Archivo**: CODIGO DE REFERENCIA GEOGRAFICA.xlsx
- **Formato**: Estructura jerárquica Departamento → Distrito → Ciudad

#### **Estructura Esperada**
| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Código Departamento** | 1-3 dígitos | 1 (Central) |
| **Nombre Departamento** | Texto | Central |
| **Código Distrito** | 1-3 dígitos | 1 (Asunción) |
| **Nombre Distrito** | Texto | Asunción |
| **Código Ciudad** | 1-3 dígitos | 1 (Asunción) |
| **Nombre Ciudad** | Texto | Asunción |

### **Uso en XML**
```xml
<!-- Emisor -->
<cDepEmi>1</cDepEmi>           <!-- Central -->
<cDisEmi>1</cDisEmi>           <!-- Asunción -->
<cCiuEmi>1</cCiuEmi>           <!-- Asunción -->
<dDesCiuEmi>Asunción</dDesCiuEmi>

<!-- Receptor -->
<cDepRec>10</cDepRec>          <!-- Alto Paraná -->
<cDisRec>1</cDisRec>           <!-- Ciudad del Este -->
<cCiuRec>1</cCiuRec>           <!-- Ciudad del Este -->
<dDesCiuRec>Ciudad del Este</dDesCiuRec>
```

## 💼 **TABLA 3 - ACTIVIDADES ECONÓMICAS**

### **Fuente Oficial**
- **URL**: https://servicios.set.gov.py/eset-publico/consultarActividadEconomicaIService.do
- **Tipo**: Web Service de consulta dinámica
- **Formato**: 6 dígitos numéricos

### **Estructura**
| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Código** | 6 dígitos | 620100 |
| **Descripción** | Texto descriptivo | Programación informática |

### **Uso en XML**
```xml
<!-- Grupo D2.1: Actividad Económica del Emisor -->
<gActEco>
    <cActEco>620100</cActEco>
    <dDesActEco>Programación informática</dDesActEco>
</gActEco>
```

## 🌎 **TABLA 4 - CODIFICACIÓN DE PAÍSES**

### **Estándar Internacional**
- **Base**: ISO 3166-1 Alfa-3 (3 caracteres)
- **Referencia**: https://es.wikipedia.org/wiki/ISO_3166-1#C%C3%B3digos_ISO_3166-1

### **Países Principales (Ejemplos)**
| Código | País | Código | País |
|--------|------|--------|------|
| **ARG** | Argentina | **PRY** | Paraguay |
| **BRA** | Brasil | **URY** | Uruguay |
| **BOL** | Bolivia | **USA** | Estados Unidos |
| **CHL** | Chile | **DEU** | Alemania |
| **COL** | Colombia | **ESP** | España |
| **ECU** | Ecuador | **FRA** | Francia |
| **PER** | Perú | **ITA** | Italia |
| **VEN** | Venezuela | **JPN** | Japón |

### **Uso en XML**
```xml
<!-- Receptor extranjero -->
<cPaisRec>ARG</cPaisRec>
<dDesPaisRe>Argentina</dDesPaisRe>

<!-- País origen producto -->
<cPaisOrig>CHN</cPaisOrig>
<dDesPaisOrig>China</dDesPaisOrig>

<!-- País destino transporte -->
<cPaisDest>BRA</cPaisDest>
<dDesPaisDest>Brasil</dDesPaisDest>
```

## 📏 **TABLA 5 - CODIFICACIÓN DE UNIDADES DE MEDIDA**

### **Unidades Principales**
| Código | Representación | Descripción | Uso Común |
|--------|----------------|-------------|-----------|
| **77** | UNI | Unidad | General |
| **83** | kg | Kilogramos | Peso |
| **86** | g | Gramos | Peso pequeño |
| **87** | m | Metros | Longitud |
| **88** | ML | Mililitros | Volumen pequeño |
| **89** | LT | Litros | Volumen |
| **91** | CM | Centímetros | Longitud pequeña |
| **95** | MM | Milímetros | Longitud muy pequeña |
| **99** | TN | Tonelada | Peso grande |
| **100** | Hs | Hora | Tiempo/Servicios |
| **104** | DET | Determinación | Servicios específicos |
| **108** | MT | Metros | Longitud (alternativo) |
| **109** | M2 | Metros cuadrados | Área |
| **110** | M3 | Metros cúbicos | Volumen |

### **Unidades Especializadas**
| Código | Representación | Descripción | Sector |
|--------|----------------|-------------|--------|
| **2329** | UI | Unidad Internacional | Farmacéutico |
| **2366** | CPM | Costo por Mil | Publicitario |
| **569** | ración | Ración | Alimentario |
| **625** | Km | Kilómetros | Transporte |
| **660** | ml | Metro lineal | Textil |
| **666** | Se | Segundo | Tiempo preciso |
| **869** | ha | Hectáreas | Inmobiliario |
| **885** | GL | Unidad Medida Global | General |
| **891** | pm | Por Milaje | Transporte |

### **Uso en XML**
```xml
<!-- Item con unidad de medida -->
<cUniMed>77</cUniMed>           <!-- Código -->
<dDesUniMed>UNI</dDesUniMed>    <!-- Descripción -->
<dCantProSer>5.0</dCantProSer>  <!-- Cantidad -->

<!-- Ejemplo para peso -->
<cUniMed>83</cUniMed>           <!-- kg -->
<dDesUniMed>kg</dDesUniMed>
<dCantProSer>2.5</dCantProSer>  <!-- 2.5 kg -->
```

## 💰 **TABLA 6 - CÓDIGOS DE AFECTACIÓN**

### **Tipos de Afectación IVA**
| Código | Descripción | Tasa IVA | Uso |
|--------|-------------|----------|-----|
| **1** | Gravado IVA | 5% o 10% | Productos/servicios normales |
| **2** | Exonerado (Art.83 - 125) | 0% | Productos con exoneración legal |
| **3** | Exento | 0% | Productos/servicios exentos |
| **4** | Gravado parcial | Variable | Casos especiales |

### **Uso en XML**
```xml
<!-- Item gravado IVA 10% -->
<cTiAfIVA>1</cTiAfIVA>          <!-- Gravado -->
<dDesTiAfIVA>Gravado IVA</dDesTiAfIVA>
<iPropIVA>10</iPropIVA>         <!-- 10% -->
<dTasaIVA>10.00</dTasaIVA>

<!-- Item exento -->
<cTiAfIVA>3</cTiAfIVA>          <!-- Exento -->
<dDesTiAfIVA>Exento</dDesTiAfIVA>
<iPropIVA>0</iPropIVA>          <!-- 0% -->
<dTasaIVA>0.00</dTasaIVA>
```

## 🚬 **TABLA 7 - CATEGORÍAS DEL ISC**

### **Secciones del Impuesto Selectivo al Consumo**
| Código | Descripción | Productos |
|--------|-------------|-----------|
| **1** | Sección I - Cigarrillos, Tabacos, Esencias y Otros derivados del Tabaco | Productos de tabaco |
| **2** | Sección II - Bebidas con y sin alcohol | Bebidas alcohólicas y no alcohólicas |
| **3** | Sección III - Alcoholes y Derivados del alcohol | Alcoholes puros y derivados |
| **4** | Sección IV - Combustibles | Gasolina, diésel, etc. |
| **5** | Sección V - Artículos considerados de lujo | Productos de lujo |

### **Uso en XML**
```xml
<!-- Producto con ISC -->
<cCategISC>2</cCategISC>        <!-- Bebidas -->
<dDesCategISC>Sección II - Bebidas con y sin alcohol</dDesCategISC>
```

## 📊 **TABLA 8 - TASAS DEL ISC**

### **Porcentajes según Decretos**
**Base legal**: Decretos N° 4344/04, N° 5158/10, N° 4693/15, N° 4694/15

| Código | Porcentaje | Código | Porcentaje |
|--------|------------|--------|------------|
| **1** | 1% | **7** | 16% |
| **2** | 5% | **8** | 18% |
| **3** | 9% | **9** | 20% |
| **4** | 10% | **10** | 24% |
| **5** | 11% | **11** | 34% |
| **6** | 13% | **12** | 38% |

### **Uso en XML**
```xml
<!-- Aplicación de ISC -->
<cTasaISC>4</cTasaISC>          <!-- Código tasa -->
<dTasaISC>10.00</dTasaISC>      <!-- 10% -->
<dBasGravISC>100000</dBasGravISC> <!-- Base gravable -->
<dLiqISC>10000</dLiqISC>        <!-- Liquidación ISC -->
```

## 🚗 **TABLA 9 - TIPOS DE VEHÍCULOS**

### **Referencia Externa**
- **Fuente**: Link de descarga oficial SET
- **Estado**: Disponible por separado
- **Uso**: Campo `cTipVeh` en sector automotores

### **Estructura Esperada**
| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Código** | 4-10 caracteres | AUTO |
| **Descripción** | Tipo de vehículo | Automóvil |

### **Uso en XML**
```xml
<!-- Sector automotores -->
<cTipVeh>AUTO</cTipVeh>
<dDesTipVeh>Automóvil</dDesTipVeh>
```

## 🚢 **TABLA 10 - CONDICIONES DE NEGOCIACIÓN (INCOTERMS)**

### **Términos Internacionales de Comercio**
| Código | Descripción | Tipo |
|--------|-------------|------|
| **CFR** | Costo y flete | Marítimo |
| **CIF** | Costo, seguro y flete | Marítimo |
| **CIP** | Transporte y seguro pagados hasta | Multimodal |
| **CPT** | Transporte pagado hasta | Multimodal |
| **DAP** | Entregada en lugar convenido | Multimodal |
| **DAT** | Entregada en terminal | Marítimo |
| **DDP** | Entregada derechos pagados | Multimodal |
| **EXW** | En fábrica | Cualquiera |
| **FAS** | Franco al costado del buque | Marítimo |
| **FCA** | Franco transportista | Multimodal |
| **FOB** | Franco a bordo | Marítimo |

### **Uso en XML**
```xml
<!-- Condición de negociación en transporte -->
<cCondNeg>CIF</cCondNeg>
<dDesCondNeg>Costo, seguro y flete</dDesCondNeg>
```

## 🏭 **TABLA 11 - REGÍMENES ADUANEROS**

### **Referencia Oficial**
- **URL**: http://www.aduana.gov.py/3123-4-circuitos-de-regimenes.html
- **Tipo**: Consulta externa a la Dirección Nacional de Aduanas

### **Uso en XML**
```xml
<!-- Régimen aduanero -->
<cRegAdu>40</cRegAdu>          <!-- Código régimen -->
<dDesRegAdu>Importación definitiva</dDesRegAdu>
```

## 📚 **REFERENCIAS ESTÁNDARES INTERNACIONALES**

### **Nomenclatura Común del Mercosur (NCM)**
- **Referencias**: 
  - http://www.sice.oas.org/Trade/MRCSRS/Resolutions/Res7006.pdf
  - https://sarem.mercosur.int/nomenclatura
- **Uso**: Campo `dNCM` en ítems (6-8 dígitos)

### **Códigos de Monedas (ISO 4217)**
- **Estándar**: ISO 4217
- **Referencia**: https://www.currency-iso.org/en/home/tables/table-a1.html
- **Uso**: Campo `cMoneOpe` (3 caracteres)

#### **Monedas Principales**
| Código | Moneda | País |
|--------|--------|------|
| **PYG** | Guaraní paraguayo | Paraguay |
| **USD** | Dólar estadounidense | Estados Unidos |
| **EUR** | Euro | Zona Euro |
| **BRL** | Real brasileño | Brasil |
| **ARS** | Peso argentino | Argentina |

## 💻 **Implementación en Código**

### **Validador de Códigos**
```python
from enum import Enum
from typing import Dict, Optional

class TipoRegimen(Enum):
    TURISMO = 1
    IMPORTADOR = 2
    EXPORTADOR = 3
    MAQUILA = 4
    LEY_60_90 = 5
    PEQUEÑO_PRODUCTOR = 6
    MEDIANO_PRODUCTOR = 7
    CONTABLE = 8

class TipoAfectacionIVA(Enum):
    GRAVADO = 1
    EXONERADO = 2
    EXENTO = 3
    GRAVADO_PARCIAL = 4

class UnidadMedida(Enum):
    UNIDAD = 77
    KILOGRAMOS = 83
    GRAMOS = 86
    METROS = 87
    MILILITROS = 88
    LITROS = 89
    CENTIMETROS = 91
    MILIMETROS = 95
    TONELADAS = 99
    HORAS = 100
    DETERMINACION = 104

class ValidadorCodigos:
    """Validador para códigos SIFEN"""
    
    # Tabla de países (muestra)
    PAISES = {
        'PRY': 'Paraguay',
        'ARG': 'Argentina', 
        'BRA': 'Brasil',
        'URY': 'Uruguay',
        'BOL': 'Bolivia',
        'CHL': 'Chile',
        'USA': 'Estados Unidos',
        'ESP': 'España',
        'DEU': 'Alemania',
        'FRA': 'Francia'
    }
    
    # Tabla de unidades de medida
    UNIDADES_MEDIDA = {
        77: 'UNI',
        83: 'kg',
        86: 'g', 
        87: 'm',
        88: 'ML',
        89: 'LT',
        91: 'CM',
        95: 'MM',
        99: 'TN',
        100: 'Hs',
        104: 'DET',
        108: 'MT',
        109: 'M2',
        110: 'M3'
    }
    
    # INCOTERMS
    INCOTERMS = {
        'CFR': 'Costo y flete',
        'CIF': 'Costo, seguro y flete',
        'CIP': 'Transporte y seguro pagados hasta',
        'CPT': 'Transporte pagado hasta',
        'DAP': 'Entregada en lugar convenido',
        'DAT': 'Entregada en terminal',
        'DDP': 'Entregada derechos pagados',
        'EXW': 'En fábrica',
        'FAS': 'Franco al costado del buque',
        'FCA': 'Franco transportista',
        'FOB': 'Franco a bordo'
    }
    
    @staticmethod
    def validar_codigo_pais(codigo: str) -> bool:
        """Validar código de país ISO 3166-1"""
        return len(codigo) == 3 and codigo.upper() in ValidadorCodigos.PAISES
    
    @staticmethod
    def obtener_descripcion_pais(codigo: str) -> Optional[str]:
        """Obtener descripción del país"""
        return ValidadorCodigos.PAISES.get(codigo.upper())
    
    @staticmethod
    def validar_unidad_medida(codigo: int) -> bool:
        """Validar código de unidad de medida"""
        return codigo in ValidadorCodigos.UNIDADES_MEDIDA
    
    @staticmethod
    def obtener_representacion_unidad(codigo: int) -> Optional[str]:
        """Obtener representación de unidad de medida"""
        return ValidadorCodigos.UNIDADES_MEDIDA.get(codigo)
    
    @staticmethod
    def validar_incoterm(codigo: str) -> bool:
        """Validar código INCOTERM"""
        return codigo.upper() in ValidadorCodigos.INCOTERMS
    
    @staticmethod
    def obtener_descripcion_incoterm(codigo: str) -> Optional[str]:
        """Obtener descripción del INCOTERM"""
        return ValidadorCodigos.INCOTERMS.get(codigo.upper())
    
    @staticmethod
    def validar_tipo_regimen(codigo: int) -> bool:
        """Validar tipo de régimen"""
        return 1 <= codigo <= 8
    
    @staticmethod
    def validar_afectacion_iva(codigo: int) -> bool:
        """Validar código de afectación IVA"""
        return 1 <= codigo <= 4
```

### **Consultor de Actividades Económicas**
```python
import requests
from typing import Dict, Optional

class ConsultorActividadEconomica:
    """Consultor para actividades económicas de SET"""
    
    BASE_URL = "https://servicios.set.gov.py/eset-publico/consultarActividadEconomicaIService.do"
    
    @staticmethod
    async def consultar_actividad(codigo: str) -> Optional[Dict]:
        """Consultar actividad económica por código"""
        try:
            # En implementación real, hacer request al WS de SET
            # Por ahora simulamos la respuesta
            actividades_mock = {
                "620100": "Programación informática",
                "471120": "Venta al por menor en comercios no especializados",
                "561010": "Actividades de restaurantes y de servicio móvil de comidas",
                "841110": "Actividades ejecutivas de la administración pública"
            }
            
            if codigo in actividades_mock:
                return {
                    "codigo": codigo,
                    "descripcion": actividades_mock[codigo],
                    "estado": "activa"
                }
            return None
            
        except Exception as e:
            print(f"Error consultando actividad económica: {e}")
            return None
    
    @staticmethod
    def validar_codigo_actividad(codigo: str) -> bool:
        """Validar formato de código de actividad"""
        return len(codigo) == 6 and codigo.isdigit()
```

### **Generador de Campos con Códigos**
```python
class GeneradorCamposCodificados:
    """Generar campos XML con códigos validados"""
    
    @staticmethod
    def generar_emisor_direccion(departamento: int, distrito: int, 
                                ciudad: int, desc_ciudad: str) -> str:
        """Generar campos de dirección del emisor"""
        return f"""
        <cDepEmi>{departamento}</cDepEmi>
        <cDisEmi>{distrito}</cDisEmi>
        <cCiuEmi>{ciudad}</cCiuEmi>
        <dDesCiuEmi>{desc_ciudad}</dDesCiuEmi>
        """
    
    @staticmethod
    def generar_item_unidad_medida(codigo_unidad: int, cantidad: float) -> str:
        """Generar campos de unidad de medida para ítem"""
        if not ValidadorCodigos.validar_unidad_medida(codigo_unidad):
            raise ValueError(f"Código de unidad inválido: {codigo_unidad}")
        
        representacion = ValidadorCodigos.obtener_representacion_unidad(codigo_unidad)
        
        return f"""
        <cUniMed>{codigo_unidad}</cUniMed>
        <dDesUniMed>{representacion}</dDesUniMed>
        <dCantProSer>{cantidad:.2f}</dCantProSer>
        """
    
    @staticmethod
    def generar_pais_origen(codigo_pais: str) -> str:
        """Generar campos de país de origen"""
        if not ValidadorCodigos.validar_codigo_pais(codigo_pais):
            raise ValueError(f"Código de país inválido: {codigo_pais}")
        
        descripcion = ValidadorCodigos.obtener_descripcion_pais(codigo_pais)
        
        return f"""
        <cPaisOrig>{codigo_pais.upper()}</cPaisOrig>
        <dDesPaisOrig>{descripcion}</dDesPaisOrig>
        """
```

## 🔍 **Consultas y Actualizaciones**

### **Fuentes Oficiales de Actualización**
1. **Actividades Económicas**: Consulta dinámica a SET
2. **Códigos Geográficos**: Archivo Excel descargable
3. **Países**: ISO 3166-1 (actualización anual)
4. **Monedas**: ISO 4217 (actualización periódica)
5. **INCOTERMS**: Cámara de Comercio Internacional
6. **Regímenes Aduaneros**: Dirección Nacional de Aduanas

### **Implementación de Cache**
```python
import json
from datetime import datetime, timedelta
from typing import Dict, Any

class CacheTablasCodigos:
    """Cache para tablas de códigos con actualización automática"""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, datetime] = {}
        self.ttl_horas = 24  # Time to live en horas
    
    async def obtener_actividades_economicas(self) -> Dict:
        """Obtener actividades económicas con cache"""
        if self._cache_valido('actividades'):
            return self.cache['actividades']
        
        # Consultar WS de SET
        actividades = await self._consultar_actividades_set()
        self._guardar_cache('actividades', actividades)
        return actividades
    
    async def obtener_codigos_geograficos(self) -> Dict:
        """Obtener códigos geográficos con cache"""
        if self._cache_valido('geograficos'):
            return self.cache['geograficos']
        
        # Descargar archivo Excel de SET
        geograficos = await self._descargar_geograficos_set()
        self._guardar_cache('geograficos', geograficos)
        return geograficos
    
    def _cache_valido(self, clave: str) -> bool:
        """Verificar si el cache es válido"""
        if clave not in self.timestamps:
            return False
        
        tiempo_transcurrido = datetime.now() - self.timestamps[clave]
        return tiempo_transcurrido < timedelta(hours=self.ttl_horas)
    
    def _guardar_cache(self, clave: str, datos: Any):
        """Guardar datos en cache"""
        self.cache[clave] = datos
        self.timestamps[clave] = datetime.now()
    
    async def _consultar_actividades_set(self) -> Dict:
        """Consultar actividades económicas a SET"""
        # Implementar consulta real al WS
        pass
    
    async def _descargar_geograficos_set(self) -> Dict:
        """Descargar códigos geográficos de SET"""
        # Implementar descarga del Excel
        pass
```

---

**📝 Notas de Implementación:**
- Mantener actualizadas las tablas de códigos según fuentes oficiales
- Implementar validación local antes de envío a SIFEN
- Considerar cache para consultas externas frecuentes
- Validar códigos antes de generar XML

**🔄 Última actualización**: Basado en Manual Técnico SIFEN v150