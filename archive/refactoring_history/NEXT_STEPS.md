# Joget-Toolkit Refactoring - Immediate Next Steps

**Updated**: November 16, 2025
**Current Phase**: Ready to Start Day 2
**Estimated Time**: 30 minutes to first milestone

---

## 🎯 Start Here

### Step 1: Create Test Helpers (30 minutes)

Open your editor and create/update `tests/conftest.py`:

```python
"""
Shared test fixtures for joget-toolkit tests.

Provides common fixtures to reduce test boilerplate and ensure consistency.
"""
import pytest
from unittest.mock import Mock, patch
from joget_deployment_toolkit.config import ClientConfig, AuthConfig, AuthType
from joget_deployment_toolkit.client import JogetClient
from joget_deployment_toolkit.auth import APIKeyAuth, SessionAuth


@pytest.fixture
def base_url():
    """Default base URL for testing."""
    return "http://localhost:8080/jw"


@pytest.fixture
def api_key():
    """Default API key for testing."""
    return "test-api-key"


@pytest.fixture
def credentials():
    """Default username/password credentials."""
    return {"username": "admin", "password": "admin"}


@pytest.fixture
def basic_config(base_url, api_key):
    """
    Create a basic ClientConfig with API key auth.

    Most tests can use this directly.
    """
    return ClientConfig(
        base_url=base_url,
        auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
        timeout=30,
        debug=False
    )


@pytest.fixture
def session_config(base_url, credentials):
    """Create a ClientConfig with session auth."""
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
def custom_config(base_url, api_key):
    """
    Create a ClientConfig factory for custom configurations.

    Usage:
        config = custom_config(timeout=60, debug=True)
    """
    def _create_config(**overrides):
        base = {
            "base_url": base_url,
            "auth": AuthConfig(type=AuthType.API_KEY, api_key=api_key),
            "timeout": 30,
            "debug": False
        }
        base.update(overrides)
        return ClientConfig(**base)

    return _create_config


@pytest.fixture
def mock_auth_strategy():
    """Create a mocked authentication strategy."""
    mock_auth = Mock(spec=APIKeyAuth)
    mock_auth.authenticate = Mock(return_value=True)
    mock_auth.get_headers = Mock(return_value={"Authorization": "Bearer test"})
    mock_auth.is_authenticated = Mock(return_value=True)
    return mock_auth


@pytest.fixture
def mock_client(basic_config, mock_auth_strategy):
    """
    Create a fully mocked JogetClient.

    This is the most commonly used fixture. It provides a client
    with mocked HTTP operations ready for testing.

    Usage:
        def test_something(mock_client):
            with patch.object(mock_client, 'get') as mock_get:
                mock_get.return_value = Mock(status_code=200, json=...)
                result = mock_client.list_forms("app")
    """
    with patch('joget_deployment_toolkit.auth.select_auth_strategy') as mock_select:
        mock_select.return_value = mock_auth_strategy

        client = JogetClient(basic_config, auth_strategy=mock_auth_strategy)

        # Mock the session to avoid actual HTTP calls
        client.session = Mock()

        return client


@pytest.fixture
def mock_response():
    """
    Create a factory for mock HTTP responses.

    Usage:
        response = mock_response(status=200, json_data={"key": "value"})
    """
    def _create_response(status=200, json_data=None, text="", headers=None):
        mock_resp = Mock()
        mock_resp.status_code = status
        mock_resp.text = text
        mock_resp.headers = headers or {}

        if json_data is not None:
            mock_resp.json = Mock(return_value=json_data)
        else:
            mock_resp.json = Mock(side_effect=ValueError("No JSON"))

        return mock_resp

    return _create_response
```

**Test it works**:
```bash
cd /Users/aarelaponin/PycharmProjects/dev/joget-toolkit
pytest tests/test_auth.py -v  # Should still pass
```

---

## Step 2: Fix First Test (10 minutes)

Update `tests/test_client.py`, line 57-72:

**Before**:
```python
def test_init_with_username_password(self, base_url, credentials):
    """Test initialization with username/password."""
    with patch('joget_deployment_toolkit.client.SessionAuth') as mock_auth:
        mock_auth_instance = Mock()
        mock_auth_instance.authenticate = Mock(return_value=True)
        mock_auth.return_value = mock_auth_instance

        with patch('joget_deployment_toolkit.client.select_auth_strategy', return_value=mock_auth_instance):
            client = JogetClient(
                base_url,
                username=credentials["username"],
                password=credentials["password"]
            )

            assert client.base_url == base_url
```

**After**:
```python
def test_init_with_username_password(self, session_config, mock_auth_strategy):
    """Test initialization with username/password."""
    with patch('joget_deployment_toolkit.auth.select_auth_strategy') as mock_select:
        mock_select.return_value = mock_auth_strategy

        client = JogetClient(session_config, auth_strategy=mock_auth_strategy)

        assert client.base_url == session_config.base_url
        assert client.config.auth.username == "admin"
        assert isinstance(client.auth_strategy, Mock)
```

**Test it**:
```bash
pytest tests/test_client.py::TestClientInitialization::test_init_with_username_password -v
```

Should see: `PASSED` ✅

---

## Step 3: Fix Next 2 Tests (20 minutes)

Apply the same pattern to:

### Test 3: `test_init_custom_timeout`

**Replace** lines 73-79 with:
```python
def test_init_custom_timeout(self, base_url, api_key, mock_auth_strategy):
    """Test initialization with custom timeout."""
    config = ClientConfig(
        base_url=base_url,
        auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
        timeout=60  # Custom timeout
    )

    with patch('joget_deployment_toolkit.auth.select_auth_strategy') as mock_select:
        mock_select.return_value = mock_auth_strategy
        client = JogetClient(config, auth_strategy=mock_auth_strategy)

        assert client.config.timeout == 60
```

