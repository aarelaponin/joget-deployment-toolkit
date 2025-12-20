"""
Inventory API for Joget deployment toolkit.

Provides functions to check instance status and compare applications
across multiple Joget instances before deployment.

Functions:
    list_instances: List all configured instances with running status
    get_instance_status: Get detailed status of a single instance
    get_apps_overview: Get applications across multiple instances
    compare_apps: Compare applications between two instances

Example:
    >>> from joget_deployment_toolkit.inventory import list_instances, get_instance_status
    >>>
    >>> # Check all instances
    >>> instances = list_instances()
    >>> for inst in instances:
    ...     print(f"{inst.name}: {inst.status}")
    >>>
    >>> # Check specific instance before deployment
    >>> status = get_instance_status("jdx4")
    >>> if status.reachable:
    ...     # proceed with deployment
    ...     pass
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

import requests

from .config.shared_loader import get_instance, load_instances
from .models import AppComparison, AppSummary, InstanceInfo, InstanceStatus

logger = logging.getLogger(__name__)

# Default timeout for HTTP checks (seconds)
DEFAULT_CHECK_TIMEOUT = 5

# Maximum workers for parallel instance checks
DEFAULT_MAX_WORKERS = 6


def _check_instance_http(url: str, timeout: int = DEFAULT_CHECK_TIMEOUT) -> dict[str, Any]:
    """
    Check if a Joget instance is reachable via HTTP.

    Args:
        url: Base URL of the instance (e.g., http://localhost:8084/jw)
        timeout: Request timeout in seconds

    Returns:
        Dict with keys: reachable, response_time_ms, http_status, error
    """
    # Normalize URL - ensure it has /jw context path if not present
    base_url = url.rstrip("/")
    if not base_url.endswith("/jw"):
        base_url = f"{base_url}/jw"

    # Use the published apps endpoint as a simple health check
    # Note: This endpoint may return 302 (redirect to login) or 400 (bad request)
    # but any HTTP response means the server is running
    check_url = f"{base_url}/web/json/console/app/list"

    start_time = datetime.now()
    try:
        response = requests.get(check_url, timeout=timeout, allow_redirects=False)
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Any HTTP response (even 302, 400, 401) means the server is running
        # Only 5xx errors indicate server problems
        is_running = response.status_code < 500

        return {
            "reachable": is_running,
            "response_time_ms": elapsed_ms,
            "http_status": response.status_code,
            "error": None if is_running else f"HTTP {response.status_code}",
        }
    except requests.exceptions.ConnectionError:
        return {
            "reachable": False,
            "response_time_ms": None,
            "http_status": None,
            "error": "Connection refused",
        }
    except requests.exceptions.Timeout:
        return {
            "reachable": False,
            "response_time_ms": None,
            "http_status": None,
            "error": f"Timeout after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return {
            "reachable": False,
            "response_time_ms": None,
            "http_status": None,
            "error": str(e),
        }


def get_instance_status(
    instance_name: str,
    timeout: int = DEFAULT_CHECK_TIMEOUT,
) -> InstanceStatus:
    """
    Get detailed status of a single Joget instance.

    Performs an HTTP check to determine if the instance is reachable
    and responding to API requests.

    Args:
        instance_name: Name of the instance (e.g., 'jdx4')
        timeout: Request timeout in seconds (default: 5)

    Returns:
        InstanceStatus with reachability info and response time

    Raises:
        KeyError: If instance not found in configuration

    Example:
        >>> status = get_instance_status("jdx4")
        >>> if status.reachable:
        ...     print(f"Instance is up ({status.response_time_ms}ms)")
        ... else:
        ...     print(f"Instance is down: {status.error}")
    """
    # Load instance configuration
    instance_config = get_instance(instance_name)
    url = instance_config.get("url", "")

    if not url:
        return InstanceStatus(
            name=instance_name,
            reachable=False,
            error="No URL configured for instance",
            timestamp=datetime.now(),
        )

    # Perform HTTP check
    check_result = _check_instance_http(url, timeout)

    return InstanceStatus(
        name=instance_name,
        reachable=check_result["reachable"],
        response_time_ms=check_result["response_time_ms"],
        http_status=check_result["http_status"],
        version=instance_config.get("version"),
        error=check_result["error"],
        timestamp=datetime.now(),
    )


def list_instances(
    check_status: bool = True,
    timeout: int = DEFAULT_CHECK_TIMEOUT,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[InstanceInfo]:
    """
    List all configured Joget instances with their running status.

    Loads all instances from ~/.joget/instances.yaml and optionally
    checks each one to determine if it's running.

    Args:
        check_status: Whether to check running status via HTTP (default: True)
        timeout: Request timeout for status checks in seconds (default: 5)
        max_workers: Maximum parallel workers for status checks (default: 6)

    Returns:
        List of InstanceInfo objects with status information

    Example:
        >>> instances = list_instances()
        >>> running = [i for i in instances if i.is_running()]
        >>> print(f"Running instances: {[i.name for i in running]}")

        >>> # Quick list without status check
        >>> instances = list_instances(check_status=False)
    """
    # Load all instances from shared config
    instances_config = load_instances()

    # Build instance info list
    instance_infos: list[InstanceInfo] = []

    for name, config in instances_config.items():
        # Extract configuration values
        tomcat = config.get("tomcat", {})
        database = config.get("database", {})

        # Get DB port from mysql_instances if referenced
        db_port = None
        mysql_instance = database.get("mysql_instance")
        if mysql_instance:
            # Try to load mysql instance config
            try:
                from pathlib import Path

                import yaml

                config_file = Path.home() / ".joget" / "instances.yaml"
                if config_file.exists():
                    with open(config_file) as f:
                        full_config = yaml.safe_load(f)
                        mysql_instances = full_config.get("mysql_instances", {})
                        if mysql_instance in mysql_instances:
                            db_port = mysql_instances[mysql_instance].get("port")
            except Exception:
                pass

        info = InstanceInfo(
            name=name,
            version=config.get("version", "unknown"),
            environment=config.get("environment", "unknown"),
            url=tomcat.get("url", ""),
            web_port=tomcat.get("http_port", 0),
            db_port=db_port,
            status="unknown",
            response_time_ms=None,
        )
        instance_infos.append(info)

    # Check status if requested
    if check_status and instance_infos:
        _check_instances_parallel(instance_infos, timeout, max_workers)

    return instance_infos


def _check_instances_parallel(
    instances: list[InstanceInfo],
    timeout: int,
    max_workers: int,
) -> None:
    """
    Check status of multiple instances in parallel.

    Updates the status and response_time_ms fields of each InstanceInfo in place.
    """

    def check_one(info: InstanceInfo) -> tuple[str, dict[str, Any]]:
        result = _check_instance_http(info.url, timeout)
        return info.name, result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_one, info): info for info in instances}

        for future in as_completed(futures):
            info = futures[future]
            try:
                _, result = future.result()
                if result["reachable"]:
                    info.status = "running"
                    info.response_time_ms = result["response_time_ms"]
                else:
                    info.status = "stopped"
            except Exception as e:
                logger.warning(f"Error checking instance {info.name}: {e}")
                info.status = "unknown"


def get_apps_overview(
    instances: list[str] | None = None,
    timeout: int = DEFAULT_CHECK_TIMEOUT,
) -> dict[str, list[AppSummary]]:
    """
    Get applications across multiple Joget instances.

    Connects to each running instance and retrieves the list of
    published applications.

    Args:
        instances: List of instance names to check (default: all running instances)
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Dict mapping instance name to list of AppSummary objects.
        Only includes instances that are reachable.

    Example:
        >>> overview = get_apps_overview()
        >>> for instance, apps in overview.items():
        ...     print(f"{instance}: {len(apps)} apps")

        >>> # Check specific instances
        >>> overview = get_apps_overview(["jdx1", "jdx2"])
    """
    from .client import JogetClient

    result: dict[str, list[AppSummary]] = {}

    # Determine which instances to check
    if instances is None:
        # Get all running instances
        all_instances = list_instances(check_status=True, timeout=timeout)
        instance_names = [i.name for i in all_instances if i.is_running()]
    else:
        instance_names = instances

    for instance_name in instance_names:
        try:
            # Check if instance is reachable first
            status = get_instance_status(instance_name, timeout)
            if not status.reachable:
                logger.debug(f"Skipping {instance_name}: not reachable")
                continue

            # Create client and get apps
            client = JogetClient.from_instance(instance_name)
            apps = client.list_applications()

            # Convert to AppSummary
            app_summaries = [
                AppSummary(
                    id=app.id,
                    name=app.name,
                    version=app.version,
                    published=app.published,
                )
                for app in apps
            ]

            result[instance_name] = app_summaries

        except Exception as e:
            logger.warning(f"Error getting apps from {instance_name}: {e}")
            continue

    return result


def compare_apps(
    instance_a: str,
    instance_b: str,
    timeout: int = DEFAULT_CHECK_TIMEOUT,
) -> AppComparison:
    """
    Compare applications between two Joget instances.

    Identifies which apps exist only in one instance, which exist in both,
    and which have different versions.

    Args:
        instance_a: Name of first instance
        instance_b: Name of second instance
        timeout: Request timeout in seconds (default: 5)

    Returns:
        AppComparison with differences between the two instances

    Raises:
        RuntimeError: If either instance is not reachable

    Example:
        >>> diff = compare_apps("jdx2", "jdx4")  # staging vs client
        >>> if diff.has_differences():
        ...     print(f"Only in staging: {diff.only_in_a}")
        ...     print(f"Only in client: {diff.only_in_b}")
        ...     print(f"Version differences: {diff.version_diff}")
    """
    # Get apps from both instances
    overview = get_apps_overview([instance_a, instance_b], timeout)

    if instance_a not in overview:
        raise RuntimeError(f"Instance {instance_a} is not reachable or has no apps")
    if instance_b not in overview:
        raise RuntimeError(f"Instance {instance_b} is not reachable or has no apps")

    apps_a = {app.id: app for app in overview[instance_a]}
    apps_b = {app.id: app for app in overview[instance_b]}

    ids_a = set(apps_a.keys())
    ids_b = set(apps_b.keys())

    # Find differences
    only_in_a = list(ids_a - ids_b)
    only_in_b = list(ids_b - ids_a)
    in_both = list(ids_a & ids_b)

    # Check version differences for apps in both
    version_diff: dict[str, tuple[str, str]] = {}
    for app_id in in_both:
        ver_a = apps_a[app_id].version
        ver_b = apps_b[app_id].version
        if ver_a != ver_b:
            version_diff[app_id] = (ver_a, ver_b)

    return AppComparison(
        instance_a=instance_a,
        instance_b=instance_b,
        only_in_a=sorted(only_in_a),
        only_in_b=sorted(only_in_b),
        in_both=sorted(in_both),
        version_diff=version_diff,
    )


__all__ = [
    "list_instances",
    "get_instance_status",
    "get_apps_overview",
    "compare_apps",
    "InstanceInfo",
    "InstanceStatus",
    "AppSummary",
    "AppComparison",
]
