import subprocess
import sys
import os


def create_exe():
    # Path to your main Python file
    main_script = "your_main_script.py"

    # Define the PyInstaller command
    command = [
        'pyinstaller',
        '--onefile',           # Single executable file
        '--windowed',          # Hide the console window (for GUI apps)
        main_script
    ]

    # Run PyInstaller command
    subprocess.check_call(command)


if __name__ == '__main__':
    create_exe()
