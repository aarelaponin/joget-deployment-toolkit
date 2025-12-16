#!/usr/bin/env python3
"""
Configuration loader for joget-toolkit.

Provides multi-source configuration loading with priority:
1. Explicit configuration file
2. Environment variables
3. Profile configuration
4. Default configuration
"""

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .models import AuthType, ClientConfig


class ConfigurationLoader:
    """
    Multi-source configuration loader.

    Loads configuration from multiple sources with priority order:
    1. Explicit config file (highest priority)
    2. Environment variables
    3. Profile configuration
    4. Default values (lowest priority)
    """

    def __init__(
        self,
        config_file: str | Path | None = None,
        env_prefix: str = "JOGET_",
        load_dotenv_file: bool = True,
        dotenv_path: str | Path | None = None,
    ):
        """
        Initialize configuration loader.

        Args:
            config_file: Path to configuration file (YAML or JSON)
            env_prefix: Prefix for environment variables
            load_dotenv_file: Load .env file if present
            dotenv_path: Custom path to .env file
        """
        self.config_file = Path(config_file) if config_file else None
        self.env_prefix = env_prefix
        self.load_dotenv_file = load_dotenv_file
        self.dotenv_path = Path(dotenv_path) if dotenv_path else None

        # Load .env file if requested
        if self.load_dotenv_file:
            if self.dotenv_path and self.dotenv_path.exists():
                load_dotenv(self.dotenv_path)
            else:
                # Try to find .env in current directory or parent directories
                load_dotenv(override=False)

    def load(self) -> ClientConfig:
        """
        Load configuration from all sources.

        Priority order (later overrides earlier):
        1. Default values
        2. Profile configuration
        3. Environment variables
        4. Configuration file

        Returns:
            ClientConfig instance
        """
        # Start with empty dict
        config_data: dict[str, Any] = {}

        # 1. Load from environment variables (lowest priority after defaults)
        env_config = self._load_from_env()
        if env_config:
            config_data.update(env_config)

        # 2. Load from configuration file (highest priority)
        if self.config_file:
            file_config = self._load_from_file(self.config_file)
            if file_config:
                config_data.update(file_config)

        # Create ClientConfig
        if config_data:
            return ClientConfig(**config_data)
        else:
            # Must at least have base_url
            raise ValueError("No configuration found. Please provide base_url at minimum.")

    def _load_from_file(self, file_path: Path) -> dict[str, Any]:
        """
        Load configuration from YAML or JSON file.

        Args:
            file_path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        suffix = file_path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            with open(file_path) as f:
                data = yaml.safe_load(f)
        elif suffix == ".json":
            with open(file_path) as f:
                data = json.load(f)
        else:
            raise ValueError(
                f"Unsupported configuration file format: {suffix}. Use .yaml, .yml, or .json"
            )

        return data or {}

    def _load_from_env(self) -> dict[str, Any]:
        """
        Load configuration from environment variables.

        Environment variables are expected in the format:
        - JOGET_BASE_URL
        - JOGET_API_KEY
        - JOGET_AUTH_TYPE
        - JOGET_TIMEOUT
        - JOGET_RETRY_COUNT
        - etc.

        Returns:
            Configuration dictionary
        """
        config: dict[str, Any] = {}

        # Core settings
        if base_url := os.getenv(f"{self.env_prefix}BASE_URL"):
            config["base_url"] = base_url

        if timeout := os.getenv(f"{self.env_prefix}TIMEOUT"):
            config["timeout"] = int(timeout)

        if verify_ssl := os.getenv(f"{self.env_prefix}VERIFY_SSL"):
            config["verify_ssl"] = verify_ssl.lower() in ("true", "1", "yes")

        if debug := os.getenv(f"{self.env_prefix}DEBUG"):
            config["debug"] = debug.lower() in ("true", "1", "yes")

        # Authentication
        auth_config = self._load_auth_from_env()
        if auth_config:
            config["auth"] = auth_config

        # Retry configuration
        retry_config = self._load_retry_from_env()
        if retry_config:
            config["retry"] = retry_config

        # Database configuration
        db_config = self._load_database_from_env()
        if db_config:
            config["database"] = db_config

        # Logging
        if log_level := os.getenv(f"{self.env_prefix}LOG_LEVEL"):
            config["log_level"] = log_level.upper()

        return config

    def _load_auth_from_env(self) -> dict[str, Any] | None:
        """
        Load authentication configuration from environment variables.

        Returns:
            Authentication configuration dictionary
        """
        auth_type = os.getenv(f"{self.env_prefix}AUTH_TYPE", "").lower()

        if auth_type == "api_key" or os.getenv(f"{self.env_prefix}API_KEY"):
            return {"type": AuthType.API_KEY, "api_key": os.getenv(f"{self.env_prefix}API_KEY")}
        elif auth_type in ("session", "basic"):
            username = os.getenv(f"{self.env_prefix}USERNAME")
            password = os.getenv(f"{self.env_prefix}PASSWORD")
            if username and password:
                auth_type_enum = AuthType.SESSION if auth_type == "session" else AuthType.BASIC
                return {"type": auth_type_enum, "username": username, "password": password}

        return None

    def _load_retry_from_env(self) -> dict[str, Any] | None:
        """
        Load retry configuration from environment variables.

        Returns:
            Retry configuration dictionary
        """
        retry_config = {}

        if retry_count := os.getenv(f"{self.env_prefix}RETRY_COUNT"):
            retry_config["count"] = int(retry_count)

        if retry_delay := os.getenv(f"{self.env_prefix}RETRY_DELAY"):
            retry_config["delay"] = float(retry_delay)

        if retry_backoff := os.getenv(f"{self.env_prefix}RETRY_BACKOFF"):
            retry_config["backoff"] = float(retry_backoff)

        if retry_strategy := os.getenv(f"{self.env_prefix}RETRY_STRATEGY"):
            retry_config["strategy"] = retry_strategy.lower()

        return retry_config if retry_config else None

    def _load_database_from_env(self) -> dict[str, Any] | None:
        """
        Load database configuration from environment variables.

        Returns:
            Database configuration dictionary
        """
        # Check if database is configured
        db_host = os.getenv(f"{self.env_prefix}DB_HOST")
        db_user = os.getenv(f"{self.env_prefix}DB_USER")

        if not db_host and not db_user:
            return None

        db_config = {}

        if db_host:
            db_config["host"] = db_host

        if db_port := os.getenv(f"{self.env_prefix}DB_PORT"):
            db_config["port"] = int(db_port)

        if db_name := os.getenv(f"{self.env_prefix}DB_NAME"):
            db_config["database"] = db_name

        if db_user:
            db_config["user"] = db_user

        if db_password := os.getenv(f"{self.env_prefix}DB_PASSWORD"):
            db_config["password"] = db_password

        if db_pool_size := os.getenv(f"{self.env_prefix}DB_POOL_SIZE"):
            db_config["pool_size"] = int(db_pool_size)

        if db_ssl := os.getenv(f"{self.env_prefix}DB_SSL"):
            db_config["ssl"] = db_ssl.lower() in ("true", "1", "yes")

        return db_config if db_config else None

    @classmethod
    def from_file(cls, file_path: str | Path) -> ClientConfig:
        """
        Load configuration from file only.

        Args:
            file_path: Path to configuration file

        Returns:
            ClientConfig instance
        """
        loader = cls(config_file=file_path, load_dotenv_file=False)
        return loader.load()

    @classmethod
    def from_env(cls, env_prefix: str = "JOGET_") -> ClientConfig:
        """
        Load configuration from environment variables only.

        Args:
            env_prefix: Environment variable prefix

        Returns:
            ClientConfig instance
        """
        loader = cls(env_prefix=env_prefix, load_dotenv_file=True)
        return loader.load()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClientConfig:
        """
        Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            ClientConfig instance
        """
        return ClientConfig(**data)


class ConfigurationWriter:
    """
    Write configuration to files.

    Provides methods to save configuration to various formats.
    """

    @staticmethod
    def write_yaml(config: ClientConfig, file_path: str | Path) -> None:
        """
        Write configuration to YAML file.

        Args:
            config: ClientConfig instance
            file_path: Output file path
        """
        path = Path(file_path)
        data = config.to_dict()

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @staticmethod
    def write_json(config: ClientConfig, file_path: str | Path, indent: int = 2) -> None:
        """
        Write configuration to JSON file.

        Args:
            config: ClientConfig instance
            file_path: Output file path
            indent: JSON indentation
        """
        path = Path(file_path)
        data = config.to_dict()

        with open(path, "w") as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def write_env(
        config: ClientConfig, file_path: str | Path, prefix: str = "JOGET_"
    ) -> None:
        """
        Write configuration to .env file.

        Args:
            config: ClientConfig instance
            file_path: Output file path
            prefix: Environment variable prefix
        """
        path = Path(file_path)
        lines = []

        # Core settings
        lines.append(f"{prefix}BASE_URL={config.base_url}")
        lines.append(f"{prefix}TIMEOUT={config.timeout}")
        lines.append(f"{prefix}VERIFY_SSL={str(config.verify_ssl).lower()}")
        lines.append(f"{prefix}DEBUG={str(config.debug).lower()}")

        # Authentication
        if config.auth.type != AuthType.NONE:
            lines.append(f"{prefix}AUTH_TYPE={config.auth.type.value}")
            if config.auth.api_key:
                lines.append(f"{prefix}API_KEY={config.auth.api_key}")
            if config.auth.username:
                lines.append(f"{prefix}USERNAME={config.auth.username}")
            if config.auth.password:
                lines.append(f"{prefix}PASSWORD={config.auth.password}")

        # Retry
        lines.append(f"{prefix}RETRY_COUNT={config.retry.count}")
        lines.append(f"{prefix}RETRY_DELAY={config.retry.delay}")
        lines.append(f"{prefix}RETRY_BACKOFF={config.retry.backoff}")

        # Database
        if config.database:
            lines.append(f"{prefix}DB_HOST={config.database.host}")
            lines.append(f"{prefix}DB_PORT={config.database.port}")
            lines.append(f"{prefix}DB_NAME={config.database.database}")
            lines.append(f"{prefix}DB_USER={config.database.user}")
            lines.append(f"{prefix}DB_PASSWORD={config.database.password}")
            lines.append(f"{prefix}DB_POOL_SIZE={config.database.pool_size}")

        with open(path, "w") as f:
            f.write("\n".join(lines))
            f.write("\n")


__all__ = [
    "ConfigurationLoader",
    "ConfigurationWriter",
]
