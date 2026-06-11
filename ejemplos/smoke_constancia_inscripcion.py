#!/usr/bin/python
# -*- coding: utf8 -*-
"""Smoke en vivo (GATEADO) — Consulta a Padrón Constancia de Inscripción.

Servicio nuevo `ws_sr_constancia_inscripcion` (manual V4.1), reemplazo del
deprecado `ws_sr_padron_a5`. Usa la operación `getPersona_v2`, que expone el tag
opcional `fechaSolicitud` dentro de cada `<caracterizacion>` (ARCA 11/02/2026).

NO ejecutar hasta confirmar que `ws_sr_constancia_inscripcion` está autorizado al
certificado en WSASS. Mientras no lo esté, AFIP responde `coe.notAuthorized`
(se captura y se imprime; no rompe).

Objetivo: volcar denominación, estado, impuestos y el listado completo de
caracterizaciones (con `fecha_solicitud` cuando venga) para detectar la 639
(Ganancias Simplificada Ley 27.779).

Uso:
    python ejemplos/smoke_constancia_inscripcion.py \
        --cert /ruta/cert.crt --key /ruta/clave.key --cuit-repr 30999999999 \
        [--persona 30673134773] [--prod]
"""

import argparse
import json
import sys
import traceback

from pyarcaws.wsaa import WSAA
from pyarcaws.ws_sr_padron import WSSrConstanciaInscripcion

WSDL_HOMO = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL"
WSDL_PROD = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL"
SERVICE = "ws_sr_constancia_inscripcion"


def parse_args(argv):
    p = argparse.ArgumentParser(description="Smoke Constancia de Inscripción (gateado)")
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
    print("SMOKE Constancia de Inscripción —", "PRODUCCIÓN" if args.prod else "HOMOLOGACIÓN")
    print("Servicio WSAA:", SERVICE, "| operación: getPersona_v2")
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

    padron = WSSrConstanciaInscripcion()
    padron.LanzarExcepciones = False  # degradar limpio, capturar todo textual
    padron.SetTicketAcceso(ta)
    padron.Cuit = args.cuit_repr
    if not padron.Conectar("", wsdl):
        print("[Constancia] No conectó:", padron.Excepcion)
        return 1

    # --- 2) Dummy ---------------------------------------------------------
    try:
        padron.Dummy()
        print("\n[Dummy] App=%s Db=%s Auth=%s" % (
            padron.AppServerStatus, padron.DbServerStatus, padron.AuthServerStatus))
    except Exception:
        traceback.print_exc()

    # --- 3) Consultar (getPersona_v2) -------------------------------------
    print("\n[Consulta] idPersona:", args.persona)
    try:
        padron.Consultar(args.persona)
    except Exception:
        traceback.print_exc()

    print("\n--- Resultado ---")
    print("denominacion:", padron.denominacion)
    print("estado:", padron.estado)
    print("impuestos:", padron.impuestos)
    print("actividades:", padron.actividades)
    print("Excepcion:", padron.Excepcion)
    print("errores:", padron.errores)
    print("\n--- Caracterizaciones (parseadas) ---")
    import pprint
    pprint.pprint(padron.caracterizaciones)
    print("¿Tiene 639?:", padron.TieneCaracterizacion(639))
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
