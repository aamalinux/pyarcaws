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

"""Parser OFFLINE de padrones de alícuotas de Ingresos Brutos (ARBA y AGIP).

Regímenes generales de percepción/retención de IIBB. Lee los archivos de padrón
(ZIP o TXT, encoding latin-1, campos separados por ``;``) y permite consultar la
alícuota por CUIT. **Sin red, sin credenciales, sin WSAA**: es lectura de
archivos.

NO confundir con:
  - ``iibb.py``: web service DFE de ARBA (consulta *online*, con credenciales).
  - ``padron.py``: padrón de contribuyentes de ARCA (ex AFIP), otro organismo.

Formatos soportados (layout confirmado contra los PDF oficiales de diseño de
registro de ARBA y AGIP):

  - **ARBA — "Régimen de Recaudación por Sujeto"**: dos archivos por ZIP,
    ``PadronRGSRetMMAAAA.txt`` (retención) y ``PadronRGSPerMMAAAA.txt``
    (percepción). Cada archivo trae UNA alícuota; el campo *Régimen* (``R``/``P``)
    la identifica. Se fusionan por CUIT. El padrón ARBA **no trae razón social**.

  - **AGIP — "Padrón Unificado"** (contribuyentes exentos / alícuotas
    diferenciales): un único archivo con AMBAS alícuotas (percepción y retención)
    por CUIT, más la razón social.

Las alícuotas vienen en formato ``9,99`` (coma decimal); las fechas en
``DDMMAAAA``. Una consulta de un CUIT que no está en el padrón devuelve ``None``
(nunca una alícuota 0, que es un valor válido distinto).
"""

import argparse
import datetime
import logging
import os
import re
import zipfile

__author__ = "pyarcaws (aamalinux)"
__copyright__ = "Copyright (C) 2026 pyarcaws"
__license__ = "LGPL-3.0-or-later"
__version__ = "1.0.0"

logger = logging.getLogger(__name__)

ARBA = "ARBA"
AGIP = "AGIP"

# Índices de campo (tras separar la línea por ';'), según los diseños oficiales.
# ARBA "Régimen de Recaudación por Sujeto" (10 campos, sin razón social):
_ARBA_REGIMEN = 0          # 'R' retención / 'P' percepción
_ARBA_VIG_DESDE = 2
_ARBA_VIG_HASTA = 3
_ARBA_CUIT = 4
_ARBA_TIPO_CONTRIB = 5     # 'C' Convenio Multilateral / 'D' Directo Pcia Bs.As.
_ARBA_MARCA_ALTA_BAJA = 6  # 'S' alta / 'B' baja
_ARBA_ALICUOTA = 8
_ARBA_GRUPO = 9
# AGIP "Padrón Unificado" (12 campos, con razón social):
_AGIP_VIG_DESDE = 1
_AGIP_VIG_HASTA = 2
_AGIP_CUIT = 3
_AGIP_TIPO_CONTRIB = 4
_AGIP_MARCA_ALTA = 5
_AGIP_ALIC_PERCEPCION = 7
_AGIP_ALIC_RETENCION = 8
_AGIP_GRUPO_PERCEPCION = 9
_AGIP_GRUPO_RETENCION = 10
_AGIP_RAZON_SOCIAL = 11


def _alicuota(valor):
    "Convierte '9,99' (coma decimal) a float. Vacío/ inválido -> None."
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def _fecha(valor):
    "Convierte 'DDMMAAAA' a datetime.date. Vacío/ inválido -> None."
    valor = (valor or "").strip()
    if len(valor) != 8 or not valor.isdigit():
        return None
    try:
        return datetime.date(int(valor[4:8]), int(valor[2:4]), int(valor[0:2]))
    except ValueError:
        return None


def _normalizar_cuit(cuit):
    "Deja sólo los dígitos del CUIT (acepta int, o str con guiones/espacios)."
    return re.sub(r"\D", "", str(cuit))


def _registro(cuit, jurisdiccion):
    "Registro normalizado vacío para un CUIT."
    return {
        "cuit": cuit,
        "jurisdiccion": jurisdiccion,
        "regimen_tipo_contribuyente": None,  # 'C' | 'D' | None
        "alicuota_percepcion": None,
        "alicuota_retencion": None,
        "grupo_percepcion": None,
        "grupo_retencion": None,
        "vigencia_desde": None,
        "vigencia_hasta": None,
        "razon_social": "",
        "marca_alta_baja": "",
    }


