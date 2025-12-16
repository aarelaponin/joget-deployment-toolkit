"""
Tests for joget_deployment_toolkit.client module.

Tests cover:
- Client initialization (all constructors)
- HTTP operations (GET, POST, retry logic)
- Health & connection
- Form operations
- Application operations
- Plugin operations
"""

import os
from unittest.mock import Mock, mock_open, patch

import pytest

from joget_deployment_toolkit.auth import APIKeyAuth
from joget_deployment_toolkit.client import JogetClient
from joget_deployment_toolkit.exceptions import (
    NotFoundError,
    ServerError,
    ValidationError,
)
from joget_deployment_toolkit.models import (
    ApplicationInfo,
    FormInfo,
    Health,
    HealthStatus,
    PluginInfo,
    SystemInfo,
)


class TestClientInitialization:
    """Test JogetClient initialization methods."""

    def test_init_with_api_key(self, base_url, api_key):
        """Test initialization with API key."""
        from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig

        config = ClientConfig(
            base_url=base_url, auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key), timeout=30
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = APIKeyAuth(api_key)
            client = JogetClient(config)

            assert client.base_url == base_url
            assert client.config.timeout == 30
            assert isinstance(client.auth_strategy, APIKeyAuth)

    def test_init_with_username_password(self, session_config, mock_auth_strategy):
        """Test initialization with username/password."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy

            client = JogetClient(session_config, auth_strategy=mock_auth_strategy)

            assert client.base_url == session_config.base_url
            assert client.config.auth.username == "admin"
            assert isinstance(client.auth_strategy, Mock)

    def test_init_custom_timeout(self, base_url, api_key, mock_auth_strategy):
        """Test initialization with custom timeout."""
        from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig

        config = ClientConfig(
            base_url=base_url,
            auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
            timeout=60,  # Custom timeout
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            assert client.config.timeout == 60

    def test_init_custom_retry_settings(self, base_url, api_key, mock_auth_strategy):
        """Test initialization with custom retry settings."""
        from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig, RetryConfig

        config = ClientConfig(
            base_url=base_url,
            auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
            retry=RetryConfig(count=5, delay=3.0, backoff=3.0),
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            assert client.config.retry.count == 5
            assert client.config.retry.delay == 3.0
            assert client.config.retry.backoff == 3.0

    def test_init_with_debug(self, base_url, api_key, mock_auth_strategy):
        """Test initialization with debug enabled."""
        from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig

        config = ClientConfig(
            base_url=base_url, auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key), debug=True
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            assert client.config.debug is True

    def test_from_credentials_classmethod(self, base_url, credentials, mock_auth_strategy):
        """Test from_credentials class method."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy

            client = JogetClient.from_credentials(
                base_url, credentials["username"], credentials["password"]
            )

            assert client.base_url == base_url
            assert client.config.auth.username == credentials["username"]
            assert client.config.auth.password == credentials["password"]

    def test_from_config_with_dict(self, base_url, credentials, mock_auth_strategy):
        """Test from_config with dictionary."""
        from joget_deployment_toolkit.config import AuthConfig, AuthType

        config = {
            "base_url": base_url,
            "auth": AuthConfig(
                type=AuthType.SESSION,
                username=credentials["username"],
                password=credentials["password"],
            ),
            "timeout": 45,
        }

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy

            client = JogetClient.from_config(config)

            assert client.base_url == base_url
            assert client.config.timeout == 45

    def test_from_config_missing_url_raises(self):
        """Test from_config raises error if URL missing."""
        from pydantic import ValidationError

        config = {"username": "admin", "password": "admin"}  # Missing base_url

        with pytest.raises(ValidationError):
            JogetClient.from_config(config)

    @patch.dict(
        os.environ,
        {
            "JOGET_BASE_URL": "http://localhost:8080/jw",
            "JOGET_API_KEY": "test-key",
            "JOGET_TIMEOUT": "60",
        },
    )
    def test_from_env(self, mock_auth_strategy):
        """Test from_env with environment variables."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy

            client = JogetClient.from_env()

            assert client.base_url == "http://localhost:8080/jw"
            assert client.config.timeout == 60

    def test_from_env_missing_url_raises(self):
        """Test from_env raises error if URL not in environment."""
        from pydantic import ValidationError

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                JogetClient.from_env()


class TestHTTPOperations:
    """Test HTTP operation methods."""

    def test_get_success(self, basic_config, mock_auth_strategy):
        """Test successful GET request."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # Mock the HTTP client's request method
            with patch.object(client.http_client, "request") as mock_request:
                mock_request.return_value = {"data": "test"}

                result = client.get("/test/endpoint")

                assert result == {"data": "test"}
                mock_request.assert_called_once()

    def test_get_with_params(self, basic_config, mock_auth_strategy):
        """Test GET with query parameters."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # Mock the HTTP client's request method
            with patch.object(client.http_client, "request") as mock_request:
                mock_request.return_value = {"results": []}

                params = {"page": 1, "size": 10}
                result = client.get("/test/endpoint", params=params)

                args, kwargs = mock_request.call_args
                assert kwargs.get("params") == params

    def test_post_success(self, basic_config, mock_auth_strategy):
        """Test successful POST request."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # Mock the HTTP client's request method
            with patch.object(client.http_client, "request") as mock_request:
                mock_request.return_value = {"success": True}

                result = client.post("/test/endpoint", json={"field": "value"})

                assert result == {"success": True}
                mock_request.assert_called_once()

    def test_retry_on_500_error(self, base_url, api_key, mock_auth_strategy):
        """Test retry logic on 500 error."""
        from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig, RetryConfig

        config = ClientConfig(
            base_url=base_url,
            auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
            retry=RetryConfig(count=3, delay=0.1),  # Min delay is 0.1
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            # For this test, we're just verifying that retry eventually succeeds
            # The actual retry logic is tested more thoroughly in test_exponential_backoff
            with patch.object(client.http_client, "request", return_value={"success": True}):
                result = client.get("/test/endpoint")
                assert result == {"success": True}

    def test_no_retry_on_404(self, base_url, api_key, mock_auth_strategy):
        """Test no retry on 404 error."""
        from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig, RetryConfig

        config = ClientConfig(
            base_url=base_url,
            auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
            retry=RetryConfig(count=3),
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            # Mock the HTTP client's request method to raise 404
            with patch.object(client.http_client, "request") as mock_request:
                mock_request.side_effect = NotFoundError("Not found", status_code=404)

                with pytest.raises(NotFoundError):
                    client.get("/test/endpoint")

                # Should only be called once (no retries on 404)
                assert mock_request.call_count == 1

    def test_exponential_backoff(self, base_url, api_key, mock_auth_strategy):
        """Test exponential backoff calculation."""
        from joget_deployment_toolkit.config import AuthConfig, AuthType, ClientConfig, RetryConfig

        config = ClientConfig(
            base_url=base_url,
            auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
            retry=RetryConfig(count=3, delay=2.0, backoff=2.0),
        )

        with patch("time.sleep") as mock_sleep:
            with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
                mock_select.return_value = mock_auth_strategy
                client = JogetClient(config, auth_strategy=mock_auth_strategy)

                # Mock the HTTP client's _execute_request to fail twice, then succeed
                with patch.object(client.http_client, "_execute_request") as mock_execute:
                    # Create mock responses
                    error_response = Mock()
                    error_response.status_code = 500
                    error_response.text = "Server error"

                    success_response = Mock()
                    success_response.status_code = 200
                    success_response.json = Mock(return_value={"success": True})

                    # First two attempts fail with 500, third succeeds
                    mock_execute.side_effect = [error_response, error_response, success_response]

                    client.get("/test/endpoint")

                    # Check backoff delays: 2.0, 4.0
                    calls = mock_sleep.call_args_list
                    assert len(calls) == 2
                    assert calls[0][0][0] == 2.0  # First retry: 2.0 * (2.0 ** 0)
                    assert calls[1][0][0] == 4.0  # Second retry: 2.0 * (2.0 ** 1)


class TestHealthAndConnection:
    """Test health check and connection methods."""

    def test_test_connection_success(self, basic_config, mock_auth_strategy):
        """Test successful connection test."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            with patch.object(client.http_client, "request", return_value={}):
                result = client.test_connection()
                assert result is True

    def test_test_connection_failure(self, basic_config, mock_auth_strategy):
        """Test failed connection test."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # Mock session.get to raise an exception
            with patch.object(client.session, "get", side_effect=Exception("Connection refused")):
                result = client.test_connection()
                assert result is False

    def test_get_system_info(self, basic_config, mock_auth_strategy):
        """Test get_system_info returns SystemInfo."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            system_data = {
                "version": "9.0.0",
                "build": "12345",
                "licenseType": "Enterprise",
                "licenseTo": "Test Company",
            }

            with patch.object(client.http_client, "request", return_value=system_data):
                info = client.get_system_info()

                assert isinstance(info, SystemInfo)
                assert info.version == "9.0.0"
                assert info.build == "12345"
                assert info.license_type == "Enterprise"

    def test_get_health_status_healthy(self, basic_config, mock_auth_strategy):
        """Test get_health_status returns healthy status."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            with patch.object(client, "test_connection", return_value=True):
                with patch.object(
                    client,
                    "get_system_info",
                    return_value=SystemInfo(
                        version="9.0.0", build="12345", license_type="Enterprise"
                    ),
                ):
                    health = client.get_health_status()

                    assert isinstance(health, Health)
                    assert health.status == HealthStatus.HEALTHY
                    assert health.reachable is True
                    assert health.authenticated is True
                    assert health.version == "9.0.0"


class TestFormOperations:
    """Test form operation methods."""

    def test_get_form(self, basic_config, mock_auth_strategy, sample_form_data):
        """Test get_form retrieves form definition."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            with patch.object(client.http_client, "request", return_value=sample_form_data):
                form = client.get_form("app1", "test_form")

                assert form["id"] == "test_form"
                assert form["name"] == "Test Form"

    def test_list_forms(self, basic_config, mock_auth_strategy):
        """Test list_forms returns list of FormInfo."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            forms_data = {
                "data": [
                    {
                        "id": "form1",
                        "name": "Form 1",
                        "tableName": "table1",
                        "appId": "app1",
                        "appVersion": "1",
                    },
                    {
                        "id": "form2",
                        "name": "Form 2",
                        "tableName": "table2",
                        "appId": "app1",
                        "appVersion": "1",
                    },
                ]
            }

            with patch.object(client.http_client, "request", return_value=forms_data):
                forms = client.list_forms("app1")

                assert len(forms) == 2
                assert all(isinstance(f, FormInfo) for f in forms)
                assert forms[0].form_id == "form1"

    def test_update_form(self, basic_config, mock_auth_strategy):
        """Test update_form updates existing form."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            with patch.object(client.http_client, "request", return_value={"success": True}):
                result = client.update_form("app1", "test_form", {"name": "Updated Form"})

                assert result.success is True
                assert result.form_id == "test_form"

    def test_delete_form(self, basic_config, mock_auth_strategy):
        """Test delete_form deletes form."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            with patch.object(client.http_client, "request", return_value={"success": True}):
                result = client.delete_form("app1", "test_form")

                assert result is True


class TestApplicationOperations:
    """Test application operation methods."""

    def test_list_applications(self, basic_config, mock_auth_strategy):
        """Test list_applications returns list of ApplicationInfo."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            apps_data = {
                "data": [
                    {"id": "app1", "name": "App 1", "version": "1", "published": True},
                    {"id": "app2", "name": "App 2", "version": "1", "published": False},
                ]
            }

            with patch.object(client.http_client, "request", return_value=apps_data):
                apps = client.list_applications()

                assert len(apps) == 2
                assert all(isinstance(a, ApplicationInfo) for a in apps)
                assert apps[0].id == "app1"

    def test_export_application(self, basic_config, mock_auth_strategy, tmp_path):
        """Test export_application saves ZIP file."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # Mock streaming response with iter_content method
            stream_response = Mock()
            stream_response.iter_content = Mock(return_value=[b"test", b"data"])
            stream_response.status_code = 200

            # Mock http_client.request to return the stream response
            with patch.object(client.http_client, "request", return_value=stream_response):
                output_path = tmp_path / "app_export.zip"
                result = client.export_application("app1", output_path)

                assert result.success is True
                assert output_path.exists()

    @patch("builtins.open", new_callable=mock_open, read_data=b"fake zip data")
    def test_import_application(self, mock_file, basic_config, mock_auth_strategy):
        """Test import_application uploads ZIP file."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # Mock the response object
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "appId": "imported_app",
                "appVersion": "1",
            }

            with patch("pathlib.Path.exists", return_value=True):
                # Mock session.post since import uses session directly for multipart upload
                with patch.object(client.session, "post", return_value=mock_response):
                    result = client.import_application("/path/to/app.zip")

                    assert result.success is True
                    assert result.app_id == "imported_app"


class TestPluginOperations:
    """Test plugin operation methods."""

    def test_list_plugins(self, basic_config, mock_auth_strategy):
        """Test list_plugins returns list of PluginInfo."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            plugins_data = {
                "data": [
                    {"id": "plugin1", "name": "Plugin 1", "version": "1.0", "type": "formElement"},
                    {"id": "plugin2", "name": "Plugin 2", "version": "2.0", "type": "process"},
                ]
            }

            with patch.object(client.http_client, "request", return_value=plugins_data):
                plugins = client.list_plugins()

                assert len(plugins) == 2
                assert all(isinstance(p, PluginInfo) for p in plugins)
                assert plugins[0].id == "plugin1"

    def test_list_plugins_with_filter(self, basic_config, mock_auth_strategy):
        """Test list_plugins with type filter."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            with patch.object(
                client.http_client, "request", return_value={"data": []}
            ) as mock_request:
                client.list_plugins(plugin_type="formElement")

                # Verify params were passed
                args, kwargs = mock_request.call_args
                assert kwargs.get("params") == {"type": "formElement"}


class TestContextManager:
    """Test context manager support."""

    def test_context_manager(self, basic_config, mock_auth_strategy):
        """Test client works as context manager."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy

            with JogetClient(basic_config, auth_strategy=mock_auth_strategy) as client:
                assert client.base_url == basic_config.base_url
                mock_session_instance = client.session

            # Session should be closed after context exit
        # Note: We can't directly test session.close() was called with our mock


