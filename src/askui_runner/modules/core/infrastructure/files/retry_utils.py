import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


def extract_response_text(response: requests.Response) -> str | None:
    """
    Safely extract text content from an HTTP response.
    Prioritizes JSON 'detail' field if available.

    Args:
        response: The HTTP response to extract text from

    Returns:
        str | None: The extracted text or None if extraction failed
    """
    # First try to parse as JSON and look for 'detail' field
    try:
        json_data = response.json()
        if isinstance(json_data, dict) and "detail" in json_data:
            return str(json_data["detail"])
    except (ValueError, AttributeError):
        # Not JSON or couldn't parse, continue to text extraction
        pass

    # Fall back to regular text extraction
    try:
        return response.text
    except (AttributeError, UnicodeDecodeError):
        try:
            return str(response.content)
        except:  # noqa: E722
            return None


class NonRetryableHTTPError(Exception):
    """Exception for HTTP errors that should not be retried."""

    def __init__(self, response: requests.Response):
        self.response = response
        self.status_code = response.status_code
        response_text = extract_response_text(response)

        # Create a more detailed error message including the response text
        error_message = (
            f"{response.status_code} {response.reason} for url: {response.url}"
        )
        if response_text:
            error_message += f"\n\n{response_text}"

        super().__init__(error_message)


# List of HTTP status codes that are considered transient and should be retried
TRANSIENT_HTTP_STATUS_CODES = (408, 429, 500, 502, 503, 504)


def handle_response_status(
    response: requests.Response, expected_status_code: int = 200
) -> None:
    """
    Handle HTTP response status, raising appropriate exceptions.

    Args:
        response: The HTTP response to check
        expected_status_code: The expected successful status code

    Raises:
        requests.exceptions.HTTPError: For transient errors that should be retried
        NonRetryableHTTPError: For non-transient errors that should not be retried
    """
    if response.status_code != expected_status_code:
        # Only retry on specific status codes that might be transient
        if response.status_code in TRANSIENT_HTTP_STATUS_CODES:
            response.raise_for_status()
        else:
            # For other status codes, raise without allowing retry
            raise NonRetryableHTTPError(response)


# Standard retry decorator for HTTP operations
http_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(),
    retry=retry_if_exception_type(
        (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RetryError,
            requests.exceptions.HTTPError,
        )
    ),
)
