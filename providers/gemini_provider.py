# providers/gemini_provider.py

import google.generativeai as genai
from utils.retry_decorator import retry
from utils.file_utils import handle_error
import errno

# Attempt to import specific exceptions; fallback to generic Exception if not available
try:
    from google.generativeai.error import RateLimitError, APIConnectionError, Timeout, GenerativeAIError
    GEMINI_EXCEPTIONS = (RateLimitError, APIConnectionError, Timeout, GenerativeAIError)
except ImportError:
    # If specific exceptions are not available, use generic Exception
    GEMINI_EXCEPTIONS = (Exception,)

@retry(max_retries=10, initial_wait=2, backoff_factor=2, exceptions=GEMINI_EXCEPTIONS)
def generate_with_gemini(prompt, model="gemini-1.5-flash"):
    try:
        # Ensure the API is configured
        model_instance = genai.GenerativeModel(model)
        response = model_instance.generate_content(prompt)

        # Check if the response contains valid content
        ret = response.text
        if ret is not None and ret.strip():
            return ret
        else:
            handle_error("ProcessingError", "Gemini returned no valid content.")
            raise ValueError("Gemini returned no valid content.")

    except GEMINI_EXCEPTIONS as e:
        handle_error("APIError", f"Gemini API Error: {e}")
        raise e  # Re-raise to trigger retry

    except OSError as e:
        if e.errno == errno.ENOSPC:
            handle_error("StorageError", "No space left on device.")
        else:
            handle_error("APIError", f"An OS error occurred with Gemini: {e}")
        raise e  # Re-raise to trigger retry

    except Exception as e:
        handle_error("APIError", f"Failed to generate response from Gemini: {e}")
        raise e  # Re-raise to trigger retry
