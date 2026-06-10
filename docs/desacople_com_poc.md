# PoC: desacople de COM en tres capas (módulos `pyqr` y `pyi25`)

## Resumen del patrón

Los módulos históricos de pyafipws/pyarcaws mezclan tres responsabilidades en
una sola clase: la lógica de negocio, la interfaz COM de Windows (atributos
`_public_methods_`, `_reg_clsid_`, etc.) y la línea de comandos. Eso obliga a
cargar (o al menos convivir con) infraestructura de `pywin32` aunque uno solo
quiera usar el módulo como librería en Linux.

El patrón aplicado separa eso en tres capas:

1. **Núcleo puro** (`core/qr.py`): la lógica de negocio en Python normal.
   Sin COM, sin estado global, con type hints y excepciones comunes.
   Importable desde cualquier proyecto con `pip install` y nada más.
2. **Wrapper COM** (`pyqr.py`, clase `PyQR`): una clase fina que conserva
   la interfaz histórica que esperan Windows/COM y el código existente
   (métodos CamelCase, errores volcados en atributos `Excepcion`/`Traceback`,
   GUIDs de registro intactos) y delega todo el trabajo en el núcleo.
3. **CLI / empaquetado** (`main()` en `pyqr.py`): la línea de comandos usa el
   wrapper; el registro COM (`--register`, `--unregister`, `/Automate`) quedó
   en funciones separadas (`registrar_com()`, `servir_automate()`) que hacen
   import diferido de `pythoncom`/`win32com`, así nunca se cargan en
   Linux/macOS. El empaquetado py2exe (`windows/setup_win.py`) sigue
   apuntando a `pyqr.py` sin cambios.

## Mapa de capas (qué quedó dónde)

| Capa | Archivo | Contenido |
|------|---------|-----------|
| 1. Núcleo | `core/qr.py` | `QRGenerator` (`armar_datos`, `generar_url`, `generar_imagen`, `generar_qr`), `crear_archivo_temporal()`, constantes `URL_TEMPLATE` y `DEFAULT_*` |
| 1. Núcleo | `core/__init__.py` | docstring del subpaquete `pyarcaws.core` |
| 2. Wrapper | `pyqr.py` → `PyQR` | `_public_methods_`, `_public_attrs_`, `_reg_progid_`, `_reg_clsid_`, `TYPELIB`/`_typelib_*` (GUIDs sin tocar), `CrearArchivo`/`GenerarImagen` que delegan en el núcleo, captura de excepciones en `Excepcion`/`Traceback` (y re-lanzado), `InstallDir`/`INSTALL_DIR` vía `get_install_dir()` |
| 3. CLI | `pyqr.py` → `main()` | flags `--datos`, `--archivo`, `--size`, `--border`, `--url`, `--prueba`, `--mostrar`; `registrar_com()` y `servir_automate()` con imports diferidos de pywin32 |
| Tests | `tests/test_core_qr.py` | cobertura del núcleo sin red ni COM |
| Empaquetado | `setup.py` | se agregó `pyarcaws.core` a `packages` |

### Segundo módulo migrado: `pyi25`

El mismo patrón se replicó en `pyi25.py` (código de barras Entrelazado 2 de 5):

| Capa | Archivo | Contenido |
|------|---------|-----------|
| 1. Núcleo | `core/i25.py` | funciones `digito_verificador_modulo10()`, `calcular_ancho()`, `generar_imagen()`, constante `BARS` |
| 2. Wrapper | `pyi25.py` → `PyI25` | misma interfaz (`GenerarImagen`, `DigitoVerificadorModulo10`), GUID `_reg_clsid_` intacto, captura en `Excepcion`/`Traceback` + re-lanzado |
| 3. CLI | `pyi25.py` → `main()` | flags `--barras`, `--noverificador`, `--archivo`, `--mostrar`; `registrar_com()`, `servir_automate()` y `empaquetar_py2exe()` con imports diferidos |

Decisiones particulares de `pyi25`:

- El núcleo usa **funciones de módulo** (no una clase): la generación es
  stateless, sin parámetros de estilo persistentes como en el QR.
- El `print(width)` de debug que hacía `GenerarImagen` al calcular el ancho
  automático **se conservó en el wrapper** (no en el núcleo) para que la
  salida de consola sea idéntica; candidato a eliminar más adelante.
- `pyi25.py` tenía además una rama `py2exe` propia en `main()` (empaquetado
  standalone); quedó en `empaquetar_py2exe()` con imports diferidos.
- Se eliminó el import sin uso de `PIL.ImageFont`; riesgo residual: código
  que hiciera `from pyarcaws.pyi25 import Image` (no se encontró ninguno).
- Verificación: CLI vieja vs nueva idéntica (default, `--barras` par e impar,
  `--noverificador`, `--archivo` JPG) e imágenes byte a byte iguales;
  `tests/test_pyi25.py` (5/5) sin cambios y 8 tests nuevos en
  `tests/test_core_i25.py`.

## Decisiones de diseño y hallazgos

- **Excepciones: capturar y re-lanzar.** El código original declaraba
  `Excepcion`/`Traceback` en `_public_attrs_` pero nunca los poblaba (y el
  `__init__` tenía un typo: inicializaba `self.Exception` en vez de
  `self.Excepcion`). Como `pyfepdf.GenerarQR()` depende de que las
  excepciones se propaguen (las captura su propio decorador), el wrapper
  ahora **puebla los atributos y re-lanza**: se gana la información para COM
  sin cambiar la propagación que espera el código Python existente.
