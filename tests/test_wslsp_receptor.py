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

"""Tests unitarios offline de WSLSP: consulta de liquidación por receptor
(comprador) y parseo tolerante de errores.

No usan red ni cassettes: ejercitan AnalizarLiquidacion/__analizar_errores con
estructuras mockeadas (modeladas del WSDL/XSD del servicio y de una respuesta
real capturada) y ConsultarLiquidacion con un cliente SOAP falso.

Caso de referencia (DeckPagos / CABRAS): liquidación tipo 190, PV 3, N° 16,
CUIT emisor 30690720023, CAE 86217130787511, $80.735.921,11.
"""

import pytest

from pyarcaws.wslsp import WSLSP

# Offline: no usar la fixture de autenticación (auth) del conftest
pytestmark = pytest.mark.dontusefix


def _nuevo_wslsp():
    w = WSLSP()
    w.LanzarExcepciones = True  # que cualquier bug de parseo aflore en el test
    w.Errores = []
    w.errores = []
    w.ErrCode = w.ErrMsg = ""
    w.inicializar()
    return w


def _analizar_errores(w, ret):
    return w._WSLSP__analizar_errores(ret)


# --- Estructuras mock ------------------------------------------------------

# Respuesta exitosa (consultarLiquidacionPorNroComprobante). gasto/tributo van
# como dict único a propósito para verificar la tolerancia single-vs-list.
LIQ_OK = {
    "cabecera": {
        "cae": "86217130787511",
        "fechaVencimientoCae": "20260606",
        "fechaProcesoAFIP": "20260527",
        "nroCodigoBarras": "8621713078751120260606",
    },
    "datosLiquidacion": {"fechaComprobante": "20260527"},
    "emisor": {
        "tipoComprobante": 190,
        "puntoVenta": 3,
        "nroComprobante": 16,
        "razonSocial": "FRIGORIFICO EJEMPLO SA",
        "domicilioPuntoVenta": "RUTA 5 KM 100",
    },
    "receptor": {"nombre": "COMPRADOR EJEMPLO SA", "domicilio": "AV SIEMPREVIVA 742"},
    "resumenTotales": {
        "importeBruto": 80735921.11,
        "importeTotalGastos": 100.0,
        "importeTotalTributos": 50.0,
        "importeTotalNeto": 80735771.11,
        "importeIVASobreBruto": 8000.0,
        "importeIVASobreGastos": 10.0,
    },
    "gasto": {"codGasto": 16, "importe": 100.0},
    "tributo": {
        "codTributo": 5,
        "importe": 50.0,
        "baseImponible": 80735921.11,
        "alicuota": 2.5,
        "descripcion": "IIBB",
    },
    "pdf": b"%PDF-1.4 contenido de prueba",
}

# Error de negocio único -> pysimplesoap entrega <errores> como dict.
# Caso textual capturado: servicio no autorizado para el certificado.
ERR_NO_AUTORIZADO = {
    "errores": {
        "error": {
            "codigo": "coe.notAuthorized",
            "descripcion": "El CUIT representado no se encuentra autorizado a "
            "utilizar el presente WebService.",
        }
    }
}

# Varios errores -> lista.
ERR_MULTIPLES = {
    "errores": {
        "error": [
            {"codigo": "1009", "descripcion": "Primer error"},
            {"codigo": "2010", "descripcion": "Segundo error"},
        ]
    }
}

# Liquidación inexistente: error de negocio sin bloque de datos (sin cabecera).
LIQ_INEXISTENTE = {
    "errores": {
        "error": {
            "codigo": "501",
            "descripcion": "No existe la liquidación solicitada.",
        }
    }
}


# --- Cliente SOAP falso ----------------------------------------------------


class _FakeClient:
    def __init__(self, respuesta):
        self._respuesta = respuesta
        self.calls = []
        self.xml_request = ""
        self.xml_response = ""

    def consultarLiquidacionPorNroComprobante(self, **kwargs):
        self.calls.append(("porNro", kwargs))
        return {"respuesta": self._respuesta}

    def consultarLiquidacionPorCae(self, **kwargs):
        self.calls.append(("porCae", kwargs))
        return {"respuesta": self._respuesta}


# --- Tests de parseo de errores -------------------------------------------


