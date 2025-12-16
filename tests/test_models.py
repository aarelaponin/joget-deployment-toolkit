"""
Tests for joget_deployment_toolkit.models module.
"""

from datetime import datetime

from joget_deployment_toolkit.models import (
    ApplicationInfo,
    BatchResult,
    DatabaseConfig,
    ExportResult,
    FormInfo,
    FormResult,
    Health,
    HealthCheckResult,
    HealthStatus,
    ImportResult,
    SystemInfo,
    application_info_from_dict,
    form_info_from_dict,
    parse_datetime,
    plugin_info_from_dict,
)


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_status_values(self):
        """Test HealthStatus has correct values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestSystemInfo:
    """Test SystemInfo model."""

    def test_init_minimal(self):
        """Test initialization with minimal data."""
        info = SystemInfo(version="9.0.0", build="12345", license_type="Enterprise")

        assert info.version == "9.0.0"
        assert info.build == "12345"
        assert info.license_type == "Enterprise"
        assert info.license_to is None
        assert info.license_expiry is None

    def test_init_complete(self):
        """Test initialization with complete data."""
        expiry = datetime(2025, 12, 31)
        info = SystemInfo(
            version="9.0.0",
            build="12345",
            license_type="Enterprise",
            license_to="Test Company",
            license_expiry=expiry,
        )

        assert info.license_to == "Test Company"
        assert info.license_expiry == expiry

    def test_str_representation(self):
        """Test string representation."""
        info = SystemInfo(version="9.0.0", build="12345", license_type="Enterprise")
        result = str(info)

        assert "9.0.0" in result
        assert "12345" in result
        assert "Enterprise" in result


class TestHealthCheckResult:
    """Test HealthCheckResult model."""

    def test_init_passed(self):
        """Test initialization for passed check."""
        result = HealthCheckResult(name="reachable", passed=True, message="OK")

        assert result.name == "reachable"
        assert result.passed is True
        assert result.message == "OK"

    def test_init_failed(self):
        """Test initialization for failed check."""
        result = HealthCheckResult(
            name="authenticated", passed=False, message="Auth failed", duration_ms=100.5
        )

        assert result.passed is False
        assert result.message == "Auth failed"
        assert result.duration_ms == 100.5

    def test_str_representation_passed(self):
        """Test string representation for passed check."""
        result = HealthCheckResult(name="test", passed=True)
        output = str(result)

        assert "✓" in output or "test" in output

    def test_str_representation_failed(self):
        """Test string representation for failed check."""
        result = HealthCheckResult(name="test", passed=False, message="Error")
        output = str(result)

        assert "✗" in output or "test" in output or "Error" in output


class TestHealth:
    """Test Health model."""

    def test_init(self):
        """Test initialization."""
        health = Health(
            status=HealthStatus.HEALTHY, reachable=True, authenticated=True, version="9.0.0"
        )

        assert health.status == HealthStatus.HEALTHY
        assert health.reachable is True
        assert health.authenticated is True
        assert health.version == "9.0.0"

    def test_is_healthy_true(self):
        """Test is_healthy returns True for healthy status."""
        health = Health(status=HealthStatus.HEALTHY, reachable=True, authenticated=True)

        assert health.is_healthy() is True

    def test_is_healthy_false_for_degraded(self):
        """Test is_healthy returns False for degraded status."""
        health = Health(status=HealthStatus.DEGRADED, reachable=True, authenticated=False)

        assert health.is_healthy() is False

    def test_is_healthy_false_for_unhealthy(self):
        """Test is_healthy returns False for unhealthy status."""
        health = Health(status=HealthStatus.UNHEALTHY, reachable=False, authenticated=False)

        assert health.is_healthy() is False


class TestFormInfo:
    """Test FormInfo model."""

    def test_str_representation(self):
        """Test string representation."""
        form = FormInfo(
            form_id="test_form",
            form_name="Test Form",
            table_name="app_fd_test",
            app_id="app1",
            app_version="1",
        )
        result = str(form)

        assert "test_form" in result
        assert "Test Form" in result


class TestFormResult:
    """Test FormResult model."""

    def test_success(self):
        """Test successful form result."""
        result = FormResult(success=True, form_id="test_form", message="Created successfully")

        assert result.success is True
        assert result.form_id == "test_form"
        assert result.message == "Created successfully"
        assert result.errors is None

    def test_failure_with_errors(self):
        """Test failed form result with errors."""
        errors = ["Field 'name' is required", "Invalid value"]
        result = FormResult(
            success=False, form_id="test_form", message="Validation failed", errors=errors
        )

        assert result.success is False
        assert result.errors == errors

    def test_str_representation_success(self):
        """Test string representation for success."""
        result = FormResult(success=True, form_id="test_form")
        output = str(result)

        assert "Success" in output
        assert "test_form" in output

    def test_str_representation_failure(self):
        """Test string representation for failure."""
        result = FormResult(success=False, form_id="test_form", message="Error occurred")
        output = str(result)

        assert "Failed" in output
        assert "test_form" in output


class TestApplicationInfo:
    """Test ApplicationInfo model."""

    def test_init(self):
        """Test initialization."""
        app = ApplicationInfo(id="test_app", name="Test App", version="1", published=True)

        assert app.id == "test_app"
        assert app.name == "Test App"
        assert app.version == "1"
        assert app.published is True

    def test_str_representation(self):
        """Test string representation."""
        app = ApplicationInfo(id="app1", name="App", version="1", published=True)
        result = str(app)

        assert "app1" in result
        assert "App" in result
        assert "published" in result


class TestBatchResult:
    """Test BatchResult model."""

    def test_init(self):
        """Test initialization."""
        result = BatchResult(total=10, successful=8, failed=2)

        assert result.total == 10
        assert result.successful == 8
        assert result.failed == 2

    def test_success_rate(self):
        """Test success_rate calculation."""
        result = BatchResult(total=10, successful=8, failed=2)
        assert result.success_rate() == 80.0

    def test_success_rate_zero_total(self):
        """Test success_rate with zero total."""
        result = BatchResult(total=0, successful=0, failed=0)
        assert result.success_rate() == 0.0

    def test_is_complete_success(self):
        """Test is_complete_success."""
        result = BatchResult(total=10, successful=10, failed=0)
        assert result.is_complete_success() is True

        result = BatchResult(total=10, successful=8, failed=2)
        assert result.is_complete_success() is False


class TestExportResult:
    """Test ExportResult model."""

    def test_success(self):
        """Test successful export."""
        result = ExportResult(
            success=True, output_path="/path/to/export.zip", file_size_bytes=1024, duration_ms=500.0
        )

        assert result.success is True
        assert result.output_path == "/path/to/export.zip"
        assert result.file_size_bytes == 1024

    def test_str_representation(self):
        """Test string representation."""
        result = ExportResult(success=True, output_path="/test.zip", file_size_bytes=2048)
        output = str(result)

        assert "Success" in output
        assert "/test.zip" in output
        assert "2048" in output


class TestImportResult:
    """Test ImportResult model."""

    def test_success(self):
        """Test successful import."""
        result = ImportResult(
            success=True, app_id="test_app", app_version="1", message="Imported successfully"
        )

        assert result.success is True
        assert result.app_id == "test_app"
        assert result.app_version == "1"

    def test_with_warnings(self):
        """Test import with warnings."""
        warnings = ["Warning 1", "Warning 2"]
        result = ImportResult(success=True, app_id="test_app", app_version="1", warnings=warnings)

        assert result.warnings == warnings


class TestDatabaseConfig:
    """Test DatabaseConfig model."""

    def test_to_connection_string(self):
        """Test connection string generation."""
        config = DatabaseConfig(
            host="localhost", port=3306, database="jwdb", user="admin", password="password123"
        )

        conn_str = config.to_connection_string()

        assert "mysql://" in conn_str
        assert "localhost:3306" in conn_str
        assert "jwdb" in conn_str
        assert "admin" in conn_str
        assert "password123" in conn_str

    def test_to_connection_string_with_ssl(self):
        """Test connection string with SSL."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="jwdb",
            user="admin",
            password="password123",
            ssl=True,
        )

        conn_str = config.to_connection_string()

        assert "mysql+ssl://" in conn_str

    def test_str_hides_password(self):
        """Test string representation hides password."""
        config = DatabaseConfig(
            host="localhost", port=3306, database="jwdb", user="admin", password="secret123"
        )

        output = str(config)

        # Password should not be in output
        assert "secret123" not in output
        assert "admin" in output
        assert "localhost" in output


