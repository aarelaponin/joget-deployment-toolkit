"""
Tests for the forms deployment command.
"""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from joget_deployment_toolkit.cli.main import app
from joget_deployment_toolkit.models import InstanceStatus, ApplicationInfo, FormInfo

runner = CliRunner()

# Patch paths - must match where the imports are used, not where they're defined
GET_INSTANCE_STATUS_PATH = "joget_deployment_toolkit.inventory.get_instance_status"
JOGET_CLIENT_PATH = "joget_deployment_toolkit.client.JogetClient"
GET_INSTANCE_PATH = "joget_deployment_toolkit.config.shared_loader.get_instance"


def create_test_forms_dir(tmp_path: Path) -> Path:
    """Helper to create a temp directory with test form JSON files."""
    forms_dir = tmp_path / "forms"
    forms_dir.mkdir()

    form1 = {
        "className": "org.joget.apps.form.model.Form",
        "properties": {"id": "testForm1", "name": "Test Form 1", "tableName": "testForm1"},
        "elements": [],
    }
    form2 = {
        "className": "org.joget.apps.form.model.Form",
        "properties": {"id": "testForm2", "name": "Test Form 2", "tableName": "testForm2"},
        "elements": [],
    }

    (forms_dir / "testForm1.json").write_text(json.dumps(form1))
    (forms_dir / "testForm2.json").write_text(json.dumps(form2))

    return forms_dir


class TestFormsCommand:
    """Tests for joget-deploy forms command."""

    def test_forms_help(self):
        """Test that --help works."""
        result = runner.invoke(app, ["forms", "--help"])
        assert result.exit_code == 0
        assert "Deploy form JSON files" in result.output
        assert "--instance" in result.output
        assert "--app" in result.output
        assert "--dry-run" in result.output

    def test_forms_interactive_mode_without_instance(self, tmp_path):
        """Test that interactive mode is triggered when instance is not provided."""
        forms_dir = create_test_forms_dir(tmp_path)

        # Without instance flag, it tries to enter interactive mode
        # In test environment without TTY, this will fail to list instances
        with patch("joget_deployment_toolkit.inventory.list_instances") as mock_list:
            mock_list.side_effect = FileNotFoundError("No config file")

            result = runner.invoke(app, ["forms", str(forms_dir)])

        # Should fail because no instances configured
        assert result.exit_code == 2
        assert "No instances configured" in result.output

    def test_forms_interactive_cancelled(self, tmp_path):
        """Test that cancelling instance selection exits gracefully."""
        forms_dir = create_test_forms_dir(tmp_path)

        with patch("joget_deployment_toolkit.inventory.list_instances") as mock_list, \
             patch("joget_deployment_toolkit.cli.interactive.select_instance") as mock_select:

            from joget_deployment_toolkit.models import InstanceInfo
            mock_list.return_value = [
                InstanceInfo(
                    name="jdx4",
                    version="9.0.1",
                    environment="dev",
                    url="http://localhost:8084/jw",
                    web_port=8084,
                    db_port=3309,
                    status="running",
                    response_time_ms=45,
                )
            ]
            mock_select.return_value = None  # User cancelled

            result = runner.invoke(app, ["forms", str(forms_dir)])

        assert result.exit_code == 3
        assert "cancelled" in result.output.lower()


class TestFormsWithMocks:
    """Tests requiring mocked external dependencies."""

    def test_forms_instance_not_found(self, tmp_path):
        """Test error when instance is not in configuration."""
        forms_dir = create_test_forms_dir(tmp_path)

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status:
            mock_status.side_effect = KeyError("Instance not found")

            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "nonexistent",
                "--app", "farmersPortal",
                "--yes"
            ])

        assert result.exit_code == 2
        assert "not found in configuration" in result.output

    def test_forms_instance_not_reachable(self, tmp_path):
        """Test error when instance is not reachable."""
        forms_dir = create_test_forms_dir(tmp_path)

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status:
            mock_status.return_value = InstanceStatus(
                name="jdx4",
                reachable=False,
                error="Connection refused",
            )

            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
                "--yes"
            ])

        assert result.exit_code == 2
        assert "not reachable" in result.output

    def test_forms_app_not_found(self, tmp_path):
        """Test error when application doesn't exist."""
        forms_dir = create_test_forms_dir(tmp_path)

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )

            mock_client = MagicMock()
            mock_client.list_applications.return_value = [
                ApplicationInfo(id="otherApp", name="Other", version="1", published=True)
            ]
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "jdx4",
                "--app", "nonexistent",
                "--yes"
            ])

        assert result.exit_code == 2
        assert "not found" in result.output

    def test_forms_dry_run(self, tmp_path):
        """Test dry-run mode doesn't deploy."""
        forms_dir = create_test_forms_dir(tmp_path)

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class, \
             patch(GET_INSTANCE_PATH) as mock_get_instance:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )
            mock_get_instance.return_value = {"url": "http://localhost:8084/jw"}

            mock_client = MagicMock()
            mock_client.list_applications.return_value = [
                ApplicationInfo(id="farmersPortal", name="FP", version="1", published=True)
            ]
            mock_client.list_forms.return_value = []
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
                "--dry-run"
            ])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        mock_client.create_form.assert_not_called()

    def test_forms_successful_deployment(self, tmp_path):
        """Test successful form deployment."""
        forms_dir = create_test_forms_dir(tmp_path)

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class, \
             patch(GET_INSTANCE_PATH) as mock_get_instance:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )
            mock_get_instance.return_value = {"url": "http://localhost:8084/jw"}

            mock_client = MagicMock()
            mock_client.list_applications.return_value = [
                ApplicationInfo(id="farmersPortal", name="FP", version="1", published=True)
            ]
            mock_client.list_forms.return_value = []
            mock_client.create_form.return_value = {"id": "uuid-123", "errors": {}}
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
                "--yes"
            ])

        assert result.exit_code == 0
        assert "DEPLOYMENT COMPLETE" in result.output
        assert "Created: 2" in result.output
        assert mock_client.create_form.call_count == 2