def test_error_no_autorizado_unico_no_explota():
    """coe.notAuthorized llega como <error> único (dict): no debe lanzar
    TypeError y debe poblar Errores/ErrMsg."""
    w = _nuevo_wslsp()
    _analizar_errores(w, ERR_NO_AUTORIZADO)
    assert w.ErrMsg
    assert "coe.notAuthorized" in w.ErrMsg
    assert w.Errores == [
        "coe.notAuthorized: El CUIT representado no se encuentra autorizado a "
        "utilizar el presente WebService."
    ]
    assert w.errores[0]["codigo"] == "coe.notAuthorized"


def test_errores_multiples_como_lista():
    w = _nuevo_wslsp()
    _analizar_errores(w, ERR_MULTIPLES)
    assert w.Errores == ["1009: Primer error", "2010: Segundo error"]
    assert len(w.errores) == 2


def test_sin_errores_no_toca_errmsg():
    w = _nuevo_wslsp()
    _analizar_errores(w, {"cabecera": {"cae": "1"}})
    assert w.ErrMsg == ""
    assert w.Errores == []


# --- Tests de la consulta por comprador -----------------------------------


def test_consultar_por_comprador_y_pdf(tmp_path):
    """ConsultarLiquidacion por receptor: arma el request con cuitComprador,
    parsea la liquidación y guarda el PDF en disco."""
    w = _nuevo_wslsp()
    w.Token, w.Sign, w.Cuit = "TK", "SG", "20111111112"
    w.client = _FakeClient(LIQ_OK)
    pdf_path = tmp_path / "liq.pdf"

    ok = w.ConsultarLiquidacion(
        tipo_cbte=190,
        pto_vta=3,
        nro_cbte=16,
        cuit_comprador="30690720023",
        pdf=str(pdf_path),
    )

    assert ok
    # se usó el método por número de comprobante con el CUIT comprador
    modo, kwargs = w.client.calls[0]
    assert modo == "porNro"
    sol = kwargs["solicitud"]
    assert sol["cuitComprador"] == "30690720023"
    assert sol["tipoComprobante"] == 190
    assert sol["puntoVenta"] == 3
    assert sol["nroComprobante"] == 16
    assert sol["pdf"] is True
    # datos de la liquidación poblados
    assert w.CAE == "86217130787511"
    assert w.NroComprobante == 16
    assert w.ImporteBruto == 80735921.11
    assert w.params_out["emisor"]["razon_social"] == "FRIGORIFICO EJEMPLO SA"
    assert w.params_out["receptor"]["nombre"] == "COMPRADOR EJEMPLO SA"
    # gasto/tributo único (dict) tolerado y normalizado a lista
    assert w.params_out["gasto"] == [{"cod_gasto": 16, "importe": 100.0}]
    assert w.params_out["tributo"][0]["codigo"] == 5
    # PDF escrito a disco
    assert pdf_path.read_bytes() == b"%PDF-1.4 contenido de prueba"
    assert not w.Errores


def test_consultar_por_cae(tmp_path):
    """Con CAE usa el método por CAE (sin tocar cuitComprador)."""
    w = _nuevo_wslsp()
    w.Token, w.Sign, w.Cuit = "TK", "SG", "20111111112"
    w.client = _FakeClient(LIQ_OK)

    ok = w.ConsultarLiquidacion(cae="86217130787511", pdf=str(tmp_path / "x.pdf"))

    assert ok
    modo, kwargs = w.client.calls[0]
    assert modo == "porCae"
    assert kwargs["solicitud"]["cae"] == "86217130787511"


def test_consultar_liquidacion_inexistente_degrada_limpio(tmp_path):
    """Liquidación inexistente: error de negocio, sin cabecera; ConsultarLiquidacion
    retorna sin excepción con Errores poblado y CAE vacío."""
    w = _nuevo_wslsp()
    w.Token, w.Sign, w.Cuit = "TK", "SG", "20111111112"
    w.client = _FakeClient(LIQ_INEXISTENTE)

    ok = w.ConsultarLiquidacion(
        tipo_cbte=190, pto_vta=3, nro_cbte=99999, cuit_comprador="30690720023",
        pdf="",
    )

    assert ok
    assert w.CAE == ""
    assert w.Errores == ["501: No existe la liquidación solicitada."]
