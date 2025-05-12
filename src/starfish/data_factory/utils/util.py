import os
import re
import json
import aiofiles
from typing import List, Dict, Any


def get_platform_name() -> str:
    """Check if the code is running in a Jupyter notebook."""
    try:
        # Check for IPython kernel
        from IPython import get_ipython

        ipython = get_ipython()

        # If not in an interactive environment
        if ipython is None:
            return "PythonShell"

        shell = ipython.__class__.__name__

        # Direct check for Google Colab
        try:
            import google.colab

            shell = "GoogleColabShell"
        except ImportError:
            # Check for VS Code specific environment variables
            if "VSCODE_PID" in os.environ or "VSCODE_CWD" in os.environ:
                shell = "VSCodeShell"
        return shell

    except:
        return "PythonShell"  # Probably standard Python interpreter


def split_into_chunks(text: str, chunk_size: int = 400, overlap: int = 20, min_chunk_size: int = 100) -> List[str]:
    """Split text into chunks with optional overlap.

    Args:
        text: Input text to split
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        min_chunk_size: Minimum acceptable chunk size (avoids tiny final chunks)

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
        if current_chunk and len(current_chunk) + len(para) > chunk_size:
            # Ensure we don't create chunks smaller than min_chunk_size
            if len(current_chunk) >= min_chunk_size:
                chunks.append(current_chunk)

                # Create overlap using sentence boundaries
                sentences = [s for s in re.split(r"(?<=[.!?])\s+", current_chunk) if s]
                overlap_text = ""

                # Add sentences until we reach the desired overlap
                for sentence in reversed(sentences):
                    if len(overlap_text) + len(sentence) <= overlap:
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
    if current_chunk and len(current_chunk) >= min_chunk_size:
        chunks.append(current_chunk)

    return chunks


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract JSON from text that might contain markdown or other content"""
    text = text.strip()

    # Try to parse as complete JSON
    if text.startswith("{") and text.endswith("}") or text.startswith("[") and text.endswith("]"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Look for JSON within Markdown code blocks
    json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(json_pattern, text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try a more aggressive pattern
    json_pattern = r"\{[\s\S]*\}|\[[\s\S]*\]"
    match = re.search(json_pattern, text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from the response")


def read_file(file_path: str) -> str:
    document_text = None
    with open(file_path, "r", encoding="utf-8") as f:
        document_text = f.read()
    return document_text


async def async_read_file(file_path: str) -> str:
    """Asynchronously read a file's contents.

    Args:
        file_path: Path to the file to read

    Returns:
        The file's contents as a string
    """

    async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
        return await f.read()
