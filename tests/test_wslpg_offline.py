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

"""Tests unitarios offline de WSLPG (Liquidación Primaria Electrónica de Granos).

No usan red ni cassettes: ejercitan con un cliente SOAP falso la estructura
modelada del WSDL vivo (wslpg/LpgService). Cubren:

  - importación / alias y la autenticación clásica (``cuit`` en minúsculas,
    igual que WSLSP/WSLCA — *no* ``cuitRepresentada``).
  - el patrón builder: ``CrearLiquidacion`` + los ``Agregar*`` persisten entre
    llamadas decoradas (cada una pasa por ``inicializar``) y arman el envelope
    que recibe ``AutorizarLiquidacion``.
  - el parseo tolerante single-vs-list de los nodos repetibles (catálogos,
    ``errores`` y las sub-estructuras retenciones/deducciones de la respuesta):
    pysimplesoap entrega un único hijo como dict y varios como lista; con
    ``como_lista`` ninguno rompe.

Marca ``dontusefix``: corren sin certificado ni red.
"""

import pytest

from pyarcaws.wslpg import WSLPG

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


class _FakeClient:
    """Cliente SOAP falso: cada operación devuelve la respuesta preconfigurada.

    Registra las llamadas (nombre + kwargs) para inspeccionar el request armado.
    """

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
    w = WSLPG()
    w.LanzarExcepciones = True
    w.Token, w.Sign, w.Cuit = "TK", "SG", 20111111112
    w.client = client
    return w


# --- importación / autenticación -------------------------------------------


def test_import_y_version():
    w = WSLPG()
    assert "WSLPG" in w.Version or w.Version  # versión presente


def test_dummy():
    cliente = _FakeClient(
        {"dummy": {"return": {"appserver": "OK", "dbserver": "OK", "authserver": "OK"}}}
    )
    w = _nuevo(cliente)
    assert w.Dummy()
    assert w.AppServerStatus == "OK"
    assert w.DbServerStatus == "OK"
    assert w.AuthServerStatus == "OK"


def test_auth_usa_cuit_no_cuit_representada():
    "Diferencia clave: WSLPG autentica con 'cuit' (minúscula), no cuitRepresentada."
    cliente = _FakeClient({"provinciasConsultar": {"provinciasReturn": {"provincias": []}}})
    w = _nuevo(cliente)
    w.ConsultarProvincias()
    op, kw = cliente.calls[0]
    assert op == "provinciasConsultar"
    assert kw["auth"] == {"token": "TK", "sign": "SG", "cuit": 20111111112}
    assert "cuitRepresentada" not in kw["auth"]


# --- builder: persistencia de los Agregar* entre llamadas decoradas ---------


def test_crear_liquidacion_y_agregar_persisten():
    """Cada Agregar* pasa por @inicializar_y_capturar_excepciones; las listas
    creadas en CrearLiquidacion NO se resetean en inicializar y acumulan."""
    cliente = _FakeClient(
        {"liquidacionAutorizar": {"liqReturn": {"autorizacion": {"coe": "330100000001",
                                                                 "nroOrden": 1,
                                                                 "estado": "AC"}}}}
    )
    w = _nuevo(cliente)
    w.CrearLiquidacion(
        nro_orden=1,
        cuit_comprador=20111111112,
        nro_act_comprador=29,
        cod_grano=2,
        cuit_vendedor=23000000000,
        fecha_precio_operacion="2026-06-01",
        precio_ref_tn=100,
    )
    w.AgregarCertificado(
        tipo_certificado_deposito=5,
        nro_certificado_deposito="123",
        peso_neto=1000,
        cod_localidad_procedencia=3,
        cod_prov_procedencia=1,
        campania=2526,
        fecha_cierre="2026-06-01",
    )
    w.AgregarRetencion(codigo_concepto="RI", detalle_aclaratorio="IVA",
                       base_calculo=100, alicuota=10.5)
    w.AgregarRetencion(codigo_concepto="RG", detalle_aclaratorio="Gan",
                       base_calculo=100, alicuota=2.0)
    w.AgregarDeduccion(codigo_concepto="AL", detalle_aclaratorio="alm",
                       dias_almacenaje="5", precio_pkg_diario=0.1, alicuota=21)

    # las estructuras se acumularon pese a inicializar() en cada Agregar*
    assert len(w.liquidacion["certificados"]) == 1
    assert len(w.retenciones) == 2
    assert len(w.deducciones) == 1


def test_autorizar_liquidacion_arma_envelope():
    cliente = _FakeClient(
        {"liquidacionAutorizar": {"liqReturn": {"autorizacion": {"coe": "330100000002",
                                                                 "nroOrden": 7,
                                                                 "estado": "AC"}}}}
    )
    w = _nuevo(cliente)
    w.CrearLiquidacion(nro_orden=7, cod_grano=2, cuit_vendedor=23000000000)
    w.AgregarRetencion(codigo_concepto="RI", detalle_aclaratorio="IVA",
                       base_calculo=100, alicuota=10.5)
    assert w.AutorizarLiquidacion()

    op, kw = cliente.calls[-1]
    assert op == "liquidacionAutorizar"
    # auth clásico
    assert kw["auth"]["cuit"] == 20111111112
    # la liquidación viaja con nroOrden y codGrano
    assert kw["liquidacion"]["nroOrden"] == 7
    assert kw["liquidacion"]["codGrano"] == 2
    # la retención agregada viaja en el request
    assert kw["retenciones"][0]["retencion"]["codigoConcepto"] == "RI"
    # respuesta parseada
    assert w.COE == "330100000002"
    assert w.NroOrden == 7
    assert w.Estado == "AC"


