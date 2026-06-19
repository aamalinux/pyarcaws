# Relevamiento de servicios — pyarcaws

> Fecha: 2026-06-14 · Branch base: `main` (v1.2.0) · Método: **medido, no asumido**.
>
> - **Import**: `python -c "import pyarcaws.<mod>"` en venv con `pip install -e .` (Python 3).
> - **WSDL vivo**: descarga pública del WSDL de **homologación** (sin autenticar);
>   se reporta el código HTTP real. Sin llamadas autenticadas a ARCA en esta tanda.
> - **Tests/cassettes**: presencia de `tests/test_<mod>.py` y de cassettes VCR
>   (replay **offline**) o marca `online` (requiere cert/red).
>
> Convención de estado:
> - **ACTIVO (live)** — anda y fue validado en vivo contra homologación en el fork.
> - **ACTIVO (cassette)** — importa + WSDL vivo + tiene cassette offline que pasa,
>   pero sin validación en vivo en el fork (forma de request/response probada).
> - **IMPORTA-SIN-PROBAR** — importa limpio y (si aplica) el WSDL responde, pero
>   **no hay test ni evidencia de uso en Py3** en el fork. Heredado de pyafipws.
> - **DEPRECADO** — marcado con `DeprecationWarning` en código y WSDL caído.

---

## Tarea 1 — Auditoría de módulos presentes

Resultado global: **los 31 módulos de servicio importan limpio en Python 3** (0 errores
de import). La diferencia de madurez está en *tests* y *validación en vivo*, no en el import.

### ARCA — fiscal / factura electrónica

| Módulo | Dominio | Import Py3 | Tests / cassettes | WSDL homo | Estado | Nota |
|--------|---------|:---:|---|:---:|---|---|
| `wsaa` | Autenticación (base) | OK | sí · cassette + `online` | 200 | **ACTIVO (live)** | Lo usa todo el resto |
| `wsfev1` | Factura mercado interno | OK | sí · cassette offline (dummy/obs/errores) + `online` | 200 | **ACTIVO (live)** | Validado en vivo; fixes `<Errors>`/`<Obs>` |
| `wsmtx` (MTXCA) | Factura con ítems/código de barras | OK | sí · cassette + `online` | 200 | **ACTIVO (cassette)** | |
| `wsct` | Factura turismo (IVA tax-free) | OK | sí · cassette | 200 | **ACTIVO (cassette)** | |
| `wsbfev1` | Bonos fiscales | OK | sí · cassette + `online` | 200 | **ACTIVO (cassette)** | |
| `wsfexv1` | Factura exportación | OK | sí · cassette + `online` | 200 | **ACTIVO (cassette)** | |
| `wscdc` | Constatación de comprobantes | OK | sí · cassette offline (errores/obs) | 200 | **ACTIVO (live)** | Validado; parseo tolerante |
| `ws_sr_padron` | Padrón A4 / Constancia (ex A5) / A10 / A100 | OK | sí · cassettes offline (a10_vcr, constancia_vcr) + tests | 200 (A4/A5/A10/A100) | **ACTIVO (live)** | A10 y constancia validados en vivo |
| `wsfecred` | Facturas de Crédito Electrónicas MiPyME | OK | **no** | 200 | **IMPORTA-SIN-PROBAR** | Candidato a cassette |
| `ws_sire` | SIRE — certificado retención C2005 (IVA) | OK | sí · tests offline (fakes) | 200 (reca.homo) | **PROBADO OFFLINE** | Dominio RECA, `soap_server="oracle"`. `Emitir`/`anular` **gateados por WSASS** (`coe.notAuthorized`) + agente de retención IVA. `Dummy` (sin auth): endpoint responde SOAP a curl, pero httplib2 recibe HTML de sondeo del WAF → sin cassette (ver hallazgo) |
| `wscoc` | Operaciones cambiarias (RG 3210) | OK | no | **404** | **DEPRECADO** | `DeprecationWarning`; régimen discontinuado 2015, sin reemplazo |

### ARCA — agro / liquidaciones / remitos

