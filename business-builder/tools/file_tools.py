"""File tool — writes markdown content to the outputs/ directory."""

import os
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")


class FileWriteInput(BaseModel):
    filepath: str = Field(description="Relative path within outputs/ to write to, e.g. 'reports/business_plan.md'")
    content: str = Field(description="Markdown content to write to the file")


class FileWriteTool(BaseTool):
    name: str = "file_tool"
    description: str = "Writes markdown content to a file inside the outputs/ directory."
    args_schema: type[BaseModel] = FileWriteInput

    def _run(self, filepath: str, content: str) -> str:
        try:
            full_path = os.path.join(OUTPUTS_DIR, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Written: {full_path}"
        except Exception as e:
            return f"Error writing file '{filepath}': {e}"


file_tool = FileWriteTool()
