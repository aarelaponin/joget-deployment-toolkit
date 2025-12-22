"""
Tests for the check (validation) command.
"""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from joget_deployment_toolkit.cli.main import app
from joget_deployment_toolkit.models import InstanceStatus, ApplicationInfo, FormInfo

runner = CliRunner()

# Patch paths
GET_INSTANCE_STATUS_PATH = "joget_deployment_toolkit.inventory.get_instance_status"
JOGET_CLIENT_PATH = "joget_deployment_toolkit.client.JogetClient"


def create_valid_form(form_id: str, name: str) -> dict:
    """Create a valid form JSON structure."""
    return {
        "className": "org.joget.apps.form.model.Form",
        "properties": {"id": form_id, "name": name, "tableName": form_id},
        "elements": [],
    }


def create_form_with_dependency(form_id: str, name: str, depends_on: str) -> dict:
    """Create a form with a dependency on another form."""
    return {
        "className": "org.joget.apps.form.model.Form",
        "properties": {"id": form_id, "name": name, "tableName": form_id},
        "elements": [{
            "className": "org.joget.plugin.enterprise.FormGrid",
            "properties": {"id": "grid", "formDefId": depends_on},
            "elements": []
        }],
    }


class TestCheckCommand:
    """Tests for joget-deploy check command."""

    def test_check_help(self):
        """Test that --help works."""
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0
        assert "Validate" in result.output or "form package" in result.output
        assert "--instance" in result.output
        assert "--app" in result.output

    def test_check_valid_package(self, tmp_path):
        """Test checking a valid package."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        form1 = create_valid_form("testForm1", "Test Form 1")
        form2 = create_valid_form("testForm2", "Test Form 2")

        (forms_dir / "testForm1.json").write_text(json.dumps(form1))
        (forms_dir / "testForm2.json").write_text(json.dumps(form2))

        result = runner.invoke(app, ["check", str(forms_dir)])

        assert result.exit_code == 0
        assert "VALIDATION PASSED" in result.output
        assert "Forms:" in result.output

    def test_check_empty_directory(self, tmp_path):
        """Test error when directory has no JSON files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(app, ["check", str(empty_dir)])

        assert result.exit_code == 2
        assert "No JSON files found" in result.output

    def test_check_invalid_json(self, tmp_path):
        """Test error when JSON file is invalid."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()
        (forms_dir / "badForm.json").write_text("{ invalid json }")

        result = runner.invoke(app, ["check", str(forms_dir)])

        assert result.exit_code == 2
        assert "Invalid JSON" in result.output or "validation errors" in result.output.lower()

    def test_check_missing_classname(self, tmp_path):
        """Test error when form missing className."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        bad_form = {"properties": {"id": "test"}}
        (forms_dir / "badForm.json").write_text(json.dumps(bad_form))

        result = runner.invoke(app, ["check", str(forms_dir)])

        assert result.exit_code == 2
        assert "className" in result.output

    def test_check_form_id_too_long(self, tmp_path):
        """Test error when form ID exceeds 20 characters."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        long_id = "thisFormIdIsWayTooLongForJoget"
        form = create_valid_form(long_id, "Long Form")
        (forms_dir / f"{long_id}.json").write_text(json.dumps(form))

        result = runner.invoke(app, ["check", str(forms_dir)])

        assert result.exit_code == 2
        assert "exceeds 20 characters" in result.output

    def test_check_with_dependencies(self, tmp_path):
        """Test checking package with internal dependencies."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        parent = create_form_with_dependency("parent", "Parent Form", "child")
        child = create_valid_form("child", "Child Form")

        (forms_dir / "parent.json").write_text(json.dumps(parent))
        (forms_dir / "child.json").write_text(json.dumps(child))

        result = runner.invoke(app, ["check", str(forms_dir)])

        assert result.exit_code == 0
        assert "VALIDATION PASSED" in result.output
        # Verify deployment order shows dependency
        assert "child" in result.output
        assert "parent" in result.output

    def test_check_circular_dependency(self, tmp_path):
        """Test error when circular dependencies exist."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        form_a = create_form_with_dependency("formA", "Form A", "formB")
        form_b = create_form_with_dependency("formB", "Form B", "formA")

        (forms_dir / "formA.json").write_text(json.dumps(form_a))
        (forms_dir / "formB.json").write_text(json.dumps(form_b))

        result = runner.invoke(app, ["check", str(forms_dir)])

        assert result.exit_code == 2
        assert "Circular" in result.output or "circular" in result.output

    def test_check_external_dependencies(self, tmp_path):
        """Test detecting external dependencies."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        form = create_form_with_dependency("myForm", "My Form", "externalForm")
        (forms_dir / "myForm.json").write_text(json.dumps(form))

        result = runner.invoke(app, ["check", str(forms_dir), "--verbose"])

        assert result.exit_code == 0
        assert "externalForm" in result.output
        assert "External" in result.output


