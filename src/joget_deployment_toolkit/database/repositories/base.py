"""
Base repository with common database operations.

Provides abstract base class for repository pattern implementation with:
- Generic CRUD operations
- Query execution utilities
- Transaction support
- Error handling
- Logging integration
"""

import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generic, TypeVar

from ..connection import DatabaseConnectionPool

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common database operations.

    This class implements the Repository pattern for data access, providing
    a clean abstraction over database operations. Subclasses must implement
    the abstract methods for entity-specific operations.

    Type Parameters:
        T: The entity type managed by this repository

    Example:
        >>> class UserRepository(BaseRepository[User]):
        ...     def find_by_id(self, id: str) -> Optional[User]:
        ...         query = "SELECT * FROM users WHERE id = %s"
        ...         results = self.execute_query(query, (id,))
        ...         return User(**results[0]) if results else None
        ...
        ...     def find_all(self) -> List[User]:
        ...         query = "SELECT * FROM users"
        ...         results = self.execute_query(query)
        ...         return [User(**r) for r in results]
        ...
        ...     def save(self, entity: User) -> User:
        ...         # Implementation...
        ...         pass
        ...
        ...     def delete(self, id: str) -> bool:
        ...         query = "DELETE FROM users WHERE id = %s"
        ...         affected = self.execute_update(query, (id,))
        ...         return affected > 0
    """

    def __init__(self, connection_pool: DatabaseConnectionPool):
        """
        Initialize repository with database connection pool.

        Args:
            connection_pool: Database connection pool for executing queries
        """
        self.pool = connection_pool
        self.logger = logger

    # ========================================================================
    # Abstract Methods (Must be implemented by subclasses)
    # ========================================================================

    @abstractmethod
    def find_by_id(self, id: str) -> T | None:
        """
        Find entity by its unique identifier.

        Args:
            id: Unique identifier of the entity

        Returns:
            Entity instance if found, None otherwise

        Example:
            >>> user = user_repository.find_by_id("user123")
            >>> if user:
            ...     print(f"Found: {user.name}")
        """
        pass

    @abstractmethod
    def find_all(self) -> list[T]:
        """
        Find all entities of this type.

        Returns:
            List of all entities (may be empty)

        Warning:
            This method loads all entities into memory. For large datasets,
            consider implementing pagination or streaming.

        Example:
            >>> all_users = user_repository.find_all()
            >>> print(f"Total users: {len(all_users)}")
        """
        pass

    @abstractmethod
    def save(self, entity: T) -> T:
        """
        Save (insert or update) an entity.

        Args:
            entity: Entity instance to save

        Returns:
            Saved entity (may have updated fields like ID, timestamps)

        Raises:
            ValueError: If entity data is invalid
            DatabaseError: If save operation fails

        Example:
            >>> user = User(name="John", email="john@example.com")
            >>> saved_user = user_repository.save(user)
            >>> print(f"Saved with ID: {saved_user.id}")
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        Delete entity by its unique identifier.

        Args:
            id: Unique identifier of the entity to delete

        Returns:
            True if entity was deleted, False if not found

        Example:
            >>> if user_repository.delete("user123"):
            ...     print("User deleted")
            ... else:
            ...     print("User not found")
        """
        pass

    # ========================================================================
    # Query Execution Methods
    # ========================================================================

    def execute_query(self, query: str, params: tuple | None = None) -> list[dict[str, Any]]:
        """
        Execute a SELECT query and return results as dictionaries.

        Uses the connection pool's cursor with dictionary=True to return
        results as list of dictionaries with column names as keys.

        Args:
            query: SQL SELECT query with parameter placeholders (%s)
            params: Tuple of parameters for query placeholders (default: None)

        Returns:
            List of dictionaries representing query results.
            Empty list if no results.

        Raises:
            DatabaseError: If query execution fails

        Example:
            >>> query = "SELECT * FROM users WHERE age > %s AND status = %s"
            >>> results = repo.execute_query(query, (18, 'active'))
            >>> for row in results:
            ...     print(f"{row['name']}: {row['email']}")
        """
        try:
            with self.pool.get_cursor() as cursor:
                cursor.execute(query, params or ())
                results = cursor.fetchall()

                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Query executed: {cursor.rowcount} rows returned")

                return results

        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            self.logger.debug(f"Query: {query}, Params: {params}")
            raise

    def execute_update(self, query: str, params: tuple | None = None) -> int:
        """
        Execute an UPDATE, INSERT, or DELETE query.

        Args:
            query: SQL UPDATE/INSERT/DELETE query with parameter placeholders
            params: Tuple of parameters for query placeholders (default: None)

        Returns:
            Number of affected rows

        Raises:
            DatabaseError: If query execution fails

        Example:
            >>> query = "UPDATE users SET status = %s WHERE age < %s"
            >>> affected = repo.execute_update(query, ('inactive', 18))
            >>> print(f"Updated {affected} users")
        """
        try:
            with self.pool.get_cursor() as cursor:
                cursor.execute(query, params or ())
                affected_rows = cursor.rowcount

                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Update executed: {affected_rows} rows affected")

                return affected_rows

        except Exception as e:
            self.logger.error(f"Update execution failed: {e}")
            self.logger.debug(f"Query: {query}, Params: {params}")
            raise

    def execute_scalar(self, query: str, params: tuple | None = None) -> Any | None:
        """
        Execute a query and return a single scalar value.

        Useful for COUNT, MAX, MIN, SUM queries or queries that return
        a single value.

        Args:
            query: SQL query returning single value
            params: Tuple of parameters for query placeholders (default: None)

        Returns:
            Single value from query result, or None if no results

        Example:
            >>> count = repo.execute_scalar("SELECT COUNT(*) FROM users")
            >>> print(f"Total users: {count}")
            >>>
            >>> max_age = repo.execute_scalar(
            ...     "SELECT MAX(age) FROM users WHERE status = %s",
            ...     ('active',)
            ... )
        """
        results = self.execute_query(query, params)
        if results and len(results) > 0:
            first_row = results[0]
            if first_row:
                # Return first column value
                return list(first_row.values())[0]
        return None

    def exists(self, query: str, params: tuple | None = None) -> bool:
        """
        Check if any rows match the query.

        Args:
            query: SQL query to check existence
            params: Tuple of parameters for query placeholders (default: None)

        Returns:
            True if at least one row matches, False otherwise

        Example:
            >>> user_exists = repo.exists(
            ...     "SELECT 1 FROM users WHERE email = %s",
            ...     ('john@example.com',)
            ... )
            >>> if user_exists:
            ...     print("Email already registered")
        """
        results = self.execute_query(query, params)
        return len(results) > 0

    # ========================================================================
    # Transaction Support
    # ========================================================================

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.

        Automatically commits on success or rolls back on exception.
        Uses the connection pool's connection with manual commit control.

        Yields:
            Database connection for manual operations if needed

        Example:
            >>> with repo.transaction():
            ...     repo.execute_update("UPDATE users SET status = 'active'")
            ...     repo.execute_update("UPDATE logs SET processed = true")
            ...     # Both updates committed together
            >>>
            >>> try:
            ...     with repo.transaction():
            ...         repo.execute_update("UPDATE accounts SET balance = balance - 100")
            ...         raise Exception("Simulated error")
            ...         repo.execute_update("UPDATE accounts SET balance = balance + 100")
            ... except:
            ...     pass  # Transaction rolled back automatically
        """
        with self.pool.get_connection() as connection:
            try:
                # Disable autocommit for transaction
                connection.autocommit = False
                yield connection
                connection.commit()

                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug("Transaction committed")

            except Exception as e:
                connection.rollback()
                self.logger.warning(f"Transaction rolled back: {e}")
                raise

            finally:
                # Restore autocommit
                connection.autocommit = True

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def count(self, table: str, where: str | None = None, params: tuple | None = None) -> int:
        """
        Count rows in a table with optional WHERE clause.

        Args:
            table: Table name
            where: Optional WHERE clause (without 'WHERE' keyword)
            params: Parameters for WHERE clause placeholders

        Returns:
            Number of rows matching criteria

        Example:
            >>> total = repo.count("users")
            >>> active = repo.count("users", "status = %s", ('active',))
            >>> print(f"{active}/{total} users are active")
        """
        query = f"SELECT COUNT(*) as count FROM {table}"
        if where:
            query += f" WHERE {where}"

        result = self.execute_scalar(query, params)
        return int(result) if result is not None else 0
