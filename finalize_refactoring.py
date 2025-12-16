#!/usr/bin/env python3
"""
Joget-Toolkit v3.0 Refactoring Finalization Script

This script automates the final steps of the refactoring process.
Run each phase sequentially to complete the v3.0 release.

Usage:
    python finalize_refactoring.py --phase 1  # Run integration tests
    python finalize_refactoring.py --phase 2  # Update documentation
    python finalize_refactoring.py --phase 3  # Code quality checks
    python finalize_refactoring.py --phase 4  # Prepare release
    python finalize_refactoring.py --all      # Run all phases
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_header(message: str):
    """Print a formatted header."""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}{message:^60}{RESET}")
    print(f"{BLUE}{BOLD}{'='*60}{RESET}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{GREEN}✅ {message}{RESET}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{YELLOW}⚠️  {message}{RESET}")


def print_error(message: str):
    """Print error message."""
    print(f"{RED}❌ {message}{RESET}")


def run_command(cmd: str, description: str = None) -> Tuple[bool, str]:
    """Run a shell command and return success status and output."""
    if description:
        print(f"📋 {description}...")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr

    except subprocess.TimeoutExpired:
        return False, "Command timed out after 5 minutes"
    except Exception as e:
        return False, str(e)


def phase1_integration_tests():
    """Phase 1: Run integration tests."""
    print_header("Phase 1: Integration Testing & Verification")

    # Check for environment variables
    required_env = ["JOGET_BASE_URL", "JOGET_USERNAME", "JOGET_PASSWORD"]
    missing = [var for var in required_env if not os.getenv(var)]

    if missing:
        print_warning("Missing environment variables for integration tests:")
        for var in missing:
            print(f"  - {var}")
        print("\nTo run integration tests, set:")
        print("  export JOGET_BASE_URL=http://localhost:8080/jw")
        print("  export JOGET_USERNAME=admin")
        print("  export JOGET_PASSWORD=admin")
        print("\nSkipping integration tests...")
        return

    # Run integration tests
    success, output = run_command(
        "pytest tests/test_integration.py -v",
        "Running integration tests"
    )

    if success:
        print_success("Integration tests completed")
        # Parse and display results
        if "passed" in output:
            print(output.split("\n")[-2])  # Show summary line
    else:
        print_error("Integration tests failed")
        print(output)


def phase2_documentation():
    """Phase 2: Update documentation."""
    print_header("Phase 2: Documentation Updates")

    # Check current version in pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        if 'version = "2.1.0"' in content:
            print_warning("Version still shows 2.1.0 in pyproject.toml")
            print("Consider updating to 3.0.0 for breaking changes")

    # Create migration guide if it doesn't exist
    migration_path = Path("MIGRATION_GUIDE.md")
    if not migration_path.exists():
        print("Creating MIGRATION_GUIDE.md...")
        migration_content = """# Migration Guide: v2.x to v3.0

## Breaking Changes

### 1. Client Initialization

**v2.x (deprecated):**
```python
client = JogetClient("http://localhost:8080/jw", api_key="key")
```

**v3.0 (required):**
```python
from joget_deployment_toolkit.config import ClientConfig

config = ClientConfig(
    base_url="http://localhost:8080/jw",
    auth={"type": "api_key", "api_key": "key"}
)
client = JogetClient(config)
```

### 2. Alternative Constructors

Use the new convenience constructors:
```python
# From credentials
client = JogetClient.from_credentials(base_url, username, password)

# From environment
client = JogetClient.from_env()

# From config dict
client = JogetClient.from_config(config_dict)
```

### 3. Error Handling

All operations now raise specific exceptions:
- `AuthenticationError`: Authentication failures
- `NotFoundError`: 404 responses
- `ValidationError`: 400 responses
- `ServerError`: 5xx responses
- `JogetAPIError`: General API errors

### 4. Removed Features

- `from_kwargs()` and `to_kwargs()` configuration methods
- Mixed bool/exception return patterns
- Old `client.py` wrapper module

## Step-by-Step Migration

1. Update imports
2. Change initialization code
3. Add exception handling
4. Test thoroughly

