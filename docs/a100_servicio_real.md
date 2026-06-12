# A100 (`ws_sr_padron_a100`) — servicio real encontrado

> Estado: **informe** (no implementado todavía). Fecha: 2026-06-12.

## Resumen

El WSDL de A100 **sí existe y responde**. El motivo por el que antes daba
"Servicio inexistente" es que se buscaba bajo `sr-padron/webservices/`, pero el
servicio vive bajo **`sr-parametros/webservices/`**. Confirmado contra el manual
oficial **V2.1 (20/12/2023)** y por descarga pública del WSDL (HTTP 200 en homo
y producción).

- Manual: `https://www.afip.gob.ar/ws/ws_sr_padron_a100/manual_ws_sr_padron_a100_v2.1.pdf`
- **ID de servicio WSAA**: `ws_sr_padron_a100`

## URLs reales (verificadas, HTTP 200)

| Ambiente | WSDL |
|----------|------|
| Homologación | `https://awshomo.afip.gov.ar/sr-parametros/webservices/parameterServiceA100?wsdl` |
| Producción | `https://aws.afip.gov.ar/sr-parametros/webservices/parameterServiceA100?wsdl` |

(El endpoint SOAP es la misma URL sin `?wsdl`.) `targetNamespace` =
`http://a100.soap.ws.server.pucParam.sr/`, `elementFormDefault="unqualified"`.

## Operaciones

- **`dummy`** — verificación del servicio, sin auth.
- **`getParameterCollectionByName`** — la consulta principal.

### Esquema de `getParameterCollectionByName`

**Solicitud** (misma terna de auth que A4/A5/A10 + el nombre de la tabla):

```
token : string
sign : string
cuitRepresentada : long
collectionName : string      # nombre de la tabla (columna "CollectionName" del manual)
```

**Respuesta**: `parameterCollectionReturn` → `parameterCollection`:

```
name : string
parameterList : parameter[]        # maxOccurs unbounded
    parameter:
        id : string                # identifica el elemento dentro de la colección
        description : string
        attributeList : parameterAttribute[]   # maxOccurs unbounded
```

## Estimación de esfuerzo: **baja (≈ A10)**

Es el mismo patrón que el resto de la familia Padrón. Plan:

1. `WSSrPadronA100(BaseWS)` en `ws_sr_padron.py`:
   - WSDL homo `parameterServiceA100` (comentario con prod), service WSAA
     `ws_sr_padron_a100`, progid/clsid nuevos, alias `PadronA100`, flag
     `main() --a100`.
   - `Dummy()` (sin auth).
   - `ConsultarParametros(collection_name)` → `getParameterCollectionByName`
     con `{token, sign, cuitRepresentada, collectionName}`; poblar
     `self.parametros` como lista de dicts normalizada:
     `{"id", "descripcion", "atributos": [...]}`.
   - **Normalización obligatoria** de `parameterList` y `attributeList` con
     `como_lista` / `normalizar_lista_soap` (son `maxOccurs="unbounded"`: con un
     solo elemento llegan como dict, no como lista — mismo patrón ya corregido
     en el resto del fork).
2. La solicitud es **plana** (token/sign/cuit/collectionName como parámetros
   directos de la operación, como el `getPersona` de A10), así que **no** sufre
   el bug de namespaces de schemas anidados; el fix de `elementFormDefault` ya
   en main cubre cualquier caso.
3. Tests offline con cliente falso (colección con varios elementos / con uno
   solo como dict / vacía; verificar que la auth llega).
4. Smoke gateado contra homologación (requiere autorizar `ws_sr_padron_a100` en
   WSASS).

## Conclusión

A100 pasa de "no disponible públicamente" a **disponible y especificado**; queda
listo para implementarse como un servicio más de la familia Padrón cuando se
priorice (sugerido: junto con la futura v1.2.0 o en una v1.3.0).
