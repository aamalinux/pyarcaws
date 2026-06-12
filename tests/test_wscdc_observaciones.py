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

"""Tests offline de WSCDC: parseo tolerante de <Observaciones> (sin red).

Bug real de producción (DeckPagos): cuando ConstatarComprobante devuelve
Resultado='R' con UNA sola <Obs>, pysimplesoap entrega <Observaciones> como
dict (no lista) y el parseo lanzaba el mismo TypeError histórico de <Errors>.
Casos reales: Obs 100 (CAE inexistente) y Obs 110 (importe alterado).
"""

import pytest

from pyarcaws.wscdc import WSCDC

pytestmark = pytest.mark.dontusefix


def _cmp_resp():
    return {
        "CbteFch": "20260527",
        "CbteNro": 16,
        "PtoVta": 3,
        "ImpTotal": 80735921.11,
        "CbteModo": "CAE",
        "CodAutorizacion": "86217130787511",
        "DocTipoReceptor": 80,
        "DocNroReceptor": 20111111112,
    }


OBS_100 = {"Code": 100, "Msg": "El N° de CAI/CAE/CAEA consultado no existe en "
           "las bases del organismo."}
OBS_110 = {"Code": 110, "Msg": "El importe total no se corresponde con el "
           "comprobante consultado."}


class _FakeClient:
    def __init__(self, result):
        self._result = result
        self.xml_request = ""
        self.xml_response = ""

    def ComprobanteConstatar(self, **kwargs):
        return {"ComprobanteConstatarResult": self._result}


def _constatar(result):
    w = WSCDC()
    w.LanzarExcepciones = True
    w.Token = w.Sign = "x"
    w.Cuit = "20111111112"
    w.client = _FakeClient(result)
    ok = w.ConstatarComprobante(
        cbte_modo="CAE", cuit_emisor="30690720023", pto_vta=3, cbte_tipo=190,
        cbte_nro=16, cbte_fch="20260527", imp_total=80735921.11,
        cod_autorizacion="86217130787511",
    )
    return w, ok


def test_resultado_r_una_obs_100_no_explota():
    """Una sola Obs (dict): no debe lanzar TypeError; puebla Obs/Observaciones."""
    w, ok = _constatar({
        "Resultado": "R", "FchProceso": "20260611",
        "Observaciones": {"Obs": OBS_100},
        "CmpResp": _cmp_resp(),
    })
    assert ok
    assert w.Resultado == "R"
    assert w.Observaciones == ["100: El N° de CAI/CAE/CAEA consultado no existe "
                               "en las bases del organismo."]
    assert "100" in w.Obs
    assert w.observaciones == [{"code": 100, "msg": OBS_100["Msg"]}]


def test_resultado_r_una_obs_110():
    w, ok = _constatar({
        "Resultado": "R", "FchProceso": "20260611",
        "Observaciones": {"Obs": OBS_110},
        "CmpResp": _cmp_resp(),
    })
    assert ok
    assert w.observaciones == [{"code": 110, "msg": OBS_110["Msg"]}]
    assert "110" in w.Obs


def test_resultado_r_varias_obs_lista():
    w, ok = _constatar({
        "Resultado": "R", "FchProceso": "20260611",
        "Observaciones": {"Obs": [OBS_100, OBS_110]},
        "CmpResp": _cmp_resp(),
    })
    assert ok
    assert [o["code"] for o in w.observaciones] == [100, 110]
    assert w.Observaciones[0].startswith("100:")
    assert w.Observaciones[1].startswith("110:")


def test_resultado_a_sin_observaciones():
    w, ok = _constatar({
        "Resultado": "A", "FchProceso": "20260611",
        "CmpResp": _cmp_resp(),
    })
    assert ok
    assert w.Resultado == "A"
    assert w.Observaciones == []
    assert w.Obs == ""
