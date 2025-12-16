"""
Base client with core HTTP operations and session management.

Provides the foundation for all Joget API operations including:
- Session management with connection pooling
- Authentication integration
- HTTP request execution via HTTPClient
- Alternative constructors for backward compatibility
"""

import logging

import requests
from requests.adapters import HTTPAdapter

from ..auth import APIKeyAuth, AuthStrategy, select_auth_strategy
from ..config import ClientConfig
from ..exceptions import AuthenticationError
from .http_client import HTTPClient

logger = logging.getLogger(__name__)


class BaseClient:
    """
    Base client with core HTTP operations and session management.

    Provides fundamental client functionality that all operation mixins
    can use. Handles session management, authentication, and HTTP requests.
    """

    def __init__(self, config: ClientConfig, auth_strategy: AuthStrategy | None = None):
        """
        Initialize base client.

        Args:
            config: ClientConfig instance
            auth_strategy: Authentication strategy (optional)

        Raises:
            TypeError: If config is not a ClientConfig instance
            ValueError: If configuration is invalid
            AuthenticationError: If authentication setup fails
        """
        if not isinstance(config, ClientConfig):
            raise TypeError("config must be a ClientConfig instance")

        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.logger = logging.getLogger(__name__)

        # Setup authentication strategy
        if auth_strategy:
            self.auth_strategy = auth_strategy
        else:
            # Create auth strategy from config
            self.auth_strategy = self._create_auth_strategy()

        # Create HTTP client for requests
        self.http_client = HTTPClient(config)

        # Create session with connection pooling
        self.session = self._create_session()

        # Perform initial authentication if needed
        if hasattr(self.auth_strategy, "authenticate"):
            try:
                self.auth_strategy.authenticate(self.session)
            except Exception as e:
                raise AuthenticationError(f"Initial authentication failed: {e}")

        if self.config.debug:
            self.logger.debug(f"Initialized client: {self.base_url}")
            self.logger.debug(f"Auth strategy: {self.auth_strategy.__class__.__name__}")

    def _create_auth_strategy(self) -> AuthStrategy:
        """
        Create authentication strategy from configuration.

        Returns:
            AuthStrategy instance
        """
        auth_config = self.config.auth

        return select_auth_strategy(
            api_key=auth_config.api_key,
            username=auth_config.username,
            password=auth_config.password,
            base_url=self.base_url,
        )

    def _create_session(self) -> requests.Session:
        """
        Create configured session with connection pooling.

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=self.config.connection_pool.pool_connections,
            pool_maxsize=self.config.connection_pool.pool_maxsize,
            max_retries=0,  # We handle retries in HTTPClient
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set SSL verification
        session.verify = self.config.verify_ssl

        # Set default headers
        session.headers.update(
            {
                "User-Agent": self.config.user_agent,
                "Accept": "application/json",
                **self.config.extra_headers,
            }
        )

        return session

    def _get_headers(
        self, api_id: str | None = None, api_key: str | None = None
    ) -> dict[str, str]:
        """
        Get request headers with authentication.

        Args:
            api_id: API ID for specific endpoint (for API-based endpoints like FormCreator)
            api_key: API key for specific endpoint (for API-based endpoints like FormCreator)

        Returns:
            Dictionary of headers
        """
        # Get headers from auth strategy
        if isinstance(self.auth_strategy, APIKeyAuth):
            headers = self.auth_strategy.get_headers(api_id=api_id or api_key)
        else:
            headers = self.auth_strategy.get_headers()

        # Add api_id and api_key headers for plugin API endpoints (e.g., FormCreator)
        # These are separate from the main authentication strategy
        if api_id:
            headers["api_id"] = api_id
        if api_key:
            headers["api_key"] = api_key

        # Ensure standard headers
        headers.setdefault("Accept", "application/json")
        # Don't set Content-Type here - let requests library handle it based on data type
        # (JSON for json=, form-encoded for data=)

        return headers

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Execute HTTP request with authentication and retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional request parameters

        Returns:
            requests.Response object

        Raises:
            JogetAPIError: On request failure
        """
        # Construct full URL
        url = f"{self.base_url}{endpoint}"

        # Merge authentication headers
        headers = kwargs.pop("headers", {})
        api_id = kwargs.pop("api_id", None)
        api_key = kwargs.pop("api_key", None)
        auth_headers = self._get_headers(api_id=api_id, api_key=api_key)
        headers = {**auth_headers, **headers}

        # IMPORTANT: When sending files, remove Content-Type header
        # Let requests library set it automatically to multipart/form-data with boundary
        if "files" in kwargs and "Content-Type" in headers:
            del headers["Content-Type"]

        # Add cookies from session if using session auth
        # BUT skip session cookies when calling plugin API endpoints (indicated by api_id)
        # because plugin APIs use their own authentication (api_id/api_key headers)
        if hasattr(self.auth_strategy, "session") and not api_id:
            kwargs["cookies"] = self.session.cookies

        # Execute request via HTTP client
        return self.http_client.request(method, url, headers=headers, **kwargs)

    # Convenience methods
    def get(self, endpoint: str, **kwargs) -> dict:
        """Execute GET request and return JSON response."""
        response = self.request("GET", endpoint, **kwargs)
        return response.json()

    def post(self, endpoint: str, **kwargs) -> dict:
        """Execute POST request and return JSON response."""
        response = self.request("POST", endpoint, **kwargs)
        return response.json()

    def put(self, endpoint: str, **kwargs) -> dict:
        """Execute PUT request and return JSON response."""
        response = self.request("PUT", endpoint, **kwargs)
        return response.json()

    def delete(self, endpoint: str, **kwargs) -> dict:
        """Execute DELETE request and return JSON response."""
        response = self.request("DELETE", endpoint, **kwargs)
        return response.json()

    def close(self):
        """Close the session and cleanup resources."""
        if self.session:
            self.session.close()
            if self.config.debug:
                self.logger.debug("Session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(base_url={self.base_url})"


__all__ = ["BaseClient"]
