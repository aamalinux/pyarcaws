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

"""Tests offline del marshalling SOAP de WSLSP (sin red).

Genera el envelope real con el pysimplesoap vendoreado a partir de los WSDL
fixtures (descargados de homologación) e inspecciona el XML producido, sin
enviar nada a ARCA. Cubre los bugs hallados contra el servicio vivo:

  - Bug 1: ``cuitComprador`` ya no viaja en la solicitud.
  - Bug 3: ``pdf`` ya no viaja en la solicitud (es sólo nombre de archivo local).
  - Bug 4: los elementos hoja NO se califican con namespace cuando el schema es
    ``elementFormDefault="unqualified"`` (WSLSP); y SÍ se siguen calificando
    cuando es ``qualified`` (WSCDC) — prueba de no-regresión.
"""

import os
import pytest

from pyarcaws.wslsp import WSLSP
from pyarcaws.wscdc import WSCDC

pytestmark = pytest.mark.dontusefix

WSDL_DIR = os.path.join(os.path.dirname(__file__), "wsdl")
WSLSP_WSDL = os.path.join(WSDL_DIR, "wslsp_homo.wsdl")
WSCDC_WSDL = os.path.join(WSDL_DIR, "wscdc_homo.wsdl")
WSLSP_NS = "http://serviciosjava.afip.gob.ar/wslsp/"


def _capturar_envelope(ws, wsdl, invoke):
    """Conecta desde un WSDL local, intercepta el envío y devuelve el envelope
    que pysimplesoap habría mandado (str), sin tocar la red."""
    try:
        ws.Conectar(cache="", wsdl=wsdl)
    except TypeError:
        ws.Conectar("", wsdl)  # WSLSP.Conectar usa 'url' posicional

    def fake_send(method, xml, *a, **k):
        fake_send.captured = xml
        raise RuntimeError("__STOP__")

    ws.client.send = fake_send
    ws.Token, ws.Sign, ws.Cuit = "TK", "SG", "20111111112"
    try:
        invoke(ws)
    except RuntimeError as e:
        if "__STOP__" not in str(e):
            raise
    env = fake_send.captured
    return env.decode() if isinstance(env, (bytes, bytearray)) else env


def test_wslsp_solicitud_limpia_y_sin_namespace_en_hojas():
    """WSLSP (schema unqualified): la solicitud lleva sólo puntoVenta/
    tipoComprobante/nroComprobante, sin cuitComprador ni pdf, y los elementos
    hoja van SIN xmlns (calificación que el schema vivo rechaza)."""
    w = WSLSP()
    w.LanzarExcepciones = True
    env = _capturar_envelope(
        w, WSLSP_WSDL,
        lambda ws: ws.ConsultarLiquidacion(tipo_cbte=190, pto_vta=3, nro_cbte=16),
    )
    # bug 1 y 3: nada de cuitComprador / pdf en la solicitud
    assert "cuitComprador" not in env
    assert "<pdf" not in env and "pdf>" not in env
    # bug 4: ningún elemento hoja calificado con el namespace de wslsp
    assert ('xmlns="%s"' % WSLSP_NS) not in env
    # la solicitud tiene exactamente los 3 campos del esquema, sin namespace
    assert "<puntoVenta>3</puntoVenta>" in env
    assert "<tipoComprobante>190</tipoComprobante>" in env
    assert "<nroComprobante>16</nroComprobante>" in env
    # auth también sin calificar las hojas
    assert "<token>TK</token>" in env


def test_wslsp_cuit_comprador_emite_userwarning():
    w = WSLSP()
    w.LanzarExcepciones = True
    with pytest.warns(UserWarning, match="emisor"):
        _capturar_envelope(
            w, WSLSP_WSDL,
            lambda ws: ws.ConsultarLiquidacion(
                tipo_cbte=190, pto_vta=3, nro_cbte=16, cuit_comprador="30690720023"
            ),
        )


def test_wscdc_qualified_sigue_calificando_hojas():
    """No-regresión bug 4: WSCDC tiene elementFormDefault="qualified"; sus
    elementos deben seguir calificados con xmlns (el fix sólo toca unqualified)."""
    w = WSCDC()
    w.LanzarExcepciones = True
    env = _capturar_envelope(
        w, WSCDC_WSDL,
        lambda ws: ws.client.ComprobanteConstatar(
            Auth={"Token": "TK", "Sign": "SG", "Cuit": "20111111112"},
            CmpReq={
                "CbteModo": "CAE", "CuitEmisor": "30690720023", "PtoVta": 3,
                "CbteTipo": 190, "CbteNro": 16, "CbteFch": "20260527",
                "ImpTotal": 100.0, "CodAutorizacion": "86217130787511",
            },
        ),
    )
    wscdc_ns = "http://servicios1.afip.gob.ar/wscdc/"
    # los elementos SIGUEN calificados (comportamiento correcto para qualified)
    assert ('<Token xmlns="%s">TK</Token>' % wscdc_ns) in env
    assert ('<CbteTipo xmlns="%s">190</CbteTipo>' % wscdc_ns) in env
