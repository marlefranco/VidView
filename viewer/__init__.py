"""Video Viewer package."""

from importlib import util
from pathlib import Path


_main_viewer_cls = None


def _load_main_viewer():
    global _main_viewer_cls
    if _main_viewer_cls is None:
        spec = util.spec_from_file_location(
            "_viewer_module", Path(__file__).resolve().parent.parent / "viewer.py"
        )
        module = util.module_from_spec(spec)
        assert spec.loader is not None  # for mypy/typing
        spec.loader.exec_module(module)
        _main_viewer_cls = module.MainViewerWindow
    return _main_viewer_cls

__all__ = ["VideoSpectraViewer", "MainViewerWindow"]


def __getattr__(name: str):
    if name == "VideoSpectraViewer":
        from .video_spectra_viewer import VideoSpectraViewer
        return VideoSpectraViewer
    if name == "MainViewerWindow":

        cls = _load_main_viewer()
        globals()["MainViewerWindow"] = cls
        return cls

    raise AttributeError(name)
