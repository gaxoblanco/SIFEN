"""
Fixtures de documentos XML para tests de integración SIFEN

Contiene templates XML válidos e inválidos basados en:
- Manual Técnico SIFEN v150
- Esquemas XSD oficiales
- Casos de test reales del ambiente SIFEN

Tipos de documentos:
- Factura Electrónica (FE) - Tipo 1
- Nota de Crédito (NCE) - Tipo 5  
- Documentos inválidos para tests de error
"""

from datetime import datetime
from typing import Optional, Tuple, List

# =====================================
# FACTURA ELECTRÓNICA VÁLIDA (FE)
# =====================================

VALID_FACTURA_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd" 
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd">
    <dVerFor>150</dVerFor>
    <DE Id="01{ruc_emisor}001001000000120240101100000123456789">
        <gOpeDE>
            <iTipDE>1</iTipDE>
            <dNumID>{numero_documento}</dNumID>
            <dFeEmiDE>{fecha_emision}</dFeEmiDE>
            <iTipEmi>1</iTipEmi>
        </gOpeDE>
        
        <gTimb>
            <iTiDE>1</iTiDE>
            <dNumTim>12345678</dNumTim>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>0000001</dNumDoc>
            <dSerieNum>A</dSerieNum>
            <dFeIniT>2024-01-01</dFeIniT>
        </gTimb>
        
        <gDatGralOpe>
            <dFeEmiDE>{fecha_emision}</dFeEmiDE>
            <iTipTra>1</iTipTra>
            <iTImp>1</iTImp>
            <cMoneOpe>PYG</cMoneOpe>
            <dCondTiCam>1</dCondTiCam>
            <dTiCam>1</dTiCam>
            <iCondAnt>1</iCondAnt>
        </gDatGralOpe>
        
        <gDatGralOpe>
            <gOpeCom>
                <iTipTra>1</iTipTra>
                <dDesTipTra>Venta de mercaderia</dDesTipTra>
                <iTImp>1</iTImp>
                <dDesTImp>IVA</dDesTImp>
                <cMoneOpe>PYG</cMoneOpe>
                <dDesMoneOpe>Guarani</dDesMoneOpe>
                <dCondTiCam>1</dCondTiCam>
                <dTiCam>1.00</dTiCam>
            </gOpeCom>
        </gDatGralOpe>
        
        <gDatRec>
            <iNatRec>1</iNatRec>
            <iTiOpe>1</iTiOpe>
            <cPaisRec>PRY</cPaisRec>
            <iTiContRec>1</iTiContRec>
            <dRucRec>4444444</dRucRec>
            <dDVRec>4</dDVRec>
            <dNomRec>Cliente de Prueba S.A.</dNomRec>
            <dNomFanRec>Cliente Test</dNomFanRec>
            <dDirRec>Av. Test 123</dDirRec>
            <dNumCasRec>456</dNumCasRec>
            <cDepRec>11</cDepRec>
            <dDesDepRec>ALTO PARANA</dDesDepRec>
            <cDisRec>143</cDisRec>
            <dDesDisRec>CIUDAD DEL ESTE</dDesDisRec>
            <cCiuRec>3344</cCiuRec>
            <dDesCiuRec>CIUDAD DEL ESTE</dDesCiuRec>
            <dTelRec>0981123456</dTelRec>
            <dCelRec>0981123456</dCelRec>
            <dEmailRec>cliente@test.com</dEmailRec>
            <dCodCliente>CLI001</dCodCliente>
        </gDatRec>
        
        <gDatEm>
            <dRucEm>{ruc_emisor}</dRucEm>
            <dDVEmi>5</dDVEmi>
            <dNomEmi>Empresa Test S.A.</dNomEmi>
            <dNomFanEmi>Test Corp</dNomFanEmi>
            <dDirEmi>Av. Principal 123</dDirEmi>
            <dNumCasEmi>100</dNumCasEmi>
            <cDepEmi>11</cDepEmi>
            <dDesDepEmi>ALTO PARANA</dDesDepEmi>
            <cDisEmi>143</cDisEmi>
            <dDesDisEmi>CIUDAD DEL ESTE</dDesDisEmi>
            <cCiuEmi>3344</cCiuEmi>
            <dDesCiuEmi>CIUDAD DEL ESTE</dDesCiuEmi>
            <dTelEmi>021123456</dTelEmi>
            <dEmailEmi>test@empresa.com</dEmailEmi>
            <dDenSuc>Casa Matriz</dDenSuc>
        </gDatEm>
        
        <gDtipDE>
            <gCamFE>
                <iIndPres>1</iIndPres>
                <dDesIndPres>Operacion presencial</dDesIndPres>
                <iIndRec>1</iIndRec>
                <dDesIndRec>Contado</dDesIndRec>
                <iTipRec>1</iTipRec>
                <dDesTipRec>Efectivo</dDesTipRec>
                <dVTotRec>110000</dVTotRec>
                <iMoneTipRec>1</iMoneTipRec>
                <dDMoneTipRec>Guarani</dDMoneTipRec>
                <dTiCamTipRec>1.00</dTiCamTipRec>
            </gCamFE>
            
            <gCamItem>
                <dCodInt>PROD001</dCodInt>
                <dParAranc>123456</dParAranc>
                <dNCM>12345678</dNCM>
                <dDncpG>12345</dDncpG>
                <dDncpE>123456789</dDncpE>
                <dGtin>1234567890123</dGtin>
                <dGtinPq>1234567890123</dGtinPq>
                <dDesProSer>Producto de prueba</dDesProSer>
                <cUniMed>77</cUniMed>
                <dDesUniMed>Unidad</dDesUniMed>
                <dCantProSer>1.00</dCantProSer>
                <cPaisOrig>PRY</cPaisOrig>
                <dDesPaisOrig>Paraguay</dDesPaisOrig>
                <dInfItem>Informacion adicional del item</dInfItem>
                <cRelMerc>1</cRelMerc>
                <dDesRelMerc>Producto</dDesRelMerc>
                <dCanQuiMer>1.00</dCanQuiMer>
                <dPorDesc>0.00</dPorDesc>
                <dDescGloItem>0</dDescGloItem>
                <dAntPreUniIt>0</dAntPreUniIt>
                <dAntGloPreUniIt>0</dAntGloPreUniIt>
                <dTotAnt>0</dTotAnt>
                <dPUniProSer>100000.00</dPUniProSer>
                <dTiCamIt>1.00</dTiCamIt>
                <dTotBruOpeItem>100000</dTotBruOpeItem>
                
                <gValorItem>
                    <dPUniProSer>100000.00</dPUniProSer>
                    <dTiCamIt>1.00</dTiCamIt>
                    <dTotBruOpeItem>100000</dTotBruOpeItem>
                    <gValorRestaItem>
                        <dDescItem>0</dDescItem>
                        <dPorcDesIt>0.00</dPorcDesIt>
                        <dDescGloItem>0</dDescGloItem>
                        <dAntPreUniIt>0</dAntPreUniIt>
                        <dAntGloPreUniIt>0</dAntGloPreUniIt>
                        <dTotAnt>0</dTotAnt>
                        <dTotOpe>100000</dTotOpe>
                    </gValorRestaItem>
                </gValorItem>
                
                <gCamIVA>
                    <iAfecIVA>1</iAfecIVA>
                    <dDesAfecIVA>Gravado IVA</dDesAfecIVA>
                    <dPropIVA>10.00</dPropIVA>
                    <dTasaIVA>10.00</dTasaIVA>
                    <dBasGravIVA>100000</dBasGravIVA>
                    <dLiqIVAItem>10000</dLiqIVAItem>
                    <dBasExe>0</dBasExe>
                </gCamIVA>
            </gCamItem>
        </gDtipDE>
        
        <gTotSub>
            <dSubExe>0</dSubExe>
            <dSubExo>0</dSubExo>
            <dSub5>0</dSub5>
            <dSub10>100000</dSub10>
            <dTotOpe>100000</dTotOpe>
            <dTotDesc>0</dTotDesc>
            <dTotDescGloItem>0</dTotDescGloItem>
            <dTotAntItem>0</dTotAntItem>
            <dTotAnt>0</dTotAnt>
            <dPorcDescTotal>0.00</dPorcDescTotal>
            <dDescTotal>0</dDescTotal>
            <dAnticipo>0</dAnticipo>
            <dRedon>0</dRedon>
            <dComi>0</dComi>
            <dTotGralOpe>110000</dTotGralOpe>
            <dIVA5>0</dIVA5>
            <dIVA10>10000</dIVA10>
            <dLiqTotIVA10>10000</dLiqTotIVA10>
            <dIVAComi>0</dIVAComi>
            <dTotIVA>10000</dTotIVA>
            <dBaseGrav5>0</dBaseGrav5>
            <dBaseGrav10>100000</dBaseGrav10>
            <dTBasGraIVA>100000</dTBasGraIVA>
        </gTotSub>
        
        <gCamGen>
            <dFecVencEmi>2024-12-31</dFecVencEmi>
            <gCamCond>
                <iCondOpe>1</iCondOpe>
                <dDCondOpe>Contado</dDCondOpe>
            </gCamCond>
            
            <gCamItem>
                <dCodInt>PROD001</dCodInt>
                <dDesProSer>Producto de prueba</dDesProSer>
                <dCantProSer>1.00</dCantProSer>
                <dPUniProSer>100000.00</dPUniProSer>
                <dTotBruOpeItem>100000</dTotBruOpeItem>
            </gCamItem>
            
            <gPagTarCD>
                <iDenTarj>1</iDenTarj>
                <dDesDenTarj>Visa</dDesDenTarj>
                <dRSocTarj>Banco Test</dRSocTarj>
                <dRUCTarj>1234567</dRUCTarj>
                <dDVTarj>8</dDVTarj>
                <iForProPa>1</iForProPa>
                <dCodAuOpe>123456</dCodAuOpe>
                <dNomTit>TITULAR TEST</dNomTit>
                <dNumTarj>1234</dNumTarj>
            </gPagTarCD>
        </gCamGen>
        
        <gCamEspDE>
            <gGrupEner>
                <nItemEner>1</nItemEner>
                <dDescProdEner>Producto energetico</dDescProdEner>
                <dCantAntEner>100.00</dCantAntEner>
                <dCantActEner>200.00</dCantActEner>
                <dCantConEner>100.00</dCantConEner>
                <dPUniEner>1000.00</dPUniEner>
                <dTotEner>100000</dTotEner>
            </gGrupEner>
        </gCamEspDE>
        
        <gCamFuFD>
            <dCarQR>01|01{ruc_emisor}001001000000120240101100000123456789|{fecha_emision}|4444444|110000|10000|1|{csc}|ABC123</dCarQR>
        </gCamFuFD>
    </DE>
