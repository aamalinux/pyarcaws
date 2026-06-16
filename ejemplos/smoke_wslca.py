#!/usr/bin/python
# -*- coding: utf8 -*-
"""Smoke en vivo (GATEADO) — WSLCA (Liquidación de Caña de Azúcar).

Cubre la superficie de lectura segura: `Dummy` + catálogos (provincias,
tributos, tipos de comprobante, puntos de venta, condiciones de venta, medios
de pago, otros conceptos). NO emite ni autoriza ninguna liquidación.

NO ejecutar hasta confirmar que `wslca` está autorizado al certificado en
WSASS. Mientras no lo esté, ARCA responde un error de autorización (se captura
y se imprime; no rompe).

Uso:
    python ejemplos/smoke_wslca.py \
        --cert /ruta/cert.crt --key /ruta/clave.key --cuit-repr 30999999999 \
        [--prod]
"""

import argparse
import sys
import traceback

from pyarcaws.wsaa import WSAA
from pyarcaws.wslca import WSLCA

WSDL_HOMO = "https://fwshomo.afip.gov.ar/wslca/services/soap?wsdl"
WSDL_PROD = "https://serviciosjava.afip.gob.ar/wslca/services/soap?wsdl"
SERVICE = "wslca"


def parse_args(argv):
    p = argparse.ArgumentParser(description="Smoke WSLCA caña de azúcar (gateado)")
    p.add_argument("--cert", required=True, help="ruta al certificado .crt")
    p.add_argument("--key", required=True, help="ruta a la clave privada .key")
    p.add_argument("--cuit-repr", required=True, dest="cuit_repr",
                   help="CUIT representado (el autenticado)")
    p.add_argument("--prod", action="store_true", help="usar producción (default: homologación)")
    return p.parse_args(argv)


def _catalogo(wslca, nombre, metodo, *args):
    print("\n[%s]" % nombre)
    try:
        # el método decorado devuelve None si capturó un error de negocio
        # (p. ej. "800: sin resultados"); tolerarlo y mostrar el ErrMsg abajo
        for fila in (metodo(*args) or []):
            print("  ", fila)
    except Exception:
        traceback.print_exc()
    if wslca.ErrMsg:
        print("   ErrMsg:", wslca.ErrMsg)


def main(argv):
    args = parse_args(argv)
    wsdl = WSDL_PROD if args.prod else WSDL_HOMO

    print("=" * 70)
    print("SMOKE WSLCA (caña de azúcar) —", "PRODUCCIÓN" if args.prod else "HOMOLOGACIÓN")
    print("Servicio WSAA:", SERVICE, "| solo lectura (Dummy + catálogos)")
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

    wslca = WSLCA()
    wslca.LanzarExcepciones = False
    wslca.SetTicketAcceso(ta)
    wslca.Cuit = args.cuit_repr
    if not wslca.Conectar("", wsdl):
        print("[WSLCA] No conectó:", wslca.Excepcion)
        return 1

    try:
        wslca.Dummy()
        print("\n[Dummy] App=%s Db=%s Auth=%s" % (
            wslca.AppServerStatus, wslca.DbServerStatus, wslca.AuthServerStatus))
    except Exception:
        traceback.print_exc()

    _catalogo(wslca, "Provincias", wslca.ConsultarProvincias)
    _catalogo(wslca, "Tributos", wslca.ConsultarTributos)
    _catalogo(wslca, "TiposComprobante", wslca.ConsultarTiposComprobante)
    _catalogo(wslca, "PuntosVenta", wslca.ConsultarPuntosVenta)
    _catalogo(wslca, "CondicionesVenta", wslca.ConsultarCondicionesVenta)
    _catalogo(wslca, "MediosPago", wslca.ConsultarMediosPago)
    _catalogo(wslca, "OtrosConceptos", wslca.ConsultarOtrosConceptos)

    print("\n[Excepcion final]:", wslca.Excepcion)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
