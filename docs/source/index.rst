Joget Toolkit Documentation
============================

**Version 2.1.0**

Joget Toolkit is a comprehensive Python library for automating Joget DX platform operations. It provides:

* **Modular API Client** - Clean, composable client architecture with multiple authentication strategies
* **Repository Pattern** - Efficient database access with connection pooling
* **Form Discovery** - Extract and analyze form definitions from Joget databases
* **Type Safety** - Full type hints and Pydantic models for robust development
* **Backward Compatible** - 100% compatible with v2.0.x codebases

Quick Start
-----------

Installation::

    pip install joget-toolkit

Basic Usage::

    from joget_deployment_toolkit import JogetClient

    # Create client with API key authentication
    client = JogetClient.from_credentials(
        base_url="http://localhost:8080/jw",
        username="admin",
        password="admin"
    )

    # List applications
    apps = client.list_applications()

    # Export an application
    result = client.export_application("myApp", "output/myApp.zip")

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   quickstart
   migration_guide
   examples

.. toctree::
   :maxdepth: 3
   :caption: API Reference

   api/client
   api/auth
   api/models
   api/database
   api/discovery
   api/exceptions

.. toctree::
   :maxdepth: 1
   :caption: Additional Info

   changelog
   contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
