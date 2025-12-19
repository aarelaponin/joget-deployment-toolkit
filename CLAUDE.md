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
- **REST API client** - Type-safe Joget DX API client with multiple auth strategies
- **Form discovery** - Extract form definitions from Joget MySQL database
- **Shared config integration** - Zero-config client creation via `from_instance('jdx4')`

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

## Architecture

```
joget_deployment_toolkit/
├── client/                    # API client with operation mixins
│   ├── __init__.py           # JogetClient class (combines mixins)
│   ├── base.py               # HTTP client foundation
│   ├── forms.py              # FormOperations mixin
│   ├── applications.py       # ApplicationOperations mixin
│   └── data.py               # DataOperations mixin
├── auth.py                   # Authentication strategies
├── config/                   # Configuration management
│   ├── models.py             # Pydantic config models
│   ├── loader.py             # Config file loading
│   └── shared_loader.py      # Shared config integration
├── operations/               # High-level orchestration
│   ├── mdm_deployer.py       # MDM deployment workflow
│   └── component_deployer.py # Component deployment (MDM + forms)
├── inventory.py              # Instance status & app comparison
├── database/                 # Database access
│   ├── connection.py         # Connection pooling
│   └── repositories/         # Repository pattern for queries
├── discovery.py              # Form discovery from database
├── models.py                 # API response models (Pydantic)
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

- **Forms**: `list_forms()`, `get_form()`, `create_form()`, `update_form()`, `delete_form()`
- **Applications**: `list_applications()`, `export_application()`, `import_application()`
- **Data**: `submit_form_data()`, `submit_batch()`

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

### 4. FormDiscovery

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
