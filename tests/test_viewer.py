import ast
from pathlib import Path

def test_viewer_syntax():
    source = Path('viewer.py').read_text()
    ast.parse(source)


def test_export_csv_default_path():
    source = Path('viewer.py').read_text()
    tree = ast.parse(source)

    cls = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MainViewerWindow'
    )
    func = next(
        node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'export_csv'
    )

    # first argument after 'self'
    assert func.args.args[1].arg == 'path'
    assert isinstance(func.args.defaults[0], ast.Constant)
    assert func.args.defaults[0].value == 'output.csv'


def test_export_csv_functionality(tmp_path, monkeypatch):
    source = Path('viewer.py').read_text()
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MainViewerWindow')
    func = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'export_csv')

    module = ast.Module([func], [])
    ast.fix_missing_locations(module)
    namespace = {}
    exec(compile(module, filename="<export_csv>", mode="exec"), namespace)
    export_csv = namespace['export_csv']

    called = {}
    def fake_write_csv(path, frame_times, spectral_df, metadata_df):
        called['path'] = path
        called['frame_times'] = frame_times

    export_csv.__globals__['write_csv'] = fake_write_csv

    dummy = type('Dummy', (), {
        'frame_times': [1],
        'spectral_df': None,
        'metadata_df': None,
    })()

    export_csv(dummy)
    assert called['path'] == 'output.csv'