class PadronIIBB(object):
    "Parser/índice de padrones de alícuotas IIBB (ARBA / AGIP)."

    def __init__(self):
        self.registros = {}        # cuit (str de 11 dígitos) -> dict normalizado
        self.jurisdiccion = None   # 'ARBA' | 'AGIP' tras Cargar()

    # -- carga -------------------------------------------------------------

    def Cargar(self, ruta):
        """Carga un padrón desde un ZIP o un TXT.

        Detecta el formato por el nombre del archivo (``PadronRGS*`` = ARBA) y,
        si no, por la estructura del primer registro. Para ARBA fusiona los
        archivos de retención y percepción en un único registro por CUIT.

        Devuelve la cantidad de registros (CUIT) cargados.
        """
        archivos = self._leer_archivos(ruta)
        self.jurisdiccion = self._detectar_formato(archivos)
        parsear = (
            self._parsear_linea_arba
            if self.jurisdiccion == ARBA
            else self._parsear_linea_agip
        )
        for nombre, contenido in archivos:
            for nro, linea in enumerate(contenido.splitlines(), 1):
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    parsear(linea)
                except Exception as e:
                    # registro malformado / encabezado: log y seguir
                    logger.warning(
                        "padron_iibb: línea %d de %s ignorada (%s): %r",
                        nro, nombre, e, linea[:60],
                    )
        return len(self.registros)

    def _leer_archivos(self, ruta):
        "Devuelve [(nombre, contenido_str_latin1), ...] de un ZIP o un TXT."
        if zipfile.is_zipfile(ruta):
            with zipfile.ZipFile(ruta) as zf:
                return [
                    (nombre, zf.read(nombre).decode("latin-1"))
                    for nombre in zf.namelist()
                    if nombre.lower().endswith(".txt")
                ]
        with open(ruta, "rb") as f:
            return [(os.path.basename(ruta), f.read().decode("latin-1"))]

    def _detectar_formato(self, archivos):
        "ARBA si hay un archivo PadronRGS*; si no, por estructura del 1er registro."
        nombres = " ".join(os.path.basename(n).lower() for n, _ in archivos)
        if "padronrgs" in nombres:
            return ARBA
        for _, contenido in archivos:
            for linea in contenido.splitlines():
                linea = linea.strip()
                if not linea:
                    continue
                # ARBA: el primer campo es el Régimen ('R'/'P'); AGIP: una fecha.
                primero = linea.split(";", 1)[0].strip()
                return ARBA if primero in ("R", "P") else AGIP
        return AGIP

    # -- parsers por jurisdicción -----------------------------------------

    def _parsear_linea_arba(self, linea):
        partes = linea.split(";")
        if len(partes) <= _ARBA_GRUPO:
            raise ValueError("campos insuficientes para ARBA")
        cuit = _normalizar_cuit(partes[_ARBA_CUIT])
        if len(cuit) != 11:
            raise ValueError("CUIT inválido")
        regimen = partes[_ARBA_REGIMEN].strip().upper()
        reg = self.registros.setdefault(cuit, _registro(cuit, ARBA))
        reg["vigencia_desde"] = _fecha(partes[_ARBA_VIG_DESDE])
        reg["vigencia_hasta"] = _fecha(partes[_ARBA_VIG_HASTA])
        reg["regimen_tipo_contribuyente"] = partes[_ARBA_TIPO_CONTRIB].strip() or None
        reg["marca_alta_baja"] = partes[_ARBA_MARCA_ALTA_BAJA].strip()
        alicuota = _alicuota(partes[_ARBA_ALICUOTA])
        grupo = partes[_ARBA_GRUPO].strip() or None
        if regimen == "R":
            reg["alicuota_retencion"] = alicuota
            reg["grupo_retencion"] = grupo
        elif regimen == "P":
            reg["alicuota_percepcion"] = alicuota
            reg["grupo_percepcion"] = grupo
        else:
            raise ValueError("régimen ARBA desconocido: %r" % regimen)

    def _parsear_linea_agip(self, linea):
        partes = linea.split(";")
        if len(partes) <= _AGIP_RAZON_SOCIAL:
            raise ValueError("campos insuficientes para AGIP")
        cuit = _normalizar_cuit(partes[_AGIP_CUIT])
        if len(cuit) != 11:
            raise ValueError("CUIT inválido")
        reg = _registro(cuit, AGIP)
        reg["vigencia_desde"] = _fecha(partes[_AGIP_VIG_DESDE])
        reg["vigencia_hasta"] = _fecha(partes[_AGIP_VIG_HASTA])
        reg["regimen_tipo_contribuyente"] = partes[_AGIP_TIPO_CONTRIB].strip() or None
        reg["marca_alta_baja"] = partes[_AGIP_MARCA_ALTA].strip()
        reg["alicuota_percepcion"] = _alicuota(partes[_AGIP_ALIC_PERCEPCION])
        reg["alicuota_retencion"] = _alicuota(partes[_AGIP_ALIC_RETENCION])
        reg["grupo_percepcion"] = partes[_AGIP_GRUPO_PERCEPCION].strip() or None
        reg["grupo_retencion"] = partes[_AGIP_GRUPO_RETENCION].strip() or None
        reg["razon_social"] = partes[_AGIP_RAZON_SOCIAL].strip()
        self.registros[cuit] = reg

    # -- consulta ----------------------------------------------------------

    def Consultar(self, cuit):
        """Devuelve el registro normalizado del CUIT, o ``None`` si no está.

        ``None`` significa "no está en el padrón" — distinto de un registro con
        ``alicuota_* == 0.0`` o ``None`` (un sujeto presente sin esa alícuota).
        """
        return self.registros.get(_normalizar_cuit(cuit))


def main():
    parser = argparse.ArgumentParser(
        description="Parser offline de padrones de alícuotas IIBB (ARBA / AGIP)."
    )
    parser.add_argument("archivo", help="ZIP o TXT del padrón")
    parser.add_argument("--cuit", help="consultar un CUIT puntual")
    parser.add_argument("--debug", action="store_true", help="mostrar advertencias")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.debug else logging.ERROR)
    padron = PadronIIBB()
    cantidad = padron.Cargar(args.archivo)
    print("Cargados %d registros del padrón %s" % (cantidad, padron.jurisdiccion))
    if args.cuit:
        reg = padron.Consultar(args.cuit)
        if reg is None:
            print("CUIT %s: NO está en el padrón" % args.cuit)
        else:
            for clave, valor in reg.items():
                print("  %-28s %s" % (clave, valor))


if __name__ == "__main__":
    main()
