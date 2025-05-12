from dataclasses import dataclass
from typing import Any, Callable, Collection, List, Literal, Optional, Union, AbstractSet

from starfish.data_ingest.splitter.base_splitter import TextSplitter


class TokenTextSplitter(TextSplitter):
    """Splits text into chunks using a tokenizer, with configurable chunk size and overlap."""

    def __init__(
        self,
        encoding_name: str = "gpt2",
        model_name: Optional[str] = None,
        allowed_special: Union[Literal["all"], AbstractSet[str]] = set(),
        disallowed_special: Union[Literal["all"], Collection[str]] = "all",
        chunk_size: int = 400,
        chunk_overlap: int = 20,
        **kwargs: Any,
    ) -> None:
        """Initialize the token splitter.

        Args:
            encoding_name: Name of the encoding to use
            model_name: Optional model name to get encoding for
            allowed_special: Special tokens to allow
            disallowed_special: Special tokens to disallow
            chunk_size: Maximum number of tokens per chunk
            chunk_overlap: Number of overlapping tokens between chunks
        """
        super().__init__(**kwargs)
        self._tokenizer = self._get_tokenizer(encoding_name, model_name)
        self._allowed_special = allowed_special
        self._disallowed_special = disallowed_special
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def _get_tokenizer(self, encoding_name: str, model_name: Optional[str]) -> Any:
        """Get tokenizer instance."""
        try:
            import tiktoken

            return tiktoken.encoding_for_model(model_name) if model_name else tiktoken.get_encoding(encoding_name)
        except ImportError:
            raise ImportError("tiktoken package required. Install with `pip install tiktoken`.")

    def split_text(self, text: str) -> List[str]:
        """Split text into chunks based on tokenization."""
        tokenizer = Tokenizer(
            chunk_overlap=self._chunk_overlap,
            tokens_per_chunk=self._chunk_size,
            decode=self._tokenizer.decode,
            encode=lambda t: self._tokenizer.encode(
                t,
                allowed_special=self._allowed_special,
                disallowed_special=self._disallowed_special,
            ),
        )
        return split_text_on_tokens(text=text, tokenizer=tokenizer)


@dataclass(frozen=True)
class Tokenizer:
    """Tokenizer data class."""

    chunk_overlap: int
    """Overlap in tokens between chunks"""
    tokens_per_chunk: int
    """Maximum number of tokens per chunk"""
    decode: Callable[[List[int]], str]
    """ Function to decode a list of token ids to a string"""
    encode: Callable[[str], List[int]]
    """ Function to encode a string to a list of token ids"""


def split_text_on_tokens(*, text: str, tokenizer: Tokenizer) -> List[str]:
    """Split incoming text and return chunks using tokenizer."""
    splits: List[str] = []
    input_ids = tokenizer.encode(text)
    start_idx = 0
    cur_idx = min(start_idx + tokenizer.tokens_per_chunk, len(input_ids))
    chunk_ids = input_ids[start_idx:cur_idx]
    while start_idx < len(input_ids):
        splits.append(tokenizer.decode(chunk_ids))
        if cur_idx == len(input_ids):
            break
        start_idx += tokenizer.tokens_per_chunk - tokenizer.chunk_overlap
        cur_idx = min(start_idx + tokenizer.tokens_per_chunk, len(input_ids))
        chunk_ids = input_ids[start_idx:cur_idx]
    return splits
