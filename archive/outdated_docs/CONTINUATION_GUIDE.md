# Joget-Toolkit Refactoring - Continuation Guide

**Quick Start Guide for Resuming Development**

---

## Current Status (2025-11-16)

✅ **Week 1: Foundation Layer - 100% Complete**
✅ **Week 2: Client Refactoring - 38% Complete** (3/8 tasks done)

**Lines Written**: 2,578 across 11 modules
**Overall Progress**: 11/31 tasks (35%)

---

## What's Already Done

### ✅ Completed Modules

1. **Configuration System** (config/)
   - `models.py` - Pydantic v2 configuration models
   - `loader.py` - Multi-source configuration loading
   - `validator.py` - Configuration validation + connectivity tests
   - `profiles.py` - Environment profiles (dev/staging/prod/test)

2. **Database Layer** (database/)
   - `connection.py` - Thread-safe connection pool

3. **Client Foundation** (client/)
   - `http_client.py` - HTTP client with retry logic
   - `base.py` - BaseClient with session management
   - `forms.py` - FormOperations mixin (CRUD + batch)

### 📋 Documentation Created

- `REFACTORING_STATUS.md` - Comprehensive status document (12,000+ lines)
- `CONTINUATION_GUIDE.md` - This file
- Skeleton test files in `tests/refactored/`
- Migration helper script: `migrate_to_modular.py`

---

## Next 5 Tasks (Resume Here)

### Task 1: ApplicationOperations Mixin (~2 hours)

**File**: `src/joget_deployment_toolkit/client/applications.py`

**Source Reference**: Lines 1056-1180 in original `client.py`

**Implementation Pattern** (follow FormOperations):

```python
"""
Application operations mixin for Joget client.

Provides all application-related operations including:
- Listing and querying applications
- Exporting applications to ZIP
- Importing applications from ZIP
- Batch operations
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging

from ..models import ApplicationInfo, ApplicationDetails, ExportResult, ImportResult, application_info_from_dict
from ..exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

class ApplicationOperations:
    """Mixin providing application management operations."""

    def list_applications(self) -> List[ApplicationInfo]:
        """List all published applications."""
        endpoint = "/web/json/apps/published/list"
        data = self.get(endpoint)

        apps = []
        for item in data.get("data", []):
            apps.append(application_info_from_dict(item))
        return apps

    def get_application(
        self,
        app_id: str,
        *,
        app_version: str = "1"
    ) -> ApplicationDetails:
        """Get application details."""
        endpoint = f"/web/json/console/app/{app_id}/{app_version}"
        data = self.get(endpoint)

        return ApplicationDetails(
            id=data.get("id", app_id),
            name=data.get("name", ""),
            version=data.get("version", app_version),
            published=data.get("published", False),
            description=data.get("description"),
            raw_data=data
        )

    def export_application(
        self,
        app_id: str,
        output_path: Union[str, Path],
        *,
        app_version: str = "1"
    ) -> ExportResult:
        """Export application to ZIP file."""
        # Read lines 1104-1140 from original client.py for implementation
        # Uses streaming response to save file
        pass

    def import_application(self, zip_path: Union[str, Path]) -> ImportResult:
        """Import application from ZIP file."""
        # Read lines 1142-1180 from original client.py
        # Uses multipart file upload
        pass

    def batch_export_applications(
        self,
        app_ids: List[str],
        output_dir: Path,
        *,
        app_version: str = "1",
        stop_on_error: bool = False
    ) -> List[ExportResult]:
        """Export multiple applications to directory."""
        # Similar pattern to batch_create_forms in FormOperations
        pass
```

**Steps**:
1. Read original client.py lines 1056-1180
2. Extract methods to new file
3. Follow FormOperations pattern for consistency
4. Add comprehensive docstrings
5. Handle errors appropriately

### Task 2: PluginOperations Mixin (~1 hour)

**File**: `src/joget_deployment_toolkit/client/plugins.py`

**Source Reference**: Lines 1181-1250 in original `client.py`

**Implementation**:

