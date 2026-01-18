import asyncio
from typing import Optional

import discord

from config import AUTO_INDEX_LIMIT
from db import message_db
from services.message_indexer import get_message_indexer
from utils.logging import get_logger

logger = get_logger("auto_index")


class AutoIndexService:
  """Automatically indexes messages when bot joins a new guild."""

  def __init__(self):
    self.indexer = get_message_indexer()

  async def should_auto_index(self, guild_id: str) -> bool:
    """Check if guild has no indexed messages."""
    count = await message_db.get_message_count(guild_id=guild_id)
    return count == 0

  async def auto_index_guild(self, guild: discord.Guild) -> dict:
    """Index messages for a guild in the background."""
    guild_id = str(guild.id)

    if not await self.should_auto_index(guild_id):
      logger.info(f"Guild {guild.name} already indexed, skipping")
      return {"status": "skipped", "reason": "already_indexed"}

    logger.info(f"🔄 Starting auto-index for: {guild.name}")

    total_queued = 0
    total_skipped = 0
    channels_processed = 0
    messages_remaining = AUTO_INDEX_LIMIT

    for channel in guild.text_channels:
      if messages_remaining <= 0:
        break

      try:
        if not channel.permissions_for(guild.me).read_message_history:
          logger.debug(f"Skipping #{channel.name} (no permissions)")
          continue

        channel_queued = 0

        async for message in channel.history(limit=min(100, messages_remaining)):
          if message.author.bot:
            continue

          if not message.content or not message.content.strip():
            continue

          if message.content.startswith("/"):
            continue

          queued = await self.indexer.queue_message(message)
          if queued:
            channel_queued += 1
            messages_remaining -= 1
          else:
            total_skipped += 1

          if messages_remaining <= 0:
            break

        total_queued += channel_queued
        channels_processed += 1
        logger.info(f"  📂 #{channel.name}: {channel_queued} messages queued")

        await asyncio.sleep(0.3)

      except discord.Forbidden:
        logger.debug(f"Skipping #{channel.name} (forbidden)")
        continue
      except Exception as e:
        logger.error(f"Error in #{channel.name}: {e}")
        continue

    logger.info(
      f"✅ Auto-index complete: {total_queued} queued, "
      f"{total_skipped} skipped, {channels_processed} channels"
    )

    return {
      "status": "completed",
      "total_queued": total_queued,
      "total_skipped": total_skipped,
      "channels_processed": channels_processed,
    }


_auto_index_service: Optional[AutoIndexService] = None


def get_auto_index_service() -> AutoIndexService:
  global _auto_index_service
  if _auto_index_service is None:
    _auto_index_service = AutoIndexService()
  return _auto_index_service