### Test 4: `test_init_custom_retry_settings`

**Replace** lines 81-95 with:
```python
def test_init_custom_retry_settings(self, base_url, api_key, mock_auth_strategy):
    """Test initialization with custom retry settings."""
    from joget_deployment_toolkit.config import RetryConfig

    config = ClientConfig(
        base_url=base_url,
        auth=AuthConfig(type=AuthType.API_KEY, api_key=api_key),
        retry=RetryConfig(
            count=5,
            delay=3.0,
            backoff=3.0
        )
    )

    with patch('joget_deployment_toolkit.auth.select_auth_strategy') as mock_select:
        mock_select.return_value = mock_auth_strategy
        client = JogetClient(config, auth_strategy=mock_auth_strategy)

        assert client.config.retry.count == 5
        assert client.config.retry.delay == 3.0
        assert client.config.retry.backoff == 3.0
```

**Test them**:
```bash
pytest tests/test_client.py::TestClientInitialization -v
```

Should see: `4 passed` (the one we fixed earlier + these 3)

---

## 🎉 First Milestone: 4 Tests Passing

After completing Steps 1-3, you'll have:
- ✅ Test helpers created
- ✅ 4 client initialization tests passing
- ✅ Clear pattern established for remaining tests

**Commit your work**:
```bash
git add tests/conftest.py tests/test_client.py
git commit -m "refactor(tests): Add test helpers and fix 3 client init tests

- Created comprehensive test fixtures in conftest.py
- Fixed test_init_with_username_password
- Fixed test_init_custom_timeout
- Fixed test_init_custom_retry_settings
- Tests passing: 131/169 (78%)"
```

---

## Next Actions (After First Milestone)

### Continue with Remaining Init Tests (40 minutes)

Fix these tests using the same pattern:

1. **test_init_with_debug** (5 min)
   - Add `debug=True` to config
   - Assert `client.config.debug is True`

2. **test_from_credentials_classmethod** (10 min)
   - Test the `JogetClient.from_credentials()` method
   - Verify it creates config correctly

3. **test_from_config_with_dict** (10 min)
   - Test the `JogetClient.from_config()` method
   - Verify dict → config conversion

4. **test_from_env** (10 min)
   - Test environment variable loading
   - Use `@patch.dict(os.environ, {...})`

5. **test_from_env_missing_url_raises** (5 min)
   - Already passing, just verify

**Expected result**: All 9 TestClientInitialization tests passing

---

## Time Check & Decision Point

After the first milestone (1 hour total):

### If ahead of schedule:
→ Continue with TestHTTPOperations (6 tests, 1 hour)

### If on schedule:
→ Take a break, then continue with TestHTTPOperations

### If behind schedule:
→ Review what's slowing you down:
- Are fixtures working as expected?
- Is the pattern clear?
- Do you need to adjust approach?

---

## Success Indicators

You're on track if:
- ✅ conftest.py created in <30 minutes
- ✅ Each test fix takes <10 minutes
- ✅ Pattern feels repetitive (good sign!)
- ✅ No new errors appearing

You may need help if:
- ❌ Fixtures aren't being recognized
- ❌ Mocking isn't working as expected
- ❌ Test fixes taking >15 minutes each
- ❌ New errors appearing

---

## Quick Reference

### Import Additions Needed
```python
# Add to test_client.py imports
from joget_deployment_toolkit.config import ClientConfig, AuthConfig, AuthType, RetryConfig
```

### Common Test Pattern
```python
def test_something(self, mock_client):
    """Test description."""
    # Use the mock_client fixture
    with patch.object(mock_client, 'get') as mock_get:
        mock_get.return_value = Mock(status_code=200, json=lambda: {...})

        result = mock_client.some_operation()

        assert result == expected
```

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific class
pytest tests/test_client.py::TestClientInitialization -v

# Specific test
pytest tests/test_client.py::TestClientInitialization::test_init_with_api_key -v

# Show only failures
pytest tests/test_client.py --tb=short

# Count passing tests
pytest tests/ --tb=no | grep passed
```

---

## Troubleshooting

### Issue: "fixture not found"
**Solution**: Make sure conftest.py is in `tests/` directory

### Issue: "Mock object has no attribute"
**Solution**: Check that you're patching the right module path

### Issue: "AttributeError: config"
**Solution**: Use `client.config.timeout` not `client.timeout`

### Issue: Tests still failing after fix
**Solution**: Run `pytest --cache-clear` to clear cached results

---

## Documentation

As you work, keep notes in `REFACTORING_PROGRESS_DAY2.md`:

```markdown
# Refactoring Progress - Day 2

## Session 1 (Morning)

### Completed
- Created test helpers (30 min)
- Fixed test_init_with_username_password (10 min)
- Fixed test_init_custom_timeout (5 min)
- Fixed test_init_custom_retry_settings (10 min)

### Challenges
- [Note any issues encountered]

### Tests Status
- Passing: 131/169 (78%)
- Fixed this session: 3 tests
```

---

## End of Session Checklist

Before stopping:
- [ ] Run full test suite to verify no regressions
- [ ] Commit your changes with clear message
- [ ] Update PROGRESS_TRACKER.md with new numbers
- [ ] Note any blockers or questions for next session

---

**Ready to Start?**

1. Open terminal: `cd /Users/aarelaponin/PycharmProjects/dev/joget-toolkit`
2. Open editor: Open `tests/conftest.py` (create it)
3. Start timer: 30 minutes for Step 1
4. Begin coding!

**Good luck!** 🚀
