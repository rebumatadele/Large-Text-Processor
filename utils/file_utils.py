# utils/file_utils.py

import os
import time
import streamlit as st
import shutil
import errno
import re

# Define paths
ERROR_LOG_PATH = os.path.join("logs", "error_log.txt")
PROMPTS_DIR = os.path.join("prompts")  # Directory to store prompts

def handle_error(error_type, message):
    """
    Handles errors by displaying a user-friendly message, logging the technical details,
    and maintaining an error history in session state.
    """
    # Define user-friendly messages based on error_type
    user_messages = {
        "FileNotFound": {
            "message": "The file you are trying to access was not found.",
            "suggestion": "Please ensure you have uploaded the correct file."
        },
        "APIError": {
            "message": "We're experiencing issues connecting to the AI service.",
            "suggestion": "Please check your internet connection and try again. If the problem persists, it might be a temporary service outage."
        },
        "InvalidInput": {
            "message": "The input provided is invalid.",
            "suggestion": "Please verify that your file is in the correct format and try again."
        },
        "ProcessingError": {
            "message": "An error occurred while processing your request.",
            "suggestion": "Please try again. If the issue continues, consider contacting support."
        },
        "StorageError": {
            "message": "Insufficient storage space detected.",
            "suggestion": "Please free up some disk space and try again."
        },
        "UnknownError": {
            "message": "An unexpected error occurred.",
            "suggestion": "Please try again or reach out to support for assistance."
        }
    }

    # Map technical message to user-friendly message
    if error_type in user_messages:
        user_message = user_messages[error_type]["message"]
        user_suggestion = user_messages[error_type]["suggestion"]
    else:
        user_message = user_messages["UnknownError"]["message"]
        user_suggestion = user_messages["UnknownError"]["suggestion"]

    # Display user-friendly message in the sidebar
    st.sidebar.error(f"{user_message} {user_suggestion}")

    # Create the error message with timestamp
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    formatted_error = f"[{timestamp}] - {error_type}: {message}"

    # Initialize error history in session state if not present
    if 'errors' not in st.session_state:
        st.session_state.errors = []

    # Prepend the new error to have the latest at the top
    st.session_state.errors.insert(0, formatted_error)

    # Log the technical error to the log file
    try:
        os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)  # Ensure the logs directory exists
        with open(ERROR_LOG_PATH, "a") as log_file:
            log_file.write(f"{timestamp} - {error_type}: {message}\n")
    except OSError as e:
        if e.errno == errno.ENOSPC:
            # No space left on device
            st.sidebar.error("Critical Error: No space left on device. Please free up disk space and restart the app.")
        else:
            # Other OS errors
            st.sidebar.error(f"An OS error occurred while logging: {e}")

def sanitize_file_name(file_name):
    """
    Sanitizes the file name by replacing invalid characters with an underscore.
    """
    return re.sub(r'[<>:"/\\|?*\r\n]+', '_', file_name)

def list_saved_prompts():
    """
    Lists all saved prompts in the prompts directory.
    Returns:
        List of prompt names without the .txt extension.
    """
    try:
        os.makedirs(PROMPTS_DIR, exist_ok=True)  # Ensure the prompts directory exists
        prompts = [f[:-4] for f in os.listdir(PROMPTS_DIR) if f.endswith('.txt')]
        return prompts
    except OSError as e:
        handle_error("ProcessingError", f"Failed to list saved prompts: {e}")
        return []

def load_prompt(name=""):
    """
    Loads a prompt by name. If no name is provided, loads the default prompt.txt.
    Args:
        name (str): The name of the prompt to load.
    Returns:
        The content of the prompt as a string.
    """
    try:
        os.makedirs(PROMPTS_DIR, exist_ok=True)  # Ensure the prompts directory exists
        if name:
            file_path = os.path.join(PROMPTS_DIR, f"{sanitize_file_name(name)}.txt")
        else:
            file_path = "prompt.txt"  # Default prompt file
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        handle_error("FileNotFound", f"Prompt '{name}' not found.")
        return ""
    except OSError as e:
        handle_error("ProcessingError", f"Failed to load prompt '{name}': {e}")
        return ""