| Módulo | Dominio | Import Py3 | Tests / cassettes | WSDL homo | Estado | Nota |
|--------|---------|:---:|---|:---:|---|---|
| `wslsp` | Liquidación sector pecuario | OK | sí · cassette offline (marshalling/receptor) | 200 | **ACTIVO (live)** | Validado; fix `elementFormDefault` |
| `wsltv` | Liquidación tabaco verde | OK | sí · cassette | 200 | **ACTIVO (cassette)** | |
| `wslum` | Liquidación lechería | OK | sí · cassette | 200 | **ACTIVO (cassette)** | |
| `wslpg` | Liquidación primaria de granos | OK | sí · tests offline (marshalling/catálogos/tolerancia) | 200 | **PROBADO OFFLINE** | Builder + auth + parseo tolerante single-vs-list. Smoke en vivo **bloqueado por WSASS** (cert no autorizado para `wslpg`); **sin validar en vivo** |
| `wscpe` | Carta de Porte Electrónica | OK | sí · offline (fakes) + cassettes homo nuevos (Dummy + catálogos); 33 heredados (host viejo) | 200 (`cpea-ws-qaext`) | **ACTIVO (live)** | Endpoint **migrado** a `cpea-ws-qaext` (homo) / `cpea-ws` (prod); `fwshomo`/`serviciosjava` dan 404. `Dummy` + catálogos `Consultar*` **validados en vivo** (fix `__analizar_errores` con `<errores>` vacío); escrituras modeladas offline. Mismo namespace/ops que el módulo (salvo 2 ops `editarCPEConfirmada*Dg`) |
| `wsctg` | Trazabilidad de granos | OK | no | **404** | **DEPRECADO** | `DeprecationWarning` → usar **WSCPE** |
| `wsremcarne` | Remito electrónico cárnico | OK | sí · cassette | 200 | **ACTIVO (cassette)** | |
| `wsremazucar` | Remito azúcar/alcohol | OK | **no** | 200 | **IMPORTA-SIN-PROBAR** | |
| `wsremharina` | Remito harina de trigo | OK | **no** | 200 | **IMPORTA-SIN-PROBAR** | |

### Provincial / otros organismos

| Módulo | Organismo | Import Py3 | Tests | Endpoint | Estado | Nota |
|--------|-----------|:---:|:---:|:---:|---|---|
| `cot` | ARBA (Bs. As.) | OK | no | 200 (test) | **IMPORTA-SIN-PROBAR** | Remito electrónico; **REST/POST, no SOAP** |
| `iibb` | ARBA (Bs. As.) | OK | no | timeout | **IMPORTA-SIN-PROBAR** | Percepciones/retenciones IIBB (WS DFE, online); el endpoint `dfe.test.arba.gov.ar` no respondió (timeout) |
| `padron_iibb` | ARBA + AGIP (Bs.As./CABA) | OK | sí · tests offline (fixtures) | n/a (offline) | **PROBADO OFFLINE** | **Parser de archivos**, no WS: lee padrones de alícuotas IIBB (ZIP/TXT latin-1). Layout ARBA+AGIP confirmado contra los PDF oficiales. Sin red ni credenciales. Distinto de `iibb.py` (WS DFE) y `padron.py` (ARCA) |
| `padron` | ARCA (padrón bulk) | OK | no | ⚠️ SOA `v2/persona` **404** | **IMPORTA-SIN-PROBAR** | Descarga el ZIP de padrón + API SOA REST; el endpoint público `soa.afip.gob.ar/sr-padron/v2/persona` da **404** (movido/discontinuado) → usar la familia autenticada A4/A10/A13/constancia. `Consultar` ahora surge el motivo claro (no `JSONDecodeError`) |
| `trazamed` | ANMAT/PAMI (SNT) | OK | no | 200 | **IMPORTA-SIN-PROBAR** | Trazabilidad medicamentos |
| `trazarenpre` | RENPRE/SEDRONAR (SNT) | OK | no | 200 | **IMPORTA-SIN-PROBAR** | Precursores químicos |
| `trazafito` | SENASA (SNT) | OK | no | 200 | **IMPORTA-SIN-PROBAR** | Fitosanitarios |
| `trazaprodmed` | ANMAT (SNT) | OK | no | 200 | **IMPORTA-SIN-PROBAR** | Productos médicos |
| `trazavet` | SENASA (SNT) | OK | no | 200 | **IMPORTA-SIN-PROBAR** | Productos veterinarios |

**Hallazgos de la auditoría**

