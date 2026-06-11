#!/usr/bin/python
# -*- coding: utf8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Tests unitarios del parseo de errores de WSCDC (sin red ni cassettes).

Reproduce el bug de producción reportado por DeckPagos: cuando ARCA devuelve
un único <Err>, pysimplesoap entrega ``Errors`` como dict (no como lista) y el
parseo heredado de pyafipws explotaba con ``TypeError: string indices must be
integers``.
"""

import pytest

from pyarcaws.wscdc import WSCDC

# Tests offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


def _nuevo_wscdc():
    """WSCDC con las listas de errores ya inicializadas (lo que hace el
    decorador inicializar_y_capturar_excepciones antes de cada llamada)."""
    w = WSCDC()
    w.Errores = []
    w.errores = []
    w.Observaciones = []
    w.observaciones = []
    w.Eventos = []
    w.ErrCode = w.ErrMsg = w.Obs = ""
    return w


def _analizar(w, ret):
    # __analizar_errores está name-manglado (método "privado" de WSCDC)
    return w._WSCDC__analizar_errores(ret)


# Caso reproducible exacto capturado en producción (un solo Err -> dict)
ERR_UNICO_DICT = {
    "Errors": {
        "Err": {
            "Code": 4,
            "Msg": "Campo CbteTipo no se corresponde con alguno de los "
            "comprobantes habilitados en ComprobantesTipoConsultar",
        }
    }
}

# Múltiples errores -> lista de Err bajo un único Errors (otra forma SOAP)
ERR_MULTIPLE_LISTA = {
    "Errors": {
        "Err": [
            {"Code": 4, "Msg": "Primer error"},
            {"Code": 100, "Msg": "Segundo error"},
        ]
    }
}

# Forma histórica que asumía el código viejo (lista de {'Err': {...}}), que
# debe seguir funcionando para no romper el test existente test_analizar_errores
ERR_LISTA_DE_DICTS = {
    "Errors": [
        {"Err": {"Code": 100, "Msg": "El N° de CAE consultado no existe."}},
    ]
}


def test_error_unico_como_dict_no_explota():
    """El caso de producción: un solo Err llega como dict, no debe lanzar
    TypeError y debe poblar Errores/ErrMsg/ErrCode."""
    w = _nuevo_wscdc()
    _analizar(w, ERR_UNICO_DICT)
    assert w.ErrMsg
    assert "CbteTipo" in w.ErrMsg
    assert w.Errores == [
        "4: Campo CbteTipo no se corresponde con alguno de los "
        "comprobantes habilitados en ComprobantesTipoConsultar"
    ]
    assert w.errores == [
        {
            "code": 4,
            "msg": "Campo CbteTipo no se corresponde con alguno de los "
            "comprobantes habilitados en ComprobantesTipoConsultar",
        }
    ]
    assert w.ErrCode == "4"


def test_errores_multiples_como_lista():
    """Varios Err bajo un mismo Errors (lista) se aplanan correctamente."""
    w = _nuevo_wscdc()
    _analizar(w, ERR_MULTIPLE_LISTA)
    assert w.Errores == ["4: Primer error", "100: Segundo error"]
    assert w.ErrCode == "4 100"
    assert len(w.errores) == 2


def test_forma_historica_lista_de_dicts():
    """La forma antigua (lista de {'Err': {...}}) sigue soportada."""
    w = _nuevo_wscdc()
    _analizar(w, ERR_LISTA_DE_DICTS)
    assert w.Errores == ["100: El N° de CAE consultado no existe."]
    assert w.ErrCode == "100"


def test_sin_errores_camino_feliz():
    """Respuesta válida sin clave Errors: no toca ErrMsg (camino feliz,
    referencia real de producción: FC C, Resultado='A')."""
    w = _nuevo_wscdc()
    _analizar(w, {"Resultado": "A", "CmpResp": {"CbteNro": 16}})
    assert w.ErrMsg == ""
    assert w.Errores == []


@pytest.mark.parametrize("ret", [
    {"Errors": None},
    {"Errors": ""},
    {"Errors": {}},
    {"Errors": []},
])
def test_errors_vacio_o_nulo_no_explota(ret):
    """Errors ausente de contenido (None/''/{}/[]) no debe lanzar excepción."""
    w = _nuevo_wscdc()
    _analizar(w, ret)
    assert w.ErrMsg == ""
    assert w.Errores == []
