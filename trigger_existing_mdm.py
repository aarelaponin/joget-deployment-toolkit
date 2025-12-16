#!/usr/bin/env python3
"""
Trigger FormCreator plugin for existing form_creator records.

The 30 existing records have file references but the plugin didn't execute.
This script updates each record to trigger the plugin.
"""

import sys
import logging
import time
import requests
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def get_existing_records():
    """Get all form_creator records via API."""
    url = "http://localhost:8084/jw/api/list/farmersPortal/app_fd_form_creator/list"
    headers = {
        'api_id': 'API-693d7ff0-253c-4a5d-9894-a92b47452a22',
        'api_key': 'b2cc0157ab464ff5b1f07a5907ef9690'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('data', [])
    return []


def update_record_to_trigger_plugin(record_id):
    """Update a record via form submission to trigger the plugin."""
    url = f"http://localhost:8084/jw/web/form/farmersPortal/1/form/formCreator/submit/{record_id}"
    headers = {
        'api_id': 'API-693d7ff0-253c-4a5d-9894-a92b47452a22',
        'api_key': 'b2cc0157ab464ff5b1f07a5907ef9690'
    }

    # Submit empty update (just to trigger post-processor)
    data = {'id': record_id}

    response = requests.post(url, headers=headers, data=data)
    return response.status_code == 200


def main():
    logger.info('=' * 70)
    logger.info('TRIGGER FORMCREATOR PLUGIN FOR EXISTING RECORDS')
    logger.info('=' * 70)
    logger.info('')

    # Get all records
    logger.info('Fetching existing form_creator records...')
    records = get_existing_records()

    if not records:
        logger.error('No records found or API failed!')
        return 1

    # Filter to md* forms (exclude x1, testMD02, etc.)
    md_records = [r for r in records if r.get('form_id', '').startswith('md')]

    logger.info(f'Found {len(md_records)} MDM records to process')
    logger.info('')

    # Update each record
    success = 0
    failed = 0

    for record in md_records:
        form_id = record.get('form_id')
        record_id = record.get('id')

        logger.info(f'Triggering plugin for {form_id} (ID: {record_id})...')

        if update_record_to_trigger_plugin(record_id):
            logger.info(f'  ✓ {form_id} updated')
            success += 1
        else:
            logger.error(f'  ✗ {form_id} failed')
            failed += 1

        # Small delay
        time.sleep(0.5)

    # Summary
    logger.info('')
    logger.info('=' * 70)
    logger.info(f'✓ Successful: {success}')
    logger.info(f'✗ Failed: {failed}')
    logger.info('=' * 70)
    logger.info('')
    logger.info('Check the Joget forms list - all MDM forms should now be there!')

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
