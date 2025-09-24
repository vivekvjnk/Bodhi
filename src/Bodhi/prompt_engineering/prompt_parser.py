"""
Author: Prophet System Team
Date: 2024-06-15
Prompt Parser for Prophet/Bodhi
Builds a hierarchical dictionary of Prompt objects from generated prompt files.
"""

import importlib
import re
from types import ModuleType
from typing import Dict, Any

def parse_prompts(module_name: str) -> Dict[str, Any]:
    """
    Parse a prompt module into a hierarchical dictionary.

    Args:
        module_name (str): Name of the Python module (e.g., "example_prompts")

    Returns:
        dict: Hierarchical dictionary of prompts
    """
    mod: ModuleType = importlib.import_module(module_name)
    prompt_dict: Dict[str, Any] = {}

    roles = ["system","human","user","source"]
    for name, obj in vars(mod).items():
        if not name.startswith("PROMPT_"):
            continue

        if not hasattr(obj, "text"):  # not a Prompt
            continue

        # Example: PROMPT_ENTITY_EXTRACTION_SYSTEM
        parts = name[len("PROMPT_"):].split("_")

        # Build hierarchy
        d = prompt_dict
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        
        if parts[-1].lower() in roles:
            d[parts[-1].lower()] = obj # parts[-1].lower() : Last part of the name is the LLM role. it should be lower case.
        else:
            d[parts[-1]] = obj

    return prompt_dict
