# streamlit_app.py

import streamlit as st
import os
from config.load_env import load_environment_variables
from config.api_config import configure_openai, configure_anthropic, configure_gemini
from utils.file_utils import (
    load_prompt,
    save_prompt,
    handle_error,
    sanitize_file_name,
    clear_error_logs,
    clear_cache,
    list_saved_prompts,
    delete_prompt 
)
from utils.text_processing import split_text_into_chunks, get_cached_response
import time

# Initialize session state for error history, processed_chunks, and chat_buffer if not already initialized
if 'errors' not in st.session_state:
    st.session_state.errors = []
if 'processed_chunks' not in st.session_state:
    st.session_state.processed_chunks = {}
if 'chat_buffer' not in st.session_state:
    st.session_state.chat_buffer = ""

# Load environment variables
env_vars = load_environment_variables()

# Initialize providers with API keys
def initialize_providers(provider_choice, api_key):
    if provider_choice == "OpenAI":
        configure_openai(api_key)
    elif provider_choice == "Anthropic":
        configure_anthropic(api_key)
    elif provider_choice == "Gemini":
        configure_gemini(api_key)

# Streamlit app UI configuration
st.set_page_config(page_title="Text Processor with Generative AI", page_icon="🤖", layout="wide")

# Sidebar for configuration and management
st.sidebar.title("Configuration & Management")
st.sidebar.subheader("Provider Settings")

# Select provider
provider_choice = st.sidebar.selectbox(
    "Choose a provider",
    ["Anthropic", "Gemini", "OpenAI"]
)

# Add model selection for all providers
model_choice = None
if provider_choice == "OpenAI":
    model_choice = st.sidebar.selectbox("Choose a model", ["gpt-3.5-turbo", "gpt-4"])
elif provider_choice == "Anthropic":
    model_choice = st.sidebar.selectbox("Choose a model", ["claude-3-5-sonnet-20240620", "claude-3-5"])
elif provider_choice == "Gemini":
    model_choice = st.sidebar.selectbox("Choose a model", ["gemini-1.5-flash", "gemini-1.5"])

# Prefill the API key field from environment variables or manual entry
api_key = st.sidebar.text_input(
    "API Key", 
    type="password", 
    value={
        "OpenAI": env_vars.get("OPENAI_API_KEY", ""),
        "Anthropic": env_vars.get("ANTHROPIC_API_KEY", ""),
        "Gemini": env_vars.get("GEMINI_API_KEY", "")
    }.get(provider_choice, "")
)

# Configure the provider when the button is clicked
if st.sidebar.button("Configure"):
    if api_key:
        try:
            initialize_providers(provider_choice, api_key)
            st.sidebar.success(f"{provider_choice} configured successfully!")
        except Exception as e:
            handle_error("APIError", f"Configuration failed for {provider_choice}: {e}")
    else:
        handle_error("InvalidInput", "Please enter a valid API key.")

# Display error history in a collapsible section in the sidebar
st.sidebar.subheader("Error Logs")
with st.sidebar.expander("View Error History"):
    if st.session_state.errors:
        displayed_errors = st.session_state.errors[:50]  # Display only the latest 50 errors
        for error in displayed_errors:
            st.write(error)
    else:
        st.write("No errors logged yet.")

# Button to clear error logs
if st.sidebar.button("Clear Errors"):
    clear_error_logs()

# Button to clear cache
st.sidebar.subheader("Cache Management")
if st.sidebar.button("Clear Cache"):
    clear_cache()

# Prompt Management Section
st.sidebar.subheader("Prompt Management")

# Dropdown to select a saved prompt
saved_prompts = list_saved_prompts()
# Include "Default Prompt" if not already in saved_prompts
prompt_options = ["Default Prompt"] + saved_prompts
selected_prompt = st.sidebar.selectbox(
    "Select a saved prompt",
    prompt_options
)

# Load the selected prompt
if selected_prompt == "Default Prompt":
    prompt_content = load_prompt("Default Prompt")  # Ensure 'Default Prompt' exists
else:
    prompt_content = load_prompt(selected_prompt)

# Editable prompt area
st.header("Prompt Template")
edited_prompt = st.text_area("Edit your prompt template", value=prompt_content, height=200)

# Prompt management actions
with st.sidebar.expander("Manage Prompts"):
    # Option to save the current prompt
    with st.form(key="save_prompt_form"):
        st.write("### Save Current Prompt")
        new_prompt_name = st.text_input("Prompt Name")
        save_prompt_button = st.form_submit_button("Save Prompt")
        if save_prompt_button:
            if new_prompt_name:
                save_prompt(new_prompt_name, edited_prompt)
                st.sidebar.success(f"Prompt '{new_prompt_name}' saved successfully!")
            else:
                handle_error("InvalidInput", "Please provide a valid name for the prompt.")

    # Option to delete a saved prompt
    if saved_prompts:
        with st.form(key="delete_prompt_form"):
            st.write("### Delete a Prompt")
            prompt_to_delete = st.selectbox("Select a prompt to delete", saved_prompts)
            delete_prompt_button = st.form_submit_button("Delete Prompt")
            if delete_prompt_button:
                confirm = st.checkbox(f"Are you sure you want to delete '{prompt_to_delete}'?")
                if confirm:
                    delete_prompt(prompt_to_delete)
                    st.sidebar.success(f"Prompt '{prompt_to_delete}' deleted successfully!")