- **Ningún módulo roto por import.** La deuda real es de *cobertura de tests*: 15 de 31
  módulos no tienen ni un test (todos los `traza*`, `wslpg`, `wsfecred`, `ws_sire`,
  `wsremazucar`, `wsremharina`, `cot`, `iibb`, `padron`).
- **`wscpe` (Carta de Porte): endpoint MIGRADO (resuelto).** Las URLs viejas
  (`fwshomo.afip.gov.ar` homo, `serviciosjava.afip.gob.ar` prod) dan **404**: ARCA movió
  el servicio a los hosts `cpea-ws*` (`cpea-ws-qaext.afip.gob.ar` homo,
  `cpea-ws.afip.gob.ar` prod; WSDL 200, mismo `targetNamespace` y operaciones). Módulo
  actualizado; `Conectar`+`Dummy` validados en vivo en homo. Catálogos/escrituras
  **gateados por WSASS** (cert no autorizado para `wscpe`). Hallazgo: 2 ops del módulo
  (`editarCPEConfirmadaAutomotorDg`/`...FerroviariaDg`) no figuran con ese nombre en el
  WSDL vivo (el WSDL usa `editarCPEDGConfirmada*` / `editarCPEConfirmada*`) — divergencia
  de naming preexistente, a decidir.
- **`wsctg` y `wscoc`**: confirmados **DEPRECADOS** — `DeprecationWarning` en código y
  WSDL **404**. WSCTG se reemplaza por **WSCPE**; WSCOC no tiene reemplazo.
- **`wslpg`** (liquidación primaria de granos): servicio mayor, WSDL vivo, pero **sin un
  solo test** → prioridad alta para cassettes si hay caso de uso de granos.
- **`ws_sire`** (SIRE C2005): dominio RECA `ws-aplicativos-reca.homo.afip.gob.ar`
  (no `fwshomo`), `soap_server="oracle"`, WSDL+XSD vivos (200). Tests offline
  agregados (marshalling de `Emitir` con `cuitAgente`). **Gates**: (1) `sire-ws` no
  autorizado en WSASS (`coe.notAuthorized`) y `Emitir` exige agente de retención IVA
  designado → escritura sin validar en vivo; (2) **hallazgo de transporte**: el
  `Dummy` no requiere auth y el endpoint RECA devuelve un `dummyResponse` válido a un
  POST crudo de `curl` (mismos headers/body), pero el httplib2 vendoreado recibe una
  página **HTML de sondeo** del Oracle/WAF (request-id cambiante) → `ExpatError`; el
  GET del WSDL sí funciona. Causa no fijada (curl HTTP/1.1 anda; probable
  fingerprint TLS/WAF), no es bug del módulo — bloquea grabar cassette de Dummy.
  Inconsistencia menor: `HOMO=False` pese a que el módulo sólo trae el WSDL de homo.

---

## Tarea 2 — Catálogo de lo NO implementado

