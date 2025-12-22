# Joget Deployment Toolkit - Interactive CLI Design Document

## 1. Overview

### 1.1 Purpose

Design an interactive command-line interface (CLI) for the `joget-deployment-toolkit` that provides a safe, guided deployment experience with proper pre-flight checks, confirmation prompts, and clear feedback.

### 1.2 Goals

1. **Safety First**: Prevent accidental deployments to wrong instances/apps
2. **Interactive by Default**: Guide users through instance and app selection
3. **Pre-requisite Validation**: Check dependencies before deployment
4. **Dry-Run Support**: Preview changes without executing
5. **Clear Feedback**: Show progress, results, and actionable errors
6. **Scriptable**: Support non-interactive mode for CI/CD pipelines

### 1.3 Non-Goals

- GUI interface (CLI only)
- Rollback automation (manual via Joget UI)
- Multi-instance deployment in single command

---

## 2. User Experience

### 2.1 Interactive Deployment Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     JOGET DEPLOYMENT TOOLKIT                            │
│                        Forms Deployment                                 │
└─────────────────────────────────────────────────────────────────────────┘

Step 1: Select Target Instance
──────────────────────────────
Checking configured instances...

   #  Instance   Environment   Status     URL                    
  ───────────────────────────────────────────────────────────────
   1  jdx4       dev           ✓ running  http://localhost:8084/jw
   2  jdx5       staging       ✓ running  http://localhost:8085/jw
   3  jdx6       prod          ✗ stopped  http://localhost:8086/jw
   4  jdx-imm    imm-dev       ✓ running  http://localhost:8888/jw

Select instance [1-4] or name: 4

