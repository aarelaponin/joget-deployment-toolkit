"""
Form repository for accessing Joget form data.

Provides database access for form-related operations including:
- Finding forms by application
- Finding forms by table name
- Getting form definitions
- Finding API endpoints
- Table existence checks
"""

import json
import logging
from typing import Any

from ...models import FormInfo
from .base import BaseRepository

logger = logging.getLogger(__name__)


class FormRepository(BaseRepository[FormInfo]):
    """
    Repository for accessing Joget form data from the database.

    This repository provides methods for querying the app_form and app_builder
    tables to discover forms, their definitions, and associated API endpoints.

    Example:
        >>> from joget_deployment_toolkit.database import DatabaseConnectionPool
        >>> from joget_deployment_toolkit.models import DatabaseConfig
        >>>
        >>> config = DatabaseConfig(
        ...     host="localhost",
        ...     port=3306,
        ...     database="jwdb",
        ...     user="root",
        ...     password="password"
        ... )
        >>> pool = DatabaseConnectionPool(config)
        >>> repo = FormRepository(pool)
        >>>
        >>> # Find all forms in an application
        >>> forms = repo.find_by_app("farmersPortal", "1")
        >>> for form in forms:
        ...     print(f"{form.form_id}: {form.form_name}")
        >>>
        >>> # Get form definition
        >>> definition = repo.get_form_definition("farmersPortal", "1", "farmer_basic")
        >>> print(definition)
    """

    # ========================================================================
    # Required Abstract Methods Implementation
    # ========================================================================

    def find_by_id(self, id: str) -> FormInfo | None:
        """
        Find form by form ID.

        Note: This searches across all applications. Use find_by_app_and_id()
        if you know the specific application.

        Args:
            id: Form ID to search for

        Returns:
            FormInfo if found, None otherwise

        Example:
            >>> form = repo.find_by_id("farmer_basic")
            >>> if form:
            ...     print(f"Found in app: {form.app_id}")
        """
        query = """
            SELECT formId, name, tableName, appId, appVersion
            FROM app_form
            WHERE formId = %s
            LIMIT 1
        """

        results = self.execute_query(query, (id,))

        if not results:
            return None

        row = results[0]
        form_info = self._row_to_form_info(row)

        # Try to find API endpoint
        api_info = self.find_api_endpoint(
            form_info.app_id, form_info.app_version, form_info.form_id
        )
        if api_info:
            form_info.api_endpoint = api_info["name"]
            form_info.api_id = api_info["id"]

        return form_info

    def find_all(self) -> list[FormInfo]:
        """
        Find all forms across all applications.

        Warning:
            This may return a large number of forms. Consider using
            find_by_app() to filter by application.

        Returns:
            List of all FormInfo objects

        Example:
            >>> all_forms = repo.find_all()
            >>> print(f"Total forms in database: {len(all_forms)}")
        """
        query = """
            SELECT formId, name, tableName, appId, appVersion
            FROM app_form
            ORDER BY appId, appVersion, name
        """

        results = self.execute_query(query)
        return [self._row_to_form_info(row) for row in results]

    def save(self, entity: FormInfo) -> FormInfo:
        """
        Save form information.

        Note: This implementation only updates metadata. For full form
        deployment, use the Joget API client.

        Args:
            entity: FormInfo to save

        Returns:
            Saved FormInfo

        Raises:
            NotImplementedError: Full form save not supported via database
        """
        raise NotImplementedError(
            "Form save via database is not supported. " "Use JogetClient for form deployment."
        )

    def delete(self, id: str) -> bool:
        """
        Delete form by ID.

        Note: This is a dangerous operation and should be used carefully.
        Consider using the Joget API for safe form deletion.

        Args:
            id: Form ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            NotImplementedError: Direct database deletion not supported
        """
        raise NotImplementedError(
            "Form deletion via database is not supported. "
            "Use JogetClient for safe form deletion."
        )

    # ========================================================================
    # Form-Specific Query Methods
    # ========================================================================

    def find_by_app(self, app_id: str, app_version: str = "1") -> list[FormInfo]:
        """
        Find all forms in a specific application.

        Args:
            app_id: Application ID
            app_version: Application version (default: "1")

        Returns:
            List of FormInfo objects for the application

        Example:
            >>> forms = repo.find_by_app("farmersPortal")
            >>> print(f"Found {len(forms)} forms")
            >>> for form in forms:
            ...     print(f"  - {form.form_name} ({form.table_name})")
        """
        query = """
            SELECT formId, name, tableName, appId, appVersion
            FROM app_form
            WHERE appId = %s AND appVersion = %s
            ORDER BY name
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Finding forms for app: {app_id} v{app_version}")

        results = self.execute_query(query, (app_id, app_version))

        forms = []
        for row in results:
            form_info = self._row_to_form_info(row)

            # Try to find associated API endpoint
            api_info = self.find_api_endpoint(app_id, app_version, form_info.form_id)
            if api_info:
                form_info.api_endpoint = api_info["name"]
                form_info.api_id = api_info["id"]

            forms.append(form_info)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Found {len(forms)} forms")

        return forms

    def find_by_app_and_id(
        self, app_id: str, form_id: str, app_version: str = "1"
    ) -> FormInfo | None:
        """
        Find a specific form in an application.

        Args:
            app_id: Application ID
            form_id: Form ID
            app_version: Application version (default: "1")

        Returns:
            FormInfo if found, None otherwise

        Example:
            >>> form = repo.find_by_app_and_id("farmersPortal", "farmer_basic")
            >>> if form:
            ...     print(f"Table: {form.table_name}")
        """
        query = """
            SELECT formId, name, tableName, appId, appVersion
            FROM app_form
            WHERE appId = %s AND appVersion = %s AND formId = %s
        """

        results = self.execute_query(query, (app_id, app_version, form_id))

        if not results:
            return None

        form_info = self._row_to_form_info(results[0])

        # Try to find API endpoint
        api_info = self.find_api_endpoint(app_id, app_version, form_id)
        if api_info:
            form_info.api_endpoint = api_info["name"]
            form_info.api_id = api_info["id"]

        return form_info

    def find_by_table_name(self, table_name: str) -> list[FormInfo]:
        """
        Find forms by database table name.

        Multiple forms can use the same table, so this returns a list.

        Args:
            table_name: Database table name

        Returns:
            List of FormInfo objects using this table

        Example:
            >>> forms = repo.find_by_table_name("app_fd_farmer_basic")
            >>> for form in forms:
            ...     print(f"{form.app_id}/{form.form_id} uses this table")
        """
        query = """
            SELECT formId, name, tableName, appId, appVersion
            FROM app_form
            WHERE tableName = %s
        """

        results = self.execute_query(query, (table_name,))
        return [self._row_to_form_info(row) for row in results]

    def get_form_definition(
        self, app_id: str, app_version: str, form_id: str
    ) -> dict[str, Any] | None:
        """
        Get form JSON definition from database.

        Retrieves the complete form definition JSON from the app_form table.

        Args:
            app_id: Application ID
            app_version: Application version
            form_id: Form ID

        Returns:
            Form definition as dictionary, or None if not found

        Example:
            >>> definition = repo.get_form_definition(
            ...     "farmersPortal", "1", "farmer_basic"
            ... )
            >>> if definition:
            ...     print(f"Form name: {definition.get('name')}")
            ...     print(f"Elements: {len(definition.get('properties', {}).get('elements', []))}")
        """
        query = """
            SELECT json
            FROM app_form
            WHERE appId = %s AND appVersion = %s AND formId = %s
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Getting form definition: {app_id}/{app_version}/{form_id}")

        results = self.execute_query(query, (app_id, app_version, form_id))

        if not results or not results[0].get("json"):
            return None

        try:
            form_json = json.loads(results[0]["json"])
            return form_json
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in form definition: {e}")
            return None

    # ========================================================================
    # API Endpoint Methods
    # ========================================================================

    def find_api_endpoint(
        self, app_id: str, app_version: str, form_id: str
    ) -> dict[str, str] | None:
        """
        Find API endpoint associated with a form.

        Searches for common API naming patterns in the app_builder table.

        Args:
            app_id: Application ID
            app_version: Application version
            form_id: Form ID

        Returns:
            Dictionary with 'id' and 'name' keys, or None if not found

        Example:
            >>> api_info = repo.find_api_endpoint("farmersPortal", "1", "farmer_basic")
            >>> if api_info:
            ...     print(f"API: {api_info['name']} (ID: {api_info['id']})")
        """
        # Common API naming patterns
        api_name_patterns = [f"api_{form_id}", form_id, f"{form_id}API", f"{form_id}_api"]

        query = """
            SELECT id, name
            FROM app_builder
            WHERE appId = %s
              AND appVersion = %s
              AND type = 'api'
              AND name = %s
        """

        for api_name in api_name_patterns:
            results = self.execute_query(query, (app_id, app_version, api_name))

            if results:
                return {"id": results[0]["id"], "name": results[0]["name"]}

        return None

    # ========================================================================
    # Table Utility Methods
    # ========================================================================

    def check_table_exists(self, table_name: str) -> bool:
        """
        Check if a database table exists.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise

        Example:
            >>> if repo.check_table_exists("app_fd_farmer_basic"):
            ...     print("Table exists")
            ... else:
            ...     print("Table not found")
        """
        query = """
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = %s
        """

        result = self.execute_scalar(query, (table_name,))
        return int(result) > 0 if result else False

    def get_table_row_count(self, table_name: str) -> int:
        """
        Get number of rows in a form's table.

        Args:
            table_name: Name of the table

        Returns:
            Number of rows in table

        Raises:
            Exception: If table doesn't exist

        Example:
            >>> count = repo.get_table_row_count("app_fd_farmer_basic")
            >>> print(f"Table has {count} records")
        """
        if not self.check_table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")

        return self.count(table_name)

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_form_info(self, row: dict[str, Any]) -> FormInfo:
        """
        Convert database row to FormInfo object.

        Args:
            row: Database row dictionary

        Returns:
            FormInfo instance
        """
        return FormInfo(
            form_id=row["formId"],
            form_name=row["name"],
            table_name=row["tableName"],
            app_id=row["appId"],
            app_version=row["appVersion"],
        )
