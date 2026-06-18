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

"""Tests unitarios offline de WSCPE (Carta de Porte Electrónica).

No usan red ni cassettes: ejercitan con un cliente SOAP falso la estructura
modelada del WSDL vivo (wscpe/services/soap). Cubren:

  - el **endpoint migrado**: ARCA movió WSCPE de `fwshomo`/`serviciosjava` a los
    hosts `cpea-ws*`; este test fija las URLs vigentes (homo `cpea-ws-qaext`,
    prod `cpea-ws`) para que una regresión de URL no pase inadvertida.
  - `Dummy` y la autenticación (auth con **`cuitRepresentada`**, no `cuit`).
  - los catálogos read-only `Consultar*` y `ConsultarUltNroOrden`.
  - el patrón builder Automotor: `CrearCPE` + `AgregarCabecera` arman el
    `solicitud` que recibe `AutorizarCPEAutomotor`, y el parseo de la cabecera.

Los tests de integración heredados (`test_wscpe.py`) dependen de la fixture
`auth` (cert WSAA, sólo con `--run-online`) y replayan los 33 cassettes viejos
grabados contra el host `fwshomo` (ver nota de endpoint en `wscpe.py`). Estos
tests, en cambio, corren con `dontusefix`: sin red ni certificado.
"""

import pytest

from pyarcaws.wscpe import WSCPE, WSDL

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


class _FakeClient:
    def __init__(self, respuestas=None):
        self._respuestas = respuestas or {}
        self.xml_request = self.xml_response = ""
        self.calls = []

    def __getattr__(self, name):
        def _op(**kwargs):
            self.calls.append((name, kwargs))
            return self._respuestas.get(name, {})

        return _op


def _nuevo(client):
    w = WSCPE()
    w.LanzarExcepciones = True
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = client
    return w


# --- endpoint migrado -------------------------------------------------------


def test_endpoint_homo_y_prod_migrados():
    """ARCA migró WSCPE a los hosts cpea-ws*; las URLs viejas dan 404."""
    prod, homo = WSDL[False], WSDL[True]
    assert homo == "https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap?wsdl"
    assert prod == "https://cpea-ws.afip.gob.ar/wscpe/services/soap?wsdl"
    # ninguna URL debe seguir apuntando a los hosts viejos (404)
    for url in (prod, homo):
        assert "fwshomo.afip.gov.ar" not in url
        assert "serviciosjava.afip.gob.ar" not in url


# --- dummy / autenticación --------------------------------------------------


def test_dummy():
    cliente = _FakeClient(
        {"dummy": {"respuesta": {"appserver": "OK", "dbserver": "OK", "authserver": "OK"}}}
    )
    w = _nuevo(cliente)
    w.Dummy()
    assert w.AppServerStatus == "OK"
    assert w.DbServerStatus == "OK"
    assert w.AuthServerStatus == "OK"


def test_auth_usa_cuit_representada():
    "WSCPE autentica con cuitRepresentada (no `cuit` a secas)."
    cliente = _FakeClient({"consultarProvincias": {"respuesta": {"provincia": []}}})
    w = _nuevo(cliente)
    w.ConsultarProvincias()
    op, kw = cliente.calls[0]
    assert op == "consultarProvincias"
    assert kw["auth"] == {"token": "TK", "sign": "SG", "cuitRepresentada": 20111111112}


# --- catálogos read-only ----------------------------------------------------


def test_consultar_provincias():
    cliente = _FakeClient({"consultarProvincias": {"respuesta": {"provincia": [
        {"codigo": "1", "descripcion": "BUENOS AIRES"},
        {"codigo": "2", "descripcion": "CATAMARCA"},
    ]}}})
    w = _nuevo(cliente)
    out = w.ConsultarProvincias(sep=None)
    assert out == [
        {"codigo": "1", "descripcion": "BUENOS AIRES"},
        {"codigo": "2", "descripcion": "CATAMARCA"},
    ]
    # con sep arma la línea formateada
    assert w.ConsultarProvincias() == ["|| 1 || BUENOS AIRES ||", "|| 2 || CATAMARCA ||"]


def test_consultar_tipos_grano():
    cliente = _FakeClient({"consultarTiposGrano": {"respuesta": {"grano": [
        {"codigo": "23", "descripcion": "SOJA"},
    ]}}})
    w = _nuevo(cliente)
    assert w.ConsultarTiposGrano() == ["|| 23 || SOJA ||"]


def test_consultar_localidades_envia_solicitud():
    cliente = _FakeClient({"consultarLocalidadesPorProvincia": {"respuesta": {"localidad": [
        {"codigo": "10", "descripcion": "LA PLATA"},
    ]}}})
    w = _nuevo(cliente)
    out = w.ConsultarLocalidadesPorProvincia(cod_provincia=1, sep=None)
    assert out == [{"codigo": "10", "descripcion": "LA PLATA"}]
    op, kw = cliente.calls[0]
    assert kw["solicitud"] == {"codProvincia": 1}


def test_consultar_ult_nro_orden():
    cliente = _FakeClient(
        {"consultarUltNroOrden": {"respuesta": {"nroOrden": 99}}}
    )
    w = _nuevo(cliente)
    assert w.ConsultarUltNroOrden(sucursal=221, tipo_cpe=74)
    assert w.NroOrden == 99
    op, kw = cliente.calls[0]
    assert kw["solicitud"] == {"sucursal": 221, "tipoCPE": 74}
    assert kw["auth"]["cuitRepresentada"] == 20111111112


# --- builder Automotor ------------------------------------------------------


def test_builder_autorizar_automotor(tmp_path):
    """CrearCPE + AgregarCabecera arman el `solicitud` de autorizarCPEAutomotor."""
    cliente = _FakeClient({"autorizarCPEAutomotor": {"respuesta": {
        "cabecera": {"nroCTG": 10100000001, "nroOrden": 1, "estado": "AC"},
    }}})
    w = _nuevo(cliente)
    w.CrearCPE()
    w.AgregarCabecera(tipo_cpe=74, cuit_solicitante=20111111112,
                      sucursal=1, nro_orden=1, planta=1)
    assert w.AutorizarCPEAutomotor(archivo=str(tmp_path / "cpe.pdf"))

    op, kw = cliente.calls[-1]
    assert op == "autorizarCPEAutomotor"
    sol = kw["solicitud"]
    assert sol["cabecera"]["tipoCP"] == 74
    assert sol["cabecera"]["cuitSolicitante"] == 20111111112
    assert sol["cabecera"]["sucursal"] == 1
    # respuesta parseada
    assert w.NroCTG == 10100000001
    assert w.Estado == "AC"
