# **🎮 Multi-Game Dedicated Monitor Bot (Discord Python Bot)**

This Discord bot is designed to provide real-time status, administration, and automated maintenance for multiple dedicated game servers using **RCON (Remote Console)**. It currently supports **Minecraft (MC)**, **Palworld (PAL)**, and **ARK: Survival Ascended (ASA)**.

The bot utilizes asynchronous RCON connections (python-rcon and discord.py) to manage game state, enforce bans, and perform critical actions like auto-saving.

## **✨ Features**

* **Multi-Game Support:** Simultaneously monitor and manage Minecraft, Palworld, and ARK: ASA servers.  
* **Auto-Saving:** Automatically runs save commands for Palworld and ASA on configurable intervals.  
* **Server Status:** Check server online/offline status and RCON connectivity.  
* **Player Listing:** Get a real-time list of connected players.  
* **Powerful Admin Commands:**  
  * **Raw RCON Execution (\!rcon\_raw):** Send any arbitrary RCON command directly to any game server.  
  * **Player Management:** Kick, ban, and unban players across all supported games.  
  * **Minecraft Whitelisting:** Easily add or remove players from the Minecraft whitelist.  
* **Role/Permission Control:** All administrative commands are restricted to users with the **Administrator** role and must be run in a designated admin channel.

## **🛠️ Setup and Installation**

### **1\. Prerequisites**

You must have **Python 3.8+** installed. You will also need RCON enabled on all your dedicated servers.

### **2\. Download and Dependencies**

Clone this repository or download the files. Then, run the setup script:

\# Install required Python libraries  
pip install \-r requirements.txt

### **3\. Configuration (.env file)**

The bot uses a .env file to store all sensitive configuration details. Make sure to create this file and edit it with your specific details:

\# \--- Environment Variables for Multi-Game\_Dedicated\_Monitor\_Bot.py \---

\# 1\. DISCORD CONFIGURATION (MANDATORY)  
DISCORD\_TOKEN="YOUR\_DISCORD\_BOT\_TOKEN\_HERE"  
ADMIN\_CHANNEL\_ID=000000000000000000  \# Channel where ALL RCON commands are allowed  
MC\_CHANNEL\_ID=000000000000000000     \# Channel for Minecraft status/logs  
PAL\_CHANNEL\_ID=000000000000000000     \# Channel for Palworld status/auto-save logs  
ASA\_CHANNEL\_ID=000000000000000000     \# Channel for ARK: ASA status/auto-save logs

\# 2\. MINECRAFT RCON CONFIGURATION  
MC\_RCON\_HOST="127.0.0.1"  
MC\_RCON\_PORT=25575  
MC\_RCON\_PASSWORD="YOUR\_MC\_RCON\_PASSWORD\_HERE"

\# 3\. PALWORLD RCON CONFIGURATION  
PAL\_RCON\_HOST="127.0.0.1"  
PAL\_RCON\_PORT=25576  
PAL\_RCON\_PASSWORD="YOUR\_PAL\_RCON\_PASSWORD\_HERE"  
PAL\_SAVE\_INTERVAL=30 \# Auto-save interval in minutes

\# 4\. ASA RCON CONFIGURATION  
ASA\_RCON\_HOST="127.0.0.1"  
ASA\_RCON\_PORT=27020  
ASA\_RCON\_PASSWORD="YOUR\_ASA\_RCON\_PASSWORD\_HERE"  
ASA\_SAVE\_INTERVAL=60 \# Auto-save interval in minutes

### **4\. Running the Bot**

Start the bot using the main script:

python Multi-Game\_Dedicated\_Monitor\_Bot.py

## **💻 Command Reference**

The bot uses the prefix \! for all commands.

| Command | Usage | Description | Requires Admin? | Games Supported |
| :---- | :---- | :---- | :---- | :---- |
| \!help | \!help | Displays this command list. | No | All |
| \!status | \!status \<game\> | Checks if the server is online and RCON is responsive. | No | All |
| \!players | \!players \<game\> | Lists all connected players. | No | All |
| \!save | \!save \<game\> | Forces the server to perform a manual save. | Yes | All |
| \!broadcast | \!broadcast \<game\> \<message\> | Sends a message to all players in-game. | Yes | All |
| **\!rcon\_raw** | **\!rcon\_raw \<game\> \<command\>** | **Sends a custom, raw RCON command.** | Yes | All |
| \!kick | \!kick \<game\> \<ID/Name\> | Kicks a player from the server. | Yes | All |
| \!ban | \!ban \<game\> \<ID/Name\> | Permanently bans a player from the server. | Yes | All |
| **\!unban\_mc** | **\!unban\_mc \<player\_name\>** | **Unbans a player from Minecraft.** | Yes | MC |
| **\!unban\_pal** | **\!unban\_pal \<steam\_id\>** | **Unbans a player from Palworld.** | Yes | PAL |
| **\!unban\_asa** | **\!unban\_asa \<steam\_id/ID\>** | **Unbans a player from ARK: ASA.** | Yes | ASA |
| **\!mc\_whitelist** | **\!mc\_whitelist \<player\_name\>** | **Adds a player to the MC whitelist.** | Yes | MC |
| **\!mc\_unwhitelist** | **\!mc\_unwhitelist \<player\_name\>** | **Removes a player from the MC whitelist.** | Yes | MC |

*(Game identifiers: mc, pal, asa)*