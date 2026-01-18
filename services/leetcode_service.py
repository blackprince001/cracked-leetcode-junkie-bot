from typing import Dict, Optional

import aiohttp
import discord

from config import LEETCODE_API_URL
from utils.logging import get_logger

logger = get_logger("leetcode")


class LeetCodeService:
  """Service to fetch LeetCode Problem of the Day."""

  def __init__(self):
    self.session: Optional[aiohttp.ClientSession] = None

  async def _get_session(self) -> aiohttp.ClientSession:
    if self.session is None or self.session.closed:
      self.session = aiohttp.ClientSession()
    return self.session

  async def fetch_daily_question(self) -> Optional[Dict]:
    """Fetch the active daily coding challenge question from LeetCode."""
    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        userStatus
        link
        question {
          acRate
          difficulty
          freqBar
          frontendQuestionId: questionFrontendId
          isFavor
          paidOnly: isPaidOnly
          status
          title
          titleSlug
          hasVideoSolution
          hasSolution
          topicTags {
            name
            id
            slug
          }
        }
      }
    }
    """
    
    payload = {
        "query": query,
        "operationName": "questionOfToday"
    }

    try:
      session = await self._get_session()
      async with session.post(LEETCODE_API_URL, json=payload, headers={"Content-Type": "application/json"}) as response:
        if response.status != 200:
          logger.error(f"LeetCode API failed with status {response.status}")
          return None
        
        data = await response.json()
        if "errors" in data:
          logger.error(f"LeetCode GraphQL errors: {data['errors']}")
          return None
          
        return data.get("data", {}).get("activeDailyCodingChallengeQuestion")

    except Exception as e:
      logger.error(f"Error fetching LeetCode daily question: {e}")
      return None

  def create_daily_embed(self, question_data: Dict) -> discord.Embed:
    """Create a polished Discord Embed for the daily question."""
    if not question_data:
        return discord.Embed(title="Error", description="Could not fetch daily question.", color=discord.Color.red())

    date = question_data.get("date", "Today")
    link = f"https://leetcode.com{question_data.get('link', '')}"
    
    q_info = question_data.get("question", {})
    title = q_info.get("title", "Unknown Title")
    difficulty = q_info.get("difficulty", "Unknown")
    ac_rate = q_info.get("acRate", 0.0)
    question_id = q_info.get("frontendQuestionId", "?")
    tags = [tag["name"] for tag in q_info.get("topicTags", [])]

    # Color based on difficulty
    color = discord.Color.green()  # Easy
    if difficulty == "Medium":
        color = discord.Color.gold()
    elif difficulty == "Hard":
        color = discord.Color.red()

    embed = discord.Embed(
        title=f"🧩 LeetCode Daily: {title}",
        url=link,
        description=f"**Date:** {date}\n**Difficulty:** {difficulty}",
        color=color
    )
    
    embed.add_field(name="Question ID", value=question_id, inline=True)
    embed.add_field(name="Acceptance Rate", value=f"{ac_rate:.1f}%", inline=True)
    
    if tags:
        embed.add_field(name="Topics", value=", ".join(tags), inline=False)
        
    embed.set_footer(text="Good luck! 🚀 • Cracked LeetCode Bot")
    
    return embed

  async def close(self):
    if self.session and not self.session.closed:
        await self.session.close()


_leetcode_service: Optional[LeetCodeService] = None


def get_leetcode_service() -> LeetCodeService:
  global _leetcode_service
  if _leetcode_service is None:
    _leetcode_service = LeetCodeService()
  return _leetcode_service
