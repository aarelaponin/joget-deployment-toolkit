"""
Tests for refactored client modules.
"""

from unittest.mock import patch

from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.config import ClientConfig


class TestRefactoredClient:
    """Test the refactored modular client."""

    def test_backward_compatibility(self):
        """Test that old initialization still works."""
        with patch("joget_deployment_toolkit.client.base.BaseClient._create_session"):
            client = JogetClient("http://localhost:8080/jw", api_key="test-key")

            # All methods should still be available
            assert hasattr(client, "list_forms")
            assert hasattr(client, "list_applications")
            assert hasattr(client, "test_connection")

    def test_new_initialization(self):
        """Test new initialization with config."""
        config = ClientConfig(
            base_url="http://localhost:8080/jw", auth={"type": "api_key", "api_key": "test-key"}
        )

        with patch("joget_deployment_toolkit.client.base.BaseClient._create_session"):
            client = JogetClient.from_config(config)

            assert client.config.base_url == "http://localhost:8080/jw"

    def test_mixins_integration(self):
        """Test that all mixins are properly integrated."""
        with patch("joget_deployment_toolkit.client.base.BaseClient._create_session"):
            client = JogetClient("http://localhost:8080/jw", api_key="test-key")

            # Check methods from each mixin
            # FormOperations
            assert callable(getattr(client, "list_forms", None))
            assert callable(getattr(client, "get_form", None))

            # ApplicationOperations
            assert callable(getattr(client, "list_applications", None))
            assert callable(getattr(client, "export_application", None))

            # HealthOperations
            assert callable(getattr(client, "test_connection", None))
            assert callable(getattr(client, "get_health_status", None))