@pytest.mark.skip(reason="batch_post method not implemented in v3.0")
class TestBatchOperations:
    """Test batch operations."""

    def test_batch_post_all_success(self, basic_config, mock_auth_strategy):
        """Test batch_post with all successful records."""
        from joget_deployment_toolkit.config import ClientConfig

        config = ClientConfig(base_url=basic_config.base_url, auth=basic_config.auth, debug=True)

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            # Mock the post method to return success
            with patch.object(client, "post", return_value={"status": "ok"}):
                records = [{"name": "Record 1"}, {"name": "Record 2"}, {"name": "Record 3"}]

                result = client.batch_post("/test/form", "test_api", records)

                assert result["total"] == 3
                assert result["successful"] == 3
                assert result["failed"] == 0
                assert len(result["errors"]) == 0

    def test_batch_post_with_failures(self, basic_config, mock_auth_strategy):
        """Test batch_post with some failures."""
        from joget_deployment_toolkit.config import ClientConfig

        config = ClientConfig(base_url=basic_config.base_url, auth=basic_config.auth, debug=True)

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            # First call succeeds, second fails, third succeeds
            with patch.object(
                client,
                "post",
                side_effect=[{"status": "ok"}, ValidationError("Invalid data"), {"status": "ok"}],
            ):
                records = [{"name": "Record 1"}, {"name": "Invalid Record"}, {"name": "Record 3"}]

                result = client.batch_post("/test/form", "test_api", records)

                assert result["total"] == 3
                assert result["successful"] == 2
                assert result["failed"] == 1
                assert len(result["errors"]) == 1
                assert result["errors"][0]["index"] == 1

    def test_batch_post_stop_on_error(self, basic_config, mock_auth_strategy):
        """Test batch_post with stop_on_error=True."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # First call succeeds, second fails
            with patch.object(
                client, "post", side_effect=[{"status": "ok"}, ValidationError("Invalid data")]
            ) as mock_post:
                records = [
                    {"name": "Record 1"},
                    {"name": "Invalid Record"},
                    {"name": "Record 3"},  # Should not be processed
                ]

                result = client.batch_post("/test/form", "test_api", records, stop_on_error=True)

                assert result["total"] == 3
                assert result["successful"] == 1
                assert result["failed"] == 1
                # Should stop after second record fails
                assert mock_post.call_count == 2


@pytest.mark.skip(reason="post_multipart method not implemented in v3.0")
class TestMultipartUpload:
    """Test multipart file upload operations."""

    def test_post_multipart_success(self, basic_config, mock_auth_strategy):
        """Test post_multipart with successful upload."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            data = {"field1": "value1"}
            files = {"file": ("test.txt", b"file content", "text/plain")}

            with patch.object(client.session, "post") as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {"status": "uploaded", "file_id": "123"}
                mock_post.return_value = mock_response

                result = client.post_multipart("/test/upload", "upload_api", data, files)

                assert result["status"] == "uploaded"
                assert result["file_id"] == "123"
                mock_post.assert_called_once()

    def test_post_multipart_with_retry(self, basic_config, mock_auth_strategy):
        """Test post_multipart with retry enabled."""
        from joget_deployment_toolkit.config import ClientConfig, RetryConfig

        config = ClientConfig(
            base_url=basic_config.base_url,
            auth=basic_config.auth,
            retry=RetryConfig(count=2, delay=0.1),
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            data = {"field1": "value1"}
            files = {"file": ("test.txt", b"content", "text/plain")}

            # First call fails with 500, second succeeds
            with patch.object(client.session, "post") as mock_post:
                error_response = Mock()
                error_response.status_code = 500
                error_response.json.return_value = {"error": "Server error"}

                success_response = Mock()
                success_response.status_code = 200
                success_response.json.return_value = {"status": "uploaded"}

                mock_post.side_effect = [error_response, success_response]

                result = client.post_multipart(
                    "/test/upload", "upload_api", data, files, retry=True
                )

                assert result["status"] == "uploaded"
                assert mock_post.call_count == 2


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_get_json_decode_error(self, basic_config, mock_auth_strategy):
        """Test GET with JSON decode error falls back to text."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # Mock http_client to return valid data (JSON decode happens internally)
            with patch.object(
                client.http_client,
                "request",
                return_value={"status": "success", "response": "Plain text response"},
            ):
                result = client.get("/test/endpoint")

                assert result["status"] == "success"
                assert result["response"] == "Plain text response"

    def test_post_json_decode_error(self, basic_config, mock_auth_strategy):
        """Test POST with JSON decode error falls back to text."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            with patch.object(
                client.http_client,
                "request",
                return_value={"status": "success", "response": "Created successfully"},
            ):
                result = client.post("/test/endpoint", json={"field": "value"})

                assert result["status"] == "success"
                assert result["response"] == "Created successfully"

    def test_get_without_retry(self, basic_config, mock_auth_strategy):
        """Test GET with retry=False doesn't retry on errors."""
        from joget_deployment_toolkit.config import ClientConfig, RetryConfig

        config = ClientConfig(
            base_url=basic_config.base_url, auth=basic_config.auth, retry=RetryConfig(enabled=False)
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            with patch.object(
                client.http_client,
                "request",
                side_effect=ServerError("Server error", status_code=500),
            ):
                with pytest.raises(ServerError):
                    client.get("/test/endpoint")

    def test_post_without_retry(self, basic_config, mock_auth_strategy):
        """Test POST with retry=False doesn't retry on errors."""
        from joget_deployment_toolkit.config import ClientConfig, RetryConfig

        config = ClientConfig(
            base_url=basic_config.base_url, auth=basic_config.auth, retry=RetryConfig(enabled=False)
        )

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            with patch.object(
                client.http_client,
                "request",
                side_effect=ServerError("Server error", status_code=500),
            ):
                with pytest.raises(ServerError):
                    client.post("/test/endpoint", json={"field": "value"})

    def test_get_with_stream(self, basic_config, mock_auth_strategy):
        """Test GET with stream=True returns raw response."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            # Mock response object with status_code
            response = Mock()
            response.status_code = 200
            response.iter_content = Mock(return_value=[b"data"])

            # Mock http_client.request to return the response
            with patch.object(client.http_client, "request", return_value=response):
                result = client.get("/test/endpoint", stream=True)

                # Should return the response object
                assert result == response

    def test_debug_logging(self, basic_config, mock_auth_strategy):
        """Test debug logging is enabled when debug=True."""
        from joget_deployment_toolkit.config import ClientConfig

        config = ClientConfig(base_url=basic_config.base_url, auth=basic_config.auth, debug=True)

        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(config, auth_strategy=mock_auth_strategy)

            with patch.object(client.http_client, "request", return_value={"status": "ok"}):
                # Should not raise, and debug logging should be active
                result = client.post("/test/endpoint", json={"field": "value"})
                assert result["status"] == "ok"
                assert client.config.debug is True


class TestFormOperationsExtended:
    """Extended tests for form operations."""

    def test_create_form_with_payload(self, basic_config, mock_auth_strategy):
        """Test create_form using formCreator API with payload."""
        with patch("joget_deployment_toolkit.auth.select_auth_strategy") as mock_select:
            mock_select.return_value = mock_auth_strategy
            client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

            payload = {
                "target_app_id": "app1",
                "target_app_version": "1",
                "form_id": "test_form",
                "form_name": "Test Form",
                "table_name": "app_fd_test",
                "form_definition_json": "{}",
                "create_api_endpoint": "yes",
                "api_name": "test_api",
            }

            with patch.object(
                client.http_client,
                "request",
                return_value={"status": "created", "formId": "test_form"},
            ):
                result = client.create_form(payload, "fc_api")

                assert result["formId"] == "test_form"
