import json
import unittest
from unittest.mock import MagicMock, patch

from tap_kustomer.sync import (
    get_bookmark,
    process_records,
    sync_endpoint,
    write_record,
    update_currently_syncing,
    write_bookmark,
    write_schema,
    sync,
)


class TestSyncHelpers(unittest.TestCase):
    def test_get_bookmark_with_missing_state_returns_default(self):
        self.assertEqual(get_bookmark(None, "users", "default"), "default")
        self.assertEqual(get_bookmark({}, "users", "default"), "default")

    def test_get_bookmark_with_state_returns_stream_bookmark(self):
        state = {"bookmarks": {"users": "2020-01-01T00:00:00Z"}}
        self.assertEqual(get_bookmark(state, "users", "default"), "2020-01-01T00:00:00Z")

    @patch("tap_kustomer.sync.singer.write_state")
    def test_write_bookmark_updates_state_and_persists(self, mock_write_state):
        state = {}
        write_bookmark(state, "users", "2020-01-01T00:00:00Z")

        self.assertIn("bookmarks", state)
        self.assertEqual(state["bookmarks"]["users"], "2020-01-01T00:00:00Z")
        mock_write_state.assert_called_once_with(state)

    @patch("tap_kustomer.sync.singer.write_state")
    @patch("tap_kustomer.sync.singer.set_currently_syncing")
    def test_update_currently_syncing_sets_stream(self, mock_set_currently_syncing, mock_write_state):
        state = {}
        update_currently_syncing(state, "users")

        mock_set_currently_syncing.assert_called_once_with(state, "users")
        mock_write_state.assert_called_once_with(state)

    @patch("tap_kustomer.sync.singer.write_state")
    def test_update_currently_syncing_clears_existing_value(self, mock_write_state):
        state = {"currently_syncing": "users"}
        update_currently_syncing(state, None)

        self.assertNotIn("currently_syncing", state)
        mock_write_state.assert_called_once_with(state)

    @patch("tap_kustomer.sync.singer.write_schema")
    def test_write_schema_passes_expected_values(self, mock_write_schema):
        catalog = MagicMock()
        stream = MagicMock()
        stream.schema.to_dict.return_value = {"type": "object"}
        stream.key_properties = ["id"]
        catalog.get_stream.return_value = stream

        write_schema(catalog, "users")

        mock_write_schema.assert_called_once_with("users", {"type": "object"}, ["id"])


class TestSyncOrchestration(unittest.TestCase):
    @patch("tap_kustomer.sync.sync_endpoint")
    @patch("tap_kustomer.sync.update_currently_syncing")
    @patch("tap_kustomer.sync.singer.get_currently_syncing")
    def test_sync_runs_for_each_selected_stream(
        self,
        mock_get_currently_syncing,
        mock_update_currently_syncing,
        mock_sync_endpoint,
    ):
        mock_get_currently_syncing.return_value = None
        mock_sync_endpoint.return_value = 1

        selected = [MagicMock(stream="users"), MagicMock(stream="teams")]
        catalog = MagicMock()
        catalog.get_selected_streams.return_value = selected

        client = MagicMock()
        state = {}
        config = {"start_date": "2020-01-01T00:00:00Z", "date_window_size": 30, "page_size_limit": 100}

        sync(client=client, config=config, catalog=catalog, state=state)

        self.assertEqual(mock_sync_endpoint.call_count, 2)
        self.assertEqual(mock_update_currently_syncing.call_count, 4)

    @patch("tap_kustomer.sync.sync_endpoint")
    @patch("tap_kustomer.sync.singer.get_currently_syncing")
    def test_sync_returns_when_no_selected_streams(self, mock_get_currently_syncing, mock_sync_endpoint):
        mock_get_currently_syncing.return_value = None
        catalog = MagicMock()
        catalog.get_selected_streams.return_value = []

        sync(client=MagicMock(), config={"start_date": "2020-01-01T00:00:00Z"}, catalog=catalog, state={})

        mock_sync_endpoint.assert_not_called()


class TestWriteSchemaError(unittest.TestCase):
    """Covers lines 21-23: OSError in write_schema."""

    @patch("tap_kustomer.sync.singer.write_schema", side_effect=OSError("disk full"))
    def test_write_schema_oserror_reraises(self, mock_write_schema):
        catalog = MagicMock()
        stream = MagicMock()
        stream.schema.to_dict.return_value = {"type": "object"}
        stream.key_properties = ["id"]
        catalog.get_stream.return_value = stream

        with self.assertRaises(OSError):
            write_schema(catalog, "users")


