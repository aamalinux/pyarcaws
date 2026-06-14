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

"""Tests de robustez de ``Conectar`` y del parseo de WSDL (sin red).

Cubre dos arreglos de librería:

1. Sufijo ``?WSDL`` case-insensitive: una URL terminada en ``?WSDL`` (mayúsculas,
   como la usan algunos ejemplos/integraciones) no debe reincorporar ``?wsdl`` y
   quedar como ``...?WSDL?wsdl`` (URL inválida que devolvía una página de error).
2. Cuando el servidor devuelve un documento que no es un WSDL (SOAP Fault o
   página HTML de error), el parseo debe surgir el motivo real (faultstring /
   raíz inesperada) en vez del críptico ``Tag not found: message``.
"""

import warnings

import pytest

from pyarcaws._vendor.pysimplesoap import client as C
from pyarcaws.ws_sr_padron import WSSrConstanciaInscripcion

pytestmark = pytest.mark.dontusefix


WSDL_BASE = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5"

FAULT_XML = (
    b'<soapenv:Envelope '
    b'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
    b'<soapenv:Body><soapenv:Fault>'
    b'<faultcode>soapenv:Server</faultcode>'
    b'<faultstring>Servicio no disponible (homologacion)</faultstring>'
    b'</soapenv:Fault></soapenv:Body></soapenv:Envelope>'
)

HTML_404 = b'<html><head><title>404 Not Found</title></head><body>x</body></html>'


@pytest.mark.parametrize("sufijo", ["?WSDL", "?wsdl", ""])
def test_conectar_sufijo_wsdl_case_insensitive(monkeypatch, sufijo):
    """Conectar no debe duplicar el sufijo aunque la URL use ?WSDL en mayúsculas."""
    capturado = {}

    # interceptar la descarga del WSDL para no usar red y ver la URL final
    def fake_url_to_xml_tree(self, url, cache, force_download):
        capturado["url"] = url
        raise RuntimeError("corte intencional luego de fijar la URL")

    monkeypatch.setattr(C.SoapClient, "_url_to_xml_tree", fake_url_to_xml_tree)

    ws = WSSrConstanciaInscripcion()
    ws.LanzarExcepciones = False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ws.Conectar(wsdl=WSDL_BASE + sufijo)

    # la URL no debe contener el sufijo duplicado
    assert "?WSDL?wsdl" not in capturado["url"]
    assert "?wsdl?wsdl" not in capturado["url"]
    assert capturado["url"].lower().endswith("?wsdl")


def test_wsdl_no_valido_surge_faultstring(monkeypatch):
    """Un SOAP Fault en vez de un WSDL debe surgir el faultstring real."""
    monkeypatch.setattr(C, "fetch", lambda *a, **k: FAULT_XML)
    ws = WSSrConstanciaInscripcion()
    ws.LanzarExcepciones = False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ok = ws.Conectar(wsdl=WSDL_BASE)
    assert ok is False
    assert "Tag not found" not in ws.Excepcion
    assert "Servicio no disponible" in ws.Excepcion


def test_wsdl_no_valido_html_surge_raiz(monkeypatch):
    """Una página HTML de error debe surgir la raíz inesperada, no 'Tag not found'."""
    monkeypatch.setattr(C, "fetch", lambda *a, **k: HTML_404)
    ws = WSSrConstanciaInscripcion()
    ws.LanzarExcepciones = False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ok = ws.Conectar(wsdl=WSDL_BASE)
    assert ok is False
    assert "Tag not found" not in ws.Excepcion
    assert "<html>" in ws.Excepcion
