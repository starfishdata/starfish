import os
from typing import Dict, Any
from starfish.data_ingest.parsers.base_parser import BaseParser


class PDFParser(BaseParser):
    """Parser for PDF documents"""

    def __init__(self):
        super().__init__()
        self._pdfminer_loaded = False
        self.supported_extensions = [".pdf"]
        self.metadata = {}

    def _load_pdfminer(self):
        """Lazy load pdfminer module"""
        if not self._pdfminer_loaded:
            global extract_text
            from pdfminer.high_level import extract_text

            self._pdfminer_loaded = True

    def parse(self, file_path: str) -> str:
        """Parse a PDF file into plain text

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text from the PDF
        """
        try:
            if not self._pdfminer_loaded:
                self._load_pdfminer()

            # Extract metadata
            from pdfminer.pdfparser import PDFParser as PDFMinerParser
            from pdfminer.pdfdocument import PDFDocument

            with open(file_path, "rb") as f:
                parser = PDFMinerParser(f)
                document = PDFDocument(parser)
                self.metadata = {
                    "title": document.info[0].get("Title", b"").decode("utf-8", errors="ignore"),
                    "author": document.info[0].get("Author", b"").decode("utf-8", errors="ignore"),
                    "creation_date": document.info[0].get("CreationDate", b"").decode("utf-8", errors="ignore"),
                    "modification_date": document.info[0].get("ModDate", b"").decode("utf-8", errors="ignore"),
                }

            return extract_text(file_path)
        except ImportError:
            raise ImportError("pdfminer.six is required for PDF parsing. Install it with: pip install pdfminer.six")

    def get_metadata(self) -> Dict[str, Any]:
        """Get document metadata

        Returns:
            Dictionary containing document metadata
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

    # def save(self, content: str, output_path: str) -> None:
    #     """Save the extracted text to a file

    #     Args:
    #         content: Extracted text content
    #         output_path: Path to save the text
    #     """
    #     os.makedirs(os.path.dirname(output_path), exist_ok=True)
    #     with open(output_path, "w", encoding="utf-8") as f:
    #         f.write(content)
