"""Module for generating the output file from frame times, parsed data, and control inputs."""

from __future__ import annotations

import os
import pandas as pd
from pathlib import Path
from typing import Union, List, Dict, Any

from viewer.models import FrameTimesModel, SpectralDataModel, MetadataModel
from logging_config import get_logger

# Create a logger for this module
logger = get_logger("output_file")

def generate_output_file(
    frame_times_path: Union[str, Path],
    parsed_data_path: Union[str, Path],
    control_inputs_path: Union[str, Path],
    output_path: Union[str, Path] = "output.txt"
) -> None:
    """Generate an output file by combining data from frame times, parsed data, and control inputs.

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

    # Create a new DataFrame for the output
    output_df = pd.DataFrame()

    # Load frame times directly from frame_times.txt
    # The frame_times.txt file has a format like:
    # frame,timestamp
    # 1,20250613_132845.542
    # 2,20250613_132845.555
    # ...
    frame_to_timestamp = {}
    try:
        with open(frame_times_path, "r", encoding="utf-8") as f:
            # Skip header
            next(f)
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    frame_number = int(parts[0])
                    timestamp = parts[1]
                    frame_to_timestamp[frame_number] = timestamp

        logger.info(f"Loaded {len(frame_to_timestamp)} frame numbers and timestamps directly from {frame_times_path}")
    except Exception as e:
        logger.error(f"Error loading frame times directly from {frame_times_path}: {e}")
        # Fall back to using the model
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

        # Add the row to the output DataFrame
        output_df = pd.concat([output_df, pd.DataFrame([new_row])], ignore_index=True)

    # Save the output file
    output_df.to_csv(output_path, index=False)

    # Now directly update the timestamp column in the output file to use the timestamps from frame_times.txt
    try:
        # Read the output file
        output_data = pd.read_csv(output_path)

        # Load frame times directly from frame_times.txt
        frame_to_timestamp = {}
        with open(frame_times_path, "r", encoding="utf-8") as f:
            # Skip header
            next(f)
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    frame_number = int(parts[0])
                    timestamp = parts[1]
                    frame_to_timestamp[frame_number] = timestamp

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