class TestUtilityFunctions:
    """Test utility functions."""

    def test_parse_datetime_standard_format(self):
        """Test parsing standard datetime format."""
        result = parse_datetime("2025-01-15 10:30:00")
        assert result == datetime(2025, 1, 15, 10, 30, 0)

    def test_parse_datetime_iso_format(self):
        """Test parsing ISO format."""
        result = parse_datetime("2025-01-15T10:30:00")
        assert result == datetime(2025, 1, 15, 10, 30, 0)

    def test_parse_datetime_date_only(self):
        """Test parsing date-only format."""
        result = parse_datetime("2025-01-15")
        assert result == datetime(2025, 1, 15, 0, 0, 0)

    def test_parse_datetime_invalid(self):
        """Test parsing invalid datetime returns None."""
        result = parse_datetime("invalid-date")
        assert result is None

    def test_parse_datetime_none(self):
        """Test parsing None returns None."""
        result = parse_datetime(None)
        assert result is None

    def test_form_info_from_dict(self, sample_form_data):
        """Test creating FormInfo from dict."""
        form = form_info_from_dict(sample_form_data)

        assert form.form_id == "test_form"
        assert form.form_name == "Test Form"
        assert form.table_name == "app_fd_test_form"

    def test_application_info_from_dict(self, sample_app_data):
        """Test creating ApplicationInfo from dict."""
        app = application_info_from_dict(sample_app_data)

        assert app.id == "test_app"
        assert app.name == "Test Application"
        assert app.version == "1"
        assert app.published is True

    def test_plugin_info_from_dict(self, sample_plugin_data):
        """Test creating PluginInfo from dict."""
        plugin = plugin_info_from_dict(sample_plugin_data)

        assert plugin.id == "test_plugin"
        assert plugin.name == "Test Plugin"
        assert plugin.version == "1.0.0"
        assert plugin.type == "formElement"
