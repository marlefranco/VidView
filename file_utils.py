"""Utility functions for file operations in the VidView application."""

from pathlib import Path
from typing import Tuple, Dict, Union, Dict, Optional
import logging

def check_data_folder(folder_path: Path) -> Tuple[bool, str, Dict[str, Path]]:
    """Check if the folder contains the required data files.

    Args:
        folder_path (Path): The folder path to check.

    Returns:
        Tuple[bool, str, Dict[str, Path]]: A tuple containing:
            - bool: True if all required files exist, False otherwise.
            - str: Error message if any files are missing.
            - Dict[str, Path]: Dictionary of file paths if all files exist.
    """
    required_files = {
        "video": folder_path / "video.avi",
        "frame_times": folder_path / "frame_times.txt",
        "parsed_data": folder_path / "parsed_data.txt",
        "control_inputs": folder_path / "control_inputs_log.txt"
    }

    missing_files = []
    for name, path in required_files.items():
        if not path.exists():
            missing_files.append(f"{name} ({path.name})")

    if missing_files:
        return False, f"Missing required files: {', '.join(missing_files)}", {}

    return True, "", required_files


def load_frame_times(frame_times_path: Union[str, Path], logger: Optional[logging.Logger] = None) -> Dict[int, str]:
    """Load frame times from a file and return a mapping of frame numbers to timestamps.

    Args:
        frame_times_path (Union[str, Path]): Path to the frame times file.
        logger (Optional[logging.Logger], optional): Logger to use for logging messages. Defaults to None.

    Returns:
        Dict[int, str]: Dictionary mapping frame numbers to timestamps.
    """
    frame_to_timestamp = {}
    try:
        with open(frame_times_path, "r", encoding="utf-8") as f:
            # Skip header
            next(f)
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    frame_number = int(parts[0])
                    timestamp = parts[1]
                    frame_to_timestamp[frame_number] = timestamp

        if logger:
            logger.info(f"Loaded {len(frame_to_timestamp)} frame numbers and timestamps directly from {frame_times_path}")
    except Exception as e:
        if logger:
            logger.error(f"Error loading frame times directly from {frame_times_path}: {e}")
        # Don't re-raise the exception, just return an empty dict
        # The caller can check if the dict is empty and handle accordingly

    return frame_to_timestamp
