#!/usr/bin/python
# -*- coding: utf8 -*-
"""Smoke en vivo (GATEADO) — Padrón Alcance 10: getPersona (datos mínimos).

Validación rápida de un CUIT. Servicio WSAA `ws_sr_padron_a10`.

NO ejecutar hasta confirmar que `ws_sr_padron_a10` está autorizado al
certificado en WSASS. Mientras no lo esté, AFIP responde `coe.notAuthorized`
(se captura y se imprime; no rompe).

Uso:
    python ejemplos/smoke_padron_a10.py \
        --cert /ruta/cert.crt --key /ruta/clave.key --cuit-repr 30999999999 \
        [--persona 20267565393] [--prod]
"""

import argparse
import json
import sys
import traceback

from pyarcaws.wsaa import WSAA
from pyarcaws.ws_sr_padron import WSSrPadronA10

WSDL_HOMO = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA10?WSDL"
WSDL_PROD = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA10?WSDL"
SERVICE = "ws_sr_padron_a10"


def parse_args(argv):
    p = argparse.ArgumentParser(description="Smoke Padrón A10 (gateado)")
    p.add_argument("--cert", required=True, help="ruta al certificado .crt")
    p.add_argument("--key", required=True, help="ruta a la clave privada .key")
    p.add_argument("--cuit-repr", required=True, dest="cuit_repr",
                   help="CUIT representado (el autenticado)")
    p.add_argument("--persona", default="20267565393",
                   help="CUIT a consultar (default 20267565393)")
    p.add_argument("--prod", action="store_true", help="usar producción (default: homologación)")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    wsdl = WSDL_PROD if args.prod else WSDL_HOMO

    print("=" * 70)
    print("SMOKE Padrón Alcance 10 —", "PRODUCCIÓN" if args.prod else "HOMOLOGACIÓN")
    print("Servicio WSAA:", SERVICE, "| operación: getPersona")
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

    padron = WSSrPadronA10()
    padron.LanzarExcepciones = False  # degradar limpio, capturar todo textual
    padron.SetTicketAcceso(ta)
    padron.Cuit = args.cuit_repr
    if not padron.Conectar("", wsdl):
        print("[Padrón A10] No conectó:", padron.Excepcion)
        return 1

    # --- 2) Dummy ---------------------------------------------------------
    try:
        padron.Dummy()
        print("\n[Dummy] App=%s Db=%s Auth=%s" % (
            padron.AppServerStatus, padron.DbServerStatus, padron.AuthServerStatus))
    except Exception:
        traceback.print_exc()

    # --- 3) Consultar (getPersona) ----------------------------------------
    print("\n[Consulta] idPersona:", args.persona)
    try:
        padron.Consultar(args.persona)
    except Exception:
        traceback.print_exc()

    print("\n--- Resultado (datos mínimos A10) ---")
    print("denominacion:", padron.denominacion)
    print("tipo/nro doc:", padron.tipo_persona, padron.tipo_doc, padron.nro_doc)
    print("estado:", padron.estado)
    print("domicilio:", padron.domicilio)
    print("actividad principal:", padron.actividades, padron.actividad_principal)
    print("ErrMsg:", padron.ErrMsg)
    print("Excepcion:", padron.Excepcion)
    print("\n--- Persona (JSON crudo de AFIP) ---")
    try:
        print(json.dumps(json.loads(padron.Persona), indent=2, ensure_ascii=False))
    except Exception:
        print(padron.Persona)
    print("\n--- XmlResponse (primeros 4000 chars) ---")
    print((padron.XmlResponse or "")[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
