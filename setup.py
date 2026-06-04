#!/usr/bin/python
# -*- coding: utf8 -*-

"Creador de instalador para PyAfipWs"

__author__ = "Mariano Reingart (reingart@gmail.com)"
__copyright__ = "Copyright (C) 2008-2021 Mariano Reingart"

import glob
import os
import subprocess
import sys

import setuptools

try:
    rev = subprocess.check_output(
        ["git", "rev-list", "--count", "--all"], stderr=subprocess.PIPE
    ).strip().decode("ascii")
except Exception:
    rev = 0

__version__ = "%s.%s.%s" % (sys.version_info[0:2] + (rev,))

kwargs = {}
desc = (
    "Interfases, tools and apps for Argentina's gov't. webservices "
    "(soap, com/dll, pdf, dbf, xml, etc.)"
)
kwargs["package_dir"] = {"pyafipws": "."}
kwargs["packages"] = ["pyafipws", "pyafipws.formatos"]
opts = {}
data_files = [("pyafipws/plantillas", glob.glob("plantillas/*"))]

parent_dir = os.getcwd()
long_desc = open(os.path.join(parent_dir, "README.md")).read()

setuptools.setup(
    name="PyAfipWs",
    version=__version__,
    description=desc,
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author="Mariano Reingart",
    author_email="reingart@gmail.com",
    url="https://github.com/reingart/pyafipws",
    license="LGPL-3.0-or-later",
    python_requires=">=3.9",
    install_requires=[
        "httplib2>=0.20.4",
        "pysimplesoap>=1.8.22",
        "cryptography>=41.0.1",
        "fpdf>=1.7.2",
        "dbf>=0.88.019",
        "Pillow>=2.0.0",
        "tabulate>=0.8.5",
        "certifi>=2020.4.5.1",
        "qrcode>=6.1",
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
