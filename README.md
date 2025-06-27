# Video Spectra Viewer

A PyQt6 app for inspecting video and synchronized spectral data frame by frame.
It allows loading custom datasets, editing per-frame metadata and exporting the
results to CSV.

---

## Features
- Video player
- Synchronized spectral graph
- Editable metadata per frame
- Import video, spectral data and frame-time mappings
- One-click analysis to locate the first spectral entry
- Export combined metadata and spectra to CSV

---

## Setup
Follow the steps below to set up the application for development on a **Windows system** using **PyCharm IDE**.

### Step 1: Install Windows Subsystem for Linux (WSL)
WSL allows you to run a Linux environment directly on Windows. This step is essential if you want to run Bash scripts like `generate_ui_py.sh`. Follow these instructions to set it up:

1. **Open PowerShell as Administrator**:
   - Right-click the Start Menu and select `Windows Terminal (Admin)` or `PowerShell (Admin)`.

2. **Install WSL**:
   - Run the following command:
     ```powershell
     wsl --install
     ```
   - This will install WSL and the default Linux distribution (usually Ubuntu).
   - Restart your computer if prompted.

3. **Launch WSL**:
   - Open the **Start Menu** and search for your installed Linux distribution (e.g., Ubuntu).
   - When prompted, set up a username and password for your Linux user account.

4. **Access Your Project**:
   - Navigate to your project folder in WSL by running:
     ```bash
     cd /mnt/c/Users/<YourUsername>/PycharmProjects/VideoViewer
     ```

---

### Step 2: Set Up the Virtual Environment
1. Open the project in **PyCharm IDE**.
2. Open a WSL terminal in PyCharm or use the integrated terminal (ensure you're in WSL mode).
3. Create and activate the virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Linux/macOS
   # source venv/bin/activate
   ```
   On Windows, you can also activate the virtual environment with:
   ```bash
   .venv\Scripts\activate
   ```

4. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
   The application requires PyQt6.
3. Generate the Python file for the Qt UI:

---

### Step 3: Generate the Python File for the Qt UI
The `generate_ui_py.sh` script converts Qt `.ui` files into Python `.py` files.

1. Ensure the script has executable permissions (skip this step if already done):
   ```bash
   chmod +x generate_ui_py.sh
   ```

2. Run the script directly:
   ```bash
   ./generate_ui_py.sh
   ```
   This will generate the Python file (`.py`) corresponding to the `.ui` file in your project.

3. If any errors occur (such as missing PyQt), ensure PyQt6 is installed within your virtual environment:
   ```bash
   pip install PyQt6
   ```
   Without arguments the application loads sample data from the
   `ExampleFiles/` directory.

## Command-line usage
- `python main.py` - start the GUI application.
- `pytest` - run the test suite located in the `tests/` directory.
- `pyinstaller --onefile main.py` - build a standalone Windows executable.
---

### Step 4: Run the Application
Once everything is set up, you can run the application by executing the main Python script:

1. **Activate the Virtual Environment** (if not already activated):
   ```bash
   source .venv/bin/activate   # On Linux/Mac/WSL
   .venv\Scripts\activate      # On Windows
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```

3. **Optional: Specify Configuration or Parameters**:
   If the application supports configuration files or command-line arguments, ensure they are passed correctly when launching the `main.py` file.

## Working in PyCharm
1. Open the project directory in PyCharm.
2. Configure the interpreter to use the `venv` created above.
3. Create a run configuration that launches `main.py`.
4. Run or debug the application directly from the IDE.

---

Let me know if you need additional clarifications or enhancements! 😊