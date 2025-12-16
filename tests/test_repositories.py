"""
Tests for database repositories.

Tests cover:
- BaseRepository abstract methods and utilities
- FormRepository CRUD and query operations
- ApplicationRepository CRUD and query operations
- Connection pool integration
- Error handling
"""

from unittest.mock import MagicMock, Mock

import pytest

from joget_deployment_toolkit.database import DatabaseConnectionPool
from joget_deployment_toolkit.database.repositories import (
    ApplicationRepository,
    FormRepository,
)
from joget_deployment_toolkit.models import ApplicationInfo, DatabaseConfig, FormInfo

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_config():
    """Database configuration for testing."""
    return DatabaseConfig(
        host="localhost", port=3306, database="jwdb_test", user="test_user", password="test_pass"
    )


@pytest.fixture
def mock_pool():
    """Mock database connection pool."""
    pool = Mock(spec=DatabaseConnectionPool)

    # Create mock cursor with context manager support
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    mock_cursor.fetchall = Mock(return_value=[])
    mock_cursor.fetchone = Mock(return_value=None)
    mock_cursor.rowcount = 0

    # Create mock connection with context manager support
    mock_connection = MagicMock()
    mock_connection.__enter__ = Mock(return_value=mock_connection)
    mock_connection.__exit__ = Mock(return_value=False)
    mock_connection.autocommit = True

    pool.get_cursor = Mock(return_value=mock_cursor)
    pool.get_connection = Mock(return_value=mock_connection)

    return pool


@pytest.fixture
def form_repository(mock_pool):
    """FormRepository instance with mocked pool."""
    return FormRepository(mock_pool)


@pytest.fixture
def app_repository(mock_pool):
    """ApplicationRepository instance with mocked pool."""
    return ApplicationRepository(mock_pool)


# ============================================================================
# BaseRepository Tests
# ============================================================================


class TestBaseRepository:
    """Test BaseRepository functionality."""

    def test_execute_query_success(self, mock_pool):
        """Test execute_query returns results."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [
            {"id": "1", "name": "Test"},
            {"id": "2", "name": "Test2"},
        ]

        repo = FormRepository(mock_pool)

        # Act
        results = repo.execute_query("SELECT * FROM test")

        # Assert
        assert len(results) == 2
        assert results[0]["id"] == "1"
        mock_cursor.execute.assert_called_once()

    def test_execute_query_with_params(self, mock_pool):
        """Test execute_query with parameters."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"id": "1"}]

        repo = FormRepository(mock_pool)

        # Act
        results = repo.execute_query("SELECT * FROM test WHERE id = %s", ("1",))

        # Assert
        assert len(results) == 1
        mock_cursor.execute.assert_called_with("SELECT * FROM test WHERE id = %s", ("1",))

    def test_execute_update_returns_affected_rows(self, mock_pool):
        """Test execute_update returns row count."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.rowcount = 3

        repo = FormRepository(mock_pool)

        # Act
        affected = repo.execute_update("UPDATE test SET status = %s", ("active",))

        # Assert
        assert affected == 3
        mock_cursor.execute.assert_called_once()

    def test_execute_scalar_returns_single_value(self, mock_pool):
        """Test execute_scalar returns first column value."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"count": 42}]

        repo = FormRepository(mock_pool)

        # Act
        result = repo.execute_scalar("SELECT COUNT(*) as count FROM test")

        # Assert
        assert result == 42

    def test_execute_scalar_returns_none_when_no_results(self, mock_pool):
        """Test execute_scalar returns None for empty results."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = []

        repo = FormRepository(mock_pool)

        # Act
        result = repo.execute_scalar("SELECT COUNT(*) FROM test")

        # Assert
        assert result is None

    def test_exists_returns_true_when_rows_found(self, mock_pool):
        """Test exists returns True when rows match."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"id": "1"}]

        repo = FormRepository(mock_pool)

        # Act
        result = repo.exists("SELECT 1 FROM test WHERE id = %s", ("1",))

        # Assert
        assert result is True

    def test_exists_returns_false_when_no_rows(self, mock_pool):
        """Test exists returns False when no rows match."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = []

        repo = FormRepository(mock_pool)

        # Act
        result = repo.exists("SELECT 1 FROM test WHERE id = %s", ("999",))

        # Assert
        assert result is False

    def test_count_with_where_clause(self, mock_pool):
        """Test count with WHERE clause."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"count": 5}]

        repo = FormRepository(mock_pool)

        # Act
        result = repo.count("users", "status = %s", ("active",))

        # Assert
        assert result == 5
        # Verify the query structure
        call_args = mock_cursor.execute.call_args[0]
        assert "SELECT COUNT(*)" in call_args[0]
        assert "FROM users" in call_args[0]
        assert "WHERE status = %s" in call_args[0]


