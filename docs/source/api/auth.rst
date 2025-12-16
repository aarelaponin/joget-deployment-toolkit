Authentication
==============

Authentication strategies for Joget DX API access.

Auth Strategy Base
------------------

Abstract base class for authentication strategies.

.. autoclass:: joget_deployment_toolkit.auth.AuthStrategy
   :members:
   :show-inheritance:

API Key Authentication
----------------------

Authenticate using Joget API keys.

.. autoclass:: joget_deployment_toolkit.auth.APIKeyAuth
   :members:
   :show-inheritance:

Session Authentication
----------------------

Authenticate using username/password with session cookies.

.. autoclass:: joget_deployment_toolkit.auth.SessionAuth
   :members:
   :show-inheritance:

Basic Authentication
--------------------

HTTP Basic Authentication (username/password in headers).

.. autoclass:: joget_deployment_toolkit.auth.BasicAuth
   :members:
   :show-inheritance:

No Authentication
-----------------

For public endpoints that don't require authentication.

.. autoclass:: joget_deployment_toolkit.auth.NoAuth
   :members:
   :show-inheritance:

Auth Selection
--------------

.. autofunction:: joget_deployment_toolkit.auth.select_auth_strategy
