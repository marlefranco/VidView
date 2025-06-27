import ast
from pathlib import Path

def test_main_syntax():
    source = Path('main.py').read_text()
    ast.parse(source)


def test_main_init_failure(monkeypatch):
    import sys
    import types
    import importlib
    import pytest
    from pathlib import Path
    import importlib.util

    class DummyApp:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return 0

    qtwidgets = types.SimpleNamespace(
        QApplication=DummyApp,
        QMainWindow=object,
        QLabel=object,
        QTableWidgetItem=object,
        QTableWidget=object,
        QPushButton=object,
        QStatusBar=object,
        QWidget=object,
        QVBoxLayout=object,
        QHBoxLayout=object,
        QFileDialog=object,
        QMessageBox=types.SimpleNamespace(warning=lambda *a, **k: None),
    )
    qtcore = types.SimpleNamespace(Qt=types.SimpleNamespace(AlignCenter=0))
    qtgui = types.SimpleNamespace(QImage=object, QPixmap=object)

    monkeypatch.setitem(sys.modules, 'cv2', types.SimpleNamespace(VideoCapture=lambda *a, **k: types.SimpleNamespace(isOpened=lambda: False, release=lambda: None, get=lambda *a, **k: 0)))
    monkeypatch.setitem(sys.modules, 'PyQt5', types.SimpleNamespace(QtCore=qtcore, QtGui=qtgui, QtWidgets=qtwidgets))
    monkeypatch.setitem(sys.modules, 'PyQt5.QtCore', qtcore)
    monkeypatch.setitem(sys.modules, 'PyQt5.QtGui', qtgui)
    monkeypatch.setitem(sys.modules, 'PyQt5.QtWidgets', qtwidgets)
    monkeypatch.setitem(sys.modules, 'matplotlib', types.SimpleNamespace(use=lambda *a, **k: None))
    monkeypatch.setitem(sys.modules, 'matplotlib.backends.backend_qtagg', types.SimpleNamespace(FigureCanvasQTAgg=object))
    monkeypatch.setitem(sys.modules, 'matplotlib.figure', types.SimpleNamespace(Figure=object))
    monkeypatch.setitem(sys.modules, 'pandas', types.SimpleNamespace())

    spec = importlib.util.spec_from_file_location('viewer', Path('viewer.py'))
    viewer_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(viewer_mod)
    monkeypatch.setitem(sys.modules, 'viewer', viewer_mod)

    main = importlib.reload(importlib.import_module('main'))

    def boom(*args, **kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr(main, 'MainViewerWindow', boom)

    with pytest.raises(RuntimeError):
        main.main()
