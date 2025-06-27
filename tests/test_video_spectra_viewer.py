import sys
import types
from pathlib import Path

def test_save_metadata_union(tmp_path, monkeypatch):
    # Provide dummy modules for PyQt5 and related dependencies
    class DummyWindow: pass
    qtwidgets = types.SimpleNamespace(
        QFileDialog=types.SimpleNamespace(getSaveFileName=lambda *a, **k: (str(tmp_path/'out.csv'), None)),
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
    monkeypatch.setitem(sys.modules, 'cv2', types.SimpleNamespace(VideoCapture=lambda *a, **k: types.SimpleNamespace(isOpened=lambda: True, get=lambda *args: 0, read=lambda: (False, None))))
    monkeypatch.setitem(sys.modules, 'PyQt5', types.SimpleNamespace(QtCore=qtcore, QtGui=qtgui, QtWidgets=qtwidgets))
    monkeypatch.setitem(sys.modules, 'PyQt5.QtCore', qtcore)
    monkeypatch.setitem(sys.modules, 'PyQt5.QtGui', qtgui)
    monkeypatch.setitem(sys.modules, 'PyQt5.QtWidgets', qtwidgets)
    monkeypatch.setitem(sys.modules, 'matplotlib', types.SimpleNamespace(use=lambda *a, **k: None))
    monkeypatch.setitem(sys.modules, 'matplotlib.backends.backend_qt5agg', types.SimpleNamespace(FigureCanvasQTAgg=object))
    monkeypatch.setitem(sys.modules, 'matplotlib.figure', types.SimpleNamespace(Figure=object))

    from viewer.video_spectra_viewer import VideoSpectraViewer, FrameMetadata

    viewer = VideoSpectraViewer.__new__(VideoSpectraViewer)
    viewer.control_log = [
        FrameMetadata(0.0, {"a": 1}),
        FrameMetadata(1.0, {"b": 2}),
    ]
    viewer._save_metadata_from_table = lambda: None
    viewer.status_bar = types.SimpleNamespace(showMessage=lambda *args, **kwargs: None)

    viewer.save_metadata()

    out_file = tmp_path / 'out.csv'
    data = out_file.read_text().splitlines()
    assert data[0] == 'timestamp,a,b'
    assert data[1] == '0.0,1,'
    assert data[2] == '1.0,,2'

