"""Qt window for displaying video frames with spectral information.

This module is maintained for backward compatibility.
The actual implementation has been moved to the viewer package.
"""
from __future__ import annotations

# Import from the viewer package
from viewer.main_viewer import MainViewerWindow
from viewer.filters import apply_fir_filter
from viewer import __version__

# This file is kept for backward compatibility only.
# All functionality has been moved to the viewer package.
