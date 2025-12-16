Form Discovery
==============

Extract and analyze form definitions from Joget databases.

FormDiscovery
-------------

Main class for discovering forms and their metadata.

.. autoclass:: joget_deployment_toolkit.discovery.FormDiscovery
   :members:
   :special-members: __init__, __enter__, __exit__
   :show-inheritance:

Usage Examples
--------------

Basic Discovery
~~~~~~~~~~~~~~~

::

    from joget_deployment_toolkit import JogetClient, FormDiscovery
    from joget_deployment_toolkit.models import DatabaseConfig

    client = JogetClient.from_env()
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
            print(f"{form.form_id}: {form.form_name}")

Extract Form Definitions
~~~~~~~~~~~~~~~~~~~~~~~~

::

    with FormDiscovery(client, db_config) as discovery:
        forms = discovery.discover_all_forms("myApp", "1")

        # Extract full definitions
        definitions = discovery.extract_form_definitions(forms)
        for form_id, definition in definitions.items():
            print(f"Form {form_id} has {len(definition.get('elements', []))} elements")
