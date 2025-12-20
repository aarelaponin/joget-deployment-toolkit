"""
Joget API Exception Hierarchy

Provides specific exception types for different API error conditions,
enabling better error handling and debugging.

Usage:
    from joget_deployment_toolkit.exceptions import JogetAPIError, NotFoundError

    try:
        client.get_form("app1", "form123")
    except NotFoundError:
        print("Form not found")
    except JogetAPIError as e:
        print(f"API error: {e.message}, status: {e.status_code}")
"""


import requests


class JogetAPIError(Exception):
    """
    Base exception for all Joget API errors.

    All Joget-specific exceptions inherit from this class, allowing
    catch-all error handling when needed.

    Attributes:
        message: Human-readable error description
        status_code: HTTP status code (if applicable)
        response: Original requests.Response object (if applicable)
        endpoint: API endpoint that failed (if applicable)
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response: requests.Response | None = None,
        endpoint: str | None = None,
    ):
        """
        Initialize Joget API error.

        Args:
            message: Error description
            status_code: HTTP status code (optional)
            response: Original response object (optional)
            endpoint: API endpoint (optional)
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        self.endpoint = endpoint
        super().__init__(message)

    def __str__(self):
        """String representation with status code and endpoint if available."""
        # Ensure message is a string (could be dict from JSON response)
        msg = str(self.message) if not isinstance(self.message, str) else self.message
        parts = [msg]
        if self.status_code:
            parts.append(f"(status {self.status_code})")
        if self.endpoint:
            parts.append(f"at {self.endpoint}")
        return " ".join(parts)

    def __repr__(self):
        """Detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code}, "
            f"endpoint={self.endpoint!r})"
        )


class ConnectionError(JogetAPIError):
    """
    Cannot connect to Joget instance.

    Raised when the client cannot establish a connection to the Joget
    server, typically due to network issues, wrong URL, or server being down.

    Example:
        try:
            client.test_connection()
        except ConnectionError:
            print("Cannot reach Joget server")
    """

    pass


class AuthenticationError(JogetAPIError):
    """
    Authentication failed.

    Raised when authentication credentials are invalid or expired.
    This includes:
    - Invalid API key (401)
    - Invalid username/password (401)
    - Expired session (401)
    - Insufficient permissions (403)

    Example:
        try:
            client = JogetClient(base_url, api_key="wrong-key")
            client.list_applications()
        except AuthenticationError:
            print("Invalid credentials")
    """

    pass


class NotFoundError(JogetAPIError):
    """
    Resource not found (HTTP 404).

    Raised when attempting to access a resource that doesn't exist:
    - Non-existent application
    - Non-existent form
    - Non-existent plugin
    - Invalid endpoint

    Example:
        try:
            form = client.get_form("app1", "nonexistent_form")
        except NotFoundError:
            print("Form does not exist")
    """

    pass


class ValidationError(JogetAPIError):
    """
    Request validation failed (HTTP 400).

    Raised when the request is malformed or contains invalid data:
    - Invalid JSON structure
    - Missing required fields
    - Invalid field values
    - Schema validation failures

    Example:
        try:
            client.create_form("app1", {})  # Missing required fields
        except ValidationError as e:
            print(f"Invalid form definition: {e.message}")
    """

    pass


class ConflictError(JogetAPIError):
    """
    Resource conflict (HTTP 409).

    Raised when attempting to create a resource that already exists
    or when the request conflicts with the current state:
    - Creating form with duplicate ID
    - Importing application that already exists (without overwrite flag)
    - Version conflicts

    Example:
        try:
            client.import_application("app.zip", overwrite=False)
        except ConflictError:
            print("Application already exists")
    """

    pass


class ServerError(JogetAPIError):
    """
    Server error (HTTP 5xx).

    Raised when the Joget server encounters an internal error:
    - Internal server error (500)
    - Bad gateway (502)
    - Service unavailable (503)
    - Gateway timeout (504)

    These errors typically indicate server-side issues that may be
    transient and could succeed on retry.

    Example:
        try:
            client.export_application("app1", "output.zip")
        except ServerError:
            print("Server error, try again later")
    """

    pass


class TimeoutError(JogetAPIError):
    """
    Request timed out.

    Raised when a request exceeds the configured timeout period.
    This can occur with:
    - Slow network connections
    - Large file uploads/downloads
    - Complex operations taking too long

    Example:
        try:
            client = JogetClient(base_url, timeout=5)
            client.export_application("large_app", "output.zip")
        except TimeoutError:
            print("Operation timed out, increase timeout or try again")
    """

    pass


class BatchError(JogetAPIError):
    """
    Error during batch operation.

    Raised when a batch operation fails. Contains details about
    which records succeeded and which failed.

    Attributes:
        total: Total number of records in batch
        successful: Number of successful operations
        failed: Number of failed operations
        errors: List of error details for failed operations

    Example:
        try:
            result = client.batch_post("/endpoint", records)
        except BatchError as e:
            print(f"Batch completed {e.successful}/{e.total}")
            for error in e.errors:
                print(f"  Failed: {error}")
    """

    def __init__(
        self,
        message: str,
        *,
        total: int = 0,
        successful: int = 0,
        failed: int = 0,
        errors: list | None = None,
        **kwargs,
    ):
        """
        Initialize batch error.

        Args:
            message: Error description
            total: Total records in batch
            successful: Number of successful operations
            failed: Number of failed operations
            errors: List of error details
            **kwargs: Additional JogetAPIError arguments
        """
        super().__init__(message, **kwargs)
        self.total = total
        self.successful = successful
        self.failed = failed
        self.errors = errors or []

    def __str__(self):
        """String representation with batch statistics."""
        return (
            f"{self.message} "
            f"({self.successful}/{self.total} successful, "
            f"{self.failed} failed)"
        )


def map_http_error(response: requests.Response, endpoint: str | None = None) -> JogetAPIError:
    """
    Map HTTP response to appropriate exception.

    Examines the HTTP status code and response body to determine
    the most specific exception type to raise.

    Args:
        response: requests.Response object
        endpoint: API endpoint (optional, for error message)

    Returns:
        Appropriate JogetAPIError subclass instance

    Example:
        response = requests.get(url)
        if response.status_code != 200:
            raise map_http_error(response, "/api/endpoint")
    """
    status = response.status_code
    message = f"Request failed with status {status}"

    # Try to extract error message from response
    try:
        data = response.json()
        if "error" in data:
            message = data["error"]
        elif "message" in data:
            message = data["message"]
        elif "errorMessage" in data:
            message = data["errorMessage"]
    except Exception:
        # If JSON parsing fails, try to get text
        try:
            text = response.text
            if text and len(text) < 200:  # Only include short error messages
                message = text
        except Exception:
            pass

    # Map status codes to exception classes
    error_map = {
        400: ValidationError,
        401: AuthenticationError,
        403: AuthenticationError,
        404: NotFoundError,
        409: ConflictError,
        500: ServerError,
        502: ServerError,
        503: ServerError,
        504: TimeoutError,
    }

    error_class = error_map.get(status, JogetAPIError)
    return error_class(message, status_code=status, response=response, endpoint=endpoint)


__all__ = [
    "JogetAPIError",
    "ConnectionError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "ServerError",
    "TimeoutError",
    "BatchError",
    "map_http_error",
]
