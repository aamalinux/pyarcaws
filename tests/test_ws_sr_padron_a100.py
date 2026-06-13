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

"""Tests unitarios offline de WSSrPadronA100 (Consulta de Tablas de Parámetros).

No usan red ni cassettes: ejercitan Consultar/Dummy con un cliente SOAP falso y
la estructura modelada del WSDL parameterServiceA100 (parameterCollectionReturn
→ parameterCollection → parameterList → parameter). Se verifica la normalización
de las listas maxOccurs="unbounded" (parameterList/attributeList llegan como
dict cuando hay un único elemento) y que la auth llega al cliente.
"""

import pytest

from pyarcaws.ws_sr_padron import WSSrPadronA100
from pyarcaws.utils import SoapFault

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


def _coleccion(parameter_list):
    return {
        "parameterCollectionReturn": {
            "parameterCollection": {
                "name": "Provincias",
                "parameterList": parameter_list,
            }
        }
    }


class _FakeClient:
    def __init__(self, respuesta=None, exc=None):
        self._respuesta = respuesta
        self._exc = exc
        self.xml_request = ""
        self.xml_response = ""
        self.calls = []

    def getParameterCollectionByName(self, **kwargs):
        self.calls.append(("getParameterCollectionByName", kwargs))
        if self._exc:
            raise self._exc
        return self._respuesta

    def dummy(self):
        self.calls.append(("dummy", {}))
        return {
            "dummyReturn": {
                "appserver": "OK",
                "dbserver": "OK",
                "authserver": "OK",
            }
        }


def _nuevo(client, lanzar=True):
    w = WSSrPadronA100()
    w.LanzarExcepciones = lanzar
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = client
    return w


# --- Dummy -----------------------------------------------------------------


def test_dummy():
    w = _nuevo(_FakeClient())
    assert w.Dummy()
    assert w.AppServerStatus == "OK"
    assert w.DbServerStatus == "OK"
    assert w.AuthServerStatus == "OK"


# --- consulta exitosa ------------------------------------------------------


def test_consultar_varios_elementos_y_auth():
    lista = [
        {"id": "1", "description": "BUENOS AIRES",
         "attributeList": [{"k": "ar-b"}]},
        {"id": "2", "description": "CATAMARCA",
         "attributeList": [{"k": "ar-k"}, {"k": "extra"}]},
    ]
    w = _nuevo(_FakeClient(_coleccion(lista)))
    ok = w.Consultar("Provincias")
    assert ok
    # auth llegó al cliente con la terna + collectionName
    op, kw = w.client.calls[0]
    assert op == "getParameterCollectionByName"
    assert kw["token"] == "TK"
    assert kw["sign"] == "SG"
    assert kw["cuitRepresentada"] == 20111111112
    assert kw["collectionName"] == "Provincias"
    # estructura normalizada
    assert w.nombre == "Provincias"
    assert len(w.parametros) == 2
    assert w.parametros[0]["id"] == "1"
    assert w.parametros[0]["descripcion"] == "BUENOS AIRES"
    assert w.parametros[0]["atributos"] == [{"k": "ar-b"}]
    assert w.parametros[1]["atributos"] == [{"k": "ar-k"}, {"k": "extra"}]


def test_un_solo_elemento_como_dict_tolerado():
    # pysimplesoap entrega parameterList como dict cuando hay un único parameter
    uno = {"id": "1", "description": "BUENOS AIRES",
           "attributeList": {"k": "ar-b"}}
    w = _nuevo(_FakeClient(_coleccion(uno)))
    ok = w.Consultar("Provincias")
    assert ok
    assert len(w.parametros) == 1
    assert w.parametros[0]["id"] == "1"
    # attributeList único como dict también se normaliza a lista
    assert w.parametros[0]["atributos"] == [{"k": "ar-b"}]


def test_coleccion_vacia():
    w = _nuevo(_FakeClient(_coleccion([])))
    ok = w.Consultar("Provincias")
    assert ok
    assert w.parametros == []


def test_buscar_parametro():
    lista = [
        {"id": "1", "description": "BUENOS AIRES", "attributeList": []},
        {"id": "2", "description": "CATAMARCA", "attributeList": []},
    ]
    w = _nuevo(_FakeClient(_coleccion(lista)))
    w.Consultar("Provincias")
    assert w.BuscarParametro("2")["descripcion"] == "CATAMARCA"
    assert w.BuscarParametro(2)["descripcion"] == "CATAMARCA"  # tolerante a int
    assert w.BuscarParametro("99") is None


# --- colección inexistente / no autorizado (SOAP fault) --------------------


def test_coleccion_inexistente_soap_fault_no_rompe():
    """A100 no define bloque de error de negocio en el WSDL: una colección
    inexistente / servicio no autorizado llega como SOAP fault, capturado por el
    decorador en Excepcion/ErrMsg sin propagar (LanzarExcepciones=False)."""
    w = _nuevo(
        _FakeClient(exc=SoapFault("coe.notAuthorized", "Coleccion inexistente")),
        lanzar=False,
    )
    ok = w.Consultar("NoExiste")
    assert ok is None  # degradó sin excepción
    assert w.ErrCode == "coe.notAuthorized"
    assert "inexistente" in w.ErrMsg
