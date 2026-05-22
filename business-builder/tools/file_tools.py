"""File tool — writes markdown content to the outputs/ directory."""

import json
import os
from typing import Any

from crewai.tools import BaseTool

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

_USAGE = (
    "Call this tool with: filepath (string, relative path inside outputs/) "
    "and content (string, full markdown text). "
    'Example: filepath="reports/business_plan.md", content="# My Plan\\n..."'
)


class FileWriteTool(BaseTool):
    name: str = "file_tool"
    description: str = (
        "Writes markdown content to a file inside the outputs/ directory. "
        + _USAGE
    )

    def _run(self, **kwargs: Any) -> str:
        filepath = kwargs.get("filepath") or kwargs.get("file_path")
        content = kwargs.get("content")

        if not filepath:
            return f"Error: 'filepath' argument is required. {_USAGE}"
        if content is None:
            return f"Error: 'content' argument is required. {_USAGE}"

        try:
            full_path = os.path.join(OUTPUTS_DIR, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(str(content))
            return f"Written: {full_path}"
        except Exception as e:
            return f"Error writing file '{filepath}': {e}"


file_tool = FileWriteTool()
