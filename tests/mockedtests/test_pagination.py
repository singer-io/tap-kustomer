import unittest
from unittest.mock import MagicMock, patch

from tap_kustomer.sync import sync

from .base import KustomerBaseTest


class PaginationMockedIntegrationTest(KustomerBaseTest, unittest.TestCase):
    def test_pagination_fetches_all_pages_for_users(self):
        stream_name = "users"

        page_1 = {
            "data": [
                {
                    "id": "user_1",
                    "attributes": {"updatedAt": "2024-03-01T00:00:00Z"},
                    "relationships": {"data": {}},
                }
            ],
            "links": {"next": "?page=2"},
            "meta": {"total": 2},
        }
        page_2 = {
            "data": [
                {
                    "id": "user_2",
                    "attributes": {"updatedAt": "2024-03-02T00:00:00Z"},
                    "relationships": {"data": {}},
                }
            ],
            "links": {"next": None},
            "meta": {"total": 2},
        }

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"
        client.fetch.side_effect = [page_1, page_2]

        catalog = self._make_catalog([stream_name], client=client)
        written_records = []

        with patch("tap_kustomer.sync.singer.write_schema"), \
             patch("tap_kustomer.sync.singer.write_state"), \
             patch("tap_kustomer.sync.singer.messages.write_record",
                   side_effect=lambda s, r, time_extracted=None: written_records.append((s, r))):
            sync(client=client, config=self.config, catalog=catalog, state={})

        users_records = [record for stream, record in written_records if stream == stream_name]
        self.assertEqual(client.fetch.call_count, 2)
        self.assertEqual(len(users_records), 2)
