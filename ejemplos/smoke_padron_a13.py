#!/usr/bin/python
# -*- coding: utf8 -*-
"""Smoke en vivo (GATEADO) — Padrón Alcance 13.

Cubre lo distintivo de A13: la búsqueda inversa por número de documento
(`getIdPersonaListByDocumento`: documento → lista de idPersona/CUIT), además de
`getPersona` y `Dummy`. Servicio WSAA `ws_sr_padron_a13`.

NO ejecutar hasta confirmar que `ws_sr_padron_a13` está autorizado al
certificado en WSASS. Mientras no lo esté, ARCA responde `coe.notAuthorized`
(se captura y se imprime; no rompe).

Uso:
    python ejemplos/smoke_padron_a13.py \
        --cert /ruta/cert.crt --key /ruta/clave.key --cuit-repr 30999999999 \
        [--persona 20267565393] [--documento 26756539] [--prod]
"""

import argparse
import sys
import traceback

from pyarcaws.wsaa import WSAA
from pyarcaws.ws_sr_padron import WSSrPadronA13

WSDL_HOMO = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13?WSDL"
WSDL_PROD = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13?WSDL"
SERVICE = "ws_sr_padron_a13"


def parse_args(argv):
    p = argparse.ArgumentParser(description="Smoke Padrón A13 (gateado)")
    p.add_argument("--cert", required=True, help="ruta al certificado .crt")
    p.add_argument("--key", required=True, help="ruta a la clave privada .key")
    p.add_argument("--cuit-repr", required=True, dest="cuit_repr",
                   help="CUIT representado (el autenticado)")
    p.add_argument("--persona", default="20267565393",
                   help="CUIT a consultar con getPersona (default 20267565393)")
    p.add_argument("--documento", default="26756539",
                   help="Nro de documento para la búsqueda inversa (default 26756539)")
    p.add_argument("--prod", action="store_true", help="usar producción (default: homologación)")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    wsdl = WSDL_PROD if args.prod else WSDL_HOMO

    print("=" * 70)
    print("SMOKE Padrón Alcance 13 —", "PRODUCCIÓN" if args.prod else "HOMOLOGACIÓN")
    print("Servicio WSAA:", SERVICE)
    print("Operaciones: dummy / getPersona / getIdPersonaListByDocumento")
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

    padron = WSSrPadronA13()
    padron.LanzarExcepciones = False
    padron.SetTicketAcceso(ta)
    padron.Cuit = args.cuit_repr
    if not padron.Conectar("", wsdl):
        print("[Padrón A13] No conectó:", padron.Excepcion)
        return 1

    # --- Dummy ------------------------------------------------------------
    try:
        padron.Dummy()
        print("\n[Dummy] App=%s Db=%s Auth=%s" % (
            padron.AppServerStatus, padron.DbServerStatus, padron.AuthServerStatus))
    except Exception:
        traceback.print_exc()

    # --- getPersona (heredado de A10) -------------------------------------
    print("\n[getPersona] idPersona:", args.persona)
    try:
        padron.Consultar(args.persona)
    except Exception:
        traceback.print_exc()
    print("denominacion:", padron.denominacion)
    print("estado:", padron.estado, "| tipo/nro:", padron.tipo_persona, padron.nro_doc)
    print("ErrMsg:", padron.ErrMsg, "| Excepcion:", padron.Excepcion)

    # --- getIdPersonaListByDocumento (lo distintivo de A13) ---------------
    print("\n[getIdPersonaListByDocumento] documento:", args.documento)
    try:
        padron.ConsultarListaPersonaPorDocumento(args.documento)
    except Exception:
        traceback.print_exc()
    print("personas (idPersona/CUIT):", padron.personas)
    print("ErrMsg:", padron.ErrMsg, "| Excepcion:", padron.Excepcion)

    print("\n--- XmlResponse (primeros 4000 chars) ---")
    print((padron.XmlResponse or "")[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
