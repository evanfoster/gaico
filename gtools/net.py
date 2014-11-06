# -*- coding: utf-8 -*-

import gevent
import struct
import time
from gevent import select, sleep, socket


ICMP_ECHO_REQUEST = 8
ICMPV6_ECHO_REQUEST = 128


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


def ping(hosts, timeout=10, count=10, packet_size=64, interval=1, deadline=None):
    """ Ping `hosts`.

    :param hosts: hosts to ping (ip addresses or hostnames)
    :param timeout: timeout in second for a single ping round trip (default: 10)
    :param count: number of ping round trips (default 10)
    :param packet_size: the number of bytes to send (default: 64)
    :param interval: wait interval seconds between sending two packets (default: 1)
    :param deadline: timeout in second, before `ping` returns regardless of how
    many packets have been sent or received (default: no deadline)

    Returns a dictionary for each host with the following fields:
        `host`: *string*; the IP address used to ping the target
        `sent`: *int*; the number of ping request packets sent
        `received`: *int*; the number of ping reply packets received
        `minping`: *float*; the minimum (fastest) round trip ping request/reply time in seconds
        `avgping`: *float*; the average round trip ping time in seconds
        `maxping`: *float*; the maximum (slowest) round trip ping time in seconds
        `packet_size`: *int*; the number of data bytes sent
        `packet_loss`: *float*; percentage of lost packets
    """

    def checksum(source_string):
        sum = 0
        count_to = int((len(source_string) / 2) * 2)
        for count in xrange(0, count_to, 2):
            this = ord(source_string[count + 1]) * 256 + ord(source_string[count])
            sum = sum + this
            sum = sum & 0xFFFFFFFF

        if count_to < len(source_string):
            sum = sum + ord(source_string[len(source_string) - 1])
            sum = sum & 0xFFFFFFFF

        sum = (sum >> 16) + (sum & 0xFFFF)
        sum = sum + (sum >> 16)
        answer = ~sum
        answer = answer & 0xFFFF

        return answer

    def receive_one_ping(my_socket, addr_info, identifier, sequence):
        """ Wait for a ping reply from `host`. """

        host = addr_info[4][0]
        header_offset = 20
        if my_socket.family == socket.AF_INET6:
            header_offset = 0
        data_offset = header_offset + 8

        time_left = timeout
        while True:
            started_select = time.time()
            what_ready = select.select([my_socket], [], [], time_left)
            how_long_in_select = (time.time() - started_select)
            if what_ready[0] == []:
                # Timeout
                return

            time_received = time.time()
            received_packet, addr = my_socket.recvfrom(1024)
            icmp_header = received_packet[header_offset:data_offset]
            message_type, code, checksum, recv_identifier, recv_sequence = struct.unpack(
                "!BBHHH", icmp_header
            )

            if recv_identifier == identifier and recv_sequence == sequence and addr[0] == host:
                bytes_size = struct.calcsize("d")
                time_sent = struct.unpack(
                    "!d",
                    received_packet[data_offset:data_offset + bytes_size]
                )[0]
                return time_received - time_sent

            time_left = time_left - how_long_in_select
            if time_left <= 0:
                # Timeout
                return

    def send_one_ping(my_socket, addr_info, identifier, sequence):
        """ Send one ping request to `address`. """

        # Header is type (8), code (8), checksum (16), id (16), sequence (16)
        my_checksum = 0

        icmp_type = ICMP_ECHO_REQUEST
        if my_socket.family == socket.AF_INET6:
            icmp_type = ICMPV6_ECHO_REQUEST

        # Make a dummy heder with a 0 checksum.
        header = struct.pack(
            "!BBHHH", icmp_type, 0, my_checksum, identifier, sequence
        )
        bytes_size = struct.calcsize("d")
        data = ((packet_size - 8) - bytes_size) * "Q"
        data = struct.pack("!d", time.time()) + data

        # Calculate the checksum on the data and the dummy header.
        my_checksum = checksum(header + data)

        # Now that we have the right checksum, we put that in. It's just easier
        # to make up a new header than to stuff it into the dummy.
        header = struct.pack(
            "!BBHHH", icmp_type, 0, socket.htons(my_checksum), identifier, sequence
        )
        packet = header + data
        my_socket.sendto(packet, addr_info[4])

    def do_one_ping(addr_info, identifier, sequence):
        """ Returns either the delay (in seconds) or `None` on timeout. """

        icmp = socket.getprotobyname('icmp')
        if addr_info[0] == socket.AF_INET6:
            icmp = socket.getprotobyname('ipv6-icmp')

        try:
            my_socket = socket.socket(addr_info[0], socket.SOCK_RAW, icmp)
        except socket.error, (errno, msg):
            if errno == 1:
                # Operation not permitted
                msg = msg + " - Note that ICMP messages can only by sent from processes running " \
                    "as root."
                raise socket.error(msg)
            # raise the original error
            raise

        send_one_ping(my_socket, addr_info, identifier, sequence)
        delay = receive_one_ping(my_socket, addr_info, identifier, sequence)

        my_socket.close()

        return delay

    def ping_worker(addr_info):
        """ Worker that is run for each host. Concurrency is handled by gevent. """

        minping = None
        avgping = None
        maxping = None
        replies = []

        deadline_time = None
        if deadline is not None:
            deadline_time = time.time() + deadline

        identifier = int(time.time() * 1000000) & 0xFFFF
        sequence = 1

        sent_packets = 0
        for i in xrange(count):
            time_ping_sent = time.time()
            delay = do_one_ping(addr_info, identifier, sequence)

            sequence = sequence + 1
            sent_packets = sent_packets + 1

            if delay is not None:
                # we got a reply
                replies.append(delay)

            if deadline_time is not None and deadline_time < time.time():
                # deadline reached
                break

            time_delta = time.time() - time_ping_sent
            if time_delta < interval:
                sleep(interval - time_delta)

        percent_lost = 100 - (len(replies) * 100 / sent_packets)

        if replies:
            minping = min(replies)
            maxping = max(replies)
            avgping = sum(replies) / len(replies)

        return {
            'host': addr_info[4][0],
            'send': sent_packets,
            'received': len(replies),
            'minping': minping,
            'maxping': maxping,
            'avgping': avgping,
            'packet_loss': percent_lost,
        }

    addresses_info = getaddrinfo(hosts, None)

    jobs = []
    failures = {}
    for host in hosts:
        addr_info = addresses_info[host]
        if addr_info is None or isinstance(addr_info, Exception):
            failures[host] = addr_info
            continue
        if len(addr_info) >= 1:
            jobs.append(gevent.spawn(ping_worker, addr_info[0]))
    gevent.joinall(jobs)

    ping_results = [job.value for job in jobs]
    results = dict(zip(hosts, ping_results))
    results.update(failures)

    return results
