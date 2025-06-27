"""Utility functions for loading and searching spectral data."""

from __future__ import annotations

import csv
import os
from bisect import bisect_left
from typing import Dict, List


def read_csv_file(path: str) -> List[Dict[str, float]]:
    """Read ``path`` as CSV returning rows with numeric values when possible."""

    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    rows: List[Dict[str, float]] = []
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            parsed: Dict[str, float] = {}
            for key, value in row.items():
                try:
                    parsed[key] = float(value)
                except (TypeError, ValueError):
                    parsed[key] = float("nan")
            rows.append(parsed)
    return rows


def nearest_by_timestamp(data: List[Dict[str, float]], timestamp: float) -> Dict[str, float]:
    """Return entry from *data* whose ``timestamp`` is closest to ``timestamp``."""

    if not data:
        raise ValueError("data must not be empty")

    timestamps = [row["timestamp"] for row in data]
    idx = bisect_left(timestamps, timestamp)

    if idx == 0:
        return data[0]
    if idx == len(timestamps):
        return data[-1]

    before = data[idx - 1]
    after = data[idx]

    if timestamp - before["timestamp"] <= after["timestamp"] - timestamp:
        return before
    return after

