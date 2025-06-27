"""Qt window for displaying video frames with spectral information."""
from __future__ import annotations

import cv2
from datetime import datetime
from ui.main_window import Ui_MainViewerWindow

from PyQt6.QtWidgets import (
    QMainWindow,
    QTableWidgetItem,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
)
from pathlib import Path
from PyQt6.QtGui import QImage, QPixmap
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from data_handler import parse_frame_times, parse_spectral_data, parse_metadata
from output_writer import write_csv
from ui.main_window import Ui_MainViewerWindow
from constants import TS_FORMAT


class MainViewerWindow(QMainWindow):
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
        super().__init__()
        self.ui = Ui_MainViewerWindow()
        self.ui.setupUi(self)

        self.video_path = video_path
        self.frame_times_path = frame_times_path
        self.spectral_path = spectral_path
        self.metadata_path = metadata_path

        self.cap = cv2.VideoCapture(self.video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0

        self.frame_times = parse_frame_times(self.frame_times_path)
        self.spectral_df = parse_spectral_data(self.spectral_path)
        self.metadata_df = parse_metadata(self.metadata_path, len(self.frame_times))

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        plot_layout = self.ui.plotWidget.layout()
        if plot_layout is None:
            plot_layout = QVBoxLayout(self.ui.plotWidget)
        plot_layout.addWidget(self.canvas)

        self.ui.nextButton.clicked.connect(self.next_frame)
        self.ui.prevButton.clicked.connect(self.prev_frame)
        self.ui.exportButton.clicked.connect(lambda checked=False: self.export_csv())
        if hasattr(self.ui, "importVideoButton"):
            self.ui.importVideoButton.clicked.connect(self.import_video)
        if hasattr(self.ui, "importSpectralButton"):
            self.ui.importSpectralButton.clicked.connect(self.import_spectral)
        if hasattr(self.ui, "importFrameTimesButton"):
            self.ui.importFrameTimesButton.clicked.connect(self.import_frame_times)
        if hasattr(self.ui, "analyzeButton"):
            self.ui.analyzeButton.clicked.connect(self.analyze_data)

        self.display_frame(0)

    # ------------------------------------------------------------------
    # Data Import Actions
    # ------------------------------------------------------------------
    def import_spectral(self) -> None:
        """Import a spectral data file and refresh the current plot."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Spectral Data",
            str(Path(self.spectral_path).resolve().parent),
            "Text Files (*.txt *.csv);;All Files (*)",
        )
        if not file_path:
            return
        try:
            self.spectral_df = parse_spectral_data(file_path)
        except Exception as exc:
            QMessageBox.warning(self, "Error Loading Data", str(exc))
            return
        self.spectral_path = file_path
        self.update_spectrum(self.current_frame)

    def import_frame_times(self) -> None:
        """Import frame time mapping for the current video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Frame Times",
            str(Path(self.frame_times_path).resolve().parent),
            "Text Files (*.txt *.csv);;All Files (*)",
        )
        if not file_path:
            return
        try:
            self.frame_times = parse_frame_times(file_path)
        except Exception as exc:
            QMessageBox.warning(self, "Error Loading Data", str(exc))
            return
        self.frame_times_path = file_path
        self.total_frames = len(self.frame_times)
        if self.current_frame >= self.total_frames:
            self.current_frame = 0
        self.display_frame(self.current_frame)

    def analyze_data(self) -> None:
        """Show first spectral row and corresponding video frame."""
        if self.spectral_df.empty or not self.frame_times:
            QMessageBox.warning(self, "Missing Data", "Import video, frame times and spectra first")
            return
        first_row = self.spectral_df.iloc[0]
        ts = str(first_row["timestamp"])
        target = datetime.strptime(ts, TS_FORMAT)
        times = [datetime.strptime(t, TS_FORMAT) for t in self.frame_times]
        diffs = [abs(t - target) for t in times]
        frame_index = diffs.index(min(diffs))
        self.current_frame = frame_index
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.cap.read()
        if ret:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            qimg = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
            self.ui.videoLabel.setPixmap(QPixmap.fromImage(qimg))
        self.ax.clear()
        self._plot_spectra(first_row)
        self.ax.set_title("First Spectral Row")
        self.canvas.draw()
        self.update_metadata_table(frame_index)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Release the video capture when the window is closed."""
        self.cap.release()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # UI updates
    # ------------------------------------------------------------------
    def display_frame(self, index: int) -> None:
        if index < 0 or index >= self.total_frames:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ret, frame = self.cap.read()
        if not ret:
            return
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, ch = rgb_image.shape
        bytes_per_line = ch * width
        qimg = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        self.ui.videoLabel.setPixmap(QPixmap.fromImage(qimg))
        self.update_spectrum(index)
        self.update_metadata_table(index)

    def update_spectrum(self, index: int) -> None:
        frame_time = self.frame_times[index]
        row = self._find_nearest_spectral_row(frame_time)
        self.ax.clear()
        self._plot_spectra(row)
        self.ax.set_title(f"Spectrum @ Frame {index}")
        self.canvas.draw()

    def update_metadata_table(self, index: int) -> None:
        self.ui.metadataTable.setRowCount(1)
        self.ui.metadataTable.setColumnCount(len(self.metadata_df.columns))
        self.ui.metadataTable.setHorizontalHeaderLabels(list(self.metadata_df.columns))
        for col_idx, col in enumerate(self.metadata_df.columns):
            item = QTableWidgetItem(str(self.metadata_df.iloc[index, col_idx]))
            self.ui.metadataTable.setItem(0, col_idx, item)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def next_frame(self) -> None:
        if self.current_frame < self.total_frames - 1:
            self._save_current_metadata()
            self.current_frame += 1
            self.display_frame(self.current_frame)

    def prev_frame(self) -> None:
        if self.current_frame > 0:
            self._save_current_metadata()
            self.current_frame -= 1
            self.display_frame(self.current_frame)

    def _find_nearest_spectral_row(self, frame_time: str) -> pd.Series:
        """Return row in ``spectral_df`` closest to ``frame_time``."""
        target = datetime.strptime(frame_time, TS_FORMAT)
        timestamps = self.spectral_df["timestamp"].apply(
            lambda s: datetime.strptime(str(s), TS_FORMAT)
        )
        diffs = (timestamps - target).abs()
        return self.spectral_df.loc[diffs.idxmin()]

    def _plot_spectra(self, spectra_row) -> None:
        """Plot spectra with wavelengths sorted numerically.

        Some spectral files include additional columns (e.g. ``eventID``)
        that are not numeric wavelengths.  Attempting to convert those
        column names to ``float`` will raise ``ValueError`` which in turn
        prevents the plot from rendering.  Here we silently skip any
        non-numeric columns so the viewer can handle a wider range of
        input files.
        """
        keys = []
        for k in spectra_row.index:
            if k == "timestamp":
                continue
            try:
                float(k)
            except ValueError:
                continue
            keys.append(k)
        keys = sorted(keys, key=float)
        values = [float(spectra_row[k]) for k in keys]
        self.ax.plot([float(k) for k in keys], values)

    def _save_current_metadata(self) -> None:
        for col_idx, col in enumerate(self.metadata_df.columns):
            item = self.ui.metadataTable.item(0, col_idx)
            if item is not None:
                self.metadata_df.at[self.current_frame, col] = item.text()

    def export_csv(self, path: str = "output.csv") -> None:
        write_csv(path, self.frame_times, self.spectral_df, self.metadata_df)

    def import_video(self) -> None:
        """Open a dialog to select a new dataset and load it."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            str(Path(self.video_path).resolve().parent),
            "Video Files (*.avi *.mp4 *.mov *.mkv);;All Files (*)",
        )
        if not file_path:
            return

        base = Path(file_path).resolve().parent
        frame_times = base / "frame_times.txt"
        spectral = base / "parsed_data.txt"
        metadata = base / "control_inputs_log.txt"

        missing = [p.name for p in (frame_times, spectral, metadata) if not p.exists()]
        if missing:
            QMessageBox.warning(
                self,
                "Missing Files",
                "Required data files not found: " + ", ".join(missing),
            )
            return

        try:
            new_frame_times = parse_frame_times(str(frame_times))
            new_spectral_df = parse_spectral_data(str(spectral))
            new_metadata_df = parse_metadata(str(metadata), len(new_frame_times))
        except Exception as exc:  # catch parsing errors
            QMessageBox.warning(self, "Error Loading Data", str(exc))
            return

        self.cap.release()
        self.video_path = file_path
        self.frame_times_path = str(frame_times)
        self.spectral_path = str(spectral)
        self.metadata_path = str(metadata)

        self.cap = cv2.VideoCapture(self.video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0

        self.frame_times = new_frame_times
        self.spectral_df = new_spectral_df
        self.metadata_df = new_metadata_df

        self.display_frame(0)