</rDE>'''


# =====================================
# NOTA DE CRÉDITO VÁLIDA (NCE)
# =====================================

VALID_NOTA_CREDITO_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd" 
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd DE_v150.xsd">
    <dVerFor>150</dVerFor>
    <DE Id="05{ruc_emisor}001001000000120240101100000123456789">
        <gOpeDE>
            <iTipDE>5</iTipDE>
            <dNumID>{numero_documento}</dNumID>
            <dFeEmiDE>{fecha_emision}</dFeEmiDE>
            <iTipEmi>1</iTipEmi>
        </gOpeDE>
        
        <gTimb>
            <iTiDE>5</iTiDE>
            <dNumTim>12345678</dNumTim>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>0000002</dNumDoc>
            <dSerieNum>B</dSerieNum>
            <dFeIniT>2024-01-01</dFeIniT>
        </gTimb>
        
        <gDatGralOpe>
            <dFeEmiDE>{fecha_emision}</dFeEmiDE>
            <iTipTra>1</iTipTra>
            <iTImp>1</iTImp>
            <cMoneOpe>PYG</cMoneOpe>
            <dCondTiCam>1</dCondTiCam>
            <dTiCam>1</dTiCam>
            <iCondAnt>1</iCondAnt>
        </gDatGralOpe>
        
        <gDatRec>
            <iNatRec>1</iNatRec>
            <iTiOpe>1</iTiOpe>
            <cPaisRec>PRY</cPaisRec>
            <iTiContRec>1</iTiContRec>
            <dRucRec>4444444</dRucRec>
            <dDVRec>4</dDVRec>
            <dNomRec>Cliente de Prueba S.A.</dNomRec>
            <dDirRec>Av. Test 123</dDirRec>
            <dNumCasRec>456</dNumCasRec>
            <cDepRec>11</cDepRec>
            <dDesDepRec>ALTO PARANA</dDesDepRec>
            <cDisRec>143</cDisRec>
            <dDesDisRec>CIUDAD DEL ESTE</dDesDisRec>
            <cCiuRec>3344</cCiuRec>
            <dDesCiuRec>CIUDAD DEL ESTE</dDesCiuRec>
            <dTelRec>0981123456</dTelRec>
            <dEmailRec>cliente@test.com</dEmailRec>
        </gDatRec>
        
        <gDatEm>
            <dRucEm>{ruc_emisor}</dRucEm>
            <dDVEmi>5</dDVEmi>
            <dNomEmi>Empresa Test S.A.</dNomEmi>
            <dDirEmi>Av. Principal 123</dDirEmi>
            <dNumCasEmi>100</dNumCasEmi>
            <cDepEmi>11</cDepEmi>
            <dDesDepEmi>ALTO PARANA</dDesDepEmi>
            <cDisEmi>143</cDisEmi>
            <dDesDisEmi>CIUDAD DEL ESTE</dDesDisEmi>
            <cCiuEmi>3344</cCiuEmi>
            <dDesCiuEmi>CIUDAD DEL ESTE</dDesCiuEmi>
            <dTelEmi>021123456</dTelEmi>
            <dEmailEmi>test@empresa.com</dEmailEmi>
        </gDatEm>
        
        <gDtipDE>
            <gCamNCE>
                <iMotEmi>1</iMotEmi>
                <dDesMotEmi>Devolucion de mercaderia</dDesMotEmi>
                <gCamFE>
                    <iIndPres>1</iIndPres>
                    <dDesIndPres>Operacion presencial</dDesIndPres>
                    <iIndRec>1</iIndRec>
                    <dDesIndRec>Contado</dDesIndRec>
                    <iTipRec>1</iTipRec>
                    <dDesTipRec>Efectivo</dDesTipRec>
                    <dVTotRec>55000</dVTotRec>
                    <iMoneTipRec>1</iMoneTipRec>
                    <dDMoneTipRec>Guarani</dDMoneTipRec>
                    <dTiCamTipRec>1.00</dTiCamTipRec>
                </gCamFE>
            </gCamNCE>
            
            <gCamItem>
                <dCodInt>PROD001</dCodInt>
                <dDesProSer>Producto devuelto</dDesProSer>
                <cUniMed>77</cUniMed>
                <dDesUniMed>Unidad</dDesUniMed>
                <dCantProSer>0.50</dCantProSer>
                <dPUniProSer>100000.00</dPUniProSer>
                <dTotBruOpeItem>50000</dTotBruOpeItem>
                
                <gValorItem>
                    <dPUniProSer>100000.00</dPUniProSer>
                    <dTotBruOpeItem>50000</dTotBruOpeItem>
                    <gValorRestaItem>
                        <dTotOpe>50000</dTotOpe>
                    </gValorRestaItem>
                </gValorItem>
                
                <gCamIVA>
                    <iAfecIVA>1</iAfecIVA>
                    <dDesAfecIVA>Gravado IVA</dDesAfecIVA>
                    <dPropIVA>10.00</dPropIVA>
                    <dTasaIVA>10.00</dTasaIVA>
                    <dBasGravIVA>50000</dBasGravIVA>
                    <dLiqIVAItem>5000</dLiqIVAItem>
                </gCamIVA>
            </gCamItem>
        </gDtipDE>
        
        <gTotSub>
            <dSubExe>0</dSubExe>
            <dSubExo>0</dSubExo>
            <dSub5>0</dSub5>
            <dSub10>50000</dSub10>
            <dTotOpe>50000</dTotOpe>
            <dTotGralOpe>55000</dTotGralOpe>
            <dIVA10>5000</dIVA10>
            <dTotIVA>5000</dTotIVA>
            <dBaseGrav10>50000</dBaseGrav10>
            <dTBasGraIVA>50000</dTBasGraIVA>
        </gTotSub>
        
        <gCamGen>
            <gCamCond>
                <iCondOpe>1</iCondOpe>
                <dDCondOpe>Contado</dDCondOpe>
            </gCamCond>
        </gCamGen>
        
        <gCamDEAsoc>
            <iTipDocAso>1</iTipDocAso>
            <dDesTipDocAso>Factura Electronica</dDesTipDocAso>
            <dCdCDERef>01{ruc_emisor}001001000000120240101100000123456788</dCdCDERef>
            <dNTimDI>12345678</dNTimDI>
            <dEstDI>001</dEstDI>
            <dPExpDI>001</dPExpDI>
            <dNumDI>0000001</dNumDI>
            <dSerieNum>A</dSerieNum>
            <dFecEmiDI>2024-01-01</dFecEmiDI>
        </gCamDEAsoc>
        
        <gCamFuFD>
            <dCarQR>05|05{ruc_emisor}001001000000120240101100000123456789|{fecha_emision}|4444444|55000|5000|1|{csc}|DEF456</dCarQR>
        </gCamFuFD>
    </DE>
</rDE>'''


