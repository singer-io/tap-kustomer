import unittest
from unittest.mock import MagicMock, patch

from tap_kustomer.client import (
    KustomerClient,
    KustomerError,
    Server429Error,
    Server5xxError,
    get_exception_for_error_code,
    raise_for_error,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, content=b"x"):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"status={self.status_code}")

    def json(self):
        return self._payload


class TestClient(unittest.TestCase):
    def test_get_exception_for_error_code_unknown(self):
        self.assertIs(get_exception_for_error_code(999), KustomerError)

    def test_raise_for_error_raises_kustomer_error_for_api_error_payload(self):
        response = FakeResponse(
            status_code=400,
            payload={"error": {"code": 400}, "message": "Bad input"},
            content=b"{\"error\":true}",
        )

        with self.assertRaises(KustomerError):
            raise_for_error(response)

    def test_raise_for_error_returns_when_no_content(self):
        response = FakeResponse(status_code=500, payload={}, content=b"")
        self.assertIsNone(raise_for_error(response))

    def test_check_token_missing_token_raises(self):
        client = KustomerClient(token=None)
        raw_check_token = KustomerClient.check_token.__wrapped__.__wrapped__
        with self.assertRaises(Exception):
            raw_check_token(client)

    @patch("tap_kustomer.client.metrics.http_request_timer")
    def test_request_sets_headers_and_returns_json(self, mock_http_timer):
        timer_cm = MagicMock()
        timer_cm.__enter__.return_value = MagicMock(tags={})
        timer_cm.__exit__.return_value = False
        mock_http_timer.return_value = timer_cm

        client = KustomerClient(token="abc", user_agent="ua")
        client._KustomerClient__verified = True

        response = FakeResponse(status_code=200, payload={"ok": True}, headers={})
        client._KustomerClient__session.request = MagicMock(return_value=response)

        raw_request = KustomerClient.request.__wrapped__.__wrapped__
        result = raw_request(client, "POST", path="users", data="{}", endpoint="users")

        self.assertEqual(result, {"ok": True})
        called_kwargs = client._KustomerClient__session.request.call_args.kwargs
        self.assertEqual(called_kwargs["headers"]["Authorization"], "Bearer abc")
        self.assertEqual(called_kwargs["headers"]["Accept"], "application/json")
        self.assertEqual(called_kwargs["headers"]["User-Agent"], "ua")
        self.assertEqual(called_kwargs["headers"]["Content-Type"], "application/json")

    @patch("tap_kustomer.client.metrics.http_request_timer")
    def test_request_raises_server_5xx(self, mock_http_timer):
        timer_cm = MagicMock()
        timer_cm.__enter__.return_value = MagicMock(tags={})
        timer_cm.__exit__.return_value = False
        mock_http_timer.return_value = timer_cm

        client = KustomerClient(token="abc")
        client._KustomerClient__verified = True
        client._KustomerClient__session.request = MagicMock(return_value=FakeResponse(status_code=500))

        raw_request = KustomerClient.request.__wrapped__.__wrapped__
        with self.assertRaises(Server5xxError):
            raw_request(client, "GET", path="users", endpoint="users")

    @patch("tap_kustomer.client.sleep")
    @patch("tap_kustomer.client.metrics.http_request_timer")
    def test_request_rate_limit_raises_server429(self, mock_http_timer, mock_sleep):
        timer_cm = MagicMock()
        timer_cm.__enter__.return_value = MagicMock(tags={})
        timer_cm.__exit__.return_value = False
        mock_http_timer.return_value = timer_cm

        client = KustomerClient(token="abc")
        client._KustomerClient__verified = True
        headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "9999999999"}
        client._KustomerClient__session.request = MagicMock(
            return_value=FakeResponse(status_code=200, payload={"ok": True}, headers=headers)
        )

        raw_request = KustomerClient.request.__wrapped__.__wrapped__
        with self.assertRaises(Server429Error):
            raw_request(client, "GET", path="users", endpoint="users")
        self.assertTrue(mock_sleep.called)

    def test_fetch_routes_to_get_and_post(self):
        client = KustomerClient(token="abc")
        client.get = MagicMock(return_value={"method": "GET"})
        client.post = MagicMock(return_value={"method": "POST"})

        self.assertEqual(client.fetch("GET", url="u", path="p"), {"method": "GET"})
        self.assertEqual(client.fetch("POST", url="u", path="p", data="{}"), {"method": "POST"})
        client.get.assert_called_once()
        client.post.assert_called_once()
