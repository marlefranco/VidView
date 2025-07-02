"""Base class for video spectra viewers."""

from __future__ import annotations

import cv2
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, QSize
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from .filters import apply_fir_filter
from .dark_reference import load_dark_reference, apply_dark_reference


class BaseViewer(QMainWindow):
    """Base class for video spectra viewers.

    This class provides common functionality for video spectra viewers,
    including video frame display, spectral plotting, and dark reference handling.

    Attributes
    ----------
    video_path : str
        Path to the video file.
    dark_reference : Dict[float, List[float]]
        Dictionary mapping integration times to dark reference data.
    cap : cv2.VideoCapture
        OpenCV video capture object.
    total_frames : int
        Total number of frames in the video.
    current_frame : int
        Index of the current frame.
    figure : Figure
        Matplotlib figure for plotting spectral data.
    canvas : FigureCanvas
        Canvas for displaying the matplotlib figure.
    """

    def __init__(self, video_path: str) -> None:
        """Initialize the base viewer.

        Parameters
        ----------
        video_path : str
            Path to the video file.
        """
        super().__init__()
        self.video_path = video_path

        # Load dark reference
        dark_path = Path(__file__).resolve().parent.parent / "darkreferencelog.txt"
        self.dark_reference = load_dark_reference(dark_path)

        # Initialize video capture
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video file {video_path}")

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0

        # Initialize matplotlib figure for spectral plotting
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self._apply_dark_theme()

    def _apply_dark_theme(self) -> None:
        """Configure the matplotlib plot with a dark theme."""
        bg_color = "#2b2b2b"
        self.figure.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)
        for spine in self.ax.spines.values():
            spine.set_color("white")
        if hasattr(self.ax, "tick_params"):
            self.ax.tick_params(colors="white", labelcolor="white")
        self.ax.set_xlabel("Wavelength", color="white")
        self.ax.set_ylabel("Intensity", color="white")

    def display_frame(self, index: int, label: Any) -> None:
        """Display the video frame at the given index.

        Parameters
        ----------
        index : int
            Index of the frame to display.
        label : Any
            QLabel or similar widget to display the frame in.
        """
        if index < 0 or index >= self.total_frames:
            return

        # Check if we're requesting the next sequential frame to avoid seeking
        if not hasattr(self, '_last_frame_index') or self._last_frame_index != index - 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        self._last_frame_index = index

        ret, frame = self.cap.read()
        if not ret:
            return

        # Convert BGR to RGB for Qt display
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, ch = rgb_image.shape
        bytes_per_line = ch * width

        # Create QImage from frame data
        qimg = QImage(
            rgb_image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )

        # Cache the label size to avoid repeated calls
        label_size = label.size()

        # Create and scale pixmap
        pixmap = QPixmap.fromImage(qimg)

        # Only scale if necessary (when the image is larger than the label)
        if (width > label_size.width() or height > label_size.height()):
            pixmap = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        label.setPixmap(pixmap)

    def plot_spectra(self, wavelengths: List[float], intensities: List[float], 
                     integration: Optional[float] = None, title: str = "") -> None:
        """Plot spectral data on the matplotlib canvas.

        Parameters
        ----------
        wavelengths : List[float]
            List of wavelength values.
        intensities : List[float]
            List of intensity values.
        integration : Optional[float], optional
            Integration time, by default None
        title : str, optional
            Plot title, by default ""
        """
        print(f"\n==== PLOT SPECTRA ====")
        print(f"plot_spectra called with {len(wavelengths)} wavelengths and {len(intensities)} intensities")
        print(f"Integration: {integration}, Title: {title}")

        # Print samples of wavelengths and intensities
        if wavelengths and intensities:
            print("Wavelength samples (first 5):")
            for i in range(min(5, len(wavelengths))):
                print(f"  {i}: {wavelengths[i]}")

            print("Intensity samples (first 5):")
            for i in range(min(5, len(intensities))):
                print(f"  {i}: {intensities[i]}")

            # Check if wavelengths are sequential indices (which would create a 45-degree line)
            if len(wavelengths) > 2:
                is_sequential = True
                increment = wavelengths[1] - wavelengths[0]
                print(f"First wavelength increment: {increment}")

                # Check a few more increments
                for i in range(1, min(5, len(wavelengths) - 1)):
                    next_increment = wavelengths[i+1] - wavelengths[i]
                    print(f"Increment {i+1}: {next_increment}")
                    if abs(next_increment - increment) > 0.01:
                        is_sequential = False
                        break

                print(f"Wavelengths appear to be sequential indices: {is_sequential}")

                # Check if intensities are all similar (which would create a 45-degree line)
                if is_sequential and len(intensities) > 2:
                    intensity_range = max(intensities) - min(intensities)
                    intensity_avg = sum(intensities) / len(intensities)
                    print(f"Intensity range: {intensity_range}, average: {intensity_avg}")
                    print(f"Range/average ratio: {intensity_range / intensity_avg if intensity_avg != 0 else 'N/A'}")

                    if intensity_range < 0.1 * intensity_avg:
                        print("WARNING: Detected potential 45-degree line pattern in data")
                        print("Wavelengths appear to be sequential indices and intensities are similar")

        self.ax.clear()
        self._apply_dark_theme()

        # Check if we have data to plot
        if not wavelengths or not intensities or len(wavelengths) != len(intensities):
            print(f"No data to plot: wavelengths={bool(wavelengths)}, intensities={bool(intensities)}, lengths match={len(wavelengths) == len(intensities) if wavelengths and intensities else False}")
            # No data or mismatched lengths, just set the title and return
            if title:
                self.ax.set_title(title, color="white")
            self.canvas.draw()
            print("No data to plot, returning")
            print("==== END PLOT SPECTRA ====\n")
            return

        # Apply dark reference correction if available
        print("Applying dark reference correction...")
        corrected_data = apply_dark_reference(intensities, integration, self.dark_reference)
        print(f"After dark reference correction: {len(corrected_data)} values")

        # Print samples of corrected data
        if corrected_data:
            print("Corrected data samples (first 5):")
            for i in range(min(5, len(corrected_data))):
                print(f"  {i}: {corrected_data[i]}")

        # Apply FIR filter for smoothing with less aggressive parameters
        print("Applying FIR filter...")
        # Increase cutoff frequency from 10 to 100 to allow more high-frequency components
        # Reduce numtaps from 101 to 51 for less smoothing
        filtered_result = apply_fir_filter([corrected_data], 2047, 100, 51)
        print(f"After FIR filtering: {len(filtered_result)} rows")

        # Check if we got a result
        if not filtered_result:
            print("No filtered result")
            # No filtered data, just set the title and return
            if title:
                self.ax.set_title(title, color="white")
            self.canvas.draw()
            print("No filtered result, returning")
            print("==== END PLOT SPECTRA ====\n")
            return

        filtered_row = filtered_result[0]
        print(f"Filtered row length: {len(filtered_row)}")

        # Print samples of filtered data
        if len(filtered_row) > 0:
            print("Filtered data samples (first 5):")
            for i in range(min(5, len(filtered_row))):
                try:
                    print(f"  {i}: {filtered_row[i]}")
                except:
                    print(f"  {i}: Error accessing filtered_row[{i}]")

        # Convert to list if it's a numpy array
        try:
            import numpy as np
            if isinstance(filtered_row, np.ndarray):
                y_plot = filtered_row.tolist()
                print("Converted numpy array to list")
            else:
                y_plot = list(filtered_row)
                print("Converted filtered_row to list")
        except (ImportError, AttributeError) as e:
            print(f"Error converting filtered_row to list: {e}")
            y_plot = list(filtered_row)

        print(f"y_plot length: {len(y_plot)}")

        # Print samples of y_plot
        if y_plot:
            print("y_plot samples (first 5):")
            for i in range(min(5, len(y_plot))):
                print(f"  {i}: {y_plot[i]}")

        # Plot the data
        line_color = "#66b3ff"
        print(f"Plotting {len(wavelengths)} wavelengths and {len(y_plot)} intensities")
        try:
            self.ax.plot(wavelengths, y_plot, color=line_color)
            print("Successfully plotted data")
        except Exception as e:
            print(f"Error plotting data: {e}")
            # Try to plot with default values if there's an error
            try:
                print("Trying to plot with default values...")
                self.ax.plot(range(len(y_plot)), y_plot, color=line_color)
                print("Successfully plotted data with default x values")
            except Exception as e2:
                print(f"Error plotting with default values: {e2}")

        # Set title with integration time if available
        if title:
            if integration is not None:
                title += f" (Integration: {integration})"
            self.ax.set_title(title, color="white")

        self.canvas.draw()
        print("Canvas drawn")
        print("==== END PLOT SPECTRA ====\n")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Release the video capture when the window is closed."""
        self.cap.release()
        super().closeEvent(event)
