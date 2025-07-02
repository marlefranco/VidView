import ast
import inspect
from pathlib import Path
from viewer import MainViewerWindow

def test_viewer_syntax():
    # Test that the MainViewerWindow class can be imported
    assert inspect.isclass(MainViewerWindow)


def test_export_csv_default_path():
    # Check that export_csv method has a default path parameter of 'output.csv'
    signature = inspect.signature(MainViewerWindow.export_csv)
    path_param = signature.parameters.get('path')
    assert path_param is not None
    assert path_param.default == 'output.csv'


def test_export_csv_functionality(monkeypatch):
    # Test the functionality of the export_csv method
    from viewer.controllers import VideoSpectraController

    # Create a mock controller
    called = {}
    def fake_export_csv(self, path):
        called['path'] = path

    # Patch the export_csv method in the controller
    monkeypatch.setattr(VideoSpectraController, 'export_csv', fake_export_csv)

    # Create a dummy MainViewerWindow instance with a mocked controller
    dummy = MainViewerWindow.__new__(MainViewerWindow)
    dummy.controller = VideoSpectraController.__new__(VideoSpectraController)
    dummy.output_path = 'output.csv'

    # Call the export_csv method
    dummy.export_csv(dummy.output_path)

    # Check that the controller's export_csv method was called with the right path
    assert called['path'] == 'output.csv'
