# utils/retry_decorator.py

import time
from utils.file_utils import handle_error

def retry(max_retries=5, initial_wait=5, backoff_factor=2, exceptions=(Exception,)):
    """
    Decorator to retry a function with exponential backoff upon specified exceptions.
    
    :param max_retries: Maximum number of retries.
    :param initial_wait: Initial wait time between retries (in seconds).
    :param backoff_factor: Factor by which the wait time increases with each retry.
    :param exceptions: Tuple of exceptions that trigger a retry.
    """
    def decorator_retry(func):
        def wrapper_retry(*args, **kwargs):
            retries = 0
            wait_time = initial_wait
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries == max_retries:
                        handle_error("ProcessingError", f"Failed to execute {func.__name__} after {max_retries} retries.")
                        return "[Failed to process this chunk.]"
                    handle_error("ProcessingError", f"Error in {func.__name__}: {e}. Retrying {retries}/{max_retries} in {wait_time} seconds...")
                    time.sleep(wait_time)
                    wait_time *= backoff_factor
            return "[Failed to process this chunk.]"
        return wrapper_retry
    return decorator_retry
