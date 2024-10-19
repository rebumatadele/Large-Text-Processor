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

        # Log the raw response structure for debugging
        print("Gemini API raw response:", response)

        # Check if the response contains valid candidates
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]  # Get the first candidate

            # Check if the candidate has content with parts and retrieve the text
            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                ret = ''.join([part.text for part in candidate.content.parts if hasattr(part, 'text')])

                # Check if the text is valid and not empty
                if ret and ret.strip():
                    return ret
                else:
                    # Log the safety ratings and finish reason for debugging purposes
                    if candidate.finish_reason == "SAFETY":  # Indicates a content safety issue
                        safety_ratings = candidate.safety_ratings if hasattr(candidate, 'safety_ratings') else []
                        handle_error("ProcessingError", f"Gemini blocked content due to safety concerns. Safety ratings: {safety_ratings}")
                        return "[Content blocked due to safety concerns]"
                    else:
                        handle_error("ProcessingError", "Gemini returned no valid content.")
                        return "[Content blocked due to safety concerns]"
            else:
                handle_error("ProcessingError", "Gemini returned no content parts.")
                return "[No content parts available from Gemini.]"
        else:
            # Log an error for no valid candidates or a blocked response
            handle_error("ProcessingError", "Gemini returned no valid candidates or the response was blocked.")
            return "[No candidates available or response was blocked.]"

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
