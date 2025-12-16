"""
Shared configuration loader for Joget instances.

Loads instance configuration from the shared config file (~/.joget/instances.yaml),
which is written by sysadmin-scripts and serves as the single source of truth
for Joget instance configuration.

This module provides read-only access to the shared configuration.
"""

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def load_instances(config_file: Path | None = None) -> Dict[str, Dict[str, Any]]:
    """
    Load all instances from shared Joget config.

    Args:
        config_file: Optional path to config file. If None, uses ~/.joget/instances.yaml

    Returns:
        Dictionary of instance configurations, keyed by instance name

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid or missing 'instances' section

    Example:
        >>> instances = load_instances()
        >>> print(instances.keys())
        dict_keys(['jdx1', 'jdx2', 'jdx3', 'jdx4', 'jdx5', 'jdx6'])
    """
    if config_file is None:
        config_file = Path.home() / '.joget' / 'instances.yaml'

    if not config_file.exists():
        raise FileNotFoundError(
            f"Shared config file not found: {config_file}\n"
            f"Run 'python scripts/joget_instance_manager.py --sync-all-to-joget' "
            f"in sysadmin-scripts to create it."
        )

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file {config_file}: {e}")

    if not isinstance(config, dict) or 'instances' not in config:
        raise ValueError(
            f"Invalid config structure in {config_file}. "
            f"Expected top-level 'instances' key."
        )

    return config['instances']


def get_instance(instance_name: str, config_file: Path | None = None) -> Dict[str, Any]:
    """
    Get configuration for a specific instance.

    Args:
        instance_name: Name of instance (e.g., 'jdx4')
        config_file: Optional path to config file

    Returns:
        Instance configuration dictionary with keys:
        - url: Joget instance URL (e.g., http://localhost:8084/jw)
        - web_port: Tomcat HTTP port
        - db_host: Database host
        - db_port: Database port
        - db_name: Database name
        - username: Admin username (typically 'admin')
        - password_env: Environment variable name containing password
        - version: Joget version
        - installation_path: (optional) Path to Joget installation

    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If instance not found in config

    Example:
        >>> config = get_instance('jdx4')
        >>> print(config['url'])
        http://localhost:8084/jw
        >>> print(config['db_port'])
        3309
    """
    instances = load_instances(config_file)

    if instance_name not in instances:
        available = ', '.join(sorted(instances.keys()))
        raise KeyError(
            f"Instance '{instance_name}' not found in shared config.\n"
            f"Available instances: {available}"
        )

    instance_raw = instances[instance_name]

    # Transform nested structure to flat structure for backward compatibility
    # New format has tomcat.url, credentials.username, database.*, etc.
    # We flatten it to url, username, password_env, db_*, etc.
    config = {
        'name': instance_raw.get('name'),
        'version': instance_raw.get('version'),
        'environment': instance_raw.get('environment'),
        'description': instance_raw.get('description'),
        'installation_path': instance_raw.get('installation_path'),
    }

    # Extract Tomcat configuration
    if 'tomcat' in instance_raw:
        tomcat = instance_raw['tomcat']
        config['url'] = tomcat.get('url')
        config['web_port'] = tomcat.get('http_port')

    # Extract credentials
    if 'credentials' in instance_raw:
        creds = instance_raw['credentials']
        config['username'] = creds.get('username')
        config['password_env'] = creds.get('password_env')

    # Extract database configuration
    if 'database' in instance_raw:
        db = instance_raw['database']
        config['db_name'] = db.get('name')
        config['db_user'] = db.get('user')
        config['db_password_env'] = db.get('password_env')

        # Look up MySQL instance details if mysql_instance is specified
        mysql_instance_name = db.get('mysql_instance')
        if mysql_instance_name and config_file:
            try:
                with open(config_file, 'r') as f:
                    full_config = yaml.safe_load(f)
                    mysql_instances = full_config.get('mysql_instances', {})
                    if mysql_instance_name in mysql_instances:
                        mysql = mysql_instances[mysql_instance_name]
                        config['db_host'] = mysql.get('host', 'localhost')
                        config['db_port'] = mysql.get('port')
                        config['db_socket'] = mysql.get('socket')
            except Exception:
                # If we can't load MySQL details, use defaults
                config['db_host'] = 'localhost'
        elif mysql_instance_name:
            # Try to load from default config path
            default_config = Path.home() / '.joget' / 'instances.yaml'
            if default_config.exists():
                try:
                    with open(default_config, 'r') as f:
                        full_config = yaml.safe_load(f)
                        mysql_instances = full_config.get('mysql_instances', {})
                        if mysql_instance_name in mysql_instances:
                            mysql = mysql_instances[mysql_instance_name]
                            config['db_host'] = mysql.get('host', 'localhost')
                            config['db_port'] = mysql.get('port')
                            config['db_socket'] = mysql.get('socket')
                except Exception:
                    config['db_host'] = 'localhost'

    return config


def get_instance_password(instance_config: Dict[str, Any]) -> str | None:
    """
    Resolve password from environment variable.

    Args:
        instance_config: Instance configuration dict (from get_instance())

    Returns:
        Password from environment variable, or None if not set

    Example:
        >>> config = get_instance('jdx4')
        >>> password = get_instance_password(config)  # Reads from $JDX4_PASSWORD
    """
    password_env = instance_config.get('password_env')
    if not password_env:
        return None

    return os.getenv(password_env)


__all__ = [
    'load_instances',
    'get_instance',
    'get_instance_password',
]
