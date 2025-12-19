# Joget Deployment Toolkit - Interactive CLI Design

## Implementation Prompt

You are implementing an interactive CLI for `joget-deployment-toolkit` located at:
```
/Users/aarelaponin/PycharmProjects/dev/joget-deployment-toolkit
```

The toolkit already has these building blocks in `src/joget_deployment_toolkit/`:
- `client/` - JogetClient with `from_instance()`, `list_applications()`, `list_forms()`, `create_form()`, `update_form()`
- `config/shared_loader.py` - `load_instances()`, `get_instance()` reading from `~/.joget/instances.yaml`
- `inventory.py` - `list_instances()`, `get_instance_status()` for checking connectivity
- `operations/mdm_deployer.py` - MDMDataDeployer for bulk deployment
- `models.py` - Pydantic models for API responses

**Your task**: Create an interactive CLI that wraps these building blocks with a safe, guided deployment protocol.

---

## 1. Requirements

### 1.1 Core User Flow

```
joget-deploy forms <source-dir>

Step 1: Instance Selection
  - List all configured instances with status (running/stopped)
  - User selects by number or name
  - Validate connectivity before proceeding

Step 2: Application Selection  
  - List all apps in selected instance
  - User selects by number or ID
  - Validate app exists

Step 3: Package Analysis
  - Scan source directory for JSON files
  - Analyze dependencies between forms
  - Identify external dependencies (forms referenced but not in package)
  - Check which forms already exist in target app

Step 4: Pre-Deployment Checks
  - Verify all dependencies can be satisfied
  - Warn about forms that will be updated (already exist)
  - Block if critical dependencies missing

Step 5: Deployment Plan
  - Show forms to CREATE (new)
  - Show forms to UPDATE (existing)
  - Show deployment order (dependencies first)

Step 6: Confirmation
  - Require explicit confirmation
  - Extra confirmation for production environments

Step 7: Execute Deployment
  - Deploy in dependency order
  - Show progress
  - Handle partial failures gracefully

Step 8: Summary
  - Show results (created/updated/failed counts)
  - Provide verification URL
```

### 1.2 Non-Interactive Mode

All prompts skippable via flags for CI/CD:
```bash
joget-deploy forms specs/imm/output/ \
  --instance jdx-imm \
  --app farmersPortal \
  --yes
```

### 1.3 Dry-Run Mode

Preview without executing:
```bash
joget-deploy forms specs/imm/output/ --dry-run
```

---

## 2. CLI Commands

### 2.1 Main Commands

| Command | Purpose |
|---------|---------|
| `joget-deploy forms <dir>` | Deploy form JSON files |
| `joget-deploy status` | Show all instances with status |
| `joget-deploy check <dir>` | Validate package without deploying |

### 2.2 Options for `forms` Command

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--instance` | `-i` | Target instance name | (interactive) |
| `--app` | `-a` | Target application ID | (interactive) |
| `--app-version` | `-v` | Application version | `1` |
| `--yes` | `-y` | Skip confirmation | `false` |
| `--dry-run` | `-n` | Preview only | `false` |
| `--verbose` | | Detailed output | `false` |

### 2.3 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Deployment failed |
| 2 | Pre-check failed |
| 3 | User cancelled |

---

## 3. Module Structure

Create this structure in `src/joget_deployment_toolkit/`:

```
cli/
├── __init__.py
├── main.py                 # Typer app entry point
├── commands/
│   ├── __init__.py
│   ├── forms.py            # `joget-deploy forms` command
│   ├── status.py           # `joget-deploy status` command
│   └── check.py            # `joget-deploy check` command
├── interactive.py          # Instance/app selection prompts
├── display.py              # Rich output formatting
└── analysis.py             # Dependency analysis, prerequisite checks
```

---

## 4. Key Classes

### 4.1 DeploymentContext

```python
@dataclass
class DeploymentContext:
    """Holds all deployment parameters."""
    instance_name: str
    instance_url: str
    app_id: str
    app_version: str
    source_dir: Path
    client: JogetClient
    dry_run: bool = False
    verbose: bool = False
```

### 4.2 DeploymentPlan

```python
@dataclass
class DeploymentPlan:
    """Computed deployment plan."""
    forms_to_create: List[str]      # Form IDs to create (new)
    forms_to_update: List[str]      # Form IDs to update (existing)
    deployment_order: List[str]     # Ordered list for deployment
    external_deps: List[str]        # Dependencies outside package
    missing_deps: List[str]         # Dependencies that don't exist
    warnings: List[str]
    errors: List[str]
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
```

### 4.3 DeploymentResult

```python
@dataclass
class DeploymentResult:
    """Result after deployment execution."""
    success: bool
    created: int
    updated: int
    failed: int
    duration_seconds: float
    failed_forms: List[Tuple[str, str]]  # (form_id, error_message)
