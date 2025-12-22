"""
Datalist repository for accessing Joget datalist data.

Provides database access for datalist-related operations including:
- Finding datalists by application
- Finding datalists by pattern (e.g., list_md%)
- Getting datalist definitions
"""

import json
import logging
from typing import Any

from ...models import DatalistInfo
from .base import BaseRepository

logger = logging.getLogger(__name__)


class DatalistRepository(BaseRepository[DatalistInfo]):
    """
    Repository for accessing Joget datalist data from the database.

    This repository provides methods for querying the app_datalist table
    to discover datalists and their definitions.

    Example:
        >>> from joget_deployment_toolkit.database import DatabaseConnectionPool
        >>> from joget_deployment_toolkit.models import DatabaseConfig
        >>>
        >>> config = DatabaseConfig(
        ...     host="localhost",
        ...     port=3309,
        ...     database="jwdb",
        ...     user="root",
        ...     password="password"
        ... )
        >>> pool = DatabaseConnectionPool(config)
        >>> repo = DatalistRepository(pool)
        >>>
        >>> # Find all MDM datalists
        >>> datalists = repo.find_by_pattern("subsidyApplication", "list_md%")
        >>> for dl in datalists:
        ...     print(f"{dl.id}: {dl.name}")
    """

    # ========================================================================
    # Required Abstract Methods Implementation
    # ========================================================================

    def find_by_id(self, id: str) -> DatalistInfo | None:
        """
        Find datalist by datalist ID.

        Note: This searches across all applications. Use find_by_app_and_id()
        if you know the specific application.

        Args:
            id: Datalist ID to search for

        Returns:
            DatalistInfo if found, None otherwise
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_datalist
            WHERE id = %s
            LIMIT 1
        """

        results = self.execute_query(query, (id,))

        if not results:
            return None

        return self._row_to_datalist_info(results[0])

    def find_all(self) -> list[DatalistInfo]:
        """
        Find all datalists across all applications.

        Warning:
            This may return a large number of datalists. Consider using
            find_by_app() to filter by application.

        Returns:
            List of all DatalistInfo objects
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_datalist
            ORDER BY appId, appVersion, name
        """

        results = self.execute_query(query)
        return [self._row_to_datalist_info(row) for row in results]

    def save(self, entity: DatalistInfo) -> DatalistInfo:
        """
        Save datalist information.

        Note: This implementation only updates metadata. For full datalist
        deployment, use the Joget API client.

        Raises:
            NotImplementedError: Full datalist save not supported via database
        """
        raise NotImplementedError(
            "Datalist save via database is not supported. "
            "Use JogetClient for datalist deployment."
        )

    def delete(self, id: str) -> bool:
        """
        Delete datalist by ID.

        Raises:
            NotImplementedError: Direct database deletion not supported
        """
        raise NotImplementedError(
            "Datalist deletion via database is not supported. "
            "Use JogetClient for safe datalist deletion."
        )

    # ========================================================================
    # Datalist-Specific Query Methods
    # ========================================================================

    def find_by_app(self, app_id: str, app_version: str = "1") -> list[DatalistInfo]:
        """
        Find all datalists in a specific application.

        Args:
            app_id: Application ID
            app_version: Application version (default: "1")

        Returns:
            List of DatalistInfo objects for the application

        Example:
            >>> datalists = repo.find_by_app("farmersPortal")
            >>> print(f"Found {len(datalists)} datalists")
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_datalist
            WHERE appId = %s AND appVersion = %s
            ORDER BY name
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Finding datalists for app: {app_id} v{app_version}")

        results = self.execute_query(query, (app_id, app_version))
        datalists = [self._row_to_datalist_info(row) for row in results]

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Found {len(datalists)} datalists")

        return datalists

    def find_by_pattern(
        self, app_id: str, pattern: str, app_version: str = "1"
    ) -> list[DatalistInfo]:
        """
        Find datalists matching a pattern.

        Uses SQL LIKE pattern matching (% for wildcard, _ for single char).

        Args:
            app_id: Application ID
            pattern: SQL LIKE pattern (e.g., "list_md%")
            app_version: Application version (default: "1")

        Returns:
            List of matching DatalistInfo objects

        Example:
            >>> # Find all MDM datalists
            >>> datalists = repo.find_by_pattern("subsidyApplication", "list_md%")
            >>> for dl in datalists:
            ...     print(f"{dl.id}")
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_datalist
            WHERE appId = %s AND appVersion = %s AND id LIKE %s
            ORDER BY id
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Finding datalists matching pattern: {pattern}")

        results = self.execute_query(query, (app_id, app_version, pattern))
        datalists = [self._row_to_datalist_info(row) for row in results]

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Found {len(datalists)} datalists matching pattern")

        return datalists

    def find_by_app_and_id(
        self, app_id: str, datalist_id: str, app_version: str = "1"
    ) -> DatalistInfo | None:
        """
        Find a specific datalist in an application.

        Args:
            app_id: Application ID
            datalist_id: Datalist ID
            app_version: Application version (default: "1")

        Returns:
            DatalistInfo if found, None otherwise
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_datalist
            WHERE appId = %s AND appVersion = %s AND id = %s
        """

        results = self.execute_query(query, (app_id, app_version, datalist_id))

        if not results:
            return None

        return self._row_to_datalist_info(results[0])

    def get_datalist_definition(
        self, app_id: str, app_version: str, datalist_id: str
    ) -> dict[str, Any] | None:
        """
        Get datalist JSON definition from database.

        Args:
            app_id: Application ID
            app_version: Application version
            datalist_id: Datalist ID

        Returns:
            Datalist definition as dictionary, or None if not found
        """
        query = """
            SELECT json
            FROM app_datalist
            WHERE appId = %s AND appVersion = %s AND id = %s
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Getting datalist definition: {app_id}/{app_version}/{datalist_id}")

        results = self.execute_query(query, (app_id, app_version, datalist_id))

        if not results or not results[0].get("json"):
            return None

        try:
            return json.loads(results[0]["json"])
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in datalist definition: {e}")
            return None

    def copy_datalist(
        self,
        source_app_id: str,
        source_app_version: str,
        datalist_id: str,
        target_app_id: str,
        target_app_version: str = "1",
    ) -> bool:
        """
        Copy a datalist from one application to another.

        Used for cross-instance migration when direct SQL access is available.

        Args:
            source_app_id: Source application ID
            source_app_version: Source application version
            datalist_id: Datalist ID to copy
            target_app_id: Target application ID
            target_app_version: Target application version

        Returns:
            True if copied successfully, False otherwise
        """
        # Get source datalist
        source = self.find_by_app_and_id(source_app_id, datalist_id, source_app_version)
        if not source:
            self.logger.warning(f"Source datalist not found: {datalist_id}")
            return False

        # Get full definition
        definition = self.get_datalist_definition(source_app_id, source_app_version, datalist_id)
        if not definition:
            self.logger.warning(f"Could not load datalist definition: {datalist_id}")
            return False

        # Delete existing in target if present
        delete_query = """
            DELETE FROM app_datalist
            WHERE appId = %s AND appVersion = %s AND id = %s
        """
        self.execute_update(delete_query, (target_app_id, target_app_version, datalist_id))

        # Insert into target
        insert_query = """
            INSERT INTO app_datalist (appId, appVersion, id, name, description, json, dateCreated, dateModified)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        self.execute_update(
            insert_query,
            (
                target_app_id,
                target_app_version,
                datalist_id,
                source.name,
                source.description or "",
                json.dumps(definition),
            ),
        )

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Copied datalist {datalist_id} to {target_app_id}")

        return True

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_datalist_info(self, row: dict[str, Any]) -> DatalistInfo:
        """
        Convert database row to DatalistInfo object.

        Args:
            row: Database row dictionary

        Returns:
            DatalistInfo instance
        """
        json_def = None
        if row.get("json"):
            try:
                json_def = json.loads(row["json"])
            except json.JSONDecodeError:
                pass

        return DatalistInfo(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            app_id=row["appId"],
            app_version=row["appVersion"],
            json_definition=json_def,
        )
