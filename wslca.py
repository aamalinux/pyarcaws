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

"""Módulo para obtener Código de Autorización Electrónica (CAE) de la
Liquidación de Caña de Azúcar (LCA) del web service WSLCA de ARCA (ex AFIP).

Verificado contra el WSDL vivo de homologación
``https://fwshomo.afip.gov.ar/wslca/services/soap?wsdl`` (mismo patrón
``services/soap`` que WSCPE). El esquema es ``unqualified`` (sin
``elementFormDefault``), por lo que aplica el fix de marshalling del
pysimplesoap vendoreado (igual que WSLSP). La autenticación usa
``cuitRepresentada`` (no ``cuit`` como WSLSP).

NOTA: las operaciones de **generación** (``generarLiquidacion`` y ajustes) se
modelaron fielmente contra el WSDL pero **aún no fueron validadas en vivo**
(esta tanda es offline, sin certificado). La superficie de **lectura**
(``Dummy`` + catálogos + consultas) sí tiene tests offline.
"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"
__version__ = "1.00a"

import sys

from pyarcaws.utils import (
    BaseWS,
    inicializar_y_capturar_excepciones,
    get_install_dir,
    normalizar_lista_soap,
    como_lista,
)

LICENCIA = """
wslca.py: Interfaz para generar Código de Autorización Electrónica (CAE) para
          Liquidación de Caña de Azúcar (LcaService)
Copyright (C) 2021 Mariano Reingart reingart@gmail.com

Este programa es software libre, se entrega ABSOLUTAMENTE SIN GARANTIA
y es bienvenido a redistribuirlo respetando la licencia LGPLv3.
"""

AYUDA = """
Opciones:
  --ayuda: este mensaje
  --debug: modo depuración (detalla y confirma las operaciones)
  --dummy: consulta estado de servidores
  --ult: consulta el último número de comprobante (puntoVenta/tipoComprobante)
  --consultar: consulta una liquidación por nro de comprobante
  --provincias / --localidades / --tributos / --tiposcomprobante /
  --puntosventa / --condicionesventa / --mediospago / --otrosconceptos:
       consultan los catálogos correspondientes

