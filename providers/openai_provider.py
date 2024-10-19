# providers/openai_provider.py

import openai
from utils.retry_decorator import retry
from utils.file_utils import handle_error
import errno

# Attempt to import specific exceptions; fallback to generic Exception if not available
try:
    from openai.error import RateLimitError, APIConnectionError, Timeout, ContentPolicyViolationError
    OPENAI_EXCEPTIONS = (RateLimitError, APIConnectionError, Timeout, ContentPolicyViolationError)
except ImportError:
    # If specific exceptions are not available, use generic Exception
    OPENAI_EXCEPTIONS = (Exception,)

@retry(max_retries=10, initial_wait=2, backoff_factor=2, exceptions=OPENAI_EXCEPTIONS)
def generate_with_openai(prompt, model="gpt-4"):
    try:
        response = openai.ChatCompletion.create(
            model=model,  
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.get('content')
        if content and content.strip():
            return content
        else:
            handle_error("ProcessingError", "OpenAI returned no valid content.")
            raise ValueError("OpenAI returned no valid content.")
    
    except RateLimitError:
        handle_error("APIError", "Rate limit exceeded. Please wait a moment before retrying.")
        raise RateLimitError("Rate limit exceeded. Please wait a moment before retrying.")
    
    except APIConnectionError:
        handle_error("APIError", "Failed to connect to OpenAI service. Please check your internet connection.")
        raise APIConnectionError("Failed to connect to OpenAI service. Please check your internet connection.")
    
    except Timeout:
        handle_error("APIError", "The request to OpenAI timed out. Retrying might help.")
        raise Timeout("The request to OpenAI timed out. Retrying might help.")
    
    except ContentPolicyViolationError:
        handle_error("APIError", "Your request was blocked by OpenAI's content policy.")
        raise ContentPolicyViolationError("Your request was blocked by OpenAI's content policy.")
    
    except OSError as e:
        if e.errno == errno.ENOSPC:
            handle_error("StorageError", "No space left on device.")
        else:
            handle_error("APIError", f"An OS error occurred with OpenAI: {e}")
        raise e  # Re-raise to trigger retry
    
    except Exception as e:
        handle_error("APIError", f"An unexpected error occurred with OpenAI: {e}")
        raise e  # Re-raise to trigger retry
