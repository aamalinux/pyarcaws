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

"""Módulo para generar códigos QR (interfaz COM y CLI).

La lógica de negocio vive en ``pyarcaws.core.qr`` (Python puro, sin COM);
este módulo conserva la clase ``PyQR`` con su interfaz histórica (métodos
CamelCase, atributos ``Excepcion``/``Traceback``, registro COM en Windows)
y el ``main()`` de línea de comandos.
"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2020-2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"
__version__ = "3.05b"

import base64
import json
import os
import sys
import traceback

from pyarcaws.core import qr as core_qr


TEST_QR_DATA = """
eyJ2ZXIiOjEsImZlY2hhIjoiMjAyMC0xMC0xMyIsImN1aXQiOjMwMDAwMDAwMDA3LCJwdG9WdGEiOj
EwLCJ0aXBvQ21wIjoxLCJucm9DbXAiOjk0LCJpbXBvcnRlIjoxMjEwMCwibW9uZWRhIjoiRE9MIiwi
Y3R6Ijo2NSwidGlwb0RvY1JlYyI6ODAsIm5yb0RvY1JlYyI6MjAwMDAwMDAwMDEsInRpcG9Db2RBdX
QiOiJFIiwiY29kQXV0Ijo3MDQxNzA1NDM2NzQ3Nn0=""".replace(
    "\n", ""
)

TYPELIB = False


class PyQR:
    "Interfaz para generar Codigo QR de Factura Electrónica"
    _public_methods_ = [
        "GenerarImagen",
        "CrearArchivo",
    ]
    _public_attrs_ = [
        "Version",
        "Excepcion",
        "Traceback",
        "URL",
        "Archivo",
        "Extension",
        "InstallDir",
        "qr_ver",
        "box_size",
        "border",
        "error_correction",
    ]

    _reg_progid_ = "PyQR"
    _reg_clsid_ = "{B176B1CE-E7B5-4BB2-ADEC-9EB9F249DF07}"

    if TYPELIB:
        _typelib_guid_ = '{418C11BF-1051-4B51-95CE-638DC3686634}'
        _typelib_version_ = 1, 5
        _com_interfaces_ = ['IPyQR']

    URL = core_qr.URL_TEMPLATE
    Archivo = "qr.png"
    Extension = "PNG"

    # qrencode default parameters:
    qr_ver = core_qr.DEFAULT_QR_VER
    box_size = core_qr.DEFAULT_BOX_SIZE
    border = core_qr.DEFAULT_BORDER
    error_correction = core_qr.DEFAULT_ERROR_CORRECTION

    def __init__(self):
        self.Version = __version__
        self.Excepcion = self.Traceback = ""

    def _capturar_excepcion(self, e):
        "Vuelca la excepción a los atributos que espera la interfaz COM"
        self.Excepcion = traceback.format_exception_only(type(e), e)[0].strip()
        self.Traceback = traceback.format_exc()

    def CrearArchivo(self):
        """Crea un nombre de archivo temporal"""
        # para evitar errores de permisos y poder generar varios qr simultaneos
        try:
            self.Archivo = core_qr.crear_archivo_temporal(self.Extension)
            return self.Archivo
        except Exception as e:
            self._capturar_excepcion(e)
            raise

    def GenerarImagen(
        self,
        ver=1,
        fecha="2020-10-13",
        cuit=30000000007,
        pto_vta=10,
        tipo_cmp=1,
        nro_cmp=94,
        importe=12100,
        moneda="PES",
        ctz=1.000,
        tipo_doc_rec=80,
        nro_doc_rec=20000000001,
        tipo_cod_aut="E",
        cod_aut=70417054367476,
        color_relleno="black",
        color_fondo="white",
    ):
        "Generar una imágen con el código QR"
        # basado en: https://www.afip.gob.ar/fe/qr/especificaciones.asp
        try:
            generador = core_qr.QRGenerator(
                url_template=self.URL,
                qr_ver=self.qr_ver,
                box_size=self.box_size,
                border=self.border,
                error_correction=self.error_correction,
            )
            return generador.generar_qr(
                self.Archivo,
                self.Extension,
                color_relleno,
                color_fondo,
                ver=ver,
                fecha=fecha,
                cuit=cuit,
                pto_vta=pto_vta,
                tipo_cmp=tipo_cmp,
                nro_cmp=nro_cmp,
                importe=importe,
                moneda=moneda,
                ctz=ctz,
                tipo_doc_rec=tipo_doc_rec,
                nro_doc_rec=nro_doc_rec,
                tipo_cod_aut=tipo_cod_aut,
                cod_aut=cod_aut,
            )
        except Exception as e:
            self._capturar_excepcion(e)
            raise


from pyarcaws.utils import get_install_dir
INSTALL_DIR = PyQR.InstallDir = get_install_dir()


def registrar_com():
    "Registra/desregistra el servidor COM en Windows (import diferido de pywin32)"
    import pythoncom

    if TYPELIB:
        if '--register' in sys.argv:
            tlb = os.path.abspath(os.path.join(INSTALL_DIR, "typelib", "pyqr.tlb"))
            print("Registering %s" % (tlb, ))
            tli = pythoncom.LoadTypeLib(tlb)
            pythoncom.RegisterTypeLib(tli, tlb)
        elif '--unregister' in sys.argv:
            k = PyQR
            pythoncom.UnRegisterTypeLib(k._typelib_guid_,
                                        k._typelib_version_[0],
                                        k._typelib_version_[1],
                                        0,
                                        pythoncom.SYS_WIN32)
            print("Unregistered typelib")
    import win32com.server.register

    win32com.server.register.UseCommandLine(PyQR)


def servir_automate():
    "Atiende las class factories COM (flag /Automate de Windows)"
    # MS seems to like /automate to run the class factories.
    import win32com.server.localserver

    win32com.server.localserver.serve([PyQR._reg_clsid_])


def main():
    url = None
    if "--register" in sys.argv or "--unregister" in sys.argv:
        registrar_com()
    elif "/Automate" in sys.argv:
        servir_automate()
    else:

        pyqr = PyQR()

        if "--datos" in sys.argv:
            args = sys.argv[sys.argv.index("--datos") + 1 :]
            (
                ver,
                fecha,
                cuit,
                pto_vta,
                tipo_cmp,
                nro_cmp,
                importe,
                moneda,
                ctz,
                tipo_doc_rec,
                nro_doc_rec,
                tipo_cod_aut,
                cod_aut
            ) = args
        else:
            ver = 1
            fecha = "2020-10-13"
            cuit = 30000000007
            pto_vta = 10
            tipo_cmp = 1
            nro_cmp = 94
            importe = 12100
            moneda = "DOL"
            ctz = 65.000
            tipo_doc_rec = 80
            nro_doc_rec = 20000000001
            tipo_cod_aut = "E"
            cod_aut = 70417054367476

        if "--archivo" in sys.argv:
            pyqr.Archivo = sys.argv[sys.argv.index("--archivo") + 1]
            ext = os.path.splitext(pyqr.Archivo)[1][1:].upper()
            if ext == "JPG":
                ext = "JPEG"
            PyQR.Extension = ext
        else:
            pyqr.CrearArchivo()

        if "--size" in sys.argv:
            pyqr.box_size = int(sys.argv[sys.argv.index("--size") + 1])

        if "--border" in sys.argv:
            pyqr.border = int(sys.argv[sys.argv.index("--border") + 1])

        if "--url" in sys.argv:
            pyqr.URL = sys.argv[sys.argv.index("--url") + 1]

        print(
            "datos:",
            (
                ver,
                fecha,
                cuit,
                pto_vta,
                tipo_cmp,
                nro_cmp,
                importe,
                moneda,
                ctz,
                tipo_doc_rec,
                nro_doc_rec,
                tipo_cod_aut,
                cod_aut,
            ),
        )
        print("archivo", pyqr.Archivo)
        print("extension", pyqr.Extension)

        url = pyqr.GenerarImagen(
            ver,
            fecha,
            cuit,
            pto_vta,
            tipo_cmp,
            nro_cmp,
            importe,
            moneda,
            ctz,
            tipo_doc_rec,
            nro_doc_rec,
            tipo_cod_aut,
            cod_aut,
        )

        print("url generada:", url)

        if "--prueba" in sys.argv:
            qr_data_test = json.loads(base64.b64decode(TEST_QR_DATA))
            qr_data_gen = json.loads(base64.b64decode(url[33:]))
            assert url.startswith("https://www.afip.gob.ar/fe/qr/?p=")
            assert qr_data_test == qr_data_gen, "Diff: %r != %r" % (
                qr_data_test,
                qr_data_gen,
            )
            print("QR data ok:", qr_data_gen)

        if not "--mostrar" in sys.argv:
            pass
        elif sys.platform == "linux2" or sys.platform == "linux":
            os.system("eog " "%s" "" % pyqr.Archivo)
        else:
            os.startfile(pyqr.Archivo)

    return url

if __name__ == "__main__":
    main()
