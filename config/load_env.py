# config/load_env.py

from dotenv import load_dotenv
import os

def load_environment_variables():
    load_dotenv()  # Ensure this is called as early as possible in the Streamlit app
    env_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "")  # Check this key
    }
    return env_vars
