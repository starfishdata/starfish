from urllib.parse import urlparse
import requests
from typing import Dict, Any, Tuple
from starfish.data_ingest.parsers.base_parser import BaseParser


class HTMLDocumentParser(BaseParser):
    def __init__(self):
        super().__init__()
        self._bs4 = None
        self.metadata = {}

    def _load_bs4(self):
        if self._bs4 is None:
            try:
                from bs4 import BeautifulSoup

                self._bs4 = BeautifulSoup
            except ImportError:
                raise ImportError("BeautifulSoup is required for HTML parsing. Install it with: pip install beautifulsoup4")

    def parse(self, file_path: str) -> str:
        """Parse an HTML file or URL into plain text and extract metadata

        Args:
            file_path: Path to the HTML file or URL

        Returns:
            Tuple of (extracted text, metadata dictionary)
        """
        self._load_bs4()

        self.metadata = {}

        # Determine if file_path is a URL or a local file
        if file_path.startswith(("http://", "https://")):
            # It's a URL, fetch content
            response = requests.get(file_path)
            response.raise_for_status()
            html_content = response.text
        else:
            # It's a local file, read it
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        # Parse HTML and extract text
        soup = self._bs4(html_content, "html.parser")

        # Extract metadata
        if soup.title:
            self.metadata["title"] = soup.title.string
        if soup.find("meta", attrs={"name": "description"}):
            self.metadata["description"] = soup.find("meta", attrs={"name": "description"})["content"]
        if soup.find("meta", attrs={"property": "og:type"}):
            self.metadata["type"] = soup.find("meta", attrs={"property": "og:type"})["content"]
        if soup.find("meta", attrs={"charset": True}):
            self.metadata["charset"] = soup.find("meta", attrs={"charset": True})["charset"]

        # Add URL metadata if parsing from URL
        if file_path.startswith(("http://", "https://")):
            parsed_url = urlparse(file_path)
            self.metadata["url"] = file_path
            self.metadata["domain"] = parsed_url.netloc
            self.metadata["path"] = parsed_url.path

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()

        # Get text
        text = soup.get_text()

        # Break into lines and remove leading and trailing space
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text
