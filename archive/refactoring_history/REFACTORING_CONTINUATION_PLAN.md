# Joget-Toolkit Refactoring - Detailed Continuation Plan

**Date**: November 16, 2025
**Current Status**: Day 1 Complete (v3.0 clean break in progress)
**Remaining Work**: 8-10 hours over 2 days
**Target**: v3.0.0 (breaking change release)

---

## Executive Summary

### What's Done (Day 1 - 3.5 hours)
✅ **Removed backward compatibility** - Clean v3.0 break
✅ **Fixed Pydantic v2 bugs** - `.dict()` → `.model_dump()`
✅ **Simplified configuration** - Removed `from_kwargs()` and `to_kwargs()`
✅ **Updated 1 test** - Pattern established

### What's Needed (Days 2-3)
🔧 **Fix 41 remaining tests** - Follow established pattern (4-5 hours)
🔧 **Standardize error handling** - All operations raise exceptions (2-3 hours)
🔧 **Verify integration** - End-to-end testing (1-2 hours)
🔧 **Documentation** - Update for v3.0 breaking changes (1 hour)

### Key Insight from Day 1
**The clean break approach is working beautifully:**
- Code is significantly simpler without backward compat
- Less confusion about which pattern to use
- Architecture is cleaner and more maintainable
- Test updates are mechanical, not complex

---

## Current Architecture Analysis

### ✅ What's Working Well

1. **Modular client structure** (5 mixins):
   - `BaseClient` - HTTP operations, session management
   - `FormOperations` - Form CRUD
   - `ApplicationOperations` - App management
   - `PluginOperations` - Plugin listing
   - `HealthOperations` - Connection testing

2. **Configuration system** (Pydantic v2):
   - `ClientConfig` - Main configuration model
   - `AuthConfig` - Authentication settings
   - `RetryConfig` - Retry behavior
   - Multi-source loading (env, file, dict)

3. **Authentication strategies**:
   - `APIKeyAuth` - API key authentication
   - `SessionAuth` - Session-based auth
   - `BasicAuth` - HTTP basic auth
   - `NoAuth` - No authentication

4. **Repository pattern**:
   - `DatabaseConnectionPool` - Thread-safe pooling
   - `BaseRepository` - Common operations
   - `FormRepository` - Form data access
   - `ApplicationRepository` - App data access

### ❌ What Needs Fixing

1. **Tests using old patterns**:
   - Old: `client = JogetClient(base_url, api_key=key)`
   - New: `client = JogetClient(ClientConfig(...))`
   - Old: `client.timeout`
   - New: `client.config.timeout`
   - Old: `patch('joget_deployment_toolkit.client.SessionAuth')`
   - New: `patch('joget_deployment_toolkit.auth.SessionAuth')`

2. **Inconsistent error handling**:
   - Some methods return `bool` (e.g., `delete_form()`)
   - Some return result objects (e.g., `FormResult`)
   - Some raise exceptions (e.g., `get_form()`)
   - **Decision**: Standardize on exceptions (Pythonic)

3. **Incomplete helper methods**:
   - `JogetClient.from_credentials()` exists but needs testing
   - `JogetClient.from_config()` exists but needs testing
   - `JogetClient.from_env()` exists but needs testing

---

## Day 2: Test Updates & Error Handling (5-6 hours)

### Phase 1: Create Test Helper (30 min)

**Goal**: Simplify test setup to reduce repetition

**File**: `tests/conftest.py`

```python
import pytest
from joget_deployment_toolkit.config import ClientConfig, AuthConfig, AuthType
from joget_deployment_toolkit.client import JogetClient
from joget_deployment_toolkit.auth import APIKeyAuth, SessionAuth
from unittest.mock import Mock

@pytest.fixture
def mock_config(base_url, api_key):
    """Create a mock ClientConfig for testing."""
    return ClientConfig(
        base_url=base_url,
        auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
        timeout=30,
        debug=False
    )

@pytest.fixture
def mock_session_config(base_url, credentials):
    """Create a mock ClientConfig with session auth."""
    return ClientConfig(
        base_url=base_url,
        auth=AuthConfig(
            type=AuthType.SESSION,
            username=credentials["username"],
            password=credentials["password"]
        ),
        timeout=30
    )

@pytest.fixture
def mock_client(mock_config):
    """Create a fully mocked JogetClient."""
    with patch('joget_deployment_toolkit.auth.select_auth_strategy') as mock_select:
        mock_auth = Mock(spec=APIKeyAuth)
        mock_auth.authenticate = Mock(return_value=True)
        mock_auth.get_headers = Mock(return_value={"Authorization": "Bearer test"})
        mock_select.return_value = mock_auth

        client = JogetClient(mock_config, auth_strategy=mock_auth)
        return client

def create_config(**overrides):
    """Helper to create ClientConfig with overrides."""
    base = {
        "base_url": "http://localhost:8080/jw",
        "auth": {"type": "api_key", "api_key": "test-key"},
        "timeout": 30
    }
    base.update(overrides)
    return ClientConfig(**base)
```

