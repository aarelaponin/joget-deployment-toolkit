"""
Pytest configuration and shared fixtures.
"""

from unittest.mock import Mock

import pytest
import requests


@pytest.fixture
def mock_response():
    """Create a mock response object."""

    def _make_response(status_code=200, json_data=None, text="", headers=None):
        response = Mock(spec=requests.Response)
        response.status_code = status_code
        response.text = text
        response.headers = headers or {}

        if json_data is not None:
            response.json = Mock(return_value=json_data)
        else:
            response.json = Mock(side_effect=ValueError("No JSON"))

        # Add iter_content for streaming
        response.iter_content = Mock(return_value=[b"test data"])

        return response

    return _make_response


@pytest.fixture
def mock_session(mock_response):
    """Create a mock requests.Session."""
    session = Mock(spec=requests.Session)
    session.verify = True

    # Default successful response
    session.get = Mock(return_value=mock_response(200, {"success": True}))
    session.post = Mock(return_value=mock_response(200, {"success": True}))

    return session


@pytest.fixture
def base_url():
    """Standard base URL for tests."""
    return "http://localhost:8080/jw"


@pytest.fixture
def api_key():
    """Standard API key for tests."""
    return "test-api-key-12345"


@pytest.fixture
def credentials():
    """Standard credentials for tests."""
    return {"username": "admin", "password": "admin"}


@pytest.fixture
def sample_form_data():
    """Sample form definition."""
    return {
        "id": "test_form",
        "name": "Test Form",
        "tableName": "app_fd_test_form",
        "description": "A test form",
        "json": {
            "className": "org.joget.apps.form.model.Form",
            "properties": {"id": "test_form", "name": "Test Form"},
        },
    }


@pytest.fixture
def sample_app_data():
    """Sample application data."""
    return {
        "id": "test_app",
        "name": "Test Application",
        "version": "1",
        "published": True,
        "description": "Test application",
    }


@pytest.fixture
def sample_plugin_data():
    """Sample plugin data."""
    return {
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "type": "formElement",
        "description": "A test plugin",
        "className": "com.test.TestPlugin",
    }


# ============================================================================
# New v3.0 Configuration Fixtures
# ============================================================================


@pytest.fixture
def basic_config(base_url, api_key):
    """
    Create a basic ClientConfig with API key auth.

    Most tests can use this directly.
    """
    from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig

    return ClientConfig(
        base_url=base_url,
        auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
        timeout=30,
        debug=False,
    )


@pytest.fixture
def session_config(base_url, credentials):
    """Create a ClientConfig with session auth."""
    from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig

    return ClientConfig(
        base_url=base_url,
        auth=AuthConfig(
            type=AuthType.SESSION,
            username=credentials["username"],
            password=credentials["password"],
        ),
        timeout=30,
    )


@pytest.fixture
def custom_config(base_url, api_key):
    """
    Create a ClientConfig factory for custom configurations.

    Usage:
        config = custom_config(timeout=60, debug=True)
    """
    from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig

    def _create_config(**overrides):
        base = {
            "base_url": base_url,
            "auth": AuthConfig(type=AuthType.API_KEY, api_key=api_key),
            "timeout": 30,
            "debug": False,
        }
        base.update(overrides)
        return ClientConfig(**base)

    return _create_config


@pytest.fixture
def mock_auth_strategy():
    """Create a mocked authentication strategy."""
    from joget_deployment_toolkit.auth import APIKeyAuth

    mock_auth = Mock(spec=APIKeyAuth)
    mock_auth.authenticate = Mock(return_value=True)
    mock_auth.get_headers = Mock(return_value={"Authorization": "Bearer test"})
    mock_auth.is_authenticated = Mock(return_value=True)
    return mock_auth


@pytest.fixture
def mock_client(basic_config, mock_auth_strategy):
    """
    Create a fully mocked JogetClient.

    This is the most commonly used fixture. It provides a client
    with mocked HTTP operations ready for testing.

    Usage:
        def test_something(mock_client):
            with patch.object(mock_client, 'get') as mock_get:
                mock_get.return_value = Mock(status_code=200, json=...)
                result = mock_client.list_forms("app")
    """
    from joget_deployment_toolkit.client import JogetClient

    with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
        mock_select.return_value = mock_auth_strategy

        client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

        # Mock the session to avoid actual HTTP calls
        client.session = Mock()

        return client
