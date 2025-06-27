# Video Spectra Viewer

A desktop application for inspecting video frames alongside synchronized spectral data. It allows interactive navigation through frames, editing per-frame metadata, and exporting combined data to CSV files.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
- [Technologies Used](#technologies-used)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)
- [Support](#support)
- [Project Status](#project-status)

## Overview
Video Spectra Viewer loads a video together with corresponding frame timestamps, spectral readings and metadata. The application synchronises these data sources so you can step through the video frame by frame while inspecting the nearest spectral measurement. Edited metadata and spectra can be exported for further analysis.

## Installation
1. Create and activate a Python virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Generate the Qt UI Python code if you modify the `.ui` file:
   ```bash
   ./generate_ui_py.sh
   ```

## Usage
Run the GUI application:
```bash
python main.py
```
Without arguments the viewer loads sample data from the `ExampleFiles/` directory. Use the **Import Data** button to load your own dataset (video, frame times, spectral data and metadata). Navigate with **Next** and **Previous** to review frames, update the metadata table and export the results with **Export Metadata**.

The `viewer/video_spectra_viewer.py` module also exposes a command line interface:
```bash
python viewer/video_spectra_viewer.py <video> <spectra> [--controls CONTROL_LOG]
```

## Features
- Video playback with frame-by-frame navigation
- Graph of spectral intensities synchronized with the current frame
- Editable metadata per frame
- Import video, spectral data and frame-time mappings
- Analysis action to jump to the first spectral record
- Export combined metadata and spectra to CSV

## Technologies Used
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI
- [OpenCV](https://opencv.org/) for video handling
- [Matplotlib](https://matplotlib.org/) for plotting spectra
- [pandas](https://pandas.pydata.org/) for data processing

## Contributing
Contributions are welcome! Fork the repository and submit a pull request. Please ensure code is formatted with standard tools and include tests when appropriate.

## License
This project is licensed under the [MIT License](LICENSE).

## Credits
Developed by [marlefranco](https://github.com/marlefranco) and contributors.

## Support
Please use the issue tracker on GitHub to report problems or request features.

## Project Status
Active development

