"""
Batch processor for Video Spectra Viewer.

This script allows the user to select a parent directory, then processes all subfolders
within that directory to generate output.txt files without launching the UI.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from output_file import generate_output_file
from logging_config import get_logger
from file_utils import check_data_folder

# Create a logger for this module
logger = get_logger("batch_processor")

def select_parent_directory() -> Optional[Path]:
    """Show a folder browser dialog to select the parent directory.

    Returns:
        Optional[Path]: The selected folder path, or None if canceled.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = QFileDialog()
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dialog.setWindowTitle("Select Parent Directory")

    # Try to start in the current directory
    dialog.setDirectory(os.getcwd())

    if dialog.exec():
        selected_folders = dialog.selectedFiles()
        if selected_folders:
            return Path(selected_folders[0])

    return None


def get_all_subfolders(parent_dir: Path) -> List[Path]:
    """Get all subfolders in the parent directory.

    Args:
        parent_dir (Path): The parent directory.

    Returns:
        List[Path]: List of subfolder paths.
    """
    return [f for f in parent_dir.iterdir() if f.is_dir()]

def process_folder(folder_path: Path) -> bool:
    """Process a single folder to generate the output file.

    Args:
        folder_path (Path): The folder path to process.

    Returns:
        bool: True if processing was successful, False otherwise.
    """
    logger.info(f"Processing folder: {folder_path}")

    # Check if the folder contains the required files
    valid, error_message, file_paths = check_data_folder(folder_path)
    if not valid:
        logger.error(f"Folder {folder_path} does not contain all required files: {error_message}")
        return False

    # Generate the output file
    output_path = folder_path / "output.txt"
    try:
        generate_output_file(
            file_paths["frame_times"],
            file_paths["parsed_data"],
            file_paths["control_inputs"],
            output_path
        )
        logger.info(f"Successfully generated output file at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error generating output file for {folder_path}: {e}")
        return False

def main() -> int:
    """Main function to process all subfolders in the parent directory."""
    app = QApplication(sys.argv)

    # Select parent directory
    parent_dir = select_parent_directory()
    if parent_dir is None:
        logger.error("No parent directory selected. Exiting.")
        return 1

    logger.info(f"Selected parent directory: {parent_dir}")

    # Get all subfolders
    subfolders = get_all_subfolders(parent_dir)
    if not subfolders:
        message = f"No subfolders found in {parent_dir}"
        logger.warning(message)
        QMessageBox.warning(None, "No Subfolders", message)
        return 1

    logger.info(f"Found {len(subfolders)} subfolders")

    # Process each subfolder
    successful_folders = 0
    failed_folders = 0

    for folder in subfolders:
        if process_folder(folder):
            successful_folders += 1
        else:
            failed_folders += 1

    # Show summary message
    summary = (
        f"Processing complete!\n\n"
        f"Total subfolders: {len(subfolders)}\n"
        f"Successfully processed: {successful_folders}\n"
        f"Failed to process: {failed_folders}"
    )

    logger.info(summary.replace('\n', ' '))
    QMessageBox.information(None, "Processing Complete", summary)

    return 0

if __name__ == "__main__":
    sys.exit(main())
