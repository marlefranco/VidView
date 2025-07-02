"""Controllers for the video spectra viewer application."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

import pandas as pd
from PyQt6.QtWidgets import QTableWidgetItem, QLabel, QTableWidget, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt

from .models import SpectralDataModel, FrameTimesModel, MetadataModel
from .base_viewer import BaseViewer
from logging_config import get_logger

# Create a logger for this module
logger = get_logger("controllers")


class VideoSpectraController:
    """Controller for the video spectra viewer application.

    This class coordinates between the data models and the UI views.

    Attributes
    ----------
    spectral_model : SpectralDataModel
        Model for spectral data.
    frame_times_model : FrameTimesModel
        Model for frame times data.
    metadata_model : MetadataModel
        Model for metadata.
    view : BaseViewer
        The viewer UI.
    current_row : int
        Index of the current spectral data row.
    current_frame : int
        Index of the current video frame.
    """

    def __init__(
        self,
        view: BaseViewer,
        video_path: str,
        spectral_path: str,
        frame_times_path: str,
        metadata_path: str,
    ) -> None:
        """Initialize the controller.

        Parameters
        ----------
        view : BaseViewer
            The viewer UI.
        video_path : str
            Path to the video file.
        spectral_path : str
            Path to the spectral data file.
        frame_times_path : str
            Path to the frame times data file.
        metadata_path : str
            Path to the metadata file.
        """
        logger.debug("Initializing video spectra controller")
        logger.debug(f"Video path: {video_path}")
        logger.debug(f"Spectral path: {spectral_path}")
        logger.debug(f"Frame times path: {frame_times_path}")
        logger.debug(f"Metadata path: {metadata_path}")

        self.view = view
        logger.debug("View assigned")

        logger.debug("Initializing spectral model...")
        self.spectral_model = SpectralDataModel(spectral_path)
        logger.debug(f"Spectral model initialized with {len(self.spectral_model.data)} rows")

        # Log column names from the spectral data
        if not self.spectral_model.data.empty:
            logger.debug(f"Spectral data columns: {self.spectral_model.data.columns.tolist()}")

            # Check if any column names can be interpreted as wavelengths
            wavelength_cols = []
            for col in self.spectral_model.data.columns:
                if col == "timestamp" or col.lower() in {"integrationtime", "integration_time", "integration"}:
                    continue
                try:
                    float_val = float(col)
                    wavelength_cols.append((float_val, col))
                except (ValueError, TypeError):
                    continue

            if wavelength_cols:
                logger.debug(f"Found {len(wavelength_cols)} column names that can be interpreted as wavelengths")
                wavelength_cols.sort(key=lambda x: x[0])
                logger.debug(f"First few wavelength columns: {wavelength_cols[:5]}")
            else:
                logger.debug("No column names can be interpreted as wavelengths")
        else:
            logger.warning("Spectral data is empty")

        logger.debug("Initializing frame times model...")
        self.frame_times_model = FrameTimesModel(frame_times_path)
        logger.debug(f"Frame times model initialized with {len(self.frame_times_model.frame_times)} entries")

        # Log first few frame times
        if self.frame_times_model.frame_times:
            logger.debug("First few frame times:")
            for i, time in enumerate(self.frame_times_model.frame_times[:5]):
                logger.debug(f"  {i}: {time}")
        else:
            logger.warning("Frame times list is empty")

        logger.debug("Initializing metadata model...")
        self.metadata_model = MetadataModel(metadata_path, len(self.frame_times_model.frame_times))
        logger.debug(f"Metadata model initialized with {len(self.metadata_model.data)} rows")

        self.current_row = 0
        self.current_frame = 0
        logger.debug("Current row and frame initialized to 0")
        logger.info("Video spectra controller initialization complete")

    def display_row(self, row_index: int, video_label: QLabel) -> None:
        """Display a row of spectral data and the corresponding video frame.

        Parameters
        ----------
        row_index : int
            Index of the spectral data row to display.
        video_label : QLabel
            Label to display the video frame in.
        """
        print(f"\n==== DISPLAY ROW {row_index} ====")
        print(f"display_row called with row_index={row_index}")
        print(f"Current spectral data has {len(self.spectral_model.data)} rows")
        print(f"Current frame times has {len(self.frame_times_model.frame_times)} entries")

        if row_index < 0 or row_index >= len(self.spectral_model.data):
            print(f"Row index {row_index} out of bounds for data with {len(self.spectral_model.data)} rows")
            return

        # Get the spectral data row
        row = self.spectral_model.get_row(row_index)
        print(f"Got row with index {row_index}")
        print(f"Row index names: {row.index.tolist()}")

        # Print a sample of the row values
        sample_values = {}
        for i, (idx, val) in enumerate(row.items()):
            if i < 5 or i >= len(row) - 5:  # First 5 and last 5 values
                sample_values[idx] = val
            if i == 5 and len(row) > 10:
                sample_values["..."] = "..."
        print(f"Row sample values: {sample_values}")

        # Get the timestamp and find the corresponding frame
        timestamp = self.spectral_model.get_timestamp(row)
        print(f"Timestamp: {timestamp}")
        frame_index = self.frame_times_model.find_nearest_frame_index(timestamp)
        print(f"Found nearest frame index: {frame_index}")

        # Update current indices
        self.current_row = row_index
        self.current_frame = frame_index

        # Display the frame
        self.view.display_frame(frame_index, video_label)
        print(f"Displayed frame {frame_index}")

        # Extract and plot spectral data
        print("Extracting wavelengths and intensities...")
        wavelengths, intensities = self.spectral_model.get_wavelengths_and_intensities(row)
        print(f"Extracted {len(wavelengths)} wavelengths and {len(intensities)} intensities")

        # Print a sample of the wavelengths and intensities
        if wavelengths and intensities:
            print("Wavelength samples:")
            for i in range(min(5, len(wavelengths))):
                print(f"  {i}: {wavelengths[i]}")
            if len(wavelengths) > 10:
                print("  ...")
            for i in range(max(5, len(wavelengths) - 5), len(wavelengths)):
                print(f"  {i}: {wavelengths[i]}")

            print("Intensity samples:")
            for i in range(min(5, len(intensities))):
                print(f"  {i}: {intensities[i]}")
            if len(intensities) > 10:
                print("  ...")
            for i in range(max(5, len(intensities) - 5), len(intensities)):
                print(f"  {i}: {intensities[i]}")
        else:
            print("No wavelengths or intensities extracted")

        integration = self.spectral_model.get_integration_time(row)
        print(f"Integration time: {integration}")

        # Clean up timestamp to ensure it doesn't contain data headers or spectral data
        # If timestamp is too long, it might contain data that shouldn't be in the title
        if len(timestamp) > 30:
            timestamp = timestamp[:30] + "..."

        title = f"Spectrum at {timestamp}"
        subtitle = (
            f"Spec Row {row_index + 1}/{len(self.spectral_model.data)} "
            f"Frame {frame_index + 1}/{len(self.frame_times_model.frame_times)}"
        )
        print(f"Plotting with title: {title}\n{subtitle}")
        self.view.plot_spectra(wavelengths, intensities, integration, f"{title}\n{subtitle}")
        print("Finished display_row")
        print("==== END DISPLAY ROW ====\n")

    def update_metadata_table(self, table_widget: QTableWidget, version: str = "") -> None:
        """Update the metadata table with the current frame's metadata from output.txt.

        Parameters
        ----------
        table_widget : QTableWidget
            Table widget to update.
        version : str, optional
            Version string to display in the header, by default ""
            (This parameter is kept for backward compatibility but no longer used)
        """
        print(f"\n==== UPDATE METADATA TABLE ====")
        # Set table to have 1 row for data
        table_widget.setRowCount(1)

        # Get the current frame number (1-based)
        frame_number = self.current_frame + 1
        print(f"Current frame number: {frame_number}")

        # Get the current spectral data row's KecmTimestamp
        current_row_index = self.current_row
        if current_row_index >= 0 and current_row_index < len(self.spectral_model.data):
            current_row = self.spectral_model.get_row(current_row_index)
            current_timestamp = self.spectral_model.get_timestamp(current_row)
            print(f"Current spectral data row index: {current_row_index}")
            print(f"Current spectral data KecmTimestamp: {current_timestamp}")
        else:
            current_timestamp = None
            print(f"No current spectral data row (index: {current_row_index})")

        # Path to the output.txt file
        output_path = Path(self.view.video_path).resolve().parent / "output.txt"
        print(f"Output path: {output_path}")

        if not output_path.exists():
            print(f"Output file does not exist: {output_path}")
            # Fall back to the original metadata if output.txt doesn't exist
            metadata = self.metadata_model.get_row(self.current_frame)

            # Set column count and headers
            table_widget.setColumnCount(len(metadata.index))
            table_widget.setHorizontalHeaderLabels(list(metadata.index))

            # Add metadata in row 0
            for col_idx, col in enumerate(metadata.index):
                item = QTableWidgetItem(str(metadata[col]))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Make the item editable
                table_widget.setItem(0, col_idx, item)
            print("Using original metadata (output file not found)")
            print("==== END UPDATE METADATA TABLE ====\n")
            return

        try:
            # Read the output.txt file
            print(f"Reading output file: {output_path}")
            output_df = pd.read_csv(output_path)
            print(f"Output file has {len(output_df)} rows and {len(output_df.columns)} columns")

            # Find the rows that match the current frame
            matching_rows = output_df[output_df["frame"] == frame_number]
            print(f"Found {len(matching_rows)} rows matching frame {frame_number}")

            if matching_rows.empty:
                print(f"No rows found for frame {frame_number}")
                # Fall back to the original metadata if no matching rows are found
                metadata = self.metadata_model.get_row(self.current_frame)

                # Set column count and headers
                table_widget.setColumnCount(len(metadata.index))
                table_widget.setHorizontalHeaderLabels(list(metadata.index))

                # Add metadata in row 0
                for col_idx, col in enumerate(metadata.index):
                    item = QTableWidgetItem(str(metadata[col]))
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Make the item editable
                    table_widget.setItem(0, col_idx, item)
                print("Using original metadata (no matching rows)")
                print("==== END UPDATE METADATA TABLE ====\n")
                return

            # If we have a current timestamp, try to find a row with matching KecmTimestamp
            row_data = None
            if current_timestamp and "KecmTimestamp" in matching_rows.columns:
                timestamp_matching_rows = matching_rows[matching_rows["KecmTimestamp"] == current_timestamp]
                print(f"Found {len(timestamp_matching_rows)} rows matching both frame {frame_number} and KecmTimestamp {current_timestamp}")
                if not timestamp_matching_rows.empty:
                    row_data = timestamp_matching_rows.iloc[0]
                    print(f"Using row data for frame {frame_number} and KecmTimestamp {current_timestamp}")

            # If no matching row with the same KecmTimestamp, use the first matching row by frame
            if row_data is None:
                row_data = matching_rows.iloc[0]
                print(f"Using first row data for frame {frame_number}")

            # Set column count and headers
            table_widget.setColumnCount(len(row_data.index))
            table_widget.setHorizontalHeaderLabels(list(row_data.index))

            # Add row data to the table
            for col_idx, col in enumerate(row_data.index):
                item = QTableWidgetItem(str(row_data[col]))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Make the item editable
                table_widget.setItem(0, col_idx, item)

            print(f"Updated table with {len(row_data.index)} columns from output file")
            print("==== END UPDATE METADATA TABLE ====\n")

        except Exception as e:
            print(f"Error reading output.txt: {e}")
            # Fall back to the original metadata if there's an error
            metadata = self.metadata_model.get_row(self.current_frame)

            # Set column count and headers
            table_widget.setColumnCount(len(metadata.index))
            table_widget.setHorizontalHeaderLabels(list(metadata.index))

            # Add metadata in row 0
            for col_idx, col in enumerate(metadata.index):
                item = QTableWidgetItem(str(metadata[col]))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Make the item editable
                table_widget.setItem(0, col_idx, item)
            print("Using original metadata (error reading output file)")
            print("==== END UPDATE METADATA TABLE ====\n")

    def save_metadata_from_table(self, table_widget: QTableWidget) -> None:
        """Save metadata from the table to the model.

        Parameters
        ----------
        table_widget : QTableWidget
            Table widget containing the metadata.
        """
        values = {}
        for col_idx in range(table_widget.columnCount()):
            item = table_widget.item(0, col_idx)  # Row 0 contains the data (no header row anymore)
            if item is None:
                continue
            header_item = table_widget.horizontalHeaderItem(col_idx)
            if header_item is None:
                continue
            values[header_item.text()] = item.text()

        self.metadata_model.update_row(self.current_frame, values)

    def next_frame(self, video_label: QLabel, table_widget: QTableWidget) -> None:
        """Display the next frame.

        Parameters
        ----------
        video_label : QLabel
            Label to display the video frame in.
        table_widget : QTableWidget
            Table widget containing the metadata.
        """
        print(f"\n==== NEXT FRAME ====")
        print(f"Current row: {self.current_row}, Total rows: {len(self.spectral_model.data)}")

        if self.current_row < len(self.spectral_model.data) - 1:
            print(f"Moving to next row: {self.current_row + 1}")
            self.save_metadata_from_table(table_widget)
            self.current_row += 1
            self.display_row(self.current_row, video_label)
            self.update_metadata_table(table_widget)
        else:
            print(f"Already at last row, cannot move to next frame")

        print(f"==== END NEXT FRAME ====\n")

    def prev_frame(self, video_label: QLabel, table_widget: QTableWidget) -> None:
        """Display the previous frame.

        Parameters
        ----------
        video_label : QLabel
            Label to display the video frame in.
        table_widget : QTableWidget
            Table widget containing the metadata.
        """
        print(f"\n==== PREV FRAME ====")
        print(f"Current row: {self.current_row}, Total rows: {len(self.spectral_model.data)}")

        if self.current_row > 0:
            print(f"Moving to previous row: {self.current_row - 1}")
            self.save_metadata_from_table(table_widget)
            self.current_row -= 1
            self.display_row(self.current_row, video_label)
            self.update_metadata_table(table_widget)
        else:
            print(f"Already at first row, cannot move to previous frame")

        print(f"==== END PREV FRAME ====\n")

    def export_csv(self, path: str) -> None:
        """Export data to a CSV file.

        Parameters
        ----------
        path : str
            Path to save the CSV file to.
        """
        from output_writer import write_csv
        write_csv(
            path, 
            self.frame_times_model.frame_times, 
            self.spectral_model.data, 
            self.metadata_model.data
        )

    def import_spectral_data(self, parent_widget: Any, video_label: QLabel) -> None:
        """Import spectral data from a file.

        Parameters
        ----------
        parent_widget : Any
            Parent widget for the file dialog.
        video_label : QLabel
            Label to display the video frame in.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Open Spectral Data",
            str(Path(self.spectral_model.data_path).resolve().parent),
            "Text Files (*.txt *.csv);;All Files (*)",
        )
        if not file_path:
            return
        try:
            self.spectral_model = SpectralDataModel(file_path)
        except Exception as exc:
            QMessageBox.warning(parent_widget, "Error Loading Data", str(exc))
            return
        self.display_row(self.current_row, video_label)

    def import_frame_times(self, parent_widget: Any, video_label: QLabel) -> None:
        """Import frame times from a file.

        Parameters
        ----------
        parent_widget : Any
            Parent widget for the file dialog.
        video_label : QLabel
            Label to display the video frame in.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Open Frame Times",
            str(Path(self.frame_times_model.data_path).resolve().parent),
            "Text Files (*.txt *.csv);;All Files (*)",
        )
        if not file_path:
            return
        try:
            self.frame_times_model = FrameTimesModel(file_path)
            # Update metadata model with new frame count
            self.metadata_model = MetadataModel(
                self.metadata_model.data_path, 
                len(self.frame_times_model.frame_times)
            )
        except Exception as exc:
            QMessageBox.warning(parent_widget, "Error Loading Data", str(exc))
            return

        # Reset to first frame if current frame is out of bounds
        if self.current_frame >= len(self.frame_times_model.frame_times):
            self.current_frame = 0
            self.current_row = 0

        self.display_row(self.current_row, video_label)
