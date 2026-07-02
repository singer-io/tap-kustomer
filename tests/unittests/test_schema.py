import unittest

from tap_kustomer.schema import get_abs_path, get_schemas
from tap_kustomer.streams import STREAMS


class TestSchema(unittest.TestCase):
    def test_get_abs_path_points_to_tap_schema_file(self):
        path = get_abs_path("schemas/users.json")
        self.assertTrue(path.endswith("schemas\\users.json") or path.endswith("schemas/users.json"))

    def test_get_schemas_returns_stream_schemas_and_metadata(self):
        schemas, field_metadata = get_schemas()

        self.assertEqual(set(schemas.keys()), set(STREAMS.keys()))
        self.assertEqual(set(field_metadata.keys()), set(STREAMS.keys()))

        for stream_name in STREAMS:
            self.assertIn("type", schemas[stream_name])
            self.assertTrue(field_metadata[stream_name])
