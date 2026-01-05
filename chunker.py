import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MarkdownChunker:
    """Semantic markdown chunker that splits by headers."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        """
        Initialize the chunker.

        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using word count × 1.3.
        This matches the estimation used in the Next.js app.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        word_count = len(text.split())
        return int(word_count * 1.3)

    def _extract_header_info(self, section: str) -> dict:
        """
        Extract header information from a markdown section.

        Args:
            section: Markdown text section

        Returns:
            Dictionary with heading and section metadata
        """
        # Find the first header in the section
        header_match = re.match(r"^(#{1,6})\s+(.+)$", section, re.MULTILINE)

        if header_match:
            level = len(header_match.group(1))
            heading = header_match.group(2).strip()
            return {"heading": heading, "section": f"h{level}"}

        return {}

    def _split_by_headers(self, markdown_text: str) -> list[tuple[str, dict]]:
        """
        Split markdown by headers (H1-H6).

        Args:
            markdown_text: Full markdown text

        Returns:
            List of (section_text, metadata) tuples
        """
        # Split by headers while keeping the header with the content
        sections = re.split(r"(?=^#{1,6}\s+)", markdown_text, flags=re.MULTILINE)

        result = []
        for section in sections:
            section = section.strip()
            if not section:
                continue

            metadata = self._extract_header_info(section)
            result.append((section, metadata))

        return result if result else [(markdown_text, {})]

    def _split_large_section(
        self, text: str, metadata: dict
    ) -> list[tuple[str, dict]]:
        """
        Split a large section that exceeds max_tokens into smaller chunks.

        Args:
            text: Text to split
            metadata: Metadata to attach to chunks

        Returns:
            List of (chunk_text, metadata) tuples
        """
        chunks = []
        paragraphs = text.split("\n\n")
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)

            # If a single paragraph is too large, split by sentences
            if para_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append(("\n\n".join(current_chunk), metadata.copy()))
                    current_chunk = []
                    current_tokens = 0

                # Split by sentences
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sentence_chunk = []
                sentence_tokens = 0

                for sentence in sentences:
                    sent_tokens = self._estimate_tokens(sentence)

                    if sentence_tokens + sent_tokens > self.max_tokens:
                        if sentence_chunk:
                            chunks.append((" ".join(sentence_chunk), metadata.copy()))
                        sentence_chunk = [sentence]
                        sentence_tokens = sent_tokens
                    else:
                        sentence_chunk.append(sentence)
                        sentence_tokens += sent_tokens

                if sentence_chunk:
                    chunks.append((" ".join(sentence_chunk), metadata.copy()))

            # If adding this paragraph would exceed max_tokens
            elif current_tokens + para_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append(("\n\n".join(current_chunk), metadata.copy()))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

        # Add remaining content
        if current_chunk:
            chunks.append(("\n\n".join(current_chunk), metadata.copy()))

        return chunks

    def chunk(self, markdown_text: str) -> list[dict]:
        """
        Chunk markdown text semantically by headers.

        Args:
            markdown_text: Full markdown text to chunk

        Returns:
            List of chunk dictionaries with 'content' and 'metadata' keys
        """
        logger.info(
            f"Chunking markdown text ({len(markdown_text)} characters) "
            f"with max_tokens={self.max_tokens}"
        )

        # Split by headers first
        sections = self._split_by_headers(markdown_text)

        chunks = []
        for section_text, metadata in sections:
            section_tokens = self._estimate_tokens(section_text)

            # If section fits within max_tokens, keep it as one chunk
            if section_tokens <= self.max_tokens:
                chunks.append({"content": section_text, "metadata": metadata})
            else:
                # Split large sections further
                sub_chunks = self._split_large_section(section_text, metadata)
                for chunk_text, chunk_metadata in sub_chunks:
                    chunks.append({"content": chunk_text, "metadata": chunk_metadata})

        logger.info(
            f"Created {len(chunks)} chunks from markdown "
            f"(avg {len(markdown_text) // len(chunks) if chunks else 0} chars per chunk)"
        )

        return chunks
