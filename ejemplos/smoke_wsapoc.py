#!/usr/bin/python
# -*- coding: utf8 -*-
"""Smoke en vivo (GATEADO) — WSAPOC (consulta de apócrifos, base APOC).

Cubre `Dummy` + `Consultar(cuit)` (GetPublicacionAPOC: ¿el CUIT está en la base
de apócrifos?). Es solo lectura; no emite ni modifica nada.

NO ejecutar hasta confirmar que `wsapoc` está autorizado al certificado en
WSASS. Mientras no lo esté, ARCA responde un error de autorización (se captura
y se imprime; no rompe).

Uso:
    python ejemplos/smoke_wsapoc.py \
        --cert /ruta/cert.crt --key /ruta/clave.key --cuit-deleg 30999999999 \
        [--consultar 20267565393] [--prod]
"""

import argparse
import sys
import traceback

from pyarcaws.wsaa import WSAA
from pyarcaws.wsapoc import WSAPOC

WSDL_HOMO = "https://eapoc-ws-qaext.afip.gob.ar/Service.asmx?WSDL"
WSDL_PROD = "https://eapoc-ws.afip.gob.ar/service.asmx?WSDL"
SERVICE = "wsapoc"


def parse_args(argv):
    p = argparse.ArgumentParser(description="Smoke WSAPOC apócrifos (gateado)")
    p.add_argument("--cert", required=True, help="ruta al certificado .crt")
    p.add_argument("--key", required=True, help="ruta a la clave privada .key")
    p.add_argument("--cuit-deleg", required=True, dest="cuit_deleg",
                   help="CUITDelegado (el CUIT autenticado)")
    p.add_argument("--consultar", default="20267565393",
                   help="CUIT a consultar en la base de apócrifos")
    p.add_argument("--prod", action="store_true", help="usar producción (default: homologación)")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    wsdl = WSDL_PROD if args.prod else WSDL_HOMO

    print("=" * 70)
    print("SMOKE WSAPOC (apócrifos) —", "PRODUCCIÓN" if args.prod else "HOMOLOGACIÓN")
    print("Servicio WSAA:", SERVICE, "| solo lectura (Dummy + Consultar)")
    print("WSDL:", wsdl)
    print("=" * 70)

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

    wsapoc = WSAPOC()
    wsapoc.LanzarExcepciones = False
    wsapoc.SetTicketAcceso(ta)
    wsapoc.Cuit = args.cuit_deleg
    if not wsapoc.Conectar("", wsdl):
        print("[WSAPOC] No conectó:", wsapoc.Excepcion)
        return 1

    try:
        wsapoc.Dummy()
        print("\n[Dummy] App=%s Db=%s Auth=%s" % (
            wsapoc.AppServerStatus, wsapoc.DbServerStatus, wsapoc.AuthServerStatus))
    except Exception:
        traceback.print_exc()

    print("\n[Consultar] CUIT:", args.consultar)
    try:
        wsapoc.Consultar(args.consultar)
    except Exception:
        traceback.print_exc()
    print("Codigo:", wsapoc.CodigoRespuesta, "| Mensaje:", wsapoc.MensajeRespuesta)
    print("¿Es apócrifo?:", wsapoc.EsApocrifo)
    print("Resultados:", wsapoc.resultados)
    print("Excepcion:", wsapoc.Excepcion)

    print("\n--- XmlResponse (primeros 4000 chars) ---")
    print((wsapoc.XmlResponse or "")[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
