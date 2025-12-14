from typing import List, Optional, Tuple

from config import DEFAULT_SEARCH_LIMIT
from db import message_db
from services.embedding_service import get_embedding_service


class SearchService:
  def __init__(self):
    self.embedding_service = get_embedding_service()

  async def search_messages(
    self, query: str, guild_id: Optional[str] = None, limit: int = DEFAULT_SEARCH_LIMIT
  ) -> List[Tuple[str, float]]:
    if not query or not query.strip():
      return []

    query_embedding = await self.embedding_service.generate_embedding(query)
    if query_embedding is None:
      return []

    results = await message_db.search_similar_messages(
      query_embedding=query_embedding,
      guild_id=guild_id,
      limit=limit,
    )

    return results

  async def search_messages_urls_only(
    self, query: str, guild_id: Optional[str] = None, limit: int = DEFAULT_SEARCH_LIMIT
  ) -> List[str]:
    results = await self.search_messages(query, guild_id, limit)
    return [url for url, _ in results]


_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
  global _search_service
  if _search_service is None:
    _search_service = SearchService()
  return _search_service
