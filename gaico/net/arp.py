# -*- coding: utf-8 -*-

import gevent
import struct
import time
from gevent import select, socket
from gaico.net import getaddrinfo

"""
    Pure python ARP request implementation.
"""

ARP_PROTO = struct.pack('!H', 0x0806)
ARP_REQUEST = struct.pack('!H', 0x0001)
ARP_REPLY = struct.pack('!H', 0x0002)


def receive_reply(my_socket, source_ip, destination_ip, timeout):
    """ Wait for an ARP Reply. """
    time_left = timeout
    while True:
        started_select = time.time()
        what_ready = select.select([my_socket], [], [], time_left)
        how_long_in_select = (time.time() - started_select)
        if what_ready[0] == []:
            # timeout
            return

        # read from the socket
        frame, addr = my_socket.recvfrom(1024)

        time_left = time_left - how_long_in_select
        if time_left <= 0:
            # timeout
            return

        if frame[12:14] != ARP_PROTO:
            # not an ARP packet
            continue

        if frame[20:22] != ARP_REPLY:
            # not an ARP reply
            continue

        arp_headers = frame[18:20]
        hlen, plen = struct.unpack('!1B1B', arp_headers)

        arp_addrs = frame[22:22 + 2 * hlen + 2 * plen]
        src_hw, src_ip, dst_hw, dst_ip = struct.unpack(
            '!{hlen}s{plen}s{hlen}s{plen}s'.format(hlen=hlen, plen=plen),
            arp_addrs
        )

        if src_ip == destination_ip and dst_ip == source_ip:
            return src_hw


def send_request(my_socket, destination_ip, source_ip, interface):
    """ Send an ARP request. """
    bcast_mac = struct.pack('!6B', *[0xFF]*6)
    source_mac = my_socket.getsockname()[4]
    destination_mac = struct.pack('!6B', *[0x00]*6)

    arpframe = [
        # Ethernet
        bcast_mac,
        source_mac,
        ARP_PROTO,

        # ARP
        struct.pack('!H', 0x0001),  # HTYPE
        struct.pack('!H', 0x0800),  # PTYPE
        struct.pack('!B', 0x0006),  # HLEN
        struct.pack('!B', 0x0004),  # PLEN
        ARP_REQUEST,
        source_mac,
        source_ip,
        destination_mac,
        destination_ip,
    ]

    my_socket.send(''.join(arpframe))


def arp_worker(destination, source, interface, timeout):
    """ Worker that is run for each host. Concurrency is handled by gevent. """

    if destination[0] != source[0]:
        # source and destination must be both ipv4 or ipv6
        # should raise an Exception?
        return

    source_ip = socket.inet_pton(source[0], source[4][0])
    destination_ip = socket.inet_pton(destination[0], destination[4][0])

    try:
        my_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.SOCK_RAW)
    except socket.error, (errno, msg):
        if errno == 1:
            # Operation not permitted
            msg = msg + (
                " - Note that ARP requests can only be sent from processes"
                " running as root."
            )
            raise socket.error(msg)
        # raise the original error
        raise

    my_socket.bind((interface, socket.SOCK_RAW))

    send_request(my_socket, destination_ip, source_ip, interface)
    mac_address = receive_reply(my_socket, source_ip, destination_ip, timeout)

    return mac_address


def arp_request(hosts, source, interface, timeout=10):
    """ Pure Python implementation of ARP request.

    :param hosts: targets of the ARP requests (ip address or hostname)
    :param source: the source of the ARP request (ip address or hostname)
    :param interface: the name of the network interface where the ARP request will be sent
    :param timeout: how many seconds to wait for a reply (default: 10)

    Returns a dictionary with hosts as keys and the MAC address of the host or
    `None` if no replies are received.
    """

    addresses_info = getaddrinfo(hosts, None, socket.AF_INET)
    src_addr_info = getaddrinfo([source], None, socket.AF_INET)[source]

    if isinstance(src_addr_info, Exception):
        raise src_addr_info

    jobs = []
    failures = {}
    for host in hosts:
        addr_info = addresses_info[host]
        if addr_info is None or isinstance(addr_info, Exception):
            failures[host] = addr_info
            continue
        jobs.append(gevent.spawn(arp_worker, addr_info[0], src_addr_info[0], interface,
                                 timeout))
    gevent.joinall(jobs)

    arp_results = [job.value for job in jobs]
    results = dict(zip(hosts, arp_results))
    results.update(failures)

    return results
