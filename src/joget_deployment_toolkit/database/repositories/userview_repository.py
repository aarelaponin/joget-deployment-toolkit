"""
Userview repository for accessing Joget userview data.

Provides database access for userview-related operations including:
- Finding userviews by application
- Getting userview definitions
- Parsing/updating userview JSON structure
- Category and menu operations
"""

import json
import logging
from typing import Any

from ...models import UserviewInfo
from .base import BaseRepository

logger = logging.getLogger(__name__)


class UserviewRepository(BaseRepository[UserviewInfo]):
    """
    Repository for accessing Joget userview data from the database.

    This repository provides methods for querying the app_userview table
    to discover userviews and their definitions.

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
        >>> repo = UserviewRepository(pool)
        >>>
        >>> # Get userview with Master Data category
        >>> userview = repo.find_by_app_and_id("farmersPortal", "v")
        >>> if userview:
        ...     print(f"Found: {userview.name}")
    """

    # ========================================================================
    # Required Abstract Methods Implementation
    # ========================================================================

    def find_by_id(self, id: str) -> UserviewInfo | None:
        """
        Find userview by userview ID.

        Note: This searches across all applications. Use find_by_app_and_id()
        if you know the specific application.

        Args:
            id: Userview ID to search for

        Returns:
            UserviewInfo if found, None otherwise
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_userview
            WHERE id = %s
            LIMIT 1
        """

        results = self.execute_query(query, (id,))

        if not results:
            return None

        return self._row_to_userview_info(results[0])

    def find_all(self) -> list[UserviewInfo]:
        """
        Find all userviews across all applications.

        Returns:
            List of all UserviewInfo objects
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_userview
            ORDER BY appId, appVersion, name
        """

        results = self.execute_query(query)
        return [self._row_to_userview_info(row) for row in results]

    def save(self, entity: UserviewInfo) -> UserviewInfo:
        """
        Save userview information.

        Raises:
            NotImplementedError: Full userview save not supported via database
        """
        raise NotImplementedError(
            "Userview save via database is not supported. "
            "Use JogetClient for userview deployment."
        )

    def delete(self, id: str) -> bool:
        """
        Delete userview by ID.

        Raises:
            NotImplementedError: Direct database deletion not supported
        """
        raise NotImplementedError(
            "Userview deletion via database is not supported. "
            "Use JogetClient for safe userview deletion."
        )

    # ========================================================================
    # Userview-Specific Query Methods
    # ========================================================================

    def find_by_app(self, app_id: str, app_version: str = "1") -> list[UserviewInfo]:
        """
        Find all userviews in a specific application.

        Args:
            app_id: Application ID
            app_version: Application version (default: "1")

        Returns:
            List of UserviewInfo objects for the application

        Example:
            >>> userviews = repo.find_by_app("farmersPortal")
            >>> for uv in userviews:
            ...     print(f"{uv.id}: {uv.name}")
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_userview
            WHERE appId = %s AND appVersion = %s
            ORDER BY name
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Finding userviews for app: {app_id} v{app_version}")

        results = self.execute_query(query, (app_id, app_version))
        userviews = [self._row_to_userview_info(row) for row in results]

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Found {len(userviews)} userviews")

        return userviews

    def find_by_app_and_id(
        self, app_id: str, userview_id: str, app_version: str = "1"
    ) -> UserviewInfo | None:
        """
        Find a specific userview in an application.

        Args:
            app_id: Application ID
            userview_id: Userview ID
            app_version: Application version (default: "1")

        Returns:
            UserviewInfo if found, None otherwise
        """
        query = """
            SELECT id, name, description, appId, appVersion, json
            FROM app_userview
            WHERE appId = %s AND appVersion = %s AND id = %s
        """

        results = self.execute_query(query, (app_id, app_version, userview_id))

        if not results:
            return None

        return self._row_to_userview_info(results[0])

    def get_userview_definition(
        self, app_id: str, app_version: str, userview_id: str
    ) -> dict[str, Any] | None:
        """
        Get userview JSON definition from database.

        Args:
            app_id: Application ID
            app_version: Application version
            userview_id: Userview ID

        Returns:
            Userview definition as dictionary, or None if not found
        """
        query = """
            SELECT json
            FROM app_userview
            WHERE appId = %s AND appVersion = %s AND id = %s
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Getting userview definition: {app_id}/{app_version}/{userview_id}")

        results = self.execute_query(query, (app_id, app_version, userview_id))

        if not results or not results[0].get("json"):
            return None

        try:
            return json.loads(results[0]["json"])
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in userview definition: {e}")
            return None

    def update_userview_json(
        self,
        app_id: str,
        app_version: str,
        userview_id: str,
        definition: dict[str, Any],
    ) -> bool:
        """
        Update userview JSON definition in database.

        WARNING: Changes made via direct database update may not be visible
        until Joget/Tomcat is restarted due to caching.

        Args:
            app_id: Application ID
            app_version: Application version
            userview_id: Userview ID
            definition: Updated userview definition

        Returns:
            True if updated successfully, False otherwise
        """
        query = """
            UPDATE app_userview
            SET json = %s, dateModified = NOW()
            WHERE appId = %s AND appVersion = %s AND id = %s
        """

        affected = self.execute_update(
            query, (json.dumps(definition), app_id, app_version, userview_id)
        )

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Updated userview {userview_id}: {affected} rows affected")

        return affected > 0

    # ========================================================================
    # Category Operations
    # ========================================================================

    def find_category(
        self,
        app_id: str,
        userview_id: str,
        category_label: str,
        app_version: str = "1",
    ) -> dict[str, Any] | None:
        """
        Find a category in userview by label.

        Args:
            app_id: Application ID
            userview_id: Userview ID
            category_label: Label to search for (partial match)
            app_version: Application version (default: "1")

        Returns:
            Category dict if found, None otherwise
        """
        definition = self.get_userview_definition(app_id, app_version, userview_id)
        if not definition:
            return None

        for category in definition.get("categories", []):
            label = category.get("properties", {}).get("label", "")
            if category_label in label:
                return category

        return None

    def get_category_menus(
        self,
        app_id: str,
        userview_id: str,
        category_label: str,
        app_version: str = "1",
    ) -> list[dict[str, Any]]:
        """
        Get all menus in a specific category.

        Args:
            app_id: Application ID
            userview_id: Userview ID
            category_label: Category label to find
            app_version: Application version

        Returns:
            List of menu configurations, empty list if category not found
        """
        category = self.find_category(app_id, userview_id, category_label, app_version)
        if not category:
            return []

        return category.get("menus", [])

    def get_existing_form_ids_in_category(
        self,
        app_id: str,
        userview_id: str,
        category_label: str,
        app_version: str = "1",
    ) -> set[str]:
        """
        Get form IDs already present in a category's menus.

        Useful for checking which forms already have menu items.

        Args:
            app_id: Application ID
            userview_id: Userview ID
            category_label: Category label
            app_version: Application version

        Returns:
            Set of form IDs that have menu entries
        """
        menus = self.get_category_menus(app_id, userview_id, category_label, app_version)

        form_ids = set()
        for menu in menus:
            form_id = menu.get("properties", {}).get("addFormId", "")
            if form_id:
                form_ids.add(form_id)

        return form_ids

    def add_menus_to_category(
        self,
        app_id: str,
        userview_id: str,
        category_label: str,
        menus: list[dict[str, Any]],
        app_version: str = "1",
        skip_existing: bool = True,
    ) -> int:
        """
        Add menu items to a category via direct database update.

        WARNING: Requires Joget/Tomcat restart for changes to be visible.

        Args:
            app_id: Application ID
            userview_id: Userview ID
            category_label: Category label to add menus to
            menus: List of menu configurations to add
            app_version: Application version
            skip_existing: Skip menus whose form_id already exists

        Returns:
            Number of menus added

        Raises:
            ValueError: If category not found
        """
        # Get current definition
        definition = self.get_userview_definition(app_id, app_version, userview_id)
        if not definition:
            raise ValueError(f"Userview '{userview_id}' not found")

        # Find category
        category_found = False
        category_idx = -1
        for idx, category in enumerate(definition.get("categories", [])):
            label = category.get("properties", {}).get("label", "")
            if category_label in label:
                category_found = True
                category_idx = idx
                break

        if not category_found:
            raise ValueError(f"Category '{category_label}' not found in userview '{userview_id}'")

        # Get existing form IDs
        existing_menus = definition["categories"][category_idx].get("menus", [])
        existing_form_ids = set()
        for menu in existing_menus:
            form_id = menu.get("properties", {}).get("addFormId", "")
            if form_id:
                existing_form_ids.add(form_id)

        # Add new menus
        added = 0
        for menu in menus:
            form_id = menu.get("properties", {}).get("addFormId", "")

            if skip_existing and form_id in existing_form_ids:
                continue

            existing_menus.append(menu)
            added += 1

        # Update category
        definition["categories"][category_idx]["menus"] = existing_menus

        # Save
        if added > 0:
            self.update_userview_json(app_id, app_version, userview_id, definition)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Added {added} menus to category '{category_label}'")

        return added

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_userview_info(self, row: dict[str, Any]) -> UserviewInfo:
        """
        Convert database row to UserviewInfo object.

        Args:
            row: Database row dictionary

        Returns:
            UserviewInfo instance
        """
        json_def = None
        if row.get("json"):
            try:
                json_def = json.loads(row["json"])
            except json.JSONDecodeError:
                pass

        return UserviewInfo(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            app_id=row["appId"],
            app_version=row["appVersion"],
            json_definition=json_def,
        )