✓ Selected: jdx-imm (http://localhost:8888/jw)

Step 2: Select Target Application
─────────────────────────────────
Fetching applications from jdx-imm...

   #  App ID          App Name              Version  Forms
  ───────────────────────────────────────────────────────────
   1  farmersPortal   Farmers Portal        1        47
   2  masterData      Master Data           1        25
   3  testApp         Test Application      1        3

Select application [1-3] or ID: 1

✓ Selected: farmersPortal (Farmers Portal) v1

Step 3: Analyze Deployment Package
──────────────────────────────────
Source: /Users/user/joget-form-generator/specs/imm/output/
Found 18 form files

Analyzing dependencies...

   Form                  Type         Dependencies              Status
  ────────────────────────────────────────────────────────────────────────
   md38InputCategory     master       (none)                    ✓ ready
   md39CampaignType      master       (none)                    ✓ ready
   md40DistribModel      master       (none)                    ✓ ready
   md41AllocBasis        master       (none)                    ✓ ready
   md42TargetCategory    master       (none)                    ✓ ready
   md43DealerCategory    master       (none)                    ✓ ready
   md44Input             master       md38InputCategory         ✓ ready
   md45DistribPoint      master       mdDistrict                ✓ ready
   md47PackageContent    grid         md44Input                 ✓ ready
   md46InputPackage      master       md42TargetCategory        ✓ ready
   imCampaignInput       grid         md44Input, md41AllocBasis ✓ ready
   imCampaignDistPt      grid         md45DistribPoint          ✓ ready
   imEntitlementItem     grid         md44Input                 ✓ ready
   imDistribItem         grid         md44Input                 ✓ ready
   imAgroDealer          transaction  md43DealerCategory        ✓ ready
   imCampaign            transaction  (multiple)                ✓ ready
   imEntitlement         transaction  (multiple)                ✓ ready
   imDistribution        transaction  (multiple)                ✓ ready

Step 4: Pre-Deployment Checks
─────────────────────────────
Checking prerequisites...

   Check                              Status
  ──────────────────────────────────────────────────────
   Instance connectivity              ✓ passed
   Application exists                 ✓ passed
   User has admin permissions         ✓ passed
   External dependencies:
     - mdDistrict                     ✓ exists in app
     - mdAgroEcoZone                  ✓ exists in app
   Existing forms (will be updated):
     - md38InputCategory              ⚠ exists (will update)
     - md39CampaignType               ⚠ exists (will update)
   New forms (will be created):
     - imCampaign                     ○ new
     - imEntitlement                  ○ new
     - imDistribution                 ○ new
     - ... (12 more)

Step 5: Deployment Plan
───────────────────────
   Action     Count   Forms
  ────────────────────────────────────────────────
   CREATE     15      imCampaign, imEntitlement, ...
   UPDATE     3       md38InputCategory, md39CampaignType, ...
   SKIP       0       (none)

Step 6: Confirmation
────────────────────
⚠ WARNING: This will modify 18 forms in farmersPortal on jdx-imm

Proceed with deployment? [y/N]: y

Step 7: Deployment Progress
───────────────────────────
Deploying forms in dependency order...

   [████████████████████████████████████████] 18/18

   ✓ md38InputCategory    created
   ✓ md39CampaignType     created
   ✓ md40DistribModel     created
   ... (15 more)

Step 8: Summary
───────────────
┌─────────────────────────────────────────────────────────────────────────┐
│ DEPLOYMENT COMPLETE                                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ Instance:    jdx-imm (http://localhost:8888/jw)                        │
│ Application: farmersPortal v1                                           │
│ Duration:    12.3 seconds                                               │
├─────────────────────────────────────────────────────────────────────────┤
│ Results:                                                                │
│   ✓ Created: 15 forms                                                   │
│   ✓ Updated: 3 forms                                                    │
│   ✗ Failed:  0 forms                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Verify at: http://localhost:8888/jw/web/console/app/farmersPortal/1/forms│
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Non-Interactive Mode (CI/CD)

```bash
# Full specification via flags
joget-deploy forms specs/imm/output/ \
  --instance jdx-imm \
  --app farmersPortal \
  --app-version 1 \
  --yes \
  --fail-on-warning

# Using environment variables
export JOGET_INSTANCE=jdx-imm
export JOGET_APP=farmersPortal
joget-deploy forms specs/imm/output/ --yes
```

### 2.3 Dry-Run Mode

```bash
joget-deploy forms specs/imm/output/ --dry-run

# Shows full analysis and deployment plan without executing
# Exits with code 0 if deployment would succeed, 1 if issues found
```

---

## 3. CLI Commands Structure

### 3.1 Command Hierarchy

```
joget-deploy
├── forms <source-dir>       # Deploy form JSON files
├── mdm <source-dir>         # Deploy MDM forms + CSV data
├── component <source-dir>   # Deploy complete component (MDM + forms)
├── status                   # Show all instances status
├── apps [--instance NAME]   # List apps in instance(s)
├── check <source-dir>       # Validate deployment package (no deploy)
└── config                   # Show/manage configuration
    ├── show                 # Display current config
    ├── instances            # List configured instances
    └── test <instance>      # Test instance connectivity
```

### 3.2 Command: `joget-deploy forms`

**Purpose**: Deploy Joget form JSON files to a target instance/app

**Syntax**:
```bash
joget-deploy forms <source-dir> [OPTIONS]
```

**Arguments**:
| Argument | Description |
|----------|-------------|
| `source-dir` | Directory containing form JSON files |

**Options**:
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--instance` | `-i` | Target instance name | (interactive) |
| `--app` | `-a` | Target application ID | (interactive) |
| `--app-version` | `-v` | Application version | `1` |
| `--yes` | `-y` | Skip confirmation prompts | `false` |
| `--dry-run` | `-n` | Show plan without executing | `false` |
| `--fail-on-warning` | | Exit with error if warnings | `false` |
| `--skip-existing` | | Skip forms that already exist | `false` |
| `--update-only` | | Only update existing forms | `false` |
| `--order-file` | `-o` | File specifying deployment order | (auto-detect) |
| `--verbose` | | Show detailed output | `false` |
| `--quiet` | `-q` | Minimal output (errors only) | `false` |
| `--output-format` | | Output format: `text`, `json` | `text` |

**Exit Codes**:
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Deployment failed |
| 2 | Pre-requisite check failed |
| 3 | User cancelled |
| 4 | Configuration error |

### 3.3 Command: `joget-deploy mdm`

**Purpose**: Deploy MDM forms with CSV data population

**Syntax**:
```bash
joget-deploy mdm <source-dir> [OPTIONS]
```

**Arguments**:
| Argument | Description |
|----------|-------------|
| `source-dir` | Directory containing `forms/` and `data/` subdirectories |

**Additional Options** (beyond `forms` command):
| Option | Description | Default |
|--------|-------------|---------|
| `--forms-subdir` | Subdirectory for form files | `forms` |
| `--data-subdir` | Subdirectory for CSV files | `data` |
| `--skip-data` | Deploy forms only, no data | `false` |
| `--truncate-first` | Clear existing data before import | `false` |

**Expected Directory Structure**:
```
source-dir/
├── forms/
│   ├── md38InputCategory.json
│   ├── md39CampaignType.json
│   └── ...
└── data/
    ├── md38InputCategory.csv
    ├── md39CampaignType.csv
    └── ...
```

### 3.4 Command: `joget-deploy status`

**Purpose**: Show status of all configured Joget instances

**Syntax**:
```bash
joget-deploy status [OPTIONS]
```

**Options**:
| Option | Description | Default |
|--------|-------------|---------|
| `--timeout` | Connection timeout (seconds) | `5` |
| `--output-format` | Output format: `text`, `json`, `table` | `table` |

**Example Output**:
```
Joget Instances Status
══════════════════════════════════════════════════════════════════════════

   Instance   Environment   Version   Status     Response   URL
  ─────────────────────────────────────────────────────────────────────────
   jdx4       dev           9.0.0     ✓ running  45ms       localhost:8084
   jdx5       staging       9.0.0     ✓ running  52ms       localhost:8085
   jdx6       prod          9.0.0     ✗ stopped  -          localhost:8086
   jdx-imm    imm-dev       9.0.0     ✓ running  38ms       localhost:8888

Summary: 3 running, 1 stopped, 0 unknown
```

### 3.5 Command: `joget-deploy check`

**Purpose**: Validate deployment package without deploying

**Syntax**:
```bash
joget-deploy check <source-dir> [OPTIONS]
```

**Options**:
| Option | Description | Default |
|--------|-------------|---------|
| `--instance` | Check against specific instance | (none) |
| `--app` | Check against specific app | (none) |
| `--strict` | Treat warnings as errors | `false` |

**Checks Performed**:
1. JSON syntax validation
2. Required properties (id, tableName, name)
3. Form ID length (≤20 characters)
4. Duplicate form IDs
5. Dependency graph (no circular dependencies)
6. External references (if instance/app specified)

---

## 4. Pre-Requisite Checking

### 4.1 Check Categories

#### 4.1.1 Infrastructure Checks
| Check | Description | Severity |
|-------|-------------|----------|
| Instance connectivity | Can reach Joget server | BLOCKER |
| Authentication | Valid credentials | BLOCKER |
| Application exists | Target app exists | BLOCKER |
| User permissions | Has admin/deploy rights | BLOCKER |

#### 4.1.2 Package Validation
| Check | Description | Severity |
|-------|-------------|----------|
| JSON syntax | All files are valid JSON | BLOCKER |
| Form ID format | IDs ≤20 chars, valid chars | BLOCKER |
| Required properties | id, tableName, name present | BLOCKER |
| Duplicate IDs | No duplicate form IDs | BLOCKER |
| Circular dependencies | No circular form references | BLOCKER |

#### 4.1.3 Dependency Checks
| Check | Description | Severity |
|-------|-------------|----------|
| Internal dependencies | Referenced forms in package | WARNING if missing |
| External dependencies | Referenced forms in app | WARNING if missing |
| Grid sub-forms | formGrid references exist | WARNING if missing |
| Lookup sources | optionsSource forms exist | WARNING if missing |

#### 4.1.4 Conflict Detection
| Check | Description | Severity |
|-------|-------------|----------|
| Existing forms | Forms with same ID in app | INFO (will update) |
| Table conflicts | Table name used by other form | WARNING |

### 4.2 Dependency Analysis Algorithm

```python
def analyze_dependencies(forms: List[FormDefinition]) -> DependencyGraph:
    """
    Analyze form dependencies and build deployment order.
    
    Dependency sources:
    1. formGrid.formId - embedded grid form
    2. subform.formDefId - embedded subform  
    3. optionsSource.formId - lookup data source
    4. (any other form reference patterns)
    
    Returns:
        DependencyGraph with:
        - forms: List of forms in topological order
        - dependencies: Dict[form_id, List[dependency_form_id]]
        - external: List of references to forms not in package
        - circular: List of circular dependency chains (error if any)
    """
```

### 4.3 External Dependency Resolution

When a form references another form not in the deployment package:

1. **Check if exists in target app** → OK (external dependency satisfied)
2. **Check if exists in same instance (other app)** → WARNING (cross-app reference)
3. **Not found anywhere** → WARNING (deployment will succeed but form may not work)

---

## 5. Safety Features

### 5.1 Confirmation Prompts

**Always require confirmation for**:
- Production environments (environment = "prod" or "production")
- Large deployments (>20 forms)
- Updates to existing forms
- Destructive operations (truncate data)

**Confirmation message format**:
```
⚠ WARNING: You are about to deploy to PRODUCTION

   Instance:    jdx6 (prod)
   Application: farmersPortal v1
   Action:      CREATE 15 forms, UPDATE 3 forms
   
This action cannot be automatically rolled back.

Type 'deploy' to confirm: _
```

### 5.2 Environment Protection

```yaml
# In ~/.joget/instances.yaml
instances:
  jdx6:
    environment: production
    protection:
      require_confirmation: true
      require_explicit_flag: true  # Requires --production flag
      allowed_users: [admin, deploy-bot]
```

**Protected environment behavior**:
```bash
# Without --production flag
joget-deploy forms specs/imm/output/ -i jdx6 -a farmersPortal --yes

Error: Instance 'jdx6' is a production environment.
Use --production flag to confirm deployment to production.

# With flag
joget-deploy forms specs/imm/output/ -i jdx6 -a farmersPortal --yes --production
```

### 5.3 Dry-Run Mode

**Always available** via `--dry-run` or `-n`:
- Performs all checks
- Shows complete deployment plan
- Does NOT make any changes
- Returns exit code based on whether deployment would succeed

### 5.4 Deployment Audit Log

Every deployment creates an audit record:

```json
{
  "timestamp": "2024-01-20T14:30:00Z",
  "user": "aare",
  "hostname": "macbook.local",
  "command": "joget-deploy forms specs/imm/output/ -i jdx-imm -a farmersPortal",
  "instance": "jdx-imm",
  "application": "farmersPortal",
  "app_version": "1",
  "source_dir": "/Users/aare/specs/imm/output",
  "forms_deployed": 18,
  "forms_created": 15,
  "forms_updated": 3,
  "forms_failed": 0,
  "duration_seconds": 12.3,
  "status": "success",
  "details": [
    {"form_id": "md38InputCategory", "action": "create", "status": "success"},
    {"form_id": "md39CampaignType", "action": "create", "status": "success"}
  ]
}
```

**Log location**: `~/.joget/deploy-audit.jsonl` (JSON Lines format)

---

## 6. Configuration

### 6.1 Configuration Sources (Priority Order)

1. **Command-line arguments** (highest priority)
2. **Environment variables** (`JOGET_INSTANCE`, `JOGET_APP`, etc.)
3. **Project config file** (`.joget-deploy.yaml` in current directory)
4. **User config file** (`~/.joget/deploy-config.yaml`)
5. **Default values** (lowest priority)

### 6.2 Project Configuration File

`.joget-deploy.yaml` in project root:

```yaml
# Default deployment target
defaults:
  instance: jdx-imm
  app: farmersPortal
  app_version: "1"

# Deployment order (optional - overrides auto-detection)
deployment_order:
  - md38InputCategory
  - md39CampaignType
  - md40DistribModel
  # ... etc

# External dependencies (forms expected to exist in target app)
external_dependencies:
  - mdDistrict
  - mdAgroEcoZone
  - mdRelationship

# Pre-deployment hooks
hooks:
  pre_deploy:
    - script: ./scripts/validate-forms.sh
      description: "Custom form validation"
  post_deploy:
    - script: ./scripts/notify-slack.sh
      description: "Send Slack notification"
```

### 6.3 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `JOGET_INSTANCE` | Default target instance | `jdx-imm` |
| `JOGET_APP` | Default target application | `farmersPortal` |
| `JOGET_APP_VERSION` | Default app version | `1` |
| `JOGET_DEPLOY_YES` | Skip confirmations | `true` |
| `JOGET_DEPLOY_DRY_RUN` | Always dry-run | `true` |

---

## 7. Technical Architecture

### 7.1 Module Structure

```
src/joget_deployment_toolkit/
├── cli/
│   ├── __init__.py
│   ├── main.py              # Typer app, entry point
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── forms.py         # joget-deploy forms
│   │   ├── mdm.py           # joget-deploy mdm
│   │   ├── status.py        # joget-deploy status
│   │   ├── apps.py          # joget-deploy apps
│   │   ├── check.py         # joget-deploy check
│   │   └── config.py        # joget-deploy config
│   ├── prompts.py           # Interactive prompts (questionary/rich)
│   ├── display.py           # Output formatting (rich tables, progress)
│   ├── validators.py        # Input validation
│   └── models.py            # CLI-specific models (DeploymentPlan, etc.)
├── analysis/
│   ├── __init__.py
│   ├── dependency.py        # Dependency graph analysis
│   ├── prerequisites.py     # Pre-requisite checking
│   └── conflicts.py         # Conflict detection
├── deployment/
│   ├── __init__.py
│   ├── executor.py          # Deployment execution engine
│   ├── order.py             # Deployment order resolution
│   └── audit.py             # Audit logging
└── ... (existing modules)
```

### 7.2 Key Dependencies

```toml
[project.dependencies]
# Existing
requests = ">=2.28"
pydantic = ">=2.0"
PyYAML = ">=6.0"

# New for CLI
typer = ">=0.9.0"           # CLI framework
rich = ">=13.0"             # Rich terminal output
questionary = ">=2.0"       # Interactive prompts

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    # ...
]
```

### 7.3 Entry Points

```toml
[project.scripts]
joget-deploy = "joget_deployment_toolkit.cli.main:app"
```

### 7.4 Core Classes

```python
# cli/models.py

@dataclass
class DeploymentContext:
    """Context for a deployment operation."""
    instance_name: str
    instance_config: InstanceConfig
    client: JogetClient
    app_id: str
    app_version: str
    source_dir: Path
    dry_run: bool
    verbose: bool


@dataclass
class DeploymentPlan:
    """Plan for deploying forms."""
    forms_to_create: List[FormInfo]
    forms_to_update: List[FormInfo]
    forms_to_skip: List[FormInfo]
    deployment_order: List[str]
    warnings: List[str]
    errors: List[str]
    
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


@dataclass  
class DeploymentResult:
    """Result of a deployment operation."""
    success: bool
    forms_created: int
    forms_updated: int
    forms_failed: int
    duration_seconds: float
    details: List[FormDeploymentDetail]
    audit_id: str


# analysis/dependency.py

class DependencyAnalyzer:
    """Analyzes form dependencies and determines deployment order."""
    
    def analyze(self, forms: List[FormDefinition]) -> DependencyGraph:
        """Build dependency graph from form definitions."""
        
    def get_deployment_order(self, graph: DependencyGraph) -> List[str]:
        """Get topological sort of forms for deployment."""
        
    def find_external_dependencies(
        self, 
        graph: DependencyGraph,
        existing_forms: Set[str]
    ) -> List[ExternalDependency]:
        """Find dependencies on forms not in the package."""


# analysis/prerequisites.py

class PrerequisiteChecker:
    """Checks deployment prerequisites."""
    
    def check_all(self, context: DeploymentContext) -> PrerequisiteResult:
        """Run all prerequisite checks."""
        
    def check_connectivity(self, context: DeploymentContext) -> CheckResult:
        """Check instance connectivity."""
        
    def check_permissions(self, context: DeploymentContext) -> CheckResult:
        """Check user permissions."""
        
    def check_dependencies(
        self, 
        context: DeploymentContext,
        graph: DependencyGraph
    ) -> CheckResult:
        """Check all form dependencies are satisfied."""
```

---

## 8. Error Handling

### 8.1 Error Categories

| Category | Example | User Action |
|----------|---------|-------------|
| Configuration | Missing instance config | Fix configuration file |
| Connectivity | Cannot reach instance | Check instance is running |
| Authentication | Invalid credentials | Update password |
| Validation | Invalid form JSON | Fix form definition |
| Dependency | Missing required form | Deploy dependency first |
| Conflict | Form ID already exists | Use --update or rename |
| Permission | No admin rights | Contact administrator |
| Server | Joget server error | Check server logs |

### 8.2 Error Message Format

```
Error: [CATEGORY] Brief description

Details:
  - Specific detail 1
  - Specific detail 2

Suggestion:
  Try running: joget-deploy check specs/imm/output/ --verbose
  
Documentation:
  https://docs.example.com/deployment/errors#category
```

### 8.3 Partial Failure Handling

When some forms deploy successfully and others fail:

```
Deployment partially completed with errors

   Successful: 15 forms
   Failed: 3 forms

   Failed forms:
   ✗ imCampaign: Server error (500) - check Joget logs
   ✗ imEntitlement: Timeout after 60s - retry with --timeout 120
   ✗ imDistribution: Validation error - invalid field reference

Options:
  1. Fix errors and re-run (successful forms will be skipped with --skip-existing)
  2. Retry failed forms only: joget-deploy forms ... --retry-failed
  3. Check Joget UI for partial state

Audit log: ~/.joget/deploy-audit.jsonl (id: deploy-20240120-143000)
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

- Dependency analyzer (graph building, topological sort, cycle detection)
- Prerequisite checker (mock client responses)
- Deployment order resolution
- CLI argument parsing
- Output formatting

### 9.2 Integration Tests

- End-to-end deployment to test instance
- Interactive prompt flows (using pytest-mock for input simulation)
- Audit log creation
- Configuration file loading

### 9.3 Test Fixtures

```python
@pytest.fixture
def mock_joget_instance():
    """Mock Joget instance for testing."""
    with responses.RequestsMock() as rsps:
        # Mock connectivity check
        rsps.add(responses.GET, 
                 "http://localhost:8888/jw/web/json/apps/published/list",
                 json={"apps": []}, status=200)
        # Mock form list
        rsps.add(responses.GET,
                 "http://localhost:8888/jw/web/json/console/app/farmersPortal/1/forms",
                 json={"data": [...]}, status=200)
        yield rsps
```

---

## 10. Implementation Phases

### Phase 1: Core CLI Framework (MVP)
- [ ] Basic Typer CLI structure
- [ ] `joget-deploy forms` command (non-interactive)
- [ ] `joget-deploy status` command
- [ ] Basic prerequisite checks (connectivity, app exists)
- [ ] Dry-run mode
- [ ] Exit codes

### Phase 2: Interactive Mode
- [ ] Instance selection prompt
- [ ] Application selection prompt
- [ ] Confirmation prompts
- [ ] Progress display (rich)
- [ ] Deployment summary

### Phase 3: Advanced Analysis
- [ ] Dependency graph analysis
- [ ] External dependency checking
- [ ] Conflict detection
- [ ] Deployment order optimization

### Phase 4: Safety & Production Features
- [ ] Environment protection
- [ ] Audit logging
- [ ] Project config file support
- [ ] Hooks (pre/post deploy)

### Phase 5: Additional Commands
- [ ] `joget-deploy mdm` command
- [ ] `joget-deploy component` command
- [ ] `joget-deploy check` command
- [ ] `joget-deploy apps` command

---

## 11. Usage Examples

### 11.1 First-Time Deployment (Interactive)

```bash
$ cd /path/to/joget-form-generator
$ joget-deploy forms specs/imm/output/

# Interactive prompts guide through instance/app selection
# Shows deployment plan and asks for confirmation
# Deploys forms and shows summary
```

### 11.2 Repeat Deployment (Semi-Interactive)

```bash
$ joget-deploy forms specs/imm/output/ -i jdx-imm -a farmersPortal

# Skips instance/app selection (provided via flags)
# Still shows deployment plan and asks for confirmation
# Deploys forms and shows summary
```

### 11.3 CI/CD Pipeline

```bash
$ joget-deploy forms specs/imm/output/ \
    --instance jdx-staging \
    --app farmersPortal \
    --yes \
    --fail-on-warning \
    --output-format json > deploy-result.json
    
$ echo "Exit code: $?"
```

### 11.4 Validation Only

```bash
$ joget-deploy check specs/imm/output/ -i jdx-imm -a farmersPortal --strict

# Validates package against target environment
# Returns exit code 0 if valid, 1 if errors, 2 if warnings (with --strict)
# Does not deploy anything
```

### 11.5 Preview Changes

```bash
$ joget-deploy forms specs/imm/output/ -i jdx-imm -a farmersPortal --dry-run

# Shows complete deployment plan
# Shows which forms would be created/updated
# Does not deploy anything
```

---

## 12. Open Questions

1. **Rollback strategy**: Should we backup forms before updating? How to restore?
2. **Concurrent deployments**: How to handle multiple users deploying to same app?
3. **Form versioning**: Should we track form versions for better diff/merge?
4. **Plugin dependencies**: Should we check for required Joget plugins?
5. **Database migrations**: Should we handle table schema changes?

---

## Appendix A: Form Dependency Detection Patterns

Forms can reference other forms in several ways:

| Pattern | Location in JSON | Example |
|---------|------------------|---------|
| formGrid | `elements[].formDefId` | `"formDefId": "imCampaignInput"` |
| subform | `elements[].formDefId` | `"formDefId": "addressSubform"` |
| optionsSource | `elements[].properties.optionsSource.formId` | `"formId": "mdDistrict"` |
| AJAX popup | `elements[].properties.formDefId` | Various patterns |

---

## Appendix B: Sample Audit Log Entry

```json
{
  "id": "deploy-20240120-143000-a1b2c3",
  "timestamp": "2024-01-20T14:30:00.123Z",
  "user": "aare",
  "hostname": "macbook.local",
  "working_dir": "/Users/aare/projects/frs",
  "command": {
    "name": "forms",
    "args": ["specs/imm/output/"],
    "options": {
      "instance": "jdx-imm",
      "app": "farmersPortal",
      "app_version": "1",
      "dry_run": false
    }
  },
  "target": {
    "instance": "jdx-imm",
    "url": "http://localhost:8888/jw",
    "environment": "development",
    "app_id": "farmersPortal",
    "app_version": "1"
  },
  "source": {
    "directory": "/Users/aare/projects/frs/specs/imm/output",
    "form_count": 18,
    "total_size_bytes": 125000
  },
  "prerequisites": {
    "connectivity": "pass",
    "authentication": "pass",
    "app_exists": "pass",
    "dependencies": "pass",
    "warnings": []
  },
  "plan": {
    "create": 15,
    "update": 3,
    "skip": 0
  },
  "execution": {
    "start_time": "2024-01-20T14:30:01.000Z",
    "end_time": "2024-01-20T14:30:13.300Z",
    "duration_seconds": 12.3
  },
  "results": {
    "status": "success",
    "created": 15,
    "updated": 3,
    "failed": 0,
    "details": [
      {"form_id": "md38InputCategory", "action": "create", "status": "success", "duration_ms": 450},
      {"form_id": "md39CampaignType", "action": "create", "status": "success", "duration_ms": 380}
    ]
  }
}
```
