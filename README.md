# **🎮 Multi-Game Dedicated Server Monitor & RCON Bot**

This is a powerful Discord bot built with discord.py designed to manage and monitor multiple dedicated game servers—specifically **Minecraft**, **Palworld**, and **ARK: Survival Ascended (ASA)**—using RCON (Remote Console).

The bot provides real-time status updates, scheduled automatic backups, and administrator tools directly accessible via Discord commands.

## **✨ Features**

* **Multi-Game Support:** Unified management for Minecraft, Palworld, and ASA.  
* **Real-time Status Monitoring:** Automatically checks and reports the online/offline status of all configured servers.  
* **Scheduled Actions:** Automated **Palworld** and **ASA** world-saving loops to ensure data integrity.  
* **RCON Command Execution:** Send in-game chat messages and execute ban commands across all supported servers.  
* **Discord Integration:** Sends essential logs (status changes, errors) to designated Discord channels.  
* **Permission Control:** All administrative commands require the Discord user to have **Administrator** permissions.

## **🛠️ Prerequisites**

Before running the bot, you must have the following set up:

1. **Python 3.8+** installed.  
2. A **Discord Bot Token** and a Discord server where the bot has appropriate permissions (including the ability to read messages and send embeds).  
3. **RCON enabled and configured** on each of your dedicated game servers:  
   * **Minecraft:** Requires a server with RCON enabled (e.g., Paper, Spigot, Vanilla with RCON enabled).  
   * **Palworld:** Requires RCON configuration in DefaultPalWorldSettings.ini or similar.  
   * **ASA:** Requires RCON configuration in your server's command line or GameUserSettings.ini.

## **⚙️ Installation & Setup**

### **1\. Dependencies**

Install the required Python packages using pip:

pip install \-r requirements.txt

*(Note: The primary external libraries needed are discord.py (specifically discord.ext.commands) and rcon-asyncio.)*

### **2\. Configuration (Environment Variables)**

The bot is configured primarily using environment variables for security. You can set these in a shell or use a .env file (if you are using a tool that supports it).

| Variable | Description | Example Value |
| :---- | :---- | :---- |
| DISCORD\_TOKEN | **Mandatory.** Your Discord Bot Token. | NzQ3NjY4Mzk0NzgwODcwMjY3.X8n9\_A.L32qE... |
| TARGET\_CHANNEL\_ID | **Mandatory.** The Discord channel ID for status reports and logs. | 123456789012345678 |
| LOG\_CHANNEL\_ID | **Optional.** Channel ID for more verbose admin/error logs (defaults to TARGET\_CHANNEL\_ID). | 987654321098765432 |
| MC\_RCON\_HOST | Minecraft RCON IP address. | 127.0.0.1 |
| MC\_RCON\_PORT | Minecraft RCON Port. | 25575 |
| MC\_RCON\_PASSWORD | Minecraft RCON Password. | mc-secret-pw |
| PAL\_RCON\_HOST | Palworld RCON IP address. | 127.0.0.1 |
| PAL\_RCON\_PORT | Palworld RCON Port. | 25576 |
| PAL\_RCON\_PASSWORD | Palworld RCON Password. | pal-secret-pw |
| ASA\_RCON\_HOST | ASA RCON IP address. | 127.0.0.1 |
| ASA\_RCON\_PORT | ASA RCON Port. | 25577 |
| ASA\_RCON\_PASSWORD | ASA RCON Password. | asa-secret-pw |
| ASA\_SAVE\_INTERVAL | ASA Auto-save interval in minutes. | 60 (Default) |
| PAL\_SAVE\_INTERVAL | Palworld Auto-save interval in minutes. | 30 (Default) |

### **3\. Running the Bot**

Once the configuration is complete, run the Python script:

python Multi-Game Dedicated Monitor Bot.py

## **🚀 Discord Commands**

All RCON commands listed below require the user to have the **Administrator** permission role in the Discord server.

### **Server Status**

| Command | Description |
| :---- | :---- |
| \!status | Checks the connection and current player count for all configured game servers. |

### **RCON Messaging**

| Command | Server | Usage | Description |
| :---- | :---- | :---- | :---- |
| \!say\_mc | Minecraft | \!say\_mc \<message\> | Sends a message to all players on the Minecraft server. |
| \!say\_pal | Palworld | \!say\_pal \<message\> | Sends a message to all players on the Palworld server. |
| \!say\_asa | ASA | \!say\_asa \<message\> | Broadcasts a message on the ARK server. |

### **Player Management (Banning)**

| Command | Server | Usage | Description |
| :---- | :---- | :---- | :---- |
| \!ban\_mc | Minecraft | \!ban\_mc \<player\_name\> | Bans a player by name from the Minecraft server. |
| \!ban\_pal | Palworld | \!ban\_pal \<steam\_id\> | Bans a player by their Steam ID from the Palworld server. |
| \!ban\_asa | ASA | \!ban\_asa \<steam\_id\_or\_name\> | Bans a player by Steam ID or name from the ASA server. |

### **Server Actions**

| Command | Server | Usage | Description |
| :---- | :---- | :---- | :---- |
| \!save\_pal | Palworld | \!save\_pal | Manually triggers a world save on the Palworld server. |
| \!save\_asa | ASA | \!save\_asa | Manually triggers a world save on the ASA server. |
| \!shutdown\_pal | Palworld | \!shutdown\_pal \<delay\_seconds\> \<message\> | Shuts down the Palworld server after a delay (e.g., \!shutdown\_pal 60 Server restarting). |
| \!shutdown\_asa | ASA | \!shutdown\_asa | **Warning:** This command is configured to send the RCON DoExit command, which immediately shuts down the ASA server. |
| \!reload\_asa\_config | ASA | \!reload\_asa\_config | Reloads the configuration files for the ASA server. |

## **📝 Troubleshooting**

* **Fatal Error: DISCORD\_TOKEN Missing:** Ensure the DISCORD\_TOKEN environment variable is set correctly and is not the default placeholder.  
* **Permission Denied:** If commands fail with "Permission Denied\!", ensure the bot's Discord role has the **Administrator** permission enabled.  
* **RCON Connection Failed:** Double-check the RCON host, port, and password for the specific game in your configuration. Verify that the RCON service is running and accessible on the server's firewall.