**Rationale**:
- Eliminates repetitive config creation in each test
- Provides standard mocked client for most tests
- Easy to override for specific test scenarios

---

### Phase 2: Update Test Patterns (3-4 hours)

**Strategy**: Fix tests in groups by test class

#### Group 1: TestClientInitialization (8 tests)

**Pattern to apply**:

```python
# OLD (broken)
def test_init_with_username_password(self, base_url, credentials):
    with patch('joget_deployment_toolkit.client.SessionAuth') as mock_auth:
        client = JogetClient(base_url, username=..., password=...)

# NEW (working)
def test_init_with_username_password(self, base_url, credentials):
    config = ClientConfig(
        base_url=base_url,
        auth=AuthConfig(
            type=AuthType.SESSION,
            username=credentials["username"],
            password=credentials["password"]
        )
    )
    with patch('joget_deployment_toolkit.auth.select_auth_strategy') as mock_select:
        mock_auth = Mock()
        mock_auth.authenticate = Mock(return_value=True)
        mock_select.return_value = mock_auth

        client = JogetClient(config)
        assert client.base_url == base_url
```

**Tests to update**:
1. ✅ `test_init_with_api_key` - Already done
2. `test_init_with_username_password` - Apply pattern above
3. `test_init_custom_timeout` - Use config with custom timeout
4. `test_init_custom_retry_settings` - Use config with retry settings
5. `test_init_with_debug` - Use config with debug=True
6. `test_from_credentials_classmethod` - Test the helper method
7. `test_from_config_with_dict` - Test dict-based config creation
8. `test_from_env` - Test environment variable loading
9. `test_from_env_missing_url_raises` - Test validation

**Estimated time**: 1 hour

---

#### Group 2: TestHTTPOperations (6 tests)

**Pattern to apply**:

```python
# OLD (broken)
def test_get_success(self, base_url, api_key):
    client = JogetClient(base_url, api_key=api_key)
    assert client.timeout == 30

# NEW (working)
def test_get_success(self, mock_config):
    client = JogetClient(mock_config)
    assert client.config.timeout == 30

    # Use mock_client fixture for most tests
def test_get_success(self, mock_client):
    with patch.object(mock_client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        result = mock_client.get("/endpoint")
        assert result.json()["data"] == "test"
```

**Tests to update**:
1. `test_get_success` - Use mock_client fixture
2. `test_get_with_params` - Test parameter passing
3. `test_post_success` - Test POST requests
4. `test_retry_on_500_error` - Test retry logic
5. `test_no_retry_on_404` - Test no retry on client errors
6. `test_exponential_backoff` - Test backoff calculation

**Estimated time**: 1 hour

---

#### Group 3: Form, App, Plugin, Health Operations (20 tests)

**Pattern to apply**:

```python
# Use mock_client fixture for all operation tests
def test_list_forms(self, mock_client):
    with patch.object(mock_client, 'get') as mock_get:
        mock_get.return_value = Mock(
            status_code=200,
            json=Mock(return_value=[
                {"id": "form1", "name": "Form 1"},
                {"id": "form2", "name": "Form 2"}
            ])
        )

        forms = mock_client.list_forms("app1")
        assert len(forms) == 2
        assert forms[0].id == "form1"
```

**Tests by category**:
- **TestFormOperations** (4 tests):
  - `test_get_form`
  - `test_list_forms`
  - `test_update_form`
  - `test_delete_form`

- **TestApplicationOperations** (3 tests):
  - `test_list_applications`
  - `test_export_application`
  - `test_import_application`

