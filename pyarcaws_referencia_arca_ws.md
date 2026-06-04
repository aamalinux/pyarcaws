# Referencia técnica — Web Services SOAP de ARCA (ex-AFIP)

Consolidado para el proyecto **pyarcaws**. Fuente: documentación oficial de ARCA
(`https://www.arca.gob.ar/ws/documentacion/`). Revisado: junio 2026.

> Los enlaces a PDFs/WSDL son oficiales y de descarga directa. El servidor de ARCA
> bloquea descargas automatizadas, por eso aquí va el resumen + los links para bajar
> manualmente lo que haga falta.

---

## 1. Arquitectura general

El intercambio entre ARCA y los entes externos (EE) se hace con **Web Services SOAP
sobre HTTPS**. Todos los WS de negocio (WSN) son accesibles directamente por Internet:
no hacen falta VPNs ni canales especiales.

El acceso a cualquier WSN está mediado por el **WSAA** (Web Service de Autenticación y
Autorización), que autentica a la app cliente y le otorga un **Ticket de Acceso (TA)**.

- Cada TA es válido para **un único WSN**.
- Vigencia del TA: **12 horas** (conviene cachearlo y reutilizarlo, no pedir uno por request).
- El WSN rechaza la solicitud si no se le presenta un TA válido.

### Flujo de autenticación (resumen del modelo de seguridad)

1. El EE obtiene un **certificado digital X.509** emitido por ARCA (actúa como Autoridad
   Certificante, sin cargo).
2. Se asocia ese certificado al WSN que se va a consumir (trámite de autorización).
3. El cliente arma un **TRA** (Ticket de Requerimiento de Acceso) y lo envuelve en una
   estructura **CMS / PKCS#7 (S/MIME)**: el TRA + su firma digital separada + el certificado X.509.
4. Envía ese CMS al WSAA (método `LoginCms`).
5. El WSAA verifica firma y autorización. Si todo está OK, devuelve el **TA**; si no, un
   mensaje de error.
6. El cliente extrae del TA dos componentes — **Token** y **Sign** — y los manda junto con
   los datos de negocio en **cada** request al WSN.

---

## 2. Endpoints WSAA

| Entorno    | URL                                                              |
| ---------- | ---------------------------------------------------------------- |
| Testing    | `https://wsaahomo.afip.gov.ar/ws/services/LoginCms`              |
| Producción | `https://wsaa.afip.gov.ar/ws/services/LoginCms`                  |

WSDL: agregar `?wsdl` a la URL del entorno correspondiente.

### Documentación WSAA (PDF)

- Especificación Técnica WSAA v1.2.2 — `https://www.arca.gob.ar/ws/WSAA/Especificacion_Tecnica_WSAA_1.2.2.pdf`
- Manual del Desarrollador WSAA — `https://www.arca.gob.ar/ws/WSAA/WSAAmanualDev.pdf`
- Obtener certificado (producción) — `https://www.arca.gob.ar/ws/WSAA/wsaa_obtener_certificado_produccion.pdf`
- Asociar certificado a un WSN (producción) — `https://www.arca.gob.ar/ws/WSAA/wsaa_asociar_certificado_a_wsn_produccion.pdf`

### Ejemplos de cliente WSAA

- Java — `https://www.arca.gob.ar/ws/WSAA/ejemplos/wsaa_client_java.tgz`
- PHP — `https://www.arca.gob.ar/ws/WSAA/ejemplos/wsaa-client-php.zip`
- C# (.NET) — `https://www.arca.gob.ar/ws/WSAA/ejemplos/dev-wsaa-cliente-dotnet-cs.zip`
- VB (.NET) — `https://www.arca.gob.ar/ws/WSAA/ejemplos/dev-wsaa-cliente-dotnet-vb.zip`
- PowerShell — `https://www.arca.gob.ar/ws/WSAA/ejemplos/dev-wsaa-cliente-powershell.zip`

---

## 3. Certificados digitales

### Testing / Homologación — vía **WSASS**

Aplicación web para gestionar certificados de testing. Se adhiere desde el
**Administrador de Relaciones de Clave Fiscal** (ingresar con clave fiscal de **persona
física**, no jurídica): `https://auth.afip.gov.ar/contribuyente_/login.xhtml?action=SYSTEM&system=adminrel`

