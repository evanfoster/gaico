# -*- coding: utf-8 -*-

"""
    Gaico test suite
    ~~~~~~~~~~~~~~~~

"""

import unittest
from gaico.net.ping import PingPacket, ICMPV4_ECHO_REQUEST, ICMPV6_ECHO_REQUEST


class PingPacketIPV4TestCase(unittest.TestCase):
    """ Tests for the `gaico.net.ping.PingPacket` class with IPv4. """

    def setUp(self):
        self.message_type = ICMPV4_ECHO_REQUEST
        self.identifier = 22666
        self.sequence = 7
        self.checksum = 0x7044
        self.ipv6 = False
        self.payload = "\x41\xd5\x19\x96\xb5\xb6\xc3\xad\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51"
        self.pp = PingPacket(self.identifier, self.sequence, self.payload, self.ipv6)

        final_packet = "\x08\x00\x70\x44\x58\x8a\x00\x07\x41\xd5\x19\x96\xb5\xb6\xc3\xad" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51"
        self.final_packet = final_packet

    def test_init(self):
        self.assertEqual(self.pp.code, 0)
        self.assertEqual(self.pp.identifier, self.identifier)
        self.assertEqual(self.pp.sequence, self.sequence)
        self.assertEqual(self.pp.payload, self.payload)
        self.assertEqual(self.pp.ipv6, self.ipv6)
        self.assertEqual(self.pp.message_type, self.message_type)

    def test_checksum(self):
        self.assertEqual(self.pp.checksum, self.checksum)

    def test_pack(self):
        self.assertEqual(self.pp.pack(), self.final_packet)

    def test_fromdata(self):
        # create an object from data
        pp = PingPacket.fromdata(self.final_packet)

        # checks the object is populated correctly
        self.assertEqual(self.pp.code, pp.code)
        self.assertEqual(self.pp.identifier, pp.identifier)
        self.assertEqual(self.pp.sequence, pp.sequence)
        self.assertEqual(self.pp.payload, pp.payload)
        self.assertEqual(self.pp.ipv6, pp.ipv6)
        self.assertEqual(self.pp.message_type, pp.message_type)


class PingPacketIPV6TestCase(PingPacketIPV4TestCase):
    """ Tests for the `gaico.net.ping.PingPacket` class with IPv6. """

    def setUp(self):
        self.message_type = ICMPV6_ECHO_REQUEST
        self.identifier = 0xda25
        self.sequence = 9
        self.checksum = 0  # the checksum is calculated by the IPv6 stack
        self.ipv6 = True
        self.payload = "\x41\xd5\x1b\x67\x5e\xd1\x9f\x5a\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51"
        self.pp = PingPacket(self.identifier, self.sequence, self.payload, self.ipv6)

        final_packet = "\x80\x00\x00\x00\xda\x25\x00\x09\x41\xd5\x1b\x67\x5e\xd1\x9f\x5a" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51" \
                       "\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51\x51"
        self.final_packet = final_packet


if __name__ == '__main__':
    unittest.main()
