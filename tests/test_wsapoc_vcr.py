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

"""Test de replay (cassette VCR) de WSAPOC contra el envelope real.

Reproduce una interacción real grabada contra homologación (WSDL vivo
``eapoc-ws-qaext.afip.gob.ar/Service.asmx`` + consulta), validando el parseo del
``MessageResponse`` (codigo/descripcion/resultados) contra la estructura real.

Cassette saneado: token/sign del Ticket de Acceso reemplazados por placeholders
y CUITDelegado del titular por una sintética. El replay matchea por método+URI;
las llamadas se hacen en el mismo orden que la grabación.

``vcr`` + ``dontusefix``: corre **offline**, sin certificado ni red.
"""

import pytest

from pyarcaws.wsapoc import WSAPOC

pytestmark = [pytest.mark.vcr, pytest.mark.dontusefix]

WSDL = "https://eapoc-ws-qaext.afip.gob.ar/Service.asmx?WSDL"


def test_consultar_wsapoc_homologacion():
    """Replay de Dummy + Consultar real (CUIT no apócrifo → respuesta limpia)."""
    w = WSAPOC()
    w.LanzarExcepciones = False
    w.Token, w.Sign = "TOKEN_SANITIZED", "SIGN_SANITIZED"
    w.Cuit = 20111111112
    assert w.Conectar("", WSDL) is True

    # mismo orden que la grabación: Dummy, Consultar
    w.Dummy()

    ok = w.Consultar("20267565393")
    assert ok is True
    # MessageResponse real parseado: codigo 0/OK, sin publicaciones → no apócrifo
    assert w.CodigoRespuesta == "0"
    assert w.EsApocrifo is False
    assert w.resultados == []
