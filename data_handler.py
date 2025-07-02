"""Utility functions for loading and validating viewer data."""
from __future__ import annotations

from datetime import datetime
from typing import List

from constants import TS_FORMAT

import pandas as pd


def _validate_timestamp(ts: str) -> None:
    """Raise ``ValueError`` if ``ts`` does not match ``TS_FORMAT``."""
    try:
        datetime.strptime(ts, TS_FORMAT)
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {ts}") from exc


def parse_frame_times(path: str) -> List[str]:
    """Return a list of timestamp strings from ``path``."""
    times: List[str] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            ts = line.strip()
            if not ts:
                continue
            # handle CSV formatted lines with frame numbers or headers
            if "," in ts:
                parts = [p.strip() for p in ts.split(",")]
                if parts[0].lower().startswith("frame") or parts[0].isdigit():
                    if len(parts) > 1:
                        ts = parts[-1]
                if ts.lower().startswith("timestamp"):
                    continue
            if ts == "FILE_START":
                continue
            _validate_timestamp(ts)
            times.append(ts)
    if not times:
        raise ValueError(f"No frame times found in {path}")
    return times


def parse_spectral_data(path: str) -> pd.DataFrame:
    """Return a DataFrame of spectral data with a validated timestamp column.

    Optimized for performance with large datasets.
    """
    # Use a more efficient approach for large files
    try:
        # Try to use pandas' built-in type inference and validation
        df = pd.read_csv(
            path, 
            skiprows=1,  # Skip optional leading line like 'FILE_START'
            dtype={'timestamp': str},  # Ensure timestamp is read as string
            low_memory=False  # Avoid dtype warnings for mixed columns
        )
    except Exception:
        # Fallback to standard read_csv if optimized approach fails
        try:
            df = pd.read_csv(path, skiprows=1)
        except Exception:
            # Try with different separator detection
            df = pd.read_csv(path, sep=None, engine='python', skiprows=1)

    if df.empty:
        raise ValueError(f"Spectral data {path} is empty")

    # Handle column names from ExampleFiles
    if "KecmTimestamp" in df.columns:
        df.rename(columns={"KecmTimestamp": "timestamp"}, inplace=True)
    elif 0 in df.columns:
        df.rename(columns={0: "timestamp"}, inplace=True)

    # Check if any column name contains 'timestamp' (case-insensitive)
    if "timestamp" not in df.columns:
        timestamp_cols = [col for col in df.columns if 'timestamp' in str(col).lower()]
        if timestamp_cols:
            df.rename(columns={timestamp_cols[0]: "timestamp"}, inplace=True)
        else:
            # If still no timestamp column, try to use the first column as timestamp
            if len(df.columns) > 0:
                df.rename(columns={df.columns[0]: "timestamp"}, inplace=True)
            else:
                raise ValueError("Spectral data missing timestamp column")

    # Check if column names might be wavelengths (numeric values)
    # This helps ensure the data is in the right format for spectral plotting
    numeric_cols = []
    for col in df.columns:
        if col == "timestamp":
            continue
        try:
            float(col)
            numeric_cols.append(col)
        except (ValueError, TypeError):
            continue

    # If we found numeric column names, they might be wavelengths
    # Make sure they're properly sorted
    if numeric_cols:
        print(f"Found {len(numeric_cols)} columns with numeric names (potential wavelengths)")
        # Sort columns by numeric value
        sorted_cols = sorted(numeric_cols, key=lambda x: float(x))
        # If the order is different, reorder the columns
        if sorted_cols != numeric_cols:
            print("Reordering columns to ensure wavelengths are in ascending order")
            # Keep timestamp first, then add sorted wavelength columns, then any other columns
            new_cols = ["timestamp"] + sorted_cols + [col for col in df.columns if col != "timestamp" and col not in numeric_cols]
            df = df[new_cols]

    # Use vectorized operations instead of row-by-row processing
    # First convert all timestamps to strings
    df["timestamp"] = df["timestamp"].astype(str)

    # Create a mask for valid timestamps using vectorized operations
    def is_valid_timestamp(ts):
        try:
            datetime.strptime(ts, TS_FORMAT)
            return True
        except ValueError:
            return False

    # Apply validation in chunks for better performance with large datasets
    chunk_size = 10000
    valid_rows = []

    for i in range(0, len(df), chunk_size):
        chunk = df["timestamp"].iloc[i:i+chunk_size]
        valid_chunk = [is_valid_timestamp(ts) for ts in chunk]
        valid_rows.extend(valid_chunk)

    # Filter out invalid rows
    df = df[valid_rows].reset_index(drop=True)

    # Convert numeric columns efficiently
    # Get non-timestamp columns
    numeric_cols = [col for col in df.columns if col != "timestamp"]

    # Convert in one operation instead of column by column
    if numeric_cols:
        # Replace deprecated errors='ignore' with explicit try-except
        for col in numeric_cols:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                # Keep column as is if conversion fails
                pass

    return df


def parse_metadata(path: str, num_rows: int) -> pd.DataFrame:
    """Parse key=value pairs and repeat for ``num_rows`` rows."""
    with open(path, "r", encoding="utf-8") as fh:
        line = fh.readline().strip()

    pairs = [p.split("=", 1) for p in line.split(",") if "=" in p]
    columns = [p[0] for p in pairs]
    values = []
    for _, val in pairs:
        try:
            values.append(float(val))
        except ValueError:
            values.append(val)

    df = pd.DataFrame([values] * num_rows, columns=columns)
    return df


def validate_row_counts(frame_times: List[str], spectral_df: pd.DataFrame) -> None:
    """Raise ``ValueError`` if the row counts between datasets differ."""
    if len(frame_times) != len(spectral_df):
        raise ValueError(
            f"Frame time count {len(frame_times)} does not match spectral row count {len(spectral_df)}"
        )
