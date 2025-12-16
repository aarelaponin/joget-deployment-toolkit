Quick Start Guide
=================

This guide will help you get started with Joget Toolkit quickly.

Installation
------------

Install from PyPI::

    pip install joget-toolkit

Or install from source::

    git clone https://github.com/your-org/joget-toolkit.git
    cd joget-toolkit
    pip install -e .

Basic Configuration
-------------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

The easiest way to configure Joget Toolkit is through environment variables::

    export JOGET_BASE_URL="http://localhost:8080/jw"
    export JOGET_USERNAME="admin"
    export JOGET_PASSWORD="admin"

Then create a client::

    from joget_deployment_toolkit import JogetClient

    client = JogetClient.from_env()

Programmatic Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also configure the client programmatically::

    from joget_deployment_toolkit import JogetClient

    client = JogetClient.from_credentials(
        base_url="http://localhost:8080/jw",
        username="admin",
        password="admin"
    )

Common Operations
-----------------

List Applications
~~~~~~~~~~~~~~~~~

::

    apps = client.list_applications()
    for app in apps:
        print(f"{app.id} v{app.version}: {app.name}")

Export an Application
~~~~~~~~~~~~~~~~~~~~~

::

    from pathlib import Path

    result = client.export_application(
        app_id="myApp",
        output_path=Path("exports/myApp.zip"),
        app_version="1"
    )

    if result.success:
        print(f"Exported to {result.output_path} ({result.file_size_bytes} bytes)")

Import an Application
~~~~~~~~~~~~~~~~~~~~~

::

    result = client.import_application(
        zip_path=Path("exports/myApp.zip"),
        overwrite=False
    )

    if result.success:
        print(f"Imported {result.app_id} v{result.app_version}")

Working with Forms
~~~~~~~~~~~~~~~~~~

::

    # List forms in an application
    forms = client.list_forms(app_id="myApp", app_version="1")

    # Get a specific form
    form = client.get_form(
        app_id="myApp",
        app_version="1",
        form_id="customerForm"
    )

Health Checks
~~~~~~~~~~~~~

::

    # Test connection
    is_up = client.test_connection()

    # Get system info
    info = client.get_system_info()
    print(f"Joget {info.version} build {info.build}")

    # Comprehensive health check
    health = client.get_health_status()
    print(f"Status: {health.status.value}")
    print(f"Reachable: {health.reachable}")
    print(f"Authenticated: {health.authenticated}")

Database Operations
-------------------

Form Discovery
~~~~~~~~~~~~~~

::

    from joget_deployment_toolkit import FormDiscovery
    from joget_deployment_toolkit.models import DatabaseConfig

    db_config = DatabaseConfig(
        host="localhost",
        port=3306,
        database="jwdb",
        user="root",
        password="password"
    )

    with FormDiscovery(client, db_config) as discovery:
        forms = discovery.discover_all_forms("myApp", "1")
        for form in forms:
            print(f"{form.form_id}: {form.form_name} (table: {form.table_name})")

Using Repositories
~~~~~~~~~~~~~~~~~~

::

    from joget_deployment_toolkit.database import DatabaseConnectionPool, FormRepository
    from joget_deployment_toolkit.models import DatabaseConfig

    db_config = DatabaseConfig(
        host="localhost",
        port=3306,
        database="jwdb",
        user="root",
        password="password"
    )

    pool = DatabaseConnectionPool(db_config)
    form_repo = FormRepository(pool)

    # Find all forms in an app
    forms = form_repo.find_by_app("myApp", "1")

    # Get form definition
    definition = form_repo.get_form_definition("myApp", "1", "customerForm")

    # Check if table exists
    table_exists = form_repo.check_table_exists("app_fd_customer")

    pool.close()

Error Handling
--------------

::

    from joget_deployment_toolkit.exceptions import (
        AuthenticationError,
        NotFoundError,
        ConnectionError
    )

    try:
        apps = client.list_applications()
    except AuthenticationError:
        print("Invalid credentials")
    except NotFoundError:
        print("Endpoint not found")
    except ConnectionError:
        print("Cannot connect to Joget server")

Next Steps
----------

* Read the :doc:`examples` for more use cases
* Check the :doc:`api/client` for complete API reference
* See the :doc:`migration_guide` if upgrading from v2.0.x
