#!/usr/bin/python
# -*- coding: utf8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

import os
import pytest
from pyarcaws.wsaa import WSAA

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2021- Mariano Reingart"
__license__ = "GPL 3.0"


WSDL = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
CUIT = 20267565393
CERT = "reingart.crt"
PKEY = "reingart.key"
CACHE=""
# CERT = "/home/reingart/pyarcaws/reingart.crt"
# PRIVATEKEY = "/home/reingart/pyarcaws/reingart.key"
# CACERT = "/home/reingart/pyarcaws/afip_root_desa_ca.crt"
# CACHE = "/home/reingart/pyarcaws/cache"

os.environ["CUIT"] = str(CUIT)


def pytest_addoption(parser):
    parser.addoption(
        "--run-online",
        action="store_true",
        default=False,
        help="ejecutar los tests marcados 'online' (requieren red y/o certificado ARCA)",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-saltea los tests marcados 'online' salvo que se pase --run-online.

    Son tests de integración (típicamente vía ``main()`` de cada módulo) que
    autentican contra WSAA y/o pegan a la red: en un checkout limpio sin
    certificado fallan o cuelgan. Se mantienen para correrse explícitamente
    (``pytest --run-online``) con un certificado de homologación configurado.
    """
    if config.getoption("--run-online"):
        return
    skip_online = pytest.mark.skip(
        reason="requiere red/certificado ARCA (correr con --run-online)"
    )
    for item in items:
        if "online" in item.keywords:
            item.add_marker(skip_online)


#fixture for setting directory
@pytest.fixture(scope='module')
def vcr_cassette_dir(request):
    # Put all cassettes in vhs/{module}/{test}.yaml
    return os.path.join('tests/cassettes', request.module.__name__)

#WSAA authentication fixture, used by all tests
@pytest.fixture(autouse=True)
def auth(request):
    if 'dontusefix' in request.keywords:
        return
    # Esta fixture autentica contra WSAA firmando el TRA con un certificado
    # (lado cliente, antes de cualquier cassette): los tests que la usan
    # requieren cert + servicio autorizado, así que son 'online'. En un checkout
    # limpio (CI sin cert) se saltan, salvo que se pase --run-online con un
    # certificado de homologación configurado.
    if not request.config.getoption("--run-online"):
        pytest.skip("requiere certificado ARCA (correr con --run-online)")
    z=request.module.__obj__
    z.Cuit = CUIT
    wsaa=WSAA()
    ta = wsaa.Autenticar(request.module.__service__, CERT, PKEY)
    z.SetTicketAcceso(ta)
    z.Conectar(CACHE, request.module.__WSDL__)
    return z