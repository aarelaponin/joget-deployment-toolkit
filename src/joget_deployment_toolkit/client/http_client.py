#!/usr/bin/env python3
"""
HTTP client with retry logic for Joget API.

Provides low-level HTTP operations with:
- Exponential backoff retry
- Error mapping and handling
- Request/response logging
- Timeout management
"""

import logging
import time

import requests
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import (
    RequestException,
)
from requests.exceptions import (
    Timeout as RequestsTimeout,
)

from ..config import ClientConfig, RetryStrategy
from ..exceptions import ConnectionError, JogetAPIError, TimeoutError, map_http_error

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    Low-level HTTP client with retry logic.

    Handles HTTP operations with automatic retry, exponential backoff,
    and comprehensive error handling.
    """

    def __init__(self, config: ClientConfig):
        """
        Initialize HTTP client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.logger = logger

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Execute HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Full URL to request
            **kwargs: Additional arguments for requests.request()

        Returns:
            requests.Response object

        Raises:
            JogetAPIError: On request failure after retries
            ConnectionError: On connection errors
            TimeoutError: On timeout errors
        """
        # Set default timeout from config if not provided
        kwargs.setdefault("timeout", self.config.timeout)
        kwargs.setdefault("verify", self.config.verify_ssl)

        if self.config.retry.enabled:
            return self._request_with_retry(method, url, **kwargs)
        else:
            return self._execute_request(method, url, **kwargs)

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Execute request with retry logic and exponential backoff.

        Algorithm:
            - Try up to retry_count times
            - On failure, wait delay * (backoff ** attempt) seconds
            - Don't retry on client errors (4xx except 429)
            - Raise mapped exception after final failure

        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Request parameters

        Returns:
            requests.Response on success

        Raises:
            JogetAPIError: Mapped from HTTP status code
        """
        last_exception: Exception | None = None
        retry_count = self.config.retry.count

        for attempt in range(retry_count + 1):  # +1 for initial attempt
            try:
                if self.config.debug and attempt > 0:
                    self.logger.debug(f"Retry attempt {attempt}/{retry_count} for {method} {url}")

                response = self._execute_request(method, url, **kwargs)

                # Consider 2xx successful
                if 200 <= response.status_code < 300:
                    if attempt > 0:
                        self.logger.info(
                            f"Request succeeded on attempt {attempt + 1}/{retry_count + 1}"
                        )
                    return response

                # Map error for non-2xx responses
                error = map_http_error(response, url)

                # Don't retry on client errors (except 429 rate limit)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    if self.config.debug:
                        self.logger.debug(f"Client error {response.status_code}, not retrying")
                    raise error

                # Server errors and 429 - retry
                last_exception = error
                self.logger.warning(f"Request failed with {response.status_code}, will retry")

            except RequestsTimeout as e:
                last_exception = TimeoutError(f"Request timeout: {e}")
                self.logger.warning(f"Request timeout on attempt {attempt + 1}")

            except RequestsConnectionError as e:
                last_exception = ConnectionError(f"Connection error: {e}")
                self.logger.warning(f"Connection error on attempt {attempt + 1}")

            except RequestException as e:
                last_exception = JogetAPIError(f"Request error: {e}")
                self.logger.warning(f"Request exception on attempt {attempt + 1}: {e}")

            # Don't sleep after the last attempt
            if attempt < retry_count:
                delay = self._calculate_delay(attempt)
                if self.config.debug:
                    self.logger.debug(f"Waiting {delay:.2f}s before retry")
                time.sleep(delay)

        # All retries exhausted
        if last_exception:
            self.logger.error(f"Request failed after {retry_count + 1} attempts")
            raise last_exception
        else:
            raise JogetAPIError(f"Request failed after {retry_count + 1} attempts")

    def _execute_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Execute a single HTTP request without retry.

        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Request parameters

        Returns:
            requests.Response

        Raises:
            RequestException: On request failure
        """
        if self.config.debug:
            self.logger.debug(f"{method} {url}")
            if "json" in kwargs:
                self.logger.debug(f"Request body: {kwargs['json']}")
            if "headers" in kwargs:
                self.logger.debug(f"Headers: {kwargs['headers']}")
            if "data" in kwargs:
                self.logger.debug(f"Form data keys: {list(kwargs['data'].keys()) if isinstance(kwargs['data'], dict) else 'non-dict'}")
            if "files" in kwargs:
                self.logger.debug(f"Files: {list(kwargs['files'].keys()) if isinstance(kwargs['files'], dict) else 'non-dict'}")

        try:
            response = requests.request(method, url, **kwargs)

            if self.config.debug:
                self.logger.debug(f"Response: {response.status_code}")
                self.logger.debug(f"Response body: {response.text[:500]}")

            return response

        except RequestsTimeout as e:
            self.logger.error(f"Request timeout: {url}")
            raise TimeoutError(f"Request timeout: {e}")

        except RequestsConnectionError as e:
            self.logger.error(f"Connection error: {url}")
            raise ConnectionError(f"Connection error: {e}")

        except RequestException as e:
            self.logger.error(f"Request failed: {url} - {e}")
            raise JogetAPIError(f"Request error: {e}")

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before retry based on strategy.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.config.retry.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            # Exponential backoff: delay * (backoff ^ attempt)
            delay = self.config.retry.delay * (self.config.retry.backoff**attempt)
        elif self.config.retry.strategy == RetryStrategy.LINEAR:
            # Linear backoff: delay * (1 + attempt)
            delay = self.config.retry.delay * (1 + attempt)
        else:  # FIXED
            # Fixed delay
            delay = self.config.retry.delay

        # Cap at max_delay
        return min(delay, self.config.retry.max_delay)

    def get(self, url: str, **kwargs) -> requests.Response:
        """Execute GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Execute POST request."""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """Execute PUT request."""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """Execute DELETE request."""
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs) -> requests.Response:
        """Execute PATCH request."""
        return self.request("PATCH", url, **kwargs)


__all__ = ["HTTPClient"]
