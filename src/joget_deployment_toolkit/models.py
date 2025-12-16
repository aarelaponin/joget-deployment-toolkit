#!/usr/bin/env python3
"""
Data models for Joget toolkit

Pydantic models and dataclasses for type-safe operations and API responses.

This module provides:
- Configuration models (JogetConfig, DatabaseConfig, DeploymentConfig)
- API response models (SystemInfo, FormInfo, ApplicationInfo, etc.)
- Result models (FormResult, BatchResult, etc.)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class FormInfo:
    """Information about a form in Joget"""

    form_id: str
    form_name: str
    table_name: str
    app_id: str
    app_version: str
    api_endpoint: str | None = None
    api_id: str | None = None
    form_definition: dict[str, Any] | None = None


class JogetConfig(BaseModel):
    """Configuration for Joget connection"""

    base_url: str = Field(
        ..., description="Base URL for Joget API (e.g., http://localhost:8080/jw/api/form)"
    )
    api_key: str | None = Field(None, description="Default API key for requests")
    timeout: int = Field(30, description="Request timeout in seconds")
    retry_count: int = Field(3, description="Number of retry attempts")
    retry_delay: float = Field(2.0, description="Delay between retries in seconds")
    debug: bool = Field(False, description="Enable debug logging")


class DatabaseConfig(BaseModel):
    """Configuration for Joget database connection"""

    host: str = Field("localhost", description="MySQL host")
    port: int = Field(3306, description="MySQL port")
    database: str = Field("jwdb", description="Database name")
    user: str = Field(..., description="Database user")
    password: str = Field(..., description="Database password")

    # Connection pool settings
    pool_name: str = Field("joget_pool", description="Connection pool name")
    pool_size: int = Field(5, description="Connection pool size")
    pool_reset_session: bool = Field(
        True, description="Reset session variables on connection reuse"
    )

    # Connection settings
    autocommit: bool = Field(False, description="Enable autocommit mode")
    use_unicode: bool = Field(True, description="Use Unicode for strings")
    charset: str = Field("utf8mb4", description="Character set")
    collation: str = Field("utf8mb4_unicode_ci", description="Collation")
    connection_timeout: int = Field(10, description="Connection timeout in seconds")

    # SSL settings
    ssl: bool = Field(False, description="Use SSL connection")
    ssl_ca: str | None = Field(None, description="Path to SSL CA certificate")
    ssl_cert: str | None = Field(None, description="Path to SSL client certificate")
    ssl_key: str | None = Field(None, description="Path to SSL client key")

    class Config:
        """Pydantic config"""

        # Allow password to be excluded from logs
        json_encoders = {str: lambda v: "***" if v else None}

    def to_connection_string(self) -> str:
        """
        Generate MySQL connection string.

        Returns:
            Connection string in format: mysql://user:password@host:port/database
            or mysql+ssl://... if SSL is enabled
        """
        protocol = "mysql+ssl" if self.ssl else "mysql"
        return f"{protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def __str__(self) -> str:
        """
        Human-readable representation that hides the password.

        Returns:
            String like "DatabaseConfig(user@host:port/database)"
        """
        ssl_marker = "+ssl" if self.ssl else ""
        return f"DatabaseConfig({self.user}@{self.host}:{self.port}/{self.database}{ssl_marker})"


class DeploymentConfig(BaseModel):
    """Configuration for form deployment"""

    target_app_id: str = Field(..., description="Target application ID")
    target_app_version: str = Field("1", description="Target application version")
    form_creator_api_id: str | None = Field(None, description="API ID for formCreator endpoint")
    form_creator_api_key: str | None = Field(None, description="API key for formCreator")
    create_api_endpoint: bool = Field(True, description="Create API endpoint for forms")
    create_crud: bool = Field(True, description="Create CRUD operations")
    api_name_prefix: str = Field("api_", description="Prefix for generated API names")


# ============================================================================
# API Response Models
# ============================================================================


class HealthStatus(str, Enum):
    """Overall health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class SystemInfo:
    """Joget system information from /web/json/monitoring/system/info"""

    version: str
    build: str
    license_type: str
    license_to: str | None = None
    license_expiry: datetime | None = None
    raw_data: dict[str, Any] | None = None

    def __str__(self):
        return f"Joget {self.version} build {self.build} ({self.license_type})"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    passed: bool
    message: str | None = None
    duration_ms: float | None = None

    def __str__(self):
        status = "✓" if self.passed else "✗"
        return f"{status} {self.name}" + (f": {self.message}" if self.message else "")


