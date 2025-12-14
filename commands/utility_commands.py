from discord.ext import commands

from db import message_db
from services.backfill_service import get_backfill_service
from services.update_embeddings_service import get_update_embeddings_service


def setup_utility_commands(bot: commands.Bot):
  @bot.command()
  async def ping(ctx):
    await ctx.send("pong")

  @bot.command()
  async def greet_user(ctx, user: str = "everyone"):
    await ctx.send(f"@{user}, greetings!")

  @bot.command()
  async def ai_help(ctx):
    help_text = """
**Bot AI Commands:**

`/ask <question>` - Ask any question to the AI  
`/chat <message>` - Have a casual conversation with the AI  
`/explain <topic>` - Get an explanation of a topic  
`/code_help <question>` - Get help with coding questions  
`/think <problem>` - Ask AI to think step-by-step about a problem  
`/ai_status` - Check if the Gemini API is working  
`/summarize [channel|guild] [message_limit=50]` - Generate a summary of recent activity in the channel or guild
`/search_messages <query>` - Search for similar messages in the server

**Normal Bot / Utility Commands:**

`/add_message <content> | <thread title>` - Add a message to the leetcode rotation (use `|` to separate content and thread title)  
`/list_messages` - List messages currently in the rotation  
`/remove_message <index>` - Remove a message from the rotation by 1-based index  
`/rotation_status` - Show current rotation index and total messages  
`/ping` - Responds with 'pong'  
`/greet_user [username]` - Greet a user (defaults to 'everyone')
`/backfill_messages [limit=100]` - Index historical messages from the server (admin recommended)
`/update_embeddings [limit=100]` - Update embeddings for messages that don't have them yet
`/reset_index [yes]` - Reset the message index for this server (requires confirmation)
`/index_stats` - Show statistics about indexed messages

**Scheduled Behavior:**
- Daily leetcode question(s) posted to the `dsa` channel at configured time (uses messages.json rotation).  
- Daily "gm" message posted to the `gm` channel at configured time.

**Examples:**
`/ask What is the capital of France?`  
`/chat Hello, how are you today?`  
`/explain machine learning`  
`/code_help How do I create a list in Python?`  
`/think How do I solve 2x + 5 = 15?`  
`/add_message Reverse a linked list | Linked List - Reverse`  
`/list_messages`  
`/remove_message 3`
`/search_messages python tutorial`

If you need help with a specific command, mention it and I'll show usage.
"""
    await ctx.send(help_text)

  @bot.command()
  async def backfill_messages(ctx, limit_per_channel: int = 100):
    if not ctx.guild:
      await ctx.send("This command can only be used in a server.")
      return

    if limit_per_channel < 1 or limit_per_channel > 10000:
      await ctx.send("Limit must be between 1 and 10000.")
      return

    await ctx.send(
      f"🔄 Starting backfill for this server (up to {limit_per_channel} messages per channel). This may take a while..."
    )

    backfill_service = get_backfill_service()
    result = await backfill_service.backfill_guild(ctx.guild, limit_per_channel)

    await ctx.send(
      f"✅ Backfill complete!\n"
      f"📊 {result['total_indexed']} messages queued for indexing\n"
      f"⏭️  {result['total_skipped']} messages skipped\n"
      f"📂 {result['channels_processed']} channels processed"
    )

  @bot.command()
  async def update_embeddings(ctx, limit: int = 100):
    if not ctx.guild:
      await ctx.send("This command can only be used in a server.")
      return

    if limit < 1 or limit > 1000:
      await ctx.send("Limit must be between 1 and 1000.")
      return

    await ctx.send(
      f"🔄 Starting embedding update for up to {limit} messages without embeddings. This may take a while..."
    )

    update_service = get_update_embeddings_service()
    guild_id = str(ctx.guild.id)
    result = await update_service.update_missing_embeddings(guild_id=guild_id, limit=limit)

    await ctx.send(
      f"✅ Embedding update complete!\n"
      f"📊 {result['updated']} embeddings updated\n"
      f"❌ {result['failed']} failed\n"
      f"📈 {result['total']} total processed"
    )

  @bot.command()
  async def reset_index(ctx, confirm: str = ""):
    if not ctx.guild:
      await ctx.send("This command can only be used in a server.")
      return

    if confirm != "yes":
      count = await message_db.get_message_count(guild_id=str(ctx.guild.id))
      await ctx.send(
        f"⚠️  **WARNING:** This will delete all {count} indexed messages for this server!\n"
        f"To confirm, run: `/reset_index yes`\n"
        f"This action cannot be undone!"
      )
      return

    guild_id = str(ctx.guild.id)
    count = await message_db.get_message_count(guild_id=guild_id)

    await ctx.send(f"🔄 Resetting index for this server...")

    deleted_count = await message_db.reset_database(guild_id=guild_id)

    await ctx.send(
      f"✅ Database reset complete!\n"
      f"🗑️  Deleted {deleted_count} messages\n"
      f"💡 You can now use `/backfill_messages` to re-index messages"
    )

  @bot.command()
  async def index_stats(ctx):
    if not ctx.guild:
      await ctx.send("This command can only be used in a server.")
      return

    guild_id = str(ctx.guild.id)
    total_count = await message_db.get_message_count(guild_id=guild_id)
    total_all = await message_db.get_message_count()

    await ctx.send(
      f"📊 **Index Statistics:**\n"
      f"📝 This server: {total_count} messages indexed\n"
      f"🌐 All servers: {total_all} messages indexed"
    )
