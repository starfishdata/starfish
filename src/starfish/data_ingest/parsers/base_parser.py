import os


class BaseParser:
    def __init__(self):
        """Initialize the base parser."""
        pass

    def parse(self, file_path: str) -> str:
        raise NotImplementedError("Subclasses must implement parse method")

    async def parse_async(self, file_path: str) -> str:
        """Asynchronously parse the file content.

        Args:
            file_path: Path to the file to parse

        Returns:
            str: Parsed content
        """
        raise NotImplementedError("Subclasses must implement parse_async method")

    def save(self, content: str, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