@dataclass
class Health:
    """Comprehensive health status."""

    status: HealthStatus
    reachable: bool
    authenticated: bool
    version: str | None = None
    checks: list[HealthCheckResult] = field(default_factory=list)
    timestamp: datetime | None = None

    def __str__(self):
        return (
            f"Health: {self.status.value} (reachable={self.reachable}, auth={self.authenticated})"
        )

    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY


@dataclass
class FormResult:
    """Result of form operation (create/update/delete)."""

    success: bool
    form_id: str
    message: str | None = None
    errors: list[str] | None = None
    raw_data: dict[str, Any] | None = None

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{status}: {self.form_id}" + (f" - {self.message}" if self.message else "")


@dataclass
class ApplicationInfo:
    """Basic application information from list_applications()."""

    id: str
    name: str
    version: str
    published: bool
    date_created: datetime | None = None
    date_modified: datetime | None = None
    raw_data: dict[str, Any] | None = None

    def __str__(self):
        status = "published" if self.published else "unpublished"
        return f"App({self.id} v{self.version}: {self.name}) [{status}]"


@dataclass
class ApplicationDetails(ApplicationInfo):
    """Detailed application information from get_application()."""

    description: str | None = None
    license: str | None = None
    forms: list[FormInfo] | None = None
    processes: list[str] | None = None
    datalists: list[str] | None = None
    userview: list[str] | None = None


@dataclass
class PluginInfo:
    """Plugin information from list_plugins()."""

    id: str
    name: str
    version: str
    type: str
    description: str | None = None
    class_name: str | None = None
    raw_data: dict[str, Any] | None = None

    def __str__(self):
        return f"Plugin({self.id} v{self.version}: {self.name}) [{self.type}]"


@dataclass
class PluginDetails(PluginInfo):
    """Detailed plugin information from get_plugin()."""

    properties: dict[str, Any] | None = None


@dataclass
class BatchResult:
    """Result of batch operation."""

    total: int
    successful: int
    failed: int
    errors: list[dict[str, Any]] | None = None
    results: list[dict[str, Any]] | None = None
    duration_ms: float | None = None

    def __str__(self):
        return f"Batch: {self.successful}/{self.total} successful, {self.failed} failed"

    def success_rate(self) -> float:
        return (self.successful / self.total * 100) if self.total > 0 else 0.0

    def is_complete_success(self) -> bool:
        return self.failed == 0 and self.successful == self.total


@dataclass
class ExportResult:
    """Result of application export operation."""

    success: bool
    output_path: str
    file_size_bytes: int | None = None
    duration_ms: float | None = None
    message: str | None = None

    def __str__(self):
        status = "Success" if self.success else "Failed"
        size = f" ({self.file_size_bytes} bytes)" if self.file_size_bytes else ""
        return f"{status}: {self.output_path}{size}"


@dataclass
class ImportResult:
    """Result of application import operation."""

    success: bool
    app_id: str
    app_version: str
    message: str | None = None
    warnings: list[str] | None = None

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{status}: {self.app_id} v{self.app_version}"


@dataclass
class DataSubmissionResult:
    """Result of form data submission operation."""

    success: bool
    record_id: str | None = None
    message: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} DataSubmission(id={self.record_id}, msg={self.message})"

    def __str__(self) -> str:
        status = "Success" if self.success else "Failed"
        id_info = f" (ID: {self.record_id})" if self.record_id else ""
        msg_info = f": {self.message}" if self.message else ""
        return f"{status}{id_info}{msg_info}"


# ============================================================================
# Utility Functions
# ============================================================================


