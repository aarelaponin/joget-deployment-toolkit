# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**joget-deployment-toolkit** is a focused Python toolkit for automating Joget DX form and application deployment. It provides a type-safe REST API client, MDM data deployment orchestration, and seamless integration with instance configuration managed by [joget-instance-manager](https://github.com/aarelaponin/joget-instance-manager).

**Core Mission:** Simplify and automate deployment of forms, applications, and Master Data Management (MDM) to Joget DX instances.

**Version:** 1.1.0

## Tool Ecosystem

```
┌─────────────────────────────────────┐
│  joget-instance-manager             │  ← Instance Configuration Layer
│  (setup, reset, configure)          │
│                                     │
│  Creates: Database, Tomcat config,  │
│           Datasource, Schema        │
└──────────────┬──────────────────────┘
               │ writes/reads
               ▼
┌─────────────────────────────────────┐
│  ~/.joget/instances.yaml            │  ← Single Source of Truth
│  (shared configuration)             │
└──────────────┬──────────────────────┘
               │ reads
               ▼
┌─────────────────────────────────────┐
│  joget-deployment-toolkit           │  ← Content Deployment Layer
│  (deploy forms, MDM, apps)          │
└─────────────────────────────────────┘
```

## What This Toolkit IS

- **Deployment automation** - Forms, applications, data submission, MDM orchestration
- **Cross-instance migration** - Migrate forms, datalists, data, and menus between instances
- **REST API client** - Type-safe Joget DX API client with multiple auth strategies
- **Form discovery** - Extract form definitions from Joget MySQL database
- **Shared config integration** - Zero-config client creation via `from_instance('jdx4')`
- **CLI tool** - `joget-deploy` command with status, forms, check, and migrate commands

## What This Toolkit IS NOT

- **Not an instance manager** - Use joget-instance-manager for setup/reset/configure
- **Not a health check tool** - Use joget-instance-manager for health monitoring
- **Not a plugin manager** - Focused on deployment, not plugin discovery

## Password Types (Important!)

Three types of passwords in the ecosystem:

```bash
# 1. MySQL root passwords - used by joget-instance-manager for database creation
MYSQL4_ROOT_PASSWORD=root_password

# 2. Database user passwords - used by Joget app to connect to database
JOGET_CLIENT_ALPHA_PASSWORD=db_user_password

# 3. Web admin passwords - used by THIS TOOLKIT for REST API access
JDX4_PASSWORD=admin
```

**This toolkit only needs type 3 (web admin password).** Types 1 and 2 are managed by joget-instance-manager.

### Shared .env File

All passwords are centralized in the joget-instance-manager project's `.env` file:

**Location:** `/Users/aarelaponin/PycharmProjects/dev/joget-instance-manager/.env`

```bash
# MySQL Root Passwords (all instances)
MYSQL1_ROOT_PASSWORD=at456vkm
MYSQL2_ROOT_PASSWORD=at456vkm
MYSQL3_ROOT_PASSWORD=at456vkm
MYSQL4_ROOT_PASSWORD=at456vkm
MYSQL5_ROOT_PASSWORD=at456vkm
MYSQL6_ROOT_PASSWORD=at456vkm

# Joget Web Admin Passwords (for REST API access)
JDX1_PASSWORD=admin
JDX2_PASSWORD=admin
JDX3_PASSWORD=admin
JDX4_PASSWORD=admin
JDX5_PASSWORD=admin
JDX6_PASSWORD=admin
```

**To use:** Source the .env file before running toolkit commands:
```bash
source /Users/aarelaponin/PycharmProjects/dev/joget-instance-manager/.env
```

Or for direct database access (forms/data deployment without REST API):
```bash
# MySQL instance ports:
# mysql1: 3306, mysql2: 3307, mysql3: 3308, mysql4: 3309, mysql5: 3310, mysql6: 3311
mysql -h localhost -P 3309 -u root -p$MYSQL4_ROOT_PASSWORD jwdb
```

## Menu Types (Important!)

When creating userview menus, always use **CrudMenu** (not FormMenu):

| Menu Type | Class | Use Case |
|-----------|-------|----------|
| **CrudMenu** | `org.joget.plugin.enterprise.CrudMenu` | Standard CRUD operations with datalist + forms |
| FormMenu | `org.joget.apps.userview.lib.FormMenu` | Standalone form only (no list view) |

