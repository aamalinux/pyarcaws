#!/usr/bin/python
# -*- coding: utf8 -*-
"""Smoke en vivo (GATEADO) — WSLSP: consultar una liquidación pecuaria como
receptor/comprador.

NO ejecutar hasta confirmar que el servicio `wslsp` está habilitado en el
Administrador de Relaciones para el certificado. Mientras no lo esté, AFIP
responde `coe.notAuthorized` (este script lo captura y lo imprime, no rompe).

Reglas de seguridad: SÓLO Dummy() y Consultar*. Jamás Autorizar/Generar/Liquidar.
Un único intento de TA.

Uso:
    python ejemplos/smoke_wslsp_receptor.py \
        --cert /ruta/cert.crt --key /ruta/clave.key --cuit 30999999999 \
        [--prod] [--tipo 190 --ptovta 3 --nro 16 --comprador 30690720023] \
        [--cae 86217130787511]

Caso de referencia (CABRAS): tipo 190, PV 3, N° 16, CUIT emisor 30690720023,
CAE 86217130787511, $80.735.921,11.

Nota técnica (ver docstring de WSLSP.ConsultarLiquidacion): el WSDL de
homologación v1.4.1 identifica la liquidación sólo por puntoVenta+tipoComprobante+
nroComprobante, acotada al CUIT autenticado; no hay parámetro cuitComprador. Este
script vuelca las operaciones reales del WSDL vivo para confirmar/desmentir eso
bajo el certificado habilitado.
"""

import argparse
import re
import sys
import traceback

from pyarcaws.wsaa import WSAA
from pyarcaws.wslsp import WSLSP

WSDL_HOMO = "https://fwshomo.afip.gov.ar/wslsp/LspService?wsdl"
WSDL_PROD = "https://serviciosjava.afip.gov.ar/wslsp/LspService?wsdl"
SERVICE = "wslsp"


def _redact(s):
    "Censura token/sign del Ticket de Acceso antes de imprimir (no loguear credenciales)"
    if isinstance(s, bytes):
        s = s.decode("utf-8", "replace")
    s = re.sub(r"(<token>).*?(</token>)", r"\1***REDACTED***\2", s or "", flags=re.S)
    s = re.sub(r"(<sign>).*?(</sign>)", r"\1***REDACTED***\2", s, flags=re.S)
    return s


