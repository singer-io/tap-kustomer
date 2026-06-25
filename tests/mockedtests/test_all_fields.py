import json
import unittest
from unittest.mock import MagicMock, patch

from tap_kustomer.schema import get_abs_path
from tap_kustomer.sync import sync

from .base import KustomerBaseTest


class AllFieldsMockedIntegrationTest(KustomerBaseTest, unittest.TestCase):
    def test_all_fields_users_schema_present_in_written_record(self):
        stream_name = "users"
        schema_path = get_abs_path(f"schemas/{stream_name}.json")
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            schema = json.load(schema_file)

        expected_fields = set(schema.get("properties", {}).keys())

        attributes = {field: None for field in expected_fields}
        attributes["updatedAt"] = "2024-02-01T00:00:00Z"

        payload = {
            "data": [
                {
                    "id": "user_1",
                    "attributes": attributes,
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

        self.assertTrue(written_records)
        users_records = [record for stream, record in written_records if stream == stream_name]
        self.assertTrue(users_records)

        first_record = users_records[0]
        missing_fields = expected_fields - set(first_record.keys())
        self.assertEqual(missing_fields, set(), f"Missing schema fields in record: {missing_fields}")
