"""Filtering utilities for spectral data processing."""

from __future__ import annotations

from typing import Iterable, List, Any

try:  # optional numpy/scipy dependencies
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - numpy optional
    np = None  # type: ignore
try:
    from scipy.signal import firwin, lfilter  # type: ignore
except Exception:  # pragma: no cover - fallback if SciPy missing
    firwin = None
    lfilter = None


def apply_fir_filter(
    data: Iterable[Iterable[float]],
    sample_rate: float,
    cutoff_freq: float,
    numtaps: int = 100,
) -> Any:
    """Applies an FIR filter to smooth spectral data.

    Parameters
    ----------
    data : Iterable[Iterable[float]]
        The data to filter, as a sequence of sequences of float values.
    sample_rate : float
        The sample rate of the data.
    cutoff_freq : float
        The cutoff frequency for the filter.
    numtaps : int, optional
        The number of filter taps, by default 100.

    Returns
    -------
    Any
        The filtered data, either as a numpy array or a list of lists.
    """
    print(f"apply_fir_filter called with sample_rate={sample_rate}, cutoff_freq={cutoff_freq}, numtaps={numtaps}")

    # Convert data to list and handle empty case
    data_list = list(data)
    print(f"Data list length: {len(data_list)}")
    if not data_list:
        print("Empty data list, returning empty list")
        return []

    # Convert data to list of lists
    try:
        rows = [list(map(float, row)) for row in data_list]
        print(f"Converted to {len(rows)} rows")
        if rows:
            print(f"First row length: {len(rows[0])}")
    except Exception as e:
        print(f"Error converting data to list of lists: {e}")
        return []

    if np is not None and firwin is not None and lfilter is not None:
        print("Using numpy/scipy implementation")
        # Use numpy for efficient filtering
        arr = np.asarray(rows, dtype=float)
        print(f"Array shape: {arr.shape}")

        # Handle empty array case
        if arr.size == 0 or (arr.ndim > 0 and 0 in arr.shape):
            print("Empty array, returning empty list")
            return []

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
            print(f"Reshaped array to {arr.shape}")
        nyquist_rate = sample_rate / 2.0
        # Cache the filter coefficients for repeated calls with the same parameters
        if not hasattr(apply_fir_filter, 'fir_coeff_cache'):
            apply_fir_filter.fir_coeff_cache = {}
        cache_key = (sample_rate, cutoff_freq, numtaps)
        if cache_key not in apply_fir_filter.fir_coeff_cache:
            apply_fir_filter.fir_coeff_cache[cache_key] = firwin(numtaps, cutoff_freq / nyquist_rate)
        fir_coeff = apply_fir_filter.fir_coeff_cache[cache_key]
        print(f"Filter coefficients length: {len(fir_coeff)}")

        # Apply filter to all rows at once for better performance
        result = np.apply_along_axis(
            lambda row: lfilter(fir_coeff, 1.0, row), axis=1, arr=arr
        )
        print(f"Filtered result shape: {result.shape}")
        return result

    # Fallback implementation for when numpy/scipy are not available
    print("Using fallback implementation (numpy/scipy not available)")
    coeffs = [1.0 / numtaps] * numtaps

    def smooth_row(row: List[float]) -> List[float]:
        print(f"Smoothing row of length {len(row)}")
        # Handle empty row case
        if not row:
            print("Empty row, returning empty list")
            return []

        padding = numtaps // 2
        padded = [row[0]] * padding + row + [row[-1]] * padding
        result = []
        # Pre-calculate window indices for better performance
        windows = [padded[i:i + numtaps] for i in range(len(row))]
        for window in windows:
            # Use sum() instead of generator expression for better performance
            result.append(sum(c * x for c, x in zip(coeffs, window)))
        print(f"Smoothed row length: {len(result)}")
        return result

    result = [smooth_row(row) for row in rows]
    print(f"Filtered result length: {len(result)}")
    return result
