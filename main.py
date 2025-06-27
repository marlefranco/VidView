"""Entry point for the Video Spectra Viewer application."""
import sys
from typing import Optional
from PyQt6.QtWidgets import QApplication

try:  # Prefer the package but fall back to the standalone module
    from viewer import MainViewerWindow  # type: ignore
except ImportError:  # package provides no MainViewerWindow
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "_viewer_module", Path(__file__).with_name("viewer.py")
    )
    if spec is None or spec.loader is None:
        raise
    _mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_mod)
    MainViewerWindow = _mod.MainViewerWindow


def main() -> int:
    """Launch the application and ensure video resources are released."""
    app = QApplication(sys.argv)
    window: Optional[MainViewerWindow] = None
    try:
        window = MainViewerWindow()
        window.show()
        return app.exec()
    finally:
        # Release the capture in case the window was closed programmatically
        if window is not None and window.cap.isOpened():
            window.cap.release()


if __name__ == "__main__":
    sys.exit(main())