### CrudMenu Requirements

A CrudMenu requires THREE components to work:
1. **Form** - for add/edit operations
2. **Datalist** - for listing records (naming convention: `list_{formId}`)
3. **Menu config** - linking datalist + form

```python
# CORRECT - Use create_crud_menu() which generates proper CrudMenu
menu = client.create_crud_menu(
    form_id="farmerRegistrationForm",
    form_name="01 - Farmer Registration Form",
    datalist_id="list_farmerRegistrationForm"  # Must exist!
)

# WRONG - Don't create FormMenu for CRUD operations
# FormMenu only shows a form, no list/delete capabilities
```

### Migration Checklist

When migrating forms between instances:
- [ ] Migrate the form definition
- [ ] Migrate the corresponding datalist (`list_{formId}`)
- [ ] Create CrudMenu (not FormMenu) in userview
- [ ] Restart Tomcat to clear cache

### Datalist Naming Convention

The toolkit expects datalists to follow the pattern `list_{formId}`:
- Form: `farmerRegistrationForm` → Datalist: `list_farmerRegistrationForm`
- Form: `md01` → Datalist: `list_md01`

## Architecture

```
joget_deployment_toolkit/
├── client/                    # API client with operation mixins
│   ├── __init__.py           # JogetClient class (combines mixins)
│   ├── base.py               # HTTP client foundation
│   ├── forms.py              # FormOperations mixin
│   ├── applications.py       # ApplicationOperations mixin
│   ├── data.py               # DataOperations mixin
│   ├── datalists.py          # DatalistOperations mixin
│   └── userviews.py          # UserviewOperations mixin
├── auth.py                   # Authentication strategies
├── config/                   # Configuration management
│   ├── models.py             # Pydantic config models
│   ├── loader.py             # Config file loading
│   └── shared_loader.py      # Shared config integration
├── operations/               # High-level orchestration
│   ├── mdm_deployer.py       # MDM deployment workflow
│   ├── component_deployer.py # Component deployment (MDM + forms)
│   └── instance_migrator.py  # Cross-instance migration
├── inventory.py              # Instance status & app comparison
├── database/                 # Database access
│   ├── connection.py         # Connection pooling
│   └── repositories/         # Repository pattern for queries
│       ├── form_repository.py
│       ├── datalist_repository.py
│       └── userview_repository.py
├── discovery.py              # Form discovery from database
├── models.py                 # API response models (Pydantic)
├── cli/                      # Command-line interface
│   └── commands/
│       ├── status.py         # Instance status command
│       ├── forms.py          # Form deployment command
│       ├── check.py          # Package validation command
│       └── migrate.py        # Cross-instance migration command
└── exceptions.py             # Error handling hierarchy
```

### Key Design Patterns

1. **Mixin Pattern** - JogetClient combines operation mixins (Forms, Data, Applications)
2. **Repository Pattern** - Database access abstracted via repositories
3. **Strategy Pattern** - Pluggable authentication strategies
4. **Factory Pattern** - Multiple `from_*()` class methods for client creation

## Shared Config Integration

### Config File: `~/.joget/instances.yaml`

Created and managed by joget-instance-manager:

```yaml
instances:
  jdx4:
    name: jdx4
    installation_path: /path/to/joget
    tomcat:
      http_port: 8084
    database:
      name: jwdb
      mysql_instance: mysql4
    credentials:
      username: admin
      password_env: JDX4_PASSWORD  # References environment variable
```

### Using Shared Config

```python
from joget_deployment_toolkit import JogetClient

# Zero-config client creation (reads from ~/.joget/instances.yaml)
client = JogetClient.from_instance('jdx4')

# Password is read from $JDX4_PASSWORD environment variable
```

## Core Components

### 1. JogetClient

**Location:** `src/joget_deployment_toolkit/client/__init__.py`

**Creation Methods:**

