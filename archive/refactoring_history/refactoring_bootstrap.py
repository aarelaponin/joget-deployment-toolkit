#!/usr/bin/env python3
"""
Bootstrap script for joget-toolkit refactoring.

This script creates the new package structure and generates
skeleton files for the refactored architecture.

Usage:
    python refactoring_bootstrap.py [--dry-run]
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
import argparse

# Template for new module files
MODULE_TEMPLATES = {
    "client/__init__.py": '''"""
Joget client package.

This package contains the refactored, modular client implementation.
"""

from .base import BaseClient
from .forms import FormOperations
from .applications import ApplicationOperations
from .plugins import PluginOperations
from .health import HealthOperations

class JogetClient(
    BaseClient,
    FormOperations,
    ApplicationOperations,
    PluginOperations,
    HealthOperations
):
    """
    Main Joget client combining all operation mixins.

    Maintains backward compatibility with the original monolithic client.
    """
    pass

__all__ = ["JogetClient"]
''',

    "client/base.py": '''"""
Base client with core HTTP operations.
"""

from typing import Dict, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..auth import AuthStrategy
from ..config import ClientConfig
from ..exceptions import JogetAPIError, map_http_error


class BaseClient:
    """Base client with core HTTP operations and session management."""

    def __init__(self, config: ClientConfig, auth_strategy: AuthStrategy):
        """
        Initialize base client.

        Args:
            config: Client configuration
            auth_strategy: Authentication strategy
        """
        self.config = config
        self.auth = auth_strategy
        self.base_url = config.base_url.rstrip('/')
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create configured session with connection pooling."""
        session = requests.Session()

        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=self.config.connection_pool.pool_connections,
            pool_maxsize=self.config.connection_pool.pool_maxsize,
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        # Set default headers
        session.headers.update({
            'User-Agent': self.config.user_agent,
            **self.config.extra_headers
        })

        return session

    def _get_headers(self, api_id: Optional[str] = None) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = self.auth.get_headers()
        if api_id:
            headers['api_id'] = api_id
        return headers

    def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """
        Execute HTTP request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response object

        Raises:
            JogetAPIError: On request failure
        """
        # Implementation will be moved from current client._retry_request
        url = f"{self.base_url}{endpoint}"

        # Add authentication headers
        kwargs.setdefault('headers', {}).update(self._get_headers())

        # Set timeout
        kwargs.setdefault('timeout', self.config.timeout)

        # Execute request
        response = self.session.request(method, url, **kwargs)

        # Handle errors
        if not response.ok:
            raise map_http_error(response, endpoint)

        return response

    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
''',

    "client/forms.py": '''"""
Form-related operations for Joget client.
"""

from typing import List, Dict, Any, Optional

from ..models import FormInfo, FormResult


class FormOperations:
    """Mixin for form-related operations."""

    def list_forms(
        self,
        app_id: str,
        app_version: str = "1"
    ) -> List[FormInfo]:
        """
        List all forms in an application.

        Args:
            app_id: Application ID
            app_version: Application version

        Returns:
            List of FormInfo objects
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/forms"
        response = self.request("GET", endpoint)

        forms_data = response.json()
        return [FormInfo(**form) for form in forms_data]

    def get_form(
        self,
        app_id: str,
        form_id: str,
        app_version: str = "1"
    ) -> Dict[str, Any]:
        """
        Get form definition.

        Args:
            app_id: Application ID
            form_id: Form ID
            app_version: Application version

        Returns:
            Form definition dictionary
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}"
        response = self.request("GET", endpoint)
        return response.json()

    def create_form(
        self,
        app_id: str,
        form_definition: Dict[str, Any],
        app_version: str = "1"
    ) -> FormResult:
        """
        Create a new form.

        Args:
            app_id: Application ID
            form_definition: Form definition
            app_version: Application version

        Returns:
            FormResult object
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form"
        response = self.request("POST", endpoint, json=form_definition)

        return FormResult(
            success=response.status_code == 200,
            form_id=form_definition.get('id', ''),
            message="Form created successfully" if response.ok else "Failed to create form"
        )

    def update_form(
        self,
        app_id: str,
        form_id: str,
        form_definition: Dict[str, Any],
        app_version: str = "1"
    ) -> FormResult:
        """
        Update existing form.

        Args:
            app_id: Application ID
            form_id: Form ID
            form_definition: Updated form definition
            app_version: Application version

        Returns:
            FormResult object
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}"
        response = self.request("PUT", endpoint, json=form_definition)

        return FormResult(
            success=response.status_code == 200,
            form_id=form_id,
            message="Form updated successfully" if response.ok else "Failed to update form"
        )

    def delete_form(
        self,
        app_id: str,
        form_id: str,
        app_version: str = "1"
    ) -> bool:
        """
        Delete a form.

        Args:
            app_id: Application ID
            form_id: Form ID
            app_version: Application version

        Returns:
            True if successful
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}"
        response = self.request("DELETE", endpoint)
        return response.status_code == 200
''',

    "config/__init__.py": '''"""
