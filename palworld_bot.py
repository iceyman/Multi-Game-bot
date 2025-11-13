import os
import discord
import asyncio
from discord.ext import commands, tasks
import logging
# --- NEW RCON LIBRARY IMPORT ---
try:
    from rcon import RconAsync
except ImportError:
    # This prevents crash if the user hasn't installed the library yet
    RconAsync = None 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('PalBot')

# --- CONFIGURATION (START HERE!) ---
# ⚠️ WARNING: For production environments, it is HIGHLY recommended to use
# Environment Variables (as described in SETUP_INSTRUCTIONS.md) for security.
#
# If the environment variable is not found, the script uses the hardcoded string below.
# Newcomers can quickly enter their credentials by replacing the 'YOUR_...' placeholders.

# 1. DISCORD SETTINGS: Get these from your Discord Developer Portal.
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', 'YOUR_DISCORD_BOT_TOKEN_HERE')
TARGET_CHANNEL_ID = os.getenv('TARGET_CHANNEL_ID', 'YOUR_CHANNEL_ID_HERE')

# 2. RCON SETTINGS: Get these from your Palworld server configuration.
RCON_HOST = os.getenv('RCON_HOST', '127.0.0.1')
RCON_PORT = int(os.getenv('RCON_PORT', 25575)) # Default RCON port for Palworld is 25575
RCON_PASSWORD = os.getenv('RCON_PASSWORD', 'YOUR_RCON_PASSWORD_HERE')
# --- CONFIGURATION (END HERE!) ---

# --- INITIALIZATION AND VALIDATION ---

# Check if required values were provided (either via hardcode or environment variables)
if DISCORD_TOKEN == 'YOUR_DISCORD_BOT_TOKEN_HERE' or TARGET_CHANNEL_ID == 'YOUR_CHANNEL_ID_HERE':
    logger.critical("FATAL: Discord credentials (TOKEN and CHANNEL_ID) must be updated.")
    logger.critical("Please update the values in the 'CONFIGURATION' block at the top of the script.")
    exit(1)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True # Required to read messages for command processing
bot = commands.Bot(command_prefix='!', intents=intents)

# --- RCON IMPLEMENTATION (Real RCON Client) ---

async def _send_rcon_command(command: str) -> str:
    """
    Connects to the Palworld server via RCON and sends a command using python-rcon.
    """
    logger.info(f"Executing RCON command: {command} to {RCON_HOST}:{RCON_PORT}")

    if not RconAsync:
        raise ImportError("RCON library not found. Please run: pip install python-rcon")

    if not RCON_PASSWORD or RCON_PASSWORD == 'YOUR_RCON_PASSWORD_HERE':
        raise ConnectionError("RCON_PASSWORD not configured.")

    rcon = None
    try:
        # Establish connection
        rcon = RconAsync(RCON_HOST, RCON_PORT, RCON_PASSWORD)
        await rcon.connect()
        
        # Send command
        response = await rcon.send(command)
        
        return response.strip()

    except Exception as e:
        logger.error(f"RCON Error executing '{command}': {e}")
        # Convert any RCON library exception into our standard ConnectionError
        raise ConnectionError(f"RCON failed: {e}")
    finally:
        # Ensure connection is closed
        if rcon:
            if hasattr(rcon, 'close'):
                await rcon.close()

async def _get_current_players() -> list[dict]:
    """
    Gets a list of currently online players with their Name, PlayerUID, and SteamID.
    Returns: A list of dictionaries, e.g., [{'name': 'Player1', 'player_uid': '123...', 'steam_id': '765...'}]
    """
    try:
        response = await _send_rcon_command("ShowPlayers")
    except ConnectionError:
        raise 

    players = []
    # Palworld RCON usually returns "Name, PlayerUID, SteamID" followed by a list of players
    lines = response.strip().split('\n')
    
    if len(lines) > 1:
        # Start parsing after the header line
        for line in lines[1:]: 
            parts = [p.strip() for p in line.split(',')]
            # Ensure we have at least three parts: Name, PlayerUID, SteamID
            if len(parts) >= 3 and parts[0] and parts[0].lower() != 'name':
                players.append({
                    'name': parts[0],
                    'player_uid': parts[1],
                    'steam_id': parts[2]
                })
                
    return players

# --- BACKGROUND MONITORING TASK ---

# Stores the last known set of player NAMES
last_player_set = set()

