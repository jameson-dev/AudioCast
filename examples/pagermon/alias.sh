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
    # Extract the ID from the JSON using grep and sed (fallback to 'unknown' if not found)
    ID=$(echo "$DATA" | grep -o '"id":"[^"]*"' | sed 's/"id":"\(.*\)"/\1/')
    ID=${ID:-unknown}

    # Get the current system timestamp in the format YYYYMMDD_HHMMSS
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

    # Extract the priority from the message (P1, P2, or P3)
    PRIORITY=$(echo "$MESSAGE" | grep -o ' P[123] ')
    PRIORITY=${PRIORITY:-P?}

    # Create a timestamped file named after the matched keyword and priority
    FILENAME="$OUTPUT_DIR/${PRIORITY}_$(echo "$MATCHED_KEYWORD" | tr ' ' '_')_${TIMESTAMP}_${ID}.rfa"

    # Write minimal details to the file
    {
        echo "Incident Detected: $MATCHED_KEYWORD"
        echo "Priority: $PRIORITY"
        echo "Address: $ADDRESS"
        echo "Message: $MESSAGE"
        echo "System Timestamp: $TIMESTAMP"
        echo "ID: $ID"
    } > "$FILENAME"else
    echo "No keyword match found in the message."
fi
