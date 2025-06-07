import json
import os
from datetime import time
import aiohttp
import asyncio

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Add this to your .env file
TIMEZONE = "UTC"
LEETCODE_SCHEDULE_TIME = time(hour=5, minute=00)
GM_SCHEDULE_TIME = time(hour=0, minute=00)

# DeepSeek API endpoint
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)



# def load_data():
#     default_data = {"messages": [], "last_used_index": 0}

#     try:
#         with open("messages.json", "r") as f:
#             data = json.load(f)

#             if not isinstance(data, dict):
#                 print("Invalid data format in messages.json, resetting to default.")
#                 return default_data

#             if "messages" not in data or "last_used_index" not in data:
#                 print("Missing keys in messages.json, resetting to default.")
#                 return default_data

#             return data

#     except FileNotFoundError:
#         print("messages.json not found, creating with default data.")
#         save_data(default_data)
#         return default_data

#     except json.JSONDecodeError:
#         print("Error decoding messages.json, resetting to default.")
#         save_data(default_data)
#         return default_data


# def save_data(data):
#     with open("messages.json", "w") as f:
#         json.dump(data, f, indent=4)


# @tasks.loop(time=LEETCODE_SCHEDULE_TIME)
# async def leetcode_scheduled_message():
#     channel = bot.get_channel(LEETCODE_CHANNEL_ID)
#     if not channel:
#         print(f"Could not find channel with ID {LEETCODE_CHANNEL_ID}")
#         return

#     data = load_data()
#     messages = data["messages"]

#     if not messages:
#         print("No messages found in messages.json")
#         return

#     # Get and validate current index
#     current_index = data["last_used_index"]
#     if current_index >= len(messages):
#         current_index = 0

#     try:
#         # Send the current message
#         message_content = messages[current_index]
#         msg = await channel.send("Question of the Day\n\n" + message_content["content"])
#         await msg.create_thread(name=message_content["thread_title"])

#         # Update index for next run
#         new_index = (current_index + 1) % len(messages)
#         data["last_used_index"] = new_index
#         save_data(data)

#         print(f"Sent message {current_index + 1}/{len(messages)}")

#     except discord.DiscordException as e:
#         print(f"Error sending message: {str(e)}")

# @bot.command()
# async def add_message(ctx, *, content: str):
#     if "|" not in content:
#         await ctx.send(
#             "Error: Use format: `!add_message Message Content | Thread Title`"
#         )
#         return

#     content_part, thread_part = content.split("|", 1)
#     content_part = content_part.strip()
#     thread_part = thread_part.strip()

#     if not content_part or not thread_part:
#         await ctx.send("Error: Both message content and thread title are required")
#         return

#     new_message = {"content": content_part, "thread_title": thread_part}

#     data = load_data()
#     data["messages"].append(new_message)
#     save_data(data)

#     await ctx.send(f'Message added! Total messages: {len(data["messages"])}')


# @bot.command()
# async def list_messages(ctx):
#     data = load_data()
#     messages = data["messages"]

#     if not messages:
#         await ctx.send("No messages in rotation!")
#         return

#     response = [
#         f"**Message Rotation (Current: {data['last_used_index'] + 1}/{len(messages)})**"
#     ]
#     for idx, msg in enumerate(messages, 1):
#         response.append(
#             f"{idx}. {msg['content'][:50]}... | Thread: {msg['thread_title']}"
#         )

#     await ctx.send("\n".join(response[:15]))


# @bot.command()
# async def remove_message(ctx, index: int):
#     data = load_data()
#     messages = data["messages"]

#     if 1 <= index <= len(messages):
#         removed = messages.pop(index - 1)
#         if data["last_used_index"] >= len(messages):
#             data["last_used_index"] = 0
#         save_data(data)
#         await ctx.send(f'Removed: "{removed["content"][:50]}..."')
#     else:
#         await ctx.send(f"Invalid index! Use 1-{len(messages)}")


async def call_deepseek_ai(prompt: str, max_tokens: int = 512, system_message: str = None) -> str:
    """
    Call DeepSeek API with the given prompt
    """
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Build messages array for chat completion
    messages = []
    
    if system_message:
        messages.append({"role": "system", "content": system_message})
    
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": False
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    # Extract the response from DeepSeek format
                    if 'choices' in result and len(result['choices']) > 0:
                        return result['choices'][0]['message']['content']
                    else:
                        return "No response received from DeepSeek"
                else:
                    error_text = await response.text()
                    return f"Error: API returned status {response.status}: {error_text}"
    except asyncio.TimeoutError:
        return "Error: Request timed out"
    except Exception as e:
        return f"Error calling DeepSeek API: {str(e)}"


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
        response = await call_deepseek_ai(question)
    
    # Discord has a 2000 character limit, so we need to handle long responses
    if len(response) > 2000:
        # Split response into chunks
        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
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
    
    # Add system message for conversational context
    system_msg = "You are a helpful and friendly AI assistant in a Discord chat. Respond naturally and conversationally."
    
    async with ctx.typing():
        response = await call_deepseek_ai(message, system_message=system_msg)
    
    if len(response) > 2000:
        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
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
        response = await call_deepseek_ai(prompt, max_tokens=800, system_message=system_msg)
    
    if len(response) > 2000:
        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
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
        response = await call_deepseek_ai(coding_question, max_tokens=1000, system_message=system_msg)
    
    if len(response) > 2000:
        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
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
        test_response = await call_deepseek_ai("Hello, this is a test message. Please respond with 'DeepSeek AI is working correctly!'")
    
    if "Error" in test_response:
        await ctx.send(f"❌ DeepSeek API Error: {test_response}")
    else:
        await ctx.send(f"✅ DeepSeek API is working! Response: {test_response}")


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
        response = await call_deepseek_ai(prompt, max_tokens=1000, system_message=system_msg)
    
    if len(response) > 2000:
        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
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

            if channel.name == "leetcode-and-prep":
                global LEETCODE_CHANNEL_ID
                LEETCODE_CHANNEL_ID = channel.id

            if channel.name == "gm":
                global GM_CHANNEL_ID
                GM_CHANNEL_ID = channel.id

    if not gm_scheduled_message.is_running():
        gm_scheduled_message.start()


@bot.command()
async def rotation_status(ctx):
    await ctx.send("nothing in rotation now")


@bot.command()
async def ping(ctx):
    await ctx.send("pong")


@bot.command()
async def greet_user(ctx, user: str = "everyone"):
    await ctx.send(f"@{user}, greetings!")


@bot.command()
async def help_ai(ctx):
    """
    Show available AI commands
    """
    help_text = """
**DeepSeek AI Commands Available:**

`!ask <question>` - Ask any question to the AI
`!chat <message>` - Have a casual conversation with the AI
`!explain <topic>` - Get an explanation of a topic
`!code_help <question>` - Get help with coding questions
`!think <problem>` - Ask AI to think step-by-step about a problem
`!ai_status` - Check if the DeepSeek API is working

**Examples:**
`!ask What is the capital of France?`
`!chat Hello, how are you today?`
`!explain machine learning`
`!code_help How do I create a list in Python?`
`!think How do I solve 2x + 5 = 15?`
    """
    await ctx.send(help_text)


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("Missing DISCORD_BOT_TOKEN in environment variables")
    if not DEEPSEEK_API_KEY:
        raise ValueError("Missing DEEPSEEK_API_KEY in environment variables")
    bot.run(TOKEN)