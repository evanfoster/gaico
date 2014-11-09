# -*- coding: utf-8 -*-

import gevent
from gevent import socket


def getaddrinfo(hosts, port, family=0, socktype=0, proto=0, flags=0):
    """ Wrapper arround gevent.socket.getaddrinfo to handle multiple hosts. """

    def worker(host):
        try:
            return socket.getaddrinfo(host, port, family, socktype, proto, flags)
        except Exception as e:
            return e

    jobs = [gevent.spawn(worker, host) for host in hosts]
    gevent.joinall(jobs)
    results = [job.value for job in jobs]

    return dict(zip(hosts, results))
