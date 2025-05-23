import re
import json
import aiofiles
from typing import Dict, Any


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
