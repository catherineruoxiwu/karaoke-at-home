import os
from threading import Lock

# Directory paths
SONG_DIR = "downloads"
SEPARATED_DIR = "separated"
PROCESSED_DIR = "processed"

# Ensure directories exist
os.makedirs(SONG_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Cancellation state
cancelled_song_ids = set()
cancelled_lock = Lock()

# DB URL
DATABASE_URL = "sqlite:///songs.db"
