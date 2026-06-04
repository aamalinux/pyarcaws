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

"""Módulo para acceder a web services de la afip
"""

# inspect.getargspec fue removido en Python 3.11; pysimplesoap lo usa en
# transport.py a nivel de módulo. Este shim lo restaura usando getfullargspec,
# que devuelve los mismos campos en [0] (args) que usaba el código original.
import inspect
if not hasattr(inspect, "getargspec"):
    inspect.getargspec = inspect.getfullargspec
__author__ = "Mariano Reingart (mariano@gmail.com)"
__copyright__ = "Copyright (C) 2008-2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"
__version__ = "1.0.0"
