import json
import os
import threading
from datetime import time

import discord
import uvicorn
from discord.ext import commands, tasks
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

TIMEZONE = "UTC"
LEETCODE_SCHEDULE_TIME = time(hour=5, minute=00)
GM_SCHEDULE_TIME = time(hour=0, minute=00)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "Discord bot is running!"}


def run_fastapi():
    """Run the FastAPI server."""
    uvicorn.run(app, host="0.0.0.0", port=10000)


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


@tasks.loop(time=LEETCODE_SCHEDULE_TIME)
async def leetcode_scheduled_message():
    channel = bot.get_channel(LEETCODE_CHANNEL_ID)
    if not channel:
        print(f"Could not find channel with ID {LEETCODE_CHANNEL_ID}")
        return

    data = load_data()
    messages = data["messages"]

    if not messages:
        print("No messages found in messages.json")
        return

    # Get and validate current index
    current_index = data["last_used_index"]
    if current_index >= len(messages):
        current_index = 0

    try:
        # Send the current message
        message_content = messages[current_index]
        msg = await channel.send("Question of the Day\n\n" + message_content["content"])
        await msg.create_thread(name=message_content["thread_title"])

        # Update index for next run
        new_index = (current_index + 1) % len(messages)
        data["last_used_index"] = new_index
        save_data(data)

        print(f"Sent message {current_index + 1}/{len(messages)}")

    except discord.DiscordException as e:
        print(f"Error sending message: {str(e)}")


@tasks.loop(time=GM_SCHEDULE_TIME)
async def gm_scheduled_message():
    channel = bot.get_channel(GM_CHANNEL_ID)
    if not channel:
        print(f"Could not find channel with ID {GM_CHANNEL_ID}")
        return

    try:
        await channel.send("gm")
        print("Sent message Good Morning Message")

    except discord.DiscordException as e:
        print(f"Error sending message: {str(e)}")


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

    for guild in bot.guilds:
        print(f"Guild: {guild.name} (ID: {guild.id})")
        for channel in guild.channels:
            print(
                f" - Channel: {channel.name} (ID: {channel.id}, Type: {channel.type})"
            )

            if channel.name == "leetcode-and-prep":
                global LEETCODE_CHANNEL_ID
                LEETCODE_CHANNEL_ID = channel.id

            if channel.name == "gm":
                global GM_CHANNEL_ID
                GM_CHANNEL_ID == channel.id

    if (
        not leetcode_scheduled_message.is_running()
        and not gm_scheduled_message.is_running()
    ):
        leetcode_scheduled_message.start()
        gm_scheduled_message.start()


@bot.command()
async def add_message(ctx, *, content: str):
    if "|" not in content:
        await ctx.send(
            "Error: Use format: `!add_message Message Content | Thread Title`"
        )
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

    await ctx.send(f'Message added! Total messages: {len(data["messages"])}')


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


if __name__ == "__main__":
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()

    if not TOKEN:
        raise ValueError("Missing DISCORD_BOT_TOKEN in environment variables")
    bot.run(TOKEN)
