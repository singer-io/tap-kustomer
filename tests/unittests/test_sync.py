import unittest
from unittest.mock import MagicMock, patch

from tap_kustomer.sync import (
    get_bookmark,
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
