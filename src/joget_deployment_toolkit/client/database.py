"""
Database operations mixin for Joget client.

Provides database access for operations that require querying the Joget database directly.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """
    Mixin providing database-related operations.

    This mixin requires the class to have:
    - self.config.db_config -> DatabaseConfig or dict
    - self.logger -> logging.Logger
    """

    def get_api_id_for_form(
        self, app_id: str, api_name: str, app_version: str = "1"
    ) -> str | None:
        """
        Query database for API ID by application and API name.

        This method queries the app_builder table to find the API ID for a given
        API endpoint. This is needed after creating forms with the FormCreator plugin,
        which auto-generates API endpoints with predictable naming patterns.

        Args:
            app_id: Application ID
            api_name: API endpoint name (e.g., "api_md01maritalStatus")
            app_version: Application version (default: "1")

        Returns:
            API ID if found, None otherwise

        Example:
            >>> api_id = client.get_api_id_for_form(
            ...     "farmersPortal",
            ...     "api_md01maritalStatus",
            ...     "1"
            ... )
            >>> if api_id:
            ...     print(f"Found API: {api_id}")
        """
        try:
            # Import here to avoid circular dependencies
            from ..database.connection import DatabaseConnectionPool
            from ..database.repositories.form_repository import FormRepository
            from ..models import DatabaseConfig

            # Get database config from client config
            if not hasattr(self, "config"):
                self.logger.warning("Client has no config attribute")
                return None

            db_config_data = getattr(self.config, "db_config", None)
            if not db_config_data:
                self.logger.warning("No database configuration available")
                return None

            # Convert to DatabaseConfig if it's a dict
            if isinstance(db_config_data, dict):
                db_config = DatabaseConfig(**db_config_data)
            else:
                db_config = db_config_data

            # Create connection pool and repository
            pool = DatabaseConnectionPool(db_config)
            repo = FormRepository(pool)

            # Query for API endpoint
            api_info = repo.find_api_endpoint(app_id, app_version, api_name)

            # Close pool
            pool.close()

            if api_info:
                return api_info["id"]

            return None

        except Exception as e:
            self.logger.error(f"Failed to query API ID: {e}")
            return None


__all__ = ["DatabaseOperations"]
