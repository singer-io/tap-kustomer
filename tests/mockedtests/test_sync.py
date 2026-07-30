import unittest
from unittest.mock import MagicMock, patch

from .base import KustomerBaseTest
from tap_kustomer.sync import sync


class SyncMockedIntegrationTest(KustomerBaseTest, unittest.TestCase):

    @patch("tap_kustomer.sync.singer.write_state")
    @patch("tap_kustomer.sync.singer.messages.write_record")
    @patch("tap_kustomer.sync.singer.write_schema")
    def test_sync_users_stream_with_mocked_fetch(self, mock_write_schema, mock_write_record, mock_write_state):

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"

        client.fetch.return_value = {
            "data": [
                {
                    "id": "user_1",
                    "attributes": {
                        "updatedAt": "2020-02-01T00:00:00Z",
                        "name": "Alice"
                    },
                    "relationships": {"data": {}}
                }
            ],
            "links": {"next": None},
            "meta": {"total": 1}
        }

        catalog = self._make_catalog(["users"], client=client)
        sync(client=client, config=self.config, catalog=catalog, state=self.state)

        self.assertTrue(mock_write_schema.called)
        self.assertEqual(mock_write_record.call_count, 1)
        self.assertTrue(mock_write_state.called)
        self.assertIn("bookmarks", self.state)
        self.assertIn("users", self.state["bookmarks"])
