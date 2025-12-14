from typing import Optional

from config import DEFAULT_CONTEXT_LIMIT
from services.search_service import get_search_service


class ContextGrabber:
  def __init__(self):
    self.search_service = get_search_service()

  async def get_relevant_context(
    self, query: str, guild_id: Optional[str] = None, limit: int = DEFAULT_CONTEXT_LIMIT
  ) -> str:
    if not query or not query.strip():
      return ""

    message_urls = await self.search_service.search_messages_urls_only(
      query=query,
      guild_id=guild_id,
      limit=limit,
    )

    if not message_urls:
      return ""

    context_lines = ["Relevant server context:"]
    for i, url in enumerate(message_urls, 1):
      context_lines.append(f"{i}. {url}")

    return "\n".join(context_lines)


_context_grabber: Optional[ContextGrabber] = None


def get_context_grabber() -> ContextGrabber:
  global _context_grabber
  if _context_grabber is None:
    _context_grabber = ContextGrabber()
  return _context_grabber
