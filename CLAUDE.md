# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**joget-deployment-toolkit** is a focused Python toolkit for automating Joget DX form and application deployment. It provides a type-safe REST API client, MDM data deployment orchestration, and seamless integration with instance configuration managed by [sysadmin-scripts](https://github.com/your-org/sysadmin-scripts).

**Core Mission:** Simplify and automate deployment of forms, applications, and Master Data Management (MDM) to Joget DX instances.

**Version:** 1.0.0 (Fresh start after refactoring from joget-toolkit v3.0.0)

## What This Toolkit IS

✅ **Deployment automation** - Forms, applications, data submission, MDM orchestration
✅ **REST API client** - Type-safe Joget DX API client with multiple auth strategies
✅ **Form discovery** - Extract form definitions from Joget MySQL database
✅ **Shared config integration** - Zero-config client creation via `from_instance('jdx4')`
✅ **Production-ready** - Error handling, retries, type safety

## What This Toolkit IS NOT

❌ **Not FRS-specific** - Generic Joget deployment tool (not tied to FRS platform)
❌ **Not a health check tool** - Use sysadmin-scripts for health monitoring
❌ **Not a plugin manager** - Focused on deployment, not plugin discovery
❌ **Not a generic library** - Optimized for deployment workflows

## Architecture

### Modular Client Design

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
│   └── shared_loader.py      # Shared config integration (NEW in v1.0.0)
├── operations/               # High-level orchestration
│   └── mdm_deployer.py       # MDM deployment workflow
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

## Shared Config Integration (IMPORTANT)

### The Pattern

This toolkit integrates with **sysadmin-scripts** for instance configuration:

```
sysadmin-scripts (WRITES)
    ↓
~/.joget/instances.yaml (SINGLE SOURCE OF TRUTH)
    ↓
joget-deployment-toolkit (READS)
```

### Config File Structure

Located at `~/.joget/instances.yaml`:

```yaml
instances:
  jdx4:
    url: http://localhost:8084/jw
    web_port: 8084
    db_host: localhost
    db_port: 3309
    db_name: jwdb
    username: admin
    password_env: JDX4_PASSWORD  # References environment variable
    version: "9.0.0"
```

### Creating Config

Config is created/updated by sysadmin-scripts:

```bash
# In sysadmin-scripts directory
python scripts/joget_instance_manager.py --sync-all-to-joget
```

### Using Shared Config

```python
from joget_deployment_toolkit import JogetClient

# Zero-config client creation (reads from ~/.joget/instances.yaml)
client = JogetClient.from_instance('jdx4')

# Password is read from $JDX4_PASSWORD environment variable
```

### Implementation Details

- **Loader**: `src/joget_deployment_toolkit/config/shared_loader.py`
- **Functions**: `load_instances()`, `get_instance()`, `get_instance_password()`
- **Client method**: `JogetClient.from_instance()` in `client/__init__.py`

## Core Components

### 1. JogetClient

**Location:** `src/joget_deployment_toolkit/client/__init__.py`

Main API client that combines all operation mixins.

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

# Method 3: From environment variables
client = JogetClient.from_env()

# Method 4: From ClientConfig
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

### 2. FormDiscovery

**Location:** `src/joget_deployment_toolkit/discovery.py`

Extracts form definitions directly from Joget MySQL database.

```python
from joget_deployment_toolkit import FormDiscovery

db_config = {
    'host': 'localhost',
    'port': 3309,
    'database': 'jwdb',
    'user': 'root',
    'password': 'password'
}

discovery = FormDiscovery(db_config)
forms = discovery.discover_all_forms('farmersPortal', app_version='1')
```

**Use Case:** Extracting forms from live instances for migration or analysis.

### 3. MDMDataDeployer

**Location:** `src/joget_deployment_toolkit/operations/mdm_deployer.py`

High-level orchestration for deploying Master Data Management forms with CSV data.

```python
from joget_deployment_toolkit.operations import MDMDataDeployer
from joget_deployment_toolkit import JogetClient

client = JogetClient.from_instance('jdx5')

deployer = MDMDataDeployer(
    client=client,
    app_id='masterData',
    mdm_forms_dir='path/to/mdm/forms',
    csv_data_dir='path/to/csv/data'
)

result = deployer.deploy_all()
print(f"Deployed {result.forms_deployed} forms with {result.records_imported} records")
```

**Business Value:** Deploy 30+ MDM forms with CSV data in one operation.

### 4. Authentication Strategies

**Location:** `src/joget_deployment_toolkit/auth.py`

Pluggable authentication strategies:

- **SessionAuth** - Username/password (creates session)
- **APIKeyAuth** - API key header
- **BasicAuth** - HTTP Basic Authentication
- **NoAuth** - No authentication

**Custom Strategy:**

```python
from joget_deployment_toolkit.auth import AuthStrategy

class CustomAuth(AuthStrategy):
    def apply(self, request_kwargs):
        request_kwargs['headers']['X-Custom-Token'] = 'my-token'
        return request_kwargs
```

## Common Workflows

### Deploying Forms

```python
from joget_deployment_toolkit import JogetClient

client = JogetClient.from_instance('jdx4')

# List forms
forms = client.list_forms('farmersPortal')

# Get form definition
form_def = client.get_form('farmersPortal', 'farmer_basic')

# Create/update form
import json
with open('new_form.json') as f:
    form_json = json.load(f)
    client.create_form('farmersPortal', form_json)
```

