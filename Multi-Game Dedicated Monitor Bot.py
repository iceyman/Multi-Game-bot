# -*- coding: utf-8 -*-
import os
import asyncio
import json
from datetime import datetime
from discord.ext import commands, tasks
from discord import Intents, Status, Game, Embed, Colour
from rcon.asyncio import RconAsync, RCONException

# ==============================================================================
# ⚠️ CONFIGURATION BLOCK ⚠️
# Update these settings before running the bot.
# ==============================================================================

# --- DISCORD CONFIGURATION ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', "YOUR_DISCORD_BOT_TOKEN_HERE")
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID', 0)) # Channel for joins/leaves/auto-saves
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', TARGET_CHANNEL_ID)) # Channel for admin/error logs

# --- MINECRAFT RCON CONFIGURATION ---
MC_RCON_HOST = os.getenv('MC_RCON_HOST', "127.0.0.1")
MC_RCON_PORT = int(os.getenv('MC_RCON_PORT', 25575))
MC_RCON_PASSWORD = os.getenv('MC_RCON_PASSWORD', "YOUR_MC_RCON_PASSWORD_HERE")

# --- PALWORLD RCON CONFIGURATION ---
PAL_RCON_HOST = os.getenv('PAL_RCON_HOST', "127.0.0.1")
PAL_RCON_PORT = int(os.getenv('PAL_RCON_PORT', 25575))
PAL_RCON_PASSWORD = os.getenv('PAL_RCON_PASSWORD', "YOUR_PAL_RCON_PASSWORD_HERE")

# --- BOT CONSTANTS ---
PREFIX = "!server-"
RCON_CHECK_INTERVAL_SECONDS = 30
STATISTICS_FILE = "player_stats.json"

# ==============================================================================
# GLOBAL STATE & PERSISTENCE
# ==============================================================================

# Global bot instance
intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Global data structure for tracking player statistics (first join, playtime)
player_stats = {}
# Dictionary to hold active RCON connections
rcon_clients = {}
# Current players for live monitoring
current_mc_players = set()
current_pal_players = set()
# Player join timestamps (for calculating session time)
mc_join_times = {}
pal_join_times = {}


def load_stats():
    """Loads player statistics from a JSON file."""
    global player_stats
    if os.path.exists(STATISTICS_FILE):
        with open(STATISTICS_FILE, 'r') as f:
            try:
                player_stats = json.load(f)
            except json.JSONDecodeError:
                print("Warning: Failed to decode player_stats.json. Starting fresh.")
                player_stats = {}
    else:
        player_stats = {}

def save_stats():
    """Saves player statistics to a JSON file."""
    with open(STATISTICS_FILE, 'w') as f:
        json.dump(player_stats, f, indent=4)

def update_player_join(game: str, player: str):
    """Updates player stats upon joining."""
    player_key = f"{game}:{player}"
    now = datetime.now()
    
    # 1. Update Persistent Stats (First Join)
    if player_key not in player_stats:
        player_stats[player_key] = {
            "first_join": now.strftime("%Y-%m-%d %H:%M:%S"),
            "total_playtime_seconds": 0
        }
        save_stats()
        
    # 2. Update Live Join Times (for session tracking)
    if game == 'mc':
        mc_join_times[player] = now
    elif game == 'pal':
        pal_join_times[player] = now

def update_player_leave(game: str, player: str):
    """Updates player stats upon leaving and calculates playtime."""
    player_key = f"{game}:{player}"
    
    if game == 'mc' and player in mc_join_times:
        join_time = mc_join_times.pop(player)
    elif game == 'pal' and player in pal_join_times:
        join_time = pal_join_times.pop(player)
    else:
        # Player wasn't tracked (e.g., bot restarted while they were online)
        return

    session_duration = (datetime.now() - join_time).total_seconds()
    
    if player_key in player_stats:
        player_stats[player_key]["total_playtime_seconds"] += session_duration
        save_stats()

def format_duration(seconds: float) -> str:
    """Formats seconds into Hh Mmin Ssec string."""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}min")
    parts.append(f"{seconds}sec")
    
    return " ".join(parts) or "0sec"