- **El typo `self.Exception` se corrigió** a `self.Excepcion`. Riesgo
  residual: código que leyera el atributo `Exception` (improbable; no estaba
  en `_public_attrs_`).
- **`qrcode` ya no se importa en `pyqr.py`**: el default de
  `error_correction` viene de `core.qr.DEFAULT_ERROR_CORRECTION` (mismo
  valor, `ERROR_CORRECT_L`). Si algún código hacía `from pyarcaws.pyqr
  import qrcode`, dejaría de andar (no se encontró ningún uso así).
- **El bug de `url` sin definir en `main()`** ya estaba mitigado con
  `url = None` al inicio; se mantuvo y ahora las ramas COM están en
  funciones aparte, con lo que el flujo es más claro.
- **Quirk preservado adrede**: `--archivo` setea `PyQR.Extension` (atributo
  de **clase**, no de instancia), afectando instancias futuras en el mismo
  proceso. Es raro pero se conservó para no cambiar comportamiento en esta
  PoC. Candidato a corregir cuando se replique el patrón.
- **`CrearArchivo` ahora cierra el descriptor** del archivo temporal (el
  original lo dejaba abierto hasta el GC). Mismo contrato, sin fuga de fd.
- **Verificación de equivalencia**: la salida de la CLI vieja y nueva es
  idéntica (incluso con `--datos`/`--size`/`--border`/`--url`) y las
  imágenes generadas son **byte a byte iguales**.

## Checklist replicable para el próximo módulo

Para `pyi25.py` (siguiente candidato, también simple):

1. Leer el módulo completo y buscar **todos** los consumidores
   (`grep -rn "from pyarcaws.pyi25 import\|import pyi25"`), incluidos
   `setup.cfg` (entry point), `windows/setup_win.py` y los tests.
2. Crear `core/<modulo>.py` con la lógica pura:
   - sin `_public_*`/`_reg_*`, sin `get_install_dir()` a nivel módulo,
   - API snake_case con type hints, excepciones normales,
   - parámetros de configuración como argumentos del constructor o de los
     métodos (nada de atributos de clase mutables).
3. Reescribir la clase histórica como wrapper:
   - mismos nombres CamelCase, mismos `_public_methods_`/`_public_attrs_`,
   - **GUIDs (`_reg_clsid_`, `_typelib_guid_`) intactos**,
   - capturar excepciones del núcleo en `Excepcion`/`Traceback` y re-lanzar,
   - `InstallDir` solo en esta capa.
4. En `main()`: extraer las ramas `--register`/`--unregister`/`/Automate` a
   funciones con import diferido de `pythoncom`/`win32com`.
5. Agregar el submódulo nuevo a `packages` en `setup.py` (solo la primera
   vez por subpaquete).
6. Tests:
   - `tests/test_core_<modulo>.py` sin red ni COM (marcar `dontusefix`),
   - test de que importar el núcleo no carga `pythoncom`/`win32com`,
   - correr los tests existentes del módulo y de sus consumidores **antes**
     del cambio (línea base) y después, comparando fallos.
7. Smoke test de CLI: capturar la salida de la versión vieja
   (`git show HEAD:<modulo>.py > /tmp/old.py`) y la nueva con los mismos
   flags, y hacer `diff`; si genera archivos, comparar con `cmp`.

### Notas para módulos con `BaseWS` (etapa posterior)

- `BaseWS` (en `utils.py`) ya concentra la infraestructura común; la capa
  COM ahí no está en cada clase sino en el patrón `main()` +
  `win32com.server.register`. La separación probablemente sea:
  núcleo = cliente SOAP + armado de mensajes; wrapper = `BaseWS` actual con
  sus decoradores `inicializar_y_capturar_excepciones` (que ya implementan
  el patrón `Excepcion`/`Traceback`, con `LanzarExcepciones` configurable).
- Ojo con el estado mutable compartido (`self.factura`, colas de detalles,
  etc.): al extraer el núcleo conviene que sean estructuras explícitas que
  se pasan/devuelven, no atributos acumulados.
- Los tests de esos módulos dependen de cassettes VCR/red: armar la línea
  base con `-m dontusefix` y los cassettes existentes antes de tocar nada.

## Estado de los tests (en esta PoC)

- Nuevos: `tests/test_core_qr.py` → **9 passed**.
- Compatibilidad: `tests/test_pyqr.py` → **6 passed** (incluye comparación
  de imagen contra referencia, sin cambios); `tests/test_pyfepdf.py` (sin
  los `test_main_*`) → **9 passed**, incluido `test_generar_qr` que usa
  `PyQR` desde `pyfepdf`.
- Preexistente (sin relación con este cambio, igual antes y después):
  - los `test_main_*` de `test_pyfepdf.py` quedan girando en un bucle
    infinito (100% CPU) — excluidos de la línea base,
  - `test_pyfepdf.py::test_generar_qr` falla si se corre **aislado**
    (`KeyError: 'fecha_cbte'`): depende de que los tests anteriores del
    archivo armen la factura compartida,
  - ~43 fallos `SystemExit: Imposible autenticar...` en los tests que
    requieren red/certificados (algunos flaky entre corridas).
