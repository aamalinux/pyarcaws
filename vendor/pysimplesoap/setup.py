#!/usr/bin/env python
# Versión local de pysimplesoap 1.16.2 con dos correcciones:
#   1. from setuptools import setup  (distutils removido en Python 3.12+)
#   2. transport.py: getfullargspec  (getargspec removido en Python 3.11)
# No importa el paquete en setup.py para no romper builds aislados (PEP 517).

from setuptools import setup

setup(
    name='PySimpleSOAP',
    version='1.16.2',
    description='Python simple and lightweight SOAP Library',
    author='Mariano Reingart',
    author_email='reingart@gmail.com',
    url='https://github.com/pysimplesoap/pysimplesoap',
    packages=['pysimplesoap'],
    license='LGPL 3.0',
    python_requires='>=3.9',
    classifiers=[
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
