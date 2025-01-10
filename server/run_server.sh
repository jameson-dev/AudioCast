#!/bin/bash

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