Ver wslca.ini para parámetros de configuración (URL, certificados, etc.)
"""

# Homologación; producción: https://serviciosjava.afip.gob.ar/wslca/services/soap?wsdl
WSDL = "https://fwshomo.afip.gov.ar/wslca/services/soap?wsdl"

DEBUG = False
XML = False
CONFIG_FILE = "wslca.ini"
HOMO = False


class WSLCA(BaseWS):
    "Interfaz para el WebService de Liquidación de Caña de Azúcar (WSLCA)"

    _public_methods_ = [
        "Conectar",
        "Dummy",
        "CrearLiquidacion",
        "AgregarDetalle",
        "AgregarOtroConcepto",
        "AgregarTributo",
        "AutorizarLiquidacion",
        "AnalizarLiquidacion",
        "ConsultarLiquidacion",
        "ConsultarUltimoComprobante",
        "ConsultarProvincias",
        "ConsultarLocalidades",
        "ConsultarTiposComprobante",
        "ConsultarTributos",
        "ConsultarPuntosVenta",
        "ConsultarCondicionesVenta",
        "ConsultarMediosPago",
        "ConsultarOtrosConceptos",
        "SetParametros",
        "SetTicketAcceso",
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
        "ErrCode",
        "ErrMsg",
        "Errores",
        "CAE",
        "NroComprobante",
        "FechaComprobante",
        "FechaVencimientoCae",
        "FechaProcesoAFIP",
        "ImporteTotal",
        "datos",
    ]

    _reg_progid_ = "WSLCA"
    _reg_clsid_ = "{A1F4C2D8-7E6B-4A9C-B3D5-2C8E1F90A6B7}"

    # Variables globales para BaseWS:
    HOMO = HOMO
    WSDL = WSDL
    LanzarExcepciones = False
    Version = "%s %s" % (__version__, HOMO and "Homologación" or "")

    def inicializar(self):
        BaseWS.inicializar(self)
        self.AppServerStatus = self.DbServerStatus = self.AuthServerStatus = None
        self.errores = []
        self.Errores = []
        self.ErrCode = self.ErrMsg = ""
        self.CAE = ""
        self.NroComprobante = self.FechaComprobante = ""
        self.FechaVencimientoCae = self.FechaProcesoAFIP = ""
        self.ImporteTotal = None
        self.datos = {}
        # self.solicitud NO se resetea acá: la crea CrearLiquidacion y debe
        # persistir entre las llamadas decoradas del builder (Agregar*), igual
        # que en wslsp. Se inicializa una sola vez al construir.
        if not hasattr(self, "solicitud"):
            self.solicitud = {}

    def __analizar_errores(self, ret):
        "Comprueba y extrae errores si existen en la respuesta XML."
        # <errores><error><codigo/><descripcion/></error>...</errores>
        # pysimplesoap entrega <errores> como dict {'error': {...}} cuando hay
        # un solo <error> y como {'error': [...]} con varios; normalizamos ambas
        # formas con el helper compartido (evita el TypeError clásico).
        errores = normalizar_lista_soap(ret.get("errores"), "error")
        if not errores:
            return
        self.Errores = [
            "%s: %s" % (e.get("codigo", ""), e.get("descripcion", ""))
            for e in errores
        ]
        self.errores = [
            {
                "codigo": e.get("codigo", ""),
                "descripcion": str(e.get("descripcion", ""))
                .replace("\n", "")
                .replace("\r", ""),
            }
            for e in errores
        ]
        self.ErrCode = " ".join([e.get("codigo", "") for e in self.errores])
        self.ErrMsg = "\n".join(self.Errores)

    @property
    def _auth(self):
        "Bloque de autenticación de WSLCA (usa cuitRepresentada, no cuit)."
        return {"token": self.Token, "sign": self.Sign, "cuitRepresentada": self.Cuit}

    @inicializar_y_capturar_excepciones
    def Dummy(self):
        "Obtener el estado de los servidores de ARCA."
        results = self.client.dummy()["respuesta"]
        self.AppServerStatus = str(results["appserver"])
        self.DbServerStatus = str(results["dbserver"])
        self.AuthServerStatus = str(results["authserver"])
        return True

    # --- Generación de liquidaciones (modelado del WSDL, pendiente smoke) -----

    @inicializar_y_capturar_excepciones
    def CrearLiquidacion(
        self,
        punto_venta,
        tipo_comprobante,
        nro_comprobante,
        fecha_comprobante,
        cod_condicion_venta=None,
        cod_medio_pago=None,
        fecha_inicio_actividades=None,
        iibb=None,
        leyenda=None,
        **kwargs
    ):
        "Inicializa internamente los datos de una liquidación para autorizar."
        self.solicitud = {
            "emisor": {
                "comprobante": {
                    "puntoVenta": punto_venta,
                    "tipoComprobante": tipo_comprobante,
                    "nroComprobante": nro_comprobante,
                },
                "fechaInicioActividades": fecha_inicio_actividades,
                "iibb": iibb,
                "leyenda": leyenda,
            },
            "datosGenerales": {
                "fechaComprobante": fecha_comprobante,
                "condicionVenta": {"codigo": cod_condicion_venta},
                "medioPago": {"codigo": cod_medio_pago},
            },
            "detalle": [],
            "otroConcepto": [],
            "tributo": [],
        }
        return True

    @inicializar_y_capturar_excepciones
    def AgregarDetalle(
        self,
        cod_producto,
        cantidad,
        unidad_medida,
        precio_unitario,
        alicuota_iva=None,
        **kwargs
    ):
        "Agrega un renglón de detalle a la liquidación en curso."
        self.solicitud["detalle"].append(
            {
                "producto": cod_producto,
                "cantidad": cantidad,
                "unidadMedida": unidad_medida,
                "precioUnitario": precio_unitario,
                "alicuotaIVA": alicuota_iva,
            }
        )
        return True

    @inicializar_y_capturar_excepciones
    def AgregarOtroConcepto(self, codigo, descripcion=None, importe=None, **kwargs):
        "Agrega un 'otro concepto' a la liquidación en curso."
        self.solicitud["otroConcepto"].append(
            {"codigo": codigo, "descripcion": descripcion, "importe": importe}
        )
        return True

    @inicializar_y_capturar_excepciones
    def AgregarTributo(self, codigo, base_imponible=None, alicuota=None, importe=None, **kwargs):
        "Agrega un tributo a la liquidación en curso."
        self.solicitud["tributo"].append(
            {
                "codigo": codigo,
                "baseImponible": base_imponible,
                "alicuota": alicuota,
                "importe": importe,
            }
        )
        return True

    @inicializar_y_capturar_excepciones
    def AutorizarLiquidacion(self):
        "Envía la liquidación a ARCA para su autorización (generarLiquidacion)."
        ret = self.client.generarLiquidacion(
            auth=self._auth,
            solicitud=self.solicitud,
        )["respuesta"]
        self.__analizar_errores(ret)
        self.AnalizarLiquidacion(ret)
        return True

    def AnalizarLiquidacion(self, ret):
        "Extrae los datos de la respuesta de una liquidación autorizada/consultada."
        self.datos = ret
        cab = ret.get("cabecera", {}) or {}
        aut = ret.get("autorizacion", {}) or ret.get("autorizacionLiquidacion", {}) or {}
        comp = cab.get("comprobante", {}) or ret.get("comprobante", {}) or {}
        if comp:
            self.NroComprobante = comp.get("nroComprobante")
        if aut:
            self.CAE = str(aut.get("cae", "") or "")
            self.FechaVencimientoCae = aut.get("fechaVencimientoCae", "")
            self.FechaProcesoAFIP = aut.get("fechaProcesoAFIP", "")
        self.FechaComprobante = (cab.get("fechaComprobante", "")
                                 or ret.get("fechaComprobante", ""))
        return True

    # --- Consultas ------------------------------------------------------------

    @inicializar_y_capturar_excepciones
    def ConsultarLiquidacion(self, punto_venta, tipo_comprobante, nro_comprobante):
        "Consulta una liquidación registrada en ARCA por nro de comprobante."
        ret = self.client.consultarLiquidacionPorNroComprobante(
            auth=self._auth,
            solicitud={
                "puntoVenta": punto_venta,
                "tipoComprobante": tipo_comprobante,
                "nroComprobante": nro_comprobante,
            },
        )["respuesta"]
        self.__analizar_errores(ret)
        self.AnalizarLiquidacion(ret)
        return True

    @inicializar_y_capturar_excepciones
    def ConsultarUltimoComprobante(self, punto_venta, tipo_comprobante):
        "Consulta el último número de comprobante para un punto de venta/tipo."
        ret = self.client.consultarUltimoNroComprobantePorPtoVta(
            auth=self._auth,
            solicitud={
                "puntoVenta": punto_venta,
                "tipoComprobante": tipo_comprobante,
            },
        )["respuesta"]
        self.__analizar_errores(ret)
        self.NroComprobante = ret.get("nroComprobante")
        return self.NroComprobante

    # --- Catálogos ------------------------------------------------------------

    def _consultar_catalogo(self, operation, key, sep="||", **solicitud):
        "Helper genérico para los catálogos código/descripción de WSLCA."
        kwargs = {"auth": self._auth}
        if solicitud:
            kwargs["solicitud"] = solicitud
        ret = getattr(self.client, operation)(**kwargs)["respuesta"]
        self.__analizar_errores(ret)
        array = como_lista(ret.get(key))
        if sep is None:
            return dict([(it["codigo"], it["descripcion"]) for it in array])
        return [
            ("%s %%s %s %%s %s" % (sep, sep, sep)) % (it["codigo"], it["descripcion"])
            for it in array
        ]

    @inicializar_y_capturar_excepciones
    def ConsultarProvincias(self, sep="||"):
        "Consulta las provincias habilitadas."
        return self._consultar_catalogo("consultarProvincias", "provincia", sep)

    @inicializar_y_capturar_excepciones
    def ConsultarLocalidades(self, cod_provincia, sep="||"):
        "Consulta las localidades habilitadas para una provincia."
        return self._consultar_catalogo(
            "consultarLocalidadesPorProvincia", "localidad", sep,
            codProvincia=cod_provincia,
        )

    @inicializar_y_capturar_excepciones
    def ConsultarTiposComprobante(self, sep="||"):
        "Consulta los tipos de comprobante habilitados."
        return self._consultar_catalogo(
            "consultarTiposComprobante", "tipoComprobante", sep
        )

    @inicializar_y_capturar_excepciones
    def ConsultarTributos(self, sep="||"):
        "Consulta los tipos de tributo habilitados."
        return self._consultar_catalogo("consultarTributos", "tributo", sep)

    @inicializar_y_capturar_excepciones
    def ConsultarPuntosVenta(self, sep="||"):
        "Consulta los puntos de venta habilitados."
        return self._consultar_catalogo("consultarPuntosVenta", "puntoVenta", sep)

    @inicializar_y_capturar_excepciones
    def ConsultarCondicionesVenta(self, sep="||"):
        "Consulta las condiciones de venta habilitadas."
        return self._consultar_catalogo(
            "consultarCondicionesVenta", "condicionVenta", sep
        )

    @inicializar_y_capturar_excepciones
    def ConsultarMediosPago(self, sep="||"):
        "Consulta los medios de pago habilitados."
        return self._consultar_catalogo("consultarMediosPago", "medioPago", sep)

    @inicializar_y_capturar_excepciones
    def ConsultarOtrosConceptos(self, sep="||"):
        "Consulta los otros conceptos habilitados."
        return self._consultar_catalogo("consultarOtrosConceptos", "otroConcepto", sep)


# busco el directorio de instalación (global para que no cambie si usan otra dll)
INSTALL_DIR = WSLCA.InstallDir = get_install_dir()

LiquidacionCanaAzucar = WSLCA  # alias descriptivo


def main():
    "Función principal de pruebas (no autoriza nada sin certificado)."
    DEBUG = "--debug" in sys.argv

    if "--ayuda" in sys.argv:
        print(LICENCIA)
        print(AYUDA)
        return

    from configparser import ConfigParser

    config = ConfigParser()
    config.read(CONFIG_FILE)
    if config.has_section("WSAA"):
        crt = config.get("WSAA", "CERT")
        key = config.get("WSAA", "PRIVATEKEY")
        cuit = config.get("WSLCA", "CUIT")
    else:
        crt, key = "reingart.crt", "reingart.key"
        cuit = "20267565393"
    url_wsaa = config.get("WSAA", "URL", fallback=None) if config.has_section("WSAA") else None

    from pyarcaws.wsaa import WSAA

    wsaa = WSAA()
    ta = wsaa.Autenticar("wslca", crt, key, url_wsaa)
    if DEBUG:
        print("WSAA.Excepcion:", wsaa.Excepcion)

    wslca = WSLCA()
    wslca.SetTicketAcceso(ta)
    wslca.Cuit = cuit
    wslca.Conectar(cacert="conf/afip_ca_info.crt")

    if "--dummy" in sys.argv:
        wslca.Dummy()
        print("AppServerStatus", wslca.AppServerStatus)
        print("DbServerStatus", wslca.DbServerStatus)
        print("AuthServerStatus", wslca.AuthServerStatus)

    if "--provincias" in sys.argv:
        print("\n".join(wslca.ConsultarProvincias()))
    if "--tributos" in sys.argv:
        print("\n".join(wslca.ConsultarTributos()))
    if "--tiposcomprobante" in sys.argv:
        print("\n".join(wslca.ConsultarTiposComprobante()))
    if "--puntosventa" in sys.argv:
        print("\n".join(wslca.ConsultarPuntosVenta()))
    if "--condicionesventa" in sys.argv:
        print("\n".join(wslca.ConsultarCondicionesVenta()))
    if "--mediospago" in sys.argv:
        print("\n".join(wslca.ConsultarMediosPago()))
    if "--otrosconceptos" in sys.argv:
        print("\n".join(wslca.ConsultarOtrosConceptos()))

    if wslca.Excepcion:
        print("Excepcion:", wslca.Excepcion)
    return wslca


if __name__ == "__main__":
    if "--register" in sys.argv or "--unregister" in sys.argv:
        import win32com.server.register

        win32com.server.register.UseCommandLine(WSLCA)
    else:
        main()
