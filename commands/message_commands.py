import json

from discord.ext import commands


def load_data():
  default_data = {"messages": [], "last_used_index": 0}

  try:
    with open("messages.json", "r") as f:
      data = json.load(f)

      if not isinstance(data, dict):
        print("Invalid data format in messages.json, resetting to default.")
        return default_data

      if "messages" not in data or "last_used_index" not in data:
        print("Missing keys in messages.json, resetting to default.")
        return default_data

      return data

  except FileNotFoundError:
    print("messages.json not found, creating with default data.")
    save_data(default_data)
    return default_data

  except json.JSONDecodeError:
    print("Error decoding messages.json, resetting to default.")
    save_data(default_data)
    return default_data


def save_data(data):
  with open("messages.json", "w") as f:
    json.dump(data, f, indent=4)


def setup_message_commands(bot: commands.Bot):
  @bot.command()
  async def add_message(ctx, *, content: str):
    if "|" not in content:
      await ctx.send("Error: Use format: `/add_message Message Content | Thread Title`")
      return

    content_part, thread_part = content.split("|", 1)
    content_part = content_part.strip()
    thread_part = thread_part.strip()

    if not content_part or not thread_part:
      await ctx.send("Error: Both message content and thread title are required")
      return

    new_message = {"content": content_part, "thread_title": thread_part}

    data = load_data()
    data["messages"].append(new_message)
    save_data(data)

    await ctx.send(f"Message added! Total messages: {len(data['messages'])}")

  @bot.command()
  async def list_messages(ctx):
    data = load_data()
    messages = data["messages"]

    if not messages:
      await ctx.send("No messages in rotation!")
      return

    response = [
      f"**Message Rotation (Current: {data['last_used_index'] + 1}/{len(messages)})**"
    ]
    for idx, msg in enumerate(messages, 1):
      response.append(
        f"{idx}. {msg['content'][:50]}... | Thread: {msg['thread_title']}"
      )

    await ctx.send("\n".join(response[:15]))

  @bot.command()
  async def remove_message(ctx, index: int):
    data = load_data()
    messages = data["messages"]

    if 1 <= index <= len(messages):
      removed = messages.pop(index - 1)
      if data["last_used_index"] >= len(messages):
        data["last_used_index"] = 0
      save_data(data)
      await ctx.send(f'Removed: "{removed["content"][:50]}..."')
    else:
      await ctx.send(f"Invalid index! Use 1-{len(messages)}")

  @bot.command()
  async def rotation_status(ctx):
    data = load_data()
    await ctx.send(
      f"**Current Rotation Status:**\n"
      f"Next message: {data['last_used_index'] + 1}/{len(data['messages'])}\n"
      f"Total messages: {len(data['messages'])}"
    )