Base: [catálogo oficial de WSN de ARCA](https://www.afip.gob.ar/ws/documentacion/catalogo.asp),
contrastado contra el árbol del repo. Esfuerzo estimado **relativo al patrón A10/A100**
ya conocido (BAJO = misma forma; MEDIO = nuevo schema con varias operaciones; ALTO =
familia/dominio nuevo o muy fragmentado).

### ARCA — servicios faltantes

| Candidato | Qué resuelve | WSDL/API pública | Esfuerzo | Acuerdo especial |
|-----------|--------------|:---:|:---:|---|
| ~~**ws_sr_padron_a13**~~ | Padrón Alcance 13 (búsqueda inversa documento→CUIT) | Sí | **BAJO** | ✅ **IMPLEMENTADO** (v1.3.0, pendiente validación en vivo) |
| ~~**WSLCA**~~ | Liquidación de **caña de azúcar** | Sí | **BAJO** | ✅ **IMPLEMENTADO** (v1.3.0, pendiente validación en vivo) |
| ~~**WSAPOC**~~ | Consulta de **apócrifos** (base APOC, validar proveedores) | Sí (`eapoc-ws-qaext`) | **BAJO** | ✅ **IMPLEMENTADO** (v1.3.0, pendiente validación en vivo) |
| **TRABAJO_F931** | Consulta de DDJJ F931 de Seguridad Social (SICOSS) | Sí (catálogo) | MEDIO | No aparente |
| **SETIWS / VEP** (`SETIWS-PAGO-API`) | Crear y gestionar VEP (volantes electrónicos de pago) | Sí (catálogo) | MEDIO | No aparente |
| **WSCTA** | Certificados DNRPA / CETA (transferencias automotores) | ⛔ **404** homo (`fwshomo/wscta`) | — | ⛔ **DIFERIDO**: WSDL homo caído + acceso de rol DNRPA/registro (`aprobarCertificado`), no general |
| **wscec** | Consultas Ley Economía del Conocimiento | ⛔ no hallado (sin README ni WSDL en patrones) | — | ⛔ **DIFERIDO**: falta confirmar endpoint/manual |
| **WSSEG** | Operaciones de seguros de caución | Sí | MEDIO | No aparente |
| **WSTABACO** | Régimen tabacalero | Sí | MEDIO | No aparente |
| **wscec** | Consultas Ley Economía del Conocimiento | Sí | BAJO-MEDIO | No aparente |
| **Plataformas digitales** (RG 5319) | Percepción IVA plataformas / situación fiscal | Restringida | MEDIO | **Sí (RG 5319/2023)** |
| **sud_restricciones / sud_contrataciones** | Consulta de deuda por CUIT | Restringida | MEDIO | **Sí** (bancos / proveedores del Estado) |
| **WSCCOMU** (Ventanilla Electrónica) | Consumo de comunicaciones de Ventanilla | Sí | MEDIO | No aparente |
| **Aduana** (WGESINV, wConsDepFiel, WSSV, wGesTabRef, etc.) | Operatoria aduanera por rol de agente | Restringida | ALTO | **Sí** (rol OTEN/PSAD/DESP/etc.) |

> Nota: `WSFEcred`, `WSCPE`, `WSCDCV1`, `ws_sr_padron_a4/a10/a100`,
> `ws_sr_constancia_inscripcion`, `WSLPG/LSP/LTV/LUM`, `WSREMCARNE/AZUCAR/HARINA`,
> `WSBFE`, `WSSEG`(no), `SIRE` **ya están en el repo** (algunos como IMPORTA-SIN-PROBAR).
> `ws_sr_padron_a5` figura **deprecado** también en el catálogo oficial (coincide con el
> fork: A5 → Constancia de Inscripción).

### Ingresos Brutos provinciales — **FRENTE, no un servicio**

Es un esfuerzo **grande y fragmentado**: cada jurisdicción tiene su propia agencia, su
propio WS/API (muchos REST, no SOAP), su propia autenticación y su propio padrón de
alícuotas. Panorama de cobertura:

| Jurisdicción | Agencia | WS/API | En repo | Nota |
|--------------|---------|:---:|:---:|---|
| Buenos Aires (pcia.) | **ARBA** | COT + DFE (alícuotas/deuda IIBB) | **Parcial** (`cot`, `iibb`) | REST/POST; `iibb` sin probar |
| CABA | **AGIP** | `ISIBWS` (datos ISIB) + Consulta Deuda ISIB | No | WS documentado; candidato más claro tras ARBA |
| Santa Fe | **API** | API/WS propio | No | Documentación dispersa |
| Córdoba | **DGR / Rentas** | API propio | No | Fragmentado |
| Mendoza / otras (ATM, etc.) | varias | heterogéneo | No | Caso por caso |
| **Multilateral** | **SIRCREB / Convenio Multilateral** | padrón de regímenes de recaudación | No | Transversal; alto valor pero complejo |

**Recomendación del frente IIBB**: no encararlo "en bloque". Tratar cada jurisdicción
como mini-proyecto **disparado por demanda concreta** de un usuario. El próximo paso
natural y de mayor cobertura tras ARBA es **AGIP (CABA)** por tener WS documentado.

### Otros organismos (SNT — trazabilidad)

Los 5 módulos `traza*` ya presentes cubren ANMAT (medicamentos/productos médicos),
SENASA (fito/veterinaria) y RENPRE (precursores). Todos con **WSDL vivo (200)** pero
**sin tests**. No se detectaron servicios nuevos de esos organismos con caso de uso
general que falten; la prioridad acá es **validar** lo que ya hay (cassettes), no sumar.

---

## Tarea 3 — Matriz de priorización

### Implementados hacia v1.3.0

- ✅ **ws_sr_padron_a13** (`WSSrPadronA13`) — **VALIDADO EN VIVO** (homologación) +
  cassette offline (`test_ws_sr_padron_a13_vcr.py`): `getPersona` (persona activa) y
  `getIdPersonaListByDocumento` (lista real de varios idPersona).
- ✅ **WSLCA** (`wslca.py`) — **VALIDADO EN VIVO** + cassette offline
  (`test_wslca_vcr.py`): catálogos reales (provincias, tributos, tipos de comprobante
  = "Liquidación de Compra de Caña de Azúcar Clase A/B"). Generación modelada del WSDL
  (no ejercitada en vivo).
- ✅ **WSAPOC** (`wsapoc.py`) — **VALIDADO EN VIVO** + cassette offline
  (`test_wsapoc_vcr.py`): `Consultar` de un CUIT no apócrifo (respuesta limpia
  `codigo 0`, `EsApocrifo=False`). Auth `Credencial{Token, Sign, CUITDelegado}`.
- ⚠️ **ws_sr_padron_a100** (`WSSrPadronA100`) — **integración validada, sin positivo en
  homologación**. El WSDL vivo solo expone `dummy` y `getParameterCollectionByName`:
  **no hay operación que liste las colecciones disponibles** sin pasar `collectionName`.
  ~14 nombres probados (`Provincias`, `Actividades`, `Impuestos`, …) devuelven
  `ParameterDefinition no encontrada en PUC_PARAM.DICCIONARIO_PARAMETROS`. Dos hipótesis,
  ambas posibles: **(a)** los `collectionName` válidos son nombres específicos del manual
  V2.1 (PDF imagen, no extraíble) que no probamos; **(b)** el diccionario de parámetros de
  **homologación está vacío** (común en homo), con lo que ningún nombre daría positivo
  hasta producción. Auth/Dummy/parseo del fault confirmados OK. Sin cassette por ahora.

### Top candidatos por valor/esfuerzo (próximos a sumar)

1. **TRABAJO_F931 (Seguridad Social)** — esfuerzo **MEDIO**, **valor general alto**
   (uso contable/liquidación de sueldos transversal). Mejor relación valor/esfuerzo de
   los "grandes".
2. **SETIWS / VEP (volantes de pago)** — esfuerzo **MEDIO**, valor general alto
   (generar VEP es una necesidad muy común). Buen candidato si se quiere ampliar más
   allá de facturación.

**Solo si aparece caso de uso concreto**: WSCTA (automotores), WSSEG (caución),
WSTABACO, wscec, WSCCOMU (Ventanilla), y todo **Aduana** (requiere rol de agente →
acceso restringido, esfuerzo ALTO). **Plataformas digitales RG 5319** y
`sud_*` requieren **acuerdo/autorización especial** con ARCA → no encarar sin ese
acceso.

**Frente IIBB provincial**: encarar **AGIP (CABA)** como siguiente jurisdicción solo
ante demanda; el resto, caso por caso. No es un "servicio" sino un programa.

### Estado del inventario existente (acciones sugeridas)

- **IMPORTA-SIN-PROBAR → validar con cassettes** (futura tanda con certificado, por
  orden de valor): **`wslpg`** (el más importante sin test), `wsfecred`, `ws_sire`,
  `wsremazucar`, `wsremharina`, y los `traza*`. `cot`/`iibb`/`padron` validan contra
  endpoints provinciales/bulk (no requieren cert ARCA pero sí datos de prueba).
- **`wscpe`** — RESUELTO: el endpoint se movió a `cpea-ws*` (ver hallazgos); módulo
  actualizado y `Dummy` validado en vivo.
- **DEPRECADOS** (ya señalizados, remoción prevista 2.0): **`wscoc`**, **`wsctg`**.
  No invertir; mantener el `DeprecationWarning`.

---

## Metodología y reproducibilidad

```bash
python3 -m venv /tmp/audit_venv
/tmp/audit_venv/bin/pip install -e .
# import de cada módulo:
/tmp/audit_venv/bin/python -c "import pyarcaws.<mod>"
# liveness WSDL (GET público, sin autenticar) → código HTTP real
```

Sin llamadas autenticadas a ARCA. Las descargas de WSDL son públicas. Los endpoints que
no respondieron (`iibb` ARBA timeout, `wscpe`/`wsctg`/`wscoc` 404) se reportan tal cual,
sin reintentos insistentes.
