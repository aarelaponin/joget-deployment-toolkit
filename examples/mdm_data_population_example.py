#!/usr/bin/env python3
"""
MDM Data Population Example

This example demonstrates how to use the joget-toolkit to deploy Master Data
Management (MDM) forms with data population from CSV files.

Prerequisites:
1. Joget DX instance running
2. FormCreator plugin installed and configured
3. FRS configuration set up (~/.frs-dev/config.yaml)
4. CSV data files in config/metadata/
5. Form JSON definitions in config/metadata_forms/

Usage:
    python examples/mdm_data_population_example.py
"""

import json
import logging
from pathlib import Path

from joget_deployment_toolkit import DataSubmissionResult
from joget_deployment_toolkit.integrations import from_frs
from joget_deployment_toolkit.loaders import CSVDataLoader
from joget_deployment_toolkit.operations import MDMDataDeployer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def example_1_load_csv_data():
    """Example 1: Load CSV data with infrastructure field stripping."""
    logger.info("=" * 60)
    logger.info("Example 1: Load CSV Data")
    logger.info("=" * 60)

    csv_file = Path("config/metadata/md01maritalStatus.csv")

    if not csv_file.exists():
        logger.warning(f"CSV file not found: {csv_file}")
        return

    # Load CSV with automatic infrastructure field stripping
    records = CSVDataLoader.load_csv(csv_file, strip_infrastructure=True)

    logger.info(f"Loaded {len(records)} records from {csv_file.name}")
    for i, record in enumerate(records[:3], 1):  # Show first 3
        logger.info(f"  Record {i}: {record}")

    # Validate records don't contain infrastructure fields
    try:
        CSVDataLoader.validate_records(records, form_id="md01maritalStatus")
        logger.info("✓ Validation passed: No infrastructure fields found")
    except ValueError as e:
        logger.error(f"✗ Validation failed: {e}")


def example_2_submit_single_record():
    """Example 2: Submit single record via API."""
    logger.info("=" * 60)
    logger.info("Example 2: Submit Single Record")
    logger.info("=" * 60)

    # Connect to Joget instance via FRS config
    client = from_frs("jdx4")  # Change to your instance name

    # Single record (business fields only)
    data = {"code": "single", "name": "Single Person"}

    # Submit to form (requires API endpoint to be created)
    try:
        result = client.submit_form_data(
            form_id="md01maritalStatus",
            data=data,
            api_id="API-xxxx-xxxx-xxxx",  # Replace with actual API ID
        )

        if result.success:
            logger.info(f"✓ Record created: {result.record_id}")
        else:
            logger.error(f"✗ Submission failed: {result.message}")

    except Exception as e:
        logger.error(f"Error submitting data: {e}")


def example_3_submit_batch_records():
    """Example 3: Submit batch records from CSV."""
    logger.info("=" * 60)
    logger.info("Example 3: Submit Batch Records")
    logger.info("=" * 60)

    client = from_frs("jdx4")
    csv_file = Path("config/metadata/md01maritalStatus.csv")

    if not csv_file.exists():
        logger.warning(f"CSV file not found: {csv_file}")
        return

    # Load records
    records = CSVDataLoader.load_csv(csv_file, strip_infrastructure=True)

    logger.info(f"Submitting {len(records)} records...")

    # Progress callback
    def progress(current, total, result):
        status = "✓" if result.success else "✗"
        logger.info(f"  [{current}/{total}] {status} {result.message or 'OK'}")

    try:
        results = client.submit_form_data_batch(
            form_id="md01maritalStatus",
            records=records,
            api_id="API-xxxx-xxxx-xxxx",  # Replace with actual API ID
            progress_callback=progress,
        )

        # Summary
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        logger.info(f"\nResults: {successful} successful, {failed} failed")

    except Exception as e:
        logger.error(f"Error in batch submission: {e}")


