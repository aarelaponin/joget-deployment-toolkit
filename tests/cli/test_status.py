"""
Tests for the status command.
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from joget_deployment_toolkit.cli.main import app
from joget_deployment_toolkit.models import InstanceInfo

runner = CliRunner()

# Patch path for list_instances (imported inside status function)
LIST_INSTANCES_PATH = "joget_deployment_toolkit.inventory.list_instances"


class TestStatusCommand:
    """Tests for joget-deploy status command."""

    def test_status_help(self):
        """Test that --help works."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "Show status" in result.output or "instances" in result.output.lower()

    @patch(LIST_INSTANCES_PATH)
    def test_status_with_instances(self, mock_list_instances):
        """Test status command with configured instances."""
        mock_list_instances.return_value = [
            InstanceInfo(
                name="jdx4",
                version="9.0.1",
                environment="dev",
                url="http://localhost:8084/jw",
                web_port=8084,
                db_port=3309,
                status="running",
                response_time_ms=45,
            ),
            InstanceInfo(
                name="jdx5",
                version="9.0.1",
                environment="staging",
                url="http://localhost:8085/jw",
                web_port=8085,
                db_port=3310,
                status="stopped",
                response_time_ms=None,
            ),
        ]

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "jdx4" in result.output
        assert "jdx5" in result.output
        assert "running" in result.output
        assert "stopped" in result.output

    @patch(LIST_INSTANCES_PATH)
    def test_status_no_check(self, mock_list_instances):
        """Test status command with --no-check flag."""
        mock_list_instances.return_value = [
            InstanceInfo(
                name="jdx4",
                version="9.0.1",
                environment="dev",
                url="http://localhost:8084/jw",
                web_port=8084,
                db_port=3309,
                status="unknown",
                response_time_ms=None,
            ),
        ]

        result = runner.invoke(app, ["status", "--no-check"])

        assert result.exit_code == 0
        # Verify list_instances was called with check_status=False
        mock_list_instances.assert_called_once_with(check_status=False)

    @patch(LIST_INSTANCES_PATH)
    def test_status_empty_instances(self, mock_list_instances):
        """Test status command with no instances configured."""
        mock_list_instances.return_value = []

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "No instances found" in result.output

    @patch(LIST_INSTANCES_PATH)
    def test_status_file_not_found(self, mock_list_instances):
        """Test status command when config file doesn't exist."""
        mock_list_instances.side_effect = FileNotFoundError("Config file not found")

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "No instances configured" in result.output or "Error" in result.output


class TestStatusDisplay:
    """Tests for status command display formatting."""

    @patch(LIST_INSTANCES_PATH)
    def test_displays_running_status_icon(self, mock_list_instances):
        """Test that running instances show correct status icon."""
        mock_list_instances.return_value = [
            InstanceInfo(
                name="jdx4",
                version="9.0.1",
                environment="dev",
                url="http://localhost:8084/jw",
                web_port=8084,
                db_port=3309,
                status="running",
                response_time_ms=45,
            ),
        ]

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        # Check for running indicator (checkmark or "running")
        assert "running" in result.output.lower()

    @patch(LIST_INSTANCES_PATH)
    def test_displays_response_time(self, mock_list_instances):
        """Test that response time is displayed for running instances."""
        mock_list_instances.return_value = [
            InstanceInfo(
                name="jdx4",
                version="9.0.1",
                environment="dev",
                url="http://localhost:8084/jw",
                web_port=8084,
                db_port=3309,
                status="running",
                response_time_ms=123,
            ),
        ]

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "123" in result.output  # Response time in ms


class TestMainApp:
    """Tests for the main CLI app."""

    def test_no_args_shows_help(self):
        """Test that running without arguments shows help."""
        result = runner.invoke(app, [])

        # Should show help or usage information
        assert "status" in result.output.lower() or "Usage" in result.output

    def test_main_help(self):
        """Test that --help works on main command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()
