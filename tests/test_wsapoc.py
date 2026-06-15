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

"""Tests unitarios offline de WSAPOC (consulta de apócrifos, base APOC).

No usan red ni cassettes: ejercitan con un cliente SOAP falso la estructura
modelada del WSDL vivo (eapoc-ws-qaext.afip.gob.ar/Service.asmx, esquema
qualified). Cubren: Dummy, consulta de un CUIT (apócrifo vs no apócrifo),
normalización de resultados single-vs-lista y la autenticación por
`Credencial` con `CUITDelegado` (no `cuit`/`cuitRepresentada`).
"""

import pytest

from pyarcaws.wsapoc import WSAPOC, Apocrifos

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


def _msg(codigo="0", descripcion="OK", publicaciones=None):
    "Arma un MessageResponse con la lista de PublicacionAPOC."
    resultados = {}
    if publicaciones is not None:
        resultados = {"PublicacionAPOC": publicaciones}
    return {"codigo": codigo, "descripcion": descripcion, "resultados": resultados}


def _pub(cuit=20111111112):
    return {
        "Cuit": cuit,
        "Descripcion": "FACTURAS APOCRIFAS",
        "FechaCondicion": "2025-01-01",
        "FechaPublicacion": "2025-02-01",
    }


class _FakeClient:
    def __init__(self, respuestas=None, exc=None):
        self._respuestas = respuestas or {}
        self._exc = exc
        self.xml_request = self.xml_response = ""
        self.calls = []

    def __getattr__(self, name):
        def _op(**kwargs):
            self.calls.append((name, kwargs))
            if self._exc:
                raise self._exc
            return self._respuestas.get(name, {})
        return _op


def _nuevo(client):
    w = WSAPOC()
    w.LanzarExcepciones = True
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = client
    return w


def test_alias():
    assert Apocrifos is WSAPOC


def test_auth_usa_cuit_delegado():
    "Diferencia clave: WSAPOC autentica con Credencial{Token,Sign,CUITDelegado}."
    w = _nuevo(_FakeClient())
    assert w._cred == {"Token": "TK", "Sign": "SG", "CUITDelegado": 20111111112}


def test_dummy():
    cliente = _FakeClient({"Dummy": {"DummyResult": {
        "appserver": "OK", "dbserver": "OK", "authserver": "OK"}}})
    w = _nuevo(cliente)
    assert w.Dummy()
    assert w.AppServerStatus == "OK"
    assert w.DbServerStatus == "OK"
    assert w.AuthServerStatus == "OK"


def test_consultar_cuit_apocrifo():
    cliente = _FakeClient({"GetPublicacionAPOC": {
        "GetPublicacionAPOCResult": _msg(publicaciones=[_pub(20111111112)])
    }})
    w = _nuevo(cliente)
    assert w.Consultar(20111111112)
    # auth (Credencial) + cuit llegaron al cliente
    op, kw = cliente.calls[0]
    assert op == "GetPublicacionAPOC"
    assert kw["Credencial"]["CUITDelegado"] == 20111111112
    assert kw["cuit"] == 20111111112
    # resultado: es apócrifo
    assert w.EsApocrifo is True
    assert len(w.resultados) == 1
    assert w.resultados[0]["cuit"] == 20111111112
    assert w.resultados[0]["fecha_publicacion"] == "2025-02-01"


def test_consultar_cuit_no_apocrifo():
    "Sin resultados → no apócrifo (resultados vacíos, sin error)."
    cliente = _FakeClient({"GetPublicacionAPOC": {
        "GetPublicacionAPOCResult": _msg(publicaciones=None)
    }})
    w = _nuevo(cliente)
    w.Consultar(20999999990)
    assert w.EsApocrifo is False
    assert w.resultados == []
    assert w.CodigoRespuesta == "0"


def test_resultado_unico_como_dict_tolerado():
    "Un único PublicacionAPOC llega como dict (no lista): como_lista lo aplana."
    cliente = _FakeClient({"GetPublicacionAPOC": {
        "GetPublicacionAPOCResult": _msg(publicaciones=_pub(30111111118))
    }})
    w = _nuevo(cliente)
    w.Consultar(30111111118)
    assert w.EsApocrifo is True
    assert len(w.resultados) == 1
    assert w.resultados[0]["cuit"] == 30111111118


def test_consultar_por_publicacion():
    cliente = _FakeClient({"GetAllByPublicacion": {
        "GetAllByPublicacionResult": _msg(publicaciones=[_pub(20111111112), _pub(30111111118)])
    }})
    w = _nuevo(cliente)
    assert w.ConsultarPorPublicacion("2025-01-01", "2025-12-31")
    op, kw = cliente.calls[0]
    assert op == "GetAllByPublicacion"
    assert kw["desde"] == "2025-01-01" and kw["hasta"] == "2025-12-31"
    assert len(w.resultados) == 2
