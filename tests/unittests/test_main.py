import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tap_kustomer.__init__ import do_discover, main


class TestMainDiscover(unittest.TestCase):

    @patch("tap_kustomer.__init__.json.dump")
    @patch("tap_kustomer.__init__.discover")
    def test_do_discover_emits_catalog(self, mock_discover, mock_dump):
        fake_catalog = MagicMock()
        fake_catalog.to_dict.return_value = {"streams": []}
        mock_discover.return_value = fake_catalog

        do_discover()

        fake_catalog.to_dict.assert_called_once()
        mock_dump.assert_called_once()

    @patch("tap_kustomer.__init__.sync")
    @patch("tap_kustomer.__init__.KustomerClient")
    @patch("tap_kustomer.__init__.singer.utils.parse_args")
    def test_main_runs_sync_when_catalog_present(self, mock_parse_args, mock_client_cls, mock_sync):
        parsed = SimpleNamespace(
            config={"api_token": "token", "user_agent": "ua", "start_date": "2020-01-01T00:00:00Z"},
            state={"bookmarks": {}},
            discover=False,
            catalog=MagicMock(),
        )
        mock_parse_args.return_value = parsed

        client_cm = MagicMock()
        client = MagicMock()
        client_cm.__enter__.return_value = client
        client_cm.__exit__.return_value = False
        mock_client_cls.return_value = client_cm

        main.__wrapped__()

        mock_sync.assert_called_once_with(
            client=client,
            config=parsed.config,
            catalog=parsed.catalog,
            state=parsed.state,
        )

    @patch("tap_kustomer.__init__.do_discover")
    @patch("tap_kustomer.__init__.KustomerClient")
    @patch("tap_kustomer.__init__.singer.utils.parse_args")
    def test_main_runs_discover_when_flag_enabled(self, mock_parse_args, mock_client_cls, mock_do_discover):
        parsed = SimpleNamespace(
            config={"api_token": "token", "user_agent": "ua", "start_date": "2020-01-01T00:00:00Z"},
            state=None,
            discover=True,
            catalog=None,
        )
        mock_parse_args.return_value = parsed

        client_cm = MagicMock()
        client_cm.__enter__.return_value = MagicMock()
        client_cm.__exit__.return_value = False
        mock_client_cls.return_value = client_cm

        main.__wrapped__()

        mock_do_discover.assert_called_once_with()
