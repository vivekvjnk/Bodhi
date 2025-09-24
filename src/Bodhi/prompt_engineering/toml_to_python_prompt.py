
#!/usr/bin/env python3
"""
Author: Prophet System Team
Date: 2024-06-15
TOML → Python Prompt Converter
Usage:
    python toml_to_python.py input.toml output.py
"""

import sys
import toml
import os

HEADER = '''"""
Author: Prophet System Team
Auto-generated Prompt File (from TOML)
Do not edit manually.
"""

from prompt_core import Prompt

'''

def to_constant_name(section, field):
    return f"PROMPT_{"".join([s.capitalize() for s in section.split("_")])}_{field.upper()}"

def convert_toml_to_python(toml_file, py_file):
    # Load TOML
    data = toml.load(toml_file)

    # Open .py output
    with open(py_file, "w") as out:
        out.write(HEADER)

        for section, content in data.items():
            if not isinstance(content, dict):
                continue

            for field, text in content.items():
                if not text:  # skip empty
                    continue
                const_name = to_constant_name(section, field)
                out.write(f'{const_name} = Prompt("""{text.strip()}""")\n')

    print(f"[✓] Converted {toml_file} → {py_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python toml_to_python.py input.toml output.py")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        sys.exit(1)

    convert_toml_to_python(input_file, output_file)
