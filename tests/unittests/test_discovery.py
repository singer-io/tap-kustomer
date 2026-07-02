import json
import pytest
from unittest.mock import patch, MagicMock
from singer.catalog import Catalog
from tap_kustomer.discover import discover, _apply_access_checks, _check_stream_access
from tap_kustomer.client import KustomerForbiddenError
from tap_kustomer.schema import get_schemas
from tap_kustomer.streams import STREAMS


def _mock_client(forbidden_streams=None):
    """Create a mock KustomerClient that returns 403 for specified streams."""
    forbidden_streams = forbidden_streams or []
    client = MagicMock()

    def _check_access(stream_name, method, path, body=None):
        # Match stream by body queryContext (POST) or path (GET)
        if body:
            parsed = json.loads(body)
            context = parsed.get('queryContext', '')
            for s in forbidden_streams:
                stream_cfg = STREAMS.get(s, {})
                stream_body = stream_cfg.get('body', {})
                if stream_body.get('queryContext') == context:
                    return False
        else:
            for s in forbidden_streams:
                stream_cfg = STREAMS.get(s, {})
                stream_path = stream_cfg.get('path', s)
                if stream_path == path:
                    return False
        return True

    client.check_stream_access = MagicMock(side_effect=_check_access)
    return client


class TestDiscoverAllAccessible:
    """Discovery with full access to all streams."""

    def test_returns_catalog(self):
        client = _mock_client()
        catalog = discover(client)
        assert isinstance(catalog, Catalog)

    def test_all_streams_in_catalog(self):
        client = _mock_client()
        catalog = discover(client)
        stream_names = {s.stream for s in catalog.streams}
        assert stream_names == set(STREAMS.keys())

    def test_catalog_entry_has_key_properties(self):
        client = _mock_client()
        catalog = discover(client)
        for entry in catalog.streams:
            expected = STREAMS[entry.stream]['key_properties']
            assert entry.key_properties == expected

    def test_catalog_entry_has_schema(self):
        client = _mock_client()
        catalog = discover(client)
        for entry in catalog.streams:
            assert entry.schema is not None
            assert entry.schema.to_dict()

    def test_catalog_entry_has_metadata(self):
        client = _mock_client()
        catalog = discover(client)
        for entry in catalog.streams:
            assert entry.metadata is not None


class TestDiscoverPartialAccess:
    """Discovery when some streams return 403."""

    def test_excludes_forbidden_stream(self):
        client = _mock_client(forbidden_streams=['users'])
        catalog = discover(client)
        stream_names = {s.stream for s in catalog.streams}
        assert 'users' not in stream_names

    def test_keeps_accessible_streams(self):
        client = _mock_client(forbidden_streams=['users'])
        catalog = discover(client)
        stream_names = {s.stream for s in catalog.streams}
        expected = set(STREAMS.keys()) - {'users'}
        assert stream_names == expected

    def test_excludes_multiple_forbidden_streams(self):
        client = _mock_client(forbidden_streams=['users', 'teams', 'tags'])
        catalog = discover(client)
        stream_names = {s.stream for s in catalog.streams}
        assert 'users' not in stream_names
        assert 'teams' not in stream_names
        assert 'tags' not in stream_names

    def test_logs_warning_for_excluded_streams(self):
        client = _mock_client(forbidden_streams=['users'])
        with patch('tap_kustomer.discover.LOGGER') as mock_logger:
            discover(client)
            mock_logger.warning.assert_called_once_with(
                "Unauthorized streams have been excluded: %s",
                "users",
            )

    def test_logs_warning_lists_all_excluded_streams(self):
        client = _mock_client(forbidden_streams=['users', 'teams'])
        with patch('tap_kustomer.discover.LOGGER') as mock_logger:
            discover(client)
            mock_logger.warning.assert_called_once()
            logged_streams = mock_logger.warning.call_args[0][1]
            assert 'users' in logged_streams
            assert 'teams' in logged_streams


class TestDiscoverNoAccess:
    """Discovery when no streams are accessible."""

    def test_raises_forbidden_error(self):
        all_streams = list(STREAMS.keys())
        client = _mock_client(forbidden_streams=all_streams)
        with pytest.raises(KustomerForbiddenError):
            discover(client)

    def test_raises_with_descriptive_message(self):
        all_streams = list(STREAMS.keys())
        client = _mock_client(forbidden_streams=all_streams)
        with pytest.raises(KustomerForbiddenError, match="No streams are accessible"):
            discover(client)


class TestApplyAccessChecks:
    """Unit tests for _apply_access_checks."""

    def test_removes_inaccessible_from_schemas(self):
        schemas, field_metadata = get_schemas()
        client = _mock_client(forbidden_streams=['users'])
        _apply_access_checks(client, schemas, field_metadata)
        assert 'users' not in schemas

    def test_removes_inaccessible_from_field_metadata(self):
        schemas, field_metadata = get_schemas()
        client = _mock_client(forbidden_streams=['users'])
        _apply_access_checks(client, schemas, field_metadata)
        assert 'users' not in field_metadata

    def test_no_change_when_all_accessible(self):
        schemas, field_metadata = get_schemas()
        original_keys = set(schemas.keys())
        client = _mock_client()
        _apply_access_checks(client, schemas, field_metadata)
        assert set(schemas.keys()) == original_keys


