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

"""Tests de las deprecaciones de servicios sin reemplazo / reemplazados.

- WSCOC (Operaciones Cambiarias): régimen discontinuado por ARCA en 2015, sin
  WS activo ni reemplazo.
- WSCTG (Trazabilidad de Granos): reemplazado por la Carta de Porte Electrónica
  (WSCPE).

Ambos emiten DeprecationWarning al instanciarse (patrón ya usado en
WSSrPadronA5) y siguen funcionando para no romper compatibilidad. Remoción
prevista para pyarcaws 2.0.
"""

import pytest

pytestmark = pytest.mark.dontusefix


def test_wscoc_emite_deprecation_warning():
    from pyarcaws.wscoc import WSCOC

    with pytest.warns(DeprecationWarning, match="WSCOC"):
        WSCOC()


def test_wsctg_emite_deprecation_warning():
    from pyarcaws.wsctg import WSCTG

    with pytest.warns(DeprecationWarning, match="WSCPE"):
        WSCTG()
