import discord
from discord.ext import commands

from commands import ai_commands, message_commands, utility_commands
from config import GEMINI_API_KEY, TOKEN
from db import message_db
from services.message_indexer import get_message_indexer

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)


@bot.event
async def on_ready():
  print(f"{bot.user} has connected to Discord!")

  await message_db.init_db()
  print("Database initialized.")

  indexer = get_message_indexer()
  indexer.start()
  print("Message indexer started.")

  for guild in bot.guilds:
    print(f"Guild: {guild.name} (ID: {guild.id})")
    for channel in guild.channels:
      print(f" - Channel: {channel.name} (ID: {channel.id}, Type: {channel.type})")


@bot.event
async def on_message(message: discord.Message):
  await bot.process_commands(message)

  if message.author.bot:
    return

  if not message.content or not message.content.strip():
    return

  if message.content.startswith("/"):
    return

  if not message.guild:
    return

  indexer = get_message_indexer()
  await indexer.queue_message(message)


setup_ai_commands = ai_commands.setup_ai_commands
setup_message_commands = message_commands.setup_message_commands
setup_utility_commands = utility_commands.setup_utility_commands

setup_ai_commands(bot)
setup_message_commands(bot)
setup_utility_commands(bot)


if __name__ == "__main__":
  if not TOKEN:
    raise ValueError("Missing DISCORD_BOT_TOKEN in environment variables")
  if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in environment variables")

  try:
    bot.run(TOKEN)
  except KeyboardInterrupt:
    print("Bot shutting down...")
    indexer = get_message_indexer()
    indexer.stop()
