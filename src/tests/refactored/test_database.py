"""
Tests for database layer.
"""

from unittest.mock import Mock, patch

import pytest

from joget_deployment_toolkit.config import DatabaseConfig
from joget_deployment_toolkit.database import DatabaseConnectionPool, FormRepository


class TestDatabaseConnectionPool:
    """Test database connection pool."""

    def test_singleton(self):
        """Test singleton pattern."""
        config = DatabaseConfig(host="localhost", user="test", password="test")

        with patch("mysql.connector.pooling.MySQLConnectionPool"):
            pool1 = DatabaseConnectionPool(config)
            pool2 = DatabaseConnectionPool()

            assert pool1 is pool2


class TestFormRepository:
    """Test form repository."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock connection pool."""
        return Mock(spec=DatabaseConnectionPool)

    def test_find_by_id(self, mock_pool):
        """Test finding form by ID."""
        repo = FormRepository(mock_pool)

        # Mock cursor and results
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [{"formId": "test_form", "name": "Test Form"}]

        with patch.object(repo, "execute_query", return_value=mock_cursor.fetchall()):
            form = repo.find_by_id("test_form")

            assert form is not None
            assert form.form_id == "test_form"
