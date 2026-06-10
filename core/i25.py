# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

"""Núcleo puro para generar códigos de barra Entrelazado 2 de 5 (I25).

Implementa el código de barras de los comprobantes electrónicos (CAE) sin
ninguna dependencia de COM/Windows: solo requiere Pillow. La interfaz COM
y la CLI viven en ``pyarcaws.pyi25``, que delega acá.

Basado en:
 * http://www.fpdf.org/en/script/script67.php
 * http://code.activestate.com/recipes/426069/
"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2011-2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"

from typing import Optional

from PIL import Image, ImageDraw

# códigos ancho/angostos (wide/narrow) para los dígitos
BARS = (
    "nnwwn",
    "wnnnw",
    "nwnnw",
    "wwnnn",
    "nnwnw",
    "wnwnn",
    "nwwnn",
    "nnnww",
    "wnnwn",
    "nwnwn",
    "nn",
    "wn",
)

DEFAULT_BASEWIDTH = 3
DEFAULT_HEIGHT = 30


def digito_verificador_modulo10(codigo: str) -> str:
    """Calcula el dígito verificador 'módulo 10' del código.

    Devuelve cadena vacía si el código no es numérico.
    http://www.consejo.org.ar/Bib_elect/diciembre04_CT/documentos/rafip1702.htm
    """
    # Etapa 1: comenzar desde la izquierda, sumar todos los caracteres ubicados en las posiciones impares.
    codigo = codigo.strip()
    if not codigo or not codigo.isdigit():
        return ""
    etapa1 = sum([int(c) for i, c in enumerate(codigo) if not i % 2])
    # Etapa 2: multiplicar la suma obtenida en la etapa 1 por el número 3
    etapa2 = etapa1 * 3
    # Etapa 3: comenzar desde la izquierda, sumar todos los caracteres que están ubicados en las posiciones pares.
    etapa3 = sum([int(c) for i, c in enumerate(codigo) if i % 2])
    # Etapa 4: sumar los resultados obtenidos en las etapas 2 y 3.
    etapa4 = etapa2 + etapa3
    # Etapa 5: buscar el menor número que sumado al resultado obtenido en la etapa 4 dé un número múltiplo de 10. Este será el valor del dígito verificador del módulo 10.
    digito = 10 - (etapa4 - (etapa4 // 10 * 10))
    if digito == 10:
        digito = 0
    return str(digito)


def calcular_ancho(codigo: str, basewidth: int = DEFAULT_BASEWIDTH) -> int:
    """Calcula el ancho de imagen automático para el código (ya con el 0 de relleno)."""
    largo = len(codigo) + len(codigo) % 2
    narrow = basewidth // 3
    return (largo * 3) * basewidth + (10 * narrow)


def generar_imagen(
    codigo: str,
    archivo: str = "barras.png",
    basewidth: int = DEFAULT_BASEWIDTH,
    width: Optional[int] = None,
    height: int = DEFAULT_HEIGHT,
    extension: str = "PNG",
) -> None:
    """Genera la imagen del código de barras I25 y la guarda en ``archivo``.

    Si ``width`` es None se calcula automáticamente según el largo del código.
    """
    wide = basewidth
    narrow = basewidth // 3

    # agregar un 0 al principio si el número de dígitos es impar
    if len(codigo) % 2:
        codigo = "0" + codigo

    if not width:
        width = calcular_ancho(codigo, basewidth)

    # crear una nueva imágen
    im = Image.new("1", (width, height))

    # agregar códigos de inicio y final
    codigo = "::" + codigo.lower() + ";:"  # A y Z en el original

    # crear un drawer
    draw = ImageDraw.Draw(im)

    # limpiar la imágen
    draw.rectangle(((0, 0), (im.size[0], im.size[1])), fill=256)

    xpos = 0
    # dibujar los códigos de barras
    for i in range(0, len(codigo), 2):
        # obtener el próximo par de dígitos
        bar = ord(codigo[i]) - ord("0")
        space = ord(codigo[i + 1]) - ord("0")
        # crear la sequencia barras (1er dígito=barras, 2do=espacios)
        seq = ""
        for s in range(len(BARS[bar])):
            seq = seq + BARS[bar][s] + BARS[space][s]

        for s in range(len(seq)):
            if seq[s] == "n":
                ancho_barra = narrow
            else:
                ancho_barra = wide

            # dibujar barras impares (las pares son espacios)
            if not s % 2:
                draw.rectangle(((xpos, 0), (xpos + ancho_barra - 1, height)), fill=0)
            xpos = xpos + ancho_barra

    im.save(archivo, extension.upper())
