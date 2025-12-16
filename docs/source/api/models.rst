Data Models
===========

Type-safe data models for configuration and API responses.

Configuration Models
--------------------

Joget Client Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.JogetConfig
   :members:
   :show-inheritance:

Database Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.DatabaseConfig
   :members:
   :show-inheritance:

Deployment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.DeploymentConfig
   :members:
   :show-inheritance:

API Response Models
-------------------

Form Information
~~~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.FormInfo
   :members:
   :show-inheritance:

Application Information
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.ApplicationInfo
   :members:
   :show-inheritance:

.. autoclass:: joget_deployment_toolkit.models.ApplicationDetails
   :members:
   :show-inheritance:

Plugin Information
~~~~~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.PluginInfo
   :members:
   :show-inheritance:

.. autoclass:: joget_deployment_toolkit.models.PluginDetails
   :members:
   :show-inheritance:

System Information
~~~~~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.SystemInfo
   :members:
   :show-inheritance:

Health Check Models
-------------------

Health Status
~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.HealthStatus
   :members:
   :show-inheritance:

Health Check Result
~~~~~~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.HealthCheckResult
   :members:
   :show-inheritance:

Overall Health
~~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.Health
   :members:
   :show-inheritance:

Operation Results
-----------------

Form Result
~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.FormResult
   :members:
   :show-inheritance:

Batch Result
~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.BatchResult
   :members:
   :show-inheritance:

Export Result
~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.ExportResult
   :members:
   :show-inheritance:

Import Result
~~~~~~~~~~~~~

.. autoclass:: joget_deployment_toolkit.models.ImportResult
   :members:
   :show-inheritance:

Utility Functions
-----------------

.. autofunction:: joget_deployment_toolkit.models.parse_datetime
.. autofunction:: joget_deployment_toolkit.models.form_info_from_dict
.. autofunction:: joget_deployment_toolkit.models.application_info_from_dict
.. autofunction:: joget_deployment_toolkit.models.plugin_info_from_dict
