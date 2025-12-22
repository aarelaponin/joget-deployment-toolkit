"""
Instance migration orchestration.

Coordinates migration of forms, datalists, data, and userview menus between
Joget instances.

Example:
    >>> from joget_deployment_toolkit import JogetClient
    >>> from joget_deployment_toolkit.operations import InstanceMigrator
    >>>
    >>> source = JogetClient.from_instance('jdx3')
    >>> target = JogetClient.from_instance('jdx4')
    >>>
    >>> migrator = InstanceMigrator(source, target)
    >>> result = migrator.migrate_app_component(
    ...     source_app_id='subsidyApplication',
    ...     target_app_id='farmersPortal',
    ...     pattern='md%',
    ...     with_data=True,
    ...     userview_id='v',
    ...     category_label='Master Data'
    ... )
    >>> print(result)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from ..database import DatabaseConnectionPool
from ..database.repositories import DatalistRepository, FormRepository, UserviewRepository
from ..models import MigrationResult

logger = logging.getLogger(__name__)


@dataclass
class MigrationAnalysis:
    """Analysis result before migration."""

    forms_to_migrate: list[str] = field(default_factory=list)
    datalists_to_migrate: list[str] = field(default_factory=list)
    existing_forms: list[str] = field(default_factory=list)
    existing_datalists: list[str] = field(default_factory=list)
    existing_menus: list[str] = field(default_factory=list)
    category_found: bool = False
    category_label: str = ""
    data_records: dict[str, int] = field(default_factory=dict)

    def __str__(self):
        return (
            f"Migration Analysis:\n"
            f"  Forms to migrate: {len(self.forms_to_migrate)}\n"
            f"  Datalists to migrate: {len(self.datalists_to_migrate)}\n"
            f"  Already in target (forms): {len(self.existing_forms)}\n"
            f"  Already in target (datalists): {len(self.existing_datalists)}\n"
            f"  Category '{self.category_label}' found: {self.category_found}\n"
            f"  Data records: {sum(self.data_records.values())}"
        )


class InstanceMigrator:
    """
    Orchestrate migration of components between Joget instances.

    This class provides high-level orchestration for migrating forms,
    datalists, data, and userview menus from one Joget instance to another.

    Migration order (critical for dependencies):
    1. Forms first (no dependencies)
    2. Data tables (depend on forms existing)
    3. Datalists (reference forms)
    4. Userview menus (reference datalists + forms)

    Example:
        >>> source = JogetClient.from_instance('jdx3')
        >>> target = JogetClient.from_instance('jdx4')
        >>> migrator = InstanceMigrator(source, target)
        >>>
        >>> # Analyze first
        >>> analysis = migrator.analyze(
        ...     source_app_id='subsidyApplication',
        ...     target_app_id='farmersPortal',
        ...     pattern='md%'
        ... )
        >>> print(analysis)
        >>>
        >>> # Then migrate
        >>> result = migrator.migrate_app_component(
        ...     source_app_id='subsidyApplication',
        ...     target_app_id='farmersPortal',
        ...     pattern='md%',
        ...     with_data=True,
        ...     userview_id='v',
        ...     category_label='Master Data'
        ... )
    """

    def __init__(self, source_client, target_client):
        """
        Initialize migrator with source and target clients.

        Args:
            source_client: JogetClient for source instance
            target_client: JogetClient for target instance

        Example:
            >>> source = JogetClient.from_instance('jdx3')
            >>> target = JogetClient.from_instance('jdx4')
            >>> migrator = InstanceMigrator(source, target)
        """
        self.source = source_client
        self.target = target_client
        self.logger = logging.getLogger(__name__)

        # Create repositories if database config available
        self._source_pool = None
        self._target_pool = None
        self._source_form_repo = None
        self._target_form_repo = None
        self._source_datalist_repo = None
        self._target_datalist_repo = None
        self._target_userview_repo = None

    def _ensure_source_repos(self):
        """Initialize source database repositories if not already done."""
        if self._source_pool is not None:
            return

        if not hasattr(self.source.config, 'db_config') or not self.source.config.db_config:
            raise ValueError(
                "Source client does not have database configuration. "
                "Use from_instance() with proper database config."
            )

        self._source_pool = DatabaseConnectionPool(self.source.config.db_config)
        self._source_form_repo = FormRepository(self._source_pool)
        self._source_datalist_repo = DatalistRepository(self._source_pool)

    def _ensure_target_repos(self):
        """Initialize target database repositories if not already done."""
        if self._target_pool is not None:
            return

        if not hasattr(self.target.config, 'db_config') or not self.target.config.db_config:
            raise ValueError(
                "Target client does not have database configuration. "
                "Use from_instance() with proper database config."
            )

        self._target_pool = DatabaseConnectionPool(self.target.config.db_config)
        self._target_form_repo = FormRepository(self._target_pool)
        self._target_datalist_repo = DatalistRepository(self._target_pool)
        self._target_userview_repo = UserviewRepository(self._target_pool)

    def analyze(
        self,
        source_app_id: str,
        target_app_id: str,
        pattern: str | None = None,
        *,
        source_app_version: str = "1",
        target_app_version: str = "1",
        userview_id: str | None = None,
        category_label: str | None = None,
    ) -> MigrationAnalysis:
        """
        Analyze what would be migrated without making changes.

        Args:
            source_app_id: Source application ID
            target_app_id: Target application ID
            pattern: Form ID pattern to filter (e.g., 'md%')
            source_app_version: Source app version
            target_app_version: Target app version
            userview_id: Optional userview ID to check for category
            category_label: Optional category label to check

        Returns:
            MigrationAnalysis with details of what would be migrated
        """
        self._ensure_source_repos()
        self._ensure_target_repos()

        analysis = MigrationAnalysis()
        analysis.category_label = category_label or ""

        # Get source forms
        if pattern:
            # Convert % to SQL LIKE pattern
            source_forms = self._source_form_repo.find_by_app(source_app_id, source_app_version)
            source_forms = [f for f in source_forms if f.form_id.startswith(pattern.rstrip('%'))]
        else:
            source_forms = self._source_form_repo.find_by_app(source_app_id, source_app_version)

        # Get target forms
        target_forms = self._target_form_repo.find_by_app(target_app_id, target_app_version)
        target_form_ids = {f.form_id for f in target_forms}

        # Categorize forms
        for form in source_forms:
            if form.form_id in target_form_ids:
                analysis.existing_forms.append(form.form_id)
            else:
                analysis.forms_to_migrate.append(form.form_id)

        # Get source datalists
        if pattern:
            datalist_pattern = f"list_{pattern.rstrip('%')}%"
            source_datalists = self._source_datalist_repo.find_by_pattern(
                source_app_id, datalist_pattern, source_app_version
            )
        else:
            source_datalists = self._source_datalist_repo.find_by_app(
                source_app_id, source_app_version
            )

        # Get target datalists
        target_datalists = self._target_datalist_repo.find_by_app(
            target_app_id, target_app_version
        )
        target_datalist_ids = {dl.id for dl in target_datalists}

        # Categorize datalists
        for dl in source_datalists:
            if dl.id in target_datalist_ids:
                analysis.existing_datalists.append(dl.id)
            else:
                analysis.datalists_to_migrate.append(dl.id)

        # Check userview category
        if userview_id and category_label:
            category = self._target_userview_repo.find_category(
                target_app_id, userview_id, category_label, target_app_version
            )
            analysis.category_found = category is not None

            if category:
                existing_form_ids = self._target_userview_repo.get_existing_form_ids_in_category(
                    target_app_id, userview_id, category_label, target_app_version
                )
                analysis.existing_menus = list(existing_form_ids)

        return analysis

    def migrate_app_component(
        self,
        source_app_id: str,
        target_app_id: str,
        pattern: str | None = None,
        *,
        source_app_version: str = "1",
        target_app_version: str = "1",
        with_data: bool = False,
        userview_id: str | None = None,
        category_label: str | None = None,
        skip_existing: bool = True,
        dry_run: bool = False,
    ) -> MigrationResult:
        """
        Migrate components between instances.

        Handles:
        1. Forms (app_form) - with optional pattern filter
        2. Datalists (app_datalist) - matching forms
        3. Data tables (app_fd_*) - if with_data=True
        4. Userview menus - adds to existing category (if specified)

        Args:
            source_app_id: Source application ID
            target_app_id: Target application ID
            pattern: Form ID pattern to filter (e.g., 'md%')
            source_app_version: Source app version
            target_app_version: Target app version
            with_data: Copy data tables (default: False)
            userview_id: Userview ID for menu creation
            category_label: Category label for menu creation (required if userview_id set)
            skip_existing: Skip components that already exist in target
            dry_run: Analyze only, don't make changes

        Returns:
            MigrationResult with counts and any errors

        Raises:
            ValueError: If category specified but doesn't exist in target

        Example:
            >>> result = migrator.migrate_app_component(
            ...     source_app_id='subsidyApplication',
            ...     target_app_id='farmersPortal',
            ...     pattern='md%',
            ...     with_data=True,
            ...     userview_id='v',
            ...     category_label='Master Data'
            ... )
            >>> print(f"Migrated {result.forms_migrated} forms")
        """
        self._ensure_source_repos()
        self._ensure_target_repos()

        result = MigrationResult(success=True)

        # Validate category if userview specified
        if userview_id and category_label:
            if not self._target_userview_repo.find_category(
                target_app_id, userview_id, category_label, target_app_version
            ):
                result.success = False
                result.errors.append(
                    f"Category '{category_label}' not found in userview '{userview_id}'. "
                    f"Please create the category in Joget UI first, then re-run migration."
                )
                return result

        if dry_run:
            analysis = self.analyze(
                source_app_id, target_app_id, pattern,
                source_app_version=source_app_version,
                target_app_version=target_app_version,
                userview_id=userview_id,
                category_label=category_label,
            )
            self.logger.info(f"[DRY RUN] {analysis}")
            result.forms_migrated = len(analysis.forms_to_migrate)
            result.datalists_migrated = len(analysis.datalists_to_migrate)
            return result

        # Step 1: Migrate forms
        self.logger.info("Step 1: Migrating forms...")
        forms_migrated = self._migrate_forms(
            source_app_id, target_app_id, pattern,
            source_app_version=source_app_version,
            target_app_version=target_app_version,
            skip_existing=skip_existing,
            with_data=with_data,
        )
        result.forms_migrated = forms_migrated["count"]
        result.data_records_copied = forms_migrated.get("data_records", 0)
        if forms_migrated.get("errors"):
            result.errors.extend(forms_migrated["errors"])

        # Step 2: Migrate datalists
        self.logger.info("Step 2: Migrating datalists...")
        datalists_migrated = self._migrate_datalists(
            source_app_id, target_app_id, pattern,
            source_app_version=source_app_version,
            target_app_version=target_app_version,
            skip_existing=skip_existing,
        )
        result.datalists_migrated = datalists_migrated["count"]
        if datalists_migrated.get("errors"):
            result.errors.extend(datalists_migrated["errors"])

        # Step 3: Add userview menus
        if userview_id and category_label:
            self.logger.info("Step 3: Adding userview menus...")
            menus_added = self._add_userview_menus(
                source_app_id, target_app_id, pattern,
                userview_id=userview_id,
                category_label=category_label,
                source_app_version=source_app_version,
                target_app_version=target_app_version,
            )
            result.menus_added = menus_added["count"]
            if menus_added.get("errors"):
                result.errors.extend(menus_added["errors"])
            if menus_added.get("warnings"):
                result.warnings.extend(menus_added["warnings"])

        # Set success based on errors
        result.success = len(result.errors) == 0

        self.logger.info(f"Migration complete: {result}")

        return result

    def _migrate_forms(
        self,
        source_app_id: str,
        target_app_id: str,
        pattern: str | None,
        *,
        source_app_version: str,
        target_app_version: str,
        skip_existing: bool,
        with_data: bool,
    ) -> dict[str, Any]:
        """Migrate form definitions and optionally data."""
        result = {"count": 0, "data_records": 0, "errors": []}

        # Get source forms
        source_forms = self._source_form_repo.find_by_app(source_app_id, source_app_version)
        if pattern:
            prefix = pattern.rstrip('%')
            source_forms = [f for f in source_forms if f.form_id.startswith(prefix)]

        # Get existing target forms
        target_forms = self._target_form_repo.find_by_app(target_app_id, target_app_version)
        target_form_ids = {f.form_id for f in target_forms}

        for form in source_forms:
            if skip_existing and form.form_id in target_form_ids:
                self.logger.debug(f"Skipping existing form: {form.form_id}")
                continue

            try:
                # Get form definition
                form_def = self._source_form_repo.get_form_definition(
                    source_app_id, source_app_version, form.form_id
                )
                if not form_def:
                    result["errors"].append(f"Could not load form definition: {form.form_id}")
                    continue

                # Use API to create/update form in target
                if form.form_id in target_form_ids:
                    self.target.update_form(
                        target_app_id, form.form_id, form_def,
                        app_version=target_app_version
                    )
                else:
                    # For new forms, we need to use formCreator or direct database
                    # For now, use the form repository's direct insert
                    self._copy_form_via_db(
                        source_app_id, source_app_version, form.form_id,
                        target_app_id, target_app_version
                    )

                result["count"] += 1
                self.logger.debug(f"Migrated form: {form.form_id}")

                # Copy data if requested
                if with_data:
                    records = self._copy_form_data(
                        form.table_name,
                        source_app_id,
                        target_app_id
                    )
                    result["data_records"] += records

            except Exception as e:
                result["errors"].append(f"Error migrating form {form.form_id}: {e}")
                self.logger.error(f"Error migrating form {form.form_id}: {e}")

        return result

    def _copy_form_via_db(
        self,
        source_app_id: str,
        source_app_version: str,
        form_id: str,
        target_app_id: str,
        target_app_version: str,
    ):
        """Copy form definition directly via database."""
        # Get source form details
        query = """
            SELECT formId, name, tableName, json, description
            FROM app_form
            WHERE appId = %s AND appVersion = %s AND formId = %s
        """
        results = self._source_form_repo.execute_query(
            query, (source_app_id, source_app_version, form_id)
        )

        if not results:
            raise ValueError(f"Form not found: {form_id}")

        row = results[0]

        # Delete if exists in target
        delete_query = """
            DELETE FROM app_form
            WHERE appId = %s AND appVersion = %s AND formId = %s
        """
        self._target_form_repo.execute_update(
            delete_query, (target_app_id, target_app_version, form_id)
        )

        # Insert into target
        insert_query = """
            INSERT INTO app_form (appId, appVersion, formId, name, tableName, json, dateCreated, dateModified, description)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
        """
        self._target_form_repo.execute_update(
            insert_query,
            (
                target_app_id, target_app_version,
                row["formId"], row["name"], row["tableName"],
                row["json"], row.get("description", "")
            )
        )

    def _copy_form_data(self, table_name: str, source_app_id: str, target_app_id: str) -> int:
        """Copy data from source table to target."""
        full_table_name = f"app_fd_{table_name}"

        # Check if source table exists
        if not self._source_form_repo.check_table_exists(full_table_name):
            return 0

        try:
            # Get source table structure
            show_create = self._source_form_repo.execute_query(
                f"SHOW CREATE TABLE {full_table_name}"
            )
            if not show_create:
                return 0

            create_stmt = show_create[0].get("Create Table", "")

            # Drop and recreate in target
            self._target_form_repo.execute_update(f"DROP TABLE IF EXISTS {full_table_name}")
            self._target_form_repo.execute_update(create_stmt)

            # Get source data
            source_data = self._source_form_repo.execute_query(f"SELECT * FROM {full_table_name}")
            if not source_data:
                return 0

            # Get column names
            columns = list(source_data[0].keys())
            placeholders = ", ".join(["%s"] * len(columns))
            col_names = ", ".join([f"`{c}`" for c in columns])

            # Insert data
            insert_query = f"INSERT INTO {full_table_name} ({col_names}) VALUES ({placeholders})"

            count = 0
            for row in source_data:
                values = [row[col] for col in columns]
                try:
                    self._target_form_repo.execute_update(insert_query, tuple(values))
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Error inserting row: {e}")

            return count

        except Exception as e:
            self.logger.error(f"Error copying data for {table_name}: {e}")
            return 0

    def _migrate_datalists(
        self,
        source_app_id: str,
        target_app_id: str,
        pattern: str | None,
        *,
        source_app_version: str,
        target_app_version: str,
        skip_existing: bool,
    ) -> dict[str, Any]:
        """Migrate datalist definitions."""
        result = {"count": 0, "errors": []}

        # Get source datalists
        if pattern:
            datalist_pattern = f"list_{pattern.rstrip('%')}%"
            source_datalists = self._source_datalist_repo.find_by_pattern(
                source_app_id, datalist_pattern, source_app_version
            )
        else:
            source_datalists = self._source_datalist_repo.find_by_app(
                source_app_id, source_app_version
            )

        # Get existing target datalists
        target_datalists = self._target_datalist_repo.find_by_app(
            target_app_id, target_app_version
        )
        target_datalist_ids = {dl.id for dl in target_datalists}

        for dl in source_datalists:
            if skip_existing and dl.id in target_datalist_ids:
                self.logger.debug(f"Skipping existing datalist: {dl.id}")
                continue

            try:
                # Copy datalist via repository
                success = self._source_datalist_repo.copy_datalist(
                    source_app_id, source_app_version, dl.id,
                    target_app_id, target_app_version
                )

                if success:
                    result["count"] += 1
                    self.logger.debug(f"Migrated datalist: {dl.id}")
                else:
                    result["errors"].append(f"Failed to copy datalist: {dl.id}")

            except Exception as e:
                result["errors"].append(f"Error migrating datalist {dl.id}: {e}")
                self.logger.error(f"Error migrating datalist {dl.id}: {e}")

        return result

    def _add_userview_menus(
        self,
        source_app_id: str,
        target_app_id: str,
        pattern: str | None,
        *,
        userview_id: str,
        category_label: str,
        source_app_version: str,
        target_app_version: str,
    ) -> dict[str, Any]:
        """Add CRUD menus to userview category."""
        result = {"count": 0, "errors": [], "warnings": []}

        # Get forms to create menus for
        source_forms = self._source_form_repo.find_by_app(source_app_id, source_app_version)
        if pattern:
            prefix = pattern.rstrip('%')
            source_forms = [f for f in source_forms if f.form_id.startswith(prefix)]

        # Get existing menus in category
        existing_form_ids = self._target_userview_repo.get_existing_form_ids_in_category(
            target_app_id, userview_id, category_label, target_app_version
        )

        # Get existing datalists in target to validate menu creation
        target_datalists = self._target_datalist_repo.find_by_app(
            target_app_id, target_app_version
        )
        target_datalist_ids = {dl.id for dl in target_datalists}

        # Create menu configs for forms not already in category
        menus_to_add = []
        for form in source_forms:
            if form.form_id in existing_form_ids:
                continue

            # Validate datalist exists before creating menu
            datalist_id = f"list_{form.form_id}"
            if datalist_id not in target_datalist_ids:
                warning = (
                    f"Skipping menu for '{form.form_id}': "
                    f"datalist '{datalist_id}' not found in target. "
                    f"Migrate datalist first or create it manually."
                )
                result["warnings"].append(warning)
                self.logger.warning(warning)
                continue

            menu = self.target.create_crud_menu(
                form_id=form.form_id,
                form_name=form.form_name,
                datalist_id=datalist_id,
            )
            menus_to_add.append(menu)

        if menus_to_add:
            try:
                added = self._target_userview_repo.add_menus_to_category(
                    target_app_id, userview_id, category_label,
                    menus_to_add, target_app_version
                )
                result["count"] = added
                self.logger.info(f"Added {added} menus to category '{category_label}'")
            except Exception as e:
                result["errors"].append(f"Error adding menus: {e}")
                self.logger.error(f"Error adding menus: {e}")

        return result


__all__ = ["InstanceMigrator", "MigrationAnalysis"]