def parse_datetime(value: str | None) -> datetime | None:
    """Parse datetime string to datetime object."""
    if not value:
        return None
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def form_info_from_dict(data: dict[str, Any]) -> FormInfo:
    """Create FormInfo from API response dictionary."""
    return FormInfo(
        form_id=data.get("id", ""),
        form_name=data.get("name", ""),
        table_name=data.get("tableName", ""),
        app_id=data.get("appId", ""),
        app_version=data.get("appVersion", "1"),
        api_endpoint=data.get("apiEndpoint"),
        api_id=data.get("apiId"),
        form_definition=data.get("json"),
    )


def application_info_from_dict(data: dict[str, Any]) -> ApplicationInfo:
    """Create ApplicationInfo from API response dictionary."""
    return ApplicationInfo(
        id=data.get("id", ""),
        name=data.get("name", ""),
        version=data.get("version", "1"),
        published=data.get("published", False),
        date_created=parse_datetime(data.get("dateCreated")),
        date_modified=parse_datetime(data.get("dateModified")),
        raw_data=data,
    )


def plugin_info_from_dict(data: dict[str, Any]) -> PluginInfo:
    """Create PluginInfo from API response dictionary."""
    return PluginInfo(
        id=data.get("id", ""),
        name=data.get("name", ""),
        version=data.get("version", ""),
        type=data.get("type", ""),
        description=data.get("description"),
        class_name=data.get("className"),
        raw_data=data,
    )


# ============================================================================
# Inventory Models
# ============================================================================


@dataclass
class InstanceInfo:
    """Information about a Joget instance from inventory.

    Used by list_instances() to provide overview of all configured instances.
    """

    name: str  # e.g., "jdx4"
    version: str  # e.g., "9.0.1"
    environment: str  # e.g., "client_alpha"
    url: str  # e.g., "http://localhost:8084/jw"
    web_port: int  # e.g., 8084
    db_port: int | None  # e.g., 3309
    status: str  # "running" | "stopped" | "unknown"
    response_time_ms: int | None = None  # HTTP response time if running

    def __str__(self):
        status_icon = "✓" if self.status == "running" else "✗" if self.status == "stopped" else "?"
        return f"{status_icon} {self.name} ({self.environment}) - {self.url} [{self.status}]"

    def is_running(self) -> bool:
        return self.status == "running"


@dataclass
class InstanceStatus:
    """Detailed status of a single Joget instance.

    Used by get_instance_status() for health checks before deployment.
    """

    name: str
    reachable: bool
    response_time_ms: int | None = None
    http_status: int | None = None
    version: str | None = None  # From API if reachable
    error: str | None = None  # Error message if not reachable
    timestamp: datetime | None = None

    def __str__(self):
        if self.reachable:
            time_info = f" ({self.response_time_ms}ms)" if self.response_time_ms else ""
            return f"✓ {self.name}: reachable{time_info}"
        else:
            return f"✗ {self.name}: {self.error or 'unreachable'}"


@dataclass
class AppSummary:
    """Summary of an application for cross-instance overview.

    Used by get_apps_overview() to compare apps across instances.
    """

    id: str
    name: str
    version: str
    published: bool

    def __str__(self):
        status = "published" if self.published else "unpublished"
        return f"{self.id} v{self.version} ({self.name}) [{status}]"


@dataclass
class AppComparison:
    """Result of comparing applications between two instances.

    Used by compare_apps() to identify differences between environments.
    """

    instance_a: str
    instance_b: str
    only_in_a: list[str] = field(default_factory=list)  # App IDs only in instance_a
    only_in_b: list[str] = field(default_factory=list)  # App IDs only in instance_b
    in_both: list[str] = field(default_factory=list)  # App IDs in both
    version_diff: dict[str, tuple[str, str]] = field(
        default_factory=dict
    )  # {app_id: (ver_a, ver_b)}

    def __str__(self):
        return (
            f"Comparison {self.instance_a} vs {self.instance_b}: "
            f"{len(self.only_in_a)} only in {self.instance_a}, "
            f"{len(self.only_in_b)} only in {self.instance_b}, "
            f"{len(self.in_both)} in both, "
            f"{len(self.version_diff)} version differences"
        )

    def has_differences(self) -> bool:
        return bool(self.only_in_a or self.only_in_b or self.version_diff)
