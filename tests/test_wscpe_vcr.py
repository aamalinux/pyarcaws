#!/usr/bin/python
# -*- coding: utf8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

"""Replay offline (cassettes VCR) de WSCPE contra el endpoint NUEVO.

ARCA migró WSCPE del host `fwshomo` (homologación) a `cpea-ws-qaext.afip.gob.ar`
(ver nota de endpoint en `wscpe.py`). Estos cassettes se grabaron contra ese
endpoint vigente, en homologación con el certificado de autogestión WSASS:
incluyen el GET del WSDL + el POST de la operación. Cassettes **saneados**:
token/sign del Ticket de Acceso → placeholders, CUIT del agente → sintético;
cookies `Set-Cookie` del balanceador filtradas. Los catálogos devuelven datos
de referencia de ARCA (provincias, tipos de grano, localidades), sin PII.

`vcr` + `dontusefix`: corren offline, sin red ni certificado. Matchean por
método+URI contra el mismo host nuevo con que se grabaron.

Nota: los 33 cassettes heredados (`tests/cassettes/test_wscpe/`) se grabaron
contra el host VIEJO `fwshomo` y dependen de la fixture `auth` (cert WSAA, sólo
`--run-online`); no replayean offline. Quedan como están; estos cassettes nuevos
los reemplazan para la validación offline de lectura.
"""

import pytest

from pyarcaws.wscpe import WSCPE, WSDL

pytestmark = [pytest.mark.vcr, pytest.mark.dontusefix]

HOMO = WSDL[True]


def _conectado():
    w = WSCPE()
    w.LanzarExcepciones = False
    # token/sign/cuit de relleno (los cassettes están saneados y matchean por URI)
    w.Token, w.Sign, w.Cuit = "TOKEN_SANITIZED", "SIGN_SANITIZED", 20111111112
    assert w.Conectar("", HOMO) is True
    return w


def test_dummy_homologacion():
    """Conectar (WSDL nuevo) + Dummy contra cpea-ws-qaext (sin auth)."""
    w = WSCPE()
    w.LanzarExcepciones = False
    assert w.Conectar("", HOMO) is True
    w.Dummy()
    assert w.AppServerStatus == "Ok"
    assert w.DbServerStatus == "Ok"
    assert w.AuthServerStatus == "Ok"


def test_consultar_provincias():
    """Catálogo de provincias real de ARCA (valida el parseo de <errores> vacío)."""
    w = _conectado()
    provincias = w.ConsultarProvincias(sep=None)
    assert w.Errores == []
    assert isinstance(provincias, list) and len(provincias) >= 24
    porcodigo = {p["codigo"]: p["descripcion"] for p in provincias}
    assert porcodigo["1"] == "BUENOS AIRES"
    assert porcodigo["0"] == "CAP.FEDERAL"


def test_consultar_tipos_grano():
    w = _conectado()
    granos = w.ConsultarTiposGrano(sep=None)
    assert w.Errores == []
    assert isinstance(granos, list) and len(granos) >= 30
    # cada item es {codigo, descripcion}
    assert all("codigo" in g and "descripcion" in g for g in granos)


def test_consultar_localidades_por_provincia():
    w = _conectado()
    localidades = w.ConsultarLocalidadesPorProvincia(cod_provincia=1, sep=None)
    assert w.Errores == []
    assert isinstance(localidades, list) and len(localidades) > 100
    assert all("codigo" in loc and "descripcion" in loc for loc in localidades)


def test_consultar_ult_nro_orden():
    """ConsultarUltNroOrden envía `solicitud` y parsea sin romper (agente sin CPE)."""
    w = _conectado()
    w.ConsultarUltNroOrden(sucursal=1, tipo_cpe=74)
    assert w.Errores == []
    # el agente de prueba no tiene CPE en esa sucursal: nroOrden 0
    assert w.NroOrden == 0
