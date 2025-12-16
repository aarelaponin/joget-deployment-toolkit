"""
Component deployment orchestration.

Deploys complete components containing MDM tables and forms.

A component is a directory structure with:
- mdm/forms/*.json - MDM form definitions (deployed first)
- mdm/data/*.csv - CSV data for MDM forms
- forms/*.json - Regular form definitions (deployed second)

The deployment order ensures MDM data is available before
forms that use select boxes referencing MDM tables.

Example:
    >>> from joget_deployment_toolkit import JogetClient
    >>> from joget_deployment_toolkit.operations import ComponentDeployer
    >>> from pathlib import Path
    >>>
    >>> client = JogetClient.from_instance("jdx4")
    >>> deployer = ComponentDeployer(client)
    >>>
    >>> result = deployer.deploy_component(
    ...     component_dir=Path("equipment_component"),
    ...     target_app_id="farmersPortal",
    ...     formcreator_api_id="fc_api"
    ... )
    >>>
    >>> print(result)  # ✓ equipment_component: MDM 2/2, Forms 3/3
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..models import FormResult
from .mdm_deployer import MDMDataDeployer, MDMDeploymentResult

logger = logging.getLogger(__name__)


@dataclass
class ComponentDeploymentResult:
    """Result of component deployment."""

    component_name: str
    mdm_results: list[MDMDeploymentResult] = field(default_factory=list)
    form_results: list[FormResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if deployment was completely successful."""
        if self.errors:
            return False
        mdm_ok = all(r.success for r in self.mdm_results)
        forms_ok = all(r.success for r in self.form_results)
        return mdm_ok and forms_ok

    @property
    def partial_success(self) -> bool:
        """Check if deployment was at least partially successful."""
        mdm_any = any(r.success for r in self.mdm_results)
        forms_any = any(r.success for r in self.form_results)
        return mdm_any or forms_any

    def __str__(self) -> str:
        mdm_count = len(self.mdm_results)
        mdm_ok = sum(1 for r in self.mdm_results if r.success)
        form_count = len(self.form_results)
        form_ok = sum(1 for r in self.form_results if r.success)
        status = "✓" if self.success else "⚠" if self.partial_success else "✗"
        return (
            f"{status} {self.component_name}: "
            f"MDM {mdm_ok}/{mdm_count}, Forms {form_ok}/{form_count}"
        )


