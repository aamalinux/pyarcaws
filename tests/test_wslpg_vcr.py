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

"""Replay offline (cassette VCR) de los catálogos de WSLPG contra homologación.

Un único cassette con el GET del WSDL + los POST de todos los catálogos read-only
(mismo endpoint), grabado en vivo contra homologación con el certificado WSASS
(wslpg autorizado). El test los reproduce en el MISMO orden que la grabación
(VCR matchea por método+URI y consume las interacciones en secuencia).

Valida el parseo contra el envelope real de ARCA: la estructura de los catálogos
es ``{<nodo>: {codigoDescripcion: [...]}}`` (el nodo repetible es
``codigoDescripcion``); el módulo lo aplana con ``normalizar_lista_soap``.

Cassette **saneado**: token/sign del Ticket de Acceso → placeholders, CUIT del
agente → sintético, cookies ``Set-Cookie`` del balanceador filtradas. Los
catálogos son datos de referencia públicos (sin PII).

`vcr` + `dontusefix`: corre offline, sin red ni certificado.

Nota: `Dummy` no se valida en vivo — el endpoint lo responde con
``[common_001] Acceso Denegado`` (se invoca sin auth), independientemente de la
autorización WSASS. Las escrituras (`AutorizarLiquidacion`/ajustes/anulaciones)
quedan modeladas offline en ``test_wslpg_offline.py``.
"""

import pytest

from pyarcaws.wslpg import WSLPG, WSDL

pytestmark = [pytest.mark.vcr, pytest.mark.dontusefix]


def test_catalogos_homologacion():
    w = WSLPG()
    w.LanzarExcepciones = False
    w.Token, w.Sign, w.Cuit = "TOKEN_SANITIZED", "SIGN_SANITIZED", 20111111112
    assert w.Conectar("", WSDL) is True

    # MISMO orden que la grabación (todos los POST van al mismo endpoint)
    w.ConsultarUltNroOrden(pto_emision=1)
    assert w.Errores == []
    assert w.NroOrden == 0  # el agente de prueba no tiene órdenes en homo

    provincias = w.ConsultarProvincias(sep=None)
    assert w.Errores == []
    assert isinstance(provincias, dict) and len(provincias) >= 24
    assert provincias[1] == "BUENOS AIRES"
    assert provincias[0] == "CAP.FEDERAL"

    granos = w.ConsultarTipoGrano(sep=None)
    assert isinstance(granos, dict) and len(granos) >= 60
    assert granos["1"] == "LINO"

    campanias = w.ConsultarCampanias()
    assert len(campanias) >= 10
    assert any("2025/2026" in c for c in campanias)

    puertos = w.ConsultarPuerto()
    assert len(puertos) >= 14

    actividades = w.ConsultarTipoActividad()
    assert len(actividades) >= 30

    deducciones = w.ConsultarTipoDeduccion()
    assert len(deducciones) >= 3
    assert any("Comision" in d for d in deducciones)

    retenciones = w.ConsultarTipoRetencion()
    assert len(retenciones) >= 4
    assert any("I.V.A." in r for r in retenciones)

    grados_ref = w.ConsultarCodigoGradoReferencia()
    assert len(grados_ref) >= 3

    tipos_cert = w.ConsultarTipoCertificadoDeposito()
    assert len(tipos_cert) >= 1

    # gradoEnt tiene un anidamiento distinto ({gradoEnt: [{codigoDescripcion, valor}]})
    grados_ent = w.ConsultarGradoEntregadoXTipoGrano(1, sep=None)
    assert isinstance(grados_ent, dict) and len(grados_ent) >= 1

    localidades = w.ConsultarLocalidadesPorProvincia(24, sep=None)
    assert isinstance(localidades, dict) and len(localidades) >= 50
