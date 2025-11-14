import discord
from discord.ext import commands, tasks
from discord import app_commands

import json
import asyncio
import logging
import os
import sys
import datetime
from typing import List, Optional, Dict, Any
import re 
import time

# --- V3.0 IMPORT ---
# Import the new database file
try:
    import database as db
except ImportError:
    print("ERROR: database.py not found. Please make sure it is in the same directory.")
    sys.exit(1)

# Import game-specific libraries
from mcstatus import JavaServer
from mcrcon import MCRcon
import a2s

# Import web scraping libraries
import httpx
from bs4 import BeautifulSoup

# --- V2.0 IMPORT ---
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("ERROR: 'watchdog' library not found. Please install it with 'pip install watchdog'")
    sys.exit(1)
import io

# ---------------------------------
# Logging Setup
# ---------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discord_bot')

# ---------------------------------
# Configuration Loading
# ---------------------------------
CONFIG_FILE = 'config.json'

def load_config():
    """Loads the config.json file."""
    if not os.path.exists(CONFIG_FILE):
        logger.critical(f"{CONFIG_FILE} not found. Please copy {CONFIG_FILE}.example to {CONFIG_FILE} and fill it out.")
        sys.exit(1)
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        if "discord_bot_token" not in config or not config["discord_bot_token"]:
            logger.critical("discord_bot_token is missing from config.json.")
            sys.exit(1)
            
        return config
    except json.JSONDecodeError:
        logger.critical(f"Error parsing {CONFIG_FILE}. Please ensure it is valid JSON.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An error occurred loading the config: {e}")
        sys.exit(1)

config = load_config()

def get_config_value(key, default=None):
    """Safely get a value from the loaded config."""
    keys = key.split('.')
    value = config
    try:
        for k in keys:
            value = value[k]
        return value
    except KeyError:
        return default
    except TypeError:
         return default

# ---------------------------------
# Bot Setup
# ---------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class GameBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.status_message_id = None
        self.log_watcher_cog = None 
        
        # --- V3.0 ---
        # Initialize the database
        db_name = get_config_value("database_name", "bot_database.db")
        db.init_db(db_name)
        logger.info(f"Database initialized at {db_name}")

    async def setup_hook(self):
        """Called when the bot is setting up, before login."""
        default_icon = "https://i.imgur.com/8VAl4QO.png"
        util_icon = get_config_value("embed_images.utility_icon", default_icon)
        mc_icon = get_config_value("embed_images.minecraft_icon", default_icon)
        pal_icon = get_config_value("embed_images.palworld_icon", default_icon)
        ark_icon = get_config_value("embed_images.ark_icon", default_icon)
        eco_icon = get_config_value("embed_images.economy_icon", default_icon) # V3

        await self.add_cog(UtilityCog(self, util_icon))
        await self.add_cog(MinecraftCog(self, mc_icon))
        await self.add_cog(PalworldCog(self, pal_icon))
        await self.add_cog(ArkCog(self, ark_icon))
        await self.add_cog(TasksCog(self))
        
        # --- V2.0 COG ---
        self.log_watcher_cog = LogWatcherCog(self)
        await self.add_cog(self.log_watcher_cog)
        
        # --- V3.0 COG ---
        if get_config_value("economy.enabled", False):
            await self.add_cog(EconomyCog(self, eco_icon))
            logger.info("EconomyCog loaded.")
        else:
            logger.info("Economy is disabled in config. Skipping EconomyCog.")

        logger.info("All cogs loaded.")
        
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} application commands globally.")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('---------------------------------')
        if self.log_watcher_cog:
            self.log_watcher_cog.start_watching()

    async def on_message(self, message: discord.Message):
        """V2.0 Feature: Cross-Server Chat (Discord -> Game)"""
        if message.author.bot:
            return

        if not get_config_value("cross_server_chat.enabled", False):
            return

        relay_channels = {
            'mc': get_config_value("discord_channel_ids.minecraft_chat_relay_channel_id"),
            'pal': get_config_value("discord_channel_ids.palworld_chat_relay_channel_id"),
            'ark': get_config_value("discord_channel_ids.ark_chat_relay_channel_id"),
        }
        
        current_channel_id = str(message.channel.id)
        game_key = None
        
        for key, channel_id in relay_channels.items():
            if current_channel_id == channel_id:
                game_key = key
                break
        
        if not game_key:
            return

        username_format = get_config_value("cross_server_chat.discord_username_format", "[Discord] {username}")
        username = username_format.format(username=message.author.display_name)
        chat_message = f"{username}: {message.clean_content}"
        
        try:
            cog_map = {'mc': 'MinecraftCog', 'pal': 'PalworldCog', 'ark': 'ArkCog'}
            cog = self.get_cog(cog_map.get(game_key))
            if not cog:
                return

            if game_key == 'mc':
                await run_rcon_command(cog.rcon_command, f"say {chat_message}")
            elif game_key == 'pal':
                pal_message = chat_message.replace(" ", "_")
                await run_rcon_command(cog.rcon_command, f"Broadcast {pal_message}")
            elif game_key == 'ark':
                await run_rcon_command(cog.rcon_command, f"ServerChat {chat_message}")
            
        except Exception as e:
            logger.error(f"Failed to send cross-chat message to {game_key}: {e}")
            try:
                await message.add_reaction("❌")
            except discord.Forbidden:
                pass 

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error(f"An error occurred in a command: {error}")
        await ctx.send("An unexpected error occurred. Please contact the bot admin.", ephemeral=True)

    async def close(self):
        logger.info("Bot is shutting down...")
        if self.log_watcher_cog:
            self.log_watcher_cog.stop_watching()
        await super().close()

bot = GameBot(command_prefix="!", intents=intents)

