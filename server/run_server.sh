#!/bin/bash

# Check Python version
REQUIRED_PYTHON="3.10"
PYTHON_VERSION=$(python3 --version | awk '{print $2}')

if [[ $(echo -e "$REQUIRED_PYTHON\n$PYTHON_VERSION" | sort -V | head -n 1) != "$REQUIRED_PYTHON" ]]; then
    echo "Error: Python 3.10 or higher is required. Installed version is $PYTHON_VERSION."
    exit 1
fi

# Ensure the script is run from the directory where it's located
cd "$(dirname "$0")"

# Activate the virtual environment, or create it if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install required dependencies if they're not already installed
REQUIREMENTS_FILE="server_requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing required dependencies..."
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "server_requirements.txt not found. Skipping dependency installation."
fi

# Run the server
echo "Starting server..."
python3 server.py "$@"