"""
Interactive prompts for the joget-deploy CLI.

Provides user-friendly selection prompts for instances and applications
when command-line flags are not provided.
"""

from typing import Optional

import questionary
from questionary import Style

from .display import console, show_error

# Custom style for questionary prompts
PROMPT_STYLE = Style([
    ('qmark', 'fg:cyan bold'),
    ('question', 'bold'),
    ('answer', 'fg:cyan'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan bold'),
    ('selected', 'fg:green'),
    ('separator', 'fg:gray'),
    ('instruction', 'fg:gray'),
])


def select_instance(
    instances: list,
    message: str = "Select target instance",
) -> Optional[str]:
    """
    Prompt user to select a Joget instance.

    Args:
        instances: List of InstanceInfo objects from inventory
        message: Prompt message to display

    Returns:
        Selected instance name, or None if cancelled

    Example:
        >>> from joget_deployment_toolkit.inventory import list_instances
        >>> instances = list_instances(check_status=True)
        >>> name = select_instance(instances)
        >>> print(f"Selected: {name}")
    """
    if not instances:
        show_error("No instances available")
        return None

    # Build choices with status indicators
    choices = []
    for inst in instances:
        # Format: "jdx4 (dev) - running [45ms]" or "jdx5 (staging) - stopped"
        status_icon = "✓" if inst.is_running() else "✗"
        status_text = "running" if inst.is_running() else "stopped"

        if inst.response_time_ms:
            label = f"{inst.name} ({inst.environment}) - {status_icon} {status_text} [{inst.response_time_ms}ms]"
        else:
            label = f"{inst.name} ({inst.environment}) - {status_icon} {status_text}"

        choices.append(questionary.Choice(
            title=label,
            value=inst.name,
            disabled="not reachable" if not inst.is_running() else None,
        ))

    # Add cancel option
    choices.append(questionary.Choice(title="Cancel", value=None))

    try:
        result = questionary.select(
            message,
            choices=choices,
            style=PROMPT_STYLE,
            use_shortcuts=True,
        ).ask()
        return result
    except KeyboardInterrupt:
        return None


def select_application(
    applications: list,
    message: str = "Select target application",
) -> Optional[str]:
    """
    Prompt user to select a Joget application.

    Args:
        applications: List of ApplicationInfo objects
        message: Prompt message to display

    Returns:
        Selected application ID, or None if cancelled

    Example:
        >>> apps = client.list_applications()
        >>> app_id = select_application(apps)
        >>> print(f"Selected: {app_id}")
    """
    if not applications:
        show_error("No applications available")
        return None

    # Build choices
    choices = []
    for app in applications:
        # Format: "farmersPortal - Farmers Portal (v1)"
        pub_indicator = "" if app.published else " [unpublished]"
        label = f"{app.id} - {app.name} (v{app.version}){pub_indicator}"

        choices.append(questionary.Choice(
            title=label,
            value=app.id,
        ))

    # Sort by app ID
    choices.sort(key=lambda c: c.value)

    # Add cancel option
    choices.append(questionary.Choice(title="Cancel", value=None))

    try:
        result = questionary.select(
            message,
            choices=choices,
            style=PROMPT_STYLE,
            use_shortcuts=True,
        ).ask()
        return result
    except KeyboardInterrupt:
        return None


def confirm_deployment(
    instance: str,
    app_id: str,
    form_count: int,
    create_count: int,
    update_count: int,
) -> bool:
    """
    Prompt user to confirm deployment.

    Args:
        instance: Target instance name
        app_id: Target application ID
        form_count: Total number of forms
        create_count: Number of forms to create
        update_count: Number of forms to update

    Returns:
        True if user confirms, False otherwise
    """
    console.print()

    # Build confirmation message
    action_parts = []
    if create_count > 0:
        action_parts.append(f"create {create_count}")
    if update_count > 0:
        action_parts.append(f"update {update_count}")

    action_str = " and ".join(action_parts) if action_parts else f"deploy {form_count}"

    message = f"Deploy to {app_id} on {instance}? ({action_str} forms)"

    try:
        result = questionary.confirm(
            message,
            default=False,
            style=PROMPT_STYLE,
        ).ask()
        return result if result is not None else False
    except KeyboardInterrupt:
        return False


def prompt_for_value(
    message: str,
    default: Optional[str] = None,
    validate: Optional[callable] = None,
) -> Optional[str]:
    """
    Prompt user for a text value.

    Args:
        message: Prompt message
        default: Default value
        validate: Optional validation function

    Returns:
        User input or None if cancelled
    """
    try:
        result = questionary.text(
            message,
            default=default or "",
            validate=validate,
            style=PROMPT_STYLE,
        ).ask()
        return result
    except KeyboardInterrupt:
        return None


def select_from_list(
    items: list[str],
    message: str,
    allow_cancel: bool = True,
) -> Optional[str]:
    """
    Generic selection from a list of strings.

    Args:
        items: List of string options
        message: Prompt message
        allow_cancel: Whether to include cancel option

    Returns:
        Selected item or None if cancelled
    """
    if not items:
        return None

    choices = [questionary.Choice(title=item, value=item) for item in items]

    if allow_cancel:
        choices.append(questionary.Choice(title="Cancel", value=None))

    try:
        result = questionary.select(
            message,
            choices=choices,
            style=PROMPT_STYLE,
        ).ask()
        return result
    except KeyboardInterrupt:
        return None


__all__ = [
    "select_instance",
    "select_application",
    "confirm_deployment",
    "prompt_for_value",
    "select_from_list",
]
