from abc import ABC, abstractmethod


class TextSplitter(ABC):
    """Abstract base class for text splitters."""

    @abstractmethod
    def split_text(self, text: str) -> list[str]:
        """Split text into chunks.

        Args:
            text: The text to split.

        Returns:
            List of text chunks.
        """
        pass