# ==============================================================================
# RCON CONNECTION MANAGER
# ==============================================================================

class RconManager:
    """Manages the RCON connection and state for a single game."""
    def __init__(self, host, port, password, game_name, list_command, player_name_extractor):
        self.game_name = game_name
        self.host = host
        self.port = port
        self.password = password
        self.list_command = list_command
        self.player_name_extractor = player_name_extractor
        self.client = None
        self.connected = False
        self.last_error = None
        self.channel = None

    async def connect(self):
        """Attempts to establish RCON connection."""
        if self.connected and self.client:
            return True

        try:
            self.client = RconAsync(self.host, self.port, self.password)
            await self.client.connect()
            self.connected = True
            self.last_error = None
            return True
        except (RCONException, asyncio.TimeoutError, ConnectionRefusedError, Exception) as e:
            self.connected = False
            self.client = None
            self.last_error = str(e)
            return False

    async def send_command(self, command: str) -> str:
        """Sends a command, reconnecting if necessary."""
        if not await self.connect():
            return f"ERROR: Not connected. Last RCON failure: {self.last_error}"

        try:
            response = await self.client.send(command)
            return response.strip()
        except RCONException as e:
            self.connected = False
            self.last_error = str(e)
            return f"ERROR: Command failed and connection dropped ({e})."
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            return f"ERROR: An unexpected RCON error occurred: {e}"

    async def get_players(self) -> tuple[set, str]:
        """Sends the list command and returns player set and raw response."""
        response = await self.send_command(self.list_command)
        
        if response.startswith("ERROR:"):
            return set(), response
        
        return self.player_name_extractor(response), response

# --- Palworld specific logic ---
def pal_player_extractor(response: str) -> set:
    """Parses Palworld's ShowPlayers RCON output."""
    # Palworld response format (often tab-separated): Name,UID,SteamID
    players = set()
    lines = response.split('\n')[1:] # Skip header
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) >= 1:
            name = parts[0].strip()
            if name:
                players.add(name)
    return players

# --- Minecraft specific logic ---
def mc_player_extractor(response: str) -> set:
    """Parses Minecraft's list RCON output."""
    # Minecraft response: "There are X of a max of Y players online: PlayerA, PlayerB"
    players = set()
    if ':' in response:
        player_list_str = response.split(':', 1)[1].strip()
        player_names = [name.strip() for name in player_list_str.split(',') if name.strip()]
        players.update(player_names)
    return players

# Initialize RCON managers
mc_monitor = RconManager(
    host=MC_RCON_HOST, 
    port=MC_RCON_PORT, 
    password=MC_RCON_PASSWORD, 
    game_name="Minecraft", 
    list_command="list",
    player_name_extractor=mc_player_extractor
)
pal_monitor = RconManager(
    host=PAL_RCON_HOST, 
    port=PAL_RCON_PORT, 
    password=PAL_RCON_PASSWORD, 
    game_name="Palworld", 
    list_command="ShowPlayers", # Palworld uses ShowPlayers
    player_name_extractor=pal_player_extractor
)


# ==============================================================================
# DISCORD EVENTS AND TASKS
# ==============================================================================

@bot.event
async def on_ready():
    """Executed when the bot is connected to Discord."""
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    await bot.change_presence(activity=Game(f"Monitoring 2 Servers | {PREFIX}help"))

    # Load persistent data
    load_stats()
    
    # Set channels for RCON managers
    mc_monitor.channel = bot.get_channel(TARGET_CHANNEL_ID)
    pal_monitor.channel = bot.get_channel(TARGET_CHANNEL_ID)

    if not mc_monitor.channel or not pal_monitor.channel:
        print(f"ERROR: Channel ID {TARGET_CHANNEL_ID} not found. Monitoring tasks will not start.")
        return

    # Start background tasks
    if not player_monitor_task.running:
        player_monitor_task.start()
        print("Player monitoring task started.")
    if not scheduled_actions_task.running:
        scheduled_actions_task.start()
        print("Scheduled actions task started.")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ You need the **Administrator** permission to use the `{ctx.command.name}` command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: {error}. Usage: `{PREFIX}{ctx.command.name} {ctx.command.signature}`")
    elif isinstance(error, commands.CommandNotFound):
        # Ignore command not found errors to avoid spam
        return
    else:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        error_msg = f"Unhandled error in `{ctx.command}`: {error.__class__.__name__}: {error}"
        print(error_msg)
        if log_channel:
            await log_channel.send(f"⚠️ **Command Error** in {ctx.channel.mention}:\n{error_msg}")
        await ctx.send("❌ An unexpected error occurred while executing the command. Details have been logged.")


