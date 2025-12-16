"""
Tests for joget_deployment_toolkit.exceptions module.
"""

from unittest.mock import Mock

from joget_deployment_toolkit.exceptions import (
    AuthenticationError,
    BatchError,
    ConflictError,
    ConnectionError,
    JogetAPIError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
    map_http_error,
)


class TestJogetAPIError:
    """Test base JogetAPIError exception."""

    def test_init_with_message_only(self):
        """Test creating error with just message."""
        error = JogetAPIError("Test error")
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.response is None
        assert error.endpoint is None

    def test_init_with_all_params(self, mock_response):
        """Test creating error with all parameters."""
        response = mock_response(404, text="Not found")
        error = JogetAPIError(
            "Resource not found", status_code=404, response=response, endpoint="/api/test"
        )

        assert error.message == "Resource not found"
        assert error.status_code == 404
        assert error.response == response
        assert error.endpoint == "/api/test"

    def test_str_representation(self):
        """Test string representation."""
        error = JogetAPIError("Test error", status_code=500, endpoint="/api/test")
        result = str(error)

        assert "Test error" in result
        assert "500" in result
        assert "/api/test" in result

    def test_repr_representation(self):
        """Test repr representation."""
        error = JogetAPIError("Test error", status_code=404)
        result = repr(error)

        assert "JogetAPIError" in result
        assert "Test error" in result
        assert "404" in result


class TestSpecificExceptions:
    """Test specific exception types."""

    def test_connection_error(self):
        """Test ConnectionError is subclass of JogetAPIError."""
        error = ConnectionError("Cannot connect")
        assert isinstance(error, JogetAPIError)
        assert error.message == "Cannot connect"

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid credentials")
        assert isinstance(error, JogetAPIError)
        assert error.message == "Invalid credentials"

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Resource not found")
        assert isinstance(error, JogetAPIError)
        assert error.message == "Resource not found"

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid data")
        assert isinstance(error, JogetAPIError)
        assert error.message == "Invalid data"

    def test_conflict_error(self):
        """Test ConflictError."""
        error = ConflictError("Resource already exists")
        assert isinstance(error, JogetAPIError)
        assert error.message == "Resource already exists"

    def test_server_error(self):
        """Test ServerError."""
        error = ServerError("Internal server error")
        assert isinstance(error, JogetAPIError)
        assert error.message == "Internal server error"

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Request timed out")
        assert isinstance(error, JogetAPIError)
        assert error.message == "Request timed out"


class TestBatchError:
    """Test BatchError with statistics."""

    def test_init_with_stats(self):
        """Test creating BatchError with statistics."""
        errors = [{"index": 0, "error": "Failed"}]
        error = BatchError("Batch failed", total=10, successful=8, failed=2, errors=errors)

        assert error.message == "Batch failed"
        assert error.total == 10
        assert error.successful == 8
        assert error.failed == 2
        assert error.errors == errors

    def test_str_with_stats(self):
        """Test string representation includes statistics."""
        error = BatchError("Batch failed", total=10, successful=8, failed=2)
        result = str(error)

        assert "Batch failed" in result
        assert "8/10" in result
        assert "2 failed" in result


class TestMapHttpError:
    """Test map_http_error function."""

    def test_map_400_to_validation_error(self, mock_response):
        """Test 400 maps to ValidationError."""
        response = mock_response(400, text="Bad request")
        error = map_http_error(response, "/api/test")

        assert isinstance(error, ValidationError)
        assert error.status_code == 400
        assert error.endpoint == "/api/test"

    def test_map_401_to_authentication_error(self, mock_response):
        """Test 401 maps to AuthenticationError."""
        response = mock_response(401, text="Unauthorized")
        error = map_http_error(response)

        assert isinstance(error, AuthenticationError)
        assert error.status_code == 401

    def test_map_403_to_authentication_error(self, mock_response):
        """Test 403 maps to AuthenticationError."""
        response = mock_response(403, text="Forbidden")
        error = map_http_error(response)

        assert isinstance(error, AuthenticationError)
        assert error.status_code == 403

    def test_map_404_to_not_found_error(self, mock_response):
        """Test 404 maps to NotFoundError."""
        response = mock_response(404, text="Not found")
        error = map_http_error(response)

        assert isinstance(error, NotFoundError)
        assert error.status_code == 404

    def test_map_409_to_conflict_error(self, mock_response):
        """Test 409 maps to ConflictError."""
        response = mock_response(409, text="Conflict")
        error = map_http_error(response)

        assert isinstance(error, ConflictError)
        assert error.status_code == 409

    def test_map_500_to_server_error(self, mock_response):
        """Test 500 maps to ServerError."""
        response = mock_response(500, text="Internal server error")
        error = map_http_error(response)

        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_map_502_to_server_error(self, mock_response):
        """Test 502 maps to ServerError."""
        response = mock_response(502, text="Bad gateway")
        error = map_http_error(response)

        assert isinstance(error, ServerError)
        assert error.status_code == 502

    def test_map_503_to_server_error(self, mock_response):
        """Test 503 maps to ServerError."""
        response = mock_response(503, text="Service unavailable")
        error = map_http_error(response)

        assert isinstance(error, ServerError)
        assert error.status_code == 503

    def test_map_504_to_timeout_error(self, mock_response):
        """Test 504 maps to TimeoutError."""
        response = mock_response(504, text="Gateway timeout")
        error = map_http_error(response)

        assert isinstance(error, TimeoutError)
        assert error.status_code == 504

    def test_map_unknown_code_to_generic_error(self, mock_response):
        """Test unknown status code maps to generic JogetAPIError."""
        response = mock_response(418, text="I'm a teapot")
        error = map_http_error(response)

        assert isinstance(error, JogetAPIError)
        assert error.status_code == 418

    def test_extract_error_from_json(self, mock_response):
        """Test extracting error message from JSON response."""
        response = mock_response(400, json_data={"error": "Invalid field value"})
        error = map_http_error(response)

        assert "Invalid field value" in str(error)

    def test_extract_message_from_json(self, mock_response):
        """Test extracting message from JSON response."""
        response = mock_response(400, json_data={"message": "Validation failed"})
        error = map_http_error(response)

        assert "Validation failed" in str(error)

    def test_extract_error_message_from_json(self, mock_response):
        """Test extracting errorMessage from JSON response."""
        response = mock_response(400, json_data={"errorMessage": "Something wrong"})
        error = map_http_error(response)

        assert "Something wrong" in str(error)

    def test_fallback_to_text_if_no_json(self, mock_response):
        """Test falling back to text if JSON parsing fails."""
        response = mock_response(400, text="Plain text error")
        response.json = Mock(side_effect=ValueError("No JSON"))
        error = map_http_error(response)

        assert "Plain text error" in str(error) or "400" in str(error)
