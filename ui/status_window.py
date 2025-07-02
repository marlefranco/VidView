from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, QTimer

class StatusWindow(QDialog):
    """A simple status window to show progress while the application is loading."""

    def __init__(self, parent=None):
        """Initialize the status window."""
        super().__init__(parent)
        self.setWindowTitle("Video Spectra Viewer - Loading")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.CustomizeWindowHint)

        # Create layout
        layout = QVBoxLayout(self)

        # Add status label
        self.status_label = QLabel("Initializing application...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)

        # Center the window on the screen
        self.center_on_screen()

    def center_on_screen(self):
        """Center the window on the screen."""
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def update_status(self, message):
        """Update the status message."""
        self.status_label.setText(message)
        # Process events to update the UI
        QApplication.processEvents()
