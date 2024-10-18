import time
from nltk import sent_tokenize
from utils.file_utils import handle_error, sanitize_file_name, rotate_logs, check_disk_space
from providers.openai_provider import generate_with_openai
from providers.anthropic_provider import generate_with_anthropic
from providers.gemini_provider import generate_with_gemini
import streamlit as st

@st.cache_data(show_spinner=False, persist="disk")
def get_cached_response(provider_choice, prompt, chunk, chunk_size, model_choice=None, api_keys=None):
    """
    Retrieves cached response if available; otherwise, processes the chunk and caches the result.
    """
    combined_prompt = prompt + chunk
    try:
        if provider_choice == "OpenAI":
            response = generate_with_openai(combined_prompt, model=model_choice)
        elif provider_choice == "Anthropic":
            response = generate_with_anthropic(combined_prompt, api_key=api_keys.get("ANTHROPIC_API_KEY", ""))
        elif provider_choice == "Gemini":
            response = generate_with_gemini(combined_prompt, model=model_choice)
        else:
            raise ValueError(f"Unsupported provider: {provider_choice}")
        return response
    except Exception as e:
        # Let the caller handle the exception
        raise e

def split_text_into_chunks(text, chunk_size, chunk_by="words"):
    if chunk_by == "words":
        words = text.split()
        for i in range(0, len(words), chunk_size):
            yield ' '.join(words[i:i + chunk_size])
    elif chunk_by == "sentences":
        sentences = sent_tokenize(text)
        for i in range(0, len(sentences), chunk_size):
            yield ' '.join(sentences[i:i + chunk_size])
    elif chunk_by == "paragraphs":
        paragraphs = text.split('\n\n')
        for paragraph in paragraphs:
            yield paragraph  # Yield one paragraph at a time

def process_text_stream(text, provider_choice, prompt, chunk_size=500, chunk_by="words", model_choice=None, api_keys=None, max_retries=5):
    """
    Processes text using generators to handle large files efficiently.
    """
    final_response = []
    try:
        for chunk in split_text_into_chunks(text, chunk_size, chunk_by):
            cache_key = f"{prompt}_{chunk}"
            try:
                response = get_cached_response(provider_choice, prompt, chunk, chunk_size, model_choice, api_keys)
            except Exception as e:
                handle_error("ProcessingError", str(e))
                response = "[Failed to process this chunk.]"
            
            final_response.append(response)
            yield response  # Yield each response as it's processed
    except Exception as e:
        handle_error("ProcessingError", f"Stream processing failed: {e}")
        yield "[Processing failed due to an unexpected error.]"
