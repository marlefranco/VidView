"""Utility functions for loading and searching spectral data."""

from __future__ import annotations

import csv
import os
from bisect import bisect_left
from typing import Dict, List


def read_csv_file(path: str) -> List[Dict[str, float]]:
    """Read ``path`` as CSV returning rows with numeric values when possible.

    Optimized for performance with large datasets.
    """
    import pandas as pd
    from typing import Dict, List, Any

    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    # Use pandas for faster CSV reading and numeric conversion
    try:
        # Read CSV with pandas which is much faster for large files
        df = pd.read_csv(path, low_memory=False)

        # Convert all possible columns to numeric at once
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except:
                pass

        # Convert DataFrame to list of dictionaries
        rows: List[Dict[str, float]] = []

        # Process in chunks for better memory usage with large files
        chunk_size = 10000
        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i:i+chunk_size]
            # Convert chunk to records and process
            for record in chunk.to_dict('records'):
                parsed: Dict[str, float] = {}
                for key, value in record.items():
                    if pd.isna(value):
                        parsed[key] = float("nan")
                    elif isinstance(value, (int, float)):
                        parsed[key] = float(value)
                    else:
                        try:
                            parsed[key] = float(value)
                        except (TypeError, ValueError):
                            parsed[key] = float("nan")
                rows.append(parsed)

        return rows

    except ImportError:
        # Fallback to standard CSV reader if pandas is not available
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
    """Return entry from *data* whose ``timestamp`` is closest to ``timestamp``.

    Optimized for performance with large datasets and repeated calls.
    """
    if not data:
        raise ValueError("data must not be empty")

    # Cache sorted timestamps and indices for repeated calls
    # This avoids extracting and sorting timestamps for every call
    if not hasattr(nearest_by_timestamp, '_cache') or nearest_by_timestamp._cache_data_id != id(data):
        # Create a new cache when data changes
        nearest_by_timestamp._cache = {}
        nearest_by_timestamp._cache_data_id = id(data)
        nearest_by_timestamp._cache['timestamps'] = [row["timestamp"] for row in data]
        nearest_by_timestamp._cache['sorted_indices'] = None

    timestamps = nearest_by_timestamp._cache['timestamps']

    # Check if timestamps are already sorted
    if not nearest_by_timestamp._cache.get('is_sorted'):
        # Check if timestamps are sorted
        is_sorted = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
        nearest_by_timestamp._cache['is_sorted'] = is_sorted

        # If not sorted, create a mapping from sorted positions to original indices
        if not is_sorted:
            sorted_indices = sorted(range(len(timestamps)), key=lambda i: timestamps[i])
            sorted_timestamps = [timestamps[i] for i in sorted_indices]
            nearest_by_timestamp._cache['sorted_indices'] = sorted_indices
            nearest_by_timestamp._cache['sorted_timestamps'] = sorted_timestamps

    # Use the appropriate timestamps array and index mapping
    if nearest_by_timestamp._cache.get('is_sorted'):
        # If already sorted, use original timestamps
        search_timestamps = timestamps
        idx = bisect_left(search_timestamps, timestamp)

        if idx == 0:
            return data[0]
        if idx == len(search_timestamps):
            return data[-1]

        before = data[idx - 1]
        after = data[idx]
    else:
        # If not sorted, use the sorted timestamps and mapping
        sorted_timestamps = nearest_by_timestamp._cache['sorted_timestamps']
        sorted_indices = nearest_by_timestamp._cache['sorted_indices']

        idx = bisect_left(sorted_timestamps, timestamp)

        if idx == 0:
            return data[sorted_indices[0]]
        if idx == len(sorted_timestamps):
            return data[sorted_indices[-1]]

        before_idx = sorted_indices[idx - 1]
        after_idx = sorted_indices[idx]

        before = data[before_idx]
        after = data[after_idx]

    # Return the closest match
    if timestamp - before["timestamp"] <= after["timestamp"] - timestamp:
        return before
    return after
