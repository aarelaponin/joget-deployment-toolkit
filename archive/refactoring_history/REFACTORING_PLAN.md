# Joget Toolkit Code Organization Refactoring Plan

## Executive Summary

This document outlines a comprehensive plan to refactor the joget-toolkit codebase for improved maintainability, scalability, and code organization. The refactoring will focus on three main areas:

1. **Splitting the monolithic client module** into focused, single-responsibility modules
2. **Separating database operations** from business logic using a repository pattern
3. **Creating a centralized configuration system** for better settings management

**Timeline**: 3-4 weeks
**Risk Level**: Low (with backward compatibility maintained)
**Breaking Changes**: None (facade pattern ensures compatibility)

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Proposed Architecture](#proposed-architecture)
3. [Implementation Plan](#implementation-plan)
4. [Migration Strategy](#migration-strategy)
5. [Testing Strategy](#testing-strategy)
6. [Timeline and Milestones](#timeline-and-milestones)

## Current State Analysis

### Problems Identified

1. **client.py** - 1,290 lines containing:
   - HTTP operations
   - Form management
   - Application management
   - Plugin operations
   - Health monitoring
   - Authentication logic
   - Retry mechanisms

2. **discovery.py** - Mixes:
   - Database connections
   - SQL queries
   - Business logic
   - No connection pooling

3. **Configuration** - Scattered across:
   - Environment variables
   - Constructor parameters
   - Hardcoded defaults

## Proposed Architecture

### 1. Client Module Refactoring

Transform the monolithic `client.py` into a modular structure:

```
src/joget_deployment_toolkit/
├── client/
│   ├── __init__.py           # Main JogetClient facade
│   ├── base.py               # BaseClient with HTTP operations
│   ├── forms.py              # FormOperations mixin
│   ├── applications.py       # ApplicationOperations mixin
│   ├── plugins.py            # PluginOperations mixin
│   ├── health.py             # HealthOperations mixin
│   └── http_client.py        # HTTP client with retry logic
├── client.py                 # Backward compatibility wrapper
```

#### New Module Structure

**base.py** - Core HTTP client functionality
```python
from typing import Dict, Optional, Any
import requests
from ..auth import AuthStrategy
from ..config import ClientConfig

class BaseClient:
    """Base client with core HTTP operations."""

    def __init__(self, config: ClientConfig, auth_strategy: AuthStrategy):
        self.config = config
        self.auth = auth_strategy
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create configured session with connection pooling."""
        session = requests.Session()

        # Configure connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=self.config.pool_connections,
            pool_maxsize=self.config.pool_maxsize,
            max_retries=0  # We handle retries ourselves
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session

    def _get_headers(self, api_id: Optional[str] = None) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = self.auth.get_headers()
        if api_id:
            headers['api_id'] = api_id
        return headers

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Execute HTTP request with retry logic."""
        # Implementation moved from current client._retry_request
        pass
```

**forms.py** - Form-specific operations
```python
from typing import List, Dict, Any, Optional
from .base import BaseClient
from ..models import FormInfo, FormResult

class FormOperations:
    """Mixin for form-related operations."""

    def list_forms(
        self: BaseClient,
        app_id: str,
        app_version: str = "1"
    ) -> List[FormInfo]:
        """List all forms in an application."""
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/forms"
        response = self.request("GET", endpoint)
        return [FormInfo.from_dict(f) for f in response.json()]

    def get_form(
        self: BaseClient,
        app_id: str,
        form_id: str,
        app_version: str = "1"
    ) -> Dict[str, Any]:
        """Get form definition."""
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}"
        response = self.request("GET", endpoint)
        return response.json()

    def create_form(
        self: BaseClient,
        app_id: str,
        form_definition: Dict[str, Any],
        app_version: str = "1"
    ) -> FormResult:
        """Create a new form."""
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form"
        response = self.request("POST", endpoint, json=form_definition)
        return FormResult.from_response(response)

    def update_form(
        self: BaseClient,
        app_id: str,
        form_id: str,
        form_definition: Dict[str, Any],
        app_version: str = "1"
    ) -> FormResult:
        """Update existing form."""
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}"
        response = self.request("PUT", endpoint, json=form_definition)
        return FormResult.from_response(response)

    def delete_form(
        self: BaseClient,
        app_id: str,
        form_id: str,
        app_version: str = "1"
    ) -> bool:
        """Delete a form."""
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}"
        response = self.request("DELETE", endpoint)
        return response.status_code == 200
```

**applications.py** - Application management
```python
from typing import List, Optional
from pathlib import Path
from .base import BaseClient
from ..models import ApplicationInfo, ApplicationDetails, ImportResult, ExportResult

class ApplicationOperations:
    """Mixin for application-related operations."""

    def list_applications(self: BaseClient) -> List[ApplicationInfo]:
        """List all applications."""
        endpoint = "/web/json/console/apps/published"
        response = self.request("GET", endpoint)
        return [ApplicationInfo.from_dict(app) for app in response.json()]

    def get_application(
        self: BaseClient,
        app_id: str,
        version: Optional[str] = None
    ) -> ApplicationDetails:
        """Get application details."""
        endpoint = f"/web/json/console/app/{app_id}"
        if version:
            endpoint += f"/{version}"
        response = self.request("GET", endpoint)
        return ApplicationDetails.from_dict(response.json())

    def export_application(
        self: BaseClient,
        app_id: str,
        output_path: Path,
        version: Optional[str] = None
    ) -> ExportResult:
        """Export application to ZIP file."""
        # Implementation here
        pass

    def import_application(
        self: BaseClient,
        file_path: Path,
        overwrite: bool = False
    ) -> ImportResult:
        """Import application from ZIP file."""
        # Implementation here
        pass
```

**Main client facade**
```python
# client/__init__.py
from .base import BaseClient
from .forms import FormOperations
from .applications import ApplicationOperations
from .plugins import PluginOperations
from .health import HealthOperations
from ..config import ClientConfig
from ..auth import AuthStrategy, select_auth_strategy

class JogetClient(
    BaseClient,
    FormOperations,
    ApplicationOperations,
    PluginOperations,
    HealthOperations
):
    """
    Main Joget client combining all operation mixins.

    This class maintains the same interface as the original
    monolithic client for backward compatibility.
    """

    def __init__(self, base_url: str, **kwargs):
        """Initialize client with backward-compatible signature."""
        # Parse kwargs to create ClientConfig
        config = ClientConfig.from_kwargs(base_url=base_url, **kwargs)

        # Select authentication strategy
        auth_strategy = select_auth_strategy(
            api_key=kwargs.get('api_key'),
            username=kwargs.get('username'),
            password=kwargs.get('password'),
            base_url=base_url,
            auth_strategy=kwargs.get('auth_strategy')
        )

        # Initialize base client
        super().__init__(config, auth_strategy)

    @classmethod
    def from_config(cls, config: ClientConfig) -> "JogetClient":
        """Create client from configuration object."""
        return cls(config.base_url, **config.to_kwargs())
```

### 2. Database Layer Separation

Create a dedicated data access layer using the repository pattern:

```
src/joget_deployment_toolkit/
├── database/
│   ├── __init__.py
│   ├── connection.py         # Connection pool management
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py          # BaseRepository
│   │   ├── form_repository.py
│   │   └── application_repository.py
│   └── models/
│       ├── __init__.py
│       └── db_models.py      # Database-specific models
```

#### Database Connection Pool
```python
# database/connection.py
import mysql.connector.pooling
from typing import Optional, Dict, Any
from contextlib import contextmanager
import threading
from ..config import DatabaseConfig

class DatabaseConnectionPool:
    """Thread-safe database connection pool."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config: Optional[DatabaseConfig] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[DatabaseConfig] = None):
        if not hasattr(self, '_initialized'):
            if config is None:
                raise ValueError("DatabaseConfig required for first initialization")

            self._pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="joget_pool",
                pool_size=config.pool_size,
                pool_reset_session=True,
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password,
                autocommit=True
            )
            self._initialized = True

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        connection = self._pool.get_connection()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def get_cursor(self, dictionary=True, buffered=True):
        """Get a cursor with automatic connection management."""
        with self.get_connection() as connection:
            cursor = connection.cursor(dictionary=dictionary, buffered=buffered)
            try:
                yield cursor
            finally:
                cursor.close()
```

#### Repository Pattern
```python
# database/repositories/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from ..connection import DatabaseConnectionPool

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository with common database operations."""

    def __init__(self, connection_pool: DatabaseConnectionPool):
        self.pool = connection_pool

    @abstractmethod
    def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID."""
        pass

    @abstractmethod
    def find_all(self) -> List[T]:
        """Find all entities."""
        pass

    @abstractmethod
    def save(self, entity: T) -> T:
        """Save entity."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        pass

    def execute_query(self, query: str, params: tuple = None) -> List[dict]:
        """Execute a SELECT query and return results."""
        with self.pool.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an UPDATE/INSERT/DELETE query."""
        with self.pool.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.rowcount
```

#### Form Repository
```python
# database/repositories/form_repository.py
from typing import List, Optional, Dict, Any
from .base import BaseRepository
from ...models import FormInfo

class FormRepository(BaseRepository[FormInfo]):
    """Repository for form-related database operations."""

    def find_by_id(self, form_id: str) -> Optional[FormInfo]:
        """Find form by ID."""
        query = """
            SELECT formId, name, tableName, appId, appVersion
            FROM app_form
            WHERE formId = %s
            LIMIT 1
        """
        results = self.execute_query(query, (form_id,))
        if results:
            return self._map_to_form_info(results[0])
        return None

    def find_all_by_app(
        self,
        app_id: str,
        app_version: str
    ) -> List[FormInfo]:
        """Find all forms in an application."""
        query = """
            SELECT formId, name, tableName, appId, appVersion
            FROM app_form
            WHERE appId = %s AND appVersion = %s
            ORDER BY name
        """
        results = self.execute_query(query, (app_id, app_version))
        return [self._map_to_form_info(row) for row in results]

    def get_form_definition(
        self,
        app_id: str,
        app_version: str,
        form_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get form JSON definition."""
        query = """
            SELECT json
            FROM app_form
            WHERE appId = %s AND appVersion = %s AND formId = %s
        """
        results = self.execute_query(query, (app_id, app_version, form_id))
        if results and results[0]['json']:
            import json
            return json.loads(results[0]['json'])
        return None

    def check_table_exists(self, table_name: str) -> bool:
        """Check if form table exists."""
        query = """
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = %s
        """
        results = self.execute_query(query, (table_name,))
        return results[0]['count'] > 0 if results else False

    def find_api_endpoint(
        self,
        app_id: str,
        app_version: str,
        form_id: str
    ) -> Optional[Dict[str, str]]:
        """Find API endpoint for form."""
        patterns = [f"api_{form_id}", form_id, f"{form_id}API"]

        for pattern in patterns:
            query = """
                SELECT id, name
                FROM app_builder
                WHERE appId = %s
                  AND appVersion = %s
                  AND type = 'api'
                  AND name = %s
            """
            results = self.execute_query(query, (app_id, app_version, pattern))
            if results:
                return results[0]
        return None

    def _map_to_form_info(self, row: dict) -> FormInfo:
        """Map database row to FormInfo model."""
        return FormInfo(
            form_id=row['formId'],
            form_name=row['name'],
            table_name=row['tableName'],
            app_id=row['appId'],
            app_version=row['appVersion']
        )

    def save(self, entity: FormInfo) -> FormInfo:
        """Not implemented for forms (managed by Joget)."""
        raise NotImplementedError("Forms are managed through Joget API")

    def delete(self, id: str) -> bool:
        """Not implemented for forms (managed by Joget)."""
        raise NotImplementedError("Forms are managed through Joget API")

    def find_all(self) -> List[FormInfo]:
        """Find all forms across all applications."""
        query = """
            SELECT formId, name, tableName, appId, appVersion
            FROM app_form
            ORDER BY appId, appVersion, name
        """
        results = self.execute_query(query)
        return [self._map_to_form_info(row) for row in results]
```

#### Refactored Discovery Module
```python
# discovery.py - Refactored to use repository pattern
from typing import List, Optional, Dict, Any
import logging
from .database.connection import DatabaseConnectionPool
from .database.repositories.form_repository import FormRepository
from .models import FormInfo
from .client import JogetClient

class FormDiscovery:
    """
    Service for discovering forms in Joget instance.
    Now uses repository pattern for data access.
    """

    def __init__(
        self,
        client: JogetClient,
        db_config: Dict[str, Any],
        logger: Optional[logging.Logger] = None
    ):
        self.client = client
        self.logger = logger or logging.getLogger('joget_deployment_toolkit.discovery')

        # Initialize database connection pool
        from .config import DatabaseConfig
        config = DatabaseConfig(**db_config)
        self.connection_pool = DatabaseConnectionPool(config)
        self.form_repository = FormRepository(self.connection_pool)

    def discover_all_forms(
        self,
        app_id: str,
        app_version: str
    ) -> List[FormInfo]:
        """
        Discover all forms in application.
        Business logic separated from data access.
        """
        self.logger.info(f"Discovering forms in app: {app_id} v{app_version}")

        # Get forms from repository
        forms = self.form_repository.find_all_by_app(app_id, app_version)

        # Enrich with API endpoints
        for form in forms:
            api_info = self.form_repository.find_api_endpoint(
                app_id, app_version, form.form_id
            )
            if api_info:
                form.api_endpoint = api_info['name']
                form.api_id = api_info['id']

        self.logger.info(f"Found {len(forms)} forms")
        return forms

    def get_form_definition(
        self,
        app_id: str,
        app_version: str,
        form_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get form definition with validation."""
        return self.form_repository.get_form_definition(
            app_id, app_version, form_id
        )

    def check_form_exists(
        self,
        app_id: str,
        app_version: str,
        form_id: str
    ) -> bool:
        """Check if form exists."""
        form = self.form_repository.find_by_id(form_id)
        if form:
            return form.app_id == app_id and form.app_version == app_version
        return False

    def check_table_exists(self, table_name: str) -> bool:
        """Check if database table exists."""
        return self.form_repository.check_table_exists(table_name)
```

### 3. Centralized Configuration System

Create a comprehensive configuration management system:

```
src/joget_deployment_toolkit/
├── config/
│   ├── __init__.py
│   ├── models.py             # Configuration models
│   ├── loader.py             # Configuration loaders
│   ├── validator.py          # Configuration validation
│   └── profiles.py           # Configuration profiles
```

#### Configuration Models
```python
# config/models.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from enum import Enum

class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class RetryStrategy(str, Enum):
    """Retry strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"

class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""
    pool_connections: int = Field(10, ge=1, le=100)
    pool_maxsize: int = Field(10, ge=1, le=100)
    pool_block: bool = Field(False)

class RetryConfig(BaseModel):
    """Retry configuration."""
    enabled: bool = Field(True)
    max_retries: int = Field(3, ge=0, le=10)
    initial_delay: float = Field(1.0, ge=0.1, le=60)
    max_delay: float = Field(60.0, ge=1, le=300)
    backoff_factor: float = Field(2.0, ge=1, le=10)
    strategy: RetryStrategy = Field(RetryStrategy.EXPONENTIAL)
    retry_on_status: list[int] = Field(default_factory=lambda: [500, 502, 503, 504])

class AuthConfig(BaseModel):
    """Authentication configuration."""
    type: str = Field(..., description="Auth type: api_key, session, basic, none")
    api_key: Optional[str] = Field(None, description="API key")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")
    default_api_id: Optional[str] = Field(None, description="Default API ID")

    @validator('type')
    def validate_type(cls, v):
        valid_types = ['api_key', 'session', 'basic', 'none']
        if v not in valid_types:
            raise ValueError(f"Auth type must be one of {valid_types}")
        return v

class DatabaseConfig(BaseModel):
    """Enhanced database configuration."""
    host: str = Field("localhost")
    port: int = Field(3306)
    database: str = Field("jwdb")
    user: str = Field(...)
    password: str = Field(...)

    # Connection pool settings
    pool_size: int = Field(5, ge=1, le=20)
    pool_name: str = Field("joget_pool")
    pool_reset_session: bool = Field(True)

    # Connection settings
    autocommit: bool = Field(True)
    use_unicode: bool = Field(True)
    charset: str = Field("utf8mb4")
    collation: str = Field("utf8mb4_unicode_ci")

    # SSL settings
    ssl_enabled: bool = Field(False)
    ssl_ca: Optional[str] = Field(None)
    ssl_cert: Optional[str] = Field(None)
    ssl_key: Optional[str] = Field(None)

    # Timeouts
    connection_timeout: int = Field(10)

    class Config:
        json_encoders = {
            str: lambda v: "***" if "password" in v.lower() else v
        }

class ClientConfig(BaseModel):
    """Complete client configuration."""
    # Core settings
    base_url: str = Field(..., description="Joget instance URL")
    timeout: int = Field(30, ge=1, le=300)
    verify_ssl: bool = Field(True)

    # Sub-configurations
    auth: AuthConfig
    retry: RetryConfig = Field(default_factory=RetryConfig)
    connection_pool: ConnectionPoolConfig = Field(default_factory=ConnectionPoolConfig)
    database: Optional[DatabaseConfig] = None

    # Logging
    log_level: LogLevel = Field(LogLevel.INFO)
    log_requests: bool = Field(False)
    log_responses: bool = Field(False)

    # Advanced
    user_agent: str = Field("JogetToolkit/2.1.0")
    extra_headers: Dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_kwargs(cls, base_url: str, **kwargs) -> "ClientConfig":
        """Create config from legacy kwargs (backward compatibility)."""
        # Map old parameters to new structure
        auth_config = AuthConfig(
            type='api_key' if kwargs.get('api_key') else 'session',
            api_key=kwargs.get('api_key'),
            username=kwargs.get('username'),
            password=kwargs.get('password')
        )

        retry_config = RetryConfig(
            max_retries=kwargs.get('retry_count', 3),
            initial_delay=kwargs.get('retry_delay', 2.0),
            backoff_factor=kwargs.get('retry_backoff', 2.0)
        )

        return cls(
            base_url=base_url,
            timeout=kwargs.get('timeout', 30),
            verify_ssl=kwargs.get('verify_ssl', True),
            auth=auth_config,
            retry=retry_config,
            log_level=LogLevel.DEBUG if kwargs.get('debug') else LogLevel.INFO
        )

    def to_kwargs(self) -> Dict[str, Any]:
        """Convert to legacy kwargs (backward compatibility)."""
        return {
            'api_key': self.auth.api_key,
            'username': self.auth.username,
            'password': self.auth.password,
            'timeout': self.timeout,
            'retry_count': self.retry.max_retries,
            'retry_delay': self.retry.initial_delay,
            'retry_backoff': self.retry.backoff_factor,
            'verify_ssl': self.verify_ssl,
            'debug': self.log_level == LogLevel.DEBUG
        }
```

#### Configuration Loader
```python
# config/loader.py
import os
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from .models import ClientConfig, DatabaseConfig, AuthConfig

class ConfigurationLoader:
    """Load configuration from multiple sources."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".joget-toolkit"
        self.config_dir.mkdir(exist_ok=True)

        # Load environment variables
        load_dotenv()

    def load_config(
        self,
        profile: str = "default",
        config_file: Optional[Path] = None
    ) -> ClientConfig:
        """
        Load configuration with priority:
        1. Explicit config_file
        2. Environment variables
        3. Profile configuration
        4. Default configuration
        """
        config_dict = {}

        # Load default configuration
        default_file = self.config_dir / "config.yaml"
        if default_file.exists():
            config_dict = self._load_yaml(default_file)

        # Load profile configuration
        profile_file = self.config_dir / f"config.{profile}.yaml"
        if profile_file.exists():
            profile_config = self._load_yaml(profile_file)
            config_dict = self._merge_configs(config_dict, profile_config)

        # Load explicit config file
        if config_file:
            explicit_config = self._load_file(config_file)
            config_dict = self._merge_configs(config_dict, explicit_config)

        # Override with environment variables
        env_config = self._load_from_env()
        config_dict = self._merge_configs(config_dict, env_config)

        # Create and validate configuration
        return ClientConfig(**config_dict)

    def _load_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        if file_path.suffix == '.yaml' or file_path.suffix == '.yml':
            return self._load_yaml(file_path)
        elif file_path.suffix == '.json':
            return self._load_json(file_path)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")

    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration."""
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON configuration."""
        with open(file_path, 'r') as f:
            return json.load(f)

    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        # Base URL
        if base_url := os.getenv('JOGET_BASE_URL'):
            config['base_url'] = base_url

        # Authentication
        auth = {}
        if api_key := os.getenv('JOGET_API_KEY'):
            auth['type'] = 'api_key'
            auth['api_key'] = api_key
        elif username := os.getenv('JOGET_USERNAME'):
            auth['type'] = 'session'
            auth['username'] = username
            auth['password'] = os.getenv('JOGET_PASSWORD')

        if auth:
            config['auth'] = auth

        # Database
        if db_host := os.getenv('JOGET_DB_HOST'):
            config['database'] = {
                'host': db_host,
                'port': int(os.getenv('JOGET_DB_PORT', '3306')),
                'database': os.getenv('JOGET_DB_NAME', 'jwdb'),
                'user': os.getenv('JOGET_DB_USER'),
                'password': os.getenv('JOGET_DB_PASSWORD')
            }

        # Other settings
        if timeout := os.getenv('JOGET_TIMEOUT'):
            config['timeout'] = int(timeout)

        if log_level := os.getenv('JOGET_LOG_LEVEL'):
            config['log_level'] = log_level

        return config

    def _merge_configs(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def save_config(
        self,
        config: ClientConfig,
        profile: str = "default",
        exclude_secrets: bool = True
    ):
        """Save configuration to file."""
        file_path = self.config_dir / f"config.{profile}.yaml"

        config_dict = config.dict(exclude_unset=True)

        if exclude_secrets:
            # Remove sensitive information
            if 'auth' in config_dict:
                config_dict['auth'].pop('password', None)
                config_dict['auth'].pop('api_key', None)
            if 'database' in config_dict:
                config_dict['database'].pop('password', None)

        with open(file_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
```

#### Configuration Profiles
```python
# config/profiles.py
from enum import Enum
from .models import ClientConfig, AuthConfig, RetryConfig, LogLevel

class ProfileType(str, Enum):
    """Predefined configuration profiles."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

def get_profile_config(profile: ProfileType) -> ClientConfig:
    """Get predefined configuration for a profile."""

    if profile == ProfileType.DEVELOPMENT:
        return ClientConfig(
            base_url="http://localhost:8080/jw",
            timeout=60,
            verify_ssl=False,
            auth=AuthConfig(type="session", username="admin", password="admin"),
            retry=RetryConfig(max_retries=1, initial_delay=0.5),
            log_level=LogLevel.DEBUG,
            log_requests=True,
            log_responses=True
        )

    elif profile == ProfileType.PRODUCTION:
        return ClientConfig(
            base_url="https://joget.production.com/jw",
            timeout=30,
            verify_ssl=True,
            auth=AuthConfig(type="api_key"),  # Must be provided via env
            retry=RetryConfig(
                max_retries=5,
                initial_delay=2.0,
                max_delay=120,
                backoff_factor=2.0
            ),
            log_level=LogLevel.WARNING,
            log_requests=False,
            log_responses=False
        )

    elif profile == ProfileType.TESTING:
        return ClientConfig(
            base_url="http://localhost:8080/jw",
            timeout=5,
            verify_ssl=False,
            auth=AuthConfig(type="none"),
            retry=RetryConfig(enabled=False),
            log_level=LogLevel.ERROR
        )

    else:  # STAGING
        return ClientConfig(
            base_url="https://joget.staging.com/jw",
            timeout=45,
            verify_ssl=True,
            auth=AuthConfig(type="api_key"),
            retry=RetryConfig(max_retries=3, initial_delay=1.0),
            log_level=LogLevel.INFO
        )
```

## Implementation Plan

### Phase 1: Foundation (Week 1)

1. **Create new package structure**
   - Create directories: `client/`, `database/`, `config/`
   - Set up `__init__.py` files
   - Configure imports

2. **Implement configuration system**
   - Create configuration models
   - Implement configuration loader
   - Add configuration profiles
   - Write configuration tests

3. **Set up database layer**
   - Implement connection pool
   - Create base repository
   - Write repository tests

### Phase 2: Client Refactoring (Week 2)

1. **Extract base client**
   - Move HTTP operations to `base.py`
   - Implement retry logic in `http_client.py`
   - Create session management

2. **Create operation mixins**
   - Extract form operations to `forms.py`
   - Extract application operations to `applications.py`
   - Extract plugin operations to `plugins.py`
   - Extract health operations to `health.py`

3. **Create facade client**
   - Implement main `JogetClient` class
   - Ensure backward compatibility
   - Add deprecation warnings for old patterns

### Phase 3: Database Refactoring (Week 3)

1. **Implement repositories**
   - Create `FormRepository`
   - Create `ApplicationRepository`
   - Add repository tests

2. **Refactor discovery module**
   - Update to use repositories
   - Separate business logic from data access
   - Update tests

3. **Add connection management**
   - Implement proper connection pooling
   - Add connection health checks
   - Add retry logic for database operations

### Phase 4: Integration & Testing (Week 4)

1. **Integration testing**
   - Test backward compatibility
   - Test new modular structure
   - Performance testing

2. **Documentation**
   - Update API documentation
   - Create migration guide
   - Add configuration examples

3. **Migration tools**
   - Create automated migration script
   - Add compatibility layer warnings
   - Create upgrade guide

## Migration Strategy

### Backward Compatibility

1. **Maintain existing API**
   ```python
   # Old code continues to work
   from joget_deployment_toolkit import JogetClient
   client = JogetClient("http://localhost:8080/jw", api_key="key")
   forms = client.list_forms("app", "1")
   ```

2. **Add deprecation warnings**
   ```python
   import warnings

   def old_method(self, *args, **kwargs):
       warnings.warn(
           "This method is deprecated. Use new_method() instead.",
           DeprecationWarning,
           stacklevel=2
       )
       return self.new_method(*args, **kwargs)
   ```

3. **Provide migration path**
   ```python
   # New recommended approach
   from joget_deployment_toolkit.config import ClientConfig, ConfigurationLoader
   from joget_deployment_toolkit import JogetClient

   # Load configuration
   loader = ConfigurationLoader()
   config = loader.load_config(profile="production")

   # Create client
   client = JogetClient.from_config(config)
   ```

### Version Strategy

- **2.1.0**: Add new modular structure alongside existing code
- **2.2.0**: Mark old patterns as deprecated
- **3.0.0**: Remove deprecated code (6 months later)

## Testing Strategy

### Unit Tests

```python
# tests/test_config.py
import pytest
from joget_deployment_toolkit.config import ClientConfig, ConfigurationLoader

def test_config_from_dict():
    """Test configuration creation from dictionary."""
    config_dict = {
        "base_url": "http://localhost:8080/jw",
        "auth": {"type": "api_key", "api_key": "test-key"},
        "timeout": 30
    }
    config = ClientConfig(**config_dict)
    assert config.base_url == "http://localhost:8080/jw"
    assert config.auth.api_key == "test-key"

def test_config_validation():
    """Test configuration validation."""
    with pytest.raises(ValueError):
        ClientConfig(base_url="invalid-url", auth={"type": "invalid"})

def test_backward_compatibility():
    """Test backward compatibility with old constructor."""
    from joget_deployment_toolkit import JogetClient
    client = JogetClient("http://localhost:8080/jw", api_key="key")
    assert client.base_url == "http://localhost:8080/jw"
```

### Integration Tests

```python
# tests/integration/test_refactored_client.py
import pytest
from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.config import ClientConfig, ProfileType, get_profile_config

@pytest.fixture
def test_client():
    """Create test client with test profile."""
    config = get_profile_config(ProfileType.TESTING)
    return JogetClient.from_config(config)

def test_modular_client_operations(test_client):
    """Test that modular client maintains all operations."""
    # Test form operations
    assert hasattr(test_client, 'list_forms')
    assert hasattr(test_client, 'get_form')

    # Test application operations
    assert hasattr(test_client, 'list_applications')
    assert hasattr(test_client, 'export_application')

    # Test health operations
    assert hasattr(test_client, 'test_connection')
    assert hasattr(test_client, 'get_health_status')
```

### Performance Tests

```python
# tests/performance/test_connection_pool.py
import time
import concurrent.futures
from joget_deployment_toolkit.database import DatabaseConnectionPool

def test_connection_pool_performance():
    """Test connection pool performance under load."""
    pool = DatabaseConnectionPool(config)

    def execute_query():
        with pool.get_cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone()

    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(execute_query) for _ in range(100)]
        results = [f.result() for f in futures]
    elapsed = time.time() - start

    assert elapsed < 5.0  # Should complete in under 5 seconds
    assert len(results) == 100
```

## Timeline and Milestones

### Week 1: Foundation
- [ ] Set up package structure
- [ ] Implement configuration system
- [ ] Create database connection pool
- [ ] Write foundation tests

### Week 2: Client Refactoring
- [ ] Extract base client
- [ ] Create operation mixins
- [ ] Implement facade pattern
- [ ] Ensure backward compatibility

### Week 3: Database Layer
- [ ] Implement repositories
- [ ] Refactor discovery module
- [ ] Add connection management
- [ ] Update tests

### Week 4: Integration
- [ ] Complete integration testing
- [ ] Update documentation
- [ ] Create migration tools
- [ ] Performance validation

## Success Metrics

1. **Code Quality**
   - Reduce client.py from 1,290 lines to <200 lines
   - Each module <400 lines
   - Cyclomatic complexity <10 per method

2. **Performance**
   - Connection pool reduces database overhead by 50%
   - Configuration loading <100ms
   - No performance regression in existing operations

3. **Maintainability**
   - 100% backward compatibility
   - Test coverage remains >70%
   - Clear separation of concerns

4. **Developer Experience**
   - Configuration from multiple sources
   - Better error messages
   - Improved debugging capabilities

## Risk Management

### Risks and Mitigations

1. **Breaking Changes**
   - Risk: Existing code breaks
   - Mitigation: Facade pattern, extensive testing, gradual migration

2. **Performance Regression**
   - Risk: New structure adds overhead
   - Mitigation: Performance benchmarks, profiling, optimization

3. **Complex Migration**
   - Risk: Users struggle to migrate
   - Mitigation: Clear documentation, migration tools, support period

## Appendix

### Example Configuration Files

**config.yaml**
```yaml
base_url: http://localhost:8080/jw
timeout: 30
verify_ssl: false

auth:
  type: api_key
  api_key: ${JOGET_API_KEY}  # Environment variable reference

retry:
  max_retries: 3
  initial_delay: 1.0
  strategy: exponential

database:
  host: localhost
  port: 3306
  database: jwdb
  user: root
  password: ${JOGET_DB_PASSWORD}
  pool_size: 5

log_level: INFO
```

**config.production.yaml**
```yaml
base_url: https://joget.company.com/jw
verify_ssl: true

auth:
  type: api_key
  # API key from environment variable

retry:
  max_retries: 5
  max_delay: 120

connection_pool:
  pool_connections: 20
  pool_maxsize: 20

log_level: WARNING
```

### Usage Examples

**Simple Usage (Backward Compatible)**
```python
from joget_deployment_toolkit import JogetClient

# Works exactly as before
client = JogetClient("http://localhost:8080/jw", api_key="key")
forms = client.list_forms("app", "1")
```

**Modern Usage with Configuration**
```python
from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.config import ConfigurationLoader

# Load configuration from file/env
loader = ConfigurationLoader()
config = loader.load_config(profile="production")

# Create client
client = JogetClient.from_config(config)

# Use client
forms = client.list_forms("app", "1")
```

**Direct Module Usage**
```python
from joget_deployment_toolkit.client.forms import FormOperations
from joget_deployment_toolkit.client.base import BaseClient
from joget_deployment_toolkit.config import ClientConfig

# Create specialized client
config = ClientConfig(...)
base_client = BaseClient(config, auth_strategy)
form_ops = FormOperations()

# Use specific operations
forms = form_ops.list_forms(base_client, "app", "1")
```

This comprehensive plan provides a clear roadmap for refactoring the joget-toolkit codebase with improved organization, maintainability, and scalability while ensuring backward compatibility.