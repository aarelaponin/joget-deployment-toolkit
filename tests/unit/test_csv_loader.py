"""
Unit tests for CSV data loader.
"""

import csv
import tempfile
from pathlib import Path

import pytest

from joget_deployment_toolkit.loaders import CSVDataLoader, INFRASTRUCTURE_FIELDS


class TestCSVDataLoader:
    """Test CSV data loading and infrastructure field stripping."""

    def test_infrastructure_fields_defined(self):
        """Test that infrastructure fields are properly defined."""
        assert "id" in INFRASTRUCTURE_FIELDS
        assert "dateCreated" in INFRASTRUCTURE_FIELDS
        assert "dateModified" in INFRASTRUCTURE_FIELDS
        assert "createdBy" in INFRASTRUCTURE_FIELDS
        assert "modifiedBy" in INFRASTRUCTURE_FIELDS

    def test_strip_infrastructure_fields(self):
        """Test infrastructure field stripping from records."""
        records = [
            {
                "id": "1",
                "code": "single",
                "name": "Single",
                "dateCreated": "2024-01-01",
                "dateModified": "2024-01-01",
            },
            {
                "id": "2",
                "code": "married",
                "name": "Married",
                "dateCreated": "2024-01-01",
            },
        ]

        cleaned = CSVDataLoader.strip_infrastructure_fields(records)

        assert len(cleaned) == 2
        assert cleaned[0] == {"code": "single", "name": "Single"}
        assert cleaned[1] == {"code": "married", "name": "Married"}

    def test_strip_infrastructure_fields_case_insensitive(self):
        """Test case-insensitive infrastructure field stripping."""
        records = [
            {
                "ID": "1",  # Uppercase
                "Code": "single",
                "datecreated": "2024-01-01",  # Lowercase
                "DateModified": "2024-01-01",  # Mixed case
            }
        ]

        cleaned = CSVDataLoader.strip_infrastructure_fields(records)

        assert len(cleaned) == 1
        assert "ID" not in cleaned[0]
        assert "datecreated" not in cleaned[0]
        assert "DateModified" not in cleaned[0]
        assert cleaned[0] == {"Code": "single"}

    def test_load_csv_with_infrastructure_fields(self):
        """Test loading CSV file with infrastructure fields."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "code", "name", "dateCreated"]
            )
            writer.writeheader()
            writer.writerow(
                {"id": "1", "code": "single", "name": "Single", "dateCreated": "2024-01-01"}
            )
            writer.writerow(
                {"id": "2", "code": "married", "name": "Married", "dateCreated": "2024-01-02"}
            )
            temp_path = Path(f.name)

        try:
            # Load with stripping (default)
            records = CSVDataLoader.load_csv(temp_path, strip_infrastructure=True)

            assert len(records) == 2
            assert records[0] == {"code": "single", "name": "Single"}
            assert records[1] == {"code": "married", "name": "Married"}

        finally:
            temp_path.unlink()

    def test_load_csv_without_stripping(self):
        """Test loading CSV file without infrastructure field stripping."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "code", "name"])
            writer.writeheader()
            writer.writerow({"id": "1", "code": "single", "name": "Single"})
            temp_path = Path(f.name)

        try:
            # Load without stripping
            records = CSVDataLoader.load_csv(temp_path, strip_infrastructure=False)

            assert len(records) == 1
            assert records[0] == {"id": "1", "code": "single", "name": "Single"}

        finally:
            temp_path.unlink()

    def test_load_csv_file_not_found(self):
        """Test loading non-existent CSV file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            CSVDataLoader.load_csv(Path("/nonexistent/file.csv"))

    def test_load_csv_empty_file(self):
        """Test loading empty CSV file returns empty list."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["code", "name"])
            writer.writeheader()
            temp_path = Path(f.name)

        try:
            records = CSVDataLoader.load_csv(temp_path)
            assert records == []

        finally:
            temp_path.unlink()

    def test_validate_records_clean_data(self):
        """Test validation passes for clean data."""
        records = [{"code": "single", "name": "Single"}]

        # Should not raise exception
        CSVDataLoader.validate_records(records, form_id="test_form")

    def test_validate_records_with_infrastructure_fields(self):
        """Test validation fails for data with infrastructure fields."""
        records = [
            {"id": "1", "code": "single", "name": "Single", "dateCreated": "2024-01-01"}
        ]

        with pytest.raises(ValueError, match="infrastructure fields"):
            CSVDataLoader.validate_records(records, form_id="test_form")

    def test_load_all_csv_from_dir(self):
        """Test loading all CSV files from directory."""
        # Create temporary directory with CSV files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create md01.csv
            with open(tmp_path / "md01maritalStatus.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["code", "name"])
                writer.writeheader()
                writer.writerow({"code": "single", "name": "Single"})

            # Create md02.csv
            with open(tmp_path / "md02gender.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["code", "name"])
                writer.writeheader()
                writer.writerow({"code": "male", "name": "Male"})

            # Create non-matching file
            with open(tmp_path / "other.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["code", "name"])
                writer.writeheader()

            # Load all md*.csv files
            data = CSVDataLoader.load_all_csv_from_dir(tmp_path, pattern="md*.csv")

            assert len(data) == 2
            assert "md01maritalStatus" in data
            assert "md02gender" in data
            assert "other" not in data
            assert data["md01maritalStatus"][0] == {"code": "single", "name": "Single"}
            assert data["md02gender"][0] == {"code": "male", "name": "Male"}

    def test_load_all_csv_from_dir_not_found(self):
        """Test loading from non-existent directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            CSVDataLoader.load_all_csv_from_dir(Path("/nonexistent/dir"))