# =====================================
# DOCUMENTOS INVÁLIDOS PARA TESTS
# =====================================

INVALID_XML_MISSING_NAMESPACE = '''<?xml version="1.0" encoding="UTF-8"?>
<rDE version="150">
    <DE>
        <gOpeDE>
            <iTipDE>1</iTipDE>
            <dNumID>001-001-0000001</dNumID>
            <dFeEmiDE>2024-01-01T10:00:00</dFeEmiDE>
        </gOpeDE>
    </DE>
</rDE>'''

INVALID_XML_MALFORMED = '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <DE>
        <gOpeDE>
            <iTipDE>1</iTipDE>
            <dNumID>001-001-0000001</dNumID>
            <dFeEmiDE>2024-01-01T10:00:00</dFeEmiDE>
        </gOpeDE>
        <!-- XML mal cerrado - falta </DE> -->
    </DE>
<!-- XML mal formado - falta </rDE> -->'''

INVALID_XML_WRONG_STRUCTURE = '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <DE>
        <!-- Estructura incorrecta - faltan elementos requeridos -->
        <iTipDE>1</iTipDE>
        <dNumID>001-001-0000001</dNumID>
    </DE>
</rDE>'''

INVALID_XML_WRONG_VALUES = '''<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <dVerFor>150</dVerFor>
    <DE>
        <gOpeDE>
            <iTipDE>99</iTipDE>  <!-- Tipo de documento inválido -->
            <dNumID>INVALID-FORMAT</dNumID>  <!-- Formato incorrecto -->
            <dFeEmiDE>invalid-date</dFeEmiDE>  <!-- Fecha inválida -->
            <iTipEmi>9</iTipEmi>  <!-- Tipo emisión inválido -->
        </gOpeDE>
        
        <gTimb>
            <iTiDE>99</iTiDE>  <!-- Tipo DE inválido -->
            <dNumTim>INVALID</dNumTim>  <!-- Timbrado inválido -->
            <dEst>ABCD</dEst>  <!-- Establecimiento inválido -->
            <dPunExp>EFGH</dPunExp>  <!-- Punto expedición inválido -->
            <dNumDoc>INVALID</dNumDoc>  <!-- Número documento inválido -->
        </gTimb>
        
        <gDatGralOpe>
            <dFeEmiDE>invalid-date</dFeEmiDE>
            <iTipTra>99</iTipTra>  <!-- Tipo transacción inválido -->
            <iTImp>99</iTImp>  <!-- Tipo impuesto inválido -->
            <cMoneOpe>XXX</cMoneOpe>  <!-- Moneda inválida -->
            <dTiCam>invalid</dTiCam>  <!-- Tipo cambio inválido -->
        </gDatGralOpe>
    </DE>
</rDE>'''


