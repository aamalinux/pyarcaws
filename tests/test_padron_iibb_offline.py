#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

"""Tests offline del parser de padrones de alícuotas IIBB (``padron_iibb``).

100% offline: leen fixtures TXT/ZIP hechas a mano (latin-1) que reproducen los
diseños oficiales de ARBA ("Régimen de Recaudación por Sujeto") y AGIP ("Padrón
Unificado"). Sin red ni credenciales.
"""

import datetime
import os

import pytest

from pyarcaws.padron_iibb import PadronIIBB, ARBA, AGIP

pytestmark = pytest.mark.dontusefix

FIXT = os.path.join(os.path.dirname(__file__), "fixtures", "padron_iibb")


def _arba():
    p = PadronIIBB()
    p.Cargar(os.path.join(FIXT, "arba_rgs_062026.zip"))
    return p


def _agip():
    p = PadronIIBB()
    p.Cargar(os.path.join(FIXT, "AgipPadronUnificado.txt"))
    return p


# --- ARBA -------------------------------------------------------------------


def test_cargar_arba_zip_detecta_jurisdiccion():
    p = _arba()
    assert p.jurisdiccion == ARBA
    # 4 CUIT válidos (los 2 registros malformados se ignoran)
    assert len(p.registros) == 4


def test_arba_fusiona_retencion_y_percepcion():
    "Un CUIT presente en el archivo de Ret y en el de Per se fusiona en un registro."
    p = _arba()
    reg = p.Consultar("30500010912")
    assert reg is not None
    assert reg["jurisdiccion"] == ARBA
    assert reg["alicuota_retencion"] == 1.50
    assert reg["alicuota_percepcion"] == 2.25
    assert reg["grupo_retencion"] == "05"
    assert reg["grupo_percepcion"] == "07"
    # ARBA no trae razón social
    assert reg["razon_social"] == ""


def test_arba_solo_retencion_deja_percepcion_none():
    p = _arba()
    reg = p.Consultar("20111111112")
    assert reg["alicuota_retencion"] == 3.00
    assert reg["alicuota_percepcion"] is None
    assert reg["grupo_percepcion"] is None


def test_arba_solo_percepcion_deja_retencion_none():
    p = _arba()
    reg = p.Consultar("33693450239")
    assert reg["alicuota_percepcion"] == 5.00
    assert reg["alicuota_retencion"] is None


def test_alicuota_cero_no_es_none():
    "Una alícuota 0,00 es un valor válido (0.0), distinto de 'no informada' (None)."
    p = _arba()
    reg = p.Consultar("27000000014")
    assert reg["alicuota_retencion"] == 0.0
    assert reg["alicuota_retencion"] is not None


def test_tipo_contribuyente_y_marca_alta_baja():
    p = _arba()
    assert p.Consultar("30500010912")["regimen_tipo_contribuyente"] == "C"
    assert p.Consultar("20111111112")["regimen_tipo_contribuyente"] == "D"
    assert p.Consultar("30500010912")["marca_alta_baja"] == "S"
    assert p.Consultar("27000000014")["marca_alta_baja"] == "B"


def test_fecha_ddmmaaaa_a_date():
    p = _arba()
    reg = p.Consultar("30500010912")
    assert reg["vigencia_desde"] == datetime.date(2026, 6, 2)
    assert reg["vigencia_hasta"] == datetime.date(2026, 8, 31)


def test_lineas_malformadas_no_revientan():
    "Líneas vacías / mal formadas / con CUIT inválido se ignoran sin excepción."
    # _arba() ya cargó un fixture con una línea vacía + 2 malformadas: si
    # reventara, _arba() habría lanzado. Verificamos que cargó sólo las válidas.
    p = _arba()
    assert len(p.registros) == 4
    assert p.Consultar("00000000000") is None  # el CUIT 'ABC' inválido no entró


def test_cargar_txt_directo_sin_zip():
    "Cargar acepta un TXT suelto (no sólo ZIP)."
    p = PadronIIBB()
    p.Cargar(os.path.join(FIXT, "PadronRGSRet062026.txt"))
    assert p.jurisdiccion == ARBA
    assert p.Consultar("30500010912")["alicuota_retencion"] == 1.50
    # sin el archivo de percepción, esa alícuota queda None
    assert p.Consultar("30500010912")["alicuota_percepcion"] is None


# --- AGIP -------------------------------------------------------------------


def test_cargar_agip_detecta_jurisdiccion():
    p = _agip()
    assert p.jurisdiccion == AGIP
    assert len(p.registros) == 3


def test_agip_ambas_alicuotas_y_razon_social():
    p = _agip()
    reg = p.Consultar("30700000005")
    assert reg["jurisdiccion"] == AGIP
    assert reg["alicuota_percepcion"] == 1.00
    assert reg["alicuota_retencion"] == 2.50
    assert reg["grupo_percepcion"] == "00"
    assert reg["grupo_retencion"] == "00"
    assert reg["razon_social"] == "EMPRESA EJEMPLO SA"
    assert reg["regimen_tipo_contribuyente"] == "D"


def test_agip_razon_social_latin1():
    "La razón social con ñ/ó (latin-1) se decodifica correctamente."
    p = _agip()
    reg = p.Consultar("23333333334")
    assert reg["razon_social"] == u"CAÑUELAS DISTRIBUCIÓN SA"
    assert reg["alicuota_percepcion"] == 3.75
    assert reg["alicuota_retencion"] == 0.0  # 0,00 válido, no None


def test_agip_zip():
    p = PadronIIBB()
    p.Cargar(os.path.join(FIXT, "agip_unificado.zip"))
    assert p.jurisdiccion == AGIP
    assert p.Consultar("20222222223")["razon_social"] == "JUAN PEREZ"


# --- consulta / normalización ----------------------------------------------


def test_cuit_no_en_padron_devuelve_none():
    "No encontrado -> None (sentinel), nunca un registro con alícuota 0."
    p = _arba()
    assert p.Consultar("99999999999") is None


def test_consultar_normaliza_cuit_con_guiones():
    p = _arba()
    base = p.Consultar("30500010912")
    assert p.Consultar("30-50001091-2") is base
    assert p.Consultar(30500010912) is base  # int también