@tasks.loop(seconds=RCON_CHECK_INTERVAL_SECONDS)
async def player_monitor_task():
    """Background task to continuously check players and report joins/leaves for both servers."""
    global current_mc_players, current_pal_players

    async def check_server(monitor: RconManager, game_code: str, current_set: set) -> set:
        """Helper function to perform checks for one server."""
        try:
            new_players, raw_response = await monitor.get_players()
        except Exception as e:
            # Report connectivity loss to admin channel
            if current_set:
                 await monitor.channel.send(f"⚠️ **{monitor.game_name} Alert:** Lost RCON connectivity ({e}). Status monitoring paused.")
            return set()

        if "ERROR:" in raw_response:
            # Send RCON command error to log channel
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"⚠️ **{monitor.game_name} RCON Error:** {raw_response}")
            return current_set # Don't update player state on error

        # Check for Joins
        joined_players = new_players - current_set
        for player in joined_players:
            update_player_join(game_code, player)
            embed = Embed(
                title=f"🟢 Player Joined ({monitor.game_name})",
                description=f"**{player}** has joined the server.",
                color=Colour.green()
            )
            await monitor.channel.send(embed=embed)

        # Check for Leaves
        left_players = current_set - new_players
        for player in left_players:
            update_player_leave(game_code, player)
            embed = Embed(
                title=f"🔴 Player Left ({monitor.game_name})",
                description=f"**{player}** has left the server. Session duration logged.",
                color=Colour.red()
            )
            await monitor.channel.send(embed=embed)

        return new_players

    # Check Minecraft
    current_mc_players = await check_server(mc_monitor, 'mc', current_mc_players)
    
    # Check Palworld
    current_pal_players = await check_server(pal_monitor, 'pal', current_pal_players)


@tasks.loop(hours=1) # Run every hour for auto-save
async def scheduled_actions_task():
    """Performs scheduled maintenance tasks like auto-save."""
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        return

    # --- Minecraft Auto-Save ---
    mc_response = await mc_monitor.send_command("save-all")
    if "ERROR:" not in mc_response:
        await channel.send("✅ **[Minecraft Auto-Save]** World state successfully saved.")
    else:
        await channel.send(f"❌ **[Minecraft Auto-Save Failed]** {mc_response}")
        
    # --- Palworld Auto-Save ---
    pal_response = await pal_monitor.send_command("Save") # Palworld uses 'Save'
    if "ERROR:" not in pal_response:
        await channel.send("✅ **[Palworld Auto-Save]** World state successfully saved.")
    else:
        await channel.send(f"❌ **[Palworld Auto-Save Failed]** {pal_response}")

# ==============================================================================
# DISCORD COMMANDS (PALWORLD)
# ==============================================================================

@bot.group(name="pal", invoke_without_command=True)
async def palworld(ctx):
    """Palworld administration commands."""
    await ctx.send(f"Use `{PREFIX}pal-help` for Palworld commands.")

@palworld.command(name="help")
async def pal_help_command(ctx):
    """Displays a list of Palworld administrative commands."""
    help_text = f"""
    __**Palworld Admin Commands ({PREFIX}pal-)**__
    *All commands require **Administrator** permission in Discord.*

    **!server-pal-status**
    > Shows the current player count and RCON connection health.

    **!server-pal-players**
    > Lists all currently logged-in players (names, playtime, stats).

    **!server-pal-broadcast <message>**
    > Sends a server-wide broadcast message to all players.

    **!server-pal-save**
    > Forces the server to immediately save the world state (`Save`).
    
    **!server-pal-kick <SteamID>**
    > Kicks a player using their SteamID. (SteamID required, not name).

    **!server-pal-shutdown <seconds> <message>**
    > Shuts down the server after a delay with a final broadcast message.
    """
    embed = Embed(title="🎮 Palworld Admin Help", description=help_text, color=Colour.from_rgb(0, 150, 255))
    await ctx.send(embed=embed)