def parse_args(argv):
    p = argparse.ArgumentParser(description="Smoke WSLSP receptor (gateado)")
    p.add_argument("--cert", required=True, help="ruta al certificado .crt")
    p.add_argument("--key", required=True, help="ruta a la clave privada .key")
    p.add_argument("--cuit", required=True, help="CUIT autenticado (el comprador/receptor)")
    p.add_argument("--prod", action="store_true", help="usar producción (default: homologación)")
    p.add_argument("--tipo", type=int, default=190, help="tipoComprobante (default 190)")
    p.add_argument("--ptovta", type=int, default=3, help="puntoVenta (default 3)")
    p.add_argument("--nro", type=int, default=16, help="nroComprobante (default 16)")
    p.add_argument("--comprador", default=None, help="cuit_comprador (informativo; ver docstring)")
    p.add_argument("--cae", default=None, help="consultar por CAE en vez de por nro")
    p.add_argument("--pdf", default="liq_smoke.pdf", help="archivo destino del PDF")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    wsdl = WSDL_PROD if args.prod else WSDL_HOMO

    print("=" * 70)
    print("SMOKE WSLSP receptor —", "PRODUCCIÓN" if args.prod else "HOMOLOGACIÓN")
    print("WSDL:", wsdl)
    print("=" * 70)

    # --- 1) Ticket de Acceso (un único intento) ---------------------------
    wsaa = WSAA()
    try:
        ta = wsaa.Autenticar(SERVICE, args.cert, args.key)
    except Exception:
        traceback.print_exc()
        ta = None
    print("\n[WSAA] Excepcion:", wsaa.Excepcion)
    if not ta:
        print("[WSAA] No se obtuvo TA. Abortando (sin reintentos).")
        print("[WSAA] Traceback:\n", wsaa.Traceback)
        return 1

    wslsp = WSLSP()
    wslsp.LanzarExcepciones = False  # degradar limpio, capturar todo textual
    wslsp.SetTicketAcceso(ta)
    wslsp.Cuit = args.cuit
    if not wslsp.Conectar("", wsdl):
        print("[WSLSP] No conectó:", wslsp.Excepcion)
        return 1

    # Volcar las operaciones reales del WSDL vivo (clave para confirmar el
    # esquema de la consulta por comprador):
    try:
        metodos = set()
        for svc in (wslsp.client.services or {}).values():
            for port in svc.get("ports", {}).values():
                metodos.update(port.get("operations", {}).keys())
        print("\n[WSDL] métodos disponibles:", sorted(metodos))
    except Exception as e:
        print("[WSDL] no se pudieron listar métodos:", e)

    # --- 2) Dummy (verificación de infraestructura) -----------------------
    try:
        wslsp.Dummy()
        print("\n[Dummy] App=%s Db=%s Auth=%s" % (
            wslsp.AppServerStatus, wslsp.DbServerStatus, wslsp.AuthServerStatus))
    except Exception:
        traceback.print_exc()

    # --- 2.5) Catálogos read-only: PRUEBA END-TO-END del fix de namespaces ---
    # Estas operaciones llevan auth+solicitud anidados; si el servidor las
    # acepta (devuelve datos) en vez de un fault cvc-.../[common_001], el
    # envelope corregido (hojas sin namespace) es válido contra el servicio vivo.
    for metodo, kwargs in [
        ("ConsultarProvincias", {}),
        ("ConsultarTiposComprobante", {}),
    ]:
        print("\n[Catálogo] %s ..." % metodo)
        try:
            res = getattr(wslsp, metodo)(**kwargs)
            n = len(res) if hasattr(res, "__len__") else "?"
            print("  OK — %s registros. Primeros 3: %s" % (n, (res or [])[:3]))
            print("  ErrMsg:", wslsp.ErrMsg, "| Excepcion:", wslsp.Excepcion)
            xmlreq = _redact(wslsp.XmlRequest)
            print("  XmlRequest (Body):",
                  xmlreq.split("<soapenv:Body>")[-1][:400])
        except Exception:
            traceback.print_exc()
            print("  XmlResponse:", (wslsp.XmlResponse or "")[:600])

    # --- 4) ConsultarUltimoComprobante (lectura) --------------------------
    print("\n[ConsultarUltimoComprobante] tipo=%s ptovta=%s" % (args.tipo, args.ptovta))
    try:
        ult = wslsp.ConsultarUltimoComprobante(tipo_cbte=args.tipo, pto_vta=args.ptovta)
        print("  Último Nro:", ult, "| ErrMsg:", wslsp.ErrMsg, "| Excepcion:", wslsp.Excepcion)
    except Exception:
        traceback.print_exc()

    # --- 5) ConsultarLiquidacion (lectura) --------------------------------
    print("\n[Consulta] tipo=%s ptovta=%s nro=%s cae=%s comprador=%s" % (
        args.tipo, args.ptovta, args.nro, args.cae, args.comprador))
    try:
        wslsp.ConsultarLiquidacion(
            tipo_cbte=args.tipo,
            pto_vta=args.ptovta,
            nro_cbte=args.nro,
            cae=args.cae,
            cuit_comprador=args.comprador,
            pdf=args.pdf,
        )
    except Exception:
        traceback.print_exc()

    print("\n--- Resultado ---")
    print("CAE:", wslsp.CAE)
    print("NroComprobante:", wslsp.NroComprobante)
    print("ImporteBruto:", wslsp.ImporteBruto)
    print("Errores:", wslsp.Errores)
    print("ErrMsg:", wslsp.ErrMsg)
    print("Excepcion:", wslsp.Excepcion)
    print("\n--- params_out (crudo) ---")
    import pprint
    pprint.pprint(getattr(wslsp, "params_out", None))
    print("\n--- XmlResponse (primeros 4000 chars) ---")
    print((wslsp.XmlResponse or "")[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
