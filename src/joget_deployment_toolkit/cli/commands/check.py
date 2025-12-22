"""
Check command for joget-deploy CLI.

Validates a form package without deploying it.

Usage:
    joget-deploy check <source-dir> [OPTIONS]

Examples:
    # Basic validation (no instance connection required)
    joget-deploy check components/imm/forms/

    # Full validation including external dependency check
    joget-deploy check components/imm/forms/ --instance jdx3 --app farmersPortal
"""

import json
from pathlib import Path
from typing import Optional

import typer

from ..analysis import analyze_dependencies, format_dependency_report
from ..display import (
    console,
    show_header,
    show_step,
    show_error,
    show_warning,
    show_success,
    show_info,
    show_check_result,
)

app = typer.Typer(help="Validate form package without deploying")


@app.command()
def validate(
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
        help="Target instance for external dependency check (optional)",
    ),
    app_id: Optional[str] = typer.Option(
        None,
        "--app",
        "-a",
        help="Target application for external dependency check (optional)",
    ),
    app_version: str = typer.Option(
        "1",
        "--app-version",
        "-v",
        help="Target application version",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed output",
    ),
) -> None:
    """
    Validate a form package without deploying.

    Checks:
    - JSON syntax validity
    - Form ID length (max 20 characters)
    - Internal dependencies (forms referencing other forms in package)
    - Circular dependencies
    - External dependencies (optionally verified against target app)

    Use --instance and --app to verify external dependencies exist
    in the target application.
    """
    show_header("PACKAGE VALIDATION")

    # Step 1: Scan source directory
    show_step(1, "Scanning Package")

    console.print(f"Source: {source_dir}")

    form_files = sorted(source_dir.glob("*.json"))
    if not form_files:
        show_error(f"No JSON files found in {source_dir}")
        raise typer.Exit(code=2)

    console.print(f"Found: {len(form_files)} form files")
    console.print()

    # Step 2: Load and validate JSON
    show_step(2, "Validating JSON")

    forms_data: dict[str, dict] = {}
    validation_errors: list[str] = []
    warnings: list[str] = []

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
                validation_errors.append(f"{form_id}: Form ID exceeds 20 characters ({len(form_id)} chars)")
                continue

            # Check for properties
            if "properties" not in form_json:
                warnings.append(f"{form_id}: Missing 'properties' field")

            # Check for tableName
            props = form_json.get("properties", {})
            if not props.get("tableName"):
                warnings.append(f"{form_id}: Missing 'tableName' in properties")

            forms_data[form_id] = form_json

            if verbose:
                form_name = props.get("name", form_id)
                console.print(f"  [green]✓[/green] {form_id}: {form_name}")

        except json.JSONDecodeError as e:
            validation_errors.append(f"{form_id}: Invalid JSON - {e}")
        except Exception as e:
            validation_errors.append(f"{form_id}: Error reading file - {e}")

    # Show JSON validation results
    json_valid = len(validation_errors) == 0
    show_check_result(
        "JSON syntax valid",
        json_valid,
        is_blocker=True,
        message=f"{len(validation_errors)} errors" if not json_valid else f"{len(forms_data)} files"
    )

    show_check_result(
        "Form IDs valid (≤20 chars)",
        all(len(fid) <= 20 for fid in forms_data.keys()),
        is_blocker=True,
    )

    if validation_errors:
        console.print()
        for err in validation_errors:
            console.print(f"  [red]✗[/red] {err}")
        console.print()
        show_error("Package has validation errors")
        raise typer.Exit(code=2)

    if warnings:
        console.print()
        for warn in warnings:
            console.print(f"  [yellow]![/yellow] {warn}")

    console.print()

    # Step 3: Analyze dependencies
    show_step(3, "Analyzing Dependencies")

    # Get existing forms from target app if instance/app provided
    existing_forms: set[str] = set()
    if instance and app_id:
        try:
            from ...inventory import get_instance_status
            from ...client import JogetClient

            status = get_instance_status(instance)
            if status.reachable:
                client = JogetClient.from_instance(instance)
                forms = client.list_forms(app_id, app_version=app_version)
                existing_forms = {f.form_id for f in forms}
                console.print(f"[dim]Found {len(existing_forms)} existing forms in {app_id}[/dim]")
            else:
                show_warning(f"Instance '{instance}' not reachable, skipping external dependency check")
        except Exception as e:
            show_warning(f"Could not check target app: {e}")

    dep_analysis = analyze_dependencies(forms_data, existing_forms=existing_forms)

    # Check for circular dependencies
    show_check_result(
        "No circular dependencies",
        not dep_analysis.has_issues(),
        is_blocker=True,
        message=f"{len(dep_analysis.circular_dependencies)} cycles" if dep_analysis.has_issues() else None
    )

    if dep_analysis.has_issues():
        console.print()
        show_error("Circular dependencies detected:")
        for cycle in dep_analysis.circular_dependencies:
            console.print(f"  [red]✗[/red] {' -> '.join(cycle)}")
        console.print()
        raise typer.Exit(code=2)

    # Check internal dependencies
    internal_satisfied = dep_analysis.internal_dependencies.issubset(set(forms_data.keys()))
    show_check_result(
        "Internal dependencies satisfied",
        internal_satisfied,
        is_blocker=True,
        message=f"{len(dep_analysis.internal_dependencies)} internal refs" if dep_analysis.internal_dependencies else None
    )

    # Check external dependencies
    if dep_analysis.external_dependencies:
        if existing_forms:
            missing = dep_analysis.external_dependencies - existing_forms
            if missing:
                show_check_result(
                    "External dependencies",
                    False,
                    is_blocker=False,
                    message=f"{len(missing)} missing"
                )
                if verbose:
                    console.print("  [dim]Missing external forms:[/dim]")
                    for ext in sorted(missing):
                        console.print(f"    [dim]- {ext}[/dim]")
            else:
                show_check_result(
                    "External dependencies",
                    True,
                    message=f"all {len(dep_analysis.external_dependencies)} found"
                )
        else:
            show_check_result(
                "External dependencies",
                True,
                is_blocker=False,
                message=f"{len(dep_analysis.external_dependencies)} refs (not verified)"
            )
            if verbose:
                console.print("  [dim]External forms referenced:[/dim]")
                for ext in sorted(dep_analysis.external_dependencies):
                    console.print(f"    [dim]- {ext}[/dim]")

    console.print()

    # Step 4: Show deployment order
    show_step(4, "Deployment Order")

    console.print("Forms will be deployed in this order:")
    console.print()
    for i, form_id in enumerate(dep_analysis.deployment_order, 1):
        deps = dep_analysis.dependencies.get(form_id, set())
        internal_deps = deps & set(forms_data.keys())
        if internal_deps:
            console.print(f"  {i}. {form_id} [dim](after: {', '.join(sorted(internal_deps))})[/dim]")
        else:
            console.print(f"  {i}. {form_id}")

    console.print()

    # Step 5: Summary
    show_step(5, "Summary")

    console.print()
    console.print(f"[bold green]VALIDATION PASSED[/bold green]")
    console.print()
    console.print(f"  Forms:              {len(forms_data)}")
    console.print(f"  Internal deps:      {len(dep_analysis.internal_dependencies)}")
    console.print(f"  External deps:      {len(dep_analysis.external_dependencies)}")

    if instance and app_id:
        console.print()
        console.print(f"  Target instance:    {instance}")
        console.print(f"  Target app:         {app_id} v{app_version}")

    console.print()
    show_info("Package is ready for deployment")

    if not instance or not app_id:
        console.print()
        console.print("[dim]Tip: Use --instance and --app to verify external dependencies exist[/dim]")

    raise typer.Exit(code=0)


__all__ = ["app"]
