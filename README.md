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

- **Mejor compatibilidad Linux/Mac/ARM** — se eliminó completamente el soporte para Python 2.7
- **Python 3.9 a 3.13 (matriz probada en CI)** — se eliminó completamente el soporte para Python 2.7
- **Dependencias actualizadas** — cryptography, Pillow, qrcode, dbf y otras llevan versiones modernas
- **Código limpio** — removidos imports de compatibilidad (`future`, `past`, `builtins`)
- **Versionado semántico** — reemplaza la numeración de revisiones Mercurial por semver (`v1.0.0`)
- **pysimplesoap vendoreado y mantenido** — incluido como `pyarcaws._vendor.pysimplesoap`, portado a Python 3 (caché WSDL, comparación de versiones, `getargspec`) y con un fix de `elementFormDefault="unqualified"` para que el envelope generado sea aceptado por servicios como WSLSP; instala como wheel. El paquete de PyPI está abandonado/roto.
- **Bugs silenciosos de producción corregidos** — p. ej. la lógica de reintentos en `utils.py` que comparaba `e[0]` en vez de `e.errno` (rota en Python 3) ahora reintenta correctamente ante cortes de conexión; y el parseo tolerante de nodos repetibles SOAP (una sola `<Obs>`/`<Err>` ya no lanza `TypeError`).
- **Suite de tests con cassettes VCR** — gran parte de los tests reproducen las respuestas grabadas sin pegarle a la red; además los tests unitarios nuevos (`pytest -m dontusefix`) corren sin certificado ni conexión.

---

Información general:
--------------------

- **Este fork:** https://github.com/aamalinux/pyarcaws
- **Historial de cambios:** [CHANGELOG.md](CHANGELOG.md)
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

**ARCA (ex AFIP):**

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
  (Alcance 4, Alcance 5 / Constancia de Inscripción, Alcance 10)

**ARBA:**

- [COT][20]: Código de Operación de Traslado (remito electrónico provincial)

**ANMAT/SEDRONAR/SENASA (SNT):**

- [TrazaMed][21]: trazabilidad de medicamentos
- [TrazaRenpre][24]: trazabilidad de precursores químicos controlados
- [TrazaFito][25]: trazabilidad de productos fitosanitarios

---

Notas de compatibilidad
-----------------------

**Validación del certificado SSL del servidor (cambio de comportamiento):**

- Desde la próxima versión, las conexiones a ARCA **validan el certificado del
  servidor por defecto** (`check_hostname` + `CERT_REQUIRED`) usando `certifi`.
  Antes viajaban sin validar (expuestas a MITM). Los endpoints de ARCA usan
  certificados públicos válidos, así que no debería romper nada.
- Para usar un CA propio: `Conectar(..., cacert="/ruta/ca.pem")`. Para
  desactivar la validación (sólo depuración): `Conectar(..., cacert=False)` —
  emite un `UserWarning`, nunca es silencioso.

**WSCDC / WSFEv1 — parseo tolerante de nodos repetibles:**

