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

"""Test de replay (cassette VCR) de WSLCA contra el envelope real.

Reproduce una interacción real grabada contra homologación (WSDL vivo
``wslca/services/soap`` + catálogos), validando el parseo de los catálogos
código/descripción contra la estructura real de ARCA (esquema unqualified).

Cassette saneado: token/sign del Ticket de Acceso reemplazados por placeholders
y CUIT representada del titular por una sintética. El replay matchea por
método+URI; las llamadas se hacen en el mismo orden que la grabación.

``vcr`` + ``dontusefix``: corre **offline**, sin certificado ni red.
"""

import pytest

from pyarcaws.wslca import WSLCA

pytestmark = [pytest.mark.vcr, pytest.mark.dontusefix]

WSDL = "https://fwshomo.afip.gov.ar/wslca/services/soap?wsdl"


def test_catalogos_wslca_homologacion():
    """Replay de Dummy + catálogos reales (provincias, tributos, tipos cbte)."""
    w = WSLCA()
    w.LanzarExcepciones = False
    w.Token, w.Sign = "TOKEN_SANITIZED", "SIGN_SANITIZED"
    w.Cuit = 20111111112
    assert w.Conectar("", WSDL) is True

    # mismo orden que la grabación: Dummy, Provincias, Tributos, TiposComprobante
    w.Dummy()

    provincias = w.ConsultarProvincias(sep=None)
    assert isinstance(provincias, dict)
    assert provincias.get("1") == "BUENOS AIRES"   # provincia real de ARCA
    assert len(provincias) >= 20

    tributos = w.ConsultarTributos(sep=None)
    assert isinstance(tributos, dict)
    assert len(tributos) >= 1

    tipos = w.ConsultarTiposComprobante(sep=None)
    assert isinstance(tipos, dict)
    # los tipos de WSLCA son las liquidaciones de compra de caña de azúcar
    assert any("CAÑA DE AZÚCAR" in v.upper() or "CANA DE AZUCAR" in v.upper()
               for v in tipos.values())