```python
"""
Plugin operations mixin for Joget client.
"""

from typing import List, Dict, Any, Optional
import logging

from ..models import PluginInfo, PluginDetails, plugin_info_from_dict

logger = logging.getLogger(__name__)

class PluginOperations:
    """Mixin for plugin-related operations."""

    def list_plugins(
        self,
        *,
        plugin_type: Optional[str] = None
    ) -> List[PluginInfo]:
        """List all plugins, optionally filtered by type."""
        # Read lines 1181-1220 from original client.py
        pass

    def get_plugin(self, plugin_id: str) -> PluginDetails:
        """Get plugin details."""
        # Read lines 1221-1240 from original client.py
        pass

    def list_plugins_by_type(self, plugin_type: str) -> List[PluginInfo]:
        """Convenience method to filter plugins."""
        return self.list_plugins(plugin_type=plugin_type)
```

### Task 3: HealthOperations Mixin (~1 hour)

**File**: `src/joget_deployment_toolkit/client/health.py`

**Source Reference**: Lines 1251-1290 in original `client.py`

**Implementation**:

```python
"""
Health check operations mixin for Joget client.
"""

from typing import Dict, Any
import logging

from ..models import SystemInfo, Health, HealthStatus, HealthCheckResult

logger = logging.getLogger(__name__)

class HealthOperations:
    """Mixin for health check operations."""

    def test_connection(self) -> bool:
        """Test if connection to Joget is successful."""
        try:
            response = self.get("/")
            return response.status_code < 500
        except:
            return False

    def get_system_info(self) -> SystemInfo:
        """Get Joget system information."""
        # Read lines 1251-1270 from original client.py
        pass

    def get_health_status(self) -> HealthCheckResult:
        """Comprehensive health check."""
        # Read lines 1271-1290 from original client.py
        # Check API connectivity, database, system info
        # Return HEALTHY, DEGRADED, or UNHEALTHY
        pass
```

### Task 4: JogetClient Facade (~1 hour)

**File**: `src/joget_deployment_toolkit/client/__init__.py` (update existing)

**Implementation**:

```python
"""
Joget client package.

This package contains the refactored, modular client implementation.
"""

from typing import Union, Dict, Any, Optional
from ..config import ClientConfig
from .base import BaseClient
from .forms import FormOperations
from .applications import ApplicationOperations
from .plugins import PluginOperations
from .health import HealthOperations


class JogetClient(
    BaseClient,
    FormOperations,
    ApplicationOperations,
    PluginOperations,
    HealthOperations
):
    """
    Main Joget DX API Client.

    Combines all operation mixins into a single, comprehensive client.
    Maintains 100% backward compatibility with v2.0.0.

    Example (new way):
        >>> from joget_deployment_toolkit.config import ClientConfig
        >>> config = ClientConfig(
        ...     base_url="http://localhost:8080/jw",
        ...     auth={"type": "api_key", "api_key": "my-key"}
        ... )
        >>> client = JogetClient(config)

    Example (old way - still works):
        >>> client = JogetClient(
        ...     "http://localhost:8080/jw",
        ...     api_key="my-key"
        ... )
    """

    def __init__(
        self,
        config: Union[ClientConfig, str],
        auth_strategy: Optional = None,
        **kwargs
    ):
        """
        Initialize Joget client.

        Args:
            config: ClientConfig instance or base_url (backward compat)
            auth_strategy: Optional authentication strategy
            **kwargs: Additional arguments for backward compatibility
        """
        # BaseClient handles both old and new initialization
        super().__init__(config, auth_strategy, **kwargs)

    # Alternative constructors for convenience
    @classmethod
    def from_credentials(
        cls,
        base_url: str,
        username: str,
        password: str,
        **kwargs
    ) -> "JogetClient":
        """
        Create client with username/password authentication.

        Args:
            base_url: Joget instance URL
            username: Username
            password: Password
            **kwargs: Additional configuration options

        Returns:
            JogetClient instance

        Example:
            >>> client = JogetClient.from_credentials(
            ...     "http://localhost:8080/jw",
            ...     "admin",
            ...     "admin"
            ... )
        """
        config = ClientConfig.from_kwargs(
            base_url=base_url,
            username=username,
            password=password,
            **kwargs
        )
        return cls(config)

    @classmethod
    def from_config(
        cls,
        config: Union[ClientConfig, Dict[str, Any]],
        **kwargs
    ) -> "JogetClient":
        """
        Create client from configuration.

        Args:
            config: ClientConfig instance or configuration dictionary
            **kwargs: Override configuration values

        Returns:
            JogetClient instance

        Example:
            >>> config = ClientConfig(
            ...     base_url="http://localhost:8080/jw",
            ...     auth={"type": "api_key", "api_key": "key"}
            ... )
            >>> client = JogetClient.from_config(config)
        """
        if isinstance(config, dict):
            config = ClientConfig(**config)
        return cls(config, **kwargs)

    @classmethod
    def from_env(cls, prefix: str = "JOGET_", **kwargs) -> "JogetClient":
        """
        Create client from environment variables.

        Args:
            prefix: Environment variable prefix (default: JOGET_)
            **kwargs: Override configuration values

        Returns:
            JogetClient instance

        Example:
            >>> # Set environment: JOGET_BASE_URL, JOGET_API_KEY
            >>> client = JogetClient.from_env()
        """
        config = ClientConfig.from_env(prefix)
        return cls(config, **kwargs)


__all__ = ["JogetClient"]
```

