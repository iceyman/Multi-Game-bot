import os
import subprocess
import sys

# --- Configuration ---
# NOTE: This filename MUST match the renamed main script.
BOT_FILENAME = "Multi-Game_Dedicated_Monitor_Bot.py"
ENV_FILENAME = ".env"
REQUIREMENTS_FILE = "requirements.txt"

# Default configuration for the .env file
DEFAULT_ENV_CONTENT = f"""# --- Environment Variables for {BOT_FILENAME} ---

# 1. DISCORD CONFIGURATION (MANDATORY)
DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
ADMIN_CHANNEL_ID=000000000000000000  # Channel where RCON commands are allowed
MC_CHANNEL_ID=000000000000000000     # Channel for Minecraft status
PAL_CHANNEL_ID=000000000000000000     # Channel for Palworld status and auto-save logs
ASA_CHANNEL_ID=000000000000000000     # Channel for ARK: ASA status and auto-save logs

# 2. MINECRAFT RCON CONFIGURATION
MC_RCON_HOST="127.0.0.1"
MC_RCON_PORT=25575
MC_RCON_PASSWORD="YOUR_MC_RCON_PASSWORD_HERE"

# 3. PALWORLD RCON CONFIGURATION
PAL_RCON_HOST="127.0.0.1"
PAL_RCON_PORT=25576
PAL_RCON_PASSWORD="YOUR_PAL_RCON_PASSWORD_HERE"
PAL_SAVE_INTERVAL=30 # Auto-save interval in minutes

# 4. ASA RCON CONFIGURATION
ASA_RCON_HOST="127.0.0.1"
ASA_RCON_PORT=27020
ASA_RCON_PASSWORD="YOUR_ASA_RCON_PASSWORD_HERE"
ASA_SAVE_INTERVAL=60 # Auto-save interval in minutes
"""

def install_dependencies():
    """Installs required packages using pip."""
    print("--- 1. Installing Python Dependencies ---")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE])
        print("✅ Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during dependency installation: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Error: {REQUIREMENTS_FILE} not found. Please ensure it is in the same directory.")
        return False

def create_env_file():
    """Creates the .env file if it doesn't exist."""
    print(f"\n--- 2. Checking for Configuration File ({ENV_FILENAME}) ---")
    if os.path.exists(ENV_FILENAME):
        print(f"✅ {ENV_FILENAME} already exists. Skipping creation.")
        print("   Please ensure all placeholder values are updated inside the file.")
    else:
        with open(ENV_FILENAME, 'w') as f:
            f.write(DEFAULT_ENV_CONTENT)
        print(f"✅ {ENV_FILENAME} created successfully.")
        print("⚠️ ACTION REQUIRED: You must open the .env file and replace all 'YOUR_..._HERE' and '0000...' placeholders.")

def create_runner_scripts():
    """Creates basic start scripts for convenience."""
    print("\n--- 3. Creating Runner Scripts ---")

    # Windows Batch File
    bat_content = f"""@echo off
echo Starting the Multi-Game Dedicated Monitor Bot...
python "{BOT_FILENAME}"
echo Bot stopped or crashed. Press any key to close.
pause
"""
    with open("start_bot.bat", 'w') as f:
        f.write(bat_content)
    print("✅ Created start_bot.bat (Windows)")

    # Unix Shell Script
    sh_content = f"""#!/bin/bash
echo "Starting the Multi-Game Dedicated Monitor Bot..."
python3 "{BOT_FILENAME}"
echo "Bot stopped or crashed."
"""
    with open("start_bot.sh", 'w') as f:
        f.write(sh_content)

    try:
        os.chmod("start_bot.sh", 0o755)
        print("✅ Created and set executable permission for start_bot.sh (Linux/macOS)")
    except Exception:
        print("✅ Created start_bot.sh (Linux/macOS - NOTE: You may need to run 'chmod +x start_bot.sh' manually.)")

def main():
    print(f"\n=======================================================")
    print(f"   {BOT_FILENAME} Setup Script")
    print(f"=======================================================\n")
    
    if install_dependencies():
        create_env_file()
        create_runner_scripts()
    
    print(f"\n=======================================================")
    print("SETUP COMPLETE.")
    print(f"1. **REQUIRED:** Edit the **{ENV_FILENAME}** file with your token, channel IDs, and RCON passwords.")
    print("2. Run the bot using **start_bot.sh** (Linux/macOS) or **start_bot.bat** (Windows).")
    print("=======================================================")

if __name__ == "__main__":
    main()
