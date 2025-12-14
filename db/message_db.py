from typing import List, Optional, Tuple

import aiosqlite
import numpy as np

from config import DB_PATH


async def init_db():
  import os

  db_dir = os.path.dirname(DB_PATH)
  if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

  schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
  async with aiosqlite.connect(DB_PATH) as db:
    with open(schema_path, "r") as f:
      schema = f.read()
    await db.executescript(schema)
    await db.commit()


async def insert_message(
  message_id: str,
  channel_id: str,
  guild_id: str,
  author_id: str,
  content: str,
  content_hash: str,
  embedding: Optional[bytes],
  message_url: str,
) -> bool:
  async with aiosqlite.connect(DB_PATH) as db:
    try:
      await db.execute(
        """
                INSERT INTO messages 
                (message_id, channel_id, guild_id, author_id, content, content_hash, embedding, message_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          message_id,
          channel_id,
          guild_id,
          author_id,
          content,
          content_hash,
          embedding,
          message_url,
        ),
      )
      await db.commit()
      return True
    except aiosqlite.IntegrityError:
      return False


async def get_message_by_hash(content_hash: str) -> Optional[dict]:
  async with aiosqlite.connect(DB_PATH) as db:
    db.row_factory = aiosqlite.Row
    async with db.execute(
      "SELECT * FROM messages WHERE content_hash = ?", (content_hash,)
    ) as cursor:
      row = await cursor.fetchone()
      if row:
        return dict(row)
      return None


async def get_existing_hashes(content_hashes: List[str]) -> set:
  if not content_hashes:
    return set()

  async with aiosqlite.connect(DB_PATH) as db:
    placeholders = ",".join("?" * len(content_hashes))
    async with db.execute(
      f"SELECT content_hash FROM messages WHERE content_hash IN ({placeholders})",
      content_hashes,
    ) as cursor:
      rows = await cursor.fetchall()
      return {row[0] for row in rows}


async def get_all_embeddings(
  guild_id: Optional[str] = None,
) -> List[Tuple[int, bytes, str]]:
  async with aiosqlite.connect(DB_PATH) as db:
    if guild_id:
      async with db.execute(
        "SELECT id, embedding, message_url FROM messages WHERE guild_id = ? AND embedding IS NOT NULL",
        (guild_id,),
      ) as cursor:
        rows = await cursor.fetchall()
    else:
      async with db.execute(
        "SELECT id, embedding, message_url FROM messages WHERE embedding IS NOT NULL"
      ) as cursor:
        rows = await cursor.fetchall()

    return [(row[0], row[1], row[2]) for row in rows]


async def search_similar_messages(
  query_embedding: np.ndarray, guild_id: Optional[str] = None, limit: int = 10
) -> List[Tuple[str, float]]:
  embeddings_data = await get_all_embeddings(guild_id)

  if not embeddings_data:
    return []

  similarities = []
  query_norm = np.linalg.norm(query_embedding)

  if query_norm == 0:
    return []

  for _, embedding_blob, message_url in embeddings_data:
    stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32)

    dot_product = np.dot(query_embedding, stored_embedding)
    stored_norm = np.linalg.norm(stored_embedding)

    if stored_norm == 0:
      continue

    similarity = dot_product / (query_norm * stored_norm)
    similarities.append((message_url, float(similarity)))

  similarities.sort(key=lambda x: x[1], reverse=True)
  return similarities[:limit]


async def get_message_urls(message_ids: List[int]) -> List[str]:
  if not message_ids:
    return []

  async with aiosqlite.connect(DB_PATH) as db:
    placeholders = ",".join("?" * len(message_ids))
    async with db.execute(
      f"SELECT message_url FROM messages WHERE id IN ({placeholders})",
      message_ids,
    ) as cursor:
      rows = await cursor.fetchall()
      return [row[0] for row in rows]


async def reset_database(guild_id: Optional[str] = None) -> int:
  async with aiosqlite.connect(DB_PATH) as db:
    if guild_id:
      async with db.execute(
        "DELETE FROM messages WHERE guild_id = ?", (guild_id,)
      ) as cursor:
        await db.commit()
        return cursor.rowcount
    else:
      async with db.execute("DELETE FROM messages") as cursor:
        await db.commit()
        return cursor.rowcount


async def get_message_count(guild_id: Optional[str] = None) -> int:
  async with aiosqlite.connect(DB_PATH) as db:
    if guild_id:
      async with db.execute(
        "SELECT COUNT(*) FROM messages WHERE guild_id = ?", (guild_id,)
      ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0
    else:
      async with db.execute("SELECT COUNT(*) FROM messages") as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_messages_without_embeddings(
  guild_id: Optional[str] = None, limit: Optional[int] = None
) -> List[dict]:
  async with aiosqlite.connect(DB_PATH) as db:
    db.row_factory = aiosqlite.Row
    query = "SELECT id, message_id, content FROM messages WHERE embedding IS NULL"
    params = []
    
    if guild_id:
      query += " AND guild_id = ?"
      params.append(guild_id)
    
    query += " ORDER BY created_at DESC"
    
    if limit:
      query += " LIMIT ?"
      params.append(limit)
    
    async with db.execute(query, params) as cursor:
      rows = await cursor.fetchall()
      return [dict(row) for row in rows]


async def update_message_embedding(message_id: str, embedding: bytes) -> bool:
  async with aiosqlite.connect(DB_PATH) as db:
    try:
      await db.execute(
        "UPDATE messages SET embedding = ? WHERE message_id = ?",
        (embedding, message_id),
      )
      await db.commit()
      return True
    except Exception as e:
      print(f"Error updating embedding for message {message_id}: {e}")
      return False
