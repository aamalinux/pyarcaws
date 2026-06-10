#!/usr/bin/python
# -*- coding: utf8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

"""Tests del núcleo puro pyarcaws.core.qr (sin red ni COM)"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2020-2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"

import base64
import json
import os
import subprocess
import sys

import pytest

from pyarcaws.core.qr import QRGenerator, crear_archivo_temporal, URL_TEMPLATE
from pyarcaws.pyqr import TEST_QR_DATA

pytestmark = [pytest.mark.dontusefix]

# mismos datos que el modo --prueba de la CLI (coinciden con TEST_QR_DATA)
DATOS_PRUEBA = dict(
    ver=1,
    fecha="2020-10-13",
    cuit=30000000007,
    pto_vta=10,
    tipo_cmp=1,
    nro_cmp=94,
    importe=12100,
    moneda="DOL",
    ctz=65.000,
    tipo_doc_rec=80,
    nro_doc_rec=20000000001,
    tipo_cod_aut="E",
    cod_aut=70417054367476,
)


def decodificar_url(url):
    "Extrae y decodifica el payload JSON de la URL del QR"
    prefijo = URL_TEMPLATE % ""
    assert url.startswith(prefijo)
    return json.loads(base64.b64decode(url[len(prefijo):]))


def test_generar_url_coincide_con_test_qr_data():
    "La URL generada con los datos de prueba decodifica al mismo JSON que TEST_QR_DATA"
    gen = QRGenerator()
    url = gen.generar_url(gen.armar_datos(**DATOS_PRUEBA))
    esperado = json.loads(base64.b64decode(TEST_QR_DATA))
    assert decodificar_url(url) == esperado


def test_generar_qr_archivo_png(tmp_path):
    "La imagen PNG se crea y no está vacía"
    archivo = str(tmp_path / "qr.png")
    gen = QRGenerator()
    url = gen.generar_qr(archivo, "PNG", **DATOS_PRUEBA)
    assert url.startswith(URL_TEMPLATE % "")
    assert os.path.exists(archivo)
    assert os.path.getsize(archivo) > 0
    with open(archivo, "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n"


def test_generar_qr_archivo_jpeg(tmp_path):
    "La imagen JPEG se crea y respeta el formato"
    archivo = str(tmp_path / "qr.jpg")
    gen = QRGenerator()
    gen.generar_qr(archivo, "JPEG", **DATOS_PRUEBA)
    assert os.path.getsize(archivo) > 0
    with open(archivo, "rb") as f:
        assert f.read(2) == b"\xff\xd8"  # cabecera JPEG


def test_casteos_strings_numericos():
    "Strings numéricos se castean a los tipos que exige la especificación"
    gen = QRGenerator()
    datos = gen.armar_datos(
        ver="1",
        cuit="30000000007",
        pto_vta="10",
        tipo_cmp="1",
        nro_cmp="94",
        importe="12100.50",
        ctz="65.0",
        tipo_doc_rec="80",
        nro_doc_rec="20000000001",
        cod_aut="70417054367476",
    )
    decodificado = decodificar_url(gen.generar_url(datos))
    assert decodificado["ver"] == 1
    assert decodificado["cuit"] == 30000000007
    assert decodificado["ptoVta"] == 10
    assert decodificado["importe"] == 12100.50
    assert isinstance(decodificado["importe"], float)
    assert decodificado["ctz"] == 65.0
    assert isinstance(decodificado["ctz"], float)
    assert decodificado["nroDocRec"] == 20000000001
    assert isinstance(decodificado["codAut"], int)


def test_casteo_invalido_lanza_excepcion():
    "El núcleo propaga excepciones normales (sin patrón Excepcion/Traceback)"
    gen = QRGenerator()
    with pytest.raises(ValueError):
        gen.armar_datos(cuit="no-es-un-numero")


def test_parametros_de_estilo(tmp_path):
    "box_size, border y colores no rompen la generación"
    archivo = str(tmp_path / "qr_estilo.png")
    gen = QRGenerator(box_size=4, border=2)
    gen.generar_qr(
        archivo, "PNG", color_relleno="darkblue", color_fondo="lightyellow",
        **DATOS_PRUEBA
    )
    assert os.path.getsize(archivo) > 0


def test_crear_archivo_temporal():
    "El archivo temporal se crea con el prefijo y la extensión pedidos"
    ruta = crear_archivo_temporal("JPEG")
    try:
        assert os.path.exists(ruta)
        assert os.path.basename(ruta).startswith("qr_afip_")
        assert ruta.endswith(".jpeg")
    finally:
        os.unlink(ruta)


def test_url_template_personalizada():
    "Se puede cambiar la plantilla de URL (equivale al flag --url de la CLI)"
    gen = QRGenerator(url_template="https://ejemplo.test/qr/?p=%s")
    url = gen.generar_url(gen.armar_datos(**DATOS_PRUEBA))
    assert url.startswith("https://ejemplo.test/qr/?p=")


def test_import_core_sin_com():
    "Importar el núcleo no debe cargar pythoncom/win32com (clave en Linux/macOS)"
    codigo = (
        "import sys; import pyarcaws.core.qr; "
        "mods = [m for m in sys.modules if m.startswith(('pythoncom', 'win32com'))]; "
        "assert not mods, mods"
    )
    subprocess.run([sys.executable, "-c", codigo], check=True)
