from abc import ABC, abstractmethod
from dataclasses import dataclass
from starfish.llm.prompt.prompt_template import qa_generation


class PromptFormatter(ABC):
    """Abstract base class for prompt configurations"""

    @abstractmethod
    def format(self) -> str:
        """Format the template with provided parameters"""
        pass


@dataclass
class QAGenerationPrompt(PromptFormatter):
    """Dataclass for QA generation prompt configuration"""

    template: str = qa_generation
    num_pairs: int = 5
    text: str = ""

    def format(self) -> str:
        """Format the template with num_pairs and provided text"""
        return self.template.format(num_pairs=self.num_pairs, text=self.text)
