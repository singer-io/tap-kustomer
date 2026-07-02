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

    # --- Tests for uncovered lines ---

    def test_raise_for_error_errors_array_style(self):
        """Covers lines 84-85: 'errors' array-style response handling."""
        from tap_kustomer.client import KustomerBadRequestError

        response = FakeResponse(
            status_code=400,
            payload={"errors": [{"code": "INVALID", "title": "Bad field"}]},
            content=b'{"errors":[]}',
        )
        with self.assertRaises(KustomerBadRequestError) as ctx:
            raise_for_error(response)
        self.assertIn("INVALID", str(ctx.exception))
        self.assertIn("Bad field", str(ctx.exception))

    def test_raise_for_error_errors_array_empty(self):
        """Covers line 84: empty 'errors' array falls back to defaults."""
        response = FakeResponse(
            status_code=400,
            payload={"errors": []},
            content=b'{"errors":[]}',
        )
        with self.assertRaises(KustomerError):
            raise_for_error(response)

    def test_raise_for_error_expired_token(self):
        """Covers lines 92-96: 401 with 'Expired token' message."""
        from tap_kustomer.client import KustomerUnauthorizedError

        response = FakeResponse(
            status_code=401,
            payload={"error": "Expired token", "message": "Token has expired"},
            content=b'{"error":"Expired token"}',
        )
        with self.assertRaises(KustomerUnauthorizedError) as ctx:
            raise_for_error(response)
        self.assertIn("Expired token", str(ctx.exception))

    def test_raise_for_error_json_parse_error(self):
        """Covers line 99: ValueError when response.json() fails."""
        import requests as req

        class BadJsonResponse:
            status_code = 500
            content = b"not json"
            headers = {}

            def raise_for_status(self):
                raise req.HTTPError("500 Server Error")

            def json(self):
                raise ValueError("No JSON")

        with self.assertRaises(KustomerError):
            raise_for_error(BadJsonResponse())

    def test_context_manager_enter_exit(self):
        """Covers lines 111-112, 115: __enter__ calls check_token, __exit__ closes session."""
        client = KustomerClient(token="abc")
        raw_check_token = KustomerClient.check_token.__wrapped__.__wrapped__

        with patch.object(KustomerClient, "check_token", wraps=raw_check_token) as mock_check:
            mock_check.return_value = True
            result = client.__enter__()
            self.assertIs(result, client)
            mock_check.assert_called_once()

        with patch.object(client._KustomerClient__session, "close") as mock_close:
            client.__exit__(None, None, None)
            mock_close.assert_called_once()

    def test_check_token_success(self):
        """Covers lines 122-138: successful token check."""
        client = KustomerClient(token="abc", user_agent="test-agent")
        response = FakeResponse(status_code=200, payload={"results": [{"id": "1"}]})
        client._KustomerClient__session.get = MagicMock(return_value=response)

        raw_check_token = KustomerClient.check_token.__wrapped__.__wrapped__
        result = raw_check_token(client)
        self.assertTrue(result)

    def test_check_token_non_200_raises(self):
        """Covers lines 133-135: check_token with non-200 status."""
        client = KustomerClient(token="abc")
        response = FakeResponse(
            status_code=400,
            payload={"error": "bad", "message": "Bad request"},
            content=b'{"error":"bad"}',
        )
        client._KustomerClient__session.get = MagicMock(return_value=response)

        raw_check_token = KustomerClient.check_token.__wrapped__.__wrapped__
        with self.assertRaises(KustomerError):
            raw_check_token(client)

    def test_check_token_no_results_returns_false(self):
        """Covers line 138: check_token returns False when no 'results' key."""
        client = KustomerClient(token="abc")
        response = FakeResponse(status_code=200, payload={"data": []})
        client._KustomerClient__session.get = MagicMock(return_value=response)

        raw_check_token = KustomerClient.check_token.__wrapped__.__wrapped__
        result = raw_check_token(client)
        self.assertFalse(result)

    @patch("tap_kustomer.client.metrics.http_request_timer")
    def test_request_calls_check_token_when_not_verified(self, mock_http_timer):
        """Covers line 147: request calls check_token when not verified."""
        timer_cm = MagicMock()
        timer_cm.__enter__.return_value = MagicMock(tags={})
        timer_cm.__exit__.return_value = False
        mock_http_timer.return_value = timer_cm

        client = KustomerClient(token="abc")
        client._KustomerClient__verified = False

        response = FakeResponse(status_code=200, payload={"ok": True}, headers={})
        client._KustomerClient__session.request = MagicMock(return_value=response)

        raw_check_token = KustomerClient.check_token.__wrapped__.__wrapped__
        with patch.object(KustomerClient, "check_token", wraps=raw_check_token) as mock_check:
            mock_check.return_value = True
            raw_request = KustomerClient.request.__wrapped__.__wrapped__
            result = raw_request(client, "GET", path="users", endpoint="users")
            mock_check.assert_called_once()
        self.assertEqual(result, {"ok": True})

    @patch("tap_kustomer.client.sleep")
    @patch("tap_kustomer.client.metrics.http_request_timer")
    def test_request_rate_limit_invalid_reset_value(self, mock_http_timer, mock_sleep):
        """Covers lines 188-189: rate limit with invalid reset header value."""
        timer_cm = MagicMock()
        timer_cm.__enter__.return_value = MagicMock(tags={})
        timer_cm.__exit__.return_value = False
        mock_http_timer.return_value = timer_cm

        client = KustomerClient(token="abc")
        client._KustomerClient__verified = True
        headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "not-a-number"}
        client._KustomerClient__session.request = MagicMock(
            return_value=FakeResponse(status_code=200, payload={"ok": True}, headers=headers)
        )

        raw_request = KustomerClient.request.__wrapped__.__wrapped__
        with self.assertRaises(Server429Error):
            raw_request(client, "GET", path="users", endpoint="users")
        mock_sleep.assert_called_once_with(0)

    @patch("tap_kustomer.client.metrics.http_request_timer")
    def test_request_non_200_calls_raise_for_error(self, mock_http_timer):
        """Covers line 200: non-200 status (not 401/403/5xx) calls raise_for_error."""
        from tap_kustomer.client import KustomerNotFoundError

        timer_cm = MagicMock()
        timer_cm.__enter__.return_value = MagicMock(tags={})
        timer_cm.__exit__.return_value = False
        mock_http_timer.return_value = timer_cm

        client = KustomerClient(token="abc")
        client._KustomerClient__verified = True
        response = FakeResponse(
            status_code=404,
            payload={"error": "not_found", "message": "Resource not found"},
            content=b'{"error":"not_found"}',
        )
        client._KustomerClient__session.request = MagicMock(return_value=response)

        raw_request = KustomerClient.request.__wrapped__.__wrapped__
        with self.assertRaises(KustomerNotFoundError):
            raw_request(client, "GET", path="users/123", endpoint="users")

    def test_check_stream_access_returns_false_on_forbidden(self):
        """Covers line 220: check_stream_access returns False on KustomerForbiddenError."""
        from tap_kustomer.client import KustomerForbiddenError

        client = KustomerClient(token="abc")
        client.request = MagicMock(side_effect=KustomerForbiddenError("Forbidden"))

        result = client.check_stream_access("conversations", "GET", "conversations")
        self.assertFalse(result)

    def test_get_delegates_to_request(self):
        """Covers line 223: get method calls request."""
        client = KustomerClient(token="abc")
        client.request = MagicMock(return_value={"data": []})

        result = client.get(url=None, path="users")
        self.assertEqual(result, {"data": []})
        client.request.assert_called_once_with("GET", url=None, path="users")