- Cómo adherirse al WSASS — `https://www.arca.gob.ar/ws/WSASS/WSASS_como_adherirse.pdf`
- Manual WSASS (HTML) — `https://www.arca.gob.ar/ws/WSASS/html/index.html`
- Manual WSASS (PDF) — `https://www.arca.gob.ar/ws/WSASS/WSASS_manual.pdf`
- Cadena de certificación homologación 2014–2024 — `https://www.arca.gob.ar/ws/WSASS/Cadena_de_certificacion_homo_2014_2024.zip`
- Cadena de certificación homologación 2022–2034 — `https://www.arca.gob.ar/ws/WSASS/Cadena_de_certificacion_homo_2022_2034.zip`

### Producción

Se gestionan con "Administración de Certificados Digitales" + "Administrador de
Relaciones de Clave Fiscal" (login con clave fiscal: `https://auth.afip.gob.ar/contribuyente_/login.xhtml`).

- Cadena de certificación producción 2016–2024 — `https://www.arca.gob.ar/ws/documentacion/certificados/Cadena_de_certificacion_prod_2016_2024.zip`
- Cadena de certificación producción 2024–2035 — `https://www.arca.gob.ar/ws/documentacion/certificados/Cadena_de_certificacion_prod_2024_2035.zip`
- Generación de certificados para WS — `https://www.arca.gob.ar/ws/WSAA/WSAA.ObtenerCertificado.pdf`
- Delegación de WS (Admin. de Relaciones) — `https://www.arca.gob.ar/ws/WSAA/ADMINREL.DelegarWS.pdf`

---

## 4. Web Services de Factura Electrónica

> **Adecuación vigente:** RG N° 5.616/2024 (homologación externa). Manuales:
> `https://www.arca.gob.ar/ws/documentacion/homologacion-externa.asp`

