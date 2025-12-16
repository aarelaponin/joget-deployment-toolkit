#!/usr/bin/env python3
"""
Test MDM deployment with a single form
"""

import sys
import logging
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from joget_deployment_toolkit import JogetClient
from joget_deployment_toolkit.operations.mdm_deployer import MDMDataDeployer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Test deployment of single MDM form."""

    # Configuration
    forms_dir = Path('/Users/aarelaponin/PycharmProjects/dev/frs-implementation-hub/config/metadata_forms')
    data_dir = Path('/Users/aarelaponin/PycharmProjects/dev/frs-implementation-hub/config/metadata')
    target_app_id = 'farmersPortal'
    formcreator_api_id = 'API-693d7ff0-253c-4a5d-9894-a92b47452a22'
    formcreator_api_key = 'b2cc0157ab464ff5b1f07a5907ef9690'

    # Test form
    test_form = 'md01maritalStatus'

    logger.info('=' * 70)
    logger.info('SINGLE MDM FORM DEPLOYMENT TEST')
    logger.info('=' * 70)
    logger.info(f'Form: {test_form}')
    logger.info(f'Target app: {target_app_id}')
    logger.info('=' * 70)

    try:
        # Create client for jdx4
        logger.info('Connecting to jdx4...')
        client = JogetClient.from_instance('jdx4')
        logger.info(f'✓ Connected to: {client.base_url}')
        logger.info('')

        # Read form definition
        form_file = forms_dir / f'{test_form}.json'
        csv_file = data_dir / f'{test_form}.csv'

        logger.info(f'Reading form definition from: {form_file}')
        with open(form_file) as f:
            form_def = json.load(f)

        logger.info(f'Form name: {form_def["properties"]["name"]}')
        logger.info('')

        # Create deployer
        deployer = MDMDataDeployer(client)

        # Deploy single form
        logger.info('Deploying form...')
        result = deployer.deploy_mdm_form_with_data(
            form_id=test_form,
            form_name=form_def['properties']['name'],
            form_definition=form_def,
            csv_file=csv_file,
            target_app_id=target_app_id,
            target_app_version='1',
            formcreator_api_id=formcreator_api_id,
            formcreator_api_key=formcreator_api_key,
            create_crud=True,
            create_api_endpoint=True,
        )

        # Report results
        logger.info('')
        logger.info('=' * 70)
        logger.info('DEPLOYMENT RESULT')
        logger.info('=' * 70)

        if result.success:
            logger.info(f'✓ SUCCESS')
            logger.info(f'  Form created: {result.form_created}')
            logger.info(f'  Records imported: {result.records_submitted}/{result.total_records}')
        elif result.partial_success:
            logger.warning(f'⚠ PARTIAL SUCCESS')
            logger.warning(f'  Form created: {result.form_created}')
            logger.warning(f'  Records imported: {result.records_submitted}/{result.total_records}')
        else:
            logger.error(f'✗ FAILED')
            logger.error(f'  Errors: {result.errors}')

        logger.info('=' * 70)

        return 0 if result.success else 1

    except Exception as e:
        logger.error(f'Test failed with error: {e}')
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