### Task 5: Backward Compatibility Wrapper (~30 minutes)

**File**: `src/joget_deployment_toolkit/client.py` (modify existing)

**Strategy**: Keep file, import from new location

```python
"""
Joget DX API Client

DEPRECATED: This module provides backward compatibility with v2.0.0.
The implementation has been refactored into joget_deployment_toolkit.client package.

For new code, use:
    from joget_deployment_toolkit import JogetClient
    # or
    from joget_deployment_toolkit.client import JogetClient

This file will be removed in v3.0.0.
"""

import warnings

# Import new implementation
from .client import JogetClient as _ModularJogetClient

# Export as JogetClient for backward compatibility
class JogetClient(_ModularJogetClient):
    """
    Backward compatibility wrapper for JogetClient.

    This class is deprecated and will be removed in v3.0.0.
    Use joget_deployment_toolkit.client.JogetClient instead.
    """

    def __init__(self, base_url: str, **kwargs):
        """
        Initialize Joget API client (v2.0.0 compatible).

        DEPRECATED: Use ClientConfig-based initialization.

        Args:
            base_url: Joget instance URL
            **kwargs: Client options
        """
        # Optionally show deprecation warning
        # warnings.warn(
        #     "Direct initialization is deprecated. "
        #     "Use JogetClient.from_config() or pass ClientConfig instance.",
        #     DeprecationWarning,
        #     stacklevel=2
        # )

        # Call parent with old-style args
        super().__init__(base_url, **kwargs)


# Re-export everything for backward compatibility
__all__ = ['JogetClient']
```

---

## Testing After Tasks 1-5

### Quick Verification

```python
# Test old way still works
from joget_deployment_toolkit import JogetClient

client = JogetClient(
    "http://localhost:8080/jw",
    api_key="test-key"
)

# Should have all methods
assert hasattr(client, 'list_forms')
assert hasattr(client, 'list_applications')
assert hasattr(client, 'list_plugins')
assert hasattr(client, 'test_connection')

print("✅ Backward compatibility maintained!")
```

### Run Existing Tests

```bash
cd /Users/aarelaponin/PycharmProjects/dev/joget-toolkit

# Run all existing tests
pytest tests/ -v

# Should pass with no modifications needed
```

---

## Week 3 Preview: Repository Pattern

### BaseRepository Implementation

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from ..connection import DatabaseConnectionPool

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository with common database operations."""

    def __init__(self, connection_pool: DatabaseConnectionPool):
        self.pool = connection_pool

    @abstractmethod
    def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID."""
        pass

    def execute_query(self, query: str, params: tuple = None) -> List[dict]:
        """Execute SELECT query."""
        with self.pool.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
```

---

## Quick Reference

### Import Locations

```python
# Configuration
from joget_deployment_toolkit.config import (
    ClientConfig,
    DatabaseConfig,
    ConfigurationLoader,
    validate_config,
    get_profile_config,
    ProfileType
)