# =====================================
# RESPUESTAS MOCK DE SIFEN
# =====================================

SIFEN_SUCCESS_RESPONSE = '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Body>
        <ns2:rResEnviDE xmlns:ns2="http://ekuatia.set.gov.py/sifen/xsd">
            <ns2:dEstRes>1</ns2:dEstRes>
            <ns2:dProtAut>01{ruc_emisor}001001000000120240101100000123456789</ns2:dProtAut>
            <ns2:dDigVal>ABC123DEF456GHI789</ns2:dDigVal>
            <ns2:dMsgRes>Aprobado</ns2:dMsgRes>
            <ns2:dCodRes>0260</ns2:dCodRes>
            <ns2:dMsgResDet>
                <ns2:rGesRec>
                    <ns2:Id>01{ruc_emisor}001001000000120240101100000123456789</ns2:Id>
                    <ns2:dFecProc>2024-01-01T10:15:00</ns2:dFecProc>
                    <ns2:dCodRes>0260</ns2:dCodRes>
                    <ns2:dMsgRes>Aprobado</ns2:dMsgRes>
                </ns2:rGesRec>
            </ns2:dMsgResDet>
        </ns2:rResEnviDE>
    </soap:Body>
</soap:Envelope>'''

SIFEN_ERROR_RESPONSE_1250 = '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Body>
        <ns2:rResEnviDE xmlns:ns2="http://ekuatia.set.gov.py/sifen/xsd">
            <ns2:dEstRes>0</ns2:dEstRes>
            <ns2:dProtAut></ns2:dProtAut>
            <ns2:dDigVal></ns2:dDigVal>
            <ns2:dMsgRes>Rechazado</ns2:dMsgRes>
            <ns2:dCodRes>1250</ns2:dCodRes>
            <ns2:dMsgResDet>
                <ns2:rGesRec>
                    <ns2:Id></ns2:Id>
                    <ns2:dFecProc>2024-01-01T10:15:00</ns2:dFecProc>
                    <ns2:dCodRes>1250</ns2:dCodRes>
                    <ns2:dMsgRes>RUC emisor inexistente</ns2:dMsgRes>
                </ns2:rGesRec>
            </ns2:dMsgResDet>
        </ns2:rResEnviDE>
    </soap:Body>
</soap:Envelope>'''

