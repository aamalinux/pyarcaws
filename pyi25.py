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

"""Módulo para generar códigos de barra en Entrelazado 2 de 5 (I25).

La lógica de negocio vive en ``pyarcaws.core.i25`` (Python puro, sin COM);
este módulo conserva la clase ``PyI25`` con su interfaz histórica (métodos
CamelCase, atributos ``Excepcion``/``Traceback``, registro COM en Windows)
y el ``main()`` de línea de comandos.
"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2011-2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"
__version__ = "3.02e"

import os
import sys
import traceback

from pyarcaws.core import i25 as core_i25


class PyI25:
    "Interfaz para generar PDF de Factura Electrónica"
    _public_methods_ = ["GenerarImagen", "DigitoVerificadorModulo10"]
    _public_attrs_ = ["Version", "Excepcion", "Traceback"]

    _reg_progid_ = "PyI25"
    _reg_clsid_ = "{5E6989E8-F658-49FB-8C39-97C74BC67650}"

    def __init__(self):
        self.Version = __version__
        self.Excepcion = self.Traceback = ""

    def _capturar_excepcion(self, e):
        "Vuelca la excepción a los atributos que espera la interfaz COM"
        self.Excepcion = traceback.format_exception_only(type(e), e)[0].strip()
        self.Traceback = traceback.format_exc()

    def GenerarImagen(
        self,
        codigo,
        archivo="barras.png",
        basewidth=3,
        width=None,
        height=30,
        extension="PNG",
    ):
        "Generar una imágen con el código de barras Interleaved 2 of 5"
        try:
            if not width:
                width = core_i25.calcular_ancho(codigo, basewidth)
                print(width)
            core_i25.generar_imagen(codigo, archivo, basewidth, width, height, extension)
            return True
        except Exception as e:
            self._capturar_excepcion(e)
            raise

    def DigitoVerificadorModulo10(self, codigo):
        "Rutina para el cálculo del dígito verificador 'módulo 10'"
        try:
            return core_i25.digito_verificador_modulo10(codigo)
        except Exception as e:
            self._capturar_excepcion(e)
            raise


def registrar_com():
    "Registra/desregistra el servidor COM en Windows (import diferido de pywin32)"
    import win32com.server.register

    win32com.server.register.UseCommandLine(PyI25)


def servir_automate():
    "Atiende las class factories COM (flag /Automate de Windows)"
    # MS seems to like /automate to run the class factories.
    import win32com.server.localserver

    win32com.server.localserver.serve([PyI25._reg_clsid_])


def empaquetar_py2exe():
    "Empaqueta el módulo como ejecutable/DLL de Windows (import diferido de py2exe)"
    from setuptools import setup
    from pyarcaws.windows.nsis import build_installer, Target
    import py2exe
    import glob

    VCREDIST = (
        ".",
        glob.glob(r"c:\Program Files\Mercurial\mfc*.*")
        + glob.glob(r"c:\Program Files\Mercurial\Microsoft.VC90.CRT.manifest"),
    )
    setup(
        name="PyI25",
        version=__version__,
        description="Interfaz pyarcaws I25 %s",
        long_description=__doc__,
        author="Mariano Reingart",
        author_email="reingart@gmail.com",
        url="http://www.sistemasagiles.com.ar",
        license="GNU GPL v3",
        com_server=[
            {"modules": "pyi25", "create_exe": True, "create_dll": True},
        ],
        console=[
            Target(
                module=sys.modules[__name__],
                script="pyi25.py",
                dest_base="pyi25_cli",
            )
        ],
        windows=[
            Target(
                module=sys.modules[__name__],
                script="pyi25.py",
                dest_base="pyi25_win",
            )
        ],
        options={
            "py2exe": {
                "includes": [],
                "optimize": 2,
                "excludes": [
                    "pywin",
                    "pywin.dialogs",
                    "pywin.dialogs.list",
                    "win32ui",
                    "distutils.core",
                    "py2exe",
                    "nsis",
                ],
                #'skip_archive': True,
            }
        },
        data_files=[
            VCREDIST,
            (".", ["licencia.txt"]),
        ],
        cmdclass={"py2exe": build_installer},
    )


def main():

    if "--register" in sys.argv or "--unregister" in sys.argv:
        registrar_com()
    elif "/Automate" in sys.argv:
        servir_automate()
    elif "py2exe" in sys.argv:
        empaquetar_py2exe()
    else:

        pyi25 = PyI25()

        if "--barras" in sys.argv:
            barras = sys.argv[sys.argv.index("--barras") + 1]
        else:
            cuit = 20267565393
            tipo_cbte = 2
            punto_vta = 4001
            cae = 61203034739042
            fch_venc_cae = 20110529

            # codigo de barras de ejemplo:
            barras = "%11s%02d%04d%s%8s" % (
                cuit,
                tipo_cbte,
                punto_vta,
                cae,
                fch_venc_cae,
            )

        if not "--noverificador" in sys.argv:
            barras = barras + pyi25.DigitoVerificadorModulo10(barras)

        if "--archivo" in sys.argv:
            archivo = sys.argv[sys.argv.index("--archivo") + 1]
            extension = os.path.splitext(archivo)[1]
            extension = extension.upper()[1:]
            if extension == "JPG":
                extension = "JPEG"
        else:
            archivo = "prueba-cae-i25.png"
            extension = "PNG"

        print("barras", barras)
        print("archivo", archivo)
        pyi25.GenerarImagen(barras, archivo, extension=extension)

        if not "--mostrar" in sys.argv:
            pass
        elif sys.platform == "linux2" or sys.platform == "linux":
            os.system("eog " "%s" "" % archivo)
        else:
            os.startfile(archivo)

if __name__ == "__main__":
    main()
