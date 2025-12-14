import asyncio
from typing import Optional

from db import message_db
from services.embedding_service import get_embedding_service


class UpdateEmbeddingsService:
  def __init__(self):
    self.embedding_service = get_embedding_service()

  async def update_missing_embeddings(
    self, guild_id: Optional[str] = None, limit: Optional[int] = None, batch_size: int = 50
  ):
    from config import EMBEDDING_BATCH_SIZE

    messages = await message_db.get_messages_without_embeddings(guild_id, limit)
    
    if not messages:
      print("No messages found without embeddings.")
      return {"updated": 0, "failed": 0, "total": 0}

    total = len(messages)
    updated = 0
    failed = 0

    print(f"🔄 Found {total} messages without embeddings. Starting batch update...")

    for i in range(0, total, batch_size):
      batch = messages[i : i + batch_size]
      
      texts = [msg["content"] for msg in batch]
      embeddings = await self.embedding_service.generate_embeddings_batch(texts)
      
      for msg, embedding in zip(batch, embeddings):
        try:
          message_id = msg["message_id"]
          
          if embedding is None:
            print(f"⚠️  Failed to generate embedding for message {message_id}")
            failed += 1
            continue
          
          embedding_bytes = self.embedding_service.embedding_to_bytes(embedding)
          success = await message_db.update_message_embedding(message_id, embedding_bytes)
          
          if success:
            updated += 1
          else:
            failed += 1
        except Exception as e:
          failed += 1
          print(f"❌ Error updating message {msg.get('message_id', 'unknown')}: {e}")
      
      print(f"📊 Progress: {min(i + batch_size, total)}/{total} processed ({updated} updated, {failed} failed)")
      
      if i + batch_size < total:
        await asyncio.sleep(0.5)

    print(f"✅ Update complete: {updated} updated, {failed} failed out of {total} total")
    
    return {"updated": updated, "failed": failed, "total": total}


_update_embeddings_service: Optional[UpdateEmbeddingsService] = None


def get_update_embeddings_service() -> UpdateEmbeddingsService:
  global _update_embeddings_service
  if _update_embeddings_service is None:
    _update_embeddings_service = UpdateEmbeddingsService()
  return _update_embeddings_service

