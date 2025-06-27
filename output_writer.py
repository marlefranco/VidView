"""CSV export helpers."""
from __future__ import annotations

import pandas as pd


def write_csv(path: str, frame_times, spectral_df: pd.DataFrame, metadata_df: pd.DataFrame) -> None:
    """Write viewer results to ``path``.

    Parameters
    ----------
    path:
        Output file path.
    frame_times:
        Sequence of timestamp strings for each video frame.
    spectral_df:
        Spectral data with a ``timestamp`` column.
    metadata_df:
        Per-frame metadata edited in the UI.
    """
    try:
        output = pd.DataFrame({
            "frame": range(len(frame_times)),
            "frame_timestamp": frame_times,
        })

        # align spectral rows with frame timestamps
        trimmed_spec = spectral_df.iloc[: len(frame_times)].reset_index(drop=True)
        output["spectral_timestamp"] = trimmed_spec["timestamp"].tolist()
        spectral_values = trimmed_spec.drop(columns=["timestamp"], errors="ignore")

        output = pd.concat(
            [output, spectral_values, metadata_df.reset_index(drop=True)], axis=1
        )
        output.to_csv(path, index=False)
    except Exception as exc:
        raise IOError(f"Failed to write CSV: {exc}") from exc
