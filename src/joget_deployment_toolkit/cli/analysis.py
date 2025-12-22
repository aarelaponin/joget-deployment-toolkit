"""
Dependency analysis for Joget form deployment.

Extracts form dependencies and determines optimal deployment order
using topological sorting.

Dependencies are extracted from:
- FormGrid.formDefId - Subform references
- SubForm.formDefId - Embedded form references
- optionsBinder.formDefId - Select box data sources
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DependencyAnalysis:
    """Result of analyzing form dependencies."""

    # Map of form_id -> set of form IDs it depends on
    dependencies: dict[str, set[str]] = field(default_factory=dict)

    # Ordered list of form IDs for deployment (dependencies first)
    deployment_order: list[str] = field(default_factory=list)

    # Dependencies that exist within the package
    internal_dependencies: set[str] = field(default_factory=set)

    # Dependencies that must exist in the target app (not in package)
    external_dependencies: set[str] = field(default_factory=set)

    # Forms with circular dependencies (if any)
    circular_dependencies: list[tuple[str, ...]] = field(default_factory=list)

    def has_issues(self) -> bool:
        """Check if there are any dependency issues."""
        return len(self.circular_dependencies) > 0


def extract_dependencies(form_json: dict[str, Any]) -> set[str]:
    """
    Extract form IDs referenced by a form definition.

    Scans the form JSON for:
    - FormGrid/SubForm formDefId properties
    - optionsBinder.formDefId in select boxes

    Args:
        form_json: Parsed form JSON definition

    Returns:
        Set of form IDs that this form depends on

    Example:
        >>> form = {"elements": [{"properties": {"formDefId": "subForm1"}}]}
        >>> deps = extract_dependencies(form)
        >>> "subForm1" in deps
        True
    """
    dependencies: set[str] = set()

    def scan_element(element: dict[str, Any]) -> None:
        """Recursively scan element and children for dependencies."""
        props = element.get("properties", {})

        # Check for direct formDefId (FormGrid, SubForm)
        form_def_id = props.get("formDefId")
        if form_def_id and isinstance(form_def_id, str) and form_def_id.strip():
            dependencies.add(form_def_id.strip())

        # Check for optionsBinder.formDefId (SelectBox, CheckBox, Radio)
        options_binder = props.get("optionsBinder", {})
        if isinstance(options_binder, dict):
            binder_props = options_binder.get("properties", {})
            if isinstance(binder_props, dict):
                binder_form_id = binder_props.get("formDefId")
                if binder_form_id and isinstance(binder_form_id, str) and binder_form_id.strip():
                    dependencies.add(binder_form_id.strip())

        # Check for loadBinder.formDefId (less common but possible)
        load_binder = props.get("loadBinder", {})
        if isinstance(load_binder, dict):
            load_props = load_binder.get("properties", {})
            if isinstance(load_props, dict):
                load_form_id = load_props.get("formDefId")
                if load_form_id and isinstance(load_form_id, str) and load_form_id.strip():
                    dependencies.add(load_form_id.strip())

        # Recurse into child elements
        for child in element.get("elements", []):
            if isinstance(child, dict):
                scan_element(child)

    # Scan all top-level elements
    for element in form_json.get("elements", []):
        if isinstance(element, dict):
            scan_element(element)

    return dependencies


def build_dependency_graph(
    forms_data: dict[str, dict[str, Any]]
) -> dict[str, set[str]]:
    """
    Build a dependency graph for all forms in a package.

    Args:
        forms_data: Map of form_id -> form JSON definition

    Returns:
        Map of form_id -> set of form IDs it depends on

    Example:
        >>> forms = {
        ...     "form1": {"elements": [{"properties": {"formDefId": "form2"}}]},
        ...     "form2": {"elements": []}
        ... }
        >>> graph = build_dependency_graph(forms)
        >>> graph["form1"]
        {'form2'}
        >>> graph["form2"]
        set()
    """
    return {
        form_id: extract_dependencies(form_json)
        for form_id, form_json in forms_data.items()
    }


def topological_sort(
    forms_data: dict[str, dict[str, Any]],
    dependency_graph: dict[str, set[str]] | None = None,
) -> tuple[list[str], list[tuple[str, ...]]]:
    """
    Sort forms in dependency order using Kahn's algorithm.

    Forms with no dependencies come first, followed by forms
    that depend only on already-listed forms.

    Args:
        forms_data: Map of form_id -> form JSON definition
        dependency_graph: Pre-computed dependency graph (optional)

    Returns:
        Tuple of (ordered_list, circular_dependencies)
        - ordered_list: Form IDs in deployment order
        - circular_dependencies: List of circular dependency cycles (if any)

    Example:
        >>> forms = {
        ...     "parent": {"elements": [{"properties": {"formDefId": "child"}}]},
        ...     "child": {"elements": []}
        ... }
        >>> order, cycles = topological_sort(forms)
        >>> order
        ['child', 'parent']
        >>> cycles
        []
    """
    if dependency_graph is None:
        dependency_graph = build_dependency_graph(forms_data)

    form_ids = set(forms_data.keys())

    # Filter dependencies to only include forms in the package
    # External dependencies are ignored for ordering purposes
    internal_deps: dict[str, set[str]] = {
        form_id: deps & form_ids
        for form_id, deps in dependency_graph.items()
    }

    # Build reverse graph (who depends on me)
    dependents: dict[str, set[str]] = defaultdict(set)
    for form_id, deps in internal_deps.items():
        for dep in deps:
            dependents[dep].add(form_id)

    # Calculate in-degree (number of dependencies)
    in_degree: dict[str, int] = {
        form_id: len(deps) for form_id, deps in internal_deps.items()
    }

    # Start with forms that have no dependencies
    queue = [fid for fid, degree in in_degree.items() if degree == 0]
    queue.sort()  # Alphabetical for deterministic order

    result: list[str] = []

    while queue:
        # Take form with no remaining dependencies
        form_id = queue.pop(0)
        result.append(form_id)

        # Reduce in-degree for forms that depend on this one
        for dependent in sorted(dependents[form_id]):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
        queue.sort()

    # Check for circular dependencies
    circular: list[tuple[str, ...]] = []
    remaining = [fid for fid in form_ids if fid not in result]

    if remaining:
        # Find cycles using DFS
        cycles = _find_cycles(remaining, internal_deps)
        circular.extend(cycles)

    return result, circular


def _find_cycles(
    nodes: list[str],
    deps: dict[str, set[str]]
) -> list[tuple[str, ...]]:
    """Find circular dependency cycles using DFS."""
    cycles: list[tuple[str, ...]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        if node in rec_stack:
            # Found cycle - extract it from path
            cycle_start = path.index(node)
            cycle = tuple(path[cycle_start:] + [node])
            if cycle not in cycles:
                cycles.append(cycle)
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for dep in deps.get(node, set()):
            if dep in nodes:  # Only follow internal deps
                dfs(dep)

        path.pop()
        rec_stack.remove(node)

    for node in sorted(nodes):
        if node not in visited:
            dfs(node)

    return cycles


def analyze_dependencies(
    forms_data: dict[str, dict[str, Any]],
    existing_forms: set[str] | None = None,
) -> DependencyAnalysis:
    """
    Perform complete dependency analysis on a form package.

    Args:
        forms_data: Map of form_id -> form JSON definition
        existing_forms: Set of form IDs that exist in target app (optional)

    Returns:
        DependencyAnalysis with full dependency information

    Example:
        >>> forms = {
        ...     "form1": {"elements": [{"properties": {"formDefId": "form2"}}]},
        ...     "form2": {"elements": [{"properties": {"optionsBinder": {
        ...         "properties": {"formDefId": "external"}}}}]}
        ... }
        >>> analysis = analyze_dependencies(forms, existing_forms={"external"})
        >>> analysis.deployment_order
        ['form2', 'form1']
        >>> "external" in analysis.external_dependencies
        True
    """
    if existing_forms is None:
        existing_forms = set()

    form_ids = set(forms_data.keys())

    # Build dependency graph
    dep_graph = build_dependency_graph(forms_data)

    # Collect all referenced forms
    all_deps: set[str] = set()
    for deps in dep_graph.values():
        all_deps.update(deps)

    # Categorize dependencies
    internal = all_deps & form_ids
    external = all_deps - form_ids

    # Check which external deps exist vs are missing
    # External deps that exist in target are OK
    # External deps that don't exist are potential issues

    # Get deployment order
    order, cycles = topological_sort(forms_data, dep_graph)

    return DependencyAnalysis(
        dependencies=dep_graph,
        deployment_order=order,
        internal_dependencies=internal,
        external_dependencies=external,
        circular_dependencies=cycles,
    )


def format_dependency_report(analysis: DependencyAnalysis) -> str:
    """
    Format dependency analysis as human-readable report.

    Args:
        analysis: DependencyAnalysis result

    Returns:
        Formatted string report
    """
    lines = ["Dependency Analysis", "=" * 40, ""]

    # Deployment order
    lines.append("Deployment Order:")
    for i, form_id in enumerate(analysis.deployment_order, 1):
        deps = analysis.dependencies.get(form_id, set())
        if deps:
            lines.append(f"  {i}. {form_id} (depends on: {', '.join(sorted(deps))})")
        else:
            lines.append(f"  {i}. {form_id}")
    lines.append("")

    # External dependencies
    if analysis.external_dependencies:
        lines.append("External Dependencies (must exist in target app):")
        for dep in sorted(analysis.external_dependencies):
            lines.append(f"  - {dep}")
        lines.append("")

    # Circular dependencies
    if analysis.circular_dependencies:
        lines.append("WARNING: Circular Dependencies Detected:")
        for cycle in analysis.circular_dependencies:
            lines.append(f"  - {' -> '.join(cycle)}")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "DependencyAnalysis",
    "extract_dependencies",
    "build_dependency_graph",
    "topological_sort",
    "analyze_dependencies",
    "format_dependency_report",
]
