import ast
from pathlib import Path

def test_output_writer_syntax():
    source = Path('output_writer.py').read_text()
    ast.parse(source)