@palworld.command(name="status")
@commands.has_permissions(administrator=True)
async def pal_status_command(ctx):
    """Checks the current Palworld server status and player count."""
    if not await pal_monitor.connect():
        embed = Embed(
            title="🔴 Palworld Server Status",
            description=f"RCON Connection Failed to **{pal_monitor.host}:{pal_monitor.port}**.\nLast Error: `{pal_monitor.last_error}`",
            color=Colour.red()
        )
    else:
        players, _ = await pal_monitor.get_players()
        embed = Embed(
            title="🟢 Palworld Server Status",
            description=f"**Online and Responsive**\n\nPlayers Online: **{len(players)}**",
            color=Colour.green()
        )
        embed.add_field(name="RCON Endpoint", value=f"`{pal_monitor.host}:{pal_monitor.port}`", inline=False)

    await ctx.send(embed=embed)


@palworld.command(name="players")
@commands.has_permissions(administrator=True)
async def pal_players_command(ctx):
    """Lists all Palworld players currently online with stats."""
    players, raw_response = await pal_monitor.get_players()

    if "ERROR:" in raw_response:
        await ctx.send(f"❌ **Palworld RCON Error:** Could not retrieve player list. {raw_response}")
        return

    if not players:
        embed = Embed(title="🎮 Palworld Online Players (0)", description="The server is currently empty.", color=Colour.orange())
        await ctx.send(embed=embed)
        return

    player_details = []
    for name in sorted(players):
        stats_key = f"pal:{name}"
        stats = player_stats.get(stats_key, {})
        
        # Calculate current session time
        session_time_str = "N/A"
        if name in pal_join_times:
            session_seconds = (datetime.now() - pal_join_times[name]).total_seconds()
            session_time_str = format_duration(session_seconds)
            
        total_time_str = format_duration(stats.get("total_playtime_seconds", 0))
        first_join = stats.get("first_join", "Unknown")
        
        player_details.append(
            f"**{name}**\n"
            f"• Session: {session_time_str}\n"
            f"• Total Time: {total_time_str}\n"
            f"• First Join: {first_join}"
        )

    embed = Embed(
        title=f"🎮 Palworld Online Players ({len(players)})",
        description="List of currently logged-in players:",
        color=Colour.blue()
    )
    embed.add_field(name="Player Stats (Session/Total)", value="\n\n".join(player_details), inline=False)
    await ctx.send(embed=embed)


@palworld.command(name="broadcast")
@commands.has_permissions(administrator=True)
async def pal_broadcast_command(ctx, *, message: str):
    """Sends a broadcast message to all Palworld players."""
    # Palworld RCON command for broadcasting: Broadcast <message>
    command = f"Broadcast {message.replace(' ', '_')}" # Palworld requires underscores/no spaces
    response = await pal_monitor.send_command(command)

    if "ERROR:" in response:
        await ctx.send(f"❌ **Palworld Broadcast Failed!** {response}")
    else:
        embed = Embed(
            title="📣 Palworld Broadcast Sent",
            description=f"Message: *{message}*",
            color=Colour.gold()
        )
        await ctx.send(embed=embed)

@palworld.command(name="save")
@commands.has_permissions(administrator=True)
async def pal_save_command(ctx):
    """Forces the Palworld server to save the world state."""
    command = "Save"
    response = await pal_monitor.send_command(command)

    if "ERROR:" in response:
        await ctx.send(f"❌ **Palworld Save Failed!** {response}")
    else:
        embed = Embed(
            title="💾 Palworld World Saved",
            description="The Palworld server was commanded to save the world state.",
            color=Colour.green()
        )
        await ctx.send(embed=embed)

