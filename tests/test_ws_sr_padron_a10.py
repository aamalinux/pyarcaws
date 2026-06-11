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

"""Tests unitarios offline de WSSrPadronA10 (Consulta a Padrón Alcance 10).

No usan red ni cassettes: ejercitan Consultar con un cliente SOAP falso y la
estructura modelada del WSDL vivo personaServiceA10 (personaReturn → persona,
estructura liviana). El WSDL no define bloques de error de negocio: la persona
inexistente / servicio no autorizado llega como SOAP fault.
"""

import pytest

from pyarcaws.ws_sr_padron import WSSrPadronA10
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


DOMICILIO_FISCAL = {
    "tipoDomicilio": "FISCAL",
    "direccion": "AV CORRIENTES 1234",
    "localidad": "CABA",
    "idProvincia": 0,
    "codPostal": "1043",
}


class _FakeClient:
    def __init__(self, respuesta=None, exc=None):
        self._respuesta = respuesta
        self._exc = exc
        self.xml_request = ""
        self.xml_response = ""
        self.calls = []

    def getPersona(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc:
            raise self._exc
        return self._respuesta


def _nuevo(client):
    w = WSSrPadronA10()
    w.LanzarExcepciones = True
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = client
    return w


# --- consulta exitosa ------------------------------------------------------


def test_consultar_persona_completa_y_auth():
    w = _nuevo(_FakeClient(_persona(domicilio=[DOMICILIO_FISCAL])))
    ok = w.Consultar(20267565393)
    assert ok
    # auth llegó al cliente
    kw = w.client.calls[0]
    assert kw["token"] == "TK"
    assert kw["sign"] == "SG"
    assert kw["cuitRepresentada"] == 20111111112
    assert kw["idPersona"] == 20267565393
    # campos mínimos poblados
    assert w.cuit == 20267565393
    assert w.tipo_persona == "FISICA"
    assert w.nro_doc == "26756539"
    assert w.estado == "ACTIVO"
    assert w.denominacion == "PEREZ, JUAN"
    assert w.direccion == "AV CORRIENTES 1234"
    assert w.localidad == "CABA"
    assert w.cod_postal == "1043"
    # actividad principal (A10 sólo expone la principal)
    assert w.actividades == [620100]
    assert w.actividad_principal == "SERVICIOS DE INFORMATICA"
    # A10 no trae impuestos ni caracterizaciones
    assert w.impuestos == []
    assert w.caracterizaciones == []


def test_razon_social_para_persona_juridica():
    resp = _persona(domicilio=[DOMICILIO_FISCAL])
    p = resp["personaReturn"]["persona"]
    p.pop("apellido"); p.pop("nombre")
    p["tipoPersona"] = "JURIDICA"
    p["razonSocial"] = "ACME SA"
    w = _nuevo(_FakeClient(resp))
    w.Consultar(20267565393)
    assert w.denominacion == "ACME SA"


def test_domicilio_unico_como_dict_tolerado():
    # pysimplesoap puede entregar un único domicilio como dict (no lista)
    w = _nuevo(_FakeClient(_persona(domicilio=DOMICILIO_FISCAL)))
    w.Consultar(20267565393)
    assert w.direccion == "AV CORRIENTES 1234"
    assert len(w.domicilios) == 1


def test_sin_domicilio():
    w = _nuevo(_FakeClient(_persona(domicilio=None)))
    w.Consultar(20267565393)
    assert w.domicilios == []
    assert w.direccion == ""


# --- persona inexistente / no autorizado (SOAP fault) ----------------------


def test_persona_inexistente_soap_fault_no_rompe():
    """A10 no define bloque de error de negocio en el WSDL: la persona
    inexistente / servicio no autorizado llega como SOAP fault, capturado por
    el decorador en Excepcion/ErrMsg sin propagar (LanzarExcepciones=False)."""
    w = WSSrPadronA10()
    w.LanzarExcepciones = False
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = _FakeClient(
        exc=SoapFault("coe.notAuthorized", "No existe la persona consultada")
    )
    ok = w.Consultar(20267565393)
    assert ok is None  # degradó sin excepción
    assert w.ErrCode == "coe.notAuthorized"
    assert "persona" in w.ErrMsg
