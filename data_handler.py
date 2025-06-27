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
    """Return a DataFrame of spectral data with a validated timestamp column."""
    # Skip optional leading line like 'FILE_START'
    df = pd.read_csv(path, skiprows=1)
    if df.empty:
        raise ValueError(f"Spectral data {path} is empty")

    # Handle column names from ExampleFiles
    if "KecmTimestamp" in df.columns:
        df.rename(columns={"KecmTimestamp": "timestamp"}, inplace=True)
    elif 0 in df.columns:
        df.rename(columns={0: "timestamp"}, inplace=True)

    if "timestamp" not in df.columns:
        raise ValueError("Spectral data missing timestamp column")

    # Remove rows with missing or invalid timestamps (e.g. trailing 'FILE_END')
    valid_rows = []
    for ts in df["timestamp"]:
        try:
            _validate_timestamp(str(ts))
            valid_rows.append(True)
        except ValueError:
            valid_rows.append(False)
    df = df[valid_rows].reset_index(drop=True)

    # convert remaining columns to numeric if possible
    for col in df.columns:
        if col == "timestamp":
            continue
        df[col] = pd.to_numeric(df[col], errors="ignore")

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