@palworld.command(name="kick")
@commands.has_permissions(administrator=True)
async def pal_kick_command(ctx, steam_id: str):
    """Kicks a Palworld player using their SteamID."""
    command = f"KickPlayer {steam_id}"
    response = await pal_monitor.send_command(command)

    if "ERROR:" in response:
        await ctx.send(f"❌ **Palworld Kick Failed!** Make sure the SteamID (`{steam_id}`) is correct. Response: {response}")
    else:
        embed = Embed(
            title="👟 Palworld Player Kicked",
            description=f"Player with SteamID **{steam_id}** has been kicked from the server.",
            color=Colour.orange()
        )
        await ctx.send(embed=embed)

@palworld.command(name="shutdown")
@commands.has_permissions(administrator=True)
async def pal_shutdown_command(ctx, delay_seconds: int, *, message: str):
    """Shuts down the Palworld server after a delay."""
    # Palworld RCON command: Shutdown <seconds> <message>
    command = f"Shutdown {delay_seconds} {message.replace(' ', '_')}"
    response = await pal_monitor.send_command(command)

    if "ERROR:" in response:
        await ctx.send(f"❌ **Palworld Shutdown Failed!** {response}")
    else:
        embed = Embed(
            title="🛑 Palworld Server Shutdown Initiated",
            description=f"The server will shut down in **{delay_seconds} seconds** with the message: *{message}*.",
            color=Colour.red()
        )
        await ctx.send(embed=embed)

# ==============================================================================
# DISCORD COMMANDS (MINECRAFT)
# ==============================================================================

@bot.group(name="mine", invoke_without_command=True)
async def minecraft(ctx):
    """Minecraft administration commands."""
    await ctx.send(f"Use `{PREFIX}mine-help` for Minecraft commands.")

@minecraft.command(name="help")
async def mc_help_command(ctx):
    """Displays a list of Minecraft administrative commands."""
    help_text = f"""
    __**Minecraft Admin Commands ({PREFIX}mine-)**__
    *All commands require **Administrator** permission in Discord.*

    **!server-mine-status**
    > Shows the current player count and RCON connection health.

    **!server-mine-players**
    > Lists all currently logged-in players (names, playtime, stats).

    **!server-mine-say <message>**
    > Sends a message to the in-game chat, prefixed by `[Discord Admin]`.

    **!server-mine-save**
    > Forces the server to immediately save the world state (`save-all`).

    **!server-mine-kick <Name>**
    > Kicks a player using their exact in-game name.

    **!server-mine-ban <Name>**
    > Bans a player using their exact in-game name.
    """
    embed = Embed(title="🧱 Minecraft Admin Help", description=help_text, color=Colour.from_rgb(100, 200, 50))
    await ctx.send(embed=embed)


@minecraft.command(name="status")
@commands.has_permissions(administrator=True)
async def mc_status_command(ctx):
    """Checks the current Minecraft server status and player count."""
    if not await mc_monitor.connect():
        embed = Embed(
            title="🔴 Minecraft Server Status",
            description=f"RCON Connection Failed to **{mc_monitor.host}:{mc_monitor.port}**.\nLast Error: `{mc_monitor.last_error}`",
            color=Colour.red()
        )
    else:
        players, raw_response = await mc_monitor.get_players()
        
        # Try to extract max player count from the 'list' response
        max_players_str = "Unknown Max"
        if "max of" in raw_response:
            try:
                max_players_str = raw_response.split('max of ')[1].split(' ')[0].strip()
            except:
                pass

        embed = Embed(
            title="🟢 Minecraft Server Status",
            description=f"**Online and Responsive**\n\nPlayers Online: **{len(players)}** (Max: {max_players_str})",
            color=Colour.green()
        )
        embed.add_field(name="RCON Endpoint", value=f"`{mc_monitor.host}:{mc_monitor.port}`", inline=False)

    await ctx.send(embed=embed)


