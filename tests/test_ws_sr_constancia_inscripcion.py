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

"""Tests unitarios offline de WSSrConstanciaInscripcion (getPersona_v2) y de la
deprecación de WSSrPadronA5.

No usan red ni cassettes: ejercitan Consultar con un cliente SOAP falso y la
estructura modelada del WSDL vivo personaServiceA5 (personaReturn →
datosGenerales/datosMonotributo/datosRegimenGeneral + bloques de error). La
caracterización cuelga dentro de datosGenerales e incluye el tag opcional
fechaSolicitud (ARCA 11/02/2026).
"""

import pytest

from pyarcaws.ws_sr_padron import (
    WSSrPadronA5,
    WSSrConstanciaInscripcion,
)

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


CARACT_639 = {
    "idCaracterizacion": 639,
    "descripcionCaracterizacion": "GANANCIAS SIMPLIFICADA LEY 27.779",
    "periodo": 202602,
    "fechaSolicitud": 20260211,  # xs:int, opcional (getPersona_v2)
}

CARACT_VARIAS = [
    {"idCaracterizacion": 13, "descripcionCaracterizacion": "RI", "periodo": 202401},
    {"idCaracterizacion": 639, "descripcionCaracterizacion": "GAN SIMPL", "periodo": 202602},
]


def _persona_return(caracterizacion=None, errores=None):
    dg = {
        "idPersona": 30673134773,
        "tipoPersona": "JURIDICA",
        "tipoClave": "CUIT",
        "razonSocial": "EMPRESA EJEMPLO SA",
        "estadoClave": "ACTIVO",
        "domicilioFiscal": {
            "direccion": "CALLE 1",
            "localidad": "CABA",
            "idProvincia": 0,
            "codPostal": "1000",
        },
    }
    if caracterizacion is not None:
        dg["caracterizacion"] = caracterizacion
    ret = {
        "datosGenerales": dg,
        "datosRegimenGeneral": {
            "impuesto": [{"idImpuesto": 30, "estadoImpuesto": "ACTIVO"}],
            "actividad": [{"idActividad": 461000}],
        },
        "datosMonotributo": {},
        "metadata": {"servidor": "test", "fechaHora": "2026-06-11T10:00:00"},
    }
    if errores:
        ret.update(errores)
    return ret


class _FakeClient:
    def __init__(self, persona_return):
        self._ret = persona_return
        self.xml_request = ""
        self.xml_response = ""
        self.calls = []

    def getPersona_v2(self, **kwargs):
        self.calls.append(("v2", kwargs))
        return {"personaReturn": self._ret}

    def getPersona(self, **kwargs):
        self.calls.append(("v1", kwargs))
        return {"personaReturn": self._ret}


def _consultar(persona_return):
    w = WSSrConstanciaInscripcion()
    w.LanzarExcepciones = True
    w.Token = w.Sign = "x"
    w.Cuit = "20111111112"
    w.client = _FakeClient(persona_return)
    ok = w.Consultar(30673134773)
    return w, ok


# --- caracterizaciones -----------------------------------------------------


def test_usa_getpersona_v2_y_caracterizacion_unica_con_fecha():
    w, ok = _consultar(_persona_return(caracterizacion=CARACT_639))
    assert ok
    # se llamó a la operación nueva, no a la vieja
    assert w.client.calls[0][0] == "v2"
    assert w.caracterizaciones == [
        {
            "id": 639,
            "descripcion": "GANANCIAS SIMPLIFICADA LEY 27.779",
            "periodo": 202602,
            "fecha_solicitud": 20260211,
        }
    ]
    assert w.TieneCaracterizacion(639) is True
    assert w.TieneCaracterizacion(13) is False
    # datos generales también poblados
    assert w.denominacion == "EMPRESA EJEMPLO SA"
    assert w.estado == "ACTIVO"
    assert w.impuestos == [30]
    assert w.actividades == [461000]


def test_varias_caracterizaciones_lista_sin_fecha():
    w, ok = _consultar(_persona_return(caracterizacion=CARACT_VARIAS))
    assert ok
    ids = [c["id"] for c in w.caracterizaciones]
    assert ids == [13, 639]
    assert all(c["fecha_solicitud"] is None for c in w.caracterizaciones)
    assert w.TieneCaracterizacion(639) is True


def test_sin_caracterizaciones():
    w, ok = _consultar(_persona_return(caracterizacion=None))
    assert ok
    assert w.caracterizaciones == []
    assert w.TieneCaracterizacion(639) is False


# --- errores tolerantes ----------------------------------------------------


def test_error_constancia_dict_unico_no_explota():
    """errorConstancia llega como dict único con 'error' string: no debe
    lanzar TypeError; puebla errores/Excepcion limpio."""
    ret = _persona_return(
        errores={"errorConstancia": {"error": "No existe la persona consultada", "idPersona": 1}}
    )
    w, ok = _consultar(ret)
    assert ok is False  # hubo errores
    assert w.errores == ["No existe la persona consultada"]
    assert "No existe la persona consultada" in w.Excepcion


def test_errores_multiples_lista():
    ret = _persona_return(
        errores={
            "errorMonotributo": {"error": ["err A", "err B"], "mensaje": "x"},
            "errorRegimenGeneral": {"error": "err C"},
        }
    )
    w, ok = _consultar(ret)
    assert ok is False
    assert w.errores == ["err A", "err B", "err C"]


# --- deprecación de A5 -----------------------------------------------------


def test_a5_emite_deprecation_warning():
    with pytest.warns(DeprecationWarning, match="ws_sr_padron_a5"):
        WSSrPadronA5()


def test_constancia_no_emite_deprecation_warning(recwarn):
    WSSrConstanciaInscripcion()
    assert not any(
        issubclass(w.category, DeprecationWarning) for w in recwarn
    )
