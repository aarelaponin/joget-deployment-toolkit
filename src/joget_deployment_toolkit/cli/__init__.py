"""
CLI module for Joget Deployment Toolkit.

Provides an interactive command-line interface for safe, guided deployment
of forms and applications to Joget DX instances.

Commands:
    joget-deploy status     Show all configured instances with status
    joget-deploy forms      Deploy form JSON files with safety checks
    joget-deploy check      Validate package without deploying

Example:
    $ joget-deploy status
    $ joget-deploy forms components/imm/forms/ --instance jdx4 --app farmersPortal
    $ joget-deploy forms components/imm/forms/  # Interactive mode
"""

from .models import DeploymentContext, DeploymentPlan, DeploymentResult

__all__ = [
    "DeploymentContext",
    "DeploymentPlan",
    "DeploymentResult",
]
