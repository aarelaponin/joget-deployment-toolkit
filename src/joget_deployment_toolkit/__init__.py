"""
Joget Deployment Toolkit - Focused toolkit for Joget DX deployment automation

This package provides:
- JogetClient: Enhanced REST API client for Joget DX with multiple auth methods
- Authentication: Pluggable auth strategies (API Key, Session, Basic Auth)
- Exceptions: Comprehensive error handling with specific exception types
- Models: Type-safe data models for API responses and configuration
- FormDiscovery: Extract form definitions from Joget database
- Repository Pattern: Efficient database access with connection pooling
- MDM Deployment: Orchestration for Master Data Management deployment
- Inventory: Instance status checks and cross-instance app comparison

Version 1.0.0 - Initial release as focused deployment toolkit
"""

__version__ = "1.1.0"

# Core client (now from modular implementation)
# Authentication strategies
from joget_deployment_toolkit.auth import (
    APIKeyAuth,
    AuthStrategy,
    BasicAuth,
    NoAuth,
    SessionAuth,
)
from joget_deployment_toolkit.client import JogetClient

# Discovery (existing)
from joget_deployment_toolkit.discovery import FormDiscovery

# Exceptions
from joget_deployment_toolkit.exceptions import (
    AuthenticationError,
    BatchError,
    ConflictError,
    ConnectionError,
    JogetAPIError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)

# Data models
from joget_deployment_toolkit.models import (
    ApplicationDetails,
    ApplicationInfo,
    BatchResult,
    DatabaseConfig,
    DataSubmissionResult,
    DeploymentConfig,
    ExportResult,
    FormInfo,
    FormResult,
    ImportResult,
    # Configuration models
    JogetConfig,
    # Response models
    SystemInfo,
    # Inventory models
    AppComparison,
    AppSummary,
    InstanceInfo,
    InstanceStatus,
)

# Inventory functions
from joget_deployment_toolkit.inventory import (
    compare_apps,
    get_apps_overview,
    get_instance_status,
    list_instances,
)

# Operations (high-level orchestration)
from joget_deployment_toolkit.operations import (
    ComponentDeployer,
    ComponentDeploymentResult,
)

__all__ = [
    # Version
    "__version__",
    # Core client
    "JogetClient",
    # Exceptions
    "JogetAPIError",
    "ConnectionError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "ServerError",
    "TimeoutError",
    "BatchError",
    # Authentication
    "AuthStrategy",
    "APIKeyAuth",
    "SessionAuth",
    "BasicAuth",
    "NoAuth",
    # Configuration models
    "JogetConfig",
    "DatabaseConfig",
    "DeploymentConfig",
    # Response models
    "SystemInfo",
    "FormInfo",
    "FormResult",
    "ApplicationInfo",
    "ApplicationDetails",
    "BatchResult",
    "ExportResult",
    "ImportResult",
    "DataSubmissionResult",
    # Discovery
    "FormDiscovery",
    # Inventory functions
    "list_instances",
    "get_instance_status",
    "get_apps_overview",
    "compare_apps",
    # Inventory models
    "InstanceInfo",
    "InstanceStatus",
    "AppSummary",
    "AppComparison",
    # Operations
    "ComponentDeployer",
    "ComponentDeploymentResult",
]
