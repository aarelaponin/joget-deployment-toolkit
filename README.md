# Joget Deployment Toolkit

**Focused Python toolkit for Joget DX form and application deployment automation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/your-org/joget-deployment-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

`joget-deployment-toolkit` is a production-ready Python toolkit for automating Joget DX deployments. It provides a type-safe REST API client, MDM data deployment orchestration, and seamless integration with instance configuration managed by [sysadmin-scripts](https://github.com/your-org/sysadmin-scripts).

**Core Mission:** Simplify and automate deployment of forms, applications, and Master Data Management (MDM) to Joget DX instances.

## Features

### 🚀 Deployment Operations

- **Form Deployment**: Create, update, and manage Joget forms via REST API
- **Application Management**: List, export, import applications
- **Component Deployment**: Deploy complete components (MDM + forms) in correct order
- **MDM Data Deployment**: Deploy 30+ MDM forms with CSV data in one operation
- **Data Submission**: Submit form data with batch support
- **Form Discovery**: Extract form definitions from Joget database
- **Instance Inventory**: Check instance status and compare apps across environments

### 🔧 Developer Experience

- **Shared Configuration**: Zero-config client creation via `from_instance('jdx4')`
- **Multiple Auth Methods**: API Key, Session (username/password), Basic Auth
- **Type Safety**: Pydantic models for all operations
- **Error Handling**: Specific exceptions for HTTP status codes
- **Smart Retries**: Exponential backoff for transient failures

### 🎯 What Makes This Focused

This toolkit is **specifically designed for deployment workflows**. It does NOT include:
- ❌ Health checks (use sysadmin-scripts)
- ❌ Plugin discovery (not deployment-related)
- ❌ Framework-specific abstractions

## Installation

```bash
# Standard installation
pip install joget-deployment-toolkit

# Development mode (with test tools)
pip install -e ".[dev]"
```

## Quick Start

### Using Shared Config (Recommended)

The toolkit integrates with instance configuration from `~/.joget/instances.yaml` (managed by sysadmin-scripts):

```python
from joget_deployment_toolkit import JogetClient

# Connect to instance by name (reads from ~/.joget/instances.yaml)
client = JogetClient.from_instance('jdx4')

# List applications
apps = client.list_applications()
print(f"Found {len(apps)} applications")

# Export an application
client.export_application('farmersPortal', 'backup.zip')
```

**Password handling:** The toolkit reads passwords from environment variables:
```bash
export JDX4_PASSWORD=admin
export JDX5_PASSWORD=admin
```

### Alternative: Direct Configuration

```python
from joget_deployment_toolkit import JogetClient

# Method 1: Username/password authentication
client = JogetClient.from_credentials(
    "http://localhost:8084/jw",
    username="admin",
    password="admin"
)

# Method 2: API key authentication
from joget_deployment_toolkit.config import ClientConfig, AuthConfig

config = ClientConfig(
    base_url="http://localhost:8084/jw",
    auth=AuthConfig(type="api_key", api_key="your-key")
)
client = JogetClient(config)
```

## Configuration Setup

### 1. Configure Instances (One-Time Setup)

If using the recommended shared config approach, first export your instance configuration:

```bash
# In sysadmin-scripts directory
python scripts/joget_instance_manager.py --sync-all-to-joget
```

This creates `~/.joget/instances.yaml`:

```yaml
instances:
  jdx4:
    url: http://localhost:8084/jw
    web_port: 8084
    db_host: localhost
    db_port: 3309
    db_name: jwdb
    username: admin
    password_env: JDX4_PASSWORD
    version: "9.0.0"
```

### 2. Set Environment Variables

```bash
# Set passwords for instances
export JDX4_PASSWORD=admin
export JDX5_PASSWORD=admin
export JDX6_PASSWORD=admin
```

**Best practice:** Add these to your `.bashrc` or `.zshrc`, or use a password manager integration.

## Usage Examples

### Form Operations

```python
from joget_deployment_toolkit import JogetClient

client = JogetClient.from_instance('jdx4')

# List all forms in an application
forms = client.list_forms('farmersPortal')
for form in forms:
    print(f"Form: {form.form_id} - {form.name}")

# Get form definition
form_def = client.get_form('farmersPortal', 'farmer_basic')
print(f"Form has {len(form_def.get('elements', []))} elements")

# Create or update form
with open('new_form.json') as f:
    form_json = json.load(f)
    client.create_form('farmersPortal', form_json)
```

### Application Management

```python
# List all applications
apps = client.list_applications()

# Export application
client.export_application('farmersPortal', 'backup.zip')

# Import application
client.import_application('new_app.zip')
```

### Data Submission

```python
# Submit data to a form
data = {
    'farmer_name': 'John Doe',
    'district': 'Maseru',
    'crop_type': 'Maize'
}
result = client.submit_form_data('farmersPortal', 'farmer_registration', data)
print(f"Record ID: {result.record_id}")

# Batch submission
records = [
    {'name': 'Alice', 'email': 'alice@example.com'},
    {'name': 'Bob', 'email': 'bob@example.com'},
]
batch_result = client.submit_batch('myApp', 'contacts', records)
print(f"Success: {batch_result.success_count}, Failed: {batch_result.fail_count}")
```

### Component Deployment

Deploy complete components containing MDM tables and forms that depend on them:

```python
from joget_deployment_toolkit import JogetClient, ComponentDeployer
from pathlib import Path

client = JogetClient.from_instance('jdx4')
deployer = ComponentDeployer(client)

# Deploy complete component
result = deployer.deploy_component(
    component_dir=Path("equipment_component"),
    target_app_id="farmersPortal",
    formcreator_api_id="fc_api"
)

print(result)  # ✓ equipment_component: MDM 2/2, Forms 3/3
```

**Expected component structure:**
```
equipment_component/
├── mdm/                      # Deployed FIRST
│   ├── forms/
│   │   └── md25equipment.json
│   └── data/
│       └── md25equipment.csv
└── forms/                    # Deployed SECOND
    └── equipmentRequest.json
```

### MDM Deployment

For deploying MDM forms with CSV data (lower-level API):

```python
from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.operations import MDMDataDeployer
from pathlib import Path

client = JogetClient.from_instance('jdx5')
deployer = MDMDataDeployer(client)

# Deploy all MDM forms from directories
results = deployer.deploy_all_mdm_from_directory(
    forms_dir=Path("mdm/forms"),
    data_dir=Path("mdm/data"),
    target_app_id="farmersPortal",
    formcreator_api_id="fc_api"
)

for r in results:
    print(r)  # ✓ md01maritalStatus: 15 records
```

### Instance Inventory

Check instance status before deployment and compare apps across environments:

```python
from joget_deployment_toolkit import list_instances, get_instance_status, compare_apps

# List all configured instances with status
instances = list_instances()
for inst in instances:
    print(inst)  # ✓ jdx4 (client_alpha) - http://localhost:8084/jw [running]

# Check specific instance before deployment
status = get_instance_status("jdx4")
if status.reachable:
    print(f"Instance up ({status.response_time_ms}ms)")
else:
    print(f"Instance down: {status.error}")

# Compare apps between staging and production
diff = compare_apps("jdx2", "jdx4")
print(f"Only in staging: {diff.only_in_a}")
print(f"Version differences: {diff.version_diff}")
```

### Form Discovery (Database Access)

Extract form definitions directly from the Joget database:

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

# Discover all forms in an application
forms = discovery.discover_all_forms('farmersPortal', app_version='1')

for form in forms:
    print(f"{form.form_id}: {form.name} ({form.table_name})")
    print(f"  Fields: {len(form.elements)}")
```

## Authentication

The toolkit supports multiple authentication strategies:

### 1. Session Authentication (Recommended)

```python
client = JogetClient.from_credentials(
    "http://localhost:8080/jw",
    username="admin",
    password="admin"
)
```

### 2. API Key Authentication

```python
from joget_deployment_toolkit.config import ClientConfig, AuthConfig

config = ClientConfig(
    base_url="http://localhost:8080/jw",
    auth=AuthConfig(type="api_key", api_key="your-api-key")
)
client = JogetClient(config)
```

### 3. Basic HTTP Authentication

```python
from joget_deployment_toolkit.auth import BasicAuth

auth = BasicAuth(username="admin", password="admin")
config = ClientConfig(
    base_url="http://localhost:8080/jw",
    auth=auth
)
client = JogetClient(config, auth_strategy=auth)
```

### 4. Custom Authentication

```python
from joget_deployment_toolkit.auth import AuthStrategy

class CustomAuth(AuthStrategy):
    def apply(self, request_kwargs):
        request_kwargs['headers']['X-Custom-Token'] = 'my-token'
        return request_kwargs

client = JogetClient(config, auth_strategy=CustomAuth())
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

## Configuration Options

### ClientConfig

```python
from joget_deployment_toolkit.config import ClientConfig

config = ClientConfig(
    base_url="http://localhost:8080/jw",
    auth={"type": "session", "username": "admin", "password": "admin"},
    timeout=30,              # Request timeout in seconds
    verify_ssl=True,         # SSL certificate verification
    retry_count=3,           # Number of retries for failed requests
    retry_backoff=2.0,       # Exponential backoff multiplier
    debug=False              # Enable debug logging
)
```

### DatabaseConfig

```python
from joget_deployment_toolkit.config import DatabaseConfig

db_config = DatabaseConfig(
    host='localhost',
    port=3309,
    database='jwdb',
    user='root',
    password='password',
    pool_size=5,            # Connection pool size
    pool_name='joget_pool'
)
```

## Integration with sysadmin-scripts

This toolkit is designed to work seamlessly with [sysadmin-scripts](https://github.com/your-org/sysadmin-scripts) for instance management:

**Workflow:**
1. **sysadmin-scripts**: Manages MySQL + Joget instances, exports config
2. **joget-deployment-toolkit**: Reads config, deploys forms/apps/data

**Config flow:**
```
sysadmin-scripts (WRITES)
    ↓
~/.joget/instances.yaml (SINGLE SOURCE OF TRUTH)
    ↓
joget-deployment-toolkit (READS)
```

**Example integration:**

```bash
# 1. Set up instance (sysadmin-scripts)
cd sysadmin-scripts
python scripts/joget_instance_manager.py --setup joget_instance_4

# 2. Export config to shared location
python scripts/joget_instance_manager.py --sync-all-to-joget

# 3. Deploy forms (joget-deployment-toolkit)
cd ../deployment-scripts
python deploy_mdm.py --instance jdx4  # Uses shared config automatically
```

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

## Architecture

The toolkit uses a modular architecture with clear separation of concerns:

```
joget_deployment_toolkit/
├── client/                  # API client with operation mixins
│   ├── base.py             # HTTP client foundation
│   ├── forms.py            # Form CRUD operations
│   ├── applications.py     # Application management
│   └── data.py             # Data submission
├── auth.py                 # Authentication strategies
├── config/                 # Configuration management
│   ├── models.py           # Pydantic config models
│   ├── loader.py           # Config file loading
│   └── shared_loader.py    # Shared config integration
├── operations/             # High-level orchestration
│   ├── mdm_deployer.py     # MDM deployment workflow
│   └── component_deployer.py # Component deployment (MDM + forms)
├── inventory.py            # Instance status & app comparison
├── database/               # Database access
│   └── repositories/       # Repository pattern
├── discovery.py            # Form discovery from DB
├── models.py               # API response models
└── exceptions.py           # Error handling
```

## Migration from v3.x (joget-toolkit)

If you're upgrading from the previous `joget-toolkit` v3.x:

### Package Rename

```python
# OLD (v3.x)
from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.integrations import from_frs

# NEW (v1.0.0)
from joget_deployment_toolkit import JogetClient
```

### Configuration Changes

```python
# OLD (v3.x) - FRS integration
from joget_deployment_toolkit.integrations import from_frs
client = from_frs('jdx4')  # Read from ~/.frs-dev/config.yaml

# NEW (v1.0.0) - Shared config
from joget_deployment_toolkit import JogetClient
client = JogetClient.from_instance('jdx4')  # Read from ~/.joget/instances.yaml
```

### Config File Migration

```bash
# If you have ~/.frs-dev/config.yaml, re-export from sysadmin-scripts:
cd sysadmin-scripts
python scripts/joget_instance_manager.py --sync-all-to-joget

# This creates ~/.joget/instances.yaml with the same instance data
```

### Removed Features

The following features were removed in v1.0.0 (use sysadmin-scripts instead):
- ❌ `client.test_connection()` → Use `sysadmin-scripts/scripts/health_check.py`
- ❌ `client.get_health_status()` → Use health_check.py
- ❌ `client.list_plugins()` → Not needed for deployment workflows

## Changelog

### v1.1.0 (2025-12-16)

**New Features:**
- Added `ComponentDeployer` for deploying complete components (MDM + forms) in correct order
- Added Inventory API for pre-deployment checks:
  - `list_instances()` - List all configured instances with running status
  - `get_instance_status()` - Check single instance health
  - `get_apps_overview()` - Get apps across multiple instances
  - `compare_apps()` - Compare applications between environments
- Added `JogetClient.check_instance()` class method for quick connectivity checks

### v1.0.0 (2025-01-19)

**Breaking Changes:**
- Renamed package from `joget-toolkit` to `joget-deployment-toolkit`
- Removed FRS Platform integration (replaced with shared config)
- Removed health check operations (use sysadmin-scripts instead)
- Removed plugin discovery (not deployment-related)
- Changed config location: `~/.frs-dev/config.yaml` → `~/.joget/instances.yaml`

**New Features:**
- Added `JogetClient.from_instance()` for zero-config setup
- Added shared config loader (`config/shared_loader.py`)
- PyYAML now a core dependency (not optional)

**Improvements:**
- Simplified focus on deployment operations
- Clearer integration with sysadmin-scripts
- Better documentation and examples

## Contributing

Contributions are welcome! This is a focused tool for deployment automation.

**Before contributing:**
1. Check existing issues and PRs
2. Ensure changes align with deployment focus
3. Add tests for new features
4. Update documentation

## License

MIT License - see [LICENSE](LICENSE) file

## Related Projects

- **[sysadmin-scripts](https://github.com/your-org/sysadmin-scripts)** - Infrastructure layer for MySQL + Joget instance management
- **[joget-form-generator](https://github.com/your-org/joget-form-generator)** - Generate Joget forms from YAML/Excel/DB schemas
- **[req-to-form-spec](https://github.com/your-org/req-to-form-spec)** - Convert business requirements to form specifications with AI

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/joget-deployment-toolkit/issues)
- **Documentation**: [Full Documentation](https://joget-deployment-toolkit.readthedocs.io)