```

---

## 5. Dependency Analysis

### 5.1 How Forms Reference Other Forms

Scan form JSON for these patterns:

```python
def extract_dependencies(form_json: dict) -> Set[str]:
    """Extract form IDs that this form depends on."""
    deps = set()
    
    def scan_element(element: dict):
        props = element.get('properties', {})
        
        # formGrid / subform reference
        if 'formDefId' in props:
            deps.add(props['formDefId'])
        
        # optionsSource lookup
        options_source = props.get('optionsSource', {})
        if options_source.get('type') == 'formData':
            form_id = options_source.get('formId')
            if form_id:
                deps.add(form_id)
        
        # Recurse into child elements
        for child in element.get('elements', []):
            scan_element(child)
    
    for element in form_json.get('elements', []):
        scan_element(element)
    
    return deps
```

### 5.2 Deployment Order

Use topological sort to order forms so dependencies come first:

```python
def compute_deployment_order(
    forms: Dict[str, dict],  # form_id -> form_json
    existing_forms: Set[str]  # forms already in target app
) -> List[str]:
    """Return form IDs in dependency order."""
    # Build dependency graph
    # Topological sort
    # External deps (in existing_forms) don't need to be in order
```

---

## 6. Interactive Prompts

Use `questionary` or `rich.prompt` for interactive selection:

### 6.1 Instance Selection

```python
def select_instance() -> str:
    """Prompt user to select a Joget instance."""
    instances = list_instances(check_status=True)
    
    # Display table:
    # #  Instance   Environment  Status     URL
    # 1  jdx4       dev          ✓ running  localhost:8084
    # 2  jdx5       staging      ✗ stopped  localhost:8085
    
    # Prompt: "Select instance [1-N] or name:"
    # Validate selection
    # Return instance name
```

### 6.2 Application Selection

```python
def select_application(client: JogetClient) -> str:
    """Prompt user to select target application."""
    apps = client.list_applications()
    
    # Display table:
    # #  App ID          Name              Version
    # 1  farmersPortal   Farmers Portal    1
    # 2  masterData      Master Data       1
    
    # Prompt: "Select application [1-N] or ID:"
    # Return app_id
```

---

## 7. Display Formatting

Use `rich` library for formatted output:

### 7.1 Tables

```python
from rich.table import Table
from rich.console import Console

console = Console()

def show_instances(instances: List[InstanceInfo]):
    table = Table(title="Available Instances")
    table.add_column("#", style="dim")
    table.add_column("Instance")
    table.add_column("Environment")
    table.add_column("Status")
    table.add_column("URL")
    
    for i, inst in enumerate(instances, 1):
        status = "✓ running" if inst.is_running() else "✗ stopped"
        table.add_row(str(i), inst.name, inst.environment, status, inst.url)
    
    console.print(table)
```

### 7.2 Progress

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Deploying forms...", total=len(forms))
    for form_id in deployment_order:
        # deploy form
        progress.advance(task)
```

### 7.3 Deployment Summary

```
┌─────────────────────────────────────────────────────┐
│ DEPLOYMENT COMPLETE                                 │
├─────────────────────────────────────────────────────┤
│ Instance:    jdx-imm                                │
│ Application: farmersPortal v1                       │
│ Duration:    12.3s                                  │
├─────────────────────────────────────────────────────┤
│ ✓ Created: 15    ✓ Updated: 3    ✗ Failed: 0       │
├─────────────────────────────────────────────────────┤
│ Verify: http://localhost:8888/jw/.../forms          │
└─────────────────────────────────────────────────────┘
```

---

## 8. Pre-Deployment Checks

### 8.1 Check List

| Check | Severity | Action if Failed |
|-------|----------|------------------|
| Instance reachable | BLOCKER | Stop with error |
| App exists | BLOCKER | Stop with error |
| JSON files valid | BLOCKER | Stop with error |
| Form IDs ≤20 chars | BLOCKER | Stop with error |
| Internal deps satisfied | BLOCKER | Stop with error |
| External deps exist in app | WARNING | Show warning, continue |
| Forms will be overwritten | INFO | Show in plan |

### 8.2 Check Function

```python
def run_prechecks(context: DeploymentContext, plan: DeploymentPlan) -> bool:
    """Run all pre-deployment checks. Return True if OK to proceed."""
    checks = [
        ("Instance connectivity", check_connectivity),
        ("Application exists", check_app_exists),
        ("JSON syntax valid", check_json_valid),
        ("Form IDs valid", check_form_ids),
        ("Dependencies satisfied", check_dependencies),
    ]
    
    all_passed = True
    for name, check_fn in checks:
        result = check_fn(context, plan)
        display_check_result(name, result)
        if result.is_blocker and not result.passed:
            all_passed = False
    
    return all_passed
```

---

## 9. Entry Point

### 9.1 pyproject.toml Addition

