import os
import subprocess
import sys
from textwrap import dedent

# --- Configuration for Installer ---
DOTENV_PATH = '.env'
REQUIREMENTS_PATH = 'requirements.txt'
BOT_FILE_NAME = 'Multi-Game Dedicated Monitor Bot.py'

# Template for the .env file with essential configuration placeholders
ENV_TEMPLATE = dedent(f"""\
    # ======================================================================================================
    # REQUIRED CONFIGURATION FOR DISCORD BOT
    # 
    # 1. DISCORD_TOKEN: Get this from the Discord Developer Portal for your bot.
    # 2. ADMIN_CHANNEL_ID: The ID of the Discord channel where RCON commands must be executed (e.g., !ban_pal).
    # 3. Game Channel IDs: The channel IDs where status messages and logs for each game will be posted.
    # 
    # NOTE: You MUST replace all placeholder values (e.g., 'YOUR_DISCORD_TOKEN_HERE') with your actual credentials.
    # ======================================================================================================

    DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
    ADMIN_CHANNEL_ID=000000000000000000  # REPLACE with the ID of your Admin/RCON command channel.

    # --- GAME SPECIFIC CHANNEL IDs ---
    MC_CHANNEL_ID=000000000000000001    # REPLACE with the ID for Minecraft logs
    PAL_CHANNEL_ID=000000000000000002   # REPLACE with the ID for Palworld logs
    ASA_CHANNEL_ID=000000000000000003   # REPLACE with the ID for ARK: ASA logs

    # ======================================================================================================
    # RCON CONFIGURATION
    # Ensure RCON is enabled and correctly configured on your game servers.
    # ======================================================================================================

    # --- MINECRAFT RCON ---
    MC_RCON_HOST="127.0.0.1"
    MC_RCON_PORT=25575
    MC_RCON_PASSWORD="YOUR_MC_RCON_PASSWORD_HERE"

    # --- PALWORLD RCON ---
    PAL_RCON_HOST="127.0.0.1"
    PAL_RCON_PORT=25576
    PAL_RCON_PASSWORD="YOUR_PAL_RCON_PASSWORD_HERE"
    PAL_SAVE_INTERVAL=30 # Auto-save interval in minutes

    # --- ARK: ASA RCON ---
    ASA_RCON_HOST="127.0.0.1"
    ASA_RCON_PORT=25577
    ASA_RCON_PASSWORD="YOUR_ASA_RCON_PASSWORD_HERE"
    ASA_SAVE_INTERVAL=60 # Auto-save interval in minutes
""")


def check_python_version():
    """Checks if the required Python version (3.8+) is running."""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required.")
        print(f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected.")

def install_dependencies():
    """Installs required Python packages using pip."""
    print(f"\n⚙️ Installing dependencies from {REQUIREMENTS_PATH}...")
    try:
        # Use subprocess to run pip install
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', REQUIREMENTS_PATH])
        print("✅ Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during dependency installation. Check your internet connection and pip setup. Error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{REQUIREMENTS_PATH}'. Ensure the file exists.")
        sys.exit(1)

def create_env_file():
    """Creates the .env configuration file."""
    if os.path.exists(DOTENV_PATH):
        print(f"⚠️ '{DOTENV_PATH}' already exists. Skipping creation.")
        return
    
    try:
        with open(DOTENV_PATH, 'w') as f:
            f.write(ENV_TEMPLATE)
        print(f"✅ Created configuration file: '{DOTENV_PATH}'")
        print("   -> Please open this file and fill in all the placeholder values!")
    except IOError as e:
        print(f"❌ Error writing '{DOTENV_PATH}'. Check permissions. Error: {e}")
        sys.exit(1)

def main():
    print("==============================================")
    print("🤖 Multi-Game RCON Bot Setup Wizard")
    print("==============================================")
    
    check_python_version()
    
    if not os.path.exists(REQUIREMENTS_PATH):
        print(f"❌ FATAL: '{REQUIREMENTS_PATH}' not found. Please ensure it is in the same directory as the installer.")
        sys.exit(1)

    install_dependencies()
    create_env_file()

    print("\n==============================================")
    print("🎉 SETUP COMPLETE! NEXT STEPS:")
    print("==============================================")
    print(f"1. **Edit the '.env' file** that was just created. You must fill in the Discord Token and all RCON passwords and channel IDs.")
    print(f"2. To run the bot, use either `python {BOT_FILE_NAME}` or the provided run scripts:")
    print("   - Windows: Double-click `start_bot.bat`")
    print("   - Linux/macOS: Run `./start_bot.sh` (you may need to run `chmod +x start_bot.sh` first)")
    print("==============================================")

if __name__ == "__main__":
    main()
