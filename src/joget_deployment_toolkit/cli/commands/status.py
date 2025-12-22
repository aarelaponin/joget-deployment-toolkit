"""
Status command for joget-deploy CLI.

Shows all configured Joget instances with their running status.

Usage:
    joget-deploy status [--no-check]
"""

import typer

from ..display import console, show_header, show_instances_table, show_error

app = typer.Typer(help="Show status of configured Joget instances")


@app.callback(invoke_without_command=True)
def status(
    ctx: typer.Context,
    no_check: bool = typer.Option(
        False,
        "--no-check",
        help="Skip connectivity check (faster but no status)",
    ),
) -> None:
    """
    Show all configured Joget instances with their running status.

    Reads instances from ~/.joget/instances.yaml and optionally
    checks each instance for connectivity.

    Examples:
        joget-deploy status           # Check all instances
        joget-deploy status --no-check  # Quick list without connectivity check
    """
    from ...inventory import list_instances

    show_header("INSTANCE STATUS")

    # Check status unless --no-check is specified
    check_status = not no_check

    if check_status:
        console.print("Checking instances...", style="dim")
        console.print()

    try:
        instances = list_instances(check_status=check_status)
    except FileNotFoundError:
        show_error("No instances configured. Run 'joget-instance-manager --sync-all-to-joget' first.")
        raise typer.Exit(code=1)
    except Exception as e:
        show_error(f"Failed to load instances: {e}")
        raise typer.Exit(code=1)

    if not instances:
        console.print("No instances found in configuration.")
        console.print()
        console.print("Configure instances at: ~/.joget/instances.yaml")
        raise typer.Exit(code=0)

    show_instances_table(instances)

    # Summary
    if check_status:
        running = sum(1 for i in instances if i.is_running())
        console.print()
        console.print(
            f"[dim]{running}/{len(instances)} instances running[/dim]"
        )


__all__ = ["app"]
