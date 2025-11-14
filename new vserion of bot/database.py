# --- NEW FILE: database.py ---
# This file manages the bot's memory (database).
import sqlite3
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger('database')

DB_NAME = "bot_database.db"

def init_db(db_name: str = DB_NAME):
    """Initializes the database and creates tables if they don't exist."""
    global DB_NAME
    DB_NAME = db_name
    
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        # User table to link Discord to in-game accounts
        # Making in_game_name UNIQUE is crucial for lookups
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id TEXT PRIMARY KEY,
                in_game_name TEXT UNIQUE,
                points INTEGER DEFAULT 0
            )
        """)
        # We can add more tables later, e.g., for transaction logs
        con.commit()
    logger.info(f"Database '{DB_NAME}' initialized successfully.")

def get_db_connection():
    """Helper to get a database connection."""
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row # This lets us access columns by name
    return con

def link_user(discord_id: str, in_game_name: str) -> bool:
    """Links a Discord ID to an in-game name. Replaces any existing link."""
    try:
        with get_db_connection() as con:
            cur = con.cursor()
            
            # First, check if in_game_name is taken by *another* user
            cur.execute("SELECT discord_id FROM users WHERE in_game_name = ?", (in_game_name,))
            existing_ign = cur.fetchone()
            if existing_ign and existing_ign["discord_id"] != discord_id:
                logger.warning(f"In-game name '{in_game_name}' is already linked to another user.")
                return False # In-game name already taken

            # Second, check if the discord_id is already in the table
            cur.execute("SELECT points FROM users WHERE discord_id = ?", (discord_id,))
            existing_user = cur.fetchone()
            
            current_points = 0
            if existing_user:
                current_points = existing_user["points"]

            # Use INSERT OR REPLACE to handle the primary key (discord_id)
            # This will update the in_game_name and points for an existing user
            cur.execute("""
                INSERT OR REPLACE INTO users (discord_id, in_game_name, points)
                VALUES (?, ?, ?)
            """, (discord_id, in_game_name, current_points))
            
            # Clean up old entries just in case
            cur.execute("DELETE FROM users WHERE in_game_name = ? AND discord_id != ?",
                        (in_game_name, discord_id))
            
            con.commit()
            logger.info(f"Successfully linked Discord user {discord_id} to {in_game_name}.")
            return True
    except sqlite3.IntegrityError:
         logger.warning(f"In-game name '{in_game_name}' is already linked to another user (IntegrityError).")
         return False # UNIQUE constraint failed
    except sqlite3.Error as e:
        logger.error(f"Database error in link_user: {e}")
        return False

def unlink_user(discord_id: str):
    """Removes the in-game name link from a Discord user."""
    try:
        with get_db_connection() as con:
            # We don't delete the user, just their link, so they keep their points
            con.execute("UPDATE users SET in_game_name = NULL WHERE discord_id = ?", (discord_id,))
            con.commit()
            logger.info(f"Unlinked Discord user {discord_id}.")
    except sqlite3.Error as e:
        logger.error(f"Database error in unlink_user: {e}")

def get_user_by_discord_id(discord_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a user's data by their Discord ID."""
    try:
        with get_db_connection() as con:
            cur = con.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
            user = cur.fetchone()
            return dict(user) if user else None
    except sqlite3.Error as e:
        logger.error(f"Database error in get_user_by_discord_id: {e}")
        return None

def get_user_by_in_game_name(in_game_name: str) -> Optional[Dict[str, Any]]:
    """Fetches a user's data by their in-game name."""
    try:
        with get_db_connection() as con:
            cur = con.execute("SELECT * FROM users WHERE in_game_name = ?", (in_game_name,))
            user = cur.fetchone()
            return dict(user) if user else None
    except sqlite3.Error as e:
        logger.error(f"Database error in get_user_by_in_game_name: {e}")
        return None

def get_points(discord_id: str) -> int:
    """Gets a user's point balance."""
    user = get_user_by_discord_id(discord_id)
    return user['points'] if user else 0

def update_points(discord_id: str, amount: int) -> int:
    """
    Adds or removes points for a user.
    Creates the user if they don't exist.
    Returns the new point balance.
    """
    try:
        with get_db_connection() as con:
            # Ensure user exists
            con.execute("INSERT OR IGNORE INTO users (discord_id, points) VALUES (?, 0)", (discord_id,))
            
            # Update points
            con.execute("UPDATE users SET points = points + ? WHERE discord_id = ?", (amount, discord_id,))
            
            # Get new balance
            cur = con.execute("SELECT points FROM users WHERE discord_id = ?", (discord_id,))
            new_balance = cur.fetchone()['points']
            
            con.commit()
            logger.info(f"Updated points for {discord_id} by {amount}. New balance: {new_balance}")
            return new_balance
    except sqlite3.Error as e:
        logger.error(f"Database error in update_points: {e}")
        return -1 # Indicate an error