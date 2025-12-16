#!/usr/bin/env python3
"""
Migration helper for updating existing code to use the new modular structure.

This script helps identify and update import statements in existing code.
"""

from pathlib import Path


def find_joget_imports(file_path: Path) -> list[tuple[int, str]]:
    """Find all joget_deployment_toolkit imports in a file."""
    imports = []

    with open(file_path) as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        if "from joget_deployment_toolkit" in line or "import joget_deployment_toolkit" in line:
            imports.append((i, line.strip()))

    return imports


def suggest_replacements(imports: list[tuple[int, str]]) -> list[tuple[str, str]]:
    """Suggest replacement imports for old patterns."""
    replacements = []

    for line_num, import_line in imports:
        old = import_line
        new = import_line  # Default to no change

        # Detect common patterns and suggest replacements
        if "from joget_deployment_toolkit import JogetClient" in import_line:
            # This remains the same - backward compatible
            new = import_line + "  # No change needed - backward compatible"
        elif "from joget_deployment_toolkit.client import JogetClient" in import_line:
            new = "from joget_deployment_toolkit import JogetClient  # Updated import path"

        replacements.append((old, new))

    return replacements


def main():
    """Main migration helper function."""
    import argparse

    parser = argparse.ArgumentParser(description="Help migrate to new joget-toolkit structure")
    parser.add_argument("path", type=Path, help="Path to scan for Python files")
    parser.add_argument("--fix", action="store_true", help="Apply fixes automatically")
    args = parser.parse_args()

    # Find all Python files
    if args.path.is_file():
        python_files = [args.path] if args.path.suffix == ".py" else []
    else:
        python_files = list(args.path.rglob("*.py"))

    print(f"Found {len(python_files)} Python files to check")

    for file_path in python_files:
        imports = find_joget_imports(file_path)
        if imports:
            print(f"\n{file_path}:")
            replacements = suggest_replacements(imports)

            for old, new in replacements:
                if old != new:
                    print(f"  - {old}")
                    print(f"  + {new}")

            if args.fix:
                # Apply fixes
                print("  [Fixes would be applied here]")

    print("\nMigration check complete!")


if __name__ == "__main__":
    main()
