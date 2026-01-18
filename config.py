import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3-flash-preview"

DB_PATH = "data/messages.db"

INDEXING_BATCH_SIZE = 10
INDEXING_QUEUE_MAX_SIZE = 1000
EMBEDDING_BATCH_SIZE = 50

# Auto-indexing on guild join
AUTO_INDEX_LIMIT = 1000  # Total messages to index when joining a new server

DEFAULT_SEARCH_LIMIT = 10
DEFAULT_CONTEXT_LIMIT = 5

EMBEDDING_MODEL = "gemini-embedding-001"
