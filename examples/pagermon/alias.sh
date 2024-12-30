#!/bin/bash

# Arguments passed from PagerMon
ADDRESS="$1"       # Address (Integer)
MESSAGE="$2"       # Message (Text)
DATA="$3"          # Data (JSON)
OUTPUT_DIR="/home/Administrator/AudioCast/server/rfa"  # Directory to save output files

# Keywords to search for (modify this array to add more keywords)
KEYWORDS=("TREE DOWN" "ROAD CRASH RESCUE" "VEHICLE ACCIDENT" "RESCUE VERTICAL" "RESCUE FROM HEIGHTS" "RESCUE FROM DEPTHS" "RESCUE CONFINED SPACE" "SEVERE WEATHER" "SES ASSIST POLICE" "VEHICLE RECOVERY" "SES PROVIDE EQUIPMENT" "SEARCH" "FLOODING SALVAGE")

# Function to check if a message contains any keyword
contains_keyword() {
    local message="$1"
    for keyword in "${KEYWORDS[@]}"; do
        if echo "$message" | grep -iq "$keyword"; then
            echo "$keyword"
            return 0
        fi
    done
    return 1
}

# Check if the message contains any keyword
MATCHED_KEYWORD=$(contains_keyword "$MESSAGE")
if [[ $? -eq 0 ]]; then
    # Extract basic information from the JSON using grep and sed
    ID=$(echo "$DATA" | grep -o '"id":"[^"]*"' | sed 's/"id":"\(.*\)"/\1/')
    TIMESTAMP=$(echo "$DATA" | grep -o '"timestamp":"[^"]*"' | sed 's/"timestamp":"\(.*\)"/\1/')

    # Create a timestamped file named after the matched keyword
    FILENAME="$OUTPUT_DIR/${MATCHED_KEYWORD// /_}_${TIMESTAMP:-unknown}_${ID:-unknown}.rfa"

    # Write minimal details to the file
    {
        echo "Incident Detected: $MATCHED_KEYWORD"
        echo "Address: $ADDRESS"
        echo "Message: $MESSAGE"
        echo "Timestamp: ${TIMESTAMP:-unknown}"
        echo "ID: ${ID:-unknown}"
    } > "$FILENAME"

    echo "File created: $FILENAME"
else
    echo "No keyword match found in the message."
fi