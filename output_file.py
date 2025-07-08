"""Module for generating the output file from frame times, parsed data, and control inputs."""

from __future__ import annotations

import os
import pandas as pd
from pathlib import Path
from typing import Union, List, Dict, Any

from viewer.models import FrameTimesModel, SpectralDataModel, MetadataModel
from logging_config import get_logger
from file_utils import load_frame_times

# Create a logger for this module
logger = get_logger("output_file")

def generate_output_file(
    frame_times_path: Union[str, Path],
    parsed_data_path: Union[str, Path],
    control_inputs_path: Union[str, Path],
    output_path: Union[str, Path] = "output.txt"
) -> None:
    """Generate an output file by combining data from frame times, parsed data, and control inputs.
    Also generates a rangetime.txt file with the first and last spectral timestamps.

    Parameters
    ----------
    frame_times_path : Union[str, Path]
        Path to the frame times file.
    parsed_data_path : Union[str, Path]
        Path to the parsed data file.
    control_inputs_path : Union[str, Path]
        Path to the control inputs file.
    output_path : Union[str, Path], optional
        Path to save the output file, by default "output.txt"
    """
    logger.info("Generating output file...")
    logger.info(f"Frame times path: {frame_times_path}")
    logger.info(f"Parsed data path: {parsed_data_path}")
    logger.info(f"Control inputs path: {control_inputs_path}")
    logger.info(f"Output path: {output_path}")

    # Load the data using the existing models
    frame_times_model = FrameTimesModel(frame_times_path)
    parsed_data_model = SpectralDataModel(parsed_data_path)
    control_inputs_model = MetadataModel(control_inputs_path, 1)  # Only need one row of metadata

    # Check if data was loaded successfully
    if len(frame_times_model.frame_times) == 0:
        logger.error("No frame times data loaded")
        return
    if parsed_data_model.data.empty:
        logger.error("No parsed data loaded")
        return
    if control_inputs_model.data.empty:
        logger.error("No control inputs data loaded")
        return

    logger.info(f"Loaded {len(frame_times_model.frame_times)} frame times")
    logger.info(f"Loaded {len(parsed_data_model.data)} parsed data rows")
    logger.info(f"Loaded {len(control_inputs_model.data)} control inputs rows")

    # Load frame times directly from frame_times.txt
    # The frame_times.txt file has a format like:
    # frame,timestamp
    # 1,20250613_132845.542
    # 2,20250613_132845.555
    # ...
    frame_to_timestamp = load_frame_times(frame_times_path, logger)

    # If loading failed, fall back to using the model
    if not frame_to_timestamp:
        for i in range(len(frame_times_model.frame_times)):
            frame_to_timestamp[i + 1] = frame_times_model.get_frame_time(i)  # Frame numbers are 1-based
        logger.info(f"Falling back to model: Created mapping of {len(frame_to_timestamp)} frame numbers to timestamps")

    # Print the first few frame numbers and timestamps for debugging
    logger.info("First few frame numbers and timestamps:")
    for frame_number in sorted(list(frame_to_timestamp.keys()))[:5]:
        logger.info(f"Frame {frame_number}: {frame_to_timestamp[frame_number]}")

    # Create a mapping from KecmTimestamp to the nearest frame number
    timestamp_to_frame = {}
    for i, row in parsed_data_model.data.iterrows():
        timestamp = parsed_data_model.get_timestamp(row)
        if timestamp and timestamp != "nan":
            frame_index = frame_times_model.find_nearest_frame_index(timestamp)
            frame_number = frame_index + 1  # Frame numbers are 1-based
            timestamp_to_frame[timestamp] = frame_number

    # Collect rows for the output DataFrame
    output_rows = []

    # For each row in the parsed data
    for i, row in parsed_data_model.data.iterrows():
        # Get the timestamp from the parsed data
        timestamp = parsed_data_model.get_timestamp(row)

        if not timestamp or timestamp == "nan":
            logger.warning(f"No valid timestamp found for row {i}, skipping")
            continue

        # Get the frame number for this timestamp
        frame_number = timestamp_to_frame.get(timestamp, 1)  # Default to frame 1 if not found

        # Get the timestamp from frame_times.txt for this frame number
        frame_timestamp = frame_to_timestamp.get(frame_number, "")

        # Create a new row with frame number, timestamp from frame_times.txt, and KecmTimestamp from parsed_data.txt
        new_row = {
            "frame": frame_number,
            "timestamp": frame_timestamp,  # Use timestamp from frame_times.txt
            "KecmTimestamp": timestamp  # Include the original timestamp from parsed_data.txt
        }

        # Add control inputs data
        for col in control_inputs_model.data.columns:
            if not control_inputs_model.data.empty:
                new_row[col] = control_inputs_model.data.iloc[0].get(col, "")

        # Add parsed data
        for col in parsed_data_model.data.columns:
            new_row[col] = row.get(col, "")

        # Add the row to our collection
        output_rows.append(new_row)

    # Create the output DataFrame from all collected rows at once
    output_df = pd.DataFrame(output_rows)

    # Save the output file
    output_df.to_csv(output_path, index=False)

    # Now directly update the timestamp column in the output file to use the timestamps from frame_times.txt
    try:
        # Read the output file
        output_data = pd.read_csv(output_path)

        # Load frame times directly from frame_times.txt
        frame_to_timestamp = load_frame_times(frame_times_path, logger)

        # Update the timestamp column based on the frame number
        for i, row in output_data.iterrows():
            frame_number = int(row["frame"])
            if frame_number in frame_to_timestamp:
                output_data.at[i, "timestamp"] = frame_to_timestamp[frame_number]

        # Save the updated output file
        output_data.to_csv(output_path, index=False)
        logger.info(f"Updated output file with timestamps from frame_times.txt")
    except Exception as e:
        logger.error(f"Error updating timestamps in output file: {e}")

    logger.info(f"Output file saved to {output_path}")

    # Generate rangetime.txt file with first and last spectral timestamps
    try:
        # Get the first and last timestamps from the parsed data
        if not parsed_data_model.data.empty:
            # Check if timestamp column exists
            if "timestamp" not in parsed_data_model.data.columns:
                logger.warning("No 'timestamp' column found in parsed data. Looking for alternative timestamp columns.")
                # Try to find a column that might contain timestamps
                timestamp_cols = [col for col in parsed_data_model.data.columns if 'timestamp' in str(col).lower()]
                if timestamp_cols:
                    logger.info(f"Using '{timestamp_cols[0]}' as timestamp column")
                    timestamp_col = timestamp_cols[0]
                else:
                    logger.error("No timestamp column found in parsed data")
                    raise ValueError("No timestamp column found in parsed data")
            else:
                timestamp_col = "timestamp"

            # Get all timestamps and ensure they're valid
            all_timestamps = []
            for i, row in parsed_data_model.data.iterrows():
                timestamp = parsed_data_model.get_timestamp(row)
                if timestamp and timestamp != "nan" and timestamp.strip() and timestamp.lower() != "none":
                    all_timestamps.append(timestamp)

            if not all_timestamps:
                logger.error("No valid timestamps found in parsed data")
                raise ValueError("No valid timestamps found in parsed data")

            logger.debug(f"Found {len(all_timestamps)} valid timestamps")

            # Sort timestamps (they might be in string format)
            # This ensures correct chronological ordering
            all_timestamps.sort()

            # Get first and last timestamps
            first_timestamp = all_timestamps[0]
            last_timestamp = all_timestamps[-1]

            # Final check to ensure timestamps are not None or empty
            if first_timestamp.lower() == "none" or not first_timestamp.strip():
                logger.warning("First timestamp is 'None' or empty, trying to find another valid timestamp")
                # Try to find the first valid timestamp that's not None or empty
                for ts in all_timestamps:
                    if ts.lower() != "none" and ts.strip():
                        first_timestamp = ts
                        logger.info(f"Found alternative first timestamp: {first_timestamp}")
                        break
                else:
                    logger.warning("No valid alternative first timestamp found, using empty string")
                    first_timestamp = ""

            if last_timestamp.lower() == "none" or not last_timestamp.strip():
                logger.warning("Last timestamp is 'None' or empty, trying to find another valid timestamp")
                # Try to find the last valid timestamp that's not None or empty
                for ts in reversed(all_timestamps):
                    if ts.lower() != "none" and ts.strip():
                        last_timestamp = ts
                        logger.info(f"Found alternative last timestamp: {last_timestamp}")
                        break
                else:
                    logger.warning("No valid alternative last timestamp found, using empty string")
                    last_timestamp = ""

            logger.info(f"First timestamp: {first_timestamp}")
            logger.info(f"Last timestamp: {last_timestamp}")

            # Create the rangetime.txt file path in the same directory as the output file
            output_dir = Path(output_path).parent
            rangetime_path = output_dir / "rangetime.txt"

            # Write the timestamps in CSV format
            with open(rangetime_path, 'w') as f:
                f.write("first_timestamp,last_timestamp\n")
                f.write(f"{first_timestamp},{last_timestamp}\n")

            logger.info(f"Rangetime file saved to {rangetime_path}")
        else:
            logger.error("Cannot create rangetime.txt: No parsed data available")
    except Exception as e:
        logger.error(f"Error creating rangetime.txt file: {e}")

def generate_output_on_startup() -> None:
    """Generate the output file on application startup using the example files."""
    # Get the directory of the example files
    example_dir = Path("ExampleFiles")

    # Check if the example files exist
    frame_times_path = example_dir / "frame_times.txt"
    parsed_data_path = example_dir / "parsed_data.txt"
    control_inputs_path = example_dir / "control_inputs_log.txt"

    if not frame_times_path.exists():
        logger.error(f"Frame times file not found: {frame_times_path}")
        return
    if not parsed_data_path.exists():
        logger.error(f"Parsed data file not found: {parsed_data_path}")
        return
    if not control_inputs_path.exists():
        logger.error(f"Control inputs file not found: {control_inputs_path}")
        return

    # Generate the output file in the same directory as the input files
    output_path = example_dir / "output.txt"

    # Generate the output file
    generate_output_file(
        frame_times_path,
        parsed_data_path,
        control_inputs_path,
        output_path
    )