Configuration management for joget-toolkit.
"""

from .models import (
    ClientConfig,
    DatabaseConfig,
    AuthConfig,
    RetryConfig,
    ConnectionPoolConfig,
    LogLevel,
    RetryStrategy
)
from .loader import ConfigurationLoader
from .profiles import ProfileType, get_profile_config

__all__ = [
    "ClientConfig",
    "DatabaseConfig",
    "AuthConfig",
    "RetryConfig",
    "ConnectionPoolConfig",
    "LogLevel",
    "RetryStrategy",
    "ConfigurationLoader",
    "ProfileType",
    "get_profile_config",
]
''',

    "database/__init__.py": '''"""
Database layer for joget-toolkit.
"""

from .connection import DatabaseConnectionPool
from .repositories import FormRepository, ApplicationRepository

__all__ = [
    "DatabaseConnectionPool",
    "FormRepository",
    "ApplicationRepository",
]
''',

    "database/connection.py": '''"""
Database connection pool management.
"""

import threading
from contextlib import contextmanager
from typing import Optional
import mysql.connector.pooling

from ..config import DatabaseConfig


class DatabaseConnectionPool:
    """Thread-safe database connection pool using singleton pattern."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config: Optional[DatabaseConfig] = None):
        """Ensure single instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize connection pool."""
        if not hasattr(self, '_initialized'):
            if config is None:
                raise ValueError("DatabaseConfig required for first initialization")

            self._pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=config.pool_name,
                pool_size=config.pool_size,
                pool_reset_session=config.pool_reset_session,
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password,
                autocommit=config.autocommit,
                use_unicode=config.use_unicode,
                charset=config.charset,
                collation=config.collation,
                connection_timeout=config.connection_timeout
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
''',

    "database/repositories/__init__.py": '''"""
Repository implementations for data access.
"""

from .base import BaseRepository
from .form_repository import FormRepository
from .application_repository import ApplicationRepository

__all__ = [
    "BaseRepository",
    "FormRepository",
    "ApplicationRepository",
]
''',

    "database/repositories/base.py": '''"""
Base repository with common database operations.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

from ..connection import DatabaseConnectionPool

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Base repository with common database operations."""

    def __init__(self, connection_pool: DatabaseConnectionPool):
        """
        Initialize repository.

        Args:
            connection_pool: Database connection pool
        """
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
'''
}

def create_directory_structure(base_path: Path, dry_run: bool = False) -> List[Path]:
    """
    Create the new directory structure.

    Args:
        base_path: Base path for the joget-toolkit source
        dry_run: If True, only print what would be created

    Returns:
        List of created directories
    """
    directories = [
        base_path / "client",
        base_path / "config",
        base_path / "database",
        base_path / "database" / "repositories",
        base_path / "database" / "models",
    ]

    created = []
    for dir_path in directories:
        if not dir_path.exists():
            if dry_run:
                print(f"[DRY RUN] Would create directory: {dir_path}")
            else:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"Created directory: {dir_path}")
            created.append(dir_path)
        else:
            print(f"Directory already exists: {dir_path}")

    return created


def create_module_files(base_path: Path, dry_run: bool = False) -> List[Tuple[Path, bool]]:
    """
    Create skeleton module files.

    Args:
        base_path: Base path for the joget-toolkit source
        dry_run: If True, only print what would be created

    Returns:
        List of (file_path, created) tuples
    """
    results = []

    for relative_path, content in MODULE_TEMPLATES.items():
        file_path = base_path / relative_path

        if file_path.exists():
            print(f"File already exists: {file_path}")
            results.append((file_path, False))
        else:
            if dry_run:
                print(f"[DRY RUN] Would create file: {file_path}")
                print(f"  First 3 lines of content:")
                lines = content.split('\n')[:3]
                for line in lines:
                    print(f"    {line}")
            else:
                file_path.write_text(content)
                print(f"Created file: {file_path}")
            results.append((file_path, True))

    return results


def create_migration_script(base_path: Path, dry_run: bool = False) -> Path:
    """
    Create a migration helper script.

    Args:
        base_path: Base path for the joget-toolkit source
        dry_run: If True, only print what would be created

    Returns:
        Path to the migration script
    """
    migration_script = '''#!/usr/bin/env python3
