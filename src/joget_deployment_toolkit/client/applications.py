"""
Application operations mixin for Joget client.

Provides all application-related operations including:
- Listing and querying applications
- Exporting applications to ZIP
- Importing applications from ZIP
- Batch operations
"""

import logging
from datetime import datetime
from pathlib import Path

from ..models import (
    ApplicationDetails,
    ApplicationInfo,
    ExportResult,
    ImportResult,
    application_info_from_dict,
)

logger = logging.getLogger(__name__)


class ApplicationOperations:
    """
    Mixin providing application management operations.

    This mixin requires the class to have:
    - self.get(endpoint, **kwargs) -> Dict
    - self.post(endpoint, **kwargs) -> Dict
    - self.session -> requests.Session
    - self.base_url -> str
    - self._get_headers() -> Dict[str, str]
    - self.config.timeout -> int
    - self.config.debug -> bool
    - self.logger -> logging.Logger
    """

    # ========================================================================
    # Application Query Operations
    # ========================================================================

    def list_applications(self) -> list[ApplicationInfo]:
        """
        List all published applications.

        Endpoint: /web/json/console/app/list

        Returns:
            List of ApplicationInfo objects containing basic metadata
            for each published application

        Raises:
            JogetAPIError: On API errors
            AuthenticationError: If authentication fails

        Example:
            >>> client = JogetClient("http://localhost:8080/jw", api_key="key")
            >>> apps = client.list_applications()
            >>> for app in apps:
            ...     print(f"{app.id} v{app.version}: {app.name}")
        """
        endpoint = "/web/json/console/app/list"
        data = self.get(endpoint)

        apps = []
        for item in data.get("data", []):
            apps.append(application_info_from_dict(item))

        if self.config.debug:
            self.logger.debug(f"Found {len(apps)} published applications")

        return apps

    def get_application(self, app_id: str, *, app_version: str = "1") -> ApplicationDetails:
        """
        Get detailed application information.

        Endpoint: /web/json/console/app/{appId}/{version}

        Args:
            app_id: Application ID
            app_version: Application version (default: "1")

        Returns:
            ApplicationDetails with complete metadata including
            description, forms, processes, datalists, and userviews

        Raises:
            NotFoundError: If application doesn't exist
            AuthenticationError: If authentication fails
            JogetAPIError: On other API errors

        Example:
            >>> app = client.get_application("farmersPortal")
            >>> print(f"Name: {app.name}")
            >>> print(f"Published: {app.published}")
            >>> print(f"Description: {app.description}")
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}"

        if self.config.debug:
            self.logger.debug(f"Fetching application: {app_id} v{app_version}")

        data = self.get(endpoint)

        return ApplicationDetails(
            id=data.get("id", app_id),
            name=data.get("name", ""),
            version=data.get("version", app_version),
            published=data.get("published", False),
            description=data.get("description"),
            raw_data=data,
        )

    # ========================================================================
    # Application Export/Import Operations
    # ========================================================================

    def export_application(
        self, app_id: str, output_path: str | Path, *, app_version: str = "1"
    ) -> ExportResult:
        """
        Export application to ZIP file.

        This method streams the application export to a file, handling
        large applications efficiently without loading the entire ZIP
        into memory.

        Endpoint: /web/json/console/app/{appId}/{version}/export

        Args:
            app_id: Application ID to export
            output_path: Path where ZIP file will be saved
            app_version: Application version (default: "1")

        Returns:
            ExportResult containing:
            - success: True if export succeeded
            - output_path: Path to exported file
            - file_size_bytes: Size of exported ZIP
            - duration_ms: Export duration in milliseconds
            - message: Success/error message

        Raises:
            NotFoundError: If application doesn't exist
            IOError: If cannot write to output_path
            AuthenticationError: If authentication fails
            JogetAPIError: On other API errors

        Example:
            >>> result = client.export_application(
            ...     "farmersPortal",
            ...     "backups/farmersPortal.zip"
            ... )
            >>> if result.success:
            ...     print(f"Exported {result.file_size_bytes} bytes")
            ... else:
            ...     print(f"Export failed: {result.message}")
        """
        start_time = datetime.now()
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/export"

        if self.config.debug:
            self.logger.debug(f"Exporting application: {app_id} v{app_version} to {output_path}")

        try:
            # Get streaming response
            response = self.get(endpoint, stream=True)

            # Ensure output directory exists
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Stream response to file
            file_size = 0
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        file_size += len(chunk)

            duration = (datetime.now() - start_time).total_seconds() * 1000

            if self.config.debug:
                self.logger.debug(f"Export completed: {file_size} bytes in {duration:.0f}ms")

            return ExportResult(
                success=True,
                output_path=str(output_path),
                file_size_bytes=file_size,
                duration_ms=duration,
                message=f"Exported {app_id} to {output_path}",
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000

            if self.config.debug:
                self.logger.error(f"Export failed after {duration:.0f}ms: {e}")

            return ExportResult(
                success=False,
                output_path=str(output_path),
                duration_ms=duration,
                message=f"Export failed: {e}",
            )

    def import_application(
        self, zip_path: str | Path, *, overwrite: bool = False
    ) -> ImportResult:
        """
        Import application from ZIP file.

        Uploads and imports a previously exported application ZIP file.
        Uses multipart file upload to handle large application files.

        Endpoint: /web/json/console/app/import

        Args:
            zip_path: Path to application ZIP export file
            overwrite: If True, overwrite existing application with same ID.
                      If False, raise ConflictError if application exists.
                      (default: False)

        Returns:
            ImportResult containing:
            - success: True if import succeeded
            - app_id: ID of imported application
            - app_version: Version of imported application
            - message: Success/error message
            - warnings: List of warning messages (if any)

        Raises:
            FileNotFoundError: If zip_path doesn't exist
            ValidationError: If ZIP file is invalid or corrupted
            ConflictError: If application exists and overwrite=False
            AuthenticationError: If authentication fails
            JogetAPIError: On other API errors

        Example:
            >>> # Import new application
            >>> result = client.import_application("app_export.zip")
            >>> if result.success:
            ...     print(f"Imported: {result.app_id} v{result.app_version}")
            ...
            >>> # Import and overwrite existing application
            >>> result = client.import_application(
            ...     "app_export.zip",
            ...     overwrite=True
            ... )
        """
        zip_path = Path(zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        if self.config.debug:
            self.logger.debug(f"Importing application from {zip_path} (overwrite={overwrite})")

        endpoint = "/web/json/console/app/import"

        with open(zip_path, "rb") as f:
            files = {"file": (zip_path.name, f, "application/zip")}
            data = {"overwrite": "true" if overwrite else "false"}

            # Use session directly for multipart upload
            # (our wrapper may not handle files correctly)
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()

            response = self.session.post(
                url, headers=headers, data=data, files=files, timeout=self.config.timeout
            )

            # Import map_http_error locally to avoid circular imports
            from ..exceptions import map_http_error

            if not (200 <= response.status_code < 300):
                raise map_http_error(response, endpoint)

            result = response.json()

            import_result = ImportResult(
                success=result.get("success", False),
                app_id=result.get("appId", ""),
                app_version=result.get("appVersion", "1"),
                message=result.get("message"),
                warnings=result.get("warnings"),
            )

            if self.config.debug:
                if import_result.success:
                    self.logger.debug(
                        f"Import succeeded: {import_result.app_id} v{import_result.app_version}"
                    )
                else:
                    self.logger.error(f"Import failed: {import_result.message}")

            return import_result

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def batch_export_applications(
        self,
        app_ids: list[str],
        output_dir: str | Path,
        *,
        app_version: str = "1",
        stop_on_error: bool = False,
    ) -> list[ExportResult]:
        """
        Export multiple applications to a directory.

        Exports each application in the list to a separate ZIP file in
        the specified output directory. Files are named:
        {app_id}_v{app_version}.zip

        Args:
            app_ids: List of application IDs to export
            output_dir: Directory where ZIP files will be saved
            app_version: Application version for all apps (default: "1")
            stop_on_error: If True, stop on first failure. If False,
                          continue exporting remaining apps. (default: False)

        Returns:
            List of ExportResult objects, one for each application.
            Results are in same order as app_ids list.

        Example:
            >>> apps = ["farmersPortal", "farmlandRegistry", "masterData"]
            >>> results = client.batch_export_applications(
            ...     apps,
            ...     "backups/20250116"
            ... )
            >>> successful = [r for r in results if r.success]
            >>> print(f"Exported {len(successful)}/{len(apps)} applications")
            >>>
            >>> # Check individual results
            >>> for result in results:
            ...     if result.success:
            ...         print(f"✓ {result.output_path}")
            ...     else:
            ...         print(f"✗ Failed: {result.message}")
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.config.debug:
            self.logger.debug(f"Batch exporting {len(app_ids)} applications to {output_dir}")

        results = []

        for app_id in app_ids:
            output_path = output_dir / f"{app_id}_v{app_version}.zip"

            try:
                result = self.export_application(app_id, output_path, app_version=app_version)
                results.append(result)

                if not result.success and stop_on_error:
                    if self.config.debug:
                        self.logger.warning(f"Stopping batch export: {result.message}")
                    break

            except Exception as e:
                result = ExportResult(
                    success=False, output_path=str(output_path), message=f"Export failed: {e}"
                )
                results.append(result)

                if stop_on_error:
                    if self.config.debug:
                        self.logger.warning(f"Stopping batch export: {e}")
                    break

        successful = sum(1 for r in results if r.success)

        if self.config.debug:
            self.logger.debug(f"Batch export completed: {successful}/{len(results)} successful")

        return results
