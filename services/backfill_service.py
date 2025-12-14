import asyncio
from typing import Optional

import discord

from services.message_indexer import get_message_indexer


class BackfillService:
  def __init__(self):
    self.indexer = get_message_indexer()

  async def backfill_guild(
    self, guild: discord.Guild, limit_per_channel: Optional[int] = None
  ) -> dict:
    total_indexed = 0
    total_skipped = 0
    channels_processed = 0

    print(f"🔄 Starting backfill for guild: {guild.name}")

    for channel in guild.text_channels:
      try:
        if not channel.permissions_for(guild.me).read_message_history:
          print(f"⏭️  Skipping channel #{channel.name} (no read permissions)")
          continue

        print(f"📂 Processing channel: #{channel.name}")

        channel_indexed = 0
        channel_skipped = 0

        async for message in channel.history(limit=limit_per_channel):
          if message.author.bot:
            continue

          if not message.content or not message.content.strip():
            continue

          if message.content.startswith("/"):
            continue

          queued = await self.indexer.queue_message(message)
          if queued:
            channel_indexed += 1
          else:
            channel_skipped += 1

        total_indexed += channel_indexed
        total_skipped += channel_skipped
        channels_processed += 1

        print(
          f"✅ Channel #{channel.name}: {channel_indexed} queued, {channel_skipped} skipped"
        )

        await asyncio.sleep(0.5)

      except discord.Forbidden:
        print(f"⏭️  Skipping channel #{channel.name} (forbidden)")
        continue
      except Exception as e:
        print(f"❌ Error processing channel #{channel.name}: {e}")
        continue

    print(
      f"🎉 Backfill complete: {total_indexed} messages queued, {total_skipped} skipped across {channels_processed} channels"
    )

    return {
      "total_indexed": total_indexed,
      "total_skipped": total_skipped,
      "channels_processed": channels_processed,
    }


_backfill_service: Optional[BackfillService] = None


def get_backfill_service() -> BackfillService:
  global _backfill_service
  if _backfill_service is None:
    _backfill_service = BackfillService()
  return _backfill_service