"""
Migration helper for updating existing code to use the new modular structure.

This script helps identify and update import statements in existing code.
"""

import re
import ast
from pathlib import Path
from typing import List, Tuple


def find_joget_imports(file_path: Path) -> List[Tuple[int, str]]:
    """Find all joget_deployment_toolkit imports in a file."""
    imports = []

    with open(file_path, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        if 'from joget_deployment_toolkit' in line or 'import joget_deployment_toolkit' in line:
            imports.append((i, line.strip()))

    return imports


def suggest_replacements(imports: List[Tuple[int, str]]) -> List[Tuple[str, str]]:
    """Suggest replacement imports for old patterns."""
    replacements = []

    for line_num, import_line in imports:
        old = import_line
        new = import_line  # Default to no change

        # Detect common patterns and suggest replacements
        if 'from joget_deployment_toolkit import JogetClient' in import_line:
            # This remains the same - backward compatible
            new = import_line + "  # No change needed - backward compatible"
        elif 'from joget_deployment_toolkit.client import JogetClient' in import_line:
            new = "from joget_deployment_toolkit import JogetClient  # Updated import path"

        replacements.append((old, new))

    return replacements


def main():
    """Main migration helper function."""
    import argparse

    parser = argparse.ArgumentParser(description="Help migrate to new joget-toolkit structure")
    parser.add_argument('path', type=Path, help="Path to scan for Python files")
    parser.add_argument('--fix', action='store_true', help="Apply fixes automatically")
    args = parser.parse_args()

    # Find all Python files
    if args.path.is_file():
        python_files = [args.path] if args.path.suffix == '.py' else []
    else:
        python_files = list(args.path.rglob('*.py'))

    print(f"Found {len(python_files)} Python files to check")

    for file_path in python_files:
        imports = find_joget_imports(file_path)
        if imports:
            print(f"\\n{file_path}:")
            replacements = suggest_replacements(imports)

            for old, new in replacements:
                if old != new:
                    print(f"  - {old}")
                    print(f"  + {new}")

            if args.fix:
                # Apply fixes
                print("  [Fixes would be applied here]")

    print("\\nMigration check complete!")


if __name__ == "__main__":
    main()
'''

    script_path = base_path.parent / "migrate_to_modular.py"

    if dry_run:
        print(f"[DRY RUN] Would create migration script: {script_path}")
    else:
        script_path.write_text(migration_script)
        script_path.chmod(0o755)  # Make executable
        print(f"Created migration script: {script_path}")

    return script_path


def create_tests_structure(base_path: Path, dry_run: bool = False) -> List[Path]:
    """
    Create test structure for new modules.

    Args:
        base_path: Base path for tests
        dry_run: If True, only print what would be created

    Returns:
        List of created test files
    """
    test_files = {
        "test_config.py": '''"""
Tests for configuration management.
"""

import pytest
from pathlib import Path
from joget_deployment_toolkit.config import ClientConfig, ConfigurationLoader, ProfileType


class TestClientConfig:
    """Test ClientConfig model."""

    def test_minimal_config(self):
        """Test minimal configuration."""
        config = ClientConfig(
            base_url="http://localhost:8080/jw",
            auth={"type": "api_key", "api_key": "test-key"}
        )
        assert config.base_url == "http://localhost:8080/jw"
        assert config.auth.api_key == "test-key"

    def test_backward_compatibility(self):
        """Test backward compatibility methods."""
        config = ClientConfig.from_kwargs(
            base_url="http://localhost:8080/jw",
            api_key="test-key",
            timeout=60
        )
        assert config.timeout == 60

        kwargs = config.to_kwargs()
        assert kwargs['api_key'] == "test-key"
        assert kwargs['timeout'] == 60


class TestConfigurationLoader:
    """Test configuration loader."""

    def test_load_from_env(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("JOGET_BASE_URL", "http://test.com/jw")
        monkeypatch.setenv("JOGET_API_KEY", "env-key")

        loader = ConfigurationLoader()
        # Would load from env
''',
        "test_database.py": '''"""
Tests for database layer.
"""

import pytest
from unittest.mock import Mock, patch
from joget_deployment_toolkit.database import DatabaseConnectionPool, FormRepository
from joget_deployment_toolkit.config import DatabaseConfig


class TestDatabaseConnectionPool:
    """Test database connection pool."""

    def test_singleton(self):
        """Test singleton pattern."""
        config = DatabaseConfig(
            host="localhost",
            user="test",
            password="test"
        )

        with patch('mysql.connector.pooling.MySQLConnectionPool'):
            pool1 = DatabaseConnectionPool(config)
            pool2 = DatabaseConnectionPool()

            assert pool1 is pool2


class TestFormRepository:
    """Test form repository."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock connection pool."""
        return Mock(spec=DatabaseConnectionPool)

    def test_find_by_id(self, mock_pool):
        """Test finding form by ID."""
        repo = FormRepository(mock_pool)

        # Mock cursor and results
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {'formId': 'test_form', 'name': 'Test Form'}
        ]

        with patch.object(repo, 'execute_query', return_value=mock_cursor.fetchall()):
            form = repo.find_by_id('test_form')

            assert form is not None
            assert form.form_id == 'test_form'
''',
        "test_refactored_client.py": '''"""
Tests for refactored client modules.
"""

import pytest
from unittest.mock import Mock, patch
from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.config import ClientConfig


class TestRefactoredClient:
    """Test the refactored modular client."""

    def test_backward_compatibility(self):
        """Test that old initialization still works."""
        with patch('joget_deployment_toolkit.client.base.BaseClient._create_session'):
            client = JogetClient(
                "http://localhost:8080/jw",
                api_key="test-key"
            )

            # All methods should still be available
            assert hasattr(client, 'list_forms')
            assert hasattr(client, 'list_applications')
            assert hasattr(client, 'test_connection')

    def test_new_initialization(self):
        """Test new initialization with config."""
        config = ClientConfig(
            base_url="http://localhost:8080/jw",
            auth={"type": "api_key", "api_key": "test-key"}
        )

        with patch('joget_deployment_toolkit.client.base.BaseClient._create_session'):
            client = JogetClient.from_config(config)

            assert client.config.base_url == "http://localhost:8080/jw"

    def test_mixins_integration(self):
        """Test that all mixins are properly integrated."""
        with patch('joget_deployment_toolkit.client.base.BaseClient._create_session'):
            client = JogetClient(
                "http://localhost:8080/jw",
                api_key="test-key"
            )

            # Check methods from each mixin
            # FormOperations
            assert callable(getattr(client, 'list_forms', None))
            assert callable(getattr(client, 'get_form', None))

            # ApplicationOperations
            assert callable(getattr(client, 'list_applications', None))
            assert callable(getattr(client, 'export_application', None))

            # HealthOperations
            assert callable(getattr(client, 'test_connection', None))
            assert callable(getattr(client, 'get_health_status', None))
'''
    }

    test_dir = base_path.parent / "tests" / "refactored"
    created = []

    if not test_dir.exists():
        if dry_run:
            print(f"[DRY RUN] Would create test directory: {test_dir}")
        else:
            test_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created test directory: {test_dir}")

    for filename, content in test_files.items():
        file_path = test_dir / filename
        if dry_run:
            print(f"[DRY RUN] Would create test file: {file_path}")
        else:
            file_path.write_text(content)
            print(f"Created test file: {file_path}")
        created.append(file_path)

    return created


def main():
    """Main bootstrap function."""
    parser = argparse.ArgumentParser(
        description="Bootstrap the joget-toolkit refactoring"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be created without actually creating files"
    )
    parser.add_argument(
        '--path',
        type=Path,
        default=Path.cwd() / "src" / "joget_deployment_toolkit",
        help="Path to joget_deployment_toolkit source directory"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Joget Toolkit Refactoring Bootstrap")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN MODE - No files will be created")
        print()

    # Verify path
    if not args.path.parent.exists():
        print(f"Error: Parent directory does not exist: {args.path.parent}")
        sys.exit(1)

    print(f"Target directory: {args.path}")
    print()

    # Create directory structure
    print("Creating directory structure...")
    create_directory_structure(args.path, args.dry_run)
    print()

    # Create module files
    print("Creating module skeleton files...")
    create_module_files(args.path, args.dry_run)
    print()

    # Create migration script
    print("Creating migration helper script...")
    create_migration_script(args.path, args.dry_run)
    print()

    # Create test structure
    print("Creating test structure...")
    create_tests_structure(args.path, args.dry_run)
    print()

    print("=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE - Review output above")
        print("Run without --dry-run to actually create files")
    else:
        print("BOOTSTRAP COMPLETE!")
        print()
        print("Next steps:")
        print("1. Review the created skeleton files")
        print("2. Start moving code from client.py to the new modules")
        print("3. Update imports to use the new structure")
        print("4. Run tests to ensure backward compatibility")
        print()
        print("Use the migration script to check existing code:")
        print("  python migrate_to_modular.py <path-to-scan>")
    print("=" * 60)


if __name__ == "__main__":
    main()