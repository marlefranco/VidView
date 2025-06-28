import sys
import types
import importlib


def load_viewer(monkeypatch):
    class DummyWindow:  # minimal stub for QMainWindow
        pass

    qtwidgets = types.SimpleNamespace(
        QFileDialog=types.SimpleNamespace(getSaveFileName=lambda *a, **k: ("", None)),
        QMainWindow=DummyWindow,
        QLabel=object,
        QTableWidget=object,
        QPushButton=object,
        QStatusBar=object,
        QWidget=object,
        QVBoxLayout=object,
        QHBoxLayout=object,
    )
    qtcore = types.SimpleNamespace(Qt=types.SimpleNamespace(AlignCenter=0))
    qtgui = types.SimpleNamespace(QImage=object, QPixmap=object)
    monkeypatch.setitem(
        sys.modules,
        "cv2",
        types.SimpleNamespace(VideoCapture=lambda *a, **k: types.SimpleNamespace(isOpened=lambda: True, get=lambda *args: 0, read=lambda: (False, None))),
    )
    monkeypatch.setitem(sys.modules, "PyQt6", types.SimpleNamespace(QtCore=qtcore, QtGui=qtgui, QtWidgets=qtwidgets))
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, "PyQt6.QtGui", qtgui)
    monkeypatch.setitem(sys.modules, "PyQt6.QtWidgets", qtwidgets)
    monkeypatch.setitem(sys.modules, "matplotlib", types.SimpleNamespace(use=lambda *a, **k: None))
    monkeypatch.setitem(sys.modules, "matplotlib.backends.backend_qtagg", types.SimpleNamespace(FigureCanvasQTAgg=object))
    monkeypatch.setitem(sys.modules, "matplotlib.figure", types.SimpleNamespace(Figure=object))

    module = importlib.import_module("viewer.video_spectra_viewer")
    return module.VideoSpectraViewer, module.FrameMetadata


def test_get_nearest_spectra(monkeypatch):
    VideoSpectraViewer, _ = load_viewer(monkeypatch)
    viewer = VideoSpectraViewer.__new__(VideoSpectraViewer)
    viewer.spectra_data = [
        {"timestamp": 0.0, "a": 1},
        {"timestamp": 1.0, "a": 2},
        {"timestamp": 2.0, "a": 3},
    ]
    result = viewer._get_nearest_spectra(1.4)
    assert result["timestamp"] == 1.0


def test_show_next_frame_calls_update(monkeypatch):
    VideoSpectraViewer, FrameMetadata = load_viewer(monkeypatch)
    viewer = VideoSpectraViewer.__new__(VideoSpectraViewer)
    viewer.current_frame_index = 0
    viewer.total_frames = 3
    viewer.control_log = [FrameMetadata(0.0, {})]

    called = {}
    monkeypatch.setattr(viewer, "_save_metadata_from_table", lambda: called.setdefault("save", True))
    monkeypatch.setattr(viewer, "_update_display", lambda: called.setdefault("update", True))

    viewer.show_next_frame()

    assert viewer.current_frame_index == 1
    assert called.get("update")


def test_plot_title_includes_integration_time(monkeypatch):
    VideoSpectraViewer, _ = load_viewer(monkeypatch)
    viewer = VideoSpectraViewer.__new__(VideoSpectraViewer)

    captured = {}
    axis = types.SimpleNamespace(
        plot=lambda *a, **k: None,
        set_xlabel=lambda *a, **k: None,
        set_ylabel=lambda *a, **k: None,
        set_title=lambda text: captured.setdefault("title", text),
    )
    viewer.figure = types.SimpleNamespace(
        clear=lambda: None,
        add_subplot=lambda *a, **k: axis,
    )
    viewer.canvas = types.SimpleNamespace(draw=lambda: None)

    spectra = {"timestamp": 1.0, "IntegrationTime": 50, "500": 0.1}
    viewer._plot_spectra(spectra)

    assert "Integration" in captured.get("title", "")
