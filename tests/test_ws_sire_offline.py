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

"""Tests unitarios offline de WSSIREc2005 (SIRE — certificado de retención C2005).

SIRE (Sistema Integral de Retenciones Electrónicas, RG 4523/19): el agente de
retención de IVA emite el certificado C2005. El servicio vive en el dominio RECA
(`ws-aplicativos-reca.homo.afip.gob.ar`, distinto del `fwshomo` clásico) y usa
`soap_server="oracle"`.

No usan red ni cassettes: ejercitan con un cliente SOAP falso la estructura
modelada del WSDL/XSD vivo (`sire/c2005`, esquema `unqualified`). Cubren:

  - import / versión.
  - `Dummy` (estado de servidores; sin autenticación).
  - el marshalling de `Emitir`: el envelope viaja con **`cuitAgente`** (no `cuit`
    ni `cuitRepresentada`) y el dict `certificado` con los campos del XSD, y la
    respuesta puebla `CertificadoNro` + `CodigoSeguridad`.
  - la rama de anulación (`motivoAnulacion` / `numeroCertificadoOriginal` /
    `importeCertificadoOriginal`), que el módulo modela como campos del mismo
    `certificado` de `emitir`.

Marca ``dontusefix``: corren sin certificado ni red.
"""

import pytest

from pyarcaws.ws_sire import WSSIREc2005

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
    w = WSSIREc2005()
    w.LanzarExcepciones = True
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = client
    return w


def test_import_y_version():
    w = WSSIREc2005()
    assert w.Version  # versión presente (string no vacío)


def test_dummy():
    cliente = _FakeClient(
        {"dummy": {"appserver": "OK", "dbserver": "OK", "authserver": "OK"}}
    )
    w = _nuevo(cliente)
    assert w.Dummy()
    assert w.AppServerStatus == "OK"
    assert w.DbServerStatus == "OK"
    assert w.AuthServerStatus == "OK"


def test_emitir_usa_cuit_agente():
    "El envelope de emitir lleva cuitAgente (no cuit/cuitRepresentada)."
    cliente = _FakeClient(
        {"emitir": {"certificadoNro": "C123", "codigoSeguridad": "S456"}}
    )
    w = _nuevo(cliente)
    assert w.Emitir(impuesto=216, regimen=831, importe_retencion=100.0,
                    importe_base_calculo=1000.0, cuit_retenido="30500010912")
    op, kw = cliente.calls[0]
    assert op == "emitir"
    # auth: token/sign sueltos + cuitAgente (no anidados, no 'cuit')
    assert kw["token"] == "TK"
    assert kw["sign"] == "SG"
    assert kw["cuitAgente"] == 20111111112
    assert "cuit" not in kw and "cuitRepresentada" not in kw


def test_emitir_arma_certificado_y_parsea_respuesta():
    cliente = _FakeClient(
        {"emitir": {"certificadoNro": "0001-00000042", "codigoSeguridad": "ABC123"}}
    )
    w = _nuevo(cliente)
    assert w.Emitir(
        impuesto=216,
        regimen=831,
        fecha_retencion="2026-06-18T11:22:00.000-03:00",
        importe_retencion=210.0,
        importe_base_calculo=1000.0,
        tipo_comprobante=1,
        numero_comprobante="0001-00000099",
        importe_comprobante=1210.0,
        cuit_retenido="30500010912",
        condicion=1,
    )
    op, kw = cliente.calls[0]
    cert = kw["certificado"]
    assert cert["impuesto"] == 216
    assert cert["regimen"] == 831
    assert cert["importeRetencion"] == 210.0
    assert cert["importeBaseCalculo"] == 1000.0
    assert cert["tipoComprobante"] == 1
    assert cert["numeroComprobante"] == "0001-00000099"
    assert cert["cuitRetenido"] == "30500010912"
    # respuesta parseada en atributos públicos
    assert w.CertificadoNro == "0001-00000042"
    assert w.CodigoSeguridad == "ABC123"


def test_emitir_rama_anulacion():
    "La anulación viaja como campos del certificado de emitir (motivoAnulacion, ...)."
    cliente = _FakeClient(
        {"emitir": {"certificadoNro": "0001-00000043", "codigoSeguridad": "DEF456"}}
    )
    w = _nuevo(cliente)
    assert w.Emitir(
        motivo_anulacion=1,
        numero_certificado_original="0001-00000042",
        importe_certificado_original=210.0,
        cuit_retenido="30500010912",
    )
    op, kw = cliente.calls[0]
    cert = kw["certificado"]
    assert cert["motivoAnulacion"] == 1
    assert cert["numeroCertificadoOriginal"] == "0001-00000042"
    assert cert["importeCertificadoOriginal"] == 210.0
    assert w.CertificadoNro == "0001-00000043"
