import discord
from discord.ext import commands

from services.ai_service import get_ai_service
from services.context_grabber import get_context_grabber
from utils.discord_helpers import get_guild_id, send_long_message
from utils.logging import get_logger

logger = get_logger("commands")


def setup_ai_commands(bot: commands.Bot):
  ai_service = get_ai_service()
  context_grabber = get_context_grabber()

  @bot.command()
  async def chat(ctx, *, message: str):
    """Main AI chat command with Google Search grounding and server context."""
    if not message:
      await ctx.send("Please provide a message to chat with the AI!")
      return

    if not ctx.guild:
      await ctx.send("This command can only be used in a server.")
      return

    logger.info(f"💬 Chat from {ctx.author.display_name}: {message[:50]}...")

    messages_per_channel = 20
    max_total_messages = 100

    system_msg = (
      "You are a chill, helpful bot in a Discord server. "
      "Keep responses SHORT and conversational - like texting a friend. "
      "Don't lecture, don't give unsolicited advice, don't be preachy. "
      "Just answer what's asked. Use casual language. "
      "Only use Google Search results when the question actually needs current info. "
      "The chat history is just for context - don't summarize it or reference it explicitly."
    )

    async with ctx.typing():
      context_messages = []

      # Gather messages from all text channels in the guild
      for channel in ctx.guild.text_channels:
        try:
          if not channel.permissions_for(ctx.guild.me).read_message_history:
            continue

          async for ctx_msg in channel.history(limit=messages_per_channel):
            if ctx_msg.author.bot:
              continue
            context_messages.append({
              "timestamp": ctx_msg.created_at,
              "channel": channel.name,
              "author": ctx_msg.author.display_name,
              "content": ctx_msg.content,
            })

        except discord.Forbidden:
          continue

      # Sort by timestamp and take the most recent
      context_messages.sort(key=lambda x: x["timestamp"])
      context_messages = context_messages[-max_total_messages:]

      # Format for the prompt
      chat_history = "\n".join(
        f"[#{m['channel']}] {m['author']}: {m['content']}"
        for m in context_messages
      )

      guild_id = get_guild_id(ctx)
      server_context = await context_grabber.get_relevant_context(
        message, guild_id=guild_id
      )

      prompt = (
        f"Here is the recent message history from across the server:\n\n"
        f"--- CHAT HISTORY ---\n"
        f"{chat_history}\n"
        f"--- END HISTORY ---\n\n"
      )

      if server_context:
        prompt += f"{server_context}\n\n"

      prompt += f"User message to respond to: {message}"

      response = await ai_service.call_gemini_ai(
        prompt, system_message=system_msg, use_search=True
      )

    logger.info(f"💬 Response sent to {ctx.author.display_name}")
    await send_long_message(ctx, response)

  @bot.command()
  async def ai_status(ctx):
    """Check if the AI is working."""
    logger.info(f"🔧 Status check from {ctx.author.display_name}")
    async with ctx.typing():
      test_response = await ai_service.call_gemini_ai(
        "Hello, respond with 'Gemini AI is working correctly!'",
        use_search=False,
      )

    if "Error" in test_response:
      await ctx.send(f"❌ GEMINI API Error: {test_response}")
    else:
      await ctx.send(f"✅ GEMINI API is working! Response: {test_response}")

  @bot.command()
  async def search_messages(ctx, *, query: str):
    """Search for similar messages in the server's indexed history."""
    if not query:
      await ctx.send("Please provide a search query!")
      return

    logger.info(f"� Search from {ctx.author.display_name}: {query[:50]}...")

    async with ctx.typing():
      from services.search_service import get_search_service

      search_service = get_search_service()

      guild_id = get_guild_id(ctx)
      results = await search_service.search_messages(query, guild_id=guild_id)

    if not results:
      await ctx.send(f"No similar messages found for: {query}")
      return

    response_lines = [f"Found {len(results)} similar messages:"]
    for i, (url, content, score) in enumerate(results, 1):
      score_percent = score * 100
      preview = content[:80] + "..." if len(content) > 80 else content
      response_lines.append(f"{i}. {preview} ({score_percent:.1f}%)\n   {url}")

    response = "\n".join(response_lines)
    await send_long_message(ctx, response)
