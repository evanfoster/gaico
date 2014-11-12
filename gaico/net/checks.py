# -*- coding: utf-8 -*-

import gevent
from gevent import socket
from gaico.net import getaddrinfo


def _check_port_state(addr_info, port, timeout):
    """ Check the state of a single `port` on `host`. """

    s = socket.socket(addr_info[0], socket.SOCK_STREAM)
    s.settimeout(timeout)

    host = addr_info[4][0]

    try:
        s.connect((host, port))
    except Exception as e:
        return e
    finally:
        s.close()

    return True


def check_ports_state(hosts_ports, timeout=10):
    """ Check if the given `ports` are open on all `hosts`.

    :param hosts_ports: dictionay with hosts (ip address or hostname) as key,
    and a list of ports as value
    :param timeout: timeout in second to wait for a reply (default: 10)

    Returns a dictionary for each host with the following fields:
        `host`: *string*; the IP address used
        port number 1: `True`, if the port is open, or an Exception
        port number 2: `True`, if the port is open, or an Exception
        ...
    """

    addresses_info = getaddrinfo(hosts_ports.keys(), None)

    jobs = []
    failures = {}
    for host, ports in hosts_ports.items():
        addr_info = addresses_info[host]
        if isinstance(addr_info, Exception):
            failures[host] = addr_info
            continue
        for port in ports:
            job = gevent.spawn(_check_port_state, addr_info[0], port, timeout)
            job.host = host
            job.port = port
            job.resolved_host = addr_info[0][4][0]
            jobs.append(job)
    gevent.joinall(jobs)

    results = {}
    for job in jobs:
        host = job.host
        port = job.port

        res = results.get(host, {})
        res[port] = job.value
        res['host'] = job.resolved_host
        results[host] = res

    results.update(failures)

    return results
