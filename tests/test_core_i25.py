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

"""Tests del núcleo puro pyarcaws.core.i25 (sin red ni COM)"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2011-2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"

import os
import subprocess
import sys

import pytest
from PIL import Image, ImageChops

from pyarcaws.core.i25 import (
    calcular_ancho,
    digito_verificador_modulo10,
    generar_imagen,
)

pytestmark = [pytest.mark.dontusefix]

# código de barras de ejemplo (CUIT + tipo + pto vta + CAE + vencimiento + DV)
BARRAS = "2026756539302400161203034739042201105299"


def test_digito_verificador_modulo10():
    "El dígito verificador coincide con el histórico"
    assert digito_verificador_modulo10(BARRAS[:-1]) == "9"


def test_digito_verificador_entrada_invalida():
    "Entradas vacías o no numéricas devuelven cadena vacía"
    assert digito_verificador_modulo10("") == ""
    assert digito_verificador_modulo10("   ") == ""
    assert digito_verificador_modulo10("12a4") == ""


def test_generar_imagen_igual_a_referencia(tmp_path):
    "La imagen generada es idéntica a la de referencia del repo"
    archivo = str(tmp_path / "barras.png")
    generar_imagen(BARRAS, archivo)
    ref = Image.open("tests/images/prueba-cae-i25.png")
    test = Image.open(archivo)
    assert ImageChops.difference(ref, test).getbbox() is None


def test_generar_imagen_jpeg(tmp_path):
    "La imagen JPEG se crea y respeta el formato"
    archivo = str(tmp_path / "barras.jpg")
    generar_imagen(BARRAS, archivo, extension="JPEG")
    assert os.path.getsize(archivo) > 0
    with open(archivo, "rb") as f:
        assert f.read(2) == b"\xff\xd8"  # cabecera JPEG


def test_ancho_automatico():
    "El ancho automático replica la fórmula histórica y se usa al generar"
    assert calcular_ancho(BARRAS) == len(BARRAS) * 3 * 3 + 10 * 1


def test_codigo_impar_se_rellena(tmp_path):
    "Un código de largo impar se rellena con 0 (mismo ancho que el par equivalente)"
    impar = BARRAS[1:]  # 39 dígitos
    assert calcular_ancho(impar) == calcular_ancho("0" + impar)
    archivo_impar = str(tmp_path / "impar.png")
    archivo_par = str(tmp_path / "par.png")
    generar_imagen(impar, archivo_impar)
    generar_imagen("0" + impar, archivo_par)
    a = Image.open(archivo_impar)
    b = Image.open(archivo_par)
    assert ImageChops.difference(a, b).getbbox() is None


def test_ancho_y_alto_explicitos(tmp_path):
    "width/height explícitos definen el tamaño de la imagen"
    archivo = str(tmp_path / "fijo.png")
    generar_imagen(BARRAS, archivo, width=500, height=50)
    im = Image.open(archivo)
    assert im.size == (500, 50)


def test_import_core_sin_com():
    "Importar el núcleo no debe cargar pythoncom/win32com (clave en Linux/macOS)"
    codigo = (
        "import sys; import pyarcaws.core.i25; "
        "mods = [m for m in sys.modules if m.startswith(('pythoncom', 'win32com'))]; "
        "assert not mods, mods"
    )
    subprocess.run([sys.executable, "-c", codigo], check=True)
