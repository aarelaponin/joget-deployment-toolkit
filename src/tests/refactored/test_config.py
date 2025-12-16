"""
Tests for configuration management.
"""

from joget_deployment_toolkit.config import ClientConfig, ConfigurationLoader


class TestClientConfig:
    """Test ClientConfig model."""

    def test_minimal_config(self):
        """Test minimal configuration."""
        config = ClientConfig(
            base_url="http://localhost:8080/jw", auth={"type": "api_key", "api_key": "test-key"}
        )
        assert config.base_url == "http://localhost:8080/jw"
        assert config.auth.api_key == "test-key"

    def test_backward_compatibility(self):
        """Test backward compatibility methods."""
        config = ClientConfig.from_kwargs(
            base_url="http://localhost:8080/jw", api_key="test-key", timeout=60
        )
        assert config.timeout == 60

        kwargs = config.to_kwargs()
        assert kwargs["api_key"] == "test-key"
        assert kwargs["timeout"] == 60


class TestConfigurationLoader:
    """Test configuration loader."""

    def test_load_from_env(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("JOGET_BASE_URL", "http://test.com/jw")
        monkeypatch.setenv("JOGET_API_KEY", "env-key")

        loader = ConfigurationLoader()
        # Would load from env
