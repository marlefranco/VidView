"""Entry point for the Video Spectra Viewer application."""
import sys
import os
from typing import Optional, Tuple
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from viewer import MainViewerWindow
from output_file import generate_output_file
from ui.status_window import StatusWindow


def select_data_folder() -> Optional[Path]:
    """Show a folder browser dialog to select the data folder.

    Returns:
        Optional[Path]: The selected folder path, or None if canceled.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = QFileDialog()
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dialog.setWindowTitle("Select Data Folder")

    # Try to start in the ExampleFiles directory if it exists
    example_dir = Path("ExampleFiles")
    if example_dir.exists():
        dialog.setDirectory(str(example_dir))

    if dialog.exec():
        selected_folders = dialog.selectedFiles()
        if selected_folders:
            return Path(selected_folders[0])

    return None


def check_data_folder(folder_path: Path) -> Tuple[bool, str, dict]:
    """Check if the selected folder contains the required data files.

    Args:
        folder_path (Path): The folder path to check.

    Returns:
        Tuple[bool, str, dict]: A tuple containing:
            - bool: True if all required files exist, False otherwise.
            - str: Error message if any files are missing.
            - dict: Dictionary of file paths if all files exist.
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


def main() -> int:
    """Launch the application and ensure video resources are released."""
    app = QApplication(sys.argv)

    # Apply dark theme to the entire application
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #2b2b2b;
            color: white;
        }
        QLabel {
            color: white;
        }
        QPushButton {
            background-color: #3b3b3b;
            color: white;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #4b4b4b;
        }
        QTableWidget {
            background-color: #2b2b2b;
            color: white;
            gridline-color: #3b3b3b;
            border: 1px solid #3b3b3b;
        }
        QTableWidget::item {
            background-color: #2b2b2b;
            color: white;
        }
        QHeaderView::section {
            background-color: #3b3b3b;
            color: white;
            border: 1px solid #4b4b4b;
        }
        QMenuBar {
            background-color: #2b2b2b;
            color: white;
        }
        QMenuBar::item {
            background-color: #2b2b2b;
            color: white;
        }
        QStatusBar {
            background-color: #2b2b2b;
            color: white;
        }
    """)

    # Select data folder
    folder_path = select_data_folder()
    if folder_path is None:
        # If no folder selected, use the default ExampleFiles folder
        folder_path = Path("ExampleFiles")

    # Check if the folder contains the required files
    valid, error_message, file_paths = check_data_folder(folder_path)
    if not valid:
        QMessageBox.critical(None, "Error", f"The selected folder does not contain all required files.\n\n{error_message}")
        return 1

    # Show status window
    status_window = StatusWindow()
    status_window.show()
    status_window.update_status("Generating output file...")

    # Generate the output file
    output_path = folder_path / "output.txt"
    generate_output_file(
        file_paths["frame_times"],
        file_paths["parsed_data"],
        file_paths["control_inputs"],
        output_path
    )

    status_window.update_status("Initializing main window...")

    window: Optional[MainViewerWindow] = None
    try:
        # Initialize the main window with the selected file paths
        window = MainViewerWindow(
            str(file_paths["video"]),
            str(file_paths["frame_times"]),
            str(file_paths["parsed_data"]),
            str(file_paths["control_inputs"])
        )

        # Close the status window and show the main window
        status_window.close()
        window.show()

        return app.exec()
    finally:
        # Release the capture in case the window was closed programmatically
        if window is not None and window.cap.isOpened():
            window.cap.release()


if __name__ == "__main__":
    sys.exit(main())