For questions or issues, please open an issue on GitHub.
"""
        migration_path.write_text(migration_content)
        print_success("Created MIGRATION_GUIDE.md")
    else:
        print_success("MIGRATION_GUIDE.md already exists")

    # Check for API documentation
    docs_dir = Path("docs")
    if docs_dir.exists():
        print("📚 Documentation directory exists")
        print("  Run 'make html' in docs/ to generate API documentation")
    else:
        print_warning("No docs/ directory found")


def phase3_code_quality():
    """Phase 3: Code quality checks."""
    print_header("Phase 3: Code Quality & Polish")

    checks = [
        ("pytest --tb=no", "Running test suite"),
        ("pytest --cov=joget_deployment_toolkit --cov-report=term-missing --tb=no | grep TOTAL",
         "Checking test coverage"),
    ]

    for cmd, description in checks:
        success, output = run_command(cmd, description)
        if success:
            print_success(f"{description} - passed")
            if "TOTAL" in output:
                # Extract and show coverage percentage
                lines = output.strip().split("\n")
                for line in lines:
                    if "TOTAL" in line:
                        print(f"  Coverage: {line.split()[-1]}")
        else:
            print_warning(f"{description} - see output for details")

    # Check for development tools
    dev_tools = ["black", "ruff", "mypy"]
    missing_tools = []

    for tool in dev_tools:
        result = subprocess.run(
            f"which {tool}",
            shell=True,
            capture_output=True
        )
        if result.returncode != 0:
            missing_tools.append(tool)

    if missing_tools:
        print_warning(f"Missing development tools: {', '.join(missing_tools)}")
        print("Install with: pip install -e '.[dev]'")
    else:
        print_success("All development tools available")


def phase4_release_prep():
    """Phase 4: Prepare release."""
    print_header("Phase 4: Release Preparation")

    # Check version in pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        if 'version = "2.1.0"' in content:
            print_warning("Remember to update version to 3.0.0 in pyproject.toml")
        elif 'version = "3.0.0"' in content:
            print_success("Version already updated to 3.0.0")

    # Check CHANGELOG
    changelog_path = Path("CHANGELOG.md")
    if changelog_path.exists():
        content = changelog_path.read_text()
        if "3.0.0" not in content:
            print_warning("CHANGELOG.md needs v3.0.0 entry")
        else:
            print_success("CHANGELOG.md includes v3.0.0 entry")
    else:
        print_warning("No CHANGELOG.md found")

    # Release checklist
    print("\n📋 Release Checklist:")
    checklist = [
        "All tests passing (153/153)",
        "Coverage > 60%",
        "Version bumped to 3.0.0",
        "CHANGELOG.md updated",
        "MIGRATION_GUIDE.md created",
        "README.md updated",
        "Documentation generated",
        "Package builds successfully"
    ]

    for item in checklist:
        print(f"  [ ] {item}")

    print("\n🚀 To build and test the package:")
    print("  rm -rf build/ dist/ *.egg-info")
    print("  python -m build")
    print("  pip install dist/joget-toolkit-3.0.0.tar.gz")


def run_all_phases():
    """Run all phases sequentially."""
    phases = [
        phase1_integration_tests,
        phase2_documentation,
        phase3_code_quality,
        phase4_release_prep
    ]

    for i, phase in enumerate(phases, 1):
        phase()
        if i < len(phases):
            print(f"\n{BOLD}Continue to next phase? (y/n):{RESET} ", end="")
            response = input().strip().lower()
            if response != 'y':
                print("Stopping at user request.")
                break

    print_header("Finalization Complete!")
    print("✨ The joget-toolkit v3.0 refactoring is ready for release!")
    print("\nNext steps:")
    print("1. Review the checklist above")
    print("2. Make any final adjustments")
    print("3. Build and test the package")
    print("4. Tag and release v3.0.0")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Joget-Toolkit v3.0 Refactoring Finalization"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run specific phase (1-4)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all phases sequentially"
    )

    args = parser.parse_args()

    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    print(f"Working directory: {project_dir}")

    if args.all:
        run_all_phases()
    elif args.phase:
        phases = {
            1: phase1_integration_tests,
            2: phase2_documentation,
            3: phase3_code_quality,
            4: phase4_release_prep
        }
        phases[args.phase]()
    else:
        print("Usage: python finalize_refactoring.py --phase [1-4] or --all")
        print("\nPhases:")
        print("  1: Integration Testing & Verification")
        print("  2: Documentation Updates")
        print("  3: Code Quality & Polish")
        print("  4: Release Preparation")
        print("\nRun all phases with: python finalize_refactoring.py --all")


if __name__ == "__main__":
    main()