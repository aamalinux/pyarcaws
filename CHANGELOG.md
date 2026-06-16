# Changelog

Todos los cambios notables de **pyarcaws** (fork de
[pyafipws](https://github.com/reingart/pyafipws)) se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
el proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Seguridad
- **`WebClient` — validación del certificado SSL activada por defecto** (fix de
  seguridad con **cambio de comportamiento**). Antes, `WebClient` (el cliente
  HTTP liviano que usan `padron.py`, `cot.py`, `iibb.py`, que **no** pasan por el
  `Conectar` hardeneado de `BaseWS`) hacía `disable_ssl_certificate_validation =
  cacert is None`: con el default `cacert=None` la validación quedaba
  **desactivada** (expuesta a MITM). Ahora valida por defecto contra el bundle de
  `certifi` (reusa `_ca_bundle`/`_advertir_ssl_inseguro` del transport vendoreado),
  alineado con el resto del repo. El opt-out de depuración sigue disponible con
  `cacert=False` (emite `UserWarning`, nunca silencioso). Además, una ruta de CA
  **relativa** (p. ej. `cot`/`iibb` con `"conf/arba.crt"`) ahora se resuelve a
  absoluta y, si falta, avisa y cae a `certifi` en vez de un error SSL opaco.
  Verificado: el endpoint `soa.afip.gob.ar` (cert `*.afip.gob.ar`) valida con
  `certifi`, así que el nuevo default no rompe la consulta de padrón.
- **Ticket de Acceso WSAA cacheado con permisos `0o600`.** El TA (token/sign,
  válido por horas) se escribía con el umask por defecto; ahora se crea con
  permisos de sólo-dueño (`os.open(..., 0o600)`; inocuo en Windows).

### Corregido
- **`PadronAFIP.Consultar` — respuesta no-JSON del padrón (SOA).** El método hacía
  `json.loads(self.response)` asumiendo siempre JSON; si el SOA respondía con HTML
  (p. ej. un **404** porque el endpoint público `soa.afip.gob.ar/sr-padron/v2/persona`
  se movió/discontinuó) explotaba con un críptico `JSONDecodeError`. Ahora se valida
  que la respuesta sea JSON (tolerando `bytes`) y, si no, se surge un mensaje
  accionable con el motivo y un fragmento del cuerpo. _Nota: al momento de este fix el
  endpoint SOA v2 de padrón devuelve 404; para consultar el padrón con servicio
  garantizado usar la familia autenticada (`ws_sr_padron_a4/a10/a13` /
  `ws_sr_constancia_inscripcion`)._
- **WSAA — expiración del TA por contenido, no sólo por `mtime`.** La frescura del
  TA cacheado se decidía con `getmtime + DEFAULT_TTL`, ignorando el
  `expirationTime` real; con un `TTL` distinto al default podía servirse un TA
  vencido. Ahora, en el cache-hit, se valida el `expirationTime` del TA leído (o
  se regenera si está vencido o el cache está corrupto). La rama de regeneración
  se extrajo a un helper privado `_solicitar_ta(...)`; `Autenticar` mantiene firma
  y comportamiento públicos.
- **WSFEv1 `CAESolicitar` — guarda de `FeDetResp`.** Una respuesta de error podía
  traer `FeCabResp` sin `FeDetResp` y reventar con `KeyError`; ahora se exige
  ambos y, si falta el detalle, se delega en `__analizar_errores` para surgir el
  motivo real.

### Cambiado
- **Higiene interna (sin impacto de API):** `WSFEv1.LeerFacturaX` acota su
  `except` a `(KeyError, IndexError, TypeError)` con log (antes `except:` mudo);
  en `BaseWS.Conectar` se quitó un `return False` inalcanzable y el `except:`
  final pasó a `except Exception:` (no captura `KeyboardInterrupt`/`SystemExit`);
  en WSAA el `raise` de `Autenticar` depende de `LanzarExcepciones` (no de `DEBUG`)
  y el `DEBUG` de módulo quedó en `False` por defecto (sólo controla los prints de
  diagnóstico, no la propagación de errores).

## [1.3.0] - 2026-06-16

### Pruebas
- **Cassettes de homologación (replay offline) para A13, WSLCA y WSAPOC.** Se
  grabaron contra homologación, con el certificado de autogestión WSASS,
  interacciones reales — WSDL vivo + respuesta — y se conectaron a tests de
  replay (`test_ws_sr_padron_a13_vcr.py`: `getPersona` + búsqueda inversa por
  documento; `test_wslca_vcr.py`: catálogos de caña de azúcar; `test_wsapoc_vcr.py`:
  consulta de apócrifos) que corren **sin red ni certificado** (`vcr` +
  `dontusefix`), validando el parseo contra el envelope real de ARCA. Cassettes
  **saneados**: token/sign del Ticket de Acceso reemplazados por placeholders y
  CUIT del titular por una sintética; las entidades consultadas son de
  homologación con datos de relleno (sin PII real).

### Agregado
- **Consulta de Apócrifos** (`WSAPOC`, módulo `wsapoc.py`, servicio WSAA
  `wsapoc`): verificado contra el WSDL vivo de homologación
  (`eapoc-ws-qaext.afip.gob.ar/Service.asmx`, .NET `asmx`, esquema `qualified`).
  Consulta el registro de facturas/contribuyentes apócrifos (base APOC) — caso
  de uso de validación de proveedores. Expone `Dummy`, `Consultar(cuit)`
  (`GetPublicacionAPOC` → `self.EsApocrifo` + `self.resultados`),
  `ConsultarTodos` (`GetAll`) y `ConsultarPorPublicacion(desde, hasta)`
  (`GetAllByPublicacion`). La autenticación va en `Credencial` con `Token`,
  `Sign` y **`CUITDelegado`** (no `cuit`/`cuitRepresentada`). Alias `Apocrifos`,
  registro COM, CLI. Tests offline con fakes + cassette de homologación (ver
  _Pruebas_). **Validado en vivo** contra homologación.
- **Padrón Alcance 13** (`WSSrPadronA13`, servicio WSAA `ws_sr_padron_a13`):
  verificado contra el WSDL vivo de homologación (`personaServiceA13`). Hereda
  `getPersona` de Alcance 10 (mismo parseo de `personaReturn` → `persona`) y
  agrega lo distintivo del alcance: la **búsqueda inversa por documento**
  (`getIdPersonaListByDocumento` → `ConsultarListaPersonaPorDocumento(documento)`
  → `self.personas`, lista de CUIT/CUIL/CDI), que A4/A5/A10 no cubren. Flag de
  CLI `--a13` (con `--documento`), alias `PadronA13`, registro COM. Tests
  offline con fakes + cassette de homologación (ver _Pruebas_). **Validado en
  vivo** contra homologación.
- **Liquidación de Caña de Azúcar** (`WSLCA`, módulo `wslca.py`, servicio WSAA
  `wslca`): verificado contra el WSDL vivo de homologación
  (`wslca/services/soap`, esquema `unqualified` como WSLSP → aplica el fix de
  marshalling del pysimplesoap vendoreado). Expone `Dummy`, los catálogos
  `Consultar*` (provincias, localidades, tipos de comprobante, tributos, puntos
  de venta, condiciones de venta, medios de pago, otros conceptos),
  `ConsultarUltimoComprobante`, `ConsultarLiquidacion` (por nro de comprobante)
  y el builder `CrearLiquidacion`/`AgregarDetalle`/`AgregarTributo`/
  `AgregarOtroConcepto`/`AutorizarLiquidacion` (`generarLiquidacion`, modelado
  fielmente contra el WSDL). Auth con `cuitRepresentada`. Errores tolerantes
  (`normalizar_lista_soap`). Alias `LiquidacionCanaAzucar`, registro COM, CLI.
  Tests offline (catálogos single/lista, errores uno/varios, consultas,
  builder) + cassette de catálogos de homologación (ver _Pruebas_). Los
  **catálogos quedaron validados en vivo**; la superficie de **generación**
  (`generarLiquidacion`) queda pendiente de validación en vivo.

## [1.2.0] - 2026-06-13

### Seguridad
- **Validación del certificado SSL del servidor activada por defecto.** Antes,
  el transporte vendoreado (`_vendor/pysimplesoap/transport.py`) usaba
  `disable_ssl_certificate_validation`/`CERT_NONE`: toda conexión a ARCA viajaba
  **sin validar** el certificado del servidor (expuesta a MITM). Ahora se valida
  por defecto (`check_hostname` + `CERT_REQUIRED`) usando el bundle de `certifi`
  o un CA propio (`cacert="<ruta>"`). El opt-out sigue disponible para
  depuración con `cacert=False`, pero **nunca es silencioso**: emite un
  `UserWarning`. Los endpoints de ARCA (homologación y producción) usan
  certificados públicos válidos, por lo que el nuevo default no debería romper
  integraciones existentes.

### Agregado
- **Padrón Alcance 10** (`WSSrPadronA10`, servicio WSAA `ws_sr_padron_a10`):
  consulta liviana para validación rápida de un CUIT vía `getPersona`. Puebla
  denominación, tipo/nro de documento, estado de la clave, domicilio(s) y
  actividad principal (`actividad_principal`). Verificado contra el WSDL vivo
  `personaServiceA10`. Flag de CLI `--a10`, alias `PadronA10`, registro COM.
  _(Irá en la próxima v1.2.0, a la espera de la validación del smoke de
  homologación.)_
- **Padrón Alcance 100** (`WSSrPadronA100`, servicio WSAA `ws_sr_padron_a100`):
  consulta de **tablas de parámetros** por nombre (`getParameterCollectionByName`).
  A diferencia del resto de la familia Padrón, vive bajo
  `sr-parametros/webservices/parameterServiceA100`. Expone `Dummy()`,
  `Consultar(collection_name)` → `self.parametros` (lista normalizada de
  `{id, descripcion, atributos}`) y `BuscarParametro(id)`. `parameterList` y
  `attributeList` (`maxOccurs="unbounded"`) se normalizan con `como_lista`. Flag
  de CLI `--a100`, alias `PadronA100`, registro COM. Especificado contra el
  manual oficial V2.1; smoke de homologación gateado (requiere autorizar
  `ws_sr_padron_a100` en WSASS).

### Corregido
- **`WSSrPadronA10.Dummy()`** — el servicio `personaServiceA10` entrega el
  estado de servidores en `<return>` (no en `<dummyReturn>` como A4/A5), así que
  el `Dummy()` heredado lanzaba `KeyError: 'dummyReturn'`. Detectado en el smoke
  de homologación; ahora el `Dummy()` de la familia Padrón tolera ambos
  envoltorios.
- **`Conectar` — sufijo `?WSDL` case-insensitive.** La comprobación del sufijo
  del WSDL era case-sensitive (`self.WSDL[-5:] == "?wsdl"`): una URL terminada
  en `?WSDL` (mayúsculas, usada por varios ejemplos/integraciones) no matcheaba
  y se le reincorporaba `?wsdl`, quedando `...?WSDL?wsdl` (URL inválida que el
  servidor respondía con una página de error, rompiendo el parseo del WSDL).
- **Parseo de WSDL — surgir el motivo real ante una respuesta inválida.** El
  parser (pysimplesoap vendoreado) asumía que la descarga del WSDL siempre era
  un `<definitions>`. Si el servidor devolvía un SOAP Fault o una página HTML de
  error, el parseo fallaba más adelante con un críptico `Tag not found: message
  (No elements found)`. Ahora se valida la raíz y se surge la causa accionable
  (el `faultstring` real del Fault, o la raíz inesperada + un fragmento).

### Pruebas
- **Primer lote de cassettes de homologación (replay offline).** Se grabaron
  contra homologación, con el certificado de autogestión WSASS, interacciones
  reales de `WSSrPadronA10.Consultar` (getPersona) y
  `WSSrConstanciaInscripcion.Consultar` (getPersona_v2) — WSDL vivo + respuesta —
  y se conectaron a tests de replay (`test_ws_sr_padron_a10_vcr.py`,
  `test_ws_sr_constancia_inscripcion_vcr.py`) que corren **sin red ni
  certificado** (`vcr` + `dontusefix`), validando el parseo contra el envelope
  real de ARCA. Cassettes **saneados**: token/sign del Ticket de Acceso
  reemplazados por placeholders y CUIT del titular por una sintética; la persona
  consultada es una entidad de homologación con datos de relleno (sin PII real).

### Deprecado
- **`WSCOC`** (Consulta de Operaciones Cambiarias): el régimen fue
  discontinuado por ARCA en 2015 y no tiene WS activo ni reemplazo. Instanciarlo
  emite `DeprecationWarning`; **remoción prevista para la 2.0**.
- **`WSCTG`** (Código de Trazabilidad de Granos): reemplazado por la Carta de
  Porte Electrónica (`WSCPE`, `wscpe.py`). Instanciarlo emite
  `DeprecationWarning`; **remoción prevista para la 2.0**.

## [1.1.1] - 2026-06-12

### Corregido
- **WSCDC / WSFEv1 — parseo tolerante de nodos repetibles.** El fix de `<Errors>`
  de la 1.1.0 no cubría `<Observaciones>`: una constatación WSCDC con
  `Resultado='R'` y una sola `<Obs>` (p. ej. Obs 100 "CAE inexistente" u Obs 110
  "importe no se corresponde") llegaba como dict (no lista) y lanzaba
  `TypeError: string indices must be integers`. Se normalizaron, con los helpers
  de `utils.py` (`normalizar_observaciones` / `normalizar_lista_soap`), todos los
  nodos `maxOccurs="unbounded"` que el código indexaba como lista: en WSCDC
  `ConstatarComprobante`, y en WSFEv1 las `Observaciones` de `CAESolicitar` /
  `CompConsultar` / `CAEARegInformativo` / `CAEASolicitar`, más `Iva`,
  `Tributos`, `CbtesAsoc`, `Opcionales`, `Compradores` y `Actividades` de
  `FECompConsultar`.

## [1.1.0] - 2026-06-11

### Agregado
- **Padrón Constancia de Inscripción** (`WSSrConstanciaInscripcion`, servicio
  WSAA `ws_sr_constancia_inscripcion`): reemplazo del deprecado
  `ws_sr_padron_a5`, usa la operación `getPersona_v2` sobre el mismo endpoint
  `personaServiceA5`. Expone `self.caracterizaciones` (lista de
  `{id, descripcion, periodo, fecha_solicitud}`) con el tag opcional
  `fechaSolicitud` (incorporado por ARCA el 11/02/2026), y el helper
  `TieneCaracterizacion(id)` para detectar caracterizaciones como la **639**
  (Ganancias Simplificada Ley 27.779).
- **Padrón Alcance 4**: parseo del bloque `<caracterizacion>`
  (`self.caracterizaciones`).

### Cambiado
- **`WSSrPadronA5` quedó deprecado**: instanciarlo emite `DeprecationWarning`;
  sigue funcionando para no romper compatibilidad.
- **WSLSP `ConsultarLiquidacion` (consulta emisor-céntrica)**: la solicitud
  lleva sólo `puntoVenta + tipoComprobante + nroComprobante` (se quitaron
  `cuitComprador` y `pdf`, que el servicio vivo rechaza). `cuit_comprador` se
  mantiene por compatibilidad pero se ignora con `UserWarning`. La rama por CAE
  falla con un error claro: `consultarLiquidacionPorCae` no existe ni en
  homologación ni en producción.

### Corregido
- **pysimplesoap vendoreado — `elementFormDefault="unqualified"`.** El
  marshalling calificaba con namespace los elementos hoja de schemas
  unqualified, generando un envelope que WSLSP rechazaba. Ahora respeta
  `elementFormDefault` y no afecta a los servicios `qualified` (WSFEv1, WSCDC).
- **WSCDC / WSFEv1 — `<Errors>` tolerante**: una sola `<Err>` llegaba como dict
  (no lista) y lanzaba `TypeError`; se normalizó con helpers en `utils.py`.

## [1.0.0] - 2026-06-04

Línea base del fork: modernización de pyafipws para Python 3 y rebranding a ARCA.

### Agregado
- **pysimplesoap vendoreado** como `pyarcaws._vendor.pysimplesoap` (cierra el
  gap del paquete de PyPI, abandonado/roto), portado a Python 3.11–3.13: caché
  de WSDL, comparación numérica de versiones de httplib2, reemplazo de
  `getargspec`.
- **CI con matriz Python 3.9 / 3.11 / 3.12 / 3.13.**

### Cambiado
- **Renombrado del paquete** `pyafipws` → `pyarcaws` en todo el proyecto;
  documentación y configuración actualizadas (AFIP → ARCA).
- **Versionado semántico** (semver `v1.0.0`) en reemplazo de las revisiones
  Mercurial heredadas.
- **Código Windows/COM desacoplado** a `windows/`.
- Encoding `latin1` unificado en todas las lecturas de configuración.

### Eliminado
- **Soporte de Python 2.7** y los imports de compatibilidad (`future`, `past`,
  `builtins`).
- Ejemplos legacy (VB, Delphi, C, Java, `.bat`) y tests/recursos COM sin uso.

### Corregido
- **Lógica de reintentos rota en Python 3**: el wrapper comparaba `e[0]` en vez
  de `e.errno`, por lo que no reintentaba ante cortes de conexión.
- Compatibilidad Python 3.11–3.13: `SafeConfigParser` → `ConfigParser`,
  `dict.has_key()` → operador `in`, `distutils` → `setuptools`, y varios
  arreglos reales de la suite de tests.

[Sin publicar]: https://github.com/aamalinux/pyarcaws/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/aamalinux/pyarcaws/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/aamalinux/pyarcaws/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/aamalinux/pyarcaws/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/aamalinux/pyarcaws/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/aamalinux/pyarcaws/releases/tag/v1.0.0
