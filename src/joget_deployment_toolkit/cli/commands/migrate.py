"""
Migrate command for joget-deploy CLI.

Migrates forms, datalists, data, and userview menus between Joget instances.

Usage:
    joget-deploy migrate --source jdx3 --source-app subsidyApplication \
                         --target jdx4 --target-app farmersPortal \
                         --pattern "md%" --with-data \
                         --userview v --category "Master Data"

Examples:
    # Analyze what would be migrated (dry-run)
    joget-deploy migrate --source jdx3 --source-app subsidyApplication \
                         --target jdx4 --target-app farmersPortal \
                         --pattern "md%" --dry-run

    # Migrate MDM forms with data and menu items
    joget-deploy migrate --source jdx3 --source-app subsidyApplication \
                         --target jdx4 --target-app farmersPortal \
                         --pattern "md%" --with-data \
                         --userview v --category "Master Data"
"""

from typing import Optional

import typer

from ..display import (
    console,
    show_header,
    show_step,
    show_error,
    show_warning,
    show_success,
    show_info,
)

app = typer.Typer(help="Migrate components between Joget instances")


@app.command()
def run(
    source: str = typer.Option(
        ...,
        "--source",
        "-s",
        help="Source instance name (e.g., jdx3)",
    ),
    source_app: str = typer.Option(
        ...,
        "--source-app",
        help="Source application ID",
    ),
    target: str = typer.Option(
        ...,
        "--target",
        "-t",
        help="Target instance name (e.g., jdx4)",
    ),
    target_app: str = typer.Option(
        ...,
        "--target-app",
        help="Target application ID",
    ),
    pattern: Optional[str] = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Form ID pattern to filter (e.g., 'md%' for all MDM forms)",
    ),
    source_version: str = typer.Option(
        "1",
        "--source-version",
        help="Source application version",
    ),
    target_version: str = typer.Option(
        "1",
        "--target-version",
        help="Target application version",
    ),
    with_data: bool = typer.Option(
        False,
        "--with-data",
        help="Also copy data from source tables",
    ),
    userview: Optional[str] = typer.Option(
        None,
        "--userview",
        "-u",
        help="Target userview ID for adding menu items",
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Category label in userview for menu items (required if --userview set)",
    ),
    skip_existing: bool = typer.Option(
        True,
        "--skip-existing/--overwrite",
        help="Skip components that already exist in target (default: skip)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Analyze what would be migrated without making changes",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
) -> None:
    """
    Migrate forms, datalists, data, and menu items between Joget instances.

    Migration order (critical for dependencies):
    1. Forms first (no dependencies)
    2. Data tables (if --with-data)
    3. Datalists (reference forms)
    4. Userview menus (if --userview and --category specified)

    IMPORTANT: The category must already exist in the target userview.
    Create it manually in Joget UI before running migration.

    Examples:

        # Dry-run to see what would be migrated
        joget-deploy migrate -s jdx3 --source-app subsidyApplication \\
                             -t jdx4 --target-app farmersPortal \\
                             -p "md%" --dry-run

        # Full migration with data and menus
        joget-deploy migrate -s jdx3 --source-app subsidyApplication \\
                             -t jdx4 --target-app farmersPortal \\
                             -p "md%" --with-data \\
                             -u v -c "Master Data"
    """
    # Validate userview/category pairing
    if userview and not category:
        show_error("--category is required when --userview is specified")
        raise typer.Exit(code=1)

    show_header("INSTANCE MIGRATION")

    # Show configuration
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  Source: {source} / {source_app} v{source_version}")
    console.print(f"  Target: {target} / {target_app} v{target_version}")
    if pattern:
        console.print(f"  Pattern: {pattern}")
    console.print(f"  With data: {'Yes' if with_data else 'No'}")
    if userview:
        console.print(f"  Userview: {userview} / category '{category}'")
    console.print()

    # Step 1: Connect to instances
    show_step(1, "Connecting to Instances")

    try:
        from ...client import JogetClient

        console.print(f"  Connecting to {source}...", end="")
        source_client = JogetClient.from_instance(source)
        console.print(" [green]OK[/green]")

        console.print(f"  Connecting to {target}...", end="")
        target_client = JogetClient.from_instance(target)
        console.print(" [green]OK[/green]")

    except FileNotFoundError as e:
        show_error(f"Configuration not found: {e}")
        show_info("Ensure ~/.joget/instances.yaml exists with instance definitions")
        raise typer.Exit(code=1)
    except KeyError as e:
        show_error(f"Instance not found: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        show_error(f"Connection failed: {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(code=1)

    # Step 2: Create migrator and analyze
    show_step(2, "Analyzing Migration")

    try:
        from ...operations import InstanceMigrator

        migrator = InstanceMigrator(source_client, target_client)

        analysis = migrator.analyze(
            source_app_id=source_app,
            target_app_id=target_app,
            pattern=pattern,
            source_app_version=source_version,
            target_app_version=target_version,
            userview_id=userview,
            category_label=category,
        )

        console.print(f"  Forms to migrate: [green]{len(analysis.forms_to_migrate)}[/green]")
        console.print(f"  Forms already in target: {len(analysis.existing_forms)}")
        console.print(f"  Datalists to migrate: [green]{len(analysis.datalists_to_migrate)}[/green]")
        console.print(f"  Datalists already in target: {len(analysis.existing_datalists)}")

        if userview and category:
            if analysis.category_found:
                console.print(f"  Category '{category}': [green]Found[/green]")
                console.print(f"  Existing menus in category: {len(analysis.existing_menus)}")
            else:
                show_error(f"Category '{category}' not found in userview '{userview}'")
                show_info("Please create the category in Joget UI first, then re-run migration")
                raise typer.Exit(code=1)

        if verbose:
            if analysis.forms_to_migrate:
                console.print("\n  [bold]Forms to migrate:[/bold]")
                for form_id in analysis.forms_to_migrate[:10]:
                    console.print(f"    - {form_id}")
                if len(analysis.forms_to_migrate) > 10:
                    console.print(f"    ... and {len(analysis.forms_to_migrate) - 10} more")

    except ValueError as e:
        show_error(str(e))
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(code=1)
    except Exception as e:
        show_error(f"Analysis failed: {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(code=1)

    # Stop here if dry-run
    if dry_run:
        console.print()
        show_info("Dry-run complete. No changes were made.")
        console.print()
        console.print("[bold]Summary:[/bold]")
        console.print(f"  Would migrate {len(analysis.forms_to_migrate)} forms")
        console.print(f"  Would migrate {len(analysis.datalists_to_migrate)} datalists")
        if userview:
            menus_to_add = len(analysis.forms_to_migrate) - len(analysis.existing_menus)
            console.print(f"  Would add ~{max(0, menus_to_add)} menu items")
        if with_data:
            console.print("  Would copy data tables")
        raise typer.Exit(code=0)

    # Step 3: Confirm migration
    show_step(3, "Confirmation")

    if len(analysis.forms_to_migrate) == 0 and len(analysis.datalists_to_migrate) == 0:
        show_info("Nothing to migrate. All components already exist in target.")
        raise typer.Exit(code=0)

    console.print()
    console.print("[yellow]This will modify the target instance database.[/yellow]")
    if with_data:
        console.print("[yellow]Data tables will be REPLACED (existing data will be lost).[/yellow]")
    console.print()

    proceed = typer.confirm("Proceed with migration?", default=False)
    if not proceed:
        console.print("Migration cancelled.")
        raise typer.Exit(code=0)

    # Step 4: Execute migration
    show_step(4, "Executing Migration")

    try:
        result = migrator.migrate_app_component(
            source_app_id=source_app,
            target_app_id=target_app,
            pattern=pattern,
            source_app_version=source_version,
            target_app_version=target_version,
            with_data=with_data,
            userview_id=userview,
            category_label=category,
            skip_existing=skip_existing,
        )

        console.print()
        if result.success:
            show_success("Migration completed successfully!")
        else:
            show_warning("Migration completed with errors")

        console.print()
        console.print("[bold]Results:[/bold]")
        console.print(f"  Forms migrated: {result.forms_migrated}")
        console.print(f"  Datalists migrated: {result.datalists_migrated}")
        if with_data:
            console.print(f"  Data records copied: {result.data_records_copied}")
        if userview:
            console.print(f"  Menu items added: {result.menus_added}")

        if result.errors:
            console.print()
            show_warning(f"{len(result.errors)} errors occurred:")
            for error in result.errors[:5]:
                console.print(f"  - {error}")
            if len(result.errors) > 5:
                console.print(f"  ... and {len(result.errors) - 5} more")

        if result.warnings:
            console.print()
            show_info(f"{len(result.warnings)} warnings:")
            for warning in result.warnings[:5]:
                console.print(f"  - {warning}")

        # Reminder about Joget cache
        console.print()
        show_warning("IMPORTANT: Restart Tomcat on target instance to clear Joget cache.")
        console.print(f"  Userview URL: http://localhost:808{target[-1]}/jw/web/userview/{target_app}/{userview or 'v'}")

        exit_code = 0 if result.success else 1
        raise typer.Exit(code=exit_code)

    except typer.Exit:
        raise
    except Exception as e:
        show_error(f"Migration failed: {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


__all__ = ["app", "run"]
