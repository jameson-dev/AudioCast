#!/bin/sh

LOG_FILE="logfile.log"
exec >> "$LOG_FILE" 2>&1

# Arguments passed from PagerMon
ADDRESS="$1"       # Address (Integer)
MESSAGE="$2"       # Message (Text)
DATA="$3"          # Data (JSON)
OUTPUT_DIR="/home/Administrator/AudioCast/server/rfa"  # Directory to save output files

# Keywords to search for (one per line)
KEYWORDS="ADDITIONAL
STOP FOR
TREE DOWN
ROAD CRASH RESCUE
VEHICLE ACCIDENT
RESCUE VERTICAL
RESCUE FROM HEIGHTS
RESCUE FROM DEPTHS
RESCUE CONFINED SPACE
SEVERE WEATHER
SES ASSIST POLICE
VEHICLE RECOVERY
SES PROVIDE EQUIPMENT
SEARCH
FLOODING SALVAGE"

# Function to check if a message contains any keyword
contains_keyword() {
    message="$1"
    while IFS= read -r keyword; do
        if echo "$message" | grep -iq "$keyword"; then
            echo "$keyword"  # Output the matched keyword
            return 0        # Return success if matched
        fi
    done <<EOF
$KEYWORDS
EOF
    return 1  # Return failure if no match found
}

# Initialize MATCHED_KEYWORD
MATCHED_KEYWORD=""

# Call the function and capture the result and exit status
if result=$(contains_keyword "$MESSAGE"); then
    MATCHED_KEYWORD="$result"  # Assign matched keyword to variable
fi

if [ -n "$MATCHED_KEYWORD" ]; then
    # Extract basic information from the JSON using grep and sed
    ID=$(echo "$DATA" | grep -o '"id":"[^"]*"' | sed 's/"id":"\(.*\)"/\1/')
    TIMESTAMP=$(echo "$DATA" | grep -o '"timestamp":"[^"]*"' | sed 's/"timestamp":"\(.*\)"/\1/')

    # Create a timestamped file named after the matched keyword
    FILENAME="$OUTPUT_DIR/$(echo "$MATCHED_KEYWORD" | tr ' ' '_')_${TIMESTAMP:-unknown}_${ID:-unknown}.rfa"

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