class TestWriteRecordError(unittest.TestCase):
    """Covers lines 31-34: OSError in write_record."""

    @patch("tap_kustomer.sync.singer.messages.write_record", side_effect=OSError("broken pipe"))
    def test_write_record_oserror_reraises(self, mock_write_record):
        with self.assertRaises(OSError):
            write_record("users", {"id": "1"}, time_extracted=None)


class TestProcessRecordsNoBokmarkField(unittest.TestCase):
    """Covers lines 94-97: process_records without bookmark_field writes all records."""

    @patch("tap_kustomer.sync.write_record")
    def test_process_records_no_bookmark_field(self, mock_write_record):
        catalog = MagicMock()
        stream = MagicMock()
        stream.schema.to_dict.return_value = {
            "type": "object",
            "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
        }
        stream.metadata = []
        catalog.get_stream.return_value = stream

        records = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]

        max_bm, count = process_records(
            catalog=catalog,
            stream_name="users",
            records=records,
            time_extracted=None,
            bookmark_field=None,
            max_bookmark_value=None,
            last_datetime=None,
        )

        self.assertEqual(count, 2)
        self.assertEqual(mock_write_record.call_count, 2)


class TestSyncEndpoint(unittest.TestCase):
    """Covers lines 124-125, 162-168, 219-220, 238, 243-245, 286."""

    @patch("tap_kustomer.sync.write_schema")
    @patch("tap_kustomer.sync.utils.now")
    def test_sync_endpoint_empty_response_returns_zero(self, mock_now, mock_write_schema):
        """Covers lines 219-220: empty response breaks and returns 0."""
        from singer.utils import strptime_to_utc as real_strptime

        mock_now.return_value = real_strptime("2024-01-02T00:00:00Z")

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"
        client.fetch.return_value = {}

        catalog = MagicMock()
        endpoint_config = {"api_method": "GET", "params": {}, "body": None}

        result = sync_endpoint(
            client=client,
            catalog=catalog,
            state={},
            start_date="2024-01-01T00:00:00Z",
            stream_name="users",
            path="users",
            endpoint_config=endpoint_config,
            static_params={},
            bookmark_query_field_from=None,
            bookmark_query_field_to=None,
            bookmark_field="updated_at",
            bookmark_type="datetime",
            data_key="data",
            id_fields=["id"],
            days_interval=30,
            page_size_limit=100,
        )

        self.assertEqual(result, 0)

    @patch("tap_kustomer.sync.strptime_to_utc")
    @patch("tap_kustomer.sync.process_records")
    @patch("tap_kustomer.sync.transform_json")
    @patch("tap_kustomer.sync.write_schema")
    @patch("tap_kustomer.sync.utils.now")
    def test_sync_endpoint_integer_bookmark_type(
        self, mock_now, mock_write_schema, mock_transform, mock_process, mock_strptime
    ):
        """Covers lines 124-125, 162-168: integer bookmark type path."""
        from singer.utils import strptime_to_utc as real_strptime

        fake_now = real_strptime("2024-01-02T00:00:00Z")
        mock_now.return_value = fake_now
        mock_strptime.return_value = real_strptime("2024-01-01T00:00:00Z")
        mock_transform.return_value = [{"id": "1", "seq": 5}]
        mock_process.return_value = (5, 1)

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"
        client.fetch.return_value = {
            "data": [{"id": "1", "attributes": {"updatedAt": "2024-01-01T12:00:00Z"}}],
            "meta": {"total": 1},
            "links": {"next": None},
        }

        catalog = MagicMock()
        endpoint_config = {"api_method": "GET", "params": {"page": 1, "pageSize": 100}, "body": None}

        result = sync_endpoint(
            client=client,
            catalog=catalog,
            state={"bookmarks": {"users": 3}},
            start_date="2024-01-01T00:00:00Z",
            stream_name="users",
            path="users",
            endpoint_config=endpoint_config,
            static_params={},
            bookmark_query_field_from="sinceId",
            bookmark_query_field_to="untilId",
            bookmark_field="seq",
            bookmark_type="integer",
            data_key="data",
            id_fields=["id"],
            days_interval=30,
            page_size_limit=100,
        )

        self.assertEqual(result, 1)

    @patch("tap_kustomer.sync.process_records")
    @patch("tap_kustomer.sync.transform_json")
    @patch("tap_kustomer.sync.write_schema")
    @patch("tap_kustomer.sync.utils.now")
    def test_sync_endpoint_missing_id_field_logs_warning(
        self, mock_now, mock_write_schema, mock_transform, mock_process
    ):
        """Covers lines 243-245: missing key in record logs info."""
        from singer.utils import strptime_to_utc as real_strptime

        mock_now.return_value = real_strptime("2024-01-02T00:00:00Z")
        mock_transform.return_value = [{"name": "Alice"}]  # missing 'id'
        mock_process.return_value = ("2024-01-01T12:00:00Z", 1)

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"
        client.fetch.return_value = {
            "data": [{"id": "1", "attributes": {"updatedAt": "2024-01-01T12:00:00Z"}}],
            "meta": {"total": 1},
            "links": {"next": None},
        }

        catalog = MagicMock()
        endpoint_config = {"api_method": "GET", "params": {}, "body": None}

        result = sync_endpoint(
            client=client,
            catalog=catalog,
            state={},
            start_date="2024-01-01T00:00:00Z",
            stream_name="users",
            path="users",
            endpoint_config=endpoint_config,
            static_params={},
            bookmark_query_field_from="updatedAt_gte",
            bookmark_query_field_to=None,
            bookmark_field="updated_at",
            bookmark_type="datetime",
            data_key="data",
            id_fields=["id"],
            days_interval=30,
            page_size_limit=100,
        )

        self.assertEqual(result, 1)

    @patch("tap_kustomer.sync.process_records")
    @patch("tap_kustomer.sync.transform_json")
    @patch("tap_kustomer.sync.write_schema")
    @patch("tap_kustomer.sync.utils.now")
    def test_sync_endpoint_data_key_none_uses_results(
        self, mock_now, mock_write_schema, mock_transform, mock_process
    ):
        """Covers line 238: data_key=None uses 'results' key."""
        from singer.utils import strptime_to_utc as real_strptime

        mock_now.return_value = real_strptime("2024-01-02T00:00:00Z")
        mock_transform.return_value = [{"id": "1"}]
        mock_process.return_value = ("2024-01-01T12:00:00Z", 1)

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"
        client.fetch.return_value = {
            "data": [{"id": "1", "attributes": {"updatedAt": "2024-01-01T12:00:00Z"}}],
            "meta": {"total": 1},
            "links": {"next": None},
        }

        catalog = MagicMock()
        endpoint_config = {"api_method": "GET", "params": {}, "body": None}

        result = sync_endpoint(
            client=client,
            catalog=catalog,
            state={},
            start_date="2024-01-01T00:00:00Z",
            stream_name="users",
            path="users",
            endpoint_config=endpoint_config,
            static_params={},
            bookmark_field="updated_at",
            bookmark_type="datetime",
            data_key=None,
            id_fields=["id"],
            days_interval=30,
            page_size_limit=100,
        )

        # Verify transform_json was called with 'results' as data_key
        mock_transform.assert_called_once()
        self.assertEqual(mock_transform.call_args[0][2], "results")

    @patch("tap_kustomer.sync.transform_json")
    @patch("tap_kustomer.sync.write_schema")
    @patch("tap_kustomer.sync.utils.now")
    def test_sync_endpoint_no_transformed_data_breaks(
        self, mock_now, mock_write_schema, mock_transform
    ):
        """Covers empty transformed_data breaking the loop."""
        from singer.utils import strptime_to_utc as real_strptime

        mock_now.return_value = real_strptime("2024-01-02T00:00:00Z")
        mock_transform.return_value = []

        client = MagicMock()
        client.base_url = "https://api.kustomerapp.com/v1"
        client.fetch.return_value = {
            "data": [{"id": "1", "attributes": {"updatedAt": "2024-01-01T12:00:00Z"}}],
            "meta": {"total": 1},
            "links": {"next": None},
        }

        catalog = MagicMock()
        endpoint_config = {"api_method": "GET", "params": {}, "body": None}

        result = sync_endpoint(
            client=client,
            catalog=catalog,
            state={},
            start_date="2024-01-01T00:00:00Z",
            stream_name="users",
            path="users",
            endpoint_config=endpoint_config,
            static_params={},
            bookmark_field="updated_at",
            bookmark_type="datetime",
            data_key="data",
            id_fields=["id"],
            days_interval=30,
            page_size_limit=100,
        )

        self.assertEqual(result, 0)
