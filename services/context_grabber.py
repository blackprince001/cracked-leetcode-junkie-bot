from typing import Optional

from config import DEFAULT_CONTEXT_LIMIT
from services.search_service import get_search_service


class ContextGrabber:
  def __init__(self):
    self.search_service = get_search_service()

  async def get_relevant_context(
    self, query: str, guild_id: Optional[str] = None, limit: int = DEFAULT_CONTEXT_LIMIT
  ) -> str:
    """Fetch relevant message content to use as context for AI responses."""
    if not query or not query.strip():
      return ""

    results = await self.search_service.search_messages(
      query=query,
      guild_id=guild_id,
      limit=limit,
    )

    if not results:
      return ""

    context_lines = ["Here are relevant messages from this server that may help:"]
    for i, (_url, content, _score) in enumerate(results, 1):
      # Truncate long messages to keep context manageable
      truncated_content = content[:300] + "..." if len(content) > 300 else content
      context_lines.append(f"{i}. {truncated_content}")

    return "\n".join(context_lines)


_context_grabber: Optional[ContextGrabber] = None


def get_context_grabber() -> ContextGrabber:
  global _context_grabber
  if _context_grabber is None:
    _context_grabber = ContextGrabber()
  return _context_grabber