# --- catálogos: tolerancia single-vs-list ----------------------------------


def _provincias_resp(cod_desc):
    # estructura REAL de ARCA: el nodo repetible es <codigoDescripcion> dentro de
    # <provincias> (varios -> lista; uno solo -> dict). Confirmado en vivo (homo).
    return {"provinciasConsultar": {"provinciasReturn":
            {"provincias": {"codigoDescripcion": cod_desc}}}}


def test_provincias_lista():
    cliente = _FakeClient(_provincias_resp([
        {"codigo": "1", "descripcion": "BUENOS AIRES"},
        {"codigo": "2", "descripcion": "CATAMARCA"},
    ]))
    w = _nuevo(cliente)
    out = w.ConsultarProvincias(sep=None)
    assert out == {1: "BUENOS AIRES", 2: "CATAMARCA"}


def test_provincia_unica_como_dict_tolerada():
    "Con un único elemento ARCA entrega <codigoDescripcion> como dict (no lista):"
    "normalizar_lista_soap lo aplana."
    cliente = _FakeClient(_provincias_resp(
        {"codigo": "1", "descripcion": "BUENOS AIRES"}
    ))
    w = _nuevo(cliente)
    out = w.ConsultarProvincias(sep=None)
    assert out == {1: "BUENOS AIRES"}


def test_tipo_grano_unico_tolerado():
    cliente = _FakeClient({"tipoGranoConsultar": {"tipoGranoReturn": {"granos":
        {"codigoDescripcion": {"codigo": "2", "descripcion": "TRIGO"}}}}})  # único
    w = _nuevo(cliente)
    assert w.ConsultarTipoGrano(sep=None) == {"2": "TRIGO"}


def test_campanias_lista_formato_sep():
    cliente = _FakeClient({"campaniaConsultar": {"campaniaReturn": {"campanias":
        {"codigoDescripcion": [{"codigo": "2526", "descripcion": "2025/2026"}]}}}})
    # ojo: el método llama a campaniasConsultar (plural)
    cliente._respuestas["campaniasConsultar"] = cliente._respuestas.pop("campaniaConsultar")
    w = _nuevo(cliente)
    out = w.ConsultarCampanias()
    assert out == ["|| 2526 || 2025/2026 ||"]


# --- errores: tolerancia single-vs-list ------------------------------------


def test_error_unico_no_rompe():
    "Un único <errores> llega como dict; como_lista lo aplana sin TypeError."
    cliente = _FakeClient({"provinciasConsultar": {"provinciasReturn": {
        "errores": {"error": {"codigo": "100", "descripcion": "Sin autorización"}}
    }}})
    w = _nuevo(cliente)
    w.ConsultarProvincias()
    assert w.errores == [{"codigo": "100", "descripcion": "Sin autorización"}]
    assert "100" in w.ErrCode


def test_errores_varios():
    cliente = _FakeClient({"provinciasConsultar": {"provinciasReturn": {"errores": [
        {"error": {"codigo": "1", "descripcion": "err uno"}},
        {"error": {"codigo": "2", "descripcion": "err dos"}},
    ]}}})
    w = _nuevo(cliente)
    w.ConsultarProvincias()
    assert [e["codigo"] for e in w.errores] == ["1", "2"]


# --- respuesta: sub-estructuras repetibles single-vs-list ------------------


def test_autorizar_parsea_una_sola_retencion():
    "La respuesta con una única retención llega como dict: como_lista la aplana."
    aut = {
        "coe": "330100000003", "nroOrden": 9, "estado": "AC",
        "retenciones": {"retencionReturn": {
            "importeRetencion": 10,
            "retencion": {"alicuota": 10.5, "codigoConcepto": "RI",
                          "detalleAclaratorio": "IVA"},
        }},
        "deducciones": {"deduccionReturn": {
            "importeDeduccion": 5,
            "deduccion": {"alicuotaIva": 21, "codigoConcepto": "AL"},
        }},
    }
    cliente = _FakeClient({"liquidacionAutorizar": {"liqReturn": {"autorizacion": aut}}})
    w = _nuevo(cliente)
    w.CrearLiquidacion(nro_orden=9, cod_grano=2)
    assert w.AutorizarLiquidacion()
    assert len(w.params_out["retenciones"]) == 1
    assert w.params_out["retenciones"][0]["codigo_concepto"] == "RI"
    assert len(w.params_out["deducciones"]) == 1
    assert w.params_out["deducciones"][0]["codigo_concepto"] == "AL"


# --- consultas simples ------------------------------------------------------


def test_consultar_ult_nro_orden():
    cliente = _FakeClient(
        {"liquidacionUltimoNroOrdenConsultar": {"liqUltNroOrdenReturn": {"nroOrden": 42}}}
    )
    w = _nuevo(cliente)
    assert w.ConsultarUltNroOrden(pto_emision=1)
    assert w.NroOrden == 42
    op, kw = cliente.calls[0]
    assert kw["ptoEmision"] == 1
    assert kw["auth"]["cuit"] == 20111111112
