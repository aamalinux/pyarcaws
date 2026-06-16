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

"""Tests offline de PadronAFIP.Consultar (API REST/SOA del padrón).

Cubren el manejo robusto de respuestas que NO son JSON (el endpoint público
`soa.afip.gob.ar/sr-padron/v2/persona` hoy devuelve un HTML 404), incluido el
caso de un JSON truncado que igual empieza con `{` (backstop try/except). Sin
red, sin certificado y sin tocar la base SQLite.
"""

import pytest

from unittest.mock import Mock
from pyarcaws.padron import PadronAFIP

pytestmark = pytest.mark.dontusefix


def _padron_con_respuesta(body, status="404"):
    # __new__ evita __init__ (que abre SQLite en InstallDir/padron.db). Consultar
    # sólo necesita client + LanzarExcepciones; el decorador llama self.inicializar()
    # (que NO toca la DB) y setea Excepcion.
    p = PadronAFIP.__new__(PadronAFIP)
    p.LanzarExcepciones = False
    fake = Mock()
    fake.return_value = body
    fake.response = {"status": status}
    p.client = fake
    return p


def test_consultar_html_404_surge_motivo():
    p = _padron_con_respuesta("<html><h1>404 Not Found</h1></html>")
    assert p.Consultar("20267565393") is False
    assert "no-JSON" in p.Excepcion


def test_consultar_body_vacio():
    p = _padron_con_respuesta("")
    assert p.Consultar("20267565393") is False
    assert "no-JSON" in p.Excepcion


def test_consultar_json_truncado_no_propaga_jsondecode():
    # empieza con "{" pero está roto: NO debe surgir un JSONDecodeError opaco
    p = _padron_con_respuesta('{"success": true, "data": {"idPer')
    assert p.Consultar("20267565393") is False
    assert "no-JSON" in p.Excepcion
    assert "JSONDecodeError" not in (p.Excepcion or "")


def test_consultar_json_valido_ok():
    body = (
        '{"success": true, "data": {"idPersona": 20267565393, '
        '"tipoPersona": "FISICA", "tipoClave": "CUIT"}}'
    )
    p = _padron_con_respuesta(body, status="200")
    assert p.Consultar("20267565393") is True
