#!/bin/bash
# This is the main script to run your bot.
# It automatically runs the one-time setup (build.sh) if it hasn't been run yet.

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VENV_DIR="$DIR/venv"
BUILD_SCRIPT="$DIR/build.sh"
RUN_SCRIPT="$DIR/run.sh"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Make sure the other scripts are executable, just in case
if [ -f "$BUILD_SCRIPT" ]; then
    chmod +x "$BUILD_SCRIPT"
fi
if [ -f "$RUN_SCRIPT" ]; then
    chmod +x "$RUN_SCRIPT"
fi

# Check if the virtual environment folder exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}Virtual environment not found. Running the one-time build script...${NC}"
    
    # Run build.sh
    "$BUILD_SCRIPT"
    
    # Check if build.sh failed
    if [ $? -ne 0 ]; then
        echo -e "${RED}Build script failed. Please check the errors above. Exiting.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Build complete. Now starting the bot...${NC}"
fi

# Now that we know venv exists, run the bot
echo -e "${GREEN}Starting the V3 Bot...${NC}"
"$RUN_SCRIPT"