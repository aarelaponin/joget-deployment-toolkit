# Changelog

All notable changes to joget-toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-11-17

### 🎉 Major Release: FRS Platform Integration & Architecture Improvements

This release introduces **FRS Development Platform integration** for centralized configuration management, eliminating hardcoded ports and enabling true multi-instance orchestration.

### ⚠️ Breaking Changes

**Note:** While this is a major version bump, breaking changes are minimal. The main change is improved configuration patterns. Legacy initialization still works but is discouraged.

#### Configuration Changes
- **Recommended:** Use `from_frs()` for FRS platform integration
- **Alternative:** Use `JogetClient.from_credentials()` or `JogetClient.from_env()`
- **Deprecated:** Direct keyword arguments to `JogetClient()` (still works, will warn in v3.1)

#### Error Handling
- All operations now raise specific exceptions (already in v2.1.0, now enforced)
- Mixed bool/exception returns removed

### 🚀 Added

#### FRS Platform Integration (NEW!)
- **`from_frs(instance_name)`**: Create client from FRS Development Platform configuration
- **`FRSConfigLoader`**: Load and convert FRS platform configs
- **Multi-instance support**: Manage 6+ Joget instances from single config file
- **Centralized configuration**: All instance settings in `~/.frs-dev/config.yaml`
- **No hardcoded ports**: Ports, URLs, credentials all from central config
- **Optional dependency**: `pip install joget-toolkit[frs]` includes PyYAML

Example:
```python
from joget_deployment_toolkit.integrations import from_frs

# One line - no hardcoded ports!
client = from_frs("jdx1")  # Gets correct URL, ports from FRS config
```

#### Documentation
- **FRS_INTEGRATION.md**: Complete 350+ line integration guide
- API reference for all FRS integration functions
- 10+ working code examples
- Troubleshooting section
- Migration patterns from direct configuration

### ✅ Tests
- **17 new tests** for FRS integration (all passing)
- **89.47% coverage** of integration code
- Tests for multi-instance patterns
- Error handling verification
- Optional dependency behavior

### 📦 Package Updates
- Version bumped to **3.0.0**
- Added `[frs]` optional dependency group
- Updated exports in `__init__.py`

### 🎯 Benefits

#### Before v3.0.0:
```python
# Had to remember/hardcode ports for every instance
client1 = JogetClient("http://localhost:8080/jw", username="admin", password="pass")
client2 = JogetClient("http://localhost:9999/jw", username="admin", password="pass")
# Which instance is which? What are the DB ports?
```

#### After v3.0.0:
```python
# Crystal clear, all config centralized
client1 = from_frs("jdx1")  # MOA Back Office
client2 = from_frs("jdx2")  # Farmers Portal
# Ports, credentials automatic from FRS config
```

### 🔧 Improved

#### Multi-Instance Testing
```python
# Test all configured instances with 3 lines
from joget_deployment_toolkit.integrations import from_frs, FRSConfigLoader

for instance in FRSConfigLoader.list_instances():
    client = from_frs(instance)
    assert client.test_connection()
```

#### Team Collaboration
- Share configuration file (without passwords)
- Each developer sets own password environment variables
- Consistent instance names across team

### 📚 Architecture

The FRS integration follows a clean separation:

```
FRS Development Platform (Command Center)
    ↓
    ~/.frs-dev/config.yaml (Single Source of Truth)
    ↓
FRSConfigLoader.to_client_config()
    ↓
JogetClient (joget-toolkit)
    ↓
Joget Instances (jdx1-6+)
```

### 🔐 Security
- Passwords stored in environment variables (never in config files)
- Password environment variable names configurable
- Follows security best practices

### 🎓 Use Cases

1. **Multi-instance deployments**: Deploy to jdx4, jdx5, jdx6 in one script
2. **Instance health monitoring**: Check all instances with one loop
3. **Parametrized testing**: Test all instances with pytest fixtures
4. **Team collaboration**: Shared config, individual credentials

### 📝 See Also
- [FRS_INTEGRATION.md](FRS_INTEGRATION.md) - Complete integration guide
- [V3_IMPLEMENTATION_SUMMARY.md](V3_IMPLEMENTATION_SUMMARY.md) - Technical details
- [README.md](README.md) - Main documentation

### 🔗 Integration Points
- Compatible with existing joget-toolkit features
- Works with FRS Development Platform
- Optional (toolkit works fine without FRS platform)
- No circular dependencies

---

## [2.1.0] - 2025-11-16

### Added

- **Modular Client Architecture**: Split monolithic client (1,290 lines) into focused operation mixins
  - BaseClient: Core HTTP and authentication functionality
  - FormOperations: Form-related API operations
  - ApplicationOperations: Application management operations
  - PluginOperations: Plugin listing and inspection
  - HealthOperations: Health checks and monitoring
  - JogetClient: Facade combining all mixins

- **Repository Pattern**: Clean data access abstraction with connection pooling
  - BaseRepository: Generic CRUD operations with TypeVar support
  - FormRepository: Form-specific database operations
  - ApplicationRepository: Application-specific database operations
  - DatabaseConnectionPool: Thread-safe singleton connection pool

- **Alternative Constructors**: Convenient client creation methods
  - JogetClient.from_credentials(): Create from username/password
  - JogetClient.from_config(): Create from configuration object
  - JogetClient.from_env(): Create from environment variables

- **Health Monitoring**: Comprehensive health check operations
  - test_connection(): Basic connectivity test
  - get_system_info(): Retrieve Joget version and build information
  - get_health_status(): Complete health assessment (HEALTHY/DEGRADED/UNHEALTHY)

- **Comprehensive Documentation**:
  - Sphinx-based API documentation with RTD theme
  - Quick start guide with common operations
  - Migration guide for v2.0.x users
  - Examples of advanced usage patterns

### Performance

- **50%+ Database Operation Speed Up**: Through connection pooling
  - Reduced connection creation/teardown overhead
  - Connection reuse across multiple queries

### Fixed

- Fixed verify_ssl and timeout attribute access in HealthOperations
- Fixed missing auth strategy imports in backward compatibility wrapper
- Fixed repository test failures for API endpoint lookups

### Tests

- Added 27 new repository tests (all passing)
- Total test count: 169 tests passing
- Test coverage: ~85%+

### Backward Compatibility

- **100% backward compatible with v2.0.x**
- All existing code continues to work without modifications
- Zero breaking changes

## [2.0.0] - Prior Release

- Initial release with basic functionality
- Form discovery and extraction
- Application export/import
- Basic error handling

[3.0.0]: https://github.com/your-org/joget-toolkit/compare/v2.1.0...v3.0.0
[2.1.0]: https://github.com/your-org/joget-toolkit/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/your-org/joget-toolkit/releases/tag/v2.0.0
