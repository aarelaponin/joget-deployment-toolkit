"""
MDM deployment orchestration.

Coordinates form creation and data population for MDM (Master Data Management) forms.

Workflow:
1. Create form via formCreator plugin (with optional API endpoint and CRUD)
2. Query auto-generated API ID from database
3. Load CSV data and strip infrastructure fields
4. Submit data via Joget API
5. Report detailed results

Example:
    >>> from joget_deployment_toolkit import JogetClient
    >>> from joget_deployment_toolkit.operations import MDMDataDeployer
    >>> from pathlib import Path
    >>>
    >>> client = JogetClient.from_instance("jdx4")
    >>> deployer = MDMDataDeployer(client)
    >>>
    >>> result = deployer.deploy_mdm_form_with_data(
    ...     form_id="md01maritalStatus",
    ...     form_name="MD.01 - Marital Status",
    ...     form_definition=form_def,
    ...     csv_file=Path("config/metadata/md01maritalStatus.csv"),
    ...     target_app_id="farmersPortal",
    ...     formcreator_api_id="fc_api"
    ... )
    >>>
    >>> if result.success:
    ...     print(f"✓ {result.form_id}: {result.records_submitted} records")
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..loaders.csv_loader import CSVDataLoader

logger = logging.getLogger(__name__)


@dataclass
class MDMDeploymentResult:
    """Result of MDM deployment operation."""

    form_id: str
    form_created: bool
    form_message: str
    api_id: str | None = None
    records_submitted: int = 0
    records_failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if deployment was completely successful."""
        return self.form_created and self.records_failed == 0

    @property
    def total_records(self) -> int:
        """Total records attempted."""
        return self.records_submitted + self.records_failed

    @property
    def partial_success(self) -> bool:
        """Check if deployment was partially successful."""
        return self.form_created and self.records_submitted > 0

    def __str__(self) -> str:
        if self.success:
            return f"✓ {self.form_id}: {self.records_submitted} records"
        elif self.partial_success:
            return (
                f"⚠ {self.form_id}: {self.records_submitted}/{self.total_records} "
                f"records (partial success)"
            )
        else:
            error_msg = self.errors[0] if self.errors else "unknown error"
            return f"✗ {self.form_id}: {error_msg}"


