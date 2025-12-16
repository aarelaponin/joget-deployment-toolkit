#!/usr/bin/env python3
"""
Basic usage example for joget-toolkit

Demonstrates:
- Creating a JogetClient
- Discovering forms in an application
- Working with form metadata
"""

from joget_deployment_toolkit import JogetClient, FormDiscovery
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Database configuration (from .env file typically)
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'jwdb',
        'user': 'root',
        'password': 'your_password'
    }

    # Initialize Joget client
    client = JogetClient(
        base_url='http://localhost:8080/jw/api/form',
        debug=True
    )

    # Test connection
    if client.test_connection():
        logger.info("✓ Connected to Joget server")
    else:
        logger.error("✗ Failed to connect to Joget server")
        return

    # Initialize form discovery
    discovery = FormDiscovery(
        client=client,
        db_config=db_config
    )

    # Discover forms in an application
    app_id = 'masterData'
    app_version = '1'

    logger.info(f"\nDiscovering forms in {app_id} v{app_version}...")

    forms = discovery.discover_all_forms(
        app_id=app_id,
        app_version=app_version
    )

    logger.info(f"Found {len(forms)} forms:")
    for form in forms:
        logger.info(f"  - {form.form_id}: {form.form_name}")
        logger.info(f"    Table: {form.table_name}")
        if form.api_endpoint:
            logger.info(f"    API: {form.api_endpoint} (ID: {form.api_id})")

    # Get form definition
    if forms:
        form = forms[0]
        logger.info(f"\nFetching definition for {form.form_id}...")

        definition = discovery.get_form_definition(
            app_id=app_id,
            app_version=app_version,
            form_id=form.form_id
        )

        if definition:
            logger.info(f"✓ Retrieved form definition")
            logger.info(f"  Fields: {len(definition.get('properties', {}).get('elements', []))}")
        else:
            logger.warning(f"✗ No definition found")


if __name__ == '__main__':
    main()
