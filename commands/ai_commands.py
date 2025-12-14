import discord
from discord.ext import commands

from services.ai_service import get_ai_service
from services.context_grabber import get_context_grabber


def setup_ai_commands(bot: commands.Bot):
  ai_service = get_ai_service()
  context_grabber = get_context_grabber()

  @bot.command()
  async def ask(ctx, *, question: str):
    if not question:
      await ctx.send("Please provide a question to ask the AI!")
      return

    async with ctx.typing():
      guild_id = str(ctx.guild.id) if ctx.guild else None
      context = await context_grabber.get_relevant_context(question, guild_id=guild_id)

      response = await ai_service.call_gemini_ai(question, context=context)

    if len(response) > 2000:
      chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
      for chunk in chunks:
        await ctx.send(chunk)
    else:
      await ctx.send(response)

  @bot.command()
  async def chat(ctx, *, message: str):
    if not message:
      await ctx.send("Please provide a message to chat with the AI!")
      return

    context_limit = 100

    system_msg = (
      "You are a helpful and friendly AI assistant in a Discord chat. "
      "You will be given the recent message history from the channel. "
      "Your task is to respond *only* to the very last message in the history, "
      "using the previous messages as context to understand the flow of conversation. "
      "Respond naturally and conversationally."
    )

    async with ctx.typing():
      context_messages = []
      async for ctx_msg in ctx.channel.history(limit=context_limit):
        msg: str = f"{ctx_msg.author.display_name}: {ctx_msg.content}"
        context_messages.append(msg)

      context_messages.reverse()
      chat_history = "\n".join(context_messages)

      guild_id = str(ctx.guild.id) if ctx.guild else None
      server_context = await context_grabber.get_relevant_context(
        message, guild_id=guild_id
      )

      prompt = (
        f"Here is the recent message history from the channel:\n\n"
        f"--- CHAT HISTORY ---\n"
        f"{chat_history}\n"
        f"--- END HISTORY ---\n\n"
      )

      if server_context:
        prompt += f"{server_context}\n\n"

      prompt += "Please provide a natural, conversational response to the *last* message in this history."

      response = await ai_service.call_gemini_ai(prompt, system_message=system_msg)

    if len(response) > 2000:
      chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
      for chunk in chunks:
        await ctx.send(chunk)
    else:
      await ctx.send(response)

  @bot.command()
  async def explain(ctx, *, topic: str):
    if not topic:
      await ctx.send("Please provide a topic to explain!")
      return

    system_msg = "You are an expert educator. Explain topics clearly and concisely in a way that's easy to understand."
    prompt = f"Please explain {topic}:"

    async with ctx.typing():
      guild_id = str(ctx.guild.id) if ctx.guild else None
      context = await context_grabber.get_relevant_context(topic, guild_id=guild_id)

      response = await ai_service.call_gemini_ai(
        prompt, system_message=system_msg, context=context
      )

    if len(response) > 2000:
      chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
      for chunk in chunks:
        await ctx.send(chunk)
    else:
      await ctx.send(response)

  @bot.command()
  async def code_help(ctx, *, coding_question: str):
    if not coding_question:
      await ctx.send("Please provide a coding question!")
      return

    system_msg = "You are an expert programming assistant. Provide clear explanations and code examples when appropriate. Format code using markdown code blocks."

    async with ctx.typing():
      guild_id = str(ctx.guild.id) if ctx.guild else None
      context = await context_grabber.get_relevant_context(
        coding_question, guild_id=guild_id
      )

      response = await ai_service.call_gemini_ai(
        coding_question, system_message=system_msg, context=context
      )

    if len(response) > 2000:
      chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
      for chunk in chunks:
        await ctx.send(chunk)
    else:
      await ctx.send(response)

  @bot.command()
  async def ai_status(ctx):
    async with ctx.typing():
      test_response = await ai_service.call_gemini_ai(
        "Hello, this is a test message. Please respond with 'Gemini AI is working correctly!'"
      )

    if "Error" in test_response:
      await ctx.send(f"❌ GEMINI API Error: {test_response}")
    else:
      await ctx.send(f"✅ GEMINI API is working! Response: {test_response}")

  @bot.command()
  async def think(ctx, *, problem: str):
    if not problem:
      await ctx.send("Please provide a problem to think about!")
      return

    system_msg = "You are a logical thinking assistant. Break down problems step-by-step and show your reasoning process clearly."
    prompt = f"Please think through this step-by-step: {problem}"

    async with ctx.typing():
      guild_id = str(ctx.guild.id) if ctx.guild else None
      context = await context_grabber.get_relevant_context(problem, guild_id=guild_id)

      response = await ai_service.call_gemini_ai(
        prompt, system_message=system_msg, context=context
      )

    if len(response) > 2000:
      chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
      for chunk in chunks:
        await ctx.send(chunk)
    else:
      await ctx.send(response)

  @bot.command()
  async def summarize(ctx, scope: str = "channel", message_limit: int = 200):
    scope = scope.lower()
    if scope not in ["channel", "guild"]:
      await ctx.send("Invalid scope. Use 'channel' or 'guild'.")
      return

    message_limit = int(message_limit)

    if message_limit < 5 or message_limit > 200:
      await ctx.send("Message limit must be between 5 and 200.")
      return

    async with ctx.typing():
      messages = []

      if scope == "channel":
        async for message in ctx.channel.history(limit=message_limit):
          if not message.author.bot:
            messages.append(f"{message.author.display_name}: {message.content}")
      else:
        for channel in ctx.guild.text_channels:
          try:
            async for message in channel.history(limit=20):
              if not message.author.bot:
                messages.append(
                  f"{channel.name} - {message.author.display_name}: {message.content}"
                )
              if len(messages) >= message_limit:
                break
            if len(messages) >= message_limit:
              break
          except discord.Forbidden:
            continue

      if not messages:
        await ctx.send("No messages found to summarize.")
        return

      messages_text = "\n".join(messages[-message_limit:])
      prompt = (
        f"Please analyze these recent Discord messages and provide a concise summary "
        f"of the main topics, discussions, and notable events. "
        f"Focus on key points and trends:\n\n{messages_text}"
      )

      system_msg = (
        "You are a Discord community analyst. Provide clear, concise summaries of "
        "channel activity. Identify main topics, ongoing discussions, and notable "
        "events. Keep it brief but informative."
      )

      summary = await ai_service.call_gemini_ai(prompt, system_message=system_msg)

      title = f"📊 Summary of recent {scope} activity:"
      response = f"{title}\n\n{summary}"

      if len(response) > 2000:
        chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
          await ctx.send(chunk)
      else:
        await ctx.send(response)

  @bot.command()
  async def search_messages(ctx, *, query: str):
    if not query:
      await ctx.send("Please provide a search query!")
      return

    async with ctx.typing():
      from services.search_service import get_search_service

      search_service = get_search_service()

      guild_id = str(ctx.guild.id) if ctx.guild else None
      results = await search_service.search_messages(query, guild_id=guild_id)

    if not results:
      await ctx.send(f"No similar messages found for: {query}")
      return

    response_lines = [f"Found {len(results)} similar messages:"]
    for i, (url, score) in enumerate(results, 1):
      score_percent = score * 100
      response_lines.append(f"{i}. {url} (similarity: {score_percent:.1f}%)")

    response = "\n".join(response_lines)

    if len(response) > 2000:
      chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
      for chunk in chunks:
        await ctx.send(chunk)
    else:
      await ctx.send(response)
