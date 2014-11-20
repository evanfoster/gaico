# -*- coding: utf-8 -*-

import gevent
import struct
import time
from gevent import select, sleep, socket
from gaico.net import getaddrinfo


ICMPV4_ECHO_REQUEST = 8
ICMPV6_ECHO_REQUEST = 128


class PingPacket(object):
    """ Object representing an PING packet. """

    def __init__(self, identifier, sequence, payload, ipv6=False):
        """ Create a PING packet with default values. """

        # ICMP v4 or v6
        self.message_type = ICMPV4_ECHO_REQUEST
        if ipv6:
            self.message_type = ICMPV6_ECHO_REQUEST

        # the code is always 0 for ICMP echo packets
        self.code = 0

        self.identifier = identifier
        self.sequence = sequence
        self.payload = payload
        self.ipv6 = ipv6

    def pack(self, checksum=None):
        """ Create the packet. """

        if checksum is None:
            checksum = self.checksum

        # header is type (8), code (8), checksum (16), id (16), sequence (16)
        header = struct.pack(
            "!BBHHH", self.message_type, self.code, checksum, self.identifier, self.sequence
        )

        return header + self.payload

    @property
    def checksum(self):
        """ Compute the checksum. """

        if self.ipv6:
            # ICMPv6 has the IP stack calculate the checksum for us
            # just returns 0
            return 0

        # get a dummy packet with a 0 checksum
        packet = self.pack(checksum=0)

        if len(packet) % 2 == 1:
            # padding to have an even number of bytes
            packet = packet + '\0'

        checksum = 0
        for count in xrange(0, len(packet), 2):
            value, = struct.unpack("!H", packet[count:count+2])
            checksum = checksum + value

        checksum = (checksum >> 16) + (checksum & 0xFFFF)
        checksum = checksum + (checksum >> 16)
        checksum = ~checksum
        checksum = checksum & 0xFFFF

        return checksum

    @classmethod
    def fromdata(cls, data):
        """ Create a PingPacket object from `data`. """

        payload_offset = 8
        icmp_header = data[0:payload_offset]
        message_type, code, checksum, identifier, sequence = struct.unpack(
            "!BBHHH", icmp_header
        )

        payload = data[payload_offset:]

        # ICMP v4 or v6
        ipv6 = message_type == ICMPV6_ECHO_REQUEST

        packet = cls(identifier, sequence, payload, ipv6)
        return packet


def receive_one_ping(my_socket, addr_info, identifier, sequence, timeout):
    """ Wait for a ping reply from `host`. """

    host = addr_info[4][0]

    # is ipv6?
    ipv6 = my_socket.family == socket.AF_INET6

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

        if not ipv6:
            # IP header is included only with IPv4 (remove it)
            received_packet = received_packet[20:]

        # contruct a PING packet
        packet = PingPacket.fromdata(received_packet)

        # is this the reply we are looking for?
        if packet.identifier == identifier and packet.sequence == sequence and addr[0] == host:
            # extract the timestamp from the payload
            bytes_size = struct.calcsize("d")
            time_sent, = struct.unpack(
                "!d",
                packet.payload[0:bytes_size]
            )
            return time_received - time_sent

        time_left = time_left - how_long_in_select
        if time_left <= 0:
            # Timeout
            return


def send_one_ping(my_socket, addr_info, identifier, sequence, packet_size):
    """ Send one ping request the given `addr_info`. """

    # add the current timestamp in the payload
    bytes_size = struct.calcsize("d")
    payload = ((packet_size - 8) - bytes_size) * "Q"
    payload = struct.pack("!d", time.time()) + payload

    # is ipv6?
    ipv6 = my_socket.family == socket.AF_INET6

    # our PING packet
    packet = PingPacket(identifier, sequence, payload, ipv6)

    # send the packet on the wire
    my_socket.sendto(packet.pack(), addr_info[4])


def do_one_ping(addr_info, identifier, sequence, timeout, packet_size):
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

    send_one_ping(my_socket, addr_info, identifier, sequence, packet_size)
    delay = receive_one_ping(my_socket, addr_info, identifier, sequence, timeout)

    my_socket.close()

    return delay


def ping_worker(addr_info, timeout, count, packet_size, interval, deadline):
    """ Worker that is run for each host. Concurrency is handled by gevent. """

    minping = None
    avgping = None
    maxping = None
    replies = []

    deadline_time = None
    if deadline is not None:
        deadline_time = time.time() + deadline

    identifier = int(time.time() * 1000000) & 0xFFFF

    sent_packets = 0
    for sequence in xrange(count):
        time_ping_sent = time.time()
        delay = do_one_ping(addr_info, identifier, sequence, timeout, packet_size)

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
        'sent': sent_packets,
        'received': len(replies),
        'minping': minping,
        'maxping': maxping,
        'avgping': avgping,
        'packet_loss': percent_lost,
    }


def ping(hosts, timeout=10, count=10, packet_size=64, interval=1, deadline=None):
    """ Pure Python implementation of the ping command.

    :param hosts: hosts to ping (ip addresses or hostnames)
    :param timeout: timeout in second for a single ping round trip (default: 10)
    :param count: number of ping round trips (default 10)
    :param packet_size: the number of bytes to send (default: 64)
    :param interval: wait interval seconds between sending two packets (default: 1)
    :param deadline: timeout in second, before `ping` returns regardless of how
    many packets have been sent or received (default: no deadline)

    Returns an Exception or a dictionary for each host with the following fields:
        `host`: *string*; the IP address used to ping the target
        `sent`: *int*; the number of ping request packets sent
        `received`: *int*; the number of ping reply packets received
        `minping`: *float*; the minimum (fastest) round trip ping request/reply time in seconds
        `avgping`: *float*; the average round trip ping time in seconds
        `maxping`: *float*; the maximum (slowest) round trip ping time in seconds
        `packet_loss`: *float*; percentage of lost packets
    """

    addresses_info = getaddrinfo(hosts, None)

    jobs = []
    failures = {}
    for host in hosts:
        addr_info = addresses_info[host]
        if addr_info is None or isinstance(addr_info, Exception):
            failures[host] = addr_info
            continue
        if len(addr_info) >= 1:
            jobs.append(gevent.spawn(ping_worker, addr_info[0], timeout, count, packet_size,
                                     interval, deadline))
    gevent.joinall(jobs)

    ping_results = [job.value for job in jobs]
    results = dict(zip(hosts, ping_results))
    results.update(failures)

    return results
