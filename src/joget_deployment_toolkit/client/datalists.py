"""
Datalist operations mixin for Joget client.

Provides all datalist-related operations including:
- Console API operations (list, get, create, update, delete)
- Batch operations for migration
"""

import json
import logging
from typing import Any

from ..exceptions import ValidationError
from ..models import DatalistInfo, datalist_info_from_dict

logger = logging.getLogger(__name__)


class DatalistOperations:
    """
    Mixin providing datalist-related operations.

    This mixin requires the class to have:
    - self.get(endpoint, **kwargs) -> Dict
    - self.post(endpoint, **kwargs) -> Dict
    - self.config.debug -> bool
    - self.logger -> logging.Logger
    """

    # ========================================================================
    # Console API Operations
    # ========================================================================

    def list_datalists(self, app_id: str, *, app_version: str = "1") -> list[DatalistInfo]:
        """
        List all datalists in an application via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/datalist/list

        Args:
            app_id: Application ID
            app_version: Application version (default: "1")

        Returns:
            List of DatalistInfo objects

        Raises:
            NotFoundError: If application doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> client = JogetClient.from_instance('jdx4')
            >>> datalists = client.list_datalists("farmersPortal")
            >>> for dl in datalists:
            ...     print(f"{dl.id}: {dl.name}")
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/datalist/list"
        data = self.get(endpoint)

        datalists = []
        for item in data.get("data", []):
            info = datalist_info_from_dict(item)
            info.app_id = app_id
            info.app_version = app_version
            datalists.append(info)

        if self.config.debug:
            self.logger.debug(f"Found {len(datalists)} datalists in {app_id}")

        return datalists

    def get_datalist(
        self, app_id: str, datalist_id: str, *, app_version: str = "1"
    ) -> dict[str, Any]:
        """
        Retrieve complete datalist definition via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/datalist/{datalistId}

        Args:
            app_id: Application ID
            datalist_id: Datalist ID
            app_version: Application version (default: "1")

        Returns:
            Complete datalist definition as dictionary

        Raises:
            NotFoundError: If datalist doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> datalist_def = client.get_datalist("farmersPortal", "list_md01")
            >>> print(datalist_def['name'])
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/datalist/{datalist_id}"
        return self.get(endpoint)

    def create_datalist(
        self,
        app_id: str,
        datalist_id: str,
        name: str,
        definition: dict[str, Any],
        *,
        app_version: str = "1",
        description: str = "",
    ) -> dict[str, Any]:
        """
        Create a new datalist via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/datalist/submit

        Args:
            app_id: Application ID
            datalist_id: Datalist identifier
            name: Datalist display name
            definition: Complete datalist JSON definition
            app_version: Application version (default: "1")
            description: Optional description

        Returns:
            Response data as dictionary

        Raises:
            ValidationError: If definition is invalid
            ConflictError: If datalist already exists
            JogetAPIError: On API errors

        Example:
            >>> result = client.create_datalist(
            ...     "farmersPortal", "list_md01", "MD01 List",
            ...     datalist_definition
            ... )
        """
        if not definition:
            raise ValidationError("Datalist definition cannot be empty")

        endpoint = f"/web/json/console/app/{app_id}/{app_version}/datalist/submit"

        payload = {
            "id": datalist_id,
            "name": name,
            "description": description,
            "json": json.dumps(definition) if isinstance(definition, dict) else definition,
        }

        if self.config.debug:
            self.logger.debug(f"Creating datalist: {datalist_id} in {app_id}")

        return self.post(endpoint, data=payload)

    def update_datalist(
        self,
        app_id: str,
        datalist_id: str,
        definition: dict[str, Any],
        *,
        app_version: str = "1",
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Update existing datalist via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/datalist/{datalistId}/submit

        Args:
            app_id: Application ID
            datalist_id: Datalist ID
            definition: Updated datalist definition (complete JSON)
            app_version: Application version (default: "1")
            name: Optional new name
            description: Optional new description

        Returns:
            Response with success status

        Raises:
            NotFoundError: If datalist doesn't exist
            ValidationError: If definition is invalid
            JogetAPIError: On API errors

        Example:
            >>> datalist_def = client.get_datalist("farmersPortal", "list_md01")
            >>> datalist_def['name'] = "Updated Name"
            >>> result = client.update_datalist("farmersPortal", "list_md01", datalist_def)
        """
        if not definition:
            raise ValidationError("Datalist definition cannot be empty")

        endpoint = f"/web/json/console/app/{app_id}/{app_version}/datalist/{datalist_id}/submit"

        payload = {
            "json": json.dumps(definition) if isinstance(definition, dict) else definition,
        }

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description

        if self.config.debug:
            self.logger.debug(f"Updating datalist: {datalist_id} in {app_id}")

        return self.post(endpoint, data=payload)

    def delete_datalist(
        self, app_id: str, datalist_id: str, *, app_version: str = "1"
    ) -> bool:
        """
        Delete datalist via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/datalist/delete

        Args:
            app_id: Application ID
            datalist_id: Datalist ID
            app_version: Application version (default: "1")

        Returns:
            True if deleted successfully, False otherwise

        Raises:
            NotFoundError: If datalist doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> success = client.delete_datalist("farmersPortal", "old_list")
            >>> if success:
            ...     print("Datalist deleted")
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/datalist/delete"
        response = self.post(endpoint, data={"ids": [datalist_id]})

        success = response.get("success", False)
        if self.config.debug:
            self.logger.debug(
                f"Delete datalist {datalist_id}: {'success' if success else 'failed'}"
            )

        return success

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def batch_create_datalists(
        self,
        app_id: str,
        datalists: list[dict[str, Any]],
        *,
        app_version: str = "1",
        stop_on_error: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Create multiple datalists in batch.

        Args:
            app_id: Target application ID
            datalists: List of dicts with 'id', 'name', and 'definition' keys
            app_version: Application version
            stop_on_error: If True, stop on first error

        Returns:
            List of results (one per datalist)

        Example:
            >>> datalists = [
            ...     {"id": "list_md01", "name": "MD01 List", "definition": dl1_def},
            ...     {"id": "list_md02", "name": "MD02 List", "definition": dl2_def}
            ... ]
            >>> results = client.batch_create_datalists("farmersPortal", datalists)
        """
        results = []

        for i, dl in enumerate(datalists):
            datalist_id = dl.get("id")
            name = dl.get("name", datalist_id)
            definition = dl.get("definition")
            description = dl.get("description", "")

            if not datalist_id or not definition:
                results.append({
                    "index": i,
                    "datalist_id": datalist_id or "unknown",
                    "success": False,
                    "error": "Missing id or definition",
                })
                continue

            try:
                result = self.create_datalist(
                    app_id, datalist_id, name, definition,
                    app_version=app_version,
                    description=description,
                )
                results.append({
                    "index": i,
                    "datalist_id": datalist_id,
                    "success": True,
                    "result": result,
                })

                if self.config.debug:
                    self.logger.debug(
                        f"Created datalist {i+1}/{len(datalists)}: {datalist_id}"
                    )

            except Exception as e:
                error_info = {
                    "index": i,
                    "datalist_id": datalist_id,
                    "success": False,
                    "error": str(e),
                }
                results.append(error_info)

                self.logger.error(f"Failed to create datalist {datalist_id}: {e}")

                if stop_on_error:
                    break

        return results


__all__ = ["DatalistOperations"]
