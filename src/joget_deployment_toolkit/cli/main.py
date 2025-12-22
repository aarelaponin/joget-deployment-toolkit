"""
Main entry point for joget-deploy CLI.

Provides an interactive command-line interface for safe, guided deployment
of forms and applications to Joget DX instances.

Usage:
    joget-deploy status     Show all configured instances
    joget-deploy forms      Deploy form JSON files (Phase 2)
    joget-deploy check      Validate package without deploying (Phase 5)
    joget-deploy migrate    Migrate components between instances
"""

import typer

from .commands import status
from .commands.forms import deploy as forms_deploy
from .commands.check import validate as check_validate
from .commands.migrate import run as migrate_run

# Create main Typer app
app = typer.Typer(
    name="joget-deploy",
    help="Interactive deployment tool for Joget DX",
    no_args_is_help=True,
    add_completion=False,
)

# Register commands
app.add_typer(status.app, name="status")
app.command(name="forms")(forms_deploy)
app.command(name="check")(check_validate)
app.command(name="migrate")(migrate_run)


@app.callback()
def main_callback() -> None:
    """
    Joget Deployment Toolkit - Interactive CLI

    Deploy forms and applications to Joget DX instances with safety checks,
    dependency analysis, and guided workflows.
    """
    pass


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
