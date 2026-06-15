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

"""Módulo para consultar el registro de **facturas/contribuyentes apócrifos**
(base APOC) de ARCA (ex AFIP) mediante el web service WSAPOC.

Verificado contra el WSDL vivo de homologación
``https://eapoc-ws-qaext.afip.gob.ar/Service.asmx?WSDL`` (servicio .NET asmx,
esquema ``qualified``). Servicio WSAA a autorizar: ``wsapoc``. La autenticación
va en un objeto ``Credencial`` con ``Token``, ``Sign`` y **``CUITDelegado``**
(el CUIT autenticado) — no ``cuit``/``cuitRepresentada`` como otros servicios.

Operaciones del WSDL:
- ``Dummy`` → estado de servidores.
- ``GetPublicacionAPOC(Credencial, cuit)`` → consulta si un CUIT está en la
  base de apócrifos (caso de uso de validación de proveedores).
- ``GetAll(Credencial)`` → la base completa de apócrifos.
- ``GetAllByPublicacion(Credencial, desde, hasta)`` → por rango de publicación.

Cada respuesta es un ``MessageResponse`` con ``codigo``/``descripcion`` y una
lista ``resultados`` de ``PublicacionAPOC`` (Cuit, Descripcion, FechaCondicion,
FechaPublicacion).
"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"
__version__ = "1.00a"

import sys

from pyarcaws.utils import (
    inicializar_y_capturar_excepciones,
    BaseWS,
    get_install_dir,
    como_lista,
)

# Homologación; producción: https://eapoc-ws.afip.gob.ar/service.asmx?WSDL
WSDL = "https://eapoc-ws-qaext.afip.gob.ar/Service.asmx?WSDL"

HOMO = False
CONFIG_FILE = "wsapoc.ini"


class WSAPOC(BaseWS):
    "Interfaz para el WebService de consulta de apócrifos (base APOC) de ARCA"

    _public_methods_ = [
        "Conectar",
        "Dummy",
        "Consultar",
        "ConsultarTodos",
        "ConsultarPorPublicacion",
        "SetTicketAcceso",
        "SetParametros",
        "GetParametro",
        "AnalizarXml",
        "ObtenerTagXml",
        "LoadTestXML",
        "DebugLog",
    ]
    _public_attrs_ = [
        "Token",
        "Sign",
        "Cuit",
        "AppServerStatus",
        "DbServerStatus",
        "AuthServerStatus",
        "XmlRequest",
        "XmlResponse",
        "Version",
        "InstallDir",
        "Excepcion",
        "Traceback",
        "LanzarExcepciones",
        "CodigoRespuesta",
        "MensajeRespuesta",
        "EsApocrifo",
        "resultados",
    ]

    _reg_progid_ = "WSAPOC"
    _reg_clsid_ = "{B7E3F1A9-5C24-4D8E-9A16-3F70C2E84B5D}"

    HOMO = HOMO
    WSDL = WSDL
    Version = "%s %s" % (__version__, HOMO and "Homologación" or "")
    LanzarExcepciones = False

    def inicializar(self):
        BaseWS.inicializar(self)
        self.AppServerStatus = self.DbServerStatus = self.AuthServerStatus = None
        self.CodigoRespuesta = ""
        self.MensajeRespuesta = ""
        self.EsApocrifo = None
        self.resultados = []

    @property
    def _cred(self):
        "Credencial de WSAPOC: Token, Sign y CUITDelegado (el CUIT autenticado)."
        return {"Token": self.Token, "Sign": self.Sign, "CUITDelegado": self.Cuit}

    def __analizar_respuesta(self, ret):
        "Extrae codigo/descripcion y la lista de PublicacionAPOC de un MessageResponse."
        ret = ret or {}
        self.CodigoRespuesta = ret.get("codigo", "")
        self.MensajeRespuesta = ret.get("descripcion", "")
        # <resultados><PublicacionAPOC>...</PublicacionAPOC>...</resultados>
        # pysimplesoap entrega un único elemento como dict (no lista): aplanar.
        arr = ret.get("resultados") or {}
        if isinstance(arr, dict):
            publicaciones = como_lista(arr.get("PublicacionAPOC"))
        else:
            publicaciones = como_lista(arr)
        self.resultados = [
            {
                "cuit": p.get("Cuit"),
                "descripcion": p.get("Descripcion"),
                "fecha_condicion": p.get("FechaCondicion"),
                "fecha_publicacion": p.get("FechaPublicacion"),
            }
            for p in publicaciones
        ]
        return self.resultados

    @inicializar_y_capturar_excepciones
    def Dummy(self):
        "Obtener el estado de los servidores de ARCA."
        result = self.client.Dummy()["DummyResult"]
        self.AppServerStatus = result.get("appserver")
        self.DbServerStatus = result.get("dbserver")
        self.AuthServerStatus = result.get("authserver")
        return True

    @inicializar_y_capturar_excepciones
    def Consultar(self, cuit):
        "Consulta si un CUIT está en la base de apócrifos (GetPublicacionAPOC)."
        ret = self.client.GetPublicacionAPOC(
            Credencial=self._cred,
            cuit=cuit,
        )["GetPublicacionAPOCResult"]
        self.__analizar_respuesta(ret)
        # apócrifo si la base devolvió al menos una publicación para el CUIT
        self.EsApocrifo = bool(self.resultados)
        return True

    @inicializar_y_capturar_excepciones
    def ConsultarTodos(self):
        "Devuelve la base completa de apócrifos (GetAll). Puede ser grande."
        ret = self.client.GetAll(Credencial=self._cred)["GetAllResult"]
        self.__analizar_respuesta(ret)
        return True

    @inicializar_y_capturar_excepciones
    def ConsultarPorPublicacion(self, desde, hasta):
        "Apócrifos por rango de fecha de publicación (GetAllByPublicacion)."
        ret = self.client.GetAllByPublicacion(
            Credencial=self._cred,
            desde=desde,
            hasta=hasta,
        )["GetAllByPublicacionResult"]
        self.__analizar_respuesta(ret)
        return True


# busco el directorio de instalación (global para que no cambie si usan otra dll)
INSTALL_DIR = WSAPOC.InstallDir = get_install_dir()

Apocrifos = WSAPOC  # alias descriptivo


def main():
    "Función principal de pruebas (requiere certificado autorizado a wsapoc)."
    DEBUG = "--debug" in sys.argv

    if "--ayuda" in sys.argv:
        print(__doc__)
        return

    from configparser import ConfigParser

    config = ConfigParser()
    config.read(CONFIG_FILE)
    if config.has_section("WSAA"):
        crt = config.get("WSAA", "CERT")
        key = config.get("WSAA", "PRIVATEKEY")
        cuit = config.get("WSAPOC", "CUIT")
    else:
        crt, key = "reingart.crt", "reingart.key"
        cuit = "20267565393"
    url_wsaa = config.get("WSAA", "URL", fallback=None) if config.has_section("WSAA") else None

    from pyarcaws.wsaa import WSAA

    wsaa = WSAA()
    ta = wsaa.Autenticar("wsapoc", crt, key, url_wsaa)
    if DEBUG:
        print("WSAA.Excepcion:", wsaa.Excepcion)

    wsapoc = WSAPOC()
    wsapoc.SetTicketAcceso(ta)
    wsapoc.Cuit = cuit
    wsapoc.Conectar()

    if "--dummy" in sys.argv:
        wsapoc.Dummy()
        print("AppServerStatus", wsapoc.AppServerStatus)
        print("DbServerStatus", wsapoc.DbServerStatus)
        print("AuthServerStatus", wsapoc.AuthServerStatus)

    if "--consultar" in sys.argv:
        cuit_consulta = sys.argv[sys.argv.index("--consultar") + 1]
        wsapoc.Consultar(cuit_consulta)
        print("Codigo:", wsapoc.CodigoRespuesta, "| Mensaje:", wsapoc.MensajeRespuesta)
        print("Es apócrifo:", wsapoc.EsApocrifo)
        print("Resultados:", wsapoc.resultados)

    if wsapoc.Excepcion:
        print("Excepcion:", wsapoc.Excepcion)
    return wsapoc


if __name__ == "__main__":
    if "--register" in sys.argv or "--unregister" in sys.argv:
        import win32com.server.register

        win32com.server.register.UseCommandLine(WSAPOC)
    else:
        main()