- **TestPluginOperations** (2 tests):
  - `test_list_plugins`
  - `test_list_plugins_with_filter`

- **TestHealthAndConnection** (4 tests):
  - `test_test_connection_success`
  - `test_test_connection_failure`
  - `test_get_system_info`
  - `test_get_health_status_healthy`

**Estimated time**: 1.5 hours

---

#### Group 4: Advanced Operations (7 tests)

**Tests**:
- **TestContextManager** (1 test):
  - `test_context_manager` - Test `with` statement usage

- **TestBatchOperations** (3 tests):
  - `test_batch_post_all_success`
  - `test_batch_post_with_failures`
  - `test_batch_post_stop_on_error`

- **TestMultipartUpload** (2 tests):
  - `test_post_multipart_success`
  - `test_post_multipart_with_retry`

- **TestErrorHandling** (6 tests):
  - `test_get_json_decode_error`
  - `test_post_json_decode_error`
  - `test_get_without_retry`
  - `test_post_without_retry`
  - `test_get_with_stream`
  - `test_debug_logging`

- **TestFormOperationsExtended** (1 test):
  - `test_create_form_with_payload`

**Estimated time**: 1 hour

---

### Phase 3: Standardize Error Handling (2 hours)

**Goal**: Make all operations raise exceptions instead of returning booleans or result objects

#### Decision Matrix

| Operation Type | Current Return | Target Return | Exception on Error |
|---------------|----------------|---------------|-------------------|
| `get_form()` | `Dict` or `None` | `Dict` | `NotFoundError` |
| `list_forms()` | `List[FormInfo]` | `List[FormInfo]` | `ServerError` |
| `create_form()` | `FormResult` | `FormInfo` | `ValidationError` |
| `update_form()` | `FormResult` | `FormInfo` | `NotFoundError` |
| `delete_form()` | `bool` | `None` (success) | `NotFoundError` |

#### Changes Needed

**File**: `src/joget_deployment_toolkit/client/forms.py`

```python
# BEFORE
def delete_form(self, app_id: str, form_id: str, app_version: str = "1") -> bool:
    """Delete a form."""
    try:
        response = self.delete(f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}")
        return response.status_code == 200
    except Exception:
        return False

# AFTER
def delete_form(self, app_id: str, form_id: str, app_version: str = "1") -> None:
    """
    Delete a form.

    Args:
        app_id: Application ID
        form_id: Form ID
        app_version: Application version (default: "1")

    Raises:
        NotFoundError: If form doesn't exist
        ServerError: If deletion fails
    """
    try:
        response = self.delete(f"/web/json/console/app/{app_id}/{app_version}/form/{form_id}")
        if response.status_code == 404:
            raise NotFoundError(f"Form not found: {form_id}")
        elif response.status_code >= 400:
            raise ServerError(f"Failed to delete form: {response.text}")
        # Success - no return needed (None is implicit)
    except requests.RequestException as e:
        raise ServerError(f"Request failed: {e}")
```

**Apply to**:
1. `forms.py` - `delete_form()`, `create_form()`, `update_form()`
2. `applications.py` - `delete_application()`, all operations
3. `plugins.py` - All operations
4. `health.py` - `test_connection()` (raise `ConnectionError` instead of returning `False`)

**Update tests**:

```python
# BEFORE
def test_delete_form(self, mock_client):
    result = mock_client.delete_form("app", "form1")
    assert result is True

# AFTER
def test_delete_form(self, mock_client):
    # Success case - no exception
    mock_client.delete_form("app", "form1")  # Returns None

    # Failure case - raises exception
    with pytest.raises(NotFoundError):
        mock_client.delete_form("app", "nonexistent")
```

**Estimated time**: 1 hour implementation + 1 hour test updates

---

### Phase 4: Integration Verification (1 hour)

**Goal**: Verify everything works together

#### Create Integration Test Script

**File**: `tests/integration/test_full_workflow.py`