```toml
[project.scripts]
joget-deploy = "joget_deployment_toolkit.cli.main:app"

[project.dependencies]
# Add these
typer = ">=0.9.0"
rich = ">=13.0"
questionary = ">=2.0"
```

### 9.2 Main Entry Point

```python
# src/joget_deployment_toolkit/cli/main.py
import typer
from .commands import forms, status, check

app = typer.Typer(
    name="joget-deploy",
    help="Interactive deployment tool for Joget DX"
)

app.add_typer(forms.app, name="forms")
app.add_typer(status.app, name="status")
app.add_typer(check.app, name="check")

if __name__ == "__main__":
    app()
```

---

## 10. Implementation Order

### Phase 1: Basic Structure
1. Create `cli/` module structure
2. Implement `joget-deploy status` (simplest command)
3. Add entry point to pyproject.toml
4. Test: `joget-deploy status`

### Phase 2: Forms Command (Non-Interactive)
1. Implement `joget-deploy forms` with all flags required
2. Add JSON loading and validation
3. Add basic deployment execution
4. Test: `joget-deploy forms dir/ -i inst -a app -y`

### Phase 3: Analysis
1. Implement dependency extraction
2. Implement deployment order computation
3. Implement prerequisite checks
4. Add deployment plan display

### Phase 4: Interactive Mode
1. Add instance selection prompt
2. Add application selection prompt
3. Add confirmation prompts
4. Make flags optional (fall back to interactive)

### Phase 5: Polish
1. Add rich progress display
2. Add deployment summary
3. Add dry-run mode
4. Add verbose mode

---

## 11. Example Session

```
$ joget-deploy forms specs/imm/output/

╭─────────────────────────────────────────────╮
│         JOGET DEPLOYMENT TOOLKIT            │
│            Forms Deployment                 │
╰─────────────────────────────────────────────╯

Step 1: Select Target Instance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Checking instances...

  #  Instance   Env       Status      URL
 ─────────────────────────────────────────────
  1  jdx4       dev       ✓ running   localhost:8084
  2  jdx5       staging   ✓ running   localhost:8085
  3  jdx-imm    imm-dev   ✓ running   localhost:8888

Select instance [1-3]: 3
✓ Selected: jdx-imm

Step 2: Select Target Application
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fetching applications...

  #  App ID          Name               Version  Forms
 ──────────────────────────────────────────────────────
  1  farmersPortal   Farmers Portal     1        47
  2  masterData      Master Data        1        25

Select application [1-2]: 1
✓ Selected: farmersPortal v1

Step 3: Analyzing Package
━━━━━━━━━━━━━━━━━━━━━━━━━
Source: specs/imm/output/
Found: 18 form files

Step 4: Pre-Deployment Checks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Instance connectivity
  ✓ Application exists
  ✓ JSON syntax valid
  ✓ Form IDs valid
  ✓ Internal dependencies satisfied
  ⚠ External dependencies: mdDistrict, mdAgroEcoZone (exist in app)

Step 5: Deployment Plan
━━━━━━━━━━━━━━━━━━━━━━━
  CREATE: 18 forms
  UPDATE: 0 forms

  Deployment order:
    1. md38InputCategory
    2. md39CampaignType
    ... (16 more)

Step 6: Confirm
━━━━━━━━━━━━━━━
Deploy 18 forms to farmersPortal on jdx-imm? [y/N]: y

Step 7: Deploying
━━━━━━━━━━━━━━━━
Deploying forms... ━━━━━━━━━━━━━━━━━━━━ 100% 18/18

Step 8: Complete
━━━━━━━━━━━━━━━━
╭──────────────────────────────────────────────╮
│ DEPLOYMENT COMPLETE                          │
├──────────────────────────────────────────────┤
│ ✓ Created: 18   Updated: 0   Failed: 0       │
│ Duration: 8.2s                               │
├──────────────────────────────────────────────┤
│ Verify: http://localhost:8888/jw/web/...     │
╰──────────────────────────────────────────────╯
```

---

## 12. Testing

### 12.1 Unit Tests

```python
# tests/cli/test_analysis.py
def test_extract_dependencies():
    form_json = {...}  # Form with optionsSource
    deps = extract_dependencies(form_json)
    assert "mdDistrict" in deps

def test_compute_deployment_order():
    forms = {"a": ..., "b": ...}  # b depends on a
    order = compute_deployment_order(forms, set())
    assert order.index("a") < order.index("b")
```

### 12.2 Integration Tests

```python
# tests/cli/test_commands.py
from typer.testing import CliRunner
from joget_deployment_toolkit.cli.main import app

runner = CliRunner()

def test_status_command():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0

def test_forms_dry_run(mock_instance):
    result = runner.invoke(app, [
        "forms", "test_forms/",
        "-i", "jdx-test",
        "-a", "testApp", 
        "--dry-run"
    ])
    assert result.exit_code == 0
    assert "Deployment Plan" in result.output
```
