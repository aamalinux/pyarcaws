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

"""Test de replay (cassette VCR) de WSSrPadronA10 contra el envelope real.

A diferencia de ``test_ws_sr_padron_a10.py`` (cliente falso), este test reproduce
una interacción **real** grabada contra homologación (WSDL vivo personaServiceA10
+ respuesta de getPersona), de modo que valida el parseo contra la estructura de
envelope/namespaces real de ARCA — no una modelada a mano.

Cassette saneado: token/sign del Ticket de Acceso reemplazados por placeholders,
CUIT representada del titular del certificado reemplazada por una sintética, y la
persona consultada (30500010912) es una entidad de homologación con datos de
relleno (sin PII real). El replay usa el match por método+URI (no por body), así
que las credenciales saneadas no afectan la reproducción.

Se combina ``vcr`` (reproduce el cassette) con ``dontusefix`` (saltea la fixture
de autenticación viva del conftest): el test corre **offline**, sin certificado
ni red, fijando Token/Sign directamente.
"""

import pytest

from pyarcaws.ws_sr_padron import WSSrPadronA10

pytestmark = [pytest.mark.vcr, pytest.mark.dontusefix]

WSDL = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA10?wsdl"


def test_consultar_a10_homologacion():
    """Replay del getPersona real: Conectar (WSDL del cassette) + Consultar."""
    w = WSSrPadronA10()
    w.LanzarExcepciones = False
    # credenciales placeholder (el cassette no matchea por body)
    w.Token, w.Sign = "TOKEN_SANITIZED", "SIGN_SANITIZED"
    w.Cuit = 20111111112

    assert w.Conectar("", WSDL) is True
    ok = w.Consultar("30500010912")
    assert ok is True
    # la respuesta real se parseó: persona jurídica de homologación
    assert w.cuit == 30500010912
    assert w.tipo_persona == "JURIDICA"
    assert w.denominacion  # razón social poblada
    assert w.estado  # estado de la clave poblado
    # A10 sólo expone la actividad principal (no el listado detallado)
    assert w.impuestos == []
