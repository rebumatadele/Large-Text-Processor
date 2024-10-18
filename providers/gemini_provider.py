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

@retry(max_retries=5, initial_wait=5, backoff_factor=2, exceptions=GEMINI_EXCEPTIONS)
def generate_with_gemini(prompt, model="gemini-1.5-flash"):
    try:
        # Ensure the API is configured
        model = genai.GenerativeModel(model)
        response = model.generate_content(prompt)

        # Check if the response contains valid content
        if not response:
            handle_error("ProcessingError", "Gemini returned no valid content.")
            return "[No valid content returned.]"
            
        return response.text

    
    except GEMINI_EXCEPTIONS as e:
        handle_error("APIError", f"Gemini API Error: {e}")
        return f"[Gemini API error: {e}]"
    except OSError as e:
        if e.errno == errno.ENOSPC:
            handle_error("StorageError", "No space left on device.")
        else:
            handle_error("APIError", f"An OS error occurred with Gemini: {e}")
        return f"[OS error: {e}]"
    except Exception as e:
        handle_error("APIError", f"Failed to generate response from Gemini: {e}")
        return f"[Unexpected error: {e}]"
