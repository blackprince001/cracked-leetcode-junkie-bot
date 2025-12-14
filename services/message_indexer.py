import asyncio
import hashlib
from typing import Optional

import discord

from config import INDEXING_BATCH_SIZE, INDEXING_QUEUE_MAX_SIZE
from db import message_db
from services.embedding_service import get_embedding_service


class MessageIndexer:
  def __init__(self):
    self.queue: asyncio.Queue = asyncio.Queue(maxsize=INDEXING_QUEUE_MAX_SIZE)
    self.worker_task: Optional[asyncio.Task] = None
    self.running = False
    self.embedding_service = get_embedding_service()

  def start(self):
    if not self.running:
      self.running = True
      self.worker_task = asyncio.create_task(self._worker())

  def stop(self):
    self.running = False
    if self.worker_task:
      self.worker_task.cancel()

  async def queue_message(self, message: discord.Message):
    try:
      self.queue.put_nowait(message)
      return True
    except asyncio.QueueFull:
      print(f"Warning: Indexing queue is full, dropping message {message.id}")
      return False

  def _calculate_hash(self, content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

  def _create_message_url(self, message: discord.Message) -> str:
    return f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"

  async def _worker(self):
    batch = []

    while self.running:
      try:
        try:
          message = await asyncio.wait_for(self.queue.get(), timeout=1.0)
          batch.append(message)
        except asyncio.TimeoutError:
          if batch:
            await self._process_batch(batch)
            batch = []
          continue

        if len(batch) >= INDEXING_BATCH_SIZE:
          await self._process_batch(batch)
          batch = []

      except asyncio.CancelledError:
        if batch:
          await self._process_batch(batch)
        break
      except Exception as e:
        print(f"Error in indexer worker: {e}")

    if batch:
      await self._process_batch(batch)

  async def _process_batch(self, batch: list):
    valid_messages = []
    message_data = []

    for msg in batch:
      if not msg.content or not msg.content.strip():
        continue

      content_hash = self._calculate_hash(msg.content)
      message_data.append(
        {
          "message": msg,
          "content_hash": content_hash,
          "message_url": self._create_message_url(msg),
        }
      )
      valid_messages.append(msg)

    if not valid_messages:
      return

    content_hashes = [data["content_hash"] for data in message_data]
    existing_hashes = await message_db.get_existing_hashes(content_hashes)

    to_index = []
    for data in message_data:
      if data["content_hash"] in existing_hashes:
        print(
          f"⏭️  Skipping duplicate message {data['message'].id} from {data['message'].author.display_name}"
        )
      else:
        to_index.append(data)

    if not to_index:
      return

    print(f"📝 Batch indexing {len(to_index)} messages")

    texts = [data["message"].content for data in to_index]
    embeddings = await self.embedding_service.generate_embeddings_batch(texts)

    for data, embedding in zip(to_index, embeddings):
      try:
        msg = data["message"]
        embedding_bytes = None
        if embedding is not None:
          embedding_bytes = self.embedding_service.embedding_to_bytes(embedding)

        inserted = await message_db.insert_message(
          message_id=str(msg.id),
          channel_id=str(msg.channel.id),
          guild_id=str(msg.guild.id) if msg.guild else "DM",
          author_id=str(msg.author.id),
          content=msg.content,
          content_hash=data["content_hash"],
          embedding=embedding_bytes,
          message_url=data["message_url"],
        )

        if inserted:
          print(
            f"✅ Indexed message {msg.id} from {msg.author.display_name} in #{msg.channel.name}"
          )
        else:
          print(f"⚠️  Failed to insert message {msg.id} (duplicate or error)")

      except Exception as e:
        print(f"❌ Error processing message {data['message'].id}: {e}")


_message_indexer: Optional[MessageIndexer] = None


def get_message_indexer() -> MessageIndexer:
  global _message_indexer
  if _message_indexer is None:
    _message_indexer = MessageIndexer()
  return _message_indexer
