import asyncio
from typing import List, Optional

import numpy as np
from google import genai

from config import EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL, GEMINI_API_KEY


class EmbeddingService:
  def __init__(self):
    self.client = genai.Client(api_key=GEMINI_API_KEY).aio

  async def generate_embedding(self, text: str) -> Optional[np.ndarray]:
    if not text or not text.strip():
      return None

    results = await self.generate_embeddings_batch([text])
    return results[0] if results else None

  async def generate_embeddings_batch(
    self, texts: List[str]
  ) -> List[Optional[np.ndarray]]:
    if not texts:
      return []

    valid_texts = [(i, text) for i, text in enumerate(texts) if text and text.strip()]
    
    if not valid_texts:
      return [None] * len(texts)

    results = [None] * len(texts)

    for i in range(0, len(valid_texts), EMBEDDING_BATCH_SIZE):
      batch = valid_texts[i : i + EMBEDDING_BATCH_SIZE]
      batch_texts = [text for _, text in batch]
      batch_indices = [idx for idx, _ in batch]

      try:
        response = await self.client.models.embed_content(
          model=EMBEDDING_MODEL,
          contents=batch_texts,
        )

        if hasattr(response, "embeddings") and response.embeddings:
          for j, embedding_obj in enumerate(response.embeddings):
            if j < len(batch_indices):
              if hasattr(embedding_obj, "values"):
                embedding_values = embedding_obj.values
                if embedding_values:
                  results[batch_indices[j]] = np.array(
                    embedding_values, dtype=np.float32
                  )

        await asyncio.sleep(0.1)

      except Exception as e:
        print(f"Error generating batch embeddings: {e}")
        import traceback

        traceback.print_exc()

    return results

  def embedding_to_bytes(self, embedding: np.ndarray) -> bytes:
    return embedding.tobytes()

  def bytes_to_embedding(self, data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
  global _embedding_service
  if _embedding_service is None:
    _embedding_service = EmbeddingService()
  return _embedding_service
