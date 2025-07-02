"""Dark reference handling for spectral data processing."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Union


def load_dark_reference(path: Union[str, Path]) -> Dict[float, List[float]]:
    """Load dark reference data keyed by integration time.

    Parameters
    ----------
    path : Union[str, Path]
        Path to the dark reference file.

    Returns
    -------
    Dict[float, List[float]]
        Dictionary mapping integration times to lists of intensity values.
    """
    print(f"Loading dark reference from {path}")
    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        print(f"Dark reference file does not exist: {path}")
        return {}

    data: Dict[float, List[float]] = {}
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            row_count = 0
            for row in reader:
                row_count += 1
                integration: Optional[float] = None
                intensities: List[float] = []
                for key, value in row.items():
                    lname = key.lower().replace(" ", "")
                    if lname in {"integrationtime", "integration_time", "integration"}:
                        try:
                            integration = float(value)
                            print(f"Found integration time: {integration}")
                        except (TypeError, ValueError):
                            print(f"Invalid integration time: {value}")
                            integration = None
                    elif lname != "timestamp":
                        try:
                            intensities.append(float(value))
                        except (TypeError, ValueError):
                            intensities.append(float("nan"))
                if integration is not None:
                    data[integration] = intensities
                    print(f"Added dark reference for integration time {integration} with {len(intensities)} values")
            print(f"Processed {row_count} rows from dark reference file")
    except Exception as e:
        print(f"Error loading dark reference: {e}")
        return {}

    print(f"Loaded dark reference with {len(data)} integration times: {list(data.keys())}")
    return data


def apply_dark_reference(
    data: List[float], 
    integration: Optional[float], 
    dark_reference: Dict[float, List[float]]
) -> List[float]:
    """Apply dark reference correction to spectral data.

    Parameters
    ----------
    data : List[float]
        The spectral data to correct.
    integration : Optional[float]
        The integration time used for the spectral data.
    dark_reference : Dict[float, List[float]]
        Dictionary mapping integration times to dark reference data.

    Returns
    -------
    List[float]
        The dark-corrected spectral data.
    """
    print(f"apply_dark_reference called with data length={len(data) if data else 0}, integration={integration}")
    print(f"dark_reference has {len(dark_reference)} entries for integration times: {list(dark_reference.keys())}")

    # Handle empty data case
    if not data:
        print("Empty data, returning empty list")
        return []

    if integration is None:
        print("No integration time provided, returning original data")
        return data

    try:
        dark = dark_reference.get(float(integration))
        print(f"Dark reference for integration {integration}: {'found' if dark else 'not found'}")
        if dark:
            print(f"Dark reference length: {len(dark)}, data length: {len(data)}")

        if dark and len(dark) == len(data):
            print("Applying dark reference correction")
            corrected = [val - d for val, d in zip(data, dark)]
            print(f"Corrected data length: {len(corrected)}")
            return corrected
        else:
            print("Dark reference not applied (missing or length mismatch)")
    except (TypeError, ValueError) as e:
        # If integration can't be converted to float, just return the original data
        print(f"Error applying dark reference: {e}")
        pass

    print("Returning original data")
    return data
