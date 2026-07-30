import unittest

from singer import metadata
from unittest.mock import MagicMock
from .base import KustomerBaseTest
from tap_kustomer.discover import discover


class DiscoveryMockedIntegrationTest(KustomerBaseTest, unittest.TestCase):

    def test_discovery_streams_and_metadata(self):
        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"
        catalog = discover(client)
        stream_map = {stream.tap_stream_id: stream for stream in catalog.streams}

        self.assertEqual(set(stream_map.keys()), self.expected_stream_names())

        for stream_name, expected in self.expected_metadata().items():
            with self.subTest(stream=stream_name):
                root = metadata.to_map(stream_map[stream_name].metadata)[()]
                self.assertEqual(set(root.get("table-key-properties", [])), expected[self.PRIMARY_KEYS])
                self.assertEqual(root.get("forced-replication-method"), expected[self.REPLICATION_METHOD])
                self.assertEqual(set(root.get("valid-replication-keys", [])), expected[self.REPLICATION_KEYS])
