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

"""Test de replay (cassette VCR) de WSSrConstanciaInscripcion (getPersona_v2).

Reproduce una interacción **real** grabada contra homologación (WSDL vivo
personaServiceA5 + respuesta de getPersona_v2), validando el parseo de la
constancia (denominación, estado, impuestos y bloque ``caracterizacion`` con
``fechaSolicitud``) contra la estructura de envelope real de ARCA.

Cassette saneado: token/sign reemplazados por placeholders, CUIT representada del
titular del certificado reemplazada por una sintética; la persona consultada
(30500010912) es una entidad de homologación con datos de relleno (sin PII real).
El replay matchea por método+URI (no por body). Combina ``vcr`` (reproduce) con
``dontusefix`` (saltea la auth viva): corre **offline**, sin certificado ni red.
"""

import pytest

from pyarcaws.ws_sr_padron import WSSrConstanciaInscripcion

pytestmark = [pytest.mark.vcr, pytest.mark.dontusefix]

WSDL = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl"


def test_consultar_constancia_homologacion():
    """Replay del getPersona_v2 real: Conectar (WSDL del cassette) + Consultar."""
    w = WSSrConstanciaInscripcion()
    w.LanzarExcepciones = False
    w.Token, w.Sign = "TOKEN_SANITIZED", "SIGN_SANITIZED"
    w.Cuit = 20111111112

    assert w.Conectar("", WSDL) is True
    ok = w.Consultar("30500010912")
    assert ok is True
    # la respuesta real se parseó:
    assert w.data.get("idPersona") == 30500010912
    assert w.tipo_persona == "JURIDICA"
    assert w.estado == "ACTIVO"
    assert w.denominacion  # razón social poblada
    assert w.impuestos  # constancia trae el listado de impuestos activos
    # bloque caracterizacion parseado (id/descripcion/periodo + fechaSolicitud)
    assert w.caracterizaciones
    car = w.caracterizaciones[0]
    assert "id" in car and "descripcion" in car and "fecha_solicitud" in car
