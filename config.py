import os
from datetime import time

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TIMEZONE = "UTC"
LEETCODE_SCHEDULE_TIME = time(hour=5, minute=00)
GM_SCHEDULE_TIME = time(hour=0, minute=00)

DB_PATH = "data/messages.db"

INDEXING_BATCH_SIZE = 10
INDEXING_QUEUE_MAX_SIZE = 1000
EMBEDDING_BATCH_SIZE = 50

DEFAULT_SEARCH_LIMIT = 10
DEFAULT_CONTEXT_LIMIT = 5

EMBEDDING_MODEL = "gemini-embedding-001"
