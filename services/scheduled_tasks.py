import datetime

import discord
from discord.ext import tasks

from config import (
    LEETCODE_CHANNEL_NAME,
    LEETCODE_DAILY_TIME_HOUR,
    LEETCODE_DAILY_TIME_MINUTE,
)
from services.leetcode_service import get_leetcode_service
from utils.logging import get_logger

logger = get_logger("scheduler")


class ScheduledTasks:
    def __init__(self, bot):
        self.bot = bot
        self.leetcode_service = get_leetcode_service()
        
        # Calculate time for the loop
        self.daily_time = datetime.time(
            hour=LEETCODE_DAILY_TIME_HOUR,
            minute=LEETCODE_DAILY_TIME_MINUTE,
            tzinfo=datetime.timezone.utc
        )
        
        # Start loops
        self.leetcode_daily_task.start()
        logger.info(f"📅 LeetCode scheduler initialized for {self.daily_time} UTC")

    def cog_unload(self):
        self.leetcode_daily_task.cancel()

    @tasks.loop(time=[datetime.time(hour=LEETCODE_DAILY_TIME_HOUR, minute=LEETCODE_DAILY_TIME_MINUTE, tzinfo=datetime.timezone.utc)])
    async def leetcode_daily_task(self):
        """Task that runs daily to post the LeetCode question."""
        logger.info("⏰ Running daily LeetCode task")
        await self.post_daily_leetcode()

    async def post_daily_leetcode(self, target_channel_id: int = None):
        """Logic to fetch and post the message."""
        try:
            question = await self.leetcode_service.fetch_daily_question()
            if not question:
                logger.error("Failed to fetch daily LeetCode question")
                return

            embed = self.leetcode_service.create_daily_embed(question)
            
            # Post to all guilds that have the configured channel
            for guild in self.bot.guilds:
                target_channel = None
                
                # If specific ID provided (for testing), use it if valid
                if target_channel_id:
                    target_channel = guild.get_channel(target_channel_id)
                else:
                    # Otherwise find channel by name
                    target_channel = discord.utils.get(guild.text_channels, name=LEETCODE_CHANNEL_NAME)

                if target_channel:
                    try:
                        message = await target_channel.send(embed=embed)
                        
                        # Create a thread for discussion
                        question_title = question.get("question", {}).get("title", "Daily Question")
                        thread_name = f"🧵 {question_title}"
                        await message.create_thread(name=thread_name, auto_archive_duration=1440)
                        
                        logger.info(f"✅ Posted LeetCode daily to {guild.name} #{target_channel.name}")
                    except discord.Forbidden:
                        logger.warning(f"❌ Missing permissions to post/thread to {guild.name} #{target_channel.name}")
                    except Exception as e:
                        logger.error(f"❌ Error posting to {guild.name}: {e}")
                else:
                    # Debug log only to avoid spam
                    logger.debug(f"Skipping {guild.name}: No #{LEETCODE_CHANNEL_NAME} channel found")

        except Exception as e:
            logger.error(f"Error in daily LeetCode task: {e}")

    @leetcode_daily_task.before_loop
    async def before_leetcode_task(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()


def setup_scheduled_tasks(bot):
    return ScheduledTasks(bot)
