"""
Userview operations mixin for Joget client.

Provides all userview-related operations including:
- Console API operations (list, get, update)
- Menu manipulation for adding CRUD items to categories
"""

import json
import logging
import uuid
from typing import Any

from ..exceptions import NotFoundError, ValidationError
from ..models import UserviewInfo, userview_info_from_dict

logger = logging.getLogger(__name__)


class UserviewOperations:
    """
    Mixin providing userview-related operations.

    This mixin requires the class to have:
    - self.get(endpoint, **kwargs) -> Dict
    - self.post(endpoint, **kwargs) -> Dict
    - self.config.debug -> bool
    - self.logger -> logging.Logger
    """

    # ========================================================================
    # Console API Operations
    # ========================================================================

    def list_userviews(self, app_id: str, *, app_version: str = "1") -> list[UserviewInfo]:
        """
        List all userviews in an application via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/userview/list

        Args:
            app_id: Application ID
            app_version: Application version (default: "1")

        Returns:
            List of UserviewInfo objects

        Raises:
            NotFoundError: If application doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> client = JogetClient.from_instance('jdx4')
            >>> userviews = client.list_userviews("farmersPortal")
            >>> for uv in userviews:
            ...     print(f"{uv.id}: {uv.name}")
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/userview/list"
        data = self.get(endpoint)

        userviews = []
        for item in data.get("data", []):
            info = userview_info_from_dict(item)
            info.app_id = app_id
            info.app_version = app_version
            userviews.append(info)

        if self.config.debug:
            self.logger.debug(f"Found {len(userviews)} userviews in {app_id}")

        return userviews

    def get_userview(
        self, app_id: str, userview_id: str, *, app_version: str = "1"
    ) -> dict[str, Any]:
        """
        Retrieve complete userview definition via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/userview/{userviewId}

        Args:
            app_id: Application ID
            userview_id: Userview ID
            app_version: Application version (default: "1")

        Returns:
            Complete userview definition as dictionary

        Raises:
            NotFoundError: If userview doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> userview_def = client.get_userview("farmersPortal", "v")
            >>> print(userview_def['properties']['name'])
        """
        endpoint = f"/web/json/console/app/{app_id}/{app_version}/userview/{userview_id}"
        return self.get(endpoint)

    def update_userview(
        self,
        app_id: str,
        userview_id: str,
        definition: dict[str, Any],
        *,
        app_version: str = "1",
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Update existing userview via Console API.

        Endpoint: /web/json/console/app/{appId}/{version}/userview/{userviewId}/submit

        Args:
            app_id: Application ID
            userview_id: Userview ID
            definition: Updated userview definition (complete JSON)
            app_version: Application version (default: "1")
            name: Optional new name
            description: Optional new description

        Returns:
            Response with success status

        Raises:
            NotFoundError: If userview doesn't exist
            ValidationError: If definition is invalid
            JogetAPIError: On API errors

        Example:
            >>> uv_def = client.get_userview("farmersPortal", "v")
            >>> # Modify uv_def as needed
            >>> result = client.update_userview("farmersPortal", "v", uv_def)
        """
        if not definition:
            raise ValidationError("Userview definition cannot be empty")

        endpoint = f"/web/json/console/app/{app_id}/{app_version}/userview/{userview_id}/submit"

        payload = {
            "json": json.dumps(definition) if isinstance(definition, dict) else definition,
        }

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description

        if self.config.debug:
            self.logger.debug(f"Updating userview: {userview_id} in {app_id}")

        return self.post(endpoint, data=payload)

    # ========================================================================
    # Menu Manipulation Operations
    # ========================================================================

    def find_category(
        self,
        userview_definition: dict[str, Any],
        category_label: str,
    ) -> dict[str, Any] | None:
        """
        Find a category in userview by label.

        Args:
            userview_definition: Complete userview JSON definition
            category_label: Label to search for (partial match)

        Returns:
            Category dict if found, None otherwise

        Example:
            >>> uv_def = client.get_userview("farmersPortal", "v")
            >>> cat = client.find_category(uv_def, "Master Data")
            >>> if cat:
            ...     print(f"Found category with {len(cat.get('menus', []))} menus")
        """
        for category in userview_definition.get("categories", []):
            label = category.get("properties", {}).get("label", "")
            if category_label in label:
                return category
        return None

    def create_crud_menu(
        self,
        form_id: str,
        form_name: str,
        datalist_id: str | None = None,
        custom_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a CrudMenu configuration for a form.

        Creates standard Joget CrudMenu JSON structure following enterprise patterns.

        Args:
            form_id: Form ID for add/edit operations
            form_name: Display name for the menu label
            datalist_id: Datalist ID (defaults to list_{form_id})
            custom_id: Custom menu ID (defaults to {form_id}_crud)

        Returns:
            CrudMenu JSON configuration

        Example:
            >>> menu = client.create_crud_menu("md01", "Marital Status")
            >>> print(menu['properties']['label'])  # "Manage Marital Status"
        """
        return {
            "className": "org.joget.plugin.enterprise.CrudMenu",
            "properties": {
                "id": str(uuid.uuid4()),
                "customId": custom_id or f"{form_id}_crud",
                "label": f"Manage {form_name}",
                "datalistId": datalist_id or f"list_{form_id}",
                "addFormId": form_id,
                "editFormId": form_id,
                "checkboxPosition": "left",
                "selectionType": "multiple",
                "buttonPosition": "bothLeft",
                "rowCount": "true",
                "keyName": "",
                "edit-afterSaved": "list",
                "add-afterSaved": "list",
                "edit-readonly": "",
                "edit-allowRecordTraveling": "",
                "list-showDeleteButton": "yes",
                "add-customHeader": "",
                "add-customFooter": "",
                "add-messageShowAfterComplete": "",
                "add-saveButtonLabel": "",
                "add-cancelButtonLabel": "",
                "add-afterSavedRedirectUrl": "",
                "add-afterSavedRedirectParamName": "",
                "add-afterSavedRedirectParamvalue": "",
                "edit-customHeader": "",
                "edit-customFooter": "",
                "edit-messageShowAfterComplete": "",
                "edit-readonlyLabel": "",
                "edit-saveButtonLabel": "",
                "edit-prevButtonLabel": "",
                "edit-afterSavedRedirectUrl": "",
                "edit-afterSavedRedirectParamName": "",
                "edit-afterSavedRedirectParamvalue": "",
                "list-customHeader": "",
                "list-customFooter": "",
                "list-newButtonLabel": "",
                "list-deleteButtonLabel": "",
                "list-editLinkLabel": "",
                "edit-firstButtonLabel": "",
                "edit-lastButtonLabel": "",
                "edit-nextButtonLabel": "",
                "edit-moreActions": [],
                "list-moreActions": [],
            },
        }

    def add_menu_to_category(
        self,
        app_id: str,
        userview_id: str,
        category_label: str,
        menu_config: dict[str, Any],
        *,
        app_version: str = "1",
        skip_if_exists: bool = True,
    ) -> dict[str, Any]:
        """
        Add a menu item to a specific category in a userview.

        This method:
        1. Gets the current userview definition
        2. Finds the specified category by label
        3. Adds the menu if not already present
        4. Saves the updated userview

        Args:
            app_id: Application ID
            userview_id: Userview ID
            category_label: Label of the category to add menu to
            menu_config: Menu configuration (from create_crud_menu or similar)
            app_version: Application version (default: "1")
            skip_if_exists: Skip if menu with same addFormId already exists

        Returns:
            Response with success status and action taken

        Raises:
            NotFoundError: If userview or category doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> menu = client.create_crud_menu("md03", "Gender")
            >>> result = client.add_menu_to_category(
            ...     "farmersPortal", "v", "Master Data", menu
            ... )
            >>> print(result['action'])  # "added" or "skipped"
        """
        # Get current userview
        userview_def = self.get_userview(app_id, userview_id, app_version=app_version)

        # Find the category
        category = self.find_category(userview_def, category_label)
        if not category:
            raise NotFoundError(
                f"Category '{category_label}' not found in userview '{userview_id}'"
            )

        # Check if menu already exists (by addFormId)
        menus = category.get("menus", [])
        form_id = menu_config.get("properties", {}).get("addFormId", "")

        if skip_if_exists:
            for existing_menu in menus:
                existing_form_id = existing_menu.get("properties", {}).get("addFormId", "")
                if existing_form_id == form_id:
                    if self.config.debug:
                        self.logger.debug(f"Menu for {form_id} already exists, skipping")
                    return {"success": True, "action": "skipped", "form_id": form_id}

        # Add the menu
        menus.append(menu_config)
        category["menus"] = menus

        # Update userview
        result = self.update_userview(app_id, userview_id, userview_def, app_version=app_version)

        if self.config.debug:
            self.logger.debug(f"Added menu for {form_id} to category '{category_label}'")

        return {"success": True, "action": "added", "form_id": form_id, "result": result}

    def add_menus_to_category(
        self,
        app_id: str,
        userview_id: str,
        category_label: str,
        menu_configs: list[dict[str, Any]],
        *,
        app_version: str = "1",
        skip_if_exists: bool = True,
    ) -> dict[str, Any]:
        """
        Add multiple menu items to a category in a single update.

        More efficient than calling add_menu_to_category multiple times.

        Args:
            app_id: Application ID
            userview_id: Userview ID
            category_label: Label of the category to add menus to
            menu_configs: List of menu configurations
            app_version: Application version (default: "1")
            skip_if_exists: Skip menus that already exist

        Returns:
            Summary of added/skipped menus

        Raises:
            NotFoundError: If userview or category doesn't exist
            JogetAPIError: On API errors

        Example:
            >>> menus = [
            ...     client.create_crud_menu("md03", "Gender"),
            ...     client.create_crud_menu("md04", "Education"),
            ... ]
            >>> result = client.add_menus_to_category(
            ...     "farmersPortal", "v", "Master Data", menus
            ... )
            >>> print(f"Added: {result['added']}, Skipped: {result['skipped']}")
        """
        # Get current userview
        userview_def = self.get_userview(app_id, userview_id, app_version=app_version)

        # Find the category
        category = self.find_category(userview_def, category_label)
        if not category:
            raise NotFoundError(
                f"Category '{category_label}' not found in userview '{userview_id}'"
            )

        # Get existing form IDs
        menus = category.get("menus", [])
        existing_form_ids = set()
        for menu in menus:
            form_id = menu.get("properties", {}).get("addFormId", "")
            if form_id:
                existing_form_ids.add(form_id)

        # Add new menus
        added = 0
        skipped = 0
        added_forms = []
        skipped_forms = []

        for menu_config in menu_configs:
            form_id = menu_config.get("properties", {}).get("addFormId", "")

            if skip_if_exists and form_id in existing_form_ids:
                skipped += 1
                skipped_forms.append(form_id)
                continue

            menus.append(menu_config)
            added += 1
            added_forms.append(form_id)

        # Update if any menus were added
        if added > 0:
            category["menus"] = menus
            self.update_userview(app_id, userview_id, userview_def, app_version=app_version)

        if self.config.debug:
            self.logger.debug(
                f"Added {added} menus, skipped {skipped} to category '{category_label}'"
            )

        return {
            "success": True,
            "added": added,
            "skipped": skipped,
            "added_forms": added_forms,
            "skipped_forms": skipped_forms,
        }

    def category_exists(
        self,
        app_id: str,
        userview_id: str,
        category_label: str,
        *,
        app_version: str = "1",
    ) -> bool:
        """
        Check if a category exists in a userview.

        Args:
            app_id: Application ID
            userview_id: Userview ID
            category_label: Label to search for
            app_version: Application version (default: "1")

        Returns:
            True if category exists, False otherwise

        Example:
            >>> if client.category_exists("farmersPortal", "v", "Master Data"):
            ...     print("Category exists, safe to add menus")
        """
        try:
            userview_def = self.get_userview(app_id, userview_id, app_version=app_version)
            return self.find_category(userview_def, category_label) is not None
        except Exception:
            return False


__all__ = ["UserviewOperations"]
