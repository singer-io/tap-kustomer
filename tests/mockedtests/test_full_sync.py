import unittest
from unittest.mock import MagicMock, patch

from tap_kustomer.streams import STREAMS
from tap_kustomer.sync import sync

from .base import KustomerBaseTest


class FullSyncMockedIntegrationTest(KustomerBaseTest, unittest.TestCase):
    @patch("tap_kustomer.sync.singer.write_state")
    @patch("tap_kustomer.sync.singer.messages.write_record")
    @patch("tap_kustomer.sync.singer.write_schema")
    def test_sync_all_streams_with_mocked_fetch(self, mock_write_schema, mock_write_record, mock_write_state):
        catalog = self._make_catalog()

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"

        def _fetch_side_effect(method, url, path, data=None, **kwargs):
            return {
                "data": [
                    {
                        "id": f"{kwargs.get('endpoint', 'stream')}_1",
                        "attributes": {
                            "updatedAt": "2020-02-01T00:00:00Z",
                            "name": "Record",
                        },
                        "relationships": {"data": {}},
                    }
                ],
                "links": {"next": None},
                "meta": {"total": 1},
            }

        client.fetch.side_effect = _fetch_side_effect

        sync(client=client, config=self.config, catalog=catalog, state=self.state)

        self.assertEqual(mock_write_schema.call_count, len(STREAMS))
        self.assertGreaterEqual(mock_write_record.call_count, len(STREAMS))
        self.assertTrue(mock_write_state.called)

        self.assertIn("bookmarks", self.state)
        self.assertEqual(set(self.state["bookmarks"].keys()), set(STREAMS.keys()))
