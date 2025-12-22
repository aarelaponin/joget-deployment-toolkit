"""
Tests for the interactive prompts module.
"""

import pytest
from unittest.mock import patch, MagicMock

from joget_deployment_toolkit.cli.interactive import (
    select_instance,
    select_application,
    confirm_deployment,
    select_from_list,
)
from joget_deployment_toolkit.models import InstanceInfo, ApplicationInfo


class TestSelectInstance:
    """Tests for select_instance function."""

    def test_select_instance_returns_selected_name(self):
        """Test that selecting an instance returns its name."""
        instances = [
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
                status="running",
                response_time_ms=50,
            ),
        ]

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = "jdx4"
            mock_q.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

            result = select_instance(instances)

        assert result == "jdx4"

    def test_select_instance_empty_list(self):
        """Test with empty instances list."""
        with patch("joget_deployment_toolkit.cli.interactive.show_error") as mock_error:
            result = select_instance([])

        assert result is None
        mock_error.assert_called_once()

    def test_select_instance_cancelled(self):
        """Test user cancelling selection."""
        instances = [
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

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = None
            mock_q.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

            result = select_instance(instances)

        assert result is None

    def test_select_instance_keyboard_interrupt(self):
        """Test handling KeyboardInterrupt."""
        instances = [
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

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.side_effect = KeyboardInterrupt()
            mock_q.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

            result = select_instance(instances)

        assert result is None


class TestSelectApplication:
    """Tests for select_application function."""

    def test_select_application_returns_id(self):
        """Test that selecting an app returns its ID."""
        apps = [
            ApplicationInfo(id="farmersPortal", name="Farmers Portal", version="1", published=True),
            ApplicationInfo(id="masterData", name="Master Data", version="1", published=True),
        ]

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = "farmersPortal"

            # Create a mock Choice class that returns sortable objects
            class MockChoice:
                def __init__(self, **kwargs):
                    self.title = kwargs.get("title")
                    self.value = kwargs.get("value")

            mock_q.Choice = MockChoice

            result = select_application(apps)

        assert result == "farmersPortal"

    def test_select_application_empty_list(self):
        """Test with empty applications list."""
        with patch("joget_deployment_toolkit.cli.interactive.show_error") as mock_error:
            result = select_application([])

        assert result is None
        mock_error.assert_called_once()

    def test_select_application_cancelled(self):
        """Test user cancelling selection."""
        apps = [
            ApplicationInfo(id="farmersPortal", name="Farmers Portal", version="1", published=True),
        ]

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = None

            class MockChoice:
                def __init__(self, **kwargs):
                    self.title = kwargs.get("title")
                    self.value = kwargs.get("value")

            mock_q.Choice = MockChoice

            result = select_application(apps)

        assert result is None


class TestConfirmDeployment:
    """Tests for confirm_deployment function."""

    def test_confirm_returns_true(self):
        """Test confirmation returns True when user confirms."""
        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.confirm.return_value.ask.return_value = True

            result = confirm_deployment(
                instance="jdx4",
                app_id="farmersPortal",
                form_count=5,
                create_count=3,
                update_count=2,
            )

        assert result is True

    def test_confirm_returns_false(self):
        """Test confirmation returns False when user declines."""
        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.confirm.return_value.ask.return_value = False

            result = confirm_deployment(
                instance="jdx4",
                app_id="farmersPortal",
                form_count=5,
                create_count=3,
                update_count=2,
            )

        assert result is False

    def test_confirm_keyboard_interrupt(self):
        """Test handling KeyboardInterrupt."""
        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.confirm.return_value.ask.side_effect = KeyboardInterrupt()

            result = confirm_deployment(
                instance="jdx4",
                app_id="farmersPortal",
                form_count=5,
                create_count=0,
                update_count=0,
            )

        assert result is False


class TestSelectFromList:
    """Tests for select_from_list function."""

    def test_select_from_list_returns_selection(self):
        """Test selecting from a list of strings."""
        items = ["option1", "option2", "option3"]

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = "option2"
            mock_q.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

            result = select_from_list(items, "Select an option")

        assert result == "option2"

    def test_select_from_list_empty(self):
        """Test with empty list."""
        result = select_from_list([], "Select an option")
        assert result is None

    def test_select_from_list_cancelled(self):
        """Test user cancelling selection."""
        items = ["option1"]

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = None
            mock_q.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

            result = select_from_list(items, "Select an option")

        assert result is None


class TestInstanceChoiceFormatting:
    """Tests for instance choice formatting."""

    def test_running_instance_format(self):
        """Test that running instances show correct format."""
        instances = [
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

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = "jdx4"
            choices_captured = []

            def capture_choice(**kwargs):
                choices_captured.append(kwargs)
                return kwargs

            mock_q.Choice = MagicMock(side_effect=capture_choice)

            select_instance(instances)

        # Find the jdx4 choice
        jdx4_choice = next((c for c in choices_captured if c.get("value") == "jdx4"), None)
        assert jdx4_choice is not None
        assert "running" in jdx4_choice["title"]
        assert "45ms" in jdx4_choice["title"]
        assert jdx4_choice.get("disabled") is None

    def test_stopped_instance_disabled(self):
        """Test that stopped instances are disabled."""
        instances = [
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

        with patch("joget_deployment_toolkit.cli.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = None
            choices_captured = []

            def capture_choice(**kwargs):
                choices_captured.append(kwargs)
                return kwargs

            mock_q.Choice = MagicMock(side_effect=capture_choice)

            select_instance(instances)

        # Find the jdx5 choice
        jdx5_choice = next((c for c in choices_captured if c.get("value") == "jdx5"), None)
        assert jdx5_choice is not None
        assert "stopped" in jdx5_choice["title"]
        assert jdx5_choice.get("disabled") == "not reachable"
