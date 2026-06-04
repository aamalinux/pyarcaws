pyarcaws
========

**pyarcaws** es un fork activo y mantenido de [pyafipws](https://github.com/reingart/pyafipws), la librería Python para operar con los servicios web de ARCA (Argentina) y otros organismos del Estado, principalmente relacionados con facturación electrónica, liquidaciones e impuestos.

---

**Autoría original:** Copyright 2008 - 2022 (C) Mariano Reingart [reingart@gmail.com](mailto:reingart@gmail.com) (creador y mantenedor original). Todos los derechos reservados.

**Fork mantenido por:** [aamalinux](https://github.com/aamalinux)

**Licencia:** LGPLv3+, con excepción "comercial" disponible para incluirlo y distribuirlo con programas propietarios (ver `licencia.txt`).

---

## ¿Por qué este fork?

El proyecto original [pyafipws](https://github.com/reingart/pyafipws) tiene muchos años de desarrollo, con el cambio de nombre de la AFIP a ARCA quise reflejar el nuevo nombre **pyarcaws** y continuar su desarrollo con los siguientes objetivos:

- **Solo Python 3.9+** — se eliminó completamente el soporte para Python 2.7
- **Dependencias actualizadas** — cryptography, Pillow, qrcode, dbf y otras llevan versiones modernas
- **Código limpio** — removidos imports de compatibilidad (`future`, `past`, `builtins`)
- **Versionado semántico** — reemplaza la numeración de revisiones Mercurial por semver (`v1.0.0`)

---

Información general:
--------------------

- **Este fork:** https://github.com/aamalinux/pyarcaws
- **Proyecto original:** https://github.com/reingart/pyafipws
- **Manual de usuario:** http://www.sistemasagiles.com.ar/trac/wiki/ManualPyAfipWs (Español)
- **Documentación original:** https://github.com/reingart/pyafipws/wiki (Español/Inglés)
- **Foro de la comunidad:** http://groups.google.com/group/pyafipws

Estructura del proyecto:
------------------------

- [Librería Python][1]: una clase auxiliar por cada servicio web para facilitar el uso de sus métodos y atributos
- Herramientas de [consola][4] (línea de comandos) con archivos de entrada/salida simplificados (TXT, DBF, JSON)
- Ejemplos para Java, .NET (C#, VB.NET), Visual Basic, Visual Fox Pro, Delphi, C, PHP
- Módulos para [OpenERP/Odoo][27] y [Tryton][28]

Funcionalidades:
----------------

- Formatos de intercambio soportados: TXT (longitud fija COBOL), CSV, DBF (Clipper/xBase/Harbour), XML, JSON
- Automatización completa para solicitar autenticación y autorización de comprobantes (CAE, COE, etc.)
- Soporte de proxy, caché XML y manipulación avanzada de XML
- Generación de PDF personalizable con diseñador visual (plantillas CSV)
- Utilidades para email, códigos de barras (PIL), configuración (.INI) y depuración

Servicios web soportados:
-------------------------

**AFIP:**

- [WSAA][10]: autenticación y autorización con firma criptográfica digital
- [WSFEv1][11]: mercado interno (factura electrónica) — [English][12]
- [WSMTXCA][22]: mercado interno (factura electrónica) con artículos y códigos de barras
- [WSCT][22b]: turismo (factura electrónica) — devolución de IVA para turistas extranjeros
- [WSBFEv1][13]: bonos fiscales (factura electrónica)
- [WSFEXv1][14]: comercio exterior (factura electrónica) — [English][15]
- [WSCTG][16]: agricultura (código de trazabilidad de granos)
- [WSLPG][17]: agricultura (liquidación primaria de granos)
- [WSLTV][17b]: agricultura (tabaco verde)
- [WSLUM][17c]: agricultura (lechería)
- [WSLSP][17d]: agricultura (sector pecuario/ganadero)
- [WSCDC][23]: constatación de comprobantes
- [Padrón de contribuyentes][26]: verificación de vendedores y compradores

**ARBA:**

- [COT][20]: Código de Operación de Traslado (remito electrónico provincial)

**ANMAT/SEDRONAR/SENASA (SNT):**

- [TrazaMed][21]: trazabilidad de medicamentos
- [TrazaRenpre][24]: trazabilidad de precursores químicos controlados
- [TrazaFito][25]: trazabilidad de productos fitosanitarios

---

Instalación:
------------

**Requisitos:**
- Python 3.9 o superior: https://www.python.org/downloads/

### Instalación rápida

```bash
git clone https://github.com/aamalinux/pyarcaws.git
cd pyarcaws
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

O usando el `Makefile`:

```bash
make install
```

### Certificado digital

Necesitás un certificado (.crt) y clave privada (.key) para autenticarte con AFIP
(ver [instrucciones de generación de certificados][29]).

Para pruebas podés usar el certificado de testing del autor original:

```bash
wget https://www.sistemasagiles.com.ar/soft/pyafipws/reingart.zip -O reingart.zip
python -m zipfile -e reingart.zip .
cp conf/*.ini .
```

### Verificación rápida

```bash
python -m pyafipws.wsaa           # obtener ticket de autorización
python -m pyafipws.wsfev1 --prueba  # emitir factura de prueba (CAE de homologación)
```

### Ejecutar tests

```bash
pytest tests
# o con el Makefile:
make test
```

---

Desarrollo:
-----------

Para contribuir a este fork o reportar problemas:
https://github.com/aamalinux/pyarcaws/issues

Para contribuir al proyecto original de Reingart:
https://github.com/reingart/pyafipws

---

 [1]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaElectronicaPython
 [4]: http://www.sistemasagiles.com.ar/trac/wiki/HerramientaFacturaElectronica
 [5]: http://www.sistemasagiles.com.ar/trac/wiki/PyRece
 [6]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaLibre
 [10]: http://www.sistemasagiles.com.ar/trac/wiki/ManualPyAfipWs#ServicioWebdeAutenticaciónyAutorizaciónWSAA
 [11]: http://www.sistemasagiles.com.ar/trac/wiki/ProyectoWSFEv1
 [12]: https://github.com/reingart/pyafipws/wiki/WSFEv1
 [13]: http://www.sistemasagiles.com.ar/trac/wiki/BonosFiscales
 [14]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaElectronicaExportacion
 [15]: https://github.com/reingart/pyafipws/wiki/WSFEX
 [16]: http://www.sistemasagiles.com.ar/trac/wiki/CodigoTrazabilidadGranos
 [17]: http://www.sistemasagiles.com.ar/trac/wiki/LiquidacionPrimariaGranos
 [17b]: http://www.sistemasagiles.com.ar/trac/wiki/LiquidacionTabacoVerde
 [17c]: http://www.sistemasagiles.com.ar/trac/wiki/LiquidacionUnicaMensualLecheria
 [17d]: http://www.sistemasagiles.com.ar/trac/wiki/LiquidacionSectorPecuario
 [20]: http://www.sistemasagiles.com.ar/trac/wiki/RemitoElectronicoCotArba
 [21]: http://www.sistemasagiles.com.ar/trac/wiki/TrazabilidadMedicamentos
 [22]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaElectronicaMTXCAService
 [22b]: http://www.sistemasagiles.com.ar/trac/wiki/FacturaElectronicaComprobantesTurismo
 [23]: http://www.sistemasagiles.com.ar/trac/wiki/ConstatacionComprobantes
 [24]: http://www.sistemasagiles.com.ar/trac/wiki/TrazabilidadPrecursoresQuimicos
 [25]: http://www.sistemasagiles.com.ar/trac/wiki/TrazabilidadProductosFitosanitarios
 [26]: http://www.sistemasagiles.com.ar/trac/wiki/PadronContribuyentesAFIP
 [27]: https://github.com/reingart/openerp_pyafipws
 [28]: https://github.com/tryton-ar/account_invoice_ar
 [29]: http://www.sistemasagiles.com.ar/trac/wiki/ManualPyAfipWs#Certificados
