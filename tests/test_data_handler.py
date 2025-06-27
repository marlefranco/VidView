import ast
from pathlib import Path

import importlib
import sys
import types
import pytest


def load_data_handler(monkeypatch):
    """Import ``data_handler`` with a stubbed pandas module."""
    pandas_stub = types.SimpleNamespace(DataFrame=list)
    monkeypatch.setitem(sys.modules, "pandas", pandas_stub)
    return importlib.reload(importlib.import_module("data_handler"))

def test_data_handler_syntax():
    source = Path('data_handler.py').read_text()
    ast.parse(source)


def test_validate_row_counts_passes_when_equal(monkeypatch):
    dh = load_data_handler(monkeypatch)
    frame_times = ["20200101_000000.000000", "20200101_000001.000000"]
    df_rows = [1, 2]
    dh.validate_row_counts(frame_times, df_rows)


def test_validate_row_counts_raises_on_mismatch(monkeypatch):
    dh = load_data_handler(monkeypatch)
    frame_times = ["20200101_000000.000000"]
    df_rows = [1, 2]
    with pytest.raises(ValueError):
        dh.validate_row_counts(frame_times, df_rows)
