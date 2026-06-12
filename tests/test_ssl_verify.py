#!/usr/bin/python
# -*- coding: utf8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

"""Tests del endurecimiento de la validación SSL del transporte (sin red).

Verifica que, por defecto, el contexto/transporte valida el certificado del
servidor (check_hostname + CERT_REQUIRED), y que el opt-out explícito
(``cacert=False``) la desactiva emitiendo un UserWarning (nunca en silencio).
"""

import ssl

import pytest

from pyarcaws._vendor.pysimplesoap import transport as T

pytestmark = pytest.mark.dontusefix


def test_build_ssl_context_valida_por_defecto():
    ctx = T.build_ssl_context()  # cacert=None
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_build_ssl_context_cacert_false_desactiva_con_warning():
    with pytest.warns(UserWarning, match="MITM"):
        ctx = T.build_ssl_context(False)
    assert ctx.verify_mode == ssl.CERT_NONE
    assert ctx.check_hostname is False


def test_httplib2_transport_valida_por_defecto():
    certifi = pytest.importorskip("certifi")
    tr = T.Httplib2Transport(timeout=30)
    assert tr.disable_ssl_certificate_validation is False
    assert tr.ca_certs == certifi.where()


def test_httplib2_transport_cacert_false_warning_y_desactiva():
    with pytest.warns(UserWarning, match="MITM"):
        tr = T.Httplib2Transport(timeout=30, cacert=False)
    assert tr.disable_ssl_certificate_validation is True


def test_httplib2_transport_cacert_custom_se_respeta():
    tr = T.Httplib2Transport(timeout=30, cacert="/ruta/mi_ca.pem")
    assert tr.disable_ssl_certificate_validation is False
    assert tr.ca_certs == "/ruta/mi_ca.pem"
