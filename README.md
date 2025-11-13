# **Multi-Game Dedicated Server Monitor and RCON Bot**

This Python-based Discord bot provides real-time status monitoring, automated saving, and administrator Remote Console (RCON) command execution for multiple dedicated game servers, including **Minecraft**, **Palworld**, and **ARK: Survival Ascended (ASA)**.

## **✨ Features**

* **Multi-Server Status:** Use the \!status command to get the current online status and player count for all configured servers.  
* **Automated Backups:** Scheduled automatic world saving for Palworld and ASA (configurable interval).  
* **Administrator RCON Commands:** Securely run server commands (e.g., \!say\_mc, \!shutdown\_pal, \!ban\_asa) from a dedicated Discord channel.  
* **Persistent Palworld Ban List:** Automatically tracks and kicks players using a server-independent, file-based Steam ID blacklist.  
* **Secure Configuration:** Uses a .env file to securely manage Discord tokens and RCON passwords.  
* **Easy Setup:** Includes an installer script (setup\_bot.py) to handle dependencies and initial configuration file generation.

## **🛠️ Setup and Installation**

### **Prerequisites**

1. **Python 3.8+** (Required)  
2. **RCON Enabled** on all target game servers (Minecraft, Palworld, ASA) with host, port, and password noted.  
3. A **Discord Bot Token** and the ability to find your desired Discord **Channel IDs**.

### **Step 1: Run the Installer**

The included setup\_bot.py script will install all necessary Python libraries and create the configuration file.

1. Ensure you have the following files in the same directory:  
   * Multi-Game Dedicated Monitor Bot.py  
   * requirements.txt  
   * setup\_bot.py  
2. Open your terminal or command prompt in that directory and run:  
   python setup\_bot.py

### **Step 2: Configure the Bot**

The installer created a file named **.env**. You **must** open this file and replace all placeholder values (YOUR\_...\_HERE or 0000...) with your actual information.

| Variable | Description | Example Value |
| :---- | :---- | :---- |
| DISCORD\_TOKEN | Your Discord bot's authentication token. | MzIwMDMwNjY1MzM2ODQ2OTc2.C8-QJg.cM5R5j2R... |
| ADMIN\_CHANNEL\_ID | The ID of the Discord channel where RCON commands (\!say\_mc, \!ban\_pal, etc.) can be used. | 123456789012345678 |
| MC\_CHANNEL\_ID | Channel ID for Minecraft status updates. | 123456789012345679 |
| PAL\_CHANNEL\_ID | Channel ID for Palworld status and auto-save logs. | 123456789012345680 |
| ASA\_CHANNEL\_ID | Channel ID for ARK: ASA status and auto-save logs. | 123456789012345681 |
| \[GAME\]\_RCON\_HOST/PORT/PASSWORD | Host IP (usually 127.0.0.1 if on the same machine), Port, and Password for each game's RCON service. | MC\_RCON\_PORT=25575 |
| PAL\_SAVE\_INTERVAL | Automated save interval for Palworld in **minutes** (Default: 30). | 30 |
| ASA\_SAVE\_INTERVAL | Automated save interval for ARK: ASA in **minutes** (Default: 60). | 60 |

### **Step 3: Run the Bot**

Use one of the included runner scripts to start the bot:

| System | Command | Notes |
| :---- | :---- | :---- |
| **Windows** | Double-click start\_bot.bat | This script will keep the window open after execution. |
| **Linux/macOS** | ./start\_bot.sh | You may need to run chmod \+x start\_bot.sh first to grant execution permission. |

## **💻 Bot Commands (Admin Channel Only)**

All RCON and admin commands require the user to have the **Administrator** permission in the Discord server and must be used in the channel specified by ADMIN\_CHANNEL\_ID.

| Command | Usage | Description |
| :---- | :---- | :---- |
| \!status | \!status | **(Any Channel)** Displays the current online status and player counts for all servers. |
| \!say\_mc | \!say\_mc Hello everyone\! | Broadcasts a message to the Minecraft server. |
| \!ban\_mc | \!ban\_mc PlayerName | Bans a player by name on the Minecraft server. |
| \!shutdown\_pal | \!shutdown\_pal \[delay\_seconds\] \[message\] | Safely shuts down the Palworld server after a countdown (default 60s). |
| \!save\_pal | \!save\_pal | Manually triggers an immediate world save for Palworld. |
| \!ban\_pal | \!ban\_pal 76561198000000000 | **Bans a player by 17-digit Steam ID.** Adds the ID to the persistent blacklist and attempts an immediate kick. |
| \!unban\_pal | \!unban\_pal 76561198000000000 | Removes a Steam ID from the persistent blacklist. |
| \!list\_bans\_pal | \!list\_bans\_pal | Lists all Steam IDs currently on the persistent blacklist. |
| \!ban\_asa | \!ban\_asa PlayerName | Bans a player by name or ID on the ARK: ASA server. |