def example_4_deploy_single_mdm_form():
    """Example 4: Deploy single MDM form with data."""
    logger.info("=" * 60)
    logger.info("Example 4: Deploy Single MDM Form")
    logger.info("=" * 60)

    client = from_frs("jdx4")
    deployer = MDMDataDeployer(client)

    # Form definition
    form_def = {
        "className": "org.joget.apps.form.model.Form",
        "properties": {
            "id": "md01maritalStatus",
            "name": "MD.01 - Marital Status",
            "tableName": "md01maritalStatus",
        },
        "elements": [
            {
                "className": "org.joget.apps.form.lib.TextField",
                "properties": {"id": "code", "label": "Code", "required": "true"},
            },
            {
                "className": "org.joget.apps.form.lib.TextField",
                "properties": {"id": "name", "label": "Name", "required": "true"},
            },
        ],
    }

    csv_file = Path("config/metadata/md01maritalStatus.csv")

    if not csv_file.exists():
        logger.warning(f"CSV file not found: {csv_file}")
        return

    try:
        result = deployer.deploy_mdm_form_with_data(
            form_id="md01maritalStatus",
            form_name="MD.01 - Marital Status",
            form_definition=form_def,
            csv_file=csv_file,
            target_app_id="farmersPortal",
            formcreator_api_id="fc_api",  # Replace with actual formCreator API ID
            create_crud=True,
            create_api_endpoint=True,
        )

        logger.info(str(result))

        if result.success:
            logger.info(
                f"✓ Deployment successful: {result.records_submitted} records loaded"
            )
        elif result.partial_success:
            logger.warning(
                f"⚠ Partial success: {result.records_submitted}/{result.total_records} records loaded"
            )
        else:
            logger.error(f"✗ Deployment failed: {result.errors}")

    except Exception as e:
        logger.error(f"Deployment error: {e}")


def example_5_deploy_all_mdm_forms():
    """Example 5: Deploy all MDM forms from directories."""
    logger.info("=" * 60)
    logger.info("Example 5: Deploy All MDM Forms")
    logger.info("=" * 60)

    client = from_frs("jdx4")
    deployer = MDMDataDeployer(client)

    forms_dir = Path("config/metadata_forms")
    data_dir = Path("config/metadata")

    if not forms_dir.exists():
        logger.warning(f"Forms directory not found: {forms_dir}")
        return

    if not data_dir.exists():
        logger.warning(f"Data directory not found: {data_dir}")
        return

    try:
        results = deployer.deploy_all_mdm_from_directory(
            forms_dir=forms_dir,
            data_dir=data_dir,
            target_app_id="farmersPortal",
            formcreator_api_id="fc_api",  # Replace with actual formCreator API ID
            create_crud=True,
            create_api_endpoint=True,
            # dry_run=True,  # Uncomment to preview without executing
        )

        # Summary statistics
        successful = sum(1 for r in results if r.success)
        partial = sum(1 for r in results if r.partial_success and not r.success)
        failed = sum(1 for r in results if not r.form_created)

        logger.info("\n" + "=" * 60)
        logger.info("DEPLOYMENT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total forms: {len(results)}")
        logger.info(f"✓ Successful: {successful}")
        logger.info(f"⚠ Partial: {partial}")
        logger.info(f"✗ Failed: {failed}")

        # Show failed forms
        if failed > 0:
            logger.info("\nFailed forms:")
            for r in results:
                if not r.form_created:
                    logger.info(f"  - {r.form_id}: {r.errors[0] if r.errors else 'Unknown error'}")

    except Exception as e:
        logger.error(f"Batch deployment error: {e}")


def main():
    """Run all examples."""
    logger.info("MDM Data Population Examples")
    logger.info("=" * 60)

    # Example 1: Load CSV data
    try:
        example_1_load_csv_data()
    except Exception as e:
        logger.error(f"Example 1 failed: {e}")

    # Note: Examples 2-5 require actual Joget instance configuration
    # Uncomment to run when you have the environment set up

    # example_2_submit_single_record()
    # example_3_submit_batch_records()
    # example_4_deploy_single_mdm_form()
    # example_5_deploy_all_mdm_forms()

    logger.info("\nAll examples completed!")


if __name__ == "__main__":
    main()
