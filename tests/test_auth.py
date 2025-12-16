"""
Tests for joget_deployment_toolkit.auth module.
"""

import base64
from unittest.mock import Mock

import pytest

from joget_deployment_toolkit.auth import (
    APIKeyAuth,
    BasicAuth,
    NoAuth,
    SessionAuth,
    select_auth_strategy,
)


class TestAPIKeyAuth:
    """Test APIKeyAuth strategy."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        auth = APIKeyAuth("test-key-123")
        assert auth.api_key == "test-key-123"
        assert auth.default_api_id is None

    def test_init_with_api_key_and_api_id(self):
        """Test initialization with API key and default API ID."""
        auth = APIKeyAuth("test-key", default_api_id="fc_api")
        assert auth.api_key == "test-key"
        assert auth.default_api_id == "fc_api"

    def test_authenticate_returns_true(self, mock_session):
        """Test authenticate always returns True (no upfront auth needed)."""
        auth = APIKeyAuth("test-key")
        result = auth.authenticate(mock_session)
        assert result is True

    def test_get_headers_with_api_key(self):
        """Test get_headers returns API key header."""
        auth = APIKeyAuth("test-key-123")
        headers = auth.get_headers()

        assert "api_key" in headers
        assert headers["api_key"] == "test-key-123"
        assert headers["Content-Type"] == "application/json"

    def test_get_headers_with_api_id(self):
        """Test get_headers with API ID."""
        auth = APIKeyAuth("test-key", default_api_id="fc_api")
        headers = auth.get_headers()

        assert headers["api_id"] == "fc_api"
        assert headers["api_key"] == "test-key"

    def test_get_headers_override_api_id(self):
        """Test get_headers with overridden API ID."""
        auth = APIKeyAuth("test-key", default_api_id="default_api")
        headers = auth.get_headers(api_id="custom_api")

        assert headers["api_id"] == "custom_api"
        assert headers["api_key"] == "test-key"


class TestSessionAuth:
    """Test SessionAuth strategy."""

    def test_init(self, base_url, credentials):
        """Test initialization."""
        auth = SessionAuth(base_url, credentials["username"], credentials["password"])
        assert auth.base_url == base_url
        assert auth.username == credentials["username"]
        assert auth.password == credentials["password"]
        assert auth._authenticated is False

    def test_authenticate_success(self, base_url, credentials, mock_session, mock_response):
        """Test successful authentication."""
        # Mock successful login (redirect away from login page)
        success_response = mock_response(200)
        success_response.url = "http://localhost:8080/jw/home"
        mock_session.post = Mock(return_value=success_response)

        auth = SessionAuth(base_url, credentials["username"], credentials["password"])
        result = auth.authenticate(mock_session)

        assert result is True
        assert auth._authenticated is True
        mock_session.post.assert_called_once()

    def test_authenticate_failure(self, base_url, credentials, mock_session, mock_response):
        """Test failed authentication (stays on login page)."""
        # Mock failed login (URL still contains 'login')
        fail_response = mock_response(200)
        fail_response.url = "http://localhost:8080/jw/login?error"
        mock_session.post = Mock(return_value=fail_response)

        auth = SessionAuth(base_url, credentials["username"], credentials["password"])
        result = auth.authenticate(mock_session)

        assert result is False
        assert auth._authenticated is False

    def test_get_headers(self, base_url, credentials):
        """Test get_headers returns standard headers (no auth headers for session)."""
        auth = SessionAuth(base_url, credentials["username"], credentials["password"])
        headers = auth.get_headers()

        assert "Content-Type" in headers
        # Session auth uses cookies, so no Authorization header
        assert "Authorization" not in headers
        assert "api_key" not in headers

    def test_is_authenticated_after_success(
        self, base_url, credentials, mock_session, mock_response
    ):
        """Test is_authenticated returns True after successful auth."""
        success_response = mock_response(200)
        success_response.url = "http://localhost:8080/jw/home"
        mock_session.post = Mock(return_value=success_response)

        auth = SessionAuth(base_url, credentials["username"], credentials["password"])
        auth.authenticate(mock_session)

        assert auth.is_authenticated() is True


class TestBasicAuth:
    """Test BasicAuth strategy."""

    def test_init(self, credentials):
        """Test initialization."""
        auth = BasicAuth(credentials["username"], credentials["password"])
        assert auth.username == credentials["username"]
        assert auth.password == credentials["password"]
        assert auth._auth_header is not None

    def test_generate_auth_header(self, credentials):
        """Test auth header generation."""
        auth = BasicAuth(credentials["username"], credentials["password"])

        # Decode and verify
        expected_creds = f"{credentials['username']}:{credentials['password']}"
        expected_encoded = base64.b64encode(expected_creds.encode()).decode()
        expected_header = f"Basic {expected_encoded}"

        assert auth._auth_header == expected_header

    def test_authenticate_returns_true(self, credentials, mock_session):
        """Test authenticate returns True (no upfront auth needed)."""
        auth = BasicAuth(credentials["username"], credentials["password"])
        result = auth.authenticate(mock_session)
        assert result is True

    def test_get_headers(self, credentials):
        """Test get_headers includes Authorization header."""
        auth = BasicAuth(credentials["username"], credentials["password"])
        headers = auth.get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert "Content-Type" in headers

    def test_authorization_header_format(self, credentials):
        """Test Authorization header has correct format."""
        auth = BasicAuth(credentials["username"], credentials["password"])
        headers = auth.get_headers()

        auth_header = headers["Authorization"]
        assert auth_header.startswith("Basic ")

        # Decode and verify
        encoded = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        assert decoded == f"{credentials['username']}:{credentials['password']}"


class TestNoAuth:
    """Test NoAuth strategy."""

    def test_authenticate_returns_true(self, mock_session):
        """Test authenticate returns True."""
        auth = NoAuth()
        result = auth.authenticate(mock_session)
        assert result is True

    def test_get_headers(self):
        """Test get_headers returns standard headers."""
        auth = NoAuth()
        headers = auth.get_headers()

        assert "Content-Type" in headers
        assert "Authorization" not in headers
        assert "api_key" not in headers


class TestSelectAuthStrategy:
    """Test select_auth_strategy auto-selection."""

    def test_select_explicit_strategy(self):
        """Test using explicit auth_strategy takes precedence."""
        explicit = APIKeyAuth("test-key")
        result = select_auth_strategy(api_key="other-key", auth_strategy=explicit)

        assert result is explicit

    def test_select_api_key_auth(self):
        """Test auto-select APIKeyAuth when api_key provided."""
        result = select_auth_strategy(api_key="test-key-123")

        assert isinstance(result, APIKeyAuth)
        assert result.api_key == "test-key-123"

    def test_select_session_auth_with_base_url(self, base_url, credentials):
        """Test auto-select SessionAuth when username+password+base_url."""
        result = select_auth_strategy(
            username=credentials["username"], password=credentials["password"], base_url=base_url
        )

        assert isinstance(result, SessionAuth)
        assert result.username == credentials["username"]
        assert result.password == credentials["password"]

    def test_select_basic_auth_without_base_url(self, credentials):
        """Test auto-select BasicAuth when username+password without base_url."""
        result = select_auth_strategy(
            username=credentials["username"], password=credentials["password"]
        )

        assert isinstance(result, BasicAuth)
        assert result.username == credentials["username"]
        assert result.password == credentials["password"]

    def test_error_without_credentials(self):
        """Test raises ValueError when no credentials provided."""
        with pytest.raises(ValueError, match="authentication credentials"):
            select_auth_strategy()

    def test_priority_api_key_over_credentials(self, base_url, credentials):
        """Test API key takes priority over username/password."""
        result = select_auth_strategy(
            api_key="test-key",
            username=credentials["username"],
            password=credentials["password"],
            base_url=base_url,
        )

        # API key should be selected
        assert isinstance(result, APIKeyAuth)
        assert result.api_key == "test-key"
