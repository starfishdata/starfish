from typing import Optional, List
from .base_parser import BaseParser


class UnstructuredParser(BaseParser):
    def __init__(self, strategy: str = "auto", ocr_languages: Optional[List[str]] = None):
        """
        Initialize the unstructured parser

        Args:
            strategy: Partitioning strategy ("auto", "fast", "hi_res", "ocr_only")
            ocr_languages: List of languages for OCR (e.g., ["eng", "spa"])
        """
        super().__init__()
        self.strategy = strategy
        self.ocr_languages = ocr_languages or ["eng"]
        self._unstructured_loaded = False

    def _load_unstructured(self):
        """Lazy load unstructured module"""
        if not self._unstructured_loaded:
            global partition_pdf
            from unstructured.partition.pdf import partition_pdf

            self._unstructured_loaded = True

    def parse(self, file_path: str) -> str:
        """
        Parse a document using unstructured.io

        Args:
            file_path: Path to the document file

        Returns:
            str: Extracted text content
        """
        try:
            if not self._unstructured_loaded:
                self._load_unstructured()

            # Convert list of languages to comma-separated string
            ocr_lang_str = ",".join(self.ocr_languages)

            # Partition the document
            elements = partition_pdf(
                filename=file_path,
                strategy=self.strategy,
                ocr_languages=ocr_lang_str,  # Pass string instead of list
            )

            # Join elements with double newlines for better readability
            return "\n\n".join([str(el) for el in elements])

        except Exception as e:
            raise Exception(f"Failed to parse document {file_path}: {str(e)}")