class TestCheckStreamAccess:
    """Unit tests for _check_stream_access."""

    def test_get_stream_accessible(self):
        client = MagicMock()
        client.check_stream_access.return_value = True
        result = _check_stream_access(client, 'users', STREAMS['users'])
        assert result is True
        client.check_stream_access.assert_called_once_with(
            'users', 'GET', 'users', body=None
        )

    def test_post_stream_sends_body(self):
        client = MagicMock()
        client.check_stream_access.return_value = True
        result = _check_stream_access(client, 'customers', STREAMS['customers'])
        assert result is True
        call_args = client.check_stream_access.call_args
        assert call_args[0][0] == 'customers'
        assert call_args[0][1] == 'POST'
        assert call_args[1]['body'] is not None
        body = json.loads(call_args[1]['body'])
        assert body.get('queryContext') == 'customer'

    def test_post_stream_replaces_placeholder_with_valid_timestamp(self):
        client = MagicMock()
        client.check_stream_access.return_value = True
        _check_stream_access(client, 'customers', STREAMS['customers'])
        call_args = client.check_stream_access.call_args
        body = json.loads(call_args[1]['body'])
        bookmark_field = STREAMS['customers']['bookmark_query_field']
        gte_value = body['and'][0][bookmark_field]['gte']
        # Should be a recent timestamp (1 day ago), not a hardcoded old date
        from datetime import datetime, timezone
        parsed = datetime.strptime(gte_value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert (now - parsed).days <= 1
        assert '{end_window}' not in call_args[1]['body']

    def test_returns_false_when_forbidden(self):
        client = MagicMock()
        client.check_stream_access.return_value = False
        result = _check_stream_access(client, 'users', STREAMS['users'])
        assert result is False


class TestCheckStreamAccessLogging:
    """Unit tests for the warning log in KustomerClient.check_stream_access."""

    def test_logs_warning_on_403(self):
        from unittest.mock import patch
        from tap_kustomer.client import KustomerClient, KustomerForbiddenError

        with patch('tap_kustomer.client.LOGGER') as mock_logger:
            client = KustomerClient('fake_token', 'test-agent')
            client._KustomerClient__verified = True

            with patch.object(client, 'request',
                              side_effect=KustomerForbiddenError('403 Forbidden')):
                result = client.check_stream_access('users', 'GET', 'users')

            assert result is False
            mock_logger.warning.assert_called_once_with(
                "Unauthorized Stream: %s, excluding from catalog. "
                "HTTP-Error-Message:'%s'",
                'users',
                '403 Forbidden',
            )

    def test_no_warning_on_success(self):
        from unittest.mock import patch
        from tap_kustomer.client import KustomerClient

        with patch('tap_kustomer.client.LOGGER') as mock_logger:
            client = KustomerClient('fake_token', 'test-agent')
            client._KustomerClient__verified = True

            with patch.object(client, 'request', return_value={}):
                result = client.check_stream_access('users', 'GET', 'users')

            assert result is True
            mock_logger.warning.assert_not_called()


class TestRequestRaises403:
    """Unit test for the KustomerForbiddenError raised by request() on 401/403."""

    def test_request_raises_forbidden_on_403_with_response_text(self):
        from unittest.mock import patch
        from tap_kustomer.client import KustomerClient, KustomerForbiddenError

        with patch('requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session

            forbidden_response = MagicMock()
            forbidden_response.status_code = 403
            forbidden_response.text = '{"error": "Access denied for this resource"}'
            forbidden_response.headers = {}

            mock_session.request.return_value = forbidden_response

            client = KustomerClient('fake_token', 'test-agent')
            client._KustomerClient__verified = True

            import pytest
            with pytest.raises(KustomerForbiddenError) as exc_info:
                client.request('GET', path='teams')

            assert 'HTTP-error-code: 403' in str(exc_info.value)
            assert '{"error": "Access denied for this resource"}' in str(exc_info.value)

    def test_request_raises_forbidden_on_401_with_response_text(self):
        from unittest.mock import patch
        from tap_kustomer.client import KustomerClient, KustomerForbiddenError

        with patch('requests.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session

            unauthorized_response = MagicMock()
            unauthorized_response.status_code = 401
            unauthorized_response.text = '{"error": "Invalid or expired token"}'
            unauthorized_response.headers = {}

            mock_session.request.return_value = unauthorized_response

            client = KustomerClient('fake_token', 'test-agent')
            client._KustomerClient__verified = True

            import pytest
            with pytest.raises(KustomerForbiddenError) as exc_info:
                client.request('GET', path='users')

            assert 'HTTP-error-code: 401' in str(exc_info.value)
            assert '{"error": "Invalid or expired token"}' in str(exc_info.value)
