# cache.py
import os
import sqlite3
from pathlib import Path

# Set up paths and constants
CACHE_DB_PATH = Path.home() / ".media_rotation_cache.db"


def initialize_cache_db():
    """Initializes the SQLite cache if it doesn't already exist."""
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS imported_media (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL CHECK(type IN ('movie', 'show')),
        title TEXT,
        list_name TEXT,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


def add_to_cache(item_id, media_type, title, list_name):
    """Adds a media item to the cache."""
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR IGNORE INTO imported_media (id, type, title, list_name)
    VALUES (?, ?, ?, ?)
    """,
        (item_id, media_type, title, list_name),
    )
    conn.commit()
    conn.close()


def is_in_cache(item_id):
    """Checks if an item is already in the cache."""
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM imported_media WHERE id = ?", (item_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def remove_from_cache(item_id):
    """Removes an item from the cache."""
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM imported_media WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def get_oldest_entry(media_type):
    """Returns the oldest imported item for the given media type."""
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT id, title FROM imported_media
    WHERE type = ?
    ORDER BY imported_at ASC LIMIT 1
    """,
        (media_type,),
    )
    result = cursor.fetchone()
    conn.close()
    return result


# Initialize cache and show location
initialize_cache_db()
CACHE_DB_PATH
