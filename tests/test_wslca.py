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

"""Tests unitarios offline de WSLCA (Liquidación de Caña de Azúcar).

No usan red ni cassettes: ejercitan con un cliente SOAP falso la estructura
modelada del WSDL vivo (wslca/services/soap). Cubren: Dummy, catálogos
código/descripción (single vs lista), normalización tolerante de <errores>
(uno vs varios), la autenticación (cuitRepresentada, no cuit) y la consulta por
nro de comprobante.

Nota: el esquema WSLCA es ``unqualified`` (sin elementFormDefault); el fix de
marshalling vive en el pysimplesoap vendoreado y está cubierto por
``test_wslsp_marshalling.py`` (mismo código compartido), por eso no se duplica
acá un fixture de WSDL de 65 KB.
"""

import pytest

from pyarcaws.wslca import WSLCA, LiquidacionCanaAzucar

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


def _resp(**kwargs):
    return {"respuesta": kwargs}


class _FakeClient:
    def __init__(self, respuestas=None, exc=None):
        self._respuestas = respuestas or {}
        self._exc = exc
        self.xml_request = self.xml_response = ""
        self.calls = []

    def __getattr__(self, name):
        # cualquier operación SOAP devuelve la respuesta preconfigurada
        def _op(**kwargs):
            self.calls.append((name, kwargs))
            if self._exc:
                raise self._exc
            return self._respuestas.get(name, {"respuesta": {}})
        return _op


def _nuevo(client):
    w = WSLCA()
    w.LanzarExcepciones = True
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = client
    return w


def test_alias():
    assert LiquidacionCanaAzucar is WSLCA


def test_auth_usa_cuit_representada():
    "Diferencia clave vs WSLSP: el Auth de WSLCA usa cuitRepresentada."
    w = _nuevo(_FakeClient())
    assert w._auth == {"token": "TK", "sign": "SG", "cuitRepresentada": 20111111112}


def test_dummy():
    cliente = _FakeClient({"dummy": _resp(appserver="OK", dbserver="OK", authserver="OK")})
    w = _nuevo(cliente)
    assert w.Dummy()
    assert w.AppServerStatus == "OK"
    assert w.DbServerStatus == "OK"
    assert w.AuthServerStatus == "OK"


# --- catálogos: single vs lista --------------------------------------------


def test_provincias_lista():
    cliente = _FakeClient({"consultarProvincias": _resp(provincia=[
        {"codigo": "1", "descripcion": "BUENOS AIRES"},
        {"codigo": "22", "descripcion": "TUCUMAN"},
    ])})
    w = _nuevo(cliente)
    out = w.ConsultarProvincias(sep=None)
    assert out == {"1": "BUENOS AIRES", "22": "TUCUMAN"}
    # auth llegó
    op, kw = cliente.calls[0]
    assert op == "consultarProvincias"
    assert kw["auth"]["cuitRepresentada"] == 20111111112


def test_provincia_unica_como_dict_tolerada():
    "pysimplesoap entrega un único elemento como dict (no lista): como_lista lo aplana."
    cliente = _FakeClient({"consultarProvincias": _resp(
        provincia={"codigo": "22", "descripcion": "TUCUMAN"}
    )})
    w = _nuevo(cliente)
    out = w.ConsultarProvincias(sep=None)
    assert out == {"22": "TUCUMAN"}


def test_localidades_envia_solicitud():
    cliente = _FakeClient({"consultarLocalidadesPorProvincia": _resp(
        localidad={"codigo": "1", "descripcion": "SAN MIGUEL DE TUCUMAN"}
    )})
    w = _nuevo(cliente)
    out = w.ConsultarLocalidades(22, sep=None)
    assert out == {"1": "SAN MIGUEL DE TUCUMAN"}
    op, kw = cliente.calls[0]
    assert kw["solicitud"] == {"codProvincia": 22}


def test_tributos_formato_sep():
    cliente = _FakeClient({"consultarTributos": _resp(
        tributo=[{"codigo": "01", "descripcion": "IVA"}]
    )})
    w = _nuevo(cliente)
    out = w.ConsultarTributos()
    assert out == ["|| 01 || IVA ||"]


# --- errores tolerantes (uno vs varios) ------------------------------------


def test_errores_uno_solo_no_rompe():
    "Un único <error> llega como dict; normalizar_lista_soap lo aplana."
    cliente = _FakeClient({"consultarProvincias": _resp(
        errores={"error": {"codigo": "100", "descripcion": "Sin autorización"}}
    )})
    w = _nuevo(cliente)
    w.ConsultarProvincias()
    assert w.errores == [{"codigo": "100", "descripcion": "Sin autorización"}]
    assert "100" in w.ErrCode


def test_errores_varios():
    cliente = _FakeClient({"consultarProvincias": _resp(errores={"error": [
        {"codigo": "1", "descripcion": "err uno"},
        {"codigo": "2", "descripcion": "err dos"},
    ]})})
    w = _nuevo(cliente)
    w.ConsultarProvincias()
    assert [e["codigo"] for e in w.errores] == ["1", "2"]


# --- consultas --------------------------------------------------------------


def test_consultar_ultimo_comprobante():
    cliente = _FakeClient({"consultarUltimoNroComprobantePorPtoVta": _resp(
        nroComprobante=42
    )})
    w = _nuevo(cliente)
    assert w.ConsultarUltimoComprobante(1, 60) == 42
    op, kw = cliente.calls[0]
    assert kw["solicitud"] == {"puntoVenta": 1, "tipoComprobante": 60}


def test_consultar_liquidacion_extrae_cae():
    cliente = _FakeClient({"consultarLiquidacionPorNroComprobante": _resp(
        cabecera={"comprobante": {"nroComprobante": 42}},
        autorizacion={"cae": 75123456789012, "fechaVencimientoCae": "2026-07-01"},
    )})
    w = _nuevo(cliente)
    assert w.ConsultarLiquidacion(1, 60, 42)
    assert w.CAE == "75123456789012"
    assert w.NroComprobante == 42
    assert w.FechaVencimientoCae == "2026-07-01"


# --- builder de generación (estructura del request) ------------------------


def test_crear_y_autorizar_arma_solicitud():
    "CrearLiquidacion + AgregarDetalle arman el 'solicitud' que se envía."
    cliente = _FakeClient({"generarLiquidacion": _resp(
        cabecera={"comprobante": {"nroComprobante": 7}},
        autorizacion={"cae": 75000000000001},
    )})
    w = _nuevo(cliente)
    w.CrearLiquidacion(
        punto_venta=1, tipo_comprobante=60, nro_comprobante=7,
        fecha_comprobante="2026-06-14", cod_condicion_venta=1, cod_medio_pago=1,
    )
    w.AgregarDetalle(cod_producto=1, cantidad=100, unidad_medida=1, precio_unitario=50.0)
    assert w.AutorizarLiquidacion()
    op, kw = cliente.calls[0]
    assert op == "generarLiquidacion"
    sol = kw["solicitud"]
    assert sol["emisor"]["comprobante"]["nroComprobante"] == 7
    assert sol["datosGenerales"]["fechaComprobante"] == "2026-06-14"
    assert len(sol["detalle"]) == 1
    assert sol["detalle"][0]["producto"] == 1
    assert w.CAE == "75000000000001"
