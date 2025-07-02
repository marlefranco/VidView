"""Main viewer window implementation."""

from __future__ import annotations

import cv2
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QTableWidgetItem,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
    QLabel,
)
from PyQt6.QtCore import Qt, QRect, QTimer

from ui.main_window import Ui_MainViewerWindow
from . import __version__
from .base_viewer import BaseViewer
from .controllers import VideoSpectraController
from .models import SpectralDataModel, FrameTimesModel, MetadataModel


class MainViewerWindow(BaseViewer):
    """Main application window.

    Parameters default to sample data under ``ExampleFiles/`` so the
    viewer can be launched without explicitly providing file paths.
    """

    def __init__(
        self,
        video_path: str = "ExampleFiles/video.avi",
        frame_times_path: str = "ExampleFiles/frame_times.txt",
        spectral_path: str = "ExampleFiles/parsed_data.txt",
        metadata_path: str = "ExampleFiles/control_inputs_log.txt",
    ) -> None:
        print("\n==== INITIALIZING MAIN VIEWER WINDOW ====")
        print(f"Video path: {video_path}")
        print(f"Frame times path: {frame_times_path}")
        print(f"Spectral path: {spectral_path}")
        print(f"Metadata path: {metadata_path}")

        # Check if files exist
        import os
        for path, name in [(video_path, "Video"), (frame_times_path, "Frame times"), 
                          (spectral_path, "Spectral"), (metadata_path, "Metadata")]:
            if os.path.exists(path):
                print(f"{name} file exists: {path}")
                # Print file size
                size = os.path.getsize(path)
                print(f"{name} file size: {size} bytes")

                # If it's a text file, print the first few lines
                if name in ["Frame times", "Spectral", "Metadata"]:
                    try:
                        with open(path, 'r') as f:
                            lines = f.readlines()[:5]  # Read first 5 lines
                            print(f"{name} file first {len(lines)} lines:")
                            for i, line in enumerate(lines):
                                print(f"  {i+1}: {line.strip()}")
                    except Exception as e:
                        print(f"Error reading {name} file: {e}")
            else:
                print(f"{name} file does not exist: {path}")

        super().__init__(video_path)
        print("BaseViewer initialized")

        self.ui = Ui_MainViewerWindow()
        self.ui.setupUi(self)
        print("UI setup complete")

        self.frame_times_path = frame_times_path
        self.spectral_path = spectral_path
        self.metadata_path = metadata_path

        # Initialize controller
        print("Initializing controller...")
        self.controller = VideoSpectraController(
            self,
            self.video_path,
            self.spectral_path,
            self.frame_times_path,
            self.metadata_path
        )
        print("Controller initialized")
        print(f"Spectral model has {len(self.controller.spectral_model.data)} rows")
        print(f"Frame times model has {len(self.controller.frame_times_model.frame_times)} entries")

        # Set up plot widget
        print("Setting up plot widget...")
        plot_layout = self.ui.plotWidget.layout()
        if plot_layout is None:
            plot_layout = QVBoxLayout(self.ui.plotWidget)
        plot_layout.addWidget(self.canvas)
        self.ui.videoPlotLayout.setStretch(0, 1)
        self.ui.videoPlotLayout.setStretch(1, 1)
        self.ui.videoLabel.setScaledContents(False)
        print("Plot widget setup complete")

        # Add version header to metadata table
        from . import __version__
        print(f"Version: {__version__}")
        self.controller.update_metadata_table(self.ui.metadataTable, __version__)
        print("Metadata table updated with version")

        # Add Save Updates button
        from PyQt6.QtWidgets import QPushButton
        self.saveUpdatesButton = QPushButton("Save Updates")
        self.saveUpdatesButton.setMinimumSize(150, 0)
        self.saveUpdatesButton.setMaximumSize(150, 16777215)
        self.ui.gridLayout.addWidget(self.saveUpdatesButton, 2, 1, 1, 1)

        # Add Play button
        self.playButton = QPushButton("Play")
        self.playButton.setMinimumSize(150, 0)
        self.playButton.setMaximumSize(150, 16777215)
        self.ui.gridLayout.addWidget(self.playButton, 1, 1, 1, 1)

        # Initialize timer for auto-play
        self.playTimer = QTimer()
        self.playTimer.setInterval(1000)  # 1 second delay
        self.playTimer.timeout.connect(self.next_frame)
        self.isPlaying = False

        # Connect signals
        print("Connecting signals...")
        self.ui.nextButton.clicked.connect(self.next_frame)
        self.ui.prevButton.clicked.connect(self.prev_frame)
        self.saveUpdatesButton.clicked.connect(self.save_updates)
        self.playButton.clicked.connect(self.toggle_play)
        self.output_path = "output.csv"
        self.ui.exportButton.clicked.connect(
            lambda checked=False: self.export_csv(self.output_path)
        )
        if hasattr(self.ui, "importVideoButton"):
            self.ui.importVideoButton.clicked.connect(self.import_data)
            print("importVideoButton connected")
        if hasattr(self.ui, "importSpectralButton"):
            self.ui.importSpectralButton.clicked.connect(self.import_spectral)
            print("importSpectralButton connected")
        if hasattr(self.ui, "importFrameTimesButton"):
            self.ui.importFrameTimesButton.clicked.connect(self.import_frame_times)
            print("importFrameTimesButton connected")
        if hasattr(self.ui, "analyzeButton"):
            self.ui.analyzeButton.clicked.connect(self.analyze_data)
            print("analyzeButton connected")
        print("Signals connected")

        # Update folder path label
        self.ui.folderPathLabel.setText(f"Data folder: {Path(self.video_path).resolve().parent}")

        # Display initial data
        print("Displaying initial data...")
        self.controller.display_row(0, self.ui.videoLabel)
        print("Initial data displayed")
        print("==== MAIN VIEWER WINDOW INITIALIZATION COMPLETE ====\n")

        # Generate output file
        from output_file import generate_output_file
        generate_output_file(
            self.frame_times_path,
            self.spectral_path,
            self.metadata_path,
            Path(self.video_path).resolve().parent / "output.txt"
        )

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        # Rescale current frame to fit new label size
        self.controller.display_row(self.controller.current_row, self.ui.videoLabel)

        # Reposition folder path label to stay in top right corner
        width = self.width()
        self.ui.folderPathLabel.setGeometry(QRect(width - 360, 10, 350, 20))

    # ------------------------------------------------------------------
    # Button Actions
    # ------------------------------------------------------------------
    def next_frame(self) -> None:
        """Display the next frame."""
        # Check if we're at the last frame
        if self.controller.current_row >= len(self.controller.spectral_model.data) - 1:
            # If we're playing, stop playback
            if self.isPlaying:
                self.toggle_play()
            return

        self.controller.next_frame(self.ui.videoLabel, self.ui.metadataTable)

    def prev_frame(self) -> None:
        """Display the previous frame."""
        self.controller.prev_frame(self.ui.videoLabel, self.ui.metadataTable)

    def toggle_play(self) -> None:
        """Toggle play/stop functionality."""
        if self.isPlaying:
            # Stop playback
            self.playTimer.stop()
            self.isPlaying = False
            self.playButton.setText("Play")
        else:
            # Check if we're at the end of the data
            if self.controller.current_row >= len(self.controller.spectral_model.data) - 1:
                # Restart from the beginning
                self.controller.display_row(0, self.ui.videoLabel)
                self.controller.update_metadata_table(self.ui.metadataTable)

            # Start playback
            self.playTimer.start()
            self.isPlaying = True
            self.playButton.setText("Stop")

    def export_csv(self, path: str) -> None:
        """Export data to CSV and copy output.txt with timestamp."""
        # Export data to CSV
        self.controller.export_csv(path)

        # Copy output.txt with timestamp
        from datetime import datetime
        import shutil

        # Path to the output.txt file
        output_path = Path(self.video_path).resolve().parent / "output.txt"

        if not output_path.exists():
            QMessageBox.warning(self, "Error", f"Output file does not exist: {output_path}")
            return

        try:
            # Generate timestamp in the required format
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S.%f")[:-3]  # Format: YYYYMMDD_hhmmss.SSS

            # Create new filename
            new_filename = f"MetaData_{timestamp}.txt"
            new_path = output_path.parent / new_filename

            # Copy the file
            shutil.copy2(output_path, new_path)

            QMessageBox.information(self, "Success", f"Metadata exported to {new_filename}")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error exporting metadata: {e}")

    def import_spectral(self) -> None:
        """Import a spectral data file and refresh the current plot."""
        self.controller.import_spectral_data(self, self.ui.videoLabel)

    def import_frame_times(self) -> None:
        """Import frame time mapping for the current video."""
        self.controller.import_frame_times(self, self.ui.videoLabel)

    def save_updates(self) -> None:
        """Save updates to the output.txt file."""
        # Get the current frame number and KecmTimestamp
        frame_number = self.controller.current_frame + 1  # Frame numbers are 1-based
        current_row_index = self.controller.current_row

        if current_row_index < 0 or current_row_index >= len(self.controller.spectral_model.data):
            QMessageBox.warning(self, "Error", "No current spectral data row")
            return

        current_row = self.controller.spectral_model.get_row(current_row_index)
        current_timestamp = self.controller.spectral_model.get_timestamp(current_row)

        # Get the edited values from the metadata table
        edited_values = {}
        for col_idx in range(self.ui.metadataTable.columnCount()):
            item = self.ui.metadataTable.item(0, col_idx)  # Row 0 contains the data
            if item is None:
                continue
            header_item = self.ui.metadataTable.horizontalHeaderItem(col_idx)
            if header_item is None:
                continue
            edited_values[header_item.text()] = item.text()

        # Path to the output.txt file
        output_path = Path(self.video_path).resolve().parent / "output.txt"

        if not output_path.exists():
            QMessageBox.warning(self, "Error", f"Output file does not exist: {output_path}")
            return

        try:
            # Read the output.txt file
            import pandas as pd
            output_df = pd.read_csv(output_path)

            # Find the rows that match the current frame
            matching_rows = output_df[output_df["frame"] == frame_number]

            if matching_rows.empty:
                QMessageBox.warning(self, "Error", f"No rows found for frame {frame_number}")
                return

            # If we have a current timestamp, try to find a row with matching KecmTimestamp
            row_indices = []
            if current_timestamp and "KecmTimestamp" in matching_rows.columns:
                timestamp_matching_rows = matching_rows[matching_rows["KecmTimestamp"] == current_timestamp]
                if not timestamp_matching_rows.empty:
                    # Get the indices of the matching rows
                    row_indices = timestamp_matching_rows.index.tolist()

            # If no matching row with the same KecmTimestamp, use the first matching row by frame
            if not row_indices:
                row_indices = [matching_rows.index[0]]

            # Update the row(s) with the edited values
            for idx in row_indices:
                for col, value in edited_values.items():
                    if col in output_df.columns:
                        output_df.at[idx, col] = value

            # Save the updated file
            output_df.to_csv(output_path, index=False)

            QMessageBox.information(self, "Success", "Updates saved to output.txt")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error saving updates: {e}")

    def analyze_data(self) -> None:
        """Show first spectral row and corresponding video frame."""
        if len(self.controller.spectral_model.data) == 0 or len(self.controller.frame_times_model.frame_times) == 0:
            QMessageBox.warning(self, "Missing Data", "Import video, frame times and spectra first")
            return
        self.controller.display_row(0, self.ui.videoLabel)

    def import_data(self) -> None:
        """Select a directory containing viewer data and load it."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Data Directory",
            str(Path(self.video_path).resolve().parent),
        )
        if not directory:
            return

        base = Path(directory)
        video = base / "video.avi"
        frame_times = base / "frame_times.txt"
        spectral = base / "parsed_data.txt"
        metadata = base / "control_inputs_log.txt"

        missing = [p.name for p in (video, frame_times, spectral, metadata) if not p.exists()]
        if missing:
            QMessageBox.warning(
                self,
                "Missing Files",
                "Required data files not found: " + ", ".join(missing),
            )
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output CSV",
            str(base / "output.csv"),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not output_path:
            output_path = str(base / "output.csv")

        # Release current video capture
        self.cap.release()

        # Update paths
        self.video_path = str(video)
        self.frame_times_path = str(frame_times)
        self.spectral_path = str(spectral)
        self.metadata_path = str(metadata)
        self.output_path = output_path

        # Reinitialize video capture
        self.cap = cv2.VideoCapture(self.video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Create new controller with updated paths
        self.controller = VideoSpectraController(
            self,
            self.video_path,
            self.spectral_path,
            self.frame_times_path,
            self.metadata_path
        )

        # Display initial data
        self.controller.display_row(0, self.ui.videoLabel)
        self.controller.update_metadata_table(self.ui.metadataTable, __version__)

        # Update folder path label
        self.ui.folderPathLabel.setText(f"Data folder: {Path(self.video_path).resolve().parent}")

        # Generate output file
        from output_file import generate_output_file
        generate_output_file(
            self.frame_times_path,
            self.spectral_path,
            self.metadata_path,
            Path(self.video_path).resolve().parent / "output.txt"
        )
