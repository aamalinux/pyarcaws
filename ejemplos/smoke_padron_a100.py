#!/usr/bin/python
# -*- coding: utf8 -*-
"""Smoke en vivo (GATEADO) — Padrón Alcance 100 (tablas de parámetros).

Consulta una colección de parámetros por nombre (`getParameterCollectionByName`).
Servicio WSAA `ws_sr_padron_a100`. Solo lectura.

NO ejecutar hasta confirmar que `ws_sr_padron_a100` está autorizado al
certificado en WSASS. Mientras no lo esté, ARCA responde error de autorización
(se captura y se imprime; no rompe).

Uso:
    python ejemplos/smoke_padron_a100.py \
        --cert /ruta/cert.crt --key /ruta/clave.key --cuit-repr 30999999999 \
        [--coleccion Provincias] [--prod]
"""

import argparse
import sys
import traceback

from pyarcaws.wsaa import WSAA
from pyarcaws.ws_sr_padron import WSSrPadronA100

WSDL_HOMO = "https://awshomo.afip.gov.ar/sr-parametros/webservices/parameterServiceA100?wsdl"
WSDL_PROD = "https://aws.afip.gov.ar/sr-parametros/webservices/parameterServiceA100?wsdl"
SERVICE = "ws_sr_padron_a100"


def parse_args(argv):
    p = argparse.ArgumentParser(description="Smoke Padrón A100 (gateado)")
    p.add_argument("--cert", required=True, help="ruta al certificado .crt")
    p.add_argument("--key", required=True, help="ruta a la clave privada .key")
    p.add_argument("--cuit-repr", required=True, dest="cuit_repr",
                   help="CUIT representado (el autenticado)")
    p.add_argument("--coleccion", default="Provincias",
                   help="nombre de la colección de parámetros (default Provincias)")
    p.add_argument("--prod", action="store_true", help="usar producción (default: homologación)")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    wsdl = WSDL_PROD if args.prod else WSDL_HOMO

    print("=" * 70)
    print("SMOKE Padrón Alcance 100 —", "PRODUCCIÓN" if args.prod else "HOMOLOGACIÓN")
    print("Servicio WSAA:", SERVICE, "| getParameterCollectionByName")
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

    padron = WSSrPadronA100()
    padron.LanzarExcepciones = False
    padron.SetTicketAcceso(ta)
    padron.Cuit = args.cuit_repr
    if not padron.Conectar("", wsdl):
        print("[Padrón A100] No conectó:", padron.Excepcion)
        return 1

    try:
        padron.Dummy()
        print("\n[Dummy] App=%s Db=%s Auth=%s" % (
            padron.AppServerStatus, padron.DbServerStatus, padron.AuthServerStatus))
    except Exception:
        traceback.print_exc()

    print("\n[Consultar] colección:", args.coleccion)
    try:
        padron.Consultar(args.coleccion)
    except Exception:
        traceback.print_exc()
    print("Nombre:", getattr(padron, "nombre", ""))
    print("Cantidad de parámetros:", len(padron.parametros))
    for p in padron.parametros[:10]:
        print("  ", p.get("id"), "->", p.get("descripcion"))
    if len(padron.parametros) > 10:
        print("   ... (%d más)" % (len(padron.parametros) - 10))
    print("ErrMsg:", padron.ErrMsg, "| Excepcion:", padron.Excepcion)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
