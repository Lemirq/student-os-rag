import asyncio
import logging
from openai import AsyncOpenAI, RateLimitError
from config import settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings using OpenAI's API with retry logic."""

    def __init__(self, max_retries: int = 2, retry_delay_ms: int = 1000):
        """
        Initialize the embedding generator.

        Args:
            max_retries: Maximum number of retries for failed requests
            retry_delay_ms: Initial delay between retries in milliseconds
        """
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms
        self.model = settings.embedding_model
        self.expected_dimensions = settings.embedding_dimensions

    async def _generate_with_retry(
        self, text: str, attempt: int = 0
    ) -> list[float]:
        """
        Generate embedding with exponential backoff retry logic.

        Args:
            text: Text to generate embedding for
            attempt: Current attempt number (0-indexed)

        Returns:
            Embedding vector

        Raises:
            Exception: If all retries fail
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model, input=text, encoding_format="float"
            )

            embedding = response.data[0].embedding

            # Validate dimensions
            if len(embedding) != self.expected_dimensions:
                raise ValueError(
                    f"Expected {self.expected_dimensions} dimensions, "
                    f"got {len(embedding)}"
                )

            return embedding

        except RateLimitError as e:
            if attempt < self.max_retries:
                # Exponential backoff: 1s, 2s, 4s, etc.
                delay_seconds = (self.retry_delay_ms / 1000) * (2**attempt)
                logger.warning(
                    f"Rate limit hit, retrying in {delay_seconds}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(delay_seconds)
                return await self._generate_with_retry(text, attempt + 1)
            else:
                logger.error(f"Rate limit exceeded after {self.max_retries} retries")
                raise Exception(f"Rate limit exceeded: {str(e)}")

        except Exception as e:
            if attempt < self.max_retries:
                delay_seconds = (self.retry_delay_ms / 1000) * (2**attempt)
                logger.warning(
                    f"Embedding generation failed, retrying in {delay_seconds}s: {str(e)}"
                )
                await asyncio.sleep(delay_seconds)
                return await self._generate_with_retry(text, attempt + 1)
            else:
                logger.error(
                    f"Embedding generation failed after {self.max_retries} retries: {str(e)}"
                )
                raise Exception(f"Embedding generation failed: {str(e)}")

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of text strings to generate embeddings for

        Returns:
            List of embedding vectors

        Raises:
            Exception: If embedding generation fails
        """
        logger.info(f"Generating embeddings for {len(texts)} texts")

        try:
            # Generate embeddings concurrently
            tasks = [self._generate_with_retry(text) for text in texts]
            embeddings = await asyncio.gather(*tasks)

            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {str(e)}")
            raise

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        return await self._generate_with_retry(text)
