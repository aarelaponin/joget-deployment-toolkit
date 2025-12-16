"""
Authentication Strategies for Joget API Client

Provides pluggable authentication mechanisms supporting:
- API Key authentication (header-based)
- Session-based authentication (username/password with cookies)
- HTTP Basic authentication

Usage:
    from joget_deployment_toolkit.auth import APIKeyAuth, SessionAuth, BasicAuth

    # API Key (recommended for API endpoints)
    auth = APIKeyAuth("your-api-key")

    # Session-based (for console API)
    auth = SessionAuth("http://localhost:8080/jw", "admin", "admin")

    # HTTP Basic Auth
    auth = BasicAuth("admin", "admin")
"""

import base64
import logging
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger(__name__)


class AuthStrategy(ABC):
    """
    Base class for authentication strategies.

    All authentication strategies must implement:
    - authenticate(): Perform initial authentication (if needed)
    - get_headers(): Return headers to include in requests
    - prepare_request(): Modify request before sending (optional)
    """

    @abstractmethod
    def authenticate(self, session: requests.Session) -> bool:
        """
        Perform authentication.

        Called once when client is initialized or when authentication
        needs to be refreshed.

        Args:
            session: requests.Session to authenticate with

        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    def get_headers(self) -> dict[str, str]:
        """
        Get headers to include in all requests.

        Returns:
            Dictionary of header name -> value
        """
        pass

    def prepare_request(self, request: requests.PreparedRequest) -> None:
        """
        Modify request before sending (optional).

        Can be overridden to add authentication details directly to
        the request object.

        Args:
            request: PreparedRequest to modify
        """
        pass

    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return True  # Default: always authenticated


class APIKeyAuth(AuthStrategy):
    """
    API key authentication (header-based).

    This is the recommended authentication method for Joget API endpoints
    that support the formCreator plugin or other API-based operations.

    The API key is sent in request headers:
        api_id: <api_id>
        api_key: <api_key>

    Usage:
        auth = APIKeyAuth(api_key="your-api-key")
        # Or with custom API ID per request:
        auth = APIKeyAuth(api_key="your-api-key", default_api_id="fc_api")

    Example:
        from joget_deployment_toolkit.client import JogetClient
        from joget_deployment_toolkit.auth import APIKeyAuth

        auth = APIKeyAuth("your-api-key")
        client = JogetClient(
            "http://localhost:8080/jw",
            auth_strategy=auth
        )
    """

    def __init__(self, api_key: str, default_api_id: str | None = None):
        """
        Initialize API key authentication.

        Args:
            api_key: API key for authentication
            default_api_id: Default API ID to use (can be overridden per request)
        """
        self.api_key = api_key
        self.default_api_id = default_api_id
        logger.debug("Initialized API key authentication")

    def authenticate(self, session: requests.Session) -> bool:
        """
        No upfront authentication needed for API key.

        Args:
            session: requests.Session (unused)

        Returns:
            Always returns True
        """
        return True

    def get_headers(self, api_id: str | None = None) -> dict[str, str]:
        """
        Get headers with API authentication.

        Args:
            api_id: API ID to use (overrides default_api_id)

        Returns:
            Headers dictionary with api_id and api_key
        """
        headers = {"Content-Type": "application/json", "api_key": self.api_key}

        # Include api_id if provided or if default is set
        if api_id or self.default_api_id:
            headers["api_id"] = api_id or self.default_api_id

        return headers


class SessionAuth(AuthStrategy):
    """
    Session-based authentication (username/password with cookies).

    This authentication method:
    1. Performs a login request to establish a session
    2. Stores session cookies
    3. Uses cookies for subsequent requests

    Required for Joget Console API endpoints that don't support API keys.

    Usage:
        auth = SessionAuth(
            base_url="http://localhost:8080/jw",
            username="admin",
            password="admin"
        )

    Example:
        from joget_deployment_toolkit.client import JogetClient
        from joget_deployment_toolkit.auth import SessionAuth

        auth = SessionAuth("http://localhost:8080/jw", "admin", "admin")
        client = JogetClient(
            "http://localhost:8080/jw",
            auth_strategy=auth
        )
    """

    def __init__(self, base_url: str, username: str, password: str):
        """
        Initialize session-based authentication.

        Args:
            base_url: Joget instance base URL
            username: Username for authentication
            password: Password for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._authenticated = False
        logger.debug(f"Initialized session authentication for user: {username}")

    def authenticate(self, session: requests.Session) -> bool:
        """
        Authenticate and establish session.

        Performs login via Joget's Spring Security endpoint and stores
        session cookies for subsequent requests.

        Args:
            session: requests.Session to authenticate

        Returns:
            True if login successful, False otherwise

        Raises:
            requests.RequestException: If login request fails
        """
        login_url = f"{self.base_url}/j_spring_security_check"

        logger.debug(f"Authenticating user {self.username} at {login_url}")

        try:
            response = session.post(
                login_url,
                data={"j_username": self.username, "j_password": self.password},
                allow_redirects=True,
            )

            # Check if login was successful
            # Joget redirects to error page on failed login
            if response.status_code == 200 and "login" not in response.url.lower():
                self._authenticated = True
                logger.info(f"Successfully authenticated user: {self.username}")
                return True
            else:
                self._authenticated = False
                logger.warning(f"Authentication failed for user: {self.username}")
                return False

        except requests.RequestException as e:
            logger.error(f"Authentication request failed: {e}")
            self._authenticated = False
            raise

    def get_headers(self) -> dict[str, str]:
        """
        Get headers for session-based auth.

        Session authentication relies on cookies, so no special headers
        are needed beyond standard content type.

        Returns:
            Standard headers dictionary
        """
        return {"Content-Type": "application/json"}

    def is_authenticated(self) -> bool:
        """
        Check if session is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self._authenticated


class BasicAuth(AuthStrategy):
    """
    HTTP Basic authentication.

    Sends username and password in the Authorization header using
    Base64 encoding:
        Authorization: Basic <base64(username:password)>

    Supported by most Joget endpoints as an alternative to API keys.

    Usage:
        auth = BasicAuth(username="admin", password="admin")

    Example:
        from joget_deployment_toolkit.client import JogetClient
        from joget_deployment_toolkit.auth import BasicAuth

        auth = BasicAuth("admin", "admin")
        client = JogetClient(
            "http://localhost:8080/jw",
            auth_strategy=auth
        )
    """

    def __init__(self, username: str, password: str):
        """
        Initialize HTTP Basic authentication.

        Args:
            username: Username for authentication
            password: Password for authentication
        """
        self.username = username
        self.password = password
        self._auth_header = self._generate_auth_header()
        logger.debug(f"Initialized Basic Auth for user: {username}")

    def _generate_auth_header(self) -> str:
        """
        Generate Base64-encoded authorization header value.

        Returns:
            "Basic <base64(username:password)>" string
        """
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def authenticate(self, session: requests.Session) -> bool:
        """
        No upfront authentication needed for Basic Auth.

        Credentials are sent with each request.

        Args:
            session: requests.Session (unused)

        Returns:
            Always returns True
        """
        return True

    def get_headers(self) -> dict[str, str]:
        """
        Get headers with Basic Auth.

        Returns:
            Headers dictionary with Authorization header
        """
        return {"Content-Type": "application/json", "Authorization": self._auth_header}


class NoAuth(AuthStrategy):
    """
    No authentication (for public endpoints).

    Use this when accessing public Joget endpoints that don't
    require authentication.

    Usage:
        auth = NoAuth()

    Example:
        from joget_deployment_toolkit.client import JogetClient
        from joget_deployment_toolkit.auth import NoAuth

        auth = NoAuth()
        client = JogetClient(
            "http://localhost:8080/jw",
            auth_strategy=auth
        )
    """

    def authenticate(self, session: requests.Session) -> bool:
        """
        No authentication needed.

        Args:
            session: requests.Session (unused)

        Returns:
            Always returns True
        """
        return True

    def get_headers(self) -> dict[str, str]:
        """
        Get standard headers without authentication.

        Returns:
            Basic headers dictionary
        """
        return {"Content-Type": "application/json"}


def select_auth_strategy(
    *,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
    base_url: str | None = None,
    auth_strategy: AuthStrategy | None = None,
) -> AuthStrategy:
    """
    Automatically select authentication strategy based on provided credentials.

    Priority:
        1. Explicit auth_strategy parameter
        2. API key (if provided)
        3. Username + password -> Session auth (if base_url provided)
        4. Username + password -> Basic auth (if no base_url)
        5. Raise error if no credentials provided

    Args:
        api_key: API key for APIKeyAuth
        username: Username for SessionAuth or BasicAuth
        password: Password for SessionAuth or BasicAuth
        base_url: Base URL for SessionAuth
        auth_strategy: Explicit auth strategy

    Returns:
        Selected AuthStrategy instance

    Raises:
        ValueError: If no valid authentication credentials provided

    Example:
        # Auto-select API key auth
        auth = select_auth_strategy(api_key="key123")

        # Auto-select session auth
        auth = select_auth_strategy(
            username="admin",
            password="admin",
            base_url="http://localhost:8080/jw"
        )

        # Auto-select basic auth (no base_url)
        auth = select_auth_strategy(username="admin", password="admin")
    """
    # Use explicit strategy if provided
    if auth_strategy:
        logger.debug(f"Using explicit auth strategy: {auth_strategy.__class__.__name__}")
        return auth_strategy

    # API key authentication (preferred)
    if api_key:
        logger.debug("Auto-selected API key authentication")
        return APIKeyAuth(api_key)

    # Username/password authentication
    if username and password:
        if base_url:
            # Session-based auth (for console API)
            logger.debug("Auto-selected session authentication")
            return SessionAuth(base_url, username, password)
        else:
            # Basic auth (for API endpoints)
            logger.debug("Auto-selected Basic authentication")
            return BasicAuth(username, password)

    # No authentication credentials provided
    raise ValueError(
        "Must provide authentication credentials: "
        "api_key, or username+password, or auth_strategy"
    )


__all__ = [
    "AuthStrategy",
    "APIKeyAuth",
    "SessionAuth",
    "BasicAuth",
    "NoAuth",
    "select_auth_strategy",
]
