Database Layer
==============

Repository pattern and connection pool for efficient database operations.

Connection Pool
---------------

Thread-safe connection pool with singleton pattern.

.. autoclass:: joget_deployment_toolkit.database.DatabaseConnectionPool
   :members:
   :show-inheritance:

Repositories
------------

Base Repository
~~~~~~~~~~~~~~~

Generic repository base class with common CRUD operations.

.. autoclass:: joget_deployment_toolkit.database.repositories.BaseRepository
   :members:
   :show-inheritance:

Form Repository
~~~~~~~~~~~~~~~

Repository for form-related database operations.

.. autoclass:: joget_deployment_toolkit.database.repositories.FormRepository
   :members:
   :show-inheritance:

Application Repository
~~~~~~~~~~~~~~~~~~~~~~

Repository for application-related database operations.

.. autoclass:: joget_deployment_toolkit.database.repositories.ApplicationRepository
   :members:
   :show-inheritance:
