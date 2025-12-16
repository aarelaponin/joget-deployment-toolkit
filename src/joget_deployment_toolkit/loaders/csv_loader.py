"""
CSV data loader with infrastructure field stripping.

Loads CSV files and prepares them for Joget API submission by automatically
removing infrastructure fields that Joget auto-generates (id, dateCreated, etc.).
"""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


# Infrastructure fields that Joget auto-generates
INFRASTRUCTURE_FIELDS: Set[str] = {
    "id",
    "dateCreated",
    "dateModified",
    "createdBy",
    "modifiedBy",
    "createdByName",
    "modifiedByName",
}


class CSVDataLoader:
    """
    Load and preprocess CSV data for Joget forms.

    Automatically strips infrastructure fields that Joget generates,
    preventing conflicts when submitting data via API.

    Example:
        >>> loader = CSVDataLoader()
        >>> records = loader.load_csv(Path("config/metadata/md01maritalStatus.csv"))
        >>> print(records[0])
        {'code': 'single', 'name': 'Single'}
    """

    @staticmethod
    def load_csv(
        csv_file: Path,
        *,
        strip_infrastructure: bool = True,
        encoding: str = "utf-8",
    ) -> List[Dict[str, Any]]:
        """
        Load CSV file and return records.

        Args:
            csv_file: Path to CSV file
            strip_infrastructure: Remove id, dateCreated, etc. (default: True)
            encoding: File encoding (default: utf-8)

        Returns:
            List of record dictionaries (business fields only if strip_infrastructure=True)

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV is empty or malformed

        Example:
            >>> records = CSVDataLoader.load_csv(
            ...     Path("config/metadata/md01maritalStatus.csv")
            ... )
            >>> print(f"Loaded {len(records)} records")
            Loaded 4 records
        """
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        with open(csv_file, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                raise ValueError(f"CSV file is empty or has no header: {csv_file}")

            # Load all rows
            records = list(reader)

        if not records:
            logger.warning(f"CSV file has no data rows: {csv_file}")
            return []

        # Strip infrastructure fields if requested
        if strip_infrastructure:
            original_count = len(records)
            records = CSVDataLoader.strip_infrastructure_fields(records)

            # Log what was stripped
            if records and original_count > 0:
                original_fields = set(csv.DictReader(open(csv_file, 'r', encoding=encoding)).__next__().keys())
                stripped_fields = original_fields & {f.lower() for f in INFRASTRUCTURE_FIELDS}
                if stripped_fields:
                    logger.debug(
                        f"Stripped infrastructure fields from {csv_file.name}: "
                        f"{', '.join(sorted(stripped_fields))}"
                    )

        logger.info(
            f"Loaded {len(records)} records from {csv_file.name} "
            f"({'with infrastructure stripped' if strip_infrastructure else 'raw'})"
        )

        return records

    @staticmethod
    def strip_infrastructure_fields(
        records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove infrastructure fields from records.

        Infrastructure fields are those that Joget auto-generates:
        - id (primary key)
        - dateCreated, dateModified (timestamps)
        - createdBy, modifiedBy (usernames)
        - createdByName, modifiedByName (full names)

        Args:
            records: List of record dictionaries

        Returns:
            New list with infrastructure fields removed

        Example:
            >>> records = [
            ...     {'id': '1', 'code': 'single', 'name': 'Single', 'dateCreated': '2024-01-01'}
            ... ]
            >>> cleaned = CSVDataLoader.strip_infrastructure_fields(records)
            >>> print(cleaned[0])
            {'code': 'single', 'name': 'Single'}
        """
        cleaned = []
        infrastructure_lower = {f.lower() for f in INFRASTRUCTURE_FIELDS}

        for record in records:
            # Remove infrastructure fields (case-insensitive)
            cleaned_record = {
                k: v
                for k, v in record.items()
                if k.lower() not in infrastructure_lower
            }
            cleaned.append(cleaned_record)

        return cleaned

    @staticmethod
    def load_all_csv_from_dir(
        data_dir: Path,
        *,
        pattern: str = "md*.csv",
        strip_infrastructure: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load all CSV files from directory.

        Args:
            data_dir: Directory containing CSV files
            pattern: Glob pattern for files (default: "md*.csv")
            strip_infrastructure: Strip infrastructure fields (default: True)

        Returns:
            Dictionary mapping form_id -> records

        Raises:
            FileNotFoundError: If data directory doesn't exist

        Example:
            >>> data = CSVDataLoader.load_all_csv_from_dir(
            ...     Path("config/metadata")
            ... )
            >>> print(f"Loaded {len(data)} forms")
            Loaded 49 forms
            >>> print(f"md01maritalStatus has {len(data['md01maritalStatus'])} records")
            md01maritalStatus has 4 records
        """
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        if not data_dir.is_dir():
            raise ValueError(f"Path is not a directory: {data_dir}")

        csv_files = sorted(data_dir.glob(pattern))

        if not csv_files:
            logger.warning(f"No CSV files found in {data_dir} matching {pattern}")
            return {}

        data = {}
        successful = 0
        failed = 0

        for csv_file in csv_files:
            # Derive form ID from filename (remove .csv extension)
            form_id = csv_file.stem

            try:
                records = CSVDataLoader.load_csv(
                    csv_file, strip_infrastructure=strip_infrastructure
                )
                data[form_id] = records
                successful += 1

            except Exception as e:
                logger.error(f"Failed to load {csv_file.name}: {e}")
                failed += 1

        logger.info(
            f"Loaded {successful} CSV files from {data_dir} "
            f"({failed} failed)" if failed else f"Loaded {successful} CSV files from {data_dir}"
        )

        return data

    @staticmethod
    def validate_records(
        records: List[Dict[str, Any]], *, form_id: str = "form"
    ) -> None:
        """
        Validate that records don't contain infrastructure fields.

        Raises ValidationError if infrastructure fields are found.

        Args:
            records: Records to validate
            form_id: Form ID for error messages

        Raises:
            ValueError: If records contain infrastructure fields

        Example:
            >>> records = [{'code': 'single', 'name': 'Single'}]
            >>> CSVDataLoader.validate_records(records, form_id="md01maritalStatus")
            # No exception - records are valid
        """
        if not records:
            return

        infrastructure_lower = {f.lower() for f in INFRASTRUCTURE_FIELDS}

        for i, record in enumerate(records):
            invalid_fields = {k for k in record.keys() if k.lower() in infrastructure_lower}
            if invalid_fields:
                raise ValueError(
                    f"Record {i + 1} in {form_id} contains infrastructure fields "
                    f"that Joget auto-generates: {', '.join(sorted(invalid_fields))}. "
                    f"These fields must be removed before submission."
                )