| WS         | Uso                                                                 | RG          | Manual |
| ---------- | ------------------------------------------------------------------- | ----------- | ------ |
| **wsfev1** | Comprobantes A, B, C y M **sin** detalle de ítem; CAE y CAEA (A/B). Reemplaza al viejo `wsfe`. | 4.291 | [Manual v4.1](https://www.arca.gob.ar/ws/documentacion/manuales/manual-desarrollador-ARCA-COMPG-v4-1.pdf) |
| **wsmtxca**| Comprobantes A y B **con** detalle de ítems; CAE y CAEA.            | 2.904       | [Manual v0.25.4](https://www.arca.gob.ar/ws/documentacion/manuales/Web-Service-MTXCA-v25.pdf) |
| **wsfexv1**| Facturas de **exportación** (tipo E).                               | 2.758       | [Manual v3.1.1](https://www.arca.gob.ar/ws/documentacion/manuales/WSFEX-Manualparaeldesarrollador_V3.1.1_ARCA.pdf) |
| **wsbfev1**| Bonos Fiscales Electrónicos (bienes de capital).                    | 5427/2023; 2.861 | [Manual v3.0](https://www.arca.gob.ar/ws/documentacion/manuales/WSBFEV1-ManualParaElDesarrollador_ARCA_V3_0.pdf) |
| **wsct**   | Comprobantes T (alojamiento a turistas extranjeros).                | 3.971       | [Manual v1.6.4](https://www.arca.gob.ar/ws/documentacion/manuales/Manual_Desarrollador_WSCT_v1.6.4.pdf) |
| **wsseg**  | Seguros de Caución.                                                 | 2.668       | [Manual v0.9](https://www.arca.gob.ar/ws/documentacion/manuales/WSSEG-ManualParaElDesarrollador_ARCA.pdf) |

Endpoints de negocio (producción) más comunes:
- wsfev1: `https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL`
- wsfexv1: `https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL`
- wsmtxca: `https://serviciosjava.afip.gob.ar/wsmtxca/services/MTXCAService`

(En homologación, mismos paths con host `wswhomo`/`fwshomo` según el WS — ver cada manual.)

---

## 5. Otros WSN del catálogo (selección útil)

Catálogo completo: `https://www.arca.gob.ar/ws/documentacion/catalogo.asp`

**Padrón / consulta de contribuyentes**
- Constancia de Inscripción (`ws_sr_constancia_inscripcion`, reemplaza al A5) — v4.1 — `https://www.arca.gob.ar/ws/WSCI/manual_ws_sr_ws_constancia_inscripcion.pdf`
  - ⚠️ Desde **11/02/2026** `getPersona_v2` agrega tag opcional `fechaSolicitud` dentro de caracterización.
- Padrón Alcance 4 (situación tributaria) — v1.3 — `https://www.arca.gob.ar/ws/ws_sr_padron_a4/manual_ws_sr_padron_a4_v1.3.pdf`
- Padrón Alcance 10 (datos resumidos) — v1.2 — `https://www.arca.gob.ar/ws/ws_sr_padron_a10/manual_ws_sr_padron_a10_v1.2.pdf`
- Padrón Alcance 13 — v1.3 — `https://www.arca.gob.ar/ws/ws-padron-a13/manual-ws-sr-padron-a13-v1.3.pdf`
- Padrón Alcance 100 (tablas de parámetros) — v2.1 — `https://www.arca.gob.ar/ws/ws_sr_padron_a100/manual_ws_sr_padron_a100_v2.1.pdf`
- Padrón A5: **deprecado** (usar Constancia de Inscripción).

**Comprobantes**
- Constatación de Comprobantes (`wscdcv1`) — v0.4 — `https://www.arca.gob.ar/ws/WSCDCV1/WSCDC-manual-desarrollador-v4.pdf`

**Otros frecuentes**
- Carta de Porte Electrónica (`wscpe`) v2.2.0 — `https://www.arca.gob.ar/ws/documentos/manual-wscpe.pdf`
- Liquidación Primaria de Granos (`wslpg`) v1.24 — `https://www.arca.gob.ar/ws/WSLiquiGranos/manual_wslpg_1.24.pdf`
- Liquidación Sector Pecuario (`wslsp`) v2.0.4 — `https://www.arca.gob.ar/ws/WSLSP/manual-wslsp-2.0.4.pdf`
- Bonos Fiscales (`wsbfe`) — `https://www.arca.gob.ar/ws/WSBFE/WSBFE - Manual para el desarrollador_V1_1.pdf`

---

## 6. Requisito de seguridad TLS

ARCA está discontinuando **TLS 1.0 y 1.1**. Hay que usar **TLS v1.2** en todos los
sitios (`auth.afip.gob.ar`, `servicios1.afip.gob.ar`, `serviciosjava.afip.gob.ar`, etc.).
Fechas de corte: "próximamente" (sin fecha firme al momento de esta revisión).
Detalle: `https://www.arca.gob.ar/ws/documentacion/cronograma-TLS.asp`

➡️ Asegurar que el stack HTTP/SOAP de pyarcaws negocie TLS 1.2 como mínimo.

---

## 7. Notas de implementación para pyarcaws

- **Cachear el TA** por WSN durante sus 12h en vez de re-autenticar en cada llamada.
- El TRA lleva `uniqueId`, `generationTime` y `expirationTime`; el `service` debe coincidir
  con el WSN destino (ej. `wsfe`, `ws_sr_padron_a4`).
- Firma CMS: en Python suele resolverse con `cryptography` (PKCS#7) u OpenSSL como
  fallback (mismo patrón que usa `pyafipws`).
- Mantener dos juegos de config endpoint/cert: **homologación** vs **producción**.
- El proyecto de referencia `pyafipws` (en el conocimiento del proyecto) ya implementa
  WSAA + la mayoría de estos WSN; sirve como guía de los nombres de servicio y estructuras.

---

## 8. Páginas índice oficiales

- Arquitectura — `https://www.arca.gob.ar/ws/documentacion/arquitectura-general.asp`
- Certificados — `https://www.arca.gob.ar/ws/documentacion/certificados.asp`
- WSAA — `https://www.arca.gob.ar/ws/documentacion/wsaa.asp`
- Autoridades certificantes — `https://www.arca.gob.ar/ws/documentacion/autoridades-certificantes.asp`
- WS Factura Electrónica — `https://www.arca.gob.ar/ws/documentacion/ws-factura-electronica.asp`
- Catálogo de WSN — `https://www.arca.gob.ar/ws/documentacion/catalogo.asp`
- Cronograma TLS — `https://www.arca.gob.ar/ws/documentacion/cronograma-TLS.asp`
- Servicios migrados — `https://www.arca.gob.ar/ws/documentacion/servicios-migrados.asp`
