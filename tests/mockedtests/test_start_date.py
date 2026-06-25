import unittest
from unittest.mock import MagicMock, patch

from tap_kustomer.sync import sync

from .base import KustomerBaseTest


class StartDateMockedIntegrationTest(KustomerBaseTest, unittest.TestCase):
    def test_start_date_filters_out_old_records_without_bookmark(self):
        stream_name = "users"
        config = {**self.config, "start_date": "2024-02-01T00:00:00Z"}
        state = {}

        payload = {
            "data": [
                {
                    "id": "user_old",
                    "attributes": {"updatedAt": "2024-01-01T00:00:00Z"},
                    "relationships": {"data": {}},
                },
                {
                    "id": "user_new",
                    "attributes": {"updatedAt": "2024-03-01T00:00:00Z"},
                    "relationships": {"data": {}},
                },
            ],
            "links": {"next": None},
            "meta": {"total": 2},
        }

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"
        client.fetch.return_value = payload

        catalog = self._make_catalog([stream_name])
        written_records = []

        with patch("tap_kustomer.sync.singer.write_schema"), \
             patch("tap_kustomer.sync.singer.write_state"), \
             patch("tap_kustomer.sync.singer.messages.write_record",
                   side_effect=lambda s, r, time_extracted=None: written_records.append((s, r))):
            sync(client=client, config=config, catalog=catalog, state=state)

        users_records = [record for stream, record in written_records if stream == stream_name]
        self.assertEqual(len(users_records), 1)
        self.assertEqual(users_records[0]["id"], "user_new")
