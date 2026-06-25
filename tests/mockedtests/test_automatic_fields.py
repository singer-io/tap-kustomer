import unittest
from unittest.mock import MagicMock, patch

from tap_kustomer.streams import STREAMS
from tap_kustomer.sync import sync

from .base import KustomerBaseTest


class AutomaticFieldsMockedIntegrationTest(KustomerBaseTest, unittest.TestCase):
    def _run_stream(self, stream_name):
        payload = {
            "data": [
                {
                    "id": f"{stream_name}_1",
                    "attributes": {
                        "updatedAt": "2024-02-01T00:00:00Z",
                        "name": "Record",
                    },
                    "relationships": {"data": {}},
                }
            ],
            "links": {"next": None},
            "meta": {"total": 1},
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
            sync(client=client, config=self.config, catalog=catalog, state={})

        return [record for stream, record in written_records if stream == stream_name]

    def test_automatic_fields_primary_and_replication_keys_present(self):
        for stream_name in STREAMS.keys():
            with self.subTest(stream=stream_name):
                records = self._run_stream(stream_name)
                self.assertTrue(records)
                first_record = records[0]
                self.assertIn("id", first_record)
                self.assertIn("updated_at", first_record)
