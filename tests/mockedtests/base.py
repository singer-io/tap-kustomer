"""Base helpers for tap-kustomer mocked integration tests."""
from singer import metadata
from singer.catalog import Catalog

from tap_kustomer.discover import discover
from tap_kustomer.streams import STREAMS


class KustomerBaseTest:
    PRIMARY_KEYS = "primary_keys"
    REPLICATION_METHOD = "replication_method"
    REPLICATION_KEYS = "replication_keys"

    default_start_date = "2020-01-01T00:00:00Z"

    @classmethod
    def expected_metadata(cls):
        return {
            stream_name: {
                cls.PRIMARY_KEYS: set(stream_cfg.get("key_properties", [])),
                cls.REPLICATION_METHOD: stream_cfg.get("replication_method"),
                cls.REPLICATION_KEYS: set(stream_cfg.get("replication_keys", [])),
            }
            for stream_name, stream_cfg in STREAMS.items()
        }

    def expected_stream_names(self):
        return set(self.expected_metadata().keys())

    def setUp(self):
        self.config = {
            "api_token": "mock_token",
            "user_agent": "tap-kustomer <tests@example.com>",
            "start_date": self.default_start_date,
            "date_window_size": 30,
            "page_size_limit": 100,
        }
        self.state = {}

    @staticmethod
    def _make_catalog(stream_names=None):
        catalog = discover()
        if stream_names is None:
            stream_names = {entry.tap_stream_id for entry in catalog.streams}
        else:
            stream_names = set(stream_names)

        selected_entries = []
        for entry in catalog.streams:
            if entry.tap_stream_id not in stream_names:
                continue
            mdata = metadata.to_map(entry.metadata)
            mdata[()] = dict(mdata.get((), {}))
            mdata[()]["selected"] = True
            entry.metadata = metadata.to_list(mdata)
            selected_entries.append(entry)

        selected_catalog = Catalog(selected_entries)
        selected_catalog.get_selected_streams = lambda _state: selected_entries
        return selected_catalog