# Database
from joget_deployment_toolkit.database import DatabaseConnectionPool

# Client (after Week 2 complete)
from joget_deployment_toolkit import JogetClient
# or
from joget_deployment_toolkit.client import JogetClient
```

### Key Files to Reference

1. **Original client.py**: `/Users/aarelaponin/PycharmProjects/dev/joget-toolkit/src/joget_deployment_toolkit/client.py`
   - Lines 1056-1180: Application operations
   - Lines 1181-1250: Plugin operations
   - Lines 1251-1290: Health operations

2. **FormOperations (template)**: `/Users/aarelaponin/PycharmProjects/dev/joget-toolkit/src/joget_deployment_toolkit/client/forms.py`
   - Follow this pattern for ApplicationOperations, PluginOperations, HealthOperations

3. **BaseClient (foundation)**: `/Users/aarelaponin/PycharmProjects/dev/joget-toolkit/src/joget_deployment_toolkit/client/base.py`
   - Provides: self.get(), self.post(), self.request(), self.config, self.logger

### Coding Patterns to Follow

1. **Mixin Structure**:
   - No `__init__` method in mixins
   - Assume `self.get()`, `self.post()`, `self.request()` exist
   - Assume `self.config` and `self.logger` exist

2. **Error Handling**:
   ```python
   from ..exceptions import NotFoundError, ValidationError, JogetAPIError

   if not data:
       raise NotFoundError(f"Form {form_id} not found")
   ```

3. **Docstrings**:
   ```python
   def method_name(self, arg1: str, *, arg2: str = "default") -> ReturnType:
       """
       Brief description.

       Endpoint: /web/json/path/to/endpoint

       Args:
           arg1: Description
           arg2: Description (default: "default")

       Returns:
           Description of return value

       Raises:
           NotFoundError: When resource doesn't exist
           JogetAPIError: On API errors

       Example:
           >>> client = JogetClient(...)
           >>> result = client.method_name("value")
           >>> print(result)
       """
   ```

4. **Logging**:
   ```python
   if self.config.debug:
       self.logger.debug(f"Operation: {details}")
   ```

---

## Commit Strategy

After completing each task:

```bash
git add src/joget_deployment_toolkit/client/applications.py
git commit -m "feat: implement ApplicationOperations mixin

- Add list_applications, get_application methods
- Add export_application, import_application methods
- Add batch_export_applications for bulk operations
- Follow FormOperations pattern for consistency
- ~300 lines, comprehensive docstrings

Refs: Week 2 Task 1 of refactoring plan"
```

---

## Time Estimates

| Task | Time | Complexity |
|------|------|------------|
| ApplicationOperations | 2 hours | Medium (file upload) |
| PluginOperations | 1 hour | Low |
| HealthOperations | 1 hour | Low |
| JogetClient Facade | 1 hour | Low |
| Backward Compat | 30 min | Low |
| **Total Week 2** | **5.5 hours** | - |

---

## Success Checklist

After completing Tasks 1-5:

- [ ] All 5 tasks implemented
- [ ] All methods have docstrings
- [ ] Error handling in place
- [ ] Logging added for debug mode
- [ ] Old tests pass without modification
- [ ] Can import: `from joget_deployment_toolkit import JogetClient`
- [ ] Can use old syntax: `JogetClient("url", api_key="key")`
- [ ] Can use new syntax: `JogetClient(config)`
- [ ] All operation methods available

Test it:
```python
from joget_deployment_toolkit import JogetClient

client = JogetClient("http://localhost:8080/jw", api_key="test")

# Should all work
client.list_forms("app")
client.list_applications()
client.list_plugins()
client.test_connection()
```

---

## Need Help?

1. **Check REFACTORING_STATUS.md**: Comprehensive documentation
2. **Review FormOperations.py**: Template for mixin pattern
3. **Read original client.py**: Source code to extract from
4. **Follow the patterns**: Consistency is key

---

**Ready to Resume!** Start with Task 1: ApplicationOperations mixin.

Good luck! 🚀
