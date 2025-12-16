"""
Form operations mixin for Joget client.

Provides all form-related operations including:
- Console API operations (list, get, update, delete)
- formCreator plugin operations (create with API endpoint)
- Batch operations
"""

import json
import logging
from typing import Any

from ..exceptions import ValidationError
from ..models import FormInfo, FormResult, form_info_from_dict

logger = logging.getLogger(__name__)


class FormOperations:
    """
    Mixin providing form-related operations.

    This mixin requires the class to have:
    - self.get(endpoint, **kwargs) -> Dict
    - self.post(endpoint, **kwargs) -> Dict
    - self.config.debug -> bool
    - self.logger -> logging.Logger
    """

    # ========================================================================
    # Console API Operations
    # ========================================================================

    def list_forms(self, app_id: str, *, app_version: str = "1") -> list[FormInfo]:
        """
        List all forms in an application via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/forms

        Args:
            app_id: Application ID
            app_version: Application version (default: "1")

        Returns:
            List of FormInfo objects

        Raises:
            NotFoundError: If application doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> client = JogetClient("http://localhost:8080/jw", api_key="key")
            >>> forms = client.list_forms("farmersPortal")
            >>> for form in forms:
            ...     print(f"{form.form_id}: {form.form_name}")
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/forms"
        data = self.get(endpoint)

        forms = []
        for item in data.get("data", []):
            forms.append(form_info_from_dict(item))

        if self.config.debug:
            self.logger.debug(f"Found {len(forms)} forms in {app_id}")

        return forms

    def get_form(self, app_id: str, form_id: str, *, app_version: str = "1") -> dict[str, Any]:
        """
        Retrieve complete form definition via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/form/{formId}

        Args:
            app_id: Application ID
            form_id: Form ID
            app_version: Application version (default: "1")

        Returns:
            Complete form definition as dictionary

        Raises:
            NotFoundError: If form doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> form_def = client.get_form("farmersPortal", "farmer_basic")
            >>> print(form_def['properties']['name'])
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}"
        return self.get(endpoint)

    def update_form(
        self, app_id: str, form_id: str, form_definition: dict[str, Any], *, app_version: str = "1"
    ) -> FormResult:
        """
        Update existing form via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/form/{formId}/update

        Args:
            app_id: Application ID
            form_id: Form ID
            form_definition: Updated form definition (complete JSON)
            app_version: Application version (default: "1")

        Returns:
            FormResult with success status and message

        Raises:
            NotFoundError: If form doesn't exist
            ValidationError: If form definition is invalid
            JogetAPIError: On API errors

        Example:
            >>> form_def = client.get_form("farmersPortal", "farmer_basic")
            >>> form_def['properties']['name'] = "Updated Form Name"
            >>> result = client.update_form("farmersPortal", "farmer_basic", form_def)
            >>> print(result.message)
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}/update"

        if not form_definition:
            raise ValidationError("Form definition cannot be empty")

        response = self.post(endpoint, json=form_definition)

        return FormResult(
            success=response.get("success", False),
            form_id=form_id,
            message=response.get("message"),
            raw_data=response,
        )

    def delete_form(self, app_id: str, form_id: str, *, app_version: str = "1") -> bool:
        """
        Delete form via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/form/{formId}/delete

        Args:
            app_id: Application ID
            form_id: Form ID
            app_version: Application version (default: "1")

        Returns:
            True if deleted successfully, False otherwise

        Raises:
            NotFoundError: If form doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> success = client.delete_form("farmersPortal", "old_form")
            >>> if success:
            ...     print("Form deleted")
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}/delete"
        response = self.post(endpoint, json={})

        success = response.get("success", False)
        if self.config.debug:
            self.logger.debug(f"Delete form {form_id}: {'success' if success else 'failed'}")

        return success

    # ========================================================================
    # formCreator Plugin Operations
    # ========================================================================

    def create_form(
        self, payload: dict[str, Any], form_definition: dict[str, Any], api_id: str, api_key: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new form using the formCreator plugin API.

        This method uses the formCreator plugin to create a form with
        automatic API endpoint generation and CRUD operations.

        Args:
            payload: Form creation payload containing:
                - target_app_id (str): Target application ID
                - target_app_version (str): Target application version
                - form_id (str): Form identifier
                - form_name (str): Form display name
                - table_name (str): Database table name
                - form_definition_json (str): Empty string (file will be uploaded)
                - create_api_endpoint (str): "yes" or "no"
                - create_crud (str): "yes" or "no"
            form_definition: Form JSON definition (dict)
            api_id: API ID for the formCreator endpoint
            api_key: Optional API key override

        Returns:
            Response data as dictionary

        Raises:
            ValidationError: If required fields are missing
            JogetAPIError: On API errors

        Example:
            >>> payload = {
            ...     "target_app_id": "farmersPortal",
            ...     "target_app_version": "1",
            ...     "form_id": "new_form",
            ...     "form_name": "New Form",
            ...     "table_name": "new_form",
            ...     "form_definition_json": "",
            ...     "create_api_endpoint": "yes",
            ...     "create_crud": "yes"
            ... }
            >>> result = client.create_form(payload, form_def, api_id="fc_api")
        """
        # Validate required fields (excluding form_definition_json which can be empty)
        required_fields = [
            "target_app_id",
            "target_app_version",
            "form_id",
            "form_name",
            "table_name",
        ]

        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

        if self.config.debug:
            self.logger.debug(
                f"Creating form: {payload.get('form_id')} in {payload.get('target_app_id')}"
            )

        # Prepare form JSON as temporary file
        # CRITICAL: Do NOT add 'form_definition_json' to payload dict
        # Only upload as file - otherwise empty string overwrites file reference
        import tempfile
        import os

        form_json_str = json.dumps(form_definition)

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            prefix=f'{payload.get("form_id", "form")}_',
            delete=False
        )
        temp_file.write(form_json_str)
        temp_file.close()

        try:
            # Upload as file (do NOT include in payload dict)
            with open(temp_file.name, 'rb') as f:
                files = {'form_definition_json': f}

                # Use the formCreator API endpoint with file upload
                response = self.post(
                    endpoint="/api/form/formCreator/addWithFiles",
                    data=payload,  # Form data fields (NO form_definition_json here!)
                    files=files,  # File upload
                    api_id=api_id,
                    api_key=api_key,
                )
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                if self.config.debug:
                    self.logger.debug(f"Failed to delete temp file {temp_file.name}: {e}")

        return response

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def batch_create_forms(
        self,
        payloads: list[dict[str, Any]],
        api_id: str,
        api_key: str | None = None,
        stop_on_error: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Create multiple forms in batch.

        Args:
            payloads: List of form creation payloads
            api_id: API ID for formCreator
            api_key: Optional API key override
            stop_on_error: If True, stop on first error; if False, continue

        Returns:
            List of results (one per form)

        Example:
            >>> payloads = [payload1, payload2, payload3]
            >>> results = client.batch_create_forms(payloads, api_id="fc_api")
            >>> for i, result in enumerate(results):
            ...     if result.get("error"):
            ...         print(f"Form {i} failed: {result['error']}")
        """
        results = []

        for i, payload in enumerate(payloads):
            try:
                result = self.create_form(payload, api_id, api_key)
                results.append(
                    {
                        "index": i,
                        "form_id": payload.get("form_id"),
                        "success": True,
                        "result": result,
                    }
                )

                if self.config.debug:
                    self.logger.debug(
                        f"Created form {i+1}/{len(payloads)}: {payload.get('form_id')}"
                    )

            except Exception as e:
                error_info = {
                    "index": i,
                    "form_id": payload.get("form_id"),
                    "success": False,
                    "error": str(e),
                }
                results.append(error_info)

                self.logger.error(f"Failed to create form {i+1}/{len(payloads)}: {e}")

                if stop_on_error:
                    break

        return results

    def batch_update_forms(
        self,
        updates: list[dict[str, Any]],
        app_id: str,
        *,
        app_version: str = "1",
        stop_on_error: bool = False,
    ) -> list[FormResult]:
        """
        Update multiple forms in batch.

        Args:
            updates: List of dicts with 'form_id' and 'definition' keys
            app_id: Application ID
            app_version: Application version
            stop_on_error: If True, stop on first error

        Returns:
            List of FormResult objects

        Example:
            >>> updates = [
            ...     {"form_id": "form1", "definition": form1_def},
            ...     {"form_id": "form2", "definition": form2_def}
            ... ]
            >>> results = client.batch_update_forms(updates, "farmersPortal")
        """
        results = []

        for i, update in enumerate(updates):
            form_id = update.get("form_id")
            definition = update.get("definition")

            if not form_id or not definition:
                results.append(
                    FormResult(
                        success=False,
                        form_id=form_id or "unknown",
                        message="Missing form_id or definition",
                    )
                )
                continue

            try:
                result = self.update_form(app_id, form_id, definition, app_version=app_version)
                results.append(result)

                if self.config.debug:
                    self.logger.debug(f"Updated form {i+1}/{len(updates)}: {form_id}")

            except Exception as e:
                result = FormResult(success=False, form_id=form_id, message=str(e))
                results.append(result)

                self.logger.error(f"Failed to update form {form_id}: {e}")

                if stop_on_error:
                    break

        return results

    # ========================================================================
    # Form Management API Plugin Operations (Direct Form Creation)
    # ========================================================================

    def create_form_direct(
        self,
        app_id: str,
        form_id: str,
        form_name: str,
        table_name: str,
        form_definition: dict[str, Any],
        *,
        app_version: str = "1",
        create_api_endpoint: bool = False,
        api_name: str | None = None,
        create_crud: bool = False,
        crud_name: str | None = None,
        overwrite_if_exists: bool = False
    ) -> FormResult:
        """
        Create form directly using Form Management API Plugin.

        This method bypasses the formCreator plugin entirely and uses
        a dedicated API plugin for reliable programmatic form creation.
        The plugin creates the form definition and allows Joget to auto-create
        the table when the form is first accessed.

        Args:
            app_id: Target application ID
            form_id: Form identifier
            form_name: Display name for the form
            table_name: Database table name
            form_definition: Complete form JSON definition
            app_version: Application version (default: "1")
            create_api_endpoint: Create REST API endpoint for form data (not yet implemented)
            api_name: API endpoint name (defaults to "{form_id}_api")
            create_crud: Create CRUD datalist (not yet implemented)
            crud_name: CRUD datalist name (defaults to "{form_id}_list")
            overwrite_if_exists: Overwrite if form already exists

        Returns:
            FormResult with creation status and metadata

        Raises:
            ConflictError: If form exists and overwrite=False
            ValidationError: If form JSON is invalid
            JogetAPIError: On API errors

        Example:
            >>> result = client.create_form_direct(
            ...     app_id="farmersPortal",
            ...     form_id="md01maritalStatus",
            ...     form_name="MD.01 - Marital Status",
            ...     table_name="md01maritalStatus",
            ...     form_definition=form_def
            ... )
            >>> print(f"Form created: {result.form_id}")
            >>> print(f"Success: {result.success}")
        """
        # Prepare request payload
        payload = {
            "appId": app_id,
            "appVersion": app_version,
            "formId": form_id,
            "formName": form_name,
            "tableName": table_name,
            "formDefinition": form_definition,
            "options": {
                "createApiEndpoint": create_api_endpoint,
                "apiName": api_name or f"{form_id}_api",
                "createCrud": create_crud,
                "crudName": crud_name or f"{form_id}_list",
                "overwriteIfExists": overwrite_if_exists
            }
        }

        if self.config.debug:
            self.logger.debug(
                f"Creating form via Form Management API: {form_id} in {app_id}"
            )

        # Call Form Management API
        response = self.post(
            endpoint="/api/form-management/forms",
            json=payload
        )

        # Parse response
        return FormResult(
            success=response.get("success", False),
            form_id=response.get("formId", form_id),
            message=response.get("message"),
            raw_data=response
        )


__all__ = ["FormOperations"]
