"""
Database connection pool management.

Provides thread-safe connection pooling for MySQL database operations with:
- Singleton pattern for single pool instance
- Context managers for automatic cleanup
- SSL support
- Connection health checks
- Pool statistics
"""

import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

import mysql.connector.pooling
from mysql.connector import Error as MySQLError

from ..models import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """
    Thread-safe database connection pool using singleton pattern.

    Ensures only one connection pool exists per application, reducing
    resource usage and improving performance.

    Example:
        >>> from joget_deployment_toolkit.config import DatabaseConfig
        >>> config = DatabaseConfig(host="localhost", user="root", password="pass", database="jwdb")
        >>> pool = DatabaseConnectionPool(config)
        >>> with pool.get_cursor() as cursor:
        ...     cursor.execute("SELECT * FROM app_fd_form")
        ...     results = cursor.fetchall()
    """

    _instance: Optional["DatabaseConnectionPool"] = None
    _lock = threading.Lock()

    def __new__(cls, config: DatabaseConfig | None = None):
        """
        Ensure single instance (singleton pattern).

        Args:
            config: Database configuration (required for first call)

        Returns:
            Singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: DatabaseConfig | None = None):
        """
        Initialize connection pool.

        Args:
            config: Database configuration (required for first initialization)

        Raises:
            ValueError: If config not provided on first initialization
            MySQLError: If connection pool creation fails
        """
        if not hasattr(self, "_initialized"):
            if config is None:
                raise ValueError("DatabaseConfig required for first initialization")

            self._config = config
            self._connection_count = 0
            self._error_count = 0
            self._created_at = datetime.now()

            # Prepare connection parameters
            pool_params = {
                "pool_name": config.pool_name,
                "pool_size": config.pool_size,
                "pool_reset_session": config.pool_reset_session,
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "user": config.user,
                "password": config.password,
                "autocommit": config.autocommit,
                "use_unicode": config.use_unicode,
                "charset": config.charset,
                "collation": config.collation,
                "connection_timeout": config.connection_timeout,
            }

            # Add SSL configuration if enabled
            if config.ssl:
                ssl_params = {}
                if config.ssl_ca:
                    ssl_params["ca"] = str(config.ssl_ca)
                if config.ssl_cert:
                    ssl_params["cert"] = str(config.ssl_cert)
                if config.ssl_key:
                    ssl_params["key"] = str(config.ssl_key)

                if ssl_params:
                    pool_params["ssl_disabled"] = False
                    # Note: mysql-connector-python handles SSL params differently in pooling

            try:
                self._pool = mysql.connector.pooling.MySQLConnectionPool(**pool_params)
                self._initialized = True
                logger.info(
                    f"Database connection pool initialized: {config.pool_name} (size: {config.pool_size})"
                )
            except MySQLError as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool with automatic cleanup.

        Yields:
            mysql.connector.connection.MySQLConnection: Database connection

        Raises:
            MySQLError: If connection cannot be obtained
        """
        connection = None
        try:
            connection = self._pool.get_connection()
            self._connection_count += 1
            yield connection
        except MySQLError as e:
            self._error_count += 1
            logger.error(f"Database error: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()

    @contextmanager
    def get_cursor(self, dictionary: bool = True, buffered: bool = True):
        """
        Get a cursor with automatic connection and cursor management.

        Args:
            dictionary: Return rows as dictionaries (default: True)
            buffered: Use buffered cursor (default: True)

        Yields:
            mysql.connector.cursor.MySQLCursor: Database cursor

        Raises:
            MySQLError: If cursor cannot be created
        """
        with self.get_connection() as connection:
            cursor = connection.cursor(dictionary=dictionary, buffered=buffered)
            try:
                yield cursor
            except MySQLError as e:
                logger.error(f"Cursor error: {e}")
                raise
            finally:
                cursor.close()

    def test_connection(self) -> bool:
        """
        Test if the connection pool can establish a connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                if conn.is_connected():
                    return True
        except MySQLError as e:
            logger.error(f"Connection test failed: {e}")
            return False
        return False

    def get_pool_stats(self) -> dict[str, Any]:
        """
        Get connection pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        return {
            "pool_name": self._config.pool_name,
            "pool_size": self._config.pool_size,
            "connection_count": self._connection_count,
            "error_count": self._error_count,
            "created_at": self._created_at.isoformat(),
            "uptime_seconds": (datetime.now() - self._created_at).total_seconds(),
            "host": self._config.host,
            "port": self._config.port,
            "database": self._config.database,
        }

    def reset_stats(self):
        """Reset connection statistics."""
        self._connection_count = 0
        self._error_count = 0
        logger.info(f"Pool statistics reset: {self._config.pool_name}")

    @classmethod
    def reset_instance(cls):
        """
        Reset singleton instance (useful for testing).

        Warning:
            This will close the existing pool and reset the singleton.
            Only use this in testing scenarios.
        """
        with cls._lock:
            if cls._instance is not None:
                logger.warning("Resetting database connection pool instance")
                cls._instance = None

    def __repr__(self) -> str:
        """String representation of the pool."""
        return (
            f"DatabaseConnectionPool(pool_name={self._config.pool_name}, "
            f"pool_size={self._config.pool_size}, "
            f"connections={self._connection_count})"
        )


__all__ = ["DatabaseConnectionPool"]
