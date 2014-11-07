# -*- coding: utf-8 -*-

"""
    Gaico
    ~~~~~

    Gaico is a collection of small useful functions. Nothing fancy or
    revolutionary, just little things I use in several projects. The primary
    goal of this package is to provide pure python implementations of network
    tools (like ping).

"""

from setuptools import setup, find_packages


setup(
    name='gaico',
    version='0.1.0',
    description='A set of network tools written in pure Python with gevent.',
    long_description=__doc__,
    author='Laurent Meunier',
    author_email='laurent@deltalima.net',
    url='https://github.com/lmeunier/gaico',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['gevent==1.0.1'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Utilities',
    ]
)
