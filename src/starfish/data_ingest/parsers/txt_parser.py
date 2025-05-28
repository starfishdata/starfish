import os
from typing import Dict, Any
from starfish.data_ingest.parsers.base_parser import BaseParser


class TXTParser(BaseParser):
    """Parser for plain text files"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = [".txt"]
        self.metadata = {}

    def parse(self, file_path: str) -> str:
        """Parse a text file

        Args:
            file_path: Path to the text file

        Returns:
            Text content
        """
        # Basic file metadata
        self.metadata = {"file_size": os.path.getsize(file_path), "modified_time": os.path.getmtime(file_path), "created_time": os.path.getctime(file_path)}

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_metadata(self) -> Dict[str, Any]:
        """Get file metadata

        Returns:
            Dictionary containing file metadata
        """
        return self.metadata

    def is_supported(self, file_path: str) -> bool:
        """Check if the file is supported by this parser

        Args:
            file_path: Path to the file

        Returns:
            True if the file is supported, False otherwise
        """
        return os.path.splitext(file_path)[1].lower() in self.supported_extensions