SIFEN_ERROR_RESPONSE_1000 = '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Body>
        <ns2:rResEnviDE xmlns:ns2="http://ekuatia.set.gov.py/sifen/xsd">
            <ns2:dEstRes>0</ns2:dEstRes>
            <ns2:dProtAut></ns2:dProtAut>
            <ns2:dDigVal></ns2:dDigVal>
            <ns2:dMsgRes>Rechazado</ns2:dMsgRes>
            <ns2:dCodRes>1000</ns2:dCodRes>
            <ns2:dMsgResDet>
                <ns2:rGesRec>
                    <ns2:Id></ns2:Id>
                    <ns2:dFecProc>2024-01-01T10:15:00</ns2:dFecProc>
                    <ns2:dCodRes>1000</ns2:dCodRes>
                    <ns2:dMsgRes>CDC no corresponde con XML</ns2:dMsgRes>
                </ns2:rGesRec>
            </ns2:dMsgResDet>
        </ns2:rResEnviDE>
    </soap:Body>
</soap:Envelope>'''

SIFEN_TIMEOUT_RESPONSE = '''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Body>
        <soap:Fault>
            <soap:Code>
                <soap:Value>soap:Receiver</soap:Value>
            </soap:Code>
            <soap:Reason>
                <soap:Text>Gateway Timeout</soap:Text>
            </soap:Reason>
            <soap:Detail>
                <errorCode>504</errorCode>
                <errorMessage>El servidor no pudo procesar la solicitud en el tiempo esperado</errorMessage>
            </soap:Detail>
        </soap:Fault>
    </soap:Body>
