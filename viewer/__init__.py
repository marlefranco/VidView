"""Video Viewer package.

This package provides classes for viewing video frames alongside spectral data.
"""

__version__ = "1.0.0"  # Version 1

# Import public classes
from .main_viewer import MainViewerWindow
from .video_spectra_viewer import VideoSpectraViewer
from .base_viewer import BaseViewer
from .models import SpectralDataModel, FrameTimesModel, MetadataModel
from .controllers import VideoSpectraController
from .filters import apply_fir_filter
from .dark_reference import load_dark_reference, apply_dark_reference

# Define public API
__all__ = [
    "MainViewerWindow",
    "VideoSpectraViewer",
    "BaseViewer",
    "SpectralDataModel",
    "FrameTimesModel",
    "MetadataModel",
    "VideoSpectraController",
    "apply_fir_filter",
    "load_dark_reference",
    "apply_dark_reference",
    "__version__",
]