class TestCheckWithInstance:
    """Tests for check command with instance connection."""

    def test_check_verifies_external_deps(self, tmp_path):
        """Test that external deps are verified against target app."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        form = create_form_with_dependency("myForm", "My Form", "existingForm")
        (forms_dir / "myForm.json").write_text(json.dumps(form))

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )

            mock_client = MagicMock()
            mock_client.list_forms.return_value = [
                FormInfo(
                    form_id="existingForm",
                    form_name="Existing Form",
                    table_name="existingForm",
                    app_id="farmersPortal",
                    app_version="1"
                )
            ]
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "check", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal"
            ])

        assert result.exit_code == 0
        assert "VALIDATION PASSED" in result.output

    def test_check_reports_missing_external_deps(self, tmp_path):
        """Test that missing external deps are reported."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        form = create_form_with_dependency("myForm", "My Form", "missingForm")
        (forms_dir / "myForm.json").write_text(json.dumps(form))

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status, \
             patch(JOGET_CLIENT_PATH) as mock_client_class:

            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=True, response_time_ms=45
            )

            mock_client = MagicMock()
            mock_client.list_forms.return_value = []  # No forms exist
            mock_client_class.from_instance.return_value = mock_client

            result = runner.invoke(app, [
                "check", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal",
                "--verbose"
            ])

        # Should still pass (missing external deps is warning, not blocker)
        assert result.exit_code == 0
        assert "missing" in result.output.lower()

    def test_check_handles_unreachable_instance(self, tmp_path):
        """Test graceful handling of unreachable instance."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        form = create_valid_form("myForm", "My Form")
        (forms_dir / "myForm.json").write_text(json.dumps(form))

        with patch(GET_INSTANCE_STATUS_PATH) as mock_status:
            mock_status.return_value = InstanceStatus(
                name="jdx4", reachable=False, error="Connection refused"
            )

            result = runner.invoke(app, [
                "check", str(forms_dir),
                "--instance", "jdx4",
                "--app", "farmersPortal"
            ])

        # Should still pass with warning
        assert result.exit_code == 0
        assert "not reachable" in result.output


class TestCheckVerbose:
    """Tests for check command verbose output."""

    def test_verbose_shows_form_names(self, tmp_path):
        """Test that verbose mode shows form names."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        form = create_valid_form("testForm", "My Test Form Name")
        (forms_dir / "testForm.json").write_text(json.dumps(form))

        result = runner.invoke(app, ["check", str(forms_dir), "--verbose"])

        assert result.exit_code == 0
        assert "My Test Form Name" in result.output

    def test_verbose_shows_external_deps(self, tmp_path):
        """Test that verbose mode lists external dependencies."""
        forms_dir = tmp_path / "forms"
        forms_dir.mkdir()

        form = create_form_with_dependency("myForm", "My Form", "externalLookup")
        (forms_dir / "myForm.json").write_text(json.dumps(form))

        result = runner.invoke(app, ["check", str(forms_dir), "--verbose"])

        assert result.exit_code == 0
        assert "externalLookup" in result.output


class TestCheckRealForms:
    """Tests using real form files."""

    @pytest.fixture
    def imm_forms_dir(self) -> Path:
        """Get path to IMM forms directory."""
        return Path(__file__).parent.parent.parent / "components" / "imm" / "forms"

    def test_check_imm_forms(self, imm_forms_dir: Path):
        """Test checking real IMM forms package."""
        if not imm_forms_dir.exists():
            pytest.skip("IMM forms directory not found")

        result = runner.invoke(app, ["check", str(imm_forms_dir)])

        assert result.exit_code == 0
        assert "VALIDATION PASSED" in result.output

    def test_check_imm_forms_verbose(self, imm_forms_dir: Path):
        """Test checking real IMM forms with verbose output."""
        if not imm_forms_dir.exists():
            pytest.skip("IMM forms directory not found")

        result = runner.invoke(app, ["check", str(imm_forms_dir), "--verbose"])

        assert result.exit_code == 0
        assert "VALIDATION PASSED" in result.output
        # Should show deployment order
        assert "Deployment Order" in result.output