# Button to save the edited prompt (overwrites if it's the default prompt)
if st.button("Save Current Prompt") and not st.session_state.get('processing', False):
    if selected_prompt == "Default Prompt":
        save_prompt("Default Prompt", edited_prompt)  # Save as 'Default Prompt'
    else:
        save_prompt(selected_prompt, edited_prompt)
    st.success("Prompt saved successfully!")

st.markdown("---")

# Initialize session state for uploaded files and results
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'file_contents' not in st.session_state:
    st.session_state.file_contents = {}
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'current_file_index' not in st.session_state:
    st.session_state.current_file_index = 0
if 'current_chunk_index' not in st.session_state:
    st.session_state.current_chunk_index = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

# File uploader for multiple files with a dynamic key
st.header("Upload Files")
uploaded_files = st.file_uploader(
    "Upload input text files", 
    type="txt", 
    accept_multiple_files=True, 
    key=f"file_uploader_{st.session_state.uploader_key}"
)

# Store uploaded files in session state
if uploaded_files and not st.session_state.processing:
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        if file_name not in st.session_state.file_contents:
            try:
                file_content = uploaded_file.read().decode('utf-8')
                st.session_state.file_contents[file_name] = file_content
                st.session_state.uploaded_files.append(file_name)
            except Exception as e:
                handle_error("ProcessingError", f"Error reading {file_name}: {e}")

# Clear button to clear the uploaded files and errors
if st.session_state.file_contents and not st.session_state.processing:
    if st.button("Clear Files and Outputs"):
        st.session_state.uploaded_files = []
        st.session_state.results = {}
        st.session_state.file_contents = {}
        st.session_state.processed_chunks = {}
        st.session_state.errors = []
        st.session_state.uploader_key += 1
        st.rerun()
st.markdown("---")

# Preview and edit section
if st.session_state.file_contents and not st.session_state.processing:
    st.header("Preview and Edit Files")
    selected_file = st.selectbox("Select a file to preview and edit", list(st.session_state.file_contents.keys()), key="file_selector")
    
    # Initialize the edited content in session state if it doesn't exist
    if f"edited_{selected_file}" not in st.session_state:
        st.session_state[f"edited_{selected_file}"] = st.session_state.file_contents[selected_file]
    
    # Use a unique key for the text_area to ensure it updates correctly
    edited_content = st.text_area(
        "Edit the content", 
        value=st.session_state[f"edited_{selected_file}"], 
        height=300, 
        key=f"edit_{selected_file}"
    )
    
    # Update the session state whenever the content changes
    if edited_content != st.session_state[f"edited_{selected_file}"]:
        st.session_state[f"edited_{selected_file}"] = edited_content
    
    if st.button("Save Changes", key=f"save_{selected_file}") and not st.session_state.processing:
        st.session_state.file_contents[selected_file] = edited_content
        st.success(f"Changes to {selected_file} saved successfully!")
        st.rerun()

# Input for chunk size and chunk type (words, sentences, paragraphs)
st.header("Processing Settings")
chunk_size_input = st.number_input("Set chunk size", min_value=1, max_value=5000, value=500)
chunk_by = st.selectbox("Chunk by", ["words", "sentences", "paragraphs"])

st.markdown("---")

# Initialize placeholders for progress and status
progress_bar = st.progress(0)
percentage_text = st.empty()
time_text = st.empty()
status_placeholder = st.empty()


