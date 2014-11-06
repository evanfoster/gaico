# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from gaico import __version__ as version


setup(
    name='gaico',
    version=version,
    description='A set of network tools written in pure Python with gevent.',
    long_description=__doc__,
    author='Laurent Meunier',
    author_email='laurent@deltalima.net',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['gevent==1.0.1'],
)