```python
"""
Integration test simulating real usage patterns.
"""
import pytest
from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.config import ClientConfig, AuthConfig, AuthType
from joget_deployment_toolkit.exceptions import NotFoundError

@pytest.mark.integration
def test_complete_workflow():
    """Test a complete form management workflow."""
    # 1. Create client
    config = ClientConfig(
        base_url="http://localhost:8080/jw",
        auth=AuthConfig(type=AuthType.API_KEY, api_key="test-key"),
        timeout=60,
        debug=True
    )
    client = JogetClient(config)

    # 2. Test connection
    assert client.test_connection()

    # 3. List applications
    apps = client.list_applications()
    assert len(apps) > 0

    # 4. List forms in first app
    if apps:
        forms = client.list_forms(apps[0].id)
        # Should return list (empty or populated)
        assert isinstance(forms, list)

@pytest.mark.integration
def test_error_handling():
    """Test that errors are properly raised."""
    config = ClientConfig(
        base_url="http://localhost:8080/jw",
        auth=AuthConfig(type=AuthType.API_KEY, api_key="test-key")
    )
    client = JogetClient(config)

    # Test NotFoundError
    with pytest.raises(NotFoundError):
        client.get_form("nonexistent_app", "nonexistent_form")

    # Test ValidationError for bad data
    # ... add more error scenarios

@pytest.mark.integration
def test_alternative_constructors():
    """Test all client construction methods."""
    # Method 1: Direct config
    config = ClientConfig(
        base_url="http://localhost:8080/jw",
        auth=AuthConfig(type=AuthType.API_KEY, api_key="key")
    )
    client1 = JogetClient(config)
    assert client1.base_url == "http://localhost:8080/jw"

    # Method 2: from_credentials
    client2 = JogetClient.from_credentials(
        "http://localhost:8080/jw",
        "admin",
        "admin"
    )
    assert client2.base_url == "http://localhost:8080/jw"

    # Method 3: from_config (dict)
    client3 = JogetClient.from_config({
        "url": "http://localhost:8080/jw",
        "username": "admin",
        "password": "admin"
    })
    assert client3.base_url == "http://localhost:8080/jw"

    # Method 4: from_env (if env vars set)
    # ... test env loading
```

**Run Integration Tests**:

```bash
# Run with local Joget instance
pytest tests/integration/ -v --tb=short

# Run without Joget (mock tests only)
pytest tests/ -v -m "not integration"
```

---

## Day 3: Polish & Release (2-3 hours)

### Phase 1: Documentation Updates (1 hour)

**Update files**:

1. **README.md** - Update all examples for v3.0:

```markdown
## Installation

```bash
pip install joget-toolkit
```

## Quick Start (v3.0)

```python
from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.config import ClientConfig, AuthConfig, AuthType

# Create configuration
config = ClientConfig(
    base_url="http://localhost:8080/jw",
    auth=AuthConfig(type=AuthType.API_KEY, api_key="your-api-key"),
    timeout=60
)

# Create client
client = JogetClient(config)

# Use client
forms = client.list_forms("myApp")
for form in forms:
    print(f"Form: {form.name} (ID: {form.id})")
```

## Alternative Construction Methods

```python
# Method 1: From credentials
client = JogetClient.from_credentials(
    "http://localhost:8080/jw",
    "admin",
    "admin"
)

# Method 2: From dictionary
client = JogetClient.from_config({
    "url": "http://localhost:8080/jw",
    "username": "admin",
    "password": "admin",
    "timeout": 60
})

# Method 3: From environment variables
# Set: JOGET_BASE_URL, JOGET_API_KEY or JOGET_USERNAME/JOGET_PASSWORD
client = JogetClient.from_env()
```
```

2. **MIGRATION_GUIDE.md** - Create guide for v2.x → v3.0:

```markdown
# Migration Guide: v2.x → v3.0

## Breaking Changes

### 1. Client Initialization

**v2.x (old)**:
```python
client = JogetClient("http://localhost:8080/jw", api_key="key")
```

**v3.0 (new)**:
```python
from joget_deployment_toolkit.config import ClientConfig, AuthConfig, AuthType

config = ClientConfig(
    base_url="http://localhost:8080/jw",
    auth=AuthConfig(type=AuthType.API_KEY, api_key="key")
)
client = JogetClient(config)
```

**Migration path**: Use helper methods for easier transition:
```python
# Easiest: from_credentials
client = JogetClient.from_credentials("http://localhost:8080/jw", "user", "pass")

