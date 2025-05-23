from typing import List
import re

from starfish.data_ingest.splitter.base_splitter import TextSplitter


class TextChunkSplitter(TextSplitter):
    """Splitting text into chunks with optional overlap and minimum size constraints."""

    def __init__(
        self,
        chunk_size: int = 400,
        overlap: int = 20,
        min_chunk_size: int = 100,
    ) -> None:
        """Create a new TextChunkSplitter.

        Args:
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum acceptable chunk size (avoids tiny final chunks)
        """
        self._chunk_size = chunk_size
        self._overlap = overlap
        self._min_chunk_size = min_chunk_size

    def split_text(self, text: str) -> List[str]:
        """Split text into chunks with optional overlap.

        Args:
            text: Input text to split

        Returns:
            List of text chunks
        """
        # Normalize whitespace and handle different paragraph separators
        text = re.sub(r"\n{2,}", "\n\n", text.strip())
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # Skip empty paragraphs
            if not para.strip():
                continue

            # If adding this paragraph would exceed chunk size
            if current_chunk and len(current_chunk) + len(para) > self._chunk_size:
                # Ensure we don't create chunks smaller than min_chunk_size
                if len(current_chunk) >= self._min_chunk_size:
                    chunks.append(current_chunk)

                    # Create overlap using sentence boundaries
                    sentences = [s for s in re.split(r"(?<=[.!?])\s+", current_chunk) if s]
                    overlap_text = ""

                    # Add sentences until we reach the desired overlap
                    for sentence in reversed(sentences):
                        if len(overlap_text) + len(sentence) <= self._overlap:
                            overlap_text = sentence + " " + overlap_text
                        else:
                            break

                    current_chunk = overlap_text.strip() + "\n\n" + para
                else:
                    # If chunk is too small, keep adding to it
                    current_chunk += "\n\n" + para
            else:
                current_chunk += ("\n\n" + para) if current_chunk else para

        # Add the final chunk if it meets minimum size
        if current_chunk and len(current_chunk) >= self._min_chunk_size:
            chunks.append(current_chunk)

        return chunks
