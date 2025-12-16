Changelog
=========

Version 2.1.0 (Upcoming)
------------------------

**Major Refactoring Release**

New Features
~~~~~~~~~~~~

* **Modular Client Architecture** - Separated concerns into focused operation mixins
* **Repository Pattern** - Efficient database access with connection pooling
* **Alternative Constructors** - ``from_credentials()``, ``from_config()``, ``from_env()``
* **Health Check Operations** - Comprehensive monitoring with ``get_health_status()``
* **Connection Pooling** - 50%+ performance improvement for database operations

Improvements
~~~~~~~~~~~~

* Enhanced type hints throughout the codebase
* Better error messages and exception handling
* Comprehensive API documentation
* Migration guide for upgrading from v2.0.x
* All tests passing (169 tests)

Architecture Changes
~~~~~~~~~~~~~~~~~~~~

* Split monolithic client (1,290 lines) into modular structure
* Introduced ``BaseClient`` with operation mixins
* Created ``FormRepository`` and ``ApplicationRepository``
* Refactored ``FormDiscovery`` to use repository pattern
* Added ``DatabaseConnectionPool`` singleton

Backward Compatibility
~~~~~~~~~~~~~~~~~~~~~~

* 100% backward compatible with v2.0.x
* All existing code works without modification
* Deprecated features will show warnings but still function

Version 2.0.0
-------------

* Initial release with basic client functionality
* Form discovery capabilities
* Application export/import
* Basic error handling

For detailed changes, see the `Git commit history <https://github.com/your-org/joget-toolkit/commits/main>`_.
