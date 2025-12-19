# Joget Deployment Toolkit

**Focused Python toolkit for Joget DX form and application deployment automation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/aarelaponin/joget-deployment-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

`joget-deployment-toolkit` is a production-ready Python toolkit for automating Joget DX deployments. It provides a type-safe REST API client, MDM data deployment orchestration, and seamless integration with instance configuration managed by [joget-instance-manager](https://github.com/aarelaponin/joget-instance-manager).

**Core Mission:** Simplify and automate deployment of forms, applications, and Master Data Management (MDM) to Joget DX instances.

### Tool Ecosystem

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

## Features

### Deployment Operations

- **Form Deployment**: Create, update, and manage Joget forms via REST API
- **Application Management**: List, export, import applications
- **Component Deployment**: Deploy complete components (MDM + forms) in correct order
- **MDM Data Deployment**: Deploy 30+ MDM forms with CSV data in one operation
- **Data Submission**: Submit form data with batch support
- **Form Discovery**: Extract form definitions from Joget database
- **Instance Inventory**: Check instance status and compare apps across environments

### Developer Experience

- **Shared Configuration**: Zero-config client creation via `from_instance('jdx4')`
- **Multiple Auth Methods**: API Key, Session (username/password), Basic Auth
- **Type Safety**: Pydantic models for all operations
- **Error Handling**: Specific exceptions for HTTP status codes
- **Smart Retries**: Exponential backoff for transient failures

### What This Toolkit Does NOT Do

This toolkit is **specifically designed for deployment workflows**. For instance management, use [joget-instance-manager](https://github.com/aarelaponin/joget-instance-manager):
- Instance setup/reset/configuration
- Health checks
- Database schema management
- Tomcat/Glowroot configuration

## Installation

```bash
# Standard installation
pip install joget-deployment-toolkit

# Development mode (with test tools)
pip install -e ".[dev]"
```

## Quick Start

### Using Shared Config (Recommended)

The toolkit integrates with instance configuration from `~/.joget/instances.yaml` (managed by joget-instance-manager):

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

### Password Handling

The toolkit reads the **web admin password** from environment variables. This is one of three password types in the ecosystem:

```bash
# MySQL root passwords - used by joget-instance-manager for database creation
MYSQL4_ROOT_PASSWORD=root_password

# Database user passwords - used by Joget app to connect to database
JOGET_CLIENT_ALPHA_PASSWORD=db_user_password

# Web admin passwords - used by THIS TOOLKIT for REST API access
export JDX4_PASSWORD=admin
export JDX5_PASSWORD=admin
```

**This toolkit only needs the web admin password (JDX{N}_PASSWORD).** The other passwords are managed by joget-instance-manager.

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

### 1. Set Up Instance (joget-instance-manager)

First, ensure the instance is configured using joget-instance-manager:

```bash
# In joget-instance-manager directory
python scripts/joget_instance_manager.py --setup jdx4
```

This creates `~/.joget/instances.yaml` with instance configuration:

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
      password_env: JDX4_PASSWORD
```

### 2. Set Web Admin Password

```bash
# Set password for REST API access
export JDX4_PASSWORD=admin
```

**Best practice:** Add to your `.bashrc` or `.zshrc`, or use a password manager integration.

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

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=joget_deployment_toolkit --cov-report=html
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
- Removed health check operations (use joget-instance-manager instead)
- Removed plugin discovery (not deployment-related)
- Changed config location: `~/.frs-dev/config.yaml` → `~/.joget/instances.yaml`

**New Features:**
- Added `JogetClient.from_instance()` for zero-config setup
- Added shared config loader (`config/shared_loader.py`)

## Related Projects

- **[joget-instance-manager](https://github.com/aarelaponin/joget-instance-manager)** - Instance configuration layer: setup, reset, configure Joget instances (writes `~/.joget/instances.yaml`)
- **[joget-form-generator](https://github.com/aarelaponin/joget-form-generator)** - Generate Joget forms from YAML/Excel/DB schemas

## License

MIT License - see [LICENSE](LICENSE) file
