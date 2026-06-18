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

"""Replay offline (cassette VCR) de WSCPE contra el endpoint NUEVO.

ARCA migró WSCPE del host `fwshomo` (homologación) a `cpea-ws-qaext.afip.gob.ar`
(ver nota de endpoint en `wscpe.py`). Este cassette se grabó contra ese endpoint
vigente: incluye el GET del WSDL + el POST de `dummy`. Como `Dummy` no requiere
autenticación (ni token/sign ni CUIT), el cassette no tiene material sensible y
valida **en vivo** que el endpoint nuevo conecta y responde.

`vcr` + `dontusefix`: corre offline, sin red ni certificado. Matchea por
método+URI contra el mismo host nuevo con que se grabó.

Nota: los 33 cassettes heredados (`tests/cassettes/test_wscpe/`) se grabaron
contra el host VIEJO `fwshomo` y dependen de la fixture `auth` (cert WSAA, sólo
`--run-online`); no replayean offline. Re-grabarlos contra el endpoint nuevo
requiere autorizar `wscpe` en WSASS (las operaciones con auth dan hoy
`coe.notAuthorized`).
"""

import pytest

from pyarcaws.wscpe import WSCPE, WSDL

pytestmark = [pytest.mark.vcr, pytest.mark.dontusefix]


def test_dummy_homologacion():
    """Replay de Conectar (WSDL nuevo) + Dummy contra el endpoint cpea-ws-qaext."""
    w = WSCPE()
    w.LanzarExcepciones = False
    assert w.Conectar("", WSDL[True]) is True
    w.Dummy()
    assert w.AppServerStatus == "Ok"
    assert w.DbServerStatus == "Ok"
    assert w.AuthServerStatus == "Ok"
