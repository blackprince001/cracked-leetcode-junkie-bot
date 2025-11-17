import asyncio
import json
import os
from datetime import time

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TIMEZONE = "UTC"
LEETCODE_SCHEDULE_TIME = time(hour=5, minute=00)
GM_SCHEDULE_TIME = time(hour=0, minute=00)

AI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)


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

    # Prepare to send up to 2 messages
    if len(messages) == 1:
        indices_to_send = [current_index]
    else:
        indices_to_send = [current_index, (current_index + 1) % len(messages)]

    sent_count = 0
    for idx in indices_to_send:
        try:
            message_content = messages[idx]
            msg = await channel.send(
                "Have you practiced today? A practice a day keeps rust away! \n\nQuestion of the Day\n\n"
                + message_content["content"]
            )
            # Create a thread for each posted question
            thread_title = message_content.get("thread_title", f"Question {idx + 1}")
            try:
                await msg.create_thread(name=thread_title)
            except discord.DiscordException as e:
                print(f"Warning: failed to create thread for message {idx}: {e}")

            sent_count += 1
            print(f"Sent message index {idx + 1}/{len(messages)}")

        except discord.DiscordException as e:
            print(f"Error sending message index {idx}: {str(e)}")
        except Exception as e:
            print(f"Unexpected error sending message index {idx}: {str(e)}")

    if sent_count > 0:
        # Advance the rotation by the number of messages actually sent
        data["last_used_index"] = (current_index + sent_count) % len(messages)
        save_data(data)
        print(f"Updated rotation index to {data['last_used_index']}")
    else:
        print("No messages were sent this run.")


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


async def call_gemini_ai(prompt: str, system_message: str = None) -> str:
    """
    Call Gemini API with the given prompt
    """
    # Build the full prompt with system message if provided
    if not prompt:
        return "You need a prompt to be able to interact with the AI."

    try:
        response = AI_CLIENT.models.generate_content(
            model="gemini-2.5-pro",
            config=types.GenerateContentConfig(system_instruction=system_message)
            if system_message is not None
            else None,
            contents=prompt,
        )

        return response.text if response.text else "No response from Gemini"
    except asyncio.TimeoutError:
        return "Error: Request timed out"
    except Exception as e:
        return f"Error calling Gemini API: {str(e)}"


@bot.command()
async def ask(ctx, *, question: str):
    """
    Ask a question to the AI
    Usage: !ask What is the weather like today?
    """
    if not question:
        await ctx.send("Please provide a question to ask the AI!")
        return

    # Send typing indicator
    async with ctx.typing():
        response = await call_gemini_ai(question)

    # Discord has a 2000 character limit, so we need to handle long responses
    if len(response) > 2000:
        # Split response into chunks
        chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)


@bot.command()
async def chat(ctx, *, message: str):
    """
    Have a casual conversation with the AI
    Usage: !chat Hello, how are you today?
    """
    if not message:
        await ctx.send("Please provide a message to chat with the AI!")
        return

    context_limit = 100

    # Add system message for conversational context
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

        prompt = (
            f"Here is the recent message history from the channel:\n\n"
            f"--- CHAT HISTORY ---\n"
            f"{chat_history}\n"
            f"--- END HISTORY ---\n\n"
            f"Please provide a natural, conversational response to the *last* message in this history."
            f"message: {message}"
        )

        response = await call_gemini_ai(prompt, system_message=system_msg)

    if len(response) > 2000:
        chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)


@bot.command()
async def explain(ctx, *, topic: str):
    """
    Ask the AI to explain a topic
    Usage: !explain quantum computing
    """
    if not topic:
        await ctx.send("Please provide a topic to explain!")
        return

    system_msg = "You are an expert educator. Explain topics clearly and concisely in a way that's easy to understand."
    prompt = f"Please explain {topic}:"

    async with ctx.typing():
        response = await call_gemini_ai(prompt, system_message=system_msg)

    if len(response) > 2000:
        chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)


@bot.command()
async def code_help(ctx, *, coding_question: str):
    """
    Ask the AI for coding help
    Usage: !code_help How do I reverse a string in Python?
    """
    if not coding_question:
        await ctx.send("Please provide a coding question!")
        return

    system_msg = "You are an expert programming assistant. Provide clear explanations and code examples when appropriate. Format code using markdown code blocks."

    async with ctx.typing():
        response = await call_gemini_ai(coding_question, system_message=system_msg)

    if len(response) > 2000:
        chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)


@bot.command()
async def ai_status(ctx):
    """
    Check if the DeepSeek API is working
    """
    async with ctx.typing():
        test_response = await call_gemini_ai(
            "Hello, this is a test message. Please respond with 'DeepSeek AI is working correctly!'"
        )

    if "Error" in test_response:
        await ctx.send(f"❌ GEMINI API Error: {test_response}")
    else:
        await ctx.send(f"✅ GEMINI API is working! Response: {test_response}")


