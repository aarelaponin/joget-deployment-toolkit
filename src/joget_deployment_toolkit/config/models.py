#!/usr/bin/env python3
"""
Configuration models for joget-toolkit.

Provides Pydantic v2 models for type-safe configuration management with
support for multiple sources (files, environment, profiles) and backward
compatibility with the original client interface.
"""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ============================================================================
# Enums
# ============================================================================


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RetryStrategy(str, Enum):
    """Retry strategies for failed requests."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR = "linear"
    FIXED = "fixed"


class AuthType(str, Enum):
    """Authentication types."""

    API_KEY = "api_key"
    SESSION = "session"
    BASIC = "basic"
    NONE = "none"


# ============================================================================
# Configuration Models
# ============================================================================


class RetryConfig(BaseModel):
    """Configuration for retry logic."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable retry logic")
    count: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    delay: float = Field(
        default=2.0, ge=0.1, le=60.0, description="Initial delay between retries (seconds)"
    )
    backoff: float = Field(
        default=2.0, ge=1.0, le=10.0, description="Exponential backoff multiplier"
    )
    strategy: RetryStrategy = Field(
        default=RetryStrategy.EXPONENTIAL_BACKOFF, description="Retry strategy"
    )
    max_delay: float = Field(
        default=60.0, ge=1.0, description="Maximum delay between retries (seconds)"
    )

    @field_validator("delay", "max_delay")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Ensure delay values are positive."""
        if v <= 0:
            raise ValueError("Delay must be positive")
        return v


class ConnectionPoolConfig(BaseModel):
    """Configuration for HTTP connection pooling."""

    model_config = ConfigDict(extra="forbid")

    pool_connections: int = Field(
        default=10, ge=1, le=100, description="Number of connection instances to cache"
    )
    pool_maxsize: int = Field(
        default=10, ge=1, le=100, description="Maximum number of connections to save in pool"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Number of retries for connection pool"
    )
    pool_block: bool = Field(default=False, description="Block when no free connections available")


class AuthConfig(BaseModel):
    """Configuration for authentication."""

    model_config = ConfigDict(extra="forbid")

    type: AuthType = Field(default=AuthType.NONE, description="Authentication type")
    api_key: str | None = Field(default=None, description="API key for authentication")
    username: str | None = Field(default=None, description="Username for session/basic auth")
    password: str | None = Field(
        default=None, description="Password for session/basic auth", repr=False
    )

    @model_validator(mode="after")
    def validate_auth_credentials(self) -> "AuthConfig":
        """Validate that required credentials are provided for each auth type."""
        if self.type == AuthType.API_KEY and not self.api_key:
            raise ValueError("api_key required for API_KEY authentication")
        if self.type in (AuthType.SESSION, AuthType.BASIC):
            if not self.username or not self.password:
                raise ValueError(
                    f"username and password required for {self.type.value} authentication"
                )
        return self

    def __repr__(self) -> str:
        """Safe representation that hides password."""
        return f"AuthConfig(type={self.type.value}, username={self.username or 'None'}, password={'***' if self.password else 'None'})"


class DatabaseConfig(BaseModel):
    """Configuration for MySQL database connection."""

    model_config = ConfigDict(extra="forbid")

    host: str = Field(default="localhost", description="MySQL host")
    port: int = Field(default=3306, ge=1, le=65535, description="MySQL port")
    database: str = Field(description="Database name")
    user: str = Field(description="Database user")
    password: str = Field(description="Database password", repr=False)

    # Connection pooling
    pool_name: str = Field(default="joget_pool", description="Connection pool name")
    pool_size: int = Field(default=5, ge=1, le=32, description="Connection pool size")
    pool_reset_session: bool = Field(
        default=True, description="Reset session variables on connection reuse"
    )

    # Connection options
    autocommit: bool = Field(default=True, description="Enable autocommit")
    use_unicode: bool = Field(default=True, description="Use Unicode")
    charset: str = Field(default="utf8mb4", description="Character set")
    collation: str = Field(default="utf8mb4_unicode_ci", description="Collation")
    connection_timeout: int = Field(
        default=10, ge=1, le=300, description="Connection timeout (seconds)"
    )

    # SSL
    ssl: bool = Field(default=False, description="Use SSL connection")
    ssl_ca: Path | None = Field(default=None, description="SSL CA certificate path")
    ssl_cert: Path | None = Field(default=None, description="SSL client certificate path")
    ssl_key: Path | None = Field(default=None, description="SSL client key path")

    def to_connection_string(self) -> str:
        """
        Generate MySQL connection string.

        Returns:
            Connection string in format: mysql://user:password@host:port/database
        """
        protocol = "mysql+ssl" if self.ssl else "mysql"
        return f"{protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def to_connector_params(self) -> dict[str, Any]:
        """
        Generate mysql-connector-python connection parameters.

        Returns:
            Dictionary of connection parameters
        """
        params = {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "autocommit": self.autocommit,
            "use_unicode": self.use_unicode,
            "charset": self.charset,
            "collation": self.collation,
            "connection_timeout": self.connection_timeout,
        }

        if self.ssl:
            ssl_params = {}
            if self.ssl_ca:
                ssl_params["ca"] = str(self.ssl_ca)
            if self.ssl_cert:
                ssl_params["cert"] = str(self.ssl_cert)
            if self.ssl_key:
                ssl_params["key"] = str(self.ssl_key)
            if ssl_params:
                params["ssl"] = ssl_params

        return params

    def __repr__(self) -> str:
        """Safe representation that hides password."""
        ssl_marker = "+ssl" if self.ssl else ""
        return f"DatabaseConfig({self.user}@{self.host}:{self.port}/{self.database}{ssl_marker})"


class ClientConfig(BaseModel):
    """
    Main configuration for Joget client.

    This model supports configuration from multiple sources:
    - Direct instantiation
    - YAML/JSON files
    - Environment variables
    - Configuration profiles
    """

    model_config = ConfigDict(extra="allow")  # Allow extra fields for extensibility

    # Core settings
    base_url: str = Field(description="Joget instance URL (e.g., http://localhost:8080/jw)")

    # Authentication
    auth: AuthConfig = Field(
        default_factory=lambda: AuthConfig(type=AuthType.NONE),
        description="Authentication configuration",
    )

    # Network settings
    timeout: int = Field(default=30, ge=1, le=600, description="Request timeout (seconds)")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    # Retry configuration
    retry: RetryConfig = Field(default_factory=RetryConfig, description="Retry configuration")

    # Connection pooling
    connection_pool: ConnectionPoolConfig = Field(
        default_factory=ConnectionPoolConfig, description="Connection pool configuration"
    )

    # Database (optional)
    database: DatabaseConfig | None = Field(
        default=None, description="Database configuration for discovery"
    )

    # Logging and debugging
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Advanced
    user_agent: str = Field(default="joget-toolkit/2.1.0", description="User-Agent header")
    extra_headers: dict[str, str] = Field(
        default_factory=dict, description="Additional HTTP headers"
    )
    raise_on_error: bool = Field(default=True, description="Raise exceptions on errors")

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        if not v:
            raise ValueError("base_url cannot be empty")

        # Ensure it starts with http:// or https://
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")

        # Remove trailing slash
        return v.rstrip("/")

    # ========================================================================
    # Backward Compatibility Methods

    # ========================================================================
    # Factory Methods
    # ========================================================================

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClientConfig":
        """
        Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            ClientConfig instance
        """
        return cls(**data)

    @classmethod
    def from_env(cls, prefix: str = "JOGET_") -> "ClientConfig":
        """
        Create configuration from environment variables.

        Environment variables are expected in the format:
        - JOGET_BASE_URL
        - JOGET_API_KEY
        - JOGET_TIMEOUT
        - etc.

        Args:
            prefix: Environment variable prefix

        Returns:
            ClientConfig instance

        Note:
            Full implementation will be in ConfigurationLoader
        """
        import os

        env_vars = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix) :].lower()
                env_vars[config_key] = value

        # Convert string values to appropriate types
        if "timeout" in env_vars:
            env_vars["timeout"] = int(env_vars["timeout"])
        if "debug" in env_vars:
            env_vars["debug"] = env_vars["debug"].lower() in ("true", "1", "yes")
        if "verify_ssl" in env_vars:
            env_vars["verify_ssl"] = env_vars["verify_ssl"].lower() in ("true", "1", "yes")

        # Handle auth
        auth_params = {}
        if "api_key" in env_vars:
            auth_params = {"type": AuthType.API_KEY, "api_key": env_vars.pop("api_key")}
        elif "username" in env_vars and "password" in env_vars:
            auth_params = {
                "type": AuthType.SESSION,
                "username": env_vars.pop("username"),
                "password": env_vars.pop("password"),
            }

        if auth_params:
            env_vars["auth"] = AuthConfig(**auth_params)

        return cls(**env_vars)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as dictionary
        """
        return self.model_dump(exclude_none=True, mode="python")

    def to_json(self, **kwargs) -> str:
        """
        Convert configuration to JSON string.

        Args:
            **kwargs: Additional arguments for json.dumps

        Returns:
            JSON string
        """
        return self.model_dump_json(exclude_none=True, **kwargs)


# ============================================================================
# Helper Functions
# ============================================================================


def create_auth_config(
    api_key: str | None = None, username: str | None = None, password: str | None = None
) -> AuthConfig:
    """
    Create AuthConfig from credentials (helper function).

    Args:
        api_key: API key for authentication
        username: Username for session/basic auth
        password: Password for session/basic auth

    Returns:
        AuthConfig instance
    """
    if api_key:
        return AuthConfig(type=AuthType.API_KEY, api_key=api_key)
    elif username and password:
        return AuthConfig(type=AuthType.SESSION, username=username, password=password)
    else:
        return AuthConfig(type=AuthType.NONE)


__all__ = [
    "LogLevel",
    "RetryStrategy",
    "AuthType",
    "RetryConfig",
    "ConnectionPoolConfig",
    "AuthConfig",
    "DatabaseConfig",
    "ClientConfig",
    "create_auth_config",
]
