from discord.ext import commands

from db import message_db
from utils.logging import get_logger

logger = get_logger("utility")


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
**Bot Commands:**

`/chat <message>` - Chat with the AI (uses Google Search for up-to-date info)
`/ai_status` - Check if the AI is working
`/search_messages <query>` - Search for similar messages in server history

**Message Rotation:**

`/add_message <content> | <thread title>` - Add a message to the leetcode rotation
`/list_messages` - List messages in rotation
`/remove_message <index>` - Remove a message by index
`/rotation_status` - Show rotation status

**Utility:**

`/ping` - Check if bot is responsive
`/greet_user [username]` - Greet a user
`/reset_index [yes]` - Reset the message index (requires confirmation)
`/index_stats` - Show indexing statistics

**Auto-Features:**
- Messages are automatically indexed for context retrieval
- When joining a server, the bot indexes up to 1000 recent messages
"""
    await ctx.send(help_text)

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
    logger.info(f"🗑️  Resetting index for guild {guild_id}")

    await ctx.send("🔄 Resetting index for this server...")

    deleted_count = await message_db.reset_database(guild_id=guild_id)

    logger.info(f"🗑️  Deleted {deleted_count} messages from guild {guild_id}")
    await ctx.send(
      f"✅ Database reset complete!\n"
      f"🗑️  Deleted {deleted_count} messages\n"
      f"💡 New messages will be indexed automatically"
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

  @bot.command()
  async def force_leetcode(ctx):
    """Manually triggers the LeetCode daily post (Admin only)."""
    # Simple check for admin permissions or specific user
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You need administrator permissions to use this command.")
        return

    await ctx.send("⏳ Fetching LeetCode daily question...")
    
    # Import here to avoid circular dependencies if any
    from services.scheduled_tasks import get_leetcode_service
    leetcode_service = get_leetcode_service()
    
    question = await leetcode_service.fetch_daily_question()
    if not question:
        await ctx.send("❌ Failed to fetch daily question. Check logs.")
        return
        
    embed = leetcode_service.create_daily_embed(question)
    message = await ctx.send(embed=embed)
    
    # Create thread
    question_title = question.get("question", {}).get("title", "Daily Question")
    await message.create_thread(name=f"🧵 {question_title}", auto_archive_duration=1440)