@tasks.loop(seconds=5.0)
async def monitor_rcon_task():
    """Periodically checks the server for player joins and leaves."""
    global last_player_set
    
    if not bot.is_ready():
        return
        
    channel = bot.get_channel(int(TARGET_CHANNEL_ID))
    if not channel:
        logger.warning(f"Target channel ID {TARGET_CHANNEL_ID} not found.")
        return

    try:
        current_players_data = await _get_current_players()
        current_player_set = {p['name'] for p in current_players_data} # Extract names for comparison
    except ConnectionError as ce:
        # Log RCON specific connection errors, but keep the bot loop running.
        logger.warning(f"RCON Monitor skipped due to connection error: {ce}")
        return

    if not last_player_set:
        # First run, just initialize the set
        last_player_set = current_player_set
        logger.info(f"RCON Monitor initialized with {len(current_player_set)} players.")
        return

    # 1. Check for JOINS
    players_joined = current_player_set - last_player_set
    for player in players_joined:
        message = f"🟢 **{player}** has joined the server! Welcome!"
        await channel.send(message)
        logger.info(f"Joined: {player}")

    # 2. Check for LEAVES
    players_left = last_player_set - current_player_set
    for player in players_left:
        message = f"🔴 **{player}** has left the server. See ya!"
        await channel.send(message)
        logger.info(f"Left: {player}")

    # Update the last known state
    last_player_set = current_player_set

# --- DISCORD BOT EVENTS ---

