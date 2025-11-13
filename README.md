# **🎮 Multi-Game Dedicated Server Monitor & RCON Bot**

This is a powerful Discord bot built with discord.py designed to manage and monitor multiple dedicated game servers—specifically **Minecraft**, **Palworld**, and **ARK: Survival Ascended (ASA)**—using RCON (Remote Console).

The bot provides real-time status updates, scheduled automatic backups, and administrator tools directly accessible via Discord commands.

## **✨ Features**

* **Dedicated Channel Routing:** Status updates, auto-save messages, and server change notifications are sent to game-specific channels (\#minecraft-status, \#palworld-logs, etc.).  
* **Admin-Only Channel Enforcement:** All administrative RCON commands (like \!say, \!ban, \!shutdown) **must be executed** in a single, dedicated **Admin Channel**.  
* **Multi-Game Support:** Unified management for Minecraft, Palworld, and ASA.  
* **Real-time Status Monitoring:** Automatically checks and reports the online/offline status of all configured servers.  
* **Scheduled Actions:** Automated **Palworld** and **ASA** world-saving loops to ensure data integrity.  
* **RCON Command Execution:** Send in-game chat messages and execute ban commands.  
* **Permission Control:** All administrative commands require the Discord user to have **Administrator** permissions.

## **🛠️ Prerequisites**

Before running the bot, you must have the following set up:

1. **Python 3.8+** installed.  
2. A **Discord Bot Token** and a Discord server where the bot has appropriate permissions (including the ability to read messages and send embeds).  
3. **RCON enabled and configured** on each of your dedicated game servers.

## **⚙️ Installation & Setup**

### **1\. Dependencies**

Install the required Python packages using pip:

pip install \-r requirements.txt

### **2\. Configuration (Environment Variables)**

The bot is configured primarily using environment variables. **You must configure the four new channel IDs.**

| Variable | Description | Example Value |
| :---- | :---- | :---- |
| DISCORD\_TOKEN | **Mandatory.** Your Discord Bot Token. | NzQ3NjY4Mzk0NzgwODcwMjY3.X8n9\_A.L32qE... |
| ADMIN\_CHANNEL\_ID | **MANDATORY.** Channel ID where **all RCON commands** must be run. | 123456789012345678 |
| MC\_CHANNEL\_ID | **MANDATORY.** Channel ID for Minecraft status updates/logs. | 112233445566778899 |
| PAL\_CHANNEL\_ID | **MANDATORY.** Channel ID for Palworld status, auto-saves, and logs. | 223344556677889900 |
| ASA\_CHANNEL\_ID | **MANDATORY.** Channel ID for ASA status, auto-saves, and logs. | 334455667788990011 |
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

| Command | Status/Log Destination | Execution Requirement | Description |
| :---- | :---- | :---- | :---- |
| \!status | Reply in Channel | Any Channel | Checks and reports the status and player count for all servers. |
| \!say\_mc, \!ban\_pal, \!shutdown\_asa, etc. | Reply in **Admin Channel** | **Admin Channel ONLY** & **Admin Permission** | All RCON administration commands. |

**Important:** If you attempt to run any administrative command (e.g., \!ban\_pal) outside of the channel specified by ADMIN\_CHANNEL\_ID, the bot will deny the command and instruct you to use the correct channel.