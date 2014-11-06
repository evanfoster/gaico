# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from gtools import __version__ as version


setup(
    name='gtools',
    version=version,
    description='gevent tools',
    long_description=__doc__,
    author='Laurent Meunier',
    author_email='laurent@deltalima.net',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['gevent==1.0.1'],
)
