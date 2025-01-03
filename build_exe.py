import subprocess
import sys
import os


def create_exe(script_name):
    # Define the PyInstaller command
    if "server.py" in script_name:
        command = [
            'pyinstaller',
            '--onefile',  # Single executable file
            script_name
        ]

        # Run PyInstaller command
        subprocess.check_call(command)
    elif "client.py" in script_name:
        command = [
            'pyinstaller',
            '--onefile',  # Single executable file
            '--windowed',  # Hide the console window (for GUI apps)
            script_name
        ]

        # Run PyInstaller command
        subprocess.check_call(command)


if __name__ == '__main__':
    # First argument is the script to convert into an EXE
    if len(sys.argv) < 2:
        print("Please provide the script name (client.py or server.py)")
        sys.exit(1)

    script_file = sys.argv[1]

    if not os.path.exists(script_file):
        print(f"The file {script_file} does not exist.")
        sys.exit(1)

    create_exe(script_file)