# ---------------------------------
# Helper Functions
# ---------------------------------
async def fetch_html(url: str) -> Optional[str]:
    """Asynchronously fetches HTML content from a URL."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=10.0)
            response.raise_for_status() 
            return response.text
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching {url}: {e}")
        return None
    except httpx.RequestError as e:
        logger.warning(f"Network error fetching {url}: {e}")
        return None

def create_embed(title: str, description: str, color: discord.Color, image_url: str = None) -> discord.Embed:
    """Helper function to create a standardized embed."""
    embed = discord.Embed(title=title, description=description, color=color)
    if image_url:
        embed.set_thumbnail(url=image_url)
    embed.set_footer(text=f"Game Server Bot | {bot.user.name}")
    return embed

async def run_rcon_command(rcon_func, *args):
    """Runs a blocking RCON command in a separate thread."""
    loop = asyncio.get_event_loop()
    try:
        response = await asyncio.to_thread(rcon_func, *args)
        return response
    except ConnectionRefusedError:
        return "RCON_ERROR: Connection refused. Is the server online and RCON enabled?"
    except Exception as e:
        logger.error(f"RCON command failed: {e}")
        return f"RCON_ERROR: An unexpected error occurred: {e}"

async def run_a2s_query(address: tuple):
    """Runs a blocking A2S query in a separate thread."""
    loop = asyncio.get_event_loop()
    try:
        info = await asyncio.to_thread(a2s.info, address, timeout=5.0)
        return info
    except asyncio.TimeoutError:
        return "A2S_ERROR: Query timed out. Server might be offline."
    except Exception as e:
        logger.error(f"A2S query failed: {e}")
        return f"A2S_ERROR: An unexpected error occurred: {e}"

# ---------------------------------
# Channel Check Decorator
# ---------------------------------
def check_channel_id(allowed_channel_ids_key: str):
    """Decorator to check if a command is used in an allowed channel."""
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed_ids = get_config_value(f"discord_channel_ids.{allowed_channel_ids_key}", [])
        admin_ids = get_config_value("discord_channel_ids.admin_channel_ids", [])
        combined_allowed_ids = set(allowed_ids + admin_ids)
        
        if str(interaction.channel_id) in combined_allowed_ids:
            return True
        
        allowed_channels_mentions = []
        for channel_id in combined_allowed_ids:
            try:
                channel_mention = f"<#{int(channel_id)}>"
                allowed_channels_mentions.append(channel_mention)
            except ValueError:
                logger.warning(f"Invalid channel ID in config: {channel_id}")

        if not allowed_channels_mentions:
            error_message = "This command is not allowed in this channel. (No allowed channels are configured.)"
        else:
            error_message = f"This command can only be used in:\n" + "\n".join(allowed_channels_mentions)

        admin_icon = get_config_value("embed_images.admin_icon")
        embed = create_embed(
            "Command Not Allowed",
            error_message,
            discord.Color.red(),
            admin_icon
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    
    return app_commands.check(predicate)

# ---------------------------------
# Cog: UtilityCog (--- V3.0 UPDATED ---)
# ---------------------------------
class UtilityCog(commands.Cog):
    def __init__(self, bot: GameBot, image_url: str):
        self.bot = bot
        self.image_url = image_url

    @app_commands.command(name="help", description="Shows a list of all available commands.")
    @check_channel_id("admin_channel_ids")
    async def help(self, interaction: discord.Interaction):
        embed = create_embed(
            "Game Server Bot Help",
            "Here are all the commands you can use. Admin commands are marked with 👑.",
            discord.Color.blue(),
            self.image_url
        )

        admin_channels = ", ".join([f"<#{cid}>" for cid in get_config_value("discord_channel_ids.admin_channel_ids", [])]) or "None"
        mc_channels = ", ".join([f"<#{cid}>" for cid in get_config_value("discord_channel_ids.minecraft_channel_ids", [])]) or "None"
        pal_channels = ", ".join([f"<#{cid}>" for cid in get_config_value("discord_channel_ids.palworld_channel_ids", [])]) or "None"
        ark_channels = ", ".join([f"<#{cid}>" for cid in get_config_value("discord_channel_ids.ark_channel_ids", [])]) or "None"

        embed.add_field(
            name="Channel Setup",
            value=f"**Admin:** {admin_channels}\n"
                  f"**Minecraft:** {mc_channels}\n"
                  f"**Palworld:** {pal_channels}\n"
                  f"**ARK:** {ark_channels}",
            inline=False
        )
        
        embed.add_field(
            name="V2.0 Chat Relay Setup",
            value=f"**MC Chat:** <#{get_config_value('discord_channel_ids.minecraft_chat_relay_channel_id', 'None')}>\n"
                  f"**Pal Chat:** <#{get_config_value('discord_channel_ids.palworld_chat_relay_channel_id', 'None')}>\n"
                  f"**ARK Chat:** <#{get_config_value('discord_channel_ids.ark_chat_relay_channel_id', 'None')}>\n",
            inline=False
        )

        embed.add_field(
            name="🌐 Utility Commands",
            value="`/help` - Shows this message.\n"
                  "`/links` - Displays helpful wiki links.\n"
                  "`/status_all` - 👑 Checks status of all servers.",
            inline=False
        )

        # --- V3.0 ---
        if get_config_value("economy.enabled", False):
            embed.add_field(
                name="💰 Economy Commands",
                value="`/link [ign]` - Links your Discord to your in-game name.\n"
                      "`/unlink` - Removes your in-game name link.\n"
                      "`/balance` - Checks your points balance.\n"
                      "`/shop` - Shows the in-game item shop.\n"
                      "`/buy [id]` - Buys an item from the shop.",
                inline=False
            )

        embed.add_field(
            name="🧱 Minecraft Commands",
            value="`/minecraft_status` - Checks Minecraft server status.\n"
                  "`/say [msg]` - 👑 Broadcasts a message.\n"
                  "`/whitelist [user]` - 👑 Whitelists a player.\n"
                  "`/minecraft_kick [user]` - 👑 Kicks a player.\n"
                  "`/minecraft_ban [user]` - 👑 Bans a player.",
            inline=False
        )
        
        embed.add_field(
            name="🐾 Palworld Commands",
            value="`/palworld_status` - Checks Palworld server status.\n"
                  "`/pal_broadcast [msg]` - 👑 Broadcasts a message.\n"
                  "`/pal_players` - 👑 Lists connected players.\n"
                  "`/pal_save` - 👑 Saves the world.\n"
                  "`/pal_kick [name/id]` - 👑 Kicks a player.\n"
                  "`/pal_ban [name/id]` - 👑 **(V2)** Kicks and adds to banlist.txt.\n"
                  "`/pal_info [pal]` - Looks up info about a Pal.",
            inline=False
        )
        
        embed.add_field(
            name="🦖 ARK: ASA Commands",
            value="`/ark_status` - Checks ARK server status.\n"
                  "`/ark_broadcast [msg]` - 👑 Broadcasts a message.\n"
                  "`/ark_players` - 👑 Lists connected players.\n"
                  "`/ark_save` - 👑 Saves the world.\n"
                  "`/ark_kick [id]` - 👑 Kicks a player.\n"
                  "`/ark_ban [id]` - 👑 Bans a player.\n"
                  "`/ark_tame [creature]` - Looks up taming info for a creature.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="links", description="Displays helpful wiki and resource links.")
    @check_channel_id("admin_channel_ids")
    async def links(self, interaction: discord.Interaction):
        links_dict = get_config_value("links", {})
        if not links_dict:
            embed = create_embed(
                "Helpful Links",
                "No links are configured in `config.json`.",
                discord.Color.yellow(),
                self.image_url
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        description = ""
        for name, url in links_dict.items():
            description += f"[{name}]({url})\n"
        
        embed = create_embed(
            "Helpful Links",
            description,
            discord.Color.green(),
            self.image_url
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="status_all", description="Checks the status of all configured game servers.")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def status_all(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        
        admin_icon = get_config_value("embed_images.admin_icon")
        embed = create_embed(
            "All Server Status",
            "Fetching status for all servers, please wait...",
            discord.Color.purple(),
            admin_icon
        )
        
        mc_cog = self.bot.get_cog("MinecraftCog")
        pal_cog = self.bot.get_cog("PalworldCog")
        ark_cog = self.bot.get_cog("ArkCog")
        
        if mc_cog:
            mc_status_str = await mc_cog.get_minecraft_status()
            embed.add_field(name="Minecraft", value=mc_status_str, inline=False)
        
        if pal_cog:
            pal_status_str = await pal_cog.get_palworld_status()
            embed.add_field(name="Palworld", value=pal_status_str, inline=False)

        if ark_cog:
            ark_status_str = await ark_cog.get_ark_status()
            embed.add_field(name="ARK: ASA", value=ark_status_str, inline=False)
            
        embed.description = "All server statuses:"
        await interaction.followup.send(embed=embed)
# ---------------------------------
# Cog: MinecraftCog
# ---------------------------------
class MinecraftCog(commands.Cog, name="MinecraftCog"):
    def __init__(self, bot: GameBot, image_url: str):
        self.bot = bot
        self.image_url = image_url
        self.server_ip = get_config_value("server_ips.minecraft_ip", "")
        self.rcon_port = get_config_value("rcon_settings.minecraft_rcon_port", 0)
        self.rcon_pass = get_config_value("rcon_settings.minecraft_rcon_pass", "")
        
        if not self.server_ip:
            logger.error("Minecraft IP not set in config.")
        
    async def get_minecraft_status(self) -> str:
        if not self.server_ip:
            return "Server IP not configured."
        try:
            server = await JavaServer.async_lookup(self.server_ip)
            status = await server.async_status()
            return f"**Online** - `{status.version.name}`\n" \
                   f"Players: `{status.players.online}/{status.players.max}`\n" \
                   f"Ping: `{status.latency:.2f} ms`"
        except Exception as e:
            logger.warning(f"Failed to ping Minecraft server {self.server_ip}: {e}")
            return "**Offline**"

    def rcon_command(self, command: str):
        """Helper to run a single MC RCON command."""
        try:
            with MCRcon(self.server_ip.split(':')[0], self.rcon_pass, self.rcon_port) as mcr:
                response = mcr.command(command)
                return response or "Command sent (no response)."
        except Exception as e:
            raise e

    @app_commands.command(name="minecraft_status", description="Checks the status of the Minecraft server.")
    @check_channel_id("minecraft_channel_ids")
    async def minecraft_status(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        status_str = await self.get_minecraft_status()
        color = discord.Color.green() if "Online" in status_str else discord.Color.red()
        embed = create_embed("Minecraft Server Status", status_str, color, self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="say", description="Broadcasts a message to the Minecraft server.")
    @app_commands.describe(message="The message to send")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def say(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, f"say {message}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Broadcast Sent", f"Sent to Minecraft server:\n`{message}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="whitelist", description="Adds a player to the Minecraft server whitelist.")
    @app_commands.describe(username="The username of the player to whitelist")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def whitelist(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, f"whitelist add {username}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Whitelist Updated", f"Response from server:\n`{response}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="minecraft_kick", description="Kicks a player from the Minecraft server.")
    @app_commands.describe(username="The username of the player to kick")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def minecraft_kick(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, f"kick {username}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Kick Command Sent", f"Response from server:\n`{response}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="minecraft_ban", description="Bans a player from the Minecraft server.")
    @app_commands.describe(username="The username of the player to ban")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def minecraft_ban(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, f"ban {username}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Ban Command Sent", f"Response from server:\n`{response}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

# ---------------------------------
# Cog: PalworldCog (--- V2.0 CHANGES ---)
# ---------------------------------
class PalworldCog(commands.Cog, name="PalworldCog"):
    def __init__(self, bot: GameBot, image_url: str):
        self.bot = bot
        self.image_url = image_url
        self.server_ip = get_config_value("server_ips.palworld_ip", "").split(':')[0]
        self.rcon_port = get_config_value("server_ips.palworld_ip", ":0").split(':')[1]
        self.query_port = get_config_value("query_ports.palworld_query_port", 0)
        self.rcon_pass = get_config_value("rcon_settings.palworld_admin_pass", "")
        
        # --- V2.0 ---
        self.banlist_path = get_config_value("server_file_paths.palworld_banlist_path", "")

    async def get_palworld_status(self) -> str:
        if not self.server_ip or not self.query_port:
            return "Server IP or Query Port not configured."
        address = (self.server_ip, int(self.query_port))
        try:
            info = await run_a2s_query(address)
            if "A2S_ERROR" in str(info): return f"**Offline**\nReason: `{info}`"
            return f"**Online** - `{info.server_name}`\n" \
                   f"Players: `{info.player_count}/{info.max_players}`\n" \
                   f"Map: `{info.map_name}`"
        except Exception as e:
            logger.warning(f"Failed to query Palworld server {address}: {e}")
            return "**Offline**"
            
    def rcon_command(self, command: str):
        pal_ip = self.server_ip
        pal_port = int(self.rcon_port)
        pal_pass = self.rcon_pass
        try:
            with MCRcon(pal_ip, pal_pass, pal_port) as mcr:
                response = mcr.command(command)
                return response or "Command sent (no response)."
        except Exception as e:
            raise e
            
    # --- V2.0 ---
    async def add_to_banlist(self, player_id: str) -> str:
        """Appends a player ID to the Palworld banlist.txt."""
        if not self.banlist_path:
            logger.warning("Palworld banlist_path not set in config.json.")
            return "File Error: `palworld_banlist_path` not configured."

        if not os.path.exists(self.banlist_path):
            logger.warning(f"Palworld banlist file not found at: {self.banlist_path}")
            return "File Error: Ban list file not found. Check config path."

        try:
            # Run file I/O in a separate thread to avoid blocking
            def write_to_file():
                with open(self.banlist_path, 'a+') as f:
                    # Move to start to read
                    f.seek(0)
                    for line in f:
                        if player_id in line:
                            return "Player is already in banlist.txt."
                    
                    # Not found, go to end to append
                    f.write(f"\n{player_id}")
                    return f"Successfully added `{player_id}` to `banlist.txt`."
            
            response = await asyncio.to_thread(write_to_file)
            return response
            
        except PermissionError:
            logger.error(f"Permission denied writing to {self.banlist_path}")
            return "File Error: Bot does not have permission to write to the ban list."
        except Exception as e:
            logger.error(f"Failed to write to banlist: {e}")
            return f"File Error: An unexpected error occurred: {e}"

    @app_commands.command(name="palworld_status", description="Checks the status of the Palworld server.")
    @check_channel_id("palworld_channel_ids")
    async def palworld_status(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        status_str = await self.get_palworld_status()
        color = discord.Color.green() if "Online" in status_str else discord.Color.red()
        embed = create_embed("Palworld Server Status", status_str, color, self.image_url)
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="pal_broadcast", description="Broadcasts a message to the Palworld server.")
    @app_commands.describe(message="The message to send (spaces will be replaced with underscores)")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def pal_broadcast(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(thinking=True)
        formatted_message = message.replace(" ", "_")
        response = await run_rcon_command(self.rcon_command, f"Broadcast {formatted_message}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Broadcast Sent", f"Sent to Palworld server:\n`{message}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pal_players", description="Lists players on the Palworld server.")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def pal_players(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, "ShowPlayers")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Palworld Player List", f"```{response}```", discord.Color.blue(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pal_save", description="Saves the Palworld server world.")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def pal_save(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, "Save")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("World Save", f"Response from server:\n`{response}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pal_kick", description="Kicks a player from the Palworld server (SteamID or Name).")
    @app_commands.describe(player_id="The SteamID or in-game name of the player")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def pal_kick(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, f"KickPlayer {player_id}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Kick Command Sent", f"Response from server:\n`{response}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pal_ban", description="V2: Kicks and adds player to banlist.txt.")
    @app_commands.describe(player_id="The SteamID or in-game name of the player")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def pal_ban(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.defer(thinking=True)
        
        # --- V2.0 ---
        # Step 1: Send RCON Kick (to get them off now)
        rcon_response = await run_rcon_command(self.rcon_command, f"KickPlayer {player_id}")
        
        # Step 2: Add to banlist.txt for persistence
        file_response = await self.add_to_banlist(player_id)
        
        if "RCON_ERROR" in rcon_response:
            embed = create_embed("RCON Error", rcon_response, discord.Color.red(), self.image_url)
            embed.add_field(name="File Status", value=file_response)
        else:
            embed = create_embed("Ban Command Sent", f"RCON Kick Response:\n`{rcon_response}`", discord.Color.green(), self.image_url)
            embed.add_field(name="Persistent Ban Status", value=file_response, inline=False)
            
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pal_info", description="Looks up information about a specific Pal.")
    @app_commands.describe(pal_name="The name of the Pal to look up")
    @check_channel_id("palworld_channel_ids")
    async def pal_info(self, interaction: discord.Interaction, pal_name: str):
        await interaction.response.defer(thinking=True)
        pal_name_formatted = pal_name.replace(" ", "_").title()
        page_url = f"https://palworld.fandom.com/wiki/{pal_name_formatted}"
        
        html = await fetch_html(page_url)
        if not html:
            embed = create_embed(
                "Pal Not Found",
                f"Could not find a wiki page for **{pal_name}**.\n"
                f"Check your spelling or try this link: [Search Wiki](https://palworld.fandom.com/wiki/Special:Search?search={pal_name_formatted})",
                discord.Color.orange(),
                self.image_url
            )
            await interaction.followup.send(embed=embed)
            return

        embed = await asyncio.to_thread(self.parse_pal_info, html, pal_name, page_url)
        await interaction.followup.send(embed=embed)
        
    def parse_pal_info(self, html: str, pal_name: str, page_url: str) -> discord.Embed:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            elements = []
            element_div = soup.find('div', {'data-source': 'element'})
            if element_div:
                for a_tag in element_div.find_all('a'):
                    elements.append(a_tag.get('title', ''))
            elements_str = ", ".join(elements) or "Unknown"
            work_suitability = []
            work_div = soup.find('div', {'data-source': 'work'})
            if work_div:
                for a_tag in work_div.find_all('a'):
                    work_title = a_tag.get('title', '')
                    level_span = a_tag.find_next_sibling('span')
                    if level_span:
                        work_title += f" {level_span.text.strip()}"
                    work_suitability.append(work_title)
            work_str = "\n".join(work_suitability) or "None"
            image_url = self.image_url 
            img_tag = soup.find('figure', {'data-source': 'image'})
            if img_tag and img_tag.find('a'):
                image_url = img_tag.find('a')['href']
            embed = create_embed(f"Pal Info: {pal_name.title()}", f"[View Full Wiki Page]({page_url})", discord.Color.blue(), image_url)
            embed.add_field(name="Element(s)", value=elements_str, inline=True)
            embed.add_field(name="Work Suitability", value=work_str, inline=True)
            return embed
        except Exception as e:
            logger.error(f"Failed to parse Palworld wiki page: {e}")
            return create_embed("Parse Error", f"Could not parse the wiki page for {pal_name}. The wiki layout may have changed.", discord.Color.red(), self.image_url)

# ---------------------------------
# Cog: ArkCog
# ---------------------------------
class ArkCog(commands.Cog, name="ArkCog"):
    def __init__(self, bot: GameBot, image_url: str):
        self.bot = bot
        self.image_url = image_url
        self.server_ip = get_config_value("server_ips.ark_ip", "").split(':')[0]
        self.rcon_port = get_config_value("server_ips.ark_ip", ":0").split(':')[1]
        self.query_port = get_config_value("query_ports.ark_query_port", 0)
        self.rcon_pass = get_config_value("rcon_settings.ark_admin_pass", "")
        
    async def get_ark_status(self) -> str:
        if not self.server_ip or not self.query_port:
            return "Server IP or Query Port not configured."
        address = (self.server_ip, int(self.query_port))
        try:
            info = await run_a2s_query(address)
            if "A2S_ERROR" in str(info): return f"**Offline**\nReason: `{info}`"
            return f"**Online** - `{info.server_name}`\n" \
                   f"Players: `{info.player_count}/{info.max_players}`\n" \
                   f"Map: `{info.map_name}`"
        except Exception as e:
            logger.warning(f"Failed to query ARK server {address}: {e}")
            return "**Offline**"

    def rcon_command(self, command: str):
        ark_ip = self.server_ip
        ark_port = int(self.rcon_port)
        ark_pass = self.rcon_pass
        try:
            with MCRcon(ark_ip, ark_pass, ark_port) as mcr:
                response = mcr.command(command)
                return response or "Command sent (no response)."
        except Exception as e:
            raise e

    @app_commands.command(name="ark_status", description="Checks the status of the ARK: ASA server.")
    @check_channel_id("ark_channel_ids")
    async def ark_status(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        status_str = await self.get_ark_status()
        color = discord.Color.green() if "Online" in status_str else discord.Color.red()
        embed = create_embed("ARK: ASA Server Status", status_str, color, self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ark_broadcast", description="Broadcasts a message to the ARK server.")
    @app_commands.describe(message="The message to send")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def ark_broadcast(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, f"ServerChat {message}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Broadcast Sent", f"Sent to ARK server:\n`{message}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ark_players", description="Lists players on the ARK server.")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def ark_players(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, "ListPlayers")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("ARK Player List", f"```{response}```", discord.Color.blue(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ark_save", description="Saves the ARK server world.")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def ark_save(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, "SaveWorld")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("World Save", f"Response from server:\n`{response}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ark_kick", description="Kicks a player from the ARK server (must be SteamID).")
    @app_commands.describe(steam_id="The 64-bit SteamID of the player")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def ark_kick(self, interaction: discord.Interaction, steam_id: str):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, f"KickPlayer {steam_id}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Kick Command Sent", f"Response from server:\n`{response}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ark_ban", description="Bans a player from the ARK server (must be SteamID).")
    @app_commands.describe(steam_id="The 64-bit SteamID of the player")
    @app_commands.checks.has_permissions(administrator=True)
    @check_channel_id("admin_channel_ids")
    async def ark_ban(self, interaction: discord.Interaction, steam_id: str):
        await interaction.response.defer(thinking=True)
        response = await run_rcon_command(self.rcon_command, f"BanPlayer {steam_id}")
        if "RCON_ERROR" in response:
            embed = create_embed("RCON Error", response, discord.Color.red(), self.image_url)
        else:
            embed = create_embed("Ban Command Sent", f"Response from server:\n`{response}`", discord.Color.green(), self.image_url)
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="ark_tame", description="Looks up taming info for an ARK creature.")
    @app_commands.describe(creature_name="The name of the creature to look up")
    @check_channel_id("ark_channel_ids")
    async def ark_tame(self, interaction: discord.Interaction, creature_name: str):
        await interaction.response.defer(thinking=True)
        creature_name_formatted = creature_name.replace(" ", "_").title()
        page_url = f"https://ark.fandom.com/wiki/{creature_name_formatted}"
        
        html = await fetch_html(page_url)
        if not html:
            embed = create_embed("Creature Not Found", f"Could not find a wiki page for **{creature_name}**.", discord.Color.orange(), self.image_url)
            await interaction.followup.send(embed=embed)
            return

        embed = await asyncio.to_thread(self.parse_ark_tame, html, creature_name, page_url)
        await interaction.followup.send(embed=embed)
        
    def parse_ark_tame(self, html: str, creature_name: str, page_url: str) -> discord.Embed:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            taming_method = "Unknown"
            taming_div = soup.find('div', {'data-source': 'tamingmethod'})
            if taming_div:
                taming_method = taming_div.find('div', class_='pi-data-value').text.strip()
            food = "Unknown"
            food_div = soup.find('div', {'data-source': 'food'})
            if food_div:
                food = food_div.find('div', class_='pi-data-value').text.strip()
            image_url = self.image_url
            img_tag = soup.find('figure', {'data-source': 'image'})
            if img_tag and img_tag.find('a'):
                image_url = img_tag.find('a')['href']
            embed = create_embed(f"ARK Taming: {creature_name.title()}", f"[View Full Wiki Page]({page_url})", discord.Color.blue(), image_url)
            embed.add_field(name="Taming Method", value=taming_method, inline=True)
            embed.add_field(name="Preferred Food", value=food, inline=True)
            return embed
        except Exception as e:
            logger.error(f"Failed to parse ARK wiki page: {e}")
            return create_embed("Parse Error", f"Could not parse the wiki page for {creature_name}.", discord.Color.red(), self.image_url)

# ---------------------------------
# Cog: EconomyCog (--- V3.0 NEW ---)
# ---------------------------------
class EconomyCog(commands.Cog):
    def __init__(self, bot: GameBot, image_url: str):
        self.bot = bot
        self.image_url = image_url
        self.cog_map = {'mc': 'MinecraftCog', 'pal': 'PalworldCog', 'ark': 'ArkCog'}

    @app_commands.command(name="link", description="Links your Discord account to your in-game name (IGN).")
    @app_commands.describe(in_game_name="Your exact in-game name")
    async def link(self, interaction: discord.Interaction, in_game_name: str):
        discord_id = str(interaction.user.id)
        
        success = await asyncio.to_thread(db.link_user, discord_id, in_game_name)
        
        if success:
            embed = create_embed(
                "Account Linked",
                f"Your Discord account is now linked to the in-game name: **{in_game_name}**",
                discord.Color.green(),
                self.image_url
            )
        else:
            embed = create_embed(
                "Link Failed",
                f"The in-game name **{in_game_name}** is already linked to another Discord account. "
                "If this is a mistake, please contact an admin.",
                discord.Color.red(),
                self.image_url
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unlink", description="Removes the in-game name link from your Discord account.")
    async def unlink(self, interaction: discord.Interaction):
        discord_id = str(interaction.user.id)
        await asyncio.to_thread(db.unlink_user, discord_id)
        embed = create_embed(
            "Account Unlinked",
            "Your in-game name has been unlinked. You will keep your points.",
            discord.Color.orange(),
            self.image_url
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="balance", description="Checks your current point balance.")
    async def balance(self, interaction: discord.Interaction):
        discord_id = str(interaction.user.id)
        points = await asyncio.to_thread(db.get_points, discord_id)
        user = await asyncio.to_thread(db.get_user_by_discord_id, discord_id)
        ign = user.get('in_game_name', 'Not Linked') if user else 'Not Linked'
        
        embed = create_embed(
            f"{interaction.user.display_name}'s Balance",
            f"You have **{points}** points.",
            discord.Color.blue(),
            self.image_url
        )
        embed.add_field(name="Linked Account", value=f"`{ign}`")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="shop", description="Displays the in-game item shop.")
    async def shop(self, interaction: discord.Interaction):
        shop_items = get_config_value("shop_items", [])
        if not shop_items:
            embed = create_embed("Shop is Empty", "There are no items in the shop. Contact an admin.", discord.Color.red(), self.image_url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = create_embed("In-Game Shop", "Use `/buy [item_id]` to purchase an item.", discord.Color.gold(), self.image_url)
        
        for item in shop_items:
            embed.add_field(
                name=f"{item.get('name', 'Unknown Item')} ({item.get('game', '??').upper()})",
                value=f"**Cost:** {item.get('cost', 0)} points\n"
                      f"**ID:** `{item.get('id', 'N/A')}`",
                inline=True
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buys an item from the shop.")
    @app_commands.describe(item_id="The ID of the item you want to buy (see /shop)")
    async def buy(self, interaction: discord.Interaction, item_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        discord_id = str(interaction.user.id)
        
        # 1. Check if user is linked
        user = await asyncio.to_thread(db.get_user_by_discord_id, discord_id)
        if not user or not user.get('in_game_name'):
            embed = create_embed("Purchase Failed", "You must link your in-game name first using `/link [ign]`.", discord.Color.red(), self.image_url)
            await interaction.followup.send(embed=embed)
            return
        
        in_game_name = user['in_game_name']
        
        # 2. Find the item
        shop_items = get_config_value("shop_items", [])
        item_to_buy = next((item for item in shop_items if item.get('id') == item_id), None)
        
        if not item_to_buy:
            embed = create_embed("Purchase Failed", f"Could not find an item with the ID `{item_id}`. Use `/shop` to see items.", discord.Color.red(), self.image_url)
            await interaction.followup.send(embed=embed)
            return

        item_cost = item_to_buy.get('cost', 0)
        
        # 3. Check points
        current_points = user.get('points', 0)
        if current_points < item_cost:
            embed = create_embed("Purchase Failed", f"You do not have enough points. You need **{item_cost}** but only have **{current_points}**.", discord.Color.red(), self.image_url)
            await interaction.followup.send(embed=embed)
            return

        # 4. Get the correct cog
        game_key = item_to_buy.get('game')
        cog_name = self.cog_map.get(game_key)
        cog = self.bot.get_cog(cog_name)
        
        if not cog:
            logger.error(f"Shop item '{item_id}' has invalid game key '{game_key}'.")
            embed = create_embed("Purchase Failed", "This item is misconfigured. Please contact an admin.", discord.Color.red(), self.image_url)
            await interaction.followup.send(embed=embed)
            return

        # 5. All checks passed. Subtract points & Run RCON
        new_balance = await asyncio.to_thread(db.update_points, discord_id, -item_cost)
        
        rcon_errors = []
        for command in item_to_buy.get('rcon_commands', []):
            formatted_cmd = command.format(in_game_name=in_game_name)
            response = await run_rcon_command(cog.rcon_command, formatted_cmd)
            if "RCON_ERROR" in response:
                rcon_errors.append(response)

        # 6. Send receipt
        if rcon_errors:
            embed = create_embed(
                "Purchase Partially Failed",
                f"You bought **{item_to_buy.get('name')}** for {item_cost} points.\n"
                f"Your new balance is **{new_balance}** points.\n\n"
                f"**However, an error occurred giving you the items:**\n`{rcon_errors[0]}`\n"
                "Please contact an admin.",
                discord.Color.orange(),
                self.image_url
            )
        else:
            embed = create_embed(
                "Purchase Successful!",
                f"You bought **{item_to_buy.get('name')}** for {item_cost} points.\n"
                f"Your new balance is **{new_balance}** points.\n\n"
                "Your items have been delivered in-game!",
                discord.Color.green(),
                self.image_url
            )
        await interaction.followup.send(embed=embed)

# ---------------------------------
# Cog: TasksCog (--- V3.0 UPDATED ---)
# ---------------------------------
class TasksCog(commands.Cog):
    def __init__(self, bot: GameBot):
        self.bot = bot
        self.status_message_id = None
        
        # V1 Tasks
        self.auto_status_config = get_config_value("automated_tasks.auto_status", {})
        
        # V3 Tasks
        self.crash_detector_config = get_config_value("proactive_management.crash_detector", {})
        self.smart_restart_config = get_config_value("proactive_management.smart_restart", {})
        
        self.offline_counters = {'mc': 0, 'pal': 0, 'ark': 0}

        # Start loops if enabled
        if self.auto_status_config.get("enabled", False):
            interval = self.auto_status_config.get("update_interval_minutes", 5)
            self.update_server_status.change_interval(minutes=interval)
            self.update_server_status.start()
            logger.info(f"Auto-status task started. Updating every {interval} minutes.")
            
        if self.crash_detector_config.get("enabled", False):
            self.crash_detector_task.start()
            logger.info("Crash detector task started.")

        if self.smart_restart_config.get("enabled", False):
            self.smart_restart_task.start()
            logger.info("Smart restart task started.")

    async def cog_unload(self):
        """Called when cog is unloaded to stop tasks."""
        self.update_server_status.cancel()
        self.crash_detector_task.cancel()
        self.smart_restart_task.cancel()

    @tasks.loop(minutes=5)
    async def update_server_status(self):
        channel_id_str = self.auto_status_config.get("channel_id")
        if not channel_id_str:
            logger.warning("Auto-status enabled but no channel_id set.")
            return
        try:
            channel = await self.bot.fetch_channel(int(channel_id_str))
        except (discord.NotFound, discord.Forbidden):
            logger.error(f"Cannot find or access auto-status channel: {channel_id_str}")
            return
        except ValueError:
            logger.error(f"Invalid auto-status channel ID: {channel_id_str}")
            return
            
        mc_cog = self.bot.get_cog("MinecraftCog")
        pal_cog = self.bot.get_cog("PalworldCog")
        ark_cog = self.bot.get_cog("ArkCog")
        admin_icon = get_config_value("embed_images.admin_icon")

        embed = create_embed("Live Server Status", f"Last updated: <t:{int(datetime.datetime.now().timestamp())}:R>", discord.Color.dark_purple(), admin_icon)
        
        if mc_cog: embed.add_field(name="Minecraft", value=await mc_cog.get_minecraft_status(), inline=False)
        if pal_cog: embed.add_field(name="Palworld", value=await pal_cog.get_palworld_status(), inline=False)
        if ark_cog: embed.add_field(name="ARK: ASA", value=await ark_cog.get_ark_status(), inline=False)
        
        try:
            if self.status_message_id:
                message = await channel.fetch_message(self.status_message_id)
                await message.edit(embed=embed)
            else:
                # Try to find a previous message to edit
                async for msg in channel.history(limit=50):
                    if msg.author.id == self.bot.user.id and msg.embeds and msg.embeds[0].title == "Live Server Status":
                        await msg.edit(embed=embed)
                        self.status_message_id = msg.id
                        return
                # No message found, send a new one
                message = await channel.send(embed=embed)
                self.status_message_id = message.id
        except discord.NotFound:
            message = await channel.send(embed=embed)
            self.status_message_id = message.id
        except discord.Forbidden:
            logger.error(f"Bot lacks permissions in auto-status channel: {channel_id_str}")
        except Exception as e:
            logger.error(f"Failed to update auto-status message: {e}")

    @update_server_status.before_loop
    async def before_update_server_status(self):
        await self.bot.wait_until_ready()

    # --- V3.0 ---
    @tasks.loop(minutes=1)
    async def crash_detector_task(self):
        """Checks server statuses and sends an alert if a server is offline for too long."""
        mc_cog = self.bot.get_cog("MinecraftCog")
        pal_cog = self.bot.get_cog("PalworldCog")
        ark_cog = self.bot.get_cog("ArkCog")
        
        check_threshold = self.crash_detector_config.get("offline_checks_before_alert", 3)
        alert_channel_id = self.crash_detector_config.get("alert_channel_id")
        admin_role_id = self.crash_detector_config.get("admin_role_id", "")
        ping = f"<@&{admin_role_id}>" if admin_role_id else "@here"
        
        if not alert_channel_id:
            logger.warning("Crash detector enabled but no alert_channel_id set.")
            return

        server_statuses = {
            'mc': await mc_cog.get_minecraft_status() if mc_cog else "**Offline**",
            'pal': await pal_cog.get_palworld_status() if pal_cog else "**Offline**",
            'ark': await ark_cog.get_ark_status() if ark_cog else "**Offline**",
        }

        for server, status in server_statuses.items():
            if "**Offline**" in status:
                self.offline_counters[server] += 1
                logger.warning(f"Crash Detector: {server} is offline. Count: {self.offline_counters[server]}")
                
                if self.offline_counters[server] == check_threshold:
                    logger.critical(f"SERVER DOWN: {server} has been offline for {check_threshold} checks. Sending alert.")
                    try:
                        channel = await self.bot.fetch_channel(int(alert_channel_id))
                        admin_icon = get_config_value("embed_images.admin_icon")
                        embed = create_embed(
                            "🚨 SERVER OFFLINE 🚨",
                            f"{ping} The **{server.upper()}** server has been detected as **OFFLINE** for {check_threshold} consecutive minutes.",
                            discord.Color.red(),
                            admin_icon
                        )
                        await channel.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Failed to send crash alert: {e}")
            else:
                if self.offline_counters[server] >= check_threshold:
                    # Server is back online
                    logger.info(f"Server {server} is back online.")
                    try:
                        channel = await self.bot.fetch_channel(int(alert_channel_id))
                        admin_icon = get_config_value("embed_images.admin_icon")
                        embed = create_embed(
                            "✅ SERVER ONLINE ✅",
                            f"The **{server.upper()}** server is now back **ONLINE**.",
                            discord.Color.green(),
                            admin_icon
                        )
                        await channel.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Failed to send server recovery alert: {e}")
                self.offline_counters[server] = 0

    @crash_detector_task.before_loop
    async def before_crash_detector_task(self):
        await self.bot.wait_until_ready()

    # --- V3.0 ---
    @tasks.loop(seconds=60)
    async def smart_restart_task(self):
        """Runs scheduled broadcasts and shutdowns based on UTC time."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        current_time_str = now_utc.strftime('%H:%M')
        
        schedule = self.smart_restart_config.get("schedule", [])
        
        for event in schedule:
            if event.get("time_utc") == current_time_str:
                logger.info(f"Smart Restart: Triggering event for {current_time_str} UTC.")
                
                mc_cog = self.bot.get_cog("MinecraftCog")
                pal_cog = self.bot.get_cog("PalworldCog")
                ark_cog = self.bot.get_cog("ArkCog")
                
                # 1. Send Broadcast Message
                message = event.get("message", "")
                if message and mc_cog:
                    await run_rcon_command(mc_cog.rcon_command, f"say {message}")
                if message and pal_cog:
                    pal_message = message.replace(" ", "_")
                    await run_rcon_command(pal_cog.rcon_command, f"Broadcast {pal_message}")
                if message and ark_cog:
                    await run_rcon_command(ark_cog.rcon_command, f"ServerChat {message}")

                # 2. Run Save Commands
                save_commands = event.get("commands", [])
                for cmd in save_commands:
                    if mc_cog: await run_rcon_command(mc_cog.rcon_command, cmd)
                    if pal_cog: await run_rcon_command(pal_cog.rcon_command, cmd)
                    if ark_cog: await run_rcon_command(ark_cog.rcon_command, cmd)

                # 3. Run Shutdown Commands
                shutdown_commands = event.get("shutdown_commands", [])
                for cmd in shutdown_commands:
                    if mc_cog: await run_rcon_command(mc_cog.rcon_command, cmd)
                    if pal_cog: await run_rcon_command(pal_cog.rcon_command, cmd)
                    if ark_cog: await run_rcon_command(ark_cog.rcon_command, cmd)

    @smart_restart_task.before_loop
    async def before_smart_restart_task(self):
        await self.bot.wait_until_ready()

