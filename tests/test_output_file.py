"""Tests for the output_file module."""

import os
import unittest
from pathlib import Path

import pandas as pd

from output_file import generate_output_file


class TestOutputFile(unittest.TestCase):
    """Tests for the output_file module."""

    def setUp(self):
        """Set up test fixtures."""
        self.example_dir = Path("ExampleFiles")
        self.frame_times_path = self.example_dir / "frame_times.txt"
        self.parsed_data_path = self.example_dir / "parsed_data.txt"
        self.control_inputs_path = self.example_dir / "control_inputs_log.txt"
        self.output_path = self.example_dir / "test_output.txt"

    def tearDown(self):
        """Tear down test fixtures."""
        # Remove the output file if it exists
        if self.output_path.exists():
            os.remove(self.output_path)

    def test_generate_output_file(self):
        """Test that the output file is generated correctly."""
        # Generate the output file
        generate_output_file(
            self.frame_times_path,
            self.parsed_data_path,
            self.control_inputs_path,
            self.output_path
        )

        # Check that the output file exists
        self.assertTrue(self.output_path.exists())

        # Check that the output file is not empty
        self.assertGreater(os.path.getsize(self.output_path), 0)

        # Load the output file and check its structure
        output_df = pd.read_csv(self.output_path)

        # Check that the output file has the expected columns
        self.assertIn("frame", output_df.columns)
        self.assertIn("timestamp", output_df.columns)

        # Print the columns for debugging
        print("Output file columns:", output_df.columns.tolist())

        # Check for essential columns from control_inputs_log.txt
        self.assertIn("filename1", output_df.columns)
        self.assertIn("filename2", output_df.columns)
        self.assertIn("fps", output_df.columns)

        # Check that the output file has the expected number of rows
        # This should match the number of rows in the parsed data
        parsed_data_df = pd.read_csv(self.parsed_data_path, skiprows=1)  # Skip FILE_START
        self.assertEqual(len(output_df), len(parsed_data_df))

        # Check that the frame numbers are within the expected range
        self.assertTrue(all(output_df["frame"] >= 1))
        self.assertTrue(all(output_df["frame"] <= len(pd.read_csv(self.frame_times_path))))

        # Print information about the timestamp column
        print("Sample timestamps:", output_df["timestamp"].head().tolist())
        print("Number of NaN values in timestamp column:", output_df["timestamp"].isna().sum())

        # Print indices of rows with NaN values
        nan_indices = output_df.index[output_df["timestamp"].isna()].tolist()
        print("Indices of rows with NaN values:", nan_indices[:10] if nan_indices else "None")

        # Check that there are few NaN values in the timestamp column (less than 1%)
        nan_count = output_df["timestamp"].isna().sum()
        total_count = len(output_df["timestamp"])
        nan_percentage = (nan_count / total_count) * 100
        print(f"NaN percentage in timestamp column: {nan_percentage:.2f}%")
        self.assertLess(nan_percentage, 1.0, "Too many NaN values in timestamp column")


if __name__ == "__main__":
    unittest.main()
