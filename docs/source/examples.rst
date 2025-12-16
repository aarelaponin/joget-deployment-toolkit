Examples
========

This page contains practical examples of using Joget Toolkit.

Batch Application Export
-------------------------

Export multiple applications in parallel::

    from joget_deployment_toolkit import JogetClient
    from pathlib import Path

    client = JogetClient.from_env()

    # List all applications
    apps = client.list_applications()

    # Batch export
    app_ids = [app.id for app in apps]
    results = client.batch_export_applications(
        app_ids=app_ids,
        output_dir=Path("exports"),
        app_version="1"
    )

    print(f"Exported {results.successful}/{results.total} applications")
    if results.failed > 0:
        print("Failures:")
        for error in results.errors:
            print(f"  - {error}")

Migration Workflow
------------------

Export from one instance, import to another::

    from joget_deployment_toolkit import JogetClient
    from pathlib import Path

    # Source instance
    source = JogetClient.from_credentials(
        base_url="http://source:8080/jw",
        username="admin",
        password="admin"
    )

    # Target instance
    target = JogetClient.from_credentials(
        base_url="http://target:8080/jw",
        username="admin",
        password="admin"
    )

    # Export from source
    export_result = source.export_application(
        app_id="myApp",
        output_path=Path("temp/myApp.zip")
    )

    if export_result.success:
        # Import to target
        import_result = target.import_application(
            zip_path=Path("temp/myApp.zip"),
            overwrite=True
        )

        if import_result.success:
            print(f"Migration complete: {import_result.app_id} v{import_result.app_version}")
        else:
            print(f"Import failed: {import_result.message}")

Form Analysis
-------------

Analyze forms across an application::

    from joget_deployment_toolkit import FormDiscovery
    from joget_deployment_toolkit.models import DatabaseConfig
    import json

    db_config = DatabaseConfig(
        host="localhost",
        port=3306,
        database="jwdb",
        user="root",
        password="password"
    )

    with FormDiscovery(client, db_config) as discovery:
        forms = discovery.discover_all_forms("myApp", "1")

        print(f"Found {len(forms)} forms in myApp")

        # Extract definitions
        definitions = discovery.extract_form_definitions(forms)

        # Analyze field types
        field_counts = {}
        for form_id, definition in definitions.items():
            elements = definition.get("elements", [])
            for element in elements:
                class_name = element.get("className", "unknown")
                field_counts[class_name] = field_counts.get(class_name, 0) + 1

        print("\\nField type distribution:")
        for field_type, count in sorted(field_counts.items()):
            print(f"  {field_type}: {count}")

Health Monitoring
-----------------

Monitor multiple instances::

    from joget_deployment_toolkit import JogetClient
    from joget_deployment_toolkit.models import HealthStatus

    instances = [
        ("Production", "http://prod:8080/jw"),
        ("Staging", "http://staging:8080/jw"),
        ("Development", "http://dev:8080/jw"),
    ]

    for name, url in instances:
        client = JogetClient.from_credentials(
            base_url=url,
            username="admin",
            password="admin"
        )

        health = client.get_health_status()

        status_icon = {
            HealthStatus.HEALTHY: "✓",
            HealthStatus.DEGRADED: "⚠",
            HealthStatus.UNHEALTHY: "✗"
        }[health.status]

        print(f"{status_icon} {name}: {health.status.value}")
        if health.version:
            print(f"  Version: {health.version}")

Custom Repository
-----------------

Create a custom repository for specific queries::

    from joget_deployment_toolkit.database.repositories import BaseRepository
    from typing import List, Dict, Any

    class CustomFormRepository(BaseRepository):
        """Custom repository with business-specific queries."""

        def find_forms_with_api(self, app_id: str) -> List[Dict[str, Any]]:
            """Find forms that have API endpoints."""
            query = \"\"\"
                SELECT af.formId, af.name, af.tableName, ae.api_id, ae.api_key
                FROM app_form af
                INNER JOIN app_api_endpoint ae
                    ON af.formId = ae.form_id
                    AND af.appId = ae.app_id
                    AND af.appVersion = ae.app_version
                WHERE af.appId = %s
                ORDER BY af.name
            \"\"\"
            return self.execute_query(query, (app_id,))

        def get_form_usage_stats(self, table_name: str) -> Dict[str, Any]:
            """Get usage statistics for a form table."""
            count_query = f"SELECT COUNT(*) as total FROM {table_name}"
            date_query = f\"\"\"
                SELECT
                    MIN(dateCreated) as first_entry,
                    MAX(dateModified) as last_modified
                FROM {table_name}
            \"\"\"

            count_result = self.execute_scalar(count_query)
            date_result = self.execute_query(date_query)

            return {
                'total_records': count_result,
                'first_entry': date_result[0].get('first_entry') if date_result else None,
                'last_modified': date_result[0].get('last_modified') if date_result else None
            }

    # Usage
    pool = DatabaseConnectionPool(db_config)
    custom_repo = CustomFormRepository(pool)

    forms_with_api = custom_repo.find_forms_with_api("myApp")
    for form in forms_with_api:
        print(f"{form['formId']}: {form['api_id']}")

Transaction Management
----------------------

Use transactions for atomic operations::

    from joget_deployment_toolkit.database import DatabaseConnectionPool
    from joget_deployment_toolkit.database.repositories import BaseRepository

    class DataMigrationRepo(BaseRepository):
        def migrate_data(self, source_table: str, target_table: str):
            \"\"\"Migrate data between tables atomically.\"\"\"
            with self.transaction() as conn:
                cursor = conn.cursor(buffered=True)

                # Copy data
                copy_query = f"INSERT INTO {target_table} SELECT * FROM {source_table}"
                cursor.execute(copy_query)

                # Archive source
                archive_query = f"UPDATE {source_table} SET archived = 1"
                cursor.execute(archive_query)

                # If anything fails, the whole transaction rolls back

    pool = DatabaseConnectionPool(db_config)
    migration_repo = DataMigrationRepo(pool)

    try:
        migration_repo.migrate_data("app_fd_old_customer", "app_fd_customer")
        print("Migration successful")
    except Exception as e:
        print(f"Migration failed (rolled back): {e}")
