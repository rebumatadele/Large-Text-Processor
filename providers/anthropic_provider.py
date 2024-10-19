# providers/anthropic_provider.py

from curl_cffi.requests import post
from curl_cffi.requests.exceptions import (
    CurlError,
    HTTPError,
    ConnectionError,
    Timeout
)
from utils.retry_decorator import retry
from utils.file_utils import handle_error
import errno

# Define the exceptions to catch
ANTHROPIC_EXCEPTIONS = (CurlError, HTTPError, ConnectionError, Timeout)

@retry(max_retries=10, initial_wait=2, backoff_factor=2, exceptions=ANTHROPIC_EXCEPTIONS)
def generate_with_anthropic(prompt, api_key):
    headers = {
        'x-api-key': api_key,
        'content-type': 'application/json',
        'anthropic-version': '2023-06-01',
    }

    data = {
        "model": "claude-3-5-sonnet-20240620",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }
    try:
        response = post('https://api.anthropic.com/v1/messages', headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            response_json = response.json()
            content = response_json.get("content")
            print(content)
            if content:
                if isinstance(content, list):
                    return "".join([item.get("text", "") for item in content])
                return content
            else:
                handle_error("ProcessingError", "No content field in Anthropic response.")
                raise ValueError("No content field in response.")
        elif response.status_code == 429:
            handle_error("APIError", "Anthropic rate limit exceeded. Please wait before retrying.")
            raise HTTPError("Anthropic rate limit exceeded. Please wait before retrying.")
        else:
            error_message = response.json().get('error', {}).get('message', 'Unknown error')
            handle_error("APIError", f"Anthropic Error: {response.status_code} - {error_message}")
            raise HTTPError(f"Anthropic API error: {error_message}")
    except ANTHROPIC_EXCEPTIONS as e:
        handle_error("APIError", f"Failed to connect to Anthropic service: {e}")
        raise e  # Re-raise to trigger retry
    except OSError as e:
        if e.errno == errno.ENOSPC:
            handle_error("StorageError", "No space left on device.")
            raise e  # Re-raise as it's a critical error
        else:
            handle_error("APIError", f"An OS error occurred with Anthropic: {e}")
            raise e  # Re-raise to trigger retry
    except Exception as e:
        handle_error("APIError", f"An unexpected error occurred with Anthropic: {e}")
        raise e  # Re-raise to trigger retry