class ComponentDeployer:
    """
    Deploy complete component (MDM + forms).

    Orchestrates deployment of a component directory containing
    MDM forms with data and regular forms that depend on them.

    The deployer ensures correct deployment order:
    1. MDM forms with CSV data (so data is available)
    2. Regular forms (can reference MDM via select boxes)

    Example:
        >>> deployer = ComponentDeployer(client)
        >>> result = deployer.deploy_component(
        ...     component_dir=Path("my_component"),
        ...     target_app_id="farmersPortal",
        ...     formcreator_api_id="fc_api"
        ... )
        >>> if result.success:
        ...     print("Component deployed successfully")
    """

    def __init__(self, client):
        """
        Initialize deployer with Joget client.

        Args:
            client: JogetClient instance (from_instance() recommended)

        Example:
            >>> from joget_deployment_toolkit import JogetClient
            >>> client = JogetClient.from_instance("jdx4")
            >>> deployer = ComponentDeployer(client)
        """
        self.client = client
        self.mdm_deployer = MDMDataDeployer(client)
        self.logger = logging.getLogger(__name__)

    def deploy_component(
        self,
        component_dir: Path,
        target_app_id: str,
        formcreator_api_id: str,
        *,
        target_app_version: str = "1",
        formcreator_api_key: str | None = None,
        create_crud: bool = True,
        create_api_endpoint: bool = True,
        dry_run: bool = False,
    ) -> ComponentDeploymentResult:
        """
        Deploy complete component.

        Workflow:
        1. Validate component structure
        2. Deploy MDM forms + data (if mdm/ exists)
        3. Deploy regular forms (if forms/ exists)

        Args:
            component_dir: Path to component directory
            target_app_id: Target application ID
            formcreator_api_id: API ID for formCreator endpoint
            target_app_version: Application version (default: "1")
            formcreator_api_key: API key for formCreator (optional)
            create_crud: Create CRUD datalists (default: True)
            create_api_endpoint: Create API endpoints (default: True)
            dry_run: Preview actions without executing (default: False)

        Returns:
            ComponentDeploymentResult with all results

        Raises:
            FileNotFoundError: If component_dir doesn't exist

        Example:
            >>> result = deployer.deploy_component(
            ...     component_dir=Path("equipment_component"),
            ...     target_app_id="farmersPortal",
            ...     formcreator_api_id="fc_api"
            ... )
            >>> print(f"Success: {result.success}")
        """
        component_dir = Path(component_dir)

        if not component_dir.exists():
            raise FileNotFoundError(f"Component directory not found: {component_dir}")

        result = ComponentDeploymentResult(component_name=component_dir.name)

        # Define paths
        mdm_forms_dir = component_dir / "mdm" / "forms"
        mdm_data_dir = component_dir / "mdm" / "data"
        forms_dir = component_dir / "forms"

        # Validate structure
        has_mdm = mdm_forms_dir.exists()
        has_forms = forms_dir.exists()

        if not has_mdm and not has_forms:
            result.errors.append(
                f"Component has no deployable content. "
                f"Expected mdm/forms/ or forms/ directory."
            )
            return result

        if has_mdm and not mdm_data_dir.exists():
            result.errors.append(
                f"MDM forms directory exists but data directory missing: {mdm_data_dir}"
            )
            return result

        # Step 1: Deploy MDM forms with data (if present)
        if has_mdm:
            self.logger.info(f"Deploying MDM forms from {mdm_forms_dir}...")
            result.mdm_results = self.mdm_deployer.deploy_all_mdm_from_directory(
                forms_dir=mdm_forms_dir,
                data_dir=mdm_data_dir,
                target_app_id=target_app_id,
                target_app_version=target_app_version,
                formcreator_api_id=formcreator_api_id,
                formcreator_api_key=formcreator_api_key,
                create_crud=create_crud,
                create_api_endpoint=create_api_endpoint,
                dry_run=dry_run,
            )

            mdm_ok = sum(1 for r in result.mdm_results if r.success)
            self.logger.info(
                f"MDM deployment: {mdm_ok}/{len(result.mdm_results)} successful"
            )

        # Step 2: Deploy regular forms (if present)
        if has_forms:
            self.logger.info(f"Deploying regular forms from {forms_dir}...")
            form_files = sorted(forms_dir.glob("*.json"))

            if not form_files:
                self.logger.warning(f"No JSON files found in {forms_dir}")
            else:
                for form_file in form_files:
                    form_result = self._deploy_form(
                        form_file=form_file,
                        target_app_id=target_app_id,
                        target_app_version=target_app_version,
                        formcreator_api_id=formcreator_api_id,
                        formcreator_api_key=formcreator_api_key,
                        create_crud=create_crud,
                        create_api_endpoint=create_api_endpoint,
                        dry_run=dry_run,
                    )
                    result.form_results.append(form_result)
                    self.logger.info(str(form_result))

                forms_ok = sum(1 for r in result.form_results if r.success)
                self.logger.info(
                    f"Form deployment: {forms_ok}/{len(result.form_results)} successful"
                )

        # Summary
        self.logger.info(str(result))
        return result

    def _deploy_form(
        self,
        form_file: Path,
        target_app_id: str,
        target_app_version: str,
        formcreator_api_id: str,
        formcreator_api_key: str | None,
        create_crud: bool,
        create_api_endpoint: bool,
        dry_run: bool,
    ) -> FormResult:
        """Deploy single form file."""
        form_id = form_file.stem

        if dry_run:
            self.logger.info(f"[DRY RUN] Would deploy form: {form_id}")
            return FormResult(
                success=True,
                form_id=form_id,
                message="[DRY RUN] Skipped",
            )

        try:
            with open(form_file, encoding="utf-8") as f:
                form_def = json.load(f)

            form_name = form_def.get("properties", {}).get("name", form_id)

            create_result = self.client.create_form(
                payload={
                    "target_app_id": target_app_id,
                    "target_app_version": target_app_version,
                    "form_id": form_id,
                    "form_name": form_name,
                    "table_name": form_id,
                    "create_api_endpoint": "yes" if create_api_endpoint else "no",
                    "create_crud": "yes" if create_crud else "no",
                },
                form_definition=form_def,
                api_id=formcreator_api_id,
                api_key=formcreator_api_key,
            )

            # FormCreator API returns: {"id": "uuid", "errors": {}}
            has_id = bool(create_result.get("id"))
            has_errors = bool(create_result.get("errors"))

            if has_id and not has_errors:
                return FormResult(
                    success=True,
                    form_id=form_id,
                    message=f"Created with ID: {create_result.get('id')}",
                    raw_data=create_result,
                )
            else:
                errors = create_result.get("errors", {})
                error_msg = (
                    "; ".join(f"{k}: {v}" for k, v in errors.items())
                    if errors
                    else "Unknown error"
                )
                return FormResult(
                    success=False,
                    form_id=form_id,
                    message=f"Creation failed: {error_msg}",
                    errors=[error_msg],
                    raw_data=create_result,
                )

        except json.JSONDecodeError as e:
            return FormResult(
                success=False,
                form_id=form_id,
                message=f"Invalid JSON: {e}",
                errors=[str(e)],
            )
        except Exception as e:
            return FormResult(
                success=False,
                form_id=form_id,
                message=str(e),
                errors=[str(e)],
            )
