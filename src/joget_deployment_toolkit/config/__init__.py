"""
Configuration management for joget-toolkit.

Provides comprehensive configuration management with:
- Type-safe configuration models (Pydantic v2)
- Multi-source loading (files, environment, profiles)
- Configuration validation
- Pre-configured environment profiles
"""

from .loader import (
    ConfigurationLoader,
    ConfigurationWriter,
)
from .models import (
    AuthConfig,
    AuthType,
    ClientConfig,
    ConnectionPoolConfig,
    DatabaseConfig,
    LogLevel,
    RetryConfig,
    RetryStrategy,
    create_auth_config,
)
from .profiles import (
    ProfileType,
    create_custom_profile,
    get_default_database_config,
    get_profile_config,
    get_profile_for_url,
    list_profiles,
    merge_profiles,
)
from .validator import (
    ConfigurationValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    validate_config,
)

__all__ = [
    # Models
    "ClientConfig",
    "DatabaseConfig",
    "AuthConfig",
    "RetryConfig",
    "ConnectionPoolConfig",
    "LogLevel",
    "RetryStrategy",
    "AuthType",
    "create_auth_config",
    # Loader
    "ConfigurationLoader",
    "ConfigurationWriter",
    # Validator
    "ConfigurationValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "validate_config",
    # Profiles
    "ProfileType",
    "get_profile_config",
    "get_profile_for_url",
    "list_profiles",
    "create_custom_profile",
    "merge_profiles",
    "get_default_database_config",
]
