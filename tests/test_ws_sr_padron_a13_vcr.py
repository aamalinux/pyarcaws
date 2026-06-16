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

"""Tests de replay (cassette VCR) de WSSrPadronA13 contra el envelope real.

A diferencia de ``test_ws_sr_padron_a13.py`` (cliente falso), estos tests
reproducen interacciones **reales** grabadas contra homologación (WSDL vivo
personaServiceA13 + respuestas), validando el parseo contra la estructura de
envelope/namespaces real de ARCA.

Cassettes saneados: token/sign del Ticket de Acceso reemplazados por
placeholders y CUIT representada del titular por una sintética. La persona
consultada (30500010912) es una entidad de homologación con datos de relleno
(sin PII real); los CUIT de la búsqueda inversa son datos de prueba de homo.
El replay matchea por método+URI (no por body), así que las credenciales
saneadas no afectan la reproducción.

Se combina ``vcr`` (reproduce el cassette) con ``dontusefix`` (saltea la fixture
de autenticación viva): corren **offline**, sin certificado ni red.
"""

import pytest

from pyarcaws.ws_sr_padron import WSSrPadronA13

pytestmark = [pytest.mark.vcr, pytest.mark.dontusefix]

WSDL = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13?wsdl"


def _nuevo():
    w = WSSrPadronA13()
    w.LanzarExcepciones = False
    w.Token, w.Sign = "TOKEN_SANITIZED", "SIGN_SANITIZED"
    w.Cuit = 20111111112
    assert w.Conectar("", WSDL) is True
    return w


def test_consultar_a13_homologacion():
    """Replay de getPersona real: persona jurídica activa de homologación."""
    w = _nuevo()
    ok = w.Consultar("30500010912")
    assert ok is True
    assert w.cuit == 30500010912
    assert w.tipo_persona == "JURIDICA"
    assert w.denominacion  # razón social / denominación poblada
    assert w.estado == "ACTIVO"


def test_lista_por_documento_homologacion():
    """Replay de getIdPersonaListByDocumento: lista real de varios idPersona."""
    w = _nuevo()
    ok = w.ConsultarListaPersonaPorDocumento("12345678")
    assert ok is True
    # el envelope real trae varios <idPersona>: el parseo con como_lista debe
    # devolver una lista de enteros (no romperse ni quedarse con uno solo)
    assert isinstance(w.personas, list)
    assert len(w.personas) > 1
    assert all(isinstance(p, int) for p in w.personas)