# Button to process the files
num_files = len(st.session_state.file_contents)
if st.button("Process Text") and not st.session_state.processing:
    # Define it once with a unique key outside the loop
    ai_responses_placeholder = st.empty()

    if 'chat_area_initialized' not in st.session_state:
        st.session_state.chat_area_initialized = True
        st.session_state.chat_buffer = ""

    ai_responses_placeholder.text_area(
        "AI Responses", 
        value=st.session_state.chat_buffer, 
        height=400, 
        key="chat_area", 
        disabled=False
    )
    if st.session_state.file_contents:
        st.session_state.processing = True
        st.session_state.results = {}
        st.session_state.chat_buffer = ""  # Reset chat buffer

        # Reset progress and status
        progress_bar.progress(0)
        percentage_text.text("0% completed.")
        time_text.text("Estimated time remaining: Calculating...")
        status_placeholder.text("Starting processing...")

        # Reset the AI Responses text area
        ai_responses_placeholder.text_area(
            "AI Responses", 
            value=st.session_state.chat_buffer, 
            height=400, 
            disabled=True
        )

        # Calculate total steps: splitting, processing, merging per file
        total_steps = 0
        split_steps = len(st.session_state.file_contents)
        processing_steps = sum([len(list(split_text_into_chunks(content, chunk_size_input, chunk_by))) for content in st.session_state.file_contents.values()])
        merge_steps = len(st.session_state.file_contents)
        total_steps = split_steps + processing_steps + merge_steps
        current_step = 0
        processed = 0

        # Start time for estimating remaining time
        st.session_state.start_time = time.time()

        # Processing logic
        for i, (file_name, file_content) in enumerate(st.session_state.file_contents.items()):
            # Check if file is already processed
            if file_name in st.session_state.results:
                split_chunks = list(split_text_into_chunks(file_content, chunk_size_input, chunk_by))
                current_step += (len(split_chunks) + 1)
                progress_bar.progress(current_step / total_steps)
                continue

            # Split the file
            status_placeholder.text(f"Splitting {file_name}...")

            # Add file header to chat
            st.session_state.chat_buffer += f"**{file_name}**:\n"
            st.session_state.chat_buffer += "🔄 Splitting the file into chunks...\n\n"
            
            # Update the text area with the new chat buffer content without redefining the key
            ai_responses_placeholder.text_area(
                "AI Responses For Each Chunk", 
                value=st.session_state.chat_buffer, 
                height=400, 
                disabled=False
            )

            split_chunks = list(split_text_into_chunks(file_content, chunk_size_input, chunk_by))
            current_step += 1
            progress_bar.progress(current_step / total_steps)

            # Initialize results for this file
            results = []

            # Process each split chunk
            for j, chunk in enumerate(split_chunks):
                # Update status
                status_placeholder.text(f"Processing chunk {j + 1}/{len(split_chunks)} of {file_name}...")

                try:
                    response = get_cached_response(
                        provider_choice=provider_choice,
                        prompt=edited_prompt,
                        chunk=chunk,
                        chunk_size=chunk_size_input,
                        model_choice=model_choice,
                        api_keys=env_vars
                    )
                except Exception as e:
                    handle_error("ProcessingError", str(e))
                    response = "[Failed to process this chunk.]"

                # Append response to results
                results.append(response)

                # Append response to chat buffer
                st.session_state.chat_buffer += f"Chunk {j + 1}:\n{response}\n\n"

                # Update the text area with the new chat buffer content without redefining the key
                ai_responses_placeholder.text_area(
                    "AI Responses For Each Chunk", 
                    value=st.session_state.chat_buffer, 
                    height=400, 
                    disabled=False
                )

                # Update progress
                current_step += 1
                progress_bar.progress(current_step / total_steps)

                # Update percentage and time
                elapsed_time = time.time() - st.session_state.start_time
                if current_step > 0:
                    estimated_total_time = (elapsed_time / current_step) * total_steps
                    estimated_time_remaining = estimated_total_time - elapsed_time
                    percentage = int((current_step / total_steps) * 100)
                    percentage_text.text(f"{percentage}% completed.")
                    time_text.text(f"Estimated time remaining: {int(estimated_time_remaining)} seconds.")
                else:
                    percentage_text.text("0% completed.")
                    time_text.text("Estimated time remaining: Calculating...")

                # Short sleep to allow UI to update
                time.sleep(0.1)

            # Merge processed chunks and store the result
            status_placeholder.text(f"Merging processed chunks for {file_name}...")
            merged_text = "\n".join(results)
            st.session_state.results[file_name] = merged_text
            current_step += 1
            progress_bar.progress(current_step / total_steps)
            processed += 1
            percentage = int((current_step / total_steps) * 100)
            percentage_text.text(f"{percentage}% completed.")
            time_text.text(f"Estimated time remaining: Calculating...")
            st.session_state.chat_buffer += f"✅ {file_name} processed, {processed} out of {num_files} files.\n\n"

            # Update the text area with the final chat buffer content without redefining the key
            ai_responses_placeholder.text_area(
                "AI Responses For Each Chunk", 
                value=st.session_state.chat_buffer, 
                height=400, 
                disabled=False
            )

        st.session_state.processing = False
        st.success("Processing completed!")
        st.rerun()

st.markdown("---")

# Display results in a chat-like interface (Final Results)
st.header("Final Results")
with st.container():
    for file_name, response_text in st.session_state.results.items():
        st.subheader(f"Output for {file_name}")
        st.text_area(f"Output for {file_name}", value=response_text, height=300, key=f"final_output_{file_name}")
        st.download_button(
            label=f"Download Output for {file_name}",
            data=response_text,
            file_name=f"{sanitize_file_name(file_name)}_final.txt",
            mime="text/plain"
        )
