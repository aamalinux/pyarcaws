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

"""Tests offline de WSFEv1: parseo tolerante de nodos repetibles (sin red).

Mismo bug de single-item-como-dict que <Errors>: <Observaciones>/<Obs>,
<Iva>/<AlicIva>, <Tributos>/<Tributo>, etc. Se verifica vía CompConsultar
(consulta read-only) con un cliente SOAP falso, incluyendo el caso combinado
observaciones + eventos + errores en la misma respuesta.
"""

import pytest

from pyarcaws.wsfev1 import WSFEv1

pytestmark = pytest.mark.dontusefix


def _resultget(observaciones=None, iva=None, tributos=None):
    rg = {
        "CbteFch": "20260527", "CbteDesde": 16, "CbteHasta": 16, "PtoVta": 3,
        "FchVto": "20260606", "ImpTotal": 121.0, "ImpNeto": 100.0, "ImpIVA": 21.0,
        "ImpOpEx": 0.0, "ImpTrib": 0.0, "CodAutorizacion": "86217130787511",
        "Resultado": "A", "EmisionTipo": "CAE",
    }
    if observaciones is not None:
        rg["Observaciones"] = observaciones
    if iva is not None:
        rg["Iva"] = iva
    if tributos is not None:
        rg["Tributos"] = tributos
    return rg


class _FakeClient:
    def __init__(self, result):
        self._result = result
        self.xml_request = ""
        self.xml_response = ""

    def FECompConsultar(self, **kwargs):
        return {"FECompConsultarResult": self._result}


def _consultar(result):
    w = WSFEv1()
    w.LanzarExcepciones = True
    w.Token = w.Sign = "x"
    w.Cuit = "20111111112"
    w.client = _FakeClient(result)
    ok = w.CompConsultar(tipo_cbte=1, punto_vta=3, cbte_nro=16)
    return w, ok


def test_comp_consultar_nodos_unicos_como_dict_no_explota():
    """Iva/Tributo/Obs como dict único (no lista): no debe lanzar TypeError;
    se aplanan correctamente en la estructura interna."""
    rg = _resultget(
        observaciones={"Obs": {"Code": 110, "Msg": "El importe total no se "
                               "corresponde."}},
        iva={"AlicIva": {"Id": 5, "BaseImp": 100.0, "Importe": 21.0}},
        tributos={"Tributo": {"Id": 1, "Desc": "IIBB", "Importe": 10.0}},
    )
    w, ok = _consultar({"ResultGet": rg})
    assert ok
    assert w.factura["iva"] == [{"iva_id": 5, "base_imp": 100.0, "importe": 21.0}]
    assert w.factura["tributos"][0]["tributo_id"] == 1
    assert w.factura["obs"] == [{"code": 110, "msg": "El importe total no se "
                                 "corresponde."}]
    assert w.Observaciones == ["110: El importe total no se corresponde."]


def test_comp_consultar_obs_multiples_lista():
    rg = _resultget(observaciones={"Obs": [
        {"Code": 100, "Msg": "obs A"}, {"Code": 110, "Msg": "obs B"},
    ]})
    w, ok = _consultar({"ResultGet": rg})
    assert ok
    assert w.Observaciones == ["100: obs A", "110: obs B"]


def test_comp_consultar_sin_observaciones():
    w, ok = _consultar({"ResultGet": _resultget()})
    assert ok
    assert w.Observaciones == []
    assert w.Obs == ""


def test_comp_consultar_combinado_obs_eventos_errores():
    """Observaciones + Events + Errors (todos como dict único) en la misma
    respuesta: ninguno debe explotar."""
    rg = _resultget(observaciones={"Obs": {"Code": 110, "Msg": "obs unica"}})
    result = {
        "ResultGet": rg,
        "Errors": {"Err": {"Code": 600, "Msg": "error unico"}},
        "Events": {"Evt": {"Code": 1, "Msg": "evento unico"}},
    }
    w, ok = _consultar(result)
    assert ok
    assert w.Observaciones == ["110: obs unica"]
    assert w.Errores == ["600: error unico"]
    assert w.Eventos == ["1: evento unico"]