class TestFormsValidation:
    """Tests for form file validation."""

    def test_empty_directory(self, tmp_path):
        """Test error when directory has no JSON files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )

            mock_client = MagicMock()
            mock_client.list_applications.return_value = [
                ApplicationInfo(id="farmersPortal", name="FP", version="1", published=True)
            ]
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "forms", str(empty_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
                "--yes"
            ])

        assert result.exit_code == 2
        assert "No JSON files found" in result.output

    def test_invalid_json_file(self, tmp_path):
        """Test error when JSON file is invalid."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()
        (forms_dir / "badForm.json").write_text("{ invalid json }")

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )

            mock_client = MagicMock()
            mock_client.list_applications.return_value = [
                ApplicationInfo(id="farmersPortal", name="FP", version="1", published=True)
            ]
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
                "--yes"
            ])

        assert result.exit_code == 2
        assert "Invalid JSON" in result.output or "Validation errors" in result.output


class TestFormsDependencyAnalysis:
    """Tests for dependency analysis integration."""

    def test_forms_with_dependencies_ordered_correctly(self, tmp_path):
        """Test that forms are deployed in dependency order."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        # Create parent form that depends on child
        parent = {
            "className": "org.joget.apps.form.model.Form",
            "properties": {"id": "parent", "name": "Parent Form", "tableName": "parent"},
            "elements": [{
                "className": "org.joget.plugin.enterprise.FormGrid",
                "properties": {"id": "grid", "formDefId": "child"},
                "elements": []
            }],
        }
        child = {
            "className": "org.joget.apps.form.model.Form",
            "properties": {"id": "child", "name": "Child Form", "tableName": "child"},
            "elements": [],
        }

        (forms_dir / "parent.json").write_text(json.dumps(parent))
        (forms_dir / "child.json").write_text(json.dumps(child))

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class, \
             patch(GET_INSTANCE_PATH) as mock_get_instance:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )
            mock_get_instance.return_value = {"url": "http://localhost:8084/jw"}

            mock_client = MagicMock()
            mock_client.list_applications.return_value = [
                ApplicationInfo(id="farmersPortal", name="FP", version="1", published=True)
            ]
            mock_client.list_forms.return_value = []
            mock_client.create_form.return_value = {"id": "uuid-123", "errors": {}}
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
                "--yes"
            ])

        assert result.exit_code == 0
        # Verify child was deployed before parent
        calls = mock_client.create_form.call_args_list
        assert len(calls) == 2
        # First call should be for child
        assert calls[0][1]["payload"]["form_id"] == "child"
        # Second call should be for parent
        assert calls[1][1]["payload"]["form_id"] == "parent"

    def test_circular_dependency_blocks_deployment(self, tmp_path):
        """Test that circular dependencies prevent deployment."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        # Create forms with circular dependency
        form_a = {
            "className": "org.joget.apps.form.model.Form",
            "properties": {"id": "formA", "name": "Form A", "tableName": "formA"},
            "elements": [{
                "className": "org.joget.plugin.enterprise.FormGrid",
                "properties": {"formDefId": "formB"},
                "elements": []
            }],
        }
        form_b = {
            "className": "org.joget.apps.form.model.Form",
            "properties": {"id": "formB", "name": "Form B", "tableName": "formB"},
            "elements": [{
                "className": "org.joget.plugin.enterprise.FormGrid",
                "properties": {"formDefId": "formA"},
                "elements": []
            }],
        }

        (forms_dir / "formA.json").write_text(json.dumps(form_a))
        (forms_dir / "formB.json").write_text(json.dumps(form_b))

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )

            mock_client = MagicMock()
            mock_client.list_applications.return_value = [
                ApplicationInfo(id="farmersPortal", name="FP", version="1", published=True)
            ]
            mock_client.list_forms.return_value = []
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
                "--yes"
            ])

        assert result.exit_code == 2
        assert "Circular" in result.output or "circular" in result.output


class TestFormsConfirmation:
    """Tests for confirmation prompts."""

    def test_cancel_on_no_confirmation(self, tmp_path):
        """Test deployment is cancelled when user says no."""
        forms_dir = create_test_forms_dir(tmp_path)

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class, \
             patch(GET_INSTANCE_PATH) as mock_get_instance:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )
            mock_get_instance.return_value = {"url": "http://localhost:8084/jw"}

            mock_client = MagicMock()
            mock_client.list_applications.return_value = [
                ApplicationInfo(id="farmersPortal", name="FP", version="1", published=True)
            ]
            mock_client.list_forms.return_value = []
            mock_client_class.from_instance.return_value = mock_client

            # Simulate user typing 'n' for no
            result = runner.invoke(app, [
                "forms", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
            ], input="n\n")

        assert result.exit_code == 3
        assert "cancelled" in result.output.lower()
        mock_client.create_form.assert_not_called()
