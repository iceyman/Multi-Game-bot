# **⚙️ Palworld Discord Bot Setup and Installation**

This guide explains how to install dependencies, configure environment variables, and run the palworld\_bot.py script.

## **1\. Prerequisites**

You must have the following installed on your system:

* **Python 3.8+**  
* **pip** (Python package installer)

### **1.1. Install Python Libraries**

The bot requires the discord.py library and the **asynchronous RCON client** to communicate with the Palworld server.

pip install discord.py python-rcon

### **1.2. Configure Palworld Server RCON**

Ensure RCON is enabled and configured in your Palworld server's PalWorldSettings.ini (or equivalent configuration file). You will need the **RCON Port** and **RCON Password**.

## **2\. Configuration Secrets (Easiest Method)**

The fastest way to configure the bot is by editing the **CONFIGURATION** block directly at the top of the palworld\_bot.py file.

1. Open palworld\_bot.py.  
2. Replace the placeholder values (YOUR\_DISCORD\_BOT\_TOKEN\_HERE, YOUR\_CHANNEL\_ID\_HERE, etc.) with your actual credentials.

| Variable | Description | Where to Get It | Example Value |  
| DISCORD\_TOKEN | The unique token for your Discord bot application. | Discord Developer Portal | MzY4ODYwMTIyMTExNTY2NDAw.GjB4Wd.3\_j4X8hY... |  
| TARGET\_CHANNEL\_ID | The ID of the Discord channel where messages (joins/leaves/chat) will be posted. | Discord (Enable Developer Mode, right-click channel, "Copy ID") | 123456789012345678 |  
| RCON\_HOST | The IP address or hostname of your Palworld server. | Your server's public IP or domain. | 192.168.1.10 or my.palworldserver.com |  
| RCON\_PORT | The RCON port configured in your Palworld server settings (default is 25575). | Palworld server settings | 25575 |  
| RCON\_PASSWORD | The password set in your Palworld server settings for RCON access. | Palworld server settings | MySuperSecretRCONPass |

### **2.1. Secure Method (Using Environment Variables)**

For security, especially when hosting the bot publicly or on a shared server, **Environment Variables** are the recommended approach. The bot will automatically prioritize these if they are set, ignoring the hardcoded placeholders in the script.

export DISCORD\_TOKEN="YOUR\_ACTUAL\_BOT\_TOKEN"  
export TARGET\_CHANNEL\_ID="YOUR\_ACTUAL\_CHANNEL\_ID"  
export RCON\_HOST="YOUR\_SERVER\_IP\_OR\_HOSTNAME"  
export RCON\_PORT="YOUR\_RCON\_PORT"  
export RCON\_PASSWORD="YOUR\_RCON\_PASSWORD"

## **3\. Running the Bot**

If you used the **Secure Method**, export the variables in your terminal first. If you used the **Easiest Method**, you can skip this step.

### **3.1. Execute the Bot Script**

Run the Python file:

python palworld\_bot.py

## **4\. Final Verification**

The palworld\_bot.py script now contains a fully functional RCON implementation using the python-rcon library.

**Before closing the project:**

* Ensure the configuration variables in Section 2 are correctly set.  
* Make sure you have run the installation command: pip install discord.py python-rcon.  
* Verify that your server's RCON is enabled and accessible (often port 25575).

## **5\. Bot Commands (Server Admin)**

The bot includes commands that can be used directly in Discord. **All maintenance commands require Discord Administrator permissions.**

### **\!status**

Usage: \!status  
Description: Shows the current player count and lists the names of all players currently online (using the RCON ShowPlayers command).

### **\!broadcast**

Usage: \!broadcast \[message\]  
Description: Sends a message to all players in the game using RCON Broadcast.  
\!broadcast Server is restarting in 5 minutes for maintenance\!

### **\!save**

Usage: \!save  
Description: Forces the Palworld server to immediately save the world state. Use this before running updates or performing manual shutdowns to prevent data loss.

### **\!shutdown**

Usage: \!shutdown \[delay\_seconds\] \[message\]  
Description: Executes a graceful shutdown of the server. It first sends a warning broadcast to all players, waits for the specified delay (default is 10 seconds), and then executes the DoExit RCON command.  
**Examples:**

* \!shutdown (Shuts down in 10 seconds with default message)  
* \!shutdown 60 Final restart of the night, see you tomorrow\!