Gaico
=====

.. image:: https://travis-ci.org/lmeunier/gaico.svg?branch=master
    :target: https://travis-ci.org/lmeunier/gaico

Overview
--------

Gaico is a collection of small useful functions. Nothing fancy or
revolutionary, just little things I use in several projects. The primary goal
of this package is to provide pure python implementations of network tools
(like ping or ARP).

Requirements
------------

- Python 3.5
- gevent 1.1.0

Installation
------------

- from PyPI:

.. code:: bash

   pip install gaico

- from Git:

.. code:: bash

    git clone https://github.com/lmeunier/gaico
    cd gaico
    python setup.py install

Functions
---------

- ``gaico.net.ping``: Ping multiple hosts concurrently.
- ``gaico.net.getaddrinfo``: Same as ``gevent.socket.getaddrinfo`` except that
  you can pass multiple hosts.
- ``gaico.net.arp_request``: Send ARP request for multiple hosts concurrently.
- ``gaico.net.check_ports_state``: Check if TCP ports are open on given hosts.

To view detailed help on a particular function, use the ``help()`` Python
built-in function.

.. code:: python

    from gaico.net import ping
    help(ping)

Credits
-------

Gaico is maintained by `Laurent Meunier <http://www.deltalima.net/>`_.

Licenses
--------

Gaico is Copyright (c) 2014 Laurent Meunier. It is free software, and may be
redistributed under the terms specified in the LICENSE file (a 3-clause BSD
License).
