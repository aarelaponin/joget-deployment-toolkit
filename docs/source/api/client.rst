Client
======

The Joget Toolkit client provides a comprehensive, modular interface for interacting with the Joget DX REST API.

JogetClient
-----------

The main client class that combines all operation mixins.

.. autoclass:: joget_deployment_toolkit.client.JogetClient
   :members:
   :special-members: __init__
   :show-inheritance:

Alternative Constructors
~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: joget_deployment_toolkit.client.JogetClient.from_credentials
.. automethod:: joget_deployment_toolkit.client.JogetClient.from_config
.. automethod:: joget_deployment_toolkit.client.JogetClient.from_env

Base Client
-----------

Core HTTP client functionality.

.. autoclass:: joget_deployment_toolkit.client.base.BaseClient
   :members:
   :show-inheritance:

Form Operations
---------------

Form-related API operations.

.. autoclass:: joget_deployment_toolkit.client.forms.FormOperations
   :members:
   :show-inheritance:

Application Operations
----------------------

Application management operations.

.. autoclass:: joget_deployment_toolkit.client.applications.ApplicationOperations
   :members:
   :show-inheritance:

Plugin Operations
-----------------

Plugin listing and inspection.

.. autoclass:: joget_deployment_toolkit.client.plugins.PluginOperations
   :members:
   :show-inheritance:

Health Operations
-----------------

Health check and monitoring operations.

.. autoclass:: joget_deployment_toolkit.client.health.HealthOperations
   :members:
   :show-inheritance:

Client Configuration
--------------------

Configuration model for client settings.

.. autoclass:: joget_deployment_toolkit.models.JogetConfig
   :members:
   :show-inheritance:
