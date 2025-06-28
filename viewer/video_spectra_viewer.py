"""GUI application to view video frames alongside spectral data."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import List, Dict, Iterable, Any, Optional
from pathlib import Path

import cv2
import matplotlib
try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - numpy optional
    np = None  # type: ignore
try:  # optional SciPy dependency
    from scipy.signal import firwin, lfilter  # type: ignore
except Exception:  # pragma: no cover - fallback if SciPy missing
    firwin = None
    lfilter = None
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6 import QtCore, QtGui, QtWidgets

from .data_utils import read_csv_file, nearest_by_timestamp

# Ensure using non-interactive backend for embedding in PyQt6

matplotlib.use("Agg")


def apply_fir_filter(
    data: Iterable[Iterable[float]],
    sample_rate: float,
    cutoff_freq: float,
    numtaps: int = 100,
) -> Any:
    """Applies an FIR filter to smooth spectral data."""

    rows = [list(map(float, row)) for row in data]

    if np is not None and firwin is not None and lfilter is not None:
        arr = np.asarray(rows, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        nyquist_rate = sample_rate / 2.0
        fir_coeff = firwin(numtaps, cutoff_freq / nyquist_rate)
        return np.apply_along_axis(
            lambda row: lfilter(fir_coeff, 1.0, row), axis=1, arr=arr
        )

    coeffs = [1.0 / numtaps] * numtaps

    def smooth_row(row: List[float]) -> List[float]:
        padding = numtaps // 2
        padded = [row[0]] * padding + row + [row[-1]] * padding
        result = []
        for i in range(len(row)):
            window = padded[i : i + numtaps]
            result.append(sum(c * x for c, x in zip(coeffs, window)))
        return result

    return [smooth_row(row) for row in rows]




@dataclass
class FrameMetadata:
    """Metadata associated with a single video frame."""

    timestamp: float
    controls: Dict[str, float] = field(default_factory=dict)


class VideoSpectraViewer(QtWidgets.QMainWindow):
    """Main window displaying video frames with spectral data."""

    def __init__(self, video_path: str, spectra_path: str, control_log_path: str | None = None):
        super().__init__()
        self.video_path = video_path
        self.spectra_data = read_csv_file(spectra_path)
        self.control_log: List[FrameMetadata] = []
        dark_path = Path(__file__).resolve().parent.parent / "darkreferencelog.txt"
        self.dark_reference = self._load_dark_reference(dark_path)

        if control_log_path and os.path.exists(control_log_path):
            raw_logs = read_csv_file(control_log_path)
            for row in raw_logs:
                timestamp = row.pop("timestamp")
                self.control_log.append(FrameMetadata(timestamp, row))

        self.video = cv2.VideoCapture(video_path)
        if not self.video.isOpened():
            raise RuntimeError(f"Could not open video file {video_path}")

        self.total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.video.get(cv2.CAP_PROP_FPS)
        self.current_frame_index = 0

        self._init_ui()
        self._update_display()

    # -------------------------- UI Setup --------------------------
    def _init_ui(self) -> None:
        self.setWindowTitle("Video Spectra Viewer")
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QVBoxLayout(central_widget)

        video_plot_layout = QtWidgets.QHBoxLayout()

        # Video display
        self.video_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        video_plot_layout.addWidget(self.video_label)

        # Spectra plot
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        video_plot_layout.addWidget(self.canvas)

        # apply a dark theme to the plot area
        bg_color = "#2b2b2b"
        self.figure.set_facecolor(bg_color)
        self.canvas.setStyleSheet(f"background-color: {bg_color};")

        video_plot_layout.setStretch(0, 1)
        video_plot_layout.setStretch(1, 1)
        layout.addLayout(video_plot_layout)

        # Controls and metadata
        controls_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(controls_layout)

        self.prev_button = QtWidgets.QPushButton("Previous")
        self.prev_button.clicked.connect(self.show_prev_frame)
        controls_layout.addWidget(self.prev_button)

        self.next_button = QtWidgets.QPushButton("Next")
        self.next_button.clicked.connect(self.show_next_frame)
        controls_layout.addWidget(self.next_button)

        self.save_button = QtWidgets.QPushButton("Save CSV")
        self.save_button.clicked.connect(self.save_metadata)
        controls_layout.addWidget(self.save_button)

        # Metadata table (editable)
        self.meta_table = QtWidgets.QTableWidget()
        controls_layout.addWidget(self.meta_table)

        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

    # -------------------------- Frame Display Logic --------------------------
    def _update_display(self) -> None:
        """Load and display the current frame and corresponding spectra."""
        self.video.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_index)
        ret, frame = self.video.read()
        if not ret:
            self.status_bar.showMessage("Failed to read frame")
            return

        # Convert BGR to RGB for Qt
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QtGui.QImage(
            frame_rgb.data,
            w,
            h,
            bytes_per_line,
            QtGui.QImage.Format.Format_RGB888,
        )
        pixmap = QtGui.QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap)

        timestamp = self.current_frame_index / self.fps
        spectra = self._get_nearest_spectra(timestamp)
        self._plot_spectra(spectra)
        self._update_metadata_table(timestamp)

        self.status_bar.showMessage(f"Frame {self.current_frame_index+1}/{self.total_frames}")

    def _get_nearest_spectra(self, timestamp: float) -> Dict[str, float]:
        """Return spectral row with timestamp closest to ``timestamp``."""

        return nearest_by_timestamp(self.spectra_data, timestamp)

    def _load_dark_reference(self, path: Path) -> Dict[float, List[float]]:
        """Load dark reference data keyed by integration time."""
        if not path.exists():
            return {}
        data: Dict[float, List[float]] = {}
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                integration: Optional[float] = None
                intensities: List[float] = []
                for key, value in row.items():
                    lname = key.lower().replace(" ", "")
                    if lname in {"integrationtime", "integration_time", "integration"}:
                        try:
                            integration = float(value)
                        except (TypeError, ValueError):
                            integration = None
                    elif lname != "timestamp":
                        try:
                            intensities.append(float(value))
                        except (TypeError, ValueError):
                            intensities.append(float("nan"))
                if integration is not None:
                    data[integration] = intensities
        return data

    def _plot_spectra(self, spectra: Dict[str, float]) -> None:
        """Plot spectral data on matplotlib canvas."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        bg_color = "#2b2b2b"
        line_color = "#66b3ff"

        if hasattr(ax, "set_facecolor"):
            ax.set_facecolor(bg_color)

        x = [k for k in spectra.keys() if k != "timestamp" and "integration" not in k.lower()]
        y = [spectra[k] for k in x]

        integration = None
        for key in spectra:
            lowered = key.lower().replace(" ", "")
            if lowered in {"integrationtime", "integration_time", "integration"}:
                integration = spectra.get(key)
                break

        dark = None
        if integration is not None:
            dark_map = getattr(self, "dark_reference", {})
            if isinstance(dark_map, dict):
                dark = dark_map.get(float(integration))
        if dark and len(dark) == len(y):
            data_subtracted = [val - d for val, d in zip(y, dark)]
        else:
            data_subtracted = y

        filtered_result = apply_fir_filter([data_subtracted], 2047, 10, 101)
        filtered_row = filtered_result[0]
        if np is not None and hasattr(filtered_row, "tolist"):
            y_plot = filtered_row.tolist()
        else:
            y_plot = list(filtered_row)
        ax.plot(x, y_plot, marker="o", color=line_color)
        ax.set_xlabel("Wavelength", color="white")
        ax.set_ylabel("Intensity", color="white")
        if hasattr(ax, "tick_params"):
            ax.tick_params(colors="white", labelcolor="white")
        for spine in getattr(ax, "spines", {}).values():
            spine.set_color("white")

        title = f"Timestamp: {spectra['timestamp']:.2f}s"
        if integration is not None and integration == integration:
            title += f" | Integration: {integration}"

        ax.set_title(title)
        if hasattr(ax, "title") and hasattr(ax.title, "set_color"):
            ax.title.set_color("white")
        self.canvas.draw()

    # -------------------------- Metadata Handling --------------------------
    def _update_metadata_table(self, timestamp: float) -> None:
        """Display metadata for the current frame."""
        # Ensure we have metadata entry for this frame
        if self.current_frame_index >= len(self.control_log):
            self.control_log.append(FrameMetadata(timestamp, {}))

        metadata = self.control_log[self.current_frame_index]
        metadata.timestamp = timestamp

        self.meta_table.clear()
        self.meta_table.setRowCount(1)
        self.meta_table.setColumnCount(len(metadata.controls) or 1)
        self.meta_table.setVerticalHeaderLabels(["Value"])
        self.meta_table.setHorizontalHeaderLabels(list(metadata.controls.keys()) or ["No Controls"])

        for col, key in enumerate(metadata.controls.keys()):
            item = QtWidgets.QTableWidgetItem(str(metadata.controls[key]))
            self.meta_table.setItem(0, col, item)

        self.meta_table.resizeColumnsToContents()

    def _save_metadata_from_table(self) -> None:
        """Store edited metadata back into control_log."""
        metadata = self.control_log[self.current_frame_index]
        updated: Dict[str, float] = {}
        for col in range(self.meta_table.columnCount()):
            item = self.meta_table.item(0, col)
            header_item = self.meta_table.horizontalHeaderItem(col)
            if item is None or header_item is None:
                continue
            try:
                updated[header_item.text()] = float(item.text())
            except ValueError:
                self.status_bar.showMessage(f"Invalid value in column '{header_item.text()}'")
        metadata.controls = updated

    # -------------------------- Button Actions --------------------------
    def show_next_frame(self) -> None:
        self._save_metadata_from_table()
        if self.current_frame_index < self.total_frames - 1:
            self.current_frame_index += 1
            self._update_display()

    def show_prev_frame(self) -> None:
        self._save_metadata_from_table()
        if self.current_frame_index > 0:
            self.current_frame_index -= 1
            self._update_display()

    def save_metadata(self) -> None:
        self._save_metadata_from_table()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save CSV", "metadata.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as csvfile:
                if not self.control_log:
                    return

                # Gather the union of all control keys
                all_keys = set()
                for meta in self.control_log:
                    all_keys.update(meta.controls.keys())

                fieldnames = ["timestamp"] + sorted(all_keys)
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for meta in self.control_log:
                    row = {"timestamp": meta.timestamp}
                    for key in all_keys:
                        row[key] = meta.controls.get(key, "")
                    writer.writerow(row)
        except OSError as exc:
            self.status_bar.showMessage(f"Failed to save file: {exc}")
        else:
            self.status_bar.showMessage(f"Saved metadata to {path}")


# -------------- Entry Point --------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Video and Spectra Viewer")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("spectra", help="Path to spectral data CSV")
    parser.add_argument("--controls", help="Path to control inputs log", default=None)
    args = parser.parse_args()

    app = QtWidgets.QApplication([])
    viewer = VideoSpectraViewer(args.video, args.spectra, args.controls)
    viewer.show()
    app.exec()


if __name__ == "__main__":
    main()
