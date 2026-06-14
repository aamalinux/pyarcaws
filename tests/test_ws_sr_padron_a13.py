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

"""Tests unitarios offline de WSSrPadronA13 (Consulta a Padrón Alcance 13).

No usan red ni cassettes: ejercitan con un cliente SOAP falso la estructura
modelada del WSDL vivo personaServiceA13. A13 comparte ``getPersona`` con A10
(parseo heredado) y agrega la búsqueda inversa ``getIdPersonaListByDocumento``
(documento → lista de idPersona), que es lo distintivo de este alcance.
"""

import pytest

from pyarcaws.ws_sr_padron import WSSrPadronA13, PadronA13
from pyarcaws.utils import SoapFault

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


def _persona(domicilio=None):
    p = {
        "idPersona": 20267565393,
        "tipoPersona": "FISICA",
        "tipoClave": "CUIT",
        "numeroDocumento": "26756539",
        "estadoClave": "ACTIVO",
        "apellido": "PEREZ",
        "nombre": "JUAN",
        "idActividadPrincipal": 620100,
        "descripcionActividadPrincipal": "SERVICIOS DE INFORMATICA",
    }
    if domicilio is not None:
        p["domicilio"] = domicilio
    return {"personaReturn": {"metadata": {"servidor": "test"}, "persona": p}}


class _FakeClient:
    def __init__(self, persona=None, id_lista=None, exc=None):
        self._persona = persona
        self._id_lista = id_lista
        self._exc = exc
        self.xml_request = self.xml_response = ""
        self.calls = []

    def getPersona(self, **kwargs):
        self.calls.append(("getPersona", kwargs))
        if self._exc:
            raise self._exc
        return self._persona

    def getIdPersonaListByDocumento(self, **kwargs):
        self.calls.append(("getIdPersonaListByDocumento", kwargs))
        if self._exc:
            raise self._exc
        return self._id_lista

    def dummy(self):
        return {"return": {"appserver": "OK", "dbserver": "OK", "authserver": "OK"}}


def _nuevo(client):
    w = WSSrPadronA13()
    w.LanzarExcepciones = True
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = client
    return w


def test_alias_y_wsdl():
    assert PadronA13 is WSSrPadronA13
    w = WSSrPadronA13()
    assert "personaServiceA13" in w.WSDL


def test_getpersona_heredado_de_a10():
    "getPersona usa el mismo parseo que A10 (denominación, doc, estado)."
    w = _nuevo(_FakeClient(persona=_persona()))
    assert w.Consultar(20267565393)
    assert w.client.calls[0][0] == "getPersona"
    assert w.denominacion == "PEREZ, JUAN"
    assert w.estado == "ACTIVO"
    assert w.nro_doc == "26756539"


# --- búsqueda inversa por documento: lo distintivo de A13 -------------------


def test_lista_por_documento_varios():
    "getIdPersonaListByDocumento con varios idPersona (lista)."
    cliente = _FakeClient(
        id_lista={"idPersonaListReturn": {
            "idPersona": [20267565393, 27267565398],
            "metadata": {"servidor": "test"},
        }}
    )
    w = _nuevo(cliente)
    ok = w.ConsultarListaPersonaPorDocumento("26756539")
    assert ok
    # auth + documento llegaron al cliente
    op, kw = cliente.calls[0]
    assert op == "getIdPersonaListByDocumento"
    assert kw["token"] == "TK" and kw["sign"] == "SG"
    assert kw["cuitRepresentada"] == 20111111112
    assert kw["documento"] == "26756539"
    assert w.personas == [20267565393, 27267565398]


def test_lista_por_documento_unico_como_dict():
    "Un único idPersona puede llegar como escalar (no lista): tolerar."
    w = _nuevo(_FakeClient(
        id_lista={"idPersonaListReturn": {"idPersona": 20267565393}}
    ))
    w.ConsultarListaPersonaPorDocumento("26756539")
    assert w.personas == [20267565393]


def test_lista_por_documento_vacia():
    "Documento sin personas asociadas: lista vacía, sin error."
    w = _nuevo(_FakeClient(id_lista={"idPersonaListReturn": {"metadata": {}}}))
    w.ConsultarListaPersonaPorDocumento("00000000")
    assert w.personas == []


def test_documento_inexistente_soap_fault():
    "Documento inexistente / no autorizado llega como SOAP fault."
    w = _nuevo(_FakeClient(exc=SoapFault("Server", "No existe persona")))
    w.LanzarExcepciones = False
    ok = w.ConsultarListaPersonaPorDocumento("99999999")
    assert not ok
    assert w.personas == []
