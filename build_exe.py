import subprocess
import sys
import os

def create_exe(script_name):
    print(f"Running PyInstaller for {script_name}")

    # Get the absolute path to the script
    script_path = os.path.abspath(script_name)

    # Log the current directory for debugging
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script path: {script_path}")

    # Define the PyInstaller command
    if "server.py" in script_name:
        command = f'pyinstaller --onefile --add-data "../assets/audiocast.ico;assets" --distpath dist\\server --icon=assets/audiocast.ico {script_path}'
    elif "client.py" in script_name:
        command = f'pyinstaller --onefile --add-data "../assets/audiocast.ico;assets" --distpath dist\\client --icon=assets/audiocast.ico --windowed {script_path}'
    else:
        print("Invalid script name. Use client.py or server.py.")
        sys.exit(1)

    # Run PyInstaller command and capture output
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed for {script_name}. Error: {e}")
        sys.exit(1)

    # Log the contents of the dist folder after PyInstaller runs
    print(f"Contents of dist folder after build:")
    dist_contents = os.listdir('dist')
    for item in dist_contents:
        print(item)


if __name__ == '__main__':
    # First argument is the script to convert into an EXE
    if len(sys.argv) < 2:
        print("Please provide the script name (client.py or server.py)")
        sys.exit(1)

    script_file = sys.argv[1]

    # Check if the file exists relative to the current working directory
    if not os.path.exists(script_file):
        print(f"The file {script_file} does not exist in the current directory.")
        sys.exit(1)

    create_exe(script_file)
