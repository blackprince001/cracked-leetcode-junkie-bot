from typing import Optional

from discord.ext import commands


async def send_long_message(
  ctx: commands.Context, text: str, max_length: int = 2000
) -> None:
  """Send a message, automatically chunking if it exceeds Discord's limit."""
  if len(text) > max_length:
    chunks = [text[i : i + max_length] for i in range(0, len(text), max_length)]
    for chunk in chunks:
      await ctx.send(chunk)
  else:
    await ctx.send(text)


def get_guild_id(ctx: commands.Context) -> Optional[str]:
  """Safely extract guild ID from context, returns None for DMs."""
  return str(ctx.guild.id) if ctx.guild else None
