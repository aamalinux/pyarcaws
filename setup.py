#!/usr/bin/python
# -*- coding: utf8 -*-

"Creador de instalador para pyarcaws"

__author__ = "Mariano Reingart (reingart@gmail.com)"
__copyright__ = "Copyright (C) 2008-2021 Mariano Reingart"

import glob
import os
import re

import setuptools

# Versión canónica definida en __init__.py
with open(os.path.join(os.path.dirname(__file__), "__init__.py")) as f:
    match = re.search(r'^__version__\s*=\s*[\'"]([^\'"]+)[\'"]', f.read(), re.M)
    __version__ = match.group(1) if match else "0.0.0"

kwargs = {}
desc = (
    "Interfases, tools and apps for Argentina's gov't. webservices "
    "(soap, com/dll, pdf, dbf, xml, etc.)"
)
kwargs["package_dir"] = {"pyarcaws": "."}
kwargs["packages"] = [
    "pyarcaws",
    "pyarcaws.formatos",
    "pyarcaws.windows",
    "pyarcaws._vendor",
    "pyarcaws._vendor.pysimplesoap",
]
opts = {}
data_files = [("pyarcaws/plantillas", glob.glob("plantillas/*"))]

# Plantillas PDF (CSV/PNG) DENTRO del paquete: pyfepdf las busca en
# InstallDir/plantillas (= site-packages/pyarcaws/plantillas). El data_files de
# arriba las deja en sys.prefix/pyarcaws, donde pyfepdf no las encuentra al
# instalar con `setup.py install` (FileNotFoundError en main()/plantillas).
kwargs["package_data"] = {"pyarcaws": ["plantillas/*"]}

parent_dir = os.path.dirname(__file__) or os.getcwd()
# encoding explícito: el README es UTF-8 (acentos, emoji U+FE0F). En Windows el
# default de open() es cp1252 y `setup.py install` reventaba con
# `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f` (CI x86/x64).
long_desc = open(os.path.join(parent_dir, "README.md"), encoding="utf-8").read()

setuptools.setup(
    name="pyarcaws",
    version=__version__,
    description=desc,
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author="Mariano Reingart",
    author_email="reingart@gmail.com",
    url="https://github.com/aamalinux/pyarcaws",
    license="LGPL-3.0-or-later",
    python_requires=">=3.9",
    install_requires=[
        "httplib2>=0.22.0",
        # pysimplesoap se incluye como _vendor/pysimplesoap (corregido para 3.11+)
        "cryptography>=42.0.0",
        "fpdf>=1.7.2",
        "dbf>=0.99.0",
        "Pillow>=10.0.0",
        "tabulate>=0.9.0",
        "certifi>=2024.1.1",
        "qrcode>=7.4",
    ],
    extras_require={
        "opt": ["pywin32==304;sys_platform == 'win32'"]
    },
    options=opts,
    data_files=data_files,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Natural Language :: Spanish",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Object Brokering",
    ],
    keywords="webservice electronic invoice pdf traceability",
    **kwargs
)