# Or: from_config with dict
client = JogetClient.from_config({
    "url": "http://localhost:8080/jw",
    "api_key": "key"
})
```

### 2. Accessing Configuration

**v2.x (old)**:
```python
timeout = client.timeout
retry_count = client.retry_count
```

**v3.0 (new)**:
```python
timeout = client.config.timeout
retry_count = client.config.retry.count
```

### 3. Error Handling

**v2.x (old)**:
```python
if client.delete_form("app", "form"):
    print("Deleted")
else:
    print("Failed")
```

**v3.0 (new)**:
```python
try:
    client.delete_form("app", "form")
    print("Deleted")
except NotFoundError:
    print("Form not found")
except ServerError:
    print("Deletion failed")
```

## Why These Changes?

1. **Cleaner architecture** - Separation of configuration from client logic
2. **Better type safety** - Pydantic v2 validation
3. **More Pythonic** - Exceptions instead of boolean returns
4. **Easier testing** - Configuration objects are easier to mock
5. **Future-proof** - Easier to add new features without breaking changes
```

3. **CHANGELOG.md** - Document v3.0.0 release:

```markdown
# Changelog

## [3.0.0] - 2025-11-XX

### Breaking Changes
- **Client initialization**: Now requires `ClientConfig` object instead of string URL
- **Configuration access**: Changed from `client.timeout` to `client.config.timeout`
- **Error handling**: All operations now raise exceptions instead of returning booleans
- **Removed backward compatibility**: No support for v2.x patterns

### Added
- `JogetClient.from_credentials()` - Convenient constructor for username/password
- `JogetClient.from_config()` - Constructor accepting dict configuration
- `JogetClient.from_env()` - Load configuration from environment variables
- Comprehensive exception hierarchy for better error handling
- Repository pattern for database operations
- Connection pooling for improved performance

### Changed
- Refactored monolithic client (1,290 lines) into 5 focused mixins
- Improved configuration system with Pydantic v2
- Standardized all operations to raise exceptions on errors
- Enhanced type hints throughout codebase

### Migration Guide
See MIGRATION_GUIDE.md for detailed upgrade instructions.

## [2.0.0] - Previous Release
...
```

---

### Phase 2: Final Validation (1 hour)

**Checklist**:

1. **Run full test suite**:
```bash
pytest tests/ -v --cov=joget_deployment_toolkit --cov-report=html
```
Expected: All tests passing, >80% coverage

2. **Run linters**:
```bash
ruff check src/
black --check src/
mypy src/
```

3. **Build package**:
```bash
python -m build
```

4. **Test package locally**:
```bash
pip install -e .
python -c "from joget_deployment_toolkit import JogetClient; print('Import OK')"
```

5. **Test all constructor methods**:
```python
# test_constructors.py
from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.config import ClientConfig, AuthConfig, AuthType

# Test 1: Direct config
config = ClientConfig(
    base_url="http://localhost:8080/jw",
    auth=AuthConfig(type=AuthType.API_KEY, api_key="test")
)
client = JogetClient(config)
print("✓ Direct config works")

# Test 2: from_credentials
client = JogetClient.from_credentials(
    "http://localhost:8080/jw", "admin", "admin"
)
print("✓ from_credentials works")

# Test 3: from_config
client = JogetClient.from_config({
    "url": "http://localhost:8080/jw",
    "api_key": "test"
})
print("✓ from_config works")

print("\n✅ All constructors working!")
```

---

### Phase 3: Release Preparation (30 min)

1. **Update version** in `pyproject.toml`:
```toml
[project]
name = "joget-toolkit"
version = "3.0.0"
```

2. **Create git tag**:
```bash
git add .
git commit -m "Release v3.0.0 - Major refactoring with breaking changes"
git tag -a v3.0.0 -m "Version 3.0.0

Breaking changes:
- New configuration-based initialization
- Exception-based error handling
- Modular architecture

See CHANGELOG.md for full details."
git push origin main --tags
```

3. **Build and publish** (if ready):
```bash
python -m build
twine check dist/*
# twine upload dist/*  # When ready for PyPI
```

---

## Implementation Strategy

### Time Boxing

