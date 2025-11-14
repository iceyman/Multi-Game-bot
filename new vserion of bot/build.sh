#!/bin/bash

# This script will set up the Python virtual environment for the bot.

# --- Configuration ---
PYTHON_CMD="python3" # Use "python" if "python3" isn't on your path
MIN_PYTHON_VERSION="3.10"
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# --- Helper Functions ---
version_gt() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"
}

echo -e "${GREEN}Starting Bot V3 Setup...${NC}"

# --- Check 1: Check for requirements.txt ---
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${RED}ERROR: '$REQUIREMENTS_FILE' not found!${NC}"
    echo "This file is required to install the bot's libraries. Please make sure it's in the same folder."
    exit 1
fi
echo "✅ Found $REQUIREMENTS_FILE"

# --- Check 2: Check for Python ---
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}ERROR: Python ($PYTHON_CMD) is not installed.${NC}"
    echo "Please install Python ${MIN_PYTHON_VERSION} or newer to continue."
    echo "You can download it from ${YELLOW}https://www.python.org/${NC}"
    exit 1
fi

# --- Check 3: Check Python Version ---
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if ! version_gt $PYTHON_VERSION $MIN_PYTHON_VERSION && [ "$PYTHON_VERSION" != "$MIN_PYTHON_VERSION" ]; then
    echo -e "${RED}ERROR: Your Python version is $PYTHON_VERSION.${NC}"
    echo "This bot requires Python ${MIN_PYTHON_VERSION} or newer."
    echo "Please upgrade your Python installation."
    exit 1
fi
echo "✅ Found Python $PYTHON_VERSION (which is >= $MIN_PYTHON_VERSION)"

# --- Setup 1: Create Virtual Environment ---
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Existing '$VENV_DIR' folder found. Removing it to start fresh.${NC}"
    rm -rf "$VENV_DIR"
fi

echo "Creating virtual environment in './$VENV_DIR'..."
if !$PYTHON_CMD -m venv $VENV_DIR; then
    echo -e "${RED}ERROR: Failed to create virtual environment.${NC}"
    echo "Make sure you have the 'python3-venv' package (or equivalent) installed."
    exit 1
fi
echo "✅ Virtual environment created."

# --- Setup 2: Install Libraries ---
echo "Activating virtual environment and installing libraries from $REQUIREMENTS_FILE..."
# Activate venv and install requirements in one subshell
(
    source "$VENV_DIR/bin/activate" && \
    echo "Upgrading pip..." && \
    pip install --upgrade pip && \
    echo "Installing libraries..." && \
    pip install -r "$REQUIREMENTS_FILE"
)

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to install libraries.${NC}"
    echo "Please check the console output above for errors."
    exit 1
fi
echo "✅ All libraries installed successfully."

# --- Finish ---
echo -e "${GREEN}Build Complete!${NC}"
echo "The virtual environment is built."
echo "Returning to start.sh to run the bot."