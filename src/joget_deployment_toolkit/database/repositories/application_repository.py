"""
Application repository for accessing Joget application data.

Provides database access for application-related operations including:
- Finding applications
- Finding published applications
- Finding by version
- Application metadata queries
"""

import logging
from typing import Any

from ...models import ApplicationInfo, parse_datetime
from .base import BaseRepository

logger = logging.getLogger(__name__)


class ApplicationRepository(BaseRepository[ApplicationInfo]):
    """
    Repository for accessing Joget application data from the database.

    This repository provides methods for querying the app_app table
    to discover applications and their metadata.

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
        >>> repo = ApplicationRepository(pool)
        >>>
        >>> # Find all published applications
        >>> apps = repo.find_published()
        >>> for app in apps:
        ...     print(f"{app.id} v{app.version}: {app.name}")
        >>>
        >>> # Find specific version
        >>> app = repo.find_by_version("farmersPortal", "1")
        >>> print(app.name if app else "Not found")
    """

    # ========================================================================
    # Required Abstract Methods Implementation
    # ========================================================================

    def find_by_id(self, id: str) -> ApplicationInfo | None:
        """
        Find application by ID (returns latest version).

        Args:
            id: Application ID

        Returns:
            ApplicationInfo for latest version if found, None otherwise

        Example:
            >>> app = repo.find_by_id("farmersPortal")
            >>> if app:
            ...     print(f"Latest version: {app.version}")
        """
        query = """
            SELECT appId, appVersion, name, published, dateCreated, dateModified
            FROM app_app
            WHERE appId = %s
            ORDER BY appVersion DESC
            LIMIT 1
        """

        results = self.execute_query(query, (id,))

        if not results:
            return None

        return self._row_to_application_info(results[0])

    def find_all(self) -> list[ApplicationInfo]:
        """
        Find all applications (all versions).

        Returns:
            List of all ApplicationInfo objects

        Warning:
            This returns ALL versions of ALL applications.
            Consider using find_published() or find_latest_versions() instead.

        Example:
            >>> all_apps = repo.find_all()
            >>> print(f"Total app versions: {len(all_apps)}")
        """
        query = """
            SELECT appId, appVersion, name, published, dateCreated, dateModified
            FROM app_app
            ORDER BY appId, appVersion
        """

        results = self.execute_query(query)
        return [self._row_to_application_info(row) for row in results]

    def save(self, entity: ApplicationInfo) -> ApplicationInfo:
        """
        Save application information.

        Note: This implementation is not supported. Use Joget API for
        application deployment.

        Args:
            entity: ApplicationInfo to save

        Returns:
            Saved ApplicationInfo

        Raises:
            NotImplementedError: Application save not supported via database
        """
        raise NotImplementedError(
            "Application save via database is not supported. "
            "Use JogetClient for application deployment."
        )

    def delete(self, id: str) -> bool:
        """
        Delete application by ID.

        Note: This is a dangerous operation and not supported.
        Use the Joget API for safe application deletion.

        Args:
            id: Application ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            NotImplementedError: Direct database deletion not supported
        """
        raise NotImplementedError(
            "Application deletion via database is not supported. "
            "Use JogetClient for safe application deletion."
        )

    # ========================================================================
    # Application-Specific Query Methods
    # ========================================================================

    def find_published(self) -> list[ApplicationInfo]:
        """
        Find all published applications (latest versions only).

        Returns:
            List of published ApplicationInfo objects

        Example:
            >>> published_apps = repo.find_published()
            >>> print(f"Published applications: {len(published_apps)}")
            >>> for app in published_apps:
            ...     print(f"  {app.name} v{app.version}")
        """
        query = """
            SELECT a1.appId, a1.appVersion, a1.name, a1.published,
                   a1.dateCreated, a1.dateModified
            FROM app_app a1
            INNER JOIN (
                SELECT appId, MAX(appVersion) as maxVersion
                FROM app_app
                WHERE published = 1
                GROUP BY appId
            ) a2 ON a1.appId = a2.appId AND a1.appVersion = a2.maxVersion
            WHERE a1.published = 1
            ORDER BY a1.name
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("Finding published applications")

        results = self.execute_query(query)
        apps = [self._row_to_application_info(row) for row in results]

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Found {len(apps)} published applications")

        return apps

    def find_by_version(self, app_id: str, app_version: str) -> ApplicationInfo | None:
        """
        Find specific application version.

        Args:
            app_id: Application ID
            app_version: Application version

        Returns:
            ApplicationInfo if found, None otherwise

        Example:
            >>> app = repo.find_by_version("farmersPortal", "1")
            >>> if app:
            ...     print(f"Published: {app.published}")
        """
        query = """
            SELECT appId, appVersion, name, published, dateCreated, dateModified
            FROM app_app
            WHERE appId = %s AND appVersion = %s
        """

        results = self.execute_query(query, (app_id, app_version))

        if not results:
            return None

        return self._row_to_application_info(results[0])

    def find_all_versions(self, app_id: str) -> list[ApplicationInfo]:
        """
        Find all versions of an application.

        Args:
            app_id: Application ID

        Returns:
            List of ApplicationInfo objects for all versions

        Example:
            >>> versions = repo.find_all_versions("farmersPortal")
            >>> print(f"Versions: {[v.version for v in versions]}")
        """
        query = """
            SELECT appId, appVersion, name, published, dateCreated, dateModified
            FROM app_app
            WHERE appId = %s
            ORDER BY appVersion
        """

        results = self.execute_query(query, (app_id,))
        return [self._row_to_application_info(row) for row in results]

    def find_latest_versions(self) -> list[ApplicationInfo]:
        """
        Find latest version of each application.

        Returns:
            List of ApplicationInfo objects (one per app, latest version)

        Example:
            >>> latest_apps = repo.find_latest_versions()
            >>> for app in latest_apps:
            ...     print(f"{app.id} v{app.version} (published={app.published})")
        """
        query = """
            SELECT a1.appId, a1.appVersion, a1.name, a1.published,
                   a1.dateCreated, a1.dateModified
            FROM app_app a1
            INNER JOIN (
                SELECT appId, MAX(appVersion) as maxVersion
                FROM app_app
                GROUP BY appId
            ) a2 ON a1.appId = a2.appId AND a1.appVersion = a2.maxVersion
            ORDER BY a1.name
        """

        results = self.execute_query(query)
        return [self._row_to_application_info(row) for row in results]

    def is_published(self, app_id: str, app_version: str) -> bool:
        """
        Check if specific application version is published.

        Args:
            app_id: Application ID
            app_version: Application version

        Returns:
            True if published, False otherwise

        Example:
            >>> if repo.is_published("farmersPortal", "1"):
            ...     print("Application is published")
        """
        query = """
            SELECT published
            FROM app_app
            WHERE appId = %s AND appVersion = %s
        """

        result = self.execute_scalar(query, (app_id, app_version))
        return bool(result) if result is not None else False

    def count_versions(self, app_id: str) -> int:
        """
        Count number of versions for an application.

        Args:
            app_id: Application ID

        Returns:
            Number of versions

        Example:
            >>> count = repo.count_versions("farmersPortal")
            >>> print(f"Application has {count} versions")
        """
        return self.count("app_app", "appId = %s", (app_id,))

    def search_by_name(self, name_pattern: str) -> list[ApplicationInfo]:
        """
        Search applications by name (case-insensitive, wildcard search).

        Args:
            name_pattern: Name pattern to search (use % for wildcard)

        Returns:
            List of matching ApplicationInfo objects (latest versions)

        Example:
            >>> # Find all apps with "farmer" in name
            >>> apps = repo.search_by_name("%farmer%")
            >>> for app in apps:
            ...     print(app.name)
        """
        query = """
            SELECT a1.appId, a1.appVersion, a1.name, a1.published,
                   a1.dateCreated, a1.dateModified
            FROM app_app a1
            INNER JOIN (
                SELECT appId, MAX(appVersion) as maxVersion
                FROM app_app
                WHERE LOWER(name) LIKE LOWER(%s)
                GROUP BY appId
            ) a2 ON a1.appId = a2.appId AND a1.appVersion = a2.maxVersion
            ORDER BY a1.name
        """

        results = self.execute_query(query, (name_pattern,))
        return [self._row_to_application_info(row) for row in results]

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_application_info(self, row: dict[str, Any]) -> ApplicationInfo:
        """
        Convert database row to ApplicationInfo object.

        Args:
            row: Database row dictionary

        Returns:
            ApplicationInfo instance
        """
        return ApplicationInfo(
            id=row["appId"],
            name=row["name"],
            version=row["appVersion"],
            published=bool(row.get("published", False)),
            date_created=parse_datetime(row.get("dateCreated")),
            date_modified=parse_datetime(row.get("dateModified")),
            raw_data=row,
        )