| Day | Phase | Time | Tasks |
|-----|-------|------|-------|
| **Day 2 Morning** | Test Helpers | 30 min | Create conftest.py helpers |
| **Day 2 Morning** | Init Tests | 1.5 hrs | Fix TestClientInitialization (9 tests) |
| **Day 2 Afternoon** | HTTP Tests | 1 hr | Fix TestHTTPOperations (6 tests) |
| **Day 2 Afternoon** | Operation Tests | 1.5 hrs | Fix Form/App/Plugin/Health (13 tests) |
| **Day 2 Evening** | Advanced Tests | 1 hr | Fix remaining tests (13 tests) |
| **Day 3 Morning** | Error Handling | 2 hrs | Standardize exceptions |
| **Day 3 Morning** | Integration | 1 hr | Create & run integration tests |
| **Day 3 Afternoon** | Documentation | 1 hr | Update all docs |
| **Day 3 Afternoon** | Release | 30 min | Version, tag, build |

**Total**: ~10 hours

---

## Quality Gates

### Before Moving to Next Phase

- [ ] **Phase 1 Complete**: All test helpers created and documented
- [ ] **Phase 2 Complete**: All 41 tests passing
- [ ] **Phase 3 Complete**: All operations raise exceptions consistently
- [ ] **Phase 4 Complete**: Integration tests pass
- [ ] **Documentation Complete**: README, CHANGELOG, MIGRATION_GUIDE updated
- [ ] **Release Ready**: Package builds successfully, all quality checks pass

---

## Risk Management

### Risk 1: Test Updates Take Longer Than Expected
**Likelihood**: Medium
**Impact**: High (delays release)
**Mitigation**:
- Use fixtures to reduce boilerplate
- Fix in batches (don't try to fix all at once)
- Focus on critical path tests first

### Risk 2: Error Handling Changes Break Existing Behavior
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Integration tests catch behavioral changes
- Document all changes in MIGRATION_GUIDE
- Clear v3.0 major version signals breaking changes

### Risk 3: Documentation Becomes Outdated
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Update docs in parallel with code changes
- Include code examples in docs that are tested
- Review all documentation before release

---

## Success Criteria

### Must Have (Release Blockers)
- ✅ All 169 tests passing (currently 128/169)
- ✅ Error handling standardized (all exceptions)
- ✅ All client constructors working (`from_credentials`, `from_config`, `from_env`)
- ✅ Documentation updated for v3.0
- ✅ Package builds without errors

### Should Have
- ✅ Integration tests pass
- ✅ Code coverage >80%
- ✅ All linters pass (ruff, black, mypy)
- ✅ Migration guide complete

### Nice to Have (Can Defer to v3.0.1)
- ⏳ Performance benchmarks
- ⏳ Additional integration examples
- ⏳ Video tutorial for migration

---

## Post-Release Plan

### v3.0.1 (Patch - 1 week after v3.0.0)
- Bug fixes from user feedback
- Performance optimizations if needed
- Documentation improvements

### v3.1.0 (Minor - 1 month after v3.0.0)
- Basic caching layer
- Additional convenience methods
- Enhanced logging

### v3.2.0 (Minor - 2 months after v3.0.0)
- Async support (AsyncJogetClient)
- Query builder for complex searches

---

## Immediate Next Steps

1. **Create test helpers** (`tests/conftest.py`) - 30 min
2. **Fix first batch of tests** (TestClientInitialization) - 1 hour
3. **Review progress** - Are patterns working? Any adjustments needed?
4. **Continue with remaining test groups** - Follow time boxes

---

## Key Takeaways

1. **Clean break was the right choice** - Code is much simpler
2. **Pydantic v2 is working well** - Configuration validation is solid
3. **Test patterns are clear** - Just need to apply them consistently
4. **Exception-based errors are better** - More Pythonic, easier to handle
5. **Time estimates are realistic** - 10 hours total is achievable

---

**Status**: Ready to continue
**Confidence**: High (95%)
**Next Action**: Create test helpers in conftest.py

---

## Quick Reference Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_client.py::TestClientInitialization -v

# Run with coverage
pytest --cov=joget_deployment_toolkit --cov-report=html

# Run only passing tests
pytest tests/test_auth.py tests/test_exceptions.py -v

# Check what's failing
pytest tests/test_client.py -v --tb=no | grep FAILED

# Format code
black src/ tests/

# Lint
ruff check src/

# Type check
mypy src/

# Build package
python -m build
```
