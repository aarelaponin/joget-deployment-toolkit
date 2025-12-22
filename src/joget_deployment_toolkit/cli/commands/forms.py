"""
Forms deployment command for joget-deploy CLI.

Deploys form JSON files to a Joget DX instance with safety checks.

Usage:
    joget-deploy forms <source-dir> [OPTIONS]

Examples:
    # Interactive mode (prompts for instance and app)
    joget-deploy forms components/imm/forms/

    # Non-interactive mode (all flags specified)
    joget-deploy forms components/imm/forms/ --instance jdx4 --app farmersPortal --yes

    # Dry-run mode (preview without deploying)
    joget-deploy forms components/imm/forms/ --instance jdx4 --app farmersPortal --dry-run
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from ..analysis import analyze_dependencies
from ..display import (
    console,
    show_header,
    show_step,
    show_error,
    show_warning,
    show_success,
    show_info,
    show_check_result,
    show_deployment_plan,
    show_deployment_summary,
    create_progress,
)
from ..models import DeploymentContext, DeploymentPlan, DeploymentResult

app = typer.Typer(help="Deploy form JSON files to Joget instance")


@app.command()
def deploy(
    source_dir: Path = typer.Argument(
        ...,
        help="Directory containing form JSON files",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    instance: Optional[str] = typer.Option(
        None,
        "--instance",
        "-i",
        help="Target instance name (e.g., jdx4)",
    ),
    app_id: Optional[str] = typer.Option(
        None,
        "--app",
        "-a",
        help="Target application ID (e.g., farmersPortal)",
    ),
    app_version: str = typer.Option(
        "1",
        "--app-version",
        "-v",
        help="Target application version",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Preview deployment without executing",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed output",
    ),
    formcreator_api_id: str = typer.Option(
        "formCreator",
        "--api-id",
        help="API ID for formCreator endpoint",
    ),
) -> None:
    """
    Deploy form JSON files to a Joget instance.

    Reads form definitions from SOURCE_DIR and deploys them to the
    specified instance and application.

    In non-interactive mode, all required options must be provided:
        --instance, --app, --yes

    In interactive mode (default), you will be prompted to select
    the target instance and application.
    """
    show_header("FORMS DEPLOYMENT")

    from ...inventory import get_instance_status, list_instances
    from ...client import JogetClient
    from ..interactive import select_instance, select_application

    # Interactive mode: prompt for instance if not provided
    if not instance:
        show_step(1, "Select Instance")
        console.print("Checking available instances...")
        console.print()

        try:
            instances = list_instances(check_status=True)
        except FileNotFoundError:
            show_error("No instances configured.")
            console.print("Run 'joget-instance-manager --sync-all-to-joget' first.")
            raise typer.Exit(code=2)

        if not instances:
            show_error("No instances found in configuration.")
            raise typer.Exit(code=2)

        # Filter to only running instances for selection
        running_instances = [i for i in instances if i.is_running()]
        if not running_instances:
            show_warning("No running instances found.")
            console.print("Available instances (all stopped):")
            for inst in instances:
                console.print(f"  - {inst.name} ({inst.environment})")
            raise typer.Exit(code=2)

        instance = select_instance(running_instances)
        if not instance:
            show_info("Deployment cancelled.")
            raise typer.Exit(code=3)

        console.print()

    # Step 1: Validate instance connectivity
    show_step(1 if app_id else 2, "Validating Instance")

    try:
        status = get_instance_status(instance)
    except KeyError:
        show_error(f"Instance '{instance}' not found in configuration.")
        console.print("Run 'joget-deploy status' to see available instances.")
        raise typer.Exit(code=2)

    if not status.reachable:
        show_error(f"Instance '{instance}' is not reachable: {status.error}")
        raise typer.Exit(code=2)

    show_success(f"Connected to {instance} ({status.response_time_ms}ms)")

    # Create client
    try:
        client = JogetClient.from_instance(instance)
    except Exception as e:
        show_error(f"Failed to create client: {e}")
        raise typer.Exit(code=1)

    # Interactive mode: prompt for application if not provided
    apps = None  # Track if we already fetched apps

    if not app_id:
        show_step(2, "Select Application")
        console.print("Fetching applications...")
        console.print()

        try:
            apps = client.list_applications()
        except Exception as e:
            show_error(f"Failed to list applications: {e}")
            raise typer.Exit(code=1)

        if not apps:
            show_error(f"No applications found in instance '{instance}'.")
            raise typer.Exit(code=2)

        app_id = select_application(apps)
        if not app_id:
            show_info("Deployment cancelled.")
            raise typer.Exit(code=3)

        console.print()
        # App was selected from the list, so it exists
        show_success(f"Selected application: {app_id}")
    else:
        # Validate application exists (only if app_id was provided via flag)
        show_step(2, "Validating Application")

        try:
            apps = client.list_applications()
            app_exists = any(a.id == app_id for a in apps)
        except Exception as e:
            show_error(f"Failed to list applications: {e}")
            raise typer.Exit(code=1)

        if not app_exists:
            show_error(f"Application '{app_id}' not found in instance '{instance}'.")
            console.print()
            console.print("Available applications:")
            for a in apps[:10]:
                console.print(f"  - {a.id} ({a.name})")
            if len(apps) > 10:
                console.print(f"  ... and {len(apps) - 10} more")
            raise typer.Exit(code=2)

        show_success(f"Found application: {app_id} v{app_version}")

    # Step 3: Scan source directory
    show_step(3, "Analyzing Package")

    console.print(f"Source: {source_dir}")

    form_files = sorted(source_dir.glob("*.json"))
    if not form_files:
        show_error(f"No JSON files found in {source_dir}")
        raise typer.Exit(code=2)

    console.print(f"Found: {len(form_files)} form files")

    # Load and validate form JSON files
    forms_data: dict[str, dict] = {}
    validation_errors: list[str] = []

    for form_file in form_files:
        form_id = form_file.stem
        try:
            with open(form_file, encoding="utf-8") as f:
                form_json = json.load(f)

            # Basic validation
            if "className" not in form_json:
                validation_errors.append(f"{form_id}: Missing 'className' field")
                continue

            # Check form ID length (Joget limit)
            if len(form_id) > 20:
                validation_errors.append(f"{form_id}: Form ID exceeds 20 characters")
                continue

            forms_data[form_id] = form_json

            if verbose:
                form_name = form_json.get("properties", {}).get("name", form_id)
                console.print(f"  [dim]✓ {form_id}[/dim]: {form_name}")

        except json.JSONDecodeError as e:
            validation_errors.append(f"{form_id}: Invalid JSON - {e}")
        except Exception as e:
            validation_errors.append(f"{form_id}: Error reading file - {e}")

    # Step 4: Pre-deployment checks
    show_step(4, "Pre-Deployment Checks")

    show_check_result("Instance connectivity", True)
    show_check_result("Application exists", True)
    show_check_result("JSON syntax valid", len(validation_errors) == 0, is_blocker=True,
                      message=f"{len(validation_errors)} errors" if validation_errors else None)
    show_check_result("Form IDs valid", all(len(fid) <= 20 for fid in forms_data.keys()))

    if validation_errors:
        console.print()
        show_error("Validation errors:")
        for err in validation_errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(code=2)

    # Check which forms already exist
    try:
        existing_forms = client.list_forms(app_id, app_version=app_version)
        existing_ids = {f.form_id for f in existing_forms}
    except Exception as e:
        show_warning(f"Could not check existing forms: {e}")
        existing_ids = set()

    forms_to_create = [fid for fid in forms_data.keys() if fid not in existing_ids]
    forms_to_update = [fid for fid in forms_data.keys() if fid in existing_ids]

    if forms_to_update:
        show_check_result(
            "Forms will be overwritten",
            True,
            is_blocker=False,
            message=f"{len(forms_to_update)} existing forms"
        )

    # Analyze dependencies
    dep_analysis = analyze_dependencies(forms_data, existing_forms=existing_ids)

    # Check for circular dependencies (blocker)
    show_check_result(
        "No circular dependencies",
        not dep_analysis.has_issues(),
        is_blocker=True,
        message=f"{len(dep_analysis.circular_dependencies)} cycles found" if dep_analysis.has_issues() else None
    )

    if dep_analysis.has_issues():
        console.print()
        show_error("Circular dependencies detected:")
        for cycle in dep_analysis.circular_dependencies:
            console.print(f"  [red]✗[/red] {' -> '.join(cycle)}")
        raise typer.Exit(code=2)

    # Check internal dependencies satisfied
    internal_deps_satisfied = dep_analysis.internal_dependencies.issubset(set(forms_data.keys()))
    show_check_result(
        "Internal dependencies satisfied",
        internal_deps_satisfied,
        is_blocker=True,
    )

    # External dependencies (warning only)
    if dep_analysis.external_dependencies:
        # Check which external deps exist in target app
        missing_external = dep_analysis.external_dependencies - existing_ids
        if missing_external:
            show_check_result(
                "External dependencies",
                False,
                is_blocker=False,
                message=f"{len(missing_external)} missing (may exist as MDM)"
            )
            if verbose:
                console.print("  [dim]Missing external forms:[/dim]")
                for ext in sorted(missing_external):
                    console.print(f"    [dim]- {ext}[/dim]")
        else:
            show_check_result("External dependencies", True, message="all found in target app")

    # Step 5: Deployment Plan
    show_step(5, "Deployment Plan")

    # Use topological order (dependencies first)
    deployment_order = dep_analysis.deployment_order

    show_deployment_plan(
        forms_to_create=forms_to_create,
        forms_to_update=forms_to_update,
        deployment_order=deployment_order,
    )

    # Show dependency info if verbose
    if verbose and dep_analysis.dependencies:
        console.print()
        console.print("[dim]Dependencies:[/dim]")
        for form_id in deployment_order:
            deps = dep_analysis.dependencies.get(form_id, set())
            if deps:
                internal = deps & set(forms_data.keys())
                external = deps - internal
                parts = []
                if internal:
                    parts.append(f"internal: {', '.join(sorted(internal))}")
                if external:
                    parts.append(f"external: {', '.join(sorted(external))}")
                console.print(f"  [dim]{form_id}: {'; '.join(parts)}[/dim]")

    # Step 6: Confirmation
    if not dry_run:
        show_step(6, "Confirmation")

        if not yes:
            console.print()
            confirm = typer.confirm(
                f"Deploy {len(forms_data)} forms to {app_id} on {instance}?",
                default=False,
            )
            if not confirm:
                show_info("Deployment cancelled.")
                raise typer.Exit(code=3)
        else:
            console.print(f"[dim]--yes flag provided, skipping confirmation[/dim]")

    # Step 7: Execute Deployment
    if dry_run:
        show_step(7, "Dry Run Complete")
        console.print("[yellow]DRY RUN[/yellow] - No changes made")
        console.print()
        console.print("To deploy for real, remove --dry-run flag and add --yes")
        raise typer.Exit(code=0)

    show_step(7, "Deploying")

    start_time = time.time()
    created_count = 0
    updated_count = 0
    failed_count = 0
    failed_forms: list[tuple[str, str]] = []

    with create_progress() as progress:
        task = progress.add_task("Deploying forms...", total=len(deployment_order))

        for form_id in deployment_order:
            form_json = forms_data[form_id]
            form_name = form_json.get("properties", {}).get("name", form_id)
            is_update = form_id in existing_ids

            try:
                # Use formCreator API to create/update form
                result = client.create_form(
                    payload={
                        "target_app_id": app_id,
                        "target_app_version": app_version,
                        "form_id": form_id,
                        "form_name": form_name,
                        "table_name": form_id,
                        "create_api_endpoint": "no",
                        "create_crud": "no",
                    },
                    form_definition=form_json,
                    api_id=formcreator_api_id,
                )

                # Check result
                if result.get("id") and not result.get("errors"):
                    if is_update:
                        updated_count += 1
                    else:
                        created_count += 1
                    if verbose:
                        action = "Updated" if is_update else "Created"
                        console.print(f"  [green]✓[/green] {action}: {form_id}")
                else:
                    failed_count += 1
                    error_msg = str(result.get("errors", "Unknown error"))
                    failed_forms.append((form_id, error_msg))
                    if verbose:
                        console.print(f"  [red]✗[/red] Failed: {form_id} - {error_msg}")

            except Exception as e:
                failed_count += 1
                failed_forms.append((form_id, str(e)))
                if verbose:
                    console.print(f"  [red]✗[/red] Failed: {form_id} - {e}")

            progress.advance(task)

    duration = time.time() - start_time

    # Step 8: Summary
    show_step(8, "Complete")

    # Build verification URL
    from ...config.shared_loader import get_instance
    try:
        instance_config = get_instance(instance)
        # Get URL from tomcat config
        tomcat = instance_config.get("tomcat", {})
        base_url = tomcat.get("url", "")
        if not base_url:
            base_url = instance_config.get("url", "")
        verify_url = f"{base_url}/web/console/app/{app_id}/{app_version}/forms"
    except Exception:
        verify_url = None

    show_deployment_summary(
        instance_name=instance,
        app_id=app_id,
        app_version=app_version,
        created=created_count,
        updated=updated_count,
        failed=failed_count,
        duration_seconds=duration,
        verify_url=verify_url,
    )

    # Show failed forms if any
    if failed_forms:
        console.print()
        console.print("[red]Failed forms:[/red]")
        for form_id, error in failed_forms:
            console.print(f"  [red]✗[/red] {form_id}: {error}")

    # Exit with appropriate code
    if failed_count > 0:
        raise typer.Exit(code=1)
    else:
        raise typer.Exit(code=0)


__all__ = ["app"]
