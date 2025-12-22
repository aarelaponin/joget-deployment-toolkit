"""
CLI-specific data models.

Dataclasses for managing deployment context, plans, and results
throughout the CLI workflow.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import JogetClient


@dataclass
class DeploymentContext:
    """
    Holds all deployment parameters for a deployment session.

    Collects instance, application, and source information needed
    to execute a deployment.
    """

    instance_name: str
    instance_url: str
    app_id: str
    app_version: str
    source_dir: Path
    client: "JogetClient"
    dry_run: bool = False
    verbose: bool = False

    def __str__(self) -> str:
        mode = "[DRY RUN] " if self.dry_run else ""
        return f"{mode}Deploy to {self.app_id} v{self.app_version} on {self.instance_name}"


@dataclass
class DeploymentPlan:
    """
    Computed deployment plan after package analysis.

    Contains the list of forms to create/update, deployment order,
    and any warnings or errors from pre-deployment checks.
    """

    forms_to_create: list[str] = field(default_factory=list)  # Form IDs to create (new)
    forms_to_update: list[str] = field(default_factory=list)  # Form IDs to update (existing)
    deployment_order: list[str] = field(default_factory=list)  # Ordered list for deployment
    external_deps: list[str] = field(default_factory=list)  # Dependencies outside package
    missing_deps: list[str] = field(default_factory=list)  # Dependencies that don't exist
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if plan has no blocking errors."""
        return len(self.errors) == 0

    @property
    def total_forms(self) -> int:
        """Total number of forms to deploy."""
        return len(self.forms_to_create) + len(self.forms_to_update)

    def __str__(self) -> str:
        status = "Valid" if self.is_valid else "Invalid"
        return (
            f"DeploymentPlan({status}): "
            f"{len(self.forms_to_create)} create, "
            f"{len(self.forms_to_update)} update, "
            f"{len(self.warnings)} warnings, "
            f"{len(self.errors)} errors"
        )


@dataclass
class DeploymentResult:
    """
    Result after deployment execution.

    Tracks success/failure counts and timing information.
    """

    success: bool
    created: int = 0
    updated: int = 0
    failed: int = 0
    duration_seconds: float = 0.0
    failed_forms: list[tuple[str, str]] = field(default_factory=list)  # (form_id, error_message)

    @property
    def total_deployed(self) -> int:
        """Total successfully deployed forms."""
        return self.created + self.updated

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return (
            f"DeploymentResult({status}): "
            f"{self.created} created, {self.updated} updated, {self.failed} failed "
            f"in {self.duration_seconds:.1f}s"
        )


@dataclass
class CheckResult:
    """
    Result of a single pre-deployment check.

    Used to report pass/fail status of individual validation checks.
    """

    name: str
    passed: bool
    is_blocker: bool  # If True, failure prevents deployment
    message: str | None = None

    def __str__(self) -> str:
        icon = "✓" if self.passed else ("✗" if self.is_blocker else "⚠")
        return f"{icon} {self.name}" + (f": {self.message}" if self.message else "")


__all__ = [
    "DeploymentContext",
    "DeploymentPlan",
    "DeploymentResult",
    "CheckResult",
]
