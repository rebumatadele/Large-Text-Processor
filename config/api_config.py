# config/api_config.py

import openai
from anthropic import Anthropic
import google.generativeai as genai

def configure_openai(api_key):
    openai.api_key = api_key

def configure_anthropic(api_key):
    try:
        # Correctly initializing Anthropic with the API key
        anthropic_instance = Anthropic(api_key=api_key)
        return anthropic_instance
    except Exception as e:
        raise Exception(f"Failed to configure Anthropic: {e}")

def configure_gemini(api_key):
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise Exception(f"Failed to configure Gemini: {e}")
