"""
Joget client package.

This package contains the refactored, modular client implementation.

The main JogetClient class combines all operation mixins into a single,
comprehensive API client while maintaining 100% backward compatibility
with v2.0.0.
"""

from typing import Any, Dict, Optional, Union

from ..auth import AuthStrategy
from ..config import AuthConfig, AuthType, ClientConfig
from .applications import ApplicationOperations
from .base import BaseClient
from .data import DataOperations
from .database import DatabaseOperations
from .datalists import DatalistOperations
from .forms import FormOperations
from .userviews import UserviewOperations


class JogetClient(
    BaseClient,
    FormOperations,
    DataOperations,
    ApplicationOperations,
    DatabaseOperations,
    DatalistOperations,
    UserviewOperations,
):
    """
    Main Joget DX API Client.

    Combines all operation mixins into a single, comprehensive client
    for interacting with Joget DX instances.

    The client provides operations for:
    - Forms (create, read, update, delete, batch operations)
    - Data Submission (submit records via API, batch operations)
    - Applications (list, get, export, import, batch export)
    - Datalists (list, get, create, update, delete)
    - Userviews (list, get, update, menu manipulation)

    Initialization Examples:
        >>> # Method 1: Old way (backward compatible)
        >>> client = JogetClient(
        ...     "http://localhost:8080/jw",
        ...     api_key="my-key",
        ...     timeout=60
        ... )
        >>>
        >>> # Method 2: With ClientConfig
        >>> from joget_deployment_toolkit.config import ClientConfig
        >>> config = ClientConfig(
        ...     base_url="http://localhost:8080/jw",
        ...     auth={"type": "api_key", "api_key": "my-key"},
        ...     timeout=60
        ... )
        >>> client = JogetClient(config)
        >>>
        >>> # Method 3: Using from_credentials
        >>> client = JogetClient.from_credentials(
        ...     "http://localhost:8080/jw",
        ...     "admin",
        ...     "admin"
        ... )
        >>>
        >>> # Method 4: Using from_env (loads from environment variables)
        >>> client = JogetClient.from_env()

    Usage Examples:
        >>> # Form operations
        >>> forms = client.list_forms("farmersPortal")
        >>> form_def = client.get_form("farmersPortal", "farmer_basic")
        >>>
        >>> # Application operations
        >>> apps = client.list_applications()
        >>> client.export_application("farmersPortal", "backup.zip")
        >>>
        >>> # Data submission
        >>> data = {"name": "John Doe", "email": "john@example.com"}
        >>> result = client.submit_form_data("myApp", "contactForm", data)
    """

    def __init__(self, config: ClientConfig, auth_strategy: AuthStrategy | None = None):
        """
        Initialize Joget API client.

        Args:
            config: ClientConfig instance
            auth_strategy: Optional authentication strategy

        Raises:
            TypeError: If config is not a ClientConfig instance
            ValueError: If configuration is invalid
            AuthenticationError: If authentication setup fails

        Example:
            >>> from joget_deployment_toolkit.config import ClientConfig
            >>> config = ClientConfig(
            ...     base_url="http://localhost:8080/jw",
            ...     auth={"type": "api_key", "api_key": "my-key"}
            ... )
            >>> client = JogetClient(config)
        """
        # BaseClient handles initialization
        super().__init__(config, auth_strategy)

    @classmethod
    def from_credentials(
        cls, base_url: str, username: str, password: str, **kwargs
    ) -> "JogetClient":
        """
        Create client with username/password authentication.

        Args:
            base_url: Joget instance URL
            username: Username
            password: Password
            **kwargs: Additional configuration options (timeout, verify_ssl, etc.)

        Returns:
            JogetClient instance configured with session authentication

        Example:
            >>> client = JogetClient.from_credentials(
            ...     "http://localhost:8080/jw",
            ...     "admin",
            ...     "admin",
            ...     timeout=60
            ... )
            >>> apps = client.list_applications()
        """
        auth_config = AuthConfig(type=AuthType.SESSION, username=username, password=password)

        # Extract known config parameters from kwargs
        config = ClientConfig(
            base_url=base_url,
            auth=auth_config,
            timeout=kwargs.get("timeout", 30),
            verify_ssl=kwargs.get("verify_ssl", True),
            debug=kwargs.get("debug", False),
        )
        return cls(config)

    @classmethod
    def from_config(cls, config: ClientConfig | dict[str, Any], **kwargs) -> "JogetClient":
        """
        Create client from configuration object or dictionary.

        Args:
            config: ClientConfig instance or configuration dictionary
            **kwargs: Override specific configuration values

        Returns:
            JogetClient instance

        Example:
            >>> config = ClientConfig(
            ...     base_url="http://localhost:8080/jw",
            ...     auth={"type": "api_key", "api_key": "my-key"}
            ... )
            >>> client = JogetClient.from_config(config)
            >>>
            >>> # Or from dictionary
            >>> config_dict = {
            ...     "base_url": "http://localhost:8080/jw",
            ...     "auth": {"type": "api_key", "api_key": "my-key"},
            ...     "timeout": 60
            ... }
            >>> client = JogetClient.from_config(config_dict)
        """
        if isinstance(config, dict):
            config = ClientConfig(**config)

        # Apply overrides if provided
        if kwargs:
            config = ClientConfig(**{**config.model_dump(), **kwargs})

        return cls(config)

    @classmethod
    def from_env(cls, prefix: str = "JOGET_", **kwargs) -> "JogetClient":
        """
        Create client from environment variables.

        Loads configuration from environment variables with specified prefix.
        Supported environment variables:
        - {prefix}BASE_URL: Joget instance URL
        - {prefix}API_KEY: API key for authentication
        - {prefix}USERNAME: Username for session authentication
        - {prefix}PASSWORD: Password for session authentication
        - {prefix}TIMEOUT: Request timeout in seconds
        - {prefix}DB_HOST: Database host
        - {prefix}DB_PORT: Database port
        - {prefix}DB_NAME: Database name
        - {prefix}DB_USER: Database user
        - {prefix}DB_PASSWORD: Database password
        - {prefix}LOG_LEVEL: Logging level

        Args:
            prefix: Environment variable prefix (default: "JOGET_")
            **kwargs: Override specific configuration values

        Returns:
            JogetClient instance

        Example:
            >>> # Set environment variables:
            >>> # export JOGET_BASE_URL=http://localhost:8080/jw
            >>> # export JOGET_API_KEY=my-api-key
            >>> client = JogetClient.from_env()
            >>>
            >>> # Custom prefix
            >>> client = JogetClient.from_env(prefix="MY_APP_")
        """
        config = ClientConfig.from_env(prefix)

        # Apply overrides if provided
        if kwargs:
            config = ClientConfig(**{**config.model_dump(), **kwargs})

        return cls(config)

    @classmethod
    def from_instance(cls, instance_name: str, config_file: Optional[str] = None, **kwargs) -> "JogetClient":
        """
        Create client from shared Joget instance configuration.

        Loads configuration from ~/.joget/instances.yaml (single source of truth
        managed by sysadmin-scripts).

        Args:
            instance_name: Instance name (e.g., 'jdx4', 'jdx5')
            config_file: Optional path to config file (defaults to ~/.joget/instances.yaml)
            **kwargs: Override specific configuration values

        Returns:
            JogetClient instance

        Raises:
            FileNotFoundError: If shared config file doesn't exist
            KeyError: If instance not found in config

        Example:
            >>> # Load from shared config
            >>> client = JogetClient.from_instance('jdx4')
            >>>
            >>> # Password is read from $JDX4_PASSWORD environment variable
            >>> apps = client.list_applications()
            >>>
            >>> # Custom config file
            >>> client = JogetClient.from_instance('jdx4', config_file='/path/to/config.yaml')
            >>>
            >>> # Override timeout
            >>> client = JogetClient.from_instance('jdx4', timeout=60)
        """
        from ..config.shared_loader import get_instance, get_instance_password
        from pathlib import Path

        # Load instance config from shared file
        config_path = Path(config_file) if config_file else None
        instance_config = get_instance(instance_name, config_path)

        # Get password from environment
        password = get_instance_password(instance_config)
        if not password:
            import warnings
            password_env = instance_config.get('password_env', f'{instance_name.upper()}_PASSWORD')
            warnings.warn(
                f"Password environment variable '{password_env}' not set. "
                f"Authentication may fail.",
                UserWarning
            )

        # Create auth config
        auth_config = AuthConfig(
            type=AuthType.SESSION,
            username=instance_config.get('username', 'admin'),
            password=password or ''
        )

        # Create database config if available
        db_config = None
        if 'db_host' in instance_config and 'db_port' in instance_config:
            import os
            import warnings as warn_module
            from ..models import DatabaseConfig

            # Get database password from environment if specified
            db_password = instance_config.get('db_password', '')
            db_password_env = instance_config.get('db_password_env')
            if db_password_env and not db_password:
                db_password = os.environ.get(db_password_env, '')
                if not db_password:
                    warn_module.warn(
                        f"Database password environment variable '{db_password_env}' not set",
                        UserWarning
                    )

            db_config = DatabaseConfig(
                host=instance_config.get('db_host', 'localhost'),
                port=instance_config.get('db_port', 3306),
                database=instance_config.get('db_name', 'jwdb'),
                user=instance_config.get('db_user', 'root'),
                password=db_password
            )

        # Create client config
        config = ClientConfig(
            base_url=instance_config['url'],
            auth=auth_config,
            db_config=db_config,
            timeout=kwargs.get('timeout', 30),
            verify_ssl=kwargs.get('verify_ssl', True),
            debug=kwargs.get('debug', False),
        )

        return cls(config)

    @classmethod
    def check_instance(
        cls,
        instance_name: str,
        timeout: int = 5,
    ) -> "InstanceStatus":
        """
        Quick connectivity check for a Joget instance.

        Performs an HTTP health check without creating a full client.
        Useful for validating instance availability before deployment.

        Args:
            instance_name: Instance name (e.g., 'jdx4')
            timeout: Request timeout in seconds (default: 5)

        Returns:
            InstanceStatus with reachability info

        Raises:
            KeyError: If instance not found in configuration

        Example:
            >>> status = JogetClient.check_instance('jdx4')
            >>> if status.reachable:
            ...     client = JogetClient.from_instance('jdx4')
            ...     # proceed with deployment
            ... else:
            ...     print(f"Instance down: {status.error}")
        """
        from ..inventory import get_instance_status
        from ..models import InstanceStatus

        return get_instance_status(instance_name, timeout)


__all__ = ["JogetClient"]
