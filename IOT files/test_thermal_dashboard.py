"""Offline protocol checks: python tools/test_thermal_dashboard.py."""
import struct
import unittest
import zlib
import thermal_dashboard as dashboard

class EndOfPackets(Exception):
    pass

class FakeSocket:
    def __init__(self, packets):
        self.packets = iter(packets)

    def recvfrom(self, size):
        try:
            return next(self.packets), ('192.168.1.50', 5005)
        except StopIteration:
            raise EndOfPackets

def packet(sequence=1, uptime=200, state=0, maximum=2500, x=0, y=0):
    first = struct.pack('<HIIBBhhBBH', 101, sequence, uptime, state, 0, maximum, 0, x, y, 0)
    return first + struct.pack('<I', zlib.crc32(first) & 0xffffffff)

class ReceiverTests(unittest.TestCase):
    def setUp(self):
        dashboard.nodes.clear()
        dashboard.events.clear()
        for key in dashboard.counters:
            dashboard.counters[key] = 0

    def receive(self, *packets):
        with self.assertRaises(EndOfPackets):
            dashboard.receive(FakeSocket(packets))

    def test_valid_packet_and_size(self):
        payload = packet()
        self.assertEqual(len(payload), 24)
        self.receive(payload)
        self.assertEqual(dashboard.nodes[101]['max_temp_c'], 25.0)
        self.assertEqual(dashboard.nodes[101]['state'], 'NORMAL')

    def test_bad_length(self):
        self.receive(b'invalid')
        self.assertEqual(dashboard.counters['bad_length'], 1)
        self.assertFalse(dashboard.nodes)

    def test_corrupt_crc(self):
        payload = bytearray(packet())
        payload[10] ^= 1
        self.receive(bytes(payload))
        self.assertEqual(dashboard.counters['bad_crc'], 1)
        self.assertFalse(dashboard.nodes)

    def test_sequence_gap_and_duplicate(self):
        self.receive(packet(sequence=1), packet(sequence=4, uptime=800), packet(sequence=4, uptime=800))
        self.assertEqual(dashboard.nodes[101]['sequence_gaps'], 2)
        self.assertEqual(dashboard.nodes[101]['sequence'], 4)

    def test_reboot_resets_gaps(self):
        self.receive(packet(sequence=1), packet(sequence=4, uptime=800), packet(sequence=1, uptime=100))
        self.assertEqual(dashboard.nodes[101]['sequence_gaps'], 0)
        self.assertEqual(dashboard.nodes[101]['uptime_ms'], 100)

    def test_out_of_order_is_ignored(self):
        self.receive(packet(sequence=4, uptime=800), packet(sequence=3, uptime=800))
        self.assertEqual(dashboard.nodes[101]['sequence'], 4)

    def test_unavailable_value(self):
        self.receive(packet(state=3, maximum=-32768, x=255, y=255))
        self.assertIsNone(dashboard.nodes[101]['max_temp_c'])
        self.assertIsNone(dashboard.nodes[101]['hotspot'])

    def test_invalid_state(self):
        self.receive(packet(state=9))
        self.assertEqual(dashboard.counters['invalid'], 1)
        self.assertFalse(dashboard.nodes)

if __name__ == '__main__':
    unittest.main()
