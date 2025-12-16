#!/usr/bin/env python3
"""
Form Discovery

Discovers forms and API endpoints in a running Joget instance.

SINGLE RESPONSIBILITY: Query Joget instance for existing forms
Does NOT: Create forms, compare, or deploy

Uses both database queries (via repositories) and API calls to discover:
- Existing forms in application
- Form definitions
- API endpoints
- Form table names

Version: 3.0.0 - Refactored to use repository pattern
"""

import logging
from typing import Any

from joget_deployment_toolkit.client import JogetClient
from joget_deployment_toolkit.database import DatabaseConnectionPool
from joget_deployment_toolkit.database.repositories import FormRepository
from joget_deployment_toolkit.models import DatabaseConfig, FormInfo


class FormDiscovery:
    """
    Discover forms in running Joget instance.

    Uses combination of:
    - Database queries via FormRepository
    - Joget API calls via JogetClient

    Version 3.0.0 - Refactored to use repository pattern for better:
    - Code reusability
    - Connection management
    - Performance (connection pooling)
    - Testability

    Example:
        >>> from joget_deployment_toolkit import JogetClient
        >>> from joget_deployment_toolkit.models import DatabaseConfig
        >>>
        >>> # Initialize client
        >>> client = JogetClient("http://localhost:8080/jw", api_key="key")
        >>>
        >>> # Initialize discovery with database config
        >>> db_config = DatabaseConfig(
        ...     host="localhost",
        ...     port=3306,
        ...     database="jwdb",
        ...     user="root",
        ...     password="password"
        ... )
        >>> discovery = FormDiscovery(client, db_config)
        >>>
        >>> # Discover all forms
        >>> forms = discovery.discover_all_forms("farmersPortal", "1")
        >>> for form in forms:
        ...     print(f"{form.form_id}: {form.form_name}")
    """

    def __init__(
        self,
        client: JogetClient,
        db_config: DatabaseConfig | dict[str, Any],
        logger: logging.Logger | None = None,
    ):
        """
        Initialize form discovery.

        Args:
            client: JogetClient instance for API calls
            db_config: Database configuration (DatabaseConfig or dict)
            logger: Optional logger instance

        Example:
            >>> # With DatabaseConfig
            >>> config = DatabaseConfig(host="localhost", user="root", password="pass")
            >>> discovery = FormDiscovery(client, config)
            >>>
            >>> # With dict (legacy)
            >>> db_config = {"host": "localhost", "user": "root", "password": "pass"}
            >>> discovery = FormDiscovery(client, db_config)
        """
        self.client = client
        self.logger = logger or logging.getLogger("joget_deployment_toolkit.discovery")

        # Handle both DatabaseConfig and dict for backward compatibility
        if isinstance(db_config, dict):
            # Convert dict to DatabaseConfig
            self.db_config = DatabaseConfig(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", 3306),
                database=db_config.get("database", "jwdb"),
                user=db_config["user"],
                password=db_config["password"],
                ssl=db_config.get("ssl", False),
            )
        else:
            self.db_config = db_config

        # Initialize connection pool and repository
        self.pool = DatabaseConnectionPool(self.db_config)
        self.form_repository = FormRepository(self.pool)

    def discover_all_forms(self, app_id: str, app_version: str = "1") -> list[FormInfo]:
        """
        Discover all forms in application.

        Uses FormRepository to query the database efficiently with
        connection pooling.

        Args:
            app_id: Application ID
            app_version: Application version (default: "1")

        Returns:
            List of FormInfo objects with form metadata and API endpoints

        Example:
            >>> forms = discovery.discover_all_forms("farmersPortal")
            >>> for form in forms:
            ...     print(f"{form.form_id}: {form.form_name}")
            ...     if form.api_endpoint:
            ...         print(f"  API: {form.api_endpoint}")
        """
        self.logger.info(f"Discovering forms in app: {app_id} v{app_version}")

        # Use repository instead of raw SQL
        forms = self.form_repository.find_by_app(app_id, app_version)

        self.logger.info(f"Found {len(forms)} forms in {app_id} v{app_version}")

        return forms

    def get_form_definition(
        self, app_id: str, app_version: str, form_id: str
    ) -> dict[str, Any] | None:
        """
        Get form JSON definition from database.

        Uses FormRepository to retrieve form definition efficiently.

        Args:
            app_id: Application ID
            app_version: Application version
            form_id: Form ID

        Returns:
            Form definition as dictionary, or None if not found

        Example:
            >>> definition = discovery.get_form_definition(
            ...     "farmersPortal", "1", "farmer_basic"
            ... )
            >>> if definition:
            ...     print(f"Form name: {definition.get('name')}")
            ...     print(f"Elements: {len(definition.get('properties', {}).get('elements', []))}")
        """
        self.logger.debug(f"Getting form definition: {app_id}/{app_version}/{form_id}")

        # Use repository instead of raw SQL
        definition = self.form_repository.get_form_definition(app_id, app_version, form_id)

        if definition:
            self.logger.debug(f"Retrieved form definition for {form_id}")
        else:
            self.logger.warning(f"Form definition not found for {form_id}")

        return definition

    def check_form_exists(self, app_id: str, app_version: str, form_id: str) -> bool:
        """
        Check if form exists in Joget instance.

        Uses FormRepository for efficient existence check.

        Args:
            app_id: Application ID
            app_version: Application version
            form_id: Form ID to check

        Returns:
            True if form exists, False otherwise

        Example:
            >>> if discovery.check_form_exists("farmersPortal", "1", "farmer_basic"):
            ...     print("Form exists")
            ... else:
            ...     print("Form not found")
        """
        try:
            # Use repository to find form
            form = self.form_repository.find_by_app_and_id(app_id, form_id, app_version)
            return form is not None

        except Exception as e:
            self.logger.debug(f"Error checking form existence: {e}")
            return False

    def check_table_exists(self, table_name: str) -> bool:
        """
        Check if database table exists for form.

        Uses FormRepository for table existence check.

        Args:
            table_name: Database table name (e.g., app_fd_maritalStatus)

        Returns:
            True if table exists, False otherwise

        Example:
            >>> if discovery.check_table_exists("app_fd_farmer_basic"):
            ...     print("Table exists")
            ...     count = discovery.get_table_row_count("app_fd_farmer_basic")
            ...     print(f"Records: {count}")
        """
        try:
            # Use repository method
            return self.form_repository.check_table_exists(table_name)

        except Exception as e:
            self.logger.debug(f"Error checking table existence: {e}")
            return False

    def get_table_row_count(self, table_name: str) -> int:
        """
        Get number of rows in a form's database table.

        Uses FormRepository for efficient row counting.

        Args:
            table_name: Database table name

        Returns:
            Number of rows in table

        Raises:
            ValueError: If table doesn't exist

        Example:
            >>> count = discovery.get_table_row_count("app_fd_farmer_basic")
            >>> print(f"Table has {count} records")
        """
        try:
            return self.form_repository.get_table_row_count(table_name)

        except ValueError:
            # Table doesn't exist
            raise

        except Exception as e:
            self.logger.error(f"Error getting table row count: {e}")
            return 0

    def find_forms_by_table(self, table_name: str) -> list[FormInfo]:
        """
        Find all forms that use a specific database table.

        Multiple forms can share the same table, so this returns a list.

        Args:
            table_name: Database table name

        Returns:
            List of FormInfo objects using this table

        Example:
            >>> forms = discovery.find_forms_by_table("app_fd_farmer_basic")
            >>> for form in forms:
            ...     print(f"{form.app_id}/{form.form_id} uses this table")
        """
        try:
            return self.form_repository.find_by_table_name(table_name)

        except Exception as e:
            self.logger.error(f"Error finding forms by table: {e}")
            return []

    def get_form_info(
        self, app_id: str, app_version: str, form_id: str, include_definition: bool = False
    ) -> FormInfo | None:
        """
        Get complete information about a form.

        Args:
            app_id: Application ID
            app_version: Application version
            form_id: Form ID
            include_definition: If True, also load form JSON definition

        Returns:
            FormInfo with complete metadata, or None if not found

        Example:
            >>> form = discovery.get_form_info(
            ...     "farmersPortal", "1", "farmer_basic",
            ...     include_definition=True
            ... )
            >>> if form:
            ...     print(f"Name: {form.form_name}")
            ...     print(f"Table: {form.table_name}")
            ...     if form.api_endpoint:
            ...         print(f"API: {form.api_endpoint}")
            ...     if form.form_definition:
            ...         print(f"Definition loaded: {len(form.form_definition)} keys")
        """
        try:
            # Get basic form info
            form = self.form_repository.find_by_app_and_id(app_id, form_id, app_version)

            if not form:
                return None

            # Optionally load definition
            if include_definition:
                definition = self.form_repository.get_form_definition(app_id, app_version, form_id)
                form.form_definition = definition

            return form

        except Exception as e:
            self.logger.error(f"Error getting form info: {e}")
            return None

    def close(self):
        """
        Close database connection pool.

        Should be called when discovery is no longer needed to free resources.

        Example:
            >>> discovery = FormDiscovery(client, db_config)
            >>> try:
            ...     forms = discovery.discover_all_forms("farmersPortal", "1")
            ... finally:
            ...     discovery.close()
        """
        if hasattr(self, "pool") and self.pool:
            self.pool.close()
            self.logger.debug("Connection pool closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection pool."""
        self.close()
