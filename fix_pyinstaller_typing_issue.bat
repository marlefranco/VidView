@echo off
echo Fixing PyInstaller compatibility issue with 'typing' package...
pip uninstall -y typing
echo.
echo The 'typing' package has been removed. You can now run PyInstaller with:
echo pyinstaller --name=VidView --windowed --add-data "ExampleFiles;ExampleFiles" --add-data "ui;ui" --add-data "*.png;." main.py
echo.
echo Press any key to exit...
pause > nul