</soap:Envelope>'''


# =====================================
# DATOS DE PRUEBA ADICIONALES
# =====================================

TEST_CERTIFICATE_DATA = {
    'valid_serial': '1234567890ABCDEF',
    'invalid_serial': 'INVALID',
    'test_ruc': '80016875-5',  # RUC oficial para ambiente test SIFEN
    'test_password': 'test_password_123',
    'cert_path': '/tmp/test_certificate.p12'
}

TEST_CSC_CODES = [
    'TEST1234',
    'DEMO5678',
    'PRUEBA90',
    'SAMPLE12',
    'TESTCODE'
]

TEST_DOCUMENT_NUMBERS = [
    '001-001-0000001',
    '001-001-0000002',
    '001-001-0000003',
    '001-001-0000004',
    '001-001-0000005'
]

ERROR_TEST_SCENARIOS = [
    {
        'name': 'ruc_inexistente',
        'ruc': '99999999',
        'expected_code': '1250',
        'description': 'RUC emisor inexistente en base SIFEN'
    },
    {
        'name': 'cdc_duplicado',
        'cdc_duplicate': True,
        'expected_code': '1001',
        'description': 'CDC duplicado enviado anteriormente'
    },
    {
        'name': 'timbrado_invalido',
        'timbrado': '00000000',
        'expected_code': '1101',
        'description': 'Número de timbrado inválido'
    },
    {
        'name': 'xml_malformado',
        'xml_malformed': True,
        'expected_code': '1000',
        'description': 'XML no corresponde con CDC generado'
    }
]


# =====================================
# HELPER FUNCTIONS
# =====================================

def get_valid_factura_xml(
    ruc_emisor: str = "80016875",
    fecha_emision: Optional[str] = None,
    numero_documento: str = "001-001-0000001",
    csc: str = "TEST1234"
) -> str:
    """
    Genera XML de factura válida con parámetros personalizables

    Args:
        ruc_emisor: RUC del emisor (sin guión)
        fecha_emision: Fecha en formato ISO (default: ahora)
        numero_documento: Número de documento
        csc: Código de seguridad del contribuyente

    Returns:
        XML formateado y listo para envío
    """
    if fecha_emision is None:
        fecha_emision = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    return VALID_FACTURA_XML.format(
        ruc_emisor=ruc_emisor,
        fecha_emision=fecha_emision,
        numero_documento=numero_documento,
        csc=csc
    )


def get_valid_nota_credito_xml(
    ruc_emisor: str = "80016875",
    fecha_emision: Optional[str] = None,
    numero_documento: str = "001-001-0000002",
    csc: str = "TEST5678"
) -> str:
    """
    Genera XML de nota de crédito válida
    """
    if fecha_emision is None:
        fecha_emision = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    return VALID_NOTA_CREDITO_XML.format(
        ruc_emisor=ruc_emisor,
        fecha_emision=fecha_emision,
        numero_documento=numero_documento,
        csc=csc
    )


def get_invalid_xml_by_type(error_type: str) -> str:
    """
    Retorna XML inválido según el tipo de error deseado

    Args:
        error_type: Tipo de error ('namespace', 'malformed', 'structure', 'values')

    Returns:
        XML inválido para testing
    """
    error_xmls = {
        'namespace': INVALID_XML_MISSING_NAMESPACE,
        'malformed': INVALID_XML_MALFORMED,
        'structure': INVALID_XML_WRONG_STRUCTURE,
        'values': INVALID_XML_WRONG_VALUES
    }

    return error_xmls.get(error_type, INVALID_XML_MALFORMED)


def get_sifen_mock_response(response_type: str, **kwargs) -> str:
    """
    Retorna respuesta mock de SIFEN según el tipo

    Args:
        response_type: Tipo de respuesta ('success', 'error_1250', 'error_1000', 'timeout')
        **kwargs: Parámetros adicionales para formatear la respuesta

    Returns:
        XML de respuesta SIFEN mock
    """
    responses = {
        'success': SIFEN_SUCCESS_RESPONSE,
        'error_1250': SIFEN_ERROR_RESPONSE_1250,
        'error_1000': SIFEN_ERROR_RESPONSE_1000,
        'timeout': SIFEN_TIMEOUT_RESPONSE
    }

    response = responses.get(response_type, SIFEN_SUCCESS_RESPONSE)

    # Formatear con parámetros si se proporcionan
    if kwargs:
        try:
            response = response.format(**kwargs)
        except KeyError:
            pass  # Ignorar claves faltantes

    return response


# =====================================
# VALIDADORES DE DOCUMENTOS
# =====================================

def validate_xml_structure(xml_content: str) -> tuple[bool, list[str]]:
    """
    Valida estructura básica del XML sin enviar a SIFEN

    Returns:
        tuple: (es_válido, lista_errores)
    """
    errors = []

    # Validaciones básicas
    if not xml_content.strip():
        errors.append("XML vacío")
        return False, errors

    if 'xmlns="http://ekuatia.set.gov.py/sifen/xsd"' not in xml_content:
        errors.append("Namespace SIFEN faltante")

    if '<dVerFor>150</dVerFor>' not in xml_content:
        errors.append("Versión de formato requerida")

    required_elements = ['<rDE', '<DE', '<gOpeDE>', '<iTipDE>', '<dNumID>']
    for element in required_elements:
        if element not in xml_content:
            errors.append(f"Elemento requerido faltante: {element}")

    return len(errors) == 0, errors


def get_cdc_from_xml(xml_content: str) -> str:
    """
    Extrae el CDC del atributo Id del elemento DE

    Returns:
        CDC extraído o string vacío si no se encuentra
    """
    import re

    # Buscar patrón: <DE Id="CDC_44_CHARS">
    pattern = r'<DE[^>]+Id="([^"]{44})"'
    match = re.search(pattern, xml_content)

    return match.group(1) if match else ""


# =====================================
# CONFIGURACIÓN DE TESTS
# =====================================

TEST_CONFIG = {
    'sifen_test_url': 'https://sifen-test.set.gov.py',
    'timeout_seconds': 30,
    'max_retries': 3,
    'expected_response_time_ms': 10000,  # 10 segundos máximo
    'certificate_validation': True,
    'ssl_verify': True,
    'batch_size_limit': 50,
    'concurrent_requests': 5
}


# =====================================
# DATOS PARA TESTS DE RENDIMIENTO
# =====================================

def generate_batch_documents(count: int, base_ruc: str = "80016875") -> list[tuple[str, str]]:
    """
    Genera una lista de documentos para tests de lotes

    Args:
        count: Número de documentos a generar
        base_ruc: RUC base para los documentos

    Returns:
        Lista de tuplas (xml_content, certificate_serial)
    """
    documents = []

    for i in range(count):
        xml_content = get_valid_factura_xml(
            ruc_emisor=base_ruc,
            numero_documento=f"001-001-{i+1:07d}",
            csc=f"BATCH{i:03d}"
        )

        documents.append((xml_content, TEST_CERTIFICATE_DATA['valid_serial']))

    return documents


def get_stress_test_scenarios():
    """
    Retorna escenarios para tests de estrés
    """
    return [
        {
            'name': 'small_batch',
            'document_count': 5,
            'max_concurrent': 3,
            'expected_time_max': 30
        },
        {
            'name': 'medium_batch',
            'document_count': 20,
            'max_concurrent': 5,
            'expected_time_max': 60
        },
        {
            'name': 'large_batch',
            'document_count': 50,
            'max_concurrent': 10,
            'expected_time_max': 120
        }
    ]


# =====================================
# MOCK RESPONSES PARA DIFERENTES ESCENARIOS
# =====================================

MOCK_RESPONSES = {
    'success_fast': {
        'response_time_ms': 500,
        'xml': SIFEN_SUCCESS_RESPONSE,
        'status_code': 200
    },
    'success_slow': {
        'response_time_ms': 8000,
        'xml': SIFEN_SUCCESS_RESPONSE,
        'status_code': 200
    },
    'error_1250_ruc_invalid': {
        'response_time_ms': 1000,
        'xml': SIFEN_ERROR_RESPONSE_1250,
        'status_code': 200
    },
    'error_1000_cdc_mismatch': {
        'response_time_ms': 1200,
        'xml': SIFEN_ERROR_RESPONSE_1000,
        'status_code': 200
    },
    'timeout_504': {
        'response_time_ms': 30000,
        'xml': SIFEN_TIMEOUT_RESPONSE,
        'status_code': 504
    },
    'connection_error': {
        'response_time_ms': 0,
        'xml': None,
        'status_code': 0,
        'exception': 'ConnectionError'
    }
}


# =====================================
# UTILIDADES DE VALIDACIÓN
# =====================================

def is_valid_cdc(cdc: str) -> bool:
    """
    Valida formato de CDC (44 caracteres numéricos)
    """
    return cdc is not None and len(cdc) == 44 and cdc.isdigit()


def is_valid_sifen_date(date_str: str) -> bool:
    """
    Valida formato de fecha SIFEN (ISO 8601)
    """
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def extract_ruc_from_cdc(cdc: str) -> str:
    """
    Extrae RUC del CDC (primeros 8 dígitos)
    """
    if is_valid_cdc(cdc):
        return cdc[:8]
    return ""


def extract_document_type_from_cdc(cdc: str) -> str:
    """
    Extrae tipo de documento del CDC (posiciones 9-10)
    """
    if is_valid_cdc(cdc):
        return cdc[8:10]
    return ""


# =====================================
# TEMPLATES PARA CASOS ESPECÍFICOS
# =====================================

def get_xml_with_large_items(item_count: int = 100) -> str:
    """
    Genera XML con muchos items para tests de rendimiento
    """
    base_xml = get_valid_factura_xml()

    # Generar items adicionales
    additional_items = ""
    for i in range(1, item_count):
        additional_items += f'''
            <gCamItem>
                <dCodInt>PROD{i:03d}</dCodInt>
                <dDesProSer>Producto {i}</dDesProSer>
                <cUniMed>77</cUniMed>
                <dDesUniMed>Unidad</dDesUniMed>
                <dCantProSer>1.00</dCantProSer>
                <dPUniProSer>1000.00</dPUniProSer>
                <dTotBruOpeItem>1000</dTotBruOpeItem>
                <gValorItem>
                    <dPUniProSer>1000.00</dPUniProSer>
                    <dTotBruOpeItem>1000</dTotBruOpeItem>
                    <gValorRestaItem>
                        <dTotOpe>1000</dTotOpe>
                    </gValorRestaItem>
                </gValorItem>
                <gCamIVA>
                    <iAfecIVA>1</iAfecIVA>
                    <dDesAfecIVA>Gravado IVA</dDesAfecIVA>
                    <dPropIVA>10.00</dPropIVA>
                    <dTasaIVA>10.00</dTasaIVA>
                    <dBasGravIVA>1000</dBasGravIVA>
                    <dLiqIVAItem>100</dLiqIVAItem>
                </gCamIVA>
            </gCamItem>'''

    # Insertar items adicionales antes del cierre de gDtipDE
    return base_xml.replace('</gDtipDE>', additional_items + '</gDtipDE>')


def get_xml_with_special_characters() -> str:
    """
    Genera XML con caracteres especiales para tests de encoding
    """
    return get_valid_factura_xml().replace(
        'Empresa Test S.A.',
        'Empresa Ñandú & Cía. S.A. (Ñ-ñ-ü-é-á)'
    ).replace(
        'Producto de prueba',
        'Producto con ñ, tildes á é í ó ú y símbolos &'
    )


# =====================================
# CONSTANTES PARA ASSERTIONS
# =====================================

EXPECTED_SUCCESS_CODES = ["0260"]  # Aprobado
EXPECTED_SUCCESS_WITH_OBSERVATIONS = ["1005"]  # Aprobado con observaciones
EXPECTED_ERROR_CODES = [
    "1000",  # CDC no corresponde
    "1001",  # CDC duplicado
    "1101",  # Timbrado inválido
    "1250",  # RUC inexistente
    "0141"   # Firma inválida
]

SIFEN_ENDPOINTS = {
    'test': {
        'base_url': 'https://sifen-test.set.gov.py',
        'send_document': '/de/ws/sync/recibe.wsdl',
        'send_batch': '/de/ws/async/recibe-lote.wsdl',
        'query_document': '/de/ws/consultas/consulta.wsdl',
        'query_ruc': '/de/ws/consultas/consulta-ruc.wsdl'
    },
    'production': {
        'base_url': 'https://sifen.set.gov.py',
        'send_document': '/de/ws/sync/recibe.wsdl',
        'send_batch': '/de/ws/async/recibe-lote.wsdl',
        'query_document': '/de/ws/consultas/consulta.wsdl',
        'query_ruc': '/de/ws/consultas/consulta-ruc.wsdl'
    }
}


# =====================================
# METADATA PARA TESTS
# =====================================

TEST_METADATA = {
    'module': 'sifen_client',
    'version': '1.0.0',
    'sifen_version': '150',
    'test_environment': 'sifen-test.set.gov.py',
    'manual_reference': 'Manual Técnico SIFEN v150',
    'last_updated': '2024-01-01',
    'test_categories': [
        'integration',
        'unit',
        'performance',
        'error_handling',
        'security'
    ]
}
