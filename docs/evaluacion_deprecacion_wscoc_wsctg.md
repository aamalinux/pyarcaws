# Evaluación de deprecación: `wscoc` y `wsctg`

> Estado: **informe para decisión** (no se implementó ninguna deprecación).
> Fecha: 2026-06-12. Rama base: main post-v1.1.1.

Dos módulos heredados del upstream estaban flaggeados como candidatos a
deprecación. Este informe reúne la evidencia y una recomendación por servicio.
La decisión final la toma el usuario.

## Metodología

- **Código**: existencia, import en Python 3, tests/cassettes en el repo.
- **WSDL vivo**: descarga pública (sin auth) de las URLs que usa el módulo, en
  homologación y producción.
- **Normativa**: estado del régimen que le da sentido al servicio (búsqueda en
  documentación oficial de ARCA/AFIP y fuentes de referencia).

> ⚠️ Aclaración honesta: un `404` en la URL del WSDL **no prueba** por sí solo
> que el servicio esté muerto (la URL del código puede haber quedado vieja; la
> puerta 404 de AFIP es genérica). Por eso el peso de la recomendación recae en
> el **estado del régimen normativo**, no sólo en el HTTP.

---

## `wscoc` — Consulta de Operaciones Cambiarias

| Ítem | Resultado |
|------|-----------|
| Archivo | `wscoc.py` (~45 KB), importa OK en Python 3 |
| WSDL en código (homo) | `https://fwshomo.afip.gov.ar/wscoc/COCService` → **HTTP 404** |
| WSDL en código (prod) | `https://serviciosjava.afip.gob.ar/wscoc2/COCService` → **HTTP 404** |
| Tests / cassettes | **Ninguno** |
| Régimen | **Programa de Consulta de Operaciones Cambiarias** (RG 3210/2011 — el "cepo cambiario"): controlaba en tiempo real la compra de divisas. |
| Estado del régimen | **Discontinuado** (la consulta previa a la compra de divisas se eliminó en diciembre de 2015). El servicio ya no tiene contraparte funcional vigente. |

**Recomendación: DEPRECAR con `DeprecationWarning` ahora y REMOVER en la 2.0.**
El régimen que le daba sentido no existe; el servicio no tiene utilidad actual y
su WSDL no responde. Riesgo de romper consumidores: muy bajo (no hay tests ni,
verosímilmente, usuarios activos).

## `wsctg` — Código de Trazabilidad de Granos

| Ítem | Resultado |
|------|-----------|
| Archivo | `wsctg.py` (~54 KB), importa OK en Python 3 |
| WSDL en código (homo) | `https://fwshomo.afip.gov.ar/wsctg/services/CTGService_v4.0?wsdl` → **HTTP 404** |
| WSDL en código (prod) | idem en `serviciosjava.afip.gob.ar` → **HTTP 404** |
| Tests / cassettes | **Ninguno** |
| Régimen | Código de Trazabilidad de Granos (CTG), RG 2806/2010 (WSCTGv2/v4). |
| Estado del régimen | **Superado por la Carta de Porte Electrónica (CPE)**: el CTG (12 dígitos) hoy se **genera automáticamente** al emitir una CPE. El fork ya implementa la CPE en `wscpe.py` (con cassettes activos en `tests/cassettes/test_wscpe`). |

**Recomendación: DEPRECAR con `DeprecationWarning` apuntando a `wscpe`** (Carta
de Porte Electrónica) como reemplazo. **Antes de remover** conviene una
verificación extra: el CTG sigue existiendo como concepto dentro de la CPE y no
se descarta que haya un endpoint WSCTG vigente bajo otra URL; el `404` actual es
sobre la URL del código, posiblemente desactualizada. Es decir: deprecar ahora,
remover en 2.0 sólo tras confirmar que no queda consumo legítimo.

---

## Plan de implementación (si se aprueba)

Mismo patrón ya usado para `WSSrPadronA5` (no rompe compatibilidad):

```python
import warnings

class WSCOC(BaseWS):
    def __init__(self, *args, **kwargs):
        if type(self) is WSCOC:
            warnings.warn(
                "wscoc (Consulta de Operaciones Cambiarias, RG 3210) está "
                "deprecado: el régimen fue discontinuado (dic-2015). Se removerá "
                "en pyarcaws 2.0.",
                DeprecationWarning, stacklevel=2,
            )
        super().__init__(*args, **kwargs)
```

Para `wsctg`, el mensaje debe orientar a `wscpe` (Carta de Porte Electrónica).

- Entrada de CHANGELOG bajo `### Obsoleto` (Deprecated) en `[Sin publicar]`.
- Nota en README de que ambos quedan deprecados y por qué.
- Remoción efectiva: recién en la 2.0, con su propia entrada `### Eliminado`.

## Resumen ejecutivo

| Servicio | WSDL responde | Régimen vigente | Recomendación |
|----------|---------------|-----------------|----------------|
| `wscoc`  | No (404)      | **No** (eliminado 2015) | Deprecar ya → remover en 2.0 |
| `wsctg`  | No (404)      | Superado por CPE (`wscpe`) | Deprecar ya (apuntar a `wscpe`) → remover en 2.0 tras confirmar |
