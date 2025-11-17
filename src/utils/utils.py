import os
import shutil
from src.utils.logger import log_func


def create_directory(path: str):
    """Create output directory if it does not exist."""
    if not os.path.exists(path):
        os.makedirs(path)


def clean_directory(directory_path):
    """Remove all contents of a directory."""
    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)
        try:
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            log_func(f"Warning: Failed to delete {item_path}: {e}")


def remove_file(directory_path, file_name):
    """Remove a specific file from a directory."""
    file_path = os.path.join(directory_path, file_name)
    try:
        if os.path.isfile(file_path):
            os.unlink(file_path)
    except Exception as e:
        log_func(f"Warning: Failed to delete {file_path}: {e}")


def remove_directory(directory_path):
    """Remove an entire directory including the folder itself."""
    try:
        if os.path.isdir(directory_path):
            shutil.rmtree(directory_path)
    except Exception as e:
        log_func(f"Warning: Failed to delete directory {directory_path}: {e}")
