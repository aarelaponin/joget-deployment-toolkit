#!/usr/bin/env python3
"""
Configuration profiles for joget-toolkit.

Provides pre-configured profiles for different environments:
- Development (local development with debug enabled)
- Staging (pre-production testing)
- Production (production deployment with optimized settings)
- Testing (unit/integration testing)
"""

from enum import Enum
from typing import Any

from .models import (
    ClientConfig,
    DatabaseConfig,
    LogLevel,
    RetryStrategy,
)


class ProfileType(str, Enum):
    """Available configuration profiles."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# ============================================================================
# Profile Definitions
# ============================================================================

DEVELOPMENT_PROFILE: dict[str, Any] = {
    "base_url": "http://localhost:8080/jw",
    "timeout": 60,  # Longer timeout for debugging
    "verify_ssl": False,  # Local development often uses self-signed certs
    "debug": True,
    "log_level": LogLevel.DEBUG,
    "retry": {
        "enabled": True,
        "count": 2,  # Fewer retries for faster feedback
        "delay": 1.0,
        "backoff": 1.5,
        "strategy": RetryStrategy.EXPONENTIAL_BACKOFF,
    },
    "connection_pool": {"pool_connections": 5, "pool_maxsize": 5, "max_retries": 2},
    "raise_on_error": True,
    "user_agent": "joget-toolkit/2.1.0-dev",
}


STAGING_PROFILE: dict[str, Any] = {
    "timeout": 45,
    "verify_ssl": True,
    "debug": False,
    "log_level": LogLevel.INFO,
    "retry": {
        "enabled": True,
        "count": 3,
        "delay": 2.0,
        "backoff": 2.0,
        "strategy": RetryStrategy.EXPONENTIAL_BACKOFF,
    },
    "connection_pool": {"pool_connections": 10, "pool_maxsize": 10, "max_retries": 3},
    "raise_on_error": True,
    "user_agent": "joget-toolkit/2.1.0-staging",
}


PRODUCTION_PROFILE: dict[str, Any] = {
    "timeout": 30,
    "verify_ssl": True,
    "debug": False,
    "log_level": LogLevel.WARNING,  # Only warnings and errors in production
    "retry": {
        "enabled": True,
        "count": 5,  # More retries for production reliability
        "delay": 2.0,
        "backoff": 2.0,
        "strategy": RetryStrategy.EXPONENTIAL_BACKOFF,
        "max_delay": 30.0,
    },
    "connection_pool": {
        "pool_connections": 20,  # Larger pool for production load
        "pool_maxsize": 20,
        "max_retries": 5,
    },
    "raise_on_error": False,  # Don't crash on errors in production
    "user_agent": "joget-toolkit/2.1.0",
}


TESTING_PROFILE: dict[str, Any] = {
    "base_url": "http://localhost:8080/jw",
    "timeout": 10,  # Short timeout for fast tests
    "verify_ssl": False,
    "debug": False,  # Keep logs clean in tests
    "log_level": LogLevel.ERROR,  # Only log errors during tests
    "retry": {"enabled": False, "count": 0},  # No retries in tests for predictability
    "connection_pool": {"pool_connections": 2, "pool_maxsize": 2, "max_retries": 0},
    "raise_on_error": True,  # Always raise in tests
    "user_agent": "joget-toolkit/2.1.0-test",
}


# Map profile types to their configurations
PROFILE_CONFIGS: dict[ProfileType, dict[str, Any]] = {
    ProfileType.DEVELOPMENT: DEVELOPMENT_PROFILE,
    ProfileType.STAGING: STAGING_PROFILE,
    ProfileType.PRODUCTION: PRODUCTION_PROFILE,
    ProfileType.TESTING: TESTING_PROFILE,
}


# ============================================================================
# Profile Functions
# ============================================================================


def get_profile_config(
    profile: ProfileType, base_url: str | None = None, **overrides
) -> ClientConfig:
    """
    Get a pre-configured profile with optional overrides.

    Args:
        profile: Profile type to load
        base_url: Override base_url (required if not in profile)
        **overrides: Additional configuration overrides

    Returns:
        ClientConfig instance

    Example:
        >>> config = get_profile_config(
        ...     ProfileType.PRODUCTION,
        ...     base_url="https://prod.example.com/jw",
        ...     timeout=60
        ... )

    Raises:
        ValueError: If profile is unknown or required fields are missing
    """
    if profile not in PROFILE_CONFIGS:
        raise ValueError(f"Unknown profile: {profile}")

    # Get base profile configuration
    profile_data = PROFILE_CONFIGS[profile].copy()

    # Apply base_url override if provided
    if base_url:
        profile_data["base_url"] = base_url

    # Apply additional overrides
    for key, value in overrides.items():
        profile_data[key] = value

    # Create ClientConfig
    return ClientConfig(**profile_data)


def get_profile_for_url(url: str) -> ProfileType:
    """
    Suggest appropriate profile based on URL.

    Args:
        url: Joget instance URL

    Returns:
        Suggested ProfileType

    Example:
        >>> profile = get_profile_for_url("http://localhost:8080/jw")
        >>> profile
        <ProfileType.DEVELOPMENT: 'development'>
    """
    url_lower = url.lower()

    if "localhost" in url_lower or "127.0.0.1" in url_lower:
        return ProfileType.DEVELOPMENT
    elif "staging" in url_lower or "stg" in url_lower or "test" in url_lower:
        return ProfileType.STAGING
    elif "prod" in url_lower or "production" in url_lower:
        return ProfileType.PRODUCTION
    else:
        # Default to staging for unknown URLs
        return ProfileType.STAGING


def list_profiles() -> dict[ProfileType, str]:
    """
    List all available profiles with descriptions.

    Returns:
        Dictionary mapping profile types to descriptions
    """
    return {
        ProfileType.DEVELOPMENT: "Local development with debug enabled, relaxed SSL",
        ProfileType.STAGING: "Pre-production testing with moderate retry and logging",
        ProfileType.PRODUCTION: "Production deployment with optimized settings and retries",
        ProfileType.TESTING: "Unit/integration testing with minimal retries and fast timeouts",
    }


def create_custom_profile(
    name: str, base_profile: ProfileType = ProfileType.DEVELOPMENT, **overrides
) -> ClientConfig:
    """
    Create a custom profile based on an existing profile.

    Args:
        name: Custom profile name (for user_agent)
        base_profile: Base profile to start from
        **overrides: Configuration overrides

    Returns:
        ClientConfig instance

    Example:
        >>> config = create_custom_profile(
        ...     "my-custom",
        ...     base_profile=ProfileType.PRODUCTION,
        ...     timeout=120,
        ...     debug=True
        ... )
    """
    # Get base profile
    profile_data = PROFILE_CONFIGS[base_profile].copy()

    # Update user agent with custom name
    profile_data["user_agent"] = f"joget-toolkit/2.1.0-{name}"

    # Apply overrides
    for key, value in overrides.items():
        profile_data[key] = value

    return ClientConfig(**profile_data)


def merge_profiles(*profiles: ProfileType, **overrides) -> ClientConfig:
    """
    Merge multiple profiles with later profiles overriding earlier ones.

    Args:
        *profiles: Profile types to merge (in priority order)
        **overrides: Final configuration overrides

    Returns:
        ClientConfig instance

    Example:
        >>> # Start with production, override with staging retry settings
        >>> config = merge_profiles(
        ...     ProfileType.PRODUCTION,
        ...     ProfileType.STAGING,
        ...     base_url="https://my-instance.com/jw"
        ... )
    """
    if not profiles:
        raise ValueError("At least one profile must be specified")

    # Start with first profile
    merged_data = PROFILE_CONFIGS[profiles[0]].copy()

    # Merge subsequent profiles
    for profile in profiles[1:]:
        profile_data = PROFILE_CONFIGS[profile]
        merged_data.update(profile_data)

    # Apply final overrides
    merged_data.update(overrides)

    return ClientConfig(**merged_data)


# ============================================================================
# Database Profile Helpers
# ============================================================================


def get_default_database_config(
    host: str = "localhost",
    port: int = 3306,
    database: str = "jwdb",
    user: str = "root",
    password: str = "",
    profile: ProfileType = ProfileType.DEVELOPMENT,
) -> DatabaseConfig:
    """
    Get a database configuration with profile-appropriate settings.

    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password
        profile: Profile type for pool size and timeout settings

    Returns:
        DatabaseConfig instance
    """
    # Profile-specific pool sizes
    pool_sizes = {
        ProfileType.DEVELOPMENT: 3,
        ProfileType.STAGING: 5,
        ProfileType.PRODUCTION: 10,
        ProfileType.TESTING: 2,
    }

    # Profile-specific timeouts
    timeouts = {
        ProfileType.DEVELOPMENT: 30,
        ProfileType.STAGING: 20,
        ProfileType.PRODUCTION: 10,
        ProfileType.TESTING: 5,
    }

    return DatabaseConfig(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        pool_size=pool_sizes.get(profile, 5),
        connection_timeout=timeouts.get(profile, 10),
    )


__all__ = [
    "ProfileType",
    "get_profile_config",
    "get_profile_for_url",
    "list_profiles",
    "create_custom_profile",
    "merge_profiles",
    "get_default_database_config",
    "DEVELOPMENT_PROFILE",
    "STAGING_PROFILE",
    "PRODUCTION_PROFILE",
    "TESTING_PROFILE",
]
