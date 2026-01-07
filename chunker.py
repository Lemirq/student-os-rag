import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MarkdownChunker:
    """Semantic markdown chunker with multi-pass adaptive splitting."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        """
        Initialize chunker.

        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.increased_overlap = overlap_tokens * 2  # Increased overlap for final fallback

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
            return {"heading": heading, "section": f"h{level}", "chunking_method": "markdown_headers"}

        return {}

    def _has_markdown_subheaders(self, text: str) -> bool:
        """
        Check if text contains markdown subheaders (h2-h6).

        Args:
            text: Text to check

        Returns:
            True if subheaders found, False otherwise
        """
        # Look for ## or ### etc. (excluding h1 which might be at the top)
        return bool(re.search(r"^#{2,6}\s+", text, re.MULTILINE))

    def _has_bold_headings(self, text: str, min_splits: int = 2) -> bool:
        """
        Check if text contains standalone bold headings suitable for splitting.

        Args:
            text: Text to check
            min_splits: Minimum number of bold headings required

        Returns:
            True if sufficient bold headings found, False otherwise
        """
        # Find standalone bold headings: line starts and ends with **
        # Must be at least 3 words (to avoid noise like "Note:")
        bold_pattern = r"^\*\*.{6,}\*\*$"
        bold_headings = re.findall(bold_pattern, text, re.MULTILINE)

        # Must have minimum number of splits
        return len(bold_headings) >= min_splits

    def _extract_bold_heading_info(self, section: str) -> dict:
        """
        Extract bold heading information from a section.

        Args:
            section: Markdown text section

        Returns:
            Dictionary with heading and section metadata
        """
        # Find standalone bold heading at the start
        bold_match = re.match(r"^(\*\*.+\*\*)$", section, re.MULTILINE)

        if bold_match:
            # Remove ** markers and clean up
            heading = bold_match.group(1).replace("**", "").strip()
            return {"heading": heading, "section": "bold", "chunking_method": "bold_headings"}

        # If section starts with # header instead (text before first bold)
        header_match = re.match(r"^(#{1,6})\s+(.+)$", section, re.MULTILINE)
        if header_match:
            level = len(header_match.group(1))
            heading = header_match.group(2).strip()
            return {"heading": heading, "section": f"h{level}", "chunking_method": "bold_headings"}

        return {"chunking_method": "bold_headings"}

    def _split_by_bold_headings(self, text: str) -> list[tuple[str, dict]]:
        """
        Split markdown by standalone bold headings.

        Args:
            text: Full markdown text

        Returns:
            List of (section_text, metadata) tuples
        """
        # Split by standalone bold headings while keeping the heading with content
        sections = re.split(r"(?=^\*\*.{6,}\*\*$)", text, flags=re.MULTILINE)

        result = []
        for section in sections:
            section = section.strip()
            if not section:
                continue

            metadata = self._extract_bold_heading_info(section)
            result.append((section, metadata))

        return result if result else [(text, {"chunking_method": "paragraph_split"})]

    def _split_by_structural_markers(self, text: str) -> list[tuple[str, dict]]:
        """
        Split markdown by structural markers (lists, rules, etc.).

        Args:
            text: Full markdown text

        Returns:
            List of (section_text, metadata) tuples
        """
        # Split by various structural markers while keeping marker with content
        # Matches: bullet lists, numbered lists, horizontal rules
        pattern = r"(?:(?=\n[-*]\s+)|(?=\n\d+\.\s+)|(?=\n[-*]{3,}\n))"
        sections = re.split(pattern, text)

        result = []
        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Try to extract a heading from the first line
            first_line = section.split("\n")[0]
            heading = first_line[:100]  # Truncate if too long

            metadata = {
                "heading": heading,
                "section": "structural",
                "chunking_method": "structural_markers"
            }
            result.append((section, metadata))

        return result if result else [(text, {"chunking_method": "paragraph_split"})]

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

    def _split_by_paragraphs(
        self, text: str, metadata: dict, use_increased_overlap: bool = False
    ) -> list[tuple[str, dict]]:
        """
        Split text into chunks by paragraphs with optional overlap.

        Args:
            text: Text to split
            metadata: Metadata to attach to chunks
            use_increased_overlap: Use increased overlap for fallback mode

        Returns:
            List of (chunk_text, metadata) tuples
        """
        overlap = self.increased_overlap if use_increased_overlap else self.overlap_tokens

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

        # Add overlap between chunks if requested
        if use_increased_overlap and len(chunks) > 1:
            overlap_chunks = []
            for i in range(len(chunks)):
                current_text = chunks[i][0]

                # Add overlap from previous chunk
                if i > 0:
                    prev_text = chunks[i - 1][0]
                    overlap_text = self._get_overlap_text(prev_text, overlap)
                    current_text = f"{overlap_text}\n\n{current_text}"

                overlap_chunks.append((current_text, chunks[i][1]))

            return overlap_chunks

        return chunks

    def _get_overlap_text(self, text: str, target_tokens: int) -> str:
        """
        Extract the last N tokens from text for overlap.

        Args:
            text: Text to extract overlap from
            target_tokens: Target number of tokens for overlap

        Returns:
            Overlap text
        """
        if not text or target_tokens <= 0:
            return ""

        # Split into sentences and take from the end
        sentences = re.split(r"(?<=[.!?])\s+", text)
        overlap = ""
        tokens = 0

        for i in range(len(sentences) - 1, -1, -1):
            sentence = sentences[i]
            sentence_tokens = self._estimate_tokens(sentence)

            if tokens + sentence_tokens > target_tokens:
                break

            overlap = sentence + (" " if overlap else "") + overlap
            tokens += sentence_tokens

        return overlap.strip()

    def _split_large_section_adaptive(
        self, text: str, metadata: dict
    ) -> list[tuple[str, dict]]:
        """
        Split a large section using adaptive multi-pass strategy.

        Strategy:
        1. Check for markdown subheaders (##, ###, etc.)
        2. If none, try bold heading detection
        3. If insufficient bold headings, try structural markers
        4. Fallback to paragraph splitting with increased overlap

        Args:
            text: Text to split
            metadata: Metadata to attach to chunks

        Returns:
            List of (chunk_text, metadata) tuples
        """
        logger.info("Using adaptive chunking strategy for large section")
        logger.info(f"Text length: {len(text)} chars, estimated tokens: {self._estimate_tokens(text)}")

        # Pass 1: Check for markdown subheaders
        if self._has_markdown_subheaders(text):
            logger.info("Pass 1: Found markdown subheaders, using header-based split")
            sections = self._split_by_headers(text)
            # Filter out empty sections and process
            chunks = []
            for section_text, section_metadata in sections:
                if not section_text.strip():
                    continue
                section_tokens = self._estimate_tokens(section_text)
                if section_tokens <= self.max_tokens:
                    chunks.append((section_text, section_metadata))
                else:
                    # Recursively split large subsections
                    sub_chunks = self._split_by_paragraphs(section_text, section_metadata)
                    chunks.extend(sub_chunks)
            return chunks

        # Pass 2: Try bold heading detection
        bold_count = len(re.findall(r"^\*\*.{6,}\*\*$", text, re.MULTILINE))
        logger.info(f"Pass 2: Found {bold_count} potential bold headings")
        if self._has_bold_headings(text, min_splits=2):
            logger.info("Pass 2: Found sufficient bold headings, using bold-based split")
            sections = self._split_by_bold_headings(text)
            # Check if this produced reasonable splits
            if len(sections) >= 2:
                chunks = []
                for section_text, section_metadata in sections:
                    if not section_text.strip():
                        continue
                    section_tokens = self._estimate_tokens(section_text)
                    if section_tokens <= self.max_tokens:
                        chunks.append((section_text, section_metadata))
                    else:
                        sub_chunks = self._split_by_paragraphs(section_text, section_metadata)
                        chunks.extend(sub_chunks)
                return chunks

        # Pass 3: Try structural markers
        logger.info("Pass 3: Using structural markers for split")
        sections = self._split_by_structural_markers(text)
        # Check if this produced reasonable splits
        if len(sections) >= 2:
            chunks = []
            for section_text, section_metadata in sections:
                if not section_text.strip():
                    continue
                section_tokens = self._estimate_tokens(section_text)
                if section_tokens <= self.max_tokens:
                    chunks.append((section_text, section_metadata))
                else:
                    sub_chunks = self._split_by_paragraphs(section_text, section_metadata)
                    chunks.extend(sub_chunks)
            return chunks

        # Pass 4: Final fallback - paragraph splitting with increased overlap
        logger.info("Pass 4: Fallback to paragraph splitting with increased overlap")
        # Update metadata to reflect fallback method
        fallback_metadata = metadata.copy()
        fallback_metadata["chunking_method"] = "paragraph_split"
        return self._split_by_paragraphs(text, fallback_metadata, use_increased_overlap=True)

    def chunk(self, markdown_text: str) -> list[dict]:
        """
        Chunk markdown text using adaptive multi-pass strategy.

        Args:
            markdown_text: Full markdown text to chunk

        Returns:
            List of chunk dictionaries with 'content' and 'metadata' keys
        """
        logger.info(
            f"Chunking markdown text ({len(markdown_text)} characters) "
            f"with max_tokens={self.max_tokens}, overlap={self.overlap_tokens}"
        )

        # Pass 1: Split by markdown headers (H1-H6)
        sections = self._split_by_headers(markdown_text)

        chunks = []
        for section_text, metadata in sections:
            section_tokens = self._estimate_tokens(section_text)

            # Check if section needs adaptive splitting
            # Apply adaptive splitting if:
            # 1. Section exceeds max_tokens, OR
            # 2. Section is large (>80% of max_tokens) and has sub-structure
            needs_adaptive_splitting = (
                section_tokens > self.max_tokens or
                (section_tokens > self.max_tokens * 0.8 and self._has_markdown_subheaders(section_text)) or
                (section_tokens > self.max_tokens * 0.8 and self._has_bold_headings(section_text, min_splits=2))
            )

            if not needs_adaptive_splitting:
                # Section is small and has no sub-structure, keep as one chunk
                chunks.append({"content": section_text, "metadata": metadata})
            else:
                # Use adaptive strategy for large or complex sections
                logger.info(f"Section ({section_tokens} tokens) needs adaptive splitting")
                sub_chunks = self._split_large_section_adaptive(section_text, metadata)
                for chunk_text, chunk_metadata in sub_chunks:
                    chunks.append({"content": chunk_text, "metadata": chunk_metadata})

        logger.info(
            f"Created {len(chunks)} chunks from markdown "
            f"(avg {len(markdown_text) // len(chunks) if chunks else 0} chars per chunk)"
        )

        return chunks
