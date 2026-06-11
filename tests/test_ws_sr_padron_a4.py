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

"""Tests unitarios offline de WSSrPadronA4: caracterizaciones (incl. 639 /
Ganancias Simplificada Ley 27.779) y el tag opcional ``fechaSolicitud``
(getPersona_v2, ARCA 11/02/2026).

No usan red ni cassettes: ejercitan analizar_caracterizaciones con dicts
mockeados (modelados del XSD del servicio) y Consultar con un cliente SOAP
falso.
"""

import pytest

from pyarcaws.ws_sr_padron import WSSrPadronA4
from pyarcaws.utils import SoapFault

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


# --- Estructuras mock (modeladas del XSD tns:caracterizacion) --------------

CARACT_639 = {
    "idCaracterizacion": 639,
    "descripcionCaracterizacion": "Ganancias Simplificada Ley 27.779",
    "periodo": 202602,
    "fechaSolicitud": "2026-02-11",
}

CARACT_VARIAS = [
    {"idCaracterizacion": 13, "descripcionCaracterizacion": "Responsable Inscripto", "periodo": 202401},
    {"idCaracterizacion": 639, "descripcionCaracterizacion": "Ganancias Simplificada", "periodo": 202602},
]


def _persona_base():
    "Persona física mínima que satisface los accesos de Consultar."
    return {
        "idPersona": 30673134773,
        "tipoPersona": "JURIDICA",
        "tipoClave": "CUIT",
        "numeroDocumento": "30673134773",
        "estadoClave": "ACTIVO",
        "razonSocial": "EMPRESA EJEMPLO SA",
        "domicilio": [
            {"tipoDomicilio": "FISCAL", "direccion": "CALLE 1", "localidad": "CABA", "idProvincia": 0, "codPostal": "1000"},
        ],
        "impuesto": [{"idImpuesto": 30, "estado": "ACTIVO"}],
        "actividad": [{"idActividad": 461000}],
        "categoria": [],
    }


class _FakeClient:
    def __init__(self, persona=None, exc=None):
        self._persona = persona
        self._exc = exc
        self.xml_request = ""
        self.xml_response = ""
        self.calls = []

    def getPersona(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc:
            raise self._exc
        return {"personaReturn": {"persona": self._persona}}


# --- Tests del parseo de caracterizaciones --------------------------------


def test_caracterizacion_639_con_fecha_solicitud():
    """Caracterización única (dict) con fechaSolicitud: se expone id/descr/
    período/fecha_solicitud."""
    w = WSSrPadronA4()
    w.analizar_caracterizaciones({"caracterizacion": CARACT_639})
    assert w.caracterizaciones == [
        {
            "id": 639,
            "descripcion": "Ganancias Simplificada Ley 27.779",
            "periodo": 202602,
            "fecha_solicitud": "2026-02-11",
        }
    ]
    assert any(c["id"] == 639 for c in w.caracterizaciones)


def test_varias_caracterizaciones_sin_fecha_solicitud():
    """Lista de caracterizaciones sin fechaSolicitud: fecha_solicitud = None,
    sin romper."""
    w = WSSrPadronA4()
    w.analizar_caracterizaciones({"caracterizacion": CARACT_VARIAS})
    assert len(w.caracterizaciones) == 2
    ids = [c["id"] for c in w.caracterizaciones]
    assert ids == [13, 639]
    assert all(c["fecha_solicitud"] is None for c in w.caracterizaciones)


def test_sin_bloque_de_caracterizaciones():
    """Persona sin nodo <caracterizacion>: lista vacía, sin excepción."""
    w = WSSrPadronA4()
    w.analizar_caracterizaciones({"idPersona": 20111111112})
    assert w.caracterizaciones == []


# --- Tests de extremo a extremo (cliente falso) ----------------------------


def test_consultar_persona_con_639(tmp_path):
    """getPersona completo con caracterización 639: Consultar puebla
    self.caracterizaciones junto con los datos generales."""
    persona = _persona_base()
    persona["caracterizacion"] = CARACT_639
    w = WSSrPadronA4()
    w.Sign, w.Token, w.Cuit = "SG", "TK", 20111111112
    w.client = _FakeClient(persona=persona)

    ok = w.Consultar(30673134773)

    assert ok
    assert w.cuit == 30673134773
    assert w.denominacion == "EMPRESA EJEMPLO SA"
    assert {"id": 639, "descripcion": "Ganancias Simplificada Ley 27.779",
            "periodo": 202602, "fecha_solicitud": "2026-02-11"} in w.caracterizaciones


def test_consultar_error_soap_fault_no_rompe():
    """Un SoapFault (p. ej. coe.notAuthorized) se captura en ErrMsg sin
    propagar cuando LanzarExcepciones=False."""
    w = WSSrPadronA4()
    w.LanzarExcepciones = False
    w.Sign, w.Token, w.Cuit = "SG", "TK", 20111111112
    w.client = _FakeClient(
        exc=SoapFault("coe.notAuthorized", "El CUIT no se encuentra autorizado")
    )

    ok = w.Consultar(30673134773)

    assert ok is None  # degradó sin excepción
    assert w.ErrCode == "coe.notAuthorized"
    assert "autorizado" in w.ErrMsg
    assert w.caracterizaciones == []