@bot.event
async def on_ready():
    """Fires when the bot successfully connects to Discord."""
    try:
        # Set bot activity status
        await bot.change_presence(activity=discord.Game(name="Palworld Server"))
        
        channel = bot.get_channel(int(TARGET_CHANNEL_ID))
        if channel:
            await channel.send("🤖 **PalBot Online** and ready to monitor the server!")
            logger.info(f"Bot connected as {bot.user.name}. Monitoring channel {channel.name}.")
        else:
            logger.error(f"Target channel ID {TARGET_CHANNEL_ID} is invalid or bot cannot see it.")
            
        # Start the background monitoring task
        if not monitor_rcon_task.is_running():
            monitor_rcon_task.start()
            
    except Exception as e:
        logger.error(f"Error during on_ready or startup: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Handles errors when processing commands."""
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need **Administrator** permissions to use that command.")
        return
    logger.error(f"Command error: {error}")
    await ctx.send(f"An error occurred: {error}")

# --- DISCORD BOT COMMANDS ---

@bot.command(name='status')
async def status_command(ctx):
    """Shows the current status (player count and names) of the Palworld server."""
    try:
        current_players_data = await _get_current_players()
        player_count = len(current_players_data)
        player_names = [p['name'] for p in current_players_data]
        player_list = "\n- ".join(player_names) if player_names else "No players currently online."
        
        embed = discord.Embed(
            title="🎮 Palworld Server Status",
            description=f"**{RCON_HOST}:{RCON_PORT}**",
            color=0x00FF00 if player_count > 0 else 0xFF0000
        )
        embed.add_field(name="Current Players", value=f"**{player_count}** online", inline=False)
        
        if player_count > 0:
            embed.add_field(name="Player List", value=f"- {player_list}", inline=False)
            
        await ctx.send(embed=embed)
    except ConnectionError as e:
        await ctx.send(f"❌ Server Status Check Failed: {e}. Check RCON credentials and server status.")
    except ImportError as e:
        await ctx.send(f"❌ Setup Error: {e}")

@bot.command(name='players')
@commands.has_permissions(administrator=True)
async def players_command(ctx):
    """Lists online players with their unique IDs needed for Kick/Ban commands."""
    try:
        current_players_data = await _get_current_players()
        player_count = len(current_players_data)

        if player_count == 0:
            await ctx.send("ℹ️ No players are currently online.")
            return

        response_lines = ["**Online Players (Use SteamID for Kick/Ban):**\n"]
        for p in current_players_data:
            response_lines.append(f"• **{p['name']}** (UID: `{p['steam_id']}`)")
        
        # Split the message into chunks if it's too long for Discord (max 2000 chars)
        message_chunks = []
        current_chunk = ""
        for line in response_lines:
            if len(current_chunk) + len(line) > 1900:
                message_chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += line + "\n"
        if current_chunk:
            message_chunks.append(current_chunk)

        for chunk in message_chunks:
            await ctx.send(chunk)

    except ConnectionError as e:
        await ctx.send(f"❌ Failed to retrieve player list: {e}. Check RCON credentials and server status.")
    except ImportError as e:
        await ctx.send(f"❌ Setup Error: {e}")

@bot.command(name='broadcast')
@commands.has_permissions(administrator=True)
async def broadcast_command(ctx, *, message: str):
    """Sends a message to all players in the game using RCON Broadcast."""
    if not message:
        await ctx.send("Please provide a message to broadcast, e.g., `!broadcast Server restarting soon!`")
        return

    rcon_command = f"Broadcast {message}"
    
    try:
        await _send_rcon_command(rcon_command)
        await ctx.send(f"✅ Successfully sent broadcast: `{message}`")
            
    except Exception as e:
        logger.error(f"Failed to send broadcast via RCON: {e}")
        await ctx.send(f"❌ Failed to send broadcast. Server unreachable or RCON error: `{e}`")

@bot.command(name='save')
@commands.has_permissions(administrator=True)
async def save_command(ctx):
    """Forces the Palworld server to save the current world state."""
    try:
        await ctx.send("💾 Attempting to save the world state...")
        # The Palworld command to save the world is 'Save'
        response = await _send_rcon_command("Save")
        
        if "saved" in response.lower() or "completed" in response.lower():
            await ctx.send("✅ World Save successful! Data secured.")
        else:
            await ctx.send(f"⚠️ World Save sent, but received unusual response: `{response}`")
            
    except Exception as e:
        logger.error(f"Failed to execute SaveWorld via RCON: {e}")
        await ctx.send(f"❌ Failed to save world. Server unreachable or RCON error: `{e}`")

@bot.command(name='shutdown')
@commands.has_permissions(administrator=True)
async def shutdown_command(ctx, delay_seconds: int = 10, *, message: str = "Server is shutting down for maintenance!"):
    """
    Shuts down the server gracefully after a broadcast message and delay.
    Usage: !shutdown [delay_seconds] [message]
    """
    
    # 1. Send warning broadcast
    try:
        warning_msg = f"Server SHUTTING DOWN in {delay_seconds} seconds! Please disconnect now. Reason: {message}"
        await ctx.send(f"🚨 Sending shutdown warning: `{warning_msg}`")
        # Palworld RCON broadcast requires the message to be quoted
        await _send_rcon_command(f"Broadcast {warning_msg}") 
    except Exception as e:
        await ctx.send(f"❌ Warning broadcast failed. Attempting shutdown anyway: `{e}`")

    # 2. Wait for the specified delay
    await asyncio.sleep(delay_seconds)
    
    # 3. Execute graceful shutdown
    try:
        await ctx.send("🛑 Executing graceful server shutdown (`DoExit`).")
        # Palworld command for graceful exit is 'DoExit'
        await _send_rcon_command("DoExit")
        await ctx.send("✅ Shutdown command sent. The server should now be exiting.")
    except Exception as e:
        logger.error(f"Failed to execute DoExit via RCON: {e}")
        await ctx.send(f"❌ Failed to send DoExit command. Server may already be down or RCON error: `{e}`")

@bot.command(name='kick')
@commands.has_permissions(administrator=True)
async def kick_command(ctx, player_id: str):
    """Kicks a player from the server using their unique SteamID/PlayerUID. Use !players to find the ID."""
    if not player_id:
        await ctx.send("❌ Please provide the player's SteamID/PlayerUID. Use `!players` to find it.")
        return
    
    rcon_command = f"KickPlayer {player_id}"
    try:
        response = await _send_rcon_command(rcon_command)
        if "kicked" in response.lower() or "completed" in response.lower() or "success" in response.lower():
            await ctx.send(f"✅ Successfully kicked player with ID: `{player_id}`")
        else:
            await ctx.send(f"⚠️ Kick command sent, but received unusual response: `{response}`")
    except Exception as e:
        await ctx.send(f"❌ Failed to kick player. Server unreachable or RCON error: `{e}`")

@bot.command(name='ban')
@commands.has_permissions(administrator=True)
async def ban_command(ctx, player_id: str):
    """Bans a player from the server using their unique SteamID/PlayerUID. Use !players to find the ID."""
    if not player_id:
        await ctx.send("❌ Please provide the player's SteamID/PlayerUID. Use `!players` to find it.")
        return
        
    rcon_command = f"BanPlayer {player_id}"
    try:
        response = await _send_rcon_command(rcon_command)
        if "banned" in response.lower() or "completed" in response.lower() or "success" in response.lower():
            await ctx.send(f"✅ Successfully banned player with ID: `{player_id}`")
        else:
            await ctx.send(f"⚠️ Ban command sent, but received unusual response: `{response}`")
    except Exception as e:
        await ctx.send(f"❌ Failed to ban player. Server unreachable or RCON error: `{e}`")


# --- START BOT ---
if __name__ == "__main__":
    try:
        logger.info("Starting PalBot...")
        bot.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        logger.critical("FATAL: Invalid Discord token. Please check your DISCORD_TOKEN environment variable.")
    except Exception as e:
        logger.critical(f"FATAL: An unhandled error occurred during execution: {e}")