@bot.command()
async def think(ctx, *, problem: str):
    """
    Ask DeepSeek to think step-by-step about a problem
    Usage: !think How do I solve this math problem: 2x + 5 = 15?
    """
    if not problem:
        await ctx.send("Please provide a problem to think about!")
        return

    system_msg = "You are a logical thinking assistant. Break down problems step-by-step and show your reasoning process clearly."
    prompt = f"Please think through this step-by-step: {problem}"

    async with ctx.typing():
        response = await call_gemini_ai(prompt, system_message=system_msg)

    if len(response) > 2000:
        chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)


@bot.command()
async def summarize(ctx, scope: str = "channel", message_limit: int = 200):
    """
    Generate a summary of recent activity in the channel or guild
    Usage: !summarize [channel|guild] [message_limit=50]
    """
    # Validate inputs
    scope = scope.lower()
    if scope not in ["channel", "guild"]:
        await ctx.send("Invalid scope. Use 'channel' or 'guild'.")
        return

    message_limit = int(message_limit)

    if message_limit < 5 or message_limit > 200:
        await ctx.send("Message limit must be between 5 and 200.")
        return

    async with ctx.typing():
        # Collect messages based on scope
        messages = []

        if scope == "channel":
            # Get messages from current channel
            async for message in ctx.channel.history(limit=message_limit):
                if not message.author.bot:  # Skip bot messages
                    messages.append(f"{message.author.display_name}: {message.content}")
        else:
            # Get messages from all text channels in guild
            for channel in ctx.guild.text_channels:
                try:
                    async for message in channel.history(
                        limit=20
                    ):  # Fewer per channel for guild-wide
                        if not message.author.bot:
                            messages.append(
                                f"{channel.name} - {message.author.display_name}: {message.content}"
                            )
                        if len(messages) >= message_limit:
                            break
                    if len(messages) >= message_limit:
                        break
                except discord.Forbidden:
                    continue  # Skip channels we can't read

        if not messages:
            await ctx.send("No messages found to summarize.")
            return

        # Prepare prompt for AI
        messages_text = "\n".join(
            messages[-message_limit:]
        )  # Ensure we don't exceed limit
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

        # Get summary from AI
        summary = await call_gemini_ai(prompt, system_message=system_msg)

        # Send the summary
        title = f"📊 Summary of recent {scope} activity:"
        response = f"{title}\n\n{summary}"

        if len(response) > 2000:
            chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send(response)


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

            if channel.name == "dsa":
                global LEETCODE_CHANNEL_ID
                LEETCODE_CHANNEL_ID = channel.id

            if channel.name == "gm":
                global GM_CHANNEL_ID
                GM_CHANNEL_ID = channel.id

    if not gm_scheduled_message.is_running():
        gm_scheduled_message.start()

    # if not leetcode_scheduled_message.is_running():
    #     leetcode_scheduled_message.start()


@bot.command()
async def rotation_status(ctx):
    data = load_data()
    await ctx.send(
        f"**Current Rotation Status:**\n"
        f"Next message: {data['last_used_index'] + 1}/{len(data['messages'])}\n"
        f"Total messages: {len(data['messages'])}"
    )


@bot.command()
async def ping(ctx):
    await ctx.send("pong")


@bot.command()
async def greet_user(ctx, user: str = "everyone"):
    await ctx.send(f"@{user}, greetings!")


@bot.command()
async def ai_help(ctx):
    """
    Show available commands (AI + normal)
    """
    help_text = """
**Bot AI Commands:**

`/ask <question>` - Ask any question to the AI  
`/chat <message>` - Have a casual conversation with the AI  
`/explain <topic>` - Get an explanation of a topic  
`/code_help <question>` - Get help with coding questions  
`/think <problem>` - Ask AI to think step-by-step about a problem  
`/ai_status` - Check if the Gemini API is working  
`/summarize [channel|guild] [message_limit=50]` - Generate a summary of recent activity in the channel or guild

**Normal Bot / Utility Commands:**

`/add_message <content> | <thread title>` - Add a message to the leetcode rotation (use `|` to separate content and thread title)  
`/list_messages` - List messages currently in the rotation  
`/remove_message <index>` - Remove a message from the rotation by 1-based index  
`/rotation_status` - Show current rotation index and total messages  
`/ping` - Responds with 'pong'  
`/greet_user [username]` - Greet a user (defaults to 'everyone')

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

If you need help with a specific command, mention it and I'll show usage.
"""
    await ctx.send(help_text)


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("Missing DISCORD_BOT_TOKEN in environment variables")
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY in environment variables")
    bot.run(TOKEN)