# ---------------------------------
# Cog: LogWatcherCog (--- V3.0 UPDATED ---)
# ---------------------------------
class LogFileHandler(FileSystemEventHandler):
    def __init__(self, bot: GameBot):
        self.bot = bot
        self.file_handles: Dict[str, io.BufferedReader] = {}
        self.log_paths: Dict[str, Dict[str, Any]] = {}
        self.economy_enabled = get_config_value("economy.enabled", False)
        self.points_per_chat = get_config_value("economy.points_per_chat_message", 0)
        self.chat_cooldowns = {} # V3: Player chat cooldowns
        self.cooldown_seconds = get_config_value("economy.chat_cooldown_seconds", 60)
        
        # --- V3.0 ---
        # Define regex patterns for parsing logs
        # These will likely need to be customized for specific server setups
        self.regex_patterns = {
            'mc': [
                re.compile(r'\[Server thread/INFO\]: <(?P<username>\w+)> (?P<message>.+)'), # MC Chat
                re.compile(r'\[User Authenticator #\d+/INFO\]: UUID of player (?P<username>\w+) is .+'), # MC Join
                re.compile(r'\[Server thread/INFO\]: (?P<username>\w+) left the game'), # MC Leave
                re.compile(r'\[Server thread/INFO\]: (?P<message>.+ (was slain by|drowned|fell|burned|etc\.))') # MC Death (basic)
            ],
            'pal': [
                re.compile(r'\]: (?P<username>.+): (?P<message>.+)'), # Palworld Chat
                re.compile(r'OnPlayerJoined.+?\](?P<username>.+),') # Palworld Join
            ],
            'ark': [
                re.compile(r'Server: (?P<username>.+?): (?P<message>.+)'), # ARK Chat
                re.compile(r'("?)(?P<username>.+?)\1 has joined this ARK!'), # ARK Join
                re.compile(r'("?)(?P<username>.+?)\1 left this ARK!'), # ARK Leave
                re.compile(r'("?)(?P<username>.+?)\1 was killed by ("?)(?P<killer>.+?)\3!'), # ARK PVP Death
                re.compile(r'("?)(?P<username>.+?)\1 was killed!'), # ARK PVE Death
                re.compile(r'Tribe ("?)(?P<tribe>.+?)\1, Member ("?)(?P<username>.+?)\3 Tamed an? ("?)(?P<creature>.+?)\5 Lvl (?P<level>\d+)') # ARK Tame
            ]
        }
        
        self.relay_channels = {
            'mc': get_config_value("discord_channel_ids.minecraft_chat_relay_channel_id"),
            'pal': get_config_value("discord_channel_ids.palworld_chat_relay_channel_id"),
            'ark': get_config_value("discord_channel_ids.ark_chat_relay_channel_id"),
        }
        
        self.log_paths_config = get_config_value("server_file_paths", {})
        if self.log_paths_config.get("minecraft_log_path"):
            self.log_paths["mc"] = {'path': self.log_paths_config["minecraft_log_path"]}
        if self.log_paths_config.get("palworld_log_path"):
            self.log_paths["pal"] = {'path': self.log_paths_config["palworld_log_path"]}
        if self.log_paths_config.get("ark_log_path"):
            self.log_paths["ark"] = {'path': self.log_paths_config["ark_log_path"]}

    def start_monitoring(self):
        """Opens log files and seeks to the end."""
        for game, config in self.log_paths.items():
            path = config['path']
            if not path or not os.path.exists(path):
                logger.warning(f"Log path for {game} not found or not set: {path}. Skipping.")
                continue
            try:
                f = open(path, 'r', encoding='utf-8', errors='ignore')
                f.seek(0, io.SEEK_END)
                self.file_handles[game] = f
                logger.info(f"Monitoring log file for {game} at {path}")
            except Exception as e:
                logger.error(f"Failed to open log file {path}: {e}")

    def stop_monitoring(self):
        """Closes all open log file handles."""
        for game, f in self.file_handles.items():
            try:
                f.close()
                logger.info(f"Stopped monitoring log file for {game}.")
            except Exception as e:
                logger.error(f"Failed to close log file for {game}: {e}")

    def process_new_lines(self):
        """Reads new lines from all monitored files and processes them."""
        for game, f in self.file_handles.items():
            try:
                new_lines = f.readlines()
                if new_lines:
                    for line in new_lines:
                        self.parse_log_line(game, line.strip())
            except Exception as e:
                logger.error(f"Error reading log file for {game}: {e}")

    def on_modified(self, event):
        """Called by watchdog when a file is modified."""
        # This event can be noisy; process_new_lines is called by the loop
        pass

    def on_created(self, event):
        """Called by watchdog when a file is created (e.g., log rotation)."""
        logger.info(f"Log file event (created): {event.src_path}. Re-opening files.")
        self.stop_monitoring()
        self.start_monitoring()

    def parse_log_line(self, game: str, line: str):
        """Parses a single log line against regex patterns."""
        if not line:
            return

        for pattern in self.regex_patterns.get(game, []):
            match = pattern.search(line)
            if match:
                data = match.groupdict()
                # Schedule the async Discord message
                asyncio.run_coroutine_threadsafe(self.handle_log_event(game, data), self.bot.loop)
                return # Stop after first match

    async def handle_log_event(self, game: str, data: Dict[str, Any]):
        """Formats the parsed log data and sends it to Discord."""
        channel_id = self.relay_channels.get(game)
        if not channel_id:
            return

        try:
            channel = await self.bot.fetch_channel(int(channel_id))
        except (discord.NotFound, discord.Forbidden):
            logger.warning(f"Cannot find or access relay channel {channel_id} for {game}.")
            return
        
        message = ""
        
        # V3: Economy - Points for Chat
        if 'username' in data and 'message' in data and self.economy_enabled and self.points_per_chat > 0:
            username = data['username']
            # Check cooldown
            now = time.time()
            if now - self.chat_cooldowns.get(username, 0) > self.cooldown_seconds:
                self.chat_cooldowns[username] = now
                # Award points in a separate thread
                await asyncio.to_thread(db.add_points_by_ign, username, self.points_per_chat)

        # Standard Chat Relay
        if 'username' in data and 'message' in data:
            message = f"**{data['username']}**: {data['message']}"
        # Join/Leave
        elif 'username' in data and 'joined' in line:
            message = f"➡️ *{data['username']} joined the {game.upper()} server.*"
        elif 'username' in data and 'left' in line:
            message = f"⬅️ *{data['username']} left the {game.upper()} server.*"
        
        # --- V3.0 Events ---
        # ARK Taming
        elif 'tribe' in data and 'creature' in data:
            message = f"🦖 **TAME!** Tribe **{data['tribe']}** (member {data['username']}) just tamed a **Lvl {data['level']} {data['creature']}**!"
        # ARK PVP Death
        elif 'username' in data and 'killer' in data:
            message = f"⚔️ **PVP!** *{data['username']}* was killed by *{data['killer']}*!"
        # ARK/MC PVE Death
        elif 'username' in data and 'killed' in line:
            message = f"☠️ *{data['username']} was killed!*"
        elif 'message' in data and any(kw in data['message'] for kw in ['slain', 'drowned', 'fell', 'burned']):
             message = f"☠️ *{data['message']}*"

        if message:
            try:
                await channel.send(message)
            except discord.Forbidden:
                logger.warning(f"Missing permissions to send message in relay channel {channel_id}")
            except Exception as e:
                logger.error(f"Failed to send relay message: {e}")


