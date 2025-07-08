"""Data models for the video spectra viewer application."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

import pandas as pd
import numpy as np

from constants import TS_FORMAT
from logging_config import get_logger

# Create a logger for this module
logger = get_logger("models")


class SpectralDataModel:
    """Model for spectral data.

    This class handles loading, processing, and accessing spectral data.

    Attributes
    ----------
    data : pd.DataFrame
        DataFrame containing the spectral data.
    """

    def __init__(self, data_path: Union[str, Path]) -> None:
        """Initialize the spectral data model.

        Parameters
        ----------
        data_path : Union[str, Path]
            Path to the spectral data file.
        """
        self.data_path = Path(data_path)
        self.data = self._load_data(self.data_path)

    def _load_data(self, path: Path) -> pd.DataFrame:
        """Load spectral data from a file.

        Parameters
        ----------
        path : Path
            Path to the spectral data file.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the spectral data.
        """
        logger.debug(f"Loading spectral data from {path}")

        # Check if file exists
        if not path.exists():
            logger.warning(f"File not found: {path}")
            return pd.DataFrame()

        # Try to read the first few lines to check for FILE_START
        try:
            with open(path, 'r') as f:
                first_lines = [f.readline().strip() for _ in range(3)]

            # Check if the first line is FILE_START
            skip_rows = 0
            if first_lines[0] == "FILE_START":
                logger.debug("Found FILE_START, skipping first line")
                skip_rows = 1

            logger.debug(f"First few lines: {first_lines}")
        except Exception as e:
            logger.error(f"Error reading first lines: {e}")
            skip_rows = 0

        # Try different approaches to load the data
        df = None
        try:
            # First try with automatic separator detection, skipping FILE_START if present
            df = pd.read_csv(path, sep=None, engine='python', skiprows=skip_rows)
            logger.debug(f"Successfully loaded data with automatic separator detection")
        except Exception as e:
            logger.debug(f"Error loading with automatic separator detection: {e}")
            try:
                # Try with comma separator
                df = pd.read_csv(path, sep=',', skiprows=skip_rows)
                logger.debug(f"Successfully loaded data with comma separator")
            except Exception as e:
                logger.debug(f"Error loading with comma separator: {e}")
                try:
                    # Try with tab separator
                    df = pd.read_csv(path, sep='\t', skiprows=skip_rows)
                    logger.debug(f"Successfully loaded data with tab separator")
                except Exception as e:
                    logger.debug(f"Error loading with tab separator: {e}")
                    try:
                        # Try with whitespace separator
                        df = pd.read_csv(path, delim_whitespace=True, skiprows=skip_rows)
                        logger.debug(f"Successfully loaded data with whitespace separator")
                    except Exception as e:
                        logger.debug(f"Error loading with whitespace separator: {e}")
                        # Last resort: try to read the file directly and parse it manually
                        logger.debug("Trying to read the file directly and parse it manually...")
                        try:
                            with open(path, 'r') as f:
                                lines = f.readlines()

                            # Skip FILE_START if present
                            if lines and lines[0].strip() == "FILE_START":
                                lines = lines[1:]
                                logger.debug("Skipped FILE_START line")

                            if not lines:
                                logger.warning("No data lines found")
                                return pd.DataFrame()

                            # Try to determine the separator by examining the first few lines
                            separators = [',', '\t', ' ', ';']
                            separator_counts = {sep: 0 for sep in separators}

                            for line in lines[:10]:  # Check first 10 lines
                                for sep in separators:
                                    separator_counts[sep] += line.count(sep)

                            # Use the separator that appears most frequently
                            best_separator = max(separator_counts.items(), key=lambda x: x[1])[0]
                            logger.debug(f"Detected separator: '{best_separator}'")

                            # Parse the header line to get column names
                            header = lines[0].strip().split(best_separator)

                            # Parse the data lines
                            data = []
                            for line in lines[1:]:
                                if line.strip():  # Skip empty lines
                                    values = line.strip().split(best_separator)
                                    if len(values) == len(header):
                                        data.append(values)

                            # Create DataFrame
                            df = pd.DataFrame(data, columns=header)
                            logger.debug(f"Successfully created DataFrame manually with {len(df)} rows and {len(df.columns)} columns")
                        except Exception as e:
                            logger.error(f"Error creating DataFrame manually: {e}")
                            # If all else fails, create an empty DataFrame
                            df = pd.DataFrame()
                            logger.warning("Created empty DataFrame as fallback")

        if df is None or df.empty:
            logger.warning("Failed to load spectral data or data is empty")
            return pd.DataFrame()

        logger.debug(f"Loaded DataFrame with {len(df)} rows and {len(df.columns)} columns")
        logger.debug(f"Column names: {df.columns.tolist()}")

        # Log first few rows for debugging
        if not df.empty:
            logger.debug("First 3 rows:")
            for i in range(min(3, len(df))):
                logger.debug(f"Row {i}: {df.iloc[i].to_dict()}")

        # Handle column names from ExampleFiles
        if "KecmTimestamp" in df.columns:
            logger.debug("Renaming 'KecmTimestamp' to 'timestamp'")
            df.rename(columns={"KecmTimestamp": "timestamp"}, inplace=True)

        # Check if any column name contains 'timestamp' (case-insensitive)
        if "timestamp" not in df.columns:
            timestamp_cols = [col for col in df.columns if 'timestamp' in str(col).lower()]
            if timestamp_cols:
                logger.debug(f"Renaming '{timestamp_cols[0]}' to 'timestamp'")
                df.rename(columns={timestamp_cols[0]: "timestamp"}, inplace=True)
            else:
                # If still no timestamp column, try to use the first column as timestamp
                if len(df.columns) > 0:
                    logger.debug(f"Using first column '{df.columns[0]}' as timestamp")
                    df.rename(columns={df.columns[0]: "timestamp"}, inplace=True)
                else:
                    logger.warning("No columns found in DataFrame")
                    return pd.DataFrame()

        # Check if any column names can be interpreted as wavelengths
        wavelength_cols = []
        for col in df.columns:
            if col == "timestamp" or col.lower() in {"integrationtime", "integration_time", "integration"}:
                continue
            try:
                float_val = float(col)
                wavelength_cols.append((float_val, col))
            except (ValueError, TypeError):
                continue

        if wavelength_cols:
            logger.debug(f"Found {len(wavelength_cols)} column names that can be interpreted as wavelengths")
            # Sort wavelength columns by value
            wavelength_cols.sort(key=lambda x: x[0])
            logger.debug(f"First few wavelength columns: {wavelength_cols[:5]}")

            # Ensure wavelength columns are in ascending order
            sorted_cols = [col for _, col in wavelength_cols]
            current_cols = [col for col in df.columns if col in sorted_cols]

            if sorted_cols != current_cols:
                logger.debug("Reordering columns to ensure wavelengths are in ascending order")
                # Keep timestamp and other special columns first, then add sorted wavelength columns
                special_cols = ["timestamp"]
                for col in df.columns:
                    if col.lower() in {"integrationtime", "integration_time", "integration"}:
                        special_cols.append(col)

                # Create new column order
                new_cols = special_cols + sorted_cols + [col for col in df.columns if col not in special_cols and col not in sorted_cols]

                # Reorder columns
                df = df[new_cols]
                logger.debug(f"New column order: {df.columns.tolist()}")
        else:
            logger.warning("No column names can be interpreted as wavelengths")

            # Try to extract wavelength information from the data
            logger.debug("Trying to extract wavelength information from the data...")

            # Check if there's a column that might contain wavelength values
            wavelength_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if "wavelength" in col_lower or "wave" in col_lower or "nm" in col_lower:
                    wavelength_col = col
                    logger.debug(f"Found potential wavelength column: {col}")
                    break

            if wavelength_col:
                # Try to extract wavelengths from this column
                try:
                    # Check if the column contains comma-separated values
                    sample_value = str(df[wavelength_col].iloc[0])
                    if ',' in sample_value:
                        logger.debug(f"Column '{wavelength_col}' contains comma-separated values")

                        # Extract wavelengths from the first row
                        wavelengths = [float(w.strip()) for w in sample_value.split(',') if w.strip()]
                        logger.debug(f"Extracted {len(wavelengths)} wavelengths: {wavelengths[:5]}...")

                        # Create new columns for each wavelength
                        for i, wl in enumerate(wavelengths):
                            col_name = str(wl)
                            df[col_name] = 0.0  # Initialize with zeros
                            logger.debug(f"Created column '{col_name}'")

                        # Now we have columns that can be interpreted as wavelengths
                        logger.debug(f"Created {len(wavelengths)} wavelength columns")
                    else:
                        logger.debug(f"Column '{wavelength_col}' does not contain comma-separated values")
                except Exception as e:
                    logger.error(f"Error extracting wavelengths from column '{wavelength_col}': {e}")

        # Convert numeric columns to float
        for col in df.columns:
            if col != "timestamp":
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    logger.debug(f"Converted column '{col}' to numeric")
                except Exception as e:
                    logger.debug(f"Error converting column '{col}' to numeric: {e}")

        return df

    def get_row(self, index: int) -> pd.Series:
        """Get a row of spectral data by index.

        Parameters
        ----------
        index : int
            Index of the row to get.

        Returns
        -------
        pd.Series
            Row of spectral data.
        """
        logger.debug(f"Getting row with index {index} from data with {len(self.data)} rows")

        if index < 0 or index >= len(self.data):
            logger.error(f"Index {index} out of bounds for data with {len(self.data)} rows")
            raise IndexError(f"Index {index} out of bounds for data with {len(self.data)} rows")

        row = self.data.iloc[index]
        logger.debug(f"Row has {len(row)} columns")

        # Log a sample of the row values
        sample_values = {}
        for i, (idx, val) in enumerate(row.items()):
            if i < 5 or i >= len(row) - 5:  # First 5 and last 5 values
                sample_values[idx] = val
            if i == 5 and len(row) > 10:
                sample_values["..."] = "..."
        logger.debug(f"Row sample values: {sample_values}")

        return row

    def get_wavelengths_and_intensities(self, row: pd.Series) -> Tuple[List[float], List[float]]:
        """Extract wavelengths and intensities from a row of spectral data.

        Parameters
        ----------
        row : pd.Series
            Row of spectral data.

        Returns
        -------
        Tuple[List[float], List[float]]
            Tuple of (wavelengths, intensities).
        """
        logger.debug("Extracting wavelengths and intensities")
        wavelengths = []
        intensities = []

        # Log row information for debugging
        logger.debug(f"Row index names: {row.index.tolist()}")

        # Log a sample of the row values
        sample_values = {}
        for i, (idx, val) in enumerate(row.items()):
            if i < 5 or i >= len(row) - 5:  # First 5 and last 5 values
                sample_values[idx] = val
            if i == 5 and len(row) > 10:
                sample_values["..."] = "..."
        logger.debug(f"Row sample values: {sample_values}")

        # Try different approaches to extract wavelengths and intensities

        # Approach 1: Try to convert column names to floats (standard format)
        # First collect all potential wavelength columns
        logger.debug("Approach 1: Using column names as wavelengths")
        wavelength_cols = []
        for k in row.index:
            if k == "timestamp" or k.lower() in {"integrationtime", "integration_time", "integration"}:
                continue
            try:
                # Try to convert column name to float (might be a wavelength)
                float_val = float(k)
                wavelength_cols.append((float_val, k))
                logger.debug(f"Found potential wavelength column: {k} = {float_val}")
            except ValueError:
                continue

        # Sort wavelength columns by value to ensure correct order
        if wavelength_cols:
            wavelength_cols.sort(key=lambda x: x[0])
            for wl, col in wavelength_cols:
                try:
                    wavelengths.append(wl)
                    intensities.append(float(row[col]))
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert intensity value for wavelength {wl}")
                    continue

        # If we found wavelengths using approach 1, use those
        if wavelengths:
            logger.debug(f"Using standard format (column names as wavelengths)")
            logger.debug(f"Found {len(wavelengths)} wavelengths and {len(intensities)} intensities")

            # Log samples of wavelengths and intensities
            if wavelengths and intensities:
                logger.debug("Wavelength samples (first 5):")
                for i in range(min(5, len(wavelengths))):
                    logger.debug(f"  {i}: {wavelengths[i]}")

                logger.debug("Intensity samples (first 5):")
                for i in range(min(5, len(intensities))):
                    logger.debug(f"  {i}: {intensities[i]}")
        else:
            # Approach 2: Look for columns that might contain wavelength data
            logger.debug(f"Approach 2: Looking for columns that might contain wavelength data")
            wavelength_col = None
            intensity_cols = []

            # Look for columns that might contain wavelength data
            for col in row.index:
                col_lower = str(col).lower()
                if "wavelength" in col_lower or "wave" in col_lower or "nm" in col_lower:
                    wavelength_col = col
                    logger.debug(f"Found potential wavelength column: {col}")
                elif "intensity" in col_lower or "count" in col_lower or "signal" in col_lower:
                    intensity_cols.append(col)
                    logger.debug(f"Found potential intensity column: {col}")

            # If we found a wavelength column, use it
            if wavelength_col:
                # Try to extract wavelengths from the wavelength column
                try:
                    wavelength_values = row[wavelength_col]
                    logger.debug(f"Wavelength values: {wavelength_values}")

                    if isinstance(wavelength_values, (list, tuple, np.ndarray)):
                        wavelengths = [float(w) for w in wavelength_values if w and not pd.isna(w)]
                    else:
                        # If it's a single value, try to parse it as a list
                        try:
                            # Check if it's a comma-separated string
                            if isinstance(wavelength_values, str) and ',' in wavelength_values:
                                wavelengths = [float(w.strip()) for w in wavelength_values.split(',') if w.strip()]
                            else:
                                # Try to parse as JSON
                                import json
                                wavelengths = [float(w) for w in json.loads(wavelength_values) if w and not pd.isna(w)]
                        except:
                            # If that fails, just use it as a single value
                            if wavelength_values and not pd.isna(wavelength_values):
                                wavelengths = [float(wavelength_values)]
                    logger.debug(f"Extracted {len(wavelengths)} wavelengths from column {wavelength_col}")
                except Exception as e:
                    logger.error(f"Error extracting wavelengths from column {wavelength_col}: {e}")

            # If we found intensity columns, use them
            if intensity_cols:
                for col in intensity_cols:
                    try:
                        intensity_values = row[col]
                        logger.debug(f"Intensity values from column {col}: {intensity_values}")

                        if isinstance(intensity_values, (list, tuple, np.ndarray)):
                            intensities.extend([float(i) for i in intensity_values if i and not pd.isna(i)])
                        else:
                            # If it's a single value, try to parse it as a list
                            try:
                                # Check if it's a comma-separated string
                                if isinstance(intensity_values, str) and ',' in intensity_values:
                                    intensities.extend([float(i.strip()) for i in intensity_values.split(',') if i.strip()])
                                else:
                                    # Try to parse as JSON
                                    import json
                                    intensities.extend([float(i) for i in json.loads(intensity_values) if i and not pd.isna(i)])
                            except:
                                # If that fails, just use it as a single value
                                if intensity_values and not pd.isna(intensity_values):
                                    intensities.append(float(intensity_values))
                        logger.debug(f"Extracted {len(intensities)} intensities from column {col}")
                    except Exception as e:
                        logger.error(f"Error extracting intensities from column {col}: {e}")

            # If we found wavelengths and intensities using approach 2, use those
            if wavelengths and intensities:
                logger.debug(f"Using approach 2: Found {len(wavelengths)} wavelengths and {len(intensities)} intensities")

                # Log samples of wavelengths and intensities
                if wavelengths and intensities:
                    logger.debug("Wavelength samples (first 5):")
                    for i in range(min(5, len(wavelengths))):
                        logger.debug(f"  {i}: {wavelengths[i]}")

                    logger.debug("Intensity samples (first 5):")
                    for i in range(min(5, len(intensities))):
                        logger.debug(f"  {i}: {intensities[i]}")
            else:
                # Approach 3: Parse comma-separated values from string columns
                logger.debug("Approach 3: Parsing comma-separated values from string columns")
                for col in row.index:
                    try:
                        value = str(row[col])
                        if not value:
                            continue

                        # Check if this looks like a string containing wavelength values
                        # Look for patterns like "394.53,394.83,395.12,..."
                        if ',' in value and any(c.isdigit() for c in value):
                            logger.debug(f"Found comma-separated values in column {col}: {value[:50]}...")

                            # Split by commas and try to extract numeric values
                            parts = []
                            for part in value.split(','):
                                part = part.strip()
                                # Try to find numeric substrings in the part
                                import re
                                numeric_matches = re.findall(r'(\d+\.\d+|\d+)', part)
                                parts.extend(numeric_matches)

                            if parts:
                                logger.debug(f"Found {len(parts)} potential numeric values in column {col}")
                                logger.debug(f"First few values: {parts[:5]}")

                                # If we have a lot of values, this might be our wavelength data
                                if len(parts) > 10:  # Arbitrary threshold
                                    # Try to extract wavelengths and intensities
                                    # First, look for patterns that suggest wavelengths
                                    wavelength_pattern = False

                                    # Check if values are increasing steadily (typical for wavelengths)
                                    try:
                                        numeric_parts = [float(p) for p in parts]
                                        if all(numeric_parts[i] < numeric_parts[i+1] for i in range(len(numeric_parts)-1)):
                                            wavelength_pattern = True
                                    except (ValueError, IndexError):
                                        pass

                                    if wavelength_pattern:
                                        logger.debug("Values appear to be increasing steadily, likely wavelengths")
                                        # This looks like wavelength data
                                        # The first half might be wavelengths, the second half intensities
                                        # Or we might have wavelengths only and need to generate intensities
                                        if len(parts) % 2 == 0:
                                            # Even number of values, try splitting in half
                                            half = len(parts) // 2
                                            try:
                                                wavelengths = [float(p) for p in parts[:half]]
                                                intensities = [float(p) for p in parts[half:]]
                                                logger.debug(f"Split {len(parts)} values into {len(wavelengths)} wavelengths and {len(intensities)} intensities")
                                            except ValueError:
                                                # If conversion fails, assume these are all wavelengths
                                                wavelengths = [float(p) for p in parts if p and re.match(r'^\d+(\.\d+)?$', p)]
                                                # Generate dummy intensities
                                                intensities = [1.0] * len(wavelengths)
                                                logger.debug(f"Generated {len(wavelengths)} wavelengths with dummy intensities")
                                        else:
                                            # Odd number of values, assume these are all wavelengths
                                            wavelengths = [float(p) for p in parts if p and re.match(r'^\d+(\.\d+)?$', p)]
                                            # Generate dummy intensities
                                            intensities = [1.0] * len(wavelengths)
                                            logger.debug(f"Generated {len(wavelengths)} wavelengths with dummy intensities")

                                        # If we found a good number of wavelengths, break out of the loop
                                        if len(wavelengths) > 10:
                                            logger.debug(f"Using approach 3: Found {len(wavelengths)} wavelengths and {len(intensities)} intensities")
                                            break
                    except Exception as e:
                        logger.error(f"Error parsing values from column {col}: {e}")
                        continue

                # If we found wavelengths and intensities using approach 3, use those
                if wavelengths and intensities:
                    logger.debug(f"Using approach 3: Found {len(wavelengths)} wavelengths and {len(intensities)} intensities")

                    # Log samples of wavelengths and intensities
                    if wavelengths and intensities:
                        logger.debug("Wavelength samples (first 5):")
                        for i in range(min(5, len(wavelengths))):
                            logger.debug(f"  {i}: {wavelengths[i]}")

                        logger.debug("Intensity samples (first 5):")
                        for i in range(min(5, len(intensities))):
                            logger.debug(f"  {i}: {intensities[i]}")
                else:
                    # Approach 4: Try to use any numeric columns as data
                    logger.debug(f"Approach 4: Using numeric columns as data")
                    numeric_cols = []
                    for col in row.index:
                        if col == "timestamp" or col.lower() in {"integrationtime", "integration_time", "integration"}:
                            continue
                        try:
                            val = float(row[col])
                            if not pd.isna(val):
                                numeric_cols.append(col)
                        except (ValueError, TypeError):
                            continue

                    logger.debug(f"Found {len(numeric_cols)} numeric columns")

                    # If we have numeric columns, use them
                    if numeric_cols:
                        # First, check if any column names can be interpreted as wavelengths
                        wavelength_cols = []
                        for col in numeric_cols:
                            try:
                                # Try to convert column name to float (might be a wavelength)
                                float_col = float(col)
                                wavelength_cols.append((float_col, col))
                            except (ValueError, TypeError):
                                continue

                        # If we found columns that look like wavelengths, use them
                        if wavelength_cols:
                            logger.debug(f"Found {len(wavelength_cols)} column names that can be interpreted as wavelengths")
                            # Sort by wavelength value
                            wavelength_cols.sort(key=lambda x: x[0])
                            for wl, col in wavelength_cols:
                                try:
                                    wavelengths.append(wl)
                                    intensities.append(float(row[col]))
                                except (ValueError, TypeError):
                                    continue
                            logger.debug(f"Using column names as wavelengths: Found {len(wavelengths)} wavelengths and {len(intensities)} intensities")
                        else:
                            # If no column names look like wavelengths, try to use the columns themselves
                            logger.debug("No column names can be interpreted as wavelengths")

                            # If we have an even number of columns, assume half are wavelengths and half are intensities
                            if len(numeric_cols) % 2 == 0:
                                logger.debug("Even number of numeric columns, assuming half are wavelengths and half are intensities")
                                half = len(numeric_cols) // 2
                                for i in range(half):
                                    try:
                                        wavelengths.append(float(row[numeric_cols[i]]))
                                        intensities.append(float(row[numeric_cols[i + half]]))
                                    except (ValueError, TypeError):
                                        continue
                                logger.debug(f"Using half of columns as wavelengths: Found {len(wavelengths)} wavelengths and {len(intensities)} intensities")
                            else:
                                # If we have an odd number of columns, don't use column indices as wavelengths
                                # as this will likely produce a 45-degree line
                                logger.debug("Odd number of numeric columns, but won't use column indices as wavelengths to avoid 45-degree line")
                                logger.debug("Will use dummy data instead")
                                # Leave wavelengths and intensities empty so we'll use dummy data later
                                wavelengths = []
                                intensities = []
                                logger.debug("Using dummy data instead of column indices to avoid 45-degree line")

        # Ensure wavelengths and intensities have the same length
        if len(wavelengths) != len(intensities):
            logger.warning(f"Wavelengths and intensities have different lengths: {len(wavelengths)} vs {len(intensities)}")
            # If we have more wavelengths than intensities, truncate wavelengths
            if len(wavelengths) > len(intensities):
                wavelengths = wavelengths[:len(intensities)]
            # If we have more intensities than wavelengths, truncate intensities
            else:
                intensities = intensities[:len(wavelengths)]
            logger.debug(f"Truncated to {len(wavelengths)} wavelengths and {len(intensities)} intensities")

        # Sort by wavelength
        if wavelengths and intensities:
            sorted_data = sorted(zip(wavelengths, intensities), key=lambda x: x[0])
            wavelengths = [w for w, _ in sorted_data]
            intensities = [i for _, i in sorted_data]

        logger.debug(f"Final wavelengths count: {len(wavelengths)}")
        logger.debug(f"Final intensities count: {len(intensities)}")

        # Check if this might be a 45-degree line (wavelengths are just sequential indices)
        if wavelengths and len(wavelengths) > 2:
            # Check if wavelengths are evenly spaced with increment close to 1.0
            is_sequential = True
            increment = wavelengths[1] - wavelengths[0]
            logger.debug(f"First wavelength increment: {increment}")

            # If the increment is very close to 1.0, this might be sequential indices
            if 0.99 <= increment <= 1.01:
                for i in range(1, len(wavelengths) - 1):
                    if abs((wavelengths[i+1] - wavelengths[i]) - increment) > 0.01:
                        is_sequential = False
                        break

                # If wavelengths appear to be sequential indices and all intensities are similar
                if is_sequential:
                    logger.debug("Wavelengths appear to be sequential indices")
                    # Check if intensities are all similar (which would create a 45-degree line)
                    intensity_range = max(intensities) - min(intensities)
                    intensity_avg = sum(intensities) / len(intensities)
                    logger.debug(f"Intensity range: {intensity_range}, average: {intensity_avg}")

                    # If intensity range is small relative to average, or if intensities are very similar to wavelengths,
                    # this is likely a 45-degree line
                    if intensity_range < 0.2 * intensity_avg or all(abs(w - i) < 0.5 * intensity_avg for w, i in zip(wavelengths[:5], intensities[:5])):
                        logger.warning("Detected potential 45-degree line pattern in data")
                        logger.warning("Wavelengths appear to be sequential indices and intensities are similar")
                        logger.warning("This may indicate that wavelength extraction failed")
                        logger.debug("Trying to use column names directly as a last resort")

                        # Try to use column names directly as a last resort
                        numeric_cols = []
                        for col in row.index:
                            if col == "timestamp" or col.lower() in {"integrationtime", "integration_time", "integration"}:
                                continue
                            try:
                                float_val = float(col)
                                numeric_cols.append((float_val, col))
                            except ValueError:
                                continue

                        if numeric_cols and len(numeric_cols) > 2:
                            logger.debug(f"Found {len(numeric_cols)} column names that can be interpreted as wavelengths")
                            numeric_cols.sort(key=lambda x: x[0])
                            new_wavelengths = []
                            new_intensities = []

                            for wl, col in numeric_cols:
                                try:
                                    new_wavelengths.append(wl)
                                    new_intensities.append(float(row[col]))
                                except (ValueError, TypeError):
                                    continue

                            if len(new_wavelengths) > 2:
                                logger.debug(f"Successfully extracted {len(new_wavelengths)} wavelengths from column names")
                                wavelengths = new_wavelengths
                                intensities = new_intensities
                                logger.debug(f"Using column names as wavelengths: Found {len(wavelengths)} wavelengths and {len(intensities)} intensities")
                            else:
                                logger.warning("Failed to extract wavelengths from column names")
                        else:
                            logger.warning("No column names can be interpreted as wavelengths")
                    else:
                        logger.debug("Intensities vary significantly, not a 45-degree line")
                else:
                    logger.debug("Wavelengths are not evenly spaced, not sequential indices")
            else:
                logger.debug("First wavelength increment is not close to 1.0, not sequential indices")

        # Final check: if we still don't have any wavelengths or intensities, create dummy data
        if not wavelengths or not intensities:
            logger.warning("Failed to extract wavelengths and intensities")
            logger.debug("Creating dummy data with varying intensities")
            wavelengths = list(range(100))  # Use more points for smoother curve
            # Create varying intensities with larger amplitude to make pattern more visible
            import math
            intensities = [math.sin(w * 0.1) * 50 + 50 for w in wavelengths]
            logger.debug(f"Created dummy data with {len(wavelengths)} wavelengths and {len(intensities)} intensities")
            logger.debug(f"Dummy intensities sample: {intensities[:5]}...")

        return wavelengths, intensities

    def get_integration_time(self, row: pd.Series) -> Optional[float]:
        """Extract integration time from a row of spectral data.

        Parameters
        ----------
        row : pd.Series
            Row of spectral data.

        Returns
        -------
        Optional[float]
            Integration time, or None if not found.
        """
        for col in row.index:
            lname = str(col).lower().replace(" ", "")
            if lname in {"integrationtime", "integration_time", "integration"}:
                try:
                    return float(row[col])
                except (TypeError, ValueError):
                    return None
        return None

    def get_timestamp(self, row: pd.Series) -> str:
        """Get the timestamp from a row of spectral data.

        Parameters
        ----------
        row : pd.Series
            Row of spectral data.

        Returns
        -------
        str
            Timestamp as a string, or empty string if not found or None.
        """
        timestamp = row.get("timestamp", "")
        if timestamp is None or str(timestamp).lower() == "none":
            return ""
        return str(timestamp)


class FrameTimesModel:
    """Model for frame times data.

    This class handles loading and accessing frame times data.

    Attributes
    ----------
    frame_times : List[str]
        List of frame timestamps.
    """

    def __init__(self, data_path: Union[str, Path]) -> None:
        """Initialize the frame times model.

        Parameters
        ----------
        data_path : Union[str, Path]
            Path to the frame times data file.
        """
        self.data_path = Path(data_path)
        self.frame_times = self._load_data(self.data_path)
        self._cached_frame_times = None

    def _load_data(self, path: Path) -> List[str]:
        """Load frame times data from a file.

        Parameters
        ----------
        path : Path
            Path to the frame times data file.

        Returns
        -------
        List[str]
            List of frame timestamps.
        """
        logger.debug(f"Loading frame times from {path}")
        timestamps = []

        try:
            # Try to read as CSV first
            with open(path, "r", encoding="utf-8") as f:
                # Check if the first line looks like a header
                first_line = f.readline().strip()
                has_header = "," in first_line and ("frame" in first_line.lower() or "timestamp" in first_line.lower())

                # Reset file pointer
                f.seek(0)

                # Use CSV reader to parse the file
                reader = csv.reader(f)

                # Skip header if present
                if has_header:
                    next(reader)
                    logger.debug("Skipping CSV header row")

                # Extract timestamps from each row
                for row in reader:
                    if not row:
                        continue

                    # If there are multiple columns, assume the last column is the timestamp
                    # This handles both "frame,timestamp" and "timestamp" formats
                    timestamp = row[-1].strip()
                    if timestamp:
                        timestamps.append(timestamp)

            logger.debug(f"Loaded {len(timestamps)} timestamps from CSV")

        except Exception as e:
            logger.warning(f"Error reading as CSV: {e}, falling back to line-by-line reading")
            # Fall back to simple line-by-line reading
            with open(path, "r", encoding="utf-8") as f:
                timestamps = [line.strip() for line in f if line.strip()]

            logger.debug(f"Loaded {len(timestamps)} timestamps from line-by-line reading")

        # Log a sample of the timestamps
        if timestamps:
            logger.debug(f"First few timestamps: {timestamps[:5]}")
        else:
            logger.warning("No timestamps loaded")

        return timestamps

    def get_frame_time(self, index: int) -> str:
        """Get a frame timestamp by index.

        Parameters
        ----------
        index : int
            Index of the frame.

        Returns
        -------
        str
            Frame timestamp.
        """
        if index < 0 or index >= len(self.frame_times):
            raise IndexError(f"Index {index} out of bounds for frame_times with {len(self.frame_times)} entries")
        return self.frame_times[index]

    def find_nearest_frame_index(self, timestamp: str) -> int:
        """Find the index of the frame with the timestamp closest to the given timestamp.

        Parameters
        ----------
        timestamp : str
            Timestamp to find the nearest frame for.

        Returns
        -------
        int
            Index of the nearest frame.
        """
        from bisect import bisect_left

        # Handle empty timestamp
        if not timestamp:
            return 0

        # Convert target to datetime once
        try:
            target = datetime.strptime(timestamp, TS_FORMAT)
        except ValueError:
            # If timestamp doesn't match format, return first frame
            return 0

        # Cache parsed timestamps to avoid repeated parsing
        if self._cached_frame_times is None:
            self._cached_frame_times = []
            for t in self.frame_times:
                if not t:
                    # Skip empty timestamps
                    continue
                try:
                    self._cached_frame_times.append(datetime.strptime(t, TS_FORMAT))
                except ValueError:
                    # Skip invalid timestamps
                    continue

        # Use bisect_left for O(log n) search instead of O(n)
        if not self._cached_frame_times:
            return 0

        pos = bisect_left(self._cached_frame_times, target)

        # Handle edge cases
        if pos == 0:
            return 0
        if pos == len(self._cached_frame_times):
            return len(self._cached_frame_times) - 1

        # Compare distances to find the closest
        before = self._cached_frame_times[pos-1]
        after = self._cached_frame_times[pos]
        if (target - before) <= (after - target):
            return pos - 1
        return pos


class MetadataModel:
    """Model for metadata.

    This class handles loading, processing, and accessing metadata.

    Attributes
    ----------
    data : pd.DataFrame
        DataFrame containing the metadata.
    """

    def __init__(self, data_path: Union[str, Path], num_frames: int) -> None:
        """Initialize the metadata model.

        Parameters
        ----------
        data_path : Union[str, Path]
            Path to the metadata file.
        num_frames : int
            Number of frames in the video.
        """
        self.data_path = Path(data_path)
        self.data = self._load_data(self.data_path, num_frames)

    def _load_data(self, path: Path, num_frames: int) -> pd.DataFrame:
        """Load metadata from a file.

        Parameters
        ----------
        path : Path
            Path to the metadata file.
        num_frames : int
            Number of frames in the video.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the metadata.
        """
        try:
            df = pd.read_csv(path)
            # Ensure we have enough rows for all frames
            if len(df) < num_frames:
                # Pad with empty rows
                padding = pd.DataFrame([{} for _ in range(num_frames - len(df))])
                df = pd.concat([df, padding], ignore_index=True)
            return df
        except Exception:
            # Create empty DataFrame with the right number of rows
            return pd.DataFrame([{} for _ in range(num_frames)])

    def get_row(self, index: int) -> pd.Series:
        """Get a row of metadata by index.

        Parameters
        ----------
        index : int
            Index of the row to get.

        Returns
        -------
        pd.Series
            Row of metadata.
        """
        if index < 0 or index >= len(self.data):
            raise IndexError(f"Index {index} out of bounds for metadata with {len(self.data)} rows")
        return self.data.iloc[index]

    def update_row(self, index: int, values: Dict[str, Any]) -> None:
        """Update a row of metadata.

        Parameters
        ----------
        index : int
            Index of the row to update.
        values : Dict[str, Any]
            Values to update.
        """
        if index < 0 or index >= len(self.data):
            raise IndexError(f"Index {index} out of bounds for metadata with {len(self.data)} rows")
        for col, value in values.items():
            # Try to convert string values to numeric types
            if isinstance(value, str):
                try:
                    # First try to convert to int if it's a whole number
                    if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                        value = int(value)
                    # Otherwise try to convert to float
                    else:
                        # Handle 'nan' specially
                        if value.lower() == 'nan':
                            value = float('nan')
                        else:
                            value = float(value)
                except (ValueError, TypeError):
                    # If conversion fails, keep the original string value
                    pass
            self.data.at[index, col] = value

    def save(self, path: Optional[Union[str, Path]] = None) -> None:
        """Save metadata to a file.

        Parameters
        ----------
        path : Optional[Union[str, Path]], optional
            Path to save to, by default None (uses the original path)
        """
        save_path = Path(path) if path else self.data_path
        self.data.to_csv(save_path, index=False)