### Deploying MDM

```python
from joget_deployment_toolkit.operations import MDMDataDeployer
from joget_deployment_toolkit import JogetClient

client = JogetClient.from_instance('jdx5')

deployer = MDMDataDeployer(
    client=client,
    app_id='masterData',
    mdm_forms_dir='mdm_forms/',
    csv_data_dir='csv_data/'
)

result = deployer.deploy_all()
```

### Extracting Forms from Database

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

for form in forms:
    print(f"{form.form_id}: {form.name}")
    # Save to file
    import json
    with open(f"{form.form_id}.json", 'w') as f:
        json.dump(form.to_dict(), f, indent=2)
```

## Error Handling

The toolkit provides specific exceptions for different error conditions:

```python
from joget_deployment_toolkit import (
    JogetClient,
    AuthenticationError,
    NotFoundError,
    ConflictError,
    ServerError,
    TimeoutError
)

client = JogetClient.from_instance('jdx4')

try:
    client.export_application('nonexistent', 'backup.zip')
except NotFoundError as e:
    print(f"Application not found: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ServerError as e:
    print(f"Server error: {e}")
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
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=joget_deployment_toolkit --cov-report=html

# Run specific tests
pytest tests/test_client.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Adding New Operations

To add a new operation mixin:

1. Create new file in `client/` (e.g., `processes.py`)
2. Define mixin class with methods
3. Add mixin to `JogetClient` inheritance in `client/__init__.py`
4. Update `__init__.py` exports
5. Add tests in `tests/`

## Migration from joget-toolkit v3.x

**Breaking Changes in v1.0.0:**

1. **Package Rename**: `joget_toolkit` → `joget_deployment_toolkit`
2. **Config Change**: `~/.frs-dev/config.yaml` → `~/.joget/instances.yaml`
3. **Client Creation**: `from_frs('jdx4')` → `JogetClient.from_instance('jdx4')`
4. **Removed**: Health checks, plugin discovery, FRS integration

**Migration Steps:**

```bash
# 1. Export config from sysadmin-scripts
cd /path/to/sysadmin-scripts
python scripts/joget_instance_manager.py --sync-all-to-joget

# 2. Install new toolkit
cd /path/to/joget-deployment-toolkit
pip install -e .

# 3. Update imports in your scripts
# OLD:
from joget_deployment_toolkit.integrations import from_frs
client = from_frs('jdx4')

# NEW:
from joget_deployment_toolkit import JogetClient
client = JogetClient.from_instance('jdx4')
```

## Related Projects

- **[sysadmin-scripts](https://github.com/your-org/sysadmin-scripts)** - Infrastructure layer for MySQL + Joget instance management (writes shared config)
- **[joget-form-generator](https://github.com/your-org/joget-form-generator)** - Generate Joget forms from YAML/Excel/DB schemas
- **[req-to-form-spec](https://github.com/your-org/req-to-form-spec)** - Convert business requirements to form specifications with AI

## Important Notes for AI Assistants

### When Working with This Code

1. **Never hardcode instance URLs/ports** - Always use shared config or ClientConfig
2. **Always use type hints** - This is a type-safe codebase (Pydantic models)
3. **Follow mixin pattern** - New operations go in separate mixin files
4. **Use repository pattern** - Database access goes through repositories
5. **Handle errors properly** - Use specific exception types
6. **Test your changes** - Add tests for new features

### When Testing or Making Joget API Calls

**CRITICAL: Always use the toolkit - never use raw curl/requests for Joget API operations.**

1. **Use JogetClient for all API calls** - `submit_form_data()`, `list_forms()`, `create_form()`, etc.
2. **If something fails, debug the toolkit** - Don't bypass it with curl commands
3. **Write test scripts using the toolkit** - This validates both the test and the toolkit itself

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

### When Helping Users

1. **Check if shared config exists** - `cat ~/.joget/instances.yaml`
2. **Verify password env vars set** - `echo $JDX4_PASSWORD`
3. **Recommend `from_instance()`** - Simplest and most maintainable
4. **Don't suggest health checks** - Point to sysadmin-scripts instead
5. **Don't suggest plugin operations** - Not part of this toolkit

### Common User Issues

**"Instance not found":**
```bash
# Solution: Export config from sysadmin-scripts
cd /path/to/sysadmin-scripts
python scripts/joget_instance_manager.py --sync-all-to-joget
```

**"Authentication failed":**
```bash
# Solution: Set password environment variable
export JDX4_PASSWORD=admin
```

**"Cannot import joget_deployment_toolkit":**
```bash
# Solution: Update imports to joget_deployment_toolkit
from joget_deployment_toolkit import JogetClient
```

## Key Files to Know

- `src/joget_deployment_toolkit/__init__.py` - Main exports
- `src/joget_deployment_toolkit/client/__init__.py` - JogetClient class
- `src/joget_deployment_toolkit/config/shared_loader.py` - Shared config integration
- `src/joget_deployment_toolkit/operations/mdm_deployer.py` - MDM deployment
- `pyproject.toml` - Package configuration (version, dependencies)
- `README.md` - User-facing documentation