class MDMDataDeployer:
    """
    Orchestrate MDM form deployment with data population.

    This class provides high-level orchestration for deploying Master Data
    Management forms to Joget instances. It handles the complete workflow:
    - Form creation via formCreator plugin
    - API endpoint generation
    - CRUD datalist creation
    - Data population from CSV files

    The deployer automatically handles:
    - Infrastructure field stripping from CSV data
    - API ID discovery from database
    - Progress tracking for batch operations
    - Detailed error reporting

    Example:
        >>> deployer = MDMDataDeployer(client)
        >>> results = deployer.deploy_all_mdm_from_directory(
        ...     forms_dir=Path("config/metadata_forms"),
        ...     data_dir=Path("config/metadata"),
        ...     target_app_id="farmersPortal",
        ...     formcreator_api_id="fc_api"
        ... )
        >>> successful = sum(1 for r in results if r.success)
        >>> print(f"Deployed {successful}/{len(results)} MDM forms")
    """

    def __init__(self, client):
        """
        Initialize deployer with Joget client.

        Args:
            client: JogetClient instance (from_instance() recommended)

        Example:
            >>> from joget_deployment_toolkit import JogetClient
            >>> client = JogetClient.from_instance("jdx4")
            >>> deployer = MDMDataDeployer(client)
        """
        self.client = client
        self.logger = logging.getLogger(__name__)

    def deploy_mdm_form_with_data(
        self,
        form_id: str,
        form_name: str,
        form_definition: dict[str, Any],
        csv_file: Path,
        *,
        target_app_id: str,
        target_app_version: str = "1",
        formcreator_api_id: str,
        formcreator_api_key: str | None = None,
        create_crud: bool = True,
        create_api_endpoint: bool = True,
        dry_run: bool = False,
    ) -> MDMDeploymentResult:
        """
        Deploy single MDM form with data.

        Complete workflow:
        1. Create form via formCreator plugin
        2. Query auto-generated API ID from database (if create_api_endpoint=True)
        3. Load CSV data with infrastructure field stripping
        4. Submit data via Joget API

        Args:
            form_id: Form identifier (e.g., "md01maritalStatus")
            form_name: Display name (e.g., "MD.01 - Marital Status")
            form_definition: Form JSON definition
            csv_file: Path to CSV file with data
            target_app_id: Target application ID
            target_app_version: Application version (default: "1")
            formcreator_api_id: API ID for formCreator endpoint
            create_crud: Create CRUD datalist (default: True)
            create_api_endpoint: Create API endpoint (default: True)
            dry_run: Preview actions without executing (default: False)

        Returns:
            MDMDeploymentResult with detailed status

        Example:
            >>> result = deployer.deploy_mdm_form_with_data(
            ...     form_id="md01maritalStatus",
            ...     form_name="MD.01 - Marital Status",
            ...     form_definition=form_def,
            ...     csv_file=Path("config/metadata/md01maritalStatus.csv"),
            ...     target_app_id="farmersPortal",
            ...     formcreator_api_id="fc_api"
            ... )
            >>> print(result)
        """
        result = MDMDeploymentResult(
            form_id=form_id, form_created=False, form_message=""
        )

        if dry_run:
            self.logger.info(f"[DRY RUN] Would deploy form: {form_id}")
            result.form_created = True
            result.form_message = "[DRY RUN] Skipped"
            return result

        # Step 1: Create form with API endpoint
        self.logger.info(f"Creating form: {form_id}...")

        try:
            # Check if client has create_form method
            if not hasattr(self.client, "create_form"):
                raise AttributeError(
                    "Client does not have create_form() method. "
                    "Ensure formCreator plugin integration is available."
                )

            create_result = self.client.create_form(
                payload={
                    "target_app_id": target_app_id,
                    "target_app_version": target_app_version,
                    "form_id": form_id,
                    "form_name": form_name,
                    "table_name": form_id,  # Use form_id as table name
                    # NOTE: Do NOT include 'form_definition_json' here!
                    # The empty string would overwrite the file upload reference in the database,
                    # causing the FormCreator post-processor plugin to fail silently.
                    # The form definition is uploaded as a file (see create_form method).
                    "create_api_endpoint": "yes" if create_api_endpoint else "no",
                    "create_crud": "yes" if create_crud else "no",
                },
                form_definition=form_definition,  # Pass form definition separately
                api_id=formcreator_api_id,
                api_key=formcreator_api_key,
            )

            # FormCreator API returns: {"id": "uuid", "errors": {}}
            # Success = has ID and no errors
            has_id = bool(create_result.get("id"))
            has_errors = bool(create_result.get("errors"))

            result.form_created = has_id and not has_errors
            result.form_message = f"Form created with ID: {create_result.get('id', 'N/A')}"

            if not result.form_created:
                errors = create_result.get("errors", {})
                error_msg = "; ".join(f"{k}: {v}" for k, v in errors.items()) if errors else "Unknown error"
                result.errors.append(f"Form creation failed: {error_msg}")
                return result

            self.logger.info(f"Form created successfully: {form_id} (ID: {create_result.get('id')})")

        except Exception as e:
            result.errors.append(f"Form creation error: {e}")
            self.logger.error(f"Failed to create form {form_id}: {e}")
            return result

        # Step 2: Get API ID (if API endpoint was created)
        if create_api_endpoint:
            self.logger.info(f"Querying API ID for {form_id}...")

            try:
                # Check if client has get_api_id_for_form method
                if hasattr(self.client, "get_api_id_for_form"):
                    api_id = self.client.get_api_id_for_form(
                        app_id=target_app_id,
                        api_name=f"api_{form_id}",
                        app_version=target_app_version,
                    )

                    if not api_id:
                        result.errors.append("API ID not found after form creation")
                        self.logger.warning(
                            f"API ID not found for {form_id}. Data submission will be skipped."
                        )
                        return result

                    result.api_id = api_id
                    self.logger.info(f"Found API ID: {api_id}")
                else:
                    self.logger.warning(
                        "Client does not have get_api_id_for_form() method. "
                        "Skipping data submission."
                    )
                    result.errors.append("API ID query not available")
                    return result

            except Exception as e:
                result.errors.append(f"API ID query error: {e}")
                self.logger.error(f"Failed to get API ID for {form_id}: {e}")
                return result
        else:
            self.logger.info("API endpoint creation disabled. Skipping data submission.")
            return result

        # Step 3: Load CSV data
        self.logger.info(f"Loading data from {csv_file.name}...")

        try:
            records = CSVDataLoader.load_csv(
                csv_file, strip_infrastructure=True  # Remove id, dateCreated, etc.
            )

            if not records:
                self.logger.warning(f"No data to import for {form_id}")
                return result

            self.logger.info(f"Loaded {len(records)} records")

        except Exception as e:
            result.errors.append(f"CSV loading error: {e}")
            self.logger.error(f"Failed to load CSV for {form_id}: {e}")
            return result

        # Step 4: Submit data
        self.logger.info(f"Submitting {len(records)} records...")

        try:
            # Check if client has submit_form_data_batch method
            if not hasattr(self.client, "submit_form_data_batch"):
                raise AttributeError(
                    "Client does not have submit_form_data_batch() method. "
                    "Ensure DataOperations mixin is included."
                )

            submission_results = self.client.submit_form_data_batch(
                form_id=form_id,
                records=records,
                api_id=result.api_id,
                progress_callback=self._progress_callback,
            )

            # Count successes and failures
            result.records_submitted = sum(1 for r in submission_results if r.success)
            result.records_failed = sum(1 for r in submission_results if not r.success)

            # Collect error messages (limit to first 5)
            for i, r in enumerate(submission_results):
                if not r.success and i < 5:
                    result.errors.append(f"Record {i+1} failed: {r.message}")

            if result.records_failed > 5:
                result.errors.append(
                    f"... and {result.records_failed - 5} more failed records"
                )

            self.logger.info(
                f"Submitted {result.records_submitted}/{result.total_records} "
                f"records for {form_id}"
            )

        except Exception as e:
            result.errors.append(f"Data submission error: {e}")
            self.logger.error(f"Failed to submit data for {form_id}: {e}")

        return result

    def deploy_all_mdm_from_directory(
        self,
        forms_dir: Path,
        data_dir: Path,
        *,
        target_app_id: str,
        target_app_version: str = "1",
        formcreator_api_id: str,
        formcreator_api_key: str | None = None,
        create_crud: bool = True,
        create_api_endpoint: bool = True,
        dry_run: bool = False,
    ) -> list[MDMDeploymentResult]:
        """
        Deploy all MDM forms from directories.

        Expects:
        - forms_dir: Directory with form JSON files (md*.json)
        - data_dir: Directory with CSV data files (md*.csv)

        Args:
            forms_dir: Directory containing form JSON definitions
            data_dir: Directory containing CSV data files
            target_app_id: Target application ID
            target_app_version: Application version (default: "1")
            formcreator_api_id: API ID for formCreator endpoint
            create_crud: Create CRUD datalists (default: True)
            create_api_endpoint: Create API endpoints (default: True)
            dry_run: Preview actions without executing (default: False)

        Returns:
            List of MDMDeploymentResult for each form

        Example:
            >>> results = deployer.deploy_all_mdm_from_directory(
            ...     forms_dir=Path("config/metadata_forms"),
            ...     data_dir=Path("config/metadata"),
            ...     target_app_id="farmersPortal",
            ...     formcreator_api_id="fc_api"
            ... )
            >>> successful = sum(1 for r in results if r.success)
            >>> print(f"Deployed {successful}/{len(results)} MDM forms")
        """
        results = []

        # Find all form JSON files
        form_files = sorted(forms_dir.glob("md*.json"))

        if not form_files:
            self.logger.warning(f"No form files found in {forms_dir}")
            return results

        self.logger.info(f"Deploying {len(form_files)} MDM forms...")

        for form_file in form_files:
            form_id = form_file.stem
            csv_file = data_dir / f"{form_id}.csv"

            # Skip if no CSV data
            if not csv_file.exists():
                self.logger.warning(f"No CSV data for {form_id}, skipping")
                continue

            # Load form definition
            try:
                with open(form_file, encoding="utf-8") as f:
                    form_def = json.load(f)

                form_name = form_def.get("properties", {}).get("name", form_id)

            except Exception as e:
                self.logger.error(f"Failed to load form definition {form_file}: {e}")
                results.append(
                    MDMDeploymentResult(
                        form_id=form_id,
                        form_created=False,
                        form_message=f"Failed to load form definition: {e}",
                        errors=[str(e)],
                    )
                )
                continue

            # Deploy form with data
            result = self.deploy_mdm_form_with_data(
                form_id=form_id,
                form_name=form_name,
                form_definition=form_def,
                csv_file=csv_file,
                target_app_id=target_app_id,
                target_app_version=target_app_version,
                formcreator_api_id=formcreator_api_id,
                formcreator_api_key=formcreator_api_key,
                create_crud=create_crud,
                create_api_endpoint=create_api_endpoint,
                dry_run=dry_run,
            )

            results.append(result)

            # Log result
            self.logger.info(str(result))

        # Summary
        successful = sum(1 for r in results if r.success)
        partial = sum(1 for r in results if r.partial_success and not r.success)
        failed = sum(1 for r in results if not r.form_created)

        self.logger.info(
            f"Deployment complete: {successful} successful, "
            f"{partial} partial, {failed} failed"
        )

        return results

    def _progress_callback(self, current: int, total: int, result):
        """Progress callback for batch operations."""
        if result.success:
            self.logger.debug(f"  [{current}/{total}] ✓ {result.record_id}")
        else:
            self.logger.debug(f"  [{current}/{total}] ✗ {result.message}")