@minecraft.command(name="players")
@commands.has_permissions(administrator=True)
async def mc_players_command(ctx):
    """Lists all Minecraft players currently online with stats."""
    players, raw_response = await mc_monitor.get_players()

    if "ERROR:" in raw_response:
        await ctx.send(f"❌ **Minecraft RCON Error:** Could not retrieve player list. {raw_response}")
        return

    if not players:
        embed = Embed(title="🎮 Minecraft Online Players (0)", description="The server is currently empty.", color=Colour.orange())
        await ctx.send(embed=embed)
        return

    player_details = []
    for name in sorted(players):
        stats_key = f"mc:{name}"
        stats = player_stats.get(stats_key, {})
        
        # Calculate current session time
        session_time_str = "N/A"
        if name in mc_join_times:
            session_seconds = (datetime.now() - mc_join_times[name]).total_seconds()
            session_time_str = format_duration(session_seconds)
            
        total_time_str = format_duration(stats.get("total_playtime_seconds", 0))
        first_join = stats.get("first_join", "Unknown")
        
        player_details.append(
            f"**{name}**\n"
            f"• Session: {session_time_str}\n"
            f"• Total Time: {total_time_str}\n"
            f"• First Join: {first_join}"
        )

    embed = Embed(
        title=f"🎮 Minecraft Online Players ({len(players)})",
        description="List of currently logged-in players:",
        color=Colour.blue()
    )
    embed.add_field(name="Player Stats (Session/Total)", value="\n\n".join(player_details), inline=False)
    await ctx.send(embed=embed)


@minecraft.command(name="say")
@commands.has_permissions(administrator=True)
async def mc_say_command(ctx, *, message: str):
    """Sends a message to the in-game chat."""
    full_message = f"[Discord Admin] {message}"
    command = f"say {full_message}"
    response = await mc_monitor.send_command(command)

    if "ERROR:" in response:
        await ctx.send(f"❌ **Minecraft Say Failed!** {response}")
    else:
        embed = Embed(
            title="📣 Minecraft Message Sent In-Game",
            description=f"Message: *{full_message}*",
            color=Colour.gold()
        )
        await ctx.send(embed=embed)


@minecraft.command(name="save")
@commands.has_permissions(administrator=True)
async def mc_save_command(ctx):
    """Forces the Minecraft server to save the world state."""
    command = "save-all"
    response = await mc_monitor.send_command(command)

    if "ERROR:" in response:
        await ctx.send(f"❌ **Minecraft Save Failed!** {response}")
    else:
        embed = Embed(
            title="💾 Minecraft World Saved",
            description="The Minecraft server was commanded to save the world state.",
            color=Colour.green()
        )
        await ctx.send(embed=embed)


@minecraft.command(name="kick")
@commands.has_permissions(administrator=True)
async def mc_kick_command(ctx, player_name: str):
    """Kicks a Minecraft player using their exact in-game name."""
    command = f"kick {player_name}"
    response = await mc_monitor.send_command(command)

    if "ERROR:" in response:
        await ctx.send(f"❌ **Minecraft Kick Failed!** Make sure the player name (`{player_name}`) is correct and the player is online. Response: {response}")
    else:
        embed = Embed(
            title="👟 Minecraft Player Kicked",
            description=f"**{player_name}** has been kicked from the server.",
            color=Colour.orange()
        )
        await ctx.send(embed=embed)


@minecraft.command(name="ban")
@commands.has_permissions(administrator=True)
async def mc_ban_command(ctx, player_name: str):
    """Bans a Minecraft player using their exact in-game name."""
    command = f"ban {player_name}"
    response = await mc_monitor.send_command(command)

    if "ERROR:" in response:
        await ctx.send(f"❌ **Minecraft Ban Failed!** Make sure the player name (`{player_name}`) is correct. Response: {response}")
    else:
        embed = Embed(
            title="🔨 Minecraft Player Banned",
            description=f"**{player_name}** has been **banned** from the server.",
            color=Colour.dark_red()
        )
        await ctx.send(embed=embed)

# ==============================================================================
# RUN BOT
# ==============================================================================

if not DISCORD_TOKEN or TARGET_CHANNEL_ID == 0 or not MC_RCON_PASSWORD or not PAL_RCON_PASSWORD:
    print("\n\n--------------------------------------------------------------")
    print("FATAL ERROR: Please update the CONFIGURATION BLOCK in the script.")
    print("--------------------------------------------------------------\n")
else:
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"\n\nFATAL RUNTIME ERROR: {e}")
        print("Check if your DISCORD_TOKEN is valid and that you have installed discord.py and python-rcon.")
