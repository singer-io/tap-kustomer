import unittest

from tap_kustomer.discover import discover
from tap_kustomer.streams import STREAMS


class TestDiscover(unittest.TestCase):

    def test_discover_returns_all_streams(self):
        catalog = discover()
        actual = {entry.tap_stream_id for entry in catalog.streams}
        self.assertEqual(actual, set(STREAMS.keys()))

    def test_discover_catalog_entry_key_properties(self):
        catalog = discover()
        stream_map = {entry.tap_stream_id: entry for entry in catalog.streams}

        for stream_name, stream_cfg in STREAMS.items():
            self.assertEqual(stream_map[stream_name].key_properties, stream_cfg["key_properties"])