- Los nodos `maxOccurs="unbounded"` (`<Errors>/<Err>`, `<Events>/<Evt>`,
  `<Observaciones>/<Obs>`, y en `FECompConsultar` también `<Iva>`, `<Tributos>`,
  `<CbtesAsoc>`, `<Opcionales>`, `<Compradores>`, `<Actividades>`) llegan como
  **dict único** cuando hay un solo hijo y como **lista** cuando hay varios. El
  parseo se normaliza con `como_lista` / `normalizar_lista_soap` (helpers de
  `utils.py`) para tolerar ambas formas y no lanzar
  `TypeError: string indices must be integers`. En particular, una constatación
  WSCDC con `Resultado='R'` y una sola observación (p. ej. Obs 100 "CAE no
  existe" u Obs 110 "importe no se corresponde") ahora puebla `Obs`/
  `Observaciones` correctamente en vez de explotar.

**WSLSP — consulta de liquidaciones (veredicto definitivo):**

Verificado contra los WSDL vivos de **homologación y producción (11/06/2026)**:

- La única consulta puntual es **`consultarLiquidacionPorNroComprobante`** (más
  la variante avícola). Identifica la liquidación por
  `puntoVenta + tipoComprobante + nroComprobante`, acotada al CUIT autenticado.
  Es **emisor-céntrica**: no existe consulta por CAE, por receptor/comprador ni
  por período. Autenticá con el certificado del **emisor**.
- `ConsultarLiquidacion(tipo_cbte=..., pto_vta=..., nro_cbte=...)` es la forma
  correcta. El parámetro `cuit_comprador` se mantiene por compatibilidad pero
  **se ignora** (emite `UserWarning`): ARCA descartó la consulta por comprador.
- `ConsultarLiquidacion(cae=...)` falla con un error claro: la operación
  `consultarLiquidacionPorCae` **no existe ni en homologación ni en producción**.
  Podés chequear disponibilidad con `wslsp.OperacionDisponible(nombre)`.
- El `pdf` es sólo el nombre de archivo **local** donde guardar el PDF que viene
  en la respuesta; no viaja ningún elemento `pdf` ni `cuitComprador` en la
  solicitud (el schema vivo los rechaza).
- Nota técnica: el WSDL de WSLSP usa `elementFormDefault="unqualified"`; el
  pysimplesoap vendoreado fue corregido para no calificar con namespace los
  elementos hoja de schemas unqualified (antes generaba un envelope que el
  servicio rechazaba). El fix respeta `elementFormDefault` y no afecta a los
  servicios `qualified` (WSFEv1, WSCDC, etc.).

**Padrón Alcance 5 → Constancia de Inscripción:**

- ARCA **deprecó** `ws_sr_padron_a5`. Usá **`WSSrConstanciaInscripcion`**
  (servicio WSAA `ws_sr_constancia_inscripcion`, Consulta a Padrón Constancia de
  Inscripción, manual V4.1), que invoca **`getPersona_v2`** sobre el mismo
  endpoint SOAP `personaServiceA5`. Instanciar `WSSrPadronA5` emite un
  `DeprecationWarning`; sigue funcionando para no romper compatibilidad.
- `WSSrConstanciaInscripcion.Consultar(cuit)` puebla los campos clásicos
  (denominación, domicilio, impuestos, actividades, `cat_iva`, etc.) y además
  `self.caracterizaciones` — lista de `{id, descripcion, periodo,
  fecha_solicitud}`. El tag **`fechaSolicitud`** (xs:int) es opcional, sólo
  presente desde el 11/02/2026; se expone cuando viene y es `None` si falta.
  Helper `TieneCaracterizacion(id)` para detectar, p. ej., la **639**
  (Ganancias Simplificada Ley 27.779), que la constancia clásica no publicaba.
- Los bloques de error (`errorConstancia` / `errorMonotributo` /
  `errorRegimenGeneral`) se parsean tolerando dict único vs lista (no explotan
  con `TypeError` ante un solo error).

**Padrón — alcances y servicios deprecados:**

- Los padrones viejos **N3 y N10 fueron reemplazados** por los WebServices de
  **Alcance 4** (`WSSrPadronA4`, `ws_sr_padron_a4`) y **Alcance 10**
  (`WSSrPadronA10`, `ws_sr_padron_a10`) respectivamente.
- **`WSSrPadronA10`** (Alcance 10) es la versión liviana para validación rápida
  de un CUIT: `Consultar(cuit)` puebla denominación, tipo/nro de documento,
  estado de la clave, domicilio(s) y la actividad principal
  (`actividad_principal`). No trae impuestos/actividades detalladas/categorías
  ni caracterizaciones (para eso usar Alcance 4 o la Constancia de Inscripción).
  Verificado contra el WSDL vivo `personaServiceA10` (operación `getPersona`,
  sin `getPersona_v2`); los errores de negocio llegan como SOAP fault.
- **Alcance 100** (`ws_sr_padron_a100`, consulta de parámetros del Sistema
  Registral): servicio **identificado y disponible** — el WSDL vive bajo
  `sr-parametros/webservices/parameterServiceA100` (no `sr-padron`), operación
  `getParameterCollectionByName`. Aún **no implementado** en la librería; ver
  [docs/a100_servicio_real.md](docs/a100_servicio_real.md) (URLs, esquema y
  estimación de esfuerzo).

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

### Certificado digital (homologación, autogestión WSASS)

Necesitás un certificado (`.crt`) y su clave privada (`.key`) para autenticarte
con ARCA. Para **homologación** se obtiene gratis por autogestión en el portal
**WSASS** de ARCA. Pasos:

1. Generar la clave privada y el pedido de certificado (CSR) localmente:

   ```bash
   openssl genrsa -out homo.key 2048
   openssl req -new -key homo.key \
     -subj "/C=AR/O=MiEmpresa/CN=miAlias/serialNumber=CUIT 20XXXXXXXXX" \
     -out homo.csr
   ```

2. Ingresá al portal **WSASS** ("Autogestión de certificados para Web Services
   en ambientes de homologación") con **Clave Fiscal nivel 3**. Si el servicio
   no aparece, adherilo primero desde el **Administrador de Relaciones** de
   Clave Fiscal. Elegí **"Nuevo certificado"**, pegá el contenido de `homo.csr`
   y guardá el `.crt` que devuelve.

3. En **"Crear autorización a servicio"**, autorizá el DN del certificado a
   cada Web Service que vayas a probar; por ejemplo: `wsfe`, `wscdc`,
   `ws_sr_padron_a4`, `ws_sr_constancia_inscripcion`, `wslsp`.

> **WSASS es solo para homologación.** Para **producción** el trámite es
> distinto: certificado de producción (Clave Fiscal / portal de ARCA) y
> delegación del servicio en el **Administrador de Relaciones**.

> ⚠️ El histórico `reingart.zip` (`reingart.crt`/`reingart.key`) que recomendaba
> el README original **está vencido** y ya no sirve para autenticarse; usá la
> autogestión WSASS de arriba.

### Verificación rápida

```bash
python -m pyarcaws.wsaa           # obtener ticket de autorización
python -m pyarcaws.wsfev1 --prueba  # emitir factura de prueba (CAE de homologación)
```

### Ejecutar tests

Los tests usan cassettes VCR (respuestas grabadas), así que no le pegan a la red:

```bash
pytest tests
# o con el Makefile:
make test
```

Los tests unitarios que no requieren certificado ni conexión se corren con:

```bash
pytest -m dontusefix
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
