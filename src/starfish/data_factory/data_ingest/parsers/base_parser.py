import os


class BaseParser:
    def parse(self, file_path: str) -> str:
        raise NotImplementedError("Subclasses must implement parse method")

    def save(self, content: str, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
