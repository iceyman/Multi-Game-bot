#!/bin/bash
# This script runs the bot inside its virtual environment.
echo "Starting Game Server Bot V3..."
# Get the directory this script is in
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Activate the venv and run the bot
source "$DIR/venv/bin/activate"
python3 "$DIR/game_bot_starter.py"
echo "Bot has stopped."