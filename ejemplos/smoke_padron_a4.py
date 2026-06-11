#!/usr/bin/python
# -*- coding: utf8 -*-
"""Smoke en vivo (GATEADO) — Padrón A4: getPersona con caracterizaciones.

NO ejecutar hasta confirmar que el servicio `ws_sr_padron_a4` está habilitado en
el Administrador de Relaciones para el certificado. Mientras no lo esté, AFIP
responde `coe.notAuthorized` (se captura y se imprime; no rompe).

Objetivo: volcar las caracterizaciones crudas del CUIT consultado para detectar
la caracterización 639 (Ganancias Simplificada Ley 27.779), que la constancia A5
no publica, y observar el tag opcional `fechaSolicitud` (ARCA 11/02/2026).

Reglas de seguridad: SÓLO Dummy() y Consultar. Un único intento de TA.

Uso:
    python ejemplos/smoke_padron_a4.py \
        --cert /ruta/cert.crt --key /ruta/clave.key --cuit-repr 30999999999 \
        [--persona 30673134773] [--prod]
"""

import argparse
import json
import sys
import traceback

from pyarcaws.wsaa import WSAA
from pyarcaws.ws_sr_padron import WSSrPadronA4

WSDL_HOMO = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4?wsdl"
WSDL_PROD = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4?wsdl"
SERVICE = "ws_sr_padron_a4"


def parse_args(argv):
    p = argparse.ArgumentParser(description="Smoke Padrón A4 (gateado)")
    p.add_argument("--cert", required=True, help="ruta al certificado .crt")
    p.add_argument("--key", required=True, help="ruta a la clave privada .key")
    p.add_argument("--cuit-repr", required=True, dest="cuit_repr",
                   help="CUIT representado (el autenticado)")
    p.add_argument("--persona", default="30673134773",
                   help="CUIT a consultar (default 30673134773)")
    p.add_argument("--prod", action="store_true", help="usar producción (default: homologación)")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    wsdl = WSDL_PROD if args.prod else WSDL_HOMO

    print("=" * 70)
    print("SMOKE Padrón A4 —", "PRODUCCIÓN" if args.prod else "HOMOLOGACIÓN")
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

    padron = WSSrPadronA4()
    padron.LanzarExcepciones = False  # degradar limpio, capturar todo textual
    padron.SetTicketAcceso(ta)
    padron.Cuit = args.cuit_repr
    if not padron.Conectar("", wsdl):
        print("[Padrón A4] No conectó:", padron.Excepcion)
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

    print("\n--- Resultado ---")
    print("denominacion:", padron.denominacion)
    print("estado:", padron.estado)
    print("ErrMsg:", padron.ErrMsg)
    print("ErrCode:", padron.ErrCode)
    print("Excepcion:", padron.Excepcion)
    print("\n--- Caracterizaciones (parseadas) ---")
    import pprint
    pprint.pprint(padron.caracterizaciones)
    print("¿Tiene 639?:", any(c.get("id") == 639 for c in padron.caracterizaciones))
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