# ============================================================================
# FormRepository Tests
# ============================================================================


class TestFormRepository:
    """Test FormRepository functionality."""

    def test_find_by_app_returns_forms(self, form_repository, mock_pool):
        """Test find_by_app returns list of forms."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        # Return forms on first call, empty list for API endpoint queries
        mock_cursor.fetchall.side_effect = [
            # First call - get forms
            [
                {
                    "formId": "form1",
                    "name": "Form 1",
                    "tableName": "app_fd_form1",
                    "appId": "testApp",
                    "appVersion": "1",
                },
                {
                    "formId": "form2",
                    "name": "Form 2",
                    "tableName": "app_fd_form2",
                    "appId": "testApp",
                    "appVersion": "1",
                },
            ],
            # Subsequent calls - API endpoint lookups (return empty)
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
        ]

        # Act
        forms = form_repository.find_by_app("testApp", "1")

        # Assert
        assert len(forms) == 2
        assert forms[0].form_id == "form1"
        assert forms[0].form_name == "Form 1"
        assert forms[1].form_id == "form2"

    def test_find_by_app_and_id_returns_specific_form(self, form_repository, mock_pool):
        """Test find_by_app_and_id returns specific form."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        # Return form on first call, empty for API endpoint lookups
        mock_cursor.fetchall.side_effect = [
            # First call - get form
            [
                {
                    "formId": "form1",
                    "name": "Form 1",
                    "tableName": "app_fd_form1",
                    "appId": "testApp",
                    "appVersion": "1",
                }
            ],
            # Subsequent calls - API endpoint lookups (return empty)
            [],
            [],
            [],
            [],
        ]

        # Act
        form = form_repository.find_by_app_and_id("testApp", "form1", "1")

        # Assert
        assert form is not None
        assert form.form_id == "form1"
        assert form.app_id == "testApp"

    def test_find_by_app_and_id_returns_none_when_not_found(self, form_repository, mock_pool):
        """Test find_by_app_and_id returns None when form not found."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = []

        # Act
        form = form_repository.find_by_app_and_id("testApp", "nonexistent", "1")

        # Assert
        assert form is None

    def test_find_by_table_name_returns_forms(self, form_repository, mock_pool):
        """Test find_by_table_name returns forms using table."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [
            {
                "formId": "form1",
                "name": "Form 1",
                "tableName": "app_fd_shared_table",
                "appId": "testApp",
                "appVersion": "1",
            }
        ]

        # Act
        forms = form_repository.find_by_table_name("app_fd_shared_table")

        # Assert
        assert len(forms) == 1
        assert forms[0].table_name == "app_fd_shared_table"

    def test_get_form_definition_returns_json(self, form_repository, mock_pool):
        """Test get_form_definition returns parsed JSON."""
        # Arrange
        import json

        form_def = {"name": "Test Form", "properties": {"elements": []}}
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"json": json.dumps(form_def)}]

        # Act
        definition = form_repository.get_form_definition("testApp", "1", "form1")

        # Assert
        assert definition is not None
        assert definition["name"] == "Test Form"
        assert "properties" in definition

    def test_get_form_definition_returns_none_when_not_found(self, form_repository, mock_pool):
        """Test get_form_definition returns None when not found."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = []

        # Act
        definition = form_repository.get_form_definition("testApp", "1", "nonexistent")

        # Assert
        assert definition is None

    def test_check_table_exists_returns_true(self, form_repository, mock_pool):
        """Test check_table_exists returns True when table exists."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"count": 1}]

        # Act
        exists = form_repository.check_table_exists("app_fd_form1")

        # Assert
        assert exists is True

    def test_check_table_exists_returns_false(self, form_repository, mock_pool):
        """Test check_table_exists returns False when table doesn't exist."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"count": 0}]

        # Act
        exists = form_repository.check_table_exists("nonexistent_table")

        # Assert
        assert exists is False

    def test_save_raises_not_implemented(self, form_repository):
        """Test save raises NotImplementedError."""
        # Arrange
        form = FormInfo(
            form_id="test",
            form_name="Test",
            table_name="app_fd_test",
            app_id="testApp",
            app_version="1",
        )

        # Act & Assert
        with pytest.raises(NotImplementedError):
            form_repository.save(form)

    def test_delete_raises_not_implemented(self, form_repository):
        """Test delete raises NotImplementedError."""
        # Act & Assert
        with pytest.raises(NotImplementedError):
            form_repository.delete("form1")


# ============================================================================
# ApplicationRepository Tests
# ============================================================================


class TestApplicationRepository:
    """Test ApplicationRepository functionality."""

    def test_find_published_returns_apps(self, app_repository, mock_pool):
        """Test find_published returns published applications."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [
            {
                "appId": "app1",
                "appVersion": "1",
                "name": "App 1",
                "published": 1,
                "dateCreated": "2024-01-01 00:00:00",
                "dateModified": "2024-01-02 00:00:00",
            },
            {
                "appId": "app2",
                "appVersion": "2",
                "name": "App 2",
                "published": 1,
                "dateCreated": "2024-01-01 00:00:00",
                "dateModified": "2024-01-02 00:00:00",
            },
        ]

        # Act
        apps = app_repository.find_published()

        # Assert
        assert len(apps) == 2
        assert apps[0].id == "app1"
        assert apps[0].published is True
        assert apps[1].id == "app2"

    def test_find_by_version_returns_specific_version(self, app_repository, mock_pool):
        """Test find_by_version returns specific app version."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [
            {
                "appId": "app1",
                "appVersion": "2",
                "name": "App 1",
                "published": 1,
                "dateCreated": "2024-01-01 00:00:00",
                "dateModified": "2024-01-02 00:00:00",
            }
        ]

        # Act
        app = app_repository.find_by_version("app1", "2")

        # Assert
        assert app is not None
        assert app.id == "app1"
        assert app.version == "2"

    def test_find_all_versions_returns_all_versions(self, app_repository, mock_pool):
        """Test find_all_versions returns all versions of an app."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [
            {
                "appId": "app1",
                "appVersion": "1",
                "name": "App 1",
                "published": 0,
                "dateCreated": "2024-01-01 00:00:00",
                "dateModified": "2024-01-02 00:00:00",
            },
            {
                "appId": "app1",
                "appVersion": "2",
                "name": "App 1",
                "published": 1,
                "dateCreated": "2024-01-01 00:00:00",
                "dateModified": "2024-01-02 00:00:00",
            },
        ]

        # Act
        versions = app_repository.find_all_versions("app1")

        # Assert
        assert len(versions) == 2
        assert versions[0].version == "1"
        assert versions[1].version == "2"

    def test_is_published_returns_true(self, app_repository, mock_pool):
        """Test is_published returns True for published app."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"published": 1}]

        # Act
        is_published = app_repository.is_published("app1", "1")

        # Assert
        assert is_published is True

    def test_is_published_returns_false(self, app_repository, mock_pool):
        """Test is_published returns False for unpublished app."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"published": 0}]

        # Act
        is_published = app_repository.is_published("app1", "1")

        # Assert
        assert is_published is False

    def test_count_versions_returns_count(self, app_repository, mock_pool):
        """Test count_versions returns number of versions."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [{"count": 3}]

        # Act
        count = app_repository.count_versions("app1")

        # Assert
        assert count == 3

    def test_search_by_name_returns_matching_apps(self, app_repository, mock_pool):
        """Test search_by_name returns matching applications."""
        # Arrange
        mock_cursor = mock_pool.get_cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = [
            {
                "appId": "farmersPortal",
                "appVersion": "1",
                "name": "Farmers Portal",
                "published": 1,
                "dateCreated": "2024-01-01 00:00:00",
                "dateModified": "2024-01-02 00:00:00",
            }
        ]

        # Act
        apps = app_repository.search_by_name("%farmer%")

        # Assert
        assert len(apps) == 1
        assert "farmer" in apps[0].name.lower()

    def test_save_raises_not_implemented(self, app_repository):
        """Test save raises NotImplementedError."""
        # Arrange
        app = ApplicationInfo(id="test", name="Test", version="1", published=False)

        # Act & Assert
        with pytest.raises(NotImplementedError):
            app_repository.save(app)

    def test_delete_raises_not_implemented(self, app_repository):
        """Test delete raises NotImplementedError."""
        # Act & Assert
        with pytest.raises(NotImplementedError):
            app_repository.delete("app1")
