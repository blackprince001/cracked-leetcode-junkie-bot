import asyncio
from typing import Optional

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL
from utils.logging import get_logger

logger = get_logger("ai")


class AIService:
  def __init__(self):
    self.client = genai.Client(api_key=GEMINI_API_KEY).aio

  async def call_gemini_ai(
    self,
    prompt: str,
    system_message: str = "",
    context: str = "",
    use_search: bool = True,
  ) -> str:
    if not prompt:
      return "You need a prompt to be able to interact with the AI."

    full_prompt = prompt
    if context:
      full_prompt = f"{context}\n\n{prompt}"

    logger.info(f"🤖 AI request: {prompt[:80]}...")

    try:
      # Build config with optional Google Search grounding
      tools = []
      if use_search:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        tools.append(grounding_tool)

      config = types.GenerateContentConfig(
        tools=tools if tools else None,
        system_instruction=system_message if system_message else None,
      )

      response = await self.client.models.generate_content(
        model=GEMINI_MODEL,
        config=config,
        contents=full_prompt,
      )

      result = response.text if response.text else "No response from Gemini"
      logger.info(f"🤖 AI response: {result[:80]}...")
      return result
    except asyncio.TimeoutError:
      logger.error("AI request timed out")
      return "Error: Request timed out"
    except Exception as e:
      logger.error(f"AI error: {e}")
      return f"Error calling Gemini API: {str(e)}"


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
  global _ai_service
  if _ai_service is None:
    _ai_service = AIService()
  return _ai_service
