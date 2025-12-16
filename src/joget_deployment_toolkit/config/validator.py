#!/usr/bin/env python3
"""
Configuration validator for joget-toolkit.

Provides validation utilities for configuration objects including
connectivity tests, credential validation, and configuration consistency checks.
"""

from dataclasses import dataclass
from enum import Enum

import requests

from .models import AuthConfig, AuthType, ClientConfig, DatabaseConfig


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue."""

    severity: ValidationSeverity
    field: str
    message: str
    suggestion: str | None = None

    def __str__(self) -> str:
        """String representation of the issue."""
        result = f"[{self.severity.value.upper()}] {self.field}: {self.message}"
        if self.suggestion:
            result += f"\n  Suggestion: {self.suggestion}"
        return result


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    valid: bool
    issues: list[ValidationIssue]

    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)

    def get_errors(self) -> list[ValidationIssue]:
        """Get all error-level issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]

    def get_warnings(self) -> list[ValidationIssue]:
        """Get all warning-level issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]

    def __str__(self) -> str:
        """String representation of validation result."""
        if self.valid:
            return "Configuration is valid"

        lines = ["Configuration validation failed:"]
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


class ConfigurationValidator:
    """
    Validator for joget-toolkit configuration.

    Performs validation checks including:
    - Required fields presence
    - Value range validation
    - Connectivity tests
    - Credential validation
    - Configuration consistency
    """

    def __init__(self, test_connectivity: bool = False, timeout: int = 5):
        """
        Initialize validator.

        Args:
            test_connectivity: Test actual connectivity to services
            timeout: Timeout for connectivity tests (seconds)
        """
        self.test_connectivity = test_connectivity
        self.timeout = timeout

    def validate(self, config: ClientConfig) -> ValidationResult:
        """
        Validate complete configuration.

        Args:
            config: ClientConfig to validate

        Returns:
            ValidationResult with any issues found
        """
        issues: list[ValidationIssue] = []

        # Validate core settings
        issues.extend(self._validate_core_settings(config))

        # Validate authentication
        issues.extend(self._validate_auth(config.auth))

        # Validate retry configuration
        issues.extend(self._validate_retry(config))

        # Validate database if configured
        if config.database:
            issues.extend(self._validate_database(config.database))

        # Connectivity tests if requested
        if self.test_connectivity:
            issues.extend(self._test_connectivity(config))

        # Check for configuration conflicts
        issues.extend(self._check_conflicts(config))

        # Validation passes if there are no ERROR-level issues
        valid = not any(issue.severity == ValidationSeverity.ERROR for issue in issues)

        return ValidationResult(valid=valid, issues=issues)

    def _validate_core_settings(self, config: ClientConfig) -> list[ValidationIssue]:
        """Validate core configuration settings."""
        issues = []

        # URL validation
        if not config.base_url:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="base_url",
                    message="base_url is required",
                    suggestion="Provide a valid Joget instance URL (e.g., http://localhost:8080/jw)",
                )
            )
        elif not config.base_url.startswith(("http://", "https://")):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="base_url",
                    message=f"Invalid URL protocol: {config.base_url}",
                    suggestion="URL must start with http:// or https://",
                )
            )

        # Timeout validation
        if config.timeout < 1:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="timeout",
                    message=f"Very low timeout value: {config.timeout}s",
                    suggestion="Consider using timeout >= 5 seconds for reliable operations",
                )
            )
        elif config.timeout > 300:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="timeout",
                    message=f"Very high timeout value: {config.timeout}s",
                    suggestion="Consider reducing timeout to avoid long hangs",
                )
            )

        # SSL verification
        if not config.verify_ssl:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="verify_ssl",
                    message="SSL verification is disabled",
                    suggestion="Enable SSL verification for production use",
                )
            )

        return issues

    def _validate_auth(self, auth: AuthConfig) -> list[ValidationIssue]:
        """Validate authentication configuration."""
        issues = []

        if auth.type == AuthType.API_KEY:
            if not auth.api_key:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field="auth.api_key",
                        message="API key is required for API_KEY authentication",
                        suggestion="Provide a valid API key",
                    )
                )
            elif len(auth.api_key) < 10:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        field="auth.api_key",
                        message="API key seems unusually short",
                        suggestion="Verify that the API key is correct",
                    )
                )

        elif auth.type in (AuthType.SESSION, AuthType.BASIC):
            if not auth.username:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field="auth.username",
                        message=f"Username is required for {auth.type.value} authentication",
                    )
                )
            if not auth.password:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field="auth.password",
                        message=f"Password is required for {auth.type.value} authentication",
                    )
                )

        elif auth.type == AuthType.NONE:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    field="auth.type",
                    message="No authentication configured",
                    suggestion="Most Joget API endpoints require authentication",
                )
            )

        return issues

    def _validate_retry(self, config: ClientConfig) -> list[ValidationIssue]:
        """Validate retry configuration."""
        issues = []

        if config.retry.count > 10:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="retry.count",
                    message=f"High retry count: {config.retry.count}",
                    suggestion="Consider reducing retry count to avoid excessive delays",
                )
            )

        if config.retry.delay > 30:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="retry.delay",
                    message=f"Very long retry delay: {config.retry.delay}s",
                    suggestion="Consider reducing retry delay",
                )
            )

        # Check if retry delay with backoff could exceed reasonable time
        if config.retry.count > 0:
            total_delay = sum(
                config.retry.delay * (config.retry.backoff**i) for i in range(config.retry.count)
            )
            if total_delay > 300:  # 5 minutes
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        field="retry",
                        message=f"Total retry time could exceed {total_delay:.1f}s",
                        suggestion="Reduce retry count or delay to avoid long waits",
                    )
                )

        return issues

    def _validate_database(self, db_config: DatabaseConfig) -> list[ValidationIssue]:
        """Validate database configuration."""
        issues = []

        # Port validation
        if db_config.port < 1 or db_config.port > 65535:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="database.port",
                    message=f"Invalid port number: {db_config.port}",
                    suggestion="Port must be between 1 and 65535",
                )
            )

        # Pool size validation
        if db_config.pool_size < 1:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="database.pool_size",
                    message="Pool size must be at least 1",
                )
            )
        elif db_config.pool_size > 20:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="database.pool_size",
                    message=f"Large pool size: {db_config.pool_size}",
                    suggestion="Consider if you really need this many connections",
                )
            )

        # SSL certificate validation
        if db_config.ssl:
            if db_config.ssl_ca and not db_config.ssl_ca.exists():
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field="database.ssl_ca",
                        message=f"SSL CA file not found: {db_config.ssl_ca}",
                    )
                )
            if db_config.ssl_cert and not db_config.ssl_cert.exists():
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field="database.ssl_cert",
                        message=f"SSL certificate file not found: {db_config.ssl_cert}",
                    )
                )
            if db_config.ssl_key and not db_config.ssl_key.exists():
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        field="database.ssl_key",
                        message=f"SSL key file not found: {db_config.ssl_key}",
                    )
                )

        return issues

    def _test_connectivity(self, config: ClientConfig) -> list[ValidationIssue]:
        """Test actual connectivity to configured services."""
        issues = []

        # Test HTTP connectivity to Joget
        try:
            response = requests.get(
                config.base_url,
                timeout=self.timeout,
                verify=config.verify_ssl,
                allow_redirects=True,
            )
            if response.status_code >= 500:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        field="base_url",
                        message=f"Joget server returned error: {response.status_code}",
                        suggestion="Check if Joget instance is running properly",
                    )
                )
        except requests.exceptions.Timeout:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="base_url",
                    message=f"Connection timeout after {self.timeout}s",
                    suggestion="Check if Joget instance is accessible and increase timeout if needed",
                )
            )
        except requests.exceptions.SSLError as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="verify_ssl",
                    message=f"SSL verification failed: {str(e)}",
                    suggestion="Set verify_ssl=False for self-signed certificates (not recommended for production)",
                )
            )
        except requests.exceptions.ConnectionError as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="base_url",
                    message=f"Cannot connect to {config.base_url}: {str(e)}",
                    suggestion="Verify the URL and ensure the Joget instance is running",
                )
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="base_url",
                    message=f"Connectivity test failed: {str(e)}",
                )
            )

        # Test database connectivity if configured
        if config.database:
            issues.extend(self._test_database_connectivity(config.database))

        return issues

    def _test_database_connectivity(self, db_config: DatabaseConfig) -> list[ValidationIssue]:
        """Test database connectivity."""
        issues = []

        try:
            import mysql.connector
            from mysql.connector import Error as MySQLError

            connection = mysql.connector.connect(
                **db_config.to_connector_params(), connection_timeout=self.timeout
            )
            connection.close()
        except MySQLError as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="database",
                    message=f"Database connection failed: {str(e)}",
                    suggestion="Check database credentials and ensure MySQL is accessible",
                )
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="database",
                    message=f"Database connectivity test failed: {str(e)}",
                )
            )

        return issues

    def _check_conflicts(self, config: ClientConfig) -> list[ValidationIssue]:
        """Check for configuration conflicts or inconsistencies."""
        issues = []

        # Check if debug mode is on in production-like settings
        if config.debug and config.base_url.startswith("https://"):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    field="debug",
                    message="Debug mode enabled for HTTPS endpoint",
                    suggestion="Disable debug mode in production",
                )
            )

        # Check if SSL verification is disabled for HTTPS
        if not config.verify_ssl and config.base_url.startswith("https://"):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    field="verify_ssl",
                    message="SSL verification disabled for HTTPS connection",
                    suggestion="Enable SSL verification for secure connections",
                )
            )

        # Check if both database and no auth are configured
        if config.database and config.auth.type == AuthType.NONE:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    field="auth",
                    message="Database configured but no authentication provided",
                    suggestion="Database operations may require authentication",
                )
            )

        return issues


def validate_config(
    config: ClientConfig, test_connectivity: bool = False, raise_on_error: bool = False
) -> ValidationResult:
    """
    Convenience function to validate configuration.

    Args:
        config: Configuration to validate
        test_connectivity: Test actual connectivity
        raise_on_error: Raise exception if validation fails

    Returns:
        ValidationResult

    Raises:
        ValueError: If validation fails and raise_on_error=True
    """
    validator = ConfigurationValidator(test_connectivity=test_connectivity)
    result = validator.validate(config)

    if raise_on_error and not result.valid:
        raise ValueError(f"Configuration validation failed:\n{result}")

    return result


__all__ = [
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationResult",
    "ConfigurationValidator",
    "validate_config",
]
