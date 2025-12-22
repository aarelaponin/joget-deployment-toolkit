"""
Rich output formatting for CLI.

Provides formatted tables, panels, and progress displays
for the interactive deployment CLI.
"""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text

from ..models import ApplicationInfo, InstanceInfo

# Global console instance
console = Console()


def show_header(title: str = "JOGET DEPLOYMENT TOOLKIT") -> None:
    """Display CLI header banner."""
    console.print()
    console.print(Panel(title, style="bold blue", padding=(0, 2)))
    console.print()


def show_step(number: int, title: str) -> None:
    """Display a step header."""
    console.print()
    console.print(f"[bold]Step {number}: {title}[/bold]")
    console.print("━" * 40)


def show_instances_table(instances: list[InstanceInfo]) -> None:
    """
    Display instances in a formatted table.

    Args:
        instances: List of InstanceInfo objects from list_instances()
    """
    table = Table(title="Available Instances", show_header=True, header_style="bold cyan")

    table.add_column("#", style="dim", width=4)
    table.add_column("Instance", style="bold")
    table.add_column("Environment")
    table.add_column("Status", justify="center")
    table.add_column("URL")
    table.add_column("Response", justify="right")

    for i, inst in enumerate(instances, 1):
        # Status styling
        if inst.status == "running":
            status = Text("✓ running", style="green")
        elif inst.status == "stopped":
            status = Text("✗ stopped", style="red")
        else:
            status = Text("? unknown", style="yellow")

        # Response time
        response = f"{inst.response_time_ms}ms" if inst.response_time_ms else "-"

        table.add_row(
            str(i),
            inst.name,
            inst.environment,
            status,
            inst.url,
            response,
        )

    console.print(table)


def show_applications_table(apps: list[ApplicationInfo]) -> None:
    """
    Display applications in a formatted table.

    Args:
        apps: List of ApplicationInfo objects from list_applications()
    """
    table = Table(title="Available Applications", show_header=True, header_style="bold cyan")

    table.add_column("#", style="dim", width=4)
    table.add_column("App ID", style="bold")
    table.add_column("Name")
    table.add_column("Version", justify="center")
    table.add_column("Status", justify="center")

    for i, app in enumerate(apps, 1):
        status = Text("published", style="green") if app.published else Text("draft", style="yellow")

        table.add_row(
            str(i),
            app.id,
            app.name,
            app.version,
            status,
        )

    console.print(table)


def show_deployment_plan(
    forms_to_create: list[str],
    forms_to_update: list[str],
    deployment_order: list[str],
    external_deps: list[str] | None = None,
) -> None:
    """
    Display deployment plan summary.

    Args:
        forms_to_create: Form IDs that will be created
        forms_to_update: Form IDs that will be updated
        deployment_order: Forms in deployment order
        external_deps: External dependencies (optional warning)
    """
    # Summary counts
    console.print()
    console.print(f"  [green]CREATE[/green]: {len(forms_to_create)} forms")
    console.print(f"  [yellow]UPDATE[/yellow]: {len(forms_to_update)} forms")

    # External dependencies warning
    if external_deps:
        console.print()
        console.print(f"  [yellow]⚠ External dependencies[/yellow]: {', '.join(external_deps)}")

    # Deployment order
    if deployment_order:
        console.print()
        console.print("  [bold]Deployment order:[/bold]")
        for i, form_id in enumerate(deployment_order[:10], 1):
            action = "[green]CREATE[/green]" if form_id in forms_to_create else "[yellow]UPDATE[/yellow]"
            console.print(f"    {i}. {form_id} ({action})")
        if len(deployment_order) > 10:
            console.print(f"    ... ({len(deployment_order) - 10} more)")


def show_check_result(name: str, passed: bool, is_blocker: bool = True, message: str | None = None) -> None:
    """
    Display a single check result.

    Args:
        name: Name of the check
        passed: Whether the check passed
        is_blocker: If True, failure is critical
        message: Optional message to display
    """
    if passed:
        icon = "[green]✓[/green]"
    elif is_blocker:
        icon = "[red]✗[/red]"
    else:
        icon = "[yellow]⚠[/yellow]"

    line = f"  {icon} {name}"
    if message:
        line += f": {message}"
    console.print(line)


def show_deployment_summary(
    instance_name: str,
    app_id: str,
    app_version: str,
    created: int,
    updated: int,
    failed: int,
    duration_seconds: float,
    verify_url: str | None = None,
) -> None:
    """
    Display deployment completion summary.

    Args:
        instance_name: Target instance name
        app_id: Target application ID
        app_version: Target application version
        created: Number of forms created
        updated: Number of forms updated
        failed: Number of forms failed
        duration_seconds: Total deployment time
        verify_url: URL to verify deployment (optional)
    """
    success = failed == 0
    title = "[green]DEPLOYMENT COMPLETE[/green]" if success else "[red]DEPLOYMENT FAILED[/red]"

    lines = [
        f"[bold]Instance:[/bold]    {instance_name}",
        f"[bold]Application:[/bold] {app_id} v{app_version}",
        f"[bold]Duration:[/bold]    {duration_seconds:.1f}s",
        "",
        f"[green]✓ Created:[/green] {created}   [yellow]✓ Updated:[/yellow] {updated}   [red]✗ Failed:[/red] {failed}",
    ]

    if verify_url:
        lines.append("")
        lines.append(f"[bold]Verify:[/bold] {verify_url}")

    content = "\n".join(lines)
    console.print()
    console.print(Panel(content, title=title, border_style="green" if success else "red"))


def show_error(message: str) -> None:
    """Display an error message."""
    console.print(f"[red]Error:[/red] {message}")


def show_warning(message: str) -> None:
    """Display a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


def show_success(message: str) -> None:
    """Display a success message."""
    console.print(f"[green]✓[/green] {message}")


def show_info(message: str) -> None:
    """Display an info message."""
    console.print(f"[cyan]ℹ[/cyan] {message}")


def create_progress() -> Progress:
    """
    Create a Rich progress bar for deployment tracking.

    Returns:
        Progress instance configured for form deployment
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


__all__ = [
    "console",
    "show_header",
    "show_step",
    "show_instances_table",
    "show_applications_table",
    "show_deployment_plan",
    "show_check_result",
    "show_deployment_summary",
    "show_error",
    "show_warning",
    "show_success",
    "show_info",
    "create_progress",
]