class LogWatcherCog(commands.Cog):
    def __init__(self, bot: GameBot):
        self.bot = bot
        self.handler = LogFileHandler(bot)
        self.observer = Observer()
        self.monitoring_paths = set()
        
        for config in self.handler.log_paths.values():
            path = config['path']
            if path:
                self.monitoring_paths.add(os.path.dirname(path))
        
        self.log_reader_task.start()

    def start_watching(self):
        """Starts the watchdog observer."""
        if not self.monitoring_paths:
            logger.warning("Log Watcher: No valid log paths configured. Watcher will not start.")
            return

        self.handler.start_monitoring()
        
        for path in self.monitoring_paths:
            try:
                self.observer.schedule(self.handler, path, recursive=False)
                logger.info(f"Log Watcher: Observer scheduled for path: {path}")
            except Exception as e:
                logger.error(f"Failed to schedule observer for {path}: {e}")
        
        try:
            self.observer.start()
            logger.info("Log Watcher: File observer started.")
        except Exception as e:
            logger.critical(f"Log Watcher: Observer failed to start: {e}")

    def stop_watching(self):
        """Stops the watchdog observer and closes files."""
        logger.info("Log Watcher: Stopping observer...")
        self.observer.stop()
        self.observer.join()
        self.handler.stop_monitoring()
        self.log_reader_task.cancel()
        logger.info("Log Watcher: Observer stopped.")

    @tasks.loop(seconds=1.0)
    async def log_reader_task(self):
        """Periodically polls the log files for new lines."""
        try:
            # Run the blocking file read in a separate thread
            await asyncio.to_thread(self.handler.process_new_lines)
        except Exception as e:
            logger.error(f"Error in log_reader_task: {e}")

    @log_reader_task.before_loop
    async def before_log_reader_task(self):
        await self.bot.wait_until_ready()

    async def cog_unload(self):
        """Ensures the observer is stopped when the cog is unloaded."""
        self.stop_watching()

# ---------------------------------
# Main Bot Execution
# ---------------------------------
async def main():
    token = get_config_value("discord_bot_token")
    if not token:
        logger.critical("Bot token not found in config.json. Exiting.")
        return
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.critical("Invalid Discord token. Please check your config.json.")
    except Exception as e:
        logger.critical(f"An error occurred while running the bot: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user.")