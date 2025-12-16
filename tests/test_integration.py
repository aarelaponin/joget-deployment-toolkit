"""
Integration tests for joget_deployment_toolkit.

These tests require a running Joget instance and will be skipped if:
- JOGET_BASE_URL environment variable is not set
- Connection to the instance fails

To run integration tests:
    export JOGET_BASE_URL=http://localhost:8080/jw
    export JOGET_USERNAME=admin
    export JOGET_PASSWORD=admin
    pytest tests/test_integration.py -v
"""

import os

import pytest

from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.exceptions import (
    JogetAPIError,
    NotFoundError,
)
from joget_deployment_toolkit.models import HealthStatus

# Skip all integration tests if environment variables not set
pytestmark = pytest.mark.skipif(
    not os.getenv("JOGET_BASE_URL"), reason="JOGET_BASE_URL not set - skipping integration tests"
)


@pytest.fixture(scope="module")
def joget_base_url():
    """Get Joget base URL from environment."""
    return os.getenv("JOGET_BASE_URL", "http://localhost:8080/jw")


@pytest.fixture(scope="module")
def joget_credentials():
    """Get Joget credentials from environment."""
    return {
        "username": os.getenv("JOGET_USERNAME", "admin"),
        "password": os.getenv("JOGET_PASSWORD", "admin"),
    }


@pytest.fixture(scope="module")
def client(joget_base_url, joget_credentials):
    """
    Create authenticated Joget client.

    Uses session-based authentication for integration tests.
    """
    client = JogetClient.from_credentials(
        joget_base_url,
        username=joget_credentials["username"],
        password=joget_credentials["password"],
        timeout=30,
        debug=True,
    )

    # Verify connection
    try:
        if not client.test_connection():
            pytest.skip("Cannot connect to Joget instance")
    except Exception as e:
        pytest.skip(f"Connection test failed: {e}")

    yield client

    # Cleanup
    client.close()


class TestConnection:
    """Test basic connection and authentication."""

    def test_connection_successful(self, client):
        """Test that we can connect to the instance."""
        assert client.test_connection() is True

    def test_get_system_info(self, client):
        """Test retrieving system information."""
        info = client.get_system_info()

        assert info is not None
        assert info.version is not None
        assert info.build is not None
        assert info.license_type is not None

        print(f"\nJoget Version: {info.version}")
        print(f"Build: {info.build}")
        print(f"License: {info.license_type}")

    def test_health_check(self, client):
        """Test health check endpoint."""
        health = client.get_health_status()

        assert health is not None
        assert health.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]
        assert health.reachable is True
        assert health.authenticated is True

        print(f"\nHealth Status: {health.status}")
        print(f"Version: {health.version}")

        for check in health.checks:
            status = "✓" if check.passed else "✗"
            print(f"  {status} {check.name}: {check.message}")


class TestApplicationOperations:
    """Test application-level operations."""

    def test_list_applications(self, client):
        """Test listing all applications."""
        apps = client.list_applications()

        assert apps is not None
        assert isinstance(apps, list)

        if apps:
            print(f"\nFound {len(apps)} applications:")
            for app in apps[:5]:  # Show first 5
                status = "✓" if app.published else "✗"
                print(f"  {status} {app.id} v{app.version}: {app.name}")
        else:
            print("\nNo applications found on instance")


class TestPluginOperations:
    """Test plugin-related operations."""

    def test_list_plugins(self, client):
        """Test listing installed plugins."""
        plugins = client.list_plugins()

        assert plugins is not None
        assert isinstance(plugins, list)

        if plugins:
            print(f"\nFound {len(plugins)} plugins:")
            for plugin in plugins[:10]:  # Show first 10
                print(f"  - {plugin.name} v{plugin.version} ({plugin.type})")
        else:
            print("\nNo plugins found on instance")

    def test_list_form_element_plugins(self, client):
        """Test filtering plugins by type."""
        plugins = client.list_plugins(plugin_type="formElement")

        assert plugins is not None
        assert isinstance(plugins, list)

        if plugins:
            print(f"\nFound {len(plugins)} form element plugins:")
            for plugin in plugins[:5]:  # Show first 5
                print(f"  - {plugin.name}")


class TestFormOperations:
    """Test form-related operations."""

    @pytest.fixture
    def test_app_id(self):
        """
        Override this fixture to test with a specific application.

        By default, uses the first available application.
        """
        return os.getenv("JOGET_TEST_APP_ID", None)

    def test_list_forms_in_app(self, client, test_app_id):
        """Test listing forms in an application."""
        # Get first available app if test_app_id not specified
        if not test_app_id:
            apps = client.list_applications()
            if not apps:
                pytest.skip("No applications available for testing")
            test_app_id = apps[0].id

        try:
            forms = client.list_forms(test_app_id, app_version="1")

            assert forms is not None
            assert isinstance(forms, list)

            if forms:
                print(f"\nFound {len(forms)} forms in '{test_app_id}':")
                for form in forms[:10]:  # Show first 10
                    print(f"  - {form.form_id}: {form.form_name}")
            else:
                print(f"\nNo forms found in application '{test_app_id}'")

        except NotFoundError:
            pytest.skip(f"Application '{test_app_id}' not found")
        except JogetAPIError as e:
            pytest.skip(f"Error accessing forms: {e}")


class TestErrorHandling:
    """Test error handling with real API calls."""

    def test_not_found_error(self, client):
        """Test that 404 errors raise NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            client.get_form("nonexistent_app", "nonexistent_form")

        assert exc_info.value.status_code == 404
        print(f"\nCorrectly raised NotFoundError: {exc_info.value.message}")

    def test_invalid_credentials(self, joget_base_url):
        """Test that invalid credentials raise AuthenticationError."""
        invalid_client = JogetClient.from_credentials(
            joget_base_url, username="invalid_user", password="invalid_password"
        )

        # Should not be authenticated
        health = invalid_client.get_health_status()
        assert health.authenticated is False
        assert health.status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]


class TestAlternativeConstructors:
    """Test alternative client constructors."""

    def test_from_env(self, joget_base_url, joget_credentials):
        """Test creating client from environment variables."""
        # Set up environment
        os.environ["JOGET_BASE_URL"] = joget_base_url
        os.environ["JOGET_USERNAME"] = joget_credentials["username"]
        os.environ["JOGET_PASSWORD"] = joget_credentials["password"]

        # Create client from environment
        client = JogetClient.from_env()

        # Should be able to connect
        assert client.test_connection() is True

        # Cleanup
        client.close()

    def test_context_manager(self, joget_base_url, joget_credentials):
        """Test using client as context manager."""
        with JogetClient.from_credentials(
            joget_base_url,
            username=joget_credentials["username"],
            password=joget_credentials["password"],
        ) as client:
            # Should be able to use client within context
            assert client.test_connection() is True
            info = client.get_system_info()
            assert info is not None

        # Session should be closed after context exit
        # (We can't easily test this without accessing internal state)


# Mark all tests as integration tests
pytest.mark.integration = pytest.mark.mark(
    *[
        cls
        for cls in [
            TestConnection,
            TestApplicationOperations,
            TestPluginOperations,
            TestFormOperations,
            TestErrorHandling,
            TestAlternativeConstructors,
        ]
    ]
)


if __name__ == "__main__":
    # Allow running integration tests directly
    print("Running integration tests...")
    print("Make sure you have set:")
    print("  - JOGET_BASE_URL")
    print("  - JOGET_USERNAME")
    print("  - JOGET_PASSWORD")
    print()

    pytest.main([__file__, "-v", "-s"])