```python
# Method 1: From shared config (RECOMMENDED)
client = JogetClient.from_instance('jdx4')

# Method 2: From credentials
client = JogetClient.from_credentials(
    "http://localhost:8084/jw",
    username="admin",
    password="admin"
)

# Method 3: From ClientConfig
from joget_deployment_toolkit.config import ClientConfig
config = ClientConfig(
    base_url="http://localhost:8084/jw",
    auth={"type": "session", "username": "admin", "password": "admin"}
)
client = JogetClient(config)
```

**Available Operations:**

- **Forms**: `list_forms()`, `get_form()`, `create_form()`, `update_form()`, `delete_form()`, `deploy_form()`
- **Applications**: `list_applications()`, `export_application()`, `import_application()`
- **Data**: `submit_form_data()`, `submit_batch()`
- **Datalists**: `list_datalists()`, `get_datalist()`, `create_datalist()`, `update_datalist()`, `delete_datalist()`
- **Userviews**: `list_userviews()`, `get_userview()`, `update_userview()`, `create_crud_menu()`, `add_menu_to_category()`

### FormCreator Plugin Integration

The `deploy_form()` method uses the **FormCreator API plugin** for reliable form deployment with automatic table creation and cache invalidation.

**Plugin Repository:** [form-creator-api](https://github.com/aarelaponin/joget-form-creator-api)

**Working Endpoint:** `POST /jw/api/formcreator/formcreator/forms`

> **Note:** The redundant path (`formcreator/formcreator`) is a quirk of Joget's API plugin routing where `getTag()` and `@Operation(path)` are concatenated.

#### API Credentials Setup

Before using `deploy_form()`, create API credentials in Joget:

1. Go to **Settings → API Key Manager → Add**
2. Create a credential with:
   - **API Name:** `formCreatorApi` (or any name)
   - **Auth Type:** Simple
3. Note the generated **API ID** and **API Key**

#### Usage

```python
from joget_deployment_toolkit import JogetClient
import json

client = JogetClient.from_instance('jdx4')

# Load form definition
form_def = json.load(open("my_form.json"))

# Deploy form using FormCreator plugin
result = client.deploy_form(
    app_id="farmersPortal",
    form_definition=form_def,
    api_id="API-4e39106c-67b1-4155-8c80-2f5ed6d1aae5",
    api_key="b2cc0157ab464ff5b1f07a5907ef9690",
    create_crud=True,   # Optional: create datalist + menu
    create_api=False    # Optional: create REST API endpoint
)

print(f"Success: {result.success}")
print(f"Form ID: {result.form_id}")
```

#### When to Use deploy_form() vs Direct Database

| Method | Use Case |
|--------|----------|
| `deploy_form()` | Production deployment with plugin installed |
| Direct DB insert | Quick prototyping, plugin not available |
| `InstanceMigrator` | Cross-instance migration with data |

### 2. ComponentDeployer

**Location:** `src/joget_deployment_toolkit/operations/component_deployer.py`

Deploys complete components (MDM + forms) in correct dependency order.

```python
from joget_deployment_toolkit import JogetClient, ComponentDeployer

client = JogetClient.from_instance('jdx4')
deployer = ComponentDeployer(client)

result = deployer.deploy_component(
    component_dir=Path("equipment_component"),
    target_app_id="farmersPortal",
    formcreator_api_id="fc_api"
)
```

### 3. MDMDataDeployer

**Location:** `src/joget_deployment_toolkit/operations/mdm_deployer.py`

Deploy MDM forms with CSV data.

```python
from joget_deployment_toolkit.operations import MDMDataDeployer

deployer = MDMDataDeployer(client)
results = deployer.deploy_all_mdm_from_directory(
    forms_dir=Path("mdm/forms"),
    data_dir=Path("mdm/data"),
    target_app_id="farmersPortal",
    formcreator_api_id="fc_api"
)
```

### 4. InstanceMigrator

**Location:** `src/joget_deployment_toolkit/operations/instance_migrator.py`

Migrate forms, datalists, data, and userview menus between Joget instances.

```python
from joget_deployment_toolkit import JogetClient, InstanceMigrator

source = JogetClient.from_instance('jdx3')
target = JogetClient.from_instance('jdx4')

migrator = InstanceMigrator(source, target)

# Analyze first (dry-run)
analysis = migrator.analyze(
    source_app_id='subsidyApplication',
    target_app_id='farmersPortal',
    pattern='md%',
    userview_id='v',
    category_label='Master Data'
)
print(analysis)

# Execute migration
result = migrator.migrate_app_component(
    source_app_id='subsidyApplication',
    target_app_id='farmersPortal',
    pattern='md%',
    with_data=True,
    userview_id='v',
    category_label='Master Data'
)
print(f"Migrated {result.forms_migrated} forms, {result.datalists_migrated} datalists")
```

**CLI Usage:**

```bash
# Dry-run to see what would be migrated
joget-deploy migrate --source jdx3 --source-app subsidyApplication \
                     --target jdx4 --target-app farmersPortal \
                     --pattern "md%" --dry-run

# Full migration with data and menu items
joget-deploy migrate --source jdx3 --source-app subsidyApplication \
                     --target jdx4 --target-app farmersPortal \
                     --pattern "md%" --with-data \
                     --userview v --category "Master Data"
```

**Important Notes:**
- Category must already exist in target userview (create manually in Joget UI first)
- Restart Tomcat on target instance after migration to clear Joget cache
- Use `--dry-run` to preview what would be migrated

### 5. FormDiscovery

**Location:** `src/joget_deployment_toolkit/discovery.py`

Extract form definitions from Joget MySQL database.

```python
from joget_deployment_toolkit import FormDiscovery

discovery = FormDiscovery({
    'host': 'localhost',
    'port': 3309,
    'database': 'jwdb',
    'user': 'root',
    'password': 'password'
})

forms = discovery.discover_all_forms('farmersPortal', app_version='1')
```

## Error Handling

```python
from joget_deployment_toolkit import (
    JogetClient,
    AuthenticationError,
    NotFoundError,
    ConflictError,
    ServerError,
    TimeoutError
)

try:
    client.export_application('nonexistent', 'backup.zip')
except NotFoundError as e:
    print(f"Application not found: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
```

**Exception Hierarchy:**

- `JogetAPIError` (base)
  - `ConnectionError` - Network issues
  - `AuthenticationError` - 401/403 responses
  - `NotFoundError` - 404 responses
  - `ValidationError` - 400 responses
  - `ConflictError` - 409 responses
  - `ServerError` - 500+ responses
  - `TimeoutError` - Request timeout
  - `BatchError` - Batch operation failures

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
pytest --cov=joget_deployment_toolkit --cov-report=html
```

### Code Quality

```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

## Related Projects

- **[joget-instance-manager](https://github.com/aarelaponin/joget-instance-manager)** - Instance configuration layer (writes `~/.joget/instances.yaml`)
- **[joget-form-generator](https://github.com/aarelaponin/joget-form-generator)** - Generate Joget forms from YAML/Excel/DB schemas

## Important Notes for AI Assistants

### When Working with This Code

1. **Never hardcode instance URLs/ports** - Always use shared config or ClientConfig
2. **Always use type hints** - This is a type-safe codebase (Pydantic models)
3. **Follow mixin pattern** - New operations go in separate mixin files
4. **Use repository pattern** - Database access goes through repositories
5. **Handle errors properly** - Use specific exception types

### When Testing or Making Joget API Calls

**CRITICAL: Always use the toolkit - never use raw curl/requests for Joget API operations.**

```python
# CORRECT - Use the toolkit
from joget_deployment_toolkit import JogetClient

client = JogetClient.from_instance('jdx4')
result = client.submit_form_data(
    form_id="x1",
    data={"x1": "Test Value"},
    api_id="API-..."
)

# WRONG - Don't use raw curl/requests
# curl -X POST http://localhost:8084/jw/api/form/x1 ...
```

### Common User Issues

**"Instance not found":**
```bash
# Solution: Ensure instance configured in joget-instance-manager
cat ~/.joget/instances.yaml
```

**"Authentication failed":**
```bash
# Solution: Set password environment variable
export JDX4_PASSWORD=admin
```

### Key Files to Know

- `src/joget_deployment_toolkit/__init__.py` - Main exports
- `src/joget_deployment_toolkit/client/__init__.py` - JogetClient class
- `src/joget_deployment_toolkit/config/shared_loader.py` - Shared config integration
- `src/joget_deployment_toolkit/operations/` - MDM and component deployment
- `pyproject.toml` - Package configuration
