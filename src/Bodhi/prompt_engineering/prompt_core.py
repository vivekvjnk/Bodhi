"""
Author: Prophet System Team
Date: 2024-06-15
Core Prompt class for Prophet/Bodhi prompt system.
This file is shared across all generated prompt files.
"""

class Prompt:
    def __init__(self, text: str):
        self.text = text

    def __add__(self, other: "Prompt") -> "Prompt":
        return Prompt(self.text + "\n" + other.text)

    def __sub__(self, other: "Prompt") -> "Prompt":
        return Prompt(self.text.replace(other.text, ""))

    def __str__(self) -> str:
        return self.text

    def format(self, **kwargs) -> str:
        """
        Fill in variables in the prompt text using Python's str.format().
        Returns a plain string (safe for passing into an LLM call).
        """
        return self.text.format(**kwargs)
        
    def text(self) -> str:
        return self.text
