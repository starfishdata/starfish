import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# Import parsers from parsers folder
from starfish.data_factory.data_ingest.parsers import (
    BaseParser,
    PDFParser,
    HTMLDocumentParser,
    YouTubeParser,
    WordDocumentParser,
    PPTParser,
    TXTParser,
    ExcelParser,
)
from starfish.data_factory.utils.util import split_into_chunks

PARSER_MAPPING = {
    # URL patterns
    "youtube.com": YouTubeParser,
    "youtu.be": YouTubeParser,
    # File extensions
    ".pdf": PDFParser,
    ".html": HTMLDocumentParser,
    ".htm": HTMLDocumentParser,
    ".docx": WordDocumentParser,
    ".pptx": PPTParser,
    ".txt": TXTParser,
    ".xlsx": ExcelParser,
    ".xls": ExcelParser,
}


def determine_parser(file_path: str) -> BaseParser:
    """Determine the appropriate parser for a file or URL.

    Args:
        file_path: Path to the file or URL to parse

    Returns:
        Appropriate parser instance

    Raises:
        ValueError: If file extension is not supported
        FileNotFoundError: If file does not exist
    """
    # Check if it's a URL
    if file_path.startswith(("http://", "https://")):
        for pattern, parser in PARSER_MAPPING.items():
            if pattern in file_path:
                return parser()
        return HTMLDocumentParser()  # Default for other URLs

    # File path - determine by extension
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext in PARSER_MAPPING:
        return PARSER_MAPPING[ext]()

    raise ValueError(f"Unsupported file extension: {ext}")


def generate_output_name(file_path: str) -> str:
    """Generate output filename based on input file or URL.

    Args:
        file_path: Path to the file or URL

    Returns:
        Generated filename with .txt extension
    """
    if file_path.startswith(("http://", "https://")):
        if "youtube.com" in file_path or "youtu.be" in file_path:
            video_id = re.search(r"(?:v=|\.be/)([^&]+)", file_path).group(1)
            return f"youtube_{video_id}.txt"
        domain = urlparse(file_path).netloc.replace(".", "_")
        return f"{domain}.txt"

    base_name = os.path.basename(file_path)
    return os.path.splitext(base_name)[0] + ".txt"


def process_file(
    file_path: str,
    output_dir: Optional[str] = None,
    output_name: Optional[str] = None,
) -> str:
    """Process a file using the appropriate parser.

    Args:
        file_path: Path to the file or URL to parse
        output_dir: Directory to save parsed text
        output_name: Custom filename for output

    Returns:
        Path to the output file

    Raises:
        ValueError: If output_dir is not provided
    """
    if not output_dir:
        raise ValueError("Output directory must be specified")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Determine and use parser
    parser = determine_parser(file_path)
    content = parser.parse(file_path)

    # Generate output filename
    output_name = output_name or generate_output_name(file_path)
    if not output_name.endswith(".txt"):
        output_name += ".txt"

    # Save the content
    output_path = os.path.join(output_dir, output_name)
    parser.save(content, output_path)

    return output_path


def generate_input_data(document_text: str, chunk_size: int = 400, min_chunk_size: int = 100, overlap: int = 20, num_pairs: int = 100) -> list:
    from starfish.llm.prompt.prompt_template import qa_generation

    chunks = split_into_chunks(document_text, chunk_size=chunk_size, min_chunk_size=min_chunk_size, overlap=overlap)

    all_qa_pairs = []
    pairs_per_chunk = max(1, round(num_pairs / len(chunks)))
    qa_prompt_template = qa_generation
    all_messages = []
    for i, chunk in enumerate(chunks):
        # Format the prompt with summary and text
        qa_prompt = qa_prompt_template.format(num_pairs=pairs_per_chunk, text=chunk)

        messages = [{"role": "system", "content": qa_prompt}]
        all_messages.append(messages)
    print(f"Processing {len(chunks)} chunks to generate QA pairs...")
    return all_messages
