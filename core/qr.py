# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

"""Núcleo puro para generar códigos QR de factura electrónica (ARCA/AFIP).

Implementa la especificación https://www.afip.gob.ar/fe/qr/especificaciones.asp
sin ninguna dependencia de COM/Windows: solo requiere ``qrcode`` (y Pillow).
La interfaz COM y la CLI viven en ``pyarcaws.pyqr``, que delega acá.
"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2020-2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"

import base64
import json
import tempfile
from typing import Union

import qrcode

# URL pública de ARCA/AFIP donde se valida el comprobante (%s: payload base64)
URL_TEMPLATE = "https://www.afip.gob.ar/fe/qr/?p=%s"

# parámetros por defecto de qrencode:
DEFAULT_QR_VER = 1
DEFAULT_BOX_SIZE = 10
DEFAULT_BORDER = 4
DEFAULT_ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_L


def crear_archivo_temporal(extension: str = "PNG") -> str:
    """Crea un archivo temporal ``qr_afip_*.<ext>`` y devuelve su ruta.

    El archivo no se borra automáticamente, para evitar errores de permisos
    y poder generar varios QR simultáneos.
    """
    tmp = tempfile.NamedTemporaryFile(
        prefix="qr_afip_", suffix=".%s" % extension.lower(), delete=False
    )
    tmp.close()
    return tmp.name


class QRGenerator:
    """Generador de códigos QR de factura electrónica según espec. ARCA/AFIP.

    Los parámetros de estilo se fijan al construir; los datos del comprobante
    se pasan en cada llamada. Las excepciones (datos no convertibles, formato
    de imagen inválido, etc.) se propagan normalmente.
    """

    def __init__(
        self,
        url_template: str = URL_TEMPLATE,
        qr_ver: int = DEFAULT_QR_VER,
        box_size: int = DEFAULT_BOX_SIZE,
        border: int = DEFAULT_BORDER,
        error_correction: int = DEFAULT_ERROR_CORRECTION,
    ) -> None:
        self.url_template = url_template
        self.qr_ver = qr_ver
        self.box_size = box_size
        self.border = border
        self.error_correction = error_correction

    def armar_datos(
        self,
        ver: Union[int, str] = 1,
        fecha: str = "2020-10-13",
        cuit: Union[int, str] = 30000000007,
        pto_vta: Union[int, str] = 10,
        tipo_cmp: Union[int, str] = 1,
        nro_cmp: Union[int, str] = 94,
        importe: Union[float, str] = 12100,
        moneda: str = "PES",
        ctz: Union[float, str] = 1.000,
        tipo_doc_rec: Union[int, str] = 80,
        nro_doc_rec: Union[int, str] = 20000000001,
        tipo_cod_aut: str = "E",
        cod_aut: Union[int, str] = 70417054367476,
    ) -> dict:
        """Arma el dict del comprobante con los tipos que exige la especificación."""
        return {
            "ver": int(ver),
            "fecha": fecha,
            "cuit": int(cuit),
            "ptoVta": int(pto_vta),
            "tipoCmp": int(tipo_cmp),
            "nroCmp": int(nro_cmp),
            "importe": float(importe),
            "moneda": moneda,
            "ctz": float(ctz),
            "tipoDocRec": int(tipo_doc_rec),
            "nroDocRec": int(nro_doc_rec),
            "tipoCodAut": tipo_cod_aut,
            "codAut": int(cod_aut),
        }

    def generar_url(self, datos_cmp: dict) -> str:
        """Serializa los datos a JSON, codifica en base64 y arma la URL final."""
        datos_cmp_json = json.dumps(datos_cmp)
        payload = base64.b64encode(datos_cmp_json.encode("ascii")).decode("ascii")
        return self.url_template % payload

    def generar_imagen(
        self,
        url: str,
        archivo: str,
        extension: str = "PNG",
        color_relleno: str = "black",
        color_fondo: str = "white",
    ) -> None:
        """Genera la imagen del código QR para ``url`` y la guarda en ``archivo``."""
        qr = qrcode.QRCode(
            version=self.qr_ver,
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color=color_relleno, back_color=color_fondo)
        img.save(archivo, extension.upper())

    def generar_qr(
        self,
        archivo: str,
        extension: str = "PNG",
        color_relleno: str = "black",
        color_fondo: str = "white",
        **datos_comprobante,
    ) -> str:
        """Genera URL e imagen QR en un paso; devuelve la URL del comprobante.

        ``datos_comprobante`` acepta los mismos argumentos que :meth:`armar_datos`.
        """
        datos_cmp = self.armar_datos(**datos_comprobante)
        url = self.generar_url(datos_cmp)
        self.generar_imagen(url, archivo, extension, color_relleno, color_fondo)
        return url