def save_prompt(name, content):
    """
    Saves a prompt with the given name and content.
    Args:
        name (str): The name of the prompt.
        content (str): The content of the prompt.
    """
    try:
        os.makedirs(PROMPTS_DIR, exist_ok=True)  # Ensure the prompts directory exists
        file_path = os.path.join(PROMPTS_DIR, f"{sanitize_file_name(name)}.txt")
        with open(file_path, 'w') as file:
            file.write(content)
        st.sidebar.success(f"Prompt '{name}' saved successfully!")
    except OSError as e:
        if e.errno == errno.ENOSPC:
            handle_error("StorageError", "No space left on device. Unable to save the prompt.")
        else:
            handle_error("ProcessingError", f"Failed to save prompt '{name}': {e}")

def delete_prompt(name):
    """
    Deletes a prompt by name.
    Args:
        name (str): The name of the prompt to delete.
    """
    try:
        file_path = os.path.join(PROMPTS_DIR, f"{sanitize_file_name(name)}.txt")
        if os.path.exists(file_path):
            os.remove(file_path)
            st.sidebar.success(f"Prompt '{name}' deleted successfully!")
        else:
            handle_error("FileNotFound", f"Prompt '{name}' does not exist.")
    except OSError as e:
        handle_error("ProcessingError", f"Failed to delete prompt '{name}': {e}")

def clear_error_logs():
    """
    Clears the error logs by overwriting the log file with empty content.
    """
    try:
        if os.path.exists(ERROR_LOG_PATH):
            with open(ERROR_LOG_PATH, "w") as log_file:
                log_file.write("")
        # Also reset the in-memory error history
        st.session_state.errors = []
        st.sidebar.success("Error logs cleared successfully.")
    except OSError as e:
        if e.errno == errno.ENOSPC:
            # No space left on device
            st.sidebar.error("Critical Error: No space left on device. Unable to clear error logs.")
        else:
            # Other OS errors
            st.sidebar.error(f"An OS error occurred while clearing error logs: {e}")

def rotate_logs(max_size=10*1024*1024):
    """
    Rotates the log file if it exceeds max_size.
    :param max_size: Maximum size of the log file in bytes before rotation.
    """
    if os.path.exists(ERROR_LOG_PATH) and os.path.getsize(ERROR_LOG_PATH) > max_size:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        archived_log = f"{ERROR_LOG_PATH}.{timestamp}.bak"
        try:
            shutil.move(ERROR_LOG_PATH, archived_log)
            # Create a new empty log file
            with open(ERROR_LOG_PATH, "w") as log_file:
                log_file.write("")
            st.sidebar.info(f"Log file rotated. Archived as {archived_log}.")
        except OSError as e:
            if e.errno == errno.ENOSPC:
                st.sidebar.error("Critical Error: No space left on device. Unable to rotate logs.")
            else:
                st.sidebar.error(f"An OS error occurred while rotating logs: {e}")

def check_disk_space(required_space=100*1024*1024):
    """
    Checks if there is enough disk space.
    :param required_space: Required space in bytes. Default is 100MB.
    :return: True if enough space, False otherwise.
    """
    try:
        statvfs = os.statvfs('/')
        free_space = statvfs.f_frsize * statvfs.f_bavail
        return free_space >= required_space
    except Exception as e:
        handle_error("UnknownError", f"Failed to check disk space: {e}")
        return False

def clear_cache():
    """
    Clears the Streamlit cache and any other cached data.
    """
    try:
        # Clears all cached data using Streamlit's clear function
        st.cache_data.clear()
        
        # Clear the processed_chunks from session state if used elsewhere
        if 'processed_chunks' in st.session_state:
            st.session_state.processed_chunks = {}
        
        st.success("Streamlit cache cleared successfully.")
    except Exception as e:
        handle_error("ProcessingError", f"Failed to clear cache: {e}")
