import asyncio
from typing import Optional

from google import genai
from google.genai import types

from config import GEMINI_API_KEY


class AIService:
  def __init__(self):
    self.client = genai.Client(api_key=GEMINI_API_KEY).aio

  async def call_gemini_ai(
    self, prompt: str, system_message: str = "", context: str = ""
  ) -> str:
    if not prompt:
      return "You need a prompt to be able to interact with the AI."

    full_prompt = prompt
    if context:
      full_prompt = f"{context}\n\n{prompt}"

    try:
      config = None
      if system_message:
        config = types.GenerateContentConfig(system_instruction=system_message)

      response = await self.client.models.generate_content(
        model="gemini-3-flash",
        config=config,
        contents=full_prompt,
      )

      return response.text if response.text else "No response from Gemini"
    except asyncio.TimeoutError:
      return "Error: Request timed out"
    except Exception as e:
      return f"Error calling Gemini API: {str(e)}"


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
  global _ai_service
  if _ai_service is None:
    _ai_service = AIService()
  return _ai_service
